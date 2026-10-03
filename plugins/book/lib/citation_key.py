#!/usr/bin/env python3
"""The citation key: how it is derived from an author list, and how it is validated.

This is the only place the key rule lives. Nothing in any skill may decide what a key
should look like on its own; every script imports this module.

    from citation_key import derive, validate
    derive(["Adams", "Baker", "Clark", "Davis"], 1994)   # -> 'ABCD94'

The rule is BibTeX alpha.bst, with no local dialect:

  1 author     `{v{}}{l{}}`, falling back to the first THREE letters of the Last part
               when that fragment is a single character      Smith 1999        -> Smi99
  2-4 authors  one fragment each, no '+'                     Adams + 3         -> ABCD94
  5 or more    the first THREE fragments, then '+'           Adams + 4         -> ABC+20

A fragment is the first letter of every token of the von part, then of every token of
the Last part:

  * a lower-case particle is kept          van Berg          -> vB
  * every word of a multi-word surname     Perez Molina      -> PM
  * a hyphen separates tokens too          Owen-Price        -> OP
  * every token keeps its own case         Rocha da Lima     -> RdL
                                           Rocha Da Lima     -> RDL

Two conventions sit on top of alpha:

  * `--` in place of the year when no date can be established, in the entry `(--)` and
    in the key (`Wal--`). An access date describes the reader, not the source, so it
    never becomes the year.
  * a trailing lower-case letter separates same-stem, same-year keys (`Smi72a`). alpha
    does this too.

Keys are ASCII: diacritics are folded (`Deniz` from `Déniz`), where alpha.bst would emit
the accented bytes.

The module also owns the shapes around a key: the bank entry heading (`### [Key] ...`),
the bibliography line (`[Key] Author, A. (Year). Title.`), and reading author lists
from both. Exit status of --self-test is 0 when clean, 1 otherwise.
"""

import argparse
import re
import sys
sys.dont_write_bytecode = True
import unicodedata

CONTRACT = "citation-key/7"

STYLE = "alpha"

PARTICLES = {
    "van", "von", "de", "der", "den", "del", "della", "di", "da", "dos", "du",
    "la", "le", "el", "al", "bin", "ibn", "ter", "ten", "op", "st",
}


def _split_von_last(surname):
    words = [w for w in re.split(r"[\s]+", surname.strip()) if w]
    if not words:
        return [], []
    von = []
    while len(words) > 1 and words[0][:1].islower():
        von.append(words.pop(0))
    return von, words


def _ascii(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text)
                   if not unicodedata.combining(c))


def _fragment(surname):
    von, last = _split_von_last(_ascii(surname))
    if not last:
        return ""
    return "".join(piece[:1]
                   for word in von + last
                   for piece in word.split("-") if piece)


def _single_author_stem(surname):
    fragment = _fragment(surname)
    if len(fragment) >= 2:
        return fragment
    _, last = _split_von_last(_ascii(surname))
    word = last[0]
    return word[0].upper() + word[1:3]


_PARTICLE_RUN = r"(?:(?:" + "|".join(sorted(PARTICLES)) + r")\s+)*"
_SURNAME_WORD = r"[A-Z][A-Za-z'’-]+"
AUTHOR_UNIT = re.compile(
    rf"({_PARTICLE_RUN}{_SURNAME_WORD}(?:\s+{_SURNAME_WORD})*)"
    r",\s*([A-Z]\.(?:-?[A-Z]\.)*)")

NO_DATE = re.compile(r"\((?:--|n\.d\.)\)")
YEAR_IN_ENTRY = re.compile(r"\((?:c\.\s*)?((?:1[89]|20)\d{2})")


def surnames_from_author_text(text):
    flags = []
    if "et al" in text.lower():
        flags.append("et-al")
    if re.search(r"\beds?\.", text):
        flags.append("eds")
    surnames = [m.group(1).strip() for m in AUTHOR_UNIT.finditer(text)]
    if not surnames:
        flags.append("org-or-unparsed")
    return surnames, flags


