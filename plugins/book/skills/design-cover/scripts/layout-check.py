#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parents[2] / 'lib'))
sys.path.insert(0, str(SCRIPTS))

from back_copy_text import BackCopyError
from book_config import ConfigError, add_config_arguments, config_from_args
from check_output import CheckReport, add_output_arguments, tool_failed
from cover_design import DesignError
from cover_loader import build_wrap, design_path_of, report_skipped_for_missing_design
from cover_settings import CoverSettingsError, PageCountUnknown, read_cover_settings
from cover_geometry import SPINE_INCHES_PER_PAGE, CoverSizeError
from layout_rules import LAYOUT_CLASSES, layout_findings
from text_width import FontFileError

TOOL = 'layout-check'


def main():
    parser = argparse.ArgumentParser(
        description='Check where the cover puts its text: every line of the back text inside '
                    'the safe area and out of the KDP barcode area, spine text only when the '
                    'page count allows it and only when it fits the spine, and every text the '
                    'design placed with place_text inside the safe area of its panel. Nothing '
                    'is written.')
    parser.add_argument('--design', help='the design file (default: cover.design)')
    parser.add_argument('--pages', type=int, help='interior page count')
    parser.add_argument('--paper', choices=sorted(SPINE_INCHES_PER_PAGE), help='paper type')
    parser.add_argument('--trim', help='trim size, for example 6x9')
    add_config_arguments(parser)
    add_output_arguments(parser)
    args = parser.parse_args()
    report = CheckReport(TOOL, LAYOUT_CLASSES)
    try:
        settings = read_cover_settings(config_from_args(args))
        skipped = report_skipped_for_missing_design(report, settings, args.design, args.format)
        if skipped is not None:
            return skipped
        wrap, _notes = build_wrap(settings, design_path_of(settings, args.design), args.pages,
                                  args.paper, args.trim)
        findings = layout_findings(wrap)
    except PageCountUnknown as reason:
        report.skip(str(reason))
        return report.emit(args.format)
    except (ConfigError, CoverSettingsError, CoverSizeError, DesignError, BackCopyError,
            FontFileError) as error:
        return tool_failed(str(error), TOOL)
    for finding in findings:
        report.add(finding.key, finding.finding_class, finding.message)
    return report.emit(args.format)


if __name__ == '__main__':
    sys.exit(main())
