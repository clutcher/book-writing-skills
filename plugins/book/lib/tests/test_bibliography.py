import unittest

from support import NEW_BOOK, TemporaryBook, run_script

from bibliography import (BibliographyError, expected_key, format_bibliography, label_names,
                          make_entry, parse_bibliography, parse_names, plain_text,
                          read_bibliography, write_bibliography)

STANDARD_FORM = """% sources the book tracks

@string{press = {Example Press}}

@book{Hal19,
  author = {Hale, Ruth},
  title = {Bread at Home},
  publisher = {Example Press},
  year = {2019},
  isbn = {9780306406157},
}

@comment{a second printing is on order}

@article{KO21,
  author = {Kim, Lee and Olsen, Peter},
  title = {Salt Levels and Gluten Networks in {Wheat} Dough},
  journal = {Journal of Cereal Notes},
  volume = {4},
  pages = {12--19},
  year = {2021},
  doi = {10.5555/salt.2021.4},
}
"""

HAND_WRITTEN = """@ARTICLE{KO21,
   Title = "Salt Levels and Gluten Networks
            in {Wheat} Dough",
   year = 2021, Author = {Kim, Lee and Olsen, Peter}, journal={Journal of Cereal Notes}
}
"""

CONCATENATED = """@inproceedings{Ada20,
  author = {Adams, Ann},
  title = {Rising Slowly},
  booktitle = acm # " Conference on " # "Things",
  year = {2020},
}
"""

CROSS_REFERENCED = """@inproceedings{Ada20x,
  author = {Adams, Ann},
  title = {Rising Slowly},
  crossref = {Pro20},
}

@inbook{Bak19x,
  title = {Folding by Hand},
  chapter = {3},
  crossref = {bak19},
}

@book{Bak19,
  editor = {Baker, Bea},
  title = {A Handbook of Dough},
  publisher = {Example Press},
  year = {2019},
}

@proceedings{Pro20,
  editor = {Price, Paul},
  title = {Proceedings of the Bread Meeting},
  year = {2020},
}
"""


class ReadingTest(unittest.TestCase):
    def test_should_read_entries_with_their_type_key_and_fields(self):
        # when
        bibliography = parse_bibliography(STANDARD_FORM)

        # then
        self.assertEqual(bibliography.keys, ["Hal19", "KO21"])
        entry = bibliography.entry("KO21")
        self.assertEqual(entry.entry_type, "article")
        self.assertEqual(entry.field("journal"), "Journal of Cereal Notes")
        self.assertEqual(entry.field("pages"), "12--19")
        self.assertEqual([name.last for name in entry.authors], ["Kim", "Olsen"])

    def test_should_read_quoted_values_bare_numbers_and_any_letter_case(self):
        # when
        entry = parse_bibliography(HAND_WRITTEN).entry("KO21")

        # then
        self.assertEqual(entry.entry_type, "article")
        self.assertEqual(entry.field("title"), "Salt Levels and Gluten Networks in {Wheat} Dough")
        self.assertEqual(entry.field("year"), "2021")
        self.assertEqual(entry.field("Author"), "Kim, Lee and Olsen, Peter")

    def test_should_read_windows_line_endings_and_keep_them_on_write(self):
        with TemporaryBook() as folder:
            # given
            path = folder / "references.bib"
            path.write_bytes(STANDARD_FORM.replace("\n", "\r\n").encode("utf-8"))

            # when
            write_bibliography(path, read_bibliography(path))

            # then
            self.assertEqual(path.read_bytes(), STANDARD_FORM.replace("\n", "\r\n").encode("utf-8"))

    def test_should_refuse_an_entry_that_is_never_closed(self):
        # then
        with self.assertRaises(BibliographyError) as raised:
            parse_bibliography("@book{Hal19,\n  title = {Bread at Home,\n")
        self.assertIn("line 2", str(raised.exception))

    def test_should_list_a_key_that_is_written_twice(self):
        # when
        bibliography = parse_bibliography("@book{Hal19, title = {A}}\n@book{Hal19, title = {B}}\n")

        # then
        self.assertEqual(bibliography.duplicate_keys, ["Hal19"])
        self.assertEqual(bibliography.entry("Hal19").field("title"), "A")


