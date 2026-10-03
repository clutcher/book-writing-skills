#!/usr/bin/env python3
"""Align the citation keys used in the book's thinking files with the bibliography.

It reads every markdown file in the book's thinking folder (`thinking.dir`, all subfolders:
the argument, the doubts and the author files), or, in a book with no thinking folder, the
stance, audience, argument and doubts places the config names. A file or folder given on the
command line is read alone.

Argument files (any file of the thinking folder) are written over a long time and
often cite the SAME source under a different key than the bibliography. Every such pair
silently breaks the join between an argument file and the book. But MOST keys used only in argument files are
legitimate (background reading, alternatives considered), so a key is never flagged
merely for being absent from the bibliography.

An argument file that uses bracket keys carries a "## References" section listing each key
with full detail, in the bibliography's format. That turns the right key into a
computation: parse authors and year, apply the alpha rule (lib/citation_key.py),
compare. Keys are scope-local: an a/b letter resolves a clash inside ONE file, and the
bibliography is one scope while each argument file is another.

Classes, in order of confidence:
  alias               DEFECT   the sources list records the key as a former name
                               ("_formerly registered as [Old]_" under the entry that
                               replaced it): the author's own declaration. --fix renames
  alias-by-sentence   ADVISORY an alias whose target has a/b siblings in the bibliography:
                               the right one depends on the sentence
  book-owned          DEFECT   the source is in the bibliography (authors + year, or title
                               + year) under another key: the book's key wins
  book-owned-maybe    ADVISORY same title, different year, or a/b siblings: an author call
  derivable-mismatch  DEFECT   not in the book, and the key differs from the derived one
                               (--fix-derived applies book-owned and derivable renames)
  collision           DEFECT   two distinct sources in one file derive to one key with no
                               a/b letters: the author assigns them
  duplicate-label     DEFECT   one source under two labels in one file
  cross-scope         INFORMATIONAL an argument key denotes a different work than the same
                               key in the bibliography; act only if the source is promoted
                               into the book, which merges the scopes
  non-derivable       INFORMATIONAL no parseable authors or no year
  shape-only          ADVISORY last resort for keys with no References entry: same letters
                               and year as a bibliography key, different string. Shape is
                               not evidence ([Pal72] and [Pal79] are different papers)
  bibliography-key    DEFECT   a bibliography entry's own authors and year derive another
                               key (a preprint year kept after publication is the usual
                               cause). Fix the book, not the argument files. A letter key whose
                               sibling is registered but uncited is accepted

Multi-key brackets are split: a naive \\[[^]]+\\] treats "[A99, B01]" as one key.

Usage:
  argument-key-check.py                        the whole thinking folder (thinking.dir)
  argument-key-check.py <file-or-folder>       only this file or folder
  argument-key-check.py --fix                  apply the list-declared aliases
  argument-key-check.py --fix-derived          also apply book-owned and derivable renames
  argument-key-check.py --plan PATH            write the rename plan as markdown
  argument-key-check.py --self-test
"""

import argparse
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import (add_config_arguments, load_book, shown_path, thinking_paths,
                          tool_failed, visible_markdown_files_under)
from check_output import (ADVISORY, DEFECT, INFORMATIONAL, CheckReport,
                          add_output_arguments)
from citation_key import (BIB_ENTRY, BIB_ENTRY_ANY, ENTRY_HEADING, KEY_SHAPE, is_placeholder,
                          parse as parse_key, strip_disambiguator,
                          derive as derive_alpha)

TOOL = "argument-key-check"
CLASSES = {
    "alias": DEFECT, "alias-by-sentence": ADVISORY, "book-owned": DEFECT,
    "book-owned-maybe": ADVISORY, "derivable-mismatch": DEFECT, "collision": DEFECT,
    "duplicate-label": DEFECT, "cross-scope": INFORMATIONAL, "non-derivable": INFORMATIONAL,
    "shape-only": ADVISORY, "bibliography-key": DEFECT,
}

BRACKET_RE = re.compile(r'\[([^\]\[\n]{1,200})\]')
BIB_ENTRY_RE = BIB_ENTRY
REGISTRY_HEADING_RE = ENTRY_HEADING
FORMERLY_RE = re.compile(r'_formerly registered as \[([^\]]+)\]_')
FENCE_RE = re.compile(r'```.*?```', re.S)

ENTRY_RE = BIB_ENTRY_ANY
YEAR_RE = re.compile(r'\((?:c\.\s*)?((?:1[89]|20)\d{2})[a-z]?(?:\s*/\s*(?:1[89]|20)\d{2})?\)')
INITIAL_TOKEN_RE = re.compile(r"^[A-Z]\.(?:-?[A-Z]\.?)*$|^[A-Z]$")
ELLIPSIS_RE = re.compile(r'\.\.\.|…')
NAME_WORD = r"[^\W\d_](?:[^\W\d_]|['’./-])*"
NAME_RE = re.compile(rf"^{NAME_WORD}(?:\s+{NAME_WORD})*$", re.UNICODE)
ORG_WORD_RE = re.compile(
    r'\b(?:group|division|department|institute|corporation|corp|university|college|'
    r'laborator(?:y|ies)|labs?|foundation|committee|blog|project|research|inc|ltd|llc|'
    r'association|consortium|society|council|agency|bureau|office|cent(?:re|er)|'
    r'systems|technolog(?:y|ies)|press|news|team|company|standards|organi[sz]ation)\b',
    re.I)
