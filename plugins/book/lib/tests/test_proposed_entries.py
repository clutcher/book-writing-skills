import unittest

from support import NEW_BOOK, TemporaryBook, run_script

from proposed_entries import bank_keys, field_problems, header_intact, insert, split_entries
from proposed_entries import vocabularies
from bibliography import read_bibliography
from source_registry import parse_bank, separator_defects

BANK = (
    "# Sources List\n\n## Entry format\n\n```\n"
    "### [<Key>]\n\n**Access URLs:** where it can be read\n```\n\n"
    "Prose about the rules.\n\n---\n\n"
    "### [AAA01]\n\n**Access status:** fetched\n\n---\n\n"
    "### [ZZZ99]\n\n**Access status:** fetched\n\n---\n"
)

EMPTY_BANK = (
    "# Sources List\n\n## Entry format\n\n```\n"
    "### [<Key>]\n\n**Access URLs:** where it can be read\n```\n"
)

RUN_FOLDER = ".book/runs/2025-04-01-1200-collect-sources-download"


class ProposedEntriesTest(unittest.TestCase):
    def test_should_skip_the_format_example_when_listing_the_keys_of_a_bank(self):
        # then
        self.assertEqual(bank_keys(BANK), ["AAA01", "ZZZ99"])

    def test_should_insert_an_entry_at_its_sorted_place_and_keep_the_example(self):
        # when
        merged = insert(BANK, "MMM50", "### [MMM50]\n\n**Access status:** fetched")

        # then
        self.assertEqual(bank_keys(merged), ["AAA01", "MMM50", "ZZZ99"])
        self.assertTrue(header_intact(merged))

    def test_should_put_a_separator_before_the_first_entry_of_an_empty_bank(self):
        # when
        merged = insert(EMPTY_BANK, "MMM50", "### [MMM50]\n\n**Access status:** fetched")

        # then
        self.assertEqual(bank_keys(merged), ["MMM50"])
        self.assertIn("```\n\n---\n\n### [MMM50]", merged)
        self.assertEqual(separator_defects(parse_bank(merged)), [])

    def test_should_keep_one_separator_when_the_last_entry_already_ends_in_one(self):
        # when
        merged = insert(BANK, "ZZZ99a", "### [ZZZ99a]\n\n**Access status:** fetched")

        # then
        self.assertEqual(separator_defects(parse_bank(merged)), [])
        self.assertNotIn("---\n\n---", merged)

    def test_should_name_the_fields_that_belong_to_the_other_bank(self):
        # given
        approved, other = vocabularies("list")

        # when
        misplaced, unapproved = field_problems(
            "### [X01]\n**Note:** t\n**Relation:** r\n**Whatever:** w", approved, other)

        # then
        self.assertEqual(misplaced, ["Relation"])
        self.assertEqual(unapproved, ["Whatever"])

    def test_should_leave_a_correction_note_for_a_person_when_it_follows_an_entry(self):
        # when
        entries, leftovers = split_entries(
            "### [H01]\n**Note:** H\n\n"
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
                "### [Kim21]\n\n**Access URLs:** https://example.org/kim-third-work\n",
                encoding="utf-8")

            # when
            result = run_script("proposed_entries.py", "--run", str(book / RUN_FOLDER),
                                "--fix", cwd=book)

            # then
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("### [Kim21]", (book / "sources" / "list.md").read_text(encoding="utf-8"))

    def test_should_reject_a_list_entry_that_carries_identity(self):
        with TemporaryBook(copy_of=NEW_BOOK) as book:
            # given
            before = (book / "sources" / "list.md").read_text(encoding="utf-8")
            staged = book / RUN_FOLDER / "proposed-entries" / "list"
            staged.mkdir(parents=True)
            (staged / "agent-1.md").write_text(
                '### [Kim21] Kim, "A Third Work" (2021)\n\n**Full title:** A Third Work\n'
                "**Year:** 2021\n", encoding="utf-8")

            # when
            result = run_script("proposed_entries.py", "--run", str(book / RUN_FOLDER),
                                "--fix", cwd=book)
            after = (book / "sources" / "list.md").read_text(encoding="utf-8")

        # then
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("identity belongs in the .bib entry", result.stdout)
        self.assertEqual(after, before)

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

    def test_should_merge_staged_bib_entries_into_the_bib_file_in_key_order(self):
        with TemporaryBook(copy_of=NEW_BOOK) as book:
            # given
            staged = book / RUN_FOLDER / "proposed-entries" / "bib"
            staged.mkdir(parents=True)
            (staged / "agent-1.bib").write_text(
                "@book{Kim21, title = {A Third Work}, author = {Kim, Lee}, year = 2021}\n"
                "@book{Jon74, title = {A Copy}, author = {Jones, Ann}, year = 1974}\n",
                encoding="utf-8")

            # when
            result = run_script("proposed_entries.py", "--run", str(book / RUN_FOLDER),
                                "--bank", "bib", "--fix", cwd=book)
            keys = read_bibliography(book / "sources" / "references.bib").keys

        # then
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("COLLISION  Jon74", result.stdout)
        self.assertEqual(keys, ["Jon74", "Kim21", "Smi99"])

    def test_should_print_help_when_asked(self):
        # then
        self.assertEqual(run_script("proposed_entries.py", "--help").returncode, 0)


if __name__ == "__main__":
    unittest.main()
