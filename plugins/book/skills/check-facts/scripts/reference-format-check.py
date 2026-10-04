#!/usr/bin/env python3
"""Check the format of the book's .bib entries, and how the prose writes the titles it cites.

The .bib (sources.bibliography), default mode:
  missing-field      DEFECT  a field the entry type needs is missing (article: author,
                             title, journal; book: author or editor, title, publisher; ...).
                             The year is left to citation-key-check.py: a work with no
                             date has no year and takes `--` in its key
                             A field the entry takes from its `crossref` parent counts,
                             as in BibTeX
  unknown-type       DEFECT  an entry type that is not a standard BibTeX type
  unknown-field      DEFECT  a field outside the identity fields the book keeps in the
                             .bib (access, cache and findings belong in the two banks)
  repeated-field     DEFECT  one field written twice in an entry (bibtex keeps the first)
  duplicate-key      DEFECT  two entries with one key
  doi-not-bare       DEFECT  a doi written as a link or with a `doi:` label; write 10.x/y
  isbn-not-13        DEFECT  an isbn that is not 13 digits with a valid check digit
--fix writes the bare doi and the 13-digit isbn (an ISBN-10 is converted), and writes the
file back in its standard form (lib/bibliography.py).

Titles in the prose (--titles):
  book-not-italic    DEFECT  a book title in the prose that is not in *italics*
  paper-not-quoted   DEFECT  a paper or article title that is not in "quotation marks"
A title counts as formatted when a wider italic or quoted span covers it. Headings, table
rows and fenced code are skipped. A one-word or short title that is also an ordinary name
in the prose (a language, a practice, a tool) is listed in the book's config as
`terms.watch_words.titles_used_as_names`; such a title is matched only in full, never by
its short form. --titles --fix adds the italics or quotation marks.

Whether every citation has an entry, old `[Key]` citations and a hand-written references list are
citation-check.py.

Usage:
  reference-format-check.py                       the .bib
  reference-format-check.py --fix
  reference-format-check.py --titles [<file-or-folder>]
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
from bibliography import (IDENTITY_FIELDS, BibliographyError, parse_bibliography,
                          read_bibliography, write_bibliography)
from check_output import DEFECT, CheckReport, add_output_arguments, skipped_for_missing

TOOL = "reference-format-check"
CLASSES = {"missing-field": DEFECT, "unknown-type": DEFECT, "unknown-field": DEFECT,
           "repeated-field": DEFECT, "duplicate-key": DEFECT, "doi-not-bare": DEFECT,
           "isbn-not-13": DEFECT}
TITLE_CLASSES = {"book-not-italic": DEFECT, "paper-not-quoted": DEFECT}

REQUIRED_FIELDS = {
    "article": (("author",), ("title",), ("journal",)),
    "book": (("author", "editor"), ("title",), ("publisher",)),
    "booklet": (("title",),),
    "inbook": (("author", "editor"), ("title",), ("chapter", "pages"), ("publisher",)),
    "incollection": (("author",), ("title",), ("booktitle",), ("publisher",)),
    "inproceedings": (("author",), ("title",), ("booktitle",)),
    "conference": (("author",), ("title",), ("booktitle",)),
    "manual": (("title",),),
    "mastersthesis": (("author",), ("title",), ("school",)),
    "misc": (),
    "phdthesis": (("author",), ("title",), ("school",)),
    "proceedings": (("title",),),
    "techreport": (("author",), ("title",), ("institution",)),
    "unpublished": (("author",), ("title",), ("note",)),
}

BOOK_TYPES = ("book", "booklet", "manual", "proceedings", "phdthesis", "mastersthesis",
              "techreport")
PAPER_TYPES = ("article", "inproceedings", "conference", "incollection", "inbook",
               "unpublished")

BARE_DOI = re.compile(r"^10\.\d{4,9}/\S+$")
DOI_WRAPPING = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.I)


class Reference(NamedTuple):
    key: str
    title: str
    short_title: str
    ref_type: str


class Issue(NamedTuple):
    line_num: int
    title: str
    issue_type: str
    line_content: str


def isbn_digits(value):
    return re.sub(r"[\s-]", "", value or "").upper()


def isbn13_check_digit(first_twelve):
    total = sum(int(digit) * (1 if index % 2 == 0 else 3)
                for index, digit in enumerate(first_twelve))
    return str((10 - total % 10) % 10)


def isbn10_is_valid(digits):
    if not re.fullmatch(r"\d{9}[\dX]", digits):
        return False
    total = sum((10 - index) * (10 if digit == "X" else int(digit))
                for index, digit in enumerate(digits))
    return total % 11 == 0


def isbn13_is_valid(digits):
    return bool(re.fullmatch(r"\d{13}", digits)) and isbn13_check_digit(digits[:12]) == digits[12]


def standard_isbn(value):
    digits = isbn_digits(value)
    if isbn13_is_valid(digits):
        return digits
    if isbn10_is_valid(digits):
        first_twelve = "978" + digits[:9]
        return first_twelve + isbn13_check_digit(first_twelve)
    return None


def bare_doi(value):
    stripped = DOI_WRAPPING.sub("", (value or "").strip())
    return stripped if BARE_DOI.match(stripped) else None


def missing_fields(entry):
    needed = REQUIRED_FIELDS.get(entry.entry_type, ())
    return [" or ".join(choices) for choices in needed
            if not any(entry.field(name) for name in choices)]


def entry_findings(bibliography):
    found = []
    for key in bibliography.duplicate_keys:
        found.append((key, "duplicate-key", "two entries have this key; keep one"))
    for key, entry in bibliography.entries.items():
        where = f"line {entry.line}"
        if entry.entry_type not in REQUIRED_FIELDS:
            found.append((key, "unknown-type", f"{where}: @{entry.entry_type} is not a "
                                               f"standard BibTeX entry type"))
        for name in missing_fields(bibliography.with_inherited_fields(entry)):
            found.append((key, "missing-field", f"{where}: @{entry.entry_type} needs {name}"))
        for name in entry.fields:
            if name not in IDENTITY_FIELDS:
                found.append((key, "unknown-field", f"{where}: {name} is not an identity "
                                                    f"field; access and cache lines go in "
                                                    f"the sources list"))
        for name in entry.repeated_fields:
            found.append((key, "repeated-field", f"{where}: {name} is written twice"))
        doi = entry.field("doi")
        if doi and doi != bare_doi(doi):
            found.append((key, "doi-not-bare", f"{where}: doi {doi!r}; write "
                                               f"{bare_doi(doi) or 'the bare 10.x/y form'}"))
        isbn = entry.field("isbn")
        if isbn and isbn != standard_isbn(isbn):
            found.append((key, "isbn-not-13", f"{where}: isbn {isbn!r}; write "
                                              f"{standard_isbn(isbn) or '13 digits'}"))
    return found


def fix_entries(bibliography):
    changed = 0
    for entry in bibliography.entries.values():
        doi, isbn = entry.field("doi"), entry.field("isbn")
        if doi and bare_doi(doi) and bare_doi(doi) != doi:
            entry.fields["doi"] = bare_doi(doi)
            changed += 1
        if isbn and standard_isbn(isbn) and standard_isbn(isbn) != isbn:
            entry.fields["isbn"] = standard_isbn(isbn)
            changed += 1
    return changed


def references_from(bibliography) -> Dict[str, Reference]:
    references = {}
    for key, entry in bibliography.entries.items():
        title = entry.plain("title")
        if entry.entry_type in BOOK_TYPES:
            kind = "book"
        elif entry.entry_type in PAPER_TYPES:
            kind = "paper"
        else:
            continue
        if title and (kind == "book" or len(title) > 5):
            references[key] = Reference(key, title, get_short_title(title), kind)
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


def check_file(filepath, references: Dict[str, Reference], verbose: bool = False) -> List[Issue]:
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
    return [str(p) for p in paths if skip is None or Path(p).resolve() != skip]


FIXTURE_BIBLIOGRAPHY = '''@book{Ren11,
  author = {Rennie, A.},
  title = {Raised Beds: A Season-by-Season Guide},
  publisher = {Example Press},
  year = {2011},
  isbn = {9780000000064},
}

@inproceedings{Vas14,
  author = {Vasquez, E. N.},
  title = {Marshtalk},
  booktitle = {Proceedings of the Ninth Meeting on Regional Speech},
  year = {2014},
  doi = {https://doi.org/10.5555/vas14},
}

@article{Dun88,
  author = {Dunmore, F. E.},
  title = {Hedges for Exposed Coastal Farms},
  journal = {Journal of Examples},
  year = {1988},
  doi = {10.5555/dun88},
}

@article{Bry86a,
  author = {Bryce, N. T.},
  title = {Sowing Too Late in Cold Valleys},
  journal = {Journal of Examples},
  year = {1986},
}

@misc{Bry79,
  author = {Bryce, N. T.},
  title = {Notebook on ditch clearing, spring floods and the mending of banks},
  year = {1979},
}

@article{Lin91,
  author = {Lindqvist, K. A.},
  title = {The Fallow Year Rule},
  journal = {Farm Notes},
  year = {1991},
}

@book{Ash13,
  author = {Ashby, C.},
  title = {Deep Furrows: A Handbook of Market Garden Work},
  publisher = {Example Press},
  year = {2013},
  isbn = {0-306-40615-2},
}

@book{Pel10,
  author = {Pelham, G.},
  title = {The Herb Border},
  year = {2010},
  isbn = {9780000000089},
  urldate = {2024-01-01},
}

@online{Wal--,
  author = {Walsh, K.},
  title = {A living catalog},
  url = {https://catalog.example.org/},
}

@book{Ash13,
  author = {Ashby, C.},
  title = {A second entry under one key},
  publisher = {Example Press},
}
'''

FIXTURE_ENTRY_FINDINGS = {
    ("Ash13", "duplicate-key"),
    ("Vas14", "doi-not-bare"),
    ("Ash13", "isbn-not-13"),
    ("Pel10", "missing-field"),
    ("Pel10", "isbn-not-13"),
    ("Pel10", "unknown-field"),
    ("Wal--", "unknown-type"),
}

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

::: {#refs}

Bryce named the problem in Sowing Too Late in Cold Valleys in 1986.

He also wrote "The Layout of a Hill Pasture" that same year.

Notebook on ditch clearing, spring floods and the mending of banks is [@Bry79].
'''

FIXTURE_EXPECTED = {
    (3, 'book-not-italic', 'Deep Furrows'),
    (9, 'paper-not-quoted', 'Hedges for Exposed Coastal Farms'),
    (19, 'paper-not-quoted', 'The Fallow Year Rule'),
    (29, 'paper-not-quoted', 'Sowing Too Late in Cold Valleys'),
}


def self_test() -> int:
    failures = []

    def require(condition, message):
        if not condition:
            failures.append(message)

    bibliography = parse_bibliography(FIXTURE_BIBLIOGRAPHY)
    found = {(key, name) for key, name, _ in entry_findings(bibliography)}
    for item in sorted(FIXTURE_ENTRY_FINDINGS - found):
        failures.append("%s %s NOT REPORTED" % item)
    for item in sorted(found - FIXTURE_ENTRY_FINDINGS):
        failures.append("%s %s FALSE POSITIVE" % item)
    require(standard_isbn("0-306-40615-2") == "9780306406157", "an ISBN-10 was not converted")
    require(bare_doi("doi: 10.5555/x") == "10.5555/x", "a doi: label was not removed")
    require(fix_entries(bibliography) == 2, "the fixer should change one doi and one isbn")
    require(bibliography.entry("Vas14").field("doi") == "10.5555/vas14", "the doi was not bared")
    require(bibliography.entry("Ash13").field("isbn") == "9780306406157", "the isbn was not fixed")

    EPONYMOUS_TITLES.clear()
    EPONYMOUS_TITLES.update({'Marshtalk', 'Raised Beds'})
    references = references_from(bibliography)
    with tempfile.TemporaryDirectory() as root:
        chapter_path = Path(root, '110-chapter-1.md')
        chapter_path.write_text(FIXTURE_CHAPTER, encoding='utf-8')
        issues = check_file(chapter_path, references)
    EPONYMOUS_TITLES.clear()
    for key, expected_type in (('Ash13', 'book'), ('Ren11', 'book'), ('Dun88', 'paper'),
                               ('Vas14', 'paper'), ('Lin91', 'paper')):
        reference = references.get(key)
        require(reference is not None and reference.ref_type == expected_type,
                "%s should read as a %s: %s" % (key, expected_type, reference))
    require('Bry79' not in references and 'Wal--' not in references,
            "a misc or an unknown type has no title rule")
    found = {(issue.line_num, issue.issue_type, issue.title) for issue in issues}
    for item in sorted(FIXTURE_EXPECTED - found):
        failures.append("line %d %s %r NOT REPORTED" % item)
    for item in sorted(found - FIXTURE_EXPECTED):
        failures.append("line %d %s %r FALSE POSITIVE" % item)
    for line in failures:
        print(f"FAIL {line}")
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def check_bibliography(args, bibliography_path):
    report = CheckReport(TOOL, CLASSES)
    try:
        bibliography = read_bibliography(bibliography_path)
    except (OSError, BibliographyError) as error:
        return tool_failed("cannot read %s: %s" % (bibliography_path, error), TOOL)
    if args.fix:
        changed = fix_entries(bibliography)
        write_bibliography(bibliography_path, bibliography)
        if args.format == "text":
            print("fixed %d field(s) in %s" % (changed, bibliography_path))
    for key, name, message in entry_findings(bibliography):
        report.add(key, name, message)
    if args.format == "text":
        print("%d entries read\n" % len(bibliography.entries))
    return report.emit(args.format)


def check_titles(args, config, bibliography_path):
    report = CheckReport(TOOL + "-titles", TITLE_CLASSES)
    if args.target and not Path(args.target).exists():
        return tool_failed("not found: %s" % args.target, TOOL)
    names = (config.terms.watch_words or {}).get('titles_used_as_names') or []
    EPONYMOUS_TITLES.update(names if isinstance(names, list) else [names])
    files = prose_files(manuscript_paths(config, TOOL, args.target), config.manuscript.references)
    if not files:
        report.skip("no manuscript files at %s" % (args.target or config.manuscript.dir))
        return report.emit(args.format)
    try:
        references = references_from(read_bibliography(bibliography_path))
    except (OSError, BibliographyError) as error:
        return tool_failed("cannot read %s: %s" % (bibliography_path, error), TOOL)
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


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument('target', nargs='?',
                        help="with --titles, a file or folder (default: the book's manuscript files)")
    parser.add_argument('--bibliography', help='the .bib file (default: sources.bibliography)')
    parser.add_argument('--titles', action='store_true',
                        help='check how the prose writes the cited titles instead of the .bib')
    parser.add_argument('--fix', action='store_true',
                        help='write the fixes (the .bib, or with --titles the manuscript)')
    parser.add_argument('--verbose', action='store_true', help='print each fix')
    parser.add_argument('--self-test', action='store_true', help='run the built-in examples')
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    bibliography_path = args.bibliography or config.sources.bibliography
    if args.bibliography and not Path(bibliography_path).exists():
        return tool_failed("bibliography not found: %s" % bibliography_path, TOOL)
    if skipped_for_missing(TOOL, bibliography_path, "bibliography", args.format):
        return 0
    if args.titles:
        return check_titles(args, config, bibliography_path)
    return check_bibliography(args, bibliography_path)


if __name__ == '__main__':
    sys.exit(main())
