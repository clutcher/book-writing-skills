#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path

FACTS_SELF_CHECK = Path(__file__).resolve().parents[2] / "check-facts" / "scripts" / "self-check.py"


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="self-check.py",
        description="Run the self-test of every collect-sources script and the fixture books; no "
                    "book needed. It runs the check-facts skill's self-check.py --skill "
                    "collect-sources; see that script's --help.")
    parser.add_argument("--quiet", action="store_true", help="print failures and warnings only")
    arguments = parser.parse_args(argv)
    command = [sys.executable, str(FACTS_SELF_CHECK), "--skill", "collect-sources"]
    if arguments.quiet:
        command.append("--quiet")
    return subprocess.run(command).returncode


if __name__ == "__main__":
    sys.exit(main())
