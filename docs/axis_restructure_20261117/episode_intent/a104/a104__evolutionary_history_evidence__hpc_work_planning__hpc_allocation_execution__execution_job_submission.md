# a104 / evolutionary_history_evidence / hpc_work_planning / hpc_allocation_execution / execution_job_submission

Source: the episode's own files at commit `97308b94c`
(`git show HEAD:gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/<file>`).
The folder has no `grading/`, `scoring/` or `tests/` subfolder. The child folders (`api_job_execution`, `hpc_job_execution`,
`local_job_execution`) are documented separately. Old binding class: `ExecutionEpisode` (Launch). Decision source: `LaunchTask`, with
`child_return_form_policy = HPC_HANDOFF_RETURN_POLICY`. Prompt renderer: `present_execution_context`. Commissioning parent:
`evolutionary_history_evidence/hpc_work_planning/hpc_allocation_execution`.

## Purpose (goal, in its own words)

Role `launch`. It is not an entry role, and it replaces the default instructions. From `goal.py`:

> Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, recorded
> inventory and timing information inform the choice. Preserve the original job, immutable inputs, constraints and
> pinned instructions. A resource child owns iterative execution in the shared loop. Receive its requested typed
> handoff; no infrastructure chooses an approach. Actual received usable handoff completes this launch endpoint with
> exact zero future credit.

## Task and instructions

`task_instructions.instructions` is the same composition as Results' `instructions.py`. The goal replaces the A-root `INSTRUCTIONS`. It
then appends:
- `REASONING_COMMIT_REQUIREMENT`, when reason is permitted;
- the tool knowledge and the launch-instruction library;
- the repair text;
- the wait text and the native-event text, when they apply.

Under `decision_exchange_v1`, the history paragraph is substituted.

`task_action.apply_response` differs from Results:
- a `reason` selection is validated against `workflow.reasoning_action_schema` and the store's reasoning schema;
- an all-empty commit is rejected (`empty_reasoning_commit`) unless `evidence_processing.kind == 'no_applicable_evidence'` or the binding
  says it has task content;
- report admission uses grain `launch`.

## What it reads from its parent's assignment

The assignment is `execution_launch_assignment_v1` (`from_parent.assignment_schema`). It has these fields:
- `requests`: a map from resource id to a launch request schema per resource, with at least one entry;
- `immutable_input_versions`;
- `constraints`;
- `launch_instructions`: a selection from the launch-instruction library.

`prepare_assignment` checks the schema. Under an `hpc` or `hpc_execution` parent, it calls the HPC parent's `authenticate_launch`: the
assignment must equal exactly one frozen plan's launch assignment, and that plan's allocation slot is reserved. It then validates:
- each request (BLAST graded requests must use an `ncbi_blast` resource; API requests go through `api_execution.validate_assignment`);
- the constraints;
- the masking and utility inputs;
- the input versions;
- the native and standard BLAST database job inputs.

## Children

The children are `launch_api`, `launch_local` and `launch_hpc`. `allowed_children` offers only the kinds that have a configured resource
permitted by the assignment.
- Sent: the old `assemble_request` per child (`to_child_*_job_execution.py`, identical apart from the docstring). There is no
  episode-specific preparation in these files. The child's assignment is the selected request.
- Taken back: the old common child-form receipt (`from_child_*_job_execution.receive_report`, identical across all three). The handoff
  references then count through `received_records._received` as usable handoffs (`targets.usable_handoff`).

## Decision state and what the model sees

The common decision state (`decision_context.py`) applies. The episode's own `internal_summary.decision_context` adds:
- `execution_assignment`;
- `execution_progress`, the current facts;
- `selected_execution_task`: scientific question and selected tool info from `services.scientific_parent_task`, the requests with
  resource information, constraints and selector.

`resource_information.initial_decision_context` adds the execution resource capabilities and the initial information. Under an HPC
parent, the HPC parent's `LaunchPreparation.initial_decision_context` supplies `hpc_execution_job` for launch children.

## Tools

The only tool is `execution.capabilities` (`capability_operations`). It returns the caller-bound resource configuration and the recorded
inventory, with no discovery or selection.

