#!/usr/bin/env python3
"""Check how often the book's coined terms appear, where, and in which compounds.

The terms come from the book config: `terms.families` (term, role, other forms) drives the
density report, `terms.compounds` drives the compound check.

Roles:
    primary    a coined term; needs the full learning phase (10-15 encounters)
    antonym    the opposite of a coined term; its own word family, its own learning phase
    borrowed   known from another field; no learning phase

A book may have several pairs: each antonym pairs with the nearest primary listed above it that
has no antonym yet. List each primary, then its antonym.

The report shows, per chapter and per term: counts and density, a phase summary (--phases),
gaps inside a chapter over 3,000 words, where in each chapter the mentions sit (intro, body,
summary), distance statistics, antonym pairs within 100 words (interference while learning),
paragraphs with more than two mentions of one term, the largest gaps, and uses of a term in a
compound the book has not accepted (drift). A spread that is uneven is expected: dense while
the reader learns the term, sparse in maintenance, denser where the meaning deepens.

Chapters are the manuscript files the book config classifies as chapters, in chapter order.
Order matters: phases, gaps and deserts all read the files in order. `--pattern GLOB` names the
chapter files for a book whose names the config does not match.

--first-use reports the first emphasised use (*italic* or **bold**) of each glossary term
(`rules.glossary`). Only entries under `## Defined terms` are italic candidates;
`--all-kinds` also lists the usage and drift guards.

The research behind every threshold is in `references/coined-terms.md` of this skill.
The report is advisory: the exit code is 0 unless the check could not run (2).
"""

import argparse
import contextlib
import io
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

from book_files import (ConfigError, SAMPLE_BOOK, add_config_arguments, config_for_targets,
                        natural_sort_key, tool_failed)
from book_config import TermFamily

WORDS_PER_PAGE = 390
SUMMARY_HEADING = "Summary"
MAINTENANCE_DENSITY = 10_000
LEARNING_MIN = 10
LEARNING_MAX = 15
ANTONYM_WINDOW = 100
MAX_PER_PARAGRAPH = 2
WITHIN_CHAPTER_DESERT = 3000


FUNCTION_WORDS_AFTER = {
    "and", "or", "but", "yet", "because", "when", "if", "that", "which",
    "who", "than", "while", "so",
    "to", "in", "on", "at", "by", "for", "with", "from", "of", "about",
    "into", "onto", "upon", "between", "within", "through", "under", "over",
    "against", "among", "across", "around", "before", "after", "during",
    "since", "until", "throughout", "via", "per",
    "is", "are", "was", "were", "be", "been", "being", "am",
    "become", "becomes", "became", "seem", "seems", "seemed",
    "remain", "remains", "remained", "appear", "appears", "appeared",
    "means", "describes", "denotes", "refers", "signals", "captures",
    "names", "represents", "indicates", "implies", "suggests", "carries",
    "gains", "holds", "provides",
    "will", "would", "shall", "should", "can", "could", "may", "might",
    "must", "do", "does", "did", "has", "have", "had",
}


SENTENCE_END_PUNCT = {".", "!", "?", ";", ":"}


def _has_sentence_boundary(text, start, end):
    if start >= end or start < 0 or end > len(text):
        return False
    for i in range(start, end):
        if text[i] in SENTENCE_END_PUNCT:
            if i + 1 >= len(text) or text[i + 1].isspace():
                return True
    return False


def antonym_pairs(families):
    pairs = {}
    last_primary = None
    for family in families:
        if family.role == "primary":
            last_primary = family.term
        elif family.role == "antonym" and last_primary and last_primary not in pairs:
            pairs[last_primary] = family.term
            pairs[family.term] = last_primary
    return pairs


def term_groups_from_families(families):
    pairs = antonym_pairs(families)
    term_groups = []
    for family in families:
        alternatives = [re.escape(family.term)] + [re.escape(a) for a in family.also]
        pattern = r"(?i)\b(?:" + "|".join(alternatives) + r")\w*\b"
        term_groups.append({"name": family.term, "patterns": [pattern],
                            "role": family.role, "antonym": pairs.get(family.term)})
    return term_groups


def is_prose_line(line):
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("#"):
        return False
    if stripped.startswith("|") and stripped.endswith("|"):
        return False
    if stripped.startswith("```"):
        return False
    if stripped.startswith("- ") or stripped.startswith("* "):
        return False
    return True


def count_prose_words_per_line(lines):
    in_code_block = False
    word_counts = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            word_counts.append(0)
            continue
        if in_code_block:
            word_counts.append(0)
            continue
        if is_prose_line(line):
            word_counts.append(len(line.split()))
        else:
            word_counts.append(0)
    return word_counts


def detect_zones(lines):
    first_section = None
    summary_start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## ") and first_section is None:
            first_section = i
        if re.match(r"^## " + re.escape(SUMMARY_HEADING), stripped, re.IGNORECASE):
            summary_start = i
    return first_section, summary_start


def get_zone(line_idx, first_section, summary_start):
    if first_section is not None and line_idx < first_section:
        return "intro"
    if summary_start is not None and line_idx >= summary_start:
        return "summary"
    return "body"


def build_positions(filepath, term_groups):
    text = Path(filepath).read_text(encoding="utf-8")
    lines = text.split("\n")
    prose_words_per_line = count_prose_words_per_line(lines)
    total_prose_words = sum(prose_words_per_line)
    raw_word_count = len(text.split())
    fname = Path(filepath).name.replace(".md", "").replace("chapter-", "Ch")

    first_section, summary_start = detect_zones(lines)

    cumulative_prose_words = 0
    positions = []
    in_code_block = False

    for line_idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        for group in term_groups:
            for pattern in group["patterns"]:
                for m in re.finditer(pattern, line):
                    words_before_match = len(line[:m.start()].split()) if m.start() > 0 else 0
                    word_pos = cumulative_prose_words + words_before_match
                    positions.append({
                        "word_pos": word_pos,
                        "file": fname,
                        "line": line_idx + 1,
                        "line_text": line,
                        "match_start": m.start(),
                        "match_end": m.end(),
                        "term": group["name"],
                        "role": group["role"],
                        "antonym": group["antonym"],
                        "matched": m.group(),
                        "zone": get_zone(line_idx, first_section, summary_start),
                    })

        cumulative_prose_words += prose_words_per_line[line_idx]

    return {
        "file": filepath,
        "fname": fname,
        "word_count": total_prose_words,
        "raw_word_count": raw_word_count,
        "positions": positions,
    }


