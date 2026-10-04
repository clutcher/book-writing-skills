import json
import shlex
import unittest
from pathlib import Path

from support import NEW_BOOK, NEW_PAPER, TemporaryBook, run_script

import book_config
from book_config import (KIND_BACK_MATTER, KIND_CHAPTER, KIND_FRONT_MATTER, KIND_PART,
                         KIND_REFERENCES, ConfigError, chapter_number, load_config,
                         manuscript_files, read_yaml_subset)


class NewLayoutBookTest(unittest.TestCase):
    def setUp(self):
        self.config = load_config(start=NEW_BOOK / "manuscript")

    def test_should_find_book_yaml_when_started_in_a_subfolder(self):
        # then
        self.assertEqual(self.config.config_file, NEW_BOOK / "book.yaml")
        self.assertEqual(self.config.root, NEW_BOOK)

    def test_should_resolve_new_layout_paths_against_the_config_folder(self):
        # then
        self.assertEqual(self.config.sources.list, NEW_BOOK / "sources" / "list.md")
        self.assertEqual(self.config.sources.quotes, NEW_BOOK / "sources" / "quotes.md")
        self.assertEqual(self.config.sources.library, NEW_BOOK / "sources" / "library")
        self.assertEqual(self.config.sources.library_index,
                         NEW_BOOK / "sources" / "library-index")
        self.assertEqual(self.config.rules.glossary, NEW_BOOK / "rules" / "glossary.md")
        self.assertEqual(self.config.rules.decisions, NEW_BOOK / "rules" / "decisions.md")
        self.assertEqual(self.config.rules.voice, NEW_BOOK / "rules" / "voice.md")
        self.assertEqual(self.config.rules.vale_ini, NEW_BOOK / "rules" / "vale" / "vale.ini")
        self.assertEqual(self.config.thinking.stance,
                         NEW_BOOK / "thinking" / "author" / "stance.md")
        self.assertEqual(self.config.thinking.audience,
                         NEW_BOOK / "thinking" / "author" / "audience.md")
        self.assertEqual(self.config.thinking.argument, NEW_BOOK / "thinking" / "argument")
        self.assertEqual(self.config.thinking.doubts, NEW_BOOK / "thinking" / "doubts")
        self.assertEqual(self.config.notes, NEW_BOOK / "notes")
        self.assertEqual(self.config.publishing.cover, NEW_BOOK / "publishing" / "cover")
        self.assertEqual(self.config.publishing.sales_text,
                         NEW_BOOK / "publishing" / "sales-text")
        self.assertEqual(self.config.cover.design,
                         NEW_BOOK / "publishing" / "cover" / "design.py")
        self.assertEqual(self.config.manuscript.references,
                         NEW_BOOK / "manuscript" / "900-references.md")

    def test_should_derive_work_folders_when_work_is_a_single_folder(self):
        # then
        self.assertEqual(self.config.work.dir, NEW_BOOK / ".book")
        self.assertEqual(self.config.work.runs, NEW_BOOK / ".book" / "runs")
        self.assertEqual(self.config.work.output, NEW_BOOK / ".book" / "output")
        self.assertEqual(self.config.work.caches, NEW_BOOK / ".book" / "caches")
        self.assertEqual(self.config.sources.to_add, NEW_BOOK / ".book" / "sources-to-add")

    def test_should_expand_home_folder_when_a_path_starts_with_tilde(self):
        # then
        self.assertEqual(self.config.sources.backup,
                         Path("~/private/book-backup").expanduser())

    def test_should_read_typed_metadata_when_values_are_quoted_or_plain(self):
        # given
        book = self.config.book

        # then
        self.assertEqual(book.title, "A Small Book: Tests")
        self.assertEqual(book.subtitle, "It's only a fixture")
        self.assertEqual(book.get("Font-Size"), "11pt")
        self.assertIs(book.get("toc"), False)
        self.assertEqual(book.get("publication_date"), 2025)
        self.assertEqual(book.language, "en-US")
        self.assertEqual(book.path("cover_front"), NEW_BOOK / "cover" / "final" / "front.png")

    def test_should_keep_block_strings_when_folded_or_literal(self):
        # then
        self.assertEqual(self.config.book.get("description"),
                         "First line of a folded description.\nSecond paragraph.\n")
        self.assertEqual(self.config.book.get("note"), "kept\n  as written\n")

    def test_should_read_coined_terms_when_written_as_block_and_inline_items(self):
        # given
        terms = self.config.terms

        # then
        self.assertEqual([(f.term, f.role, f.also) for f in terms.families],
                         [("mulched", "primary", ["mulching"]), ("bare", "antonym", [])])
        self.assertEqual(terms.compounds, ["mulched bed", "bare bed"])
        self.assertEqual(terms.watch_words, {"internal_first_nouns": ["bed", "row"]})
        self.assertEqual(terms.family("MULCHED").role, "primary")

    def test_should_list_manuscript_in_natural_order_with_kinds(self):
        # when
        files = manuscript_files(self.config)

        # then
        self.assertEqual([(item.name, item.kind, item.chapter) for item in files], [
            ("000-copyright.md", KIND_FRONT_MATTER, None),
            ("010-preface.md", KIND_FRONT_MATTER, None),
            ("100-part-one.md", KIND_PART, None),
            ("110-chapter-1.md", KIND_CHAPTER, 1),
            ("120-chapter-2.md", KIND_CHAPTER, 2),
            ("200-part-two.md", KIND_PART, None),
            ("210-chapter-10.md", KIND_CHAPTER, 10),
            ("900-references.md", KIND_REFERENCES, None),
            ("910-index.md", KIND_BACK_MATTER, None),
        ])

    def test_should_return_only_chapters_when_kind_is_chapter(self):
        # when
        chapters = self.config.manuscript_files(kinds=KIND_CHAPTER)

        # then
        self.assertEqual([item.chapter for item in chapters], [1, 2, 10])

    def test_should_give_chapter_number_only_for_chapter_files(self):
        # then
        self.assertEqual(chapter_number(NEW_BOOK / "manuscript" / "210-chapter-10.md",
                                        self.config), 10)
        self.assertIsNone(chapter_number(NEW_BOOK / "manuscript" / "100-part-one.md",
                                         self.config))

    def test_should_prefer_command_line_when_it_overrides_book_yaml(self):
        # when
        config = load_config(start=NEW_BOOK, overrides=["sources.list=other/list.md",
                                                         "book.Title=Changed"])

        # then
        self.assertEqual(config.sources.list, NEW_BOOK / "other" / "list.md")
        self.assertEqual(config.book.title, "Changed")
        self.assertEqual(config.key_origins["sources.list"], book_config.SOURCE_CLI)

    def test_should_use_explicit_config_when_a_path_is_given(self):
        # when
        config = load_config(config=NEW_BOOK / "book.yaml", start="/")

        # then
        self.assertEqual(config.root, NEW_BOOK)


