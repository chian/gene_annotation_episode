# Proposed HMMER API resource implementation scope

Record: `HMMER_API_RESOURCE_SCOPE_2026-10-22_001`.

Status: **review proposal; not an adopted implementation or coding assignment**.
This record specifies a possible next increment. It changes neither the fixed
goal nor earlier notes. Source inspection establishes the missing API resource
seam; this document establishes no execution, deployment, authentication,
configured-model behavior or completed scientific work.

The scope is explicitly **HMMER only**: the existing public `phmmer` and `hmmscan`
HTTP capabilities. The new adapter must reject BLAST and other providers before
creating an order. Existing direct HMMER, BLAST and Rfam tools keep their current
contracts and behavior. A future BLAST adapter is separate work, including its
contact, installed-client, request-spacing and RID-specific contracts.

No database, algorithm, scientific itinerary or remote allocation is selected
here. A public HMMER request is not an interchangeable execution of an existing
native corpus/CPU assignment. The assigning scientific episode supplies the
selected job, scope, constraints and typed return form. Launch chooses an actual
eligible resource where that choice remains open. The API child owns iterative
preparation, submission, inspection and repair choices in shared `method_loop`.
Primitive HTTP operations contain no model or investigation loop.

## Existing boundary

`ResourceEpisodes` has an explicit adapter port and API role, but the only
concrete reconstructed adapter is `HomologyResourceAdapter`, which accepts local
launch/results and publishes native homology receivers. Ordinary
`public.hmmer.search` and `collect` submit/wait/acquire within one ordinary action;
they do not provide a launch-only resource handoff. `RemoteSearches` already
owns provider requests, handles and exact HTTP snapshots. Those records are the
reuse boundary, not evidence that the missing API adapter exists.

Native progress and operational proof consumers currently require native
homology status, query/CPU/search-mode operands and phmmer extraction witnesses.
They must not accept fabricated native values for external work.

## Stable outer contracts and new identities

Keep these existing schemas/versions unchanged:

- `resource_launch_assignment_v1`, `resource_results_assignment_v1` and their
  outer schemas in `resource_records.py`;
- `execution_handoff_v1`, its resource selection, input versions and receiver
  shapes;
- native `job_execution_status_v1` and episode `execution_status_v1`;
- the fields of `progress_snapshot_v1`, adding an explicitly tagged external
  status alternative to its status union;
- all existing direct public-search contracts and native profile descriptors;
- the native `ResourceOperationalCredit` implementation/descriptor when API
  support is absent.

Use these new implementation/record versions:

```text
hmmer_service_resource_adapter_v1
public_search_registry_v1
public_search_order_v1
public_search_submission_claim_v1
public_search_operation_v1
external_job_execution_status_v1
hmmer_progress_provider_v1
api_search_handoff_information_v1
api_search_result_publication_v1
api_search_result_publication_row_v1
public_search_result_selector_v1
qualified_api_launch_v1
received_api_search_operational_credit_v1
explicit_resource_credit_dispatch_v1
public_search_http_capture_v1
hmmer_public_client_binding_v1
```

The caller explicitly supplies this immutable registry descriptor:

```json
{
  "version": "public_search_registry_v1",
  "registry_ref": "<actual caller-bound execution_registry reference>",
  "resource_id": "<actual caller-bound resource identifier>",
  "provider": "hmmer",
  "client_binding_sha256": "<64 lowercase hexadecimal characters>"
}
```

`provider` is constant `hmmer` in this increment. The client digest identifies
the actual effective HMMER client implementation and transport configuration,
including its selected transport timeout and fixed endpoint implementation.
The caller retains the reconstructible binding preimage. The application source
pin remains independently checked. No service availability or authentication is
inferred from the existence of this descriptor. No production resource ID is
guessed. The registry is not a second job-status authority. The closed client
binding preimage is exactly `version="hmmer_public_client_binding_v1",
provider="hmmer", transport_timeout_seconds, implementation_sha256,
submit_url_prefix, status_url_prefix, result_url_prefix`. Timeout is a positive
integer. The implementation digest identifies the actual client source, not a
capability-description document. URL prefixes are the actual implemented EBI
HMMER search/status/result prefixes; the binding supplies no arbitrary endpoint
substitution facility. Caller test bindings must identify their fixture client
explicitly rather than claim that a fixture is the deployed public service.

Parent-facing execution identity is the existing `provider_job` reference.
The remote UUID is separately retained in `provider_jobs.remote_id`. Operation
keys retain the existing runtime-selected identity; do not substitute a new key
or derive a second execution handle from a later action.

## Shared request normalization

Extract the current request-building/parsing block of `RemoteSearches.search`
into the following function in `provider_jobs.py`:

```python
def build_search_request(
    *, subject_ref: str, query_fasta: str, algorithm: str, database: str,
    parameters: dict | None = None, page_size: int = 50,
    provider: str = "hmmer",
) -> tuple[dict, list[SequenceRecord]]: ...

def provider_job_reference(operation_key: str, request: dict) -> str:
    return identity("provider_job", {
        "operation_key": operation_key, "request": request,
    })
```

