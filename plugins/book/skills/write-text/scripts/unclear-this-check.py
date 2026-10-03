#!/usr/bin/env python3
"""Flag paragraphs that open with a demonstrative whose noun has no antecedent.

A paragraph that opens with "This/That/These/Those/The + abstract noun" must find that noun in
the last sentence of the paragraph before (rules 2.2 and 12.2). The nouns are general ones
(approach, idea, problem, method, ...); in a file that holds a code block, nouns of code
(code, function, class, implementation, ...) are checked too. Headings do not break the
chain, so the search crosses them. The opener is accepted when:
    - the sentence carries a location word (above, below, following, previous, ...)
    - a code block sits earlier in the same section and the noun points at code
      (example, snippet, function, ...)
    - a list sits earlier in the same section and the noun points at a list
      (step, point, item, rule, question)
    - the noun appears in the last sentence of the previous text paragraph
    - the noun phrase carries its own complement ("The X of Y", "The X that ...")

This is a recall-first surfacer: expect false positives; the author judges each case.
Findings are advisory, so the exit code is 0 unless the check could not run (2).
"""

import argparse
import contextlib
import io
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

from book_files import (ConfigError, SAMPLE_BOOK, add_config_arguments, config_for_targets,
                        is_english_book, markdown_files, skipped_for_language, tool_failed)
from terminal_colors import CYAN, GREEN, NC, RED, YELLOW

ABSTRACT_NOUNS = {
    "approach", "approaches",
    "technique", "techniques",
    "pattern", "patterns",
    "principle", "principles",
    "mechanism", "mechanisms",
    "idea", "ideas",
    "concept", "concepts",
    "observation", "observations",
    "question", "questions",
    "problem", "problems",
    "issue", "issues",
    "distinction", "distinctions",
    "split", "splits",
    "difference", "differences",
    "change", "changes",
    "challenge", "challenges",
    "insight", "insights",
    "point", "points",
    "rule", "rules",
    "definition", "definitions",
    "property", "properties",
    "characteristic", "characteristics",
    "consequence", "consequences",
    "effect", "effects",
    "reason", "reasons",
    "case", "cases",
    "example", "examples",
    "result", "results",
    "trade-off", "trade-offs",
    "tradeoff", "tradeoffs",
    "limit", "limits",
    "boundary", "boundaries",
    "step", "steps",
    "method", "methods",
}

NOUNS_OF_FILES_WITH_CODE = {
    "code", "snippet", "snippets",
    "listing", "listings",
    "implementation", "implementations",
    "function", "functions",
    "class", "classes",
    "refactor", "refactors",
}

CODE_REFERENTIAL_NOUNS = {
    "example", "examples",
    "code", "snippet", "snippets",
    "listing", "listings",
    "implementation", "implementations",
    "method", "methods",
    "function", "functions",
    "class", "classes",
    "refactor", "refactors",
}

LIST_REFERENTIAL_NOUNS = {
    "step", "steps",
    "point", "points",
    "item", "items",
    "rule", "rules",
    "question", "questions",
}

LOCATION_MARKER_PATTERN = re.compile(
    r"\b(above|below|following|preceding|previous|next|earlier|later)\b",
    re.IGNORECASE,
)

DEMONSTRATIVES = ("This", "That", "These", "Those", "The")

COMPLEMENT_MARKERS = {
    "of", "between", "behind", "among", "across", "against",
    "that", "which", "where", "whose",
}



def parse_blocks(text):
    blocks = []
    in_code = False
    buf = []
    buf_start = 0
    buf_type = None

    def flush():
        nonlocal buf, buf_start, buf_type
        if buf:
            blocks.append((buf_start, buf_type, "\n".join(buf)))
            buf = []
            buf_type = None

    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()

        if stripped.startswith("```"):
            flush()
            in_code = not in_code
            if in_code:
                blocks.append((i, "code", ""))
            continue
        if in_code:
            continue

        if line.startswith("#") and not line.startswith("#!"):
            flush()
            blocks.append((i, "heading", line))
            continue

        if not stripped:
            flush()
            continue

        if stripped.startswith("|"):
            if buf_type != "table":
                flush()
                buf_type = "table"
                buf_start = i
            buf.append(line)
            continue

        if re.match(r"^\s*([-*+]\s|\d+\.\s)", line):
            if buf_type != "list":
                flush()
                buf_type = "list"
                buf_start = i
            buf.append(line)
            continue

        if stripped.startswith(">"):
            if buf_type != "blockquote":
                flush()
                buf_type = "blockquote"
                buf_start = i
            buf.append(line)
            continue

        if buf_type != "text":
            flush()
            buf_type = "text"
            buf_start = i
        buf.append(line)

    flush()
    return blocks


