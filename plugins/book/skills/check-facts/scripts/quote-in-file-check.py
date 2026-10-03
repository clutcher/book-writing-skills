#!/usr/bin/env python3
"""Hold each `Verified quotes` line to the cached file it claims to have been read from.

A quotes entry with verified quotes says somebody read the source and copied the words
out of it. That can be false while every other check passes: the cache can hold a
different author's page on the same topic, a discussion thread about the source, or an
arXiv abstract page standing in for the paper whose table the entry quotes.
unread-sources.py cannot see these, because they all HAVE quotes entries. The question
here is not "was the source read" but "is the file on disk the source the entry says".

The cached ORIGINAL is searched too, meta tags included: a script-rendered page can
extract to nothing while the quote sits in its `og:description`. The extraction's size
describes the extraction, never the holding.

Classes:
  quote-not-found       ADVISORY  a quote is absent from every cached form, and so is
                                  every 8-word window of it. A question for a person,
                                  not proof of a bad entry: open the page image
  no-extraction         DEFECT    the entry quotes a key with no `<Key>.txt`
  cache-stub            DEFECT    the extraction is under 2000 characters
  cache-landing         DEFECT    the cache is an abstract page, landing page or
                                  download interstitial (many hosts answer HTTP 200
                                  for those, so `status: cached` proves nothing)
  identity-mismatch     DEFECT    almost no title word and no author surname appear
  cache-title-mismatch  DEFECT    no title word in the OPENING of the document: a page
                                  that NAMES the author but is somebody else's
  text-unusable         DEFECT    under 90% printable ASCII: a broken font encoding or
                                  a translation into another script
  holdings-stale        DEFECT    the fetch record says paywalled/failed while a real
                                  file sits on disk and was read (it gets re-fetched
                                  forever and stays on the download list)
  extraction-stale      DEFECT    a newer original sits beside the one the .txt came from
  quote-partial         INFORMATIONAL  an 8-word window matches, the full string does not
  extraction-missing    INFORMATIONAL  no usable .txt, but every quote is in the original
  ocr-quote-miss        INFORMATIONAL  a miss on OCR text; such quotes are confirmed
                                  against the page image, not the text
  ocr-title-unmatched   INFORMATIONAL  the title check on OCR text

Matching is aggressive on purpose, because a false NOT-FOUND reads exactly like "the
source does not say this". Quote and cache are squashed to bare letters and digits,
which absorbs ligatures, hyphenation, run-together words and case. Then, in order: the
Elsevier substitution family (`V` for ff, `W` for fi), `<Key>.layout.txt` and a fresh
plain pdftotext of the cached PDF (plain is the right mode for two-column prose), the
pieces an ellipsis joins, and an 8-word window. Every route is tried in full before
any fallback.

There is no --fix: a wrong cache is repaired by fetching the real document, a bank edit
needs judgment, and rewriting a fetch record would destroy the evidence.

Usage:
  quote-in-file-check.py
  quote-in-file-check.py --key Smi99 --verbose
  quote-in-file-check.py --self-test
"""

import argparse
import collections
import glob
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import (FETCH, OCR, SourceFolders, add_config_arguments,
                          folders_from_config, load_book, tool_failed)
from check_output import (ADVISORY, DEFECT, INFORMATIONAL, SHARED_CLASSES, CheckReport,
                          add_output_arguments, skipped_for_missing)
from source_registry import read_bank
from quote_match import (has_surname, locate_in, quotes_in, squash, surnames, title_share,
                         title_words)

TOOL = "quote-in-file-check"
CLASSES = {
    "quote-not-found": ADVISORY,
    "no-extraction": DEFECT, "cache-stub": DEFECT, "cache-landing": DEFECT,
    "identity-mismatch": DEFECT, "cache-title-mismatch": DEFECT,
    "text-unusable": SHARED_CLASSES["text-unusable"],
    "holdings-stale": DEFECT, "extraction-stale": DEFECT,
    "quote-partial": INFORMATIONAL, "extraction-missing": INFORMATIONAL,
    "ocr-quote-miss": INFORMATIONAL, "ocr-title-unmatched": INFORMATIONAL,
}

