import io
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
FIXTURE_BOOK = Path(__file__).resolve().parent / 'fixtures' / 'book'
KDP_ANSWERS = Path(__file__).resolve().parent / 'fixtures' / 'kdp'
OWN_PANELS_DESIGN = Path(__file__).resolve().parent / 'fixtures' / 'own-panels' / 'design.py'
sys.path.insert(0, str(SCRIPTS.parents[2] / 'lib'))
sys.path.insert(0, str(SCRIPTS))

from back_copy_text import (BULLET, EMPHASIS_NARROW, HEADING, LINE_BREAK, NARROW, PARAGRAPH, SPACE,
                       inline_runs, parse_back_copy, read_back_copy)
from cover_settings import choose_print_pdf
from cover_tools import is_pinned_image
from back_layout import BackTypesetter
from cover_design import CoverDesign
from cover_geometry import CoverSize, CoverSizeError, parse_trim
from kdp_download import (NEW, REPLACED, SAME, TemplateAnswerError, TemplateRequest,
                          download_address_from_answer, store_templates, templates_in_archive)
from text_width import BodyWidths, FaceWidths, FontFile

COMMAND_SCRIPTS = ('make.py', 'overlay.py', 'color-check.py', 'font-check.py', 'compare.py',
                   'font-widths.py', 'cover-size.py', 'back-copy.py', 'layout-check.py',
                   'self-check.py', 'kdp-template.py')
HAS_RENDERER = bool(shutil.which('rsvg-convert') or shutil.which('cairosvg'))
HAS_IMAGE_TOOL = bool(shutil.which('magick') or (shutil.which('convert')
                                                  and shutil.which('compare')))
LONG_BACK_TEXT = '\n\n'.join(
    'A long paragraph that keeps going so that the back panel fills up well past its end, '
    'line after line after line, the way a blurb that nobody measured would.'
    for _ in range(40))
FIXED_SPINE = '''

    def spine(self, wrap):
        centre = wrap.spine_x + wrap.spine_width // 2
        return text(centre, 900, 'FIXED', self.DISPLAY_FONT, 90, self.TITLE_COLOR)
'''

CUSTOM_BACK = '''

    def back(self, wrap):
        left = wrap.back_trim_x + wrap.inches(0.75)
        svg = self.place_text(left, wrap.back_trim_y + 400, 'Read this first', self.DISPLAY_FONT,
                              60, self.TITLE_COLOR)
        right = wrap.back_trim_x + wrap.trim_width - wrap.inches(0.75)
        return svg + self.place_text(right, wrap.height - wrap.inches(0.6), 'Small print here',
                                     self.BODY_FONT, 40, self.BODY_COLOR, anchor='end')
'''
LONG_CUSTOM_SPINE = '''

    def spine(self, wrap):
        centre = wrap.spine_x + wrap.spine_width / 2
        return self.place_text(centre, wrap.height / 2, 'A SPINE LINE ' * 16, self.DISPLAY_FONT,
                               30, self.TITLE_COLOR, anchor='middle', turn=90)
'''
NO_NETWORK = {'https_proxy': 'http://127.0.0.1:9', 'HTTPS_PROXY': 'http://127.0.0.1:9',
              'no_proxy': '', 'NO_PROXY': ''}


def run_script(name, *arguments, cwd, environment=None):
    return subprocess.run([sys.executable, str(SCRIPTS / name), *arguments],
                          capture_output=True, encoding='utf-8', errors='replace', cwd=cwd,
                          env={**os.environ, **(environment or {})})


def copy_fixture_book(folder):
    target = Path(folder) / 'book'
    shutil.copytree(FIXTURE_BOOK, target)
    return target


def write_blank_png(path, width, height):
    row = b'\x00' + b'\x00' * (width * 4)
    compressed = zlib.compress(row * height, 9)

    def chunk(kind, data):
        return (struct.pack('>I', len(data)) + kind + data
                + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF))

    header = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header)
                           + chunk(b'IDAT', compressed) + chunk(b'IEND', b''))


