# Porting an `api_job_execution` episode onto the API job route (19 November 2026)

The A101 episode `root/a101/sequence_homology_evidence/execution_job_submission/api_job_execution` is ported and
runs (offline against a real local HTTP service, and by the real model against the public NCBI BLAST service).
This is the recipe for the other copies: a102, a103, a104, a106, a107 (a110 has no `api_job_execution`: its
`execution_job_submission` holds only `hpc_job_execution` and `local_job_execution`).

Read first: `episode_support/jobs/api_job_route.py` (the route), the A101 episode's ten files (the worked
example), `LAUNCH_MONITOR_EXTRACT_MECHANICS.md` section 3 (a launching child submits once, returns the handoff,
never waits).

## What exists

| Piece | Where | What it is |
|---|---|---|
| The route | `episode_support/jobs/api_job_route.py`: `ApiJobRoute(configuration, resource_id=)` | one resource of `JobAccess`, `kind = 'api'`, for a public web service that takes a request and works on it afterwards. No credential of any kind is sent |
| The protocol objects | the same module: `PROTOCOLS = {'ncbi_blast': NcbiBlastUrlApi}` | what a job is for one service, its three requests and the reading of its three replies |
| The binding | `episode_support/jobs/job_services.py`: `job_services(configuration)` with the part `'api': {resource_id: <route configuration>}` | `JobAccess` binds the route under the resource id; `job_access.read('resources')` lists it with kind `api`, `job_access.read('describe', resource_id)` is what a decision may know of it |
| A protocol test service | `episode_support/jobs/tests/blast_url_api_server.py` | a real HTTP server on 127.0.0.1 that speaks the NCBI BLAST Common URL API; `route_configuration(service, workspace)` binds a route to it |

Route configuration (every key, no default): `service`, `base_url`, `workspace`, `client_name`, `contact_email`
(`None`: none is sent), `request_spacing_seconds`, `poll_spacing_seconds`, `transport_timeout_seconds`. For the
public NCBI service: `api_world.ncbi_route(workspace)` in the A101 episode's tests (10 s between contacts, 60 s
between status requests of one job).

What the route does, by member (one HTTP request per call; only `wait` sleeps):

| Member | Request | Notes |
|---|---|---|
| `submit(handle, job, files, owner)` | the protocol's submission (NCBI: POST `CMD=Put`) | at most once per handle: intent file before the POST, the answer after it; a recorded answer is returned (`adopted`), a recorded refusal raised again, an intent without an answer is `submission_outcome_unknown` |
| `status(handle, native)` | one status request (NCBI: GET `CMD=Get&FORMAT_OBJECT=SearchInfo`) | an ended state (`finished`, `failed`) is recorded and answered from the record without a request |
| `results(handle, native)` | one result request, once (NCBI: GET `CMD=Get&FORMAT_TYPE=JSON2`) | only for a job recorded as `finished`; the files are kept in the job's directory and `read` serves them |
| `cancel` | none | the service has no cancel: `cancel_not_offered_by_the_service` |
| `await wait(handle, native)` | status requests at the provider's spacing, the first after the service's own estimate | used by `JobAccess.run`; returns when the job has ended and the service may be contacted again |

Failures are `RouteRequestError` and come back from `JobAccess` as `{'status': 'failed', 'failure': {'code',
'detail'}}`: `provider_spacing_required` (not sent; `retry_after_seconds`, `earliest_at`),
`provider_connection_failed`, `provider_request_timeout`, `provider_http_<status>`,
`provider_redirect_not_followed`, `provider_submission_response_invalid`, `provider_status_response_invalid`,
`provider_result_response_invalid`, `submission_outcome_unknown`, `results_not_available`, `job_state_unknown`.
Every failure of `submit` says in `detail['sent']` whether the request was sent: `False`, `True` or `'unknown'`.

## Step 0: is the axis's service one the route can reach?

The route is for public, unauthenticated services. Which services each copy names today:

