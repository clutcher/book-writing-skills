import re
from dataclasses import dataclass, field

from book_config import GLOSSARY_HEADING_SEPARATOR, GLOSSARY_LOCATION_PATTERN
from citation_key import FENCE_LINE

DEFAULT_HEADING_SEPARATOR = GLOSSARY_HEADING_SEPARATOR
DEFAULT_LOCATION_PATTERN = GLOSSARY_LOCATION_PATTERN

FIELD_CANONICAL_DEFINITION = "Canonical definition"
FIELD_INVARIANTS = "Invariants"
TO_CURATE = "[TO CURATE]"

ENTRY_HEADING = re.compile(r"^###\s+(.+?)\s*$")
NAME_TOKEN_SEPARATOR = re.compile(r"[-_\s]+")
FIELD_LINE = re.compile(r"^\*\*([^*]+?):\*\*\s*(.*)$")

ALSO_FORM = re.compile(r"^(.+?)\s*\(\s*also:\s*(.+?)\s*\)\s*$")
ABBREVIATION_FORM = re.compile(r"^(.+?)\s*\(([A-Z][A-Za-z]+)\)\s*$")
QUALIFIER_FORM = re.compile(r"^(.+?)\s*\([^)]+\)\s*$")


@dataclass
class GlossaryNotation:
    heading_separator: str
    location_pattern: re.Pattern


@dataclass
class GlossaryEntry:
    term: str
    location: str
    line_number: int
    fields: dict = field(default_factory=dict)

    @property
    def canonical_definition(self):
        return self.fields.get(FIELD_CANONICAL_DEFINITION, "")

    @property
    def invariants(self):
        return self.fields.get(FIELD_INVARIANTS, "")

    @property
    def search_forms(self):
        return search_forms_of(self.term)


def config_value(config, dotted_key, default):
    value = config.get(dotted_key, None)
    return default if value in (None, "") else value


def notation_from_config(config, heading_separator=None, location_pattern=None):
    separator = heading_separator or config_value(
        config, "glossary_format.heading_separator", DEFAULT_HEADING_SEPARATOR)
    pattern = location_pattern or config_value(
        config, "glossary_format.location_pattern", DEFAULT_LOCATION_PATTERN)
    return GlossaryNotation(separator, re.compile(pattern, re.IGNORECASE))


def default_notation():
    return GlossaryNotation(DEFAULT_HEADING_SEPARATOR,
                            re.compile(DEFAULT_LOCATION_PATTERN, re.IGNORECASE))


def split_heading(heading, notation):
    parts = [part.strip() for part in heading.split(notation.heading_separator)]
    if len(parts) == 1:
        return parts[0], ""
    if len(parts) == 2:
        return parts[0], parts[1]
    qualifiers = " ".join(reversed(parts[1:-1]))
    return f"{qualifiers} {parts[0]}", parts[-1]


def prose_lines(text):
    lines = []
    in_fence = False
    for line in text.splitlines():
        if FENCE_LINE.match(line):
            in_fence = not in_fence
            lines.append("")
            continue
        lines.append("" if in_fence else line)
    return lines


def parse_glossary(text, notation):
    entries = []
    for number, line in enumerate(prose_lines(text), 1):
        heading = ENTRY_HEADING.match(line)
        if heading:
            term, location = split_heading(heading.group(1), notation)
            entries.append(GlossaryEntry(term, location, number))
            continue
        field_line = FIELD_LINE.match(line)
        if field_line and entries:
            entries[-1].fields.setdefault(field_line.group(1).strip(), field_line.group(2).strip())
    return entries


def search_forms_of(term):
    text = term.strip()
    also = ALSO_FORM.match(text)
    if also:
        return _unique_forms([also.group(1), also.group(2)])
    abbreviation = ABBREVIATION_FORM.match(text)
    if abbreviation:
        return _unique_forms([abbreviation.group(1), abbreviation.group(2)])
    qualified = QUALIFIER_FORM.match(text)
    if qualified:
        return _unique_forms([qualified.group(1)])
    return _unique_forms([text])


def _unique_forms(forms):
    seen = set()
    unique = []
    for form in (form.strip() for form in forms):
        if form and form.lower() not in seen:
            seen.add(form.lower())
            unique.append(form)
    return unique


def known_forms(entries):
    return {form.lower() for entry in entries for form in entry.search_forms} | \
        {entry.term.lower() for entry in entries}


def name_tokens(text):
    return [token for token in NAME_TOKEN_SEPARATOR.split(text.lower()) if token]


def names_the_file(word, manuscript_file):
    wanted = name_tokens(word)
    tokens = name_tokens(manuscript_file.path.stem)
    return any(tokens[start:start + len(wanted)] == wanted
               for start in range(len(tokens) - len(wanted) + 1))


def locate_definition(location, notation, manuscript_files):
    found = notation.location_pattern.match(location or "")
    if not found:
        return None
    groups = found.groupdict()
    if groups.get("chapter"):
        number = int(groups["chapter"])
        return next((index for index, item in enumerate(manuscript_files)
                     if item.chapter == number), None)
    if groups.get("file"):
        return next((index for index, item in enumerate(manuscript_files)
                     if names_the_file(groups["file"], item)), None)
    return None
