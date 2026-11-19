# A103 local_job_execution: intent carried over from HEAD 97308b94c

Episode path: `gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution`
Old role: `launch_local`. Commissioning parent: `.../execution_job_submission` (role `launch`). Old class: `ExecutionEpisode` with task `NativeTask`.
Source: only the files directly in this folder at HEAD. Tests in `tests/` (test_native_task.py) were not read.

## What this episode is for (its own words)
The episode is the execution agent for one actual job on the local resource (kind `local`). Its goal text is the same terminal goal as hpc_job_execution (`terminal_goal.py`):

> "You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery from the actual resource instructions and observed results. No sequence of setup or job-stage operations is prescribed. Preserve the caller's scientific inputs, desired outputs and acceptance criteria. ... Each command is one ordinary episode action: its actual result and earned credit enter the iterator, including failure or zero progress. ... If a submission outcome is uncertain, investigate that original submission rather than create a duplicate. ... The episode iterator decides continuation from credit; add no stopping budget."

It is followed by the resource instructions from the frozen launch library.

## Task and instructions
These are the same as hpc_job_execution: `instructions.py` composes the goal with tool knowledge, the launch library and the delivery repair paragraph, and adds wait and native-event text only if wait were permitted. `task.py` is the iteration loop with the same rejection feedback branches. Report admission uses grain `launch_local`.

## What it reads from its parent's assignment
- The parent `launch` assignment `execution_launch_assignment_v1` (requests per resource, immutable_input_versions, constraints, launch_instructions).
- Its own `practical_assignment_v1`: resource_id, resource_kind = `local`, a workspace confined to the resource workspace, requested_job (generic or one native family), endpoint (`usable_handoff` | `completed_job_outputs`) and initial_context.
- Difference from HPC: `child_assignment_schema` is the plain per-resource assignment schema ("Describe this selected child's original admitted assignment"). There is no frozen-request enum.
- `prepare_assignment` and `_check_parent_inputs` run the same parent-launch re-validation (masking and utility inputs, input versions, native and standard BLAST job inputs).

## Children
None. This episode is a leaf.

## Decision state and what the model sees
Decision state is the same as hpc_job_execution: the full `decision_state` field set plus the terminal decision_context (execution_assignment, execution_resource, coordinator_workspace, execution_progress, execution_completion).
Local-only addition (`internal_summary._with_selected_execution_task`): when the services expose `scientific_parent_task`, the context gains `selected_execution_task` (`selected_execution_task_v1`). It holds the parent's scientific_question, selected_tool_info, and the requests, each with resource_id, resource_kind, endpoint, constraints, exactly one native job family (HMMER jobs shown through `native_profile_scientific_job_view`) and the resource information. It also holds constraints, selector and result_description. When this field is present, the prompt can be rendered with `render_selected_execution_prompt`.
`decision_inputs.py` captures execution_expectations for role `launch_local`.

## Tools offered
`exec_command` (cmd, workdir, env, target resource|coordinator) with the `tool` action only, as in HPC.

## Credit
`operational`. Uses the closed view when one exists, otherwise the native result family view, otherwise the practical terminal state's credit view. This is the same as HPC and is not bounded.

## Continuation
Profile key `task_yield_profiles['launch_local:' + request_yield_class]` (the class is `practical_local_<native families>_<handoff|outputs>`). Uses YieldController + PracticalYieldEstimator on verified completion, which maps to the new completion-with-a-target estimator. `require_private_yield` must be true.

## Report to parent
Same fact sources and facts as HPC, including the terminal practical facts for role `launch_local`. `validate_report` requires x-source fields to equal the recorded facts.

## Differences from siblings
- Compared with hpc_job_execution, the docstrings and role names differ. HPC has the frozen HPC child assignment enum; local does not. Local adds `selected_execution_task` to the decision context; HPC does not. All other files are byte-identical apart from role and binding names.
- Compared with api_job_execution, see that file.

## File by file (HEAD)

