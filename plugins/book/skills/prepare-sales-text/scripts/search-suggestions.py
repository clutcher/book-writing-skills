#!/usr/bin/env python3
import argparse
import datetime
import json
import sys
sys.dont_write_bytecode = True
import urllib.error
import urllib.parse
import urllib.request

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
with every result; the endpoint is public and undocumented and can change without notice.
Exit 0, or 2 when the endpoint cannot be reached."""

ENDPOINT = "https://completion.amazon.com/api/2017/suggestions"
STORE_ALIASES = {"books": "stripbooks", "kindle": "digital-text", "all": "aps"}
US_MARKET = "ATVPDKIKX0DER"


def suggestions(prefix, alias, market, timeout):
    query = urllib.parse.urlencode({
        "session-id": "000-0000000-0000000",
        "page-type": "Gateway",
        "lop": "en_US",
        "site-variant": "desktop",
        "client-info": "amazon-search-ui",
        "mid": market,
        "alias": alias,
        "suggestion-type": "KEYWORD",
        "prefix": prefix,
    })
    request = urllib.request.Request(f"{ENDPOINT}?{query}", headers={"User-Agent": "Mozilla/5.0"})
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
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser


def main():
    arguments = build_parser().parse_args()
    results = {}
    for prefix in arguments.prefixes:
        try:
            results[prefix] = suggestions(prefix, STORE_ALIASES[arguments.store], arguments.market,
                                          arguments.timeout)
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            sys.stderr.write(f"search-suggestions: cannot reach the endpoint: {error}\n")
            return 2
    asked_on = datetime.date.today().isoformat()
    if arguments.format == "json":
        print(json.dumps({"date": asked_on, "store": arguments.store, "market": arguments.market,
                          "suggestions": results}, indent=2, ensure_ascii=False))
        return 0
    print(f"date {asked_on}, store {arguments.store}, market {arguments.market}")
    for prefix, values in results.items():
        print(f"{prefix}\t{' | '.join(values) if values else '(nothing)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
