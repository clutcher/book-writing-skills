#!/usr/bin/env python3
import argparse
import copy
import fnmatch
import json
import re
import shlex
import sys
sys.dont_write_bytecode = True
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_FILE_NAMES = ("book.yaml", "book.yml", "book.json")
FALLBACK_FILE_NAME = "CLAUDE.md"
METADATA_HEADING = "## Book Metadata"
TERMS_HEADING = "## Coined Terminology"
TERM_FAMILIES_HEADING = "### Term Families"
LEGAL_COMPOUNDS_HEADING = "### Legal Compounds"
OLD_LAYOUT_MARKER = Path("review") / "sources-registry.md"

LAYOUT_NEW = "new"
LAYOUT_PREVIOUS = "previous"
LAYOUT_OLD = "old"
LAYOUTS = (LAYOUT_NEW, LAYOUT_PREVIOUS, LAYOUT_OLD)
LAYOUT_KEY = "layout"
NEW_LAYOUT_SIGNS = ("thinking", "rules", "notes", "publishing")
PREVIOUS_LAYOUT_SIGNS = ("decisions.md", "vocabulary", "reading-notes", "reasons", "author",
                         "style", "marketing", "sources/files", "sources/origin")

SOURCE_CLI = "command line"
SOURCE_CONFIG_FILE = "config file"
SOURCE_FALLBACK = "CLAUDE.md"
SOURCE_DEFAULTS = "defaults"

KIND_FRONT_MATTER = "front-matter"
KIND_PART = "part"
KIND_CHAPTER = "chapter"
KIND_REFERENCES = "references"
KIND_BACK_MATTER = "back-matter"
KIND_OTHER = "other"
MANUSCRIPT_KINDS = (KIND_FRONT_MATTER, KIND_PART, KIND_CHAPTER, KIND_REFERENCES,
                    KIND_BACK_MATTER, KIND_OTHER)

CHAPTER_PATTERN = r"(?:^|-)chapter-(\d+)\.md$"
PART_PATTERN = r"^(\d+-)?part-[\w-]+\.md$"

BIBTEX_IMAGE = ("blang/latex:ubuntu@sha256:"
                "2c32abc3555a01e180528d542955e2730f7f3793cdeba49b1655de9b897cbafb")
GLOSSARY_HEADING_SEPARATOR = " -- "
GLOSSARY_LOCATION_PATTERN = r"^(?:Ch(?:apter)?\.?\s*(?P<chapter>\d+)\b|(?P<file>[A-Za-z][\w-]*))"

BOOK_KEYS = frozenset((
    "title", "subtitle", "author", "language", "accessibility_summary", "description",
    "publication_date", "publisher", "subjects", "epub_identifier",
    "format", "layout", "pages", "font", "italic_font", "heading_font", "font_size", "leading",
    "heading_scale", "code_scale", "inline_code_scale", "chapter_style", "section_style",
    "ornament", "quote_style", "page_style", "page_ornament", "page_ornament_size",
    "all_page_folios", "highlight", "top_level", "toc_depth", "toc", "numbered",
    "pattern", "exclude", "part_pages", "part_overview",
    "cover_front", "cover_back", "ebook_cover",
    "hyphenation_language", "placeholder_text", "latex_commands_to_drop", "language_codes",
    "heading_types", "chapter_heading_word", "front_matter_pages", "copyright_markers",
    "emblem_alt", "references_heading",
))

SHARED_DEFAULTS = {
    "version": 1,
    "book": {"language": "en-US", "accessibility_summary": None, "format": "6x9"},
    "manuscript": {
        "dir": "manuscript",
        "order": "natural",
        "files": [],
        "chapter_pattern": CHAPTER_PATTERN,
        "part_pattern": PART_PATTERN,
        "front_matter": ["0[0-9][0-9]-*.md"],
        "back_matter": ["9[0-9][0-9]-*.md"],
        "references": "manuscript/900-references.md",
        "summary_heading": "Summary",
    },
    "terms": {"families": [], "compounds": [], "watch_words": {}},
    "glossary_format": {
        "heading_separator": GLOSSARY_HEADING_SEPARATOR,
        "location_pattern": GLOSSARY_LOCATION_PATTERN,
    },
    "sources": {"backup": None, "citation_style": "alpha"},
    "cover": {
        "trim": None,
        "paper": "bw-white",
        "book_pdf": None,
        "output": None,
        "templates": None,
        "shelf_screenshots": None,
        "cmyk_limit": 88,
        "icc": None,
        "srgb_profile": None,
    },
    "sales_text": {
        "amazon": None,
        "keywords": None,
        "intended_impression": None,
        "plain_description": None,
        "contents": None,
        "contents_full": None,
        "preface": None,
        "retired_phrases": [],
        "shared_spans": [],
        "contents_skip": [],
        "amazon_limit": 4000,
        "keyword_slots": 7,
        "keyword_chars": 50,
        "categories_per_format": 3,
        "sample_print_share": 0.2,
        "sample_ebook_share": 0.1,
    },
    "readers_review": {
        "room": None,
        "sources_for_reviewer": None,
        "main_metaphor": None,
        "key_sources": [],
        "research_field": None,
        "similar_books": [],
        "author_background": None,
        "audience": None,
        "lens_batch": 3,
        "skeptic_batch": 2,
        "skills_off": [],
        "plugin_id": None,
        "lenses": [],
    },
    "writing": {
        "sentence_min_words": None,
        "sentence_max_words": None,
        "sentence_review_below": None,
        "sentence_review_above": None,
        "sentence_target_share": None,
        "paragraph_min_sentences": None,
        "paragraph_max_sentences": None,
        "inversion_gap_words": None,
        "inversion_min_paragraph_gap": None,
        "inversions_per_section": None,
        "paragraph_length_exempt": [],
        "term_phases": None,
        "words_per_page": None,
    },
    "tools": {
        "pandoc_image": "pandoc/extra:3.8.3",
        "pandoc_volume": "book-to-pdf-texlive",
        "vale_image": "jdkato/vale:v3.14.2",
        "bibtex_image": BIBTEX_IMAGE,
        "render_image": None,
        "epubcheck": "5.1.0",
    },
}

NEW_LAYOUT_DEFAULTS = {
    "thinking": {
        "dir": "thinking",
        "stance": "thinking/author/stance.md",
        "stance_details": "thinking/author/stance-details.md",
        "audience": "thinking/author/audience.md",
        "argument": "thinking/argument",
        "doubts": "thinking/doubts",
    },
    "rules": {
        "dir": "rules",
        "decisions": "rules/decisions.md",
        "glossary": "rules/glossary.md",
        "voice": "rules/voice.md",
        "vale": "rules/vale",
        "vale_ini": "rules/vale/vale.ini",
    },
    "sources": {
        "list": "sources/list.md",
        "quotes": "sources/quotes.md",
        "library": "sources/library",
        "library_index": "sources/library-index",
        "to_add": None,
    },
    "notes": "notes",
    "publishing": {"cover": "publishing/cover", "sales_text": "publishing/sales-text"},
    "work": {"dir": ".book", "runs": None, "output": None, "caches": None},
    "cover": {"design": None, "final": None},
    "sales_text": {"back_cover": None},
}

