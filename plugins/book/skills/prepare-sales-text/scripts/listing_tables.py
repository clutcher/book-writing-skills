import re
from dataclasses import dataclass, field

HEADING = re.compile(r"^(#{2,6})\s+(.+?)\s*#*$")
TABLE_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
DIVIDER_CELL = re.compile(r"^:?-{3,}:?$")
BULLET = re.compile(r"^\s*[-*+]\s+(.+)$")
FENCE = re.compile(r"^\s*```")


@dataclass
class Section:
    title: str
    level: int
    lines: list = field(default_factory=list)


def sections(text):
    found = []
    current = Section("", 0)
    in_fence = False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
        heading = None if in_fence else HEADING.match(line)
        if heading:
            current = Section(heading.group(2).strip(), len(heading.group(1)))
            found.append(current)
        else:
            current.lines.append(line)
    return found


def find_section(text, first_word):
    wanted = first_word.lower()
    for section in sections(text):
        if section.title.lower().split()[:1] == [wanted]:
            return section
    return None


def split_cells(line):
    cells = re.split(r"(?<!\\)\|", TABLE_ROW.match(line).group(1))
    return [cell.strip() for cell in cells]


def first_table(section):
    if section is None:
        return []
    rows, header = [], None
    for line in section.lines:
        if not TABLE_ROW.match(line):
            if header is not None:
                break
            continue
        cells = split_cells(line)
        if header is None:
            header = [cell.lower() for cell in cells]
        elif all(DIVIDER_CELL.match(cell.replace(" ", "")) for cell in cells if cell):
            continue
        else:
            rows.append(dict(zip(header, cells)))
    return rows


def column(row, *names):
    for key, value in row.items():
        if any(key.startswith(name) for name in names):
            return value
    return ""


def bullets(section):
    if section is None:
        return []
    return [match.group(1).strip() for match in (BULLET.match(line) for line in section.lines)
            if match]


def clean_cell(value):
    return value.replace("`", "").replace("**", "").strip()


def is_placeholder(value):
    return value.startswith("<") and value.endswith(">")