ROLE_RE = re.compile(r'^\(?(?:eds?|et al|jr|sr|ed|trans)\.?\)?$', re.I)
EDITION_RE = re.compile(
    r'\b(?:\d(?:st|nd|rd|th)\s+ed|anniversary|revised|reprint|translat|'
    r'originally published|new ed|updated ed)', re.I)
REFERENCES_HEADING_RE = re.compile(r'^(?:#{2,4}\s+|\*\*)References\b', re.I)
UNRESOLVED_HEADING_RE = re.compile(r'^#{3,4}\s+(?:Unresolved|Not resolved)\b', re.I)
SECTION_HEADING_RE = re.compile(r'^##\s+')
ETAL_RE = re.compile(r'\bet\s+al', re.I)

ALLOWLIST = {'Abc99'}


def shape(key):
    parsed = parse_key(key)
    return (parsed[0].lower(), parsed[2]) if parsed else None


ARTICLE_RE = re.compile(r'^(?:the|a|an)$', re.I)
PARTICLES = {'van', 'von', 'de', 'der', 'den', 'di', 'da', 'du', 'la', 'le', 'dos', 'ter'}


def is_initials(part):
    tokens = part.split()
    if not tokens:
        return False
    dotted = 0
    for token in tokens:
        if INITIAL_TOKEN_RE.match(token):
            dotted += 1
        elif not (token.islower() and token.strip('.') in PARTICLES):
            return False
    return dotted > 0


def surname_word(name):
    return " ".join(name.split())


def author_units(author_text):
    flags = []
    text = author_text.strip()
    if ETAL_RE.search(text):
        flags.append('et-al')
    if ELLIPSIS_RE.search(text):
        flags.append('ellipsis')
    text = ELLIPSIS_RE.sub(' ', text)
    text = re.sub(r'\bet\s+al\.?', ' ', text, flags=re.I)
    text = re.sub(r'\((?:Eds?|eds?|Trans)\.?\)', ' ', text)
    parts = [p.strip().strip(',;').strip()
             for p in re.split(r'\s*(?:,|&|\band\b)\s*', text)]
    names, saw_initials = [], False
    for part in parts:
        if not part:
            continue
        if ROLE_RE.match(part) or part.lower().startswith('et al'):
            continue
        if is_initials(part):
            saw_initials = True
            continue
        part = part.strip('.')
        if not part:
            continue
        if not NAME_RE.match(part):
            continue
        first_word = part.split()[0]
        if not (part[0].isupper() or (first_word.islower() and first_word in PARTICLES)):
            continue
        names.append(part)
    if not names:
        return [], 'none', flags
    if not saw_initials and any(len(n.split()) > 1 for n in names):
        joined = ', '.join(names)
        if len(names) == 1 or ORG_WORD_RE.search(joined):
            words = [w for w in joined.replace(',', ' ').split() if not ARTICLE_RE.match(w)]
            return [' '.join(words) or joined], 'org', flags
        return names, 'ambiguous', flags
    return [surname_word(n) for n in names], 'person', flags


def stem3(word):
    letters = re.sub(r'[^A-Za-z]', '', word)
    if not letters:
        return None
    letters = letters[:3]
    return letters[0].upper() + letters[1:]


def derive_key(author_text, year2, ignore_incomplete=False):
    if not year2:
        return None, 'no year in the entry'
    if not author_text or not author_text.strip():
        return None, 'no author field'
    units, kind, flags = author_units(author_text)
    if not units:
        return None, 'no parseable author or organisation'
    if kind == 'ambiguous':
        return None, ('several multi-word units without initials: one organisation '
                      'or several people cannot be told apart')
    if not ignore_incomplete:
        if 'ellipsis' in flags:
            return None, 'an ellipsis stands in for omitted authors: the list is incomplete'
        if 'et-al' in flags and len(units) < 4:
            return None, (f"'et al.' after only {len(units)} named author(s): the count "
                          f"is unknown, and alpha keys four authors differently from five")
    if kind == 'org':
        stem = stem3(units[0])
        return (stem + year2, 'organisation') if stem else (None, 'no parseable organisation')
    truncated = 'et-al' in flags or 'ellipsis' in flags
    OMITTED = ['Omitted', 'Omitted']
    try:
        names = units[:3] + OMITTED if truncated else units
        return derive_alpha(names, year2), 'authors'
    except ValueError as error:
        return None, str(error)


def primary_author(author_text):
    units, kind, _ = author_units(author_text or '')
    if not units or kind == 'ambiguous':
        return None
    first = units[0].split()[0] if kind == 'org' else units[0]
    return re.sub(r'[^a-z]', '', first.lower()) or None


TITLE_STOP_RE = re.compile(r'(?<=[a-z0-9\)\?\!\*])\.(?:\s|$)')


def extract_title(rest_after_year):
    text = rest_after_year.lstrip(' .)').strip()
    m = TITLE_STOP_RE.search(text)
    if m:
        text = text[:m.start()]
    return text.strip()


def normalise_title(title):
    return re.sub(r'[^a-z0-9]', '', (title or '').lower())


def title_tokens(title):
    return {t for t in re.findall(r'[a-z0-9]+', (title or '').lower()) if len(t) > 2}


