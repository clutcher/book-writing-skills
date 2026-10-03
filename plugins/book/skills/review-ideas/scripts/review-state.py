#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[3] / "lib"
sys.dont_write_bytecode = True
sys.path.insert(0, str(LIB_DIR))

from check_output import (ADVISORY, DEFECT, INFORMATIONAL, CheckReport, add_output_arguments,
                          tool_failed)

ROOM_STATE_FILE = "room.json"
MERGE_MAP_FILE = "merge-map.md"
REPORT_FILE = "REVIEW-REPORT.md"
VERIFICATION_DIR = "verification"
COVERAGE_HEADING = re.compile(r"^#{2,3}\s+Coverage log", re.M | re.I)
FINDING_HEADING = re.compile(r"^#{2,4}\s+(L(\d+)-(\d+))\b[\s:.—-]*(.*)$", re.M)
SEVERITY_LINE = re.compile(r"\*\*Severity:\*\*\s*`?([A-Za-z-]+)")
TIER_LINE = re.compile(r"\*\*Tier:\*\*\s*`?([A-Za-z-]+)")
VERDICT_LINE = re.compile(r"\*\*Verdict:\*\*\s*\**`?([A-Za-z-]+)")
MERGED_ID = re.compile(r"^M\d+$")
FINDING_ID = re.compile(r"^L\d+-\d+$")
ANY_ID = re.compile(r"\b(L\d+-\d+|M\d+)\b")
SEVERITIES = ("blocker", "major", "minor", "nit", "strength")
VERIFIED_SEVERITIES = ("blocker", "major")
VERDICTS = ("confirmed", "downgraded", "killed", "rebuttable-misreading")
QUEUE_HEADING = "Verification queue"
MERGED_HEADING = "Merged findings"

CHECK_CLASSES = {
    "finding-without-severity": DEFECT,
    "severity-unknown": DEFECT,
    "finding-in-wrong-lens": DEFECT,
    "finding-id-repeated": DEFECT,
    "queue-id-unknown": DEFECT,
    "merged-id-without-members": DEFECT,
    "verdict-unknown": DEFECT,
    "killed-in-report": DEFECT,
    "lens-report-missing": INFORMATIONAL,
    "lens-report-unfinished": INFORMATIONAL,
    "verdict-missing": INFORMATIONAL,
    "finding-without-tier": ADVISORY,
    "blocker-or-major-not-queued": ADVISORY,
}


class StateError(Exception):
    pass


def load_room(room):
    state_file = room / ROOM_STATE_FILE
    if not state_file.is_file():
        raise StateError(f"{state_file} not found: is {room} a room made by clean-room.py setup?")
    return json.loads(state_file.read_text(encoding="utf-8"))


def review_folder(room):
    nested = room / "review"
    return nested if nested.is_dir() else room


