#!/usr/bin/env python3
"""Check the tools the book plugin's skills call, and say what each missing one turns off.

Every skill runs without these tools: a check whose tool is missing prints SKIPPED and says
why. This check lists them all at once, so a new machine is set up in one pass instead of
one SKIPPED line at a time.

  docker            the build (every edition), Vale, the bibliography key check
  bash              the build script (build-book.sh); on Windows it needs WSL until the
                    build runner moves to Python
  Docker images     the images pinned in book.yaml under `tools` (pandoc, Vale, BibTeX,
                    for a paper the full TeX Live 2025 image (2.6 GB), and the cover render
                    image when one is set); --pull fetches the missing ones
  tesseract         reading scanned sources (OCR)
  poppler           pdftotext, pdftoppm, pdfinfo, pdfimages, pdffonts: text from PDF sources,
                    OCR pages, page counts, scan detection
  java              epubcheck, the EPUB validator
  curl              fetching sources
  rsvg-convert      drawing the cover (or cairosvg, or the cover render image)
  magick            cover colour and comparison checks (ImageMagick 7, or convert + compare)
  fc-match          font lookups for leading and cover text widths
  qpdf              draft PDF protection without Docker, page counts
  word list         /usr/share/dict/words, for scan detection

Classes:
  found     informational  the tool is there
  missing   informational  the tool is missing; the message says what it turns off, and
                           each check it turns off says SKIPPED itself
Exit 0 always (a missing tool is not a defect), 2 when the check itself could not run.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

LIB = Path(__file__).resolve().parents[3] / "lib"
sys.path.insert(0, str(LIB))
sys.dont_write_bytecode = True

from book_config import ConfigError, load_config
from check_output import INFORMATIONAL, CheckReport, add_output_arguments, tool_failed

TOOL = "toolchain-check"
CLASSES = {"found": INFORMATIONAL, "missing": INFORMATIONAL}
WORD_LIST = "/usr/share/dict/words"
DOCKER_TIMEOUT_SECONDS = 20
PULL_TIMEOUT_SECONDS = 1800

PROGRAMS = (
    (("docker",), "build-editions: print PDF, digital PDF and EPUB; write-text: the Vale "
                  "check; check-facts: bibliography key check against real BibTeX"),
    (("bash",), "build-editions: print PDF, digital PDF and EPUB (build-book.sh needs bash; "
                "on Windows, WSL, until the build runner moves to Python)"),
    (("tesseract",), "collect-sources: OCR of scanned sources (ocr.py)"),
    (("pdftotext",), "collect-sources: text from PDF sources (fetch.py) and scan checks"),
    (("pdftoppm",), "collect-sources: page images for OCR"),
    (("pdfinfo",), "collect-sources: OCR and scan checks; build-editions and design-cover: "
                   "page count of a PDF"),
    (("pdfimages", "pdffonts"), "collect-sources: scan detection (scan-origin-check.py)"),
    (("java",), "build-editions: epubcheck, the EPUB validator (epub-check.py)"),
    (("curl",), "collect-sources: fetching sources (fetch.py)"),
    (("rsvg-convert", "cairosvg"), "design-cover: drawing the cover, unless tools.render_image "
                                   "is set"),
    (("magick", "convert"), "design-cover: colour and comparison checks"),
    (("fc-match",), "build-editions: leading from the font's x-height; design-cover: text width "
                    "checks"),
    (("qpdf",), "build-editions: draft protection without Docker, page counts"),
)

IMAGE_USES = {
    "pandoc_image": "build-editions: every edition",
    "vale_image": "write-text: the Vale check",
    "bibtex_image": "check-facts: bibliography key check (key-bibtex-check.py)",
    "paper_tex_image": "build-editions: the paper PDF and the arXiv bundle check",
    "render_image": "design-cover: drawing the cover without a local renderer",
}

PAPER_ONLY_IMAGES = ("paper_tex_image",)


def first_found(names):
    return next((name for name in names if shutil.which(name)), None)


def docker_answers():
    if not shutil.which("docker"):
        return False, "docker not found"
    try:
        result = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"],
                                capture_output=True, encoding="utf-8", errors="replace", timeout=DOCKER_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, f"docker did not answer: {error}"
    if result.returncode != 0:
        return False, "docker is installed but its daemon did not answer (is it running?)"
    return True, f"docker {result.stdout.strip()}"


def image_present(image):
    result = subprocess.run(["docker", "image", "inspect", image], capture_output=True,
                            encoding="utf-8", errors="replace", timeout=DOCKER_TIMEOUT_SECONDS)
    return result.returncode == 0


def pull_image(image):
    result = subprocess.run(["docker", "pull", image], capture_output=True, encoding="utf-8", errors="replace",
                            timeout=PULL_TIMEOUT_SECONDS)
    return result.returncode == 0, (result.stderr or result.stdout).strip().splitlines()[-1:]


def book_images(config):
    images = []
    for key, use in IMAGE_USES.items():
        image = getattr(config.tools, key, None)
        if key in PAPER_ONLY_IMAGES and not config.is_paper:
            continue
        if image:
            images.append((key, image, use))
    return images


def check_programs(report):
    for names, disables in PROGRAMS:
        found = first_found(names)
        label = " or ".join(names)
        if found:
            report.add(label, "found", shutil.which(found))
        else:
            report.add(label, "missing", f"turns off {disables}")
    if Path(WORD_LIST).exists():
        report.add("word list", "found", WORD_LIST)
    else:
        report.add("word list", "missing", f"{WORD_LIST} not found; turns off the word-based "
                                           "part of scan detection (scan-origin-check.py)")


def check_images(report, config, pull):
    answers, detail = docker_answers()
    if not answers:
        for key, image, use in book_images(config):
            report.add(f"tools.{key}", "missing", f"{image}: not checked, {detail}; turns off {use}")
        return
    for key, image, use in book_images(config):
        if image_present(image):
            report.add(f"tools.{key}", "found", image)
            continue
        if pull:
            pulled, last_line = pull_image(image)
            if pulled:
                report.add(f"tools.{key}", "found", f"{image} (pulled now)")
                continue
            report.add(f"tools.{key}", "missing",
                       f"{image}: pull failed ({' '.join(last_line)}); turns off {use}")
            continue
        report.add(f"tools.{key}", "missing",
                   f"{image} not pulled yet (run again with --pull); the first use pulls it; "
                   f"needed for {use}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--book", metavar="DIR", help="the book folder whose book.yaml names "
                                                      "the images (default: the working folder)")
    parser.add_argument("--config", help="the book's book.yaml")
    parser.add_argument("--pull", action="store_true",
                        help="pull every pinned Docker image that is missing")
    add_output_arguments(parser)
    args = parser.parse_args(argv)
    try:
        config = load_config(config=args.config, start=args.book)
    except ConfigError as error:
        return tool_failed(str(error), TOOL)
    report = CheckReport(TOOL, CLASSES)
    check_programs(report)
    try:
        check_images(report, config, args.pull)
    except (OSError, subprocess.TimeoutExpired) as error:
        return tool_failed(f"docker failed: {error}", TOOL)
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
