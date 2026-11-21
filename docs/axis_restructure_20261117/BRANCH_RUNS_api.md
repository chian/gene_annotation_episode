# BRANCH_RUNS_api (19 November 2026)

Chosen branch kind: an API branch. Episode: A101 `sequence_homology_evidence/execution_job_submission/api_job_execution`
on the public, unauthenticated NCBI BLAST service (`service='ncbi_blast'`, blastp, swissprot, one short protein query).
No BV-BRC, no credential, no login. (All 17 `api_job_execution` copies under a101..a107 share the same job-service block;
a101/a102/a106/a107 read `api_catalog`/`api_decision_context`/`received_bvbrc_context` and call `api_execute`, a103 and a104
call `api_execution`/`launch_catalog`; none was ported, see below.)

## Branch 1: `api_job_execution` alone (ncbi_blast, real model, network open): FAIL

Test written: `gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/execution_job_submission/api_job_execution/tests/test_branch_api_job_execution_model_run.py`
(`@pytest.mark.model_run`). World: real Store, RunJournal, `job_services(configuration)` (only a local route is configurable),
the episode's own settings (`resources`, `initial_information`, `handoff_unit`, `acquired_record_unit`, `task_yield_profiles`
with key `launch_api:api_ncbi_blast_blastp_swissprot_handoff`, both library directories), real `ModelProvider`,
assignment `api_service_assignment_v1`, `completion_target` 2.0.

Run dir: `runs/brm_api_2` (log `runs/brm_api_2.log`). (`runs/brm_api_1` is an empty-start leftover of a rejected launch; ignore it.)

Journal facts: the run fails in its first `decide`, before the model is asked. No unit, no model call, no credit, no
`ended_by`; no request to NCBI was built or sent, so no response, rate limit or unavailable-service outcome exists to
report. JOB_LEDGER: nothing written. Resume: not reached. Model decisions: none.

Error: `task.py:137 decide` -> `episode_runtime/services.py:80 ask` ->
`AttributeError: 'JobAccess' object has no attribute 'received_bvbrc_context'`.

Classification: LIBRARY/RUNNER (the missing `job_access` API service), surfaced in EPISODE (`task.py` carried but not ported).
Diagnosis: the episode's whole executor is `BLOCKED-ON-JOB-SERVICE` (task.py docstring). `JobAccess`
(`episode_runtime/job_access.py`) has only `resources`, `describe`, `launch`, `check`, `fetch`, `cancel`, `run`, and
`job_services` (`episode_support/jobs/job_services.py`) can bind only `LocalJobRoute` and `PbsSshRoute`: there is no API
route, so no code path sends an HTTP request. The episode still needs, in order: `read('received_bvbrc_context')`
(task.py:137, hit first), `read('api_decision_context')` (:142), `read('api_catalog')` (:112, also called again in `action`),
`api_execute(...)` (via `required_member`, task.py ~215) and `wait_for_job`; and `write_handoff_record` (task.py ~200) raises
`NotImplementedError('BLOCKED-ON-JOB-SERVICE: job record kind ...')`, so even a successful call could not write the JOB_LEDGER
handoff row. Further, the library `episode_support/acquisition/service_calls/sequence_homology_evidence/api_services.py`
(`APIServicePrimitive`: `prepare`/`invoke`/`decode`/`publish`) takes the old `tools`/`store.validate_scope`, and
`publish_existing_acquisition` uses `tools._publications`, `tools.store.transaction()`: old-runner machinery, not on custody.
Smallest suspected fix: add an API route class (a `JobAccess` route with `kind='api'`, built from `APIServicePrimitive` for
`ncbi_blast`/`uniprot`, `invoke` over plain HTTPS) to `job_services.py` configuration (`'api': {resource_id: {...}}`); give
`JobAccess` (or a wrapper) `api_catalog(service, algorithm, database)`, `api_decision_context(resource_id, service)`,
`received_bvbrc_context(resource_id)` (return `{}` for non-BV-BRC) and `api_execute(...)` returning `{'status','event','feedback','credit','facts'}`
with the handoff row via `store.table(JOB_LEDGER).put`; replace `write_handoff_record`'s raise with that table write. Then the same
test can be rerun unchanged except that the settings `resources['ncbi_blast']` names the API route.

## Branch 2: with the launching parent: NOT RUN

Per the instructions a chain stops at its first failing branch. The parent (`execution_job_submission`) commissions this
episode through its `msg_to_child`; it cannot do better than this child, which fails before any model call.

## Summary of what was not verified (all blocked by branch 1)

Request the model builds; real NCBI response; rate-limit or unavailable-service handling; JOB_LEDGER and journal records;
resume without a second API call; RETURN_FORM admission of the controlled fields.
