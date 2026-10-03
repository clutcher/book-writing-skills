#!/usr/bin/env python3
"""Find cached extractions whose STATISTICS are corrupt.

Three questions about the same bytes, three checks:

  scan-origin-check.py     is this a scan whose text layer is somebody's OCR?
  ocr-marker-check.py          is declared OCR marked everywhere it should be?
  statistic-integrity-check.py CAN I TRUST THE CHARACTERS INSIDE A NUMBER?

A born-digital PDF that remaps glyphs grades clean on the first two by construction:
its text layer can turn `=` into `5`, minus into `2` and `<` into `,`, so the extraction
reads `n 5 16` and `p , .001`. A wrong figure with a citation attached reads exactly like
a verified one, and the correct digits exist only in the page image.

Seven classes, in ascending order of how well they hide:
  digit-for-operator  a digit where an operator belongs (`n 5 16` is `n = 16`)
  operator-dropped    a statistic with NO operator (`p .001`): nothing odd to notice
  colon-in-number     the decimal point as a colon (`22:2`, `po0:001`); it reads as a
                      ratio or a typo and passes every human sanity check
  symbol-substituted  an operator or Greek letter replaced by a printable character
                      (`¼` for `=`, `c 2` for chi-squared). The font predicts the
                      pipeline, never which glyph moved
  flattened-greek     a Greek letter reduced to one Latin letter, which changes WHICH
                      statistic is named (epsilon-squared read as eta-squared); weak
  impossible-p        a p value outside [0, 1]; arithmetic, no judgment
  sign-dropped        a minus sign gone. It REVERSES A FINDING WITHOUT CHANGING A DIGIT,
                      and `r = 0.28` is ordinary, so the general case is undetectable.
                      Caught only where the source contradicts itself: a sentence says
                      the relation is negative while every value is unsigned, or a
                      confidence interval is printed largest-first. One hit condemns
                      the FILE: re-read every sign from a render. Rejected detectors,
                      not to be re-proposed: "all correlations positive" (ordinary),
                      and a suspect font as corroboration (a dropped glyph leaves no
                      font trace)

Digits and operators fail independently: a file can keep every numeral and lose its
operators, so a verified figure can sit beside a reversed comparison.

The worst case needs arithmetic, not a pattern: a dropped trailing digit leaves a legal
value (`F(3, 111)` extracted as `F(3, 1)`). So a separate section checks the numbers:
  df-truncated    a denominator df that is a strict prefix of another for the same test
  df-implausible  a denominator below 3 or below its numerator
  df-outlier      one df appearing once beside a near-identical one appearing often
  df-exceeds-n    by-subject dfs imply more subjects than the section states
  df-below-n      dfs imply fewer subjects than recruited, with no exclusion stated
The last two check the SOURCE's own arithmetic, because printed papers are sometimes
wrong. The report states the discrepancy and never picks a side; only the page image
separates an extraction defect from a printing error. A correlation's df counts
whatever was correlated, which need not be people, so a t(df) near a correlation is not
counted as a by-subject df.

Precision over recall: every pattern demands statistical context, text under 90% ASCII
is `text-unusable` and not scored, and a single hit of a class is AMBIGUOUS (one is a
typo, two is a remapping) except impossible-p and sign-dropped.

Verdicts (classes):
  corrupt            ADVISORY  two+ hits of a strong class, or any impossible-p or
                               sign-dropped: re-read every figure from a render
  likely             ADVISORY  one strong hit plus a suspect embedded font or a 2nd class
  ambiguous          ADVISORY  a single hit, or flattened-greek alone
  needs-arithmetic   ADVISORY  only the df section fired
  text-unusable      DEFECT    (shared class) the extraction cannot be scored

The claim is file-level, never line-level: "this extraction substitutes characters,
re-read every figure", not "this exact line is wrong". There is no --fix: the correct
value lives only in the page image; a script guessing `n 5 16` back to `n = 16` would
invent a figure. Each flagged key comes with the pdftoppm command for its pages.

pdfinfo and pdffonts are used when present (page numbers, font corroboration); without
them the text checks still run.

Usage:
  statistic-integrity-check.py
  statistic-integrity-check.py --key Smi09 --verbose
  statistic-integrity-check.py --self-test
"""

