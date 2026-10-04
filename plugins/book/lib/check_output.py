#!/usr/bin/env python3
import argparse
import json
import sys
import traceback
sys.dont_write_bytecode = True
from pathlib import Path

DEFECT = "defect"
INFORMATIONAL = "informational"
ADVISORY = "advisory"
CATEGORIES = (DEFECT, INFORMATIONAL, ADVISORY)

EXIT_CLEAN = 0
EXIT_DEFECTS = 1
EXIT_TOOL_FAILED = 2

FORMATS = ("text", "tsv", "json")

SHARED_CLASSES = {
    "dated-field": DEFECT,
    "doi-misfiled": DEFECT,
    "text-unusable": DEFECT,
    "no-text-layer": DEFECT,
    "txt-not-from-pdf": DEFECT,
    "moving-target": DEFECT,
    "org-or-unparsed": INFORMATIONAL,
    "identity-in-list": DEFECT,
}


class CheckReport:
    def __init__(self, tool, classes):
        unknown = {name: category for name, category in classes.items()
                   if category not in CATEGORIES}
        if unknown:
            raise ValueError(f"unknown categories: {unknown}")
        self.tool = tool
        self.classes = dict(classes)
        self.items = []
        self.skipped_reason = None

    def add(self, key, finding_class, message):
        if finding_class not in self.classes:
            raise ValueError(f"{self.tool}: class {finding_class!r} is not declared")
        self.items.append((str(key), finding_class, _one_line(message)))

    def skip(self, reason):
        self.skipped_reason = _one_line(reason)

    def skip_unless_present(self, path, feature):
        if path is not None and Path(path).exists():
            return False
        where = f" ({path} not found)" if path is not None else " (no path set)"
        self.skip(f"the book has no {feature}{where}")
        return True

    def counts(self):
        tally = {}
        for _, finding_class, _ in self.items:
            tally[finding_class] = tally.get(finding_class, 0) + 1
        return tally

    def category_of(self, finding_class):
        return self.classes[finding_class]

    def totals(self):
        totals = {category: 0 for category in CATEGORIES}
        for finding_class, count in self.counts().items():
            totals[self.category_of(finding_class)] += count
        return totals

    def exit_code(self):
        return EXIT_DEFECTS if self.totals()[DEFECT] else EXIT_CLEAN

    def item_lines(self):
        return [f"{key}\t{name}\t{message}" for key, name, message in self.items]

    def skipped_line(self):
        return f"SKIPPED   {self.skipped_reason}"

    def summary_lines(self):
        if self.skipped_reason is not None:
            return [self.skipped_line()]
        lines = []
        counts = self.counts()
        for name in sorted(counts):
            lines.append(f"{name:<24}  {counts[name]}")
        totals = self.totals()
        lines.append(f"TOTAL     {totals[DEFECT]} defects, {totals[INFORMATIONAL]} "
                     f"informational, {totals[ADVISORY]} advisory")
        return lines

    def as_dict(self):
        return {
            "tool": self.tool,
            "skipped": self.skipped_reason,
            "items": [{"key": key, "class": name, "category": self.category_of(name),
                       "message": message} for key, name, message in self.items],
            "counts": self.counts(),
            "totals": self.totals(),
            "exit": self.exit_code(),
        }

    def render(self, output_format="text"):
        if output_format == "json":
            return json.dumps(self.as_dict(), indent=2, ensure_ascii=False)
        if output_format == "tsv":
            return "\n".join(self.item_lines())
        return "\n".join(self.item_lines() + ([""] if self.items else [])
                         + self.summary_lines())

    def emit(self, output_format="text", stream=None, error_stream=None):
        stream = stream or sys.stdout
        text = self.render(output_format)
        if text:
            stream.write(text + "\n")
        if output_format == "tsv" and self.skipped_reason is not None:
            (error_stream or sys.stderr).write(self.skipped_line() + "\n")
        return self.exit_code()


