#!/usr/bin/env python3
import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

from book_config import ConfigError, add_config_arguments, config_from_args
from check_output import (ADVISORY, DEFECT, INFORMATIONAL, CheckReport,
                          add_output_arguments, tool_failed)
from citation_key import KEY_BODY, entry_keys
from citations import cited_keys
from decisions import match_finding, read_decisions

TOOL = "open-notes"
WHOLE_BOOK = "whole-book"
NOTES_SUFFIX = ".md"

NOTE_HEADING = re.compile(r"^##\s+(?P<stem>[A-Za-z0-9][\w.-]*)\s+#(?P<number>\d+)(?:\s+(?P<title>.*))?$")
SECOND_LEVEL_HEADING = re.compile(r"^##\s")
FIELD_START = re.compile(r"^\*\*[A-Za-z][A-Za-z ()-]*:\*\*")
INLINE_FIELD = re.compile(r"\*\*(?P<name>[A-Za-z][A-Za-z ()-]*):\*\*")
BLOCKQUOTE_LINE = re.compile(r"^>\s?(?P<text>.*)$")
ELLIPSIS = re.compile(r"\[\.\.\.\]|\.\.\.|…")
BRACKETED = re.compile(r"\[([^\]\n]+)\]")
CITATION_KEY = re.compile(rf"^{KEY_BODY}$")
HEADING_LINE = re.compile(r"^#{1,6}\s+(?P<title>.+)$")
RESOLVED_STATUS = re.compile(r"\[[xX]\]")
QUOTE_MARKS = "\"'“”‘’"
TITLE_DASHES = "-–—:"
SHORTEST_CHECKED_PIECE = 12
MARKDOWN_LINK = re.compile(r"!?\[(?P<text>[^\]\n]*)\]\([^)\n]*\)")
FOOTNOTE_MARK = re.compile(r"\[\^[^\]\n]+\]")
EMPHASIS_UNDERSCORE = re.compile(r"(?<![A-Za-z0-9])_+|_+(?![A-Za-z0-9])")
LINKED_NOTE = re.compile(r"(?:(?P<stem>[A-Za-z0-9][\w.-]*)\s+)?#(?P<number>\d+)\b")

TYPOGRAPHY = str.maketrans({
    "“": '"', "”": '"', "‘": "'", "’": "'",
    "–": "-", "—": "-", " ": " ", "*": None, "`": None,
})

FIELD_PARAGRAPH = "Paragraph"
FIELD_TEXT = "Text"
FIELD_NOTE = "Note"
FIELD_NOTE_EXPANDED = "Note (expanded)"
FIELD_TIER = "Tier"
FIELD_STATUS = "Status"
FIELD_RESOLUTION = "Resolution"
FIELD_LINKED = "Linked"
FIELD_FROM = "From"

FINDING_CLASSES = {
    "bad-heading": DEFECT,
    "duplicate-id": DEFECT,
    "notes-file-unmatched": DEFECT,
    "wrong-file": DEFECT,
    "unknown-file": DEFECT,
    "paragraph-not-quoted": DEFECT,
    "paragraph-changed": DEFECT,
    "resolved-note-left": DEFECT,
    "text-not-found": ADVISORY,
    "id-used-before": ADVISORY,
    "linked-note-missing": ADVISORY,
    "no-from": ADVISORY,
    "not-analysed": INFORMATIONAL,
    "open-notes": INFORMATIONAL,
}