STUB_CHARS = 2000
TITLE_OVERLAP_MIN = 0.34
IDENTITY_SAMPLE = 6000
OPENING_SAMPLE = 4000

FENCE = re.compile(r"^```.*?^```", re.M | re.S)
LANDING_MARKERS = (
    "view a pdf of the paper titled", "which authors of this paper are endorsers",
    "bibliographic explorer", "submission history", "preparing to download",
    "get access to this article", "get full access", "purchase this article",
    "sign in to continue", "please enable javascript", "checking if the site",
    "verify you are human", "enable javascript and cookies to continue",
    "this site uses cookies", "download citation", "add to cart",
    "institutional login", "subscribe to view", "javascript is required",
)
LANDING_MIN_MARKERS = 2
LANDING_MAX_CHARS = 25000
LANDING_ONE_MARKER_CHARS = 8000
ASCII_MIN = 90.0
OCR_STATUS = re.compile(r"READABLE VIA OCR", re.I)


def strip_fenced(text):
    return FENCE.sub("", text)


def entries(path):
    if not Path(path).exists():
        return
    for entry in read_bank(path).entries:
        yield entry.key, entry


def field_block(block, name):
    return block.field(name) or ""


def plain_text(key, sources):
    pdf = str(sources.file(key + ".pdf"))
    if not Path(pdf).exists():
        return ""
    try:
        return subprocess.run(["pdftotext", "-q", pdf, "-"], stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, timeout=180).stdout.decode(
                                  "utf-8", "ignore")
    except (OSError, subprocess.SubprocessError):
        return ""


META = re.compile(r"<meta[^>]+?(?:property|name)\s*=\s*[\"'](?:og:description|description|"
                  r"og:title|citation_title|twitter:description)[\"'][^>]*?>", re.I | re.S)
META_CONTENT = re.compile(r"content\s*=\s*\"([^\"]*)\"|content\s*=\s*'([^']*)'", re.I | re.S)
TAG = re.compile(r"<script.*?</script>|<style.*?</style>|<[^>]+>", re.I | re.S)
ENTITIES = (("&amp;", "&"), ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " "),
            ("&lt;", "<"), ("&gt;", ">"), ("&#x27;", "'"), ("&rsquo;", "'"),
            ("&ldquo;", '"'), ("&rdquo;", '"'), ("&mdash;", "-"), ("&ndash;", "-"))
ROUTES = ("txt", "layout", "src", "html-meta", "html-body", "pdf-plain")


def unescape(text):
    for entity, plain in ENTITIES:
        text = text.replace(entity, plain)
    return text


def original(key, sources, suffixes):
    for suffix in suffixes:
        path = sources.file(key + suffix)
        if path.exists():
            with open(path, errors="ignore", encoding="utf-8") as handle:
                return handle.read()
    return ""


def meta_text(html):
    found = []
    for tag in META.findall(html):
        for match in META_CONTENT.finditer(tag):
            found.append(unescape(match.group(1) or match.group(2) or ""))
    return " ".join(found)


def haystack(key, sources, text, cache, route):
    store = cache.setdefault(key, {})
    if route in store:
        return store[route]
    if route == "txt":
        store[route] = squash(text)
    elif route == "layout":
        path = sources.file(key + ".layout.txt")
        store[route] = squash(path.read_text(errors="ignore", encoding="utf-8")) if path.exists() else ""
    elif route == "src":
        store[route] = squash(original(key, sources, (".src.txt", ".md", ".json")))
    elif route == "html-meta":
        store[route] = squash(meta_text(original(key, sources, (".html", ".htm"))))
    elif route == "html-body":
        html = original(key, sources, (".html", ".htm"))
        store[route] = squash(unescape(TAG.sub(" ", html))) if html else ""
    else:
        store[route] = squash(plain_text(key, sources))
    return store[route]


