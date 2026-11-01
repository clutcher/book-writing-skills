# The rules, explained

This is the full text behind each one-liner in the Rules Summary of `SKILL.md`: the reasoning,
worked examples, anti-patterns and tests. Each rule keeps its number, so "Rule 4.2" in a
workflow points to both its one-liner and its section here. The word-level lookup tables
(plain vocabulary, ASCII) and the preferred patterns are at the end.

Some rules are the author's choices rather than general truths: sentence and paragraph
length, fronted inversions, punctuation habits, the use of "I", "you" and "we". Those rules say
**per the voice profile**. The voice profile is the book's `rules.voice` file, or the skill's
`profiles/default.md` when the book has none (`profiles/paper-voice.md` for a paper). Read it before applying such a rule: the rule
gives the goal, the profile gives the form and the numbers.

### 1. Structure

The writing follows a single recursive pattern at every level: chapter, section, paragraph, and sentence.

**1.1. Every unit follows Topic -> Develop -> Conclude.**

| Level | Topic Is | Topic Is NOT |
|-------|----------|--------------|
| Chapter | Question or problem to explore | The answer to that question |
| Section | Single point to develop | The conclusion of that point |
| Paragraph | What this paragraph addresses | The final synthesis |

**Cognitive basis:** This pattern implements schema formation, the brain's process of building coherent mental models. Working memory is limited, so a reader builds a new model more easily from one main idea than from several at once; each unit should build one primary idea with supporting elements. The Topic enables prediction about what comes next, Development builds understanding through reasoning, and Conclusion consolidates it.

**1.2. Apply the pattern at every level: chapter, section, paragraph, sentence.**

The same Topic -> Develop -> Conclude structure applies recursively. A chapter contains sections that each follow the pattern. A section contains paragraphs that each follow the pattern. This creates consistent, predictable structure throughout.

This fractal application extends to book-level structure: Parts follow the pattern, the book as a whole follows the pattern. Section 6 shows how this creates levels of detail in the book hierarchy, with the full table of how the pattern manifests at each level from book to paragraph.

**1.3. Topic frames the question the unit answers; transitions end with insight that leads to the next topic.**

**Example:** "What makes a good topic sentence? This paragraph explores that question. The topic frames the exploration, which means the reader knows what to expect before the development begins."

**Cognitive basis for topic framing.** Cognitive science shows that front-loading aids comprehension: a topic sentence activates relevant schemas before details arrive. The T-D-C pattern uses this through topic framing, where the opening names what to explore so the reader's prediction mechanism engages with the development. The critical distinction is between framing the question (which activates prediction) and stating the answer (which satisfies prediction before development begins). When the answer arrives first, every development sentence competes with an already-formed conclusion, which makes development read as restatement rather than discovery. Topic framing gives the reader a direction; answer front-loading gives the reader a destination that makes the journey feel redundant.

**Section openings pose questions.** A section opening frames what the section explores, so the reader follows the development toward a conclusion they discover. "What does a rain barrel save when the summer turns dry, and do the savings from the last section still hold?" poses the question. "This section establishes that a dry summer erases most of the savings" gives the answer before the development earns it.

**Section transitions end with insight.** The last sentence of a section ends with an insight that makes the reader curious about what comes next. "Every hot day now has a second job: telling the gardener the barrel is empty" leads naturally into a section about watering by hand. "The next subsection shows how watering by hand adds another cost" describes the next section's content mechanically.

**Evidence earns the naming.** When a section builds a new concept (Rule 2.5), the evidence that demonstrates the concept must precede the naming. Evidence includes worked examples, reasoning chains, analogies, or historical examples. The reader encounters the puzzle first: something varies, something feels different, something doesn't work as expected. Then the evidence shows the phenomenon. Only after the evidence does the text name the cause, mechanism, or structural property. This prevents Root Cause A (front-loading -> restatement), because the development has somewhere to go: toward the naming that the evidence earns.

When the concept is already known to the reader (Rule 2.6), the section can name it upfront and develop implications instead. The distinction follows Rules 2.5 and 2.6: new concepts need evidence before naming, known concepts can be named as context for a new question.

Example (premature): "The tiredness comes from low iron" before the blood tests that show it. The naming arrives before the evidence, so the evidence feels redundant.

Example (earned): "Sleeping longer helped some patients and did nothing for others" before the blood tests. After them: "Every patient whom sleep did not help had low iron, which is why more rest could not fix their tiredness." The evidence earns the naming.

**1.4. Develop explains WHY through reasoning.**

The Develop phase must explain WHY through reasoning. Examples become development when they include explanation. Walk the reader through reasoning so the conclusion follows logically. The reader should think "yes, that follows" not "where did that come from?"

**Example:** "Why does development require reasoning? Because examples alone show WHAT but leave WHY unexplained. When you walk through the mechanism, the reader thinks 'yes, that follows' and the conclusion feels earned."

**1.5. Conclude synthesizes by connecting ideas across sections into a whole (reader should anticipate it).**

The conclusion should feel inevitable after the development. If the reader is surprised by the conclusion, the development was insufficient.

**Summary synthesis connects ideas across sections.** A summary shows how ideas from different sections form a whole the reader hasn't seen before. Each summary sentence draws from multiple sections rather than replaying one. Test: if each summary sentence maps to exactly one section, the summary recapitulates rather than synthesizes.

**Example (synthesis):** "Salt slows the yeast, time lets the dough build strength, and the balance between the two decides how long a loaf must rest before it goes into the oven." The sentence connects concepts introduced in different sections.

**Example (recapitulation):** P1 restates the definition, P2 restates the mechanism, P3 restates the costs. Each paragraph replays one section's conclusion in order.

---

### 2. Narration Flow

The narration follows a mathematical proof style: smooth, uninterrupted, with each idea building on prior ideas.

**2.1. Maintain smooth uninterrupted flow; restructure to explain context first.**

Ideas and sentences connect smoothly in a straight line. Restructure to explain context before the main point; this keeps flow uninterrupted.

**2.2. Each sentence builds from the previous and sets up the next; each paragraph builds from the previous and sets up the next. Vary connection techniques.**

Every sentence takes what the previous sentence established and advances it, while ending with something the next sentence can build from. Every paragraph takes the previous paragraph's conclusion and builds from it, while its own conclusion sets up the next paragraph. This creates a chain where each link connects in both directions.

**"Builds from" means advancement, not restatement.** A sentence builds from the previous when it adds understanding the previous did not contain. A connector like "which" or "because" can link a restatement just as easily as an advancement, so connectors alone do not satisfy this rule. Test: state what NEW understanding each sentence adds beyond the previous.

**Anti-pattern: restatement disguised as building.**

Wrong (three sentences saying the same thing):
"A cold oven slows every loaf. This slowness hurts the bake, which makes the morning feel long. Because the oven is cold, the bread takes longer."

Each sentence restates "cold oven -> slow." Connectors create the appearance of flow, but no sentence advances beyond the first.

Right (three sentences building):
"A cold oven slows every loaf. Because the crust sets late, the dough keeps spreading, so each tray needs more time and more space. The slowest tray sets the pace of the whole morning, which means the baker plans for the worst tray rather than the average one."

S1 states the slowdown. S2 adds what the late crust does to each tray. S3 adds whose pace sets the morning and what that means for the baker. Each sentence advances.

**Anti-pattern: implicit jump (advancement without bridge).**

A sentence can advance yet still feel disconnected because it does not show HOW it connects to the previous sentence. Advancement alone does not satisfy this rule. The connection must be visible.

Wrong (advances but jumps):
"Rule 2.2 requires each sentence to build from the previous. The reader follows the progression without stopping."

S2 advances (adds what happens when building works). But nothing shows why building causes smooth progression, so the reader must infer the link.

Right (advances with explicit bridge):
"Rule 2.2 requires each sentence to build from the previous. Because each sentence connects to what came before, the reader follows the progression without stopping."

S2 advances AND shows the causal link: connecting to what came before is the reason progression feels smooth.

**Bridge test.** For each sentence, check two things: (1) does it add new understanding? (Rule 2.13) and (2) does it explicitly show its relationship to the previous sentence? Both must hold. A sentence that advances without a visible bridge creates an implicit jump the reader must fill.

**Paragraph-level bridge.** The first sentence of each paragraph must explicitly connect to the previous paragraph's conclusion. This rule applies with the same force as sentence-level bridging. Conceptual continuation (starting the next idea without an explicit link) is allowed only when two paragraphs develop the same idea within the same section and the connection is unmistakable.

Wrong (paragraph jump):
"...which means the reader holds the purpose longer. [new paragraph] Topic sentences frame what the paragraph addresses."

The new paragraph advances to a new concept, but nothing bridges from "holding purpose" to "topic sentences."

Right (paragraph bridge):
"...which means the reader holds the purpose longer. [new paragraph] Topic sentences protect this effect, because they tell the reader what to hold before details arrive."

The bridge shows how topic sentences connect to the conclusion about holding purpose.