def skipped_for_missing(tool, path, feature, output_format="text"):
    report = CheckReport(tool, {})
    if not report.skip_unless_present(path, feature):
        return False
    report.emit(output_format if output_format in FORMATS else "text")
    return True


def _one_line(text):
    return " ".join(str(text).split())


def add_output_arguments(parser):
    parser.add_argument("--format", choices=FORMATS, default="text",
                        help="text (default): items then summary; tsv: items only; "
                             "json: one object")
    return parser


def tool_failed(message, tool=None):
    prefix = f"{tool}: " if tool else ""
    sys.stderr.write(f"{prefix}{message}\n")
    return EXIT_TOOL_FAILED


def make_output_safe():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def run_main(main, tool=None):
    make_output_safe()
    tool = tool or Path(sys.argv[0]).stem
    try:
        code = main()
    except Exception as error:
        sys.stdout.flush()
        sys.stderr.write(f"{tool}: {failure_reason(error)}\n")
        code = EXIT_TOOL_FAILED
    sys.exit(code)


def failure_reason(error):
    frames = traceback.extract_tb(error.__traceback__)
    where = f" (at {Path(frames[-1].filename).name}:{frames[-1].lineno})" if frames else ""
    detail = _one_line(error) or "no details"
    return f"the tool failed: {type(error).__name__}: {detail}{where}"


def _self_test():
    failures = []

    def check(got, want, label):
        if got != want:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    report = CheckReport("demo", {"hash-stale": DEFECT, "queue": INFORMATIONAL,
                                  "maybe": ADVISORY})
    check(report.exit_code(), EXIT_CLEAN, "an empty report is clean")
    report.add("Smi99", "queue", "waiting")
    report.add("Smi99", "maybe", "look at this")
    check(report.exit_code(), EXIT_CLEAN, "informational and advisory never gate")
    report.add("AB+20", "hash-stale", "changed\nsince recorded")
    check(report.exit_code(), EXIT_DEFECTS, "a defect gates")
    check(report.item_lines()[-1], "AB+20\thash-stale\tchanged since recorded",
          "one tab-separated line per item")
    check(report.summary_lines()[-1],
          "TOTAL     1 defects, 1 informational, 1 advisory", "the TOTAL line is last")

    skipped = CheckReport("demo", {"x": DEFECT})
    skipped.skip("bibtex not found")
    check(skipped.summary_lines(), ["SKIPPED   bibtex not found"], "a skipped check says so")
    check(skipped.exit_code(), EXIT_CLEAN, "a skipped check does not report defects")

    absent = CheckReport("demo", {"x": DEFECT})
    check(absent.skip_unless_present(None, "glossary"), True, "no path means no feature")
    check(absent.summary_lines(), ["SKIPPED   the book has no glossary (no path set)"],
          "an absent feature is named in the reason")
    check(CheckReport("demo", {"x": DEFECT}).skip_unless_present(__file__, "glossary"), False,
          "a present feature is not skipped")

    try:
        report.add("Smi99", "undeclared", "x")
        failures.append("an undeclared class was accepted")
    except ValueError:
        pass
    check(json.loads(report.render("json"))["exit"], EXIT_DEFECTS, "json carries the exit code")
    check(report.render("tsv").count("\n"), 2, "tsv is the item lines only")

    for line in failures:
        print(f"FAIL  {line}")
    print(f"self-test: {'PASS' if not failures else str(len(failures)) + ' failure(s)'}")
    return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="The shared output and exit-code contract for checks. Import it from a "
                    "check; run it directly only to test the contract itself.")
    parser.add_argument("--self-test", action="store_true", help="test the contract")
    parser.add_argument("--shared-classes", action="store_true",
                        help="list the finding classes more than one script emits")
    args = parser.parse_args(argv)
    if args.self_test:
        return _self_test()
    if args.shared_classes:
        for name, category in sorted(SHARED_CLASSES.items()):
            print(f"{name}\t{category}")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    run_main(main)
