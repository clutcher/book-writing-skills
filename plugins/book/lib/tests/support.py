import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LIB = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
NEW_BOOK = FIXTURES / "new-book"

if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))


def run_script(script, *arguments, cwd=None, stdin=None):
    return subprocess.run([sys.executable, str(LIB / script), *arguments], cwd=cwd,
                          input=stdin, capture_output=True, encoding="utf-8", errors="replace",
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


class TemporaryBook:
    def __init__(self, copy_of=None):
        self.copy_of = copy_of

    def __enter__(self):
        self.folder = Path(tempfile.mkdtemp(prefix="book-test-")).resolve()
        if self.copy_of:
            shutil.copytree(self.copy_of, self.folder, dirs_exist_ok=True)
        return self.folder

    def __exit__(self, *exception):
        shutil.rmtree(self.folder, ignore_errors=True)
        return False
