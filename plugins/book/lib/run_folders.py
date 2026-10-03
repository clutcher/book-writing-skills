#!/usr/bin/env python3
import argparse
import datetime
import hashlib
import json
import re
import shutil
import sys
sys.dont_write_bytecode = True
from dataclasses import dataclass
from pathlib import Path

from book_config import ConfigError, add_config_arguments, config_from_args
from check_output import tool_failed

TOOL = "run-folders"
STAMP_FORMAT = "%Y-%m-%d-%H%M"
STAMP_PATTERN = r"\d{4}-\d{2}-\d{2}-\d{4}"
RUNS_KEPT = 3
CHECKSUMS_FILE = "file-checksums.json"
NAME_PART = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass
class Run:
    path: Path
    stamp: str
    number: int

    @property
    def order(self):
        return self.stamp, self.number


def run_folder_name(skill, mode, started, number=1):
    _check_name_part(skill, "skill")
    _check_name_part(mode, "mode")
    name = f"{started.strftime(STAMP_FORMAT)}-{skill}-{mode}"
    return name if number == 1 else f"{name}-{number}"


def _check_name_part(text, label):
    if not NAME_PART.match(text or ""):
        raise ValueError(f"the {label} must be lower-case words joined by '-', not {text!r}")


def runs_of(runs_folder, skill, mode):
    pattern = re.compile(rf"^({STAMP_PATTERN})-{re.escape(skill)}-{re.escape(mode)}"
                         rf"(?:-(\d+))?$")
    runs_folder = Path(runs_folder)
    if not runs_folder.is_dir():
        return []
    runs = []
    for path in runs_folder.iterdir():
        found = pattern.match(path.name)
        if path.is_dir() and found:
            runs.append(Run(path, found.group(1), int(found.group(2) or 1)))
    return sorted(runs, key=lambda run: run.order, reverse=True)


def latest_run(runs_folder, skill, mode):
    runs = runs_of(runs_folder, skill, mode)
    return runs[0].path if runs else None


def next_run_folder(runs_folder, skill, mode, started=None):
    started = started or datetime.datetime.now()
    stamp = started.strftime(STAMP_FORMAT)
    used = [run.number for run in runs_of(runs_folder, skill, mode) if run.stamp == stamp]
    number = max(used, default=0) + 1
    while (Path(runs_folder) / run_folder_name(skill, mode, started, number)).exists():
        number += 1
    return Path(runs_folder) / run_folder_name(skill, mode, started, number)


def runs_past_the_kept(runs_folder, skill, mode, kept=RUNS_KEPT):
    return [run.path for run in runs_of(runs_folder, skill, mode)[kept:]]


def start_run(runs_folder, skill, mode, started=None, kept=RUNS_KEPT):
    folder = next_run_folder(runs_folder, skill, mode, started)
    folder.mkdir(parents=True)
    for old in runs_past_the_kept(runs_folder, skill, mode, kept):
        if old.resolve() != folder.resolve():
            shutil.rmtree(old)
    return folder


def file_checksum(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def file_checksums(paths, root):
    return {_relative(path, root): file_checksum(path) for path in paths if Path(path).is_file()}


def _relative(path, root):
    path = Path(path).resolve()
    try:
        return path.relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def record_checksums(run_folder, paths, root):
    record = Path(run_folder) / CHECKSUMS_FILE
    record.write_text(json.dumps(file_checksums(paths, root), indent=1, sort_keys=True) + "\n",
                      encoding="utf-8")
    return record


def read_checksums(run_folder):
    record = Path(run_folder) / CHECKSUMS_FILE
    if not record.is_file():
        return None
    try:
        data = json.loads(record.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def last_recorded_run(runs_folder, skill, mode, before=None):
    for run in runs_of(runs_folder, skill, mode):
        if before is not None and run.path.resolve() == Path(before).resolve():
            continue
        if read_checksums(run.path) is not None:
            return run.path
    return None


def changed_files(runs_folder, skill, mode, paths, root, current_run=None):
    last = last_recorded_run(runs_folder, skill, mode, before=current_run)
    if last is None:
        return list(paths)
    recorded = read_checksums(last)
    return [path for path in paths if Path(path).is_file()
            and recorded.get(_relative(path, root)) != file_checksum(path)]


def _files_from(args, config):
    if args.files:
        return [Path(name).resolve() for name in args.files]
    return [item.path for item in config.manuscript_files()]


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Make, list and compare the run folders of review and check runs "
                    "(<work.runs>/<YYYY-MM-DD-HHMM>-<skill>-<mode>/, newest three kept).")
    add_config_arguments(parser)
    commands = parser.add_subparsers(dest="command", required=True)

    start = commands.add_parser("start", help="the new run folder; dry run by default")
    start.add_argument("skill")
    start.add_argument("mode")
    start.add_argument("--fix", action="store_true",
                       help="make the folder and remove the runs past the newest three")

    for name, text in (("list", "the runs of one skill and mode, newest first"),
                       ("latest", "the newest run of one skill and mode, for --resume")):
        command = commands.add_parser(name, help=text)
        command.add_argument("skill")
        command.add_argument("mode")

    changed = commands.add_parser("changed", help="the files changed since the last run")
    changed.add_argument("skill")
    changed.add_argument("mode")
    changed.add_argument("files", nargs="*", help="default: the manuscript files")

    record = commands.add_parser("record", help="write the checksums of the files a run read")
    record.add_argument("run", help="the run folder")
    record.add_argument("files", nargs="*", help="default: the manuscript files")
    record.add_argument("--fix", action="store_true", help="write the record")

    args = parser.parse_args(argv)
    try:
        config = config_from_args(args)
        runs_folder = config.work.runs
        if args.command == "start":
            folder = next_run_folder(runs_folder, args.skill, args.mode)
            removed = runs_past_the_kept(runs_folder, args.skill, args.mode, RUNS_KEPT - 1)
            if args.fix:
                folder = start_run(runs_folder, args.skill, args.mode)
            print(folder)
            for old in removed:
                print(f"{'removed' if args.fix else 'would remove'} {old}", file=sys.stderr)
            if not args.fix:
                print("dry run; pass --fix to make the folder", file=sys.stderr)
        elif args.command == "list":
            for run in runs_of(runs_folder, args.skill, args.mode):
                print(run.path)
        elif args.command == "latest":
            latest = latest_run(runs_folder, args.skill, args.mode)
            if latest is None:
                print(f"no run of {args.skill} {args.mode} in {runs_folder}", file=sys.stderr)
                return 1
            print(latest)
        elif args.command == "changed":
            for path in changed_files(runs_folder, args.skill, args.mode,
                                      _files_from(args, config), config.root):
                print(path)
        elif args.command == "record":
            files = _files_from(args, config)
            if args.fix:
                print(record_checksums(args.run, files, config.root))
            else:
                print(f"would record {len(files)} file(s) in {Path(args.run) / CHECKSUMS_FILE}; "
                      f"pass --fix to write")
    except (ConfigError, ValueError, OSError) as error:
        return tool_failed(str(error), TOOL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