PREVIOUS_LAYOUT_DEFAULTS = {
    "thinking": {
        "dir": None,
        "stance": "author/stance.md",
        "stance_details": "author/stance-details.md",
        "audience": "author/positioning.md",
        "argument": "reasons",
        "doubts": None,
    },
    "rules": {
        "dir": None,
        "decisions": "decisions.md",
        "glossary": "vocabulary/glossary.md",
        "voice": "author/voice.md",
        "vale": "style",
        "vale_ini": "style/vale.ini",
    },
    "sources": {
        "list": "sources/list.md",
        "quotes": "sources/quotes.md",
        "library": "sources/files",
        "library_index": "sources/origin",
        "to_add": None,
    },
    "notes": "reading-notes",
    "publishing": {"cover": "cover", "sales_text": "marketing"},
    "work": {"dir": ".book", "runs": None, "output": None, "caches": None},
    "cover": {"design": None, "final": None},
    "sales_text": {"back_cover": None},
}

OLD_LAYOUT_DEFAULTS = {
    "thinking": {
        "dir": None,
        "stance": "my-stance.md",
        "stance_details": "my-stance-details.md",
        "audience": "book-positioning.md",
        "argument": "research",
        "doubts": None,
    },
    "rules": {
        "dir": None,
        "decisions": "decisions.md",
        "glossary": "review/glossary-registry.md",
        "voice": None,
        "vale": ".vale",
        "vale_ini": ".vale.ini",
    },
    "sources": {
        "list": "review/sources-registry.md",
        "quotes": "review/fact-check-findings-registry.md",
        "library": "review/sources",
        "library_index": "review/sources",
        "to_add": "review/sources/incoming",
    },
    "notes": "personal-review",
    "publishing": {"cover": "cover", "sales_text": "cover"},
    "work": {"dir": ".", "runs": "review", "output": "output", "caches": "."},
    "cover": {"design": None, "final": "cover"},
    "sales_text": {"back_cover": None},
}

LAYOUT_DEFAULTS = {
    LAYOUT_NEW: NEW_LAYOUT_DEFAULTS,
    LAYOUT_PREVIOUS: PREVIOUS_LAYOUT_DEFAULTS,
    LAYOUT_OLD: OLD_LAYOUT_DEFAULTS,
}

KEY_ALIASES = {
    "decisions": "rules.decisions",
    "vocabulary.glossary": "rules.glossary",
    "reading_notes": "notes",
    "reasons": "thinking.argument",
    "author.stance": "thinking.stance",
    "author.stance_details": "thinking.stance_details",
    "author.positioning": "thinking.audience",
    "author.voice": "rules.voice",
    "style.dir": "rules.vale",
    "style.vale_ini": "rules.vale_ini",
    "sources.files": "sources.library",
    "sources.origin": "sources.library_index",
    "cover.dir": "publishing.cover",
    "marketing.dir": "publishing.sales_text",
    "sales_text.google_books": "sales_text.plain_description",
}
SECTION_ALIASES = {"marketing": "sales_text", "outside_review": "readers_review",
                   "vocabulary": "glossary_format"}
RETIRED_KEYS = {
    "work.inbox": "staged entries go inside the run folder of the run that made them",
    "sources.incoming": "files added by hand go to sources.to_add",
    "rules.accepted_flags": "no check reads accepted counts any more: every finding is "
                            "reported until it is fixed",
}
ACCEPTED_COUNTS_KEY = "rules.accepted_flags"
ACCEPTED_COUNTS_FILE = "accepted-flags.json"
OLD_ACCEPTED_COUNTS_FILE = Path("baselines") / "sources.json"

SALES_TEXT_FILE_NAMES = {
    LAYOUT_NEW: {
        "back_cover": "back-cover.md",
        "amazon": "amazon.html",
        "keywords": "keywords-and-categories.md",
        "intended_impression": "intended-impression.md",
        "plain_description": "plain-description.txt",
        "contents": "contents.html",
        "contents_full": "contents-full.html",
    },
    LAYOUT_OLD: {
        "amazon": "kdp-description.html",
        "plain_description": "plain-description.txt",
        "contents": "contents.html",
        "contents_full": "contents-full.html",
    },
}
OLD_SALES_TEXT_FILE_NAMES = {
    "plain_description": ("google-books.txt", "google-books-description.txt"),
}
SALES_TEXT_FILE_NAMES[LAYOUT_PREVIOUS] = SALES_TEXT_FILE_NAMES[LAYOUT_NEW]
COVER_FILE_NAMES = {
    LAYOUT_NEW: {"design": "design.py", "final": "final"},
    LAYOUT_PREVIOUS: {"design": "design.py", "final": "final"},
    LAYOUT_OLD: {"final": "."},
}
SHIPPED_COVER_FILES = {"cover_front": "front.png", "cover_back": "back.png",
                       "ebook_cover": "ebook.png"}
SALES_TEXT_FILES = ("amazon", "keywords", "intended_impression", "plain_description", "contents",
                    "contents_full", "preface")

COVER_OUTPUT_FOLDER = "cover"
COVER_TEMPLATES_FOLDER = "kdp-templates"
COVER_SHELF_FOLDER = "shelf-screenshots"
SOURCES_TO_ADD_FOLDER = "sources-to-add"
SOURCES_FOR_REVIEWER_FILE = "sources-for-reviewer.md"
READERS_REVIEW_ROOM_SUFFIX = "-readers-review"
OLD_READERS_REVIEW_ROOM_SUFFIX = "-outside-review"

THINKING_FILES = ("dir", "stance", "stance_details", "audience", "argument", "doubts")
RULES_FILES = ("dir", "decisions", "glossary", "voice", "vale", "vale_ini")
WORK_SUBFOLDERS = ("runs", "output", "caches")

PATH_KEYS = (
    "manuscript.dir", "manuscript.references",
    *(f"thinking.{name}" for name in THINKING_FILES),
    *(f"rules.{name}" for name in RULES_FILES),
    "sources.list", "sources.quotes", "sources.library", "sources.library_index",
    "sources.backup", "sources.to_add",
    "notes",
    "publishing.cover", "publishing.sales_text",
    "work.dir", *(f"work.{name}" for name in WORK_SUBFOLDERS),
    "cover.design", "cover.final", "cover.book_pdf", "cover.output",
    "cover.templates", "cover.shelf_screenshots", "cover.icc", "cover.srgb_profile",
    "sales_text.back_cover",
    *(f"sales_text.{name}" for name in SALES_TEXT_FILES),
    "readers_review.room", "readers_review.sources_for_reviewer",
)

TOOL_KEYS = ("pandoc_image", "pandoc_volume", "vale_image", "bibtex_image", "render_image",
             "epubcheck")

METADATA_PATH_KEYS = ("cover_front", "cover_back", "ebook_cover")

METADATA_KEYS_WITH_OWN_HOME = {
    "manuscript": "manuscript.dir",
    "output": "work.output",
}


_MISSING = object()


class ConfigError(Exception):
    pass


_NUMBER_INT = re.compile(r"^[-+]?\d+$")
_NUMBER_FLOAT = re.compile(r"^[-+]?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?$")
_BLOCK_STRING = re.compile(r"^([|>])([-+]?)$")
_ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "/": "/", "0": "\0", "r": "\r"}


@dataclass
class _Line:
    number: int
    indent: int
    text: str


def read_yaml_subset(text):
    raw_lines = text.replace("\r\n", "\n").split("\n")
    reader = _YamlReader(raw_lines)
    return reader.document()