import argparse
import collections
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import add_config_arguments, folders_from_config, load_book, tool_failed
from check_output import (ADVISORY, SHARED_CLASSES, CheckReport, add_output_arguments,
                          skipped_for_missing)

TOOL = "statistic-integrity-check"
REPORT_CLASSES = {
    "corrupt": ADVISORY, "likely": ADVISORY, "ambiguous": ADVISORY,
    "needs-arithmetic": ADVISORY, "text-unusable": SHARED_CLASSES["text-unusable"],
}
ASCII_MIN = 90.0
MIN_CHARS = 2000
STRONG_MIN_HITS = 2
CONTEXT = 90

STAT = r"(?:[FtrzdkpMNn]|SD|SE|MSE|df|dfs|chi|w2|h2|F1|F2|R2|CI)"
CONTROL = r"[\x00-\x08\x0b\x0e-\x1f\x7f]"
NEIGHBOUR = re.compile(
    r"\b(?:F|t|r|z|chi|MSE?|SD|SE|df|n|N|eta|Cohen)\s?[(=<>¼]|\bp\s?[=<]\s?0?\.\d|"
    r"significan|reliable|ANOVA")
SPLIT_NUMBER = re.compile(r"^[\s]*[-+–−\xd7*^]|^[\s]*\d")

MINUS = "-‐‑‒–—―−"
SENTENCE_END = re.compile(r"[.?!][\"')\]]*\s")
DIRECTION = r"(?:negative|negatively|inverse|inversely)"
RELATION = r"(?:correlat\w*|relationship|association|slope|coefficient)"
SIGN_PROSE = re.compile(r"\b%s\b(?:\s+\w+)?\s+%s|\b%s\b(?:\s+\w+)?\s+%s"
                        % (DIRECTION, RELATION, RELATION, DIRECTION), re.I)
SIGN_HEDGE = re.compile(
    r"\b(?:no|not|non|none|never|neither|nor|absence|absent|without|lack\w*|fail\w*|"
    r"unlike|would|could|should|might|may|if|whether|expect\w*|predict\w*|"
    r"hypothes\w*|assum\w*|suppose\w*|instead|rather than)\b", re.I)
SIGN_VALUE = re.compile(r"(?:\br|\brs|\brho|\bRho|ρ|\bbeta|\bBeta|β|\bb|\bB)"
                        r"\s?[=(]\s*([%s])?\s*0?\.\d+" % MINUS)
INTERVAL = re.compile(r"[\[(]\s*([%s]?\d*\.\d+)\s*[,;]\s*([%s]?\d*\.\d+)\s*[\])]" % (MINUS, MINUS))
INTERVAL_MARK = re.compile(r"\bCI\b|confidence interval|\b95\s?%|\bHDI\b|credible interval", re.I)
SIGN_WINDOW = 500
INTERVAL_WINDOW = 70

