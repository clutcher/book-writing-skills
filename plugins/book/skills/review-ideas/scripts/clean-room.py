#!/usr/bin/env python3
import argparse
import datetime
import json
import re
import shutil
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent
SKILLS_DIR = SKILL_DIR.parent
PLUGIN_DIR = SKILLS_DIR.parent
LIB_DIR = PLUGIN_DIR / "lib"
sys.dont_write_bytecode = True
sys.path.insert(0, str(LIB_DIR))

from book_config import ConfigError, add_config_arguments, config_from_args
from run_folders import next_run_folder, runs_of, runs_past_the_kept

REFERENCES_DIR = SKILL_DIR / "references"
TEMPLATES_DIR = SKILL_DIR / "templates"
LENSES_FILE = REFERENCES_DIR / "lenses.md"
ROOM_REFERENCES = ("readers.md", "skeptic-rules.md", "merge-and-verify.md")
ROOM_TEMPLATES = ("lens-report.md", "merge-map.md", "verification.md", "final-report.md")
ROOM_KEEP_SECTIONS = ("Before any lens reads: the contract", "Voices")
ROOM_TAIL_SECTIONS = ("Lens report rules (all lenses)",)
DEFAULT_MARKETPLACE = "book-writing-skills"
DEFAULT_LENS_BATCH = 3
DEFAULT_SKEPTIC_BATCH = 2
WEIGHTS = ("blocker", "major", "minor", "strength")
NOT_SET = "not set: find it in the book"
PLACEHOLDER_KEYS = ("main_metaphor", "key_sources", "research_field", "similar_books",
                    "author_background", "audience")
SOURCES_FOR_REVIEWER_FILE_NAME = "sources-for-reviewer.md"
ROOM_STATE_FILE = "room.json"
MECHANICAL_CHECKS_FILE = "mechanical-checks.txt"
RESULT_FILES = ("merge-map.md", "REVIEW-REPORT.md", "verification")
OLD_LENS_NAMES = {"governing device": "main image"}
RUN_SKILL = "review-ideas"
RUN_MODE = "readers"
LEGACY_ARCHIVE_DIR = "archive"
EXIT_OK = 0
EXIT_FAILED = 2


class RoomError(Exception):
    pass


def setting(config, dotted_key):
    return config.get(dotted_key, None)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def split_sections(text, level):
    marker = "#" * level + " "
    head, sections, current_title, current_lines = [], [], None, []
    for line in text.splitlines():
        if line.startswith(marker):
            if current_title is not None:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title, current_lines = line[len(marker):].strip(), []
        elif current_title is None:
            head.append(line)
        else:
            current_lines.append(line)
    if current_title is not None:
        sections.append((current_title, "\n".join(current_lines).strip()))
    return "\n".join(head).strip(), sections


def parse_default_lenses(lenses_text):
    _, top_sections = split_sections(lenses_text, 2)
    default_body = dict(top_sections).get("The default lenses", "")
    _, lens_sections = split_sections(default_body, 3)
    lenses = []
    for title, body in lens_sections:
        title_match = re.match(r"Lens\s+(\d+):\s*(.+)$", title)
        if not title_match:
            continue
        question = re.search(r"^\*\*Question:\*\*\s*(.+)$", body, re.M)
        weight = re.search(r"^\*\*Weight:\*\*\s*(\S+)", body, re.M)
        detail = re.sub(r"^\*\*(Question|Weight):\*\*.*\n?", "", body, flags=re.M).strip()
        lenses.append({
            "name": title_match.group(2).strip(),
            "question": question.group(1).strip() if question else "",
            "weight": weight.group(1).strip() if weight else "major",
            "detail": detail,
        })
    return lenses


def resolve_lenses(default_lenses, configured):
    by_name = {lens["name"].lower(): lens for lens in default_lenses}
    for old_name, new_name in OLD_LENS_NAMES.items():
        if new_name in by_name:
            by_name[old_name] = by_name[new_name]
    chosen = default_lenses if not configured else []
    for entry in configured or []:
        if isinstance(entry, str):
            if entry.lower() not in by_name:
                raise RoomError(f"readers_review.lenses: no default lens named '{entry}'")
            chosen.append(dict(by_name[entry.lower()]))
            continue
        if not isinstance(entry, dict) or not entry.get("name"):
            raise RoomError("readers_review.lenses: each item is a lens name or a mapping with 'name'")
        base = dict(by_name.get(str(entry["name"]).lower(), {}))
        base.update({key: str(value) for key, value in entry.items() if value is not None})
        if not base.get("question"):
            raise RoomError(f"readers_review.lenses: lens '{entry['name']}' has no 'question'")
        base.setdefault("weight", "major")
        base.setdefault("detail", "")
        chosen.append(base)
    resolved = []
    for number, lens in enumerate(chosen, start=1):
        if lens["weight"] not in WEIGHTS:
            raise RoomError(f"lens '{lens['name']}': weight '{lens['weight']}' is not one of {', '.join(WEIGHTS)}")
        resolved.append({**lens, "number": number,
                         "file": f"lens-{number}-{slug(lens['name'])}.md"})
    return resolved