class _YamlReader:
    def __init__(self, raw_lines):
        self.raw_lines = raw_lines
        self.lines = []
        for number, raw in enumerate(raw_lines, 1):
            if "\t" in raw[: len(raw) - len(raw.lstrip())]:
                raise ConfigError(f"line {number}: tab used for indentation")
            content = _strip_comment(raw).rstrip()
            if not content.strip():
                continue
            if content.strip() == "---" and not self.lines:
                continue
            if content.strip() in ("---", "..."):
                raise ConfigError(f"line {number}: several documents in one file "
                                  f"are not supported")
            self.lines.append(_Line(number, len(content) - len(content.lstrip()),
                                    content.strip()))
        self.position = 0

    def document(self):
        if not self.lines:
            return {}
        value = self.block(self.lines[0].indent)
        if self.position < len(self.lines):
            line = self.lines[self.position]
            raise ConfigError(f"line {line.number}: unexpected indentation")
        return value

    def block(self, indent):
        line = self.lines[self.position]
        if _is_list_item(line.text):
            return self.sequence(indent)
        return self.mapping(indent)

    def mapping(self, indent):
        result = {}
        while self.position < len(self.lines):
            line = self.lines[self.position]
            if line.indent < indent:
                break
            if line.indent > indent:
                raise ConfigError(f"line {line.number}: unexpected indentation")
            if _is_list_item(line.text):
                raise ConfigError(f"line {line.number}: a list item where a key was expected")
            key, rest = _split_key(line)
            if key in result:
                raise ConfigError(f"line {line.number}: key {key!r} appears twice")
            self.position += 1
            result[key] = self.value_after_key(rest, indent, line)
        return result

    def sequence(self, indent):
        result = []
        while self.position < len(self.lines):
            line = self.lines[self.position]
            if line.indent < indent or not _is_list_item(line.text):
                if line.indent > indent:
                    raise ConfigError(f"line {line.number}: unexpected indentation")
                break
            if line.indent > indent:
                raise ConfigError(f"line {line.number}: unexpected indentation")
            rest = line.text[1:]
            item_text = rest.lstrip()
            if not item_text:
                self.position += 1
                result.append(self.nested_or_none(indent, line, allow_same_indent_list=False))
                continue
            item_indent = indent + 1 + (len(rest) - len(item_text))
            self.lines[self.position] = _Line(line.number, item_indent, item_text)
            if _is_list_item(item_text) or _looks_like_key(item_text):
                result.append(self.block(item_indent))
            else:
                self.position += 1
                result.append(self.scalar_or_block_string(item_text, indent, line))
        return result

    def value_after_key(self, rest, indent, line):
        if rest:
            return self.scalar_or_block_string(rest, indent, line)
        return self.nested_or_none(indent, line, allow_same_indent_list=True)

    def nested_or_none(self, indent, line, allow_same_indent_list):
        if self.position >= len(self.lines):
            return None
        following = self.lines[self.position]
        if following.indent > indent:
            return self.block(following.indent)
        if (allow_same_indent_list and following.indent == indent
                and _is_list_item(following.text)):
            return self.sequence(indent)
        return None

    def scalar_or_block_string(self, text, indent, line):
        block = _BLOCK_STRING.match(text)
        if block:
            return self.block_string(block.group(1), block.group(2), indent, line)
        return parse_scalar(text, line.number)

    def block_string(self, style, chomping, indent, line):
        start = line.number
        collected = []
        index = start
        while index < len(self.raw_lines):
            raw = self.raw_lines[index]
            if raw.strip() and len(raw) - len(raw.lstrip()) <= indent:
                break
            collected.append(raw)
            index += 1
        while self.position < len(self.lines) and self.lines[self.position].number <= index:
            self.position += 1
        content_lines = [raw for raw in collected if raw.strip()]
        if not content_lines:
            return ""
        margin = min(len(raw) - len(raw.lstrip()) for raw in content_lines)
        body = [raw[margin:] if raw.strip() else "" for raw in collected]
        trailing_blank = 0
        while body and body[-1] == "":
            body.pop()
            trailing_blank += 1
        if style == "|":
            joined = "\n".join(body)
        else:
            joined = _fold(body)
        if chomping == "-":
            return joined
        if chomping == "+":
            return joined + "\n" * (1 + trailing_blank)
        return joined + "\n"


def _fold(lines):
    paragraphs, current = [], []
    for line in lines:
        if line == "":
            paragraphs.append(" ".join(current))
            current = []
        else:
            current.append(line)
    paragraphs.append(" ".join(current))
    return "\n".join(paragraphs)


def _is_list_item(text):
    return text == "-" or text.startswith("- ")


def _looks_like_key(text):
    try:
        _split_key(_Line(0, 0, text))
    except ConfigError:
        return False
    return not text.startswith(("[", "{"))


def _split_key(line):
    text = line.text
    if text.startswith(("'", '"')):
        end = _closing_quote(text, 0)
        if end is None:
            raise ConfigError(f"line {line.number}: unclosed quote in key")
        key = parse_scalar(text[: end + 1], line.number)
        rest = text[end + 1:]
        if not rest.startswith(":"):
            raise ConfigError(f"line {line.number}: expected ':' after the key")
        return str(key), rest[1:].strip()
    found = re.match(r"^([^:#\[\]{},]+?)\s*:(?:\s+(.*)|$)", text)
    if not found:
        raise ConfigError(f"line {line.number}: expected 'key: value', got {text!r}")
    return found.group(1).strip(), (found.group(2) or "").strip()


def _closing_quote(text, start):
    quote = text[start]
    index = start + 1
    while index < len(text):
        character = text[index]
        if quote == '"' and character == "\\":
            index += 2
            continue
        if character == quote:
            if quote == "'" and index + 1 < len(text) and text[index + 1] == "'":
                index += 2
                continue
            return index
        index += 1
    return None


def _strip_comment(raw):
    index = 0
    while index < len(raw):
        character = raw[index]
        if character in ("'", '"') and (index == 0 or raw[index - 1] in " \t[{,:-"):
            end = _closing_quote(raw, index)
            if end is None:
                return raw
            index = end + 1
            continue
        if character == "#" and (index == 0 or raw[index - 1] in " \t"):
            return raw[:index]
        index += 1
    return raw


def parse_scalar(text, line_number=0):
    text = text.strip()
    if text.startswith(("[", "{")):
        value, end = _parse_flow(text, 0, line_number)
        if text[end:].strip():
            raise ConfigError(f"line {line_number}: text after an inline collection; "
                              f"inline collections must fit on one line")
        return value
    if text.startswith(('"', "'")):
        end = _closing_quote(text, 0)
        if end is None or text[end + 1:].strip():
            raise ConfigError(f"line {line_number}: badly quoted string {text!r}")
        return _unquote(text[: end + 1], line_number)
    if text[:1] in ("&", "*", "!", "%", "@", "`"):
        raise ConfigError(f"line {line_number}: {text[:1]!r} starts an anchor, alias, tag "
                          f"or reserved form, which this reader does not support; quote it")
    return _plain_scalar(text)


def _plain_scalar(text):
    if text in ("", "~", "null", "Null", "NULL"):
        return None
    if text in ("true", "True", "TRUE"):
        return True
    if text in ("false", "False", "FALSE"):
        return False
    if _NUMBER_INT.match(text):
        return int(text)
    if _NUMBER_FLOAT.match(text):
        return float(text)
    return text