def titles_match(a, b):
    na, nb = normalise_title(a), normalise_title(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if min(len(na), len(nb)) >= 18 and (na.startswith(nb) or nb.startswith(na)):
        return True
    ta, tb = title_tokens(a), title_tokens(b)
    if len(ta) < 3 or len(tb) < 3:
        return False
    return len(ta & tb) / len(ta | tb) >= 0.7


def parse_entries(path, section_only=False):
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    entries = []
    inside = not section_only
    unresolved = False
    for lineno, line in enumerate(lines, 1):
        if section_only:
            if REFERENCES_HEADING_RE.match(line):
                inside, unresolved = True, False
                continue
            if UNRESOLVED_HEADING_RE.match(line):
                unresolved = True
                continue
            if line.startswith('###'):
                unresolved = False
            if SECTION_HEADING_RE.match(line) and not REFERENCES_HEADING_RE.match(line):
                inside = False
            if not inside:
                continue
        m = ENTRY_RE.match(line)
        if not m:
            continue
        key, rest = m.group(1), m.group(2)
        ym = YEAR_RE.search(rest)
        year2 = ym.group(1)[-2:] if ym else None
        year4 = ym.group(1) if ym else None
        authors = rest[:ym.start()] if ym else None
        title = extract_title(rest[ym.end():]) if ym else None
        if unresolved:
            derived, reason, tentative = None, 'listed under "Unresolved" in its own file', None
            units = []
        else:
            derived, reason = derive_key(authors, year2)
            tentative = derived or derive_key(authors, year2, ignore_incomplete=True)[0]
            units, kind, _ = author_units(authors or '')
            units = units if kind == 'person' else []
        entries.append({
            'key': key, 'authors': authors, 'year': year2, 'year4': year4,
            'title': title, 'raw': rest, 'line': lineno, 'path': Path(path),
            'derived': derived, 'reason': reason, 'unresolved': unresolved,
            'tentative': tentative, 'surnames': tuple(units),
            'primary': None if unresolved else primary_author(authors or ''),
        })
    return entries


LABEL_RE = re.compile(r'^[A-Za-z][A-Za-z0-9+.\-_]{0,15}$')
LOOSE_DEF_RE = re.compile(r'^(?:[-*]\s+|\*\*[^*]{0,24}\*\*\s+)?\[([A-Za-z][A-Za-z0-9+.\-_]{0,15})\]\s+(\S.*)$')
LOOSE_YEAR_RE = re.compile(r'(?:\(|,\s*|\s)((?:19|20)\d{2})(?=[.,;)\]]|\s|$)')


def parse_loose_definitions(path):
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    found = {}
    inside = False
    for line in lines:
        if REFERENCES_HEADING_RE.match(line):
            inside = True
            continue
        if SECTION_HEADING_RE.match(line) and not REFERENCES_HEADING_RE.match(line):
            inside = False
        if inside:
            continue
        m = LOOSE_DEF_RE.match(line)
        if not m or m.group(2).startswith('('):
            continue
        found.setdefault(m.group(1), m.group(2).strip())
    return found


YEAR_PAREN_RE = re.compile(r'\((?:19|20)\d{2}[a-z]?\)')
SENTENCE_DOT_RE = re.compile(r'(?<![A-Z])\.(?:\s|$)')


def author_field_end(text):
    year = YEAR_PAREN_RE.search(text)
    if year and year.start() > 0:
        head = text[:year.start()].strip(' .,')
        if head:
            return head
    quote = text.find('"')
    if quote > 0:
        head = text[:quote].strip(' .,')
        if head:
            return head
    dot = SENTENCE_DOT_RE.search(text)
    if dot and dot.start() > 0:
        head = text[:dot.start()].strip(' .,')
        if head:
            return head
    return None


def parse_loose_entry(key, text, path):
    authors = author_field_end(text)
    body = re.sub(r'https?://\S+', ' ', text)
    years = LOOSE_YEAR_RE.findall(body)
    year4 = years[-1] if years else None
    title = None
    quoted = re.search(r'"([^"]{4,})"', text)
    if quoted:
        title = quoted.group(1)
    units, kind, _ = author_units(authors or '')
    if kind == 'org' and len(units[0].split()) > 1 and not ORG_WORD_RE.search(units[0]):
        authors = units[0].split()[-1]
    derived, reason = derive_key(authors, year4[-2:] if year4 else None)
    return {'key': key, 'authors': authors, 'year': year4[-2:] if year4 else None,
            'year4': year4, 'title': title, 'raw': text, 'line': 0, 'path': path,
            'derived': derived, 'reason': reason, 'unresolved': False, 'loose': True,
            'surnames': tuple(), 'primary': primary_author(authors or '')}


def labels_in_text(text):
    text = FENCE_RE.sub(lambda m: '\n' * m.group(0).count('\n'), text)
    labels = set()
    for m in BRACKET_RE.finditer(text):
        if m.end() < len(text) and text[m.end()] == '(':
            continue
        for part in m.group(1).split(','):
            candidate = part.strip().rstrip('.;:')
            if LABEL_RE.match(candidate):
                labels.add(candidate)
    return labels


def parse_bibliography(path):
    keys = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        m = BIB_ENTRY_RE.match(line)
        if m:
            keys[m.group(1)] = line.strip()
    return keys


def parse_registry_aliases(path):
    aliases = {}
    registered = set()
    current = None
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        heading = REGISTRY_HEADING_RE.match(line)
        if heading and is_placeholder(heading.group(1)):
            heading = None
        if heading:
            current = heading.group(1)
            registered.add(current)
        former = FORMERLY_RE.search(line)
        if former and current:
            aliases[former.group(1)] = current
    return aliases, registered


def keys_in_text(text, extra_labels=()):
    text = FENCE_RE.sub(lambda m: '\n' * m.group(0).count('\n'), text)
    extra = set(extra_labels)
    for m in BRACKET_RE.finditer(text):
        if m.end() < len(text) and text[m.end()] == '(':
            continue
        for part in m.group(1).split(','):
            candidate = part.strip().rstrip('.;:')
            if KEY_SHAPE.match(candidate) or candidate in extra:
                yield candidate


def collect_research_keys(files, labels_by_file=None):
    usage = defaultdict(lambda: defaultdict(int))
    for f in files:
        extra = (labels_by_file or {}).get(f, ())
        for key in keys_in_text(f.read_text(encoding='utf-8'), extra):
            usage[key][f] += 1
    return usage, files


def has_suffix_family(target_key, bibliography):
    parsed = parse_key(target_key)
    if not parsed or not parsed[3]:
        return False
    base = strip_disambiguator(target_key)
    siblings = [k for k in bibliography if parse_key(k) and strip_disambiguator(k) == base]
    return len(siblings) > 1


def build_book_index(book_entries):
    by_authors_year = defaultdict(list)
    by_primary = defaultdict(list)
    for e in book_entries:
        if e['surnames'] and e['year']:
            by_authors_year[(e['surnames'], e['year'])].append(e)
        if e['primary']:
            by_primary[e['primary']].append(e)
    return by_authors_year, by_primary


def find_book_match(entry, index):
    by_authors_year, by_primary = index
    same_author_year = by_authors_year.get((entry['surnames'], entry['year']), [])
    if len(same_author_year) == 1 and (not entry['title'] or not same_author_year[0]['title']
                                       or titles_match(entry['title'], same_author_year[0]['title'])):
        return same_author_year[0], 'exact'
    for candidate in same_author_year:
        if titles_match(entry['title'], candidate['title']):
            return candidate, 'exact'
    if entry['title'] and entry['primary']:
        for candidate in by_primary.get(entry['primary'], []):
            if not titles_match(entry['title'], candidate['title']):
                continue
            return candidate, 'exact' if candidate['year'] == entry['year'] else 'title-only'
    return None, None


def has_disambiguator(key):
    return strip_disambiguator(key) != key


def next_disambiguators(base, taken):
    free = [base + c for c in 'abcdefghij' if base + c not in taken]
    return free[:2] or [base + 'a', base + 'b']


def analyse_derivation(files, book_entries, bibliography):
    index = build_book_index(book_entries)
    book_by_key = {e['key']: e for e in book_entries}

    book_owned, book_owned_soft = [], []
    mismatches, collisions, non_derivable, duplicate_labels = [], [], [], []
    cross_scope = []
    entries_by_file = {}
    all_labels = defaultdict(set)
    ok_count = 0

    for f in files:
        entries = parse_entries(f, section_only=True)
        if not entries:
            continue
        entries = list({e['key']: e for e in entries}.values())
        entries_by_file[f] = entries
        for e in entries:
            all_labels[f].add(e['key'])

        seen = []
        for e in entries:
            for other in seen:
                if e['key'] == other['key'] or not (e['title'] and other['title']):
                    continue
                if not titles_match(e['title'], other['title']):
                    continue
                if e['year'] and e['year'] == other['year']:
                    why = 'same author, title and year'
                elif EDITION_RE.search(e['raw']) or EDITION_RE.search(other['raw']):
                    continue
                else:
                    why = (f"same author and title under two years ({other['year4']} and "
                           f"{e['year4']}), with no edition marker: one work or a catalogue "
                           f"ambiguity, for the author to resolve")
                duplicate_labels.append({'file': f, 'keys': (other['key'], e['key']),
                                         'source': e['title'] or e['raw'][:70], 'why': why})
                break
            seen.append(e)

        by_derived = defaultdict(list)
        for e in entries:
            if e['derived']:
                by_derived[e['derived']].append(e)
        colliding = set()
        for derived, group in by_derived.items():
            distinct = []
            for e in group:
                if not any(titles_match(e['title'], d['title']) for d in distinct):
                    distinct.append(e)
            if len(distinct) > 1:
                labels = [d['key'] for d in distinct]
                if all(has_disambiguator(k) for k in labels) and len(set(labels)) == len(labels):
                    continue
                colliding.add(derived)
                collisions.append({'kind': 'within-file', 'file': f, 'derived': derived,
                                   'entries': distinct})

        for e in entries:
            key = e['key']
            match, confidence = find_book_match(e, index)

            if confidence == 'exact':
                if key == match['key']:
                    ok_count += 1
                elif has_suffix_family(match['key'], bibliography):
                    book_owned_soft.append({'file': f, 'key': key, 'book_key': match['key'],
                                            'source': e['title'] or e['raw'][:70],
                                            'why': 'bibliography disambiguates this year with '
                                                   'a/b siblings; the right one depends on the '
                                                   'sentence'})
                else:
                    book_owned.append({'file': f, 'key': key, 'book_key': match['key'],
                                       'source': e['title'] or e['raw'][:70]})
                continue

            if confidence == 'title-only':
                book_owned_soft.append({'file': f, 'key': key, 'book_key': match['key'],
                                        'source': e['title'] or e['raw'][:70],
                                        'why': f"same title, different publication year "
                                               f"({e['year4']} here, {match['year4']} in the "
                                               f"bibliography): an author decision"})
                continue

            clash = book_by_key.get(key) or (book_by_key.get(e['derived'])
                                             if e['derived'] != key else None)
            if clash is not None:
                if not has_disambiguator(key):
                    cross_scope.append({'file': f, 'key': key, 'book_key': clash['key'],
                                        'here': e['title'] or e['raw'][:70],
                                        'book': clash['title'] or clash['raw'][:70]})
                continue
            if e['derived'] is None:
                if e.get('tentative') and e['tentative'] == key:
                    ok_count += 1
                    continue
                non_derivable.append({'file': f, 'key': key, 'reason': e['reason'],
                                      'known': e['raw'][:110]})
                continue
            if e['derived'] in colliding:
                continue
            if key == e['derived'] or strip_disambiguator(key) == e['derived']:
                ok_count += 1
                continue
            mismatches.append({'file': f, 'key': key, 'derived': e['derived'],
                               'source': e['title'] or e['raw'][:70],
                               'authors': (e['authors'] or '').strip(), 'year': e['year4']})

    for f in files:
        text = f.read_text(encoding='utf-8')
        used = labels_in_text(text)
        documented = all_labels.get(f, set())
        undocumented = used - documented
        if not undocumented:
            continue
        loose = parse_loose_definitions(f)
        known = list(entries_by_file.get(f, []))
        for label in sorted(undocumented):
            if label in loose:
                e = parse_loose_entry(label, loose[label], f)
                known.append(e)
                all_labels[f].add(label)
                if e['derived'] is None:
                    non_derivable.append({'file': f, 'key': label, 'reason': e['reason'],
                                          'known': e['raw'][:110], 'loose': True})
                elif e['derived'] in book_by_key and e['derived'] != label:
                    if not has_disambiguator(label):
                        clash = book_by_key[e['derived']]
                        cross_scope.append({'file': f, 'key': label, 'book_key': clash['key'],
                                            'here': e['title'] or e['raw'][:70],
                                            'book': clash['title'] or clash['raw'][:70]})
                elif label != e['derived'] and strip_disambiguator(label) != e['derived']:
                    mismatches.append({'file': f, 'key': label, 'derived': e['derived'],
                                       'source': e['title'] or e['raw'][:70],
                                       'authors': (e['authors'] or '').strip(),
                                       'year': e['year4'], 'loose': True})
                else:
                    ok_count += 1
                continue
            spelled = re.sub(r'[^a-z]', '', label.lower())
            if len(spelled) < 4:
                continue
            for e in known:
                if e['primary'] and e['primary'] == spelled and e['key'] != label:
                    duplicate_labels.append({'file': f, 'keys': (e['key'], label),
                                             'source': e['title'] or e['raw'][:70],
                                             'why': 'the second label is the author surname, '
                                                    'used undefined in the prose'})
                    all_labels[f].add(label)
                    break

    return {'book_owned': book_owned, 'book_owned_soft': book_owned_soft,
            'mismatches': mismatches, 'collisions': collisions,
            'cross_scope': cross_scope,
            'non_derivable': non_derivable, 'duplicate_labels': duplicate_labels,
            'labels_by_file': all_labels, 'ok': ok_count,
            'described': {e['key'] for es in entries_by_file.values() for e in es}}


def classify(usage, bibliography, aliases, registered, described=frozenset()):
    fixable, manual, shape_hits = {}, {}, {}
    bib_by_shape = defaultdict(list)
    for key in bibliography:
        s = shape(key)
        if s:
            bib_by_shape[s].append(key)

    for key in usage:
        if key in ALLOWLIST or key in bibliography:
            continue
        target = aliases.get(key)
        if target and target != key:
            if has_suffix_family(target, bibliography):
                manual[key] = (target, 'bibliography disambiguates this year with '
                                       'a/b siblings; the right one depends on the sentence')
            else:
                fixable[key] = target
            continue
        if key in registered or key in described:
            continue
        candidates = [b for b in bib_by_shape.get(shape(key) or (), []) if b != key]
        if candidates:
            shape_hits[key] = candidates
    return fixable, manual, shape_hits


def rewrite(text, mapping):
    count = 0

    def replace(match):
        nonlocal count
        parts = []
        for part in match.group(1).split(','):
            stripped = part.strip()
            if stripped in mapping:
                parts.append(part.replace(stripped, mapping[stripped]))
                count += 1
            else:
                parts.append(part)
        return '[' + ','.join(parts) + ']'

    return BRACKET_RE.sub(replace, text), count


def apply_fixes(files, mapping):
    total, touched = 0, 0
    for f in files:
        per_file = mapping.get(f) if all(isinstance(k, Path) for k in mapping) else mapping
        if not per_file:
            continue
        text = f.read_text(encoding='utf-8')
        new_text, n = rewrite(text, per_file)
        if n:
            f.write_text(new_text, encoding='utf-8')
            print(f"  fixed {f}: {n}")
            total += n
            touched += 1
    return total, touched


def derived_rename_map(analysis):
    mapping = defaultdict(dict)
    for row in analysis['book_owned']:
        mapping[row['file']][row['key']] = row['book_key']
    for row in analysis['mismatches']:
        mapping[row['file']][row['key']] = row['derived']
    return dict(mapping)


def add_items(report, analysis, usage, fixable, manual, shape_hits, book_defects, root):
    def place(f):
        return shown_path(root, f)

    def locations(key):
        return ", ".join("%s (x%d)" % (place(f), n)
                         for f, n in sorted(usage.get(key, {}).items(), key=lambda kv: str(kv[0])))

    if analysis:
        for r in analysis['book_owned']:
            report.add(r['key'], "book-owned", "-> [%s] in %s: %s"
                       % (r['book_key'], place(r['file']), r['source'][:90]))
        for r in analysis['book_owned_soft']:
            report.add(r['key'], "book-owned-maybe", "~ [%s] in %s: %s -- %s"
                       % (r['book_key'], place(r['file']), r['source'][:80], r['why']))
        for r in analysis['mismatches']:
            report.add(r['key'], "derivable-mismatch", "-> [%s] in %s: %s (%s). %s"
                       % (r['derived'], place(r['file']), r['authors'][:60], r['year'],
                          r['source'][:70]))
        for r in analysis['duplicate_labels']:
            first, second = r['keys']
            report.add("%s,%s" % (first, second), "duplicate-label", "in %s: %s -- %s"
                       % (place(r['file']), r['source'][:80], r['why']))
        for r in analysis['collisions']:
            members = "; ".join("[%s] %s" % (e['key'], (e['title'] or e['raw'])[:60])
                                for e in r['entries'])
            report.add(r['derived'], "collision", "in %s: %s" % (place(r['file']), members))
        for r in analysis.get('cross_scope', []):
            report.add(r['key'], "cross-scope", "in %s: here %s; bibliography %s"
                       % (place(r['file']), r['here'][:60], r['book'][:60]))
        for r in analysis['non_derivable']:
            report.add(r['key'], "non-derivable", "in %s: %s" % (place(r['file']), r['reason']))
    for key in sorted(fixable):
        report.add(key, "alias", "-> [%s] in %s" % (fixable[key], locations(key)))
    for key in sorted(manual):
        target, why = manual[key]
        report.add(key, "alias-by-sentence", "~ [%s] -- %s -- %s" % (target, why, locations(key)))
    for key in sorted(shape_hits):
        report.add(key, "shape-only", "?~ %s in %s -- verify the author surnames by hand"
                   % (", ".join("[%s]" % c for c in shape_hits[key]), locations(key)))
    for d in book_defects:
        report.add(d['key'], "bibliography-key", "-> [%s] line %d: %s  %s"
                   % (d['derived'], d['line'], d['why'], d['title'][:60]))


def write_plan(path, analysis, usage, book_total, self_test):
    def occ(key, f):
        return usage.get(key, {}).get(f, 0)

    lines = ['# Argument files: citation-key derivation plan', '',
             'Made by `argument-key-check.py`. Nothing here has been applied.', '',
             '## Deriver self-test against the bibliography', '',
             f"- entries parsed: {self_test['total']}",
             f"- reproduced exactly: {self_test['ok']}",
             f"- not reproduced: {len(self_test['fail'])}", '']
    for key, expected, why in self_test['fail']:
        lines.append(f"  - `[{key}]` derives to `{expected}` -- {why}")
    lines += ['', '## Counts', '',
              '| Classification | Count |', '|---|---|',
              f"| BOOK-OWNED (rename to the book key) | {len(analysis['book_owned'])} |",
              f"| BOOK-OWNED candidate (author decision) | {len(analysis['book_owned_soft'])} |",
              f"| DERIVABLE-MISMATCH | {len(analysis['mismatches'])} |",
              f"| COLLISION | {len(analysis['collisions'])} |",
              f"| NON-DERIVABLE | {len(analysis['non_derivable'])} |",
              f"| Duplicate labels for one source | {len(analysis['duplicate_labels'])} |",
              f"| Already correct | {analysis['ok']} |", '']

    if analysis['book_owned']:
        lines += ['## BOOK-OWNED renames', '',
                  '| Current | Book key | Source | File | Uses |', '|---|---|---|---|---|']
        for r in sorted(analysis['book_owned'], key=lambda r: (str(r['file']), r['key'])):
            lines.append(f"| `{r['key']}` | `{r['book_key']}` | {r['source'][:80]} "
                         f"| `{r['file']}` | {occ(r['key'], r['file'])} |")
        lines.append('')

    if analysis['book_owned_soft']:
        lines += ['## BOOK-OWNED candidates (author decision)', '',
                  '| Current | Book key | Source | File | Uses | Why manual |',
                  '|---|---|---|---|---|---|']
        for r in sorted(analysis['book_owned_soft'], key=lambda r: (str(r['file']), r['key'])):
            lines.append(f"| `{r['key']}` | `{r['book_key']}` | {r['source'][:70]} "
                         f"| `{r['file']}` | {occ(r['key'], r['file'])} | {r['why']} |")
        lines.append('')

    if analysis['mismatches']:
        lines += ['## DERIVABLE-MISMATCH renames', '',
                  'Basis "source list" means the entry was read from the file own bullet list '
                  'rather than a References entry, so its author field is looser.', '',
                  '| Current | Derived | Source | File | Uses | Basis |',
                  '|---|---|---|---|---|---|']
        for r in sorted(analysis['mismatches'], key=lambda r: (str(r['file']), r['key'])):
            src = f"{r['authors'][:48]} ({r['year']}). {r['source'][:60]}"
            basis = 'source list' if r.get('loose') else 'References entry'
            lines.append(f"| `{r['key']}` | `{r['derived']}` | {src} "
                         f"| `{r['file']}` | {occ(r['key'], r['file'])} | {basis} |")
        lines.append('')

    if analysis['duplicate_labels']:
        lines += ['## Duplicate labels for one source', '',
                  '| Labels | Source | Why | File |', '|---|---|---|---|']
        for r in sorted(analysis['duplicate_labels'], key=lambda r: (str(r['file']), r['keys'])):
            lines.append(f"| `{r['keys'][0]}` + `{r['keys'][1]}` | {r['source'][:80]} "
                         f"| {r['why']} | `{r['file']}` |")
        lines.append('')

    if analysis.get('cross_scope'):
        lines += ['## CROSS-SCOPE key reuse (informational, no action owed)', '',
                  'A disambiguator resolves a clash inside one scope. The bibliography is one',
                  'scope and each research file is another, so the same key may denote a',
                  'different work in each without either being wrong. These become real',
                  'collisions only if the research source is promoted into the book.', '',
                  '| Key | In the research file | In the bibliography | File |', '|---|---|---|---|']
        for r in sorted(analysis['cross_scope'], key=lambda r: (str(r['file']), r['key'])):
            lines.append(f"| `{r['key']}` | {r['here'][:70]} | {r['book'][:70]} | `{r['file']}` |")
        lines.append('')

    if analysis['collisions']:
        lines += ['## COLLISIONS (author assigns a/b)', '']
        for r in sorted(analysis['collisions'], key=lambda r: (r['kind'], str(r['file']))):
            scope = 'within the file' if r['kind'] == 'within-file' else 'against the bibliography'
            lines.append(f"- `[{r['derived']}]` -- {scope} -- `{r['file']}`")
            for e in r['entries']:
                origin = 'bibliography' if e.get('book') else 'this file'
                lines.append(f"  - `[{e['key']}]` ({origin}) {(e['title'] or e['raw'])[:100]}")
        lines.append('')

    if analysis['non_derivable']:
        lines += ['## NON-DERIVABLE', '',
                  '| Label | Missing | What is known | File |', '|---|---|---|---|']
        for r in sorted(analysis['non_derivable'], key=lambda r: (str(r['file']), r['key'])):
            known = r['known'].replace('|', '\\|')[:90]
            lines.append(f"| `{r['key']}` | {r['reason']} | {known} | `{r['file']}` |")
        lines.append('')

    Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f"Plan written: {path}")


