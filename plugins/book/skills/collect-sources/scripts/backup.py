#!/usr/bin/env python3
"""Copy the cached source files that cannot be downloaded again into the private backup.

The cache (`sources.library`) is not in git. restore.py rebuilds most of it from the
recorded URLs and DOIs, but some files have no route back: a file a person downloaded
behind a check for a person, a source with no open copy that was bought or borrowed, a
book known only by its ISBN, an OCR text whose exact characters no second OCR run will
reproduce, and anything whose host has since gone. Those live in a private backup
folder, set as `sources.backup` in book.yaml (outside the repository; never public,
because the files belong to their publishers).

A key's files need the backup when any of these holds:
  * its Access status says MANUAL FETCH REQUIRED, NO OPEN-ACCESS COPY or READABLE VIA OCR
  * its .txt starts with an OCR-PROVENANCE header, or it has an OCR origin record
  * it has no download route: no `from <URL>` on its Cached original line, no cached
    fetch record with a URL, and no DOI (a manual download records "manual download")
With --all every cached file is copied.

Each copy is checked by sha256; an identical copy is skipped. A `manifest.tsv` in the
backup folder lists name, sha256, bytes and the reason, so the backup can be checked
without the book.

Classes:
  to-back-up     INFORMATIONAL  dry run: this file would be copied
  backed-up      INFORMATIONAL  copied (or replaced, when the cache changed)
  not-cached     DEFECT         the list names a file for backup that is not in the cache

Dry run by default; --fix writes. Exit 2 when sources.backup is not set.

Usage:
  backup.py
  backup.py --fix
  backup.py --fix --all
  backup.py --self-test
"""

import argparse
import hashlib
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from bibliography import read_identities
from source_files import (FETCH, OCR, SourceFolders, add_config_arguments, cache_references,
                          folders_from_config, load_book, tool_failed)
from check_output import DEFECT, INFORMATIONAL, CheckReport, add_output_arguments
from source_registry import read_bank

TOOL = "backup"
CLASSES = {"to-back-up": INFORMATIONAL, "backed-up": INFORMATIONAL, "not-cached": DEFECT}
MANIFEST = "manifest.tsv"

GATED = re.compile(r"MANUAL FETCH REQUIRED|NO OPEN-ACCESS COPY|READABLE VIA OCR", re.I)
FROM_URL = re.compile(r"from (https?://\S+?)\)?\s*$")
DOI = re.compile(r"^10\.\d{4,9}/\S+$")


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def cached_names(entry, folders):
    names = []
    for label in ("Cached text", "Cached original"):
        value = entry.field(label) or ""
        if "NOT YET FETCHED" in value:
            continue
        names.extend(reference[2] for reference in cache_references(folders, value))
    return list(dict.fromkeys(names))


def has_download_route(entry, folders, identity=None):
    original = entry.field("Cached original") or ""
    if FROM_URL.search(original.strip()):
        return True
    record = folders.read_origin_record(entry.key, FETCH) or {}
    if record.get("status") == "cached" and str(record.get("url", "")).startswith("http"):
        return True
    doi = identity.field("doi") if identity is not None else None
    return bool(DOI.match((doi or "").strip()))


def is_ocr(entry, folders):
    if folders.has_origin_record(entry.key, OCR):
        return True
    text = folders.file(entry.key + ".txt")
    if text.exists():
        with open(text, errors="ignore", encoding="utf-8") as handle:
            return "OCR-PROVENANCE" in handle.read(800)
    return False


def backup_reason(entry, folders, everything, identity=None):
    status = entry.field("Access status") or ""
    gate = GATED.search(status)
    if gate:
        return "Access status: %s" % gate.group(0).upper()
    if is_ocr(entry, folders):
        return "OCR text"
    if not has_download_route(entry, folders, identity):
        return "no download route"
    return "every file (--all)" if everything else None


def sidecar_names(entry, folders):
    if folders.merged_origin:
        return []
    return [path.name for path in (folders.origin_record_path(entry.key, FETCH),
                                   folders.origin_record_path(entry.key, OCR)) if path.exists()]


def plan(entries, folders, everything, identities=None):
    rows = []
    for entry in entries:
        names = cached_names(entry, folders)
        if not names:
            continue
        reason = backup_reason(entry, folders, everything, (identities or {}).get(entry.key))
        if not reason:
            continue
        for name in names + sidecar_names(entry, folders):
            rows.append((entry.key, name, reason))
    return rows


