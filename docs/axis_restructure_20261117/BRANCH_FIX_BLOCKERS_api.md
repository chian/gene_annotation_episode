# BRANCH_FIX_BLOCKERS_api (19 November 2026)

What the API branch fix met outside the files it may edit (`episode_support/jobs/`, the A101 episode files), with
the exact change wanted and the real mechanism used meanwhile. Nothing here stopped the A101 `api_job_execution`
episode from running.

## 1. `episode_runtime/job_access.py` (not edited)

No new member and no route-binding change was needed: `ApiJobRoute` has the eight route members
(`ROUTE_MEMBERS`) and is bound through the existing constructor `JobAccess(routes)`. Three facts of the protocol
do not fit the service exactly; each is met in the route:

| Fact | In `job_access.py` | What the API route does | Change wanted, if the owner wants one |
|---|---|---|---|
| NCBI `WAITING` is "accepted, unfinished; not known whether it has begun" | `STATES = ('queued', 'running', 'finished', 'failed', 'cancelled', 'unknown')`: no state says that | maps `WAITING` to `queued` and keeps the provider's word in the check row's reply (`provider_status`) | `STATES = (..., 'accepted')` in `job_access.py`, then `NcbiBlastUrlApi.STATES['WAITING'] = 'accepted'` |
| A provider asks for a minimum time between contacts | `fetch` calls `route.status` and then `route.results` and `route.read` at once; `run` calls `wait` and then `fetch` at once | an ended state is answered from the route's record (no request), the results are fetched once and `read` serves the kept files, and `wait` returns only when the next contact is permitted; so `fetch` after a check that saw the end is one HTTP request | none |
| A refused contact is not an observation of the job | `check` returns `{'status': 'failed', 'failure': ...}` and writes no row | `provider_spacing_required` carries `retry_after_seconds` and `earliest_at` in `failure['detail']`: the monitor's tool returns it as its outcome | none |

## 2. `job_services.CONFIGURATION` takes the part `api` beside the old key set, not instead of it

`job_services(configuration)` takes exactly `CONFIGURATION` (no API resource) or exactly `API_CONFIGURATION`
(`CONFIGURATION` and `'api': {resource_id: <route configuration>}`). The owner's rule is one named set with no
optional part. It was not made so because ten test worlds of other fixers name exactly the old set and are
outside this fix's files. Change wanted when those files are free: in `job_services.py` make
`CONFIGURATION = (..., 'api')` the only set, and add `'api': {}` to the configuration in each of:

- `episode_support/jobs/tests/test_job_services.py`
- `root/a101/sequence_homology_evidence/execution_result_acquisition/tests/test_branch_execution_result_acquisition_model_run.py`
- `root/a102/structural_homology_evidence/resource_result_acquisition/tests/test_branch_resource_result_acquisition_model_run.py`
- `root/a102/structural_homology_evidence/resource_work_submission/tests/test_branch_resource_work_submission_model_run.py`
- `root/a102/structural_homology_evidence/resource_work_submission/local_resource_work_execution/tests/test_branch_local_resource_work_execution_model_run.py`
- `root/a103/gene_context_evidence/execution_job_submission/local_job_execution/tests/test_branch_local_job_execution_model_run.py`
- `root/a104/evolutionary_history_evidence/execution_progress_assessment/tests/test_branch_execution_progress_assessment_model_run.py`
- `root/a107/partner_presence_evidence/hpc_work_planning/tests/test_branch_hpc_work_planning_model_run.py`
- `root/a107/partner_presence_evidence/hpc_work_planning/hpc_resource_prediction/tests/test_branch_hpc_resource_prediction_model_run.py`
- `root/a107/partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/tests/test_branch_hpc_allocation_execution_model_run.py`

## 3. The carried public client is not what the route sends with

The task asked for the carried `PublicClients` code to be reused. Its BLAST path
(`acquisition/sequence_homology_evidence/acquisition.py::PublicClients.blast`) cannot carry the route:

- it runs an installed third-party script (`~/.codex/plugins/cache/.../ncbi-blast-skill/scripts/ncbi_blast.py`)
  whose address is a constant of that script, so it cannot be pointed at a local protocol server, and the
  required offline tests need one;
