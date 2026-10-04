import re

from citation_key import FENCE_LINE
from citations import find_citations


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


def cited_keys(line):
    return [citation.key for citation in find_citations(line)]
