#!/usr/bin/env bash

KNOWN_PAPER_ENGINES="xelatex pdflatex"
KNOWN_PAPER_FORMATS="a4 letter"
BUILT_IN_PAPER_TEMPLATES="article acm ieee lncs"
PAPER_TEX_IMAGE_SIZE="2.6 GB"
BOOK_ONLY_EDITIONS="print digital epub"

is_paper() { [[ "${BOOK_KIND:-book}" == "paper" ]]; }

resolve_edition_for_kind() {
    local book_edition
    if is_paper; then
        [[ "$EDITION" == "all" ]] && EDITION="paper"
        for book_edition in $BOOK_ONLY_EDITIONS; do
            if [[ "$EDITION" == "$book_edition" ]]; then
                echo "Error: this is a paper (kind: paper in book.yaml), and a paper has only the paper edition."
                echo "       The $EDITION edition is for a book. Run build-book.sh with no --edition, or --edition paper."
                exit 1
            fi
        done
        refuse_for_paper "$REVIEWER_NAME" "--reviewer-copy"
        refuse_for_paper "$DIFF_FROM" "--changes-since"
        refuse_template_file_for_paper
        return 0
    fi
    if [[ "$EDITION" == "paper" ]]; then
        echo "Error: the paper edition needs kind: paper in book.yaml; this is a book."
        exit 1
    fi
    if [[ "$BUILD_ARXIV" == true || "$ANONYMOUS_OPTION" == true ]]; then
        echo "Error: --arxiv and --anonymous are for a paper (kind: paper in book.yaml); this is a book."
        exit 1
    fi
}

refuse_for_paper() {
    local value="$1" option="$2"
    [[ -z "$value" ]] && return 0
    echo "Error: $option is for a book; a paper edition has no reviewer copies or changes copies."
    exit 1
}

refuse_template_file_for_paper() {
    [[ -z "$TEMPLATE_FILE" ]] && return 0
    echo "Error: --template is for a book. A paper names its built-in template in book.yaml:"
    echo "       paper.template is one of: $BUILT_IN_PAPER_TEMPLATES."
    exit 1
}

apply_paper_defaults() {
    is_paper || return 0
    [[ "$ANONYMOUS_OPTION" == true ]] && PAPER_ANONYMOUS=true
    fail_unless_known "paper engine" "$PAPER_ENGINE" "$KNOWN_PAPER_ENGINES"
    fail_unless_known "paper format" "$PAPER_FORMAT" "$KNOWN_PAPER_FORMATS"
    fail_unless_known "paper template" "$PAPER_TEMPLATE" "$BUILT_IN_PAPER_TEMPLATES"
}

paper_template_file() {
    echo "$ASSETS_DIR/templates/paper-$PAPER_TEMPLATE.tex"
}

ensure_paper_tex_image() {
    docker image inspect "$PAPER_TEX_IMAGE" >/dev/null 2>&1 && return 0
    echo ""
    echo "Pulling the TeX Live image for papers, once ($PAPER_TEX_IMAGE_SIZE): $PAPER_TEX_IMAGE"
    if ! docker pull "$PAPER_TEX_IMAGE" >/dev/null; then
        echo "Error: could not pull the TeX Live image $PAPER_TEX_IMAGE (tools.paper_tex_image)."
        echo "       A paper compiles in full TeX Live 2025, as arXiv does. The first build needs"
        echo "       the network to pull it; check the connection and run the build again."
        exit 1
    fi
}

first_paper_author() {
    python3 -c 'import json, sys; authors = json.loads(sys.argv[1] or "[]"); print(authors[0]["name"] if authors else "")' "$PAPER_AUTHORS"
}

paper_name_slug() {
    if is_yes "$PAPER_ANONYMOUS"; then
        echo "anonymous"
        return 0
    fi
    local author
    author="$(first_paper_author)"
    [[ -z "$author" ]] && author="$BOOK_AUTHOR"
    is_set_for_name "$author" || return 0
    slugify "$(get_lastname "$author")"
}

