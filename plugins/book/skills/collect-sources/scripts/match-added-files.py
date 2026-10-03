#!/usr/bin/env python3
"""File the sources the author added by hand, under any file name, into the library.

The author saves downloaded files into the sources-to-add folder (`sources.to_add`)
under whatever name the browser gave them. For each file this script:

  1. reads its text: pdftotext for a PDF, OCR (tesseract) when the PDF is a scan with no
     text layer, the page text for HTML, the file itself for plain text
  2. finds candidate entries in the sources list: a DOI or ISBN on the first pages that
     the entry also has, and entries whose title and an author surname are on the first
     pages
  3. confirms each candidate with the entry's `Verified quotes` from the quotes bank: at
     least half of them must be found in the file (the same matching as check-facts'
     quote-in-file-check). An entry with no verified quotes is confirmed only by a DOI
     or ISBN match whose title is also on the first pages.

Exactly one confirmed entry: the file is a MATCH. With --fix it is copied into the library
as `<Key>.<ext>` with its extraction `<Key>.txt` and its library-index record, the cache
lines go into the sources list, the file leaves the sources-to-add folder, and its line
leaves `needed.txt`. Anything else is ASK: the candidates are printed and the file stays
where it is. A file is never moved on a guess, and a key already in the library is never
overwritten. A key that is not a plain file name (letters, digits and + _ . - only,
starting with a letter or digit) is never filed: it is an ASK.

After an ASK, the author names the entry: `--file NAME --key KEY` files that one file under
that key exactly as a MATCH is filed. The key must be in the sources list and not yet in
the library. NAME is a file name in the folder, not a path.

Dry run by default. Exit 0 when the run finished (ASK lines need a person, they do not
fail the run), 2 when it could not run.

Usage:
  match-added-files.py                   what each file is, and what --fix would do
  match-added-files.py --fix             file every confirmed match
  match-added-files.py --folder PATH     another folder than sources.to_add
  match-added-files.py --file NAME --key KEY [--fix]
                                         file one file under the key the author chose
  match-added-files.py --self-test
"""

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import fetch
import ocr
import script_tests
from citation_key import is_safe_file_key
from quote_match import (ALL_WINDOWS, ELLIPSIS_PIECES, ELSEVIER, FULL, has_surname, locate_in,
                         quotes_in, squash, title_share, title_words)
from source_files import (FETCH, OCR, add_config_arguments, folders_from_config, load_book,
                          shown_path, tool_failed)
from source_registry import read_bank
from sources_to_add import NEEDED_FILE_NAME, drop_needed_line, to_add_folder

TOOL = "match-added-files"
KINDS = {".pdf": "pdf", ".html": "html", ".htm": "html", ".txt": "text", ".md": "text"}
LIBRARY_SUFFIXES = {"pdf": ".pdf", "html": ".html", "text": ".src.txt"}
MANUAL_DOWNLOAD = "manual download"
OPENING_PAGES = 6
OPENING_CHARS = 20000
TITLE_SHARE_FOR_CANDIDATE = 0.75
TITLE_SHARE_FOR_IDENTITY = 0.5
CONFIRMING_MATCHES = (FULL, ELSEVIER, ELLIPSIS_PIECES, ALL_WINDOWS)
FOUND_BY_TITLE = "title and authors"
ISBN_RE = re.compile(r"\b(?:97[89][\s-]?)?(?:\d[\s-]?){9}[\dXx]\b")

MATCH = "MATCH"
ASK = "ASK"
SKIPPED = "SKIPPED"
FILED = "FILED"


class CannotRead(Exception):
    pass


@dataclass
class AddedFile:
    path: Path
    kind: str
    text: str
    other_texts: list = field(default_factory=list)
    ocr_run: dict = None

    @property
    def opening(self):
        pages = self.text.split("\f")
        head = "\n".join(pages[:OPENING_PAGES]) if len(pages) > 1 else self.text
        return head[:OPENING_CHARS]


@dataclass
class Candidate:
    entry: object
    found_by: str
    confirmed: bool
    reason: str

    @property
    def key(self):
        return self.entry.key

    def shown(self):
        return "%s (%s; %s)" % (self.key, self.found_by, self.reason)


