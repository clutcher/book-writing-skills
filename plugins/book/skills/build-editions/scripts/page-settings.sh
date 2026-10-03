#!/usr/bin/env bash

SUPPORTED_FORMATS="8x10 7.5x9.25 7x10 6.69x9.61 6.5x9.25 6.14x9.21 6x9 5.5x8.5 5x8"
KNOWN_FONTS="cochineal garamond cormorant-garamond crimson-pro baskerville palatino latin-modern"
KNOWN_HEADING_FONTS="match-body source-sans gyre-heros latin-modern-sans $KNOWN_FONTS"
KNOWN_FONT_SIZES="10pt 10.5pt 11pt 11.5pt 12pt"
KNOWN_CHAPTER_STYLES="classic technical bold elegant canonical"
KNOWN_SECTION_STYLES="technical scholarly literary editorial classic"
KNOWN_ORNAMENTS="hexagon varhexagon star sun square fleuron"
KNOWN_QUOTE_STYLES="italic plain small border dash guillemet quote"
KNOWN_PAGE_STYLES="header footer"
KNOWN_PAGE_ORNAMENTS="none spiral-straight spiral-curly wasy-hexagon wasy-verhexagon wasy-star wasy-sun adforn-fleuron adforn-leaf adforn-vine"
KNOWN_PAGE_ORNAMENT_SIZES="small medium large"
KNOWN_EDITIONS="print digital epub all"
KNOWN_TOP_LEVELS="part chapter section"

fail_unless_known() {
    local what="$1" value="$2" known="$3"
    for choice in $known; do
        [[ "$value" == "$choice" ]] && return 0
    done
    echo "Error: Unknown $what '$value'"
    echo "Available: ${known// /, }"
    exit 1
}

validate_page_format() {
    local format="$1"
    for known in $SUPPORTED_FORMATS; do
        [[ "$format" == "$known" ]] && return 0
    done
    if [[ ! "$format" =~ ^[0-9]+(\.[0-9]+)?x[0-9]+(\.[0-9]+)?$ ]]; then
        echo "Error: Invalid page format '$format' (expected WxH like 6x9 or 6.14x9.21)"
        echo "Known formats: $SUPPORTED_FORMATS"
        exit 1
    fi
}

validate_pages() {
    local pages="$1"
    [[ "$pages" == "auto" ]] && return 0
    [[ "$pages" =~ ^[0-9]+$ && "$pages" -gt 0 ]] && return 0
    echo "Error: --pages must be a positive integer or 'auto' (got '$pages')"
    exit 1
}

validate_font() { fail_unless_known "font" "$1" "$KNOWN_FONTS"; }
validate_italic_font() { fail_unless_known "italic font" "$1" "$KNOWN_FONTS"; }
validate_heading_font() { fail_unless_known "heading font" "$1" "$KNOWN_HEADING_FONTS"; }
validate_font_size() { fail_unless_known "font size" "$1" "$KNOWN_FONT_SIZES"; }
validate_chapter_style() { fail_unless_known "chapter style" "$1" "$KNOWN_CHAPTER_STYLES"; }
validate_section_style() { fail_unless_known "section style" "$1" "$KNOWN_SECTION_STYLES"; }
validate_ornament() { fail_unless_known "ornament" "$1" "$KNOWN_ORNAMENTS"; }
validate_quote_style() { fail_unless_known "quote style" "$1" "$KNOWN_QUOTE_STYLES"; }
validate_page_style() { fail_unless_known "page style" "$1" "$KNOWN_PAGE_STYLES"; }
validate_page_ornament() { fail_unless_known "page ornament" "$1" "$KNOWN_PAGE_ORNAMENTS"; }
validate_page_ornament_size() { fail_unless_known "page ornament size" "$1" "$KNOWN_PAGE_ORNAMENT_SIZES"; }
validate_edition() { fail_unless_known "edition" "$1" "$KNOWN_EDITIONS"; }
validate_top_level() { fail_unless_known "top level" "$1" "$KNOWN_TOP_LEVELS"; }

parse_format_dim() {
    awk -v F="$1" 'BEGIN { n = split(F, a, "x"); if (n == 2) printf "%s %s", a[1], a[2]; else printf "6 9" }'
}

