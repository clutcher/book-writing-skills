import json
import unittest

from support import NEW_BOOK, PREVIOUS_BOOK, TemporaryBook, run_script

from decisions import (DECIDED_CHANGED, DECIDED_NO_CHANGE, OPEN_FIX_OWED, OPEN_UNDISCUSSED,
                       index_is_current, match_finding, parse_decisions, read_decisions,
                       render_index, run_policy, with_current_index)

NEW_BOOK_DECISIONS = NEW_BOOK / "rules" / "decisions.md"

OLD_STYLE = """# Decisions

# 1. DECIDED / no change

## 1.1 Keep the long example

- **Aliases:** `A-1`
- **Idea.** The example is too long.
- **Decision.** Keep it.
- **Change.** None
- **Why.** It is the only full example.
- **Decided.** 2025-01-01
- **Refs.** none

# 4. OPEN / fix owed

## 4.1 Fix the second table -- RESOLVED

- **Aliases:** `B-2`
- **Idea:** A table row is wrong.
- **Decision:** Correct it.
- **Change:** Done.
- **Why:** It was checked against the source.
- **Decided:** 2025-02-02
- **Refs:** none
"""


SHORT_ENTRIES = """# Decisions

## Details

## D-1 Keep the long example

- **Status:** DECIDED / no change
- **Idea:** The example is too long.
- **Decision:** Keep it.
- **Why:** It is the only full example.
- **Decided:** 2025-01-01
- **Merged:** D-2, D-5

---

## D-3 Does chapter two need a summary?

- **Status:** OPEN / undiscussed
- **Idea:** Chapter two ends without a summary.
- **Decision:** Question: add one, or keep the closing paragraph?
- **Decided:** None
"""

DECIDED_WITHOUT_WHY = """# Decisions

## Details

## D-4 Spell out the acronym once

- **Status:** DECIDED / changed
- **Idea:** The acronym is never spelled out.
- **Decision:** Spell it out at first use.
- **Change:** Applied
- **Decided:** 2025-03-03
"""


class DecisionsParsingTest(unittest.TestCase):
    def setUp(self):
        self.decisions = read_decisions(NEW_BOOK_DECISIONS)

    def test_should_read_entries_and_skip_fenced_examples(self):
        # then
        self.assertEqual([entry.id for entry in self.decisions.entries], ["D-1", "D-2"])

    def test_should_read_status_aliases_and_continued_values(self):
        # given
        first = self.decisions.entry("D-1")

        # then
        self.assertEqual(first.status, DECIDED_NO_CHANGE)
        self.assertEqual(first.aliases, ["L4-2", "G.7"])
        self.assertEqual(first.field("Why"), "Length follows content. Padding it was the "
                                             "rejected option, because it adds words that "
                                             "carry no idea.")
        self.assertEqual(first.keywords, ["chapter length", "short chapter"])

    def test_should_read_a_longer_field_name_as_its_canonical_field(self):
        # then
        self.assertEqual(self.decisions.entry("D-2").field("Change"),
                         "Rows 3 and 5 still carry no source.")

    def test_should_infer_status_from_section_or_title_when_not_written(self):
        # when
        decisions = parse_decisions(OLD_STYLE)

        # then
        self.assertEqual(decisions.entry("1.1").status, DECIDED_NO_CHANGE)
        self.assertEqual(decisions.entry("1.1").status_from, "section")
        self.assertEqual(decisions.entry("4.1").status, DECIDED_CHANGED)
        self.assertEqual(decisions.entry("4.1").title, "Fix the second table")


class DecisionsMatchingTest(unittest.TestCase):
    def setUp(self):
        self.decisions = read_decisions(NEW_BOOK_DECISIONS)

    def test_should_match_surely_when_the_finding_names_an_alias(self):
        # when
        found = match_finding(self.decisions, "Lens 2 finding L2-6: numbers without a source")

        # then
        self.assertEqual(found[0].entry.id, "D-2")
        self.assertEqual(found[0].aliases, ["L2-6"])
        self.assertGreaterEqual(found[0].score, 100)

    def test_should_match_by_keywords_when_no_alias_is_named(self):
        # when
        found = match_finding(self.decisions, "Chapter 3 feels unfinished: a short chapter "
                                              "compared with its neighbours")

        # then
        self.assertEqual(found[0].entry.id, "D-1")
        self.assertIn("short chapter", found[0].phrases)

    def test_should_not_match_an_alias_inside_a_longer_id(self):
        # when
        found = match_finding(self.decisions, "finding L2-61 about fonts", threshold=50)

        # then
        self.assertEqual(found, [])

    def test_should_tell_a_run_to_stay_silent_on_decided_items(self):
        # then
        self.assertFalse(run_policy(DECIDED_NO_CHANGE).may_report)
        self.assertEqual(run_policy(OPEN_FIX_OWED).action, "regression-check")
        self.assertEqual(run_policy(OPEN_UNDISCUSSED).action, "normal")


