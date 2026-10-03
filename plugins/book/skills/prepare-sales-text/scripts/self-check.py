#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
LIB_DIR = SKILL_DIR.parents[1] / "lib"
sys.path.insert(0, str(LIB_DIR))
sys.dont_write_bytecode = True

from check_output import DEFECT, INFORMATIONAL, CheckReport, add_output_arguments

DESCRIPTION = """Run every sales-text script against the fixture book in tests/fixtures/book and
compare the result with what it must be. Uses no real book and no network (the search
suggestion script is only asked for --help).

The fixture is copied to a temporary folder first, so --fix runs never touch the skill.

Classes:
  case-failed   defect         a script gave a different exit code, different finding
                               counts, or different output than expected
  case-passed   informational  one case that matched
Exit 0 when every case passes, 1 when one fails."""

CLASSES = {"case-failed": DEFECT, "case-passed": INFORMATIONAL}

SCRIPTS = ("plain-description.py", "table-of-contents.py", "store-description-check.py",
           "keyword-check.py", "sync-check.py", "copy-stats.py", "copy-diff.py",
           "search-suggestions.py", "sales-text-files.py", "self-check.py")

TEMPLATE_KEYWORDS = str(SKILL_DIR / "templates" / "keywords-and-categories.md")

COUNT_CASES = (
    ("store description, clean", ["store-description-check.py"], 0,
     {"size": 1, "above-the-fold": 1}),
    ("store description, every defect", ["store-description-check.py",
                                         "publishing/sales-text/amazon-with-defects.html"], 1,
     {"size": 1, "above-the-fold": 1, "tag-not-allowed": 2, "tag-not-closed": 1,
      "web-address": 1, "email-address": 1, "emoji": 1, "price-or-offer": 1,
      "review-request": 1}),
    ("store description, names with dots and symbols", ["store-description-check.py",
                                                         "publishing/sales-text/amazon-technical.html"], 0,
     {"size": 1, "above-the-fold": 1, "bare-domain": 1, "symbol": 1}),
    ("keywords, unfilled template", ["keyword-check.py", TEMPLATE_KEYWORDS], 0,
     {"empty-slots": 1, "slot-usage": 1}),
    ("keywords, clean", ["keyword-check.py"], 0,
     {"empty-slots": 1, "slot-usage": 1, "picker-not-confirmed": 1}),
    ("keywords, every defect", ["keyword-check.py", "publishing/sales-text/keywords-with-defects.md"], 1,
     {"too-many-slots": 1, "quotation-marks": 1, "subjective-word": 1, "title-word": 4,
      "avoid-word": 1, "repeated-word": 2, "category-word": 3, "plural-variant": 2,
      "slot-usage": 1, "too-many-categories": 1}),
    ("sync, as written", ["sync-check.py"], 0,
     {"quantity-wording": 1, "opening-echo": 2, "opening": 3, "bold-path": 2}),
    ("sync, fewer than two selling surfaces", ["sync-check.py", "--set", "sales_text.amazon=none.html",
                                               "--set", "sales_text.back_cover=none.md"], 0,
     {}),
    ("sync, a retired phrase is back", ["sync-check.py", "--set",
                                        'sales_text.retired_phrases=["two habits"]'], 1,
     {"retired-phrase": 3, "quantity-wording": 1, "opening-echo": 2, "opening": 3,
      "bold-path": 2}),
    ("sync, a shared span changed", ["sync-check.py", "--set",
                                     'sales_text.shared_spans=["from one loaf to every bakery"]'],
     0, {"shared-span-missing": 3, "quantity-wording": 1, "opening-echo": 2, "opening": 3,
         "bold-path": 2}),
)

OUTPUT_CASES = (
    ("plain description", ["plain-description.py"], "plain-description.txt"),
    ("table of contents, chapters", ["table-of-contents.py"], "contents.html"),
    ("table of contents, sections", ["table-of-contents.py", "--depth", "sections"], "contents-full.html"),
)

FIX_CASES = (
    ("plain description --fix", ["plain-description.py", "--fix"], "publishing/sales-text/plain-description.txt",
     "plain-description.txt"),
    ("table of contents --fix", ["table-of-contents.py", "--fix"], "publishing/sales-text/contents.html",
     "contents.html"),
)


def run(arguments, cwd):
    command = [sys.executable, str(SKILL_DIR / "scripts" / arguments[0])] + arguments[1:]
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(command, cwd=cwd, capture_output=True, encoding="utf-8", errors="replace", timeout=60,
                          env=environment)


