# a103/gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/<file>` (only files directly in this
folder; its child folders `api_job_execution/`, `hpc_job_execution/`, `local_job_execution/` and `tests/` are not
covered; no `grading/` or `scoring/`). Old binding class `ExecutionEpisode`
(`binding_path = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission'`,
`commissioning_parent = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution'`, `roles = ('launch',)`,
`entry_roles = ()`), decision source `LaunchTask`, prompt renderer `decision_presentation.present_launch_task`, record
version `execution_episode_v1`.

## What it is for (its goal, in its own words)

`goal.py`:

> Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, recorded
> inventory and timing information inform the choice. Preserve the original job, immutable inputs, constraints and
> pinned instructions. A resource child owns iterative execution in the shared loop. Receive its requested typed
> handoff; no infrastructure chooses an approach. Actual received usable handoff completes this launch endpoint with
> exact zero future credit.

## Task and instructions

Each unit is `execution.capabilities`, a resource child commission, a report redelivery, and outside an `hpc` ancestor
also a reasoning commit or a wait (`action_policy.py`; under this HPC parent: `tool, child, redeliver_report`).
Instructions (`instructions.py`): goal + reasoning-commit requirement when `reason` is permitted + tool knowledge +
launch library + pending-child repair + wait + native-event texts; exchange-history swap.

## What it reads from its parent's assignment

`execution_launch_assignment_v1` (`from_parent.assignment_schema`): `requests` (map resource_id -> concrete request: an
API service assignment or a `practical_assignment_v1` with `resource_id`, `resource_kind`, `requested_job` (generic or a
native family job), workspace confined to the resource), `immutable_input_versions`, `constraints`
(`allowed_resource_ids`, `allowed_kinds`, `resource_id`, `kind`), `launch_instructions` (selection). Admission: from an
`hpc`/`hpc_execution` parent the selection must be the exact planned launch (`hpc_launch_authentication`); every request
validated (BLAST-grader requests need an `ncbi_blast` resource); masking/utility inputs, immutable input versions and
native/standard BLAST database job inputs validated. Under this HPC parent the Launch child's initial context also
carries the parent's `hpc_execution_job` (prepared by the parent).

## Children

`launch_api` -> `api_job_execution`, `launch_local` -> `local_job_execution`, `launch_hpc` -> `hpc_job_execution`;
each offered only if a resource of that kind is permitted by the assignment.
- Sends (`to_child_*`): an `EpisodeRequest` whose goal is a child goal of this goal with the report-contract schema,
  message `scope`, `initial_report`, `job_assignment` (the chosen concrete request), `episode_assignment` (launch
  instructions), optional report-contract declaration, `gene_context_evidence`, in-process completion order,
  `knowledge_inheritance`.
- Takes back (`from_child_*`): the typed form's references (records in scope + binding-admitted return references),
  progress forms, native timing receipts and tool attributions, received as `child_form` (or `report_redelivery`).
  The usable handoff in that return is this episode's credit; the child's credit is not added.

## Decision state shown to the model

The old generic view plus `execution_resource_capabilities`, `execution_initial_information`, `received_bvbrc_values`,
`received_blast_jobs`, `received_minhash_values`, `execution_assignment`, `execution_progress`,
`selected_execution_task` (when the scientific parent task is known), and per call expectations keyed `launch`.
Presented through `present_launch_task` (stateful text prompt for HPC, scientific, API-launch, selected-execution,
monitor or receiver contexts).

## Tools

`execution.capabilities` — "Read the actual caller-bound resource configuration and already recorded inventory; no
discovery or selection." (masking/utility result catalogs when the context is such a retained target).

## Credit

Kind `operational`, unbounded: closed view, family view, or `handoff_unit x` count of new resource identities with a
usable received handoff not already in the initial known references (`execution_received_records_credit_v1`).

## Continuation

