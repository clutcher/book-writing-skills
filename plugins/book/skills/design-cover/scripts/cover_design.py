import importlib.util
import inspect
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

from back_layout import ASCENT_EM, DESCENT_EM, BackTypesetter
from cover_geometry import SPINE_TEXT_EDGE_INCHES
from svg_parts import escape, spaced_name, text
from text_width import average_widths, read_body_widths


RETIRED_SETTINGS = {
    'BACK_JUSTIFY': 'the back text is always ragged-right, because SVG renderers such as '
                    'rsvg-convert ignore word-spacing; remove it from the design',
    'BACK_JUSTIFY_MAX_STRETCH': 'the back text is always ragged-right; remove it from the design',
}


PARTS = ('across', 'back', 'spine', 'front')
BOLD_WEIGHT_FROM = 600


class DesignError(Exception):
    pass


@dataclass(frozen=True)
class PlacedText:
    part: str
    content: str
    box: tuple


@dataclass(frozen=True)
class SpineText:
    role: str
    font_size: float
    centre_y: int
    estimated_length: float
    designed_size: float


@dataclass
class BookFacts:
    title: str
    subtitle: str = ''
    author: str = ''
    back_copy: list = field(default_factory=list)
    folder: Path = None

    @property
    def title_words(self):
        return self.title.split()

    @property
    def author_words(self):
        return self.author.split()


