import shlex
import unittest
from pathlib import Path

from support import NEW_BOOK, TemporaryBook, run_script

import book_config
from book_config import default, load_config
from check_output import DEFECT, SHARED_CLASSES
from citation_key import FENCE_LINE
from decisions import match_finding, read_decisions
from glossary import notation_from_config, parse_glossary


def check_book_yaml(folder, text):
    (folder / "book.yaml").write_text(text, encoding="utf-8")
    return run_script("book_config.py", "check", "--format", "tsv", cwd=folder)


class GlossaryNotationKeysTest(unittest.TestCase):
    def test_should_give_the_default_glossary_notation_when_the_book_sets_none(self):
        # when
        config = load_config(start=NEW_BOOK)

        # then
        self.assertEqual(config.get("glossary_format.heading_separator"), " -- ")
        self.assertTrue(config.get("glossary_format.location_pattern").startswith("^(?:Ch"))

    def test_should_split_a_qualified_heading_when_the_book_sets_its_own_separator(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text('glossary_format:\n  heading_separator: " | "\n',
                                              encoding="utf-8")
            notation = notation_from_config(load_config(start=folder))

        # when
        entries = parse_glossary("### flour | strong | Ch12\n\n**Invariants:** none\n"
                                 "```\n### inside a fence | Ch1\n```\n", notation)

        # then
        self.assertEqual([(entry.term, entry.location) for entry in entries],
                         [("strong flour", "Ch12")])


class CoverKeysTest(unittest.TestCase):
    def test_should_derive_cover_work_folders_when_the_book_sets_none(self):
        # when
        config = load_config(start=NEW_BOOK)

        # then
        self.assertEqual(config.cover.output, NEW_BOOK / ".book" / "output" / "cover")
        self.assertEqual(config.cover.templates, NEW_BOOK / ".book" / "caches" / "kdp-templates")
        self.assertEqual(config.cover.shelf_screenshots,
                         NEW_BOOK / ".book" / "caches" / "shelf-screenshots")
        self.assertEqual(config.cover.cmyk_limit, 88.0)
        self.assertIsNone(config.cover.book_pdf)
        self.assertIsNone(config.cover.icc)

    def test_should_resolve_cover_paths_when_the_book_sets_them(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text(
                "cover:\n  book_pdf: out/book.pdf\n  icc: profiles/swop.icc\n  cmyk_limit: 85\n",
                encoding="utf-8")

            # when
            config = load_config(start=folder)

        # then
        self.assertEqual(config.get("cover.book_pdf"), folder / "out" / "book.pdf")
        self.assertEqual(config.cover.icc, folder / "profiles" / "swop.icc")
        self.assertEqual(config.cover.cmyk_limit, 85.0)

    def test_should_accept_every_cover_key_when_checking_book_yaml(self):
        # given
        with TemporaryBook() as folder:
            # when
            result = check_book_yaml(folder, (
                "book:\n  pages: 240\ncover:\n  book_pdf: a.pdf\n  output: o\n  templates: t\n"
                "  shelf_screenshots: s\n  cmyk_limit: 88\n  icc: c.icc\n  srgb_profile: p.icc\n"
                "tools:\n  render_image: example/rsvg:2.58\n"))

        # then
        self.assertNotIn("unknown-key", result.stdout)


class SalesTextKeysTest(unittest.TestCase):
    def test_should_place_sales_text_files_in_the_sales_text_folder_when_the_book_sets_none(self):
        # when
        config = load_config(start=NEW_BOOK)

        # then
        folder = NEW_BOOK / "publishing" / "sales-text"
        self.assertEqual(config.sales_text.back_cover, folder / "back-cover.md")
        self.assertEqual(config.sales_text.amazon, folder / "amazon.html")
        self.assertEqual(config.sales_text.keywords, folder / "keywords-and-categories.md")
        self.assertEqual(config.sales_text.intended_impression,
                         folder / "intended-impression.md")
        self.assertEqual(config.sales_text.plain_description, folder / "plain-description.txt")
        self.assertEqual(config.sales_text.contents, folder / "contents.html")
        self.assertEqual(config.sales_text.contents_full, folder / "contents-full.html")
        self.assertIsNone(config.sales_text.preface)

    def test_should_follow_the_sales_text_folder_when_the_book_moves_it(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text("publishing:\n  sales_text: selling\n",
                                              encoding="utf-8")

            # when
            config = load_config(start=folder)

        # then
        self.assertEqual(config.get("sales_text.amazon"), folder / "selling" / "amazon.html")
        self.assertEqual(config.sales_text.back_cover, folder / "selling" / "back-cover.md")

    def test_should_follow_the_cover_folder_when_the_book_moves_it(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text("publishing:\n  cover: art\n", encoding="utf-8")

            # when
            config = load_config(start=folder)

        # then
        self.assertEqual(config.cover.design, folder / "art" / "design.py")
        self.assertEqual(config.cover.final, folder / "art" / "final")

    def test_should_use_the_shipped_cover_when_the_book_names_no_cover_image(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text("book:\n  title: T\n", encoding="utf-8")
            final = folder / "publishing" / "cover" / "final"
            final.mkdir(parents=True)
            (final / "front.png").write_bytes(b"png")

            # when
            config = load_config(start=folder)

        # then
        self.assertEqual(config.book.path("cover_front"), final / "front.png")
        self.assertIsNone(config.book.path("cover_back"))

    def test_should_give_the_six_by_nine_format_when_the_book_sets_none(self):
        # when
        config = load_config(start=NEW_BOOK)

        # then
        self.assertEqual(config.trim, "6x9")

    def test_should_give_store_limits_when_the_book_sets_none(self):
        # when
        config = load_config(start=NEW_BOOK)

        # then
        self.assertEqual(config.get("sales_text.amazon_limit"), 4000)
        self.assertEqual(config.get("sales_text.keyword_slots"), 7)
        self.assertEqual(config.get("sales_text.keyword_chars"), 50)
        self.assertEqual(config.get("sales_text.categories_per_format"), 3)
        self.assertEqual(config.get("sales_text.sample_print_share"), 0.2)
        self.assertEqual(config.get("sales_text.sample_ebook_share"), 0.1)
        self.assertEqual(config.get("sales_text.retired_phrases"), [])


class ReadersReviewKeysTest(unittest.TestCase):
    def test_should_put_the_room_next_to_the_book_when_the_book_sets_none(self):
        # when
        config = load_config(start=NEW_BOOK)

        # then
        self.assertEqual(config.readers_review.room,
                         NEW_BOOK.parent / "new-book-readers-review")
        self.assertEqual(config.readers_review.sources_for_reviewer,
                         NEW_BOOK / ".book" / "output" / "sources-for-reviewer.md")
        self.assertEqual(config.get("readers_review.lens_batch"), 3)
        self.assertEqual(config.get("readers_review.skeptic_batch"), 2)

    def test_should_accept_lenses_as_data_when_checking_book_yaml(self):
        # given
        with TemporaryBook() as folder:
            # when
            result = check_book_yaml(folder, (
                "readers_review:\n  room: ../room\n  sources_for_reviewer: s.md\n"
                "  main_metaphor: a river\n  key_sources: [Abc20]\n  research_field: baking\n"
                "  similar_books: [One]\n  author_background: ten years\n  audience: home bakers\n"
                "  lens_batch: 3\n  skeptic_batch: 2\n  skills_off: [x]\n  plugin_id: a@b\n"
                "  lenses:\n    - name: Legal risk\n      question: Any claim?\n"
                "      any_field_of_a_lens: kept\n"))

        # then
        self.assertEqual(result.returncode, 0, result.stdout)


class WritingKeysTest(unittest.TestCase):
    def test_should_leave_writing_numbers_to_the_voice_profile_when_the_book_sets_none(self):
        # when
        writing = load_config(start=NEW_BOOK).get("writing")

        # then
        self.assertTrue(all(value in (None, []) for value in writing.values()))
        self.assertIn("sentence_max_words", writing)
        self.assertIn("words_per_page", writing)

    def test_should_accept_every_writing_key_when_checking_book_yaml(self):
        # given
        keys = book_config.SHARED_DEFAULTS["writing"]
        text = "writing:\n" + "".join(f"  {key}: 1\n" for key in keys)
        with TemporaryBook() as folder:
            # when
            result = check_book_yaml(folder, text)

        # then
        self.assertEqual(result.returncode, 0, result.stdout)


class BookKeysTest(unittest.TestCase):
    def test_should_report_a_misspelled_book_key_when_checking_book_yaml(self):
        # given
        with TemporaryBook() as folder:
            # when
            result = check_book_yaml(folder, "book:\n  title: T\n  Font-Size: 11pt\n"
                                             "  font_szie: 12pt\n")

        # then
        self.assertEqual(result.returncode, 1)
        self.assertIn("book.font_szie\tunknown-key", result.stdout)
        self.assertNotIn("Font-Size", result.stdout)

    def test_should_report_the_accepted_flags_key_as_unknown_when_book_yaml_still_sets_it(self):
        # given
        with TemporaryBook() as folder:
            # when
            result = check_book_yaml(folder, "rules:\n  accepted_flags: rules/accepted-flags.json\n")

        # then
        self.assertEqual(result.returncode, 1)
        self.assertIn("rules.accepted_flags\tunknown-key", result.stdout)

    def test_should_return_the_default_when_a_key_is_not_set(self):
        # given
        config = load_config(start=NEW_BOOK)

        # then
        self.assertEqual(config.get("no.such.key", "fallback"), "fallback")
        self.assertIsNone(config.get("book.no_such_key", None))
        with self.assertRaises(KeyError):
            config.get("no.such.key")


class ToolKeysTest(unittest.TestCase):
    def test_should_pin_the_bibtex_image_to_a_digest(self):
        # when
        image = load_config(start=NEW_BOOK).tools.bibtex_image

        # then
        self.assertRegex(image, r"^blang/latex:ubuntu@sha256:[0-9a-f]{64}$")

    def test_should_pin_the_paper_tex_image_to_tex_live_2025_by_digest(self):
        # when
        image = load_config(start=NEW_BOOK).tools.paper_tex_image

        # then
        self.assertRegex(image, r"^texlive/texlive:TL2025-historic@sha256:[0-9a-f]{64}$")

    def test_should_print_tool_settings_when_paths_are_asked_for_shell(self):
        # when
        result = run_script("book_config.py", "paths", "--shell", cwd=NEW_BOOK)

        # then
        values = dict(shlex.split(line)[0].split("=", 1) for line in result.stdout.splitlines())
        self.assertEqual(values["BOOK_TOOLS_PANDOC_IMAGE"], "pandoc/extra:3.8.3")
        self.assertEqual(values["BOOK_TOOLS_PANDOC_VOLUME"], "book-to-pdf-texlive")
        self.assertEqual(values["BOOK_TOOLS_RENDER_IMAGE"], "")

    def test_should_give_the_built_in_default_when_asked_directly(self):
        # then
        self.assertEqual(default("sources.library"), "sources/library")
        self.assertEqual(default("rules.decisions"), "rules/decisions.md")
        self.assertEqual(default("tools.pandoc_image"), "pandoc/extra:3.8.3")


class SharedRulesTest(unittest.TestCase):
    def test_should_share_the_moving_target_class_between_checks(self):
        # then
        self.assertEqual(SHARED_CLASSES["moving-target"], DEFECT)

    def test_should_read_an_indented_fence_when_it_sits_in_a_list_item(self):
        # then
        self.assertTrue(FENCE_LINE.match("   ```java"))
        self.assertFalse(FENCE_LINE.match("    ```"))

    def test_should_ignore_a_run_local_alias_when_the_caller_names_its_shape(self):
        # given
        decisions = read_decisions(NEW_BOOK / "rules" / "decisions.md")

        # when
        plain = match_finding(decisions, "finding L2-6 about fonts", threshold=50)
        ignored = match_finding(decisions, "finding L2-6 about fonts", threshold=50,
                                ignore_alias_pattern=r"L\d+-\d+")

        # then
        self.assertEqual([found.entry.id for found in plain], ["D-2"])
        self.assertEqual(ignored, [])


if __name__ == "__main__":
    unittest.main()
