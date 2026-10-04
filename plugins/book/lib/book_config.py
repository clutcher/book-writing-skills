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

from check_output import CheckReport, run_main

CONFIG_FILE_NAMES = ("book.yaml", "book.yml", "book.json")

SOURCE_CLI = "command line"
SOURCE_CONFIG_FILE = "config file"
SOURCE_DEFAULTS = "defaults"

KIND_FRONT_MATTER = "front-matter"
KIND_PART = "part"
KIND_CHAPTER = "chapter"
KIND_REFERENCES = "references"
KIND_BACK_MATTER = "back-matter"
KIND_OTHER = "other"
MANUSCRIPT_KINDS = (KIND_FRONT_MATTER, KIND_PART, KIND_CHAPTER, KIND_REFERENCES,
                    KIND_BACK_MATTER, KIND_OTHER)

KIND_BOOK = "book"
KIND_PAPER = "paper"
DOCUMENT_KINDS = (KIND_BOOK, KIND_PAPER)

PAPER_BUILT_IN_TEMPLATE = "article"
PAPER_BUILT_IN_TEMPLATES = ("article", "acm", "ieee", "lncs")
PAPER_ENGINES = ("xelatex", "pdflatex")
PAPER_FORMATS = ("a4", "letter")
PAPER_FRONT_MATTER = ["00[0-9]-*.md"]
PAPER_AUTHOR_FIELDS = ("name", "affiliation", "email")
PUBLISHING_KEY_PREFIXES = ("publishing.", "cover.", "sales_text.")

CHAPTER_PATTERN = r"(?:^|-)chapter-(\d+)\.md$"
PART_PATTERN = r"^(\d+-)?part-[\w-]+\.md$"

BIBTEX_IMAGE = ("blang/latex:ubuntu@sha256:"
                "2c32abc3555a01e180528d542955e2730f7f3793cdeba49b1655de9b897cbafb")
PAPER_TEX_IMAGE = ("texlive/texlive:TL2025-historic@sha256:"
                   "7056390eac37715fd3e01875037ceb4016cb17d44c611f7bbbfa7a012007979f")
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
    "kind": KIND_BOOK,
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
    "sources": {"backup": None, "citation_style": "alpha", "citation_style_file": None},
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
    "paper": {
        "authors": [],
        "abstract": "manuscript/010-abstract.md",
        "template": PAPER_BUILT_IN_TEMPLATE,
        "engine": "xelatex",
        "anonymous": False,
        "arxiv_category": None,
        "abstract_max_words": 250,
        "format": "a4",
    },
    "tools": {
        "pandoc_image": "pandoc/extra:3.8.3",
        "pandoc_volume": "book-to-pdf-texlive",
        "vale_image": "jdkato/vale:v3.14.2",
        "bibtex_image": BIBTEX_IMAGE,
        "paper_tex_image": PAPER_TEX_IMAGE,
        "render_image": None,
        "epubcheck": "5.1.0",
    },
}

