#!/usr/bin/env python3
"""Compare the metadata of the book's .bib entries with independent registries and catalogues.

Every entry of the bibliography (sources.bibliography, e.g. sources/references.bib) is read
with its BibTeX fields: author or editor, title, year, journal or booktitle, pages,
publisher, doi, isbn, url. The script never writes the .bib; a person edits it.

A single registry can be confidently wrong. Crossref is the DOI registry, so it looks
the most authoritative, but it republishes what the publisher deposited and does not
audit it: a publisher can deposit proceedings under the wrong container and year, and a
single-registry pass then "corrects" a right citation into a wrong one. This script
never decides who is right. It surfaces disagreement so a person opens the source.
A disagreement is not a correction.

DOI entries: Crossref first; the second opinion is DBLP (computer science, curated),
searched by title and subtitle and accepted only on a DOI match (the DBLP API does not
accept a DOI as a query); OpenAlex when DBLP has no record. OpenAlex ingests Crossref,
so agreement backed only by OpenAlex is weak and is labelled so. A DBLP that answered
HTTP 500 is reported as unreachable, never as "no record".

Book entries (@book with no doi and no url field): Open Library
and Google Books, matched on title AND author. They share an upstream (library MARC via
LoC and OCLC), so their agreement is corroboration, not proof. Google Books needs an
API key in practice (--google-key or GOOGLE_BOOKS_API_KEY); without one every request
answers HTTP 429 and books get one source, labelled `-1`. LoC, Wikidata, DNB and
K10plus were tried as third sources and rejected: too imprecise, too thin, catalogue
translations, or a year set so broad it agrees with everything. A source must be able
to say no.

Traps:
  * Book years are compared as MEMBERSHIP in the set of edition years a catalogue
    holds, never as equality with a "first published" year, because a bibliography
    cites a later edition on purpose. Edition statements are never compared.
  * Copyright year versus retail release: a one-year book difference is usually this.
  * Titles escalate through rungs (exact, folded, joined subtitle, component,
    alphanumeric); the rung is the finding. A registry title that EXTENDS the entry
    means the entry dropped a subtitle (soft); the reverse is routine and silent. A
    catalogue title longer than the cited one is usually a different book, so the
    cited title may extend the catalogue's, never the reverse.
  * An identifier that is merely real is not thereby right: a wrong-but-real DOI
    agrees with itself everywhere.

ISBN discovery (--discover-isbn) searches Open Library EDITION records and offers a
candidate only when title, author, year and publisher all agree; it validates the check
digit and the registrant prefix. A candidate is for a person, never a patch. Pre-ISBN
works (before 1970) need an LCCN or OCLC number instead; 979-8 ISBNs have no ISBN-10.

Coverage is a minority of a typical bibliography: talks, blog posts and reports have no
registry. A clean run says nothing about the entries it could not see.

Set a contact address before running at scale: CROSSREF_CONTACT or --contact
(mailto: or URL). Responses cache under the book's work caches
(METADATA_CHECK_CACHE overrides),
so a rerun is free; --refresh bypasses.

Usage:
  metadata-check.py                                   the book's .bib
  metadata-check.py --only-disagreements
  metadata-check.py --key Smi99
  metadata-check.py --kind book --discover-isbn --json candidates.json
  metadata-check.py --doi 10.1234/abc --isbn 9780000000002
  metadata-check.py --doi-list dois.txt
  metadata-check.py --self-test

Exit 0 when it ran (disagreements are ADVISORY: open the source), 2 on a usage error.
A book with no .bib file says SKIPPED.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
sys.dont_write_bytecode = True

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import add_config_arguments, load_book, tool_cache_folder
from bibliography import BibliographyError, parse_bibliography, plain_text, read_bibliography
from user_agent import USER_AGENT

TOOL = "metadata-check"

VERSION = "2.1"
CONTACT = os.environ.get("CROSSREF_CONTACT", "")


def user_agent(contact=None):
    contact = contact or CONTACT
    tail = "; %s" % contact.strip() if contact and contact.strip() else "; no contact set"
    return "%s metadata-check/%s (bibliography cross-verification%s)" % (USER_AGENT, VERSION,
                                                                          tail)


UA = user_agent()
TIMEOUT = 20
MAX_RESPONSE_BYTES = 10 * 1024 * 1024
MAX_ERROR_BODY_BYTES = 64 * 1024
THROTTLE = 1.0
CACHE_SCHEMA = 4

DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s,;\]]+)", re.IGNORECASE)
PAGES_PATTERNS = [
    re.compile(r"pp?\.\s*(\d+)\s*[-–—]\s*(\d+)"),
    re.compile(r"(?:,|\bpp?\.)\s*(\d+)\s*[-–—]\s*(\d+)\s*(?:\.|\)|$)"),
]

GREEN, YELLOW, RED, DIM, RESET = "\033[0;32m", "\033[0;33m", "\033[0;31m", "\033[0;36m", "\033[0m"

NETWORK_ERROR = "__network_error__"
QUOTA_ERROR = "__quota_error__"

ARTICLE_FIELDS = ("year", "pages", "venue", "title")
BOOK_FIELDS = ("year", "publisher", "title")


class Fetcher:
    def __init__(self, throttle=THROTTLE, timeout=TIMEOUT):
        self.throttle = throttle
        self.timeout = timeout
        self.errors = 0
        self.requests = 0
        self.exhausted = set()
        self._last = 0.0

    def out_of_quota(self, service):
        return service in self.exhausted

    def get_json(self, url, retries=2):
        wait = self.throttle - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Accept": "application/json"}
        )
        self.requests += 1
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                self.errors += 1
                return NETWORK_ERROR
            return json.loads(body.decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            if exc.code in (400, 404):
                return None
            if exc.code == 429:
                try:
                    body = exc.read(MAX_ERROR_BODY_BYTES).decode("utf-8", "replace")
                except (OSError, ValueError):
                    body = ""
                if "quota" in body.lower():
                    return QUOTA_ERROR
            if exc.code in (429, 500, 502, 503, 504) and retries > 0:
                return self._retry(url, retries)
            self.errors += 1
            return NETWORK_ERROR
        except (urllib.error.URLError, ValueError, OSError):
            if retries > 0:
                return self._retry(url, retries)
            self.errors += 1
            return NETWORK_ERROR
        finally:
            self._last = time.time()

    def _retry(self, url, retries):
        time.sleep(self.throttle * 4 * (3 - retries))
        return self.get_json(url, retries - 1)


def extract_doi(text):
    match = DOI_RE.search(text)
    if not match:
        return None
    doi = match.group(1)
    while doi:
        if doi[-1] in ".,;:":
            doi = doi[:-1]
        elif doi[-1] == ")" and doi.count(")") > doi.count("("):
            doi = doi[:-1]
        else:
            break
    return doi or None


def normalize_pages(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        parts = [str(p) for p in value if p not in (None, "")]
        if not parts:
            return None
        return parts[0] if len(parts) == 1 else "%s-%s" % (parts[0], parts[-1])
    text = str(value).strip()
    if not text:
        return None
    for pattern in PAGES_PATTERNS:
        match = pattern.search(text)
        if match:
            return "%s-%s" % (match.group(1), match.group(2))
    match = re.match(r"^\s*(\d+)\s*[-–—]\s*(\d+)\s*$", text)
    if match:
        return "%s-%s" % (match.group(1), match.group(2))
    match = re.match(r"^\s*(\d+)\s*$", text)
    return match.group(1) if match else None


def page_bounds(value):
    if not value:
        return None, None
    match = re.match(r"^\s*(\d+)\s*[-–—]\s*(\d+)\s*$", str(value))
    if match:
        start, end = match.group(1), match.group(2)
        return start, (None if start == end else end)
    match = re.match(r"^\s*(\d+)\s*$", str(value))
    return (match.group(1), None) if match else (None, None)


def compare_pages(values):
    bounds = [page_bounds(v) for v in values]
    starts = {start for start, _ in bounds if start}
    ends = {end for _, end in bounds if end}
    return len(starts) > 1 or len(ends) > 1


def normalize_venue(value):
    if not value:
        return None
    text = re.sub(r"[^a-z0-9]+", " ", str(value).lower())
    return re.sub(r"\s+", " ", text).strip() or None


def normalize_title(value):
    if not value:
        return None
    text = str(value).lower()
    text = text.replace("[plus plus]", " plus plus ").replace("++", " plus plus ")
    text = text.replace("[sharp]", " sharp ").replace("#", " sharp ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^(the|a|an)\s+", "", text)
    return text or None


ENTITIES = (
    ("&amp;", "&"), ("&#38;", "&"), ("&quot;", '"'), ("&apos;", "'"),
    ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " "), ("&ndash;", "-"),
    ("&mdash;", "-"), ("&hellip;", "..."), ("&#x2019;", "'"), ("&#8217;", "'"),
)
LATEX_MACRO_RE = re.compile(r"\\[a-zA-Z]+\s*")
LATEX_ESCAPE_RE = re.compile(r"\\([&%$#_{}])")
UNICODE_PUNCT = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u2026": "...",
    "\u00a0": " ", "\u00ad": "",
}
SUBTITLE_SPLIT_RE = re.compile(r"\s*[:;]\s+|\s+[-\u2013\u2014]\s+")
COMPONENT_SPLIT_RE = re.compile(r"\s*[:;]\s+|\s+[-\u2013\u2014]\s+|\.\s+")
HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")
TRAILING_BRACKET_RE = re.compile(r"\s*[\[(][^\])]*[\])]\s*$")


def decode_title(value):
    if value is None:
        return None
    text = HTML_TAG_RE.sub("", str(value))
    for entity, plain in ENTITIES:
        text = text.replace(entity, plain)
    text = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), text)
    text = LATEX_ESCAPE_RE.sub(r"\1", text)
    text = LATEX_MACRO_RE.sub(" ", text)
    text = text.replace("{", "").replace("}", "").replace("``", '"').replace("''", '"')
    for symbol, plain in UNICODE_PUNCT.items():
        text = text.replace(symbol, plain)
    return re.sub(r"\s+", " ", text).strip()


def fold_title(value):
    text = decode_title(value)
    if not text:
        return None
    text = text.lower().replace("&", " and ")
    text = text.replace("[plus plus]", " plus plus ").replace("++", " plus plus ")
    text = text.replace("[sharp]", " sharp ").replace("#", " sharp ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"^(the|a|an)\s+", "", text) or None


def alnum_title(value):
    folded = fold_title(value)
    return folded.replace(" ", "") if folded else None


def title_parts(value):
    text = decode_title(value)
    if not text:
        return None, None
    pieces = SUBTITLE_SPLIT_RE.split(text, maxsplit=1)
    main = pieces[0].strip() or None
    subtitle = pieces[1].strip() if len(pieces) > 1 and pieces[1].strip() else None
    return main, subtitle


def title_rung(cited, candidate, candidate_subtitle=None):
    if not cited or not candidate:
        return None
    left, right = decode_title(cited), decode_title(candidate)
    if left == right:
        return 1, None
    if left and right and left.rstrip(".") == right.rstrip("."):
        return 1, None

    folded_left, folded_right = fold_title(left), fold_title(right)
    if not folded_left or not folded_right:
        return None
    if folded_left == folded_right:
        return 2, None

    if candidate_subtitle:
        right = "%s: %s" % (right.rstrip(": "), candidate_subtitle)
        folded_right = fold_title(right)
        if folded_right == folded_left:
            return 3, None

    note = component_relation(left, right)
    if note:
        return 4, note

    stripped = TRAILING_BRACKET_RE.sub("", right)
    if stripped != right and fold_title(stripped) == folded_left:
        return 4, "registry-annotated"

    if alnum_title(left) == alnum_title(right):
        return 5, None
    return None


def component_relation(left, right):
    left_parts = [fold_title(p) for p in COMPONENT_SPLIT_RE.split(left)]
    right_parts = [fold_title(p) for p in COMPONENT_SPLIT_RE.split(right)]
    left_parts = [p for p in left_parts if p]
    right_parts = [p for p in right_parts if p]
    if not left_parts or not right_parts or left_parts == right_parts:
        return None
    if len(left_parts) < len(right_parts):
        if right_parts[:len(left_parts)] == left_parts:
            return "cited-short"
        if right_parts[-len(left_parts):] == left_parts:
            return "registry-prefixed"
    if len(right_parts) < len(left_parts):
        if left_parts[:len(right_parts)] == right_parts:
            return "cited-long"
        if left_parts[-len(right_parts):] == right_parts:
            return "registry-truncated"
    return None


def title_finding(cited, candidate, candidate_subtitle=None):
    result = title_rung(cited, candidate, candidate_subtitle)
    if result is None:
        return "hard", "no rung matched"
    rung, note = result
    if rung == 4 and note == "cited-short":
        return "soft", "rung 4 (component prefix): entry title omits a published subtitle"
    if rung == 4 and note == "registry-annotated":
        return None
    if rung == 4 and note == "registry-prefixed":
        return "soft", "rung 4 (component suffix): registry title carries a leading section label the entry drops"
    if rung == 5:
        return "soft", "rung 5 (alphanumeric-only): titles differ in word division or hyphenation"
    return None


def clean_isbn(value):
    if not value:
        return None
    digits = re.sub(r"[^\dXx]", "", str(value)).upper()
    return digits if len(digits) in (10, 13) else None


def isbn_valid(value):
    digits = clean_isbn(value)
    if not digits:
        return False
    if len(digits) == 10:
        if not re.match(r"^\d{9}[\dX]$", digits):
            return False
        total = sum((10 - i) * (10 if c == "X" else int(c))
                    for i, c in enumerate(digits))
        return total % 11 == 0
    if not digits.isdigit():
        return False
    total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(digits))
    return total % 10 == 0


def isbn10_to_13(value):
    digits = clean_isbn(value)
    if not digits or len(digits) != 10 or not isbn_valid(digits):
        return None
    body = "978" + digits[:9]
    total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(body))
    return body + str((10 - total % 10) % 10)


def isbn13(value):
    digits = clean_isbn(value)
    if not digits or not isbn_valid(digits):
        return None
    return digits if len(digits) == 13 else isbn10_to_13(digits)


def normalize_publisher(value):
    if not value:
        return None
    text = str(value)
    if ":" in text:
        text = text.split(":", 1)[1]
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    text = re.sub(
        r"\b(inc|ltd|llc|gmbh|co|company|publishers?|publishing|press|books?|"
        r"media|group|professional|limited|international|and|the)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip() or None


def publisher_matches(book_value, candidates):
    target = normalize_publisher(book_value)
    if not target:
        return True
    for candidate in candidates:
        other = normalize_publisher(candidate)
        if not other:
            continue
        if target == other or target.startswith(other) or other.startswith(target):
            return True
    return False


def author_matches(surnames, candidates):
    wanted = {normalize_title(name) for name in surnames}
    wanted = {name for name in wanted if name}
    if not wanted:
        return False
    for candidate in candidates or []:
        listed = normalize_title(candidate)
        if not listed:
            continue
        tokens = set(listed.split())
        for name in wanted:
            if name in tokens or name == listed:
                return True
            if " " in name and name in listed:
                return True
    return False


def main_title(value):
    if not value:
        return None
    return re.split(r"\s*[:;]\s*", str(value), maxsplit=1)[0].strip() or None


def title_matches(book_title, candidate_title, candidate_subtitle=None):
    wanted = normalize_title(book_title)
    if not wanted:
        return False
    forms = set()
    for text in (candidate_title, main_title(candidate_title)):
        base = normalize_title(text)
        if base:
            forms.add(base)
    if candidate_subtitle:
        joined = normalize_title("%s %s" % (candidate_title, candidate_subtitle))
        if joined:
            forms.add(joined)
    for other in forms:
        if wanted == other:
            return True
        if wanted.startswith(other + " ") and (len(other.split()) >= 2 or len(other) >= 8):
            return True
    return False


BOOK_TYPES = ("book",)


def bibliography_entries(path):
    return [entry_from_bib(entry) for entry in read_bibliography(path).entries.values()]


def bibliography_from_text(text):
    return [entry_from_bib(entry) for entry in parse_bibliography(text).entries.values()]


def entry_from_bib(bib):
    doi = extract_doi(bib.field("doi") or "")
    common = {
        "key": bib.key,
        "title": bib.plain("title") or None,
        "authors": entry_surnames(bib),
        "year": four_digit_year(bib.field("year")),
        "from_bibliography": True,
    }
    if doi:
        return {**common, "kind": "doi", "doi": doi,
                "pages": normalize_pages(re.sub(r"-+", "-", bib.plain("pages"))),
                "venue": bib.plain("journal", "booktitle") or None}
    if bib.entry_type in BOOK_TYPES and not bib.field("url"):
        isbn = re.sub(r"[^\dXx]", "", bib.plain("isbn"))
        return {**common, "kind": "book", "doi": None,
                "publisher": bib.plain("publisher") or None,
                "isbn": isbn if len(isbn) in (10, 13) else None}
    return {**common, "kind": "other", "doi": None}


def entry_surnames(bib):
    names = bib.authors or bib.editors
    return [plain_text(name.last) if name.corporate else name.surname
            for name in names if not name.others and (name.last or name.von)]


def four_digit_year(value):
    found = re.search(r"\d{4}", plain_text(value or ""))
    return found.group(0) if found else None


def crossref_title(message):
    titles = message.get("title") or []
    title = titles[0] if titles else None
    if not title:
        return None
    subtitles = message.get("subtitle") or []
    subtitle = subtitles[0] if subtitles else None
    if subtitle and normalize_title(subtitle) not in (normalize_title(title) or ""):
        return "%s: %s" % (title.rstrip(": "), subtitle)
    return title


def query_crossref(fetcher, doi):
    data = fetcher.get_json("https://api.crossref.org/works/" + urllib.parse.quote(doi))
    if data in (None, NETWORK_ERROR):
        return data
    message = data.get("message") if isinstance(data, dict) else None
    if not message:
        return None
    parts = (message.get("issued", {}).get("date-parts") or [[None]])[0] or [None]
    container = message.get("container-title") or []
    titles = message.get("title") or []
    subtitles = message.get("subtitle") or []
    return {
        "source": "crossref",
        "year": str(parts[0]) if parts[0] else None,
        "pages": normalize_pages(message.get("page")),
        "venue": container[0] if container else None,
        "title": crossref_title(message),
        "title_main": titles[0] if titles else None,
        "title_subtitle": subtitles[0] if subtitles else None,
    }


def query_dblp(fetcher, doi, title):
    if not title:
        return None
    url = "https://dblp.org/search/publ/api?" + urllib.parse.urlencode(
        {"q": title, "format": "json", "h": 10}
    )
    data = fetcher.get_json(url)
    if data in (None, NETWORK_ERROR):
        return data
    try:
        hits = data["result"]["hits"]
        if int(hits.get("@total", 0)) == 0:
            return None
        rows = hits["hit"]
    except (TypeError, KeyError, ValueError):
        return None
    rows = rows if isinstance(rows, list) else [rows]
    for row in rows:
        info = row.get("info", {}) if isinstance(row, dict) else {}
        if (info.get("doi") or "").lower().rstrip("/") != doi.lower().rstrip("/"):
            continue
        return {
            "source": "dblp",
            "year": str(info["year"]) if info.get("year") else None,
            "pages": normalize_pages(info.get("pages")),
            "venue": info.get("venue"),
            "title": info.get("title"),
        }
    return None


def query_openalex(fetcher, doi):
    data = fetcher.get_json("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi))
    if data in (None, NETWORK_ERROR):
        return data
    if not isinstance(data, dict) or "id" not in data:
        return None
    location = (data.get("primary_location") or {}).get("source") or {}
    biblio = data.get("biblio") or {}
    pages = None
    if biblio.get("first_page"):
        pages = normalize_pages([biblio.get("first_page"), biblio.get("last_page")])
    return {
        "source": "openalex",
        "year": str(data["publication_year"]) if data.get("publication_year") else None,
        "pages": pages,
        "venue": location.get("display_name"),
        "title": data.get("title"),
    }


def query_openlibrary(fetcher, entry):
    if entry.get("isbn"):
        data = fetcher.get_json(
            "https://openlibrary.org/api/books?" + urllib.parse.urlencode(
                {"bibkeys": "ISBN:" + entry["isbn"], "format": "json", "jscmd": "data"}))
        if data is NETWORK_ERROR:
            return NETWORK_ERROR
        record = (data or {}).get("ISBN:" + entry["isbn"]) if isinstance(data, dict) else None
        if record:
            year = re.search(r"\b(\d{4})\b", str(record.get("publish_date") or ""))
            return {
                "source": "openlibrary",
                "years": [year.group(1)] if year else [],
                "publishers": [p.get("name") for p in record.get("publishers") or []],
                "title": record.get("title"),
                "title_main": record.get("title"),
                "title_subtitle": record.get("subtitle"),
                "by_isbn": entry["isbn"],
            }
    if not entry.get("title"):
        return None
    params = {
        "title": main_title(entry["title"]) or entry["title"], "limit": 10,
        "fields": "key,title,subtitle,author_name,first_publish_year,publish_year,publisher",
    }
    if entry.get("authors"):
        params["author"] = entry["authors"][0]
    data = fetcher.get_json("https://openlibrary.org/search.json?" + urllib.parse.urlencode(params))
    if data in (None, NETWORK_ERROR):
        return data
    years, publishers, titles = set(), [], []
    subtitle = None
    for doc in (data.get("docs") or []) if isinstance(data, dict) else []:
        if not title_matches(entry["title"], doc.get("title"), doc.get("subtitle")):
            continue
        if not author_matches(entry.get("authors") or [], doc.get("author_name")):
            continue
        years.update(str(y) for y in (doc.get("publish_year") or []) if y)
        if doc.get("first_publish_year"):
            years.add(str(doc["first_publish_year"]))
        publishers.extend(doc.get("publisher") or [])
        titles.append(doc.get("title"))
        subtitle = subtitle or doc.get("subtitle")
    if not titles:
        return None
    return {
        "source": "openlibrary",
        "years": sorted(years),
        "publishers": publishers,
        "title": titles[0],
        "title_main": titles[0],
        "title_subtitle": subtitle,
        "records": len(titles),
    }


def query_google_books(fetcher, entry, api_key):
    if fetcher.out_of_quota("googlebooks"):
        return QUOTA_ERROR
    if entry.get("isbn"):
        query = "isbn:" + entry["isbn"]
    elif entry.get("title"):
        query = 'intitle:"%s"' % entry["title"]
        if entry.get("authors"):
            query += ' inauthor:"%s"' % entry["authors"][0]
    else:
        return None
    params = {"q": query, "maxResults": 5, "printType": "books"}
    if api_key:
        params["key"] = api_key
    data = fetcher.get_json("https://www.googleapis.com/books/v1/volumes?" + urllib.parse.urlencode(params))
    if data is QUOTA_ERROR:
        fetcher.exhausted.add("googlebooks")
        return QUOTA_ERROR
    if data in (None, NETWORK_ERROR):
        return data
    years, publishers, matched = set(), [], None
    subtitle = None
    for item in (data.get("items") or []) if isinstance(data, dict) else []:
        info = item.get("volumeInfo") or {}
        if entry.get("title") and not title_matches(
                entry["title"], info.get("title"), info.get("subtitle")):
            continue
        if entry.get("authors") and not author_matches(entry["authors"], info.get("authors")):
            continue
        matched = matched or info.get("title")
        subtitle = subtitle or info.get("subtitle")
        year = re.match(r"\s*(\d{4})", str(info.get("publishedDate") or ""))
        if year:
            years.add(year.group(1))
        if info.get("publisher"):
            publishers.append(info["publisher"])
    if not matched:
        return None
    return {
        "source": "googlebooks",
        "years": sorted(years),
        "publishers": publishers,
        "title": matched,
        "title_main": matched,
        "title_subtitle": subtitle,
    }


def openlibrary_works(fetcher, entry):
    params = {
        "title": main_title(entry["title"]) or entry["title"], "limit": 10,
        "fields": "key,title,subtitle,author_name,first_publish_year",
    }
    if entry.get("authors"):
        params["author"] = entry["authors"][0]
    data = fetcher.get_json(
        "https://openlibrary.org/search.json?" + urllib.parse.urlencode(params))
    if data in (None, NETWORK_ERROR) or not isinstance(data, dict):
        return []
    keys = []
    for doc in data.get("docs") or []:
        if not title_matches(entry["title"], doc.get("title"), doc.get("subtitle")):
            continue
        if not author_matches(entry.get("authors") or [], doc.get("author_name")):
            continue
        if doc.get("key"):
            keys.append(doc["key"])
    return keys


def openlibrary_editions(fetcher, work_key, limit=200):
    data = fetcher.get_json(
        "https://openlibrary.org%s/editions.json?limit=%d" % (work_key, limit))
    if data in (None, NETWORK_ERROR) or not isinstance(data, dict):
        return []
    editions = []
    for record in data.get("entries") or []:
        if not isinstance(record, dict):
            continue
        year = re.search(r"\b(1[89]\d{2}|20\d{2})\b", str(record.get("publish_date") or ""))
        isbns = [clean_isbn(v) for v in
                 (record.get("isbn_13") or []) + (record.get("isbn_10") or [])]
        editions.append({
            "title": record.get("title"),
            "subtitle": record.get("subtitle"),
            "year": year.group(1) if year else None,
            "publishers": [p for p in (record.get("publishers") or []) if p],
            "isbns": [i for i in isbns if i],
            "format": record.get("physical_format"),
            "languages": [l.get("key", "").rsplit("/", 1)[-1]
                          for l in (record.get("languages") or []) if isinstance(l, dict)],
            "key": record.get("key"),
        })
    return editions


def score_edition(entry, edition):
    checks = {
        "title": bool(edition.get("title")) and title_matches(
            entry["title"], edition["title"], edition.get("subtitle")),
        "year": bool(edition.get("year")) and edition["year"] == entry.get("year"),
        "publisher": publisher_matches(entry.get("publisher"), edition.get("publishers") or []),
        "isbn": any(isbn_valid(i) for i in edition.get("isbns") or []),
    }
    english = not edition.get("languages") or "eng" in edition["languages"]
    return checks, english


def discover_isbn(fetcher, entry):
    accepted, rejected = [], []
    for work_key in openlibrary_works(fetcher, entry):
        for edition in openlibrary_editions(fetcher, work_key):
            checks, english = score_edition(entry, edition)
            edition = dict(edition, checks=checks, english=english, work=work_key)
            if all(checks.values()) and english:
                accepted.append(edition)
            elif checks["isbn"] and (checks["year"] or checks["publisher"]):
                rejected.append(edition)
    return accepted, rejected


def gather(fetcher, entry):
    doi, title = entry["doi"], entry.get("title")
    failed = dblp_down = False

    primary = query_crossref(fetcher, doi)
    if primary is NETWORK_ERROR:
        primary, failed = None, True

    if not title and primary:
        title = primary.get("title")

    secondary = query_dblp(fetcher, doi, title)
    if secondary is NETWORK_ERROR:
        secondary, failed, dblp_down = None, True, True
    if not secondary:
        secondary = query_openalex(fetcher, doi)
        if secondary is NETWORK_ERROR:
            secondary, failed = None, True

    return primary, secondary, failed, dblp_down


def gather_book(fetcher, entry, api_key):
    sources, failed, blocked = [], False, False
    for query in (query_openlibrary, query_google_books):
        result = (query(fetcher, entry, api_key)
                  if query is query_google_books else query(fetcher, entry))
        if result is QUOTA_ERROR:
            blocked = True
            continue
        if result is NETWORK_ERROR:
            failed = True
            continue
        if result:
            sources.append(result)
    return sources, failed, blocked


def compare(entry, primary, secondary, fields):
    differences = []
    for field in fields:
        if field not in ARTICLE_FIELDS or field == "title":
            continue
        values = [
            entry.get(field),
            primary.get(field) if primary else None,
            secondary.get(field) if secondary else None,
        ]
        if field == "pages":
            conflict = compare_pages(values)
        elif field == "venue":
            known = [v for v in (normalize_venue(v) for v in values) if v]
            conflict = len(set(known)) > 1
        else:
            known = [str(v) for v in values if v is not None]
            conflict = len(set(known)) > 1
        if conflict:
            differences.append((field, values[0], values[1], values[2]))
    return differences


def source_title_pair(source):
    if source.get("title_main"):
        return source["title_main"], source.get("title_subtitle")
    return source.get("title"), None


def compare_titles(cited, sources):
    findings = []
    for source in sources:
        if not source:
            continue
        title, subtitle = source_title_pair(source)
        if not title:
            continue
        finding = title_finding(cited, title, subtitle)
        if not finding:
            continue
        shown = "%s: %s" % (title, subtitle) if subtitle else title
        findings.append((source["source"], finding[0], finding[1], decode_title(shown)))
    return findings


def book_evidence(entry, sources, fields):
    present = []
    for field in fields:
        if field not in BOOK_FIELDS or not entry.get(field):
            continue
        key = "years" if field == "year" else "publishers"
        if any(source.get(key) for source in sources):
            present.append(field)
    return present


def compare_book(entry, sources, fields):
    differences = []
    for field in fields:
        if field not in BOOK_FIELDS:
            continue
        if field == "year":
            cited = entry.get("year")
            if not cited:
                continue
            offenders = []
            for source in sources:
                years = source.get("years") or []
                if years and cited not in years:
                    offenders.append("%s=%s" % (source["source"], ",".join(years)))
            if offenders:
                differences.append(("year", "cited=%s but %s" % (cited, "; ".join(offenders))))
        elif field == "publisher":
            cited = entry.get("publisher")
            if not cited:
                continue
            offenders = []
            for source in sources:
                publishers = [p for p in (source.get("publishers") or []) if p]
                if publishers and not publisher_matches(cited, publishers):
                    offenders.append("%s=%s" % (source["source"], "|".join(sorted(set(publishers))[:3])))
            if offenders:
                differences.append(("publisher", "cited=%s but %s" % (cited, "; ".join(offenders))))
    return differences


def extract_dois_from_lines(lines):
    dois, skipped = [], 0
    for line in lines:
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        doi = extract_doi(text)
        if doi:
            dois.append(doi)
        else:
            skipped += 1
    return dois, skipped


def adhoc_entry(doi):
    return {
        "key": doi, "raw": "", "kind": "doi", "doi": doi, "year": None, "pages": None,
        "venue": None, "title": None, "from_bibliography": False,
    }


def adhoc_book(isbn):
    return {
        "key": "ISBN:" + isbn, "raw": "", "kind": "book", "doi": None, "title": None,
        "authors": [], "year": None, "publisher": None, "isbn": isbn,
        "from_bibliography": False,
    }


def cache_path(directory, kind, ident):
    slug = re.sub(r"[^\w.-]", "_", ident)[:120]
    prefix = "book_" if kind == "book" else ""
    return Path(directory, prefix + slug + ".json")


def load_cached(path):
    if not Path(path).exists():
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (ValueError, OSError):
        return None
    if not isinstance(payload, dict) or payload.get("schema") != CACHE_SCHEMA:
        return None
    return payload


def store_cached(path, payload):
    try:
        with open(path, "w", encoding="utf-8") as handle:
            payload = dict(payload)
            payload["schema"] = CACHE_SCHEMA
            json.dump(payload, handle, indent=1, sort_keys=True)
    except OSError:
        pass


def format_value(value):
    return str(value) if value not in (None, "") else "-"


def year_span(source):
    years = [y for y in (source.get("years") or []) if y]
    records = source.get("records")
    tail = " from %d records" % records if records and records > 1 else ""
    if not years:
        return " (no years%s)" % tail
    if len(years) == 1:
        return " (1 edition year: %s%s)" % (years[0], tail)
    return " (%d edition years %s-%s%s)" % (len(years), min(years), max(years), tail)


def build_parser():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_config_arguments(parser)
    parser.add_argument("--bibliography", metavar="FILE",
                        help="the .bib file to check (default: sources.bibliography when no "
                             "other input is given)")
    parser.add_argument(
        "--doi", action="append", metavar="DOI",
        help="check ad-hoc DOIs; repeatable and/or comma-separated. Any string "
             "containing a DOI works (doi.org URL, 'doi:' prefix, pasted citation).",
    )
    parser.add_argument(
        "--isbn", action="append", metavar="ISBN",
        help="check ad-hoc books by ISBN; repeatable and/or comma-separated.",
    )
    parser.add_argument(
        "--doi-list", action="append", metavar="FILE",
        help="file of DOIs, one per line; blank lines and '#' comments ignored. "
             "Lines only need to contain a DOI. Repeatable.",
    )
    parser.add_argument(
        "stdin_flag", nargs="?", metavar="-",
        help="'-' reads DOIs from stdin, same free format as --doi-list. "
             "Piped input is picked up automatically when no other source is given.",
    )
    parser.add_argument("--key", help="check a single citation key (needs the bibliography)")
    parser.add_argument(
        "--kind", choices=("all", "doi", "book"), default="all",
        help="which bibliography entries to check (default: all)",
    )
    parser.add_argument(
        "--compare",
        default="year,pages,publisher,title",
        help="fields to compare (default: year,pages,publisher,title). 'year', "
             "'pages'/'venue' and 'title' apply to DOI entries, 'year', "
             "'publisher' and 'title' to books. 'venue' is noisy across "
             "registries and stays opt-in.",
    )
    parser.add_argument(
        "--google-key", default=os.environ.get("GOOGLE_BOOKS_API_KEY"),
        help="Google Books API key (or set GOOGLE_BOOKS_API_KEY). Without one, "
             "Google Books returns HTTP 429 and books get a single source.",
    )
    parser.add_argument(
        "--cache",
        default=os.environ.get("METADATA_CHECK_CACHE"),
        help="folder for cached registry responses (default: under the book's work "
             "caches, or METADATA_CHECK_CACHE)",
    )
    parser.add_argument(
        "--discover-isbn", action="store_true",
        help="for book entries with no ISBN, search Open Library editions and "
             "report candidates that agree on title, author, year and "
             "publisher. Writes findings to stdout as JSON with --json.",
    )
    parser.add_argument(
        "--json", metavar="FILE",
        help="write --discover-isbn findings to FILE as JSON for review",
    )
    parser.add_argument(
        "--contact", default=CONTACT, metavar="ADDRESS",
        help="contact address sent in the User-Agent (or set CROSSREF_CONTACT). "
             "Crossref etiquette asks for a mailto: or URL and gives identified "
             "callers a more reliable request pool. Optional; unset works.",
    )
    parser.add_argument("--only-disagreements", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="ignore cache and refetch")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--self-test", action="store_true",
                        help="test title, page, ISBN and entry parsing offline")
    return parser


def collect_entries(args, parser):
    entries, seen_doi, seen_book, skipped_lines = [], set(), set(), 0

    def add(entry):
        if entry.get("doi"):
            if entry["doi"].lower() in seen_doi:
                return
            seen_doi.add(entry["doi"].lower())
        elif entry.get("kind") == "book":
            ident = entry["key"] if entry.get("from_bibliography") else \
                (entry.get("isbn") or normalize_title(entry.get("title")) or entry["key"])
            if ident in seen_book:
                return
            seen_book.add(ident)
        entries.append(entry)

    if args.bibliography:
        if not Path(args.bibliography).exists():
            parser.error("no such file: %s" % args.bibliography)
        try:
            found = bibliography_entries(args.bibliography)
        except BibliographyError as error:
            parser.error("cannot read %s: %s" % (args.bibliography, error))
        if args.key:
            found = [e for e in found if e["key"] == args.key]
            if not found:
                parser.error("key %s not found in %s" % (args.key, args.bibliography))
        for entry in found:
            if args.kind != "all" and entry["kind"] not in (args.kind, "other"):
                continue
            add(entry)

    for value in args.doi or []:
        for piece in value.split(","):
            if not piece.strip():
                continue
            doi = extract_doi(piece)
            if not doi:
                parser.error("--doi contains no DOI: %s" % piece.strip())
            add(adhoc_entry(doi))

    for value in args.isbn or []:
        for piece in value.split(","):
            cleaned = re.sub(r"[^\dXx]", "", piece)
            if not cleaned:
                continue
            if len(cleaned) not in (10, 13):
                parser.error("--isbn is not a 10- or 13-digit ISBN: %s" % piece.strip())
            add(adhoc_book(cleaned))

    for path in args.doi_list or []:
        if not Path(path).exists():
            parser.error("no such file: %s" % path)
        try:
            with open(path, encoding="utf-8") as handle:
                dois, skipped = extract_dois_from_lines(handle)
        except OSError as exc:
            parser.error("cannot read %s: %s" % (path, exc))
        skipped_lines += skipped
        for doi in dois:
            add(adhoc_entry(doi))

    explicit = bool(args.bibliography or args.doi or args.doi_list
                    or args.isbn or args.stdin_flag)
    use_stdin = bool(args.stdin_flag) or (not explicit and not sys.stdin.isatty())
    if use_stdin:
        dois, skipped = extract_dois_from_lines(sys.stdin)
        skipped_lines += skipped
        for doi in dois:
            add(adhoc_entry(doi))

    return entries, skipped_lines, explicit or use_stdin


class Tally:
    def __init__(self):
        for name in ("checked", "disagreeing", "other_kind", "not_found", "one_source",
                     "network_failed", "derived", "registry_only", "dblp_down",
                     "books_checked", "books_matched", "books_disagreeing",
                     "books_no_match", "books_one_source", "google_unavailable",
                     "books_no_evidence", "title_hard", "title_soft",
                     "isbn_used", "isbn_found", "isbn_uncertain", "isbn_none"):
            setattr(self, name, 0)


def report_title_findings(entry, sources, args, fields, tally, rows):
    if "title" not in fields:
        return False
    live = [s for s in sources if s]
    cited, against = entry.get("title"), live
    if not cited:
        if len(live) < 2:
            return False
        cited, against = live[0].get("title") or source_title_pair(live[0])[0], live[1:]
        if not cited:
            return False
    hard = False
    for source, severity, message, registry_title in compare_titles(cited, against):
        detail = "title: entry=%r %s=%r -- %s" % (
            decode_title(cited), source, registry_title, message)
        if severity == "hard":
            hard = True
            tally.title_hard += 1
            rows.append((YELLOW, entry["key"],
                         "DISAGREE" if entry.get("from_bibliography") else "DISAGREE-REG",
                         detail))
        else:
            tally.title_soft += 1
            rows.append((DIM, entry["key"], "TITLE-SOFT", detail))
    return hard


def check_doi_entry(entry, args, fetcher, fields, tally, rows):
    path = cache_path(args.cache, "doi", entry["doi"])
    payload = None if args.refresh else load_cached(path)
    failed = False
    if payload is None:
        primary, secondary, failed, dblp_down = gather(fetcher, entry)
        if dblp_down:
            tally.dblp_down += 1
        if failed:
            tally.network_failed += 1
        else:
            store_cached(path, {"primary": primary, "secondary": secondary})
    else:
        primary, secondary = payload["primary"], payload["secondary"]

    tally.checked += 1
    if not primary and not secondary:
        tally.not_found += 1
        rows.append((RED, entry["key"], "NOT-FOUND",
                     "fetch failed, so nothing was checked" if failed
                     else "neither registry returned a record"))
        return
    if not primary or not secondary:
        tally.one_source += 1
        if not args.only_disagreements:
            have = (primary or secondary)["source"]
            rows.append((DIM, entry["key"], "ONE-SOURCE",
                         "only %s has a record; no cross-check possible" % have))
        return

    from_bibliography = entry.get("from_bibliography")
    if not from_bibliography:
        tally.registry_only += 1

    suffix = " (weak: openalex is largely crossref-derived)" \
        if secondary["source"] == "openalex" else ""

    title_hard = report_title_findings(entry, [primary, secondary], args, fields, tally, rows)

    differences = compare(entry, primary, secondary, fields)
    if differences:
        tally.disagreeing += 1
        verdict = "DISAGREE" if from_bibliography else "DISAGREE-REG"
        for field, book, first, second in differences:
            if from_bibliography:
                detail = "%s: book=%s %s=%s %s=%s" % (
                    field, format_value(book),
                    primary["source"], format_value(first),
                    secondary["source"], format_value(second))
            else:
                detail = "%s: %s=%s %s=%s" % (
                    field, primary["source"], format_value(first),
                    secondary["source"], format_value(second))
            rows.append((YELLOW, entry["key"], verdict, detail + suffix))
    if not differences and not title_hard:
        if secondary["source"] == "openalex":
            tally.derived += 1
        if not args.only_disagreements:
            rows.append((GREEN, entry["key"],
                         "AGREE" if from_bibliography else "AGREE-REG",
                         "%s + %s%s" % (primary["source"], secondary["source"], suffix)))


def check_book_entry(entry, args, fetcher, fields, tally, rows):
    ident = entry.get("isbn") or (normalize_title(entry.get("title")) or entry["key"])
    path = cache_path(args.cache, "book", ident)
    payload = None if args.refresh else load_cached(path)
    failed = False
    if payload is not None and payload.get("incomplete") and args.google_key:
        payload = None
    if payload is None:
        sources, failed, blocked = gather_book(fetcher, entry, args.google_key)
        if blocked:
            tally.google_unavailable += 1
        if failed:
            tally.network_failed += 1
        else:
            store_cached(path, {"sources": sources, "incomplete": blocked})
    else:
        sources = payload["sources"]
        if payload.get("incomplete"):
            tally.google_unavailable += 1

    tally.books_checked += 1
    if not sources:
        tally.books_no_match += 1
        if not args.only_disagreements:
            rows.append((DIM, entry["key"], "BOOK-NO-MATCH",
                         "no catalogue returned a confident title+author match"
                         + (" (fetch failed)" if failed else "")))
        return

    title_hard = report_title_findings(entry, sources, args, fields, tally, rows)

    evidence = book_evidence(entry, sources, fields)
    if not evidence:
        tally.books_no_evidence += 1
        if not args.only_disagreements:
            if entry.get("from_bibliography"):
                detail = "matched %s but it holds no %s to compare" % (
                    " + ".join(s["source"] for s in sources),
                    " or ".join(f for f in fields if f in BOOK_FIELDS))
            else:
                detail = "nothing cited to compare against; %s" % "; ".join(
                    "%s: %s%s" % (s["source"], s.get("title") or "?", year_span(s))
                    for s in sources)
            rows.append((DIM, entry["key"], "BOOK-NO-DATA", detail))
        return

    tally.books_matched += 1
    names = "%s on %s" % (" + ".join("%s%s" % (s["source"], year_span(s))
                                     for s in sources), ", ".join(evidence))
    single = len(sources) == 1
    if single:
        tally.books_one_source += 1

    differences = compare_book(entry, sources, fields)
    if differences:
        tally.books_disagreeing += 1
        verdict = "BOOK-DISAGREE-1" if single else "BOOK-DISAGREE"
        for field, detail in differences:
            rows.append((YELLOW, entry["key"], verdict, "%s: %s" % (field, detail)))
    elif not title_hard and not args.only_disagreements:
        rows.append((GREEN, entry["key"],
                     "BOOK-AGREE-1" if single else "BOOK-AGREE", names))


def run_isbn_discovery(entries, args, fetcher, tally):
    findings = []
    for entry in entries:
        if entry["kind"] != "book":
            continue
        if entry.get("isbn"):
            tally.isbn_used += 1
            print("  %sHAVE-ISBN%s     [%s] %s (%s)"
                  % (DIM, RESET, entry["key"], entry["isbn"],
                     entry.get("isbn_from") or "bibliography"))
            continue
        path = cache_path(args.cache, "isbn", entry["key"])
        payload = None if args.refresh else load_cached(path)
        if payload is None:
            accepted, rejected = discover_isbn(fetcher, entry)
            store_cached(path, {"accepted": accepted, "rejected": rejected})
        else:
            accepted, rejected = payload["accepted"], payload["rejected"]

        candidates = []
        for edition in accepted:
            for raw in edition["isbns"]:
                thirteen = isbn13(raw)
                if not thirteen or thirteen in [c["isbn13"] for c in candidates]:
                    continue
                candidates.append({
                    "isbn13": thirteen,
                    "source_form": raw,
                    "converted": len(clean_isbn(raw) or "") == 10,
                    "year": edition["year"],
                    "publishers": edition["publishers"],
                    "format": edition.get("format"),
                    "title": edition["title"],
                })
        finding = {
            "key": entry["key"], "title": entry["title"], "year": entry.get("year"),
            "publisher": entry.get("publisher"), "authors": entry.get("authors"),
            "candidates": candidates,
            "near_misses": [
                {"isbn": e["isbns"][0], "year": e["year"], "publishers": e["publishers"],
                 "title": e["title"], "checks": e["checks"], "english": e["english"]}
                for e in rejected[:6]
            ],
        }
        findings.append(finding)
        if len(candidates) == 1:
            tally.isbn_found += 1
            verdict, colour = "ISBN-FOUND", GREEN
        elif candidates:
            tally.isbn_uncertain += 1
            verdict, colour = "ISBN-MULTI", YELLOW
        else:
            tally.isbn_none += 1
            verdict, colour = "ISBN-NONE", RED
        detail = ", ".join(
            "%s (%s, %s%s)" % (c["isbn13"], c["year"], "|".join(c["publishers"][:2]),
                               ", converted from ISBN-10" if c["converted"] else "")
            for c in candidates) or "no edition agreed on title+author+year+publisher"
        print("  %s%-14s%s [%s] %s" % (colour, verdict, RESET, entry["key"], detail))

    if args.json:
        try:
            with open(args.json, "w", encoding="utf-8") as handle:
                json.dump(findings, handle, indent=1, sort_keys=True, ensure_ascii=False)
        except OSError as exc:
            print("could not write %s: %s" % (args.json, exc))

    print("\nISBN discovery: %d already had one, %d single candidate, %d ambiguous, "
          "%d with no agreeing edition."
          % (tally.isbn_used, tally.isbn_found, tally.isbn_uncertain, tally.isbn_none))
    print("A candidate is not a confirmation. Every row still needs a human to check "
          "that the ISBN denotes the edition the bibliography cites.")
    return 0


def print_summary(args, tally, skipped_lines):
    if tally.checked:
        print("\nChecked %d entr%s with a DOI: %d agree, %s%d disagree%s, "
              "%d single-source, %d not found."
              % (tally.checked, "y" if tally.checked == 1 else "ies",
                 tally.checked - tally.disagreeing - tally.one_source - tally.not_found,
                 YELLOW, tally.disagreeing, RESET, tally.one_source, tally.not_found))
    if tally.books_checked:
        print("Checked %d book entr%s: %d compared (%d agree, %s%d disagree%s), "
              "%d matched but had nothing comparable, %d unmatched."
              % (tally.books_checked, "y" if tally.books_checked == 1 else "ies",
                 tally.books_matched, tally.books_matched - tally.books_disagreeing,
                 YELLOW, tally.books_disagreeing, RESET,
                 tally.books_no_evidence, tally.books_no_match))
    if tally.other_kind:
        print("%sSkipped %d entries that are neither DOI-bearing nor book-shaped "
              "(talks, blog posts, industry reports) -- not cross-checkable here.%s"
              % (DIM, tally.other_kind, RESET))
    if skipped_lines:
        print("%sIgnored %d input line(s) that contained no DOI.%s"
              % (DIM, skipped_lines, RESET))
    if tally.registry_only:
        print("%s%d ad-hoc DOI(s) had no bibliography entry, so the registries were "
              "compared only against each other (the -REG verdicts).%s"
              % (DIM, tally.registry_only, RESET))
    if tally.derived:
        print("%s%d agreement(s) rest on OpenAlex, which ingests Crossref and so inherits "
              "its errors. Those are weak confirmations, not independent ones.%s"
              % (DIM, tally.derived, RESET))
    if tally.dblp_down:
        print("%s%d entr%s fell back to OpenAlex because DBLP could not be reached, not "
              "because DBLP lacked the record. DBLP is the independent opinion, so those "
              "checks are weaker than they look -- rerun with --refresh later.%s"
              % (YELLOW, tally.dblp_down, "y" if tally.dblp_down == 1 else "ies", RESET))
    if tally.books_one_source:
        print("%s%d book(s) matched only one catalogue (the -1 verdicts), so nothing "
              "cross-checked them. One catalogue agreeing with itself is not "
              "confirmation, and a lone catalogue that disagrees may simply be wrong.%s"
              % (DIM, tally.books_one_source, RESET))
        if tally.google_unavailable and not args.google_key:
            print("%sGoogle Books returned no record for %d book(s). Without --google-key "
                  "(or GOOGLE_BOOKS_API_KEY) calls are billed to a shared anonymous Google "
                  "project whose daily quota is normally already spent, so every request "
                  "fails with HTTP 429 and books fall back to Open Library alone.%s"
                  % (DIM, tally.google_unavailable, RESET))
    if tally.network_failed:
        print("%s%d entr%s could not be fetched (network or registry error). "
              "Those results are incomplete and were not cached.%s"
              % (RED, tally.network_failed,
                 "y" if tally.network_failed == 1 else "ies", RESET))
    if tally.title_soft or tally.title_hard:
        print("Titles: %s%d hard mismatch(es)%s, %d soft finding(s). A soft finding means "
              "the entry and the registry name the same work, but the entry records it "
              "less completely (usually a dropped subtitle)."
              % (YELLOW, tally.title_hard, RESET, tally.title_soft))
    total_disagreeing = tally.disagreeing + tally.books_disagreeing + tally.title_hard
    if total_disagreeing:
        print("%sA disagreement is not a correction.%s Registries and catalogues differ, "
              "and the registry can be the wrong one. Read the primary source before "
              "changing any entry." % (YELLOW, RESET))


def self_test():
    failures = []

    def check(got, want, label):
        if got != want:
            failures.append("%s: got %r, want %r" % (label, got, want))

    check(extract_doi("see https://doi.org/10.1234/abc.def), p. 3"), "10.1234/abc.def",
          "a DOI inside a citation")
    check(isbn_valid("9780000000002"), True, "a valid ISBN-13 check digit")
    check(isbn_valid("9780000000003"), False, "a wrong ISBN-13 check digit")
    check(isbn10_to_13("0306406152"), "9780306406157", "ISBN-10 to ISBN-13")
    check(title_matches("Working Soil: A Practical Handbook", "Working Soil"), True,
          "the catalogue dropped the subtitle")
    check(title_matches("Working Soil", "Working Soil in 30 Minutes"), False,
          "a longer catalogue title is a different book")
    sample = bibliography_from_text(
        "@book{Smi08,\n  author = {Smith, Jan},\n  title = {A Book About {Things}},\n"
        "  edition = {2},\n  publisher = {Example Press},\n  year = {2008},\n"
        "  origdate = {2001},\n  isbn = {978-0-00-000000-2},\n}\n\n"
        "@article{Jon09,\n  author = {Jones, Rae and Lee, Kim},\n  title = {An Article},\n"
        "  journal = {A Journal},\n  volume = {3},\n  pages = {1--9},\n  year = {2009},\n"
        "  doi = {10.1234/xyz.9},\n}\n\n"
        "@book{Acm17,\n  author = {{Acme Example Group}},\n  title = {A Report},\n"
        "  year = {2017},\n  url = {https://example.org/r.pdf},\n}\n")
    book, article, report = sample
    check(book["kind"], "book", "a @book with no doi and no url is a book")
    check(book["publisher"], "Example Press", "the publisher comes from its own field")
    check(book["isbn"], "9780000000002", "the ISBN is read without its hyphens")
    check(book["title"], "A Book About Things", "braces are dropped from the title")
    check(book["year"], "2008", "the year of the printing read, not origdate")
    check(book["authors"], ["Smith"], "the surname of the author")
    check(article["kind"], "doi", "an entry with a doi is checked by its DOI")
    check(article["pages"], "1-9", "BibTeX page ranges are read")
    check(article["venue"], "A Journal", "the journal is the venue")
    check(article["authors"], ["Jones", "Lee"], "every author surname")
    check(report["kind"], "other", "a book-shaped entry with a url is a report")
    check(report["authors"], ["Acme Example Group"], "a corporate author keeps its words")
    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def default_cache_folder(config):
    return tool_cache_folder(config, "metadata-check")


def main():
    parser = build_parser()
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    config = None
    no_input = not (args.bibliography or args.doi or args.doi_list or args.isbn
                    or args.stdin_flag) and sys.stdin.isatty()
    if no_input or args.bibliography or not args.cache:
        config = load_book(args, TOOL)
    if no_input:
        bibliography = config.sources.bibliography
        if not bibliography or not Path(bibliography).is_file():
            print("SKIPPED the book has no bibliography (%s)" % bibliography)
            return 0
        args.bibliography = str(bibliography)
    if not args.cache:
        args.cache = str(default_cache_folder(config))

    if args.stdin_flag not in (None, "-"):
        parser.error("unexpected argument %r (use '-' to read DOIs from stdin)"
                     % args.stdin_flag)
    if args.key and not args.bibliography:
        parser.error("--key needs the bibliography")

    valid_fields = set(ARTICLE_FIELDS) | set(BOOK_FIELDS)
    fields = [f.strip() for f in args.compare.split(",") if f.strip()]
    unknown = set(fields) - valid_fields
    if not fields or unknown:
        parser.error("--compare accepts %s" % ", ".join(sorted(valid_fields)))

    global GREEN, YELLOW, RED, DIM, RESET, UA
    if args.no_color or not sys.stdout.isatty():
        GREEN = YELLOW = RED = DIM = RESET = ""
    UA = user_agent(args.contact)

    entries, skipped_lines, have_input = collect_entries(args, parser)
    if not have_input:
        parser.error("need --bibliography, --doi, --isbn, --doi-list, or DOIs piped on stdin")

    if not entries:
        print("No checkable entries found in the input.")
        if skipped_lines:
            print("%d input line(s) contained no DOI." % skipped_lines)
        return 0

    try:
        Path(args.cache).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        parser.error("cannot create cache directory %s: %s" % (args.cache, exc))

    fetcher = Fetcher()
    tally = Tally()
    rows = []

    if args.discover_isbn:
        return run_isbn_discovery(entries, args, fetcher, tally)

    for entry in entries:
        if entry["kind"] == "doi":
            check_doi_entry(entry, args, fetcher, fields, tally, rows)
        elif entry["kind"] == "book":
            check_book_entry(entry, args, fetcher, fields, tally, rows)
        else:
            tally.other_kind += 1

    for color, key, verdict, detail in rows:
        print("  %s%-14s%s [%s] %s" % (color, verdict, RESET, key, detail))

    print_summary(args, tally, skipped_lines)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
