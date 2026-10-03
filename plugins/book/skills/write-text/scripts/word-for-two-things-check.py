#!/usr/bin/env python3
"""Flag container nouns ("framework", "system", "approach") used in two senses.

A container noun is dangerous when the manuscript uses it both for outside things (a named
method, school or product the reader already knows) and for the book's own ideas. The reader gets no signal that the word changed its
meaning, so the book's own bundle blurs with the outside one (rule 2.4).

For each watched word, every use in prose (not code, not tables) is classified by its context,
five words each side inside one sentence:
    external           the context names one of the book's outside names
    self-referential   the context points at the book ("this book", "I propose") or at one
                       of the book's own terms
    neutral            neither
A word is flagged when it has at least one external and one self-referential use.

The book's own terms are its coined terms (`terms.families`) plus
`terms.watch_words.container_terms.book_terms`. The outside names come from
`terms.watch_words.container_terms.outside_names` (for example [Montessori, Weight Watchers]
in a book on learning or on food); a name with a capital letter matches only as written, one
in lower case matches in any case. With no outside names there is nothing to compare against,
and the check prints SKIPPED. `terms.watch_words.container_terms.watchlist` replaces the
default list of watched words. This is a recall-first surfacer: expect false
positives; the author judges each case. Findings are advisory, so the exit code is 0 unless
the check could not run (2).
"""

import argparse
import contextlib
import io
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from book_files import (ConfigError, SAMPLE_BOOK, add_config_arguments, coined_words,
                        config_for_targets, is_english_book, markdown_files,
                        skipped_for_language, tool_failed, watch_words)
from terminal_colors import CYAN, GREEN, NC, RED, YELLOW

WATCHLIST = [
    ("framework", "frameworks"),
    ("mechanism", "mechanisms"),
    ("approach", "approaches"),
    ("system", "systems"),
    ("structure", "structures"),
    ("tool", "tools"),
    ("discipline", "disciplines"),
]

OUTSIDE_NAME_PATTERNS = []

SELF_REF_PHRASES = [
    r"\bthis\s+book\b",
    r"\bthe\s+book\b",
    r"\bbook['\u2019]s\b",
    r"\bthis\s+chapter\b",
    r"\bthis\s+section\b",
    r"\bour\s+(framework|approach|mechanism|system|structure|tool|discipline)\b",
    r"\bmy\s+(framework|approach|mechanism|system|structure|tool|discipline)\b",
    r"\bpresented\s+(here|in\s+this)\b",
    r"\bdeveloped\s+(here|in\s+this)\b",
    r"\bi\s+(develop|propose|present|build|offer|argue)\b",
    r"\bwe\s+(develop|propose|present|build|offer|argue)\b",
]

BOOK_TERMS = set()


CONTEXT_WORDS = 5
CONTEXT_SNIPPET_LEN = 90


def strip_code_and_tables(text):
    out = []
    in_code = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            out.append("")
            continue
        if in_code:
            out.append("")
            continue
        if stripped.startswith("|"):
            out.append("")
            continue
        out.append(line)
    return "\n".join(out)


def strip_inline_markdown(line):
    line = re.sub(r"`([^`]+)`", r"\1", line)
    line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
    line = re.sub(r"\*+", "", line)
    line = re.sub(r"_+", "", line)
    line = re.sub(r"^#+\s*", "", line)
    return line


SENTENCE_BREAK = re.compile(r"[.!?](?=\s+[A-Z\"'(])")


def extract_context(line, match_start, match_end):
    left = line[:match_start]
    right = line[match_end:]

    last_break_end = 0
    for m in SENTENCE_BREAK.finditer(left):
        last_break_end = m.end()
    left = left[last_break_end:]

    first_break = SENTENCE_BREAK.search(right)
    if first_break:
        right = right[: first_break.end()]

    left_words = re.findall(r"\S+", left)[-CONTEXT_WORDS:]
    right_words = re.findall(r"\S+", right)[:CONTEXT_WORDS]
    matched = line[match_start:match_end]
    return " ".join(left_words + [matched] + right_words).strip()


def outside_name_pattern(name):
    flags = 0 if any(character.isupper() for character in name) else re.IGNORECASE
    return re.compile(r"(?<![\w])" + re.escape(name) + r"(?![\w])", flags)


def classify_context(context):
    if any(pattern.search(context) for pattern in OUTSIDE_NAME_PATTERNS):
        return "external"
    ctx_lower = context.lower()
    lower_tokens = set(re.findall(r"[a-z0-9.+#]+", ctx_lower))
    for pat in SELF_REF_PHRASES:
        if re.search(pat, ctx_lower):
            return "self-referential"
    if lower_tokens & BOOK_TERMS:
        return "self-referential"
    return "neutral"


def find_occurrences(path):
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"{RED}Error reading {path}: {e}{NC}", file=sys.stderr)
        return []

    scrubbed = strip_code_and_tables(raw)
    occurrences = []

    forms = []
    for entry in WATCHLIST:
        canonical = entry[0]
        for form in entry:
            forms.append((form, canonical))
    form_pattern = re.compile(
        r"\b(" + "|".join(re.escape(f) for f, _ in forms) + r")\b",
        re.IGNORECASE,
    )
    form_to_canonical = {f.lower(): c for f, c in forms}

    for line_no, line in enumerate(scrubbed.splitlines(), start=1):
        if not line.strip():
            continue
        clean = strip_inline_markdown(line)
        for m in form_pattern.finditer(clean):
            form = m.group(1).lower()
            canonical = form_to_canonical[form]
            context = extract_context(clean, m.start(), m.end())
            sense = classify_context(context)
            occurrences.append(
                {
                    "file": str(path),
                    "line": line_no,
                    "word": canonical,
                    "form": form,
                    "context": context,
                    "sense": sense,
                }
            )
    return occurrences


