#!/usr/bin/env python3
"""Hold every URL in the .bib file and the sources list to what it resolves to today.

The bibliography is the book's .bib file (`sources.bibliography`): its `url` fields, and its
`doi` fields read as https://doi.org/<doi>. The sources list adds its `Access URLs`.

Every other check reads files; this one's answer lives on the network, so a clean run is
a verdict about today, not a property of the book. Run it before a build that readers will
click through, not on every edit. Its --self-test needs no network.

A URL can be well formed, match its cached bytes and agree with Crossref, and still 404.
The rule worth having is bank-drift: a bibliography URL that fails while the same key's
list entry already holds one that works. The rule is narrow on purpose: a bibliography
citing a DOI while the list records a free mirror is correct and normal; only a
bibliography URL that actually fails counts.

Two traps:
  A publisher 403 is not a dead link. For a doi.org URL the authority is doi.org's own
  redirect, never what the publisher then says to an anonymous client. A registered DOI
  whose landing page answers 404 is the publisher's defect; changing the DOI would change
  the one part that is right. Only a DOI that doi.org itself cannot resolve is dead.

  A blocked network is not a dead host. A TLS-intercepting proxy can answer every
  blocked host with one identical page. So `dead` is never reported on a transport
  failure; interception is detected two ways (a certificate-name mismatch, and one body
  arriving byte-identical from two unrelated hosts) and those hosts are reported as
  unreachable, for a person to open in a browser.

Classes:
  dead           DEFECT  404 / 410 / 451, or a hostname that does not resolve
  moved          DEFECT  a permanent redirect (301/308) landing elsewhere (fixable)
  moving-target  DEFECT  an address whose content drifts: an unpinned Wayback capture
                         (fixable: pin the capture), a GitHub blob on main/master, a
                         `/latest/` docs path
  bank-drift     DEFECT  a failing bibliography URL while the list holds a working one
                         (fixable)
  gated          INFORMATIONAL  the publisher did not serve the page on a DOI doi.org
                         confirms is registered; the reference is correct
  unreachable    INFORMATIONAL  this run could not decide
  ok             INFORMATIONAL  shown with --verbose only

--fix only writes what this run verified: a redirect target the server sent, a Wayback
timestamp the archive resolved, or a working URL already in the list. It never edits a
`Cached original:` line, which records where bytes came from; "repairing" it would
falsify provenance. A defect with no verified repair stays a report.

Only http and https are opened. A redirect to any other kind of address (file:, ftp:,
data:) is not followed, and neither is a redirect from https down to plain http: such a
URL is reported as unreachable and never written as `moved`. Requests carry a User-Agent
that names this project.

Verdicts are cached under the book's work caches (`--max-age` days, default 7); the
LINK_CHECK_CACHE environment variable overrides the folder.

Usage:
  link-check.py
  link-check.py --bibliography-only
  link-check.py --fix
  link-check.py --refresh
  link-check.py --self-test
"""

import argparse
import collections
import hashlib
import http.client
import json
import os
import re
import socket
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import add_config_arguments, load_book, tool_cache_folder, tool_failed
from check_output import (DEFECT, INFORMATIONAL, SHARED_CLASSES, CheckReport, add_output_arguments,
                          skipped_for_missing)
from citation_key import ENTRY_HEADING
from user_agent import USER_AGENT

TOOL = "link-check"
CLASSES = {
    "dead": DEFECT, "moved": DEFECT, "moving-target": SHARED_CLASSES["moving-target"],
    "bank-drift": DEFECT,
    "gated": INFORMATIONAL, "unreachable": INFORMATIONAL, "ok": INFORMATIONAL,
}
CACHE_SCHEMA = 1

TIMEOUT = 30
THROTTLE = 0.4
MAX_REDIRECTS = 8
BODY_SAMPLE = 4096

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
WEB_SCHEMES = ("http", "https")

URL_RE = re.compile(r"https?://[^\s<>\]]+")
DOI_URL_RE = re.compile(r"^https?://(dx\.)?doi\.org/", re.IGNORECASE)

ACCESS_FIELDS = ("Access URLs",)

