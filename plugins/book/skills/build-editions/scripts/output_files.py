#!/usr/bin/env python3
"""Find the newest file of one type in the book's output folder.

The EPUB scripts use this when no file is named on the command line. As a command it
prints the path of the newest file with the given ending, or nothing when there is none.
"""

import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

from book_config import ConfigError, add_config_arguments, config_from_args

EXIT_NOTHING_FOUND = 1


def newest_in_folder(folder, suffix):
    if not folder or not Path(folder).is_dir():
        return None
    candidates = sorted(Path(folder).glob(f"*{suffix}"), key=lambda path: path.stat().st_mtime)
    return candidates[-1] if candidates else None


def newest_output_file(args, suffix):
    try:
        output_folder = config_from_args(args).work.output
    except ConfigError:
        return None
    return newest_in_folder(output_folder, suffix)


def self_test():
    results = []
    with tempfile.TemporaryDirectory() as folder:
        older = Path(folder) / "older.epub"
        newer = Path(folder) / "newer.epub"
        other = Path(folder) / "newest.pdf"
        for age_in_seconds, path in ((30, older), (20, newer), (10, other)):
            path.write_text("x", encoding="utf-8")
            moment = time.time() - age_in_seconds
            os.utime(path, (moment, moment))
        results.append(("the newest file with the ending wins", newest_in_folder(folder, ".epub"), newer))
        results.append(("an ending with no file gives nothing", newest_in_folder(folder, ".azw3"), None))
        results.append(("a missing folder gives nothing", newest_in_folder(Path(folder) / "none", ".epub"), None))
    failures = [(name, got, expected) for name, got, expected in results if got != expected]
    for name, got, expected in failures:
        print(f"FAIL  {name}: got {got!r}, expected {expected!r}")
    print(f"output_files self-test: {len(results) - len(failures)}/{len(results)} passed")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    parser.add_argument("--ending", default=".epub", help="the file ending to look for (default: .epub)")
    parser.add_argument("--self-test", action="store_true", help="run the built-in tests in a temporary folder")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    newest = newest_output_file(args, args.ending)
    if newest is None:
        return EXIT_NOTHING_FOUND
    print(newest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
