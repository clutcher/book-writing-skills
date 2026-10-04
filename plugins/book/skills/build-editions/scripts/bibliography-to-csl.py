#!/usr/bin/env python3
"""Turn the book's BibTeX bibliography into the CSL-JSON file that pandoc --citeproc reads.

pandoc (tools.pandoc_image, in Docker, as the other build steps run it) reads the .bib and
writes CSL-JSON. Before that, the title fields (title, booktitle, journal, series, chapter)
get one more pair of braces in a copy of the .bib, so pandoc keeps the case the author wrote
instead of turning each title into sentence case. With citation style alpha, every entry then
gets citation-label = its key, so the text cites [Key] and the reference list starts each entry
with [Key]; pandoc's own labels are not the labels BibTeX gives. With numeric, no label is set.
Two more repairs on pandoc's output: a "von" part (van, de, von der) stays in front of the
family name, as the author wrote it, and the biblatex `eid` field, which pandoc drops, becomes
the CSL `number` that the style prints as "Article 12" (or "Paper 12" in proceedings).

The .bib is sources.bibliography (default sources/references.bib), the style
sources.citation_style (default alpha); --bibliography, --style and --image override them.
build-book.sh runs this before every edition and writes the JSON into its temporary folder.
Exit codes: 0 written, 2 the tool failed (no .bib, no Docker, pandoc could not read the .bib).
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parents[2] / "lib"))

from bibliography import BibliographyError, parse_bibliography, plain_text
from book_config import ConfigError, add_config_arguments, config_from_args, load_config
from container_run import calling_user_arguments, folder_mount

DEFAULT_BIBLIOGRAPHY = Path("sources") / "references.bib"
DEFAULT_STYLE = "alpha"
STYLES = ("alpha", "numeric")
NAME_ROLES = ("author", "editor")
CASE_KEPT_FIELDS = ("title", "booktitle", "journal", "series", "chapter")
SKIPPED_ENTRY_TYPES = ("comment", "preamble", "string")
CONTAINER_FOLDER = "/bibliography"
KEPT_CASE_FILE = "kept-case.bib"
CONVERTED_FILE = "converted.json"
PANDOC_TIME_LIMIT = 300
EXIT_WRITTEN = 0
EXIT_TOOL_FAILED = 2


class ToolFailed(Exception):
    pass


def closing_brace(text, opening):
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ToolFailed(f"a brace opened at character {opening} of the .bib is never closed")


def closing_quote(text, opening):
    depth = 0
    for index in range(opening + 1, len(text)):
        character = text[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
        elif character == '"' and depth == 0:
            return index
    raise ToolFailed(f"a quote opened at character {opening} of the .bib is never closed")


def skip_space(text, index):
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def word_end(text, index):
    while index < len(text) and (text[index].isalnum() or text[index] in "_-:+.'/"):
        index += 1
    return index


def is_one_braced_group(text):
    return text.startswith("{") and closing_brace(text, 0) == len(text) - 1


def kept_case_value(value):
    inner = value[1:-1]
    if value.startswith("{") and not is_one_braced_group(inner):
        return "{" + value + "}"
    if value.startswith('"') and not is_one_braced_group(inner):
        return '"{' + inner + '}"'
    return value


def value_end(text, index):
    if text[index] == "{":
        return closing_brace(text, index) + 1
    if text[index] == '"':
        return closing_quote(text, index) + 1
    return word_end(text, index)


def fields_with_kept_case(body):
    pieces, index = [], 0
    while index < len(body):
        name_start = skip_space(body, index)
        name_stop = word_end(body, name_start)
        equals = skip_space(body, name_stop)
        if name_stop == name_start or equals >= len(body) or body[equals] != "=":
            comma = body.find(",", index)
            stop = len(body) if comma < 0 else comma + 1
            pieces.append(body[index:stop])
            index = stop
            continue
        value_start = skip_space(body, equals + 1)
        stop = value_end(body, value_start)
        value = body[value_start:stop]
        if body[name_start:name_stop].lower() in CASE_KEPT_FIELDS:
            after = skip_space(body, stop)
            if after >= len(body) or body[after] != "#":
                value = kept_case_value(value)
        pieces.append(body[index:value_start] + value)
        index = stop
    return "".join(pieces)


def with_kept_case(text):
    pieces, index = [], 0
    while True:
        at = text.find("@", index)
        if at < 0:
            pieces.append(text[index:])
            return "".join(pieces)
        type_stop = word_end(text, at + 1)
        opening = skip_space(text, type_stop)
        if opening >= len(text) or text[opening] != "{":
            pieces.append(text[index:at + 1])
            index = at + 1
            continue
        closing = closing_brace(text, opening)
        entry_type = text[at + 1:type_stop].lower()
        body = text[opening + 1:closing]
        if entry_type not in SKIPPED_ENTRY_TYPES:
            body = fields_with_kept_case(body)
        pieces.append(text[index:opening + 1] + body + "}")
        index = closing + 1


def with_particle_kept(name):
    if "dropping-particle" not in name:
        return name
    kept = {field: value for field, value in name.items() if field != "dropping-particle"}
    particles = [name["dropping-particle"], name.get("non-dropping-particle", "")]
    kept["non-dropping-particle"] = " ".join(particle for particle in particles if particle)
    return kept


def with_particles_kept(entries):
    return [{**entry, **{role: [with_particle_kept(name) for name in entry[role]]
                         for role in NAME_ROLES if role in entry}}
            for entry in entries]


def article_numbers(text):
    return {key: plain_text(entry.field("eid"))
            for key, entry in parse_bibliography(text).entries.items() if entry.field("eid")}


def with_article_numbers(entries, numbers):
    return [{**entry, "number": numbers[entry["id"]]} if entry.get("id") in numbers else entry
            for entry in entries]


def with_labels(entries, style):
    if style != "alpha":
        return entries
    return [{**entry, "citation-label": entry["id"]} for entry in entries]


def converted_entries(bibliography, image, work_folder):
    if not shutil.which("docker"):
        raise ToolFailed("docker not found; pandoc runs in Docker to read the .bib")
    (work_folder / KEPT_CASE_FILE).write_text(
        with_kept_case(bibliography.read_text(encoding="utf-8")), encoding="utf-8")
    command = ["docker", "run", "--rm", "--network", "none", *calling_user_arguments(),
               *folder_mount(work_folder, CONTAINER_FOLDER), "--entrypoint", "pandoc", image,
               f"{CONTAINER_FOLDER}/{KEPT_CASE_FILE}", "--from=bibtex", "--to=csljson",
               f"--output={CONTAINER_FOLDER}/{CONVERTED_FILE}"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=PANDOC_TIME_LIMIT)
    if result.returncode != 0:
        raise ToolFailed(f"pandoc could not read {bibliography}:\n{result.stderr.strip()}")
    try:
        return json.loads((work_folder / CONVERTED_FILE).read_text(encoding="utf-8"))
    finally:
        for name in (KEPT_CASE_FILE, CONVERTED_FILE):
            (work_folder / name).unlink(missing_ok=True)


def configured_bibliography(config):
    configured = getattr(config.sources, "bibliography", None)
    if not configured:
        return config.root / DEFAULT_BIBLIOGRAPHY
    configured = Path(configured)
    return configured if configured.is_absolute() else config.root / configured


def chosen_settings(args):
    config = config_from_args(args)
    bibliography = Path(args.bibliography) if args.bibliography else configured_bibliography(config)
    style = args.style or getattr(config.sources, "citation_style", None) or DEFAULT_STYLE
    image = args.image or config.tools.pandoc_image
    if style not in STYLES:
        raise ToolFailed(f"citation style {style!r} is not one of: {', '.join(STYLES)}")
    if not bibliography.is_file():
        raise ToolFailed(f"no bibliography at {bibliography} (sources.bibliography)")
    return bibliography, style, image


CROSSREF_SAMPLE = """@inproceedings{Abb20,
  author = {Ann Abbott},
  title = {Small Ponds},
  crossref = {Ber20},
  pages = {1--10}
}
@proceedings{Ber20,
  editor = {Ben Berg},
  title = {Proceedings of the Garden Conference},
  booktitle = {Proceedings of the Garden Conference},
  publisher = {Garden Press},
  year = {2020}
}
"""


def crossref_child_fields(image):
    with tempfile.TemporaryDirectory() as scratch:
        bibliography = Path(scratch) / "sample.bib"
        bibliography.write_text(CROSSREF_SAMPLE, encoding="utf-8")
        entries = {entry["id"]: entry for entry in converted_entries(bibliography, image,
                                                                     Path(scratch))}
    child = entries.get("Abb20", {})
    return (child.get("container-title"), child.get("publisher"),
            child.get("issued"), [name.get("family") for name in child.get("editor", [])])


def crossref_check(checks):
    image = load_config(start=Path(tempfile.gettempdir())).tools.pandoc_image
    present = shutil.which("docker") and subprocess.run(
        ["docker", "image", "inspect", image], capture_output=True, check=False).returncode == 0
    if not present:
        print(f"SKIPPED  a crossref child gets its parent's fields: docker or {image} is missing")
        return
    checks.append(("a crossref child gets its parent's fields, with the case kept",
                   crossref_child_fields(image),
                   ("Proceedings of the Garden Conference", "Garden Press",
                    {"date-parts": [[2020]]}, ["Berg"])))


def self_test():
    checks = [
        ("a braced title gets one more pair of braces",
         with_kept_case("@book{Abc99, title = {A Title}, year = {1999}}"),
         "@book{Abc99, title = {{A Title}}, year = {1999}}"),
        ("a quoted title keeps its case",
         with_kept_case('@article{Abc99, title = "A {B} Title", journal = {J}}'),
         '@article{Abc99, title = "{A {B} Title}", journal = {{J}}}'),
        ("a title already in two braces is left alone",
         with_kept_case("@book{Abc99, title = {{A Title}}}"),
         "@book{Abc99, title = {{A Title}}}"),
        ("a quoted title already in braces is left alone",
         with_kept_case('@book{Abc99, title = "{A Title}"}'),
         '@book{Abc99, title = "{A Title}"}'),
        ("a quoted title in two braced parts gets one pair around both",
         with_kept_case('@book{Abc99, title = "{A} and {B}"}'),
         '@book{Abc99, title = "{{A} and {B}}"}'),
        ("the crossref field is not changed and the parent's booktitle keeps its case",
         with_kept_case("@inproceedings{Abb20, crossref = {Ber20}}\n"
                        "@proceedings{Ber20, booktitle = {Garden Days}}"),
         "@inproceedings{Abb20, crossref = {Ber20}}\n"
         "@proceedings{Ber20, booktitle = {{Garden Days}}}"),
        ("an empty quoted title stays balanced",
         with_kept_case('@book{Abc99, title = ""}'), '@book{Abc99, title = "{}"}'),
        ("braces inside a title stay balanced",
         with_kept_case("@book{Abc99, title = {The {LaTeX} Way}, booktitle={Big {Book}}}"),
         "@book{Abc99, title = {{The {LaTeX} Way}}, booktitle={{Big {Book}}}}"),
        ("other fields and the text between entries stay as they are",
         with_kept_case("% note\n@misc{Ab+20,\n  author = {A, B},\n  note = {Some Note}\n}\n"),
         "% note\n@misc{Ab+20,\n  author = {A, B},\n  note = {Some Note}\n}\n"),
        ("a comment entry is not changed",
         with_kept_case("@comment{title = {x}}"), "@comment{title = {x}}"),
        ("alpha sets citation-label to the key",
         with_labels([{"id": "ABC+20", "title": "T"}], "alpha"),
         [{"id": "ABC+20", "title": "T", "citation-label": "ABC+20"}]),
        ("numeric sets no label", with_labels([{"id": "Abc99"}], "numeric"), [{"id": "Abc99"}]),
        ("a von part stays in front of the family name",
         with_particles_kept([{"id": "vB99", "author": [{"family": "Berg", "given": "A.",
                                                         "dropping-particle": "van"}]}]),
         [{"id": "vB99", "author": [{"family": "Berg", "given": "A.",
                                     "non-dropping-particle": "van"}]}]),
        ("the eid field is read as the article number",
         article_numbers("@article{Abc04, title = {T}, eid = {12}}\n@book{Xy99, title = {B}}"),
         {"Abc04": "12"}),
        ("the article number reaches only its own entry",
         with_article_numbers([{"id": "Abc04"}, {"id": "Xy99"}], {"Abc04": "12"}),
         [{"id": "Abc04", "number": "12"}, {"id": "Xy99"}]),
    ]
    crossref_check(checks)
    failures = [(name, got, expected) for name, got, expected in checks if got != expected]
    for name, got, expected in failures:
        print(f"FAIL  {name}: got {got!r}, expected {expected!r}")
    print(f"bibliography-to-csl self-test: {len(checks) - len(failures)}/{len(checks)} passed")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    parser.add_argument("--bibliography", metavar="FILE", help="the .bib to read")
    parser.add_argument("--style", choices=STYLES, help="the citation style (alpha or numeric)")
    parser.add_argument("--image", metavar="IMAGE", help="the pandoc Docker image")
    parser.add_argument("--output", metavar="FILE", help="the CSL-JSON file to write")
    parser.add_argument("--self-test", action="store_true", help="run the built-in tests")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if not args.output:
        parser.error("--output is required")
    try:
        bibliography, style, image = chosen_settings(args)
        output = Path(args.output).resolve()
        numbers = article_numbers(bibliography.read_text(encoding="utf-8"))
        entries = with_article_numbers(with_particles_kept(
            converted_entries(bibliography, image, output.parent)), numbers)
        entries = with_labels(entries, style)
    except (ConfigError, ToolFailed, OSError, subprocess.TimeoutExpired,
            json.JSONDecodeError, BibliographyError) as problem:
        sys.stderr.write(f"bibliography-to-csl: {problem}\n")
        return EXIT_TOOL_FAILED
    output.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"bibliography-to-csl: {len(entries)} entries from {bibliography}, style {style}")
    return EXIT_WRITTEN


if __name__ == "__main__":
    sys.exit(main())