paper_base_name() {
    local title_slug="$1" name_slug="$2"
    if [[ -n "$title_slug" && -n "$name_slug" ]]; then
        echo "${title_slug}-${name_slug}"
    elif is_yes "$PAPER_ANONYMOUS"; then
        echo "paper-anonymous"
    else
        echo "paper"
    fi
}

paper_body_paths() {
    local abstract_relative path
    abstract_relative="/data/$(relative_to_root "$PAPER_ABSTRACT")"
    for path in "${MANUSCRIPT_PATHS_IN_CONTAINER[@]}"; do
        [[ "$path" == "$abstract_relative" ]] && continue
        echo "$path"
    done
}

paper_latexmk_option() {
    case "$PAPER_ENGINE" in
        pdflatex) echo "-pdf" ;;
        *)        echo "-xelatex" ;;
    esac
}

run_latex_in_container() {
    local build_folder="$1" tex_name="$2"
    docker run --rm \
        ${DOCKER_USER_ARGS[@]+"${DOCKER_USER_ARGS[@]}"} \
        --network none \
        -e HOME=/tmp \
        -e TEXMFVAR=/tmp/texmf-var \
        -e max_print_line=1000 \
        -v "$build_folder:/work" \
        -w /work \
        --entrypoint latexmk \
        "$PAPER_TEX_IMAGE" \
        "$(paper_latexmk_option)" -interaction=nonstopmode -halt-on-error -file-line-error "$tex_name"
}