BIB_ENTRY_START = re.compile(r"^\s*@\s*(\w+)\s*[{(]\s*([^,\s]+)\s*,")
BIB_URL_FIELD = re.compile(r"^\s*(url|doi)\s*=\s*[{\"]\s*([^}\"]*?)\s*[}\"]\s*,?\s*$",
                           re.IGNORECASE)
DOI_PREFIX = "https://doi.org/"

WAYBACK_RE = re.compile(
    r"^(https?://web\.archive\.org/web/)(\d{1,14})(id_|if_)?/(.*)$", re.IGNORECASE)
WAYBACK_PINNED = 14
GITHUB_FLOATING_RE = re.compile(
    r"^https?://github\.com/[^/]+/[^/]+/blob/(main|master)/", re.IGNORECASE)
LATEST_DOCS_RE = re.compile(r"/(latest|stable|current)/", re.IGNORECASE)

DEAD_CODES = (404, 410, 451)
GATED_CODES = (202, 401, 403, 429)

DEFECTS = ("dead", "moved", "moving-target", "bank-drift")


class Probe(object):
    __slots__ = ("url", "status", "final", "chain", "error", "body_hash", "permanent")

    def __init__(self, url, status=None, final=None, chain=None, error=None,
                 body_hash=None, permanent=False):
        self.url = url
        self.status = status
        self.final = final or url
        self.chain = chain or []
        self.error = error
        self.body_hash = body_hash
        self.permanent = permanent

    def as_dict(self):
        return {"status": self.status, "final": self.final, "chain": self.chain,
                "error": self.error, "body_hash": self.body_hash,
                "permanent": self.permanent}

    @classmethod
    def from_dict(cls, url, payload):
        return cls(url, payload.get("status"), payload.get("final"),
                   payload.get("chain"), payload.get("error"),
                   payload.get("body_hash"), payload.get("permanent", False))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def web_only_opener():
    opener = urllib.request.OpenerDirector()
    for handler in (urllib.request.ProxyHandler(), urllib.request.HTTPHandler(),
                    urllib.request.HTTPSHandler(), urllib.request.HTTPDefaultErrorHandler(),
                    urllib.request.HTTPErrorProcessor(), NoRedirect(),
                    urllib.request.UnknownHandler()):
        opener.add_handler(handler)
    return opener


def scheme_of(url):
    try:
        return urllib.parse.urlsplit(url).scheme.lower()
    except ValueError:
        return ""


def refused_redirect(current, target):
    if scheme_of(target) not in WEB_SCHEMES:
        return "a redirect to %s, which is not a web address, was not followed" % target
    if scheme_of(current) == "https" and scheme_of(target) == "http":
        return "a redirect from https down to plain http (%s) was not followed" % target
    return None


def registrable(url):
    try:
        host = urllib.parse.urlsplit(url).hostname or ""
    except ValueError:
        return ""
    return ".".join(host.lower().split(".")[-2:])