def build_small_font(path):
    advances = [(500, 0), (600, 0), (250, 0)]
    head = bytearray(54)
    struct.pack_into('>H', head, 18, 1000)
    hhea = bytearray(36)
    struct.pack_into('>H', hhea, 34, len(advances))
    maxp = struct.pack('>IH', 0x00005000, len(advances))
    hmtx = b''.join(struct.pack('>Hh', advance, bearing) for advance, bearing in advances)
    ends, starts, deltas = [32, 65, 0xFFFF], [32, 65, 0xFFFF], [(2 - 32) & 0xFFFF,
                                                               (1 - 65) & 0xFFFF, 1]
    segments = len(ends)
    subtable = struct.pack('>HHHHHHH', 4, 16 + segments * 8, 0, segments * 2, 4, 1, 2)
    subtable += b''.join(struct.pack('>H', value) for value in ends) + b'\x00\x00'
    subtable += b''.join(struct.pack('>H', value) for value in starts)
    subtable += b''.join(struct.pack('>H', value) for value in deltas)
    subtable += b'\x00\x00' * segments
    cmap = struct.pack('>HHHHI', 0, 1, 3, 1, 12) + subtable
    tables = {'cmap': cmap, 'head': bytes(head), 'hhea': bytes(hhea), 'hmtx': hmtx,
              'maxp': maxp}
    offset = 12 + 16 * len(tables)
    directory = struct.pack('>IHHHH', 0x00010000, len(tables), 0, 0, 0)
    body = b''
    for tag, data in tables.items():
        directory += struct.pack('>4sIII', tag.encode(), 0, offset + len(body), len(data))
        body += data + b'\x00' * ((4 - len(data) % 4) % 4)
    Path(path).write_bytes(directory + body)


class CoverSizeTest(unittest.TestCase):
    def test_should_match_the_kdp_template_size_when_given_a_standard_trim(self):
        # given
        size = CoverSize(234, 'bw-white', 6.14, 9.21)

        # when
        full = (size.width_px, size.height_px)

        # then
        self.assertEqual(full, (3917, 2838))
        self.assertEqual(size.spine_width_px, 158)

    def test_should_widen_the_spine_when_the_paper_is_cream(self):
        # given
        white = CoverSize(100, 'bw-white', 6, 9)
        cream = CoverSize(100, 'bw-cream', 6, 9)

        # when
        difference = cream.spine_width_px - white.spine_width_px

        # then
        self.assertEqual(cream.spine_width_px, 75)
        self.assertEqual(difference, 7)

    def test_should_refuse_spine_text_when_the_book_is_thin(self):
        # given
        thin = CoverSize(60, 'bw-white', 5, 8)

        # when
        allowed = thin.spine_text_allowed

        # then
        self.assertFalse(allowed)

    def test_should_read_the_trim_when_written_with_inches(self):
        # given
        written = '6.14in x 9.21in'

        # when
        trim = parse_trim(written)

        # then
        self.assertEqual(trim, (6.14, 9.21))

    def test_should_refuse_an_unknown_paper(self):
        # given
        paper = 'glossy-art'

        # when
        def make_size():
            return CoverSize(100, paper, 6, 9)

        # then
        self.assertRaises(CoverSizeError, make_size)

    def test_should_allow_spine_text_only_when_the_book_has_more_than_79_pages(self):
        # given
        at_limit = CoverSize(79, 'bw-white', 6, 9)
        over_limit = CoverSize(80, 'bw-white', 6, 9)

        # when
        allowed = (at_limit.spine_text_allowed, over_limit.spine_text_allowed)

        # then
        self.assertEqual(allowed, (False, True))


