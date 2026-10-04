import re
from pathlib import Path

from bibliography import read_identities
from source_files import FETCH
from source_registry import read_bank

NEEDED_FILE_NAME = "needed.txt"
SEPARATOR = " | "
NO_LINK = "no link known"

MANUAL = "MANUAL FETCH REQUIRED"
NO_FREE_COPY = "NO OPEN-ACCESS COPY"
NOT_FETCHED_STATUSES = ("paywalled", "blocked", "abstract-only", "too-short", "failed")

URL_RE = re.compile(r"https?://[^\s<>\"'`)\]]+")
PREPRINT_ONLY_RE = re.compile(
    r'cached text below is the .{0,60}preprint|preprint, not the paper of record|'
    r'verified against the preprint only', re.I)

HEADER = (
    "# Sources to download by hand. Save each file in this folder under any name;\n"
    "# the next download run finds its entry, files it in the library and drops its line.\n"
)


def to_add_folder(config):
    return Path(config.sources.to_add)


def needed_file(folder):
    return Path(folder) / NEEDED_FILE_NAME


def field(entry, name):
    return (entry.field(name) or "").strip()


def identity_field(identity, *names):
    return identity.plain(*names) if identity is not None else ""


def describe(entry, reason, identity=None):
    return {
        "key": entry.key,
        "title": identity_field(identity, "title"),
        "authors": identity_field(identity, "author", "editor"),
        "year": identity_field(identity, "year"),
        "venue": identity_field(identity, "journal", "booktitle", "publisher", "howpublished"),
        "doi": identity_field(identity, "doi"),
        "isbn": identity_field(identity, "isbn"),
        "urls": URL_RE.findall(field(entry, "Access URLs")),
        "access_raw": field(entry, "Access URLs"),
        "page_urls": URL_RE.findall(identity_field(identity, "url")),
        "status": reason,
    }


def failed_fetch(folders, key):
    record = folders.read_origin_record(key, FETCH) or {}
    status = record.get("status", "")
    return status if status in NOT_FETCHED_STATUSES else ""


def collect(list_path, folders, bibliography_path=None):
    known = read_identities(bibliography_path)
    gated, no_free_copy, fetch_failed, preprint_only = [], [], [], []
    for entry in read_bank(list_path).entries:
        identity = known.get(entry.key)
        status = field(entry, "Access status")
        if status and PREPRINT_ONLY_RE.search(entry.raw):
            preprint_only.append(describe(entry, status, identity))
            continue
        if folders.file(entry.key + ".txt").exists():
            continue
        if MANUAL in status:
            gated.append(describe(entry, status, identity))
        elif NO_FREE_COPY in status:
            no_free_copy.append(describe(entry, status, identity))
        elif failed_fetch(folders, entry.key):
            fetch_failed.append(describe(entry, "fetch " + failed_fetch(folders, entry.key),
                                         identity))
    return gated, no_free_copy, fetch_failed, preprint_only


def needed_items(list_path, folders, bibliography_path=None):
    gated, no_free_copy, fetch_failed, _preprint_only = collect(list_path, folders,
                                                                bibliography_path)
    return sorted(gated + no_free_copy + fetch_failed, key=lambda item: item["key"].lower())


def needed_line(item):
    page_urls = item.get("page_urls") or []
    link = item["urls"][0] if item["urls"] else page_urls[0] if page_urls else (
        "https://doi.org/" + item["doi"] if item["doi"] else (
            "ISBN " + item["isbn"] if item["isbn"] else NO_LINK))
    parts = (item["key"], item["title"] or "(no title recorded)", item["authors"] or "-",
             item["year"] or "-", link)
    return SEPARATOR.join(" ".join(part.split()) for part in parts)


def needed_text(items):
    return HEADER + "".join(needed_line(item) + "\n" for item in items)


def write_needed(folder, items):
    path = needed_file(folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(needed_text(items), encoding="utf-8")
    return path


def needed_keys(folder):
    path = needed_file(folder)
    if not path.is_file():
        return []
    return [line.split(SEPARATOR, 1)[0].strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]


def drop_needed_line(folder, key):
    path = needed_file(folder)
    if not path.is_file():
        return False
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    kept = [line for line in lines if line.split(SEPARATOR, 1)[0].strip() != key]
    if len(kept) == len(lines):
        return False
    path.write_text("".join(kept), encoding="utf-8")
    return True
