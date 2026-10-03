#!/usr/bin/env python3
"""Rebuild the cache of source files after a fresh checkout, and say what could not be rebuilt.

The cache (`sources.library`) is kept out of git: the files are large and many belong to
publishers. The sources list keeps what is needed to get each one back: the file names,
their sha256, the URL each original came from, the DOI and the ISBN. This script reads
those lines and restores every missing file, in this order:

  1. the private backup (`sources.backup` in book.yaml): exact bytes, no network. This
     is the only route for files that cannot be downloaded again (a manual download
     behind a check for a person, a scan, a bought copy); backup.py writes it
  2. the network: the `from <URL>` of the Cached original line, then the URL in the
     fetch record, then the DOI through doi.org. The downloaded original must match the
     recorded sha256. An HTML page can differ byte for byte while saying the same thing
     (hosts embed per-request tokens), so a differing HTML original is accepted when
     its rebuilt extraction matches the recorded text sha256

A file whose downloaded bytes match neither hash is NOT written: the source changed
since it was read, which is a finding for the run report, never something to paper over.
A book with only an ISBN cannot be downloaded; it needs the backup.

Classes:
  restored            INFORMATIONAL  written, and its hash matches the list
  would-restore       INFORMATIONAL  dry run: this route would be tried
  text-rebuilt        ADVISORY       the original matched but the rebuilt .txt differs from
                                     the recorded text hash (a different extractor
                                     version, or an OCR text that needs ocr.py); check it,
                                     then run files-hash-check.py --fix
  not-restored        DEFECT         nothing could restore it: the reason says why (no
                                     backup and no URL, download failed, content changed)

Dry run by default; --fix writes. Network routes need curl and pdftotext (SKIPPED for
the network part when missing; the backup route still runs).

Usage:
  restore.py                         what is missing, and how each would come back
  restore.py --fix
  restore.py --fix --keys Smi99,Jon01
  restore.py --fix --backup-only
  restore.py --self-test
"""

import argparse
import functools
import hashlib
import http.server
import re
import shutil
import sys
import tempfile
import threading
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import (FETCH, SourceFolders, add_config_arguments, cache_references,
                          folders_from_config, load_book, tool_failed)
from check_output import (ADVISORY, DEFECT, INFORMATIONAL, CheckReport, add_output_arguments,
                          skipped_for_missing)
from source_registry import read_bank
import fetch

TOOL = "restore"
CLASSES = {"restored": INFORMATIONAL, "would-restore": INFORMATIONAL,
           "text-rebuilt": ADVISORY, "not-restored": DEFECT}

SHA = re.compile(r"sha256[: ]+([0-9a-f]{64})")
FROM_URL = re.compile(r"from (\S+?)\)?\s*$")
DOI = re.compile(r"^(10\.\d{4,9}/\S+)$")


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def cache_plan(entry, folders):
    plan = {"key": entry.key, "text": None, "original": None, "urls": [], "isbn": ""}
    for label, slot in (("Cached text", "text"), ("Cached original", "original")):
        value = entry.field(label) or ""
        if "NOT YET FETCHED" in value:
            continue
        references = cache_references(folders, value)
        if not references:
            continue
        recorded = SHA.search(value)
        plan[slot] = (references[0][2], recorded.group(1) if recorded else None)
        if slot == "original":
            stated = FROM_URL.search(value.strip())
            if stated and stated.group(1).startswith(("http", "file:")):
                plan["urls"].append(stated.group(1).rstrip(")"))
    record = folders.read_origin_record(entry.key, FETCH) or {}
    if record.get("status") == "cached" and str(record.get("url", "")).startswith("http"):
        plan["urls"].append(record["url"])
    doi = (entry.field("DOI") or "").strip()
    if DOI.match(doi):
        plan["urls"].append("https://doi.org/" + doi)
    plan["urls"] = list(dict.fromkeys(plan["urls"]))
    plan["isbn"] = (entry.field("ISBN") or "").strip()
    return plan


def missing_names(plan, folders):
    return [slot[0] for slot in (plan["text"], plan["original"])
            if slot and not folders.file(slot[0]).exists()]


def restore_from_backup(plan, folders, backup, write):
    done = []
    if not backup:
        return done
    for slot in ("original", "text"):
        if not plan[slot]:
            continue
        name, recorded = plan[slot]
        target = folders.file(name)
        source = Path(backup) / name
        if target.exists() or not source.is_file():
            continue
        if recorded and sha256_of(source) != recorded:
            continue
        if write:
            Path(folders.files).mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        done.append(name)
    return done


