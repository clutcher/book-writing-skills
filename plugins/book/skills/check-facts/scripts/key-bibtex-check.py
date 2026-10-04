#!/usr/bin/env python3
"""Run the real bibtex with alpha.bst over the book's .bib and compare its labels with the keys.

Every other key check asks whether a key agrees with this plugin's own reading of the
alpha rule (lib/citation_key.py). This one leaves that reading behind: it runs bibtex
with Patashnik's alpha.bst on a copy of the book's .bib (sources.bibliography), with every
entry cited (`\\nocite{*}`), and compares the label bibtex prints for each entry with its key.
Two rules the keys rest on (a hyphen splits name tokens; every token keeps its own case)
live in bibtex's built-in `format.name$`, not in alpha.bst, so only running the program
settles them. Letters outside ASCII are written as LaTeX commands in the copy, so the
8-bit bibtex counts them as one letter each.

It needs a bibtex binary and alpha.bst. It looks for them on PATH (kpsewhich finds
alpha.bst); when they are missing it runs both from a docker image as the calling user,
with no network: the book's `tools.bibtex_image`, or for a paper `tools.paper_tex_image`,
the image the paper build already uses. The first run pulls the image (several GB). With
neither it prints SKIPPED and why. A skipped check is "not verified", never a pass.

Two conventions are expected deviations, reported but not counted wrong:
  * a key fragment is ASCII-folded (alpha keeps the accent command)
  * an undatable work takes `--` for its year (alpha appends nothing)

Classes:
  disagree             DEFECT        bibtex prints a different label than the key
  expected-deviation   INFORMATIONAL one of the two conventions above
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

sys.dont_write_bytecode = True

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import add_config_arguments, load_book, tool_failed
from check_output import DEFECT, INFORMATIONAL, CheckReport, add_output_arguments
from bibliography import BibliographyError, parse_bibliography
from container_run import calling_user_arguments, folder_mount

TOOL = "key-bibtex-check"
DOCKER_PROBE_SECONDS = 60
IMAGE_RUN_SECONDS = 1800
BIBTEX_RUN_SECONDS = 300
CLASSES = {"disagree": DEFECT, "expected-deviation": INFORMATIONAL}

LETTER_COMMANDS = {
    "Ł": "L", "ł": "l", "Ø": "O", "ø": "o", "ß": "ss", "Æ": "AE", "æ": "ae",
    "Œ": "OE", "œ": "oe", "ı": "i",
}
ACCENT_COMMANDS = {
    "\u0301": "'", "\u0300": "`", "\u0308": '"', "\u0302": "^", "\u0303": "~",
    "\u0304": "=", "\u0307": ".", "\u0327": "c ", "\u030c": "v ", "\u0306": "u ",
    "\u030a": "r ", "\u030b": "H ", "\u0328": "k ",
}
LETTER_COMMAND = re.compile(r"\{\\(ss|ae|AE|oe|OE|o|O|l|L|i)\}")
ACCENT_COMMAND = re.compile(r"\\(?:[`'\"^~=.]|[cvuHrk] )")


def latex_letters(text):
    written = []
    for character in text:
        if character in LETTER_COMMANDS:
            written.append("{\\" + LETTER_COMMANDS[character] + "}")
            continue
        base, *marks = unicodedata.normalize("NFD", character)
        commands = [ACCENT_COMMANDS.get(mark) for mark in marks]
        if marks and all(commands):
            written.append("{" + "".join("\\" + command for command in commands) + base + "}")
        else:
            written.append(character)
    return "".join(written)


def ascii_fold(label):
    label = normalise(LETTER_COMMAND.sub(lambda match: match.group(1), label))
    return re.sub(r"['\"^`]", "", ACCENT_COMMAND.sub("", label))


def normalise(label):
    label = label.replace(r"{\etalchar{+}}", "+")
    while re.search(r"\{([^{}]*)\}", label):
        label = re.sub(r"\{([^{}]*)\}", r"\1", label)
    return label


def write_bibtex_input(work, bibliography_text):
    with open(Path(work, "t.bib"), "w", encoding="utf-8") as handle:
        handle.write(latex_letters(bibliography_text))
    with open(Path(work, "t.aux"), "w", encoding="utf-8") as handle:
        handle.write("\\relax\n\\citation{*}\n\\bibstyle{alpha}\n\\bibdata{t}\n")


def grade(entries, emitted):
    agree, deviation, disagree = 0, [], []
    for entry in entries:
        emitted_label = emitted.get(entry.key, "(none)")
        got = normalise(emitted_label)
        if got == entry.key:
            agree += 1
        elif not entry.field("year") and entry.key == got + "--":
            deviation.append((entry.key, got, "the `--` year is a convention alpha cannot produce"))
        elif got and ascii_fold(emitted_label) == entry.key:
            deviation.append((entry.key, got, "key fragments are ASCII-folded"))
        else:
            names = entry.field("author") or entry.field("editor") or "no author or editor"
            disagree.append((entry.key, got, names[:60]))
    return agree, deviation, disagree


def read_labels(bbl):
    with open(bbl, encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    return {key: label for label, key in re.findall(r"\\bibitem\[([^\]]*)\]\{([^}]*)\}", text)}


def docker_available():
    docker = shutil.which("docker")
    if not docker:
        return None
    try:
        probe = subprocess.run([docker, "info"], capture_output=True, encoding="utf-8",
                               errors="replace", timeout=DOCKER_PROBE_SECONDS)
    except subprocess.TimeoutExpired:
        return None
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
    out = subprocess.run([docker, "run", "--rm", "--network", "none", *calling_user_arguments(),
                          "--entrypoint", "sh", image, "-c", "cat $(kpsewhich alpha.bst)"],
                         capture_output=True, encoding="utf-8", errors="replace",
                         timeout=IMAGE_RUN_SECONDS)
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
    return subprocess.run([docker, "run", "--rm", "--network", "none", *calling_user_arguments(),
                           *folder_mount(work, "/w"), "-w", "/w", "--entrypoint", "bibtex", image,
                           "t"],
                          capture_output=True, encoding="utf-8", errors="replace",
                          timeout=BIBTEX_RUN_SECONDS)


SELF_TEST_BIBLIOGRAPHY = """@book{Smi01,
  author = {Smith, John},
  title = {A Thing},
  year = {2001},
}