**Connection techniques (examples):**
- **Transition:** Explicitly reference the previous content ("This limit has consequences...")
- **Signposting:** Announce structure ("Three factors contribute...")
- **Conceptual continuation:** Start with the next idea when connection is obvious from content
- **Build on conclusion:** Use previous conclusion as starting point
- **Question:** Open with a question the unit answers
- **Contrast:** "While X..., Y..."

Other techniques that create clear connection are valid.

**Example transitions:**
- "Drought drives the next problem: smaller harvests."
- "This limit has practical consequences."
- "What happens when these safeguards fail?"
- "While interest is added automatically, its cost lands on the people who borrow."

Vary techniques across units. Avoid starting consecutive sections with "The previous section..."

**Verification: chain table.** After drafting, build a table that traces each sentence's contribution and connection:

| # | Sentence (shortened) | New understanding | Connector from previous |
|---|---|---|---|
| 1 | A savings account keeps money safe | Starting point | -- |
| 2 | Its gain depends on the interest rate | Narrows to what decides the gain | "Its gain" |
| 3 | Yet a high rate can still lose value | The puzzle | "Yet" |

Four checks catch most chain problems. First, the "New understanding" column: if two adjacent rows describe the same contribution, one restates. Second, the "Connector" column: if a cell is empty, the transition lacks an explicit connector (Rule 4.2). Third, count distinct content steps across the full table: if the paragraph has more sentences than content steps, the extra sentences are filler. Fourth, the "builds from" check: does each sentence use the previous sentence's conclusion as its starting point? Shared words between adjacent sentences do not create a chain. Two sentences that reference the same concept ("Topic sentences frame the question..." / "The framing activates prediction...") but make independent claims about it are parallel, not chained. Test: remove S1 entirely. Does S2 still make sense on its own? If yes, S2 does not build from S1.

**2.3. Ideas build on prior ideas (order matters).**

Each idea develops FROM the previous idea through causal or logical connection. The order matters because rearranging would break the chain. Content must only use concepts that have already been introduced. If you reference "compound interest" in an explanation, compound interest must already be explained. If Section A uses ideas from Section B, Section B must come first. Introduce persons before referencing their work.

**Example (meta):** "This rule requires building, which means each sentence develops from the previous. The previous sentence introduced 'building,' so this sentence can now explain what building means. Because both sentences connect logically, the reader follows the progression."

**Test:** Building means the order is necessary. Each idea answers "why?" or "so what?" from the previous idea.

**2.4. Define terms before use; use the same name for the same concept across all chapters.**

Introduce and explain all terms, concepts, and people before (or as) they are used.

**Term consistency across chapters.** Once a concept has a name, use that name consistently across all chapters. When the book defines its own terms, use those terms in all subsequent references rather than switching to synonyms borrowed from another field. A defined term also keeps one word form everywhere, including slogans, summaries and boxes: a shortened form of a defined phrase is a new term the reader must reconcile. Switching between synonyms forces the reader to determine whether the terms mean the same thing or different things, which consumes working memory without advancing understanding.

**Preserving definition across uses.** When the book formally defines a term -- via a definition sentence or blockquote -- later uses must preserve that definition. If a later context genuinely needs the colloquial or different sense, either rename the concept or explicitly redefine with acknowledgment: "In this chapter I use X in the narrower sense of..." Silent drift from the defined sense erodes the book's conceptual precision and teaches the reader that definitions are decorative.

The book glossary (`rules.glossary` in `book.yaml`) is the ground truth for defined terms. The review-ideas skill seeds and maintains it; the author curates the canonical definitions. `glossary-check.py` (run by run-checks text) surfaces uses after the definition for review.

**2.5. Core concepts: explain mechanism first, then define in "X is..." format.**

For core concepts (what the book teaches), explain the mechanism first: what triggers it, what happens, what the reader would experience. Then provide a clear definition.

**Example:** "At the end of the year the bank adds interest to the balance, and the next year it pays interest on that larger balance, so the savings grow a little faster every year. *Compound interest* is interest paid on both the money saved and the interest it has already earned."

**At chapter scale, Topic-Develop-Conclude serves as term introduction.** The Topic names what we investigate without defining it, Development explains the mechanism, and Conclusion provides the definition. Naming a term as subject of investigation differs from using it in explanations. After the chapter concludes with a definition, the term can be used freely in subsequent chapters.

**Example:** A gardening book coins the term *soil memory*. The opening chapter names the term as the thing the reader will come to understand, without defining it yet, and investigates the question the term answers. The chapter develops through evidence. The conclusion states the definition. Subsequent chapters use the term freely.

**2.6. Background concepts: definition in "X is..." format suffices.**

