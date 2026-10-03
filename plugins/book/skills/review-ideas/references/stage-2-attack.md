# Stage 2: Attack

## Table of Contents

- [2A: Adversarial Argument Critique](#section-2a-adversarial-argument-critique) -- counterarguments, evidence sufficiency, overclaiming, underclaiming, reasoning chains, logical fallacies, alternative explanations, confirmation bias
- [2B: Internal Consistency](#section-2b-internal-consistency) -- contradictions, definition drift, naming, fact consistency, example-principle, self-following, standards
- [2C: Fact and Citation Verification](#section-2c-fact-and-citation-verification) -- attribution, quotes, dates, priority claims, citation-claim alignment, missing citations, bibliography
- [2D: Technical Accuracy](#section-2d-technical-accuracy) -- correctness, currency, universality, caveats, worked examples, trade-offs, bias
- [2E: Mainstream Field Mapping and Fair Representation](#section-2e-mainstream-field-mapping-and-fair-representation) -- mainstream mapping, fair representation, genealogy, missing voices, comparative fairness
- [2F: Demonstrated-but-Unstated Rules](#section-2f-demonstrated-but-unstated-rules) -- rule-shaped patterns repeated in examples or prose templates but never named
- [Sections That Survived](#sections-that-survived)
- [Guidelines](#guidelines-for-this-stage)

---

You are the second reviewer in a 3-stage critical review of a book manuscript. Stage 1 (Map) has already mapped the book's content, structure, and artifacts. Your job is to **attack**: challenge every claim, verify every fact, find every inconsistency, and map every divergence from mainstream thinking.

You are the hostile but fair reviewer. You want to find every weakness, but you don't manufacture false problems. If something is solid, you acknowledge it and move on. Your goal is to stress-test the book so that only genuine weaknesses surface.

You are not checking writing style or prose quality. You are evaluating the **truth, consistency, and intellectual rigor** of the content.

## What You Read

1. The entire manuscript: every manuscript file in the order the run gives you, plus the bibliography
2. Stage 1 output: `stage-1-map.md` and all files in `artifacts/`, including `citation-report.md` and `glossary-report.md`

Read the manuscript fresh, cover to cover. Use Stage 1's extraction as a reference map, but form your own judgments. If Stage 1 missed something, note it.

## What You Produce

1. **`stage-2-attack.md`** -- your comprehensive critique, organized in sections 2A through 2F as described below. Every finding has a unique ID (e.g., `A-1`, `A-2` for adversarial findings; `IC-1`, `IC-2` for internal consistency; etc.) so Stage 3 can reference them.

   **Start every finding with its own heading, `#### <ID>: <the claim in one line>`.** A script reads these headings to match each finding against the book's decisions before Stage 3, so a finding written without one is never matched.

2. **Updated artifact file:** `artifacts/mainstream-map.md` (populated with your field mapping from section 2E).

---

## Section 2A: Adversarial Argument Critique

Work through the claims extracted in Stage 1 (in `artifacts/claims-evidence.md`). For each major claim, apply the following tests. You don't need to address every claim -- focus on claims that are central to the book's argument, that are stated strongly, or that are potentially controversial.

**Critical: Steel-man the book's argument first.** Before generating any counterargument, read the entire section (not just the paragraph containing the claim) and state the book's full argument in its strongest form, including its own caveats, qualifications, bridging evidence, and acknowledgments. Many claims have nuances, exceptions, and self-aware limitations in adjacent paragraphs. Your counterargument must address THIS version -- the strongest version the book actually presents -- not a simplified extract. If the book already addresses your objection in the same section or a nearby section, that is not a finding. If the book partially addresses it, your finding is about the gap, not the whole objection.

### Counterarguments

For each major claim, state the strongest counterargument an informed, thoughtful skeptic would raise. Not a straw man -- the real objection that a senior practitioner of the field or an academic would make. Include:

- **Finding ID** (e.g., `A-1`)
- **Confidence**: High / Medium / Low (how certain you are this is a genuine issue)
- **The claim** (with location)
- **The book's full argument** (steel-man: the claim + its evidence + its caveats + any self-acknowledged limitations, drawn from the entire section and adjacent sections)
- **The counterargument** (the strongest version that addresses the steel-manned argument)
- **How the book handles it** (addresses it fully, addresses it partially with gap X, or ignores it)
- **Assessment**: Is the book's treatment sufficient, or does the counterargument land despite the book's handling?

### Evidence Sufficiency

For claims that rest on evidence (citations, data, examples), assess whether the evidence actually supports the claim. Grade the evidence by where it was measured, using [evidence-grades.md](evidence-grades.md): the grade says what the text may state, and a weak grade calls for different wording, not for dropping the claim. Read the full section to find ALL evidence the book provides -- authors often build evidence across multiple paragraphs, combining empirical citations with reasoning chains and bridging arguments. Assess the cumulative evidence, not just the citation attached to one sentence.

- **Finding ID**
- **The claim and ALL its evidence** (with locations -- include bridging arguments and caveats from adjacent paragraphs)
- **Assessment**: Does the cumulative evidence support the claim as stated? Is the evidence type appropriate (anecdotal used for general claims? single study used for consensus claims?)?

### Overclaiming

Flag claims where the language is stronger than the evidence warrants. Before flagging, read the entire section to check whether the author qualifies, hedges, or narrows the claim in adjacent paragraphs. If the headline claim says "always" but the next paragraph says "except when...", the finding is about the headline phrasing, not about a missing qualification.

Two overclaiming shapes that reading one paragraph at a time never shows:

- **The hedge that does not travel.** A qualification is stated once, in the chapter body. Check every place that restates the same claim with the same citation (the chapter summary, later chapters, tables) and see whether the qualification is still there. A skimming reader and a quoting reviewer take away the restatement, not the hedged original. The finding is the restatement that dropped the hedge. FP-8 still applies: a later sentence that invokes the hedged framework by its name carries the hedge with it; flag only a restatement that asserts the claim as plain fact about the world.
- **The finding moved from another field.** A result measured in one research setting (a laboratory task, another kind of reading, another population) is cited for a sentence whose subject is the book's own domain. First look for a transfer policy the book states once, usually where it first borrows from that field. If the book has one and the sentence stays inside it, a hedge on every sentence is not owed: this is not a finding. Flag the sentence only when no policy exists or the sentence goes beyond it.

- **Finding ID**
- **The claim as stated** (with location)
- **The claim as qualified** (include any caveats from the surrounding text)
- **What the evidence actually supports** (a weaker version of the claim)
- **The gap** between the qualified claim and what's supported (this may be smaller than the gap from the headline claim)

### Underclaiming

Flag cases where the book has stronger evidence than the claim it makes -- missed opportunities to make a more powerful point:

- **Finding ID**
- **The claim** (with location)
- **What the evidence could support** (a stronger version)

### Reasoning Chain Validation

Major arguments in a book are not single claims -- they are chains where each step builds on the previous to reach a conclusion. Evidence Sufficiency checks whether the conclusion has support. This section checks whether each link in the chain holds.

For each major argument (the book's central theses and the key arguments within each chapter), trace the reasoning chain step by step:

1. **Map the chain**: List the steps from premise to conclusion as the book presents them (e.g., "A, therefore B, therefore C, therefore D")
2. **Test each link**: Does each step follow from the previous? Or is there a leap where the reader must accept a connection without evidence or reasoning?
3. **Identify the weakest link**: Which transition in the chain is least supported?

Types of chain breaks to watch for:

- **Unstated assumption**: The chain requires a premise that is never made explicit. The argument works only if the reader already believes X, but X is never stated or defended.
- **Scale leap**: A principle demonstrated at one scale (one household, one classroom) is applied at another scale (a city, a school system) without arguing that it transfers.
- **Domain leap**: Evidence from one domain (for example, studies of rats in a lab) is applied to another (the people the book advises) without bridging the gap.
- **Correlation-to-prescription leap**: Observing that good work has property X, then prescribing "therefore do X" without showing that doing X causes the work to be good.
- **Missing intermediate step**: Steps A and C are established, but B (the connection between them) is assumed rather than argued.
- **Paradigm/level gap**: A principle demonstrated in one school or method, or at one scale, is assumed to transfer to another school or scale without bridging argument. The mechanism may indeed transfer, but the book doesn't show that it does -- the reader must take it on faith. Example: a cooking book shows why a sauce splits when fat is added too fast, then never says whether the same rule holds for an emulsion made by machine, although its own explanation covers both.
- **Splice**: Two bodies of evidence that never studied the same thing are joined, one supplying the categories and the other the cost or effect, and the join itself is never evidenced. Agreement between traditions with no shared object is not triangulation. Ask for the join before judging the endpoints.
- **Multiplied figure**: A number is derived by multiplying two factors, and neither factor is supported for this use. A transparent derivation of a number is not evidence for it.
- **Rival unit mistaken for missing support**: A rival framework counts or defines the unit differently from the book. That is a disagreement to report as such, not proof that the book's claim is unsupported.

For each finding:

- **Finding ID**
- **The chain** (premise → step → step → conclusion, with locations)
- **The break** (which link fails and why)
- **Severity**: Does the break undermine the conclusion, or is the conclusion still defensible through a different path?

Focus on the book's load-bearing arguments -- the chains that support central claims. Minor supporting arguments with small gaps are not worth flagging unless the gap is a pattern.

### Logical Fallacy Scan

Systematically scan for these fallacies. Only flag genuine instances, not borderline cases. For each finding:

- **Finding ID**
- **Fallacy type**
- **Location**
- **The argument as stated**
- **Why it's fallacious**

Fallacies to check:

- **Appeal to authority without evidence**: Citing a respected name as proof, without the actual reasoning or evidence that name relies on. (Note: citing an authority alongside their evidence is fine -- that's not a fallacy.)
- **False dichotomy**: Presenting only two options when more exist.
- **Cherry-picking**: Citing evidence that supports the position while ignoring well-known contradictory evidence. The test is whether a knowledgeable reader would immediately think "but what about X?"
- **Survivorship bias**: Drawing conclusions from successes without considering failures that followed the same approach.
- **Correlation-as-causation**: Claiming X causes Y based on co-occurrence.
- **Circular reasoning**: Using the conclusion as a premise, even implicitly.
- **Hasty generalization**: Drawing broad conclusions from too few examples or too narrow a context.
- **Equivocation**: Using the same term with different meanings at different points in an argument, making the argument appear to hold when the meaning shift actually breaks it.
- **Moving goalposts**: Changing the criteria for success or the definition of a concept between chapters to make the argument work.
- **Straw man**: Weakening an opposing position before refuting it. The test: would a proponent of that position recognize the description as fair?
- **False consensus**: "Everyone agrees...", "It's widely accepted...", "No serious practitioner would..." -- claims of agreement that may not reflect reality.
- **Slippery slope without mechanism**: Claiming A leads to B leads to C without explaining the causal mechanism at each step.

### Alternative Explanations

Evidence Sufficiency checks whether evidence supports the claim. This section checks whether the same evidence could equally support a *different* conclusion that the book doesn't consider.

For key pieces of evidence (empirical studies, historical patterns, examples):
- **Finding ID** (use prefix `AE-`)
- **The evidence** (with location)
- **The book's conclusion** from this evidence
- **The alternative conclusion** the same evidence could support
- **Whether the book acknowledges the alternative** (and if so, why it prefers its interpretation)

Focus on cases where the alternative explanation is credible and well-known, not contrived. The test: would a knowledgeable reader think "but couldn't this also mean...?"

### Book-Level Confirmation Bias

Individual cherry-picking (addressed in the Logical Fallacy Scan) is per-claim: one claim ignores one piece of contradictory evidence. This section checks for a *pattern* across the whole book.

- Does the book systematically favor evidence from certain authors, schools of thought, or traditions while underrepresenting others?
- Does the book cite studies that support its thesis but omit well-known studies that challenge it?
- When the book discusses the debates of its field, does it give both sides proportional treatment, or does the "losing" side get less space, weaker evidence, or less charitable framing?
- Are there entire bodies of relevant evidence the book never engages with?

This is not about individual claims but about the book's overall evidence diet. A book that cites 20 sources supporting its view and 2 opposing is exhibiting confirmation bias even if no single claim cherry-picks.

For each finding:
- **Finding ID** (use prefix `CB-`)
- **The pattern** (what's systematically favored or underrepresented)
- **Evidence of the pattern** (multiple locations showing the same bias direction)
- **What's missing** (the underrepresented evidence, authors, or perspectives)

---

## Section 2B: Internal Consistency

This section looks for the book contradicting itself. Use Stage 1's extraction as your map, but read the text yourself to verify.

### Cross-Chapter Contradictions

Identify claims in one chapter that contradict claims in another:

- **Finding ID** (e.g., `IC-1`)
- **Claim A** (with location)
- **Claim B** (with location)
- **The contradiction**: Why these can't both be true, or how they create confusion even if technically compatible

### Definition Drift

Using the definitions index from Stage 1, check whether each term maintains consistent meaning across all its uses.

The `artifacts/glossary-report.md` file contains the mechanical output of `glossary-check.py` against the book's curated glossary: first-use vs first-defined chapter (pre-introduction flags), per-chapter distribution, total occurrences, and each term's canonical definition and invariants. Use it as the starting list of terms to scrutinize -- skip the mechanical extraction and focus on:

- Pre-introduction flags: is the early occurrence actually using the defined sense, or a generic English sense? Most flags are deliberate forward references; report one only when the early use confuses the reader.
- Never-found terms: usually the glossary heading does not match the form the book uses, not a term the book dropped. Search for the concept before reporting it missing.
- High-count terms: do later uses preserve the canonical definition, or drift?
- Cross-chapter occurrences that the registry entry's invariants would rule out.

If the glossary report is empty or missing (registry not yet curated), fall back to re-extracting definitions from the manuscript.

For each drift finding:

- **Finding ID**
- **The term**
- **Definition at introduction** (with location)
- **Changed usage** (with location)
- **The drift**: How the meaning shifted

### Naming Inconsistency

- Same concept referred to by different names in different places
- Different concepts referred to by the same name
- For each: the concept(s), the name(s), the locations, and the confusion this creates

### Fact Consistency

When the same fact, number, date, or claim appears in multiple places:
- Are all instances consistent?
- If they differ, which is correct?

### Example-Principle Consistency

Do the book's own examples actually demonstrate what they claim to?

- **Finding ID**
- **The example** (with location)
- **The principle it claims to illustrate**
- **The problem**: How the example contradicts or fails to support the principle

### Self-Following

Does the book follow its own advice? This is a powerful test of intellectual honesty:

- If the book advocates for simplicity, is the book itself simple?
- If it advocates for accurate naming, are its own chapter and section titles accurate?
- If it teaches a rule about structure, does its own structure follow that rule?
- If it teaches a rule about consistency, is each chapter consistent in the same sense?
- If it advocates against redundancy, does it avoid its own redundancy?

For each violation:
- **Finding ID**
- **The advice the book gives** (with location)
- **How the book violates it** (with location)
- **Severity**: How visible this would be to an attentive reader

### Standards Consistency

Does the book apply the same standards to everything, or does it give certain approaches special treatment?

- Praised approaches evaluated only on strengths, while criticized approaches evaluated only on weaknesses?
- Exceptions carved out for preferred patterns that wouldn't be granted to others?
- Different evidence thresholds for favored vs. disfavored positions?

---

## Section 2C: Fact and Citation Verification

Verify everything you can verify from the text itself and general knowledge. You cannot check primary sources directly, but you can flag claims that don't match established knowledge.

### Attribution Accuracy

For each citation in the citations index:
- Is it attributed to the correct person?
- Is the work title correct?
- Is the date/year plausible?
- Flag any that seem wrong or uncertain, with your reasoning

### Quote Plausibility

For direct quotes:
- Does the quote sound plausible as something this person would say?
- Flag any that seem like paraphrases presented as quotes
- Flag any where the surrounding context might misrepresent the quote's meaning

### Historical and Date Accuracy

For historical claims:
- Are dates correct?
- Are historical sequences in the right order?
- Are causal claims about history defensible?
- Flag anachronisms (attributing ideas to people before those ideas existed)

### "First" and Priority Claims

For any claim that someone was "first" to do something, or that something "originated" with a specific person/paper:
- Is this defensible?
- Are there earlier prior art that the book doesn't acknowledge?

### Citation-Claim Alignment

For each citation, does the cited source actually support the claim it's attached to? Flag cases where:
- The citation is tangential to the claim
- The cited author would likely disagree with how their work is used
- The citation supports a weaker version of the claim than the text states

### Missing Citations

Are there claims that need citations but don't have them? Specifically:
- Empirical claims (statistics, measurements, study results) without sources
- Claims about what specific people said or believe without attribution
- Historical claims without references

### Bibliography Completeness

The `artifacts/citation-report.md` file contains automated cross-matching of citations vs bibliography (`citation-check.py`). Use it directly -- do not repeat the mechanical matching. Instead, focus on what the script cannot check:

- For citations flagged as "cited but missing": is this a real key or a formatting artifact?
- For "single-use citations": do any of these support major claims that would benefit from additional sourcing?
- For density outliers: do low-density chapters make claims that need better grounding?
- Are there claims that need citations but have none? (The script finds orphaned keys, not missing citations)

---

## Section 2D: Technical Accuracy

Review every technical claim as a senior practitioner of the book's field would. For a book without technical content, keep Correctness, Currency, Universality, Missing Caveats and Trade-off Honesty, and apply Worked Example Quality to its cases, calculations and procedures.

### Correctness

Flag technical claims that are:
- **Wrong**: Factually incorrect by current understanding
- **Outdated**: Were once correct but no longer (with what changed)
- **Misleading oversimplification**: Simplified to the point of being incorrect (with what nuance is lost)

For each:
- **Finding ID** (e.g., `T-1`)
- **Confidence**: High / Medium / Low
- **The claim** (with location)
- **The problem**
- **What's actually correct**

### Currency

- Are patterns or practices described as current that are actually deprecated or fallen out of favor?
- Are version-specific claims clearly labeled?
- Would a practitioner today recognize the described practices?

### Universality

Flag claims presented as universal that are actually specific to:
- A particular tool, language, product or ecosystem
- A particular kind of setting (in a farming book: wet or dry climate, small or large farm)
- A particular scale (a small team vs. a large organization)
- A particular methodology or culture
- A particular school or paradigm -- mechanisms illustrated only with one school's examples when the argument applies equally to another school, or vice versa
- A particular level -- diagnostics or decision frameworks that work at one level the book teaches but are missing at other levels it also gives advice for. If the book gives advice at a level without providing the diagnostic to act on it, that's a universality gap.
- A particular scope -- principles claimed to hold from the smallest case to the largest but demonstrated only at some sizes

### Missing Caveats

For technical recommendations, what important caveats are missing?
- Contexts where the advice would fail
- Trade-offs not mentioned
- Prerequisites not stated

### Worked Example Quality

For code examples, pseudocode, calculations, recipes and procedures:
- Is the example correct? For code: would it compile and run, and is it idiomatic for the language?
- Does it demonstrate best practice for its field?
- Would a practitioner use it, or is it a teaching simplification that wouldn't work for real?
- Are there errors, anti-patterns, or safety issues?
- Does it follow the book's own rules? An example that breaks a rule a later chapter teaches is a finding.

### Trade-off Honesty

For each recommended approach or pattern:
- Are the downsides presented?
- Are the costs acknowledged?
- Or is it presented as purely beneficial?

### Technology and Paradigm Bias

Does the book systematically favor certain technologies, paradigms, or approaches without acknowledging viable alternatives?
- The bias (with evidence from multiple locations)
- What alternatives are underrepresented
- Whether the bias is acknowledged or invisible

---

## Section 2E: Mainstream Field Mapping and Fair Representation

### Mainstream Mapping

For every stance extracted in Stage 1 (see `artifacts/stances.md`), map it against mainstream thinking in the field. Produce a structured assessment:

- **Stance ID** (from Stage 1)
- **The book's position** (briefly)
- **Mainstream position** (what the majority of respected practitioners/authors say)
- **Alignment**: One of:
  - **Agrees** -- book aligns with mainstream
  - **Partial divergence** -- book agrees with some aspects, diverges on others
  - **Strong divergence** -- book takes a clearly different position from mainstream
  - **Novel** -- book proposes something that mainstream hasn't addressed
- **Divergence acknowledged?** Does the book acknowledge where it departs from mainstream? (yes/no/partially)
- **Key dissenters**: If the book's position is controversial, who are the notable voices who would disagree?

Write this as a structured table in `artifacts/mainstream-map.md`:

```markdown
| Stance ID | Book's Position | Mainstream Position | Alignment | Acknowledged? | Key Dissenters |
|-----------|----------------|--------------------|-----------|--------------:|----------------|
| S1 | [position] | [mainstream] | [alignment] | [yes/no/partial] | [who] |
```

### Fair Representation of Other Authors

When the book discusses, cites, or positions itself against other authors:
- Are their positions represented accurately?
- Would those authors recognize the description of their ideas?
- Are the strongest versions of their arguments addressed (steelman), or weakened versions (straw man)?

For each finding:
- **Finding ID** (e.g., `FR-1`)
- **The author and their position as described in the book** (with location)
- **What that author actually argues** (the steelman version)
- **The gap** (if any)

### Intellectual Genealogy

For ideas the book presents:
- Is the lineage clear? Can the reader trace ideas back to their origins?
- Are there ideas that appear to be original but are actually well-established (uncredited borrowing)?
- Are there ideas where credit is given to the wrong originator?
- When the book synthesizes ideas from multiple sources, is the synthesis attributed as such?

### Missing Voices

Are there important authors, perspectives, or schools of thought in the book's domain that are conspicuously absent?
- The missing perspective
- Why a reader in this field would expect to see it
- Whether the omission weakens the book's argument

**Guard against scope projection.** Before flagging "the book doesn't engage with [Author]'s [Concept]," apply this test:

1. Does the book claim to resolve the debate where that concept is relevant?
2. Does the book name the author or the concept in the context of that debate?
3. Does the book's argument depend on defeating that concept, or does it stand on independent grounds?
4. Would the missing concept align with the book's stated positions, or would it contradict them? If it contradicts, the omission is likely a deliberate stance, not an oversight.

If the argument stands without the omitted material and the book never claims the territory, the omission is a scope choice, not a gap. Citing an author for concept A does not obligate engagement with that author's concept B -- especially when concept B contradicts the book's positions. Flagging the book for not participating in a debate it never enters, or for not adopting ideas it implicitly rejects, is scope projection.

### Comparative Fairness

When the book compares approaches (two methods, two schools, two tools):
- Is the comparison balanced?
- Are both sides evaluated on the same criteria?
- Does the "losing" side get its best argument represented?

---

## Section 2F: Demonstrated-but-Unstated Rules

The book may teach rules through example repetition without ever stating them in prose. A reader copying patterns from examples learns the rule implicitly, but a reader reading prose misses it -- and worse, a reader who notices the pattern has no confirmation that it is intentional. This pass surfaces rule-shaped regularities the book enforces silently.

### What to Scan

Identify rule-shaped patterns the book repeatedly demonstrates but never names:

1. **Examples.** Do they share characteristics (realistic data, a consistent order, specific naming conventions, one recurring style of handling errors or edge cases) that are not mentioned in prose?
2. **Explanations.** Do they follow a template (define -> show -> detect -> fix -> principle -> trade-off) that is never stated as a teaching rule?
3. **Transitions and summaries.** Do they use recurring framings, sentence patterns, or closing moves that are never identified as techniques?

### What to Flag

For each demonstrated-but-unstated rule, record:

- **Finding ID:** `DU-N` (e.g., `DU-1`, `DU-2`) -- matches the Stage 2 prefix convention (A-, IC-, AE-, CB-, etc.)
- **Confidence:** High / Medium / Low
- **What the book consistently demonstrates** (one sentence)
- **Where:** at least 3 instances with file:section references
- **What the prose would need to say** to make the rule explicit (proposed sentence)
- **Recommendation:** state the rule in prose, or restructure examples so the rule is not implied

### Why this matters

Readers learn as much from examples as from prose. When the book teaches one thing in prose and demonstrates another consistent-but-unstated thing in examples, the examples win the reader's attention. A rule demonstrated but never named leaves the reader with a pattern they can copy but not verify, and no way to know whether the pattern is intentional teaching or incidental authorial habit.

---

## Sections That Survived

At the end of your review, list the chapters or major sections that survived your scrutiny with no significant findings. For each:

- The chapter/section
- A one-line note on why it's solid (e.g., "well-evidenced, acknowledges trade-offs, no consistency issues")

Stage 3 uses this as a signal of strength. Silence is ambiguous -- explicit acknowledgment is clear.

---

## Guidelines for This Stage

- **Steel-man before you attack.** For every claim you plan to challenge, first state the book's full argument in its strongest form -- including caveats, qualifications, and bridging evidence from surrounding paragraphs. Then attack THAT version. A finding that ignores the book's own handling of the objection is a wasted finding. If the book says "X" in paragraph 3 and "except when Y" in paragraph 5, your finding is about the gap between the qualified claim and the evidence, not about the unqualified claim.
- **Be the strongest critic, not the meanest one.** Your findings should be the kind that a thoughtful, senior reviewer would raise -- not nitpicks designed to show off. Every finding should matter.
- **Use confidence levels.** Mark each finding as High confidence ("this date is wrong"), Medium ("this likely misattributes the idea"), or Low ("this might be an issue but I'm not certain"). Stage 3 uses confidence for triage.
- **Finding IDs are critical.** Stage 3 will reference your findings by ID. Use consistent prefixes for every finding across all sections: `A-` for adversarial (2A), `RC-` for reasoning chain (2A), `AE-` for alternative explanations (2A), `CB-` for confirmation bias (2A), `IC-` for internal consistency (2B), `FC-` for fact/citation (2C), `T-` for technical (2D), `FR-` for fair representation (2E), `MM-` for mainstream mapping (2E), `DU-` for demonstrated-but-unstated rules (2F). Each finding opens with its `#### <ID>: ...` heading.
- **Don't attack writing quality.** "This paragraph is confusing" is not your concern. "This paragraph claims X but the evidence supports Y" is.
- **Guard against scope projection.** Your knowledge of the field will suggest topics the book "should" cover. Before flagging any omission, verify that the book actually claims to cover that territory. A book that settles a question through its own framework has no obligation to engage with every other framework that addresses the same question. A book that cites an author for one idea is not obligated to engage with that author's other ideas. The test: does the book's argument depend on the omitted material, or does it stand on its own terms? If it stands on its own, the omission is a scope choice, not a gap.
- **Don't attack the book's right to take positions.** The book is allowed to disagree with mainstream. Your job is to verify that (a) it represents the mainstream accurately before disagreeing, (b) it acknowledges the disagreement, and (c) its reasoning for diverging is sound.
- **Run FP screens BEFORE reporting any finding.** [false-positives.md](false-positives.md) lists the false-positive patterns (FP-1 through FP-12). They apply at Stage 2 exactly as at Stage 3. For every finding you plan to report, run it against every pattern that can apply before the decisions are matched (FP-11 is applied after you, by a script and Stage 3) and discard any finding that fails any screen. Do not report a finding and rely on Stage 3 to triage it -- that wastes Stage 3's attention and produces noise the user must filter manually. The most common false-positive pattern is by far FP-4 (the unit that governs the flagged text -- paragraph, citation list, the prose owning a listing, or a book-wide vocabulary ruling -- went unread); FP-9 is also frequent (the synthesis chapter explicitly commits to the position the finding attacks).
- **Three-location check for "missing X" or "overclaim Y" findings.** Before flagging any finding of the form "the book doesn't address X" or "the book overclaims Y," explicitly search (a) the chapter's summary section (its heading is set by `manuscript.summary_heading`; the run tells you), (b) the preface, (c) the synthesis chapter (typically the final chapter or the Part wrap-ups). If the qualifier exists in any of these locations, the finding is NOISE and should not be reported. State which locations you checked.
- **Quality of findings matters more than volume.** A 50-finding report with 90% VALID hits is more useful than a 200-finding report with 10% VALID hits, because the user must evaluate every finding you report. Report only findings that survive steel-manning AND all FP screens AND the three-location check. Skipping FP-failed findings is not "truncation" -- it is the standard you are asked to meet.
- **Read all files before writing.** Read the entire manuscript and all Stage 1 output before producing any findings.
