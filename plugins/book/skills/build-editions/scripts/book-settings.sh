#!/usr/bin/env bash

LIB_DIR="$(cd "$SCRIPT_DIR/../../../lib" && pwd)"
BOOK_CONFIG_TOOL="$LIB_DIR/book_config.py"
CONFIG_ARGS=()

_cli_set=""
mark_cli() { _cli_set="$_cli_set $1 "; }
is_cli_set() { [[ "$_cli_set" == *" $1 "* ]]; }

read_book_config() {
    python3 "$BOOK_CONFIG_TOOL" ${CONFIG_ARGS[@]+"${CONFIG_ARGS[@]}"} --start "$1" "${@:2}"
}

load_book_settings() {
    local start_dir="$1" shell_lines
    if ! shell_lines="$(read_book_config "$start_dir" paths --shell)"; then
        echo "Error: could not read the book config (see the message above)"
        exit 1
    fi
    eval "$shell_lines"
    if ! shell_lines="$(read_book_config "$start_dir" metadata --shell)"; then
        echo "Error: could not read the book metadata (see the message above)"
        exit 1
    fi
    eval "$shell_lines"
    DOCKER_IMAGE="$BOOK_TOOLS_PANDOC_IMAGE"
    TEXLIVE_VOLUME="$BOOK_TOOLS_PANDOC_VOLUME"
    set_docker_user
}

set_docker_user() {
    DOCKER_USER_ARGS=()
    DOCKER_OWNER=""
    case "$(uname -s)" in
        MINGW*|MSYS*|CYGWIN*) return 0 ;;
    esac
    command -v id >/dev/null 2>&1 || return 0
    DOCKER_OWNER="$(id -u):$(id -g)"
    DOCKER_USER_ARGS=(-u "$DOCKER_OWNER")
}

path_before_rename() {
    local wanted="$1" renamed_files="$2" new_path old_path
    while IFS=$'\t' read -r new_path old_path; do
        if [[ -n "$new_path" && "$new_path" == "$wanted" ]]; then
            printf '%s' "$old_path"
            return 0
        fi
    done <<< "$renamed_files"
    printf '%s' "$wanted"
}

book_order_files() {
    local manuscript_dir="$1" listed
    if ! listed="$(read_book_config "$BOOK_ROOT" --set "manuscript.dir=$manuscript_dir" files)"; then
        echo "Error: could not list the manuscript files (see the message above)" >&2
        return 1
    fi
    cut -f1 <<< "$listed"
}

matches_file_pattern() {
    local file_name="$1"
    [[ "$file_name" == $FILE_PATTERN ]]
}

list_manuscript_files() {
    local manuscript_dir="$1" ordered_files file relative_file
    ordered_files="$(book_order_files "$manuscript_dir")" || return 1
    while IFS= read -r file; do
        [[ -n "$file" ]] || continue
        matches_file_pattern "$(basename "$file")" || continue
        relative_file="$(relative_to_root "$file")"
        [[ -n "$EXCLUDE_PATTERN" ]] && grep -qE "$EXCLUDE_PATTERN" <<< "$relative_file" && continue
        echo "$relative_file"
    done <<< "$ordered_files"
}

is_yes() { [[ "$1" == "true" || "$1" == "yes" ]]; }
is_no() { [[ "$1" == "false" || "$1" == "no" ]]; }

take_value() {
    local cli_name="$1" variable="$2" value="$3"
    is_cli_set "$cli_name" && return 0
    [[ -n "$value" ]] && printf -v "$variable" '%s' "$value"
    return 0
}

take_flag() {
    local cli_name="$1" variable="$2" value="$3"
    is_cli_set "$cli_name" && return 0
    is_yes "$value" && printf -v "$variable" '%s' true
    is_no "$value" && printf -v "$variable" '%s' false
    return 0
}

