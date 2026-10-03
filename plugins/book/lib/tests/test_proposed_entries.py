import unittest

from support import NEW_BOOK, TemporaryBook, run_script

from proposed_entries import bank_keys, field_problems, header_intact, insert, split_entries
from proposed_entries import vocabularies

BANK = (
    "# Sources List\n\n## Entry format\n\n```\n"
    '### [<Key>] Author(s), "Short Title" (Year)\n\n**Full title:** the title\n```\n\n'
    "Prose about the rules.\n\n---\n\n"
    '### [AAA01] A, "First" (2001)\n\n**Full title:** First\n\n---\n\n'
    '### [ZZZ99] Z, "Last" (1999)\n\n**Full title:** Last\n\n---\n'
)

RUN_FOLDER = ".book/runs/2025-04-01-1200-collect-sources-download"


class ProposedEntriesTest(unittest.TestCase):
    def test_should_skip_the_format_example_when_listing_the_keys_of_a_bank(self):
        # then
        self.assertEqual(bank_keys(BANK), ["AAA01", "ZZZ99"])

    def test_should_insert_an_entry_at_its_sorted_place_and_keep_the_example(self):
        # when
        merged = insert(BANK, "MMM50", '### [MMM50] M, "Middle" (1950)\n\n**Full title:** Middle')

        # then
        self.assertEqual(bank_keys(merged), ["AAA01", "MMM50", "ZZZ99"])
        self.assertTrue(header_intact(merged))

    def test_should_name_the_fields_that_belong_to_the_other_bank(self):
        # given
        approved, other = vocabularies("list")

        # when
        misplaced, unapproved = field_problems(
            "### [X01] x\n**Full title:** t\n**Relation:** r\n**Whatever:** w", approved, other)

        # then
        self.assertEqual(misplaced, ["Relation"])
        self.assertEqual(unapproved, ["Whatever"])

    def test_should_leave_a_correction_note_for_a_person_when_it_follows_an_entry(self):
        # when
        entries, leftovers = split_entries(
            "### [H01] h\n**Full title:** H\n\n"
            "### DELTA for the existing `[B02]` entry\n\n**Cached text:** `b02.txt`\n")

        # then
        self.assertEqual(len(entries), 1)
        self.assertNotIn("b02", entries[0][1])
        self.assertIn("DELTA", leftovers)

    def test_should_merge_the_entries_a_run_proposed_when_fix_is_given(self):
        with TemporaryBook(copy_of=NEW_BOOK) as book:
            # given
            staged = book / RUN_FOLDER / "proposed-entries" / "list"
            staged.mkdir(parents=True)
            (staged / "agent-1.md").write_text(
                '### [Kim21] Kim, "A Third Work" (2021)\n\n**Full title:** A Third Work\n'
                "**Authors:** Lee Kim\n**Year:** 2021\n", encoding="utf-8")

            # when
            result = run_script("proposed_entries.py", "--run", str(book / RUN_FOLDER),
                                "--fix", cwd=book)

            # then
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("### [Kim21]", (book / "sources" / "list.md").read_text(encoding="utf-8"))

    def test_should_change_nothing_when_run_without_fix(self):
        with TemporaryBook(copy_of=NEW_BOOK) as book:
            # given
            before = (book / "sources" / "quotes.md").read_text(encoding="utf-8")
            staged = book / RUN_FOLDER / "proposed-entries" / "quotes"
            staged.mkdir(parents=True)
            (staged / "agent-2.md").write_text(
                '### [Kim21] Kim (2021)\n\n**Verified quotes:** "bread rises when it is warm"\n',
                encoding="utf-8")

            # when
            result = run_script("proposed_entries.py", "--run", str(book / RUN_FOLDER), cwd=book)

            # then
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("dry run", result.stdout)
            self.assertEqual((book / "sources" / "quotes.md").read_text(encoding="utf-8"), before)

    def test_should_print_help_when_asked(self):
        # then
        self.assertEqual(run_script("proposed_entries.py", "--help").returncode, 0)


if __name__ == "__main__":
    unittest.main()