def finding_blocks(text):
    matches = list(FINDING_HEADING.finditer(text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        next_section = re.search(r"^#{1,2}\s", text[match.end():end], re.M)
        if next_section and not FINDING_HEADING.match(text[match.end() + next_section.start():]):
            end = match.end() + next_section.start()
        yield match, text[match.end():end]


def read_findings(room, room_state):
    findings, lens_files = [], []
    review_dir = review_folder(room)
    for lens in room_state["lenses"]:
        path = review_dir / lens["file"]
        exists = path.is_file()
        text = path.read_text(encoding="utf-8") if exists else ""
        lens_files.append({"lens": lens["number"], "name": lens["name"], "weight": lens["weight"],
                           "file": lens["file"], "exists": exists,
                           "finished": bool(exists and COVERAGE_HEADING.search(text))})
        for match, body in finding_blocks(text):
            severity = SEVERITY_LINE.search(body)
            tier = TIER_LINE.search(body)
            findings.append({
                "id": match.group(1),
                "lens": lens["number"],
                "id_lens": int(match.group(2)),
                "severity": severity.group(1).lower() if severity else "",
                "tier": tier.group(1).lower() if tier else "",
                "title": match.group(4).strip(),
            })
    return lens_files, findings


def markdown_table_after(text, heading):
    section = re.search(rf"^#{{2,3}}\s+{re.escape(heading)}\s*$(.*?)(?=^#{{1,3}}\s|\Z)", text, re.M | re.S)
    if not section:
        return None
    rows = [line.strip() for line in section.group(1).splitlines() if line.strip().startswith("|")]
    if len(rows) < 2:
        return []
    header = [cell.strip().lower() for cell in rows[0].strip("|").split("|")]
    table = []
    for row in rows[2:]:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        table.append(dict(zip(header, cells)))
    return table


def clean_id(cell):
    found = ANY_ID.search(cell.replace("*", ""))
    return found.group(1) if found else cell.strip()


def read_merge_map(room):
    path = review_folder(room) / MERGE_MAP_FILE
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    merged = {}
    for row in markdown_table_after(text, MERGED_HEADING) or []:
        merged_id = clean_id(row.get("merged id", ""))
        members = ANY_ID.findall(row.get("members", "") or row.get("contributing findings", ""))
        merged[merged_id] = [member for member in members if FINDING_ID.match(member)]
    queue = []
    table = markdown_table_after(text, QUEUE_HEADING)
    for row in table or []:
        queue.append({
            "id": clean_id(row.get("id", "")),
            "severity": row.get("severity", "").strip("` *").lower(),
            "wave": row.get("wave", "").strip(),
            "group": row.get("group", "").strip(),
            "finding": row.get("finding", "").strip(),
        })
    return {"merged": merged, "queue": queue, "has_queue": table is not None}


def read_verdicts(room, queue):
    for item in queue:
        path = review_folder(room) / VERIFICATION_DIR / f"{item['id']}.md"
        item["file_exists"] = path.is_file()
        verdict = VERDICT_LINE.search(path.read_text(encoding="utf-8")) if path.is_file() else None
        item["verdict"] = verdict.group(1).lower() if verdict else ""
    return queue


def wave_key(wave):
    return (0, int(wave)) if str(wave).isdigit() else (1, str(wave))


def collect_state(room):
    room_state = load_room(room)
    lens_files, findings = read_findings(room, room_state)
    merge_map = read_merge_map(room)
    queue = read_verdicts(room, merge_map["queue"]) if merge_map else []
    report_exists = (review_folder(room) / REPORT_FILE).is_file()
    return room_state, lens_files, findings, merge_map, queue, report_exists


def next_step(room_state, lens_files, merge_map, queue, report_exists):
    missing = [lens for lens in lens_files if not lens["finished"]]
    if missing:
        ordered = sorted(missing, key=lambda lens: (lens["weight"] != "blocker", lens["lens"]))
        batch = ordered[:int(room_state.get("lens_batch", 3))]
        return {"stage": "A", "action": "run lens agents",
                "items": [f"Lens {lens['lens']}: {lens['name']} -> review/{lens['file']}" for lens in batch]}
    if merge_map is None or not merge_map["has_queue"]:
        return {"stage": "B", "action": "write review/merge-map.md (merge and queue)", "items": []}
    open_items = [item for item in queue if item["verdict"] not in VERDICTS]
    if open_items:
        first_wave = min((item["wave"] for item in open_items), key=wave_key)
        wave_items = [item for item in open_items if item["wave"] == first_wave]
        groups = {}
        for item in wave_items:
            groups.setdefault(item["group"] or "solo", []).append(item["id"])
        items = []
        for group, ids in groups.items():
            if group.lower() == "solo":
                items += [f"solo: {finding_id}" for finding_id in ids]
            else:
                items.append(f"{group}: {', '.join(ids)}")
        return {"stage": "C", "action": f"run skeptics for wave {first_wave} "
                f"(at most {room_state.get('skeptic_batch', 2)} at once)", "items": items}
    if not report_exists:
        return {"stage": "D", "action": "run check, then write review/REVIEW-REPORT.md", "items": []}
    return {"stage": "done", "action": "report written; run clean-room.py collect from the book", "items": []}


def run_status(room, output_format):
    room_state, lens_files, findings, merge_map, queue, report_exists = collect_state(room)
    step = next_step(room_state, lens_files, merge_map, queue, report_exists)
    finished = sum(lens["finished"] for lens in lens_files)
    verdicts = sum(item["verdict"] in VERDICTS for item in queue)
    summary = {
        "round": room_state.get("round"),
        "lenses_finished": finished,
        "lenses_total": len(lens_files),
        "findings": len(findings),
        "merge_map": merge_map is not None and merge_map["has_queue"],
        "queue": len(queue),
        "verdicts": verdicts,
        "report": report_exists,
        "next": step,
    }
    if output_format == "json":
        print(json.dumps(summary, indent=2))
        return 0
    print(f"round      {summary['round']}")
    print(f"lenses     {finished}/{len(lens_files)} finished")
    for lens in lens_files:
        state = "finished" if lens["finished"] else ("no coverage log" if lens["exists"] else "missing")
        print(f"  lens {lens['lens']:<3} {lens['name']:<34} {state}")
    print(f"findings   {len(findings)}")
    print(f"merge map  {'written' if summary['merge_map'] else 'missing'}")
    print(f"verdicts   {verdicts}/{len(queue)}")
    print(f"report     {'written' if report_exists else 'missing'}")
    print(f"NEXT       stage {step['stage']}: {step['action']}")
    for item in step["items"]:
        print(f"  {item}")
    return 0


def run_findings(room, output_format):
    _, lens_files, findings, _, _, _ = collect_state(room)
    if not any(lens["exists"] for lens in lens_files):
        raise StateError(f"no lens report found in {review_folder(room)}: room.json lists "
                         f"{len(lens_files)} lenses; is --room the room or the collected run folder?")
    if output_format == "json":
        print(json.dumps(findings, indent=2))
        return 0
    for finding in findings:
        print("\t".join([finding["id"], str(finding["lens"]), finding["severity"] or "-",
                         finding["tier"] or "-", finding["title"]]))
    return 0


def run_queue(room, output_format):
    _, _, _, merge_map, queue, _ = collect_state(room)
    if merge_map is None:
        raise StateError("review/merge-map.md does not exist yet (Stage B)")
    if output_format == "json":
        print(json.dumps(queue, indent=2))
        return 0
    for item in queue:
        print("\t".join([item["id"], item["severity"] or "-", item["wave"] or "-",
                         item["group"] or "-", item["verdict"] or "open"]))
    return 0


def run_check(room, output_format):
    room_state, lens_files, findings, merge_map, queue, report_exists = collect_state(room)
    report = CheckReport("review-state", CHECK_CLASSES)
    for lens in lens_files:
        if not lens["exists"]:
            report.add(lens["file"], "lens-report-missing", f"lens {lens['lens']} has not written its report")
        elif not lens["finished"]:
            report.add(lens["file"], "lens-report-unfinished", "no '## Coverage log' section yet")
    seen = {}
    for finding in findings:
        if finding["id"] in seen:
            report.add(finding["id"], "finding-id-repeated", f"also in lens {seen[finding['id']]}")
        seen[finding["id"]] = finding["lens"]
        if finding["id_lens"] != finding["lens"]:
            report.add(finding["id"], "finding-in-wrong-lens", f"written in the report of lens {finding['lens']}")
        if not finding["severity"]:
            report.add(finding["id"], "finding-without-severity", "no '**Severity:**' line")
        elif finding["severity"] not in SEVERITIES:
            report.add(finding["id"], "severity-unknown", f"'{finding['severity']}' is not one of {', '.join(SEVERITIES)}")
        if not finding["tier"] and finding["severity"] != "strength":
            report.add(finding["id"], "finding-without-tier", "no '**Tier:**' line")
    if merge_map is not None:
        merged = merge_map["merged"]
        for merged_id, members in merged.items():
            if not members:
                report.add(merged_id, "merged-id-without-members", "the merged findings table lists no L ids")
        queued_members = set()
        for item in queue:
            if MERGED_ID.match(item["id"]):
                if item["id"] not in merged:
                    report.add(item["id"], "queue-id-unknown", "not in the merged findings table")
                queued_members.update(merged.get(item["id"], []))
            elif item["id"] not in seen:
                report.add(item["id"], "queue-id-unknown", "no lens report has this finding")
            queued_members.add(item["id"])
            if item["file_exists"] and item["verdict"] not in VERDICTS:
                report.add(item["id"], "verdict-unknown",
                           f"'{item['verdict'] or 'none'}' is not one of {', '.join(VERDICTS)}")
            elif not item["file_exists"]:
                report.add(item["id"], "verdict-missing", "no verification file yet")
        if merge_map["has_queue"]:
            for finding in findings:
                if finding["severity"] in VERIFIED_SEVERITIES and finding["id"] not in queued_members:
                    report.add(finding["id"], "blocker-or-major-not-queued",
                               "a blocker or major that is not in the verification queue (merged away?)")
    if report_exists:
        report_text = (review_folder(room) / REPORT_FILE).read_text(encoding="utf-8")
        mentioned = set(ANY_ID.findall(report_text))
        merged = merge_map["merged"] if merge_map else {}
        for item in queue:
            if item["verdict"] != "killed":
                continue
            killed_ids = [item["id"], *merged.get(item["id"], [])]
            shown = [killed_id for killed_id in killed_ids if killed_id in mentioned]
            if shown:
                report.add(item["id"], "killed-in-report",
                           f"a killed finding appears in the report as {', '.join(shown)}")
    return report.emit(output_format)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Read the files of an outside review in a clean room and say what is done, "
                    "what runs next, and what is malformed. Reads only review/ and room.json, "
                    "never the manuscript. Also works on a folder made by clean-room.py collect. "
                    "Runs in the room, which has no book.yaml, so it takes --room and no --config.")
    parser.add_argument("--room", metavar="DIR", default=".",
                        help="the room folder, or a run folder made by clean-room.py collect "
                             "(default: the working directory)")
    commands = parser.add_subparsers(dest="command", required=True)
    status = commands.add_parser("status", help="what is finished and what runs next")
    status.add_argument("--format", choices=("text", "json"), default="text")
    findings = commands.add_parser("findings", help="every finding in the lens reports, one line each")
    findings.add_argument("--format", choices=("text", "json"), default="text",
                          help="text is tab-separated: id, lens, severity, tier, title")
    queue = commands.add_parser("queue", help="the verification queue and each verdict")
    queue.add_argument("--format", choices=("text", "json"), default="text",
                       help="text is tab-separated: id, severity, wave, group, verdict")
    check = commands.add_parser("check", help="format problems in the review files (check contract)")
    add_output_arguments(check)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    room = Path(args.room).expanduser().resolve()
    commands = {"status": run_status, "findings": run_findings, "queue": run_queue, "check": run_check}
    try:
        return commands[args.command](room, args.format)
    except (StateError, OSError, json.JSONDecodeError, KeyError) as error:
        return tool_failed(str(error), "review-state")


if __name__ == "__main__":
    sys.exit(main())