`yield_estimator._launch_yield_controller` (requires `require_private_yield`): remaining = (eligible original requests
without an initial usable handoff) x `handoff_unit`. If remaining > 0: `task_yield_profiles['launch:' + '+'.join(sorted
request classes)]` with a bounded controller capped at `remaining` (request class e.g. `practical_hpc_<native...>_handoff`,
`api_<service>[_<algorithm>][_<database>]_handoff`, `compact_<version>`). If nothing remains: exact-zero estimator with
cutoff 0 (initial credit must be 0). Completion proof via `PracticalYieldEstimator(verify_completion)`. New layout:
**bounded quality** (bound = remaining handoff credit) ending at the verified handoff endpoint (**completion with a
target** semantics: "Actual received usable handoff completes this launch endpoint with exact zero future credit").

## Report to its parent

Role `launch` facts: `execution_handoff_refs`, `execution_result_refs`, `execution_completed` (a received handoff is
returnable), `execution_result_origin`, `execution_blast_hsps`, native family facts; the HPC parent asks with
`hpc_launch_report_form` = `{execution_handoff_refs}`. Required source `execution_handoff_refs` under
`gene_context_evidence` with an annotation task. Fact fields must equal recorded facts.

## Differences from similar episodes

Identical to `a103/gene_context_evidence/hpc_work_planning/execution_job_submission` except `episode.py` (path, parent),
`binding_record.py`, `contracts.py` (terminal_execution import path) and the `to_child_*` docstrings; `task.py` has one
other copy; `closed_credit.py`, `received_record_selection.py`, `received_reference_custody.py`,
`report_reference_access.py` have 11 copies across execution episodes. Against Results: has children and (outside HPC)
`reason`/`wait`; its credit counts handoffs not bytes; its decision provider always uses its own presentation; its
`to_parent` restricts result-only sources to role `results`.

