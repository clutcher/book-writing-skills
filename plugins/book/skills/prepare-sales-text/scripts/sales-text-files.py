#!/usr/bin/env python3
import argparse
import json
import sys
sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

import surfaces
from book_config import ConfigError, add_config_arguments, config_from_args

DESCRIPTION = """List every book file the prepare-sales-text skill reads or writes, with its real path
in this book and whether it exists. Run it first: the file names in the skill's text
(rules/decisions.md, thinking/author/audience.md, amazon.html and so on) are only the default
names, and a book can keep its files anywhere.

Book keys:       rules.decisions, thinking.audience, rules.voice, rules.glossary,
                 manuscript.dir, work.runs, publishing.sales_text
Sales text keys: sales_text.back_cover, sales_text.amazon, sales_text.keywords,
                 sales_text.intended_impression, sales_text.plain_description, sales_text.contents,
                 sales_text.contents_full, sales_text.preface

A report, not a check: exit 0, or 2 when the book config cannot be read."""

BOOK_KEYS = ("rules.decisions", "thinking.audience", "rules.voice", "rules.glossary",
             "manuscript.dir", "work.runs", "publishing.sales_text")
MARKETING_KEYS = ("back_cover", "amazon", "keywords", "intended_impression", "plain_description",
                  "contents", "contents_full")


def book_path(config, key):
    try:
        value = config.path(key)
    except (KeyError, ConfigError):
        return None
    return Path(value) if value else None


def resolved_files(config):
    files = [(key, book_path(config, key)) for key in BOOK_KEYS]
    files += [(f"sales_text.{name}", surfaces.sales_text_path(config, name)) for name in MARKETING_KEYS]
    files.append(("sales_text.preface", surfaces.preface_path(config)))
    return [{"key": key, "path": str(path) if path else "", "exists": bool(path) and path.exists()}
            for key, path in files]


def build_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    add_config_arguments(parser)
    return parser


def main():
    arguments = build_parser().parse_args()
    try:
        files = resolved_files(config_from_args(arguments))
    except ConfigError as error:
        sys.stderr.write(f"sales-text-files: {error}\n")
        return 2
    if arguments.format == "json":
        print(json.dumps({"files": files}, indent=2, ensure_ascii=False))
        return 0
    for item in files:
        state = "present" if item["exists"] else "missing"
        print(f"{item['key']}\t{item['path'] or '(not set)'}\t{state}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
