#!/usr/bin/env python3
"""Flag words used in a sense the book has decided to avoid.

A book sometimes drops a framing on purpose. One example: a cookbook that does not describe a
dish as a list of separate "flavours" removes the word, and then a synonym ("note", "taste")
brings the same framing back in. This check lists every use of the watched words that sits in one of the
signal patterns typical of the avoided sense:

    quantifier      single/one/multiple/each/same/different <word>
    decomp-left     separation of / separate / split / mix / isolate <word>s
    possession      has/handles/owns/holds/carries <word>
    possessive      whose <word>
    verb-adj        serve(s) a/an/the <adjective> <word>
    negation        no common/shared/matching <word>
    predicative     predict(s) <word>s
    scope           <word> of the <target>, for the book's own scope_targets
    diverge         <word>s diverge/converge/drift

These signals are built in and fit one kind of avoided sense only: a thing described as a set
of separate, countable parts that can be split, owned or compared (the "counted flavours" kind).
For an avoided sense of another kind, they miss most uses: search for the words directly or add
a rule to the book's own Vale style instead.

The words come from `terms.watch_words.word_sense` in the book config:
    word_sense:
      name: counted flavours                   # what the avoided sense is called
      reason: why the book avoids it
      words: [[flavour, flavours], [note, notes]]
      scope_targets: [dish, sauce, loaf]       # nouns for the scope signal; none: no scope signal

With no words configured there is nothing to check, and the check prints SKIPPED. This is a
recall-first surfacer: expect false positives; the author judges each case. Findings are
advisory, so the exit code is 0 unless the check could not run (2).
"""

import argparse
import contextlib
import io
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from book_files import (ConfigError, SAMPLE_BOOK, add_config_arguments, config_for_targets,
                        markdown_files, tool_failed, watch_words)
from terminal_colors import CYAN, GREEN, NC, RED, YELLOW

WATCHLIST = []
SENSE_NAME = "avoided-sense"

QUANTIFIERS = r"single|one|multiple|many|several|each|every|two|three|four|a\s+single|same|different|the\s+same"
DECOMP_LEFT = r"separation\s+of|separate|split|splits|splitting|mixing|mix|blend|blending|combine|combining|isolate|isolates"
POSSESSION = r"has|have|having|handle|handles|handling|own|owns|owning|hold|holds|holding|carries|carry|takes|takes\s+on|assumes"

SIGNAL_PATTERNS = [
    ("quantifier",  re.compile(rf"\b({QUANTIFIERS})\s+(\w+\s+)?$", re.IGNORECASE)),
    ("decomp-left", re.compile(rf"\b({DECOMP_LEFT})\s+$", re.IGNORECASE)),
    ("possession",  re.compile(rf"\b({POSSESSION})\s+(a|an|the|one|its|their|this|that|many|multiple|several)?\s*$", re.IGNORECASE)),
    ("possessive",  re.compile(rf"\bwhose\s+$", re.IGNORECASE)),
    ("verb-adj",    re.compile(rf"\b(serve|serves|serving)\s+(a|an|the)\s+\w+\s+$", re.IGNORECASE)),
    ("negation",    re.compile(rf"\bno\s+(common|shared|matching)\s+$", re.IGNORECASE)),
    ("predicative", re.compile(rf"\b(predict|predicts|predicting)\s+$", re.IGNORECASE)),
]
SCOPE_RIGHT = []
DIVERGE_RIGHT = re.compile(rf"^\s+(diverge|diverges|diverging|converge|converges|converging|drift|drifts|drifting)\b", re.IGNORECASE)


CONTEXT_WORDS = 6


def strip_code_and_tables(text):
    out = []
    in_code = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            out.append("")
            continue
        if in_code or stripped.startswith("|"):
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
    left_sent = left[last_break_end:]

    first_break = SENTENCE_BREAK.search(right)
    right_sent = right[: first_break.end()] if first_break else right

    left_words = re.findall(r"\S+", left_sent)[-CONTEXT_WORDS:]
    right_words = re.findall(r"\S+", right_sent)[:CONTEXT_WORDS]
    matched = line[match_start:match_end]
    return left_sent, right_sent, " ".join(left_words + [matched] + right_words).strip()


