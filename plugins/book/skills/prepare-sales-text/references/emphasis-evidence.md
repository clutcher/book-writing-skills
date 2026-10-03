# Typographic emphasis, graded

What is known about bold, italic, capitals and colour in short persuasive copy, with source,
method and grade. Companion to `marketing-evidence.md`. This file makes no recommendations
except in the last section, and that section says plainly which parts are judgement.
Gathered 28 August 2026.

## How to read a grade

| Grade | Means |
|-------|-------|
| **STRONG** | Peer-reviewed with a behavioural measure, adequately powered or preregistered |
| **MODERATE** | Peer-reviewed with a behavioural measure, but small, dated, or off-domain |
| **WEAK** | Real observation, but undisclosed method, no sample size, or vendor-run |
| **OPINION** | No data. Recorded because the claim is widely repeated and needs a counterweight |
| **VERIFIED-HERE** | Numbers read directly out of the source document in the session that recorded them |

**Provenance rule.** Nothing appears below without a retrievable source. Where a study exists
but could not be retrieved, it is listed as **not retrievable** and its result is NOT stated.

**Retrieval caveat, and it matters for every "not found" below.** This work was done through
scholarly APIs (OpenAlex, Crossref, Europe PMC, NCBI, Unpaywall, OSF) and direct page fetches,
not general web search. That route finds peer-reviewed work well and practitioner blog posts
badly. So the academic gaps recorded here are real gaps; the practitioner gaps mean only that no
data-bearing version was reachable this way.

---

## 1. Does emphasised text get read first, or more?