Move that existing block without changing its defaults, operations, errors or
returned parsed-sequence list. Ordinary `search` then calls these two helpers;
its remaining submission, waiting and acquisition path stays unchanged. The API
order calls exactly the same helpers. Do not create a second normalizer.

For existing ordinary callers, preserve canonical request bytes, job IDs,
default dictionaries/page sizes/hit-list sizes, digest representations,
provider-key omission for HMMER, snapshots, exceptions and search/collect
behavior. In particular, adding API registry metadata to the existing request
would change its identity and is prohibited. The helper extraction covers all
current providers even though the new API implementation supports HMMER only.

## Provider operation port

The provider/custody owner supplies:

```python
class ProviderJobOperations:
    def __init__(self, store, remote_searches: RemoteSearches, *, registry: dict): ...

    def order(self, *, operation_key: str, provider: str, subject_ref: str,
              query_fasta: str, algorithm: str, database: str,
              parameters: dict, page_size: int | None) -> dict: ...

    def open_order(self, job_ref: str) -> dict: ...

    async def submit_once(self, job_ref: str, *, operation_key: str,
                          retry_of: str | None = None) -> dict: ...

    def recover_submission(self, job_ref: str, *, operation_key: str) -> dict: ...

    async def status_once(self, job_ref: str, *, operation_key: str) -> dict: ...

    async def result_once(self, job_ref: str, *, operation_key: str,
                          page: int | None, page_size: int | None) -> dict: ...

    def read_operation(self, receipt_ref: str) -> dict: ...
    def read_snapshot(self, receipt_ref: str) -> SourceSnapshot: ...
```

Each async operation performs zero or one HTTP request. It never polls, sleeps,
retries, chooses a timer, substitutes work or cancels another operation.
`recover_submission` performs no HTTP. Provider support is checked before any
order mutation. HMMER results require positive `page` and `page_size`.
`result_once` never inserts a status request: it reuses an exact retained page,
or uses the already captured qualified readiness. Unknown readiness returns
`result_readiness_unknown`; known pending readiness returns `result_not_ready`
without HTTP. The episode can separately select another status observation.

`order` performs no HTTP and creates this immutable sidecar:

```json
{
  "version": "public_search_order_v1",
  "registry_ref": "<registry>",
  "job_ref": "<existing provider_job reference>",
  "order_operation_key": "<original commissioning operation key>",
  "request_sha256": "<digest of canonical provider_jobs.request>",
  "request_ref": "<artifact containing that exact request>",
  "query_fasta_ref": "<artifact containing exact submitted FASTA bytes>"
}
```

The existing request retains subject, FASTA digest, sequence digest, identity
version/representation fields, query length, algorithm, database, parameters and
page size. Defaults normalize through the shared helper to `parameters={}` and
`page_size=50`. Algorithm/database have no invented defaults in API assignments.

New orders start at `provider_jobs.state=not_submitted`; remote handle,
submission, status, result and error are null. `provider_jobs` remains the one
mutable job-status authority. The sidecar is preimage/registry proof only.
Legacy provider jobs lacking that proof produce `unavailable_binding`; this
increment does not silently adopt them or invent historical input custody.

Selected operations produce immutable `public_search_operation_v1` receipts:

```json
{
  "version": "public_search_operation_v1",
  "receipt_ref": "<provider_operation reference>",
  "operation_key": "<unchanged selected operation key>",
  "selection_sha256": "<digest of registry/job/operation/exact operands>",
  "operation": "status",
  "registry_ref": "<registry>",
  "job_ref": "<provider_job>",
  "provider": "hmmer",
  "request_sha256": "<original request digest>",
  "observed_at": "<original UTC receipt observation/publication time>",
  "outcome": "completed",
  "state": "STARTED",
  "provider_chronology": "unknown",
  "remote_id": "<UUID or null>",
  "snapshot_ref": "<snapshot-envelope artifact or null>",
  "result_ready": false,
  "result_cached": false,
  "result_snapshot_refs": [],
  "failure": null
}
```

All fields are required. `operation` is `submit | recover_submission | status |
result`; `outcome` is `completed | failed`. `state` is the state captured by this
operation, not a promise that it supersedes every other receipt. Allowed states
are `not_submitted | submitting | accepted | submission_uncertain | returned |
PENDING | RECEIVED | STARTED | RETRY | SUCCESS | FAILURE | REVOKED`.
`provider_chronology` is constant `unknown`: local response/commit order does not
establish the order of remote execution events. `remote_id` and `snapshot_ref`
are nullable; `result_ready` is nullable boolean; null means no validated remote
readiness observation. `result_cached` is boolean, and `result_snapshot_refs` is
an array of actual validated retained-result snapshot artifacts. Failure is null
or the following closed object:

A recognized status response of FAILURE/REVOKED is a completed observation of
failed physical work, with receipt failure null. The external status below
records `failure_code=remote_job_failed`; failure to obtain/validate the response
is instead a failed operation receipt. Do not discard the actual observation.

