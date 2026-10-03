import json
import struct
from dataclasses import dataclass, field
from pathlib import Path

FACE_NAMES = ('regular', 'bold', 'italic')
BOLD_FLAG = 'b'
ITALIC_FLAG = 'i'
DEFAULT_CHARACTERS = (''.join(chr(code) for code in range(32, 127))
                      + '‘’“”–—•·… ')
BULLET = '•'
LETTERS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'


class FontFileError(Exception):
    pass


@dataclass
class FaceWidths:
    widths: dict
    default: float

    def measure(self, text, font_size):
        return sum(self.widths.get(character, self.default) for character in text) * font_size


@dataclass
class BodyWidths:
    faces: dict
    font: str = ''
    bullet_ink_centre_em: float = None
    source: str = ''

    def face(self, style):
        if BOLD_FLAG in style:
            return self.faces['bold']
        if ITALIC_FLAG in style:
            return self.faces['italic']
        return self.faces['regular']

    def measure(self, text, style, font_size):
        return self.face(style).measure(text, font_size)

    def as_dict(self):
        data = {'font': self.font, 'faces': {}}
        if self.bullet_ink_centre_em is not None:
            data['bullet_ink_centre_em'] = self.bullet_ink_centre_em
        for name in FACE_NAMES:
            face = self.faces[name]
            data['faces'][name] = {'default': face.default, 'widths': face.widths}
        return data


def read_body_widths(path):
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise FontFileError(f'cannot read the width table {path}: {error}')
    faces = {}
    for name in FACE_NAMES:
        face = (data.get('faces') or {}).get(name)
        if not face:
            raise FontFileError(f"the width table {path} has no '{name}' face")
        faces[name] = FaceWidths(dict(face['widths']), float(face['default']))
    return BodyWidths(faces, data.get('font', ''), data.get('bullet_ink_centre_em'), str(path))


def average_widths(default_em=0.5):
    face = FaceWidths({' ': default_em * 0.4}, default_em)
    return BodyWidths({name: face for name in FACE_NAMES}, 'average', None, 'built-in average')


