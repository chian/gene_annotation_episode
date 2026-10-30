# Per-paper instructions for the experimental scoring review

This is a new research-work instruction requested by the user on 2026-10-23.
It does not replace or edit existing records, adopt a scoring formula, change
episode behavior, or finish any evidence axis. The current work is the scoring
sheet for the first of ten evidence axes; zero sheets are complete. Three fresh
research subagents may work independently on nonoverlapping source cases.

## Required reset after every paper

Work through one paper at a time. After inspecting that paper's experimental
evidence, and BEFORE interpreting it for scoring or opening the next paper,
reload and read the complete authority set below. This applies to a fresh
primary-paper read and to reviewing a retained paper-specific evidence packet.
Reading the set once at the start of a batch does not satisfy the instruction.
Do not substitute memory, summaries, headings, search hits or snippets. Read
long documents in complete sequential portions so tool-output truncation does
not silently omit instructions. Do not claim a reread that was not performed.

Paths below are relative to /home/chia/repos/gene_annotation_episode. Read the
full documents, including their corrections and original user quotations:

1. AGENTS.md and GOAL.md.
2. docs/EPISODE_STRUCTURE.md and docs/TIME_AWARE_ESTIMATION.md.
3. docs/TOOL_KNOWLEDGE.md and docs/TASK_AND_STEERING.md.
4. docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md.
5. docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md.
6. research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md
   and VERBATIM_RECOVERY_002.md in that same directory.
7. docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md.
8. verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md.
   This is the earlier numerical example the user found closer to the intended
   direction, not an accepted complete sheet or a universal assay template.
9. This entire file, including the subsequent verbatim user instructions below,
   and every later user instruction received for the task. Read the latest human
   instructions last, immediately before making the task-specific summary.

Current user instructions override older assistant interpretations. The user's
three-part template is: investigation prompt; a numerical scoring sheet; and
targeted reader/grader functions that populate that sheet. Work here concerns
the sheet. Papers provide evidence to convert into that template; they do not
replace it. Do not introduce another organization, episode type or universal
overall grade in response to a paper. The rejected R/V/A/T category ladders and
qualitative H fallback are not template definitions or scoring authorities.

## What each paper's summary must accomplish

Summarize for the scoring task, not as an abstract of the publication. Explain
what the experiment teaches us about the requested components and how its
measurements could be used to score them. Start with experimental definitions:
organism and genotype, tested protein/construct, comparison protein/construct,
whether both proteins coexist, intended changed variable, additional changes,
measured endpoint, background contributors, and the exact numerator/denominator
of each numerical comparison. Unknown details stay explicitly unknown.

Keep two user-specified questions distinct:

- Experimental comparability: similarities and differences between the
  experimental conditions, excluding the variable deliberately being tested.
- Isolation of the measured effect: how specifically the observed outcome can
  be assigned to the intended protein or change, including mixed contributions.

Other user-specified considerations include experimental relatedness to the
claim, validity given the type of experiment, weaknesses that complementary
experiments address, signal strength, consistency, uncertainty, and relation to
the organism/system being annotated. These are the user's guideposts, not
permission to replace the template with new overall categories.

For each proposed component conversion, provide:

1. Where it belongs in the user's template and why it matters to scoring.
2. A concrete experimental comparison and source location, with its actual
   measured quantities, units, controls and uncertainties.
3. How those quantities enter a component calculation. Define every operand,
   transformation, normalization and assumption. Label proposed calculations
   and synthetic numerical illustrations explicitly; do not invent paper data.
4. How that component would combine with the others through explicit sums or
   multipliers. Distinguish measured values from proposed combination weights.
   Do not stop at a table of metadata or merely rename an overall judgment.
5. What the comparison does not isolate, which complementary measurement would
   address that limitation, and which shared measurements must not count twice.
6. Any missing input or unresolved conversion. A missing relationship is work
   still to do, not justification for a fixed 0.25/0.5/0.75 overall grade.