class WritingTest(unittest.TestCase):
    def test_should_give_the_same_bytes_when_the_file_is_already_in_standard_form(self):
        with TemporaryBook() as folder:
            # given
            path = folder / "references.bib"
            path.write_text(STANDARD_FORM, encoding="utf-8")

            # when
            write_bibliography(path, read_bibliography(path))

            # then
            self.assertEqual(path.read_text(encoding="utf-8"), STANDARD_FORM)

    def test_should_write_one_field_per_line_in_the_fixed_order_with_braces(self):
        # when
        written = format_bibliography(parse_bibliography(HAND_WRITTEN))

        # then
        self.assertEqual(written, (
            "@article{KO21,\n"
            "  author = {Kim, Lee and Olsen, Peter},\n"
            "  title = {Salt Levels and Gluten Networks in {Wheat} Dough},\n"
            "  journal = {Journal of Cereal Notes},\n"
            "  year = {2021},\n"
            "}\n"))

    def test_should_keep_comments_strings_and_preambles_in_place(self):
        # when
        written = format_bibliography(parse_bibliography(STANDARD_FORM))

        # then
        self.assertIn("% sources the book tracks", written)
        self.assertIn("@string{press = {Example Press}}", written)
        self.assertLess(written.index("Hal19"), written.index("@comment"))
        self.assertLess(written.index("@comment"), written.index("KO21"))

    def test_should_keep_a_month_macro_without_braces(self):
        # when
        written = format_bibliography(parse_bibliography("@misc{Wal80, month = jan, year = 1980}"))

        # then
        self.assertIn("  month = jan,\n", written)
        self.assertIn("  year = {1980},\n", written)

    def test_should_keep_each_part_of_a_joined_value_as_it_was_written(self):
        # when
        written = format_bibliography(parse_bibliography(CONCATENATED))

        # then
        self.assertEqual(written, CONCATENATED)

    def test_should_sort_a_new_entry_in_by_key_and_keep_the_existing_order(self):
        # given
        bibliography = parse_bibliography(STANDARD_FORM)

        # when
        bibliography.add(make_entry("book", "Jon74", {"author": "Jones, Ann",
                                                      "title": "A First Work", "year": 1974}))

        # then
        self.assertEqual(bibliography.keys, ["Hal19", "Jon74", "KO21"])

    def test_should_refuse_to_add_a_key_that_is_already_there(self):
        # given
        bibliography = parse_bibliography(STANDARD_FORM)

        # then
        with self.assertRaises(BibliographyError):
            bibliography.add(make_entry("book", "Hal19", {"title": "Again"}))

    def test_should_rename_the_crossref_of_a_child_when_its_parent_is_renamed(self):
        # given
        bibliography = parse_bibliography(CROSS_REFERENCED)

        # when
        bibliography.rename("Pro20", "Pro20a")

        # then
        self.assertEqual(bibliography.entry("Ada20x").field("crossref"), "Pro20a")
        self.assertEqual(bibliography.entry("Bak19x").field("crossref"), "bak19")

    def test_should_rename_a_key_in_place(self):
        # given
        bibliography = parse_bibliography(STANDARD_FORM)

        # when
        bibliography.rename("KO21", "KO21a")

        # then
        self.assertEqual(bibliography.keys, ["Hal19", "KO21a"])


class MakingTest(unittest.TestCase):
    def test_should_refuse_a_value_whose_braces_do_not_pair_up(self):
        # then
        with self.assertRaises(BibliographyError):
            make_entry("book", "Hal19", {"title": "Bread}, note = {at Home"})
        with self.assertRaises(BibliographyError):
            make_entry("book", "Hal19", {"title": "Bread at {Home"})

    def test_should_refuse_a_field_name_that_is_not_a_bibtex_name(self):
        # then
        with self.assertRaises(BibliographyError):
            make_entry("book", "Hal19", {"title}, note = {x": "Bread"})

    def test_should_refuse_an_entry_type_that_is_not_letters_only(self):
        # then
        with self.assertRaises(BibliographyError):
            make_entry("book{Evil99,", "Hal19", {"title": "Bread"})

    def test_should_accept_braces_that_pair_up(self):
        # when
        entry = make_entry("book", "Hal19", {"title": "Bread in {Wheat} Country"})

        # then
        self.assertEqual(entry.field("title"), "Bread in {Wheat} Country")


class NamesTest(unittest.TestCase):
    def test_should_read_the_three_ways_a_name_is_written(self):
        # when
        names = parse_names("Hale, Ruth and Jan van Berg and van der Meer, Jr., Piet")

        # then
        self.assertEqual([(n.first, n.von, n.last, n.jr) for n in names],
                         [("Ruth", "", "Hale", ""), ("Jan", "van", "Berg", ""),
                          ("Piet", "van der", "Meer", "Jr.")])

    def test_should_read_a_double_braced_name_as_one_corporate_author(self):
        # when
        names = parse_names("{Example Baking Guild} and Hale, Ruth")

        # then
        self.assertTrue(names[0].corporate)
        self.assertEqual(names[0].last, "Example Baking Guild")
        self.assertFalse(names[1].corporate)

    def test_should_not_split_on_and_inside_braces(self):
        # when
        names = parse_names("{Flour and Water Society} and Hale, Ruth")

        # then
        self.assertEqual(len(names), 2)

    def test_should_mark_and_others_as_more_names(self):
        # when
        names = parse_names("Hale, Ruth and others")

        # then
        self.assertEqual([name.others for name in names], [False, True])

    def test_should_turn_latex_accents_into_letters(self):
        # then
        self.assertEqual(plain_text(r"M{\"u}ller"), "Müller")
        self.assertEqual(plain_text(r"{\O}stergaard"), "Østergaard")
        self.assertEqual(plain_text(r"Ca\~{n}ada and {\'E}cole"), "Cañada and École")


