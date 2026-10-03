#!/usr/bin/env python3
"""Mark what changed in a markdown file since an older version, for a diff build.

Words that are new or changed inside a prose block are wrapped in
<span class="added">; a block that is new, or a code block with any change, is
wrapped in a "::: added" fenced div. Removed text is not shown. The result goes to
stdout; the diff-mode.lua filter turns the marks into highlights. Used by
build-book.sh --changes-since.
"""

import argparse
import difflib
import re
import sys
sys.dont_write_bytecode = True
from pathlib import Path


FENCE_RE = re.compile(r"^(```+|~~~+)")
TOKEN_RE = re.compile(r"(\s+|\S+)")


def split_into_blocks(text):
    lines = text.splitlines(keepends=True)
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == "":
            i += 1
            continue
        m = FENCE_RE.match(line)
        if m:
            fence = m.group(1)
            buf = [line]
            i += 1
            while i < len(lines):
                buf.append(lines[i])
                stripped = lines[i].rstrip()
                if stripped == fence or stripped.startswith(fence + " "):
                    i += 1
                    break
                i += 1
            blocks.append(("code", "".join(buf)))
            continue
        buf = [line]
        i += 1
        while i < len(lines) and lines[i].strip() != "" and not FENCE_RE.match(lines[i]):
            buf.append(lines[i])
            i += 1
        blocks.append(("prose", "".join(buf)))
    return blocks


def tokenize_words(text):
    return TOKEN_RE.findall(text)


def word_diff_prose(old_text, new_text):
    old_tokens = tokenize_words(old_text)
    new_tokens = tokenize_words(new_text)
    matcher = difflib.SequenceMatcher(a=old_tokens, b=new_tokens, autojunk=False)
    n = len(new_tokens)
    added = [False] * n
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("insert", "replace"):
            for k in range(j1, j2):
                added[k] = True

    i = 0
    while i < n:
        if not added[i]:
            i += 1
            continue
        j = i
        while j < n and added[j]:
            j += 1
        while i < j and new_tokens[i].isspace():
            added[i] = False
            i += 1
        k = j - 1
        while k >= i and new_tokens[k].isspace():
            added[k] = False
            k -= 1
        i = j

    i = 0
    while i < n:
        if added[i]:
            i += 1
            continue
        j = i
        while j < n and not added[j]:
            j += 1
        if i > 0 and j < n and added[i - 1] and added[j]:
            if all(new_tokens[k].isspace() for k in range(i, j)):
                for k in range(i, j):
                    added[k] = True
        i = j

    out_parts = []
    i = 0
    while i < n:
        if added[i]:
            j = i
            while j < n and added[j]:
                j += 1
            out_parts.append(f'<span class="added">{"".join(new_tokens[i:j])}</span>')
            i = j
        else:
            out_parts.append(new_tokens[i])
            i += 1
    return "".join(out_parts)


def wrap_block_added(block_text):
    if not block_text.endswith("\n"):
        block_text = block_text + "\n"
    return f"::: added\n\n{block_text}\n:::\n"


SIMILARITY_THRESHOLD = 0.3


def best_match_index(new_text, old_range):
    best_idx = -1
    best_ratio = 0.0
    for i, (_, old_text) in enumerate(old_range):
        ratio = difflib.SequenceMatcher(a=old_text, b=new_text, autojunk=False).quick_ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_idx = i
    return best_idx, best_ratio


def handle_replace_range(old_range, new_range):
    out = []
    available = list(range(len(old_range)))
    for new_kind, new_text in new_range:
        if new_kind != "prose":
            out.append(wrap_block_added(new_text))
            continue
        prose_olds = [(idx, old_range[idx]) for idx in available if old_range[idx][0] == "prose"]
        if not prose_olds:
            out.append(wrap_block_added(new_text))
            continue
        best_idx_local, best_ratio = best_match_index(
            new_text, [b for _, b in prose_olds]
        )
        if best_ratio < SIMILARITY_THRESHOLD:
            out.append(wrap_block_added(new_text))
            continue
        chosen_idx = prose_olds[best_idx_local][0]
        old_text = old_range[chosen_idx][1]
        available.remove(chosen_idx)
        out.append(word_diff_prose(old_text, new_text))
    return out


def diff_blocks(old_blocks, new_blocks):
    old_keys = [b[1] for b in old_blocks]
    new_keys = [b[1] for b in new_blocks]
    matcher = difflib.SequenceMatcher(a=old_keys, b=new_keys, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(j1, j2):
                out.append(new_blocks[k][1])
        elif tag == "insert":
            for k in range(j1, j2):
                out.append(wrap_block_added(new_blocks[k][1]))
        elif tag == "replace":
            out.extend(handle_replace_range(old_blocks[i1:i2], new_blocks[j1:j2]))
    return "\n\n".join(part.rstrip("\n") for part in out) + "\n"


def read_old_text(old_path):
    if old_path in ("", "-") or not Path(old_path).exists():
        return ""
    return Path(old_path).read_text(encoding="utf-8")


def marked_text(old_text, new_text):
    if old_text == new_text:
        return new_text
    if not old_text.strip():
        return wrap_block_added(new_text)
    return diff_blocks(split_into_blocks(old_text), split_into_blocks(new_text))


def self_test():
    cases = [
        ("unchanged text stays as it is", "One two.\n", "One two.\n", "One two.\n"),
        ("a new file is one added block", "", "Fresh text.\n", "::: added\n\nFresh text.\n\n:::\n"),
        ("a changed word is marked inline", "The cat sat.\n", "The dog sat.\n",
         'The <span class="added">dog</span> sat.\n'),
        ("a new paragraph is an added block", "First.\n", "First.\n\nSecond.\n",
         "First.\n\n::: added\n\nSecond.\n\n:::\n"),
        ("a changed code block is added whole", "```\na = 1\n```\n", "```\na = 2\n```\n",
         "::: added\n\n```\na = 2\n```\n\n:::\n"),
    ]
    failures = [(name, marked_text(old, new), expected) for name, old, new, expected in cases
                if marked_text(old, new) != expected]
    for name, got, expected in failures:
        print(f"FAIL  {name}: got {got!r}, expected {expected!r}")
    print(f"diff-preprocess self-test: {len(cases) - len(failures)}/{len(cases)} passed")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("old_file", nargs="?", help="the older version; '-' or a missing file means none")
    parser.add_argument("new_file", nargs="?", help="the version to render")
    parser.add_argument("--self-test", action="store_true", help="run the built-in tests")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.old_file or not args.new_file:
        parser.error("give OLD_FILE and NEW_FILE")
    try:
        new_text = Path(args.new_file).read_text(encoding="utf-8")
    except OSError as problem:
        sys.stderr.write(f"diff-preprocess: {problem}\n")
        return 2
    sys.stdout.write(marked_text(read_old_text(args.old_file), new_text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
