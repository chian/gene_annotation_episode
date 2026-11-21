# Recipe: the examination episode and its leaves, per axis (19 November 2026)

What was changed in A105 `source_evidence_examination` (SEE) and its three leaves (`table_evidence_extraction`,
`source_coverage_improvement`, `passage_evidence_extraction`), and the exact change for the copy of these four
episodes in each other axis. No other axis was edited. SEE below stands for
`root/<axis>/<head>/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination`.
The A105 files are the worked example; read them beside this recipe.

Three rules of the owner decide the shape (19 November 2026):

1. **A parent holds the ordinary tools by design.** A child is a narrower investigation that needs iteration of its
   own and passes back a summary. The prompt says when delegating is the right choice (a whole table, many passages,
   a long document in order) and prescribes no child. No test asserts that the model delegates.
2. **Controlled messaging.** The objective a commissioner gives is one value of a fixed vocabulary that the
   commissioned episode declares; the commissioned episode shows its model the value with its own meaning of it. No
   text one model wrote is shown to another episode's model.
3. **The judge of a grading is credit assignment.** It is automatic (the model never selects it, no tool offers it),
   it runs as the tail of the same unit that saved the sheet, its function lives in the episode's `credit.py`, its
   answer is a closed typed schema, its result is a record the episode holds, and `credit(summary, records)` stays a
   pure read of that record.

## Part 1. The commissioner's objective reaches the model (all nine axes)

### What A105 has now

| File | Change |
|---|---|
| `SEE/messages/read_from_parent.py` | `OBJECTIVES = {value: meaning}` (`evidence_in_table`, `evidence_in_passages`, `evidence_location_unknown`). `read_from_parent` returns `'objective': {'value': message['objective'], 'meaning': OBJECTIVES[message['objective']]}` in place of `'message': message`. A value outside the vocabulary fails there with its `KeyError` (a wrong commission fails; nothing checks ahead). |
| `SEE/messages/internal_summary.py` | `'commission': {'objective', 'objective_meaning', 'task', 'proposed_annotation_ref'}`; `source_examination_goal.objective` is the commission's value (it was `view.goal.as_record()['objective']`, which at entry is the static goal and under a parent was the parent model's text). |
| `SEE/task.py` | `BRIEF` is the first text of `instructions()`: what the episode is for, what the commissioner asked (`context.commission`), the own tools, the children and when delegating is the right choice, what earns credit. `decide` puts `commission` in the context. `OBJECTIVE` of a child commission is `{'enum': ['grade_reported_experiment', 'find_applicable_evidence']}` (it was free text). `CHILD_ARGUMENTS` descriptions say what each child does and when it is the right choice. The replaced span of the library text starts at `A commissioned child returns ONLY the parent's typed form.` so the `report_update` and `redeliver_report` paragraphs (actions that do not exist) are gone. |
| each leaf `messages/read_from_parent.py` | Its own `OBJECTIVES` (`grade_reported_experiment`, `find_applicable_evidence`, meanings worded for that leaf); `'objective': {...}` in the parent input in place of `'message': message`. |
| each leaf `messages/internal_summary.py` | `'commission': {'objective', 'objective_meaning', 'task', 'proposed_annotation_ref', 'selection'}`; where a `literature_goal_plan` exists its `objective` is the commission's value. |
| each leaf `task.py` | `BRIEF` first (what the leaf is for, what each objective value asks, the tools, credit); `commission` in the `decide` context; the same replaced span. |
| `source_relevance_assessment/task.py` (the commissioner of SEE) | `OBJECTIVE` of its page child is the enum of SEE's three values with their meanings. Nothing else of that episode was changed. |

### The same change in each other axis

In every axis the four episodes get: (a) `OBJECTIVES` in `messages/read_from_parent.py` of the commissioned episode
and `'objective': {'value', 'meaning'}` in the parent input; (b) `commission` in `internal_summary` and in the
`decide` context; (c) a `BRIEF` first in `instructions()`; (d) in the commissioner's `task.py` an enum of the child's
values in place of a text objective; (e) tests pass a vocabulary value as `message['objective']`. What differs per
axis is the starting point (read from the files on 19 November 2026):

