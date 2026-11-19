# Blocked and unplaced: A102 hpc_work_planning/hpc_allocation_execution

Old source was read with `git show 97308b94c:<path>` (git dir `/home/chia/repos/gene_annotation_episode_disk/.git`),
the episode's own files only. The hook-era files of the working tree (`allocation_runtime.py`, `episode.py`,
`tests/test_allocation_runtime.py`) were deleted first. The three child folders were read as data and not imported.
The tests in `tests/test_binding.py` pass (12 tests, slot `cov13`, `runs/cov_a102_04_u033_4`).

## BLOCKED-ON-JOB-SERVICE
Each is a function of `task.py` that names the call it wants, raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: ...')`
where it is reached and keeps the intended call after the raise.
- BLOCKED-ON-JOB-SERVICE: job ledger handoff record (the handoff row the launching child writes and returns; no job record kind is declared); wanted call: `ctx.store.table(JOB_LEDGER).get(handoff_ref)` read as the execution target (`handoff_target`; old `ExecutionTargetReader.read_target(handoff_ref, scope)`). Reached by `hpc_handoff`, `hpc_monitor`, `hpc_monitor_wait`, `hpc_results`, `hpc_allocation_order`.
- BLOCKED-ON-JOB-SERVICE: job_access.observe_target; wanted call: `await ctx.services['job_access'].observe_target(target, key=key, resumed=ctx.resumed)` (`observe_target`; old `targets.observe_target(target, operation_key=...)`).
- BLOCKED-ON-JOB-SERVICE: job_access.read_file; wanted call: `await ctx.services['job_access'].read_file(target, path=path, offset=0, limit=limit + 1, key=key, resumed=ctx.resumed)` (`read_window`; old `targets.read_file`).
- BLOCKED-ON-JOB-SERVICE: job_access.write_allocation_control; wanted call: `await ctx.services['job_access'].write_allocation_control(target, unit_ids=unit_ids, key=key, resumed=ctx.resumed)` (old `targets.operations[resource_id].write_allocation_control(...)`).
- BLOCKED-ON-JOB-SERVICE: job_access.observe_queue; wanted call: `await ctx.services['job_access'].observe_queue(configuration, key=key)` (old library function `hpc_queue.observe(configuration)`, which runs the SSH transport itself).
- BLOCKED-ON-JOB-SERVICE: job_access.run_command; wanted call: `await ctx.services['job_access'].run_command(configuration, command, key=key)` returning `{'command', 'returncode', 'stdout', 'stderr', 'observed_at', 'truncated'}` (old `subprocess.run([*configuration['ssh_argv'], command], timeout=90)`; the timeout and the 65536/8192-byte truncation are not carried).
- BLOCKED-ON-JOB-SERVICE: estimate_table.latest; wanted call: `ctx.services['estimate_table'].latest(resource, kind)` (old `ExecutionMemory.latest`).
- BLOCKED-ON-JOB-SERVICE: estimate_table.observe; wanted call: `ctx.services['estimate_table'].observe(resource, kind, data, observed_at=..., provenance=..., key=ctx.operation_key)` (old `ExecutionMemory.observe`).
- BLOCKED-ON-JOB-SERVICE: estimate_table.history; wanted call: `ctx.services['estimate_table'].history(query, now=now, queue_only=queue_only)` (old `ExecutionMemory.history`; the old `[:2000]` cut of the shared history is a count limit and is not carried).
- BLOCKED-ON-JOB-SERVICE: estimate_table.policy; wanted call: `ctx.services['estimate_table'].policy()` (old `ExecutionMemory.as_record()['policy']`).
- BLOCKED-ON-JOB-SERVICE: estimate_table.record; wanted call: `ctx.services['estimate_table'].record(**closed_measurement(...), key=ctx.operation_key)` (old `ExecutionMemory.record`).
- BLOCKED-ON-JOB-SERVICE: estimate_table.read; wanted call, in `decide`: `ctx.services['estimate_table'].read('resource_tool_estimates', 'hpc_execution')` (old `execution_expectations.capture('hpc_execution')` and `resource_estimator.estimate_context`). No such service exists, so a run cannot be linked until the caller supplies one; the shared memory calls above are reached only when the setting `shared_execution_memory` is true.
- The services `job_access` and `estimate_table` are declared in `SERVICES` and every run needs a factory for each.

## BLOCKED-ON-STORE-ACCESS
- function = `episode_support/jobs/hpc/structural_homology_evidence/hpc_ledger.py::HPCLedger` (`open_existing`, `put`, `read`, `records`, `once`, `freeze`, `score`, `accept`, `credit_view`), pattern = "library not carried": the class opens its own SQLite file by path (`sqlite3.connect`, `hpc.sqlite`), outside the Store. Called as written in `task.py` `open_ledger` (directory `settings['directory']/hpc/<digest of run id and owner>`). Intended: a declared work table of the job library (`ctx.store.table(HPC_LEDGER).put(...)`, `records.table(...).select(...)`), passed in custody between the HPC parent, its prediction sibling and this episode (its rows named in `record_refs` fields). `ledger.cached` / `save_action` / `put('action_intent')` (the old operation ledger) are not called: the system's attempts journal replaces them.
- function = `episode_support/jobs/hpc/structural_homology_evidence/hpc_monitoring.py::MonitorCronController` (`attach`, `reserve`, `wait`): library not carried (it writes the HPCLedger above); called as written by `hpc_handoff` and `hpc_monitor_wait`.
- function = `episode_support/jobs/hpc/structural_homology_evidence/hpc_history.py::closed_measurement`: pure, but takes `ledger_path` (a path of the ledger file); called as written.
- function = `episode_support/jobs/structural_homology_evidence/practical_execution_state.py::_immutable`: a private function that writes the launch input file by path (not the Store); called by `hpc_plan`.

