#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parents[2] / 'lib'))
sys.path.insert(0, str(SCRIPTS))

from book_config import ConfigError, add_config_arguments, config_from_args
from cover_settings import CoverSettingsError, read_cover_settings
from cover_geometry import SPINE_INCHES_PER_PAGE, CoverSizeError, describe


def main():
    parser = argparse.ArgumentParser(
        description='Print the paperback cover size: spine width from the page count and paper, '
                    'full cover = bleed + back + spine + front + bleed. Trim, paper and page '
                    'count come from book.yaml unless given here.')
    parser.add_argument('--pages', type=int, help='interior page count (default: book.pages, '
                                                  'else counted in the built print PDF)')
    parser.add_argument('--paper', choices=sorted(SPINE_INCHES_PER_PAGE),
                        help='paper type (default: cover.paper)')
    parser.add_argument('--trim', help='trim size, for example 6x9 (default: cover.trim, '
                                       'else the book format)')
    parser.add_argument('--json', action='store_true', help='print JSON')
    add_config_arguments(parser)
    args = parser.parse_args()
    try:
        settings = read_cover_settings(config_from_args(args))
        size = settings.cover_size(args.pages, args.paper, args.trim)
    except (ConfigError, CoverSettingsError, CoverSizeError) as error:
        print(f'cover-size: {error}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(size.as_dict(), indent=2))
    else:
        print(describe(size))
        print(f'page count from  {settings.page_count_source}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