| Axis | Episode | Services its files name | Route protocol |
|---|---|---|---|
| a101 | `sequence_homology_evidence/.../api_job_execution` | `ncbi_blast` | `NcbiBlastUrlApi` (done) |
| a102 | `structural_homology_evidence/.../api_job_execution` | the same A101-shaped job block (`api_catalog`, `api_execute`) | write the protocol of its service first (step 1) |
| a103 | `gene_context_evidence/.../api_job_execution` | `ebi_hmmer`, `bvbrc_data` | `ebi_hmmer` needs a protocol (step 1). BV-BRC is not ported here: no login or token is ever used |
| a104 | `evolutionary_history_evidence/.../api_job_execution` | `ebi_hmmer`, `uniprot`, `ncbi_blast`, `bvbrc_data`, `bvbrc_appservice` | `ncbi_blast` exists; `ebi_hmmer` needs a protocol; `bvbrc_appservice` needs a login and stays out |
| a106 | `perturbation_evidence/.../api_job_execution` | `bvbrc_appservice` only | not portable onto this route (authenticated service): report it as that episode's blocker |
| a107 | `partner_presence_evidence/.../api_job_execution` | `ebi_hmmer` | needs the `ebi_hmmer` protocol (step 1) |

A service that answers immediately (UniProt lookups) is not a job: it is an ordinary tool of the episode that
needs it, not a route.

## Step 1 (only for a service without a protocol): add a protocol object to `api_job_route.py`

A protocol is a class with the members `NcbiBlastUrlApi` has; `ApiJobRoute` calls nothing else:

| Member | Returns |
|---|---|
| `service` | the service name (the key in `PROTOCOLS`) |
| `describe()` | closed JSON a decision may read; must hold `protocol` (text), `job` (the job's keys), `request_schema` (JSON schema of the parameters a model builds; every property with `type` and `description`), `staged_inputs` (`{job key: what the staged file holds}`), `result_files`, `states`; a service whose programs take different molecules adds `query_unit_by_program` |
| `prepare(job, files)` | the request the job is, with its staged input read (closed JSON; kept as `request.json`); raises `ValueError` for a job that is not of the form |
| `submission_request(prepared)`, `status_request(remote_id)`, `result_request(remote_id)` | `(method, fields)` of the one HTTP request |
| `read_submission(body)` | `(remote id, expected seconds or None)`; `ValueError` when the reply holds no job identity |
| `read_status(body)` | `{'state' (a state of `job_access.STATES`), 'provider_status', 'has_hits'}`; `ValueError` when unreadable |
| `read_result(body, prepared)` | `[(file name, media type, bytes)]`; `ValueError` when the reply is not this job's result |
| `information(body)` | the protocol lines of a reply, kept in the reply artifact |

Rules: read replies with the library's existing readers (for EBI HMMER: `parse_hmmer` and the status reading of
`acquisition/sequence_homology_evidence/acquisition.py` and `jobs/service_calls/*/provider_jobs.py`); do not write
a second reader. The route sends form fields (`POST`: urlencoded body, `GET`: query); a service that takes a JSON
body (EBI HMMER `POST /search/phmmer`) needs `_send` to take a body kind from the protocol: add it there, once.
Register the class in `PROTOCOLS`. Test it in `episode_support/jobs/tests/` against a real local HTTP server that
speaks that service's protocol (copy the shape of `blast_url_api_server.py` and `test_api_job_route.py`); no mock
and no replaced client.

## Step 2: the episode's ten files (copy the A101 files, then make them the axis's own)

Delete the old executor path first (`required_member`, `write_handoff_record`, `service_operation`, `wait`,
`capabilities`, `catalog_of`, every `read('api_catalog' | 'api_decision_context' | 'received_bvbrc_context' |
'api_capabilities' | 'launch_catalog')`, `api_execute`, `wait_for_job`, `launch_operation`), then write the new
path. Every copy is private: copy the A101 file into the axis's folder and edit it there; no import from A101.

