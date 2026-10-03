#!/usr/bin/env python3
"""Gather the source files of a paper: the main .tex and the images it uses.

build-book.sh calls it twice for the paper edition. `stage` copies the .tex pandoc wrote and
every image its \\includegraphics lines name into a build folder, where LaTeX then runs.
`bundle` writes the arXiv source bundle (.tar.gz) from that folder: the main .tex, the images
it uses and a .bbl named like the main .tex, and nothing else (no .aux, .log or the PDF made
from the .tex). A file name with a space, an absolute path or a path that leaves the folder
stops both steps, because arXiv refuses such names. arxiv-bundle-check.py reads bundles with
the same rules.
"""

import argparse
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True

EXIT_TOOL_FAILED = 2
IMAGE_COMMAND = "\\includegraphics"
IMAGE_ENDINGS = (".pdf", ".png", ".jpg", ".jpeg", ".eps")
BIBLIOGRAPHY_ENDING = ".bbl"


class SourceProblem(Exception):
    pass


def skip_bracket_group(text, at):
    if at >= len(text) or text[at] != "[":
        return at
    depth = 0
    for position in range(at, len(text)):
        character = text[position]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
        elif character == "]" and depth == 0:
            return position + 1
    return len(text)


def brace_group(text, at):
    while at < len(text) and text[at].isspace():
        at += 1
    if at >= len(text) or text[at] != "{":
        return None
    depth = 0
    for position in range(at, len(text)):
        if text[position] == "{":
            depth += 1
        elif text[position] == "}":
            depth -= 1
            if depth == 0:
                return text[at + 1:position]
    return None


def without_comments(text):
    kept = []
    for line in text.splitlines():
        cut = next((index for index, character in enumerate(line)
                    if character == "%" and (index == 0 or line[index - 1] != "\\")), None)
        kept.append(line if cut is None else line[:cut])
    return "\n".join(kept)


def image_paths(tex_text):
    text = without_comments(tex_text)
    found = []
    start = 0
    while True:
        at = text.find(IMAGE_COMMAND, start)
        if at < 0:
            return found
        after = at + len(IMAGE_COMMAND)
        if after < len(text) and text[after] == "*":
            after += 1
        path = brace_group(text, skip_bracket_group(text, after))
        if path and path.strip() not in found:
            found.append(path.strip())
        start = after


def name_problem(relative):
    if " " in relative:
        return f"{relative!r} has a space in its name; arXiv refuses such names"
    pure = PurePosixPath(relative.replace("\\", "/"))
    if pure.is_absolute() or (len(relative) > 1 and relative[1] == ":"):
        return f"{relative!r} is an absolute path; write it relative to the manuscript"
    if ".." in pure.parts:
        return f"{relative!r} leaves the manuscript folder; keep images inside it"
    return None


def candidates_for(relative):
    if PurePosixPath(relative).suffix.lower() in IMAGE_ENDINGS:
        return [relative]
    return [relative] + [relative + ending for ending in IMAGE_ENDINGS]


def find_image(relative, folders):
    for folder in folders:
        for candidate in candidates_for(relative):
            path = Path(folder) / candidate
            if path.is_file():
                return candidate, path
    return None, None


def used_images(tex_file, folders):
    images = []
    for relative in image_paths(Path(tex_file).read_text(encoding="utf-8")):
        problem = name_problem(relative)
        if problem:
            raise SourceProblem(problem)
        found_name, found_path = find_image(relative, folders)
        if found_path is None:
            places = ", ".join(str(folder) for folder in folders)
            raise SourceProblem(f"image {relative!r} is not in {places}")
        images.append((found_name, found_path))
    return images


def stage(tex_file, folders, target):
    tex_file = Path(tex_file)
    problem = name_problem(tex_file.name)
    if problem:
        raise SourceProblem(problem)
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(tex_file, target / tex_file.name)
    copied = [tex_file.name]
    for name, path in used_images(tex_file, folders):
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target / name)
        copied.append(name)
    return copied


def bundle_members(folder, main_name):
    folder = Path(folder)
    main = folder / main_name
    if not main.is_file():
        raise SourceProblem(f"no {main_name} in {folder}")
    members = [main_name] + [name for name, _ in used_images(main, [folder])]
    bibliography = main.with_suffix(BIBLIOGRAPHY_ENDING)
    if bibliography.is_file():
        members.append(bibliography.name)
    return members


def clean_member(info):
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