Old-runner names are counted per file (also in runs/carry_over/calls/a103_05.tsv). Imports of old non-episode support modules under `root.a103.*` (native_* acquisition/results/views, a103_execution_bindings, a103_homology_execution, practical_execution_*, terminal_execution, api_service_execution, execution_progress, local_file_capture_results, practical_receipt_information, terminal_scientific_evidence, execution_contracts, launch_instructions, domain) are support code; see runs/placement_plan/placement.tsv and runs/placement_merge/plan.tsv for where they now live.

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| action_policy.py | 9 | Offers only the `tool` common action (no child, wait, reason or redeliver). | `none` |
| binding_record.py | 9 | Binding descriptor: own binding_id, VERSION `execution_episode_v1`, resources, initial_information, handoff_unit, acquired_record_unit, log window/roles, optional require_private_yield / results_yield_profiles / task_yield_profiles. | `none` |
| child_eligibility.py | 10 | No child roles; no allowed children (leaf episode). | `none` |
| closed_credit.py | 117 | Closed operational credit: once the episode yields, its projected credit view is captured in the closing facts and later reads return only that saved view (never re-priced); authenticates completion/archive carrier, observation history digest and receipt prefix. | `root.a103.episode_receipts×1`, `root.a103.episode_return_records×3`, `runtime_episodes×2`, `runtime_forms×3`, `runtime_observations×1`, `runtime_receipt_inheritance×2`, `runtime_record_receipts×2` |
| completion.py | 65 | Completion proof for one action (native masking/utility/standard-db/db result families, else delegate); verify_completion checks a recorded endpoint verdict, else family proof, else the practical state's own proof. | `ESTIMATOR_VERSION×2`, `NumericBand×2`, `root.a103.episode_return_records×1`, `root.a103.method_loop.identities×1`, `root.a103.numerical×1`, `root.a103.practical_yield×1`, `runtime_observations×1` |
| configuration.py | 65 | Validates explicit resources (kinds local/pbs_ssh/hmmer_api/api), initial inventory, positive handoff_unit/acquired_record_unit, log window/roles, results and task yield profiles {cutoff>0, parameters}; refuses foreign `native_*` bindings; builds a TerminalExecutionBehavior per non-API resource, APIServiceExecution for API resources, ExecutionProgressProvider, LocalFileSourceResults; installs result readers. | `root.a103.numerical×1`, `YieldController×3`, `YieldParameters×3` |
| contracts.py | 60 | Constants and schemas: ROLES, KINDS, ROLE_KINDS, RESULTS_SCHEMA, NATIVE_RESULT_ORIGIN (current filesystem, unverified attempt version, no atomic snapshot), launch/result operation catalogs (execution.capabilities, execution.results.status/collect/read); imports of the old shared support modules. | `root.a103.communication×1` |
| credit.py | 39 | credit_kind = `operational`; closed view if saved, else native result-family credit views, else the practical (terminal) state's credit view. | `none` |
| decision_contracts.py | 36 | Decision exchange envelope: `request_context` (lookup) or `select_action` (selection + report_update). | `_live_original_runtime.composition_lookup_schema×2`, `_live_original_runtime.Draft202012Validator×1`, `_live_original_runtime._object×3`, `root.a103.runtime×1` |
| decision_delivery.py | 82 | Aggregates decision inputs, exchange, saved-exchange and provider mixins; composes instructions(). | `_live_original_runtime._action_generation_schema×1`, `_live_original_runtime._ASSIGNMENT_TRANSPORT×1`, `_live_original_runtime.DECISION_EXCHANGE_PROTOCOL×5`, `_live_original_runtime._digest×1`, `_live_original_runtime.instructional_model_context×1`, `_live_original_runtime._json×4`, `_live_original_runtime.json×2`, `_live_original_runtime._recorded_assignment_transport×1`, `_live_original_runtime.WorkflowError×5`, `root.a103.runtime×1`, `runtime_model_calls×5`, `self.workflow.contract_information_profile×1`, `self.workflow.decision_exchanges×1`, `self.workflow.decision_protocol×3`, `self.workflow.freeze_contract_information×1`, `self.workflow.freeze_literature_numerical_contracts×1`, `self.workflow.history_preview×1`, `self.workflow.is_job_source×2`, `self.workflow.journal×1`, `self.workflow.numerical_contracts×1`, `self.workflow.provider×1`, `self.workflow.receipts×4`, `self.workflow.services×1`, `self.workflow.uses_received_record_context×2`, `self.workflow.validate_contract_information×2` |
| decision_exchange.py | 116 | Derives the received interpretation context from pending lookup exchanges. | `_live_original_runtime._action_generation_schema×1`, `_live_original_runtime._category_yield_parameters×1`, `_live_original_runtime.child_option_information×1`, `_live_original_runtime.DECISION_CONTEXT_VERSION×1`, `_live_original_runtime.instructional_model_context×2`, `_live_original_runtime._json×2`, `_live_original_runtime.lookup_attempts×1`, `_live_original_runtime.Mapping×3`, `_live_original_runtime.model_snapshot×1`, `_live_original_runtime._plain×2`, `_live_original_runtime._references_in×1`, `_live_original_runtime.requested_contract_information×1`, `_live_original_runtime.schema_failure_diagnostic×2`, `_live_original_runtime.sqlite3×1`, `_live_original_runtime.state_frame×1`, `_live_original_runtime.ValidationError×4`, `_live_original_runtime.yield_table×1`, `root.a103.runtime×1`, `runtime_model_calls×2`, `self.workflow.controller_binding×1`, `self.workflow.decision_exchanges×1`, `self.workflow.execute×1`, `self.workflow.journal×1`, `self.workflow.run_id×1`, `self.workflow.services×1`, `self.workflow.store×2`, `self.workflow.validate_contract_information×1` |
| decision_inputs.py | 70 | Adds to model inputs: resource_context, shared_information_context, launch instruction library + selected launch instructions, child options, completed_action_reports, requested_action_history (HPC prompt), pending_work, execution_expectations for its own role, resource_tool_estimates, native_execution_expectations, native_event_targets, waiting_support. | `_live_original_runtime.child_option_information×1`, `_live_original_runtime.Mapping×1`, `root.a103.episode_work_report×2`, `root.a103.library.hpc_prompt×1`, `root.a103.runtime×1`, `self.workflow.available_child_roles×1`, `self.workflow.binding_context×2`, `self.workflow.episode_bindings×1`, `self.workflow.execution_expectations×1`, `self.workflow.is_job_source×1`, `self.workflow.job_episodes×4`, `self.workflow.launch_instructions×2`, `self.workflow.native_estimation_context×1`, `self.workflow.native_event_information×2`, `self.workflow.pending_work×1`, `self.workflow.permits_common_action×1`, `self.workflow.resource_context×1`, `self.workflow.resource_estimator×5`, `self.workflow.shared_information_context×1`, `self.workflow.store×2`, `self.workflow.waiting_support×1` |
| decision_presentation.py | 59 | Prompt dispatch: chooses HPC / gene-context / API-launch / selected-execution / monitor / receiver renderer from reconstructed state frames; else raw JSON. | `_live_original_providers.apply_state_frame×3`, `_live_original_providers.DECISION_CONTEXT_VERSION×1`, `_live_original_providers.deepcopy×1`, `_live_original_providers.is_api_launch_context×2`, `_live_original_providers.is_published_scientific_context×2`, `_live_original_providers.json×1`, `_live_original_providers._ordinary_runtime_receiver_context×1`, `_live_original_providers.render_api_launch_prompt×1`, `_live_original_providers.render_gene_context_evidence_prompt×1`, `_live_original_providers.text_instructions×1`, `root.a103.library.hpc_prompt×1`, `root.a103.library.monitor_prompt×1`, `root.a103.providers×1` |
| decision_provider.py | 18 | Calls the provider with this binding's prompt renderer under conversation key REASONING. | `root.a103.runtime×1`, `self.workflow.provider×2`, `self.workflow.specialist×1` |
| decision_state.py | 45 | Model-facing state: goal, scope, working_state, visible refs, current_credit, evidence vector, credit_binding, time_accounting, pending work, last outcome, feedback, visual evidence, report deliveries, controller state/binding, tools, tool knowledge, job options, available report facts, requested purpose/form, current report update/basis, plus the binding's decision_context. | `_live_original_runtime.FACT_MEANINGS×1`, `_live_original_runtime.FACT_SOURCES×1`, `_live_original_runtime.json×2`, `_live_original_runtime.Mapping×3`, `_live_original_runtime._plain×2`, `_live_original_runtime._references_in×1`, `root.a103.runtime×1`, `runtime_actions×2`, `self.workflow.binding_context×1`, `self.workflow.catalog×1`, `self.workflow.controller_binding×1`, `self.workflow.delivery_status×1`, `self.workflow.extra_report_sources×1`, `self.workflow.is_scientific_source×1`, `self.workflow.job_episode_options×1`, `self.workflow.journal×3`, `self.workflow.knowledge×1`, `self.workflow.local_outcome_preview×1`, `self.workflow.pending_work×1`, `self.workflow.receipt_projection×1`, `self.workflow.run_id×1`, `self.workflow.source_credit_binding×1`, `self.workflow.source_credit_view×1`, `self.workflow.specialist×1`, `self.workflow.store×3`, `self.workflow.tools×1`, `self.workflow.working_state×1` |
| episode.py | 31 | Composition: binding_path, commissioning_parent `.../execution_job_submission`, single role, decision_source_type, decision_prompt_renderer, entry_roles (), replaces_default_instructions. | `none` |
| from_parent.py | 126 | Assignment schema per bound local resource; prepare_assignment validates resource kind, parent role `launch`, launch contract, masking/utility inputs, input versions, BLAST job inputs; initial_references. | `none` |
| goal.py | 7 | Goal delegates to the terminal execution goal (terminal_goal.py). | `none` |
| __init__.py | 0 | Package marker; no intent. | `none` |
| instructions.py | 22 | Instruction composition: binding goal + reasoning-commit (if allowed) + tool knowledge + launch library + delivery repair + wait + native event guidance; exchange-protocol history replacement. | `_live_original_runtime_prompt.DECISION_EXCHANGE_PROTOCOL×1`, `_live_original_runtime_prompt.INSTRUCTIONS×3`, `_live_original_runtime_prompt.REASONING_COMMIT_REQUIREMENT×1`, `root.a103.runtime_prompt×1`, `source.workflow.binding_context×1`, `source.workflow.decision_protocol×1`, `source.workflow.knowledge×1`, `source.workflow.launch_instructions×1`, `source.workflow.native_event_information×1`, `source.workflow.permits_common_action×3`, `source.workflow.specialist×1` |
| internal_summary.py | 121 | initial_decision_context, decision_context from the terminal behaviour, plus selected_execution_task built from the scientific parent (question, selected tool info, exactly one native job family); resource capabilities and tool contracts. | `none` |
| operations.py | 48 | Delegates to the per-resource TerminalExecutionBehavior; parent-launch input checks; state(); catalog; execute. | `runtime_episodes×1` |
| parent_launch_contract.py | 8 | Schema of the commissioning Launch assignment (requests per resource, immutable_input_versions, constraints, launch_instructions). | `none` |
| received_information.py | 113 | Forwarded report sources/facts for annotation/gene_context_evidence roles (file sources, masking, utility, UniProt, BLAST db, HMMER prep, BLAST pairwise, BV-BRC, MinHash, AppService returns). | `none` |
| received_record_selection.py | 35 | Selects received handoffs and result records from known refs. | `none` |
| received_reference_custody.py | 160 | Resolves received references, validates received report forms and their reference custody. | `none` |
| report_delivery.py | 25 | finish(): without a report contract returns credit + pending handles; else saved form or facts+interpretations form, then release. | `_live_original_runtime.form_with_facts×1`, `_live_original_runtime._json×2`, `_live_original_runtime.json×1`, `_live_original_runtime.Record×2`, `root.a103.library.private_policy_call×1`, `root.a103.library.report_fact_assembly×1`, `root.a103.runtime×1`, `runtime_forms×2`, `self.workflow.binding_context×1`, `self.workflow.episode_bindings×1`, `self.workflow.facts×1`, `self.workflow.journal×2`, `self.workflow.pending_handles×1`, `self.workflow.release×2`, `self.workflow.source_credit_view×1` |
| report_reference_access.py | 115 | Resolves references in this episode's outgoing report; failures deny. | `reference_in_context×4`, `root.a103.episode_bindings×2` |
| result_records.py | 260 | Result-record helpers: masking/utility inputs, target, selector, result directory, windows, result body validation/read, receipt selection, context target. | `root.a103.episode_receipts×1`, `runtime_actions×2`, `runtime_episodes×1`, `runtime_receipt_inheritance×2` |
| saved_decision_exchange.py | 82 | Authenticates frozen requests and saved exchange history. | `_live_original_runtime.apply_state_frame×1`, `_live_original_runtime.CONTRACT_INFORMATION_OPERATIONS×1`, `_live_original_runtime.DECISION_CONTEXT_VERSION×1`, `_live_original_runtime.instructional_model_context×1`, `_live_original_runtime.is_contract_information×1`, `_live_original_runtime._json×8`, `_live_original_runtime.json×1`, `_live_original_runtime.model_snapshot×1`, `_live_original_runtime._recorded_action_generation_schema×1`, `_live_original_runtime.requested_contract_information×1`, `_live_original_runtime.ValidationError×1`, `_live_original_runtime.WorkflowError×9`, `root.a103.runtime×1`, `runtime_model_calls×1`, `self.workflow.contract_information_reply×1`, `self.workflow.decision_exchanges×2`, `self.workflow.journal×1`, `self.workflow.validate_contract_information×2` |
| task.py | 226 | Iteration loop next/apply_response/execute (job_child storage-failure feedback, closed-form repair, reads.map parameter feedback); report admission grain = its role. | `_live_original_runtime.AcquisitionError×2`, `_live_original_runtime.ActionFailure×1`, `_live_original_runtime.ContractError×2`, `_live_original_runtime.ContractInformationError×1`, `_live_original_runtime._decode_recorded_action_response×1`, `_live_original_runtime.Draft202012Validator×2`, `_live_original_runtime.EventTargetError×2`, `_live_original_runtime.inspect×1`, `_live_original_runtime._json×5`, `_live_original_runtime.json×8`, `_live_original_runtime.Mapping×9`, `_live_original_runtime.nullcontext×5`, `_live_original_runtime.observes_action_outcome×1`, `_live_original_runtime._plain×1`, `_live_original_runtime.ReportBoundaryError×1`, `_live_original_runtime.ReportRedelivery×2`, `_live_original_runtime.schema_failure_diagnostic×1`, `_live_original_runtime.SourceEnd×2`, `_live_original_runtime.sqlite3×2`, `_live_original_runtime.subprocess×2`, `_live_original_runtime.validate_form×1`, `_live_original_runtime.ValidationError×3`, `_live_original_runtime._wait_target_feedback×2`, `_live_original_runtime.WorkflowError×2`, `root.a103.episode_source_failure×1`, `root.a103.library.action_contracts×1`, `root.a103.library.private_policy_call×1`, `root.a103.providers×1`, `root.a103.runtime×1`, `runtime_actions×8`, `runtime_episodes×1`, `runtime_model_calls×2`, `self.workflow.action_schema×1`, `self.workflow.automatic_score_updates×1`, `self.workflow.binding_context×1`, `self.workflow.completed_unit×3`, `self.workflow.completions×3`, `self.workflow.controller_value×2`, `self.workflow.decision_exchanges×3`, `self.workflow.delivery_resolution_inputs×1`, `self.workflow.execute×1`, `self.workflow.execution_binding×7`, `self.workflow.inprocess_replay×4`, `self.workflow.journal×7`, `self.workflow.last_observed_credit×1`, `self.workflow.next_return×1`, `self.workflow.pending_work×1`, `self.workflow.perform_selected_wait×1`, `self.workflow.permits_common_action×1`, `self.workflow.receive_native_outcome×1`, `self.workflow.receive_outcome×1`, `self.workflow.resolve_pending_deliveries×1`, `self.workflow.resolver×1`, `self.workflow.retain_shared_grading_results×1`, `self.workflow.run_id×3`, `self.workflow.selected×3`, `self.workflow.source_credit_view×1`, `self.workflow.specialist×1`, `self.workflow.store×8`, `self.workflow.validate_report×1` |
| task_state.py | 108 | Task state fields, restore/checkpoint/record_effect, record_execution_failure (failed outcome still enters the iterator with credit). | `_live_original_runtime.ActionLeaf×1`, `_live_original_runtime.EFFECT_VERSION×1`, `_live_original_runtime.Episode×1`, `_live_original_runtime.interpretation_schema×1`, `_live_original_runtime._json×2`, `_live_original_runtime.json×4`, `_live_original_runtime._object×1`, `_live_original_runtime._plain×1`, `_live_original_runtime.Record×1`, `root.a103.episode_source_failure×1`, `root.a103.runtime×1`, `runtime_actions×5`, `self.workflow.archive×1`, `self.workflow.completions×4`, `self.workflow.controller_value×1`, `self.workflow.execution_binding×4`, `self.workflow.inprocess_replay×7`, `self.workflow.journal×5`, `self.workflow.progress_provider×2`, `self.workflow.recover_commissions×1`, `self.workflow.run_id×1`, `self.workflow.source_credit_view×1`, `self.workflow.store×2` |
| terminal_assignment.py | 22 | Terminal assignment validation per resource kind. | `none` |
| terminal_contracts.py | 24 | exec_command operation contract (cmd, workdir, target resource|coordinator, env). | `root.a103.communication×1` |
| terminal_credit.py | 11 | Practical state credit view and completion proof. | `none` |
| terminal_execution.py | 41 | Composes the terminal behaviour (goal, operations, state, assignment, summary, report, credit) and practical_estimator. | `PracticalYieldEstimator×2`, `root.a103.practical_yield×1` |
| terminal_goal.py | 18 | Own terminal goal text: execution agent for the actual job/resource; exec_command; no prescribed stages; do not duplicate uncertain submissions; iterator decides continuation from credit, no stopping budget; plus resource instructions from the library. | `none` |
| terminal_operations.py | 47 | exec_command execution with PracticalState begin/finish, validations, receipts published. | `none` |
| terminal_report.py | 31 | Practical facts: practical_completed, practical_receipt_digests, practical_receipt_refs. | `none` |
| terminal_state.py | 18 | PracticalState directory per run/episode. | `none` |
| terminal_summary.py | 16 | Decision context: execution_assignment, execution_resource, coordinator_workspace, execution_progress, execution_completion. | `none` |
| to_parent.py | 132 | Fact sources incl. terminal practical facts; facts = terminal facts + handoff refs + result refs + file sources + origin + execution_completed; validate_report checks x-source fields equal recorded facts. | `none` |
| waiting.py | 9 | suspension_changed: records the wait condition and sets suspension on the execution backend. | `self.workflow.execution_backend×1`, `self.workflow.execution_handle×2` |
| yield_estimator.py | 50 | Request yield class; profile key `<role>:<class>`; YieldController(cutoff, parameters) + PracticalYieldEstimator on verify_completion; practical_estimator delegated to terminal behaviour. | `PracticalYieldEstimator×2`, `root.a103.numerical×1`, `root.a103.practical_yield×1`, `YieldController×2`, `YieldParameters×2` |

