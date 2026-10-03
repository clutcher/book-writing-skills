import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

FIXTURES_FOLDER = Path(__file__).resolve().parent / "fixtures" / "script-books"
NEW_BOOK = FIXTURES_FOLDER / "bread-book"
OLD_BOOK = FIXTURES_FOLDER / "old-book"
OTHER_BOOK = FIXTURES_FOLDER / "other-book"
NEW_BOOK_RUN = NEW_BOOK / ".book" / "runs" / "2025-04-01-100000"
OTHER_BOOK_RUN = OTHER_BOOK / "state" / "runs" / "2025-05-01-090000"


@dataclass
class ScriptRun:
    exit_code: int
    stdout: str
    stderr: str

    @property
    def findings(self):
        return [tuple(line.split("\t", 2)) for line in self.stdout.splitlines()
                if line.count("\t") >= 2]

    def keys_of(self, finding_class):
        return [key for key, name, _ in self.findings if name == finding_class]

    def message_of(self, key, finding_class):
        return next(message for found_key, name, message in self.findings
                    if found_key == key and name == finding_class)


def run_script(script_path, *arguments, book=NEW_BOOK):
    completed = subprocess.run([sys.executable, str(script_path), *arguments],
                               cwd=book, capture_output=True, encoding="utf-8", errors="replace",
                               env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    return ScriptRun(completed.returncode, completed.stdout, completed.stderr)


class CopyOfBook:
    def __init__(self, fixture):
        self.fixture = fixture

    def __enter__(self):
        self.folder = Path(tempfile.mkdtemp(prefix="script-test-")) / self.fixture.name
        shutil.copytree(self.fixture, self.folder)
        return self.folder

    def __exit__(self, *exception):
        shutil.rmtree(self.folder.parent, ignore_errors=True)
        return False
