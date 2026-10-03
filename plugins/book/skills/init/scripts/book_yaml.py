import sys
import tempfile
from pathlib import Path

LIB = Path(__file__).resolve().parents[3] / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from book_config import ConfigError, load_config, read_yaml_subset

PLAIN_UNSAFE_START = ("-", "?", ":", "|", ">", "[", "]", "{", "}", ",", "'", '"', "#", "&", "*",
                      "!", "%", "@", "`")


def plain_text(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        return {str(key): plain_text(item) for key, item in value.items()}
    if isinstance(value, list):
        return [plain_text(item) for item in value]
    return str(value)


def quoted(text):
    escaped = (text.replace("\\", "\\\\").replace('"', '\\"')
               .replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r"))
    return f'"{escaped}"'


def reads_back_as(text):
    try:
        return read_yaml_subset(f"value: {text}\n").get("value")
    except ConfigError:
        return object()


def scalar(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if (text and text == text.strip() and plain_text(reads_back_as(text)) == text
            and not text.startswith(PLAIN_UNSAFE_START) and not text.endswith(":")
            and ": " not in text and " #" not in text):
        return text
    return quoted(text)


def same_values(settings, yaml_text):
    read = read_yaml_subset(yaml_text)
    differences = []

    def walk(expected, found, dotted):
        if isinstance(expected, dict):
            if not isinstance(found, dict):
                differences.append(f"{dotted or 'top level'}: not a mapping in the written file")
                return
            for key, value in expected.items():
                walk(value, found.get(key), f"{dotted}.{key}" if dotted else key)
            return
        if plain_text(expected) != plain_text(found):
            differences.append(f"{dotted}: {plain_text(expected)!r} became {plain_text(found)!r}")

    walk(settings, read, "")
    return differences


def new_layout_paths():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder).resolve()
        (root / "book.yaml").write_text("version: 1\n", encoding="utf-8")
        config = load_config(config=root / "book.yaml")
        return {key: relative_or_none(root, value)
                for key, value in config.resolved_paths().items()}


def relative_or_none(root, value):
    if value is None:
        return None
    try:
        return Path(value).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return None
