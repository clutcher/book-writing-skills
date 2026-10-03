from dataclasses import dataclass
from pathlib import Path

from cover_geometry import CoverSize, count_pdf_pages, parse_trim

FINAL_NAMES = {
    'front': 'front.png',
    'back': 'back.png',
    'ebook': 'ebook.png',
    'print_pdf': 'paperback-cover.pdf',
}
BOOK_METADATA_NAMES = {
    'front': 'cover_front',
    'back': 'cover_back',
    'ebook': 'ebook_cover',
}


class CoverSettingsError(Exception):
    pass


class PageCountUnknown(CoverSettingsError):
    pass


def choose_print_pdf(folder):
    if not folder or not Path(folder).is_dir():
        return None
    print_pdfs = [path for path in Path(folder).glob('*.pdf')
                  if 'digital' not in path.name and 'cover' not in path.name]
    if not print_pdfs:
        return None
    finals = [path for path in print_pdfs if '-draft' not in path.name]
    pool, kind = (finals, 'final print PDF') if finals else (print_pdfs, 'print PDF')
    newest = max(pool, key=lambda path: path.stat().st_mtime)
    if len(print_pdfs) == 1:
        return newest, 'the only print PDF'
    return newest, f'the newest {kind} of {len(print_pdfs)} print PDFs'


@dataclass
class CoverSettings:
    config: object
    page_count_source: str = ''

    @property
    def design(self):
        return self.config.cover.design

    @property
    def final(self):
        return self.config.cover.final

    @property
    def output(self):
        return self.config.cover.output

    @property
    def templates(self):
        return self.config.cover.templates

    @property
    def shelf_screenshots(self):
        return self.config.cover.shelf_screenshots

    @property
    def book_pdf(self):
        return self.config.cover.book_pdf

    @property
    def icc(self):
        return self.config.cover.icc

    @property
    def srgb_profile(self):
        return self.config.cover.srgb_profile

    @property
    def render_image(self):
        return self.config.tools.render_image or None

    @property
    def cmyk_limit(self):
        return self.config.cover.cmyk_limit

    @property
    def back_cover(self):
        return self.config.sales_text.back_cover

    @property
    def title(self):
        return self.config.book.title or ''

    @property
    def subtitle(self):
        return self.config.book.subtitle or ''

    @property
    def author(self):
        return self.config.book.author or ''

    def final_file(self, name):
        metadata_name = BOOK_METADATA_NAMES.get(name)
        if metadata_name:
            from_metadata = self.config.book.path(metadata_name)
            if from_metadata:
                return from_metadata
        if self.final is None:
            raise CoverSettingsError('no cover.final folder in book.yaml')
        return self.final / FINAL_NAMES[name]

    def trim(self, override=None):
        return parse_trim(override or self.config.trim)

    def paper(self, override=None):
        return override or self.config.cover.paper

    def page_count(self, override=None):
        if override is not None:
            self.page_count_source = '--pages'
            return int(override)
        configured = self.config.book.get('pages')
        if configured is not None and str(configured).isdigit():
            self.page_count_source = 'book.pages in book.yaml'
            return int(configured)
        if self.book_pdf:
            pdf, why = self.book_pdf, 'cover.book_pdf'
        else:
            pdf, why = self._print_pdf_in_output()
        pages = count_pdf_pages(pdf)
        self.page_count_source = f'counted in {pdf} ({why})'
        return pages

    def _print_pdf_in_output(self):
        folder = self.config.work.output
        chosen = choose_print_pdf(folder)
        if chosen is None:
            raise PageCountUnknown(
                f'no page count yet: no print PDF in {folder}; build the print edition, pass '
                f'--pages, or set book.pages or cover.book_pdf in book.yaml')
        return chosen

    def cover_size(self, pages=None, paper=None, trim=None):
        trim_width, trim_height = self.trim(trim)
        return CoverSize(self.page_count(pages), self.paper(paper), trim_width, trim_height)


def read_cover_settings(config):
    return CoverSettings(config)