def _unquote(text, line_number):
    body = text[1:-1]
    if text[0] == "'":
        return body.replace("''", "'")
    result, index = [], 0
    while index < len(body):
        character = body[index]
        if character != "\\":
            result.append(character)
            index += 1
            continue
        code = body[index + 1: index + 2]
        if code == "u":
            digits = body[index + 2: index + 6]
            if not re.fullmatch(r"[0-9a-fA-F]{4}", digits):
                raise ConfigError(f"line {line_number}: bad \\u escape")
            result.append(chr(int(digits, 16)))
            index += 6
            continue
        if code not in _ESCAPES:
            raise ConfigError(f"line {line_number}: unknown escape \\{code}")
        result.append(_ESCAPES[code])
        index += 2
    return "".join(result)


def _parse_flow(text, index, line_number):
    opener = text[index]
    closer = "]" if opener == "[" else "}"
    items = [] if opener == "[" else {}
    index += 1
    while True:
        index = _skip_spaces(text, index)
        if index >= len(text):
            raise ConfigError(f"line {line_number}: inline collection not closed on its line")
        if text[index] == closer:
            return items, index + 1
        if opener == "[":
            value, index = _parse_flow_value(text, index, line_number, ",]")
            items.append(value)
        else:
            key, index = _parse_flow_value(text, index, line_number, ":")
            index = _skip_spaces(text, index)
            if index >= len(text) or text[index] != ":":
                raise ConfigError(f"line {line_number}: expected ':' in inline mapping")
            value, index = _parse_flow_value(text, index + 1, line_number, ",}")
            items[str(key)] = value
        index = _skip_spaces(text, index)
        if index < len(text) and text[index] == ",":
            index += 1
        elif index < len(text) and text[index] == closer:
            continue
        else:
            raise ConfigError(f"line {line_number}: expected ',' or {closer!r} in inline "
                              f"collection")


def _parse_flow_value(text, index, line_number, stops):
    index = _skip_spaces(text, index)
    if index < len(text) and text[index] in "[{":
        return _parse_flow(text, index, line_number)
    if index < len(text) and text[index] in "'\"":
        end = _closing_quote(text, index)
        if end is None:
            raise ConfigError(f"line {line_number}: unclosed quote")
        return _unquote(text[index: end + 1], line_number), end + 1
    start = index
    while index < len(text) and text[index] not in stops:
        if text[index] == ":" and ":" not in stops:
            break
        index += 1
    return parse_scalar(text[start:index].strip(), line_number), index


def _skip_spaces(text, index):
    while index < len(text) and text[index] in " \t":
        index += 1
    return index


def normalise_metadata_key(name):
    return re.sub(r"[\s-]+", "_", name.strip()).lower()


def read_metadata_section(text):
    metadata = {}
    inside = False
    for line in text.split("\n"):
        if line.rstrip() == METADATA_HEADING:
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if not inside:
            continue
        found = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):[ \t]*(.*)$", line)
        if not found:
            continue
        key = normalise_metadata_key(found.group(1))
        value = re.sub(r"\s+#.*$", "", found.group(2)).strip().rstrip("\r")
        metadata.setdefault(key, value)
    return metadata


def _table_rows_after(lines, heading):
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        return []
    index = start + 1
    while index < len(lines) and not _is_table_row(lines[index]):
        if lines[index].strip().startswith("#"):
            return []
        index += 1
    table = []
    while index < len(lines) and _is_table_row(lines[index]):
        table.append(lines[index])
        index += 1
    rows = []
    for position, raw in enumerate(table):
        if position == 0 or re.fullmatch(r"\|[\s|:-]+\|", raw.strip()):
            continue
        rows.append([cell.strip() for cell in raw.strip().strip("|").split("|")])
    return rows


def _is_table_row(line):
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def read_terms_section(text):
    lines = text.split("\n")
    families = []
    for cells in _table_rows_after(lines, TERM_FAMILIES_HEADING):
        if len(cells) < 2 or not cells[0]:
            continue
        also = cells[2] if len(cells) > 2 else ""
        families.append({
            "term": cells[0],
            "role": cells[1].lower(),
            "also": [word for word in re.split(r"[,\s]+", also) if word],
        })
    compounds = [cells[0].strip().lower()
                 for cells in _table_rows_after(lines, LEGAL_COMPOUNDS_HEADING)
                 if cells and cells[0].strip()]
    return {"families": families, "compounds": compounds}


def settings_from_fallback_file(path):
    text = Path(path).read_text(encoding="utf-8")
    settings = {}
    metadata = read_metadata_section(text)
    for metadata_key, dotted_key in METADATA_KEYS_WITH_OWN_HOME.items():
        if metadata.get(metadata_key):
            _set_dotted(settings, dotted_key, metadata.pop(metadata_key))
    if metadata:
        settings["book"] = metadata
    if TERMS_HEADING in text.split("\n") or TERM_FAMILIES_HEADING in text:
        terms = read_terms_section(text)
        if terms["families"] or terms["compounds"]:
            settings["terms"] = terms
    return settings


def has_fallback_sections(path):
    try:
        lines = Path(path).read_text(encoding="utf-8").split("\n")
    except OSError:
        return False
    stripped = {line.rstrip() for line in lines}
    return METADATA_HEADING in stripped or TERMS_HEADING in stripped


def find_config_file(start=None):
    for folder in _folders_upwards(start):
        for name in CONFIG_FILE_NAMES:
            candidate = folder / name
            if candidate.is_file():
                return candidate
    return None


def find_fallback_file(start=None):
    for folder in _folders_upwards(start):
        candidate = folder / FALLBACK_FILE_NAME
        if candidate.is_file() and has_fallback_sections(candidate):
            return candidate
    return None


def _folders_upwards(start):
    folder = Path(start or Path.cwd()).resolve()
    if folder.is_file():
        folder = folder.parent
    yield folder
    yield from folder.parents


def read_config_file(path):
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigError(f"{path}: {error.strerror}") from error
    try:
        if path.suffix == ".json":
            data = json.loads(text) if text.strip() else {}
        else:
            data = read_yaml_subset(text)
    except json.JSONDecodeError as error:
        raise ConfigError(f"{path}: line {error.lineno}: {error.msg}") from error
    except ConfigError as error:
        raise ConfigError(f"{path}: {error}") from error
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: the top level must be a mapping")
    return data


def _merge(base, layer):
    merged = copy.deepcopy(base)
    for key, value in layer.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _normalise_shapes(settings):
    shaped = copy.deepcopy(settings)
    if isinstance(shaped.get("work"), str):
        shaped["work"] = {"dir": shaped["work"], **{name: None for name in WORK_SUBFOLDERS}}
    if isinstance(shaped.get("book"), dict):
        shaped["book"] = {normalise_metadata_key(key): value
                          for key, value in shaped["book"].items()}
    for family in (shaped.get("terms") or {}).get("families") or []:
        if isinstance(family, dict) and isinstance(family.get("also"), str):
            family["also"] = [word for word in re.split(r"[,\s]+", family["also"]) if word]
    return shaped


def _set_dotted(settings, dotted_key, value):
    parts = dotted_key.split(".")
    node = settings
    for part in parts[:-1]:
        if not isinstance(node.get(part), dict):
            node[part] = {}
        node = node[part]
    node[parts[-1]] = value


def _get_dotted(settings, dotted_key):
    node = settings
    for part in dotted_key.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(dotted_key)
        node = node[part]
    return node


def canonical_key(dotted_key):
    if dotted_key in KEY_ALIASES:
        return KEY_ALIASES[dotted_key]
    section, _, rest = dotted_key.partition(".")
    if rest and section in SECTION_ALIASES:
        renamed = f"{SECTION_ALIASES[section]}.{rest}"
        return KEY_ALIASES.get(renamed, renamed)
    return dotted_key


