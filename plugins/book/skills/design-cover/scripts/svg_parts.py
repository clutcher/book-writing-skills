XML_HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n'


def escape(text):
    return (text.replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def rect(x, y, width, height, fill, opacity=1.0, corner_radius=0):
    radius = f' rx="{corner_radius}"' if corner_radius else ''
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}"'
            f'{radius} fill="{fill}" opacity="{opacity}"/>')


def line(x1, y1, x2, y2, stroke, stroke_width, opacity=1.0):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
            f'stroke-width="{stroke_width}" opacity="{opacity}"/>')


def text(x, y, content, font_family, font_size, fill, anchor='start', weight=500,
         style='normal', letter_spacing=0, opacity=1.0, extra=''):
    return (f'<text x="{x}" y="{y}" font-family="{font_family}" font-size="{font_size}" '
            f'font-weight="{weight}" font-style="{style}" fill="{fill}" text-anchor="{anchor}" '
            f'letter-spacing="{letter_spacing}" opacity="{opacity}"{extra}>{escape(content)}</text>')


def spaced_name(words, separator=None, separator_lift=0):
    if not separator:
        return escape(' '.join(words))
    last = len(words) - 1
    parts = []
    for index, word in enumerate(words):
        trailing = ' ' if index < last else ''
        if index == 0:
            parts.append(f'<tspan>{escape(word)}{trailing}</tspan>')
            continue
        parts.append(f'<tspan dy="{separator_lift}">{escape(separator)}</tspan>')
        parts.append(f'<tspan dy="{-separator_lift}"> {escape(word)}{trailing}</tspan>')
    return ''.join(parts)


def hex_to_rgb(value):
    digits = value.lstrip('#')
    if len(digits) == 3:
        digits = ''.join(digit * 2 for digit in digits)
    return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16))


def blend_over_white(rgb, alpha):
    return 'rgb(%d,%d,%d)' % tuple(int(round(255 + (channel - 255) * alpha)) for channel in rgb)


def mix(first, second, amount):
    return tuple(first[index] + (second[index] - first[index]) * amount for index in range(3))


def smooth_step(value):
    return value * value * (3 - 2 * value)


def noise_value(step, seed):
    number = step * 1327 + seed * 7919
    number = ((number << 13) ^ number) & 0xFFFFFFFF
    number = (number * (number * number * 15731 + 789221) + 1376312589) & 0x7FFFFFFF
    return (number / 1073741824.0) - 1.0


def polyline_path(points, stroke, stroke_width, line_cap='round'):
    path = f'M {points[0][0]:.1f} {points[0][1]:.1f}'
    for x, y in points[1:]:
        path += f' L {x:.1f} {y:.1f}'
    return (f'<path d="{path}" fill="none" stroke="{stroke}" '
            f'stroke-width="{stroke_width}" stroke-linecap="{line_cap}"/>')
