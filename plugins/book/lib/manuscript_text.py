import re

from citation_key import FENCE_LINE, KEY_BODY

KEY = re.compile(rf"^{KEY_BODY}$")
BRACKET = re.compile(r"\[([^\[\]\n]+)\]")
LOCATOR = re.compile(r"^(?:pp?\.|ch\.|chap\.|sec\.|§|fig\.|table|n\.)\s*\S", re.IGNORECASE)


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


def word_count(text):
    without_code = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    without_headings = re.sub(r"^#.*$", "", without_code, flags=re.MULTILINE)
    return len(without_headings.split())


def keys_in_bracket(content):
    parts = [part.strip() for part in content.split(",")]
    keys = [part for part in parts if KEY.match(part)]
    locators = [part for part in parts if LOCATOR.match(part)]
    if keys and len(keys) + len(locators) == len(parts):
        return keys
    return []


def cited_keys(line):
    return [key for bracket in BRACKET.finditer(line) for key in keys_in_bracket(bracket.group(1))]
