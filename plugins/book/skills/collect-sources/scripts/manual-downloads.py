#!/usr/bin/env python3
"""List the sources a person still has to download by hand, and write needed.txt.

Some sources are free and still cannot be fetched by a script: the host answers with a
check meant for a person (a checkbox, a bot challenge). That check is not something
to work around, so those entries carry `MANUAL FETCH REQUIRED` in the sources list and
wait for someone to click.

The list is derived from the sources list every time, never kept beside it: a second
hand-kept file drifts the moment an entry changes, and a stale download list sends the
reader to fetch something already cached.

Four groups:

    MANUAL FETCH REQUIRED   free, but behind a check for a person -> download by hand
    NO OPEN-ACCESS COPY     no free copy exists -> needs a library or a purchase
    fetch failed            the last fetch was refused (paywalled, blocked, too short)
    preprint only           a file is cached, but it is the preprint; the reviewed
                            paper of record was never opened

The title, authors, year, DOI and ISBN shown for each source come from its entry in the
book's .bib file (`sources.bibliography`); the URLs and the status from the sources list.

Anything already cached drops off, so the list empties itself as files arrive. With
--fix the first three groups are written to `needed.txt` in the sources-to-add folder,
where the author saves the files under any name (see match-added-files.py). This is a
worklist, not a check: it always exits 0.

Usage:
  manual-downloads.py                  human-readable, grouped
  manual-downloads.py --format urls    bare URLs, one per line
  manual-downloads.py --format tsv     key<TAB>url<TAB>file name
  manual-downloads.py --fix            also write needed.txt
  manual-downloads.py --self-test
"""

import argparse
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import (FETCH, add_config_arguments, folders_for_directory,
                          folders_from_config, load_book, shown_path, tool_failed)
from sources_to_add import collect, needed_items, needed_keys, to_add_folder, write_needed
from check_output import skipped_for_missing

TOOL = "manual-downloads"


def wrap(text, width, indent):
    words, lines, current = text.split(), [], ""
    for word in words:
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = (current + " " + word).strip()
    if current:
        lines.append(current)
    return ("\n" + indent).join(lines)


def block_for(item, want_filename):
    pad = " " * 14
    out = ["  %-11s %s" % (item["key"], wrap(item["title"] or "(title not recorded)", 60, pad))]
    if item["authors"]:
        out.append("%s%s" % (pad, wrap(item["authors"], 60, pad)))
    line = " | ".join(x for x in (item["year"], item["venue"]) if x)
    if line:
        out.append("%s%s" % (pad, wrap(line, 60, pad)))
    ids = " | ".join(x for x in ("DOI: " + item["doi"] if item["doi"] else "",
                                 "ISBN: " + item["isbn"] if item["isbn"] else "") if x)
    if ids:
        out.append("%s%s" % (pad, ids))
    if want_filename:
        out.append("%ssave as: %s.pdf" % (pad, item["key"]))
    if item["access_raw"]:
        out.append("%swhere: %s" % (pad, wrap(item["access_raw"], 58, pad + "       ")))
    elif item["doi"]:
        out.append("%swhere: https://doi.org/%s" % (pad, item["doi"]))
    out.append("")
    return out


def render(groups, fmt, list_shown, to_add_shown):
    manual, no_oa, fetch_failed, preprint_only = groups
    if fmt == "urls":
        return "\n".join(i["urls"][0] for i in manual if i["urls"])
    if fmt == "tsv":
        return "\n".join("%s\t%s\t%s.pdf" % (i["key"], i["urls"][0], i["key"])
                         for i in manual if i["urls"])

    out = [
        "Sources waiting for a manual download.",
        "",
        "Made from %s -- do not edit by hand; run the script again instead." % list_shown,
        "An entry leaves this list once the paper of record is cached.",
        "",
        "=" * 72,
        "FREE, BUT BEHIND A CHECK FOR A PERSON (%d)" % len(manual),
        "=" * 72,
        "",
        "  Free to get. The host answers scripts with a check meant for a person,",
        "  so these need a browser and a click. Save each under the name shown,",
        "  into %s/; the next download run files it (match-added-files.py)." % to_add_shown,
        "",
    ]
    for item in manual:
        out += block_for(item, want_filename=True)

    if no_oa:
        out += [
            "=" * 72,
            "NO FREE COPY FOUND (%d)" % len(no_oa),
            "=" * 72,
            "",
            "  Checked against Unpaywall and the open repositories; no free full text",
            "  turned up. These need a library, institutional access, or a purchase.",
            "",
        ]
        for item in no_oa:
            out += block_for(item, want_filename=True)
    if fetch_failed:
        out += [
            "=" * 72,
            "THE LAST FETCH WAS REFUSED (%d)" % len(fetch_failed),
            "=" * 72,
            "",
            "  A script fetch came back paywalled, blocked or too short. Try the routes in",
            "  references/fetching.md, or download by hand.",
            "",
        ]
        for item in fetch_failed:
            out += block_for(item, want_filename=False)
    if preprint_only:
        out += [
            "=" * 72,
            "REVIEWED VERSION NOT READ, PREPRINT CACHED (%d)" % len(preprint_only),
            "=" * 72,
            "",
            "  A file exists, so these look done, but the cached text is the PREPRINT.",
            "  The reviewed paper of record was never opened, and any quote or number",
            "  from these came from a draft. Decide per entry with the author: reach it",
            "  another way, buy it, or accept the preprint knowingly.",
            "",
        ]
        for item in preprint_only:
            out += block_for(item, want_filename=False)

    return "\n".join(out)


