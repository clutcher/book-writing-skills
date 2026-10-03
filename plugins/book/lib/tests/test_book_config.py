import json
import shlex
import unittest
from pathlib import Path

from support import NEW_BOOK, OLD_BOOK, PREVIOUS_BOOK, TemporaryBook, run_script

import book_config
from book_config import (KIND_BACK_MATTER, KIND_CHAPTER, KIND_FRONT_MATTER, KIND_PART,
                         KIND_REFERENCES, LAYOUT_NEW, LAYOUT_OLD, LAYOUT_PREVIOUS, ConfigError,
                         chapter_number, load_config, manuscript_files, read_yaml_subset)


class NewLayoutBookTest(unittest.TestCase):
    def setUp(self):
        self.config = load_config(start=NEW_BOOK / "manuscript")

    def test_should_find_book_yaml_when_started_in_a_subfolder(self):
        # then
        self.assertEqual(self.config.config_file, NEW_BOOK / "book.yaml")
        self.assertEqual(self.config.root, NEW_BOOK)
        self.assertEqual(self.config.layout, LAYOUT_NEW)

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


class OldLayoutBookTest(unittest.TestCase):
    def setUp(self):
        self.config = load_config(start=OLD_BOOK / "manuscript")

    def test_should_fall_back_to_claude_md_when_no_book_yaml_exists(self):
        # then
        self.assertIsNone(self.config.config_file)
        self.assertEqual(self.config.fallback_file, OLD_BOOK / "CLAUDE.md")
        self.assertEqual(self.config.layout, LAYOUT_OLD)
        self.assertEqual(self.config.source, book_config.SOURCE_FALLBACK)

    def test_should_use_old_default_paths_when_reading_claude_md(self):
        # given
        paths = self.config.resolved_paths()

        # then
        self.assertEqual(paths["sources.list"], OLD_BOOK / "review" / "sources-registry.md")
        self.assertEqual(paths["sources.quotes"],
                         OLD_BOOK / "review" / "fact-check-findings-registry.md")
        self.assertEqual(paths["rules.glossary"], OLD_BOOK / "review" / "glossary-registry.md")
        self.assertEqual(paths["sources.library"], OLD_BOOK / "review" / "sources")
        self.assertEqual(paths["thinking.argument"], OLD_BOOK / "research")
        self.assertEqual(paths["sources.to_add"], OLD_BOOK / "review" / "sources" / "incoming")
        self.assertEqual(paths["work.output"], OLD_BOOK / "output")
        self.assertEqual(paths["manuscript.references"],
                         OLD_BOOK / "manuscript" / "900-references.md")

    def test_should_read_metadata_like_sed_when_lines_carry_comments(self):
        # given
        book = self.config.book

        # then
        self.assertEqual(book.title, "The Old Book")
        self.assertEqual(book.get("TOC"), "false")
        self.assertEqual(book.get("EPUB-Identifier"),
                         "urn:uuid:00000000-0000-0000-0000-000000000000")
        self.assertEqual(book.path("Cover-Front"), OLD_BOOK / "cover" / "png" / "front.png")
        self.assertNotIn("note", book.values)
        self.assertNotIn("manuscript", book.values)

    def test_should_read_term_tables_when_coined_terminology_exists(self):
        # given
        terms = self.config.terms

        # then
        self.assertEqual([(f.term, f.role, f.also) for f in terms.families], [
            ("mulched", "primary", ["mulching", "mulcher"]),
            ("bare", "antonym", ["bareness"]),
            ("humus", "borrowed", []),
        ])
        self.assertEqual(terms.compounds, ["mulched soil", "bare soil"])


