#!/usr/bin/env python3
import argparse
import difflib
import re
import sys
sys.dont_write_bytecode = True

import surfaces

DESCRIPTION = """Show two versions of a piece of copy side by side, word by word, so the author
sees exactly what changed before anything is applied.

Removed words are shown as [-old words-] and added words as {+new words+}; --markdown shows
the new version with only the changed words in bold instead, which is the form to paste into
a message for the author. Also prints words, blocks and the longest block for each version.

Works on .md (markdown), .html and plain text. Used by the 'review' mode's version
comparison and by every 'write' proposal. A report: exit 0, or 2 if a file cannot be read."""

TOKEN = re.compile(r"\S+|\n")


def tokens(text):
    return TOKEN.findall(text)


def word_diff(old_text, new_text, markdown):
    old_tokens, new_tokens = tokens(old_text), tokens(new_text)
    matcher = difflib.SequenceMatcher(a=old_tokens, b=new_tokens, autojunk=False)
    pieces = []
    for operation, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        old_part = " ".join(old_tokens[old_start:old_end])
        new_part = " ".join(new_tokens[new_start:new_end])
        if operation == "equal":
            pieces.append(new_part)
            continue
        if markdown:
            if new_part.strip():
                pieces.append("**%s**" % new_part.strip())
            continue
        if old_part.strip():
            pieces.append("[-%s-]" % old_part.strip())
        if new_part.strip():
            pieces.append("{+%s+}" % new_part.strip())
    return re.sub(r" ?\n ?", "\n", " ".join(pieces)).strip() + "\n"


def summary(label, surface):
    blocks = surface.blocks
    longest = max((surfaces.word_count(block) for block in blocks), default=0)
    return f"{label}: {surface.words} words, {len(blocks)} blocks, longest block {longest} words"


def build_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("old", help="the current version")
    parser.add_argument("new", help="the proposed version")
    parser.add_argument("--markdown", action="store_true",
                        help="print the new version with the changed words in bold")
    return parser


def main():
    arguments = build_parser().parse_args()
    try:
        old = surfaces.load_file_as_surface(arguments.old)
        new = surfaces.load_file_as_surface(arguments.new)
    except OSError as error:
        sys.stderr.write(f"copy-diff: {error}\n")
        return 2
    print(summary("old", old))
    print(summary("new", new))
    print()
    print(word_diff(old.plain, new.plain, arguments.markdown), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
