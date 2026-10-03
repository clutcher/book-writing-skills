import sys
from dataclasses import dataclass
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN / "lib"))

from citation_key import BIB_ENTRY_ANY, ENTRY_HEADING
from manuscript_text import cited_keys, prose_lines
from source_files import thinking_paths

TEXT = "text"
FACTS = "facts"
COVER = "cover"
SALES_TEXT = "sales-text"
SETUP = "setup"
GROUPS = (TEXT, FACTS, COVER, SALES_TEXT, SETUP)
ALL = "all"
MODES = (ALL, *GROUPS)

ON_PATHS = "on the paths given"
WHOLE_BOOK = "on the whole book"

RUN_CHECKS = "run-checks"
LIB = "lib"


def feature(key, name, inside=None):
    def missing(config):
        try:
            place = config.get(key, None)
        except KeyError:
            place = None
        if place and inside:
            place = Path(place) / inside
        if place and Path(place).exists():
            return None
        return f"the book has no {name} ({place or key + ' is not set'})"
    return missing


def page_count(config):
    pages = config.book.get("pages")
    if pages is not None and str(pages).isdigit():
        return None
    book_pdf = config.get("cover.book_pdf", None)
    if book_pdf and Path(book_pdf).is_file():
        return None
    output = config.work.output
    if output and Path(output).is_dir() and any(
            "digital" not in path.name and "cover" not in path.name
            for path in Path(output).glob("*.pdf")):
        return None
    return "no page count yet: build the print edition, or set book.pages in book.yaml"


COVER_DESIGN = feature("cover.design", "cover design")
RENDERED_WRAP = feature("cover.output", "rendered cover (design-cover make)", "png/wrap.png")
GLOSSARY = feature("rules.glossary", "glossary")
BIBLIOGRAPHY = feature("manuscript.references", "bibliography")
SOURCES_LIST = feature("sources.list", "sources list")
QUOTES = feature("sources.quotes", "quotes bank")
NO_SOURCES_YET = ("no sources yet: the sources list and the bibliography have no entry, and no "
                  "manuscript or thinking file cites a [Key]")


