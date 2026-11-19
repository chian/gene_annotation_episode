# Blocked and unplaced: A107 execution_job_submission/api_job_execution

Old source was read with `git show 97308b94c:<path>` (git dir `/home/chia/repos/gene_annotation_episode_disk/.git`; the working tree has no `.git`). The folder is a private copy of the shape of the finished A101 sibling carry (same old function list, same role `launch_api`); nothing is imported from another episode. `tests/test_api_job_execution.py` has 8 passing tests (class definition, ten files, no episode import, forms, final_to_parent, controller, credit). Old tests retired in `retired_tests/a107__partner_presence_evidence__execution_job_submission__api_job_execution.tsv`.

## BLOCKED-ON-JOB-SERVICE
- BLOCKED-ON-JOB-SERVICE: job_access.read('api_catalog'); wanted call: `ctx.services['job_access'].read('api_catalog', summary['service'], summary['algorithm'], summary['database'])` (task.catalog_of, from decide and action): the API service executor's operation catalog (old `api_execution.catalog`). Not provided; the read raises.
- BLOCKED-ON-JOB-SERVICE: job_access.read('received_bvbrc_context'); wanted call: `ctx.services['job_access'].read('received_bvbrc_context', summary['resource_id'])` (task.decide: old `api_execution.received_bvbrc_context(context)`).
- BLOCKED-ON-JOB-SERVICE: job_access.read('api_decision_context'); wanted call: `ctx.services['job_access'].read('api_decision_context', summary['resource_id'], summary['service'])` (task.decide: old `api_execution.decision_context(context, view)`).
- BLOCKED-ON-JOB-SERVICE: job_access.api_execute; wanted call: `job_access.api_execute(resource_id=, service=, algorithm=, database=, operation=, arguments=, request=, scope=, input_refs=, immutable_input_versions=, handoff_unit=, acquired_record_unit=, key=ctx.operation_key)` returning `{status, event, feedback, credit, facts}` (old `api_execution.execute`, `credit_view`, `facts`, `completion_for_action`, `verify_completion`). `task.required_member` raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.api_execute')`.
- BLOCKED-ON-JOB-SERVICE: job_access.wait_for_job; wanted call: `await job_access.wait_for_job(resource_id=, service=, condition=, handoff_refs=, key=)` (old `wait` action, `waiting.py`). Raises the same way.
- BLOCKED-ON-JOB-SERVICE: job record kind (handoff row of a declared job ledger work table); wanted call: `store.table(JOB_LEDGER).put({'job', 'event': 'handoff', 'at', 'detail', 'source_ref'})`. `task.write_handoff_record` raises.

## BLOCKED-ON-STORE-ACCESS
- function = `records/service_calls/partner_presence_evidence/api_job_receipts.py::ApiJobReceipts`, pattern = "library not carried": constructor takes the old runner's `bound`. Wanted: `ApiJobReceipts(ctx.store, bound, scope, resource_id, service, request).publish(position, outcome)` in `task.write_handoff_record`. Not imported, not called.
- old call -> intended call: `self.store.db.execute('SELECT request FROM runtime_episodes ...')` in `science._check_parent_inputs` -> none (commission check deleted; the parent copies what the child reads into the assignment).
- old call -> intended call: `self.tool_registry._check_sequence_operand/_sequence` + `self.store.subject_molecule` in `science._validate_blast_api_parent_request` -> not carried (commission check).

