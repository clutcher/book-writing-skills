#!/usr/bin/env python3
"""Check that every person the book names is introduced properly on first mention (rule 2.7).

Persons are read from the authors of the .bib file (`sources.bibliography` in the book config) and the
chapters are scanned in book order. Front matter, back matter and the bibliography are skipped:
a reader can skip a preface, so an introduction there cannot carry the introduction duty.

Findings:
    BARE_SURNAME      the first mention uses only the surname
    NO_CONTEXT        the first mention says nothing about who the person is or why they matter
    CREDENTIALS_BIO   the introduction reads like a conference bio, not like a contribution
    RE_INTRODUCTION   credentials repeated after the first mention, as a bio or as an
                      appositive ("X, whose *Book* argues ...", "X, known for ...")

The default (full name at first mention, the surname alone after it) needs only the main
check. --bare-mentions is a worklist for a book whose voice profile asks for the full name on
later mentions or after long gaps: it lists every bare-surname mention, first and later. Full names are taken from the prose itself and checked against the initials in the .bib file.
Each row shows the distance since the last mention and a suggestion: PRONOUN (a tight repeat,
a pronoun reads better) or EXPAND (farther away, use the full name). Eponyms (a named law, a
named test) are skipped when the book lists them; with no eponyms in the book config, that
filter prints SKIPPED and every bare surname is listed.

Book-specific names live in `terms.watch_words.people` in the book config:
    people:
      aliases: {"Rivera, M.L.": [Maria Rivera, M. L. Rivera]}   # "Surname, Initials" of a .bib author
      eponyms: {Rivera: ["Rivera'?s?\\s+rule"]}               # eponym patterns to skip

Exit codes: 0 no findings, 1 findings, 2 the check could not run.
"""

import argparse
import contextlib
import io
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass, field

sys.dont_write_bytecode = True

from book_files import (ConfigError, SAMPLE_BOOK, add_config_arguments, config_for_targets,
                        is_english_book, natural_sort_key, skipped_for_language, tool_failed,
                        watch_words)
from check_output import run_main
from bibliography import plain_text, read_identities
from citations import CITATION
from terminal_colors import BOLD, CYAN, GREEN, NC, RED, YELLOW

SKIPPED_KINDS = {'front-matter', 'references', 'back-matter'}

CREDENTIALS_PATTERNS = [
    r'known\s+for\s+(?:his|her|their)\s+work',
    r'(?:a|an)\s+(?:renowned|well-known|famous|noted|prominent|celebrated|distinguished)',
    r'(?:a|an)\s+(?:senior|principal|lead|chief)\s+(?:[\w-]+\s+)?(?:officer|executive|editor|engineer|scientist|consultant)',
    r'(?:a|an)\s+(?:\w+\s+)?(?:Fellow|expert)',
    r'co-?founder\s+of',
    r'(?:a|an)\s+(?:\w+\s+)?trainer\s+(?:and|who)',
    r'award-winning',
    r'best-selling\s+author',
    r'creator\s+of\s+(?:the\s+)?(?:\w+\s+){0,2}(?:method|series|brand|programme|program)',
]

INTRODUCTION_PATTERNS = [
    r'(?:wrote|developed|created|designed|proposed|introduced|formalized|coined|named|defined|described|identified|discovered|observed|studied|argued|maintained|emphasized|concluded|spent\s+years|offered|pioneered|invented|captured|led\s+the|applied|translated|extended|advocated|championed|reported|examined|articulated|warned|targeted)',
    r'in\s+\*[^*]+\*',
    r'in\s+"[^"]+"',
    r'whose\s+[*`"\']*\w+',
    r'who\s+(?:spent|worked|observed|studied|proposed|developed|wrote|created|invented|designed|led|applied)',
    r'(?:experience|work)\s+(?:led|with|on)',
    r'was\s+(?:a|an|the)\s+\w+',
]

APPOSITIVE_CREDENTIAL_PATTERNS = [
    r'^\s*,\s*(?:who|whose)\b',
    r'^\s*,\s*(?:an?|the)\s+[^,]{0,80}?\b(?:who|whose)\b',
    r'^\s*,\s*(?:an?|the)\s+(?:[\w-]+\s+){0,3}'
    r'(?:engineer|architect|scientist|designer|professor|doctor|physician|historian|'
    r'researcher|author|writer|journalist|economist|consultant|psychologist|'
    r'mathematician|practitioner|teacher|lawyer)\b',
    r'^\s*,\s*(?:co-?author|author|creator|inventor|founder|co-?founder)\s+of\b',
    r'^\s*,\s*known\s+for\b',
    r'^\s+was\s+(?:an?|the)\b',
]