@dataclass
class Note:
    notes_file: Path
    stem: str
    number: int
    title: str
    line_number: int
    fields: dict = field(default_factory=dict)
    field_lines: dict = field(default_factory=dict)

    @property
    def id(self):
        return f"{self.stem} #{self.number}"

    @property
    def quoted_paragraphs(self):
        paragraphs, current = [], []
        for line in self.field_lines.get(FIELD_PARAGRAPH, []):
            quoted = BLOCKQUOTE_LINE.match(line)
            if quoted and quoted.group("text").strip():
                current.append(quoted.group("text").strip())
                continue
            if current:
                paragraphs.append(" ".join(current))
                current = []
        if current:
            paragraphs.append(" ".join(current))
        return paragraphs

    @property
    def flagged_text(self):
        value = self.fields.get(FIELD_TEXT, "").strip()
        if len(value) < 2 or value[0] not in QUOTE_MARKS:
            return None
        closing = max(value.rfind(mark) for mark in QUOTE_MARKS)
        return value[1:closing] if closing > 0 else None

    @property
    def is_resolved(self):
        status = self.fields.get(FIELD_STATUS, "")
        return bool(RESOLVED_STATUS.search(status)) or bool(self.fields.get(FIELD_RESOLUTION, "").strip())

    @property
    def tier(self):
        return self.fields.get(FIELD_TIER, "").split()[0] if self.fields.get(FIELD_TIER, "").strip() else ""

    @property
    def reader_text(self):
        return "\n".join(self.fields.get(name, "") for name in
                         (FIELD_NOTE, FIELD_NOTE_EXPANDED, FIELD_TEXT))

    @property
    def linked_ids(self):
        return [f"{found.group('stem') or self.stem} #{found.group('number')}"
                for found in LINKED_NOTE.finditer(self.fields.get(FIELD_LINKED, ""))]


@dataclass
class NotesFile:
    path: Path
    notes: list
    bad_headings: list

    @property
    def stem(self):
        return self.path.stem


def read_notes_file(path):
    lines = path.read_text(encoding="utf-8").split("\n")
    notes, bad_headings = [], []
    current, current_field = None, None
    fenced = False
    for number, line in enumerate(lines, 1):
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if SECOND_LEVEL_HEADING.match(line):
            heading = NOTE_HEADING.match(line)
            current_field = None
            if heading:
                title = (heading.group("title") or "").strip()
                current = Note(path, heading.group("stem"), int(heading.group("number")), title, number)
                notes.append(current)
                if title and title[0] in TITLE_DASHES:
                    bad_headings.append((number, line, "has a dash or colon between the id and the title"))
            else:
                current = None
                bad_headings.append((number, line, "is not a note heading '## <file-name> #<number> <title>'"))
            continue
        if current is None:
            continue
        if FIELD_START.match(line):
            starts = list(INLINE_FIELD.finditer(line))
            for index, start in enumerate(starts):
                end = starts[index + 1].start() if index + 1 < len(starts) else len(line)
                current_field = start.group("name").strip()
                current.fields[current_field] = line[start.end():end].strip()
                current.field_lines[current_field] = []
            continue
        if current_field:
            current.fields[current_field] += "\n" + line
            current.field_lines[current_field].append(line)
    return NotesFile(path, notes, bad_headings)


def read_all_notes(folder):
    if not folder or not folder.is_dir():
        return []
    return [read_notes_file(path) for path in sorted(folder.glob("*" + NOTES_SUFFIX))]


def as_reader_sees_it(text):
    without_links = MARKDOWN_LINK.sub(lambda found: found.group("text"), text)
    without_footnotes = FOOTNOTE_MARK.sub("", without_links)
    return EMPHASIS_UNDERSCORE.sub("", without_footnotes)


def normalised(text):
    return re.sub(r"\s+", " ", as_reader_sees_it(text).translate(TYPOGRAPHY)).strip()


def is_present(quote, haystack):
    pieces = [piece for piece in (normalised(part) for part in ELLIPSIS.split(quote)) if piece]
    long_pieces = [piece for piece in pieces if len(piece) >= SHORTEST_CHECKED_PIECE]
    return all(piece in haystack for piece in long_pieces or pieces)


def file_name_stem(name):
    return name[:-len(NOTES_SUFFIX)] if name.endswith(NOTES_SUFFIX) else name


def notable_files(config):
    files = {}
    for manuscript_file in config.manuscript_files():
        files.setdefault(manuscript_file.path.stem, manuscript_file.path)
    sales_text = config.publishing.sales_text
    if sales_text and sales_text.is_dir():
        for path in sorted(sales_text.iterdir()):
            if path.is_file():
                files.setdefault(path.stem, path)
    for path in thinking_files(config):
        files.setdefault(path.stem, path)
    return files