apply_book_defaults() {
    take_value title BOOK_TITLE "${BOOK_META_TITLE:-}"
    take_value subtitle BOOK_SUBTITLE "${BOOK_META_SUBTITLE:-}"
    take_value author BOOK_AUTHOR "${BOOK_META_AUTHOR:-}"
    take_value format PAGE_FORMAT "${BOOK_META_FORMAT:-}"
    if ! is_cli_set layout && [[ "${BOOK_META_LAYOUT:-}" == "oneside" ]]; then TWOSIDE_MODE=false; fi
    take_value font FONT_CHOICE "${BOOK_META_FONT:-}"
    take_value heading-font HEADING_FONT "${BOOK_META_HEADING_FONT:-}"
    take_value italic-font ITALIC_FONT_CHOICE "${BOOK_META_ITALIC_FONT:-}"
    take_value font-size FONT_SIZE "${BOOK_META_FONT_SIZE:-}"
    if ! is_cli_set proportional-headings && [[ "${BOOK_META_HEADING_SCALE:-}" =~ ^[Pp]roportional ]]; then
        PROPORTIONAL_HEADINGS=true
    fi
    take_value leading LEADING_OVERRIDE "${BOOK_META_LEADING:-}"
    take_value code-scale CODE_SCALE "${BOOK_META_CODE_SCALE:-}"
    take_value inline-code-scale INLINE_CODE_SCALE "${BOOK_META_INLINE_CODE_SCALE:-}"
    take_value chapter-style CHAPTER_STYLE "${BOOK_META_CHAPTER_STYLE:-}"
    take_value section-style SECTION_STYLE "${BOOK_META_SECTION_STYLE:-}"
    take_value pages PAGES "${BOOK_META_PAGES:-}"
    take_value ornament ORNAMENT "${BOOK_META_ORNAMENT:-}"
    take_value quote-style QUOTE_STYLE "${BOOK_META_QUOTE_STYLE:-}"
    take_value highlight HIGHLIGHT_STYLE "${BOOK_META_HIGHLIGHT:-}"
    take_value top-level TOP_LEVEL "${BOOK_META_TOP_LEVEL:-}"
    take_value toc-depth TOC_DEPTH "${BOOK_META_TOC_DEPTH:-}"
    take_flag numbered NUMBERED "${BOOK_META_NUMBERED:-}"
    take_flag toc GENERATE_TOC "${BOOK_META_TOC:-}"
    take_value pattern FILE_PATTERN "${BOOK_META_PATTERN:-}"
    take_value exclude EXCLUDE_PATTERN "${BOOK_META_EXCLUDE:-}"
    take_value page-style PAGE_STYLE "${BOOK_META_PAGE_STYLE:-}"
    take_value page-ornament PAGE_ORNAMENT "${BOOK_META_PAGE_ORNAMENT:-}"
    take_value page-ornament-size PAGE_ORNAMENT_SIZE "${BOOK_META_PAGE_ORNAMENT_SIZE:-}"
    take_flag part-pages PART_PAGES "${BOOK_META_PART_PAGES:-}"
    take_flag part-overview PART_OVERVIEW "${BOOK_META_PART_OVERVIEW:-}"
    take_flag all-page-folios ALL_PAGE_FOLIOS "${BOOK_META_ALL_PAGE_FOLIOS:-}"
    take_value cover-front COVER_FRONT "${BOOK_META_COVER_FRONT:-}"
    take_value cover-back COVER_BACK "${BOOK_META_COVER_BACK:-}"
    take_value ebook-cover EBOOK_COVER "${BOOK_META_EBOOK_COVER:-}"
    take_value placeholder-text PLACEHOLDER_TOKEN "${BOOK_META_PLACEHOLDER_TEXT:-}"
    take_value hyphenation-language HYPHENATION_LANGUAGE "${BOOK_META_HYPHENATION_LANGUAGE:-}"
    EPUB_IDENTIFIER="${BOOK_META_EPUB_IDENTIFIER:-}"
    PUBLICATION_DATE="${BOOK_META_PUBLICATION_DATE:-}"
    BOOK_PUBLISHER="${BOOK_META_PUBLISHER:-}"
    BOOK_SUBJECTS="${BOOK_META_SUBJECTS:-}"
    BOOK_DESCRIPTION="${BOOK_META_DESCRIPTION:-}"
    BOOK_LANGUAGE="${BOOK_META_LANGUAGE:-en-US}"
    ACCESSIBILITY_SUMMARY="${BOOK_META_ACCESSIBILITY_SUMMARY:-}"
}

validate_settings() {
    validate_page_format "$PAGE_FORMAT"
    validate_font "$FONT_CHOICE"
    [[ -n "$ITALIC_FONT_CHOICE" ]] && validate_italic_font "$ITALIC_FONT_CHOICE"
    validate_heading_font "$HEADING_FONT"
    validate_font_size "$FONT_SIZE"
    validate_chapter_style "$CHAPTER_STYLE"
    validate_section_style "$SECTION_STYLE"
    validate_ornament "$ORNAMENT"
    validate_pages "$PAGES"
    validate_quote_style "$QUOTE_STYLE"
    validate_page_style "$PAGE_STYLE"
    validate_page_ornament "$PAGE_ORNAMENT"
    validate_page_ornament_size "$PAGE_ORNAMENT_SIZE"
    validate_top_level "$TOP_LEVEL"
    return 0
}

relative_to_root() {
    local path="$1"
    case "$path" in
        "$BOOK_ROOT") echo "." ;;
        "$BOOK_ROOT"/*) echo "${path#"$BOOK_ROOT"/}" ;;
        *) echo "$path" ;;
    esac
}

slugify() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//'
}

get_lastname() {
    echo "$1" | awk '{print $NF}'
}
