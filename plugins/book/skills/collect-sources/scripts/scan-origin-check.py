#!/usr/bin/env python3
"""Find cached PDFs whose text layer is somebody else's OCR, and mark them.

ocr-marker-check.py only checks that OCR already marked somewhere is marked everywhere;
it discovers nothing. A scan that arrived with an OCR text layer already inside it is
marked nowhere: pdftotext succeeds, the fetch record says `extractor: pdftotext`, no OCR
record exists because no engine of ours ran, and the list says READABLE. Every character
is a machine guess and nothing says so. This script discovers those from the PDF itself.

Digits are the damage: prose absorbs a bad glyph, but "1,670 ros" for "1,670 ms" or
"53.00" for "$3.00" becomes a statistic with a citation attached.

No single signal works. A producer string alone over-reports (Ghostscript is a general
distiller that also makes born-digital LaTeX PDFs), and full-page imagery alone
over-reports on figure-heavy papers. So seven signals are collected and graded:

  ocr-producer        Producer/Creator names an OCR or scanner-imaging engine
  ocr-font-names      generated font names on at least half the fonts
  scanner-codec       bitonal CCITT/JBIG2 imagery over >= 60% of the printed page on
                      >= 50% of pages (document-scanner codecs)
  raster-pages        imagery in any codec over >= 60% of the page on >= 80% of pages
  no-embedded-fonts   a text layer with no embedded font at all
  single-font-text    the whole text drawn in ONE font (a typeset document needs at
                      least a roman and an italic)
  ocr-error-signature the text scores as machine-read (below)

Coverage is measured in printed area, not pixels: a 600 ppi code listing covers a tenth
of a page, a 300 dpi scan all of it.

Verdicts and classes:
  scan-ocr          DEFECT   a strong signal (producer, font names, scanner codec), or
                             raster-pages with any corroborating signal. --fix marks it
  partially-marked  DEFECT   OCR declared in some markers and missing from others;
                             write the missing ones by hand (--fix never rewrites an
                             existing header or record)
  likely            ADVISORY raster-pages alone, or two corroborating signals. A book
                             whose every page carries page-wide graphics lands here
  ambiguous         ADVISORY one weak signal: no-embedded-fonts alone (old Distiller
                             output does this) or the error signature alone (unusual
                             vocabulary does this). Never fixed. Record a born-digital
                             triage in the entry's Fetch note so it is not re-triaged
  no-text-layer     DEFECT   the PDF extracts to nothing: run ocr.py
  txt-not-from-pdf  DEFECT   no text layer, yet <Key>.txt has content from elsewhere
  text-unusable     DEFECT   mostly non-ASCII, so the signature cannot be computed
  scan-not-listed   DEFECT   a scan-ocr file with no list entry (a fetch never finished)

The error signature: over lower-case alphabetic tokens of 4+ letters, the share absent
from the system word list (non-word, >= 8%), and the share that become a listed word
under exactly one visual confusion (rn/m, cl/d, li/h, ...; >= 3 per 1000). A
born-digital non-word stays a non-word under any glyph swap; an OCR non-word is a real
word with one glyph wrong. Text under 90% ASCII, or with under 3% common English
function words, is not scored. The signature finds the bad scans; a GOOD OCR engine
leaves word accuracy high enough to pass it, so the structural signals decide. Do not
reason "the prose looks clean, so the text layer is real". It needs /usr/share/dict/words;
without it the signature is not scored.

--fix marks SCAN-OCR keys only: an OCR-PROVENANCE header in <Key>.txt, an OCR origin
record naming the engine as inherited, `READABLE VIA OCR` in Access status, and the new
Cached text sha256. It refuses a key with no list entry and a key whose Access status
carries a fetch gate.

Needs pdfinfo, pdfimages, pdffonts and pdftotext (poppler-utils); SKIPPED without them.

Usage:
  scan-origin-check.py
  scan-origin-check.py --key Smi93 --verbose
  scan-origin-check.py --fix
  scan-origin-check.py --self-test
"""

import argparse
import collections
import glob
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import (OCR, SourceFolders, add_config_arguments, folders_from_config,
                          load_book, tool_failed)
from check_output import (ADVISORY, DEFECT, INFORMATIONAL, SHARED_CLASSES, CheckReport,
                          add_output_arguments)
from source_registry import read_bank