def thinking_files(config):
    thinking = config.thinking
    if thinking.dir and thinking.dir.is_dir():
        return sorted(thinking.dir.rglob("*.md"))
    found = [path for path in (thinking.stance, thinking.stance_details, thinking.audience)
             if path and path.is_file()]
    for folder in (thinking.argument, thinking.doubts):
        if folder and folder.is_dir():
            found.extend(sorted(folder.rglob("*.md")))
    return found


def target_paths(stem, files):
    if stem == WHOLE_BOOK:
        return list(files.values())
    return [files[stem]] if stem in files else []


def read_text_of(paths):
    return normalised("\n".join(path.read_text(encoding="utf-8", errors="replace")
                                for path in paths))


def used_numbers_in_decisions(config, stem):
    if not config.rules.decisions or not config.rules.decisions.is_file():
        return set()
    pattern = re.compile(rf"^{re.escape(stem)}\s+#(\d+)\b")
    numbers = set()
    for entry in read_decisions(config.rules.decisions).entries:
        for alias in entry.aliases:
            found = pattern.match(alias.strip())
            if found:
                numbers.add(int(found.group(1)))
    return numbers


def relative(config, path):
    try:
        return Path(path).resolve().relative_to(config.root).as_posix()
    except ValueError:
        return str(path)


def check_notes(config, report):
    manuscript_folder = config.manuscript.dir
    if not manuscript_folder or not Path(manuscript_folder).is_dir():
        raise ValueError(f"no manuscript folder at {manuscript_folder}")
    if not config.notes or not Path(config.notes).is_dir():
        report.skip(f"no notes folder at {config.notes}")
        return
    files = notable_files(config)
    haystacks = {}
    seen_ids = {}
    all_notes = read_all_notes(config.notes)
    open_ids = {note.id for notes_file in all_notes for note in notes_file.notes}
    for notes_file in all_notes:
        file_key = relative(config, notes_file.path)
        file_is_matched = notes_file.stem == WHOLE_BOOK or notes_file.stem in files
        if not file_is_matched:
            report.add(file_key, "notes-file-unmatched",
                       f"no manuscript, thinking or sales-text file is named "
                       f"'{notes_file.stem}', "
                       f"and it is not {WHOLE_BOOK}{NOTES_SUFFIX}")
        for line_number, line, reason in notes_file.bad_headings:
            report.add(f"{file_key}:{line_number}", "bad-heading", f"'{line.strip()}' {reason}")
        if notes_file.notes:
            report.add(file_key, "open-notes", f"{len(notes_file.notes)} open")
        decided_numbers = used_numbers_in_decisions(config, notes_file.stem)
        for note in notes_file.notes:
            check_one_note(config, report, note, notes_file, files, haystacks,
                           seen_ids, decided_numbers, file_is_matched)
            check_note_fields(config, report, note, open_ids)


def check_note_fields(config, report, note, open_ids):
    key = f"{relative(config, note.notes_file)}:{note.line_number}"
    if not note.fields.get(FIELD_FROM, "").strip():
        report.add(key, "no-from",
                   f"'{note.id}' has no From line; write 'author' or the skill, mode and run time")
    for linked_id in note.linked_ids:
        if linked_id not in open_ids:
            report.add(key, "linked-note-missing",
                       f"'{note.id}' links '{linked_id}', which is no open note; "
                       f"cite its decision entry instead")


