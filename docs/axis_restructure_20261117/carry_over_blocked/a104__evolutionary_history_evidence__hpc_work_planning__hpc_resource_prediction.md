# Blocked, unplaced and misfit items: a104 / evolutionary_history_evidence / hpc_work_planning / hpc_resource_prediction

Old code was read with `git -C /home/chia/repos/gene_annotation_episode_disk show 97308b94c:<path>` (the working repository
`/home/chia/repos/gene_annotation_episode` has no `.git`; the commit is in the sibling repository
`gene_annotation_episode_disk`). Only the episode tree of this episode was read.

## BLOCKED-ON-STORE-ACCESS

None. No library function called from this episode touches the Store (the HPC library modules are pure, the ledger is
not a Store table).

## BLOCKED-ON-JOB-SERVICE (each raises where it is reached, in `task.py`)

* BLOCKED-ON-JOB-SERVICE: HPC ledger evidence record (job record kind; the parent-owned `hpc.sqlite` `evidence` table, no work table declared); wanted call: `reader.table(HPC_LEDGER).select({'owner': owner, 'id': identity})` (`ledger_find`), `reader.table(HPC_LEDGER).select({'owner': owner, 'kind': kind})` (`ledger_select`), `store.table(HPC_LEDGER).put({'owner': owner, 'id': identity, 'kind': kind, 'body': body})` (`ledger_write`). Every tool, `credit` (after `hpc_initialize`) and `internal_summary` (after `hpc_initialize`) reach these. The very first unit, `hpc_initialize`, raises.
* BLOCKED-ON-JOB-SERVICE: HPC ledger credit record (the `credits` table); wanted call: `reader.table(HPC_CREDITS).select({'owner': owner})` (`ledger_credits`), `store.table(HPC_CREDITS).put({'owner': owner, 'slot': slot, 'kind': kind, 'credit': credit, 'evidence_id': evidence_id})` (`ledger_write_credit`).
* BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: `ctx.services['estimate_table'].read('as_record')`, `.history(profile, now=now, queue_only=queue_only)`, `.latest(resource, kind)`, `.observe(resource, kind, data, observed_at=observed_at, provenance=provenance, key=ctx.operation_key)`, `.read('resource_tool_estimates', expectations)`.
* BLOCKED-ON-JOB-SERVICE: job_access; wanted call: `await ctx.services['job_access'].observe_queue(configuration, key=ctx.operation_key, resumed=ctx.resumed)`, `await ctx.services['job_access'].run_discovery(configuration['ssh_argv'], command, key=ctx.operation_key, resumed=ctx.resumed)`, `ctx.services['job_access'].read('execution_expectations', 'hpc_prediction', job_assignment)`, `ctx.services['job_access'].read('native_event_targets')`.

## Unplaced old functions

* `presentation.py::present_task_context`, `presentation_selection.py::task_presentation_selection`: the renderer state machine and the selection of `render_hpc_prompt`, `render_monitor_prompt`, `render_receiver_prompt`, `render_evolutionary_history_evidence_prompt`, `render_api_launch_prompt`, `render_selected_execution_prompt` and the `is_*_context` tests. Those renderers lived in the old shared root (`library/hpc_prompt`, `library/monitor_prompt`, `receiver_prompt`, `native_profile_presentation`, `evolutionary_history_evidence_prompt`) and are in no library module (README section 5 item 16); the old shared root is not read. The context goes to the model as the mapping `ModelRequest.context` (the old renderer's own fall-through was the JSON dump of the context). The prompt text of the HPC renderer is therefore not carried; it must be written for this episode.
* `decision_inputs.py::resource_context` (`workflow.resource_context(self)`, key `resource_context`): an old-runner callback whose content is not in the episode files; the resource configuration is shown as `hpc_resource` (from `ctx.settings['resources']`).
* `completed_action_reports` of `episode_work_report`: a module of the old shared root; replaced by `completed_action_reports` built in `messages/internal_summary.py` from the unit outcomes (tool, status, record refs, feedback). The old content of each report is not known.
* The 90 second timeout of the old discovery `subprocess.run` is not carried (`hpc_discovery_run` hands the command to `job_access`; the 64 KiB and 8 KiB output bounds are kept).
* The old `initial_decision_context(binding_context)` (`supplied_initial`) of `episode_bindings` is replaced by `settings['initial_information']`.

## Contract misfits

* new field: hpc_resource_prediction ledger_refs (record_refs; the parent-owned ledger records this episode reads; the old ledger was a file opened by path from the run directory and the owner id).
* new field: hpc_resource_prediction yield_binding (record; the old commission's `yield_bindings['hpc_prediction']` `{cutoff, parameters}`; `yield_controller` is handed no ledger to read, so the parent (`hpc_work_planning`) must copy it into the assignment).
* `commission_source_ref` is now a `record_refs` field with exactly one reference (a form has no single-reference type); `commission_id` stays text.
* hpc_result_refs is a `record_refs` field: a parent that reads the result bytes also needs each source's artifact, which the old fact did not name (the child holds only the sources, so only sources are returned; a parent that needs the artifact needs a further field).
* The old return fact `hpc_accepted_obligations` is a `list` field of obligation ids; its `validate_form` schema uses a new reference namespace `hpc_obligation` (resolved against the recorded obligations) because the library validator resolves every `identifier` string as a reference. `hpc_credit` is returned as `completion['credit']` (the old fact was the ledger credit view's `credit`; the two are the same formula, credit.py).
* The old report form was written by the parent (JSON Schema with `x-source`); `validate_report` now builds the schema from the selected fields of RETURN_FORM (`REPORT_SCHEMAS`), because the parent no longer writes one.
* The intent record says "new estimator: bounded quality", but the credit (`model_scale` x a mean log-score difference, signed) has no declared maximum and the old commission check (`validate_commission`) already opened an accumulating controller from each `yield_bindings` entry; the controller is `AccumulationYieldController` with the binding's cutoff as its cost (cutoff must be above zero for the controller to stop the Episode).
* `credit` is unbounded and the ledger credit is read after `hpc_initialize`; before it `credit` is zero (the old `credit_view` could not be read before the entry row exists).
* Execution of this episode cannot reach a model call: the first unit raises BLOCKED-ON-JOB-SERVICE (HPC ledger).
* `task.py` holds the ledger primitives and ledger-derived helpers that `credit.py` and `messages/internal_summary.py` import (`from .task import ...`), as in the A102 carry-over; they are library candidates.
