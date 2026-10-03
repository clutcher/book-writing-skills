#!/usr/bin/env python3
import argparse
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
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
from cover_tools import find_srgb_profile
from text_width import FontFileError

TOOL = 'color-check'
HEX = re.compile(r'^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$')
RGB = re.compile(r'^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$')
STYLE_PART = re.compile(r'(?:^|;)\s*(fill|stroke)\s*:\s*([^;]+)')
COLOR_NAME_PARTS = ('COLOR', 'COLOUR')
COLOR_ATTRIBUTES = ('fill', 'stroke', 'stop-color')
TEXT_TAGS = ('text', 'tspan')
POINTS_PER_INCH = 72.0
CONTRAST_LARGE = 3.0
CONTRAST_NORMAL = 4.5
LARGE_TEXT_PT = 18.0
LARGE_BOLD_TEXT_PT = 14.0
BOLD_WEIGHT = 700
DEFAULT_WEIGHT = 400
VANISHING_TINT = 5.0
TYPE = 'type'
ARTWORK = 'artwork'

CLASSES = {
    'type-contrast-low': DEFECT,
    'cmyk-over-limit': DEFECT,
    'cmyk-over-limit-profile': DEFECT,
    'cmyk-over-limit-one-mode': ADVISORY,
    'tint-may-vanish': ADVISORY,
    'type-color': INFORMATIONAL,
    'artwork-color': INFORMATIONAL,
    'not-drawn': INFORMATIONAL,
    'geometry-nominal': INFORMATIONAL,
    'icc-conversion-skipped': ADVISORY,
}


@dataclass
class Use:
    role: str
    tag: str
    emitted: tuple
    size_px: float = None
    weight: int = None
    ground: tuple = None
    element_index: int = None


@dataclass
class ColorConstant:
    name: str
    path: tuple
    value: object
    uses: list = field(default_factory=list)

    @property
    def label(self):
        index = ''.join(f'[{part}]' for part in self.path)
        return f'{self.name}{index}'


def parse_color(value):
    if is_rgb_tuple(value):
        return tuple(value)
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if HEX.match(value):
        digits = value[1:]
        if len(digits) == 3:
            digits = ''.join(digit * 2 for digit in digits)
        return tuple(int(digits[index:index + 2], 16) for index in (0, 2, 4))
    match = RGB.match(value)
    if match:
        return tuple(int(group) for group in match.groups())
    return None


def is_rgb_tuple(value):
    return (isinstance(value, tuple) and len(value) == 3
            and all(isinstance(part, int) and 0 <= part <= 255 for part in value))


def to_hex(rgb):
    return '#%02X%02X%02X' % rgb