def pdf_text(path, layout):
    command = ["pdftotext", "-q"] + (["-layout"] if layout else []) + [str(path), "-"]
    try:
        completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   timeout=300)
    except (OSError, subprocess.SubprocessError) as error:
        raise CannotRead("pdftotext failed: %s" % error)
    return completed.stdout.decode("utf-8", "replace")


def read_scan(path, options):
    missing = [tool for tool in ocr.REQUIRED_TOOLS if shutil.which(tool) is None]
    if missing:
        raise CannotRead("a scan with no text layer, and %s not on PATH (tesseract-ocr, "
                         "poppler-utils)" % ", ".join(missing))
    text, engine, pages, total = ocr.run_ocr(str(path), options.dpi, 0, options.language)
    if len(text.strip()) < ocr.MIN_CHARS:
        raise CannotRead("a scan, and OCR gave only %d characters" % len(text.strip()))
    return AddedFile(path, "pdf", text, ocr_run={"engine": engine, "dpi": options.dpi,
                                                 "pages": pages, "total": total})


def read_added_file(path, options):
    kind = KINDS[path.suffix.lower()]
    if kind == "pdf":
        if shutil.which("pdftotext") is None:
            raise CannotRead("pdftotext not on PATH (poppler-utils)")
        text = pdf_text(path, layout=True)
        if len(text.strip()) < ocr.MIN_CHARS:
            return read_scan(path, options)
        return AddedFile(path, kind, text, other_texts=[pdf_text(path, layout=False)])
    if kind == "html":
        return AddedFile(path, kind, fetch.normalise(fetch.extract_html(path.read_bytes())))
    return AddedFile(path, kind, path.read_text(encoding="utf-8", errors="replace"))


def isbn13(raw):
    digits = re.sub(r"[^0-9Xx]", "", raw).upper()
    if len(digits) == 10 and digits[:9].isdigit():
        total = sum((10 - place) * (10 if char == "X" else int(char))
                    for place, char in enumerate(digits))
        if total % 11:
            return None
        digits = "978" + digits[:9]
        return digits + str((10 - sum(int(char) * (3 if place % 2 else 1)
                                      for place, char in enumerate(digits)) % 10) % 10)
    if len(digits) == 13 and digits.isdigit():
        if sum(int(char) * (3 if place % 2 else 1) for place, char in enumerate(digits)) % 10:
            return None
        return digits
    return None


def isbns_in(text):
    return {number for number in map(isbn13, ISBN_RE.findall(text)) if number}


def dois_in(text):
    return {fetch.trim_doi(doi).lower() for doi in fetch.DOI_RE.findall(text)}


def entry_field(entry, name):
    return (entry.field(name) or "").strip()


def entry_text(entry, names):
    return " ".join(entry_field(entry, name) for name in names)


def by_identifier(opening, entries):
    dois, isbns = dois_in(opening), isbns_in(opening)
    found = {}
    for entry in entries:
        shared_dois = dois & dois_in(entry_text(entry, ("DOI", "DOI/URL", "Access URLs",
                                                        "Identifier")))
        shared_isbns = isbns & isbns_in(entry_text(entry, ("ISBN", "Identifier")))
        if shared_dois:
            found[entry.key] = (entry, "DOI " + sorted(shared_dois)[0])
        elif shared_isbns:
            found[entry.key] = (entry, "ISBN " + sorted(shared_isbns)[0])
    return found


def by_title(opening, entries):
    hay = squash(opening)
    found = {}
    for entry in entries:
        title = entry_field(entry, "Full title")
        if not title_words(title) or not has_surname(entry_field(entry, "Authors"), hay):
            continue
        if squash(title) in hay or title_share(title, hay) >= TITLE_SHARE_FOR_CANDIDATE:
            found[entry.key] = (entry, FOUND_BY_TITLE)
    return found


