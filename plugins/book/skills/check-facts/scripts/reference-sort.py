#!/usr/bin/env python3
"""Sort the bibliography entries alphabetically by citation key.

Each entry is one line starting with its key: `[Key] Author, ... (year). Title...`.
Entries sort by the key, case-insensitively (a key with a lower-case particle, like
`[vB99]`, sorts under v, not after every upper-case key). The order rule is shared with
the source banks (lib/citation_key.sort_position), so a key has one place in all three.

The header (everything up to and including the `# References` line and the blank line
after it) is kept verbatim; every entry's text is kept exactly; exactly one blank line
separates entries; the file ends with one newline.

A rewrite must never silently drop what it cannot parse: a body line that is not an
entry, or a file with no `# References` heading, stops the run instead.

Classes:
  out-of-order   DEFECT  an entry is not at its sorted position (--fix sorts)

Usage:
  reference-sort.py                     dry run over manuscript.references
  reference-sort.py --fix
  reference-sort.py <file> --fix
  reference-sort.py --self-test
"""

import argparse
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import add_config_arguments, load_book, tool_failed
from check_output import DEFECT, CheckReport, add_output_arguments, skipped_for_missing
from citation_key import bib_entry, sort_position

TOOL = "reference-sort"
CLASSES = {"out-of-order": DEFECT}

HEADING_PATTERN = re.compile(r'^#\s*References\s*$')


def entry_key(line):
    found = bib_entry(line, any_key=True)
    return found[0] if found else None


def split_header_and_body(content):
    lines = content.split('\n')
    for index, line in enumerate(lines):
        if HEADING_PATTERN.match(line):
            header_end = index + 1
            if header_end < len(lines) and lines[header_end].strip() == '':
                header_end += 1
            header = '\n'.join(lines[:header_end])
            body = '\n'.join(lines[header_end:])
            return header, body
    raise ValueError("Could not find '# References' heading line.")


def parse_entries(body):
    entries = []
    for raw_line in body.split('\n'):
        line = raw_line.rstrip('\r')
        if line.strip() == '':
            continue
        if entry_key(line) is None:
            raise ValueError(f"Line does not start with a citation key: {line[:60]!r}")
        entries.append(line)
    return entries


def sort_key(entry_line):
    return sort_position(entry_key(entry_line))


def build_output(header, sorted_entries):
    body = '\n\n'.join(sorted_entries)
    return header + '\n' + body + '\n'


FIXTURE = '''```{=latex}
\\backmatter
\\bookmarksetup{startatroot}
```

# References

[Wal26] Walsh, K. (2026). A living catalog. https://catalog.example.org/ Last modified August 5, 2026.

[Hal93b] Hallam, R.J. (1993). More Notes on Winter Pruning. *Orchard Quarterly*, 4(4), 61-70.

[dB81] de Bruin, M.L. (1981). *Barley Through the Year*. Example Press.

[Hal93a] Hallam, R.J. (1993). Notes on Winter Pruning. *Orchard Quarterly*, 4(2), 22-29.

[AMHJ22] Abel, C., Moss-Hill, E., Cole, M., & Jones, C. (2022). What helps? *A Conference 2022*.

[Wal--] Walsh, K. (--). A page whose date could not be established.
'''

EXPECTED_ORDER = ["AMHJ22", "dB81", "Hal93a", "Hal93b", "Wal--", "Wal26"]

FIXTURE_NO_HEADING = '[Hal93a] Hallam, R.J. (1993). Notes on Winter Pruning.\n'

FIXTURE_STRAY_LINE = '''# References

[Hal93a] Hallam, R.J. (1993). Notes on Winter Pruning.

Note: this line is not an entry and must stop the run rather than be dropped.
'''


def self_test():
    failures = []

    def require(condition, message):
        if not condition:
            failures.append(message)

    header, body = split_header_and_body(FIXTURE)
    entries = parse_entries(body)
    sorted_entries = sorted(entries, key=sort_key)
    output = build_output(header, sorted_entries)

    print("== sort order")
    order = [entry_key(entry) for entry in sorted_entries]
    require(order == EXPECTED_ORDER, "wrong order: %s" % order)
    print("  " + " ".join(order))
    require(sort_key('[dB81] de Bruin') == 'db81', "the sort key is not case-insensitive")
    require(order.index("dB81") < order.index("Hal93a"),
            "[dB81] must sort by 'db81', not after every uppercase key")
    require(order.index("Wal--") < order.index("Wal26"),
            "the dateless [Wal--] must sort before [Wal26]")

    print("\n== header and shape")
    require(header == '```{=latex}\n\\backmatter\n\\bookmarksetup{startatroot}\n```\n\n# References\n',
            "the raw-LaTeX header before '# References' was not preserved verbatim: %r" % header)
    require(output.startswith(header + '\n'), "the header did not survive into the output")
    require(output.endswith('\n') and not output.endswith('\n\n'),
            "the file must end with exactly one newline")
    require('\n\n\n' not in output, "entries must be separated by exactly one blank line")
    require(set(entries) == set(sorted_entries) and len(entries) == 6,
            "an entry was lost or duplicated")
    require(all(entry in output for entry in entries),
            "an entry's text was altered rather than merely moved")
    print("  header verbatim, one blank line between entries, one trailing newline")

    print("\n== idempotence")
    second_header, second_body = split_header_and_body(output)
    again = build_output(second_header, sorted(parse_entries(second_body), key=sort_key))
    require(again == output, "sorting the sorted output changed it")
    print("  sorting the output again is a no-op")

    print("\n== refusals (a rewrite must never silently drop what it cannot parse)")
    for text, label in ((FIXTURE_NO_HEADING, "no '# References' heading"),
                        (FIXTURE_STRAY_LINE, "a body line that is not an entry")):
        try:
            head, rest = split_header_and_body(text)
            parse_entries(rest)
            failures.append("%s: accepted instead of raising" % label)
        except ValueError:
            print("  refused: %s" % label)

    print()
    for line in failures:
        print(f"FAIL {line}")
    print("self-test: %d entries, %d discrepancies" % (len(entries), len(failures)))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("file", nargs="?", help="the bibliography (default: manuscript.references)")
    parser.add_argument("--fix", action="store_true", help="rewrite the file in sorted order")
    parser.add_argument("--self-test", action="store_true", help="run the built-in examples")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    path = args.file or load_book(args, TOOL).manuscript.references
    if args.file and not Path(path).is_file():
        return tool_failed("bibliography not found: %s" % path, TOOL)
    if skipped_for_missing(TOOL, path, "bibliography", args.format):
        return 0
    content = Path(path).read_text(encoding="utf-8")
    try:
        header, body = split_header_and_body(content)
        entries = parse_entries(body)
    except ValueError as error:
        return tool_failed(str(error), TOOL)
    sorted_entries = sorted(entries, key=sort_key)

    report = CheckReport(TOOL, CLASSES)
    if args.fix:
        new_content = build_output(header, sorted_entries)
        if new_content != content:
            Path(path).write_text(new_content, encoding="utf-8")
            print("wrote the sorted bibliography to %s\n" % path)
    else:
        for index, (entry, wanted) in enumerate(zip(entries, sorted_entries)):
            if entry != wanted:
                report.add(entry_key(entry), "out-of-order",
                           "at position %d, belongs at %d" % (index, sorted_entries.index(entry)))
    if args.format == "text":
        print("entries: %d\n" % len(entries))
    return report.emit(args.format)


if __name__ == '__main__':
    sys.exit(main())