write_paper_tex() {
    local tex_in_container="$1" body_paths=() path
    while IFS= read -r path; do
        [[ -n "$path" ]] && body_paths+=("$path")
    done < <(paper_body_paths)
    [[ ${#body_paths[@]} -gt 0 ]] || { echo "Error: the paper has no section files besides the abstract"; exit 1; }

    PANDOC_ARGS=(
        --from=markdown+autolink_bare_uris+raw_tex
        --to=latex
        --standalone
        --template="/template/$(basename "$TEMPLATE_FILE")"
        --top-level-division=section
        --syntax-highlighting="$HIGHLIGHT_STYLE"
        --resource-path="/data/$MANUSCRIPT_DIR:/data"
        --metadata-file=/settings/filter-settings.json
        --metadata-file=/settings/paper-metadata.json
        --metadata="paper-edition:true"
        --metadata="papersize:$PAPER_FORMAT"
        --metadata="lang:$BOOK_LANGUAGE"
        --lua-filter=/filters/paper-mode.lua
        "${CITATION_PANDOC_ARGS[@]}"
    )
    [[ -n "$BOOK_TITLE" ]] && PANDOC_ARGS+=(--metadata="title:$BOOK_TITLE")
    PANDOC_ARGS+=("${body_paths[@]}" -o "$tex_in_container")
    run_in_pandoc_container
}

check_anonymous_images() {
    local build_folder="$1"
    is_yes "$PAPER_ANONYMOUS" || return 0
    python3 "$SCRIPT_DIR/image_metadata.py" "$build_folder" > "$SETTINGS_DIR/image-metadata.txt" 2>&1
}

report_anonymous_images() {
    local status="$1"
    is_yes "$PAPER_ANONYMOUS" || return 0
    if [[ "$status" -eq 0 ]]; then
        echo "No image the paper uses names anyone in its metadata."
        return 0
    fi
    echo ""
    if [[ "$status" -ne 1 ]]; then
        echo "The image metadata could not be read, so nobody checked that the images are anonymous:"
        sed 's/^/    /' "$SETTINGS_DIR/image-metadata.txt"
        return 0
    fi
    echo "NOT ANONYMOUS: these images name someone in their metadata (image-metadata):"
    grep -v '^$' "$SETTINGS_DIR/image-metadata.txt" | sed 's/^/    /'
    echo "  The PDF and the .tex were still written. Clean the images and build again."
}

build_paper() {
    local base_name tex_file build_folder latex_log bundle_file authors_line image_status=0
    local metadata_args=() bundle_check_args=()
    base_name="$(basename "$OUTPUT_FILE" .pdf)"
    tex_file="$FULL_OUTPUT_DIR/$base_name.tex"
    build_folder="$FULL_OUTPUT_DIR/.paper-build-${TIMESTAMP}-${RANDOM_SUFFIX}"
    latex_log="$SETTINGS_DIR/latexmk.log"
    CLEANUP_PATHS+=("$build_folder")
    is_yes "$PAPER_ANONYMOUS" && metadata_args+=(--anonymous)

    authors_line="$(python3 "$SCRIPT_DIR/paper-metadata.py" ${CONFIG_ARGS[@]+"${CONFIG_ARGS[@]}"} \
        ${metadata_args[@]+"${metadata_args[@]}"} --output "$SETTINGS_DIR/paper-metadata.json")" \
        || { echo "Error: could not write the paper title block (see the message above)"; exit 1; }

    echo ""
    echo "Building the paper..."
    echo "  Mode: $([ "$DRAFT_MODE" == true ] && echo "DRAFT (only the file name says so)" || echo "FINAL")"
    echo "  Engine: $PAPER_ENGINE"
    echo "  Paper size: $PAPER_FORMAT"
    echo "  Authors: $authors_line"
    echo "  Abstract: $(relative_to_root "$PAPER_ABSTRACT")"
    [[ -n "$PAPER_ARXIV_CATEGORY" ]] && echo "  arXiv category: $PAPER_ARXIV_CATEGORY"
    echo "  Template: $TEMPLATE_FILE"
    echo "  TeX Live image: $PAPER_TEX_IMAGE"
    echo "  Book: $PROJECT_ROOT ($BOOK_CONFIG_SOURCE)"
    echo "  LaTeX source: $tex_file"
    echo "  Output: $OUTPUT_FILE"

    write_paper_tex "/output/$base_name.tex"
    [[ -f "$tex_file" ]] || { echo "Error: pandoc wrote no $tex_file"; exit 1; }

    python3 "$SCRIPT_DIR/paper_source.py" stage --tex "$tex_file" \
        --search "$FULL_MANUSCRIPT" --search "$PROJECT_ROOT" --to "$build_folder" \
        || { echo "Error: could not gather the files the paper uses (see the message above)"; exit 1; }
    check_anonymous_images "$build_folder" || image_status=$?

    ensure_paper_tex_image
    echo ""
    echo "Running latexmk with $PAPER_ENGINE..."
    if ! run_latex_in_container "$build_folder" "$base_name.tex" > "$latex_log" 2>&1; then
        echo "Error: LaTeX could not build the paper. What LaTeX said:"
        if grep -qE '^(!|.*\.tex:[0-9]+: )' "$latex_log"; then
            grep -E '^(!|.*\.tex:[0-9]+: )' "$latex_log" | head -20 | sed 's/^/    /'
        else
            tail -15 "$latex_log" | sed 's/^/    /'
        fi
        echo "  The LaTeX source is kept at $tex_file"
        exit 1
    fi
    cp "$build_folder/$base_name.pdf" "$OUTPUT_FILE"

    echo ""
    echo "Done! Output: $OUTPUT_FILE"
    echo "LaTeX source: $tex_file"
    echo "File size: $(du -h "$OUTPUT_FILE" | cut -f1)"

    if [[ "$BUILD_ARXIV" == true ]]; then
        bundle_file="$FULL_OUTPUT_DIR/$base_name-arxiv.tar.gz"
        echo ""
        echo "Writing the arXiv source bundle..."
        python3 "$SCRIPT_DIR/paper_source.py" bundle --folder "$build_folder" \
            --main "$base_name.tex" --output "$bundle_file" \
            || { echo "Error: could not write the arXiv bundle (see the message above)"; exit 1; }
        echo ""
        echo "Checking the bundle in a clean folder..."
        is_yes "$PAPER_ANONYMOUS" && bundle_check_args+=(--anonymous)
        python3 "$SCRIPT_DIR/arxiv-bundle-check.py" ${CONFIG_ARGS[@]+"${CONFIG_ARGS[@]}"} \
            --engine "$PAPER_ENGINE" ${bundle_check_args[@]+"${bundle_check_args[@]}"} "$bundle_file" \
            || echo "  The bundle check reported problems (above). The bundle was still written."
    fi
    report_anonymous_images "$image_status"
    report_placeholders
    exit 0
}
