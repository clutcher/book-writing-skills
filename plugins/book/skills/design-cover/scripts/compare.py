#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parents[2] / 'lib'))
sys.path.insert(0, str(SCRIPTS))

from book_config import ConfigError, add_config_arguments, config_from_args
from check_output import ADVISORY, INFORMATIONAL, CheckReport, add_output_arguments, tool_failed
from cover_settings import CoverSettingsError, read_cover_settings
from cover_tools import ToolError, find_image_tool, png_size

TOOL = 'compare'
THUMBNAIL_HEIGHTS = (250, 180, 120)
ONION_OPACITY = 0.5
CLASSES = {
    'pixels-differ': INFORMATIONAL,
    'pixels-same': INFORMATIONAL,
    'size-differs': ADVISORY,
    'image-written': INFORMATIONAL,
    'nothing-shipped-yet': INFORMATIONAL,
}


def compare_pair(tool, old, new, folder, report, labels):
    folder.mkdir(parents=True, exist_ok=True)
    old_size, new_size = png_size(old), png_size(new)
    if old_size != new_size:
        report.add(new.name, 'size-differs',
                   f'{old.name} is {old_size[0]} x {old_size[1]}, {new.name} is '
                   f'{new_size[0]} x {new_size[1]}; the overlay stretches the old one to fit')
    else:
        differing = tool.difference(old, new, folder / 'difference.png')
        total = new_size[0] * new_size[1]
        report.add(new.name, 'pixels-same' if differing == 0 else 'pixels-differ',
                   f'{differing} of {total} pixels differ ({100.0 * differing / total:.3f}%)'
                   + ('' if differing == 0 else f'; red marks them in {folder / "difference.png"}'))
    outputs = [
        tool.onion(new, old, folder / 'overlay.png', ONION_OPACITY),
        tool.side_by_side([old, new], labels, folder / 'side-by-side.png', new_size[1]),
    ]
    for height in THUMBNAIL_HEIGHTS:
        outputs.append(tool.side_by_side([old, new], [f'{labels[0]} {height}px',
                                                      f'{labels[1]} {height}px'],
                                         folder / f'thumbnails-{height}.png', height))
    for output in outputs:
        report.add(output.name, 'image-written', str(output))


def thumbnails_alone(tool, new, folder, report):
    folder.mkdir(parents=True, exist_ok=True)
    for height in THUMBNAIL_HEIGHTS:
        output = tool.side_by_side([new], [f'new {height}px'],
                                   folder / f'thumbnails-{height}.png', height)
        report.add(output.name, 'image-written', str(output))


def main():
    parser = argparse.ArgumentParser(
        description='Compare two cover images: the new one with the old one laid over it half '
                    'transparent, side by side at full size and at shop thumbnail sizes '
                    '(250, 180, 120 px tall), and a count of the pixels that differ. With '
                    '--grid, put any number of covers side by side with labels. With no files, '
                    'compares the shipped front (cover.final) with the one make.py just made; '
                    'before the first ship it writes the thumbnails of the new front alone.')
    parser.add_argument('old', nargs='?', help='the old image (PNG)')
    parser.add_argument('new', nargs='?', help='the new image (PNG)')
    parser.add_argument('--grid', nargs='+', metavar='PNG', help='several covers for one grid')
    parser.add_argument('--labels', nargs='+', help='labels, one per image')
    parser.add_argument('--height', type=int, default=710, help='grid cell height (default 710)')
    parser.add_argument('--out', help='output folder (default: <cover output>/compare)')
    add_config_arguments(parser)
    add_output_arguments(parser)
    args = parser.parse_args()
    report = CheckReport(TOOL, CLASSES)

    try:
        settings = read_cover_settings(config_from_args(args, targets=[args.old, *(args.grid or [])]))
        out = Path(args.out) if args.out else settings.output / 'compare'
        if args.grid:
            images = [Path(path) for path in args.grid]
        else:
            old = Path(args.old) if args.old else settings.final_file('front')
            new = Path(args.new) if args.new else settings.output / 'png' / 'front-trim.png'
            images = [old, new]
    except (ConfigError, CoverSettingsError) as error:
        return tool_failed(str(error), TOOL)
    first_cover = not args.grid and not args.old and not images[0].is_file()
    if first_cover:
        images = [images[1]]
    missing = [str(path) for path in images if not path.is_file()]
    if missing:
        return tool_failed(f'no image at {", ".join(missing)}', TOOL)
    tool = find_image_tool()
    if tool is None:
        report.skip('ImageMagick (magick, or convert and compare) is not installed')
        return report.emit(args.format)
    if first_cover:
        report.add(old.name, 'nothing-shipped-yet',
                   f'no shipped front at {old}, so there is nothing to compare with; the '
                   f'thumbnails show the new front alone')
        try:
            thumbnails_alone(tool, images[0], out / images[0].stem, report)
        except ToolError as error:
            return tool_failed(str(error), TOOL)
        return report.emit(args.format)
    labels = args.labels or ([path.stem for path in images] if args.grid else ['old', 'new'])
    if len(labels) != len(images):
        return tool_failed('give one label per image', TOOL)
    try:
        if args.grid:
            out.mkdir(parents=True, exist_ok=True)
            grid = tool.side_by_side(images, labels, out / 'grid.png', args.height)
            report.add(grid.name, 'image-written', str(grid))
        else:
            compare_pair(tool, images[0], images[1], out / images[1].stem, report, labels)
    except ToolError as error:
        return tool_failed(str(error), TOOL)
    return report.emit(args.format)


if __name__ == '__main__':
    sys.exit(main())
