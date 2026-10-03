import unittest

from support import NEW_BOOK, OLD_BOOK, TemporaryBook, run_script

from book_config import load_config
from source_registry import is_findings_bank, parse_bank, read_bank


class SourceBankTest(unittest.TestCase):
    def test_should_round_trip_both_banks_when_read_from_config_paths(self):
        # given
        config = load_config(start=NEW_BOOK)

        # when
        sources = read_bank(config.sources.list)
        quotes = read_bank(config.sources.quotes)

        # then
        self.assertEqual(sources.keys, ["Jon74", "Smi99"])
        self.assertEqual(sources.serialise(), sources.text)
        self.assertEqual(quotes.entry("Jon74").field("Guardrail"), "says nothing about speed")
        self.assertIn('"Simple things stay simple."', quotes.entry("Jon74").field("Verified quotes"))

    def test_should_tell_the_banks_apart_by_config_path(self):
        # given
        config = load_config(start=NEW_BOOK)

        # then
        self.assertTrue(is_findings_bank(config.sources.quotes, config))
        self.assertFalse(is_findings_bank(config.sources.list, config))

    def test_should_tell_old_banks_apart_by_title_when_no_config_is_given(self):
        # then
        self.assertTrue(is_findings_bank(OLD_BOOK / "review" / "fact-check-findings-registry.md"))
        self.assertFalse(is_findings_bank(OLD_BOOK / "review" / "sources-registry.md"))

    def test_should_read_a_new_book_bank_that_holds_only_its_format_header(self):
        # given
        text = "# Sources List\n\n## Entry format\n\n```\n### [<Key>] A, \"T\" (Y)\n```\n"

        # when
        bank = parse_bank(text)

        # then
        self.assertEqual(bank.keys, [])
        self.assertEqual(bank.serialise(), text)

    def test_should_refuse_a_file_with_no_entry_and_no_format_header(self):
        # then
        with self.assertRaises(ValueError):
            parse_bank("# Notes\n\nSome prose about sources.\n")

    def test_should_report_a_field_from_the_other_bank(self):
        # given
        entry = read_bank(OLD_BOOK / "review" / "sources-registry.md").entry("Jon74")

        # then
        self.assertEqual(entry.unapproved(is_findings=True), ["Full title", "Authors", "Year"])
        self.assertEqual(entry.unapproved(is_findings=False), [])

    def test_should_pass_self_test_on_the_banks_the_config_names(self):
        for book in (NEW_BOOK, OLD_BOOK):
            with self.subTest(book.name):
                # when
                result = run_script("source_registry.py", "--self-test", cwd=book)

                # then
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertEqual(result.stdout.count("round-tripped"), 2)

    def test_should_sort_only_when_fix_is_given(self):
        # given
        with TemporaryBook(NEW_BOOK) as folder:
            bank_path = folder / "sources" / "list.md"
            text = bank_path.read_text(encoding="utf-8")
            swapped = text.replace("[Jon74]", "[Zed74]")
            bank_path.write_text(swapped, encoding="utf-8")

            # when
            dry = run_script("source_registry.py", "--sort", str(bank_path), cwd=folder)
            unchanged = bank_path.read_text(encoding="utf-8")
            fixed = run_script("source_registry.py", "--sort", str(bank_path), "--fix", cwd=folder)
            keys = read_bank(bank_path).keys

        # then
        self.assertIn("pass --fix to apply", dry.stdout)
        self.assertEqual(unchanged, swapped)
        self.assertEqual(fixed.returncode, 0, fixed.stderr)
        self.assertEqual(keys, ["Smi99", "Zed74"])

    def test_should_print_help_when_asked(self):
        # then
        self.assertEqual(run_script("source_registry.py", "--help").returncode, 0)


if __name__ == "__main__":
    unittest.main()
