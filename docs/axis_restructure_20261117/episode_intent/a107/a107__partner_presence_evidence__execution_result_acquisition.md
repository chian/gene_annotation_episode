# A107 `partner_presence_evidence/execution_result_acquisition`

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/execution_result_acquisition/<file>`
(43 files directly in the folder, about 2,640 lines; this episode has no `grading/`, `scoring/` or `tests/` subfolder).

## Purpose (its own words)

`binding_path = 'partner_presence_evidence/execution_result_acquisition'`, `commissioning_parent = 'partner_presence_evidence'`,
`roles = entry_roles = ('results',)`, `replaces_default_instructions = True`. `instructions.py`:

> Acquire the original selected execution results through the original handoff. Choose bounded status or requested file/page
> reads using actual preceding outcomes. Preserve partial bytes and native scores. Native paths expose the current resource
> filesystem: the exact attempt observation does not establish that current file bytes were produced by that attempt.
> Separate read windows are not an atomic file snapshot. The scientific parent interprets the returned records. Original
> work, resource and selector stay fixed. Only actual complete acquisition establishes this endpoint.

## Task and instructions

- `task_instructions.instructions` inlines the old general scientific `INSTRUCTIONS` text, plus `DECISION_EXCHANGE_PROTOCOL` and
  `REASONING_COMMIT_REQUIREMENT`. The specialist text above replaces it, because `replaces_default_instructions` is True. If
  `reason` is permitted it adds REASONING_COMMIT_REQUIREMENT. The tool knowledge, the launch library and the pending_child_delivery
  repair paragraph follow. If `wait` is permitted it adds the in-process `pending_child_` wait guidance, and the native_event_targets
  guidance when native event information exists. Under the exchange protocol the history guidance is replaced.
- Renderer: `presentation.present_context`, the same dispatch as local_job_execution.

## What it reads from the parent's assignment

`assignment_schema('results')` = `library.execution_result_contract.RESULTS_SCHEMA` (handoff_ref + selector).
`selector.allOf` adds the conditional local_file_source_selector_v1 schema, the `result_selector_conditions()`, the
expression_nmf_result_selector_v1 schema (when the NMF readers are bound) and the RNA structure/comparison selector `oneOf` (when the RNA readers are bound).
`prepare_assignment`:
1. Restores an already returned original Results commission (`saved_commission._recorded_results_assignment`). It checks the
   parent's `knowledge_inheritance` manifest and `runtime_report_attempts`, that the child path is `('results','child_<index>')`,
   that the child state is yielded, and that the original `episode_child` action has the same assignment and scope.
2. Otherwise it resolves the target: retained NMF, utility or masking target, or `job_progress_provider.targets.read_target(handoff_ref)`.
   It validates the selector against the target and then admits the inputs for each family (file source, masking, utility, RNA comparison, RNA structure,
   standard BLAST database, BLAST database).

`initialize` (result_state.py): local file sources check selector paths. Otherwise the selector is validated. A BLAST database-grader
target (`_blast_target_requirement`, rebuilt from the original Launch request through `runtime_episodes` path lookups)
requires the typed return field `BLAST_GRADED_RETURN_SOURCE` in the parent's report schema. Masking, utility and NMF selectors pre-check
their inputs. API targets initialize through `api_execution`, and native targets create their result directory.
`initial_references`: the handoff_ref plus the selected inputs for each family.

## Children

None.

## Decision state shown to the model

- Generic snapshot `results_decision_snapshot`, the same field set as local_job_execution.
- Own `decision_context`: `{execution_assignment, execution_progress: facts(context,{}), execution_target,
  execution_target_description}` plus `selected_execution_task` (parent scientific question and tool info, with the target's
  request reduced to its scientific job view). Local file sources show
  `{resource_kind:'local', files}` and describe the status and collect operations with ORIGIN provenance. NMF targets use
  `describe_expression_nmf_result`. Other targets use `targets.describe_target(handle, scope, selector)`.
- `task_decision` adds `waiting_support` when `wait` is permitted.
- `initial_information(self, ...)`: for local file sources only the local resource capability. Otherwise it gives catalog reader info.

## Tools offered

`catalog` dispatches on the target and selector. The order is: NMF results, masking results, utility results, RNA comparison,
RNA structure, standard BLAST database, BLAST database (selector-specific), API (`api_execution.catalog`), HMMER preparation, HMMER,
BLAST pairwise, Infernal and Infernal preparation. The default is the native result catalog `execution.results.status`, `execution.results.collect`
and `execution.results.read{path, offset, limit ≤ 1 MiB}`.
`permitted_common_actions` → `('tool','wait')` for an `api_service_assignment_v1` API target, otherwise `('tool',)`.
`execute` routes to the same family adapters. The generic native path (`_execute_native_results`) writes immutable intent,
observation, per-window and receipt files under the result directory. It refuses to run after an existing completion
(`execution_results_assignment_already_completed`), records file failures as data and publishes an
`episode.execution_result` source (`execution_result_information_v2`, with NATIVE_RESULT_ORIGIN). Errors become an
`invalid` outcome (`_outcome(code=...)`), except a retained-artifact NativeFileCaptureError for file sources, which is raised.

## Credit

`credit_kind` → 'operational'. The closed view is used when one exists (closed_credit.py, identical to local_job_execution). The live
view dispatches to the family adapter, API credit or the generic native calculation:
`credit = handoff_unit * 0 + acquired_record_unit * acquired_fraction`. `acquired_fraction` is the mean, over requested paths, of
the newly covered byte positions (the union of read windows minus those already in the initially known refs) divided by the requested span
(`execution_received_selector_coverage_credit_v2`). Mixed local-file sources use
`acquired_record_unit * count` (`execution_received_records_credit_v1`). The fraction is a coverage ratio, not a clamp. The credit is unbounded
in the unit.

## Continuation

`yield_controller` requires `require_private_yield`.
- Native selector without a `version`, some requested length unbounded: `results_yield_profiles['native_unbounded_<kind>']`,
  a plain `YieldController(cutoff, parameters)` with the default estimator. This maps to accumulation.
- Native selector, all lengths finite: `task_yield_profiles['results:native_finite_<kind>']`. Its estimator returns the
  verified-endpoint estimate once `practical_completion` is in the context. It returns exactly 0 when no uncredited bytes remain
  (`finite_result_selector_exhaustion_v1`). Otherwise it uses `estimate_bounded_credit_yield(..., maximum_credit=remaining)`, with
  remaining = `acquired_record_unit*(1-original_fraction)`. This maps to bounded quality, with completion once the endpoint is verified.
- API: `task_yield_profiles['results:api_<service>[_<selector.version>]']`; typed native: `'results:typed_<kind>_<selector.version>'`;
  both with `PracticalYieldEstimator(verify_completion)`. This maps to completion with a target.

## Report to parent

`required_return_sources` → `('execution_result_refs',)` when the parent is `partner_presence_evidence` and
`services.annotation_task_required()` holds. `facts` = live facts for each family, plus the closed-credit snapshot. The generic native
path gives handoff refs, result refs (bodies with windows), file source refs, capture outcomes, `execution_result_origin` and `execution_completed`
(`_native_results_complete`: every requested byte interval is covered by windows of a completed attempt with returncode 0).
API facts add BLAST-grader rows (`_blast_grader_rows`). Each row requires exactly one tool-grading entry whose sheet schema matches
the requested return type, with a matching query length and sha and database.
`validate_report`: the family returns adapters, UniProt (which uses frozen closed facts when they exist), Rfam, `validate_form` and the fact-equality rule.

## Differences from siblings

- Configuration, binding record, resource tool contracts and closed credit are the same as local_job_execution. The completion logic is its own:
  the native results completion proof (`_proof_for_action`) rebuilds the receipt from `runtime_actions` results up to the action index.
- The only A107 execution sibling that restores a saved original commission (`saved_commission.py`) and enforces the BLAST database-
  grader typed return (`target_custody._blast_target_requirement`, `to_parent._blast_grader_rows`).
- Its old task loop is the local one with the `wait` branch inlined and `grain='results'` fixed.

## File by file

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | none | none |
| action_outcome.py | 5 | outcome envelope (`invalid` with code or `completed`) | none |
| binding_record.py | 9 | binding id/config | none |
| binding_roles.py | 6 | VERSION/ROLES/KINDS/ROLE_KINDS | none |
| closed_credit.py | 122 | closed-credit capture and replay | tables `runtime_episodes`, `runtime_observations`, `runtime_receipt_inheritance`, `runtime_record_receipts`, `runtime_forms`; `episode_receipts.EpisodeReceipts`, `episode_return_records.*`; `communication.plain` |
| completion.py | 184 | complete-acquisition predicate; proofs per family; closed verdict | tables `runtime_actions`, `runtime_observations`; `method_loop.identities.UnitRef`, `numerical.NumericBand`, `practical_yield.ESTIMATOR_VERSION`, `episode_return_records._same` |
| configuration.py | 120 | operand validation and adapter construction (same as local) | `numerical.YieldController/YieldParameters`; `services.read_received_molecular_input` |
| credit.py | 81 | selector byte-coverage credit; family dispatch | `communication.plain` |
| credit_records.py | 3 | `_CLOSED_CREDIT` name | none |
| episode.py | 109 | composition; role results; reader aliases | `communication.plain`; old shared-root `library.received_execution_*` |
| from_parent.py | 122 | results schema; prepare_assignment; initial_references; required_return_sources | `services.annotation_task_required` |
| goal.py | 19 | permitted actions (wait for API service targets) | none |
| initial_information.py | 12 | own initial information, local-file special case | `catalog.readers` |
| input_versions.py | 21 | masking/utility/NMF/version checks | none |
| instructions.py | 7 | the episode goal text | none |
| internal_summary.py | 97 | decision_context and selected_execution_task | `results_decision_snapshot`: the same self.workflow members as local's snapshot; table `runtime_actions`; `runtime.*`; `services.scientific_parent_task` |
| native_file_acquisition.py | 63 | immutable native window acquisition receipts | table `runtime_actions` |
| native_target_state.py | 8 | `state()` refuses: practical role required | none |
| presentation.py | 74 | prompt dispatch | `decision_context.*`, `_live_original_providers.*` (12) |
| receipt_selection.py | 35 | `_received` handoff/result selection | none |
| received_api_reports.py | 4 | own API readers | `catalog` |
| received_execution_information.py | 4 | own result readers | `catalog` |
| received_launch_records.py | 3 | LAUNCH_VERSION | none |
| received_launch_requests.py | 69 | original Launch request schema/validation (for BLAST custody) | none |
| report_delivery.py | 23 | none (generic finish) | self.workflow.{source_credit_view, pending_handles, episode_bindings, binding_context, release(2), journal(2), facts}; table `runtime_forms`; `runtime.*` |
| resource_information.py | 68 | resource tool contracts | none |
| result_publication.py | 13 | publish `episode.execution_result` source | none |
| result_records.py | 14 | result provider, origin and native result catalog | none |
| result_state.py | 26 | initialize per target; BLAST typed return required | none |
| saved_commission.py | 46 | restore an original returned Results commission | tables `runtime_report_attempts`, `runtime_episodes`, `runtime_actions`; `episode_receipts.EpisodeReceipts`, `episode_return_records.EpisodeReturnRecords` |
| schema_fields.py | 6 | TEXT/OFFSET/LIMIT/FILE_LIMIT | none |
| selector_records.py | 7 | NATIVE_SELECTOR_SCHEMA | none |
| target_custody.py | 68 | handoff target custody; BLAST grader requirement rebuild | table `runtime_episodes` |
| task.py | 228 | none (generic loop; wait inlined; grain 'results') | the same self.workflow set as local task.py; tables `runtime_actions`, `runtime_episodes`, `runtime_model_calls`; `runtime.*`, `providers.ModelCallError`, `episode_source_failure` |
| task_decision.py | 362 | none (generic; adds waiting_support) | the same as local task_decision plus `permits_common_action`, `waiting_support` |
| task_instructions.py | 27 | composition incl. reasoning-commit and wait guidance | self.workflow.{job_episodes, is_job_source, specialist, binding_context, permits_common_action(3), knowledge, launch_instructions, native_event_information, decision_protocol} |
| task_state.py | 108 | none | the same as local task_state |
| task_suspension.py | 9 | none | self.workflow.execution_handle(2), execution_backend |
| terminal_execution.py | 131 | copy of the TerminalExecutionBehavior (unused by role results; `state()` refuses) | `communication.*`, `practical_yield.PracticalYieldEstimator` |
| to_parent.py | 145 | facts per family; BLAST grader rows; validate_report | `communication.plain/validate_form` |
| work_operations.py | 119 | catalog/execute dispatch per target family | `communication.plain` |
| yield_estimator.py | 91 | results yield profiles and estimators | `numerical.{YieldController, YieldParameters, YieldEstimate, NumericBand, estimate_bounded_credit_yield}`, `practical_yield.PracticalYieldEstimator` |

## Carried over

The episode is carried as the private ten-file binding `ExecutionResultAcquisition(EpisodeBinding)` in
`gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/execution_result_acquisition/` (no
children: no `msg_to_child.py`, no `read_from_child.py`; `CHILD_SLOTS = {}`). Source: `git -C
/home/chia/repos/gene_annotation_episode_disk show 97308b94c:<path>` of the episode's own files (the working tree is not
a git repository). The hook-era `episode.py` (class `ExecutionEpisode(ResultAcquisitionBinding, DescendantBinding)`),
`acquisition_source.py` and the two tests were deleted first (see
`retired_tests/a107__partner_presence_evidence__execution_result_acquisition.tsv`). One row per row of
`runs/carry_over/functions/a107__partner_presence_evidence__execution_result_acquisition.tsv` (130). The class column
is machinery (old runner, not carried) or episode function; a place that starts with "unplaced" has no place now (the
class or module it called is in no place in `episode_support/`, it is a launch-role function this results role never
calls, or it needs the `job_access` service); the cause of each is in
`docs/axis_restructure_20261117/carry_over_blocked/a107__partner_presence_evidence__execution_result_acquisition.md`.
No row is "already in library": the old non-binding files of this folder (grading, scoring, readers) were not in it; the
library functions the new files call are imported by name (`episode_support/readers/**/partner_presence_evidence/*_result_views.py`,
`readers/rna_structure/*`, `readers/expression_and_perturbation/*`, `forms/rna_structure/*`,
`forms/expression_and_perturbation/*`, `acquisition/**/partner_presence_evidence/native_*_acquisition.py`,
`forms/partner_presence_evidence/execution_contracts.py` and `communication.py`,
`jobs/partner_presence_evidence/practical_execution_operations.py`, `jobs/waiting.py`, `instructions/launch_instructions.py`,
`tools/tool_knowledge.py`, `records/progress_views.py`, `model_exchange/rejection_feedback.py`). Rows marked "library
candidate" stay as old code in no file: nothing of them is written into this episode, because the family they serve is
not placed or the role that calls them is not this one.

| old file | kind | name | class | new place or reason |
|---|---|---|---|---|
| action_outcome.py | function | _outcome | episode function | task.py::_outcome |
| binding_record.py | class | ResultsBindingRecord | machinery | binding_record.py and the binding's own as_record() |
| binding_record.py | method | ResultsBindingRecord.as_record | machinery | binding_record.py and the binding's own as_record() |
| closed_credit.py | class | ResultsClosedCredit | machinery | frozen closed credit carrier over runtime_* tables and receipt inheritance; credit is completion[credit] (final_to_parent) |
| closed_credit.py | method | ResultsClosedCredit._closed_credit_carrier | machinery | frozen closed credit carrier over runtime_* tables and receipt inheritance; credit is completion[credit] (final_to_parent) |
| closed_credit.py | method | ResultsClosedCredit._closed_credit_receipts | machinery | frozen closed credit carrier over runtime_* tables and receipt inheritance; credit is completion[credit] (final_to_parent) |
| closed_credit.py | method | ResultsClosedCredit._closed_credit_value | machinery | frozen closed credit carrier over runtime_* tables and receipt inheritance; credit is completion[credit] (final_to_parent) |
| closed_credit.py | method | ResultsClosedCredit._closed_credit_facts | machinery | frozen closed credit carrier over runtime_* tables and receipt inheritance; credit is completion[credit] (final_to_parent) |
| closed_credit.py | method | ResultsClosedCredit._closed_operational_credit_view | machinery | frozen closed credit carrier over runtime_* tables and receipt inheritance; credit is completion[credit] (final_to_parent) |
| completion.py | class | ResultsCompletion | machinery | completion proof / verification over runtime_actions (not a controller input, README 7b) |
| completion.py | method | ResultsCompletion._native_results_complete | episode function | messages/internal_summary.py::_native_results_complete |
| completion.py | method | ResultsCompletion._proof_for_action | machinery | completion proof / verification over runtime_actions (not a controller input, README 7b) |
| completion.py | method | ResultsCompletion.completion_for_action | machinery | completion proof / verification over runtime_actions (not a controller input, README 7b) |
| completion.py | method | ResultsCompletion._closed_completion_verdict | machinery | completion proof / verification over runtime_actions (not a controller input, README 7b) |
| completion.py | method | ResultsCompletion.verify_completion | machinery | completion proof / verification over runtime_actions (not a controller input, README 7b) |
| configuration.py | class | ResultsConfiguration | machinery | configuration: values become ctx.settings (log_window_bytes, yield profiles), the acquired_record_unit assignment field and the job_access service |
| configuration.py | method | ResultsConfiguration.__init__ | machinery | configuration: values become ctx.settings (log_window_bytes, yield profiles), the acquired_record_unit assignment field and the job_access service |
| credit.py | class | ResultsCredit | machinery | credit_kind deleted (README 3d); project_credit / credit_view switched to the frozen closed credit view |
| credit.py | method | ResultsCredit._generic_result_selector_progress | episode function | credit.py::selector_fraction |
| credit.py | method | ResultsCredit.credit_kind | machinery | credit_kind deleted (README 3d); project_credit / credit_view switched to the frozen closed credit view |
| credit.py | method | ResultsCredit.project_credit | machinery | credit_kind deleted (README 3d); project_credit / credit_view switched to the frozen closed credit view |
| credit.py | method | ResultsCredit._live_project_credit | episode function | credit.py::credit |
| credit.py | method | ResultsCredit.credit_view | machinery | credit_kind deleted (README 3d); project_credit / credit_view switched to the frozen closed credit view |
| episode.py | class | ExecutionEpisode | machinery | episode.py::ExecutionResultAcquisition (the one class) |
| from_parent.py | class | ResultsFromParent | episode function | container: methods below |
| from_parent.py | method | ResultsFromParent.required_return_sources | episode function | the parent selects execution_result_refs in its msg_to_child (declared selectable in messages/final_to_parent.py::RETURN_FORM) |
| from_parent.py | method | ResultsFromParent.child_assignment_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM, RESULTS_SCHEMA, NATIVE_SELECTOR_SCHEMA |
| from_parent.py | method | ResultsFromParent.assignment_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM, RESULTS_SCHEMA, NATIVE_SELECTOR_SCHEMA |
| from_parent.py | method | ResultsFromParent.prepare_assignment | episode function | messages/read_from_parent.py::read_from_parent (recorded-commission restore and checks of the commission against held records not carried) |
| from_parent.py | method | ResultsFromParent.initial_references | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM record_refs (new field: the parent names every record the child reads) |
| goal.py | class | ResultsGoal | episode function | goal.py::GOAL |
| goal.py | method | ResultsGoal.child_roles | episode function | task.py::CHILD_SLOTS = {} |
| goal.py | method | ResultsGoal.allowed_children | episode function | task.py::CHILD_SLOTS = {} |
| goal.py | method | ResultsGoal.permitted_common_actions | episode function | task.py::TOOLS['wait'] (offered for an API service assignment; the API family is unplaced, so decide offers only the native result operations) |
| initial_information.py | function | initial_information | episode function | unplaced (library candidate): the resource capabilities / catalog reader information of the initial context; BLOCKED-ON-JOB-SERVICE: job_access capabilities, estimate_table |
| input_versions.py | class | ResultsInputVersions | machinery | checks of a commission's inputs against held records and the old runner (masking, utility, NMF job inputs, input versions): a wrong commission fails, nothing checks it |
| input_versions.py | method | ResultsInputVersions._masking_inputs | machinery | check of a commission's inputs (a wrong commission fails) |
| input_versions.py | method | ResultsInputVersions._utility_inputs | machinery | check of a commission's inputs (a wrong commission fails) |
| input_versions.py | method | ResultsInputVersions._expression_nmf_inputs | machinery | check of a commission's inputs (a wrong commission fails) |
| input_versions.py | method | ResultsInputVersions._versions | machinery | check of a commission's inputs (a wrong commission fails) |
| instructions.py | class | ResultsInstructions | episode function | goal.py::GOAL |
| instructions.py | method | ResultsInstructions.instructions | episode function | goal.py::GOAL |
| internal_summary.py | class | ResultsInternalSummary | episode function | container: methods below |
| internal_summary.py | method | ResultsInternalSummary._with_selected_execution_task | episode function | messages/internal_summary.py::_selected_execution_task (resource information not carried: BLOCKED-ON-JOB-SERVICE job_access capabilities) |
| internal_summary.py | method | ResultsInternalSummary.decision_context | episode function | messages/internal_summary.py::internal_summary (and task.py::decide) |
| internal_summary.py | function | results_decision_snapshot | machinery | generic decision snapshot over self.workflow (working_state, runtime_actions, journal, pending_work, report deliveries); the episode content is messages/internal_summary.py::internal_summary and task.py::decide |
| native_file_acquisition.py | class | ResultsNativeFileAcquisition | episode function | container: methods below |
| native_file_acquisition.py | method | ResultsNativeFileAcquisition._execute_native_results | episode function | task.py::_execute_native_results (with _windows, execution_results_status/collect/read) |
| native_target_state.py | class | ResultsNativeTargetState | machinery | old practical-state hook that only refuses (practical_resource_role_required); no state is kept now |
| native_target_state.py | method | ResultsNativeTargetState.state | machinery | old practical-state hook that only refuses (practical_resource_role_required); no state is kept now |
| presentation.py | function | present_context | episode function | task.py::_task_text and decide (the renderer dispatch, state-frame / bootstrap / lookup rendering and the old shared-root renderers are not carried) |
| receipt_selection.py | class | ResultsReceiptSelection | episode function | container: methods below |
| receipt_selection.py | method | ResultsReceiptSelection._received | episode function | messages/internal_summary.py::internal_summary and _initial_result (the receipt ledger itself is custody) |
| received_api_reports.py | function | received_api_reports | machinery | old reader-authority selection of the provider catalog (catalog.configured / catalog.received); custody replaces it |
| received_execution_information.py | function | received_execution_information | machinery | old reader-authority selection of the provider catalog (catalog.configured / catalog.received); custody replaces it |
| received_launch_requests.py | class | ResultsReceivedLaunchRequests | episode function | unplaced (library candidate): launch-role function (received_launch_requests.py) not used by the results role; carried by the launch episodes |
| received_launch_requests.py | method | ResultsReceivedLaunchRequests._permitted | episode function | unplaced (library candidate): launch-role function (received_launch_requests.py) not used by the results role; carried by the launch episodes |
| received_launch_requests.py | method | ResultsReceivedLaunchRequests._request_schema | episode function | unplaced (library candidate): launch-role function (received_launch_requests.py) not used by the results role; carried by the launch episodes |
| received_launch_requests.py | method | ResultsReceivedLaunchRequests._launch | episode function | unplaced (library candidate): launch-role function (received_launch_requests.py) not used by the results role; carried by the launch episodes |
| received_launch_requests.py | method | ResultsReceivedLaunchRequests._constraints | episode function | unplaced (library candidate): launch-role function (received_launch_requests.py) not used by the results role; carried by the launch episodes |
| report_delivery.py | class | ResultsReportDelivery | machinery | report delivery (finish / report_form machinery) |
| report_delivery.py | method | ResultsReportDelivery.finish | machinery | report delivery (finish / report_form machinery) |
| resource_information.py | class | ResultsResourceInformation | episode function | container: methods below |
| resource_information.py | method | ResultsResourceInformation.resource_tool_contracts | machinery | registry of bound operation contracts by route; the catalogue is TOOLS / task.CATALOG |
| result_publication.py | class | ResultsResultPublication | episode function | container: methods below |
| result_publication.py | method | ResultsResultPublication._publish_result | episode function | task.py::_publish_result |
| result_records.py | function | native_result_operation_catalog | episode function | task.py::CATALOG (tool names are lowercase identifiers) |
| result_state.py | class | ResultsResultState | machinery | result directory manifest and start-up validation (the validation is in read_from_parent) |
| result_state.py | method | ResultsResultState.initialize | machinery | result directory manifest and start-up validation (the validation is in read_from_parent) |
| saved_commission.py | class | ResultsSavedCommission | machinery | restore of a recorded commission (resume is the runner) |
| saved_commission.py | method | ResultsSavedCommission._recorded_results_assignment | machinery | restore of a recorded commission (resume is the runner) |
| target_custody.py | class | ResultsTargetCustody | episode function | container: methods below |
| target_custody.py | method | ResultsTargetCustody._context_target | machinery | launch-role target checks; the results branch (execution_result_target_conflict) is in messages/read_from_parent.py::read_from_parent |
| target_custody.py | method | ResultsTargetCustody._blast_target_requirement | episode function | unplaced: BLAST database-grader requirement rebuilt from the original Launch request (runtime_episodes path lookups) for an API ncbi_blast target; the API family is refused by read_from_parent; BLAST_GRADED_REQUEST_VERSION / BLAST_GRADED_RETURN_SOURCE have no module |
| task.py | class | ResultsTask | machinery | old task loop / checkpoint / restore / wait suspension |
| task.py | method | ResultsTask.next | machinery | old task loop / checkpoint / restore / wait suspension |
| task.py | method | ResultsTask.apply_response | episode function | task.py::action (validation of the model answer; report_update, reason and redelivery branches are not carried) |
| task.py | method | ResultsTask.execute | episode function | task.py::TOOLS (execution_results_status / collect / read, wait); the runtime_actions bookkeeping is the system's |
| task_decision.py | class | ResultsTaskDecision | machinery | old model call / saved decision / context assembly (content moved to decide and internal_summary) |
| task_decision.py | method | ResultsTaskDecision.call | machinery | old model call / saved decision / context assembly (content moved to decide and internal_summary) |
| task_decision.py | method | ResultsTaskDecision.instructions | episode function | task.py::_instructions |
| task_decision.py | method | ResultsTaskDecision.conversation_key | machinery | old model call / saved decision / context assembly (content moved to decide and internal_summary) |
| task_decision.py | method | ResultsTaskDecision.interpretation_context | machinery | decision-exchange loop and saved-exchange contract checks |
| task_decision.py | method | ResultsTaskDecision.exchange_schema | machinery | decision-exchange loop and saved-exchange contract checks |
| task_decision.py | method | ResultsTaskDecision.exchange_response | machinery | decision-exchange loop and saved-exchange contract checks |
| task_decision.py | method | ResultsTaskDecision.validate_contract_exchange_request | machinery | decision-exchange loop and saved-exchange contract checks |
| task_decision.py | method | ResultsTaskDecision.validate_contract_exchange_history | machinery | decision-exchange loop and saved-exchange contract checks |
| task_decision.py | method | ResultsTaskDecision.exchange_decision | machinery | decision-exchange loop and saved-exchange contract checks |
| task_decision.py | method | ResultsTaskDecision.decision_completion | machinery | decision-exchange loop and saved-exchange contract checks |
| task_instructions.py | function | instructions | episode function | task.py::_instructions (goal + knowledge + launch text + native-event wait text; the general scientific INSTRUCTIONS, reasoning commit requirement, pending-child, in-process wait and exchange paragraphs are replaced by the specialist text / not carried) |
| task_state.py | class | ResultsTaskState | machinery | old task loop / checkpoint / restore / wait suspension |
| task_state.py | method | ResultsTaskState.__init__ | machinery | old task loop / checkpoint / restore / wait suspension |
| task_state.py | method | ResultsTaskState.bind_execution_context | machinery | old task loop / checkpoint / restore / wait suspension |
| task_state.py | method | ResultsTaskState.record_execution_failure | machinery | old task loop / checkpoint / restore / wait suspension |
| task_state.py | method | ResultsTaskState.restore_checkpoint | machinery | old task loop / checkpoint / restore / wait suspension |
| task_state.py | method | ResultsTaskState.restore | machinery | old task loop / checkpoint / restore / wait suspension |
| task_state.py | method | ResultsTaskState.record_effect | machinery | old task loop / checkpoint / restore / wait suspension |
| task_state.py | method | ResultsTaskState.checkpoint | machinery | old task loop / checkpoint / restore / wait suspension |
| task_suspension.py | class | ResultsTaskSuspension | machinery | wait / suspension machinery |
| task_suspension.py | method | ResultsTaskSuspension.suspension_changed | machinery | wait / suspension machinery |
| terminal_execution.py | class | TerminalExecutionBehavior | episode function | unplaced: launch-role command executor (local / HPC practical commands, the practical state ledger, receipts and facts); the results role never calls it (its configuration built it per resource for the launch roles); carried by the launch episodes in their own files |
| terminal_execution.py | method | TerminalExecutionBehavior.__init__ | episode function | unplaced: launch-role command executor (local / HPC practical commands, the practical state ledger, receipts and facts); the results role never calls it (its configuration built it per resource for the launch roles); carried by the launch episodes in their own files |
| terminal_execution.py | method | TerminalExecutionBehavior._operations | episode function | unplaced: launch-role command executor (local / HPC practical commands, the practical state ledger, receipts and facts); the results role never calls it (its configuration built it per resource for the launch roles); carried by the launch episodes in their own files |
| terminal_execution.py | method | TerminalExecutionBehavior._assignment | episode function | unplaced: launch-role command executor (local / HPC practical commands, the practical state ledger, receipts and facts); the results role never calls it (its configuration built it per resource for the launch roles); carried by the launch episodes in their own files |
| terminal_execution.py | method | TerminalExecutionBehavior._state_directory | episode function | unplaced: launch-role command executor (local / HPC practical commands, the practical state ledger, receipts and facts); the results role never calls it (its configuration built it per resource for the launch roles); carried by the launch episodes in their own files |
| terminal_execution.py | method | TerminalExecutionBehavior.initialize | episode function | unplaced: launch-role command executor (local / HPC practical commands, the practical state ledger, receipts and facts); the results role never calls it (its configuration built it per resource for the launch roles); carried by the launch episodes in their own files |
| terminal_execution.py | method | TerminalExecutionBehavior.state | episode function | unplaced: launch-role command executor (local / HPC practical commands, the practical state ledger, receipts and facts); the results role never calls it (its configuration built it per resource for the launch roles); carried by the launch episodes in their own files |
| terminal_execution.py | method | TerminalExecutionBehavior.catalog | episode function | unplaced: launch-role command executor (local / HPC practical commands, the practical state ledger, receipts and facts); the results role never calls it (its configuration built it per resource for the launch roles); carried by the launch episodes in their own files |
| terminal_execution.py | method | TerminalExecutionBehavior.execute | episode function | unplaced: launch-role command executor (local / HPC practical commands, the practical state ledger, receipts and facts); the results role never calls it (its configuration built it per resource for the launch roles); carried by the launch episodes in their own files |
| terminal_execution.py | method | TerminalExecutionBehavior.completion_for_action | episode function | unplaced: launch-role command executor (local / HPC practical commands, the practical state ledger, receipts and facts); the results role never calls it (its configuration built it per resource for the launch roles); carried by the launch episodes in their own files |
| terminal_execution.py | method | TerminalExecutionBehavior.practical_estimator | episode function | unplaced: launch-role command executor (local / HPC practical commands, the practical state ledger, receipts and facts); the results role never calls it (its configuration built it per resource for the launch roles); carried by the launch episodes in their own files |
| terminal_execution.py | method | TerminalExecutionBehavior.fact_sources | episode function | unplaced: launch-role command executor (local / HPC practical commands, the practical state ledger, receipts and facts); the results role never calls it (its configuration built it per resource for the launch roles); carried by the launch episodes in their own files |
| terminal_execution.py | method | TerminalExecutionBehavior.facts | episode function | unplaced: launch-role command executor (local / HPC practical commands, the practical state ledger, receipts and facts); the results role never calls it (its configuration built it per resource for the launch roles); carried by the launch episodes in their own files |
| terminal_execution.py | method | TerminalExecutionBehavior.resolve | episode function | unplaced: launch-role command executor (local / HPC practical commands, the practical state ledger, receipts and facts); the results role never calls it (its configuration built it per resource for the launch roles); carried by the launch episodes in their own files |
| terminal_execution.py | method | TerminalExecutionBehavior.validate_report | episode function | unplaced: launch-role command executor (local / HPC practical commands, the practical state ledger, receipts and facts); the results role never calls it (its configuration built it per resource for the launch roles); carried by the launch episodes in their own files |
| terminal_execution.py | method | TerminalExecutionBehavior.credit_view | episode function | unplaced: launch-role command executor (local / HPC practical commands, the practical state ledger, receipts and facts); the results role never calls it (its configuration built it per resource for the launch roles); carried by the launch episodes in their own files |
| to_parent.py | class | ResultsToParent | episode function | container: methods below |
| to_parent.py | method | ResultsToParent.facts | episode function | messages/final_to_parent.py::_facts (with messages/internal_summary.py progress) |
| to_parent.py | method | ResultsToParent._live_facts | episode function | messages/final_to_parent.py::_facts (with messages/internal_summary.py progress) |
| to_parent.py | method | ResultsToParent.validate_report | episode function | messages/final_to_parent.py::validate_report |
| to_parent.py | method | ResultsToParent._blast_grader_rows | episode function | unplaced: BLAST database-grader rows of an API ncbi_blast result (source_tool_grading_entries over api_execution.read_result); the API family is refused by read_from_parent |
| work_operations.py | class | ResultsWorkOperations | episode function | container: methods below |
| work_operations.py | method | ResultsWorkOperations.catalog | episode function | task.py::_catalog |
| work_operations.py | method | ResultsWorkOperations.execute | episode function | task.py::TOOLS (execution_results_status/collect/read; family dispatch is read_from_parent.family) |
| yield_estimator.py | class | ExecutionEpisodeYield | episode function | container: methods below |
| yield_estimator.py | method | ExecutionEpisodeYield._request_yield_class | episode function | unplaced: classifies a launch request for the launch yield profile key; the results role never calls it (its profile keys come from the target kind and selector), so it has no use in this file (library candidate; carried by the launch episodes) |
| yield_estimator.py | method | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py::_profile |
| yield_estimator.py | method | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py::yield_controller |
| yield_estimator.py | method | ExecutionEpisodeYield._results_yield_controller | episode function | yield_estimator.py::yield_controller |
| yield_estimator.py | method | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator over verify_completion (not a controller input, README 7b) |
