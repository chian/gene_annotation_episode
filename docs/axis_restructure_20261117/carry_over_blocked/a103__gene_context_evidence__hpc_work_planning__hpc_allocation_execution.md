# Blocked, unplaced and misfit items: A103 hpc_allocation_execution (19 November 2026)

Episode: `gene_context_evidence/hpc_work_planning/hpc_allocation_execution` (a job episode; children `launch`,
`monitor`, `results` = the three child folders carried before it). Carried without git in the repository directory:
the old files were read with `git -C <disk copy of the repository> show 97308b94c:<path>` (the repository directory
has no `.git`). The episode imports and passes its class-definition checks; its real-runner test reaches its first
decision (the initial ledger lookup) and fails where the `estimate_table` service is missing. No test contacts a
remote service.

## blocked_on_store_access

- function = `episode_support/jobs/hpc/gene_context_evidence/hpc_ledger.py::HPCLedger`; pattern = "library not
  carried": the ledger opens its own SQLite file (`sqlite3.connect(directory/'hpc.sqlite')`: tables `evidence`,
  `actions`, `credits`, `forecast_slots`) beside the Store, and writes this Episode's records of work (plans,
  forecasts, measurements, results, credit slots) outside custody. Old call (kept as written in `task.py`
  `open_ledger`, `hpc_state`, `freeze`, `measure`, `collect_original_results`, ...):
  `HPCLedger.open_existing(directory)`, `ledger.put/read/records/once/freeze/score/accept/credit_view`. Intended:
  a declared work table, `TableDeclaration(...)`, written with `ctx.store.table(T).put(values)` and read with
  `records.table(T).select(...)`, so that `credit` could read the credit slots through `records` instead of the
  `credit_view` the tools return in their outcomes. The ledger is shared with the planner and its prediction
  sister, which the new form cannot do without a record kind passed in custody.
- No other library function the episode calls touches the Store. Its own writes are `ctx.store.artifact` and
  `ctx.store.put('source', ..., origin='tool')` (`publish_result`) and `ctx.store.get/get_artifact/holds/validate_scope`
  (`resolve_received_reference`, `read_evidence`), all custody operations.

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: `job_access` (declared in `SERVICES`; no factory or class exists, so a link raises
  `LinkError('service_required:...')`). Wanted calls, idempotent on the key where they act (all from `task.py`):
  `ctx.services['job_access'].observe_queue(resource_id, key=ctx.operation_key)` (old `hpc_queue.observe(configuration)`,
  returning `{'snapshot', 'acquisition'}`); `.discover(resource_id, command, key=)` (old `subprocess.run([*ssh_argv,
  command], timeout=90)`: returns `{'returncode', 'stdout' (bytes), 'stderr' (bytes)}`; the time limit is not carried);
  `.stage_input(plan_id, plan, key=)` (old `LaunchPreparation` writing the immutable `launch-inputs/<plan>.json`;
  returns `{'supplied_input_file', 'coordinator_workspace'}`); `.observe_target(target, key=)` (old
  `ExecutionTargetReader.observe_target`); `.read_file(target, path=, offset=, limit=, key=)` (old
  `ExecutionTargetReader.read_file`; the window with `bytes_base64`, `size_bytes`); `.write_allocation_control(target,
  unit_ids=, key=)` (old `targets.operations[resource].write_allocation_control`).
- BLOCKED-ON-JOB-SERVICE: `estimate_table` (declared in `SERVICES`; the old shared `ExecutionMemory`). Wanted calls,
  from the tools: `.history(query, now=, queue_only=)`, `.latest(resource, kind)`, `.observe(resource, kind, value,
  observed_at=, provenance=)`, `.record(**closed_measurement)`, `.as_record()`; from `decide` the read
  `ctx.services['estimate_table'].read('resource_tool_estimates', 'hpc_execution')` (old `resource_estimator`
  context). The tools use the memory only when the settings key `shared_execution_memory` is true; `decide` always
  reads the estimates (the real-runner test shows the run failing there).
- BLOCKED-ON-JOB-SERVICE: the job record kind handoff and its work table (`JOB_LEDGER` of the mechanics doc). Wanted
  call in `task.py read_target` (raises `NotImplementedError`): `row = ctx.store.table(JOB_LEDGER).get(handoff_ref);
  target = ctx.services['job_access'].read_target(row)`, returning `{'assignment', 'execution_id', 'resource_id', ...}`.
  `hpc_handoff`, `hpc_monitor`, `hpc_monitor_wait`, `hpc_results` and `hpc_allocation_order` reach it, so none can
  complete until the record kind exists.
