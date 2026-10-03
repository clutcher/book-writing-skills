#!/usr/bin/env python3
import argparse
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parents[2] / 'lib'))
sys.path.insert(0, str(SCRIPTS))

from back_copy_text import BackCopyError
from book_config import ConfigError, add_config_arguments, config_from_args
from cover_design import DesignError
from cover_loader import build_wrap, design_path_of
from cover_settings import CoverSettingsError, read_cover_settings
from cover_geometry import SPINE_INCHES_PER_PAGE, CoverSizeError, describe
from cover_tools import (ToolError, find_image_tool, find_srgb_profile, find_svg_converter,
                         missing_converter_reason)
from cover_wrap import PANELS, panel_file_name
from kdp_overlay import OVERLAY_OPACITY, template_for
from layout_rules import layout_findings
from text_width import FontFileError

EBOOK_HEIGHT = 2560
EBOOK_JPEG_QUALITY = 95
PRINT_DPI = 300


def main():
    parser = argparse.ArgumentParser(
        description='Make the cover from the book design file (cover.design): SVG for every '
                    'panel, PNG, the ebook cover (PNG and sRGB JPEG, 2560 px tall, no bleed), '
                    'the print PDF and the KDP template overlay (wrap-overlay.png, for looking '
                    'only). The KDP template is downloaded into cover.templates when it is '
                    'missing; with no network that is a note, not a failure. Everything else '
                    'goes to the work output folder. Dry run for the book: --fix also copies '
                    'the shipping files into cover.final.')
    parser.add_argument('--pages', type=int, help='interior page count (default: book.pages, '
                                                  'else counted in the built print PDF)')
    parser.add_argument('--paper', choices=sorted(SPINE_INCHES_PER_PAGE),
                        help='paper type (default: cover.paper)')
    parser.add_argument('--trim', help='trim size, for example 6x9 (default: cover.trim, '
                                       'else the book format)')
    parser.add_argument('--design', help='the design file (default: cover.design)')
    parser.add_argument('--out', help='output folder (default: cover.output, '
                                      'else <work.output>/cover)')
    parser.add_argument('--panel', action='append', choices=PANELS,
                        help='only these panels (repeatable; default: all)')
    parser.add_argument('--svg-only', action='store_true', help='write the SVG files only')
    parser.add_argument('--no-download', action='store_true',
                        help='never download the KDP template; use only the templates already '
                             'in cover.templates')
    parser.add_argument('--fix', action='store_true',
                        help='copy the front, back, ebook and print files into cover.final')
    add_config_arguments(parser)
    args = parser.parse_args()

    try:
        settings = read_cover_settings(config_from_args(args))
        design_path = design_path_of(settings, args.design)
        wrap, notes = build_wrap(settings, design_path, args.pages, args.paper, args.trim)
        out = Path(args.out) if args.out else settings.output
        panels = args.panel or list(PANELS)
        svg_files = {panel: wrap.save(out / 'svg' / panel_file_name(panel), panel)
                     for panel in panels}
    except (ConfigError, CoverSettingsError, CoverSizeError, DesignError, BackCopyError,
            FontFileError) as error:
        print(f'make: {error}', file=sys.stderr)
        return 2

    print(describe(wrap.size))
    print(f'page count from  {settings.page_count_source}')
    print(f'design           {design_path}')
    for note in notes:
        print(f'note             {note}')
    for finding in layout_findings(wrap):
        print(f'note             {finding.finding_class}: {finding.message}')
    for panel, path in svg_files.items():
        print(f'svg              {path}')
    if args.svg_only:
        return 0

    converter = find_svg_converter(settings.render_image, out)
    if converter is None:
        print(f'SKIPPED  PNG, ebook and PDF: {missing_converter_reason(settings.render_image)}')
        return 0

    made = {}
    skipped = []
    try:
        for panel, svg in svg_files.items():
            made[panel] = converter.to_png(svg, out / 'png' / f'{Path(svg).stem}.png')
            print(f'png              {made[panel]}')
        if 'front-trim' in svg_files:
            made['ebook'] = converter.to_png(svg_files['front-trim'], out / 'png' / 'ebook.png',
                                             EBOOK_HEIGHT)
            print(f'ebook png        {made["ebook"]}')
            image_tool = find_image_tool()
            if image_tool is None:
                skipped.append('ebook JPEG: ImageMagick (magick or convert) is not installed')
            else:
                profile = find_srgb_profile(settings.srgb_profile)
                made['ebook_jpeg'] = image_tool.jpeg(made['ebook'], out / 'png' / 'ebook.jpg',
                                                     EBOOK_JPEG_QUALITY, profile)
                print(f'ebook jpeg       {made["ebook_jpeg"]}'
                      + ('' if profile else '  (no sRGB profile file found: set '
                                           'cover.srgb_profile, KDP wants sRGB)'))
        if 'wrap' in svg_files:
            made['print_pdf'] = converter.to_pdf(
                svg_files['wrap'], out / 'pdf' / f'paperback-cover-{wrap.size.page_count}.pdf',
                PRINT_DPI)
            print(f'print pdf        {made["print_pdf"]}')
        if 'wrap' in made:
            overlay_skip = write_overlay(made, wrap.size, settings.templates,
                                         not args.no_download)
            if overlay_skip:
                skipped.append(overlay_skip)
    except ToolError as error:
        print(f'make: {error}', file=sys.stderr)
        return 2
    print(f'renderer         {converter.name}')

    shipping = [('front-trim', 'front'), ('back-trim', 'back'), ('ebook', 'ebook'),
                ('print_pdf', 'print_pdf')]
    for made_name, final_name in shipping:
        if made_name not in made:
            continue
        target = settings.final_file(final_name)
        copies = [(made[made_name], target)]
        if made_name == 'ebook' and 'ebook_jpeg' in made:
            copies.append((made['ebook_jpeg'], target.with_suffix('.jpg')))
        for source, destination in copies:
            if args.fix:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                print(f'shipped          {destination}')
            else:
                print(f'would ship       {destination}  (use --fix)')
    for reason in skipped:
        print(f'SKIPPED  {reason}')
    return 0


def write_overlay(made, size, templates_folder, may_download):
    choice = template_for(size, templates_folder, may_download)
    for note in choice.notes:
        print(f'note             {note}')
    if choice.path is None:
        return 'KDP overlay: no template (see the note above)'
    image_tool = find_image_tool()
    if image_tool is None:
        return 'KDP overlay: ImageMagick (magick or convert) is not installed'
    wrap_png = made['wrap']
    made['overlay'] = image_tool.overlay(wrap_png, choice.path,
                                         wrap_png.with_name(f'{wrap_png.stem}-overlay.png'),
                                         OVERLAY_OPACITY)
    print(f'kdp overlay      {made["overlay"]}  (template {choice.path.name}; look at it, '
          f'never upload it)')
    return None


if __name__ == '__main__':
    sys.exit(main())
