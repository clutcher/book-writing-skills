#!/usr/bin/env python3
"""Write the book settings the Lua filters read, as a pandoc metadata file.

build-book.sh passes the result to pandoc with --metadata-file, under the one key
"build-settings". digital-mode.lua and citation-links.lua read it; a key that is not set
in the book keeps the filter's own default. The keys are listed in references/settings.md.
"""

import argparse
import json
import sys
sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

from book_config import ConfigError, add_config_arguments, config_from_args

SETTINGS_KEY = "build-settings"
LIST_KEYS = ("latex_commands_to_drop", "front_matter_pages", "copyright_markers")
MAP_KEYS = ("language_codes", "heading_types")
TEXT_KEYS = ("chapter_heading_word", "emblem_alt", "references_heading")
EXIT_TOOL_FAILED = 2
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class SettingShapeError(Exception):
    pass


def as_list(name, value):
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        return [str(item) for item in value]
    raise SettingShapeError(f"book.{name} must be a list of words")


def as_map(name, value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as error:
            raise SettingShapeError(f"book.{name} must be a mapping") from error
    if not isinstance(value, dict):
        raise SettingShapeError(f"book.{name} must be a mapping")
    return {str(key): str(item) for key, item in value.items()}


def filter_settings(book):
    settings = {}
    for name in LIST_KEYS:
        if book.get(name) is not None:
            settings[name] = as_list(name, book.get(name))
    for name in MAP_KEYS:
        if book.get(name) is not None:
            settings[name] = as_map(name, book.get(name))
    for name in TEXT_KEYS:
        if book.get(name) is not None:
            settings[name] = str(book.get(name))
    return {SETTINGS_KEY: settings}


def self_test():
    from book_config import load_config
    new_book = filter_settings(load_config(start=FIXTURES / "new-book").book)[SETTINGS_KEY]
    plain_book = filter_settings(load_config(start=FIXTURES / "plain-book").book)[SETTINGS_KEY]
    overridden = filter_settings(load_config(start=FIXTURES / "plain-book",
                                             overrides=["book.emblem_alt=Seal"]).book)[SETTINGS_KEY]
    checks = [
        ("list setting read from book.yaml", new_book.get("latex_commands_to_drop"), ["enlargethispage"]),
        ("map setting read from book.yaml", new_book.get("language_codes"), {"welsh": "cy"}),
        ("text setting read from book.yaml", new_book.get("emblem_alt"), "Test press emblem"),
        ("a book that sets no filter key gives nothing", plain_book, {}),
        ("a --set override reaches the filters", overridden.get("emblem_alt"), "Seal"),
    ]
    failures = [(name, got, expected) for name, got, expected in checks if got != expected]
    for name, got, expected in failures:
        print(f"FAIL  {name}: got {got!r}, expected {expected!r}")
    print(f"filter-settings self-test: {len(checks) - len(failures)}/{len(checks)} passed")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    parser.add_argument("--output", metavar="FILE", help="write here instead of to stdout")
    parser.add_argument("--self-test", action="store_true", help="run the built-in tests on the fixture books")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    try:
        text = json.dumps(filter_settings(config_from_args(args).book), indent=2, ensure_ascii=False)
    except (ConfigError, SettingShapeError) as problem:
        sys.stderr.write(f"filter-settings: {problem}\n")
        return EXIT_TOOL_FAILED
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
