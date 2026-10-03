#!/usr/bin/env python3
import argparse
import json
import sys
sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

import surfaces
from book_config import ConfigError, add_config_arguments, config_from_args, manuscript_files

DESCRIPTION = """Measure the selling copy, so no figure is ever quoted from memory or from
old prose. Prints, for every surface (or for the files given):

  words, characters, blocks, the longest block and its word count,
  the bold spans read alone in order (the scan path), and whether each one is a full
  sentence (a scanner reads the bold spans as the whole pitch, so a fragment is a gap).

Surfaces from the book config: the back cover (sales_text.back_cover, markdown), the store
description (sales_text.amazon, HTML), the ebook description (the book's 'description'
metadata) and the preface opening. Give files instead to measure drafts or old versions.
--text also prints each surface as plain text, for the text checks of the write-text skill.

--sample shows how far the store's free sample reaches (rule C3 in
references/copy-review.md). The store gives a share of the pages (print 20%, ebook 10%,
sales_text.sample_print_share and sales_text.sample_ebook_share). Pages hold about the same
number of words each, so the sample ends where that share of the manuscript words ends.
It prints the last manuscript file that is fully inside each sample, and the file where the
sample stops. An estimate by words: a book with many figures or code pages differs.
A report, not a check: it always exits 0 unless a file cannot be read (exit 2)."""


def measure(surface):
    blocks = surface.blocks
    longest = max(blocks, key=surfaces.word_count) if blocks else ""
    return {
        "surface": surface.name,
        "path": str(surface.path),
        "words": surface.words,
        "characters": len(surface.plain.strip()),
        "blocks": len(blocks),
        "longest_block_words": surfaces.word_count(longest),
        "longest_block": longest,
        "bold_spans": [{"text": span, "full_sentence": surfaces.is_full_sentence(span)}
                       for span in surface.bold_spans],
        "text": surface.plain,
    }


def render_text(measurements, with_text):
    lines = []
    for item in measurements:
        lines.append(f"== {item['surface']}  ({item['path']})")
        lines.append(f"words {item['words']}, characters {item['characters']}, "
                     f"blocks {item['blocks']}, longest block {item['longest_block_words']} words")
        if item["longest_block"]:
            lines.append(f"longest block: {item['longest_block'][:160]}")
        if item["bold_spans"]:
            lines.append(f"scan path ({len(item['bold_spans'])} bold spans, read alone):")
            for span in item["bold_spans"]:
                marker = "" if span["full_sentence"] else "   [not a full sentence]"
                lines.append(f"  - {span['text']}{marker}")
        if with_text:
            lines.append("")
            lines.append(item["text"].rstrip())
        lines.append("")
    return "\n".join(lines)


def sample_reach(config):
    files = [(item.path, surfaces.word_count(surfaces.markdown_to_plain(surfaces.read_text(item.path))))
             for item in manuscript_files(config)]
    total = sum(words for _, words in files)
    reach = []
    for label, key in (("print", "sample_print_share"), ("ebook", "sample_ebook_share")):
        share = float(surfaces.sales_text_setting(config, key))
        limit = total * share
        running, last_inside, stops_in = 0, None, None
        for path, words in files:
            if running + words <= limit:
                last_inside = path.name
            elif stops_in is None:
                stops_in = path.name
            running += words
        reach.append({"sample": label, "share": share, "words": round(limit),
                      "total_words": total, "last_file_inside": last_inside,
                      "stops_in": stops_in})
    return reach


def render_sample(reach):
    lines = []
    for item in reach:
        lines.append(f"== free sample, {item['sample']} ({item['share']:.0%}, about "
                     f"{item['words']} of {item['total_words']} words)")
        lines.append(f"last file fully inside: {item['last_file_inside'] or '(none)'}")
        lines.append(f"stops inside: {item['stops_in'] or '(the sample holds the whole book)'}")
        lines.append("")
    return "\n".join(lines)


def build_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", help="files to measure instead of the book's surfaces "
                        "(.md, .html or plain text)")
    parser.add_argument("--text", action="store_true", help="also print each surface as plain text")
    parser.add_argument("--sample", action="store_true",
                        help="show how far the free print and ebook samples reach")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    add_config_arguments(parser)
    return parser


def print_sample(arguments):
    try:
        reach = sample_reach(config_from_args(arguments))
    except (ConfigError, OSError) as error:
        sys.stderr.write(f"copy-stats: {error}\n")
        return 2
    if arguments.format == "json":
        print(json.dumps({"sample": reach}, indent=2, ensure_ascii=False))
    else:
        print(render_sample(reach), end="")
    return 0


def main():
    arguments = build_parser().parse_args()
    if arguments.sample:
        return print_sample(arguments)
    try:
        if arguments.files:
            found, missing = [surfaces.load_file_as_surface(path) for path in arguments.files], []
        else:
            found, missing = surfaces.load_surfaces(config_from_args(arguments))
    except (ConfigError, OSError) as error:
        sys.stderr.write(f"copy-stats: {error}\n")
        return 2
    measurements = [measure(surface) for surface in found]
    if arguments.format == "json":
        print(json.dumps({"surfaces": measurements, "missing": missing}, indent=2, ensure_ascii=False))
    else:
        print(render_text(measurements, arguments.text), end="")
        for name in missing:
            print(f"== {name}  (not found)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