@misc{Wal--,
  author = {Walsh, Kim},
  title = {An Undated Thing},
}

@book{Sor99,
  author = {Sørensen, Karl},
  title = {A Third Thing},
  year = {1999},
}
"""


def self_test():
    failures = []

    def check(got, want, label):
        if got != want:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    check(normalise(r"ABC{\etalchar{+}}20"), "ABC+20", "etalchar becomes '+'")
    check(normalise("{vB}99"), "vB99", "braces dropped")
    check(latex_letters("Sørensen, K."), "S{\\o}rensen, K.", "a letter with no accent form becomes its command")
    check(latex_letters("Déniz, M."), "D{\\'e}niz, M.", "an accent becomes an accent command")
    check(ascii_fold("S{\\o}r99"), "Sor99", "a letter command folds to its letters")
    check(ascii_fold("{\\L}uk99"), "Luk99", "a capital letter command folds too")
    check(ascii_fold("D{\\'e}n96"), "Den96", "an accent command is dropped")
    check(ascii_fold("O'B03"), "OB03", "an apostrophe is dropped")
    entries = list(parse_bibliography(SELF_TEST_BIBLIOGRAPHY).entries.values())
    with tempfile.TemporaryDirectory() as work:
        write_bibtex_input(work, SELF_TEST_BIBLIOGRAPHY)
        written = Path(work, "t.bib").read_text(encoding="utf-8")
        check("S{\\o}rensen" in written, True, "the copy writes letters as LaTeX commands")
        check("\\citation{*}" in Path(work, "t.aux").read_text(encoding="utf-8"), True,
              "every entry is cited")
        Path(work, "t.bbl").write_text(
            "\\begin{thebibliography}{Smi01}\n\\bibitem[Smi01]{Smi01}\nJ.~Smith.\n"
            "\\bibitem[Wal]{Wal--}\nK.~Walsh.\n\\bibitem[S{\\o}r99]{Sor99}\nK.~S.\n",
            encoding="utf-8")
        emitted = read_labels(Path(work, "t.bbl"))
    check(emitted, {"Smi01": "Smi01", "Wal--": "Wal", "Sor99": "S{\\o}r99"}, "labels read")
    agree, deviation, disagree = grade(entries, emitted)
    check(agree, 1, "one agreement")
    check([item[0] for item in deviation], ["Wal--", "Sor99"], "two expected deviations")
    check(disagree, [], "nothing disagrees")
    agree, deviation, disagree = grade(entries[:1], {"Smi01": "Smi02"})
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
    parser.add_argument("--bibliography", help="the .bib file (default: sources.bibliography)")
    parser.add_argument("--bibtex", help="path to a bibtex binary")
    parser.add_argument("--bst", help="path to alpha.bst")
    parser.add_argument("--no-docker", action="store_true",
                        help="never fall back to the docker image")
    parser.add_argument("--keep", help="folder to leave the .bib/.aux/.bbl in")
    parser.add_argument("--self-test", action="store_true",
                        help="test the reading and grading on built-in examples")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    bibliography_path = args.bibliography or config.sources.bibliography
    report = CheckReport(TOOL, CLASSES)
    if report.skip_unless_present(bibliography_path, "bibliography"):
        return report.emit(args.format)
    try:
        bibliography_text = Path(bibliography_path).read_text(encoding="utf-8")
        entries = list(parse_bibliography(bibliography_text).entries.values())
    except (OSError, BibliographyError) as error:
        return tool_failed(f"cannot read the bibliography: {error}", TOOL)
    if not entries:
        if args.format == "text":
            print("entries compared: 0\n")
        return report.emit(args.format)

    work = args.keep or tempfile.mkdtemp(prefix="key-bibtex-check-")
    Path(work).mkdir(parents=True, exist_ok=True)
    binary = args.bibtex or shutil.which("bibtex") or shutil.which("bibtex.original")
    docker = None if (binary or args.no_docker) else docker_available()
    image = config.tools.paper_tex_image if config.is_paper else config.tools.bibtex_image
    bst = find_local_bst(args.bst)
    try:
        if not bst and docker and image:
            bst = bst_from_image(docker, image, work)
    except subprocess.TimeoutExpired:
        return tool_failed(f"docker did not finish within {IMAGE_RUN_SECONDS} s ({image})", TOOL)
    if not (binary or docker) or not bst:
        missing = []
        if not (binary or docker):
            missing.append("no bibtex binary on PATH and no docker to run "
                           + (image or "a TeX image"))
        if not bst:
            missing.append("alpha.bst not found (pass --bst)")
        report.skip("; ".join(missing))
        return report.emit(args.format)

    if Path(bst).resolve() != Path(work, "alpha.bst").resolve():
        shutil.copy(bst, Path(work, "alpha.bst"))
    write_bibtex_input(work, bibliography_text)
    try:
        run = run_bibtex(work, binary, docker, image)
    except subprocess.TimeoutExpired:
        return tool_failed(f"bibtex did not finish within {BIBTEX_RUN_SECONDS} s", TOOL)
    bbl = Path(work, "t.bbl")
    if not bbl.exists():
        return tool_failed(run.stdout + run.stderr, TOOL)
    emitted = read_labels(bbl)
    if not args.keep:
        shutil.rmtree(work, ignore_errors=True)

    agree, deviation, disagree = grade(entries, emitted)
    for key, got, why in deviation:
        report.add(key, "expected-deviation", f"bibtex prints {got}: {why}")
    for key, got, names in disagree:
        report.add(key, "disagree", f"bibtex prints {got} for {names}")
    if args.format == "text":
        version = (run.stdout.strip().split("\n") or [""])[0]
        where = binary if binary else "docker " + image
        print(f"{version} ({where})\n  style: {bst}\n  entries compared: {len(entries)}, "
              f"agree with bibtex: {agree}\n")
        if args.keep:
            print(f"  files kept in {work}\n")
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
