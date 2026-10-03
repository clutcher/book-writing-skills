#!/usr/bin/env python3
"""Fetch a source into the book's cache: the original bytes AND the extracted text.

Every piece of verification that opens a source runs this script, so the bytes are
kept. An agent that downloads a paper, reads it and moves on leaves nothing the next
run can re-open, and the next run pays for the same download again.

For each citation key the cache (`sources.library`) holds two files:

    <Key>.<ext>   the original bytes as served (pdf / html / src.txt)
    <Key>.txt     the extracted, greppable text

When the original is itself plain text it is stored as <Key>.src.txt, so it does not
collide with the extraction. An origin record (see source_files.py) keeps the fetch:
source URL, HTTP status, content type, byte counts, sha256 of both files, and for a
fetch that did not produce a cache entry, the reason and a 300-character sample.

What it refuses to cache. The dangerous failure is a source that looks fetched but is
not: a bot challenge, a landing page selling the PDF, an abstract stub. Those extract
to a few hundred plausible characters, and a later grep that finds nothing reads like
"the paper does not say this". So a fetch is rejected, not cached, when:

  * bot-challenge markers in the body       -> blocked
  * HTTP 401 / 402 / 403                    -> paywalled
  * paywall markers + short text            -> abstract-only
  * extraction under --min-chars (2000)     -> too-short

These are attempt outcomes about one request, in lower case. The list's `Access status`
is a durable judgment in upper case, reached after the free routes were tried; an
outcome is evidence toward a status and is never copied into the list as one.

Dry run by default. Without --fix the script fetches nothing and writes nothing: it
lists, for each key, whether it is cached and which URL it would try first. With --fix
it downloads, writes the cache files and the origin record, and files the cache lines
in the sources list. --dry-run is still accepted and wins over --fix.

Filing the cache lines. With --fix the script replaces an existing `**Cached ...:**` pair
rather than adding a second one, inserts a missing pair among the metadata fields
(always above the entry's `---` and above Verified quotes / Key findings), and moves a
misplaced pair back inside the entry. It refuses to write a line for a file that is not
on disk, and writes nothing for a failed fetch: that needs an `Access status`, which is
a judgment left to a person. A key with no entry is reported, never invented.

A key holding both files is skipped; --force refetches. A key holding only <Key>.txt
(a hand-made extraction) is `incomplete` and left alone unless --complete-partial is
passed, because overwriting a hand-curated extraction with a machine one is a loss.

Keys that are not plain file names. A key becomes a file name in the cache, so a key
must be letters, digits and + _ . - only, starting with a letter or digit. Any other key
(one with a slash, or `..`) is refused and nothing is written for it.

What could not be fetched. After every run with --fix that fetched (not --file),
`needed.txt` in the sources-to-add folder is made again from the list and the fetch
records: one line per source still to download by hand (title, authors, year, link).
match-added-files.py files what the author saves there.

Politeness: --delay seconds between requests, a User-Agent that names this project, and
--max as a hard per-run cap so a bulk run cannot stampede a publisher. curl is told to
use only http and https, also after a redirect, and to stop at --max-bytes, so a list
entry cannot make it read a local file or fill the disk. If a site refuses the request,
that is an answer: record it, do not work around it.

Needs `curl` and `pdftotext` on PATH (SKIPPED when missing). BeautifulSoup is used for
HTML when it can be imported; a standard-library parser is used otherwise.

Usage:
  fetch.py --all                                          what would be fetched (dry run)
  fetch.py --key Smi99 --url https://example.org/paper.pdf --fix
  fetch.py --key Smi99 --file ~/Downloads/paper.pdf --fix a file a person downloaded
  fetch.py --all --max 25 --fix                           every key in the list
  fetch.py --keys Smi99,Jon01 --fix                       some keys from the list
  fetch.py --self-test
"""

import argparse
import datetime
import hashlib
import html
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import (FETCH, SourceFolders, add_config_arguments, cache_references,
                          folders_from_config, load_book, tool_failed)
from citation_key import ENTRY_HEADING, FENCE_LINE, is_placeholder, is_safe_file_key
from user_agent import USER_AGENT
import sources_to_add

TOOL = "fetch"

DEFAULT_MIN_CHARS = 2000
DEFAULT_MAX = 25
DEFAULT_DELAY = 2.0
DEFAULT_TIMEOUT = 60
DEFAULT_MAX_BYTES = 200 * 1024 * 1024
PDFTOTEXT_TIMEOUT = 300

URL_FIELDS = ("DOI/URL", "Access URLs", "DOI", "URL", "Access note")

URL_RE = re.compile(r"https?://[^\s<>\"'\)\]]+")

DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s<>\"',\]]+)")
ENTRY_RE = ENTRY_HEADING
FIELD_RE = re.compile(r"^\*\*([^*:]+):\*\*(.*)$")

CACHE_FIELD_RE = re.compile(r"^\*\*Cached (?:text|original):\*\*")
TRAILING_FIELD_RE = re.compile(r"^\*\*(Record history|Fetch note|Note|Findings):\*\*")
CONTENT_FIELD_RE = re.compile(r"^\*\*(?:Verified quotes|Key findings):\*\*")
SEPARATOR_RE = re.compile(r"^-{3,}\s*$")
FENCE_RE = re.compile(r"^```")

NOT_ORIGINAL_SUFFIXES = (".fetch.json", ".ocr.json", ".layout.txt", ".retry", ".extract.txt")

UNFETCHABLE_HOSTS = (
    "youtube.com",
    "youtu.be",
    "vimeo.com",
    "x.com",
    "twitter.com",
    "amazon.com",
    "amazon.co.uk",
)

PAYWALL_PRONE_HOSTS = (
    "dl.acm.org",
    "ieeexplore.ieee.org",
    "sciencedirect.com",
    "link.springer.com",
    "onlinelibrary.wiley.com",
    "tandfonline.com",
    "jstor.org",
    "nature.com",
    "sagepub.com",
    "doi.org",
)

CHALLENGE_MARKERS = (
    "just a moment",
    "attention required",
    "verify you are human",
    "enable javascript and cookies",
    "checking your browser",
    "captcha",
    "unusual traffic",
    "access denied",
    "request unsuccessful",
    "incapsula",
)

PAYWALL_MARKERS = (
    "get access",
    "purchase pdf",
    "purchase access",
    "buy article",
    "add to cart",
    "institutional login",
    "sign in to download",
    "subscribe to view",
    "access through your institution",
    "get full access",
    "rent this article",
    "preview is not available",
    "you do not have access",
    "log in to view",
    "abstract only",
)


class Rejected(Exception):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status
        self.reason = reason


class TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "head"}
    BREAK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip_depth += 1
        elif tag in self.BREAK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip_depth:
            self.skip_depth -= 1
        elif tag in self.BREAK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip_depth:
            self.parts.append(data)

    def text(self):
        return "".join(self.parts)


def today():
    return datetime.date.today().isoformat()


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def missing_external_tools(tools=("curl", "pdftotext")):
    return [tool for tool in tools if shutil.which(tool) is None]