def confirm(entry, found_by, added, quotes_by_key):
    quotes = quotes_by_key.get(entry.key, [])
    if not quotes:
        title_seen = title_share(entry_field(entry, "Full title"), squash(added.opening))
        if found_by != FOUND_BY_TITLE and title_seen >= TITLE_SHARE_FOR_IDENTITY:
            return Candidate(entry, found_by, True, "no verified quotes; the title is there too")
        return Candidate(entry, found_by, False, "no verified quotes to confirm with")
    texts = [("text", squash(text)) for text in [added.text] + added.other_texts]
    found = sum(1 for quote in quotes if locate_in(quote, texts)[1] in CONFIRMING_MATCHES)
    reason = "%d of %d verified quotes found" % (found, len(quotes))
    return Candidate(entry, found_by, found > 0 and found * 2 >= len(quotes), reason)


def identify(added, entries, quotes_by_key):
    found = by_title(added.opening, entries)
    found.update(by_identifier(added.opening, entries))
    return [confirm(entry, found_by, added, quotes_by_key)
            for entry, found_by in (found[key] for key in sorted(found))]


def in_library(folders, key):
    return folders.file(key + ".txt").exists() or fetch.find_original(folders, key) is not None


def decide(candidates, folders):
    confirmed = [candidate for candidate in candidates if candidate.confirmed]
    if len(confirmed) == 1 and not is_safe_file_key(confirmed[0].key):
        return ASK, confirmed[0], "%r is not a plain file name; fix the key in the list first" % (
            confirmed[0].key)
    if len(confirmed) == 1 and in_library(folders, confirmed[0].key):
        return ASK, confirmed[0], "%s is already in the library; compare the two by hand" % (
            confirmed[0].key)
    if len(confirmed) == 1:
        return MATCH, confirmed[0], confirmed[0].shown()
    if not candidates:
        return ASK, None, "no entry in the sources list matches"
    return ASK, None, "%d candidate(s), %d confirmed: %s" % (
        len(candidates), len(confirmed), "; ".join(c.shown() for c in candidates))


def library_text(added, key, folders):
    if not added.ocr_run:
        return fetch.normalise(added.text)
    header = ocr.HEADER.format(pdf=folders.shown_file(key + ".pdf"),
                               engine=added.ocr_run["engine"], dpi=added.ocr_run["dpi"],
                               pages=added.ocr_run["pages"])
    return fetch.normalise(header + added.text)


def mark_as_ocr(added, key, folders):
    record = folders.read_origin_record(key, FETCH) or {}
    record["extractor"] = "tesseract"
    folders.write_origin_record(key, FETCH, record)
    folders.write_origin_record(key, OCR, {
        "key": key, "engine": added.ocr_run["engine"], "dpi": added.ocr_run["dpi"],
        "pages_ocred": added.ocr_run["pages"], "pages_total": added.ocr_run["total"],
        "chars": len(added.text)})


def file_in_library(added, key, folders, list_path, to_add):
    text = library_text(added, key, folders)
    meta = {"http_code": 200, "content_type": "", "final_url": MANUAL_DOWNLOAD,
            "bytes": added.path.stat().st_size}
    result = fetch.store(key, MANUAL_DOWNLOAD, meta, added.path, added.kind, text,
                         LIBRARY_SUFFIXES[added.kind], len(text.strip()), folders)
    if added.ocr_run:
        mark_as_ocr(added, key, folders)
    fetch.file_into_list([result], list_path, folders)
    added.path.unlink()
    drop_needed_line(to_add, key)
    if added.ocr_run:
        print("Line to put in the sources list for %s:" % key)
        print(ocr.access_status_line(key, added.ocr_run["dpi"]))


def added_files(folder):
    if not folder.is_dir():
        return []
    return sorted(path for path in folder.iterdir()
                  if path.is_file() and not path.name.startswith(".")
                  and path.name != NEEDED_FILE_NAME)


def verified_quotes(quotes_path):
    if not quotes_path or not Path(quotes_path).is_file():
        return {}
    return {entry.key: quotes_in(entry.field("Verified quotes") or "")
            for entry in read_bank(quotes_path).entries}


def report(outcome, name, detail):
    print("%-8s %s: %s" % (outcome, name, detail))


