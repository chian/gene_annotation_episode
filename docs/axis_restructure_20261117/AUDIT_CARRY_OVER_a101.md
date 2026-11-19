# Audit of the carry-over, axis A101 (19 November 2026)

Read-only audit of every episode folder under `gene_annotation_episode/episodic_workflow/root/a101/`.
No code or test was changed. Sources read: `AGENTS.md`, `BINDING_CONTRACT.md`, the reference episodes
`episode_runtime/tests/fact_collection/` and `fact_extraction/`, every `.py` file of the axis, the old episode
files at `97308b94c` (`git archive` of `root/a101/sequence_homology_evidence/**`), `runs/carry_over/functions/a101__*.tsv`
and the `episode_intent/a101/` tables.

Result: **19 episodes audited, 0 PASS, 19 with findings.**

Tests: `runs/audit_a101_2`, the whole axis through `tools/one_workflow.sh --slot auda101`: 151 passed in 2.2 s.
(`runs/audit_a101_1` was refused by the launcher because the run directory already existed; it holds one empty
`home/` folder.)

## Paths and abbreviations

`R` = `gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence`. Every `file:line` below is
relative to the episode's own folder, given at the start of its entry.

| Short name | Folder |
|---|---|
| HEAD | `R` |
| EJS | `R/execution_job_submission` |
| EJS/api, EJS/hpc, EJS/local | `R/execution_job_submission/{api,hpc,local}_job_execution` |
| EPA | `R/execution_progress_assessment` |
| ERA | `R/execution_result_acquisition` |
| PEA | `R/published_evidence_assessment` |
| ESSI | `PEA/evidence_search_strategy_improvement` |
| SRA | `ESSI/source_relevance_assessment` |
| SEE | `SRA/source_evidence_examination` |
| SEE/passage, SEE/coverage, SEE/table | `SEE/{passage_evidence_extraction,source_coverage_improvement,table_evidence_extraction}` |
| RRA | `R/resource_result_acquisition` |
| RWS | `R/resource_work_submission` |
| RWS/api, RWS/hpc, RWS/local | `R/resource_work_submission/{api,hpc,local}_resource_work_execution` |

## Finding types

Severity A: the episode cannot run, or an owner rule is broken. B: a deviation from the old episode or from the
audit criteria that does not by itself stop a run. C: weak, listed for completeness.

