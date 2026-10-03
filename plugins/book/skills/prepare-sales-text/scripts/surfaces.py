import fnmatch
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[3] / "lib"
sys.path.insert(0, str(LIB_DIR))

from book_config import KIND_FRONT_MATTER, manuscript_files

ALLOWED_STORE_TAGS = ("br", "p", "b", "em", "i", "u", "h4", "h5", "h6", "ol", "ul", "li")

HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
HTML_TAG = re.compile(r"<[^>]+>")
HTML_BOLD = re.compile(r"<(b|strong)>(.*?)</\1>", re.S | re.I)
MARKDOWN_BOLD = re.compile(r"\*\*(.+?)\*\*", re.S)
MARKDOWN_ITALIC = re.compile(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", re.S)
MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+")
MARKDOWN_TITLE = re.compile(r"^#\s+")
HARD_BREAK = re.compile(r"\\\n")
ADJACENT_BOLD = re.compile(r"\*\*\s+\*\*")
BLOCKQUOTE = re.compile(r"^>\s?")
RAW_BLOCK_LINE = re.compile(r"^(\\|```|<!--|-->|:::)")
SENTENCE_END = re.compile(r"[.!?][\"'”’)]*$")


@dataclass
class Surface:
    name: str
    path: Path
    raw: str
    plain: str
    bold_spans: list = field(default_factory=list)

    @property
    def blocks(self):
        return text_blocks(self.plain)

    @property
    def words(self):
        return word_count(self.plain)


def sales_text_setting(config, name, default=None):
    value = config.get(f"sales_text.{name}", None)
    return default if value is None or value == "" else value


def sales_text_list(config, name):
    value = sales_text_setting(config, name, [])
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value or []]


def sales_text_path(config, name):
    return getattr(config.sales_text, name)


def strip_html_comments(markup):
    return HTML_COMMENT.sub("", markup)


def store_body(markup):
    return strip_html_comments(markup).strip()


def html_to_plain(markup):
    body = strip_html_comments(markup)
    body = re.sub(r"<li>(.*?)</li>", lambda match: "- " + match.group(1).strip(), body,
                  flags=re.S)
    body = re.sub(r"</(p|h[1-6]|ul|ol)>", "\n\n", body)
    body = HTML_TAG.sub("", body)
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r" *\n *", "\n", body)
    return re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"


def markdown_source(text):
    body = HARD_BREAK.sub("\n", strip_html_comments(text).replace("\r\n", "\n"))
    lines = []
    for line in body.splitlines():
        stripped = BLOCKQUOTE.sub("", line.strip())
        if MARKDOWN_TITLE.match(stripped):
            continue
        lines.append(stripped)
    return ADJACENT_BOLD.sub(" ", "\n".join(lines))


def markdown_to_plain(text):
    body = markdown_source(text)
    lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if RAW_BLOCK_LINE.match(stripped):
            continue
        stripped = MARKDOWN_HEADING.sub("", stripped)
        stripped = MARKDOWN_BOLD.sub(r"\1", stripped)
        stripped = MARKDOWN_ITALIC.sub(r"\1", stripped)
        stripped = re.sub(r"^[*+]\s+", "- ", stripped)
        lines.append(stripped)
    joined = "\n".join(lines)
    joined = re.sub(r"[ \t]+", " ", joined)
    return re.sub(r"\n{3,}", "\n\n", joined).strip() + "\n"


def html_bold_spans(markup):
    body = strip_html_comments(markup)
    spans = []
    for match in HTML_BOLD.finditer(body):
        inside_list_item = body.rfind("<li>", 0, match.start()) > body.rfind("</li>", 0,
                                                                           match.start())
        if inside_list_item:
            continue
        spans.append(" ".join(HTML_TAG.sub("", match.group(2)).split()))
    return spans


def markdown_bold_spans(text):
    body = markdown_source(text)
    spans = []
    for line_block in re.split(r"\n\s*\n", body):
        if re.match(r"^\s*[-*+]\s", line_block):
            continue
        spans.extend(" ".join(match.group(1).split()) for match in MARKDOWN_BOLD.finditer(line_block))
    return spans


def text_blocks(plain):
    blocks = []
    for block in re.split(r"\n\s*\n", plain.strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if lines and all(line.startswith("- ") for line in lines):
            blocks.extend(line[2:] for line in lines)
        elif lines:
            blocks.append(" ".join(lines))
    return blocks


def word_count(text):
    return len(text.split())


def is_full_sentence(span):
    return bool(SENTENCE_END.search(span.strip())) and span.strip()[:1].isupper()


def read_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def first_paragraph(markdown_text):
    for block in re.split(r"\n\s*\n", markdown_source(markdown_text)):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        lines = [line for line in lines
                 if not MARKDOWN_HEADING.match(line) and not RAW_BLOCK_LINE.match(line)]
        if lines:
            return markdown_to_plain(" ".join(lines)).strip()
    return ""


def preface_path(config):
    if config.sales_text.preface:
        return config.sales_text.preface
    for item in manuscript_files(config, [KIND_FRONT_MATTER]):
        if "preface" in item.path.name.lower():
            return item.path
    return None


def load_back_cover(config):
    path = sales_text_path(config, "back_cover")
    if path is None or not path.is_file():
        return None
    raw = read_text(path)
    return Surface("back-cover", path, raw, markdown_to_plain(raw), markdown_bold_spans(raw))


def load_store_description(config, path=None):
    path = Path(path) if path else sales_text_path(config, "amazon")
    if path is None or not path.is_file():
        return None
    raw = read_text(path)
    return Surface("store-description", path, raw, html_to_plain(raw), html_bold_spans(raw))


def load_ebook_description(config):
    value = config.book.get("description")
    if not value:
        return None
    text = " ".join(str(value).split())
    source = config.config_file or config.fallback_file or config.root
    return Surface("ebook-description", source, text, text + "\n", [])


def load_preface_opening(config):
    path = preface_path(config)
    if path is None or not path.is_file():
        return None
    opening = first_paragraph(read_text(path))
    if not opening:
        return None
    return Surface("preface-opening", path, opening, opening + "\n", [])


def load_surfaces(config, store_path=None):
    loaders = (
        ("back-cover", lambda: load_back_cover(config)),
        ("store-description", lambda: load_store_description(config, store_path)),
        ("ebook-description", lambda: load_ebook_description(config)),
        ("preface-opening", lambda: load_preface_opening(config)),
    )
    found, missing = [], []
    for name, loader in loaders:
        surface = loader()
        if surface is None:
            missing.append(name)
        else:
            found.append(surface)
    return found, missing


def load_file_as_surface(path):
    path = Path(path)
    raw = read_text(path)
    if path.suffix.lower() in (".html", ".htm"):
        return Surface(path.name, path, raw, html_to_plain(raw), html_bold_spans(raw))
    if path.suffix.lower() in (".md", ".markdown"):
        return Surface(path.name, path, raw, markdown_to_plain(raw), markdown_bold_spans(raw))
    return Surface(path.name, path, raw, raw.strip() + "\n", [])


def matches_any(name, patterns):
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)
