#!/usr/bin/env python3
"""Check an arXiv source bundle: unpack it into a clean folder and compile it in Docker.

arXiv takes TeX source, not a PDF made from TeX, and compiles it again on its own machines
(pdflatex, xelatex or DVI latex; full TeX Live 2025 by default). This check does the same in
the pinned full TeX Live 2025 image (tools.paper_tex_image, which holds the venue classes
acmart, IEEEtran and llncs as arXiv does), with no network, and reads the bundle against
arXiv's rules: a main .tex with \\documentclass; no .aux, .log or other LaTeX work files; no
PDF made from a .tex of the bundle; no hidden files; no space in a file name; no path that
leaves the bundle; every .bbl named like a .tex; every image the .tex uses present; and no
\\pdfoutput line, which arXiv says not to use to change the output format.

The bundle is the one named on the command line, or the newest *-arxiv.tar.gz in the
output folder of a paper (build-book.sh --arxiv writes it). The engine is paper.engine
unless --engine names one. SKIPPED, with the reason, without Docker, without a bundle, or
when the image is missing and cannot be pulled.
"""

import argparse
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parents[2] / "lib"))
sys.path.insert(0, str(SCRIPTS))

from book_config import ConfigError, PAPER_ENGINES, add_config_arguments, config_from_args
from check_output import (ADVISORY, DEFECT, INFORMATIONAL, CheckReport, add_output_arguments,
                          run_main, tool_failed)
from container_run import calling_user_arguments, folder_mount
from output_files import newest_in_folder
from paper_source import find_image, image_paths, name_problem, without_comments

TOOL = "arxiv-bundle-check"
BUNDLE_ENDING = "-arxiv.tar.gz"
CLASSES = {
    "unsafe-path": DEFECT,
    "space-in-name": DEFECT,
    "hidden-file": DEFECT,
    "work-file": DEFECT,
    "pdf-from-tex": DEFECT,
    "bbl-name": DEFECT,
    "no-main-tex": DEFECT,
    "pdfoutput-line": DEFECT,
    "missing-image": DEFECT,
    "compile-failed": DEFECT,
    "several-main-files": ADVISORY,
    "compiled": INFORMATIONAL,
}
WORK_FILE_ENDINGS = (".aux", ".log", ".out", ".toc", ".lof", ".lot", ".fls", ".fdb_latexmk",
                     ".synctex.gz", ".xdv", ".dvi", ".blg", ".bcf", ".run.xml", ".nav", ".snm")
DOCUMENT_CLASS = re.compile(r"\\documentclass\b")
PDF_OUTPUT = re.compile(r"\\pdfoutput\b")
LATEXMK_OPTION = {"xelatex": "-xelatex", "pdflatex": "-pdf"}
COMPILE_TIME_LIMIT = 600
DOCKER_CHECK_TIME_LIMIT = 30
PULL_TIME_LIMIT = 1800


class SkipCheck(Exception):
    pass


def member_problems(names):
    found = []
    for name in names:
        problem = name_problem(name)
        if problem and " " in name:
            found.append((name, "space-in-name", problem))
        elif problem:
            found.append((name, "unsafe-path", problem))
        elif any(part.startswith(".") for part in PurePosixPath(name).parts):
            found.append((name, "hidden-file", "hidden files are not part of a source bundle"))
    return found


def file_members(bundle):
    with tarfile.open(bundle) as opened:
        return [member for member in opened.getmembers() if member.isfile()]


def shown_name(member):
    return str(PurePosixPath(member.name))


def unpack(bundle, target, report):
    members = file_members(bundle)
    problems = member_problems([shown_name(member) for member in members])
    for name, finding_class, message in problems:
        report.add(name, finding_class, message)
    refused = {name for name, finding_class, _ in problems if finding_class == "unsafe-path"}
    kept = []
    with tarfile.open(bundle) as opened:
        for member in members:
            name = shown_name(member)
            if name in refused:
                continue
            destination = Path(target) / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with opened.extractfile(member) as source, open(destination, "wb") as written:
                shutil.copyfileobj(source, written)
            kept.append(name)
    return kept