def relative_luminance(rgb):
    channels = []
    for raw in rgb:
        value = raw / 255.0
        channels.append(value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(first, second):
    lighter, darker = sorted((relative_luminance(first), relative_luminance(second)),
                             reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def naive_cmyk(rgb):
    red, green, blue = (channel / 255.0 for channel in rgb)
    black = 1.0 - max(red, green, blue)
    if black >= 1.0:
        return (0.0, 0.0, 0.0, 100.0)
    rest = 1.0 - black
    return ((1.0 - red - black) / rest * 100.0, (1.0 - green - black) / rest * 100.0,
            (1.0 - blue - black) / rest * 100.0, black * 100.0)


def profile_cmyk(rgb, srgb_profile, cmyk_profile, black_point_compensation):
    command = ['magick' if shutil.which('magick') else 'convert', f'xc:{to_hex(rgb)}',
               '-profile', str(srgb_profile)]
    if black_point_compensation:
        command.append('-black-point-compensation')
    command += ['-intent', 'relative', '-profile', str(cmyk_profile), '-format',
                '%[fx:100*u.c] %[fx:100*u.m] %[fx:100*u.y] %[fx:100*u.k]', 'info:']
    result = subprocess.run(command, capture_output=True, encoding='utf-8', errors='replace')
    if result.returncode != 0:
        return None
    return tuple(float(part) for part in result.stdout.split())


def is_large_text(point_size, weight):
    if point_size is None:
        return False
    if point_size >= LARGE_TEXT_PT:
        return True
    return weight is not None and weight >= BOLD_WEIGHT and point_size >= LARGE_BOLD_TEXT_PT


def color_constants(design_class):
    found = []
    seen = set()
    for holder in design_class.__mro__:
        if holder is object:
            continue
        for name, value in vars(holder).items():
            if not name.isupper() or name in seen:
                continue
            seen.add(name)
            accept_tuples = any(part in name for part in COLOR_NAME_PARTS)
            for path, color in hex_values(value, accept_tuples=accept_tuples):
                found.append(ColorConstant(name, path, color))
    return found


def hex_values(value, path=(), accept_tuples=False):
    if isinstance(value, str):
        return [(path, value)] if HEX.match(value.strip()) else []
    if accept_tuples and is_rgb_tuple(value):
        return [(path, value)]
    if isinstance(value, (list, tuple)):
        values = []
        for index, item in enumerate(value):
            values.extend(hex_values(item, path + (index,), accept_tuples))
        return values
    if isinstance(value, dict):
        values = []
        for key, item in value.items():
            values.extend(hex_values(item, path + (key,), accept_tuples))
        return values
    return []


def replace_at(value, path, new):
    if not path:
        return new
    head, rest = path[0], path[1:]
    if isinstance(value, dict):
        copy = dict(value)
        copy[head] = replace_at(value[head], rest, new)
        return copy
    items = list(value)
    items[head] = replace_at(value[head], rest, new)
    return tuple(items) if isinstance(value, tuple) else items


def opposite(value):
    rgb = parse_color(value)
    flipped = tuple(255 - channel for channel in rgb)
    if flipped == rgb:
        flipped = (rgb[0] ^ 0x80, rgb[1], rgb[2])
    return flipped if is_rgb_tuple(value) else to_hex(flipped)


def own_color_value(element, attribute):
    if attribute in element.attrib:
        return element.attrib[attribute]
    for name, value in STYLE_PART.findall(element.attrib.get('style', '')):
        if name == attribute:
            return value.strip()
    return None


def parse_svg(text):
    root = ElementTree.fromstring(text.encode('utf-8'))
    parents = {child: parent for parent in root.iter() for child in parent}
    return root, parents


def local_tag(element):
    return element.tag.rsplit('}', 1)[-1]


def inherited(element, parents, attribute):
    while element is not None:
        if attribute in element.attrib:
            return element.attrib[attribute]
        element = parents.get(element)
    return None


def number(text):
    try:
        return float(str(text).replace('px', ''))
    except (TypeError, ValueError):
        return None


def trace_uses(wrap, constant, baseline_elements, parents, backdrop):
    design = wrap.design
    original = getattr(design, constant.name)
    setattr(design, constant.name, replace_at(original, constant.path, opposite(constant.value)))
    try:
        changed_root, _ = parse_svg(wrap.render('wrap'))
    finally:
        if constant.name in vars(design):
            delattr(design, constant.name)
    changed_elements = list(changed_root.iter())
    if len(changed_elements) != len(baseline_elements):
        return None
    uses = []
    for index, (before, after) in enumerate(zip(baseline_elements, changed_elements)):
        for attribute in COLOR_ATTRIBUTES:
            if own_color_value(before, attribute) == own_color_value(after, attribute):
                continue
            emitted = parse_color(own_color_value(before, attribute))
            if emitted is None:
                continue
            tag = local_tag(before)
            role = TYPE if tag in TEXT_TAGS and attribute in ('fill', 'stroke') else ARTWORK
            if role == TYPE:
                uses.append(type_use(before, parents, emitted, backdrop, index))
            else:
                uses.append(Use(role, tag, emitted, element_index=index))
    return uses


def type_use(element, parents, emitted, backdrop, index):
    size = number(inherited(element, parents, 'font-size'))
    weight = number(inherited(element, parents, 'font-weight'))
    for child in element.iter():
        if child is element:
            continue
        child_size = number(inherited(child, parents, 'font-size'))
        if child_size is not None and (size is None or child_size < size):
            size = child_size
    return Use(TYPE, local_tag(element), emitted, size,
               int(weight) if weight is not None else DEFAULT_WEIGHT,
               backdrop.behind(element, parents), index)


def untraced_type_uses(baseline_elements, parents, backdrop, claimed):
    by_color = {}
    for index, element in enumerate(baseline_elements):
        if index in claimed or local_tag(element) not in TEXT_TAGS:
            continue
        for attribute in ('fill', 'stroke'):
            emitted = parse_color(own_color_value(element, attribute))
            if emitted is None:
                continue
            by_color.setdefault(emitted, []).append(
                type_use(element, parents, emitted, backdrop, index))
    return by_color


def worst_type_use(type_uses, dpi):
    worst = None
    for use in type_uses:
        point_size = use.size_px * POINTS_PER_INCH / dpi if use.size_px is not None else None
        threshold = CONTRAST_LARGE if is_large_text(point_size, use.weight) else CONTRAST_NORMAL
        ratio = contrast_ratio(use.emitted, use.ground)
        margin = ratio / threshold
        if worst is None or margin < worst[0]:
            worst = (margin, ratio, threshold, point_size, use)
    return worst[1:]


def grade_type(report, key, type_uses, dpi, cmyk_text, source):
    ratio, threshold, point_size, use = worst_type_use(type_uses, dpi)
    size_text = f'{point_size:.1f}pt' if point_size is not None else 'size unknown'
    verdict = (f'{source}{ratio:.2f}:1 on {to_hex(use.ground)} at {size_text}, weight '
               f'{use.weight}, needs {threshold:.1f}:1 ({len(type_uses)} type element(s)); '
               f'{cmyk_text}')
    report.add(key, 'type-contrast-low' if ratio < threshold else 'type-color', verdict)


def cmyk_text_of(rgb):
    return 'C%.0f M%.0f Y%.0f K%.0f' % naive_cmyk(rgb)


TRANSLATE = re.compile(r'translate\(\s*([-0-9.]+)[\s,]+([-0-9.]+)\s*\)')


class Backdrop:
    def __init__(self, root, background):
        self.background = parse_color(background)
        self.order = {}
        self.offsets = {}
        self.rects = []
        self._walk(root, 0.0, 0.0)

    def _walk(self, element, offset_x, offset_y):
        self.order[element] = len(self.order)
        tag = local_tag(element)
        if tag == 'svg' and self.order[element] > 0:
            offset_x += number(element.attrib.get('x')) or 0.0
            offset_y += number(element.attrib.get('y')) or 0.0
        move = TRANSLATE.search(element.attrib.get('transform', ''))
        if move:
            offset_x += float(move.group(1))
            offset_y += float(move.group(2))
        self.offsets[element] = (offset_x, offset_y)
        if tag == 'rect':
            fill = parse_color(element.attrib.get('fill'))
            left = number(element.attrib.get('x')) or 0.0
            top = number(element.attrib.get('y')) or 0.0
            width = number(element.attrib.get('width')) or 0.0
            height = number(element.attrib.get('height')) or 0.0
            if fill is not None:
                self.rects.append((self.order[element], fill, left + offset_x, top + offset_y,
                                   width, height))
        for child in element:
            self._walk(child, offset_x, offset_y)

    def behind(self, element, parents):
        anchor = element
        while anchor is not None and 'x' not in anchor.attrib:
            anchor = parents.get(anchor)
        if anchor is None:
            return self.background
        offset_x, offset_y = self.offsets[anchor]
        x = (number(anchor.attrib.get('x')) or 0.0) + offset_x
        y = (number(anchor.attrib.get('y')) or 0.0) + offset_y
        color = self.background
        for order, fill, left, top, width, height in self.rects:
            if order < self.order[element] and left <= x <= left + width and top <= y <= top + height:
                color = fill
        return color


def main():
    parser = argparse.ArgumentParser(
        description='Check the colors of the cover design (cover.design): which color constants '
                    'are type and which are artwork (found by changing each one and seeing what '
                    'moves in the rendered cover), WCAG AA contrast for all type at its printed '
                    'size, including type colors written without a constant, and the CMYK '
                    'single-channel limit (cover.cmyk_limit, default 88%%). Nothing is written.')
    parser.add_argument('--design', help='the design file (default: cover.design)')
    parser.add_argument('--icc', help='CMYK ICC profile for a real conversion, for example a '
                                      'SWOP coated profile (default: cover.icc); needs ImageMagick')
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
        baseline_text = wrap.render('wrap')
    except (ConfigError, CoverSettingsError, CoverSizeError, DesignError, BackCopyError,
            FontFileError) as error:
        return tool_failed(str(error), TOOL)

    limit = settings.cmyk_limit
    cmyk_profile = Path(args.icc) if args.icc else settings.icc
    srgb_profile = find_srgb_profile(settings.srgb_profile)
    profile_skip = None
    if cmyk_profile:
        if not (shutil.which('magick') or shutil.which('convert')):
            profile_skip = 'ICC conversion: ImageMagick is not installed'
        elif not cmyk_profile.is_file():
            profile_skip = f'ICC conversion: no profile file at {cmyk_profile}'
        elif srgb_profile is None:
            profile_skip = 'ICC conversion: no sRGB profile file found (set cover.srgb_profile)'

    baseline_root, parents = parse_svg(baseline_text)
    baseline_elements = list(baseline_root.iter())
    backdrop = Backdrop(baseline_root, wrap.design.BACKGROUND)
    if nominal_note:
        report.add('page-count', 'geometry-nominal', nominal_note)
    claimed = set()
    for constant in color_constants(type(wrap.design)):
        uses = trace_uses(wrap, constant, baseline_elements, parents, backdrop)
        rgb = parse_color(constant.value)
        key = f'{constant.label}={to_hex(rgb)}'
        cmyk = naive_cmyk(rgb)
        cmyk_text = cmyk_text_of(rgb)
        if max(cmyk) > limit:
            report.add(key, 'cmyk-over-limit',
                       f'naive CMYK {cmyk_text}: a channel is over {limit:.0f}%')
        if 0 < max(cmyk) < VANISHING_TINT:
            report.add(key, 'tint-may-vanish',
                       f'naive CMYK {cmyk_text}: every channel is under {VANISHING_TINT:.0f}%, '
                       f'so it may print as white or band')
        if cmyk_profile and not profile_skip:
            modes = {}
            for compensation in (False, True):
                converted = profile_cmyk(rgb, srgb_profile, cmyk_profile, compensation)
                if converted:
                    modes['with' if compensation else 'without'] = converted
            over = [mode for mode, values in modes.items() if max(values) > limit]
            detail = '; '.join(f'{mode} black point compensation C%.0f M%.0f Y%.0f K%.0f'
                               % values for mode, values in modes.items())
            if len(over) == len(modes) and over:
                report.add(key, 'cmyk-over-limit-profile', f'{cmyk_profile.name}: {detail}')
            elif over:
                report.add(key, 'cmyk-over-limit-one-mode',
                           f'{cmyk_profile.name}: over {limit:.0f}% only {over[0]} black point '
                           f'compensation ({detail}); the printer decides which, so check it '
                           f'on a printed proof')
        if uses is None:
            report.add(key, 'artwork-color', f'changing it changed the shape of the cover, '
                                              f'so its role could not be traced; {cmyk_text}')
            continue
        if not uses:
            report.add(key, 'not-drawn', f'nothing on the cover changes with it; {cmyk_text}')
            continue
        claimed.update(use.element_index for use in uses)
        type_uses = [use for use in uses if use.role == TYPE]
        if not type_uses:
            report.add(key, 'artwork-color',
                       f'{len(uses)} artwork element(s): {", ".join(sorted({u.tag for u in uses}))}'
                       f'; {cmyk_text}')
            continue
        grade_type(report, key, type_uses, wrap.dpi, cmyk_text, '')
    untraced = untraced_type_uses(baseline_elements, parents, backdrop, claimed)
    for rgb, type_uses in sorted(untraced.items()):
        key = f'untraced:{to_hex(rgb)}'
        if max(naive_cmyk(rgb)) > limit:
            report.add(key, 'cmyk-over-limit', f'naive CMYK {cmyk_text_of(rgb)}: a channel is '
                                               f'over {limit:.0f}%')
        grade_type(report, key, type_uses, wrap.dpi, cmyk_text_of(rgb),
                   'type color written in the design without a named constant: ')
    if profile_skip:
        report.add('icc', 'icc-conversion-skipped', profile_skip)
    return report.emit(args.format)


if __name__ == '__main__':
    sys.exit(main())
