# Blocked and unplaced: A106 perturbation_evidence/execution_job_submission/api_job_execution

Old source was read with `git show 97308b94c:<path>` (git dir `/home/chia/repos/gene_annotation_episode_disk/.git`; the working tree has no `.git`). The folder is a private copy of the shape of the finished A101/A102 api_job_execution carries; nothing is imported from another episode. No old test existed at 97308b94c (only `tests/__init__.py`); the hook-era `tests/test_api_job_runtime.py` is retired. `tests/test_api_job_execution.py` has 8 passing tests (launcher run `runs/cov_a106_01_u126_1`).

## BLOCKED-ON-JOB-SERVICE
- BLOCKED-ON-JOB-SERVICE: job_access.read('api_catalog'); wanted call: `ctx.services['job_access'].read('api_catalog', summary['service'], summary['algorithm'], summary['database'])` (task.catalog_of, from decide and action): the AppService executor's operation catalog (old `api_execution.catalog`, `service.launch_catalog(request)`). Not provided; the read raises.
- BLOCKED-ON-JOB-SERVICE: job_access.read('api_decision_context'); wanted call: `ctx.services['job_access'].read('api_decision_context', summary['resource_id'], summary['service'])` (task.decide: old `api_execution.decision_context`: api_service, api_request, received progress events, completion).
- BLOCKED-ON-JOB-SERVICE: job_access.api_execute; wanted call: `job_access.api_execute(resource_id=, service=, algorithm=, database=, operation=, arguments=, request=, scope=, input_refs=, immutable_input_versions=, handoff_unit=, acquired_record_unit=, key=ctx.operation_key)` returning `{status, event, feedback, credit, facts}` (old `api_execution.execute`, `credit_view`, `facts` incl. `application_fact_sources` projection, `completion_for_action`). `task.required_member` raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.api_execute')`.
- BLOCKED-ON-JOB-SERVICE: job_access.wait_for_job; wanted call: `await job_access.wait_for_job(resource_id=, service=, condition=, handoff_refs=, key=)` (old `wait` action, `waiting.py`).
- BLOCKED-ON-JOB-SERVICE: job record kind (handoff row of a declared job ledger work table); wanted call: `store.table(JOB_LEDGER).put({'job', 'event': 'handoff', 'at', 'detail', 'source_ref'})`. `task.write_handoff_record` raises.

## BLOCKED-ON-STORE-ACCESS
- function = `records/service_calls/bvbrc_appservice_receipt_values.py::build_appservice_receipt` and `confirm_appservice_effects` (with `records/service_calls/bvbrc_appservice_records.py`), pattern = "library not carried": the receipt of the retained AppService response was built over the old `bound`; wanted in `task.write_handoff_record`. Not imported, not called.
- old call -> intended call: `self.store.db.execute('SELECT ... FROM runtime_episodes ...')` in `_check_parent_inputs` / `execution_state.initialize` -> none (the parent copies what the child reads into the assignment; commission check deleted).

## Unplaced old functions
- `OperationalOperations.resource_tool_contracts`: assembles the commission-route contracts of every resource for the head's text; the parent writes its own text.
- `native_input_custody.py` (all 17 rows), `received_evidence.py` (all 14 rows), `to_parent.py::resolve`, `_application_resolve_own`, `_application_resolve_reference`: reference resolution/validation of received reports and native inputs over the old receipts and `runtime_*` tables; the system checks held records and this episode has no children. Classified machinery in the "Carried over" table.
- Old `validate_form` call (`validate_report` of to_parent): A106's form validation is `forms/perturbation_evidence/communication.py::validate_form` over the old `resolve`; this episode's finding is a plain form, so none is called.
- `_application_facts` (to_parent): the projection `project_application_facts(body, sheet=, components=)` of the latest adapter result (`read_latest_adapter_result` over `records/service_calls/bvbrc_appservice_saved_results.py`, old publications store) is not called: the `bvbrc_application_outcomes` value must come from the job service facts (`summary['facts']`).

## Contract misfits
- new field: api_job_execution scope; new field: api_job_execution input_refs; new field: api_job_execution completion_target (old code had a completion proof, not a numeric target); new field: api_job_execution initial_report (message field of the commission); new field: api_job_execution service (the old per-resource executor schema carried it; the hook-era assignment had only scope, resource_id, request); new field: api_job_execution immutable_input_versions and launch_instructions (old code re-read them from the parent launch assignment; now copied into the assignment); the executor-schema properties of the old assignment are outside the episode trees, so the service request rides in `request`.
- new field: api_job_execution finding (old code had no typed finding; a plain record of resource, service, handoff, completion, last status, interpretation).
- completion credit may pass its target: the executor's credit view adds `acquired_record_unit` credit for acquired result identities beyond one `handoff_unit`; the controller raises `ValueError('completion_credit_exceeds_target')` if the commissioned target is passed. The old controller was accumulation with a practical completion forecast; README 7b maps `PracticalYieldEstimator` to completion.
- The old frozen closed credit ("later delivery never reprices it") has no counterpart; the system's closure credit is used.
- `ctx.settings` must hold `resources`, `initial_information`, `handoff_unit`, `acquired_record_unit`, `task_yield_profiles` (key `launch_api:<class>` -> `{cutoff, parameters}`); optional `launch_instructions_directory`, `tool_knowledge_directory`.
- The parent `execution_job_submission` folder (not mine) must supply `completion_target`, `scope`, `service`, `request`, `input_refs`, `immutable_input_versions` and `initial_report` in its msg_to_child.
- Conditional fact sources (the AppService support refs, the application outcomes) existed in the old `fact_sources` only when the resource configuration bound them; the form is static and declares both as selectable.
- `perturbation_evidence/episode_contract.py` docstring still names `binding.ApiJobBinding` (deleted); `execution_result_acquisition/tests/test_result_acquisition_runtime.py` imports the old `ExecutionEpisode` from this folder's `episode.py` (now `ApiJobExecution`): both belong to other jobs.
- No `.git` in the working tree (`/tmp/ramrepo`): old code was read from `/home/chia/repos/gene_annotation_episode_disk`.

## Not repaired
- BLOCKED-ON-JOB-SERVICE items above (job_access api_catalog, api_decision_context, api_execute, wait_for_job, job record kind) and BLOCKED-ON-STORE-ACCESS items (appservice receipt library not carried): real limits of the system.
- Completion credit may pass its target (contract misfit above).
- tests for decide, action and the task.py tools cannot run a real unit until job_access exists.