CLASSES = (
    ("digit-for-operator", "strong", (
        re.compile(r"\b%s\s5\s+[-.\d]" % STAT),
        re.compile(r"\)\s5\s+-?\s?\d+\.\d+\s*[,;.)\]]"),
        re.compile(r"\b(?:eta|η)\s?2\s?p?\s5\s+[.\d]"),
        re.compile(r"\b[pP]s?\s,\s*0?\.\d"),
        re.compile(r"\b%s\(\d+[,;]\s?\d+\)\s,\s*[.\d]" % STAT),
    ), {}),
    ("operator-dropped", "strong", (
        re.compile(r"\b[pP]s?\s+0?\.\d{2,3}\b(?!\s*[\d.])"),
        re.compile(r"\b[FtT]s?\(\s?\d{1,3}\s?[,;]\s?\d{1,5}\s?\)\s{2,}\d*\.\d+"
                   r"(?!\s*[\d.])"),
        re.compile(r"\b(?:h|d|r|R)2?\s{2,}0?\.\d{2,3}\s*[,;.)\]]"),
        re.compile(r"\bdfs?\s+\d{1,3},\d{1,5}\b"),
    ), {}),
    ("colon-in-number", "strong", (
        re.compile(r"(?:=|¼)\s*\d{1,4}:\d"),
        re.compile(r"\b[pP]s?\s?[<>ob]?\s?0:\d"),
        re.compile(r"\b%s\s*[=¼]\s*\d{1,4}:\d" % STAT),
        re.compile(r"\b[FtT]\(\s?\d{1,3}:\d"),
    ), {}),
    ("symbol-substituted", "strong", (
        re.compile(r"[⭭⫿⫽]\s*[-.\d]"),
        re.compile(r"¼\s*[-.\d]"),
        re.compile(r"\b[FtT]\s?ð\s?\d"),
        re.compile(r"\b%s\(\d{1,3}[,;]\s?\d{1,5}\)\"[.\d]" % STAT),
        re.compile(r"\b[pP]s?\((?:0?\.\d|\d\.\d)"),
        re.compile(r"\bc\s?2\s?\(\s?\d{1,3}\s?[,)]"),
        re.compile(r"\b[pP]s?\s[bN]\s?0?\.\d"),
        re.compile(r"\b\d\s?#\s?\d[- ](?:way|by|factor|cell|design)"),
        re.compile(r"(?:%s|\)|\d)\s?%s\s?[-.\d]" % (STAT, CONTROL)),
    ), {}),
    ("flattened-greek", "weak", (
        re.compile(r"\b[cehjlq]\s?(?:²|\^2|2|%s)\s?(?:[=\"]|%s|value\s+of)\s*-?0?\.\d{2,}"
                   % (CONTROL, CONTROL)),
        re.compile(r"\b[cehjlq]\s?(?:²|\^2|2|%s)?\s?value\s+of\s+-?0?\.\d{2,}" % CONTROL),
        re.compile(r"\b[cehjlq]\s?(?:²|\^2|2|%s)?\"-?0?\.\d{2,}" % CONTROL),
    ), {}),
    ("impossible-p", "strong", (
        re.compile(r"\b[pP]s?\s*[=<>]\s*(?:[2-9]\d+|1\d+)(?=\s*(?:[,;.)\]]|$))", re.M),
    ), {"context": NEIGHBOUR, "reject_tail": SPLIT_NUMBER}),
    ("sign-dropped", "strong", (), {"scanner": "sign"}),
)

SINGLE_HIT_CLASSES = frozenset({"impossible-p", "sign-dropped"})

WEAK_CLASSES = frozenset(name for name, weight, _p, _g in CLASSES if weight == "weak")
STRONG_CLASSES = frozenset(name for name, weight, _p, _g in CLASSES if weight == "strong")

SUSPECT_FONTS = re.compile(r"Adv[TP]T|Universal-Greek|MathPi", re.I)

FTEST = re.compile(r"\b(F|t|T)s?\s?\(\s?(\d{1,3})\s?[,;]\s?(\d{1,5})\s?\)")
TTEST = re.compile(r"\bts?\s?\(\s?(\d{1,4})\s?\)")
SECTION = re.compile(r"\b(?:Participants|Subjects)\s?[.:]", re.M)
EXCLUDED = re.compile(r"\bexclud|\breplaced\b|\bdiscard|\bremoved\b|\bdropped\b|"
                      r"\bfailed to\b|\bdid not return\b", re.I)
COUNT_DIGITS = re.compile(
    r"\b(?:N|n)\s*=\s*(\d{1,4})\b|"
    r"\b(\d{1,4})\s+(?:undergraduate|graduate|university|college|paid|"
    r"volunteer|student|subject|participant|adult|profession|develop|program|"
    r"patient|child|teacher|nurse)",
    re.I)
COUNT_WORDS = re.compile(
    r"\b((?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
    r"thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)"
    r"(?:[ -](?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
    r"thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|and)){0,3})\s+"
    r"(?:undergraduate|graduate|student|subject|participant|adult|volunteer|"
    r"member|person|people|programmer|developer|patient|child|children|teacher|"
    r"nurse)", re.I)
WORD_VALUE = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
CORRELATION = re.compile(r"\bcorrelat\w*|\bSpearman\b|\bPearson\b|\brho\b|"
                         r"\b[rR]\s?[=(¼⫽\"]\s?[-.\d]", re.I)
CORRELATION_WINDOW = 160
DF_MIN = 3
OUTLIER_TOLERANCE = 0.15
N_GAP_MIN = 3
N_GAP_MAX = 0.5

