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
                          skipped_for_missing, tool_failed)

DESCRIPTION = """Check the Amazon store description against the store's own rules.

Counts what KDP counts: characters INCLUDING the HTML tags, after comments are removed
(comments are notes for the author and are not pasted). The limit, the allowed tags and
the prohibited content are in references/store-limits.md; the limit can be changed with
sales_text.amazon_limit when the store changes it.

Classes:
  over-limit          defect         more characters than the store accepts
  tag-not-allowed     defect         a tag the store does not render
  tag-not-closed      defect         an opening tag with no closing tag, or the reverse
  web-address         defect         a URL with http(s):// or www. (prohibited)
  email-address       defect         an email address (prohibited)
  emoji               defect         a picture emoji, or a symbol made an emoji by U+FE0F
                                     (prohibited)
  bare-domain         advisory       a lower-case name.com-like word: a web address, or a
                                     package or product name such as socket.io
  symbol              advisory       a dingbat or other symbol such as a check mark; the
                                     store may read it as an emoji
  price-or-offer      advisory       a price, discount or offer (prohibited, but the words
                                     can have another sense)
  review-request      advisory       asks for reviews (prohibited)
  size                informational  characters, words, headroom
  above-the-fold      informational  the first two sentences, which must carry the pitch

Exit 0 clean, 1 defects, 2 the file could not be read."""

CLASSES = {
    "over-limit": DEFECT,
    "tag-not-allowed": DEFECT,
    "tag-not-closed": DEFECT,
    "web-address": DEFECT,
    "email-address": DEFECT,
    "emoji": DEFECT,
    "bare-domain": ADVISORY,
    "symbol": ADVISORY,
    "price-or-offer": ADVISORY,
    "review-request": ADVISORY,
    "size": INFORMATIONAL,
    "above-the-fold": INFORMATIONAL,
}

TAG = re.compile(r"<\s*(/?)\s*([a-zA-Z][a-zA-Z0-9]*)[^>]*?(/?)\s*>")
WEB_ADDRESS = re.compile(r"(https?://\S+|\bwww\.\S+)", re.I)
BARE_DOMAIN = re.compile(r"(?<![/@.\w-])[a-z0-9-]+\.(com|org|net|io|dev)\b(?![.\w-])")
EMAIL_ADDRESS = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
EMOJI = re.compile("([\U0001F300-\U0001FAFF]|[\u2600-\u27BF]\uFE0F)")
SYMBOL = re.compile("([\U0001F000-\U0001F2FF]|[\u2600-\u27BF](?!\uFE0F))")
PRICE_OR_OFFER = re.compile(r"([$€£]\s?\d|\b\d+\s?%\s?off\b|\bdiscount\b|\bon sale\b|"
                            r"\bfree\b|\blimited time\b)", re.I)
REVIEW_REQUEST = re.compile(r"\b(leave|write|post)\s+(a\s+|an\s+)?(honest\s+)?review", re.I)
SELF_CLOSING = ("br",)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'“])")


def check_tags(body, report):
    allowed = set(surfaces.ALLOWED_STORE_TAGS)
    open_tags = []
    for match in TAG.finditer(body):
        closing, name = match.group(1) == "/", match.group(2).lower()
        if name not in allowed:
            report.add(name, "tag-not-allowed", f"<{match.group(0)[1:]} is not rendered by the store")
            continue
        if name in SELF_CLOSING or match.group(3) == "/":
            continue
        if not closing:
            open_tags.append(name)
        elif open_tags and open_tags[-1] == name:
            open_tags.pop()
        else:
            report.add(name, "tag-not-closed", f"</{name}> closes a tag that is not open")
    for name in open_tags:
        report.add(name, "tag-not-closed", f"<{name}> is never closed")


def check_content(plain, report):
    without_addresses = EMAIL_ADDRESS.sub(" ", WEB_ADDRESS.sub(" ", plain))
    for pattern, finding_class, text in (
            (WEB_ADDRESS, "web-address", plain), (EMAIL_ADDRESS, "email-address", plain),
            (BARE_DOMAIN, "bare-domain", without_addresses), (EMOJI, "emoji", plain),
            (SYMBOL, "symbol", plain), (PRICE_OR_OFFER, "price-or-offer", plain),
            (REVIEW_REQUEST, "review-request", plain)):
        for match in pattern.finditer(text):
            report.add(match.group(0).strip(), finding_class, context(text, match))


def context(text, match, width=40):
    start, end = max(0, match.start() - width), min(len(text), match.end() + width)
    return "..." + " ".join(text[start:end].split()) + "..."


def check_size(body, plain, limit, report):
    characters = len(body)
    words = surfaces.word_count(plain)
    if characters > limit:
        report.add("store-description", "over-limit",
                   f"{characters} characters of {limit}, {characters - limit} over")
    report.add("store-description", "size",
               f"{characters} characters of {limit} ({limit - characters} left), {words} words")
    sentences = SENTENCE_SPLIT.split(" ".join(plain.split()))
    report.add("store-description", "above-the-fold", " ".join(sentences[:2]))


def build_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", nargs="?", help="the HTML store description "
                        "(default: sales_text.amazon from the book config)")
    add_config_arguments(parser)
    add_output_arguments(parser)
    return parser


def main():
    arguments = build_parser().parse_args()
    try:
        config = config_from_args(arguments)
    except ConfigError as error:
        return tool_failed(str(error), "store-description-check")
    source = Path(arguments.source) if arguments.source else surfaces.sales_text_path(config, "amazon")
    if arguments.source and not source.is_file():
        return tool_failed(f"store description not found: {source}", "store-description-check")
    if skipped_for_missing("store-description-check", source, "store description",
                           arguments.format):
        return 0
    markup = surfaces.read_text(source)
    body = surfaces.store_body(markup)
    plain = surfaces.html_to_plain(markup)
    report = CheckReport("store-description-check", CLASSES)
    check_size(body, plain, int(surfaces.sales_text_setting(config, "amazon_limit")), report)
    check_tags(body, report)
    check_content(plain, report)
    return report.emit(arguments.format)


if __name__ == "__main__":
    sys.exit(main())