The common actions are tool, child and redeliver_report when any path element is `hpc` (inside the HPC allocation). Otherwise they are tool,
reason, child, wait and redeliver_report.

## Credit

The credit kind is `operational`. The closed view is frozen as in Results (`closed_credit`). The live credit is `handoff_unit × |resource
ids with a usable received handoff that were not already in the initial refs|`. The acquired fraction is fixed at 0. Binding
`execution_received_records_credit_v1`. Credit is not bounded.

## Continuation

The private yield applies only when `require_private_yield` (`yield_estimator._launch_yield_controller`):
- `eligible` = the requests permitted for their resource;
- `remaining = |eligible − resources already having an initial usable handoff| × handoff_unit`;
- when `remaining > 0`: profile `task_yield_profiles['launch:' + '+'.join(sorted request classes)]`, where the classes come from
  `_request_yield_class` (for example `practical_hpc_native_blast_handoff` or `api_<service>_<algorithm>_<database>_handoff`). It uses an
  old `BoundedYieldController(epoch, initial_credit, cutoff, remaining, parameters)`;
- otherwise an exact-zero estimator; nonzero initial or later credit raises.

`practical_estimator` / `verify_completion` use the completion proof: an own completed action that received a usable handoff, endpoint
`usable_handoff`.

Current-runner closest: **completion with a target**, where the target is the remaining eligible handoffs × handoff_unit, and a received
handoff completes the endpoint with exact zero future credit. Settings: `cutoff` and `parameters`.

## Report to parent

`report_facts.facts` supplies:
- `execution_handoff_refs`;
- `execution_result_refs` (windows only);
- `execution_file_source_refs`;
- `execution_file_capture_outcomes` (always empty here);
- `execution_result_origin`;
- `execution_completed` (any returnable handoff);
- `execution_blast_hsps`;
- `bvbrc_appservice_support_refs`;
- empty native family sources;
- the closed credit facts.

`required_return_sources` is `execution_handoff_refs` under an annotation-task parent. The HPC parent reads `execution_handoff_refs` through
`hpc_launch_report_form`. `to_parent.validate_report` checks masking and utility received reports and UniProt frozen facts, and requires
recorded facts to match.

## Differences from similar episodes

- Compared with Results (`hpc_work_planning/execution_result_acquisition`): the configuration operands are the same; `protected_reference_access`
  and `terminal_validation` are identical; `contracts.py` consolidates the constants Results splits across files. Launch's credit counts
  handoffs, not bytes; its yield is bounded remaining handoffs; it has resource children and only the `execution.capabilities` tool.
- The HPC-allocation-specific parts visible in this episode's own files: `authenticate_launch` in `from_parent`, the HPC handoff
  return-form policy in `task.py`, the reduced common actions under an `hpc` path, and the configuration's progress provider naming the
  sibling `hpc_allocation_execution/execution_result_acquisition` as native result owner. I did not compare against other axes'
  `execution_job_submission` copies here.

## Files