def locate(quote, key, sources, text, cache):
    texts = [(route, haystack(key, sources, text, cache, route)) for route in ROUTES]
    route, how = locate_in(quote, texts)
    if not route:
        return ""
    return route if how == "full" else route + "+" + how


def landing_markers(text):
    low = text.lower()
    return [marker for marker in LANDING_MARKERS if marker in low]


def printable_share(text):
    sample = text[:200000]
    if not sample:
        return 100.0
    good = sum(1 for char in sample if char == "\n" or char == "\t" or 32 <= ord(char) < 127)
    return 100.0 * good / len(sample)


PROVENANCE = re.compile(r"^=== OCR-PROVENANCE ===.*?=== END OCR-PROVENANCE ===\s*", re.S)


def opening_mismatch(key, registry, text):
    title = field_block(registry.get(key, ""), "Full title")
    wanted = title_words(title)
    if not wanted:
        return None
    head = squash(PROVENANCE.sub("", text)[:OPENING_SAMPLE])
    if any(word in head for word in wanted):
        return None
    return 'no title word of "%s" in the first %d characters' % (title, OPENING_SAMPLE)


def identity(key, block, registry, text):
    source = registry.get(key, "")
    title = field_block(source, "Full title") or re.sub(r"[*\"]", "", block.split("\n")[0])
    authors = field_block(source, "Authors")
    hay = squash(text[:IDENTITY_SAMPLE]) or squash(text)
    whole = squash(text)
    wanted = title_words(title)
    if not wanted:
        return None
    overlap = title_share(title, whole)
    if overlap >= TITLE_OVERLAP_MIN or has_surname(authors, hay):
        return None
    return "title words %d/%d present, no author surname in the opening (%s)" % (
        round(overlap * len(wanted)), len(wanted), ", ".join(surnames(authors)[:4])
        or "no author field")


def read_fetch(key, sources):
    return sources.read_origin_record(key, FETCH) or {}


def is_ocr(key, sources, source_block, text):
    if sources.has_origin_record(key, OCR):
        return True
    if OCR_STATUS.search(field_block(source_block, "Access status")):
        return True
    return "OCR-PROVENANCE" in text[:800]