def old_key_names(settings):
    found = []
    for key, value in settings.items():
        if key in KEY_ALIASES:
            found.append(key)
        elif isinstance(value, dict):
            found.extend(f"{key}.{name}" for name in value
                         if f"{key}.{name}" in KEY_ALIASES or key in SECTION_ALIASES)
    return found


def retired_key_names(settings):
    return [key for key in RETIRED_KEYS if _has_dotted(settings, key)]


def with_new_key_names(settings):
    renamed = copy.deepcopy(settings)
    for key in retired_key_names(renamed):
        _pop_dotted(renamed, key)
    for old_key in old_key_names(renamed):
        value = _pop_dotted(renamed, old_key)
        new_key = canonical_key(old_key)
        if not _has_dotted(renamed, new_key):
            _set_dotted(renamed, new_key, value)
    return renamed


def _has_dotted(settings, dotted_key):
    try:
        _get_dotted(settings, dotted_key)
    except KeyError:
        return False
    return True


def _pop_dotted(settings, dotted_key):
    parts = dotted_key.split(".")
    parents = [settings]
    for part in parts[:-1]:
        parents.append(parents[-1][part])
    value = parents[-1].pop(parts[-1])
    for depth in range(len(parts) - 1, 0, -1):
        if parents[depth] == {}:
            parents[depth - 1].pop(parts[depth - 1])
    return value


def parse_override(text):
    if "=" not in text:
        raise ConfigError(f"--set expects KEY=VALUE, got {text!r}")
    key, value = text.split("=", 1)
    key = key.strip()
    if key.startswith("book."):
        key = "book." + normalise_metadata_key(key[len("book."):])
    return canonical_key(key), parse_scalar(value) if value.strip() else None


def _known_keys(tree, prefix=""):
    keys = set()
    for key, value in tree.items():
        dotted = f"{prefix}{key}"
        keys.add(dotted)
        if isinstance(value, dict) and key not in ("book", "watch_words"):
            keys |= _known_keys(value, dotted + ".")
    return keys


ALL_KNOWN_KEYS = frozenset(
    {LAYOUT_KEY}.union(*(_known_keys(_merge(SHARED_DEFAULTS, defaults))
                         for defaults in LAYOUT_DEFAULTS.values())))


def unknown_keys(settings, prefix=""):
    if not prefix:
        settings = with_new_key_names(settings)
    found = []
    for key, value in settings.items():
        dotted = f"{prefix}{key}"
        if dotted not in ALL_KNOWN_KEYS:
            found.append(dotted)
            continue
        if dotted == "book" and isinstance(value, dict):
            found.extend(f"book.{name}" for name in value
                         if normalise_metadata_key(str(name)) not in BOOK_KEYS)
        elif isinstance(value, dict) and key != "watch_words" and dotted != "work":
            found.extend(unknown_keys(value, dotted + "."))
    return found


def layout_default(layout, dotted_key):
    return _get_dotted(_merge(SHARED_DEFAULTS, LAYOUT_DEFAULTS[layout]),
                       canonical_key(dotted_key))


@dataclass
class TermFamily:
    term: str
    role: str
    also: list = field(default_factory=list)


@dataclass
class Terms:
    families: list
    compounds: list
    watch_words: dict

    def family(self, term):
        return next((family for family in self.families
                     if family.term.lower() == term.lower()), None)

    def roles(self, role):
        return [family for family in self.families if family.role == role]


@dataclass
class BookMetadata:
    values: dict
    root: Path

    def get(self, name, default=None):
        value = self.values.get(normalise_metadata_key(name))
        return default if value is None or value == "" else value

    def path(self, name):
        value = self.get(name)
        return _resolve(self.root, value)

    @property
    def title(self):
        return self.get("title")

    @property
    def subtitle(self):
        return self.get("subtitle")

    @property
    def author(self):
        return self.get("author")

    @property
    def language(self):
        return self.get("language", "en-US")


@dataclass
class ManuscriptSettings:
    dir: Path
    order: str
    files: list
    chapter_pattern: str
    part_pattern: str
    front_matter: list
    back_matter: list
    references: Path
    summary_heading: str


@dataclass
class ThinkingSettings:
    dir: Path
    stance: Path
    stance_details: Path
    audience: Path
    argument: Path
    doubts: Path


@dataclass
class RulesSettings:
    dir: Path
    decisions: Path
    glossary: Path
    voice: Path
    vale: Path
    vale_ini: Path


@dataclass
class SourcesSettings:
    list: Path
    quotes: Path
    library: Path
    library_index: Path
    backup: Path
    to_add: Path
    citation_style: str

    @property
    def files(self):
        return self.library

    @property
    def origin(self):
        return self.library_index

    @property
    def incoming(self):
        return self.to_add


@dataclass
class PublishingSettings:
    cover: Path
    sales_text: Path


@dataclass
class WorkSettings:
    dir: Path
    runs: Path
    output: Path
    caches: Path


@dataclass
class CoverSettings:
    dir: Path
    design: Path
    final: Path
    trim: str
    paper: str
    book_pdf: Path
    output: Path
    templates: Path
    shelf_screenshots: Path
    cmyk_limit: float
    icc: Path
    srgb_profile: Path


@dataclass
class SalesTextSettings:
    dir: Path
    back_cover: Path
    amazon: Path
    keywords: Path
    intended_impression: Path
    plain_description: Path
    contents: Path
    contents_full: Path
    preface: Path


@dataclass
class AuthorFiles:
    stance: Path
    stance_details: Path
    positioning: Path
    voice: Path


@dataclass
class StyleFiles:
    dir: Path
    vale_ini: Path


@dataclass
class ReadersReviewSettings:
    room: Path
    sources_for_reviewer: Path


@dataclass
class ToolSettings:
    pandoc_image: str
    pandoc_volume: str
    vale_image: str
    bibtex_image: str
    render_image: str
    epubcheck: str


@dataclass
class ManuscriptFile:
    path: Path
    kind: str
    chapter: int = None

    @property
    def name(self):
        return self.path.name