def strip_markdown_prefix(text):
    return re.sub(r"^(\*+|_+|`+)?\s*", "", text.lstrip())


def first_sentence(para_text):
    cleaned = strip_markdown_prefix(para_text)
    match = re.search(r"[.!?](?=\s+[A-Z])", cleaned)
    if match:
        return cleaned[: match.start() + 1].strip()
    return cleaned.strip()


def last_sentence(para_text):
    cleaned = para_text.strip()
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", cleaned)
    return sentences[-1].strip() if sentences else cleaned


def starts_with_dangling_candidate(sentence, candidate_nouns):
    s = strip_markdown_prefix(sentence)
    for demo in DEMONSTRATIVES:
        pattern = rf"^{demo}\s+([A-Za-z-]+)"
        m = re.match(pattern, s)
        if m:
            noun = m.group(1).lower()
            if noun in candidate_nouns:
                return demo, noun
    return None


def noun_stem(noun):
    if noun.endswith("ss"):
        return noun
    if noun.endswith("ies"):
        return noun[:-3] + "y"
    if noun.endswith("es") and len(noun) > 3:
        return noun[:-2]
    if noun.endswith("s") and len(noun) > 2:
        return noun[:-1]
    return noun


def has_specifying_complement(sentence, demo, noun):
    s = strip_markdown_prefix(sentence)
    words = re.findall(r"[\w'-]+", s)[:10]
    for i, w in enumerate(words[:-1]):
        if w.lower() == demo.lower():
            noun_pos = i + 1
            for j in range(noun_pos + 1, min(noun_pos + 4, len(words))):
                if words[j].lower() in COMPLEMENT_MARKERS:
                    return True
            return False
    return False


def has_antecedent_in_text(noun, context):
    if not context:
        return False
    stem = noun_stem(noun)
    pattern = rf"\b{re.escape(stem)}(s|es|ies)?\b"
    return bool(re.search(pattern, context, re.IGNORECASE))


def check_file(path):
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"{RED}Error reading {path}: {e}{NC}", file=sys.stderr)
        return []

    blocks = parse_blocks(text)
    findings = []
    candidate_nouns = ABSTRACT_NOUNS
    if any(block_type == "code" for _, block_type, _ in blocks):
        candidate_nouns = ABSTRACT_NOUNS | NOUNS_OF_FILES_WITH_CODE

    for i, (line_no, block_type, content) in enumerate(blocks):
        if block_type != "text":
            continue

        first = first_sentence(content)
        candidate = starts_with_dangling_candidate(first, candidate_nouns)
        if not candidate:
            continue
        demo, noun = candidate

        prev_text_context = ""
        had_code_in_section = False
        had_list_in_section = False
        had_table_in_section = False
        text_captured = False
        crossed_heading = False

        for j in range(i - 1, -1, -1):
            prev_line, prev_type, prev_content = blocks[j]
            if prev_type == "heading":
                crossed_heading = True
                continue
            if prev_type == "code" and not crossed_heading:
                had_code_in_section = True
            elif prev_type == "list" and not crossed_heading:
                had_list_in_section = True
            elif prev_type == "table" and not crossed_heading:
                had_table_in_section = True
            elif prev_type == "text" and not text_captured:
                prev_text_context = last_sentence(prev_content)
                text_captured = True
                if crossed_heading:
                    break

        accepted = False

        if LOCATION_MARKER_PATTERN.search(first):
            accepted = True

        elif had_code_in_section and noun in CODE_REFERENTIAL_NOUNS:
            accepted = True

        elif had_list_in_section and noun in LIST_REFERENTIAL_NOUNS:
            accepted = True

        elif has_antecedent_in_text(noun, prev_text_context):
            accepted = True

        elif has_specifying_complement(first, demo, noun):
            accepted = True

        if not accepted:
            findings.append(
                {
                    "file": str(path),
                    "line": line_no,
                    "demo": demo,
                    "noun": noun,
                    "first_sentence": first,
                    "prev_context": prev_text_context,
                    "intervening": [
                        t
                        for t, seen in [
                            ("code", had_code_in_section),
                            ("list", had_list_in_section),
                            ("table", had_table_in_section),
                        ]
                        if seen
                    ],
                }
            )

    return findings


