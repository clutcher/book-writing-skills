# Store limits and rules

What the stores allow, with the page each rule comes from. **Stores change these pages without
dates.** Every row below was live on the day it was read (28 to 30 August 2026 unless a row
says otherwise); re-fetch the page before relying on a row for a real decision, and never state
a store rule from memory. Where a limit is observed in the UI rather than documented, the row
says so.

The scripts read three of these numbers from the book config so a store change needs no code
change: `sales_text.amazon_limit` (4000), `sales_text.keyword_slots` (7),
`sales_text.keyword_chars` (50), `sales_text.categories_per_format` (3).

## Amazon KDP: store description

| Rule | Source |
|---|---|
| **4,000 characters, HTML tags included** | [Description](https://kdp.amazon.com/en_US/help/topic/G201189630) |
| Allowed tags: `br p b em i u h4 h5 h6 ol ul li`. `h1`-`h3` are not supported. Double spaces collapse | same |
| Prohibited: reviews, quotes or testimonials; requests for reviews; URLs, email or postal addresses; phone numbers; prices or availability; time-sensitive information; Unicode emojis; "keywords or book tags phrases" | same |
| The "Read more" fold is **undocumented**. Community figures range 100-600 characters with no method. Design for it: the first two sentences carry the whole pitch, and do not spend an early line break | no primary source |
| Whether the description is indexed for search is **unresolved**; the only official word is the prohibition on keyword phrases in it | [Metadata Guidelines](https://kdp.amazon.com/en_US/help/topic/G201097560) |
| Keep keywords and description consistent across formats | [Keywords](https://kdp.amazon.com/en_US/help/topic/G201298500) |

`store-description-check.py` checks the limit, the tags and the mechanical part of the
prohibited list. A named competitor, an endorsement quote or a time-sensitive claim needs a
human read.

## Amazon KDP: keywords

| Rule | Source |
|---|---|
| **7 keyword slots.** About 50 characters each is **UI-observed**; Amazon does not publish the number ("keep an eye on the character limit in the text field") | [Keywords](https://kdp.amazon.com/en_US/help/topic/G201298500) |
| **Avoid list (Keywords page):** words already in the title or subtitle or in the chosen categories, subjective quality claims, time-sensitive words, misspellings, spacing and plural variants, other authors' names, brands you do not own, quotation marks | same |
| **An unquoted multi-word slot is matched word by word.** The "single words beat phrases" sentence sits inside the quotation-marks rule, whose example is: entering `"complex suspenseful whodunit"` (quoted) matches only shoppers who type all of it; entering the same words unquoted lets shoppers find the book with any of them | same |
| "Combine keywords in the most logical order" | same |
| **Prohibited outright (Metadata Guidelines, stricter):** references to other authors or to *books by other authors*, sales rank, advertisements or promotions, anything unrelated to the content, HTML tags. **Zero-tolerance policy** for "metadata that is meant to advertise, promote, or mislead" | [Metadata Guidelines](https://kdp.amazon.com/en_US/help/topic/G201097560) |
| **The two pages disagree on slot length.** Metadata Guidelines: "we recommend using phrases that are 2-3 words long". Keywords page: "single words work better than phrases". Record which you follow and why | both |
| Edits take up to 72 hours to show | Keywords |
| Keywords are NOT split across formats; set the same seven on paperback and ebook | Keywords |

**Read both pages, not only the Keywords page.** Reading only the softer page is how a
prohibited keyword gets recorded as merely risky.

## Amazon KDP: categories, title, sample, ranking

| Rule | Source |
|---|---|
| **3 categories per format**, chosen from the Amazon browse tree, not BISAC; paperback and ebook are set separately. The old route for requesting extra placements no longer exists, and KDP support does not advise | [Categories](https://kdp.amazon.com/en_US/help/topic/G200652170) |
| The browse store is where available categories are listed; **the picker itself needs a signed-in account.** Confirm every category in the live picker before publishing, and never from memory or an agent's list | same |
| A book ranks in up to 3 bestseller lists; **customer activity decides which three**, not your picks | [Sales Ranking](https://kdp.amazon.com/en_US/help/topic/G201648140) |
| Bestseller badge: rank #1 in a category holding at least 100 products | [sell.amazon.com](https://sell.amazon.com/blog/amazon-best-sellers-rank) |
| **Title and subtitle rules (read 3 October 2026):** no repeated generic keywords, no sales-rank words ("bestselling"), no advertising or promotion words ("free"), no HTML; the subtitle "must adhere to the same guidelines as your title"; title plus subtitle at most 200 characters; a print title must be on the cover and match the metadata | [Metadata Guidelines](https://kdp.amazon.com/en_US/help/topic/G201097560) |
| Categories may not be chosen to mislead; the title field forbids "unauthorized reference to other titles or authors" and to trademarked terms | [Metadata Guidelines](https://kdp.amazon.com/en_US/help/topic/G201097560) |
| **Title and subtitle lock at publish** (short grace period, print only). Keywords, categories and description stay editable | [Update book details](https://kdp.amazon.com/en_US/help/topic/G200736410) |
| Search uses "keywords, book details, and the text of each book": the interior is indexed | [Find your book](https://kdp.amazon.com/en_US/help/topic/GPYDJ3SECAVVPNVG) |
| Look Inside is automatic. **Print sample 20%, ebook sample 10%**. Print sample appears after about 9-10 business days | [Look Inside](https://kdp.amazon.com/en_US/help/topic/G200644250) |
| Amazon generally shows only **one format per book** in search results, so split categories across formats deliberately | [Troubleshoot search](https://kdp.amazon.com/en_US/help/topic/GFJUYYXPBB4QA2WJ) |
| A+ Content: up to 5 modules, about 8 business days review. **No competitor comparison of any kind.** Endorsements at most 4, only "well-known publications or public figures" | [A+ Content](https://kdp.amazon.com/en_US/help/topic/GHL7P99B7AA543CN), [Guidelines](https://kdp.amazon.com/en_US/help/topic/G4WB7VPPEAREHAAD) |
| Free or discounted review copies are allowed, **provided no review is required in exchange** | [Reviews](https://kdp.amazon.com/en_US/help/topic/G202101910) |
| Amazon Vine is not available to KDP authors (needs a professional seller account, brand registry and an FBA offer) | [Vine](https://sell.amazon.com/programs/vine) |
| **AI-content question at publish (read 3 October 2026).** When you publish a book, or edit and republish one, KDP asks whether it holds AI-generated content: text, images (cover and interior) or translations "created by an AI-based tool", even if you edited them a lot afterwards. Content you created yourself and only edited, refined or error-checked with an AI tool is "AI-assisted", and KDP does not require you to disclose it. Answer for each of the three kinds | [Content Guidelines](https://kdp.amazon.com/en_US/help/topic/G200672390) |

**Labelled folklore, no Amazon source:** "search suppression" as a KDP mechanism; the "A10
algorithm"; "50 reviews unlocks X"; "Hot New Releases needs rank above N in 30 days"; any "Look
Inside lifts conversion by X%"; the "37% ranking boost for a keyword in the subtitle". Do not
quote any of these as fact.

## Google Books and Google Play Books

| Rule | Grade |
|---|---|
| The description field takes plain text; `plain-description.py` makes it from the store description, so the two never drift | tool |
| No backend keyword boxes: title, subtitle and description carry the search words | practitioner sources, WEAK; verify in the Partner Center |
| Categories: BISAC (or BIC) subject headings, and more than one may be chosen | practitioner sources, WEAK; verify in the Partner Center |
| The full text is indexed and preview links can appear in ordinary Google search results | practitioner sources, WEAK |
| Google's content policy forbids metadata "confusingly similar to existing books, including misleading titles" | Google Play Books Partner Center help; re-fetch |

Look up BISAC codes in the current BISAC list; never type a code from memory.

## Other stores and landing pages

- A store page or landing page that takes a table of contents usually takes basic HTML only
  and styles it itself. `table-of-contents.py` makes that HTML from the manuscript headings.
- The categories and description limits of other stores were not researched here. Read the
  store's author help before filling them, and record what you found in the book's
  `keywords-and-categories.md`.

## The ebook description

The EPUB carries the book's `description` metadata as one line (no markup, no line breaks). It
is a condensed surface: it must not contradict the back cover or the store description, and it
need not match either.
