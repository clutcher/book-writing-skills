from cover_design import CoverDesign
from svg_parts import rect, text


class PlainCover(CoverDesign):
    BACKGROUND = '#FFFFFF'
    TITLE_COLOR = '#202020'
    SUBTITLE_COLOR = '#DDDDDD'
    AUTHOR_COLOR = '#404040'
    ACCENT_COLOR = '#205080'
    BAND_COLOR = '#2E6F95'
    UNUSED_COLOR = '#123456'

    def front(self, wrap):
        width = wrap.front_panel_width
        svg = rect(0, 0, width, wrap.height, self.BACKGROUND)
        svg += rect(0, 200, width, 300, self.BAND_COLOR)
        svg += text(150, 900, self.book.title, self.DISPLAY_FONT, 120, self.TITLE_COLOR)
        svg += text(150, 1050, self.book.subtitle, self.DISPLAY_FONT, 40, self.SUBTITLE_COLOR,
                    style='italic')
        svg += text(150, 2500, self.book.author, self.DISPLAY_FONT, 44, self.AUTHOR_COLOR)
        return svg
