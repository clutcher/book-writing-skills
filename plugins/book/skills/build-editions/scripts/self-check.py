#!/usr/bin/env python3
import argparse
import re
import shutil
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent
FIXTURES = SCRIPTS / "fixtures"
BUILD = SCRIPTS / "build-book.sh"
sys.path.insert(0, str(SKILL.parents[1] / "lib"))

from command_runs import python_command, run_command

TIME_LIMIT = 300
SELF_TESTS = ("compute-leading.py", "diff-preprocess.py", "output_files.py",
              "flatten-code-lines.py", "filter-settings.py", "epub-check.py",
              "code-font-check.py")

DESCRIPTION = """Runs every build script's self-test on the fixture books in scripts/fixtures/.
Needs Python, and bash for the steps that read settings through build-book.sh (they print
SKIPPED without bash): no Docker, no network, no real book."""

EPILOG = "exit codes: 0 every step passed, 1 otherwise."


class Steps:
    def __init__(self):
        self.failed = []

    def run(self, name, step):
        passed, detail = step()
        if passed:
            print(f"PASS  {name}", flush=True)
        else:
            print(f"FAIL  {name}", flush=True)
            for line in detail.splitlines():
                print(f"      {line}")
            self.failed.append(name)

    def skip(self, name, reason):
        print(f"SKIPPED  {name}: {reason}", flush=True)


def command_passes(command):
    def step():
        result = run_command(command, TIME_LIMIT)
        return result.passed, result.output
    return step


def bash_command(*arguments):
    return [shutil.which("bash"), *arguments]


def show_settings(book, *options, folder=None):
    where = FIXTURES / book / folder if folder else FIXTURES / book
    return run_command(bash_command(BUILD, "--show-settings", *options), TIME_LIMIT,
                       cwd=where).output


def output_contains(expected, book, *options, folder=None):
    def step():
        output = show_settings(book, *options, folder=folder)
        return expected in output, output
    return step


def output_has_line(expected, book, *options, folder=None):
    def step():
        output = show_settings(book, *options, folder=folder)
        return expected in output.splitlines(), output
    return step


def build_refuses(book, *options):
    def step():
        result = run_command(bash_command(BUILD, "--show-settings", *options), TIME_LIMIT,
                             cwd=FIXTURES / book)
        return result.exit_code != 0, result.output
    return step


def flat(text):
    return re.sub(r"\s+", " ", text).strip()


def same_licence_text():
    css = (SKILL / "assets" / "epub.css").read_text(encoding="utf-8")
    blocks = [block for block in re.findall(r"/\*(.*?)\*/", css, re.S) if "SIL" in block]
    licence = (SKILL / "assets" / "fonts" / "OFL.txt").read_text(encoding="utf-8")
    return len(blocks) == 1 and flat(licence) in flat(blocks[0]), "licence text differs"


def template_has_three_changes():
    pristine = (SKILL / "assets" / "epub3-template.pandoc-default.html").read_text(
        encoding="utf-8")
    vendored = (SKILL / "assets" / "epub3-template.html").read_text(encoding="utf-8")
    cover_svg_end = 'preserveAspectRatio="xMidYMid">'
    expected = pristine.replace(
        "<title>$pagetitle$</title>",
        "<title>$if(title)$$title$$else$$pagetitle$$endif$</title>").replace(
        "  <style>\n$if(csl-css)$\n    $styles.citations.html()$\n$endif$\n"
        "$if(highlighting-css)$\n    /* CSS for syntax highlighting */\n"
        "    $highlighting-css$\n$endif$\n  </style>\n",
        "$if(csl-css)$\n  <style>\n    $styles.citations.html()$\n  </style>\n$endif$\n").replace(
        cover_svg_end,
        'preserveAspectRatio="xMidYMid" role="img">\n'
        '<title>$if(pagetitle)$Cover: $pagetitle$$else$Cover$endif$</title>')
    return expected == vendored, "the vendored template differs in more than three places"


def script_steps(steps):
    for script in sorted(SCRIPTS.glob("*.py")):
        steps.run(f"{script.name} --help", command_passes(python_command(script, "--help")))
    for name in SELF_TESTS:
        steps.run(f"{Path(name).stem} self-test",
                  command_passes(python_command(SCRIPTS / name, "--self-test")))
    steps.run("key-pattern-check (filter keys match lib/citation_key.py)",
              command_passes(python_command(SCRIPTS / "key-pattern-check.py")))
    steps.run("code-font-check says SKIPPED when the manuscript folder holds no file",
              code_font_check_skips_a_missing_manuscript)