@dataclass
class FontFile:
    path: Path
    tables: dict = field(default_factory=dict)
    data: bytes = b''

    @classmethod
    def open(cls, path):
        path = Path(path)
        try:
            data = path.read_bytes()
        except OSError as error:
            raise FontFileError(f'cannot read the font {path}: {error}')
        if len(data) < 12:
            raise FontFileError(f'{path} is not a font file')
        count = struct.unpack('>H', data[4:6])[0]
        tables = {}
        for index in range(count):
            start = 12 + index * 16
            tag, _checksum, offset, length = struct.unpack('>4sIII', data[start:start + 16])
            tables[tag.decode('latin-1')] = (offset, length)
        font = cls(path, tables, data)
        for required in ('head', 'hhea', 'hmtx', 'cmap', 'maxp'):
            if required not in tables:
                raise FontFileError(f"{path} has no '{required}' table")
        return font

    def _table(self, tag):
        offset, length = self.tables[tag]
        return self.data[offset:offset + length]

    @property
    def units_per_em(self):
        return struct.unpack('>H', self._table('head')[18:20])[0]

    def advances(self):
        metric_count = struct.unpack('>H', self._table('hhea')[34:36])[0]
        glyph_count = struct.unpack('>H', self._table('maxp')[4:6])[0]
        table = self._table('hmtx')
        advances = [struct.unpack('>H', table[index * 4:index * 4 + 2])[0]
                    for index in range(metric_count)]
        last = advances[-1] if advances else 0
        return advances + [last] * max(0, glyph_count - metric_count)

    def character_map(self):
        table = self._table('cmap')
        count = struct.unpack('>H', table[2:4])[0]
        best = None
        for index in range(count):
            platform, encoding, offset = struct.unpack('>HHI', table[4 + index * 8:12 + index * 8])
            subtable_format = struct.unpack('>H', table[offset:offset + 2])[0]
            rank = {(3, 10): 3, (0, 4): 3, (3, 1): 2, (0, 3): 2}.get((platform, encoding), 1)
            if subtable_format in (4, 12) and (best is None or rank > best[0]):
                best = (rank, offset, subtable_format)
        if best is None:
            raise FontFileError(f'{self.path} has no Unicode character map this reader knows')
        _rank, offset, subtable_format = best
        if subtable_format == 4:
            return self._format_four(table, offset)
        return self._format_twelve(table, offset)

    @staticmethod
    def _format_four(table, offset):
        segment_count = struct.unpack('>H', table[offset + 6:offset + 8])[0] // 2
        ends_at = offset + 14
        starts_at = ends_at + segment_count * 2 + 2
        deltas_at = starts_at + segment_count * 2
        ranges_at = deltas_at + segment_count * 2
        mapping = {}
        for segment in range(segment_count):
            end = struct.unpack('>H', table[ends_at + segment * 2:ends_at + segment * 2 + 2])[0]
            start = struct.unpack('>H', table[starts_at + segment * 2:starts_at + segment * 2 + 2])[0]
            delta = struct.unpack('>h', table[deltas_at + segment * 2:deltas_at + segment * 2 + 2])[0]
            range_offset_at = ranges_at + segment * 2
            range_offset = struct.unpack('>H', table[range_offset_at:range_offset_at + 2])[0]
            for code in range(start, end + 1):
                if code == 0xFFFF:
                    continue
                if range_offset == 0:
                    glyph = (code + delta) & 0xFFFF
                else:
                    glyph_at = range_offset_at + range_offset + (code - start) * 2
                    glyph = struct.unpack('>H', table[glyph_at:glyph_at + 2])[0]
                    if glyph:
                        glyph = (glyph + delta) & 0xFFFF
                if glyph:
                    mapping[code] = glyph
        return mapping

    @staticmethod
    def _format_twelve(table, offset):
        group_count = struct.unpack('>I', table[offset + 12:offset + 16])[0]
        mapping = {}
        for group in range(group_count):
            at = offset + 16 + group * 12
            start, end, first_glyph = struct.unpack('>III', table[at:at + 12])
            for code in range(start, end + 1):
                mapping[code] = first_glyph + code - start
        return mapping

    def glyph_vertical_bounds(self, glyph):
        if 'glyf' not in self.tables or 'loca' not in self.tables:
            return None
        long_offsets = struct.unpack('>h', self._table('head')[50:52])[0] == 1
        loca = self._table('loca')
        if long_offsets:
            start, end = struct.unpack('>II', loca[glyph * 4:glyph * 4 + 8])
        else:
            start, end = (value * 2 for value in struct.unpack('>HH', loca[glyph * 2:glyph * 2 + 4]))
        if end <= start:
            return None
        glyf = self._table('glyf')
        _contours, _x_min, y_min, _x_max, y_max = struct.unpack('>hhhhh', glyf[start:start + 10])
        return y_min, y_max

    def face_widths(self, characters=DEFAULT_CHARACTERS, decimals=3):
        units = self.units_per_em
        advances = self.advances()
        mapping = self.character_map()
        widths = {}
        for character in characters:
            glyph = mapping.get(ord(character))
            if glyph is not None and glyph < len(advances):
                widths[character] = round(advances[glyph] / units, decimals)
        letters = [advances[mapping[ord(letter)]] / units for letter in LETTERS
                   if ord(letter) in mapping]
        default = round(sum(letters) / len(letters), decimals) if letters else 0.5
        return FaceWidths(widths, default)

    def bullet_ink_centre_em(self, decimals=3):
        glyph = self.character_map().get(ord(BULLET))
        if glyph is None:
            return None
        bounds = self.glyph_vertical_bounds(glyph)
        if bounds is None:
            return None
        return round((bounds[0] + bounds[1]) / 2 / self.units_per_em, decimals)