def file_under_chosen_key(options, config, folder):
    folders = folders_from_config(config)
    list_path = config.sources.list
    if Path(options.file).name != options.file or options.file in (".", ".."):
        return tool_failed("--file takes a file name in %s, not a path"
                           % shown_path(config.root, folder), TOOL)
    if not is_safe_file_key(options.key):
        return tool_failed("--key %r is not a plain file name: use letters, digits and + _ . - "
                           "only, starting with a letter or digit" % options.key, TOOL)
    path = folder / options.file
    if not path.is_file():
        return tool_failed("no file %s in %s" % (options.file, shown_path(config.root, folder)),
                           TOOL)
    if not list_path or not Path(list_path).is_file():
        return tool_failed("sources list not found: %s" % list_path, TOOL)
    if options.key not in {entry.key for entry in read_bank(list_path).entries}:
        return tool_failed("%s is not an entry in the sources list" % options.key, TOOL)
    if in_library(folders, options.key):
        return tool_failed("%s is already in the library; compare the two by hand"
                           % options.key, TOOL)
    if path.suffix.lower() not in KINDS:
        return tool_failed("%s is not a PDF, web page or text file" % options.file, TOOL)
    try:
        added = read_added_file(path, options)
    except CannotRead as reason:
        return tool_failed("%s: %s" % (options.file, reason), TOOL)
    target = folders.shown_file(options.key + LIBRARY_SUFFIXES[added.kind])
    if options.fix:
        file_in_library(added, options.key, folders, list_path, folder)
        report(FILED, path.name, "%s, chosen by the author -> %s" % (options.key, target))
    else:
        report(MATCH, path.name, "%s, chosen by the author -> would file as %s"
               % (options.key, target))
        print("dry run: pass --fix to file it")
    return 0


def run(options, config):
    folder = Path(options.folder) if options.folder else to_add_folder(config)
    if options.file or options.key:
        if not (options.file and options.key):
            return tool_failed("--file and --key go together", TOOL)
        return file_under_chosen_key(options, config, folder)
    folders = folders_from_config(config)
    list_path = config.sources.list
    files = added_files(folder)
    if not files:
        print("nothing to add: no files in %s" % shown_path(config.root, folder))
        return 0
    if not list_path or not Path(list_path).is_file():
        return tool_failed("sources list not found: %s" % list_path, TOOL)
    entries = read_bank(list_path).entries
    quotes_by_key = verified_quotes(config.sources.quotes)
    counts = {}
    for path in files:
        if path.suffix.lower() not in KINDS:
            outcome, detail = SKIPPED, "not a PDF, web page or text file; left where it is"
        else:
            try:
                added = read_added_file(path, options)
            except CannotRead as reason:
                outcome, detail = SKIPPED, str(reason)
            else:
                outcome, chosen, detail = decide(identify(added, entries, quotes_by_key), folders)
                if outcome == MATCH:
                    target = folders.shown_file(chosen.key + LIBRARY_SUFFIXES[added.kind])
                    if options.fix:
                        file_in_library(added, chosen.key, folders, list_path, folder)
                        outcome, detail = FILED, "%s -> %s" % (detail, target)
                    else:
                        detail = "%s -> would file as %s" % (detail, target)
        counts[outcome] = counts.get(outcome, 0) + 1
        report(outcome, path.name, detail)
    print("\n%d file(s): %s" % (len(files), ", ".join(
        "%s %d" % (name, counts[name]) for name in (FILED, MATCH, ASK, SKIPPED) if name in counts)))
    if counts.get(MATCH):
        print("dry run: pass --fix to file the matches")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0], epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    parser.add_argument("--folder", help="the folder to read (default: sources.to_add)")
    parser.add_argument("--file", metavar="NAME",
                        help="one file in the folder, filed under --key (after an ASK)")
    parser.add_argument("--key", help="the sources-list key the author chose for --file")
    parser.add_argument("--fix", action="store_true",
                        help="file every confirmed match; otherwise a dry run")
    parser.add_argument("--dpi", type=int, default=300, help="OCR resolution for scans")
    parser.add_argument("--language", default="eng", help="tesseract language pack for scans")
    parser.add_argument("--self-test", action="store_true", help="run the tests on fixtures")
    options = parser.parse_args()
    if options.self_test:
        return script_tests.run_self_test(__file__, "test_match_added_files.py")
    return run(options, load_book(options, TOOL))


if __name__ == "__main__":
    sys.exit(main())
