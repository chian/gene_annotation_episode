# a101 / sequence_homology_evidence / execution_job_submission / local_job_execution

Source: the episode's own files at commit `97308b94c`
(`git show HEAD:gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/execution_job_submission/local_job_execution/<file>`).
The child-episode folders and `tests/` are not covered here. Old binding class `ExecutionEpisode`; decision source `OperationalTask`.

## Purpose (goal, in its own words)

Role `launch_local`. `goal.py` hands the goal to the resource's `TerminalExecutionBehavior.instructions`
(`terminal_execution.py`), and `replaces_default_instructions = True`, so this text replaces the general investigator prompt:

> You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the
> shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery from the
> actual resource instructions and observed results. No sequence of setup or job-stage operations is prescribed.
> Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical inventory is context,
> not proof of present usability. Each command is one ordinary episode action: its actual result and earned credit
> enter the iterator, including failure or zero progress. ... If a submission outcome is uncertain, investigate that
> original submission rather than create a duplicate. ... The episode iterator decides continuation from credit; add
> no stopping budget.

After it come the resource-specific sections from the frozen launch instruction library (`for_resource`).

## Task and instructions

- `task_instructions.instructions(source, context)`: because this binding replaces the default instructions, the
  composer starts from the terminal goal and then adds: the tool_knowledge text (if `tool_knowledge` is in context),
  the launch instruction library text (if `launch_instruction_library` is in context), the
  pending_child_delivery/redeliver_report repair paragraph, and the decision-exchange history replacement. The
  reasoning-commit and wait/native-event paragraphs are added only when `reason` / `wait` are permitted, and here
  they never are (`permitted_common_actions` = `('tool',)`).
- `task.py` is the decision loop: restore and replay, the model call (`task_decision.call`), admitting the response
  (repair feedback on invalid selections), `execute` (the selected tool runs through the host, the outcome is saved,
  automatic score updates and credit run, and the unit is staged). A failed or invalid outcome still enters the
  iterator as an observation. `task_state.record_execution_failure` turns a crash during the selected operation into
  a failed outcome with credit.

## What it reads from its parent's assignment

- The parent is `sequence_homology_evidence/execution_job_submission`, role `launch`. `prepare_assignment` refuses
  any other parent role (`resource_child_role_owned_by_launch`).
- The assignment is one concrete request for a bound **local** resource (`from_parent.assignment_schema`): `resource_id`
  (const), `resource_kind` (const `local`), `workspace` (must stay inside the resource workspace), `endpoint`
  (`usable_handoff` | `completed_job_outputs`) and `requested_job` (the generic job schema, or a native job schema:
  native_blast, native_blast_masking, native_blast_utility, native_blast_database,
  native_blast_standard_database, native_hmmer, native_hmmer_preparation, with preparation variants).
- It also re-reads the parent's whole Launch form (`from_parent_launch`, `execution_launch_assignment_v1`):
  requests per resource, immutable_input_versions, constraints, and launch_instructions. It then checks the masking
  and utility inputs, the immutable input versions and the native BLAST (standard) database job inputs against that
  form, both at commission time and again at `initialize` (`execution_state._check_parent_inputs`).
- The parent's `episode_assignment.launch_instructions` selection is materialized and shown as
  `selected_launch_instructions`.

## Children

None. `child_roles` and `allowed_children` return `()`.

## Decision state shown to the model

`decision_state.decision_state` shows: goal, scope, working_state, visible_record_refs, current_credit,
current_evidence_vector, investigation_progress (when receipts are projected), credit_binding, time_accounting,
pending_work, last_local_outcome, feedback, visual_evidence (from the last image.view), report_deliveries, controller,
controller_binding, tools, tool_knowledge, job_episode_options, available_report_facts, requested_report_purpose,
requested_form, current_report_update, current_report_basis_refs and report_lifecycle. It also includes the
specialist `decision_context`, which comes from `internal_summary` and the terminal behaviour: execution_assignment,
execution_resource (kind, workspace, policy, account, ssh_argv, python_executable, scheduler, inventory snapshot),
coordinator_workspace, execution_progress (PracticalState credit view), execution_completion (completion proof), and
selected_execution_task (the scientific question and selected tool info from the scientific parent task, plus the
single native job view; HMMER jobs are shown through native_profile_scientific_job_view).
`decision_inputs` adds: resource_context, shared_information_context, launch_instruction_library,
selected_launch_instructions, child_options, the initial binding context (execution_resource_capabilities,
execution_initial_information, received_bvbrc_values / received_minhash_values), completed_action_reports,
requested_action_history (HPC context), execution_expectations / job_execution_options, resource_tool_estimates,
native_execution_expectations, native_event_targets and contract_information_profile.

