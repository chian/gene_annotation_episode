# a103/gene_context_evidence/execution_job_submission/local_job_execution — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/execution_job_submission/local_job_execution/<file>`
(only files directly in this folder; no `grading/` or `scoring/` subfolder; `tests/` not covered).
Old binding class: `ExecutionEpisode` (`binding_path = 'gene_context_evidence/execution_job_submission/local_job_execution'`,
`commissioning_parent = 'gene_context_evidence/execution_job_submission'`, `roles = ('launch_local',)`,
`entry_roles = ()` — reached only through a Launch parent), decision source `NativeTask`, prompt presentation
`present_native_task`, `replaces_default_instructions = True`. Contract version `execution_episode_v1`; terminal
behaviour version `terminal_execution_episode_v1`.

## What it is for (its goal, in its own words)

`goal.py` delegates to the assigned resource's `TerminalExecutionBehavior`; `terminal_goal.py`:

> You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the
> shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery from the
> actual resource instructions and observed results. No sequence of setup or job-stage operations is prescribed.
> Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical inventory is context,
> not proof of present usability. Each command is one ordinary episode action: its actual result and earned credit
> enter the iterator, including failure or zero progress. Host bookkeeping records command versions and actual native
> job identities; do not maintain a parallel receipt ledger. If a submission outcome is uncertain, investigate that
> original submission rather than create a duplicate. Use the provided resource-specific instructions, account,
> storage and existing authentication route. workdir and env apply to the selected command only. target=resource runs
> on the assigned resource; target=coordinator runs in the local run directory for supplied-input and transport work.
> Both are ordinary journaled actions; resource computation belongs on its actual allocation. For coordinator-side
> transfers, execution_resource.ssh_argv, when present, is the exact configured transport prefix. ... The episode
> iterator decides continuation from credit; add no stopping budget.

followed by "Resource instructions supplied from the frozen library:" and the selected sections of the launch
instruction library for this resource.

## Task and instructions

`instructions.py`: goal + `REASONING_COMMIT_REQUIREMENT` when reason is permitted (it is not: actions are tool only)
+ tool knowledge + launch library + repair paragraph + wait/native event paragraphs when permitted; under
decision_exchange_v1 the old history guidance is replaced by the exchange-history sentence. The task is the old
iterator copied with grain `'launch_local'` plus: reason-action execution path, job_child failure feedback,
`component_native_return_channels_required` repair feedback, `reads.map` parameter feedback, automatic score
updates after non-wait actions, shared grading retention after `shared.read_information`.
`decision_presentation.present_native_task` chooses the text prompt renderer from the state frame.

## What it reads from its parent's assignment

`from_parent.assignment_schema('launch_local')`: anyOf one concrete request per configured resource of kind local —
practical assignment schema with `resource_id` const, `resource_kind` const, and `requested_job` anyOf generic or the
resource's native job schemas (native_blast, masking, utility, database, standard database, hmmer, hmmer preparation)
and preparation schemas. `prepare_assignment` requires the parent role to be `launch`, re-reads the parent's launch
assignment, validates masking/utility inputs, immutable input versions and native/standard BLAST DB job inputs, and
the workspace confinement. `operations._check_parent_inputs` repeats this before initialize/execute.
`required_return_sources` returns `()` in every branch.

## Children it may commission

None (`child_roles = ()`, `allowed_children = ()`).

## Decision state and what it shows the model

Common decision state plus `is_scientific_source`; `initial_decision_context`: `execution_resource_capabilities`,
`execution_initial_information`, `received_bvbrc_values` (and BLAST jobs/MinHash for annotation receivers);
`decision_context`: terminal summary — `execution_assignment`, `execution_resource` (kind, workspace, policy, account,
ssh_argv, python_executable, scheduler, inventory snapshot), `coordinator_workspace`, `execution_progress` (practical
state credit view), `execution_completion` (proof) — plus `selected_execution_task` (scientific question and selected
tool info from the scientific parent, requests with job and resource). Decision inputs add shared information
context, HPC requested action history, job-source resource estimates.

## Tools it offers

`exec_command` only (`terminal_contracts.operation_catalog`): `cmd` (string or argv), `workdir`, `env`, `target`
(resource | coordinator). Each command: validated, begun/finished in the practical state, scientific command
finalized, validations assessed, practical receipt Source published. Failures return a failed native outcome inside a
completed receipt. Common actions: tool.

## How its credit is counted

`credit_kind = 'operational'`. `project_credit`: the saved closed view if the episode closed with one
(`closed_credit.py`, never re-projected), else the matching native result family's credit view, else the terminal
practical state's `credit_view()` (validated endpoint progress). Units come from configuration (`handoff_unit`,
`acquired_record_unit`).

## Continuation

Only with `require_private_yield`: `task_yield_profiles['launch_local:' + request class]` (class from
`_request_yield_class`: e.g. `practical_local_native_blast_handoff`) → `YieldController(cutoff,
YieldParameters(**parameters), estimate_with_context=PracticalYieldEstimator(verify_completion))`. New-layout
estimator: **completion with a target** (verified assignment endpoint). Settings per request class: `cutoff` (> 0),
`parameters`.

## What it reports to its parent

`to_parent.fact_sources`: native result family sources, masking/utility/BLAST DB/HMMER prep/BLAST sources,
BV-BRC/MinHash/AppService sources, terminal sources for launch_local (`practical_completed`,
`practical_receipt_digests`, `practical_receipt_refs`), `execution_handoff_refs`, `execution_result_refs`,
`execution_completed`, `execution_result_origin`, `execution_blast_hsps`. Live facts for launch_local come from the
terminal delegate plus received handoffs from its own practical receipts; closed credit facts are added at closure.
`validate_report`: fact-sourced fields must equal recorded (or frozen UniProt) facts.

