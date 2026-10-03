#!/usr/bin/env bash

set -e

export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS_DIR="$(cd "$SCRIPT_DIR/../assets" && pwd)"
BUNDLED_TEMPLATE="$ASSETS_DIR/templates/book-template.tex"
FILTER_DIR="$ASSETS_DIR/filters"

for sourced_file in "$SCRIPT_DIR/page-settings.sh" "$SCRIPT_DIR/book-settings.sh" "$SCRIPT_DIR/paper-build.sh"; do
    if [[ ! -f "$sourced_file" ]]; then
        echo "Error: missing $sourced_file" >&2
        exit 1
    fi
    . "$sourced_file"
done

show_help() {
    cat << 'EOF'
Build book editions (print PDF, digital PDF, EPUB) from manuscript markdown files,
or the paper edition (PDF and LaTeX source) when book.yaml says kind: paper.

Usage: build-book.sh [OPTIONS] [PATH]

PATH (optional):
  A folder inside the book. The book root is found by walking up from it to
  book.yaml. When PATH is a folder directly under the root, it is used as the
  manuscript folder. When omitted, the walk starts at the current working directory and
  the manuscript folder is always manuscript.dir from the config.

Book settings:
  --config <file>        Use this book.yaml instead of searching for one
  --set <key=value>      Override one config value, e.g. --set book.font=garamond
                         or --set tools.pandoc_image=pandoc/extra:3.8.3 (repeatable)
  Command-line options below win over book.yaml, which wins over the built-in
  defaults.

Editions:
  --edition <name>       print   KDP paperback PDF: two-sided, gutter margins
                         digital Screen PDF: one-sided, centered, live links, covers
                         epub    Reflowable EPUB 3, checked with epubcheck
                         all     All three (default for a book)
                         paper   Research article PDF and its .tex (the only
                                 edition of a paper, and its default)
  --arxiv                Paper only: also write the arXiv source bundle (.tar.gz)
                         and check that it compiles in a clean folder
  --anonymous            Paper only: no authors, affiliations or emails, for
                         double-blind review (default: paper.anonymous)
  --sequential           Build editions one after another; each build's output
                         arrives as it happens, which helps when one is failing
  --parallel             Build editions at the same time (default)
  --azw3                 Also convert the EPUB to AZW3 for Kindle sideloading
                         (needs calibre; the EPUB is what KDP wants)
  --all-page-folios      Print page numbers on every page. The default follows the
                         blind-folio convention: blank versos and part-title pages
                         are counted but print no number or ornament.
  --no-all-page-folios   Blind-folio convention (default)

Options:
  --final                Final output (no draft marks)
  --draft                Draft output with marks (default)
  --no-toc               Leave out the table of contents
  --toc                  Include the table of contents (default)
  --toc-depth <n>        TOC depth: 1, 2, or 3 (default: 2)
  --top-level <level>    part    -> # = Part, ## = Chapter, ### = Section
                         chapter -> # = Chapter, ## = Section (default)
                         section -> # = Section, ## = Subsection
  --numbered             Add LaTeX numbering to headings
  --unnumbered           No LaTeX numbering (default; use when markdown has numbers)
  --title <title>        Book title
  --subtitle <text>      Book subtitle
  --author <name>        Author name
  --output <file>        Output file name in the output folder (letters, digits, . _ -)
  --manuscript <dir>     Manuscript folder (default: manuscript.dir from the config)
  --output-dir <dir>     Output folder (default: work.output from the config)
  --template <file>      Custom LaTeX template file (a book only; a paper names
                         its template in paper.template)
  --pattern <glob>       Keep only the book's files whose name matches (default: *.md)
  --exclude <regex>      Leave out files matching this regex
  --format <size>        Page format (default: 6x9):
                         8x10, 7.5x9.25, 7x10, 6.69x9.61, 6.5x9.25, 6.14x9.21,
                         6x9, 5.5x8.5, 5x8, or any WxH in inches
  --font <name>          Body font (default: latin-modern): cochineal, garamond,
                         cormorant-garamond, crimson-pro, baskerville, palatino,
                         latin-modern
  --italic-font <name>   Take italic and bold italic from another family (same
                         choices as --font), e.g. --font garamond --italic-font crimson-pro
  --heading-font <name>  match-body (default), source-sans, gyre-heros,
                         latin-modern-sans, or any --font choice
  --font-size <size>     10pt, 10.5pt, 11pt, 11.5pt, 12pt (default: 11pt)
  --leading <N>          Body \setstretch. Default: computed from the font
                         x-height and the text width (compute-leading.py)
  --proportional-headings  Headings as fixed multiples of the body size
  --code-scale <N>       Code block x-height as a fraction of the body (default 0.85)
  --inline-code-scale <N>  Inline code x-height as a fraction of the body (default 1.0)
  --chapter-style <name> canonical (default), classic, technical, bold, elegant
  --section-style <name> technical (default), scholarly, literary, editorial, classic
  --pages <n|auto>       Page count for the KDP gutter (default: auto, which builds
                         again only when the count crosses a gutter band)
  --ornament <name>      hexagon (default), varhexagon, star, sun, square, fleuron
  --quote-style <name>   italic (default), plain, small, border, dash, guillemet, quote
  --highlight <style>    Code style: monochrome (default), pygments, tango, kate, none
  --page-style <style>   Page number position: header (default), footer
  --page-ornament <name> none (default), spiral-straight, spiral-curly, wasy-hexagon,
                         wasy-verhexagon, wasy-star, wasy-sun, adforn-fleuron,
                         adforn-leaf, adforn-vine
  --page-ornament-size <size>  small, medium (default), large
  --reviewer-copy <name> Reviewer name for a draft copy (adds a copyright notice)
  --changes-since <ref>  Highlight what changed since this git commit (needs git)
  --changes-until <ref>  Git commit to render as the new state (default: files on disk)
  --protected            Copy/print protection for drafts (default)
  --unprotected          No PDF protection
  --part-pages           Separate part divider pages (default)
  --no-part-pages        No part divider pages (parts appear only in the TOC)
  --part-overview        Put the paragraph after \part{...} on the divider page
  --no-part-overview     No part overview paragraphs (default)
  --twoside              Two-sided layout for print (default)
  --oneside              One-sided layout for screen reading
  --show-settings        Print the settings this build would use, then stop
                         (no Docker; for checking a book.yaml)
  --help, -h             Show this help

Examples:
  build-book.sh --edition print
  build-book.sh --final
  build-book.sh --reviewer-copy "Jane Smith" --format 7.5x9.25
  build-book.sh --top-level part --toc-depth 3
  build-book.sh ~/books/my-book --set book.font=garamond
EOF
}