| File | What it holds after the port |
|---|---|
| `goal.py` | the four texts; the goal says: build the request of the assigned job, submit it once through the job service, end at handoff |
| `messages/read_from_parent.py` | `ASSIGNMENT_FORM`: `resource_id`, `service`, the query (or other operand) as `record_refs` fields, `fixed_request` (the request parameters the parent fixed), `launch_instructions` (optional), `completion_target`. No `version`, `scope`, `immutable_input_versions`, `initial_report`. `read_from_parent` is the only reader of the assignment |
| `messages/internal_summary.py` | the parent input, the operand read through `view.records` (subject, sequence artifact, molecule, length), `submissions` (request, status, `failure_code`, `sent`, `retry_after_seconds`), `handoff_refs`, `lookups`, `credit` from `view.controller_state` |
| `task.py` | `SERVICES = ('job_access',)`; `TOOLS`: `submit` and the two library lookups; `decide`, `action` as below |
| `credit.py` | `completion_target` when a held `JOB_LEDGER` row among `summary['handoff_refs']` is a handoff, else `0.0` |
| `yield_estimator.py` | `CompletionYieldController` toward `parent_input['completion_target']`; profile key `launch_api:` + request class from `parent_input` (service, fixed program, fixed database) |
| `messages/final_to_parent.py` | `RETURN_FORM`: `credit`, `finding` (three counts), selectable `execution_handoff_refs` (`record_refs`) and `execution_completed` (boolean). Nothing a model wrote; no result fields |
| `episode.py` | unchanged |

`task.py` in detail:

1. `decide(summary, feedback, ctx)` reads `ctx.services['job_access'].read('describe', summary['resource_id'])`
   and returns one `ModelRequest`. **The prompt is the first thing to check** (owner, 19 November 2026). Print it
   (`api_world.show(asyncio.run(linked.next_decision()))`) and check it against this list:
   - the instructions open with what the episode is for (launch step of one job; build, submit once, end at
     handoff; do not wait, ask status or fetch), then where the assigned job is, then the tools, the outcomes
     and what earns credit; one short paragraph each;
   - the owner's wording that carries a decision stays ("Keep the original inputs, request, resource and parent
     constraints fixed"; "a missing reply does not establish that no job was created"; at the handoff further
     credit is exactly zero);
   - no old-runner text (transports, receipt ledgers, "the episode iterator", `report_update`, waits);
   - the context holds, once each: `assigned_job` (service, resource, the operand by reference with its molecule
     and length, `fixed`, `open`), `service` (name, protocol, `request_form`, seconds between contacts), `tools`
     (name, what it does, what to give), `progress` (handoff established, submissions, lookups), `credit` (now,
     what the handoff earns), `feedback`. No controller record, no time accounting, no second copy of the
     assignment, no sequence text.
2. The answer schema is `{'action', 'request', 'lookup'}`: `request` is the service's request form or `null`,
   `lookup` an operation of a library with `arguments_json` or `null`. The model is shown each parameter's type,
   allowed values and meaning; `action` validates the answer against the route's whole `request_schema`.
3. `action(response, summary, records, ctx)` ties the request to the assigned job and raises `Rejected` otherwise:
   the request must be of the service's form, equal every parameter of `summary['fixed_request']`, and (where the
   service has `query_unit_by_program`) name a program that takes the operand's molecule. The operand is never in
   the model's answer: `action` puts the held record's reference into the `ToolCall`.
4. `submit(arguments, ctx)` is one call: `ctx.services['job_access'].launch(ctx, resource_id, {**request,
   <staged input key>: <file name>}, inputs={<file name>: <held artifact ref>})`. It returns `handoff_refs`
   (`[launched['handoff_ref']]` or `[]`), `status`, and for a failure `failure_code`, `sent`,
   `retry_after_seconds`. It writes nothing itself: `JobAccess` writes the handoff row and the reply artifact
   through `ctx.store`, and a rerun of the unit does not submit again.
5. No `wait`, no status, no fetch, no capabilities tool: the launching child ends at handoff. The monitor
   (`execution_progress_assessment`: `job_access.check(ctx, handoff_ref)`) and the result acquisition
   (`execution_result_acquisition`: `job_access.fetch(ctx, handoff_ref)`) work from the handoff row.

## Step 3: the launching parent (`execution_job_submission`)