@dataclass
class BookConfig:
    root: Path
    config_file: Path
    fallback_file: Path
    source: str
    layout: str
    version: int
    book: BookMetadata
    manuscript: ManuscriptSettings
    terms: Terms
    thinking: ThinkingSettings
    rules: RulesSettings
    sources: SourcesSettings
    notes: Path
    publishing: PublishingSettings
    work: WorkSettings
    cover: CoverSettings
    sales_text: SalesTextSettings
    readers_review: ReadersReviewSettings
    tools: ToolSettings
    settings: dict
    key_origins: dict

    def get(self, dotted_key, default=_MISSING):
        dotted_key = canonical_key(dotted_key)
        if dotted_key in PATH_KEYS:
            return self.path(dotted_key)
        if dotted_key.startswith("book."):
            return self.book.get(dotted_key[len("book."):],
                                 None if default is _MISSING else default)
        try:
            return _get_dotted(self.settings, dotted_key)
        except KeyError:
            if default is _MISSING:
                raise
            return default

    def path(self, dotted_key):
        resolved = self.resolved_paths()
        dotted_key = canonical_key(dotted_key)
        if dotted_key not in resolved:
            raise KeyError(dotted_key)
        return resolved[dotted_key]

    def resolved_paths(self):
        return {
            "manuscript.dir": self.manuscript.dir,
            "manuscript.references": self.manuscript.references,
            **{f"thinking.{name}": getattr(self.thinking, name) for name in THINKING_FILES},
            **{f"rules.{name}": getattr(self.rules, name) for name in RULES_FILES},
            "sources.list": self.sources.list,
            "sources.quotes": self.sources.quotes,
            "sources.library": self.sources.library,
            "sources.library_index": self.sources.library_index,
            "sources.backup": self.sources.backup,
            "sources.to_add": self.sources.to_add,
            "notes": self.notes,
            "publishing.cover": self.publishing.cover,
            "publishing.sales_text": self.publishing.sales_text,
            "work.dir": self.work.dir,
            **{f"work.{name}": getattr(self.work, name) for name in WORK_SUBFOLDERS},
            "cover.design": self.cover.design,
            "cover.final": self.cover.final,
            "cover.book_pdf": self.cover.book_pdf,
            "cover.output": self.cover.output,
            "cover.templates": self.cover.templates,
            "cover.shelf_screenshots": self.cover.shelf_screenshots,
            "cover.icc": self.cover.icc,
            "cover.srgb_profile": self.cover.srgb_profile,
            "sales_text.back_cover": self.sales_text.back_cover,
            **{f"sales_text.{name}": getattr(self.sales_text, name)
               for name in SALES_TEXT_FILES},
            "readers_review.room": self.readers_review.room,
            "readers_review.sources_for_reviewer": self.readers_review.sources_for_reviewer,
        }

    @property
    def decisions(self):
        return self.rules.decisions

    @property
    def glossary(self):
        return self.rules.glossary

    @property
    def reading_notes(self):
        return self.notes

    @property
    def reasons(self):
        return self.thinking.argument

    @property
    def author(self):
        return AuthorFiles(self.thinking.stance, self.thinking.stance_details,
                           self.thinking.audience, self.rules.voice)

    @property
    def style(self):
        return StyleFiles(self.rules.vale, self.rules.vale_ini)

    @property
    def marketing(self):
        return self.sales_text

    @property
    def outside_review(self):
        return self.readers_review

    @property
    def trim(self):
        return self.cover.trim or self.book.get("format")

    def manuscript_files(self, kinds=None):
        return manuscript_files(self, kinds)

    def chapter_number(self, path):
        return chapter_number(path, self)

    def classify(self, path):
        return classify(path, self)


def _resolve(root, value):
    if value is None or value == "":
        return None
    path = Path(str(value)).expanduser()
    return path if path.is_absolute() else (root / path).resolve()


def _build(settings, root, config_file, fallback_file, source, layout, key_origins):
    def path(dotted_key):
        return _resolve(root, _get_dotted(settings, dotted_key))

    work_dir = path("work.dir")
    work = WorkSettings(
        dir=work_dir,
        **{name: path(f"work.{name}") or (work_dir / name) for name in WORK_SUBFOLDERS},
    )
    manuscript = settings["manuscript"]
    sources = settings["sources"]
    cover = settings["cover"]
    publishing = PublishingSettings(cover=path("publishing.cover"),
                                    sales_text=path("publishing.sales_text"))
    cover_final = path("cover.final") or _cover_default(publishing.cover, layout, "final")
    book_values = _with_shipped_cover(settings.get("book") or {}, cover_final, layout, root)
    terms = settings.get("terms") or {}
    families = []
    for family in terms.get("families") or []:
        if not isinstance(family, dict) or not family.get("term"):
            raise ConfigError(f"terms.families: every item needs a 'term', got {family!r}")
        families.append(TermFamily(str(family["term"]), str(family.get("role") or "").lower(),
                                   [str(word) for word in family.get("also") or []]))
    return BookConfig(
        root=root,
        config_file=config_file,
        fallback_file=fallback_file,
        source=source,
        layout=layout,
        version=settings.get("version"),
        book=BookMetadata(book_values, root),
        manuscript=ManuscriptSettings(
            dir=path("manuscript.dir"),
            order=manuscript.get("order") or "natural",
            files=list(manuscript.get("files") or []),
            chapter_pattern=manuscript.get("chapter_pattern") or CHAPTER_PATTERN,
            part_pattern=manuscript.get("part_pattern") or PART_PATTERN,
            front_matter=_as_list(manuscript.get("front_matter")),
            back_matter=_as_list(manuscript.get("back_matter")),
            references=path("manuscript.references"),
            summary_heading=manuscript.get("summary_heading") or "Summary",
        ),
        terms=Terms(families, [str(c).lower() for c in terms.get("compounds") or []],
                    dict(terms.get("watch_words") or {})),
        thinking=ThinkingSettings(**{name: path(f"thinking.{name}") for name in THINKING_FILES}),
        rules=RulesSettings(**{name: path(f"rules.{name}") for name in RULES_FILES}),
        sources=SourcesSettings(
            list=path("sources.list"),
            quotes=path("sources.quotes"),
            library=path("sources.library"),
            library_index=path("sources.library_index"),
            backup=path("sources.backup"),
            to_add=path("sources.to_add") or work_dir / SOURCES_TO_ADD_FOLDER,
            citation_style=sources.get("citation_style") or "alpha",
        ),
        notes=path("notes"),
        publishing=publishing,
        work=work,
        cover=CoverSettings(
            dir=publishing.cover,
            design=path("cover.design") or _cover_default(publishing.cover, layout, "design"),
            final=cover_final,
            trim=cover.get("trim"),
            paper=cover.get("paper") or "bw-white",
            book_pdf=path("cover.book_pdf"),
            output=path("cover.output") or work.output / COVER_OUTPUT_FOLDER,
            templates=path("cover.templates") or work.caches / COVER_TEMPLATES_FOLDER,
            shelf_screenshots=path("cover.shelf_screenshots") or work.caches / COVER_SHELF_FOLDER,
            cmyk_limit=float(cover.get("cmyk_limit") or SHARED_DEFAULTS["cover"]["cmyk_limit"]),
            icc=path("cover.icc"),
            srgb_profile=path("cover.srgb_profile"),
        ),
        sales_text=SalesTextSettings(
            dir=publishing.sales_text,
            back_cover=path("sales_text.back_cover")
            or _sales_text_default(publishing.sales_text, layout, "back_cover"),
            **{name: path(f"sales_text.{name}")
               or _sales_text_default(publishing.sales_text, layout, name)
               for name in SALES_TEXT_FILES},
        ),
        readers_review=ReadersReviewSettings(
            room=path("readers_review.room") or _readers_room_default(root),
            sources_for_reviewer=path("readers_review.sources_for_reviewer")
            or work.output / SOURCES_FOR_REVIEWER_FILE,
        ),
        tools=ToolSettings(**{name: str(settings["tools"].get(name) or "")
                              for name in TOOL_KEYS}),
        settings=settings,
        key_origins=key_origins,
    )


def _cover_default(folder, layout, name):
    file_name = COVER_FILE_NAMES[layout].get(name)
    if folder is None or file_name is None:
        return None
    return folder if file_name == "." else folder / file_name


def _with_shipped_cover(book, cover_final, layout, root):
    if layout == LAYOUT_OLD or cover_final is None:
        return book
    filled = dict(book)
    for key, file_name in SHIPPED_COVER_FILES.items():
        shipped = cover_final / file_name
        if not filled.get(key) and shipped.is_file():
            filled[key] = _from_root(shipped, root)
    return filled