class LabelTest(unittest.TestCase):
    def label(self, author, year="2019", entry_type="book", **fields):
        values = {"author": author, "year": year, **fields} if author else {"year": year, **fields}
        return expected_key(make_entry(entry_type, "X", values))

    def test_should_give_the_labels_real_bibtex_alpha_gives(self):
        # then
        self.assertEqual(self.label("Hale, Ruth"), "Hal19")
        self.assertEqual(self.label("Ruth Hale and Peter Olsen"), "HO19")
        self.assertEqual(self.label("A, B and C, D and E, F and G, H and I, J", "2009"), "ACE+09")
        self.assertEqual(self.label("Hale, Ruth and others", "2001"), "H+01")
        self.assertEqual(self.label("Ann Adams and Bob Baker and Cy Clark and others", "2002"),
                         "ABC+02")
        self.assertEqual(self.label("Rocha da Lima, José", "2003"), "RdL03")
        self.assertEqual(self.label("José Rocha da Lima", "2003"), "dL03")
        self.assertEqual(self.label("van Berg, Jan", "2008"), "vB08")
        self.assertEqual(self.label("Owen-Price, Al", "2005"), "OP05")

    def test_should_fold_accents_the_way_the_key_rule_does(self):
        # then
        self.assertEqual(self.label(r"M{\"u}ller, Hans", "2004"), "Mul04")
        self.assertEqual(self.label(r"{\O}stergaard, Ole", "2007"), "Ost07")

    def test_should_take_three_letters_of_a_corporate_author(self):
        # then
        self.assertEqual(self.label("{Example Baking Guild}", "1999"), "Exa99")
        self.assertEqual(self.label("{Example Baking Guild} and Hale, Ruth", "1999"), "EH99")

    def test_should_use_the_editor_of_a_book_with_no_author(self):
        # then
        self.assertEqual(self.label(None, "2006", editor="Eli Eads"), "Ead06")

    def test_should_write_two_dashes_when_there_is_no_year(self):
        # when
        entry = make_entry("misc", "Wal--", {"author": "Walsh, M.", "title": "A catalog"})

        # then
        self.assertEqual(expected_key(entry), "Wal--")

    def test_should_take_the_year_and_editor_from_the_crossref_parent(self):
        # given
        bibliography = parse_bibliography(CROSS_REFERENCED)

        # when
        child_paper = expected_key(bibliography.entry("Ada20x"), bibliography)
        child_chapter = expected_key(bibliography.entry("Bak19x"), bibliography)

        # then
        self.assertEqual(child_paper, "Ada20")
        self.assertEqual(child_chapter, "Bak19")
        self.assertEqual(expected_key(bibliography.entry("Ada20x")), "Ada--")

    def test_should_keep_the_own_names_of_a_child_over_those_of_its_parent(self):
        # given
        bibliography = parse_bibliography(CROSS_REFERENCED)

        # when
        found = label_names(bibliography.entry("Ada20x"), bibliography)

        # then
        self.assertEqual(found.surnames, ["Adams"])
        self.assertEqual(found.source_field, "author")

    def test_should_give_no_label_when_the_entry_has_no_names(self):
        # when
        entry = make_entry("misc", "X", {"title": "A page"})

        # then
        self.assertIsNone(label_names(entry))
        self.assertIsNone(expected_key(entry))


class CommandTest(unittest.TestCase):
    def test_should_print_each_key_with_the_label_its_names_give(self):
        # when
        result = run_script("bibliography.py", str(NEW_BOOK / "sources" / "references.bib"),
                            "--keys")

        # then
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "Jon74\tJon74\nSmi99\tSmi99\n")

    def test_should_print_a_dash_when_the_names_hold_no_latin_letters(self):
        with TemporaryBook() as folder:
            # given
            path = folder / "references.bib"
            path.write_text("@book{Pet16,\n  author = {Петренко, Олена},\n  title = {Хліб},\n"
                            "  year = {2016},\n}\n", encoding="utf-8")

            # when
            result = run_script("bibliography.py", str(path), "--keys")

            # then
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "Pet16\t-\n")

    def test_should_say_the_fixture_is_already_in_standard_form(self):
        # when
        result = run_script("bibliography.py", str(NEW_BOOK / "sources" / "references.bib"))

        # then
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_should_write_only_with_fix(self):
        with TemporaryBook() as folder:
            # given
            path = folder / "references.bib"
            path.write_text(HAND_WRITTEN, encoding="utf-8")

            # when
            dry = run_script("bibliography.py", str(path))
            unchanged = path.read_text(encoding="utf-8")
            fixed = run_script("bibliography.py", str(path), "--fix")

            # then
            self.assertEqual(dry.returncode, 1)
            self.assertEqual(unchanged, HAND_WRITTEN)
            self.assertEqual(fixed.returncode, 0, fixed.stderr)
            self.assertTrue(path.read_text(encoding="utf-8").startswith("@article{KO21,\n"))


if __name__ == "__main__":
    unittest.main()
