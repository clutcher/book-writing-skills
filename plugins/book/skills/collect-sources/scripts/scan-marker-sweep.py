#!/usr/bin/env python3
"""Sweep the cache for machine-read text that no TOOL can see, and for prose claims to check.

A source can be declared machine-read in PROSE (a Note saying "the text layer is OCR")
and nowhere a tool looks. ocr-marker-check.py polices only OCR already marked where a
tool reads; scan-origin-check.py reads the PDF and never reads the note. This sweep
joins the two, and asks whether the prose claim survives the bytes.

A prose caution is a CLAIM TO CHECK, never acted on: a note can say "OCR" about a
born-digital book whose photographs are bitonal plates and whose odd glyph is an italic
digit. Marking that source would write a false declaration into the bank. A bank
sentence is evidence, not authority.

Classes:
  undeclared-scan    DEFECT    scan-origin-check grades the file SCAN-OCR and no
                               marker exists; its --fix is the repair (one rule, one
                               implementation)
  hybrid-scan        ADVISORY  no font embedded anywhere AND page-scale scanner codecs
                               on at least a fifth of the pages: a partly scanned
                               document between the thresholds; settled by a render
  prose-only-claim   ADVISORY  a bank field says in prose the text is OCR while no marker
                               exists. Two repairs are possible and the script cannot
                               choose: mark the source, or correct the prose
  structural-suspect ADVISORY  a LIKELY or AMBIGUOUS grade on an unmarked key
  marker-partial     INFORMATIONAL  the three markers disagree; ocr-marker-check owns it
  text-gap           INFORMATIONAL  3+ pages with no text layer inside an otherwise
                               extractable PDF: a grep miss inside those pages is not
                               evidence of absence, while every other page extracts fine
  no-text-layer / txt-not-from-pdf / text-unusable   DEFECT, as in scan-origin-check
  marked / clean / no-pdf  INFORMATIONAL (--verbose)

Why the conjunctions: a producer string alone is wrong (Ghostscript is a distiller, not
OCR); a full-page-image ratio alone flags figure-heavy papers; no embedded font alone
is common in old Distiller output. HYBRID needs page-scale codec coverage, not merely
some.

There is no --fix: marking a confirmed scan belongs to scan-origin-check.py --fix,
and the other classes are settled by rendering a page:
  pdftoppm -r 170 -f 1 -l 2 -png <files>/<Key>.pdf /tmp/<Key>

Needs pdfinfo, pdfimages, pdffonts and pdftotext; SKIPPED without them.

Usage:
  scan-marker-sweep.py
  scan-marker-sweep.py --key Smi95 --verbose
  scan-marker-sweep.py --self-test
"""

import argparse
import collections
import glob
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import (OCR, add_config_arguments, folders_from_config, load_book,
                          tool_failed)
from check_output import (ADVISORY, DEFECT, INFORMATIONAL, SHARED_CLASSES, CheckReport,
                          add_output_arguments)
from source_registry import read_bank

TOOL = "scan-marker-sweep"
ORIGIN_CHECK_SCRIPT = "scan-origin-check.py"
CLASSES = {
    "undeclared-scan": DEFECT, "hybrid-scan": ADVISORY, "prose-only-claim": ADVISORY,
    "structural-suspect": ADVISORY, "marker-partial": INFORMATIONAL,
    "text-gap": INFORMATIONAL,
    "no-text-layer": SHARED_CLASSES["no-text-layer"],
    "txt-not-from-pdf": SHARED_CLASSES["txt-not-from-pdf"],
    "text-unusable": SHARED_CLASSES["text-unusable"],
    "marked": INFORMATIONAL, "clean": INFORMATIONAL, "no-pdf": INFORMATIONAL,
}

OCR_PROSE = re.compile(
    r"\btext layer is (?:itself )?ocr\b|\bocr(?:'?e?d)?\b|\bmachine[- ]read\b"
    r"|\bocr text layer\b|\bscanned (?:pdf|copy|image|print)\b"
    r"|\bimage[- ]only (?:pdf|scan)\b|\bword[- ]joining artifact",
    re.I)
NEGATED = re.compile(r"\b(?:not|n't|never|nor|no)\s+(?:\w+\s+){0,3}$", re.I)
CLEARED = re.compile(r"scan-origin-check|scan-provenance-check|ocr-provenance-check|ocr-marker-check|\bgrades?\b|\bgraded\b"
                     r"|\brefuted\b|\bcleared\b|\bfalse positive\b|\bAMBIGUOUS\b", re.I)
PROSE_FIELDS = ("Note", "Fetch note", "Access status", "Identifier", "Record history",
                "Edition", "Scope", "Guardrail", "Verified quotes", "Key findings")


