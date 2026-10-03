#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parents[2] / 'lib'))
sys.path.insert(0, str(SCRIPTS))

from back_copy_text import LINE_BREAK, BackCopyError, read_back_copy
from book_config import ConfigError, add_config_arguments, config_from_args


def main():
    parser = argparse.ArgumentParser(
        description='Show how the cover reads the back-cover text file (sales_text.back_cover): '
                    'one line per block with its kind. Nothing is written.')
    parser.add_argument('file', nargs='?', help='a back-cover markdown file '
                                                '(default: sales_text.back_cover)')
    parser.add_argument('--json', action='store_true', help='print the blocks as JSON')
    add_config_arguments(parser)
    args = parser.parse_args()
    try:
        path = Path(args.file) if args.file else config_from_args(args).sales_text.back_cover
        if path is None:
            raise BackCopyError('no back-cover file: set sales_text.back_cover in book.yaml')
        blocks = read_back_copy(path)
    except (ConfigError, BackCopyError) as error:
        print(f'back-copy: {error}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(blocks, indent=1, ensure_ascii=False))
        return 0
    for kind, content in blocks:
        if isinstance(content, (str, int)):
            print(f'{kind:22} {content}')
        else:
            shown = ' '.join('|' if style == LINE_BREAK else f'[{style}] {text.strip()}'
                             for style, text in content)
            print(f'{kind:22} {shown}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
