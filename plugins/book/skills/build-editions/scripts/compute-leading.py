#!/usr/bin/env python3
"""Compute the LaTeX \\setstretch value for body text from the font x-height and the measure.

    L = k(cpl) * size * xfactor          leading in points
    xfactor = 0.5 + 0.5 * (x / x_ref)    a small x-height takes less leading
    N = L / D(size)                      \\setstretch over the default baselineskip

The x-height and the average lowercase advance are read from the font file that fc-match
finds for the family. Prints N. Exits 2 when the font cannot be found or read, so the build
falls back to the template default. The model is explained in references/leading-model.md.
"""

import argparse
import shutil
import struct
import subprocess
import sys
sys.dont_write_bytecode = True
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

from book_config import ConfigError, add_config_arguments, config_from_args

REFERENCE_X_HEIGHT = 0.448
CLASS_BASELINESKIP = {10: 12.0, 11: 13.6, 12: 14.5}
FONTSIZE_PACKAGE_FACTOR = 1.2
MEASURE_COEFFICIENTS = [(45, 1.20), (55, 1.28), (66, 1.35), (80, 1.42), (90, 1.45)]
POINTS_PER_INCH = 72.0
LOWERCASE_LETTERS = "abcdefghijklmnopqrstuvwxyz"
OS2_X_HEIGHT_OFFSET = 86
OS2_FIRST_VERSION_WITH_X_HEIGHT = 2
EXIT_TOOL_FAILED = 2


class FontReadError(Exception):
    pass


@dataclass
class FontMetrics:
    x_height: float
    average_lowercase_advance: float


def default_baselineskip(size):
    rounded = int(round(size))
    if abs(size - rounded) < 1e-9 and rounded in CLASS_BASELINESKIP:
        return CLASS_BASELINESKIP[rounded]
    return FONTSIZE_PACKAGE_FACTOR * size


def leading_coefficient(characters_per_line):
    if characters_per_line <= MEASURE_COEFFICIENTS[0][0]:
        return MEASURE_COEFFICIENTS[0][1]
    if characters_per_line >= MEASURE_COEFFICIENTS[-1][0]:
        return MEASURE_COEFFICIENTS[-1][1]
    for (low_cpl, low_k), (high_cpl, high_k) in zip(MEASURE_COEFFICIENTS, MEASURE_COEFFICIENTS[1:]):
        if low_cpl <= characters_per_line <= high_cpl:
            return low_k + (characters_per_line - low_cpl) / (high_cpl - low_cpl) * (high_k - low_k)
    return MEASURE_COEFFICIENTS[2][1]


@dataclass
class LeadingResult:
    characters_per_line: float
    coefficient: float
    x_factor: float
    leading_points: float
    baselineskip: float
    stretch: float


def compute_stretch(metrics, size, text_width_inches, reference_x_height=REFERENCE_X_HEIGHT):
    characters_per_line = text_width_inches * POINTS_PER_INCH / (metrics.average_lowercase_advance * size)
    coefficient = leading_coefficient(characters_per_line)
    x_factor = 0.5 + 0.5 * (metrics.x_height / reference_x_height)
    leading_points = coefficient * size * x_factor
    baselineskip = default_baselineskip(size)
    return LeadingResult(characters_per_line, coefficient, x_factor, leading_points,
                         baselineskip, leading_points / baselineskip)


def sfnt_tables(data):
    if data[:4] == b"ttcf":
        first_font_offset = struct.unpack(">I", data[12:16])[0]
        data_offset = first_font_offset
    else:
        data_offset = 0
    table_count = struct.unpack(">H", data[data_offset + 4:data_offset + 6])[0]
    tables = {}
    for index in range(table_count):
        record = data_offset + 12 + 16 * index
        tag = data[record:record + 4].decode("latin-1")
        offset, length = struct.unpack(">II", data[record + 8:record + 16])
        tables[tag] = data[offset:offset + length]
    return tables


