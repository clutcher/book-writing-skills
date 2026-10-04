#!/usr/bin/env python3
import argparse
import re
import sys
sys.dont_write_bytecode = True
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from bisect import bisect_right

from citation_key import UnkeyableName, derive_label, sort_position

FIELD_ORDER = (
    "author", "editor", "title", "booktitle", "journal", "series", "edition", "volume",
    "number", "eid", "chapter", "pages", "pagetotal", "publisher", "institution", "school",
    "type", "address", "howpublished", "month", "year", "date", "origdate", "language", "doi",
    "isbn", "url", "note", "crossref",
)

IDENTITY_FIELDS = frozenset(FIELD_ORDER)

NAME_FIELDS = ("author", "editor")

PRESERVED_TYPES = ("comment", "string", "preamble")

EDITOR_LABEL_TYPES = ("book", "inbook")

EDITOR_ONLY_LABEL_TYPES = ("proceedings",)

OTHERS = "others"

FIELD_NAME = re.compile(r"[A-Za-z][\w\-:.+]*")

ENTRY_TYPE = re.compile(r"[A-Za-z]+")

INDENT = "  "


class BibliographyError(ValueError):
    def __init__(self, message, line=None):
        super().__init__(f"line {line}: {message}" if line else message)
        self.line = line


@dataclass
class Name:
    first: str
    von: str
    last: str
    jr: str
    corporate: bool = False
    others: bool = False

    @property
    def surname(self):
        if self.corporate:
            return re.sub(r"[\s-]+", "", plain_text(self.last))
        return " ".join(part for part in (plain_text(self.von), plain_text(self.last)) if part)


@dataclass
class LabelNames:
    surnames: list
    and_others: bool
    year: str
    source_field: str


@dataclass
class BibEntry:
    entry_type: str
    key: str
    fields: dict = field(default_factory=dict)
    expressions: set = field(default_factory=set)
    repeated_fields: list = field(default_factory=list)
    line: int = 0

    def field(self, name):
        return self.fields.get(name.lower())

    def plain(self, *names):
        for name in names:
            value = self.field(name)
            if value:
                return plain_text(value)
        return ""

    def names(self, field_name):
        value = self.field(field_name)
        return parse_names(value) if value else []

    @property
    def authors(self):
        return self.names("author")

    @property
    def editors(self):
        return self.names("editor")

    def ordered_fields(self):
        known = [name for name in FIELD_ORDER if name in self.fields]
        other = [name for name in self.fields if name not in IDENTITY_FIELDS]
        return known + other


@dataclass
class PreservedBlock:
    text: str
    line: int = 0


@dataclass
class Bibliography:
    items: list = field(default_factory=list)
    line_ending: str = "\n"
    byte_order_mark: bool = False
    duplicate_keys: list = field(default_factory=list)
    path: Path = None

    @property
    def entries(self):
        found = {}
        for item in self.items:
            if isinstance(item, BibEntry) and item.key not in found:
                found[item.key] = item
        return found

    @property
    def keys(self):
        return list(self.entries)

    def entry(self, key):
        return self.entries.get(key)

    def add(self, entry):
        if entry.key in self.entries:
            raise BibliographyError(f"the key {entry.key} is already in the bibliography")
        for index, item in enumerate(self.items):
            if isinstance(item, BibEntry) and sort_position(item.key) > sort_position(entry.key):
                self.items.insert(index, entry)
                return entry
        self.items.append(entry)
        return entry

    def remove(self, key):
        before = len(self.items)
        self.items = [item for item in self.items
                      if not (isinstance(item, BibEntry) and item.key == key)]
        return len(self.items) != before

    def rename(self, old_key, new_key):
        if new_key in self.entries:
            raise BibliographyError(f"the key {new_key} is already in the bibliography")
        entry = self.entry(old_key)
        if entry is None:
            raise BibliographyError(f"no entry with the key {old_key}")
        entry.key = new_key
        for child in self.entries.values():
            parent_key = child.field("crossref")
            if parent_key and parent_key.lower() == old_key.lower():
                child.fields["crossref"] = new_key
        return entry

    def crossref_parent(self, entry):
        parent_key = entry.field("crossref")
        if not parent_key:
            return None
        return next((found for key, found in self.entries.items()
                     if key.lower() == parent_key.strip().lower() and found is not entry), None)

    def with_inherited_fields(self, entry):
        parent = self.crossref_parent(entry)
        if parent is None:
            return entry
        fields = dict(entry.fields)
        for name, value in parent.fields.items():
            if name != "crossref" and not fields.get(name):
                fields[name] = value
        return BibEntry(entry.entry_type, entry.key, fields, set(entry.expressions),
                        list(entry.repeated_fields), entry.line)