_REG_SUFFIX = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "phd", "md"}
_REG_ORG_WORD = re.compile(
    r"\b(Inc|Ltd|LLC|Corp|Corporation|Technologies|Technology|Project|Team|Blog|"
    r"Foundation|Consortium|Committee|Institute|Association|Labs?|Research|Staff|"
    r"Group|Conference|University|Department|Society|Council|Board|Company|Systems|"
    r"Software|AI)\b", re.I)
_REG_PROSE = re.compile(
    r"\b(no author|not printed|not state|does not|unknown|anonymous|unattributed|"
    r"carries no|none is asserted|the paper states|a forum answer|accepted answer|writing as|"
    r"contributed equally|published by the)\b|\b(question|thread)\)", re.I)
_REG_INITIAL = re.compile(r"^[A-Z]\.?(-?[A-Z]\.?)*$")


def _reg_given_first_surname(unit):
    words = [w for w in unit.split() if w.lower() not in _REG_SUFFIX]
    words = [w for w in words if not _REG_INITIAL.match(w)]
    if not words:
        return None
    surname = [words[-1]]
    i = len(words) - 2
    while i >= 0 and words[i].islower() and words[i].lower() in PARTICLES:
        surname.insert(0, words[i])
        i -= 1
    return " ".join(surname), (i > 0 and words[i][0].isupper())


def surnames_from_registry_field(field):
    text = re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", " ", field)).strip(" ;,")
    if not text:
        return [], None, "empty Authors field"
    if _REG_PROSE.search(text):
        return [], None, "the field is prose about authorship, not an author list"
    if re.search(r"\bet al\b|\band others\b|\.\.\.|…", text, re.I):
        return [], None, "the author list is truncated, so the count is unknown"

    units = [u.strip() for u in text.split(";") if u.strip()]

    if len(units) > 1 and all("," in u for u in units):
        out = []
        for u in units:
            head = u.split(",")[0].strip()
            if not head or not head[0].isupper():
                return [], None, f"surname-first unit not readable: {u!r}"
            out.append(head)
        return out, "high", "surname-first, semicolon-separated"

    if len(units) == 1 and text.count(",") == 1:
        head, tail = (x.strip() for x in text.split(","))
        tail_words = tail.split()
        if (head and head[0].isupper() and len(head.split()) <= 3
                and tail_words and len(tail_words) <= 3
                and _REG_INITIAL.match(tail_words[-1])
                and all(w[0].isupper() or w.lower() in PARTICLES for w in tail_words)
                and not _REG_ORG_WORD.search(text)):
            return [head], "high", "surname-first, single author"

    if (len(units) == 1 and text.count(",") == 1
            and len(text.split(",")[0].split()) == 1
            and not _REG_ORG_WORD.search(text)):
        return [], None, ("one unit, one comma, and a single-word head: 'Surname, Given' "
                          "and a two-author given-first list cannot be told apart here")

    parts = [u.strip() for u in re.split(r";|,|\band\b|&", text) if u.strip()]
    parts = [u for u in parts if not _REG_INITIAL.match(u)]
    if not parts:
        return [], None, "no author units found"

    if _REG_ORG_WORD.search(text):
        return [], None, f"organisation: {text!r}"
    if len(parts) == 1 and not re.search(r"\b[A-Z]\.", text):
        words = parts[0].split()
        if len(words) == 1:
            return [], None, f"a single bare word, not a parseable person: {text!r}"
        if len(words) > 2:
            return [], None, (f"one run of {len(words)} words with no initial to break it "
                              f"up: an organisation and a full name cannot be told apart "
                              f"here: {text!r}")

    out, compound = [], []
    for u in parts:
        got = _reg_given_first_surname(u)
        if not got:
            return [], None, f"unit not readable: {u!r}"
        surname, looks_compound = got
        out.append(surname)
        if looks_compound:
            compound.append(surname)
    if compound:
        return out, None, "possible compound surname, needs a human: " + ", ".join(compound)
    return out, "high", "given-first"


def strip_disambiguator(key):
    found = re.match(r"^(.*?(?:\d{2}|--))([a-z])$", key)
    return found.group(1) if found else key