def detect_signals(left_sent, right_sent):
    hits = []
    for name, pat in SIGNAL_PATTERNS:
        if pat.search(left_sent):
            hits.append(name)
    if any(pattern.match(right_sent) for pattern in SCOPE_RIGHT):
        hits.append("scope")
    if DIVERGE_RIGHT.match(right_sent):
        hits.append("diverge")
    return hits


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
            left_sent, right_sent, context = extract_context(clean, m.start(), m.end())
            signals = detect_signals(left_sent, right_sent)
            occurrences.append({
                "file": str(path),
                "line": line_no,
                "word": canonical,
                "form": form,
                "context": context,
                "signals": signals,
            })
    return occurrences


def snippet(text, limit=110):
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def format_occ(occ):
    loc = f"{CYAN}{occ['file']}:{occ['line']}{NC}"
    sig = f" [{YELLOW}{','.join(occ['signals'])}{NC}]" if occ["signals"] else ""
    return f"    {loc}{sig} \"{snippet(occ['context'])}\""


def scope_pattern(targets):
    nouns = "|".join(re.escape(target) + "s?" for target in targets)
    return re.compile(rf"^\s+of\s+(the|a|an|this|that)\s+({nouns})\b", re.IGNORECASE)


def apply_book_words(config):
    global SENSE_NAME
    settings = watch_words(config, "word_sense")
    SENSE_NAME = str(settings.get("name") or SENSE_NAME)
    WATCHLIST[:] = [tuple([entry]) if isinstance(entry, str) else tuple(entry)
                    for entry in settings.get("words") or []]
    targets = [str(target) for target in settings.get("scope_targets") or [] if str(target)]
    SCOPE_RIGHT[:] = [scope_pattern(targets)] if targets else []
    return bool(WATCHLIST)


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("paths", nargs="*", help="files or folders (default: the manuscript)")
    parser.add_argument("--verbose", action="store_true",
                        help="also show uses that hit no signal pattern")
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
        has_words = apply_book_words(config)
        files = markdown_files(options.paths, config)
    except (ConfigError, FileNotFoundError) as error:
        return tool_failed(str(error), "word-sense-check")
    if not has_words:
        print("SKIPPED   word-sense-check: no words to check "
              "(terms.watch_words.word_sense.words is empty in book.yaml)")
        return 0
    return report(files, options.verbose, options.stats)


def report(files, verbose, stats_only):
    all_occ = []
    for path in files:
        all_occ.extend(find_occurrences(Path(path)))
    files_scanned = len(files)

    groups = {}
    for o in all_occ:
        groups.setdefault(o["word"], []).append(o)

    if stats_only:
        print(f"Files scanned: {files_scanned}")
        print(f"Total occurrences: {len(all_occ)}")
        print("\nPer word (signal = flagged by a signal pattern):")
        for word, occs in sorted(groups.items(), key=lambda x: -len(x[1])):
            sig = sum(1 for o in occs if o["signals"])
            flag = f" {RED}[FLAG]{NC}" if sig else ""
            print(f"  {word:<16} total={len(occs):4d}  signal={sig:3d}{flag}")
        return 0

    flagged_total = 0
    for word in sorted(groups.keys()):
        occs = groups[word]
        signal_hits = [o for o in occs if o["signals"]]
        if not signal_hits and not verbose:
            continue
        print(f"word: {word}  (total={len(occs)}, signal={len(signal_hits)})")
        for o in signal_hits:
            print(format_occ(o))
        if verbose:
            neutral = [o for o in occs if not o["signals"]]
            if neutral:
                print(f"  {CYAN}neutral (N={len(neutral)}):{NC}")
                for o in neutral:
                    print(format_occ(o))
        print()
        flagged_total += len(signal_hits)

    if flagged_total == 0:
        print(f"{GREEN}No {SENSE_NAME}-sense signal hits ({files_scanned} files).{NC}")
        return 0
    print(f"{RED}Flagged {flagged_total} signal hit(s) across {files_scanned} file(s).{NC}")
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
    if "word: flavour" not in text or "quantifier" not in text:
        failures.append("'a single flavour' was not flagged")
    if "word: note" not in text or "scope" not in text:
        failures.append("'each note of the crust' was not flagged")
    for line in failures:
        print(f"FAIL  {line}")
    print(f"self-test: {'PASS' if not failures else str(len(failures)) + ' failure(s)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
