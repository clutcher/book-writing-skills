#!/usr/bin/env python3
"""Check sentence length, paragraph length and prose style against the book's voice profile.

With no path, every manuscript file of the book is checked. The numbers (sentence and paragraph
limits, the fronted-inversion floor) come from the voice profile: the book's `rules.voice` file,
else `profiles/default.md` in this skill (`profiles/paper-voice.md` for a paper);
`--set writing.<key>=VALUE` overrides one.

Modes:
    (default)       sentence and paragraph limits (rules 3.4, 3.6)
    --stats         compliance statistics
    --style         connectors and inversions per section (rules 4.2, 4.5)
    --connectors    connector misuse: tautological or characterization "because",
                    "while" across two different measures (rule 4.2 three-way test)
    --meta          meta-announcements that describe the text instead of arguing
    --inversions    fronted inversions as a running gap, plus proximity and variety (rule 4.5);
                    pass the whole manuscript, because a gap can cross a chapter boundary

The scan skips headings, code blocks (a paragraph boundary), tables, list items and bibliography
lines. Short questions and lead-ins ending in ":" may run short, and a paragraph that ends in
":" leads into a list, so it has no paragraph length. Quoted text is not counted.
Exit codes: 0 clean, 1 findings, 2 the check could not run.
"""

import argparse
import contextlib
import io
import re
import sys
from pathlib import Path
from typing import List, Tuple, NamedTuple

sys.dont_write_bytecode = True

from book_files import (ConfigError, FIXTURES_DIR, SAMPLE_BOOK, add_config_arguments,
                        coined_words, config_for_targets, is_english_book, markdown_files,
                        skipped_for_language, tool_failed)
from terminal_colors import CYAN, GREEN, NC, RED, YELLOW
from voice_profile import load_voice_profile


MIN_WORDS = 15
MAX_WORDS = 25
SOFT_MIN_WORDS = 9
SOFT_MAX_WORDS = 40
TARGET_COMPLIANCE = 0.90

MIN_SENTENCES = 5
MAX_SENTENCES = 8

CODE_BLOCK_MARKER = '\n\n<<<CODE_BLOCK>>>\n\n'

CITATION_START = r'\[[^\[\]\n]*@'

CITATION_GROUP = r'\[[^\[\]\n]*@[^\[\]\n]*\](?!\()'

DIV_FENCE = re.compile(r'^:{3,}(?:\s*\{[^}]*\}|\s*[\w-]+)?\s*$')

DEFAULT_PARAGRAPH_LENGTH_EXEMPT_PATTERNS = [
    r'^(\d+-)?part-[\w-]+\.md$',
    r'references?\.md$',
    r'bibliography\.md$',
    r'acknowledge?ments?\.md$',
]

PARAGRAPH_LENGTH_EXEMPT_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in DEFAULT_PARAGRAPH_LENGTH_EXEMPT_PATTERNS
]

EXEMPT_FILES = set()
LENGTH_FREE_PLACES = set()
LENGTH_ISSUE_TYPES = {'very_short', 'short', 'long', 'consecutive_short', 'para_short',
                      'para_long'}

VOICE_SETTING_NAMES = {
    'MIN_WORDS': 'sentence_min_words',
    'MAX_WORDS': 'sentence_max_words',
    'SOFT_MIN_WORDS': 'sentence_review_below',
    'SOFT_MAX_WORDS': 'sentence_review_above',
    'TARGET_COMPLIANCE': 'sentence_target_share',
    'MIN_SENTENCES': 'paragraph_min_sentences',
    'MAX_SENTENCES': 'paragraph_max_sentences',
    'INVERSION_GAP_LIMIT': 'inversion_gap_words',
    'INVERSION_MIN_PARAGRAPH_GAP': 'inversion_min_paragraph_gap',
    'MIN_INVERSIONS_PER_SECTION': 'inversions_per_section',
}


CONNECTORS_PRIMARY = [
    'which', 'because', 'so', 'where', 'therefore',
]

CONNECTORS_RELATIVE = [
    'which', 'that', 'who', 'whom', 'whose', 'where', 'when', 'while',
]

CONNECTORS_CAUSAL = [
    'because', 'since', 'as', 'so', 'therefore', 'thus', 'hence',
    'consequently', 'accordingly',
]

CONNECTORS_CONTRASTIVE = [
    'but', 'however', 'yet', 'although', 'though', 'whereas',
    'nevertheless', 'nonetheless', 'still', 'instead',
]

CONNECTORS_ADDITIVE = [
    'also', 'moreover', 'furthermore', 'additionally',
]

CONNECTORS_SEQUENTIAL = [
    'then', 'next', 'first', 'finally', 'meanwhile',
    'afterward', 'subsequently', 'later',
]

CONNECTORS_MULTI_WORD = {
    'due to': 'causal',
    'mainly due to': 'causal',
    'leads to': 'causal',
    'this means': 'causal',
    'for that reason': 'causal',
    'because of': 'causal',
    'which means': 'causal',
    'in the end': 'sequential',
}

ALL_CONNECTORS = list(set(
    CONNECTORS_PRIMARY +
    CONNECTORS_RELATIVE +
    CONNECTORS_CAUSAL +
    CONNECTORS_CONTRASTIVE +
    CONNECTORS_ADDITIVE +
    CONNECTORS_SEQUENTIAL
))


FRONTED_INVERSION_PATTERNS = [
    r'^(?:(?:So|And|Yet|Still|Then|Instead)\s+|[A-Z][^,.]{0,45},\s+)?From .{0,90}?(?:emerge[ds]?|came|comes?|arose|arises?|follows?|results?)\b',
    r'^(?:(?:So|And|Yet|Still|Then|Instead)\s+|[A-Z][^,.]{0,45},\s+)?Out of (?:(?:this|these|that|those|the|such|both|each|every)\s+)?\w.{0,90}?(?:emerge[sd]?|came|comes?|arose|arises?|follows?|results?)\b',
    r'^(?:(?:So|And|Yet|Still|Then|Instead)\s+|[A-Z][^,.]{0,45},\s+)?Into (?:(?:this|these|that|those|the|such|both|each|every)\s+)?\w.{0,70}?(?:stepped|came|comes?|entered|walked)\b',
    r'^(?:(?:So|And|Yet|Still|Then|Instead)\s+|[A-Z][^,.]{0,45},\s+)?Thus (?:emerge[sd]?|arose|came|began|begins?)\b',
]

OTHER_INVERSION_PATTERNS = [
    r'^(?:Behind|Beneath|Below|Beyond|Underneath|Above|Within|Inside|Around|Alongside|Across|Against|Beside|Between)\s+[^,]{0,70}?(?:lies?|lay|sits?|sat|stands?|stood|runs?|ran|waits?|remains?|rests?)\s+(?:a|an|the|no|one|two|three|another|every|each|its|his|her|their|our|this|these|that|those|only|what|whatever|something)\b',
    r'^Here (?:was|were|is|are|stands?|stood|lies?|lay)',
    r'^There (?:was|were|is|are|stands?|stood|lies?|lay|emerged?|came|arose)',
    r'^Only then (?:did|could|would|can|will)',
    r'^Not until .+? (?:did|could|would)',
    r'^Never before (?:had|have|has|did|could|would)',
    r'^Rarely (?:did|does|do|had|have|has)',
    r'^Seldom (?:did|does|do|had|have|has)',
    r'^So (?:great|strong|powerful|important|significant|profound).+?(?:was|were|is|are)',
    r'^Such (?:was|were|is|are)',
    r'^Had (?:it|he|she|they|we|the|this|that) (?:been|not)',
    r'^Were (?:it|he|she|they|we|the|this|that) to',
]

