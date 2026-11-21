# A101 branch runs (19 November 2026)

Runner report; nothing in the episodes, library or runner was edited. One test file was written:
`root/a101/sequence_homology_evidence/execution_result_acquisition/tests/test_branch_execution_result_acquisition_model_run.py`
(two `@pytest.mark.model_run` tests; the held world is the caller's: a real Store, `job_services(...)`, a real detached
local job launched through `JobAccess.launch` by the job probe test episode, the entry assignment built from that launch
as the commissioner would: handoff row ref, `execution_target_v1` with the job directory as workspace, selector
`{'paths': [<job dir>/result.txt]}`, credit unit 1.0). No remote service was contacted.

## 1. execution_result_acquisition, plain fetch of a local file result: FAIL

Runs (real model, Codex credential): finished job `runs/brm_a101_3` (log `runs/brm_a101_3.log`); not-yet-finished job
`runs/brm_a101_4` (log `runs/brm_a101_4.log`). (Runs `_1`, `_2` were my fixture errors, fixed: `-k` matched both tests,
`Store` has no `.table`.)

Journal facts, both worlds identical: the entry assignment admitted (family `native_bytes`); one model call; the
model's only decision was `execution_results_status` with `{}`; that unit raised before an outcome, so no unit outcome,
no credit, no `ended_by`, no return, no resume to test. The job itself was launched and (finished case) had ended, so
the world is sound.

Error: `NotImplementedError: BLOCKED-ON-JOB-SERVICE: job_access.observe_target` at
`execution_result_acquisition/task.py:115` (`_service_call`), reached from `_execute_native_results` (task.py:174).
The model did what the offered catalog allowed.

Classification: EPISODE (task) with a LIBRARY/RUNNER-side gap in what `JobAccess` offers.

Diagnosis: for a plain local-file target the family is `native_bytes` and `_catalog` (task.py:547) offers only
`execution_results_status`, `_collect` and `_read`. They call `job_access.observe_target` and `.read_file`
(task.py:174, 181), which `JobAccess` (`episode_runtime/job_access.py`) does not have; it has `check`, `fetch`, `cancel`,
`run`. `execution_results_fetch` (task.py:206, the correct `JobAccess.fetch` call) exists but is offered only for the
`blast_graded` and `phmmer_graded` families (`_blast_catalog`, `_phmmer_catalog`), never for `native_bytes`. So a plain
fetch of a local job result cannot run, and a not-yet-finished job cannot be tested either (it fails on the same first
call, before any "results_not_available" outcome is reachable).

Smallest suspected fix: in `task.py::_catalog` for `native_bytes` offer `FETCH` (while the handoff is held and not
closed) and have `execution_results_fetch`'s outcome feed credit; then `internal_summary` (non-graded branch, lines
~170-239), `credit.py::credit` (native_bytes: coverage fraction over `summary['results']`, which fetch results do not
populate), `yield_estimator.py` (native_bytes needs `results_yield_profiles` / `task_yield_profiles`; I supplied
`native_unbounded_local` and `results:native_finite_local`) and `final_to_parent` must read the fetch outcome's
`results`/`result_refs` into `execution_result_refs`. Alternatively give `JobAccess` the two members
(`observe_target`, `read_file`) the status/collect/read tools were written against.

Also noticed (not run): `_selected_execution_task` and `family` need `target['assignment']['workspace']` for
`native_bytes`; nothing in the handoff row carries it, so the commissioner (`msg_to_child._results` of the head, per
AXIS_WAVE_BLOCKERS_a101.md section 1) must build it from the row's `detail['native']['directory']`.

## 2. resource_result_acquisition: NOT RUN

It does not run the same way: its entry is an `execution_handoff_v1` record plus `requested_data_selector` (old
`RESULTS_SCHEMA`), it serves through the `resources` adapter service chosen by the handoff's `resource_selection`, and its
prompt is the literature-investigation text with report/reasoning-commit actions (task.py header). It has no
`execution_results_fetch`-like path from a `JobAccess` handoff row without building an old-form handoff, so it was not
run with this world. Only `tests/test_binding.py` exists for it.