## Differences from siblings / similar episodes

- Shares about 25 files nearly verbatim with execution_result_acquisition (closed credit, configuration, reference
  custody, report reference access, exchange split files); its terminal behaviour is split into `terminal_*.py`
  while results carries a single-file `terminal_execution.py`.
- Goal delegates to the terminal behaviour; results has its own goal text.
- `required_return_sources` is empty here; results returns `('execution_result_refs',)` under an annotation task.
- Uses `present_native_task` (renders any text task); results' provider uses presentation only for
  selected-execution contexts.
- No entry role; actions are tool only (results adds wait for API services).
- Its results/launch credit and fact branches for roles other than launch_local (results, annotation receivers) are
  carried in its copies but only launch_local is its own role.

## File by file
| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `action_policy.py` | 9 | Common actions: tool only. | none |
| `binding_record.py` | 9 | Binding descriptor: resources, initial_information, handoff_unit, acquired_record_unit, log window bytes/roles, require_private_yield, results/task yield profiles. | none |
| `child_eligibility.py` | 10 | No children. | none |
| `closed_credit.py` | 117 | Closed operational credit: capture the projected credit once at closure, pin the receipt prefix; later reads return only that saved view. | EpisodeReceipts, EpisodeReturnRecords, import:episode_receipts, import:episode_return_records×3, runtime_episodes×2, runtime_forms×3, runtime_observations, runtime_receipt_inheritance×2, runtime_record_receipts×2 |
| `completion.py` | 65 | Completion proof per action (native result families, else delegate to terminal state); verify_completion, reusing a recorded endpoint verdict for closed episodes. | import:episode_return_records, import:method_loop.identities, import:numerical, import:practical_yield, runtime_observations |
| `configuration.py` | 65 | Settings: resources (kinds local/pbs_ssh/hmmer_api/api), initial_information, tool_registry, handoff_unit and acquired_record_unit (> 0), log_window_bytes, log_roles, require_private_yield, results_yield_profiles (native_unbounded_local/hpc), task_yield_profiles; builds a TerminalExecutionBehavior per non-API resource, APIServiceExecution, progress provider, local file sources and result readers. | import:api_service_execution, import:execution_progress, import:numerical |
| `contracts.py` | 60 | Versions, ROLES, KINDS, ROLE_KINDS, schemas (results, native selector, origin), launch and native result operation catalogs, outcome helper. | import:a103_execution_bindings, import:a103_homology_execution, import:communication, import:domain, import:execution_contracts, import:gene_context_evidence.execution_job_submission.local_job_execution.terminal_execution, import:launch_instructions, import:local_file_capture_results, import:native_blast_acquisition, import:native_blast_database_acquisition, import:native_blast_masking_acquisition, import:native_blast_standard_database_acquisition, import:native_blast_utility_acquisition, import:native_hmmer_acquisition, import:native_hmmer_preparation_acquisition, import:practical_execution_operations, import:practical_execution_records, import:practical_execution_state, import:practical_receipt_information, import:resource_records |
| `credit.py` | 39 | Credit kind 'operational'; closed view if saved, else the matching native result family's credit view, else the terminal state's credit view. | none |
| `decision_contracts.py` | 36 | Split copy of the decision exchange envelope (request_context vs select_action) and lookup schema. | import:root.a103, import:runtime, runtime.composition_lookup_schema×2, runtime.Draft202012Validator, runtime._object×3 |
| `decision_delivery.py` | 82 | Old decision call (freeze literature numerical contracts; receipts except job sources). | import:root.a103, import:runtime, runtime._action_generation_schema, runtime._ASSIGNMENT_TRANSPORT, runtime.DECISION_EXCHANGE_PROTOCOL×5, runtime._digest, runtime.instructional_model_context, runtime._json×4, runtime.json×2, runtime_model_calls×5, runtime._recorded_assignment_transport, runtime.WorkflowError×5, workflow.contract_information_profile, workflow.decision_exchanges, workflow.decision_protocol×3, workflow.freeze_contract_information, workflow.freeze_literature_numerical_contracts, workflow.history_preview, workflow.is_job_source×2, workflow.journal, workflow.numerical_contracts, workflow.provider, workflow.receipts×4, workflow.services, workflow.uses_received_record_context×2, workflow.validate_contract_information×2 |
| `decision_exchange.py` | 116 | Split copy of the exchange loop (lookups of own attempts, child options, composition information while one decision is pending). Own intent: lookups create no completed action. | import:root.a103, import:runtime, runtime._action_generation_schema, runtime._category_yield_parameters, runtime.child_option_information, runtime.DECISION_CONTEXT_VERSION, runtime.instructional_model_context×2, runtime._json×2, runtime.lookup_attempts, runtime.Mapping×3, runtime_model_calls×2, runtime.model_snapshot, runtime._plain×2, runtime._references_in, runtime.requested_contract_information, runtime.schema_failure_diagnostic×2, runtime.sqlite3, runtime.state_frame, runtime.ValidationError×4, runtime.yield_table, workflow.controller_binding, workflow.decision_exchanges, workflow.execute, workflow.journal, workflow.run_id, workflow.services, workflow.store×2, workflow.validate_contract_information |
| `decision_inputs.py` | 70 | Copy of decision inputs for role 'launch_local' plus shared_information_context, requested_action_history (HPC), job-source resource estimates. | import:episode_work_report×2, import:library.hpc_prompt, import:root.a103, import:runtime, runtime.child_option_information, runtime.Mapping, workflow.available_child_roles, workflow.binding_context×2, workflow.episode_bindings, workflow.execution_expectations, workflow.is_job_source, workflow.job_episodes×4, workflow.launch_instructions×2, workflow.native_estimation_context, workflow.native_event_information×2, workflow.pending_work, workflow.permits_common_action, workflow.resource_context, workflow.resource_estimator×5, workflow.shared_information_context, workflow.store×2, workflow.waiting_support |
| `decision_presentation.py` | 59 | Provider presentation: choose a text prompt renderer (hpc, published scientific, api launch, selected execution, monitor, receiver) from the reconstructed state frame. | import:gene_context_evidence_prompt, import:library.hpc_prompt, import:library.monitor_prompt, import:native_profile_presentation, import:providers, import:receiver_prompt, import:root.a103, providers.apply_state_frame×3, providers.DECISION_CONTEXT_VERSION, providers.deepcopy, providers.is_api_launch_context×2, providers.is_published_scientific_context×2, providers.json, providers._ordinary_runtime_receiver_context, providers.render_api_launch_prompt, providers.render_gene_context_evidence_prompt, providers.text_instructions |
| `decision_provider.py` | 18 | Provider dispatch with this episode's prompt renderer and conversation key. | import:runtime, workflow.provider×2, workflow.specialist |
| `decision_state.py` | 45 | Copy of the old decision-state assembler: goal, scope, visible refs, current credit, evidence vector, pending work, last outcome, feedback, report deliveries, controller state, tools, tool knowledge, job options, available report facts, requested report form/purpose, current report update and basis; then the binding's own decision_context. Own intent: what the model is shown each decision. | import:root.a103, import:runtime, runtime_actions×2, runtime.FACT_MEANINGS, runtime.FACT_SOURCES, runtime.json×2, runtime.Mapping×3, runtime._plain×2, runtime._references_in, workflow.binding_context, workflow.catalog, workflow.controller_binding, workflow.delivery_status, workflow.extra_report_sources, workflow.is_scientific_source, workflow.job_episode_options, workflow.journal×3, workflow.knowledge, workflow.local_outcome_preview, workflow.pending_work, workflow.receipt_projection, workflow.run_id, workflow.source_credit_binding, workflow.source_credit_view, workflow.specialist, workflow.store×3, workflow.tools, workflow.working_state |
| `episode.py` | 31 | Wires launch_local: path gene_context_evidence/execution_job_submission/local_job_execution, commissioning parent execution_job_submission, role 'launch_local', no entry roles, task NativeTask, present_native_task renderer, replaces default instructions. | none |
| `from_parent.py` | 125 | Assignment: concrete per-resource request of kind local (practical_assignment schema with requested_job alternatives); must come from a 'launch' parent; validate masking/utility inputs, immutable input versions, native/standard BLAST database job inputs. Initial references for launch/launch_local/results roles. | import:native_blast_database_result_publication×2, import:native_blast_standard_database_result_publication×2 |
| `goal.py` | 7 | Goal comes from the delegated terminal behaviour (terminal_goal.py). | none |
| `__init__.py` | 0 | Package marker; no intent. | none |
| `instructions.py` | 22 | Instruction composition: goal + reasoning commit requirement + tool knowledge + launch library + repair, wait, native event; exchange-protocol history replacement. | import:root.a103, import:runtime_prompt, runtime_prompt.DECISION_EXCHANGE_PROTOCOL, runtime_prompt.INSTRUCTIONS×3, runtime_prompt.REASONING_COMMIT_REQUIREMENT, workflow.binding_context, workflow.decision_protocol, workflow.knowledge, workflow.launch_instructions, workflow.native_event_information, workflow.permits_common_action×3, workflow.specialist |
| `internal_summary.py` | 121 | Initial decision context (resource capabilities, initial information, received BV-BRC values, BLAST jobs, MinHash); decision context from the terminal delegate plus selected_execution_task from the scientific parent; capabilities; resource tool contracts. | import:native_profile_presentation |
| `operations.py` | 48 | Delegate to the terminal behaviour for the assigned resource; re-check the parent Launch inputs before initialize/execute. | import:native_blast_database_result_publication, import:native_blast_standard_database_result_publication, runtime_episodes |
| `received_information.py` | 113 | Report fact sources/facts forwarded for annotation/gene_context_evidence receivers. | import:blast_pairwise_result_views, import:blast_utility_result_views, import:bvbrc_data_views, import:bvbrc_minhash_views, import:hmmer_preparation_result_views, import:native_blast_database_result_views, import:native_blast_standard_database_result_views, import:sequence_masking_result_views, import:uniprot_return_contracts |
| `received_record_selection.py` | 35 | Received handoffs and result bodies from known refs. | none |
| `received_reference_custody.py` | 160 | Receiver-side reference resolution, received report validation and admitted form references for all result families. | import:bvbrc_homology_returns, import:hmmer_native_result_views |
| `report_delivery.py` | 25 | Copy (common). | import:library.private_policy_call, import:library.report_fact_assembly, import:root.a103, import:runtime, runtime_forms×2, runtime.form_with_facts, runtime._json×2, runtime.json, runtime.Record×2, workflow.binding_context, workflow.episode_bindings, workflow.facts, workflow.journal×2, workflow.pending_handles, workflow.release×2, workflow.source_credit_view |
| `report_reference_access.py` | 115 | Outgoing-report reference resolution across all result families; failures deny. | import:bvbrc_data_views, import:bvbrc_homology_returns, import:episode_bindings×2, import:hmmer_preparation_result_views, import:native_blast_database_results, import:native_blast_standard_database_results |
| `result_records.py` | 260 | Result target/selector/window/receipt validation, result body reading, receiver selection, context target checks. | EpisodeReceipts, import:blast_pairwise_result_views, import:blast_utility_result_views×2, import:bvbrc_homology_returns, import:episode_receipts, import:execution_input_versions, import:hmmer_native_result_views, import:hmmer_preparation_result_views, import:native_blast_database_result_views, import:native_blast_standard_database_result_views, import:sequence_masking_result_views×2, runtime_actions×2, runtime_episodes, runtime_receipt_inheritance×2 |
| `saved_decision_exchange.py` | 82 | Split copy of saved-exchange authentication against the old journal; replay-only, no own intent. | import:root.a103, import:runtime, runtime.apply_state_frame, runtime.CONTRACT_INFORMATION_OPERATIONS, runtime.DECISION_CONTEXT_VERSION, runtime.instructional_model_context, runtime.is_contract_information, runtime._json×8, runtime.json, runtime_model_calls, runtime.model_snapshot, runtime._recorded_action_generation_schema, runtime.requested_contract_information, runtime.ValidationError, runtime.WorkflowError×9, workflow.contract_information_reply, workflow.decision_exchanges×2, workflow.journal, workflow.validate_contract_information×2 |
| `task.py` | 226 | Copy of task step with grain 'launch_local', reason action, job_child failure feedback, reads.map parameter feedback, automatic score updates, shared grading retention. | import:episode_source_failure, import:library.action_contracts, import:library.private_policy_call, import:providers, import:read_mapping, import:root.a103, import:runtime, runtime.AcquisitionError×2, runtime.ActionFailure, runtime_actions×8, runtime.ContractError×2, runtime.ContractInformationError, runtime._decode_recorded_action_response, runtime.Draft202012Validator×2, runtime_episodes, runtime.EventTargetError×2, runtime.inspect, runtime._json×5, runtime.json×8, runtime.Mapping×9, runtime_model_calls×2, runtime.nullcontext×5, runtime.observes_action_outcome, runtime._plain, runtime.ReportBoundaryError, runtime.ReportRedelivery×2, runtime.schema_failure_diagnostic, runtime.SourceEnd×2, runtime.sqlite3×2, runtime.subprocess×2, runtime.validate_form, runtime.ValidationError×3, runtime._wait_target_feedback×2, runtime.WorkflowError×2, workflow.action_schema, workflow.automatic_score_updates, workflow.binding_context, workflow.completed_unit×3, workflow.completions×3, workflow.controller_value×2, workflow.decision_exchanges×3, workflow.delivery_resolution_inputs, workflow.execute, workflow.execution_binding×7, workflow.inprocess_replay×4, workflow.journal×7, workflow.last_observed_credit, workflow.next_return, workflow.pending_work, workflow.perform_selected_wait, workflow.permits_common_action, workflow.receive_native_outcome, workflow.receive_outcome, workflow.resolve_pending_deliveries, workflow.resolver, workflow.retain_shared_grading_results, workflow.run_id×3, workflow.selected×3, workflow.source_credit_view, workflow.specialist, workflow.store×8, workflow.validate_report |
| `task_state.py` | 108 | Copy (common). | import:episode_source_failure, import:root.a103, import:runtime, runtime.ActionLeaf, runtime_actions×5, runtime.EFFECT_VERSION, runtime.Episode, runtime.interpretation_schema, runtime._json×2, runtime.json×4, runtime._object, runtime._plain, runtime.Record, workflow.archive, workflow.completions×4, workflow.context, workflow.controller_value, workflow.execution_binding×4, workflow.grains, workflow.inprocess_replay×7, workflow.journal×5, workflow.progress_provider×2, workflow.recover_commissions, workflow.run_id, workflow.source_credit_view, workflow.store×2 |
| `terminal_assignment.py` | 22 | Terminal assignment validation by resource kind. | none |
| `terminal_contracts.py` | 24 | exec_command tool (cmd, workdir, target resource\|coordinator, env). | import:acquisition, import:communication, import:domain, import:practical_execution_operations, import:practical_execution_records, import:practical_execution_state, import:terminal_execution |
| `terminal_credit.py` | 11 | Terminal credit view and completion proof from the practical state. | none |
| `terminal_execution.py` | 41 | TerminalExecutionBehavior composition and practical_estimator (PracticalYieldEstimator). | import:practical_yield |
| `terminal_goal.py` | 18 | Goal text (quoted in the doc) + resource-specific instructions from the frozen launch library. | none |
| `terminal_operations.py` | 47 | exec_command execution: validate, begin/finish in practical state, finalize scientific command, assess validations, publish a practical receipt Source. | import:practical_receipt_information, import:terminal_scientific_evidence×2 |
| `terminal_report.py` | 31 | Facts practical_completed, practical_receipt_digests, practical_receipt_refs; validation. | import:practical_receipt_information×2 |
| `terminal_state.py` | 18 | Practical state per episode (initial validations). | none |
| `terminal_summary.py` | 16 | Decision context: assignment, resource, coordinator workspace, execution progress (credit view), completion. | none |
| `to_parent.py` | 132 | Fact sources (handoff refs, result refs, completed, result origin, BLAST HSPs, practical receipts for launch_local) and live/closed facts; validate_report. | import:blast_pairwise_result_views×2, import:blast_result_views, import:blast_utility_result_views×2, import:bvbrc_data_views, import:bvbrc_minhash_views, import:hmmer_native_result_views×2, import:hmmer_preparation_result_views×2, import:local_file_capture_results, import:native_blast_database_results, import:native_blast_database_result_views, import:native_blast_standard_database_results, import:native_blast_standard_database_result_views, import:native_hmmer_acquisition, import:sequence_masking_result_views×2, import:uniprot_return_contracts×2 |
| `waiting.py` | 9 | Suspension hook (common). | workflow.execution_backend, workflow.execution_handle×2 |
| `yield_estimator.py` | 50 | Completion-with-target: task_yield_profiles['launch_local:'+request class] (cutoff, parameters) with PracticalYieldEstimator over verify_completion. | import:numerical, import:practical_yield |

