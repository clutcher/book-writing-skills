#!/usr/bin/env python3
"""Check how the book writes the titles it cites, and whether every citation has an entry.

Formatting (default mode):
  book-not-italic    DEFECT  a book title in the prose that is not in *italics*
  paper-not-quoted   DEFECT  a paper or article title that is not in "quotation marks"
A title counts as formatted when a wider italic or quoted span covers it. Headings,
table rows, fenced code and bibliography lines are skipped. A one-word or short title
that is also an ordinary name in the prose (a language, a practice, a tool) is listed in
the book's config as `terms.watch_words.titles_used_as_names`; such a title is matched
only in full, never by its short form. --fix adds the italics or quotation marks.

Completeness (--completeness):
  cited-missing      DEFECT  a key cited in the chapters with no bibliography entry
  never-cited        DEFECT  a bibliography entry nothing cites (the bibliography holds
                             only what the book cites)
  bracket-adjacent   DEFECT  [Key1][Key2]; write [Key1, Key2]
Keys come from lib/citation_key.py, so an a/b letter key, a `(c. 1975)` date and a
dateless `--` key are all seen on both sides. Always run completeness again after a
--fix in citation-key-check.py.

Usage:
  reference-format-check.py                       the manuscript and its bibliography
  reference-format-check.py --fix
  reference-format-check.py --completeness
  reference-format-check.py --references <refs.md> <file-or-folder>
  reference-format-check.py --self-test
"""

import argparse
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, NamedTuple, Tuple

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import (add_config_arguments, load_book, manuscript_paths, shown_path,
                          tool_failed)
from check_output import DEFECT, CheckReport, add_output_arguments, skipped_for_missing
from citation_key import KEY_BODY, bib_blocks, bib_entries, bib_entry

TOOL = "reference-format-check"
CLASSES = {"book-not-italic": DEFECT, "paper-not-quoted": DEFECT, "cited-missing": DEFECT,
           "never-cited": DEFECT, "bracket-adjacent": DEFECT}


ENTRY_DATE = re.compile(r'^(.+?)\s*\((?:--|n\.d\.|(?:c\.\s*)?\d{4})\)')


class Reference(NamedTuple):
    key: str
    title: str
    short_title: str
    ref_type: str
    authors: str


class Issue(NamedTuple):
    line_num: int
    title: str
    issue_type: str
    line_content: str


def parse_references(references_path: str) -> Dict[str, Reference]:
    references = {}

    if not Path(references_path).exists():
        return references

    with open(references_path, 'r', encoding='utf-8') as f:
        content = f.read()

    for _lineno, key, block in bib_blocks(content):
        entry_text = block.strip().replace('\n', ' ')

        author_match = ENTRY_DATE.match(entry_text)
        if not author_match:
            continue

        authors = author_match.group(1).strip()
        after_year = entry_text[author_match.end():].strip()

        if after_year.startswith('.'):
            after_year = after_year[1:].strip()

        if after_year.startswith('*'):
            book_title_match = re.match(r'\*([^*]+)\*', after_year)
            if book_title_match:
                title = book_title_match.group(1).strip()
                short_title = get_short_title(title)
                references[key] = Reference(
                    key=key,
                    title=title,
                    short_title=short_title,
                    ref_type='book',
                    authors=authors
                )
        else:

            paper_match = re.match(r'([^*]+?)\.\s*(?:\*|In\s+\*|https?://)', after_year)
            if paper_match:
                title = paper_match.group(1).strip()
                if not title.startswith('http') and len(title) > 5:
                    short_title = get_short_title(title)
                    references[key] = Reference(
                        key=key,
                        title=title,
                        short_title=short_title,
                        ref_type='paper',
                        authors=authors
                    )

    return references


EPONYMOUS_TITLES = set()


def get_short_title(title: str) -> str:
    if ':' in title:
        short = title.split(':')[0].strip()
        if len(short) >= 10 and len(short.split()) >= 2:
            return short

    words = title.split()
    if len(words) <= 5:
        return title
    return ' '.join(words[:5])