def glyph_from_format_4(subtable, codepoint):
    segment_count = struct.unpack(">H", subtable[6:8])[0] // 2
    end_codes_at = 14
    start_codes_at = end_codes_at + 2 * segment_count + 2
    deltas_at = start_codes_at + 2 * segment_count
    range_offsets_at = deltas_at + 2 * segment_count
    for segment in range(segment_count):
        end_code = struct.unpack(">H", subtable[end_codes_at + 2 * segment:end_codes_at + 2 * segment + 2])[0]
        if codepoint > end_code:
            continue
        start_code = struct.unpack(">H", subtable[start_codes_at + 2 * segment:start_codes_at + 2 * segment + 2])[0]
        if codepoint < start_code:
            return 0
        delta = struct.unpack(">h", subtable[deltas_at + 2 * segment:deltas_at + 2 * segment + 2])[0]
        range_offset_position = range_offsets_at + 2 * segment
        range_offset = struct.unpack(">H", subtable[range_offset_position:range_offset_position + 2])[0]
        if range_offset == 0:
            return (codepoint + delta) & 0xFFFF
        glyph_position = range_offset_position + range_offset + 2 * (codepoint - start_code)
        glyph = struct.unpack(">H", subtable[glyph_position:glyph_position + 2])[0]
        return (glyph + delta) & 0xFFFF if glyph else 0
    return 0


def glyph_from_format_12(subtable, codepoint):
    group_count = struct.unpack(">I", subtable[12:16])[0]
    for group in range(group_count):
        start_char, end_char, start_glyph = struct.unpack(">III", subtable[16 + 12 * group:28 + 12 * group])
        if start_char <= codepoint <= end_char:
            return start_glyph + codepoint - start_char
    return 0


GLYPH_READERS = {4: glyph_from_format_4, 12: glyph_from_format_12}
PREFERRED_ENCODINGS = [(3, 10), (0, 4), (3, 1), (0, 3), (0, 1), (0, 0)]


def unicode_subtable(cmap):
    subtable_count = struct.unpack(">H", cmap[2:4])[0]
    found = {}
    for index in range(subtable_count):
        platform, encoding, offset = struct.unpack(">HHI", cmap[4 + 8 * index:12 + 8 * index])
        subtable_format = struct.unpack(">H", cmap[offset:offset + 2])[0]
        if subtable_format in GLYPH_READERS:
            found.setdefault((platform, encoding), (subtable_format, cmap[offset:]))
    for preferred in PREFERRED_ENCODINGS:
        if preferred in found:
            return found[preferred]
    raise FontReadError("no Unicode character map in format 4 or 12")


def advance_width(hmtx, horizontal_metric_count, glyph):
    index = min(glyph, horizontal_metric_count - 1)
    return struct.unpack(">H", hmtx[4 * index:4 * index + 2])[0]


def read_font_metrics(path):
    tables = sfnt_tables(Path(path).read_bytes())
    for required in ("head", "OS/2", "hhea", "hmtx", "cmap"):
        if required not in tables:
            raise FontReadError(f"the font has no {required} table")
    units_per_em = struct.unpack(">H", tables["head"][18:20])[0]
    os2 = tables["OS/2"]
    if struct.unpack(">H", os2[0:2])[0] < OS2_FIRST_VERSION_WITH_X_HEIGHT:
        raise FontReadError("the OS/2 table is too old to record the x-height")
    x_height_units = struct.unpack(">h", os2[OS2_X_HEIGHT_OFFSET:OS2_X_HEIGHT_OFFSET + 2])[0]
    horizontal_metric_count = struct.unpack(">H", tables["hhea"][34:36])[0]
    subtable_format, subtable = unicode_subtable(tables["cmap"])
    find_glyph = GLYPH_READERS[subtable_format]
    advances = [advance_width(tables["hmtx"], horizontal_metric_count, glyph)
                for glyph in (find_glyph(subtable, ord(letter)) for letter in LOWERCASE_LETTERS)
                if glyph]
    if not advances:
        raise FontReadError("the font maps no lowercase letters")
    return FontMetrics(x_height_units / units_per_em,
                       sum(advances) / len(advances) / units_per_em)


