# A102 branch runs: resource work (19 November 2026)

Runner report. Real model (`ModelProvider`), real Store, real `RunJournal`, the real job services
(`episode_support/jobs/job_services.py`, local route = detached systemd service). Nothing was fixed in
`episode_runtime/`, the library or the episodes; only three new test files were written (WORLD).

Note: `docs/axis_restructure_20261117/AXIS_WAVE_BLOCKERS_a102.md` does not exist (only `PILOT102_BLOCKERS.md`,
`LOST_CONTENT_a102.md`, `FINAL_TO_PARENT_NEEDS_a102.md`, `INVESTIGATION_FINDING_FEATURES_a102.md`). The state
described by `LAUNCH_MONITOR_EXTRACT_MECHANICS.md` ("Provided now") was used: `job_access` has `launch`, `check`,
`fetch`, `cancel`, `run` (and the `resource_adapter` / `resources` service is a `ResourceAdapters` over
`JobResourceAdapter`); it has no `begin_command`, `run_command`, `finish_command`, `check_handoff`.

Tests written (each `@pytest.mark.model_run`, public API only: `link(...).run()` then `resume(...).run()`):

- `root/a102/structural_homology_evidence/resource_work_submission/local_resource_work_execution/tests/test_branch_local_resource_work_execution_model_run.py`
- `root/a102/structural_homology_evidence/resource_work_submission/tests/test_branch_resource_work_submission_model_run.py` (written, NOT run: chain stopped at 1a)
- `root/a102/structural_homology_evidence/resource_result_acquisition/tests/test_branch_resource_result_acquisition_model_run.py`

World of the local job: a workspace under the job services' local route, a `practical_assignment_v1` whose
requested job is `python -c "open('result.txt','w').write(str(sum(i*i for i in range(1,101))))"` (answer 338350),
requirements `cwd` 1.0, `result_file` 2.0, `handoff` 4.0 (completion target 7.0), frozen launch and knowledge
libraries, a `local` resource configured both in the job services and in the episode's settings.

## 1a. `local_resource_work_execution` alone: FAIL (RUNNER/LIBRARY, job service not provided)

- Run directory `runs/brm_a102_10`, log `runs/brm_a102_10.log` (journal under `runs/brm_a102_10/tmp/test_the_model_runs_the_job_on0/journal.sqlite3`).
- Journal facts: run `branch102_local` linked and entered; 1 model call (`model_calls/call-00001`); 0 units
  journaled; run not closed (`active`), failure recorded; no `ended_by`. Resume not reached.
- Model decisions in order: (1) `exec_command` with `cmd` = the venv python running exactly the sum-of-squares
  program, `workdir` = the workspace, `env` = {}, `target` = resource. This is a sensible first tool for the
  assignment (no wrong tool, no repeated call, valid arguments: it passed `action`).
- Error: `NotImplementedError: BLOCKED-ON-JOB-SERVICE: job_access.begin_command; wanted call: await ctx.services["job_access"].begin_command(assignment, "exec_command", arguments, key=ctx.operation_key, run_id=ctx.run_id, episode_id=ctx.episode_id)`
  raised at `root/a102/structural_homology_evidence/resource_work_submission/local_resource_work_execution/task.py:177` (`_job_access`), called from `task.py:223` (`exec_command`).
- Classification: EPISODE (task.py still calls the old operations interface) over a missing system piece:
  the provided `JobAccess` has no `begin_command` / `run_command` / `finish_command` / `check_handoff`.
- Diagnosis and smallest suspected fix: `exec_command` (task.py:215-249) must be rewritten on the provided
  `job_access.run(ctx, resource_id, job, inputs=None, name=...)` (launch, wait, fetch in one unit; the mechanics
  table maps `run_command` / `begin_command` + `finish_command` to it): build `job = {'command': [...], 'env': ...}`
  from the model's `cmd` / `env`, call `await ctx.services['job_access'].run(ctx, assignment['resource_id'], job)`,
  keep the receipt/validation assessment (`finalize_scientific_command`, `assess_validations`) over the fetched
  files, publish the receipt through `ctx.store`. `resource_check_handoff` (task.py:~252-270) must use
  `job_access.check(ctx, handoff_ref)` (there is no `check_handoff`). Note the `job_access` `run` job has no
  per-call `workdir`/`cwd` member: whether the job route honours the model's `workdir` (the requirement `cwd` and
  `result_file` predicates read the workspace) needs a decision in the route or in the episode. A second
  consequence to expect after the fix: the model's `cmd` runs in the route's job directory, not in
  `assignment['workspace']`, so the `path_exists` requirement on `workspace/result.txt` cannot be met unless the
  job writes there by absolute path.