def restore_from_network(plan, folders, timeout):
    if not plan["original"]:
        return [], [], "no Cached original line to rebuild from"
    name, recorded = plan["original"]
    text_name, text_sha = plan["text"] if plan["text"] else (None, None)
    reasons = []
    with tempfile.TemporaryDirectory() as work:
        for url in plan["urls"]:
            target = str(Path(work) / "download")
            meta, error = fetch.download(url, target, timeout)
            if meta is None or meta["http_code"] >= 400:
                reasons.append("%s: %s" % (fetch.host_of(url), error or "HTTP %s" % meta["http_code"]))
                continue
            try:
                _kind, text, _extension = fetch.extract(target, meta["content_type"])
            except fetch.Rejected as rejection:
                reasons.append("%s: %s" % (fetch.host_of(url), rejection.reason))
                continue
            original_ok = recorded is None or sha256_of(target) == recorded
            text_ok = text_sha is not None and hashlib.sha256(text.encode("utf-8")).hexdigest() == text_sha
            if not original_ok and not (text_ok and name.endswith((".html", ".htm"))):
                reasons.append("%s: the bytes changed since the source was read" % fetch.host_of(url))
                continue
            Path(folders.files).mkdir(parents=True, exist_ok=True)
            shutil.copyfile(target, folders.file(name))
            written, rebuilt = [name], []
            if text_name and not folders.file(text_name).exists():
                folders.file(text_name).write_text(text, encoding="utf-8")
                written.append(text_name)
                if not text_ok:
                    rebuilt.append(text_name)
            return written, rebuilt, None
    if not plan["urls"]:
        return [], [], ("only an ISBN: a book needs the backup" if plan["isbn"]
                        else "no backup copy and no URL, DOI or fetch record to download from")
    return [], [], "; ".join(reasons)[:300]


def run(entries, folders, backup, write, network, timeout, report):
    for entry in entries:
        plan = cache_plan(entry, folders)
        missing = missing_names(plan, folders)
        if not missing:
            continue
        from_backup = restore_from_backup(plan, folders, backup, write)
        for name in from_backup:
            report.add(entry.key, "restored" if write else "would-restore",
                       "%s from the backup" % name)
        still = [name for name in missing if name not in from_backup]
        if not still:
            continue
        if not network:
            report.add(entry.key, "not-restored", "%s: no backup copy, and the network was not used"
                       % ", ".join(still))
            continue
        if not write:
            route = plan["urls"][0] if plan["urls"] else ("ISBN only" if plan["isbn"] else "no route")
            kind = "would-restore" if plan["urls"] else "not-restored"
            report.add(entry.key, kind, "%s via %s" % (", ".join(still), route))
            continue
        written, rebuilt, reason = restore_from_network(plan, folders, timeout)
        for name in written:
            if name in rebuilt:
                report.add(entry.key, "text-rebuilt", "%s rebuilt; its hash differs from the list"
                           % name)
            else:
                report.add(entry.key, "restored", "%s from the network" % name)
        if reason:
            report.add(entry.key, "not-restored", "%s: %s" % (", ".join(still), reason))


FIXTURE_LIST = """# Sources List

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)
```

### [Aaa01] Adams, "Backed up" (2001)

**Full title:** Backed up
**Cached text:** `sources/library/Aaa01.txt` (fetched 2025-01-01, sha256 {aaa_txt})
**Cached original:** `sources/library/Aaa01.pdf` (fetched 2025-01-01, sha256 {aaa_pdf}, from https://example.org/a.pdf)

---

### [Bbb02] Baker, "A book" (2002)

**Full title:** A book
**ISBN:** 9780000000002
**Cached text:** `sources/library/Bbb02.txt` (fetched 2025-01-01, sha256 {missing})

---

### [Ccc03] Clark, "Present" (2003)

**Full title:** Present
**Cached text:** `sources/library/Ccc03.txt` (fetched 2025-01-01, sha256 {ccc_txt})

---
"""