def bibliography_key_check(book_entries, registered=None):
    registered = registered or set()

    def disambiguated_elsewhere(key, base):
        if key == base or not key.startswith(base) or len(key) != len(base) + 1:
            return False
        return any(other != key and other.startswith(base) and
                   len(other) == len(base) + 1 and other[-1].islower()
                   for other in registered)
    by_base = defaultdict(list)
    fail, book_defects = [], []
    for e in book_entries:
        if e['derived'] is None:
            fail.append((e['key'], '(none)', f"DERIVER: {e['reason']}"))
            continue
        by_base[e['derived']].append(e)
    for base, group in by_base.items():
        group.sort(key=lambda e: e['line'])
        if len(group) == 1:
            if group[0]['key'] != base and not disambiguated_elsewhere(group[0]['key'], base):
                why = (f"authors {', '.join(group[0]['surnames']) or '(org)'} "
                       f"({group[0]['year4']})")
                fail.append((group[0]['key'], base, f"BIBLIOGRAPHY: {why}"))
                book_defects.append({'key': group[0]['key'], 'derived': base,
                                     'why': why, 'line': group[0]['line'],
                                     'title': group[0]['title'] or group[0]['raw'][:70]})
        else:
            for i, e in enumerate(group):
                expected = base + chr(ord('a') + i)
                if e['key'] != expected:
                    fail.append((e['key'], expected, 'BIBLIOGRAPHY: disambiguation order'))
                    book_defects.append({'key': e['key'], 'derived': expected,
                                         'why': 'disambiguation order', 'line': e['line'],
                                         'title': e['title'] or e['raw'][:70]})
    return {'total': len(book_entries), 'ok': len(book_entries) - len(fail),
            'fail': fail, 'book_defects': book_defects}