def _from_root(path, root):
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _readers_room_default(root):
    room = root.parent / f"{root.name}{READERS_REVIEW_ROOM_SUFFIX}"
    old_room = root.parent / f"{root.name}{OLD_READERS_REVIEW_ROOM_SUFFIX}"
    return old_room if old_room.is_dir() and not room.exists() else room


def _sales_text_default(folder, layout, name):
    file_name = SALES_TEXT_FILE_NAMES[layout].get(name)
    if folder is None or file_name is None:
        return None
    chosen = folder / file_name
    old_files = [folder / old_name for old_name in OLD_SALES_TEXT_FILE_NAMES.get(name, ())]
    old_file = next((path for path in old_files if path.is_file()), None)
    return old_file if old_file and not chosen.exists() else chosen


def _as_list(value):
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)


def _record_origins(origins, layer, source, prefix=""):
    for key, value in layer.items():
        dotted = f"{prefix}{key}"
        if isinstance(value, dict) and key != "watch_words":
            _record_origins(origins, value, source, dotted + ".")
        else:
            origins[dotted] = source


def load_config(config=None, start=None, overrides=None):
    config_file = fallback_file = None
    if config:
        chosen = Path(config).expanduser().resolve()
        if not chosen.is_file():
            raise ConfigError(f"config file not found: {chosen}")
        if chosen.name == FALLBACK_FILE_NAME or chosen.suffix == ".md":
            fallback_file = chosen
        else:
            config_file = chosen
    else:
        config_file = find_config_file(start)
        if config_file is None:
            fallback_file = find_fallback_file(start)

    if config_file:
        root = config_file.parent
        sibling = root / FALLBACK_FILE_NAME
        if sibling.is_file() and has_fallback_sections(sibling):
            fallback_file = sibling
    elif fallback_file:
        root = fallback_file.parent
    else:
        root = Path(start or Path.cwd()).resolve()

    file_layer = with_new_key_names(read_config_file(config_file)) if config_file else {}
    layout = detect_layout(root, config_file, fallback_file, file_layer.get(LAYOUT_KEY))
    settings = _merge(SHARED_DEFAULTS, LAYOUT_DEFAULTS[layout])
    origins = {}
    _record_origins(origins, settings, SOURCE_DEFAULTS)
    source = SOURCE_DEFAULTS

    if fallback_file:
        layer = _normalise_shapes(settings_from_fallback_file(fallback_file))
        settings = _merge(settings, layer)
        _record_origins(origins, layer, SOURCE_FALLBACK)
        source = SOURCE_FALLBACK
    if config_file:
        layer = _normalise_shapes(file_layer)
        settings = _merge(settings, layer)
        _record_origins(origins, layer, SOURCE_CONFIG_FILE)
        source = SOURCE_CONFIG_FILE

    for key, value in _override_items(overrides):
        _set_dotted(settings, key, value)
        origins[key] = SOURCE_CLI
    settings = _normalise_shapes(settings)

    return _build(settings, root, config_file, fallback_file, source, layout, origins)


def detect_layout(root, config_file, fallback_file, chosen=None):
    if chosen is not None:
        if chosen not in LAYOUTS:
            raise ConfigError(f"{LAYOUT_KEY} must be one of {', '.join(LAYOUTS)}, "
                              f"not {chosen!r}")
        return chosen
    if config_file:
        if any((root / sign).exists() for sign in NEW_LAYOUT_SIGNS):
            return LAYOUT_NEW
        if any((root / sign).exists() for sign in PREVIOUS_LAYOUT_SIGNS):
            return LAYOUT_PREVIOUS
        return LAYOUT_NEW
    if fallback_file or (root / OLD_LAYOUT_MARKER).is_file():
        return LAYOUT_OLD
    return LAYOUT_NEW


def _override_items(overrides):
    if not overrides:
        return []
    if isinstance(overrides, dict):
        return [(canonical_key(key), value) for key, value in overrides.items()]
    return [parse_override(item) for item in overrides]


def add_config_arguments(parser):
    parser.add_argument("--config", metavar="FILE",
                        help="the book's book.yaml (default: found by walking up from the "
                             "working directory; an older book's CLAUDE.md also works)")
    parser.add_argument("--set", dest="config_overrides", action="append", default=[],
                        metavar="KEY=VALUE",
                        help="override one config value, e.g. --set sources.list=x.md "
                             "(repeatable)")
    return parser


def config_from_args(args, start=None, targets=None):
    return load_config(getattr(args, "config", None), start or start_folder(targets),
                       getattr(args, "config_overrides", None))


def start_folder(targets):
    for target in _as_list(targets):
        if target is None or str(target) == "":
            continue
        path = Path(str(target)).expanduser()
        if path.exists():
            return (path if path.is_dir() else path.parent).resolve()
    return None


def natural_sort_key(text):
    return [(0, int(piece), "") if piece.isdigit() else (1, 0, piece.lower())
            for piece in re.split(r"(\d+)", str(text)) if piece]


def classify(path, config=None):
    config = config or load_config()
    path = Path(path)
    name = path.name
    if config.manuscript.references and path.resolve() == config.manuscript.references:
        return KIND_REFERENCES, None
    found = re.search(config.manuscript.chapter_pattern, name)
    if found:
        return KIND_CHAPTER, int(found.group(1)) if found.groups() else None
    if re.search(config.manuscript.part_pattern, name):
        return KIND_PART, None
    if any(fnmatch.fnmatch(name, pattern) for pattern in config.manuscript.front_matter):
        return KIND_FRONT_MATTER, None
    if any(fnmatch.fnmatch(name, pattern) for pattern in config.manuscript.back_matter):
        return KIND_BACK_MATTER, None
    return KIND_OTHER, None


def chapter_number(path, config=None):
    kind, number = classify(path, config)
    return number if kind == KIND_CHAPTER else None


def manuscript_files(config=None, kinds=None):
    config = config or load_config()
    folder = config.manuscript.dir
    if config.manuscript.order == "list":
        paths = [_resolve(folder, name) for name in config.manuscript.files]
        missing = [str(path) for path in paths if not path.is_file()]
        if missing:
            raise ConfigError("manuscript.files lists files that do not exist: "
                              + ", ".join(missing))
    elif config.manuscript.order == "natural":
        paths = sorted(folder.glob("*.md"), key=lambda path: natural_sort_key(path.name)) \
            if folder and folder.is_dir() else []
    else:
        raise ConfigError(f"manuscript.order must be 'natural' or 'list', "
                          f"not {config.manuscript.order!r}")
    wanted = set(_as_list(kinds)) if kinds else None
    result = []
    for path in paths:
        kind, number = classify(path, config)
        if wanted is None or kind in wanted:
            result.append(ManuscriptFile(path, kind, number))
    return result


def _shell_name(prefix, dotted_key):
    return prefix + re.sub(r"[^A-Za-z0-9]+", "_", dotted_key).upper()


