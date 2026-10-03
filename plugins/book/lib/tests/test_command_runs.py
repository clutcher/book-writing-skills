import sys
import unittest
from pathlib import Path

import support

from command_runs import python_command, run_command
from container_run import calling_user_arguments, folder_mount, path_inside, volume_mount


class RunCommandTest(unittest.TestCase):
    def test_should_report_the_exit_code_and_last_line_when_a_command_ends(self):
        # given
        command = python_command("-c", "print('first'); print('checked 3 files'); raise SystemExit(1)")

        # when
        result = run_command(command, time_limit=60)

        # then
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.last_line(), "checked 3 files")
        self.assertFalse(result.passed)

    def test_should_report_timed_out_when_a_command_runs_past_its_limit(self):
        # given
        command = [sys.executable, "-c", "import time; time.sleep(30)"]

        # when
        result = run_command(command, time_limit=1)

        # then
        self.assertTrue(result.timed_out)
        self.assertFalse(result.passed)

    def test_should_keep_the_error_output_apart_when_asked_to(self):
        # given
        command = python_command("-c", "import sys; print('{}'); sys.stderr.write('no trim size')")

        # when
        result = run_command(command, time_limit=60, keep_error_output=False)

        # then
        self.assertEqual(result.output.strip(), "{}")
        self.assertEqual(result.error_output, "no trim size")

    def test_should_report_a_failed_start_when_the_program_is_missing(self):
        # when
        result = run_command(["no-such-program-anywhere"], time_limit=5)

        # then
        self.assertEqual(result.exit_code, 127)
        self.assertIn("could not start", result.last_line())


class ContainerArgumentsTest(unittest.TestCase):
    def test_should_share_a_folder_through_a_mount_that_keeps_drive_letters_whole(self):
        # given
        folder = Path(support.FIXTURES).resolve()

        # when
        arguments = folder_mount(folder, "/book", read_only=True)

        # then
        self.assertEqual(arguments, ["--mount", f"type=bind,source={folder},target=/book,readonly"])

    def test_should_quote_the_source_when_a_folder_name_has_a_comma(self):
        # given
        folder = Path("/srv/writer/Books/Smith, Jane/notes").resolve()

        # when
        arguments = folder_mount(folder, "/book", read_only=True)

        # then
        self.assertEqual(arguments, ["--mount", f'type=bind,"source={folder}",target=/book,readonly'])

    def test_should_double_a_quote_mark_when_a_folder_name_has_one(self):
        # given
        folder = Path('/srv/writer/Books/The "Quiet" Draft, 2nd').resolve()

        # when
        arguments = folder_mount(folder, "/book")

        # then
        quoted_folder = str(folder).replace('"', '""')
        self.assertEqual(arguments, ["--mount", f'type=bind,"source={quoted_folder}",target=/book'])

    def test_should_name_a_volume_mount_by_the_volume(self):
        # then
        self.assertEqual(volume_mount("texlive", "/opt/texlive"),
                         ["--mount", "type=volume,source=texlive,target=/opt/texlive"])

    def test_should_give_a_container_path_with_forward_slashes_when_a_file_is_in_the_shared_folder(self):
        # given
        book = Path(support.NEW_BOOK).resolve()

        # when
        inside = path_inside(book / "manuscript" / "010-chapter.md", book, "/workdir")

        # then
        self.assertEqual(inside, "/workdir/manuscript/010-chapter.md")

    def test_should_refuse_a_container_path_when_a_file_is_outside_the_shared_folder(self):
        # then
        with self.assertRaises(ValueError):
            path_inside(Path(support.OLD_BOOK), Path(support.NEW_BOOK), "/workdir")

    def test_should_pass_a_user_only_on_systems_with_user_ids(self):
        # when
        arguments = calling_user_arguments()

        # then
        if sys.platform.startswith("win"):
            self.assertEqual(arguments, [])
        else:
            self.assertEqual(arguments[0], "-u")


if __name__ == "__main__":
    unittest.main()
