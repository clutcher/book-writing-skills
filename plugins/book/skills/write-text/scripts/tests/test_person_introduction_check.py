import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "lib" / "tests"))

from script_books import NEW_BOOK

SCRIPT = Path(__file__).resolve().parents[1] / "person-introduction-check.py"


class PersonIntroductionCheckTest(unittest.TestCase):
    def test_shouldPrintTheReportWhenTheOutputCannotHoldLineDrawing(self):
        # when
        completed = subprocess.run([sys.executable, str(SCRIPT)], cwd=NEW_BOOK,
                                   capture_output=True,
                                   env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                                        "PYTHONIOENCODING": "cp1252"})

        # then
        self.assertIn(completed.returncode, (0, 1), completed.stderr)
        self.assertNotIn(b"UnicodeEncodeError", completed.stderr)
        self.assertIn("PERSON INTRODUCTION CHECK", completed.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