class BackCopyTest(unittest.TestCase):
    def test_should_read_every_block_kind_when_given_the_fixture_back_cover(self):
        # given
        path = FIXTURE_BOOK / 'sales-text' / 'back-cover.md'

        # when
        blocks = read_back_copy(path)

        # then
        self.assertEqual([kind for kind, _ in blocks],
                         [PARAGRAPH, PARAGRAPH, PARAGRAPH, HEADING, BULLET, BULLET, NARROW,
                          SPACE, EMPHASIS_NARROW])
        self.assertEqual(blocks[1][1][0], ('b', 'A bold lead-in.'))
        self.assertIn((LINE_BREAK, ''), blocks[2][1])
        self.assertEqual(blocks[5][1][1], ('i', 'one italic word'))
        self.assertEqual(blocks[7], (SPACE, 40))

    def test_should_skip_notes_when_written_as_comments(self):
        # given
        text = 'First line.\n<!-- a note for the author\n     over two lines -->\n\nSecond.'

        # when
        blocks = parse_back_copy(text)

        # then
        self.assertEqual(blocks, [(PARAGRAPH, [('n', 'First line.')]),
                                  (PARAGRAPH, [('n', 'Second.')])])


    def test_should_keep_an_underscore_plain_when_it_sits_inside_a_word(self):
        # given
        text = 'name it snake_case, not _this_'

        # when
        runs = inline_runs(text)

        # then
        self.assertEqual(runs, [('n', 'name it snake_case, not '), ('i', 'this')])


class RenderImageTest(unittest.TestCase):
    def test_should_accept_only_a_pinned_render_image(self):
        # given
        images = ['example/rsvg:2.58', 'example/rsvg', 'example/rsvg:latest',
                  'registry:5000/rsvg', 'example/rsvg@sha256:abc']

        # when
        pinned = [is_pinned_image(image) for image in images]

        # then
        self.assertEqual(pinned, [True, False, False, False, True])


class TextWidthTest(unittest.TestCase):
    def test_should_read_advance_widths_when_given_a_font_file(self):
        # given
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder)
        build_small_font(folder / 'small.ttf')

        # when
        widths = FontFile.open(folder / 'small.ttf').face_widths('A ')

        # then
        self.assertEqual(widths.widths, {'A': 0.6, ' ': 0.25})
        self.assertEqual(widths.default, 0.6)


class BackLayoutTest(unittest.TestCase):
    def typesetter(self):
        face = FaceWidths({' ': 0.25}, 0.5)
        widths = BodyWidths({'regular': face, 'bold': face, 'italic': face})
        return BackTypesetter(CoverDesign(None), widths)

    def test_should_pull_a_word_down_when_the_last_line_is_a_runt(self):
        # given
        runs = [('n', 'aaaa bbbb cccc dddd eeee ffff g')]

        # when
        lines = self.typesetter().wrap_runs(runs, 100, 10)

        # then
        self.assertGreaterEqual(len(lines[-1]), 2)

    def test_should_break_the_line_when_the_copy_asks_for_it(self):
        # given
        runs = [('b', 'one two'), (LINE_BREAK, ''), ('b', 'three')]

        # when
        lines = self.typesetter().wrap_runs(runs, 1000, 10)

        # then
        self.assertEqual([[word for _, word in line] for line in lines],
                         [['one', 'two'], ['three']])