class PreviousLayoutBookTest(unittest.TestCase):
    def setUp(self):
        self.config = load_config(start=PREVIOUS_BOOK)

    def test_should_use_previous_defaults_when_the_book_has_no_new_folders(self):
        # then
        self.assertEqual(self.config.layout, LAYOUT_PREVIOUS)
        self.assertEqual(self.config.rules.decisions, PREVIOUS_BOOK / "decisions.md")
        self.assertEqual(self.config.rules.glossary, PREVIOUS_BOOK / "vocabulary" / "glossary.md")
        self.assertEqual(self.config.rules.vale_ini, PREVIOUS_BOOK / "style" / "vale.ini")
        self.assertEqual(self.config.thinking.argument, PREVIOUS_BOOK / "reasons")
        self.assertEqual(self.config.thinking.audience,
                         PREVIOUS_BOOK / "author" / "positioning.md")
        self.assertEqual(self.config.sources.library, PREVIOUS_BOOK / "sources" / "files")
        self.assertEqual(self.config.sources.library_index, PREVIOUS_BOOK / "sources" / "origin")
        self.assertEqual(self.config.notes, PREVIOUS_BOOK / "reading-notes")
        self.assertEqual(self.config.publishing.sales_text, PREVIOUS_BOOK / "marketing")
        self.assertEqual(self.config.cover.final, PREVIOUS_BOOK / "cover" / "final")

    def test_should_answer_to_old_attribute_names_when_a_script_still_uses_them(self):
        # then
        self.assertEqual(self.config.decisions, self.config.rules.decisions)
        self.assertEqual(self.config.glossary, self.config.rules.glossary)
        self.assertEqual(self.config.reading_notes, self.config.notes)
        self.assertEqual(self.config.reasons, self.config.thinking.argument)
        self.assertEqual(self.config.author.positioning, self.config.thinking.audience)
        self.assertEqual(self.config.style.dir, self.config.rules.vale)
        self.assertEqual(self.config.sources.files, self.config.sources.library)
        self.assertEqual(self.config.marketing.amazon, self.config.sales_text.amazon)
        self.assertEqual(self.config.cover.dir, self.config.publishing.cover)

    def test_should_choose_the_new_layout_when_one_new_folder_exists(self):
        # given
        with TemporaryBook(PREVIOUS_BOOK) as folder:
            (folder / "rules").mkdir()

            # when
            config = load_config(start=folder)

        # then
        self.assertEqual(config.layout, LAYOUT_NEW)
        self.assertEqual(config.rules.decisions, folder / "rules" / "decisions.md")

    def test_should_follow_the_layout_key_when_the_book_names_its_layout(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text("layout: previous\n", encoding="utf-8")

            # when
            config = load_config(start=folder)

        # then
        self.assertEqual(config.layout, LAYOUT_PREVIOUS)
        self.assertEqual(config.notes, folder / "reading-notes")

    def test_should_fail_when_the_layout_key_names_no_layout(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text("layout: newest\n", encoding="utf-8")

            # when / then
            with self.assertRaisesRegex(ConfigError, "layout must be one of"):
                load_config(start=folder)


class OldKeyNamesTest(unittest.TestCase):
    def test_should_read_old_key_names_as_the_new_keys(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text(
                "decisions: meta/choices.md\nreading_notes: margin\nreasons: why\n"
                "vocabulary:\n  glossary: meta/terms.md\n  heading_separator: ' | '\n"
                "author:\n  positioning: meta/who.md\n  voice: meta/voice.md\n"
                "style:\n  dir: lint\nsources:\n  files: library\n  origin: index\n"
                "cover:\n  dir: art\n  paper: cream\nmarketing:\n  dir: selling\n"
                "  amazon_limit: 3000\n", encoding="utf-8")

            # when
            config = load_config(start=folder)

        # then
        self.assertEqual(config.rules.decisions, folder / "meta" / "choices.md")
        self.assertEqual(config.notes, folder / "margin")
        self.assertEqual(config.thinking.argument, folder / "why")
        self.assertEqual(config.rules.glossary, folder / "meta" / "terms.md")
        self.assertEqual(config.get("vocabulary.heading_separator"), " | ")
        self.assertEqual(config.thinking.audience, folder / "meta" / "who.md")
        self.assertEqual(config.rules.voice, folder / "meta" / "voice.md")
        self.assertEqual(config.rules.vale, folder / "lint")
        self.assertEqual(config.sources.library, folder / "library")
        self.assertEqual(config.sources.library_index, folder / "index")
        self.assertEqual(config.publishing.cover, folder / "art")
        self.assertEqual(config.cover.paper, "cream")
        self.assertEqual(config.publishing.sales_text, folder / "selling")
        self.assertEqual(config.sales_text.amazon, folder / "selling" / "amazon.html")
        self.assertEqual(config.get("sales_text.amazon_limit"), 3000)

    def test_should_answer_an_old_key_name_when_a_value_is_asked_for(self):
        # given
        config = load_config(start=NEW_BOOK)

        # then
        self.assertEqual(config.get("sources.files"), config.sources.library)
        self.assertEqual(config.get("reading_notes"), config.notes)
        self.assertEqual(config.path("decisions"), config.rules.decisions)
        self.assertEqual(config.get("marketing.amazon_limit"), 4000)

    def test_should_keep_the_new_name_when_a_book_sets_both_names(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text("notes: new-place\nreading_notes: old-place\n",
                                              encoding="utf-8")

            # when
            config = load_config(start=folder)

        # then
        self.assertEqual(config.notes, folder / "new-place")

    def test_should_give_an_old_name_override_to_the_new_key(self):
        # when
        config = load_config(start=NEW_BOOK, overrides=["sources.files=elsewhere"])

        # then
        self.assertEqual(config.sources.library, NEW_BOOK / "elsewhere")

    def test_should_name_the_new_key_when_checking_a_book_with_old_names(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text("reading_notes: margin\nmarketing:\n"
                                              "  keyword_slots: 5\n", encoding="utf-8")

            # when
            result = run_script("book_config.py", "check", "--format", "tsv", cwd=folder)

        # then
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("reading_notes\told-key-name\tbook.yaml: 'reading_notes' is an old name; "
                      "write 'notes'", result.stdout)
        self.assertIn("marketing.keyword_slots\told-key-name", result.stdout)
        self.assertNotIn("unknown-key", result.stdout)

    def test_should_report_a_defect_when_a_retired_key_is_set(self):
        # given
        with TemporaryBook() as folder:
            (folder / "book.yaml").write_text("work:\n  dir: .work\n  inbox: .work/in\n"
                                              "sources:\n  incoming: drop\n", encoding="utf-8")

            # when
            result = run_script("book_config.py", "check", "--format", "tsv", cwd=folder)
            config = load_config(start=folder)

        # then
        self.assertEqual(result.returncode, 1)
        self.assertIn("work.inbox\tretired-key", result.stdout)
        self.assertIn("sources.incoming\tretired-key", result.stdout)
        self.assertEqual(config.sources.to_add, folder / ".work" / "sources-to-add")

    def test_should_say_which_layout_when_checking_a_book_in_the_previous_layout(self):
        # when
        result = run_script("book_config.py", "check", "--format", "tsv", cwd=PREVIOUS_BOOK)

        # then
        self.assertIn("layout\tprevious-layout", result.stdout)


class ConfigPrecedenceTest(unittest.TestCase):
    def test_should_prefer_book_yaml_over_claude_md_when_both_exist(self):
        # given
        with TemporaryBook(OLD_BOOK) as folder:
            (folder / "book.yaml").write_text("book:\n  title: From Yaml\n", encoding="utf-8")

            # when
            config = load_config(start=folder)

        # then
        self.assertEqual(config.book.title, "From Yaml")
        self.assertEqual(config.book.author, "Pat Example")
        self.assertEqual(config.layout, LAYOUT_NEW)

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

    def test_should_use_old_defaults_when_only_the_old_sources_bank_exists(self):
        # given
        with TemporaryBook() as folder:
            (folder / "review").mkdir()
            (folder / "review" / "sources-registry.md").write_text("# x\n", encoding="utf-8")

            # when
            config = load_config(start=folder)

        # then
        self.assertEqual(config.layout, LAYOUT_OLD)
        self.assertEqual(config.sources.list, folder / "review" / "sources-registry.md")

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


class CommandLineTest(unittest.TestCase):
    def test_should_print_eval_ready_paths_when_asked_for_shell(self):
        # when
        result = run_script("book_config.py", "paths", "--shell", cwd=OLD_BOOK)

        # then
        self.assertEqual(result.returncode, 0, result.stderr)
        values = dict(line.split("=", 1) for line in result.stdout.splitlines())
        self.assertEqual(shlex.split(values["BOOK_SOURCES_LIST"])[0],
                         str(OLD_BOOK / "review" / "sources-registry.md"))
        self.assertEqual(shlex.split(values["BOOK_LAYOUT"])[0], "old")

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
