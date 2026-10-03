#!/usr/bin/env python3
import argparse
import datetime
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from user_agent import USER_AGENT

DESCRIPTION = """Ask the Amazon search box what it suggests for each prefix: the only free
signal about what shoppers type. Used by the 'keywords' mode to test every candidate word.

What the answer means (references/pick-keywords.md):
  echoes itself       the words are a real query stem
  completes elsewhere the bare word sells something else (a vapor barrier, a sofa)
  completes to a book one rival title owns the query
  nothing             nobody types it

Suggestions measure SUPPLY, not demand: Amazon publishes no search volumes, and an empty
answer cannot tell an unmet need from a query nobody types. The first line of the answer
(the 'date', 'store' and 'market' fields in JSON) says when and where it was asked: record it
with every result.

This calls an unofficial, undocumented Amazon endpoint (the one behind the search box). It
may change or stop at any time. You run it at your own discretion and under Amazon's terms.
So it goes online only with --online; it names itself in its User-Agent, waits --delay
seconds between prefixes and asks at most --max prefixes per run.

The manual way, which needs no script: open the Amazon store, choose the Books (or Kindle)
department, type each word into the search box slowly, and write down what the drop-down
list suggests, with the date.

Without --online it prints the manual way and a SKIPPED line, and exits 0.
Exit 0, or 2 when the endpoint cannot be reached."""

DEFAULT_DELAY = 2.0
DEFAULT_MAX_PREFIXES = 20
MANUAL_WAY = ("manual way: in the Amazon store choose the Books (or Kindle) department, type "
              "each word into the search box, and write down the drop-down suggestions with "
              "the date")

ENDPOINT = "https://completion.amazon.com/api/2017/suggestions"
STORE_ALIASES = {"books": "stripbooks", "kindle": "digital-text", "all": "aps"}
US_MARKET = "ATVPDKIKX0DER"


def suggestions(prefix, alias, market, timeout):
    query = urllib.parse.urlencode({
        "lop": "en_US",
        "mid": market,
        "alias": alias,
        "suggestion-type": "KEYWORD",
        "prefix": prefix,
    })
    request = urllib.request.Request(f"{ENDPOINT}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.load(response)
    return [item.get("value", "") for item in data.get("suggestions", [])]


def build_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("prefixes", nargs="+", help="words to test, one prefix per argument")
    parser.add_argument("--store", choices=sorted(STORE_ALIASES), default="books",
                        help="which department to ask (default: books)")
    parser.add_argument("--market", default=US_MARKET,
                        help="Amazon marketplace id (default: the US store)")
    parser.add_argument("--online", action="store_true",
                        help="ask the unofficial Amazon endpoint (without it: no network)")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                        help="seconds to wait between prefixes (default %(default)s)")
    parser.add_argument("--max", type=int, default=DEFAULT_MAX_PREFIXES,
                        help="most prefixes asked in one run (default %(default)s)")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser


def main():
    arguments = build_parser().parse_args()
    if not arguments.online:
        print(MANUAL_WAY)
        print("SKIPPED  no network without --online (the endpoint is unofficial; see --help)")
        return 0
    asked = arguments.prefixes[:arguments.max]
    not_asked = arguments.prefixes[arguments.max:]
    results = {}
    for number, prefix in enumerate(asked):
        if number:
            time.sleep(arguments.delay)
        try:
            results[prefix] = suggestions(prefix, STORE_ALIASES[arguments.store], arguments.market,
                                          arguments.timeout)
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            sys.stderr.write(f"search-suggestions: cannot reach the endpoint: {error}\n")
            return 2
    asked_on = datetime.date.today().isoformat()
    if arguments.format == "json":
        print(json.dumps({"date": asked_on, "store": arguments.store, "market": arguments.market,
                          "suggestions": results, "not_asked": not_asked},
                         indent=2, ensure_ascii=False))
        return 0
    print(f"date {asked_on}, store {arguments.store}, market {arguments.market}")
    for prefix, values in results.items():
        print(f"{prefix}\t{' | '.join(values) if values else '(nothing)'}")
    if not_asked:
        print(f"not asked (--max {arguments.max} reached): {' '.join(not_asked)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