MIN_INVERSIONS_PER_SECTION = 1

INVERSION_GAP_LIMIT = 1000

INVERSION_MIN_PARAGRAPH_GAP = 3


CHARACTERIZATION_VERBS = [
    'is', 'are', 'means', 'implies', 'represents',
]

CHARACTERIZATION_BECAUSE_PATTERN = re.compile(
    r'\b(' + '|'.join(CHARACTERIZATION_VERBS) + r')\b[^.!?]{0,80}?\bbecause\b',
    re.IGNORECASE,
)

TAUTOLOGY_STOP_WORDS = {
    'because', 'there', 'their', 'these', 'those', 'where',
    'which', 'what', 'when', 'while', 'about', 'other', 'through',
    'without', 'every', 'after', 'before', 'during', 'until',
    'would', 'could', 'should', 'might', 'shall',
}

BECAUSE_CLAUSE_PATTERN = re.compile(
    r'([^.!?\n]{10,200}?)\bbecause\b([^.!?\n]{10,200})',
    re.IGNORECASE,
)

WHILE_PARALLEL_PATTERN = re.compile(
    r'([^.!?\n]{15,}?),\s+while\s+([^.!?\n]{15,})',
    re.IGNORECASE,
)

WHILE_EXCLUSION_PATTERN = re.compile(
    r'\bwhile\s+the\s+\w+\s+(runs|holds|waits|rests|cools|heats|sleeps)\b',
    re.IGNORECASE,
)

MEASURE_CATEGORIES = {
    'speed': {'fast', 'faster', 'slow', 'slower', 'speed', 'quick', 'quicker'},
    'size': {'small', 'smaller', 'large', 'larger', 'big', 'bigger', 'compact', 'heavy',
             'heavier'},
    'difficulty': {'simple', 'simpler', 'complex', 'complicated', 'easy', 'easier', 'hard',
                   'harder', 'difficult'},
    'accuracy': {'correct', 'accurate', 'accuracy', 'errors', 'mistakes', 'reliable',
                 'reliability', 'safe', 'safer'},
    'adoption': {'popular', 'adopted', 'users', 'adoption', 'widely', 'common'},
    'cost': {'cheap', 'cheaper', 'expensive', 'costly', 'cost', 'costs'},
    'book-term': set(),
}


META_PATTERNS = [
    (r'\b(The|This)\s+\w+\s+from\s+Chapter\s+\d+\s+(reveals|applies|shows|addresses|captures|demonstrates)\b',
     'chapter-reach-back'),
    (r'\b(As|Like)\s+(we|you)\s+(saw|read|noted|observed|discussed)\s+in\s+Chapter\s+\d+',
     'reader-address'),
    (r'\bBy\s+now\s+the\s+reader\b',
     'reader-state'),
    (r'\bHaving\s+(established|shown|demonstrated|explained|introduced)\s+[^,.!?]+,\s+(we|this\s+chapter|the\s+book)\b',
     'having-transition'),
    (r'\bThis\s+chapter\s+(?:will\s+\w+|shows?|explores?|describes?|covers?|discusses?)\s+how\b',
     'chapter-roadmap'),
    (r'\bAt\s+this\s+point\b',
     'filler-transition'),
    (r'\bAs\s+we(\'ll|\s+will)?\s+(see|discuss)\b',
     'forward-announce'),
    (r'\b(We|This\s+chapter)\s+(now|next)\s+turn[s]?\s+to\b',
     'procedural-turn'),
]



class Sentence(NamedTuple):
    text: str
    word_count: int
    line_num: int
    is_question: bool


class Issue(NamedTuple):
    line_num: int
    issue_type: str
    message: str
    sentences: List[Sentence]
    end_line: int = 0


class Paragraph(NamedTuple):
    text: str
    line_num: int
    sentence_count: int


class Section(NamedTuple):
    title: str
    level: int
    line_num: int
    content: str


class StyleIssue(NamedTuple):
    section: str
    issue_type: str
    message: str
    line_num: int


def extract_sections(content: str, target_level: int = 2) -> List[Section]:
    sections = []
    lines = content.split('\n')

    current_section = None
    current_content = []

    for line_num, line in enumerate(lines, 1):
        header_match = re.match(r'^(#{1,6})\s+(.+)$', line)

        if header_match:
            level = len(header_match.group(1))
            title = header_match.group(2).strip()

            if level == target_level:
                if current_section is not None:
                    sections.append(Section(
                        title=current_section['title'],
                        level=current_section['level'],
                        line_num=current_section['line_num'],
                        content='\n'.join(current_content)
                    ))

                current_section = {
                    'title': title,
                    'level': level,
                    'line_num': line_num,
                }
                current_content = []

            elif level < target_level and current_section is not None:
                sections.append(Section(
                    title=current_section['title'],
                    level=current_section['level'],
                    line_num=current_section['line_num'],
                    content='\n'.join(current_content)
                ))
                current_section = None
                current_content = []

            elif level > target_level and current_section is not None:
                current_content.append(line)

        elif current_section is not None:
            current_content.append(line)

    if current_section is not None:
        sections.append(Section(
            title=current_section['title'],
            level=current_section['level'],
            line_num=current_section['line_num'],
            content='\n'.join(current_content)
        ))

    return sections


def count_connectors(text: str) -> dict:
    text_lower = text.lower()
    words = re.findall(r'\b[a-z]+\b', text_lower)

    counts = {
        'primary': {},
        'relative': {},
        'causal': {},
        'contrastive': {},
        'additive': {},
        'sequential': {},
        'multi_word': {},
        'total': 0,
        'word_count': len(words),
    }

    for phrase, category in CONNECTORS_MULTI_WORD.items():
        pattern = r'\b' + phrase.replace(' ', r'\s+') + r'\b'
        matches = re.findall(pattern, text_lower)
        if matches:
            counts['multi_word'][phrase] = len(matches)

    for word in words:
        if word in CONNECTORS_PRIMARY:
            counts['primary'][word] = counts['primary'].get(word, 0) + 1
        if word in CONNECTORS_RELATIVE:
            counts['relative'][word] = counts['relative'].get(word, 0) + 1
        if word in CONNECTORS_CAUSAL:
            counts['causal'][word] = counts['causal'].get(word, 0) + 1
        if word in CONNECTORS_CONTRASTIVE:
            counts['contrastive'][word] = counts['contrastive'].get(word, 0) + 1
        if word in CONNECTORS_ADDITIVE:
            counts['additive'][word] = counts['additive'].get(word, 0) + 1
        if word in CONNECTORS_SEQUENTIAL:
            counts['sequential'][word] = counts['sequential'].get(word, 0) + 1

    counts['total'] = sum(sum(cat.values()) for cat in [
        counts['primary'], counts['causal'], counts['contrastive'],
        counts['additive'], counts['sequential']
    ])
    for word, count in counts['relative'].items():
        if word not in CONNECTORS_PRIMARY:
            counts['total'] += count
    counts['total'] += sum(counts['multi_word'].values())

    return counts