class Fetcher(object):
    def __init__(self, throttle=THROTTLE, timeout=TIMEOUT):
        self.throttle = throttle
        self.timeout = timeout
        self.requests = 0
        self._last = 0.0
        self._opener = web_only_opener()
        self.body_hashes = collections.defaultdict(set)
        self.cert_mismatch = set()

    def _wait(self):
        gap = self.throttle - (time.time() - self._last)
        if gap > 0:
            time.sleep(gap)

    def _once(self, url):
        self._wait()
        self.requests += 1
        request = urllib.request.Request(url, headers=HEADERS, method="GET")
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                sample = response.read(BODY_SAMPLE)
                return (response.status, None, False,
                        hashlib.sha256(sample).hexdigest())
        except urllib.error.HTTPError as exc:
            location = exc.headers.get("Location") if exc.headers else None
            try:
                sample = exc.read(BODY_SAMPLE)
            except (OSError, ValueError):
                sample = b""
            return (exc.code, location, exc.code in (301, 308),
                    hashlib.sha256(sample).hexdigest())
        finally:
            self._last = time.time()

    def probe(self, url):
        chain = []
        current = url
        permanent_so_far = True
        for _ in range(MAX_REDIRECTS):
            try:
                status, location, permanent, body_hash = self._once(current)
            except urllib.error.URLError as exc:
                return self._transport_failure(url, current, chain, exc)
            except (socket.timeout, http.client.HTTPException, OSError, ValueError) as exc:
                return Probe(url, final=current, chain=chain,
                             error="unreachable: %s" % exc)

            if status in (301, 302, 303, 307, 308) and location:
                target = urllib.parse.urljoin(current, location)
                refusal = refused_redirect(current, target)
                if refusal:
                    return Probe(url, final=current, chain=chain,
                                 error="unreachable: %s" % refusal)
                chain.append((current, status, location))
                permanent_so_far = permanent_so_far and permanent
                current = target
                continue

            self.body_hashes[registrable(current)].add(body_hash)
            return Probe(url, status=status, final=current, chain=chain,
                         body_hash=body_hash,
                         permanent=bool(chain) and permanent_so_far)
        return Probe(url, final=current, chain=chain, error="redirect loop")

    def _transport_failure(self, url, current, chain, exc):
        reason = getattr(exc, "reason", exc)
        text = str(reason)
        if isinstance(reason, ssl.SSLCertVerificationError) or "certificate" in text.lower():
            self.cert_mismatch.add(registrable(current))
            return Probe(url, final=current, chain=chain,
                         error="intercepted: %s" % text)
        if isinstance(reason, socket.gaierror):
            return Probe(url, final=current, chain=chain, error="dns: %s" % text)
        return Probe(url, final=current, chain=chain, error="unreachable: %s" % text)

    def intercepted_hosts(self):
        shared = collections.defaultdict(set)
        for host, hashes in self.body_hashes.items():
            for value in hashes:
                shared[value].add(host)
        blocked = set(self.cert_mismatch)
        for value, hosts in shared.items():
            if len(hosts) > 1:
                blocked |= hosts
        return blocked


def strip_trailing(url):
    while url:
        if url[-1] in ".,;:":
            url = url[:-1]
        elif url[-1] == ")" and url.count(")") > url.count("("):
            url = url[:-1]
        else:
            break
    return url


def bibliography_urls(path):
    key = None
    for index, line in enumerate(open(path, encoding="utf-8").read().split("\n")):
        entry = BIB_ENTRY_START.match(line)
        if entry:
            key = None if entry.group(1).lower() in ("comment", "string", "preamble") \
                else entry.group(2)
            continue
        field = BIB_URL_FIELD.match(line)
        if not (field and key and field.group(2)):
            continue
        value = field.group(2)
        url = value if field.group(1).lower() == "url" else DOI_PREFIX + value
        if URL_RE.match(url):
            yield index, key, strip_trailing(url)


def list_urls(path):
    key = None
    fenced = False
    for index, line in enumerate(open(path, encoding="utf-8").read().split("\n")):
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        heading = ENTRY_HEADING.match(line)
        if heading:
            key = heading.group(1)
            continue
        field = re.match(r"^\*\*([^*:]+):\*\*\s*(.*)$", line)
        if not (field and key and field.group(1).strip() in ACCESS_FIELDS):
            continue
        for match in URL_RE.finditer(field.group(2)):
            url = strip_trailing(match.group(0))
            if url:
                yield index, key, field.group(1).strip(), url


def moving_target(url):
    wayback = WAYBACK_RE.match(url)
    if wayback and len(wayback.group(2)) < WAYBACK_PINNED:
        return "Wayback capture not pinned (timestamp is %s digits, needs %d)" % (
            len(wayback.group(2)), WAYBACK_PINNED)
    if GITHUB_FLOATING_RE.match(url):
        return "GitHub blob on a moving branch; pin to a tag or commit"
    if LATEST_DOCS_RE.search(url) and not wayback:
        return "docs path resolves to whatever is current"
    return None


