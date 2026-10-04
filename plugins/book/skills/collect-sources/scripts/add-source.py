#!/usr/bin/env python3
"""Add a new source to the book: its identity to the .bib file, its access to the sources list.

A source lives in two places, and each holds one kind of fact:

    sources.bibliography (.bib)   who wrote it, the title, the year, the venue, DOI, ISBN
    sources.list (list.md)        where it can be read: access URLs, access status, note

This script writes both in one step, so they never disagree about the key. The key is the
BibTeX alpha label the entry's names and year give (lib/citation_key.py). With no --key the
script derives it; a --key that disagrees with the names is refused, except for one trailing
lower-case letter that tells apart two works with the same label (Smi99a, Smi99b).

It refuses a key already in the .bib file or in the list, an entry with no author or editor
(it would have no label to check), and a key that is not a plain file name. When the names
give no label because they hold no Latin letters (a name written only in another script),
it takes a --key that is a plain file name, and refuses without one.

It also refuses an entry type that is not letters only, a field name that is not a BibTeX
name, a value whose braces do not pair up, and an entry that does not read back as written.

Dry run by default: it prints the .bib entry and the list entry it would write. --fix writes
them, the .bib first: the .bib entry is sorted in by key and the file is written in its
standard form; the list entry goes in at its sorted place.

Usage:
  add-source.py --type book --field "author=Hale, Ruth" --field "title=Bread at Home" \\
                --field year=2019 --field "publisher=Example Press" \\
                --access-url https://example.org/hale --fix
  add-source.py --key Hal19a --type article --field ... --access-status "MANUAL FETCH REQUIRED"
  add-source.py --self-test
"""

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import script_tests
from bibliography import (Bibliography, BibliographyError, expected_key, format_entry,
                          make_entry, parse_bibliography, read_bibliography, write_bibliography)
from citation_key import UnkeyableName, is_safe_file_key, strip_disambiguator
from proposed_entries import header_intact, insert
from source_files import add_config_arguments, load_book, tool_failed
from source_registry import read_bank

TOOL = "add-source"

LIST_HEADER = """# Sources List

## Entry format

```
### [<Key>]

**Access URLs:** where the source can be read
**Access status:** what stops a download, in upper case, when something does
```
"""


class Refused(Exception):
    pass


def fields_from(pairs):
    fields = {}
    for pair in pairs or []:
        name, separator, value = pair.partition("=")
        if not separator or not name.strip():
            raise Refused("--field takes NAME=VALUE, not %r" % pair)
        fields[name.strip().lower()] = value.strip()
    return fields


def chosen_key(entry, wanted):
    try:
        label = expected_key(entry)
    except UnkeyableName as error:
        if wanted and is_safe_file_key(wanted):
            return wanted
        raise Refused("%s; choose a key and pass it with --key (letters, digits and + _ . - "
                      "only)" % error)
    except ValueError as error:
        raise Refused(str(error))
    if label is None:
        raise Refused("the entry has no author or editor, so it has no alpha label; add one "
                      "(a corporate author goes in double braces: {{Example Guild}})")
    if not wanted:
        return label
    if strip_disambiguator(wanted) != label:
        raise Refused("the names and year give the key %s, not %s" % (label, wanted))
    return wanted


def list_entry(key, access_urls, access_status, note):
    lines = ["### [%s]" % key, ""]
    for name, value in (("Access URLs", ", ".join(access_urls or [])),
                        ("Access status", access_status), ("Note", note)):
        if value:
            lines.append("**%s:** %s" % (name, value))
    return "\n".join(lines)


def plan(options, bibliography_path, list_path):
    entry = make_entry(options.type, "", fields_from(options.field))
    entry.key = chosen_key(entry, options.key)
    if not is_safe_file_key(entry.key):
        raise Refused("%r is not a plain file name: use letters, digits and + _ . - only"
                      % entry.key)
    bibliography = read_bibliography(bibliography_path) if Path(bibliography_path).is_file() \
        else Bibliography()
    if entry.key in bibliography.entries:
        raise Refused("%s is already in %s; a second work with the same label takes a letter "
                      "(%sa, %sb)" % (entry.key, bibliography_path, entry.key, entry.key))
    if Path(list_path).is_file() and entry.key in read_bank(list_path).keys:
        raise Refused("%s is already in the sources list" % entry.key)
    reads_back_as_written(entry)
    bibliography.add(entry)
    return entry, bibliography, list_entry(entry.key, options.access_url, options.access_status,
                                           options.note)


def reads_back_as_written(entry):
    read_back = parse_bibliography(format_entry(entry)).entries
    found = read_back.get(entry.key)
    if len(read_back) != 1 or found is None or found.entry_type != entry.entry_type \
            or found.fields != entry.fields:
        raise Refused("the entry does not read back as written; check the field values")


def list_text(list_path):
    text = Path(list_path).read_text(encoding="utf-8") if Path(list_path).is_file() \
        else LIST_HEADER
    if not header_intact(text):
        raise Refused("the sources list header looks damaged (no `## Entry format` block with "
                      "a `<Key>` example); repair it first")
    return text


def write_list_entry(list_path, text, key, body):
    Path(list_path).parent.mkdir(parents=True, exist_ok=True)
    Path(list_path).write_text(insert(text, key, body), encoding="utf-8")


def run(options, config):
    bibliography_path = config.sources.bibliography
    list_path = config.sources.list
    try:
        entry, bibliography, body = plan(options, bibliography_path, list_path)
    except (Refused, BibliographyError) as reason:
        print("REFUSED  %s" % reason)
        return 1
    print("%s  <- the .bib entry\n" % bibliography_path)
    print(format_entry(entry))
    print("\n%s  <- the sources-list entry\n" % list_path)
    print(body)
    if not options.fix:
        print("\ndry run: pass --fix to write both")
        return 0
    try:
        text = list_text(list_path)
    except Refused as reason:
        print("REFUSED  %s" % reason)
        return 1
    Path(bibliography_path).parent.mkdir(parents=True, exist_ok=True)
    write_bibliography(bibliography_path, bibliography)
    write_list_entry(list_path, text, entry.key, body)
    print("\nadded %s to both files" % entry.key)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0], epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    parser.add_argument("--type", default="misc",
                        help="the BibTeX entry type: book, article, inproceedings, incollection, "
                             "techreport, phdthesis, misc ... (default misc)")
    parser.add_argument("--field", action="append", metavar="NAME=VALUE",
                        help="one BibTeX field (repeatable): author, editor, title, year, "
                             "journal, booktitle, publisher, doi, isbn, url ...")
    parser.add_argument("--key", help="the key; default: the alpha label the names give")
    parser.add_argument("--access-url", action="append", metavar="URL",
                        help="where the source can be read (repeatable)")
    parser.add_argument("--access-status", help="for example MANUAL FETCH REQUIRED (gate)")
    parser.add_argument("--note", help="a note for the sources list")
    parser.add_argument("--fix", action="store_true", help="write both files; otherwise a dry run")
    parser.add_argument("--self-test", action="store_true", help="run the tests on fixtures")
    options = parser.parse_args()
    if options.self_test:
        return script_tests.run_self_test(__file__, "test_add_source.py")
    return run(options, load_book(options, TOOL))


if __name__ == "__main__":
    sys.exit(main())