kdp_band() {
    awk -v P="$1" 'BEGIN {
        if      (P <= 150) print "a"
        else if (P <= 300) print "b"
        else if (P <= 500) print "c"
        else if (P <= 700) print "d"
        else               print "e"
    }'
}

compute_geometry() {
    local format="$1" pages="$2" symmetric="${3:-false}"
    read -r W H <<< "$(parse_format_dim "$format")"
    awk -v W="$W" -v H="$H" -v P="$pages" -v SYM="$symmetric" 'BEGIN {
        if      (P <= 150) g = 0.375
        else if (P <= 300) g = 0.500
        else if (P <= 500) g = 0.625
        else if (P <= 700) g = 0.750
        else               g = 0.875
        inner  = 0.143 * W
        if (inner < g) inner = g
        outer  = 0.106 * W
        if (SYM == "true") {
            center = (inner + outer) / 2
            inner = center
            outer = center
        }
        top    = 0.076 * H
        bottom = 0.0923 * H
        printf "paperwidth=%.3fin,paperheight=%.3fin,top=%.3fin,bottom=%.3fin,inner=%.3fin,outer=%.3fin", W, H, top, bottom, inner, outer
    }'
}

resolve_leading() {
    local family="$1" size_raw="$2" geometry="$3" override="$4"
    if [[ -n "$override" ]]; then echo "$override"; return; fi
    local helper="$SCRIPT_DIR/compute-leading.py"
    [[ -f "$helper" ]] || return 0
    command -v python3 >/dev/null 2>&1 || return 0
    local size="${size_raw%pt}"
    local paper_width inner outer text_width
    paper_width=$(sed -n 's/.*paperwidth=\([0-9.]*\)in.*/\1/p' <<<"$geometry")
    inner=$(sed -n 's/.*inner=\([0-9.]*\)in.*/\1/p' <<<"$geometry")
    outer=$(sed -n 's/.*outer=\([0-9.]*\)in.*/\1/p' <<<"$geometry")
    [[ -n "$paper_width" && -n "$inner" && -n "$outer" ]] || return 0
    text_width=$(awk -v a="$paper_width" -v b="$inner" -v c="$outer" 'BEGIN{printf "%.4f", a-b-c}')
    python3 "$helper" --family "$family" --size "$size" --text-width-in "$text_width" 2>/dev/null || true
}

nearest_standard_size() {
    awk -v s="${1%pt}" 'BEGIN{ if (s<10.5) print "10pt"; else if (s<11.5) print "11pt"; else print "12pt" }'
}

get_pdf_pages() {
    local pdf="$1"
    if command -v pdfinfo >/dev/null 2>&1; then
        pdfinfo "$pdf" 2>/dev/null | awk '/^Pages:/ {print $2}'
    elif command -v qpdf >/dev/null 2>&1; then
        qpdf --show-npages "$pdf" 2>/dev/null
    else
        docker run --rm --entrypoint sh -v "$(dirname "$pdf"):/work:ro" "$DOCKER_IMAGE" \
            -c "apk add --no-cache qpdf >/dev/null 2>&1 && qpdf --show-npages /work/$(basename "$pdf")" 2>/dev/null
    fi
}

get_font_name() {
    case "$1" in
        "cochineal")          echo "Cochineal" ;;
        "garamond")           echo "EB Garamond" ;;
        "cormorant-garamond") echo "Cormorant Garamond" ;;
        "crimson-pro")        echo "Crimson Pro" ;;
        "baskerville")        echo "BaskervilleF" ;;
        "palatino")           echo "Domitian" ;;
        *)                    echo "Latin Modern Roman" ;;
    esac
}

get_italic_file_for_shortcut() {
    case "$1" in
        "cochineal")          echo "Cochineal-Italic.otf" ;;
        "garamond")           echo "EBGaramond-Italic.otf" ;;
        "cormorant-garamond") echo "CormorantGaramond-Italic.ttf" ;;
        "crimson-pro")        echo "CrimsonPro-Italic.ttf" ;;
        "baskerville")        echo "BaskervilleF-Italic.otf" ;;
        "palatino")           echo "Domitian-Italic.otf" ;;
        "latin-modern")       echo "lmroman10-italic.otf" ;;
        *)                    echo "" ;;
    esac
}