def classify(url, probe, blocked_hosts):
    if registrable(probe.final or url) in blocked_hosts or (
            probe.error or "").startswith("intercepted:"):
        return "unreachable", "network intercepted; this run cannot judge this host"

    if probe.error:
        if probe.error.startswith("dns:"):
            if blocked_hosts:
                return "unreachable", "hostname did not resolve, but this run hit an interception proxy"
            return "dead", "hostname does not resolve"
        return "unreachable", probe.error

    if DOI_URL_RE.match(url):
        if not probe.chain:
            return "dead", "doi.org did not resolve this DOI (HTTP %s)" % probe.status
        if probe.status in DEAD_CODES:
            return "gated", "DOI registered; publisher landing page returned %d" % probe.status
        if probe.status in GATED_CODES:
            return "gated", "DOI registered; publisher returned %d" % probe.status
        return "ok", "DOI registered"

    if probe.status in DEAD_CODES:
        return "dead", "HTTP %d" % probe.status

    drift = moving_target(url)
    if drift:
        return "moving-target", drift

    if probe.status in GATED_CODES:
        return "gated", "HTTP %d (bot gate or paywall)" % probe.status

    if probe.status and 200 <= probe.status < 300:
        if (probe.permanent and normalize(probe.final) != normalize(url)
                and not refused_redirect(url, probe.final)):
            return "moved", "permanently redirected to %s" % probe.final
        return "ok", "HTTP %d" % probe.status

    return "unreachable", "HTTP %s" % probe.status


def normalize(url):
    url = re.sub(r"^https?://", "", (url or "").strip())
    url = re.sub(r"^www\.", "", url)
    return url.rstrip("/").lower()


def pin_wayback(url, probe):
    for _, _, location in probe.chain:
        landed = WAYBACK_RE.match(urllib.parse.urljoin(url, location))
        if landed and len(landed.group(2)) == WAYBACK_PINNED:
            original = WAYBACK_RE.match(url)
            return "%s%s%s/%s" % (landed.group(1), landed.group(2),
                                  original.group(3) or "", landed.group(4))
    return None


def cache_path(directory, url):
    return Path(directory, hashlib.sha256(url.encode("utf-8")).hexdigest()[:32] + ".json")


def cache_load(directory, url, max_age_days):
    if max_age_days is None:
        return None
    path = cache_path(directory, url)
    if not Path(path).exists():
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (ValueError, OSError):
        return None
    if payload.get("schema") != CACHE_SCHEMA:
        return None
    if time.time() - payload.get("checked", 0) > max_age_days * 86400:
        return None
    return Probe.from_dict(url, payload)


