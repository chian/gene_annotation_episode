# A107 branch runs: hpc_work_planning subtree (19 November 2026)

Runner report only; nothing fixed. Real model credential exposed, but no branch reached a model call: each fails before
the first model decision (the first unit of both sisters is a code-issued tool call, `hpc_open` / `hpc_read`).
No journal rows beyond what is noted. Nothing remote was contacted; Aurora was never authenticated to. The real remote
system would be needed for: `hpc_discovery_run` (SSH read-only commands), `hpc_queue_observe` (PBS queue and ALCF score),
the launch, monitor and fetch children (qsub/qstat/read_output), and the `job_access` service routes. None of those was
reached.

Tests written (my fixtures; the commission, resources and settings are real-shaped, `job_services` is the real library
function over local paths):
- `root/a107/partner_presence_evidence/hpc_work_planning/hpc_resource_prediction/tests/test_branch_hpc_resource_prediction_model_run.py`
- `.../hpc_work_planning/hpc_allocation_execution/tests/test_branch_hpc_allocation_execution_model_run.py`
- `.../hpc_work_planning/tests/test_branch_hpc_work_planning_model_run.py`

## Branch 1: hpc_resource_prediction alone: FAIL

Run dir `runs/brm_a107_2`, log `runs/brm_a107_2.log`. Two tests.

1. `test_link_with_the_real_job_services_and_no_hpc_ledger_service`: `link` raises
   `LinkError('service_required:partner_presence_evidence/hpc_work_planning/hpc_resource_prediction:hpc_ledger')`
   (`episode_runtime/runner.py:267`). Classification: EPISODE. `task.py:83` `SERVICES = ('hpc_ledger', 'job_access',
   'estimate_table')` still declares `hpc_ledger` as a service; `jobs/job_services.py` says the ledger "is not a service" but
   the work table `HPC_LEDGER`.
2. With a placeholder `hpc_ledger` factory (fixture only, to see the next break): run starts, unit 1 is the code-issued
   `ToolCall('hpc_open')` (`task.py:548`), which raises
   `NotImplementedError: BLOCKED-ON-JOB-SERVICE: hpc_ledger ...` at `task.py:129` (`_open_ledger`, called from
   `hpc_open` `task.py:397`). No unit is journaled, no model call, no credit, no close.

Journal facts: no completed unit, no model calls, run not closed.

Model decisions: none.

Diagnosis (EPISODE): `hpc_resource_prediction/task.py` was not carried onto `HpcLedger` (IMPORT_FIX_NOTES lists only the
planning/execution tasks of other axes; for A107 only the execution sister was adapted). `_open_ledger` is still the
stub; `_commission` (`task.py:378`) also calls `hpc_commission_sources.read(ctx.store, ...)` flagged BLOCKED-ON-STORE-ACCESS
for the `commission_source_ref` form. `_remote` (`:135`) and `_acquire_queue` are job_access stubs. Smallest fix: remove
`'hpc_ledger'` from `SERVICES` (`task.py:83`); make `_open_ledger` (`:128`) return `HpcLedger.open(ctx.store, commission)`
in `hpc_open` and `HpcLedger.existing(ctx.store, arguments['ledger'])` in the other tools; add a `ledger` field to the
assignment form (`messages/read_from_parent.py`) and to the tool schemas (as the execution sister already has);
replace `ledger.once`/`.path` calls by the local `recorded` helper as in the execution sister; the test
`test_binding_form.py::test_the_ledger_is_not_available_without_its_service` and the `services` assertion in
`test_importing_episode...` then change. Also note the `hpc_commission` shown after `hpc_open`: `ledger.commission` now
exists on `HpcLedger`, but the old `ledger.read('owner')` identity check (`task.py:398`) needs an `owner` row written by
`hpc_open`.

## Branch 2: hpc_allocation_execution alone: FAIL