CHAPTER_NUMBERS = {}


def extract_chapter_number(filename):
    if filename in CHAPTER_NUMBERS:
        return CHAPTER_NUMBERS[filename]
    m = re.search(r"chapter-(\d+)", filename)
    if m:
        return int(m.group(1))
    return 999


def compute_global_positions(all_file_data):
    all_positions = []
    cumulative_offset = 0

    for fd in all_file_data:
        for p in fd["positions"]:
            all_positions.append({
                **p,
                "global_pos": cumulative_offset + p["word_pos"],
            })
        cumulative_offset += fd["word_count"]

    all_positions.sort(key=lambda x: x["global_pos"])
    return all_positions


def compute_distances(all_positions, filter_term=None):
    if filter_term:
        positions = [p for p in all_positions if p["term"] == filter_term]
    else:
        positions = all_positions

    if len(positions) < 2:
        return None

    gaps = []
    for i in range(len(positions) - 1):
        dist = positions[i + 1]["global_pos"] - positions[i]["global_pos"]
        gaps.append((dist, positions[i], positions[i + 1]))

    distances = sorted([g[0] for g in gaps])
    top_gaps = sorted(gaps, key=lambda x: -x[0])[:10]
    n = len(distances)

    avg = sum(distances) / n
    median = distances[n // 2] if n % 2 == 1 else (distances[n // 2 - 1] + distances[n // 2]) / 2
    p10 = distances[max(0, int(n * 0.1))]
    p90 = distances[min(n - 1, int(n * 0.9))]

    return {
        "positions": positions,
        "count": len(positions),
        "distances": distances,
        "min": distances[0],
        "max": distances[-1],
        "avg": round(avg),
        "median": round(median),
        "p10": p10,
        "p90": p90,
        "top_gaps": top_gaps,
    }


def detect_antonym_interference(all_positions, window=ANTONYM_WINDOW):
    co_occurrences = []
    paragraph_clusters = {}

    for i, p in enumerate(all_positions):
        if not p.get("antonym"):
            continue
        for j in range(i + 1, len(all_positions)):
            q = all_positions[j]
            dist = q["global_pos"] - p["global_pos"]
            if dist > window:
                break
            if q["term"] == p["antonym"]:
                co_occurrences.append((dist, p, q))

        key = (p["file"], p["line"])
        if key not in paragraph_clusters:
            paragraph_clusters[key] = {"terms": set(), "count": 0}
        paragraph_clusters[key]["terms"].add(p["term"])
        paragraph_clusters[key]["count"] += 1

    dense_paragraphs = []
    for (fname, line), info in paragraph_clusters.items():
        if len(info["terms"]) > 1 and info["count"] >= 3:
            dense_paragraphs.append((fname, line, info["count"], info["terms"]))

    dense_paragraphs.sort(key=lambda x: -x[2])
    return co_occurrences, dense_paragraphs


def detect_paragraph_clustering(all_positions, max_per_para=MAX_PER_PARAGRAPH):
    by_paragraph = {}
    for p in all_positions:
        key = (p["file"], p["line"], p["term"])
        by_paragraph.setdefault(key, []).append(p)

    violations = []
    for (fname, line, term), mentions in by_paragraph.items():
        if len(mentions) > max_per_para:
            violations.append((fname, line, term, len(mentions)))

    violations.sort(key=lambda x: -x[3])
    return violations


def detect_within_chapter_deserts(all_file_data, all_positions, threshold=WITHIN_CHAPTER_DESERT):
    deserts = []
    for fd in all_file_data:
        fname = fd["fname"]
        chapter_positions = [p for p in all_positions if p["file"] == fname]
        if len(chapter_positions) < 2:
            continue

        chapter_positions.sort(key=lambda x: x["global_pos"])

        for i in range(len(chapter_positions) - 1):
            gap = chapter_positions[i + 1]["global_pos"] - chapter_positions[i]["global_pos"]
            if gap >= threshold:
                deserts.append((fname, gap, chapter_positions[i], chapter_positions[i + 1]))

    deserts.sort(key=lambda x: -x[1])
    return deserts


def _tokenize_line(line):
    tokens = []
    for m in re.finditer(r"[A-Za-z0-9]+", line):
        tokens.append((m.group().lower(), m.start(), m.end()))
    return tokens


def _token_matches(source_tok, compound_tok, is_family_slot, family_names_lower):
    if is_family_slot:
        return source_tok == compound_tok or source_tok.startswith(compound_tok)
    if source_tok == compound_tok:
        return True
    if source_tok == compound_tok + "s":
        return True
    return False


def detect_compound_drift(all_positions, all_file_data, compounds, family_names):
    if not compounds:
        return []

    family_names_lower = {n.lower() for n in family_names}

    compound_specs = []
    families_with_compounds = set()
    for phrase in compounds:
        comp_tokens = re.findall(r"[A-Za-z0-9]+", phrase.lower())
        if not comp_tokens:
            continue
        family_indices = [i for i, t in enumerate(comp_tokens) if t in family_names_lower]
        if not family_indices:
            family_indices = list(range(len(comp_tokens)))
        for fi in family_indices:
            tok = comp_tokens[fi]
            if tok in family_names_lower:
                families_with_compounds.add(tok)
        compound_specs.append({
            "phrase": phrase,
            "tokens": comp_tokens,
            "family_indices": family_indices,
        })

    file_lines = {}
    for fd in all_file_data:
        text = Path(fd["file"]).read_text(encoding="utf-8")
        file_lines[fd["fname"]] = text.split("\n")

    drifts = []

    for p in all_positions:
        matched_lower = p["matched"].lower()
        line_text = p.get("line_text", "")
        match_start = p.get("match_start", 0)
        match_end = p.get("match_end", 0)

        term_lower = p["term"].lower()
        if term_lower not in families_with_compounds:
            continue

        tokens = _tokenize_line(line_text)
        hit_token_idx = None
        for ti, (_, start, end) in enumerate(tokens):
            if start == match_start:
                hit_token_idx = ti
                break
        if hit_token_idx is None:
            for ti, (_, start, end) in enumerate(tokens):
                if start <= match_start < end:
                    hit_token_idx = ti
                    break
        if hit_token_idx is None:
            continue

        accepted_by_compound = False
        for spec in compound_specs:
            comp_tokens = spec["tokens"]
            for fi in spec["family_indices"]:
                start_idx = hit_token_idx - fi
                end_idx = start_idx + len(comp_tokens)
                if start_idx < 0 or end_idx > len(tokens):
                    continue
                ok = True
                for j, comp_tok in enumerate(comp_tokens):
                    src_tok = tokens[start_idx + j][0]
                    is_family_slot = (j in spec["family_indices"]) or (src_tok in family_names_lower)
                    if is_family_slot:
                        if not (src_tok == comp_tok or src_tok.startswith(comp_tok)):
                            ok = False
                            break
                    else:
                        if not (src_tok == comp_tok or src_tok == comp_tok + "s"):
                            ok = False
                            break
                if not ok:
                    continue
                span_start = tokens[start_idx][1]
                span_end = tokens[end_idx - 1][2]
                if _has_sentence_boundary(line_text, span_start, span_end):
                    continue
                accepted_by_compound = True
                break
            if accepted_by_compound:
                break

        if accepted_by_compound:
            continue

        next_token = tokens[hit_token_idx + 1][0] if hit_token_idx + 1 < len(tokens) else None
        next_token_start = tokens[hit_token_idx + 1][1] if hit_token_idx + 1 < len(tokens) else len(line_text)

        if _has_sentence_boundary(line_text, match_end, next_token_start):
            continue

        char_after_end = match_end
        while char_after_end < len(line_text) and line_text[char_after_end].isspace():
            char_after_end += 1
        if char_after_end >= len(line_text) or line_text[char_after_end] in ".,;:!?)\"'":
            continue

        if next_token is not None and next_token in FUNCTION_WORDS_AFTER:
            continue

        if next_token is None:
            continue

        snippet_start = max(0, hit_token_idx - 1)
        snippet_end = min(len(tokens), hit_token_idx + 4)
        snippet = " ".join(tokens[k][0] for k in range(snippet_start, snippet_end))

        drifts.append({
            "file": p["file"],
            "line": p["line"],
            "term": p["term"],
            "matched": p["matched"],
            "next": next_token,
            "snippet": snippet,
        })

    return drifts


def parse_phases(phases_str):
    phases = {}
    for part in phases_str.split(","):
        part = part.strip()
        if ":" not in part:
            continue
        range_str, phase_name = part.split(":", 1)
        phase_name = phase_name.strip()
        if "-" in range_str:
            start, end = range_str.split("-")
            for ch in range(int(start.strip()), int(end.strip()) + 1):
                phases[ch] = phase_name
        else:
            phases[int(range_str.strip())] = phase_name
    return phases


def print_distance_stats(dist, label="all terms"):
    print(f"  [{label}]")
    print(f"    Min:      {dist['min']:>6}")
    print(f"    P10:      {dist['p10']:>6}")
    print(f"    Median:   {dist['median']:>6}")
    print(f"    Average:  {dist['avg']:>6}")
    print(f"    P90:      {dist['p90']:>6}")
    print(f"    Max:      {dist['max']:>6}")

    if dist["median"] < 300:
        print(f"    WARNING: median ({dist['median']}w) is very dense -- risk of formulaic feel")
    elif dist["median"] < 500:
        print(f"    NOTE: median ({dist['median']}w) is dense -- ~1.5 pages between mentions")


def print_report(all_file_data, term_groups, compounds, page_override=None,
                 verbose=False, debug=False, phases=None, run_compound_drift=True):
    all_file_data.sort(key=lambda r: extract_chapter_number(Path(r["file"]).name))

    total_words = sum(r["word_count"] for r in all_file_data)
    total_raw = sum(r["raw_word_count"] for r in all_file_data)
    total_pages = page_override or (total_raw / WORDS_PER_PAGE)

    term_names = [g["name"] for g in term_groups]

    print("=" * 80)
    print("TERM DENSITY REPORT")
    print("=" * 80)
    print(f"Files:       {len(all_file_data)}")
    print(f"Raw words:   {total_raw:,} (everything)")
    print(f"Prose words: {total_words:,} (excluding code/tables/headers)")
    print(f"Est. pages:  {total_pages:.0f} (from raw, at {WORDS_PER_PAGE} w/p)")
    print()

    has_phases = phases is not None
    header = f"{'Chapter':<30} {'Words':>7}"
    if has_phases:
        header += f"  {'Phase':>12}"
    for tn in term_names:
        header += f"  {tn:>10}"
    header += f"  {'Combined':>10}  {'Density':>12}"
    print(header)
    print("-" * len(header))

    grand_totals = {tn: 0 for tn in term_names}
    chapter_gaps = []
    chapter_densities = []
    phase_data = {}

    for fd in all_file_data:
        short = fd["fname"]
        wc = fd["word_count"]
        ch_num = extract_chapter_number(Path(fd["file"]).name)
        phase_name = phases.get(ch_num, "?") if has_phases else None

        term_counts = {}
        for tn in term_names:
            term_counts[tn] = sum(1 for p in fd["positions"] if p["term"] == tn)

        row = f"{short:<30} {wc:>7}"
        if has_phases:
            row += f"  {phase_name:>12}"
        combined = 0
        for tn in term_names:
            c = term_counts[tn]
            grand_totals[tn] += c
            combined += c
            row += f"  {c:>10}"

        words_per_mention = round(wc / combined) if combined > 0 else float("inf")
        density_str = f"1/{words_per_mention:,}w" if combined > 0 else "none"
        row += f"  {combined:>10}  {density_str:>12}"
        print(row)

        chapter_densities.append((short, combined, wc, words_per_mention))
        if combined == 0:
            chapter_gaps.append(short)

        if has_phases and phase_name:
            if phase_name not in phase_data:
                phase_data[phase_name] = {"words": 0, "counts": {tn: 0 for tn in term_names}, "chapters": []}
            phase_data[phase_name]["words"] += wc
            for tn in term_names:
                phase_data[phase_name]["counts"][tn] += term_counts[tn]
            phase_data[phase_name]["chapters"].append(short)

    print("-" * len(header))
    grand_combined = sum(grand_totals.values())
    grand_density_str = f"1/{round(total_words / grand_combined)}w" if grand_combined > 0 else "none"
    row = f"{'TOTAL':<30} {total_words:>7}"
    if has_phases:
        row += f"  {'':>12}"
    for tn in term_names:
        row += f"  {grand_totals[tn]:>10}"
    row += f"  {grand_combined:>10}  {grand_density_str:>12}"
    print(row)

    if has_phases and phase_data:
        print()
        print("=" * 80)
        print("PHASE SUMMARY")
        print("=" * 80)

        phase_targets = {
            "learning": "Dense: 10-15 total per term across these chapters (front-loaded, expanding intervals)",
            "maintenance": "Sparse: 1-4 per chapter per term (~1 per 10,000w); never 0 in a chapter",
            "deepening": "Denser where new meaning develops (polysemy advantage, but each new sense needs learning)",
        }

        for phase_name, data in phase_data.items():
            chapters_str = ", ".join(data["chapters"])
            print(f"\n  {phase_name.upper()} ({chapters_str}): {data['words']:,}w")
            for tn in term_names:
                c = data["counts"][tn]
                density = round(data["words"] / c) if c > 0 else float("inf")
                density_str = f"1/{density:,}w" if c > 0 else "none"
                print(f"    {tn}: {c} uses ({density_str})")

            target = phase_targets.get(phase_name)
            if target:
                print(f"    Target: {target}")

    print()
    print("=" * 80)
    print("PER-TERM ANALYSIS (each word family needs its own threshold)")
    print("=" * 80)

    all_positions = compute_global_positions(all_file_data)

    for group in term_groups:
        tn = group["name"]
        count = grand_totals.get(tn, 0)
        if count == 0:
            continue

        is_borrowed = group["role"] == "borrowed"

        if is_borrowed:
            print(f"\n  {tn} (borrowed): {count} uses across ", end="")
            chapters_present = set()
            chapters_absent = []
            for fd in all_file_data:
                tc = sum(1 for p in fd["positions"] if p["term"] == tn)
                if tc > 0:
                    chapters_present.add(fd["fname"])
                else:
                    chapters_absent.append(fd["fname"])
            print(f"{len(chapters_present)} chapters")
            print(f"    Borrowed term -- reader knows this from another domain, no learning threshold needed")
            if chapters_present:
                print(f"    Present in: {', '.join(sorted(chapters_present, key=lambda x: extract_chapter_number(x)))}")
            continue

        maintenance_min = max(1, round((total_words - 15000) / MAINTENANCE_DENSITY))
        absolute_min = LEARNING_MAX + maintenance_min
        sweet_lo = round(absolute_min * 1.3)
        sweet_hi = round(absolute_min * 2.0)

        if count < absolute_min:
            status = "UNDERUSE"
        elif count < sweet_lo:
            status = "LOW"
        elif count <= sweet_hi:
            status = "GOOD"
        else:
            status = "HIGH"

        chapters_present = set()
        chapters_absent = []
        for fd in all_file_data:
            tc = sum(1 for p in fd["positions"] if p["term"] == tn)
            if tc > 0:
                chapters_present.add(fd["fname"])
            else:
                chapters_absent.append(fd["fname"])

        print(f"\n  {tn} ({group['role']}): {count} uses across {len(chapters_present)} chapters")
        print(f"    Minimum: ~{absolute_min}  Sweet spot: ~{sweet_lo}-{sweet_hi}  Status: {status}")
        if chapters_absent:
            print(f"    Absent from: {', '.join(chapters_absent)}")

        dist = compute_distances(all_positions, filter_term=tn)
        if dist:
            print_distance_stats(dist, label=tn)

    print()
    print("=" * 80)
    print("COMBINED ANALYSIS")
    print("=" * 80)

    if chapter_gaps:
        print(f"  GAPS: {', '.join(chapter_gaps)} have 0 mentions of any term")

    if len(all_file_data) > 0:
        first = all_file_data[0]
        first_name = first["fname"]
        first_combined = len(first["positions"])
        if first_combined < 10:
            print(f"  FRONT-LOADING: {first_name} has {first_combined} uses (recommended: 10-15)")
        elif first_combined <= 15:
            print(f"  FRONT-LOADING: {first_name} has {first_combined} uses (good)")
        else:
            print(f"  FRONT-LOADING: {first_name} has {first_combined} uses (above 15 -- check paragraph clustering)")

    consecutive_low = []
    run = []
    for short, combined, wc, wpm in chapter_densities:
        if combined <= 1:
            run.append(short)
        else:
            if len(run) >= 2:
                consecutive_low.append(run[:])
            run = []
    if len(run) >= 2:
        consecutive_low.append(run[:])

    for run in consecutive_low:
        print(f"  DROUGHT: {' -> '.join(run)} ({len(run)} consecutive chapters with 0-1 mentions)")

    densest = sorted(chapter_densities, key=lambda x: x[3])
    sparsest = sorted(chapter_densities, key=lambda x: -x[3] if x[3] != float("inf") else 0)
    if len(densest) > 0 and densest[0][3] != float("inf"):
        d = densest[0]
        print(f"  DENSEST: {d[0]} (1 per {d[3]:,} words, {d[1]} mentions in {d[2]:,} words)")
    if len(sparsest) > 0 and sparsest[0][1] > 0:
        s = sparsest[0]
        print(f"  SPARSEST: {s[0]} (1 per {s[3]:,} words, {s[1]} mentions in {s[2]:,} words)")

    print()
    print(f"  NOTE: Uneven distribution is expected. Research supports front-loading with")
    print(f"  expanding intervals (Mace 1932, Pimsleur 1967), not even spread. Learning-phase")
    print(f"  chapters should be dense; maintenance chapters should be sparse. Chapters that")
    print(f"  deepen term meaning (polysemy) can be denser than maintenance. Use --phases to")
    print(f"  see per-phase assessment.")

    deserts = detect_within_chapter_deserts(all_file_data, all_positions)
    if deserts:
        print()
        print("=" * 80)
        print(f"WITHIN-CHAPTER DESERTS (>{WITHIN_CHAPTER_DESERT:,}w gaps inside a chapter)")
        print("=" * 80)
        for fname, gap, from_pos, to_pos in deserts[:15]:
            pages = round(gap / WORDS_PER_PAGE, 1)
            print(f"    {gap:>5}w (~{pages:>4}p)  {fname}:L{from_pos['line']} [{from_pos['term']}] -> L{to_pos['line']} [{to_pos['term']}]")

    dist_all = compute_distances(all_positions)
    if dist_all:
        print()
        print("=" * 80)
        print("DISTANCE BETWEEN ENCOUNTERS (prose words, all terms combined)")
        print("=" * 80)
        print_distance_stats(dist_all, label="combined")
        print()
        print(f"    Maintenance target: ~{MAINTENANCE_DENSITY:,} words between encounters")

        buckets = [0] * 6
        bucket_labels = ["<100w", "100-300w", "300-1000w", "1000-3000w", "3000-10000w", ">10000w"]
        for d in dist_all["distances"]:
            if d < 100:
                buckets[0] += 1
            elif d < 300:
                buckets[1] += 1
            elif d < 1000:
                buckets[2] += 1
            elif d < 3000:
                buckets[3] += 1
            elif d < 10000:
                buckets[4] += 1
            else:
                buckets[5] += 1

        print()
        print("    Distribution of gaps:")
        max_bar = max(buckets) if max(buckets) > 0 else 1
        for label, count in zip(bucket_labels, buckets):
            bar = "#" * round(count / max_bar * 30)
            print(f"      {label:>10}: {count:>3} {bar}")

    if dist_all and dist_all.get("top_gaps"):
        print()
        print("    Top 10 largest gaps:")
        for gap_dist, from_pos, to_pos in dist_all["top_gaps"]:
            pages = round(gap_dist / WORDS_PER_PAGE, 1)
            print(f"      {gap_dist:>6}w (~{pages:>4}p)  {from_pos['file']}:L{from_pos['line']} [{from_pos['term']}] -> {to_pos['file']}:L{to_pos['line']} [{to_pos['term']}]")

    has_antonyms = any(g.get("antonym") for g in term_groups)
    if has_antonyms:
        print()
        print("=" * 80)
        print(f"ANTONYM INTERFERENCE (Tinkham 1993: co-occurrences within {ANTONYM_WINDOW}w)")
        print("=" * 80)

        co_occs, dense_paras = detect_antonym_interference(all_positions)
        print(f"  Co-occurrences within {ANTONYM_WINDOW}w window: {len(co_occs)}")

        if dense_paras:
            print(f"  Paragraphs with 3+ mixed antonym mentions (interference risk):")
            for fname, line, count, terms_set in dense_paras[:15]:
                print(f"    {fname}:L{line} -- {count} mentions ({', '.join(sorted(terms_set))})")

        by_chapter = {}
        for dist_val, p, q in co_occs:
            ch = p["file"]
            by_chapter[ch] = by_chapter.get(ch, 0) + 1

        if by_chapter:
            print(f"\n  Co-occurrences by chapter:")
            for ch in sorted(by_chapter, key=lambda x: extract_chapter_number(x)):
                print(f"    {ch}: {by_chapter[ch]}")

    para_violations = detect_paragraph_clustering(all_positions)
    if para_violations:
        print()
        print("=" * 80)
        print(f"PARAGRAPH CLUSTERING (>{MAX_PER_PARAGRAPH} mentions of same term per paragraph)")
        print("=" * 80)
        print(f"  Paragraphs exceeding {MAX_PER_PARAGRAPH} mentions of a single term: {len(para_violations)}")
        for fname, line, term, count in para_violations[:20]:
            print(f"    {fname}:L{line} -- {count}x \"{term}\"")

    print()
    print("=" * 80)
    print("POSITION ANALYSIS (intro / body / summary)")
    print("=" * 80)

    pos_header = f"  {'Chapter':<10}"
    if has_phases:
        pos_header += f" {'Phase':<12}"
    pos_header += f" {'Intro':>6} {'Body':>6} {'Summary':>8} {'Total':>6}  Notes"
    print(pos_header)
    print("  " + "-" * (len(pos_header) - 2))

    for fd in all_file_data:
        short = fd["fname"]
        ch_num = extract_chapter_number(Path(fd["file"]).name)
        phase_name = phases.get(ch_num, "?") if has_phases else None

        intro_count = sum(1 for p in fd["positions"] if p.get("zone") == "intro")
        body_count = sum(1 for p in fd["positions"] if p.get("zone") == "body")
        summary_count = sum(1 for p in fd["positions"] if p.get("zone") == "summary")
        total = intro_count + body_count + summary_count

        notes = []
        if total == 0:
            notes.append("NO MENTIONS")
        elif body_count == 0 and total > 0:
            is_learning_or_deepening = has_phases and phase_name in ("learning", "deepening")
            if is_learning_or_deepening:
                notes.append("WARNING: no body mentions (learning/deepening needs body integration)")
            else:
                notes.append("intro+summary only (OK for maintenance)")

        row = f"  {short:<10}"
        if has_phases:
            row += f" {phase_name or '?':<12}"
        row += f" {intro_count:>6} {body_count:>6} {summary_count:>8} {total:>6}"
        if notes:
            row += f"  {'; '.join(notes)}"
        print(row)

    if has_phases:
        print()
        print(f"  Research: body-integrated placement produces deeper encoding in learning/deepening")
        print(f"  chapters (Craik & Tulving 1975, Slamecka & Graf 1978). Intro+summary is sufficient")
        print(f"  for maintenance chapters (van den Broek et al. 2022). See rule 3.14.")

    if run_compound_drift and compounds:
        family_names = [g["name"] for g in term_groups]
        drifts = detect_compound_drift(all_positions, all_file_data, compounds, family_names)
        print()
        print("=" * 80)
        print("COMPOUND VOCABULARY DRIFT")
        print("=" * 80)
        if not drifts:
            print(f"  No drift compounds found. All family-term uses match the "
                  f"{len(compounds)} accepted compounds or are bare standalone uses.")
        else:
            print(f"  {len(drifts)} family-term occurrences sit in compounds not listed in the registry.")
            print()
            for d in drifts:
                print(f"  {d['file']}:L{d['line']}  {d['snippet']}")
            print()
            print("  The script flags compounds not in the registry. Add a new form to")
            print("  terms.compounds in book.yaml to accept it, or rewrite the prose.")

    if debug and dist_all:
        print()
        print("=" * 80)
        print("DEBUG: ALL MATCHES WITH WORD POSITIONS")
        print("=" * 80)
        prev = None
        for p in dist_all["positions"]:
            gap_str = ""
            if prev is not None:
                gap = p["global_pos"] - prev["global_pos"]
                gap_str = f"  (gap: {gap}w)"
            zone = p.get("zone", "?")
            print(f"  @{p['global_pos']:>6}w  {p['file']}:L{p['line']:<4} [{p['term']:<10}] [{zone:<7}] \"{p['matched']}\"{gap_str}")
            prev = p

    if verbose and not debug:
        print()
        print("=" * 80)
        print("DETAILED MATCHES")
        print("=" * 80)
        for fd in all_file_data:
            if not fd["positions"]:
                continue
            print(f"\n  {fd['fname']}:")
            for p in sorted(fd["positions"], key=lambda x: x["word_pos"]):
                print(f"    L{p['line']:>4} [{p['term']}] \"{p['matched']}\"")

    print()


def parse_custom_terms(terms_str):
    groups = []
    names = [t.strip() for t in terms_str.split(",") if t.strip()]
    for t in names:
        first = t[0]
        case_prefix = f"[{first.upper()}{first.lower()}]"
        pattern = r"\b" + case_prefix + re.escape(t[1:]) + r"\w*\b"
        groups.append({
            "name": t,
            "patterns": [pattern],
            "role": "primary" if not groups else "standalone",
            "antonym": None,
        })
    return groups


def _natural_sort_key(name):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def _derive_surface_forms(term_part):
    surfaces = set()
    parentheticals = re.findall(r"\(([^)]*)\)", term_part)
    main = re.sub(r"\([^)]*\)", "", term_part)
    main = re.sub(r"\s+", " ", main).strip()

    if main:
        surfaces.add(main)
        dash_parts = re.split(r"\s+[\u2013\u2014-]{1,2}\s+", main)
        if len(dash_parts) == 2:
            left, right = dash_parts[0].strip(), dash_parts[1].strip()
            if left and right:
                surfaces.discard(main)
                surfaces.add(f"{right} {left}")

    for raw in parentheticals:
        alias = raw.strip()
        if ":" in alias:
            alias = alias.split(":", 1)[1].strip()
        alias = re.sub(r"\s+", " ", alias).strip()
        if alias:
            surfaces.add(alias)

    return surfaces


DEFINED_TERMS_SECTION = "defined terms"


def _split_heading_kind(term_part, tail):
    inline = re.search(r"\(([^()]*)\)\s*$", term_part)
    if inline and "discipline" in inline.group(1).lower():
        return term_part[: inline.start()].strip(), inline.group(1).strip().lower()

    trailing = re.search(r"\(([^()]*)\)\s*$", tail)
    return term_part, (trailing.group(1).strip().lower() if trailing else "")


DEFAULT_HEADING_SEPARATOR = " -- "
USAGE_GUARD_MARKS = ("book usage", "discipline", "reservation")


class GlossaryUnreadable(ConfigError):
    pass


def heading_separator_pattern(separator):
    if separator == DEFAULT_HEADING_SEPARATOR:
        return re.compile(r"\s+(?:--|\u2013|\u2014)\s+")
    return re.compile(re.escape(separator))


def split_glossary_heading(heading, separator_pattern):
    parts = [part.strip() for part in separator_pattern.split(heading)]
    if len(parts) < 2:
        return None
    qualifiers = " ".join(reversed(parts[1:-1]))
    term = f"{qualifiers} {parts[0]}" if qualifiers else parts[0]
    return term, parts[-1]


def is_usage_guard(heading, kind):
    text = f"{heading} {kind}".lower()
    return any(mark in text for mark in USAGE_GUARD_MARKS)


def parse_glossary_terms(path, separator=DEFAULT_HEADING_SEPARATOR):
    glossary_path = Path(path)
    if not glossary_path.exists():
        raise SystemExit(f"Glossary file not found: {path}")

    separator_pattern = heading_separator_pattern(separator)
    entries = []
    headings_seen = 0
    in_defined_terms = False
    for line in glossary_path.read_text(encoding="utf-8").split("\n"):
        if line.startswith("## "):
            in_defined_terms = line[3:].strip().lower() == DEFINED_TERMS_SECTION
            continue
        if not line.startswith("### "):
            continue
        headings_seen += 1
        heading = line[4:].strip()
        split = split_glossary_heading(heading, separator_pattern)
        if not split:
            continue
        term_part, kind = _split_heading_kind(*split)
        surfaces = _derive_surface_forms(term_part)
        if surfaces:
            definitional = in_defined_terms and not is_usage_guard(heading, kind)
            entries.append({"key": term_part, "surfaces": surfaces,
                            "kind": kind, "definitional": definitional})

    if headings_seen and not entries:
        raise GlossaryUnreadable(
            f"WARNING: {path} has {headings_seen} '### ' headings but none reads as "
            f"'### term{separator}location'; the first-use report would be empty. Write the "
            f"headings as '### term{separator}location (kind)', with the location in the "
            f"notation of glossary_format.location_pattern in book.yaml.")
    return entries


def _find_emphasis_spans(line):
    spans = []
    masked = list(line)
    for m in re.finditer(r"\*\*(?!\*)(.+?)\*\*", line):
        spans.append((m.group(1), m.start(), "bold"))
        for i in range(m.start(), m.end()):
            masked[i] = " "
    masked_line = "".join(masked)
    for m in re.finditer(r"(?<!\*)\*(?!\*)([^*\n]+?)\*(?!\*)", masked_line):
        spans.append((m.group(1), m.start(), "italic"))
    return spans


def _emphasis_matches_surface(emphasis_text, surfaces):
    norm = emphasis_text.strip().lower()
    norm = re.sub(r"\s*\([^)]*\)\s*$", "", norm).strip()
    norm = re.sub(r"\s+", " ", norm)
    norm = re.sub(r"^(?:a|an|the)\s+", "", norm)
    for surface in surfaces:
        sl = surface.lower()
        if norm == sl or norm == sl + "s":
            return True
        if norm.endswith("s") and norm[:-1] == sl:
            return True
    return False


def find_first_emphasis_uses(files, entries):
    remaining = {e["key"]: e["surfaces"] for e in entries}
    results = {}

    for filepath in files:
        if not remaining:
            break
        current_section = "(top)"
        in_code_block = False
        lines = Path(filepath).read_text(encoding="utf-8").split("\n")
        for line_idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            if stripped.startswith("#"):
                current_section = stripped.lstrip("#").strip()
                continue

            spans = _find_emphasis_spans(line)
            if not spans:
                continue
            spans.sort(key=lambda s: s[1])
            for key in list(remaining.keys()):
                surfaces = remaining[key]
                for text, _, kind in spans:
                    if _emphasis_matches_surface(text, surfaces):
                        results[key] = {
                            "file": Path(filepath).name,
                            "line": line_idx + 1,
                            "section": current_section,
                            "kind": kind,
                            "matched": text.strip(),
                        }
                        del remaining[key]
                        break

    return results


def print_first_use_report(entries, results, skipped=()):
    print("=" * 80)
    print("TERM FIRST-USE REPORT (first emphasized *italic* / **bold** per glossary entry)")
    print("=" * 80)
    found = 0
    not_found = []
    for entry in entries:
        key = entry["key"]
        kind = entry.get("kind") or "?"
        if key in results:
            r = results[key]
            print(
                f"{key} [{kind}] | first use: {r['file']}:{r['line']} "
                f"\u00a7{r['section']} | {r['kind']} | matched: \"{r['matched']}\""
            )
            found += 1
        else:
            print(f"{key} [{kind}] | NOT FOUND (check)")
            not_found.append(key)
    print("-" * 80)
    print(f"{found}/{len(entries)} entries found emphasized; {len(not_found)} not found.")
    if not_found:
        print("NOT FOUND: " + "; ".join(not_found))
    if skipped:
        print("-" * 80)
        print(
            f"Skipped {len(skipped)} non-definitional entries (Rule 2.4 drift guards, "
            f"not Rule 9.5 italic candidates). Use --all-kinds to include them:"
        )
        for key, kind in skipped:
            print(f"  {key} [{kind}]")


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("path", nargs="?",
                        help="manuscript folder or one file (default: the manuscript)")
    parser.add_argument("--verbose", action="store_true", help="every match with context")
    parser.add_argument("--debug", action="store_true",
                        help="every match with word positions and gaps")
    parser.add_argument("--pages", type=int, help="page count (default: words / words_per_page)")
    parser.add_argument("--terms", help="comma-separated ad-hoc terms; no compound check")
    parser.add_argument("--phases", help='chapter phases, e.g. "1-3:learning,4-8:maintenance,'
                                         '9-10:deepening" (default: writing.term_phases)')
    parser.add_argument("--pattern", metavar="GLOB", help="glob that names the chapter files")
    parser.add_argument("--first-use", action="store_true",
                        help="first emphasised use of each glossary term")
    parser.add_argument("--glossary", metavar="FILE",
                        help="glossary file (default: rules.glossary)")
    parser.add_argument("--all-kinds", action="store_true",
                        help="with --first-use, also list usage and drift guards")
    parser.add_argument("--self-test", action="store_true",
                        help="check this script against the fixture books and exit")
    add_config_arguments(parser)
    return parser.parse_args(argv)


def chapter_files(folder, config, pattern):
    if pattern:
        files = sorted(Path(folder).glob(pattern), key=lambda f: extract_chapter_number(f.name))
        if not files:
            raise ConfigError(f"--pattern '{pattern}' matched no files in {folder}")
        return files, None
    files = []
    for file in Path(folder).glob("*.md"):
        kind, number = config.classify(file)
        if kind == "chapter":
            CHAPTER_NUMBERS[file.name] = number if number is not None else 999
            files.append(file)
    if files:
        files.sort(key=lambda f: (extract_chapter_number(f.name), natural_sort_key(f.name)))
        unranked = [f.name for f in files if extract_chapter_number(f.name) == 999]
        warning = None
        if unranked:
            warning = (f"WARNING: {len(unranked)} of {len(files)} chapter files carry no chapter "
                       f"number, so they sort last in an arbitrary order: "
                       f"{', '.join(unranked[:5])}{' ...' if len(unranked) > 5 else ''}")
        return files, warning
    files = sorted(Path(folder).glob("*.md"), key=lambda f: natural_sort_key(f.name))
    return files, (f"WARNING: no file in {folder} matched manuscript.chapter_pattern, so every "
                   f".md file was read in file-name order. Phases, gaps and deserts depend on "
                   f"chapter order, so the report is right only if that order is chapter order. "
                   f"Pass --pattern '<glob>' or set manuscript.chapter_pattern in book.yaml.")


def glossary_heading_separator(config):
    try:
        separator = config.get("glossary_format.heading_separator")
    except KeyError:
        separator = None
    return separator or DEFAULT_HEADING_SEPARATOR


def run_first_use(options, config, path):
    if Path(path).is_dir():
        glob = options.pattern or "*.md"
        files = sorted((str(f) for f in Path(path).glob(glob)),
                       key=lambda f: natural_sort_key(Path(f).name))
    else:
        files = [path]
    skipped = []
    if options.terms:
        names = [t.strip() for t in options.terms.split(",") if t.strip()]
        entries = [{"key": name, "surfaces": {name}, "kind": ""} for name in names]
    else:
        glossary = options.glossary or config.rules.glossary
        if not glossary or not Path(glossary).is_file():
            raise ConfigError(f"glossary not found: {glossary}; set rules.glossary in "
                              f"book.yaml or pass --glossary FILE")
        entries = parse_glossary_terms(glossary, glossary_heading_separator(config))
        if not options.all_kinds:
            skipped = [(e["key"], e["kind"]) for e in entries if not e["definitional"]]
            entries = [e for e in entries if e["definitional"]]
    results = find_first_emphasis_uses(files, entries)
    print_first_use_report(entries, results, skipped)
    return 0


def apply_config(config):
    global WORDS_PER_PAGE, SUMMARY_HEADING
    writing = config.settings.get("writing") if isinstance(config.settings.get("writing"),
                                                            dict) else {}
    WORDS_PER_PAGE = writing.get("words_per_page") or WORDS_PER_PAGE
    SUMMARY_HEADING = config.manuscript.summary_heading or SUMMARY_HEADING
    return writing.get("term_phases")


def run(argv):
    options = parse_arguments(argv)
    if options.self_test:
        return self_test()
    try:
        config = config_for_targets(options, [options.path] if options.path else [])
        default_phases = apply_config(config)
        path = options.path or str(config.manuscript.dir)
        if options.first_use:
            return run_first_use(options, config, path)
        compounds = []
        run_compound_drift = True
        if options.terms:
            term_groups = parse_custom_terms(options.terms)
            run_compound_drift = False
        else:
            families, compounds = config.terms.families, config.terms.compounds
            if not families:
                print("SKIPPED   no coined terms in book.yaml yet (terms.families)")
                return 0
            term_groups = term_groups_from_families(families)
        if Path(path).is_dir():
            files, warning = chapter_files(path, config, options.pattern)
            if warning:
                print(warning, file=sys.stderr)
        elif Path(path).is_file():
            files = [Path(path)]
        else:
            raise ConfigError(f"not a file or folder: {path}")
    except ConfigError as error:
        return tool_failed(str(error), "term-density-check")
    phases_text = options.phases or default_phases
    phases = parse_phases(phases_text) if phases_text else None
    all_file_data = [build_positions(str(f), term_groups) for f in files]
    print_report(all_file_data, term_groups, compounds, options.pages, options.verbose,
                 options.debug, phases, run_compound_drift=run_compound_drift)
    return 0


def glossary_without_term_headings_failures():
    with tempfile.TemporaryDirectory() as folder:
        glossary = Path(folder) / "glossary.md"
        glossary.write_text("# Glossary\n\n## Defined terms\n\n### lean dough\n",
                            encoding="utf-8")
        errors = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errors):
            exit_code = run(["--first-use", "--glossary", str(glossary),
                             str(SAMPLE_BOOK / "manuscript")])
    if exit_code != 2 or "glossary_format.location_pattern" not in errors.getvalue():
        return [f"a glossary whose headings do not parse gave exit {exit_code}, expected 2 "
                f"with a warning naming glossary_format.location_pattern"]
    return []


