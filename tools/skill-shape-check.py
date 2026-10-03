#!/usr/bin/env python3
"""Maintainer tool: every skill of the plugin has the same shape.

Checks each skills/<name>/SKILL.md: the frontmatter holds exactly `name` and a folded
`description: >-` block, the name is the folder name, the file stays under the line limit,
it always has a `## Modes` section (a skill with no modes says so there), and every call
into the plugin goes through ${CLAUDE_PLUGIN_ROOT} (never a relative `scripts/...` path after
python3 or bash).
Exit 0 when every skill has the shape, 1 when one does not.
"""

import argparse
import re
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1] / "plugins" / "book"
LINE_LIMIT = 300
FRONTMATTER = re.compile(r"\A---\nname: ([a-z-]+)\ndescription: >-\n((?:  \S.*\n)+)---\n")
RELATIVE_CALL = re.compile(r"\b(?:python3|bash)\s+\"?(?:\./|\.\./|scripts/|lib/)")


def problems_of(skill_md):
    text = skill_md.read_text(encoding="utf-8")
    folder = skill_md.parent.name
    found = []
    frontmatter = FRONTMATTER.match(text)
    if not frontmatter:
        found.append("frontmatter is not exactly `name:` and a `description: >-` block")
    elif frontmatter.group(1) != folder:
        found.append(f"name {frontmatter.group(1)!r} is not the folder name {folder!r}")
    lines = text.count("\n")
    if lines > LINE_LIMIT:
        found.append(f"{lines} lines, over {LINE_LIMIT}")
    if "## Modes" not in text:
        found.append("no `## Modes` section")
    for number, line in enumerate(text.splitlines(), start=1):
        if RELATIVE_CALL.search(line):
            found.append(f"line {number}: call without ${{CLAUDE_PLUGIN_ROOT}}: {line.strip()[:70]}")
    return found


def main(argv=None):
    argparse.ArgumentParser(description=__doc__.split("\n\n")[0]).parse_args(argv)
    total = 0
    for skill_md in sorted(PLUGIN.glob("skills/*/SKILL.md")):
        for problem in problems_of(skill_md):
            print(f"{skill_md.parent.name}\t{problem}")
            total += 1
    print(f"TOTAL  {total} problem(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
