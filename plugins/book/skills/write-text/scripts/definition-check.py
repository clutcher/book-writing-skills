#!/usr/bin/env python3
"""Check that every bolded definition blockquote names a term in the book glossary.

The book states its formal definitions as blockquotes that open with the defined term in bold:

    > **A cover crop** is a crop sown to protect and feed the soil, not to be harvested.

Every such bolded term must trace to a glossary heading (the term of a `### term -- where`
heading of the glossary file, `rules.glossary` in the book config, read by lib/glossary.py
with the book's `glossary_format.heading_separator`, so this skill and the review-ideas skill agree). A bolded term with no glossary entry is drift: a definition was reworded away from its
entry, or a new term arrived without one. On a manuscript in step with its glossary this check
reports nothing; it fires when the two part.

Scope, kept narrow on purpose:
    - only single-line blockquotes; a run of two or more ">" lines is a quotation
    - only blockquotes that open with a bold span; a bare blockquote states a position
      (a thesis, a mnemonic) and is never flagged, and no bold is ever added to it
So the check cannot find a missing definition; it only keeps bolded terms traceable.

Matching is tolerant: a leading article, a trailing colon, stop words and parentheses are
dropped, and a match holds when either side's significant words are a subset of the other's
("Soil is fertile" matches "fertility (fertile soil)").

--propose is the helper for bringing new material into the convention: it lists every
blockquote and proposes which span to bold (kinds: is, means, to-is, colon, predicate,
quote, other). It changes nothing.

Exit codes: 0 no drift, 1 drift found, 2 the check could not run.
"""

import argparse
import contextlib
import io
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from book_files import (ConfigError, SAMPLE_BOOK, add_config_arguments, config_for_targets,
                        markdown_files, tool_failed)
from terminal_colors import CYAN, GREEN, NC, RED, YELLOW
from glossary import notation_from_config, parse_glossary

PREDICATE_TAILS = (" when ", " by ", " if ")
QUOTE_PREFIXES = (re.compile(r"^Rule\s+\d+\b"),)
PREDICATE_EXCLUDED_WORDS = {"a", "an", "the"}

STOP_WORDS = {
    "a", "an", "the",
    "of", "to", "is", "are", "was", "were",
    "when", "that", "which", "and", "or", "in", "on", "for", "with",
    "also",
}



def load_glossary_terms(glossary_path, notation):
    text = glossary_path.read_text(encoding="utf-8")
    return [entry.term for entry in parse_glossary(text, notation) if entry.term]


def tokenize(text):
    tokens = []
    for raw in text.lower().split():
        cleaned = raw.strip(".,:;!?\"'()[]")
        if cleaned:
            tokens.append(cleaned)
    return tokens


def strip_leading_article(text):
    return re.sub(r"^(a|an|the)\s+", "", text.strip(), flags=re.IGNORECASE)


def significant_word_list(text):
    text = strip_leading_article(text)
    seen = []
    for t in tokenize(text):
        if t not in STOP_WORDS and t not in seen:
            seen.append(t)
    return seen


def significant_words(text):
    return set(significant_word_list(text))


def glossary_term_variants(term):
    with_paren = term.replace("(", " ").replace(")", " ")
    without_paren = re.sub(r"\([^)]*\)", " ", term)
    variants = []
    for candidate in (with_paren, without_paren):
        words = significant_words(candidate)
        if words and words not in variants:
            variants.append(words)
    return variants


def match_term(bolded_list, glossary):
    bolded_words = set(bolded_list)
    head = bolded_list[0] if bolded_list else None
    best = None
    best_key = None
    for raw_term in glossary:
        for term_words in glossary_term_variants(raw_term):
            if not term_words:
                continue
            if term_words <= bolded_words or bolded_words <= term_words:
                symdiff = len(term_words ^ bolded_words)
                head_match = 1 if head in term_words else 0
                overlap = len(term_words & bolded_words)
                key = (-symdiff, head_match, overlap)
                if best_key is None or key > best_key:
                    best = raw_term
                    best_key = key
    return best


def find_single_line_bold_blockquotes(text):
    lines = text.splitlines()
    n = len(lines)
    i = 0
    while i < n:
        stripped = lines[i].strip()
        if not stripped.startswith(">"):
            i += 1
            continue

        run_start = i
        while i < n and lines[i].strip().startswith(">"):
            i += 1
        run = lines[run_start:i]

        if len(run) != 1:
            continue

        line_no = run_start + 1
        content = re.sub(r"^\s*>\s?", "", run[0])
        m = re.match(r"^\*\*(.+?)\*\*", content)
        if not m:
            continue
        yield line_no, m.group(1).strip(), run[0].strip()


def normalize_bolded_phrase(phrase):
    phrase = phrase.strip().rstrip(":.,;!?")
    return phrase


def check_file(path, glossary):
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"{RED}Error reading {path}: {e}{NC}", file=sys.stderr)
        return [], []

    findings = []
    checked = []

    for line_no, phrase, full_line in find_single_line_bold_blockquotes(text):
        normalized = normalize_bolded_phrase(phrase)
        bolded_list = significant_word_list(normalized)
        matched = match_term(bolded_list, glossary) if bolded_list else None

        record = {
            "file": str(path),
            "line": line_no,
            "phrase": phrase,
            "full_line": full_line,
            "matched_term": matched,
        }
        checked.append(record)
        if matched is None:
            findings.append(record)

    return findings, checked