def check_help(book, report):
    for script in SCRIPTS:
        result = run([script, "--help"], book)
        if result.returncode == 0 and "usage:" in result.stdout:
            report.add(script, "case-passed", "--help works")
        else:
            report.add(script, "case-failed", f"--help exit {result.returncode}: {result.stderr.strip()[:200]}")


def check_counts(book, report):
    for label, arguments, want_exit, want_counts in COUNT_CASES:
        result = run(arguments + ["--format", "json"], book)
        try:
            counts = json.loads(result.stdout)["counts"]
        except (ValueError, KeyError):
            report.add(label, "case-failed", f"no JSON report: {result.stderr.strip()[:200]}")
            continue
        if result.returncode != want_exit or counts != want_counts:
            report.add(label, "case-failed", f"exit {result.returncode} (want {want_exit}), "
                       f"counts {counts} (want {want_counts})")
        else:
            report.add(label, "case-passed", f"exit {want_exit}, {sum(counts.values())} findings")


def check_outputs(book, expected, report):
    for label, arguments, expected_name in OUTPUT_CASES:
        result = run(arguments, book)
        want = (expected / expected_name).read_text(encoding="utf-8")
        if result.returncode == 0 and result.stdout == want:
            report.add(label, "case-passed", f"matches {expected_name}")
        else:
            report.add(label, "case-failed", f"exit {result.returncode}, output differs from {expected_name}")
    for label, arguments, written, expected_name in FIX_CASES:
        result = run(arguments, book)
        target = book / written
        want = (expected / expected_name).read_text(encoding="utf-8")
        if result.returncode == 0 and target.is_file() and target.read_text(encoding="utf-8") == want:
            report.add(label, "case-passed", f"wrote {written}")
        else:
            report.add(label, "case-failed", f"exit {result.returncode}, {written} missing or different")


def check_reports(book, report):
    stats = run(["copy-stats.py", "--format", "json"], book)
    try:
        names = [item["surface"] for item in json.loads(stats.stdout)["surfaces"]]
    except (ValueError, KeyError):
        names = []
    want = ["back-cover", "store-description", "ebook-description", "preface-opening"]
    if stats.returncode == 0 and names == want:
        report.add("copy stats", "case-passed", "all four surfaces measured")
    else:
        report.add("copy stats", "case-failed", f"exit {stats.returncode}, surfaces {names}")
    sample = run(["copy-stats.py", "--sample", "--format", "json"], book)
    try:
        reach = {item["sample"]: item["stops_in"] for item in json.loads(sample.stdout)["sample"]}
    except (ValueError, KeyError):
        reach = {}
    if sample.returncode == 0 and reach == {"print": "010-preface.md", "ebook": "010-preface.md"}:
        report.add("free sample reach", "case-passed", "both samples stop in the preface")
    else:
        report.add("free sample reach", "case-failed", f"exit {sample.returncode}, reach {reach}")
    files = run(["sales-text-files.py", "--format", "json"], book)
    try:
        found = {item["key"]: item["exists"] for item in json.loads(files.stdout)["files"]}
    except (ValueError, KeyError):
        found = {}
    if files.returncode == 0 and found.get("sales_text.amazon") and found.get("sales_text.preface") \
            and found.get("rules.decisions") is False:
        report.add("sales-text files", "case-passed", "real paths listed, missing files marked")
    else:
        report.add("sales-text files", "case-failed", f"exit {files.returncode}, files {found}")
    diff = run(["copy-diff.py", "publishing/sales-text/back-cover.md", "publishing/sales-text/amazon.html"], book)
    if diff.returncode == 0 and "{+" in diff.stdout and "[-" in diff.stdout:
        report.add("copy diff", "case-passed", "word-level changes shown")
    else:
        report.add("copy diff", "case-failed", f"exit {diff.returncode}")


def build_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_output_arguments(parser)
    return parser


def main():
    arguments = build_parser().parse_args()
    report = CheckReport("sales-text-self-check", CLASSES)
    expected = SKILL_DIR / "tests" / "expected"
    with tempfile.TemporaryDirectory() as folder:
        book = Path(folder) / "book"
        shutil.copytree(SKILL_DIR / "tests" / "fixtures" / "book", book)
        check_help(book, report)
        check_counts(book, report)
        check_outputs(book, expected, report)
        check_reports(book, report)
    return report.emit(arguments.format)


if __name__ == "__main__":
    sys.exit(main())