- Also seen by reading (not by running): the episode's own `capabilities()` (task.py:~167) requires every
  `tool_names` of the selected capability to be one of `exec_command, resource_capabilities, resource_inspect,
  resource_check_handoff`; the job services' capability declarations list `job.launch, job.check, job.fetch,
  job.cancel`. Both are accepted only because this world declares them separately (episode settings vs job
  services configuration); a caller that gives the same capability to both fails with
  `resource_capability_tool_not_bound`.

## 1b. `resource_work_submission` over the local child: NOT RUN

Chain stopped at the failing 1a (a commission of the local child cannot complete). Read only, known blockers in
`resource_work_submission/task.py`, none verified by a run:

- `task.py:176` `adapter.credit_view(assignment, list(ctx.store.refs()))`: `ResourceAdapters` has no `credit_view`
  (credit is not a member per `resource_adapters.py`); `ctx.store.refs()` is not a ScopedStore member. Every
  resource tool (`resource_capabilities`, `resource_inspect`, `resource_check_handoff`) calls it, so each fails.
  Credit belongs in `credit.py` over the summary and held records (the module docstring of `credit.py` says the
  summary's `adapter_credit` comes from the tool outcome).
- `task.py:218` `adapter.can_check_handoff(resource_id)` and `task.py:223` `adapter.check_handoff(handoff, held,
  key=...)`: the service member is `await check_handoff(ctx, handoff)` and there is no `can_check_handoff`.
- `messages/final_to_parent.py` `FINDING_FORM.qualification` is a free `text` field made of prose, which
  `AGENTS.md` (controlled messaging) does not admit between episodes.
- `messages/read_from_child.py`: `result['execution_handoffs']` / `result[REF_FIELD[slot]]` are read, so the
  commission selection must include them; `msg_to_child.BASE_SELECTION` does (fine).

## 2. `resource_result_acquisition` fetching the result: FAIL (EPISODE)

- Run directory `runs/brm_a102_12` (first attempt `runs/brm_a102_11` failed only on my fixture: the caller's launch
  run and the acquisition run both built a `ModelProvider` over the same `model_calls` directory; fixed in the test),
  log `runs/brm_a102_12.log`.
- World: the run's caller launched a real local job through the job services (the `job_probe` test episode as the
  launching run, no model; plan `launch`, `wait`), the job ended and its result was not fetched; the acquisition run
  is commissioned with `{'version': 'resource_results_assignment_v1', 'handoff': <execution_handoff_v1 with the
  job's handoff_ref>, 'requested_data_selector': {'names': ['answer.txt']}}` and the message `scope`, `initial_report`.
- Journal facts: the caller's launch run completed (handoff row exists); the acquisition run linked, entered, and
  failed in its first `decide`; 0 model calls, 0 units; run state `active` with a recorded failure. Resume not reached.
- Model decisions: none (the model was never asked).
- Error: `KeyError: 'resource_selection'` at `episode_runtime/resource_adapters.py:67` (`_selected`), reached from
  `root/a102/structural_homology_evidence/resource_result_acquisition/task.py:126` (`_tools`, `resources.read('catalog', assignment)`), called from `decide` at `task.py:159`.
- Classification: EPISODE (task.py passes the wrong record to the service).
- Diagnosis and smallest suspected fix: the results assignment holds its resource selection at
  `assignment['handoff']['resource_selection']`, while `ResourceAdapters.catalog/decision_context/facts/execute`
  select with `selecting['resource_selection']['resource_id']` on the record they are given. In `task.py` lines 126,
  166 (`decision_context`), 223 (`facts`) and 254 (`execute`) pass `assignment['handoff']` (it has
  `resource_selection`) instead of `assignment`. The handoff is also what `check_handoff` already receives (line 247).
- Further failures to expect after that fix (read from the code, not run): (a) `task.py:254`
  `resources.execute(assignment, name, args, ctx.operation_key)` and `task.py:247`
  `resources.check_handoff(handoff, ctx.operation_key)` lack the `ctx` first argument of the service signatures
  `execute(ctx, assignment, tool, arguments)` and `check_handoff(ctx, handoff)`; (b) `task.py:223`
  `resources.credit_view(assignment)` does not exist, so every unit raises (the credit would have to be computed in
  `credit.py` from the held `job.fetch` results; the summary now expects `credit_view['credit']`); (c) `task.py:284`
  `report` always raises `NotImplementedError('validate_form_not_built:A102')` before its checks (dead code follows
  the raise); (d) `read_from_parent.ASSIGNMENT_FORM` has no `record_refs` field, so the handoff row of the job
  (`handoff_ref`) is not passed in custody to this Episode and `job_access.check/fetch` on it will be refused as a
  record the Episode does not hold: a `record_refs` field (for the handoff row and its check rows) is needed in the
  results assignment, as in `job_probe`'s form; (e) the adapter's catalog names `job.launch/check/fetch/cancel`
  while the model-facing wording of the episode (`resource.capabilities`) and `RESOURCE_ROLES` use `resource.*`
  names; the model will see both.
- Resume, RETURN_FORM admission, controlled fields: not reached.

## Summary

| Branch | Result | Classification | Cause |
|---|---|---|---|
| 1a local_resource_work_execution | FAIL | EPISODE (job service not provided) | `exec_command` calls `job_access.begin_command/run_command/finish_command`, which `JobAccess` lacks (task.py:177, 223); model's first choice was sensible |
| 1b resource_work_submission over local | NOT RUN | (stopped at 1a) | read: `adapter.credit_view`, `can_check_handoff`, old `check_handoff` signature are not in `ResourceAdapters` (task.py:176, 218, 223) |
| 2 resource_result_acquisition | FAIL | EPISODE | `decide` passes the results assignment to the adapter service, which wants a record with `resource_selection`; use `assignment['handoff']` (task.py:126, 159) |