def file_rules(names, folder, report):
    tex_stems = {str(PurePosixPath(name).with_suffix("")) for name in names
                 if name.lower().endswith(".tex")}
    for name in names:
        lower = name.lower()
        stem = str(PurePosixPath(name).with_suffix(""))
        if lower.endswith(WORK_FILE_ENDINGS):
            report.add(name, "work-file", "a LaTeX work file; arXiv makes its own, leave it out")
        elif lower.endswith(".pdf") and stem in tex_stems:
            report.add(name, "pdf-from-tex",
                       "a PDF made from a .tex of the bundle; arXiv wants the TeX source only")
        elif lower.endswith(".bbl") and stem not in tex_stems:
            report.add(name, "bbl-name", "a .bbl must have the name of the main .tex "
                                         f"({PurePosixPath(name).name} has no .tex beside it)")
    main_files = []
    for name in sorted(names):
        if not name.lower().endswith(".tex"):
            continue
        text = without_comments((Path(folder) / name).read_text(encoding="utf-8",
                                                                errors="replace"))
        if PDF_OUTPUT.search(text):
            report.add(name, "pdfoutput-line",
                       "\\pdfoutput is set; arXiv says not to use it to change the output format")
        if DOCUMENT_CLASS.search(text):
            main_files.append(name)
        for image in image_paths(text):
            if find_image(image, [folder])[1] is None:
                report.add(name, "missing-image", f"uses {image}, which is not in the bundle")
    return main_files


def docker_ready():
    if not shutil.which("docker"):
        raise SkipCheck("docker not found on PATH; the bundle is compiled in Docker")
    try:
        answered = subprocess.run(["docker", "info"], capture_output=True,
                                  timeout=DOCKER_CHECK_TIME_LIMIT, check=False)
    except (OSError, subprocess.TimeoutExpired) as problem:
        raise SkipCheck(f"docker did not answer ({problem})") from problem
    if answered.returncode != 0:
        raise SkipCheck("docker is installed but not running")


def image_ready(image):
    present = subprocess.run(["docker", "image", "inspect", image], capture_output=True,
                             timeout=DOCKER_CHECK_TIME_LIMIT, check=False)
    if present.returncode == 0:
        return
    try:
        pulled = subprocess.run(["docker", "pull", image], capture_output=True, encoding="utf-8",
                                errors="replace", timeout=PULL_TIME_LIMIT, check=False)
    except subprocess.TimeoutExpired as problem:
        raise SkipCheck(f"pulling {image} (tools.paper_tex_image) took too long") from problem
    if pulled.returncode != 0:
        last_line = (pulled.stderr or pulled.stdout).strip().splitlines()[-1:]
        raise SkipCheck(f"the TeX Live image {image} (tools.paper_tex_image) is not here and "
                        f"could not be pulled ({' '.join(last_line)})")


def first_error(log_text):
    for line in log_text.splitlines():
        if line.startswith("!") or re.match(r"^\S+\.tex:\d+: ", line):
            return line.strip()
    lines = [line for line in log_text.splitlines() if line.strip()]
    return lines[-1].strip() if lines else "no output"


def compile_bundle(folder, main_name, engine, image, report):
    command = ["docker", "run", "--rm", "--network", "none", *calling_user_arguments(),
               "-e", "HOME=/tmp", "-e", "TEXMFVAR=/tmp/texmf-var",
               "-e", "max_print_line=1000",
               *folder_mount(folder, "/work"), "-w", "/work", "--entrypoint", "latexmk",
               image, LATEXMK_OPTION[engine], "-interaction=nonstopmode", "-halt-on-error",
               "-file-line-error", main_name]
    try:
        finished = subprocess.run(command, capture_output=True, encoding="utf-8",
                                  errors="replace", timeout=COMPILE_TIME_LIMIT, check=False)
    except subprocess.TimeoutExpired:
        report.add(main_name, "compile-failed",
                   f"{engine} did not finish within {COMPILE_TIME_LIMIT} seconds")
        return
    pdf = (Path(folder) / main_name).with_suffix(".pdf")
    if finished.returncode != 0 or not pdf.is_file():
        report.add(main_name, "compile-failed",
                   f"{engine} failed: {first_error(finished.stdout + finished.stderr)}")
        return
    report.add(main_name, "compiled", f"compiles with {engine} in {image} in a clean folder")


def check_bundle(bundle, engine, image, report):
    docker_ready()
    image_ready(image)
    with tempfile.TemporaryDirectory(prefix="arxiv-bundle-") as folder:
        names = unpack(bundle, folder, report)
        main_files = file_rules(names, folder, report)
        if not main_files:
            report.add(Path(bundle).name, "no-main-tex", "no .tex file with \\documentclass")
            return
        if len(main_files) > 1:
            report.add(Path(bundle).name, "several-main-files",
                       f"{len(main_files)} files have \\documentclass ({', '.join(main_files)}); "
                       f"arXiv picks one, this check compiles {main_files[0]}")
        compile_bundle(folder, main_files[0], engine, image, report)