def read_bibliography(path):
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise BibliographyError(f"{path} is not UTF-8: {error}") from error
    bibliography = parse_bibliography(text)
    bibliography.path = Path(path)
    return bibliography


def read_identities(path):
    if path is None or not Path(path).is_file():
        return {}
    return read_bibliography(path).entries


def parse_bibliography(text):
    byte_order_mark = text.startswith("\ufeff")
    if byte_order_mark:
        text = text[1:]
    line_ending = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n")
    bibliography = Bibliography(line_ending=line_ending, byte_order_mark=byte_order_mark)
    _Reader(text, bibliography).read()
    return bibliography


def format_bibliography(bibliography):
    blocks = [format_entry(item) if isinstance(item, BibEntry) else item.text.strip("\n")
              for item in bibliography.items]
    blocks = [block for block in blocks if block.strip()]
    return "\n\n".join(blocks) + "\n" if blocks else ""


def write_bibliography(path, bibliography):
    text = format_bibliography(bibliography)
    if bibliography.byte_order_mark:
        text = "\ufeff" + text
    with open(path, "w", encoding="utf-8", newline=bibliography.line_ending) as handle:
        handle.write(text)


def format_entry(entry):
    lines = [f"@{entry.entry_type}{{{entry.key},"]
    for name in entry.ordered_fields():
        value = entry.fields[name]
        written = value if name in entry.expressions else "{" + value + "}"
        lines.append(f"{INDENT}{name} = {written},")
    lines.append("}")
    return "\n".join(lines)


def make_entry(entry_type, key, fields):
    if not ENTRY_TYPE.fullmatch(entry_type or ""):
        raise BibliographyError(f"{entry_type!r} is not an entry type: letters only")
    cleaned = {}
    for name, value in fields.items():
        if value is None or not str(value).strip():
            continue
        if not FIELD_NAME.fullmatch(name):
            raise BibliographyError(f"{name!r} is not a field name: a letter, then letters, "
                                    f"digits and _ - : . + only")
        if not braces_balance(str(value)):
            raise BibliographyError(f"the {name} value has braces that do not pair up: "
                                    f"{value!r}")
        cleaned[name.lower()] = _collapse(str(value))
    return BibEntry(entry_type.lower(), key, cleaned)


def braces_balance(text):
    depth = 0
    for character in text:
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def label_names(entry, bibliography=None):
    if bibliography is not None:
        entry = bibliography.with_inherited_fields(entry)
    source = _label_source(entry)
    if source is None:
        return None
    names = entry.names(source)
    people = [name for name in names if not name.others]
    if not people:
        return None
    and_others = len(people) < len(names)
    return LabelNames([name.surname for name in people], and_others,
                      _label_year(entry.field("year")), source)


def expected_key(entry, bibliography=None):
    found = label_names(entry, bibliography)
    if found is None:
        return None
    return derive_label(found.surnames, found.year, found.and_others)


def _label_source(entry):
    if entry.entry_type in EDITOR_ONLY_LABEL_TYPES:
        return "editor" if entry.field("editor") else None
    if entry.field("author"):
        return "author"
    if entry.entry_type in EDITOR_LABEL_TYPES and entry.field("editor"):
        return "editor"
    return None


