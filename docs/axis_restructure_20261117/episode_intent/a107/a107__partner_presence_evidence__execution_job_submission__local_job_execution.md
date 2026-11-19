# A107 `partner_presence_evidence/execution_job_submission/local_job_execution`

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/execution_job_submission/local_job_execution/<file>`
(29 files directly in the folder, about 2,160 lines; this episode has no `grading/`, `scoring/` or `tests/` subfolder).
Old code is the source of intention only. Every old-runner name listed below belongs to the deleted per-axis runner.

## Purpose (its own words)

`binding_path = 'partner_presence_evidence/execution_job_submission/local_job_execution'`,
`commissioning_parent = 'partner_presence_evidence/execution_job_submission'`, `roles = ('launch_local',)`, `entry_roles = ()`
(it cannot be entered directly; only the Launch parent commissions it).

The intent comes from `TerminalExecutionBehavior.instructions` (terminal_execution.py). `goal.py` delegates to it, and
`replaces_default_instructions = True`:

> You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the shell
> code needed for that job. Choose scripts, environment preparation, software invocation and recovery from the actual
> resource instructions and observed results. No sequence of setup or job-stage operations is prescribed. Preserve the
> caller's scientific inputs, desired outputs and acceptance criteria. Historical inventory is context, not proof of present
> usability. Each command is one ordinary episode action: its actual result and earned credit enter the iterator, including
> failure or zero progress. ... If a submission outcome is uncertain, investigate that original submission rather than create
> a duplicate. ... target=resource runs on the assigned resource; target=coordinator runs in the local run directory for
> supplied-input and transport work. ... The episode iterator decides continuation from credit; add no stopping budget.

The library's resource-specific sections (`launch_instructions.for_resource(resources[kind])`) are appended as
"Resource instructions supplied from the frozen library".

Module docstring (execution_contracts.py): "One explicit launch family for the shared episode loop. The binding routes a
selected concrete assignment. Resource operations and result reads contain no model, resource selection or investigation loop."

## Task and instructions

- Instruction composer: `task_instructions.instructions(source, context)`. It starts from the old shared
  `runtime_prompt.INSTRUCTIONS` (or `job_episodes.instructions` for a job source). Because `replaces_default_instructions` is
  True, the specialist's terminal-execution text replaces it. It then appends tool knowledge, the launch instruction library
  text and the `pending_child_delivery` repair paragraph. Under the decision-exchange protocol it swaps the history guidance
  for "Use request_context exchanges ... episode.history tool, view=records".
- The prompt renderer is `presentation.present_context`, which dispatches on the context kind. It uses the HPC prompt,
  the partner-presence scientific prompt (`render_partner_presence_evidence_prompt` from the parent A107 `task_decision`), the API launch
  prompt, the RNA comparison/structure prompts, the selected-execution prompt or the monitor prompt. Other contexts are dumped as JSON.
  The renderer keeps `provider.scientific_prompt_states` per `(episode_id, role)` for bootstrap, update and lookup-result frames.

## What it reads from the parent's assignment

`assignment_schema('launch_local')` is the `anyOf` over the local resources. For each resource it is
`ASSIGNMENT_SCHEMA` (practical_assignment_v1) with `resource_id` const, `resource_kind` const 'local' and
`requested_job` = `anyOf[GENERIC_REQUESTED_JOB_SCHEMA, requested_job_schemas(...), expression_nmf / rna_structure / infernal /
infernal_preparation tool schemas, preparation_job_schemas]`.
`prepare_assignment` requires `parent.role == 'launch'`. It checks that the resource kind matches the role and re-validates the parent's original
launch assignment (`_launch`). It validates the masking/utility inputs, the `immutable_input_versions` (`_versions`) and the
native BLAST database / standard BLAST database / RNA structure job inputs against the Store.
`initial_references` collects RNA-structure, masking, utility and expression-NMF input refs from the assignment.
`initialize` → `_check_parent_inputs`. It reads the parent's original `runtime_episodes.request` by path and re-checks the same inputs.

## Children

None: `child_roles()` and `allowed_children()` return `()`.

## Decision state shown to the model

- The generic old snapshot (`internal_summary.native_decision_snapshot`) contains the goal, scope, working_state,
  visible_record_refs, current_credit, credit_binding, time_accounting, pending_work, last_local_outcome, feedback,
  visual_evidence, report_deliveries, controller, tools, tool_knowledge, job_episode_options, available_report_facts,
  requested_report_purpose/form and current_report_update/basis.
- Its own `decision_context`: the terminal behaviour's `{execution_assignment, execution_resource (workspace, kind, policy,
  account, ssh_argv, python_executable, scheduler, inventory_snapshot), coordinator_workspace, execution_progress
  (PracticalState.credit_view), execution_completion (completion_proof)}`. `_with_selected_execution_task` adds
  `selected_execution_task` (version selected_execution_task_v1) when `services.scientific_parent_task(context)` returns the
  parent's `scientific_question` and `selected_tool_info`. That task records the chosen native job (exactly one of native_blast/masking/
  utility/database/standard_database/hmmer/hmmer_preparation/expression_nmf, with NMF and profile jobs reduced to their scientific view),
  the endpoint, the constraints and the resource information.
- `initial_decision_context` → `{'execution_resource_information': initial_information}`. The private
  `initial_information.py` reads `catalog.readers(binding_path)` for resource and received-API information.

## Tools offered

- `catalog` → `operation_catalog('local')` from `library.execution_operation_information` (exec_command style terminal
  operations). `permitted_common_actions` → `('tool',)` only.
- `execute`: validates the arguments and assignment, then `PracticalState.begin(operation_key)` and `TerminalExecution.execute`. Any
  ValueError/TypeError/OSError/AcquisitionError becomes a recorded failure outcome. After that come `finalize_scientific_command` and
  `assess_validations` with cwd/env revision tracking, then `state.finish`. The receipt is published as a `PracticalReceiptInformation` source.
  An invalid call returns `status:'invalid'` (it still enters the iterator).
- `resource_tool_contracts()` declares, for every bound resource (api/local/hpc), the launch and results operations with
  `invocation_route` commission routes, plus native, preparation, NMF, RNA, Infernal and homology-API contracts. This is the parent-visible
  contract list. It is identical to the copy in execution_result_acquisition.

## Credit

`credit_kind` → 'operational'. `project_credit` returns the original closed view (`_closed_operational_credit_view`) when it
exists. Otherwise it returns the live `TerminalExecutionBehavior.credit_view` = `PracticalState.credit_view()` (the receipt/validation
progress of the practical assignment). The closed-credit machinery authenticates a captured view against `runtime_episodes`
(state yielded, completion, archive), `runtime_observations`, `runtime_record_receipts`/`runtime_receipt_inheritance`
manifests and `runtime_forms` facts (`execution_closed_operational_credit_v1`). Credit is not clamped.
`handoff_unit`/`acquired_record_unit` must be finite and > 0 (they are used by the result/API credit paths).

## Continuation

`yield_controller` requires `require_private_yield=True`. It classifies the request with `_request_yield_class`:
`practical_local_<native_*...>_<handoff|outputs>`, `api_<service>[_algorithm][_database]_handoff` or `compact_<version>`.
It then takes `task_yield_profiles['launch_local:'+class]` = `{cutoff, parameters}` and builds
`YieldController(epoch, initial_credit, cutoff, YieldParameters(**parameters), estimate_with_context=PracticalYieldEstimator(verify_completion))`.
In the new layout this is "completion with a target": the target is the verified assignment endpoint
(`completion_for_action` / `verify_completion`, `practical_completion_v1`, with expected_next_gain exactly 0 once verified).
Settings: the per-request-class cutoff and parameters. A missing profile raises
`execution_original_task_yield_profile_required:<key>`.

## Report to parent

`fact_sources` (library received_result_readers) plus the terminal behaviour's `practical_completed`,
`practical_receipt_digests` and `practical_receipt_refs`. `facts` = live facts + the closed-credit snapshot:
- Empty native families (HMMER, masking, BLAST utility, RNA comparison, NMF, RNA structure, Infernal preparation, Infernal,
  standard BLAST database, BLAST database, HMMER preparation and BLAST pairwise sources), then the practical facts, then
  `execution_handoff_refs` (receipts read back through `job_progress_provider.targets._handoff_reader()` and checked by
  `_context_target`), `bvbrc_appservice_support_refs` (if appservice), `execution_blast_hsps: []`, `execution_result_refs`,
  `execution_file_source_refs`, `execution_file_capture_outcomes`, `execution_result_origin` (NATIVE_RESULT_ORIGIN when windows
  were read) and `execution_completed`.
- `validate_report` runs every native returns adapter, UniProt/Rfam, `validate_form` and then the rule that recorded fact fields must equal the facts
  (`execution_report_disagrees_with_recorded_facts`).
- `required_return_sources` returns `()` (unlike execution_result_acquisition, which requires `execution_result_refs` for an
  annotation-task scientific parent).

## Differences from siblings

- Same `configuration.py`, `binding_record.py` and `resource_information.py` as execution_result_acquisition (the same configuration
  operands: resources, initial_information, tool_registry, handoff/acquired units, log window/roles, private yield,
  results/task yield profiles). It differs in role (`launch_local` vs `results`), in delegating execution and credit to
  `TerminalExecutionBehavior` (shell-command practical state) instead of native result readers, and in its yield key.
- Its old `task.py` keeps the generic reason branch, job_child failure feedback, `automatic_score_updates` and
  `retain_shared_grading_results`. The monitor and HPC copies removed those, although only `tool` is permitted here.
- `task_instructions.py` uses the old shared `runtime_prompt.INSTRUCTIONS`. execution_result_acquisition inlines that text and adds the
  reasoning-commit and wait guidance.

## File by file

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | none | none |
| binding_record.py | 8 | binding record id and configuration fields | none |
| completion.py | 51 | completion delegated to the practical state; closed verdict reused only from a recorded verified endpoint | table `runtime_observations`; `episode_return_records._same`, `method_loop.identities.UnitRef`, `numerical.NumericBand`, `practical_yield.ESTIMATOR_VERSION`; `self.store.db` SQL |
| configuration.py | 119 | operand validation; allowed native families; local-only NMF/RNA/Infernal; builds TerminalExecutionBehavior, APIServiceExecution, ExecutionProgressProvider, LocalFileSourceResults and result readers | `numerical.YieldController/YieldParameters` (profile validation); `services.read_received_molecular_input` |
| credit.py | 136 | operational credit; closed-credit capture and replay | tables `runtime_episodes`, `runtime_observations`, `runtime_receipt_inheritance`, `runtime_record_receipts`, `runtime_forms`; `episode_receipts.EpisodeReceipts`, `episode_return_records.EpisodeReturnRecords/_same` |
| episode.py | 103 | class composition, binding path, roles, no children, `('tool',)` | imports from `runtime` (FACT_MEANINGS, FACT_SOURCES, Mapping, _plain, _references_in), `communication.plain/validate_form`, many old shared-root `a107.*` and `a107.library.*` modules |
| execution_contracts.py | 57 | VERSION, ROLES, KINDS, ROLE_KINDS, NATIVE_RESULT_ORIGIN, native result operation catalog (status/collect/read) | `communication.plain/validate_form`; old shared-root `execution_contracts`, `practical_execution_*`, `a107_execution_bindings` and others |
| from_parent.py | 113 | concrete per-resource launch_local schema; prepare_assignment checks | `library.execution_request_compatibility.launch_assignment_schema` (old shared root) |
| goal.py | 6 | delegates to the terminal instructions | none |
| initial_information.py | 9 | private initial information through catalog readers | `catalog.readers` (old reader catalog) |
| internal_summary.py | 88 | `selected_execution_task` view | `native_decision_snapshot`: self.workflow.{store(3), journal(3), working_state, run_id, local_outcome_preview, source_credit_view, source_credit_binding, pending_work, delivery_status, controller_binding, catalog, knowledge, job_episode_options, extra_report_sources, specialist, binding_context, tools}; table `runtime_actions`; `_live_original_runtime.*`; `services.scientific_parent_task` |
| presentation.py | 74 | context-kind prompt dispatch | `decision_context.VERSION/apply_state_frame`; `_live_original_providers.*` (12 names); `provider.scientific_prompt_states` |
| received_api_reports.py | 4 | selects own API reader authority | `catalog.configured/received` |
| received_execution_information.py | 4 | selects own result readers | `catalog.configured/received` |
| received_records.py | 127 | `_context_target` custody (BLAST-grader query sha check), `_received` handoff/result selection, `initial_references` | `self.store.read_snapshot`, `job_progress_provider.targets._handoff_reader` |
| resource_information.py | 70 | parent-visible resource tool contracts | none (old shared-root contract helpers) |
| science.py | 57 | masking/utility/NMF/version input checks; `_check_parent_inputs` | table `runtime_episodes` (parent request by path) |
| state.py | 19 | initialize → parent input check → practical delegate | none |
| task.py | 225 | none (generic old runner loop) | self.workflow.{journal(7), inprocess_replay(4), execution_binding(7), completions(3), completed_unit(3), selected(3), next_return, resolve_pending_deliveries, action_schema, delivery_resolution_inputs, decision_exchanges(3), permits_common_action, reasoning_action_schema, store(9), specialist(2), binding_context(2), resolver, validate_report, execute, pending_work, receive_native_outcome, receive_outcome, automatic_score_updates, last_observed_credit, source_credit_view, retain_shared_grading_results, controller_value(2), run_id(3)}; tables `runtime_episodes`, `runtime_model_calls`, `runtime_actions`; ~25 `_live_original_runtime` names; `providers.ModelCallError`; `episode_source_failure.record_source_failure` |
| task_decision.py | 357 | none (generic decision call / exchange protocol) | self.workflow.{journal, contract_information_profile, validate_contract_information(5), numerical_contracts, decision_protocol(3), decision_exchanges(4), resource_context, shared_information_context, launch_instructions(2), available_child_roles, episode_bindings, binding_context, execution_expectations, resource_estimator(5), is_job_source(3), job_episodes(2), native_estimation_context, freeze_literature_numerical_contracts, freeze_contract_information, receipts(4), uses_received_record_context(2), provider(3), history_preview, services(2), contract_information_reply, execute, specialist, store(2), run_id}; table `runtime_model_calls`; ~34 `runtime` names; `providers._ORIGINAL_MODEL_*`; `episode_work_report.*` |
| task_instructions.py | 20 | composition order (specialist text replaces the default) | self.workflow.{job_episodes, is_job_source, specialist, binding_context, knowledge, launch_instructions, native_event_information, decision_protocol}; `runtime_prompt.INSTRUCTIONS/DECISION_EXCHANGE_PROTOCOL` |
| task_report.py | 22 | none (generic finish) | self.workflow.{source_credit_view, pending_handles, episode_bindings, binding_context, release(2), journal(2), facts}; table `runtime_forms`; `runtime.Record/form_with_facts/_json` |
| task_state.py | 107 | none (generic restore/checkpoint) | self.workflow.{completions(4), inprocess_replay(7), execution_binding(4), journal(5), archive, store(2), source_credit_view, controller_value, recover_commissions, progress_provider(2), run_id}; workflow.context/grains; table `runtime_actions`; `runtime.Episode/ActionLeaf/EFFECT_VERSION/interpretation_schema` |
| task_suspension.py | 8 | none | self.workflow.execution_handle(2), execution_backend |
| terminal_execution.py | 226 | the terminal-execution intent: instructions, decision context, execute, completion, facts, validation | `communication.plain/validate_form`, `practical_yield.PracticalYieldEstimator`, `services.workflow.launch_instructions` (getattr) |
| to_parent.py | 100 | facts / validate_report / no required return sources | `services.annotation_task_required` |
| waiting.py | 10 | none (wait is not permitted here) | self.workflow.perform_selected_wait; `runtime.EventTargetError/_wait_target_feedback` |
| work_operations.py | 35 | parent-input check before every execute | none |
| yield_estimator.py | 50 | request yield class; launch_local profile; PracticalYieldEstimator | `numerical.YieldController/YieldParameters`, `practical_yield.PracticalYieldEstimator` |

`BindingContext` itself is not named. The `context` argument is the old BindingContext shape, used through `context.assignment`,
`.scope`, `.role`, `.path`, `.episode_id`, `.run_id`, `.request` and `.as_record()`.

## Carried over

Rows are the old functions of the episode folder at `97308b94c` (`runs/carry_over/functions/a107__partner_presence_evidence__execution_job_submission__local_job_execution.tsv`), one per row. New files are in `gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/execution_job_submission/local_job_execution/`. Rows beginning "unplaced" are also in `carry_over_blocked/a107__partner_presence_evidence__execution_job_submission__local_job_execution.md`. Library candidates (they stay in this episode's files): `messages/internal_summary.py` `_completion`, `yield_estimator.py` `_request_yield_class`, `messages/final_to_parent.py` `validate_report`, `_resolver`, `_facts`, `_report_schema`, `task.py` `_resource_configuration`, `_resource`, `_handoff`.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | NativeBindingRecord | machinery | binding record / the binding's own as_record() (README 3e) |
| binding_record.py | NativeBindingRecord.as_record | machinery | binding record / the binding's own as_record() (README 3e) |
| completion.py | NativeCompletion | episode function | messages/internal_summary.py _completion (practical completion proof derived from the receipts; library candidate); the proof is not a controller input (README 5 item 5) |
| completion.py | NativeCompletion.completion_for_action | episode function | messages/internal_summary.py _completion (practical completion proof derived from the receipts; library candidate); the proof is not a controller input (README 5 item 5) |
| completion.py | NativeCompletion._closed_completion_verdict | machinery | closed completion verdict / verify_completion over runtime_observations and the PracticalYieldEstimator (README 3d) |
| completion.py | NativeCompletion.verify_completion | machinery | closed completion verdict / verify_completion over runtime_observations and the PracticalYieldEstimator (README 3d) |
| configuration.py | NativeConfiguration | episode function | settings (ctx.settings): task.py _resource_configuration, _resource_information; yield_estimator.py _task_yield_profile; handoff/acquired units, log window/roles, results profiles, API execution, progress provider, result readers = old-runner wiring or results/API role (not carried) |
| configuration.py | NativeConfiguration.__init__ | episode function | settings (ctx.settings): task.py _resource_configuration, _resource_information; yield_estimator.py _task_yield_profile; handoff/acquired units, log window/roles, results profiles, API execution, progress provider, result readers = old-runner wiring or results/API role (not carried) |
| credit.py | ExecutionEpisodeCredit | episode function | credit.py credit (practical credit: project_practical_credit over the summary's receipts) |
| credit.py | ExecutionEpisodeCredit.credit_kind | machinery | credit_kind deleted (README 3d) |
| credit.py | ExecutionEpisodeCredit._closed_credit_carrier | machinery | closed-credit capture and replay over runtime_episodes/runtime_observations/runtime_record_receipts/runtime_forms (README 3e); the system returns completion['credit'] |
| credit.py | ExecutionEpisodeCredit._closed_credit_receipts | machinery | closed-credit capture and replay over runtime_episodes/runtime_observations/runtime_record_receipts/runtime_forms (README 3e); the system returns completion['credit'] |
| credit.py | ExecutionEpisodeCredit._closed_credit_value | machinery | closed-credit capture and replay over runtime_episodes/runtime_observations/runtime_record_receipts/runtime_forms (README 3e); the system returns completion['credit'] |
| credit.py | ExecutionEpisodeCredit._closed_credit_facts | machinery | closed-credit capture and replay over runtime_episodes/runtime_observations/runtime_record_receipts/runtime_forms (README 3e); the system returns completion['credit'] |
| credit.py | ExecutionEpisodeCredit._closed_operational_credit_view | machinery | closed-credit capture and replay over runtime_episodes/runtime_observations/runtime_record_receipts/runtime_forms (README 3e); the system returns completion['credit'] |
| credit.py | ExecutionEpisodeCredit.project_credit | episode function | credit.py credit (practical credit: project_practical_credit over the summary's receipts) |
| credit.py | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py credit (practical credit: project_practical_credit over the summary's receipts) |
| credit.py | ExecutionEpisodeCredit.credit_view | episode function | credit.py credit (practical credit: project_practical_credit over the summary's receipts) |
| episode.py | ExecutionEpisode | episode function | episode.py LocalJobExecution (the one EpisodeBinding class) |
| episode.py | ExecutionEpisode.child_roles | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | ExecutionEpisode.allowed_children | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | ExecutionEpisode.permitted_common_actions | episode function | task.py TOOLS (exec_command is the only action; no wait, no children) |
| execution_contracts.py | native_result_operation_catalog | episode function | unplaced: results role native result operation catalog (status/collect/read); not this launch role (carry_over_blocked) |
| from_parent.py | NativeParentRequests | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (one field per property of practical_assignment_v1) |
| from_parent.py | NativeParentRequests._permitted | episode function | unplaced: launch parent's resource permission / launch assignment re-validation against the commissioning request; a wrong commission fails (rule 1), not carried |
| from_parent.py | NativeParentRequests._request_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (one field per property of practical_assignment_v1) |
| from_parent.py | NativeParentRequests._launch | episode function | unplaced: launch parent's resource permission / launch assignment re-validation against the commissioning request; a wrong commission fails (rule 1), not carried |
| from_parent.py | NativeParentRequests._constraints | episode function | unplaced: launch parent's resource permission / launch assignment re-validation against the commissioning request; a wrong commission fails (rule 1), not carried |
| from_parent.py | NativeParentRequests.child_assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (one field per property of practical_assignment_v1) |
| from_parent.py | NativeParentRequests.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (one field per property of practical_assignment_v1) |
| from_parent.py | NativeParentRequests.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (validate_assignment) and task.py _operations (TerminalExecution.validate_assignment); the checks against the parent's launch form and runtime_* tables are checks of a commission: not carried |
| goal.py | NativeGoal | episode function | goal.py GOAL; task.py GOAL_INSTRUCTION and _instructions |
| goal.py | NativeGoal.instructions | episode function | goal.py GOAL; task.py GOAL_INSTRUCTION and _instructions |
| initial_information.py | initial_information | episode function | task.py decide (settings['initial_information'] shown as execution_initial_information) |
| internal_summary.py | native_decision_snapshot | episode function | messages/internal_summary.py internal_summary and task.py decide; the old-runner fields of the snapshot (working_state, pending_work, report_deliveries, ...) are not carried |
| internal_summary.py | NativeInternalSummary | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | NativeInternalSummary._with_selected_execution_task | episode function | messages/internal_summary.py _selected_execution_task (NMF and HMMER job views unplaced -> raise) |
| internal_summary.py | NativeInternalSummary.decision_context | episode function | messages/internal_summary.py internal_summary |
| presentation.py | present_context | episode function | task.py _task_text (the episode's own rendering of the task in decide); the per-context renderers and scientific_prompt_states are old-runner prompt machinery |
| received_api_reports.py | received_api_reports | machinery | selects the old reader catalog authority (catalog.configured/received); results/API role |
| received_execution_information.py | received_execution_information | machinery | selects the old reader catalog authority (catalog.configured/received); results/API role |
| received_records.py | NativeReceivedRecords | machinery | custody of received handoffs/results over self.store.read_snapshot and the old job_progress_provider reader (system custody, README 3c/3e); results role |
| received_records.py | NativeReceivedRecords._context_target | machinery | custody of received handoffs/results over self.store.read_snapshot and the old job_progress_provider reader (system custody, README 3c/3e); results role |
| received_records.py | NativeReceivedRecords._received | machinery | custody of received handoffs/results over self.store.read_snapshot and the old job_progress_provider reader (system custody, README 3c/3e); results role |
| received_records.py | NativeReceivedRecords.initial_references | episode function | messages/read_from_parent.py record_refs field of ASSIGNMENT_FORM |
| resource_information.py | NativeResourceInformation | episode function | unplaced: the parent-visible resource tool contract list; the parent writes its own text (README 5 item 10) |
| resource_information.py | NativeResourceInformation.resource_tool_contracts | episode function | unplaced: the parent-visible resource tool contract list; the parent writes its own text (README 5 item 10) |
| science.py | NativeScienceInputs | machinery | checks of the commission against the old runner's runtime_episodes request and Store (masking, utility, NMF, immutable versions); a wrong commission fails (rule 1) |
| science.py | NativeScienceInputs._masking_inputs | machinery | checks of the commission against the old runner's runtime_episodes request and Store (masking, utility, NMF, immutable versions); a wrong commission fails (rule 1) |
| science.py | NativeScienceInputs._utility_inputs | machinery | checks of the commission against the old runner's runtime_episodes request and Store (masking, utility, NMF, immutable versions); a wrong commission fails (rule 1) |
| science.py | NativeScienceInputs._expression_nmf_inputs | machinery | checks of the commission against the old runner's runtime_episodes request and Store (masking, utility, NMF, immutable versions); a wrong commission fails (rule 1) |
| science.py | NativeScienceInputs._versions | machinery | checks of the commission against the old runner's runtime_episodes request and Store (masking, utility, NMF, immutable versions); a wrong commission fails (rule 1) |
| science.py | NativeScienceInputs._check_parent_inputs | machinery | checks of the commission against the old runner's runtime_episodes request and Store (masking, utility, NMF, immutable versions); a wrong commission fails (rule 1) |
| state.py | NativeState | machinery | PracticalState delegate and parent-input re-check (file ledger and runtime_episodes); receipts are tool outcomes in the summary |
| state.py | NativeState.initialize | machinery | PracticalState delegate and parent-input re-check (file ledger and runtime_episodes); receipts are tool outcomes in the summary |
| state.py | NativeState.state | machinery | PracticalState delegate and parent-input re-check (file ledger and runtime_episodes); receipts are tool outcomes in the summary |
| task.py | NativeTask | episode function | task.py decide / action / exec_command (the generic old runner loop parts are machinery: journal, inprocess_replay, decision_exchanges, checkpoint restore) |
| task.py | NativeTask.next | episode function | task.py decide / action / exec_command (the generic old runner loop parts are machinery: journal, inprocess_replay, decision_exchanges, checkpoint restore) |
| task.py | NativeTask.apply_response | episode function | task.py decide / action / exec_command (the generic old runner loop parts are machinery: journal, inprocess_replay, decision_exchanges, checkpoint restore) |
| task.py | NativeTask.execute | episode function | task.py decide / action / exec_command (the generic old runner loop parts are machinery: journal, inprocess_replay, decision_exchanges, checkpoint restore) |
| task_decision.py | NativeTaskDecision | episode function | task.py decide and action (call: the model request and its answer; the exchange protocol around it is machinery) |
| task_decision.py | NativeTaskDecision.call | episode function | task.py decide and action (call: the model request and its answer; the exchange protocol around it is machinery) |
| task_decision.py | NativeTaskDecision.instructions | episode function | task.py _instructions |
| task_decision.py | NativeTaskDecision.conversation_key | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | NativeTaskDecision.interpretation_context | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | NativeTaskDecision.exchange_schema | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | NativeTaskDecision.exchange_response | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | NativeTaskDecision.validate_contract_exchange_request | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | NativeTaskDecision.validate_contract_exchange_history | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | NativeTaskDecision.exchange_decision | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | NativeTaskDecision.decision_completion | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_instructions.py | instructions | episode function | task.py _instructions (composition: specialist text, launch library, tool knowledge) |
| task_report.py | NativeTaskReport | machinery | report finish machinery (runtime_forms, release, pending_handles) |
| task_report.py | NativeTaskReport.finish | machinery | report finish machinery (runtime_forms, release, pending_handles) |
| task_state.py | NativeTaskState | machinery | checkpoint/restore/record_effect/execution-failure bookkeeping (README 3e); a failed command is a receipt returned by the tool |
| task_state.py | NativeTaskState.__init__ | machinery | checkpoint/restore/record_effect/execution-failure bookkeeping (README 3e); a failed command is a receipt returned by the tool |
| task_state.py | NativeTaskState.bind_execution_context | machinery | checkpoint/restore/record_effect/execution-failure bookkeeping (README 3e); a failed command is a receipt returned by the tool |
| task_state.py | NativeTaskState.record_execution_failure | machinery | checkpoint/restore/record_effect/execution-failure bookkeeping (README 3e); a failed command is a receipt returned by the tool |
| task_state.py | NativeTaskState.restore_checkpoint | machinery | checkpoint/restore/record_effect/execution-failure bookkeeping (README 3e); a failed command is a receipt returned by the tool |
| task_state.py | NativeTaskState.restore | machinery | checkpoint/restore/record_effect/execution-failure bookkeeping (README 3e); a failed command is a receipt returned by the tool |
| task_state.py | NativeTaskState.record_effect | machinery | checkpoint/restore/record_effect/execution-failure bookkeeping (README 3e); a failed command is a receipt returned by the tool |
| task_state.py | NativeTaskState.checkpoint | machinery | checkpoint/restore/record_effect/execution-failure bookkeeping (README 3e); a failed command is a receipt returned by the tool |
| task_suspension.py | NativeTaskSuspension | machinery | wait/suspension machinery |
| task_suspension.py | NativeTaskSuspension.suspension_changed | machinery | wait/suspension machinery |
| terminal_execution.py | TerminalExecutionBehavior | episode function | task.py / messages/* (the terminal-execution intent) |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | episode function | settings: resources, initial_information (task.py _resource_configuration, _resource) |
| terminal_execution.py | TerminalExecutionBehavior._operations | episode function | task.py _operations |
| terminal_execution.py | TerminalExecutionBehavior._assignment | episode function | messages/read_from_parent.py read_from_parent and task.py _operations |
| terminal_execution.py | TerminalExecutionBehavior._state_directory | machinery | PracticalState directory under the coordinator (old file ledger) |
| terminal_execution.py | TerminalExecutionBehavior.initialize | machinery | PracticalState initialization (file ledger); initial validations are messages/internal_summary.py internal_summary |
| terminal_execution.py | TerminalExecutionBehavior.state | machinery | PracticalState lookup (file ledger) |
| terminal_execution.py | TerminalExecutionBehavior.as_record | machinery | binding's own as_record() |
| terminal_execution.py | TerminalExecutionBehavior.child_roles | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | TerminalExecutionBehavior.credit_kind | machinery | credit_kind deleted (README 3d) |
| terminal_execution.py | TerminalExecutionBehavior.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| terminal_execution.py | TerminalExecutionBehavior.permitted_common_actions | episode function | task.py TOOLS (tool only) |
| terminal_execution.py | TerminalExecutionBehavior.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | TerminalExecutionBehavior.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent |
| terminal_execution.py | TerminalExecutionBehavior.initial_decision_context | episode function | task.py decide (execution_initial_information) |
| terminal_execution.py | TerminalExecutionBehavior._resource_information | episode function | task.py _resource |
| terminal_execution.py | TerminalExecutionBehavior._resource_instructions | episode function | task.py _instructions (LaunchInstructions.for_resource) |
| terminal_execution.py | TerminalExecutionBehavior.instructions | episode function | task.py GOAL_INSTRUCTION, _instructions |
| terminal_execution.py | TerminalExecutionBehavior.decision_context | episode function | task.py decide and messages/internal_summary.py internal_summary |
| terminal_execution.py | TerminalExecutionBehavior.catalog | episode function | task.py EXEC_COMMAND, _output_schema |
| terminal_execution.py | TerminalExecutionBehavior.execute | episode function | task.py exec_command (BLOCKED-ON-JOB-SERVICE: job_access.exec_command) and action (validation of the model's operands) |
| terminal_execution.py | TerminalExecutionBehavior.completion_for_action | episode function | messages/internal_summary.py _completion |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | machinery | PracticalYieldEstimator delegate (README 3d, 7b) |
| terminal_execution.py | TerminalExecutionBehavior.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (OWN_SOURCES, LIBRARY_SOURCES) |
| terminal_execution.py | TerminalExecutionBehavior.facts | episode function | messages/final_to_parent.py _facts |
| terminal_execution.py | TerminalExecutionBehavior.resolve | episode function | messages/final_to_parent.py _resolver |
| terminal_execution.py | TerminalExecutionBehavior.validate_report | episode function | messages/final_to_parent.py validate_report (called from final_to_parent) |
| terminal_execution.py | TerminalExecutionBehavior.credit_view | episode function | credit.py credit |
| to_parent.py | NativeParentReturns | episode function | messages/final_to_parent.py |
| to_parent.py | NativeParentReturns.required_return_sources | machinery | required_return_sources returned () (parent-form machinery, README 3b C4) |
| to_parent.py | NativeParentReturns.facts | episode function | messages/final_to_parent.py _facts (practical facts, handoff refs, empty result sources); native result family branches belong to the results role |
| to_parent.py | NativeParentReturns._live_facts | episode function | messages/final_to_parent.py _facts (practical facts, handoff refs, empty result sources); native result family branches belong to the results role |
| to_parent.py | NativeParentReturns.validate_report | episode function | messages/final_to_parent.py validate_report (the UniProt/Rfam/native adapters of the results role are unplaced) |
| waiting.py | perform_selected_native_wait | machinery | wait machinery (perform_selected_wait) |
| work_operations.py | NativeWorkOperations | episode function | task.py exec_command and action (the per-execute parent-input check is read_from_parent / _operations) |
| work_operations.py | NativeWorkOperations.catalog | episode function | task.py exec_command and action (the per-execute parent-input check is read_from_parent / _operations) |
| work_operations.py | NativeWorkOperations.execute | episode function | task.py exec_command and action (the per-execute parent-input check is read_from_parent / _operations) |
| yield_estimator.py | ExecutionEpisodeYield | episode function | yield_estimator.py (_request_yield_class, _task_yield_profile, yield_controller: completion controller) |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | yield_estimator.py (_request_yield_class, _task_yield_profile, yield_controller: completion controller) |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py (_request_yield_class, _task_yield_profile, yield_controller: completion controller) |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py (_request_yield_class, _task_yield_profile, yield_controller: completion controller) |
| yield_estimator.py | ExecutionEpisodeYield._launch_local_yield_controller | episode function | yield_estimator.py (_request_yield_class, _task_yield_profile, yield_controller: completion controller) |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator delegate (README 3d, 7b) |