def several_antonym_pairs_failures():
    families = [TermFamily("open", "primary"), TermFamily("closed", "antonym"),
                TermFamily("early", "primary"), TermFamily("late", "antonym"),
                TermFamily("ledger", "borrowed")]
    expected = {"open": "closed", "closed": "open", "early": "late", "late": "early"}
    found = antonym_pairs(families)
    if found != expected:
        return [f"two primary and antonym pairs were paired as {found}, expected {expected}"]
    return []


def self_test():
    failures = []
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exit_code = run([str(SAMPLE_BOOK / "manuscript")])
    text = output.getvalue()
    if exit_code != 0:
        failures.append(f"book.yaml terms: exit {exit_code}, expected 0")
    drift_section = text.split("COMPOUND VOCABULARY DRIFT")[-1]
    if "COMPOUND VOCABULARY DRIFT" not in text or " crust" not in drift_section:
        failures.append("book.yaml terms: the unregistered compound '... crust' was not flagged")
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        run(["--first-use", str(SAMPLE_BOOK / "manuscript")])
    if "float test [blockquote] | first use: 110-chapter-1.md" not in output.getvalue():
        failures.append("--first-use did not find the bold first use of 'float test'")
    if "rich dough [definition sentence] | first use:" not in output.getvalue():
        failures.append("--first-use did not read the qualified heading located at 'Chapter 1'")
    failures.extend(glossary_without_term_headings_failures())
    failures.extend(several_antonym_pairs_failures())
    for line in failures:
        print(f"FAIL  {line}")
    print(f"self-test: {'PASS' if not failures else str(len(failures)) + ' failure(s)'}")
    return 1 if failures else 0


def main():
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
