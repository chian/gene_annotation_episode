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

## Carried over

Rows are the old functions of the episode folder at `97308b94c` (`runs/carry_over/functions/a101__sequence_homology_evidence__execution_job_submission__local_job_execution.tsv`), one per row. New files are in `gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/execution_job_submission/local_job_execution/`. "unplaced" rows are also in `carry_over_blocked/a101__sequence_homology_evidence__execution_job_submission__local_job_execution.md`. Library candidates (they stay in this episode's files, not in the library): `messages/internal_summary.py` `_completion`, `yield_estimator.py` `_request_yield_class`, `messages/final_to_parent.py` `validate_report`, `_resolver`, `_facts`, `_report_schema`, `task.py` `_resource_configuration`, `_resource_information`, `_handoff`.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | OperationalBindingRecord | machinery | binding_record.py (the binding's own record) |
| binding_record.py | OperationalBindingRecord.as_record | machinery | binding's own as_record() (README 3e) |
| configuration.py | OperationalConfiguration | episode function | settings (ctx.settings) of the episode: task.py _resource_configuration, _resource_information; yield_estimator.py _task_yield_profile |
| configuration.py | OperationalConfiguration.__init__ | episode function | values become ctx.settings (resources, initial_information, coordinator_workspace, launch/tool-knowledge directories, task_yield_profiles); resource checks in task.py _resource_configuration (kind local, bound, native bindings: validate_primary_resource_bindings and validate_preparation_resource_binding unplaced -> raise); handoff_unit/acquired_record_unit/log_window/log_roles/results_yield_profiles/api/progress provider/native result readers/tool_registry binding = old-runner wiring or results/API role (not carried) |
| credit.py | ExecutionEpisodeCredit | episode function | credit.py credit (practical branch) |
| credit.py | ExecutionEpisodeCredit.credit_kind | machinery | credit_kind deleted (README 3d) |
| credit.py | ExecutionEpisodeCredit._closed_credit_carrier | machinery | closed credit re-authentication over runtime_episodes/archive (README 3e F8) |
| credit.py | ExecutionEpisodeCredit._closed_credit_receipts | machinery | closed credit receipt-prefix re-validation (EpisodeReceipts, runtime_* tables) |
| credit.py | ExecutionEpisodeCredit._closed_credit_value | machinery | closed credit value; completion['credit'] is the closure credit |
| credit.py | ExecutionEpisodeCredit._closed_credit_facts | machinery | closed credit snapshot fact (runtime_forms facts); the system returns completion['credit'] |
| credit.py | ExecutionEpisodeCredit._closed_operational_credit_view | machinery | closed credit view re-verification (runtime_episodes, observation history) |
| credit.py | ExecutionEpisodeCredit.project_credit | episode function | credit.py credit |
| credit.py | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py credit (practical branch: project_practical_credit); the native result family branches belong to the results role: unplaced |
| credit.py | ExecutionEpisodeCredit.credit_view | episode function | credit.py credit |
| credit.py | ExecutionEpisodeCredit._proof_for_action | episode function | unplaced: results role native completeness proof read from runtime_actions (BLOCKED-ON-STORE-ACCESS pattern runtime_actions); the practical proof is messages/internal_summary.py _completion |
| credit.py | ExecutionEpisodeCredit.completion_for_action | episode function | messages/internal_summary.py _completion (practical proof, derived from the receipts); the proof is not a controller input (README 5 item 5) |
| credit.py | ExecutionEpisodeCredit._closed_completion_verdict | machinery | reads runtime_observations / ESTIMATOR_VERSION of earlier controller records (README 3d) |
| credit.py | ExecutionEpisodeCredit.verify_completion | machinery | PracticalYieldEstimator verification callback; replaced by the completion controller (README 7b) |
| decision_inputs.py | OperationalDecisionInputs | episode function | task.py decide (context assembly) |
| decision_inputs.py | OperationalDecisionInputs.decision_inputs | episode function | task.py decide: launch_instruction_library, selected_launch_instructions, execution_resource_capabilities, execution_initial_information; resource_context, shared_information_context, completed_action_reports, requested_action_history, pending_work, execution_expectations, job_execution_options, resource_tool_estimates, native_execution_expectations, native_event_targets, contract_information_profile, child_options = old runner providers (self.workflow.*), no service for them: not carried |
| decision_inputs.py | _bind_original_task_runtime_providers | machinery | provider patching |
| decision_state.py | OperationalDecisionState | episode function | messages/internal_summary.py and task.py decide |
| decision_state.py | OperationalDecisionState.decision_state | episode function | messages/internal_summary.py internal_summary (assignment, receipts, progress, completion, controller) and task.py decide (context, feedback, time_accounting); working_state/visible_record_refs/credit_binding/visual_evidence/report_deliveries/report_lifecycle/available_report_facts read the old journal or report machinery: not carried |
| decision_state.py | _bind_original_task_runtime_providers | machinery | provider patching |
| episode.py | ExecutionEpisode | episode function | episode.py LocalJobExecution |
| episode.py | ExecutionEpisode.child_roles | episode function | task.py CHILD_SLOTS = {} |
| episode.py | ExecutionEpisode.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| episode.py | ExecutionEpisode.permitted_common_actions | machinery | common-action set of the old decision machine; decide always produces an exec_command unit |
| episode.py | ExecutionEpisode.context_hook_applies | machinery | context hook of the old runner |
| execution_contracts.py | launch_operation_catalog | episode function | unplaced: catalog of the execution.capabilities tool of the parent role launch; this role offers exec_command only |
| execution_contracts.py | native_result_operation_catalog | episode function | unplaced: results-role function (acquires results of a handed-off job); this launch role never calls it; no place in the ten files of this episode |
| execution_contracts.py | _outcome | machinery | invalid-outcome record of the old runner; a refused answer is Rejected in action |
| execution_operations.py | OperationalOperations | episode function | task.py (tools, resource information) |
| execution_operations.py | OperationalOperations._resource_information | episode function | task.py _resource_information |
| execution_operations.py | OperationalOperations.capabilities | episode function | task.py decide (execution_resource_capabilities) |
| execution_operations.py | OperationalOperations.resource_tool_contracts | machinery | tool_registry contract routes (entry_role / invocation_route commission routing) |
| execution_operations.py | OperationalOperations.catalog | episode function | task.py EXEC_COMMAND, TOOLS (native result catalogs: results role, unplaced) |
| execution_operations.py | OperationalOperations.execute | episode function | task.py exec_command (BLOCKED-ON-JOB-SERVICE job_access.exec_command) |
| execution_operations.py | OperationalOperations._has_appservice | episode function | unplaced: API-resource branch; never applies to a local resource |
| execution_operations.py | OperationalOperations._has_uniprot | episode function | unplaced: API-resource branch; never applies to a local resource |
| execution_operations.py | OperationalOperations._appservice_sources | episode function | unplaced: API-resource branch; never applies to a local resource |
| execution_state.py | OperationalExecutionState | episode function | task.py _operations and messages/internal_summary.py |
| execution_state.py | OperationalExecutionState._delegate | episode function | task.py _operations (the local transport TerminalExecution of the assigned resource) |
| execution_state.py | OperationalExecutionState._practical_context | machinery | identity function |
| execution_state.py | OperationalExecutionState.initialize | machinery | PracticalState initialisation (file ledger); the baseline validations are messages/internal_summary.py |
| execution_state.py | OperationalExecutionState._check_parent_inputs | machinery | check of the commission against runtime_episodes (wrong commission fails) |
| execution_state.py | OperationalExecutionState.state | machinery | PracticalState handle; receipts are tool outcomes in the summary |
| execution_state.py | OperationalExecutionState._target | episode function | unplaced: results-role function (acquires results of a handed-off job); this launch role never calls it; no place in the ten files of this episode |
| execution_state.py | OperationalExecutionState._selection | machinery | receipts bookkeeping (runtime_receipt_inheritance, runtime_actions, EpisodeReceipts) |
| execution_state.py | OperationalExecutionState._context_target | episode function | unplaced: results-role function (acquires results of a handed-off job); this launch role never calls it; no place in the ten files of this episode |
| from_parent.py | OperationalAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | OperationalAssignment.child_assignment_schema | machinery | child assignment schema offered by the launch parent for its own child (frozen HPC launch); this episode has no children |
| from_parent.py | OperationalAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | OperationalAssignment._permitted | episode function | unplaced: the launch parent's per-resource permission test over its own Launch form constraints (a parent-side function of execution_job_submission) |
| from_parent.py | OperationalAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (validate_assignment); masking/utility/immutable-version/native database input checks against the parent's Launch form = commission checks (wrong commission fails): not carried |
| from_parent.py | OperationalAssignment._request_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | OperationalAssignment._validate_request | episode function | messages/read_from_parent.py read_from_parent (validate_assignment) and task.py _operations (workspace confinement, transport validate_assignment) |
| from_parent.py | OperationalAssignment._launch | machinery | re-validation of the parent's whole Launch form (README 3b C3, rule 1) |
| from_parent.py | OperationalAssignment._constraints | machinery | part of the re-validation of the parent's Launch form |
| from_parent.py | OperationalAssignment.initial_references | episode function | messages/read_from_parent.py ASSIGNMENT_FORM record_refs |
| from_parent_launch.py | LaunchParentAssignment | machinery | child re-admission of the parent's original Launch form (README 3b C3) |
| from_parent_launch.py | LaunchParentAssignment._parent_launch_assignment_schema | machinery | child re-admission of the parent's original Launch form |
| goal.py | OperationalGoal | episode function | goal.py and task.py GOAL_INSTRUCTION |
| goal.py | OperationalGoal.instructions | episode function | task.py GOAL_INSTRUCTION, _instructions (text of TerminalExecutionBehavior.instructions) |
| internal_summary.py | OperationalSummary | episode function | messages/internal_summary.py and task.py decide |
| internal_summary.py | OperationalSummary.initial_decision_context | episode function | task.py decide (execution_resource_capabilities, execution_initial_information); received_bvbrc_values/received_minhash_values are API-only: unplaced |
| internal_summary.py | OperationalSummary._with_selected_execution_task | episode function | messages/internal_summary.py _selected_execution_task; the resource information of the request is added in task.py decide; native_profile_scientific_job_view unplaced -> raise |
| internal_summary.py | OperationalSummary.decision_context | episode function | messages/internal_summary.py internal_summary |
| native_input_custody.py | NativeInputCustody | episode function | see its methods: commission checks not carried; results-role selectors unplaced |
| native_input_custody.py | NativeInputCustody._masking_selector | episode function | unplaced: results-role function (acquires results of a handed-off job); this launch role never calls it; no place in the ten files of this episode |
| native_input_custody.py | NativeInputCustody._masking_inputs | machinery | check of the job inputs against the parent's Launch form and the Store (validate_job_inputs / validate_execution_input_versions are in no place now); wrong commission fails |
| native_input_custody.py | NativeInputCustody._retained_masking_target | episode function | unplaced: results-role function (acquires results of a handed-off job); this launch role never calls it; no place in the ten files of this episode |
| native_input_custody.py | NativeInputCustody._masking_reference_access | machinery | reference resolution through the receipts ledger (README 3b D2: records.holds) |
| native_input_custody.py | NativeInputCustody._utility_selector | episode function | unplaced: results-role function (acquires results of a handed-off job); this launch role never calls it; no place in the ten files of this episode |
| native_input_custody.py | NativeInputCustody._utility_inputs | machinery | check of the job inputs against the parent's Launch form and the Store (validate_job_inputs / validate_execution_input_versions are in no place now); wrong commission fails |
| native_input_custody.py | NativeInputCustody._retained_utility_target | episode function | unplaced: results-role function (acquires results of a handed-off job); this launch role never calls it; no place in the ten files of this episode |
| native_input_custody.py | NativeInputCustody._utility_reference_access | machinery | reference resolution through the receipts ledger (README 3b D2: records.holds) |
| native_input_custody.py | NativeInputCustody._versions | machinery | check of the job inputs against the parent's Launch form and the Store (validate_job_inputs / validate_execution_input_versions are in no place now); wrong commission fails |
| native_input_custody.py | NativeInputCustody._recorded_results_assignment | machinery | restores a returned Results commission from runtime_report_attempts / EpisodeReceipts |
| native_input_custody.py | NativeInputCustody._selector | episode function | unplaced: results-role function (acquires results of a handed-off job); this launch role never calls it; no place in the ten files of this episode |
| native_input_custody.py | NativeInputCustody._protein_reference_access | machinery | reference resolution through the receipts ledger (README 3b D2: records.holds) |
| native_input_custody.py | NativeInputCustody._atac_reference_access | machinery | reference resolution through the receipts ledger (README 3b D2: records.holds) |
| native_input_custody.py | NativeInputCustody._chromatin_reference_access | machinery | reference resolution through the receipts ledger (README 3b D2: records.holds) |
| native_input_custody.py | NativeInputCustody._flux_balance_reference_access | machinery | reference resolution through the receipts ledger (README 3b D2: records.holds) |
| native_input_custody.py | NativeInputCustody._fluorescence_reference_access | machinery | reference resolution through the receipts ledger (README 3b D2: records.holds) |
| native_input_custody.py | NativeInputCustody._expression_nmf_reference_access | machinery | reference resolution through the receipts ledger (README 3b D2: records.holds) |
| native_input_custody.py | NativeInputCustody._atac_inputs | machinery | check of the job inputs against the parent's Launch form and the Store (validate_job_inputs / validate_execution_input_versions are in no place now); wrong commission fails |
| native_input_custody.py | NativeInputCustody._macs2_peak_inputs | machinery | check of the job inputs against the parent's Launch form and the Store (validate_job_inputs / validate_execution_input_versions are in no place now); wrong commission fails |
| native_input_custody.py | NativeInputCustody._lumpy_inputs | machinery | check of the job inputs against the parent's Launch form and the Store (validate_job_inputs / validate_execution_input_versions are in no place now); wrong commission fails |
| native_input_custody.py | NativeInputCustody._expression_nmf_inputs | machinery | check of the job inputs against the parent's Launch form and the Store (validate_job_inputs / validate_execution_input_versions are in no place now); wrong commission fails |
| native_input_custody.py | NativeInputCustody._fluorescence_inputs | machinery | check of the job inputs against the parent's Launch form and the Store (validate_job_inputs / validate_execution_input_versions are in no place now); wrong commission fails |
| native_input_custody.py | NativeInputCustody._matches_flux_balance_assignment | episode function | unplaced: flux-balance (A110) assignment match; not an A101 job |
| received_evidence.py | ReceivedOperationalEvidence | machinery | received-report receipts bookkeeping and validation (README 3b R1, R3; F5) |
| received_evidence.py | ReceivedOperationalEvidence._received | machinery | received-report receipts bookkeeping and validation (README 3b R1, R3; F5) |
| received_evidence.py | ReceivedOperationalEvidence.received_report_sources | machinery | received-report receipts bookkeeping and validation (README 3b R1, R3; F5) |
| received_evidence.py | ReceivedOperationalEvidence.received_report_facts | machinery | received-report receipts bookkeeping and validation (README 3b R1, R3; F5) |
| received_evidence.py | ReceivedOperationalEvidence.received_report_closure_facts | machinery | received-report receipts bookkeeping and validation (README 3b R1, R3; F5) |
| received_evidence.py | ReceivedOperationalEvidence.resolve_received_reference | machinery | received-report receipts bookkeeping and validation (README 3b R1, R3; F5) |
| received_evidence.py | ReceivedOperationalEvidence.validate_received_report | machinery | received-report receipts bookkeeping and validation (README 3b R1, R3; F5) |
| received_evidence.py | ReceivedOperationalEvidence.received_form_references | machinery | received-report receipts bookkeeping and validation (README 3b R1, R3; F5) |
| report_delivery.py | OperationalReportDelivery | machinery | report delivery and release (runtime_forms, workflow.release) |
| report_delivery.py | OperationalReportDelivery.finish | machinery | report saving and release; the form is filled by messages/final_to_parent.py final_to_parent |
| report_delivery.py | _bind_original_task_runtime_providers | machinery | provider patching |
| result_acquisition.py | OperationalResultAcquisition | episode function | unplaced: results-role function (acquires results of a handed-off job); this launch role never calls it; no place in the ten files of this episode |
| result_acquisition.py | OperationalResultAcquisition._result_directory | episode function | unplaced: results-role function (acquires results of a handed-off job); this launch role never calls it; no place in the ten files of this episode |
| result_acquisition.py | OperationalResultAcquisition._windows | episode function | unplaced: results-role function (acquires results of a handed-off job); this launch role never calls it; no place in the ten files of this episode |
| result_acquisition.py | OperationalResultAcquisition._selected_result_action | episode function | unplaced: results-role function (acquires results of a handed-off job); this launch role never calls it; no place in the ten files of this episode |
| result_acquisition.py | OperationalResultAcquisition._execute_native_results | episode function | unplaced: results-role function (acquires results of a handed-off job); this launch role never calls it; no place in the ten files of this episode |
| result_acquisition.py | OperationalResultAcquisition._publish_result | episode function | unplaced: results-role function (acquires results of a handed-off job); this launch role never calls it; no place in the ten files of this episode |
| result_acquisition.py | OperationalResultAcquisition._validate_result_body | episode function | unplaced: results-role function (acquires results of a handed-off job); this launch role never calls it; no place in the ten files of this episode |
| result_acquisition.py | OperationalResultAcquisition._read_result | episode function | unplaced: results-role function (acquires results of a handed-off job); this launch role never calls it; no place in the ten files of this episode |
| result_acquisition.py | OperationalResultAcquisition._generic_result_selector_progress | episode function | unplaced: results-role function (acquires results of a handed-off job); this launch role never calls it; no place in the ten files of this episode |
| result_acquisition.py | OperationalResultAcquisition._native_results_complete | episode function | unplaced: results-role function (acquires results of a handed-off job); this launch role never calls it; no place in the ten files of this episode |
| task.py | OperationalTask | episode function | task.py decide, action, exec_command |
| task.py | OperationalTask.instructions | episode function | task.py _instructions (services.instructions composer, task_instructions.instructions) |
| task.py | OperationalTask.next | episode function | task.py decide / action (replay, restore, source-failure, delivery branches are old-runner machinery) |
| task.py | OperationalTask.apply_response | episode function | task.py action (arguments schema + transport validation -> Rejected); contract/MinHash/reads.map/report-update repair feedback belongs to the old report and component channels: not carried |
| task.py | OperationalTask.execute | episode function | task.py exec_command (BLOCKED-ON-JOB-SERVICE job_access.exec_command); journal.save/receive_outcome/automatic_score_updates/controller_value = machinery |
| task.py | _bind_original_task_runtime_providers | machinery | provider patching |
| task_decision.py | OperationalTaskDecision | machinery | decision exchange and recorded model call (README 3a) |
| task_decision.py | OperationalTaskDecision.call | machinery | model call, recorded request replay, contract-information freezing (README 3a); the request is built in task.py decide |
| task_decision.py | OperationalTaskDecision.conversation_key | machinery | conversation state |
| task_decision.py | OperationalTaskDecision.interpretation_context | machinery | report interpretation context (report_update machinery) |
| task_decision.py | OperationalTaskDecision.exchange_schema | machinery | decision exchange |
| task_decision.py | OperationalTaskDecision.exchange_response | machinery | decision exchange |
| task_decision.py | OperationalTaskDecision.validate_contract_exchange_request | machinery | decision exchange |
| task_decision.py | OperationalTaskDecision.validate_contract_exchange_history | machinery | decision exchange |
| task_decision.py | OperationalTaskDecision.exchange_decision | machinery | decision exchange loop |
| task_decision.py | _bind_original_task_runtime_providers | machinery | provider patching |
| task_instructions.py | instructions | episode function | task.py _instructions (goal text + tool knowledge + launch instructions + answer text; the repair, wait and exchange paragraphs describe actions that no longer exist) |
| task_state.py | OperationalTaskState | machinery | decision-source state, restore and checkpoint |
| task_state.py | OperationalTaskState.__init__ | machinery | decision-source state (report_values from the parent's initial_report) |
| task_state.py | OperationalTaskState.bind_execution_context | machinery | execution context binding |
| task_state.py | OperationalTaskState.record_execution_failure | machinery | failed outcome recording (README 3a/3c: the tool returns the failure as its outcome) |
| task_state.py | OperationalTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | OperationalTaskState.restore | machinery | restore |
| task_state.py | OperationalTaskState.record_effect | machinery | record_effect |
| task_state.py | OperationalTaskState.checkpoint | machinery | checkpoint |
| task_state.py | _bind_original_task_runtime_providers | machinery | provider patching |
| terminal_execution.py | operation_catalog | episode function | task.py EXEC_COMMAND |
| terminal_execution.py | TerminalExecutionBehavior | episode function | task.py (tool, instructions, resource), messages/internal_summary.py, messages/final_to_parent.py |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | episode function | ctx.settings (resources, initial_information, coordinator_workspace) |
| terminal_execution.py | TerminalExecutionBehavior._operations | episode function | task.py _operations |
| terminal_execution.py | TerminalExecutionBehavior._assignment | episode function | messages/read_from_parent.py read_from_parent and task.py _operations |
| terminal_execution.py | TerminalExecutionBehavior._state_directory | machinery | PracticalState receipt directory (file ledger outside the Store) |
| terminal_execution.py | TerminalExecutionBehavior.initialize | machinery | PracticalState initialisation; baseline in messages/internal_summary.py |
| terminal_execution.py | TerminalExecutionBehavior.state | machinery | PracticalState handle |
| terminal_execution.py | TerminalExecutionBehavior.as_record | machinery | binding record |
| terminal_execution.py | TerminalExecutionBehavior.child_roles | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | TerminalExecutionBehavior.credit_kind | machinery | credit_kind deleted |
| terminal_execution.py | TerminalExecutionBehavior.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| terminal_execution.py | TerminalExecutionBehavior.permitted_common_actions | machinery | common-action set |
| terminal_execution.py | TerminalExecutionBehavior.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | TerminalExecutionBehavior.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent |
| terminal_execution.py | TerminalExecutionBehavior.initial_decision_context | episode function | task.py decide (execution_initial_information) |
| terminal_execution.py | TerminalExecutionBehavior._resource_information | episode function | task.py _resource |
| terminal_execution.py | TerminalExecutionBehavior._resource_instructions | episode function | task.py _instructions (LaunchInstructions.for_resource) |
| terminal_execution.py | TerminalExecutionBehavior.instructions | episode function | task.py GOAL_INSTRUCTION, _instructions |
| terminal_execution.py | TerminalExecutionBehavior.decision_context | episode function | task.py decide and messages/internal_summary.py |
| terminal_execution.py | TerminalExecutionBehavior.catalog | episode function | task.py EXEC_COMMAND |
| terminal_execution.py | TerminalExecutionBehavior.execute | episode function | task.py exec_command (BLOCKED-ON-JOB-SERVICE job_access.exec_command: PracticalState.begin/finish, TerminalExecution.execute, finalize_scientific_command, assess_validations); invalid-outcome branch is action's Rejected; PracticalReceiptInformation.publish -> ctx.store.artifact (BLOCKED-ON-STORE-ACCESS: library not carried) |
| terminal_execution.py | TerminalExecutionBehavior.completion_for_action | episode function | messages/internal_summary.py _completion |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | machinery | PracticalYieldEstimator; completion controller in yield_estimator.py (README 7b) |
| terminal_execution.py | TerminalExecutionBehavior.fact_sources | episode function | messages/final_to_parent.py OWN_SOURCES / RETURN_FORM |
| terminal_execution.py | TerminalExecutionBehavior.facts | episode function | messages/final_to_parent.py _facts |
| terminal_execution.py | TerminalExecutionBehavior.resolve | episode function | messages/final_to_parent.py _resolver |
| terminal_execution.py | TerminalExecutionBehavior.validate_report | episode function | messages/final_to_parent.py validate_report |
| terminal_execution.py | TerminalExecutionBehavior.credit_view | episode function | credit.py credit |
| to_parent.py | OperationalReport | episode function | messages/final_to_parent.py |
| to_parent.py | OperationalReport.required_return_sources | machinery | parent report-form requirement (returned ()) |
| to_parent.py | OperationalReport._forwards_bvbrc_reports | episode function | unplaced: API-resource branch; never applies to a local resource |
| to_parent.py | OperationalReport._forwards_minhash_reports | episode function | unplaced: API-resource branch; never applies to a local resource |
| to_parent.py | OperationalReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (OWN_SOURCES and the library fact-source functions; masking and utility sources have dotted names and cannot be declared; UniProt, AppService, MinHash, BLAST graded sources are results/API only) |
| to_parent.py | OperationalReport.facts | episode function | messages/final_to_parent.py _facts (closed credit facts: machinery) |
| to_parent.py | OperationalReport._live_facts | episode function | messages/final_to_parent.py _facts (native families empty for a launch; job_progress_provider handoff reader -> handoff_refs of the summary) |
| to_parent.py | OperationalReport.resolve | episode function | messages/final_to_parent.py _resolver (practical_receipt and execution_handoff); the native-family, API, protected-reference and Store-reading branches are results/API role or custody (records.holds): not carried |
| to_parent.py | OperationalReport.validate_report | episode function | messages/final_to_parent.py validate_report (validate_form then recorded-fact equality; native masking/utility/UniProt validate_received_report parts are results/API role: not carried) |
| waiting.py | OperationalTaskWaiting | machinery | wait/suspension machinery |
| waiting.py | OperationalTaskWaiting.suspension_changed | machinery | suspension machinery (execution_backend) |
| yield_estimator.py | ExecutionEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | yield_estimator.py _request_yield_class (compact and API branches cannot occur) |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py _task_yield_profile |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller (CompletionYieldController; private-yield flag check = old configuration) |
| yield_estimator.py | ExecutionEpisodeYield._launch_local_yield_controller | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator (README 7b) |
| yield_estimator.py | ExecutionEpisodeYield._private_practical_estimator | machinery | PracticalYieldEstimator (README 7b) |