def _plain(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def shell_paths(config):
    lines = [
        f"BOOK_ROOT={shlex.quote(str(config.root))}",
        f"BOOK_CONFIG_FILE={shlex.quote(_plain(config.config_file))}",
        f"BOOK_FALLBACK_FILE={shlex.quote(_plain(config.fallback_file))}",
        f"BOOK_CONFIG_SOURCE={shlex.quote(config.source)}",
        f"BOOK_LAYOUT={shlex.quote(config.layout)}",
    ]
    for key, value in config.resolved_paths().items():
        lines.append(f"{_shell_name('BOOK_', key)}={shlex.quote(_plain(value))}")
    for key, value in vars(config.tools).items():
        lines.append(f"{_shell_name('BOOK_TOOLS_', key)}={shlex.quote(_plain(value))}")
    return "\n".join(lines)


def shell_metadata(config):
    return "\n".join(f"{_shell_name('BOOK_META_', key)}={shlex.quote(_plain(value))}"
                     for key, value in sorted(config.book.values.items()))


def as_dict(config):
    return {
        "root": str(config.root),
        "config_file": _plain(config.config_file) or None,
        "fallback_file": _plain(config.fallback_file) or None,
        "source": config.source,
        "layout": config.layout,
        "version": config.version,
        "book": config.book.values,
        "paths": {key: _plain(value) or None for key, value in config.resolved_paths().items()},
        "manuscript": {
            "order": config.manuscript.order,
            "files": config.manuscript.files,
            "chapter_pattern": config.manuscript.chapter_pattern,
            "part_pattern": config.manuscript.part_pattern,
            "front_matter": config.manuscript.front_matter,
            "back_matter": config.manuscript.back_matter,
            "summary_heading": config.manuscript.summary_heading,
        },
        "terms": {
            "families": [vars(family) for family in config.terms.families],
            "compounds": config.terms.compounds,
            "watch_words": config.terms.watch_words,
        },
        "sources": {"citation_style": config.sources.citation_style},
        "cover": {"trim": config.trim, "paper": config.cover.paper},
        "tools": vars(config.tools),
        "key_origins": config.key_origins,
    }


def _show(config):
    print(f"root            {config.root}")
    print(f"read from       {config.source}"
          + (f"  ({config.config_file})" if config.config_file else "")
          + (f"  (fallback {config.fallback_file})" if config.fallback_file else ""))
    print(f"layout          {config.layout}")
    print("\npaths")
    for key, value in config.resolved_paths().items():
        state = "" if value is None else ("" if value.exists() else "   (missing)")
        origin = config.key_origins.get(key, SOURCE_DEFAULTS)
        print(f"  {key:24} {_plain(value) or '-'}{state}   [{origin}]")
    print("\nbook")
    for key, value in sorted(config.book.values.items()):
        print(f"  {key:24} {_plain(value)}")
    print("\nterms")
    for family in config.terms.families:
        also = f" (also: {', '.join(family.also)})" if family.also else ""
        print(f"  {family.role:10} {family.term}{also}")
    print(f"  {len(config.terms.compounds)} legal compound(s)")
    files = manuscript_files(config)
    print(f"\nmanuscript      {len(files)} file(s)")
    for kind in MANUSCRIPT_KINDS:
        count = sum(1 for item in files if item.kind == kind)
        if count:
            print(f"  {kind:14} {count}")


CHECK_CLASSES = {
    "unknown-key": "defect",
    "retired-key": "defect",
    "old-key-name": "informational",
    "previous-layout": "informational",
    "missing-path": "informational",
    "no-config-file": "informational",
    "unused-file": "defect",
}


def unused_files(config, written):
    places = []
    if config.rules.dir:
        places.append(Path(config.rules.dir) / ACCEPTED_COUNTS_FILE)
    if config.work.dir:
        places.append(Path(config.work.dir) / OLD_ACCEPTED_COUNTS_FILE)
    if _has_dotted(written, ACCEPTED_COUNTS_KEY):
        places.append(_resolve(config.root, _get_dotted(written, ACCEPTED_COUNTS_KEY)))
    existing = {place.resolve(): place for place in places if place and place.is_file()}
    return list(existing.values())


def _check(config, output_format):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from check_output import CheckReport
    report = CheckReport("book-config", CHECK_CLASSES)
    written = {}
    if config.config_file:
        written = read_config_file(config.config_file)
        name = config.config_file.name
        for key in unknown_keys(written):
            report.add(key, "unknown-key", f"{name}: no script reads '{key}'")
        for key in retired_key_names(written):
            report.add(key, "retired-key", f"{name}: '{key}' is no longer read; "
                                           f"{RETIRED_KEYS[key]}")
        for key in old_key_names(written):
            report.add(key, "old-key-name", f"{name}: '{key}' is an old name; "
                                            f"write '{canonical_key(key)}'")
    else:
        report.add("-", "no-config-file", f"no book.yaml found; using {config.source}")
    for place in unused_files(config, written):
        report.add(str(place), "unused-file", "the accepted counts are no longer used: every "
                                              "finding is reported until it is fixed; delete it")
    if config.layout != LAYOUT_NEW:
        report.add(LAYOUT_KEY, "previous-layout",
                   f"the book uses the {config.layout} folder layout; the init skill "
                   f"(mode existing) moves it to the new one")
    for key, value in config.resolved_paths().items():
        if value is not None and not value.exists():
            report.add(key, "missing-path", str(value))
    return report.emit(output_format)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Show the book's configuration: paths, metadata, coined terms and "
                    "manuscript files, from book.yaml or an older book's CLAUDE.md.",
        epilog='Shell use: eval "$(python3 book_config.py paths --shell)"')
    add_config_arguments(parser)
    parser.add_argument("--start", metavar="DIR",
                        help="folder to walk up from (default: the working directory)")
    commands = parser.add_subparsers(dest="command", required=True)
    show = commands.add_parser("show", help="everything, with where each value came from")
    show.add_argument("--json", action="store_true", help="print JSON instead of text")
    get = commands.add_parser("get", help="one value by dotted key, e.g. sources.list")
    get.add_argument("key")
    paths = commands.add_parser("paths", help="every resolved path")
    paths.add_argument("--shell", action="store_true", help="print BOOK_*=... for eval")
    metadata = commands.add_parser("metadata", help="the book metadata")
    metadata.add_argument("--shell", action="store_true", help="print BOOK_META_*=... for eval")
    files = commands.add_parser("files", help="manuscript files in book order")
    files.add_argument("--kind", action="append", choices=MANUSCRIPT_KINDS,
                       help="only this kind (repeatable)")
    check = commands.add_parser("check", help="unknown, retired and old key names, the "
                                               "layout, missing paths and unused files")
    check.add_argument("--format", choices=("text", "tsv", "json"), default="text")
    args = parser.parse_args(argv)

    try:
        config = config_from_args(args, args.start)
        if args.command == "show":
            if args.json:
                print(json.dumps(as_dict(config), indent=2, ensure_ascii=False, default=str))
            else:
                _show(config)
        elif args.command == "get":
            try:
                value = config.get(args.key)
            except KeyError:
                sys.stderr.write(f"unknown key: {args.key}\n")
                return 2
            if isinstance(value, list):
                print("\n".join(_plain(item) for item in value))
            else:
                print(_plain(value))
        elif args.command == "paths":
            if args.shell:
                print(shell_paths(config))
            else:
                for key, value in config.resolved_paths().items():
                    print(f"{key}\t{_plain(value)}")
        elif args.command == "metadata":
            if args.shell:
                print(shell_metadata(config))
            else:
                for key, value in sorted(config.book.values.items()):
                    print(f"{key}\t{_plain(value)}")
        elif args.command == "files":
            for item in manuscript_files(config, args.kind):
                print(f"{item.path}\t{item.kind}\t{_plain(item.chapter)}")
        elif args.command == "check":
            return _check(config, args.format)
    except ConfigError as error:
        sys.stderr.write(f"book_config: {error}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