FIXTURE_REFERENCES = """# References

[Smi99] Smith, J. (1999). *A Book About Things*. Example Press.
[ABC+20] Adams, A., Baker, B., Clark, C., Davis, D., & Evans, E. (2020). A big paper. *Journal*, 1(1), 1-2.
[Jon26] Jones, K. & Lee, M. (2024). A preprint kept under its old year. *Journal*, 2(1), 3-4.
"""

FIXTURE_LIST = """# Sources List

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)
```

### [Smi99] Smith, "A Book About Things" (1999)

**Full title:** A Book About Things
**Record history:** _formerly registered as [Smit99]_

---

### [vS99] van Staden, "Particles in Names" (1999)

**Full title:** Particles in Names
**Record history:** _formerly registered as [vSn99]_

---

### [Wal--] Walsh, "An Undated Page" (--)

**Full title:** An Undated Page
**Record history:** _formerly registered as [Wsh--]_

---
"""

FIXTURE_NOTES = """# Notes

The book source is [Smith99], the alias is [Smit99], two at once [Ken05, Wal10].
A particle key alias [vSn99] and a dateless key alias [Wsh--] are aliases too.

## References

[Smith99] Smith, J. (1999). *A Book About Things*. Example Press.
[Ken05] Kent, A. & Nash, B. (2005). A paper outside the book. *Journal*, 3(1), 5-6.
[Wal10] Walsh, K. (2010). A post. https://example.org/post
"""


