# Extract port recipe: `execution_result_acquisition` on the job services (19 November 2026)

The A101 extract episode `root/a101/sequence_homology_evidence/execution_result_acquisition` acquires the plain
file result of a job on the built `JobAccess`, with the real model, for a finished job and for a job that has not
ended. It is the worked example. This file says, for every other `execution_result_acquisition` episode, which
files an agent changes and how. Nothing outside A101 was edited.

Read first: `LAUNCH_MONITOR_EXTRACT_MECHANICS.md` (sections 3, 6, 7 and "Provided now"), `TRANSFORM_GUIDE.md`,
`BRANCH_FIX_BLOCKERS_a101.md`, and in the A101 episode: `task.py`, `messages/internal_summary.py`,
`messages/final_to_parent.py`, `messages/read_from_parent.py`, `credit.py`, `goal.py`, `tests/plain_world.py`,
`tests/test_plain_results.py`, `tests/test_branch_execution_result_acquisition_model_run.py`.

## 1. What the port is

Owner rule: the model is the router. It selects one defined operation with controlled operands; code carries it
out. No operation runs a command the model wrote, and no handoff label (`results_operation: exec_command`) is read.

| Old (carried, did not run) | Now (A101) |
|---|---|
| `job_access.observe_target(target, key=...)` (raised) | `ctx.services['job_access'].check(ctx, handoff_ref)`: the service writes the check row; the tool returns the service's outcome |
| `job_access.read_file(target, path=, offset=, limit=, key=...)` for the first windows (raised) | `ctx.services['job_access'].fetch(ctx, handoff_ref, names=[...])`: each requested file is an artifact the Episode holds, the service writes the closure row; then the first window of each requested path is read from the fetched artifact with `ctx.store.open_artifact(ref)` |
| `read_file` for one selected window | a window of the already fetched artifact, read with `ctx.store.open_artifact(ref)`; offered only once a file is fetched; `path` is an enum of the fetched paths |
| a window body with `bytes_base64` | a window `{'path', 'artifact_ref', 'offset', 'returned_bytes', 'size_bytes', 'sha256'}`: the bytes stay in the fetched artifact |
| result body `execution_result_information_v2` with run id, episode id, operation key, scope, target, observation, failures, acquisition origin | body `execution_result_information_v3`: `{'version', 'assignment', 'tool_name', 'closure_ref', 'windows'}`, kept as an artifact with a `source` record of provider `episode.execution_result` over it, in one `ctx.store.transaction()` |
| the target read from the handoff (`_read_target`, raised) or taken on trust | the held job ledger handoff row: `view.records.table(JOB_LEDGER).get(handoff_ref)` in `internal_summary`; its `detail` gives `resource_id`, `kind`, `native` |
| a job that has not ended: unreachable | the service's outcome `{'status': 'failed', 'failure': {'code': 'results_not_available', ...}}` is the outcome of the unit; it earns nothing; the fetch stays offered |
| completion: an observation with state `completed` and return code 0 covering every window | the held closure row has `detail['state'] == 'finished'` and the retained windows cover every requested interval |
| `_validate_result_body`, `execution_results_assignment_already_completed`, the per-window failure list, `_settled`, `_service_call` | not carried: the body is built by code from validated operands; a refused request is the service's outcome |
| credit over windows the tools returned | the same formula over the windows of the result records the Episode holds: `internal_summary` reads every result (initial and own) from its held record; `credit.py` is unchanged in its arithmetic |
| return: open `record` and `list` fields, a qualification text | return: `credit`; `finding` of counts, booleans and two fixed vocabularies; selectable `record_refs` fields and one boolean |
| the model request: goal text of the old runner, the tool-knowledge and launch-instruction texts (tools this episode does not have), the assignment three times, the controller's internals, time accounting | purpose, what the family means and earns, the operations offered now with what each does; context of the job, the requested intervals, the acquisitions so far, a completion flag and three credit numbers |

Names of result files: a route lists a job's results by their path inside the job's directory
(`LocalJobRoute.results`, `PbsSshRoute.results`). The episode's requested paths are absolute paths inside that
directory; `read_from_parent` maps each to its name (`result_names`).

## 2. The steps, file by file (A101 names; apply the same change to the copy in each episode)

1. **`goal.py`**. Rewrite `GOAL`, `UNIT`, `RESULT` for the job service: what the episode is for (fetch the
   requested result files of the handed-off job once it has ended, retain the requested bytes, return what was
   acquired). Keep the owner's sentences that carry a decision ("Choose each operation from the actual preceding
   outcomes", "Preserve partial bytes and native scores", "The scientific parent interprets the returned records",
   "Original work, resource and selector stay fixed", "Only actual complete acquisition establishes this
   endpoint"). Remove the sentences about reading the resource's filesystem window by window.
