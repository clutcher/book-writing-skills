import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

LIB = Path(__file__).resolve().parent
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from book_config import (LAYOUT_OLD, LAYOUTS, ConfigError, add_config_arguments,
                         config_from_args, layout_default, load_config, natural_sort_key)
from check_output import tool_failed
from citation_key import is_safe_file_key

FETCH = "fetch"
OCR = "ocr"
ORIGIN_KINDS = (FETCH, OCR)

LAYOUT_CACHE_FOLDERS = tuple(dict.fromkeys(layout_default(layout, "sources.library")
                                           for layout in reversed(LAYOUTS)))

CACHE_FILE_NAME = r"[A-Za-z0-9][A-Za-z0-9+_.-]*"
CACHE_REFERENCE = re.compile(r"`((?:[^`\s]+/)?)(" + CACHE_FILE_NAME + r")`")


class UnsafeFileKey(ValueError):
    def __init__(self, key):
        super().__init__(f"the key {key!r} is not a plain file name: use letters, digits and "
                         f"+ _ . - only, starting with a letter or digit")
        self.key = key


@dataclass
class SourceFolders:
    root: Path
    files: Path
    origin: Path

    @property
    def merged_origin(self):
        return self.origin is not None and Path(self.origin).resolve() != Path(self.files).resolve()

    @property
    def shown_files(self):
        return shown_path(self.root, self.files)

    def file(self, name):
        return Path(self.files) / name

    def shown_file(self, name):
        return f"{self.shown_files}/{name}"

    def origin_record_path(self, key, kind):
        if self.merged_origin:
            return Path(self.origin) / f"{key}.json"
        return Path(self.files) / f"{key}.{kind}.json"

    def shown_origin_record(self, key, kind):
        return shown_path(self.root, self.origin_record_path(key, kind))

    def read_origin_record(self, key, kind):
        if not is_safe_file_key(key):
            return None
        path = self.origin_record_path(key, kind)
        if not path.is_file():
            return None
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return None
        if self.merged_origin:
            record = data.get(kind) if isinstance(data, dict) else None
            return record if isinstance(record, dict) else None
        return data if isinstance(data, dict) else None

    def has_origin_record(self, key, kind):
        return self.read_origin_record(key, kind) is not None

    def write_origin_record(self, key, kind, record):
        if not is_safe_file_key(key):
            raise UnsafeFileKey(key)
        path = self.origin_record_path(key, kind)
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.merged_origin:
            data = {}
            if path.is_file():
                try:
                    with open(path, encoding="utf-8") as handle:
                        data = json.load(handle)
                except (OSError, ValueError):
                    data = {}
            data[kind] = record
        else:
            data = record
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=1, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
        return path

    def keys_with_origin_record(self, kind):
        keys = set()
        if self.merged_origin:
            folder = Path(self.origin)
            if not folder.is_dir():
                return keys
            for path in folder.glob("*.json"):
                key = path.name[:-len(".json")]
                if self.read_origin_record(key, kind) is not None:
                    keys.add(key.split(".", 1)[0])
            return keys
        folder = Path(self.files)
        if folder.is_dir():
            suffix = f".{kind}.json"
            keys = {path.name.split(".", 1)[0] for path in folder.glob(f"*{suffix}")}
        return keys


def shown_path(root, path):
    path = Path(path)
    try:
        return path.resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return str(path)


def folders_from_config(config):
    return SourceFolders(root=config.root, files=config.sources.library,
                         origin=config.sources.library_index or config.sources.library)


def folders_for_directory(directory, origin=None):
    directory = Path(directory)
    return SourceFolders(root=directory.parent, files=directory,
                         origin=Path(origin) if origin else directory)


def cache_folder_prefixes(folders):
    prefixes = [folders.shown_files]
    prefixes.extend(prefix for prefix in LAYOUT_CACHE_FOLDERS if prefix not in prefixes)
    return prefixes


def cache_references(folders, text):
    prefixes = cache_folder_prefixes(folders)
    found = []
    for match in CACHE_REFERENCE.finditer(text):
        folder_part = match.group(1).rstrip("/")
        if folder_part not in prefixes:
            continue
        name = match.group(2)
        found.append((match.group(0), folder_part, name, folders.file(name)))
    return found


def is_configured_prefix(folders, folder_part):
    return folder_part == folders.shown_files


def load_book(args, tool):
    try:
        return config_from_args(args, targets=[getattr(args, "target", None)])
    except ConfigError as error:
        sys.exit(tool_failed(str(error), tool))


def manuscript_paths(config, tool, explicit=None):
    if explicit:
        return markdown_files_under(explicit)
    try:
        return [item.path for item in config.manuscript_files()]
    except ConfigError as error:
        sys.exit(tool_failed(str(error), tool))


def markdown_files_under(path):
    path = Path(path)
    if path.is_dir():
        return sorted(path.rglob("*.md"),
                      key=lambda found: natural_sort_key(found.relative_to(path).as_posix()))
    return [path] if path.is_file() else []


def visible_markdown_files_under(path):
    return [found for found in markdown_files_under(path)
            if not any(part.startswith(".") for part in found.relative_to(path).parts)]


def thinking_paths(config):
    thinking = config.thinking
    if thinking.dir and Path(thinking.dir).is_dir():
        return visible_markdown_files_under(thinking.dir)
    found = []
    for place in (thinking.stance, thinking.stance_details, thinking.audience, thinking.argument,
                  thinking.doubts):
        if place and Path(place).exists():
            found += visible_markdown_files_under(place)
    return found


def path_or_default(value, default):
    return Path(value) if value else default


def tool_cache_folder(config, name):
    if config.layout == LAYOUT_OLD:
        return Path(config.root) / f".{name}-cache"
    return Path(config.work.caches) / name


def run_from_book_root(config):
    if config.root and Path(config.root).is_dir():
        os.chdir(config.root)


__all__ = [
    "ConfigError", "add_config_arguments", "config_from_args", "load_config", "tool_failed",
    "FETCH", "OCR", "ORIGIN_KINDS", "UnsafeFileKey", "LAYOUT_CACHE_FOLDERS", "CACHE_REFERENCE",
    "SourceFolders", "shown_path", "folders_from_config", "folders_for_directory",
    "cache_folder_prefixes", "cache_references", "is_configured_prefix", "load_book",
    "manuscript_paths", "markdown_files_under", "visible_markdown_files_under", "thinking_paths",
    "path_or_default", "run_from_book_root", "tool_cache_folder",
]