def prose_of(path):
    try:
        return prose_lines(Path(path).read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return []


def markdown_under(folder):
    if not folder or not Path(folder).is_dir():
        return []
    return sorted(Path(folder).rglob("*.md"))


def thinking_files(config):
    if thinking_paths(config):
        return None
    return "the book has no thinking files"


def sources_in_use(config):
    if any(ENTRY_HEADING.match(line) for line in prose_of(config.get("sources.list", None) or "")):
        return None
    references = config.get("manuscript.references", None)
    if references and any(BIB_ENTRY_ANY.match(line) for line in prose_of(references)):
        return None
    folders = (config.get("manuscript.dir", None), config.get("thinking.dir", None),
               config.get("thinking.argument", None))
    for folder in folders:
        for path in markdown_under(folder):
            if any(cited_keys(line) for line in prose_of(path)):
                return None
    return NO_SOURCES_YET

STORE_DESCRIPTION = feature("sales_text.amazon", "store description")
KEYWORDS = feature("sales_text.keywords", "keywords file")


@dataclass(frozen=True)
class Check:
    group: str
    skill: str
    script: str
    options: tuple = ()
    fix_options: tuple = None
    reach: str = WHOLE_BOOK
    graded: bool = True
    slow: bool = False
    needs: tuple = ()
    takes_set: bool = True
    uses_vale: bool = False

    @property
    def label(self):
        return " ".join((self.script, *self.options))

    @property
    def path(self):
        if self.skill == LIB:
            return PLUGIN / LIB / self.script
        return PLUGIN / "skills" / self.skill / "scripts" / self.script

    def arguments(self, fix):
        return self.fix_options if fix and self.fix_options is not None else self.options


def text_check(script, *options, reach=ON_PATHS, graded=False, skill="write-text"):
    return Check(TEXT, skill, script, tuple(options), reach=reach, graded=graded)


def facts_check(script, *options, skill="check-facts", graded=True, slow=False, needs=()):
    return Check(FACTS, skill, script, tuple(options), graded=graded, slow=slow,
                 needs=(SOURCES_LIST, sources_in_use, *needs))


def manuscript_facts_check(script, needs=()):
    return Check(FACTS, "check-facts", script, needs=needs)


CHECKS = (
    text_check("sentence-and-paragraph-check.py"),
    text_check("sentence-and-paragraph-check.py", "--connectors"),
    text_check("sentence-and-paragraph-check.py", "--meta"),
    text_check("sentence-and-paragraph-check.py", "--inversions", reach=WHOLE_BOOK),
    text_check("ascii-normalize.py"),
    text_check("unclear-this-check.py"),
    text_check("word-for-two-things-check.py"),
    text_check("word-sense-check.py"),
    text_check("person-introduction-check.py", reach=WHOLE_BOOK),
    Check(TEXT, "write-text", "definition-check.py", reach=ON_PATHS, graded=False,
          needs=(GLOSSARY,)),
    text_check("term-density-check.py", reach=WHOLE_BOOK),
    text_check("glossary-check.py", reach=WHOLE_BOOK, graded=True),
    text_check("code-font-check.py", reach=WHOLE_BOOK, graded=True, skill="build-editions"),
    Check(TEXT, "revise-from-notes", "open-notes.py", ("check",)),
    Check(TEXT, "write-text", "vale-run.py", reach=ON_PATHS, graded=False, uses_vale=True),

    facts_check("cited-source-check.py"),
    facts_check("citation-check.py", needs=(BIBLIOGRAPHY,)),
    facts_check("entry-format-check.py", needs=(QUOTES,)),
    facts_check("entry-format-fix.py", graded=False, needs=(QUOTES,)),
    facts_check("list-quotes-join-check.py", needs=(QUOTES,)),
    facts_check("key-authors-check.py"),
    facts_check("list-bibliography-check.py", "--no-verdicts", needs=(BIBLIOGRAPHY, QUOTES)),
    facts_check("citation-key-check.py", needs=(BIBLIOGRAPHY,)),
    facts_check("key-bibtex-check.py", needs=(BIBLIOGRAPHY,)),
    facts_check("reference-format-check.py", needs=(BIBLIOGRAPHY,)),
    facts_check("reference-format-check.py", "--completeness", needs=(BIBLIOGRAPHY,)),
    facts_check("reference-sort.py", needs=(BIBLIOGRAPHY,)),
    facts_check("edition-duplicate-check.py", needs=(BIBLIOGRAPHY,)),
    facts_check("guardrail-prose-check.py", needs=(QUOTES,)),
    manuscript_facts_check("uncited-claim-check.py"),
    manuscript_facts_check("stale-argument-pointer-check.py", needs=(thinking_files,)),
    facts_check("argument-key-check.py", needs=(BIBLIOGRAPHY, thinking_files)),
    facts_check("files-hash-check.py", skill="collect-sources"),
    facts_check("ocr-marker-check.py", skill="collect-sources", needs=(QUOTES,)),
    facts_check("duplicate-source-check.py", skill="collect-sources"),
    facts_check("quote-in-file-check.py", slow=True, needs=(QUOTES,)),
    facts_check("statistic-integrity-check.py", skill="collect-sources", slow=True,
                needs=(QUOTES,)),
    facts_check("scan-origin-check.py", skill="collect-sources", slow=True),
    facts_check("scan-marker-sweep.py", skill="collect-sources", slow=True),

    Check(COVER, "design-cover", "color-check.py", needs=(COVER_DESIGN,)),
    Check(COVER, "design-cover", "font-check.py", needs=(COVER_DESIGN,)),
    Check(COVER, "design-cover", "layout-check.py", needs=(COVER_DESIGN, page_count)),
    Check(COVER, "design-cover", "overlay.py", needs=(COVER_DESIGN, page_count, RENDERED_WRAP)),

    Check(SALES_TEXT, "prepare-sales-text", "sync-check.py"),
    Check(SALES_TEXT, "prepare-sales-text", "store-description-check.py",
          needs=(STORE_DESCRIPTION,)),
    Check(SALES_TEXT, "prepare-sales-text", "keyword-check.py",
          needs=(KEYWORDS,)),

    Check(SETUP, LIB, "book_config.py", ("check",)),
    Check(SETUP, LIB, "decisions.py", ("check",), fix_options=("check", "--fix")),
    Check(SETUP, "init", "toolchain-check.py", takes_set=False),
)


def checks_of(mode):
    groups = GROUPS if mode == ALL else (mode,)
    return [check for group in groups for check in CHECKS if check.group == group]
