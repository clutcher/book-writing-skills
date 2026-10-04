#!/usr/bin/env python3
import argparse
import sys

sys.dont_write_bytecode = True

from vale_settings import (PACKAGE_NAME, ValeSetupError, add_book_arguments, copy_package,
                           docker_found, load_vale_settings, package_copy_is_current, run_vale)

DESCRIPTION = """Copy the skill's own Vale style package (PlainBook) into the book's Vale styles
folder, then run `vale sync` in Docker to fetch the upstream packages the book's Vale config
lists.

Dry run by default: says what it would copy and whether the copy in the book is current.
--fix copies the package and runs `vale sync`.

The book is found by walking up from DIR (default: the working folder); --config names its
book.yaml. The Vale config is rules.vale_ini in book.yaml; the styles folder is its StylesPath,
which must be inside the book folder. The Docker image is tools.vale_image, pinned to a tag.
Safe to run again: nothing changes when nothing changed."""

EPILOG = """exit codes: 0 done or dry run (or SKIPPED: no Docker), 2 the book or its Vale config
could not be read."""


def parse_arguments(argv):
    parser = argparse.ArgumentParser(prog="vale-sync.py", description=DESCRIPTION, epilog=EPILOG,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_book_arguments(parser)
    parser.add_argument("--fix", action="store_true", help="copy the package and run vale sync")
    parser.add_argument("--verbose", action="store_true", help="say what was copied")
    return parser.parse_args(argv)


def report_dry_run(settings):
    if package_copy_is_current(settings):
        print(f"{PACKAGE_NAME} in {settings.package_copy} is current; nothing to copy")
    else:
        print(f"Would copy {PACKAGE_NAME} to {settings.package_copy} (missing or stale)")
    print(f"Would run 'vale sync' in Docker ({settings.image}) for the packages in "
          f"{settings.vale_ini}")
    print("Dry run: nothing written. Run again with --fix to write.")


def main(argv=None):
    arguments = parse_arguments(argv)
    try:
        settings = load_vale_settings(arguments)
    except ValeSetupError as error:
        print(f"vale-sync.py: {error}", file=sys.stderr)
        return 2
    if not arguments.fix:
        report_dry_run(settings)
        return 0
    copy_package(settings)
    if arguments.verbose:
        print(f"vale-sync.py: {PACKAGE_NAME} copied to {settings.package_copy}")
    if not docker_found():
        print("SKIPPED   docker not found, so 'vale sync' did not run")
        return 0
    return run_vale(settings, ["sync"])


if __name__ == "__main__":
    sys.exit(main())
