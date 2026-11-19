# Audit of the carry-over, axis A106 (19 November 2026)

Read-only audit of every episode folder under `gene_annotation_episode/episodic_workflow/root/a106/`, against
`AGENTS.md`, `BINDING_CONTRACT.md`, the reference episodes `episode_runtime/tests/fact_collection/` and
`fact_extraction/`, the old files at `97308b94c` and `runs/carry_over/functions/a106__*.tsv`. No code or test was
changed. The tests were run once through the launcher (`runs/audit_a106_2`): 128 passed.

**Result: 15 episodes audited, 0 PASS, 15 with findings.** No episode of this axis can run a complete Episode
today: the eight scientific episodes hand `ctx.store` to a library that calls `store.db`, and the seven job episodes
raise `NotImplementedError` or need a service that does not exist.

Paths are relative to `root/a106/perturbation_evidence/` (`PE`). `PEA` = `published_evidence_assessment`,
`ESSI` = `PEA/evidence_search_strategy_improvement`, `SRA` = `ESSI/source_relevance_assessment`,
`SEE` = `SRA/source_evidence_examination`. `EJS` = `execution_job_submission`, `API` = `api_job_execution`,
`EPA` = `execution_progress_assessment`, `ERA` = `execution_result_acquisition`.

## What holds in all 15 episodes