For background concepts (prerequisites the book doesn't teach), a definition alone is sufficient.

**Example:** "An index is a list at the back of a book that shows on which pages each topic appears."

**2.7. Introduce persons before quoting them; name them per the voice profile.**

When citing an expert, establish who they are and why their opinion matters before presenting their quote or idea. Build credibility through substantive contribution to the field (expertise, work that shaped practices, principles they originated), not through employer affiliation or specific talk titles unfamiliar to the audience. The credential should answer: why does this person's opinion on this topic carry weight?

**Full name at first mention, then per the voice profile.** The first mention uses the person's full name (first name + surname). Later mentions follow the `## Names` section of the voice profile. The default profile uses the surname alone after the first mention ("Doe argues ..."), and the full name again when the person returns after a long gap, for example in a new chapter. A voice profile may instead ask for the full name on every mention.

**Do not re-state credentials.** The name may come back, but the introduction (who they are, why their opinion matters) does not. Once a person is introduced in their home chapter, later mentions name them without restating their bio. For example, an early chapter introduces an expert (say, Alex Doe) with the contribution that earns their authority on the topic at hand; a later chapter simply writes "Doe argued that ..." (or "Alex Doe argued that ..." when the voice asks for full names) with no repeated bio.

**Detection:** `scripts/person-introduction-check.py` flags a first mention without the full name or without an introduction, and credential re-introductions. The `--bare-mentions` worklist lists every bare surname with the distance since the last mention, for a book whose voice profile asks for full names on later mentions or after long gaps (full names derived from the prose, eponyms skipped).

**2.8. Develop with reasoning that explains examples.**

Examples must include explanation of WHY they demonstrate the point. The reader needs to understand the mechanism through the example.

**2.9. Ground claims with references [@Abc99].**

Support all significant claims with references, written as pandoc citations (`[@Abc99]`, `[@Abc99; @Def01, p. 12]`, narrative `@Abc99`; `citing-in-prose.md`). Every key is an entry in the book's `.bib` file (`sources.bibliography`); the build prints it in the book's citation style (`sources.citation_style`, BibTeX alpha by default). The check-facts skill owns the key and the `.bib` entry format.

**2.10. Grounding varies by section type.**

- **In introductions:** Ground abstract ideas in narrative and human experience.
- **In evidence sections:** Ground the argument in historical facts, publications, and expert quotes.
- **In conclusions:** Ground the final claims by explicitly referencing the evidence already presented.

**2.11. Every concept introduced must be used in later sections.**

A concept earns its place when later sections use it. If nothing later uses it, move it to where it is used, integrate it into a later section, or cut it. The link runs backward: the later section refers back to the concept ("the cover crop from Chapter 2"), never the early section ahead to the later one (Rule 6.3).

**2.12. Content must serve its section's topic (belongs here).**

If content serves a different section's argument, move it there.

**Example:** "This paragraph belongs in the 'content placement' section because it explains content placement. If it explained transitions instead, it would belong in section 2.2."

**2.13. Each sentence and paragraph adds new understanding; restatement is not advancement.**

Each sentence must add understanding that the previous sentence did not contain. Each paragraph must advance the argument beyond where the previous paragraph left off. New concepts are applied before the next concept arrives, so the reader grounds each idea before receiving another.

**Restatement is not advancement.** Saying the same claim in different vocabulary does not move the argument forward, even when linked with connectors. Three sentences that rephrase "overload causes difficulty" are one sentence of content with two restatements. The development phase needs three distinct steps, not one step said three ways.

**Front-loading the answer causes restatement.** Front-loading the topic is what rule 1.3 requires: it activates prediction and gives the reader direction. Front-loading the answer is different: when a paragraph or section opens with its conclusion, the development sentences have nowhere to advance. The reader already holds the answer, so each supporting sentence reads as rephrasing rather than building. The fix is to return to rule 1.3: open with the question, let development build toward the answer.

**Test for sentences:** For each sentence, state what NEW understanding it adds. If you cannot distinguish it from the previous sentence's contribution, it restates.

**Test for sections:** State what each section contributes in one sentence. Each contribution should be distinct. Sections should not be mergeable without losing development.

**2.14. Openings pose the question the unit answers; summaries synthesize across sections.**

Openings pose the question the chapter or section answers; the reader discovers the conclusion through development. Summaries synthesize by showing how ideas from different sections connect into a whole the reader hasn't seen before, then transition forward to the next chapter.

**Test for openings:** The opening names what to explore. If the opening states the conclusion, the development becomes redundant. "What does a dry summer cost?" is a question. "A dry summer erases most of the savings" is the answer.

**Test for summaries:** Each summary sentence draws from multiple sections. If each sentence maps to exactly one section, the summary recapitulates rather than synthesizes.

**2.15. Each idea has one home: arguments and examples appear once within a part.**

Within a part, when the same point appears in multiple chapters, decide which chapter owns it. The owning chapter develops the point fully; other chapters reference briefly or omit. Within a chapter, sections do not restate each other. Parts are natural boundaries because each part addresses a different theme, so cross-part duplication is less concern.

**Example (meta):** "Part 2 covers watering. The argument about when to water belongs in the chapter on soil, because that chapter explains what dry soil costs. The other chapters of Part 2 mention watering without arguing it, so the argument appears once within the part."

**Test:** Within each part, list recurring arguments and examples. Assign each to one chapter. Check that sections within each chapter contribute distinctly.

**2.16. Cite primary sources: reference the originator of an idea, not the synthesis that collected it.**

When an idea originates from research or an author, cite that primary source. Synthesis books are valid when discussing the synthesis itself, but ideas they collect should trace back to originators. This grounds claims in original research and gives credit where it belongs.

**Example:** a finding about working memory cites the researcher who measured it. A popular book that later collected the finding is cited only when the text discusses that book itself. Citing the popular book for the original finding hides where it came from.

**Test:** For each reference, ask: did this author originate the idea, or collect it from elsewhere? If collected, find and cite the originator.

**2.17. Text aligns with the book's own definitions and thesis.**

Every claim in the text must align with the book's own definitions. When the book defines a term broadly (a food book defines *fermentation* as "any change that microbes make to food"), later text uses that same scope and does not add a narrowing qualifier ("real fermentation needs ..."). When the book's thesis claims a wide reach, examples and explanations reflect that reach. Check the author's documented positions before writing claims about recommendations, because authentic experience is the source of authority.

**Test:** For each claim about a principle, verify it matches the definition given in the chapter that owns that principle. For each first-person recommendation, verify it matches the author's documented stance (`thinking.stance` in `book.yaml`).

---

### 3. Limits

**Chapter and section level:**

**3.1. Length follows from quality of ideas and argumentation.**

Chapters and sections are as long as they need to be to develop their ideas properly. Focus on the quality of reasoning and completeness of the argument, not word count.

**3.2. 1-3 main ideas per section.**

Working memory is limited, so a reader can follow one main idea, or at most a few, through a section; each section should build one primary idea with supporting elements.

**Paragraph level:**

**3.3. 1 idea per paragraph; sentences chain so each advances from where the previous left off.**

Each paragraph contains exactly one idea. Sentences develop that idea by chaining: each sentence takes what the previous established and advances it. The supporting arguments within a paragraph must build sequentially, not cluster in parallel around the central claim.

**What counts as an idea vs supporting content:**
- **Idea:** The main point or claim the paragraph develops
- **Supporting content:** Arguments, evidence, examples, and illustrations that develop the idea

A paragraph with one idea + multiple supporting arguments is correct. A paragraph with two distinct ideas should be split.

**Chaining vs parallel arguments.** When a paragraph has multiple supporting arguments, each should follow from the previous rather than standing independently.

Wrong (parallel): "Mulch keeps soil moist. It also stops weeds. It also feeds the soil."

Right (chaining): "Mulch keeps soil moist because it shades the ground from the sun. Shaded ground gives weed seeds too little light to grow, and as the mulch rots it feeds the soil it was protecting, so one layer does three jobs."

**3.4. Paragraph length per the voice profile.**

Develop a single cohesive idea across the number of sentences the voice profile sets (`paragraph_min_sentences` to `paragraph_max_sentences`; the default profile says 3-8). Maintain linear progression, moving forward through the idea. A paragraph far under the range is usually an idea that is not developed yet, or a fragment of a neighbouring idea; one far over it usually holds two ideas.

Supporting matter is exempt from paragraph length: a bibliography, an acknowledgments page, and the overview on a Part divider page. A Part overview is an advance organizer, a frame the reader carries across the whole Part, and works by staying short (two to four sentences). The check exempts these by file shape and by the book's references path; `writing.paragraph_length_exempt` in `book.yaml` replaces the default list.

**3.5. Ground abstract paragraphs with concrete example or reader experience.**

When a paragraph contains abstract concepts, include at least one concrete reference: a worked example, reader experience ("When you read..."), or familiar metaphor.

**Example:** "This rule ensures that abstract ideas connect to something tangible, which helps the reader build a mental model instead of processing words without meaning."

**Sentence level:**

**3.6. Sentence length per the voice profile.**

Sentences stay inside the range the voice profile sets (`sentence_min_words` to `sentence_max_words`; the default profile says 10-25). Longer sentences (up to `sentence_review_above`, 40 by default) work for extended logical sequences when connected prose structure (right-branching clauses, explicit connectors) keeps them clear. Treat the minimum as a floor, not an average to hover around: a shorter sentence is fixed by joining it with a related idea or by adding the reasoning behind it.

A small set of exclusions may run shorter: a teaching question ending in "?", an introductory phrase ending in ":" that leads into an example or list, or a level description such as "At the high level: ...". The set is deliberately narrow. A short sentence qualifies only when it is one of these, never because short prose reads well in the moment.

The tolerance for out-of-range sentences (`sentence_target_share`) is measured over a chapter or at most a section, not a paragraph. It is the room the exclusions occupy across a chapter, not a budget to spend locally.

**Cognitive constraints:**

**3.7. ~4 items trackable simultaneously.**

Working memory holds about four items at once (Cowan 2001). A sentence or paragraph that asks the reader to hold more open at the same time loses one of them. See `why-the-rules-work.md`.

**3.8. At most one level of self-embedding.**

A clause placed inside another clause ("The plan [that the council [that runs the town] wrote] failed") is self-embedding. In English, one level is no harder to understand than none, and comprehension breaks down at two (Miller and Isard 1964; Gibson 1998). Keep at most one level: move the inner clause to the end of the sentence or into a sentence of its own. This figure is about sentences only; no depth limit for lists follows from it.

**Coined terminology density** (research and method in `coined-terms.md`):

**3.9. Each coined word family needs 10-15 learning encounters in the first 2-3 chapters, then ~1 per 10,000 words for maintenance.**

A word family is a base word plus its inflected and derived forms (Bauer & Nation 1993). A coined adjective and its noun form are one family; a coined term and its antonym are two separate families, each needing its own threshold. This skill counts transparent collocations (the coined adjective plus an ordinary noun) toward the base term, not as separate terms to learn.

The distribution follows **front-loading with expanding intervals** (Mace 1932, Bloom & Shuell 1981): dense at introduction, increasingly spaced afterward. This is not even distribution. Learning-phase chapters (where the term is defined and reinforced) should be dense; maintenance chapters (where the term is applied to other material) should be sparse.

When a chapter introduces a genuinely new meaning layer for an existing term (polysemy), it needs more density than pure maintenance but less than the original learning phase. The polysemy advantage (Rodd et al. 2004) means related senses reinforce each other, but each new sense is stored distinctly (Klein & Murphy 2001) and requires learning encounters.

Run `term-density-check.py` to check current state. Use `--phases` to see per-phase assessment.

**3.10. Max 2 mentions of same term per paragraph.**

After the learning phase, each paragraph should contain at most 2 mentions of the same coined term. More creates formulaic-feeling prose where the reader perceives repetition rather than content. **Exception:** Definition paragraphs in the learning phase (first introduction of the term) may naturally need 3-4 mentions to establish the form-meaning connection.

**3.11. Antonym pairs in the same paragraph cause interference during the learning phase.**

Presenting semantically related words together hinders retention (Tinkham 1993, Waring 1997). The effect is strongest when related items are introduced simultaneously. After the learning phase (once both terms are established, typically after 2-3 chapters), co-occurrence reinforces rather than interferes. Ping-ponging between antonyms (4+ alternations in one paragraph) maximizes interference and should be avoided even after the learning phase.

**3.12. No chapter should have 0 mentions of any coined term. Every chapter should include at least one mention in its intro paragraph.**

If the span between encounters is too long, the reader forgets much of the word and must partly learn it again. Every chapter should contain at least one natural mention of each coined term. Within a chapter, avoid gaps larger than ~3,000 words (~8 pages) between mentions. The intro mention serves as an advance organizer that primes the reader's schema (Lorch & Lorch 1996): when most chapters signal the term in the intro but some do not, the unsignaled chapters receive weaker encoding than if no chapters signaled at all. Consistent intro placement across all chapters avoids this penalty.

**3.13. Distribution should be front-loaded with expanding intervals, not even across chapters.**

Teaching guides recommend dense introduction followed by expanding spacing (Ebbinghaus 1885, Mace 1932, Pimsleur 1967). Later studies find that equal spacing works as well or better for long-term memory (Karpicke & Roediger 2007), so treat the expanding shape as a guide, not a law. The correct shape for term distribution is asymmetric: dense at the start (learning), sparse in the middle (maintenance), and denser again where new meaning layers are introduced (polysemy deepening). Attempting even distribution would either overwhelm maintenance chapters with forced mentions or starve learning chapters of needed repetitions.

**3.14. Coined terms benefit from body-integrated placement in learning/deepening chapters, but intro+summary-only is acceptable in maintenance chapters.**

In chapters that introduce or deepen a term's meaning (learning/deepening phases), place the term where it emerges from the argument (body integration), not only in introductions and summaries. Body-integrated encounters trigger deeper processing (Craik & Tulving 1975), the generation effect (Slamecka & Graf 1978), and higher involvement load (Hulstijn & Laufer 2001). In maintenance chapters where terms are already established, intro+summary placement serves as retrieval triggers and is sufficient. The critical constraint: body placement must serve the argument. If inserting a term interrupts idea flow or feels forced, keep it in intro/summary positions. "Natural" body integration (term emerges from reasoning) activates deep processing; "forced" insertion (term dropped into an unrelated argument) does not.

**Analytical framing:**

**3.15. One analytical lens per paragraph.**

Every paragraph develops through a single analytical lens. When a chapter grounds in a foundational lens (cognitive science, historical development, economics), structural claims appear as consequence or example, not as a parallel analytical framing. Mixing two lenses inside one paragraph doubles the concepts the reader must hold active and obscures which lens drives the argument.

Example of violation: a paragraph opens with a cost claim ("A rain barrel cuts the water bill") and shifts in the next sentence to an experience claim ("Gardeners enjoy the sound of rain filling it"). Each sentence works alone, but the paragraph now demands the reader reconcile two analytical frames with no signal about which is primary.

This rule is a sharpening of 3.3 (one idea per paragraph). Two lenses are not two ideas per se; they are two framings of the same idea, which creates a subtler load. The reader cannot chunk the paragraph under a single analytical schema, so working memory holds both frames in parallel.

Fix: pick the lens that matches the chapter's foundation and subordinate the other. In a chapter grounded in cost, the cost claim leads and the experience follows as its consequence. Inversely, in a chapter grounded in the gardener's experience, cost appears as a "which is why ..." qualification after the experience.

---

### 4. Prose Style

Rules 4.1-4.16 describe prose that connects. Several of them (4.5, 4.7, 4.8, 4.9, 4.13, 4.16) set the author's own habits, so their form and numbers come from the voice profile.

**4.1. Grammatically correct English always.**

All writing must strictly follow standard English grammar, syntax, and lexical correctness. A voice profile may bring patterns from another language (long connected sentences, fronted inversions, explicit connectors), but they must always be executed within the bounds of grammatically correct English. The goal is clarity and precision, not deviation or error.

**4.2. Connect every sentence to neighbors with connectors (e.g., which, so, because, this means).**

Sentences must flow into each other, not sit side by side. Use explicit connectors both within and between sentences.

**Within sentence:** `[Main Statement]` + `, which/where/who/whose` + `[adds detail or consequence]`.

**Between sentences:** Every sentence must explicitly signal its relationship to the previous sentence. Use connectors such as "This means", "Because of this", "For that reason", "The result is", or back-references such as "This rule", "That constraint", "The same mechanism". A sentence that follows another without any visible bridge forces the reader to infer the connection, which breaks flow (Rule 2.2, bridge test).

Wrong (no bridge between sentences):
"Rule 4.2 requires explicit connectors. Readers follow the argument without stopping."

Right (bridge signals the relationship):
"Rule 4.2 requires explicit connectors. Because each connector signals how the new sentence relates to the previous one, readers follow the argument without stopping."

**Sentence-initial:** words such as "So", "Because of that", "As", "If", "Still", "Instead", "Then", "Otherwise", "Also", "Another" and "In the end" can start a sentence. The voice profile may prefer some of them.

**Example:** "The village drained its marsh to make new fields, **where** one wet spring then put every field under water."

| Connector | Use When | Example |
|-----------|----------|---------|
| which | Adding consequence | "This reduces load, which allows readers to focus." |
| because | Explaining cause | "The limit applies because the same brain processes both." |
| due to | Explaining cause | "The train stopped due to a fallen tree." |
| as | Explaining cause | "As complexity grows, understanding becomes harder." |
| so | Stating result | "So the reader follows the argument without stopping." |
| leads to | Stating consequence | "This mismatch leads to confusion." |
| where | Adding context | "Chapters group sections, where each heading names one step." |
| also | Adding related point | "The dough also needs rest." or "Also, consider the oven." |

These are examples; other connectors with similar functions are valid.

**Full example:** "Invoices are the smallest records the ledger keeps, which means every report the business reads is built from them. Each invoice carries a date and an amount, so an error in one invoice travels into every report that sums them."

**Causal connectors require true reasoning.** When using causal connectors (because, due to, as), the clause must explain WHY the main statement holds, not merely add a related fact. Test: "X because Y" should mean "Y is why X holds." Y can be a factual cause (*heat rises because warm air is less dense*) or the mechanism / evidence / rationale behind a descriptor (*the boundary is unstable because no test catches drift*). Both count as causation.

**Three-way decision for connector choice.** Before writing a connector clause, determine the relationship:

| Relationship | Test | Connector |
|---|---|---|
| Causation: Y is the reason X happens | Remove Y. Does X stop being true? | because, due to, as |
| Characterization: Y describes what X is | Y adds a property or fact about X | which, where |
| Association: Y relates to X but neither causes nor describes it | Y is relevant context | and, yet, while, but |

**Wrong (characterization disguised as causation):** "Connectors improve flow, because words like 'which' and 'because' link sentences together." (This describes WHAT connectors do, not WHY they improve flow.)

**Right (true causation):** "Connectors improve flow, because they tell the reader how each new sentence relates to the previous one." (Knowing the relationship is the reason flow improves.)

**Right (characterization using "which"):** "Connectors link adjacent sentences, which tells the reader how each new idea relates to the previous one." (The "which" clause adds what the linking achieves without claiming causation.)

**Wrong (circular -- restates the claim in different words):** "Topic sentences are effective, because stating the paragraph's subject first helps the reader." (Restates "topic sentence is effective" rather than explaining why.)

**Right (true causation):** "Topic sentences are effective, because they activate the reader's prediction mechanism before details arrive." (Prediction is the mechanism that explains why.)

**Descriptor subjects still permit `because`.** A left clause with `is/are/means` does not force a switch to `which`. When the right clause grounds the descriptor in mechanism, evidence, or rationale, `because` is correct. The three-way test's Causation row covers both factual cause-and-effect AND grounding a descriptor in the reason it holds. Switch to `which` only when the right clause restates or defines the descriptor without adding new information.

**Right (descriptor grounded in mechanism):** "The new riverbank is fragile because no roots hold the soil in place yet." (The missing roots are the mechanism that makes fragility hold.)

**Right (descriptor grounded in rationale):** "Price and taste are independent here because a cheap bakery can bake a better loaf than an expensive one." (The counterexample is the rationale justifying independence.)

**Wrong (descriptor restated, not grounded):** "The reduction is substantial because it is a large change." (Right clause restates "substantial" without naming a mechanism.)

**Switch to `which` only for restatement or definition:** "This rule is the three-way test, because it distinguishes three relationships." -> "This rule is the three-way test, **which** distinguishes three relationships."

**Comparisons require a common measure.** When comparing two things (costs, effects, mechanisms), both sides must be measurable through the same dimension. Do not compare effects from different domains using parallel connectors like "while." Instead, compare through a shared dimension. If no common measure exists, state each side independently rather than forcing a parallel structure.

**Wrong:** "A paragraph develops one idea across 3-8 sentences, while a sentence delivers one step in 10-25 words." (Sentence count and word count are different units; "while" implies comparison but these are two separate rules at different levels.)

**Right:** "Both the paragraph limit and the sentence limit serve the reader's limited attention: the paragraph limit caps how long one idea develops, and the sentence limit caps how much each step contains." (Common measure: the reader's attention.)

**"Which" clauses deliver specific content.** A "which" clause names the specific consequence, mechanism, or insight it adds. "This reflects the same dry summer that cut the first harvest" delivers specific content. "This suggests something fundamental about gardening" gestures at content without delivering it. Test: state what the "which" clause adds in one concrete phrase. If the answer is "something important" or "implications," the clause needs to name what that something is.

If the clause is merely related but not causal, use a different connector (and, yet, while) or restructure.

**4.3. Use right-branching clauses; append at end of sentences.**

Append clauses at the end of sentences; keep self-embedding to one level (Rule 3.8).

**4.4. Keep subject and verb close together.**

Structure sentences so that explanations come before or after the main clause.

**4.5. Fronted inversions at the rate the voice profile sets, and varied.**

A fronted inversion places a source, cause or earlier idea first and inverts subject and verb: "From this observation emerged a new principle." It is valid literary English. Some voices use it often enough that readers recognise it as how the author writes; others barely use it. The voice profile decides the rate (`inversion_gap_words`: no stretch of that many prose words without one; 0 means no floor), and `sentence-and-paragraph-check.py --inversions` measures it.

**Pattern:** `[From/Out of/Into] + [noun phrase]` + `[verb]` + `[subject]`

**Examples:**
- "From this observation emerged a new principle."
- "Out of this tension came the cooperative movement."
- "Into this gap stepped a new generation of practitioners."

**The inversion is of the relation, not merely of subject and verb.** Front the source, cause, or preceding idea, and postpone what it produces: "From that agreement comes confidence", never "Confidence comes from that agreement". The fronted element normally points back at the argument just made, which is why it usually opens with `this` or `these`, and the postponed subject is the new thing the argument earns. A subject-verb flip whose fronted element is only a place or a scale ("Across the valley runs the same river", "Behind both houses sits the same hill") satisfies the syntax but not the rule, because nothing is derived from anything. The script reports those separately.

Use only fronted source or time phrases for inversion. Standard word order for all other constructions.

**Why the measure is a running gap, not a per-section count.** Sections vary in length by an order of magnitude, so a per-section count is satisfied by one inversion per section whatever its length, and density collapses in long sections. The gap measure works regardless of where section boundaries fall, and it crosses chapter boundaries, so run it over the whole manuscript.

**Three constraints, checked by `sentence-and-paragraph-check.py --inversions`:**
- **Floor.** No gap longer than the profile's `inversion_gap_words`.
- **Variety.** Do not repeat the same preposition-and-verb pairing within a section. The demonstrative head ("this", "these") is not drift, because the back-reference is what makes the fronted element a source. A manuscript where most inversions use one verb and one preposition reads as formulaic, so filling a gap with yet another "From this X emerges" makes the prose worse. The script prints the lexical profile for this reason.
- **Proximity.** Never two within `inversion_min_paragraph_gap` paragraphs (three by default). The worst case is two consecutive paragraphs opening on near-identical constructions, so the second reads as an echo.

Adding an inversion is a real edit, not a mechanical insertion. It has to be the sentence the paragraph already wanted. If placing one would force the point, leave the gap and note it.

**4.6. Use conditional-consequential sequences (If... then...).**

Use `If... then...` structures to clearly lay out logical consequences for procedural clarity.

**Pattern:** `If [condition], [consequence].` / `In case of [condition], [action].`

**Example:** "**If** two diets with opposite rules both help people lose weight, **then** neither rule can be what makes a diet work."

**4.7. Prepositions per the voice profile.**

Some voices prefer specific, slightly formal prepositions ("paid via bank transfer", "stored at room temperature", "in case of failure", "for that reason" in full rather than a bare "for that"). The voice profile says whether this book does. Whatever the choice, use it the same way across the book.

**4.8. Nouns made from verbs per the voice profile.**

A noun made from a verb ("the removal of weeds", "the creation of a budget") can carry an abstract process as the subject of a sentence. Too many of them make prose heavy. The voice profile says how freely this book uses them. When used, the noun form is "removal of weeds", never the gerund "removing of weeds".

**4.9. Passive voice with a purpose.**

Use the passive voice when the actor is obvious, does not matter, or when describing an impersonal process: "The configuration can be adjusted if needed." "The bridge was opened in 1932." Use the active voice everywhere else. The voice profile says how often this book reaches for the passive. Structure: subject + be + past participle, with the articles English needs.

**4.10. Write with authoritative voice grounded in argument.**

Write with direct, earned confidence. Authority comes from explicit, well-developed argument, not from assertion alone.

**Example:** "Direct statements earn authority through grounded argument. This sentence states its point without hedging, which shows the confidence that comes from explicit reasoning."

**4.11. Acknowledge trade-offs directly ("The trade-off is...", "Unfortunately...").**

Be honest about limitations. Use direct phrases like "The trade-off is..." or "Unfortunately, it supports only..."

**4.12. Use measured language; state substance directly; match claim strength to evidence strength.**

Let substance speak for itself through measured language. The argument's quality earns attention, not intensifiers or superlatives.

**State substance directly.** Every sentence delivers its content in concrete terms. "This reflects the dry summer described in the previous chapter" is direct. "This reveals something important about health" promises without delivering. Name the implication, the relationship, or the insight rather than gesturing at it. Let evidence speak for itself: when a quote or example demonstrates a point, the reader who followed the development draws the conclusion without meta-commentary ("which emphasized the cognitive benefit").

**Match claim strength to evidence strength.** When exceptions exist, use "rarely," "most," or "typically" rather than absolutes. "Rarely does a recipe say at what altitude it was tested" matches reality where some cookbooks do say so. Claims grounded in the author's direct experience can be stated directly per rule 7.1.

**4.13. Join related ideas when a sentence would fall under the voice profile's minimum.**

When an idea alone would produce a sentence under the profile's `sentence_min_words`, join it with a related idea using relative clauses (which, where, so, because) or conjunctions. This prevents broken-up narration, while explicit connections keep the extra length easy to follow. When a voice prefers short sentences, the same rule works the other way: split a sentence that carries two ideas.

**Pattern:** "This is its purpose, which is to keep the soil moist between waterings."

**4.14. Technical register: familiar terms first, precise after schema built.**

- **First mention:** Use familiar terms ("heart attack", "high blood pressure") to reduce cognitive load.
- **After establishment:** Use precise terms ("myocardial infarction", "hypertension") once schema is built.

**4.15. Chain reasoning across sentences: statement -> which means -> so -> because.**

Each sentence adds to the previous, never restarts. The reader never wonders "why is the author saying this now?"

**Example:** "Connectors link sentences into chains. This linking creates flow, which means the reader moves forward without stopping. Because each sentence connects to the previous, the argument builds naturally."

**Counterweight: vary the cadence.** Applied in every paragraph, the same chain (statement, then "which means", then "so", then "because") produces one uniform rhythm that outside readers report as fatigue: a long declarative sentence with a trailing "which ..." or "because ..." clause, again and again. Vary the connector, the sentence shape and where the clause sits. In check mode, count "which means" per chapter; a count that stands out is a signal to rewrite some openings, not every sentence.

**4.16. Punctuation per the voice profile: colons for explanations, no exclamation marks in argument, parentheses sparingly.**

Colons connect a statement to its explanation or concrete example: "The answer lies in the flour: how much protein it holds decides how much water it takes." The colon is the main inline clarification mark and replaces a pair of dashes (rule 9.1). Exclamation marks contradict measured language (rule 4.12). Parentheses may hold brief clarifications but not arguments or content that belongs in the sentence chain. Whether semicolons are allowed, and how dashes are used, is set by the voice profile; the default profile allows rare semicolons and never wraps a phrase in a pair of dashes.

---

### 5. Audience

**5.1. Address reader as intelligent person who hasn't thought about this yet.**

You are sharing what you have learned as a peer. The reader is capable of understanding complex ideas when properly explained.

**5.2. Accessible to non-native English speakers.**

Use clear language accessible to non-native English speakers. Prefer direct phrasing that translates well across cultures.

**5.3. Layering: basic idea first, nuance after.**

Explain concepts thoroughly but efficiently, layering information (basic idea first, nuance after) so that a beginner learns the fundamentals and an expert sees deeper connections.

**Example:** "When readers meet an unfamiliar term without explanation, they must either stop to search for its meaning or continue with incomplete understanding. Both outcomes break the reading flow. This problem has a name in instructional design: *cognitive overload*, which occurs when a reader must hold more unexplained ideas than attention allows. The solution is to describe the effect first, so the reader recognizes it, and only then attach the technical label."

**5.4. Use simple vocabulary (A2 level) for general words; technical terms are allowed.**

Technical terms (compound interest, crop rotation, blood pressure) are necessary because they name specific concepts. General vocabulary should use words that elementary English learners know. The test for flagging a word is whether it blocks your reader, not its dictionary level: see `${CLAUDE_PLUGIN_ROOT}/skills/review-text/references/hard-words-criteria.md`.

**Example:** "Crop rotation moves each crop to a new bed every year, which means pests that live in the soil lose their food."

**5.5. Prefer common 1-2 syllable words over formal synonyms (see vocabulary reference table).**

Use "use" not "utilize", "help" not "facilitate", "begin" not "commence", "then" not "subsequently", "about" not "approximately".

**Vocabulary reference table:** the substitution list is in the Word-Level Lookup Tables at the end of this file. Add new violations there. Technical terms that name specific concepts keep their precise form per rule 5.4.

**5.6. Content addresses the whole audience the book names.**

The book's audience file (`thinking.audience`) names its audience. Write for all of it and do not favour one sub-group: a reader from one part of the audience should never feel the book was written for another. For a technical book this means language- and platform-neutral terms and examples; see `technical-books.md`.

**5.7. Replace opaque phrasal verbs; keep the ones your reader reads without effort.**

A phrasal verb earns replacement only when its meaning cannot be recovered from its parts **and** it is not standard register in the field. "Comes down to" and "boils down to" qualify. These do not, and should be left alone:

- **Standard academic or professional collocations** -- "account for", "draw on", "set out to", "carried out (research)", "pay off". Non-compositional by the dictionary test, but every reader of the field meets them daily.
- **Resultative forms** -- "end up", "turn out". They mark a state reached after a process, which no plain verb carries. "The bread ends up dense even though the dough rose well" loses its point as "the bread is dense".

Judge by whether your reader stumbles, not by whether a dictionary calls the phrase idiomatic. High CEFR level is not the test either: "which suggests" is B2 yet transparent, while "come down to" is A1 words and fully opaque.

Replacement is decided per site, never per word. Most of these verbs are polysemous ("account for" means handle in one sentence and explain in another), so no fixed substitution is safe.

**5.8. Rephrase a possessive on a word that ends in s.**

"Jones's design" and "the boss's name" read as "s's" and cost readers of English as a second language an extra parsing step. Rephrase with "of": "the design of Jones", "the name of the boss". Other possessives ("the reader's attention") are fine unless the voice profile says to avoid them too. The base Vale package flags only the s-ending form (`PlainBook.PossessiveSEnding`).

---

### 6. Book Architecture (Fractal Structure)

The book applies Section 1's pattern (Topic -> Develop -> Conclude) at every level from book to paragraph, which creates levels of detail the way an atlas does: a map of the country, then of a region, then of a town. Three ideas guide this architecture: each level shows the level above only what it contributes, each level keeps one degree of detail inside, and the structure is predictable.

#### The Fractal Pattern

Section 1 defines the Topic -> Develop -> Conclude pattern, which applies at every level of the book hierarchy:

| Level | Topic | Develop | Conclude |
|-------|-------|---------|----------|
| Book | Preface poses the question | Parts develop the answer | Final chapter synthesizes |
| Part | Opening chapter poses theme | Concept chapters develop | Synthesis chapter or transition |
| Chapter | Opening poses question | Sections develop the answer | Summary synthesizes |
| Section | First paragraph states topic | Middle paragraphs develop | Final paragraph synthesizes |
| Paragraph | Topic sentence | Supporting sentences | Concluding sentence |

This repeating structure creates levels of detail in the book, just as an atlas moves from the whole country to one street. The same Topic -> Develop -> Conclude pattern at each level enables readers to predict structure, which reduces cognitive load.

#### Each Level Shows Only What It Contributes

**6.1. Each Part covers its topic completely.**

A Part is complete on its own, like one volume of a field guide. When the reader finishes a Part, they should have complete understanding of that topic. Nothing should spill forward into later Parts, and nothing from later Parts should be previewed. Other Parts refer to what a Part teaches, not to how its chapters are arranged.

**Example:** A Part about soil contains everything about soil: what it is made of, how to test it, and how to improve it. The next Part can reference "the soil tests" but should not re-explain them.

**6.2. Each level tells the level above what it contributes, not how it is built.**

Other chapters refer to what a chapter teaches, not to its sections. Other sections refer to what a section shows, not to its paragraphs. The reader at each level sees what that level provides without needing the structure below.

**Example:** When a Part summary references Chapter 3, it describes what Chapter 3 contributes without walking through Chapter 3's sections one by one. At the Part level, the chapter is one contribution.

**6.3. Forward references are forbidden; backward references are encouraged.**

A chapter must NOT mention concepts explained in later chapters, because a reader cannot lean on an idea they have not met yet.

**Forbidden:** Naming concepts from later chapters before they are explained.

**Allowed:** "The previous chapter established X" in the current chapter (backward reference to explained concept).

**Transition pattern:** End a chapter with the open question or problem that the next chapter takes up, in words the reader already has ("But what does the garden do when the frost comes early?"). Do not announce the next chapter's content ("The next chapter examines ...", "The next subsection shows how ..."): review-text flags that as a mechanical transition.

**How 2.11 and 6.3 fit:** a concept is introduced before it is used, and later text refers back to it. Neither rule allows a sentence that names or explains a concept the reader has not met yet.

#### One Degree of Detail Inside Each Level

**6.4. Each level of the book stays at one level of detail.**

Each level of the book hierarchy should keep a consistent level of detail. Mixing levels within a Part or Chapter creates comprehension problems.

| Level | Level of detail | Contains |
|-------|-------------|----------|
| Part | Major theme or quality | Complete treatment of one theme |
| Chapter | Concept or principle | Full development of one idea |
| Section | Mechanism or aspect | One facet of the chapter's concept |

**Anti-pattern:** A chapter that mixes theory, principles, AND specific techniques operates at three levels. Split into separate chapters, each at one level.

**6.5. Principle chapters explain WHY; application chapters show HOW.**

Principle chapters explain WHY something works (conceptual foundation). Application chapters show HOW to apply it (specific techniques). Mixing techniques into principle chapters breaks the level of detail.

**Pattern:** Principle chapters explain the concept and its mechanism. Application chapters show techniques as applications of the principles.

**Key insight:** Named techniques exist because practitioners discovered they work. The principles explain WHY they work. This means readers who understand the principles can apply them in new situations, not just memorized patterns.

**6.6. Synthesis chapters synthesize; they do not introduce new teachable concepts. New citations and evidence are allowed when they ground a claim the chapter synthesizes.**

A synthesis chapter exists to show how previously explained concepts work together. It should reference mechanisms from earlier chapters (not re-explain them), show the unified framework briefly, demonstrate how pieces connect, and transition to the next Part.

**Anti-pattern:** A synthesis chapter that introduces new techniques, patterns, or frameworks is adding content, not synthesizing. Move new content to its own chapter.

**What the rule does NOT forbid: new grounding.** A synthesis chapter draws conclusions the earlier chapters did not state, and those conclusions need support like any other claim (Rule 2.9). Bringing in a citation, a study, or an expert position for the first time is grounding, not new content, so it stays within the rule. The test is what the reader must take away: if the reader now has to learn and apply a new technique or pattern, the chapter added content; if the reader gets evidence for a claim the chapter synthesizes from what came before, the chapter grounded it.

Example (allowed): a synthesis chapter bounds the reach of the book's principles by citing an outside distinction for the first time, or supports a delivery claim with studies no earlier chapter needed. Example (forbidden): the same chapter introduces a named pattern the reader is expected to apply, which belongs in the chapter that teaches techniques.

#### Predictable Structure

**6.7. Titles predict content at every level.**

Titles should generate accurate predictions. The reader who sees "What Composting Means" predicts this chapter defines composting. The reader who sees "Compost in Practice" predicts this chapter shows applications.

**Prediction chain:** Part title predicts the theme covered, chapter title predicts the concept explored, section title predicts the mechanism or aspect explained.

**6.8. Navigation (dive in, return) applies when content forms a framework.**

Reading a book is like exploring a city with a map. The reader dives into a concept, explores its details, then returns to the higher level with new understanding. This creates a zoom-in/zoom-out rhythm. However, this pattern applies only when the content benefits from it.

**Book-level navigation (Parts):**
```
First Part: Opening (poses the book's central question)
  -> Middle Parts: one major theme each, explored in depth
<- Last Part: Return (brings the themes together and answers the question)
```

**Part-level navigation (Chapters) - when applicable:**
```
Part opens: poses the central question
  -> Foundation chapter: establishes conceptual basis
    -> Concept chapter 1: explores first main idea
    -> Concept chapter 2: explores second main idea
  <- Synthesis chapter: return (see how concepts work together)
  -> Application chapter: show practical techniques
Part closes: reader has complete understanding
```

**When navigation pattern applies:** Multiple related concepts that form a framework, concepts that build on each other and need a "zoom out" moment, or reader needs to see how pieces connect before moving on.

**When navigation pattern does NOT apply:** Content is naturally sequential (each chapter follows logically from previous), chapters are relatively independent (no framework to synthesize), or Part covers one coherent topic without sub-frameworks.

The structure should serve the content, not force content into a template.

---

### 7. Teaching Voice

**7.1. First-person is allowed for personal experiences, discoveries, and recommendations.**

First-person creates connection with the reader. Use it for sharing experiences, discoveries, and recommendations.

**Example:** "I noticed this pattern when I taught my first bread class. I recommend starting with the simplest loaf, which builds understanding before complexity."

**7.2. Questions may guide reader toward conclusions.**

Questions prompt reflection before the answer. The reader thinks, then receives the synthesis.

**Example:** "Why does the second loaf come out flat? Both loaves used the same dough, but the second went in after the oven door had stood open for a minute. This lost heat is what turns a good dough into a flat loaf."

**7.3. Person per the voice profile, the same across the book.**

Who "I", "you", "the reader", "we" and the name of the reader's field ("nurses", "gardeners") refer to is a voice choice. The voice profile sets it. The default: "I" for the author's own experience, "you" when the reader acts, "the reader" for what happens in the reader's mind, the field's name for the profession, and "we" only when author and reader truly act together. Whatever the choice, keep it the same in every chapter, because a switch in person reads as a switch in who is speaking.

---

### 8. Headings

Headings serve as navigation and retrieval cues, which means they should name content directly.

**8.1. Headings are findable labels; each should work as an index entry.**

A reader scanning the table of contents or searching for a topic should find what they need from the heading alone. "The Hungry Gap" tells the reader exactly what that subsection covers, which means they can decide whether to read it.

**8.2. Chapter titles frame the central question.**

Chapter titles announce what question the chapter explores. "What Composting Means" frames the inquiry; the chapter develops the answer.

**8.3. Section titles (##) frame what question the section answers using "What" or "How".**

Sections use question-word phrases that scope the reader's attention. "What Turning Means" tells the reader this section defines turning a heap. "How Turning Works" tells the reader this section explains mechanisms.

**Example section titles:**
- What Turning Means (defines a concept)
- How Turning Works (explains mechanism)
- What Limits a Compost Heap (identifies constraints)
- How to Size a Compost Heap (provides guidance)

**8.4. Subsection titles (###) name concepts, phenomena, or conclusions directly.**

Subsections label what the reader will find. Three natural forms work well:

| Form | Use When | Example |
|------|----------|---------|
| Concept term | Introducing vocabulary | Humus, Leaching |
| The + noun phrase | Naming a specific phenomenon | The Hungry Gap, The Spring Flush |
| Declarative statement | Stating a conclusion | Wet Heaps Turn Sour, Why Winter Heaps Are Slower |

**8.5. Use plain language: concept terms, "The + noun phrase" for phenomena, or declarative statements.**

Headings state what is there. "The Critical Distinction" names a distinction the reader will learn. "Leaching" names a mechanism the subsection explains. This directness helps readers find and remember content.

---

### 9. Format

**9.1. ASCII only (codes 32-126), except letters with accents; use standard alternatives for special characters.**

Use standard ASCII characters (codes 32-126) throughout for consistent rendering across all systems and build tools. Letters with accents are allowed: a name or word keeps its own spelling, with its own accents (the o with an umlaut in a German surname, the e with an acute accent in a French word). The check allows the letters of Latin-1 Supplement, Latin Extended-A and Latin Extended-B; punctuation and symbols outside ASCII are still replaced. The substitution table is in the Word-Level Lookup Tables at the end of this file; `scripts/ascii-normalize.py` finds and (with `--fix`) replaces them.

When tempted to use a dash for inline clarification, restructure the sentence instead. Place the clarifying information before the main point, after a colon, or in a separate sentence.

**ASCII diagram example:**
```
+-------------+     +-------------+
|    Farm     |---->|   Market    |
+-------------+     +-------------+
```

**9.2. Prose for logical sequences.**

When items form a causal chain or logical progression, write them as connected prose with colons rather than bullet lists.

**Pattern:** "The baker mixes the dough in the evening, lets it rise overnight, and bakes it at dawn."

**Cognitive principle:** Prose with connectors builds one coherent schema; bullet lists support scanning.

**9.3. Lists for reference/scanning material only.**

**ALLOWED for bullet lists:**
- Reference material (addresses, measurements, file paths, commands)
- Checklists (verification items)
- Scanning content (not meant to be read linearly)

**Use prose instead for:**
- Logical sequences (prose with connectors)
- Comparisons ("X, while Y" or "X, whereas Y")
- Flowing arguments (connected prose)

**Conversion pattern:** When you have a bullet list of related points, convert to: "X happens in case A, while Y happens in case B. The pattern Z triggers X, whereas the pattern W triggers Y."

**9.4. Convert consecutive bold headers (3+) to connected prose.**

Multiple **bold headers** with separate short paragraphs can read like a disguised list. Convert to connected prose when content forms a logical sequence.

**Signal:** Three or more consecutive bold-header paragraphs with 1-2 sentences each.

**Solution:** Connect with "In X, ...", "For Y, ...", using relative clauses and connectors.

**9.5. New concept terms: *italic* on first use, plain text on all subsequent uses.**

When introducing a concept for the first time, italicize the term. All subsequent uses revert to plain text. This convention is common across trade, academic and technical publishers and style guides (Chicago Manual of Style 7.56, APA, Google, Microsoft); `term-formatting.md` has the details.

**Example (first use):** "*Crop rotation* moves each crop to a new bed every year, so that no pest settles in one place."

**Example (subsequent use):** "Crop rotation works the same way in a window box and on a farm."

Italicize only when the term is being introduced or defined, at its formal definition point, not at earlier preview mentions. A compound whose adjective the book already introduced needs no italic. Background terms from the field (compound interest, crop rotation) stay plain. Do not italicize on every occurrence, because overuse causes italics to lose their signaling force. The evidence behind this rule is in `term-formatting.md`.

**9.6. Code identifiers in running text: `monospace` always.**

When referencing code artifacts in prose (class names, method names, variable names, keywords, data types, filenames), use monospace (backtick) formatting. This applies on every occurrence, not just the first.

**Example:** "The `OrderService` class delegates payment processing to the `PaymentGateway` interface, which defines the `charge()` method."

Code identifiers are always monospace regardless of context, because they refer to actual code artifacts that the reader could find in a codebase.

**9.7. Concept names vs. code names: *italic* for abstract concept, `monospace` for code artifact.**

The same word can refer to either an abstract concept or a code artifact. Context determines which formatting applies. When discussing the principle or idea, use italic (on first use) or plain text (on subsequent use). When discussing the actual code element, use monospace.

**Example:** "*Backpressure* keeps a pipeline from drowning its slowest stage." (concept)

**Example:** "The `Backpressure` class wraps a queue with a size limit." (code artifact)

This distinction helps readers understand whether the author is discussing an idea or an implementation.

**9.8. Bold in running text: avoid.**

Reserve bold for headings, structural elements, and rule labels. Do not use bold in running prose to highlight terms, emphasize words, or introduce concepts. Bold in running text is a textbook convention tied to glossaries; trade and professional books use italic instead (see `term-formatting.md`). A book may reserve bold for the defined term at the start of a definition blockquote (`definition-check.py` keeps those traceable to the glossary). For emphasis, use italic sparingly or let sentence structure carry the weight.

**Exception:** Bold is acceptable in tables, rule labels (like this style guide), and structural markers.

**9.9. Quotation marks around terms: only for ironic or non-standard usage.**

Do not use quotation marks to introduce or define new terms. Use italic instead (rule 9.5). Quotation marks around terms signal ironic, skeptical, or non-standard usage.

**Correct:** Some shops call this food "natural", but the label says little about what is in it.

**Correct:** *Crop rotation* is the practice of growing a different crop in each bed every year. (italic for definition)

**Incorrect:** "Crop rotation" is the practice of growing a different crop in each bed every year. (quotes for definition)

If you write "so-called X," neither italic nor quotation marks are needed, because the phrase itself signals the special sense.

**9.10. One paragraph per line.**

Write each paragraph, list item and blockquote paragraph of a Markdown file as one line, however long. Never break it at a column: the line breaks show up in every diff when a sentence changes, and the author reads them as noise. A blank line separates two paragraphs; a line with only `>` separates two paragraphs of one blockquote.

**Exception:** Headings, table rows, code blocks, pandoc fenced divs (`::: {#refs}` and `:::`) and field lines that start with a bold label (`**From:**`, `**Note:**`) stay one item per line, because the build and the scripts read them line by line.

---

### Term Formatting Summary

| Element | Format | When |
|---------|--------|------|
| New concept term | *Italic* | First use only |
| Same concept term | Plain text | All subsequent uses |
| Code identifier | `Monospace` | Every occurrence |
| Book title | *Italic* | Every occurrence |
| Paper/article title | "Quotation marks" | Every occurrence |
| Emphasis | *Italic* (sparingly) | When sentence structure alone is insufficient |
| Ironic/non-standard usage | "Quotation marks" | First use only |
| Bold in running text | Avoid | Use only for headings and structural elements |

---

### 10. Priority

**10.1. When principles conflict, resolve in order: Context First -> Explicit Structure -> Grounded Argumentation -> Connected Prose -> Authoritative Voice.**

1. **Context First** - Foundation. Nothing else works if the reader does not understand.
2. **Explicit Structure** - Navigation. The reader must know where they are in the argument.
3. **Grounded Argumentation** - Credibility. Claims without support undermine everything.
4. **Connected Prose** - Execution. How ideas flow within the structure.
5. **Authoritative Voice** - Tone. The confidence that emerges from the above.

This priority reflects dependency: you cannot write with authority about claims you have not grounded, and you cannot ground claims the reader does not yet understand.

---

### 11. Code Examples

These rules apply when the book shows code. Code examples carry teaching like prose does, so they meet the same quality standard. More for technical books: `technical-books.md`.

**11.1. Code examples are complete enough to read without guessing.**

Every variable must be declared or its origin must be obvious from context. If the example uses `errors.add(...)`, the reader must see where `errors` comes from and what happens with it after. The reader should understand the example without referring to external knowledge about the specific framework.

**11.2. Code examples look like production code.**

Use realistic class names, method names, and domain structures that the reader would encounter in a real codebase. A domain object that stores related records as a flat list of ids is unrealistic in most production code. A name the reader does not recognise from practice (`CustomerFactory.createFrom()`) is weaker than the one they would expect (`CustomerMapper.toCustomer()`). The reader's trust in the argument depends on trusting the example.

**11.3. Examples use language-agnostic constructs.**

Use constructs that readers from any language background can follow. When a language-specific construct is necessary (access modifiers, compilation units, framework annotations), note that other languages provide equivalent mechanisms. Use a plain number and a plain object over a precise decimal type or a value object when that precision is not the point of the example.

**11.4. Each code example appears once within a Part.**

When multiple chapters need the same scenario (e.g., `checkout`), the owning chapter develops the full example with explanation. Later chapters reference it briefly: "The `checkout` example in the previous chapter showed..." Per rule 2.15, duplication wastes reader attention.

**11.5. Each example demonstrates exactly what the text claims.**

If the text says "business logic is buried after fifteen lines of detail," the example must show both the detail AND the business logic that follows it. If the text says a method violates command-query separation, the example must show both the return value and the side effect. The reader who reads the example should see exactly what the text describes.

---

### 12. Book-Level Coherence

Rules 12.1 through 12.3 address whole-book coherence that no per-chapter review can catch. They fire at sentences that look fine in isolation but erode the book's argument when accumulated across chapters. Each rule requires a reviewer to hold any hierarchy of ideas the book defines, its thesis direction, and its glossary in mind while reading.

**12.1. When the book defines a hierarchy of ideas, keep it.**

When the book defines a hierarchy of ideas (in its `thinking/argument/` folder or `decisions.md`), every sentence that names concepts from more than one level must keep it. The root cannot be skipped in the chain of reasoning, an idea built on the root cannot be treated as if it were the root, and a check must be said to measure the level it actually measures. A book that defines no hierarchy of ideas needs only Rules 12.2 and 12.3.

Example (fictional): a history book grounds its explanations in records, and draws lessons from the explanations. A sentence like "the lessons prove the records were right" inverts the hierarchy -- the records are the ground, and the lessons rest on them, not the other way round.

Fix: restate the relation in the right direction, or relocate the sentence so it names only one level. Enforcement happens in `${CLAUDE_PLUGIN_ROOT}/skills/review-text/references/consistency.md` under "Thesis Hierarchy Integrity", which reads the hierarchy map the book defines.

**12.2. Back-references require a named, defined concept.**

To back-reference an idea from an earlier chapter, either use a concept registered in the book glossary or restate the idea in full. Informal phrasings ("the question from Chapter 5," "the kind of split we discussed," or a coined-sounding label the book never actually defined) cannot serve as referential anchors. The reader has no fixed hook to retrieve the referenced idea, so the reference reads as a gesture rather than a connection.

Test: can you point to where this reference was named and defined? If yes, the referenced concept belongs in the glossary -- check that it's there. If no, the reference is invalid. Replace it by either (a) naming and defining the concept first, then back-referencing, or (b) restating the idea in full.

The book glossary (`rules.glossary` in `book.yaml`) is the authoritative list of what counts as named. Anything not in it must be restated, not referenced.

**12.3. Preserve thesis direction.**

When the book's thesis states a causal or hierarchical direction between two named concepts (e.g., *evidence grounds explanations*, *soil shapes the crops a region can grow*), every sentence naming both concepts must preserve that direction. Reversals -- positioning the derived concept as senior or the root as derived -- contradict the thesis even when each sentence reads fluently individually.

Detection phrases to watch: "X applies Y," "X implements Y," "X is built on Y," "X is based on Y," where X is the derived concept and Y is the root. Rewrite with Y as the grammatical agent: "Y produces X."

Example (fictional): a farming book's thesis is that soil shapes the crops a region can grow. "The crops of the valley decide its soil" reverses direction -- the soil is not something the crops choose, the crops are what the soil allows. Rewrite with the root as the grammatical agent: "the soil of the valley allows these crops."

---

### 13. Papers

These rules hold only for a research paper (`kind: paper` in `book.yaml`). Which rules of
Sections 1-12 a paper turns off or changes is said once, in `SKILL.md` under "A book or a
paper". A reader of a paper reads it to decide whether to trust and use a result, often
reading only the abstract, the contribution list and the figures. These rules make those parts
carry the paper alone. `paper-check.py` checks 13.1, 13.2, 13.5 and 13.7.

**13.1. The abstract states the problem, what was done, the main result and what it changes, within the word limit.**

One or two sentences for each, in that order, and no citations, figures or abbreviations the
reader must look up. The limit is `paper.abstract_max_words` in `book.yaml`; a venue or arXiv
may set a lower one. The abstract makes no claim that the body does not show.

**13.2. The introduction ends with a numbered list of contributions.**

Each item is one thing the reader can use or check, stated as a result, not as an activity
("a measured comparison of two watering times on twelve beds", not "we study watering"), and
it names the section that supports it. The list is the contract of the paper: every item is
shown in the body, and the body shows nothing larger than the list claims.

**13.3. Scope every claim to what the evidence shows.**

A claim carries the limits of its evidence: the data, the setting, the people and the time it
comes from. A result measured on twelve beds in one season is a claim about those beds in that
season, and any wider claim is stated as a reading of the result, marked as such, with its
reason. Words that widen a claim silently ("always", "in general", "developers") are the
usual leak.

Test: could a reader repeat the study and find the claim false without finding the data false?
Then the claim says more than the data.

**13.4. Hedge precisely.**

A hedge says what is uncertain and why: "the effect held in both seasons we measured; we did
not measure a dry year". A vague hedge ("this may suggest", "it seems possible") hides what is
known. Use one hedge per claim, on the uncertain part only, and none on a measured result:
state a measurement as measured. Plain words of degree with a reason ("likely, because ...")
are better than stacked qualifiers ("may perhaps").

**13.5. Name the threats to validity openly, in their own section.**

A section headed "Threats to Validity" (or "Limitations") names every reason the result could
be wrong or fail to hold elsewhere: internal (the result is wrong here), external (it does not
hold elsewhere) and construct (the study measured something other than it meant). For each
threat, say what was done to reduce it, or say that it remains. The section is written in the
same voice as the results: a threat is a fact about the study, not an apology.

**13.6. Give every measured number with its uncertainty and its unit.**

A mean comes with its spread or its interval, and the text says which one it is and how many
runs or people it rests on. Report the size of an effect, not only that a test found one.
Round to the precision the measurement supports, and use the same unit across the paper.

**13.7. Point to every figure and table from the text.**

The text names each figure and table by its number ("Figure 2 shows ...") or by its label
(`@fig:beds`), before or near where it appears, and says what the reader should see in it. A
figure no sentence points to is either not needed or not explained.

---

## Word-Level Lookup Tables

These tables are the lookups a word- or phrase-level edit consults directly. They are the single
source: other files point here rather than repeating them.

**Plain vocabulary (Rule 5.5).** Prefer the common word on the right. Technical terms that name
specific concepts keep their precise form per Rule 5.4. The base Vale package
(`PlainBook.Substitutions`) swaps the one-meaning words automatically on approval.

| Formal or uncommon | Preferred |
|--------------------|-----------|
| comprehension | understanding |
| seldom | rarely |
| whatsoever | at all |
| omission | leaving out |
| comprehensively | fully, completely |
| utilize | use |
| facilitate | help |
| commence | begin |
| subsequently | then |
| approximately | about |
| in order to | to |
| additionally, furthermore | also |
| regrettably | unfortunately |

A replacement word must itself meet the plain-English bar: "obscure", "conceal", "mask" and
"bury" are harder than the figurative "hide" they would replace.

**ASCII (Rule 9.1).** Use only codes 32-126; letters with accents are allowed. `scripts/ascii-normalize.py` maps these.

| Instead of... | Write... |
|---------------|----------|
| em-dash | colon, comma, or restructure |
| curly quotes | straight quotes (" ') |
| ellipsis character | three periods (...) |
| special bullets | dash (-) or asterisk (*) |
| box-drawing characters | + - \| for boxes |
| arrows | -> <- |
| math symbols | x, /, !=, <=, >= |

## Preferred Patterns

| Pattern | Example | Rationale |
|---------|---------|-----------|
| Direct assertion | "The solution works..." | States a conclusion earned through grounded argument |
| Demonstrative opener | "This approach..." | Connects to prior context without hedging (the noun must appear in the sentence before, Rule 2.2) |
| Action statement | "The plan should..." | Focuses on outcome, not opinion |
| Specific description | "This method gives..." | Describes what something does rather than evaluating it |
| Precise qualification | "a recipe that..." | Uses specifics instead of vague praise |
| Unadorned adjective | "important" / "fast" | Lets substance speak without intensifiers |
| Clean prose | (omit filler words) | Remove "basically", "actually" |
| Concise purpose | "to" | Replaces a wordy "in order to" |
| Complete articles | "The main idea is..." | English requires articles before noun phrases |
| Standard word order | "They no longer waited..." | Inversion only for fronted source phrases (Rule 4.5) |
| Complete clause | "A budget must be made..." | Subject before verb in standard constructions |

| Use | Instead of |
|-----|------------|
| "To do this..." | "In order to accomplish this..." |
| "Unfortunately..." | "Regrettably..." |
| "Also..." | "Additionally..." / "Furthermore..." |
