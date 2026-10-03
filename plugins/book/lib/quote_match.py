import re

QUOTE_MIN_WORDS = 4
WINDOW_WORDS = 8
QUOTE_MAX_CHARS = 2000
QUOTED = re.compile(r'"([^"\n]{8,%d})"|“([^”\n]{8,%d})”'
                    % (QUOTE_MAX_CHARS, QUOTE_MAX_CHARS), re.S)
LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi",
             "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st"}
ELLIPSIS = re.compile(r"\[?\.\.\.\]?|…")
TITLE_STOPWORDS = frozenset((
    "the", "a", "an", "and", "or", "of", "for", "in", "on", "to", "with", "from",
    "into", "as", "at", "by", "is", "are", "be", "how", "what", "why", "when",
    "does", "do", "not", "its", "their", "this", "that", "using", "toward",
    "towards", "through", "over", "under", "between", "about", "study", "case",
))

FULL = "full"
ELSEVIER = "elsevier"
ELLIPSIS_PIECES = "ellipsis"
ALL_WINDOWS = "windows"
ONE_WINDOW = "window"


def squash(text):
    for glyph, expansion in LIGATURES.items():
        text = text.replace(glyph, expansion)
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def elsevier_variant(text):
    return squash(text).replace("ff", "v").replace("fi", "w")


def words(text):
    return re.findall(r"[A-Za-z0-9]+", text)


def quotes_in(field):
    found = []
    for match in QUOTED.finditer(field):
        start = match.start()
        if start and field[start - 1].isalnum():
            continue
        span = re.sub(r"\s+", " ", (match.group(1) or match.group(2)).strip())
        span = span.strip("*_` ")
        if not span[:1].isalnum() and not span.startswith("("):
            continue
        if span.count(")") > span.count("("):
            continue
        if len(words(span)) >= QUOTE_MIN_WORDS:
            found.append(span)
    return found


def segments(quote):
    parts = [part.strip(" ,;:.") for part in ELLIPSIS.split(quote)]
    return [part for part in parts if len(words(part)) >= 3]


def windows_of(quote):
    tokens = words(quote)
    windows = [squash(" ".join(tokens[start:start + WINDOW_WORDS]))
               for start in range(0, max(1, len(tokens) - WINDOW_WORDS + 1))]
    return [window for window in windows if len(window) > 20]


def locate_in(quote, texts):
    needle = squash(quote)
    variant = elsevier_variant(quote)
    pieces = [squash(piece) for piece in segments(quote)]
    windows = windows_of(quote)
    tries = (
        (FULL, lambda hay: needle and needle in hay),
        (ELSEVIER, lambda hay: variant != needle and variant in hay),
        (ELLIPSIS_PIECES, lambda hay: len(pieces) > 1 and all(piece in hay for piece in pieces)),
        (ALL_WINDOWS, lambda hay: windows and all(window in hay for window in windows)),
        (ONE_WINDOW, lambda hay: any(window in hay for window in windows)),
    )
    for how, matches in tries:
        for name, hay in texts:
            if hay and matches(hay):
                return name, how
    return "", ""


def title_words(title):
    return [word for word in words(title.lower())
            if len(word) >= 5 and word not in TITLE_STOPWORDS]


def surnames(authors):
    return [word for word in re.findall(r"\b[A-Z][a-z]{3,}", authors)
            if word.lower() not in TITLE_STOPWORDS]


def title_share(title, squashed_text):
    wanted = title_words(title)
    if not wanted:
        return 0.0
    return sum(1 for word in wanted if word in squashed_text) / len(wanted)


def has_surname(authors, squashed_text):
    return any(squash(name) in squashed_text for name in surnames(authors))
