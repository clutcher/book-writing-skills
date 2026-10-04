import unittest

from support import run_script

from citation_key import (UnkeyableName, derive, derive_label, is_safe_file_key,
                          surnames_from_author_text, surnames_from_registry_field, validate)


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

    def test_should_end_the_label_with_a_plus_when_the_names_end_with_others(self):
        # then
        self.assertEqual(derive_label(["Adams"], 2001, and_others=True), "A+01")
        self.assertEqual(derive_label(["Adams", "Baker", "Clark"], 2002, and_others=True),
                         "ABC+02")
        self.assertEqual(derive_label(["Adams", "Baker"], 2002), "AB02")

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

    def test_should_print_a_key_when_derive_is_used_on_the_command_line(self):
        # when
        result = run_script("citation_key.py", "--derive", "Adams", "Baker", "--year", "2021")

        # then
        self.assertEqual(result.stdout.strip(), "AB21")

    def test_should_read_a_whole_surname_when_it_has_accents_or_a_hyphen(self):
        # when
        names, flags = surnames_from_author_text("Hernández-Ruiz, A., & Müller-Lyer, F. C.")

        # then
        self.assertEqual(names, ["Hernández-Ruiz", "Müller-Lyer"])
        self.assertEqual(flags, [])
        self.assertEqual(derive(names, 2001), "HRML01")

    def test_should_derive_a_key_its_own_validation_accepts_when_the_name_is_latin(self):
        cases = [(["Łukasik"], "Luk99"), (["Sørensen"], "Sor99"), (["Strauß"], "Str99"),
                 (["O'Brien"], "OB03"), (["Déniz"], "Den96")]
        for surnames, want in cases:
            with self.subTest(surnames[0]):
                # when
                key = derive(surnames, want[-2:])

                # then
                self.assertEqual(key, want)
                self.assertEqual(validate(key, surnames, want[-2:]), [])

    def test_should_refuse_a_key_when_the_name_has_no_latin_letters(self):
        # then
        with self.assertRaises(UnkeyableName):
            derive(["Иванов"], 1999)
        with self.assertRaises(UnkeyableName):
            derive(["王"], 1999)
        self.assertEqual(surnames_from_author_text("Иванов, И.")[1], ["org-or-unparsed"])
        self.assertIsNone(surnames_from_registry_field("Ivan Иванов")[1])

    def test_should_use_the_no_year_mark_when_the_year_is_not_known(self):
        # then
        self.assertEqual(derive(["Smith"], "n.d."), "Smi--")
        self.assertEqual(derive(["Smith"], None), "Smi--")
        self.assertEqual(run_script("citation_key.py", "--derive", "Walsh",
                                    "--year", "n.d.").stdout.strip(), "Wal--")
        self.assertEqual(run_script("citation_key.py", "--derive", "Walsh",
                                    "--year=").stdout.strip(), "Wal--")

    def test_should_read_two_surname_first_authors_when_joined_by_and(self):
        # when
        names, confidence, _ = surnames_from_registry_field("Smith, John and Doe, Jane")

        # then
        self.assertEqual(names, ["Smith", "Doe"])
        self.assertEqual(confidence, "high")

    def test_should_not_guess_when_authors_joined_by_and_may_be_given_first(self):
        # when
        _, confidence, reason = surnames_from_registry_field("Ann Lee, Bo Chen and Cy Dow, Di Fox")

        # then
        self.assertIsNone(confidence)
        self.assertTrue(reason)

    def test_should_accept_a_key_as_a_file_name_only_when_it_is_safe(self):
        # then
        for key in ["Smi99", "ABC+20", "Wal--", "vdM05a"]:
            self.assertTrue(is_safe_file_key(key), key)
        for key in ["", "../Smi99", "a/b", "Smi..99", ".hidden", "-Smi99", "Ива99"]:
            self.assertFalse(is_safe_file_key(key), key)

    def test_should_print_help_when_asked(self):
        # then
        self.assertEqual(run_script("citation_key.py", "--help").returncode, 0)


if __name__ == "__main__":
    unittest.main()