TOOL = "scan-origin-check"
CLASSES = {
    "scan-ocr": DEFECT, "partially-marked": DEFECT, "likely": ADVISORY, "ambiguous": ADVISORY,
    "no-text-layer": SHARED_CLASSES["no-text-layer"],
    "txt-not-from-pdf": SHARED_CLASSES["txt-not-from-pdf"],
    "text-unusable": SHARED_CLASSES["text-unusable"],
    "scan-not-listed": DEFECT, "refused": INFORMATIONAL,
    "already-marked": INFORMATIONAL, "clean": INFORMATIONAL,
}
REQUIRED_TOOLS = ("pdfinfo", "pdfimages", "pdffonts", "pdftotext")
WORDLIST = "/usr/share/dict/words"

OCR_PRODUCERS = (
    "paper capture", "clearscan", "abbyy", "finereader", "omnipage", "scansoft",
    "intelligent scanning technology", "scan plug-in", "scan server", "luradocument",
    "luratech", "readiris", "paperport", "kofax", "cvision", "pdf compressor",
    "tesseract", "ocrmypdf", "docuworks", "nuance pdf", "irisocr",
)
OCR_FONT_NAME = re.compile(
    r"^(?:[A-Z]{6}\+)?Fd\d+-|ClearScan|^T3Font\d|^(?:[A-Z]{6}\+)?font[0-9a-f]{8,}$", re.I)

PAGE_COVERAGE = 0.6
CODEC_PAGE_SHARE = 0.5
RASTER_PAGE_SHARE = 0.8
NONWORD_PCT = 8.0
CONFUSION_PER_K = 3.0
MIN_CHARS_PAGE = 200
ASCII_MIN = 90.0
ENGLISH_MIN = 3.0
ENGLISH_MARKERS = frozenset(
    ("that", "with", "this", "from", "were", "which", "have", "been", "they",
     "would", "when"))
TEXT_PAGES = 60

CONFUSIONS = [("rn", "m"), ("m", "rn"), ("cl", "d"), ("d", "cl"), ("li", "h"),
              ("h", "li"), ("ii", "n"), ("n", "ii"), ("vv", "w"), ("w", "vv"),
              ("l", "i"), ("i", "l"), ("c", "e"), ("e", "c"), ("o", "c"),
              ("c", "o"), ("in", "m"), ("nn", "m")]

TOKEN = re.compile(r"[A-Za-z][A-Za-z'-]*")
FENCE = re.compile(r"^```.*?^```", re.M | re.S)
SHA = re.compile(r"sha256[: ]+([0-9a-f]{64})")
GATED_STATUS = re.compile(r"MANUAL FETCH REQUIRED|NO OPEN-ACCESS COPY|NOT CACHED", re.I)

HEADER = (
    "=== OCR-PROVENANCE ===\n"
    "This text was extracted with `pdftotext` from a SCANNED PDF whose embedded\n"
    "text layer was itself produced by OCR before we received it{producer}. It is\n"
    "searchable but NOT authoritative: character-level errors are expected in it\n"
    "(rn/m, l/1, 0/O, 5/S), so a quote found here is evidence the passage exists,\n"
    "NOT proof of its exact wording, and NO DIGIT may be taken from it.\n"
    "Confirm any verbatim quotation, and every number, against the page image\n"
    "in {pdf}.\n"
    "Identified by scan-origin-check.py: {signals}.\n"
    "=== END OCR-PROVENANCE ===\n\n"
)
STATUS = (
    "**Access status:** READABLE VIA OCR, and the OCR is not ours: the cached PDF is a "
    "scan whose text layer arrived already machine-read{producer}, so nothing in the "
    "extraction announced itself as OCR and this entry said plain READABLE. Identified "
    "by scan-origin-check.py ({signals}). Searchable, not authoritative for wording "
    "-- confirm any quotation, and every digit, against the page image."
)