def check_file(filepath: str, references: Dict[str, Reference], verbose: bool = False) -> List[Issue]:
    issues = []

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    in_code_block = False

    for line_num, line in enumerate(lines, 1):
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue
        if line.strip().startswith('#'):
            continue
        if line.strip().startswith('|'):
            continue
        if bib_entry(line.strip()):
            continue

        for key, ref in references.items():
            titles_to_check = [ref.title]
            if ref.short_title != ref.title:
                titles_to_check.append(ref.short_title)
            titles_to_check = [x for x in titles_to_check
                               if x not in EPONYMOUS_TITLES or x == ref.title]
            if ref.title in EPONYMOUS_TITLES:
                continue

            for title in titles_to_check:
                if title not in line:
                    continue

                if ref.ref_type == 'book':
                    broad_italic_pattern = rf'\*[^*]*{re.escape(title)}[^*]*\*'
                    if not re.search(broad_italic_pattern, line):
                        issues.append(Issue(
                            line_num=line_num,
                            title=title,
                            issue_type='book-not-italic',
                            line_content=line.rstrip()
                        ))
                    break

                elif ref.ref_type == 'paper':
                    quoted_pattern = rf'[""]{re.escape(title)}[^""]*["""]'
                    full_title_pattern = rf'[""]{re.escape(ref.title)}["""]'
                    if not re.search(quoted_pattern, line) and not re.search(full_title_pattern, line):
                        issues.append(Issue(
                            line_num=line_num,
                            title=title,
                            issue_type='paper-not-quoted',
                            line_content=line.rstrip()
                        ))
                    break

    return issues


def fix_file(filepath: str, references: Dict[str, Reference], verbose: bool = False) -> Tuple[int, int]:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    issues_found = 0
    issues_fixed = 0

    for key, ref in references.items():
        titles_to_check = [ref.title]
        if ref.short_title != ref.title:
            titles_to_check.append(ref.short_title)

        for title in titles_to_check:
            if title not in content:
                continue

            if ref.ref_type == 'book':
                broad_italic_pattern = rf'\*[^*]*{re.escape(title)}[^*]*\*'
                if re.search(broad_italic_pattern, content):
                    continue

                lines = content.split('\n')
                new_lines = []
                in_code_block = False

                for line in lines:
                    if line.strip().startswith('```'):
                        in_code_block = not in_code_block
                        new_lines.append(line)
                        continue

                    if in_code_block or line.strip().startswith('#'):
                        new_lines.append(line)
                        continue

                    if bib_entry(line.strip()):
                        new_lines.append(line)
                        continue

                    if title in line and not re.search(broad_italic_pattern, line):
                        new_line = line.replace(title, f'*{title}*')
                        new_lines.append(new_line)
                        issues_found += 1
                        issues_fixed += 1
                        if verbose:
                            print(f"  Fixed book: {title}")
                    else:
                        new_lines.append(line)

                content = '\n'.join(new_lines)

            elif ref.ref_type == 'paper':
                quoted_pattern = rf'[""]{re.escape(title)}[^""]*["""]'
                full_title_pattern = rf'[""]{re.escape(ref.title)}["""]'
                if re.search(quoted_pattern, content) or re.search(full_title_pattern, content):
                    continue

                lines = content.split('\n')
                new_lines = []
                in_code_block = False

                for line in lines:
                    if line.strip().startswith('```'):
                        in_code_block = not in_code_block
                        new_lines.append(line)
                        continue

                    if in_code_block or line.strip().startswith('#'):
                        new_lines.append(line)
                        continue

                    if bib_entry(line.strip()):
                        new_lines.append(line)
                        continue

                    if re.search(full_title_pattern, line):
                        new_lines.append(line)
                        continue

                    if title in line and not re.search(quoted_pattern, line):
                        if ref.title in line:
                            new_line = line.replace(ref.title, f'"{ref.title}"')
                        else:
                            new_line = line.replace(title, f'"{title}"')
                        new_lines.append(new_line)
                        issues_found += 1
                        issues_fixed += 1
                        if verbose:
                            print(f"  Fixed paper: {ref.title}")
                    else:
                        new_lines.append(line)

                content = '\n'.join(new_lines)

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    return issues_found, issues_fixed