def placeholder_values(config):
    values = {}
    for key in PLACEHOLDER_KEYS:
        value = setting(config, f"readers_review.{key}")
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value)
        values[key] = str(value) if value not in (None, "") else NOT_SET
    return values


def fill(text, values):
    return re.sub(r"\{\{(\w+)\}\}", lambda match: values.get(match.group(1), match.group(0)), text)


def render_room_lenses(lenses_text, lenses, values):
    _, top_sections = split_sections(lenses_text, 2)
    sections = dict(top_sections)
    parts = ["# Lenses", ""]
    for title in ROOM_KEEP_SECTIONS:
        parts += [f"## {title}", "", fill(sections.get(title, ""), values), ""]
    parts += ["## The lenses for this review", ""]
    for lens in lenses:
        parts += [f"### Lens {lens['number']}: {lens['name']}",
                  f"**Question:** {lens['question']}",
                  f"**Weight:** {lens['weight']}",
                  f"**Report file:** `review/{lens['file']}`", "",
                  fill(lens.get("detail", ""), values), ""]
    for title in ROOM_TAIL_SECTIONS:
        parts += [f"## {title}", "", sections.get(title, ""), ""]
    return "\n".join(parts).rstrip() + "\n"


def lens_table(lenses):
    return "\n".join(f"| {lens['number']} | {lens['name']} | {lens['question']} | "
                     f"{lens['weight']} | `review/{lens['file']}` |" for lens in lenses)