def write_manifest(backup, rows):
    lines = ["name\tsha256\tbytes\treason"]
    for _key, name, reason in sorted(rows, key=lambda row: row[1]):
        copy = Path(backup) / name
        if copy.is_file():
            lines.append("%s\t%s\t%d\t%s" % (name, sha256_of(copy), copy.stat().st_size, reason))
    (Path(backup) / MANIFEST).write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(rows, folders, backup, write, report):
    kept = []
    for key, name, reason in rows:
        source = folders.file(name)
        if not source.exists():
            report.add(key, "not-cached", "%s is named in the list but missing from the cache" % name)
            continue
        target = Path(backup) / name
        if target.is_file() and sha256_of(target) == sha256_of(source):
            kept.append((key, name, reason))
            continue
        if write:
            Path(backup).mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            report.add(key, "backed-up", "%s (%s)" % (name, reason))
            kept.append((key, name, reason))
        else:
            report.add(key, "to-back-up", "%s (%s)" % (name, reason))
    if write:
        write_manifest(backup, kept)


FIXTURE_LIST = """# Sources List

## Entry format

```
### [<Key>]
```

### [Gat70]

**Access status:** MANUAL FETCH REQUIRED (gate)
**Cached text:** `sources/library/Gat70.txt` (fetched 2025-01-01)
**Cached original:** `sources/library/Gat70.pdf` (fetched 2025-01-01, from manual download)

---

### [Web05]

**Cached text:** `sources/library/Web05.txt` (fetched 2025-01-01)
**Cached original:** `sources/library/Web05.html` (fetched 2025-01-01, from https://example.org/w)

---

### [Scn80]

**Cached text:** `sources/library/Scn80.txt` (fetched 2025-01-01)

---

### [Doi90]

**Cached text:** `sources/library/Doi90.txt` (fetched 2025-01-01)

---
"""

FIXTURE_BIBLIOGRAPHY = """@article{Scn80,
  author = {Scan, Sam},
  title = {An OCR text},
  year = {1980},
  doi = {10.5555/scn80},
}

@article{Doi90,
  author = {Doe, Dee},
  title = {A paper with a DOI},
  year = {1990},
  doi = {10.5555/doi90},
}
"""


def self_test():
    failures = []
    with tempfile.TemporaryDirectory() as root:
        root = Path(root)
        files = root / "sources" / "library"
        files.mkdir(parents=True)
        for name, body in (("Gat70.txt", "gated text"), ("Gat70.pdf", "%PDF gated"),
                           ("Web05.txt", "web text"), ("Web05.html", "<html></html>"),
                           ("Scn80.txt", "=== OCR-PROVENANCE ===\nscan"),
                           ("Doi90.txt", "a text that can be downloaded again")):
            (files / name).write_text(body, encoding="utf-8")
        (root / "list.md").write_text(FIXTURE_LIST, encoding="utf-8")
        (root / "references.bib").write_text(FIXTURE_BIBLIOGRAPHY, encoding="utf-8")
        folders = SourceFolders(root=root, files=files, origin=root / "sources" / "library-index")
        entries = read_bank(root / "list.md").entries
        identities = read_identities(root / "references.bib")
        rows = plan(entries, folders, False, identities)
        names = sorted(name for _key, name, _reason in rows)
        if names != ["Gat70.pdf", "Gat70.txt", "Scn80.txt"]:
            failures.append("wrong files chosen for backup: %s" % names)
        backup = root / "backup"
        run(rows, folders, backup, True, CheckReport(TOOL, CLASSES))
        if not (backup / "Gat70.pdf").exists() or not (backup / MANIFEST).exists():
            failures.append("the backup or its manifest was not written")
        second = CheckReport(TOOL, CLASSES)
        run(rows, folders, backup, True, second)
        if second.items:
            failures.append("an identical copy was written again: %s" % second.items)
        if "Doi90.txt" not in [name for _k, name, _r in plan(entries, folders, False)]:
            failures.append("without the .bib a DOI is unknown, so the file needs a backup")
        everything = sorted(name for _k, name, _r in plan(entries, folders, True, identities))
        if "Web05.html" not in everything:
            failures.append("--all must include downloadable files")
    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("--keys", help="comma-separated keys (default: every entry)")
    parser.add_argument("--all", action="store_true", help="back up every cached file")
    parser.add_argument("--fix", action="store_true", help="write the copies")
    parser.add_argument("--self-test", action="store_true", help="run the built-in examples")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    if not config.sources.backup:
        return tool_failed("no backup folder: set sources.backup in book.yaml "
                           "(or pass --set sources.backup=PATH)", TOOL)
    sources_list = config.sources.list
    if not sources_list or not Path(sources_list).is_file():
        return tool_failed("sources list not found: %s" % sources_list, TOOL)
    folders = folders_from_config(config)
    wanted = {k.strip() for k in args.keys.split(",")} if args.keys else None
    entries = [e for e in read_bank(sources_list).entries if wanted is None or e.key in wanted]
    report = CheckReport(TOOL, CLASSES)
    identities = read_identities(config.sources.bibliography)
    run(plan(entries, folders, args.all, identities), folders, config.sources.backup, args.fix,
        report)
    if args.format == "text":
        print("backup folder: %s%s\n" % (config.sources.backup, "" if args.fix else " (dry run)"))
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
