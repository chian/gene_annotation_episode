# HMMER API coding assignment and shared-port clarification

This is a new permanent record. It does not replace proposal 001 (SHA256
802e9896cf733840b9d4b4a0b360e427e4a729179047fcaedf542e6d238d036f).
Root has read that complete proposal and adopts it for isolated implementation,
with the explicit port and ownership details below. Adoption authorizes coding;
it does not establish verification, deployment, scientific use or production
configuration. The fixed goal and the 41-item checklist remain unchanged.

## Shared outputs consumed by the parallel workloads

P owns `PublicSearchPorts` in `public_search_operations.py`. It is a frozen
dataclass with exactly `registry`, `operations`, `result_publisher` attributes.
The registry is a detached canonical-JSON copy of the validated descriptor.
Construction does not observe HTTP or order work. B and C import that type from
this module. No additional status authority or semantic execution handle is
introduced by the dataclass.

P's `ProviderJobOperations` additionally supplies this synchronous, read-only
port, so B/C do not depend on its private SQL tables:

```python
def inspect(self, job_ref: str) -> dict: ...
```

It returns exactly `order, request, state, remote_id,
latest_operation_refs, submission_claim_refs, result_receipt_refs`. `order` is
the complete original `public_search_order_v1`; `request` is the original
normalized provider request. State and remote ID come from the authoritative
provider job. The three arrays contain actual retained receipt/claim identifiers,
with deterministic saved order; an empty array means no such saved object.
It performs no HTTP, import, recovery or statistical update. Missing original
binding is `unavailable_binding`, rather than an invented empty order.
`open_order` returns just the original order object. All dictionaries returned
across these ports are detached JSON values.

P owns the no-network publisher constructor:

```python
PublicSearchResultPublisher(store, tool_registry, *, operations)
```

It uses that registry's existing importer/publication machinery and the exact
provider operations instance. `publish` retains proposal 001's signature and
publication/witness output; it does not call ordinary `collect` or submit.
P supplies a helper to validate/describe the actual HMMER client binding, used
by root's resolver. It derives implemented endpoints and client source digest
from the actual client; fixture clients must have explicit fixture bindings.
Neither a capability description nor a caller-provided digest alone proves the
binding. P names this helper and its callable signature to root before root
wires it; it must not require B/C to choose a configuration.

The existing resource-adapter protocol remains the B/root boundary. B supplies
`HmmerServiceResourceAdapter`, `ApiSearchInformationReader`,
`ApiSearchOperationalCredit` and `ResourceCreditDispatch` with proposal 001's
interfaces. C supplies `HmmerProgressProvider` and the external status union,
async C8 path and unchanged-unit information projection. Both consume the
immutable registry, provider receipts and saved snapshots through P's public
ports. No workload waits for another's implementation to begin: these fixed
contracts are sufficient for independent coding. Connected checks wait for the
producers' actual files.

## Execution location and exclusive ownership

The only coding checkout is
`/tmp/gene-annotation-hmmer-api-20261022-001`. Its initial 122 Python sources
match live pin
`a192366fa67def7bbeb7b7ef87330e402f4244c154d2dd635444f5e98265383a`.
The new factual commission-frame module is not included in this API baseline;
its separately verified capsule remains intact. Original tests, package data,
instructions and design references are copied for implementation context.
The live repository's application source and every active investigation remain
untouched. No worker is authorized to operate on a live run or use real public
services/models for these engineering tests.

P, B, C and root retain exactly proposal 001's file ownership. The native
`HomologyResourceAdapter` is defined inside root-owned `resource_episodes.py`,
so its foreign-assignment fix is root's responsibility. Each worker reads full
affected producer and consumer paths before editing; discovers a necessary
out-of-scope edit by reporting the exact path/reason to root; and preserves the
other workers' files. Each owns only its new test files and may run relevant
existing checks without editing them. No nested coding delegation is needed:
the three workers plus root use the four available slots.

Root performs caller/composition/reconstruction integration and reviews all
producer outputs. Tests use actual durable records/local HTTP fixture responses
with scripted episode decisions, and report those limits explicitly. No new
numerical score, continuation rule, support-axis adoption, hidden retry, fixed
polling schedule, mandatory scientific sequence or episode level is authorized.

The two earlier human questions about scientific-support combinations and the
pending/wait forecast horizon remain unanswered. This API work chooses neither.
