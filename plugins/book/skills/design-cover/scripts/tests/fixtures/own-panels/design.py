from cover_design import CoverDesign
from svg_parts import line, rect


class OwnPanelsCover(CoverDesign):
    WHITE = '#FFFFFF'
    BLUE = '#1C3D6E'

    BACKGROUND = WHITE
    TITLE_COLOR = BLUE
    BODY_COLOR = BLUE
    SUBTITLE_COLOR = BLUE
    AUTHOR_COLOR = WHITE
    ACCENT_COLOR = BLUE

    TITLE_SIZE = 300
    TITLE_Y = 900
    RULE_Y = 1100
    SUBTITLE_Y = 1250
    BAND_TOP = 2400
    AUTHOR_Y = 2700

    BACK_TITLE_TOP = 400
    BACK_SUBTITLE_BODY_GAP = 100

    SPINE_TITLE_AT = 0.4
    SPINE_AUTHOR_AT = 0.85

    def front(self, wrap):
        left = -wrap.bleed
        width = wrap.front_panel_width + wrap.bleed
        centre = wrap.trim_width / 2
        return (self.ground(left, width, wrap.height)
                + self.place_text(centre, self.TITLE_Y, self.book.title, self.DISPLAY_FONT,
                                  self.TITLE_SIZE, self.TITLE_COLOR, anchor='middle')
                + line(centre - 400, self.RULE_Y, centre + 400, self.RULE_Y, self.ACCENT_COLOR, 4, 1)
                + self.place_text(centre, self.SUBTITLE_Y, self.book.subtitle,
                                  self.DISPLAY_FONT, 80, self.SUBTITLE_COLOR, anchor='middle',
                                  weight=400, style='italic')
                + self.place_text(centre, self.AUTHOR_Y, self.author_in_capitals(),
                                  self.BODY_FONT, 40, self.AUTHOR_COLOR, anchor='middle',
                                  letter_spacing=10))

    def across(self, wrap):
        return self.ground(0, wrap.front_x, wrap.height)

    def back(self, wrap):
        left = wrap.back_trim_x + wrap.inches(self.BACK_SIDE_MARGIN_IN)
        width = wrap.trim_width - 2 * wrap.inches(self.BACK_SIDE_MARGIN_IN)
        centre = wrap.back_trim_x + wrap.trim_width / 2
        title_y = wrap.back_trim_y + self.BACK_TITLE_TOP
        svg = self.place_text(centre, title_y, self.book.title, self.DISPLAY_FONT, 70,
                              self.TITLE_COLOR, anchor='middle')
        svg += self.place_text(centre, title_y + 60, self.book.subtitle, self.DISPLAY_FONT, 40,
                               self.SUBTITLE_COLOR, anchor='middle', weight=400, style='italic')
        body_svg, _end = self.place_back_copy(left, width,
                                              title_y + 60 + self.BACK_SUBTITLE_BODY_GAP)
        return svg + body_svg

    def spine(self, wrap):
        if not wrap.size.spine_text_allowed:
            return ''
        centre = wrap.spine_x + wrap.spine_width / 2
        size = min(50, wrap.spine_width * 0.5)
        baseline_shift = size * 0.3
        return (self.place_text(centre - baseline_shift, wrap.height * self.SPINE_TITLE_AT,
                                self.book.title.upper(), self.DISPLAY_FONT, size,
                                self.TITLE_COLOR, anchor='middle', letter_spacing=4, turn=90)
                + self.place_text(centre - baseline_shift * 0.7,
                                  wrap.height * self.SPINE_AUTHOR_AT, self.author_in_capitals(),
                                  self.BODY_FONT, size * 0.7, self.TITLE_COLOR,
                                  anchor='middle', letter_spacing=4, turn=90))

    def author_in_capitals(self):
        return ' '.join(self.book.author_words).upper()

    def ground(self, left, width, height):
        return (rect(left, 0, width, height, self.WHITE)
                + rect(left, self.BAND_TOP, width, height - self.BAND_TOP, self.BLUE))