def load_scan_origin_check(directory):
    path = Path(directory, ORIGIN_CHECK_SCRIPT)
    if not Path(path).exists():
        sys.exit(tool_failed("cannot find %s beside this script" % ORIGIN_CHECK_SCRIPT, TOOL))
    spec = importlib.util.spec_from_file_location("scan_origin_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strip_fenced(text):
    return re.sub(r"^```.*?^```", "", text, flags=re.M | re.S)


def entries(path):
    if not Path(path).exists():
        return
    for entry in read_bank(path).entries:
        yield entry.key, entry


def field_block(block, name):
    return (block.field(name) or "") if block else ""


def prose_caution(blocks):
    for block in blocks:
        for name in PROSE_FIELDS:
            value = field_block(block, name)
            if not value:
                continue
            cleaned = re.sub(r"READABLE VIA OCR", " ", value, flags=re.I)
            if CLEARED.search(cleaned):
                continue
            for match in OCR_PROSE.finditer(cleaned):
                before = cleaned[max(0, match.start() - 40):match.start()].lower()
                if NEGATED.search(before):
                    continue
                start = max(0, match.start() - 90)
                return name, re.sub(r"\s+", " ", cleaned[start:match.end() + 90]).strip()
    return None, ""


def markers(key, sources, source_block):
    present = []
    if sources.has_origin_record(key, OCR):
        present.append("record")
    txt = sources.file(key + ".txt")
    if txt.exists():
        with open(txt, errors="ignore", encoding="utf-8") as handle:
            if "OCR-PROVENANCE" in handle.read(800):
                present.append("header")
    if re.search(r"READABLE VIA OCR", field_block(source_block, "Access status"), re.I):
        present.append("status")
    return present


HYBRID_CODEC_SHARE = 0.2


def grade(facts):
    delegated = facts["delegated"]
    hybrid = (facts["embedded"] == 0 and facts["fonts"] > 0
              and facts.get("codec_share", 0.0) >= HYBRID_CODEC_SHARE)
    facts["hybrid"] = hybrid
    if facts["markers"]:
        return "marked" if len(facts["markers"]) == 3 else "marker-partial"
    if delegated == "SCAN-OCR":
        return "UNDECLARED-SCAN"
    if hybrid:
        return "HYBRID-SCAN"
    if facts["caution_field"] and (delegated in ("LIKELY", "AMBIGUOUS", "no-text-layer",
                                                 "txt-not-from-pdf")
                                  or facts["generated_fonts"]
                                  or facts["embedded"] == 0):
        return "PROSE-ONLY-CLAIM"
    if delegated in ("LIKELY", "AMBIGUOUS"):
        return "structural-suspect"
    return delegated


TEXT_GAP_MIN_PAGES = 3
TEXT_GAP_MIN_CHARS = 40
GAP_TIMEOUT = 240


def page_gaps(pdf):
    try:
        output = subprocess.run(["pdftotext", "-q", pdf, "-"], stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL,
                                timeout=GAP_TIMEOUT).stdout.decode("utf-8", "ignore")
    except (OSError, subprocess.SubprocessError):
        return 0, 0, 0
    pages = output.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    empty = sum(1 for page in pages if not page.strip())
    thin = sum(1 for page in pages if len(page.strip()) < TEXT_GAP_MIN_CHARS)
    return empty, thin, len(pages)


def assess(key, sources, registry, findings, scan_origin, words):
    pdf = str(sources.file(key + ".pdf"))
    source_block = registry.get(key, "")
    facts = scan_origin.collect_facts(key, sources, words) if Path(pdf).exists() else {
        "key": key, "verdict": "no-pdf", "signals": [], "pages": 0,
        "producer": "", "creator": "", "embedded": 0, "fonts": 0,
        "bitonal_coverage": 0.0, "generated_fonts": 0, "examples": []}
    facts["delegated"] = facts.pop("verdict")
    facts["markers"] = markers(key, sources, source_block)
    facts["registered"] = bool(source_block)
    field, sentence = prose_caution([source_block, findings.get(key)])
    facts["caution_field"], facts["caution"] = field, sentence
    facts["verdict"] = grade(facts)
    measurable = Path(pdf).exists() and facts["delegated"] not in ("no-text-layer",
                                                                    "txt-not-from-pdf")
    empty, thin, extracted = page_gaps(pdf) if measurable else (0, 0, 0)
    facts["gap_pages"], facts["gap_thin"], facts["gap_of"] = empty, thin, extracted
    return facts


def detail_of(facts, verbose):
    text = "markers %s | %s | fonts %d/%d embedded | bitonal %.0f%% | %s" % (
        ",".join(facts["markers"]) or "none", facts["delegated"], facts["embedded"],
        facts["fonts"], 100 * facts.get("bitonal_coverage", 0.0),
        facts["producer"][:34] or facts["creator"][:34] or "no producer")
    if facts["caution_field"]:
        text += ' | prose (%s): "...%s..."' % (facts["caution_field"], facts["caution"][:180])
    if verbose:
        text += " | signals: %s" % (", ".join(facts["signals"]) or "none")
        if facts.get("examples"):
            text += " | OCR-error words: %s" % " ".join(facts["examples"][:8])
    return text


def has_gap(facts):
    return facts.get("gap_pages", 0) >= TEXT_GAP_MIN_PAGES


FIXTURES = {
    "Pos94": ("SCAN-OCR", 10, 9, 0, 1.0, False, "UNDECLARED-SCAN"),
    "Pos95": ("SCAN-OCR", 21, 21, 20, 0.0, False, "UNDECLARED-SCAN"),
    "Pos98": ("SCAN-OCR", 9, 0, 0, 1.0, False, "UNDECLARED-SCAN"),
    "Neg95": ("AMBIGUOUS", 8, 0, 0, 0.059, True, "PROSE-ONLY-CLAIM"),
    "Neg95-noprose": ("AMBIGUOUS", 8, 0, 0, 0.059, False, "structural-suspect"),
    "Hyb90": ("AMBIGUOUS", 6, 0, 0, 0.3, False, "HYBRID-SCAN"),
    "Cln24": ("clean", 29, 28, 0, 0.0, False, "clean"),
    "Cln07": ("clean", 17, 11, 0, 0.0, False, "clean"),
    "Cln12": ("clean", 6, 6, 0, 0.0, False, "clean"),
    "Enc02": ("text-unusable", 17, 16, 0, 0.0, False, "text-unusable"),
    "Cln14": ("clean", 14, 8, 0, 0.0, False, "clean"),
    "Neg02": ("AMBIGUOUS", 498, 0, 0, 0.0, False, "structural-suspect"),
}


def self_test():
    failures = 0
    for key, row in sorted(FIXTURES.items()):
        delegated, fonts, embedded, generated, codec, caution, expected = row
        facts = {"delegated": delegated, "fonts": fonts, "embedded": embedded,
                 "generated_fonts": generated, "codec_share": codec,
                 "markers": [], "caution_field": "Note" if caution else "",
                 "caution": "the text layer is OCR" if caution else ""}
        verdict = grade(facts)
        if verdict != expected:
            print("FAIL %-14s expected %-18s got %s" % (key, expected, verdict))
            failures += 1
    field, _sentence = prose_caution([None])
    if field is not None:
        print("FAIL an empty entry produced a prose caution")
        failures += 1
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % failures))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("--list", dest="sources_list", help="the sources list (default: sources.list)")
    parser.add_argument("--quotes", help="the quotes bank (default: sources.quotes)")
    parser.add_argument("--key", action="append", help="only this key (repeatable)")
    parser.add_argument("--verbose", action="store_true",
                        help="also marked and clean keys, signal values and OCR-error words")
    parser.add_argument("--self-test", action="store_true",
                        help="only grade the recorded fixture signals")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    report = CheckReport(TOOL, CLASSES)
    scan_origin = load_scan_origin_check(Path(__file__).resolve().parent)
    missing = [tool for tool in scan_origin.REQUIRED_TOOLS if shutil.which(tool) is None]
    if missing:
        report.skip("%s not on PATH (poppler-utils)" % ", ".join(missing))
        return report.emit(args.format)

    config = load_book(args, TOOL)
    folders = folders_from_config(config)
    if report.skip_unless_present(folders.files, "source library"):
        return report.emit(args.format)
    words = scan_origin.load_words()
    registry = dict(entries(args.sources_list or config.sources.list))
    findings = dict(entries(args.quotes or config.sources.quotes))

    keys = args.key or sorted(path.name[:-4] for path in Path(folders.files).glob("*.pdf"))
    for key in keys:
        facts = assess(key, folders, registry, findings, scan_origin, words)
        verdict = facts["verdict"].lower()
        if verdict in ("marked", "clean", "no-pdf") and not args.verbose:
            pass
        elif verdict in CLASSES:
            report.add(key, verdict, detail_of(facts, args.verbose))
        if has_gap(facts):
            report.add(key, "text-gap", "%d of %d pages carry no text, %d under %d chars"
                       % (facts["gap_pages"], facts["gap_of"], facts["gap_thin"],
                          TEXT_GAP_MIN_CHARS))
    if args.format == "text":
        print("checked %d PDF(s); render a page before acting on any of these:\n"
              "  pdftoppm -r 170 -f 1 -l 2 -png %s/<Key>.pdf /tmp/<Key>\n"
              % (len(keys), folders.shown_files))
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