CHAPTER_ORDER: List[str] = []

NON_PROSE_FILES = {'toc', 'copyright', 'references', 'preface',
                   'acknowledgments', 'dedication', 'epigraph'}
RULE_LINE = "\u2500"


def discover_chapter_order(manuscript_dir: str, config) -> List[str]:
    if not Path(manuscript_dir).is_dir():
        return []
    names = [path.name for path in Path(manuscript_dir).glob('*.md')]
    prose = [n for n in names
             if config.classify(Path(manuscript_dir) / n)[0] not in SKIPPED_KINDS
             and not any(marker in n.lower() for marker in NON_PROSE_FILES)]
    return sorted(prose, key=natural_sort_key)


@dataclass
class Person:
    full_name: str
    surname: str
    first_names: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    citation_keys: List[str] = field(default_factory=list)


@dataclass
class Mention:
    chapter: str
    line_num: int
    line_content: str
    match_text: str
    uses_full_name: bool
    has_introduction: bool
    has_credentials_bio: bool
    has_appositive_credential: bool = False
    context_before: str = ""
    context_after: str = ""


@dataclass
class Issue:
    person: str
    issue_type: str
    chapter: str
    line_num: int
    detail: str
    context: str = ""


KNOWN_ALIASES: Dict[str, List[str]] = {}

EPONYM_PATTERNS: Dict[str, List[str]] = {}

AMBIGUOUS_SURNAMES = {'An'}

PRONOUN_WORD_MAX = 25
PRONOUN_SENT_MAX = 1

NAME_STOPWORDS = {
    'The', 'This', 'That', 'These', 'Those', 'A', 'An', 'And', 'But', 'Or', 'So',
    'Yet', 'For', 'Nor', 'As', 'At', 'By', 'In', 'On', 'Of', 'To', 'From', 'With',
    'Into', 'Onto', 'Out', 'Over', 'Under', 'However', 'Because', 'Since', 'While',
    'When', 'Where', 'Why', 'How', 'If', 'Then', 'Else', 'Although', 'Though',
    'Despite', 'Unlike', 'Like', 'Both', 'Each', 'Either', 'Neither', 'All', 'Some',
    'Many', 'Most', 'Few', 'Several', 'One', 'Two', 'Three', 'First', 'Second',
    'Third', 'Later', 'Modern', 'Today', 'Here', 'There', 'Now', 'Still', 'Instead',
    'Also', 'Even', 'Only', 'Just', 'Indeed', 'Thus', 'Hence', 'Therefore',
    'Moreover', 'Furthermore', 'Meanwhile', 'Before', 'After', 'During', 'Through',
    'Within', 'Across', 'Between', 'Among', 'Against', 'Toward', 'Towards', 'About',
    'Around', 'Beyond', 'Behind', 'Besides', 'Above', 'Below', 'Inside', 'Outside',
    'Near', 'Next', 'Per', 'Via', 'Versus', 'Unfortunately', 'Later', 'Earlier',
}


def initials_of(first: str) -> str:
    words = [word for word in re.split(r"[\s.\-]+", first) if word]
    return "".join(f"{word[0].upper()}." for word in words)


def read_persons(bibliography_path: str) -> Dict[str, Person]:
    if not Path(bibliography_path).is_file():
        print(f"{RED}Error: bibliography not found: {bibliography_path}{NC}")
        return {}

    persons: Dict[str, Person] = {}

    for key, entry in read_identities(bibliography_path).items():
        for name in entry.authors or entry.editors:
            if name.corporate or name.others:
                continue
            surname = name.surname
            first_init = initials_of(plain_text(name.first))
            if not surname or not first_init:
                continue

            if surname not in persons:
                persons[surname] = Person(
                    full_name=f"{first_init} {surname}",
                    surname=surname,
                    first_names=[first_init],
                    aliases=[],
                    citation_keys=[key],
                )
            else:
                if key not in persons[surname].citation_keys:
                    persons[surname].citation_keys.append(key)
                if first_init not in persons[surname].first_names:
                    persons[surname].first_names.append(first_init)

            for alias_key in (f"{surname}, {first_init}", f"{surname}, {plain_text(name.first)}"):
                for alias in KNOWN_ALIASES.get(alias_key, []):
                    if alias not in persons[surname].aliases:
                        persons[surname].aliases.append(alias)

    return persons


