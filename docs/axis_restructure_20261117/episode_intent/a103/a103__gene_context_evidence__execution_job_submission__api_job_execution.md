# a103/gene_context_evidence/execution_job_submission/api_job_execution — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/execution_job_submission/api_job_execution/<file>`,
only the 37 files directly in the folder (3013 lines). There is no `grading/` or `scoring/` subfolder, and `tests/`
was not read. Old-runner names are listed per file below and in `runs/carry_over/calls/a103_01.tsv`.

## What it is for (its goal, in its own words)

The A103 API job execution episode (role `launch_api`), commissioned only by the launch episode. It carries out one
assigned API request against one bound API resource. `goal.py`:

> "Carry out the assigned work through {service} using one selected operation each turn. Keep the original inputs,
> request, resource and parent constraints fixed. Choose useful preparation, service requests, observations or
> repair from the actual available operations and received outcomes. Distinguish an immediate returned response
> from a service job that continues remotely. Preserve the actual request or job identity and submission
> uncertainty; a missing reply does not establish that no job was created. Establish the requested usable
> monitoring/results handoff from recorded service facts. The configured controller governs continuation; verified
> original handoff completion gives exact zero future credit."

## Task and instructions

`instructions.py` has the same composition as the launch parent, without the reasoning-commit requirement. `action_policy.py`
permits only `tool`, plus `wait` for `api_service_assignment_v1` assignments. There is no reason, child or redeliver action.
`task.py` (APIJobTask, grain `launch_api`) has the launch loop shape and drops the empty-reasoning check.

## What it reads from its parent's assignment

`from_parent.py`: the assignment schema is `anyOf` the selected request schemas of the bound API resources
(resource_id required and fixed). `prepare_assignment` validates the request, re-validates it through
`api_execution.validate_assignment(…, scope)`, and requires the resource kind to be api and the parent role to be `launch`.
It also requires the selection to match the parent's original launch (`_validate_blast_launch_selection`), and validates
the masking/utility inputs, the parent's immutable input versions, and the native/standard BLAST job inputs. At
initialize/execute time, `operations._check_parent_inputs` re-reads the parent launch request from `runtime_episodes`
and re-validates it (`_validate_blast_api_parent_request`). There are no required return sources.

## Children it may commission

None (`child_eligibility.py`: no child roles, no allowed children).

## Decision state and what it shows the model

`decision_state.py` has the same field set as the launch parent. `internal_summary.py` shows execution_assignment and
execution_progress (current facts), plus whatever `api_execution.decision_context` returns. The selected execution
task comes from the single assignment, and only `ebi_hmmer` API jobs are shown in that view.
`decision_presentation.py` is this episode's own prompt (413 lines; the launch parent uses a 59-line renderer selector):
- **TASK**: scientific QUESTION (parent task or root objective), assigned job, assigned scope (subjects and regions
  named without store handles), selected API work (resource_id, service, endpoint), parent constraints,
  parent-selected tool guidance, configured resource (kind, service, base_url, availability, API configuration
  facts), the exact assigned scientific request, execution method and decision rules, each callable operation with
  its supplied instructions and arguments, selected resource instructions, information requested by the parent, the
  requested controlled JSON return, and the meanings of the requested facts.
- **STEERING**: completed action reports, pending child delivery, own action categories (completed, observed signed
  yield, expected next yield, uncertainty, uncompleted attempts), current operational continuation (turns, credit,
  expected next gain, uncertainty, continuation cost, controller decision), yield limits, original handoff completion,
  recorded own API outcomes (each complete recorded API error shown in full), latest own action, complete returned
  feedback, own pending work, and requested lookups.
- `select_profile_api_execution_values` keeps validated API operands (service, subject_ref, algorithm, database,
  parameters, page_size) literal.

## Tools it offers

`operations.py`: the API delegate's (`api_execution`) catalog for this assignment, or the masking/utility result
catalogs when those apply. Execution goes to `api_execution.execute`.

## How its credit is counted

`credit.py`: kind `operational`. The closed view comes first, then a native family's view, else `api_execution.credit_view(context, receiver_selection)`.
Completion: native family proofs, else the API delegate's `completion_for_action`. `verify_completion` falls through to
`api_execution.verify_completion`.