## Unplaced old functions
- `decision_inputs.py::HPCWorkDecisionInputs.decision_inputs` parts `resource_context`, `child_option_information`, `completed_action_reports`, `pending_work`, `waiting_support`, `native_estimation_context`, and the `hpc_prompt.render_hpc_prompt` renderer (`library.hpc_prompt`, `episode_work_report`, `runtime`): no placed home found; the context is sent as JSON in `ModelRequest.context`, the action history is `requested_action_history` from the summary.
- `library.hpc_continuation.HPCContinuationEstimator`, `library.action_contracts`, `library.hpc_handoff_report_contract`, `library.private_policy_call`, `library.report_fact_assembly`, `episode_source_failure`, `episode_return_records`, `execution_progress`, `execution_contracts` of the old shared root: not read; no placed home found for the first six (the estimator and the report machinery are deleted; the action schema and validation are written in `task.py`).
- `configuration.py` checks (a configured `pbs_ssh` resource; static commissions validated against resources): not carried (the commission is read from the owner ledger, which validated it).
- `from_parent.py` `prepare_assignment` check that the commissioning parent is the `hpc` episode that named `owner_episode_id` with the same commission identity: not carried (no parent assignment or role reaches the episode); the owner ledger must carry this scope and commission identity (`open_ledger`).
- `to_child_execution_job_submission.py` `authenticate_launch` reservation row (`launch_commission` in the ledger): not written; a second launch of a plan, and a launch of a closed plan, are rejected in `action`.
- `waiting.py` `activity_advice`: not carried (it read the deleted estimator's journaled diagnostics); the yield table (`action_yields`) is shown instead.
- Old validate_form call (`to_parent.py` `validate_report`): A102 has none; `final_to_parent` raises `NotImplementedError('validate_form_not_built:A102')` after the agreement check, so the Episode cannot return a result until the A102 validator exists.

## Contract misfits
- new field: hpc_allocation_execution scope; new field: hpc_allocation_execution input_refs (the launch child's form needs both; the old code took them from its request and the parent's assignment). The commissioning parent's `msg_to_child` must supply them with `owner_episode_id` and one of `commission_id` / `commission_source_ref`.
- `commission_source_ref` is declared as text, not `record_refs`: only its identity is used (the commission is read from the owner ledger).
- Tool names carry underscores (`hpc_read`, ..., `hpc_monitor_wait`): `[a-z][a-z0-9_]*` does not admit the old dotted names `hpc.read`, `hpc.monitor.wait`, ...
- The old model composed child assignments from the child's schema; the parent now sends them from `CHILD_CATALOG` arguments and the summary. For the monitor and results children the model names the fields of the child's form (the monitor's `requested_fields` options are copied into `task.py`).
- The launch child declares `requests` as a list and `immutable_input_versions` as a record; the old plan carries `requests` as a mapping by resource id and `immutable_input_versions` as a list. The mapping's values are sent; a non-empty versions list fails the commission (`immutable_input_versions_list_is_not_a_record_of_the_launch_child`).
- The results child's form names the handoff record only (`handoff_ref`); it names no field for the artifacts the handoff record names, which it may need under decision T5 (a read that follows a name to an unheld record raises `CustodyError`). Not worked around.
- Credit before the first unit is 0.0 although the owner ledger may already hold credit from the prediction sibling; the first tool's outcome (the commission read) then reprices the whole ledger credit as one marginal credit. Each unit's credit is the ledger credit the last tool showed: a child unit does not change it.
- The ledger view is taken from the latest tool outcome, so work the prediction sibling did in between shows at the next tool, not at the next decision (the old `decision_context` read the ledger live).
- The yield controller is `AccumulationYieldController`: README 7b has no mapping for `HPCContinuationEstimator`, and the owner ledger credit has neither a declared maximum nor a finite target (completion would raise `completion_credit_exceeds_target` as soon as model or validation credit passed the obligations'). Settings `cutoff` (the old commission `yield_bindings['hpc_execution']` cost, above zero) and `parameters`. The old continuation packet (pending value of an open allocation, collect advice, active ceiling) is deleted.
- `ctx.settings` must hold `directory`, `resources`, `shared_execution_memory` (boolean), `handoff_unit`, `information_unit`, `acquired_record_unit`, `cutoff`, `parameters`; optional `launch_instruction_directory`, `tool_knowledge_directory`.
- `final_to_parent` always raises `NotImplementedError('validate_form_not_built:A102')` (see above), and `hpc_monitor_wait` is a wait tool: its sleeping unit earns nothing unless the ledger credit changes, as the old rule said.
- The remote project directory `/lus/flare/projects/BioReason-Aurora-Test` stays a constant of `hpc_discovery_run` (as in the old code and AGENTS.md).

## Repaired (19 November 2026)
task.py action no longer checks the commission (unknown_plan_ref, closed plan, launch-once, record_not_held removed); only the schema validation of the model answer remains.
