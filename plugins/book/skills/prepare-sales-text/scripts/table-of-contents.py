#!/usr/bin/env python3
import argparse
import html
import re
import sys
sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

import surfaces
from book_config import (KIND_BACK_MATTER, KIND_CHAPTER, KIND_FRONT_MATTER, KIND_PART,
                         KIND_REFERENCES, ConfigError, add_config_arguments, config_from_args,
                         manuscript_files)

DESCRIPTION = """Make the table of contents of the book as HTML, from the manuscript headings,
for pasting into a landing page or a store page.

DERIVED: never edit the output by hand. The HTML uses basic markup only, so the page it is
pasted into can style it: one 'toc no-parts' list, with 'section-number' spans.

What goes in:
  front matter, back matter, references  only files with a '# ' heading (title = heading)
  parts                                  '\\part{Title}' or the first '# ' heading
  chapters                               first '# ' heading; 'Chapter N: Title' gives N,
                                         otherwise N comes from the file name
  sections (--depth sections)            '## ' headings; a leading '1.2' is the number,
                                         a heading with no number (a Summary) stays unnumbered

sales_text.contents_skip in the book config lists file-name patterns to leave out.
Without --fix the HTML is printed. With --fix it is written to sales_text.contents
(chapters) or sales_text.contents_full (sections)."""

ROMAN_NUMERALS = ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
                  (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))
PART_COMMAND = re.compile(r"\\part\*?\{(.+?)\}")
TOP_HEADING = re.compile(r"^#\s+(.+?)\s*#*$")
CHAPTER_HEADING = re.compile(r"^Chapter\s+(\d+)\s*[:.]\s+(.+)$", re.I)
PART_HEADING = re.compile(r"^Part\s+[\dIVXLC]+\s*[:.]\s+(.+)$", re.I)
SECTION_HEADING = re.compile(r"^##\s+(?:(\d+(?:\.\d+)+)\s+)?(.+?)\s*#*$")


def roman(number):
    result = []
    for value, letters in ROMAN_NUMERALS:
        while number >= value:
            result.append(letters)
            number -= value
    return "".join(result)


def read_lines(path):
    return surfaces.read_text(path).splitlines()


def top_heading(lines):
    for line in lines:
        match = TOP_HEADING.match(line.strip())
        if match:
            return match.group(1)
    return None


def part_title(lines):
    for line in lines:
        match = PART_COMMAND.search(line)
        if match:
            return match.group(1)
    heading = top_heading(lines)
    if heading is None:
        return None
    match = PART_HEADING.match(heading)
    return match.group(1) if match else heading


def chapter_heading(lines, file_number):
    heading = top_heading(lines)
    if heading is None:
        return None
    match = CHAPTER_HEADING.match(heading)
    if match:
        return int(match.group(1)), match.group(2)
    return file_number, heading


def section_titles(lines):
    sections = []
    for line in lines:
        match = SECTION_HEADING.match(line.strip())
        if match:
            sections.append((match.group(1), match.group(2)))
    return sections


def build_outline(config):
    skip_patterns = surfaces.sales_text_list(config, "contents_skip")
    outline = []
    for item in manuscript_files(config):
        if surfaces.matches_any(item.path.name, skip_patterns):
            continue
        lines = read_lines(item.path)
        if item.kind in (KIND_FRONT_MATTER, KIND_BACK_MATTER, KIND_REFERENCES):
            title = top_heading(lines)
            if title:
                outline.append(("plain", title, None))
        elif item.kind == KIND_PART:
            title = part_title(lines)
            if title:
                outline.append(("part", title, None))
        elif item.kind == KIND_CHAPTER:
            found = chapter_heading(lines, item.chapter)
            if found:
                number, title = found
                outline.append(("chapter", title, (number, section_titles(lines))))
    return outline


def numbered(number, title):
    return '<span class="section-number">%s </span>%s' % (number, html.escape(title))


def render(outline, with_sections):
    lines = ['<ul class="toc no-parts">']
    part_count = 0
    part_open = False
    for kind, title, payload in outline:
        if kind in ("plain", "part") and part_open:
            lines += ["    </ul>", "  </li>"]
            part_open = False
        if kind == "plain":
            lines += ["  <li>", "    %s" % html.escape(title), "  </li>"]
        elif kind == "part":
            part_count += 1
            part_open = True
            label = "Part %s: %s" % (roman(part_count), title)
            lines += ["  <li>", "    %s" % html.escape(label), "    <ul>"]
        elif kind == "chapter":
            number, sections = payload
            label = numbered("%s." % number, title) if number is not None else html.escape(title)
            lines += ["      <li>", "        %s" % label]
            if with_sections and sections:
                lines.append("        <ul>")
                for section_number, section_title in sections:
                    entry = (numbered(section_number, section_title) if section_number
                             else html.escape(section_title))
                    lines += ["          <li>", "            %s" % entry, "          </li>"]
                lines.append("        </ul>")
            lines.append("      </li>")
    if part_open:
        lines += ["    </ul>", "  </li>"]
    lines.append("</ul>")
    return "\n".join(lines) + "\n"


def build_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--depth", choices=["chapters", "sections"], default="chapters",
                        help="chapters only (default), or chapters with their sections")
    parser.add_argument("--output", help="where --fix writes (default: sales_text.contents or "
                        "sales_text.contents_full)")
    parser.add_argument("--fix", action="store_true", help="write the HTML to the output file")
    add_config_arguments(parser)
    return parser


def main():
    arguments = build_parser().parse_args()
    try:
        config = config_from_args(arguments)
        outline = build_outline(config)
    except ConfigError as error:
        sys.stderr.write(f"table-of-contents: {error}\n")
        return 2
    if not outline:
        sys.stderr.write("table-of-contents: no headings found in the manuscript\n")
        return 2
    text = render(outline, arguments.depth == "sections")
    if arguments.fix:
        key = "contents_full" if arguments.depth == "sections" else "contents"
        target = Path(arguments.output) if arguments.output else surfaces.sales_text_path(config, key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        sys.stderr.write(f"wrote {target}\n")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
