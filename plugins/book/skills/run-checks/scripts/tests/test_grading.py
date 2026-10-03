import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "lib"))

from grading import FOUND, PASSED, grade


def report_with(tool, *items):
    counts = {}
    for _, finding_class, _ in items:
        counts[finding_class] = counts.get(finding_class, 0) + 1
    return {"tool": tool,
            "items": [{"key": key, "class": finding_class, "category": category, "message": ""}
                      for key, finding_class, category in items],
            "counts": counts}


MISSING_KEY = report_with("cited-source-check", ("Kim20", "not-in-list", "defect"))
DUPLICATE_PAIR = report_with("duplicate-source-check",
                             ("Smi99", "suspect", "advisory"), ("Lee05", "suspect", "advisory"))
READING_QUEUE = report_with("list-quotes-join-check",
                            ("Smi99", "not-read", "informational"),
                            ("Lee05", "not-read", "informational"))


class GradeTest(unittest.TestCase):
    def test_shouldFindADefectWhenTheCheckReportsOne(self):
        # when
        result = grade(MISSING_KEY)

        # then
        self.assertEqual(result.state, FOUND)
        self.assertEqual(result.summary, "not-in-list 1")

    def test_shouldFindAnAdvisoryItemWhenAPersonMustStillLookAtIt(self):
        # when
        result = grade(DUPLICATE_PAIR)

        # then
        self.assertEqual(result.state, FOUND)
        self.assertEqual(result.findings, ["suspect 2"])

    def test_shouldPassAndShowTheCountWhenOnlyAReadingQueueIsReported(self):
        # when
        result = grade(READING_QUEUE)

        # then
        self.assertEqual(result.state, PASSED)
        self.assertEqual(result.summary, "not-read 2")

    def test_shouldNameTheInformationalCountsBesideAFinding(self):
        # given
        mixed = report_with("cited-source-check", ("Kim20", "not-in-list", "defect"),
                            ("Lee05", "waits-in-needed", "informational"))

        # when
        result = grade(mixed)

        # then
        self.assertEqual(result.summary, "not-in-list 1 (informational: waits-in-needed 1)")

    def test_shouldPassWhenTheCheckFoundNothing(self):
        # when
        result = grade(report_with("cited-source-check"))

        # then
        self.assertEqual(result.state, PASSED)
        self.assertEqual(result.summary, "nothing found")


if __name__ == "__main__":
    unittest.main()
