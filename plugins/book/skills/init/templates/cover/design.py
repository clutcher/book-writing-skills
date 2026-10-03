from cover_design import CoverDesign
from svg_parts import rect


class BookCover(CoverDesign):
    TITLE_COLOR = '#1A2030'
    TITLE_SIZE = 140

    def front(self, wrap):
        width = wrap.front_panel_width
        svg = rect(0, 0, width, wrap.height, self.BACKGROUND)
        svg += self.place_text(width / 2, wrap.height * 0.45, self.book.title, self.DISPLAY_FONT,
                               self.TITLE_SIZE, self.TITLE_COLOR, anchor='middle')
        return svg