class ConfigPrecedenceTest(unittest.TestCase):
    def test_should_read_book_json_when_no_yaml_exists(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.json").write_text(json.dumps(
                {"book": {"title": "Json Book"}, "sources": {"list": "refs/list.md"}}),
                encoding="utf-8")

            # when
            config = load_config(start=folder)

        # then
        self.assertEqual(config.book.title, "Json Book")
        self.assertEqual(config.sources.list, folder / "refs" / "list.md")

    def test_should_use_new_defaults_when_nothing_is_found(self):
        # given
        with TemporaryBook() as folder:
            # when
            config = load_config(start=folder)

        # then
        self.assertEqual(config.source, book_config.SOURCE_DEFAULTS)
        self.assertEqual(config.sources.list, folder / "sources" / "list.md")

    def test_should_put_sources_to_add_in_the_work_folder_when_the_book_names_its_work_folder(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text("work:\n  dir: .work\n", encoding="utf-8")

            # when
            config = load_config(start=folder)

        # then
        self.assertEqual(config.sources.to_add, folder / ".work" / "sources-to-add")

    def test_should_ignore_a_claude_md_when_the_book_has_no_book_yaml(self):
        # given
        with TemporaryBook() as folder:
            (folder / "CLAUDE.md").write_text("## Book Metadata\n\nTitle: Old Notes\n",
                                              encoding="utf-8")

            # when
            config = load_config(start=folder)

        # then
        self.assertIsNone(config.config_file)
        self.assertIsNone(config.book.title)
        self.assertEqual(config.source, book_config.SOURCE_DEFAULTS)

    def test_should_follow_an_explicit_manuscript_list_when_order_is_list(self):
        # given
        with TemporaryBook(NEW_BOOK) as folder:
            (folder / "book.yaml").write_text(
                "manuscript:\n  order: list\n  files: [110-chapter-1.md, 000-copyright.md]\n",
                encoding="utf-8")

            # when
            names = [item.name for item in manuscript_files(load_config(start=folder))]

        # then
        self.assertEqual(names, ["110-chapter-1.md", "000-copyright.md"])


class HandWrittenConfigTest(unittest.TestCase):
    def test_should_use_defaults_when_a_section_has_only_commented_keys(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text(
                "book:\n  title: Field Notes\nsources:\n  # backup: ~/book-backup\n"
                "manuscript:\ncover:\ntools:\n", encoding="utf-8")

            # when
            config = load_config(start=folder)

        # then
        self.assertEqual(config.book.title, "Field Notes")
        self.assertEqual(config.sources.citation_style, "alpha")
        self.assertEqual(config.manuscript.dir, folder / "manuscript")
        self.assertEqual(config.cover.cmyk_limit, 88)

    def test_should_fail_as_a_tool_when_a_section_is_not_a_set_of_keys(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text("work: 5\n", encoding="utf-8")

            # when
            result = run_script("book_config.py", "show", cwd=folder)

        # then
        self.assertEqual(result.returncode, 2)
        self.assertIn("'work' must hold keys", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_should_read_the_first_key_when_the_file_starts_with_a_byte_order_mark(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text("\ufeffbook:\n  title: Field Notes\n",
                                              encoding="utf-8")

            # when
            config = load_config(start=folder)

        # then
        self.assertEqual(config.book.title, "Field Notes")

    def test_should_strip_comments_when_a_plain_value_holds_an_apostrophe(self):
        # given
        text = ("title: Rock 'n roll # working title\n"
                "subtitle: The '90s # decade\n"
                "author: 'Ann O''Neil' # quoted\n")

        # when
        data = read_yaml_subset(text)

        # then
        self.assertEqual(data, {"title": "Rock 'n roll", "subtitle": "The '90s",
                                "author": "Ann O'Neil"})

    def test_should_read_one_item_list_when_a_list_key_holds_one_text(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text(
                "manuscript:\n  order: list\n  files: 110-chapter-1.md\n"
                "terms:\n  compounds: Rule-Based\n", encoding="utf-8")

            # when
            config = load_config(start=folder)

        # then
        self.assertEqual(config.manuscript.files, ["110-chapter-1.md"])
        self.assertEqual(config.terms.compounds, ["rule-based"])

    def test_should_fail_as_a_config_error_when_the_cmyk_limit_is_not_a_usable_percent(self):
        for written in ("0", "300%", "high"):
            with self.subTest(written), TemporaryBook() as folder:
                # given
                (folder / "book.yaml").write_text(f"cover:\n  cmyk_limit: {written}\n",
                                                  encoding="utf-8")

                # when / then
                with self.assertRaisesRegex(ConfigError, "cover.cmyk_limit"):
                    load_config(start=folder)

    def test_should_keep_text_when_a_text_key_looks_like_a_number_or_a_capital_null(self):
        # given
        text = ("book:\n  title: Null\n  subtitle: 1984\n  epub_identifier: 0306406152\n"
                "  description: null\n")

        # when
        data = read_yaml_subset(text)

        # then
        self.assertEqual(data["book"], {"title": "Null", "subtitle": "1984",
                                        "epub_identifier": "0306406152", "description": None})

    def test_should_keep_three_dashes_when_they_are_inside_a_literal_block(self):
        # given
        text = "description: |\n  Part one\n  ---\n  Part two\nlanguage: en-GB\n"

        # when
        data = read_yaml_subset(text)

        # then
        self.assertEqual(data, {"description": "Part one\n---\nPart two\n",
                                "language": "en-GB"})

    def test_should_explain_the_value_when_an_override_is_not_valid(self):
        # given
        with TemporaryBook() as folder:
            # when
            result = run_script("book_config.py", "--set", "book.title=[Draft] Field Notes",
                                "get", "book.title", cwd=folder)

        # then
        self.assertEqual(result.returncode, 2)
        self.assertIn("--set book.title", result.stderr)
        self.assertNotIn("line 0", result.stderr)

    def test_should_join_subjects_with_commas_when_metadata_is_printed_for_the_shell(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text(
                "book:\n  subjects:\n    - Software Testing\n    - Quality\n",
                encoding="utf-8")

            # when
            result = run_script("book_config.py", "metadata", "--shell", cwd=folder)

        # then
        values = dict(line.split("=", 1) for line in result.stdout.splitlines())
        self.assertEqual(shlex.split(values["BOOK_META_SUBJECTS"])[0],
                         "Software Testing, Quality")


class YamlSubsetTest(unittest.TestCase):
    def test_should_parse_nested_lists_and_mappings(self):
        # given
        text = "a:\n  - - 1\n    - 2\n  - x: y\n    z: [1, {k: v}]\nb:\n- one\n- 'two # not a comment'\n"

        # when
        data = read_yaml_subset(text)

        # then
        self.assertEqual(data, {"a": [[1, 2], {"x": "y", "z": [1, {"k": "v"}]}],
                                "b": ["one", "two # not a comment"]})

    def test_should_read_empty_values_as_none(self):
        # then
        self.assertEqual(read_yaml_subset("a:\nb: ~\nc: null\n"), {"a": None, "b": None, "c": None})
        self.assertEqual(read_yaml_subset("# only a comment\n"), {})

    def test_should_keep_escapes_when_string_is_double_quoted(self):
        # then
        self.assertEqual(read_yaml_subset('a: "x\\ty\\u00e9\\"z"\n'), {"a": 'x\ty\u00e9"z'})

    def test_should_fail_with_line_number_when_input_is_outside_the_subset(self):
        # given
        broken = {
            "anchor": "a: &x 1\n",
            "alias": "a: *x\n",
            "tab": "a:\n\tb: 1\n",
            "duplicate": "a: 1\na: 2\n",
            "multi-line inline": "a: [1,\n  2]\n",
            "two documents": "a: 1\n---\nb: 2\n",
            "bad indentation": "a: 1\n   b: 2\n",
        }
        for label, text in broken.items():
            with self.subTest(label):
                # when / then
                with self.assertRaisesRegex(ConfigError, r"line \d+"):
                    read_yaml_subset(text)


class DocumentKindTest(unittest.TestCase):
    def test_should_be_a_book_when_book_yaml_names_no_kind(self):
        # when
        config = load_config(start=NEW_BOOK)

        # then
        self.assertEqual(config.kind, "book")
        self.assertFalse(config.is_paper)

    def test_should_be_a_paper_when_book_yaml_says_kind_paper(self):
        # when
        config = load_config(start=NEW_PAPER)

        # then
        self.assertEqual(config.kind, "paper")
        self.assertTrue(config.is_paper)

    def test_should_be_a_paper_when_the_command_line_sets_the_kind(self):
        # when
        config = load_config(start=NEW_BOOK, overrides=["kind=paper"])

        # then
        self.assertTrue(config.is_paper)


class PaperSettingsTest(unittest.TestCase):
    def test_should_give_the_paper_defaults_when_the_paper_sets_none(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text("kind: paper\n", encoding="utf-8")

            # when
            paper = load_config(start=folder).paper

        # then
        self.assertEqual(paper.authors, [])
        self.assertEqual(paper.abstract, folder / "manuscript" / "010-abstract.md")
        self.assertEqual(paper.template, "article")
        self.assertEqual(paper.engine, "xelatex")
        self.assertFalse(paper.anonymous)
        self.assertIsNone(paper.arxiv_category)
        self.assertEqual(paper.abstract_max_words, 250)
        self.assertEqual(paper.format, "a4")

    def test_should_read_every_author_when_the_paper_lists_them(self):
        # when
        paper = load_config(start=NEW_PAPER).paper

        # then
        self.assertEqual([(author.name, author.affiliation, author.email)
                          for author in paper.authors],
                         [("Sam Example", "Garden School", "sam@example.org"),
                          ("Lee Sample", None, None)])
        self.assertEqual(paper.arxiv_category, "cs.SE")
        self.assertEqual(paper.abstract_max_words, 200)

    def test_should_use_the_book_author_when_the_paper_lists_no_author(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text("kind: paper\nbook:\n  author: Ada Example\n",
                                              encoding="utf-8")

            # when
            paper = load_config(start=folder).paper

        # then
        self.assertEqual([author.name for author in paper.authors], ["Ada Example"])

    def test_should_accept_the_template_when_the_paper_names_a_built_in_venue(self):
        for venue in ("article", "acm", "ieee", "lncs"):
            with self.subTest(venue=venue):
                # given
                with TemporaryBook() as folder:
                    (folder / "book.yaml").write_text(f"kind: paper\npaper:\n  template: {venue}\n",
                                                      encoding="utf-8")

                    # when
                    paper = load_config(start=folder).paper
                    checked = run_script("book_config.py", "check", "--format", "tsv", cwd=folder)

                # then
                self.assertEqual(paper.template, venue)
                self.assertNotIn("paper.template", checked.stdout)

    def test_should_report_a_defect_when_the_paper_names_a_template_file(self):
        # given
        with TemporaryBook() as folder:
            (folder / "venue").mkdir()
            (folder / "venue" / "main.tex").write_text("\\documentclass{article}\n",
                                                       encoding="utf-8")
            (folder / "book.yaml").write_text("kind: paper\npaper:\n  template: venue/main.tex\n",
                                              encoding="utf-8")

            # when
            result = run_script("book_config.py", "check", "--format", "tsv", cwd=folder)

        # then
        self.assertEqual(result.returncode, 1)
        self.assertIn("paper.template\twrong-value", result.stdout)
        self.assertIn("article, acm, ieee, lncs", result.stdout)

    def test_should_print_the_paper_settings_when_paths_are_asked_for_shell(self):
        # when
        result = run_script("book_config.py", "paths", "--shell", cwd=NEW_PAPER)

        # then
        self.assertEqual(result.returncode, 0, result.stderr)
        values = {name: shlex.split(value)[0] if value else ""
                  for name, value in (line.split("=", 1) for line in result.stdout.splitlines())}
        self.assertEqual(values["BOOK_KIND"], "paper")
        self.assertEqual(values["PAPER_TEMPLATE"], "article")
        self.assertEqual(values["PAPER_ENGINE"], "xelatex")
        self.assertEqual(values["PAPER_ANONYMOUS"], "false")
        self.assertEqual(values["PAPER_FORMAT"], "a4")
        self.assertEqual(values["PAPER_ABSTRACT"],
                         str(NEW_PAPER / "manuscript" / "010-abstract.md"))
        self.assertEqual([author["name"] for author in json.loads(values["PAPER_AUTHORS"])],
                         ["Sam Example", "Lee Sample"])


class PaperCheckTest(unittest.TestCase):
    def test_should_accept_the_paper_when_every_paper_value_is_allowed(self):
        # when
        result = run_script("book_config.py", "check", "--format", "tsv", cwd=NEW_PAPER)

        # then
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("publishing.cover", result.stdout)
        self.assertNotIn("sales_text.", result.stdout)

    def test_should_report_a_defect_when_a_paper_value_is_not_allowed(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text(
                "kind: article\npaper:\n  engine: lualatex\n  format: a5\n"
                "  template: springer\n  abstract_max_words: many\n", encoding="utf-8")

            # when
            result = run_script("book_config.py", "check", "--format", "tsv", cwd=folder)

        # then
        self.assertEqual(result.returncode, 1)
        for key in ("kind", "paper.engine", "paper.format", "paper.template",
                    "paper.abstract_max_words"):
            self.assertIn(f"{key}\twrong-value", result.stdout)

    def test_should_accept_paper_keys_in_a_book_when_they_hold_allowed_values(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text("paper:\n  engine: pdflatex\n  format: letter\n",
                                              encoding="utf-8")

            # when
            result = run_script("book_config.py", "check", "--format", "tsv", cwd=folder)

        # then
        self.assertEqual(result.returncode, 0, result.stdout)


class PaperManuscriptTest(unittest.TestCase):
    def test_should_read_paper_sections_as_chapters_when_the_kind_is_paper(self):
        # when
        files = manuscript_files(load_config(start=NEW_PAPER))

        # then
        self.assertEqual([(item.name, item.kind, item.chapter) for item in files], [
            ("010-abstract.md", KIND_FRONT_MATTER, None),
            ("020-introduction.md", KIND_CHAPTER, 1),
            ("030-related-work.md", KIND_CHAPTER, 2),
            ("040-method.md", KIND_CHAPTER, 3),
            ("900-references.md", KIND_REFERENCES, None),
        ])

    def test_should_number_one_section_when_it_is_asked_for_alone(self):
        # given
        config = load_config(start=NEW_PAPER)

        # then
        self.assertEqual(chapter_number(NEW_PAPER / "manuscript" / "040-method.md", config), 3)
        self.assertIsNone(chapter_number(NEW_PAPER / "manuscript" / "010-abstract.md", config))

    def test_should_keep_a_file_before_the_abstract_as_front_matter_when_it_is_numbered_below_ten(self):
        # given
        with TemporaryBook(copy_of=NEW_PAPER) as folder:
            (folder / "manuscript" / "005-title-page.md").write_text("Title\n", encoding="utf-8")

            # when
            kinds = {item.name: item.kind for item in manuscript_files(load_config(start=folder))}

        # then
        self.assertEqual(kinds["005-title-page.md"], KIND_FRONT_MATTER)
        self.assertEqual(kinds["020-introduction.md"], KIND_CHAPTER)

    def test_should_keep_book_classification_when_the_same_files_are_a_book(self):
        # when
        files = manuscript_files(load_config(start=NEW_PAPER, overrides=["kind=book"]))

        # then
        self.assertEqual({item.kind for item in files}, {KIND_FRONT_MATTER, KIND_REFERENCES})


class CitationSettingsTest(unittest.TestCase):
    def test_should_give_the_default_bibliography_and_style_when_the_book_sets_none(self):
        # when
        config = load_config(start=NEW_BOOK)

        # then
        self.assertEqual(config.sources.bibliography, NEW_BOOK / "sources" / "references.bib")
        self.assertEqual(config.get("sources.bibliography"),
                         NEW_BOOK / "sources" / "references.bib")
        self.assertEqual(config.sources.citation_style, "alpha")
        self.assertIsNone(config.sources.citation_style_file)

    def test_should_resolve_the_bibliography_and_style_file_the_book_names(self):
        with TemporaryBook() as folder:
            # given
            (folder / "styles").mkdir()
            (folder / "styles" / "house.csl").write_text("<style/>", encoding="utf-8")
            (folder / "book.yaml").write_text(
                "sources:\n  bibliography: refs/works.bib\n  citation_style: numeric\n"
                "  citation_style_file: styles/house.csl\n", encoding="utf-8")

            # when
            config = load_config(start=folder)
            checked = run_script("book_config.py", "check", "--format", "tsv", cwd=folder)

        # then
        self.assertEqual(config.sources.bibliography, folder / "refs" / "works.bib")
        self.assertEqual(config.sources.citation_style, "numeric")
        self.assertEqual(config.sources.citation_style_file, folder / "styles" / "house.csl")
        self.assertNotIn("wrong-value", checked.stdout)

    def test_should_report_a_style_that_is_not_alpha_or_numeric(self):
        with TemporaryBook() as folder:
            # given
            (folder / "book.yaml").write_text("sources:\n  citation_style: harvard\n",
                                              encoding="utf-8")

            # when
            result = run_script("book_config.py", "check", "--format", "tsv", cwd=folder)

        # then
        self.assertEqual(result.returncode, 1)
        self.assertIn("sources.citation_style\twrong-value", result.stdout)

    def test_should_report_a_style_file_that_does_not_exist(self):
        with TemporaryBook() as folder:
            # given
            (folder / "book.yaml").write_text("sources:\n  citation_style_file: house.csl\n",
                                              encoding="utf-8")

            # when
            result = run_script("book_config.py", "check", "--format", "tsv", cwd=folder)

        # then
        self.assertEqual(result.returncode, 1)
        self.assertIn("sources.citation_style_file\twrong-value", result.stdout)
        self.assertNotIn("sources.citation_style_file\tmissing-path", result.stdout)

    def test_should_export_the_citation_settings_for_the_build(self):
        # when
        result = run_script("book_config.py", "paths", "--shell", cwd=NEW_BOOK)

        # then
        values = {name: shlex.split(value)[0] if shlex.split(value) else ""
                  for name, value in (line.split("=", 1) for line in result.stdout.splitlines())}
        self.assertEqual(values["BOOK_BIBLIOGRAPHY"], str(NEW_BOOK / "sources" / "references.bib"))
        self.assertEqual(values["BOOK_CITATION_STYLE"], "alpha")
        self.assertEqual(values["BOOK_CITATION_STYLE_FILE"], "")


class CommandLineTest(unittest.TestCase):
    def test_should_print_eval_ready_paths_when_asked_for_shell(self):
        # when
        result = run_script("book_config.py", "paths", "--shell", cwd=NEW_BOOK)

        # then
        self.assertEqual(result.returncode, 0, result.stderr)
        values = dict(line.split("=", 1) for line in result.stdout.splitlines())
        self.assertEqual(shlex.split(values["BOOK_SOURCES_LIST"])[0],
                         str(NEW_BOOK / "sources" / "list.md"))
        self.assertEqual(shlex.split(values["BOOK_CONFIG_FILE"])[0], str(NEW_BOOK / "book.yaml"))

    def test_should_print_one_value_when_getting_a_dotted_key(self):
        # when
        result = run_script("book_config.py", "get", "book.title", cwd=NEW_BOOK)

        # then
        self.assertEqual(result.stdout.strip(), "A Small Book: Tests")

    def test_should_fail_as_a_tool_when_the_key_is_unknown(self):
        # when
        result = run_script("book_config.py", "get", "no.such.key", cwd=NEW_BOOK)

        # then
        self.assertEqual(result.returncode, 2)

    def test_should_report_a_defect_when_book_yaml_has_an_unknown_key(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text("sources:\n  lsit: x.md\n", encoding="utf-8")

            # when
            result = run_script("book_config.py", "check", "--format", "tsv", cwd=folder)

        # then
        self.assertEqual(result.returncode, 1)
        self.assertIn("sources.lsit\tunknown-key", result.stdout)

    def test_should_report_an_unknown_key_when_book_yaml_uses_a_key_name_no_script_reads(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text("reading_notes: margin\nsources:\n  files: library\n"
                                              "work:\n  inbox: .work/in\n", encoding="utf-8")

            # when
            result = run_script("book_config.py", "check", "--format", "tsv", cwd=folder)

        # then
        self.assertEqual(result.returncode, 1)
        self.assertIn("reading_notes\tunknown-key", result.stdout)
        self.assertIn("sources.files\tunknown-key", result.stdout)
        self.assertIn("work.inbox\tunknown-key", result.stdout)

    def test_should_show_everything_as_json_when_asked(self):
        # when
        result = run_script("book_config.py", "show", "--json", cwd=NEW_BOOK)

        # then
        shown = json.loads(result.stdout)
        self.assertEqual(shown["paths"]["sources.quotes"], str(NEW_BOOK / "sources" / "quotes.md"))

    def test_should_print_help_when_asked(self):
        # then
        self.assertEqual(run_script("book_config.py", "--help").returncode, 0)


if __name__ == "__main__":
    unittest.main()
