# Readability scores: what they measure and what they cannot

Readability formulas are built into writing tools, so a score is often the first answer to "is
this readable?". Use a score as a surface signal, never as a target.

## The formulas

| Formula | Computed from |
|---|---|
| Flesch Reading Ease (1948) | 206.835 - 1.015 x (words per sentence) - 84.6 x (syllables per word) |
| Flesch-Kincaid Grade Level (1975) | 0.39 x (words per sentence) + 11.8 x (syllables per word) - 15.59 |
| Gunning Fog (1952) | 0.4 x (words per sentence + 100 x share of words with 3+ syllables) |
| SMOG (1969) | count of words with 3+ syllables in a sample of sentences |
| Automated Readability Index (1967) | characters per word and words per sentence |
| Coleman-Liau (1975) | letters and sentences per 100 words |

Every one measures two things: **word length** (a stand-in for how familiar the words are) and
**sentence length** (a stand-in for sentence difficulty). Neither was derived from a theory of
reading; both were chosen because they correlated with scores on graded passages and were cheap
to count.

**The coefficients cannot be compared.** "Word difficulty matters 80 times more than sentence
length" divides 84.6 by 1.015, two numbers on different units. Over typical prose, syllables per
word move the Flesch score by about 68 points and words per sentence by about 20: a factor of
about three, and a fact about the formula, not about readers.

## Adoption is not validation

Formulas were adopted by the military, written into insurance law and built into word
processors. None of that shows they predict understanding, and still less that writing to a
score improves it.

## The central problem

The correlation holds **across texts**: harder passages tend to score worse. It does **not**
hold **within a text under editing**: shortening sentences to move the score does not reliably
make the text easier to understand, and can make it harder, because the edits that lower the
score are not the edits that make meaning clearer. A predictor is not an intervention. In
Duffy and Kabance (1982), rewriting passages to halve sentence length (about 20 to 10 words)
gave no comprehension gain in a series of four experiments, and swapping a quarter of the
content words for easier ones helped in only one; Redish (2000) reviews why.

## What a formula cannot see

| Ignored | Why |
|---|---|
| Organisation | no formula looks across sentences or sections |
| Visual grouping | layout is invisible to a sentence count, and lists are mis-parsed |
| Topic structure and coherence | no relation between sentences is measured |
| Whether the content is right | no formula reads meaning or checks a fact |
| The reader's knowledge | formulas score text, not readers; a text easy for an expert can be hard for a beginner |

## Use and misuse

Defensible uses, all comparative or procedural:
- flagging passages for a person to review;
- comparing two drafts of the same text;
- meeting a legal requirement that names a score.

Uses the evidence rules out:
- as a measure of quality;
- as a rewriting target;
- on text with lists, tables or headings;
- comparing texts of different kinds or for different audiences;
- on text the formula was not fitted to, such as verse, lists of steps or source code.

## What to do instead

1. **Test with readers.** A few readers doing the task the text supports find most of the
   major failures. The usual "about five" comes from software usability testing (Nielsen and
   Landauer 1993), not from tests of books; treat it as a starting number, not a law.
2. **Follow plain-language practice:** start from what the reader must do, organise with
   informative headings, use white space and lists where the reader scans, prefer the active
   voice and common words, and test.
3. **Treat a score as a flag, never a goal.**

What readers *say* is readable is also a weak measure (practice advice; no single study is
cited here): a reader's rating and a reader's understanding can differ. Ask readers to do
something with the text, and measure that.

Two further cautions: no complexity score may be cited as predicting how hard a text is to
understand, and a sentence-length target is a style choice of the voice profile, not a finding.

## Sources

- Duffy, T. M. and Kabance, P. (1982). "Testing a readable writing approach to text revision".
  *Journal of Educational Psychology* 74(5) 733-748. DOI 10.1037/0022-0663.74.5.733.
- Redish, J. (2000). "Readability formulas have even more limitations than Klare discusses".
  *ACM Journal of Computer Documentation* 24(3) 132-137. DOI 10.1145/344599.344637.
- Nielsen, J. and Landauer, T. K. (1993). "A mathematical model of the finding of usability
  problems". *Proceedings of INTERCHI '93*, 206-213. DOI 10.1145/169059.169166.