def _label_year(value):
    if not value:
        return "--"
    digits = re.sub(r"[^0-9]", "", plain_text(value))
    return digits[-2:] if len(digits) >= 2 else "--"


def parse_names(value):
    return [_parse_name(part) for part in _split_at_depth_zero(value, r"\s+and\s+")
            if part.strip()]


def _parse_name(text):
    text = text.strip()
    if text.lower() == OTHERS:
        return Name("", "", OTHERS, "", others=True)
    if _is_one_group(text):
        return Name("", "", text[1:-1].strip(), "", corporate=True)
    parts = [part.strip() for part in _split_at_depth_zero(text, r",")]
    if len(parts) == 1:
        return _name_without_comma(_words(parts[0]))
    von, last = _von_and_last(_words(parts[0]))
    if len(parts) == 2:
        return Name(parts[1], von, last, "")
    return Name(", ".join(parts[2:]), von, last, parts[1])


def _name_without_comma(words):
    if not words:
        return Name("", "", "", "")
    lower = [index for index, word in enumerate(words[:-1]) if _is_lower_word(word)]
    if not lower:
        return Name(" ".join(words[:-1]), "", words[-1], "")
    start, end = lower[0], lower[-1] + 1
    return Name(" ".join(words[:start]), " ".join(words[start:end]), " ".join(words[end:]), "")


def _von_and_last(words):
    if not words:
        return "", ""
    end = len(words) - 1
    while end > 0 and not _is_lower_word(words[end - 1]):
        end -= 1
    return " ".join(words[:end]), " ".join(words[end:])


FOREIGN_LETTER_COMMANDS = {
    "oe": "œ", "OE": "Œ", "ae": "æ", "AE": "Æ", "aa": "å", "AA": "Å", "o": "ø", "O": "Ø",
    "l": "ł", "L": "Ł", "ss": "ß", "i": "ı", "j": "ȷ",
}

ACCENT_MARKS = {
    '"': "\u0308", "'": "\u0301", "`": "\u0300", "^": "\u0302", "~": "\u0303",
    "=": "\u0304", ".": "\u0307", "u": "\u0306", "v": "\u030c", "H": "\u030b",
    "c": "\u0327", "k": "\u0328", "r": "\u030a", "d": "\u0323", "b": "\u0331",
}


def _is_lower_word(word):
    depth, index = 0, 0
    while index < len(word):
        character = word[index]
        if character == "{":
            if depth == 0 and word[index + 1:index + 2] == "\\":
                return _special_character_is_lower(word[index + 1:])
            depth += 1
        elif character == "}":
            depth = max(depth - 1, 0)
        elif depth == 0 and character.isalpha():
            return character.islower()
        index += 1
    return False


def _special_character_is_lower(text):
    command = re.match(r"\\([A-Za-z]+|.)", text)
    if not command:
        return False
    name = command.group(1)
    if name in FOREIGN_LETTER_COMMANDS:
        return FOREIGN_LETTER_COMMANDS[name].islower()
    rest = re.search(r"[A-Za-z]", text[command.end():])
    return bool(rest) and rest.group(0).islower()


def plain_text(value):
    text = value or ""
    text = re.sub(r"\\([\"'`^~=.uvHckrdb])\s*\{?\s*(\\?[A-Za-z])\s*\}?", _accented, text)
    text = re.sub(r"\\([A-Za-z]{1,2})(?![A-Za-z])\s*(?:\{\})?",
                  lambda found: FOREIGN_LETTER_COMMANDS.get(found.group(1), found.group(0)),
                  text)
    text = text.replace("\\&", "&").replace("~", " ")
    text = re.sub(r"\\[A-Za-z]+\s*", "", text)
    text = text.replace("{", "").replace("}", "")
    return unicodedata.normalize("NFC", re.sub(r"\s+", " ", text).strip())


