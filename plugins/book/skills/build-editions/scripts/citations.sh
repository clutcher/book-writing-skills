#!/usr/bin/env bash

KNOWN_CITATION_STYLES="alpha numeric"
DEFAULT_BIBLIOGRAPHY="sources/references.bib"
CITATION_JSON_NAME="bibliography.json"
CITATION_STYLE_NAME="citation-style.csl"
REFERENCE_LIST_DIV='^:::+[[:space:]]*\{[[:space:]]*#refs[[:space:]]*\}'

book_path() {
    local path="$1"
    [[ -z "$path" ]] && return 0
    [[ "$path" == /* ]] && echo "$path" || echo "$BOOK_ROOT/$path"
}

resolve_citation_settings() {
    BIBLIOGRAPHY_FILE="$(book_path "${BOOK_BIBLIOGRAPHY:-$DEFAULT_BIBLIOGRAPHY}")"
    CITATION_STYLE="${BOOK_CITATION_STYLE:-alpha}"
    CITATION_STYLE_FILE="$(book_path "${BOOK_CITATION_STYLE_FILE:-}")"
    fail_unless_known "citation style (sources.citation_style)" "$CITATION_STYLE" "$KNOWN_CITATION_STYLES"
    if [[ -n "$CITATION_STYLE_FILE" && ! -f "$CITATION_STYLE_FILE" ]]; then
        echo "Error: sources.citation_style_file names '$CITATION_STYLE_FILE', and there is no such file."
        exit 1
    fi
    [[ -n "$CITATION_STYLE_FILE" ]] || CITATION_STYLE_FILE="$ASSETS_DIR/csl/$CITATION_STYLE.csl"
}

files_hold_reference_list() {
    local file
    for file in "$@"; do
        grep -qE "$REFERENCE_LIST_DIV" "$file" 2>/dev/null && return 0
    done
    return 1
}

prepare_citations() {
    local host_files=() path
    for path in "${MANUSCRIPT_PATHS_IN_CONTAINER[@]}"; do
        case "$path" in
            /data/*) host_files+=("$PROJECT_ROOT/${path#/data/}") ;;
            /settings/*) host_files+=("$SETTINGS_DIR/${path#/settings/}") ;;
        esac
    done

    CITATION_PANDOC_ARGS=(--metadata="citation-bibliography-file:$(relative_to_root "$BIBLIOGRAPHY_FILE")")
    echo ""
    if [[ ! -f "$BIBLIOGRAPHY_FILE" ]]; then
        echo "Citations: no bibliography at $(relative_to_root "$BIBLIOGRAPHY_FILE"), so no --citeproc;"
        echo "           the build stops if the text cites a key."
        CITATION_PANDOC_ARGS+=(--lua-filter=/filters/citation-links.lua)
        return 0
    fi

    python3 "$SCRIPT_DIR/bibliography-to-csl.py" ${CONFIG_ARGS[@]+"${CONFIG_ARGS[@]}"} \
        --bibliography "$BIBLIOGRAPHY_FILE" --style "$CITATION_STYLE" --image "$DOCKER_IMAGE" \
        --output "$SETTINGS_DIR/$CITATION_JSON_NAME" \
        || { echo "Error: could not read the bibliography (see the message above)"; exit 1; }
    cp "$CITATION_STYLE_FILE" "$SETTINGS_DIR/$CITATION_STYLE_NAME"
    echo "Citations: style $CITATION_STYLE ($CITATION_STYLE_FILE)"

    CITATION_PANDOC_ARGS+=(
        --citeproc
        --bibliography="/settings/$CITATION_JSON_NAME"
        --csl="/settings/$CITATION_STYLE_NAME"
        --metadata=link-citations:true
    )
    if ! files_hold_reference_list "${host_files[@]}"; then
        CITATION_PANDOC_ARGS+=(--metadata=suppress-bibliography:true)
    fi
    CITATION_PANDOC_ARGS+=(--lua-filter=/filters/citation-links.lua)
}