- it refuses a submission without a contact e-mail address (`ncbi_contact_not_configured`) and the script puts the
  address into the request and the `User-Agent`. No address was given for this work and none was taken from the
  user's configuration.

`PublicClients._http` is a private member of that class and sends a fixed `User-Agent` naming this project. So
the route has its own small sender (`ApiJobRoute._send`: one request, no redirect, no credential, the configured
`client_name`) and reuses the library where the protocol's science is: `blast_search.submission`, `status`,
`document`, `validate_identity`, and `parse_sequences` for the query. The spacing rule (10 s between contacts,
60 s between status requests of one job, a lock file shared by the users of one workspace, the end of a contact
as the time the next is spaced from) is the rule of `PublicClients.blast`, written for the route's own state file.
Change wanted, in the acquisition family (not this fix's files): a public method of `PublicClients` that sends
one request to a given address with a given client name, which `ApiJobRoute._send` then calls.

## 4. Library content that still describes the old operations

`episode_support/instructions/launch/sequence_homology_evidence/api-blast.md`, `api-service.md`,
`api-operations.md` and `api-results.md` describe `api.blast.prepare`, `api.blast.submit`, `api.blast.status`,
`api.blast.fetch`, the request `{subject_ref, program, database, hitlist_size?}` and `PublicClients.blast`. The
A101 API episode offers these entries through its `launch_instructions` lookup. The episode's tool is now
`submit` with the request `{program, database, hitlist_size}` and the query attached by code. The owner's
statements that carry decisions are kept in the route and the prompt (one request per call, the spacing as a
returned fact and not a sleep, an unknown submission is never repeated, the handoff is the accepted RID). The
entries need rewriting by whoever owns the instruction library.

## 5. Old-form API code the route does not use

Still in their old form and not called by the route or the A101 API episode:
`acquisition/service_calls/sequence_homology_evidence/api_services.py` (`APIServicePrimitive`,
`publish_existing_acquisition` on `tools._publications` and `tools.store.transaction()`),
`jobs/service_calls/sequence_homology_evidence/provider_jobs.py` (`RemoteSearches`, its own `provider_jobs` work
tables and polling loop) and `job_provider.py` (the `episode.api_job_receipt` sources). The job's records are now
the `JOB_LEDGER` rows `JobAccess` writes. The publication of a fetched BLAST result as per-HSP observations
(`ToolRegistry._import_blast`) is still not on custody (`AXIS_WAVE_BLOCKERS_a101.md` section 2).

## 6. What the A101 neighbours of the API launch still need (their owners' files)

- The head `sequence_homology_evidence/messages/msg_to_child.py::_results` takes the results assignment from the
  model. It now holds what it needs: the handoff row returned by the launch (`JOB_LEDGER` row; `detail` has
  `resource_id`, `kind: 'api'`, `native: {service, remote_id, expected_seconds, directory, request: {program,
  database, hitlist_size, query_title, query_length, sequence_sha256}}`, `job_sha256`).
- `execution_progress_assessment` (the monitor) is not ported: for an API job its check is
  `job_access.check(ctx, handoff_ref)`; a check that comes before the provider's spacing permits it is the failed
  outcome `provider_spacing_required` with `retry_after_seconds`.
- `execution_result_acquisition`: `execution_results_fetch` already calls `job_access.fetch(ctx, handoff_ref)`;
  for an API job the closure row names `blast_result.json` (the single-query JSON2 report, which `blast_grade`
  grades) and, when the service sent an archive, `blast_result.json2.zip`.
- `execution_job_submission` (the launching parent) was rewritten by the fixer of the local launch while this fix
  ran (its prompt, summary, credit and return; the model now answers `commission_launch` with a resource id). The
  API wiring of this fix is in it: the capabilities lookup describes an API resource from
  `job_access.describe(resource_id)`, and `msg_to_child` builds the API child's assignment (`_api_job`). Its
  `ebi_hmmer` request form (`api_execution_assignment_v1`) is mapped to `fixed_request = {'program': algorithm,
  'database': database}`; no route protocol for `ebi_hmmer` exists, so such a commission fails in the child with
  the job service's own error (`job_resource_not_bound`, or the route's request form not having the parameter).