- File set (check 1): exactly the ten files (eight for a leaf), `__init__.py`, child folders, `tests/`. No other module.
- `episode.py` (check 2): one class with the single base `EpisodeBinding`; no import from another episode folder
  (the `from ..credit` / `from ..task` / `from ..goal` imports in `messages/` are the episode's own files); no
  table of bindings.
- Stopping (check 3): `decide` and `action` return only `ToolCall`, `ChildCall` or `ModelRequest`; no elapsed-time,
  token, turn or unit-count cutoff; no second stop rule.
- No `store.db` or raw Store call in an episode file itself (the raw calls are in the library the episode calls:
  finding type RAWSTORE).
- `yield_estimator.py` reads `parent_input` and `settings` only. Every controller is one of the three of
  `yield_control`.
- Every `RETURN_FORM` declares `credit` (number) and `finding` as required; parents select in `msg_to_child.py`.
- Credit is nowhere bounded, clamped or rescaled (`max(` in the literature `credit.py` is span coverage).

## Finding types

| Code | Meaning | Rule |
|---|---|---|
| STUB | `NotImplementedError` (or an unconditional raise) on a path the episode offers | AGENTS "every episode function must end up somewhere ... None is dropped"; check 4/5 |
| SERVICE | Declares a service that nothing in the repository builds | same; the episode cannot be linked or run |
| RAWSTORE | The episode hands `ctx.store` / `records` to a library function still written against the raw Store (`store.db`, `store._require`, `store._assessment_write_extent`) | Owner rule 3 (custody only; library never writes Store tables directly) |
| PRECHECK | `action` checks a child commission ahead and returns feedback to the model | Owner rule 1 (no pre-check, no feedback path for a commission) |
| BROADEXCEPT | `try/except` that turns any exception into an outcome or relabels it | check 5 (try/except that hides errors) |
| CREDIT | `credit.py` is a pass-through, not the carried formula | check 4 |
| YIELD | Controller kind does not match the old method / the sibling copy of the same old code | check 4 |
| DROPPED | Old own-file function sampled for check 7 has no working new home | check 7; AGENTS "None is dropped" |
| PROMPT | The goal tells the model to use a tool or return a field the episode does not offer or declare | Owner rule 5 (child declares every field); prompt construction |
| TESTS | Tests do not exercise decide / action / tools / credit; or assert a stub; or use a stand-in | check 6 |
| LEFTOVER | Old-runner name or value left in the new code | check 5 |
| FALLBACK | New silent default not present in the old code, or inconsistent with the sibling copy | check 5 |

## Per episode

### 1. `PE` (head, `perturbation_evidence`) — findings

- RAWSTORE `credit.py:28` (and `messages/internal_summary.py:39`): `project_finding_progress(records, ...)`; the
  library (`episode_support/findings/perturbation_evidence/investigation_progress.py:78,130,150`) calls
  `store._require` and `store.db.execute`. `RecordReader` has neither: credit raises `AttributeError` as soon as one
  assessment of the proposed annotation is held, so the only credit this episode can return is 0.
- RAWSTORE `task.py:479`: `ToolRegistry(ctx.store, ...)`; its constructor
  (`episode_support/tools/perturbation_evidence/tools.py:75-78`) runs `store.db.execute('CREATE TABLE IF NOT EXISTS
  tool_operations ...')` and `store.db.commit()`. The call is outside the `try`, so every `selected_tool` unit ends
  the run. The library creates and writes a Store table directly.
- STUB `task.py:469`: tool `process_execution` is offered (`task.py:318`) and always raises.
- STUB `task.py:527`: `decide` raises for every evidence-axis entry that is not a published instruction entry.
- STUB `messages/final_to_parent.py:67`: the declared field `perturbation_evidence_results` always raises; and
  `messages/msg_to_child.py:44` selects it for every child of this own kind, so every recursive commission ends the
  run at the child's return.
- PRECHECK `task.py:598-602` (with `named_references`, `task.py:178-188`): `records.holds` of the records a child
  commission names, rejected with feedback. The contract allows this only for arguments of the episode's own tool.
- BROADEXCEPT `task.py:486-487`: `except Exception` -> `failure_outcome` (the old code caught named error types).
- FALLBACK `messages/msg_to_child.py:103,105`: `arguments.get('evidence_refs', summary['evidence_refs'])` and the
  same for `constraints`; the old `prepare_invocation` required both.
- DROPPED 2 of 3 sampled: `to_parent.build_process_result` / `merge_process_results` -> stub
  (`messages/final_to_parent.py:61-70`); `execution_planning.read` -> stub (`task.py:462-472`). Present:
  `credit.original_task_projector` (`messages/read_from_parent.py:57-66`, `credit.py:23-30`).
- TESTS `tests/test_binding.py`: no test calls `decide`, `action`, a tool or `credit` (`:157-163` only searches the
  source text for `NotImplementedError`); `:145` asserts the stub; nothing runs through the runner.
- Note: `yield_estimator.py:18-19` can never fire (`task_key` is a constant, `messages/read_from_parent.py:84`).

### 2. `PE/EJS` — findings

- SERVICE `task.py:56` (`job_access`); STUB `task.py:95`, `task.py:109`, `messages/final_to_parent.py:92`.
- BROADEXCEPT `task.py:92-97`: `except AttributeError: raise NotImplementedError(...) from None` relabels any
  `AttributeError` raised inside the service read.
- LEFTOVER `messages/msg_to_child.py:39`: `message={'initial_report': {}}` (the old initial report).
- DROPPED 1 of 3 sampled: `OperationalOperations.capabilities` -> `task.py:100-120`, only a call of the unbuilt
  service. Present: `_live_project_credit` (`credit.py:19-21`), `_launch_yield_controller`
  (`yield_estimator.py:24-34`, bounded quality as before).
- TESTS `tests/test_binding.py`: `decide` and the tools are never called; `action` only for one rejection (`:195`);
  no runner. Credit, controller, `msg_to_child`, `final_to_parent` are exercised on hand-built summaries.

### 3. `PE/EJS/API` — findings

- CREDIT `credit.py:14-18`: returns `summary['credit']`, the number the unbuilt `job_access.api_execute` reply reports
  (`task.py:214`). The old own-file formula `_api_operational_credit` (old `credit.py:23-45`: new handoff and result
  identities times `handoff_unit` / `acquired_record_unit`) is not in `credit.py` and no library function is called.
- SERVICE `task.py:46`; STUB `task.py:176`, `task.py:187` (`write_handoff_record` always raises, so an operation
  that produces a handoff ends the run).
- BROADEXCEPT `task.py:205-209`: `except Exception` -> failed outcome.
- FALLBACK `task.py:148`: empty `arguments_json` becomes `{}`.
- LEFTOVER `messages/read_from_parent.py:38`, `messages/internal_summary.py:14`: `initial_report`.
- DROPPED 2 of 3 sampled: `_api_operational_credit` (above); `execution_operations.execute` -> `task.py:191-216`
  (unbuilt service plus the stub). Present: `_launch_api_yield_controller` (`yield_estimator.py:28-31`, completion).
- TESTS `tests/test_api_job_execution.py`: the credit test is `credit({'credit': 7.5}, None) == 7.5` (`:104`); no
  `decide`, `action` or tool; no runner.

### 4. `PE/EPA` — findings

- STUB `task.py:105,116,126,137,149,166,207`, `credit.py:24`. `decide` calls `target_in_scope` first
  (`task.py:328`), which always raises: the episode cannot make one decision. Unreachable code after the raises:
  `task.py:107-108,118,128,154-158`.
- SERVICE `task.py:59` (`job_access`, `native_events`).
- PRECHECK `task.py:385-394`: the dependency handle, record types and known references of a monitor commission are
  checked in `action` and rejected with feedback (stated in `messages/msg_to_child.py:4-10`).
- LEFTOVER `messages/msg_to_child.py:19-20,27`: `RESULT_CONTRACT` (`decision` / `measurements` / `information`, the old
  report contract) sent in the message; the child never reads it.
- DROPPED 1 of 3 sampled: `ProgressOperations.execute` (observe) -> `task.py:202-216` -> stub `task.py:141-158`.
  Present: `information_credit` (`credit.py:38-49`), `_monitor_information_yield` (`yield_estimator.py:13-14`,
  accumulation; its non-decrease raise at `credit.py:31-35`).
- TESTS `tests/test_episode_binding.py:83-84`: `class WithoutJobs`, a stand-in for the two services; `:87-110` the
  only runner test asserts `NotImplementedError`. `credit`, `action`, tools and `final_to_parent` are not exercised.

### 5. `PE/ERA` — findings

- STUB `task.py:86`: `handoff_target` always raises and is the first statement of every job tool
  (`task.py:126,142,160`); the first unit `decide` offers (`task.py:226`) ends the run.
- SERVICE `task.py:43`.
- DROPPED 1 of 3 sampled: `execution_state._target` -> stub `task.py:79-87`. Present: `_api_operational_credit`
  (`credit.py:15-21`), `_results_yield_controller` (`yield_estimator.py:29-32`, accumulation; the practical
  completion endpoint is not carried, as the guide allows).
- TESTS `tests/test_execution_result_acquisition_binding.py:105-108` asserts the stub; no `decide`, `action`, tool
  or `final_to_parent` call; no runner. The credit formula is exercised on hand-built summaries (`:94-102`).

### 6. `PEA` — findings

- RAWSTORE `task.py:454`: `ToolRegistry(ctx.store, ...)` (as in episode 1): every access and acquisition tool ends
  the run. `credit.py:79-83`: `FindingValidity` / `target_eligible`
  (`episode_support/findings/perturbation_evidence/finding_validity.py:24`, `store._assessment_write_extent`): the
  `source_answer:assessment` credit raises once a retained current assessment is held.
- SERVICE `task.py:86` (`execution_binding`; `task.py:19-23` says it does not exist); `decide` reads it first
  (`task.py:725`).
- PRECHECK `task.py:779-781`: `records.holds` of the handoff a `results` commission names, rejected with feedback.
- BROADEXCEPT `task.py:461-462`.
- PROMPT `goal.py:15`: the joined sub-score text tells the model to "Finish A106 with literature.a106.finalize and
  return the requested literature_a106_subscore_cells"; no such tool is offered and the field is not in
  `messages/final_to_parent.py:29-37`.
- DROPPED 1 of 3 sampled: `scoring/intervention_main_sheet.InterventionMainSheet.complete_score_judgment` has no
  new home. Beyond the sample the whole population and grading route is absent (`task.py:15-16` "not built"):
  `grading/intervention_assessment.py`, `scoring/intervention_main_sheet.py`, the population branch of
  `source_operations.execute` (old `:84-123`), `scientific_records.py` (27 functions). Present: `lead_dispositions`
  (`credit.py:39-49`), `prepare_analysis_contract` (`task.py:678`).
- TESTS `tests/test_binding.py`: no `decide`, `action` or tool call; credit only for the zero case (`:132-138`); no
  runner.

### 7. `PEA/EJS` — findings

- SERVICE `task.py:55` (`job_access`; `task.py:24-27` says linking raises `LinkError`).
- FALLBACK `task.py:73,90,99`: `settings.get('initial_information', {})`; the sibling copy `PE/EJS/task.py:74`
  requires the setting.
- LEFTOVER `messages/msg_to_child.py:37`: `'initial_report': {}`.
- DROPPED 1 of 3 sampled: `OperationalOperations.capabilities` -> `task.py:102-112`, only the unbuilt service.
  Present: `_live_project_credit` (`credit.py:15-18`), `_launch_yield_controller` (`yield_estimator.py:16-24`).
- TESTS `tests/test_execution_job_submission_binding.py` (6 tests): `credit`, `final_to_parent`, `decide`, `action`
  and the tools are never called.

### 8. `PEA/EJS/API` — findings

- YIELD `yield_estimator.py:29-32`: accumulation. The old file is byte-identical to that of episode 3, which became
  completion, and the guide maps `PracticalYieldEstimator(verify_completion)` to completion. The commission still
  carries `completion_target` (`messages/read_from_parent.py:23,34`; parent `PEA/EJS/messages/msg_to_child.py:33`),
  which nothing reads.
- SERVICE `task.py:36`.
- FALLBACK `task.py:118`: `settings['initial_information'].get(resource_id)`.
- DROPPED 1 of 3 sampled: `execution_operations.execute` -> `task.py:121-129`, only the unbuilt service. Present:
  `_api_operational_credit`, re-expressed as counts (`credit.py:12-17`); `_request_yield_class`
  (`yield_estimator.py:13-19`).
- TESTS `tests/test_api_job_execution_binding.py` (4 tests): class, file set, imports and forms only.

### 9. `PEA/ERA` — findings

Private copy of episode 5 (the files differ in the binding path only). Same findings at the same lines: STUB
`task.py:86`; SERVICE `task.py:43`; DROPPED 1 of 3; TESTS `tests/test_execution_result_acquisition_binding.py:105-108`.

### 10. `ESSI` — findings

- RAWSTORE `task.py:375` (`ToolRegistry(ctx.store, ...)`), `credit.py:79-83`.
- BROADEXCEPT `task.py:382`.
- PROMPT `goal.py:18` (sub-score text: `literature.a106.finalize`, `literature_a106_subscore_cells`; neither exists
  here, `messages/final_to_parent.py:29-37`).
- DROPPED 1 of 3 sampled: `grading/intervention_assessment.InterventionAssessment._intervention_source_cells` (and
  the population and scoring route, `task.py:16`). Present: `screening_answers` (`credit.py:52`),
  `_private_yield_controller` (`yield_estimator.py:13-20`).
- TESTS `tests/test_binding.py`: no `decide`, `action` or tool call; credit only for the zero case; no runner.

### 11. `SRA` — findings

- RAWSTORE `task.py:373`, `credit.py:79-83`. BROADEXCEPT `task.py:380`. PROMPT `goal.py:17`.
- DROPPED 1 of 3 sampled: `scoring/intervention_main_sheet.InterventionMainSheet.automatic_score_judgments` (route
  not built, `task.py:16`). Present: `screening_answers` (`credit.py:52`), `_private_yield_controller`
  (`yield_estimator.py:13-20`).
- TESTS `tests/test_binding.py`: as episode 10.

### 12. `SEE` — findings

- RAWSTORE `task.py:325`, `credit.py:79-83`. BROADEXCEPT `task.py:332`. PROMPT `goal.py:17`.
- DROPPED 1 of 3 sampled: `LiteratureOperations.execute` population branch (`task.py:15` "not built"). Present:
  `screening_answers` (`credit.py:52`), `_private_yield_controller` (`yield_estimator.py:13-20`).
- TESTS `tests/test_binding.py`: as episode 10.

### 13. `SEE/passage_evidence_extraction` — findings

- RAWSTORE `task.py:265`, `credit.py:73-77`. BROADEXCEPT `task.py:272`.
- DROPPED 1 of 3 sampled: `InterventionMainSheet.complete_score_judgment` (route not built, `task.py:13`); the
  sub-score part of the old goal text is also left out (`goal.py:4-6`). Present: `screening_answers`
  (`credit.py:46`), `_private_yield_controller` (`yield_estimator.py:13-20`).
- TESTS `tests/test_binding.py`: no `decide`, `action` or tool call; credit only for the zero case; no runner.

### 14. `SEE/source_coverage_improvement` — findings

- RAWSTORE `task.py:383` (`ToolRegistry`), `task.py:335` (`LiteratureRepositories(ctx.store, ...)`; `task.py:19-21`
  says the repositories "fail where reached"), `credit.py:73-77`. `task.py:407` calls the repository's private
  `_native_source`.
- BROADEXCEPT `task.py:390`.
- PROMPT `goal.py:14`: the text asks for `literature_a106_subscore_cells`; `literature_a106_finalize` is a tool here
  (`task.py:561`) but no return field for its cells is declared (`messages/final_to_parent.py:29-37`).
- LEFTOVER `task.py:327`: `role='literature_ordered'` (the old role name) passed to the library context.
- DROPPED 1 of 3 sampled: `InterventionMainSheet.automatic_score_judgments` / `complete_score_judgment` (no code
  for score judgments in the episode). Present: the population branch of `execute` (`task.py:394`, on the raw-Store
  library), `_private_yield_controller` (`yield_estimator.py:13-20`).
- TESTS `tests/test_binding.py`: no `decide`, `action` or tool call (the population tools are only listed, `:109`);
  no runner.

### 15. `SEE/table_evidence_extraction` — findings

- RAWSTORE `task.py:269`, `credit.py:73-77`. BROADEXCEPT `task.py:276`.
- DROPPED 1 of 3 sampled: `InterventionAssessment._intervention_source_cells` (route not built, `task.py:13`); the
  sub-score part of the old goal text is left out (`goal.py:3-4`). Present: `screening_answers` (`credit.py:46`),
  `_private_yield_controller` (`yield_estimator.py:13-20`).
- TESTS `tests/test_binding.py`: as episode 13.

## Totals by finding type

| Type | Episodes | Sites | Where |
|---|---|---|---|
| TESTS | 15 | 15 | every episode; 4 of them assert a stub (1, 4, 5, 9); 1 stand-in service class (4) |
| DROPPED (check 7) | 15 | 17 of 45 sampled functions | 2 each in episodes 1 and 3; 1 in each of the other 13 |
| BROADEXCEPT | 10 | 10 | 1, 2, 3, 6, 10, 11, 12, 13, 14, 15 |
| RAWSTORE | 8 | 18 | 1 (3), 6 (2), 10 (2), 11 (2), 12 (2), 13 (2), 14 (3), 15 (2) |
| SERVICE | 8 | 8 | 2, 3, 4, 5, 6, 7, 8, 9 |
| STUB | 6 | 18 | 1 (3), 2 (3), 3 (2), 4 (8), 5 (1), 9 (1) |
| PROMPT | 5 | 5 | 6, 10, 11, 12, 14 |
| LEFTOVER | 5 | 6 | 2, 3 (2), 4, 7, 14 |
| FALLBACK | 4 | 7 | 1 (2), 3, 7 (3), 8 |
| PRECHECK | 3 | 3 | 1, 4, 6 |
| CREDIT | 1 | 1 | 3 |
| YIELD | 1 | 1 | 8 |

| | Count |
|---|---|
| Episodes audited | 15 |
| PASS | 0 |
| With findings | 15 |

## Observations not counted (for the owner's decision)

- `read_from_parent` validates the assignment it was commissioned with and raises in 14 episodes (for example
  `PE/messages/read_from_parent.py:57-83`, `PE/EJS/messages/read_from_parent.py:59-109`,
  `PE/EPA/messages/read_from_parent.py:47-54`, `PEA/messages/read_from_parent.py:50-61` and its six copies,
  `PEA/EJS/messages/read_from_parent.py:91-100`). The run fails with the error and nothing is fed back, which is what
  rule 1 asks of a wrong commission; but rule 1 also says "no extra check", and the reference `read_from_parent`
  only reads. Not counted as a finding.
- `PE/EJS/yield_estimator.py:29-30` and `PEA/EJS/yield_estimator.py:17-18` raise when no request is left without a
  handoff, where the old code built an exact-zero controller. The guide says nothing replaces that estimator.
- `ctx.settings.get('tool_registry', {})` in the eight scientific `task.py` files is an optional setting with an
  empty default.
- The seven literature `task.py` files import the library's private names `_resolve` and `_Sources`.
- `PE/task.py` and the literature and job tasks read library directories named in `ctx.settings` directly in
  `decide` (the frozen process, tool, knowledge and launch-instruction libraries), not through a declared service,
  so those reads are not recorded per unit.