def check_one_note(config, report, note, notes_file, files, haystacks, seen_ids,
                   decided_numbers, file_is_matched):
    key = f"{relative(config, note.notes_file)}:{note.line_number}"
    if note.id in seen_ids:
        report.add(key, "duplicate-id", f"'{note.id}' is also used at line {seen_ids[note.id]}")
    seen_ids.setdefault(note.id, note.line_number)
    if note.number in decided_numbers:
        report.add(key, "id-used-before",
                   f"'{note.id}' is already an alias in decisions.md: fine when part of this "
                   f"note was decided, otherwise give the note a new id (open-notes.py next-id)")
    if note.stem != notes_file.stem:
        report.add(key, "wrong-file",
                   f"'{note.id}' belongs in {note.stem}{NOTES_SUFFIX}, not {notes_file.path.name}")
    if note.is_resolved:
        report.add(key, "resolved-note-left",
                   f"'{note.id}' is resolved; record the decision and remove the note")
    targets = target_paths(note.stem, files)
    if not targets:
        if file_is_matched or note.stem != notes_file.stem:
            report.add(key, "unknown-file",
                       f"'{note.stem}' names no manuscript, thinking or sales-text file")
        return
    if FIELD_PARAGRAPH not in note.fields:
        report.add(key, "not-analysed", f"'{note.id}' has no Paragraph yet")
    elif not note.quoted_paragraphs:
        report.add(key, "paragraph-not-quoted",
                   f"'{note.id}' Paragraph is not a '>' quote of the text")
    haystack = haystacks.setdefault(note.stem, read_text_of(targets))
    for paragraph in note.quoted_paragraphs:
        if not is_present(paragraph, haystack):
            report.add(key, "paragraph-changed",
                       f"'{note.id}' quotes a paragraph that is no longer in the text: "
                       f"'{normalised(paragraph)[:70]}...'")
    flagged = note.flagged_text
    if flagged and not is_present(flagged, haystack):
        report.add(key, "text-not-found",
                   f"'{note.id}' Text is not found word for word: '{normalised(flagged)[:70]}'")


def open_notes_listing(config, only_stem=None):
    listing = []
    for notes_file in read_all_notes(config.notes):
        if only_stem and notes_file.stem != only_stem:
            continue
        listing.append({
            "file": relative(config, notes_file.path),
            "notes": [{"id": note.id, "tier": note.tier, "title": note.title,
                       "analysed": FIELD_PARAGRAPH in note.fields}
                      for note in notes_file.notes],
        })
    return listing


def next_note_id(config, stem):
    numbers = set(used_numbers_in_decisions(config, stem))
    for notes_file in read_all_notes(config.notes):
        numbers.update(note.number for note in notes_file.notes if note.stem == stem)
    return f"{stem} #{max(numbers, default=0) + 1}"


def find_note(config, note_id):
    heading = NOTE_HEADING.match("## " + normalised(note_id))
    if not heading:
        return None
    wanted = f"{heading.group('stem')} #{int(heading.group('number'))}"
    for notes_file in read_all_notes(config.notes):
        for note in notes_file.notes:
            if note.id == wanted:
                return note
    return None


def citation_keys_in(texts):
    keys = []
    for text in texts:
        for key in cited_keys(text):
            if key not in keys:
                keys.append(key)
        for bracket in BRACKETED.findall(text):
            for part in re.split(r"[,;]", bracket):
                candidate = part.strip()
                if CITATION_KEY.match(candidate) and candidate not in keys:
                    keys.append(candidate)
    return keys


def sections_holding(paragraphs, paths):
    sections = []
    for path in paths:
        heading = None
        for line in path.read_text(encoding="utf-8", errors="replace").split("\n"):
            found = HEADING_LINE.match(line)
            if found:
                heading = found.group("title").strip()
                continue
            text = normalised(line)
            if text and heading and any(normalised(paragraph)[:60] in text for paragraph in paragraphs):
                entry = f"{path.name}: {heading}"
                if entry not in sections:
                    sections.append(entry)
    return sections


def markdown_files_in(folder):
    if not folder or not folder.is_dir():
        return []
    return sorted(folder.rglob("*.md"))