def host_of(url):
    try:
        return (urllib.parse.urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def is_unfetchable(url):
    host = host_of(url)
    return any(host == bad or host.endswith("." + bad) for bad in UNFETCHABLE_HOSTS)


def url_rank(url):
    host = host_of(url)
    lowered = url.lower()
    if lowered.endswith(".pdf") or "/pdf" in lowered:
        rank = 0
    elif "arxiv.org" in host or "pmc.ncbi.nlm.nih.gov" in host:
        rank = 1
    elif any(host == bad or host.endswith("." + bad) for bad in PAYWALL_PRONE_HOSTS):
        rank = 8
    else:
        rank = 4
    if host == "doi.org":
        rank = 9
    return rank


def trim_doi(doi):
    doi = doi.rstrip(".,;")
    while doi.endswith(")") and doi.count(")") > doi.count("("):
        doi = doi[:-1].rstrip(".,;")
    return doi


class Entry:
    def __init__(self, key, heading):
        self.key = key
        self.heading = heading
        self.urls = []
        self.access_status = ""

    def add_urls(self, text):
        for url in URL_RE.findall(text):
            url = url.rstrip(".,;")
            if url not in self.urls:
                self.urls.append(url)
        for doi in DOI_RE.findall(text):
            doi = trim_doi(doi)
            if doi.lower().startswith("10.") and "doi.org/" + doi not in " ".join(self.urls):
                url = "https://doi.org/" + doi
                if url not in self.urls:
                    self.urls.append(url)

    def candidates(self):
        usable = [url for url in self.urls if not is_unfetchable(url)]
        return sorted(usable, key=url_rank)


def parse_list(path):
    entries = []
    current = None
    in_url_field = False
    in_fence = False
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if FENCE_LINE.match(line):
                in_fence = not in_fence
                current = None
                continue
            if in_fence:
                continue
            heading = ENTRY_RE.match(line)
            if heading and is_placeholder(heading.group(1)):
                current = None
                continue
            if heading:
                current = Entry(heading.group(1), line.strip())
                entries.append(current)
                in_url_field = False
                continue
            if current is None:
                continue
            field = FIELD_RE.match(line)
            if field:
                name = field.group(1).strip()
                value = field.group(2)
                in_url_field = name in URL_FIELDS
                if name == "Access status":
                    current.access_status = value.strip()
                if in_url_field:
                    current.add_urls(value)
                continue
            if in_url_field and (line.startswith(("-", "*", " ", "\t"))):
                current.add_urls(line)
                continue
            if not line.strip():
                continue
            in_url_field = False
    return entries


def curl(url, out_path, timeout, force_http11, max_bytes=DEFAULT_MAX_BYTES):
    cmd = [
        "curl", "-sSL", "--compressed", "--max-time", str(timeout), "-A", USER_AGENT,
        "--proto", "=http,https", "--proto-redir", "=http,https",
        "--max-filesize", str(max_bytes),
        "-o", out_path, "-w",
        "%{http_code}\t%{content_type}\t%{size_download}\t%{url_effective}",
    ]
    if force_http11:
        cmd.insert(1, "--http1.1")
    cmd.extend(["--url", url])
    result = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", check=False)
    if result.returncode != 0:
        return None, (result.stderr or "curl exited %d" % result.returncode).strip()
    fields = result.stdout.strip().split("\t")
    while len(fields) < 4:
        fields.append("")
    return {
        "http_code": int(fields[0] or 0),
        "content_type": fields[1].split(";")[0].strip().lower(),
        "bytes": int(fields[2] or 0),
        "final_url": fields[3] or url,
    }, None


def download(url, out_path, timeout, max_bytes=DEFAULT_MAX_BYTES):
    meta, error = curl(url, out_path, timeout, False, max_bytes)
    if meta is None or meta["http_code"] >= 400 or meta["bytes"] == 0:
        retry_path = f"{out_path}.retry"
        retry_meta, retry_error = curl(url, retry_path, timeout, True, max_bytes)
        try:
            if retry_meta is not None:
                better = meta is None or (
                    retry_meta["http_code"] < 400 and retry_meta["bytes"] > 0
                )
                if better:
                    Path(retry_path).replace(out_path)
                    return retry_meta, None
        finally:
            if Path(retry_path).exists():
                Path(retry_path).unlink()
        if meta is None:
            return None, error or retry_error
    return meta, None


def sniff_kind(path, content_type):
    with open(path, "rb") as handle:
        head = handle.read(1024)
    if head.startswith(b"%PDF"):
        return "pdf"
    if "pdf" in content_type:
        return "pdf"
    lowered = head.lower()
    if "html" in content_type or b"<html" in lowered or b"<!doctype html" in lowered:
        return "html"
    if content_type.startswith("text/") or not head:
        return "text"
    return "binary"


def extract_pdf(path):
    txt_path = f"{path}.extract.txt"
    try:
        result = subprocess.run(["pdftotext", "-layout", path, txt_path], capture_output=True,
                                encoding="utf-8", errors="replace", check=False,
                                timeout=PDFTOTEXT_TIMEOUT)
    except subprocess.TimeoutExpired:
        Path(txt_path).unlink(missing_ok=True)
        raise Rejected("failed", "pdftotext took longer than %d s" % PDFTOTEXT_TIMEOUT)
    if result.returncode != 0 or not Path(txt_path).exists():
        raise Rejected("failed", "pdftotext failed: " + (result.stderr or "").strip()[:200])
    text = Path(txt_path).read_text(encoding="utf-8", errors="replace")
    Path(txt_path).unlink()
    return text


def extract_html(raw_bytes):
    markup = raw_bytes.decode("utf-8", errors="replace")
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(markup, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "head", "nav", "footer", "header"]):
            tag.decompose()
        body = soup.find("article") or soup.find("main") or soup
        text = body.get_text("\n")
        if len(text.strip()) < 1000:
            text = soup.get_text("\n")
    except ImportError:
        parser = TextExtractor()
        parser.feed(markup)
        text = html.unescape(parser.text())
    return text