def self_test():
    failures = []
    with tempfile.TemporaryDirectory() as root:
        refs = Path(root) / "references.md"
        listed = Path(root) / "list.md"
        notes = Path(root) / "notes"
        notes.mkdir()
        refs.write_text(FIXTURE_REFERENCES, encoding="utf-8")
        listed.write_text(FIXTURE_LIST, encoding="utf-8")
        (notes / "a.md").write_text(FIXTURE_NOTES, encoding="utf-8")
        book_entries = parse_entries(refs)
        bibliography = parse_bibliography(refs)
        aliases, registered = parse_registry_aliases(listed)
        files = sorted(notes.rglob("*.md"))
        analysis = analyse_derivation(files, book_entries, bibliography)
        usage, files = collect_research_keys(files, analysis['labels_by_file'])
        fixable, manual, shape_hits = classify(usage, bibliography, aliases, registered,
                                               analysis['described'])
        defects = bibliography_key_check(book_entries, registered)['book_defects']
        mapping = derived_rename_map(analysis)
        apply_fixes(files, mapping)
        rewritten = (notes / "a.md").read_text(encoding="utf-8")
    if derive_key("Adams, A., Baker, B., Clark, C., Davis, D., & Evans, E.", "20")[0] != "ABC+20":
        failures.append("five authors must derive ABC+20")
    if derive_key("Kent, A. & Nash, B.", "05")[0] != "KN05":
        failures.append("two authors must derive KN05")
    if [(r['key'], r['book_key']) for r in analysis['book_owned']] != [("Smith99", "Smi99")]:
        failures.append("book-owned wrong: %s" % analysis['book_owned'])
    if sorted((r['key'], r['derived']) for r in analysis['mismatches']) != [("Ken05", "KN05")]:
        failures.append("derivable mismatch wrong: %s" % analysis['mismatches'])
    if fixable != {"Smit99": "Smi99", "vSn99": "vS99", "Wsh--": "Wal--"}:
        failures.append("list-declared alias wrong: %s" % fixable)
    if [d['key'] for d in defects] != ["Jon26"]:
        failures.append("the bibliography key built from a preprint year was not caught: %s" % defects)
    if "[Smi99]" not in rewritten or "[KN05, Wal10]" not in rewritten:
        failures.append("derived renames were not applied inside brackets: %r" % rewritten[:120])
    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument('target', nargs='?', default=None,
                        help='only this file or folder (default: the whole thinking folder)')
    parser.add_argument('--references', default=None, help='the bibliography')
    parser.add_argument('--list', dest='sources_list', default=None, help='the sources list')
    parser.add_argument('--fix', action='store_true', help='apply the list-declared aliases')
    parser.add_argument('--fix-derived', action='store_true',
                        help='also apply book-owned and derivable renames')
    parser.add_argument('--no-derive', action='store_true',
                        help='skip the References derivation (alias and shape only)')
    parser.add_argument('--plan', default=None, metavar='PATH',
                        help='write the rename plan to a markdown file')
    parser.add_argument('--self-test', action='store_true', help='run the built-in examples')
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    references = Path(args.references) if args.references else config.manuscript.references
    registry = Path(args.sources_list) if args.sources_list else config.sources.list
    for path, label, given in ((references, 'bibliography', args.references),
                               (args.target, 'thinking file or folder', args.target),
                               (registry, 'sources list', args.sources_list)):
        if given and not Path(path).exists():
            return tool_failed("missing %s: %s" % (label, path), TOOL)
    report = CheckReport(TOOL, CLASSES)
    for path, label in ((references, 'bibliography'), (registry, 'sources list')):
        if report.skip_unless_present(path, label):
            return report.emit(args.format)
    files = visible_markdown_files_under(args.target) if args.target else thinking_paths(config)
    if not files:
        report.skip("the book has no thinking files")
        return report.emit(args.format)

    book_entries = parse_entries(references)
    for entry in book_entries:
        entry['book'] = True
    bibliography = parse_bibliography(references)
    aliases, registered = parse_registry_aliases(registry)

    analysis = None
    labels_by_file = {}
    if not args.no_derive:
        analysis = analyse_derivation(files, book_entries, bibliography)
        labels_by_file = analysis['labels_by_file']
    usage, files = collect_research_keys(files, labels_by_file)
    described = analysis['described'] if analysis else frozenset()
    fixable, manual, shape_hits = classify(usage, bibliography, aliases, registered, described)
    book_defects = bibliography_key_check(book_entries, registered)['book_defects']

    if args.fix and fixable:
        apply_fixes(files, fixable)
        fixable = {}
    if args.fix_derived and analysis:
        apply_fixes(files, derived_rename_map(analysis))
        analysis = {**analysis, 'book_owned': [], 'mismatches': []}
    if args.plan and analysis:
        write_plan(args.plan, analysis, usage, len(bibliography),
                   bibliography_key_check(book_entries, registered))

    add_items(report, analysis, usage, fixable, manual, shape_hits, book_defects, config.root)
    if args.format == 'text':
        print("bibliography %d keys, sources list %d keys and %d aliases, thinking files %d keys in %d files\n"
              % (len(bibliography), len(registered), len(aliases), len(usage), len(files)))
    return report.emit(args.format)


if __name__ == '__main__':
    sys.exit(main())