## Tools offered

One tool, `exec_command`, with `{cmd: string | [string], workdir, env, target: resource | coordinator}`. It runs on
the assigned resource, or with `target=coordinator` in the local run directory. Each call is checked by
`TerminalExecution.validate_action`, recorded as a PracticalState receipt, finalized with
`finalize_scientific_command` and published as a `practical_receipt` source. The native result family catalogs
(`execution_operations.catalog`) also apply when a native family matches the context.

## Credit

- `credit_kind` = `operational`.
- Live view: first the native result family that applies (BLAST masking, BLAST utility, standard BLAST database,
  BLAST database, HMMER preparation, BLAST, HMMER). Otherwise the resource's `PracticalState.credit_view()`, which is
  the operational credit of command receipts and endpoint validations. The units are `handoff_unit` and
  `acquired_record_unit` from configuration.
- Completion proof `practical_completion_v1` (`completion_for_action` / `_proof_for_action`): a completed action,
  plus native results that are complete for the assignment, plus validation keys.
- Closed credit: after closure the view captured in `runtime_forms.facts[execution_closed_operational_credit_v1]`
  is returned. It is re-authenticated against the episode completion, archive, observation history and receipt
  prefix, and never reprojected. Credit is not bounded or rescaled anywhere in these files.

## Continuation

`yield_estimator.yield_controller` requires `require_private_yield=True`. The profile is
`task_yield_profiles['launch_local:' + request_yield_class]`, where the class is
`practical_local_<sorted native_* job names>_<handoff|outputs>` (API and compact variants exist). A profile is
`{cutoff > 0, parameters}`. The old controller was `YieldController(epoch, initial_credit, cutoff,
YieldParameters(**parameters), estimate_with_context=PracticalYieldEstimator(verify_completion))`, so the forecast
drops to exact zero once a verified endpoint completion proof exists. In the new layout this corresponds to the
**completion-with-a-target** yield estimator (target = verified endpoint); the settings are the per-request-class cutoff
and parameters.

## Report to parent

- Report fact sources (`to_parent.fact_sources`): native HMMER, masking, BLAST utility, standard DB / DB, HMMER
  preparation, BLAST pairwise (+ `execution_blast_pairwise_result_refs`), appservice families, BV-BRC data, MinHash,
  the terminal practical facts (`practical_completed`, `practical_receipt_digests`, `practical_receipt_refs`),
  `execution_handoff_refs`, `execution_completed`, `execution_result_origin`, `execution_blast_hsps`.
- `facts` = the native family facts, or the practical facts plus the returnable handoff refs read from practical
  receipts, plus the closed credit snapshot.
- `validate_report`: the form must resolve and must equal the recorded facts for every `x-source` field
  (`execution_report_disagrees_with_recorded_facts`).
- `report_delivery.finish` saves the typed form once (`runtime_forms`). Without a report contract it returns credit
  and pending handles.
- `required_return_sources` returns `()`.

## Differences from similar episodes

- **execution_result_acquisition** (sibling under sequence_homology_evidence): it has the same composed class. Of this
  episode's 26 files, 4 are byte-identical to the sibling's (`__init__`, `from_parent_launch`, `task_instructions`,
  `terminal_execution`), 10 differ only in docstring, binding id or module path, and 12 differ in substance (`goal`,
  `episode`, `from_parent`, `credit`, `yield_estimator`, `execution_state`, `execution_operations`,
  `internal_summary`, `to_parent`, `task`, `waiting`, `decision_inputs`). The sibling also has `blast_result_grading.py`. This one differs in role (`launch_local`, child of
  execution_job_submission, not an entry role), in goal (terminal execution agent, not result acquisition), in
  assignment (a Launch request, not a handoff + selector), in credit (PracticalState receipts, not requested-byte
  coverage), in continuation (`launch_local:` profiles), and in having no wait and no BLAST grader.
- `terminal_execution.py` holds this episode's real goal and tool. The result acquisition episode carries an identical
  copy that it does not use as its goal.