In the parent's own files (A101's are the example; the rest of the A101 parent, its prompt included, was rewritten
the same day by the fixer of the local launch, and the API parts below are in it):

- `task.py`: delete the `job_access.read('validate_assignment', ...)` call of `_bound` (the request is validated
  in `read_from_parent`), and make the capabilities lookup describe an API resource from
  `ctx.services['job_access'].describe(resource_id)` (`service`, `tool_names: ['submit']`, `request_parameters`,
  `api_configuration_facts`); delete `received_bvbrc_context` and `received_bvbrc_values`.
- `messages/msg_to_child.py`, slot `launch_api`: build the child's assignment from the chosen request (A101:
  `_api_job(request)` gives the query subject and the fixed parameters for each request form), the service from
  the capabilities lookup in the summary, `input_refs` from the records the parent holds, `completion_target`
  from `handoff_unit`; select `('execution_handoff_refs', 'execution_completed')`.
- `messages/read_from_child.py` is unchanged: the handoff row comes up in `execution_handoff_refs` and the parent
  holds it as `returned`.

## Step 4: the world and the tests (real only)

Copy and adapt, in the episode's `tests/`:

| File (A101) | What it is |
|---|---|
| `api_job_execution/tests/api_world.py` | the world: Store with the operand, `job_services` with `'api': {resource: route}`, frozen libraries, settings (`task_yield_profiles` and the two library directories), the entry input; `ncbi_route(workspace)`; `show(request)` |
| `api_job_execution/tests/test_api_job_execution.py` | no model: class and forms; the printed request and its content; `action` admissions and rejections with a real `DecisionContext` over the run's job service; `run_unit` of a lookup and of `submit` against the local protocol service; handoff row, credit, controller stop, return, resume without a second submission; a refused and a too-early submission as outcomes |
| `api_job_execution/tests/test_branch_api_job_execution_model_run.py` | real model, real public service, two tests on one durable world: (1) the model builds the request, the handoff, resume; (2) the route's wait without a deadline, then check and fetch in custody through the `job_probe` test episode. A public queue can be long: a later process given `A101_API_BRANCH_DIRECTORY=<the printed world directory>` resumes the recorded run there (no model call, no second submission) and goes on waiting for the same job |
| `execution_job_submission/tests/launch_world.py`, `test_api_launch.py`, `test_branch_api_launch_model_run.py` | the parent: capabilities lookup from the route, the commission the child's form admits; by the real model, parent and child to the handoff in custody (local protocol service) |

Commands (one workflow at a time, a fresh run directory each time):

```
# offline (the local service is on 127.0.0.1; the fixture exempts it from the blocked proxy)
bash tools/one_workflow.sh --slot <slot> runs/<fresh> -- env HOME=$PWD/runs/<fresh>/home \
  http_proxy=http://127.0.0.1:9 https_proxy=http://127.0.0.1:9 PYTHONDONTWRITEBYTECODE=1 eatmydata \
  .venv/bin/python -m pytest -p no:cacheprovider --basetemp=runs/<fresh>/tmp <paths>
# real model (and, for the child's branch test, the real public service)
bash tools/one_workflow.sh --slot <slot> runs/<fresh> -- env HOME=$PWD/runs/<fresh>/home \
  CODEX_HOME=/home/chia/.codex PYTHONDONTWRITEBYTECODE=1 eatmydata .venv/bin/python -m pytest \
  -p no:cacheprovider --basetemp=runs/<fresh>/tmp <path> -m model_run -v --tb=short -s
```

Against a public service: one tiny request per test run, the service's documented spacing in the route
configuration, no contact address unless the owner supplies one, never a credential. An unavailable service or a
long queue is a result to report, not a failure to hide.

## Checks before calling a copy done

- `grep -n "BLOCKED\|NotImplementedError\|bvbrc\|api_execute\|wait_for_job\|required_member" <episode files>` is
  empty;
- the printed request passes the prompt list of step 2;
- the offline tests and the model run pass, and the model run's printed units show the request the model built
  and the handoff row;
- the folder still holds exactly its ten files (worlds and tests are in `tests/`).