Old-runner names are listed as `name×uses`. `workflow.*` means `self.workflow.*` / `source.workflow.*` / `workflow.*`. `BindingContext .x` means the old binding-context attribute `context.x` / `parent.x`. `table x` is a journal or receipt table named in SQL or in `journal.row/save`. The full per-use list is in `runs/carry_over/calls/a104_04.tsv`.

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | Empty package marker. | none |
| `binding_record.py` | 8 | Binding record `execution_episode_v1` (same operands as Results). | none |
| `capability_operations.py` | 19 | Tool `execution.capabilities`: returns the initial decision context (caller-bound resource configuration and recorded inventory). | root.a104.native_file_capture×1 |
| `closed_credit.py` | 117 | Closed operational credit freezing (same rule as Results, without the Results-only branches). | BindingContext .as_record×2; BindingContext .episode_id×8; BindingContext .role×1; root.a104.episode_receipts×1; root.a104.episode_return_records×3; EpisodeReceipts×2; EpisodeReturnRecords×2; table runtime_episodes×2; table runtime_forms×3; table runtime_observations×1; table runtime_receipt_inheritance×2; table runtime_record_receipts×2; table sqlite_master×2 |
| `completion.py` | 72 | Completion proof: an own completed action whose record_refs include a usable handoff of this assignment (endpoint `usable_handoff`); recorded endpoint verdict reuse. | BindingContext .assignment×2; BindingContext .episode_id×7; BindingContext .run_id×3; BindingContext .scope×1; root.a104.episode_return_records×1; root.a104.method_loop.identities×1; root.a104.numerical×1; root.a104.practical_yield×1; UnitRef×2; table runtime_actions×1; table runtime_observations×1; ESTIMATOR_VERSION×2; NumericBand×2 |
| `configuration.py` | 65 | Same construction operands as Results; API side uses APIRecordAccess; progress provider's native_result_owner is `.../hpc_allocation_execution/execution_result_acquisition`. | root.a104.bvbrc_phylogeny_returns×1; root.a104.evolutionary_history_evidence.* (absolute own-tree path)×1; root.a104.execution_progress×1; root.a104.library.api_record_access×1; root.a104.numerical×1; YieldController×3; YieldParameters×3 |
| `contracts.py` | 59 | Consolidated constants and imports: versions, ROLES/KINDS/ROLE_KINDS, schemas, NATIVE_RESULT_ORIGIN, launch and native result catalogs, _outcome. | root.a104.a104_execution_bindings×1; root.a104.a104_homology_execution×1; root.a104.communication×1; root.a104.domain×1; root.a104.evolutionary_history_evidence.* (absolute own-tree path)×1; root.a104.execution_contracts×1; root.a104.launch_instructions×1; root.a104.local_file_capture_results×1; root.a104.native_blast_acquisition×1; root.a104.native_blast_database_acquisition×1; root.a104.native_blast_masking_acquisition×1; root.a104.native_blast_standard_database_acquisition×1; root.a104.native_blast_utility_acquisition×1; root.a104.native_hmmer_acquisition×1; root.a104.native_hmmer_preparation_acquisition×1; root.a104.practical_execution_operations×1; root.a104.practical_execution_records×1; root.a104.practical_execution_state×1; root.a104.practical_receipt_information×1; root.a104.resource_records×1 |
| `credit.py` | 38 | Operational credit = handoff_unit x number of new resource ids with usable handoffs (not in initial refs); acquired fraction fixed at 0. | none |
| `decision_context.py` | 54 | Decision context assembly. Old-runner machinery. | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; bind_functions×2; _bind_preserved_runtime_providers×2; SourceEnd×1; view.child_reports×2; view.controller_state×1; view.model_inputs×1; WorkflowError×1; table runtime_actions×2; workflow.binding_context×1; workflow.catalog×1; workflow.controller_binding×1; workflow.delivery_status×1; workflow.extra_report_sources×1; workflow.is_scientific_source×1; workflow.job_episode_options×1; workflow.journal×3; workflow.knowledge×1; workflow.local_outcome_preview×1; workflow.pending_work×1; workflow.receipt_projection×1; workflow.run_id×1; workflow.source_credit_binding×1; workflow.source_credit_view×1; workflow.specialist×1; workflow.store×3; workflow.tools×1; workflow.working_state×1 |
| `decision_contracts.py` | 133 | Decision-exchange envelope. Old-runner machinery. | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; bind_functions×2; _bind_preserved_runtime_providers×2; WorkflowError×10; table runtime_model_calls×1; workflow.contract_information_reply×1; workflow.decision_exchanges×2; workflow.journal×1; workflow.store×2; workflow.validate_contract_information×2; _category_yield_parameters×1; yield_table×1 |
| `decision_exchange.py` | 113 | request_context loop. Old-runner machinery. | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; bind_functions×2; _bind_preserved_runtime_providers×2; WorkflowError×1; table runtime_model_calls×2; workflow.controller_binding×1; workflow.decision_exchanges×1; workflow.execute×1; workflow.journal×1; workflow.run_id×1; workflow.services×1; workflow.validate_contract_information×1; _category_yield_parameters×2; yield_table×2 |
| `decision_provider.py` | 60 | Presentation-provider selection. Old-runner machinery. | root.a104.providers×2; root.a104.runtime×1; import root.providers×1; WorkflowError×1; workflow.provider×1; workflow.specialist×2; _category_yield_parameters×1; yield_table×1 |
| `episode.py` | 79 | ExecutionEpisode composition: role `launch`, children launch_api/launch_local/launch_hpc (only kinds with a permitted resource), common actions tool/child/redeliver_report under an hpc path else tool/reason/child/wait/redeliver_report; required return source execution_handoff_refs under an annotation parent. | BindingContext .assignment×1; BindingContext .path×2; BindingContext .role×1; self.services.annotation_task_required (getattr)×1 |
| `from_child_api_job_execution.py` | 44 | Old child-form receipt/progress admission for launch_api. | root.a104.delivery_counterpart×1; root.a104.episode_return_records×1; root.a104.runtime×1; EpisodeReturnRecords×2; WorkflowError×2; table runtime_report_attempts×2; workflow.binding_context×4; workflow.episode_bindings×1; workflow.is_job_source×2; workflow.job_episodes×2; workflow.native_timing_information×1; workflow.progress_provider×4; workflow.receipts×3; workflow.receive_tool_attributions×1; workflow.run_id×6; workflow.specialist×1; workflow.store×7 |
| `from_child_hpc_job_execution.py` | 44 | Old child-form receipt/progress admission for launch_hpc. | root.a104.delivery_counterpart×1; root.a104.episode_return_records×1; root.a104.runtime×1; EpisodeReturnRecords×2; WorkflowError×2; table runtime_report_attempts×2; workflow.binding_context×4; workflow.episode_bindings×1; workflow.is_job_source×2; workflow.job_episodes×2; workflow.native_timing_information×1; workflow.progress_provider×4; workflow.receipts×3; workflow.receive_tool_attributions×1; workflow.run_id×6; workflow.specialist×1; workflow.store×7 |
| `from_child_local_job_execution.py` | 44 | Old child-form receipt/progress admission for launch_local. | root.a104.delivery_counterpart×1; root.a104.episode_return_records×1; root.a104.runtime×1; EpisodeReturnRecords×2; WorkflowError×2; table runtime_report_attempts×2; workflow.binding_context×4; workflow.episode_bindings×1; workflow.is_job_source×2; workflow.job_episodes×2; workflow.native_timing_information×1; workflow.progress_provider×4; workflow.receipts×3; workflow.receive_tool_attributions×1; workflow.run_id×6; workflow.specialist×1; workflow.store×7 |
| `from_parent.py` | 47 | Assignment `execution_launch_assignment_v1`: requests per resource id, immutable_input_versions, constraints, launch_instructions; under an hpc/hpc_execution parent authenticate_launch must match the planned portfolio; validates requests, masking/utility inputs, versions, BLAST database job inputs. | BindingContext .role×2; root.a104.evolutionary_history_evidence.* (absolute own-tree path)×1; root.a104.native_blast_database_result_publication×1; root.a104.native_blast_standard_database_result_publication×1 |
| `goal.py` | 7 | Goal text (see Purpose). | none |
| `internal_summary.py` | 43 | decision_context: execution_assignment, execution_progress, selected_execution_task. | BindingContext .assignment×2; root.a104.native_profile_presentation×1; self.services.scientific_parent_task (getattr)×1 |
| `launch_state.py` | 15 | initialize(): validate the launch, BLAST graded request requirement, inputs and versions. | BindingContext .assignment×1; BindingContext .scope×3 |
| `native_receipt_support.py` | 13 | Delegate to the practical behaviour of the request's resource. | BindingContext .assignment×1; BindingContext .role×1 |
| `presentation.py` | 60 | Text-task prompt rendering. Provider machinery. | root.a104.evolutionary_history_evidence_prompt×2; root.a104.library.hpc_prompt×1; root.a104.library.monitor_prompt×1; root.a104.native_profile_presentation×1; root.a104.providers×1; root.a104.receiver_prompt×1 |
| `protected_reference_access.py` | 100 | Protected read authority (identical to Results). | BindingContext .assignment×4; root.a104.communication×1; root.a104.library.fluorescence_returns×1; root.a104.library.native_fluorescence_results×1; root.a104.library.native_protein_structure_results×1; root.a104.library.native_protein_structure_returns×1; root.a104.library.protein_structure_operands×1 |
| `received_records.py` | 57 | Known/initial record selection and received handoffs/results. | BindingContext .assignment×1; BindingContext .episode_id×7; BindingContext .role×1; BindingContext .scope×2; root.a104.episode_receipts×1; EpisodeReceipts×2; self.services.record_selection (getattr)×1; table runtime_actions×1; table runtime_receipt_inheritance×2; table sqlite_master×1 |
| `received_reference_access.py` | 81 | Reference access for received records. | BindingContext .role×9; root.a104.bvbrc_homology_returns×1; root.a104.bvbrc_phylogeny_returns×1; root.a104.library.bvbrc_proteome_returns×1 |
| `received_report_admission.py` | 93 | Validate received reports and collect form references. | BindingContext .role×1; root.a104.hmmer_native_result_views×1 |
| `received_reports.py` | 113 | Report sources forwarded to annotation receivers; closure facts; initial_references. | BindingContext .assignment×2; BindingContext .request×2; BindingContext .role×13; root.a104.blast_pairwise_result_views×1; root.a104.blast_utility_result_views×1; root.a104.bvbrc_data_views×1; root.a104.hmmer_preparation_result_views×1; root.a104.native_blast_database_result_publication×1; root.a104.native_blast_database_result_views×1; root.a104.native_blast_standard_database_result_publication×1; root.a104.native_blast_standard_database_result_views×1; root.a104.sequence_masking_result_views×1; root.a104.uniprot_return_contracts×1 |
| `report_delivery.py` | 32 | finish(). Old-runner machinery. | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; bind_functions×2; _bind_preserved_runtime_providers×2; form_with_facts×2; Record×3; table runtime_forms×2; workflow.binding_context×1; workflow.episode_bindings×1; workflow.facts×1; workflow.journal×2; workflow.pending_handles×1; workflow.release×2; workflow.source_credit_view×1 |
| `report_facts.py` | 35 | Report facts: execution_handoff_refs, execution_result_refs, file sources, result origin, completed (any returnable handoff), native empty families, closed credit facts. | BindingContext .scope×1; root.a104.blast_pairwise_result_views×1; root.a104.blast_utility_result_views×1; root.a104.hmmer_native_result_views×1; root.a104.hmmer_preparation_result_views×1; root.a104.library.native_blast_database_result_records×1; root.a104.library.native_blast_standard_database_result_records×1; root.a104.sequence_masking_result_views×1 |
| `report_fields.py` | 51 | fact_sources. | root.a104.blast_pairwise_result_views×1; root.a104.blast_result_views×1; root.a104.blast_utility_result_views×1; root.a104.bvbrc_data_views×1; root.a104.hmmer_native_result_views×1; root.a104.hmmer_preparation_result_views×1; root.a104.local_file_capture_results×1; root.a104.native_blast_database_result_views×1; root.a104.native_blast_standard_database_result_views×1; root.a104.native_hmmer_acquisition×1; root.a104.sequence_masking_result_views×1; root.a104.uniprot_return_contracts×1 |
| `report_reference_access.py` | 129 | resolve(). | BindingContext .role×13; BindingContext .scope×4; root.a104.bvbrc_data_views×1; root.a104.bvbrc_homology_returns×1; root.a104.bvbrc_phylogeny_returns×1; root.a104.episode_bindings×2; root.a104.hmmer_preparation_result_views×1; root.a104.library.bvbrc_proteome_returns×1; root.a104.library.native_blast_database_result_records×1; root.a104.library.native_blast_standard_database_result_records×1 |
| `request_validation.py` | 53 | Request schema per resource, request validation, constraints, permitted resource, input versions. | root.a104.library.execution_input_versions×1 |
| `resource_information.py` | 88 | Resource information, initial_decision_context, capabilities, resource tool contracts. | BindingContext .role×1; root.a104.library.bvbrc_proteome_tool_info×1 |
| `resource_return_support.py` | 20 | AppService/UniProt presence, AppService fact sources, BV-BRC forwarding rule. | root.a104.bvbrc_homology_returns×1; root.a104.bvbrc_phylogeny_returns×1; root.a104.library.bvbrc_proteome_returns×1 |
| `retained_result_receipts.py` | 171 | Target/selector/result directory/windows/result body reads (Results helpers needed for receipt checks). | BindingContext .assignment×4; BindingContext .episode_id×2; BindingContext .role×3; BindingContext .run_id×2; BindingContext .scope×7; root.a104.blast_pairwise_result_views×1; root.a104.blast_utility_result_views×1; root.a104.hmmer_native_result_views×1; root.a104.hmmer_preparation_result_views×1; root.a104.native_blast_database_result_views×1; root.a104.native_blast_standard_database_result_views×1; root.a104.sequence_masking_result_views×1; table runtime_actions×1; table runtime_episodes×1 |
| `scientific_inputs.py` | 54 | Masking/utility selectors, inputs, retained targets and reference access. | root.a104.blast_utility_result_views×1; root.a104.sequence_masking_result_views×1 |
| `task.py` | 100 | LaunchTask.next() with HPC handoff return-form policy. Old-runner machinery. | import root.a104×1; root.a104.episode_source_failure×1; root.a104.library.hpc_handoff_return_form×1; root.a104.library.live_runtime_functions×1; root.a104.providers×1; root.a104.runtime×1; bind_functions×2; _bind_preserved_runtime_providers×2; SourceEnd×3; view.units_consumed×4; WorkflowError×2; table runtime_actions×2; table runtime_episodes×1; table runtime_model_calls×1; workflow.action_schema×1; workflow.completed_unit×3; workflow.completions×2; workflow.delivery_resolution_inputs×1; workflow.execution_binding×2; workflow.inprocess_replay×4; workflow.journal×4; workflow.next_return×1; workflow.resolve_pending_deliveries×1; workflow.run_id×1; workflow.selected×2; workflow.store×3 |
| `task_action.py` | 159 | apply_response/execute: reason commits validated against the reasoning schema and an empty commit rejected unless the binding says it has task content; grain `launch`. | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.read_mapping×1; root.a104.runtime×1; ActionFailure×2; bind_functions×2; _bind_preserved_runtime_providers×2; ReportRedelivery×3; WorkflowError×2; table runtime_actions×6; table runtime_model_calls×1; workflow.automatic_score_updates×1; workflow.binding_context×2; workflow.completions×1; workflow.controller_value×2; workflow.decision_exchanges×3; workflow.execute×1; workflow.execution_binding×5; workflow.journal×3; workflow.last_observed_credit×1; workflow.pending_work×1; workflow.perform_selected_wait×1; workflow.permits_common_action×1; workflow.reasoning_action_schema×1; workflow.receive_native_outcome×1; workflow.receive_outcome×1; workflow.resolver×1; workflow.retain_shared_grading_results×1; workflow.run_id×2; workflow.selected×1; workflow.source_credit_view×1; workflow.specialist×2; workflow.store×6; workflow.validate_report×1 |
| `task_decision.py` | 154 | Decision call and inputs. Old-runner machinery. | import root.a104×1; root.a104.episode_work_report×2; root.a104.library.hpc_prompt×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; bind_functions×2; _bind_preserved_runtime_providers×2; WorkflowError×6; table runtime_model_calls×5; workflow.available_child_roles×1; workflow.binding_context×2; workflow.contract_information_profile×1; workflow.decision_exchanges×1; workflow.decision_protocol×3; workflow.episode_bindings×1; workflow.execution_expectations×1; workflow.freeze_contract_information×1; workflow.freeze_literature_numerical_contracts×1; workflow.history_preview×1; workflow.is_job_source×3; workflow.job_episodes×4; workflow.journal×1; workflow.launch_instructions×2; workflow.native_estimation_context×1; workflow.native_event_information×2; workflow.numerical_contracts×1; workflow.pending_work×1; workflow.permits_common_action×1; workflow.provider×2; workflow.receipts×4; workflow.resource_context×1; workflow.resource_estimator×5; workflow.services×1; workflow.shared_information_context×1; workflow.store×2; workflow.uses_received_record_context×2; workflow.validate_contract_information×2; workflow.waiting_support×1; _category_yield_parameters×1; yield_table×1 |
| `task_instructions.py` | 35 | Instruction composition (same as Results' instructions.py). | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime_prompt×1; bind_functions×2; _bind_preserved_runtime_providers×2; workflow.binding_context×1; workflow.decision_protocol×1; workflow.is_job_source×1; workflow.job_episodes×1; workflow.knowledge×1; workflow.launch_instructions×1; workflow.native_event_information×1; workflow.permits_common_action×3; workflow.specialist×1 |
| `task_state.py` | 117 | Task state. Old-runner machinery. | import root.a104×1; root.a104.episode_source_failure×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; ActionLeaf×2; bind_functions×2; _bind_preserved_runtime_providers×2; Episode.identity×1; Record×2; table runtime_actions×5; workflow.archive×1; workflow.completions×4; workflow.context×1; workflow.controller_value×1; workflow.execution_binding×4; workflow.grains×1; workflow.inprocess_replay×7; workflow.journal×5; workflow.progress_provider×2; workflow.recover_commissions×1; workflow.run_id×1; workflow.source_credit_view×1; workflow.store×2 |
| `task_waiting.py` | 9 | suspension_changed. Old-runner machinery. | workflow.execution_backend×1; workflow.execution_handle×2 |
| `terminal_validation.py` | 67 | TerminalExecutionBehavior (identical to Results). | BindingContext .assignment×1; BindingContext .episode_id×4; BindingContext .role×1; BindingContext .run_id×3; root.a104.acquisition×1; root.a104.communication×1; root.a104.domain×1; root.a104.library.native_terminal_transport×1; root.a104.practical_execution_operations×1; root.a104.practical_execution_records×1; root.a104.practical_execution_state×1; root.a104.practical_receipt_information×1; root.a104.terminal_scientific_evidence×1 |
| `to_child_api_job_execution.py` | 30 | assemble_request only (old). | root.a104.episode_contract_information×1; root.a104.runtime×1; EpisodeGoal×3; Episode.identity×2; EpisodeRequest×2; Record×2; workflow.context×2; workflow.evolutionary_history_evidence_binding×1; workflow.grains×2; workflow.inprocess_completion_order×2; workflow.launch_instructions×1; workflow.receipts×2 |
| `to_child_hpc_job_execution.py` | 30 | assemble_request only (old). | root.a104.episode_contract_information×1; root.a104.runtime×1; EpisodeGoal×3; Episode.identity×2; EpisodeRequest×2; Record×2; workflow.context×2; workflow.evolutionary_history_evidence_binding×1; workflow.grains×2; workflow.inprocess_completion_order×2; workflow.launch_instructions×1; workflow.receipts×2 |
| `to_child_local_job_execution.py` | 30 | assemble_request only (old). | root.a104.episode_contract_information×1; root.a104.runtime×1; EpisodeGoal×3; Episode.identity×2; EpisodeRequest×2; Record×2; workflow.context×2; workflow.evolutionary_history_evidence_binding×1; workflow.grains×2; workflow.inprocess_completion_order×2; workflow.launch_instructions×1; workflow.receipts×2 |
| `to_parent.py` | 31 | validate_report: masking/utility received report checks, UniProt frozen facts, recorded facts must match. | root.a104.uniprot_return_contracts×1 |
| `yield_estimator.py` | 67 | Private yield: remaining = eligible original requests without an initial usable handoff x handoff_unit; BoundedYieldController capped by remaining with profile `launch:<sorted request classes>`; exact-zero estimator when nothing remains. | BindingContext .assignment×1; BindingContext .role×1; BindingContext .scope×1; root.a104.numerical×1; root.a104.practical_yield×1; BoundedYieldController×2; NumericBand×2; PracticalYieldEstimator×2; YieldController×2; YieldEstimate×2; YieldParameters×3 |