def group_by_word(occurrences):
    groups = {}
    for occ in occurrences:
        groups.setdefault(occ["word"], []).append(occ)
    return groups


def snippet(text, limit=CONTEXT_SNIPPET_LEN):
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def format_occurrence(occ, indent="    "):
    loc = f"{CYAN}{occ['file']}:{occ['line']}{NC}"
    return f"{indent}{loc} \"{snippet(occ['context'])}\""


def report_word(word, occs, verbose):
    by_sense = {"external": [], "self-referential": [], "neutral": []}
    for o in occs:
        by_sense[o["sense"]].append(o)

    external = by_sense["external"]
    self_ref = by_sense["self-referential"]
    neutral = by_sense["neutral"]
    flagged = bool(external) and bool(self_ref)

    if not flagged and not verbose:
        return False

    print(f"word: {word}")
    if external:
        print(f"  external sense (N={len(external)}):")
        for o in external:
            print(format_occurrence(o))
    if self_ref:
        print(f"  self-referential sense (N={len(self_ref)}):")
        for o in self_ref:
            print(format_occurrence(o))
    if verbose and neutral:
        print(f"  neutral (N={len(neutral)}):")
        for o in neutral:
            print(format_occurrence(o))

    if flagged:
        print(
            f"  {RED}[WARNING]{NC} Same word in 2 distinct senses. "
            f"Consider renaming self-referential uses."
        )
    print()
    return flagged


def apply_book_words(config):
    settings = watch_words(config, "container_terms")
    BOOK_TERMS.clear()
    BOOK_TERMS.update(coined_words(config, roles=("primary", "antonym", "borrowed")))
    BOOK_TERMS.update(str(term).lower() for term in settings.get("book_terms") or [])
    OUTSIDE_NAME_PATTERNS[:] = [outside_name_pattern(str(name))
                                for name in settings.get("outside_names") or [] if str(name)]
    watchlist = settings.get("watchlist")
    if watchlist:
        WATCHLIST[:] = [tuple([entry]) if isinstance(entry, str) else tuple(entry)
                        for entry in watchlist]


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("paths", nargs="*", help="files or folders (default: the manuscript)")
    parser.add_argument("--verbose", action="store_true", help="show every use, also neutral")
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
        apply_book_words(config)
        files = markdown_files(options.paths, config)
    except (ConfigError, FileNotFoundError) as error:
        return tool_failed(str(error), "word-for-two-things-check")
    if not is_english_book(config):
        return skipped_for_language(config, "word-for-two-things-check")
    if not OUTSIDE_NAME_PATTERNS:
        print("SKIPPED   word-for-two-things-check: no outside names to compare against "
              "(terms.watch_words.container_terms.outside_names is empty in book.yaml)")
        return 0
    return report(files, options.verbose, options.stats)


def report(files, verbose, stats_only):
    all_occurrences = []
    for path in files:
        all_occurrences.extend(find_occurrences(Path(path)))
    files_scanned = len(files)
    groups = group_by_word(all_occurrences)
    if stats_only:
        print(f"Files scanned: {files_scanned}")
        print(f"Total occurrences: {len(all_occurrences)}")
        print("\nPer word:")
        for word, occs in sorted(groups.items(), key=lambda x: -len(x[1])):
            ext = sum(1 for o in occs if o["sense"] == "external")
            sr = sum(1 for o in occs if o["sense"] == "self-referential")
            nt = sum(1 for o in occs if o["sense"] == "neutral")
            flag = f" {RED}[FLAG]{NC}" if ext and sr else ""
            print(
                f"  {word:<12} total={len(occs):4d}  ext={ext:3d}  "
                f"self={sr:3d}  neutral={nt:3d}{flag}"
            )
        return 0

    flag_count = 0
    for word in sorted(groups.keys()):
        if report_word(word, groups[word], verbose):
            flag_count += 1

    if flag_count == 0:
        print(
            f"{GREEN}No word used for two things found "
            f"({files_scanned} files scanned).{NC}"
        )
        return 0

    print(
        f"{RED}Flagged {flag_count} container-term(s) used in multiple senses "
        f"in {files_scanned} file(s).{NC}"
    )
    print(f"{YELLOW}Note: expect false positives. Author reviews each case.{NC}")
    return 0


def self_test():
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exit_code = run(["--config", str(SAMPLE_BOOK / "book.yaml"),
                         str(SAMPLE_BOOK / "manuscript" / "110-chapter-1.md")])
    text = output.getvalue()
    failures = []
    if exit_code != 0:
        failures.append(f"exit {exit_code}, expected 0 (findings are advisory)")
    if "word: framework" not in text or "[WARNING]" not in text:
        failures.append("'framework' in two senses was not flagged")
    skipped = io.StringIO()
    with contextlib.redirect_stdout(skipped):
        skipped_exit = run(["--config", str(SAMPLE_BOOK / "book.yaml"), "--set",
                            "terms.watch_words.container_terms.outside_names=[]",
                            str(SAMPLE_BOOK / "manuscript" / "110-chapter-1.md")])
    if skipped_exit != 0 or not skipped.getvalue().rstrip().splitlines()[-1].startswith("SKIPPED"):
        failures.append("a book with no outside names was not SKIPPED")
    for line in failures:
        print(f"FAIL  {line}")
    print(f"self-test: {'PASS' if not failures else str(len(failures)) + ' failure(s)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