FIXTURE = """# Sources List

## Entry format

```
### [<Key>]
```

### [Aaa70]

**Access URLs:** https://dl.example.org/doi/pdf/10.0000/aaa70
**Access status:** MANUAL FETCH REQUIRED (gate)

---

### [Bbb71]

**Access status:** MANUAL FETCH REQUIRED (gate)

---

### [Ccc72]

**Access status:** NO OPEN-ACCESS COPY

---

### [Ddd26]

**Access status:** READABLE
**Note:** verified against the preprint only

---

### [Eee73]

**Note:** the fetch was refused

---
"""

FIXTURE_BIBLIOGRAPHY = """@article{Aaa70,
  author = {Adams, Ann},
  title = {A gated paper},
  year = {1970},
}

@article{Bbb71,
  author = {Baker, Bob},
  title = {A gated paper that is already cached},
  year = {1971},
}

@book{Ccc72,
  author = {Clark, Cat},
  title = {A closed book},
  year = {1972},
  isbn = {9780000000002},
}

@article{Ddd26,
  author = {Davis, Dan},
  title = {A paper read only as a preprint},
  year = {2026},
}

@article{Eee73,
  author = {Evans, Eve},
  title = {A paper the fetch could not get},
  year = {1973},
  doi = {10.0000/eee73},
}
"""


def self_test():
    failures = []
    with tempfile.TemporaryDirectory() as root:
        files = Path(root) / "files"
        files.mkdir()
        (files / "Bbb71.txt").write_text("cached\n", encoding="utf-8")
        list_path = Path(root) / "list.md"
        list_path.write_text(FIXTURE, encoding="utf-8")
        bibliography_path = Path(root) / "references.bib"
        bibliography_path.write_text(FIXTURE_BIBLIOGRAPHY, encoding="utf-8")
        folders = folders_for_directory(files)
        folders.write_origin_record("Eee73", FETCH, {"status": "paywalled"})
        manual, no_oa, fetch_failed, preprint_only = collect(list_path, folders, bibliography_path)
        groups = (manual, no_oa, fetch_failed, preprint_only)
        text = render(groups, "text", "list.md", "sources-to-add")
        tsv = render(groups, "tsv", "list.md", "sources-to-add")
        to_add = Path(root) / "sources-to-add"
        written = write_needed(to_add, needed_items(list_path, folders, bibliography_path)
                               ).read_text(encoding="utf-8")
        keys = needed_keys(to_add)
    checks = [
        ([i["key"] for i in manual] == ["Aaa70"], "only the uncached gated entry is listed"),
        ([i["key"] for i in no_oa] == ["Ccc72"], "the closed entry is listed apart"),
        ([i["key"] for i in preprint_only] == ["Ddd26"], "the preprint-only entry is listed"),
        (tsv == "Aaa70\thttps://dl.example.org/doi/pdf/10.0000/aaa70\tAaa70.pdf", "tsv line"),
        ("ISBN: 9780000000002" in text, "the ISBN is shown for a library request"),
        ([i["key"] for i in fetch_failed] == ["Eee73"], "the refused fetch is listed"),
        (keys == ["Aaa70", "Ccc72", "Eee73"], "needed.txt holds what is still missing"),
        ("Aaa70 | A gated paper | Adams, Ann | 1970 | https://dl.example.org/doi/pdf/10.0000/aaa70"
         in written, "a needed.txt line holds title, authors, year and link from the .bib"),
    ]
    for passed, label in checks:
        if not passed:
            failures.append(label)
    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0], epilog="A worklist: always exits 0 unless it cannot run.")
    add_config_arguments(parser)
    parser.add_argument("--list", dest="sources_list",
                        help="the sources list (default: sources.list)")
    parser.add_argument("--format", choices=("text", "urls", "tsv"), default="text")
    parser.add_argument("--fix", action="store_true",
                        help="also write needed.txt into the sources-to-add folder")
    parser.add_argument("--self-test", action="store_true", help="run on a built-in example")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    list_path = args.sources_list or config.sources.list
    if args.sources_list and not Path(list_path).exists():
        return tool_failed("sources list not found: %s" % list_path, TOOL)
    if skipped_for_missing(TOOL, list_path, "sources list"):
        return 0

    folders = folders_from_config(config)
    to_add = to_add_folder(config)
    bibliography_path = config.sources.bibliography
    groups = collect(list_path, folders, bibliography_path)
    print(render(groups, args.format, shown_path(config.root, list_path),
                 shown_path(config.root, to_add)))
    if args.fix:
        written = write_needed(to_add, needed_items(list_path, folders, bibliography_path))
        print("wrote %s (%d sources)" % (shown_path(config.root, written), len(needed_keys(to_add))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