def prose_files(paths, references_path):
    skip = Path(references_path).resolve() if references_path else None
    return [str(p) for p in paths
            if 'references.md' not in Path(p).name and Path(p).resolve() != skip]


def extract_citation_keys_from_file(filepath: str) -> Tuple[Dict[str, List[int]], List[dict]]:
    citations = {}
    adjacent_bracket_violations = []

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    in_code_block = False
    key_pattern = KEY_BODY
    single_pattern = re.compile(rf'\[({key_pattern})\]')
    multi_pattern = re.compile(rf'\[({key_pattern}(?:\s*,\s*{key_pattern})+)\]')
    adjacent_pattern = re.compile(rf'\[({key_pattern})\]\s*\[({key_pattern})\]')

    for line_num, line in enumerate(lines, 1):
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        if bib_entry(line.strip()):
            continue

        for match in adjacent_pattern.finditer(line):
            adjacent_bracket_violations.append({
                'line': line_num,
                'keys': [match.group(1), match.group(2)],
                'text': match.group(0),
            })

        for match in multi_pattern.finditer(line):
            keys = [k.strip() for k in match.group(1).split(',')]
            for key in keys:
                if key not in citations:
                    citations[key] = []
                citations[key].append(line_num)

        for match in single_pattern.finditer(line):
            full_match_start = match.start()
            already_in_multi = False
            for mm in multi_pattern.finditer(line):
                if mm.start() <= full_match_start < mm.end():
                    already_in_multi = True
                    break
            if already_in_multi:
                continue
            key = match.group(1)
            if key not in citations:
                citations[key] = []
            citations[key].append(line_num)

    return citations, adjacent_bracket_violations