## Continuation (yield estimator and settings)

`yield_estimator.py`: YieldController(epoch, initial_credit, cutoff of task profile `launch_api:<request class>`,
parameters, estimate_with_context = PracticalYieldEstimator(verify_completion)). This is the completion kind: a verified
original handoff gives exact zero future credit. It needs `require_private_yield`. Request classes are as in the launch
parent (`api_<service>[_algorithm][_database]_handoff`).

## What it reports to its parent

`to_parent.py`: the same fact-source list as the launch parent. Facts are a native family's facts, or
`api_execution.facts(context, completion_snapshot)` with `execution_result_origin` = null. `validate_report` (same as
launch) checks the received report and requires x-source fields to equal the recorded facts.

## Differences from similar episodes

- Against its sibling hpc_job_execution: an own large API prompt (vs. the shared renderer selector); `tool` + optional
  `wait` (hpc: `tool` only); credit/facts/completion from `api_execution` (hpc: from the terminal practical state);
  goal names the service (hpc: the terminal execution-agent text); no reasoning-commit text; the
  BLAST launch selection check is API-only; it keeps the launch parent's single-file `terminal_execution.py` copy
  (hpc splits it into `terminal_*` files).
- Against the launch parent: no children, no `required_return_sources`, and the yield is completion-style instead of
  bounded by the remaining request slots.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (name×uses) |
