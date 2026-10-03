#!/usr/bin/env python3
"""Remove pandoc's per-line wrapper markup from the code blocks inside an EPUB.

Pandoc wraps every highlighted code line in <span id="cbN-M"> opened by an empty
deep-link anchor. Kindle's converter loses the line structure of such listings, so
this strips the wrapper and keeps the syntax-highlighting spans. By default it only
counts what it would remove; --fix rewrites the EPUB in place. It refuses to guess: a wrapper it cannot close is an error, and
highlighted code with no wrapper at all is an error too, because it means pandoc
changed its output. Pass --allow-empty for a --highlight none build.
Reasons: references/editions.md, "Code blocks are flattened for Kindle".
"""

import argparse
import io
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

from book_config import add_config_arguments
from output_files import newest_output_file

LINE_ANCHOR = re.compile(r'<a href="#cb\d+-\d+" aria-hidden="true" tabindex="-1"></a>')
LINE_SPAN_OPEN = re.compile(r'<span id="cb\d+-\d+">')
HIGHLIGHTED_BLOCK = re.compile(r'<div class="sourceCode"')
BLOCK_TAIL = "</code></pre></div>"
CLOSE = "</span>"
TEXT_FOLDER = Path("EPUB", "text")
EXIT_TOOL_FAILED = 2


class MarkupShapeError(Exception):
    pass


def flatten_line(line):
    line, anchors = LINE_ANCHOR.subn("", line)
    line, opened = LINE_SPAN_OPEN.subn("", line, count=1)
    if not opened:
        return line, anchors, 0
    tail = BLOCK_TAIL if line.endswith(BLOCK_TAIL) else ""
    body = line[: len(line) - len(tail)] if tail else line
    if not body.endswith(CLOSE):
        raise MarkupShapeError("a line wrapper opened but did not close where expected: ..." + body[-70:])
    return body[: -len(CLOSE)] + tail, anchors, 1


def flatten_document(text):
    anchors = spans = 0
    lines = []
    for line in text.split("\n"):
        line, line_anchors, line_spans = flatten_line(line)
        anchors += line_anchors
        spans += line_spans
        lines.append(line)
    return "\n".join(lines), anchors, spans


def repack(workdir, destination):
    with zipfile.ZipFile(destination, "w") as archive:
        archive.write(Path(workdir) / "mimetype", "mimetype", zipfile.ZIP_STORED)
        for path in sorted(path for path in Path(workdir).rglob("*") if path.is_file()):
            arcname = path.relative_to(workdir).as_posix()
            if arcname != "mimetype":
                archive.write(path, arcname, zipfile.ZIP_DEFLATED)


def flatten_epub(epub_path, allow_empty, verbose, write):
    workdir = tempfile.mkdtemp(prefix="flatten-code-lines-")
    try:
        with zipfile.ZipFile(epub_path) as archive:
            archive.extractall(workdir)
        anchors = spans = highlighted_blocks = touched = 0
        text_dir = Path(workdir) / TEXT_FOLDER
        names = sorted(path.name for path in text_dir.iterdir()) if text_dir.is_dir() else []
        for name in (n for n in names if n.endswith(".xhtml")):
            path = text_dir / name
            original = path.read_text(encoding="utf-8")
            try:
                rewritten, file_anchors, file_spans = flatten_document(original)
            except MarkupShapeError as error:
                raise MarkupShapeError(f"{name}: {error}") from error
            highlighted_blocks += len(HIGHLIGHTED_BLOCK.findall(original))
            if rewritten != original:
                path.write_text(rewritten, encoding="utf-8")
                touched += 1
            anchors += file_anchors
            spans += file_spans
            if verbose and (file_anchors or file_spans):
                print(f"  {name}: {file_anchors} anchors, {file_spans} line wrappers")
        if highlighted_blocks and spans == 0 and not allow_empty:
            raise MarkupShapeError(
                "found highlighted code but no per-line markup to strip. Either this build ran "
                "with --highlight none (pass --allow-empty) or pandoc changed its output shape "
                "and this script no longer matches it. Not rewriting.")
        if touched and write:
            repack(workdir, epub_path)
        return spans, anchors
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def fixture_epub(chapter_xhtml):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("EPUB/text/ch001.xhtml", chapter_xhtml)
    return buffer.getvalue()