def extract_bibliography_keys(references_path: str) -> set:
    with open(references_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return {key for _lineno, key, _rest in bib_entries(content)}


def completeness(chapter_files, references_path):
    bibliography_keys = extract_bibliography_keys(references_path)
    cited = {}
    violations = []
    for filepath in chapter_files:
        citations, adjacent = extract_citation_keys_from_file(filepath)
        for key, lines in citations.items():
            cited.setdefault(key, []).extend((filepath, line) for line in lines)
        violations.extend((filepath, v) for v in adjacent)
    return cited, bibliography_keys, violations


FIXTURE_REFERENCES = '''# References

[Ren11] Rennie, A. (2011). *Raised Beds: A Season-by-Season Guide*. Example Press. ISBN 9780000000064.

[Vas14] Vasquez, E.N. (2014). Marshtalk. In *Proceedings of the Ninth Meeting on Regional Speech* (RSM 9) (pp. 3-1 - 3-14). Example Society. https://doi.org/10.5555/vas14

[Bry86a] Bryce, N.T. (1986). Sowing Too Late in Cold Valleys. *Journal of Examples*, 6(1), 12-15. https://doi.org/10.5555/bry86a

[Bry86b] Bryce, N.T. (1986). The Layout of a Hill Pasture. *Journal of Examples*, 6(3), 44-50. https://doi.org/10.5555/bry86b

[Bry79] Bryce, N.T. (c. 1979). Notebook on ditch clearing, spring floods and the mending of banks. https://example.org/ditch-notebook.html

[Wal--] Walsh, K. (--). A living catalog. https://catalog.example.org/

[Lin91] Lindqvist, K.A. (1991). The Fallow Year Rule. *Farm Notes*, 3(4), 112-118.

[Ash13] Ashby, C. (2013). *Deep Furrows: A Handbook of Market Garden Work*. Example Press. ISBN 9780000000071.

[Pel10] Pelham, G. (2010). *The Herb Border*. Example Press. ISBN 9780000000088.

[Dun88] Dunmore, F.E. (1988). Hedges for Exposed Coastal Farms. *Journal of Examples*, 13(2), 88-95. https://doi.org/10.5555/dun88
'''

FIXTURE_CHAPTER = '''# Deep Furrows as a heading is skipped

One author argues in Deep Furrows that beds should be small.

The same argument appears in *Deep Furrows*, where it is formatted correctly.

The whole span counts too: *Deep Furrows: A Handbook of Market Garden Work*.

Dunmore wrote Hedges for Exposed Coastal Farms in 1988.

Dunmore wrote "Hedges for Exposed Coastal Farms" in 1988.

Raised Beds, the widely used method, is not a title reference.

Marshtalk is spoken in three villages, and its last teachers retired long ago.

Both rules and the Fallow Year Rule reduce to rotation.

The Fallow Year Rule says to rest one field when the soil grows tired.

| Deep Furrows | a table row is skipped |

```text
// Deep Furrows inside a fence is skipped
```

[Ash13] Ashby, C. (2013). Deep Furrows. Example Press.

Bryce named the problem in Sowing Too Late in Cold Valleys in 1986.

He also wrote "The Layout of a Hill Pasture" that same year.

Notebook on ditch clearing, spring floods and the mending of banks is [Bry79].
'''

FIXTURE_EXPECTED = {
    (3, 'book-not-italic', 'Deep Furrows'),
    (9, 'paper-not-quoted', 'Hedges for Exposed Coastal Farms'),
    (19, 'paper-not-quoted', 'The Fallow Year Rule'),
    (29, 'paper-not-quoted', 'Sowing Too Late in Cold Valleys'),
    (33, 'paper-not-quoted', 'Notebook on ditch clearing, spring floods and the mending of banks'),
}

FIXTURE_CITING_CHAPTER = '''# Chapter 3

Hedges go back to [Dun88], and the argument for small beds to [Ash13].
Two at once: [Ash13, Dun88]. Adjacent brackets are a violation: [Bry86a][Bry86b].
A key with no bibliography entry at all: [Zzz99]. A dateless key: [Wal--].

[Ash13] Ashby, C. (2013). *Deep Furrows*. Example Press.
'''


def self_test() -> int:
    failures = []

    def require(condition, message):
        if not condition:
            failures.append(message)

    EPONYMOUS_TITLES.clear()
    EPONYMOUS_TITLES.update({'Marshtalk', 'Raised Beds'})
    with tempfile.TemporaryDirectory() as root:
        references_path = Path(root, '900-references.md')
        chapter_path = Path(root, '110-chapter-1.md')
        citing_path = Path(root, '220-chapter-3.md')
        for path, text in ((references_path, FIXTURE_REFERENCES),
                           (chapter_path, FIXTURE_CHAPTER),
                           (citing_path, FIXTURE_CITING_CHAPTER)):
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(text)
        references = parse_references(references_path)
        issues = check_file(chapter_path, references)
        bibliography_keys = extract_bibliography_keys(references_path)
        citations, violations = extract_citation_keys_from_file(citing_path)
    EPONYMOUS_TITLES.clear()

    for key, expected_type, expected_title in (
            ('Ash13', 'book', 'Deep Furrows: A Handbook of Market Garden Work'),
            ('Pel10', 'book', 'The Herb Border'),
            ('Ren11', 'book', 'Raised Beds: A Season-by-Season Guide'),
            ('Dun88', 'paper', 'Hedges for Exposed Coastal Farms'),
            ('Vas14', 'paper', 'Marshtalk'),
            ('Lin91', 'paper', 'The Fallow Year Rule')):
        reference = references.get(key)
        if not reference:
            failures.append("[%s] was not parsed at all" % key)
            continue
        require(reference.ref_type == expected_type,
                "[%s] parsed as %s, not %s" % (key, reference.ref_type, expected_type))
        require(reference.title == expected_title, "[%s] title parsed as %r" % (key, reference.title))
    found = {(issue.line_num, issue.issue_type, issue.title) for issue in issues}
    for item in sorted(FIXTURE_EXPECTED - found):
        failures.append("line %d %s %r NOT REPORTED" % item)
    for item in sorted(found - FIXTURE_EXPECTED):
        failures.append("line %d %s %r FALSE POSITIVE" % item)
    require(violations and violations[0]['keys'] == ['Bry86a', 'Bry86b'],
            "the adjacent-bracket violation was not caught")
    require('Ash13' in citations and 'Dun88' in citations, "a multi-key bracket was not split")
    require('Zzz99' in citations and 'Zzz99' not in bibliography_keys,
            "a citation with no entry must be visible as cited")
    require('Bry86a' in references and 'Bry79' in references,
            "an a/b key and a (c. 1979) date must parse for the formatting rule")
    require('Wal--' in bibliography_keys and 'Wal--' in citations,
            "a dateless -- key must be seen on both sides")
    for line in failures:
        print(f"FAIL {line}")
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument('target', nargs='?', help="a file or folder (default: the book's manuscript files)")
    parser.add_argument('--references', help='the bibliography (default: manuscript.references)')
    parser.add_argument('--completeness', action='store_true',
                        help='cross-match citations and bibliography instead of formatting')
    parser.add_argument('--fix', action='store_true', help='add the missing italics and quotes')
    parser.add_argument('--verbose', action='store_true', help='print each fix')
    parser.add_argument('--self-test', action='store_true', help='run the built-in examples')
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    references_path = args.references or config.manuscript.references
    if args.references and not Path(references_path).exists():
        return tool_failed("bibliography not found: %s" % references_path, TOOL)
    if skipped_for_missing(TOOL, references_path, "bibliography", args.format):
        return 0
    if args.target and not Path(args.target).exists():
        return tool_failed("not found: %s" % args.target, TOOL)
    names = (config.terms.watch_words or {}).get('titles_used_as_names') or []
    EPONYMOUS_TITLES.update(names if isinstance(names, list) else [names])
    files = prose_files(manuscript_paths(config, TOOL, args.target), str(references_path))

    report = CheckReport(TOOL + "-completeness" if args.completeness else TOOL, CLASSES)
    if args.completeness:
        cited, bibliography_keys, violations = completeness(files, str(references_path))
        for key in sorted(set(cited) - bibliography_keys):
            where = ", ".join("%s:%d" % (shown_path(config.root, f), n) for f, n in cited[key][:5])
            report.add(key, "cited-missing", "cited in %s" % where)
        for key in sorted(bibliography_keys - set(cited)):
            report.add(key, "never-cited", "in the bibliography, cited nowhere")
        for filepath, violation in violations:
            report.add("%s:%d" % (shown_path(config.root, filepath), violation['line']),
                       "bracket-adjacent", "%s -> [%s]" % (violation['text'], ", ".join(violation['keys'])))
        if args.format == "text":
            print("%d unique citations, %d bibliography entries, %d files\n"
                  % (len(cited), len(bibliography_keys), len(files)))
        return report.emit(args.format)

    references = parse_references(str(references_path))
    for filepath in files:
        if args.fix:
            found, fixed = fix_file(filepath, references, args.verbose)
            if fixed and args.format == "text":
                print("fixed %d in %s" % (fixed, shown_path(config.root, filepath)))
            continue
        for issue in check_file(filepath, references):
            report.add("%s:%d" % (shown_path(config.root, filepath), issue.line_num),
                       issue.issue_type, "%s -- %s" % (issue.title, issue.line_content.strip()[:100]))
    if args.format == "text":
        print("%d files, %d titles known\n" % (len(files), len(references)))
    return report.emit(args.format)


if __name__ == '__main__':
    sys.exit(main())
