import re
import shutil
import subprocess
from dataclasses import dataclass

SPINE_INCHES_PER_PAGE = {
    'bw-white': 0.002252,
    'bw-cream': 0.0025,
    'color-premium': 0.002347,
    'color-standard': 0.002252,
}
BLEED_INCHES = 0.125
SAFE_INCHES = 0.375
DOTS_PER_INCH = 300
FEWEST_PAGES_FOR_SPINE_TEXT = 80
SPINE_TEXT_EDGE_INCHES = 0.0625
BARCODE_WIDTH_INCHES = 2.0
BARCODE_HEIGHT_INCHES = 1.2
BARCODE_INSET_INCHES = 0.25
TRIM_PATTERN = re.compile(r'^\s*([0-9]*\.?[0-9]+)\s*(?:in|")?\s*[xX×]\s*([0-9]*\.?[0-9]+)\s*(?:in|")?\s*$')


class CoverSizeError(Exception):
    pass


@dataclass(frozen=True)
class CoverSize:
    page_count: int
    paper: str
    trim_width_in: float
    trim_height_in: float
    bleed_in: float = BLEED_INCHES
    dpi: int = DOTS_PER_INCH

    def __post_init__(self):
        if self.paper not in SPINE_INCHES_PER_PAGE:
            raise CoverSizeError(f"unknown paper '{self.paper}'; choose one of "
                                 f"{', '.join(sorted(SPINE_INCHES_PER_PAGE))}")
        if not isinstance(self.page_count, int) or self.page_count <= 0:
            raise CoverSizeError(f"the page count must be a whole number above 0, "
                                 f"got {self.page_count!r}")

    @property
    def spine_width_in(self):
        return self.page_count * SPINE_INCHES_PER_PAGE[self.paper]

    @property
    def full_width_in(self):
        return (self.bleed_in + self.trim_width_in + self.spine_width_in
                + self.trim_width_in + self.bleed_in)

    @property
    def full_height_in(self):
        return self.bleed_in + self.trim_height_in + self.bleed_in

    def pixels(self, inches):
        return int(round(inches * self.dpi))

    @property
    def width_px(self):
        return self.pixels(self.full_width_in)

    @property
    def height_px(self):
        return self.pixels(self.full_height_in)

    @property
    def bleed_px(self):
        return self.pixels(self.bleed_in)

    @property
    def trim_width_px(self):
        return self.pixels(self.trim_width_in)

    @property
    def trim_height_px(self):
        return self.pixels(self.trim_height_in)

    @property
    def spine_width_px(self):
        return self.pixels(self.spine_width_in)

    @property
    def safe_px(self):
        return self.pixels(SAFE_INCHES)

    @property
    def spine_text_allowed(self):
        return self.page_count >= FEWEST_PAGES_FOR_SPINE_TEXT

    def as_dict(self):
        return {
            'page_count': self.page_count,
            'paper': self.paper,
            'trim_in': [self.trim_width_in, self.trim_height_in],
            'bleed_in': self.bleed_in,
            'dpi': self.dpi,
            'spine_width_in': round(self.spine_width_in, 4),
            'full_size_in': [round(self.full_width_in, 4), round(self.full_height_in, 4)],
            'full_size_px': [self.width_px, self.height_px],
            'spine_width_px': self.spine_width_px,
            'front_panel_px': [self.trim_width_px + self.bleed_px, self.height_px],
            'safe_margin_px': self.safe_px,
            'spine_text_allowed': self.spine_text_allowed,
        }


def parse_trim(value):
    if value is None:
        raise CoverSizeError('no trim size: set cover.trim (or the book format) in book.yaml, '
                             'for example 6x9 or 6.14x9.21')
    match = TRIM_PATTERN.match(str(value))
    if not match:
        raise CoverSizeError(f"cannot read the trim size '{value}'; write it as WIDTHxHEIGHT "
                             f"in inches, for example 6.14x9.21")
    return float(match.group(1)), float(match.group(2))


def count_pdf_pages(pdf_path):
    if not shutil.which('pdfinfo'):
        raise CoverSizeError('pdfinfo is not installed (poppler); pass the page count '
                             'with --pages or set book.pages')
    result = subprocess.run(['pdfinfo', str(pdf_path)], capture_output=True, encoding='utf-8', errors='replace')
    if result.returncode != 0:
        raise CoverSizeError(f'pdfinfo failed on {pdf_path}: {result.stderr.strip()}')
    match = re.search(r'^Pages:\s+(\d+)', result.stdout, re.MULTILINE)
    if not match:
        raise CoverSizeError(f'pdfinfo printed no page count for {pdf_path}')
    return int(match.group(1))


def describe(size):
    lines = [
        f'pages            {size.page_count} ({size.paper} paper)',
        f'trim             {size.trim_width_in} x {size.trim_height_in} in',
        f'spine            {size.spine_width_in:.4f} in = {size.spine_width_px} px',
        f'full cover       {size.full_width_in:.4f} x {size.full_height_in:.4f} in '
        f'= {size.width_px} x {size.height_px} px at {size.dpi} dpi',
        f'front panel      {size.trim_width_px + size.bleed_px} x {size.height_px} px '
        f'(trim plus the outer bleed)',
        f'safe margin      {SAFE_INCHES} in = {size.safe_px} px inside the trim',
        f'spine text       {"allowed" if size.spine_text_allowed else "not allowed"} '
        f'(needs {FEWEST_PAGES_FOR_SPINE_TEXT}+ pages, '
        f'{SPINE_TEXT_EDGE_INCHES} in from each spine edge)',
    ]
    return '\n'.join(lines)