def normalise(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+$", "", line) for line in text.split("\n")]
    out = []
    blank = 0
    for line in lines:
        if line.strip():
            blank = 0
            out.append(line)
        else:
            blank += 1
            if blank <= 2:
                out.append("")
    return "\n".join(out).strip() + "\n"


def extract(path, content_type):
    kind = sniff_kind(path, content_type)
    if kind == "binary":
        raise Rejected("failed", "unsupported content type %r" % content_type)
    if kind == "pdf":
        return kind, normalise(extract_pdf(path)), ".pdf"
    if kind == "html":
        with open(path, "rb") as handle:
            return kind, normalise(extract_html(handle.read())), ".html"
    with open(path, encoding="utf-8", errors="replace") as handle:
        return kind, normalise(handle.read()), ".src.txt"


def judge(text, http_code, min_chars, allow_short):
    probe = text[:6000].lower()
    stripped = len(text.strip())

    for marker in CHALLENGE_MARKERS:
        if marker in probe:
            raise Rejected("blocked", "bot challenge (matched %r, HTTP %d)" % (marker, http_code))

    if http_code in (401, 402, 403):
        raise Rejected("paywalled", "HTTP %d" % http_code)
    if http_code >= 400:
        raise Rejected("failed", "HTTP %d" % http_code)

    hits = [marker for marker in PAYWALL_MARKERS if marker in probe]
    if hits and stripped < min_chars * 5:
        raise Rejected("abstract-only", "purchase/access page (matched %r)" % hits[0])

    if stripped < min_chars and not allow_short:
        raise Rejected("too-short",
                       "extraction is %d chars, under --min-chars %d" % (stripped, min_chars))
    return stripped


def find_original(folders, key):
    prefix = key + "."
    folder = Path(folders.files)
    if not folder.is_dir():
        return None
    for path in sorted(folder.iterdir()):
        name = path.name
        if not name.startswith(prefix) or name == key + ".txt":
            continue
        if name.endswith(NOT_ORIGINAL_SUFFIXES):
            continue
        return path
    return None


def cache_state(folders, key):
    has_text = folders.file(key + ".txt").exists()
    original = find_original(folders, key)
    if has_text and original:
        return "complete", original
    if has_text:
        return "text-only", None
    if original:
        return "original-only", original
    return "empty", None


def list_lines(folders, key, text_path, original_path, url):
    text_line = "**Cached text:** `%s` (fetched %s, sha256 %s)" % (
        folders.shown_file(Path(text_path).name), today(), sha256_of(text_path))
    original_line = "**Cached original:** `%s` (fetched %s, sha256 %s, from %s)" % (
        folders.shown_file(Path(original_path).name), today(), sha256_of(original_path), url)
    return text_line, original_line


LIST_ACTIONS = ["replaced", "inserted", "moved", "no-entry", "missing-file"]


def entry_bounds(lines, key):
    heading = "### [" + key + "]"
    start = None
    fenced = False
    for index, line in enumerate(lines):
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        if fenced or not line.startswith("### ["):
            continue
        if start is not None:
            return start, index
        if line.startswith(heading):
            start = index
    if start is None:
        return None
    return start, len(lines)


def metadata_end(block):
    for index, line in enumerate(block):
        if SEPARATOR_RE.match(line) or CONTENT_FIELD_RE.match(line):
            return index
    return len(block)


def insertion_index(block, boundary):
    for index in range(boundary):
        if TRAILING_FIELD_RE.match(block[index]):
            return index
    index = 1
    while index < boundary and not block[index].strip():
        index += 1
    while index < boundary and block[index].strip():
        index += 1
    return index


def rewrite_entry(block, text_line, original_line):
    boundary = metadata_end(block)
    existing = [index for index, line in enumerate(block) if CACHE_FIELD_RE.match(line)]
    kept = [line for index, line in enumerate(block) if index not in set(existing)]

    if existing and existing[0] < boundary:
        return kept[: existing[0]] + [text_line, original_line] + kept[existing[0]:], "replaced"

    action = "moved" if existing else "inserted"
    boundary = metadata_end(kept)
    at = insertion_index(kept, boundary)
    return kept[:at] + [text_line, original_line] + kept[at:], action


def apply_list_lines(text, updates, folders):
    lines = text.split("\n")
    outcomes = []
    for key, text_line, original_line in updates:
        missing = [reference[0] for line in (text_line, original_line)
                   for reference in cache_references(folders, line)
                   if not reference[3].exists()]
        if missing:
            outcomes.append((key, "missing-file", "not on disk: " + ", ".join(missing)))
            continue
        bounds = entry_bounds(lines, key)
        if bounds is None:
            outcomes.append((key, "no-entry", "no `### [%s]` heading in the list" % key))
            continue
        start, end = bounds
        block, action = rewrite_entry(lines[start:end], text_line, original_line)
        lines[start:end] = block
        outcomes.append((key, action, "at line %d" % (start + 1)))
    return "\n".join(lines), outcomes


def file_into_list(results, list_path, folders):
    updates = [
        (item["key"], item["text_line"], item["original_line"])
        for item in results
        if item["status"] == "cached" and item["text_line"] and item["original_line"]
    ]
    if not updates:
        print("\nList: nothing to file (no fetch produced a cache entry).")
        return
    if not list_path or not Path(list_path).exists():
        print("\nsources list not found: %s" % list_path, file=sys.stderr)
        return

    with open(list_path, encoding="utf-8") as handle:
        before = handle.read()
    after, outcomes = apply_list_lines(before, updates, folders)

    print()
    if after != before:
        with open(list_path, "w", encoding="utf-8") as handle:
            handle.write(after)
    print("List updated: %s" % list_path)

    print()
    width = max([len(key) for key, _, _ in outcomes] + [3])
    for key, action, detail in sorted(outcomes, key=lambda o: (LIST_ACTIONS.index(o[1]), o[0])):
        print("%-*s  %-13s  %s" % (width, key, action, detail))

    unfiled = [key for key, action, _ in outcomes if action in ("no-entry", "missing-file")]
    if unfiled:
        print("\nNot filed -- fix the cause, then add these by hand:\n")
        for key, text_line, original_line in updates:
            if key in unfiled:
                print("### [%s]\n%s\n%s\n" % (key, text_line, original_line))


def empty_result(key):
    return {"key": key, "status": "failed", "bytes": 0, "reason": "", "url": "",
            "text_line": "", "original_line": ""}


def process(key, urls, folders, options):
    result = empty_result(key)

    state, _existing = cache_state(folders, key)
    if state == "complete" and not options.force:
        result.update(status="skipped", bytes=folders.file(key + ".txt").stat().st_size,
                      reason="already cached")
        return result
    if state == "text-only" and not (options.force or options.complete_partial):
        result.update(status="incomplete", bytes=folders.file(key + ".txt").stat().st_size,
                      reason="extraction present, original missing (--complete-partial to fetch)")
        return result

    if not urls:
        result.update(status="no-url", reason="no fetchable URL in the list")
        return result

    if not options.write:
        result.update(status="would-fetch", url=urls[0],
                      reason="%d URL(s), first: %s" % (len(urls), urls[0]))
        return result

    attempts = []
    with tempfile.TemporaryDirectory() as workdir:
        for url in urls[: options.tries]:
            target = Path(workdir, "download")
            meta, error = download(url, target, options.timeout, options.max_bytes)
            if meta is None:
                attempts.append("%s -> %s" % (host_of(url), (error or "curl failed")[:80]))
                time.sleep(options.delay)
                continue
            try:
                outcome = accept(key, url, meta, target, folders, options)
            except Rejected as rejection:
                attempts.append("%s -> %s: %s" % (host_of(url), rejection.status, rejection.reason))
                folders.write_origin_record(key, FETCH, {
                    "key": key, "fetched": today(), "url": url,
                    "final_url": meta["final_url"], "http_code": meta["http_code"],
                    "content_type": meta["content_type"], "downloaded_bytes": meta["bytes"],
                    "status": rejection.status, "reason": rejection.reason,
                    "sample": sample_of(target, meta["content_type"]),
                })
                result.update(status=rejection.status, reason=rejection.reason, url=url)
                time.sleep(options.delay)
                continue
            time.sleep(options.delay)
            return outcome

    result.update(reason="; ".join(attempts)[:300] or "all URLs failed")
    if result["status"] == "failed" and attempts:
        for known in ("paywalled", "blocked", "abstract-only", "too-short"):
            if any(known in attempt for attempt in attempts):
                result["status"] = known
                break
    return result


def sample_of(path, content_type):
    try:
        return extract(path, content_type)[1][:300]
    except Exception:
        return ""


def store(key, url, meta, downloaded, kind, text, extension, stripped, folders):
    Path(folders.files).mkdir(parents=True, exist_ok=True)
    original_path = folders.file(key + extension)
    text_path = folders.file(key + ".txt")

    stale = find_original(folders, key)
    if stale and stale != original_path:
        stale.unlink()

    shutil.copyfile(downloaded, original_path)
    text_path.write_text(text, encoding="utf-8")

    text_line, original_line = list_lines(folders, key, text_path, original_path, url)
    folders.write_origin_record(key, FETCH, {
        "key": key, "fetched": today(), "url": url,
        "final_url": meta.get("final_url", url), "http_code": meta.get("http_code", 0),
        "content_type": meta.get("content_type", ""), "status": "cached",
        "original": folders.shown_file(original_path.name),
        "original_bytes": original_path.stat().st_size,
        "original_sha256": sha256_of(original_path),
        "text": folders.shown_file(text_path.name),
        "text_chars": stripped,
        "text_sha256": sha256_of(text_path),
        "extractor": "pdftotext -layout" if kind == "pdf" else "html-to-text",
    })
    return {
        "key": key, "status": "cached", "bytes": stripped,
        "reason": "%s, %d KB original" % (kind, original_path.stat().st_size // 1024),
        "url": url, "text_line": text_line, "original_line": original_line,
    }


def accept(key, url, meta, downloaded, folders, options):
    kind, text, extension = extract(downloaded, meta["content_type"])
    stripped = judge(text, meta["http_code"], options.min_chars, options.allow_short)
    return store(key, url, meta, downloaded, kind, text, extension, stripped, folders)


def ingest_file(key, path, url, folders, options):
    if not options.write:
        result = empty_result(key)
        result.update(status="would-fetch", url=url or "",
                      reason="would cache %s (pass --fix)" % Path(path).name)
        return result
    meta = {"http_code": 200, "content_type": "", "final_url": url or "manual download",
            "bytes": Path(path).stat().st_size}
    try:
        return accept(key, url or "manual download", meta, path, folders, options)
    except Rejected as rejection:
        result = empty_result(key)
        result.update(status=rejection.status, reason=rejection.reason, url=url or "")
        return result


STATUS_ORDER = [
    "cached", "skipped", "incomplete", "would-fetch", "paywalled", "blocked",
    "abstract-only", "too-short", "no-url", "unsafe-key", "failed",
]

UNSAFE_KEY_REASON = ("not a plain file name: use letters, digits and + _ . - only, "
                     "starting with a letter or digit")


def unsafe_key_result(key):
    result = empty_result(key)
    result.update(status="unsafe-key", reason=UNSAFE_KEY_REASON)
    return result


def report(results, write):
    width = max([len(r["key"]) for r in results] + [3])
    print()
    print("%-*s  %-13s  %10s  %s" % (width, "KEY", "STATUS", "BYTES", "DETAIL"))
    print("%s  %s  %s  %s" % ("-" * width, "-" * 13, "-" * 10, "-" * 40))
    ordered = sorted(results, key=lambda r: (
        STATUS_ORDER.index(r["status"]) if r["status"] in STATUS_ORDER else 99, r["key"]))
    for item in ordered:
        size = "%d" % item["bytes"] if item["bytes"] else "-"
        print("%-*s  %-13s  %10s  %s" % (width, item["key"], item["status"], size,
                                         item["reason"][:80]))
    counts = {}
    for item in results:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    print()
    print("total %d: " % len(results) + ", ".join(
        "%s %d" % (status, counts[status]) for status in STATUS_ORDER if status in counts))
    if not write:
        print("(dry run: nothing was fetched or written; pass --fix to fetch)")


FIXTURE_LIST = """# Sources List

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)
**Cached text:** `{d}/<Key>.txt`
```

### [Smi99] Smith, "A web page" (1999)

**Full title:** A web page
**Authors:** Sam Smith
**Year:** 1999
**Access URLs:** https://example.org/smi99.html, see also doi 10.1234/abc.(x)
**Note:** kept below the cache lines

---

### [Jon01] Jones, "Not fetched" (2001)

**Full title:** Not fetched
**DOI:** 10.5555/jon01

---
"""

FIXTURE_PAGE = ("<html><head><title>A web page</title><script>x()</script></head><body>"
                "<article><p>" + "The page body says what the source says. " * 80
                + "</p></article></body></html>")


def self_test():
    failures = []

    def require(condition, message):
        if not condition:
            failures.append(message)

    options = argparse.Namespace(min_chars=DEFAULT_MIN_CHARS, allow_short=False, force=False,
                                 complete_partial=False, write=True, tries=3,
                                 timeout=DEFAULT_TIMEOUT, delay=0, max_bytes=DEFAULT_MAX_BYTES)
    require(url_rank("https://arxiv.org/abs/1") < url_rank("https://doi.org/10.1/x"),
            "an open repository ranks before a DOI")
    require(url_rank("https://example.org/a.pdf") == 0, "a direct PDF ranks first")
    require(trim_doi("10.1234/abc.;") == "10.1234/abc", "trailing punctuation is trimmed")
    require(trim_doi("10.1234/abc.(x))") == "10.1234/abc.(x)", "an unmatched ) is dropped")
    for text, status in (("Just a moment...", "blocked"), ("x" * 50, "too-short")):
        try:
            judge(text, 200, DEFAULT_MIN_CHARS, False)
            failures.append("%r was not rejected" % text[:20])
        except Rejected as rejection:
            require(rejection.status == status, "%r gave %s" % (text[:20], rejection.status))
    try:
        judge("y" * 3000, 403, DEFAULT_MIN_CHARS, False)
        failures.append("HTTP 403 was not rejected")
    except Rejected as rejection:
        require(rejection.status == "paywalled", "HTTP 403 is paywalled")

    with tempfile.TemporaryDirectory() as folder:
        local_file = Path(folder) / "private.txt"
        local_file.write_text("a private file on this machine\n" * 200, encoding="utf-8")
        if shutil.which("curl"):
            meta, _error = curl(local_file.as_uri(), str(Path(folder) / "copy"), 10, False)
            require(meta is None and not (Path(folder) / "copy").exists(),
                    "curl must refuse a file:// URL")
        dry_folders = SourceFolders(root=Path(folder), files=Path(folder) / "files",
                                    origin=Path(folder) / "files")
        dry_run = ingest_file("Smi99", local_file, "", dry_folders,
                              argparse.Namespace(**{**vars(options), "write": False}))
        require(dry_run["status"] == "would-fetch" and not dry_folders.files.exists(),
                "without --fix a file is not cached")
        unsafe_keys = ["../../../../outside/notes", "sub/Smi99", ".hidden"]
        refused, _capped = fetch_work([(key, ["https://example.org/a.pdf"]) for key in unsafe_keys],
                                      dry_folders, argparse.Namespace(**{**vars(options), "max": 0}))
        require([item["status"] for item in refused] == ["unsafe-key"] * len(unsafe_keys)
                and not dry_folders.files.exists(),
                "a key that is not a plain file name is refused before any download")
        listed = Path(folder) / "list.md"
        listed.write_text("```\n### [Abc99] Example in the format block\n**Access URLs:** "
                          "https://example.org/a\n```\n\n### [<Key>] Placeholder\n"
                          "**Access URLs:** https://example.org/b\n\n### [Smi99] Real\n"
                          "**Access URLs:** https://example.org/c\n", encoding="utf-8")
        require([key for key, _ in work_from_list(listed, None)] == ["Smi99"],
                "--all skips the format example and the <Key> placeholder")

    for merged in (False, True):
        layout = "merged origin" if merged else "records beside files"
        with tempfile.TemporaryDirectory() as root:
            files = Path(root) / "sources" / "library"
            origin = Path(root) / "sources" / "library-index" if merged else files
            folders = SourceFolders(root=Path(root), files=files, origin=origin)
            list_path = Path(root) / "list.md"
            list_path.write_text(FIXTURE_LIST.format(d=folders.shown_files), encoding="utf-8")
            entries = {entry.key: entry for entry in parse_list(list_path)}
            require(entries["Smi99"].candidates()[0] == "https://example.org/smi99.html",
                    "%s: the page URL is the first candidate" % layout)
            require("https://doi.org/10.5555/jon01" in entries["Jon01"].urls,
                    "%s: a bare DOI becomes a doi.org URL" % layout)
            page = Path(root) / "page.html"
            page.write_text(FIXTURE_PAGE, encoding="utf-8")
            result = ingest_file("Smi99", page, "https://example.org/smi99.html", folders, options)
            require(result["status"] == "cached", "%s: the page was not cached: %s"
                    % (layout, result["reason"]))
            require(folders.file("Smi99.html").exists() and folders.file("Smi99.txt").exists(),
                    "%s: original and extraction are both written" % layout)
            record = folders.read_origin_record("Smi99", FETCH)
            require(record and record["status"] == "cached", "%s: no origin record" % layout)
            require("script" not in folders.file("Smi99.txt").read_text(encoding="utf-8"),
                    "%s: script text leaked into the extraction" % layout)
            (files / "Smi99.ocr.json").write_text("{}", encoding="utf-8")
            require(find_original(folders, "Smi99") == folders.file("Smi99.html"),
                    "%s: a sidecar was taken for the original" % layout)
            require(cache_state(folders, "Smi99")[0] == "complete", "%s: state" % layout)
            before = list_path.read_text(encoding="utf-8")
            after, outcomes = apply_list_lines(before, [(
                "Smi99", result["text_line"], result["original_line"])], folders)
            require(outcomes[0][1] == "inserted", "%s: the pair is inserted" % layout)
            require(after.index("**Cached text:**", after.index("[Smi99]"))
                    < after.index("**Note:** kept"), "%s: the pair sits before Note" % layout)
            again, outcomes = apply_list_lines(after, [(
                "Smi99", result["text_line"], result["original_line"])], folders)
            require(outcomes[0][1] == "replaced" and again == after,
                    "%s: filing twice must replace, not add" % layout)
            _text, outcomes = apply_list_lines(before, [(
                "Jon01", "**Cached text:** `%s/Jon01.txt`" % folders.shown_files,
                "**Cached original:** `%s/Jon01.pdf`" % folders.shown_files)], folders)
            require(outcomes[0][1] == "missing-file", "%s: a missing file is refused" % layout)
            _text, outcomes = apply_list_lines(before, [(
                "Zed05", result["text_line"], result["original_line"])], folders)
            require(outcomes[0][1] == "no-entry", "%s: an unknown key is not invented" % layout)

    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def write_needed_list(config, list_path, folders):
    folder = sources_to_add.to_add_folder(config)
    written = sources_to_add.write_needed(folder, sources_to_add.needed_items(list_path, folders))
    print("needed.txt: %d source(s) to download by hand -> %s"
          % (len(sources_to_add.needed_keys(folder)), written))


def work_from_list(list_path, keys):
    wanted = {k.strip() for k in keys.split(",") if k.strip()} if keys else None
    work, seen = [], set()
    for entry in parse_list(list_path):
        if entry.key in seen:
            continue
        seen.add(entry.key)
        if wanted is not None and entry.key not in wanted:
            continue
        work.append((entry.key, entry.candidates()))
    if wanted:
        for key in sorted(wanted - {key for key, _ in work}):
            print("warning: key %s not found in the list" % key, file=sys.stderr)
    return work


def fetch_work(work, folders, options):
    results, fetched, capped = [], 0, 0
    for key, urls in work:
        if not is_safe_file_key(key):
            results.append(unsafe_key_result(key))
            continue
        if options.max and fetched >= options.max and options.write:
            capped += 1
            continue
        outcome = process(key, urls, folders, options)
        results.append(outcome)
        if outcome["status"] not in ("skipped", "incomplete", "no-url", "would-fetch"):
            fetched += 1
    return results, capped


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    parser.add_argument("--key", help="citation key to fetch (with --url or --file)")
    parser.add_argument("--url", help="URL to fetch for --key")
    parser.add_argument("--file", help="a file already downloaded by hand, cached for --key")
    parser.add_argument("--all", action="store_true", help="every key in the sources list")
    parser.add_argument("--keys", help="comma-separated keys from the sources list")
    parser.add_argument("--list", dest="sources_list", help="the sources list (default: sources.list)")
    parser.add_argument("--files-dir", help="the cache folder (default: sources.library)")
    parser.add_argument("--force", action="store_true", help="refetch keys already cached")
    parser.add_argument("--complete-partial", action="store_true",
                        help="fetch originals for keys that have only an extraction")
    parser.add_argument("--dry-run", action="store_true",
                        help="list what would be fetched (the default; wins over --fix)")
    parser.add_argument("--fix", action="store_true",
                        help="fetch, write the cache files and file the cache lines in the list")
    parser.add_argument("--max", type=int, default=DEFAULT_MAX,
                        help="per-run fetch cap (default %d; 0 means no cap)" % DEFAULT_MAX)
    parser.add_argument("--tries", type=int, default=3, help="candidate URLs per key (default 3)")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="seconds between requests")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="curl --max-time")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                        help="largest download accepted (default %d)" % DEFAULT_MAX_BYTES)
    parser.add_argument("--min-chars", type=int, default=DEFAULT_MIN_CHARS,
                        help="reject extractions shorter than this (default %d)" % DEFAULT_MIN_CHARS)
    parser.add_argument("--allow-short", action="store_true",
                        help="cache short extractions anyway (blog posts, forum answers)")
    parser.add_argument("--self-test", action="store_true",
                        help="test parsing, judging, caching and filing on built-in examples")
    options = parser.parse_args()
    options.write = options.fix and not options.dry_run
    if options.self_test:
        return self_test()

    config = load_book(options, TOOL)
    folders = folders_from_config(config)
    if options.files_dir:
        folders = SourceFolders(root=config.root, files=Path(options.files_dir),
                                origin=Path(options.files_dir))
    list_path = options.sources_list or config.sources.list

    if options.key and not is_safe_file_key(options.key):
        return tool_failed("--key %r is %s" % (options.key, UNSAFE_KEY_REASON), TOOL)

    if options.key and options.file:
        results = [ingest_file(options.key, options.file, options.url, folders, options)]
        report(results, options.write)
        if options.write:
            file_into_list(results, list_path, folders)
        return 0

    if options.write:
        missing = missing_external_tools()
        if missing:
            print("SKIPPED   %s not on PATH (curl: any distribution package; "
                  "pdftotext: poppler-utils)" % ", ".join(missing))
            return 0

    if options.key:
        if not options.url:
            return tool_failed("--key needs --url or --file", TOOL)
        work = [(options.key, [options.url])]
    elif options.all or options.keys:
        if not list_path or not Path(list_path).exists():
            print("SKIPPED   the book has no sources list (%s not found)" % list_path)
            return 0
        work = work_from_list(list_path, options.keys)
    else:
        return tool_failed("need --key with --url or --file, or --all, or --keys", TOOL)

    results, capped = fetch_work(work, folders, options)
    report(results, options.write)
    if options.write:
        file_into_list(results, list_path, folders)
        write_needed_list(config, list_path, folders)
    if capped:
        print("%d key(s) not attempted: --max %d reached. Run again to continue."
              % (capped, options.max))
    return 0


if __name__ == "__main__":
    sys.exit(main())