```json
{
  "code": "submission_uncertain",
  "native_code": "provider_submission_response_invalid",
  "phase": "submission",
  "submission_outcome": "unknown",
  "prerequisite": null,
  "retry_after_seconds": null,
  "http_status": null,
  "diagnostic_ref": "<artifact or null>",
  "response_snapshot_ref": "<artifact or null>",
  "affected_refs": ["<actual references>"],
  "partial_record_refs": []
}
```

Failure `code` is one of `prerequisite_missing | spacing_required | http_failure |
connection_failed | request_timeout | client_failure | response_invalid |
remote_identity_conflict | submission_uncertain | retry_not_authorized |
submission_in_progress | result_readiness_unknown | result_not_ready |
remote_job_failed | request_conflict | unknown_job | operation_conflict |
input_unavailable | storage_failure | unsupported_provider`.
`phase` is `local_request | local_preflight | submission | status | result |
recovery | storage`. `submission_outcome` is null or `not_sent |
remote_handle_returned | unknown`. `prerequisite` is null or `ncbi_contact |
provider_access_dir | installed_client`; the BLAST-specific values are reserved
failure vocabulary, not enabled adapter capabilities. `native_code` is null or
matches `^[a-z][a-z0-9_]{0,127}$`. Retry seconds are null or nonnegative; HTTP
status is null or an integer 100--599. Diagnostic prose remains in artifacts.

Snapshot envelopes reuse the existing `SourceSnapshot` fields and
`content_ref` serialization. Retain exact response bytes, request/transport
metadata and original retrieval time before interpreting a response. An
operation key and selection digest bind each receipt. Reuse with different
operands fails `operation_conflict`; replay returns the original saved receipt.
`observed_at` is the actual local time at which this receipt's combined facts
are captured for publication. The raw response's original time remains in
`SourceSnapshot.retrieved_at`. Cache facts observed during receipt publication
must not be assigned the earlier response time. Replay preserves both times.

## Submission atomicity, cancellation and recovery

An order is never `submitting` merely because it exists. Only a selected submit
can claim submission. Under the per-job lock, use one actual
`Store.transaction()` (`BEGIN IMMEDIATE`) to validate the order, append the
immutable claim, and transition to `submitting`; commit before HTTP:

```json
{
  "version": "public_search_submission_claim_v1",
  "job_ref": "<provider_job>",
  "registry_ref": "<registry>",
  "request_sha256": "<request digest>",
  "operation_key": "<selected submit operation key>",
  "retry_of": null,
  "claimed_at": "<UTC timestamp>"
}
```

Claims are append-only. Use a unique `(job_ref, predecessor)` where predecessor
is an explicit initial sentinel or a prior `not_sent` receipt reference; nullable
SQLite uniqueness must not permit multiple initial claims.

Use a one-shot nonblocking OS lock (`LOCK_EX | LOCK_NB`) for submission
serialization. This refinement avoids a cancelled executor thread acquiring and
leaking a blocking lock later. A busy different-key caller records its own
`submission_in_progress` failure without POST. A busy same-key caller raises
`ProviderOperationInProgress(job_ref, operation_key)` without creating a second
terminal receipt for the still-running original key. The adapter reports the
condition as failed/in-progress work, not a completed yield observation. A later
explicit recovery action can inspect the original key. There is no polling,
lease, lock timeout or automatic wait/retry policy.

For the selected HTTP call, ownership of the acquired descriptor transfers to
the one-request worker before the coroutine awaits it. The worker owns release
in `finally`. Coroutine cancellation must not cancel a not-yet-started worker
after ownership transfer or close its descriptor while its HTTP call can still
run. Submit the one-shot worker to an executor and await a shielded bridge; do
not propagate coroutine cancellation into the executor future. If scheduling
fails before transfer, the caller closes the descriptor and records explicit
`not_sent` when possible. No scientific decisions run in this worker.

The worker captures the returned snapshot or structured client failure into an
atomic immutable disk capsule before releasing the lock. It uses no Store
handle or Store transaction during HTTP. The coroutine imports that capsule into
Store artifacts/receipts in a later transaction. This capsule is necessary so
cancellation after HTTP does not require repeating the request to recover its
already-returned entity. Callback/finally cleanup must close the descriptor once,
including worker startup failure. Kernel process exit releases locks. A process
death before capsule capture leaves uncertainty; it never authorizes another
POST. A lock alone never authorizes a POST: the durable claim does.

The capsule manifest has exactly `version="public_search_http_capture_v1",
registry_ref, job_ref, operation_key, selection_sha256, operation,
finished_at, snapshot, client_failure`. `snapshot` is null or exactly
`service, url, request, retrieved_at, media_type, transport,
content_file="response.entity", content_sha256, content_bytes`.
`client_failure` is null or exactly `native_code, phase,
submission_outcome, retry_after_seconds, diagnostic_file`; the nullable
diagnostic file is the relative name `diagnostic.json`. Its contents are actual
client diagnostics. Nullable fields retain the failure meanings above. At least
snapshot or client_failure is present; an HTTP error may retain both. The worker
writes entity/diagnostic bytes and the finite manifest in a private directory,
flushes them, then atomically publishes the capsule directory and flushes its
parent. It never overwrites an existing different capsule for the same key.
Store import verifies the selection, relative file names, digest/size and exact
manifest before creating the ordinary snapshot/artifact references. Failed
capsule publication leaves the claim conservative, without a second request.

