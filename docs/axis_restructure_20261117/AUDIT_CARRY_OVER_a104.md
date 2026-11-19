# Audit of the a104 carry-over (19 November 2026)

Read-only audit of every episode folder under
`gene_annotation_episode/episodic_workflow/root/a104/` (29 episodes, all depths). No code or test was changed.

**Result: 29 episodes audited, 0 PASS, 29 with findings.**

All 29 pass the two structural checks (file set; one `class X(EpisodeBinding)` importing only its own files). No
episode file contains `store.db`, raw SQL or a `Store(...)` call in executable code, and none has a count, time,
turn or token cutoff: every `yield_estimator.py` returns one of the three `yield_control` controllers from
`parent_input` and `settings`. The findings are about what the episodes can actually do: 22 of 29 have a
path in their main work that raises `NotImplementedError` or needs a service or record kind that does not exist
(for the 21 job and HPC episodes this is the path of their main tool), and the head and the 7 literature episodes
call a tool registry and credit helpers that need the raw Store.

## How this was checked

- Read in full: every `credit.py`, `yield_estimator.py` and `episode.py` import/class line; the head's ten files;
  the base copy of each job leaf; every `msg_to_child.py` and `read_from_child.py` of the head, the launch, the
  monitor, the planning, the allocation and the first literature parent; the old `credit.py`,
  `yield_estimator.py` and `task_projector.py` at `97308b94c`.
- Read in part (tools, `decide`, `action`, every `except` clause, every `raise NotImplementedError`): all 29
  `task.py` files. Copies were compared by hash and diff against their base copy.
- Not read line by line: the bodies of the HPC planning tools (`hpc_work_planning/task.py` 600-1200,
  `hpc_allocation_execution/task.py` 160-760, `hpc_resource_prediction/task.py` 380-700) and the instruction
  text constants of the literature tasks. Findings there come from targeted searches only.
- Tests: one run of the whole axis through the launcher (`runs/audit_a104_2`, output in
  `runs/audit_a104_pytest_2.txt`): **279 passed in 2.41 s**.
- Function accounting: three old functions per episode from `runs/carry_over/functions/<episode>.tsv`, checked
  in the new files (section "Function accounting").

Paths below are relative to `R = gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence`.
In episode headings: `EJS` = `execution_job_submission`, `EPA` = `execution_progress_assessment`,
`ERA` = `execution_result_acquisition`, `HWP` = `hpc_work_planning`, `HAE` = `hpc_allocation_execution`,
`HRP` = `hpc_resource_prediction`, `PEA` = `published_evidence_assessment`,
`ESSI` = `evidence_search_strategy_improvement`, `SRA` = `source_relevance_assessment`,
`SEE` = `source_evidence_examination`. File names inside a finding are relative to that episode's folder.

## Finding types

