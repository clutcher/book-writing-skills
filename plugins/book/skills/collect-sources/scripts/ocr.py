#!/usr/bin/env python3
"""Make a scanned source searchable with OCR, and mark it as OCR in all three places.

Some cached PDFs are scans with no text layer. pdftotext returns a few dozen characters
of noise, so the source is present and unsearchable, and a grep that finds nothing reads
like "the paper does not say this". Tesseract closes that gap, not perfectly: every OCR
engine confuses rn/m, l/1 and O/0. A quote found in OCR text is evidence the passage is
there and roughly worded so; it is not proof of the exact wording. Confirming a verbatim
quote, and every digit, still means looking at the page image.

So the output goes where every tool already looks, and its origin is recorded loudly:

    <Key>.pdf     the scan, untouched, still the file of record
    <Key>.txt     OCR text, starting with an OCR-PROVENANCE header
    origin record engine, version, dpi, page count, character count (kind "ocr")

and the script prints the `Access status: READABLE VIA OCR` line to put in the sources
list. All three markers must agree; ocr-marker-check.py checks that they do.

It refuses to write an extraction under 2000 characters: a near-empty .txt reads as
"the source does not say this". That refusal means the scan needs a higher --dpi or is
not usable, not that something should be worked around.

300 dpi greyscale suits journal scans; `--psm 1` detects page layout and orientation,
which matters for two-column papers. A non-English scan needs the matching tesseract
language pack (--language); if it is not installed, say so rather than calling the scan
unreadable.

Needs tesseract, pdftoppm and pdfinfo (SKIPPED when missing).

Usage:
  ocr.py --key Smi93
  ocr.py --key Smi93 --pdf ~/Downloads/scan.pdf
  ocr.py --key Smi93 --dpi 400 --force
  ocr.py --self-test
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import (OCR, SourceFolders, add_config_arguments, folders_from_config,
                          load_book, tool_failed)

TOOL = "ocr"
MIN_CHARS = 2000
REQUIRED_TOOLS = ("tesseract", "pdftoppm", "pdfinfo")
HEADER = (
    "=== OCR-PROVENANCE ===\n"
    "This text was produced by optical character recognition from a scanned\n"
    "PDF that carries no text layer. It is searchable but not authoritative:\n"
    "character-level errors are expected (rn/m, l/1, 0/O), so a quote found\n"
    "here is evidence the passage exists, NOT proof of its exact wording.\n"
    "Confirm any verbatim quotation against the page image in {pdf}.\n"
    "Engine: {engine} at {dpi} dpi, {pages} pages.\n"
    "=== END OCR-PROVENANCE ===\n\n"
)


class TooShort(Exception):
    pass


def page_count(pdf):
    try:
        out = subprocess.run(["pdfinfo", pdf], capture_output=True, encoding="utf-8", errors="replace").stdout
        for line in out.splitlines():
            if line.startswith("Pages:"):
                return int(line.split()[1])
    except Exception:
        pass
    return 0


def run_ocr(pdf, dpi, max_pages, language):
    engine = subprocess.run(["tesseract", "--version"], capture_output=True,
                            encoding="utf-8", errors="replace").stdout.splitlines()[0]
    total = page_count(pdf)
    last = min(total, max_pages) if max_pages else total
    chunks = []
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", str(dpi), "-gray", "-png", "-f", "1", "-l", str(last),
                        pdf, Path(tmp, "p")], check=False, capture_output=True)
        pages = sorted(Path(tmp).glob("*.png"))
        for number, page in enumerate(pages, 1):
            stem = page.with_suffix("")
            subprocess.run(["tesseract", page, stem, "--psm", "1",
                            "-l", language], check=False, capture_output=True)
            page_text = page.with_suffix(".txt")
            if page_text.exists():
                chunks.append(page_text.read_text(encoding="utf-8", errors="replace"))
            print("  page %d/%d" % (number, len(pages)), end="\r", file=sys.stderr)
    print(" " * 30, end="\r", file=sys.stderr)
    return "\n".join(chunks), engine, len(chunks), total


def write_result(folders, key, text, engine, dpi, pages, total):
    if len(text.strip()) < MIN_CHARS:
        raise TooShort("OCR produced only %d characters -- not writing a cache file, since a "
                       "near-empty extraction reads as 'the source does not say this'."
                       % len(text.strip()))
    out_txt = folders.file(key + ".txt")
    body = HEADER.format(pdf=folders.shown_file(key + ".pdf"), engine=engine, dpi=dpi,
                         pages=pages) + text
    out_txt.write_text(body, encoding="utf-8")
    folders.write_origin_record(key, OCR, {"key": key, "engine": engine, "dpi": dpi,
                                           "pages_ocred": pages, "pages_total": total,
                                           "chars": len(text)})
    return out_txt


def access_status_line(key, dpi):
    return ("**Access status:** READABLE VIA OCR. The cached PDF is a scan with no text layer; "
            "`%s.txt` is tesseract output at %d dpi and carries character-level errors, so it "
            "supports searching but not verbatim quotation -- confirm any quote against the "
            "page image." % (key, dpi))


def self_test():
    failures = []
    for merged in (False, True):
        with tempfile.TemporaryDirectory() as root:
            files = Path(root) / "files"
            files.mkdir()
            origin = Path(root) / "origin" if merged else files
            folders = SourceFolders(root=Path(root), files=files, origin=origin)
            try:
                write_result(folders, "Smi93", "too little", "tesseract 5", 300, 1, 1)
                failures.append("a near-empty OCR result was written")
            except TooShort:
                pass
            if folders.file("Smi93.txt").exists():
                failures.append("a refused result left a file behind")
            write_result(folders, "Smi93", "word " * 500, "tesseract 5", 300, 4, 4)
            text = folders.file("Smi93.txt").read_text(encoding="utf-8")
            if not text.startswith("=== OCR-PROVENANCE ==="):
                failures.append("the extraction does not start with the provenance header")
            record = folders.read_origin_record("Smi93", OCR)
            if not record or record.get("dpi") != 300:
                failures.append("the OCR origin record is missing (merged=%s)" % merged)
    if "READABLE VIA OCR" not in access_status_line("Smi93", 300):
        failures.append("the status line lacks READABLE VIA OCR")
    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    add_config_arguments(parser)
    parser.add_argument("--key", help="citation key of the cached scan")
    parser.add_argument("--pdf", help="source PDF (default: <sources.library>/<Key>.pdf)")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--max-pages", type=int, default=0, help="0 = all pages")
    parser.add_argument("--language", default="eng", help="tesseract language pack (default eng)")
    parser.add_argument("--force", action="store_true", help="overwrite an existing extraction")
    parser.add_argument("--self-test", action="store_true",
                        help="test the writing and refusal rules without running tesseract")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.key:
        return tool_failed("--key is required", TOOL)

    missing = [tool for tool in REQUIRED_TOOLS if shutil.which(tool) is None]
    if missing:
        print("SKIPPED   %s not on PATH (tesseract-ocr, poppler-utils)" % ", ".join(missing))
        return 0

    config = load_book(args, TOOL)
    folders = folders_from_config(config)
    Path(folders.files).mkdir(parents=True, exist_ok=True)
    dest_pdf = folders.file(args.key + ".pdf")
    pdf = Path(args.pdf) if args.pdf else dest_pdf
    if not pdf.exists():
        return tool_failed("no PDF at %s" % pdf, TOOL)
    out_txt = folders.file(args.key + ".txt")
    if out_txt.exists() and not args.force:
        return tool_failed("%s already exists; pass --force to replace it" % out_txt, TOOL)
    if pdf.resolve() != dest_pdf.resolve():
        shutil.copy(pdf, dest_pdf)

    text, engine, pages, total = run_ocr(str(dest_pdf), args.dpi, args.max_pages, args.language)
    try:
        write_result(folders, args.key, text, engine, args.dpi, pages, total)
    except TooShort as error:
        return tool_failed(str(error), TOOL)

    print("%s: %d chars from %d/%d pages -> %s" % (args.key, len(text), pages, total, out_txt))
    print("Line to put in the sources list:")
    print(access_status_line(args.key, args.dpi))
    return 0


if __name__ == "__main__":
    sys.exit(main())