class DecisionsCommandLineTest(unittest.TestCase):
    def test_should_report_no_defects_when_the_file_is_well_formed(self):
        # when
        result = run_script("decisions.py", "check", cwd=NEW_BOOK)

        # then
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("D-2\tfix-owed\t", result.stdout)
        self.assertTrue(result.stdout.rstrip().endswith(
            "TOTAL     0 defects, 1 informational, 0 advisory"))

    def test_should_report_defects_when_status_is_unknown_or_fields_are_missing(self):
        # given
        with TemporaryBook() as folder:
            (folder / "rules").mkdir()
            (folder / "rules" / "decisions.md").write_text(
                "# Decisions\n\n## D-1 Something\n\n- **Status:** MAYBE\n- **Idea:** x\n",
                encoding="utf-8")

            # when
            result = run_script("decisions.py", "check", "--format", "json", cwd=folder)

        # then
        self.assertEqual(result.returncode, 1)
        classes = {item["class"] for item in json.loads(result.stdout)["items"]}
        self.assertEqual(classes, {"unknown-status", "missing-field", "index-missing"})

    def test_should_accept_short_entries_when_their_empty_fields_are_left_out(self):
        # given
        with TemporaryBook() as folder:
            path = folder / "rules" / "decisions.md"
            path.parent.mkdir()
            path.write_text(with_current_index(SHORT_ENTRIES), encoding="utf-8")

            # when
            result = run_script("decisions.py", "check", "--format", "json", cwd=folder)

        # then
        self.assertEqual(result.returncode, 0, result.stdout)
        classes = {item["class"] for item in json.loads(result.stdout)["items"]}
        self.assertEqual(classes, {"undiscussed"})

    def test_should_report_a_missing_why_when_a_decided_entry_leaves_it_out(self):
        # given
        with TemporaryBook() as folder:
            path = folder / "rules" / "decisions.md"
            path.parent.mkdir()
            path.write_text(with_current_index(DECIDED_WITHOUT_WHY), encoding="utf-8")

            # when
            result = run_script("decisions.py", "check", "--format", "json", cwd=folder)

        # then
        self.assertEqual(result.returncode, 1)
        found = [(item["key"], item["class"]) for item in json.loads(result.stdout)["items"]]
        self.assertEqual(found, [("D-4", "missing-field")])

    def test_should_read_merged_ids_as_a_field_when_an_entry_absorbed_others(self):
        # given
        decisions = parse_decisions(SHORT_ENTRIES)

        # then
        self.assertEqual(decisions.entry("D-1").field("Merged"), "D-2, D-5")

    def test_should_write_status_lines_when_check_fix_is_given(self):
        # given
        with TemporaryBook() as folder:
            path = folder / "rules" / "decisions.md"
            path.parent.mkdir()
            path.write_text(OLD_STYLE, encoding="utf-8")

            # when
            result = run_script("decisions.py", "check", "--fix", cwd=folder)
            rewritten = read_decisions(path)

        # then
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual([entry.status_from for entry in rewritten.entries], ["field", "field"])
        self.assertEqual(rewritten.entry("4.1").status, DECIDED_CHANGED)
        self.assertTrue(index_is_current(rewritten))

    def test_should_match_from_standard_input(self):
        # when
        result = run_script("decisions.py", "match", "--json", cwd=NEW_BOOK,
                            stdin="See L4-2 again: chapter three is short")

        # then
        found = json.loads(result.stdout)
        self.assertEqual(found[0]["id"], "D-1")
        self.assertFalse(found[0]["may_report"])

    def test_should_only_print_a_new_entry_when_add_is_a_dry_run(self):
        # given
        with TemporaryBook(NEW_BOOK) as folder:
            before = (folder / "rules" / "decisions.md").read_text(encoding="utf-8")

            # when
            result = run_script("decisions.py", "add", "--title", "Name the metaphor once",
                                "--status", OPEN_UNDISCUSSED, "--idea", "x", "--decision",
                                "Nothing decided", "--why", "y", "--decided", "2025-05-05",
                                cwd=folder)
            after = (folder / "rules" / "decisions.md").read_text(encoding="utf-8")

        # then
        self.assertIn("## D-3 Name the metaphor once", result.stdout)
        self.assertEqual(before, after)

    def test_should_leave_out_empty_fields_when_add_is_given_no_value_for_them(self):
        # given
        with TemporaryBook(NEW_BOOK) as folder:
            # when
            result = run_script("decisions.py", "add", "--title", "Name the metaphor once",
                                "--status", OPEN_UNDISCUSSED, "--idea", "x", "--decision",
                                "Question: once or twice?", "--decided", "None", cwd=folder)

        # then
        self.assertEqual(result.returncode, 0, result.stdout)
        for name in ("Aliases", "Change", "Why", "Refs", "Keywords"):
            self.assertNotIn(f"**{name}:**", result.stdout)

    def test_should_refuse_a_decided_entry_when_add_is_given_no_why(self):
        # given
        with TemporaryBook(NEW_BOOK) as folder:
            # when
            result = run_script("decisions.py", "add", "--title", "Name the metaphor once",
                                "--status", DECIDED_CHANGED, "--idea", "x", "--decision",
                                "Name it once", cwd=folder)

        # then
        self.assertEqual(result.returncode, 2)

    def test_should_append_an_entry_that_parses_back_when_add_is_fixed(self):
        # given
        with TemporaryBook(NEW_BOOK) as folder:
            # when
            run_script("decisions.py", "add", "--title", "Name the metaphor once", "--status",
                       OPEN_UNDISCUSSED, "--alias", "L9-1", "--idea", "x", "--decision",
                       "Nothing decided", "--why", "y", "--fix", cwd=folder)
            check = run_script("decisions.py", "check", cwd=folder)
            added = read_decisions(folder / "rules" / "decisions.md").entry("D-3")

        # then
        self.assertEqual(added.status, OPEN_UNDISCUSSED)
        self.assertEqual(added.aliases, ["L9-1"])
        self.assertEqual(check.returncode, 0, check.stdout)

    def test_should_change_one_status_when_set_status_is_fixed(self):
        # given
        with TemporaryBook(NEW_BOOK) as folder:
            # when
            run_script("decisions.py", "set-status", "D-2", DECIDED_CHANGED, "--fix", cwd=folder)
            decisions = read_decisions(folder / "rules" / "decisions.md")

        # then
        self.assertEqual(decisions.entry("D-2").status, DECIDED_CHANGED)
        self.assertEqual(decisions.entry("D-1").status, DECIDED_NO_CHANGE)

    def test_should_create_a_clean_empty_file_when_init_is_fixed(self):
        # given
        with TemporaryBook() as folder:
            # when
            run_script("decisions.py", "init", "--fix", cwd=folder)
            check = run_script("decisions.py", "check", cwd=folder)
            entries = read_decisions(folder / "rules" / "decisions.md").entries

        # then
        self.assertEqual(entries, [])
        self.assertEqual(check.returncode, 0, check.stdout)

    def test_should_skip_the_check_when_the_book_has_no_decisions_file(self):
        # given
        with TemporaryBook() as folder:
            # when
            check = run_script("decisions.py", "check", cwd=folder)
            index = run_script("decisions.py", "index", cwd=folder)
            match = run_script("decisions.py", "match", "a short chapter", cwd=folder)

        # then
        self.assertEqual(check.returncode, 0)
        self.assertTrue(check.stdout.startswith("SKIPPED   the book has no decisions file"))
        self.assertEqual((index.returncode, index.stdout), (0, ""))
        self.assertEqual((match.returncode, match.stdout), (0, ""))

    def test_should_fail_as_a_tool_when_the_file_is_missing(self):
        # given
        with TemporaryBook() as folder:
            # when
            result = run_script("decisions.py", "list", cwd=folder)

        # then
        self.assertEqual(result.returncode, 2)

    def test_should_print_help_when_asked(self):
        # then
        self.assertEqual(run_script("decisions.py", "--help").returncode, 0)