def zip_with(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def refuses_answer(read, answer):
    try:
        read(answer)
    except TemplateAnswerError:
        return True
    return False


class KdpTemplateTest(unittest.TestCase):
    def test_should_find_the_download_address_when_kdp_answers_as_expected(self):
        # given
        answer = (KDP_ANSWERS / 'download-answer.json').read_text(encoding='utf-8')

        # when
        address = download_address_from_answer(answer)

        # then
        self.assertTrue(address.startswith('https://'))
        self.assertIn('PAPERBACK_6.000x9.000_120_BW_WHITE_en_US.zip', address)

    def test_should_stop_when_the_kdp_answer_changed_shape(self):
        # given
        answers = [(KDP_ANSWERS / 'changed-answer.json').read_text(encoding='utf-8'),
                   '<html>Sign in</html>', '{"actions": []}']

        # when
        refused = [refuses_answer(download_address_from_answer, answer) for answer in answers]

        # then
        self.assertEqual(refused, [True, True, True])

    def test_should_ask_for_the_book_trim_pages_and_paper(self):
        # given
        request = TemplateRequest(6.14, 9.21, 277, 'bw-white')

        # when
        form = request.form()

        # then
        self.assertEqual(form['trimSize'], '6_14X9_21IN')
        self.assertEqual((form['paperType'], form['interiorType'], form['pageCount']),
                         ('WHITE', 'BLACK_AND_WHITE', '277'))
        self.assertEqual(request.file_names(),
                         ['PAPERBACK_6.140x9.210_277_BW_WHITE_en_US.png',
                          'PAPERBACK_6.140x9.210_277_BW_WHITE_en_US.pdf'])

    def test_should_name_each_paper_the_way_kdp_names_it(self):
        # given
        papers = ['bw-white', 'bw-cream', 'color-premium', 'color-standard']

        # when
        asked = {paper: TemplateRequest(5.5, 8.5, 150, paper) for paper in papers}

        # then
        self.assertEqual(asked['color-premium'].form()['paperType'], 'COLOR')
        self.assertEqual(asked['color-standard'].form()['interiorType'], 'STANDARD_COLOR')
        self.assertEqual([request.file_stem for request in asked.values()],
                         ['PAPERBACK_5.500x8.500_150_BW_WHITE_en_US',
                          'PAPERBACK_5.500x8.500_150_BW_CREAM_en_US',
                          'PAPERBACK_5.500x8.500_150_PREMIUM_WHITE_en_US',
                          'PAPERBACK_5.500x8.500_150_STANDARD_WHITE_en_US'])
        self.assertEqual(TemplateRequest(6, 9, 120, 'bw-white').form()['trimSize'], '6X9IN')

    def test_should_keep_the_template_when_the_same_file_is_already_there(self):
        # given
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder)
        archive = zip_with({'PAPERBACK_6.000x9.000_120_BW_WHITE_en_US.png': b'png',
                            'PAPERBACK_6.000x9.000_120_BW_WHITE_en_US.pdf': b'pdf',
                            'readme.txt': b'read me'})

        # when
        first = store_templates(templates_in_archive(archive), folder)
        second = store_templates(templates_in_archive(archive), folder)
        changed = store_templates({'PAPERBACK_6.000x9.000_120_BW_WHITE_en_US.png': b'new'},
                                  folder)

        # then
        self.assertEqual([state for _, state in first], [NEW, NEW])
        self.assertEqual([state for _, state in second], [SAME, SAME])
        self.assertEqual([state for _, state in changed], [REPLACED])
        self.assertFalse((folder / 'readme.txt').exists())

    def test_should_refuse_a_download_with_no_template_picture(self):
        # given
        archives = [zip_with({'readme.txt': b'read me'}), b'not a zip']

        # when
        refused = [refuses_answer(templates_in_archive, archive) for archive in archives]

        # then
        self.assertEqual(refused, [True, True])


