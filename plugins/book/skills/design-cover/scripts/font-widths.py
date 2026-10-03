#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parents[2] / 'lib'))
sys.path.insert(0, str(SCRIPTS))

from book_config import ConfigError, add_config_arguments, config_from_args
from text_width import DEFAULT_CHARACTERS, FACE_NAMES, BodyWidths, FontFile, FontFileError

FONTCONFIG_WEIGHTS = {'regular': 80, 'bold': 200, 'italic': 80}
FONTCONFIG_SLANTS = {'regular': 0, 'bold': 0, 'italic': 100}
WIDTHS_FOLDER = 'font-widths'


def find_font_file(family, face):
    if not shutil.which('fc-match'):
        raise FontFileError('fc-match is not installed; pass the font files with '
                            '--regular, --bold and --italic')
    pattern = f'{family}:weight={FONTCONFIG_WEIGHTS[face]}:slant={FONTCONFIG_SLANTS[face]}'
    result = subprocess.run(['fc-match', '-f', '%{family}\t%{file}', pattern],
                            capture_output=True, encoding='utf-8', errors='replace')
    matched_family, _, file_name = result.stdout.partition('\t')
    if result.returncode != 0 or family.lower() not in matched_family.lower():
        raise FontFileError(f"the font '{family}' ({face}) is not installed; fontconfig "
                            f"offered '{matched_family or 'nothing'}'")
    return Path(file_name)


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-') or 'body-font'


def main():
    parser = argparse.ArgumentParser(
        description='Write the advance widths of the back-cover body font to a JSON table. '
                    'The back-cover text is broken into lines with this table, so it must come '
                    'from the font the cover renders in. Dry run by default: prints what it '
                    'would write; --fix writes the file.')
    parser.add_argument('--family', help='font family name as fontconfig knows it, '
                                          "for example 'Noto Sans'")
    parser.add_argument('--regular', help='font file for plain text (overrides --family)')
    parser.add_argument('--bold', help='font file for bold text (overrides --family)')
    parser.add_argument('--italic', help='font file for italic text (overrides --family)')
    parser.add_argument('--out', help='where to write the table (default: '
                                      '<cover.dir>/font-widths/<family>.json)')
    parser.add_argument('--characters', default='',
                        help='extra characters to measure; the printable ASCII set, curly '
                             'quotes, dashes, bullet and every character of the back-cover '
                             'text are always measured')
    parser.add_argument('--fix', action='store_true', help='write the table')
    add_config_arguments(parser)
    args = parser.parse_args()

    try:
        config = config_from_args(args)
        files = {}
        for face in FACE_NAMES:
            given = getattr(args, face)
            if given:
                files[face] = Path(given)
            elif args.family:
                files[face] = find_font_file(args.family, face)
            else:
                raise FontFileError(f'no font file for the {face} face: pass --family or '
                                    f'--{face}')
        characters = DEFAULT_CHARACTERS + args.characters
        back_cover = config.sales_text.back_cover
        if back_cover and back_cover.is_file():
            characters += back_cover.read_text(encoding='utf-8')
        characters = ''.join(sorted(set(characters) - set('\n\r\t')))
        fonts = {face: FontFile.open(path) for face, path in files.items()}
        widths = BodyWidths({face: font.face_widths(characters) for face, font in fonts.items()},
                            args.family or files['regular'].stem,
                            fonts['regular'].bullet_ink_centre_em())
    except (ConfigError, FontFileError) as error:
        print(f'font-widths: {error}', file=sys.stderr)
        return 2

    label = widths.font
    out = Path(args.out) if args.out else (config.cover.dir / WIDTHS_FOLDER / f'{slug(label)}.json')
    data = widths.as_dict()
    data['files'] = {face: path.name for face, path in files.items()}
    text = json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    for face in FACE_NAMES:
        face_widths = widths.faces[face]
        print(f'{face:8} {files[face].name}: {len(face_widths.widths)} characters, '
              f'average letter {face_widths.default} em')
    print(f'bullet   ink centre {widths.bullet_ink_centre_em} em above the baseline')
    if args.fix:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding='utf-8')
        print(f'written  {out}')
    else:
        print(f'dry run  would write {out} (use --fix)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
