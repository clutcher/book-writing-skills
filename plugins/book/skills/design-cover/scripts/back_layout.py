from back_copy_text import (BULLET, EMPHASIS, EMPHASIS_NARROW, HEADING, LINE_BREAK, NARROW,
                       PLAIN, SPACE)
from svg_parts import escape

LEADING_PUNCTUATION = ',.;:!?)'
ASCENT_EM = 0.8
DESCENT_EM = 0.25
NARROW_KINDS = (NARROW, EMPHASIS_NARROW)
EMPHASIS_KINDS = (EMPHASIS, EMPHASIS_NARROW)


class BackTypesetter:
    def __init__(self, design, widths):
        self.design = design
        self.widths = widths
        self.line_boxes = []

    def measure(self, text, style, font_size):
        return self.widths.measure(text, style, font_size)

    def render(self, blocks, x, width, top):
        design = self.design
        svg = ''
        y = top
        narrow_width = int(width * design.BACK_NARROW_FRACTION)
        for index, (kind, content) in enumerate(blocks):
            if kind == SPACE:
                y += int(content)
                continue
            if kind == HEADING:
                y += design.BACK_HEADING_GAP_BEFORE
            block_width = narrow_width if kind in NARROW_KINDS else width
            block_svg, y = self.block(kind, content, x, block_width, y)
            svg += block_svg
            next_kind = blocks[index + 1][0] if index + 1 < len(blocks) else None
            if kind == BULLET and next_kind == BULLET:
                y += design.BACK_BULLET_GAP
            elif kind == BULLET:
                y += design.BACK_PARAGRAPH_GAP + design.BACK_BULLET_GAP_AFTER
            else:
                y += design.BACK_PARAGRAPH_GAP
        return svg, y

    def block(self, kind, content, x, width, y):
        design = self.design
        font_size = design.BACK_BODY_SIZE
        line_height = design.BACK_LINE_HEIGHT
        if kind == BULLET:
            return self.bullet(content, x, width, y, font_size, line_height)
        if kind == HEADING:
            heading_size = font_size + design.BACK_HEADING_SIZE_STEP
            self.record_box(x, y, self.measure(content, 'b', heading_size)
                            + design.BACK_HEADING_LETTER_SPACING * len(content), heading_size)
            svg = (f'<text x="{x}" y="{y}" font-family="{design.BODY_FONT}" '
                   f'font-size="{heading_size}" '
                   f'font-weight="{design.BACK_HEADING_WEIGHT}" '
                   f'fill="{design.ACCENT_COLOR}" '
                   f'letter-spacing="{design.BACK_HEADING_LETTER_SPACING}">'
                   f'{escape(content)}</text>\n')
            return svg, y + line_height
        emphasis = kind in EMPHASIS_KINDS
        base_weight = design.BACK_EMPHASIS_WEIGHT if emphasis else design.BACK_BODY_WEIGHT
        base_style = 'italic' if emphasis else 'normal'
        runs = to_runs(content)
        if emphasis:
            runs = [(style if 'i' in style else style + 'i', text) for style, text in runs]
        svg = ''
        groups = self.split_bold_lead(runs)
        for group_index, group in enumerate(groups):
            for line in self.wrap_runs(group, width, font_size):
                svg += self.line(x, y, line, font_size, design.BODY_COLOR,
                                 base_weight, base_style)
                y += line_height
            if group_index < len(groups) - 1:
                y += design.BACK_LEAD_GAP_AFTER
        return svg, y

    def bullet(self, content, x, width, y, font_size, line_height):
        design = self.design
        indent = design.BACK_BULLET_INDENT
        lines = self.wrap_runs(to_runs(content), width - indent, font_size)
        marker_size = font_size * design.BACK_BULLET_SIZE_SCALE
        ink_centre = design.BACK_BULLET_INK_CENTRE_EM
        if ink_centre is None:
            ink_centre = self.widths.bullet_ink_centre_em or 0.0
        marker_y = y + (marker_size - font_size) * ink_centre
        svg = ''
        for index, line in enumerate(lines):
            if index == 0:
                svg += (f'<text x="{x}" y="{marker_y:.1f}" '
                        f'font-family="{design.BODY_FONT}" '
                        f'font-size="{marker_size:.1f}" '
                        f'font-weight="{design.BACK_BULLET_WEIGHT}" '
                        f'fill="{design.ACCENT_COLOR}">'
                        f'{design.BACK_BULLET_MARK}</text>\n')
            svg += self.line(x + indent, y, line, font_size, design.BODY_COLOR,
                             design.BACK_BODY_WEIGHT)
            y += line_height
        return svg, y

    def split_bold_lead(self, runs):
        if not self.design.BACK_BOLD_LEAD_OWN_LINES:
            return [runs]
        lead = []
        for style, text in runs:
            if style == LINE_BREAK:
                lead.append((style, text))
                continue
            if 'b' not in style:
                break
            lead.append((style, text))
        rest = runs[len(lead):]
        if not lead or not rest:
            return [runs]
        return [lead, rest]

    def wrap_runs(self, runs, width, font_size):
        longest = width * self.design.BACK_WRAP_MARGIN
        regular_space = self.measure(' ', PLAIN, font_size)
        bold_space = self.measure(' ', 'b', font_size)
        words = []
        for style, text in runs:
            if style == LINE_BREAK:
                words.append((LINE_BREAK, ''))
                continue
            for word in text.split():
                words.append((style, word))
        lines = []
        current = []
        current_width = 0.0
        for style, word in words:
            if style == LINE_BREAK:
                if current:
                    lines.append(current)
                    current = []
                    current_width = 0.0
                continue
            word_width = self.measure(word, style, font_size)
            gap = (bold_space if 'b' in style else regular_space) if current else 0.0
            if current_width + gap + word_width > longest and current:
                lines.append(current)
                current = [(style, word)]
                current_width = word_width
            else:
                current.append((style, word))
                current_width += gap + word_width
        if current:
            lines.append(current)
        if self.design.BACK_FIX_WIDOWS:
            lines = self.fix_widows_and_runts(lines, longest, font_size)
        return lines

    def fix_widows_and_runts(self, lines, longest=None, font_size=None):
        if len(lines) < 2:
            return lines
        out = [list(line) for line in lines]
        for index in range(len(out) - 1):
            if len(out[index]) < 2:
                continue
            _previous_style, previous_word = out[index][-2]
            _last_style, last_word = out[index][-1]
            if ends_sentence(previous_word) and starts_sentence(last_word):
                out[index + 1].insert(0, out[index].pop())
        while (len(out) >= 2 and len(out[-2]) > 2
               and self.is_runt(out[-1], longest, font_size)):
            out[-1].insert(0, out[-2].pop())
        return out

    def is_runt(self, line, longest, font_size):
        if not line:
            return False
        if len(line) == 1:
            return True
        if longest is None or font_size is None:
            return False
        return self.line_width(line, font_size) < longest * self.design.BACK_RUNT_FRACTION

    def line_width(self, line_words, font_size):
        regular_space = self.measure(' ', PLAIN, font_size)
        bold_space = self.measure(' ', 'b', font_size)
        total = 0.0
        for index, (style, word) in enumerate(line_words):
            leading_punctuation = bool(word) and word[0] in LEADING_PUNCTUATION
            if index > 0 and not leading_punctuation:
                total += bold_space if 'b' in style else regular_space
            total += self.measure(word, style, font_size)
        return total

    def record_box(self, x, baseline, width, font_size):
        self.line_boxes.append((x, baseline - ASCENT_EM * font_size, x + width,
                                baseline + DESCENT_EM * font_size))

    def line(self, x, y, line_words, font_size, color, base_weight=400, base_style='normal'):
        design = self.design
        self.record_box(x, y, self.line_width(line_words, font_size), font_size)
        italic_font = design.BODY_ITALIC_FONT or design.BODY_FONT
        svg = (f'<text x="{x}" y="{y}" xml:space="preserve" '
               f'font-family="{design.BODY_FONT}" font-size="{font_size}" '
               f'fill="{color}">')
        for index, (style, word) in enumerate(line_words):
            weight = design.BACK_BOLD_WEIGHT if 'b' in style else base_weight
            span_style = 'italic' if 'i' in style else base_style
            leading_punctuation = bool(word) and word[0] in LEADING_PUNCTUATION
            prefix = '' if (index == 0 or leading_punctuation) else ' '
            family = (f' font-family="{italic_font}"'
                      if span_style == 'italic' and italic_font != design.BODY_FONT else '')
            svg += (f'<tspan font-weight="{weight}" font-style="{span_style}"{family}>'
                    f'{prefix}{escape(word)}</tspan>')
        return svg + '</text>\n'


def to_runs(content):
    if isinstance(content, str):
        return [(PLAIN, content)]
    return content


def starts_sentence(word):
    return bool(word) and word[0].isupper() and word.lower() != 'i'


def ends_sentence(word):
    return bool(word) and word.rstrip('"\')]}').endswith(('.', '!', '?'))
