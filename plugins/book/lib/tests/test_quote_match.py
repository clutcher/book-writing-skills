import unittest

import support

from quote_match import locate_in, quotes_in, squash, title_share


class QuoteMatchTest(unittest.TestCase):
    def test_should_find_a_quote_when_the_text_broke_it_with_a_ligature_and_a_hyphen(self):
        # given
        text = squash("the ligature in this identiﬁer is\ndeliberate and the sen-\ntence ends")

        # when
        found = locate_in("the ligature in this identifier is deliberate and the sentence ends",
                          [("txt", text)])

        # then
        self.assertEqual(found, ("txt", "full"))

    def test_should_find_both_pieces_when_a_quote_joins_two_passages_with_an_ellipsis(self):
        # given
        text = squash("grades correlate with length in every class. Later on: "
                      "the correlation coefficient is 0.49 overall")

        # when
        found = locate_in("grades correlate with length ... the correlation coefficient is 0.49",
                          [("txt", text)])

        # then
        self.assertEqual(found, ("txt", "ellipsis"))

    def test_should_prefer_a_full_match_in_a_later_text_over_a_window_in_the_first(self):
        # given
        quote = "one two three four five six seven eight nine ten eleven twelve"
        texts = [("layout", squash("one two three four five six seven eight")),
                 ("plain", squash(quote))]

        # when
        found = locate_in(quote, texts)

        # then
        self.assertEqual(found, ("plain", "full"))

    def test_should_find_nothing_when_the_text_does_not_hold_the_quote(self):
        # then
        self.assertEqual(locate_in("bread rises only when it is warm enough",
                                   [("txt", squash("a page about something else"))]), ("", ""))

    def test_should_skip_an_editorial_fragment_when_it_sits_in_quotation_marks(self):
        # when
        found = quotes_in('"the first real quotation is here" and "-- quote fragments, not the '
                          'whole sentence"')

        # then
        self.assertEqual(found, ["the first real quotation is here"])

    def test_should_count_the_title_words_present_in_a_text(self):
        # then
        self.assertEqual(title_share("Baking Bread at Home", squash("home baking, bread")), 1.0)
        self.assertEqual(title_share("Baking Bread at Home", squash("baking cakes")), 0.5)


if __name__ == "__main__":
    unittest.main()