DF_CODES = ("df-truncated", "df-implausible", "df-outlier", "df-exceeds-n",
            "df-below-n")

FIXTURES_SIGN = (
    (True, "prose negative, every value unsigned",
     "A negative correlation was found with Tone (r = 0.41, p = 0.009). Next."),
    (True, "interval printed largest-first",
     "The estimate was reliable, 95% CI [0.28, 0.15], and held. Next."),
    (False, "the value carries its minus",
     "A negative correlation was found (r = -0.33, p = 0.009). Next."),
    (False, "the minus is a typographic dash",
     "A negative correlation was found (r = −0.33, p = 0.009). Next."),
    (False, "the sentence denies the relation",
     "These two variables were not correlated and showed no negative relationship,"
     " r = .02, p = .92. Next."),
    (False, "the negative relation is only predicted",
     "We predicted a negative correlation, and obtained r = 0.33. Next."),
    (False, "negative names a construct, not a direction",
     "Consistent with the absence of a negative priming effect, r = .02, p = .92. Next."),
    (False, "a squared correlation has no sign to lose",
     "The negative relationship was weak (R2 = 0.10). Next."),
    (False, "direction stated with no value beside it",
     "A negative correlation was found with Tone. Next."),
    (False, "an interval in the right order",
     "The estimate was reliable, 95% CI [-0.28, 0.15], and held. Next."),
    (False, "a table cell rather than an interval",
     "scores for Task 1 and Task 2 were (5.47, 4.06), respectively. Next."),
    (False, "a function call rather than an interval",
     "testValue(-4.0, 0.0); testValue(64.0, 8.0); Next."),
)


def read_text(key, folders):
    path = folders.file(key + ".txt")
    if not path.exists():
        return None
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def page_of(text, offset, pages):
    feeds = text.count("\f")
    if feeds:
        return "%d" % (text.count("\f", 0, offset) + 1)
    if pages:
        return "~%d" % min(pages, int(pages * offset / max(len(text), 1)) + 1)
    return "?"


