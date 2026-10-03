# Launch checklist

Packaging items a non-fiction book is judged on at the shelf, collected from outside reviews.
Each is a question for the author, not a rule: several are commonly decided "no" for good
reasons, and the answer goes to `decisions.md` either way so reviews stop raising it.

## The book itself

- [ ] **Title page and subtitle** present in the built book and in every store listing, spelled
      exactly as in the book config.
- [ ] **A professional rights and permissions contact** on the copyright page: a domain-based
      address or the book's site reads better on a permanent page than a personal mailbox.
- [ ] **Companion material** (worksheets, recipes, maps, data, code), if the book has any:
      readers in many fields expect it, and a companion page is also a search asset for a
      hard-to-search title. Referenced from the copyright page.
- [ ] **An index**, for a print reference or how-to book, or a recorded decision not to have one.
- [ ] **Errata channel**: a book website or companion page, the only channel for fixes after
      print.
- [ ] **"Who this book is for"** easy to find: a short section, or preface subheads, that a
      sampler can scan.
- [ ] **A one-page download** of the book's core checklist or questions, if it has one: a lead
      magnet and something readers link to.
- [ ] **Dated specifics** (named tools, predictions with years) reviewed for how they will read
      in three years; a book that claims to be timeless should not date itself on page 20.
- [ ] **An AI-use disclosure**: whether the book makes one, where, and in what words.

## The listing

- [ ] Title and subtitle final (they lock at publish).
- [ ] Categories confirmed in the signed-in store picker, three per format.
- [ ] Keyword slots identical on every format; `keyword-check.py` clean.
- [ ] Store description: `store-description-check.py` clean; `sync-check.py` shows no
      contradiction; the plain-text version regenerated (`plain-description.py --fix`).
- [ ] Ebook description in the book config agrees with the other surfaces.
- [ ] Table of contents for other stores regenerated from the manuscript (`table-of-contents.py`).
- [ ] Free sample: which chapters it reaches (print and ebook differ) and whether the copy
      promises anything the sample does not show.
- [ ] Which chapter a retailer's free sample shows first, if the store lets you choose.
- [ ] Author page: the same credibility signals the book uses in its own text, in the same
      restraint.
- [ ] Price recorded as a decision, with the category context.
- [ ] A trademark-style search on the book's coined words before print.
- [ ] KDP AI-content question answered truthfully (generated vs assisted) for text, cover
      images and translations; see `store-limits.md`.

## After launch

- [ ] Review copies: allowed free or discounted, never in exchange for a required review.
- [ ] Watch which categories the book actually ranks in; revise categories and keywords from
      that signal, not from guesses (both stay editable).
