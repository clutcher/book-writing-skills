#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

from vale_settings import (PACKAGE_NAME, ValeSetupError, add_book_arguments, docker_found,
                           load_vale_settings, package_copy_is_current, run_vale)

DESCRIPTION = """Run Vale in Docker against the book.

It never writes into the book: when the book's copy of PlainBook is missing or differs from the
skill's, it prints SKIPPED and asks you to run vale-sync.py --fix first. Every other argument
goes to Vale. A file or folder argument may be given relative to the working folder or as an
absolute path; it must lie inside the book folder. With no Vale arguments the manuscript folder
is checked.

The book is found by walking up from DIR (default: the working folder); --config names its
book.yaml. The Vale config is rules.vale_ini, and its StylesPath must be inside the book folder.
The Docker image is tools.vale_image, pinned to a tag. On Linux it runs as the calling user, so
files Vale writes are not owned by root."""

EPILOG = """examples:
  vale-run.py --output JSON manuscript/110-chapter-1.md
  vale-run.py --output line manuscript/
  vale-run.py ls-config

exit codes: Vale's own (0 clean, 1 alerts at error level, 2 Vale failed); 2 also when the book,
its Vale config or a path cannot be used; SKIPPED with exit 0 when Docker is missing or
PlainBook is not synced."""


def parse_arguments(argv):
    parser = argparse.ArgumentParser(prog="vale-run.py", description=DESCRIPTION, epilog=EPILOG,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     allow_abbrev=False)
    add_book_arguments(parser)
    return parser.parse_known_args(argv)


def container_arguments(settings, vale_arguments):
    mapped = []
    for argument in vale_arguments:
        if argument.startswith("-") or not Path(argument).exists():
            mapped.append(argument)
            continue
        inside = settings.container_path(argument)
        if inside is None:
            raise ValeSetupError(f"{argument} is outside the book folder {settings.book_root}")
        mapped.append(inside)
    return mapped


def main(argv=None):
    arguments, vale_arguments = parse_arguments(argv)
    if not docker_found():
        print("SKIPPED   docker not found, so Vale did not run")
        return 0
    try:
        settings = load_vale_settings(arguments)
        if not package_copy_is_current(settings):
            print(f"SKIPPED   {PACKAGE_NAME} missing or stale in {settings.styles}, "
                  f"run vale-sync.py --fix")
            return 0
        mapped = container_arguments(settings, vale_arguments or [str(settings.manuscript)])
    except ValeSetupError as error:
        print(f"vale-run.py: {error}", file=sys.stderr)
        return 2
    return run_vale(settings, mapped)


if __name__ == "__main__":
    sys.exit(main())