def format_finding(f, verbose):
    loc = f"{CYAN}{f['file']}:{f['line']}{NC}"
    head = f"{loc} [SUSPECT: '{f['demo']} {f['noun']}']"
    if verbose:
        prev = f["prev_context"] or "(no previous text paragraph in scope)"
        intervening = ", ".join(f["intervening"]) if f["intervening"] else "none"
        return "\n".join(
            [
                head,
                f"  prev text sentence: {prev}",
                f"  intervening blocks: {intervening}",
                f"  paragraph start: {f['first_sentence']}",
                f"  expected antecedent: '{f['noun']}' not found in prev sentence",
            ]
        )
    else:
        snippet = f["first_sentence"][:80]
        return f"{head}\n  '{snippet}...'"


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("paths", nargs="*", help="files or folders (default: the manuscript)")
    parser.add_argument("--verbose", action="store_true", help="show the context of each flag")
    parser.add_argument("--stats", action="store_true", help="counts only")
    parser.add_argument("--self-test", action="store_true",
                        help="check this script against the fixture book and exit")
    add_config_arguments(parser)
    return parser.parse_args(argv)


def run(argv):
    options = parse_arguments(argv)
    if options.self_test:
        return self_test()
    try:
        config = config_for_targets(options, options.paths)
        files = markdown_files(options.paths, config)
    except (ConfigError, FileNotFoundError) as error:
        return tool_failed(str(error), "unclear-this-check")
    if not is_english_book(config):
        return skipped_for_language(config, "unclear-this-check")
    return report(files, options.verbose, options.stats)


def report(files, verbose, stats_only):
    all_findings = []
    for path in files:
        all_findings.extend(check_file(Path(path)))
    files_scanned = len(files)
    if stats_only:
        by_file = {}
        for f in all_findings:
            by_file[f["file"]] = by_file.get(f["file"], 0) + 1
        print(f"Files scanned: {files_scanned}")
        print(f"Total flags: {len(all_findings)}")
        if by_file:
            print("\nPer file:")
            for fname, count in sorted(by_file.items(), key=lambda x: -x[1]):
                print(f"  {count:4d}  {fname}")
        return 0

    if not all_findings:
        print(f"{GREEN}No unclear 'this' found ({files_scanned} files scanned).{NC}")
        return 0

    for f in all_findings:
        print(format_finding(f, verbose))
        print()

    print(
        f"{RED}Flagged {len(all_findings)} dangling-demonstrative candidates in {files_scanned} file(s).{NC}"
    )
    print(f"{YELLOW}Note: expect false positives. Author reviews each case.{NC}")
    return 0


def code_noun_failures():
    with_code = ("## Watering\n\n```\nwater(bed)\n```\n\n## Summer\n\n"
                 "The garden needs water every morning in summer.\n\n"
                 "The function decides it.\n")
    failures = []
    with tempfile.TemporaryDirectory() as folder:
        plain = Path(folder) / "plain.md"
        plain.write_text("The garden needs water every morning in summer.\n\n"
                         "The function decides it.\n", encoding="utf-8")
        coded = Path(folder) / "coded.md"
        coded.write_text(with_code, encoding="utf-8")
        if check_file(plain):
            failures.append("'The function' was flagged in a file with no code block")
        if not check_file(coded):
            failures.append("'The function' was not flagged in a file with a code block")
    return failures


def self_test():
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exit_code = run(["--config", str(SAMPLE_BOOK / "book.yaml"),
                         str(SAMPLE_BOOK / "manuscript" / "110-chapter-1.md")])
    text = output.getvalue()
    failures = []
    if exit_code != 0:
        failures.append(f"exit {exit_code}, expected 0 (findings are advisory)")
    if "'The approach'" not in text:
        failures.append("the dangling 'The approach' opener was not flagged")
    if "'The framework'" in text:
        failures.append("'The framework of this book' has a complement and must pass")
    failures.extend(code_noun_failures())
    french = io.StringIO()
    with contextlib.redirect_stdout(french):
        french_exit = run(["--config", str(SAMPLE_BOOK / "book.yaml"), "--set", "book.language=fr",
                           str(SAMPLE_BOOK / "manuscript" / "110-chapter-1.md")])
    if french_exit != 0 or not french.getvalue().startswith("SKIPPED"):
        failures.append("a French book was checked with English rules instead of SKIPPED")
    for line in failures:
        print(f"FAIL  {line}")
    print(f"self-test: {'PASS' if not failures else str(len(failures)) + ' failure(s)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