After obtaining the lock, same-key replay first returns a saved receipt. If
there is a claim but no terminal receipt, recover from the original capsule or
saved submission entity. Parsing a retained valid UUID establishes `accepted`
without HTTP. No retained usable response means `submission_uncertain`, even if
the crash may actually have occurred before send. Do not infer `not_sent` from
exception class, phase, HTTP status or elapsed time.

Different-key submission of an already accepted/cached job returns its existing
identity without POST. If a prior attempt explicitly recorded `not_sent`, a new
selected attempt requires `retry_of` naming that exact current predecessor.
This is explicit child-owned repair within the original assignment. Without
that operand return `retry_not_authorized`. A prior ambiguous attempt can never
be retried through this port. Save response bytes before UUID parsing, including
HTTP error or malformed success entities.

## Concurrent status/results and transaction boundaries

No Store write transaction or read-snapshot context may span awaited HTTP.
Operation preparation/claim, network capture/import, provider-state update,
scientific publication and later C8 progress publication are separate actual
transactions. A helper leaving a caller transaction open across its await must
fail before dispatch, rather than silently hold the transaction.
Status/result HTTP workers use the same Store-free capsule capture/import seam
as submission; only submission needs its per-job POST serialization lock.

Status and result requests may overlap. Keep both immutable per-operation
receipts with their own raw observations and original times. Retained validated
results are append-only by job and exact page selector. Preserve the first
retained capture for a selected page; new operation replay or an already
retained acquisition does not fetch it again. Closure never refreshes a result.

A status update may replace the `latest_status` pointer as the latest locally
captured response, but it cannot clear validated result captures or overwrite
`provider_jobs.result` with null. In the same short status-update transaction,
leave `provider_jobs.state=returned` whenever a validated cached result exists;
otherwise retain this response's recognized provider state. A late `PENDING`
receipt still records `state=PENDING`, with `result_cached=true` and exact
result references if a result was already committed. It does not erase that
result. No local timestamp comparison invents remote chronology.

Failed status/result acquisition retains earlier valid captures and records its
own failure. Current pointers are not historical receipts. Neither a later
response nor a later cache update rewrites an older receipt, an earlier returned
progress snapshot, a completed observation or closed credit.

## Adapter, selected job and handoff

The adapter is `HmmerServiceResourceAdapter`, descriptor
`hmmer_service_resource_adapter_v1`. It implements the existing explicit
resource-adapter methods and has no loop of its own. New-job `job_request`
accepts exactly `provider="hmmer", subject_ref, algorithm=(phmmer|hmmscan),
database`, optional supported HMMER parameters and optional page size. Repair
accepts exactly `{provider: "hmmer", existing_job_ref: reference}`.

`prepare_assignment` validates original scope, input versions, request bytes and
constraints, then calls the shared order with the commissioning operation key.
`adapter_assignment` is exactly `public_search_order_v1`. Parent `job_request`,
software/resource knowledge references and constraints remain unchanged.

The adapter does not expose remote CPU/RAM/scratch/wall allocation controls.
Its selection uses null values only where the parent left those operands open.
Any required unsupported non-null allocation returns
`resource_selection_conflict`; it must not be silently nulled. Caller local
transport limits remain distinct from remote allocation.

New launch tools are `api_search.inspect({})`,
`api_search.submit({retry_of: reference|null})`,
`api_search.recover_submission({})` and `api_search.check_handoff({})`.
The `retry_of` field is required, null for the first selected attempt. Each tool
acts only on the immutable assigned order. Instructions describe iteration and
the configured controller, not a required action sequence.

The adapter constructor is exactly:

```python
class HmmerServiceResourceAdapter:
    def __init__(self, services, store, journal, *,
                 ports: PublicSearchPorts): ...
```

`PublicSearchPorts` is a frozen object with `registry`, `operations` and
`result_publisher` attributes of the types specified here. Its registry must
match the adapter descriptor. This object is not itself serialized as a new
execution identity.

A selected handoff check makes one original-job status observation and verifies
locally reconstructible monitoring/results receivers against that order,
registry/client binding, input versions and UUID. It does not fetch a pending
result to prove a receiving interface. The results receiver has an executable
same-UUID contract: acquire ready requested pages, or return specific not-ready
or remote-failure information. The check establishes addressability, not a
promise of future service retention or successful scientific completion.

Reuse `execution_handoff_v1` with these exact receiver operands:

```text
execution_handle = original provider_job
resource_selection = exact caller-bound API selection
submitted_input_versions = original assigned versions
monitoring = {provider_id: resource_id, target_handle: provider_job,
              contract_ref: "public_search.status.v1"}
results = {provider_id: resource_id, target_handle: provider_job,
           contract_ref: "public_search.results.v1"}
checked_at = original selected check time
check_record_refs = actual saved API proof reference(s)
state = usable; failure = null
```