def format_finding(f):
    loc = f"{CYAN}{f['file']}:{f['line']}{NC}"
    return "\n".join(
        [
            f"{loc} [DRIFT: bolded term not traceable to glossary]",
            f"  bolded phrase: {f['phrase']}",
            f"  blockquote: {f['full_line'][:100]}",
            f"  action: reword to match a glossary entry, or add a registry entry for a new term",
        ]
    )


def format_checked(c):
    loc = f"{CYAN}{c['file']}:{c['line']}{NC}"
    if c["matched_term"]:
        return f"{loc} {GREEN}OK{NC} '{c['phrase']}' -> glossary '{c['matched_term']}'"
    return f"{loc} {RED}UNMATCHED{NC} '{c['phrase']}'"


def propose_bold_span(text):
    for pattern in QUOTE_PREFIXES:
        if pattern.match(text):
            return "quote", None, text
    found = re.match(r"^(To\s+[^.]+?)\s+is\s+to\s+", text)
    if found:
        return "to-is", found.group(1), text[found.end(1):]
    found = re.match(r"^([A-Z][^:]+?):\s+", text)
    if found:
        return "colon", found.group(1) + ":", text[found.end():]
    found = re.match(r"^([A-Z][\w\- ]+?)\s+means\s+", text)
    if found:
        return "means", found.group(1), text[found.end(1):]
    found = re.match(r"^([A-Z][\w\- ]+?)\s+is\s+(\w+)", text)
    if found:
        subject, word = found.group(1), found.group(2)
        rest = text[found.end():]
        if (any(tail in " " + rest for tail in PREDICATE_TAILS)
                and word.lower() not in PREDICATE_EXCLUDED_WORDS):
            return "predicate", f"{subject} is {word}", rest
        return "is", subject, text[found.end(1):]
    return "other", None, text


def print_proposals(files):
    for path in files:
        for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
            if not line.startswith("> "):
                continue
            body = line[2:].strip()
            if not body:
                continue
            kind, span, rest = propose_bold_span(body)
            short_rest = (rest[:60] + "...") if len(rest) > 60 else rest
            print(f"{Path(path).name}:{number}\t{kind:9s}\t[{span or ''}]\t| {short_rest}")
    return 0


def has_entry_headings(glossary_path):
    inside_fence = False
    for line in Path(glossary_path).read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("```"):
            inside_fence = not inside_fence
        elif not inside_fence and line.startswith("### "):
            return True
    return False


def check_definitions(files, glossary_path, notation, verbose):
    glossary = load_glossary_terms(glossary_path, notation)
    if not glossary and not has_entry_headings(glossary_path):
        print(f"SKIPPED   no glossary entries yet: {glossary_path}")
        return 0
    if not glossary:
        return tool_failed(f"no terms parsed from the glossary: {glossary_path}",
                           "definition-check")
    all_findings, all_checked = [], []
    for path in files:
        findings, checked = check_file(Path(path), glossary)
        all_findings.extend(findings)
        all_checked.extend(checked)
    print(f"Glossary: {glossary_path} ({len(glossary)} terms)")
    if verbose:
        for checked in all_checked:
            print(format_checked(checked))
        print()
    if not all_findings:
        print(f"{GREEN}No blockquote drift found ({len(all_checked)} bolded blockquotes "
              f"checked, {len(files)} files scanned).{NC}")
        return 0
    for finding in all_findings:
        print(format_finding(finding))
        print()
    print(f"{RED}Flagged {len(all_findings)} bolded blockquote(s) not traceable to the "
          f"glossary in {len(files)} file(s).{NC}")
    print(f"{YELLOW}Reword the definition to match a glossary entry, or add a glossary entry "
          f"for a new term.{NC}")
    return 1


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("paths", nargs="*", help="files or folders (default: the manuscript)")
    parser.add_argument("--verbose", action="store_true",
                        help="show every bolded blockquote and the glossary term it matched")
    parser.add_argument("--glossary", metavar="FILE",
                        help="glossary file (default: rules.glossary in the book config)")
    parser.add_argument("--propose", action="store_true",
                        help="list blockquotes and propose the span to bold; changes nothing")
    parser.add_argument("--self-test", action="store_true",
                        help="check this script against the fixture books and exit")
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
        return tool_failed(str(error), "definition-check")
    if options.propose:
        return print_proposals(files)
    glossary_path = Path(options.glossary) if options.glossary else config.rules.glossary
    if not glossary_path or not glossary_path.is_file():
        return tool_failed(f"glossary not found: {glossary_path}; set rules.glossary in "
                           f"book.yaml or pass --glossary FILE", "definition-check")
    return check_definitions(files, glossary_path, notation_from_config(config),
                             options.verbose)


def self_test():
    failures = []
    cases = [
        (SAMPLE_BOOK / "manuscript" / "110-chapter-1.md", 1, "A poke test", "A float test"),
    ]
    for chapter, expected_exit, flagged, passed in cases:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = run([str(chapter)])
        text = output.getvalue()
        if exit_code != expected_exit:
            failures.append(f"{chapter.parent.parent.name}: exit {exit_code}, "
                            f"expected {expected_exit}")
        if flagged not in text:
            failures.append(f"{chapter.parent.parent.name}: {flagged!r} was not flagged")
        if passed and f"bolded phrase: {passed}" in text:
            failures.append(f"{chapter.parent.parent.name}: {passed!r} is in the glossary")
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        run(["--propose", str(SAMPLE_BOOK / "manuscript" / "110-chapter-1.md")])
    if output.getvalue().count("110-chapter-1.md:") != 2:
        failures.append("--propose did not list both blockquotes of the fixture chapter")
    for line in failures:
        print(f"FAIL  {line}")
    print(f"self-test: {'PASS' if not failures else str(len(failures)) + ' failure(s)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
