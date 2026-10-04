#!/usr/bin/env python3
"""Write the title block of a paper as a pandoc metadata file.

build-book.sh passes the result to pandoc with --metadata-file for the paper edition. It
holds the authors from paper.authors (name, affiliation, email), the affiliations once each
as numbered institutes (for templates such as lncs that print them apart from the names),
the names again for the PDF properties, and the abstract: the text of paper.abstract without
its first heading, so the abstract goes into the abstract field and never into the body.
An email has its @ escaped, so pandoc writes it as plain text and not as a link, which the
\\email command of some classes cannot take. With --anonymous, or paper.anonymous: true, no
author, affiliation or email is written at all, and `anonymous: true` is, so a venue
template can switch on its own review options. With --output it prints one line that names
the authors and where they came from: paper.authors, or book.author when paper.authors lists
nobody.
"""

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

from book_config import ConfigError, add_config_arguments, config_from_args, paper_authors_data

EXIT_TOOL_FAILED = 2
FIXTURES = Path(__file__).resolve().parent / "fixtures"
FIRST_HEADING = re.compile(r"\A\s*#\s[^\n]*\n?")


class AbstractMissing(Exception):
    pass


def abstract_text(path):
    if path is None or not Path(path).is_file():
        raise AbstractMissing(f"no abstract file at {path} (paper.abstract in book.yaml)")
    return FIRST_HEADING.sub("", Path(path).read_text(encoding="utf-8"), count=1).strip()


def text_without_links(value):
    return value.replace("@", "\\@")


def author_entries(paper):
    return [{key: text_without_links(value) if key == "email" else value
             for key, value in author.items() if value}
            for author in paper_authors_data(paper) if author.get("name")]


def institute_key(author):
    if author.get("affiliation"):
        return ("affiliation", author["affiliation"])
    if author.get("email"):
        return ("email", author["email"])
    return None


def number_institutes(authors):
    institutes = []
    numbers = {}
    for author in authors:
        key = institute_key(author)
        if key is None:
            continue
        if key not in numbers:
            numbers[key] = len(institutes) + 1
            institutes.append({"name": author.get("affiliation"), "emails": []})
        author["institute"] = numbers[key]
        if author.get("email"):
            institutes[numbers[key] - 1]["emails"].append(author["email"])
    return [{field: value for field, value in
             (("name", institute["name"]), ("emails", ", ".join(institute["emails"])))
             if value} for institute in institutes]


def paper_metadata(config, anonymous):
    metadata = {}
    abstract = abstract_text(config.paper.abstract)
    if abstract:
        metadata["abstract"] = abstract
    if anonymous:
        metadata["anonymous"] = True
    else:
        authors = author_entries(config.paper)
        if authors:
            metadata["institutes"] = number_institutes(authors)
            metadata["author"] = authors
            metadata["pdf-authors"] = ", ".join(author["name"] for author in authors)
    return metadata


def authors_line(config, anonymous):
    if anonymous:
        return "none (anonymous)"
    names = ", ".join(author.name for author in config.paper.authors)
    if not names:
        return "none (paper.authors and book.author are empty)"
    if config.get("paper.authors", None):
        return f"{names} (from paper.authors)"
    return f"{names} (from book.author, because paper.authors lists nobody)"


def self_test():
    from book_config import load_config
    config = load_config(start=FIXTURES / "new-paper")
    named = paper_metadata(config, anonymous=False)
    hidden = paper_metadata(config, anonymous=True)
    hidden_text = json.dumps(hidden)
    shared_authors = [{"name": "A", "affiliation": "Lab"}, {"name": "B", "email": "b@example.org"},
                      {"name": "C", "affiliation": "Lab", "email": "c@example.org"},
                      {"name": "D"}]
    shared_institutes = number_institutes(shared_authors)
    checks = [
        ("every author is written", [author["name"] for author in named.get("author", [])],
         ["Sam Example", "Lee Sample"]),
        ("affiliation and email are kept", named["author"][0],
         {"name": "Sam Example", "affiliation": "Garden School", "email": "sam\\@example.org",
          "institute": 1}),
        ("each affiliation is one institute with its emails", named.get("institutes"),
         [{"name": "Garden School", "emails": "sam\\@example.org"}]),
        ("authors who share an affiliation share one institute",
         [(author["name"], author.get("institute")) for author in shared_authors],
         [("A", 1), ("B", 2), ("C", 1), ("D", None)]),
        ("a shared institute lists every email of its authors", shared_institutes,
         [{"name": "Lab", "emails": "c@example.org"}, {"emails": "b@example.org"}]),
        ("an author with no affiliation gets no empty field", named["author"][1],
         {"name": "Lee Sample"}),
        ("the abstract loses its heading", named.get("abstract", "").startswith("#"), False),
        ("the abstract text is kept", "small gardens" in named.get("abstract", ""), True),
        ("an anonymous paper has no author", "author" in hidden, False),
        ("an anonymous paper has no institute", "institutes" in hidden, False),
        ("an anonymous paper names nobody anywhere",
         any(word in hidden_text for word in ("Sam", "Lee", "Garden School", "example.org")),
         False),
        ("an anonymous paper tells the template it is anonymous", hidden.get("anonymous"), True),
        ("a named paper does not say anonymous", "anonymous" in named, False),
        ("an anonymous paper keeps its abstract", hidden.get("abstract") == named.get("abstract"),
         True),
    ]
    checks.append(("the authors line says they come from paper.authors",
                   authors_line(config, anonymous=False),
                   "Sam Example, Lee Sample (from paper.authors)"))
    checks.append(("the authors line of an anonymous paper names nobody",
                   authors_line(config, anonymous=True), "none (anonymous)"))
    with tempfile.TemporaryDirectory() as scratch:
        (Path(scratch) / "book.yaml").write_text(
            "version: 1\nkind: paper\nbook:\n  title: Pond Notes\n  author: Robin Field\n",
            encoding="utf-8")
        fallback = load_config(start=Path(scratch))
        checks.append(("the authors line says when the name comes from book.author",
                       authors_line(fallback, anonymous=False),
                       "Robin Field (from book.author, because paper.authors lists nobody)"))
        try:
            abstract_text(Path(scratch) / "missing.md")
            refused = False
        except AbstractMissing:
            refused = True
        checks.append(("a missing abstract file stops the build", refused, True))
    failures = [(name, got, expected) for name, got, expected in checks if got != expected]
    for name, got, expected in failures:
        print(f"FAIL  {name}: got {got!r}, expected {expected!r}")
    print(f"paper-metadata self-test: {len(checks) - len(failures)}/{len(checks)} passed")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    parser.add_argument("--anonymous", action="store_true",
                        help="leave out every author, affiliation and email "
                             "(default: paper.anonymous)")
    parser.add_argument("--output", metavar="FILE", help="write here instead of to stdout")
    parser.add_argument("--self-test", action="store_true",
                        help="run the built-in tests on the fixture paper")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    try:
        config = config_from_args(args)
        anonymous = args.anonymous or config.paper.anonymous
        metadata = paper_metadata(config, anonymous)
    except (ConfigError, AbstractMissing) as problem:
        sys.stderr.write(f"paper-metadata: {problem}\n")
        return EXIT_TOOL_FAILED
    text = json.dumps(metadata, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(authors_line(config, anonymous))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