def font_file_for_family(family):
    if not shutil.which("fc-match"):
        raise FontReadError("fc-match is not installed")
    answer = subprocess.run(["fc-match", "-f", "%{family}\t%{file}", family],
                            capture_output=True, encoding="utf-8", errors="replace", check=False).stdout
    found_families, _, font_file = answer.partition("\t")
    if family.lower() not in [name.strip().lower() for name in found_families.split(",")]:
        raise FontReadError(f"'{family}' is not installed here (fc-match offered "
                            f"'{found_families or 'nothing'}')")
    return font_file


def size_from_config(args):
    try:
        size_text = config_from_args(args).book.get("font_size")
    except ConfigError:
        return None
    return float(str(size_text).removesuffix("pt")) if size_text else None


def self_test():
    fixture_font = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "JetBrainsMono-Regular.subset.ttf"
    metrics = read_font_metrics(fixture_font)
    garamond_like = FontMetrics(x_height=0.400, average_lowercase_advance=0.437)
    checks = [
        ("x-height read from the fixture font", round(metrics.x_height, 3), 0.55),
        ("lowercase advance read from the fixture font", round(metrics.average_lowercase_advance, 3), 0.6),
        ("standard size uses the class baselineskip", default_baselineskip(11), 13.6),
        ("half-point size uses the fontsize package default", round(default_baselineskip(11.5), 2), 13.8),
        ("short measure takes the lowest coefficient", leading_coefficient(30), 1.20),
        ("ideal measure takes the middle coefficient", leading_coefficient(66), 1.35),
        ("small x-height at 11.5pt on a 4.61in block", round(compute_stretch(garamond_like, 11.5, 4.61).stretch, 3), 1.065),
    ]
    failures = [(name, got, expected) for name, got, expected in checks if got != expected]
    for name, got, expected in failures:
        print(f"FAIL  {name}: got {got}, expected {expected}")
    print(f"compute-leading self-test: {len(checks) - len(failures)}/{len(checks)} passed")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    parser.add_argument("--family", help="font family name, as fc-match knows it")
    parser.add_argument("--size", type=float, help="body size in points (default: book.font_size)")
    parser.add_argument("--text-width-in", type=float, help="text block width in inches")
    parser.add_argument("--x-ref", type=float, default=REFERENCE_X_HEIGHT,
                        help=f"reference x-height per em (default {REFERENCE_X_HEIGHT})")
    parser.add_argument("--verbose", action="store_true", help="explain the numbers on stderr")
    parser.add_argument("--self-test", action="store_true", help="run the built-in tests on the bundled font")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    size = args.size or size_from_config(args)
    if not args.family or not size or not args.text_width_in:
        parser.error("--family, --size (or book.font_size) and --text-width-in are required")

    try:
        font_file = font_file_for_family(args.family)
        metrics = read_font_metrics(font_file)
    except (FontReadError, OSError, struct.error) as problem:
        sys.stderr.write(f"compute-leading: {problem}\n")
        return EXIT_TOOL_FAILED

    result = compute_stretch(metrics, size, args.text_width_in, args.x_ref)
    if args.verbose:
        sys.stderr.write(
            f"compute-leading: font={font_file}\n"
            f"  x/em={metrics.x_height:.3f}  avg_adv={metrics.average_lowercase_advance:.3f}em  "
            f"cpl={result.characters_per_line:.1f}\n"
            f"  k={result.coefficient:.3f}  xfactor={result.x_factor:.3f}  "
            f"L={result.leading_points:.2f}pt  D={result.baselineskip}pt  N={result.stretch:.3f}\n")
    print(f"{result.stretch:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