Unusable checks use the existing resource failure schema; detailed provider
failure facts stay in a declared `api_failure` field and actual diagnostics.
Do not expand generic resource failure codes with arbitrary provider prose.
Map invalid order/assignment to `resource_assignment_conflict`, unsupported
selection/allocation to `resource_selection_conflict`, missing usable receiving
checks to `receiving_interface_unavailable`, and invalid page selection to the
existing selector failure codes. `api_failure` is nullable and has exactly the
closed provider-failure shape above. A nullable common `execution_handoff`
allows failure returns before any usable check; it must not invent a successful
handoff proof.

The proof source provider is `episode.api_search_handoff`; its body has exactly
`version, run_id, episode_id, operation_key, scope, assignment_sha256,
registry_ref, job_ref, request_sha256, status_receipt_ref, execution_handoff,
outcome`. It validates the authoritative assignment, order, request, saved
receipt and original outcome. Its version is
`api_search_handoff_information_v1`. Closure/admission read this proof without
HTTP. API-only fact-source names use `api_*`; common handoff(s) retain their
existing meanings and aggregate only qualified relevant identities.

## Results publication and proof port

The no-network publication port is:

```python
class PublicSearchResultPublisher:
    def publish(self, receipt_ref: str, *, scope: dict,
                operation_key: str) -> dict: ...
```

It loads the original successful result snapshot, checks job/request/scope and
reuses the existing HMMER importer under its normal publication context. The
ordinary importer must not be called without initializing its publication
context. Publication stores its own operation replay and actual row witnesses.
It neither calls `collect` nor performs HTTP. It preserves valid partial writes
and existing source/reference/observation meanings.

The requested-data selector is this closed object:

```json
{
  "version": "public_search_result_selector_v1",
  "provider": "hmmer",
  "first_page": 1,
  "last_page": null,
  "page_size": 50
}
```

First page and page size are positive; last page is null or an integer at least
first page. Null leaves the requested upper bound open. It selects no polling
cadence or number of acquisition turns. Each selected `api_search.acquire`
names one page inside that interval with the exact assigned page size.
Its closed input is `{page: positive_integer}`. Results also expose selected
`api_search.coverage({})`, which reads only the saved acquisition/publication
index. No coverage read fetches or imports a page.

The saved publication source has provider
`episode.api_search_result_publication` and version
`api_search_result_publication_v1`. It binds operation key, registry/job/request,
acquisition receipt, native source, selector, actual publication rows and any
restricted projection-failure codes/locators. The acquisition receipt names
the retained snapshot. No phmmer native byte spans are fabricated.

Each row delivered to the proof/projector consumer has exactly:

```text
version="api_search_result_publication_row_v1",
registry_ref, job_ref, request_sha256, publication_operation_key,
acquisition_receipt_ref, source_ref, subject_ref, provider="hmmer",
page, page_size, hit_ordinal, domain_ordinal|null,
record_ref, record_type=(reference|observation)
```

Native array ordinals are zero-based. A reference uses null domain ordinal;
the hit-level fallback observation when no domains exist also uses null.
Source/context/term publications remain actual outcome records but are not
invented reference/observation witness rows. Coverage reports distinguish pages
actually acquired, known provider page count, requested bounds, unknown count
and projection failures. Source labels remain source assertions.

The declared `api_result_coverage` fact is null before a selected result capture,
otherwise exactly `job_ref, request_sha256, selector, acquired_pages,
page_count, all_requested_pages_acquired, projection_failure_count,
publication_refs`. Page numbers are unique sorted positive integers;
`page_count` is a nonnegative integer or null. Requested completeness is boolean
or null when the provider page count is unknown and the selector is open-ended.
Failure count is nonnegative. Publication references name the actual saved
publication sources. This is acquisition coverage, not scientific completion.

## Async progress and semantic information

Add `external_job_execution_status_v1` as a separate status-union alternative:

```text
version, handle, observed_at, lifecycle_state, result_available,
provider="hmmer", registry_ref, request_sha256, remote_id,
native_state, provider_chronology="unknown", status_receipt_ref,
status_snapshot_ref, result_cached, result_snapshot_refs,
lifecycle_basis, failure_code
```

All fields are required. `remote_id` is the actual UUID, not nullable in a
successful externally observed progress snapshot. `native_state` is one of
`PENDING | RECEIVED | STARTED | RETRY | SUCCESS | FAILURE | REVOKED`.
Lifecycle is `pending | executing | returned | null`. Without a cached result,
map `PENDING/RECEIVED/RETRY` to pending, STARTED to executing, and the three
terminal states to returned. With a validated cached result, lifecycle is
returned and `lifecycle_basis=validated_result_capture`; otherwise the basis is
`provider_status`. Result availability is true for SUCCESS or an actual cached
result, false for the other recognized states. Failure code is null or
`remote_job_failed`. Missing/invalid status fields produce a saved failure,
not an invented PENDING observation. This does not change ordinary collect's
historical parsing behavior.