| Axis | SEE `msg_to_child` today | What the leaf's model sees of the objective today | Exact change |
|---|---|---|---|
| A101 `sequence_homology_evidence` | `ChildMessage(objective=OBJECTIVES[slot], message={'slot', 'source_ref'})`: a code sentence per slot | nothing (`internal_summary` of the leaves has no objective; `read_from_parent` keeps `'message': message` unread) | Keep the per-slot code objective as the `ChildMessage.objective`. Add `message['objective']` with a leaf vocabulary value chosen by SEE's model from an enum (SEE `task.py` child input), and do (a) to (c) in the three leaves. For SEE itself do (a) to (d) against `source_relevance_assessment`. |
| A102 `structural_homology_evidence` | `ChildMessage(objective=OBJECTIVES[slot], message={})` | nothing; the leaves' `read_from_parent` does not keep the message | As A101; the leaves' `read_from_parent` gain the `objective` key. |
| A103 `gene_context_evidence` | `ChildMessage(objective=arguments['objective'], message={'scope'})`: the SEE model's text | SEE shows its own `child_reports[].objective` (its model's text); the table leaf keeps `'message'` unread | Replace the text objective by an enum in SEE `task.py` (line 397 passes `arguments['objective']`), put the value in `message['objective']`, then (a) to (c) in the leaves and (a) to (d) for SEE. |
| A104 `evolutionary_history_evidence` | `ChildMessage(objective=arguments['objective'], message={'slot', 'source_ref'})`; `CHILD_INPUT` declares `'objective': TEXT` | SEE shows `child_reports[].objective`; leaves keep `'message'` unread | As A103 (`CHILD_INPUT` in SEE `task.py` line 187 becomes the enum). |
| A106 `perturbation_evidence` | `ChildMessage(objective=OBJECTIVES[slot], message={})` | nothing; leaves keep `'message'` unread | As A101. |
| A107 `partner_presence_evidence` | `ChildMessage(objective=OBJECTIVES[slot], message=message)` | nothing | As A101; add `objective` to the message SEE already builds. |
| A108 `sample_context_evidence` | `ChildMessage(objective=arguments['objective'], message={'scope'})`: the SEE model's text; child input `'objective': TEXT` (`task.py` line 283) | SEE: `literature_goal_plan.objective = view.goal.as_record()` and `commission_message = parent['message']`; table leaf: `view.goal.as_record()`; ordered leaf: `parent['message']`; passage leaf: its static `GOAL` | As A103. The three different sources of `literature_goal_plan.objective` all become the commission's vocabulary value; `commission_message` is dropped (the message holds only the value and the scope). |
| A110 `biochemical_feasibility_evidence` | `ChildMessage(objective=OBJECTIVES[slot], message={'page_source_ref'})` | nothing; leaves keep `'message'` unread | As A101. |

Vocabularies. SEE: where the commissioner expects the evidence (`evidence_in_table`, `evidence_in_passages`,
`evidence_location_unknown`). Leaf: what the commissioner knows about the selection (`grade_reported_experiment`,
`find_applicable_evidence`). An axis whose leaves do not grade (A101, A102, A103, A107) names its leaf values after
what its leaves return (for example `extract_reported_finding`, `find_applicable_evidence`); the vocabulary is the
commissioned episode's own and is copied, not shared.

The `BRIEF` of a parent states, in this order: THIS EPISODE (one source, one task, one annotation); WHAT THE
COMMISSIONER ASKED (the value tells where to look first and prescribes no tool and no child); YOUR OWN TOOLS (ordinary
one-off work is done directly); THE CHILDREN (a child is a narrower investigation that iterates and passes back a
summary; delegating is right for a whole table, many passages, a long document in order; one read that shows the
evidence in full needs no child); CREDIT. Copy the text of `SEE/task.py` `BRIEF` and change the axis words.

Tests. The branch test of A105
(`SEE/tests/test_branch_source_evidence_examination_model_run.py`) is the model: the model-driven run reports its
units and asserts only that the request carries the commission and the brief; the commission path is exercised by
`run_unit(ChildCall(...))`, which asserts that every decision request of the child carries the commissioner's value;
a long source (several tables, many passages) reports whether the model delegates and asserts nothing about it.

## Part 2. The grading that leaves stated fields unknown, and its credit

### The defect (A105, `runs/brm_a105_4`)