def pdf_pages(key, folders):
    pdf = str(folders.file(key + ".pdf"))
    if not Path(pdf).exists():
        return 0
    try:
        out = subprocess.run(["pdfinfo", pdf], capture_output=True, encoding="utf-8", errors="replace",
                             timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return 0
    match = re.search(r"^Pages:\s+(\d+)", out, re.M)
    return int(match.group(1)) if match else 0


def suspect_font(key, folders):
    pdf = str(folders.file(key + ".pdf"))
    if not Path(pdf).exists():
        return ""
    try:
        out = subprocess.run(["pdffonts", pdf], capture_output=True, encoding="utf-8", errors="replace",
                             timeout=120).stdout
    except (OSError, subprocess.SubprocessError):
        return ""
    match = SUSPECT_FONTS.search(out)
    return match.group(0) if match else ""


def line_index(text):
    starts, at = [0], text.find("\n")
    while at >= 0:
        starts.append(at + 1)
        at = text.find("\n", at + 1)
    return starts


def line_at(starts, offset):
    low, high = 0, len(starts) - 1
    while low < high:
        mid = (low + high + 1) // 2
        if starts[mid] <= offset:
            low = mid
        else:
            high = mid - 1
    return low + 1


def sentence_around(text, at):
    start = 0
    for match in SENTENCE_END.finditer(text, max(0, at - SIGN_WINDOW), at):
        start = match.end()
    match = SENTENCE_END.search(text, at, at + SIGN_WINDOW)
    return start, match.end() if match else min(len(text), at + SIGN_WINDOW)


def scan_sign(text):
    hits = []
    for match in SIGN_PROSE.finditer(text):
        start, end = sentence_around(text, match.start())
        sentence = text[start:end]
        if SIGN_HEDGE.search(sentence):
            continue
        signs = SIGN_VALUE.findall(sentence)
        if not signs or any(signs):
            continue
        hits.append((start, "prose says %s, every value unsigned"
                     % " ".join(match.group(0).split())))
    for match in INTERVAL.finditer(text):
        low, high = (numeric(match.group(1)), numeric(match.group(2)))
        if low is None or high is None or low <= high:
            continue
        if not INTERVAL_MARK.search(text[max(0, match.start() - INTERVAL_WINDOW):
                                         match.end()]):
            continue
        hits.append((match.start(), "interval %g to %g runs backwards" % (low, high)))
    return hits


def numeric(token):
    try:
        return float(re.sub(r"^[%s]" % MINUS, "-", token))
    except ValueError:
        return None


def scan_classes(text, pages):
    starts = line_index(text)
    found = collections.OrderedDict()
    for name, _weight, patterns, guards in CLASSES:
        if guards.get("scanner") == "sign":
            hits = [{"line": line_at(starts, offset),
                     "page": page_of(text, offset, pages),
                     "text": "%s | %s" % (detail,
                                          " ".join(text[offset:offset + CONTEXT].split()))}
                    for offset, detail in scan_sign(text)]
            if hits:
                found[name] = sorted(hits, key=lambda hit: hit["line"])
            continue
        context = guards.get("context")
        reject_tail = guards.get("reject_tail")
        seen, hits = set(), []
        for pattern in patterns:
            for match in pattern.finditer(text):
                line = line_at(starts, match.start())
                if line in seen:
                    continue
                if context and not context.search(
                        text[max(0, match.start() - CONTEXT):match.end() + CONTEXT]):
                    continue
                if reject_tail and reject_tail.search(text[match.end():match.end() + 40]):
                    continue
                seen.add(line)
                snippet = text[match.start():match.start() + CONTEXT]
                hits.append({"line": line,
                             "page": page_of(text, match.start(), pages),
                             "text": " ".join(snippet.split())})
        if hits:
            found[name] = sorted(hits, key=lambda hit: hit["line"])
    return found


def stated_counts(chunk):
    counts = []
    for match in COUNT_DIGITS.finditer(chunk):
        counts.append(int(match.group(1) or match.group(2)))
    for match in COUNT_WORDS.finditer(chunk):
        counts.append(spelled_value(match.group(1)))
    return [c for c in counts if 4 <= c <= 2000]


def spelled_value(phrase):
    total = 0
    for word in re.split(r"[ -]+", phrase.lower()):
        if word == "and":
            continue
        if word == "hundred":
            total = max(total, 1) * 100
        else:
            total += WORD_VALUE.get(word, 0)
    return total


def by_subject_dfs(chunk):
    dfs = []
    for match in FTEST.finditer(chunk):
        numerator, denominator = int(match.group(2)), int(match.group(3))
        if numerator <= 4 and 3 <= denominator <= 400:
            dfs.append(denominator)
    for match in TTEST.finditer(chunk):
        value = int(match.group(1))
        if 3 <= value <= 400 and not CORRELATION.search(
                chunk[max(0, match.start() - CORRELATION_WINDOW):match.start()]):
            dfs.append(value)
    return dfs


def df_findings(text):
    findings = []
    tests = collections.defaultdict(collections.Counter)
    starts = line_index(text)
    where = {}
    for match in FTEST.finditer(text):
        letter, numerator, denominator = (match.group(1),
                                          int(match.group(2)), int(match.group(3)))
        tests[(letter, numerator)][denominator] += 1
        where.setdefault((letter, numerator, denominator),
                         line_at(starts, match.start()))

    for (letter, numerator), counter in sorted(tests.items()):
        others = sorted(counter)
        for denominator, times in sorted(counter.items()):
            line = where[(letter, numerator, denominator)]
            longer = [other for other in others
                      if other != denominator
                      and str(other).startswith(str(denominator))
                      and other >= 100 and denominator < 100]
            if longer:
                findings.append(("df-truncated", line,
                                 "%s(%d, %d) sits beside %s -- a dropped trailing digit"
                                 % (letter, numerator, denominator,
                                    ", ".join("%s(%d, %d)" % (letter, numerator, o)
                                              for o in longer))))
                continue
            if denominator < DF_MIN or denominator < numerator:
                findings.append(("df-implausible", line,
                                 "%s(%d, %d) needs fewer than five observations"
                                 % (letter, numerator, denominator)))
                continue
            if times == 1:
                near = [other for other, count in counter.items()
                        if count >= 3 and other != denominator
                        and abs(other - denominator) <= OUTLIER_TOLERANCE * other]
                if near:
                    findings.append(("df-outlier", line,
                                     "%s(%d, %d) appears once beside %s appearing %d times"
                                     % (letter, numerator, denominator,
                                        "%s(%d, %d)" % (letter, numerator, near[0]),
                                        counter[near[0]])))

    findings.extend(section_findings(text, starts))
    return findings


def section_findings(text, starts):
    findings = []
    bounds = [match.start() for match in SECTION.finditer(text)]
    for index, start in enumerate(bounds):
        end = bounds[index + 1] if index + 1 < len(bounds) else len(text)
        chunk = text[start:end]
        counts = stated_counts(chunk[:600])
        dfs = by_subject_dfs(chunk)
        if not counts or not dfs:
            continue
        stated, implied = max(counts), max(dfs) + 1
        line = line_at(starts, start)
        gap = implied - stated
        if 0 < gap and N_GAP_MIN <= gap <= N_GAP_MAX * stated:
            findings.append(("df-exceeds-n", line,
                             "section states %d but a df of %d implies at least %d"
                             % (stated, max(dfs), implied)))
        elif gap < 0 and -gap >= N_GAP_MIN and -gap <= N_GAP_MAX * stated \
                and not EXCLUDED.search(chunk[:1200]):
            findings.append(("df-below-n", line,
                             "section states %d but every df implies at most %d analysed,"
                             " with no exclusion stated" % (stated, implied)))
    return findings


def grade(classes, font):
    strong = {name: hits for name, hits in classes.items() if name in STRONG_CLASSES}
    if any(name in SINGLE_HIT_CLASSES for name in strong):
        return "CORRUPT"
    if any(len(hits) >= STRONG_MIN_HITS for hits in strong.values()):
        return "CORRUPT"
    if strong and (font or len(classes) >= 2):
        return "LIKELY"
    if classes:
        return "AMBIGUOUS"
    return "clean"


def assess_text(key, text, pages=0, font_lookup=None):
    facts = {"key": key, "classes": {}, "df": [], "font": "", "pages": pages}
    if text is None or len(text) < MIN_CHARS:
        facts["verdict"] = "no-extraction"
        return facts
    ascii_pct = 100.0 * sum(1 for char in text if ord(char) < 128) / max(len(text), 1)
    facts["ascii_pct"] = ascii_pct
    facts["chars"] = len(text)
    if ascii_pct < ASCII_MIN:
        facts["verdict"] = "text-unusable"
        return facts
    facts["classes"] = scan_classes(text, pages)
    facts["df"] = df_findings(text)
    facts["font"] = font_lookup() if (facts["classes"] and font_lookup) else ""
    facts["verdict"] = grade(facts["classes"], facts["font"])
    if facts["verdict"] == "clean" and facts["df"]:
        facts["verdict"] = "NEEDS-ARITHMETIC"
    return facts


def assess(key, folders):
    text = read_text(key, folders)
    pages = pdf_pages(key, folders) if text else 0
    return assess_text(key, text, pages, lambda: suspect_font(key, folders))


def render_command(key, facts, shown_files):
    pages = []
    for hits in facts["classes"].values():
        pages.extend(hit["page"].lstrip("~") for hit in hits[:2])
    pages.extend(str(line) for _code, line, _detail in facts["df"][:0])
    ordered = sorted({page for page in pages if page.isdigit()}, key=int)
    first = ordered[0] if ordered else "1"
    last = ordered[-1] if ordered else "1"
    return ("pdftoppm -r 200 -f %s -l %s -png %s/%s.pdf /tmp/%s"
            % (first, last, shown_files, key, key.replace("+", "")))


def detail_of(facts, verbose, shown_files):
    classes = ", ".join("%s x%d" % (name, len(hits)) for name, hits in facts["classes"].items())
    detail = classes or "-"
    if facts["font"]:
        detail += " | font %s" % facts["font"]
    if facts["df"]:
        codes = collections.Counter(code for code, _line, _detail in facts["df"])
        detail += " | " + ", ".join("%s x%d" % (code, count) for code, count in sorted(codes.items()))
    if verbose:
        for name, hits in facts["classes"].items():
            for hit in hits[:6]:
                detail += " | %s line %d p.%s: %s" % (name, hit["line"], hit["page"], hit["text"][:110])
        for code, line, message in facts["df"][:8]:
            detail += " | %s line %d: %s" % (code, line, message)
    if facts["classes"] or facts["df"]:
        detail += " | render: " + render_command(facts["key"], facts, shown_files)
    return detail


FILLER = "Plain prose about how the study was run and what it measured. " * 40

FIXTURE_TEXTS = {
    "digit-for-operator": FILLER + "\nThe sample was n 5 16 in total.\n" + FILLER
                          + "\nThe effect held, t 5 2.10 overall.\n",
    "operator-dropped": FILLER + "\nThe effect was reliable, p .001 here.\n" + FILLER
                        + "\nThe second effect held, p .012 as well.\n",
    "colon-in-number": FILLER + "\nThe main effect was F = 22:2 in size.\n" + FILLER
                       + "\nThe test gave t = 3:4 on the second run.\n",
    "symbol-substituted": FILLER + "\nThe main effect was F ¼ 4.03 overall.\n" + FILLER
                          + "\nThe follow-up gave t ¼ 2.21 as well.\n",
    "impossible-p": FILLER + "\nThe effect was significant, F(1, 20) = 5.1, p = 393, and held.\n"
                    + FILLER,
    "sign-dropped": FILLER + "\nA negative correlation was found with similarity"
                    " (r = 0.33, p = 0.009). Next.\n" + FILLER,
}
FIXTURE_ARITHMETIC = (FILLER + "\nTable 4: F(3, 111) = 4.32 and F(3, 111) = 2.10.\n" + FILLER
                      + "\nIn the extraction the same test reads F(3, 1) = 4.32.\n")
FIXTURE_CLEAN = (FILLER + "\nThe effect was reliable, F(1, 38) = 1.04, p < .05, MSE = 0.46.\n"
                 + "The groups were split in a 2:1 ratio, see [4281:79].\n" + FILLER
                 + "\nThe split statistic reads F(1,12)\n=\n4.5 in the HTML.\n")
FIXTURE_MOJIBAKE = "\u0416\u0436\u00bc\u00e6\u00f0" * 800


def self_test():
    failures = []
    for expected, text in FIXTURE_TEXTS.items():
        facts = assess_text(expected, text)
        if facts["verdict"] not in ("CORRUPT", "LIKELY"):
            failures.append("%s not caught (verdict %s)" % (expected, facts["verdict"]))
        if expected not in facts["classes"]:
            failures.append("%s caught as %s" % (expected, sorted(facts["classes"])))
    facts = assess_text("arithmetic", FIXTURE_ARITHMETIC)
    if facts["verdict"] != "NEEDS-ARITHMETIC" or "df-truncated" not in {c for c, _l, _d in facts["df"]}:
        failures.append("the dropped trailing digit was not found (%s, %s)"
                        % (facts["verdict"], facts["df"]))
    facts = assess_text("clean", FIXTURE_CLEAN)
    if facts["verdict"] != "clean":
        failures.append("clean text flagged: %s %s" % (facts["verdict"], sorted(facts["classes"])))
    if assess_text("mojibake", FIXTURE_MOJIBAKE)["verdict"] != "text-unusable":
        failures.append("mojibake was scored instead of set aside")
    for expected, label, sample in FIXTURES_SIGN:
        if bool(scan_sign(sample)) != expected:
            failures.append("sign guard '%s': expected %s" % (label, "a hit" if expected else "silence"))
    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("--key", action="append", help="check only this key (repeatable)")
    parser.add_argument("--verbose", action="store_true",
                        help="the offending lines with line and page numbers")
    parser.add_argument("--self-test", action="store_true",
                        help="run the built-in examples (no cache needed)")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    folders = folders_from_config(config)
    if skipped_for_missing(TOOL, folders.files, "source library", args.format):
        return 0
    keys = args.key or sorted(path.name[:-4] for path in Path(folders.files).glob("*.txt"))
    report = CheckReport(TOOL, REPORT_CLASSES)
    for key in keys:
        facts = assess(key, folders)
        verdict = facts["verdict"].lower()
        if verdict in REPORT_CLASSES:
            report.add(key, verdict, detail_of(facts, args.verbose, folders.shown_files))
    if args.format == "text":
        print("checked %d extraction(s). No --fix exists: the correct figure lives only in\n"
              "the page image, so re-read each flagged figure from a render.\n" % len(keys))
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