BOOK_TITLE=""
BOOK_SUBTITLE=""
BOOK_AUTHOR=""
MANUSCRIPT_OPTION=""
OUTPUT_DIR_OPTION=""
PAGE_FORMAT="6x9"
TWOSIDE_MODE=true
FONT_CHOICE="latin-modern"
HEADING_FONT="match-body"
ITALIC_FONT_CHOICE=""
FONT_SIZE="11pt"
LEADING_OVERRIDE=""
PROPORTIONAL_HEADINGS=false
CODE_SCALE=""
INLINE_CODE_SCALE=""
CHAPTER_STYLE="canonical"
SECTION_STYLE="technical"
ORNAMENT="hexagon"
PAGES="auto"
DIGITAL_EDITION_PAGES=250
QUOTE_STYLE="italic"
HIGHLIGHT_STYLE="monochrome"
TOP_LEVEL="chapter"
TOC_DEPTH="2"
NUMBERED=false
GENERATE_TOC=true
FILE_PATTERN="*.md"
EXCLUDE_PATTERN=""
PAGE_STYLE="header"
PAGE_ORNAMENT="none"
PAGE_ORNAMENT_SIZE="medium"
PART_PAGES=true
PART_OVERVIEW=false
HYPHENATION_LANGUAGE=""
EDITION="all"
PARALLEL_EDITIONS=true
BUILD_AZW3=false
ALL_PAGE_FOLIOS=false
PLACEHOLDER_TOKEN="TO BE ASSIGNED"
COVER_FRONT=""
COVER_BACK=""
EBOOK_COVER=""
TEMPLATE_FILE=""
DRAFT_MODE=true
OUTPUT_FILE_OVERRIDE=""
REVIEWER_NAME=""
PROTECTED_MODE=true
POSITIONAL_PATH=""
SHOW_SETTINGS=false
DIFF_FROM=""
DIFF_TO=""
BUILD_ARXIV=false
ANONYMOUS_OPTION=false

ORIGINAL_ARGS=("$@")

while [[ $# -gt 0 ]]; do
    case $1 in
        --config)                CONFIG_ARGS+=(--config "$2"); shift 2 ;;
        --set)                   CONFIG_ARGS+=(--set "$2"); shift 2 ;;
        --edition)               EDITION="$2"; mark_cli edition; shift 2 ;;
        --azw3)                  BUILD_AZW3=true; shift ;;
        --arxiv)                 BUILD_ARXIV=true; shift ;;
        --anonymous)             ANONYMOUS_OPTION=true; shift ;;
        --all-page-folios)       ALL_PAGE_FOLIOS=true; mark_cli all-page-folios; shift ;;
        --no-all-page-folios)    ALL_PAGE_FOLIOS=false; mark_cli all-page-folios; shift ;;
        --parallel)              PARALLEL_EDITIONS=true; shift ;;
        --sequential)            PARALLEL_EDITIONS=false; shift ;;
        --final)                 DRAFT_MODE=false; shift ;;
        --draft)                 DRAFT_MODE=true; shift ;;
        --no-toc)                GENERATE_TOC=false; mark_cli toc; shift ;;
        --toc)                   GENERATE_TOC=true; mark_cli toc; shift ;;
        --toc-depth)             TOC_DEPTH="$2"; mark_cli toc-depth; shift 2 ;;
        --top-level)             TOP_LEVEL="$2"; mark_cli top-level; shift 2 ;;
        --numbered)              NUMBERED=true; mark_cli numbered; shift ;;
        --unnumbered)            NUMBERED=false; mark_cli numbered; shift ;;
        --title)                 BOOK_TITLE="$2"; mark_cli title; shift 2 ;;
        --subtitle)              BOOK_SUBTITLE="$2"; mark_cli subtitle; shift 2 ;;
        --author)                BOOK_AUTHOR="$2"; mark_cli author; shift 2 ;;
        --output)                OUTPUT_FILE_OVERRIDE="$2"; shift 2 ;;
        --manuscript)            MANUSCRIPT_OPTION="$2"; shift 2 ;;
        --output-dir)            OUTPUT_DIR_OPTION="$2"; shift 2 ;;
        --template)              TEMPLATE_FILE="$2"; shift 2 ;;
        --pattern)               FILE_PATTERN="$2"; mark_cli pattern; shift 2 ;;
        --exclude)               EXCLUDE_PATTERN="$2"; mark_cli exclude; shift 2 ;;
        --format)                PAGE_FORMAT="$2"; mark_cli format; shift 2 ;;
        --font)                  FONT_CHOICE="$2"; mark_cli font; shift 2 ;;
        --heading-font)          HEADING_FONT="$2"; mark_cli heading-font; shift 2 ;;
        --italic-font)           ITALIC_FONT_CHOICE="$2"; mark_cli italic-font; shift 2 ;;
        --font-size)             FONT_SIZE="$2"; mark_cli font-size; shift 2 ;;
        --leading)               LEADING_OVERRIDE="$2"; mark_cli leading; shift 2 ;;
        --proportional-headings) PROPORTIONAL_HEADINGS=true; mark_cli proportional-headings; shift ;;
        --code-scale)            CODE_SCALE="$2"; mark_cli code-scale; shift 2 ;;
        --inline-code-scale)     INLINE_CODE_SCALE="$2"; mark_cli inline-code-scale; shift 2 ;;
        --chapter-style)         CHAPTER_STYLE="$2"; mark_cli chapter-style; shift 2 ;;
        --section-style)         SECTION_STYLE="$2"; mark_cli section-style; shift 2 ;;
        --pages)                 PAGES="$2"; mark_cli pages; shift 2 ;;
        --ornament)              ORNAMENT="$2"; mark_cli ornament; shift 2 ;;
        --quote-style)           QUOTE_STYLE="$2"; mark_cli quote-style; shift 2 ;;
        --highlight)             HIGHLIGHT_STYLE="$2"; mark_cli highlight; shift 2 ;;
        --reviewer-copy)         REVIEWER_NAME="$2"; shift 2 ;;
        --changes-since)         DIFF_FROM="$2"; shift 2 ;;
        --changes-until)         DIFF_TO="$2"; shift 2 ;;
        --protected)             PROTECTED_MODE=true; mark_cli protected; shift ;;
        --unprotected)           PROTECTED_MODE=false; shift ;;
        --part-pages)            PART_PAGES=true; mark_cli part-pages; shift ;;
        --no-part-pages)         PART_PAGES=false; mark_cli part-pages; shift ;;
        --part-overview)         PART_OVERVIEW=true; mark_cli part-overview; shift ;;
        --no-part-overview)      PART_OVERVIEW=false; mark_cli part-overview; shift ;;
        --twoside)               TWOSIDE_MODE=true; mark_cli layout; shift ;;
        --oneside)               TWOSIDE_MODE=false; mark_cli layout; shift ;;
        --page-style)            PAGE_STYLE="$2"; mark_cli page-style; shift 2 ;;
        --page-ornament)         PAGE_ORNAMENT="$2"; mark_cli page-ornament; shift 2 ;;
        --page-ornament-size)    PAGE_ORNAMENT_SIZE="$2"; mark_cli page-ornament-size; shift 2 ;;
        --show-settings)         SHOW_SETTINGS=true; shift ;;
        --help|-h)               show_help; exit 0 ;;
        -*)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
        *)
            if [[ -n "$POSITIONAL_PATH" ]]; then
                echo "Error: Unexpected argument '$1'. Only one path argument is allowed."
                exit 1
            fi
            POSITIONAL_PATH="$1"
            shift
            ;;
    esac
done

validate_edition "$EDITION"
validate_output_name "$OUTPUT_FILE_OVERRIDE"

if [[ -n "$POSITIONAL_PATH" && ! -d "$POSITIONAL_PATH" ]]; then
    echo "Error: '$POSITIONAL_PATH' is not a folder"
    exit 1
fi
START_DIR="$(cd "${POSITIONAL_PATH:-$PWD}" && pwd)"

load_book_settings "$START_DIR"
apply_book_defaults
validate_settings
resolve_edition_for_kind
apply_paper_defaults
[[ "$SHOW_SETTINGS" == true && "$EDITION" == "all" ]] && EDITION="print"

CLEANUP_PATHS=()
cleanup_temporary_files() {
    local path
    for path in ${CLEANUP_PATHS[@]+"${CLEANUP_PATHS[@]}"}; do rm -rf "$path"; done
}
trap cleanup_temporary_files EXIT

