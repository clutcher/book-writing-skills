import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass

from check_output import ADVISORY, DEFECT, INFORMATIONAL
from cover_geometry import (BARCODE_HEIGHT_INCHES, BARCODE_INSET_INCHES, BARCODE_WIDTH_INCHES,
                        FEWEST_PAGES_FOR_SPINE_TEXT, SPINE_TEXT_EDGE_INCHES)

LAYOUT_CLASSES = {
    'back-text-past-safe-area': DEFECT,
    'back-text-in-barcode-area': DEFECT,
    'front-text-past-safe-area': DEFECT,
    'spine-text-not-allowed': DEFECT,
    'spine-text-too-wide': DEFECT,
    'spine-text-may-run-long': ADVISORY,
    'spine-text-scaled': INFORMATIONAL,
}
TEXT_TAGS = ('text', 'tspan')


@dataclass(frozen=True)
class LayoutFinding:
    key: str
    finding_class: str
    message: str


@dataclass(frozen=True)
class Box:
    left: float
    top: float
    right: float
    bottom: float

    def overlaps(self, other):
        return (self.left < other.right and other.left < self.right
                and self.top < other.bottom and other.top < self.bottom)

    def outside_of(self, other):
        return (self.left < other.left or self.right > other.right
                or self.top < other.top or self.bottom > other.bottom)


def placed_boxes(wrap, part):
    return [Box(*placed.box) for placed in wrap.design.placed_texts[part]]


def front_safe_area(wrap):
    return Box(wrap.safe, wrap.bleed + wrap.safe, wrap.trim_width - wrap.safe,
               wrap.bleed + wrap.trim_height - wrap.safe)


def back_safe_area(wrap):
    return Box(wrap.back_trim_x + wrap.safe, wrap.back_trim_y + wrap.safe,
               wrap.back_trim_x + wrap.trim_width - wrap.safe,
               wrap.back_trim_y + wrap.trim_height - wrap.safe)


def barcode_area(wrap):
    right = wrap.back_trim_x + wrap.trim_width - wrap.inches(BARCODE_INSET_INCHES)
    bottom = wrap.back_trim_y + wrap.trim_height - wrap.inches(BARCODE_INSET_INCHES)
    return Box(right - wrap.inches(BARCODE_WIDTH_INCHES),
               bottom - wrap.inches(BARCODE_HEIGHT_INCHES), right, bottom)


def back_findings(wrap):
    boxes = placed_boxes(wrap, 'back')
    safe = back_safe_area(wrap)
    barcode = barcode_area(wrap)
    findings = []
    outside = [box for box in boxes if box.outside_of(safe)]
    if outside:
        lowest = max(box.bottom for box in outside)
        findings.append(LayoutFinding(
            'back', 'back-text-past-safe-area',
            f'{len(outside)} line(s) of the back text leave the safe area '
            f'({safe.left:.0f}-{safe.right:.0f} x {safe.top:.0f}-{safe.bottom:.0f} px); the '
            f'lowest ends at y={lowest:.0f}: shorten the text or make it smaller'))
    in_barcode = [box for box in boxes if box.overlaps(barcode)]
    if in_barcode:
        findings.append(LayoutFinding(
            'back', 'back-text-in-barcode-area',
            f'{len(in_barcode)} line(s) of the back text enter the KDP barcode area '
            f'({BARCODE_WIDTH_INCHES} x {BARCODE_HEIGHT_INCHES} in, bottom right); KDP prints '
            f'the barcode over them'))
    return findings


def front_findings(wrap):
    safe = front_safe_area(wrap)
    outside = [placed for placed in wrap.design.placed_texts['front']
               if Box(*placed.box).outside_of(safe)]
    if not outside:
        return []
    names = ', '.join(f'"{placed.content}"' for placed in outside)
    return [LayoutFinding(
        'front', 'front-text-past-safe-area',
        f'{len(outside)} placed text(s) on the front leave the safe area '
        f'({safe.left:.0f}-{safe.right:.0f} x {safe.top:.0f}-{safe.bottom:.0f} px in front '
        f'panel coordinates): {names}; move them in or make them smaller')]


def spine_font_sizes(fragment):
    root = ElementTree.fromstring(f'<g>{fragment}</g>'.encode('utf-8'))
    parents = {child: parent for parent in root.iter() for child in parent}
    sizes = []
    for element in root.iter():
        if element.tag.rsplit('}', 1)[-1] not in TEXT_TAGS:
            continue
        holder = element
        while holder is not None and 'font-size' not in holder.attrib:
            holder = parents.get(holder)
        try:
            sizes.append(float(str(holder.attrib['font-size']).replace('px', ''))
                         if holder is not None else 0.0)
        except ValueError:
            sizes.append(0.0)
    return sizes


def spine_findings(wrap):
    sizes = spine_font_sizes(wrap.design.draw('spine', wrap))
    if not sizes:
        return []
    if not wrap.size.spine_text_allowed:
        return [LayoutFinding('spine', 'spine-text-not-allowed',
                              f'the spine has text, but KDP prints spine text only on books '
                              f'with {FEWEST_PAGES_FOR_SPINE_TEXT} or more pages; this one has '
                              f'{wrap.size.page_count}')]
    findings = []
    edge = wrap.inches(SPINE_TEXT_EDGE_INCHES)
    largest = max(sizes)
    if largest + 2 * edge > wrap.spine_width:
        findings.append(LayoutFinding(
            'spine', 'spine-text-too-wide',
            f'spine type of {largest:.1f} px plus {edge} px from each edge needs '
            f'{largest + 2 * edge:.0f} px, but the spine is {wrap.spine_width} px wide: make the '
            f'spine type smaller'))
    top = wrap.bleed + wrap.safe
    bottom = wrap.height - wrap.bleed - wrap.safe
    for text in wrap.design.spine_texts:
        if text.font_size < text.designed_size:
            findings.append(LayoutFinding(
                f'spine-{text.role}', 'spine-text-scaled',
                f'the spine {text.role} was made smaller, from {text.designed_size:.0f} px to '
                f'{text.font_size:.1f} px, to fit a {wrap.spine_width} px spine'))
        start = text.centre_y - text.estimated_length / 2
        end = text.centre_y + text.estimated_length / 2
        if start < top or end > bottom:
            findings.append(LayoutFinding(
                f'spine-{text.role}', 'spine-text-may-run-long',
                f'the spine {text.role} is about {text.estimated_length:.0f} px long and may run '
                f'from y={start:.0f} to y={end:.0f}, past the safe area ({top}-{bottom} px); '
                f'the length is an estimate from the body width table, so look at the spine '
                f'panel'))
    for placed in wrap.design.placed_texts['spine']:
        box = Box(*placed.box)
        if box.top < top or box.bottom > bottom:
            findings.append(LayoutFinding(
                f'spine:{placed.content}', 'spine-text-may-run-long',
                f'the spine text "{placed.content}" may run from y={box.top:.0f} to '
                f'y={box.bottom:.0f}, past the safe area ({top}-{bottom} px); the length is an '
                f'estimate from the body width table, so look at the spine panel'))
    return findings


def layout_findings(wrap):
    wrap.render('wrap')
    return back_findings(wrap) + spine_findings(wrap) + front_findings(wrap)