def read_first(config, note):
    files = notable_files(config)
    targets = target_paths(note.stem, files)
    quotes_keys = set()
    if config.sources.quotes and config.sources.quotes.is_file():
        quotes_keys = set(entry_keys(config.sources.quotes.read_text(encoding="utf-8"), skip_fenced=True))
    anchors = note.quoted_paragraphs or [text for text in [note.flagged_text] if text]
    keys = citation_keys_in(anchors + [note.reader_text])
    related = []
    if config.rules.decisions and config.rules.decisions.is_file():
        related = [{"id": found.entry.id, "status": found.entry.status,
                    "title": found.entry.title, "reason": found.reason}
                   for found in match_finding(read_decisions(config.rules.decisions), note.reader_text)]
    book_files = {
        "decisions": config.rules.decisions, "glossary": config.rules.glossary,
        "stance": config.thinking.stance, "voice": config.rules.voice,
        "audience": config.thinking.audience,
    }
    return {
        "note": note.id,
        "tier": note.tier or "not set",
        "text files": [relative(config, path) for path in targets] if note.stem != WHOLE_BOOK else ["every manuscript file"],
        "sections": sections_holding(anchors, targets),
        "always read": {name: relative(config, path) for name, path in book_files.items()
                        if path and Path(path).is_file()},
        "related decisions": related,
        "citation keys": [{"key": key, "in quotes": "in quotes" if key in quotes_keys else "NOT in quotes"}
                          for key in keys],
        "quotes file": relative(config, config.sources.quotes) if config.sources.quotes else None,
        "argument files": [relative(config, path)
                           for path in markdown_files_in(config.thinking.argument)],
        "doubts files": [relative(config, path)
                         for path in markdown_files_in(config.thinking.doubts)],
    }


def print_listing(listing):
    total = 0
    for entry in listing:
        print(f"{entry['file']}  {len(entry['notes'])} open")
        for note in entry["notes"]:
            state = "" if note["analysed"] else "  (not analysed)"
            tier = note["tier"] or "-"
            print(f"  {note['id']:<28} {tier:<8} {note['title']}{state}")
        total += len(entry["notes"])
    print(f"TOTAL  {total} open notes in {len(listing)} files")


def print_read_first(result):
    for name, value in result.items():
        if isinstance(value, dict):
            print(f"{name}:")
            for inner_name, inner_value in value.items():
                print(f"  {inner_name}: {inner_value}")
        elif isinstance(value, list):
            print(f"{name}:" + ("" if value else " none"))
            for item in value:
                if isinstance(item, dict):
                    print("  " + "  ".join(f"{inner_value}" for inner_value in item.values()))
                else:
                    print(f"  {item}")
        else:
            print(f"{name}: {value if value is not None else 'none'}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="open-notes.py",
        description="List, check and prepare the open notes of a book. "
                    "Notes live in the folder 'notes' from the book config, one file "
                    "per manuscript, thinking or sales-text file, plus whole-book.md.")
    add_config_arguments(parser)
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="open notes per file")
    listing.add_argument("--file", metavar="NAME", help="only the notes for this file name")
    listing.add_argument("--format", choices=("text", "json"), default="text")
    checking = commands.add_parser("check", help="headings point at real files, quoted paragraphs still exist")
    add_output_arguments(checking)
    next_id = commands.add_parser("next-id", help="the id for a new note on this file")
    next_id.add_argument("name",
                         help=f"manuscript, thinking or sales-text file name, or {WHOLE_BOOK}")
    first = commands.add_parser("read-first", help="what to read before working on one note")
    first.add_argument("note_id", nargs="+", help="the note id, e.g. 110-chapter-1 #2 (a title after it is ignored)")
    first.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def run(args):
    config = config_from_args(args)
    if args.command == "list":
        only = file_name_stem(args.file) if args.file else None
        listing = open_notes_listing(config, only)
        if args.format == "json":
            print(json.dumps(listing, indent=2))
        else:
            print_listing(listing)
        return 0
    if args.command == "check":
        report = CheckReport(TOOL, FINDING_CLASSES)
        check_notes(config, report)
        return report.emit(args.format)
    if args.command == "next-id":
        print(next_note_id(config, file_name_stem(args.name)))
        return 0
    note = find_note(config, " ".join(args.note_id))
    if note is None:
        return tool_failed(f"no open note '{' '.join(args.note_id)}'", TOOL)
    result = read_first(config, note)
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print_read_first(result)
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except (ConfigError, OSError, ValueError) as error:
        return tool_failed(str(error), TOOL)


if __name__ == "__main__":
    sys.exit(main())
