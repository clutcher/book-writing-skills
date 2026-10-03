# Working in this repository

This repository is public. Everything git tracks is on the internet the moment it is pushed.

## Never run a git command

This rule is for Claude sessions in this repository: the maintainer handles git. Do not run any git command and do not raise committing or pushing. Copying, moving and deleting files with shell commands is fine.

## What it is

A Claude Code plugin marketplace with one plugin, `book` (install id `book@book-writing-skills`): skills that help anyone write, check, review and publish a non-fiction book. Nothing in a skill may assume one particular book, author, folder layout or machine.

```
.claude-plugin/marketplace.json
plugins/book/.claude-plugin/plugin.json
plugins/book/lib/            shared Python helpers, one copy each (book_config, citation_key, source_registry, source_files, decisions, ...)
plugins/book/skills/<name>/  SKILL.md + references/ + scripts/ (+ templates/, profiles/, assets/, tests/)
tools/                       maintainer checks; run `python3 tools/check-plugin.py` before handing work back
```

Skills, named verb + object: `init`, `write-text`, `review-text`, `review-ideas`, `check-facts`, `collect-sources`, `revise-from-notes`, `build-editions`, `design-cover`, `prepare-sales-text`, `run-checks`. Code shared by two skills lives in `lib/`; no skill imports from another skill's folder.

Every review (review-text, review-ideas, check-facts, the cover and sales-text reviews) writes its findings as notes in the book's notes folder, each with a `From:` line; `revise-from-notes` answers them. run-checks writes a report instead.

`.workspace/` holds maintainer-only local files and is never published (gitignored). The leak check reads a private word list from the folder in `BOOK_LEAK_LIST` (README, "For maintainers").

## Rules for every file here

- **Plain A2 English** for every name (skill, mode, script, file, folder, config key) and for the text of every SKILL.md. Name a thing by what it holds or does, never by the tool that made it or by who wrote it.
- **One config per book.** Every script finds `book.yaml` by walking up from the working directory (`--config` overrides) through `lib/book_config.py`. Precedence: command-line flag > `book.yaml` > built-in default. No script hardcodes a book path.
- **One copy of shared code**, in `lib/`. Scripts import it via their own location (`Path(__file__).resolve().parents[N] / "lib"`); SKILL.md refers to scripts as `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/scripts/<script>`.
- **No book in the skills.** No book title, author name, citation key from a real bibliography used as a live example, dated incident story, private memory reference, absolute path, or word list of one book. Book-specific data belongs in the book's `book.yaml` or files.
- **Scripts:** Python 3 standard library only, `#!/usr/bin/env python3`, argparse with a working `--help`, dry run by default, `--fix` to write, exit codes per `lib/check_contract.md`. External tools (docker, tesseract, poppler, vale, bibtex, epubcheck) are detected and, when missing, the check says SKIPPED and why. Docker images are pinned to a tag (or a digest) and run as the calling user.
- **SKILL.md** stays under about 300 lines; detail goes to `references/`. The frontmatter `description` says what the skill does and when to use it.
- **Decisions:** every skill that reviews or proposes changes reads the book's `decisions.md` first and never re-raises an item marked DECIDED.
- **Working rules with the author** (from long use, built into the skills): draft, show, then apply; rewrite rather than patch a patch; a minimal change stays minimal; truth over punch, so every claim must survive a fact-check; all copies of the same text stay in sync; reviewers are cold, one subagent per lens, with no edit history.
- Licence: MIT (`LICENSE`), for the code and the skill text alike, except the third-party files listed in `plugins/book/THIRD-PARTY.md`.
- **SKILL.md frontmatter** is exactly `name`, a folded `description: >-` block and an `argument-hint` line (`tools/skill-shape-check.py`).
