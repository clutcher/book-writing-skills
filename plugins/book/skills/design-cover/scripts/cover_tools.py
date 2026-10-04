import shutil
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'lib'))

from container_run import calling_user_arguments, folder_mount, path_inside

SRGB_PROFILE_PLACES = (
    '/usr/share/color/icc/colord/sRGB.icc',
    '/usr/share/color/icc/sRGB.icc',
    '/usr/share/color/icc/ghostscript/srgb.icc',
    '/usr/share/ghostscript/iccprofiles/srgb.icc',
    '/usr/local/share/color/icc/sRGB.icc',
    '/System/Library/ColorSync/Profiles/sRGB Profile.icc',
    'C:/Windows/System32/spool/drivers/color/sRGB Color Space Profile.icm',
)
CONTAINER_WORK_FOLDER = '/work'
HOST_FONT_FOLDERS = ('/usr/share/fonts', '/usr/local/share/fonts', '~/.local/share/fonts',
                     '~/.fonts', '/Library/Fonts', '~/Library/Fonts', 'C:/Windows/Fonts',
                     '~/AppData/Local/Microsoft/Windows/Fonts')


class ToolError(Exception):
    pass


def run(command, cwd=None):
    result = subprocess.run([str(part) for part in command], capture_output=True,
                            encoding='utf-8', errors='replace', cwd=cwd)
    if result.returncode != 0:
        raise ToolError(f'{Path(str(command[0])).name} failed: '
                        f'{(result.stderr or result.stdout).strip()}')
    return result.stdout


class SvgConverter:
    def __init__(self, name, prefix, style, shared_folder=None):
        self.name = name
        self.prefix = prefix
        self.style = style
        self.shared_folder = shared_folder

    def seen_path(self, path):
        if self.shared_folder is None:
            return str(path)
        return path_inside(path, self.shared_folder, CONTAINER_WORK_FOLDER)

    def to_png(self, svg, png, height=None):
        Path(png).parent.mkdir(parents=True, exist_ok=True)
        svg_seen, png_seen = self.seen_path(svg), self.seen_path(png)
        if self.style == 'cairosvg':
            size = ['--output-height', str(height)] if height else []
            run(self.prefix + [svg_seen, '-o', png_seen] + size)
        else:
            size = ['-h', str(height)] if height else []
            run(self.prefix + size + [svg_seen, '-o', png_seen])
        return Path(png)

    def to_pdf(self, svg, pdf, dpi):
        Path(pdf).parent.mkdir(parents=True, exist_ok=True)
        svg_seen, pdf_seen = self.seen_path(svg), self.seen_path(pdf)
        if self.style == 'cairosvg':
            run(self.prefix + [svg_seen, '-f', 'pdf', '-d', str(dpi), '-o', pdf_seen])
        else:
            run(self.prefix + ['-f', 'pdf', '-d', str(dpi), '-p', str(dpi), svg_seen, '-o',
                               pdf_seen])
        return Path(pdf)


def docker_prefix(image, folder):
    mounts = folder_mount(folder, CONTAINER_WORK_FOLDER)
    for index, place in enumerate(HOST_FONT_FOLDERS):
        expanded = Path(place).expanduser()
        if expanded.is_dir():
            mounts += folder_mount(expanded, f'/usr/share/fonts/host-{index}', read_only=True)
    return (['docker', 'run', '--rm', '--network', 'none'] + calling_user_arguments() + mounts
            + ['-w', CONTAINER_WORK_FOLDER, '--entrypoint', 'rsvg-convert', image])


def is_pinned_image(image):
    if '@sha256:' in image:
        return True
    name_end = image.rsplit('/', 1)[-1]
    if ':' not in name_end:
        return False
    return name_end.rsplit(':', 1)[1] not in ('', 'latest')


