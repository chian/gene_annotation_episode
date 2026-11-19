# a104/evolutionary_history_evidence/execution_job_submission/hpc_job_execution — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/execution_job_submission/hpc_job_execution/`
(63 Python files directly in the folder; no `grading/` or `scoring/` subfolder; `tests/` not read). Nothing from
the old shared root was read; `library.native_terminal_transport.TerminalExecution`, `practical_execution_state`,
`terminal_scientific_evidence` and `practical_receipt_information` are named only by what this episode asks of them.
Most files are copies of the launch parent's (marked "copy" below); the episode's own work is the `native_*.py`
terminal behaviour, `parent_launch_contract.py`, `parent_request_contracts.py`, `from_parent.py`, `episode.py`,
`completion.py`, `credit.py`, `to_parent.py`, `yield_estimator.py`.

Old binding: class `ExecutionEpisode`, `binding_path =
'evolutionary_history_evidence/execution_job_submission/hpc_job_execution'`, `commissioning_parent =
'evolutionary_history_evidence/execution_job_submission'`, old role `launch_hpc`, `entry_roles = ()` (never an entry),
`replaces_default_instructions = True`, version `execution_episode_v1` (terminal behaviour
`terminal_execution_episode_v1`). Decision source: `HPCExecutionTask`. Prompt renderer: `present_execution_context`
(copy).

## What this episode is for