def year_suffix(year):
    text = str(year).strip()
    if text in ("--", ""):
        return "--"
    digits = re.sub(r"\D", "", text)
    if len(digits) < 2:
        raise ValueError(f"cannot form a year suffix from {year!r}")
    return digits[-2:]


def derive(surnames, year):
    names = [s for s in surnames if s and s.strip()]
    if not names:
        raise ValueError("no surnames given")
    suffix = year_suffix(year)

    if len(names) == 1:
        return _single_author_stem(names[0]) + suffix
    if len(names) <= 4:
        return "".join(_fragment(n) for n in names) + suffix
    return "".join(_fragment(n) for n in names[:3]) + "+" + suffix


_STEM = r"[A-Za-z]{1,24}"
_PLUS = r"\+?"
_YEAR = r"\d{2}|--"
_LETTER = r"[a-z]?"

KEY_SHAPE = re.compile(rf"^({_STEM})({_PLUS})({_YEAR})({_LETTER})$")

KEY_BODY = rf"{_STEM}{_PLUS}(?:{_YEAR}){_LETTER}"

PLACEHOLDER = "<Key>"

ENTRY_HEADING = re.compile(r"^###\s+\[([^\]]+)\]\s*(.*)")

ENTRY_HEADING_M = re.compile(ENTRY_HEADING.pattern, re.M)

FENCE_LINE = re.compile(r"^ {0,3}```")

BIB_REST_OPENS = r'(?=["*_“‘A-Za-z0-9])'

BIB_ENTRY = re.compile(rf"^\[({KEY_BODY})\]\s+{BIB_REST_OPENS}(.*)")

BIB_ENTRY_ANY = re.compile(r"^\[([^\]\s]+)\]\s+(.*)")


def bib_entry(line, any_key=False):
    found = (BIB_ENTRY_ANY if any_key else BIB_ENTRY).match(line)
    return (found.group(1), found.group(2)) if found else None


def bib_entries(text, any_key=False):
    for number, line in enumerate(text.split("\n"), 1):
        found = bib_entry(line, any_key)
        if found:
            yield number, found[0], found[1]


def bib_blocks(text, any_key=False):
    lines = text.split("\n")
    starts = [(number, key) for number, key, _ in bib_entries(text, any_key)]
    for index, (number, key) in enumerate(starts):
        end = starts[index + 1][0] - 1 if index + 1 < len(starts) else len(lines)
        first = bib_entry(lines[number - 1], any_key)[1]
        tail = lines[number:end]
        yield number, key, "\n".join([first] + tail)


def is_placeholder(key):
    return key.strip() == PLACEHOLDER


def entry_headings(text, skip_fenced=False):
    fenced = False
    for number, line in enumerate(text.split("\n"), 1):
        if skip_fenced and FENCE_LINE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        found = ENTRY_HEADING.match(line)
        if found and not is_placeholder(found.group(1)):
            yield number, found.group(1).strip(), found.group(2).strip()


def entry_keys(text, skip_fenced=False):
    return [key for _, key, _ in entry_headings(text, skip_fenced)]


def sort_position(key):
    return key.lower()


def parse(key):
    found = KEY_SHAPE.match(key.strip())
    if not found:
        return None
    stem, plus, suffix, letter = found.groups()
    return stem, plus == "+", suffix, letter or ""


def validate(key, surnames=None, year=None):
    problems = []
    parsed = parse(key)
    if not parsed:
        return [f"malformed key {key!r}: expected a stem, optional '+', then two digits or '--'"]
    stem, has_plus, suffix, letter = parsed

    if surnames:
        expected = derive(surnames, year if year is not None else suffix)
        actual_core = f"{stem}{'+' if has_plus else ''}{suffix}"
        if actual_core != expected:
            problems.append(
                f"{key}: {len(surnames)} author(s) under alpha should key "
                f"as {expected}{letter}, not {actual_core}{letter}")
    elif has_plus and len(stem) < 3:
        problems.append(
            f"{key}: '+' means five or more authors, so the stem needs at least "
            f"three letters")
    return problems