def write_bundle(folder, main_name, output):
    members = bundle_members(folder, main_name)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as bundle:
        for name in members:
            bundle.add(Path(folder) / name, arcname=name, recursive=False, filter=clean_member)
    return members


def self_test():
    checks = []
    tex = ("\\documentclass{article}\n\\begin{document}\n"
           "\\pandocbounded{\\includegraphics[keepaspectratio,alt={A plot [left]}]{images/plot.pdf}}\n"
           "\\includegraphics{images/photo}\n"
           "% \\includegraphics{images/hidden.png}\n"
           "\\end{document}\n")
    checks.append(("image paths are read past options with braces", image_paths(tex),
                   ["images/plot.pdf", "images/photo"]))
    checks.append(("a space in a name is refused", name_problem("my plot.pdf") is not None, True))
    checks.append(("a path out of the folder is refused", name_problem("../plot.pdf") is not None, True))
    checks.append(("an absolute path is refused", name_problem("/tmp/plot.pdf") is not None, True))
    checks.append(("a plain relative path is accepted", name_problem("images/plot.pdf"), None))
    with tempfile.TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        manuscript = scratch / "manuscript"
        (manuscript / "images").mkdir(parents=True)
        (manuscript / "images" / "plot.pdf").write_bytes(b"%PDF-1.4\n")
        (manuscript / "images" / "photo.png").write_bytes(b"\x89PNG\r\n")
        (manuscript / "images" / "unused.png").write_bytes(b"\x89PNG\r\n")
        tex_file = scratch / "out" / "paper.tex"
        tex_file.parent.mkdir()
        tex_file.write_text(tex, encoding="utf-8")
        build = scratch / "build"
        copied = stage(tex_file, [manuscript, scratch], build)
        checks.append(("stage copies the .tex and the images it uses", sorted(copied),
                       ["images/photo.png", "images/plot.pdf", "paper.tex"]))
        for leftover in ("paper.aux", "paper.log", "paper.pdf", ".hidden", "paper.bbl"):
            (build / leftover).write_text("x", encoding="utf-8")
        bundle = scratch / "paper-arxiv.tar.gz"
        write_bundle(build, "paper.tex", bundle)
        with tarfile.open(bundle) as opened:
            names = sorted(opened.getnames())
        checks.append(("the bundle holds the .tex, its images and its .bbl only", names,
                       ["images/photo.png", "images/plot.pdf", "paper.bbl", "paper.tex"]))
        (manuscript / "images" / "plot.pdf").unlink()
        try:
            stage(tex_file, [manuscript], scratch / "again")
            missing_refused = False
        except SourceProblem:
            missing_refused = True
        checks.append(("a missing image stops the stage", missing_refused, True))
    failures = [(name, got, expected) for name, got, expected in checks if got != expected]
    for name, got, expected in failures:
        print(f"FAIL  {name}: got {got!r}, expected {expected!r}")
    print(f"paper_source self-test: {len(checks) - len(failures)}/{len(checks)} passed")
    return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--self-test", action="store_true",
                        help="run the built-in tests in a temporary folder")
    actions = parser.add_subparsers(dest="action")
    stage_parser = actions.add_parser("stage", help="copy the .tex and the images it uses "
                                                    "into a build folder")
    stage_parser.add_argument("--tex", required=True, help="the .tex file pandoc wrote")
    stage_parser.add_argument("--search", action="append", required=True, metavar="FOLDER",
                              help="a folder the image paths are relative to, tried in order "
                                   "(repeatable)")
    stage_parser.add_argument("--to", required=True, metavar="FOLDER", help="the build folder")
    bundle_parser = actions.add_parser("bundle", help="write the arXiv source bundle")
    bundle_parser.add_argument("--folder", required=True, help="the build folder")
    bundle_parser.add_argument("--main", required=True, help="the main .tex file name")
    bundle_parser.add_argument("--output", required=True, help="the .tar.gz to write")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()
    try:
        if args.action == "stage":
            copied = stage(args.tex, args.search, args.to)
            print(f"staged {len(copied)} file(s): {' '.join(copied)}")
        elif args.action == "bundle":
            members = write_bundle(args.folder, args.main, args.output)
            print(f"wrote {args.output} with {len(members)} file(s): {' '.join(members)}")
        else:
            parser.print_help()
            return EXIT_TOOL_FAILED
    except (SourceProblem, OSError) as problem:
        sys.stderr.write(f"paper_source: {problem}\n")
        return EXIT_TOOL_FAILED
    return 0


if __name__ == "__main__":
    sys.exit(main())