def code_font_check_skips_a_missing_manuscript():
    result = run_command(python_command(SCRIPTS / "code-font-check.py", "--config",
                                        FIXTURES / "new-book" / "book.yaml", "--set",
                                        "manuscript.dir=manuscrpt"), TIME_LIMIT)
    return (result.passed and result.last_line().startswith("SKIPPED   no manuscript files at"),
            result.output)


def settings_steps(steps):
    steps.run("build-book.sh --help", command_passes(bash_command(BUILD, "--help")))
    for shell_script in sorted(SCRIPTS.glob("*.sh")):
        steps.run(f"{shell_script.name} syntax",
                  command_passes(bash_command("-n", shell_script)))
    steps.run("new layout: settings come from book.yaml",
              output_contains("FONT_SIZE=11pt", "new-book"))
    steps.run("new layout: output goes to .book/output",
              output_contains("/new-book/.book/output/a-small-test-book-example.pdf",
                              "new-book", "--final"))
    steps.run("new layout: language comes from book.yaml",
              output_contains("BOOK_LANGUAGE=en-GB", "new-book"))
    steps.run("old layout: settings come from CLAUDE.md",
              output_contains("FONT_SIZE=11.5pt", "old-book"))
    steps.run("old layout: a comment after a value is stripped",
              output_contains("GENERATE_TOC=false", "old-book"))
    steps.run("old layout: output goes to output/",
              output_contains("/old-book/output/an-old-layout-book-example.pdf", "old-book",
                              "--final"))
    steps.run("new layout: accessibility summary comes from book.yaml",
              output_has_line("ACCESSIBILITY_SUMMARY=A short test summary.", "new-book"))
    steps.run("old layout: no accessibility summary unless the book writes one",
              output_has_line("ACCESSIBILITY_SUMMARY=", "old-book"))
    steps.run("files are in natural order by default",
              output_has_line("MANUSCRIPT_FILES=manuscript/000-copyright.md "
                              "manuscript/010-dedication.md manuscript/050-foreword.md "
                              "manuscript/100-part-one.md manuscript/110-chapter-1.md "
                              "manuscript/900-references.md", "new-book"))
    steps.run("manuscript.order: list keeps the order book.yaml gives",
              output_has_line("MANUSCRIPT_FILES=manuscript/110-chapter-1.md "
                              "manuscript/000-copyright.md", "new-book",
                              "--set", "manuscript.order=list",
                              "--set", "manuscript.files=[110-chapter-1.md, 000-copyright.md]"))
    steps.run("--pattern and --exclude narrow the listed files",
              output_has_line("MANUSCRIPT_FILES=manuscript/110-chapter-1.md", "new-book",
                              "--pattern", "1*.md", "--exclude", "part"))
    steps.run("a run from another folder of the book still builds the manuscript",
              output_has_line("MANUSCRIPT_DIR=manuscript", "new-book", folder="images"))
    steps.run("a folder named on the command line is the manuscript",
              output_has_line("MANUSCRIPT_DIR=manuscript", "new-book", "manuscript"))
    steps.run("the digital edition keeps a page count the book sets",
              output_has_line("PAGES=300", "new-book", "--edition", "digital", "--pages", "300"))
    steps.run("--set overrides the config",
              output_contains("FONT_CHOICE=garamond", "new-book", "--set", "book.font=garamond"))
    steps.run("an option overrides --set",
              output_contains("FONT_CHOICE=palatino", "new-book", "--set", "book.font=garamond",
                              "--font", "palatino"))
    steps.run("the pinned image comes from tools",
              output_contains("DOCKER_IMAGE=pandoc/extra:3.8.3", "new-book"))
    steps.run("the digital edition is one-sided",
              output_contains("TWOSIDE_MODE=false", "new-book", "--edition", "digital"))
    steps.run("an unknown style in the config stops the build",
              build_refuses("new-book", "--set", "book.chapter_style=fancy"))
    steps.run("an output name with a space or a quote stops the build",
              build_refuses("new-book", "--output", "Jane's draft.pdf"))
    steps.run("a plain output name is accepted",
              output_contains("/new-book/.book/output/reader-copy_v2.pdf", "new-book",
                              "--output", "reader-copy_v2.pdf"))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="self-check.py", description=DESCRIPTION,
                                     epilog=EPILOG)
    parser.parse_args(argv)
    steps = Steps()
    script_steps(steps)
    if shutil.which("bash"):
        settings_steps(steps)
    else:
        steps.skip("build-book.sh settings steps", "bash not found; build-book.sh needs bash")
    steps.run("the OFL licence in epub.css matches assets/fonts/OFL.txt", same_licence_text)
    steps.run("the vendored EPUB template differs from pandoc's in exactly three places",
              template_has_three_changes)
    print()
    if steps.failed:
        print(f"self-check: {len(steps.failed)} step(s) failed")
        return 1
    print("self-check: every step passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
