import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "scripts" / "open-notes.py"
FIXTURE_BOOK = SKILL / "tests" / "fixtures" / "book"
CHAPTER_NOTES = Path("reading-notes") / "110-chapter-1.md"


def run_open_notes(book, *arguments):
    return subprocess.run([sys.executable, str(SCRIPT), *arguments], cwd=book,
                          capture_output=True, encoding="utf-8", errors="replace",
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


def finding_classes(book):
    result = run_open_notes(book, "check", "--format", "json")
    return result.returncode, [item["class"] for item in json.loads(result.stdout)["items"]]


def replace_in(path, old, new):
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError(f"{old!r} is not in {path}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def append_to(path, text):
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


class CopiedBookTestCase(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="open-notes-test-"))
        self.book = self.folder / "book"
        shutil.copytree(FIXTURE_BOOK, self.book)

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)


class CleanBookTest(CopiedBookTestCase):
    def test_should_report_no_defects_when_every_note_matches_the_text(self):
        # when
        exit_code, classes = finding_classes(self.book)

        # then
        self.assertEqual(exit_code, 0)
        self.assertEqual(sorted(set(classes)), ["not-analysed", "open-notes"])

    def test_should_list_every_open_note_per_file_when_asked(self):
        # when
        result = run_open_notes(self.book, "list", "--format", "json")

        # then
        listing = {entry["file"]: [note["id"] for note in entry["notes"]]
                   for entry in json.loads(result.stdout)}
        self.assertEqual(listing, {
            "reading-notes/110-chapter-1.md": ["110-chapter-1 #1", "110-chapter-1 #2"],
            "reading-notes/back-cover.md": ["back-cover #1"],
            "reading-notes/whole-book.md": ["whole-book #1"],
        })

    def test_should_skip_numbers_already_used_in_decisions_when_giving_a_new_id(self):
        # when
        chapter = run_open_notes(self.book, "next-id", "110-chapter-1.md").stdout.strip()
        preface = run_open_notes(self.book, "next-id", "010-preface").stdout.strip()

        # then
        self.assertEqual(chapter, "110-chapter-1 #5")
        self.assertEqual(preface, "010-preface #1")

    def test_should_name_the_section_the_sources_and_the_reasons_when_preparing_a_note(self):
        # when
        result = run_open_notes(self.book, "read-first", "110-chapter-1", "#1", "--format", "json")

        # then
        prepared = json.loads(result.stdout)
        self.assertEqual(prepared["sections"], ["110-chapter-1.md: 1.1 What Rest Does"])
        self.assertEqual(prepared["citation keys"], [{"key": "Doe20", "in quotes": "in quotes"}])
        self.assertEqual(prepared["argument files"], ["reasons/grounding.md", "reasons/hydration.md"])
        self.assertEqual(prepared["always read"]["decisions"], "decisions.md")

    def test_should_show_a_decided_entry_when_a_note_repeats_it(self):
        # when
        result = run_open_notes(self.book, "read-first", "110-chapter-1 #2", "--format", "json")

        # then
        related = json.loads(result.stdout)["related decisions"]
        self.assertEqual([(entry["id"], entry["status"]) for entry in related],
                         [("D-1", "DECIDED / no change")])

    def test_should_fail_as_a_tool_when_the_note_does_not_exist(self):
        # when
        result = run_open_notes(self.book, "read-first", "110-chapter-1 #9")

        # then
        self.assertEqual(result.returncode, 2)

    def test_should_print_help_when_asked(self):
        # when
        result = run_open_notes(self.book, "--help")

        # then
        self.assertEqual(result.returncode, 0)
        self.assertIn("read-first", result.stdout)