No queue/execution duration, throughput, log or stage information is invented.
Observation/receipt/capture times are not remote event ordering. Same-state
polls cannot earn information merely through new IDs or timestamps.

`HmmerProgressProvider` supplies synchronous `scope`, `direct_dependencies` and
`as_record`, plus:

```python
async def observe(self, handle: str, requested_fields: list[str], scope: dict,
                  *, operation_key: str | None = None) -> dict: ...
```

Selected-operation replay restores its original provider receipt and delivery
snapshot before any HTTP. A new selected status request first commits its own
actual receipt. The progress provider then computes a semantic projection key
from registry/job/request/UUID, native state, availability/cache facts, validated
result-capture identities, failure code and requested exposed information.
Receipt IDs, capture/source representation IDs and read timestamps are not new
semantic facts. Equal projections reuse the original saved delivery snapshot,
time and provenance. The new physical HTTP receipt remains retained separately
under its operation key; reuse does not erase that attempt. Changed raw status
may be visible without creating a new eligible credit category.
Here a validated result's semantic capture identity is exactly
`(job_ref, request_sha256, page, page_size, entity_sha256)`, rather than its
snapshot-envelope/source reference. A response's receipt identity remains
separate from this delivery-information identity.

Preserve synchronous `ProgressProvider.observe` for existing native/episode
consumers. Add this explicit async path:

```python
async def observe_async(self, target_handle, requested_fields, scope, *,
                        permitted_committed_record_types=(),
                        operation_key=None) -> dict: ...

def _prepare_observation(...) -> ObservationPreparation | dict: ...
def _publish_observation(preparation, raw_job_snapshot=None) -> dict: ...
```

The two entry points share preparation and publication logic. Async dispatch
awaits an awaitable `job_provider.observe` before the publication transaction.
The synchronous entry rejects an awaitable provider with
`asynchronous_progress_observation_required`; it must not start another event
loop. The async path also handles existing synchronous providers. Repeat the
original selected-operation replay check inside publication's transaction.

`WorkflowServices.observe_progress` and its protocol become async and forward
to `ProgressProvider.observe_async`; `MonitorEpisodes.execute` already awaits
awaitable observations. An unsuccessful provider receipt raises
`ContractError("external_progress_observation_failed", detail={receipt_ref,
failure})`. The monitor catches this exact case as a failed provider outcome
with no fabricated progress snapshot or completed observation.

`ProgressInformationCredit` keeps its received-selection interface, caller unit,
formula, baseline and output fields. For external status, validate the new
representation then normalize only to existing eligible tuples:

```text
(lifecycle_state, known_value)
(result_available, boolean)
(failure_code, constrained_code) when non-null
```

Its target-scoped semantic seen set, dependencies and permitted committed
records remain unchanged. It ignores receipt/source IDs, timestamps, raw status
names, unfinished elapsed time and raw log hashes as new categories. Several
novel eligible facts in one received snapshot still earn one caller unit;
repeated same-state receipt IDs earn zero. No scientific/monitoring/operational
channels are summed and no old receipt is repriced.

## Operational qualification and initial unselected Launch

Keep native `ResourceOperationalCredit` unchanged. Introduce:

```python
class ApiSearchInformationReader:
    def as_record(self) -> dict: ...
    def qualify_launch(self, context: BindingContext) -> dict: ...
    def read_handoff_source(self, reference: str, *, scope: dict) -> dict | None: ...
    def qualify_handoff(self, context: BindingContext, qualified: dict,
                        proof: dict) -> None: ...
    def own_result_rows(self, context: BindingContext) -> list[dict]: ...

class ApiSearchOperationalCredit:
    requires_episode_receipts = True
    def __init__(self, reader, *, handoff_unit: float,
                 acquired_record_unit: float): ...
    def __call__(self, context: BindingContext, receiver_selection: dict) -> dict: ...
    def as_record(self) -> dict: ...
```

The API reader has its one actual run/registry identity. Foreign native proof
providers return None. A recognized API proof is fully validated, not silently
discarded. `qualify_launch` also runs with zero known proofs, before any order
exists. It performs read-only request/scope/version/constraint qualification
using the shared request builder, returning exactly:

```text
version="qualified_api_launch_v1", run_id, episode_id, provider="hmmer",
subject_ref, request_sha256, existing_job_ref|null,
immutable_input_versions, resource_selection|null, constraints
```

New-request qualification compares the normalized request digest to the actual
order. Repair qualification requires the same original proved job/provider.
Handoff qualification checks original inputs, selected resource where supplied,
allowed IDs/kinds, supported allocation constraints and adapter order. Results
qualification checks own actual publication rows and the requested page bounds.

Inputs are the existing `BindingContext` plus receiver selection containing
`run_id, episode_id, known_record_refs, initial_known_record_refs`. Initial
references must be known. Preserve the existing contribution meaning/formula:

```text
handoff_unit * newly_received_distinct_(registry, execution_handle)_count
+ acquired_record_unit * newly_received_distinct_canonical_result_record_count
```

