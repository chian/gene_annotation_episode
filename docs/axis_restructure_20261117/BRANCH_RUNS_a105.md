# Branch runs, axis A105 (real model)

Runner: one branch only, `source_evidence_examination` (SEE) commissioning ONE leaf, `table_evidence_extraction`.
Path: `root/a105/experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination`.
Test written (no model-run test of the branch existed that forces the table child):
`SEE/tests/test_branch_source_evidence_examination_model_run.py` (two `@pytest.mark.model_run` tests; world built from `SEE/tests/grading_world.py`:
the one assay table in the first 331 bytes, followed by a long tabular "Table 2. Purification summary" filler; task `a105_experiments`, one experiment).
Run dirs (the launcher refuses a pre-made dir: `runs/brm_a105_1` is an aborted launch with nothing in it): `runs/brm_a105_2`, `_3` (model-driven attempts),
`_4` (run_unit commission). Each has `stdout.log`; the pytest tmp (journal, model_calls/call-*) is under `runs/brm_a105_N/tmp/`.

## Branch source_evidence_examination -> table_evidence_extraction: model-driven delegation FAIL (child slot not chosen), forced commission PASS

### Attempt 1 (`runs/brm_a105_2`, test `..._delegates_the_table_to_its_child_and_resume_replays`): FAIL (assertion only)
SEE units: `child source_coverage_improvement` (credit 1.0). The model answered the first decision (call-00001) with the ordered-reading child,
window offset 0 limit 8192, and a long objective. It never chose the table child although the commissioner's message named it.
The run itself completed (ended by yield_stop after the child's credit 1.0 met the target).

### Attempt 2 (`runs/brm_a105_3`, same test, world changed to a table-shaped long source): FAIL (assertion only)
SEE units in order: `tool source_read` (completed), `child passage_evidence_extraction` (credit 1.0). Again not the table child.

Classification: INSTRUCTIONS / EPISODE (internal_summary). Diagnosis: the commissioner's `message['objective']` is read by
`messages/read_from_parent.py` (returns `'message': message`, line 199) but `messages/internal_summary.py` never puts it in the decision context
(context keys of call-00001: goal, scope, literature_assignment, literature_source_custody, own_literature_outcomes, literature_history_meaning,
source_examination_goal, credit_binding, last_local_outcome, held_record_refs, assay_sheets, child_returns, child_options, tools, time_accounting,
action_yields; no message). `source_examination_goal.objective` is `view.goal` (the static GOAL). So the model cannot be told which child to use and
had only the three one-line `child_options` descriptions; a model with an exact-window source chooses by those. The same drop exists in the leaf
(`table_evidence_extraction/messages/internal_summary.py`, context keys have no objective): the objective SEE writes in `msg_to_child` (`objective=arguments['objective']`,
`message={'objective', 'task_key'}`) never reaches the child's model (my string "Grade the assay the table reports for the proposed function." occurs 0 times in the child's request.json).
Suspected fix: add the parent's message objective to the summary of SEE and of each leaf (`read_from_parent` already returns it) and show it in `internal_summary` (a controlled/own text from the commissioner is the only
message field; if it must stay out of the model for the controlled-messaging rule, then the decision to delegate has to come from `child_options` descriptions: make the table child's description say when it is the right one).

### Attempt 3 (`runs/brm_a105_4`, test `..._table_commission_by_run_unit_with_the_real_model_in_the_child`): PASS, by `run_unit(ChildCall('table_evidence_extraction', ...))`
(done as the task allows after two failed attempts to have the model pick the child.)
- SEE journal units: 1 child unit `table_evidence_extraction_0`, report credit 1.0, completion `ended_by: yield_stop`, `units_consumed: 3`.
- Child (real model, 3 calls): `source_read` offset 0 limit 331 (completed, credit 0.0), `source_read` offset 331 limit 4096 (completed, credit 0.0 - it read past its selected window into the filler table),
  `reason` (commit + `evidence_processing.kind: graded` with one `activity_rate` grading; credit 1.0). Child stopped by its yield estimator.
- SEE then ran on (`run()`): its own controller stopped at once (target 1.0 met); no further model call by SEE.
- Return admitted under RETURN_FORM (`EPISODE.return_form.select(()).admit(result, 'return') == result`); child report keys exactly
  `slot, credit, assay_sheets, aggregation_sheets, counts, lead_source_refs, screening_covered`; child result keys exactly `{credit, finding}`; the finding carries only controlled features and the sheet reference
  (counts: `assay_count` 1, `assay_count_with_evidence_ratio` 0).