def self_test():
    failures = []
    with tempfile.TemporaryDirectory() as root:
        root = Path(root)
        files = root / "sources" / "library"
        backup = root / "backup"
        files.mkdir(parents=True)
        backup.mkdir()
        (backup / "Aaa01.txt").write_text("the text\n", encoding="utf-8")
        (backup / "Aaa01.pdf").write_bytes(b"%PDF-1.4 bytes\n")
        (files / "Ccc03.txt").write_text("present\n", encoding="utf-8")
        text = FIXTURE_LIST.format(aaa_txt=sha256_of(backup / "Aaa01.txt"),
                                   aaa_pdf=sha256_of(backup / "Aaa01.pdf"),
                                   missing="0" * 64, ccc_txt=sha256_of(files / "Ccc03.txt"))
        (root / "list.md").write_text(text, encoding="utf-8")
        folders = SourceFolders(root=root, files=files, origin=root / "sources" / "library-index")
        entries = read_bank(root / "list.md").entries
        dry = CheckReport(TOOL, CLASSES)
        run(entries, folders, backup, False, False, 30, dry)
        if (files / "Aaa01.txt").exists():
            failures.append("a dry run wrote a file")
        wet = CheckReport(TOOL, CLASSES)
        run(entries, folders, backup, True, False, 30, wet)
        got = {(key, name) for key, name, _m in wet.items}
        if not (files / "Aaa01.pdf").exists() or ("Aaa01", "restored") not in got:
            failures.append("the backup copy was not restored")
        if ("Bbb02", "not-restored") not in got:
            failures.append("a book with only an ISBN and no backup must be reported")
        if any(key == "Ccc03" for key, _name in got):
            failures.append("a present file must be left alone")
        (backup / "Aaa01.txt").write_text("tampered\n", encoding="utf-8")
        (files / "Aaa01.txt").unlink()
        again = CheckReport(TOOL, CLASSES)
        run(entries, folders, backup, True, False, 30, again)
        if (files / "Aaa01.txt").exists():
            failures.append("a backup copy with the wrong hash was restored")
    if not fetch.missing_external_tools(("curl",)):
        failures.extend(network_self_test())
    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


class QuietFileHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_arguments):
        pass


def local_web_server(folder):
    handler = functools.partial(QuietFileHandler, directory=str(folder))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def network_self_test():
    failures = []
    with tempfile.TemporaryDirectory() as root:
        root = Path(root)
        files = root / "sources" / "library"
        files.mkdir(parents=True)
        page = root / "served.html"
        page.write_text("<html><body><p>" + "The page says what it says. " * 100
                        + "</p></body></html>", encoding="utf-8")
        _kind, text, _extension = fetch.extract(str(page), "text/html")
        text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        server = local_web_server(root)
        page_address = "http://127.0.0.1:%d/%s" % (server.server_address[1], page.name)
        entry_text = ("# Sources List\n\n## Entry format\n\n```\n### [<Key>] A, \"T\" (Y)\n```\n\n"
                      "### [Web05] Web, \"A page\" (2005)\n\n**Full title:** A page\n"
                      "**Cached text:** `sources/library/Web05.txt` (fetched 2025-01-01, sha256 %s)\n"
                      "**Cached original:** `sources/library/Web05.html` (fetched 2025-01-01, "
                      "sha256 %s, from %s)\n\n---\n" % (text_sha, sha256_of(page), page_address))
        (root / "list.md").write_text(entry_text, encoding="utf-8")
        folders = SourceFolders(root=root, files=files, origin=files)
        report = CheckReport(TOOL, CLASSES)
        try:
            run(read_bank(root / "list.md").entries, folders, None, True, True, 30, report)
        finally:
            server.shutdown()
            server.server_close()
        if not (files / "Web05.html").exists() or not (files / "Web05.txt").exists():
            failures.append("the download route did not restore the page: %s" % report.items)
        elif sha256_of(files / "Web05.txt") != text_sha:
            failures.append("the rebuilt text does not match its recorded hash")
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("--keys", help="comma-separated keys (default: every entry)")
    parser.add_argument("--fix", action="store_true", help="write the restored files")
    parser.add_argument("--backup-only", action="store_true", help="never use the network")
    parser.add_argument("--timeout", type=int, default=fetch.DEFAULT_TIMEOUT)
    parser.add_argument("--self-test", action="store_true", help="run the built-in examples")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    sources_list = config.sources.list
    if skipped_for_missing(TOOL, sources_list, "sources list", args.format):
        return 0
    folders = folders_from_config(config)
    backup = config.sources.backup if config.sources.backup and Path(config.sources.backup).is_dir() else None
    wanted = {k.strip() for k in args.keys.split(",")} if args.keys else None
    entries = [e for e in read_bank(sources_list).entries if wanted is None or e.key in wanted]

    report = CheckReport(TOOL, CLASSES)
    network = not args.backup_only
    missing_tools = fetch.missing_external_tools() if network else []
    run(entries, folders, backup, args.fix, network and not missing_tools, args.timeout, report)
    if args.format == "text":
        print("backup: %s" % (backup or "not set (sources.backup) or not reachable"))
        if missing_tools:
            print("network part SKIPPED: %s not on PATH" % ", ".join(missing_tools))
        print()
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