- BLOCKED-ON-JOB-SERVICE: the scheduled-monitor controller of `hpc_monitoring` (`MonitorCronController.attach`,
  `.reserve`, `.wait`, `choose_schedule`): not in the library of gene_context_evidence (its `hpc_monitoring.py` holds
  `DEFAULT_POLICY` and `validate_policy` only; the structural and partner copies are other axes'). `task.py
  monitor_controller` raises `NotImplementedError`. `hpc_handoff` (when the commission has `monitoring`) and
  `hpc_monitor_wait` reach it.

## unplaced_old_functions

- `hpc_commission_sources.read` (called by `from_parent.HPCAssignment._commission` for a `commission_source_ref`):
  no gene_context copy in `episode_support/jobs/hpc/` (only the structural and partner copies). The commission is
  the assignment field `commission`; `commission_source_ref` stays a (record_refs) field.
- `MonitorCronController`, `choose_schedule`: see BLOCKED-ON-JOB-SERVICE above.
- `library.hpc_prompt.render_hpc_prompt` / `is_hpc_context` (old `decision_prompt_renderer`): in no library module;
  the context travels as one mapping of named sections (`task.py decision_context`).
- `library.hpc_continuation.HPCContinuationEstimator` and `HPCEpisodeYield.continuation_for_action`: deleted (an
  episode cannot supply a forecast, README 7b); the completion controller replaces them.
- `library.hpc_handoff_report_contract.validate_hpc_launch_report_contract` (`HPCWorkTask`): not in the library; the
  launch return form is the Launch child's own and the system admits it.
- `library.action_contracts.action_schema`, `library.private_policy_call`, `library.report_fact_assembly`: not in the
  library; the action schema is `task.py action_schema`, the facts are `final_to_parent.facts`.
- `decision_inputs.py`: not carried because nothing supplies them: `completed_action_reports`,
  `requested_action_history`, `execution_expectations` / `native_execution_expectations` /
  `native_event_targets` / `waiting_support`, `child_option_information`, `pending_work`,
  `contract_information_profile`. `task_instructions.py`: the pending-child delivery, wait and native-event texts
  describe actions that no longer exist.
- `ExecutionTargetReader` (`execution_progress`, old shared root): its operations are the wanted `job_access` calls
  above.
- `HPCActivityAdvice.activity_advice`: `active_next_gain`, `pending_expected_credit` and
  `pending_credit_upper_bound` came from the old estimator diagnostics in `runtime_observations`; only `mode` and
  `suggested_tool` are carried (derived from the ledger state).

## contract_misfits

- completion credit may pass its target: the credit is the signed measured credit of the ledger (accepted obligations,
  plus model improvement and fixed prospective forecast validation, which are unbounded and may be negative or
  positive), while the controller's target is the sum of the obligations' credit; the old estimator took
  `max(0, remaining)`. A validation or model credit that carries the credit past the obligations' sum raises
  `ValueError('completion_credit_exceeds_target')` from the controller, and `ledger_credit` above the target raises when
  the controller is built. The credit formula is unchanged and not clamped.
- BLOCKED-ON-JOB-SERVICE: job_access (`observe_queue`, `discover`, `stage_input`, `observe_target`, `read_file`,
  `write_allocation_control`), estimate_table (`history`, `latest`, `observe`, `record`, `as_record` and the read
  `resource_tool_estimates`), the handoff record kind / `JOB_LEDGER` and the monitor controller; wanted calls: see
  the items above.
- new field: hpc_allocation_execution commission (record): the commission the owner holds; the old code read it from
  its configuration or from the Store source, and neither `read_from_parent` nor the yield estimator can.
- new field: hpc_allocation_execution scope (record): the old `context.scope` (the sister inherits it exactly from its
  owner); the result receipts and `hpc_read` use it.
- new field: hpc_allocation_execution ledger_credit (number): the credit of the owner's (shared) ledger when the
  commission begins; the old `initial_credit` was the ledger credit view.
- `commission_source_ref` is a `record_refs` field (a list of exactly one reference), not text: custody requires it.
- new field (return): hpc_allocation_execution hpc_result_artifact_refs (record_refs, selectable): the artifact of
  each result source (a returned record does not bring the records it names); and hpc_handoff_refs (record_refs,
  selectable): the handoff records of the Launch children, for the planner to pass on.
- new fields set by this episode in its commissions (the children's forms need them; the old code read them from
  its configuration or the target): execution_job_submission `handoff_unit` (the plan's `handoff` requirement credit),
  `already_handed_off`, `input_refs` (the staged plan record) and `hpc_execution_job`; execution_progress_assessment
  `information_unit` (from the setting `monitor_information_unit`) and `known_progress_snapshots`;
  execution_result_acquisition `resource_kind` (`hpc`), `workspace` (the plan manifest's workspace) and
  `acquired_record_unit` (from the setting `acquired_record_unit`).
- Tool names with a dot become form names: `hpc.read` -> `hpc_read`, `hpc.compare` -> `hpc_compare`, `hpc.history.refresh`
  -> `hpc_history_refresh`, `hpc.discovery.run` -> `hpc_discovery_run`, `hpc.candidate.propose` ->
  `hpc_candidate_propose`, `hpc.queue.observe` -> `hpc_queue_observe`, `hpc.plan` -> `hpc_plan`, `hpc.handoff` ->
  `hpc_handoff`, `hpc.monitor` -> `hpc_monitor`, `hpc.monitor.wait` -> `hpc_monitor_wait`, `hpc.results` ->
  `hpc_results`, `hpc.allocation.order` -> `hpc_allocation_order`. This renames them against "names both sides use are
  the old names". The old child roles `launch`, `monitor`, `results` are the slot names, unchanged.
- The Launch child's supplied input file (old `LaunchPreparation.initial_decision_context`, run when the Launch child
  first decided) is staged by `hpc_plan` (job_access `stage_input`, plus the plan as an artifact named in `input_refs`),
  because `msg_to_child` only builds. A plan frozen by the owner, not by this Episode's `hpc_plan`, has no staged
  input: `action` rejects launching it (`hpc_launch_input_not_staged_for_plan`).
- The first unit is an initial lookup the task offers through its own tool: `hpc_read` of the ledger's `owner` record,
  so that the ledger state (plans, candidates, models, queue observations) reaches the summary; before it the summary
  holds only the commission's candidates and the ledger credit the commission began with.
- Credit is read from the ledger credit view each tool returns in its outcome (`credit` has no services and no ledger
  file). Credit a sister writes to the shared ledger (the model improvement of the prediction sister) shows in this
  Episode's credit only after its next tool unit.
- A tool that refuses a value it was handed (an unknown reference, a candidate that violates the queue limits, an
  unattached handoff) returns an `invalid` outcome, which is a unit that enters the controller with its credit
  unchanged, as the old `save_action` results did; the old `ValueError` rejections of the decision (no unit) are now
  `Rejected` only for the model answers `action` can see (an unknown plan, an unheld handoff, a second launch of a
  plan, a closed allocation).
- The old wait action and `redeliver_report` are not carried; `hpc_monitor_wait` (a tool) remains and is blocked on
  the monitor controller. The old `permitted_common_actions` rule (wait unless the commission has `monitoring`)
  has no object: no generic wait exists.
- Settings of this binding path: `directory`, `resources`, `monitor_information_unit`, `acquired_record_unit` and
  optionally `shared_execution_memory`, `tool_knowledge_directory`, `launch_instructions_directory`. The yield
  cost and parameters are not settings: they are the commission's `yield_bindings['hpc_execution']`, read from the
  parent input as the old code read them from the commission.
- The old checks of the child against its commission (the owner is the commissioning parent, the commission identity
  equals the parent's, the sister scope equals the owner's recorded scope) are not carried (rule 1).
- A103 is not an A105/A108 literature episode: the typed `investigation_finding` of "Required literature evidence
  processing" does not apply; `finding` is this episode's own HPC finding.
- The real-runner test registers the episode's own descendants (the three children and their three route children)
  because a link builds the whole subtree; it imports no episode outside this folder.
- Old tests: the four files at `97308b94c` inherit from the old shared root and the three hook-era tests in the
  working tree used the deleted `allocation_runtime.py`; all are recorded in `retired_tests/a103__gene_context_evidence__hpc_work_planning__hpc_allocation_execution.tsv`.
