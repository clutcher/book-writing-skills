#!/usr/bin/env python3
import argparse
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parents[2] / 'lib'))
sys.path.insert(0, str(SCRIPTS))

from back_copy_text import BackCopyError
from book_config import ConfigError, add_config_arguments, config_from_args
from check_output import (ADVISORY, DEFECT, INFORMATIONAL, CheckReport, add_output_arguments,
                          tool_failed)
from cover_design import DesignError
from cover_loader import (build_wrap, design_path_of, nominal_pages_if_unknown,
                          report_skipped_for_missing_design)
from cover_settings import CoverSettingsError, read_cover_settings
from cover_geometry import CoverSizeError
from text_width import FontFileError

TOOL = 'font-check'
GENERIC_FAMILIES = {'serif', 'sans-serif', 'monospace', 'cursive', 'fantasy', 'system-ui'}
CSS_TO_FONTCONFIG_WEIGHT = {100: 0, 200: 40, 300: 50, 400: 80, 500: 100, 600: 180, 700: 200,
                            800: 205, 900: 210}
TEXT_TAGS = ('text', 'tspan')
CLASSES = {
    'font-missing': DEFECT,
    'font-weight-substituted': ADVISORY,
    'font-style-substituted': ADVISORY,
    'font-generic-only': ADVISORY,
    'font-found': INFORMATIONAL,
    'geometry-nominal': INFORMATIONAL,
}


def local_tag(element):
    return element.tag.rsplit('}', 1)[-1]


def inherited(element, parents, attribute, default=None):
    while element is not None:
        if attribute in element.attrib:
            return element.attrib[attribute]
        element = parents.get(element)
    return default


def css_weight(value):
    names = {'normal': 400, 'bold': 700}
    if str(value) in names:
        return names[str(value)]
    try:
        return int(round(float(value) / 100.0) * 100)
    except (TypeError, ValueError):
        return 400


def nearest_css_weight(fontconfig_weight):
    return min(CSS_TO_FONTCONFIG_WEIGHT,
               key=lambda weight: abs(CSS_TO_FONTCONFIG_WEIGHT[weight] - fontconfig_weight))


def first_family(family_list):
    for family in family_list.split(','):
        name = family.strip().strip('\'"')
        if name:
            return name
    return ''


def used_fonts(svg_text):
    root = ElementTree.fromstring(svg_text.encode('utf-8'))
    parents = {child: parent for parent in root.iter() for child in parent}
    fonts = {}
    for element in root.iter():
        if local_tag(element) not in TEXT_TAGS:
            continue
        family = inherited(element, parents, 'font-family', '')
        weight = css_weight(inherited(element, parents, 'font-weight', 400))
        style = inherited(element, parents, 'font-style', 'normal')
        key = (family, weight, 'italic' if style in ('italic', 'oblique') else 'normal')
        fonts[key] = fonts.get(key, 0) + 1
    return fonts


def match_font(family, weight, style):
    pattern = (f'{family}:weight={CSS_TO_FONTCONFIG_WEIGHT.get(weight, 80)}'
               f':slant={100 if style == "italic" else 0}')
    result = subprocess.run(['fc-match', '-f', '%{family}\t%{weight}\t%{slant}\t%{file}',
                             pattern], capture_output=True, encoding='utf-8', errors='replace')
    return result.stdout.split('\t') if result.returncode == 0 else None


def weight_range(text):
    numbers = [float(part) for part in re.findall(r'[0-9.]+', text)]
    return (min(numbers), max(numbers)) if numbers else (80.0, 80.0)


def main():
    parser = argparse.ArgumentParser(
        description='Check that every font the cover asks for is installed, in the weight and '
                    'style it asks for. A missing font is silently replaced when the cover is '
                    'rendered, so the PNG and PDF would not show the design. Nothing is written.')
    parser.add_argument('--design', help='the design file (default: cover.design)')
    parser.add_argument('--pages', type=int, help='interior page count')
    add_config_arguments(parser)
    add_output_arguments(parser)
    args = parser.parse_args()
    report = CheckReport(TOOL, CLASSES)
    try:
        settings = read_cover_settings(config_from_args(args))
        skipped = report_skipped_for_missing_design(report, settings, args.design, args.format)
        if skipped is not None:
            return skipped
        pages, nominal_note = nominal_pages_if_unknown(settings, args.pages)
        wrap, _notes = build_wrap(settings, design_path_of(settings, args.design), pages)
        fonts = used_fonts(wrap.render('wrap'))
    except (ConfigError, CoverSettingsError, CoverSizeError, DesignError, BackCopyError,
            FontFileError) as error:
        return tool_failed(str(error), TOOL)
    if nominal_note:
        report.add('page-count', 'geometry-nominal', nominal_note)
    if not shutil.which('fc-match'):
        report.skip('fc-match (fontconfig) is not installed')
        return report.emit(args.format)
    for (family_list, weight, style), count in sorted(fonts.items()):
        wanted = first_family(family_list)
        key = f'{wanted} {weight} {style}'
        if not wanted or wanted.lower() in GENERIC_FAMILIES:
            report.add(key, 'font-generic-only',
                       f'only a generic family ({family_list or "none"}) is named, so the '
                       f'renderer picks the face; {count} text element(s)')
            continue
        matched = match_font(wanted, weight, style)
        if not matched or len(matched) < 4:
            report.add(key, 'font-missing', f'fontconfig could not answer for {wanted}')
            continue
        matched_family, matched_weight, matched_slant, matched_file = matched[:4]
        if wanted.lower() not in matched_family.lower():
            report.add(key, 'font-missing',
                       f'not installed; the renderer would use {matched_family.split(",")[0]} '
                       f'({Path(matched_file).name}) for {count} text element(s)')
            continue
        low, high = weight_range(matched_weight)
        wanted_weight = CSS_TO_FONTCONFIG_WEIGHT.get(weight, 80)
        if not (low - 1 <= wanted_weight <= high + 1):
            report.add(key, 'font-weight-substituted',
                       f'weight {weight} asked, {nearest_css_weight(low)} found '
                       f'({Path(matched_file).name})')
            continue
        slant_low, _ = weight_range(matched_slant)
        if (style == 'italic') != (slant_low > 0):
            report.add(key, 'font-style-substituted',
                       f'{style} asked, {Path(matched_file).name} found; the renderer may '
                       f'slant the roman face')
            continue
        report.add(key, 'font-found', f'{Path(matched_file).name}, {count} text element(s)')
    return report.emit(args.format)


if __name__ == '__main__':
    sys.exit(main())
