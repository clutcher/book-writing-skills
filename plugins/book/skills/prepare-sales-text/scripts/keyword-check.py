#!/usr/bin/env python3
import argparse
import re
import sys
sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

import listing_tables
import surfaces
from book_config import ConfigError, add_config_arguments, config_from_args
from check_output import (ADVISORY, DEFECT, INFORMATIONAL, CheckReport, add_output_arguments,
                          skipped_for_missing, tool_failed)

DESCRIPTION = """Check the chosen store keywords and categories against the store rules.

Reads the book's keywords-and-categories file (sales_text.keywords, default
<publishing.sales_text>/keywords-and-categories.md). The file shape is in
templates/keywords-and-categories.md: a '## Keywords' table with a 'Keyword' column, a
'## Categories' table with 'Format', 'Category' and 'Picker' columns, and an '## Avoid'
bullet list (other authors, their book titles, brands the book does not own).

A cell or bullet written as <...> is a template placeholder and is skipped.

Words already in the title or subtitle and words in the chosen category paths are on
KDP's own avoid list, so they are defects. Every word is checked as a whole word.

Classes:
  too-many-slots          defect         more keyword slots than the store has
  title-word              defect         a slot word is already in the title or subtitle
  category-word           defect         a slot word is in a chosen category path
  avoid-word              defect         a slot holds an item of the book's Avoid list
  quotation-marks         defect         quotes make the store match the whole phrase only
  too-many-categories     defect         more categories for one format than the store takes
  slot-too-long           advisory       over the UI-observed character limit per slot
  repeated-word           advisory       a word used in two slots adds nothing
  plural-variant          advisory       a plural or singular of a word the listing already has
  subjective-word         advisory       a quality claim or time-sensitive word
  picker-not-confirmed    advisory       a category not yet seen in the signed-in store picker
  empty-slots             informational  slots left unused
  slot-usage              informational  characters used and new index words added

Limits come from sales_text.keyword_slots, sales_text.keyword_chars and
sales_text.categories_per_format (defaults 7, 50, 3; see references/store-limits.md).
Exit 0 clean, 1 defects, 2 the file could not be read."""

CLASSES = {
    "too-many-slots": DEFECT,
    "title-word": DEFECT,
    "category-word": DEFECT,
    "avoid-word": DEFECT,
    "quotation-marks": DEFECT,
    "too-many-categories": DEFECT,
    "slot-too-long": ADVISORY,
    "repeated-word": ADVISORY,
    "plural-variant": ADVISORY,
    "subjective-word": ADVISORY,
    "picker-not-confirmed": ADVISORY,
    "empty-slots": INFORMATIONAL,
    "slot-usage": INFORMATIONAL,
}

SUBJECTIVE_WORDS = {"best", "bestseller", "bestselling", "amazing", "greatest", "top", "new",
                    "latest", "sale", "free", "discount", "cheap", "now", "ultimate", "perfect"}
FILLER_WORDS = {"and", "or", "the", "a", "an", "of", "for", "to", "in", "on", "with"}
WORD = re.compile(r"[a-z0-9][a-z0-9'-]*")
QUOTES = re.compile("[\"“”‘’]")
CONFIRMED = re.compile(r"^(yes|confirmed|\d{4}-\d{2}-\d{2})", re.I)


def words_of(text):
    found = set()
    for word in WORD.findall(text.lower()):
        found.add(word)
        found.update(part for part in word.split("-") if part)
    return found - FILLER_WORDS


def singular(word):
    if len(word) > 3 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def read_listing(path):
    text = surfaces.read_text(path)
    keywords = [listing_tables.clean_cell(listing_tables.column(row, "keyword"))
                for row in listing_tables.first_table(listing_tables.find_section(text, "keywords"))]
    categories = [
        {
            "format": listing_tables.clean_cell(listing_tables.column(row, "format")),
            "path": listing_tables.clean_cell(listing_tables.column(row, "category")),
            "picker": listing_tables.clean_cell(listing_tables.column(row, "picker")),
        }
        for row in listing_tables.first_table(listing_tables.find_section(text, "categories"))
    ]
    avoid = [listing_tables.clean_cell(item).lower()
             for item in listing_tables.bullets(listing_tables.find_section(text, "avoid"))]
    return [keyword for keyword in keywords if filled(keyword)], \
        [category for category in categories if filled(category["path"])], \
        [item for item in avoid if filled(item)]