def chosen_bundle(args, config):
    if args.bundle:
        return Path(args.bundle)
    if not config.is_paper:
        raise SkipCheck(f"the book is not a paper (kind: {config.kind}), so it has no "
                        f"arXiv bundle")
    newest = newest_in_folder(config.work.output, BUNDLE_ENDING)
    if newest is None:
        raise SkipCheck(f"no *{BUNDLE_ENDING} in {config.work.output}; build one with "
                        f"build-book.sh --arxiv")
    return newest


def self_test():
    checks = []
    with tempfile.TemporaryDirectory() as scratch:
        folder = Path(scratch)
        (folder / "images").mkdir()
        (folder / "images" / "plot.pdf").write_bytes(b"%PDF-1.4\n")
        (folder / "main.tex").write_text(
            "\\pdfoutput=1\n\\documentclass{article}\n\\begin{document}\n"
            "\\includegraphics{images/plot.pdf}\\includegraphics{images/gone}\n"
            "\\end{document}\n", encoding="utf-8")
        names = ["main.tex", "images/plot.pdf", "main.aux", "main.pdf", "other.bbl"]
        for extra in ("main.aux", "main.pdf", "other.bbl"):
            (folder / extra).write_text("x", encoding="utf-8")
        report = CheckReport(TOOL, CLASSES)
        main_files = file_rules(names, folder, report)
        found = sorted((key, finding_class) for key, finding_class, _ in report.items)
        checks.append(("the main .tex is found", main_files, ["main.tex"]))
        checks.append(("every broken rule is reported", found, [
            ("main.aux", "work-file"), ("main.pdf", "pdf-from-tex"), ("main.tex", "missing-image"),
            ("main.tex", "pdfoutput-line"), ("other.bbl", "bbl-name")]))
        checks.append(("a figure PDF is not the PDF made from the .tex",
                       any(key == "images/plot.pdf" for key, _, _ in report.items), False))
    member_found = sorted((name, finding_class) for name, finding_class, _ in member_problems(
        ["main.tex", "my figure.png", "../escape.tex", "/etc/passwd", ".hidden", "a/.cache/x"]))
    checks.append(("member names break the rules they should", member_found, sorted([
        ("/etc/passwd", "unsafe-path"), ("../escape.tex", "unsafe-path"), (".hidden", "hidden-file"),
        ("a/.cache/x", "hidden-file"), ("my figure.png", "space-in-name")])))
    checks.append(("only the engines arXiv supports can be chosen",
                   sorted(LATEXMK_OPTION) == sorted(PAPER_ENGINES), True))
    checks.append(("the LaTeX error line is the one reported",
                   first_error("This is XeTeX\n./main.tex:4: Undefined control sequence.\nmore"),
                   "./main.tex:4: Undefined control sequence."))
    failures = [(name, got, expected) for name, got, expected in checks if got != expected]
    for name, got, expected in failures:
        print(f"FAIL  {name}: got {got!r}, expected {expected!r}")
    print(f"arxiv-bundle-check self-test: {len(checks) - len(failures)}/{len(checks)} passed")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="exit codes: 0 no defects (or SKIPPED), 1 defects, "
                                            "2 the tool failed")
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("bundle", nargs="?",
                        help=f"the bundle to check (default: the newest *{BUNDLE_ENDING} in "
                             f"the paper's output folder)")
    parser.add_argument("--engine", choices=PAPER_ENGINES,
                        help="the LaTeX engine (default: paper.engine)")
    parser.add_argument("--self-test", action="store_true",
                        help="run the built-in tests; needs no Docker")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.bundle and not Path(args.bundle).is_file():
        return tool_failed(f"no such bundle: {args.bundle}", TOOL)
    try:
        config = config_from_args(args, targets=[args.bundle] if args.bundle else None)
    except ConfigError as problem:
        return tool_failed(str(problem), TOOL)
    report = CheckReport(TOOL, CLASSES)
    try:
        bundle = chosen_bundle(args, config)
        check_bundle(bundle, args.engine or config.paper.engine, config.tools.paper_tex_image,
                     report)
    except SkipCheck as reason:
        report.skip(str(reason))
    except tarfile.TarError as problem:
        return tool_failed(f"cannot read the bundle: {problem}", TOOL)
    return report.emit(args.format)


if __name__ == "__main__":
    run_main(main, TOOL)
