import unittest

from support import TemporaryBook, run_script

from citations import citation_text, cited_keys, find_citations, needs_braces, rename_key
from manuscript_text import cited_keys as cited_keys_of_line

PANDOC_3_8_3_READS = [
    ("Bread rises [@Hal19].", ["Hal19"]),
    ("[@Hal19; @KO21, p. 3]", ["Hal19", "KO21"]),
    ("[see @Hal19, ch. 2; @KO21]", ["Hal19", "KO21"]),
    ("@Hal19 says so.", ["Hal19"]),
    ("@Hal19's idea and @Hal19: a colon and @Hal19.", ["Hal19", "Hal19", "Hal19"]),
    ("[-@Hal19] and (@Hal19)", ["Hal19", "Hal19"]),
    ("@QRS+17 says, and [@QRS+17, p. 2].", ["QRS+17", "QRS+17"]),
    ("@{QRS+17} and [see @{QRS+17}; @Hal19]", ["QRS+17", "QRS+17", "Hal19"]),
    ("@Wal-- here, and @{Wal--} here", ["Wal", "Wal--"]),
    ("@QRS+ at the end", ["QRS"]),
    ("@Hal19--x", ["Hal19"]),
    ("@a.b:c-d_e and @Smi99_ and @_abc and @9abc", ["a.b:c-d_e", "Smi99_", "_abc", "9abc"]),
    ("@Müller99", ["Müller99"]),
    ("mail someone@example.com today", []),
    ("foo@Hal19 and e.g.@Hal19 and x.@Hal19 and é@Hal19 and 1@Hal19", []),
    ("w,@Hal19 and /@Hal19 and _@Hal19 and -@Hal19", ["Hal19", "Hal19", "Hal19", "Hal19"]),
    ("a/@Hal19 and x_@Hal19 and a-@Hal19 and x+@Hal19 and x|@Hal19", []),
    ("\\@Hal19 is escaped", []),
    ("`@Hal19` and ``code @Hal19`` and @KO21", ["KO21"]),
    ("<!-- @Hal19 --> and $x @Hal19$ and $$ @Hal19 $$", []),
    ("costs $5 and @Hal19 says $6", ["Hal19"]),
    ("[a link](http://x.org/@Hal19) and <http://x.org/@Hal19> and <someone@example.com>", []),
    ("See https://medium.com/@someauthor/post and ftp://example.org/@Hal19 now", []),
    ("http://example.org/a@Hal19 and https://example.org/x, then @KO21", ["KO21"]),
    ("(https://example.org/@Hal19) [@KO21]", ["KO21"]),
    ("@{Weird key} and @-x", []),
    ("@{a}b}", ["a"]),
]


class PandocRuleTest(unittest.TestCase):
    def test_should_find_the_citations_pandoc_finds(self):
        for text, keys in PANDOC_3_8_3_READS:
            with self.subTest(text=text):
                # when
                found = [citation.key for citation in find_citations(text)]

                # then
                self.assertEqual(found, keys)

    def test_should_skip_fenced_code_blocks(self):
        # given
        text = "Before @Hal19.\n\n```\n@KO21 in code\n```\n\n~~~~\n@Jon74\n~~~~\n\nAfter @Smi99.\n"

        # when
        found = [(citation.key, citation.line) for citation in find_citations(text)]

        # then
        self.assertEqual(found, [("Hal19", 1), ("Smi99", 11)])


class CitationShapeTest(unittest.TestCase):
    def test_should_tell_a_bracket_citation_from_a_narrative_one(self):
        # when
        found = find_citations("@Hal19 shows it [see @KO21, p. 12; @Jon74].")

        # then
        self.assertEqual([(c.key, c.in_brackets, c.prefix, c.locator) for c in found],
                         [("Hal19", False, "", ""), ("KO21", True, "see", "p. 12"),
                          ("Jon74", True, "", "")])

    def test_should_give_line_and_column_of_each_citation(self):
        # when
        found = find_citations("First line.\nThe rest [@Hal19].")

        # then
        self.assertEqual((found[0].line, found[0].column), (2, 11))

    def test_should_count_each_key_once_in_cited_keys(self):
        # then
        self.assertEqual(cited_keys("@Hal19 and [@Hal19; @KO21]"), ["Hal19", "KO21"])
        self.assertEqual(cited_keys_of_line("[@Hal19, p. 3] and [Old99]"), ["Hal19"])


class KeyFormTest(unittest.TestCase):
    def test_should_brace_a_key_only_when_the_bare_form_would_cut_it(self):
        # then
        self.assertFalse(needs_braces("QRS+17"))
        self.assertTrue(needs_braces("Wal--"))
        self.assertEqual(citation_text("Hal19"), "@Hal19")
        self.assertEqual(citation_text("Wal--"), "@{Wal--}")

    def test_should_rename_every_citation_of_a_key_and_leave_code_alone(self):
        # given
        text = "@Hal19 says [see @Hal19, p. 2; @KO21] and @Hal19a.\n\n```\n@Hal19\n```\n"

        # when
        renamed, count = rename_key(text, "Hal19", "Wal--")

        # then
        self.assertEqual(count, 2)
        self.assertEqual(renamed, "@{Wal--} says [see @{Wal--}, p. 2; @KO21] and @Hal19a.\n\n"
                                  "```\n@Hal19\n```\n")

    def test_should_never_rename_inside_a_bare_link(self):
        # given
        text = "Read https://example.org/@someauthor/post before @someauthor.\n"

        # when
        renamed, count = rename_key(text, "someauthor", "Som20")

        # then
        self.assertEqual(count, 1)
        self.assertEqual(renamed, "Read https://example.org/@someauthor/post before @Som20.\n")


class CommandTest(unittest.TestCase):
    def test_should_list_the_citations_of_a_file(self):
        with TemporaryBook() as folder:
            # given
            chapter = folder / "110-chapter-1.md"
            chapter.write_text("# One\n\nBread rises [@Hal19, p. 4].\n", encoding="utf-8")

            # when
            result = run_script("citations.py", str(chapter))

        # then
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split("\t")[1:], ["Hal19", "bracket", "p. 4\n"])


if __name__ == "__main__":
    unittest.main()