Usage counts per name and file: `runs/carry_over/calls/a103_02.tsv`.

## Carried over

Carried 19 November 2026 into the ten-file form (no children: no msg_to_child.py or read_from_child.py). One row per old function, class and method (`runs/carry_over/functions/...local_job_execution.tsv`). "library candidate": the function stays in the episode file that uses it. Machinery is not carried (reason given).

| old file | kind | name | class | new place or machinery reason |
|---|---|---|---|---|
| action_policy.py | class | NativeActionPolicy | machinery | the old loop's permitted common actions (the action policy ('tool',)); the system's decide/action produce only tool or child units |
| action_policy.py | method | NativeActionPolicy.permitted_common_actions | machinery | the old loop's permitted common actions (the action policy ('tool',)); the system's decide/action produce only tool or child units |
| binding_record.py | class | NativeBindingRecord | machinery | binding_record.py and the binding's own as_record() (README 3e) |
| binding_record.py | method | NativeBindingRecord.as_record | machinery | binding_record.py and the binding's own as_record() (README 3e) |
| child_eligibility.py | class | NativeChildEligibility | episode function | task.py CHILD_SLOTS = {} (no children) |
| child_eligibility.py | method | NativeChildEligibility.child_roles | episode function | task.py CHILD_SLOTS = {} (no children) |
| child_eligibility.py | method | NativeChildEligibility.allowed_children | episode function | task.py CHILD_SLOTS = {} (no children) |
| closed_credit.py | class | ClosedExecutionCredit | machinery | closed credit view rebuilt from receipts and the journal of an earlier closed run (runtime_* table re-validation, recorded-run replay) |
| closed_credit.py | method | ClosedExecutionCredit._closed_credit_carrier | machinery | closed credit view rebuilt from receipts and the journal of an earlier closed run (runtime_* table re-validation, recorded-run replay) |
| closed_credit.py | method | ClosedExecutionCredit._closed_credit_receipts | machinery | closed credit view rebuilt from receipts and the journal of an earlier closed run (runtime_* table re-validation, recorded-run replay) |
| closed_credit.py | method | ClosedExecutionCredit._closed_credit_value | machinery | closed credit view rebuilt from receipts and the journal of an earlier closed run (runtime_* table re-validation, recorded-run replay) |
| closed_credit.py | method | ClosedExecutionCredit._closed_credit_facts | machinery | closed credit view rebuilt from receipts and the journal of an earlier closed run (runtime_* table re-validation, recorded-run replay) |
| closed_credit.py | method | ClosedExecutionCredit._closed_operational_credit_view | machinery | closed credit view rebuilt from receipts and the journal of an earlier closed run (runtime_* table re-validation, recorded-run replay) |
| completion.py | class | ExecutionCompletion | machinery | class shell |
| completion.py | method | ExecutionCompletion.completion_for_action | machinery | completion proof as a controller packet (estimator packet, not a controller input in the new system); the proof is read in messages/internal_summary.py::_completion |
| completion.py | method | ExecutionCompletion._closed_completion_verdict | machinery | re-reads runtime_observations of the old journal (README 3d: reading earlier controller records) |
| completion.py | method | ExecutionCompletion.verify_completion | episode function | messages/internal_summary.py::_completion (the verified completion of the assignment's endpoint, over held receipts); library candidate |
| configuration.py | class | NativeConfiguration | machinery | NativeConfiguration.__init__ values: the run's settings (ctx.settings / settings: resource, coordinator_workspace, launch_instructions_directory, tool_knowledge_directory, task_yield_profiles); YieldController/YieldParameters construction replaced by yield_estimator.py |
| configuration.py | method | NativeConfiguration.__init__ | machinery | NativeConfiguration.__init__ values: the run's settings (ctx.settings / settings: resource, coordinator_workspace, launch_instructions_directory, tool_knowledge_directory, task_yield_profiles); YieldController/YieldParameters construction replaced by yield_estimator.py |
| contracts.py | function | launch_operation_catalog | episode function | not this episode's: the catalogue of the parent 'launch' role (execution.capabilities); not carried here, see unplaced_old_functions |
| contracts.py | function | native_result_operation_catalog | episode function | not this episode's: the catalogue of the 'results' role (execution.results.*); not carried here, see unplaced_old_functions |
| contracts.py | function | _outcome | machinery | old tool outcome envelope (status/record_refs/feedback); the new tool returns its outcome and an invalid answer is a Rejected in task.py::action |
| credit.py | class | ExecutionEpisodeCredit | machinery | class shell |
| credit.py | method | ExecutionEpisodeCredit.credit_kind | machinery | credit kind label 'operational' of the old credit view |
| credit.py | method | ExecutionEpisodeCredit.project_credit | episode function | credit.py::credit |
| credit.py | method | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py::credit (the practical branch; the native family result branches belong to the results role) |
| credit.py | method | ExecutionEpisodeCredit.credit_view | episode function | credit.py::credit |
| decision_contracts.py | class | NativeDecisionContracts | machinery | decision-exchange loop (exchange_decision schema and response) |
| decision_contracts.py | method | NativeDecisionContracts.exchange_schema | machinery | decision-exchange loop (exchange_decision schema and response) |
| decision_contracts.py | method | NativeDecisionContracts.exchange_response | machinery | decision-exchange loop (exchange_decision schema and response) |
| decision_delivery.py | class | NativeDecisionDelivery | machinery | decision-exchange loop (delivery of a decision, conversation continuation) |
| decision_delivery.py | method | NativeDecisionDelivery.call | machinery | decision-exchange loop (delivery of a decision, conversation continuation) |
| decision_delivery.py | method | NativeDecisionDelivery.instructions | machinery | decision-exchange loop (delivery of a decision, conversation continuation) |
| decision_exchange.py | class | NativeDecisionExchange | machinery | decision-exchange loop (exchange_decision, interpretation_context) |
| decision_exchange.py | method | NativeDecisionExchange.interpretation_context | machinery | decision-exchange loop (exchange_decision, interpretation_context) |
| decision_exchange.py | method | NativeDecisionExchange.exchange_decision | machinery | decision-exchange loop (exchange_decision, interpretation_context) |
| decision_inputs.py | class | NativeDecisionInputs | episode function | task.py::decide (context keys launch_instruction_library, selected_launch_instructions); the planning expectations, resource estimator, native event, waiting and completed-work branches do not apply to launch_local (wait/redelivery machinery or other roles) and are not carried |
| decision_inputs.py | method | NativeDecisionInputs.decision_inputs | episode function | task.py::decide (context keys launch_instruction_library, selected_launch_instructions); the planning expectations, resource estimator, native event, waiting and completed-work branches do not apply to launch_local (wait/redelivery machinery or other roles) and are not carried |
| decision_presentation.py | function | present_native_task | episode function | task.py::_task_text and decide (the selected-execution prompt over the summary) |
| decision_provider.py | class | NativeDecisionProvider | machinery | provider dispatch and conversation key of the old decision loop |
| decision_provider.py | method | NativeDecisionProvider.conversation_key | machinery | provider dispatch and conversation key of the old decision loop |
| decision_provider.py | method | NativeDecisionProvider.complete_decision | machinery | provider dispatch and conversation key of the old decision loop |
| decision_state.py | class | NativeDecisionState | machinery | old decision-state snapshot over the journal and workflow store; replaced by messages/internal_summary.py::internal_summary |
| decision_state.py | method | NativeDecisionState.decision_state | machinery | old decision-state snapshot over the journal and workflow store; replaced by messages/internal_summary.py::internal_summary |
| episode.py | class | ExecutionEpisode | episode function | episode.py::LocalJobExecution |
| from_parent.py | class | NativeAssignment | episode function | messages/read_from_parent.py (class shell) |
| from_parent.py | method | NativeAssignment.child_assignment_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM |
| from_parent.py | method | NativeAssignment.assignment_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM |
| from_parent.py | method | NativeAssignment._permitted | episode function | not this episode's: resource permission test of the parent launch's requests (role launch); not carried, see unplaced_old_functions |
| from_parent.py | method | NativeAssignment.prepare_assignment | episode function | messages/read_from_parent.py::read_from_parent (validate_assignment); the masking, utility, input-version and native job input checks are unplaced (modules not in the library, commission checks) |
| from_parent.py | method | NativeAssignment._request_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM (one field per property of ASSIGNMENT_SCHEMA) |
| from_parent.py | method | NativeAssignment._validate_request | episode function | messages/read_from_parent.py::read_from_parent (validate_assignment) and task.py::_operations (the resource's own validate_assignment with workspace confinement, in action) |
| from_parent.py | method | NativeAssignment._launch | machinery | re-validation of the commissioner's launch contract read from runtime_episodes |
| from_parent.py | method | NativeAssignment._constraints | machinery | part of the launch contract re-validation (_launch) |
| from_parent.py | method | NativeAssignment.required_return_sources | machinery | returns () for this role: the old runner's required return sources; the child declares its return form |
| from_parent.py | method | NativeAssignment.initial_references | episode function | messages/read_from_parent.py ASSIGNMENT_FORM record_refs field (the masking and utility input references); computing them through _masking_inputs/_utility_inputs is unplaced |
| goal.py | class | NativeGoal | episode function | goal.py / task.py::GOAL_INSTRUCTION (class shell) |
| goal.py | method | NativeGoal.instructions | episode function | task.py::GOAL_INSTRUCTION (from terminal_goal, unchanged) |
| instructions.py | function | instructions | episode function | task.py::_instructions (goal text, tool knowledge and launch library text, the resource's frozen launch instructions); reasoning, pending-delivery, wait/native-event and exchange-protocol spans are dropped (actions that no longer exist) |
| internal_summary.py | class | NativeSummary | episode function | messages/internal_summary.py (class shell) |
| internal_summary.py | method | NativeSummary.initial_decision_context | episode function | messages/internal_summary.py::internal_summary and task.py::_resource/decide (execution_resource_capabilities of this resource); the received BLAST/BVBRC/minhash branches belong to other roles |
| internal_summary.py | method | NativeSummary.decision_context | episode function | messages/internal_summary.py::internal_summary |
| internal_summary.py | method | NativeSummary._with_selected_execution_task | episode function | messages/internal_summary.py::_selected_execution_task (scientific task from the new parent-input field scientific_task); library candidate |
| internal_summary.py | method | NativeSummary._resource_information | episode function | task.py::_resource |
| internal_summary.py | method | NativeSummary.capabilities | episode function | not this episode's: configured operation availability across all resources for the root's catalogue; not carried, see unplaced_old_functions |
| internal_summary.py | method | NativeSummary.resource_tool_contracts | episode function | not this episode's: the declaration of every bound launch/results/homology operation for the parent; not carried, see unplaced_old_functions |
| operations.py | class | NativeOperations | machinery | class shell of delegation |
| operations.py | method | NativeOperations._delegate | machinery | role dispatch to the practical resource operations |
| operations.py | method | NativeOperations._practical_context | machinery | identity wrapper of the old context |
| operations.py | method | NativeOperations.initialize | machinery | state initialization of the old practical state (file-backed PracticalState) |
| operations.py | method | NativeOperations._check_parent_inputs | machinery | re-validation of the parent's saved launch request from runtime_episodes (old-runner table); its input checks are listed in unplaced_old_functions |
| operations.py | method | NativeOperations.state | machinery | file-backed practical state of the old runner |
| operations.py | method | NativeOperations.catalog | episode function | task.py::TOOLS / EXEC_COMMAND |
| operations.py | method | NativeOperations.execute | episode function | task.py::exec_command (through the job_access service, BLOCKED-ON-JOB-SERVICE) |
| received_information.py | class | ReceivedExecutionInformation | machinery | bookkeeping of received reports (bvbrc/minhash forwarding, received report facts) for the old report path; custody and receipts are the system's |
| received_information.py | method | ReceivedExecutionInformation._forwards_bvbrc_reports | machinery | bookkeeping of received reports (bvbrc/minhash forwarding, received report facts) for the old report path; custody and receipts are the system's |
| received_information.py | method | ReceivedExecutionInformation._forwards_minhash_reports | machinery | bookkeeping of received reports (bvbrc/minhash forwarding, received report facts) for the old report path; custody and receipts are the system's |
| received_information.py | method | ReceivedExecutionInformation.received_report_sources | machinery | bookkeeping of received reports (bvbrc/minhash forwarding, received report facts) for the old report path; custody and receipts are the system's |
| received_information.py | method | ReceivedExecutionInformation.received_report_facts | machinery | bookkeeping of received reports (bvbrc/minhash forwarding, received report facts) for the old report path; custody and receipts are the system's |
| received_information.py | method | ReceivedExecutionInformation.received_report_closure_facts | machinery | bookkeeping of received reports (bvbrc/minhash forwarding, received report facts) for the old report path; custody and receipts are the system's |
| received_record_selection.py | class | ReceivedRecordSelection | machinery | receipts bookkeeping (_received: handoffs and results the episode received) |
| received_record_selection.py | method | ReceivedRecordSelection._received | machinery | receipts bookkeeping (_received: handoffs and results the episode received) |
| received_reference_custody.py | class | ReceivedReferenceCustody | machinery | reference custody of received records (resolve/validate received references): the system's custody |
| received_reference_custody.py | method | ReceivedReferenceCustody.resolve_received_reference | machinery | reference custody of received records (resolve/validate received references): the system's custody |
| received_reference_custody.py | method | ReceivedReferenceCustody.validate_received_report | machinery | reference custody of received records (resolve/validate received references): the system's custody |
| received_reference_custody.py | method | ReceivedReferenceCustody.received_form_references | machinery | reference custody of received records (resolve/validate received references): the system's custody |
| report_delivery.py | class | NativeReportDelivery | machinery | report_form delivery (finish): the system admits the return form |
| report_delivery.py | method | NativeReportDelivery.finish | machinery | report_form delivery (finish): the system admits the return form |
| report_reference_access.py | class | ReportReferenceAccess | machinery | reference resolution of a report against the recorder and receipts: the system's custody |
| report_reference_access.py | method | ReportReferenceAccess.resolve | machinery | reference resolution of a report against the recorder and receipts: the system's custody |
| result_records.py | class | ExecutionResultRecords | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._masking_selector | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._masking_inputs | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._retained_masking_target | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._masking_reference_access | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._utility_selector | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._utility_inputs | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._retained_utility_target | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._utility_reference_access | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._versions | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._target | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._selector | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._result_directory | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._windows | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._selected_result_action | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._validate_result_body | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._read_result | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._selection | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._context_target | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._has_appservice | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._has_uniprot | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._appservice_sources | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| saved_decision_exchange.py | class | NativeSavedDecisionExchange | machinery | decision-exchange loop (saved exchange checks) |
| saved_decision_exchange.py | method | NativeSavedDecisionExchange.validate_contract_exchange_request | machinery | decision-exchange loop (saved exchange checks) |
| saved_decision_exchange.py | method | NativeSavedDecisionExchange.validate_contract_exchange_history | machinery | decision-exchange loop (saved exchange checks) |
| task.py | class | NativeTask | episode function | task.py::decide and action (class shell) |
| task.py | method | NativeTask.next | episode function | task.py::decide (context and request for the model) |
| task.py | method | NativeTask.apply_response | episode function | task.py::action (the answer names exec_command and valid operands, or Rejected) |
| task.py | method | NativeTask.execute | episode function | task.py::exec_command and the lookup tools |
| task_state.py | class | NativeTaskState | machinery | old task state (journal-backed) |
| task_state.py | method | NativeTaskState.__init__ | machinery | old task state (journal-backed) |
| task_state.py | method | NativeTaskState.bind_execution_context | machinery | old task state (journal-backed) |
| task_state.py | method | NativeTaskState.record_execution_failure | machinery | record_execution_failure: a tool's failure is its returned outcome |
| task_state.py | method | NativeTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | method | NativeTaskState.restore | machinery | checkpoint/restore |
| task_state.py | method | NativeTaskState.record_effect | machinery | effect record of the old journal (the system's attempts journal) |
| task_state.py | method | NativeTaskState.checkpoint | machinery | checkpoint/restore |
| terminal_assignment.py | class | TerminalAssignment | episode function | messages/read_from_parent.py |
| terminal_assignment.py | method | TerminalAssignment._assignment | episode function | task.py::_operations / messages/read_from_parent.py::read_from_parent |
| terminal_assignment.py | method | TerminalAssignment.prepare_assignment | episode function | messages/read_from_parent.py::read_from_parent (validate_assignment) and task.py::_operations |
| terminal_assignment.py | method | TerminalAssignment.assignment_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM |
| terminal_contracts.py | function | operation_catalog | episode function | task.py::EXEC_COMMAND (the exec_command catalogue entry, unchanged) |
| terminal_credit.py | class | TerminalCredit | episode function | credit.py::credit (practical credit over the receipts) |
| terminal_credit.py | method | TerminalCredit.credit_view | episode function | credit.py::credit (practical credit over the receipts) |
| terminal_credit.py | method | TerminalCredit.completion_for_action | machinery | completion proof as a controller packet; see messages/internal_summary.py::_completion |
| terminal_execution.py | class | TerminalExecutionBehavior | machinery | composition class shell of the terminal behaviour |
| terminal_execution.py | method | TerminalExecutionBehavior.__init__ | machinery | resources/initial_information held by the old composition: now settings (resource, coordinator_workspace) |
| terminal_execution.py | method | TerminalExecutionBehavior.as_record | machinery | the binding's own as_record() |
| terminal_execution.py | method | TerminalExecutionBehavior.child_roles | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | method | TerminalExecutionBehavior.credit_kind | machinery | credit kind label |
| terminal_execution.py | method | TerminalExecutionBehavior.permitted_common_actions | machinery | action policy |
| terminal_execution.py | method | TerminalExecutionBehavior.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | method | TerminalExecutionBehavior.practical_estimator | machinery | PracticalYieldEstimator provider (estimate_with_context); the controller is yield_estimator.py (completion) |
| terminal_goal.py | class | TerminalGoal | episode function | task.py::GOAL_INSTRUCTION and goal.py GOAL |
| terminal_goal.py | method | TerminalGoal.instructions | episode function | task.py::GOAL_INSTRUCTION and goal.py GOAL |
| terminal_goal.py | method | TerminalGoal._resource_instructions | episode function | task.py::_instructions (resource instructions from the frozen launch library, LaunchInstructions.for_resource) |
| terminal_operations.py | class | TerminalOperations | episode function | task.py::exec_command |
| terminal_operations.py | method | TerminalOperations._operations | episode function | task.py::_operations (TerminalExecution of the resource); library candidate |
| terminal_operations.py | method | TerminalOperations.catalog | episode function | task.py::EXEC_COMMAND |
| terminal_operations.py | method | TerminalOperations.execute | episode function | task.py::exec_command (job_access service, BLOCKED-ON-JOB-SERVICE); the invalid-argument branch is task.py::action (Rejected) |
| terminal_report.py | class | TerminalReport | episode function | messages/final_to_parent.py |
| terminal_report.py | method | TerminalReport.fact_sources | episode function | messages/final_to_parent.py::RETURN_FORM (practical_completed, practical_receipt_digests, practical_receipt_refs) |
| terminal_report.py | method | TerminalReport.facts | episode function | messages/final_to_parent.py::_facts |
| terminal_report.py | method | TerminalReport.resolve | machinery | reference resolution of a report against receipts: the system's custody |
| terminal_report.py | method | TerminalReport.validate_report | episode function | messages/final_to_parent.py::validate_report |
| terminal_state.py | class | TerminalState | machinery | file-backed PracticalState directory and initialization of the old runner; the baseline is messages/internal_summary.py (assess_validations over the initial context), the receipts are tool outcomes |
| terminal_state.py | method | TerminalState._state_directory | machinery | file-backed PracticalState directory and initialization of the old runner; the baseline is messages/internal_summary.py (assess_validations over the initial context), the receipts are tool outcomes |
| terminal_state.py | method | TerminalState.initialize | machinery | file-backed PracticalState directory and initialization of the old runner; the baseline is messages/internal_summary.py (assess_validations over the initial context), the receipts are tool outcomes |
| terminal_state.py | method | TerminalState.state | machinery | file-backed PracticalState directory and initialization of the old runner; the baseline is messages/internal_summary.py (assess_validations over the initial context), the receipts are tool outcomes |
| terminal_summary.py | class | TerminalSummary | episode function | messages/internal_summary.py |
| terminal_summary.py | method | TerminalSummary.initial_decision_context | episode function | messages/internal_summary.py::internal_summary and task.py::decide |
| terminal_summary.py | method | TerminalSummary._resource_information | episode function | task.py::_resource |
| terminal_summary.py | method | TerminalSummary.decision_context | episode function | messages/internal_summary.py::internal_summary |
| to_parent.py | class | NativeReport | episode function | messages/final_to_parent.py |
| to_parent.py | method | NativeReport.fact_sources | episode function | messages/final_to_parent.py::RETURN_FORM (every old fact source of launch_local under its old name; the execution.<name> masking and utility sources are not form field names: contract misfit) |
| to_parent.py | method | NativeReport.facts | episode function | messages/final_to_parent.py::_facts |
| to_parent.py | method | NativeReport._live_facts | episode function | messages/final_to_parent.py::_facts (practical branch; handoff references are the receipts that handed a job off) |
| to_parent.py | method | NativeReport.validate_report | episode function | messages/final_to_parent.py::validate_report |
| waiting.py | class | NativeWaiting | machinery | wait/suspension machinery (suspension_changed; unused by this role) |
| waiting.py | method | NativeWaiting.suspension_changed | machinery | wait/suspension machinery (suspension_changed; unused by this role) |
| yield_estimator.py | class | ExecutionEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | method | ExecutionEpisodeYield._request_yield_class | episode function | yield_estimator.py::request_yield_class; library candidate |
| yield_estimator.py | method | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py::task_yield_profile; library candidate |
| yield_estimator.py | method | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py::yield_controller |
| yield_estimator.py | method | ExecutionEpisodeYield._launch_local_yield_controller | episode function | yield_estimator.py::yield_controller (CompletionYieldController, README 7b) |
| yield_estimator.py | method | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator provider; replaced by the completion controller |
