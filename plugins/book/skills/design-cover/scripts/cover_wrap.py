from pathlib import Path

from svg_parts import XML_HEADER

PANELS = ('wrap', 'back', 'spine', 'front', 'front-trim', 'back-trim')
SHIPPING_PANELS = {'front-trim': 'front', 'back-trim': 'back'}


class CoverWrap:
    def __init__(self, design, size):
        self.design = design
        self.size = size
        self.dpi = size.dpi
        self.width = size.width_px
        self.height = size.height_px
        self.bleed = size.bleed_px
        self.trim_width = size.trim_width_px
        self.trim_height = size.trim_height_px
        self.spine_width = size.spine_width_px
        self.safe = size.safe_px

        self.back_x = 0
        self.back_panel_width = self.bleed + self.trim_width
        self.spine_x = self.back_panel_width
        self.front_x = self.spine_x + self.spine_width
        self.front_panel_width = self.trim_width + self.bleed

        self.back_trim_x = self.bleed
        self.back_trim_y = self.bleed
        self.front_trim_x = self.front_x
        self.front_trim_y = self.bleed

    def inches(self, value):
        return int(round(value * self.dpi))

    def render(self, panel='wrap'):
        if panel == 'wrap':
            body = (self.design.draw('across', self) + self.design.draw('back', self)
                    + self.design.draw('spine', self) + self._front())
            return self._canvas(0, 0, self.width, self.height, body)
        if panel == 'back':
            body = self.design.draw('across', self) + self.design.draw('back', self)
            return self._canvas(0, 0, self.back_panel_width, self.height, body)
        if panel == 'spine':
            body = self.design.draw('across', self) + self.design.draw('spine', self)
            return self._canvas(self.spine_x, 0, self.spine_width, self.height, body)
        if panel == 'front':
            return self._canvas(self.front_x, 0, self.front_panel_width, self.height,
                                self._front())
        if panel == 'front-trim':
            return self._canvas(self.front_trim_x, self.front_trim_y,
                                self.trim_width, self.trim_height, self._front())
        if panel == 'back-trim':
            body = self.design.draw('across', self) + self.design.draw('back', self)
            return self._canvas(self.back_trim_x, self.back_trim_y,
                                self.trim_width, self.trim_height, body)
        raise ValueError(f"unknown panel '{panel}'; choose one of {', '.join(PANELS)}")

    def _front(self):
        return (f'<svg x="{self.front_x}" y="0" width="{self.front_panel_width}" '
                f'height="{self.height}" '
                f'viewBox="0 0 {self.front_panel_width} {self.height}" '
                f'preserveAspectRatio="xMidYMid slice">'
                + self.design.draw('front', self) + '</svg>\n')

    def _canvas(self, x, y, width, height, body):
        return (XML_HEADER
                + f'<svg viewBox="{x} {y} {width} {height}" '
                  f'xmlns="http://www.w3.org/2000/svg" '
                  f'width="{width}" height="{height}">\n'
                + f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
                  f'fill="{self.design.BACKGROUND}"/>\n'
                + body + '</svg>')

    def save(self, path, panel='wrap'):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(panel), encoding='utf-8')
        return path


def panel_file_name(panel):
    return 'wrap.svg' if panel == 'wrap' else f'{panel}.svg'
