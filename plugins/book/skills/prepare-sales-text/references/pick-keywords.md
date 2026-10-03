# Choosing keywords and categories

The `pick-keywords` mode. It is a **decision job**: choose the store keyword slots, the categories
per format and the subject codes, record them in the book's `keywords-and-categories.md` with
a reason per row, and say plainly what could not be verified. It changes no copy.

## Read first

1. The index of the book's `decisions.md` (`decisions.py index`) and the keyword entries it lists (a replaced keyword set is recorded there; never propose it again).
2. The book's `keywords-and-categories.md`, if it exists (template in `templates/`).
3. `store-limits.md`: the slot count, the avoid list, both KDP pages, the category rules.
4. The book config: title, subtitle and `book.subjects`; the price from the "Book inputs" section of
   `keywords-and-categories.md` (the config has no price key); and the audience file for the buyer.

## Facts that shape everything

- **Search demand in a narrow niche is usually thin, and a book's own coined vocabulary has
  none.** Test before believing otherwise. If the book's key terms complete to unrelated
  products, keywords are a low-leverage lever: do not spend the session hunting for a magic
  word that does not exist. Categories and the copy carry discovery.
- **KDP documents keywords as the fallback shelving lever** where no category fits, so keywords
  and categories are complements.
- **The interior is indexed.** Keywords that agree with what the manuscript already says
  compound; count how often the manuscript uses a candidate, as a whole word, in the chapter files
  the book config lists, and record the count as the reason. List those files with
  `python3 ${CLAUDE_PLUGIN_ROOT}/lib/book_config.py files --kind chapter` (the path is the first
  column) and count the whole-word, any-case matches in them with the Grep tool.

## Keyword method

1. **Derive candidates from what the title and subtitle do NOT say.** Title, subtitle and
   category words are on the avoid list; repeating them wastes a slot. The listing already owns
   those words, and they come back free: an unquoted slot matches word by word, so a slot word
   plus a title word reach a two-word query together.
2. **Test each candidate** with `search-suggestions.py --online WORD ...` and record the answer
   with the date line the script prints first: echoes itself (a real query stem), completes to
   something off-domain, completes to one rival title, or nothing. It calls an unofficial Amazon
   endpoint; you run it at your own discretion. Without `--online` it prints the manual way: type
   each word into the Amazon search box, Books department, and note the suggestions with the
   date.
3. **Fill each slot with a small cluster of related, unquoted words** in a natural order. One
   word per slot wastes most of the characters. Record which KDP page's slot-length advice you
   follow (they disagree; see `store-limits.md`).
4. **Never name another author or another author's book**, not even as a phrase that is a query
   stem. The generic word inside a rival title is legal, and the title supplies the rest of the
   query. Test for a borderline word: **does the string have a reading that is not a book
   title?** A technique name that is also a book title can pass; a phrase that is only a title
   cannot. Record every such judgement call so it is not silently reversed.
5. **Run `keyword-check.py`.** It reports title, category and avoid-list words, quotes,
   repeats, plural variants and slot length, and prints the two numbers any replacement set is
   measured against: **characters used** of about 350, and **index words the title and
   subtitle do not already carry**.
6. **Record a replaced set with its arithmetic** (characters used, new index words, which rules
   it broke) in the book file and as a `decisions.md` entry, so a later session reading only
   search results does not propose it again.

## Category method

1. **Walk the live browse tree** under Books and under Kindle eBooks
   (`https://www.amazon.com/gp/bestsellers/{books|digital-text}/{node}` and the breadcrumbs).
   Record the exact spelling and the node id of every leaf, so any row can be re-fetched rather
   than argued. The two trees differ; the differences are what make a format split real.
2. **Three per format, set separately.** Only one format usually shows in search, so split
   deliberately and put the strongest shelf on both formats on purpose.
3. **Confirm every leaf in the signed-in KDP picker** before publishing. Until then, mark the
   row "not yet" in the `Picker` column; `keyword-check.py` keeps reporting it.
4. **Re-derive the category words** after any category change: they are off-limits for keyword
   slots, and a category edit silently makes a legal slot illegal. Run `keyword-check.py`.
5. **Assert nothing about competitiveness you did not retrieve yourself in this session,** with
   where you read it. Rank figures seen in passing are not recorded.

## Subject codes and other stores

- **BISAC** (Google Books, many distributors, the EPUB's subject metadata): choose from the
  current BISAC list and record code and heading in the book file. The EPUB carries
  `book.subjects` as plain subject headings, with no codes and no named authority; keep those
  headings in step with the BISAC headings chosen here.
- **Google Play Books** has no keyword boxes; the title, subtitle and description carry search.
- **Other stores** with their own categories: record them in the same book file.

## Provenance, and why it is strict here

Research on categories and ranks can produce paths, rank figures and listing counts that are
partly invented, in the same confident voice as the real data. So:

- Every path, node id and search result carries the date it was read and how (browse store,
  picker, endpoint, agent single run).
- Write **"not verified"** instead of an estimate. A figure with no retrievable source is
  treated as absent.
- Search suggestions measure supply, not demand. No public search-volume data exists for most
  book search terms; keyword tools that sell volume figures do not show their method.

## Deliver

The filled tables with a reason per row, the two slot numbers, the list of what was not
verified, and proposed `decisions.md` entries for every judgement call and replaced set. Keywords
and categories stay editable after publish: say that the set is a starting position.