- Resume: `resume(...).run()` returned the same result and the model call count was unchanged (replay without new model calls). PASS.
- Tool use: sensible sequence (read window, read on, reason); no repeated identical calls, no invalid arguments, no rejection.

### Observations that are not failures but the fixer should see
1. Grading quality (INSTRUCTIONS/WORLD-visible): the leaf model graded the assay with all nine `quantities` set to `null` and all criterion statuses `unknown`, although the window it had just read
   states effect 12.5 U/mg, variance 0.25 U/mg_squared, recovery, signals, conditions and predictions as plain numbers. The sheet shows `effect_status: unavailable`, `effect_unit: unsupported_for_quantity_kind`,
   `source_log_evidence_ratio_status: unavailable`, and the leaf still earned the full credit 1.0 and stopped. So an all-unknown sheet earns the whole credit unit; the numbers the table did contain were never graded.
   The model apparently did not manage the `source_number` witness form (`{kind: source_number, number: {witness, number_start, number_end}, unit, origin}`); `reason`'s description (`literature_reasoning.REASON_DESCRIPTION`)/`grading_section` may need a worked example of the source_number form.
   Whether the credit for an all-unavailable sheet is intended is a decision for `literature_task_answers.task_credit`.
2. The leaf read 4096 bytes beyond its selected window (offset 331): nothing in the leaf restricts a read to its selection (`selection` is context only), which matches the goal text ("a supplied reading selector is context").
3. `AXIS_WAVE_BLOCKERS_a105.md` does not exist in docs/axis_restructure_20261117; only LOST_CONTENT_a105.md was available.

## After the fix (19 November 2026): `runs/fixexa_4` to `runs/fixexa_10`

What changed and the recipe for the other axes: `EXAMINATION_PROMPT_RECIPE.md`. The branch test file now has three
tests; none asserts that the model delegates (the examination holds the ordinary tools by design).

| Run | Test | Units of the examination | Result |
|---|---|---|---|
| `fixexa_9` | examination alone, one table before a long filler | `state_query`, `source_read`, `state_query`, `reason` (failed), `source_locate` | PASS; no delegation; credit 0.0 (controller stopped after five units without credit) |
| `fixexa_6` | same test | `state_query`, `source_read`, `state_query`, `reason` (completed) | PASS; no delegation; credit 1.0; nine quantities entered, ten criteria unknown, all ten classified justified |
| `fixexa_9`, `fixexa_6` | commission by `run_unit(ChildCall('table_evidence_extraction', objective grade_reported_experiment))` | one child unit | PASS twice; child credit 1.0; every decision request of the child carries `commission.objective`; effect 12.5 U/mg populated; the child's unknown criteria classified by its own unit (one typed model call) |
| `fixexa_9` | long source: three assay tables, 180 passages, three experiments | 22 units: own grading of experiment A, then six commissions of `table_evidence_extraction` | PASS; the model delegated six times; 2.0 of 3 (A by the examination, B by the first child; five later children stopped after four to six units without credit and without a `reason`) |
| `fixexa_6` | same test | 6 units, one commission of `table_evidence_extraction` | PASS; the model delegated once; 0.0 of 3 (the child's `reason` failed on commit errors and its controller stopped it) |
| `fixexa_5`, `fixexa_7`, `fixexa_9` | table leaf: scripted all-unknown grading after a real read, classified by the real model | `source_read`, `reason` | PASS three times, same answer: nine quantities and the prediction model unjustified, eleven criteria justified, credit 11/21 = 0.524 (it was 1.0) |

Observations for whoever tunes next (not changed here):
1. At the test setting `cost` 0.1 a completion controller stops an episode after about four units without credit. A
   leaf whose first `reason` fails after two lookups often ends with credit 0 (`fixexa_6` long run, `fixexa_7` leaf alone).
2. A commission names every record the examination holds, so a leaf commissioned after the examination graded an
   experiment starts with that sheet as its initial credit and returns it in its `credit` and finding
   (`fixexa_9`: child credit 2.0 for one experiment of its own; five later children returned 1.0 with nothing new).
3. `reason` failures seen after the fix are commit errors, not null quantities: `required_grading_interpretation_uncovered`
   (a new `literature_result` reference no grading covers), `subject_label_not_in_source_span`,
   `required_grading_unresolved_alias`, `literal_source_number_required`.
