from cover_design import CoverDesign
from svg_parts import rect


class BookCover(CoverDesign):
    TITLE_COLOR = '#1A2030'
    TITLE_SIZE = 140
    TITLE_WEIGHT = 700

    DISPLAY_FONT = 'DejaVu Serif, serif'
    BODY_FONT = 'DejaVu Sans, sans-serif'

    BACK_TITLE_WEIGHT = 700
    BACK_SUBTITLE_WEIGHT = 400
    BACK_EMPHASIS_WEIGHT = 400
    BACK_HEADING_WEIGHT = 700
    SPINE_TITLE_WEIGHT = 700
    SPINE_AUTHOR_WEIGHT = 400

    def front(self, wrap):
        width = wrap.front_panel_width
        svg = rect(0, 0, width, wrap.height, self.BACKGROUND)
        svg += self.place_text(width / 2, wrap.height * 0.45, self.book.title, self.DISPLAY_FONT,
                               self.TITLE_SIZE, self.TITLE_COLOR, anchor='middle',
                               weight=self.TITLE_WEIGHT)
        return svg