Do not equate a raw ratio with the final score. Explain its role. For example,
64% protein abundance has different implications when the mutant replaces the
wild-type protein and when both coexist. It can inform experimental relevance;
the experimental arrangement determines how. A mixed activity readout creates
a separate effect-isolation question. A specifically scoped judgment is still
possible where no applicable measurement exists, as the user allowed; it must
not replace available quantitative components or become an overall vibe grade.

Use and cross-check the retained published examples. Existing lane reports
contain rejected overall score proposals as well as useful measured facts;
extract the facts and sources, not their old grades as instructions. Apply
SOURCE_CORRECTIONS.md, especially the YeaG recovery-growth versus survival
distinction. Do not infer that reports or technical repetitions are independent
experiments. Evidence can emerge without a pre-existing candidate annotation.

Report genuine gaps in the user's template explicitly for discussion. Do not
silently add, remove or redefine components, and do not change permanent records
to fit the paper. Write only new, separately owned research outputs. Corrections
to a research output are additive and identify the statement being corrected.
No production scorer, reader, library publication or scientific run is part of
this review. Paper counts do not count as completed scoring sheets.

The parent must print the useful summaries, examples and proposed calculations
in the conversation. The user does not read files for us. Record the documents
actually reread for each paper as research-work provenance; this is not a
runtime gate, extra episode, approval stage or scoring component.

## Subsequent user instructions, verbatim

> categorical scores like that are not real scores. they are categories coded by numbers. there are many aspects to scoring how much relevence there is. there is homology, then there is experimental compatibility, and so on... these all need to come together. why would you propose a transfer weight that was one simple vibe?

> These individual scores need to be multipliers or sum in some way. WTF else would you do? Why do you keep trying to do somethign else. This is literally what I told you to do before with experimental reliablity

> YOUR MISTAKE WAS NOT FOLLOWING MY INSTRUCTIONS FOR THE RELEVANCE SCORE. SOMEHOW, YOU WENT OFF AND DID YOUR RESEARCH ON HOW OTHER PEOPLE USE A105 as a principle, but then forgot to come back to MY PRINCIPLES. YOU AREN't COPYING FROM TEH PAPERS. YOU ARE MOVING THEM INTO MY TEMPLATE

> THE PAPERS DO NOT OVERRIDE THE TEMPLATE. THEY GET CONVERTED THOUGHTFULLY

> So for whatever the YeaG case is, if you are saying it expressed at 64% of the normalized value of the natural one, then that's one measure that you can use to ask if the experiment is relevant or not. That's what you need to convert to.

> You need to summarize the types of things the research does with examples and then you need to reread my instruction (to help reset your context from long-work reading) and then you need to fit things back into the template. Also, that's a fucking stupid way to put that into the table. Relative protein abundance matters how? Talk to me here

> Start with definitions Is this abundance comparison to a organism with wild type? Is it comparison to wild type expression in the same organism? This matters.

> Because in the former case, changes in any outcomes could be attributed either to reduced expression or it could be attributed to the mutated protein. IN the latter case, changes are only expected to about 2/5 of the activity since 3/5 is wildtype.

> This reasoning is more important than you finding facts and memorizing

> Once you know how this works, now you can start to see that you need an overall experimental relevance score that scores something based on similarity between experiments. And this experiment has similarities and differences (other than the target variable) and there should be some score grading these similarities so we know how isolated the target difference is. Does that make sense?

> There is also a separate question of how ISOLATED the effect is. This is relevant in both scenarios but especially in the second possibility I gave you (where both proteins are co-mingled)

> So this is what you are going through literature to review. What are the components of the score and how can I score them

> remember to re-read your rules and your design and the template after every paper. do not change the records. force yourself to read them

> set an instruction for every paper that include re-reading the whole set of instructions I gave you again

> YOu need to balance your "other" context with you "human owner provided" context

> Please do this so that it helps you summarize in a way that is meaningful to the task. Make sure the summaries are informed by the template you are trying to build from.

> You should be able to break the literature down into parts and have 3 independent agents summarizing based off the template as you go

> fresh agents, with new, correct, context
