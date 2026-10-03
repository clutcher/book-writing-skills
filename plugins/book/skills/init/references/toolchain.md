# The tools the skills call

Every skill runs on Python 3 with its standard library alone. Some checks and every edition of
the build call an outside tool. A check whose tool is missing prints `SKIPPED <reason>` as its
last line and exits 0; a skipped check is not a passed check, so whoever reports a run says which
checks were skipped and why.

`toolchain-check.py` lists everything at once, so a new machine is set up in one pass:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/init/scripts/toolchain-check.py            # report
python3 ${CLAUDE_PLUGIN_ROOT}/skills/init/scripts/toolchain-check.py --pull     # also pull images
```

## What each tool turns on

| Tool | Used by | Without it |
|---|---|---|
| docker | build-editions (all three editions), write-text (the Vale check), check-facts (bibliography key check) | no PDF or EPUB; Vale and the key check print SKIPPED |
| bash | build-editions (`build-book.sh`, the one shell script) | no PDF or EPUB. `build-book.sh` needs bash until the build runner moves to Python; on Windows that means WSL. This is the one script that does not yet run on Windows itself |
| tesseract | collect-sources: OCR of scanned sources | a scan without a text layer cannot be searched |
| poppler: pdftotext, pdftoppm, pdfinfo, pdfimages, pdffonts | collect-sources: text from PDFs, OCR page images, scan detection; build-editions and design-cover: page counts | PDF sources are not read or graded |
| java | build-editions: epubcheck | the EPUB is built but not validated |
| curl | collect-sources: fetching | sources cannot be downloaded |
| rsvg-convert (or cairosvg) | design-cover: drawing | the cover needs `tools.render_image` in Docker |
| magick (or convert and compare) | design-cover: colour and comparison checks | those checks print SKIPPED |
| fc-match | build-editions: leading from the font; design-cover: text widths | the build uses a default leading |
| qpdf | build-editions: draft protection and page counts without Docker | the build runs qpdf inside the pandoc image |
| `/usr/share/dict/words` | collect-sources: the word-based part of scan detection | that signal is left out |

Vale needs no local install: it runs in Docker from `tools.vale_image`. BibTeX needs none either:
`key-bibtex-check.py` runs `tools.bibtex_image` itself when no local `bibtex` is found.

## Docker images

- **Every image is pinned** to a tag or a digest in `book.yaml` under `tools`
  ([book-yaml.md](book-yaml.md)), so a build next year uses the same pandoc and TeX as today.
  Change a pin on purpose, in its own step, and rebuild to compare.
- **Every container writes files as the calling user**, so nothing it writes into the book is
  owned by root. On Linux and macOS the scripts pass `-u` with your user and group ids; on
  Windows (no user ids) no `-u` is passed and Docker Desktop maps the owner by itself. The one
  container that runs as root, the draft-protection step that installs qpdf, gives the PDF back
  to you with `chown` before it ends.
- **Folders are shared two ways.** The Python scripts use `--mount`, which keeps a Windows path
  with its drive letter whole and quotes a path that has a comma in it. `build-book.sh` uses
  `-v`. A Vale check sees the book read-only; only `vale sync` may write to it.
- **A folder owned by root** inside a book (a Vale package synced by an older setup) cannot be
  moved or removed without `sudo`; `existing.py` reports it instead.
- **Images are pulled on first use** by the script that needs them. `--pull` fetches them all at
  once, which is worth doing before working offline. The pandoc image's TeX packages and fonts
  live in the Docker volume `tools.pandoc_volume`, which the build fills itself.
