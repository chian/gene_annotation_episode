# A108 (sample_context_evidence): lost grading content

Scope, as the owner narrowed it on 19 November 2026: graders, subscoring sheets and scoring sheets only. That covers
grader definitions and prompts, sheet schemas, cell components, sheet columns, how a grader fills a sheet, and which
sheet an episode writes. Goals, instructions, credit, yield, tools and messages are out of scope, except where a
message field states what a sheet cell means.

## Commits compared

| Commit | Date | Where the A108 grading content is |
| --- | --- | --- |
| `b5d7c94e2` | 2026-10-30 (import) | No A108 grader in code. There is a proposal: `research/slotted_process_library/publications/2026-10-23-002/SCORING_RUBRICS_A107_A108_A110.md` "A108: organism/sample plausibility" (an ordinal grade from 0 to 4). |
| `1019717c3` | 2026-11-04 | `gene_annotation_episode/literature_a108_subscore.py`: an interval "compatibility" subscore (`selected_lower/upper/point`, `sampling_lower/upper`). |
| `078b77668` / `fb1e4d9ba` | 2026-11-10 | **The best version.** `gene_annotation_episode/literature_a108_grading.py`, `_grading_inputs.py`, `_grading_storage.py`, `_aggregation.py`, `_aggregation_storage.py`, `_storage.py`, `literature_required_grading.py`, `literature_sheet_updates.py`, `literature_a108_prompt.py` and `literature_numerical_contracts.py`, all with the owner's inline comments. The specifications are `docs/A108_NUMERICAL_SUBSCORING_PLAN.md` and `docs/A108_MAIN_EVIDENCE_SCORING_PLAN.md` (both still in the tree). |
| `dfe3e6091` to `60889621e` | 2026-11-14 to 11-17 | The copies are reformatted, which stripped the comments. `root/library/literature_a108_grading.py` and `root/library/literature_a108_aggregation.py` (the shared root) still carry their comments up to `60889621e`. The other files have none from `dfe3e6091` on. |
| `97308b94c` | 2026-11-17 | `root/a108/library/literature_a108_*`: the same strings as now, without comments. `literature_numerical_contracts.RETURN_MEANINGS` still holds the two A108 cell meanings. |
| now | | `episode_support/literature/grading/literature_grading.py`, `inputs/literature_grading_inputs.py`, `storage/literature_grading_storage.py`, `storage/literature_storage.py`, `storage/sample_context_evidence/literature_aggregation_storage.py`, `storage/sample_context_evidence/literature_sheet_updates.py`, `readers/sample_context_evidence/literature_aggregation.py`, `grading/sample_context_evidence/literature_required_grading.py` and `prompts/literature_prompt.py`. |

The two pre-`078b77668` designs (the ordinal 0 to 4 rubric and the interval subscore) are **superseded, not lost**.
`docs/A108_NUMERICAL_SUBSCORING_PLAN.md` §1 records the owner's withdrawal of category grades
(`CATEGORY_SCORE_WITHDRAWAL_2026-10-23_001.md`). It replaces them with "the number of distinct source-grounded
contextual observations that have been assessed as supporting or conflicting". The rubric's "Native temperature, pH
and salinity are returned unchanged, not converted into a confidence score" survives in the grader criteria
(`ph_circumstance`, `thermal_circumstance`, `ionic_water_property`).

## Items that are WEAKER, LOST or VIOLATES

In every LOST row below, the code that implements the decision is unchanged. What was lost is the owner's written
statement of the decision: the inline comment, or the cell meaning.