get_bold_italic_file_for_shortcut() {
    case "$1" in
        "cochineal")          echo "Cochineal-BoldItalic.otf" ;;
        "garamond")           echo "EBGaramond-BoldItalic.otf" ;;
        "cormorant-garamond") echo "CormorantGaramond-SemiBoldItalic.ttf" ;;
        "crimson-pro")        echo "CrimsonPro-BoldItalic.ttf" ;;
        "baskerville")        echo "BaskervilleF-BoldItalic.otf" ;;
        "palatino")           echo "Domitian-BoldItalic.otf" ;;
        "latin-modern")       echo "lmroman10-bolditalic.otf" ;;
        *)                    echo "" ;;
    esac
}

get_heading_font_name() {
    case "$1" in
        "source-sans")        echo "Source Sans Pro" ;;
        "gyre-heros")         echo "TeX Gyre Heros" ;;
        "latin-modern-sans")  echo "Latin Modern Sans" ;;
        "match-body")         echo "" ;;
        *)                    get_font_name "$1" ;;
    esac
}

ALL_FONT_PACKAGES="sourcecodepro sourcesanspro tex-gyre adforn wasysym wasy latexmk cochineal ebgaramond cormorantgaramond crimsonpro baskervillef domitian soul tcolorbox environ pdfcol fontsize"
DIFF_PACKAGES="soul tcolorbox environ pdfcol"
FONT_MARKER="/opt/texlive/.fonts-installed"
DIFF_PKG_MARKER="/opt/texlive/.diff-pkgs-installed"
FONTCONFIG_CACHE_DIR="/opt/texlive/.fontconfig-cache"

write_fontconfig_file() {
    local target="$1"
    cat > "$target" <<EOF
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
  <dir>/opt/texlive/texdir/texmf-dist/fonts/opentype</dir>
  <dir>/opt/texlive/texdir/texmf-dist/fonts/truetype</dir>
  <cachedir>$FONTCONFIG_CACHE_DIR</cachedir>
  <cachedir>/tmp/fontconfig-cache</cachedir>
</fontconfig>
EOF
}

texlive_marker_present() {
    docker run --rm --entrypoint sh -v "$TEXLIVE_VOLUME:/opt/texlive:ro" "$DOCKER_IMAGE" \
        -c "test -f $1 && echo yes || echo no" 2>/dev/null
}

run_as_texlive_owner() {
    docker run --rm --entrypoint sh \
        -v "$TEXLIVE_VOLUME:/opt/texlive" \
        -v "$SETTINGS_DIR:/settings:ro" \
        -e FONTCONFIG_FILE=/settings/fonts.conf \
        "$DOCKER_IMAGE" -c "$1"
}

warm_texlive_cache() {
    local need_diff_packages="${1:-false}"
    docker volume inspect "$TEXLIVE_VOLUME" >/dev/null 2>&1 || docker volume create "$TEXLIVE_VOLUME" >/dev/null
    if [[ "$(texlive_marker_present "$FONT_MARKER")" != "yes" ]]; then
        echo "Installing font packages into $TEXLIVE_VOLUME (one-time setup)..."
        run_as_texlive_owner "tlmgr install $ALL_FONT_PACKAGES >/dev/null 2>&1 && luaotfload-tool --update >/dev/null 2>&1 && mkdir -p $FONTCONFIG_CACHE_DIR && fc-cache >/dev/null 2>&1 && touch $FONT_MARKER $DIFF_PKG_MARKER"
    elif [[ "$need_diff_packages" == true && "$(texlive_marker_present "$DIFF_PKG_MARKER")" != "yes" ]]; then
        echo "Installing diff-mode packages into $TEXLIVE_VOLUME (one-time setup)..."
        run_as_texlive_owner "tlmgr install $DIFF_PACKAGES >/dev/null 2>&1 && touch $DIFF_PKG_MARKER"
    else
        echo "Using cached fonts (volume: $TEXLIVE_VOLUME)"
    fi
}