|---|---|---|---|
| action_policy.py | 12 | Permitted actions: tool, wait for api_service_assignment_v1; tool only otherwise. No reason, child or redeliver. | BindingContext.assignment×1 |
| binding_record.py | 9 | As the launch parent's, binding_id gene_context_evidence/execution_job_submission/api_job_execution. | none |
| child_eligibility.py | 12 | No child roles, no allowed children. | none |
| closed_credit.py | 117 | Same as the launch parent's closed_credit.py (class renamed): Closed operational credit: validates closed runtime metadata, pins the original receipt prefix, captures the projected view once in closing facts and returns only that view later (no repricing). | BindingContext.episode_id×8, BindingContext.role×1, import:episode_receipts×1, import:episode_return_records×3, table:runtime_episodes×2, table:runtime_forms×3, table:runtime_observations×1, table:runtime_receipt_inheritance×2, table:runtime_record_receipts×2 |
| completion.py | 65 | Native-family completion proofs as launch, then the API delegate's completion_for_action; verify_completion ends in api_execution.verify_completion. | BindingContext.assignment×1, BindingContext.episode_id×4, import:episode_return_records×1, import:method_loop.identities×1, import:numerical×1, import:practical_yield×1, table:runtime_observations×1, yield:NumericBand×2 |
| configuration.py | 65 | Same as the launch parent's configuration.py (class renamed): Operands: services, store, directory, run_id, resources (kind local/pbs_ssh/hmmer_api/api), initial_information, tool_registry, handoff_unit and acquired_record_unit (finite > 0), log_window_bytes, log_roles, require_private_yield, results_yield_profiles (native_unbounded_local/hpc), task_yield_profiles ({cutoff>0, parameters}). Only A103 native resource bindings allowed; builds TerminalExecutionBehavior per non-API resource, APIServiceExecution, ExecutionProgressProvider, LocalFileSourceResults; installs result readers. | import:api_service_execution×1, import:execution_progress×1, import:numerical×1, svc.read_received_molecular_input×1, yield:YieldController×3, yield:YieldParameters×3 |
| contracts.py | 59 | As the launch parent's contracts; imports its own copy of terminal_execution. | import:a103_execution_bindings×1, import:a103_homology_execution×1, import:communication×1, import:domain×1, import:execution_contracts×1, import:launch_instructions×1, import:local_file_capture_results×1, import:native_blast_acquisition×1, import:native_blast_database_acquisition×1, import:native_blast_masking_acquisition×1, import:native_blast_standard_database_acquisition×1, import:native_blast_utility_acquisition×1, import:native_hmmer_acquisition×1, import:native_hmmer_preparation_acquisition×1, import:practical_execution_operations×1, import:practical_execution_records×1, import:practical_execution_state×1, import:practical_receipt_information×1, import:resource_records×1 |
| credit.py | 39 | Credit kind operational; closed view, else native family view, else api_execution.credit_view. | none |
| decision_contracts.py | 36 | Same as the launch parent's decision_contracts.py (class renamed): Exchange envelope: request_context(lookup) or select_action(selection, report_update). | import:runtime×2, runtime.composition_lookup_schema×2, runtime.Draft202012Validator×1, runtime._object×3 |
| decision_delivery.py | 82 | Same as the launch parent's decision_delivery.py (class renamed): Model call for the launch decision (saved call replay, exchange protocol, provider dispatch); composes LaunchDecisionInputs/Contracts/SavedDecisionExchange/DecisionExchange/Provider. | import:runtime×2, runtime._action_generation_schema×1, runtime._ASSIGNMENT_TRANSPORT×1, runtime.DECISION_EXCHANGE_PROTOCOL×5, runtime._digest×1, runtime.instructional_model_context×1, runtime._json×4, runtime.json×2, runtime._recorded_assignment_transport×1, runtime.WorkflowError×5, wf.contract_information_profile×1, wf.decision_exchanges×1, wf.decision_protocol×3, wf.freeze_contract_information×1, wf.freeze_literature_numerical_contracts×1, wf.history_preview×1, wf.is_job_source×2, wf.journal×1, wf.numerical_contracts×1, wf.provider×1, wf.provider.has_session×1, wf.receipts×4, wf.services×1, wf.uses_received_record_context×2, wf.validate_contract_information×2, table:runtime_model_calls×5 |
| decision_exchange.py | 116 | Same as the launch parent's decision_exchange.py (class renamed): Pending-decision lookup exchange and the interpretation context derived from received lookups. | import:runtime×2, runtime._action_generation_schema×1, runtime._category_yield_parameters×1, runtime.child_option_information×1, runtime.DECISION_CONTEXT_VERSION×1, runtime.instructional_model_context×2, runtime._json×2, runtime.lookup_attempts×1, runtime.Mapping×3, runtime.model_snapshot×1, runtime._plain×2, runtime._references_in×1, runtime.requested_contract_information×1, runtime.schema_failure_diagnostic×2, runtime.sqlite3×1, runtime.state_frame×1, runtime.ValidationError×4, runtime.yield_table×1, wf.controller_binding×1, wf.decision_exchanges×1, wf.execute×1, wf.journal×1, wf.run_id×1, wf.services×1, wf.store×2, wf.store.reference_subset×1, wf.validate_contract_information×1, table:runtime_model_calls×2 |
| decision_inputs.py | 70 | As launch, with execution_expectations captured for role launch_api. | import:episode_work_report×2, import:library.hpc_prompt×1, import:runtime×2, runtime.child_option_information×1, runtime.Mapping×1, wf.available_child_roles×1, wf.binding_context×2, wf.episode_bindings×1, wf.execution_expectations×1, wf.is_job_source×1, wf.job_episodes×4, wf.launch_instructions×2, wf.native_estimation_context×1, wf.native_event_information×2, wf.pending_work×1, wf.permits_common_action×1, wf.resource_context×1, wf.resource_estimator×5, wf.shared_information_context×1, wf.store×2, wf.waiting_support×1 |
| decision_presentation.py | 413 | Own API prompt (413 lines): TASK section (scientific question, assigned job, scope named without store handles, selected API work, parent constraints, parent-selected tool guidance, configured resource, exact assigned request, execution method, callable operations with instructions/arguments, selected resource instructions, requested information and return form, meanings of requested facts) and STEERING (completed action reports, pending child delivery, own action category yields, current operational continuation, yield limits, handoff completion, recorded API outcomes and complete API errors, latest own action, feedback, pending work, lookups). render_api_job_prompt picks HPC/scientific/API/selected/monitor/receiver renderer. | import:api_error_feedback×1, import:episode_work_report×1, import:execution_contracts×1, import:gene_context_evidence_prompt×3, import:library.hpc_prompt×2, import:library.monitor_prompt×2, import:native_profile_presentation×2, import:providers×2, import:receiver_prompt×2, providers.apply_state_frame×3, providers.DECISION_CONTEXT_VERSION×1, providers.deepcopy×1, providers.is_published_scientific_context×2, providers.json×1, providers._ordinary_runtime_receiver_context×1, providers.render_gene_context_evidence_prompt×1, providers.text_instructions×1 |
| decision_provider.py | 18 | Same as the launch parent's decision_provider.py (class renamed): Provider dispatch with this binding's prompt renderer under conversation 'REASONING'. | import:runtime×1, wf.provider×2, wf.provider.conversation_key×1, wf.specialist×1 |
| decision_state.py | 45 | Same as the launch parent's decision_state.py (class renamed): Decision context shown to the model (same field set as the scientific task) plus the launch binding's decision_context. | import:runtime×2, runtime.FACT_MEANINGS×1, runtime.FACT_SOURCES×1, runtime.json×2, runtime.Mapping×3, runtime._plain×2, runtime._references_in×1, wf.binding_context×1, wf.catalog×1, wf.controller_binding×1, wf.delivery_status×1, wf.extra_report_sources×1, wf.is_scientific_source×1, wf.job_episode_options×1, wf.journal×3, wf.knowledge×1, wf.local_outcome_preview×1, wf.pending_work×1, wf.receipt_projection×1, wf.run_id×1, wf.source_credit_binding×1, wf.source_credit_view×1, wf.specialist×1, wf.store×3, wf.store.reference_subset×1, wf.tools×1, wf.tools.model_contract_catalog×1, wf.working_state×1, table:runtime_actions×2 |
| episode.py | 32 | ExecutionEpisode at gene_context_evidence/execution_job_submission/api_job_execution, commissioning_parent the launch episode, roles (launch_api,), entry_roles (), renderer render_api_job_prompt. | none |
| from_parent.py | 127 | Assignment schema = anyOf the API resources' selected request schemas; prepare_assignment validates via api_execution in scope, kind must match, parent role must be launch, the selection must match the parent's original launch (BLAST launch selection), masking/utility inputs, input versions, native/standard BLAST inputs. No required return sources. | BindingContext.assignment×3, BindingContext.path×1, BindingContext.role×6, import:native_blast_database_result_publication×2, import:native_blast_standard_database_result_publication×2, svc.annotation_task_required×1 |
| goal.py | 10 | Goal text: carry out the assigned work through <service>, one operation per turn; keep inputs/request/resource/constraints fixed; distinguish immediate response from continuing remote job; preserve request/job identity and submission uncertainty; establish the usable monitoring/results handoff; verified handoff completion gives exact zero future credit. | BindingContext.assignment×1 |
| __init__.py | 0 | Same as the launch parent's __init__.py (class renamed): Empty package marker. | none |
| instructions.py | 20 | As launch without the reasoning-commit requirement (no reason action). | import:runtime_prompt×2, runtime_prompt.DECISION_EXCHANGE_PROTOCOL×1, runtime_prompt.INSTRUCTIONS×3, wf.binding_context×1, wf.decision_protocol×1, wf.knowledge×1, wf.launch_instructions×1, wf.native_event_information×1, wf.permits_common_action×2, wf.specialist×1 |
| internal_summary.py | 124 | As launch, plus api_execution.decision_context; selected_execution_task built from the single assignment (only ebi_hmmer API jobs). | BindingContext.assignment×2, BindingContext.role×3, import:native_profile_presentation×1, svc.scientific_parent_task×1 |
| operations.py | 56 | initialize/execute first check the parent launch's original request (BLAST API parent request, masking/utility inputs, versions, native/standard BLAST inputs) read from runtime_episodes, then delegate to api_execution; catalog = delegate's catalog (or masking/utility result catalogs). | BindingContext.assignment×9, BindingContext.path×3, BindingContext.role×1, BindingContext.scope×2, import:native_blast_database_result_publication×1, import:native_blast_masking_results×1, import:native_blast_standard_database_result_publication×1, import:native_blast_utility_results×1, table:runtime_episodes×1 |
| received_information.py | 113 | Same as the launch parent's received_information.py (class renamed): Which received child report sources are forwarded (BVBRC, minhash) and received report facts / closure facts. | BindingContext.request×2, BindingContext.role×11, import:blast_pairwise_result_views×1, import:blast_utility_result_views×1, import:bvbrc_data_views×1, import:bvbrc_minhash_views×1, import:hmmer_preparation_result_views×1, import:native_blast_database_result_views×1, import:native_blast_standard_database_result_views×1, import:sequence_masking_result_views×1, import:uniprot_return_contracts×1 |
| received_record_selection.py | 35 | Same as the launch parent's received_record_selection.py (class renamed): Receipt-scoped selection of handoffs and results from received records (initial known refs, handoffs, results). | BindingContext.assignment×1, BindingContext.role×1, BindingContext.scope×2 |
| received_reference_custody.py | 160 | Same as the launch parent's received_reference_custody.py (class renamed): Resolve references received from children, validate received typed reports, collect received form references. | BindingContext.role×10, import:bvbrc_homology_returns×1, import:hmmer_native_result_views×1 |
| report_delivery.py | 25 | Same as the launch parent's report_delivery.py (class renamed): finish(): same as the scientific parent (credit + pending handles, or saved form from facts). | import:library.private_policy_call×1, import:library.report_fact_assembly×1, import:runtime×2, runtime.form_with_facts×1, runtime._json×2, runtime.json×1, runtime.Record×2, wf.binding_context×1, wf.episode_bindings×1, wf.facts×1, wf.journal×2, wf.pending_handles×1, wf.release×2, wf.source_credit_view×1, table:runtime_forms×2 |
| report_reference_access.py | 115 | Same as the launch parent's report_reference_access.py (class renamed): Outgoing-report reference resolution; failures become denial. | BindingContext.role×12, BindingContext.scope×4, import:bvbrc_data_views×1, import:bvbrc_homology_returns×1, import:episode_bindings×2, import:hmmer_preparation_result_views×1, import:native_blast_database_results×1, import:native_blast_standard_database_results×1 |
| result_records.py | 260 | Same as the launch parent's result_records.py (class renamed): Result records: masking/utility selectors and inputs, input versions, handoff target lookup, selector validation, result directory, byte windows, selected result action, result body validation/read, context target checks, appservice/uniprot presence. | BindingContext.assignment×4, BindingContext.episode_id×9, BindingContext.role×3, BindingContext.run_id×2, BindingContext.scope×7, import:blast_pairwise_result_views×1, import:blast_utility_result_views×2, import:bvbrc_homology_returns×1, import:episode_receipts×1, import:execution_input_versions×1, import:hmmer_native_result_views×1, import:hmmer_preparation_result_views×1, import:native_blast_database_result_views×1, import:native_blast_standard_database_result_views×1, import:sequence_masking_result_views×2, svc.record_selection×1, table:runtime_actions×2, table:runtime_episodes×1, table:runtime_receipt_inheritance×2 |
| saved_decision_exchange.py | 82 | Same as the launch parent's saved_decision_exchange.py (class renamed): Authenticate frozen contract-information requests and saved exchange history without dispatch. | import:runtime×2, runtime.apply_state_frame×1, runtime.CONTRACT_INFORMATION_OPERATIONS×1, runtime.DECISION_CONTEXT_VERSION×1, runtime.instructional_model_context×1, runtime.is_contract_information×1, runtime._json×8, runtime.json×1, runtime.model_snapshot×1, runtime._recorded_action_generation_schema×1, runtime.requested_contract_information×1, runtime.ValidationError×1, runtime.WorkflowError×9, wf.contract_information_reply×1, wf.decision_exchanges×2, wf.journal×1, wf.validate_contract_information×2, table:runtime_model_calls×1 |
| task.py | 226 | APIJobTask loop (grain launch_api); no empty-reasoning check because reason is not permitted. | import:episode_source_failure×1, import:library.action_contracts×1, import:library.private_policy_call×1, import:providers×1, import:read_mapping×1, import:runtime×2, runtime.AcquisitionError×2, runtime.ActionFailure×1, runtime.ContractError×2, runtime.ContractInformationError×1, runtime._decode_recorded_action_response×1, runtime.Draft202012Validator×2, runtime.EventTargetError×2, runtime.inspect×1, runtime._json×5, runtime.json×8, runtime.Mapping×9, runtime.nullcontext×5, runtime.observes_action_outcome×1, runtime._plain×1, runtime.ReportBoundaryError×1, runtime.ReportRedelivery×2, runtime.schema_failure_diagnostic×1, runtime.SourceEnd×2, runtime.sqlite3×2, runtime.subprocess×2, runtime.validate_form×1, runtime.ValidationError×3, runtime._wait_target_feedback×2, runtime.WorkflowError×2, wf.action_schema×1, wf.automatic_score_updates×1, wf.binding_context×1, wf.completed_unit×3, wf.completions×3, wf.controller_value×2, wf.decision_exchanges×3, wf.delivery_resolution_inputs×1, wf.execute×1, wf.execution_binding×7, wf.inprocess_replay×4, wf.journal×7, wf.last_observed_credit×1, wf.next_return×1, wf.pending_work×1, wf.perform_selected_wait×1, wf.permits_common_action×1, wf.receive_native_outcome×1, wf.receive_outcome×1, wf.resolve_pending_deliveries×1, wf.resolver×1, wf.retain_shared_grading_results×1, wf.run_id×3, wf.selected×3, wf.source_credit_view×1, wf.specialist×1, wf.store×8, wf.validate_report×1, table:runtime_actions×8, table:runtime_episodes×1, table:runtime_model_calls×2 |
| task_state.py | 108 | Same as the launch parent's task_state.py (class renamed): Launch decision state and checkpoint/restore (same shape as the scientific task_state). | import:episode_source_failure×1, import:runtime×2, runtime.ActionLeaf×1, runtime.EFFECT_VERSION×1, runtime.Episode×1, runtime.interpretation_schema×1, runtime._json×2, runtime.json×4, runtime._object×1, runtime._plain×1, runtime.Record×1, wf.archive×1, wf.completions×4, wf.context×1, wf.controller_value×1, wf.execution_binding×4, wf.grains×1, wf.inprocess_replay×7, wf.journal×5, wf.progress_provider×2, wf.recover_commissions×1, wf.run_id×1, wf.source_credit_view×1, wf.store×2, table:runtime_actions×5 |
| terminal_execution.py | 185 | Same as the launch parent's terminal_execution.py (class renamed): TerminalExecutionBehavior for local/HPC resources: exec_command only (cmd, workdir, target resource|coordinator, env), instruction-led shell execution with saved receipts, practical state and completion proof, PracticalYieldEstimator. | BindingContext.assignment×9, BindingContext.episode_id×4, BindingContext.role×1, BindingContext.run_id×5, import:acquisition×1, import:communication×1, import:domain×1, import:practical_execution_operations×1, import:practical_execution_records×1, import:practical_execution_state×1, import:practical_receipt_information×3, import:practical_yield×1, import:terminal_execution×1, import:terminal_scientific_evidence×2, svc.workflow×1, yield:PracticalYieldEstimator×2 |
| to_parent.py | 118 | Facts = native family facts or api_execution.facts with execution_result_origin null. | import:blast_pairwise_result_views×2, import:blast_result_views×1, import:blast_utility_result_views×2, import:bvbrc_data_views×1, import:bvbrc_minhash_views×1, import:hmmer_native_result_views×2, import:hmmer_preparation_result_views×2, import:local_file_capture_results×1, import:native_blast_database_results×1, import:native_blast_database_result_views×1, import:native_blast_standard_database_results×1, import:native_blast_standard_database_result_views×1, import:native_hmmer_acquisition×1, import:sequence_masking_result_views×2, import:uniprot_return_contracts×2 |
| waiting.py | 9 | Same as the launch parent's waiting.py (class renamed): Record suspension condition and forward it to the execution backend. | wf.execution_backend×1, wf.execution_handle×2 |
| yield_estimator.py | 50 | Controller: YieldController(cutoff from task profile `launch_api:<request class>`, parameters) with PracticalYieldEstimator verifying completion via verify_completion. | BindingContext.assignment×1, BindingContext.role×1, import:numerical×1, import:practical_yield×2, yield:PracticalYieldEstimator×4, yield:YieldController×2, yield:YieldParameters×2 |
