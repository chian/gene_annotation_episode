# Audit of the carry-over, axis a103 (19 November 2026)

Read-only audit of every episode folder under `gene_annotation_episode/episodic_workflow/root/a103/`. 34 episodes.
No code or test was changed. Paths below are relative to `root/a103/gene_context_evidence/` (written `G/`); the head
episode is `G` itself.

Result: **0 PASS, 34 with findings.** Checks 1 (file set) and 2 (`episode.py`) pass for all 34.

## What was checked, and how far

- Checks 1 and 2: listing and the class/import lines of all 34 `episode.py`. All have exactly the ten-file set (leaves
  without `msg_to_child.py`/`read_from_child.py`), one `class X(EpisodeBinding)`, no import from another episode
  folder (the six `from ..` imports are inside `messages/` and reach the episode's own `credit.py`/`task.py`), no
  table of bindings.
- Checks 3 to 5: every `credit.py`, `yield_estimator.py`, `msg_to_child.py`, `read_from_child.py` and `goal.py` read in
  full; `task.py` and the other `messages/` files read in full for the head and the seven literature episodes, and
  for `execution_job_submission` and `execution_progress_assessment` at head level. The other job-family files
  (about 9,000 lines, most of them copies) were read in outline and by targeted search (every `NotImplementedError`,
  `try`/`except`, `records.holds`, `settings.get(..., default)`, service name, time use), not line by line.
- Check 4, old side: each episode's old `yield_estimator.py` and the old `credit.py` of the literature and resource
  episodes read with `git show 97308b94c:<path>`; mapping judged against `carry_over_guide/README.md` 7b.
- Check 6: every test file classified by what it calls. One run through the launcher:
  `runs/audit_a103_2`, 272 passed in 5.4 s.
- Check 7: three old functions per episode (102), taken from `runs/carry_over/functions/<episode>.tsv` by a fixed
  rule (the longest function of the report file, of the operations file, and of the from-parent/summary file). For
  each, the error codes and field names in the old body were searched in the new episode's ten files; every miss was
  then read by hand. Table at the end.

Not verified by running: the credit failure below is established from the source (the library calls a method the
object it is handed does not have); no test was written to show it.

## Finding types

| Code | Meaning | Rule |
|---|---|---|
| CREDIT-CUSTODY | `credit` calls `A103ContextCredit`, which calls `store.read_snapshot()` (`episode_support/grading/gene_context_evidence/credit.py:87`) and reads `store.db` (`records/gene_context_evidence/attachments.py:173-178`, `publication.py:64-65`). `credit(summary, records)` is handed a `RecordReader`, which has neither (`episode_runtime/store_scope.py:210-557`; `read_snapshot` is on `ScopedStore` only, :707). The credit cannot return a number under the system | Custody only; credit must be real |
| CREDIT-SERVICE | The credit number is whatever a service's `credit_view` returned to a tool; that service has no implementation, so the credit formula is nowhere in the repository | credit must be real code |
| CREDIT-STUB | A path inside `credit.py` raises `NotImplementedError` | credit must not be a stub |
| SERVICE-MISSING | `SERVICES` names a service no module implements (`job_access`, `estimate_table`, `resource_adapter`, `resources`, `native_events`, `instruction_libraries`); the episode cannot be linked for a real run | behaviour not present |
| STUB-TASK | A tool or `decide` path raises `NotImplementedError` (`BLOCKED-ON-JOB-SERVICE`, `unplaced`, ...) | every episode function ends up somewhere |
| STUB-RETURN | A selectable field declared in `RETURN_FORM` raises `NotImplementedError` in `final_to_parent` when selected | a child declares every field it can return |
| STUB-PARENT | `read_from_parent` raises `NotImplementedError` for part of the assignments its form admits | behaviour not present |
| STUB-YIELD | `yield_controller` raises `NotImplementedError` on a path | one of the three controllers |
| PRECHECK-COMMISSION | `action` checks that the records of a child commission are held and returns the failure to the model through `Rejected` | a wrong commission just fails: no pre-check, no feedback path |
| ERR-HIDE | `except Exception` turned into an outcome, `except ...: pass`, or one error class converted into another | no try/except that hides errors |
| SILENT-DEFAULT | A setting or argument read with a default (`settings.get('tool_registry', {})`, ...) | unplanned cases must raise |
| YIELD-MISMATCH | The controller kind, its maximum/target or its settings source differs from the old episode's yield method | yield matches the old method |
| RULE4-RAW | `read_from_parent` relays the assignment unchanged and `yield_estimator` parses it | estimator reads what `read_from_parent` produced |
| RECORDING-IN-EPISODE | Episode tools keep their own durable SQLite ledger (`HPCLedger` under `settings['directory']`) and a recall device (`once`: return the saved value, else compute and save) | episodes contain no recording or replay code; custody only |
| RETURN-NO-RECORDS | `RETURN_FORM` has no `record_refs` field, so sources the child acquired never reach the parent, whose `report` tool then refuses to cite them | a return names every record the receiver needs (T5) |
| NOT-CARRIED | A sampled old function's behaviour is absent from the new files (a note or a stub stands in) | none is dropped |
| GOAL-PLACEHOLDER | `goal.py` holds a generic sentence; the carried goal text is a constant of `task.py` | `goal.py` supplies the goal |
| TEST-NO-RUN | No test runs the episode with the real runner to a result; `decide` (and mostly `action`) is never called | tests exercise decide/action/credit/final_to_parent |
| TEST-SCRIPTED | A test passes a model answer it wrote itself to `action` | no scripted stand-ins |
| TEST-STANDIN | A test supplies a hand-assembled empty class as a service (`WithoutJobs`) and asserts only that the run fails | no stand-ins |

## Per episode

**G (gene_context_evidence, head)**
- CREDIT-CUSTODY `credit.py:22`, `:26`; `messages/internal_summary.py:58` calls it for every summary, so no `decide` can run.
- PRECHECK-COMMISSION `task.py:94-103`, `:445-450` (rejected at `:485-486`).
- STUB-RETURN `messages/final_to_parent.py:70-74`. `messages/msg_to_child.py:31-33` selects `gene_context_evidence_results` for the recursive child of the top head, so that commission always fails in the child.
- ERR-HIDE `task.py:316-317`.
- SILENT-DEFAULT `task.py:231`, `:244`, `:256`, `:307`, `:452`.
- NOT-CARRIED old `operations.py::execute` [57-86]: `process.execution` and `authenticate_source_byte_operands` are not in `task.py:287-317`.
- TEST-NO-RUN `tests/test_gene_context_evidence_binding.py` (no decide, action, credit, summary); `:171-173` asserts the stub.
- Note: `messages/final_to_parent.py:63-64` fails the run when the controller stops before a `report` unit (same in all seven literature episodes).

**G/execution_job_submission**
- SERVICE-MISSING `task.py:67`. STUB-TASK `task.py:106`, `:127`, `:153`, `:181`, `:231`. ERR-HIDE `task.py:124-129`.
- STUB-PARENT `messages/read_from_parent.py:95`. STUB-RETURN `messages/final_to_parent.py:197`, `:199`.
- `messages/msg_to_child.py:25`, `:71` selects `execution_handoff_refs` from `launch_hpc`, whose `final_to_parent` raises on that field (below): every `launch_hpc` commission fails at its return.
- NOT-CARRIED `internal_summary.py::resource_tool_contracts`; the usable-handoff read of held records (`credit.py:12-18` uses the child's report instead).
- TEST-NO-RUN `tests/test_binding.py` (`:221` calls `action` with `{}` only).

**G/execution_job_submission/api_job_execution**
- SERVICE-MISSING `task.py:53`. STUB-TASK `task.py:86`, `:93`, `:458`. ERR-HIDE `task.py:83-86`, `:481-484`.
- CREDIT-SERVICE `credit.py:15` (`messages/internal_summary.py:148`).
- NOT-CARRIED `resource_tool_contracts`. TEST-NO-RUN.

**G/execution_job_submission/hpc_job_execution**
- SERVICE-MISSING `task.py:33`. STUB-RETURN `messages/final_to_parent.py:97`. NOT-CARRIED `resource_tool_contracts`. TEST-NO-RUN (3 tests, none of decide/action/credit/final).

**G/execution_job_submission/local_job_execution**
- SERVICE-MISSING `task.py:34`. STUB-TASK `task.py:101-104`. STUB-RETURN `messages/final_to_parent.py:127`, `:129`. NOT-CARRIED `resource_tool_contracts`. TEST-NO-RUN.

**G/execution_progress_assessment**
- SERVICE-MISSING `task.py:46` (read by `decide`, `:171`). STUB-TASK `task.py:101-108`: `progress_observe`, the episode's one observing tool, always raises.
- CREDIT-STUB `credit.py:24-29`. SILENT-DEFAULT `messages/msg_to_child.py:19`.
- NOT-CARRIED old `to_parent.py::validate_report` [62-91]: the permitted-record check is not in `messages/final_to_parent.py`.
- TEST-NO-RUN.

**G/execution_result_acquisition**
- SERVICE-MISSING `task.py:31`. STUB-TASK `task.py:95`. STUB-PARENT `messages/read_from_parent.py:62`.
- YIELD-MISMATCH `yield_estimator.py:27-29`: the maximum is the unit; the old one was the unit times the fraction earlier results left uncovered. The old typed and API branches are not there. SILENT-DEFAULT `yield_estimator.py:24`, `:27`.
- NOT-CARRIED old `result_selection.py::_selector` [17-66] (native typed selectors). TEST-NO-RUN.

**G/hpc_work_planning**
- SERVICE-MISSING `task.py:106` (`decide` reads `estimate_table`, `:1260-1267`).
- STUB-TASK `task.py:247`, `:257`, `:268`, `:281`, `:294`, `:306`, `:316`, `:326`, `:339`, `:348`, `:358`, `:544`, `:558`, `:853`, `:1054`, `:1189`, `:1202`.
- RECORDING-IN-EPISODE `task.py:561-568`, `:575-590`, `:593-603`.
- PRECHECK-COMMISSION `task.py:1309-1315`.
- Note: `yield_estimator.py:14` takes the cost from settings; the old one took it from the commission.
- TEST-NO-RUN `tests/test_binding.py` (7 assertions on stubs).

**G/hpc_work_planning/execution_job_submission**
- SERVICE-MISSING `task.py:62`. STUB-TASK `task.py:205`, `:247`. STUB-RETURN `messages/final_to_parent.py:125`. SILENT-DEFAULT `task.py:119`, `:163`, `:176`.
- `messages/msg_to_child.py:19`, `:40` selects `execution_handoff_refs` from `launch_hpc`, which raises on it: every `launch_hpc` commission fails at its return.
- TEST-NO-RUN.

**G/hpc_work_planning/execution_job_submission/api_job_execution**
- SERVICE-MISSING `task.py:35`. STUB-RETURN `messages/final_to_parent.py:102`. NOT-CARRIED `resource_tool_contracts`. TEST-NO-RUN (4 tests, none of decide/action/credit/final).

**G/hpc_work_planning/execution_job_submission/hpc_job_execution**
- SERVICE-MISSING `task.py:33`. STUB-RETURN `messages/final_to_parent.py:97`. NOT-CARRIED `resource_tool_contracts`. TEST-NO-RUN.

**G/hpc_work_planning/execution_job_submission/local_job_execution**
- SERVICE-MISSING `task.py:34`. STUB-TASK `task.py:101-104`. STUB-RETURN `messages/final_to_parent.py:127`, `:129`. NOT-CARRIED `resource_tool_contracts`. TEST-NO-RUN.

**G/hpc_work_planning/execution_progress_assessment**
- SERVICE-MISSING `task.py:46`. STUB-TASK `task.py:101-108`. CREDIT-STUB `credit.py:24-29`. SILENT-DEFAULT `messages/msg_to_child.py:19`. NOT-CARRIED `validate_report` permitted-record check. TEST-NO-RUN.

**G/hpc_work_planning/execution_result_acquisition**
- SERVICE-MISSING `task.py:31`. STUB-TASK `task.py:95`. STUB-PARENT `messages/read_from_parent.py:62`. YIELD-MISMATCH `yield_estimator.py:27-29`. SILENT-DEFAULT `yield_estimator.py:24`, `:27`. NOT-CARRIED `_selector`. TEST-NO-RUN.

**G/hpc_work_planning/hpc_allocation_execution**
- SERVICE-MISSING `task.py:87`. STUB-TASK `task.py:442`, `:450`. RECORDING-IN-EPISODE `task.py:329`, `:365`, `:393`, `:460`.
- YIELD-MISMATCH `yield_estimator.py:25-27`: completion with the sum of obligation credits as target. The old controller was the same kind as the planner's (mapped to accumulation there), and the ledger credit also counts model improvement and forecast validation, so it can pass the target (`completion_credit_exceeds_target`).
- TEST-STANDIN `tests/test_binding.py:124`, `:160-164` (the only runner test asserts a failure, with `pytest.raises(Exception)`). TEST-NO-RUN.

**G/hpc_work_planning/hpc_allocation_execution/execution_job_submission**
- SERVICE-MISSING `task.py:53`. STUB-TASK `task.py:154`. STUB-RETURN `messages/final_to_parent.py:123`. NOT-CARRIED `resource_tool_contracts`.
- TEST-SCRIPTED `tests/test_execution_job_submission_binding.py:200-206`. TEST-NO-RUN.

**G/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution**
- SERVICE-MISSING `task.py:35`. STUB-RETURN `messages/final_to_parent.py:102`. NOT-CARRIED `resource_tool_contracts`. TEST-NO-RUN.

**G/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution**
- SERVICE-MISSING `task.py:36`. RULE4-RAW `messages/read_from_parent.py` (the assignment relayed whole) with `yield_estimator.py:19-25`. NOT-CARRIED `resource_tool_contracts`. TEST-NO-RUN (pure-function tests on hand-built summaries).

**G/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution**
- SERVICE-MISSING `task.py:33`. STUB-TASK `task.py:91-94`. STUB-RETURN `messages/final_to_parent.py:127`, `:129`.
- YIELD-MISMATCH `yield_estimator.py:8-9`: `settings['cost']`; the old profile `launch_local:<request class>` is not used (its two sister copies use it).
- NOT-CARRIED `resource_tool_contracts`. TEST-NO-RUN.

**G/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment**
- SERVICE-MISSING `task.py:49`. STUB-TASK `task.py:87`, `:97`, `:107`, `:117`, `:145`. CREDIT-STUB `credit.py:21-25`. SILENT-DEFAULT `messages/msg_to_child.py:22`, `:31`.
- NOT-CARRIED `validate_report` permitted-record check.
- TEST-STANDIN `tests/test_episode_binding.py:75`, `:97-102`. TEST-NO-RUN.

**G/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition**
- SERVICE-MISSING `task.py:31`. STUB-TASK `task.py:95`. STUB-PARENT `messages/read_from_parent.py:62`. YIELD-MISMATCH `yield_estimator.py:27-29`. SILENT-DEFAULT `yield_estimator.py:24`, `:27`. NOT-CARRIED `_selector`. TEST-NO-RUN.

**G/hpc_work_planning/hpc_resource_prediction**
- SERVICE-MISSING `task.py:36`. STUB-TASK `task.py:105` (opening the ledger always raises, so every tool does). STUB-YIELD `yield_estimator.py:13-16`. RECORDING-IN-EPISODE `task.py:276-282`.
- Note: `yield_estimator.py:17` reads the commission from `settings['commissions']`, not from the parent input.
- TEST-NO-RUN.

**G/published_evidence_assessment**
- CREDIT-CUSTODY `credit.py:16`. ERR-HIDE `task.py:157-158`, `:308-309`. SILENT-DEFAULT `task.py:141`, `:163`. RETURN-NO-RECORDS `messages/final_to_parent.py:26-30`.
- TEST-SCRIPTED `tests/test_published_evidence_assessment_binding.py:130-139`. TEST-NO-RUN.

**G/published_evidence_assessment/evidence_search_strategy_improvement**
- CREDIT-CUSTODY `credit.py:15`. PRECHECK-COMMISSION `task.py:374-384`, `:398-399`. ERR-HIDE `task.py:156-157`, `:308-309`. SILENT-DEFAULT `task.py:140`, `:162`. RETURN-NO-RECORDS `messages/final_to_parent.py:31-35`. TEST-NO-RUN.

**G/.../source_relevance_assessment**
- CREDIT-CUSTODY `credit.py:15`. PRECHECK-COMMISSION `task.py:381-397`. ERR-HIDE `task.py:158-159`, `:318-319`. SILENT-DEFAULT `task.py:142`, `:167`. RETURN-NO-RECORDS `messages/final_to_parent.py:29-32`. TEST-NO-RUN.

**G/.../source_evidence_examination**
- CREDIT-CUSTODY `credit.py:15`. ERR-HIDE `task.py:187-188`, `:307-308`. SILENT-DEFAULT `task.py:171`, `:193`. RETURN-NO-RECORDS `messages/final_to_parent.py:28-32`. TEST-NO-RUN.

**G/.../source_evidence_examination/passage_evidence_extraction**
- CREDIT-CUSTODY `credit.py:9`. ERR-HIDE `task.py:254-255`. RETURN-NO-RECORDS `messages/final_to_parent.py:26-30`.
- NOT-CARRIED old `from_parent.py::_validate_assignment` [27-44]: a span is no longer required to be of the page's source and representation (`messages/read_from_parent.py:42-60`), and the offset bound is gone.
- GOAL-PLACEHOLDER `goal.py:4`; the carried text is `task.py:43-48`. TEST-NO-RUN.

**G/.../source_evidence_examination/source_coverage_improvement**
- CREDIT-CUSTODY `credit.py:9`. ERR-HIDE `task.py:255-256`. RETURN-NO-RECORDS `messages/final_to_parent.py:27-31`. NOT-CARRIED the offset bound of `_validate_assignment`.
- GOAL-PLACEHOLDER `goal.py:4` (text in `task.py:43-48`). TEST-SCRIPTED `tests/test_episode.py:108-113`. TEST-NO-RUN.

**G/.../source_evidence_examination/table_evidence_extraction**
- CREDIT-CUSTODY `credit.py:15`. ERR-HIDE `task.py:161-162`, `:281-282`. SILENT-DEFAULT `task.py:145`, `:167`. RETURN-NO-RECORDS `messages/final_to_parent.py:27-31`. NOT-CARRIED the offset bound of `_validate_assignment`. TEST-NO-RUN.

**G/resource_result_acquisition**
- SERVICE-MISSING `task.py:58`. CREDIT-SERVICE `credit.py:11-17`. ERR-HIDE `task.py:274-279`.
- NOT-CARRIED old `resource_selection.py::capabilities` [7-24] (the tool-bound check) and the missing-interface branch of `handoff_check.py::check_selected_handoff`: both left to the unwritten service.
- TEST-NO-RUN (3 tests, none of decide/action/credit/final).

**G/resource_work_submission**
- SERVICE-MISSING `task.py:58`. CREDIT-SERVICE `credit.py:12-13`.
- YIELD-MISMATCH `yield_estimator.py:10-12` with `messages/read_from_parent.py:33`: completion on a new assignment field `completion_target`. The old episode had no estimator of its own (the runner's default controller); its sister `resource_result_acquisition` maps the same case to accumulation.
- TEST-NO-RUN.

**G/resource_work_submission/api_resource_work_execution**, **hpc_resource_work_execution**, **local_resource_work_execution** (three episodes, same findings)
- SERVICE-MISSING `task.py:55` / `:53` / `:53`. CREDIT-SERVICE `credit.py:12-13`. YIELD-MISMATCH `yield_estimator.py:10-12`. TEST-NO-RUN.

## Totals by finding type

| Type | Episodes |
|---|---|
| TEST-NO-RUN | 34 |
| SERVICE-MISSING | 26 |
| NOT-CARRIED | 23 |
| STUB-TASK | 16 |
| SILENT-DEFAULT | 13 |
| STUB-RETURN | 11 |
| ERR-HIDE | 11 |
| YIELD-MISMATCH | 9 |
| CREDIT-CUSTODY | 8 |
| RETURN-NO-RECORDS | 7 |
| CREDIT-SERVICE | 6 |
| PRECHECK-COMMISSION | 4 |
| STUB-PARENT | 4 |
| CREDIT-STUB | 3 |
| RECORDING-IN-EPISODE | 3 |
| TEST-SCRIPTED | 3 |
| TEST-STANDIN | 2 |
| GOAL-PLACEHOLDER | 2 |
| RULE4-RAW | 1 |
| STUB-YIELD | 1 |

21 episodes have at least one `NotImplementedError` stub (STUB-TASK, STUB-RETURN, STUB-PARENT, STUB-YIELD or
CREDIT-STUB). 17 episodes have a credit that cannot produce its number today (CREDIT-CUSTODY 8, CREDIT-SERVICE 6,
CREDIT-STUB 3). No episode bounds, clamps or rescales its credit. No episode has an elapsed-time, token, turn or
count cutoff; the only stop is the controller. No episode file touches `store.db` itself.

## Function accounting (check 7)

"n/m" is how many of the old body's error codes and field names occur in the new episode's ten files. A miss that is
only a renamed tool (`hpc.read` to `hpc_read`) or a role name is counted as carried. For the job, HPC and resource
families "Carried" rests on this match and on reading the misses; the new bodies were not compared line by line.

| Episode(s) | Old function | n/m | Verdict |
|---|---|---|---|
| head | `to_parent.py::validate_report` [36-59] | 1/4 | Own-report check carried; the frozen-results check read the old journal and is not carried |
| head | `operations.py::execute` [57-86] | 11/18 | Partly: `process.execution` and source-byte authentication absent (NOT-CARRIED) |
| head | `from_parent.py::prepare_invocation` [102-143] | 2/14 | Old-runner invocation record; not carried, correctly |
| PEA, ESSI, SRA | `to_parent.py::validate_report`; `source_operations.py::catalog`; `from_parent.py::_validate_assignment` | all found | Carried (`final_to_parent.py`, `task.py` `catalog`); the commission checks dropped as rule 1 says |
| SEE | `validate_report`; `catalog`; `source_references.py::_within_source` | all found | Carried (`task.py:137-150`) |
| table | `validate_report`; `source_operations.py::_tool_arguments` [34-52]; `_validate_assignment` | 1/1, 8/8, 3/4 | Carried except the offset bound |
| passage | `validate_report`; `catalog`; `_validate_assignment` | 0/1, 3/4, 1/4 | First two carried (the miss is the role name); third NOT-CARRIED |
| coverage | same three | 0/1, 3/4, 3/4 | Carried except the offset bound |
| EJS (3 copies) | `to_parent.py::_live_facts` [60-99] | 9/10, 7/10, 7/10 | Carried in part; the selectable native-family fields raise (STUB-RETURN) |
| EJS (3 copies) | `operations.py::initialize` [14-26] | 1/1 | Carried |
| EJS (3 copies) | `internal_summary.py::resource_tool_contracts` | 0/1, 1/1, 0/1 | Carried only in `hpc_work_planning/execution_job_submission`; elsewhere NOT-CARRIED |
| api_job_execution (3) | `to_parent.py::_live_facts` [60-95] | 2/2 | Carried |
| api_job_execution (3) | `operations.py::_check_parent_inputs` [22-37] | 1/3, 0/3, 0/3 | Read the parent's row of the old runner's table; not carried, correctly |
| api_job_execution (3) | `resource_tool_contracts` | 0/1 | NOT-CARRIED |
| hpc_job_execution (3) | `to_parent.py::_live_facts` [62-109] | 8/12 | Partly; file-capture fields absent |
| hpc_job_execution (3) | `terminal_operations.py::execute` [14-47] | 4/6, 4/6, 5/6 | Carried |
| hpc_job_execution (3) | `resource_tool_contracts` | 0/1 | NOT-CARRIED |
| local_job_execution (3) | `to_parent.py::_live_facts` | 10/12 | Carried in part (STUB-RETURN fields) |
| local_job_execution (3) | `terminal_operations.py::execute` | 3/6 | The call itself is the blocked service call (STUB-TASK) |
| local_job_execution (3) | `resource_tool_contracts` | 0/1 | NOT-CARRIED |
| execution_progress_assessment (3) | `to_parent.py::validate_report` [62-91] | 3/7, 3/7, 4/7 | NOT-CARRIED in part (permitted-record check) |
| execution_progress_assessment (3) | `progress_operations.py::execute` [24-58] | 10/12, 10/12, 11/12 | Carried, except that observing raises (STUB-TASK) |
| execution_progress_assessment (3) | `from_parent.py::_assignment` [15-24] | 1/4, 1/4, 2/4 | The misses are checks of its own commission against the provider; dropped as rule 1 says |
| execution_result_acquisition (3) | `to_parent.py::_live_facts` [55-100] | 8/10 | Carried |
| execution_result_acquisition (3) | `retained_result_acquisition.py::_execute_native_results` [20-70] | 6/8 | Carried (misses are renamed tools) |
| execution_result_acquisition (3) | `result_selection.py::_selector` [17-66] | 4/14 | NOT-CARRIED (typed selectors; STUB-PARENT) |
| hpc_work_planning | `to_parent.py::facts`; `allocation_results.py::_collect_original_results`; `internal_summary.py::decision_context` | 2/2, 6/7, 24/25 | Carried |
| hpc_allocation_execution | same three | 2/2, 7/7, 22/25 | Carried |
| hpc_resource_prediction | `to_parent.py::facts`; `prediction_operations.py::execute` [38-147]; `decision_context` | 2/2, 15/19, 16/17 | Carried in text; unreachable while the ledger open raises |
| resource_result_acquisition | `to_parent.py::facts`; `handoff_check.py::check_selected_handoff`; `resource_selection.py::capabilities` | 5/5, 3/4, 2/3 | First carried; the other two partly (NOT-CARRIED) |
| resource_work_submission | same three | 5/5, 4/4, 1/3 | First two carried; `capabilities` checks left to the service |
| resource leaves (3) | `to_parent.py::facts`; `check_selected_handoff`; `from_parent.py::prepare_assignment` [24-47] | 5/5; 3/4, 3/4, 4/4; 6/7 | Carried; the one miss in `prepare_assignment` is a check of its own commission |

## Run directories

`runs/audit_a103_2` (the test run). `runs/audit_a103_1/home` is an empty directory left by a first attempt that the
launcher refused.