## Files

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | Empty package marker. | none |
| `action_policy.py` | 11 | Permitted common actions: under any `hpc` ancestor `tool, child, redeliver_report`; otherwise `tool, reason, child, wait, redeliver_report`. | `BindingContext`: path |
| `binding_record.py` | 9 | Binding identity record `execution_episode_v1` with this path and the execution configuration. | none |
| `child_commissioning.py` | 41 | Child roles `launch_api, launch_local, launch_hpc` for role `launch`, offered only for kinds with a permitted resource in the assignment; selects each child's private request assembler and report receiver. | `BindingContext`: assignment, role |
| `closed_credit.py` | 117 | Closed operational credit capture and reuse (same rule as Results; identical file in 11 execution episodes). | `BindingContext`: as_record×2, episode_id×8, role; `import`: episode_receipts, episode_return_records×3; `table`: runtime_episodes×2, runtime_forms×3, runtime_observations, runtime_receipt_inheritance×2, runtime_record_receipts×2 |
| `completion.py` | 118 | Launch completion: a completed action whose record refs include a usable handoff for this assignment's target; proof `practical_completion_v1`, validation key `received_usable_handoff`, endpoint `usable_handoff`; family proofs otherwise; recorded verdict reuse. | `BindingContext`: assignment×2, episode_id×7, run_id×3, scope; `import`: episode_return_records, method_loop.identities, numerical, practical_yield; `table`: runtime_actions, runtime_observations; `yield`: ESTIMATOR_VERSION, NumericBand |
| `configuration.py` | 65 | Construction settings identical to Results (`LaunchConfiguration`). | `import`: api_service_execution, execution_progress, numerical×2; `yield`: YieldController×2, YieldParameters×2 |
| `contracts.py` | 59 | The execution-family constants (same content as Results' `execution_contracts.py`, own `terminal_execution` import path). | `import`: a103_execution_bindings×11, a103_homology_execution×5, communication×2, domain, execution_contracts×4, gene_context_evidence.hpc_work_planning.hpc_allocation_execution.execution_job_submission.terminal_execution×2, launch_instructions, local_file_capture_results×5, native_blast_acquisition, native_blast_database_acquisition, native_blast_masking_acquisition, native_blast_standard_database_acquisition, native_blast_utility_acquisition, native_hmmer_acquisition, native_hmmer_preparation_acquisition, practical_execution_operations, practical_execution_records×4, practical_execution_state×2, practical_receipt_information, resource_records |
| `credit.py` | 48 | Credit kind `operational`: closed view, or family view, or `handoff_unit x` number of new resource identities with a usable received handoff not in the initial known refs (+ `acquired_record_unit x 0`); `execution_received_records_credit_v1`. | none |
| `decision_contracts.py` | 36 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Exchange envelope validation. | `import`: runtime (module), runtime×30; `runtime`: Draft202012Validator, _object×3, composition_lookup_schema×2 |
| `decision_delivery.py` | 82 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. The model call (Launch's copy of `task_decision.call`, freezes literature numerical contracts). | `import`: runtime (module), runtime×30; `runtime`: DECISION_EXCHANGE_PROTOCOL×5, WorkflowError×5, _ASSIGNMENT_TRANSPORT, _action_generation_schema, _digest, _json×4, _recorded_assignment_transport, instructional_model_context, json×2; `self.workflow`: contract_information_profile, decision_exchanges, decision_protocol×3, freeze_contract_information, freeze_literature_numerical_contracts, history_preview, is_job_source×2, journal, numerical_contracts, provider, receipts×4, services, uses_received_record_context×2, validate_contract_information×2; `table`: runtime_model_calls×5 |
| `decision_exchange.py` | 116 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Lookup exchange loop. | `import`: runtime (module), runtime×30; `name`: composition_information; `runtime`: DECISION_CONTEXT_VERSION, Mapping×3, ValidationError×4, _action_generation_schema, _category_yield_parameters, _json×2, _plain×2, _references_in, child_option_information, instructional_model_context×2, lookup_attempts, model_snapshot, requested_contract_information, schema_failure_diagnostic×2, sqlite3, state_frame, yield_table; `self.workflow`: controller_binding, decision_exchanges, execute, journal, run_id, services, store×2, validate_contract_information; `table`: runtime_model_calls×2 |
| `decision_inputs.py` | 70 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Expectations keyed by role `launch`. | `import`: episode_work_report×2, library.hpc_prompt, runtime (module), runtime×30; `runtime`: Mapping, child_option_information; `self.workflow`: available_child_roles, binding_context×2, episode_bindings, execution_expectations, is_job_source, job_episodes×4, launch_instructions×2, native_estimation_context, native_event_information×2, pending_work, permits_common_action, resource_context, resource_estimator×5, shared_information_context, store×2, waiting_support |
| `decision_presentation.py` | 59 | Launch prompt presentation (`present_launch_task`, run by the provider): keeps per-(episode, role) prompt state across decision frames and renders HPC, published-scientific, API-launch, selected-execution, monitor or receiver prompts; otherwise JSON context. | `import`: gene_context_evidence_prompt×2, library.hpc_prompt×2, library.monitor_prompt×2, native_profile_presentation, providers (module), providers×10, receiver_prompt; `providers`: DECISION_CONTEXT_VERSION, _ordinary_runtime_receiver_context, apply_state_frame×3, deepcopy, is_api_launch_context×2, is_published_scientific_context×2, json, render_api_launch_prompt, render_gene_context_evidence_prompt, text_instructions; `self(=old Workflow)`: scientific_prompt_states×4 |
| `decision_provider.py` | 18 | Provider dispatch: always `complete_with_presentation` with `present_launch_task` when available. | `import`: runtime×30; `self.workflow`: provider×2, specialist |
| `decision_state.py` | 45 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Same model view as Results. | `import`: runtime (module), runtime×6; `runtime`: FACT_MEANINGS, FACT_SOURCES, Mapping×3, _plain×2, _references_in, json×2; `self.workflow`: binding_context, catalog, controller_binding, delivery_status, extra_report_sources, is_scientific_source, job_episode_options, journal×3, knowledge, local_outcome_preview, pending_work, receipt_projection, run_id, source_credit_binding, source_credit_view, specialist, store×3, tools, working_state; `table`: runtime_actions×2; `view`: child_reports×2, controller_state, model_inputs |
| `episode.py` | 34 | The binding: path, commissioning parent `.../hpc_allocation_execution`, role `launch`, no entry roles, decision source `LaunchTask`, renderer `present_launch_task`, `replaces_default_instructions`; mixes in `A103HomologyExecution`. | none |
| `from_child_api_job_execution.py` | 44 | Admit the API child's typed report: recorded-admission reuse; progress forms (counterpart/receiver hook); referenced records + binding-received references; native timing receipts saved on the report attempt; receipts received as `child_form`/`report_redelivery`; tool attributions. | `import`: delivery_counterpart, episode_return_records, runtime (module), runtime×4; `runtime`: WorkflowError, _json, _references_in, json; `self(=old Workflow)`: binding_context×4, episode_bindings, is_job_source×2, job_episodes×2, native_timing_information, progress_provider×4, receipts×3, receive_tool_attributions, run_id×6, specialist, store×7; `table`: runtime_report_attempts×2 |
| `from_child_hpc_job_execution.py` | 44 | Same admission for the HPC child (identical body). | `import`: delivery_counterpart, episode_return_records, runtime (module), runtime×4; `runtime`: WorkflowError, _json, _references_in, json; `self(=old Workflow)`: binding_context×4, episode_bindings, is_job_source×2, job_episodes×2, native_timing_information, progress_provider×4, receipts×3, receive_tool_attributions, run_id×6, specialist, store×7; `table`: runtime_report_attempts×2 |
| `from_child_local_job_execution.py` | 44 | Same admission for the local child (identical body). | `import`: delivery_counterpart, episode_return_records, runtime (module), runtime×4; `runtime`: WorkflowError, _json, _references_in, json; `self(=old Workflow)`: binding_context×4, episode_bindings, is_job_source×2, job_episodes×2, native_timing_information, progress_provider×4, receipts×3, receive_tool_attributions, run_id×6, specialist, store×7; `table`: runtime_report_attempts×2 |
| `from_parent.py` | 125 | Assignment form and admission (see "What it reads"); `required_return_sources` = `execution_handoff_refs` under `gene_context_evidence` with an annotation task; initial references. | `BindingContext`: assignment×2, path, role×5; `import`: hpc_launch_authentication, native_blast_database_result_publication×2, native_blast_standard_database_result_publication×2; `services`: annotation_task_required |
| `goal.py` | 7 | Goal text (quoted). | none |
| `instructions.py` | 22 | Instruction composition: goal + `REASONING_COMMIT_REQUIREMENT` when `reason` is permitted + tool knowledge + launch library + repair/wait/native-event texts; exchange-history swap. | `import`: runtime_prompt (module), runtime_prompt×4; `runtime_prompt`: DECISION_EXCHANGE_PROTOCOL, INSTRUCTIONS×3, REASONING_COMMIT_REQUIREMENT; `self.workflow`: binding_context, decision_protocol, knowledge, launch_instructions, native_event_information, permits_common_action×3, specialist |
| `internal_summary.py` | 123 | Initial decision context (resource capabilities, inventory, received BV-BRC/BLAST/MinHash), decision context (`execution_assignment`, `execution_progress`, `selected_execution_task`), capabilities, resource tool contracts. | `BindingContext`: assignment×2, role×3; `import`: native_profile_presentation; `services`: scientific_parent_task |
| `operations.py` | 50 | Initialisation (validate launch request map, BLAST-grader launch requirements, masking/utility inputs, immutable input versions) and the single tool `execution.capabilities` (masking/utility result catalogs for those retained targets). | `BindingContext`: assignment×5, role, scope×3; `import`: native_blast_masking_results, native_blast_utility_results, native_file_capture |
| `received_information.py` | 113 | Receiving-context fact sources/facts for `annotation`/`gene_context_evidence` parents (same as Results' `received_report_facts`). | `BindingContext`: request×2, role×11; `import`: blast_pairwise_result_views, blast_utility_result_views, bvbrc_data_views, bvbrc_minhash_views, hmmer_preparation_result_views, native_blast_database_result_views, native_blast_standard_database_result_views, sequence_masking_result_views, uniprot_return_contracts |
| `received_record_selection.py` | 35 | Which received references are handoffs/results for this context (same rule as Results). | `BindingContext`: assignment, role, scope×2 |
| `received_reference_custody.py` | 160 | Receiving-context reference access and typed report admission (same as Results). | `BindingContext`: role×10; `import`: bvbrc_homology_returns, hmmer_native_result_views |
| `report_delivery.py` | 25 | Old-runner closure (same as Results). | `import`: library.private_policy_call, library.report_fact_assembly, runtime (module), runtime×4; `runtime`: Record×2, _json×2, form_with_facts, json; `self.workflow`: binding_context, episode_bindings, facts, journal×2, pending_handles, release×2, source_credit_view; `table`: runtime_forms×2 |
| `report_reference_access.py` | 115 | Outgoing report reference resolution (same as Results). | `BindingContext`: role×12, scope×4; `import`: bvbrc_data_views, bvbrc_homology_returns, episode_bindings×2, hmmer_preparation_result_views, native_blast_database_results, native_blast_standard_database_results |
| `result_records.py` | 260 | Result/selector/target helpers carried with Launch (masking/utility readers, input versions, target, selector, result directory, windows, saved result validation, receiver selection, context target, AppService/UniProt presence). | `BindingContext`: assignment×4, episode_id×9, role×3, run_id×2, scope×7; `import`: blast_pairwise_result_views, blast_utility_result_views×2, bvbrc_homology_returns, episode_receipts, execution_input_versions, hmmer_native_result_views, hmmer_preparation_result_views, native_blast_database_result_views, native_blast_standard_database_result_views, sequence_masking_result_views×2; `services`: record_selection; `table`: runtime_actions×2, runtime_episodes, runtime_receipt_inheritance×2 |
| `saved_decision_exchange.py` | 82 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Saved exchange authentication. | `import`: runtime (module), runtime×30; `name`: composition_information; `runtime`: CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION, ValidationError, WorkflowError×9, _json×8, _recorded_action_generation_schema, apply_state_frame, instructional_model_context, is_contract_information, json, model_snapshot, requested_contract_information; `self.workflow`: contract_information_reply, decision_exchanges×2, journal, validate_contract_information×2; `table`: runtime_model_calls |
| `task.py` | 235 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Launch differences: validates `reason` selections against the reasoning envelope and refuses an empty reasoning commit (unless the binding says it has task content or it is a `no_applicable_evidence` finding); report grain `launch`; carries `validate_hpc_launch_report_contract`. | `import`: episode_source_failure, library.action_contracts, library.hpc_handoff_report_contract, library.private_policy_call, providers, read_mapping, runtime (module), runtime×27; `runtime`: AcquisitionError×2, ActionFailure, ContractError×2, ContractInformationError, Draft202012Validator×3, EventTargetError×2, Mapping×9, ReportBoundaryError, ReportRedelivery×2, SourceEnd×2, ValidationError×3, WorkflowError×2, _decode_recorded_action_response, _json×5, _plain, _wait_target_feedback×2, inspect, json×8, nullcontext×5, observes_action_outcome, schema_failure_diagnostic, sqlite3×2, subprocess×2, validate_form; `self.workflow`: action_schema, automatic_score_updates, binding_context×2, completed_unit×3, completions×3, controller_value×2, decision_exchanges×3, delivery_resolution_inputs, execute, execution_binding×7, inprocess_replay×4, journal×7, last_observed_credit, next_return, pending_work, perform_selected_wait, permits_common_action, reasoning_action_schema, receive_native_outcome, receive_outcome, resolve_pending_deliveries, resolver, retain_shared_grading_results, run_id×3, selected×3, source_credit_view, specialist×2, store×9, validate_report; `table`: runtime_actions×8, runtime_episodes, runtime_model_calls×2; `view`: units_consumed×4 |
| `task_state.py` | 108 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. | `import`: episode_source_failure, runtime (module), runtime×9; `runtime`: ActionLeaf, EFFECT_VERSION, Episode, Record, _json×2, _object, _plain, interpretation_schema, json×4; `self.workflow`: archive, completions×4, controller_value, execution_binding×4, inprocess_replay×7, journal×5, progress_provider×2, recover_commissions, run_id, source_credit_view, store×2; `table`: runtime_actions×5 |
| `terminal_execution.py` | 185 | Instruction-led local/HPC terminal behaviour (`exec_command`, receipts, completion proof) used by the resource children; in-folder copy imported by `contracts.py`. | `BindingContext`: assignment×9, episode_id×4, role, run_id×5; `import`: acquisition, communication×2, domain, practical_execution_operations, practical_execution_records×3, practical_execution_state, practical_receipt_information×3, practical_yield, terminal_execution×2, terminal_scientific_evidence×2; `services`: workflow; `yield`: PracticalYieldEstimator |
| `to_child_api_job_execution.py` | 28 | Build the API child's `EpisodeRequest`: child goal of the parent goal with the contract schema; message `scope`, `initial_report`, optional in-process completion order, report contract declaration (validated saved-fact form), `job_assignment`, `episode_assignment` (launch instructions materialised), `gene_context_evidence`, `knowledge_inheritance` receipts binding. | `import`: runtime (module); `runtime`: ContractInformationError, EpisodeGoal×2, EpisodeRequest, Episode×2, Record, _plain×3, validate_saved_fact_form; `self(=old Workflow)`: context×2, grains×2, inprocess_completion_order×2, launch_instructions, legacy_parent_for_path, receipts×2 |
| `to_child_hpc_job_execution.py` | 28 | Same request assembly for the HPC child (identical body). | `import`: runtime (module); `runtime`: ContractInformationError, EpisodeGoal×2, EpisodeRequest, Episode×2, Record, _plain×3, validate_saved_fact_form; `self(=old Workflow)`: context×2, grains×2, inprocess_completion_order×2, launch_instructions, legacy_parent_for_path, receipts×2 |
| `to_child_local_job_execution.py` | 28 | Same request assembly for the local child (identical body). | `import`: runtime (module); `runtime`: ContractInformationError, EpisodeGoal×2, EpisodeRequest, Episode×2, Record, _plain×3, validate_saved_fact_form; `self(=old Workflow)`: context×2, grains×2, inprocess_completion_order×2, launch_instructions, legacy_parent_for_path, receipts×2 |
| `to_parent.py` | 122 | Fact sources and facts for role `launch`: `execution_handoff_refs`, `execution_result_refs`, `execution_completed` (= any received handoff is returnable), `execution_result_origin`, `execution_blast_hsps`, family facts; result-only sources (file sources, UniProt, BLAST grader) only for role `results`; report validation against recorded facts. | `BindingContext`: scope; `import`: blast_pairwise_result_views×2, blast_result_views, blast_utility_result_views×2, bvbrc_data_views, bvbrc_minhash_views, hmmer_native_result_views×2, hmmer_preparation_result_views×2, local_file_capture_results×2, native_blast_database_result_views, native_blast_database_results, native_blast_standard_database_result_views, native_blast_standard_database_results, native_hmmer_acquisition, sequence_masking_result_views×2, uniprot_return_contracts×2 |
| `waiting.py` | 9 | Wait suspension to the execution backend. | `self.workflow`: execution_backend, execution_handle×2 |
| `yield_estimator.py` | 68 | Continuation (see "Continuation"). | `BindingContext`: assignment, role, scope; `import`: numerical×5, practical_yield; `yield`: BoundedYieldController, NumericBand, PracticalYieldEstimator, YieldController, YieldEstimate, YieldParameters×2, estimate_with_context |