def cache_store(directory, url, probe):
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        payload = probe.as_dict()
        payload.update({"schema": CACHE_SCHEMA, "checked": time.time(), "url": url})
        with open(cache_path(directory, url), "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
    except OSError:
        pass


class Finding(object):
    __slots__ = ("source", "line", "key", "field", "url", "verdict", "detail", "repair")

    def __init__(self, source, line, key, field, url, verdict, detail, repair=None):
        self.source, self.line, self.key, self.field = source, line, key, field
        self.url, self.verdict, self.detail, self.repair = url, verdict, detail, repair


def collect(references, sources_list, bibliography_only=False):
    items = []
    if references and Path(references).exists():
        for line, key, url in bibliography_urls(references):
            items.append((references, line, key, "bibliography", url))
    if sources_list and Path(sources_list).exists() and not bibliography_only:
        for line, key, field, url in list_urls(sources_list):
            items.append((sources_list, line, key, field, url))
    return items


def run(items, fetcher, cache_dir, max_age, verbose_sink=None):
    probes = {}
    for _, _, _, _, url in items:
        if url in probes:
            continue
        cached = cache_load(cache_dir, url, max_age)
        if cached is None:
            cached = fetcher.probe(url)
            cache_store(cache_dir, url, cached)
        probes[url] = cached

    blocked = fetcher.intercepted_hosts()
    findings = []
    for source, line, key, field, url in items:
        probe = probes[url]
        verdict, detail = classify(url, probe, blocked)
        repair = None
        if verdict == "moved":
            repair = probe.final
        elif verdict == "moving-target":
            repair = pin_wayback(url, probe)
        if verbose_sink is not None:
            verbose_sink.append((key, verdict, url, detail))
        findings.append(Finding(source, line, key, field, url, verdict, detail, repair))
    return findings, probes, blocked


def add_bank_drift(findings, probes, registry_items):
    by_key = collections.defaultdict(list)
    for _, _, key, _, url in registry_items:
        by_key[key].append(url)

    for finding in findings:
        if finding.field != "bibliography" or finding.verdict not in ("dead", "moved"):
            continue
        for candidate in by_key.get(finding.key, []):
            probe = probes.get(candidate)
            if not probe or probe.error:
                continue
            if probe.status and 200 <= probe.status < 300 and \
                    normalize(candidate) != normalize(finding.url):
                finding.verdict = "bank-drift"
                finding.detail = "bibliography URL fails (%s); the list holds %s" % (
                    finding.detail, candidate)
                finding.repair = candidate
                break
    return findings


def apply_fixes(findings):
    by_file = collections.defaultdict(list)
    for finding in findings:
        if finding.repair and finding.verdict in DEFECTS:
            by_file[finding.source].append(finding)

    repaired = 0
    for path, group in by_file.items():
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().split("\n")
        for finding in group:
            if finding.url not in lines[finding.line]:
                continue
            lines[finding.line] = lines[finding.line].replace(finding.url, finding.repair)
            repaired += 1
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
    return repaired


FIXTURE_PROBES = {
    "https://doi.org/10.5555/gated.1983": Probe(
        "", status=403, final="https://dl.example.org/doi/10.5555/gated.1983",
        chain=[("https://doi.org/10.5555/gated.1983", 302, "https://dl.example.org/x")]),
    "https://doi.org/10.5555/unregistered.1986": Probe("", status=404, chain=[]),
    "https://doi.org/10.9999/registered.but.broken": Probe(
        "", status=404, final="https://publisher.example.com/gone",
        chain=[("https://doi.org/10.9999/registered.but.broken", 302,
                "https://publisher.example.com/gone")]),
    "https://www.conf.example.org/2005/village-ponds-talk": Probe("", status=404),
    "https://www.conf.example.org/legacy/2005/papers/hart.pdf": Probe("", status=200),
    "https://blog.example.com/articles/soak-rinse-sprout/": Probe(
        "", status=200, final="https://blog.example.com/soak-rinse-sprout/",
        chain=[("https://blog.example.com/articles/soak-rinse-sprout/", 301,
                "https://blog.example.com/soak-rinse-sprout/")], permanent=True),
    "https://web.archive.org/web/2020/https://papers.example.com/x.pdf": Probe(
        "", status=200,
        final="https://web.archive.org/web/20201122105532/https://papers.example.com/x.pdf",
        chain=[("https://web.archive.org/web/2020/https://papers.example.com/x.pdf", 302,
                "https://web.archive.org/web/20201122105532/https://papers.example.com/x.pdf")]),
    "https://web.archive.org/web/20201122105532id_/https://papers.example.com/x.pdf": Probe(
        "", status=200),
    "https://github.com/riverdata/riverdata/blob/main/data/levels.csv": Probe("", status=200),
    "https://dead.example.org/gone.html": Probe("", error="dns: [Errno -2] Name or service not known"),
    "https://intercepted.example.net/a": Probe(
        "", error="intercepted: certificate subject name 'proxy.test' does not match"),
}

FIXTURE_REFERENCES = """\
@article{Fry83a,
  author = {Fry, H. L.},
  title = {Notes on a Mill Race},
  year = {1983},
  doi = {10.5555/gated.1983},
}

@article{Lee86,
  author = {Lee, S.},
  title = {Plans for a Village Hall},
  year = {1986},
  doi = {10.5555/unregistered.1986},
}

@inproceedings{HKS05,
  author = {Hart, M. and Kahn, R. and Sole, C.},
  title = {A Survey of Village Ponds},
  year = {2005},
  url = {https://www.conf.example.org/2005/village-ponds-talk},
}

@misc{Wyn12,
  author = {Wynn, B. T.},
  title = {Soak, Rinse, Sprout},
  year = {2012},
  url = {https://blog.example.com/articles/soak-rinse-sprout/},
}

@misc{Col14,
  author = {Cole, J. O.},
  title = {Waste},
  year = {2014},
  url = {https://web.archive.org/web/2020/https://papers.example.com/x.pdf},
}

@misc{Riv25,
  author = {{River Data Project}},
  title = {Gauge levels},
  year = {2025},
  url = {https://github.com/riverdata/riverdata/blob/main/data/levels.csv},
}

@misc{Gon99,
  author = {Gone, A.},
  title = {Vanished},
  year = {1999},
  url = {https://dead.example.org/gone.html},
}

@article{Pub00,
  author = {Publisher, P.},
  title = {Registered But Broken},
  year = {2000},
  doi = {10.9999/registered.but.broken},
}
"""

FIXTURE_LIST = """\
### [HKS05]

**Access URLs:** https://www.conf.example.org/legacy/2005/papers/hart.pdf
**Cached original:** `sources/library/HKS05.pdf` (fetched 2025-08-09, from https://dead.example.org/gone.html)

---

### [Col14]

**Access URLs:** https://web.archive.org/web/20201122105532id_/https://papers.example.com/x.pdf (working)

---
"""


class FixtureFetcher(Fetcher):
    def __init__(self, blocked=()):
        Fetcher.__init__(self, throttle=0)
        self._blocked = set(blocked)

    def probe(self, url):
        recorded = FIXTURE_PROBES.get(url)
        if recorded is None:
            return Probe(url, status=200)
        clone = Probe(url, recorded.status, recorded.final or url, recorded.chain,
                      recorded.error, recorded.body_hash, recorded.permanent)
        if (clone.error or "").startswith("intercepted:"):
            self.cert_mismatch.add(registrable(url))
        return clone

    def intercepted_hosts(self):
        return set(self._blocked) | Fetcher.intercepted_hosts(self)


class RedirectingFetcher(Fetcher):
    def __init__(self, location):
        Fetcher.__init__(self, throttle=0)
        self.location = location

    def _once(self, url):
        self.requests += 1
        return 301, self.location, True, hashlib.sha256(b"").hexdigest()


def self_test():
    failures = []

    def require(condition, message):
        if not condition:
            failures.append(message)

    with tempfile.TemporaryDirectory() as root:
        references = Path(root, "references.bib")
        sources_list = Path(root, "list.md")
        with open(references, "w", encoding="utf-8") as handle:
            handle.write(FIXTURE_REFERENCES)
        with open(sources_list, "w", encoding="utf-8") as handle:
            handle.write(FIXTURE_LIST)
        cache = Path(root, "cache")
        items = collect(references, sources_list)
        urls = [url for _, _, _, _, url in items]
        require(sum(1 for u in urls if u == "https://dead.example.org/gone.html") == 1,
                "the provenance copy of the dead URL leaked into the check")

        findings, probes, _ = run(items, FixtureFetcher(), cache, None)
        list_items = [i for i in items if i[3] != "bibliography"]
        findings = add_bank_drift(findings, probes, list_items)
        verdicts = {(f.key, f.field): f for f in findings}
        expected = {
            "Fry83a": "gated", "Lee86": "dead", "Pub00": "gated", "HKS05": "bank-drift",
            "Wyn12": "moved", "Col14": "moving-target", "Riv25": "moving-target",
            "Gon99": "dead",
        }
        for key, verdict in expected.items():
            got = verdicts[(key, "bibliography")].verdict
            require(got == verdict, "[%s] is %s, want %s" % (key, got, verdict))
        require(verdicts[("HKS05", "bibliography")].repair ==
                "https://www.conf.example.org/legacy/2005/papers/hart.pdf",
                "bank-drift must repair from the list")
        require(verdicts[("Col14", "bibliography")].repair ==
                "https://web.archive.org/web/20201122105532/https://papers.example.com/x.pdf",
                "an unpinned Wayback URL must be pinned to the capture served")

        blocked_findings, _, _ = run(items, FixtureFetcher(blocked={"example.org"}), cache, None)
        gone = [f for f in blocked_findings if f.key == "Gon99"][0]
        require(gone.verdict == "unreachable",
                "a dead host must turn unreachable when the run was intercepted")

        repaired = apply_fixes(findings)
        require(repaired == 3, "expected 3 verified repairs, applied %d" % repaired)
        second_items = collect(references, sources_list)
        second, probes2, _ = run(second_items, FixtureFetcher(), cache, None)
        second = add_bank_drift(second, probes2,
                                [i for i in second_items if i[3] != "bibliography"])
        left = sorted({f.key for f in second if f.verdict in DEFECTS})
        require(left == ["Gon99", "Lee86", "Riv25"],
                "after --fix exactly the three unrepairable defects may remain, got %s" % left)
        require(all(f.repair is None for f in second if f.verdict in DEFECTS),
                "a defect surviving --fix must have no repair")

    for location in ("file:///etc/passwd", "ftp://files.example.org/x.pdf",
                     "http://www.example.org/paper.html"):
        fetcher = RedirectingFetcher(location)
        probe = fetcher.probe("https://www.example.org/paper.html")
        verdict, _detail = classify("https://www.example.org/paper.html", probe, set())
        require(verdict == "unreachable" and fetcher.requests == 1,
                "a redirect to %s must be unreachable and not followed, got %s"
                % (location, verdict))
    try:
        web_only_opener().open("file:///etc/hostname", timeout=1)
        failures.append("the opener read a file: address")
    except urllib.error.URLError:
        pass

    for message in failures:
        print("FAIL %s" % message)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("--bibliography", dest="references",
                        help="the .bib file (default: sources.bibliography)")
    parser.add_argument("--list", dest="sources_list", help="the sources list (default: sources.list)")
    parser.add_argument("--bibliography-only", action="store_true")
    parser.add_argument("--verbose", action="store_true", help="also list every URL that resolves")
    parser.add_argument("--fix", action="store_true",
                        help="apply redirect targets, Wayback pins and list URLs")
    parser.add_argument("--max-age", type=float, default=7,
                        help="reuse cached verdicts younger than N days (default 7)")
    parser.add_argument("--refresh", action="store_true", help="ignore the cache")
    parser.add_argument("--cache", help="verdict cache folder (default: under work.caches)")
    parser.add_argument("--timeout", type=float, default=TIMEOUT)
    parser.add_argument("--throttle", type=float, default=THROTTLE)
    parser.add_argument("--self-test", action="store_true",
                        help="only check the rules against built-in fixtures, no network")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    references = args.references or config.sources.bibliography
    sources_list = args.sources_list or config.sources.list
    cache = args.cache or os.environ.get("LINK_CHECK_CACHE") or str(tool_cache_folder(config, "link-check"))
    if args.references and not Path(references).exists():
        return tool_failed(".bib file not found: %s" % references, TOOL)
    if skipped_for_missing(TOOL, references, ".bib file", args.format):
        return 0

    items = collect(references, sources_list, args.bibliography_only)
    if not items:
        report = CheckReport(TOOL, {})
        report.skip("no URLs in the bibliography or the sources list")
        return report.emit(args.format)

    fetcher = Fetcher(throttle=args.throttle, timeout=args.timeout)
    findings, probes, blocked = run(items, fetcher, cache, None if args.refresh else args.max_age)
    findings = add_bank_drift(findings, probes, [i for i in items if i[3] != "bibliography"])

    repaired = apply_fixes(findings) if args.fix else 0
    report = CheckReport(TOOL, CLASSES)
    for finding in sorted(findings, key=lambda f: (f.verdict, f.key)):
        if finding.verdict == "ok" and not args.verbose:
            continue
        repair = (" -> %s" % finding.repair) if finding.repair else ""
        report.add(finding.key, finding.verdict,
                   "%s (%s)%s" % (finding.url, finding.detail, repair))
    if args.format == "text":
        print("checked %d distinct URLs" % len(probes))
        if blocked:
            print("%d host(s) behind an interception proxy, NOT judged: %s"
                  % (len(blocked), ", ".join(sorted(blocked))))
        if args.fix:
            print("repaired %d defect(s) with verified values" % repaired)
        print()
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