def get_connector_density(text: str) -> float:
    counts = count_connectors(text)
    if counts['word_count'] == 0:
        return 0.0
    return (counts['total'] / counts['word_count']) * 100


def find_fronted_inversions(text: str) -> List[Tuple[str, int]]:
    inversions = []

    sentences = re.split(r'(?<=[.!?])\s+', text)

    line_estimate = 1
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        for pattern in FRONTED_INVERSION_PATTERNS:
            if re.match(pattern, sentence, re.IGNORECASE):
                preview = sentence[:60] + '...' if len(sentence) > 60 else sentence
                inversions.append((preview, line_estimate))
                break

        line_estimate += max(1, len(sentence) // 80)

    return inversions


def _content_words(text: str) -> set:
    words = re.findall(r"\b[a-z]{5,}\b", text.lower())
    return {w for w in words if w not in TAUTOLOGY_STOP_WORDS}


def _measure_categories(text: str) -> set:
    tokens = set(re.findall(r"\b[a-z]+\b", text.lower()))
    cats = set()
    for cat, words in MEASURE_CATEGORIES.items():
        if tokens & words:
            cats.add(cat)
    return cats


def find_connector_issues(content: str, line_mapping: dict = None) -> List[dict]:
    issues = []
    lines = content.split('\n')
    in_code = False

    def map_line(n):
        if line_mapping is None:
            return n
        return line_mapping.get(n, n)

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('```'):
            in_code = not in_code
            continue
        if in_code:
            continue
        if stripped.startswith('|') or stripped.startswith('#'):
            continue
        if is_reference_line(line):
            continue

        for m in CHARACTERIZATION_BECAUSE_PATTERN.finditer(line):
            snippet = _extract_sentence_around(line, m.start())
            issues.append({
                'line': map_line(line_num),
                'kind': 'characterization-because',
                'snippet': snippet,
                'hint': 'Left clause characterizes with "{0}"; ask: causation, characterization, or association?'.format(
                    m.group(1).lower()
                ),
            })

        for m in BECAUSE_CLAUSE_PATTERN.finditer(line):
            left = m.group(1)
            right = m.group(2)
            overlap = _content_words(left) & _content_words(right)
            if len(overlap) >= 2:
                snippet = _extract_sentence_around(line, m.start())
                issues.append({
                    'line': map_line(line_num),
                    'kind': 'tautology-because',
                    'snippet': snippet,
                    'hint': 'Shared content words across "because": {0}. Does the right side explain or restate?'.format(
                        ', '.join(sorted(overlap))
                    ),
                })

        if WHILE_EXCLUSION_PATTERN.search(line):
            continue
        for m in WHILE_PARALLEL_PATTERN.finditer(line):
            left_cats = _measure_categories(m.group(1))
            right_cats = _measure_categories(m.group(2))
            if left_cats and right_cats and not (left_cats & right_cats):
                snippet = _extract_sentence_around(line, m.start())
                issues.append({
                    'line': map_line(line_num),
                    'kind': 'parallel-while',
                    'snippet': snippet,
                    'hint': 'Left measures {0}, right measures {1}. Different dimensions: is this causation or association misrepresented as contrast?'.format(
                        ','.join(sorted(left_cats)), ','.join(sorted(right_cats))
                    ),
                })

    return issues


def _extract_sentence_around(line: str, offset: int, max_len: int = 160) -> str:
    left = line[:offset]
    right = line[offset:]
    left_break = max(left.rfind('. '), left.rfind('! '), left.rfind('? '))
    if left_break >= 0:
        left = left[left_break + 2:]
    right_break = re.search(r'[.!?](?=\s|$)', right)
    if right_break:
        right = right[: right_break.end()]
    snippet = (left + right).strip()
    if len(snippet) > max_len:
        snippet = snippet[: max_len - 1] + '...'
    return snippet


def find_meta_announcements(content: str, line_mapping: dict = None) -> List[dict]:
    issues = []
    lines = content.split('\n')
    in_code = False

    def map_line(n):
        if line_mapping is None:
            return n
        return line_mapping.get(n, n)

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('```'):
            in_code = not in_code
            continue
        if in_code:
            continue
        if stripped.startswith('|') or stripped.startswith('#'):
            continue
        if is_reference_line(line):
            continue

        for pattern, label in META_PATTERNS:
            for m in re.finditer(pattern, line, re.IGNORECASE):
                snippet = _extract_sentence_around(line, m.start())
                issues.append({
                    'line': map_line(line_num),
                    'kind': label,
                    'match': m.group(0),
                    'snippet': snippet,
                })

    return issues


def _is_reference_file(raw: str) -> bool:
    body = [l.strip() for l in raw.split('\n') if l.strip() and not l.strip().startswith('#')]
    if not body:
        return False
    return sum(1 for l in body if is_reference_line(l)) > len(body) / 2


def scan_inversions(paths: List[str]) -> Tuple[List[dict], int]:
    rows = []
    running = 0
    per_file = {}

    for path in paths:
        raw = open(path, encoding='utf-8').read()
        if _is_reference_file(raw):
            continue
        content, line_map = replace_code_blocks(raw)
        base = Path(path).name
        per_file.setdefault(base, [0, 0])
        section = '(chapter opening)'
        para_idx = 0

        for proc_line, line in enumerate(content.split('\n'), 1):
            lineno = line_map.get(proc_line, proc_line)
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith('## '):
                section = stripped[3:].strip()
                continue
            if (is_header(stripped) or is_table_row(stripped) or is_list_item(stripped)
                    or is_blockquote(stripped) or is_code_block_marker(stripped)
                    or stripped == CODE_BLOCK_MARKER or is_html_spacer(stripped)):
                continue

            para_idx += 1
            text = remove_inline_code(stripped)

            for sentence, _ in split_into_sentences(text):
                sentence = sentence.strip()
                if not sentence:
                    continue
                words = len(sentence.split())
                for pattern in FRONTED_INVERSION_PATTERNS:
                    if re.match(pattern, sentence, re.IGNORECASE):
                        opener = ' '.join(sentence.split()[:9])
                        rows.append(dict(file=base, line=lineno, section=section,
                                         para=para_idx, offset=running,
                                         sentence=sentence, opener=opener))
                        break
                running += words
                per_file[base][1] += words

    for r in rows:
        per_file[r['file']][0] += 1

    return rows, running, per_file


def _inversion_signature(sentence: str) -> Tuple[str, str]:
    lead = re.match(r'^(Out of|From|Into|Here|There|Only then|Not until|Never before|'
                    r'Rarely|Seldom|So|Such|Thus|Had|Were)', sentence, re.IGNORECASE)
    verb = re.search(r'\b(emerges|emerge|emerged|comes|come|came|arises|arise|arose|'
                     r'stepped|steps|entered|walked|grew|grows|follows|follow|results|'
                     r'result|stood|stands|lies|lay|began|begins|ended|was|were|is|are)\b',
                     sentence, re.IGNORECASE)
    return (lead.group(1).lower() if lead else '?',
            verb.group(1).lower() if verb else '?')


def print_inversion_analysis(paths: List[str]) -> int:
    rows, total_words, per_file = scan_inversions(paths)
    flags = 0

    print(f"\n{CYAN}Fronted Inversions (rule 4.5){NC}")
    print(f"  Files: {len(paths)}   prose words: {total_words}   inversions: {len(rows)}")
    floor_per_thousand = 1000 / INVERSION_GAP_LIMIT if INVERSION_GAP_LIMIT else 0
    if rows and total_words:
        floor_text = (f"floor: {floor_per_thousand:.2f}, one per {INVERSION_GAP_LIMIT} words"
                      if INVERSION_GAP_LIMIT else "no floor in this voice profile")
        print(f"  Density: {len(rows) / total_words * 1000:.2f} per 1,000 words"
              f"   ({floor_text})")

    print(f"\n{CYAN}  Per file:{NC}")
    for base, (count, words) in per_file.items():
        if words < 200:
            continue
        density = count / words * 1000
        colour = GREEN if density >= floor_per_thousand else YELLOW
        print(f"    {base:<24} {count:>3} inv  {words:>6}w  {colour}{density:>5.2f}/1k{NC}")

    print(f"\n{CYAN}  Deserts over {INVERSION_GAP_LIMIT} words (floor violations):{NC}")
    prev_off, prev_label = 0, 'START OF TEXT'
    deserts = []
    for r in rows + [dict(offset=total_words, file='END', section='', line=0)]:
        gap = r['offset'] - prev_off
        if INVERSION_GAP_LIMIT and gap > INVERSION_GAP_LIMIT:
            deserts.append((gap, prev_label, f"{r['file']}:{r['line']} [{r['section']}]"))
        prev_off = r['offset']
        prev_label = f"{r['file']}:{r['line']} [{r['section']}]"
    for gap, after, before in sorted(deserts, key=lambda d: -d[0]):
        print(f"    {YELLOW}{gap:>5}w{NC}  after {after}")
        print(f"            up to {before}")
    flags += len(deserts)
    if not deserts:
        print(f"    {GREEN}none{NC}")

    print(f"\n{CYAN}  Proximity (two within {INVERSION_MIN_PARAGRAPH_GAP} paragraphs):{NC}")
    close = 0
    for a, b in zip(rows, rows[1:]):
        if (a['file'] == b['file'] and a['section'] == b['section']
                and b['para'] - a['para'] <= INVERSION_MIN_PARAGRAPH_GAP):
            close += 1
            print(f"    {YELLOW}{a['file']}:{a['line']} -> :{b['line']}{NC} "
                  f"({b['para'] - a['para']} paragraphs apart) [{a['section']}]")
            print(f"        {a['opener']}...")
            print(f"        {b['opener']}...")
    flags += close
    if not close:
        print(f"    {GREEN}none{NC}")

    print(f"\n{CYAN}  Variety (same preposition and verb repeated in one section):{NC}")
    seen = {}
    repeats = 0
    for r in rows:
        key = (r['file'], r['section'], _inversion_signature(r['sentence']))
        seen.setdefault(key, []).append(r)
    for key, group in seen.items():
        if len(group) > 1:
            repeats += 1
            lead, verb = key[2]
            print(f"    {YELLOW}{key[0]} [{key[1]}]{NC} '{lead} ... {verb}' x{len(group)}"
                  f" at lines {', '.join(str(g['line']) for g in group)}")
    flags += repeats
    if not repeats:
        print(f"    {GREEN}none{NC}")

    if rows:
        print(f"\n{CYAN}  Lexical profile (watch for monoculture):{NC}")
        leads, verbs = {}, {}
        demonstrative = 0
        for r in rows:
            lead, verb = _inversion_signature(r['sentence'])
            leads[lead] = leads.get(lead, 0) + 1
            verbs[verb] = verbs.get(verb, 0) + 1
            if re.match(r'^\w+(\s+of)?\s+(this|these|that|those)\b', r['sentence'], re.IGNORECASE):
                demonstrative += 1
        print("    Openers: " + ', '.join(f"{k}:{v}" for k, v in
                                          sorted(leads.items(), key=lambda x: -x[1])))
        print("    Verbs:   " + ', '.join(f"{k}:{v}" for k, v in
                                          sorted(verbs.items(), key=lambda x: -x[1])))
        print(f"    Demonstrative head (this/these): {demonstrative} of {len(rows)}")

    print(f"\n{CYAN}  All sites:{NC}")
    for r in rows:
        print(f"    {r['file'][:3]}:{r['line']:<5} [{r['section'][:32]:32}] {r['opener']}...")

    return flags


def print_connector_analysis(filepath: str):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    content_with_markers, line_mapping = replace_code_blocks(content)
    issues = find_connector_issues(content_with_markers, line_mapping)

    if not issues:
        print(f"{GREEN}OK{NC} {filepath} (no connector misuse candidates)")
        return 0

    print(f"{YELLOW}CONNECTORS{NC} {filepath}")
    by_kind = {}
    for i in issues:
        by_kind[i['kind']] = by_kind.get(i['kind'], 0) + 1
    summary = ', '.join(f"{k}:{v}" for k, v in sorted(by_kind.items(), key=lambda x: -x[1]))
    print(f"  {summary}")
    print()
    for issue in issues:
        print(f"  {CYAN}{filepath}:{issue['line']}{NC} [{issue['kind']}]")
        print(f"    \"{issue['snippet']}\"")
        print(f"    hint: {issue['hint']}")
        print()
    return len(issues)


def print_meta_analysis(filepath: str):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    content_with_markers, line_mapping = replace_code_blocks(content)
    issues = find_meta_announcements(content_with_markers, line_mapping)

    if not issues:
        print(f"{GREEN}OK{NC} {filepath} (no meta-announcement fluff)")
        return 0

    print(f"{YELLOW}META{NC} {filepath}")
    by_kind = {}
    for i in issues:
        by_kind[i['kind']] = by_kind.get(i['kind'], 0) + 1
    summary = ', '.join(f"{k}:{v}" for k, v in sorted(by_kind.items(), key=lambda x: -x[1]))
    print(f"  {summary}")
    print()
    for issue in issues:
        print(f"  {CYAN}{filepath}:{issue['line']}{NC} [{issue['kind']}] \"{issue['match']}\"")
        print(f"    \"{issue['snippet']}\"")
        print()
    return len(issues)


def analyze_style_features(filepath: str) -> dict:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    sections = extract_sections(content)
    results = {
        'sections': [],
        'issues': [],
        'totals': {
            'connectors': count_connectors(content),
            'inversions': find_fronted_inversions(content),
        }
    }

    for section in sections:
        section_data = {
            'title': section.title,
            'line_num': section.line_num,
            'connectors': count_connectors(section.content),
            'inversions': find_fronted_inversions(section.content),
            'density': get_connector_density(section.content),
        }
        results['sections'].append(section_data)

        if MIN_INVERSIONS_PER_SECTION and len(section_data['inversions']) < MIN_INVERSIONS_PER_SECTION:
            results['issues'].append(StyleIssue(
                section=section.title,
                issue_type='missing_inversion',
                message=f"Section has {len(section_data['inversions'])} fronted inversions (min {MIN_INVERSIONS_PER_SECTION})",
                line_num=section.line_num
            ))

    return results


def replace_code_blocks(content: str) -> Tuple[str, dict]:
    lines = content.split('\n')
    result_lines = []
    line_mapping = {}
    in_code_block = False
    original_line = 0
    processed_line = 0

    for original_line, line in enumerate(lines, 1):
        if line.strip().startswith('```'):
            if not in_code_block:
                in_code_block = True
                processed_line += 1
                result_lines.append('<<<CODE_BLOCK>>>')
                line_mapping[processed_line] = original_line
            else:
                in_code_block = False
        elif not in_code_block:
            processed_line += 1
            result_lines.append(line)
            line_mapping[processed_line] = original_line

    return '\n'.join(result_lines), line_mapping


def remove_inline_code(text: str) -> str:
    return re.sub(r'`[^`]+`', 'CODE', text)


def is_header(line: str) -> bool:
    return line.strip().startswith('#')


def is_table_row(line: str) -> bool:
    stripped = line.strip()
    return '|' in stripped and (stripped.startswith('|') or stripped.endswith('|'))


def is_list_item(line: str) -> bool:
    stripped = line.strip()
    return (stripped.startswith('- ') or stripped.startswith('* ')
            or stripped.startswith('-- ') or re.match(r'^\d+\.\s', stripped))


def is_reference_line(line: str) -> bool:
    return bool(DIV_FENCE.match(line.strip()))


def is_blockquote(line: str) -> bool:
    return line.strip().startswith('>')


def is_code_block_marker(line: str) -> bool:
    return '<<<CODE_BLOCK>>>' in line


def is_html_spacer(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return bool(re.match(r'^(?:&[a-zA-Z]+;|&#\d+;|<br\s*/?>)+$', stripped))


def extract_paragraphs(content: str, line_mapping: dict = None) -> List[Tuple[str, int, int, bool]]:
    paragraphs = []
    lines = content.split('\n')

    current_paragraph = []
    current_start_line = 1
    current_end_line = 1
    is_in_blockquote = False

    def map_line(processed_line: int) -> int:
        if line_mapping is None:
            return processed_line
        return line_mapping.get(processed_line, processed_line)

    def flush():
        nonlocal current_paragraph, is_in_blockquote
        if current_paragraph:
            paragraphs.append((' '.join(current_paragraph), current_start_line,
                               current_end_line, not is_in_blockquote))
            current_paragraph = []
            is_in_blockquote = False

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()

        if is_header(line):
            flush()
            continue

        if is_table_row(line):
            continue

        if is_list_item(line):
            continue

        if is_reference_line(line):
            continue

        if is_html_spacer(line):
            continue

        if is_blockquote(line):
            if current_paragraph and not is_in_blockquote:
                flush()

            blockquote_text = stripped.lstrip('>').strip()
            if blockquote_text:
                if not current_paragraph:
                    current_start_line = map_line(line_num)
                    is_in_blockquote = True
                current_end_line = map_line(line_num)
                current_paragraph.append(blockquote_text)
            continue

        if is_code_block_marker(line):
            flush()
            continue

        if not stripped:
            flush()
            continue

        if is_in_blockquote:
            flush()

        if not current_paragraph:
            current_start_line = map_line(line_num)
        current_end_line = map_line(line_num)
        current_paragraph.append(stripped)

    flush()

    return paragraphs


def split_paragraph_into_sentences(paragraph: str, start_line: int) -> List[Tuple[str, int]]:
    sentences = []
    line_estimate = start_line

    quote_placeholders = []
    echoed_punct = []

    def save_quote(match):
        quote_text = match.group(0)
        quote_placeholders.append(quote_text)
        trailing_punct = ''
        if len(quote_text) >= 3:
            char_before_close = quote_text[-2]
            if char_before_close in '.!?':
                trailing_punct = char_before_close
        echoed_punct.append(trailing_punct)
        return f'XQUOTE{len(quote_placeholders) - 1}X{trailing_punct}'

    temp_para = re.sub(r'"[^"]*"', save_quote, paragraph)
    temp_para = re.sub(r'"[^"]*"', save_quote, temp_para)
    temp_para = re.sub(r"(?<!\w)'[^']{2,}'", save_quote, temp_para)
    temp_para = re.sub(r"(?<!\w)'[^']*'", save_quote, temp_para)

    sentence_pattern = rf'(?<=[.!?])\s+(?!{CITATION_START})(?=[A-Z\[""\'\'\`\*_])'
    raw_sentences = re.split(sentence_pattern, temp_para)

    for s in raw_sentences:
        s = s.strip()
        if s:
            for i in range(len(quote_placeholders) - 1, -1, -1):
                quote = quote_placeholders[i]
                pattern = re.escape(f'XQUOTE{i}X' + echoed_punct[i])
                s = re.sub(pattern, lambda _m, q=quote: q, s)

            sentences.append((s, line_estimate))
            line_estimate += max(1, len(s) // 80)

    return sentences


def split_into_sentences(content: str) -> List[Tuple[str, int]]:
    content, line_mapping = replace_code_blocks(content)

    paragraphs = extract_paragraphs(content, line_mapping)

    all_sentences = []
    for para_text, para_line, _, _ in paragraphs:
        sentences = split_paragraph_into_sentences(para_text, para_line)
        all_sentences.extend(sentences)

    return all_sentences


def is_entirely_quote(sentence: str) -> bool:
    stripped = sentence.strip()
    stripped = re.sub(rf'\s*{CITATION_GROUP}[.!?]?\s*$', '', stripped)
    stripped = stripped.strip()

    quote_pairs = [
        ('"', '"'),
        ('"', '"'),
    ]

    for open_q, close_q in quote_pairs:
        if stripped.startswith(open_q) and stripped.endswith(close_q):
            inner = stripped[1:-1]

            inner_open = inner.count(open_q)
            inner_close = inner.count(close_q)

            if inner_open == 0 and inner_close == 0:
                return True
            if inner_open == inner_close:
                temp = inner
                for oq, cq in quote_pairs:
                    temp = re.sub(f'{re.escape(oq)}[^{re.escape(cq)}]*{re.escape(cq)}', '', temp)
                if re.match(r'^[\s.,;:!?-]*$', temp):
                    return True

    return False


def count_words(sentence: str) -> int:
    cleaned = remove_inline_code(sentence)
    cleaned = re.sub(rf'{CITATION_GROUP}[.!?]?', '', cleaned)
    cleaned = re.sub(r'["""\'\']', '', cleaned)
    words = [w for w in cleaned.split() if re.search(r'[a-zA-Z0-9]', w)]
    return len(words)


def is_question(sentence: str) -> bool:
    return sentence.rstrip().endswith('?')


def is_short_acceptable(sentence: str, word_count: int) -> bool:
    if is_question(sentence):
        return True

    if sentence.rstrip().endswith(':'):
        return True

    if re.match(r'^At (the |a )?(high|low|higher|lower|even lower)', sentence, re.IGNORECASE):
        return True

    return False


def is_lead_in(paragraph: str) -> bool:
    return paragraph.rstrip().endswith(':')


def is_paragraph_length_exempt(filepath: str) -> bool:
    if EXEMPT_FILES and Path(filepath).resolve() in EXEMPT_FILES:
        return True
    basename = Path(filepath).name
    return any(p.search(basename) for p in PARAGRAPH_LENGTH_EXEMPT_PATTERNS)


def is_thinking_file(filepath: str) -> bool:
    path = Path(filepath).resolve()
    return any(path == place or place in path.parents for place in LENGTH_FREE_PLACES)


def analyze_file(filepath: str) -> Tuple[List[Issue], List[Paragraph]]:
    issues = []
    check_paragraph_length = not is_paragraph_length_exempt(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    content_with_markers, line_mapping = replace_code_blocks(content)

    raw_paragraphs = extract_paragraphs(content_with_markers, line_mapping)

    paragraphs = []
    all_sentences = []

    for para_text, para_line, para_end_line, is_prose in raw_paragraphs:
        para_sentences = split_paragraph_into_sentences(para_text, para_line)
        sentence_count = len(para_sentences)

        is_countable = is_prose and not is_lead_in(para_text)

        paragraphs.append(Paragraph(
            text=para_text,
            line_num=para_line,
            sentence_count=sentence_count
        ))

        if is_countable and check_paragraph_length:
            if sentence_count < MIN_SENTENCES:
                issues.append(Issue(
                    line_num=para_line,
                    issue_type='para_short',
                    message=f'Paragraph too short ({sentence_count} sentences, min {MIN_SENTENCES})',
                    sentences=[],
                    end_line=para_end_line
                ))
            elif sentence_count > MAX_SENTENCES:
                issues.append(Issue(
                    line_num=para_line,
                    issue_type='para_long',
                    message=f'Paragraph too long ({sentence_count} sentences, max {MAX_SENTENCES})',
                    sentences=[],
                    end_line=para_end_line
                ))

        if is_prose:
            for text, line_num in para_sentences:
                word_count = count_words(text)
                all_sentences.append(Sentence(
                    text=text,
                    word_count=word_count,
                    line_num=line_num,
                    is_question=is_question(text)
                ))

    consecutive_short = []

    for sent in all_sentences:
        if is_entirely_quote(sent.text):
            if len(consecutive_short) >= 2:
                issues.append(Issue(
                    line_num=consecutive_short[0].line_num,
                    issue_type='consecutive_short',
                    message=f'{len(consecutive_short)} consecutive short sentences could be combined',
                    sentences=consecutive_short.copy()
                ))
            consecutive_short = []
            continue

        if sent.word_count < SOFT_MIN_WORDS:
            if not is_short_acceptable(sent.text, sent.word_count):
                issues.append(Issue(
                    line_num=sent.line_num,
                    issue_type='very_short',
                    message=f'Sentence below soft min ({sent.word_count} words, review needed)',
                    sentences=[sent]
                ))
                consecutive_short.append(sent)
            else:
                if len(consecutive_short) >= 2:
                    issues.append(Issue(
                        line_num=consecutive_short[0].line_num,
                        issue_type='consecutive_short',
                        message=f'{len(consecutive_short)} consecutive short sentences could be combined',
                        sentences=consecutive_short.copy()
                    ))
                consecutive_short = []
        elif sent.word_count < MIN_WORDS:
            if not is_short_acceptable(sent.text, sent.word_count):
                consecutive_short.append(sent)
                issues.append(Issue(
                    line_num=sent.line_num,
                    issue_type='short',
                    message=f'Sentence too short ({sent.word_count} words, min {MIN_WORDS})',
                    sentences=[sent]
                ))
            else:
                if len(consecutive_short) >= 2:
                    issues.append(Issue(
                        line_num=consecutive_short[0].line_num,
                        issue_type='consecutive_short',
                        message=f'{len(consecutive_short)} consecutive short sentences could be combined',
                        sentences=consecutive_short.copy()
                    ))
                consecutive_short = []
        elif sent.word_count > SOFT_MAX_WORDS:
            issues.append(Issue(
                line_num=sent.line_num,
                issue_type='long',
                message=f'Sentence exceeds soft max ({sent.word_count} words, review needed)',
                sentences=[sent]
            ))
            if len(consecutive_short) >= 2:
                issues.append(Issue(
                    line_num=consecutive_short[0].line_num,
                    issue_type='consecutive_short',
                    message=f'{len(consecutive_short)} consecutive short sentences could be combined',
                    sentences=consecutive_short.copy()
                ))
            consecutive_short = []
        else:
            if len(consecutive_short) >= 2:
                issues.append(Issue(
                    line_num=consecutive_short[0].line_num,
                    issue_type='consecutive_short',
                    message=f'{len(consecutive_short)} consecutive short sentences could be combined',
                    sentences=consecutive_short.copy()
                ))
            consecutive_short = []

    if len(consecutive_short) >= 2:
        issues.append(Issue(
            line_num=consecutive_short[0].line_num,
            issue_type='consecutive_short',
            message=f'{len(consecutive_short)} consecutive short sentences could be combined',
            sentences=consecutive_short.copy()
        ))

    if is_thinking_file(filepath):
        issues = [issue for issue in issues if issue.issue_type not in LENGTH_ISSUE_TYPES]
    return issues, paragraphs


def print_issues(filepath: str, issues: List[Issue], verbose: bool = False):
    exempt = is_paragraph_length_exempt(filepath)
    skip_note = f"  {CYAN}(paragraph-length check skipped: supporting matter){NC}"

    if not issues:
        print(f"{GREEN}OK{NC} {filepath}")
        if exempt:
            print(skip_note)
        return

    short_count = sum(1 for i in issues if i.issue_type == 'short')
    very_short_count = sum(1 for i in issues if i.issue_type == 'very_short')
    long_count = sum(1 for i in issues if i.issue_type == 'long')
    consecutive_count = sum(1 for i in issues if i.issue_type == 'consecutive_short')

    para_short_count = sum(1 for i in issues if i.issue_type == 'para_short')
    para_long_count = sum(1 for i in issues if i.issue_type == 'para_long')

    print(f"{YELLOW}ISSUES{NC} {filepath}")
    print(f"  Sentences: short (<{MIN_WORDS}): {YELLOW}{short_count}{NC}, "
          f"very short (<{SOFT_MIN_WORDS}): {YELLOW}{very_short_count}{NC}, "
          f"very long (>{SOFT_MAX_WORDS}): {YELLOW}{long_count}{NC}")
    if exempt:
        print(skip_note)
    else:
        print(f"  Paragraphs: short (<{MIN_SENTENCES}): {YELLOW}{para_short_count}{NC}, "
              f"long (>{MAX_SENTENCES}): {YELLOW}{para_long_count}{NC}")

    if verbose:
        print()
        for issue in issues:
            if issue.issue_type in ('para_short', 'para_long'):
                span = (f"line {issue.line_num}" if issue.end_line <= issue.line_num
                        else f"lines {issue.line_num}-{issue.end_line}")
            if issue.issue_type == 'para_short':
                print(f"  {YELLOW}[para short]{NC} {span}: {issue.message}")
            elif issue.issue_type == 'para_long':
                print(f"  {RED}[para long]{NC} {span}: {issue.message}")
            elif issue.issue_type == 'consecutive_short':
                print(f"  {CYAN}[consecutive]{NC} {issue.message}")
                for sent in issue.sentences:
                    preview = sent.text[:70] + '...' if len(sent.text) > 70 else sent.text
                    print(f"    [{sent.word_count}] {preview}")
            elif issue.issue_type == 'short':
                sent = issue.sentences[0]
                preview = sent.text[:70] + '...' if len(sent.text) > 70 else sent.text
                print(f"  {YELLOW}[short:{sent.word_count}]{NC} {preview}")
            elif issue.issue_type == 'very_short':
                sent = issue.sentences[0]
                preview = sent.text[:70] + '...' if len(sent.text) > 70 else sent.text
                print(f"  {YELLOW}[very short:{sent.word_count}]{NC} {preview}")
            elif issue.issue_type == 'long':
                sent = issue.sentences[0]
                preview = sent.text[:70] + '...' if len(sent.text) > 70 else sent.text
                print(f"  {RED}[long:{sent.word_count}]{NC} {preview}")
        print()


def get_statistics(filepath: str) -> dict:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    content_with_markers, line_mapping = replace_code_blocks(content)

    raw_paragraphs = extract_paragraphs(content_with_markers, line_mapping)

    if not raw_paragraphs:
        return {'sentences': {'total': 0}, 'paragraphs': {'total': 0}}

    sentence_data = []
    prose_sentence_counts = []

    for para_text, para_line, _, is_prose in raw_paragraphs:
        para_sentences = split_paragraph_into_sentences(para_text, para_line)
        sentence_count = len(para_sentences)

        if is_prose:
            for text, _ in para_sentences:
                sentence_data.append((count_words(text), text))
            prose_sentence_counts.append(sentence_count)

    word_counts = [wc for wc, _ in sentence_data]

    exceptions_count = 0
    for wc, text in sentence_data:
        if wc < MIN_WORDS and is_short_acceptable(text, wc):
            exceptions_count += 1

    in_range_count = sum(1 for wc, text in sentence_data
                         if MIN_WORDS <= wc <= MAX_WORDS or
                         (wc < MIN_WORDS and is_short_acceptable(text, wc)))

    under_count = sum(1 for wc, text in sentence_data
                      if wc < MIN_WORDS and not is_short_acceptable(text, wc))

    return {
        'sentences': {
            'total': len(word_counts),
            'min': min(word_counts) if word_counts else 0,
            'max': max(word_counts) if word_counts else 0,
            'avg': sum(word_counts) / len(word_counts) if word_counts else 0,
            'in_range': in_range_count,
            'under': under_count,
            'over': sum(1 for c in word_counts if c > MAX_WORDS),
            'below_soft_min': sum(1 for c in word_counts if c < SOFT_MIN_WORDS),
            'exceeds_soft_max': sum(1 for c in word_counts if c > SOFT_MAX_WORDS),
            'exceptions': exceptions_count,
        },
        'paragraphs': {
            'total': len(prose_sentence_counts),
            'min': min(prose_sentence_counts) if prose_sentence_counts else 0,
            'max': max(prose_sentence_counts) if prose_sentence_counts else 0,
            'avg': sum(prose_sentence_counts) / len(prose_sentence_counts) if prose_sentence_counts else 0,
            'in_range': sum(1 for c in prose_sentence_counts if MIN_SENTENCES <= c <= MAX_SENTENCES),
            'under': sum(1 for c in prose_sentence_counts if c < MIN_SENTENCES),
            'over': sum(1 for c in prose_sentence_counts if c > MAX_SENTENCES),
        },
    }


def process_file(filepath: str, verbose: bool = False) -> int:
    issues, _ = analyze_file(filepath)
    print_issues(filepath, issues, verbose)
    return len(issues)


def process_directory(dirpath: str, verbose: bool = False) -> Tuple[int, int]:
    total_issues = 0
    files_count = 0

    for path in sorted(Path(dirpath).rglob('*.md')):
        if 'node_modules' in str(path):
            continue
        files_count += 1
        total_issues += process_file(str(path), verbose)

    return files_count, total_issues


def print_summary(filepath: str):
    stats = get_statistics(filepath)

    sent = stats['sentences']
    para = stats['paragraphs']

    if sent['total'] == 0:
        print(f"No sentences found in {filepath}")
        return

    print(f"\n{CYAN}Statistics for {filepath}:{NC}")

    compliance = sent['in_range'] / sent['total'] if sent['total'] > 0 else 0
    compliance_color = GREEN if compliance >= TARGET_COMPLIANCE else YELLOW

    print(f"\n  {CYAN}Sentences (target {MIN_WORDS}-{MAX_WORDS} words, {TARGET_COMPLIANCE*100:.0f}% compliance):{NC}")
    print(f"    Total: {sent['total']}")
    print(f"    Range: {sent['min']} - {sent['max']} words")
    print(f"    Average: {sent['avg']:.1f} words")
    print(f"    In target range: {compliance_color}{sent['in_range']}{NC} "
          f"({compliance_color}{100*compliance:.1f}%{NC})")
    if sent.get('exceptions', 0) > 0:
        print(f"      (includes {sent['exceptions']} short questions/intros, allowed exceptions)")
    print(f"    Under {MIN_WORDS}: {sent['under']} "
          f"({100*sent['under']/sent['total']:.1f}%)")
    print(f"    Over {MAX_WORDS}: {sent['over']} "
          f"({100*sent['over']/sent['total']:.1f}%)")
    if sent['below_soft_min'] > 0:
        print(f"    Below {SOFT_MIN_WORDS} (review): {YELLOW}{sent['below_soft_min']}{NC} "
              f"({100*sent['below_soft_min']/sent['total']:.1f}%)")
    if sent['exceeds_soft_max'] > 0:
        print(f"    Exceeds {SOFT_MAX_WORDS} (review): {YELLOW}{sent['exceeds_soft_max']}{NC} "
              f"({100*sent['exceeds_soft_max']/sent['total']:.1f}%)")

    if para['total'] > 0:
        print(f"\n  {CYAN}Paragraphs (sentences per paragraph, target {MIN_SENTENCES}-{MAX_SENTENCES}):{NC}")
        print(f"    Total: {para['total']}")
        print(f"    Range: {para['min']} - {para['max']} sentences")
        print(f"    Average: {para['avg']:.1f} sentences")
        print(f"    In range: {GREEN}{para['in_range']}{NC} "
              f"({100*para['in_range']/para['total']:.1f}%)")
        print(f"    Under {MIN_SENTENCES}: {YELLOW}{para['under']}{NC} "
              f"({100*para['under']/para['total']:.1f}%)")
        print(f"    Over {MAX_SENTENCES}: {YELLOW}{para['over']}{NC} "
              f"({100*para['over']/para['total']:.1f}%)")


def print_style_analysis(filepath: str):
    results = analyze_style_features(filepath)

    print(f"\n{CYAN}Style Analysis for {filepath}:{NC}")

    conn = results['totals']['connectors']
    print(f"\n  {CYAN}Connectors (rule 4.2):{NC}")
    print(f"    Total words: {conn['word_count']}")
    print(f"    Total connectors: {conn['total']}")
    density = (conn['total'] / conn['word_count'] * 100) if conn['word_count'] > 0 else 0
    print(f"    Density: {density:.1f} per 100 words")

    if conn['primary']:
        primary_str = ', '.join(f"{k}:{v}" for k, v in sorted(conn['primary'].items(), key=lambda x: -x[1]))
        print(f"    Primary: {primary_str}")

    if conn['multi_word']:
        multi_str = ', '.join(f"{k}:{v}" for k, v in sorted(conn['multi_word'].items(), key=lambda x: -x[1]))
        print(f"    Multi-word: {multi_str}")

    if conn['causal']:
        causal_str = ', '.join(f"{k}:{v}" for k, v in sorted(conn['causal'].items(), key=lambda x: -x[1]) if k not in CONNECTORS_PRIMARY)
        if causal_str:
            print(f"    Causal: {causal_str}")
    if conn['contrastive']:
        contra_str = ', '.join(f"{k}:{v}" for k, v in sorted(conn['contrastive'].items(), key=lambda x: -x[1]))
        print(f"    Contrastive: {contra_str}")

    inv = results['totals']['inversions']
    print(f"\n  {CYAN}Fronted Inversions (rule 4.5, min {MIN_INVERSIONS_PER_SECTION}/section):{NC}")
    print(f"    Total found: {len(inv)}")
    if inv:
        for text, _ in inv[:5]:
            print(f"      - {text}")
        if len(inv) > 5:
            print(f"      ... and {len(inv) - 5} more")

    if results['sections']:
        print(f"\n  {CYAN}Per-Section Analysis:{NC}")
        for section in results['sections']:
            inv_count = len(section['inversions'])
            inv_status = GREEN if inv_count >= MIN_INVERSIONS_PER_SECTION else YELLOW
            print(f"    {section['title'][:40]:<40} inversions: {inv_status}{inv_count}{NC}, "
                  f"density: {section['density']:.1f}/100w")

    if results['issues']:
        print(f"\n  {YELLOW}Style Issues:{NC}")
        for issue in results['issues']:
            print(f"    {YELLOW}[{issue.issue_type}]{NC} {issue.section}: {issue.message}")


def apply_voice_profile(config) -> str:
    profile = load_voice_profile(config)
    module = sys.modules[__name__]
    for constant, setting in VOICE_SETTING_NAMES.items():
        setattr(module, constant, profile.number(setting))
    exempt = profile.words('paragraph_length_exempt') or DEFAULT_PARAGRAPH_LENGTH_EXEMPT_PATTERNS
    exempt = [config.manuscript.part_pattern] + list(exempt)
    PARAGRAPH_LENGTH_EXEMPT_PATTERNS[:] = [re.compile(p, re.IGNORECASE) for p in exempt]
    MEASURE_CATEGORIES['book-term'] |= coined_words(config)
    if config.manuscript.references:
        EXEMPT_FILES.add(config.manuscript.references.resolve())
    thinking = config.thinking
    for place in (thinking.dir, thinking.stance, thinking.stance_details, thinking.audience,
                  thinking.argument, thinking.doubts):
        if place:
            LENGTH_FREE_PLACES.add(Path(place).resolve())
    return str(profile.path)


def run_standalone(paths, options) -> int:
    total = 0
    if options.inversions:
        total += print_inversion_analysis(paths)
        if not (options.connectors or options.meta):
            return total
    for path in paths:
        if options.connectors:
            total += print_connector_analysis(path)
        if options.meta:
            total += print_meta_analysis(path)
    return total


def run_limits(paths, options) -> int:
    total = 0
    for path in paths:
        total += process_file(path, options.verbose)
        if options.stats:
            print_summary(path)
        if options.style:
            print_style_analysis(path)
    return total


def print_totals(paths, total, label):
    if len(paths) < 2:
        return
    print(f"\n{'='*50}")
    print(f"Processed: {GREEN}{len(paths)}{NC} files")
    print(f"Total {label}: {YELLOW if total > 0 else GREEN}{total}{NC}")


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split('\n\n', 1)[1])
    parser.add_argument('paths', nargs='*', help='files or folders (default: the manuscript)')
    parser.add_argument('--verbose', action='store_true', help='show every issue in full')
    parser.add_argument('--stats', action='store_true', help='compliance statistics')
    parser.add_argument('--style', action='store_true', help='connectors and inversions')
    parser.add_argument('--connectors', action='store_true', help='connector misuse')
    parser.add_argument('--meta', action='store_true', help='meta-announcements')
    parser.add_argument('--inversions', action='store_true', help='fronted inversions')
    parser.add_argument('--exempt-paragraph-length', metavar='REGEXES',
                        help='comma-separated file-name patterns whose paragraphs are not '
                             'length-checked (default: part files, bibliography, '
                             'acknowledgments); "" exempts nothing')
    parser.add_argument('--self-test', action='store_true',
                        help='check this script against the fixture book and exit')
    add_config_arguments(parser)
    return parser.parse_args(argv)


def run(argv) -> int:
    options = parse_arguments(argv)
    if options.self_test:
        return self_test()
    try:
        config = config_for_targets(options, options.paths)
        profile_path = apply_voice_profile(config)
        paths = [str(path) for path in markdown_files(options.paths, config)]
    except (ConfigError, FileNotFoundError, ValueError) as error:
        return tool_failed(str(error), 'sentence-and-paragraph-check')
    if not is_english_book(config):
        return skipped_for_language(config, "sentence-and-paragraph-check")
    if options.exempt_paragraph_length is not None:
        EXEMPT_FILES.clear()
        PARAGRAPH_LENGTH_EXEMPT_PATTERNS[:] = [
            re.compile(p.strip(), re.IGNORECASE)
            for p in options.exempt_paragraph_length.split(',') if p.strip()]
    if not paths:
        return tool_failed('no markdown files found; pass a file or folder',
                           'sentence-and-paragraph-check')
    if options.verbose:
        print(f"Voice profile: {profile_path}")
    if options.connectors or options.meta or options.inversions:
        total = run_standalone(paths, options)
        print_totals(paths, total, 'flags')
    else:
        total = run_limits(paths, options)
        print_totals(paths, total, 'issues')
    return 1 if total > 0 else 0


def self_test() -> int:
    failures = []
    manuscript = str(SAMPLE_BOOK / 'manuscript')
    chapter = str(SAMPLE_BOOK / 'manuscript' / '110-chapter-1.md')
    cases = [
        (['--config', str(SAMPLE_BOOK / 'book.yaml'), chapter], 1, 'very short (<6): 2'),
        (['--config', str(SAMPLE_BOOK / 'book.yaml'), '--connectors', chapter], 1,
         'characterization'),
        (['--config', str(SAMPLE_BOOK / 'book.yaml'), '--meta', chapter], 1, 'chapter-roadmap'),
        (['--config', str(SAMPLE_BOOK / 'book.yaml'), '--inversions', manuscript], 1,
         'From this observation emerges'),
        (['--config', str(SAMPLE_BOOK / 'book.yaml'), '--set', 'writing.sentence_min_words=3',
          '--set', 'writing.paragraph_min_sentences=1', '--set',
          'writing.sentence_review_below=1', str(SAMPLE_BOOK / 'manuscript' / '100-part-one.md')],
         0, ''),
        (['--config', str(SAMPLE_BOOK / 'book.yaml'), '--set', 'book.language=fr', chapter], 0,
         'SKIPPED'),
        (['--config', str(SAMPLE_BOOK / 'book.yaml'), '--set', 'thinking.argument=manuscript',
          chapter], 0, 'OK'),
        (['--config', str(FIXTURES_DIR / 'sample-paper' / 'book.yaml'),
          str(FIXTURES_DIR / 'sample-paper' / 'manuscript' / '020-introduction.md')], 0, 'OK'),
    ]
    for arguments, expected_exit, expected_text in cases:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = run(arguments)
        if exit_code != expected_exit:
            failures.append(f"{arguments[-2:]}: exit {exit_code}, expected {expected_exit}")
        if expected_text and expected_text not in output.getvalue():
            failures.append(f"{arguments[-2:]}: missing {expected_text!r}")
    for line in failures:
        print(f"FAIL  {line}")
    print(f"self-test: {'PASS' if not failures else str(len(failures)) + ' failure(s)'}")
    return 1 if failures else 0


def main():
    sys.exit(run(sys.argv[1:]))


if __name__ == '__main__':
    main()