| # | Episode / library path | Old file @ commit | Old text (exact) | Current file | Class | Decision (one sentence) | Where it belongs now |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | library, A108 grader | `gene_annotation_episode/literature_a108_grading.py` @ `078b77668` (also `root/library/…` @ `60889621e`) | `# These common identities are prerequisites, not scored checklist items.` (above `COMMON_CRITERIA`) | `episode_support/literature/grading/literature_grading.py` (no comment) | LOST (statement) | The four common criteria (source subject, original observation, context applicability, function-context connection) gate a relation; they are not scored items. | Comment or docstring on `COMMON_CRITERIA` in `literature/grading/literature_grading.py` |
| 2 | library, grading inputs (subscoring sheet reader) | `gene_annotation_episode/literature_a108_grading_inputs.py` @ `078b77668` | `# A quoted phenotype and its representations are an observation unit,` / `# not extra quantitative measurement rows created by this source reader.` | `episode_support/literature/inputs/literature_grading_inputs.py` (`measurement_keys = []`, no comment) | LOST (statement) | An A108 sheet counts observations, so a quoted phenotype creates no measurement rows. | Comment on `observation['measurement_keys'] = []` in `literature/inputs/literature_grading_inputs.py` |
| 3 | library, subscoring sheet storage | `gene_annotation_episode/literature_a108_grading_storage.py` @ `078b77668` | `# These references denote original observations, not merely` / `# entities with the same label. Two result statements at` / `# different source locations must remain distinct even when` / `# their literal labels happen to be identical.` | `episode_support/literature/storage/literature_grading_storage.py` (`original_identity`, no comment) | LOST (statement) | The identity of an original observation is its source anchor, never its label. | Comment in `original_identity` of `literature/storage/literature_grading_storage.py` |
| 4 | same | same | `# Same actual publication metadata survives fresh source acquisition` / `# IDs. Different anchors are not merged by their label. Other` / `# representations reuse the original observation ref explicitly;` / `# semantic equivalence is not guessed from prose.` | same | LOST (statement) | A re-acquired source keeps its publication identity, and other representations join an observation only through an explicit reference, never by matching prose. | same |
| 5 | library, main scoring sheet | `gene_annotation_episode/literature_a108_aggregation.py` @ `078b77668` (also `root/library/…` @ `60889621e`) | `# A changed interpretation of one original observation/claim is a revision,` / `# not independent support and conflict. Different contextual claims may` / `# legitimately give the same original observation both directional roles.` | `episode_support/literature/readers/sample_context_evidence/literature_aggregation.py` (`relation_directions`, no comment) | LOST (statement) | On one observation and claim, a re-interpretation is a revision and cannot count as both support and conflict; across different claims it can. | Comment on `relation_directions` in `literature/readers/sample_context_evidence/literature_aggregation.py` |
| 6 | same | same | `# Use original sets rather than adding domain/child counts. A single` / `# observation can legitimately belong to both directional sets.` | same (`annotation_scalar`, no comment) | LOST (statement) | The overall score comes from the union of original observation sets, never from summing domain or child counts. | Comment in `annotation_scalar` of the same file |
| 7 | library, required grading (reason coupled with its sheet) | `gene_annotation_episode/literature_required_grading.py` @ `078b77668` | `# … Merely` / `# sharing a paper, a support ref or an anchor does not establish this` / `# relationship. A108 original observations retain their own identities.` | `episode_support/literature/grading/sample_context_evidence/literature_required_grading.py` (no comment) | LOST (statement) | Unlike an A105 result, an A108 observation is never folded into another one because the two share a paper, reference or anchor. | Comment at the `contextual` branch of `literature_required_grading.py` |
| 8 | same | same | `# An explicit original-result link or its exact authenticated anchor` / `# identifies the experiment/observation; source identity alone does not.` | same | LOST (statement) | Matching a sheet to an observation needs an explicit link or an authenticated anchor, not just the same source. | same |
| 9 | same | same | `# Descriptive metadata remain committed context. Only actual` / `# results and scientific interpretations require a matching` / `# sheet. Their already saved observation, hypothesis and` / `# experiment/original-result links supply the association;` / `# the episode does not enumerate that association again.` | same | LOST (statement) | Only results and interpretations need a matching grading sheet; metadata never does. | same |
| 10 | library, automatic sheet updates | `gene_annotation_episode/literature_sheet_updates.py` @ `078b77668` | `# A received child's main sheet and a receiver's calculation over its` / `# own admitted inputs have different owners; neither replaces the` / `# other's scientific scope merely by arriving later.` (applies to `literature.a108.aggregation`) | `episode_support/literature/storage/sample_context_evidence/literature_sheet_updates.py` (no comment) | LOST (statement) | A child's A108 main sheet and the parent's own main sheet are separate, and neither replaces the other. | Comment in `_family` of `literature_sheet_updates.py` |
| 11 | same | same | `# A later child assessment does not grant its unreturned` / `# components.  Invalidate the dependent current value, retain` / `# its historical calculation and exact declared bindings, and` / `# let a later authentic receipt make the same dependency usable.` | same | LOST (statement) | When a dependent main-sheet value loses its input, it becomes unavailable rather than being guessed, and only a returned component restores it. | Comment in `_refresh_dependents` of the same file |
| 12 | same | same | `# The scientific bindings belong to the existing selected` / `# main sheet.  Missing bindings remain explicit, never chosen` / `# by magnitude, recency or the order of grader components.` | same | LOST (statement) | When the main sheet is refreshed, its inputs are never picked by size, recency or grader order. | Comment in `_refresh_main` of the same file |
| 13 | same | same | `# No semantic equivalence is guessed for unrelated source selections.` / `# An already bound input revision follows its registered family.` | same | LOST (statement) | A sheet revision is matched to its family only through registered bindings. | Comment in `_family` of the same file |
| 14 | library, cell meanings of the two A108 sheets | `root/a108/library/literature_numerical_contracts.py` @ `97308b94c` (also `gene_annotation_episode/literature_numerical_contracts.py` @ `078b77668`) | `'literature_a108_grading_cells': 'Requested purpose-specific A108 numerical counts of supporting, conflicting, overlapping and unresolved original organism-context observations. Preserve candidate and actual target organism/context, source-specific scientific criteria, original observation identity, qualified transfer and conditions. Evidence amount counts the supporting/conflicting union once; net support is separate. Repeated source representations add no observation, and these counts are not annotation probability or the Episode progress scalar.'` | `episode_support/literature/forms/literature_numerical_contracts.py` has no A108 entry | LOST | Defines what a returned subscoring cell means: separate counts, the union counted once, and not a probability or a progress scalar. | `RETURN_MEANINGS` in `literature/forms/literature_numerical_contracts.py`, or the description of `grading_cells_schema()` in `literature/storage/literature_grading_storage.py` |
| 15 | same | same | `'literature_a108_aggregation_cells': 'Requested A108 main evidence scoring sheet components for physiology, environment, availability, localization and overall. Each retains evidence amount and separate support/conflict/overlap/net/unresolved counts, recomputed from possessed original observation unions. Shared observations across sources, children or domains count once. Unselected domains remain unavailable; source context, actual contributors and unresolved relationships remain explicit.'` | none | LOST | Defines what a returned main-sheet cell means: domain and overall unions, shared observations counted once, and unselected domains marked unavailable rather than zero. | The same `RETURN_MEANINGS`, or the description of `aggregation_cells_schema()` in `literature/storage/sample_context_evidence/literature_aggregation_storage.py` |
| 16 | every literature episode under `root/a108/sample_context_evidence/published_evidence_assessment/**` (7 episodes; cell field descriptions in each `messages/final_to_parent.py`) | row 14/15 text @ `97308b94c` | (as rows 14 and 15) | e.g. `source_coverage_improvement/messages/final_to_parent.py`: `'The saved A108 subscoring cells of the requested components'`; others: `'Exactly the requested A108 contextual grading components of the sheets this episode saved, with their actual source, organism and condition qualifications'` | WEAKER | Same decision as rows 14 and 15; the returned cell field no longer says what is counted or what the counts are not. | Take the field description from the library meaning (row 14/15) instead of writing per-episode text |