default_setting() {
    case "$1" in
        CODE_SCALE) echo "0.85" ;;
        INLINE_CODE_SCALE) echo "1.0" ;;
        HYPHENATION_LANGUAGE) echo "english" ;;
    esac
}

show_settings() {
    local name fallback
    for name in BOOK_ROOT BOOK_CONFIG_SOURCE MANUSCRIPT_DIR FULL_OUTPUT_DIR OUTPUT_FILE \
                DOCKER_IMAGE TEXLIVE_VOLUME EDITION DRAFT_MODE BOOK_TITLE BOOK_SUBTITLE BOOK_AUTHOR \
                PAGE_FORMAT TWOSIDE_MODE FONT_CHOICE ITALIC_FONT_CHOICE HEADING_FONT FONT_SIZE \
                PROPORTIONAL_HEADINGS CODE_SCALE INLINE_CODE_SCALE CHAPTER_STYLE SECTION_STYLE ORNAMENT \
                PAGES QUOTE_STYLE HIGHLIGHT_STYLE TOP_LEVEL TOC_DEPTH GENERATE_TOC NUMBERED PAGE_STYLE \
                PAGE_ORNAMENT PAGE_ORNAMENT_SIZE PART_PAGES PART_OVERVIEW ALL_PAGE_FOLIOS COVER_FRONT \
                COVER_BACK EBOOK_COVER EPUB_IDENTIFIER PUBLICATION_DATE BOOK_PUBLISHER BOOK_SUBJECTS \
                BOOK_LANGUAGE ACCESSIBILITY_SUMMARY HYPHENATION_LANGUAGE PLACEHOLDER_TOKEN; do
        fallback="$(default_setting "$name")"
        if [[ -z "${!name}" && -n "$fallback" ]]; then
            printf '%s=%s (default)\n' "$name" "$fallback"
        else
            printf '%s=%s\n' "$name" "${!name}"
        fi
    done
    printf 'MANUSCRIPT_FILES=%s\n' "$(tr '\n' ' ' <<< "$MANUSCRIPT_FILES" | sed 's/ $//')"
    if is_paper; then
        for name in BOOK_KIND PAPER_TEMPLATE TEMPLATE_FILE PAPER_ENGINE PAPER_FORMAT PAPER_ANONYMOUS \
                    PAPER_ABSTRACT PAPER_ARXIV_CATEGORY PAPER_TEX_IMAGE BUILD_ARXIV; do
            printf '%s=%s\n' "$name" "${!name}"
        done
    fi
}

SETTINGS_DIR="$(mktemp -d)"
chmod 755 "$SETTINGS_DIR"
CLEANUP_PATHS+=("$SETTINGS_DIR")
write_fontconfig_file "$SETTINGS_DIR/fonts.conf"

epub_blocked_reason() {
    if [[ -n "$DIFF_FROM" ]]; then
        echo "a --changes-since copy renders in LaTeX and has no EPUB equivalent"
        return 0
    fi
    if [[ -n "$REVIEWER_NAME" ]] || is_cli_set protected; then
        echo "PDF protection was asked for and cannot apply to an EPUB"
        return 0
    fi
    return 1
}

print_placeholder_summary() {
    local hits="$1" outputs="$2" noun="$3"
    [[ -z "$hits" ]] && return 0
    echo ""
    echo "============================================================"
    if [[ "$DRAFT_MODE" == true ]]; then
        echo "  Still outstanding in this $noun ($PLACEHOLDER_TOKEN):"
    else
        echo "  FINAL BUILD WITH A PLACEHOLDER STILL IN IT ($PLACEHOLDER_TOKEN):"
    fi
    echo ""
    echo "$hits" | sed 's/^/    /'
    echo ""
    echo "  This text is printed in:"
    echo "$outputs" | sed 's/^/    /'
    if [[ "$DRAFT_MODE" != true ]]; then
        echo "  NOT fit to publish as it stands. Replace the placeholder and build again."
    fi
    echo "============================================================"
}