## Carried over

One row per old function, class and method (`runs/carry_over/functions/...tsv`). Kind: `machinery` (old runner, not carried), `episode function` (new place), `unplaced` (not carried, reported with its reason). Carried 19 November 2026 into the ten-file form; the library calls are `episode_support/...` names, the job service is BLOCKED-ON-JOB-SERVICE (see the blocked file).

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| action_policy.py | NativeActionPolicy | machinery | common-action policy: the system offers only ToolCall and ChildCall; the one tool is in task.py TOOLS |
| action_policy.py | NativeActionPolicy.permitted_common_actions | machinery | common-action policy: the system offers only ToolCall and ChildCall; the one tool is in task.py TOOLS |
| binding_record.py | NativeBindingRecord | machinery | the binding's own as_record() (README 3) |
| binding_record.py | NativeBindingRecord.as_record | machinery | the binding's own as_record() (README 3) |
| child_eligibility.py | NativeChildEligibility | episode function | task.py CHILD_SLOTS = {} |
| child_eligibility.py | NativeChildEligibility.child_roles | episode function | task.py CHILD_SLOTS = {} |
| child_eligibility.py | NativeChildEligibility.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| closed_credit.py | ClosedExecutionCredit | machinery | closed credit view saved in the closing facts, runtime_* receipts and observations, receipt inheritance; credit is completion['credit'] |
| closed_credit.py | ClosedExecutionCredit._closed_credit_carrier | machinery | closed credit view saved in the closing facts, runtime_* receipts and observations, receipt inheritance; credit is completion['credit'] |
| closed_credit.py | ClosedExecutionCredit._closed_credit_receipts | machinery | closed credit view saved in the closing facts, runtime_* receipts and observations, receipt inheritance; credit is completion['credit'] |
| closed_credit.py | ClosedExecutionCredit._closed_credit_value | machinery | closed credit view saved in the closing facts, runtime_* receipts and observations, receipt inheritance; credit is completion['credit'] |
| closed_credit.py | ClosedExecutionCredit._closed_credit_facts | machinery | closed credit view saved in the closing facts, runtime_* receipts and observations, receipt inheritance; credit is completion['credit'] |
| closed_credit.py | ClosedExecutionCredit._closed_operational_credit_view | machinery | closed credit view saved in the closing facts, runtime_* receipts and observations, receipt inheritance; credit is completion['credit'] |
| completion.py | ExecutionCompletion | episode function | class |
| completion.py | ExecutionCompletion.completion_for_action | episode function | messages/internal_summary.py _completion (practical branch); the four native result-family branches belong to the results role (unplaced) |
| completion.py | ExecutionCompletion._closed_completion_verdict | machinery | reads runtime_observations (old journal) to re-verify a recorded completion |
| completion.py | ExecutionCompletion.verify_completion | machinery | completion proof as a controller input and its re-verification; the completion controller replaces it (yield_estimator.py), the proof itself is messages/internal_summary.py _completion |
| configuration.py | NativeConfiguration | episode function | settings |
| configuration.py | NativeConfiguration.__init__ | episode function | settings: task.py reads ctx.settings (resource, coordinator_workspace, launch_instructions_directory, tool_knowledge_directory); yield_estimator.py reads settings cost and parameters; the resource check is the library TerminalExecution configuration check called by task.py _operations |
| contracts.py | launch_operation_catalog | unplaced | operation of the parent role launch (execution.capabilities); launch_local never offered it |
| contracts.py | native_result_operation_catalog | unplaced | operations of the results role (execution_result_acquisition); launch_local never offered them |
| contracts.py | _outcome | machinery | old tool-outcome wrapper (status, record_refs, changed_record_refs); the tool returns its own outcome |
| credit.py | ExecutionEpisodeCredit | episode function | credit.py |
| credit.py | ExecutionEpisodeCredit.credit_kind | machinery | credit kind deleted (README 3d) |
| credit.py | ExecutionEpisodeCredit.project_credit | episode function | credit.py credit (closed view dropped: machinery) |
| credit.py | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py credit (practical-state branch via library project_practical_credit); the seven native result-family branches belong to the results role (unplaced) |
| credit.py | ExecutionEpisodeCredit.credit_view | episode function | credit.py credit |
| decision_contracts.py | NativeDecisionContracts | machinery | decision-exchange envelope (request_context / select_action) |
| decision_contracts.py | NativeDecisionContracts.exchange_schema | machinery | decision-exchange envelope (request_context / select_action) |
| decision_contracts.py | NativeDecisionContracts.exchange_response | machinery | decision-exchange envelope (request_context / select_action) |
| decision_delivery.py | NativeDecisionDelivery | machinery | decision aggregation, exchange, provider and saved-exchange mixins, runtime_model_calls |
| decision_delivery.py | NativeDecisionDelivery.call | machinery | decision aggregation, exchange, provider and saved-exchange mixins, runtime_model_calls |
| decision_delivery.py | NativeDecisionDelivery.instructions | episode function | task.py _instructions |
| decision_exchange.py | NativeDecisionExchange | machinery | decision-exchange loop |
| decision_exchange.py | NativeDecisionExchange.interpretation_context | machinery | decision-exchange loop |
| decision_exchange.py | NativeDecisionExchange.exchange_decision | machinery | decision-exchange loop |
| decision_inputs.py | NativeDecisionInputs | episode function | class |
| decision_inputs.py | NativeDecisionInputs.decision_inputs | episode function | task.py decide: launch instruction library and selected launch instructions, tool knowledge, resource context; the other inputs (child options, completed_action_reports, hpc requested_action_history, pending_work, execution_expectations, resource estimates, native event targets, waiting support) are not carried (unplaced) |
| decision_presentation.py | present_native_task | episode function | task.py _task_text (selected-execution presentation); the hpc, monitor, api and receiver renderers do not apply |
| decision_provider.py | NativeDecisionProvider | machinery | provider call and conversation key (the system calls the model) |
| decision_provider.py | NativeDecisionProvider.conversation_key | machinery | provider call and conversation key (the system calls the model) |
| decision_provider.py | NativeDecisionProvider.complete_decision | machinery | provider call and conversation key (the system calls the model) |
| decision_state.py | NativeDecisionState | episode function | class |
| decision_state.py | NativeDecisionState.decision_state | episode function | messages/internal_summary.py internal_summary and task.py decide (the exchange, feedback, report-update and receipt fields are machinery) |
| episode.py | ExecutionEpisode | episode function | episode.py LocalJobExecution |
| from_parent.py | NativeAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | NativeAssignment.child_assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | NativeAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | NativeAssignment._permitted | machinery | check of the commission against the launch parent's own constraints (a wrong commission fails at form admission; no extra check) |
| from_parent.py | NativeAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (library validate_assignment); the parent-launch re-validation from runtime_episodes is machinery |
| from_parent.py | NativeAssignment._request_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | NativeAssignment._validate_request | episode function | messages/read_from_parent.py read_from_parent (validate_assignment) and task.py _operations (TerminalExecution.validate_assignment) |
| from_parent.py | NativeAssignment._launch | machinery | parent launch assignment re-validation (old runtime_episodes read) |
| from_parent.py | NativeAssignment._constraints | machinery | parent launch assignment re-validation |
| from_parent.py | NativeAssignment.required_return_sources | machinery | always returned (); parent selection of return fields is the system's |
| from_parent.py | NativeAssignment.initial_references | episode function | messages/read_from_parent.py ASSIGNMENT_FORM record_refs (new field: the job input records the old masking and utility input checks named) |
| goal.py | NativeGoal | episode function | goal.py GOAL and task.py GOAL_INSTRUCTION |
| goal.py | NativeGoal.instructions | episode function | task.py _instructions / GOAL_INSTRUCTION |
| instructions.py | instructions | episode function | task.py _instructions (goal, resource instructions, tool knowledge and launch library text); the delivery-repair, wait, native-event and exchange-protocol paragraphs are machinery |
| internal_summary.py | NativeSummary | episode function | messages/internal_summary.py |
| internal_summary.py | NativeSummary.initial_decision_context | episode function | task.py decide (execution_resource, launch library context) |
| internal_summary.py | NativeSummary.decision_context | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | NativeSummary._with_selected_execution_task | episode function | messages/internal_summary.py _selected_execution_task (scientific task now an optional assignment field: new field) |
| internal_summary.py | NativeSummary._resource_information | episode function | task.py _resource |
| internal_summary.py | NativeSummary.capabilities | episode function | task.py TOOLS (exec_command) |
| internal_summary.py | NativeSummary.resource_tool_contracts | unplaced | declares the launch, results and homology operation contracts of every resource of the parent routes; not this episode's |
| operations.py | NativeOperations | machinery | dispatch class |
| operations.py | NativeOperations._delegate | machinery | routing to the api or practical delegate |
| operations.py | NativeOperations._practical_context | machinery | identity context wrapper |
| operations.py | NativeOperations.initialize | machinery | practical state initialization and old parent-input check |
| operations.py | NativeOperations._check_parent_inputs | machinery | reads runtime_episodes to re-validate the parent launch assignment |
| operations.py | NativeOperations.state | machinery | the practical state is the job_access service's durable state |
| operations.py | NativeOperations.catalog | episode function | task.py EXEC_COMMAND |
| operations.py | NativeOperations.execute | episode function | task.py exec_command (through job_access: BLOCKED-ON-JOB-SERVICE) |
| parent_launch_contract.py | parent_launch_schema | machinery | parent launch assignment re-validation |
| received_information.py | ReceivedExecutionInformation | unplaced | forwarded report sources and facts for the roles annotation and gene_context_evidence; not launch_local's |
| received_information.py | ReceivedExecutionInformation._forwards_bvbrc_reports | unplaced | forwarded report sources and facts for the roles annotation and gene_context_evidence; not launch_local's |
| received_information.py | ReceivedExecutionInformation._forwards_minhash_reports | unplaced | forwarded report sources and facts for the roles annotation and gene_context_evidence; not launch_local's |
| received_information.py | ReceivedExecutionInformation.received_report_sources | unplaced | forwarded report sources and facts for the roles annotation and gene_context_evidence; not launch_local's |
| received_information.py | ReceivedExecutionInformation.received_report_facts | unplaced | forwarded report sources and facts for the roles annotation and gene_context_evidence; not launch_local's |
| received_information.py | ReceivedExecutionInformation.received_report_closure_facts | unplaced | forwarded report sources and facts for the roles annotation and gene_context_evidence; not launch_local's |
| received_record_selection.py | ReceivedRecordSelection | machinery | receipt-scoped selection class |
| received_record_selection.py | ReceivedRecordSelection._received | machinery | receipt-scoped selection of handoffs and results through the old job progress provider and receipts; custody is the system's, the handoff comes in the job_access reply |
| received_reference_custody.py | ReceivedReferenceCustody | machinery | receipt custody of received references and validation of received reports (results role) |
| received_reference_custody.py | ReceivedReferenceCustody.resolve_received_reference | machinery | receipt custody of received references and validation of received reports (results role) |
| received_reference_custody.py | ReceivedReferenceCustody.validate_received_report | machinery | receipt custody of received references and validation of received reports (results role) |
| received_reference_custody.py | ReceivedReferenceCustody.received_form_references | machinery | receipt custody of received references and validation of received reports (results role) |
| report_delivery.py | NativeReportDelivery | machinery | report delivery |
| report_delivery.py | NativeReportDelivery.finish | machinery | report form, release, saved forms (runtime_forms); messages/final_to_parent.py final_to_parent |
| report_reference_access.py | ReportReferenceAccess | machinery | custody resolver |
| report_reference_access.py | ReportReferenceAccess.resolve | machinery | resolver of references in the outgoing report (custody) |
| result_records.py | ExecutionResultRecords | unplaced | result-acquisition role (execution_result_acquisition): selectors, targets, windows, result bodies |
| result_records.py | ExecutionResultRecords._masking_selector | unplaced | result-acquisition role (execution_result_acquisition): selectors, targets, windows, result bodies |
| result_records.py | ExecutionResultRecords._masking_inputs | episode function | messages/read_from_parent.py ASSIGNMENT_FORM record_refs; the validation of the inputs (native_blast_masking_results.validate_job_inputs, old Store reads) is not carried (unplaced) |
| result_records.py | ExecutionResultRecords._retained_masking_target | unplaced | result-acquisition role (execution_result_acquisition): selectors, targets, windows, result bodies |
| result_records.py | ExecutionResultRecords._masking_reference_access | machinery | receipt custody of retained references |
| result_records.py | ExecutionResultRecords._utility_selector | unplaced | result-acquisition role (execution_result_acquisition): selectors, targets, windows, result bodies |
| result_records.py | ExecutionResultRecords._utility_inputs | episode function | messages/read_from_parent.py ASSIGNMENT_FORM record_refs; the validation of the inputs (native_blast_utility_results.validate_job_inputs, old Store reads) is not carried (unplaced) |
| result_records.py | ExecutionResultRecords._retained_utility_target | unplaced | result-acquisition role (execution_result_acquisition): selectors, targets, windows, result bodies |
| result_records.py | ExecutionResultRecords._utility_reference_access | machinery | receipt custody of retained references |
| result_records.py | ExecutionResultRecords._versions | machinery | check of the commission against the parent's immutable input versions |
| result_records.py | ExecutionResultRecords._target | unplaced | result-acquisition role (execution_result_acquisition): selectors, targets, windows, result bodies |
| result_records.py | ExecutionResultRecords._selector | unplaced | result-acquisition role (execution_result_acquisition): selectors, targets, windows, result bodies |
| result_records.py | ExecutionResultRecords._result_directory | unplaced | result-acquisition role (execution_result_acquisition): selectors, targets, windows, result bodies |
| result_records.py | ExecutionResultRecords._windows | unplaced | result-acquisition role (execution_result_acquisition): selectors, targets, windows, result bodies |
| result_records.py | ExecutionResultRecords._selected_result_action | unplaced | result-acquisition role (execution_result_acquisition): selectors, targets, windows, result bodies |
| result_records.py | ExecutionResultRecords._validate_result_body | unplaced | result-acquisition role (execution_result_acquisition): selectors, targets, windows, result bodies |
| result_records.py | ExecutionResultRecords._read_result | unplaced | result-acquisition role (execution_result_acquisition): selectors, targets, windows, result bodies |
| result_records.py | ExecutionResultRecords._selection | unplaced | result-acquisition role (execution_result_acquisition): selectors, targets, windows, result bodies |
| result_records.py | ExecutionResultRecords._context_target | machinery | receipt authentication of a handoff against the assignment |
| result_records.py | ExecutionResultRecords._has_appservice | unplaced | api resources only |
| result_records.py | ExecutionResultRecords._has_uniprot | unplaced | api resources only |
| result_records.py | ExecutionResultRecords._appservice_sources | unplaced | api resources only |
| saved_decision_exchange.py | NativeSavedDecisionExchange | machinery | saved-request and saved-history checks |
| saved_decision_exchange.py | NativeSavedDecisionExchange.validate_contract_exchange_request | machinery | saved-request and saved-history checks |
| saved_decision_exchange.py | NativeSavedDecisionExchange.validate_contract_exchange_history | machinery | saved-request and saved-history checks |
| task.py | NativeTask | machinery | the task class: the decision loop is the system's; its two episode functions are in task.py |
| task.py | NativeTask.next | machinery | the decision loop, restore, in-process replay, pending deliveries, source failure (system loop) |
| task.py | NativeTask.apply_response | episode function | task.py action (validation of the answer, rejection feedback); job_child, redelivery, contract-information and reads.map branches are not offered by this episode |
| task.py | NativeTask.execute | episode function | task.py exec_command; journaling, receipts and credit observation are machinery |
| task_state.py | NativeTaskState | machinery | task state, restore, checkpoint, record_effect |
| task_state.py | NativeTaskState.__init__ | machinery | task state, restore, checkpoint, record_effect |
| task_state.py | NativeTaskState.bind_execution_context | machinery | task state, restore, checkpoint, record_effect |
| task_state.py | NativeTaskState.record_execution_failure | machinery | a failed command is a receipt returned by the tool and enters the loop like any outcome |
| task_state.py | NativeTaskState.restore_checkpoint | machinery | task state, restore, checkpoint, record_effect |
| task_state.py | NativeTaskState.restore | machinery | task state, restore, checkpoint, record_effect |
| task_state.py | NativeTaskState.record_effect | machinery | task state, restore, checkpoint, record_effect |
| task_state.py | NativeTaskState.checkpoint | machinery | task state, restore, checkpoint, record_effect |
| terminal_assignment.py | TerminalAssignment | episode function | messages/read_from_parent.py |
| terminal_assignment.py | TerminalAssignment._assignment | episode function | task.py _operations (TerminalExecution.validate_assignment) |
| terminal_assignment.py | TerminalAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent |
| terminal_assignment.py | TerminalAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| terminal_contracts.py | operation_catalog | episode function | task.py EXEC_COMMAND |
| terminal_credit.py | TerminalCredit | episode function | credit.py |
| terminal_credit.py | TerminalCredit.credit_view | episode function | credit.py credit (library project_practical_credit over the receipts) |
| terminal_credit.py | TerminalCredit.completion_for_action | episode function | messages/internal_summary.py _completion |
| terminal_execution.py | TerminalExecutionBehavior | episode function | class of the terminal behaviour: composed into the episode files (see its methods) |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | episode function | settings (see configuration.py) |
| terminal_execution.py | TerminalExecutionBehavior.as_record | episode function | class of the terminal behaviour: composed into the episode files (see its methods) |
| terminal_execution.py | TerminalExecutionBehavior.child_roles | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | TerminalExecutionBehavior.credit_kind | episode function | class of the terminal behaviour: composed into the episode files (see its methods) |
| terminal_execution.py | TerminalExecutionBehavior.permitted_common_actions | episode function | class of the terminal behaviour: composed into the episode files (see its methods) |
| terminal_execution.py | TerminalExecutionBehavior.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | episode function | yield_estimator.py CompletionYieldController (target from read_from_parent) |
| terminal_goal.py | TerminalGoal | episode function | task.py |
| terminal_goal.py | TerminalGoal.instructions | episode function | task.py GOAL_INSTRUCTION, _instructions |
| terminal_goal.py | TerminalGoal._resource_instructions | episode function | task.py _instructions (library LaunchInstructions.for_resource) |
| terminal_operations.py | TerminalOperations | episode function | task.py |
| terminal_operations.py | TerminalOperations._operations | episode function | task.py _operations (library TerminalExecution) |
| terminal_operations.py | TerminalOperations.catalog | episode function | task.py EXEC_COMMAND |
| terminal_operations.py | TerminalOperations.execute | episode function | task.py exec_command (through job_access: BLOCKED-ON-JOB-SERVICE; the intent, executor, scientific command proof, validations and receipt are the service's) |
| terminal_report.py | TerminalReport | episode function | messages/final_to_parent.py |
| terminal_report.py | TerminalReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM |
| terminal_report.py | TerminalReport.facts | episode function | messages/final_to_parent.py _facts |
| terminal_report.py | TerminalReport.resolve | machinery | resolver of references in the outgoing report (custody) |
| terminal_report.py | TerminalReport.validate_report | episode function | messages/final_to_parent.py validate_report |
| terminal_state.py | TerminalState | machinery | the practical state is the job_access service's |
| terminal_state.py | TerminalState._state_directory | machinery | the practical state directory is the job_access service's durable state |
| terminal_state.py | TerminalState.initialize | episode function | messages/internal_summary.py (baseline validations: assess_validations over the initial context); the state directory is the service's |
| terminal_state.py | TerminalState.state | machinery | the practical state object is the job_access service's |
| terminal_summary.py | TerminalSummary | episode function | messages/internal_summary.py |
| terminal_summary.py | TerminalSummary.initial_decision_context | episode function | task.py decide (execution_resource) |
| terminal_summary.py | TerminalSummary._resource_information | episode function | task.py _resource |
| terminal_summary.py | TerminalSummary.decision_context | episode function | messages/internal_summary.py internal_summary (execution_progress, execution_completion) and task.py decide |
| to_parent.py | NativeReport | episode function | messages/final_to_parent.py |
| to_parent.py | NativeReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (the 21 dotted masking and utility sources cannot be form fields: contract misfit) |
| to_parent.py | NativeReport.facts | episode function | messages/final_to_parent.py final_to_parent |
| to_parent.py | NativeReport._live_facts | episode function | messages/final_to_parent.py _facts; the received handoffs come from the job_access reply |
| to_parent.py | NativeReport.validate_report | episode function | messages/final_to_parent.py validate_report (the results-role received-report validators are not applicable) |
| waiting.py | NativeWaiting | machinery | wait/suspension machinery |
| waiting.py | NativeWaiting.suspension_changed | machinery | wait/suspension machinery |
| yield_estimator.py | ExecutionEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | not carried: the per-request-class profile key; settings is one entry per binding path (contract misfit) |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | not carried: see _request_yield_class (settings cost and parameters) |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller (CompletionYieldController) |
| yield_estimator.py | ExecutionEpisodeYield._launch_local_yield_controller | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | practical estimator delegation (verify_completion as controller input); completion controller replaces it |
