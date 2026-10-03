import datetime
import json
import unittest

from support import NEW_BOOK, TemporaryBook, run_script

from run_folders import (CHECKSUMS_FILE, changed_files, latest_run, record_checksums,
                         run_folder_name, runs_of, start_run)

MORNING = datetime.datetime(2025, 4, 1, 9, 30)


def at_minute(minute):
    return MORNING.replace(minute=minute)


class RunFolderNameTest(unittest.TestCase):
    def test_should_name_a_run_by_its_start_minute_skill_and_mode(self):
        # then
        self.assertEqual(run_folder_name("review-text", "flow", MORNING),
                         "2025-04-01-0930-review-text-flow")
        self.assertEqual(run_folder_name("check-facts", "all", MORNING, 2),
                         "2025-04-01-0930-check-facts-all-2")

    def test_should_refuse_a_skill_name_that_would_break_the_folder_name(self):
        # then
        with self.assertRaises(ValueError):
            run_folder_name("Review Text", "flow", MORNING)


class StartRunTest(unittest.TestCase):
    def test_should_keep_only_the_newest_three_runs_of_one_skill_and_mode(self):
        # given
        with TemporaryBook() as runs:
            other = start_run(runs, "review-text", "common-problems", at_minute(0))
            for minute in range(1, 6):
                start_run(runs, "review-text", "flow", at_minute(minute))

            # when
            names = [run.path.name for run in runs_of(runs, "review-text", "flow")]
            other_kept = other.is_dir()

        # then
        self.assertEqual(names, ["2025-04-01-0905-review-text-flow",
                                 "2025-04-01-0904-review-text-flow",
                                 "2025-04-01-0903-review-text-flow"])
        self.assertTrue(other_kept)

    def test_should_number_a_second_run_in_the_same_minute(self):
        # given
        with TemporaryBook() as runs:
            start_run(runs, "check-facts", "all", MORNING)

            # when
            second = start_run(runs, "check-facts", "all", MORNING)
            latest = latest_run(runs, "check-facts", "all")

        # then
        self.assertEqual(second.name, "2025-04-01-0930-check-facts-all-2")
        self.assertEqual(latest, second)

    def test_should_keep_the_new_run_when_many_runs_start_in_the_same_minute(self):
        # given
        with TemporaryBook() as runs:
            for _ in range(4):
                start_run(runs, "run-checks", "text", MORNING)

            # when
            fifth = start_run(runs, "run-checks", "text", MORNING)
            names = [run.path.name for run in runs_of(runs, "run-checks", "text")]
            fifth_kept = fifth.is_dir()

        # then
        self.assertEqual(fifth.name, "2025-04-01-0930-run-checks-text-5")
        self.assertTrue(fifth_kept)
        self.assertEqual(names, ["2025-04-01-0930-run-checks-text-5",
                                 "2025-04-01-0930-run-checks-text-4",
                                 "2025-04-01-0930-run-checks-text-3"])

    def test_should_not_mistake_a_longer_mode_for_the_asked_one(self):
        # given
        with TemporaryBook() as runs:
            start_run(runs, "review-text", "all-problems", MORNING)

            # when
            found = runs_of(runs, "review-text", "all")

        # then
        self.assertEqual(found, [])


class ChangedFilesTest(unittest.TestCase):
    def test_should_count_every_file_as_changed_when_no_run_recorded_checksums(self):
        # given
        with TemporaryBook() as book:
            chapter = book / "110-chapter-1.md"
            chapter.write_text("First draft.\n", encoding="utf-8")

            # when
            changed = changed_files(book / "runs", "review-text", "flow", [chapter], book)

        # then
        self.assertEqual(changed, [chapter])

    def test_should_return_only_the_edited_and_new_files_since_the_last_run(self):
        # given
        with TemporaryBook() as book:
            first, second, third = (book / name for name in
                                    ("110-chapter-1.md", "120-chapter-2.md", "130-chapter-3.md"))
            first.write_text("One.\n", encoding="utf-8")
            second.write_text("Two.\n", encoding="utf-8")
            run = start_run(book / "runs", "review-text", "flow", MORNING)
            record_checksums(run, [first, second], book)
            second.write_text("Two, rewritten.\n", encoding="utf-8")
            third.write_text("Three.\n", encoding="utf-8")

            # when
            changed = changed_files(book / "runs", "review-text", "flow",
                                    [first, second, third], book)
            recorded = json.loads((run / CHECKSUMS_FILE).read_text(encoding="utf-8"))

        # then
        self.assertEqual(changed, [second, third])
        self.assertEqual(sorted(recorded), ["110-chapter-1.md", "120-chapter-2.md"])

    def test_should_compare_against_an_earlier_run_when_the_current_run_has_no_record(self):
        # given
        with TemporaryBook() as book:
            chapter = book / "110-chapter-1.md"
            chapter.write_text("One.\n", encoding="utf-8")
            earlier = start_run(book / "runs", "review-text", "flow", at_minute(0))
            record_checksums(earlier, [chapter], book)
            current = start_run(book / "runs", "review-text", "flow", at_minute(5))

            # when
            changed = changed_files(book / "runs", "review-text", "flow", [chapter], book,
                                    current_run=current)

        # then
        self.assertEqual(changed, [])


class RunFoldersCommandLineTest(unittest.TestCase):
    def test_should_only_name_the_new_folder_when_start_is_a_dry_run(self):
        # given
        with TemporaryBook(NEW_BOOK) as book:
            # when
            result = run_script("run_folders.py", "start", "review-text", "flow", cwd=book)
            made = (book / ".book" / "runs").exists()

        # then
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout.strip(),
                         r"/\.book/runs/\d{4}-\d{2}-\d{2}-\d{4}-review-text-flow$")
        self.assertFalse(made)

    def test_should_make_the_folder_in_the_book_runs_folder_when_start_is_fixed(self):
        # given
        with TemporaryBook(NEW_BOOK) as book:
            # when
            result = run_script("run_folders.py", "start", "review-text", "flow", "--fix",
                                cwd=book)
            latest = run_script("run_folders.py", "latest", "review-text", "flow", cwd=book)

        # then
        self.assertEqual(result.stdout, latest.stdout)
        self.assertTrue(result.stdout.strip().startswith(str(book / ".book" / "runs")))

    def test_should_fail_when_no_run_exists_and_the_latest_is_asked_for(self):
        # given
        with TemporaryBook(NEW_BOOK) as book:
            # when
            result = run_script("run_folders.py", "latest", "review-text", "flow", cwd=book)

        # then
        self.assertEqual(result.returncode, 1)

    def test_should_print_help_when_asked(self):
        # then
        self.assertEqual(run_script("run_folders.py", "--help").returncode, 0)


if __name__ == "__main__":
    unittest.main()