class ChangedTextTest(CopiedBookTestCase):
    def test_should_report_a_changed_paragraph_when_the_author_rewrote_it(self):
        # given
        replace_in(self.book / "manuscript" / "110-chapter-1.md",
                   "because the flour has had time", "because the flour had time")

        # when
        exit_code, classes = finding_classes(self.book)

        # then
        self.assertEqual(exit_code, 1)
        self.assertIn("paragraph-changed", classes)

    def test_should_only_advise_when_a_flagged_sentence_is_not_found_word_for_word(self):
        # given
        replace_in(self.book / "marketing" / "back-cover.md",
                   "A short book about bread", "A small book about bread")

        # when
        exit_code, classes = finding_classes(self.book)

        # then
        self.assertEqual(exit_code, 0)
        self.assertIn("text-not-found", classes)

    def test_should_accept_a_quote_with_the_middle_left_out(self):
        # given
        replace_in(self.book / CHAPTER_NOTES,
                   "> Flour takes up water slowly, so dough shaped in a hurry tears in the hand [Doe20]. A long rest helps only when the kitchen is warm enough.",
                   "> Flour takes up water slowly ... A long rest helps only when the kitchen is warm enough.")

        # when
        exit_code, classes = finding_classes(self.book)

        # then
        self.assertEqual(exit_code, 0)
        self.assertNotIn("paragraph-changed", classes)


class BrokenNotesTest(CopiedBookTestCase):
    def test_should_report_a_notes_file_that_names_no_text_file(self):
        # given
        (self.book / "reading-notes" / "150-chapter-9.md").write_text(
            "# Reading notes\n\n## 150-chapter-9 #1 Lost\n\n**Note:** where is this?\n",
            encoding="utf-8")

        # when
        exit_code, classes = finding_classes(self.book)

        # then
        self.assertEqual(exit_code, 1)
        self.assertIn("notes-file-unmatched", classes)

    def test_should_report_a_note_filed_under_another_file(self):
        # given
        append_to(self.book / CHAPTER_NOTES, "\n## 010-preface #1 Wrong home\n\n**Note:** moved\n")

        # when
        _, classes = finding_classes(self.book)

        # then
        self.assertIn("wrong-file", classes)

    def test_should_report_a_heading_that_is_not_a_note_id(self):
        # given
        append_to(self.book / CHAPTER_NOTES, "\n## Summary\n\nfree text\n")

        # when
        _, classes = finding_classes(self.book)

        # then
        self.assertIn("bad-heading", classes)

    def test_should_report_the_same_id_used_twice(self):
        # given
        append_to(self.book / CHAPTER_NOTES, "\n## 110-chapter-1 #2 Again\n\n**Note:** twice\n")

        # when
        _, classes = finding_classes(self.book)

        # then
        self.assertIn("duplicate-id", classes)

    def test_should_report_an_id_a_resolved_note_already_used(self):
        # given
        append_to(self.book / CHAPTER_NOTES, "\n## 110-chapter-1 #4 Reused\n\n**Note:** old number\n")

        # when
        _, classes = finding_classes(self.book)

        # then
        self.assertIn("id-used-before", classes)

    def test_should_report_a_resolved_note_left_in_the_folder(self):
        # given
        append_to(self.book / CHAPTER_NOTES,
                  "\n## 110-chapter-1 #3 Done\n\n**Note:** fixed\n**Status:** [x]\n")

        # when
        exit_code, classes = finding_classes(self.book)

        # then
        self.assertEqual(exit_code, 1)
        self.assertIn("resolved-note-left", classes)

    def test_should_report_a_paragraph_that_is_described_but_not_quoted(self):
        # given
        append_to(self.book / CHAPTER_NOTES,
                  "\n## 110-chapter-1 #3 Unquoted\n\n**Paragraph:** the summary paragraph\n**Note:** hm\n")

        # when
        _, classes = finding_classes(self.book)

        # then
        self.assertIn("paragraph-not-quoted", classes)

    def test_should_report_a_dash_between_the_id_and_the_title(self):
        # given
        append_to(self.book / CHAPTER_NOTES, "\n## 110-chapter-1 #3 \u2014 Dash title\n\n**Note:** hm\n")

        # when
        exit_code, classes = finding_classes(self.book)

        # then
        self.assertEqual(exit_code, 1)
        self.assertIn("bad-heading", classes)

    def test_should_advise_when_a_linked_note_is_no_longer_open(self):
        # given
        append_to(self.book / CHAPTER_NOTES,
                  "\n## 110-chapter-1 #3 Linked\n\n**Note:** hm\n**Linked:** #2 (same summary), #4 (closed)\n")

        # when
        exit_code, classes = finding_classes(self.book)

        # then
        self.assertEqual(exit_code, 0)
        self.assertEqual(classes.count("linked-note-missing"), 1)

    def test_should_advise_when_a_note_uses_an_old_field_name(self):
        # given
        append_to(self.book / CHAPTER_NOTES,
                  "\n## 110-chapter-1 #3 Old\n\n**Note:** hm\n**Recommendation:** swap it\n")

        # when
        exit_code, classes = finding_classes(self.book)

        # then
        self.assertEqual(exit_code, 0)
        self.assertIn("old-field-name", classes)