No in-scope item is VIOLATES. Every grader string, criterion question, cell component, sheet schema, operation
description and population catalog entry is unchanged from `078b77668`. Rows 1 to 13 are the only gaps there: inline
comments that the reformatting removed.

## PRESERVED / RESHAPED (in scope)

Library (shared by every A108 episode):

- `literature_grading.py` is PRESERVED (all string constants identical to `078b77668`). It holds the 11 grader types,
  `DOMAIN_BY_TYPE`, `COMMON_CRITERIA`, `SPECIFIC_CRITERIA`, the 44 `CRITERION_QUESTIONS`, `ORIGINS`, `RELATIONS`,
  `TARGET_RELATIONSHIPS`, `COMPONENTS` (`support_count`, `conflict_count`, `overlap_count`, `evidence_amount`,
  `net_support`, `unresolved_count`) and the sheet schema with `annotation_credit: null`.
- `literature_grading_inputs.py` is PRESERVED. It holds the `target_context_ref` and `target_identity` descriptions.
  Only the old-runner `legacy=` parameter was dropped.
- Main scoring sheet: `literature_aggregation.py` is PRESERVED (`COMPONENTS = (*DOMAINS, 'overall')`).
- Storage: the grading storage `OPERATION_DESCRIPTION` and the aggregation storage `OPERATION_DESCRIPTION` are
  PRESERVED. `literature_storage.py` (A108SheetRepository) is RESHAPED: the old SQL ledgers became declared tables.
- `literature_required_grading.py` is PRESERVED. Only the `account_invocation` argument was dropped.
- The grader table and grading paragraphs of `A108_CONTEXT_TASK` and the text of `A108_GRADING_TASK` and
  `A108_AGGREGATION_TASK` in `prompts/literature_prompt.py` are PRESERVED (`_GRADER_DESCRIPTIONS` is identical to
  `078b77668`).
- `literature_population_catalog.py` (`literature.a108_grading.populate` and `literature.a108.aggregate`) is PRESERVED.
- Automatic dependent-sheet refresh is PRESERVED: `literature_sheet_updates.publication` is installed by
  `LiteratureRateRepository.__init_subclass__`.

Which sheet each episode writes:

| Episode | Count | Notes |
| --- | --- | --- |
| `sample_context_evidence` (head) | 1 RESHAPED | `reason` now couples the commit with the A108 contextual grading sheet (`LiteratureA108GradingRepository`). The old head committed without a grader. This is the AGENTS.md A108 requirement. |
| `published_evidence_assessment` | 3 RESHAPED | Grading sheet through `reason`; `literature_a108_grading_populate`; `literature_a108_aggregate`, with the aggregation reading grading cells through `read_cells`. These were the old `grading/contextual_interpretation.py`, `grading/contextual_subscoring.py` and `scoring/contextual_main_sheet.py`. |
| `evidence_search_strategy_improvement` | 3 RESHAPED | Same as `published_evidence_assessment` |
| `source_relevance_assessment` | 3 RESHAPED | Same |
| `source_evidence_examination` | 3 RESHAPED | Same |
| `table_evidence_extraction` | 3 RESHAPED | Same |
| `passage_evidence_extraction` | 3 RESHAPED | Same |
| `source_coverage_improvement` | 3 RESHAPED | Same |

Counts: PRESERVED 9 (library). RESHAPED 22 (1 library and 21 in episode files). LOST 15 (13 statements of
decisions the code still implements, and 2 cell meanings). WEAKER 1 (the cell-field descriptions in 7 episodes).
VIOLATES 0.