| Finding | Source | Method | Grade |
|---|---|---|---|
| **A coloured word is much less likely to be skipped.** Skipping probability of the target word: **black 27%, grey 13%, blue 14%, green 11%, red 8%**, every colour significantly below black. Verbatim: "the saliency of the coloured target word draws attention to it, making it more likely that participants will fixate on it" | Fitzsimmons, Weal & Drieghe (2019), *PLoS ONE* 14(2), DOI [10.1371/journal.pone.0210900](https://doi.org/10.1371/journal.pone.0210900) | Eye tracking, single sentences, Exp1 n=30, linear mixed models | **STRONG**, **VERIFIED-HERE** (read from the article XML) |
| **Salience costs nothing in reading time unless it costs contrast.** No fixation-duration effect for blue or red. Grey raised first fixation +23 ms (t=2.88), single fixation +34 ms, gaze +36 ms; green raised go-past +58 ms and total time +77 ms. The authors attribute both to luminance: grey 80.0, green 73.2, background 103.0, versus blue 10.2, red 18.6, black 0.7 cd/m2 | same | same | **STRONG**, **VERIFIED-HERE** |
| **Bolding everything is worse than bolding nothing.** Bolding the first half of every word "did not facilitate reading relative to bolding the middle half or last half of every word and, in fact, led to costs relative to regular unbolded reading" | Spear, Johnson, Yun, Ashby & Kleinsmith (2025), *Attention, Perception & Psychophysics* 87(4) 1270-1286, DOI [10.3758/s13414-025-03067-w](https://doi.org/10.3758/s13414-025-03067-w), PMID 40240742 | Eye tracking, 25 paragraphs, 5 bolding conditions within-subject. **Preregistered** ([OSF fnc98](https://osf.io/fnc98/), registration `ctb97`), target 60 skilled readers. Final analysed n not stated in the abstract and the paper is paywalled | **STRONG** for its own question |
| **Text captures attention in direct proportion to its surface size**, and "only increments in the text element's surface size produce a net gain in attention to the advertisement as a whole" | Pieters & Wedel (2004), *Journal of Marketing* 68(2) 36-50, DOI [10.1509/jmkg.68.2.36.27794](https://doi.org/10.1509/jmkg.68.2.36.27794) | Infrared eye tracking, **1,363 print advertisements, more than 3,600 consumers** | MODERATE-STRONG. Size, not weight; ads, not prose |
| Signalling raises transfer and comprehension by **r = 0.17, 95% CI [.11, .22]**, moderated by prior knowledge, largest for **low** prior knowledge | Richter, Scheiter & Eitel (2015), *Educational Research Review* 17, 19-36, DOI [10.1016/j.edurev.2015.12.003](https://doi.org/10.1016/j.edurev.2015.12.003) | Meta-analysis, 27 studies, 45 comparisons, **N = 2,464** | MODERATE-STRONG, off-domain (text-picture signalling in multimedia learning) |
| **Emphasis buys form at the cost of meaning.** Visual input enhancement gave **d = 0.22** on the enhanced form and **d = -0.26** on learners' meaning processing | Lee & Huang (2008), *Studies in Second Language Acquisition* 30(3) 307-331, DOI [10.1017/S0272263108080479](https://doi.org/10.1017/S0272263108080479) | Meta-analysis, 16 studies, 20 samples. Authors themselves flag possible publication bias | MODERATE, off-domain (L2 grammar) |
| **Highlighting and underlining rated LOW utility**, alongside rereading and summarisation. "most students report rereading and highlighting, yet these techniques do not consistently boost students' performance" | Dunlosky, Rawson, Marsh, Nathan & Willingham (2013), *Psychological Science in the Public Interest* 14(1) 4-58, DOI [10.1177/1529100612453266](https://doi.org/10.1177/1529100612453266) | Ten techniques reviewed across conditions, learners, materials and criterion tasks | **STRONG** as a review, but about **reader-generated** highlighting as a study technique |
| Pre-existing **inappropriate** highlighting impairs comprehension, replicated, and also distorts metacognitive accuracy | Silvers & Kreiner (1997), DOI [10.1080/19388079709558240](https://doi.org/10.1080/19388079709558240); Gier, Kreiner & Natz-Gonzalez (2009), *J. General Psychology* 136(3) 287-302, DOI [10.3200/GENP.136.3.287-302](https://doi.org/10.3200/GENP.136.3.287-302), n=180 | Between-subjects, passages varied by highlighting condition | MODERATE |

**The honest summary of section 1.** Emphasis reliably wins a fixation on the emphasised word. It does
that by lowering the chance the word is skipped, not by pulling the eye out of sequence. Nothing
retrieved shows emphasis winning the *first* fixation in a block, and nothing retrieved shows it
improving comprehension of the surrounding text; the two meta-analytic results that speak to
surrounding text point the other way (d = -0.26 on meaning; low utility as a study aid).

## 2. How much emphasis is too much?

**One measured saturation point exists, and it is small.** Fitzsimmons et al. Experiment 2 (n=36) put
0, 1 or 3 coloured words in a sentence. Skipping probability of the target: high-frequency words
**21 / 17 / 19 percent**, low-frequency **15 / 13 / 14 percent**. Verbatim from the paper: "this effect
is only present when there is only a single coloured word. When there are three coloured words the
reduction in skipping does not happen and the skipping rates are in line with reading when there are no
coloured words in the text." Grade **STRONG**, **VERIFIED-HERE**. Caveats that matter: it is colour not
bold, one sentence not a 350-word block, and three items is a count, not a percentage.

The other endpoint is Spear et al. 2025 above: at 100% bolding the effect is a cost. So the two
retrievable data points bracket the curve at roughly "one is useful" and "everything is harmful", with
**nothing measured in between**.

| Claim | Verdict |
|---|---|
| "Bold more than 10% and nothing stands out" | **FOLKLORE.** No source with data was reachable for any numeric threshold, in this or any adjacent form |
| "If everything is emphasized, then nothing is emphasized" | **OPINION**, and honestly presented as such by its best-known statement: Butterick, *Practical Typography*, [bold-or-italic](https://practicaltypography.com/bold-or-italic.html), advises "use bold and italic as little as possible" and cites no research at all |
| Cueing can cost the reader on **un**cued material | **MODERATE.** Foster & Coles (1977), *Ergonomics* 20(1) 57-66, DOI [10.1080/00140137708931601](https://doi.org/10.1080/00140137708931601): capitals cueing raised scores on cued information but **lowered** scores on non-cued information versus control, while bold cueing showed no such trade-off. 3-minute reading, recall test |

## 3. Where should emphasis go?

The question: is bold wasted on an opening the eye reads anyway?

| Finding | Source | Method | Grade |
|---|---|---|---|
| **Skimmers already over-read the opening.** Verbatim: "Skim readers spent more time reading text that was earlier in the paragraph, toward the top of the page and in an earlier page of the document." Also: **no advantage of skimming over simply reading the first or second half of every paragraph** | Duggan & Payne (2009), *J. Experimental Psychology: Applied* 15(3) 228-242, DOI [10.1037/a0016995](https://doi.org/10.1037/a0016995) | 3 experiments plus 2 more, expository texts, time limited to half the document, page-by-page reading times and eye tracking in Exp 2 | **STRONG** |
| Emphasis acts by **reducing skipping**, and in the baseline condition only **27%** of target words were skipped at all | Fitzsimmons et al. (2019), Exp 1 | see section 1 | **STRONG** for the measurement; the step from it to "emphasis has room to work only where a reader would otherwise skip" is an **inference**, labelled as such |
| Users skip repeated opening words of consecutive lines or list items (NN/g calls this the **bypassing** pattern) | Pernice, NN/g, [F-shaped pattern](https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content/), 12 Nov 2017 | Eyetracking heatmaps. **No aggregate sample size, no statistics, not peer reviewed** | WEAK, and it cuts against "the opening is always read" |

**No study was found that manipulates the POSITION of emphasis** (opening sentence versus mid-paragraph)
and measures attention, comprehension or persuasion. The argument that bolding an opening is redundant
is therefore **supported by converging measurement and contradicted by none**, but it has not been
tested directly. Duggan & Payne is the strongest thing that bears on it, and it measures dwell under
time pressure, not the effect of adding emphasis.

## 4. Bold versus italic versus colour versus capitals

| Finding | Source | Grade |
|---|---|---|
| **The all-caps folklore is not what the vision science says.** Verbatim: "Lower-case thresholds were roughly 0.1 log unit higher than upper. Reading speeds were higher for upper- than for mixed-case text at sizes twice acuity size; at larger sizes, the upper-case advantage disappeared." Upper case is more legible **near the acuity limit**, because smaller letters can be used | Arditi & Cho (2007), *Vision Research* 47(19) 2499-2505, DOI [10.1016/j.visres.2007.06.010](https://doi.org/10.1016/j.visres.2007.06.010), PMID 17675131 | **STRONG**, and it settles only the small-size case. At back-cover sizes the upper-case advantage is gone, and this study does not license "caps are fine" |
| Capitals cueing traded a gain on cued material for a **loss** on non-cued material; bold did not | Foster & Coles (1977), see section 2 | MODERATE, and the only retrieved head-to-head of bold against capitals |
| Colour: red drew the strongest reduction in skipping with **no** reading-time cost; low-contrast colours (grey, green) cost time in early and late measures. Contrast, not hue, is the variable | Fitzsimmons et al. (2019) | **STRONG**, **VERIFIED-HERE** |
| Red cueing on screen produced "no significant difference between the experimental conditions and the control" overall; cueing a whole sentence **hindered** overall recall while cueing the specific detail helped | Dyson & Gregory (2002), *Visible Language* 36(3) 326- | WEAK-MODERATE. Sample size not retrievable |
| The canonical all-caps slowdown study | Tinker & Paterson (1928), *J. Applied Psychology* 12(4) 359-368, DOI [10.1037/h0073699](https://doi.org/10.1037/h0073699) | **Abstract not retrievable.** The widely quoted "all caps is 13-20% slower" figure is NOT sourced here, and must not be quoted from this file |
| Headline search, capitals versus lower case, 264 adults | Poulton (1967), *J. Applied Psychology* 51(5, Pt.1) 417-425, DOI [10.1037/h0025098](https://doi.org/10.1037/h0025098) | **Result not retrievable.** Every index reached truncates the abstract mid-sentence |
| **Italic versus bold** | -- | **Nothing found.** No measured comparison of italic against bold for either salience or legibility was retrievable |

## 5. Scanning patterns in short blocks of prose

All of this is Nielsen Norman Group, and none of it is peer reviewed or reports statistics.

- **F-pattern**, Nielsen, 17 Apr 2006: "232 users" across "thousands of Web pages", heatmaps only. The
  2017 restatement is candid about the shape: "The F viewing pattern is a rough, general shape rather
  than a uniform, pixel-perfect behavior", sometimes an E, sometimes an inverted L.
- **Pernice, 12 Nov 2017 and 25 Aug 2019**: six named patterns (F, spotted, layer-cake, marking,
  bypassing, commitment). The F-pattern is said to occur when "a page or a section of a page includes
  text that has little or no formatting for the web", and to be **bad** for the reader: "users may skip
  important content simply because it appears on the right side of the page." Individual heatmaps cite
  47 and 45+ participants; **no aggregate N, no method, no significance testing anywhere**.
- Grade **WEAK** as evidence, **useful as description**. NN/g's own framing is the reason it half
  transfers to a 350-word prose block: by their account the F-pattern is what unformatted prose gets.
  But the underlying material is web pages with links, headings and navigation, and a back cover has
  none of those.
- **The better-measured analogue is Duggan & Payne (2009)** in section 3, which found the same
  early-and-top gradient with eye tracking on expository text and published its method.
- The 1997 "How Users Read on the Web" numbers (scannable 47%, concise 58%, objective 27%, combined
  124%) are recorded in `marketing-evidence.md` (plain-language section). Note for this
  file: the scannable version **bundled** highlighted keywords with bullets, subheads and half the word
  count, so it isolates nothing about bold. WEAK.

## 6. Bulleted lists versus prose

**Nothing measured was found.** Searches across OpenAlex title-and-abstract space for list format
against prose, on comprehension, recall or scanning, returned no relevant experimental study. NN/g
recommends bullets in its F-pattern remedy list with no data behind it. Grade **OPINION**.

What does exist is convention: in many store categories most descriptions, and many back
covers, carry a bulleted list. Count it in the book's own category (each book records its
category in `keywords-and-categories.md`). That says what publishers do. It says nothing about what works.

## 7. Searched, and not found

Recorded so nobody repeats these:

- Any study manipulating the **position** of emphasis within a passage and measuring anything.
- Any study of emphasis in **marketing or persuasive copy** with a purchase or intent outcome.
- Any data-bearing source for a **percentage ceiling** on emphasis ("no more than 10% bold").
- Any measured comparison of **italic against bold**.
- Any experimental comparison of **bulleted list against prose**.
- Any eye-tracking study of a **book back cover or store description**.
- Full text or abstract of Tinker & Paterson (1928) and Poulton (1967); both are indexed with results
  unretrievable.
- Abstract or effect sizes of Schneider, Beege, Nebel & Rey (2018), "A meta-analysis of how signaling
  affects learning with media", *Educational Research Review* 23, 1-24,
  DOI [10.1016/j.edurev.2017.11.001](https://doi.org/10.1016/j.edurev.2017.11.001). Paywalled at every
  route tried, and elided by Semantic Scholar at the publisher's request. **The study exists; its
  numbers are not in this file and must not be invented.**
- Abstracts of the classic cueing studies: Lorch (1989), Lorch, Lorch & Klusewitz (1995), Glynn & Di
  Vesta (1979), Frase & Schwartz (1979), Fowler & Barker (1974). All indexed, all abstract-less in
  Crossref, OpenAlex and Semantic Scholar alike. **Their findings are not stated anywhere above.**

---

## What this means for a back cover

**Supported by the graded evidence:**

1. **Emphasis works by stopping a skip, not by jumping the queue.** The one clean measurement of what
   salience does to reading (Fitzsimmons et al.) is a drop in skipping probability with no reordering
   of the eye and no reading-time cost. So emphasis pays where a reader would otherwise pass over.
2. **A small number of emphasised items is the whole effect.** One coloured word in a sentence worked;
   three did not. Bolding every word cost the reader outright. Between one and everything, the evidence
   is silent, but both retrievable endpoints point the same way: fewer.
3. **The opening is already privileged.** Skimmers spend more time earlier in the paragraph and higher
   on the page (Duggan & Payne). Emphasis there is spent where attention already is. This is supported
   by measurement, not proven by a direct test.
4. **Do not use capitals for emphasis in running copy.** The only retrieved bold-versus-capitals
   comparison found capitals imposing a cost on the surrounding uncued material that bold did not. The
   vision-science defence of capitals (Arditi & Cho) applies at the acuity limit and expressly
   disappears at larger sizes, which is where a back cover lives.
5. **If colour is used, contrast is the variable, not hue.** Red and blue were free; grey and green cost
   time, and the paper ties that to luminance against the background.
6. **Do not claim emphasis aids comprehension.** The two meta-analytic results that touch surrounding
   text point the other way, and highlighting as a technique is rated low utility.

**Where the decision has to rest on judgement, and cannot rest on evidence:**

- **How many bold spans a 350-word block should carry.** Nothing measures this. "One, maybe two, per
  block" is an extrapolation from a three-word saturation point in a single sentence, and should be
  described as a choice, not a finding.
- **Whether to bold at all in a medium a reader picks up already committed.** Every study above is
  reading or study or advertising; none is a book cover in a reader's hand.
- **Bullets versus prose.** Pure convention. Choose it for category fit, and do not dress it as an
  evidence-based decision.
- **Italic against bold.** No evidence exists either way. Decide on tone.

The pattern here matches what `marketing-evidence.md` (conversion evidence) concluded about conversion evidence:
the measured literature answers a narrower question than the one being asked. It is strong on where an
eye lands in a sentence and silent on whether a bolded phrase sells a book. Say so when a decision is
made, and record the decision as judgement.