class MarkdownInTextTest(CopiedBookTestCase):
    def quote_in_note_and_write_in_text(self, text_markdown, quoted_as_reader_sees_it):
        append_to(self.book / "manuscript" / "110-chapter-1.md", "\n" + text_markdown + "\n")
        append_to(self.book / CHAPTER_NOTES,
                  "\n## 110-chapter-1 #3 Read in an app\n\n**Paragraph:** in the Summary:\n\n> "
                  + quoted_as_reader_sees_it + "\n\n**Note:** hm\n")

    def test_should_accept_a_quote_without_underscore_emphasis_when_the_text_has_it(self):
        # given
        self.quote_in_note_and_write_in_text("Rested dough asks _very_ little of a baker.",
                                             "Rested dough asks very little of a baker.")

        # when
        exit_code, classes = finding_classes(self.book)

        # then
        self.assertEqual(exit_code, 0)
        self.assertNotIn("paragraph-changed", classes)

    def test_should_accept_a_quote_without_the_link_address_when_the_text_has_a_link(self):
        # given
        self.quote_in_note_and_write_in_text("Read more about [rested dough](https://example.org) later.",
                                             "Read more about rested dough later.")

        # when
        exit_code, classes = finding_classes(self.book)

        # then
        self.assertEqual(exit_code, 0)
        self.assertNotIn("paragraph-changed", classes)

    def test_should_accept_a_quote_without_the_footnote_mark_when_the_text_has_one(self):
        # given
        self.quote_in_note_and_write_in_text("Time gives most of the flavour[^1] in rested dough.",
                                             "Time gives most of the flavour in rested dough.")

        # when
        exit_code, classes = finding_classes(self.book)

        # then
        self.assertEqual(exit_code, 0)
        self.assertNotIn("paragraph-changed", classes)

    def test_should_report_a_changed_short_quote_when_the_whole_paragraph_is_short(self):
        # given
        append_to(self.book / CHAPTER_NOTES,
                  "\n## 110-chapter-1 #3 Too short\n\n**Paragraph:** in the Summary:\n\n> One hour.\n\n**Note:** hm\n")

        # when
        exit_code, classes = finding_classes(self.book)

        # then
        self.assertEqual(exit_code, 1)
        self.assertIn("paragraph-changed", classes)


class DottedFileNameTest(CopiedBookTestCase):
    def setUp(self):
        super().setUp()
        (self.book / "manuscript" / "120-2.1-intro.md").write_text(
            "# 2.1 Intro\n\nA second chapter opens here.\n", encoding="utf-8")
        (self.book / "reading-notes" / "120-2.1-intro.md").write_text(
            "# Reading notes: 120-2.1-intro\n\n## 120-2.1-intro #1 Opening\n\n**Note:** thin\n",
            encoding="utf-8")

    def test_should_give_the_next_id_on_the_whole_name_when_the_file_name_has_a_dot(self):
        # when
        result = run_open_notes(self.book, "next-id", "120-2.1-intro")

        # then
        self.assertEqual(result.stdout.strip(), "120-2.1-intro #2")

    def test_should_list_the_notes_of_a_file_whose_name_has_a_dot(self):
        # when
        result = run_open_notes(self.book, "list", "--file", "120-2.1-intro.md", "--format", "json")

        # then
        listing = json.loads(result.stdout)
        self.assertEqual([note["id"] for entry in listing for note in entry["notes"]], ["120-2.1-intro #1"])


class MissingFoldersTest(CopiedBookTestCase):
    def test_should_say_skipped_when_the_book_has_no_reading_notes_folder(self):
        # given
        shutil.rmtree(self.book / "reading-notes")

        # when
        result = run_open_notes(self.book, "check")

        # then
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.stdout.strip().splitlines()[-1].startswith("SKIPPED"))

    def test_should_fail_as_a_tool_when_the_book_has_no_manuscript_folder(self):
        # given
        shutil.rmtree(self.book / "manuscript")

        # when
        result = run_open_notes(self.book, "check")

        # then
        self.assertEqual(result.returncode, 2)


