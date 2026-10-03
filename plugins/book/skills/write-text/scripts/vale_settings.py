import filecmp
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parents[2] / "lib"))

from book_config import ConfigError, load_config
from container_run import calling_user_arguments, folder_mount

PACKAGE_NAME = "PlainBook"
PACKAGE_SOURCE = SCRIPTS / "vale" / PACKAGE_NAME
CONTAINER_BOOK = "/workdir"
VALE_COMMANDS_THAT_WRITE = {"sync"}


class ValeSetupError(Exception):
    pass


@dataclass
class ValeSettings:
    book_root: Path
    manuscript: Path
    vale_ini: Path
    styles: Path
    image: str

    @property
    def package_copy(self):
        return self.styles / PACKAGE_NAME

    def inside_book(self, path):
        absolute = Path(path).resolve()
        root = self.book_root.resolve()
        if absolute == root:
            return "."
        try:
            return str(PurePosixPath(*absolute.relative_to(root).parts))
        except ValueError:
            return None

    def container_path(self, path):
        inside = self.inside_book(path)
        if inside is None:
            return None
        return CONTAINER_BOOK if inside == "." else f"{CONTAINER_BOOK}/{inside}"

    def docker_command(self, vale_arguments):
        book_read_only = not writes_to_book(vale_arguments)
        return (["docker", "run", "--rm", *calling_user_arguments(), "-e", "HOME=/tmp",
                 *folder_mount(self.book_root, CONTAINER_BOOK, read_only=book_read_only),
                 "-w", CONTAINER_BOOK, self.image,
                 f"--config={self.container_path(self.vale_ini)}", *vale_arguments])


def writes_to_book(vale_arguments):
    return bool(vale_arguments) and vale_arguments[0] in VALE_COMMANDS_THAT_WRITE


def add_book_arguments(parser):
    parser.add_argument("--book", metavar="DIR",
                        help="a folder inside the book (default: the working folder)")
    parser.add_argument("--config", metavar="FILE", help="the book's book.yaml")
    parser.add_argument("--set", dest="config_overrides", action="append", default=[],
                        metavar="KEY=VALUE", help="override one config value (repeatable)")


def declared_styles_path(vale_ini):
    if not vale_ini.is_file():
        return ""
    for line in vale_ini.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        if separator and name.strip() == "StylesPath":
            return value.strip()
    return ""


def styles_folder(vale_ini, default_folder):
    declared = declared_styles_path(vale_ini)
    if not declared:
        return Path(default_folder).resolve()
    declared_path = Path(declared)
    if declared_path.is_absolute():
        return declared_path.resolve()
    return (vale_ini.parent / declared_path).resolve()


def load_vale_settings(arguments):
    try:
        config = load_config(arguments.config, arguments.book, arguments.config_overrides)
    except ConfigError as error:
        raise ValeSetupError(str(error)) from error
    vale_ini = config.rules.vale_ini
    if vale_ini is None or not Path(vale_ini).is_file():
        raise ValeSetupError(f"no Vale config at {vale_ini or '<unset>'}; set rules.vale_ini "
                             f"in book.yaml")
    vale_ini = Path(vale_ini)
    settings = ValeSettings(Path(config.root), Path(config.manuscript.dir), vale_ini,
                            styles_folder(vale_ini, config.rules.vale), config.tools.vale_image)
    if settings.inside_book(vale_ini) is None:
        raise ValeSetupError(f"the Vale config {vale_ini} is outside the book folder "
                             f"{settings.book_root}, so the container cannot see it")
    if settings.inside_book(settings.styles) is None:
        raise ValeSetupError(f"the Vale StylesPath {settings.styles} is outside the book folder "
                             f"{settings.book_root}, so the container cannot see it; move the "
                             f"styles folder inside the book")
    return settings


def same_folder_contents(first, second):
    comparison = filecmp.dircmp(first, second)
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        return False
    _, mismatched, errors = filecmp.cmpfiles(first, second, comparison.common_files,
                                             shallow=False)
    if mismatched or errors:
        return False
    return all(same_folder_contents(Path(first) / name, Path(second) / name)
               for name in comparison.common_dirs)


def package_copy_is_current(settings):
    return settings.package_copy.is_dir() and same_folder_contents(PACKAGE_SOURCE,
                                                                   settings.package_copy)


def copy_package(settings):
    settings.styles.mkdir(parents=True, exist_ok=True)
    if settings.package_copy.exists():
        shutil.rmtree(settings.package_copy)
    shutil.copytree(PACKAGE_SOURCE, settings.package_copy)


def docker_found():
    return shutil.which("docker") is not None


def run_vale(settings, vale_arguments):
    sys.stdout.flush()
    return subprocess.run(settings.docker_command(vale_arguments)).returncode
