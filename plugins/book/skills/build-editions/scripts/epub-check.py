#!/usr/bin/env python3
"""Check an EPUB with the official epubcheck.

The epubcheck release is downloaded once, its jar checked against a known sha256, and
kept in the user cache. A version from book.yaml (tools.epubcheck) must look like 5.1.0; a
version with no known sha256 is refused unless you pass --allow-unverified. Without java, or without the download, the check prints SKIPPED
and says why: a validator that reports success when it never ran is worse than none.
epubcheck errors are defects; its warnings are advisory. The build never stops on this
check: an EPUB that pandoc produced is still a file you can use.
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

from book_config import ConfigError, add_config_arguments, config_from_args
from check_output import ADVISORY, DEFECT, CheckReport, add_output_arguments, tool_failed
from output_files import newest_output_file

TOOL = "epub-check"
CLASSES = {"epubcheck-error": DEFECT, "epubcheck-warning": ADVISORY}
DEFAULT_VERSION = "5.1.0"
KNOWN_JAR_SHA256 = {"5.1.0": "e03657179297d35885336474b8c7929957e3a073b5b95c6bf8765b9408a0de9f"}
RELEASE_URL = "https://github.com/w3c/epubcheck/releases/download/v{version}/epubcheck-{version}.zip"
MESSAGE_LINE = re.compile(r"^(FATAL|ERROR|WARNING)\(([A-Z]+-\d+)\):\s*(.*)$")
SEVERITY_CLASS = {"FATAL": "epubcheck-error", "ERROR": "epubcheck-error", "WARNING": "epubcheck-warning"}
DOWNLOAD_TIMEOUT_SECONDS = 120
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


class SkipCheck(Exception):
    pass


def cache_folder():
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "book" / "build-editions"


def jar_path(version):
    return cache_folder() / f"epubcheck-{version}" / "epubcheck.jar"


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def download_epubcheck(version):
    folder = cache_folder()
    folder.mkdir(parents=True, exist_ok=True)
    archive = folder / f".epubcheck-{version}-{os.getpid()}.zip"
    url = RELEASE_URL.format(version=version)
    print(f"Fetching epubcheck {version} (one time)...", file=sys.stderr)
    try:
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            archive.write_bytes(response.read())
        with zipfile.ZipFile(archive) as unpacked:
            unpacked.extractall(folder)
    except (urllib.error.URLError, OSError, zipfile.BadZipFile) as problem:
        raise SkipCheck(f"could not download epubcheck from {url} ({problem})") from problem
    finally:
        archive.unlink(missing_ok=True)


def version_refusal(version, allow_unverified):
    if not VERSION_PATTERN.match(version):
        return (f"tools.epubcheck {version!r} is not a version like {DEFAULT_VERSION}; "
                f"fix it in book.yaml")
    if version in KNOWN_JAR_SHA256 or allow_unverified:
        return None
    return (f"epubcheck {version} has no known sha256 here, so its jar cannot be checked; "
            f"use {DEFAULT_VERSION}, or run epub-check.py --allow-unverified to trust the "
            f"download as it is")


def verified_jar(version, allow_unverified):
    refusal = version_refusal(version, allow_unverified)
    if refusal:
        raise SkipCheck(refusal)
    if version not in KNOWN_JAR_SHA256:
        print(f"Note: running epubcheck {version} without a sha256 check (--allow-unverified).",
              file=sys.stderr)
    jar = jar_path(version)
    if not jar.is_file():
        download_epubcheck(version)
    if not jar.is_file():
        raise SkipCheck(f"epubcheck.jar not found after unpacking into {jar.parent}")
    expected = KNOWN_JAR_SHA256.get(version)
    if expected and sha256_of(jar) != expected:
        raise SkipCheck(f"{jar} does not match the pinned sha256 for epubcheck {version}; delete it "
                        f"and run again")
    return jar


def messages_from(output):
    for line in output.splitlines():
        found = MESSAGE_LINE.match(line.strip())
        if found:
            yield found.group(2), SEVERITY_CLASS[found.group(1)], found.group(3)


def run_epubcheck(epub, version, allow_unverified, report):
    if not shutil.which("java"):
        raise SkipCheck("no java on PATH (epubcheck needs a Java runtime)")
    jar = verified_jar(version, allow_unverified)
    finished = subprocess.run(["java", "-jar", str(jar), str(epub)], capture_output=True, encoding="utf-8", errors="replace", check=False)
    for code, finding_class, message in messages_from(finished.stdout + finished.stderr):
        report.add(code, finding_class, message)


def configured_version(args):
    try:
        return config_from_args(args).tools.epubcheck or DEFAULT_VERSION
    except ConfigError:
        return DEFAULT_VERSION


def self_test():
    sample = ("Validating using EPUB version 3.3 rules.\n"
              "ERROR(RSC-005): book.epub/EPUB/text/ch001.xhtml(5,10): Error while parsing file\n"
              "WARNING(OPF-085): book.epub/EPUB/content.opf(2,3): dc:identifier is not valid\n"
              "Messages: 0 fatals / 1 errors / 1 warnings / 0 infos\n")
    found = list(messages_from(sample))
    checks = [
        ("an error line is a defect", found[0][:2], ("RSC-005", "epubcheck-error")),
        ("a warning line is advisory", found[1][:2], ("OPF-085", "epubcheck-warning")),
        ("summary lines are not findings", len(found), 2),
        ("the pinned version has a checksum", DEFAULT_VERSION in KNOWN_JAR_SHA256, True),
        ("the pinned version is accepted", version_refusal(DEFAULT_VERSION, False), None),
        ("a version with no checksum is refused by default",
         "--allow-unverified" in (version_refusal("5.2.1", False) or ""), True),
        ("a version with no checksum runs when the user allows it",
         version_refusal("5.2.1", True), None),
        ("a version that is a path is refused even when allowed",
         "not a version" in (version_refusal("../../tmp/evil", True) or ""), True),
        ("a version with extra text is refused",
         "not a version" in (version_refusal("5.1.0-beta", True) or ""), True),
    ]
    failures = [(name, got, expected) for name, got, expected in checks if got != expected]
    for name, got, expected in failures:
        print(f"FAIL  {name}: got {got!r}, expected {expected!r}")
    print(f"epub-check self-test: {len(checks) - len(failures)}/{len(checks)} passed")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("epub", nargs="?", help="the EPUB to check (default: the newest EPUB in the "
                                                "book's output folder)")
    parser.add_argument("--self-test", action="store_true", help="run the built-in tests; needs no java")
    parser.add_argument("--allow-unverified", action="store_true",
                        help="run an epubcheck version from book.yaml that has no known sha256 "
                             "(the jar is not checked)")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    epub = Path(args.epub) if args.epub else newest_output_file(args, ".epub")
    if args.epub and not epub.is_file():
        return tool_failed(f"no such EPUB: {epub}", TOOL)
    if not epub or not epub.is_file():
        report = CheckReport(TOOL, {})
        report.skip("no EPUB built yet: run build-editions epub first")
        return report.emit(args.format)
    report = CheckReport(TOOL, CLASSES)
    try:
        run_epubcheck(epub, configured_version(args), args.allow_unverified, report)
    except SkipCheck as reason:
        report.skip(str(reason))
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
