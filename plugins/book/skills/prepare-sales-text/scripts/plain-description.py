#!/usr/bin/env python3
import argparse
import sys
sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

import surfaces
from book_config import ConfigError, add_config_arguments, config_from_args

DESCRIPTION = """Make the plain-text store description for fields that take no markup
(Google Books, most other stores) from the Amazon store description.

The plain text is DERIVED: never edit it by hand, change the HTML and run this again.
List items become '- ' lines, block tags become blank lines, comments and tags go.

Reads sales_text.amazon (default <publishing.sales_text>/amazon.html) and, with --fix, writes
sales_text.plain_description (default <publishing.sales_text>/plain-description.txt). Without --fix it prints
the text. Character and word counts go to stderr."""


def build_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", nargs="?", help="the HTML store description "
                        "(default: sales_text.amazon from the book config)")
    parser.add_argument("--output", help="where --fix writes (default: sales_text.plain_description)")
    parser.add_argument("--fix", action="store_true", help="write the plain text to the output file")
    add_config_arguments(parser)
    return parser


def main():
    arguments = build_parser().parse_args()
    try:
        config = config_from_args(arguments)
    except ConfigError as error:
        sys.stderr.write(f"plain-description: {error}\n")
        return 2
    source = Path(arguments.source) if arguments.source else surfaces.sales_text_path(config, "amazon")
    if source is None or not source.is_file():
        sys.stderr.write(f"plain-description: store description not found: {source}\n")
        return 2
    text = surfaces.html_to_plain(surfaces.read_text(source))
    if arguments.fix:
        target = Path(arguments.output) if arguments.output else surfaces.sales_text_path(
            config, "plain_description")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        sys.stderr.write(f"wrote {target}\n")
    else:
        sys.stdout.write(text)
    sys.stderr.write("%d chars, %d words\n" % (len(text.strip()), len(text.split())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