class MissingFromTest(CopiedBookTestCase):
    def test_should_advise_when_a_note_does_not_say_where_it_came_from(self):
        # given
        append_to(self.book / CHAPTER_NOTES, "\n## 110-chapter-1 #3 No source\n\n**Note:** hm\n")

        # when
        exit_code, classes = finding_classes(self.book)

        # then
        self.assertEqual(exit_code, 0)
        self.assertEqual(classes.count("no-from"), 1)


NEW_LAYOUT_MOVES = (
    ("reading-notes", "notes"),
    ("reasons", "thinking/argument"),
    ("author/stance.md", "thinking/author/stance.md"),
    ("decisions.md", "rules/decisions.md"),
    ("vocabulary/glossary.md", "rules/glossary.md"),
    ("marketing", "publishing/sales-text"),
)


class NewLayoutTest(CopiedBookTestCase):
    def setUp(self):
        super().setUp()
        for old, new in NEW_LAYOUT_MOVES:
            target = self.book / new
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(self.book / old), str(target))
        (self.book / "thinking" / "doubts").mkdir()
        (self.book / "thinking" / "doubts" / "open-questions.md").write_text(
            "# Open questions\n\nIs one hour the right rest?\n", encoding="utf-8")

    def test_should_report_no_defects_when_the_book_uses_the_new_layout(self):
        # when
        exit_code, classes = finding_classes(self.book)

        # then
        self.assertEqual(exit_code, 0)
        self.assertEqual(sorted(set(classes)), ["not-analysed", "open-notes"])

    def test_should_name_argument_and_doubts_files_when_preparing_a_note(self):
        # when
        result = run_open_notes(self.book, "read-first", "110-chapter-1 #1", "--format", "json")

        # then
        prepared = json.loads(result.stdout)
        self.assertEqual(prepared["argument files"],
                         ["thinking/argument/grounding.md", "thinking/argument/hydration.md"])
        self.assertEqual(prepared["doubts files"], ["thinking/doubts/open-questions.md"])
        self.assertEqual(prepared["always read"]["decisions"], "rules/decisions.md")

    def test_should_check_a_note_on_a_thinking_file_against_that_file(self):
        # given
        argument = (self.book / "thinking" / "argument" / "grounding.md").read_text(encoding="utf-8")
        paragraph = next(block for block in argument.split("\n\n")
                         if block.strip() and not block.startswith("#"))
        (self.book / "notes" / "grounding.md").write_text(
            "# Notes: grounding\n\n## grounding #1 Check the claim\n\n**From:** check-facts, "
            "2025-04-01 09:30\n**Paragraph:** the first paragraph:\n\n> "
            + " ".join(paragraph.split()) + "\n\n**Note:** which source?\n", encoding="utf-8")

        # when
        exit_code, classes = finding_classes(self.book)

        # then
        self.assertEqual(exit_code, 0)
        self.assertNotIn("notes-file-unmatched", classes)
        self.assertNotIn("paragraph-changed", classes)

    def test_should_report_a_changed_paragraph_of_a_thinking_file(self):
        # given
        (self.book / "notes" / "grounding.md").write_text(
            "# Notes: grounding\n\n## grounding #1 Check the claim\n\n**From:** author\n"
            "**Paragraph:** the first paragraph:\n\n> A sentence that is in no argument file "
            "at all.\n\n**Note:** which source?\n", encoding="utf-8")

        # when
        exit_code, classes = finding_classes(self.book)

        # then
        self.assertEqual(exit_code, 1)
        self.assertIn("paragraph-changed", classes)


class NoteIdWithTitleTest(CopiedBookTestCase):
    def test_should_find_the_note_when_the_author_copies_the_whole_heading(self):
        # when
        result = run_open_notes(self.book, "read-first", "110-chapter-1 #1 How slowly, and how long?",
                                "--format", "json")

        # then
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["note"], "110-chapter-1 #1")


if __name__ == "__main__":
    unittest.main()
