import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[3] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from book_config import (ConfigError, add_config_arguments, config_from_args, load_config,
                         natural_sort_key)
from check_output import EXIT_TOOL_FAILED, tool_failed

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent
FIXTURES_DIR = SCRIPTS_DIR / "fixtures"
SAMPLE_BOOK = FIXTURES_DIR / "sample-book"

__all__ = [
    "ConfigError", "EXIT_TOOL_FAILED", "FIXTURES_DIR", "SAMPLE_BOOK",
    "SKILL_DIR", "add_config_arguments", "coined_words", "config_for_targets", "is_english_book",
    "load_config", "markdown_files", "natural_sort_key", "skipped_for_language", "tool_failed",
    "watch_words",
]


def config_for_targets(args, targets):
    return config_from_args(args, targets=targets)


def markdown_files(targets, config):
    if not targets:
        return [shown_from_working_folder(manuscript_file.path)
                for manuscript_file in config.manuscript_files()]
    found = []
    for target in targets:
        path = Path(target)
        if path.is_dir():
            found.extend(sorted(path.rglob("*.md"),
                                key=lambda file: natural_sort_key(file.relative_to(path).as_posix())))
        elif path.is_file():
            found.append(path)
        else:
            raise FileNotFoundError(f"not a file or folder: {target}")
    return found


def shown_from_working_folder(path):
    try:
        return Path(path).relative_to(Path.cwd())
    except ValueError:
        return Path(path)


def watch_words(config, name):
    value = config.terms.watch_words.get(name)
    return value if isinstance(value, dict) else {}


def coined_words(config, roles=("primary", "antonym")):
    words = set()
    for family in config.terms.families:
        if family.role in roles:
            words.add(family.term.lower())
            words.update(word.lower() for word in family.also)
    return words


def is_english_book(config):
    return str(config.book.language or "en").lower().startswith("en")


def skipped_for_language(config, tool):
    print(f"SKIPPED   {tool}: the rules of this check are for English prose, and "
          f"book.language is {config.book.language}")
    return 0