def _accented(found):
    accent, letter = found.groups()
    if accent in "uvHckrdb" and found.group(0)[2:3] not in ("{", " "):
        return found.group(0)
    base = {"\\i": "i", "\\j": "j"}.get(letter, letter)
    return base + ACCENT_MARKS[accent]


def _words(text):
    return [word for word in _split_at_depth_zero(text, r"[\s~]+") if word]


def _is_one_group(text):
    if not (text.startswith("{") and text.endswith("}")):
        return False
    depth = 0
    for index, character in enumerate(text):
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0 and index != len(text) - 1:
                return False
    return True


def _split_at_depth_zero(text, separator):
    pattern = re.compile(separator, re.IGNORECASE)
    parts, start, depth, index = [], 0, 0, 0
    while index < len(text):
        character = text[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
        elif depth == 0:
            found = pattern.match(text, index)
            if found and found.end() > index:
                parts.append(text[start:index])
                start = index = found.end()
                continue
        index += 1
    parts.append(text[start:])
    return parts


def _collapse(text):
    return re.sub(r"\s+", " ", text).strip()


class _Reader:
    def __init__(self, text, bibliography):
        self.text = text
        self.bibliography = bibliography
        self.position = 0
        self.seen = set()
        self.line_starts = [0] + [index + 1 for index, character in enumerate(text)
                                  if character == "\n"]

    def line_at(self, position):
        return bisect_right(self.line_starts, position)

    def read(self):
        pending_start = 0
        while True:
            start = self._next_item_start(self.position)
            if start is None:
                self._keep(pending_start, len(self.text))
                return
            self._keep(pending_start, start)
            self.position = start
            self._read_item()
            pending_start = self.position

    def _next_item_start(self, position):
        pattern = re.compile(r"@[ \t]*([A-Za-z]+)[ \t\n]*[{(]")
        found = pattern.search(self.text, position)
        return found.start() if found else None

    def _keep(self, start, end):
        chunk = self.text[start:end]
        if chunk.strip():
            self.bibliography.items.append(PreservedBlock(chunk.strip("\n"), self.line_at(start)))

    def _read_item(self):
        start = self.position
        found = re.compile(r"@[ \t]*([A-Za-z]+)[ \t\n]*([{(])").match(self.text, start)
        entry_type = found.group(1).lower()
        opener = found.group(2)
        closer = "}" if opener == "{" else ")"
        self.position = found.end()
        if entry_type in PRESERVED_TYPES:
            end = self._matching_close(found.end() - 1, opener, closer)
            self.bibliography.items.append(
                PreservedBlock(self.text[start:end + 1], self.line_at(start)))
            self.position = end + 1
            return
        self._read_entry(entry_type, closer, self.line_at(start))

    def _matching_close(self, open_position, opener, closer):
        depth = 0
        for index in range(open_position + 1, len(self.text)):
            character = self.text[index]
            if character == "{":
                depth += 1
            elif character == "}" and depth > 0:
                depth -= 1
            elif character == closer and depth == 0:
                return index
        raise BibliographyError("an item is never closed", self.line_at(open_position))

    def _read_entry(self, entry_type, closer, line):
        key_match = re.compile(r"\s*([^,\s{}()]*)\s*([,}\)])").match(self.text, self.position)
        if not key_match:
            raise BibliographyError("an entry has no key", line)
        key = key_match.group(1)
        if not key:
            raise BibliographyError(f"an @{entry_type} entry has no key", line)
        entry = BibEntry(entry_type, key, line=line)
        self.position = key_match.end()
        if key_match.group(2) != ",":
            self._finish_entry(entry)
            return
        while True:
            self._skip_space()
            if self._at(closer):
                self.position += 1
                break
            name_match = re.compile(r"([A-Za-z][\w\-:.+]*)\s*=\s*").match(self.text, self.position)
            if not name_match:
                raise BibliographyError(f"{key}: a field name was expected here",
                                        self.line_at(self.position))
            self.position = name_match.end()
            name = name_match.group(1).lower()
            value, expression = self._read_value(key, closer)
            if name in entry.fields:
                entry.repeated_fields.append(name)
            else:
                entry.fields[name] = value
                if expression:
                    entry.expressions.add(name)
            self._skip_space()
            if self._at(","):
                self.position += 1
                continue
            if self._at(closer):
                self.position += 1
                break
            raise BibliographyError(f"{key}: a comma or the end of the entry was expected",
                                    self.line_at(self.position))
        self._finish_entry(entry)

    def _finish_entry(self, entry):
        if entry.key in self.seen:
            self.bibliography.duplicate_keys.append(entry.key)
        self.seen.add(entry.key)
        self.bibliography.items.append(entry)

    def _at(self, character):
        return self.text.startswith(character, self.position)

    def _skip_space(self):
        while self.position < len(self.text) and self.text[self.position].isspace():
            self.position += 1

    def _read_value(self, key, closer):
        parts = []
        while True:
            self._skip_space()
            parts.append(self._read_value_part(key, closer))
            self._skip_space()
            if self._at("#"):
                self.position += 1
                continue
            break
        if len(parts) == 1 and parts[0][0] in ("braced", "quoted", "number"):
            return _collapse(parts[0][1]), False
        return " # ".join(raw for _, _, raw in parts), True

    def _read_value_part(self, key, closer):
        start = self.position
        if self._at("{"):
            end = self._balanced_end(start, key)
            self.position = end + 1
            return "braced", self.text[start + 1:end], self.text[start:end + 1]
        if self._at('"'):
            end = self._quoted_end(start, key)
            self.position = end + 1
            content = self.text[start + 1:end]
            return "quoted", content, self.text[start:end + 1]
        found = re.compile(r"[^\s,#{}\"()=]+").match(self.text, start)
        if not found:
            raise BibliographyError(f"{key}: a field value was expected",
                                    self.line_at(start))
        self.position = found.end()
        word = found.group(0)
        return ("number" if word.isdigit() else "macro"), word, word

    def _balanced_end(self, start, key):
        depth = 0
        for index in range(start, len(self.text)):
            character = self.text[index]
            if character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                if depth == 0:
                    return index
        raise BibliographyError(f"{key}: a brace is never closed", self.line_at(start))

    def _quoted_end(self, start, key):
        depth = 0
        for index in range(start + 1, len(self.text)):
            character = self.text[index]
            if character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
            elif character == '"' and depth == 0:
                return index
        raise BibliographyError(f"{key}: a quote is never closed", self.line_at(start))


def main():
    parser = argparse.ArgumentParser(
        description="Read the book's .bib file and show its entries, the label each entry's "
                    "names give, or the file in its standard written form.")
    parser.add_argument("bibliography", help="the .bib file")
    parser.add_argument("--keys", action="store_true",
                        help="print each key with the alpha label its names give")
    parser.add_argument("--fix", action="store_true",
                        help="write the file back in its standard form (default: dry run, "
                             "say whether it would change)")
    args = parser.parse_args()
    try:
        bibliography = read_bibliography(args.bibliography)
    except (OSError, BibliographyError) as error:
        sys.stderr.write(f"bibliography: {error}\n")
        return 2
    if args.keys:
        for key, entry in bibliography.entries.items():
            try:
                label = expected_key(entry, bibliography)
            except UnkeyableName:
                label = None
            print(f"{key}\t{label or '-'}")
        return 0
    original = Path(args.bibliography).read_bytes().decode("utf-8").replace("\r\n", "\n")
    standard = format_bibliography(bibliography)
    if original.lstrip("\ufeff") == standard:
        print(f"{args.bibliography}: already in the standard form "
              f"({len(bibliography.entries)} entries)")
        return 0
    if args.fix:
        write_bibliography(args.bibliography, bibliography)
        print(f"{args.bibliography}: written in the standard form")
        return 0
    print(f"{args.bibliography}: not in the standard form; pass --fix to write it")
    return 1


if __name__ == "__main__":
    sys.exit(main())
