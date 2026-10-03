import io
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'lib'))
from user_agent import USER_AGENT

CALCULATOR_PAGE = 'https://kdp.amazon.com/en_US/cover-calculator'
DOWNLOAD_ADDRESS = 'https://kdp.amazon.com/en_US/cover-calculator/template-download'
SUCCESS_EVENT = 'cover-template-download:success'
WAIT_SECONDS = 60
DEFAULT_PRINT_LOCALE = 'en_US'
TEMPLATE_SUFFIXES = ('.png', '.pdf')
KDP_PAPER = {
    'bw-white': {'paperType': 'WHITE', 'interiorType': 'BLACK_AND_WHITE', 'name': 'BW_WHITE'},
    'bw-cream': {'paperType': 'CREAM', 'interiorType': 'BLACK_AND_WHITE', 'name': 'BW_CREAM'},
    'color-premium': {'paperType': 'COLOR', 'interiorType': 'PREMIUM_COLOR',
                      'name': 'PREMIUM_WHITE'},
    'color-standard': {'paperType': 'WHITE', 'interiorType': 'STANDARD_COLOR',
                       'name': 'STANDARD_WHITE'},
}
SAME = 'same'
NEW = 'new'
REPLACED = 'replaced'


class TemplateAnswerError(Exception):
    pass


class NetworkMissingError(Exception):
    pass


def trim_code(width_in, height_in):
    def number(value):
        return f'{value:g}'.replace('.', '_')
    return f'{number(width_in)}X{number(height_in)}IN'


@dataclass(frozen=True)
class TemplateRequest:
    trim_width_in: float
    trim_height_in: float
    page_count: int
    paper: str
    print_locale: str = DEFAULT_PRINT_LOCALE

    def form(self):
        kdp_paper = KDP_PAPER[self.paper]
        return {
            'bindingType': 'PAPERBACK',
            'paperType': kdp_paper['paperType'],
            'rightToLeft': 'false',
            'trimSize': trim_code(self.trim_width_in, self.trim_height_in),
            'pageCount': str(self.page_count),
            'interiorType': kdp_paper['interiorType'],
            'printLocale': self.print_locale,
        }

    @property
    def file_stem(self):
        return (f'PAPERBACK_{self.trim_width_in:.3f}x{self.trim_height_in:.3f}_'
                f'{self.page_count}_{KDP_PAPER[self.paper]["name"]}_{self.print_locale}')

    def file_names(self):
        return [self.file_stem + suffix for suffix in TEMPLATE_SUFFIXES]

    def as_text(self):
        return f'POST {DOWNLOAD_ADDRESS} {urllib.parse.urlencode(self.form())}'

    def manual_way(self, folder):
        return (f'download it by hand: open {CALCULATOR_PAGE}, choose paperback, trim '
                f'{self.trim_width_in:g} x {self.trim_height_in:g} in, {self.page_count} pages, '
                f'{self.paper} paper, download the template, unzip it and put '
                f'{self.file_stem}.png in {folder} (cover.templates)')


def download_address_from_answer(text):
    try:
        answer = json.loads(text)
        for entry in answer['_nested_scripter']:
            for action in entry['actions']:
                arguments = action.get('args') or []
                if (len(arguments) >= 2 and arguments[0] == SUCCESS_EVENT
                        and str(arguments[1]).startswith('https://')):
                    return arguments[1]
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        raise TemplateAnswerError(f'the KDP answer has a shape this script does not know '
                                  f'({type(error).__name__}: {error})') from error
    raise TemplateAnswerError('the KDP answer has no download address in it; the cover '
                              'calculator may have changed')


def read_address(request):
    try:
        with urllib.request.urlopen(request, timeout=WAIT_SECONDS) as answer:
            return answer.read()
    except urllib.error.HTTPError as error:
        raise TemplateAnswerError(f'KDP answered HTTP {error.code} for {request.full_url}; '
                                  f'the cover calculator may have changed, or it does not '
                                  f'offer this trim, page count and paper') from error
    except (urllib.error.URLError, OSError) as error:
        raise NetworkMissingError(f'cannot reach {urllib.parse.urlsplit(request.full_url).netloc}'
                                  f' ({getattr(error, "reason", error)})') from error


def ask_download_address(template_request):
    body = urllib.parse.urlencode(template_request.form()).encode('ascii')
    request = urllib.request.Request(DOWNLOAD_ADDRESS, data=body, method='POST', headers={
        'User-Agent': USER_AGENT,
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    })
    return download_address_from_answer(read_address(request).decode('utf-8', 'replace'))


def download_archive(address):
    return read_address(urllib.request.Request(address, headers={'User-Agent': USER_AGENT}))


def templates_in_archive(archive):
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as opened:
            files = {Path(member.filename).name: opened.read(member)
                     for member in opened.infolist()
                     if not member.is_dir()
                     and Path(member.filename).suffix.lower() in TEMPLATE_SUFFIXES}
    except zipfile.BadZipFile as error:
        raise TemplateAnswerError(f'the KDP download is not a zip file ({error})') from error
    if not any(name.lower().endswith('.png') for name in files):
        raise TemplateAnswerError('the KDP zip file holds no template PNG')
    return files


def store_templates(files, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    results = []
    for name, content in sorted(files.items()):
        target = folder / name
        if target.is_file() and target.read_bytes() == content:
            results.append((target, SAME))
            continue
        state = REPLACED if target.exists() else NEW
        target.write_bytes(content)
        results.append((target, state))
    return results


def fetch_templates(template_request, folder):
    address = ask_download_address(template_request)
    return store_templates(templates_in_archive(download_archive(address)), folder)