Output is exactly `credit, operational_credit, operational_credit_binding,
new_handoff_count, new_acquired_record_count`. Initial inherited contributions
and repeated proof representations earn nothing. The API descriptor version is
`received_api_search_operational_credit_v1`; it records the real reader and the
unchanged caller units, not a new numeric policy.

Explicit caller routing is:

```python
class ResourceCreditDispatch:
    def __init__(self, *, native_projector, api_projector,
                 native_resource_id: str, api_resource_id: str): ...
    def __call__(self, context, receiver_selection) -> dict: ...
    def as_record(self) -> dict: ...
```

For unselected Launch, classify the original request contract before reading
proofs: existing native query/CPU requests use the native projector; explicit
HMMER public-search requests use the API qualifier, including their initial
zero-proof state. Assigned children/results use their selected resource ID.
The dispatch returns one underlying view unchanged; it does not sum scores.
Its descriptor lists actual routes/registry identities and contains no synthetic
combined registry. API support absent means install the original native instance
and descriptor directly, without this dispatch.

## Foreign adapter ownership and reconstruction

Before two adapters coexist, assigned resource roles/results must dispatch
`resolve` and `validate_report` to their selected adapter. Unselected Launch may
consult several adapters only for proofs/references each owns and that qualify
against its original request. Adapters whose request family does not match
return no handoffs/estimates for that Launch; they do not reinterpret its job.

`HomologyResourceAdapter._legacy` must check selected resource ID/kind/registry
before reading `adapter_assignment`, returning None for foreign assignments.
Foreign assignment validation is a no-op; foreign resource-reference resolution
returns false. Handoff arrays dispatch each element by its resource selection.
API fact names do not collide with native facts. These are integration changes,
not adapter-local assumptions.

Composition recognizes `hmmer_service_resource_adapter_v1` and receives actual
caller-bound provider operations/publication ports through this resolver:

```python
def WorkflowServices.public_search_ports(
    self, registry: dict,
) -> PublicSearchPorts: ...
```

The corresponding protocol declares the same synchronous method. It resolves
the explicit saved registry against actual `ToolRegistry.remote_searches`,
clients and the no-network publisher. It performs no HTTP and selects no
configuration. It compares the actual client-binding preimage/digest before
returning ports. `compose_episode_bindings` can retain its existing arguments
because it already receives these services; it calls this method only for the
explicit API descriptor. No API descriptor means no API port construction.

The API descriptor returned by `as_record` is exactly
`version="hmmer_service_resource_adapter_v1", resource_id, registry,
implementation_sha256`; resource_id must equal registry.resource_id. The new
progress constructor is exactly
`HmmerProgressProvider(store, *, run_id, ports: PublicSearchPorts)`.
Its descriptor has exactly `version="hmmer_progress_provider_v1", registry,
implementation_sha256`. A caller-bound progress router may address both native
and API handles, but dispatches by actual registered ownership, not guessed
prefixes. Each underlying provider keeps its real registry. Root owns that
composition wrapper in `assembled_service_setup.py`; its descriptor lists both
actual provider descriptors without inventing another registry.

Caller setup explicitly opts into the HMMER registry/adapter/progress provider,
API qualifier and credit dispatch. Existing no-API setup and descriptor behavior
remain byte-for-byte. An opt-in saved service configuration needs its own new
version rather than changing the meaning of the existing strict configuration.
The root and detached child reconstruct the same saved registry/client binding,
request/order, adapter/progress descriptors, proof readers, units and original
forms. Existing saved-factory and source-pin checks remain the durable worker
mechanism; no private execution loop or implicit factory inference is added.
Missing proof/port/configuration is `unavailable_binding`; mismatched saved
identity is `identity_conflict`, before model transport. No alternative service,
database, algorithm or allocation is substituted.

## Exclusive proposed file ownership

This table is a proposed division for root review, not an assignment. Paths not
listed for an owner are outside that owner's edits. New test files follow the
same owner as their producer. Any added path requires root reassignment first.

| Owner | Source files | Required output / consumer |
| --- | --- | --- |
| P: provider/custody/publication | `gene_annotation_episode/provider_jobs.py`; new `public_search_operations.py`; new `public_search_publication.py`; bounded no-network publication seam in `tools.py` | Shared builder/identity; ordered provider job; claim/capsule/operation receipts; exact saved SourceSnapshot; actual importer/publication witnesses. B and C consume these ports. |
| B: API adapter/proof/operational qualification | New `gene_annotation_episode/hmmer_resource_adapter.py`; `hmmer_resource_information.py`; `api_resource_credit.py` | Adapter descriptor/catalog/assigned operations; checked handoff proof; qualified launch and own result rows; API operational view and explicit dispatch. Root composition consumes descriptors/ports; C consumes no B-private state. |
| C: external progress/received information | New `gene_annotation_episode/hmmer_progress.py`; `progress_records.py`; `episode_monitoring.py`; `episode_progress_credit.py` | External status validator; one-request async provider; semantic delivery reuse; async C8 preparation/publication; unchanged-unit received-information projection. Root services forwards to these ports. |
| Root: caller/composition/integration | `gene_annotation_episode/resource_episodes.py`; `episode_composition.py`; `episode_services.py`; `episode_bindings.py`; `resource_service_setup.py`; `assembled_service_setup.py`; `assembled_case_policy.py` | Foreign-ownership fixes; explicit actual-client port resolution; async service/protocol forwarding; saved opt-in setup and native/API credit routing; reconstruction/integration verification. |
| P tests | New `tests/test_hmmer_api_operations.py`; `tests/test_hmmer_api_publication.py` | Builder compatibility, send/concurrency/cancellation/custody and actual publication checks; no service calls. |
| B tests | New `tests/test_hmmer_api_adapter.py`; `tests/test_hmmer_api_information.py` | Assignment/proof/selector validation, initial zero-proof dispatch, partial results and repeated contribution checks. |
| C tests | New `tests/test_hmmer_api_progress.py` | Real local HTTP fixture responses through async capture/progress/credit; semantic repetition, concurrent result/status and original replay checks. |
| Root tests | New `tests/test_hmmer_api_reconstruction.py`; `tests/test_hmmer_api_connected.py` | Complete shared-loop/durable-worker consumer and native profile regression. Root owns any changes to existing integration tests. |

