#!/usr/bin/env python3
"""Run the real bibtex with alpha.bst over the bibliography and compare its labels with our keys.

Every other key check asks whether a key agrees with this plugin's own reading of the
alpha rule (lib/citation_key.py). This one leaves that reading behind: it runs bibtex
with Patashnik's alpha.bst and compares the label bibtex prints with the key the book
uses. Two rules the keys rest on (a hyphen splits name tokens; every token keeps its
own case) live in bibtex's built-in `format.name$`, not in alpha.bst, so only running
the program settles them.

It needs a bibtex binary and alpha.bst. It looks for them on PATH (kpsewhich finds
alpha.bst); when they are missing it runs both from the book's `tools.bibtex_image`
docker image as the calling user. With neither it prints SKIPPED and why. A skipped
check is "not verified", never a pass.

Two conventions are expected deviations, reported but not counted wrong:
  * a key fragment is ASCII-folded (alpha keeps the accent command)
  * an undatable work takes `--` for its year (alpha appends nothing)

Classes:
  disagree             DEFECT        bibtex prints a different label than the key
  expected-deviation   INFORMATIONAL one of the two conventions above, or a sibling key
                                     that is registered but not cited
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import add_config_arguments, load_book, tool_failed
from check_output import DEFECT, INFORMATIONAL, CheckReport, add_output_arguments
from citation_key import bib_entries, entry_keys
from container_run import calling_user_arguments, folder_mount

TOOL = "key-bibtex-check"
CLASSES = {"disagree": DEFECT, "expected-deviation": INFORMATIONAL}

YEAR = re.compile(r"\((?:c\.\s*)?((?:1[89]|20)\d{2})\)")
NODATE = re.compile(r"\((?:--|n\.d\.)\)")
UNIT = re.compile(r"([^,]+?,\s*(?:[A-Z]\.(?:-?[A-Z]\.)*)+)")


def bibtex_authors(segment):
    seg = segment.strip().rstrip(",").strip()
    etal = bool(re.search(r"\bet al\.?", seg, re.I))
    seg = re.sub(r",?\s*et al\.?", "", seg, flags=re.I)
    units = [re.sub(r"^(?:&|and)\s+", "", u.strip()) for u in UNIT.findall(seg)]
    if units:
        return " and ".join(units) + (" and others" if etal else ""), "personal"
    org = seg.rstrip(".").strip()
    if not org:
        return None, "empty"
    parts = [p.strip() for p in re.split(r"\s*&\s*", org) if p.strip()]
    return " and ".join("{" + p + "}" for p in parts) + (" and others" if etal else ""), "corporate"


def normalise(label):
    label = label.replace(r"{\etalchar{+}}", "+")
    while re.search(r"\{([^{}]*)\}", label):
        label = re.sub(r"\{([^{}]*)\}", r"\1", label)
    return label


def bibliography_rows(text):
    rows = []
    for _, key, rest in bib_entries(text):
        year_match, nodate_match = YEAR.search(rest), NODATE.search(rest)
        if not year_match and not nodate_match:
            continue
        authors, kind = bibtex_authors(rest[: (year_match or nodate_match).start()])
        if authors:
            rows.append({"id": "k%03d" % len(rows), "key": key, "kind": kind,
                         "authors": authors,
                         "year": year_match.group(1) if year_match else None})
    return rows


def write_bibtex_input(work, rows):
    with open(Path(work, "t.bib"), "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write("@article{%s,\n  author = {%s},\n" % (row["id"], row["authors"]))
            if row["year"]:
                handle.write("  year = {%s},\n" % row["year"])
            handle.write("  title = {T},\n  journal = {J}\n}\n\n")
    with open(Path(work, "t.aux"), "w", encoding="utf-8") as handle:
        handle.write("\\relax\n")
        for row in rows:
            handle.write("\\citation{%s}\n" % row["id"])
        handle.write("\\bibstyle{alpha}\n\\bibdata{t}\n")


def sibling_registered(key, got, registered):
    if not (key.startswith(got) and len(key) == len(got) + 1 and key[-1].islower()):
        return False
    return any(other != key and other.startswith(got) and len(other) == len(got) + 1
               and other[-1].islower() for other in registered)


def grade(rows, emitted, registered):
    agree, deviation, disagree = 0, [], []
    for row in rows:
        got = normalise(emitted.get(row["id"], "(none)"))
        if got == row["key"]:
            agree += 1
        elif not row["year"] and row["key"] == got + "--":
            deviation.append((row["key"], got, "the `--` year is a convention alpha cannot produce"))
        elif got and re.sub(r"\\.|[{}'\"^`]", "", got) == row["key"]:
            deviation.append((row["key"], got, "key fragments are ASCII-folded"))
        elif sibling_registered(row["key"], got, registered):
            deviation.append((row["key"], got,
                              "disambiguated against the sources list, whose sibling is uncited"))
        else:
            disagree.append((row["key"], got, row["authors"][:60]))
    return agree, deviation, disagree


def docker_available():
    docker = shutil.which("docker")
    if not docker:
        return None
    probe = subprocess.run([docker, "info"], capture_output=True, encoding="utf-8", errors="replace")
    return docker if probe.returncode == 0 else None


def find_local_bst(explicit):
    if explicit:
        return explicit if Path(explicit).exists() else None
    found = shutil.which("kpsewhich")
    if found:
        out = subprocess.run([found, "alpha.bst"], capture_output=True, encoding="utf-8", errors="replace")
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    return None


def bst_from_image(docker, image, work):
    out = subprocess.run([docker, "run", "--rm", *calling_user_arguments(), "--entrypoint", "sh", image,
                          "-c", "cat $(kpsewhich alpha.bst)"],
                         capture_output=True, encoding="utf-8", errors="replace")
    if out.returncode != 0 or "ENTRY" not in out.stdout:
        return None
    path = Path(work, "alpha.bst")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(out.stdout)
    return path


def run_bibtex(work, binary, docker, image):
    env = dict(os.environ, BSTINPUTS=".", BIBINPUTS=".")
    if binary:
        return subprocess.run([binary, "t"], cwd=work, env=env, capture_output=True, encoding="utf-8", errors="replace")
    return subprocess.run([docker, "run", "--rm", *calling_user_arguments(), *folder_mount(work, "/w"),
                           "-w", "/w", "--entrypoint", "bibtex", image, "t"],
                          capture_output=True, encoding="utf-8", errors="replace")


def self_test():
    failures = []

    def check(got, want, label):
        if got != want:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    check(bibtex_authors("Smith, J. & Jones, A."), ("Smith, J. and Jones, A.", "personal"),
          "two personal authors")
    check(bibtex_authors("Rocha Da Lima, M., et al."),
          ("Rocha Da Lima, M. and others", "personal"), "et al. becomes 'and others'")
    check(bibtex_authors("Acme Research & Widget Labs."),
          ("{Acme Research} and {Widget Labs}", "corporate"),
          "two corporate authors are braced one by one")
    check(normalise(r"ABC{\etalchar{+}}20"), "ABC+20", "etalchar becomes '+'")
    check(normalise("{vB}99"), "vB99", "braces dropped")
    rows = bibliography_rows(
        "[Smi01] Smith, J. (2001). A thing.\n"
        "[Wal--] Walsh, K. (--). An undated thing.\n"
        "[Jon05b] Jones, A. (2005). Another thing.\n")
    check([row["key"] for row in rows], ["Smi01", "Wal--", "Jon05b"], "rows parsed")
    emitted = {rows[0]["id"]: "Smi01", rows[1]["id"]: "Wal", rows[2]["id"]: "Jon05"}
    agree, deviation, disagree = grade(rows, emitted, {"Jon05a", "Jon05b"})
    check(agree, 1, "one agreement")
    check([item[0] for item in deviation], ["Wal--", "Jon05b"], "two expected deviations")
    check(disagree, [], "nothing disagrees")
    agree, deviation, disagree = grade(rows[:1], {rows[0]["id"]: "Smi02"}, set())
    check([item[0] for item in disagree], ["Smi01"], "a different label disagrees")
    for line in failures:
        print(f"FAIL  {line}")
    print(f"self-test: {'PASS' if not failures else str(len(failures)) + ' failure(s)'}")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="Exit 0 no disagreement (or SKIPPED), 1 a label disagrees, 2 the tool failed.")
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("--references", help="the bibliography (default: manuscript.references)")
    parser.add_argument("--list", dest="sources_list",
                        help="the sources list, which owns the key namespace (default: sources.list)")
    parser.add_argument("--bibtex", help="path to a bibtex binary")
    parser.add_argument("--bst", help="path to alpha.bst")
    parser.add_argument("--no-docker", action="store_true",
                        help="never fall back to the docker image")
    parser.add_argument("--keep", help="folder to leave the .bib/.aux/.bbl in")
    parser.add_argument("--self-test", action="store_true",
                        help="test the parsing and grading on built-in examples")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    references = args.references or config.manuscript.references
    sources_list = args.sources_list or config.sources.list
    report = CheckReport(TOOL, CLASSES)

    work = args.keep or tempfile.mkdtemp(prefix="key-bibtex-check-")
    Path(work).mkdir(parents=True, exist_ok=True)
    binary = args.bibtex or shutil.which("bibtex") or shutil.which("bibtex.original")
    docker = None if (binary or args.no_docker) else docker_available()
    image = config.tools.bibtex_image
    bst = find_local_bst(args.bst)
    if not bst and docker and image:
        bst = bst_from_image(docker, image, work)
    if not (binary or docker) or not bst:
        missing = []
        if not (binary or docker):
            missing.append("no bibtex binary on PATH and no docker to run "
                           + (image or "a TeX image"))
        if not bst:
            missing.append("alpha.bst not found (pass --bst)")
        report.skip("; ".join(missing))
        return report.emit(args.format)

    try:
        with open(references, encoding="utf-8") as handle:
            rows = bibliography_rows(handle.read())
    except (OSError, TypeError) as error:
        return tool_failed(f"cannot read the bibliography: {error}", TOOL)

    if Path(bst).resolve() != Path(work, "alpha.bst").resolve():
        shutil.copy(bst, Path(work, "alpha.bst"))
    write_bibtex_input(work, rows)
    run = run_bibtex(work, binary, docker, image)
    bbl = Path(work, "t.bbl")
    if not Path(bbl).exists():
        return tool_failed(run.stdout + run.stderr, TOOL)
    with open(bbl, encoding="utf-8") as handle:
        emitted = {k: v for v, k in re.findall(r"\\bibitem\[([^\]]*)\]\{(k\d+)\}", handle.read())}

    registered = set()
    try:
        with open(sources_list, encoding="utf-8") as handle:
            registered = set(entry_keys(handle.read(), skip_fenced=True))
    except (OSError, TypeError):
        pass

    agree, deviation, disagree = grade(rows, emitted, registered)
    for key, got, why in deviation:
        report.add(key, "expected-deviation", f"bibtex prints {got}: {why}")
    for key, got, authors in disagree:
        report.add(key, "disagree", f"bibtex prints {got} for {authors}")
    if args.format == "text":
        version = (run.stdout.strip().split("\n") or [""])[0]
        where = binary if binary else "docker " + image
        print(f"{version} ({where})\n  style: {bst}\n  entries compared: {len(rows)}, "
              f"agree with bibtex: {agree}\n")
        if args.keep:
            print(f"  files kept in {work}\n")
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