def load_words():
    words = set()
    if not Path(WORDLIST).exists():
        return words
    with open(WORDLIST, errors="ignore", encoding="utf-8") as handle:
        for line in handle:
            word = line.strip().lower()
            if word:
                words.add(word)
                if word.endswith("'s"):
                    words.add(word[:-2])
    return words


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=600).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def digest(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def pdf_info(pdf):
    info = {}
    for line in run(["pdfinfo", pdf]).splitlines():
        if ":" in line:
            name, value = line.split(":", 1)
            clean = "".join(char for char in value if char.isprintable())
            info[name.strip()] = clean.strip()
    return info


def page_area(info):
    match = re.search(r"([\d.]+) x ([\d.]+) pts", info.get("Page size", ""))
    if not match:
        return 8.5 * 11.0
    return (float(match.group(1)) / 72.0) * (float(match.group(2)) / 72.0)


def image_coverage(pdf, pages, sheet):
    per_page = collections.Counter()
    bitonal = collections.Counter()
    for line in run(["pdfimages", "-list", pdf]).splitlines()[2:]:
        cols = line.split()
        if len(cols) < 12:
            continue
        try:
            page, width, height, bpc = int(cols[0]), int(cols[3]), int(cols[4]), int(cols[7])
            xppi, yppi = float(cols[-4]), float(cols[-3])
        except ValueError:
            continue
        if xppi <= 0 or yppi <= 0:
            continue
        share = (width / xppi) * (height / yppi) / sheet
        per_page[page] += share
        if bpc == 1 and cols[8] in ("ccitt", "jbig2"):
            bitonal[page] += share
    return {
        "coverage": sum(per_page.values()) / pages,
        "bitonal_coverage": sum(bitonal.values()) / pages,
        "raster_share": sum(1 for s in per_page.values() if s >= PAGE_COVERAGE) / pages,
        "codec_share": sum(1 for s in bitonal.values() if s >= PAGE_COVERAGE) / pages,
    }


def font_signals(pdf):
    total = embedded = generated = 0
    families = set()
    for line in run(["pdffonts", pdf]).splitlines()[2:]:
        if not line.strip():
            continue
        total += 1
        name = line.split()[0]
        families.add(name.split("+")[-1].lower())
        flags = re.findall(r"\b(yes|no)\b", line[36:])
        if flags and flags[0] == "yes":
            embedded += 1
        if OCR_FONT_NAME.search(name):
            generated += 1
    return {"fonts": total, "embedded": embedded, "generated_fonts": generated,
            "families": len(families)}


def pdf_text(pdf, pages):
    last = min(pages, TEXT_PAGES)
    text = run(["pdftotext", "-q", "-l", str(last), pdf, "-"])
    return text, last


def recoverable(token, words):
    for old, new in CONFUSIONS:
        start = 0
        while True:
            at = token.find(old, start)
            if at < 0:
                break
            if token[:at] + new + token[at + len(old):] in words:
                return True
            start = at + 1
    return False


def text_signature(text, words):
    ascii_pct = 100.0 * sum(1 for char in text if ord(char) < 128) / max(len(text), 1)
    tokens = [t for t in TOKEN.findall(text)
              if len(t) >= 4 and t.islower() and "'" not in t and "-" not in t]
    english_pct = 100.0 * sum(1 for t in tokens if t in ENGLISH_MARKERS) / max(len(tokens), 1)
    result = {"ascii_pct": ascii_pct, "tokens": len(tokens), "english_pct": english_pct,
              "nonword_pct": 0.0, "confusion_per_k": 0.0, "examples": []}
    if (not words or len(tokens) < 200 or ascii_pct < ASCII_MIN
            or english_pct < ENGLISH_MIN):
        result["scored"] = False
        return result
    nonwords = [t for t in tokens if t not in words]
    hits = {t for t in set(nonwords) if recoverable(t, words)}
    result["scored"] = True
    result["nonword_pct"] = 100.0 * len(nonwords) / len(tokens)
    result["confusion_per_k"] = 1000.0 * sum(1 for t in nonwords if t in hits) / len(tokens)
    result["examples"] = sorted(hits)[:8]
    return result


def entries(path):
    return {entry.key: entry for entry in read_bank(path).entries}


def field(block, name):
    for found in block.fields:
        if found.name == name:
            return found.line_value
    return ""


def marker_state(key, block, folders):
    present, missing = [], []
    (present if "READABLE VIA OCR" in field(block, "Access status").upper()
     else missing).append("list")
    (present if folders.has_origin_record(key, OCR) else missing).append("record")
    header = False
    txt = folders.file(key + ".txt")
    if txt.exists():
        with open(txt, errors="ignore", encoding="utf-8") as handle:
            header = "OCR-PROVENANCE" in handle.read(600)
    (present if header else missing).append("header")
    return present, missing


def already_marked(key, block, folders):
    return not marker_state(key, block, folders)[1]


def collect_facts(key, folders, words):
    pdf = str(folders.file(key + ".pdf"))
    txt = folders.file(key + ".txt")
    info = pdf_info(pdf)
    try:
        pages = int(info.get("Pages", "0")) or 1
    except ValueError:
        pages = 1
    facts = {"key": key, "pages": pages, "producer": info.get("Producer", ""),
             "creator": info.get("Creator", "")}
    facts.update(image_coverage(pdf, pages, page_area(info)))
    facts.update(font_signals(pdf))
    text, sampled = pdf_text(pdf, pages)
    facts["chars_page"] = len(text) / max(sampled, 1)
    facts.update(text_signature(text, words))
    facts["txt_chars"] = txt.stat().st_size if txt.exists() else 0
    return grade(facts)


def grade(facts):
    if facts["chars_page"] < MIN_CHARS_PAGE:
        facts["verdict"] = "txt-not-from-pdf" if facts["txt_chars"] > 2000 else "no-text-layer"
        facts["signals"] = []
        return facts

    signals = []
    stamp = (facts["producer"] + " " + facts["creator"]).lower()
    if any(name in stamp for name in OCR_PRODUCERS):
        signals.append("ocr-producer")
    if facts["generated_fonts"] >= max(1, facts["fonts"] / 2):
        signals.append("ocr-font-names")
    if facts["codec_share"] >= CODEC_PAGE_SHARE:
        signals.append("scanner-codec")
    if facts["raster_share"] >= RASTER_PAGE_SHARE:
        signals.append("raster-pages")
    if facts["embedded"] == 0:
        signals.append("no-embedded-fonts")
    if facts["families"] == 1:
        signals.append("single-font-text")
    if facts["scored"] and (facts["nonword_pct"] >= NONWORD_PCT
                            or facts["confusion_per_k"] >= CONFUSION_PER_K):
        signals.append("ocr-error-signature")
    facts["signals"] = signals

    strong = {"ocr-producer", "ocr-font-names", "scanner-codec"}
    corroborating = {"no-embedded-fonts", "single-font-text", "ocr-error-signature"}
    present = set(signals)
    if strong & present:
        facts["verdict"] = "SCAN-OCR"
    elif "raster-pages" in present and corroborating & present:
        facts["verdict"] = "SCAN-OCR"
    elif "raster-pages" in present or len(corroborating & present) >= 2:
        facts["verdict"] = "LIKELY"
    elif signals:
        facts["verdict"] = "AMBIGUOUS"
    elif not facts["scored"] and facts["ascii_pct"] < ASCII_MIN:
        facts["verdict"] = "text-unusable"
    else:
        facts["verdict"] = "clean"
    return facts


def marking_note(facts):
    producer = (facts["producer"] or facts["creator"]).strip()
    return (" (Producer: %s)" % producer) if producer else ""


def write_header(key, facts, folders):
    txt = folders.file(key + ".txt")
    body = txt.read_text(encoding="utf-8", errors="replace")
    if "OCR-PROVENANCE" in body[:600]:
        return digest(txt), len(body)
    header = HEADER.format(producer=marking_note(facts), pdf=folders.shown_file(key + ".pdf"),
                           signals=", ".join(facts["signals"]))
    txt.write_text(header + body, encoding="utf-8")
    return digest(txt), len(body)


def write_ocr_record(key, facts, chars, folders):
    producer = facts["producer"] or facts["creator"] or "unrecorded"
    note = ("NOT our OCR. The scan arrived with an OCR text layer already in it and was read "
            "with pdftotext. Identified by scan-origin-check.py: %s. Every digit must be "
            "confirmed against the page image before it enters the quotes bank or the book."
            % ", ".join(facts["signals"]))
    folders.write_origin_record(key, OCR, {
        "key": key,
        "engine": "inherited -- the PDF's own text layer, produced by OCR before we "
                  "received it; PDF Producer: %s" % producer,
        "dpi": None, "pages_ocred": None, "pages_total": facts["pages"],
        "chars": chars, "note": note})


def update_list(path, key, facts, new_hash, dry_run=False):
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().split("\n")
    start = end = None
    for index, line in enumerate(lines):
        if line.startswith("### ["):
            if start is not None:
                end = index
                break
            if line.startswith("### [%s]" % key):
                start = index
    if start is None:
        return "no list entry"
    if end is None:
        end = len(lines)

    status_at = cached_at = insert_at = None
    for index in range(start, end):
        if lines[index].startswith("**Access status:**"):
            status_at = index
        elif lines[index].startswith("**Cached text:**"):
            cached_at = index
            if insert_at is None:
                insert_at = index
    if status_at is not None and GATED_STATUS.match(
            lines[status_at].split(":**", 1)[-1].strip()):
        return "Access status carries a fetch gate"
    if status_at is None and insert_at is None:
        return "entry has no Cached text line to anchor the status"
    if dry_run:
        return None

    status = STATUS.format(producer=marking_note(facts), signals=", ".join(facts["signals"]))
    if status_at is not None:
        kept = re.sub(r"^\*\*Access status:\*\*\s*READABLE[.,]?\s*", "", lines[status_at])
        lines[status_at] = (status + " " + kept).rstrip() if kept.strip() else status
    else:
        lines.insert(insert_at, status)
        if cached_at is not None and cached_at >= insert_at:
            cached_at += 1

    if new_hash and cached_at is not None:
        recorded = SHA.search(lines[cached_at])
        if recorded:
            lines[cached_at] = lines[cached_at].replace(recorded.group(1), new_hash)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    return None


def report_line(facts):
    detail = ("%s | page %.0f%% imagery (%.0f%% scanner codec), page-scale on %.0f%% of pages"
              " | fonts %d/%d embedded") % (
        ", ".join(facts["signals"]) or "-", 100 * facts["coverage"],
        100 * facts["bitonal_coverage"], 100 * facts["raster_share"],
        facts["embedded"], facts["fonts"])
    if facts.get("scored"):
        detail += " | nonword %.1f%%, confusion %.1f/k" % (
            facts["nonword_pct"], facts["confusion_per_k"])
    if facts["producer"]:
        detail += " | %s" % facts["producer"][:40]
    return detail


def base_facts(**changes):
    facts = {"key": "Smi93", "pages": 10, "producer": "", "creator": "", "coverage": 0.1,
             "bitonal_coverage": 0.0, "raster_share": 0.0, "codec_share": 0.0,
             "fonts": 4, "embedded": 4, "generated_fonts": 0, "families": 3,
             "chars_page": 2500, "txt_chars": 25000, "scored": True, "ascii_pct": 99.0,
             "nonword_pct": 2.0, "confusion_per_k": 0.5, "english_pct": 7.0, "tokens": 900,
             "examples": []}
    facts.update(changes)
    return facts


FIXTURE_LIST = """# Sources List

## Entry format

```
### [<Key>]
```

---

### [Smi93]

**Access status:** READABLE
**Cached text:** `sources/library/Smi93.txt` (fetched 2025-01-01, sha256 0000000000000000000000000000000000000000000000000000000000000000)

---

### [Gat90]

**Access status:** MANUAL FETCH REQUIRED (gate)
**Cached text:** NOT YET FETCHED

---
"""


def self_test():
    failures = []

    def expect(facts, verdict, label):
        got = grade(facts)["verdict"]
        if got != verdict:
            failures.append("%s: got %s, want %s" % (label, got, verdict))

    expect(base_facts(), "clean", "a born-digital paper")
    expect(base_facts(producer="Adobe Acrobat Paper Capture Plug-in"), "SCAN-OCR",
           "an OCR engine in the producer string")
    expect(base_facts(producer="dvips + GPL Ghostscript"), "clean",
           "Ghostscript alone is a distiller, not OCR")
    expect(base_facts(codec_share=0.9), "SCAN-OCR", "page-scale scanner codec")
    expect(base_facts(raster_share=0.95), "LIKELY", "raster pages alone")
    expect(base_facts(raster_share=0.95, families=1), "SCAN-OCR",
           "raster pages with one font over them")
    expect(base_facts(embedded=0), "AMBIGUOUS", "no embedded fonts alone")
    expect(base_facts(chars_page=10, txt_chars=0), "no-text-layer", "no text layer")
    expect(base_facts(chars_page=10, txt_chars=9000), "txt-not-from-pdf",
           "text from somewhere else")
    expect(base_facts(scored=False, ascii_pct=60.0), "text-unusable", "mojibake")

    if not recoverable("rnethod", {"method"}):
        failures.append("an rn/m confusion must be recoverable")
    if recoverable("gardening", {"method"}):
        failures.append("an unrelated word must not be recoverable")

    with tempfile.TemporaryDirectory() as root:
        files = Path(root) / "sources" / "library"
        files.mkdir(parents=True)
        folders = SourceFolders(root=Path(root), files=files, origin=Path(root) / "sources" / "library-index")
        (files / "Smi93.txt").write_text("the scanned text " * 200, encoding="utf-8")
        list_path = Path(root) / "list.md"
        list_path.write_text(FIXTURE_LIST, encoding="utf-8")
        bank = entries(list_path)
        facts = grade(base_facts(producer="ABBYY FineReader"))
        if already_marked("Smi93", bank["Smi93"], folders):
            failures.append("an unmarked key counted as marked")
        if update_list(list_path, "Gat90", facts, None, dry_run=True) != "Access status carries a fetch gate":
            failures.append("a gated entry was not refused")
        new_hash, chars = write_header("Smi93", facts, folders)
        update_list(list_path, "Smi93", facts, new_hash)
        write_ocr_record("Smi93", facts, chars, folders)
        bank = entries(list_path)
        if not already_marked("Smi93", bank["Smi93"], folders):
            failures.append("after marking, not all three markers are present: %s"
                            % (marker_state("Smi93", bank["Smi93"], folders),))
        if new_hash not in list_path.read_text(encoding="utf-8"):
            failures.append("the Cached text sha256 was not refreshed")

    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("--list", dest="sources_list", help="the sources list (default: sources.list)")
    parser.add_argument("--key", action="append", help="check only this key (repeatable)")
    parser.add_argument("--verbose", action="store_true",
                        help="also list clean and already-marked keys, with signal values")
    parser.add_argument("--fix", action="store_true", help="mark the SCAN-OCR keys")
    parser.add_argument("--self-test", action="store_true",
                        help="test grading and marking on built-in examples, no PDFs needed")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    report = CheckReport(TOOL, CLASSES)
    missing = [tool for tool in REQUIRED_TOOLS if shutil.which(tool) is None]
    if missing:
        report.skip("%s not on PATH (poppler-utils)" % ", ".join(missing))
        return report.emit(args.format)

    config = load_book(args, TOOL)
    folders = folders_from_config(config)
    sources_list = args.sources_list or config.sources.list
    if args.sources_list and not Path(sources_list).exists():
        return tool_failed("sources list not found: %s" % sources_list, TOOL)
    if report.skip_unless_present(sources_list, "sources list"):
        return report.emit(args.format)

    words = load_words()
    banked = entries(sources_list)
    keys = args.key or sorted(path.name[:-4] for path in Path(folders.files).glob("*.pdf"))

    fixed = 0
    for key in keys:
        block = banked.get(key) or banked.get(key.split(".", 1)[0])
        if block is not None and already_marked(key, block, folders):
            if args.verbose:
                report.add(key, "already-marked", "declared OCR in all three places")
            continue
        facts = collect_facts(key, folders, words)
        if block is not None:
            present, absent = marker_state(key, block, folders)
            if present:
                report.add(key, "partially-marked",
                           "OCR declared in %s but missing from %s -- write the missing "
                           "marker(s) by hand" % (", ".join(present), ", ".join(absent)))
                continue
        verdict = facts["verdict"]
        detail = report_line(facts)
        if verdict == "clean":
            if args.verbose:
                report.add(key, "clean", detail)
            continue
        if verdict != "SCAN-OCR":
            report.add(key, verdict.lower(), detail)
            continue
        if block is None:
            report.add(key, "scan-not-listed", "a scan with no list entry; none is invented")
            continue
        if not args.fix:
            report.add(key, "scan-ocr", detail)
            continue
        if not folders.file(key + ".txt").exists():
            report.add(key, "refused", "no cached .txt to carry the header")
            report.add(key, "scan-ocr", detail)
            continue
        reason = update_list(sources_list, key, facts, None, dry_run=True)
        if reason:
            report.add(key, "refused", reason)
            report.add(key, "scan-ocr", detail)
            continue
        new_hash, chars = write_header(key, facts, folders)
        update_list(sources_list, key, facts, new_hash)
        write_ocr_record(key, facts, chars, folders)
        fixed += 1
    if args.format == "text":
        print("checked %d PDF(s)%s\n" % (len(keys), ", marked %d" % fixed if args.fix else ""))
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