class CoverDesign:
    BACKGROUND = '#FFFFFF'
    TITLE_COLOR = '#202020'
    BODY_COLOR = '#202020'
    SUBTITLE_COLOR = '#4A4A4A'
    AUTHOR_COLOR = '#4A4A4A'
    ACCENT_COLOR = '#202020'

    DISPLAY_FONT = 'serif'
    DISPLAY_ITALIC_FONT = None
    BODY_FONT = 'sans-serif'
    BODY_ITALIC_FONT = None
    BODY_WIDTHS = None

    AUTHOR_SEPARATOR = None

    BACK_SIDE_MARGIN_IN = 0.75
    BACK_TITLE_TOP = 300
    BACK_TITLE_SIZE = 54
    BACK_TITLE_WEIGHT = 600
    BACK_TITLE_LETTER_SPACING = 0
    BACK_SUBTITLE_SIZE = 30
    BACK_SUBTITLE_WEIGHT = 500
    BACK_SUBTITLE_LETTER_SPACING = 1
    BACK_TITLE_SUBTITLE_GAP = 42
    BACK_SUBTITLE_BODY_GAP = 110
    BACK_BODY_SIZE = 30
    BACK_BODY_WEIGHT = 400
    BACK_BOLD_WEIGHT = 700
    BACK_EMPHASIS_WEIGHT = 500
    BACK_LINE_HEIGHT = 39
    BACK_PARAGRAPH_GAP = 28
    BACK_HEADING_GAP_BEFORE = 24
    BACK_HEADING_SIZE_STEP = 4
    BACK_HEADING_WEIGHT = 600
    BACK_HEADING_LETTER_SPACING = 0.5
    BACK_BULLET_GAP = 12
    BACK_BULLET_GAP_AFTER = 24
    BACK_BULLET_INDENT = 36
    BACK_BULLET_MARK = '•'
    BACK_BULLET_SIZE_SCALE = 1.5
    BACK_BULLET_WEIGHT = 700
    BACK_BULLET_INK_CENTRE_EM = None
    BACK_NARROW_FRACTION = 0.55
    BACK_BOLD_LEAD_OWN_LINES = True
    BACK_LEAD_GAP_AFTER = 14
    BACK_FIX_WIDOWS = True
    BACK_RUNT_FRACTION = 0.25
    BACK_WRAP_MARGIN = 1.0

    SPINE_TITLE_AT = 0.42
    SPINE_AUTHOR_AT = 0.86
    SPINE_TITLE_SIZE = 58
    SPINE_TITLE_WEIGHT = 600
    SPINE_TITLE_LETTER_SPACING = 6
    SPINE_TITLE_BASELINE = 16
    SPINE_TITLE_WORD_GAP = 10
    SPINE_AUTHOR_SIZE = 32
    SPINE_AUTHOR_WEIGHT = 500
    SPINE_AUTHOR_LETTER_SPACING = 6
    SPINE_AUTHOR_BASELINE = 16
    SPINE_SEPARATOR_LIFT = -4

    def __init__(self, book):
        self.book = book
        self._widths = None
        self.drawing_part = None
        self.placed_texts = {part: [] for part in PARTS}
        self.spine_texts = []

    def draw(self, part, wrap):
        self.drawing_part = part
        self.placed_texts[part] = []
        if part == 'spine':
            self.spine_texts = []
        try:
            return getattr(self, part)(wrap)
        finally:
            self.drawing_part = None

    def place_text(self, x, y, content, font_family, font_size, fill, anchor='start',
                   weight=500, style='normal', letter_spacing=0, opacity=1.0, turn=0):
        width = (self.body_widths().measure(content, width_style(weight, style), font_size)
                 + letter_spacing * len(content))
        left = {'start': x, 'middle': x - width / 2, 'end': x - width}[anchor]
        box = turned_box((left, y - ASCENT_EM * font_size, left + width,
                          y + DESCENT_EM * font_size), x, y, turn)
        self.record_text(content, box)
        extra = f' transform="rotate({turn} {x} {y})"' if turn else ''
        return text(x, y, content, font_family, font_size, fill, anchor, weight, style,
                    letter_spacing, opacity, extra)

    def place_back_copy(self, left, width, top):
        typesetter = BackTypesetter(self, self.body_widths())
        svg, end = typesetter.render(self.book.back_copy, left, width, top)
        for box in typesetter.line_boxes:
            self.record_text('', box)
        return svg, end

    def record_text(self, content, box):
        if self.drawing_part is None:
            return
        self.placed_texts[self.drawing_part].append(
            PlacedText(self.drawing_part, content, tuple(box)))

    def front(self, wrap):
        raise NotImplementedError('a cover design must draw its front panel: define front(wrap)')

    def across(self, wrap):
        return ''

    def back(self, wrap):
        left = wrap.back_trim_x + wrap.inches(self.BACK_SIDE_MARGIN_IN)
        width = wrap.trim_width - 2 * wrap.inches(self.BACK_SIDE_MARGIN_IN)
        title_y = wrap.back_trim_y + self.BACK_TITLE_TOP
        svg = self.place_text(left, title_y, self.book.title, self.DISPLAY_FONT,
                              self.BACK_TITLE_SIZE, self.TITLE_COLOR,
                              weight=self.BACK_TITLE_WEIGHT,
                              letter_spacing=self.BACK_TITLE_LETTER_SPACING) + '\n'
        subtitle_y = title_y + self.BACK_TITLE_SUBTITLE_GAP
        if self.book.subtitle:
            svg += self.place_text(left, subtitle_y, self.book.subtitle,
                                   self.DISPLAY_ITALIC_FONT or self.DISPLAY_FONT,
                                   self.BACK_SUBTITLE_SIZE, self.SUBTITLE_COLOR,
                                   weight=self.BACK_SUBTITLE_WEIGHT, style='italic',
                                   letter_spacing=self.BACK_SUBTITLE_LETTER_SPACING) + '\n'
        body_top = subtitle_y + self.BACK_SUBTITLE_BODY_GAP
        body_svg, _body_end = self.place_back_copy(left, width, body_top)
        return svg + body_svg

    def spine(self, wrap):
        if not wrap.size.spine_text_allowed:
            return ''
        centre = wrap.spine_x + wrap.spine_width // 2
        room = wrap.spine_width - 2 * wrap.inches(SPINE_TEXT_EDGE_INCHES)
        title_words = [word.upper() for word in self.book.title_words]
        title_scale = min(1.0, room / self.SPINE_TITLE_SIZE)
        title_gap = self.SPINE_TITLE_WORD_GAP * title_scale
        title_spans = ''.join(
            f'<tspan>{escape(word)}</tspan>' if index == 0 else
            f'<tspan dx="{title_gap:.1f}"> {escape(word)}</tspan>'
            for index, word in enumerate(title_words))
        svg = self.spine_line(
            wrap, 'title', title_words, title_spans, centre, self.SPINE_TITLE_AT,
            self.SPINE_TITLE_SIZE * title_scale, self.SPINE_TITLE_SIZE,
            self.SPINE_TITLE_BASELINE * title_scale, self.SPINE_TITLE_WEIGHT, self.TITLE_COLOR,
            self.SPINE_TITLE_LETTER_SPACING * title_scale, title_gap)
        if not self.book.author:
            return svg
        author_words = [word.upper() for word in self.book.author_words]
        author_scale = min(1.0, room / self.SPINE_AUTHOR_SIZE)
        name = spaced_name(author_words, self.AUTHOR_SEPARATOR, self.SPINE_SEPARATOR_LIFT)
        return svg + self.spine_line(
            wrap, 'author', author_words, name, centre, self.SPINE_AUTHOR_AT,
            self.SPINE_AUTHOR_SIZE * author_scale, self.SPINE_AUTHOR_SIZE,
            self.SPINE_AUTHOR_BASELINE * author_scale, self.SPINE_AUTHOR_WEIGHT,
            self.AUTHOR_COLOR, self.SPINE_AUTHOR_LETTER_SPACING * author_scale, 0)

    def spine_line(self, wrap, role, words, content, centre, at, size, designed_size, baseline,
                   weight, color, letter_spacing, word_gap):
        line_centre = int(wrap.height * at)
        self.spine_texts.append(SpineText(
            role, size, line_centre, self.spaced_length(words, size, letter_spacing, word_gap),
            designed_size))
        return (f'<g transform="translate({centre},{line_centre}) rotate(90)">'
                f'<text x="0" y="{baseline:.1f}" font-family="{self.DISPLAY_FONT}" '
                f'font-size="{size:.1f}" font-weight="{weight}" fill="{color}" '
                f'text-anchor="middle" letter-spacing="{letter_spacing:.1f}" '
                f'xml:space="preserve">{content}</text></g>\n')

    def spaced_length(self, words, font_size, letter_spacing, word_gap):
        text = ' '.join(words)
        return (self.body_widths().measure(text, 'b', font_size) + letter_spacing * len(text)
                + word_gap * max(len(words) - 1, 0))

    def body_widths(self):
        if self._widths is None:
            if self.BODY_WIDTHS:
                path = Path(self.BODY_WIDTHS)
                if not path.is_absolute() and self.book.folder:
                    path = self.book.folder / path
                self._widths = read_body_widths(path)
            else:
                self._widths = average_widths()
        return self._widths


