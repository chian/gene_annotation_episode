# a102/structural_homology_evidence/execution_job_submission/api_job_execution — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence/execution_job_submission/api_job_execution/`
(39 files directly in the folder; no `grading/` or `scoring/` subfolder; `tests/` not read). Nothing from the old
shared root was read; where behaviour lives there (the API service executor `api_service_execution.APIServiceExecution`,
the prompt renderer), this page says only what this episode's own files ask of it.

Old binding: class `ExecutionEpisode`, `binding_path =
'structural_homology_evidence/execution_job_submission/api_job_execution'`, `commissioning_parent =
'structural_homology_evidence/execution_job_submission'`, old role `launch_api`, `entry_roles = ()` (never an
entry), version `execution_episode_v1`. Decision source: `APIJobTask`. Prompt renderer: `render_api_launch_prompt`.

## What this episode is for

It carries out one concrete API request that its launch parent chose, through the configured service, one
operation per turn, until a usable monitoring/results handoff exists. In its own words (`goal.py`, the whole text;
`{service}` is the request's service):

> Carry out the assigned work through {service} using one selected operation each turn. Keep the original inputs,
> request, resource and parent constraints fixed. Choose useful preparation, service requests, observations or
> repair from the actual available operations and received outcomes. Distinguish an immediate returned response
> from a service job that continues remotely. Preserve the actual request or job identity and submission
> uncertainty; a missing reply does not establish that no job was created. Establish the requested usable
> monitoring/results handoff from recorded service facts. The configured controller governs continuation;
> verified original handoff completion gives exact zero future credit.

## Task and instructions

- One unit is one model-selected tool action. Permitted actions (`action_policy.py`): `tool` only, or `tool` and
  `wait` when the request is an `api_service_assignment_v1` (a service job that continues remotely). No reasoning
  commit, no children, no redelivery.
- Instructions (`instructions.py`): the goal text above replaces the default; then tool knowledge, the launch
  instruction library, the redelivery paragraph, the wait paragraphs and the native event paragraph when waiting is
  permitted, and the `request_context` history guidance. (Same composition text as the launch parent.)
- `task.py` keeps the head's decision-source text but drops the reasoning-commit branch: every selection is
  validated against the selection schema; the report update is validated for grain `launch_api`.

## What it reads from its parent's assignment

`from_parent.py`, `parent_input_custody.py`:

- Assignment form: `anyOf` the request forms of the configured API resources (`api_execution.assignment_schema`
  per resource, with `resource_id` required and fixed); `{'not': {}}` when no API resource is configured.
- The request is validated by the API executor (also against the scope); its resource must be of kind `api`.
- It must be commissioned by the old `launch` role (`resource_child_role_owned_by_launch`).
- The parent's own launch assignment supplies the `immutable_input_versions`, which are validated; the request's
  protein-structure inputs are validated.
- Before initialize and before every execution (`_check_parent_inputs`) it re-reads its parent's recorded launch
  assignment from the old `runtime_episodes` table and repeats those checks.
- Required returns from its parent's form: none (`required_return_sources` returns `()` in both branches).

## Children

None (`child_eligibility.py`: `child_roles` and `allowed_children` return `()`).

## Decision state and what it shows the model

- Source state and model inputs: same text as the launch parent (`task_state.py`, `decision_state.py`).
- Own block (`internal_summary.py`): `execution_assignment`, `execution_progress` (its current facts), plus whatever
  the API executor's `decision_context(context, view)` adds. The local-protein `selected_execution_task` of the
  launch parent is not built here.
- Initial context (`resource_information.py`, same as parent): `execution_resource_capabilities`,
  `execution_initial_information`; API resources carry `api_configuration_facts`
  (`ncbi_contact_configured`, `provider_rate_state_configured`, booleans that must agree).
- Context additions before each decision (`decision_inputs.py`): as the parent, with execution expectations
  captured for `launch_api`.
- Presentation (`decision_provider.py`): the episode's renderer is used when the context is an API launch context
  (and not HPC or published scientific); otherwise the plain provider call.

## Tools it offers

The API executor's catalog for this context (`api_operations.py`: `self._delegate(context).catalog(context)`), or
the native protein-structure result catalog when that applies. Execution is delegated to the API executor after
`_check_parent_inputs`. The tool names come from `api_execution.capabilities(resource_id)`; they are not listed in
this folder.

## How its credit is counted

Credit kind `operational`. `credit.py`: the credit view is the API executor's `credit_view(context,
receiver_selection)` (or the native protein-structure results view). The closed view captured at close is returned
afterwards (`closed_credit.py`, same text as parent). `handoff_unit` and `acquired_record_unit` are construction
settings passed into the API executor (`configuration.py`). Completion (`completion.py`): the API executor's
`completion_for_action` and `verify_completion`, with the recorded-history verdict first.

## Continuation

`yield_estimator.py`: old `YieldController` (today's accumulation estimator) with:

- the profile `launch_api:{request yield class}` from `task_yield_profiles`; class is
  `api_{service}[_{algorithm}][_{database}]_handoff`;
- settings: the profile's `cutoff` (above zero) and `parameters`;
- `estimate_with_context=PracticalYieldEstimator(verify_completion)`: once completion is verified the forecast is
  exactly zero.

`private_yield_binding` must be enabled.

## What it reports to its parent

`to_parent.py`: fact sources as the launch parent (handoff refs, result refs, completed, origin, file sources,
protein-structure sources); facts are the API executor's `facts(context, snapshot)` plus empty protein lists and
`execution_result_origin: null`. Any report field bound to a fact must equal the recorded fact. The final form is
saved once (`report_delivery.py`).

## How it differs from similar episodes

- Against its parent `execution_job_submission`: no children, no reasoning, waiting only for service jobs;
  credit, completion, catalog, initialize and facts are delegated to the API executor instead of counting received
  handoffs; continuation is accumulation with a completion estimate instead of bounded by remaining requests;
  goal text is service work, not resource choice; it re-checks its parent's recorded launch assignment.
- Against its sibling `hpc_job_execution`: same family layout and same yield shape (`launch_hpc:` vs `launch_api:`
  profile); HPC delegates to the command behaviour (`exec_command`) and permits only `tool`; API delegates to the
  API executor and may `wait`. API keeps the parent's split decision files (`task_decision.py`,
  `decision_inputs.py`, `decision_state.py`, ...); HPC has `decision_delivery.py` and `decision_context.py`.
- `terminal_execution.py` (242 lines) is an identical copy of the parent's local/HPC command behaviour, imported
  by `execution_contracts.py`; the API path does not run commands.
- About 20 of its files differ from the parent's copies only in class prefix and docstring (see the table).

## Points the carry-over has to settle (seen in these files)

- `PracticalYieldEstimator` passed as `estimate_with_context` is a fourth estimator-shaped object; only the three
  yield estimators exist now.
- `_check_parent_inputs` reads the parent's request from the old `runtime_episodes` table by path; the new runner
  gives the parent's commission through `bound.assignment`/the journal.
- `wait` is an old-runner action.
- Files serving the old `results` role (`result_selection.py`, `retained_result_*.py`) are copied here but the
  role is `launch_api`.

## Old-runner names (totals for this episode)

| Group | Distinct names | Uses |
|---|---|---|
| `self.workflow.<member>` | 74 | 196 |
| BindingContext (`binding_context`), receipts, return records, `UnitRef`, raw `store.db.execute`, `_ready_owned_child` | 6 | 27 |
| imports from old `root.a102` shared modules (incl. `runtime`, `providers`, `communication`, `decision_context`, `episode_bindings`, `episode_journal`, `composition_information`) | 44 | 110 |
| old `services.<member>` (services held the Workflow) | 2 | 2 |
| old journal and receipt tables | 8 | 49 |
| old yield names | 5 | 20 |
| symbols through `runtime`, `runtime_prompt`, `providers` | 55 | 148 |

Counted mechanically from the files at `97308b94c`; every row (name, file, uses, purpose) is in
`runs/carry_over/calls/a102_01.tsv`. `workflow.x` and `source.workflow.x` are counted as `self.workflow.x`.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (uses) |
|---|---|---|---|
| `__init__.py` | 0 | empty | none |
| `action_policy.py` | 13 | tool only; tool+wait when the request is an api_service_assignment_v1 | none |
| `api_operations.py` | 17 | catalog and execution delegated to the API service executor, after parent-input check | `import root.a102.native_protein_structure_results` 1 |
| `binding_record.py` | 8 | binding identity record with resources, units, log window/roles, yield profiles | none |
| `child_eligibility.py` | 11 | no children | none |
| `closed_credit.py` | 116 | captures credit view at close; closed view returned unchanged afterwards | `EpisodeReceipts` 2, `EpisodeReturnRecords` 2, `import root.a102.episode_receipts` 1, `import root.a102.episode_return_records` 3, `store.db.execute` 5, `table runtime_episodes` 2, `table runtime_forms` 3, `table runtime_observations` 1, `table runtime_receipt_inheritance` 2, `table runtime_record_receipts` 2, `table sqlite_master` 2 |
| `completion.py` | 49 | completion proof and verification delegated to the API service executor | `import root.a102.episode_return_records` 1, `import root.a102.method_loop.identities` 1, `import root.a102.numerical` 1, `import root.a102.practical_yield` 1, `store.db.execute` 1, `table runtime_observations` 1, `UnitRef` 2, `ESTIMATOR_VERSION` 2, `NumericBand` 2 |
| `configuration.py` | 61 | construction settings: resources, inventory, handoff_unit, acquired_record_unit (positive), log window/roles, private yield flag, results/task yield profiles; builds per-resource executors | `import root.a102.api_service_execution` 1, `import root.a102.execution_progress` 1, `import root.a102.native_protein_structure_results` 1, `import root.a102.native_protein_structure_returns` 1, `import root.a102.numerical` 1, `YieldController` 3, `YieldParameters` 3 |
| `credit.py` | 22 | operational credit = API service executor credit view | none |
| `decision_contracts.py` | 127 | request_context exchange envelope and replay checks | `import root.a102.decision_context` 1, `import root.a102.execution_prompt` 1, `import root.a102.library.hpc_prompt` 1, `import root.a102.runtime` 2, `import root.a102.structural_homology_evidence_prompt` 1, `runtime.apply_state_frame` 1, `runtime.composition_lookup_schema` 2, `runtime.CONTRACT_INFORMATION_OPERATIONS` 1, `runtime.DECISION_CONTEXT_VERSION` 1, `runtime.Draft202012Validator` 1, `runtime.instructional_model_context` 1, `runtime.is_contract_information` 1, `runtime._json` 8, `runtime.Mapping` 2, `runtime.model_snapshot` 1, `runtime._object` 3, `runtime._recorded_action_generation_schema` 1, `runtime._references_in` 1, `runtime.requested_contract_information` 1, `runtime.ValidationError` 1, `runtime.WorkflowError` 9, `self.workflow.contract_information_reply` 1, `self.workflow.decision_exchanges` 2, `self.workflow.journal` 1, `self.workflow.store` 2, `self.workflow.validate_contract_information` 2, `table runtime_model_calls` 1 |
| `decision_exchange.py` | 107 | request_context exchange loop | `import root.a102.decision_context` 1, `import root.a102.execution_prompt` 1, `import root.a102.library.hpc_prompt` 1, `import root.a102.runtime` 2, `import root.a102.structural_homology_evidence_prompt` 1, `runtime._action_generation_schema` 1, `runtime._category_yield_parameters` 1, `runtime.child_option_information` 1, `runtime.DECISION_CONTEXT_VERSION` 1, `runtime.instructional_model_context` 2, `runtime._json` 2, `runtime.lookup_attempts` 1, `runtime.Mapping` 1, `runtime.model_snapshot` 1, `runtime._plain` 2, `runtime.requested_contract_information` 1, `runtime.schema_failure_diagnostic` 2, `runtime.sqlite3` 1, `runtime.state_frame` 1, `runtime.ValidationError` 4, `runtime.yield_table` 1, `self.workflow.controller_binding` 1, `self.workflow.decision_exchanges` 1, `self.workflow.execute` 1, `self.workflow.journal` 1, `self.workflow.run_id` 1, `self.workflow.services` 1, `self.workflow.validate_contract_information` 1, `table runtime_model_calls` 2 |
| `decision_inputs.py` | 58 | context additions (expectations captured for launch_api) | `binding_context` 1, `import root.a102.episode_work_report` 2, `import root.a102.library.hpc_prompt` 1, `import root.a102.runtime` 2, `runtime.child_option_information` 1, `runtime.Mapping` 1, `self.workflow.available_child_roles` 1, `self.workflow.binding_context` 1, `self.workflow.episode_bindings` 1, `self.workflow.execution_expectations` 1, `self.workflow.is_job_source` 1, `self.workflow.job_episodes` 2, `self.workflow.launch_instructions` 2, `self.workflow.native_estimation_context` 1, `self.workflow.pending_work` 1, `self.workflow.permits_common_action` 1, `self.workflow.resource_context` 1, `self.workflow.resource_estimator` 5, `self.workflow.shared_information_context` 1, `self.workflow.waiting_support` 1 |
| `decision_provider.py` | 19 | API launch prompt renderer when the context is an API launch | `import root.a102.decision_context` 1, `import root.a102.execution_prompt` 1, `import root.a102.library.hpc_prompt` 1, `import root.a102.runtime` 1, `import root.a102.structural_homology_evidence_prompt` 1, `self.workflow.provider` 1, `self.workflow.specialist` 1 |
| `decision_state.py` | 45 | model inputs assembled from state and controller | `binding_context` 1, `import root.a102.runtime` 2, `runtime.FACT_MEANINGS` 1, `runtime.FACT_SOURCES` 1, `runtime.Mapping` 3, `runtime._plain` 2, `runtime._references_in` 1, `self.workflow.binding_context` 1, `self.workflow.catalog` 1, `self.workflow.controller_binding` 1, `self.workflow.delivery_status` 1, `self.workflow.extra_report_sources` 1, `self.workflow.is_scientific_source` 1, `self.workflow.job_episode_options` 1, `self.workflow.journal` 3, `self.workflow.knowledge` 1, `self.workflow.local_outcome_preview` 1, `self.workflow.pending_work` 1, `self.workflow.receipt_projection` 1, `self.workflow.run_id` 1, `self.workflow.source_credit_binding` 1, `self.workflow.source_credit_view` 1, `self.workflow.specialist` 1, `self.workflow.store` 3, `self.workflow.tools` 1, `self.workflow.working_state` 1, `table runtime_actions` 2 |
| `episode.py` | 39 | binding identity: role launch_api, parent execution_job_submission, not an entry, renderer render_api_launch_prompt | `import root.a102.execution_prompt` 1 |
| `execution_contracts.py` | 47 | constants and launch/result operation catalogs | `import root.a102.communication` 1, `import root.a102.domain` 1, `import root.a102.execution_contracts` 1, `import root.a102.launch_instructions` 1, `import root.a102.local_file_capture_results` 1, `import root.a102.native_protein_structure_acquisition` 1, `import root.a102.practical_execution_operations` 1, `import root.a102.practical_execution_records` 1, `import root.a102.practical_execution_state` 1, `import root.a102.practical_receipt_information` 1, `import root.a102.resource_records` 1 |
| `execution_state.py` | 37 | initialize: parent-input check then API executor initialize | none |
| `from_parent.py` | 53 | one API request of the right kind; must be commissioned by launch; inputs/versions checked against the parent launch; requires nothing back | `import root.a102.protein_structure_operands` 3, `services.annotation_task_required` 1 |
| `goal.py` | 11 | goal text: carry out the assigned work through the service, one operation per turn | none |
| `instructions.py` | 23 | instruction composition (goal replaces default) | `binding_context` 1, `import root.a102.runtime_prompt` 2, `runtime_prompt.DECISION_EXCHANGE_PROTOCOL` 1, `runtime_prompt.INSTRUCTIONS` 3, `runtime_prompt.REASONING_COMMIT_REQUIREMENT` 1, `self.workflow.binding_context` 1, `self.workflow.decision_protocol` 1, `self.workflow.knowledge` 1, `self.workflow.launch_instructions` 1, `self.workflow.native_event_information` 1, `self.workflow.permits_common_action` 3, `self.workflow.specialist` 1 |
| `internal_summary.py` | 17 | execution_assignment, execution_progress, plus the API executor decision context | none |
| `parent_input_custody.py` | 78 | as launch, plus _check_parent_inputs against the recorded parent launch assignment | `import root.a102.execution_input_versions` 1, `import root.a102.native_protein_structure_tool_info` 1, `import root.a102.protein_structure_operands` 1, `store.db.execute` 1, `table runtime_episodes` 1 |
| `received_record_selection.py` | 35 | selects received handoffs/results that belong to its own requests | none |
| `received_records.py` | 37 | facts the annotation/head parent may receive from it | `import root.a102.protein_structure_result_views` 1 |
| `received_reference_custody.py` | 35 | received reference resolution and admission of handoff/result references | none |
| `report_delivery.py` | 25 | final form = report values + facts | `binding_context` 1, `import root.a102.library.private_policy_call` 1, `import root.a102.library.report_fact_assembly` 1, `import root.a102.runtime` 2, `runtime.form_with_facts` 1, `runtime._json` 2, `runtime.Record` 2, `self.workflow.binding_context` 1, `self.workflow.episode_bindings` 1, `self.workflow.facts` 1, `self.workflow.journal` 2, `self.workflow.pending_handles` 1, `self.workflow.release` 2, `self.workflow.source_credit_view` 1, `table runtime_forms` 2 |
| `report_reference_access.py` | 45 | reference resolution for its report | `import root.a102.episode_bindings` 2 |
| `resource_information.py` | 82 | initial context (resource capabilities, inventory); resource_tool_contracts for the head | `import root.a102.native_protein_structure_tool_info` 1 |
| `result_selection.py` | 75 | results target/selector/windows; receiver selection; handoff-to-request match | `EpisodeReceipts` 2, `import root.a102.episode_receipts` 1, `import root.a102.protein_structure_selection` 1, `services.record_selection` 1, `store.db.execute` 3, `table runtime_actions` 1, `table runtime_receipt_inheritance` 2, `table sqlite_master` 1 |
| `retained_protein_reader.py` | 94 | retained protein structure reader; protected protein references | `import root.a102.execution_contracts` 1, `import root.a102.native_protein_structure_results` 1, `import root.a102.native_protein_structure_returns` 1, `import root.a102.protein_structure_contracts` 1, `import root.a102.protein_structure_operands` 1, `import root.a102.protein_structure_selection` 1, `import root.a102.state` 1, `store.db.execute` 1, `table runtime_episodes` 1 |
| `retained_result_acquisition.py` | 19 | selected result action lookup | `store.db.execute` 1, `table runtime_actions` 1 |
| `retained_result_publication.py` | 53 | result receipt validation and reading | `store.db.execute` 1, `table runtime_episodes` 1 |
| `task.py` | 223 | decision source; no reasoning branch; grain launch_api | `binding_context` 1, `_execution_context._ready_owned_child` 1, `import root.a102.episode_source_failure` 1, `import root.a102.library.action_contracts` 1, `import root.a102.library.private_policy_call` 1, `import root.a102.providers` 1, `import root.a102.read_mapping` 1, `import root.a102.runtime` 2, `runtime.AcquisitionError` 2, `runtime.ActionFailure` 1, `runtime.ContractError` 1, `runtime.ContractInformationError` 1, `runtime._decode_recorded_action_response` 1, `runtime.Draft202012Validator` 2, `runtime.EventTargetError` 2, `runtime.inspect` 1, `runtime._json` 5, `runtime.Mapping` 2, `runtime.nullcontext` 5, `runtime.observes_action_outcome` 1, `runtime.ReportBoundaryError` 1, `runtime.ReportRedelivery` 2, `runtime.schema_failure_diagnostic` 1, `runtime.SourceEnd` 2, `runtime.sqlite3` 2, `runtime.subprocess` 2, `runtime.validate_form` 1, `runtime.ValidationError` 3, `runtime._wait_target_feedback` 2, `runtime.WorkflowError` 2, `self.workflow.action_schema` 1, `self.workflow.automatic_score_updates` 1, `self.workflow.binding_context` 1, `self.workflow.completed_unit` 3, `self.workflow.completions` 3, `self.workflow.controller_value` 2, `self.workflow.decision_exchanges` 3, `self.workflow.delivery_resolution_inputs` 1, `self.workflow.execute` 1, `self.workflow.execution_binding` 7, `self.workflow.inprocess_replay` 4, `self.workflow.journal` 7, `self.workflow.last_observed_credit` 1, `self.workflow.next_return` 1, `self.workflow.pending_work` 1, `self.workflow.perform_selected_wait` 1, `self.workflow.permits_common_action` 1, `self.workflow.receive_native_outcome` 1, `self.workflow.receive_outcome` 1, `self.workflow.resolve_pending_deliveries` 1, `self.workflow.resolver` 1, `self.workflow.retain_shared_grading_results` 1, `self.workflow.run_id` 3, `self.workflow.selected` 3, `self.workflow.source_credit_view` 1, `self.workflow.specialist` 1, `self.workflow.store` 8, `self.workflow.validate_report` 1, `table runtime_actions` 8, `table runtime_episodes` 1, `table runtime_model_calls` 2 |
| `task_decision.py` | 88 | decision call | `import root.a102.decision_context` 1, `import root.a102.execution_prompt` 1, `import root.a102.library.hpc_prompt` 1, `import root.a102.runtime` 2, `import root.a102.structural_homology_evidence_prompt` 1, `runtime._action_generation_schema` 1, `runtime._ASSIGNMENT_TRANSPORT` 1, `runtime.DECISION_EXCHANGE_PROTOCOL` 5, `runtime._digest` 1, `runtime.instructional_model_context` 1, `runtime._json` 4, `runtime._recorded_assignment_transport` 1, `runtime.WorkflowError` 5, `self.workflow.contract_information_profile` 1, `self.workflow.decision_exchanges` 1, `self.workflow.decision_protocol` 3, `self.workflow.freeze_contract_information` 1, `self.workflow.freeze_literature_numerical_contracts` 1, `self.workflow.history_preview` 1, `self.workflow.is_job_source` 2, `self.workflow.journal` 1, `self.workflow.numerical_contracts` 1, `self.workflow.provider` 2, `self.workflow.receipts` 4, `self.workflow.services` 1, `self.workflow.uses_received_record_context` 2, `self.workflow.validate_contract_information` 2, `table runtime_model_calls` 5 |
| `task_state.py` | 108 | source state, failure as unit, restore/checkpoint | `import root.a102.episode_source_failure` 1, `import root.a102.runtime` 2, `runtime.ActionLeaf` 1, `runtime.EFFECT_VERSION` 1, `runtime.Episode` 1, `runtime.interpretation_schema` 1, `runtime._json` 2, `runtime._object` 1, `runtime._plain` 1, `runtime.Record` 1, `self.workflow.archive` 1, `self.workflow.completions` 4, `self.workflow.context` 1, `self.workflow.controller_value` 1, `self.workflow.execution_binding` 4, `self.workflow.grains` 1, `self.workflow.inprocess_replay` 7, `self.workflow.journal` 5, `self.workflow.progress_provider` 2, `self.workflow.recover_commissions` 1, `self.workflow.run_id` 1, `self.workflow.source_credit_view` 1, `self.workflow.store` 2, `table runtime_actions` 5 |
| `terminal_execution.py` | 242 | copy of the local/HPC command behaviour (unused by API path except imports) | `import root.a102.acquisition` 1, `import root.a102.communication` 1, `import root.a102.domain` 1, `import root.a102.practical_execution_operations` 1, `import root.a102.practical_execution_records` 1, `import root.a102.practical_execution_state` 1, `import root.a102.practical_receipt_information` 3, `import root.a102.practical_yield` 1, `import root.a102.terminal_execution` 1, `import root.a102.terminal_scientific_evidence` 2, `PracticalYieldEstimator` 2 |
| `to_parent.py` | 42 | facts from the API executor; execution_result_origin null | `import root.a102.local_file_capture_results` 1, `import root.a102.protein_structure_result_views` 2 |
| `waiting.py` | 9 | suspension forwarded to backend | `self.workflow.execution_backend` 1, `self.workflow.execution_handle` 2 |
| `yield_estimator.py` | 52 | accumulation controller, profile launch_api:<class>, practical completion estimate | `import root.a102.numerical` 1, `import root.a102.practical_yield` 2, `PracticalYieldEstimator` 4, `YieldController` 2, `YieldParameters` 2 |

## Carried over

This carry-over is a private copy of the shape of the finished sibling carry of the same old source (same old files, same function list; nothing imported). Rows with kind machinery are not carried.

| old file | name | kind | new place or reason |
|---|---|---|---|
| action_policy.py | APIActionPolicy | episode function | task.py wait_permitted/offered_actions |
| action_policy.py | APIActionPolicy.permitted_common_actions | episode function | task.py wait_permitted/offered_actions |
| api_operations.py | APIApiOperations | episode function | task.py catalog_of/service_operation (BLOCKED-ON-JOB-SERVICE: job_access api_catalog/api_execute) |
| api_operations.py | APIApiOperations.catalog | episode function | task.py catalog_of/service_operation (BLOCKED-ON-JOB-SERVICE: job_access api_catalog/api_execute) |
| api_operations.py | APIApiOperations.execute | episode function | task.py catalog_of/service_operation (BLOCKED-ON-JOB-SERVICE: job_access api_catalog/api_execute) |
| binding_record.py | APIBindingRecord | machinery | the binding's own as_record(); the system records the binding |
| binding_record.py | APIBindingRecord.as_record | machinery | the binding's own as_record(); the system records the binding |
| child_eligibility.py | APIChildEligibility | machinery | no children (CHILD_SLOTS = {}); eligibility is not an episode function |
| child_eligibility.py | APIChildEligibility.child_roles | machinery | no children (CHILD_SLOTS = {}); eligibility is not an episode function |
| child_eligibility.py | APIChildEligibility.allowed_children | machinery | no children (CHILD_SLOTS = {}); eligibility is not an episode function |
| closed_credit.py | APIClosedCredit | machinery | frozen closed credit view re-validated against the old journal tables; the system closure credit is used |
| closed_credit.py | APIClosedCredit._closed_credit_carrier | machinery | frozen closed credit view re-validated against the old journal tables; the system closure credit is used |
| closed_credit.py | APIClosedCredit._closed_credit_receipts | machinery | frozen closed credit view re-validated against the old journal tables; the system closure credit is used |
| closed_credit.py | APIClosedCredit._closed_credit_value | machinery | frozen closed credit view re-validated against the old journal tables; the system closure credit is used |
| closed_credit.py | APIClosedCredit._closed_credit_facts | machinery | frozen closed credit view re-validated against the old journal tables; the system closure credit is used |
| closed_credit.py | APIClosedCredit._closed_operational_credit_view | machinery | frozen closed credit view re-validated against the old journal tables; the system closure credit is used |
| completion.py | APICompletion | episode function | yield_estimator.py yield_controller (CompletionYieldController, target completion_target); verification of completion is done by the job service credit |
| completion.py | APICompletion.completion_for_action | episode function | yield_estimator.py yield_controller (CompletionYieldController, target completion_target); verification of completion is done by the job service credit |
| completion.py | APICompletion._closed_completion_verdict | episode function | yield_estimator.py yield_controller (CompletionYieldController, target completion_target); verification of completion is done by the job service credit |
| completion.py | APICompletion.verify_completion | episode function | yield_estimator.py yield_controller (CompletionYieldController, target completion_target); verification of completion is done by the job service credit |
| configuration.py | APIConfiguration | episode function | yield_estimator.py settings['cost'], settings['parameters']; task.py settings resources/initial_information/handoff_unit/acquired_record_unit |
| configuration.py | APIConfiguration.__init__ | episode function | yield_estimator.py settings['cost'], settings['parameters']; task.py settings resources/initial_information/handoff_unit/acquired_record_unit |
| credit.py | APICredit | episode function | credit.py credit (service credit read from the summary) |
| credit.py | APICredit.credit_kind | episode function | credit.py credit (service credit read from the summary) |
| credit.py | APICredit.project_credit | episode function | credit.py credit (service credit read from the summary) |
| credit.py | APICredit._live_project_credit | episode function | credit.py credit (service credit read from the summary) |
| credit.py | APICredit.credit_view | episode function | credit.py credit (service credit read from the summary) |
| decision_contracts.py | APITaskDecisionContracts | machinery | decision-exchange loop contracts (exchange_decision); offered actions and output schema are task.py output_schema/offered_actions |
| decision_contracts.py | APITaskDecisionContracts.interpretation_context | machinery | decision-exchange loop contracts (exchange_decision); offered actions and output schema are task.py output_schema/offered_actions |
| decision_contracts.py | APITaskDecisionContracts.exchange_schema | machinery | decision-exchange loop contracts (exchange_decision); offered actions and output schema are task.py output_schema/offered_actions |
| decision_contracts.py | APITaskDecisionContracts.exchange_response | machinery | decision-exchange loop contracts (exchange_decision); offered actions and output schema are task.py output_schema/offered_actions |
| decision_contracts.py | APITaskDecisionContracts.validate_contract_exchange_request | machinery | decision-exchange loop contracts (exchange_decision); offered actions and output schema are task.py output_schema/offered_actions |
| decision_contracts.py | APITaskDecisionContracts.validate_contract_exchange_history | machinery | decision-exchange loop contracts (exchange_decision); offered actions and output schema are task.py output_schema/offered_actions |
| decision_exchange.py | APITaskDecisionExchange | machinery | decision-exchange loop (exchange_decision) |
| decision_exchange.py | APITaskDecisionExchange.exchange_decision | machinery | decision-exchange loop (exchange_decision) |
| decision_inputs.py | APIDecisionInputs | episode function | task.py decide (context) |
| decision_inputs.py | APIDecisionInputs.decision_inputs | episode function | task.py decide (context) |
| decision_provider.py | APITaskDecisionProvider | machinery | provider patching / recorded model call; the system makes the model call |
| decision_provider.py | APITaskDecisionProvider.complete_decision | machinery | provider patching / recorded model call; the system makes the model call |
| decision_state.py | APIDecisionState | episode function | messages/internal_summary.py internal_summary + task.py decide |
| decision_state.py | APIDecisionState.decision_state | episode function | messages/internal_summary.py internal_summary + task.py decide |
| episode.py | ExecutionEpisode | episode function | episode.py ApiJobExecution(EpisodeBinding) |
| execution_contracts.py | launch_operation_catalog | episode function | task.py capabilities/service_operation; native_result_operation_catalog not used by launch_api (unplaced) |
| execution_contracts.py | native_result_operation_catalog | episode function | task.py capabilities/service_operation; native_result_operation_catalog not used by launch_api (unplaced) |
| execution_contracts.py | _outcome | episode function | task.py capabilities/service_operation; native_result_operation_catalog not used by launch_api (unplaced) |
| execution_state.py | APIExecutionState | episode function | messages/internal_summary.py internal_summary; task.py resource_capabilities (_practical_context/_result_directory unplaced: results role) |
| execution_state.py | APIExecutionState._delegate | episode function | messages/internal_summary.py internal_summary; task.py resource_capabilities (_practical_context/_result_directory unplaced: results role) |
| execution_state.py | APIExecutionState._practical_context | episode function | messages/internal_summary.py internal_summary; task.py resource_capabilities (_practical_context/_result_directory unplaced: results role) |
| execution_state.py | APIExecutionState.initialize | episode function | messages/internal_summary.py internal_summary; task.py resource_capabilities (_practical_context/_result_directory unplaced: results role) |
| execution_state.py | APIExecutionState._result_directory | episode function | messages/internal_summary.py internal_summary; task.py resource_capabilities (_practical_context/_result_directory unplaced: results role) |
| from_parent.py | APIFromParent | episode function | messages/read_from_parent.py ASSIGNMENT_FORM/read_from_parent; required_return_sources -> messages/final_to_parent.py RETURN_FORM |
| from_parent.py | APIFromParent.required_return_sources | episode function | messages/read_from_parent.py ASSIGNMENT_FORM/read_from_parent; required_return_sources -> messages/final_to_parent.py RETURN_FORM |
| from_parent.py | APIFromParent.child_assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM/read_from_parent; required_return_sources -> messages/final_to_parent.py RETURN_FORM |
| from_parent.py | APIFromParent.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM/read_from_parent; required_return_sources -> messages/final_to_parent.py RETURN_FORM |
| from_parent.py | APIFromParent.prepare_assignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM/read_from_parent; required_return_sources -> messages/final_to_parent.py RETURN_FORM |
| from_parent.py | APIFromParent.initial_references | episode function | messages/read_from_parent.py ASSIGNMENT_FORM/read_from_parent; required_return_sources -> messages/final_to_parent.py RETURN_FORM |
| goal.py | APIGoal | episode function | goal.py GOAL / task.py GOAL_TEXT |
| goal.py | APIGoal.instructions | episode function | goal.py GOAL / task.py GOAL_TEXT |
| instructions.py | instructions | episode function | task.py instructions/GOAL_TEXT/ACTION_TEXT |
| internal_summary.py | APIInternalSummary | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | APIInternalSummary._with_selected_execution_task | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | APIInternalSummary.decision_context | episode function | messages/internal_summary.py internal_summary |
| parent_input_custody.py | APIParentInputCustody | machinery | receipts/custody of parent inputs is the runner's; ASSIGNMENT_FORM fields carry the checked request (a wrong commission just fails) |
| parent_input_custody.py | APIParentInputCustody._versions | machinery | receipts/custody of parent inputs is the runner's; ASSIGNMENT_FORM fields carry the checked request (a wrong commission just fails) |
| parent_input_custody.py | APIParentInputCustody._check_parent_inputs | machinery | receipts/custody of parent inputs is the runner's; ASSIGNMENT_FORM fields carry the checked request (a wrong commission just fails) |
| parent_input_custody.py | APIParentInputCustody._permitted | machinery | receipts/custody of parent inputs is the runner's; ASSIGNMENT_FORM fields carry the checked request (a wrong commission just fails) |
| parent_input_custody.py | APIParentInputCustody._request_schema | machinery | receipts/custody of parent inputs is the runner's; ASSIGNMENT_FORM fields carry the checked request (a wrong commission just fails) |
| parent_input_custody.py | APIParentInputCustody._validate_request | machinery | receipts/custody of parent inputs is the runner's; ASSIGNMENT_FORM fields carry the checked request (a wrong commission just fails) |
| parent_input_custody.py | APIParentInputCustody._launch | machinery | receipts/custody of parent inputs is the runner's; ASSIGNMENT_FORM fields carry the checked request (a wrong commission just fails) |
| parent_input_custody.py | APIParentInputCustody._constraints | machinery | receipts/custody of parent inputs is the runner's; ASSIGNMENT_FORM fields carry the checked request (a wrong commission just fails) |
| received_record_selection.py | APIReceivedRecordSelection | machinery | receipts bookkeeping / received-record custody; no children |
| received_record_selection.py | APIReceivedRecordSelection._received | machinery | receipts bookkeeping / received-record custody; no children |
| received_records.py | APIReceivedRecords | machinery | receipts bookkeeping; no children |
| received_records.py | APIReceivedRecords.received_report_sources | machinery | receipts bookkeeping; no children |
| received_records.py | APIReceivedRecords.received_report_facts | machinery | receipts bookkeeping; no children |
| received_records.py | APIReceivedRecords.received_report_closure_facts | machinery | receipts bookkeeping; no children |
| received_reference_custody.py | APIReceivedReferenceCustody | machinery | receipt/custody check; validate_received_report -> messages/final_to_parent.py validate_report |
| received_reference_custody.py | APIReceivedReferenceCustody.resolve_received_reference | machinery | receipt/custody check; validate_received_report -> messages/final_to_parent.py validate_report |
| received_reference_custody.py | APIReceivedReferenceCustody.validate_received_report | machinery | receipt/custody check; validate_received_report -> messages/final_to_parent.py validate_report |
| received_reference_custody.py | APIReceivedReferenceCustody.received_form_references | machinery | receipt/custody check; validate_received_report -> messages/final_to_parent.py validate_report |
| report_delivery.py | APIReportDelivery | machinery | report_form machinery / report delivery (finish); the system returns final_to_parent result |
| report_delivery.py | APIReportDelivery.finish | machinery | report_form machinery / report delivery (finish); the system returns final_to_parent result |
| report_reference_access.py | APIReportReferenceAccess | machinery | receipt reference resolution (custody is the system's) |
| report_reference_access.py | APIReportReferenceAccess.resolve | machinery | receipt reference resolution (custody is the system's) |
| resource_information.py | APIResourceInformation | episode function | task.py resource_capabilities/capabilities (resource_tool_contracts unplaced: results/practical roles) |
| resource_information.py | APIResourceInformation._resource_information | episode function | task.py resource_capabilities/capabilities (resource_tool_contracts unplaced: results/practical roles) |
| resource_information.py | APIResourceInformation.initial_decision_context | episode function | task.py resource_capabilities/capabilities (resource_tool_contracts unplaced: results/practical roles) |
| resource_information.py | APIResourceInformation.capabilities | episode function | task.py resource_capabilities/capabilities (resource_tool_contracts unplaced: results/practical roles) |
| resource_information.py | APIResourceInformation.resource_tool_contracts | episode function | task.py resource_capabilities/capabilities (resource_tool_contracts unplaced: results/practical roles) |
| result_selection.py | APIResultSelection | episode function | unplaced, library candidate: not carried; result-selection of the results/acquisition role, no use in launch_api; custody; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| result_selection.py | APIResultSelection._target | episode function | unplaced, library candidate: not carried; result-selection of the results/acquisition role, no use in launch_api; custody; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| result_selection.py | APIResultSelection._selector | episode function | unplaced, library candidate: not carried; result-selection of the results/acquisition role, no use in launch_api; custody; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| result_selection.py | APIResultSelection._windows | episode function | unplaced, library candidate: not carried; result-selection of the results/acquisition role, no use in launch_api; custody; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| result_selection.py | APIResultSelection._selection | episode function | unplaced, library candidate: not carried; result-selection of the results/acquisition role, no use in launch_api; custody; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| result_selection.py | APIResultSelection._context_target | episode function | unplaced, library candidate: not carried; result-selection of the results/acquisition role, no use in launch_api; custody; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| retained_protein_reader.py | APIRetainedProteinReader | episode function | unplaced, library candidate: not carried; results-role protein reader; not used by this episode; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| retained_protein_reader.py | APIRetainedProteinReader.retained_protein_structure_reader | episode function | unplaced, library candidate: not carried; results-role protein reader; not used by this episode; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| retained_protein_reader.py | APIRetainedProteinReader._protein_reference_access | episode function | unplaced, library candidate: not carried; results-role protein reader; not used by this episode; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| retained_protein_reader.py | APIRetainedProteinReader._retained_protein_result | episode function | unplaced, library candidate: not carried; results-role protein reader; not used by this episode; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| retained_result_acquisition.py | APIRetainedResultAcquisition | episode function | unplaced, library candidate: not carried; results-role action; not used by this episode; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| retained_result_acquisition.py | APIRetainedResultAcquisition._selected_result_action | episode function | unplaced, library candidate: not carried; results-role action; not used by this episode; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| retained_result_publication.py | APIRetainedResultPublication | episode function | unplaced, library candidate: not carried; results-role publication; not used by this episode; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| retained_result_publication.py | APIRetainedResultPublication._validate_result_body | episode function | unplaced, library candidate: not carried; results-role publication; not used by this episode; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| retained_result_publication.py | APIRetainedResultPublication._read_result | episode function | unplaced, library candidate: not carried; results-role publication; not used by this episode; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| task.py | APIJobTask | episode function | task.py decide/action/TOOLS (task.next -> decide; apply_response -> action; execute -> tools) |
| task.py | APIJobTask.next | episode function | task.py decide/action/TOOLS (task.next -> decide; apply_response -> action; execute -> tools) |
| task.py | APIJobTask.apply_response | episode function | task.py decide/action/TOOLS (task.next -> decide; apply_response -> action; execute -> tools) |
| task.py | APIJobTask.execute | episode function | task.py decide/action/TOOLS (task.next -> decide; apply_response -> action; execute -> tools) |
| task_decision.py | APITaskDecision | episode function | task.py decide/instructions (call/conversation_key are recorded model call machinery) |
| task_decision.py | APITaskDecision.call | episode function | task.py decide/instructions (call/conversation_key are recorded model call machinery) |
| task_decision.py | APITaskDecision.instructions | episode function | task.py decide/instructions (call/conversation_key are recorded model call machinery) |
| task_decision.py | APITaskDecision.conversation_key | episode function | task.py decide/instructions (call/conversation_key are recorded model call machinery) |
| task_state.py | APITaskState | machinery | checkpoint/restore and recorded state; state is rebuilt by internal_summary from recorded outcomes |
| task_state.py | APITaskState.__init__ | machinery | checkpoint/restore and recorded state; state is rebuilt by internal_summary from recorded outcomes |
| task_state.py | APITaskState.bind_execution_context | machinery | checkpoint/restore and recorded state; state is rebuilt by internal_summary from recorded outcomes |
| task_state.py | APITaskState.record_execution_failure | episode function | task.py service_operation failure_outcome |
| task_state.py | APITaskState.restore_checkpoint | machinery | checkpoint/restore and recorded state; state is rebuilt by internal_summary from recorded outcomes |
| task_state.py | APITaskState.restore | machinery | checkpoint/restore and recorded state; state is rebuilt by internal_summary from recorded outcomes |
| task_state.py | APITaskState.record_effect | episode function | messages/internal_summary.py (steps) |
| task_state.py | APITaskState.checkpoint | machinery | checkpoint/restore and recorded state; state is rebuilt by internal_summary from recorded outcomes |
| terminal_execution.py | operation_catalog | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior._operations | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior._assignment | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior._state_directory | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.initialize | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.state | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.as_record | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.child_roles | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.credit_kind | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.assignment_schema | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.permitted_common_actions | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.allowed_children | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.prepare_assignment | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.initial_decision_context | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior._resource_information | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior._resource_instructions | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.instructions | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.decision_context | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.catalog | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.execute | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.completion_for_action | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.fact_sources | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.facts | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.resolve | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.validate_report | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| terminal_execution.py | TerminalExecutionBehavior.credit_view | episode function | unplaced, library candidate: not carried; local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution/local_job_execution; the old class serves another role (local/hpc shell execution or results acquisition) than launch_api (old roles = ('launch_api',)) and its old-Store/old-runner calls (store.db, runtime_actions, Store) have no custody replacement; raises explicitly if reached |
| to_parent.py | APIToParent | episode function | messages/final_to_parent.py RETURN_FORM/final_to_parent/validate_report |
| to_parent.py | APIToParent.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM/final_to_parent/validate_report |
| to_parent.py | APIToParent.facts | episode function | messages/final_to_parent.py RETURN_FORM/final_to_parent/validate_report |
| to_parent.py | APIToParent._live_facts | episode function | messages/final_to_parent.py RETURN_FORM/final_to_parent/validate_report |
| to_parent.py | APIToParent.validate_report | episode function | messages/final_to_parent.py RETURN_FORM/final_to_parent/validate_report |
| waiting.py | APIWaiting | machinery | wait/suspension machinery (suspension_changed); the wait TOOL is task.py wait |
| waiting.py | APIWaiting.suspension_changed | machinery | wait/suspension machinery (suspension_changed); the wait TOOL is task.py wait |
| yield_estimator.py | ExecutionEpisodeYield | episode function | yield_estimator.py yield_controller (CompletionYieldController) |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | yield_estimator.py yield_controller (CompletionYieldController) |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py yield_controller (CompletionYieldController) |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller (CompletionYieldController) |
| yield_estimator.py | ExecutionEpisodeYield._launch_api_yield_controller | episode function | yield_estimator.py yield_controller (CompletionYieldController) |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | episode function | yield_estimator.py yield_controller (CompletionYieldController) |