def assess(key, block, registry, sources, cache):
    facts = {"key": key, "issues": [], "quotes": [], "chars": 0, "ocr": False}
    txt = str(sources.file(key + ".txt"))
    source_block = registry.get(key, "")
    quotes = quotes_in(field_block(block, "Verified quotes"))
    facts["claimed"] = len(quotes)
    text = ""
    if Path(txt).exists():
        text = open(txt, errors="ignore", encoding="utf-8").read()
    facts["chars"] = len(text)
    facts["ocr"] = is_ocr(key, sources, source_block, text)
    fetch = read_fetch(key, sources)

    pdf = str(sources.file(key + ".pdf"))
    held = Path(sources.files).is_dir() and any(
        sources.file(key + suffix).exists()
        for suffix in (".pdf", ".html", ".htm", ".src.txt", ".layout.txt", ".md", ".json"))
    routes = []
    for quote in quotes:
        route = locate(quote, key, sources, text, cache) if text or held else ""
        routes.append(route)
        facts["quotes"].append((route, quote))
    elsewhere = [route for route in routes
                 if route.split("+")[0] in ("src", "html-meta", "html-body", "pdf-plain")]
    covered = quotes and all(routes)

    if not Path(txt).exists() or len(text.strip()) < STUB_CHARS:
        missing = "no %s.txt" % key if not Path(txt).exists() else (
            "%d characters, under the %d floor" % (len(text.strip()), STUB_CHARS))
        if "text_chars" in fetch:
            missing += " (fetch record: text_chars %s)" % fetch["text_chars"]
        if covered and elsewhere:
            facts["issues"].append(("extraction-missing", "%s; all %d quotes are in the "
                                    "cached original (%s)"
                                    % (missing, len(quotes), ", ".join(sorted(set(elsewhere))))))
        elif not quotes:
            facts["issues"].append(("extraction-missing", missing + "; no quotes claimed"))
        elif not Path(txt).exists():
            facts["issues"].append(("no-extraction", missing))
        else:
            facts["issues"].append(("cache-stub", missing))
    usable = printable_share(text) >= ASCII_MIN
    if text and not usable:
        facts["issues"].append(("text-unusable", "%.0f%% printable ASCII -- a broken font "
                                "encoding, or a non-Latin script; either way an English "
                                "quote cannot be located in it" % printable_share(text)))
    if text and usable:
        markers = landing_markers(text)
        if (len(markers) >= LANDING_MIN_MARKERS and len(text) < LANDING_MAX_CHARS) or (
                markers and len(text) < LANDING_ONE_MARKER_CHARS):
            facts["issues"].append(("cache-landing", "%s -- %d characters"
                                    % ("; ".join(markers[:3]), len(text))))
        mismatch = (identity(key, block, registry, text)
                    if len(text.strip()) >= STUB_CHARS else None)
        final = fetch.get("final_url") or fetch.get("url")
        if mismatch:
            detail = mismatch
            if final:
                detail += "; fetched from %s" % final
            facts["issues"].append(("identity-mismatch", detail))
        else:
            opening = (opening_mismatch(key, registry, text)
                       if len(text.strip()) >= STUB_CHARS else None)
            if opening:
                detail = opening + ("; fetched from %s" % final if final else "")
                facts["issues"].append(
                    ("ocr-title-unmatched" if facts["ocr"] else "cache-title-mismatch",
                     detail))

    status = fetch.get("status")
    if status and status != "cached":
        held = Path(pdf).stat().st_size if Path(pdf).exists() else 0
        if held > 50000 or len(text.strip()) >= STUB_CHARS:
            facts["issues"].append(("holdings-stale",
                                    'fetch record says "%s" (%s) while %d KB is on disk'
                                    % (status, fetch.get("reason", "no reason recorded"),
                                       (held or len(text)) // 1024)))
    recorded = fetch.get("original", "")
    if (recorded.endswith(".html") and Path(pdf).exists() and Path(txt).exists()
            and Path(pdf).stat().st_mtime > Path(txt).stat().st_mtime):
        facts["issues"].append(("extraction-stale",
                                "the .txt came from %s while a newer %s.pdf sits beside it"
                                % (Path(recorded).name, key)))

    for route, quote in zip(routes, quotes):
        if route:
            if route.endswith("+window"):
                facts["issues"].append(("quote-partial", '%s: "%s"'
                                        % (route, quote[:90])))
            continue
        if facts["ocr"]:
            facts["issues"].append(("ocr-quote-miss", '"%s"' % quote[:110]))
        else:
            facts["issues"].append(("quote-not-found", '"%s"' % quote[:110]))
    return facts


def run(findings, sources_list, sources):
    registry = dict(entries(sources_list))
    cache = {}
    return [assess(key, block, registry, sources, cache)
            for key, block in entries(findings)]


def report(facts, verbose):
    head = "[%s]" % facts["key"]
    print("\n%-12s %d quotes claimed, %d characters cached%s"
          % (head, facts["claimed"], facts["chars"], ", OCR" if facts["ocr"] else ""))
    for rule, detail in facts["issues"]:
        print("   %-20s %s" % (rule, detail if verbose else detail[:170]))
    for route, quote in facts["quotes"]:
        print("   %-20s %s" % (route or "MISS", quote[:150]))


FIXTURE_FINDINGS = '''# Quotes Bank

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)

**Verified quotes:** "a string the header must not be searched for at all"
```

---

### [Orr15] Orr, social post (2015)

**Verified quotes:** "Has anyone else seen herons on the canal this week? I counted six, and I usually see none."
**Source:** see `sources/list.md`

---

### [Ped09] Pedersen, "Planting Shallots in Clay" (2009)

**Verified quotes:** "Soak the bulbs overnight, plant them shallow, then firm the soil around each one."
**Source:** see `sources/list.md`

---

### [XYZW26] Xu et al., "Rethinking Flow" (2026)

**Verified quotes:** Table 3: "mean flow remained unchanged at 18.3 across the dry season rows"
**Source:** see `sources/list.md`

---

### [GLN14] Gale, Lim & Noor, "From stomach to brain" (2014)

**Verified quotes:** "hunger was not tied to any single brain region in this sample"
**Source:** see `sources/list.md`

---

### [Hea01] Healthy, "A Well Formed Entry" (2001)

**Verified quotes:** "the ligature in this identifier is deliberate and the sentence is long enough to be a quotation"
**Source:** see `sources/list.md`

---
'''

FIXTURE_LIST = '''# Sources List

## Entry format

```
### [<Key>] Author, "Title" (Year)

**Full title:** a template that must not be parsed as an entry
```

---

### [Orr15] Orr, social post (2015)

**Full title:** Has anyone else seen herons on the canal this week
**Authors:** Ines Orr
**Year:** 2015

---

### [Ped09] Pedersen, "Planting Shallots in Clay" (2009)

**Full title:** Planting Shallots in Clay
**Authors:** Dana Pedersen
**Year:** 2009

---

### [XYZW26] Xu et al., "Rethinking Flow" (2026)

**Full title:** Rethinking River Flow Through the Lens of Satellite Images
**Authors:** Chen Xu, Xiao Yang, Yu Zhao, Bei Wang
**Year:** 2026

---

### [GLN14] Gale, Lim & Noor (2014)

**Full title:** From stomach to brain: neural signs of hunger and fullness
**Authors:** Mira Gale, Nora Lim, Anat Noor
**Year:** 2014

---

### [Hea01] Healthy, "A Well Formed Entry" (2001)

**Full title:** A Well Formed Entry About Ligatures
**Authors:** Hilary Healthy
**Year:** 2001

---
'''

FIXTURE_CACHE = {
    "Orr15.html": '<html><head><meta property="og:description" content="@userone '
                  '@usertwo Has anyone else seen herons on the canal this week?  I counted '
                  'six, and I usually see none." /><title>Ines Orr on a social site</title>'
                  '</head><body><div id="root"></div></body></html>',
    "Ped09.txt": "A Different Page\n\n21 August 2013\n\nMark Fields\n\n"
                 "A style of planning beds. " + "filler text " * 400,
    "XYZW26.txt": "Physics > Geophysics\n\narXiv:0000.00000\n\n"
                  "View a PDF of the paper titled Rethinking River Flow Through the "
                  "Lens of Satellite Images, by Chen Xu and 3 other authors\n\n"
                  "View PDF\n\nSubmission history\n\nWhich authors of this paper are "
                  "endorsers?\n\nAbstract: River flow gauges such as weirs "
                  "have long been used.",
    "GLN14.txt": "From stomach to brain: neural signs of hunger and fullness"
                  "\n\nMira Gale, Nora Lim, Anat Noor\n\n"
                  "hunger was not tied to any single brain region in this "
                  "sample. " + "body text " * 400,
    "Hea01.txt": "A Well Formed Entry About Ligatures\n\nHilary Healthy\n\n"
                 "the ligature in this identi\ufb01er is\ndeliberate and the sen-\n"
                 "tence is long enough to be a quotation. " + "body text " * 400,
}
FIXTURE_FETCH = {
    "Orr15": {"status": "cached", "text_chars": 0, "original": "sources/library/Orr15.html"},
    "Ped09": {"status": "cached", "final_url": "https://blog.example.com/a-different-page.html",
              "original": "sources/library/Ped09.html"},
    "XYZW26": {"status": "cached", "final_url": "https://arxiv.org/abs/0000.00000",
               "original": "sources/library/XYZW26.html"},
    "GLN14": {"status": "paywalled", "reason": "HTTP 403",
              "final_url": "https://journal.example.org/article-pdf"},
}
FIXTURE_EXPECTED = {
    ("Orr15", "extraction-missing"),
    ("Ped09", "identity-mismatch"),
    ("Ped09", "quote-not-found"),
    ("XYZW26", "cache-stub"),
    ("XYZW26", "cache-landing"),
    ("XYZW26", "quote-not-found"),
    ("GLN14", "holdings-stale"),
}


def self_test():
    failures = 0
    for merged in (False, True):
        with tempfile.TemporaryDirectory() as root:
            files = Path(root) / "files"
            files.mkdir()
            origin = Path(root) / "origin" if merged else files
            folders = SourceFolders(root=Path(root), files=files, origin=origin)
            quotes = Path(root) / "quotes.md"
            sources_list = Path(root) / "list.md"
            quotes.write_text(FIXTURE_FINDINGS, encoding="utf-8")
            sources_list.write_text(FIXTURE_LIST, encoding="utf-8")
            for name, text in FIXTURE_CACHE.items():
                (files / name).write_text(text, encoding="utf-8")
            for key, record in FIXTURE_FETCH.items():
                folders.write_origin_record(key, FETCH, record)
            (files / "GLN14.pdf").write_bytes(b"%PDF-1.4\n" + b"0" * 60000)
            findings = run(quotes, sources_list, folders)
        found = set((facts["key"], rule) for facts in findings for rule, _ in facts["issues"])
        for key, rule in sorted(FIXTURE_EXPECTED - found):
            print("FAIL %-10s %-18s NOT REPORTED (merged=%s)" % (key, rule, merged))
            failures += 1
        for key, rule in sorted(found - FIXTURE_EXPECTED):
            print("FAIL %-10s %-18s FALSE POSITIVE (merged=%s)" % (key, rule, merged))
            failures += 1
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % failures))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("--quotes", help="the quotes bank (default: sources.quotes)")
    parser.add_argument("--list", dest="sources_list", help="the sources list (default: sources.list)")
    parser.add_argument("--key", action="append", help="only this key (repeatable)")
    parser.add_argument("--verbose", action="store_true",
                        help="also print every quote and the route that matched it")
    parser.add_argument("--self-test", action="store_true",
                        help="only check the classes against built-in fixtures")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    config = load_book(args, TOOL)
    quotes = args.quotes or config.sources.quotes
    sources_list = args.sources_list or config.sources.list
    folders = folders_from_config(config)
    if args.quotes and not Path(quotes).exists():
        return tool_failed("quotes bank not found: %s" % quotes, TOOL)
    if (skipped_for_missing(TOOL, quotes, "quotes bank", args.format)
            or skipped_for_missing(TOOL, folders.files, "source library", args.format)):
        return 0

    findings = run(quotes, sources_list, folders)
    if args.key:
        wanted = set(args.key)
        findings = [facts for facts in findings if facts["key"] in wanted]

    if args.verbose and args.format == "text":
        for facts in sorted(findings, key=lambda f: f["key"].lower()):
            if facts["quotes"]:
                report(facts, True)
        print()
    output = CheckReport(TOOL, CLASSES)
    for facts in sorted(findings, key=lambda f: f["key"].lower()):
        for rule, detail in facts["issues"]:
            output.add(facts["key"], rule, detail)
    if args.format == "text":
        print("entries %d, with quotes %d, quotes checked %d\n"
              % (len(findings), sum(1 for f in findings if f["claimed"]),
                 sum(len(f["quotes"]) for f in findings)))
    return output.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