- Several branches are dead for this role but kept as written: `if 'launch_local' in ROLE_KINDS` is always true;
  `parent.role in ('hpc','hpc_execution') and False`; `_practical_context` is the identity; API branches never apply
  to a local resource.

## Per-file table

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| __init__.py | 0 | Empty package marker. | none |
| binding_record.py | 8 | Binding record id `sequence_homology_evidence/execution_job_submission/local_job_execution`, VERSION `execution_episode_v1`, and the configuration it records: resources, initial_information, handoff_unit, acquired_record_unit, log_window_bytes, log_roles, optional require_private_yield / results_yield_profiles / task_yield_profiles. | none |
| configuration.py | 119 | Construction-time configuration: explicit resources (kind in local/pbs_ssh/hmmer_api/api), inventory bound to resources, positive finite handoff_unit and acquired_record_unit, log window selection, private-yield flag, results_yield_profiles (only native_unbounded_local/hpc) and task_yield_profiles (each {cutoff>0, parameters}); A101-only native job kinds allowed (native_blast*, native_hmmer*); one TerminalExecutionBehavior per non-API resource; API execution, progress provider, local file sources, native result readers (BLAST masking/utility/database/standard database, HMMER, preparation) and optional FBA/NMF/ATAC/chromatin/fluorescence/protein-structure result families. | `import:a101.api_service_execution` (1), `import:a101.execution_progress` (1), `import:a101.library.retained_input_authority.atac_differential_returns` (1), `import:a101.library.retained_input_authority.chromatin_interaction_returns` (1), `import:a101.library.retained_input_authority.expression_nmf_returns` (1), `import:a101.library.retained_input_authority.fluorescence_returns` (1), `import:a101.library.retained_input_authority.flux_balance_execution_inputs` (1), `import:a101.library.retained_input_authority.flux_balance_returns` (1), `import:a101.library.retained_input_authority.native_atac_differential_results` (1), `import:a101.library.retained_input_authority.native_chromatin_interaction_results` (1), `import:a101.library.retained_input_authority.native_expression_nmf_results` (1), `import:a101.library.retained_input_authority.native_fluorescence_results` (1), `import:a101.library.retained_input_authority.native_flux_balance_results` (1), `import:a101.library.retained_input_authority.native_protein_structure_results` (1), `import:a101.library.retained_input_authority.native_protein_structure_returns` (1), `import:a101.numerical` (1), `name:YieldController` (3), `name:YieldParameters` (3) |
| credit.py | 260 | Operational credit (credit_kind 'operational'). Credit view comes from the matching native result family (masking, utility, standard database, database, HMMER preparation, BLAST, HMMER) or else from the resource's PracticalState credit_view (terminal command receipts). Completion proof per action (`practical_completion_v1`) from completed actions plus native results completeness. Closed-credit snapshot: once the episode closed, the original view is returned and re-verified (never reprojected). | `import:a101.episode_receipts` (1), `import:a101.episode_return_records` (4), `import:a101.method_loop.identities` (1), `import:a101.numerical` (1), `import:a101.practical_yield` (1), `name:ESTIMATOR_VERSION` (2), `name:NumericBand` (2), `table:runtime_actions` (2), `table:runtime_episodes` (2), `table:runtime_forms` (3), `table:runtime_observations` (2), `table:runtime_receipt_inheritance` (2), `table:runtime_record_receipts` (2), `table:sqlite_master` (2) |
| decision_inputs.py | 76 | Decision inputs added before each model call: resource_context, shared_information_context, launch_instruction_library + selected_launch_instructions from the parent's episode_assignment, child_options, initial binding context, completed_action_reports, requested_action_history (HPC prompts), pending_work, execution_expectations / job_execution_options, resource_tool_estimates, native_execution_expectations, native_event_targets, contract_information_profile. | `import:a101.episode_work_report` (2), `import:a101.hpc_prompt` (1), `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.available_child_roles` (1), `self.workflow.binding_context` (2), `self.workflow.episode_bindings` (1), `self.workflow.execution_expectations` (1), `self.workflow.job_episodes` (2), `self.workflow.launch_instructions` (2), `self.workflow.native_estimation_context` (1), `self.workflow.native_event_information` (2), `self.workflow.pending_work` (1), `self.workflow.resource_context` (1), `self.workflow.resource_estimator` (4), `self.workflow.shared_information_context` (1), `self.workflow.store` (2) |
| decision_state.py | 55 | What the model sees: goal, scope, working_state, visible_record_refs, current_credit / evidence vector / investigation_progress, credit_binding, time_accounting, pending_work, last_local_outcome, feedback, visual_evidence (last image.view), report_deliveries, controller + controller_binding, tools, tool_knowledge, job_episode_options, available_report_facts, requested_report_purpose, requested_form, current_report_update, current_report_basis_refs, report_lifecycle; plus specialist decision_context (internal_summary) and _completed_work_axis_results. | `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.binding_context` (1), `self.workflow.catalog` (1), `self.workflow.controller_binding` (1), `self.workflow.delivery_status` (1), `self.workflow.extra_report_sources` (1), `self.workflow.job_episode_options` (1), `self.workflow.journal` (3), `self.workflow.knowledge` (1), `self.workflow.local_outcome_preview` (1), `self.workflow.pending_work` (1), `self.workflow.receipt_projection` (1), `self.workflow.run_id` (1), `self.workflow.source_credit_binding` (1), `self.workflow.source_credit_view` (1), `self.workflow.specialist` (1), `self.workflow.store` (3), `self.workflow.tools` (1), `self.workflow.working_state` (1), `table:runtime_actions` (2) |
| episode.py | 52 | Composes the binding (role `launch_local`, commissioning parent `sequence_homology_evidence/execution_job_submission`, no entry roles, no children, permitted actions `('tool',)`, replaces_default_instructions=True, context hooks only for launch_local). | `import:a101.library.blast_axis_summaries` (1), `import:a101.library.blast_return_contracts` (1) |
| execution_contracts.py | 59 | Launch-family constants: VERSION, LAUNCH_VERSION `execution_launch_assignment_v1`, RESULTS_VERSION, RESULT_PROVIDER `episode.execution_result`, ROLES, KINDS, ROLE_KINDS, NATIVE_RESULT_ORIGIN (current filesystem, unverified attempt output version, non-atomic windows), RESULTS_SCHEMA, NATIVE_SELECTOR_SCHEMA, launch/native-result operation catalogs, `_outcome`. Re-exports many shared-root helpers. | `import:a101.communication` (1), `import:a101.domain` (1), `import:a101.execution_contracts` (1), `import:a101.launch_instructions` (1), `import:a101.library.blast_return_contracts` (1), `import:a101.local_file_capture_results` (1), `import:a101.native_blast_acquisition` (1), `import:a101.native_blast_database_acquisition` (1), `import:a101.native_blast_masking_acquisition` (1), `import:a101.native_blast_standard_database_acquisition` (1), `import:a101.native_blast_utility_acquisition` (1), `import:a101.native_hmmer_acquisition` (1), `import:a101.native_hmmer_preparation_acquisition` (1), `import:a101.practical_execution_operations` (1), `import:a101.practical_execution_records` (1), `import:a101.practical_execution_state` (1), `import:a101.practical_receipt_information` (1), `import:a101.resource_records` (1) |
| execution_operations.py | 174 | Resource information, capabilities and tool contracts for bound A101 launch/result/homology operations; tool catalog per context (native result family catalogs or resource exec_command catalog) and tool execution routing. | `import:a101.bvbrc_proteome_tool_info` (1), `import:a101.library.bvbrc_homology_return_values` (1), `import:a101.library.bvbrc_proteome_return_values` (1), `import:a101.library.retained_input_authority.bvbrc_alignment_returns` (1), `import:a101.library.retained_input_authority.bvbrc_application_returns` (1), `import:a101.library.retained_input_authority.bvbrc_comparative_systems_returns` (1), `import:a101.library.retained_input_authority.bvbrc_fastqutils_returns` (1), `import:a101.library.retained_input_authority.bvbrc_genome_alignment_returns` (1), `import:a101.library.retained_input_authority.bvbrc_phylogeny_returns` (1), `import:a101.native_blast_database_results` (1), `import:a101.native_blast_masking_results` (1), `import:a101.native_blast_results` (1), `import:a101.native_blast_standard_database_results` (1), `import:a101.native_blast_utility_results` (1), `import:a101.native_file_capture` (1), `import:a101.native_hmmer_preparation_results` (1), `import:a101.native_hmmer_results` (1) |
| execution_state.py | 89 | `_delegate` (practical resource or API execution), initialize (checks original parent Launch inputs: masking/utility inputs, immutable input versions, native BLAST database inputs), state, `_target`, `_selection` (receipt-backed known/initial record refs), `_context_target`. | `import:a101.episode_receipts` (1), `import:a101.native_blast_database_result_publication` (1), `import:a101.native_blast_standard_database_result_publication` (1), `table:runtime_actions` (1), `table:runtime_episodes` (1), `table:runtime_receipt_inheritance` (2), `table:sqlite_master` (1) |
| from_parent.py | 111 | Assignment schema: anyOf one request per bound local resource (resource_id const, resource_kind const, requested_job anyOf generic + native job + preparation schemas). prepare_assignment only from parent role `launch`; re-validates the parent's whole Launch form, masking/utility inputs, immutable input versions, native BLAST database job inputs. initial_references = masking/utility inputs. | `import:a101.hpc_launch_authentication` (1), `import:a101.native_blast_database_result_publication` (1), `import:a101.native_blast_standard_database_result_publication` (1) |
| from_parent_launch.py | 9 | Schema of the parent's original Launch form (`execution_launch_assignment_v1`: requests per resource, immutable_input_versions, constraints, launch_instructions selection). | none |
| goal.py | 9 | Goal text = the resource-specific TerminalExecutionBehavior.instructions (delegated). | none |
| internal_summary.py | 52 | initial_decision_context: execution_resource_capabilities, execution_initial_information, received_bvbrc_values / received_minhash_values. decision_context: delegate's execution_assignment, execution_resource, coordinator_workspace, execution_progress, execution_completion, plus selected_execution_task (scientific question and selected tool info from the scientific parent task, the single native job view). | `import:a101.library.native_profile_presentation` (1) |
| native_input_custody.py | 313 | Custody checks of native inputs: masking/utility selectors and retained targets, input-version validation, recorded Results commission restore, selector validation per native family, protected protein-structure/ATAC/chromatin/FBA/fluorescence/NMF reference access, ATAC/MACS2/LUMPY/NMF/fluorescence/FBA job input validation. | `import:a101.episode_receipts` (1), `import:a101.episode_return_records` (1), `import:a101.execution_contracts` (1), `import:a101.execution_input_versions` (1), `import:a101.library.blast_pairwise_result_views` (1), `import:a101.library.blast_utility_result_views` (2), `import:a101.library.hmmer_native_result_views` (1), `import:a101.library.hmmer_preparation_result_views` (1), `import:a101.library.native_blast_database_result_views` (1), `import:a101.library.native_blast_standard_database_result_views` (1), `import:a101.library.retained_input_authority.atac_differential_operands` (1), `import:a101.library.retained_input_authority.expression_nmf_operands` (1), `import:a101.library.retained_input_authority.fluorescence_operands` (1), `import:a101.library.retained_input_authority.flux_balance_request_binding` (1), `import:a101.library.retained_input_authority.lumpy_request_binding` (1), `import:a101.library.retained_input_authority.protein_structure_operands` (1), `import:a101.library.retained_input_authority.received_native_file_inputs` (1), `import:a101.library.sequence_masking_result_views` (2), `table:runtime_actions` (1), `table:runtime_episodes` (1), `table:runtime_report_attempts` (1) |
| received_evidence.py | 351 | Received report sources/facts/closure facts from execution children (masking, utility, UniProt, BLAST databases, HMMER preparation, BLAST pairwise, BV-BRC data, MinHash, appservice families), reference resolution of received records, received report validation, received form references. | `import:a101.library.blast_pairwise_result_views` (1), `import:a101.library.blast_utility_result_views` (1), `import:a101.library.bvbrc_data_views` (1), `import:a101.library.bvbrc_homology_return_values` (1), `import:a101.library.bvbrc_minhash_views` (1), `import:a101.library.bvbrc_proteome_return_values` (1), `import:a101.library.hmmer_native_result_views` (1), `import:a101.library.hmmer_preparation_result_views` (1), `import:a101.library.native_blast_database_result_views` (1), `import:a101.library.native_blast_standard_database_result_views` (1), `import:a101.library.retained_input_authority.bvbrc_alignment_returns` (1), `import:a101.library.retained_input_authority.bvbrc_application_returns` (1), `import:a101.library.retained_input_authority.bvbrc_comparative_systems_returns` (1), `import:a101.library.retained_input_authority.bvbrc_fastqutils_returns` (1), `import:a101.library.retained_input_authority.bvbrc_genome_alignment_returns` (1), `import:a101.library.retained_input_authority.bvbrc_phylogeny_returns` (1), `import:a101.library.sequence_masking_result_views` (1), `import:a101.library.uniprot_return_contracts` (1) |
| report_delivery.py | 34 | finish: report-less closure returns credit + pending_handles + current report facts; otherwise build the typed form from saved facts + report_values once and save it. | `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.binding_context` (1), `self.workflow.episode_bindings` (1), `self.workflow.facts` (1), `self.workflow.journal` (2), `self.workflow.pending_handles` (1), `self.workflow.release` (2), `self.workflow.source_credit_view` (1), `table:runtime_forms` (2) |
| result_acquisition.py | 209 | Result directory, requested byte windows, selected result actions, publishing and validating result bodies, `_generic_result_selector_progress` (credits newly covered requested byte positions once), `_native_results_complete` (completed attempt with returncode 0 and all requested bytes covered). | `table:runtime_actions` (2), `table:runtime_episodes` (1) |
| task.py | 214 | Decision source loop: replay/restore, model call, apply response (validation feedback incl. component return channels, BV-BRC MinHash input detail, reads.map parameter errors), execute selected tool, record outcome, automatic score updates, credit, staged unit. | `import:a101.episode_source_failure` (1), `import:a101.library.live_runtime_functions` (1), `import:a101.library.read_mapping_values` (1), `import:a101.providers` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.action_schema` (1), `self.workflow.automatic_score_updates` (1), `self.workflow.completed_unit` (3), `self.workflow.completions` (3), `self.workflow.controller_value` (2), `self.workflow.decision_exchanges` (3), `self.workflow.delivery_resolution_inputs` (1), `self.workflow.execute` (1), `self.workflow.execution_binding` (7), `self.workflow.inprocess_replay` (4), `self.workflow.journal` (7), `self.workflow.next_return` (1), `self.workflow.pending_work` (1), `self.workflow.receive_native_outcome` (1), `self.workflow.receive_outcome` (1), `self.workflow.resolve_pending_deliveries` (1), `self.workflow.resolver` (1), `self.workflow.retain_shared_grading_results` (1), `self.workflow.run_id` (2), `self.workflow.selected` (3), `self.workflow.services` (1), `self.workflow.source_credit_view` (1), `self.workflow.store` (7), `self.workflow.validate_report` (1), `table:runtime_actions` (8), `table:runtime_episodes` (1), `table:runtime_model_calls` (2) |
| task_decision.py | 294 | Model call with recorded-request replay, contract-information profile freezing, decision_exchange_v1 request_context exchanges (child_options, composition_information, own attempt lookups), restored_episode_history, yield_table snapshot. | `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.contract_information_profile` (1), `self.workflow.contract_information_reply` (1), `self.workflow.controller_binding` (1), `self.workflow.decision_exchanges` (4), `self.workflow.decision_protocol` (3), `self.workflow.execute` (1), `self.workflow.freeze_contract_information` (1), `self.workflow.freeze_literature_numerical_contracts` (1), `self.workflow.history_preview` (1), `self.workflow.journal` (3), `self.workflow.numerical_contracts` (1), `self.workflow.provider` (4), `self.workflow.receipts` (4), `self.workflow.run_id` (1), `self.workflow.services` (1), `self.workflow.store` (2), `self.workflow.uses_received_record_context` (2), `self.workflow.validate_contract_information` (5), `table:runtime_model_calls` (8) |
| task_instructions.py | 26 | Shared A-root investigator INSTRUCTIONS text and composer; for this binding the specialist goal replaces it (replaces_default_instructions); appends knowledge/launch instruction library text, pending_child_delivery repair, wait and native event guidance when permitted, decision-exchange history guidance. | `self.workflow.binding_context` (1), `self.workflow.decision_protocol` (1), `self.workflow.knowledge` (1), `self.workflow.launch_instructions` (1), `self.workflow.native_event_information` (1), `self.workflow.permits_common_action` (3), `self.workflow.specialist` (1) |
| task_state.py | 115 | Decision-source state (report_values from parent's initial_report, interpretation schema from report contract), execution failure recording as a failed outcome entering the iterator, restore/checkpoint/effect recording. | `import:a101.episode_source_failure` (1), `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.archive` (1), `self.workflow.completions` (4), `self.workflow.context` (1), `self.workflow.controller_value` (1), `self.workflow.execution_binding` (4), `self.workflow.grains` (1), `self.workflow.inprocess_replay` (7), `self.workflow.journal` (5), `self.workflow.progress_provider` (2), `self.workflow.recover_commissions` (1), `self.workflow.run_id` (1), `self.workflow.source_credit_view` (1), `self.workflow.store` (2), `table:runtime_actions` (5) |
| terminal_execution.py | 242 | The episode's actual goal and tool: TerminalExecutionBehavior with `exec_command` (cmd, workdir, env, target resource/coordinator); instructions "You are the execution agent for the actual job and resource assigned below..."; decision context (assignment, resource, coordinator workspace, execution_progress, execution_completion); execute -> PracticalState receipts; fact sources practical_completed / practical_receipt_digests / practical_receipt_refs; PracticalYieldEstimator; report validation against recorded facts. | `import:a101.acquisition` (1), `import:a101.communication` (1), `import:a101.domain` (1), `import:a101.practical_execution_operations` (1), `import:a101.practical_execution_records` (1), `import:a101.practical_execution_state` (1), `import:a101.practical_receipt_information` (3), `import:a101.practical_yield` (1), `import:a101.terminal_execution` (1), `import:a101.terminal_scientific_evidence` (2), `name:PracticalYieldEstimator` (2) |
| to_parent.py | 296 | Report fact sources (native HMMER, masking, utility, UniProt, BLAST DB, HMMER prep, BLAST pairwise, appservice, BV-BRC, MinHash, terminal practical facts, execution_handoff_refs, execution_completed, execution_result_origin, execution_blast_hsps, BLAST graded return); facts (native family facts or practical facts + handoff refs); resolve (many reference namespaces); validate_report (form must equal recorded facts). | `import:a101.episode_bindings` (2), `import:a101.library.blast_pairwise_result_views` (2), `import:a101.library.blast_result_views` (1), `import:a101.library.blast_utility_result_views` (2), `import:a101.library.bvbrc_data_views` (2), `import:a101.library.bvbrc_homology_return_values` (1), `import:a101.library.bvbrc_minhash_views` (1), `import:a101.library.bvbrc_proteome_return_values` (1), `import:a101.library.hmmer_native_result_views` (2), `import:a101.library.hmmer_preparation_result_views` (3), `import:a101.library.native_blast_database_result_views` (1), `import:a101.library.native_blast_standard_database_result_views` (1), `import:a101.library.retained_input_authority.bvbrc_alignment_returns` (1), `import:a101.library.retained_input_authority.bvbrc_application_returns` (1), `import:a101.library.retained_input_authority.bvbrc_comparative_systems_returns` (1), `import:a101.library.retained_input_authority.bvbrc_fastqutils_returns` (1), `import:a101.library.retained_input_authority.bvbrc_genome_alignment_returns` (1), `import:a101.library.retained_input_authority.bvbrc_phylogeny_returns` (1), `import:a101.library.sequence_masking_result_views` (2), `import:a101.library.uniprot_return_contracts` (2), `import:a101.local_file_capture_results` (1), `import:a101.native_blast_database_results` (2), `import:a101.native_blast_standard_database_results` (2), `import:a101.native_hmmer_acquisition` (1) |
| waiting.py | 9 | suspension_changed: mark external execution backend suspension. | `self.workflow.execution_backend` (1), `self.workflow.execution_handle` (2) |
| yield_estimator.py | 58 | Continuation: requires private yield binding; profile `launch_local:<request yield class>` from task_yield_profiles (class from request version / resource kind / native job names / endpoint); YieldController(cutoff, YieldParameters) with PracticalYieldEstimator (endpoint completion proof). | `import:a101.numerical` (1), `import:a101.practical_yield` (2), `name:PracticalYieldEstimator` (4), `name:YieldController` (2), `name:YieldParameters` (2) |

Old-runner names are counted per file: `self.workflow.<member>` (also `source.workflow` and `workflow.` in module functions), `self.services.<member>`, journal/receipt table names, imports from old shared-root modules (`import:<module>`), and old yield/rebinding names (`name:`). No `BindingContext` literal occurs in these files; the old binding context arrives through `self.workflow.binding_context(...)`. The same rows are in `runs/carry_over/calls/a101_02.tsv`.