2. **`messages/read_from_parent.py`**.
   - The handoff arrives as a record reference: the handoff row's id, with the row passed in a `record_refs`
     field. Where the form already has `handoff_ref` as `record_refs` (A102, A103, A106, A110, the HPC copies of
     A104 and A107) keep it; where it is text plus `record_refs` (A104 and A107 head copies, as A101) keep that.
   - Add `result_names(...)`: each requested path relative to the job's directory. The directory is
     `target['assignment']['workspace']` (A101 form) or the assignment's `workspace` field (A103 form); in both the
     commissioner sets it to the handoff row's `detail['native']['directory']`. Where the form has neither (A102,
     A110), do not add a field: read the directory from the held handoff row in `internal_summary`
     (`handoff['detail']['native']['directory']`) and compute the names there.
   - Remove `scientific_task` (an open record of the parent's free text; for the plain family it never reached
     the model) and every field whose only reader was the removed target description.
   - Put `result_names` into the parent input beside `requested`.
3. **`task.py`**. Delete `_service_call`, `_settled`, `_read_target`, the `observe_target` and `read_file`
   wrappers, `_outcome`, `_validate_result_body`, `_publish_result`, `_windows`, `_execute_native_results`
   (`_acquire` in the A103 form), `base64`, `inspect`, `LaunchInstructions`, `ToolKnowledge`,
   `KNOWLEDGE_INSTRUCTIONS`, `LAUNCH_INSTRUCTIONS`, `time_accounting`. Then write, as in A101:
   - `execution_results_status(arguments, ctx)`: `return ctx.services['job_access'].check(ctx, handoff_ref)`;
   - `_window(store, path, file, offset, limit)` and `_retain(ctx, tool_name, arguments, windows)`;
   - `execution_results_collect`: `fetch(ctx, handoff_ref, names=[names[path] for path in requested])`; a
     `failed` outcome is returned as it is; otherwise the first window of each requested path
     (`min(settings['log_window_bytes'], FILE_LIMIT)`, and the requested length when shorter) and `_retain`;
   - `execution_results_read`: a window outside the requested interval returns the `invalid` outcome
     `execution_results_selector_conflict`; otherwise `_window` and `_retain`;
   - `STATUS`, `COLLECT`, `_plain_catalog(summary)`: status always, collect while the job is not closed, read once
     files are fetched;
   - `PLAIN_INSTRUCTIONS`, `ANSWER_INSTRUCTION`, `_instructions(summary, catalog)`, `_context(...)`, `decide`;
   - `action`: after the schema check, build each `ToolCall` from the summary (the handoff reference, the
     assignment, the requested intervals, the names, the fetched file and the closure for a read); only `path`,
     `offset` and `limit` come from the model.
   - `SERVICES` stays `('job_access',)`. The settings the episode reads are `log_window_bytes` and its yield
     profiles; `launch_instructions_directory` and `tool_knowledge_directory` are no longer read.
4. **`messages/internal_summary.py`**. Replace the native branch by A101's `_plain`: read the handoff row, the
   latest check or closure (`_observed`), the closure's `detail['results']` for the fetched files, every result
   from its held record (`_result`), the acquisitions from `view.outcomes`, completion (`_complete`), and the
   record references of the return (`execution_progress`). Replace `yield_table(...)` or
   `controller_state.as_record()` by `_credit_view` (credit unit, current credit, credit of each unit). Import the
   readers from `episode_support/jobs/job_records.py` (`JOB_LEDGER`, `checks`, `closure`, `job_rows`).