def find_svg_converter(render_image=None, work_folder=None):
    if shutil.which('rsvg-convert'):
        return SvgConverter('rsvg-convert', ['rsvg-convert'], 'rsvg')
    if shutil.which('cairosvg'):
        return SvgConverter('cairosvg', ['cairosvg'], 'cairosvg')
    if (render_image and is_pinned_image(render_image) and shutil.which('docker')
            and work_folder):
        return SvgConverter(f'docker {render_image}', docker_prefix(render_image, work_folder),
                            'rsvg', shared_folder=work_folder)
    return None


def missing_converter_reason(render_image=None):
    if render_image and not is_pinned_image(render_image):
        return (f'no rsvg-convert or cairosvg, and tools.render_image {render_image} is not '
                f'pinned: give it a version tag other than latest, or a @sha256 digest')
    if render_image and not shutil.which('docker'):
        return f'no rsvg-convert or cairosvg, and docker is not installed for {render_image}'
    return ('no rsvg-convert or cairosvg, and no tools.render_image (a pinned docker image '
            'with rsvg-convert) in book.yaml')


class ImageTool:
    def __init__(self, magick):
        self.magick = magick

    def command(self, name):
        if self.magick:
            return ['magick'] if name == 'convert' else ['magick', name]
        return [name]

    def jpeg(self, png, jpg, quality, srgb_profile=None):
        profile = ['-profile', str(srgb_profile)] if srgb_profile else []
        run(self.command('convert') + [png, '-background', 'white', '-alpha', 'remove',
                                       '-alpha', 'off', '-colorspace', 'sRGB', '-strip']
            + profile + ['-sampling-factor', '4:4:4', '-quality', str(quality), jpg])
        return Path(jpg)

    def overlay(self, art, template, out, opacity):
        width, height = png_size(art)
        run(self.command('convert') + [
            art, '(', template, '-resize', f'{width}x{height}!', '-alpha', 'on',
            '-channel', 'A', '-evaluate', 'multiply', str(opacity), '+channel', ')',
            '-compose', 'over', '-composite', '-alpha', 'off', out])
        return Path(out)

    def onion(self, new, old, out, opacity):
        width, height = png_size(new)
        run(self.command('convert') + [
            new, '(', old, '-resize', f'{width}x{height}!', '-alpha', 'on',
            '-channel', 'A', '-evaluate', 'multiply', str(opacity), '+channel', ')',
            '-compose', 'over', '-composite', '-alpha', 'off', out])
        return Path(out)

    def difference(self, first, second, out):
        result = subprocess.run(self.command('compare') + ['-metric', 'AE', str(first),
                                                           str(second), str(out)],
                                capture_output=True, encoding='utf-8', errors='replace')
        if result.returncode not in (0, 1):
            raise ToolError(f'compare failed: {result.stderr.strip()}')
        figure = (result.stderr or result.stdout).strip().split()[0]
        return int(float(figure))

    def side_by_side(self, images, labels, out, height, background='#F5F0EB'):
        cells = []
        for image, label in zip(images, labels):
            cells += ['(', image, '-resize', f'x{height}', '-background', background,
                      '-gravity', 'North', '-splice', '0x40', '-pointsize', '22',
                      '-annotate', '+0+8', label, ')']
        run(self.command('convert') + ['-background', background] + cells
            + ['-gravity', 'North', '-bordercolor', background, '-border', '10', '+append', out])
        return Path(out)

    def resize(self, image, out, height):
        run(self.command('convert') + [image, '-resize', f'x{height}', out])
        return Path(out)


def find_image_tool():
    if shutil.which('magick'):
        return ImageTool(True)
    if shutil.which('convert') and shutil.which('compare'):
        return ImageTool(False)
    return None


def find_srgb_profile(configured=None):
    if configured:
        return Path(configured) if Path(configured).is_file() else None
    for place in SRGB_PROFILE_PLACES:
        if Path(place).is_file():
            return Path(place)
    return None


def png_size(path):
    with open(path, 'rb') as handle:
        header = handle.read(24)
    if header[:8] != b'\x89PNG\r\n\x1a\n' or header[12:16] != b'IHDR':
        raise ToolError(f'{path} is not a PNG file')
    return struct.unpack('>II', header[16:24])