It runs the assigned job on the assigned HPC resource by writing and running shell commands, one per turn, until the
original endpoint predicates are validated. In its own words (`native_goal.py`, the whole text, followed by the
frozen library's resource instructions for that resource when any):

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
> transfers, execution_resource.ssh_argv, when present, is the exact configured transport prefix. Append the remote
> shell command as its final argument and preserve stdin. The supplied configuration gives the existing connection
> details. target=resource uses that transport directly. The episode iterator decides continuation from credit; add
> no stopping budget.

## Task and instructions

- Permitted actions: `tool` only. No reason, wait, children or redelivery.
- Instructions: the text above replaces the defaults (`instructions.py`, same composer text as the launch parent's).
- `task_action.py`: no reasoning-commit branch; report update admitted for grain `launch_hpc`.

## What it reads from its parent's assignment

`from_parent.py`, `parent_request_contracts.py`, `parent_launch_contract.py`:

- Assignment form: when commissioned by `launch` under an `hpc` ancestor, a frozen `enum` of the parent's already
  authorised HPC requests ("A frozen HPC launch exposes only its already authorized request");
  otherwise `anyOf` the request schemas of the configured HPC resources with `resource_id` required.
- `prepare_assignment`: request validated (workspace confinement, operations validator); its resource kind must be
  `hpc`; the parent must be `launch`; the parent launch assignment (schema in `parent_launch_contract.py`) supplies
  `immutable_input_versions`; masking/utility and native BLAST database inputs validated.
- `_check_parent_inputs` repeats this before initialize and every execution, re-reading the parent launch assignment
  from `runtime_episodes` by path.
- Required returns: none.

## Children

None.

## Decision state and what it shows the model

- Context: the shared decision-context text; execution expectations captured for `launch_hpc`.
- Own block (`internal_summary.py` → `native_internal_summary.py`): `execution_assignment`, `execution_resource`
  (kind, workspace, and when configured kind, policy, account, `ssh_argv`, python executable, scheduler, inventory
  snapshot), `coordinator_workspace`, `execution_progress` (practical credit view), `execution_completion` (proof or
  null).
- Initial context: resource capabilities and initial information (copy of the parent's `resource_information.py`).

## Tools

`native_tool_contracts.py`, `native_tool_actions.py`: one tool, `exec_command` {`cmd` string or argv, `workdir`,
`target` resource|coordinator, `env`}, all but target required. Execution validates the arguments and the action
against the assignment, begins the operation in the practical state (an already completed key returns its receipt),
runs it, finalizes the scientific command outcome, records cwd/environment changes for resource commands inside the
workspace, assesses the endpoint validations, finishes the receipt and publishes it as a practical receipt source. A
failure becomes `execution_action_failed` inside the outcome.

## Credit

`credit.py`, `native_credit.py`: kind `operational`; closed view first, otherwise the practical state's credit view.
Completion: the practical state's completion proof; verification by the practical state.

## Continuation

`yield_estimator.py`: profile `task_yield_profiles['launch_hpc:<request class>']`; accumulation controller with the
practical estimator (verified completion → exact zero future credit).

## What it reports to its parent

`to_parent.py`, `native_return.py`: the launch fact set (handoffs, results, origin, BLAST HSPs, file sources, native
families) plus `practical_completed`, `practical_receipt_digests`, `practical_receipt_refs`; practical receipt refs
that are returnable handoffs matching this context join `execution_handoff_refs`; `execution_completed` is
`practical_completed`. Return fields must equal these facts.

## Differences from similar episodes

- Versus `api_job_execution`: tool only (no wait); one generic `exec_command` tool instead of service operations; the
  execution-agent instruction text; credit and completion from the practical receipt state; the frozen-request
  assignment form under an hpc ancestor.
- Versus the launch parent's `terminal_validation.py`: this episode owns its own split copy of the terminal behaviour
  (`native_*.py`) including goal, return facts, credit and completion, where the parent's copy has only the catalog,
  assignment, state and resolve parts.

## Files

Name abbreviations: `wf.X` = old `self.workflow.X` / `source.workflow.X` / `workflow.X`; `wf(self).X` = a parent-runtime function bound into the old workflow namespace using `self.X`; `BC.X` = old `BindingContext` field; `services.X` = old binding services; `SelectionView.X` = old selection view; `tbl:` = old journal/receipt/provider table; `imp:` = import from old `root.a104.<module>`; `lrf.` = `library.live_runtime_functions` rebinding into the old runtime namespace; bare names are old runtime/provider/numerical names. Counts are uses in that file. Full rows: `runs/carry_over/calls/a104_01.tsv`.

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | empty package marker | none |
| `action_outcome.py` | 5 | outcome envelope (copy) | none |
| `binding_record.py` | 9 | binding identity with binding_id .../hpc_job_execution | none |
| `binding_roles.py` | 6 | roles and kinds (copy) | none |
| `closed_credit.py` | 122 | closed operational credit (copy) | BC.as_record×2, BC.episode_id×8, BC.role×1, imp:communication×1, imp:episode_receipts×1, imp:episode_return_records×3, imp:execution_contracts×2, EpisodeReceipts×2, EpisodeReturnRecords×2, tbl:runtime_episodes×2, tbl:runtime_forms×3, tbl:runtime_observations×1, tbl:runtime_receipt_inheritance×2, tbl:runtime_record_receipts×2 |
| `completion.py` | 57 | completion and verification delegated to the terminal behaviour's practical state | BC.assignment×1, BC.episode_id×4, imp:communication×1, imp:episode_return_records×1, imp:execution_contracts×1, imp:method_loop.identities×1, imp:native_blast_database_acquisition×1, imp:native_blast_standard_database_acquisition×1, imp:numerical×1, imp:practical_execution_records×1, imp:practical_yield×1, ESTIMATOR_VERSION×2, NumericBand×2, UnitRef×2, tbl:runtime_observations×1 |
| `configuration.py` | 76 | constructor (copy) using this episode's own native_execution_service terminal behaviour | imp:a104_execution_bindings×4, imp:bvbrc_phylogeny_returns×1, imp:communication×1, imp:evolutionary_history_evidence.execution_progress_assessment.api_observer×1, imp:execution_contracts×1, imp:execution_progress×1, imp:library.api_record_access×1, imp:local_file_capture_results×1, imp:numerical×1, YieldController×3, YieldParameters×3 |
| `credit.py` | 28 | operational credit: closed view first, else the practical state's credit view | imp:communication×1 |
| `credit_records.py` | 3 | closed credit fact name | none |
| `decision_context.py` | 54 | decision context assembly (shared text) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, FACT_MEANINGS×1, FACT_SOURCES×1, _references_in×1, SelectionView.child_reports×2, SelectionView.controller_state×1, SelectionView.model_inputs×1, tbl:runtime_actions×2, wf.binding_context×2, wf.catalog×1, wf.controller_binding×1, wf.delivery_status×1, wf.extra_report_sources×1, wf.is_scientific_source×1, wf.job_episode_options×1, wf.journal×3, wf.knowledge×1, wf.local_outcome_preview×1, wf.pending_work×1, wf.receipt_projection×1, wf.run_id×1, wf.source_credit_binding×1, wf.source_credit_view×1, wf.specialist×1, wf.store×3, wf.tools×1, wf.working_state×1 |
| `decision_contracts.py` | 133 | exchange envelope and replay validation (shared text) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, apply_state_frame×1, composition_lookup_schema×2, CONTRACT_INFORMATION_OPERATIONS×1, DECISION_CONTEXT_VERSION×1, instructional_model_context×1, is_contract_information×1, model_snapshot×1, _references_in×1, requested_contract_information×1, WorkflowError×9, tbl:runtime_model_calls×1, wf.contract_information_reply×1, wf.decision_exchanges×2, wf.journal×1, wf.store×2, wf.validate_contract_information×2 |
| `decision_exchange.py` | 113 | request_context exchange loop (shared text) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, _action_generation_schema×1, _category_yield_parameters×1, child_option_information×1, DECISION_CONTEXT_VERSION×1, instructional_model_context×2, lookup_attempts×1, model_snapshot×1, requested_contract_information×1, state_frame×1, yield_table×1, tbl:runtime_model_calls×2, wf.controller_binding×1, wf.decision_exchanges×1, wf.execute×1, wf.journal×1, wf.run_id×1, wf.services×1, wf.validate_contract_information×1 |
| `decision_provider.py` | 60 | provider routing (shared text) | imp:providers×2, imp:runtime×1, imp:root.providers×1, _ORIGINAL_DECLARED_PRESENTATION×2, _ORIGINAL_MODEL_COMPLETE×3, _ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION×3, _ORIGINAL_MODEL_INSTANCE_DICT×4, wf.provider×1, wf.specialist×2 |
| `episode.py` | 47 | assembles the HPC binding; binding_path .../hpc_job_execution, commissioning_parent .../execution_job_submission, roles (launch_hpc,), entry_roles (); no children; tool actions only | imp:a104_homology_execution×1 |
| `from_parent.py` | 74 | assignment: frozen enum of already authorised HPC requests when commissioned by launch under an hpc ancestor, else anyOf HPC request schemas; prepare_assignment checks kind, parent launch, original launch versions and inputs; no required returns | BC.assignment×4, BC.path×2, BC.role×5, imp:communication×1, imp:execution_contracts×1, imp:native_blast_database_acquisition×1, imp:native_blast_database_result_publication×2, imp:native_blast_standard_database_acquisition×1, imp:native_blast_standard_database_result_publication×2, services.annotation_task_required×1 |
| `goal.py` | 7 | instructions come from the terminal behaviour (native_goal) | none |
| `instructions.py` | 36 | instruction composer (same text as the launch parent's) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime_prompt×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, DECISION_EXCHANGE_PROTOCOL×1, REASONING_COMMIT_REQUIREMENT×1, wf.binding_context×2, wf.decision_protocol×1, wf.is_job_source×1, wf.job_episodes×1, wf.knowledge×1, wf.launch_instructions×1, wf.native_event_information×1, wf.permits_common_action×3, wf.specialist×1 |
| `internal_summary.py` | 13 | own block from the terminal behaviour's decision context | BC.assignment×1, imp:communication×1 |
| `native_actions.py` | 17 | tool catalog and execution delegated to the terminal behaviour after checking parent inputs | imp:communication×1 |
| `native_assignment.py` | 26 | terminal assignment validation per role kind | BC.assignment×1, BC.role×1, imp:communication×1, imp:practical_execution_records×2 |
| `native_completion.py` | 12 | completion proof and practical estimator from the practical state | imp:practical_yield×1, PracticalYieldEstimator×2 |
| `native_configuration.py` | 27 | terminal behaviour constructor (local/hpc resources) and TerminalExecution operations | imp:communication×1, imp:library.native_terminal_transport×1, imp:terminal_scientific_evidence×1 |
| `native_credit.py` | 10 | operational credit from the practical state | none |
| `native_execution_service.py` | 22 | TerminalExecutionBehavior assembled from the native_* mixins; no children; tool only | none |
| `native_goal.py` | 18 | the execution-agent instruction text plus frozen resource instructions | BC.assignment×1, services.workflow×1 |
| `native_internal_summary.py` | 17 | terminal decision context: assignment, resource (kind, workspace, policy, account, ssh_argv, python, scheduler, inventory), coordinator workspace, progress, completion | BC.assignment×2, imp:communication×1 |
| `native_receipt_state.py` | 20 | practical state directory and initialization | BC.episode_id×4, BC.run_id×2, imp:library.native_terminal_transport×1, imp:practical_execution_records×1, imp:practical_execution_state×1 |
| `native_resource_contracts.py` | 4 | VERSION terminal_execution_episode_v1 and role kinds | none |
| `native_return.py` | 32 | fact sources and facts practical_completed, practical_receipt_digests, practical_receipt_refs; resolve; validate_report | BC.run_id×2, imp:communication×1, imp:library.native_terminal_transport×1, imp:practical_receipt_information×2 |
| `native_state.py` | 31 | initialize through the terminal behaviour after checking parent inputs; results directory | BC.assignment×1, BC.episode_id×2, BC.run_id×2, BC.scope×1, imp:communication×1, imp:execution_contracts×2, imp:practical_execution_state×2 |
| `native_tool_actions.py` | 50 | exec_command execution: validation, begin/finish practical state, finalize scientific command, cwd/env revision, validations, publishes a practical receipt | BC.assignment×5, BC.run_id×1, imp:acquisition×1, imp:communication×1, imp:domain×1, imp:library.native_terminal_transport×1, imp:practical_execution_records×1, imp:practical_receipt_information×1, imp:terminal_scientific_evidence×1 |
| `native_tool_contracts.py` | 8 | exec_command catalog | none |
| `parent_launch_contract.py` | 14 | the commissioning launch assignment schema | imp:a104_execution_bindings×1, imp:execution_contracts×1, imp:launch_instructions×1, imp:resource_records×1 |
| `parent_request_contracts.py` | 93 | _check_parent_inputs (re-reads the parent launch assignment), _permitted, request schema, _validate_request, _launch (from parent_launch_contract), constraints | BC.assignment×4, BC.path×3, BC.scope×1, imp:a104_execution_bindings×2, imp:a104_homology_execution×2, imp:communication×1, imp:execution_contracts×2, imp:native_blast_database_result_publication×1, imp:native_blast_standard_database_result_publication×1, imp:practical_execution_operations×1, imp:practical_execution_records×3, tbl:runtime_episodes×1 |
| `presentation.py` | 60 | presentation (copy) | imp:evolutionary_history_evidence_prompt×2, imp:library.hpc_prompt×1, imp:library.monitor_prompt×1, imp:native_profile_presentation×1, imp:providers×1, imp:receiver_prompt×1, apply_state_frame×3, DECISION_CONTEXT_VERSION×1, is_api_launch_context×2, is_published_scientific_context×2, _ordinary_runtime_receiver_context×1, render_api_launch_prompt×1, render_evolutionary_history_evidence_prompt×1, text_instructions×1 |
| `protected_reference_access.py` | 100 | protected readers (copy) | BC.assignment×4, imp:communication×1, imp:library.fluorescence_returns×1, imp:library.native_fluorescence_results×1, imp:library.native_protein_structure_results×1, imp:library.native_protein_structure_returns×1, imp:library.protein_structure_operands×1 |
| `receipt_selection.py` | 59 | receiver selection (copy) | BC.assignment×1, BC.episode_id×7, BC.role×1, BC.scope×2, imp:communication×1, imp:episode_receipts×1, EpisodeReceipts×2, services.record_selection×1, tbl:runtime_actions×1, tbl:runtime_receipt_inheritance×2 |
| `received_action_identity.py` | 26 | selected action identity (copy) | imp:communication×1, imp:execution_contracts×1, imp:practical_execution_state×2, tbl:runtime_actions×1 |
| `received_launch_records.py` | 3 | LAUNCH_VERSION (copy) | none |
| `received_parent_records.py` | 106 | received report sources/facts (copy) | BC.request×2, BC.role×10, imp:a104_homology_execution×1, imp:blast_pairwise_result_views×1, imp:blast_utility_result_views×1, imp:bvbrc_data_views×1, imp:bvbrc_homology_returns×1, imp:bvbrc_phylogeny_returns×1, imp:communication×1, imp:hmmer_preparation_result_views×1, imp:library.bvbrc_proteome_returns×1, imp:native_blast_database_result_views×1, imp:native_blast_standard_database_result_views×1, imp:sequence_masking_result_views×1, imp:uniprot_return_contracts×1 |
| `received_reference_access.py` | 109 | resolve_received_reference (copy) | BC.role×9, imp:a104_homology_execution×1, imp:blast_utility_result_views×1, imp:bvbrc_homology_returns×1, imp:bvbrc_phylogeny_returns×1, imp:communication×1, imp:library.bvbrc_proteome_returns×1, imp:sequence_masking_result_views×1 |
| `received_report_admission.py` | 94 | received report admission (copy) | BC.role×1, imp:a104_homology_execution×1, imp:communication×1, imp:hmmer_native_result_views×1 |
| `received_result_custody.py` | 62 | result custody (copy) | imp:communication×1, imp:domain×1, imp:execution_contracts×2, imp:local_file_capture_results×1, imp:practical_execution_state×1, tbl:runtime_episodes×1 |
| `report_delivery.py` | 32 | finish (shared text) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, form_with_facts×1, tbl:runtime_forms×2, wf.binding_context×2, wf.episode_bindings×1, wf.facts×1, wf.journal×2, wf.pending_handles×1, wf.release×2, wf.source_credit_view×1 |
| `report_fields.py` | 61 | fact_sources (copy, with own terminal behaviour) | imp:a104_homology_execution×2, imp:blast_pairwise_result_views×1, imp:blast_result_views×1, imp:blast_utility_result_views×1, imp:bvbrc_data_views×1, imp:communication×2, imp:execution_contracts×1, imp:hmmer_native_result_views×1, imp:hmmer_preparation_result_views×1, imp:local_file_capture_results×2, imp:native_blast_database_result_views×1, imp:native_blast_standard_database_result_views×1, imp:native_hmmer_acquisition×1, imp:practical_receipt_information×1, imp:sequence_masking_result_views×1, imp:uniprot_return_contracts×1 |
| `report_reference_access.py` | 139 | resolve (copy) | BC.role×13, BC.scope×4, imp:a104_homology_execution×2, imp:bvbrc_data_views×1, imp:bvbrc_homology_returns×1, imp:bvbrc_phylogeny_returns×1, imp:communication×2, imp:episode_bindings×2, imp:execution_contracts×1, imp:hmmer_preparation_result_views×1, imp:library.bvbrc_proteome_returns×1, imp:library.native_blast_database_result_records×1, imp:library.native_blast_standard_database_result_records×1, imp:local_file_capture_results×1, imp:practical_receipt_information×1, reference_in_context×4 |
| `resource_information.py` | 95 | resource information (copy, own exec_command catalog) | BC.role×1, imp:a104_execution_bindings×3, imp:execution_contracts×1, imp:library.bvbrc_proteome_tool_info×1 |
| `resource_operations.py` | 7 | execution.capabilities catalog (copy) | imp:execution_contracts×1 |
| `result_operations.py` | 10 | native result operations (copy) | imp:execution_contracts×1 |
| `result_records.py` | 9 | result constants (copy) | imp:execution_contracts×1 |
| `retained_native_receipts.py` | 19 | _delegate, practical context, and state() for resource roles | BC.assignment×1, BC.role×2, imp:communication×1 |
| `schema_fields.py` | 6 | schema constants (copy) | none |
| `scientific_inputs.py` | 14 | input validation (copy) | imp:library.execution_input_versions×1 |
| `selector_contracts.py` | 80 | selector validation (copy) | imp:blast_pairwise_result_views×1, imp:blast_utility_result_views×1, imp:execution_contracts×1, imp:hmmer_native_result_views×1, imp:hmmer_preparation_result_views×1, imp:local_file_capture_results×1, imp:native_blast_acquisition×1, imp:native_blast_database_acquisition×1, imp:native_blast_database_result_views×1, imp:native_blast_masking_acquisition×1, imp:native_blast_standard_database_acquisition×1, imp:native_blast_standard_database_result_views×1, imp:native_blast_utility_acquisition×1, imp:native_hmmer_acquisition×1, imp:native_hmmer_preparation_acquisition×1, imp:practical_execution_operations×1, imp:sequence_masking_result_views×1 |
| `selector_records.py` | 7 | native selector schema (copy) | imp:execution_contracts×1 |
| `target_custody.py` | 52 | target custody (copy) | BC.assignment×3, BC.role×3, BC.scope×6, imp:a104_homology_execution×1, imp:communication×1, imp:execution_contracts×2 |
| `task.py` | 97 | decision-source next() (shared text) | imp:root.a104×1, imp:episode_source_failure×1, imp:library.live_runtime_functions×1, imp:providers×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, ModelCallError×2, record_source_failure×2, SourceEnd×2, WorkflowError×1, SelectionView.units_consumed×4, tbl:runtime_actions×2, tbl:runtime_episodes×1, tbl:runtime_model_calls×1, wf.action_schema×1, wf.completed_unit×3, wf.completions×2, wf.delivery_resolution_inputs×1, wf.execution_binding×2, wf.inprocess_replay×4, wf.journal×4, wf.next_return×1, wf.resolve_pending_deliveries×1, wf.run_id×1, wf.selected×2, wf.store×3 |
| `task_action.py` | 149 | action admission without the reasoning-commit branch (grain launch_hpc) and execution | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:read_mapping×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, ActionFailure×1, _decode_recorded_action_response×1, observes_action_outcome×1, ReportRedelivery×2, _wait_target_feedback×2, WorkflowError×1, tbl:runtime_actions×6, tbl:runtime_model_calls×1, wf.automatic_score_updates×1, wf.binding_context×2, wf.completions×1, wf.controller_value×2, wf.decision_exchanges×3, wf.execute×1, wf.execution_binding×5, wf.journal×3, wf.last_observed_credit×1, wf.pending_work×1, wf.perform_selected_wait×1, wf.permits_common_action×1, wf.receive_native_outcome×1, wf.receive_outcome×1, wf.resolver×1, wf.retain_shared_grading_results×1, wf.run_id×2, wf.selected×1, wf.source_credit_view×1, wf.specialist×1, wf.store×5, wf.validate_report×1 |
| `task_decision.py` | 154 | decision call (execution expectations for launch_hpc) | imp:root.a104×1, imp:episode_work_report×2, imp:library.hpc_prompt×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, _action_generation_schema×1, _ASSIGNMENT_TRANSPORT×1, child_option_information×1, completed_action_reports×3, DECISION_EXCHANGE_PROTOCOL×5, instructional_model_context×1, _recorded_assignment_transport×1, requested_action_history×3, WorkflowError×5, tbl:runtime_model_calls×5, wf.available_child_roles×1, wf.binding_context×4, wf.contract_information_profile×1, wf.decision_exchanges×1, wf.decision_protocol×3, wf.episode_bindings×1, wf.execution_expectations×1, wf.freeze_contract_information×1, wf.freeze_literature_numerical_contracts×1, wf.history_preview×1, wf.is_job_source×3, wf.job_episodes×4, wf.journal×1, wf.launch_instructions×2, wf.native_estimation_context×1, wf.native_event_information×2, wf.numerical_contracts×1, wf.pending_work×1, wf.permits_common_action×1, wf.provider×2, wf.receipts×4, wf.resource_context×1, wf.resource_estimator×5, wf.services×1, wf.shared_information_context×1, wf.store×2, wf.uses_received_record_context×2, wf.validate_contract_information×2, wf.waiting_support×1 |
| `task_state.py` | 117 | source state (shared text) | imp:root.a104×1, imp:episode_source_failure×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, ActionLeaf×1, EFFECT_VERSION×1, Episode.identity×1, record_source_failure×2, tbl:runtime_actions×5, wf.archive×1, wf.completions×4, wf.context×1, wf.controller_value×1, wf.execution_binding×4, wf.grains×1, wf.inprocess_replay×7, wf.journal×5, wf.progress_provider×2, wf.recover_commissions×1, wf.run_id×1, wf.source_credit_view×1, wf.store×2 |
| `to_parent.py` | 84 | facts: launch facts plus the terminal behaviour's practical facts; practical receipt refs that are returnable handoffs join execution_handoff_refs; execution_completed is practical_completed | BC.scope×1, imp:a104_homology_execution×2, imp:blast_pairwise_result_views×1, imp:blast_utility_result_views×1, imp:communication×2, imp:execution_contracts×1, imp:hmmer_native_result_views×1, imp:hmmer_preparation_result_views×1, imp:library.native_blast_database_result_records×1, imp:library.native_blast_standard_database_result_records×1, imp:local_file_capture_results×1, imp:practical_receipt_information×1, imp:sequence_masking_result_views×1, imp:uniprot_return_contracts×1 |
| `waiting.py` | 9 | suspension notice | wf.execution_backend×1, wf.execution_handle×2 |
| `yield_estimator.py` | 49 | task profile key launch_hpc:<request class>; accumulation controller with the practical (verified completion) estimator | BC.assignment×1, BC.role×1, imp:communication×1, imp:numerical×1, imp:practical_yield×1, PracticalYieldEstimator×2, YieldController×2, YieldParameters×2 |
