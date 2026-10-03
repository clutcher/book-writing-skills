import re
import sys
import tempfile
from pathlib import Path

LIB = Path(__file__).resolve().parents[3] / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from book_config import (METADATA_HEADING, ConfigError, load_config, normalise_metadata_key,
                         read_yaml_subset, settings_from_fallback_file)

INDENT = "  "
FLOW_LIST_WIDTH = 72
PLAIN_UNSAFE_START = ("-", "?", ":", "|", ">", "[", "]", "{", "}", ",", "'", '"', "#", "&", "*",
                      "!", "%", "@", "`")
METADATA_LINE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):[ \t]*(.*?)\s+#\s*(.*)$")


def plain_text(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        return {str(key): plain_text(item) for key, item in value.items()}
    if isinstance(value, list):
        return [plain_text(item) for item in value]
    return str(value)


def quoted(text):
    escaped = (text.replace("\\", "\\\\").replace('"', '\\"')
               .replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r"))
    return f'"{escaped}"'


def reads_back_as(text):
    try:
        return read_yaml_subset(f"value: {text}\n").get("value")
    except ConfigError:
        return object()


def scalar(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if (text and text == text.strip() and plain_text(reads_back_as(text)) == text
            and not text.startswith(PLAIN_UNSAFE_START) and not text.endswith(":")
            and ": " not in text and " #" not in text):
        return text
    return quoted(text)


def flow_item(value):
    if isinstance(value, dict):
        inside = ", ".join(f"{key}: {flow_item(item)}" for key, item in value.items())
        return "{" + inside + "}"
    if isinstance(value, list):
        return "[" + ", ".join(flow_item(item) for item in value) + "]"
    text = scalar(value)
    if not text.startswith('"') and re.search(r"[,:\[\]{}]", text):
        return quoted(str(value))
    return text


def dump(data, comments=None, level=0):
    comments = comments or {}
    blocks = [block_of(key, value, comments, level) for key, value in data.items()]
    return ("\n\n" if level == 0 else "\n").join(blocks)


def block_of(key, value, comments, level):
    pad = INDENT * level
    comment = comments.get(key)
    tail = f"  # {comment}" if comment else ""
    if isinstance(value, dict) and value:
        inner = {name[len(key) + 1:]: text for name, text in comments.items()
                 if name.startswith(key + ".")}
        return f"{pad}{key}:{tail}\n" + dump(value, inner, level + 1)
    if isinstance(value, list) and value:
        flow = f"{pad}{key}: {flow_item(value)}"
        if len(flow) <= FLOW_LIST_WIDTH and not any(isinstance(item, dict) for item in value):
            return flow + tail
        items = "\n".join(f"{pad}{INDENT}- {flow_item(item)}" for item in value)
        return f"{pad}{key}:{tail}\n{items}"
    if isinstance(value, dict):
        return f"{pad}{key}: {{}}{tail}"
    if isinstance(value, list):
        return f"{pad}{key}: []{tail}"
    return f"{pad}{key}: {scalar(value)}{tail}"


def metadata_comments(claude_md_text):
    comments = {}
    inside = False
    for line in claude_md_text.split("\n"):
        if line.rstrip() == METADATA_HEADING:
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        found = METADATA_LINE.match(line) if inside else None
        if found:
            comments.setdefault(normalise_metadata_key(found.group(1)), found.group(3).strip())
    return comments


def settings_from_claude_md(path):
    layer = settings_from_fallback_file(path)
    settings = {"version": 1}
    if layer.get("book"):
        settings["book"] = dict(layer["book"])
    for section in ("manuscript", "work"):
        if layer.get(section):
            settings[section] = dict(layer[section])
    terms = layer.get("terms") or {}
    if terms.get("families") or terms.get("compounds"):
        families = []
        for family in terms.get("families") or []:
            item = {"term": family["term"], "role": family["role"]}
            if family.get("also"):
                item["also"] = list(family["also"])
            families.append(item)
        settings["terms"] = {"families": families, "compounds": list(terms.get("compounds") or [])}
    return settings


def same_values(settings, yaml_text):
    read = read_yaml_subset(yaml_text)
    differences = []

    def walk(expected, found, dotted):
        if isinstance(expected, dict):
            if not isinstance(found, dict):
                differences.append(f"{dotted or 'top level'}: not a mapping in the written file")
                return
            for key, value in expected.items():
                walk(value, found.get(key), f"{dotted}.{key}" if dotted else key)
            return
        if plain_text(expected) != plain_text(found):
            differences.append(f"{dotted}: {plain_text(expected)!r} became {plain_text(found)!r}")

    walk(settings, read, "")
    return differences


def config_values(config):
    return {
        "book": {key: plain_text(value) for key, value in config.book.values.items()},
        "terms": {
            "families": [plain_text(vars(family)) for family in config.terms.families],
            "compounds": list(config.terms.compounds),
        },
        "manuscript.dir": str(config.manuscript.dir),
    }


def new_layout_paths():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder).resolve()
        (root / "book.yaml").write_text("version: 1\n", encoding="utf-8")
        config = load_config(config=root / "book.yaml")
        return {key: relative_or_none(root, value)
                for key, value in config.resolved_paths().items()}


def relative_or_none(root, value):
    if value is None:
        return None
    try:
        return Path(value).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return None


TOP_KEY_LINE = re.compile(r"^([A-Za-z_][\w-]*)[ \t]*:(?:[ \t]+(.*)|[ \t]*)$")
CHILD_KEY_LINE = re.compile(r"^([ \t]+)([A-Za-z_][\w-]*)[ \t]*:(?:[ \t]+(.*)|[ \t]*)$")
LIST_ITEM_LINE = re.compile(r"^[ \t]+-(?:[ \t]|$)")


def indent_of(line):
    return len(line) - len(line.lstrip(" \t"))


def is_blank(line):
    return not line.strip()


def is_comment(line):
    return line.lstrip().startswith("#")


def value_span(line):
    found = TOP_KEY_LINE.match(line)
    group = 2
    if not found:
        found, group = CHILD_KEY_LINE.match(line), 3
    if not found or found.group(group) is None:
        return None
    start = found.start(group)
    kept = strip_comment(line[start:]).rstrip()
    if not kept:
        return None
    return start, start + len(kept)


def strip_comment(text):
    index = 0
    while index < len(text):
        character = text[index]
        if character in ("'", '"') and index == 0:
            end = closing_quote(text, index)
            if end is None:
                return text
            index = end + 1
            continue
        if character == "#" and (index == 0 or text[index - 1] in " \t"):
            return text[:index]
        index += 1
    return text


def closing_quote(text, start):
    quote = text[start]
    index = start + 1
    while index < len(text):
        if quote == '"' and text[index] == "\\":
            index += 2
            continue
        if text[index] == quote:
            if quote == "'" and text[index + 1:index + 2] == "'":
                index += 2
                continue
            return index
        index += 1
    return None


def with_value(line, value):
    span = value_span(line)
    if span is None:
        return line.rstrip() + " " + scalar(value)
    start, end = span
    return line[:start] + scalar(value) + line[end:]


class Child:
    def __init__(self, key, lines):
        self.key = key
        self.lines = lines


class Block:
    def __init__(self, key, lead, head, body):
        self.key = key
        self.lead = lead
        self.head = head
        self.body = body
        self.children = None
        self.child_indent = None

    def split_children(self):
        content = [line for line in self.body if not is_blank(line) and not is_comment(line)]
        if not content or LIST_ITEM_LINE.match(content[0]):
            return
        found = CHILD_KEY_LINE.match(content[0])
        if not found or (value_span(self.head) is not None):
            return
        self.child_indent = indent_of(content[0])
        children, waiting = [], []
        for line in self.body:
            found = CHILD_KEY_LINE.match(line)
            if found and indent_of(line) == self.child_indent and not LIST_ITEM_LINE.match(line):
                children.append(Child(found.group(2), waiting + [line]))
                waiting = []
            elif (is_comment(line) or is_blank(line)) and (not children or
                                                            indent_of(line) <= self.child_indent):
                waiting.append(line)
            elif children:
                children[-1].lines.extend(waiting + [line])
                waiting = []
            else:
                waiting.append(line)
        if not children:
            return
        children[-1].lines.extend(waiting)
        self.children = children

    def child(self, key):
        return next((item for item in self.children or [] if item.key == key), None)

    def lines(self):
        if self.children is None:
            return self.lead + [self.head] + self.body
        inside = [line for child in self.children for line in child.lines]
        return self.lead + [self.head] + inside


class ConfigLines:
    def __init__(self, text):
        self.items = []
        lines = text.split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        index = 0
        loose = []
        while index < len(lines):
            line = lines[index]
            found = TOP_KEY_LINE.match(line)
            if not found:
                loose.append(line)
                index += 1
                continue
            lead = []
            while loose and is_comment(loose[-1]) and indent_of(loose[-1]) == 0:
                lead.insert(0, loose.pop())
            self.items.extend(loose)
            loose = []
            end = index + 1
            last = index
            while end < len(lines) and not TOP_KEY_LINE.match(lines[end]):
                if not is_blank(lines[end]) and indent_of(lines[end]) > 0:
                    last = end
                end += 1
            block = Block(found.group(1), lead, line, lines[index + 1:last + 1])
            block.split_children()
            self.items.append(block)
            index = last + 1
        self.items.extend(loose)

    def blocks(self):
        return [item for item in self.items if isinstance(item, Block)]

    def block(self, key):
        return next((item for item in self.blocks() if item.key == key), None)

    def entry(self, dotted):
        section, _, name = dotted.partition(".")
        block = self.block(section)
        if not name:
            return block
        return block.child(name) if block else None

    def lines_of(self, dotted):
        section, _, name = dotted.partition(".")
        block = self.block(section)
        if not name:
            return block.lead + [block.head] + block.body
        pad = block.child_indent
        return [line[pad:] if line[:pad].strip() == "" else line
                for line in block.child(name).lines]

    def move(self, old, new):
        old_section, _, old_name = old.partition(".")
        new_section, _, new_name = new.partition(".")
        if old_name and new_name and old_section == new_section:
            child = self.entry(old)
            child.key = new_name
            at = next(index for index, line in enumerate(child.lines)
                      if CHILD_KEY_LINE.match(line) and not is_comment(line))
            line = child.lines[at]
            child.lines[at] = line[:indent_of(line)] + new_name + line[indent_of(line) + len(old_name):]
            return
        near = self.block(old_section)
        self.add(new, self.lines_of(old), near)
        self.remove(old)

    def remove(self, dotted):
        section, _, name = dotted.partition(".")
        block = self.block(section)
        if not name:
            self.items[self.items.index(block)] = None
            return block.lead + [block.head] + block.body
        child = block.child(name)
        block.children.remove(child)
        if not block.children:
            self.items[self.items.index(block)] = None
        return [line[block.child_indent:] if line[:block.child_indent].strip() == "" else line
                for line in child.lines]

    def add(self, dotted, lines, near=None):
        section, _, name = dotted.partition(".")
        renamed = renamed_key_line(lines, name or section)
        if not name:
            key_at = next(index for index, line in enumerate(renamed) if TOP_KEY_LINE.match(line)
                          and not is_comment(line))
            self.insert(Block(section, renamed[:key_at], renamed[key_at], renamed[key_at + 1:]),
                        near)
            return
        block = self.block(section)
        if block is None:
            block = Block(section, [], f"{section}:", [])
            block.children, block.child_indent = [], len(INDENT)
            self.insert(block, near)
        if block.children is None:
            raise ConfigError(f"{section}: holds a value, so {dotted} cannot be added under it")
        pad = " " * block.child_indent
        block.children.append(Child(name, [pad + line if line.strip() else line
                                           for line in renamed]))

    def insert(self, block, near):
        if near is not None and near in self.items:
            self.items.insert(self.items.index(near), block)
            return
        while self.items and isinstance(self.items[-1], str) and is_blank(self.items[-1]):
            self.items.pop()
        self.items.extend(["", block])

    def set_value(self, dotted, value):
        entry = self.entry(dotted)
        holder = entry.lines if isinstance(entry, Child) else None
        if holder is None:
            entry.head = with_value(entry.head, value)
            return
        for index, line in enumerate(holder):
            if CHILD_KEY_LINE.match(line) and not is_comment(line):
                holder[index] = with_value(line, value)
                return

    def text(self):
        lines = []
        for item in self.items:
            if item is None:
                continue
            if isinstance(item, Block):
                lines.extend(item.lines())
            elif not (is_blank(item) and (not lines or is_blank(lines[-1]))):
                lines.append(item)
        while lines and is_blank(lines[-1]):
            lines.pop()
        return "\n".join(lines) + "\n"


def renamed_key_line(lines, name):
    result, done = [], False
    for line in lines:
        found = TOP_KEY_LINE.match(line)
        if not done and found and not is_comment(line):
            line = name + line[len(found.group(1)):]
            done = True
        result.append(line)
    return result