def _self_test():
    failures = []

    def check(got, want, label):
        if got != want:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    four = ["Adams", "Baker", "Clark", "Davis"]

    check(derive(["Smith"], 2001), "Smi01", "one author falls back to three letters")
    check(derive(["Jones"], 1974), "Jon74", "one author")
    check(derive(["Brown"], 1972), "Bro72", "one author")

    check(derive(["Adams", "Baker"], 1995), "AB95", "two authors")
    check(derive(["Li", "Ng"], 2004), "LN04", "two short surnames")

    check(derive(four, 1994), "ABCD94", "four authors, no '+'")
    check(derive(["Evans", "Fox", "Grant"], 2021), "EFG21", "three authors, no '+'")
    check(derive(["Alpha", "Beta", "Gamma", "Delta", "Epsilon"], 1999), "ABG+99",
          "five authors take '+'")

    check(derive(["Hall", "Irwin", "van Berg"], 2010), "HIvB10", "particle kept")
    check(_single_author_stem("van Berg"), "vB", "'vB' is 2 chars, so no 'vBe' fallback")
    check(derive(["van Berg"], 1999), "vB99", "single-author particle key")
    check(_fragment("van der Meer"), "vdM", "two-token von part")
    check(derive(["van Dam", "Kerr", "van Loon"], 1998), "vDKvL98", "both particles kept")
    check(derive(["von Stein", "Lane"], 1997), "vSL97", "von particle kept")

    check(_fragment("Rocha Da Lima"), "RDL", "every word of a multi-word surname counts")
    check(_fragment("Perez Molina"), "PM", "two-word surname gives two letters")
    check(_single_author_stem("Perez Molina"), "PM", "'PM' is 2 chars, so no 'Per' fallback")
    check(derive(["Perez Molina", "Moss", "Nash"], 2020), "PMMN20", "multi-word surname in a list")

    check(_single_author_stem("McAdam"), "McA", "internal capital preserved (not 'Mca')")

    check(_fragment("Owen-Price"), "OP", "hyphen splits: 'OP', not 'O'")
    check(_single_author_stem("Owen-Price"), "OP", "'OP' is 2 chars, so no 'Owe' fallback")
    check(derive(["Hart-Lowe"], 2014), "HL14", "hyphenated single author")
    check(derive(["Olsen", "Owen-Price", "Park", "Quinn"], 2022), "OOPPQ22",
          "a hyphenated surname contributes one letter per part")
    check(derive(["Reed", "Shaw", "Todd-Hill"], 2008), "RSTH08", "hyphenated third author")
    check(_single_author_stem("Smith"), "Smi", "one author falls back to three letters")

    check(_fragment("Rocha da Lima"), "RdL", "lower-case word inside Last keeps its case")
    check(_fragment("Moreno de Luz"), "MdL", "the same, in a double surname")
    check(_fragment("Souza e Melo"), "SeM", "the same, with a connective")
    check(_fragment("Rocha Da Lima"), "RDL", "a capitalised Da is a Last token and stays upper")
    check(derive(["Upton", "Moreno de Luz"], 2025), "UMdL25", "end to end")

    check(derive(["Walsh"], "--"), "Wal--", "undated key")

    check(parse("ABC+25a"), ("ABC", True, "25", "a"), "letter suffix parsed")
    if validate("ABC+25a"):
        failures.append("ABC+25a rejected: the a/b/c discriminator is correct")

    if validate("vdMRS+24"):
        failures.append("vdMRS+24 rejected: a '+' stem may exceed three characters")

    for long_key in ["CdFCdRSeM19", "RdLAB+23", "ABCDE26", "RDLARDL+26", "vDKvL98"]:
        if not parse(long_key):
            failures.append(f"{long_key} does not parse: the stem bound is too tight")
        if not bib_entry(f"[{long_key}] Someone, S. (2019). A thing."):
            failures.append(f"{long_key} is not recognised as a bibliography line")
    check(derive(["Costa", "de Faria Cruz", "de Rosa", "Souza e Melo"], 2019),
          "CdFCdRSeM19", "four compound surnames give a nine-character stem")

    def reg(field):
        names, confidence, _ = surnames_from_registry_field(field)
        return names if confidence == "high" else None

    check(reg("Hill, Mark; Porter, Frank; Young, Jeffrey M."),
          ["Hill", "Porter", "Young"], "surname-first, semicolons")
    check(reg("Young, Jeffrey M."), ["Young"], "surname-first, one author")
    check(reg("Rocha Da Lima, Jose Aldo; Gomez, Rita; Ramos, Marco"),
          ["Rocha Da Lima", "Gomez", "Ramos"], "surname-first keeps a compound whole")

    check(reg("George H. Bell; John B. Cole; Tara J. Turner"),
          ["Bell", "Cole", "Turner"], "given-first, semicolons")
    check(reg("Anna Adams, Ben Baker, Carl Clark, Dan Davis"),
          ["Adams", "Baker", "Clark", "Davis"], "given-first, commas")
    check(reg("Anna von Stein; A. Mary Lane"),
          ["von Stein", "Lane"], "given-first keeps a lower-case particle")
    check(reg("Tom A. van Dam"), ["van Dam"], "given-first, single author with particle")

    for field, why in [
        ("Acme Technologies", "organisation"),
        ("Example Project", "organisation"),
        ("Sample project", "organisation"),
        ("Example Testing Blog", "organisation"),
        ("ACME, Short Range Task Force", "committee, comma-separated"),
        ("Jon Hill, Gail C. Moss, Kris De Vries", "compound surname 'De Vries'"),
        ("Maria Perez Molina, Mark Moss, Sam Nash", "compound surname 'Perez Molina'"),
        ("Vera Arnold, Marco Di Luca, Gino Rossi", "compound 'Di Luca'"),
        ("Anna A. Kova et al.", "truncated author list"),
        ("Ian Gray, Arthur Gomez Leal, and others", "truncated author list"),
        ("no author is printed in the document", "prose, not an author list"),
        ("Ana Reyes (question). The accepted answer, which gives the method, is by "
         "**Tom Hale**.", "prose: a forum thread with a question and an answer"),
        ("published by the forum user `someone`; the cached page does not state a real "
         "name, so none is asserted here", "prose: a handle, with no name asserted"),
        ("Tom Hey (Example Univ); Julia Frey (Example Inst). The paper states that both "
         "authors contributed equally", "a sentence trailing a real author list"),
        ("", "empty field"),
    ]:
        names, confidence, reason = surnames_from_registry_field(field)
        if confidence == "high":
            failures.append(f"registry field {field[:40]!r} was DERIVED as {names}; "
                            f"it must be refused: {why}")

    check(reg("Eli Adler, Dan G. Fisher"), ["Adler", "Fisher"],
          "two-author given-first with one comma")
    check(reg("Rob D. Ross, Steve Mills"), ["Ross", "Mills"], "two-author given-first")
    check(reg("Amy J. Kay, Brad A. Moore"), ["Kay", "Moore"], "two-author given-first")
    check(reg("Steve Ford, Nat Price"), ["Ford", "Price"],
          "two-author given-first with no initials at all")
    check(derive(reg("Eli Adler, Dan G. Fisher"), 17), "AF17", "end to end: AF17")

    check(reg("West, Dan"), None, "'Surname, Given' with a bare head is refused")
    check(reg("Smith, Miller"), None, "two bare surnames are refused for the same reason")
    check(reg("Kyle D. Chen, Reid Hall"), ["Chen", "Hall"],
          "a multi-word head means given-first, so the comma separates authors")

    check(reg("Alan Bradley"), ["Bradley"], "two bare words are a person")
    check(reg("Martin Walsh"), ["Walsh"], "two bare words are a person")
    check(reg("Bjorn Strand (Example State University)"), ["Strand"],
          "an affiliation in parentheses is stripped before the org test")
    for field, why in [
        ("Examplesoft", "a single bare word"),
        ("Contoso", "a single bare word"),
        ("Carl Fox (Acme), writing on the Example project blog", "carries 'project'/'blog'"),
    ]:
        if surnames_from_registry_field(field)[1] == "high":
            failures.append(f"{field!r} was derived; it must be refused: {why}")

    check(_ascii("Déniz"), "Deniz", "ascii fold removes the accent")
    check(_ascii("Plain"), "Plain", "ascii fold leaves plain text alone")
    check(derive(["Déniz"], 1996), "Den96", "accented surname keys as ASCII")
    check(derive(["Köster", "Kahn", "Vogel"], 2000), "KKV00", "accent in the first author")
    check(derive(["Gårdström Holm", "Söder", "Rydén"], 2026), "GHSR26",
          "accents do not change a multi-word fragment")

    if not surnames_from_registry_field("Acme Technologies")[2]:
        failures.append("a refused registry field carried no reason")

    names, flags = surnames_from_author_text("Adams, E., Baker, R., Clark, R., & Davis, J.")
    check(names, four, "author text parsed")
    check(flags, [], "clean author text has no flags")
    check(surnames_from_author_text("van Dam, R.")[0], ["van Dam"],
          "particle kept by the parser, so _fragment can give 'vD'")
    check(derive(surnames_from_author_text("van Dam, R.")[0], 1999), "vD99",
          "end to end: author text -> alpha key with a particle")
    check(derive(surnames_from_author_text("van Dam, R., Kerr, E., & van Loon, F.")[0],
                 1998), "vDKvL98", "end to end: both particles kept")
    check(surnames_from_author_text("Perez Molina, M., Moss, M., & Nash, S.")[0],
          ["Perez Molina", "Moss", "Nash"], "multi-word surname kept whole by the parser")
    check(surnames_from_author_text("Acme Inc.")[1], ["org-or-unparsed"], "org flagged")
    check(surnames_from_author_text("Smith, J., et al.")[1], ["et-al"], "et al flagged")
    check(strip_disambiguator("Smi72a"), "Smi72", "disambiguator stripped")
    check(strip_disambiguator("Wal--"), "Wal--", "undated key survives stripping")

    if not validate("nonsense"):
        failures.append("malformed key accepted")

    if not is_placeholder("<Key>"):
        failures.append("is_placeholder failed on the documentation example")
    if is_placeholder("Smi01"):
        failures.append("is_placeholder rejected a real key")

    bank = (
        '## Entry format\n\n```\n### [<Key>] Author(s), "Short Title" (Year)\n```\n\n'
        '### [AAA01] A, "First" (2001)\n\n'
        '###   [BBB02] B, "Tab-and-space dialect" (2002)\n\n'
        'Not a heading: ### [NOT01] inside prose\n'
    )
    keys = entry_keys(bank)
    if keys != ["AAA01", "BBB02"]:
        failures.append(f"entry_keys wrong: {keys} (placeholder or indentation mishandled)")
    numbers = [n for n, _, _ in entry_headings(bank)]
    if numbers != [7, 9]:
        failures.append(f"entry_headings line numbers wrong: {numbers}")

    fenced_bank = (
        '## Entry format\n\n```\n### [<Key>] Author(s), "Short Title" (Year)\n\n'
        '### [ZZZ99] a worked example written with a real-looking key\n```\n\n'
        '### [AAA01] A, "First" (2001)\n\n'
        '**Full title:** First\n\n'
        '```\n### [YYY98] a second fence, mid-entry\n```\n\n'
        '### [BBB02] B, "Second" (2002)\n'
    )
    if entry_keys(fenced_bank) != ["ZZZ99", "AAA01", "YYY98", "BBB02"]:
        failures.append(f"the default changed: {entry_keys(fenced_bank)} -- fences must "
                        f"still be read unless skip_fenced is asked for")
    masked = entry_keys(fenced_bank, skip_fenced=True)
    if masked != ["AAA01", "BBB02"]:
        failures.append(f"skip_fenced wrong: {masked} (a fenced heading was counted)")
    masked_numbers = [n for n, _, _ in entry_headings(fenced_bank, skip_fenced=True)]
    if masked_numbers != [9, 17]:
        failures.append(f"skip_fenced line numbers wrong: {masked_numbers}")
    if sorted(["b", "A"], key=sort_position) != ["A", "b"]:
        failures.append("sort_position is not case-insensitive")

    for line, want in [
        ("[Smi72a] Smith, A. (1972). Notes on a River Town. *Journal*.",
         ("Smi72a", "Smith, A. (1972). Notes on a River Town. *Journal*.")),
        ("[Jon01] Jones, N. (2001). A number of things.",
         ("Jon01", "Jones, N. (2001). A number of things.")),
        ("[ABC+94] Adams, R., et al. (1994). *Field Notes*.",
         ("ABC+94", "Adams, R., et al. (1994). *Field Notes*.")),
        ("[Wal--] Walsh, M. (--). An online catalog.",
         ("Wal--", "Walsh, M. (--). An online catalog.")),
        ('[Lee08] "A quoted title." The Example Blog.',
         ("Lee08", '"A quoted title." The Example Blog.')),
    ]:
        check(bib_entry(line), want, f"bib_entry {want[0]}")

    for line in ["[ABC12] (a harvest count that is not a weight measure). All are gated",
                 "[ABCD11] / [XYZ18] cross-check, and the per-acre yield ([RM05]).",
                 "[Jon74], p. 268, section 1.",
                 "[Smi23], [AB97], [Lee77].",
                 "[Alpha] [Beta] [Gamma]",
                 "   [Smi01] indented, so not a bibliography line"]:
        if bib_entry(line):
            failures.append(f"bib_entry wrongly accepted prose: {line[:40]!r}")

    if bib_entry("[Smith2001] Smith, N. (2001). Something."):
        failures.append("bib_entry accepted a four-digit year")

    check(bib_entry("[NotAKey] Someone, S. (1999). A thing.", any_key=True),
          ("NotAKey", "Someone, S. (1999). A thing."), "any_key sees a malformed key")
    if bib_entry("[NotAKey] Someone, S. (1999). A thing."):
        failures.append("strict BIB_ENTRY accepted a malformed key")
    if bib_entry("[Jon74], p. 268.", any_key=True):
        failures.append("any_key accepted prose with no space after the bracket")

    bibliography = (
        "# References\n"
        "\n"
        "[Smi01] Smith, N. (2001). A number of things. *Journal*.\n"
        "[Smi72a] Smith, A. (1972). Notes on a River Town.\n"
        "    continued on a wrapped line\n"
        "[Wal--] Walsh, M. (--). An online catalog.\n"
    )
    found = [(n, k) for n, k, _ in bib_entries(bibliography)]
    if found != [(3, "Smi01"), (4, "Smi72a"), (6, "Wal--")]:
        failures.append(f"bib_entries wrong: {found}")
    blocks = list(bib_blocks(bibliography))
    if len(blocks) != 3 or "wrapped line" not in blocks[1][2]:
        failures.append("bib_blocks did not carry a wrapped entry whole")
    if blocks[0][2] != "Smith, N. (2001). A number of things. *Journal*.":
        failures.append(f"bib_blocks mangled an unwrapped entry: {blocks[0][2]!r}")

    if not validate("ABC+94", four, 1994):
        failures.append("validation did not flag a '+' key for four authors")
    if validate("ABCD94", four, 1994):
        failures.append("validation wrongly flagged the correct alpha key")

    for line in failures:
        print(f"FAIL  {line}")
    print(f"\ncontract {CONTRACT}, style={STYLE}")
    print(f"self-test: {'PASS' if not failures else str(len(failures)) + ' failure(s)'}")
    return 1 if failures else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true", help="run the built-in tests")
    ap.add_argument("--derive", nargs="+", metavar="SURNAME",
                    help="derive a key from surnames; pass --year as well")
    ap.add_argument("--year", help="the year for --derive, or -- when there is none")
    ap.add_argument("--validate", metavar="KEY", help="check the shape of one key")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()
    if args.derive:
        if not args.year:
            sys.stderr.write("--derive needs --year\n")
            return 2
        print(derive(args.derive, args.year))
        return 0
    if args.validate:
        problems = validate(args.validate)
        for problem in problems:
            print(problem)
        return 1 if problems else 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