`acquisition.py`, `blast_search.py`, `resource_records.py`, `homology_jobs.py`,
native `resource_information.py`/`resource_operational_credit.py`,
`tool_configuration.py` and `independent_execution.py` are expected unchanged.
The existing HMMER HTTP primitives and saved worker mechanism suffice. If full
path inspection finds a necessary edit there, root reviews/reassigns it before
coding; this proposal does not authorize silent scope expansion.

## Required verification after adoption

Verification below is proposed, not performed by this record. Use synthetic
scientific content, scripted decisions/controllers and local HTTP fixture
servers for engineering checks. A real service/model/scientific demonstration
is later, explicitly distinguished work.

1. Existing ordinary HMMER, BLAST and Rfam request bytes/IDs/defaults and saved
   fixture outcomes remain unchanged after shared-builder extraction. Existing
   direct search/collect/replay paths need no API sidecar.
2. A selected child order commits exact preimage/registry/input facts at
   not_submitted with zero HTTP. Initial unselected API Launch gets a zero-proof
   operational view without entering the native query/CPU parser. Native setup
   without API retains its original descriptors/views.
3. Two processes selecting submission for one order produce one POST. Same-key
   completed replay is exact. Busy same-key dispatch creates no competing
   terminal receipt. Different keys cannot claim the same predecessor. Explicit
   not_sent retry requires the recorded retry_of; uncertainty never permits it.
4. Cancel during lock contention, before dispatch transfer, during the one HTTP
   request and after response capture. No leaked descriptor or duplicate POST;
   capture survives when actually written. Kill the request owner after claim:
   recovery uses existing capsule/response or returns uncertainty, without a
   lease, timeout or resubmission heuristic.
5. Interrupt after raw response capture but before UUID/receipt publication.
   Recover that original UUID and request without POST. Missing/malformed capture
   remains actionable failure. Legacy no-proof work fails unavailable binding.
6. A pending HMMER status yields a checked original-job monitor/results handoff
   without fetching results. A monitor can close while the job remains active;
   acquisition of a not-ready page returns the specific same-job condition.
7. Commit a valid result while an earlier status request is outstanding, then
   return PENDING. Retain both receipts, preserve the cached result/current
   availability and disclose unknown remote chronology. Old progress/credit does
   not change. Exercise the reverse response order too.
8. Prove no Store transaction/read snapshot remains open during awaited HTTP.
   Another connection can commit relevant independent work while the local
   fixture delays a response. Response import and later C8 publication use
   separate transactions. HTTP never runs inside a scientific publication.
9. Repeated same-state responses with different timestamps/receipt IDs preserve
   the original semantic delivery identity and yield zero additional monitoring
   information. STARTED/SUCCESS or actual failure changes reach the existing
   semantic consumer; no raw-ID or elapsed-time credit appears. Selected replay
   does not poll after the fixture's state changes.
10. Acquire several selected pages, preserve exact original sources and correct
    hit/domain locators, enforce page bounds, and distinguish partial acquisition
    from known complete coverage. A later failed page/projection keeps earlier
    valid publications. Repeated delivery earns no repeated operational credit.
11. Bind native and API adapters together. Foreign adapter assignments never
    enter native parsing; unsupported original request families produce no
    handoffs. Check selected-resource resolution, handoff arrays, initial/final
    forms, actual scope/version references and caller allocation constraints.
12. Through real durable fixture workers and shared method_loop: scientific
    parent commissions Launch, Launch commissions API child, pending handoff
    returns through the original typed form, selected monitor obtains progress,
    and results child acquires original-job evidence. Later parent decisions use
    the returned form. No fixed order is installed by the runtime.
13. Restart the parent/worker with existing handles; recover original order,
    claims, receipts, forms, completion identity and contribution baselines.
    Change a saved client/registry/adapter/credit binding and reject before model
    transport. Parent yield does not cancel remote work or rewrite closed history.

Root must read and accept/revise this complete contract before assigning coding.
The live configured investigation and its source pin/state remain untouched.