def plugin_identity(config):
    configured = setting(config, "readers_review.plugin_id")
    plugin_name = json.loads((PLUGIN_DIR / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["name"]
    plugin_id = configured or f"{plugin_name}@{DEFAULT_MARKETPLACE}"
    skill_names = sorted(path.parent.name for path in SKILLS_DIR.glob("*/SKILL.md"))
    return plugin_id, plugin_name, skill_names


def settings_for_room(config, existing):
    plugin_id, plugin_name, skill_names = plugin_identity(config)
    settings = dict(existing)
    enabled = dict(settings.get("enabledPlugins", {}))
    enabled[plugin_id] = False
    settings["enabledPlugins"] = enabled
    overrides = dict(settings.get("skillOverrides", {}))
    for name in skill_names:
        overrides[f"{plugin_name}:{name}"] = "off"
    for name in setting(config, "readers_review.skills_off") or []:
        overrides[str(name)] = "off"
    settings["skillOverrides"] = overrides
    return settings


def resolve_room(config, requested):
    room = Path(requested).expanduser() if requested else Path(config.path("readers_review.room"))
    room = room.resolve()
    book_root = config.root.resolve()
    if room == book_root or book_root in room.parents:
        raise RoomError(f"the room must be outside the book folder, not {room}")
    if room in book_root.parents:
        raise RoomError(f"the room must not contain the book folder: {room}")
    if room.exists() and not room.is_dir():
        raise RoomError(f"the room path is a file, not a folder: {room}")
    if is_other_folder(room):
        raise RoomError(f"{room} holds files but no {ROOM_STATE_FILE}, so clean-room.py setup "
                        f"did not make it; choose an empty or new folder with --room")
    return room


def is_other_folder(room):
    return (room.is_dir() and not (room / ROOM_STATE_FILE).is_file()
            and any(room.iterdir()))


def resolve_sources_for_reviewer(config, args):
    if args.no_sources_for_reviewer:
        return None
    candidates = []
    if args.sources_for_reviewer:
        candidates.append(Path(args.sources_for_reviewer).expanduser())
    configured = setting(config, "readers_review.sources_for_reviewer")
    if configured:
        candidates.append(Path(configured))
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    looked = ", ".join(str(candidate) for candidate in candidates) or "nowhere"
    raise RoomError("no sources for the reviewer found (looked at: " + looked + "). Make the "
                    "file with sources-for-reviewer.py draft, pass "
                    "--sources-for-reviewer FILE, or pass --no-sources-for-reviewer")


def read_room_state(room):
    state_file = room / ROOM_STATE_FILE
    if state_file.is_file():
        return json.loads(state_file.read_text(encoding="utf-8"))
    return {}


def book_facts(config):
    lines = ["# Book facts", "",
             "These live outside the manuscript: on the title page, the cover and the store page.", ""]
    for label, key in (("Title", "title"), ("Subtitle", "subtitle"), ("Author", "author"),
                       ("Language", "language"), ("Description", "description")):
        value = config.book.get(key)
        lines.append(f"- **{label}:** {value if value else 'not set'}")
    return "\n".join(lines) + "\n"


def has_results(review_dir, state):
    if not review_dir.is_dir():
        return False
    lens_files = {lens.get("file") for lens in state.get("lenses", [])}
    for entry in review_dir.iterdir():
        if entry.name in RESULT_FILES or entry.name in lens_files or entry.name.startswith("lens-"):
            return True
    return False


def runs_folder(config):
    return Path(config.path("work.runs"))


def round_of_run(run_folder):
    if not (run_folder / ROOM_STATE_FILE).is_file():
        return None
    return int(read_room_state(run_folder).get("round", 1))


def collected_run(config, room_round):
    for run in runs_of(runs_folder(config), RUN_SKILL, RUN_MODE):
        if (round_of_run(run.path) == room_round
                and (run.path / "review" / "REVIEW-REPORT.md").is_file()):
            return run.path
    return None


def remove_runs_past_the_kept(config):
    for old in runs_past_the_kept(runs_folder(config), RUN_SKILL, RUN_MODE):
        shutil.rmtree(old)


class RoomPlan:
    def __init__(self):
        self.actions = []

    def copy_tree(self, source, target):
        self.actions.append(("copy", source, target))

    def copy_file(self, source, target):
        self.actions.append(("copy", source, target))

    def write(self, target, text):
        self.actions.append(("write", text, target))

    def move(self, source, target):
        self.actions.append(("move", source, target))

    def remove(self, target):
        self.actions.append(("remove", None, target))

    def describe(self, room):
        lines = []
        for kind, source, target in self.actions:
            shown_target = target.relative_to(room) if room in target.parents or target == room else target
            if kind == "write":
                lines.append(f"write   {shown_target}")
            elif kind == "remove":
                lines.append(f"remove  {shown_target}")
            else:
                lines.append(f"{kind:<7} {source} -> {shown_target}")
        return lines

    def apply(self):
        for kind, source, target in self.actions:
            if kind == "remove":
                if target.is_dir():
                    shutil.rmtree(target)
                elif target.exists():
                    target.unlink()
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if kind == "write":
                target.write_text(source, encoding="utf-8")
            elif kind == "move":
                shutil.move(str(source), str(target))
            elif Path(source).is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)


def plan_setup(config, args):
    room = resolve_room(config, args.room)
    warnings = []
    manuscript_dir = Path(config.path("manuscript.dir"))
    if not manuscript_dir.is_dir():
        raise RoomError(f"manuscript folder not found: {manuscript_dir}")
    sources_for_reviewer = resolve_sources_for_reviewer(config, args)
    checks = Path(args.checks).expanduser().resolve() if args.checks else None
    if checks and not checks.is_file():
        raise RoomError(f"--checks file not found: {checks}")

    state = read_room_state(room)
    review_dir = room / "review"
    previous_round = int(state.get("round", 0))

    plan = RoomPlan()
    if has_results(review_dir, state):
        archived_round = previous_round or 1
        this_round = archived_round + 1
        if collected_run(config, archived_round):
            plan.remove(review_dir)
            if (room / ROOM_STATE_FILE).is_file():
                plan.remove(room / ROOM_STATE_FILE)
        else:
            archive = next_run_folder(runs_folder(config), RUN_SKILL, RUN_MODE)
            plan.move(review_dir, archive / "review")
            if (room / ROOM_STATE_FILE).is_file():
                plan.move(room / ROOM_STATE_FILE, archive / ROOM_STATE_FILE)
    else:
        this_round = previous_round or 1
        if (review_dir / MECHANICAL_CHECKS_FILE).exists():
            plan.remove(review_dir / MECHANICAL_CHECKS_FILE)
    if (room / LEGACY_ARCHIVE_DIR).exists():
        warnings.append(f"{room / LEGACY_ARCHIVE_DIR} holds earlier rounds inside the room; "
                        f"cold reviewers must not see them: move it to {runs_folder(config)}")
    for replaced in ("manuscript", "plan", "book", "sources", "decisions.md", "REVIEW-PLAN.md"):
        if (room / replaced).exists():
            plan.remove(room / replaced)

    plan.copy_tree(manuscript_dir, room / "manuscript")
    sources_list = config.path("sources.list")
    if sources_list and Path(sources_list).is_file():
        plan.copy_file(Path(sources_list), room / "sources" / "list.md")
    else:
        warnings.append(f"no sources list at {sources_list}; the room has none")
    if sources_for_reviewer:
        plan.copy_file(sources_for_reviewer, room / "sources" / SOURCES_FOR_REVIEWER_FILE_NAME)
    else:
        warnings.append("no sources for the reviewer (--no-sources-for-reviewer); skeptics fetch sources from the list only")
    decisions = config.path("decisions")
    if decisions and Path(decisions).is_file():
        plan.copy_file(Path(decisions), room / "decisions.md")
    else:
        warnings.append(f"no decisions file at {decisions}; reviewers cannot tell decided items")
        plan.write(room / "decisions.md", "# Decisions\n\nNo decisions recorded yet.\n")
    back_cover = config.path("sales_text.back_cover")
    if back_cover and Path(back_cover).is_file():
        plan.copy_file(Path(back_cover), room / "book" / "back-cover.md")
    else:
        plan.write(room / "book" / "back-cover.md", "# Back cover\n\nThe book has no back-cover text yet.\n")
    plan.write(room / "book" / "facts.md", book_facts(config))
    if checks:
        plan.copy_file(checks, review_dir / MECHANICAL_CHECKS_FILE)
    else:
        warnings.append("no --checks file; Stage B must report 'mechanical checks not run'")

    lenses_text = LENSES_FILE.read_text(encoding="utf-8")
    lenses = resolve_lenses(parse_default_lenses(lenses_text), setting(config, "readers_review.lenses"))
    values = placeholder_values(config)
    lens_batch = int(setting(config, "readers_review.lens_batch") or DEFAULT_LENS_BATCH)
    skeptic_batch = int(setting(config, "readers_review.skeptic_batch") or DEFAULT_SKEPTIC_BATCH)
    today = datetime.date.today().isoformat()
    state_command = f'python3 "{SCRIPTS_DIR / "review-state.py"}" --room "{room}"'
    decisions_command = (f'python3 "{LIB_DIR / "decisions.py"}" --file decisions.md '
                         f'match "<one-line finding>"   # earlier decisions this finding may repeat')
    plan_values = {
        "title": config.book.title or "untitled book",
        "round": str(this_round),
        "date": today,
        "lens_table": lens_table(lenses),
        "lens_batch": str(lens_batch),
        "skeptic_batch": str(skeptic_batch),
        "state_command": state_command,
        "decisions_command": decisions_command,
        "sources_for_reviewer_note": "" if sources_for_reviewer else "(not provided for this round)",
        "mechanical_checks_note": ("results are in `review/mechanical-checks.txt`." if checks else
                                   "not run before this round; say so in the merge map and the report."),
    }
    plan.write(room / "REVIEW-PLAN.md", fill((TEMPLATES_DIR / "room-plan.md").read_text(encoding="utf-8"), plan_values))
    plan.write(room / "plan" / "lenses.md", render_room_lenses(lenses_text, lenses, values))
    for name in ROOM_REFERENCES:
        plan.copy_file(REFERENCES_DIR / name, room / "plan" / name)
    for name in ROOM_TEMPLATES:
        plan.copy_file(TEMPLATES_DIR / name, room / "plan" / "templates" / name)
    plan.write(room / "CLAUDE.md", (TEMPLATES_DIR / "room-claude.md").read_text(encoding="utf-8"))
    settings_path = room / ".claude" / "settings.local.json"
    existing = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.is_file() else {}
    plan.write(settings_path, json.dumps(settings_for_room(config, existing), indent=2) + "\n")
    room_state = {
        "round": this_round,
        "made": today,
        "title": config.book.title,
        "lens_batch": lens_batch,
        "skeptic_batch": skeptic_batch,
        "lenses": [{key: lens[key] for key in ("number", "name", "question", "weight", "file")}
                   for lens in lenses],
    }
    plan.write(room / ROOM_STATE_FILE, json.dumps(room_state, indent=2) + "\n")
    return room, plan, warnings, this_round


def run_setup(config, args):
    room, plan, warnings, this_round = plan_setup(config, args)
    print(f"room    {room}  (round {this_round})")
    for line in plan.describe(room):
        print(line)
    for warning in warnings:
        print(f"WARN    {warning}")
    if not args.fix:
        print("dry run: nothing written; add --fix to make the room")
        return EXIT_OK
    plan.apply()
    remove_runs_past_the_kept(config)
    print(f"done: open a new Claude Code session in {room} and ask it to run REVIEW-PLAN.md")
    return EXIT_OK


def run_collect(config, args):
    room = resolve_room(config, args.room)
    review_dir = room / "review"
    if not (review_dir / "REVIEW-REPORT.md").is_file():
        raise RoomError(f"no report yet: {review_dir / 'REVIEW-REPORT.md'} does not exist")
    state = read_room_state(room)
    earlier = collected_run(config, int(state.get("round", 1)))
    if earlier:
        raise RoomError(f"round {state.get('round', 1)} is already collected in {earlier}")
    target = next_run_folder(runs_folder(config), RUN_SKILL, RUN_MODE)
    print(f"copy    {review_dir} -> {target / 'review'}")
    print(f"copy    {room / ROOM_STATE_FILE} -> {target / ROOM_STATE_FILE}")
    if not args.fix:
        print("dry run: nothing written; add --fix to copy the results")
        return EXIT_OK
    target.mkdir(parents=True)
    shutil.copytree(review_dir, target / "review")
    if (room / ROOM_STATE_FILE).is_file():
        shutil.copy2(room / ROOM_STATE_FILE, target / ROOM_STATE_FILE)
    remove_runs_past_the_kept(config)
    print(f"done: results in {target}; read them with review-state.py --room \"{target}\"")
    return EXIT_OK


def run_remove(config, args):
    room = resolve_room(config, args.room)
    if not room.is_dir():
        print(f"no room at {room}; nothing to remove")
        return EXIT_OK
    state = read_room_state(room)
    room_round = int(state.get("round", 1))
    if has_results(room / "review", state) and not collected_run(config, room_round):
        raise RoomError(f"round {room_round} has results that are not collected yet; "
                        f"run clean-room.py collect --fix first")
    print(f"remove  {room}")
    if not args.fix:
        print("dry run: nothing removed; add --fix to remove the room")
        return EXIT_OK
    shutil.rmtree(room)
    print("done: the room is gone; its results stay in the book's run folder")
    return EXIT_OK


def build_parser():
    parser = argparse.ArgumentParser(
        description="Make the clean room for a readers review of a book, bring its results "
                    "back into the book's run folder, or remove the room. Dry run by default; "
                    "--fix writes.")
    add_config_arguments(parser)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser(
        "setup", help="make or refresh the clean room next to the book folder",
        description="Copy the manuscript, sources list, sources for the reviewer, decisions.md and book "
                    "facts into a folder next to the book, write the review plan and a "
                    ".claude/settings.local.json that switches the book skills off. "
                    "An earlier round's results leave the room: removed when collect already "
                    "copied them, else moved to a new <work.runs>/<YYYY-MM-DD-HHMM>-review-ideas-"
                    "readers/ folder. A room with no results yet keeps its round.")
    setup.add_argument("--room", metavar="DIR",
                       help="the room folder (default: readers_review.room, else "
                            "<book folder>-readers-review next to the book)")
    setup.add_argument("--sources-for-reviewer", metavar="FILE",
                       help="the sources for the reviewer (default: "
                            "readers_review.sources_for_reviewer, else "
                            f"<work.output>/{SOURCES_FOR_REVIEWER_FILE_NAME})")
    setup.add_argument("--no-sources-for-reviewer", action="store_true",
                       help="make the room without sources for the reviewer")
    setup.add_argument("--checks", metavar="FILE",
                       help="saved output of the mechanical citation checks, copied to "
                            "review/mechanical-checks.txt")
    setup.add_argument("--fix", action="store_true", help="write the room (default: dry run)")
    collect = commands.add_parser(
        "collect", help="copy the room's finished review/ into the book's run folder",
        description="Copy review/ and room.json from the room into "
                    "<work.runs>/<YYYY-MM-DD-HHMM>-review-ideas-readers/ (newest three kept), "
                    "where review-state.py can read them.")
    collect.add_argument("--room", metavar="DIR", help="the room folder (default as for setup)")
    collect.add_argument("--fix", action="store_true", help="copy the files (default: dry run)")
    remove = commands.add_parser(
        "remove", help="remove the room once its results are collected",
        description="Remove the room folder next to the book. Refused while the room holds "
                    "results that collect has not copied into the book's run folder.")
    remove.add_argument("--room", metavar="DIR", help="the room folder (default as for setup)")
    remove.add_argument("--fix", action="store_true", help="remove the room (default: dry run)")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        config = config_from_args(args)
        if args.command == "setup":
            return run_setup(config, args)
        if args.command == "remove":
            return run_remove(config, args)
        return run_collect(config, args)
    except (ConfigError, RoomError, OSError, json.JSONDecodeError) as error:
        print(f"ERROR   {error}", file=sys.stderr)
        return EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
