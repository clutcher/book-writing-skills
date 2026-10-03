import re
from pathlib import Path

PARAGRAPH = 'para'
EMPHASIS = 'para_emphasis'
NARROW = 'para_narrow'
EMPHASIS_NARROW = 'para_emphasis_narrow'
HEADING = 'heading'
BULLET = 'bullet'
SPACE = 'spacer'
BLOCK_KINDS = (PARAGRAPH, EMPHASIS, NARROW, EMPHASIS_NARROW, HEADING, BULLET, SPACE)

PLAIN = 'n'
BOLD = 'b'
ITALIC = 'i'
BOLD_ITALIC = 'bi'
LINE_BREAK = 'BR'

SPACE_COMMENT = re.compile(r'<!--\s*(?:gap|space)\s+(\d+)\s*-->')
SPACE_MARK = re.compile(r'^\x00space (\d+)\x00$')
ANY_COMMENT = re.compile(r'<!--.*?-->', re.DOTALL)
FILE_TITLE = re.compile(r'^#\s+')
HEADING_LINE = re.compile(r'^#{2,6}\s+(.*?)\s*#*$')
BULLET_LINE = re.compile(r'^[-*+]\s+(.*)$')
QUOTE_LINE = re.compile(r'^>\s?(.*)$')
INLINE_MARK = re.compile(r'(\*\*\*|\*\*|\*|(?<![^\W_])_{1,3}(?=\S)|(?<=\S)_{1,3}(?![^\W_]))')
WHOLE_ITALIC = re.compile(r'^(\*|_)(?!\1)(.+?)(?<!\1)\1$', re.DOTALL)


class BackCopyError(Exception):
    pass


def inline_runs(text):
    runs = []
    bold = italic = False
    pieces = INLINE_MARK.split(text)
    for piece in pieces:
        if piece in ('***', '___'):
            bold, italic = not bold, not italic
            continue
        if piece in ('**', '__'):
            bold = not bold
            continue
        if piece in ('*', '_'):
            italic = not italic
            continue
        if not piece:
            continue
        style = (BOLD if bold else '') + (ITALIC if italic else '')
        runs.append((style or PLAIN, piece))
    return merge_runs(runs)


def merge_runs(runs):
    merged = []
    for style, text in runs:
        if merged and merged[-1][0] == style and style != LINE_BREAK:
            merged[-1] = (style, merged[-1][1] + text)
        else:
            merged.append((style, text))
    return merged


def paragraph_runs(lines):
    runs = []
    for index, raw in enumerate(lines):
        text = raw.rstrip()
        hard_break = text.endswith('\\')
        if text.endswith('\\'):
            text = text[:-1].rstrip()
        if index > 0 and runs and runs[-1][0] != LINE_BREAK:
            runs.append((runs[-1][0], ' '))
        runs.extend(inline_runs(text))
        if hard_break and index < len(lines) - 1:
            runs.append((LINE_BREAK, ''))
    return [run for run in merge_runs(runs) if run[0] == LINE_BREAK or run[1].strip()]


def whole_italic(lines):
    joined = ' '.join(line.rstrip('\\').strip() for line in lines)
    match = WHOLE_ITALIC.match(joined)
    if match and '*' not in match.group(2) and '_' not in match.group(2):
        return match.group(2)
    return None


def paragraph_block(lines, narrow):
    italic_text = whole_italic(lines)
    if italic_text is not None:
        return (EMPHASIS_NARROW if narrow else EMPHASIS, [(PLAIN, italic_text)])
    runs = paragraph_runs(lines)
    if narrow and all(style == PLAIN for style, _ in runs) and len(runs) == 1:
        return (NARROW, runs[0][1])
    return (NARROW if narrow else PARAGRAPH, runs)


def parse_back_copy(text):
    blocks = []
    paragraph = []
    quoted = []

    def flush():
        if paragraph:
            blocks.append(paragraph_block(list(paragraph), False))
            paragraph.clear()
        if quoted:
            blocks.append(paragraph_block(list(quoted), True))
            quoted.clear()

    text = SPACE_COMMENT.sub(lambda match: f'\n\x00space {match.group(1)}\x00\n', text)
    text = ANY_COMMENT.sub('', text)
    for raw in text.splitlines():
        stripped = raw.strip()
        space = SPACE_MARK.match(stripped)
        if space:
            flush()
            blocks.append((SPACE, int(space.group(1))))
            continue
        if not stripped:
            flush()
            continue
        if FILE_TITLE.match(stripped):
            flush()
            continue
        heading = HEADING_LINE.match(stripped)
        if heading:
            flush()
            blocks.append((HEADING, heading.group(1)))
            continue
        bullet = BULLET_LINE.match(stripped)
        if bullet:
            flush()
            runs = inline_runs(bullet.group(1))
            if len(runs) == 1 and runs[0][0] == PLAIN:
                blocks.append((BULLET, runs[0][1]))
            else:
                blocks.append((BULLET, runs))
            continue
        quote = QUOTE_LINE.match(stripped)
        if quote:
            if paragraph:
                flush()
            if quote.group(1).strip():
                quoted.append(quote.group(1).strip())
            else:
                flush()
            continue
        if quoted:
            flush()
        paragraph.append(stripped)
    flush()
    return blocks


def read_back_copy(path):
    path = Path(path)
    try:
        return parse_back_copy(path.read_text(encoding='utf-8'))
    except OSError as error:
        raise BackCopyError(f'cannot read the back-cover text {path}: {error}')


def plain_text(blocks):
    lines = []
    for kind, content in blocks:
        if kind == SPACE:
            continue
        if isinstance(content, str):
            lines.append(content)
        else:
            lines.append(''.join(' ' if style == LINE_BREAK else text for style, text in content))
    return '\n\n'.join(lines)
