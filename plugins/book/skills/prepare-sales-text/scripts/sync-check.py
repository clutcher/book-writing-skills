#!/usr/bin/env python3
import argparse
import re
import sys
sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

import surfaces
from book_config import ConfigError, add_config_arguments, config_from_args
from check_output import (ADVISORY, DEFECT, INFORMATIONAL, CheckReport, add_output_arguments,
                          tool_failed)

DESCRIPTION = """Check that the selling surfaces agree with each other and with the book's
decisions. The surfaces are NOT copies of each other; this check finds the mechanical part
of a disagreement, and the agent reads the rest (see "Keeping the surfaces in step" in SKILL.md).

Surfaces: the back cover (sales_text.back_cover), the store description (sales_text.amazon),
the ebook description (the book's 'description' metadata) and the opening paragraph of the
preface (sales_text.preface, or the first front-matter file named *preface*).

Book settings it reads (all optional, in book.yaml under sales_text):
  retired_phrases   wordings the author decided never to use again
  shared_spans      wordings that must stay word for word the same on every selling surface

Classes:
  retired-phrase        defect         a retired wording is back on a surface
  shared-span-missing   advisory       a shared wording is missing or changed on a surface
  quantity-wording      advisory       one quantity in two wordings ('thirty years' and
                                       'three decades') reads as a slip or as two claims
  opening-echo          advisory       the preface opening repeats a long run of words from a
                                       selling surface (the buyer meets both minutes apart)
  surface-missing       advisory       a surface file or value does not exist, so nothing
                                       was compared with it
  opening               informational  the first sentence of each selling surface
  bold-path             informational  the bold spans of a surface, read together

With fewer than two selling surfaces there is nothing to compare: the report ends with
'SKIPPED fewer than two selling surfaces' instead of a clean total, unless a retired
wording was found on the one surface there is.
Exit 0 clean or skipped, 1 defects, 2 the config could not be read."""

CLASSES = {
    "retired-phrase": DEFECT,
    "shared-span-missing": ADVISORY,
    "quantity-wording": ADVISORY,
    "opening-echo": ADVISORY,
    "surface-missing": ADVISORY,
    "opening": INFORMATIONAL,
    "bold-path": INFORMATIONAL,
}

SELLING_SURFACES = ("back-cover", "store-description", "ebook-description")
ECHO_RUN_WORDS = 8
UNITS = {
    "year": ("year", 1), "decade": ("year", 10), "century": ("year", 100),
    "month": ("month", 1), "week": ("week", 1), "day": ("day", 1),
}
SMALL_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100, "dozen": 12,
}
NUMBER_TOKEN = r"(\d+|(?:%s)(?:-(?:%s))?)" % ("|".join(SMALL_NUMBERS), "|".join(SMALL_NUMBERS))
QUANTITY = re.compile(r"\b%s[\s-]+(\w+)" % NUMBER_TOKEN, re.I)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'“])")
WORD = re.compile(r"[\w'-]+")


def normalised(text):
    return " ".join(text.lower().replace("’", "'").split())


def number_value(token):
    token = token.lower()
    if token.isdigit():
        return int(token)
    return sum(SMALL_NUMBERS[part] for part in token.split("-"))


def unit_of(word):
    word = word.lower()
    for singular, unit in UNITS.items():
        if word in (singular, singular + "s", "centuries" if singular == "century" else ""):
            return unit
    return (word[:-1] if word.endswith("s") and len(word) > 3 else word), 1


def quantities(text):
    for match in QUANTITY.finditer(text):
        unit, factor = unit_of(match.group(2))
        yield (number_value(match.group(1)) * factor, unit), normalised(match.group(0))


def check_retired(found, retired, report):
    for surface in found:
        text = normalised(surface.plain)
        for phrase in retired:
            if normalised(phrase) in text:
                report.add(surface.name, "retired-phrase", f"'{phrase}' was retired by decision")


def check_shared(found, shared, report):
    for surface in found:
        if surface.name not in SELLING_SURFACES:
            continue
        text = normalised(surface.plain)
        for span in shared:
            if normalised(span) not in text:
                report.add(surface.name, "shared-span-missing", f"'{span}'")


def check_quantities(found, report):
    wordings = {}
    for surface in found:
        if surface.name not in SELLING_SURFACES:
            continue
        for key, wording in quantities(surface.plain):
            wordings.setdefault(key, {}).setdefault(wording, set()).add(surface.name)
    for (value, unit), forms in wordings.items():
        if len(forms) > 1:
            listed = "; ".join(f"'{form}' ({', '.join(sorted(names))})"
                               for form, names in sorted(forms.items()))
            report.add(f"{value}-{unit}", "quantity-wording", listed)


def word_runs(text, length):
    words = [word.lower() for word in WORD.findall(text)]
    return {" ".join(words[index:index + length]) for index in range(len(words) - length + 1)}


def check_opening_echo(found, report):
    preface = next((surface for surface in found if surface.name == "preface-opening"), None)
    if preface is None:
        return
    preface_runs = word_runs(preface.plain, ECHO_RUN_WORDS)
    for surface in found:
        if surface.name not in SELLING_SURFACES:
            continue
        shared = preface_runs & word_runs(surface.plain, ECHO_RUN_WORDS)
        if shared:
            report.add(surface.name, "opening-echo",
                       f"{len(shared)} runs of {ECHO_RUN_WORDS} words shared with the preface "
                       f"opening, e.g. '{sorted(shared)[0]}'")


def report_openings(found, report):
    for surface in found:
        if surface.name not in SELLING_SURFACES:
            continue
        first = SENTENCE_SPLIT.split(" ".join(surface.plain.split()))[0]
        report.add(surface.name, "opening", first)
        if surface.bold_spans:
            report.add(surface.name, "bold-path", " | ".join(surface.bold_spans))


MISSING_FILE_ADVICE = "not found; set its path in book.yaml under sales_text"
MISSING_SURFACE_ADVICE = {
    "ebook-description": "not set: write the one-line description in book.description",
}


def skipped_report(found, report):
    selling = [surface for surface in found if surface.name in SELLING_SURFACES]
    if len(selling) >= 2 or report.totals()[DEFECT]:
        return None
    skipped = CheckReport("sync-check", CLASSES)
    skipped.skip(f"fewer than two selling surfaces ({len(selling)} found)")
    return skipped


def build_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--store", help="the HTML store description (default: sales_text.amazon)")
    add_config_arguments(parser)
    add_output_arguments(parser)
    return parser


def main():
    arguments = build_parser().parse_args()
    try:
        config = config_from_args(arguments)
        found, missing = surfaces.load_surfaces(config, Path(arguments.store) if arguments.store else None)
    except ConfigError as error:
        return tool_failed(str(error), "sync-check")
    report = CheckReport("sync-check", CLASSES)
    check_retired(found, surfaces.sales_text_list(config, "retired_phrases"), report)
    check_shared(found, surfaces.sales_text_list(config, "shared_spans"), report)
    check_quantities(found, report)
    check_opening_echo(found, report)
    skipped = skipped_report(found, report)
    if skipped is not None:
        return skipped.emit(arguments.format)
    report_openings(found, report)
    for name in missing:
        report.add(name, "surface-missing", MISSING_SURFACE_ADVICE.get(name, MISSING_FILE_ADVICE))
    return report.emit(arguments.format)


if __name__ == "__main__":
    sys.exit(main())