class PrintPdfChoiceTest(unittest.TestCase):
    def _output_folder(self, names_oldest_first):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder)
        for age_in_seconds, name in zip(range(len(names_oldest_first) * 10, 0, -10),
                                        names_oldest_first):
            path = folder / name
            path.write_bytes(b'pdf')
            moment = path.stat().st_mtime - age_in_seconds
            os.utime(path, (moment, moment))
        return folder

    def test_should_count_the_final_print_pdf_when_drafts_are_newer(self):
        # given
        folder = self._output_folder(['river-guide-jones.pdf',
                                      'river-guide-jones-draft-20300101_090000.pdf',
                                      'river-guide-jones-draft-20300102_090000.pdf',
                                      'river-guide-jones-digital.pdf'])

        # when
        chosen, why = choose_print_pdf(folder)

        # then
        self.assertEqual(chosen.name, 'river-guide-jones.pdf')
        self.assertIn('final', why)

    def test_should_count_the_newest_draft_when_there_is_no_final_print_pdf(self):
        # given
        folder = self._output_folder(['river-guide-jones-draft-20300101_090000.pdf',
                                      'river-guide-jones-draft-20300102_090000.pdf',
                                      'river-guide-jones-digital-draft-20300103_090000.pdf'])

        # when
        chosen, why = choose_print_pdf(folder)

        # then
        self.assertEqual(chosen.name, 'river-guide-jones-draft-20300102_090000.pdf')
        self.assertIn('newest', why)

    def test_should_find_nothing_when_the_folder_has_no_print_pdf(self):
        # given
        folder = self._output_folder(['river-guide-jones-digital.pdf'])

        # when
        chosen = choose_print_pdf(folder)

        # then
        self.assertIsNone(chosen)


class CommandTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.book = copy_fixture_book(self.folder)

    def test_should_answer_help_when_asked(self):
        # given
        scripts = COMMAND_SCRIPTS

        # when
        results = {name: run_script(name, '--help', cwd=self.book) for name in scripts}

        # then
        for name, result in results.items():
            self.assertEqual(result.returncode, 0, f'{name}: {result.stderr}')

    def test_should_write_every_panel_when_making_the_svg(self):
        # given
        output = self.book / '.book' / 'output' / 'cover' / 'svg'

        # when
        result = run_script('make.py', '--svg-only', cwd=self.book)

        # then
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(path.name for path in output.glob('*.svg')),
                         ['back-trim.svg', 'back.svg', 'front-trim.svg', 'front.svg',
                          'spine.svg', 'wrap.svg'])
        wrap = (output / 'wrap.svg').read_text(encoding='utf-8')
        size = CoverSize(120, 'bw-white', 6, 9)
        self.assertIn(f'width="{size.width_px}" height="{size.height_px}"', wrap)
        self.assertIn('What you will learn', (output / 'back.svg').read_text(encoding='utf-8'))
        self.assertIn('EXAMPLE', (output / 'spine.svg').read_text(encoding='utf-8'))

    def test_should_plan_the_template_download_without_writing_when_not_fixing(self):
        # given
        templates = self.book / '.book' / 'caches' / 'kdp-templates'

        # when
        result = run_script('kdp-template.py', '--format', 'tsv', cwd=self.book)

        # then
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('trimSize=6X9IN', result.stdout)
        self.assertIn('pageCount=120', result.stdout)
        self.assertIn('PAPERBACK_6.000x9.000_120_BW_WHITE_en_US.png\ttemplate-missing',
                      result.stdout)
        self.assertFalse(templates.exists())

    def test_should_report_low_contrast_when_type_is_pale(self):
        # given
        design = self.book / 'cover' / 'design.py'

        # when
        result = run_script('color-check.py', '--format', 'tsv', cwd=self.book)

        # then
        self.assertTrue(design.is_file())
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('SUBTITLE_COLOR=#DDDDDD\ttype-contrast-low', result.stdout)
        self.assertIn('UNUSED_COLOR=#123456\tnot-drawn', result.stdout)
        self.assertIn('BAND_COLOR=#2E6F95\tartwork-color', result.stdout)
        self.assertIn('TITLE_COLOR=#202020\ttype-color', result.stdout)

    @unittest.skipUnless(HAS_RENDERER, 'no SVG renderer installed')
    def test_should_flag_art_made_for_another_page_count(self):
        # given
        templates = self.book / 'templates'
        templates.mkdir()
        size = CoverSize(120, 'bw-white', 6, 9)
        write_blank_png(templates / 'PAPERBACK_6.000x9.000_120_BW_WHITE_en_US.png',
                        size.width_px * 2, size.height_px * 2)
        made = run_script('make.py', '--panel', 'wrap', '--no-download', cwd=self.book)

        # when
        same = run_script('overlay.py', '--templates', str(templates), '--format', 'tsv',
                          cwd=self.book)
        other = run_script('overlay.py', '--templates', str(templates), '--pages', '300',
                           '--format', 'tsv', cwd=self.book)

        # then
        self.assertEqual(made.returncode, 0, made.stderr)
        self.assertNotIn('art-size-wrong', same.stdout)
        self.assertNotIn('template-size-wrong', same.stdout)
        self.assertEqual(other.returncode, 1, other.stderr)
        self.assertIn('art-size-wrong', other.stdout)
        self.assertIn('template-nearest', other.stdout)

    @unittest.skipUnless(HAS_RENDERER and HAS_IMAGE_TOOL, 'no SVG renderer or ImageMagick')
    def test_should_write_the_overlay_image_only_when_asked(self):
        # given
        templates = self.book / 'templates'
        templates.mkdir()
        size = CoverSize(120, 'bw-white', 6, 9)
        write_blank_png(templates / 'PAPERBACK_6.000x9.000_120_BW_WHITE_en_US.png',
                        size.width_px * 2, size.height_px * 2)
        made = run_script('make.py', '--panel', 'wrap', '--no-download', cwd=self.book)
        overlay = next(self.book.rglob('wrap.png')).with_name('wrap-overlay.png')
        overlay.unlink(missing_ok=True)

        # when
        checked = run_script('overlay.py', '--templates', str(templates), '--format', 'tsv',
                             cwd=self.book)
        written_after_check = overlay.exists()
        fixed = run_script('overlay.py', '--templates', str(templates), '--fix',
                           '--format', 'tsv', cwd=self.book)

        # then
        self.assertEqual(made.returncode, 0, made.stderr)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertIn('overlay-not-written', checked.stdout)
        self.assertFalse(written_after_check)
        self.assertEqual(fixed.returncode, 0, fixed.stderr)
        self.assertIn('overlay-written', fixed.stdout)
        self.assertTrue(overlay.is_file())

    @unittest.skipUnless(HAS_RENDERER, 'no SVG renderer installed')
    def test_should_name_the_download_command_when_no_template_is_there(self):
        # given
        templates = self.book / 'templates'
        templates.mkdir()
        made = run_script('make.py', '--panel', 'wrap', '--no-download', cwd=self.book)

        # when
        result = run_script('overlay.py', '--templates', str(templates), cwd=self.book)

        # then
        self.assertEqual(made.returncode, 0, made.stderr)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('SKIPPED', result.stdout)
        self.assertIn('kdp-template.py --fix', result.stdout)

    def test_should_flag_back_text_when_it_runs_past_the_panel(self):
        # given
        (self.book / 'sales-text' / 'back-cover.md').write_text(LONG_BACK_TEXT, encoding='utf-8')

        # when
        checked = run_script('layout-check.py', '--format', 'tsv', cwd=self.book)
        made = run_script('make.py', '--svg-only', cwd=self.book)

        # then
        self.assertEqual(checked.returncode, 1, checked.stderr)
        self.assertIn('back-text-past-safe-area', checked.stdout)
        self.assertIn('back-text-in-barcode-area', checked.stdout)
        self.assertIn('note             back-text-past-safe-area', made.stdout)

    def test_should_pass_the_layout_when_the_back_text_fits(self):
        # given
        book = self.book

        # when
        result = run_script('layout-check.py', '--format', 'tsv', cwd=book)

        # then
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_should_leave_the_spine_empty_when_the_book_is_too_thin(self):
        # given
        spine = self.book / '.book' / 'output' / 'cover' / 'svg' / 'spine.svg'

        # when
        made = run_script('make.py', '--svg-only', '--pages', '60', cwd=self.book)
        checked = run_script('layout-check.py', '--pages', '60', '--format', 'tsv',
                             cwd=self.book)

        # then
        self.assertEqual(made.returncode, 0, made.stderr)
        self.assertNotIn('<text', spine.read_text(encoding='utf-8'))
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def use_fixed_spine(self):
        design = self.book / 'cover' / 'design.py'
        design.write_text(design.read_text(encoding='utf-8') + FIXED_SPINE, encoding='utf-8')

    def test_should_flag_spine_type_when_it_is_wider_than_the_spine(self):
        # given
        self.use_fixed_spine()

        # when
        result = run_script('layout-check.py', '--format', 'tsv', cwd=self.book)

        # then
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('spine-text-too-wide', result.stdout)

    def test_should_flag_spine_text_when_the_book_is_too_thin_for_it(self):
        # given
        self.use_fixed_spine()

        # when
        result = run_script('layout-check.py', '--pages', '60', '--format', 'tsv',
                            cwd=self.book)

        # then
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('spine-text-not-allowed', result.stdout)

    def test_should_shrink_the_default_spine_type_when_the_spine_is_narrow(self):
        # given
        book = self.book

        # when
        result = run_script('layout-check.py', '--format', 'tsv', cwd=book)

        # then
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('spine-title\tspine-text-scaled', result.stdout)

    def test_should_grade_type_color_written_without_a_constant(self):
        # given
        design = self.book / 'cover' / 'design.py'
        design.write_text(design.read_text(encoding='utf-8').replace(
            '        return svg\n',
            "        svg += text(150, 1200, 'small print', self.DISPLAY_FONT, 30, '#EEEEEE')\n"
            '        return svg\n'), encoding='utf-8')

        # when
        result = run_script('color-check.py', '--format', 'tsv', cwd=self.book)

        # then
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('untraced:#EEEEEE\ttype-contrast-low', result.stdout)

    def test_should_check_fonts_and_colors_when_the_page_count_is_unknown(self):
        # given
        config = self.book / 'book.yaml'
        config.write_text(config.read_text(encoding='utf-8').replace('  pages: 120\n', ''),
                          encoding='utf-8')

        # when
        colors = run_script('color-check.py', '--format', 'tsv', cwd=self.book)
        fonts = run_script('font-check.py', '--format', 'tsv', cwd=self.book)

        # then
        self.assertEqual(colors.returncode, 1, colors.stderr)
        self.assertIn('geometry-nominal', colors.stdout)
        self.assertNotEqual(fonts.returncode, 2, fonts.stderr)

    @unittest.skipUnless(HAS_RENDERER, 'no SVG renderer installed')
    def test_should_ship_nothing_until_asked_to_fix(self):
        # given
        final = self.book / 'cover' / 'final'

        # when
        dry = run_script('make.py', '--panel', 'front-trim', cwd=self.book)
        shipped_after_dry_run = sorted(final.glob('*')) if final.exists() else []
        fixed = run_script('make.py', '--panel', 'front-trim', '--fix', cwd=self.book)

        # then
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn('would ship', dry.stdout)
        self.assertEqual(shipped_after_dry_run, [])
        self.assertEqual(fixed.returncode, 0, fixed.stderr)
        self.assertTrue((final / 'front.png').is_file())

    @unittest.skipUnless(HAS_RENDERER and HAS_IMAGE_TOOL, 'no SVG renderer or ImageMagick')
    def test_should_show_the_new_front_alone_when_nothing_is_shipped_yet(self):
        # given
        run_script('make.py', '--panel', 'front-trim', cwd=self.book)

        # when
        result = run_script('compare.py', '--format', 'tsv', cwd=self.book)

        # then
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('nothing-shipped-yet', result.stdout)
        self.assertIn('thumbnails-180.png', result.stdout)

    def add_to_design(self, code):
        design = self.book / 'cover' / 'design.py'
        design.write_text(design.read_text(encoding='utf-8') + code, encoding='utf-8')

    def test_should_flag_text_placed_by_a_custom_back_when_it_enters_the_barcode_area(self):
        # given
        self.add_to_design(CUSTOM_BACK)

        # when
        result = run_script('layout-check.py', '--format', 'tsv', cwd=self.book)

        # then
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('back-text-in-barcode-area', result.stdout)
        self.assertNotIn('back-text-past-safe-area', result.stdout)

    def test_should_flag_text_placed_on_a_custom_spine_when_it_runs_long(self):
        # given
        self.add_to_design(LONG_CUSTOM_SPINE)

        # when
        result = run_script('layout-check.py', '--format', 'tsv', cwd=self.book)

        # then
        self.assertIn('spine-text-may-run-long', result.stdout)
        self.assertNotIn('spine-text-too-wide', result.stdout)

    def test_should_check_the_fixture_back_title_when_the_default_back_draws_it(self):
        # given
        config = self.book / 'book.yaml'
        config.write_text(config.read_text(encoding='utf-8').replace(
            'title: Plain Example Book',
            'title: Plain Example Book With A Title Far Too Long For The Back Panel'),
            encoding='utf-8')

        # when
        result = run_script('layout-check.py', '--format', 'tsv', cwd=self.book)

        # then
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('back-text-past-safe-area', result.stdout)

    @unittest.skipUnless(HAS_RENDERER and HAS_IMAGE_TOOL, 'no SVG renderer or ImageMagick')
    def test_should_make_a_design_that_draws_its_own_front_back_and_spine(self):
        # given
        shutil.copyfile(OWN_PANELS_DESIGN, self.book / 'cover' / 'design.py')
        templates = self.book / '.book' / 'caches' / 'kdp-templates'
        templates.mkdir(parents=True)
        size = CoverSize(120, 'bw-white', 6, 9)
        write_blank_png(templates / 'PAPERBACK_6.000x9.000_120_BW_WHITE_en_US.png',
                        size.width_px, size.height_px)
        made_png = self.book / '.book' / 'output' / 'cover' / 'png'

        # when
        made = run_script('make.py', '--no-download', cwd=self.book)
        checked = run_script('layout-check.py', '--format', 'tsv', cwd=self.book)

        # then
        self.assertEqual(made.returncode, 0, made.stderr)
        for name in ('wrap.png', 'front-trim.png', 'back-trim.png', 'spine.png', 'ebook.jpg',
                     'wrap-overlay.png'):
            self.assertTrue((made_png / name).is_file(), name)
        self.assertEqual(png_size_of(made_png / 'wrap.png'), (size.width_px, size.height_px))
        flagged = [row.split('\t')[1] for row in checked.stdout.splitlines() if '\t' in row]
        self.assertEqual(flagged, ['front-text-past-safe-area'])
        self.assertIn('ANA EXAMPLE', checked.stdout)

    @unittest.skipUnless(HAS_RENDERER and HAS_IMAGE_TOOL, 'no SVG renderer or ImageMagick')
    def test_should_still_make_the_cover_when_the_template_cannot_be_downloaded(self):
        # given
        templates = self.book / '.book' / 'caches' / 'kdp-templates'

        # when
        made = run_script('make.py', '--panel', 'wrap', cwd=self.book, environment=NO_NETWORK)

        # then
        self.assertEqual(made.returncode, 0, made.stderr)
        self.assertIn('KDP template not downloaded', made.stdout)
        self.assertIn('SKIPPED  KDP overlay', made.stdout)
        self.assertFalse(any(templates.glob('*.png')) if templates.exists() else False)


def png_size_of(path):
    return struct.unpack('>II', Path(path).read_bytes()[16:24])


if __name__ == '__main__':
    unittest.main()
