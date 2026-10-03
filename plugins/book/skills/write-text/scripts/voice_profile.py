import re
from dataclasses import dataclass
from pathlib import Path

from book_files import SKILL_DIR
from book_config import parse_scalar

DEFAULT_PROFILE = SKILL_DIR / "profiles" / "default.md"
PAPER_PROFILE = SKILL_DIR / "profiles" / "paper-voice.md"
SETTINGS_HEADING = "## Settings"
SETTING_LINE = re.compile(r"^([a-z][a-z0-9_]*):[ \t]*(.*?)\s*$")


@dataclass
class VoiceProfile:
    path: Path
    settings: dict

    def number(self, key):
        value = self.settings.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"voice profile setting {key!r} must be a number, got {value!r} "
                             f"(from {self.path})")
        return value

    def words(self, key):
        value = self.settings.get(key) or []
        return [value] if isinstance(value, str) else list(value)


def read_settings_section(text):
    settings = {}
    inside = False
    for line in text.split("\n"):
        if line.rstrip() == SETTINGS_HEADING:
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        found = SETTING_LINE.match(line) if inside else None
        if found:
            settings[found.group(1)] = parse_scalar(re.sub(r"\s+#.*$", "", found.group(2)))
    return settings


def default_profile(config):
    return PAPER_PROFILE if config.is_paper else DEFAULT_PROFILE


def load_voice_profile(config):
    path = default_profile(config)
    settings = read_settings_section(path.read_text(encoding="utf-8"))
    book_profile = config.rules.voice
    if book_profile and Path(book_profile).is_file():
        path = Path(book_profile)
        settings.update(read_settings_section(path.read_text(encoding="utf-8")))
    overrides = config.settings.get("writing")
    if isinstance(overrides, dict):
        settings.update({key: value for key, value in overrides.items() if value is not None})
    return VoiceProfile(path, settings)