Run dir `runs/brm_a107_6` (earlier fixture-only failures: `brm_a107_3` children not registered, `brm_a107_4` per-child
settings, `brm_a107_5` missing `cutoff`), log `runs/brm_a107_6.log`.

Run links (subtree of 7 episodes, real `job_services`), starts, unit 1 is the code-issued `hpc_read` of `'commission'`
(`task.py:1121`) and raises
`ValueError: original_hpc_commission_missing:commission` (`jobs/hpc_ledger.py:56`, `read`, via `HpcLedger.existing`
`:65` from `open_ledger` `task.py:504`). No unit journaled, no model call.

Classification: WORLD limitation caused by a SYSTEM gap, plus an EPISODE inconsistency. The sister works on a ledger its
parent or prediction sister opened; a run's caller cannot write `HPC_LEDGER` rows (`Store` has no `table`; only a unit's
`ctx.store.table(...)` does, `episode_runtime/store_scope.py:962`), so a standalone caller-built world cannot hold the
commission/owner/model rows or pass `ledger_row_refs`. This branch can only be run after branch 1 (or the planning head)
creates the ledger in the same run. Not fixed by me. Smallest fix options: (a) a caller-side way to put declared work-table
rows into a run's Store as origin `caller` with refs usable in `ledger_row_refs` (RUNNER), or (b) run it under the head
once branch 3 works.

Other findings in this branch:
- `yield_estimator.py:14` reads `settings['cutoff']`; the prediction sister and the other episodes read `settings['cost']`.
  A fixture needs both. Likely EPISODE inconsistency (one name should be used).
- `decide` (`task.py:1139`) reads `ctx.services['estimate_table'].read('resource_tool_estimates', 'hpc_execution')` and the
  episode's own stubs at `task.py:208-330` (`handoff_target`, `observe_target`, `read_window`, `write_allocation_control`,
  `observe_queue_value`, `run_command`, `estimate_*`) still raise `NotImplementedError('BLOCKED-ON-JOB-SERVICE...')`;
  they were not reached. The real `EstimateTable` (`episode_runtime/estimate_table.py`) and `JobAccess` exist, so those
  stubs can now be written against them. A real remote system would be needed only where a stub reaches PBS/SSH.
- Not reached: ledger rows, predictions, refusals; nothing was written.

## Branch 3: hpc_work_planning over its children: FAIL

Run dir `runs/brm_a107_7`, log `runs/brm_a107_7.log`.

`ModuleNotFoundError: No module named 'gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence.hpc_ledger'`
at `hpc_work_planning/task.py:79` (import of the deleted `HPCLedger`), raised when `episode.py:4` is imported. The head
cannot be linked at all. Classification: EPISODE (carry-over not done; already recorded as AXIS_WAVE_BLOCKERS_a107
section 4). No journal, no model call.

Smallest fix (task.py in the head): import `HpcLedger` from `episode_support/jobs/hpc_ledger`; `HPCLedger(ledger_directory(ctx),
commission_of(arguments, ctx))` (`:576`) -> `HpcLedger.open(ctx.store, commission)`; `HPCLedger.open_existing(...)`
(`:563`) -> `HpcLedger.existing(ctx.store, ledger_id)`; remove `ledger_directory` and the `directory` setting; replace
`ledger.path` uses at `:444` (`launch_input_path`), `:693` (`closed_measurement(..., ledger_path=ledger.path)`) and
`:977` (provenance, `ledger.ledger`); the head's `msg_to_child` for both sisters must pass `ledger` (= `ledger.ledger`) and
`ledger_row_refs` (= `ledger.refs()`), the execution sister's form already requires them. After that, branch 3 can be rerun
and also gives branch 2 a ledger. The prediction sister must be on `HpcLedger` first (branch 1), since the head commissions it.

## Summary of what runs today

Nothing in the HPC subtree runs: planning cannot be imported, prediction cannot be linked with the real services or opened,
and the execution sister cannot be given a ledger. Planning, ledger rows, predictions and refusals could not be exercised.