def filled(value):
    return bool(value) and not listing_tables.is_placeholder(value)


def check_slots(keywords, title_words, category_words, avoid, limits, report):
    if len(keywords) > limits["slots"]:
        report.add("keywords", "too-many-slots", f"{len(keywords)} slots, the store has {limits['slots']}")
    elif len(keywords) < limits["slots"]:
        report.add("keywords", "empty-slots", f"{limits['slots'] - len(keywords)} of {limits['slots']} unused")
    seen = {}
    for index, keyword in enumerate(keywords, start=1):
        slot = f"slot-{index}"
        if QUOTES.search(keyword):
            report.add(slot, "quotation-marks", keyword)
        if len(keyword) > limits["chars"]:
            report.add(slot, "slot-too-long", f"{len(keyword)} characters, observed limit {limits['chars']}")
        slot_words = words_of(keyword)
        lowered = f" {' '.join(WORD.findall(keyword.lower()))} "
        for item in avoid:
            if f" {' '.join(WORD.findall(item))} " in lowered:
                report.add(slot, "avoid-word", f"'{item}' is on the book's Avoid list")
        for word in sorted(slot_words):
            if word in title_words:
                report.add(slot, "title-word", f"'{word}' is already in the title or subtitle")
            elif word in category_words:
                report.add(slot, "category-word", f"'{word}' is in a chosen category path")
            elif singular(word) in {singular(other) for other in title_words | category_words}:
                report.add(slot, "plural-variant", f"'{word}' is a variant of a title or category word")
            if word in SUBJECTIVE_WORDS:
                report.add(slot, "subjective-word", f"'{word}'")
            if word in seen:
                report.add(slot, "repeated-word", f"'{word}' is also in {seen[word]}")
            elif singular(word) in {singular(other) for other in seen}:
                report.add(slot, "plural-variant", f"'{word}' is a variant of a word in another slot")
            seen.setdefault(word, slot)
    used = sum(len(keyword) for keyword in keywords)
    new_words = set(seen) - title_words
    report.add("keywords", "slot-usage",
               f"{used} of about {limits['slots'] * limits['chars']} characters used, "
               f"{len(new_words)} index words the title and subtitle do not carry")


def check_categories(categories, limits, report):
    per_format = {}
    for category in categories:
        per_format.setdefault(category["format"] or "any", []).append(category)
    for store_format, rows in per_format.items():
        if len(rows) > limits["categories"]:
            report.add(store_format, "too-many-categories",
                       f"{len(rows)} categories, the store takes {limits['categories']} per format")
        for row in rows:
            if not CONFIRMED.match(row["picker"]):
                report.add(store_format, "picker-not-confirmed", row["path"])


def build_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", nargs="?", help="the keywords-and-categories file "
                        "(default: sales_text.keywords from the book config)")
    add_config_arguments(parser)
    add_output_arguments(parser)
    return parser


def main():
    arguments = build_parser().parse_args()
    try:
        config = config_from_args(arguments)
    except ConfigError as error:
        return tool_failed(str(error), "keyword-check")
    source = Path(arguments.source) if arguments.source else surfaces.sales_text_path(config, "keywords")
    if arguments.source and not source.is_file():
        return tool_failed(f"keywords file not found: {source}", "keyword-check")
    if skipped_for_missing("keyword-check", source, "keywords file", arguments.format):
        return 0
    keywords, categories, avoid = read_listing(source)
    title_words = words_of(" ".join(filter(None, [config.book.title or "", config.book.subtitle or ""])))
    category_words = set()
    for category in categories:
        category_words |= words_of(category["path"].replace(">", " "))
    limits = {
        "slots": int(surfaces.sales_text_setting(config, "keyword_slots")),
        "chars": int(surfaces.sales_text_setting(config, "keyword_chars")),
        "categories": int(surfaces.sales_text_setting(config, "categories_per_format")),
    }
    report = CheckReport("keyword-check", CLASSES)
    check_slots(keywords, title_words, category_words, avoid, limits, report)
    check_categories(categories, limits, report)
    return report.emit(arguments.format)


if __name__ == "__main__":
    sys.exit(main())
