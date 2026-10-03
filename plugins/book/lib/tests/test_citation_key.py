import unittest

from support import run_script

from citation_key import bib_entry, derive, surnames_from_registry_field, validate


class CitationKeyTest(unittest.TestCase):
    def test_should_pass_its_own_self_test(self):
        # when
        result = run_script("citation_key.py", "--self-test")

        # then
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("self-test: PASS", result.stdout)

    def test_should_derive_alpha_keys_for_one_to_five_authors(self):
        # then
        self.assertEqual(derive(["Smith"], 1999), "Smi99")
        self.assertEqual(derive(["Adams", "Baker"], 2020), "AB20")
        self.assertEqual(derive(["Adams", "Baker", "Clark", "Davis"], 1994), "ABCD94")
        self.assertEqual(derive(["Adams", "Baker", "Clark", "Davis", "Evans"], 2020), "ABC+20")

    def test_should_keep_particles_and_hyphen_parts_in_the_key(self):
        # then
        self.assertEqual(derive(["van Berg", "Owen-Price"], 2010), "vBOP10")

    def test_should_refuse_to_guess_when_an_author_field_is_an_organisation(self):
        # when
        names, confidence, reason = surnames_from_registry_field("Example Software Foundation")

        # then
        self.assertIsNone(confidence)
        self.assertTrue(reason)

    def test_should_flag_a_key_that_does_not_match_its_authors(self):
        # then
        self.assertTrue(validate("ABC+94", ["Adams", "Baker", "Clark", "Davis"], 1994))
        self.assertEqual(validate("ABCD94", ["Adams", "Baker", "Clark", "Davis"], 1994), [])

    def test_should_read_a_bibliography_line_but_not_prose(self):
        # then
        self.assertEqual(bib_entry("[Smi99] Smith, A. (1999). A Title."),
                         ("Smi99", "Smith, A. (1999). A Title."))
        self.assertIsNone(bib_entry("[Smi99], p. 4, says so."))

    def test_should_print_a_key_when_derive_is_used_on_the_command_line(self):
        # when
        result = run_script("citation_key.py", "--derive", "Adams", "Baker", "--year", "2021")

        # then
        self.assertEqual(result.stdout.strip(), "AB21")

    def test_should_print_help_when_asked(self):
        # then
        self.assertEqual(run_script("citation_key.py", "--help").returncode, 0)


if __name__ == "__main__":
    unittest.main()