The table leaf read a window that prints nine quantities and saved a sheet with all nine null and every criterion
`unknown`; the sheet earned the full unit. Two causes:

* **Instructions.** The grader arguments are a JSON-encoded string whose schema (86 KB) is only in the description
  of that string; the `source_number` operand (byte witness, in-witness character positions, unit witness) had no
  example; and the owner's grader text says "Save an initial partial subscoring sheet ... then refine", while the
  credit rule paid the whole unit for the first sheet and the completion controller then stopped the episode.
* **Credit.** One unit per commissioned experiment whose sheet exists and matches a current assessment; the content
  of the sheet did not enter.

### What A105 has now

| File | Change |
|---|---|
| `episode_support/literature/prompts/experimental_activity_evidence/literature_grading_instructions.py` | `QUANTITY_ENTRY`, shown first in `grading_section()`: the keys of the argument object, null means "the examined source does not state it" and nothing else, the `source_number` form with one worked example, where byte offsets come from, an invalid operand is corrected and not replaced by null; and what a commit needs to be accepted (every observation, assessment and new assay or result reference covered by a grading of the same commit; the commissioned experiment reference reused; a label copied from inside its anchor). |
| `episode_support/literature/grading/experimental_activity_evidence/literature_unknown_classification.py` (new) | The pieces of the typed classification: `graded_fields`, `unknown_fields`, `classification_schema` (closed: one required property per unknown field, each `justified` or `unjustified`), `classification_request` (instructions, context, schema), `classification_result` (the answer admitted against the schema), `classification_record` and `held_classification` (a `source` record of provider `literature.a105.unknown_classification`, read through custody), `classification_features` (counts and a status), `graded_share`, `examined_windows`, `window_texts`. |
| `episode_support/literature/readers/experimental_activity_evidence/literature_assay_grading_features.py` | Five features per sheet: `graded_field_count`, `unknown_field_count`, `unknown_classification_status` (`classified`, `not_classified`), and, when classified, `justified_unknown_count` and `unjustified_unknown_count`. They are in the finding every A105 literature episode returns. |
| `episode_support/literature/grading/experimental_activity_evidence/literature_task_answers.py` | `classified_task_credit` and `classified_credit_binding`. For `a105_experiments`: `credit_unit` times the sum over answered experiments of `graded_share` of the experiment's current sheet. `task_credit` is unchanged and is what the four A105 ancestors still call. |
| each of the four `credit.py` | `async def classify_unknowns(outcome, scope, windows, ctx)`: for each sheet the unit saved that leaves a field unknown, one `ctx.model.complete` (recorded with the unit, replayed on resume) with the closed schema; the validated result is saved with `ctx.store.artifact` and `ctx.store.put('source', ...)`, so the episode holds it as produced. `credit` is `classified_task_credit(summary, records)`: a pure read. |
| each of the four `task.py` | `reason` is `async` and ends with `return await classify_unknowns(outcome, scope, arguments['examined_windows'], ctx)`. `action` passes `summary['examined_windows']` in the tool envelope. No tool is added and the model is not told to call anything. The `BRIEF` states the credit rule. |
| each of the four `messages/internal_summary.py` | `'examined_windows': examined_windows(view.outcomes)` (the spans of the episode's own completed `source_read` units) and `classified_credit_binding` for the binding shown to the model. |

The credit rule. A sheet has fields: the nine quantities, the prediction model and the criteria it carries (21 for a
sheet with eleven criteria). `graded_share = (entered fields + unknown fields held justified) / all fields`. An
unknown field held unjustified earns nothing; an unknown field that is not classified earns nothing (no window was
read, so nothing justifies it); a sheet of nothing but unjustified unknowns earns nothing; a sheet whose unknowns are
all justified earns the unit (the partial or unresolved grading AGENTS.md requires for what a source does not give).

### A108 `sample_context_evidence`: the same classifier

A108 has the same required grading (`episode_support/literature/grading/sample_context_evidence/literature_required_grading.py`,
called by `reason` in SEE `task.py` line 571 and in the three leaves) and the same kind of credit: `credit.py`
`assessment_answers` counts one current retained assessment anchored in the task's sources, whatever its contextual
sheet leaves unknown. Apply the pattern:

1. Library, under `episode_support/literature/grading/sample_context_evidence/`: a copy of
   `literature_unknown_classification.py` whose `graded_fields` and `unknown_fields` read the A108 contextual
   grading arguments (the fields its subscoring sheet defines: the contextual observation's components and the
   interpretation criteria of the contextual grader), with A108 questions for each field, its own provider
   (`literature.a108.unknown_classification`) and the same `classification_schema`, `classification_request`,
   `classification_result`, `classification_record`, `held_classification`, `classification_features`,
   `graded_share`, `examined_windows` and `window_texts`. A108 keeps original observation identities explicit: the
   request lists the observation the sheet grades by its reference, and the classification is per sheet.
2. Features: add the five classification features to the A108 sheet features
   (`grading_features` in `episode_support/literature/readers/sample_context_evidence/literature_context_findings.py`) so the finding
   carries them.
3. In each of the four A108 episodes: `classify_unknowns` in `credit.py` (the A105 function with the A108 library
   names); `reason` in `task.py` made `async` with the classifier as its tail after
   `literature_required_grading.execute` returned; `examined_windows` in `internal_summary` and in the tool
   envelope of `action`.
4. Credit: in each `credit.py`, an `assessment` answer earns `credit_unit * graded_share(features of the sheet that
   grades the answering assessment)` in place of `credit_unit`. A108's `credit.py` files are private copies of the
   whole rule (they do not call a library credit), so the change is made in each of the four files.
5. Tests as in A105 `table_evidence_extraction/tests/test_grading.py`: offline, a classification record supplied
   through custody (`received_record_refs`) to a run whose scripted `reason` leaves fields unknown with no window
   read; with the real model, a scripted all-unknown grading after a real `source_read`, classified by the tail.

### A106 `perturbation_evidence`: the score judgment becomes this

`literature_a106_score_judgment` is today a task tool of SEE and of the leaves (`task.py`: `async def
literature_a106_score_judgment(arguments, ctx)` -> `literature/storage/literature_population_route.py`
`score_judgment`: `prepare_judgments` -> `ctx.model.complete` -> `complete_judgment`). The model selects it; it is
credit assignment and must not be a task action. The change:

1. Remove `literature_a106_score_judgment` from `TOOLS`, from the offered names and from the catalog of each A106
   episode that has it, and delete the tool function. Delete `score_judgment` from `literature_population_route.py`.
2. In each of those episodes' `credit.py` add `async def judge_scores(outcome, envelope, ctx)`: the body of the old
   `score_judgment` (the repository's `prepare_judgments`, one `ctx.model.complete` per request with
   `generation_schema(request['output_schema'])`, `complete_judgment`), returning the unit's outcome with the
   judgments' controlled result.
3. Call it as the tail of the unit that saves or revises an intervention assessment (the population tools of the
   intervention family and `reason`), after the sheet is saved and outside its transaction (`prepare_judgments`
   already refuses to run inside one).
4. `credit(summary, records)` reads the saved judgment (the A106 final subscore rows) and does not make it.
5. The instructions lose every sentence that tells the model to request a score judgment.

### The other axes

A101, A102, A103, A104, A107 and A110 were not examined for this defect beyond their `credit.py` imports. Where an
axis's credit counts a saved sheet or an accepted assessment without reading what the sheet leaves unknown, the same
three steps apply: the typed classifier as library pieces under that axis's name, `classify_unknowns` in each
`credit.py` called as the tail of the unit that saves the sheet, and the share in `credit`. Where an axis's credit
already reads the sheet's content (A101 `scoring`, A103 `A103ContextCredit`, A110 `investigation_finding_features`),
check first whether an all-unknown sheet earns anything; the classifier is needed only if it does.

## Not done in A105 (same axis, outside the four episodes)

The four ancestors (`experimental_activity_evidence`, `published_evidence_assessment`,
`evidence_search_strategy_improvement`, `source_relevance_assessment`) still call `task_credit` (one unit per
answered experiment) and their own `reason` has no classifier tail. A sheet a descendant returns carries its
classification features, but these ancestors do not read them for credit. The change for each is the A105 leaf
change: `classify_unknowns` in `credit.py`, the tail in `reason`, `examined_windows` in the summary and the
envelope, `classified_task_credit` and `classified_credit_binding`.