def self_test():
    wrapped = ('<div class="sourceCode" id="cb1"><pre class="sourceCode python"><code class="sourceCode python">'
               '<span id="cb1-1"><a href="#cb1-1" aria-hidden="true" tabindex="-1"></a>'
               '<span class="kw">import</span> os</span>\n'
               '<span id="cb1-2"><a href="#cb1-2" aria-hidden="true" tabindex="-1"></a>a = 1;</span>'
               '</code></pre></div>')
    flat = ('<div class="sourceCode" id="cb1"><pre class="sourceCode python"><code class="sourceCode python">'
            '<span class="kw">import</span> os\na = 1;</code></pre></div>')
    results = []
    with tempfile.TemporaryDirectory() as folder:
        epub = Path(folder) / "book.epub"
        epub.write_bytes(fixture_epub(wrapped))
        flatten_epub(str(epub), False, False, False)
        with zipfile.ZipFile(epub) as archive:
            unchanged_by_dry_run = archive.read("EPUB/text/ch001.xhtml").decode("utf-8")
        results.append(("a dry run writes nothing", unchanged_by_dry_run, wrapped))
        spans, anchors = flatten_epub(str(epub), False, False, True)
        with zipfile.ZipFile(epub) as archive:
            text = archive.read("EPUB/text/ch001.xhtml").decode("utf-8")
            first_entry = archive.namelist()[0]
        results.append(("wrappers and anchors are removed", (spans, anchors), (2, 2)))
        results.append(("syntax spans stay", text, flat))
        results.append(("mimetype stays first", first_entry, "mimetype"))
        epub.write_bytes(fixture_epub("<p>No code here.</p>"))
        results.append(("a book with no code passes", flatten_epub(str(epub), False, False, True), (0, 0)))
        epub.write_bytes(fixture_epub(flat))
        try:
            flatten_epub(str(epub), False, False, True)
            refused = False
        except MarkupShapeError:
            refused = True
        results.append(("highlighted code with no wrappers is refused", refused, True))
    failures = [(name, got, expected) for name, got, expected in results if got != expected]
    for name, got, expected in failures:
        print(f"FAIL  {name}: got {got!r}, expected {expected!r}")
    print(f"flatten-code-lines self-test: {len(results) - len(failures)}/{len(results)} passed")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    parser.add_argument("epub", nargs="?", help="the EPUB to flatten (default: the newest EPUB in the "
                                                "book's output folder)")
    parser.add_argument("--fix", action="store_true", help="rewrite the EPUB in place; without it nothing is written")
    parser.add_argument("--allow-empty", action="store_true",
                        help="accept finding nothing to strip; pass this for a --highlight none build")
    parser.add_argument("--verbose", action="store_true", help="name each file and its counts")
    parser.add_argument("--self-test", action="store_true", help="run the built-in tests on a made-up EPUB")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    epub_path = args.epub or newest_output_file(args, ".epub")
    if not epub_path or not Path(epub_path).is_file():
        sys.stderr.write(f"flatten-code-lines: no such EPUB: {epub_path or '(none found in the output folder)'}\n")
        return EXIT_TOOL_FAILED
    try:
        spans, anchors = flatten_epub(str(epub_path), args.allow_empty, args.verbose, args.fix)
    except (MarkupShapeError, zipfile.BadZipFile, OSError) as problem:
        sys.stderr.write(f"flatten-code-lines: {problem}\n")
        return EXIT_TOOL_FAILED
    if args.fix:
        print(f"  Flattened {spans} code lines, removed {anchors} empty anchors.")
    else:
        print(f"  Would flatten {spans} code lines and remove {anchors} empty anchors (dry run; --fix writes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
