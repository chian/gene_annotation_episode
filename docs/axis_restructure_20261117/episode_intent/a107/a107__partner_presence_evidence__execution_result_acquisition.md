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
