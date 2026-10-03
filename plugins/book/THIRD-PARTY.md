# Third-party files

Everything in this plugin is under the MIT License (`LICENSE`), except the files below. Each
keeps its own licence, and its licence text travels with it.

| Files | Where they come from | Licence | Licence text |
|---|---|---|---|
| `skills/build-editions/assets/epub3-template.html`, `skills/build-editions/assets/epub3-template.pandoc-default.html` | pandoc's default EPUB 3 template (https://github.com/jgm/pandoc); the first file has three small changes, described in `skills/build-editions/references/epub.md` | BSD 3-Clause (pandoc offers its templates under GPL-2.0-or-later or BSD 3-Clause; they are used here under BSD 3-Clause) | `skills/build-editions/assets/epub3-template-LICENSE.txt` |
| `skills/build-editions/assets/fonts/JetBrainsMono-*.subset.ttf` | JetBrains Mono (https://github.com/JetBrains/JetBrainsMono), cut down to the characters the EPUB needs | SIL Open Font License 1.1 | `skills/build-editions/assets/fonts/OFL.txt`; the same text is also inside `skills/build-editions/assets/epub.css`, so it travels inside every EPUB |
| a few standard lines in `skills/build-editions/assets/templates/book-template.tex` | pandoc's default LaTeX template (https://github.com/jgm/pandoc) | BSD 3-Clause | the BSD 3-Clause text in `skills/build-editions/assets/epub3-template-LICENSE.txt` (same copyright holders: John MacFarlane and pandoc contributors) |

The SPDX expression in `.claude-plugin/plugin.json` is `MIT AND BSD-3-Clause AND OFL-1.1`.
