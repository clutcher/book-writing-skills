from pathlib import Path

from back_copy_text import read_back_copy
from cover_design import BookFacts, DesignError, load_design_class
from cover_settings import CoverSettingsError
from cover_geometry import CoverSizeError
from cover_wrap import CoverWrap

NOMINAL_PAGE_COUNT = 200


def report_skipped_for_missing_design(report, settings, override, output_format):
    if override or not report.skip_unless_present(settings.design, "cover design"):
        return None
    return report.emit(output_format)


def design_path_of(settings, override=None):
    path = Path(override) if override else settings.design
    if path is None:
        raise DesignError('no design file: set cover.design in book.yaml or pass --design')
    return path


def nominal_pages_if_unknown(settings, pages):
    if pages is not None:
        return pages, None
    try:
        return settings.page_count(), None
    except (CoverSettingsError, CoverSizeError) as error:
        return NOMINAL_PAGE_COUNT, (f'the page count is unknown ({error}); the geometry uses '
                                    f'a nominal {NOMINAL_PAGE_COUNT} pages, which is fine for '
                                    f'this check but not for the spine or the template')


def build_wrap(settings, design_path, pages=None, paper=None, trim=None):
    size = settings.cover_size(pages, paper, trim)
    back_copy = []
    notes = []
    if settings.back_cover and settings.back_cover.is_file():
        back_copy = read_back_copy(settings.back_cover)
    else:
        notes.append(f'no back-cover text ({settings.back_cover or "sales_text.back_cover not set"})'
                     f': the back panel shows the title only')
    design_class = load_design_class(design_path)
    facts = BookFacts(settings.title, settings.subtitle, settings.author, back_copy,
                      Path(design_path).parent)
    return CoverWrap(design_class(facts), size), notes