| Code | Meaning | Rule broken |
|---|---|---|
| B | A tool, `decide` or message function raises `NotImplementedError`, or needs a service or record kind that does not exist, so some or all units of the episode's main work cannot run | AGENTS.md "every episode function must end up somewhere"; audit item 4/7 |
| S | Episode code calls a library object that reads or writes the raw Store (`store.db`, `store.path`, `store.read_snapshot`, Store private helpers), or keeps its own SQLite ledger outside custody | "Library functions never write to the Store or its tables directly"; contract rule 3 |
| C | `credit.py` has a path that raises not-implemented/not-carried, or calls a library function that cannot run on the custody reader | audit item 4 |
| K | Axis credit is bounded and rescaled | audit item 4; "never bound axis credits" |
| Y | Yield estimator has a not-implemented path or departs from the old episode's method | audit item 4 |
| R | `RETURN_FORM` declares selectable fields that raise when selected | "a child declares every field it can return" |
| P | A commission is checked ahead, or a held-record check on records about to be passed to a child feeds `Rejected` feedback | "no extra check ... no feedback path"; contract rule 1 "checks ahead" |
| X | `except Exception`, or a broad `except` that turns `KeyError`/`TypeError` into an outcome, or a swallowed error | audit item 5 |
| D | Silent default | audit item 5; no fallbacks |
| T | Tests are structural only: no run through the real runner to a completed unit; `decide`, `action` and the tools are not exercised | audit item 6; carry-over guide step 15 |
| U | Old episode functions that are in no place (the carriers' own intent record says "unplaced" / "not built") | "None is dropped" |

T applies to all 29 and is described once, under "Tests". It is listed on each episode line for completeness.

## Per episode

### 1. `evolutionary_history_evidence` (head) — findings: S, C, K, R, D, T, U

- **C, S** `credit.py:40` calls the library projector with `records`. `A104EvolutionaryCredit.__call__` opens
  `store.read_snapshot()` (`episode_support/grading/evolutionary_history_evidence/credit.py:88`), which the
  custody reader does not offer; the panel and alignment projectors run `store.db.execute` (same file, 280-282,
  341-343). The credit raises on the real reader, so the initial credit cannot be computed.
  `messages/internal_summary.py:66` calls the same `credit_view` in every summary.
- **K** `credit.py:40` with `yield_estimator.py:81-82`: the whole-axis credit is the library's length-weighted
  mean of `((1+p)(1+h)(1+c)-1)/7` (library `credit.py:147,158`), a value in [0, 1], with `yield_method =
  'bounded_quality'` and `native_score_maximum = 1.` (library `credit.py:16-17`). This is the old method, carried
  unchanged; it is bounded and rescaled.
- **S** `task.py:186` `ToolRegistry(ctx.store, ...)`: the registry runs `store.db.execute("CREATE TABLE IF NOT
  EXISTS tool_operations ...")` and reads `store.path` in its constructor
  (`episode_support/tools/evolutionary_history_evidence/tools.py:92-105`). Every selected-tool unit fails. The
  file's own docstring says so (`task.py:23-24`).
- **R** `messages/final_to_parent.py:91` raises `NotImplementedError('unplaced:...')` for three of the four
  declared selectable fields (`evolutionary_history_evidence_results`, `protein_conservation_outcomes`,
  `protein_phylogeny_outcomes`). `messages/msg_to_child.py:49` selects the first of them for every own-kind
  child of a depth-1 head, and `task.py:90-92` offers all three to the model, so such a child fails when it
  closes.
- **D** `credit.py:33` `TASK_PROJECTORS.get(task.get('name'), A104EvolutionaryCredit)`: the old check of the
  task name against `TASKS` and `allowed_tasks` (old `task_projector.py`, `a104_original_task_definition_required`)
  is gone; `messages/read_from_parent.py:59` keeps only "is a dict". (An unknown name still fails later, in the
  yield binding lookup.)
- Note: slots `launch`, `monitor`, `results`, `literature` are declared (`task.py:69-74`) and have a branch in
  `msg_to_child.py:54-58`, but `action` can only produce the two offered slots. The branch is unreachable.
- **U** about 23 of 156 old rows unplaced by the intent record; the report fact sources are among them.

### 2. `EJS` — findings: B, P, R, Y, T, U

- **B** `task.py:125`, `:150`, `:178` (`job_access.validate_assignment`, `.capabilities`,
  `.received_bvbrc_context` do not exist), `:228` (`unplaced:native_profile_scientific_job_view`);
  `messages/read_from_parent.py:89`.
- **P** `task.py:107-130`, called at `:293`: `_bound` validates every request with the child's own transport
  validator (`TerminalExecution(...).validate_assignment(request)`) before any commission. The request is the
  child's assignment (`messages/msg_to_child.py:27-58`).
- **R** `messages/final_to_parent.py:191`, `:193`.
- **Y** `yield_estimator.py:30-31`: a launch whose every request already has a handoff now raises; the old code
  built an exact-zero controller. (The guide's section 7b says the zero estimator is not carried; the raise is
  the carrier's choice.)
- Note: `credit.py:22-24` counts a child's own report where the old code asked the job provider
  `usable_handoff`. `messages/msg_to_child.py:54-58` passes no records to the HPC child (its form has no
  `record_refs`).

### 3. `EJS/api_job_execution` — findings: B, R, X, T, U

- **B** `task.py:81` `_job_ledger()` raises, and the only tool calls it first (`task.py:89`): no unit can
  complete. `messages/internal_summary.py:22`. The `job_access` service (`task.py:41`) does not exist.
- **R** `messages/final_to_parent.py:90-93`: `execution_result_origin` and every record-typed native field are
  declared and raise `ValueError` when selected.
- **X** `task.py:95` catches `KeyError` and `TypeError` around the custody read and the service call and returns
  an `invalid` outcome.

### 4. `EJS/hpc_job_execution` — findings: B, R, X, T, U

- **B** `task.py:68-69` (`job_access.exec_command`). **R** `messages/final_to_parent.py:110`, `:112`.
- **X** `task.py:107` catches `TypeError` and returns a failed outcome.

### 5. `EJS/local_job_execution` — findings: B, R, T, U

- **B** `task.py:120`: the whole execution (begin the intent, run, prove the command, assess the validations,
  finish the receipt) is handed to `job_access.exec_command`, which does not exist.
  `messages/internal_summary.py:60`. **R** `messages/final_to_parent.py:120`, `:122`.

### 6. `EPA` — findings: B, C, P, T, U

- **B** `task.py:117` `_observe_progress` always raises: the observe tool cannot run. `decide` reads
  `job_access.describe_progress_target` (`task.py:185`, `:230`). `messages/final_to_parent.py:116`.
- **C** `credit.py:25`: raises `NotImplementedError` for any progress reference the commissioner passed in
  `known_progress_refs`.
- **P** `messages/msg_to_child.py:19-24`: two tests of the commission before it is built (redundant with the
  schema enum in `task.py:169-171`).

### 7. `ERA` — findings: B, C, Y, R, T, U

- **B** `task.py:105`, `:209` (the `wait` tool), `:226`; `messages/read_from_parent.py:119`, `:125`;
  `messages/internal_summary.py:96`.
- **C** `credit.py:54` raises for every family except native bytes.
- **Y** `yield_estimator.py:36` raises for the typed and API families; `:46` bounds by the whole
  `acquired_record_unit` where the old maximum was the unit times the fraction not yet covered.
- **R** `messages/final_to_parent.py:167`, `:225`.

### 8. `HWP` — findings: B, S, P, X, T, U

- **S** `task.py:575` and `open_ledger` (`task.py:565-568`): the tools open the library's `HPCLedger`, a SQLite
  file under `settings['directory']`, directly. The episode's credit is read from it (`credit.py:14`). It is
  neither a custody work table nor a declared service (the docstring says so, `task.py:35-38`).
- **B** eleven helpers raise (`task.py:241`, `:251`, `:262`, `:275`, `:288`, `:300`, `:310`, `:320`, `:333`,
  `:342`, `:352`), plus `:534` (commission source) and `:558` (tool request).
  `messages/msg_to_child.py:53`: `ledger_refs` always raises, so the `hpc_prediction` commission always fails.
- **P** `task.py:1256-1259`: `records.holds` on the result references the model names for the results child,
  with `Rejected` feedback.
- **X** `task.py:728-729` (`except ValueError: return False`), `:762`, `:798` (`KeyError`/`TypeError` stored as
  a `progress_failure` string).
- Note: `task.py:102` hard-codes `PROJECT_DIRECTORY = '/lus/flare/projects/BioReason-Aurora-Test'`. Code follows
  each `raise NotImplementedError` in the blocked helpers and is unreachable.

### 9. `HWP/EJS` — findings: B, P, R, Y, T, U

- **B** `task.py:116`, `:139`, `:206`; `messages/read_from_parent.py:85`. **P** `task.py:98-121`, called at
  `:268`. **R** `messages/final_to_parent.py:168`, `:194`, `:196`, `:198`. **Y** `yield_estimator.py:29-30`.

### 10. `HWP/EJS/api_job_execution` — findings: B, R, X, T, U

- **B** `job_access` (`task.py:46`) does not exist; this copy declares the job ledger table itself
  (`task.py:44-45`) where copies 3 and 17 raise. **R** `messages/final_to_parent.py:90-93`. **X** `task.py:90`.

### 11. `HWP/EJS/hpc_job_execution` — findings: B, R, X, T, U

- **B** `task.py:115`, `:142`. **R** `messages/final_to_parent.py:121`, `:123`. **X** `task.py:126`.

### 12. `HWP/EJS/local_job_execution` — findings: B, R, T, U

- **B** `task.py:117`; `messages/internal_summary.py:60`. **R** `messages/final_to_parent.py:124`, `:126`.

### 13. `HWP/EPA` — findings: B, C, P, T, U

- **B** `task.py:87`. **C** `credit.py:25`. **P** `messages/msg_to_child.py:16-21`.

### 14. `HWP/ERA` — findings: B, C, Y, D, T, U

- **B** `task.py:95`; `messages/read_from_parent.py:62` raises for typed, API and local-file targets.
- **C** only the native-bytes credit is carried (`credit.py:38-40`); the other old credit branches are in no
  place. **Y** `yield_estimator.py:27-29`: maximum is the whole unit. **D** `yield_estimator.py:24`, `:27`
  `settings.get(..., {})`.

### 15. `HWP/HAE` — findings: B, P, X, T, U

- **B** `task.py:138`: every access to `hpc_ledger`, `job_access` and `estimate_table` (`task.py:76`) goes
  through a `hasattr` test that raises. The episode's own test confirms that a real run stops at the first unit
  (`tests/test_episode.py:273-289`).
- **P** `task.py:1046-1061`, called at `:1077`: `_check_child` tests the plan state and
  `records.holds(plan['handoff_ref'])` for the commission, with `Rejected` feedback.
- **X** `task.py:576`, `:636`.

### 16. `HWP/HAE/EJS` — findings: B, P, R, Y, T, U

- **B** `task.py:78`, `:100`. **P** `task.py:63-83`, called at `:169`.
  **R** `messages/final_to_parent.py:124`, `:126`, `:128`. **Y** `yield_estimator.py:29`.

### 17. `HWP/HAE/EJS/api_job_execution` — findings: B, R, X, T, U

- Identical to episode 3 except the binding path. **B** `task.py:81`, `:89`; `messages/internal_summary.py:22`.
  **R** `messages/final_to_parent.py:90-93`. **X** `task.py:95`.

### 18. `HWP/HAE/EJS/hpc_job_execution` — findings: B, R, X, T, U

- Identical to episode 11 except the binding path. **B** `task.py:115`, `:142`.
  **R** `messages/final_to_parent.py:121`, `:123`. **X** `task.py:126`.

### 19. `HWP/HAE/EJS/local_job_execution` — findings: B, R, T, U

- Identical to episode 5 except the binding path. **B** `task.py:120`; `messages/internal_summary.py:60`.
  **R** `messages/final_to_parent.py:120`, `:122`.

### 20. `HWP/HAE/EPA` — findings: B, C, P, T, U

- Identical to episode 13 except the binding path. **B** `task.py:87`. **C** `credit.py:25`.
  **P** `messages/msg_to_child.py:16-21`.

### 21. `HWP/HAE/ERA` — findings: B, C, Y, D, T, U

- **B** `task.py:95`; `messages/read_from_parent.py:62`. **C** as episode 14 (`credit.py:44-46`).
  **Y** `yield_estimator.py:30-32`. **D** `yield_estimator.py:27`, `:30`.

### 22. `HWP/HRP` — findings: B, C, T, U

- **B** every ledger and service primitive raises: `task.py:148`, `:158`, `:168`, `:179`, `:189`, `:267`,
  `:277`, `:287`, `:297`, `:309`, `:321`, `:331`, `:342`, `:356`. The first unit (`hpc_initialize`,
  `task.py:563`) needs them.
- **C** `credit.py:25-33`: the formula is the old one, but each read it makes raises once the episode is
  initialized. Before that it returns 0.0 (`credit.py:22-24`).
- Note: the controller's cost comes from `parent_input['yield_binding']` (`yield_estimator.py:20-22`), a new
  assignment field. This follows the old source of the value (the commission), not the settings.

### 23. `PEA` — findings: S, C, P, X, D, T, U

- **S** `task.py:505` `ToolRegistry(ctx.store, ...)`: fails in its constructor on the custody store (as the
  head). Every access and acquisition tool unit fails.
- **C** `credit.py:81-85`: `FindingValidity` and `target_eligible` call `store._assessment_write_extent`
  (`episode_support/findings/evolutionary_history_evidence/finding_validity.py:24`), a private Store helper the
  custody reader does not offer. `credit.py:108` raises `literature_task_kind_not_carried` for three task kinds
  that `messages/read_from_parent.py:37,54` admits.
- **P** `task.py:778-787`: `records.holds` on the references the model names for the child commission, with
  `Rejected` feedback (`task.py:820-821`); the same check for a report reading is at `task.py:815`.
- **X** `task.py:512` `except Exception` turns any failure of the selected operation into a `failed` outcome
  (only `CustodyError` is re-raised).
- **D** `task.py:445`, `:505` `settings.get('tool_registry', {})`.
- **U** the rate-population route and the assay-grading logic are "not built" (`task.py:11-12`).
- Note: the instruction constant still contains the `redeliver_report` and `episode.history` paragraphs
  (`task.py:377-392`); `instructions()` replaces that span before the model sees it (`task.py:406-431`, not run here).

### 24. `PEA/ESSI` — findings: S, C, P, X, D, T, U

- As episode 23: **S** `task.py:480`. **C** `credit.py:81-85`, `:108`. **P** `task.py:753-762`.
  **X** `task.py:487`. **D** `task.py:420`, `:480`.

### 25. `PEA/ESSI/SRA` — findings: S, C, P, X, D, T, U

- **S** `task.py:508`. **C** `credit.py:81-85`, `:108`. **P** `task.py:787`, `:796`. **X** `task.py:515`.
  **D** `task.py:438`, `:508`.

### 26. `PEA/ESSI/SRA/SEE` — findings: S, C, X, D, T, U

- **S** `task.py:485`. **C** `credit.py:81-85`, `:108`. **X** `task.py:492`. **D** `task.py:404`, `:485`.

### 27. `PEA/ESSI/SRA/SEE/passage_evidence_extraction` — findings: S, C, X, D, T, U

- **S** `task.py:454`. **C** `credit.py:77-81`, `:104`. **X** `task.py:461`. **D** `task.py:377`, `:454`.

### 28. `PEA/ESSI/SRA/SEE/source_coverage_improvement` — findings: B, S, C, X, T, U

- **B** `task.py:239` `_validated_lead` raises `NotImplementedError('library_not_carried:...validate_lead')`
  inside the `reason` tool's transaction (`task.py:259`), for every lead of a `verified_source_leads` task.
- **S** `task.py:156`, `:169`, `:252`. **C** `credit.py:77-81`, `:104`.
- **X** `task.py:322-323` `except ValueError: pass`.

### 29. `PEA/ESSI/SRA/SEE/table_evidence_extraction` — findings: S, C, X, D, T, U

- **S** `task.py:426`. **C** `credit.py:77-81`, `:104`. **X** `task.py:433`. **D** `task.py:346`, `:426`.

## Tests (finding T, all 29 episodes)

The 29 test files hold 279 tests and none is faked or mocked. They are tests of form: the class inherits only
`EpisodeBinding`, the folder holds the ten files, no module imports another episode, the forms admit a
hand-written assignment, `credit`, `yield_controller` and `final_to_parent` return the expected value on a
hand-written summary.

| What the tests do | Episodes |
|---|---|
| Run the episode through `link(...)` and `run()` | 1 (`HWP/HAE/tests/test_episode.py:273-289`); the test asserts that the run fails at the first unit with `BLOCKED-ON-JOB-SERVICE: hpc_ledger.open` |
| Run any tool of `TOOLS` | 0 |
| Call `decide` | at most 2 (`HWP/HAE`, `HWP/HRP`) |
| Call `action` | 3 (`EJS`, `HWP`, `HWP/HRP`) |
| Call `credit` | 21 (not: head, `EJS/local`, `HWP/EJS/hpc`, `HWP/EJS/local`, `HWP/EPA`, `HAE/EJS/local`, `HAE/EPA`, `source_coverage_improvement`) |
| Call `final_to_parent` | 21 (not: the same list without the head, plus `HWP/ERA`) |

- No test asserts on a journal record of a completed unit; the guide's step 15 asks for that.
- `HWP/tests/test_binding.py:259-296` builds a `DecisionContext` by hand from `episode_runtime.recording` (a
  runner internal, with `clock=None`) and writes the model answers itself.
- `HWP/HAE/tests/test_episode.py:269` supplies an empty class as each of the run's three services.
- Parent tests admit their commission against the child's real form (for example
  `HWP/HAE/tests/test_episode.py:187-192`). That is a test, not a link-time check.

## Function accounting (item 7, finding U)

Three old functions per episode. "Present" means the behaviour is in the named new file; "blocked" means the
function is there but its first call raises; "absent" means the behaviour is in no episode file and no library
module.

| Episodes | Old function | New place | Result |
|---|---|---|---|
| head | `task_projector.original_task_projector` | `credit.py:23-33` | present; name validation dropped |
| head | `scientific_operations.validate_tool_name` | `task.py:176` | present |
| head | `to_parent.facts` / `fact_sources` | `messages/final_to_parent.py:85-93` | absent for three of four sources (raises) |
| EJS (2, 9, 16) | `yield_estimator._launch_yield_controller` | `yield_estimator.py` | present; zero-remaining branch replaced by a raise |
| EJS (2, 9, 16) | `credit._live_project_credit` | `credit.py` | present; the usable-handoff test is the child's report |
| EJS (2, 9, 16) | `resource_information.capabilities` | `task.py` `execution_capabilities` | present for local and HPC; blocked for API |
| api (3, 10, 17) | `yield_estimator._request_yield_class` | `yield_estimator.py:14-23` | present (API branch) |
| api (3, 10, 17) | `api_service.credit_view` | `credit.py:18-27` | present |
| api (3, 10, 17) | `api_service._execute_locked`, `_publish_handoff` | `task.py` `launch_operation` | the handoff row write is present; the executor is absent (`job_access`); 3 and 17 are blocked at `task.py:81` |
| hpc (4, 11, 18) | `native_tool_actions.execute` | `task.py` `exec_command` | receipt and validation present; execution blocked |
| hpc (4, 11, 18) | `credit._live_project_credit` | 4: `messages/internal_summary.py:38`; 11, 18: `credit.py:12` | present |
| hpc (4, 11, 18) | `yield_estimator._request_yield_class` | `yield_estimator.py` | present |
| local (5, 12, 19) | `native_tool_actions.execute` | `task.py` `exec_command` | absent: the whole body is the missing service's |
| local (5, 12, 19) | `credit._live_project_credit` | `credit.py:11-13` | present |
| local (5, 12, 19) | `yield_estimator._request_yield_class` | `yield_estimator.py` | present |
| EPA (6, 13, 20) | `credit.information_credit` | `credit.py:33-39` | present |
| EPA (6, 13, 20) | `to_child_...prepare_dependency_request` | `messages/msg_to_child.py` | present |
| EPA (6, 13, 20) | `progress_operations.execute` (observe) | `task.py` `_observe_progress` | absent (always raises) |
| ERA (7, 14, 21) | `credit._generic_result_selector_progress` | `credit.py` | present |
| ERA (7, 14, 21) | `yield_estimator._results_yield_controller` | `yield_estimator.py` | present for native bytes; typed and API absent |
| ERA (7, 14, 21) | `hmmer_acquisition.execute`, `api_acquisition._execute_locked` | none | absent |
| HWP (8) | `allocation_order._order_original_units` | `task.py:1136` `hpc_allocation_order` | present (body not read); reaches blocked `job_access` |
| HWP (8) | `portfolio_planning._freeze_portfolio_plan` | `task.py:1002` `hpc_plan` | present (body not read) |
| HWP (8) | `from_parent._tool_request` | `task.py:550-558` | absent (raises) |
| HAE (15) | `_order_original_units`, `_freeze_portfolio_plan`, `_attach_original_handoff` | `task.py:753`, `:488`, `:527` | present (bodies not read); all behind the blocked `hpc_ledger.open` |
| HRP (22) | `credit._quality` | `task.py:372` `model_quality` | present |
| HRP (22) | `portfolio_comparison._comparisons` | `task.py:471` | present (body not read) |
| HRP (22) | `prediction_state.initialize` | `task.py:563` `hpc_initialize` | blocked (ledger primitives raise) |
| literature (23-27, 29) | `scientific_interpretation.reasoning_has_task_content` | `task.py` `empty_commit` | present |
| literature (23-27, 29) | `source_admission._tool_arguments` | `task.py` `admitted` | present |
| literature (23-27, 29) | `evidence_grading.execute`, `contracts._required_grading_logic` | none | absent ("not built") |
| source_coverage (28) | `_tool_arguments`, `reasoning_has_task_content` | `task.py` `_admit`, `_empty_commit` | present |
| source_coverage (28) | library `validate_lead` | `task.py:232-239` | absent (raises) |

The carriers' own intent records (`docs/axis_restructure_20261117/episode_intent/a104/*.md`, section "Carried
over") mark old rows as unplaced or not built. Counted by keyword over those tables, so approximate:

| Episode | Old rows | Machinery | Unplaced / not built |
|---|---|---|---|
| head | 156 | 85 | 23 |
| EJS (2 / 9 / 16) | 178 / 176 / 176 | 102 / 85 / 94 | 23 / 35 / 20 |
| api (3 / 10 / 17) | 215 / 216 / 216 | 78 / 78 / 78 | 76 / 77 / 77 |
| hpc (4 / 11 / 18) | 200 / 200 / 200 | 76 / 125 / 125 | 68 / 13 / 13 |
| local (5 / 12 / 19) | 200 / 200 / 200 | 122 / 101 / 122 | 18 / 21 / 18 |
| EPA (6 / 13 / 20) | 111 / 111 / 111 | 43 / 40 / 40 | 22 / 22 / 22 |
| ERA (7 / 14 / 21) | 248 / 248 / 248 | 126 / 85 / 81 | 75 / 120 / 120 |
| HWP / HAE / HRP | 165 / 154 / 102 | 65 / 62 / 51 | 13 / 3 / 11 |
| PEA / ESSI / SRA / SEE | 189 / 188 / 188 / 192 | 54 / 53 / 53 / 53 | 83 / 83 / 83 / 88 |
| passage / source_coverage / table | 187 / 187 / 187 | 52 / 52 / 52 | 89 / 90 / 89 |

Copies of one old episode are classified differently by different carriers (for example `hpc_job_execution`:
76 machinery rows in copy 4, 125 in copies 11 and 18). The records were not reconciled.

## Totals by finding type

| Code | Finding | Episodes |
|---|---|---|
| T | Tests are structural only | 29 |
| U | Old functions in no place | 29 |
| B | Not-implemented or missing-service path in the main work | 22 |
| C | Credit path raises or cannot run on the custody reader | 15 |
| X | `except Exception`, broad `except`, swallowed error | 15 |
| R | Declared return fields that raise when selected | 14 |
| P | Commission checked ahead, or held-record check with feedback | 11 |
| S | Raw-Store library object, or ledger outside custody | 9 |
| D | Silent default | 9 |
| Y | Yield stub path or departure from the old method | 6 |
| K | Axis credit bounded and rescaled | 1 |

Checks with no finding in any episode: file set (item 1); `episode.py` form and imports (item 2); stopping only
by the yield controller, no cutoffs (item 3); `yield_estimator.py` reads only `parent_input` and `settings`;
`credit` and `finding` required in every `RETURN_FORM`; every `final_to_parent` returns `completion['credit']`;
no `NotImplementedError`-only `credit.py`; no fake or mock in any test.

## Judgement calls to confirm

- **P** is the least certain type. The three literature parents and the two HPC parents check, in `action`,
  that the Episode holds records the model named for a child, and reject the answer with feedback. The contract
  allows that check for an argument of the episode's own tool and says it is "never a check of a commission".
  I counted it because here the records are exactly what the commission passes. The launch episodes' `_bound`
  and the monitor's `msg_to_child` tests raise and fail the run; they have no feedback path, and I counted them
  as "checks ahead".
- **B** follows the carry-over guide's own instruction (section 5: code that needs a missing piece raises at
  that point). It is counted because the audit asks whether the behaviour is really there, and it is not.
- **K** is the old method, carried faithfully through the library projector. It is counted because it breaks
  the rule as written.
- A105/A108 grading rules do not apply to this axis.
