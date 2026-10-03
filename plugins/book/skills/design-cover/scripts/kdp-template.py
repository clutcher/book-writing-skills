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
from cover_geometry import SPINE_INCHES_PER_PAGE, CoverSizeError
from kdp_download import (CALCULATOR_PAGE, DEFAULT_PRINT_LOCALE, NEW, REPLACED, SAME, NetworkMissingError,
                          TemplateAnswerError, TemplateRequest, fetch_templates)

TOOL = 'kdp-template'
CLASSES = {
    'request-planned': INFORMATIONAL,
    'template-present': INFORMATIONAL,
    'template-missing': INFORMATIONAL,
    'template-written': INFORMATIONAL,
    'template-replaced': ADVISORY,
}
STATE_CLASSES = {SAME: 'template-present', NEW: 'template-written', REPLACED: 'template-replaced'}
STATE_MESSAGES = {
    SAME: 'already there and the same as the KDP file; nothing written',
    NEW: 'written',
    REPLACED: 'KDP now sends a different file; the old one was replaced, so look at the overlay '
              'again',
}


def main():
    parser = argparse.ArgumentParser(
        description='Download the KDP paperback cover template (PNG and PDF) for the trim, page '
                    'count and paper of the book into cover.templates. Dry run by default: '
                    'prints the request and the target files and uses no network. --fix asks '
                    'the KDP cover calculator and unpacks the template; a file that is '
                    'already there with the same bytes is left alone. '
                    'This calls an unofficial, undocumented Amazon endpoint (the one behind the '
                    'cover calculator page). It may change or stop at any time. You run it at '
                    'your own discretion and under Amazon\'s terms. It names itself in its '
                    'User-Agent and sends one request for the template and one for the zip '
                    'file. When the endpoint changes, the script stops with exit 2 and says how '
                    'to download the template by hand. '
                    f'The manual way: open {CALCULATOR_PAGE}, choose paperback, the trim size, '
                    'the page count and the paper, download the template, unzip it and put the '
                    'PNG and PDF in cover.templates.')
    parser.add_argument('--pages', type=int, help='interior page count (default: book.pages, '
                                                  'else counted in the built print PDF)')
    parser.add_argument('--paper', choices=sorted(SPINE_INCHES_PER_PAGE),
                        help='paper type (default: cover.paper)')
    parser.add_argument('--trim', help='trim size in inches, for example 6x9 (default: '
                                       'cover.trim, else the book format)')
    parser.add_argument('--print-locale', default=DEFAULT_PRINT_LOCALE,
                        help=f'KDP print locale (default {DEFAULT_PRINT_LOCALE})')
    parser.add_argument('--templates', help='folder for the templates (default: '
                                            'cover.templates)')
    parser.add_argument('--fix', action='store_true',
                        help='download the template and write it into the folder')
    add_config_arguments(parser)
    add_output_arguments(parser)
    args = parser.parse_args()
    report = CheckReport(TOOL, CLASSES)

    try:
        settings = read_cover_settings(config_from_args(args))
        size = settings.cover_size(args.pages, args.paper, args.trim)
    except (ConfigError, CoverSettingsError, CoverSizeError) as error:
        return tool_failed(str(error), TOOL)
    folder = Path(args.templates) if args.templates else settings.templates
    if folder is None:
        return tool_failed('no cover.templates folder in book.yaml: pass --templates', TOOL)
    template_request = TemplateRequest(size.trim_width_in, size.trim_height_in,
                                       size.page_count, size.paper, args.print_locale)
    report.add('request', 'request-planned',
               f'{template_request.as_text()} (page count: {settings.page_count_source})')

    if not args.fix:
        for name in template_request.file_names():
            target = folder / name
            if target.is_file():
                report.add(name, 'template-present', f'{target} is there; --fix downloads it '
                                                      f'again and keeps it when it is the same')
            else:
                report.add(name, 'template-missing', f'{target}: run with --fix to download it')
        return report.emit(args.format)

    try:
        results = fetch_templates(template_request, folder)
    except TemplateAnswerError as error:
        return tool_failed(f'{error}. {template_request.manual_way(folder)}', TOOL)
    except NetworkMissingError as error:
        report.skip(f'{error}; {template_request.manual_way(folder)}')
        return report.emit(args.format)
    for target, state in results:
        report.add(target.name, STATE_CLASSES[state], f'{target}: {STATE_MESSAGES[state]}')
    return report.emit(args.format)


if __name__ == '__main__':
    sys.exit(main())