def is_inside_code_block(lines: List[str], line_idx: int) -> bool:
    in_code = False
    for i in range(line_idx):
        if lines[i].strip().startswith('```'):
            in_code = not in_code
    return in_code


def is_inside_comment(line: str, match_start: int) -> bool:
    before = line[:match_start]
    return bool(re.search(r'#\s*$', before)) or bool(re.search(r'//\s*$', before))


def is_citation_only(line: str, match_start: int, match_end: int) -> bool:
    return any(found.start() <= match_start and match_end <= found.end()
               for found in CITATION.finditer(line))


def is_possessive_citation(line: str, surname: str) -> bool:
    return bool(re.search(rf"{re.escape(surname)}'s\s+\[", line))


def find_mentions(chapter_path: str, persons: Dict[str, Person]) -> List[Tuple[str, Mention]]:
    with open(chapter_path, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.split('\n')

    chapter_name = Path(chapter_path).name
    mentions: List[Tuple[str, Mention]] = []
    seen_lines: Dict[str, set] = {}

    for surname, person in persons.items():
        search_terms = [surname]
        for alias in person.aliases:
            if alias != surname:
                search_terms.append(alias)

        search_terms.sort(key=len, reverse=True)
        seen_lines[surname] = set()

        for term in search_terms:
            escaped = re.escape(term)
            pattern = rf'(?<![`\w]){escaped}(?![`\w])'

            for i, line in enumerate(lines):
                if i in seen_lines[surname]:
                    continue

                if is_inside_code_block(lines, i):
                    continue

                if line.strip().startswith('#'):
                    continue

                for m in re.finditer(pattern, line):
                    if is_inside_comment(line, m.start()):
                        continue

                    if is_citation_only(line, m.start(), m.end()):
                        continue

                    seen_lines[surname].add(i)

                    context_before = lines[max(0, i-2):i]
                    context_after = lines[i+1:min(len(lines), i+3)]

                    surrounding = ' '.join(context_before + [line] + context_after)

                    uses_full = False
                    for alias in person.aliases:
                        if ' ' in alias and alias in surrounding:
                            uses_full = True
                            break
                    full_name_pattern = rf'[A-Z][a-z]+\s+{re.escape(surname)}'
                    if re.search(full_name_pattern, surrounding):
                        uses_full = True

                    has_intro = False
                    for intro_pat in INTRODUCTION_PATTERNS:
                        nearby = ' '.join(context_before[-1:] + [line] + context_after[:1])
                        if re.search(intro_pat, nearby):
                            has_intro = True
                            break

                    has_cred = False
                    for cred_pat in CREDENTIALS_PATTERNS:
                        nearby_text = ' '.join(context_before[-1:] + [line])
                        if re.search(cred_pat, nearby_text, re.IGNORECASE):
                            has_cred = True
                            break

                    trailing = line[m.end():]
                    has_appositive = any(
                        re.match(pat, trailing, re.IGNORECASE)
                        for pat in APPOSITIVE_CREDENTIAL_PATTERNS
                    )

                    mention = Mention(
                        chapter=chapter_name,
                        line_num=i + 1,
                        line_content=line.strip(),
                        match_text=m.group(),
                        uses_full_name=uses_full,
                        has_introduction=has_intro,
                        has_credentials_bio=has_cred,
                        has_appositive_credential=has_appositive,
                        context_before='\n'.join(context_before),
                        context_after='\n'.join(context_after),
                    )
                    mentions.append((surname, mention))
                    break

    return mentions


def chapter_sort_key(chapter_name: str) -> int:
    if chapter_name in CHAPTER_ORDER:
        return CHAPTER_ORDER.index(chapter_name)
    return 999


def analyze(manuscript_dir: str, bibliography_path: str, verbose: bool = False) -> List[Issue]:
    persons = read_persons(bibliography_path)
    if not persons:
        print(f"{RED}No persons found among the authors in the .bib file.{NC}")
        return []

    chapter_files = []
    for ch in CHAPTER_ORDER:
        path = Path(manuscript_dir, ch)
        if Path(path).exists():
            chapter_files.append(path)

    all_mentions: Dict[str, List[Mention]] = {}

    for chapter_path in chapter_files:
        chapter_mentions = find_mentions(chapter_path, persons)
        for surname, mention in chapter_mentions:
            if surname not in all_mentions:
                all_mentions[surname] = []
            all_mentions[surname].append(mention)

    for surname in all_mentions:
        all_mentions[surname].sort(
            key=lambda m: (chapter_sort_key(m.chapter), m.line_num)
        )

    issues: List[Issue] = []

    mentioned_persons = {
        surname: mentions
        for surname, mentions in all_mentions.items()
        if len(mentions) > 0
    }

    print(f"\n{BOLD}{'='*80}{NC}")
    print(f"{BOLD}PERSON INTRODUCTION CHECK{NC}")
    print(f"{BOLD}{'='*80}{NC}\n")

    print(f"{CYAN}Found {len(mentioned_persons)} persons mentioned in manuscript{NC}\n")

    print(f"{BOLD}{RULE_LINE * 80}{NC}")
    print(f"{BOLD}FIRST MENTION REGISTRY{NC}")
    print(f"{BOLD}{RULE_LINE * 80}{NC}\n")

    print(f"  {'Person':<30} {'First Mention':<20} {'Line':<6} {'Full Name':<10} {'Intro':<8} {'Total':<6}")
    print(f"  {RULE_LINE * 30} {RULE_LINE * 20} {RULE_LINE * 6} {RULE_LINE * 10} {RULE_LINE * 8} {RULE_LINE * 6}")

    sorted_persons = sorted(
        mentioned_persons.items(),
        key=lambda x: (chapter_sort_key(x[1][0].chapter), x[1][0].line_num)
    )

    for surname, mentions in sorted_persons:
        first = mentions[0]
        full_mark = f"{GREEN}{'yes':<8}{NC}" if first.uses_full_name else f"{RED}{'NO':<8}{NC}"
        intro_mark = f"{GREEN}{'yes':<6}{NC}" if first.has_introduction else f"{RED}{'NO':<6}{NC}"
        total = len(mentions)

        display_name = surname
        if persons[surname].aliases:
            for alias in persons[surname].aliases:
                if ' ' in alias:
                    display_name = alias
                    break

        print(f"  {display_name:<30} {first.chapter:<20} {first.line_num:<6} {full_mark} {intro_mark} {total:<6}")

    print()

    properly_introduced = []
    for surname, mentions in sorted_persons:
        first = mentions[0]
        if first.uses_full_name and first.has_introduction and not first.has_credentials_bio:
            display_name = surname
            for alias in persons[surname].aliases:
                if ' ' in alias:
                    display_name = alias
                    break
            properly_introduced.append((display_name, first))

    if properly_introduced:
        print(f"{BOLD}{RULE_LINE * 80}{NC}")
        print(f"{GREEN}PROPERLY INTRODUCED ({len(properly_introduced)} persons){NC}")
        print(f"{BOLD}{RULE_LINE * 80}{NC}\n")

        for display_name, first in properly_introduced:
            truncated = first.line_content[:110] + '...' if len(first.line_content) > 110 else first.line_content
            print(f"  {GREEN}{display_name:<28}{NC} {first.chapter}:{first.line_num}")
            print(f"    {truncated}")
            print()

    for surname, mentions in sorted_persons:
        first = mentions[0]
        person = persons[surname]

        display_name = surname
        for alias in person.aliases:
            if ' ' in alias:
                display_name = alias
                break

        if not first.uses_full_name:
            issues.append(Issue(
                person=display_name,
                issue_type='BARE_SURNAME',
                chapter=first.chapter,
                line_num=first.line_num,
                detail=f'First mention uses bare surname "{first.match_text}" without full name',
                context=first.line_content,
            ))

        if not first.has_introduction:
            issues.append(Issue(
                person=display_name,
                issue_type='NO_CONTEXT',
                chapter=first.chapter,
                line_num=first.line_num,
                detail='First mention lacks introduction (who they are / why their opinion matters)',
                context=first.line_content,
            ))

        if first.has_credentials_bio:
            issues.append(Issue(
                person=display_name,
                issue_type='CREDENTIALS_BIO',
                chapter=first.chapter,
                line_num=first.line_num,
                detail='Introduction uses credentials/bio style instead of contribution-based',
                context=first.line_content,
            ))

        for mention in mentions[1:]:
            if mention.has_credentials_bio:
                issues.append(Issue(
                    person=display_name,
                    issue_type='RE_INTRODUCTION',
                    chapter=mention.chapter,
                    line_num=mention.line_num,
                    detail='Redundant re-introduction with credentials after first mention',
                    context=mention.line_content,
                ))
            elif mention.has_appositive_credential:
                issues.append(Issue(
                    person=display_name,
                    issue_type='RE_INTRODUCTION',
                    chapter=mention.chapter,
                    line_num=mention.line_num,
                    detail='Credential clause attached to the name after first mention '
                           '(name the person and the work, not why they matter)',
                    context=mention.line_content,
                ))

    if issues:
        print(f"{BOLD}{RULE_LINE * 80}{NC}")
        print(f"{BOLD}ISSUES ({len(issues)} found){NC}")
        print(f"{BOLD}{RULE_LINE * 80}{NC}\n")

        by_type: Dict[str, List[Issue]] = {}
        for issue in issues:
            if issue.issue_type not in by_type:
                by_type[issue.issue_type] = []
            by_type[issue.issue_type].append(issue)

        type_labels = {
            'BARE_SURNAME': f'{RED}BARE_SURNAME{NC} -- First mention uses only surname, needs full name',
            'NO_CONTEXT': f'{YELLOW}NO_CONTEXT{NC} -- First mention lacks "who they are / why it matters"',
            'CREDENTIALS_BIO': f'{YELLOW}CREDENTIALS_BIO{NC} -- Bio/credentials style instead of contribution-based',
            'RE_INTRODUCTION': f'{CYAN}RE_INTRODUCTION{NC} -- Redundant re-introduction after first mention',
        }

        for issue_type in ['BARE_SURNAME', 'NO_CONTEXT', 'CREDENTIALS_BIO', 'RE_INTRODUCTION']:
            if issue_type not in by_type:
                continue

            print(f"  {type_labels[issue_type]}")
            print()

            for issue in by_type[issue_type]:
                print(f"    {issue.person:<25} {issue.chapter}:{issue.line_num}")
                print(f"    {issue.detail}")
                if verbose:
                    truncated = issue.context[:120] + '...' if len(issue.context) > 120 else issue.context
                    print(f"    Context: {truncated}")
                print()
    else:
        print(f"{GREEN}No issues found. All persons are properly introduced.{NC}\n")

    if verbose and mentioned_persons:
        print(f"{BOLD}{RULE_LINE * 80}{NC}")
        print(f"{BOLD}ALL MENTIONS (by person){NC}")
        print(f"{BOLD}{RULE_LINE * 80}{NC}\n")

        for surname, mentions in sorted_persons:
            display_name = surname
            for alias in persons[surname].aliases:
                if ' ' in alias:
                    display_name = alias
                    break

            print(f"  {BOLD}{display_name}{NC} ({len(mentions)} mentions)")
            for i, mention in enumerate(mentions):
                marker = ">>> " if i == 0 else "    "
                full_tag = "[full]" if mention.uses_full_name else "[surname]"
                intro_tag = "[intro]" if mention.has_introduction else ""
                cred_tag = "[bio]" if mention.has_credentials_bio else ""
                tags = f" {full_tag}{intro_tag}{cred_tag}"
                print(f"    {marker}{mention.chapter}:{mention.line_num}{tags}")
                if verbose and i == 0:
                    truncated = mention.line_content[:100] + '...' if len(mention.line_content) > 100 else mention.line_content
                    print(f"         {truncated}")
            print()

    bare_count = sum(1 for i in issues if i.issue_type == 'BARE_SURNAME')
    no_ctx_count = sum(1 for i in issues if i.issue_type == 'NO_CONTEXT')
    cred_count = sum(1 for i in issues if i.issue_type == 'CREDENTIALS_BIO')
    re_intro_count = sum(1 for i in issues if i.issue_type == 'RE_INTRODUCTION')

    print(f"{BOLD}{RULE_LINE * 80}{NC}")
    print(f"Summary: {len(mentioned_persons)} persons, {len(issues)} issues")
    if issues:
        parts = []
        if bare_count:
            parts.append(f"{RED}{bare_count} bare surname{NC}")
        if no_ctx_count:
            parts.append(f"{YELLOW}{no_ctx_count} no context{NC}")
        if cred_count:
            parts.append(f"{YELLOW}{cred_count} credentials bio{NC}")
        if re_intro_count:
            parts.append(f"{CYAN}{re_intro_count} re-introduction{NC}")
        print(f"  {', '.join(parts)}")
    print(f"{BOLD}{RULE_LINE * 80}{NC}\n")

    return issues


def derive_full_names(manuscript_dir: str, persons: Dict[str, Person]) -> Dict[str, dict]:
    initials: Dict[str, set] = {}
    for surname, person in persons.items():
        for fi in person.first_names:
            if fi and fi[0].isalpha():
                initials.setdefault(surname, set()).add(fi[0].upper())

    pred_counts: Dict[str, Dict[str, int]] = {sn: {} for sn in persons}
    surnames = sorted(persons, key=len, reverse=True)

    for ch in CHAPTER_ORDER:
        path = Path(manuscript_dir, ch)
        if not Path(path).exists():
            continue
        lines = open(path, 'r', encoding='utf-8').read().split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('#') or is_inside_code_block(lines, i):
                continue
            for sn in surnames:
                for m in re.finditer(rf"\b([A-Z][a-zA-Z'-]+)\s+{re.escape(sn)}\b", line):
                    pred = m.group(1)
                    pred_counts[sn][pred] = pred_counts[sn].get(pred, 0) + 1

    derived: Dict[str, dict] = {}
    for sn in persons:
        alias_tokens: set = set()
        alias_full: Optional[str] = None
        for alias in persons[sn].aliases:
            if ' ' in alias:
                alias_tokens.add(alias.split()[0])
                if alias_full is None:
                    alias_full = alias

        valid: Dict[str, int] = {}
        for pred, c in pred_counts.get(sn, {}).items():
            if pred in NAME_STOPWORDS:
                continue
            ini = initials.get(sn)
            if pred in alias_tokens or (ini and pred[0].upper() in ini):
                valid[pred] = c

        spellings = set(valid) | alias_tokens
        if valid:
            canonical = max(valid, key=lambda w: valid[w])
            full = f"{canonical} {sn}"
        else:
            full = alias_full
        warn = None
        if len(valid) > 1:
            warn = "multiple first-name spellings: " + ", ".join(sorted(valid))
        derived[sn] = {'full': full, 'spellings': spellings, 'warn': warn}
    return derived


def report_bare_mentions(manuscript_dir: str, persons: Dict[str, Person]) -> int:
    if not EPONYM_PATTERNS:
        print("SKIPPED   eponym filter: terms.watch_words.people.eponyms is empty in "
              "book.yaml, so a surname inside a named law or test is listed too")
    derived = derive_full_names(manuscript_dir, persons)
    known_surnames = set(persons)
    surnames = sorted(persons, key=len, reverse=True)

    mentions: Dict[str, List[tuple]] = {sn: [] for sn in persons}
    unresolved: set = set()
    gword = 0
    gsent = 0
    for ch in CHAPTER_ORDER:
        path = Path(manuscript_dir, ch)
        if not Path(path).exists():
            continue
        lines = open(path, 'r', encoding='utf-8').read().split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('#') or is_inside_code_block(lines, i):
                continue
            for sn in surnames:
                if sn in AMBIGUOUS_SURNAMES:
                    continue
                info = derived.get(sn, {'full': None, 'spellings': set()})
                full, spellings = info['full'], info['spellings']
                if spellings:
                    fpat = re.compile('|'.join(
                        rf'\b{re.escape(sp)}\s+{re.escape(sn)}\b' for sp in spellings))
                    for m in fpat.finditer(line):
                        wp = gword + len(line[:m.start()].split())
                        sp = gsent + len(re.findall(r'[.!?]', line[:m.start()]))
                        mentions[sn].append((wp, sp, ch, i + 1, False, None, ''))
                epos = EPONYM_PATTERNS.get(sn, [])
                pat = re.compile(rf'(?<![`\w]){re.escape(sn)}(?![`\w])')
                for m in pat.finditer(line):
                    if is_citation_only(line, m.start(), m.end()):
                        continue
                    seg = line[max(0, m.start()-30):m.end()+30]
                    if any(re.search(e, seg) for e in epos):
                        continue
                    pm = re.search(r"([A-Za-z][A-Za-z.'-]*)\s*$", line[:m.start()])
                    if (pm.group(1) if pm else '') in spellings:
                        continue
                    nm = re.match(r"\s*([A-Za-z][A-Za-z-]*)", line[m.end():])
                    nextw = nm.group(1) if nm else ''
                    if nextw and nextw != sn and nextw in known_surnames:
                        continue
                    if full:
                        suggest = full
                    else:
                        suggest = f"{sn} (no full name in prose -- verify)"
                        unresolved.add(sn)
                    wp = gword + len(line[:m.start()].split())
                    sp = gsent + len(re.findall(r'[.!?]', line[:m.start()]))
                    a, b = max(0, m.start()-45), min(len(line), m.end()+45)
                    mentions[sn].append((wp, sp, ch, i + 1, True, suggest, line[a:b].strip()))
            gword += len(line.split())
            gsent += len(re.findall(r'[.!?]', line))

    def tier(gw, gs):
        if gw is None:
            return 'FIRST'
        if gw <= PRONOUN_WORD_MAX and gs <= PRONOUN_SENT_MAX:
            return 'PRONOUN'
        return 'EXPAND'

    rows: List[tuple] = []
    for sn in persons:
        seq = sorted(mentions[sn])
        for idx, (wp, sp, ch, ln, is_bare, suggest, snip) in enumerate(seq):
            if not is_bare:
                continue
            if idx == 0:
                gw = gs = None
            else:
                gw = wp - seq[idx - 1][0]
                gs = sp - seq[idx - 1][1]
            rows.append((CHAPTER_ORDER.index(ch), ch, ln, sn, suggest, gw, gs, tier(gw, gs), snip))

    rows.sort(key=lambda r: (r[0], r[2]))

    print(f"\n{BOLD}{'='*80}{NC}")
    print(f"{BOLD}BARE-SURNAME MENTIONS  (later-mention name review, Rule 2.7){NC}")
    print(f"{BOLD}{'='*80}{NC}")
    print("gap = prose-words / sentences since the previous mention (full name or surname).")
    print(f"tier: PRONOUN (<= {PRONOUN_WORD_MAX}w and <= {PRONOUN_SENT_MAX} sentence) | "
          f"EXPAND (farther -> use full name) | FIRST (first in book)\n")

    if not rows:
        print(f"{GREEN}No bare-surname person references found.{NC}\n")
        return 0

    tier_color = {'PRONOUN': CYAN, 'EXPAND': GREEN, 'FIRST': RED}
    per_person: Dict[str, int] = {}
    tier_counts: Dict[str, int] = {}
    cur_ch = None
    for _, ch, ln, sn, suggest, gw, gs, tr, snip in rows:
        if ch != cur_ch:
            cur_ch = ch
            print(f"\n{BOLD}{CYAN}{ch}{NC}")
        per_person[suggest] = per_person.get(suggest, 0) + 1
        tier_counts[tr] = tier_counts.get(tr, 0) + 1
        gap = "first in book" if gw is None else f"{gw}w/{gs}s"
        tc = tier_color.get(tr, NC)
        print(f"  L{ln:<4} [{tc}{tr}{NC}] gap {gap:<14} {YELLOW}{sn}{NC} -> {GREEN}{suggest}{NC}")
        print(f"        ...{snip}...")

    print(f"\n{BOLD}{RULE_LINE * 80}{NC}")
    print(f"{BOLD}TIER COUNTS{NC}  (suggested action)")
    print(f"{BOLD}{RULE_LINE * 80}{NC}")
    for tr in ['EXPAND', 'PRONOUN', 'FIRST']:
        if tr in tier_counts:
            print(f"  {tier_counts[tr]:>3}  {tr}")

    print(f"\n{BOLD}{RULE_LINE * 80}{NC}")
    print(f"{BOLD}PER-PERSON COUNTS{NC}")
    print(f"{BOLD}{RULE_LINE * 80}{NC}")
    for suggest, c in sorted(per_person.items(), key=lambda x: -x[1]):
        print(f"  {c:>3}  {suggest}")

    warns = [(sn, derived[sn]['warn']) for sn in derived if derived[sn].get('warn')]
    if warns:
        print(f"\n{BOLD}{YELLOW}FIRST-NAME SPELLING WARNINGS{NC}")
        for sn, w in warns:
            print(f"  {sn}: {w}")

    if unresolved:
        print(f"\n{BOLD}{YELLOW}UNRESOLVED (no full name found in prose -- may be org/false match){NC}")
        print(f"  {', '.join(sorted(unresolved))}")

    n_chapters = len({r[1] for r in rows})
    print(f"\n{BOLD}TOTAL bare-surname mentions: {len(rows)} across {n_chapters} chapters{NC}\n")
    return len(rows)


def apply_book_people(config):
    people = watch_words(config, 'people')
    KNOWN_ALIASES.clear()
    for reference_name, aliases in (people.get('aliases') or {}).items():
        KNOWN_ALIASES[str(reference_name)] = [str(alias) for alias in aliases or []]
    EPONYM_PATTERNS.clear()
    for surname, patterns in (people.get('eponyms') or {}).items():
        EPONYM_PATTERNS[str(surname)] = [str(p) for p in patterns or []]


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split('\n\n', 1)[1])
    parser.add_argument('manuscript_dir', nargs='?',
                        help='manuscript folder (default: manuscript.dir in the book config)')
    parser.add_argument('--verbose', '-v', action='store_true', help='show context')
    parser.add_argument('--bibliography', metavar='FILE',
                        help='the .bib file (default: sources.bibliography in the book config)')
    parser.add_argument('--bare-mentions', action='store_true',
                        help='list every bare-surname mention, for a voice that wants full names on later mentions')
    parser.add_argument('--self-test', action='store_true',
                        help='check this script against the fixture book and exit')
    add_config_arguments(parser)
    return parser.parse_args(argv)