def width_style(weight, style):
    bold = 'b' if int(weight) >= BOLD_WEIGHT_FROM else ''
    italic = 'i' if style == 'italic' else ''
    return bold + italic


def turned_box(box, x, y, turn):
    if not turn:
        return box
    angle = math.radians(turn)
    cosine, sine = math.cos(angle), math.sin(angle)
    corners = [(box[0], box[1]), (box[2], box[1]), (box[0], box[3]), (box[2], box[3])]
    turned = [(x + (corner_x - x) * cosine - (corner_y - y) * sine,
               y + (corner_x - x) * sine + (corner_y - y) * cosine)
              for corner_x, corner_y in corners]
    return (min(point[0] for point in turned), min(point[1] for point in turned),
            max(point[0] for point in turned), max(point[1] for point in turned))


def load_design_class(design_path):
    design_path = Path(design_path)
    if not design_path.is_file():
        raise DesignError(f'no cover design file at {design_path}: set cover.design in book.yaml')
    scripts = str(Path(__file__).resolve().parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    module_name = f'cover_book_design_{abs(hash(str(design_path)))}'
    spec = importlib.util.spec_from_file_location(module_name, design_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise DesignError(f'the cover design {design_path} failed to load: '
                          f'{type(error).__name__}: {error}')
    chosen = getattr(module, 'DESIGN', None)
    if chosen is None:
        chosen = only_design_class(module, module_name, design_path)
    retired = sorted(name for name in RETIRED_SETTINGS if hasattr(chosen, name))
    if retired:
        raise DesignError(f'{design_path} sets {", ".join(retired)}: '
                          f'{RETIRED_SETTINGS[retired[0]]}')
    return chosen


def only_design_class(module, module_name, design_path):
    own = [value for value in vars(module).values()
           if inspect.isclass(value) and issubclass(value, CoverDesign)
           and value.__module__ == module_name]
    leaves = [value for value in own if not any(other is not value and issubclass(other, value)
                                                for other in own)]
    if len(leaves) != 1:
        raise DesignError(f'{design_path} must define one CoverDesign subclass, or name the one '
                          f'to use with DESIGN = <class>; found {len(leaves)}')
    return leaves[0]