## Unplaced old functions
- `science.py` (all 7 rows) and the commission checks of `from_parent.py` (`_permitted`, `_launch`, `_constraints`, `prepare_assignment`): checks of this episode's own commission against the parent's launch row (BLAST-graded request: same service, same query digest, same database; masking/utility inputs; input versions). Rule 1 leaves them nowhere; classified machinery.
- `execution_contracts.py::native_result_operation_catalog`, `resource_information.py` (`NativeResourceInformation`, `resource_tool_contracts`), `from_parent.py::child_assignment_schema` and all of `terminal_execution.py` (28 rows except as_record, practical_estimator, completion_for_action): other roles (results, local, hpc) never reached by the `launch_api` branch; carried by execution_result_acquisition, hpc_job_execution and local_job_execution. Every row is in the "Carried over" table.
- Fact sources of the old shared root without an A107 library function: Rfam, UniProt, AppService, Infernal (preparation and native), RNA structure and comparison, expression NMF, and the BV-BRC data and MinHash families; their fields are not declared in `RETURN_FORM`. Old `validate_report` adapters for them (`rfam_returns`, `uniprot_returns`, infernal/rna/nmf returns) are not carried.
- Old `validate_form` call (`to_parent.validate_report`): A107 has `forms/partner_presence_evidence/communication.py`; the old report was filled by the parent's form (`form_with_facts`), and this episode's `finding` is a plain form, so none is called.

## Contract misfits
- new field: api_job_execution scope; new field: api_job_execution request; new field: api_job_execution input_refs; new field: api_job_execution completion_target (old code had a completion proof, not a numeric target); new field: api_job_execution scientific_question; new field: api_job_execution selected_tool_info (old `services.scientific_parent_task`); the executor-schema properties of the old assignment (service-specific request parameters) are unknown (executor outside the episode trees), so they ride in `request`.
- new field: api_job_execution finding (old code had no typed finding; a plain record of resource, service, handoff, completion, last status, interpretation); new field: api_job_execution initial_report (message field of the commission).
- completion credit may pass its target: the executor's credit view adds `acquired_record_unit` credit beyond one `handoff_unit`; the controller raises `ValueError('completion_credit_exceeds_target')` if the commissioned target is passed. The old controller was accumulation with a practical completion forecast; README 7b maps `PracticalYieldEstimator` to completion.
- `execution_result_origin` is always null in the old live facts and a form has no null type: declared as text, selecting it raises.
- Form field names must match `[a-z][a-z0-9_]*`: the old fact sources `execution.masking_*` (7) and `execution.blast_utility_*` (14) contain a dot and cannot be declared under their old names; they were always empty lists for this role.
- Conditional fact sources existed in the old `fact_sources` only when the resource configuration bound them; the form is static, so the native families that exist in episode_support are declared and the others are not.
- The old frozen closed credit ("later delivery never reprices it") has no counterpart; the system's closure credit is used.
- `ctx.settings` must hold `resources`, `initial_information`, `handoff_unit`, `acquired_record_unit`, `task_yield_profiles` (key `launch_api:<class>` -> `{cutoff, parameters}`); optional `launch_instructions_directory`, `tool_knowledge_directory`.
- The parent `execution_job_submission` folder (not mine) must supply `completion_target`, `scope`, `request`, `input_refs` and `initial_report` (and optionally `scientific_question`, `selected_tool_info`) in its msg_to_child.
- Hook-era files `configuration.py`, `appservice_source.py`, `runtime_credit.py` deleted (not in the old episode tree; AppService path is not part of the ten-file form). Also deleted earlier: `api_job_binding.py`, `runtime_source.py`, old `episode.py`, both old test files.
- A library module (`appservice_results.py`) imports an episode folder module, against the layout rule; reported, not touched.
- No `.git` in the working tree: old code was read from `/home/chia/repos/gene_annotation_episode_disk`.

## Not repaired

- BLOCKED-ON-JOB-SERVICE: job_access.read('api_catalog'|'received_bvbrc_context'|'api_decision_context'), api_execute, wait_for_job; write_handoff_record needs job ledger work table (raises NotImplementedError).
- Return form: execution_result_origin (no null type), dotted execution.masking_*/blast_utility_* fact sources and non-declared families (contract limit).
- Completion credit may pass its target: executor credit can exceed completion_target; the controller's ValueError is the failure.
- Commission checks (_check_parent_inputs, _validate_blast_api_parent_request) not carried (wrong commission just fails).
- Importers of the deleted files now break: execution_result_acquisition/acquisition_source.py (configuration.build_api_service) and episode_support/acquisition/service_calls/{partner_presence,gene_context,evolutionary_history}_evidence/appservice_results.py (out of scope).
