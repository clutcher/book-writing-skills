"""Grade one check's JSON report: is there anything in it the author must fix?

Every DEFECT and every ADVISORY item is a finding, on every run, until the file is fixed.
There is no accepted count. An INFORMATIONAL item is an expected state or a worklist: it is
counted and shown, and it is never a finding.

  found    the report holds at least one DEFECT or ADVISORY item
  passed   it holds none (it may hold INFORMATIONAL items)
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

from check_output import INFORMATIONAL

PASSED = "passed"
FOUND = "found"


@dataclass
class Grade:
    state: str
    summary: str
    findings: list = field(default_factory=list)


def class_categories(report):
    return {item["class"]: item["category"] for item in report.get("items", [])}


def counts_text(counts):
    return ", ".join(f"{name} {count}" for name, count in counts)


def grade(report):
    categories = class_categories(report)
    counts = sorted(report.get("counts", {}).items())
    findings = [(name, count) for name, count in counts
                if count and categories.get(name) != INFORMATIONAL]
    informational = [(name, count) for name, count in counts
                     if count and categories.get(name) == INFORMATIONAL]
    if findings:
        summary = counts_text(findings)
        if informational:
            summary += f" (informational: {counts_text(informational)})"
        return Grade(FOUND, summary, [f"{name} {count}" for name, count in findings])
    return Grade(PASSED, counts_text(informational) or "nothing found")