class DecisionsIndexTest(unittest.TestCase):
    def test_should_list_every_entry_with_status_and_title_when_the_index_is_built(self):
        # when
        index = render_index(read_decisions(NEW_BOOK_DECISIONS))

        # then
        self.assertEqual(index.split("\n"), [
            "## Index",
            "",
            "| Id | Status | Title |",
            "|---|---|---|",
            "| D-1 | DECIDED / no change | Short chapters are fine when each covers one "
            "whole task |",
            "| D-2 | OPEN / fix owed | The speed table needs a source for every row |",
        ])

    def test_should_put_the_index_and_details_before_the_first_status_section(self):
        # when
        text = with_current_index(OLD_STYLE)

        # then
        self.assertTrue(text.startswith("# Decisions\n\n## Index\n"))
        self.assertIn("|---|---|---|\n| 1.1 | DECIDED / no change | Keep the long example |\n"
                      "| 4.1 | DECIDED / changed | Fix the second table |\n\n## Details\n\n"
                      "# 1. DECIDED / no change\n", text)
        self.assertEqual(parse_decisions(text).entry("1.1").status, DECIDED_NO_CHANGE)
        self.assertEqual(with_current_index(text), text)

    def test_should_put_the_index_before_the_first_topic_heading(self):
        # given
        text = ("# Decisions\n\nEntries are grouped by topic.\n\n---\n\n# Fonts\n\n"
                "## D-1 Keep the serif\n\n- **Status:** DECIDED / no change\n")

        # when
        rebuilt = with_current_index(text)

        # then
        self.assertIn("grouped by topic.\n\n## Index\n", rebuilt)
        self.assertIn("| D-1 | DECIDED / no change | Keep the serif |\n\n## Details\n\n---\n\n"
                      "# Fonts\n", rebuilt)

    def test_should_escape_a_bar_when_a_title_holds_one(self):
        # given
        text = "# Decisions\n\n## D-1 Keep a | b apart\n\n- **Status:** OPEN / undiscussed\n"

        # when
        index = render_index(parse_decisions(text))

        # then
        self.assertIn("| D-1 | OPEN / undiscussed | Keep a \\| b apart |", index)

    def test_should_report_a_stale_index_when_an_entry_changed_status_by_hand(self):
        # given
        with TemporaryBook(NEW_BOOK) as folder:
            path = folder / "rules" / "decisions.md"
            path.write_text(path.read_text(encoding="utf-8").replace(
                "- **Status:** OPEN / fix owed", "- **Status:** DECIDED / changed"),
                encoding="utf-8")

            # when
            before = run_script("decisions.py", "check", "--format", "tsv", cwd=folder)
            fixed = run_script("decisions.py", "check", "--fix", "--format", "tsv", cwd=folder)
            index = run_script("decisions.py", "index", cwd=folder)

        # then
        self.assertEqual(before.returncode, 1)
        self.assertIn("index\tindex-stale", before.stdout)
        self.assertEqual(fixed.returncode, 0, fixed.stdout)
        self.assertIn("| D-2 | DECIDED / changed |", index.stdout)

    def test_should_report_a_missing_index_when_the_file_is_in_the_previous_format(self):
        # when
        result = run_script("decisions.py", "check", "--format", "tsv", cwd=PREVIOUS_BOOK)

        # then
        self.assertEqual(result.returncode, 1)
        self.assertIn("index\tindex-missing", result.stdout)

    def test_should_keep_the_index_current_when_add_and_set_status_write(self):
        # given
        with TemporaryBook(NEW_BOOK) as folder:
            # when
            run_script("decisions.py", "add", "--title", "Name the metaphor once", "--status",
                       OPEN_UNDISCUSSED, "--idea", "x", "--decision", "Nothing decided",
                       "--why", "y", "--fix", cwd=folder)
            run_script("decisions.py", "set-status", "D-1", OPEN_UNDISCUSSED, "--fix",
                       cwd=folder)
            decisions = read_decisions(folder / "rules" / "decisions.md")

        # then
        self.assertTrue(index_is_current(decisions))
        self.assertIn("| D-3 | OPEN / undiscussed | Name the metaphor once |",
                      render_index(decisions))


if __name__ == "__main__":
    unittest.main()
