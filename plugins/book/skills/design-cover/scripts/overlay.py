#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parents[2] / 'lib'))
sys.path.insert(0, str(SCRIPTS))

from book_config import ConfigError, add_config_arguments, config_from_args
from check_output import (ADVISORY, DEFECT, INFORMATIONAL, CheckReport, add_output_arguments,
                          tool_failed)
from cover_settings import CoverSettingsError, PageCountUnknown, read_cover_settings
from cover_geometry import SPINE_INCHES_PER_PAGE, CoverSizeError
from cover_tools import ToolError, find_image_tool, png_size
from kdp_download import (NEW, REPLACED, NetworkMissingError, TemplateAnswerError,
                          TemplateRequest, fetch_templates)
from kdp_overlay import (FETCH_COMMAND, OVERLAY_OPACITY, TEMPLATE_NAME, choose_template,
                         paper_from_name, read_templates)

TOOL = 'overlay'
CLASSES = {
    'art-size-wrong': DEFECT,
    'template-size-wrong': DEFECT,
    'template-trim-differs': DEFECT,
    'template-paper-differs': DEFECT,
    'template-nearest': ADVISORY,
    'overlay-written': INFORMATIONAL,
    'overlay-image-skipped': INFORMATIONAL,
    'template-fetched': INFORMATIONAL,
    'template-fetch-skipped': INFORMATIONAL,
}


def main():
    parser = argparse.ArgumentParser(
        description='Check the wrap against the KDP cover template for this page count and '
                    'write an overlay image (template at 55%% over the art). The overlay is for '
                    'looking only: never upload it. kdp-template.py --fix downloads the '
                    'template into cover.templates; --fetch here does the same first.')
    parser.add_argument('--art', help='the wrap PNG (default: <cover output>/png/wrap.png)')
    parser.add_argument('--template', help='one KDP template PNG (default: chosen by page '
                                           'count from cover.templates)')
    parser.add_argument('--templates', help='folder of KDP template PNGs '
                                            '(default: cover.templates)')
    parser.add_argument('--out', help='overlay image (default: next to the art, -overlay.png)')
    parser.add_argument('--opacity', type=float, default=OVERLAY_OPACITY,
                        help='template opacity (default 0.55)')
    parser.add_argument('--pages', type=int, help='interior page count')
    parser.add_argument('--paper', choices=sorted(SPINE_INCHES_PER_PAGE), help='paper type')
    parser.add_argument('--trim', help='trim size, for example 6x9')
    parser.add_argument('--fetch', action='store_true',
                        help='first download the KDP template for this trim, page count and '
                             'paper into the templates folder (writes files; needs the network)')
    add_config_arguments(parser)
    add_output_arguments(parser)
    args = parser.parse_args()
    report = CheckReport(TOOL, CLASSES)

    try:
        settings = read_cover_settings(config_from_args(args))
        size = settings.cover_size(args.pages, args.paper, args.trim)
    except PageCountUnknown as reason:
        report.skip(str(reason))
        return report.emit(args.format)
    except (ConfigError, CoverSettingsError, CoverSizeError) as error:
        return tool_failed(str(error), TOOL)

    art = Path(args.art) if args.art else settings.output / 'png' / 'wrap.png'
    if args.art and not art.is_file():
        return tool_failed(f'no wrap image at {art}: run make.py first', TOOL)
    if not art.is_file():
        report.skip(f'no rendered cover yet ({art} not found): run design-cover make first')
        return report.emit(args.format)
    art_width, art_height = png_size(art)
    if (art_width, art_height) != (size.width_px, size.height_px):
        report.add(art.name, 'art-size-wrong',
                   f'the art is {art_width} x {art_height} px but {size.page_count} pages on '
                   f'{size.paper} paper need {size.width_px} x {size.height_px} px: make it again')

    if args.template:
        template = Path(args.template)
        match = TEMPLATE_NAME.match(template.name)
        entry = (int(match.group('pages')) if match else size.page_count, template, match)
        exact = entry[0] == size.page_count
    else:
        folder = Path(args.templates) if args.templates else settings.templates
        if args.fetch:
            template_request = TemplateRequest(size.trim_width_in, size.trim_height_in,
                                               size.page_count, size.paper)
            try:
                for target, state in fetch_templates(template_request, folder):
                    if state in (NEW, REPLACED):
                        report.add(target.name, 'template-fetched', f'{target} ({state})')
            except TemplateAnswerError as error:
                return tool_failed(f'{error}. {template_request.manual_way(folder)}', TOOL)
            except NetworkMissingError as error:
                report.add('fetch', 'template-fetch-skipped',
                           f'{error}: checked against the templates already in {folder}')
        templates = read_templates(folder)
        if not templates:
            report.skip(f'no KDP template PNG in {folder}: download the paperback template for '
                        f'{size.page_count} pages with {FETCH_COMMAND} (or overlay.py --fetch), '
                        f'or by hand from the KDP cover calculator')
            return report.emit(args.format)
        entry, exact = choose_template(templates, size.page_count)
    template_pages, template, match = entry
    if not exact:
        report.add(template.name, 'template-nearest',
                   f'no template for {size.page_count} pages; using the {template_pages}-page '
                   f'one, so the spine guides are off by the page difference; '
                   f'{FETCH_COMMAND} downloads the right one')
    if match:
        template_trim = (float(match.group('width')), float(match.group('height')))
        if (abs(template_trim[0] - size.trim_width_in) > 0.005
                or abs(template_trim[1] - size.trim_height_in) > 0.005):
            report.add(template.name, 'template-trim-differs',
                       f'template trim {template_trim[0]} x {template_trim[1]} in, book trim '
                       f'{size.trim_width_in} x {size.trim_height_in} in')
        template_paper = paper_from_name(match.group('paper'))
        if template_paper and template_paper != size.paper:
            report.add(template.name, 'template-paper-differs',
                       f'template paper {template_paper}, book paper {size.paper}')
    template_width, template_height = png_size(template)
    scale = max(1, round(template_width / size.width_px))
    if exact and (abs(template_width - size.width_px * scale) > scale
                  or abs(template_height - size.height_px * scale) > scale):
        report.add(template.name, 'template-size-wrong',
                   f'template {template_width} x {template_height} px is not {scale} x the '
                   f'derived {size.width_px} x {size.height_px} px (1 px allowed): check '
                   f'trim, paper and page count')

    image_tool = find_image_tool()
    if image_tool is None:
        report.add(art.name, 'overlay-image-skipped',
                   'the size checks ran, but the overlay image was not written: ImageMagick '
                   '(magick or convert) is not installed')
        return report.emit(args.format)
    out = Path(args.out) if args.out else art.with_name(f'{art.stem}-overlay.png')
    try:
        image_tool.overlay(art, template, out, args.opacity)
    except ToolError as error:
        return tool_failed(str(error), TOOL)
    report.add(out.name, 'overlay-written', f'{out} (look at it; never upload it)')
    return report.emit(args.format)


if __name__ == '__main__':
    sys.exit(main())