def resolve_bibliography(options, config) -> Optional[str]:
    if options.bibliography:
        return options.bibliography
    configured = config.sources.bibliography
    return str(configured) if configured and configured.is_file() else None


def run(argv) -> int:
    options = parse_arguments(argv)
    if options.self_test:
        return self_test()
    try:
        config = config_for_targets(options, [options.manuscript_dir] if options.manuscript_dir
                                    else [])
    except ConfigError as error:
        return tool_failed(str(error), 'person-introduction-check')
    if not is_english_book(config):
        return skipped_for_language(config, "person-introduction-check")
    apply_book_people(config)
    manuscript_dir = options.manuscript_dir or str(config.manuscript.dir)
    if not Path(manuscript_dir).is_dir():
        return tool_failed(f'not a folder: {manuscript_dir}', 'person-introduction-check')
    CHAPTER_ORDER[:] = discover_chapter_order(manuscript_dir, config)
    if not CHAPTER_ORDER:
        return tool_failed(f'no prose .md files found in {manuscript_dir}',
                           'person-introduction-check')
    bibliography_path = resolve_bibliography(options, config)
    if not bibliography_path:
        print(f"SKIPPED   the book has no .bib file ({config.sources.bibliography}); "
              f"pass --bibliography FILE or set sources.bibliography in book.yaml")
        return 0
    if options.bare_mentions:
        persons = read_persons(bibliography_path)
        if not persons:
            return tool_failed('no persons found among the authors in the .bib file',
                               'person-introduction-check')
        return 1 if report_bare_mentions(manuscript_dir, persons) else 0
    issues = analyze(manuscript_dir, bibliography_path, options.verbose)
    return 1 if issues else 0


def self_test() -> int:
    failures = []
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exit_code = run(['--config', str(SAMPLE_BOOK / 'book.yaml')])
    text = output.getvalue()
    if exit_code != 1:
        failures.append(f'exit {exit_code}, expected 1')
    if 'BARE_SURNAME' not in text or 'Rivera' not in text:
        failures.append('the bare first mention of Rivera was not flagged')
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        run(['--config', str(SAMPLE_BOOK / 'book.yaml'), '--bare-mentions'])
    if 'Rivera' not in output.getvalue():
        failures.append('--bare-mentions did not list Rivera')
    for line in failures:
        print(f'FAIL  {line}')
    print(f"self-test: {'PASS' if not failures else str(len(failures)) + ' failure(s)'}")
    return 1 if failures else 0


def main():
    return run(sys.argv[1:])


if __name__ == '__main__':
    run_main(main)