| Code | Sev | Finding type | Rule |
|---|---|---|---|
| T1 | B | Tests do not exercise `decide`, `action`, `credit` and `final_to_parent` in a run. They are form tests and calls of single functions on hand-written summaries (`ctx=None`); no test links an episode with the runner, a `Store` or a model | check 6 |
| T2 | A | Old episode behaviour, or a service the episode needs, is a `NotImplementedError` (`unplaced:...`, `BLOCKED-ON-JOB-SERVICE:...`) | AGENTS.md "every episode function must end up somewhere ... None is dropped"; check 7 |
| T3 | A | `credit` calls `NativeCorrespondenceScoring.read_details`, which calls `store.read_snapshot()` and `store.db.execute(...)` (`episode_support/grading/sequence_alignment/native_correspondence.py:78,104,112`). `credit` is handed a `RecordReader`, which has neither (`episode_runtime/store_scope.py`: `read_snapshot` is defined only on `ScopedStore`, line 707). The first credit evaluation, the one that builds the controller, raises `AttributeError` | owner rule 3 (custody only); check 4 |
| T4 | A | `credit.py` raises `NotImplementedError` on a path it can reach | check 4 |
| T5 | B | The credit number is not carried from the episode's old file: a new formula, or the pass-through of a number a service that is not provided would return (old `credit.py` was `services.bound_role_credit` / `api_execution.credit_view`) | check 4 |
| T6 | B | The yield controller cannot be confirmed against the old episode: the old `yield_estimator.py` chose nothing (returned `None`, or handed the choice to the runner's `controller_factory`); the kind is the carrier's choice | check 4 |
| T7 | B | The yield controller deviates from the old one | check 4 |
| T8 | B | `except Exception` turns any error of a tool into a `failed` outcome (also two narrower catches that change the error) | check 5 |
| T9 | A | A commission is checked ahead: `action` rejects the model's commission with feedback, or `msg_to_child` tests what it is about to send | owner rule 1 |
| T10 | B | A selectable return field is declared and raises when it is selected | owner rule 5 ("declares every field it can return") |
| T11 | C | Silent default or fallback | check 5 |

Checks with no finding in any of the 19 episodes: the file set (check 1); one `class X(EpisodeBinding)` per
`episode.py`, no other base, no import from another episode folder, no table of bindings (check 2); no stopping
rule other than the controller, no elapsed-time, token, turn or count cutoff; no `store.db`, `Store(...)` or raw
SQL in an episode file; every `yield_estimator.py` reads `parent_input` and `settings` only and returns a
`yield_control` controller; `credit` and `finding` required in every `RETURN_FORM`; every parent selects in
`msg_to_child`; no credit is bounded, clamped or rescaled; no old-runner name (`recorder`, `recall`, `SourceEnd`,
`Done`, `prepare_assignment`, `admit_return`, `receive_report`) outside docstrings; no mock, fake, monkeypatch or
stand-in class in any test.

## Per episode

### HEAD (`R`) — findings
- T3 `credit.py:50` (through `credit.py:42`). The docstring states it (`credit.py:13-14`).
- T2 `task.py:464`: tool `process_execution` (old `execution_planning.read`) is a stub that is declared in `TOOLS` (`task.py:467-468`). `messages/final_to_parent.py:79`: `sequence_homology_evidence_results` (old `build_process_result`, `merge_process_results`, `project_process_result`) raises.
- T10 `messages/final_to_parent.py:76-79`, and `messages/msg_to_child.py:104-106` requires that field of the recursive child at path depth 1: every recursive commission of the top head fails.
- T9 `messages/msg_to_child.py:85-86` (`child_proposed_annotation_differs_from_original_task` raised while the commission is built).
- T8 `task.py:426-427`.
- T1 `tests/test_episode_form.py`: 3 tests (class definition, file set, imports); none calls `decide`, `action`, `credit`, `final_to_parent`, `internal_summary` or `yield_controller`.

### EJS — findings
- T2 `task.py:124`, `task.py:150`, `task.py:178` (`job_access` members), `task.py:228` (`native_profile_scientific_job_view`: every decision for a native HMMER request raises), `messages/read_from_parent.py:94` (BLAST graded request).
- T10 `messages/final_to_parent.py:196`, `messages/final_to_parent.py:198`.
- T7 `yield_estimator.py:29-30`: the old exact-zero estimator (`no_remaining_requests`) is replaced by `ValueError('launch_every_original_request_already_has_a_handoff')`.
- T8 (narrow) `task.py:121-126`: `except AttributeError` around a service read is re-raised as `NotImplementedError`.
- T1 `tests/test_binding.py`: `action` once, `credit` and `final_to_parent` on hand-written summaries; `decide` never.

### EJS/api — findings
- T2 `task.py:196` (`required_member`), `task.py:209` (`write_handoff_record`: a successful operation with a handoff raises, so no handoff can be established).
- T5 `credit.py:15`: the credit is `reply['credit']` of `job_access.api_execute` (`task.py:236`), a service that is not provided.
- T10 `messages/final_to_parent.py:103-104` (`execution_result_origin`), `messages/final_to_parent.py:82`.
- T8 `task.py:227-231`.
- T1 `tests/test_api_job_execution.py`: `credit`, `final_to_parent`, `yield_controller`; `decide` and `action` never.

### EJS/hpc — findings
- T2 `task.py:97`: `run_command` always raises; it is not among the errors `exec_command` catches (`task.py:110`), so the episode's only tool ends the run.
- T1 `tests/test_binding.py`: `credit`, `final_to_parent`, `yield_controller`; `decide` and `action` never.
- Otherwise in form: `credit.py:13-15` is the old practical credit; `yield_estimator.py:13-19` is the old completion rule.

### EJS/local — findings
- T2 `task.py:102` (`validate_primary_resource_bindings`), `task.py:130` (`job_access.exec_command`), `messages/internal_summary.py:61`.
- T10 `messages/final_to_parent.py:185`.
- T1 `tests/test_episode.py`: `credit`, `final_to_parent`, `yield_controller`; `decide` and `action` never.

### EPA — findings
- T2 `task.py:107` (`_observe_progress` always raises: the observation tool cannot run), `task.py:119`.
- T4 `credit.py:28`: a baseline `known_progress_refs` entry raises.
- T9 `messages/msg_to_child.py:18-19` and `messages/msg_to_child.py:22-23` (two tests of the commission before it is sent).
- T11 `messages/msg_to_child.py:21`.
- T1 `tests/test_binding_form.py`: `yield_controller` and `final_to_parent`; `decide`, `action` and `credit` never.

### ERA — findings
- T4 `credit.py:53`: every result family but `native_bytes` raises (typed native BLAST and HMMER families, API results, local file sources).
- T2 `yield_estimator.py:34`, `task.py:94`, `task.py:198`, `task.py:213`, `messages/internal_summary.py:84`, `messages/internal_summary.py:91`, `messages/read_from_parent.py:117`, `messages/read_from_parent.py:123`, `messages/final_to_parent.py:166`.
- T10 `messages/final_to_parent.py:224`.
- T7 `yield_estimator.py:44-45`: the bounded maximum is the whole `acquired_record_unit`; the old one was `acquired_record_unit * (1 - original fraction)`.
- T8 (narrow) `task.py:176-177`: `TypeError` becomes an `invalid` outcome.
- T1 `tests/test_episode.py`: `credit`, `final_to_parent`, `yield_controller`; `decide` and `action` never.

### PEA — findings
- T3 `credit.py:43`.
- T6 `yield_estimator.py:11-13` (old file returned `None`).
- T8 `task.py:265-266`.
- T11 `task.py:215`, `task.py:258` (`settings.get('tool_registry', {})`; the head reads the same setting without a default, `R/task.py:414`).
- T1 `tests/test_binding.py`: `final_to_parent` only; the credit test reads the source text of `credit.py` (`tests/test_binding.py:92`).

### ESSI — findings
- T3 `credit.py:42`. T6 `yield_estimator.py:11-13`. T8 `task.py:266-267`. T11 `task.py:216`, `task.py:259`.
- T1 `tests/test_binding.py`: `final_to_parent` only (`tests/test_binding.py:91` reads source text).

### SRA — findings
- T3 `credit.py:42`. T6 `yield_estimator.py:11-13`. T8 `task.py:262-263`. T11 `task.py:212`, `task.py:255`.
- T1 `tests/test_binding.py`: `final_to_parent` only (`tests/test_binding.py:91` reads source text).

### SEE — findings
- T3 `credit.py:42`. T6 `yield_estimator.py:11-13`. T8 `task.py:278-279`. T11 `task.py:206`, `task.py:271`.
- T1 `tests/test_binding.py`: `final_to_parent` only (`tests/test_binding.py:95` reads source text).

### SEE/passage — findings
- T3 `credit.py:42`. T6 `yield_estimator.py:11-13`. T8 `task.py:233-234`. T11 `task.py:165`, `task.py:226`.
- T1 `tests/test_binding.py`: `final_to_parent` once; `decide`, `action`, `credit` never.

### SEE/coverage — findings
- T3 `credit.py:42`. T6 `yield_estimator.py:11-13`. T8 `task.py:240-241`. T11 `task.py:172`, `task.py:233`.
- T1 `tests/test_source_coverage_improvement_binding.py`: 3 tests; none calls `decide`, `action`, `credit` or `final_to_parent`.

### SEE/table — findings
- T3 `credit.py:42`. T6 `yield_estimator.py:11-13`. T8 `task.py:241-242`. T11 `task.py:170`, `task.py:234`.
- T1 `tests/test_table_evidence_extraction_binding.py`: 4 tests; none calls `decide`, `action`, `credit` or `final_to_parent`.

### RRA — findings
- T5 `credit.py:11-17`: the credit is `credit_view(assignment)['credit']` of the service `resources` (`task.py:207`), which no library module provides.
- T6 `yield_estimator.py:12-14` (old file handed the choice to `controller_factory`).
- T11 `task.py:164`, `messages/final_to_parent.py:78`.
- T1 `tests/test_binding.py`: 3 tests; none calls `decide`, `action`, `credit` or `final_to_parent`.

### RWS — findings
- T2 `task.py:140`: `blocked()` always raises, and `read_adapters` (`task.py:148`) and `adapters` (`task.py:156`) call it before their own `return`. Every decision and every resource tool raises; the lines after the raise (`task.py:149`, `task.py:157`) are never reached.
- T9 `task.py:359-373` with `task.py:396` and `task.py:403-404`: `check_child_selection` tests the model's commission of a resource child in `action` and returns it to the model as rejection feedback.
- T5 `credit.py:13`: `completion_target * len(execution_handoffs)` is a new formula.
- T6 `yield_estimator.py:14-16`.
- T11 `messages/read_from_child.py:19` (two-level fallback over the child's field names), `messages/read_from_child.py:22`.
- T1 `tests/test_binding.py`: `decide` and `action` are called only to assert the `NotImplementedError` (`tests/test_binding.py:179-185`).

### RWS/api — findings
- T5 `credit.py:12-13`: the credit is the `adapter_credit` the service `resource_adapter` returned (`task.py:174-179`); the service is not provided (`task.py:18-26`).
- T6 `yield_estimator.py:10-12` (completion, the carrier's choice).
- T11 `messages/internal_summary.py:38`, `task.py:245`.
- T1 `tests/test_api_resource_work_execution_binding.py`: `credit`, `final_to_parent`; `decide` and `action` never.

### RWS/hpc — findings
- T2 `task.py:86`, `task.py:128`, `task.py:141`: each raises before its own `return` (`task.py:88`, `task.py:130-131`, `task.py:144-145` are never reached); no decision and no adapter tool can run.
- T5 `credit.py:12`: `float(len(execution_handoffs))` is a new formula (its parent RWS counts the same handoffs times `completion_target`).
- T6 `yield_estimator.py:14-16`.
- T1 `tests/test_binding.py`: `credit`, `final_to_parent`, `yield_controller`; `decide` and `action` never.

### RWS/local — findings
- T5 `credit.py:11-17`: pass-through of `credit_view` of the service `resources`.
- T6 `yield_estimator.py:11-13`.
- T11 `messages/final_to_parent.py:79`.
- T1 `tests/test_binding.py`: 3 tests; none calls `decide`, `action`, `credit` or `final_to_parent`.

## Function accounting (check 7): three old functions per episode

"confirmed" = the behaviour is in the named new lines. "partial" = part of it is. "not carried" = no code in the
episode folder has it (a note in `episode_intent/` is not counted). "blocked" = the code is written and cannot be
reached, or raises.

| Episode | Old function (file at `97308b94c`) | New location | Result |
|---|---|---|---|
| HEAD | `yield_estimator.py` `SequenceHomologyEvidenceYield.yield_controller` | `yield_estimator.py:18-24` | confirmed (bounded quality; the two other kinds could not be reached for this projector) |
| HEAD | `execution_planning.py` `read` | `task.py:459-464` | not carried (stub) |
| HEAD | `to_parent.py` `ScientificReport.facts` | `messages/final_to_parent.py:76-79` | not carried (raises; alignment-site sources not declared) |
| EJS | `credit.py` `_live_project_credit` | `credit.py:21-24` | confirmed (the usable-handoff re-read is replaced by the child's report) |
| EJS | `yield_estimator.py` `_launch_yield_controller` | `yield_estimator.py:24-34` | partial (see T7) |
| EJS | `blast_request_custody.py` `_validate_blast_launch_selection` | none; `messages/read_from_parent.py:94` raises for the request it served | not carried |
| EJS/api | `credit.py` `_live_project_credit` (`api_execution.credit_view`) | `credit.py:14-18` | blocked (pass-through of a service reply) |
| EJS/api | `yield_estimator.py` `_launch_api_yield_controller` | `yield_estimator.py:32-35` | confirmed |
| EJS/api | `blast_request_custody.py` `_validate_blast_api_parent_request` | none | not carried |
| EJS/hpc | `terminal_execution.py` `TerminalExecutionBehavior.execute` | `task.py:102-131` | partial (receipt, context and validations are there; the transport `task.py:89-99` raises; the old `state.begin` intent that made a repeated key return its receipt is not in the tool) |
| EJS/hpc | `terminal_execution.py` `credit_view` | `credit.py:13-15` | confirmed |
| EJS/hpc | `yield_estimator.py` `_launch_hpc_yield_controller` | `yield_estimator.py:13-19` | confirmed |
| EJS/local | `terminal_execution.py` `TerminalExecutionBehavior.execute` | `task.py:122-139` | blocked (the whole behaviour is asked of `job_access.exec_command`) |
| EJS/local | `terminal_execution.py` `credit_view` | `credit.py:13-15` | confirmed |
| EJS/local | `terminal_execution.py` `facts` | `messages/final_to_parent.py:130` (`_facts`) | confirmed |
| EPA | `progress_operations.py` `ProgressOperations.execute` | `task.py:115-152` | partial (`progress_read`, `progress_log` confirmed; `progress_observe` raises at `task.py:107`) |
| EPA | `yield_estimator.py` `blast_monitor_yield` | `yield_estimator.py:28-30` | confirmed (as a completion controller with the information unit as target) |
| EPA | `to_parent.py` `MonitorReport.facts` | `messages/final_to_parent.py:95-105` | confirmed |
| ERA | `result_acquisition.py` `_generic_result_selector_progress` | `credit.py:28-45` | confirmed |
| ERA | `yield_estimator.py` `_results_yield_controller` | `yield_estimator.py:30-45` | partial (native byte selectors only; see T2, T7) |
| ERA | `blast_result_grading.py` `_blast_grader_rows` | none | not carried |
| PEA | `source_operations.py` `LiteratureOperations.catalog` | `task.py:212-227` with `task.py:51-161` | confirmed (the tool descriptions and input schemas are written out in the episode; the old code read them from the tool catalog) |
| PEA | `source_operations.py` `LiteratureOperations.execute` | `task.py:246-266` | confirmed |
| PEA | `to_parent.py` `LiteratureReport.validate_report` | `messages/final_to_parent.py:39-46` | partial (form and held references; the assignment is not validated again) |
| ESSI | `source_operations.py` `LiteratureOperations.catalog` | `task.py:220` | confirmed |
| ESSI | `source_operations.py` `_tool_arguments` | `task.py:241` (`admitted`) | confirmed |
| ESSI | `to_child_source_relevance_assessment.py` `prepare_request` | `messages/msg_to_child.py:14-19` | confirmed |
| SRA | `source_operations.py` `LiteratureOperations.execute` | `task.py:243` (`run_access_tool`) | confirmed |
| SRA | `to_child_source_evidence_examination.py` `prepare_request` | `messages/msg_to_child.py:15-20` | confirmed |
| SRA | `from_parent.py` `_validate_assignment` | `messages/read_from_parent.py:25-27` | partial (the form; every reference in scope and being a source is not tested) |
| SEE | `source_references.py` `_within_source` | `task.py:231-244` | confirmed |
| SEE | `source_operations.py` `_tool_arguments` (page branch) | `task.py:247-256` | confirmed |
| SEE | `from_parent.py` `_validate_page` | none (`literature_source_artifact_mismatch` is in no file of the folder) | not carried |
| SEE/passage | `from_parent.py` `_validate_assignment` (spans) | `messages/read_from_parent.py:38-52` | partial (`source_offset_out_of_bounds` and the artifact test are absent) |
| SEE/passage | `source_operations.py` `_tool_arguments` | `task.py:202` | confirmed |
| SEE/passage | `to_parent.py` `validate_report` | `messages/final_to_parent.py:31-43` | confirmed |
| SEE/coverage | `source_references.py` `_artifact` | `messages/internal_summary.py:17-22` | confirmed |
| SEE/coverage | `source_operations.py` `LiteratureOperations.execute` | `task.py:221` | confirmed |
| SEE/coverage | `from_parent.py` `_validate_assignment` (window) | `messages/read_from_parent.py:38` | partial (as SEE/passage) |
| SEE/table | `source_operations.py` `_tool_arguments` (sheet rule) | `task.py:207` (`literature_table_sheet_mismatch`) | confirmed |
| SEE/table | `from_parent.py` assignment schema (table or window) | `messages/read_from_parent.py:58-66` | confirmed |
| SEE/table | `to_parent.py` `validate_report` | `messages/final_to_parent.py:34` | confirmed |
| RRA | `execution_operations.py` `OperationalOperations.execute` | `task.py:210-241` | confirmed (against a service that is not provided) |
| RRA | `to_parent.py` `OperationalReport.facts` | `messages/final_to_parent.py:40-55` | confirmed |
| RRA | `credit.py` `ResourceEpisodeCredit.credit_view` | `credit.py:10-17` | confirmed as delegation (T5) |
| RWS | `execution_operations.py` `capabilities` | `task.py:113-127` | confirmed |
| RWS | `execution_operations.py` `execute` | `task.py:160-200` | blocked (`task.py:152-157`) |
| RWS | `from_parent.py` `_require_launch_child_instruction_pins` | `task.py:359-373` | confirmed (and finding T9) |
| RWS/api | `from_parent.py` `prepare_assignment` (capability test) | `task.py:126-139` | confirmed |
| RWS/api | `execution_operations.py` `execute` | `task.py:146-179` | confirmed (against a service that is not provided) |
| RWS/api | `credit.py` `credit_view` | `credit.py:11-13` | confirmed as delegation (T5) |
| RWS/hpc | `execution_operations.py` `capabilities` | `task.py:91-101` | blocked (`task.py:81-88`) |
| RWS/hpc | `execution_operations.py` `execute` | `task.py:148-163` | blocked (`task.py:134-145`) |
| RWS/hpc | `credit.py` `credit_view` | `credit.py:11-12` | not carried (new formula) |
| RWS/local | `execution_operations.py` `execute` | `task.py:216` (`resource_tool`) | confirmed (against a service that is not provided) |
| RWS/local | `to_parent.py` `OperationalReport.facts` | `messages/final_to_parent.py:39` (`facts_from`) | confirmed |
| RWS/local | `credit.py` `credit_view` | `credit.py:10-17` | confirmed as delegation (T5) |

Of 57: 37 confirmed, 8 partial, 5 blocked, 7 not carried.

## Totals by finding type

| Code | Finding type | Episodes | Sites |
|---|---|---|---|
| T1 | Tests do not exercise the decide/action/credit/final_to_parent paths in a run | 19 | 19 test files |
| T6 | Yield controller is the carrier's choice (old file chose nothing) | 12 | 12 |
| T11 | Silent default or fallback | 12 | 22 |
| T2 | `NotImplementedError` in place of old behaviour or a missing service | 9 | 28 |
| T8 | `except Exception` to an outcome | 9 | 9 (and 2 narrow catches in EJS, ERA) |
| T3 | Credit cannot run under custody (`read_snapshot`, `store.db` in the library call) | 8 | 8 |
| T5 | Credit number not from the old episode file | 6 | 6 |
| T10 | Declared return field that raises when selected | 5 | 7 |
| T9 | Commission checked ahead or returned to the model as feedback | 3 | 4 |
| T4 | `credit.py` raises `NotImplementedError` | 2 | 2 |
| T7 | Yield controller deviates from the old one | 2 | 2 |

Episodes with at least one severity-A finding (T2, T3, T4 or T9): 16. The three without one are RRA, RWS/api and
RWS/local; their code assumes the services `resources`, `resource_adapter`, `native_events` and
`instruction_libraries`, which no library module provides.

## Observations that are not counted

- Service names differ between episodes that need the same thing: `job_access` (EJS and its three children, EPA,
  ERA), `resource_adapters` (RWS), `resource_adapter` (RWS/api, RWS/hpc), `resources` with `native_events` and
  `instruction_libraries` (RWS/local, RRA). `LAUNCH_MONITOR_EXTRACT_MECHANICS.md` names only `job_access` and
  `estimate_table`.
- The settings key of the launch-instruction library is `launch_instruction_directory` in HEAD (`R/task.py:333`),
  SEE/coverage and SEE/table, and `launch_instructions_directory` in EJS, its children, EPA, ERA and RWS.
- EJS cannot pass records to its HPC child: EJS/hpc declares no `record_refs` field
  (`R/execution_job_submission/messages/msg_to_child.py:21-22`).
- Fifteen assertions in six test files expect `NotImplementedError`, so the blocked state is what the suite
  checks (for example `R/resource_work_submission/tests/test_binding.py:179-185`,
  `R/execution_result_acquisition/tests/test_episode.py:121-228`).
- The BLAST database-grader custody of the old launch, API and results episodes (`_blast_launch_requirement`,
  `_validate_blast_launch_selection`, `_validate_blast_api_parent_request`, `_blast_target_requirement`,
  `_blast_grader_rows`) is in no file of the axis; `episode_intent/a101/` lists these as "not placed" or
  "machinery".