build_all_editions() {
    local fanout_args=() skip_next=false arg one_edition reason
    for arg in ${ORIGINAL_ARGS[@]+"${ORIGINAL_ARGS[@]}"}; do
        if [[ "$skip_next" == true ]]; then skip_next=false; continue; fi
        if [[ "$arg" == "--edition" ]]; then skip_next=true; continue; fi
        fanout_args+=("$arg")
    done

    local failed_editions=() attempted_editions=()
    PLACEHOLDER_REPORT_FILE="$(mktemp)"
    CLEANUP_PATHS+=("$PLACEHOLDER_REPORT_FILE")
    export PLACEHOLDER_REPORT_FILE

    for one_edition in print digital epub; do
        if [[ "$one_edition" == "epub" ]] && reason="$(epub_blocked_reason)"; then
            echo ""
            echo "Skipping EPUB: $reason"
            continue
        fi
        attempted_editions+=("$one_edition")
    done

    if [[ "$PARALLEL_EDITIONS" == true && ${#attempted_editions[@]} -gt 1 ]]; then
        warm_texlive_cache "$([[ -n "$DIFF_FROM" ]] && echo true || echo false)"
        local parallel_logs edition_pids=() index
        parallel_logs="$(mktemp -d)"
        CLEANUP_PATHS+=("$parallel_logs")
        echo ""
        echo "Building ${#attempted_editions[@]} editions in parallel: ${attempted_editions[*]}"
        for one_edition in "${attempted_editions[@]}"; do
            "$0" --edition "$one_edition" ${fanout_args[@]+"${fanout_args[@]}"} \
                > "$parallel_logs/$one_edition.log" 2>&1 &
            edition_pids+=("$!")
        done
        for index in "${!attempted_editions[@]}"; do
            one_edition="${attempted_editions[$index]}"
            wait "${edition_pids[$index]}" || failed_editions+=("$one_edition")
            echo ""
            echo "============================================================"
            echo "  Edition: $one_edition"
            echo "============================================================"
            cat "$parallel_logs/$one_edition.log"
        done
    else
        for one_edition in "${attempted_editions[@]}"; do
            echo ""
            echo "============================================================"
            echo "  Edition: $one_edition"
            echo "============================================================"
            "$0" --edition "$one_edition" ${fanout_args[@]+"${fanout_args[@]}"} || failed_editions+=("$one_edition")
        done
    fi

    print_placeholder_summary \
        "$(grep '^HIT ' "$PLACEHOLDER_REPORT_FILE" 2>/dev/null | sed 's/^HIT //' | sort -u || true)" \
        "$(grep '^OUTPUT ' "$PLACEHOLDER_REPORT_FILE" 2>/dev/null | sed 's/^OUTPUT //' | sort -u || true)" \
        "set of drafts"

    if [[ ${#failed_editions[@]} -gt 0 ]]; then
        echo ""
        echo "============================================================"
        echo "  Failed: ${failed_editions[*]}"
        if [[ ${#failed_editions[@]} -eq ${#attempted_editions[@]} ]]; then
            echo "  Nothing was written."
        else
            echo "  Every other edition was written."
        fi
        echo "============================================================"
        exit 1
    fi
    exit 0
}

if [[ "$EDITION" == "all" ]]; then
    build_all_editions
fi

if [[ "$EDITION" == "epub" ]] && reason="$(epub_blocked_reason)"; then
    echo "Error: cannot build an EPUB here -- $reason"
    exit 1
fi

PROJECT_ROOT="$BOOK_ROOT"

if [[ -n "$MANUSCRIPT_OPTION" ]]; then
    [[ "$MANUSCRIPT_OPTION" == /* ]] || MANUSCRIPT_OPTION="$PROJECT_ROOT/$MANUSCRIPT_OPTION"
    [[ -d "$MANUSCRIPT_OPTION" ]] || { echo "Error: Manuscript folder '$MANUSCRIPT_OPTION' not found"; exit 1; }
    FULL_MANUSCRIPT="$(cd "$MANUSCRIPT_OPTION" && pwd)"
elif [[ -n "$POSITIONAL_PATH" && "$START_DIR" != "$PROJECT_ROOT" && "$(dirname "$START_DIR")" == "$PROJECT_ROOT" ]]; then
    FULL_MANUSCRIPT="$START_DIR"
else
    FULL_MANUSCRIPT="$BOOK_MANUSCRIPT_DIR"
fi

case "$FULL_MANUSCRIPT" in
    "$PROJECT_ROOT"/*) MANUSCRIPT_DIR="$(relative_to_root "$FULL_MANUSCRIPT")" ;;
    *)
        echo "Error: Manuscript folder '$FULL_MANUSCRIPT' is outside the book root '$PROJECT_ROOT'"
        exit 1
        ;;
esac

if [[ -n "$OUTPUT_DIR_OPTION" ]]; then
    [[ "$OUTPUT_DIR_OPTION" == /* ]] && FULL_OUTPUT_DIR="$OUTPUT_DIR_OPTION" || FULL_OUTPUT_DIR="$PROJECT_ROOT/$OUTPUT_DIR_OPTION"
else
    FULL_OUTPUT_DIR="$BOOK_WORK_OUTPUT"
fi

SYMMETRIC_MARGINS=false
case "$EDITION" in
    digital)
        SYMMETRIC_MARGINS=true
        TWOSIDE_MODE=false
        [[ "$PAGES" == "auto" ]] && PAGES="$DIGITAL_EDITION_PAGES"
        ;;
    epub|print)
        COVER_FRONT=""
        COVER_BACK=""
        ;;
esac

if is_paper; then
    TEMPLATE_FILE="$(paper_template_file)"
elif [[ -z "$TEMPLATE_FILE" ]]; then
    TEMPLATE_FILE="$BUNDLED_TEMPLATE"
fi
if [[ ! -f "$TEMPLATE_FILE" ]]; then
    echo "Error: No template at '$TEMPLATE_FILE'. Use --template to name one."
    exit 1
fi
TEMPLATE_FILE="$(cd "$(dirname "$TEMPLATE_FILE")" && pwd)/$(basename "$TEMPLATE_FILE")"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RANDOM_SUFFIX=$(printf '%04x%04x' $RANDOM $RANDOM)
DRAFT_ID="DRAFT-${TIMESTAMP}-${RANDOM_SUFFIX}"

TITLE_SLUG=""
LASTNAME_SLUG=""
[[ -n "$BOOK_TITLE" ]] && TITLE_SLUG=$(slugify "$BOOK_TITLE")
[[ -n "$BOOK_AUTHOR" ]] && LASTNAME_SLUG=$(slugify "$(get_lastname "$BOOK_AUTHOR")")

is_paper && LASTNAME_SLUG="$(paper_name_slug)"

case "$EDITION" in
    paper)   EDITION_SUFFIX="";         OUTPUT_EXT="pdf"  ;;
    print)   EDITION_SUFFIX="";         OUTPUT_EXT="pdf"  ;;
    digital) EDITION_SUFFIX="-digital"; OUTPUT_EXT="pdf"  ;;
    epub)    EDITION_SUFFIX="";         OUTPUT_EXT="epub" ;;
esac

if [[ -n "$OUTPUT_FILE_OVERRIDE" ]]; then
    OUTPUT_FILE="$FULL_OUTPUT_DIR/$OUTPUT_FILE_OVERRIDE"
elif is_paper; then
    BASE_NAME="$(paper_base_name "$TITLE_SLUG" "$LASTNAME_SLUG")"
    if [[ "$DRAFT_MODE" == true ]]; then
        OUTPUT_FILE="$FULL_OUTPUT_DIR/${BASE_NAME}-draft-${TIMESTAMP}.pdf"
    else
        OUTPUT_FILE="$FULL_OUTPUT_DIR/${BASE_NAME}.pdf"
    fi
elif [[ -n "$TITLE_SLUG" && -n "$LASTNAME_SLUG" ]]; then
    BASE_NAME="${TITLE_SLUG}-${LASTNAME_SLUG}${EDITION_SUFFIX}"
    if [[ "$DRAFT_MODE" != true ]]; then
        OUTPUT_FILE="$FULL_OUTPUT_DIR/${BASE_NAME}.${OUTPUT_EXT}"
    elif [[ -n "$REVIEWER_NAME" ]]; then
        OUTPUT_FILE="$FULL_OUTPUT_DIR/${BASE_NAME}-draft-$(slugify "$(get_lastname "$REVIEWER_NAME")")-${TIMESTAMP}.${OUTPUT_EXT}"
    else
        OUTPUT_FILE="$FULL_OUTPUT_DIR/${BASE_NAME}-draft-${TIMESTAMP}.${OUTPUT_EXT}"
    fi
elif [[ "$DRAFT_MODE" == true ]]; then
    OUTPUT_FILE="$FULL_OUTPUT_DIR/book${EDITION_SUFFIX}-draft-${TIMESTAMP}.${OUTPUT_EXT}"
else
    OUTPUT_FILE="$FULL_OUTPUT_DIR/book${EDITION_SUFFIX}.${OUTPUT_EXT}"
fi

MANUSCRIPT_FILES="$(list_manuscript_files "$FULL_MANUSCRIPT")" || exit 1

if [[ -z "$MANUSCRIPT_FILES" ]]; then
    echo "Error: No files matching '$FILE_PATTERN' found in $FULL_MANUSCRIPT/"
    exit 1
fi

if [[ "$SHOW_SETTINGS" == true ]]; then
    show_settings
    exit 0
fi

echo "Found $(grep -c . <<< "$MANUSCRIPT_FILES") manuscript files."

mkdir -p "$FULL_OUTPUT_DIR"
FULL_OUTPUT_DIR="$(cd "$FULL_OUTPUT_DIR" && pwd)"
OUTPUT_FILE="$FULL_OUTPUT_DIR/$(basename "$OUTPUT_FILE")"
TEMP_PDF="$FULL_OUTPUT_DIR/.book-temp-${EDITION}-${TIMESTAMP}-${RANDOM_SUFFIX}.pdf"
OUTPUT_FILE_IN_CONTAINER="/output/$(basename "$OUTPUT_FILE")"
TEMP_PDF_IN_CONTAINER="/output/$(basename "$TEMP_PDF")"


MANUSCRIPT_PATHS_IN_CONTAINER=()
while IFS= read -r file; do
    [[ -n "$file" ]] && MANUSCRIPT_PATHS_IN_CONTAINER+=("/data/$file")
done <<< "$MANUSCRIPT_FILES"

stage_diff_files() {
    local diff_preprocessor="$SCRIPT_DIR/diff-preprocess.py"
    command -v git >/dev/null 2>&1 || { echo "Error: --changes-since needs git"; exit 1; }
    command -v python3 >/dev/null 2>&1 || { echo "Error: --changes-since needs python3"; exit 1; }

    GIT_ROOT="$(git -C "$PROJECT_ROOT" rev-parse --show-toplevel 2>/dev/null || true)"
    if [[ -z "$GIT_ROOT" ]]; then
        echo "Error: --changes-since needs the book to be inside a git repository"
        exit 1
    fi
    git -C "$GIT_ROOT" rev-parse --verify "$DIFF_FROM^{commit}" >/dev/null 2>&1 \
        || { echo "Error: --changes-since '$DIFF_FROM' is not a valid git ref"; exit 1; }
    DIFF_FROM_SHA="$(git -C "$GIT_ROOT" rev-parse --short "$DIFF_FROM")"

    local diff_head_sha=""
    if [[ -n "$DIFF_TO" ]]; then
        git -C "$GIT_ROOT" rev-parse --verify "$DIFF_TO^{commit}" >/dev/null 2>&1 \
            || { echo "Error: --changes-until '$DIFF_TO' is not a valid git ref"; exit 1; }
        DIFF_TO_LABEL="$(git -C "$GIT_ROOT" rev-parse --short "$DIFF_TO")"
    else
        diff_head_sha="$(git -C "$GIT_ROOT" rev-parse --short HEAD 2>/dev/null || echo "unknown")"
        DIFF_TO_LABEL="current files on disk"
    fi

    local staging_dir="$SETTINGS_DIR/diff"
    mkdir -p "$staging_dir"
    echo "changes-since: staging changes from $DIFF_FROM_SHA to $DIFF_TO_LABEL"

    local diff_range=("$DIFF_FROM") pathspec="${FULL_MANUSCRIPT#"$GIT_ROOT"/}" rename_status rename_old rename_new
    local renamed_files="" renamed_count=0
    [[ -n "$DIFF_TO" ]] && diff_range+=("$DIFF_TO")
    while IFS=$'\t' read -r rename_status rename_old rename_new; do
        [[ "$rename_status" == R* ]] || continue
        renamed_files+="$rename_new"$'\t'"$rename_old"$'\n'
        renamed_count=$((renamed_count + 1))
    done < <(git -C "$GIT_ROOT" -c diff.renameLimit=9999 diff --find-renames \
                --name-status "${diff_range[@]}" -- "$pathspec" 2>/dev/null)
    [[ "$renamed_count" -gt 0 ]] && echo "  Resolved $renamed_count renamed file(s) to their pre-rename content"

    if [[ -z "$DIFF_TO" ]]; then
        local dirty_count
        dirty_count=$(git -C "$GIT_ROOT" status --porcelain -- "$pathspec" | grep -c . || true)
        if [[ "$dirty_count" -gt 0 ]]; then
            echo "  Including $dirty_count uncommitted manuscript file(s)"
        else
            echo "  No uncommitted manuscript changes (disk matches HEAD $diff_head_sha)"
        fi
    fi

    MANUSCRIPT_PATHS_IN_CONTAINER=()
    local file absolute_new relative_to_git old_relative old_copy new_source marked_copy
    while IFS= read -r file; do
        [[ -z "$file" ]] && continue
        absolute_new="$PROJECT_ROOT/$file"
        relative_to_git="${absolute_new#"$GIT_ROOT"/}"
        old_relative="$(path_before_rename "$relative_to_git" "$renamed_files")"
        old_copy="$staging_dir/before/$file"
        marked_copy="$staging_dir/marked/$file"
        mkdir -p "$(dirname "$old_copy")" "$(dirname "$marked_copy")"
        git -C "$GIT_ROOT" show "$DIFF_FROM:$old_relative" > "$old_copy" 2>/dev/null || : > "$old_copy"
        if [[ -n "$DIFF_TO" ]]; then
            new_source="$staging_dir/after/$file"
            mkdir -p "$(dirname "$new_source")"
            if ! git -C "$GIT_ROOT" show "$DIFF_TO:$relative_to_git" > "$new_source" 2>/dev/null; then
                echo "  - $file: not present in $DIFF_TO (skipping)"
                continue
            fi
        else
            [[ -f "$absolute_new" ]] || { echo "  - $file: not present on disk (skipping)"; continue; }
            new_source="$absolute_new"
        fi
        python3 "$diff_preprocessor" "$old_copy" "$new_source" > "$marked_copy"
        MANUSCRIPT_PATHS_IN_CONTAINER+=("/settings/diff/marked/$file")
    done <<< "$MANUSCRIPT_FILES"

    [[ ${#MANUSCRIPT_PATHS_IN_CONTAINER[@]} -gt 0 ]] || { echo "Error: no files survived diff staging"; exit 1; }
}

[[ -n "$DIFF_FROM" ]] && stage_diff_files

echo "Files to process:"
printf '  - %s\n' "${MANUSCRIPT_PATHS_IN_CONTAINER[@]#/data/}"

MANUSCRIPT_FILE_LIST=()
while IFS= read -r file; do
    if [[ -n "$file" ]]; then MANUSCRIPT_FILE_LIST+=("$file"); fi
done <<< "$MANUSCRIPT_FILES"
PLACEHOLDER_SCAN_STATUS=0
PLACEHOLDER_HITS=$(cd "$PROJECT_ROOT" && grep -H -n -F -e "$PLACEHOLDER_TOKEN" -- "${MANUSCRIPT_FILE_LIST[@]}") \
    || PLACEHOLDER_SCAN_STATUS=$?
if [[ "$PLACEHOLDER_SCAN_STATUS" -gt 1 ]]; then
    echo "Error: could not scan the manuscript for '$PLACEHOLDER_TOKEN' (see the message above)"
    exit 1
fi

report_placeholders() {
    [[ -z "$PLACEHOLDER_HITS" ]] && return 0
    if [[ -n "${PLACEHOLDER_REPORT_FILE:-}" ]]; then
        {
            echo "OUTPUT $OUTPUT_FILE"
            echo "$PLACEHOLDER_HITS" | sed 's/^/HIT /'
        } >> "$PLACEHOLDER_REPORT_FILE"
        return 0
    fi
    print_placeholder_summary "$PLACEHOLDER_HITS" "$OUTPUT_FILE" "draft"
}

python3 "$SCRIPT_DIR/filter-settings.py" ${CONFIG_ARGS[@]+"${CONFIG_ARGS[@]}"} \
    --output "$SETTINGS_DIR/filter-settings.json" \
    || { echo "Error: could not write the filter settings"; exit 1; }

run_in_pandoc_container() {
    docker run --rm \
        ${DOCKER_USER_ARGS[@]+"${DOCKER_USER_ARGS[@]}"} \
        -e HOME=/tmp \
        -e TEXMFVAR=/tmp/texmf-var \
        -e FONTCONFIG_FILE=/settings/fonts.conf \
        -v "$PROJECT_ROOT:/data:ro" \
        -v "$FULL_OUTPUT_DIR:/output" \
        -v "$SETTINGS_DIR:/settings:ro" \
        -v "$FILTER_DIR:/filters:ro" \
        -v "$ASSETS_DIR:/assets:ro" \
        -v "$(dirname "$TEMPLATE_FILE"):/template:ro" \
        "$@" \
        -w /data \
        --entrypoint pandoc \
        "$DOCKER_IMAGE" \
        "${PANDOC_ARGS[@]}"
}

xml_escape() {
    printf '%s' "$1" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g; s/"/\&quot;/g'
}

normalise_epub_identifier() {
    EPUB_IDENTIFIER_SCHEME=""
    local isbn_candidate="${EPUB_IDENTIFIER//[ -]/}"
    if [[ "$isbn_candidate" =~ ^(978|979)[0-9]{10}$ ]]; then
        EPUB_IDENTIFIER="urn:isbn:$isbn_candidate"
        EPUB_IDENTIFIER_SCHEME="ISBN-13"
    elif [[ "$isbn_candidate" =~ ^[0-9]{9}[0-9Xx]$ ]]; then
        EPUB_IDENTIFIER="urn:isbn:$isbn_candidate"
        EPUB_IDENTIFIER_SCHEME="ISBN-10"
    fi
}

write_epub_metadata() {
    local target="$1" copyright_year="${PUBLICATION_DATE:0:4}" creator_attributes subject
    [[ -z "$copyright_year" ]] && copyright_year="$(date +%Y)"
    {
        echo "<dc:language>$(xml_escape "$BOOK_LANGUAGE")</dc:language>"
        if [[ -n "$EPUB_IDENTIFIER" && -n "$EPUB_IDENTIFIER_SCHEME" ]]; then
            echo "<dc:identifier opf:scheme=\"$EPUB_IDENTIFIER_SCHEME\">$(xml_escape "$EPUB_IDENTIFIER")</dc:identifier>"
        elif [[ -n "$EPUB_IDENTIFIER" ]]; then
            echo "<dc:identifier>$(xml_escape "$EPUB_IDENTIFIER")</dc:identifier>"
        fi
        if [[ -n "$BOOK_TITLE" ]]; then
            echo "<dc:title opf:type=\"main\">$(xml_escape "$BOOK_TITLE")</dc:title>"
            [[ -n "$BOOK_SUBTITLE" ]] && echo "<dc:title opf:type=\"subtitle\">$(xml_escape "$BOOK_SUBTITLE")</dc:title>"
        fi
        if [[ -n "$BOOK_AUTHOR" ]]; then
            creator_attributes=' opf:role="aut"'
            if [[ "$BOOK_AUTHOR" == *" "* ]]; then
                creator_attributes+=" opf:file-as=\"$(xml_escape "$(get_lastname "$BOOK_AUTHOR"), ${BOOK_AUTHOR% *}")\""
            fi
            echo "<dc:creator$creator_attributes>$(xml_escape "$BOOK_AUTHOR")</dc:creator>"
        fi
        [[ -n "$PUBLICATION_DATE" ]] && echo "<dc:date>$(xml_escape "$PUBLICATION_DATE")</dc:date>"
        [[ -n "$BOOK_PUBLISHER" ]] && echo "<dc:publisher>$(xml_escape "$BOOK_PUBLISHER")</dc:publisher>"
        [[ -n "$BOOK_DESCRIPTION" ]] && echo "<dc:description>$(xml_escape "$BOOK_DESCRIPTION")</dc:description>"
        if [[ -n "$BOOK_SUBJECTS" ]]; then
            echo "$BOOK_SUBJECTS" | tr ',' '\n' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' | \
            while read -r subject; do
                if [[ -n "$subject" ]]; then
                    echo "<dc:subject>$(xml_escape "$subject")</dc:subject>"
                fi
            done
        fi
        echo "<dc:rights>Copyright (c) $copyright_year $(xml_escape "${BOOK_AUTHOR:-the author}"). All rights reserved.</dc:rights>"
    } > "$target"
}

check_epub_template_drift() {
    local pristine="$ASSETS_DIR/epub3-template.pandoc-default.html" current
    if [[ ! -f "$pristine" ]]; then
        echo ""
        echo "Template drift check SKIPPED: no pristine copy at $pristine"
        echo "  Take one with:"
        echo "    docker run --rm --entrypoint pandoc $DOCKER_IMAGE --print-default-template=epub3 > '$pristine'"
        return 0
    fi
    current="$(docker run --rm ${DOCKER_USER_ARGS[@]+"${DOCKER_USER_ARGS[@]}"} --entrypoint pandoc "$DOCKER_IMAGE" --print-default-template=epub3 2>/dev/null || true)"
    if [[ -z "$current" ]]; then
        echo ""
        echo "Template drift check SKIPPED: $DOCKER_IMAGE would not print its default epub3 template."
        return 0
    fi
    if ! diff -q <(printf '%s\n' "$current") "$pristine" >/dev/null 2>&1; then
        echo ""
        echo "Warning: pandoc's default epub3 template in $DOCKER_IMAGE no longer matches"
        echo "         the copy epub3-template.html was taken from. Take the template again,"
        echo "         apply the three local changes (references/epub.md), and refresh the"
        echo "         pristine copy beside it in the same change."
    fi
}

build_epub() {
    local required
    for required in "$FILTER_DIR/digital-mode.lua" "$FILTER_DIR/citation-links.lua" \
                    "$ASSETS_DIR/epub.css" "$ASSETS_DIR/epub3-template.html"; do
        [[ -f "$required" ]] || { echo "Error: missing $required"; exit 1; }
    done

    if [[ -n "$EPUB_IDENTIFIER" ]]; then
        normalise_epub_identifier
    else
        echo ""
        echo "Warning: no epub_identifier in the book config."
        echo "         pandoc will make up a random UUID, so this EPUB is a different book"
        echo "         to every reading system than the last one built: readers lose their"
        echo "         place and their notes, and stores see a new title."
    fi
    write_epub_metadata "$SETTINGS_DIR/epub-metadata.xml"

    if [[ -n "$EBOOK_COVER" && ! -f "$PROJECT_ROOT/$EBOOK_COVER" ]]; then
        echo "Error: ebook_cover '$EBOOK_COVER' not found under $PROJECT_ROOT"
        exit 1
    fi

    PANDOC_ARGS=(
        --from=markdown+autolink_bare_uris+raw_tex
        --to=epub3
        --metadata-file=/settings/filter-settings.json
        --lua-filter=/filters/digital-mode.lua
        --lua-filter=/filters/citation-links.lua
        --css=/assets/epub.css
        --template=/assets/epub3-template.html
        --epub-embed-font=/assets/fonts/JetBrainsMono-Regular.subset.ttf
        --epub-embed-font=/assets/fonts/JetBrainsMono-Bold.subset.ttf
        --epub-embed-font=/assets/fonts/JetBrainsMono-Italic.subset.ttf
        --epub-metadata=/settings/epub-metadata.xml
        --epub-title-page=false
        --split-level=1
        --toc
        --toc-depth="$TOC_DEPTH"
        --syntax-highlighting="$HIGHLIGHT_STYLE"
    )
    if [[ -n "$ACCESSIBILITY_SUMMARY" ]]; then
        PANDOC_ARGS+=(--metadata="accessibilitySummary:$ACCESSIBILITY_SUMMARY")
    else
        echo ""
        echo "Warning: no accessibility_summary in the book config, so the EPUB states none."
        echo "         Write one that says only what is true of this book (references/epub.md)."
    fi
    [[ -n "$BOOK_TITLE" ]] && PANDOC_ARGS+=(--variable=pagetitle="$(xml_escape "$BOOK_TITLE")")
    [[ -n "$EBOOK_COVER" ]] && PANDOC_ARGS+=(--epub-cover-image="/data/$EBOOK_COVER")
    PANDOC_ARGS+=("${MANUSCRIPT_PATHS_IN_CONTAINER[@]}" -o "$OUTPUT_FILE_IN_CONTAINER")

    echo ""
    echo "Building EPUB..."
    echo "  Language: $BOOK_LANGUAGE"
    echo "  Cover: ${EBOOK_COVER:-none}"
    echo "  Output: $OUTPUT_FILE"

    run_in_pandoc_container
    [[ -f "$OUTPUT_FILE" ]] || { echo "Error: EPUB build produced no output"; exit 1; }

    local flatten_args=()
    [[ "$HIGHLIGHT_STYLE" == "none" ]] && flatten_args+=(--allow-empty)
    echo ""
    echo "Flattening code-block line markup for Kindle..."
    if ! python3 "$SCRIPT_DIR/flatten-code-lines.py" --fix ${flatten_args[@]+"${flatten_args[@]}"} "$OUTPUT_FILE"; then
        echo "Error: code-block flattening failed; the EPUB is not fit for KDP." >&2
        exit 1
    fi

    echo ""
    echo "Done! Output: $OUTPUT_FILE"
    echo "File size: $(du -h "$OUTPUT_FILE" | cut -f1)"

    echo ""
    echo "Checking the EPUB with epubcheck..."
    python3 "$SCRIPT_DIR/epub-check.py" ${CONFIG_ARGS[@]+"${CONFIG_ARGS[@]}"} "$OUTPUT_FILE" \
        || echo "  epubcheck reported issues (above). The EPUB was still written."

    if [[ "$BUILD_AZW3" == true ]]; then
        local azw3_file="${OUTPUT_FILE%.epub}.azw3"
        echo ""
        if command -v ebook-convert >/dev/null 2>&1; then
            echo "Converting to AZW3 for Kindle sideloading..."
            if ebook-convert "$OUTPUT_FILE" "$azw3_file" >/dev/null 2>&1; then
                echo "Done! Output: $azw3_file"
            else
                echo "Warning: ebook-convert failed; the EPUB is not affected."
            fi
        else
            echo "AZW3 SKIPPED: ebook-convert (calibre) not found."
        fi
    fi

    check_epub_template_drift
    report_placeholders
    exit 0
}

[[ "$EDITION" == "paper" ]] && build_paper
[[ "$EDITION" == "epub" ]] && build_epub

LATEX_TOC_DEPTH=$((TOC_DEPTH - 1))
TEMPLATE_NAME="$(basename "$TEMPLATE_FILE")"

if [[ "$PAGES" == "auto" ]]; then
    PAGES_PROVISIONAL=250
    PAGES_MODE="auto"
else
    PAGES_PROVISIONAL="$PAGES"
    PAGES_MODE="fixed"
fi

GEOMETRY="$(compute_geometry "$PAGE_FORMAT" "$PAGES_PROVISIONAL" "$SYMMETRIC_MARGINS")"

PANDOC_ARGS=(
    --from=markdown+autolink_bare_uris+raw_tex
    --pdf-engine=latexmk
    --pdf-engine-opt=-xelatex
    --template="/template/$TEMPLATE_NAME"
    --toc-depth="$TOC_DEPTH"
    --syntax-highlighting="$HIGHLIGHT_STYLE"
    --top-level-division="$TOP_LEVEL"
    --metadata-file=/settings/filter-settings.json
    --metadata="geometry:$GEOMETRY"
    --metadata="toc-depth:$LATEX_TOC_DEPTH"
)

[[ -n "$BOOK_TITLE" ]] && PANDOC_ARGS+=(--metadata="title:$BOOK_TITLE")
[[ -n "$BOOK_SUBTITLE" ]] && PANDOC_ARGS+=(--metadata="subtitle:$BOOK_SUBTITLE")
[[ -n "$BOOK_AUTHOR" ]] && PANDOC_ARGS+=(--metadata="author:$BOOK_AUTHOR")
[[ "$DRAFT_MODE" == true ]] && PANDOC_ARGS+=(--metadata="draft:true" --metadata="draftid:$DRAFT_ID")
[[ "$NUMBERED" == true ]] && PANDOC_ARGS+=(--metadata="numberedsections:true")
[[ "$GENERATE_TOC" == true ]] && PANDOC_ARGS+=(--toc)
[[ -n "$REVIEWER_NAME" ]] && PANDOC_ARGS+=(--metadata="reviewer:$REVIEWER_NAME")
[[ -n "$HYPHENATION_LANGUAGE" ]] && PANDOC_ARGS+=(--metadata="hyphenation-language:$HYPHENATION_LANGUAGE")

FONT_NAME=$(get_font_name "$FONT_CHOICE")
PANDOC_ARGS+=(--metadata="mainfont:$FONT_NAME")

CLASS_FONTSIZE="$FONT_SIZE"
case "$FONT_SIZE" in
    10pt|11pt|12pt) ;;
    *)
        PANDOC_ARGS+=(--metadata="bodyfontsize:$FONT_SIZE")
        CLASS_FONTSIZE="$(nearest_standard_size "$FONT_SIZE")"
        ;;
esac
PANDOC_ARGS+=(--metadata="fontsize:$CLASS_FONTSIZE")

LEADING_STRETCH="$(resolve_leading "$FONT_NAME" "$FONT_SIZE" "$GEOMETRY" "$LEADING_OVERRIDE")"
[[ -n "$LEADING_STRETCH" ]] && PANDOC_ARGS+=(--metadata="leadingstretch:$LEADING_STRETCH")
[[ "$PROPORTIONAL_HEADINGS" == true ]] && PANDOC_ARGS+=(--metadata="proportionalheadings:true")
[[ -n "$CODE_SCALE" ]] && PANDOC_ARGS+=(--metadata="codescale:$CODE_SCALE")
[[ -n "$INLINE_CODE_SCALE" ]] && PANDOC_ARGS+=(--metadata="inlinecodescale:$INLINE_CODE_SCALE")
if [[ -n "$INLINE_CODE_SCALE" ]]; then
    PANDOC_ARGS+=(--metadata="codeblockfontratio:$(awk -v c="${CODE_SCALE:-0.85}" -v i="$INLINE_CODE_SCALE" 'BEGIN{printf "%.4f", c/i}')")
fi

ITALIC_FONT_FILE=""
BOLD_ITALIC_FONT_FILE=""
if [[ -n "$ITALIC_FONT_CHOICE" ]]; then
    ITALIC_FONT_FILE=$(get_italic_file_for_shortcut "$ITALIC_FONT_CHOICE")
    BOLD_ITALIC_FONT_FILE=$(get_bold_italic_file_for_shortcut "$ITALIC_FONT_CHOICE")
fi
[[ -n "$ITALIC_FONT_FILE" ]] && PANDOC_ARGS+=(--metadata="italicfont:$ITALIC_FONT_FILE")
[[ -n "$BOLD_ITALIC_FONT_FILE" ]] && PANDOC_ARGS+=(--metadata="bolditalicfont:$BOLD_ITALIC_FONT_FILE")

HEADING_FONT_NAME=$(get_heading_font_name "$HEADING_FONT")
[[ -n "$HEADING_FONT_NAME" ]] && PANDOC_ARGS+=(--metadata="headingfont:$HEADING_FONT_NAME")

[[ "$TWOSIDE_MODE" == true ]] && PANDOC_ARGS+=(--metadata="twoside:true")
[[ "$CHAPTER_STYLE" != "classic" ]] && PANDOC_ARGS+=(--metadata="chapter-style-${CHAPTER_STYLE}:true")
[[ "$SECTION_STYLE" != "classic" ]] && PANDOC_ARGS+=(--metadata="section-style-${SECTION_STYLE}:true")
PANDOC_ARGS+=(--metadata="ornament-${ORNAMENT}:true")
PANDOC_ARGS+=(--metadata="quote-style-${QUOTE_STYLE}:true")
[[ "$PAGE_STYLE" == "footer" ]] && PANDOC_ARGS+=(--metadata="page-style-footer:true")
[[ "$PAGE_ORNAMENT" != "none" ]] && PANDOC_ARGS+=(--metadata="page-ornament-${PAGE_ORNAMENT}:true")
[[ "$PART_PAGES" == false ]] && PANDOC_ARGS+=(--metadata="no-part-pages:true")
[[ "$PART_OVERVIEW" == true ]] && PANDOC_ARGS+=(--metadata="part-overview:true")
[[ "$ALL_PAGE_FOLIOS" == true ]] && PANDOC_ARGS+=(--metadata="all-page-folios:true")
[[ "$EDITION" == "digital" ]] && PANDOC_ARGS+=(--metadata="digital-edition:true")
[[ -n "$COVER_FRONT" ]] && PANDOC_ARGS+=(--metadata="coverfront:$COVER_FRONT")
[[ -n "$COVER_BACK" ]] && PANDOC_ARGS+=(--metadata="coverback:$COVER_BACK")
[[ "$PAGE_ORNAMENT_SIZE" == "small" ]] && PANDOC_ARGS+=(--metadata="page-ornament-size-small:true")
[[ "$PAGE_ORNAMENT_SIZE" == "large" ]] && PANDOC_ARGS+=(--metadata="page-ornament-size-large:true")

if [[ -n "$DIFF_FROM" ]]; then
    PANDOC_ARGS+=(--metadata="diff-mode:true" --lua-filter=/filters/diff-mode.lua)
fi
PANDOC_ARGS+=(--lua-filter=/filters/citation-links.lua)
PANDOC_ARGS+=("${MANUSCRIPT_PATHS_IN_CONTAINER[@]}")

APPLY_PROTECTION=false
if [[ "$DRAFT_MODE" == true && "$PROTECTED_MODE" == true ]]; then
    APPLY_PROTECTION=true
    PANDOC_OUTPUT="$TEMP_PDF"
    PANDOC_ARGS+=(-o "$TEMP_PDF_IN_CONTAINER")
else
    PANDOC_OUTPUT="$OUTPUT_FILE"
    PANDOC_ARGS+=(-o "$OUTPUT_FILE_IN_CONTAINER")
fi

echo ""
echo "Building PDF..."
echo "  Mode: $([ "$DRAFT_MODE" == true ] && echo "DRAFT" || echo "FINAL")"
echo "  TOC:  $([ "$GENERATE_TOC" == true ] && echo "Yes" || echo "No")"
echo "  Format: $PAGE_FORMAT"
echo "  Font: $FONT_NAME ($FONT_CHOICE)"
[[ -n "$ITALIC_FONT_CHOICE" ]] && echo "  Italic override: $ITALIC_FONT_CHOICE ($ITALIC_FONT_FILE / $BOLD_ITALIC_FONT_FILE)"
echo "  Heading font: ${HEADING_FONT_NAME:-match-body} ($HEADING_FONT)"
echo "  Font size: $FONT_SIZE"
echo "  Leading: \\setstretch{${LEADING_STRETCH:-template default}}$([ -n "$LEADING_OVERRIDE" ] && echo " (override)" || echo " (from x-height and measure)")"
echo "  Headings: $([ "$PROPORTIONAL_HEADINGS" == true ] && echo "proportional" || echo "default ladder")"
echo "  Code scale: block ${CODE_SCALE:-0.85 (default)}, inline ${INLINE_CODE_SCALE:-1.0 (body size)}"
echo "  Chapter style: $CHAPTER_STYLE"
[[ "$CHAPTER_STYLE" == "canonical" ]] && echo "  Ornament: $ORNAMENT"
echo "  Section style: $SECTION_STYLE"
echo "  Quote style: $QUOTE_STYLE"
echo "  Geometry: $GEOMETRY"
echo "  Pages: $([ "$PAGES_MODE" == "auto" ] && echo "auto (provisional $PAGES_PROVISIONAL)" || echo "$PAGES (fixed)")"
echo "  Layout: $([ "$TWOSIDE_MODE" == true ] && echo "Two-sided (print)" || echo "One-sided (screen)")"
echo "  Page style: $PAGE_STYLE"
[[ "$PAGE_ORNAMENT" != "none" ]] && echo "  Page ornament: $PAGE_ORNAMENT ($PAGE_ORNAMENT_SIZE)"
echo "  Template: $TEMPLATE_FILE"
echo "  Book: $PROJECT_ROOT ($BOOK_CONFIG_SOURCE)"
[[ "$DRAFT_MODE" == true ]] && echo "  Draft ID: $DRAFT_ID"
[[ -n "$REVIEWER_NAME" ]] && echo "  Reviewer: $REVIEWER_NAME"
[[ -n "$DIFF_FROM" ]] && echo "  Diff: $DIFF_FROM_SHA -> $DIFF_TO_LABEL (changes highlighted in yellow)"
echo "  Protection: $([ "$APPLY_PROTECTION" == true ] && echo "Yes (no copy/print)" || echo "No")"
echo "  Output: $OUTPUT_FILE"
echo ""

warm_texlive_cache "$([[ -n "$DIFF_FROM" ]] && echo true || echo false)"

update_geometry_arg() {
    local new_geometry="$1" index
    for index in "${!PANDOC_ARGS[@]}"; do
        if [[ "${PANDOC_ARGS[$index]}" == --metadata=geometry:* ]]; then
            PANDOC_ARGS[$index]="--metadata=geometry:$new_geometry"
            return
        fi
    done
}

run_pdf_build() {
    run_in_pandoc_container -v "$TEXLIVE_VOLUME:/opt/texlive:ro"
}

run_pdf_build

if [[ "$PAGES_MODE" == "auto" ]]; then
    ACTUAL_PAGES=$(get_pdf_pages "$PANDOC_OUTPUT" 2>/dev/null | head -1 | tr -d '[:space:]')
    if [[ "$ACTUAL_PAGES" =~ ^[0-9]+$ && "$ACTUAL_PAGES" -gt 0 ]]; then
        OLD_BAND=$(kdp_band "$PAGES_PROVISIONAL")
        NEW_BAND=$(kdp_band "$ACTUAL_PAGES")
        echo ""
        echo "Page count: $ACTUAL_PAGES (provisional was $PAGES_PROVISIONAL, KDP band: $OLD_BAND -> $NEW_BAND)"
        if [[ "$OLD_BAND" != "$NEW_BAND" ]]; then
            echo "Page count crossed a KDP gutter band; building again with corrected margins..."
            update_geometry_arg "$(compute_geometry "$PAGE_FORMAT" "$ACTUAL_PAGES" "$SYMMETRIC_MARGINS")"
            run_pdf_build
        fi
    fi
fi

protect_pdf() {
    local owner_password
    owner_password=$(printf '%04x%04x%04x%04x' $RANDOM $RANDOM $RANDOM $RANDOM)
    if command -v qpdf >/dev/null 2>&1; then
        qpdf --encrypt '' "$owner_password" 256 --extract=n --print=none --modify=none -- "$TEMP_PDF" "$OUTPUT_FILE"
    else
        docker run --rm --entrypoint sh -v "$FULL_OUTPUT_DIR:/output" "$DOCKER_IMAGE" \
            -c 'apk add --no-cache qpdf >/dev/null 2>&1 \
                && qpdf --encrypt "" "$1" 256 --extract=n --print=none --modify=none -- "$2" "$3" \
                && if [ -n "$4" ]; then chown "$4" "$3"; fi' \
            protect-pdf "$owner_password" "$TEMP_PDF_IN_CONTAINER" "$OUTPUT_FILE_IN_CONTAINER" "$DOCKER_OWNER"
    fi
    rm -f "$TEMP_PDF"
}

if [[ "$APPLY_PROTECTION" == true && -f "$TEMP_PDF" ]]; then
    echo ""
    echo "Applying PDF protection..."
    protect_pdf
    echo "  Restrictions: copy=disabled, print=disabled, modify=disabled"
fi

echo ""
if [[ ! -f "$OUTPUT_FILE" ]]; then
    echo "Error: Output file was not created"
    exit 1
fi
echo "Done! Output: $OUTPUT_FILE"
echo "File size: $(du -h "$OUTPUT_FILE" | cut -f1)"
[[ "$DRAFT_MODE" == true ]] && echo "Draft ID: $DRAFT_ID"
report_placeholders
exit 0
