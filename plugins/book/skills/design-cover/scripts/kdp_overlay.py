import re
from dataclasses import dataclass, field
from pathlib import Path

from kdp_download import (NetworkMissingError, TemplateAnswerError, TemplateRequest,
                          fetch_templates)

OVERLAY_OPACITY = 0.55
FETCH_COMMAND = 'kdp-template.py --fix'
TEMPLATE_NAME = re.compile(r'^PAPERBACK_(?P<width>[0-9.]+)x(?P<height>[0-9.]+)_(?P<pages>\d+)_'
                           r'(?P<paper>[A-Z_]+?)(?:_[a-z]{2}_[A-Z]{2})?\.png$')


@dataclass
class TemplateChoice:
    path: Path = None
    pages: int = None
    exact: bool = False
    notes: list = field(default_factory=list)


def paper_from_name(text):
    if 'CREAM' in text:
        return 'bw-cream'
    if 'PREMIUM' in text:
        return 'color-premium'
    if 'STANDARD' in text:
        return 'color-standard'
    if 'WHITE' in text:
        return 'bw-white'
    return None


def read_templates(folder):
    templates = []
    if folder and Path(folder).is_dir():
        for path in sorted(Path(folder).glob('PAPERBACK_*.png')):
            match = TEMPLATE_NAME.match(path.name)
            if match:
                templates.append((int(match.group('pages')), path, match))
    return templates


def choose_template(templates, pages):
    exact = [entry for entry in templates if entry[0] == pages]
    if exact:
        return exact[0], True
    return min(templates, key=lambda entry: abs(entry[0] - pages)), False


def matching_templates(folder, size):
    return [entry for entry in read_templates(folder)
            if abs(float(entry[2].group('width')) - size.trim_width_in) <= 0.005
            and abs(float(entry[2].group('height')) - size.trim_height_in) <= 0.005
            and paper_from_name(entry[2].group('paper')) in (None, size.paper)]


def template_for(size, folder, may_download):
    choice = TemplateChoice()
    if folder is None:
        choice.notes.append('no cover.templates folder in book.yaml, so no KDP template')
        return choice
    has_exact = any(entry[0] == size.page_count for entry in matching_templates(folder, size))
    if not has_exact and may_download:
        template_request = TemplateRequest(size.trim_width_in, size.trim_height_in,
                                           size.page_count, size.paper)
        try:
            for target, state in fetch_templates(template_request, folder):
                choice.notes.append(f'KDP template {target.name} downloaded ({state})')
        except (NetworkMissingError, TemplateAnswerError) as error:
            choice.notes.append(f'KDP template not downloaded: {error}; '
                                f'{template_request.manual_way(folder)}')
    templates = matching_templates(folder, size)
    if not templates:
        choice.notes.append(f'no KDP template for this trim and paper in {folder}: '
                            f'{FETCH_COMMAND} downloads it')
        return choice
    (pages, path, _match), exact = choose_template(templates, size.page_count)
    choice.path, choice.pages, choice.exact = path, pages, exact
    if not exact:
        choice.notes.append(f'no template for {size.page_count} pages; the overlay uses the '
                            f'{pages}-page one, so its spine guides are off by the page '
                            f'difference')
    return choice