5. **`credit.py`**. Keep the coverage arithmetic. Make it read `summary['results']` with the rows `{'initial',
   'windows': [{'path', 'offset', 'returned_bytes', 'size_bytes'}]}` (the A103 form has `initial` and `own`
   lists: either keep its two lists, filled from held records, or adopt A101's one list). Rewrite the docstring.
6. **`yield_estimator.py`**. No change of logic: an unbounded selector names the accumulation controller, a finite
   one the bounded-quality controller with the credit unit as its maximum. Where the kind of the resource came
   from an assignment field (`resource_kind`), keep reading it from the parent input.
7. **`messages/final_to_parent.py`**. Controlled fields only.
   - `FINDING_FORM`: `execution_completed` (boolean), `target_family` (choice, where the episode has families),
     `acquisitions`, `failure_count`, `results_not_available`, `windows_acquired`, `bytes_acquired` (integers),
     `job_state` (choice over `not_observed`, `queued`, `running`, `finished`, `failed`, `cancelled`, `unknown`).
     Remove every `Field('text', ...)` that holds prose (`qualification`), every open `Field('record', ...)`
     without a form (`qualification`, `execution_result_origin`) and every open `Field('list', ...)` without an
     item form (`requested_paths`, `uncovered_paths`, `observation_states`, `failures`, `handoff_refs` as a list,
     `execution_file_capture_outcomes`, the `(none)` structure lists of A102, `execution_blast_hsps`).
   - Selectable: `execution_handoff_refs`, `execution_job_record_refs` (the latest check row and the closure row),
     `execution_result_refs` (each own result record, its information artifact and the fetched files its windows
     lie in), `execution_completed`. `final_to_parent` is `{'credit': completion['credit'], 'finding':
     _finding(summary), **{name: facts[name] for name in selection}}`.
8. **The parent's list of this child's selectable fields**, where the parent keeps one (A101:
   `sequence_homology_evidence/task.py`, `SELECTABLE`): remove the deleted names, add `execution_job_record_refs`.
   The parent's `msg_to_child` builds the commission from the handoff row it holds
   (`BRANCH_FIX_BLOCKERS_a101.md`, section 3); that is the head's work, not this port's.
9. **Tests** (copy from A101 and adapt the import paths and the settings keys):
   - `tests/plain_world.py`: `world`, `launch_job` (a real local job through the job probe test episode),
     `entry_input` (the commission built from the handoff row), `linked`;
   - `tests/test_plain_results.py`: four tests through `next_decision` and `run_unit`: the first request; status,
     fetch, further windows, the stop and the resume of a finished job; a job that has not ended; a finite
     selector with a window outside it;
   - `tests/test_branch_execution_result_acquisition_model_run.py`: the two real-model runs;
   - the existing form test of the episode (`test_binding.py`, `test_episode.py`, `test_binding_form.py`): change
     the assertions on the return form, the catalog and the summary shape; delete the assertions that a stub
     raises.

Check per episode: no `NotImplementedError('BLOCKED-ON-JOB-SERVICE` left for status, collect or read; the offline
tests pass; both model runs pass (`ended_by == 'yield_stop'`, the return admits, resume asks no model).

## 3. The episodes, by the form their files have today

Paths are below `gene_annotation_episode/episodic_workflow/root/`. Copies of one form are identical in the points
that matter here; port one, then apply the same edit to the others (they stay separate files).

### Form 1: A101's twin (`_service_call`, `target` in the assignment)

- `a104/evolutionary_history_evidence/execution_result_acquisition` (tests: `test_episode.py`)
- `a107/partner_presence_evidence/execution_result_acquisition` (tests: `test_episode.py`)

Apply section 2 as written; the A101 files can be taken function by function. Both have `scientific_task`
(remove), `wait` (see `BRANCH_FIX_BLOCKERS_a101.md`, section 2: leave it or delete it, do not offer it),
`KNOWLEDGE_INSTRUCTIONS` and `LAUNCH_INSTRUCTIONS` in `_instructions` (remove), `yield_table` in the summary
(replace). A104's finding has `Field('text')` for `target_family` and `handoff_ref` and an open `failures` list;
A107's `final_to_parent.py` names `execution_result_origin` and `execution_file_capture_outcomes` on nine lines
(remove). They
have no graded family: drop the BLAST and phmmer parts of the A101 files.

### Form 2: handoff as `record_refs`, wrappers that raise (`observe_target`, `read_file`, `_read_target`)

- `a102/structural_homology_evidence/execution_result_acquisition`
- `a102/structural_homology_evidence/hpc_work_planning/execution_result_acquisition`
- `a102/structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition`
- `a110/biochemical_feasibility_evidence/execution_result_acquisition`
- `a110/biochemical_feasibility_evidence/hpc_work_planning/execution_result_acquisition`

(tests: `test_binding.py` in A102, `test_binding_form.py` in A110.) The assignment already passes the handoff in
custody (`handoff_ref`, `record_refs`, exactly one) and gives `resource_kind`. Differences from section 2:

- the function that reads the handoff (A102 `task.py` line 95, A110 line 83) raises `BLOCKED-ON-JOB-SERVICE: job
  ledger handoff record`: delete it; the row is read in `internal_summary` with
  `view.records.table(JOB_LEDGER).get(parent['handoff_ref'])`;
- there is no workspace in the assignment: take the job's directory from the row
  (`handoff['detail']['native']['directory']`), confine the requested paths to it and compute `result_names` in
  `internal_summary` (not in `read_from_parent`, which has no records);
- A110 declares `resource_kind` as `Field('text')`: make it a `ChoiceField` over `local`, `hpc`;
- A102 has `known_result_refs` where A101 has `initial_result_refs`: same use (results whose bytes earn nothing);
- A102's finding has `requested_paths`, `uncovered_paths` (open lists) and `qualification` (text); A110's has
  `handoff_refs` (list) and `qualification` (text); A102's return has four `execution_protein_structure_*` lists
  marked "(none)": remove all of them;
- A102 `task.py` adds `KNOWLEDGE_INSTRUCTIONS` and `LAUNCH_INSTRUCTIONS` conditionally (lines 255, 257): remove.

### Form 3: handoff as `record_refs`, `workspace` and `resource_kind` given, direct calls on `access`

- `a103/gene_context_evidence/execution_result_acquisition`
- `a103/gene_context_evidence/hpc_work_planning/execution_result_acquisition`
- `a103/gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition`
- `a104/evolutionary_history_evidence/hpc_work_planning/execution_result_acquisition`
- `a104/evolutionary_history_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition`
- `a107/partner_presence_evidence/hpc_work_planning/execution_result_acquisition`
- `a107/partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition`

(tests: `test_binding.py`.) Differences from section 2:

- `_acquire` calls `access.observe_target` and `access.read_file` (A103 `task.py` lines 140 and 144; A107
  allocation copy lines 169 and 173) and `_read_target` raises (A103 line 95): replace `_acquire` by the three
  tools of section 2, step 3;
- the assignment has `workspace` (text): the commissioner sets it to the handoff row's
  `detail['native']['directory']`; `result_names` is computed in `read_from_parent` from it, as in A101;
- `initial_result_artifact_refs` stays (the artifacts of the initial results, passed in custody); add to its
  meaning that the fetched files those results' windows name are passed there too;
- the summary has `initial` and `own` lists and puts `controller_state.as_record()` into the summary: fill both
  lists from held records and replace the controller record by `_credit_view`;
- the finding has `requested_paths`, `observation_states` (open lists), `qualification` (open record),
  `acquired_selector_fraction` (a number that restates credit: remove), and the selectable fields include
  `execution_result_origin`, `execution_file_capture_outcomes`, `execution_blast_hsps` and family lists built by
  `_family_fields()`: remove the open ones;
- the model exchange goes through `action_transport` (`decode_response`, `generation_schema`): keep the episode's
  own transport, change only the catalog, the instructions and the context;
- the A107 planning copy (`hpc_work_planning/execution_result_acquisition`) also reads `KNOWLEDGE_INSTRUCTIONS`,
  `LAUNCH_INSTRUCTIONS` and `yield_table`: remove as in form 1.

### Form 4: API service results (not portable yet)

- `a106/perturbation_evidence/execution_result_acquisition`
- `a106/perturbation_evidence/published_evidence_assessment/execution_result_acquisition`

(tests: `test_execution_result_acquisition_binding.py`.) Their tools are `result_catalog`, `api_result_operation`,
`wait_for_service_job`, `knowledge_lookup` and `launch_instruction_lookup`, for the result of an API service job.
`JobAccess` has no route to an API service (`LAUNCH_MONITOR_EXTRACT_MECHANICS.md`, "Not provided yet", item 3), so
`check` and `fetch` cannot reach such a job. What can be done now, without the route: read the handoff row from
custody in place of the raise at `task.py` line 86; remove `qualification` (text) and the open list of the return;
rewrite the request (purpose, operations, credit; no library texts in the instructions when the lookups are tools
of the episode, name them as operations). The acquisition itself waits for the API route: with it,
`result_catalog` and `api_result_operation` become `job_access.fetch(ctx, handoff_ref, names=[...])` and
`wait_for_service_job` becomes `await ctx.services['native_events'].wait(ctx, condition)`.

## 4. What to expect from the runs (A101, settings of the test: cutoff 0.1, `uncertainty_alpha` 0.05)

- Finished job, unbounded selector (`paths`): the model selected `execution_results_status` (finished), then
  `execution_results_collect` (credit 1.0, complete), then `execution_results_status` 10 to 12 times until the
  accumulation controller stopped the Episode (three runs: 12, 13 and 14 units, one model call each).
- Job that has not ended: the model selected `execution_results_status` four times (running each time) and never
  the fetch; the controller stopped the Episode at credit 0. The return has `job_state: running`, no result
  reference and the latest check row. The refused fetch (`results_not_available`) is run offline in
  `test_plain_results.py`.
- Finite selector (`path`, `offset`, `limit`): the bounded-quality controller stops on the unit that completes
  the interval.