FOLDER_DEFAULTS = {
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
        "bibliography": "sources/references.bib",
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

SALES_TEXT_FILE_NAMES = {
    "back_cover": "back-cover.md",
    "amazon": "amazon.html",
    "keywords": "keywords-and-categories.md",
    "intended_impression": "intended-impression.md",
    "plain_description": "plain-description.txt",
    "contents": "contents.html",
    "contents_full": "contents-full.html",
}
COVER_FILE_NAMES = {"design": "design.py", "final": "final"}
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

THINKING_FILES = ("dir", "stance", "stance_details", "audience", "argument", "doubts")
RULES_FILES = ("dir", "decisions", "glossary", "voice", "vale", "vale_ini")
WORK_SUBFOLDERS = ("runs", "output", "caches")

PATH_KEYS = (
    "manuscript.dir", "manuscript.references",
    *(f"thinking.{name}" for name in THINKING_FILES),
    *(f"rules.{name}" for name in RULES_FILES),
    "sources.list", "sources.quotes", "sources.bibliography", "sources.library",
    "sources.library_index", "sources.backup", "sources.to_add", "sources.citation_style_file",
    "notes",
    "publishing.cover", "publishing.sales_text",
    "work.dir", *(f"work.{name}" for name in WORK_SUBFOLDERS),
    "cover.design", "cover.final", "cover.book_pdf", "cover.output",
    "cover.templates", "cover.shelf_screenshots", "cover.icc", "cover.srgb_profile",
    "sales_text.back_cover",
    *(f"sales_text.{name}" for name in SALES_TEXT_FILES),
    "readers_review.room", "readers_review.sources_for_reviewer",
)

TOOL_KEYS = ("pandoc_image", "pandoc_volume", "vale_image", "bibtex_image", "paper_tex_image",
             "render_image", "epubcheck")

METADATA_PATH_KEYS = ("cover_front", "cover_back", "ebook_cover")

CITATION_STYLES = ("alpha", "numeric")
DEFAULT_CITATION_STYLE = "alpha"

_MISSING = object()


class ConfigError(Exception):
    pass


_NUMBER_INT = re.compile(r"^[-+]?\d+$")
_NUMBER_FLOAT = re.compile(r"^[-+]?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?$")
_BLOCK_STRING = re.compile(r"^([|>])([-+]?)$")
_DOCUMENT_MARKERS = ("---", "...")
_UNSET_TEXT = ("", "~", "null")
_TEXT_KEYS = frozenset(("title", "subtitle", "author", "publisher", "epub_identifier",
                        "description", "accessibility_summary"))
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
            self.lines.append(_Line(number, len(content) - len(content.lstrip()),
                                    content.strip()))
        self.position = 0

    def document(self):
        if not self.lines:
            return {}
        value = self.block(self.lines[0].indent)
        if self.position < len(self.lines):
            line = self.lines[self.position]
            _refuse_document_marker(line)
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
            _refuse_document_marker(line)
            if line.indent > indent:
                raise ConfigError(f"line {line.number}: unexpected indentation")
            if _is_list_item(line.text):
                raise ConfigError(f"line {line.number}: a list item where a key was expected")
            key, rest = _split_key(line)
            if key in result:
                raise ConfigError(f"line {line.number}: key {key!r} appears twice")
            self.position += 1
            result[key] = self.value_after_key(rest, indent, line, key in _TEXT_KEYS)
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

    def value_after_key(self, rest, indent, line, keep_plain_text=False):
        if rest:
            return self.scalar_or_block_string(rest, indent, line, keep_plain_text)
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

    def scalar_or_block_string(self, text, indent, line, keep_plain_text=False):
        block = _BLOCK_STRING.match(text)
        if block:
            return self.block_string(block.group(1), block.group(2), indent, line)
        return parse_scalar(text, line.number, keep_plain_text)

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


def _refuse_document_marker(line):
    if line.text in _DOCUMENT_MARKERS:
        raise ConfigError(f"line {line.number}: several documents in one file "
                          f"are not supported")


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
    flow_depth = 0
    while index < len(raw):
        character = raw[index]
        before = raw[:index]
        if character in ("'", '"') and _opens_quoted_scalar(before, flow_depth):
            end = _closing_quote(raw, index)
            if end is None:
                return raw
            index = end + 1
            continue
        if character in "[{" and (flow_depth or _starts_value(before)):
            flow_depth += 1
        elif character in "]}" and flow_depth:
            flow_depth -= 1
        elif character == "#" and (index == 0 or raw[index - 1] in " \t"):
            return raw[:index]
        index += 1
    return raw


def _starts_value(before):
    before = before.rstrip()
    return (not before or before.endswith(":")
            or re.fullmatch(r"\s*-(?:\s+-)*", before) is not None)


def _opens_quoted_scalar(before, flow_depth):
    if _starts_value(before):
        return True
    return flow_depth > 0 and before.rstrip().endswith(("[", "{", ","))


def parse_scalar(text, line_number=0, keep_plain_text=False):
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
    if keep_plain_text and text not in _UNSET_TEXT:
        return text
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


def find_config_file(start=None):
    for folder in _folders_upwards(start):
        for name in CONFIG_FILE_NAMES:
            candidate = folder / name
            if candidate.is_file():
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
        text = path.read_text(encoding="utf-8-sig")
    except OSError as error:
        raise ConfigError(f"{path}: {error.strerror}") from error
    except UnicodeDecodeError as error:
        raise ConfigError(f"{path}: not UTF-8 text ({error.reason})") from error
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


def sections_as_mappings(settings, defaults=None, prefix=""):
    defaults = all_defaults() if defaults is None else defaults
    shaped = {}
    for key, value in settings.items():
        default = defaults.get(key)
        dotted = f"{prefix}{key}"
        if not isinstance(default, dict) or dotted == "work" and isinstance(value, str):
            shaped[key] = value
        elif value is None:
            continue
        elif not isinstance(value, dict):
            raise ConfigError(f"'{dotted}' must hold keys (one per line below it), "
                              f"not {value!r}")
        elif key in ("book", "watch_words"):
            shaped[key] = value
        else:
            shaped[key] = sections_as_mappings(value, default, dotted + ".")
    return shaped


def all_defaults():
    return _merge(SHARED_DEFAULTS, FOLDER_DEFAULTS)


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


def parse_override(text):
    if "=" not in text:
        raise ConfigError(f"--set expects KEY=VALUE, got {text!r}")
    key, value = text.split("=", 1)
    key = key.strip()
    if key.startswith("book."):
        key = "book." + normalise_metadata_key(key[len("book."):])
    if not value.strip():
        return key, None
    keep_plain_text = key.rsplit(".", 1)[-1] in _TEXT_KEYS
    try:
        return key, parse_scalar(value, keep_plain_text=keep_plain_text)
    except ConfigError as error:
        reason = re.sub(r"^line \d+: ", "", str(error))
        raise ConfigError(f"--set {key}: {reason}; to pass it as plain text, quote the value, "
                          f"e.g. --set '{key}=\"{value.strip()}\"'") from error


def _known_keys(tree, prefix=""):
    keys = set()
    for key, value in tree.items():
        dotted = f"{prefix}{key}"
        keys.add(dotted)
        if isinstance(value, dict) and key not in ("book", "watch_words"):
            keys |= _known_keys(value, dotted + ".")
    return keys


ALL_KNOWN_KEYS = frozenset(_known_keys(all_defaults()))


def unknown_keys(settings, prefix=""):
    found = []
    for key, value in settings.items():
        dotted = f"{prefix}{key}"
        if dotted not in ALL_KNOWN_KEYS:
            found.append(dotted)
            continue
        if dotted == "book" and isinstance(value, dict):
            found.extend(f"book.{name}" for name in value
                         if normalise_metadata_key(str(name)) not in BOOK_KEYS)
        elif isinstance(value, dict) and key != "watch_words":
            found.extend(unknown_keys(value, dotted + "."))
    return found


def default(dotted_key):
    return _get_dotted(all_defaults(), dotted_key)


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
    bibliography: Path
    library: Path
    library_index: Path
    backup: Path
    to_add: Path
    citation_style: str
    citation_style_file: Path


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
class ReadersReviewSettings:
    room: Path
    sources_for_reviewer: Path


@dataclass
class ToolSettings:
    pandoc_image: str
    pandoc_volume: str
    vale_image: str
    bibtex_image: str
    paper_tex_image: str
    render_image: str
    epubcheck: str


@dataclass
class PaperAuthor:
    name: str
    affiliation: str = None
    email: str = None


@dataclass
class PaperSettings:
    authors: list
    abstract: Path
    template: str
    engine: str
    anonymous: bool
    arxiv_category: str
    abstract_max_words: int
    format: str


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
    source: str
    version: int
    kind: str
    book: BookMetadata
    paper: PaperSettings
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
            "sources.bibliography": self.sources.bibliography,
            "sources.library": self.sources.library,
            "sources.library_index": self.sources.library_index,
            "sources.backup": self.sources.backup,
            "sources.to_add": self.sources.to_add,
            "sources.citation_style_file": self.sources.citation_style_file,
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
    def is_paper(self):
        return self.kind == KIND_PAPER

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


def _build(settings, root, config_file, source, key_origins):
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
    cover_final = path("cover.final") or _cover_default(publishing.cover, "final")
    book_values = _with_shipped_cover(settings.get("book") or {}, cover_final, root)
    kind = str(settings.get("kind") or KIND_BOOK).strip().lower()
    paper = _paper_settings(settings.get("paper") or {}, root, book_values.get("author"))
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
        source=source,
        version=settings.get("version"),
        kind=kind,
        book=BookMetadata(book_values, root),
        paper=paper,
        manuscript=ManuscriptSettings(
            dir=path("manuscript.dir"),
            order=manuscript.get("order") or "natural",
            files=_as_list(manuscript.get("files")),
            chapter_pattern=manuscript.get("chapter_pattern") or CHAPTER_PATTERN,
            part_pattern=manuscript.get("part_pattern") or PART_PATTERN,
            front_matter=_front_matter_patterns(manuscript, kind, paper, key_origins),
            back_matter=_back_matter_patterns(manuscript, kind, key_origins),
            references=path("manuscript.references"),
            summary_heading=manuscript.get("summary_heading") or "Summary",
        ),
        terms=Terms(families, [str(c).lower() for c in _as_list(terms.get("compounds"))],
                    dict(terms.get("watch_words") or {})),
        thinking=ThinkingSettings(**{name: path(f"thinking.{name}") for name in THINKING_FILES}),
        rules=RulesSettings(**{name: path(f"rules.{name}") for name in RULES_FILES}),
        sources=SourcesSettings(
            list=path("sources.list"),
            quotes=path("sources.quotes"),
            bibliography=path("sources.bibliography"),
            library=path("sources.library"),
            library_index=path("sources.library_index"),
            backup=path("sources.backup"),
            to_add=path("sources.to_add") or work_dir / SOURCES_TO_ADD_FOLDER,
            citation_style=str(sources.get("citation_style") or DEFAULT_CITATION_STYLE).strip(),
            citation_style_file=path("sources.citation_style_file"),
        ),
        notes=path("notes"),
        publishing=publishing,
        work=work,
        cover=CoverSettings(
            dir=publishing.cover,
            design=path("cover.design") or _cover_default(publishing.cover, "design"),
            final=cover_final,
            trim=cover.get("trim"),
            paper=cover.get("paper") or "bw-white",
            book_pdf=path("cover.book_pdf"),
            output=path("cover.output") or work.output / COVER_OUTPUT_FOLDER,
            templates=path("cover.templates") or work.caches / COVER_TEMPLATES_FOLDER,
            shelf_screenshots=path("cover.shelf_screenshots") or work.caches / COVER_SHELF_FOLDER,
            cmyk_limit=_cmyk_limit(cover.get("cmyk_limit")),
            icc=path("cover.icc"),
            srgb_profile=path("cover.srgb_profile"),
        ),
        sales_text=SalesTextSettings(
            dir=publishing.sales_text,
            back_cover=path("sales_text.back_cover")
            or _sales_text_default(publishing.sales_text, "back_cover"),
            **{name: path(f"sales_text.{name}")
               or _sales_text_default(publishing.sales_text, name)
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


def _set_by_the_book(key_origins, dotted_key):
    return key_origins.get(dotted_key, SOURCE_DEFAULTS) != SOURCE_DEFAULTS


def _front_matter_patterns(manuscript, kind, paper, key_origins):
    if kind != KIND_PAPER or _set_by_the_book(key_origins, "manuscript.front_matter"):
        return _as_list(manuscript.get("front_matter"))
    patterns = list(PAPER_FRONT_MATTER)
    if paper.abstract is not None:
        patterns.append(paper.abstract.name)
    return patterns


def _back_matter_patterns(manuscript, kind, key_origins):
    if kind != KIND_PAPER or _set_by_the_book(key_origins, "manuscript.back_matter"):
        return _as_list(manuscript.get("back_matter"))
    return []


def _paper_settings(paper, root, book_author):
    defaults = SHARED_DEFAULTS["paper"]
    template = str(paper.get("template") or PAPER_BUILT_IN_TEMPLATE).strip()
    return PaperSettings(
        authors=_paper_authors(paper.get("authors"), book_author),
        abstract=_resolve(root, paper.get("abstract")),
        template=template,
        engine=str(paper.get("engine") or defaults["engine"]).strip().lower(),
        anonymous=paper.get("anonymous") is True,
        arxiv_category=paper.get("arxiv_category") or None,
        abstract_max_words=_whole_number(paper.get("abstract_max_words"),
                                         defaults["abstract_max_words"]),
        format=str(paper.get("format") or defaults["format"]).strip().lower(),
    )


def _paper_authors(written, book_author):
    authors = [author for author in (_paper_author(item) for item in _as_list(written))
               if author is not None]
    if authors or not book_author:
        return authors
    return [PaperAuthor(str(book_author))]


def _paper_author(item):
    if isinstance(item, str) and item.strip():
        return PaperAuthor(item.strip())
    if isinstance(item, dict) and str(item.get("name") or "").strip():
        return PaperAuthor(**{name: _text_or_none(item.get(name))
                              for name in PAPER_AUTHOR_FIELDS})
    return None


def _text_or_none(value):
    return None if value is None or str(value).strip() == "" else str(value).strip()


def _whole_number(value, fallback):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return fallback
    return value


def _cmyk_limit(value):
    if value is None or value == "":
        return float(SHARED_DEFAULTS["cover"]["cmyk_limit"])
    try:
        limit = float(str(value).strip().rstrip("%").strip())
    except ValueError:
        limit = None
    if limit is None or not 0 < limit <= 100:
        raise ConfigError(f"cover.cmyk_limit must be a percent above 0 and at most 100, "
                          f"such as 88, not {value!r}")
    return limit


def _cover_default(folder, name):
    if folder is None:
        return None
    return folder / COVER_FILE_NAMES[name]


def _with_shipped_cover(book, cover_final, root):
    if cover_final is None:
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
    return root.parent / f"{root.name}{READERS_REVIEW_ROOM_SUFFIX}"


def _sales_text_default(folder, name):
    file_name = SALES_TEXT_FILE_NAMES.get(name)
    if folder is None or file_name is None:
        return None
    return folder / file_name


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
    if config:
        config_file = Path(config).expanduser().resolve()
        if not config_file.is_file():
            raise ConfigError(f"config file not found: {config_file}")
    else:
        config_file = find_config_file(start)
    root = config_file.parent if config_file else Path(start or Path.cwd()).resolve()

    settings = all_defaults()
    origins = {}
    _record_origins(origins, settings, SOURCE_DEFAULTS)
    source = SOURCE_DEFAULTS
    if config_file:
        layer = _normalise_shapes(_config_file_layer(config_file))
        settings = _merge(settings, layer)
        _record_origins(origins, layer, SOURCE_CONFIG_FILE)
        source = SOURCE_CONFIG_FILE

    for key, value in _override_items(overrides):
        _set_dotted(settings, key, value)
        origins[key] = SOURCE_CLI
    settings = _normalise_shapes(settings)

    return _build(settings, root, config_file, source, origins)


def _config_file_layer(config_file):
    try:
        return sections_as_mappings(read_config_file(config_file))
    except ConfigError as error:
        if str(error).startswith(str(config_file)):
            raise
        raise ConfigError(f"{config_file}: {error}") from error


def _override_items(overrides):
    if not overrides:
        return []
    if isinstance(overrides, dict):
        return list(overrides.items())
    return [parse_override(item) for item in overrides]


def add_config_arguments(parser):
    parser.add_argument("--config", metavar="FILE",
                        help="the book's book.yaml (default: found by walking up from the "
                             "working directory)")
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
    if config.is_paper:
        return _classify_paper_file(path, config)
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


def _classify_paper_file(path, config):
    kind = _paper_file_kind(path, config)
    if kind != KIND_CHAPTER:
        return kind, None
    return KIND_CHAPTER, _paper_section_number(path, config)


def _paper_file_kind(path, config):
    resolved = path.resolve()
    if config.manuscript.references and resolved == config.manuscript.references:
        return KIND_REFERENCES
    if config.paper.abstract and resolved == config.paper.abstract:
        return KIND_FRONT_MATTER
    if _matches_any(path.name, config.manuscript.front_matter):
        return KIND_FRONT_MATTER
    if _matches_any(path.name, config.manuscript.back_matter):
        return KIND_BACK_MATTER
    return KIND_CHAPTER


def _paper_section_number(path, config):
    try:
        ordered = _ordered_manuscript_paths(config)
    except ConfigError:
        return None
    sections = [candidate.resolve() for candidate in ordered
                if _paper_file_kind(candidate, config) == KIND_CHAPTER]
    resolved = path.resolve()
    return sections.index(resolved) + 1 if resolved in sections else None


def _matches_any(name, patterns):
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def chapter_number(path, config=None):
    kind, number = classify(path, config)
    return number if kind == KIND_CHAPTER else None


def manuscript_files(config=None, kinds=None):
    config = config or load_config()
    paths = _ordered_manuscript_paths(config)
    wanted = set(_as_list(kinds)) if kinds else None
    result = []
    for path in paths:
        kind, number = classify(path, config)
        if wanted is None or kind in wanted:
            result.append(ManuscriptFile(path, kind, number))
    return result


def _ordered_manuscript_paths(config):
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
    return paths


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
        f"BOOK_CONFIG_SOURCE={shlex.quote(config.source)}",
    ]
    for key, value in config.resolved_paths().items():
        lines.append(f"{_shell_name('BOOK_', key)}={shlex.quote(_plain(value))}")
    for key, value in vars(config.tools).items():
        lines.append(f"{_shell_name('BOOK_TOOLS_', key)}={shlex.quote(_plain(value))}")
    for name, value in shell_paper_values(config).items():
        lines.append(f"{name}={shlex.quote(value)}")
    for name, value in shell_citation_values(config).items():
        lines.append(f"{name}={shlex.quote(value)}")
    return "\n".join(lines)


def shell_citation_values(config):
    sources = config.sources
    return {
        "BOOK_BIBLIOGRAPHY": _plain(sources.bibliography),
        "BOOK_CITATION_STYLE": sources.citation_style,
        "BOOK_CITATION_STYLE_FILE": _plain(sources.citation_style_file),
    }


def shell_paper_values(config):
    paper = config.paper
    return {
        "BOOK_KIND": config.kind,
        "PAPER_TEMPLATE": paper.template,
        "PAPER_ENGINE": paper.engine,
        "PAPER_ANONYMOUS": _plain(paper.anonymous),
        "PAPER_FORMAT": paper.format,
        "PAPER_ABSTRACT": _plain(paper.abstract),
        "PAPER_AUTHORS": _plain(paper_authors_data(paper)),
        "PAPER_ARXIV_CATEGORY": _plain(paper.arxiv_category),
        "PAPER_ABSTRACT_MAX_WORDS": _plain(paper.abstract_max_words),
    }


def paper_authors_data(paper):
    return [vars(author) for author in paper.authors]


def shell_metadata(config):
    return "\n".join(f"{_shell_name('BOOK_META_', key)}={shlex.quote(_metadata_text(value))}"
                     for key, value in sorted(config.book.values.items()))


def _metadata_text(value):
    if isinstance(value, list):
        return ", ".join(_plain(item) for item in value if _plain(item))
    return _plain(value)


def as_dict(config):
    return {
        "root": str(config.root),
        "config_file": _plain(config.config_file) or None,
        "source": config.source,
        "version": config.version,
        "kind": config.kind,
        "book": config.book.values,
        "paper": {**{key: _plain(value) or None if isinstance(value, Path) else value
                     for key, value in vars(config.paper).items() if key != "authors"},
                  "authors": paper_authors_data(config.paper)},
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
    print(f"kind            {config.kind}")
    print(f"read from       {config.source}"
          + (f"  ({config.config_file})" if config.config_file else ""))
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
    "wrong-value": "defect",
    "missing-path": "informational",
    "no-config-file": "informational",
}


def _check(config, output_format):
    report = CheckReport("book-config", CHECK_CLASSES)
    if config.config_file:
        written = read_config_file(config.config_file)
        name = config.config_file.name
        for key in unknown_keys(written):
            report.add(key, "unknown-key", f"{name}: no script reads '{key}'")
    else:
        report.add("-", "no-config-file", f"no book.yaml found; using {config.source}")
    for key, message in wrong_values(config):
        report.add(key, "wrong-value", message)
    for key, value in _paths_to_check(config).items():
        if value is not None and not value.exists():
            report.add(key, "missing-path", str(value))
    return report.emit(output_format)


def _paths_to_check(config):
    paths = {key: value for key, value in config.resolved_paths().items()
             if key != "sources.citation_style_file"}
    if not config.is_paper:
        return paths
    kept = {key: value for key, value in paths.items()
            if not key.startswith(PUBLISHING_KEY_PREFIXES)}
    kept["paper.abstract"] = config.paper.abstract
    return kept


def wrong_values(config):
    paper = config.settings.get("paper") or {}
    found = []
    found.extend(_wrong_citation_values(config))
    if config.kind not in DOCUMENT_KINDS:
        found.append(("kind", f"kind must be one of {', '.join(DOCUMENT_KINDS)}, "
                              f"not {config.settings.get('kind')!r}"))
    if config.paper.engine not in PAPER_ENGINES:
        found.append(("paper.engine", f"paper.engine must be one of {', '.join(PAPER_ENGINES)}, "
                                      f"not {paper.get('engine')!r}"))
    if config.paper.format not in PAPER_FORMATS:
        found.append(("paper.format", f"paper.format must be one of {', '.join(PAPER_FORMATS)}, "
                                      f"not {paper.get('format')!r}"))
    if config.paper.template not in PAPER_BUILT_IN_TEMPLATES:
        found.append(("paper.template", f"paper.template must be one of "
                                        f"{', '.join(PAPER_BUILT_IN_TEMPLATES)}, not "
                                        f"{config.paper.template!r}; a venue not in this list is "
                                        f"added to the plugin as a new built-in template"))
    if _whole_number(paper.get("abstract_max_words"), None) is None:
        found.append(("paper.abstract_max_words", f"paper.abstract_max_words must be a whole "
                                                  f"number above 0, not "
                                                  f"{paper.get('abstract_max_words')!r}"))
    if not isinstance(paper.get("anonymous"), bool):
        found.append(("paper.anonymous", f"paper.anonymous must be true or false, "
                                         f"not {paper.get('anonymous')!r}"))
    authors = paper.get("authors")
    if authors is not None and not isinstance(authors, list):
        found.append(("paper.authors", "paper.authors must be a list"))
    for item in authors if isinstance(authors, list) else []:
        if _paper_author(item) is None:
            found.append(("paper.authors", f"every paper author needs a name, got {item!r}"))
    return found


def _wrong_citation_values(config):
    found = []
    style = config.sources.citation_style
    if style not in CITATION_STYLES:
        found.append(("sources.citation_style", f"sources.citation_style must be one of "
                                                f"{', '.join(CITATION_STYLES)}, not {style!r}"))
    style_file = config.sources.citation_style_file
    if style_file is not None and not style_file.is_file():
        found.append(("sources.citation_style_file", f"sources.citation_style_file names a file "
                                                     f"that does not exist: {style_file}"))
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Show the book's configuration: paths, metadata, coined terms and "
                    "manuscript files, from book.yaml.",
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
    check = commands.add_parser("check", help="unknown keys and missing paths")
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
                    print(f"{key}\t{_metadata_text(value)}")
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
    run_main(main)
