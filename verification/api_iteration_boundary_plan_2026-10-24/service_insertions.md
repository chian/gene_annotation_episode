# Concrete service insertions for the proposed API template

These are source-derived meanings to populate the common template. They are
not new service episodes or extra model prompts. Include the selected service's
rows only, along with all its selected substantive instruction bodies. This
record neither changes a callable nor claims live verification.

## EBI HMMER

Assignment: one supplied protein; selected `phmmer` or `hmmscan`; exact database,
parameters and result-page size. `phmmer` searches a protein query against protein
sequences; `hmmscan` compares the protein against profile models. These roles do
not authorize the unbound HMMER algorithms documented elsewhere.

Handoff: one received successful `api.hmmer.check_handoff` outcome validates the
original addressable search as submitted, running or completed. Submission alone
is insufficient in this binding. Separate results acquisition requests a native
page; launch never claims those results have been acquired.

| Available action | What it obtains or establishes | Inputs | Conditions and limits |
| --- | --- | --- | --- |
| api.hmmer.databases | One current served-database response. | Empty arguments; this assignment's service. | Does not choose a database or establish acceptance of this search. |
| api.hmmer.prepare | Exact scoped query, submitted FASTA and fixed request preparation. | Empty arguments; original supplied protein/settings. | No HTTP request; repeat uses original preparation. |
| api.hmmer.submit | One original search submission and actual response. | Empty arguments; original preparation/settings. | Includes preparation if needed. Existing or uncertain submission is not replaced. This legacy binding exposes no selected replacement-submit recovery even after a prior not-sent failure. |
| api.hmmer.status | One status observation for the original submitted search. | Empty arguments; original job must already be known. | Observation failure is distinct from native job failure; status alone does not establish this binding's validated handoff. |
| api.hmmer.check_handoff | One status observation plus original-job handoff validation. | Empty arguments; original job must already be known. | Submitted/running/completed can qualify; failed/unknown cannot. Successful validation completes launch while the physical job may continue. |

No wait or child branch is currently available for this legacy launch role.
HMMER status mapping comes from `_native_status`: PENDING/RECEIVED → submitted,
STARTED/RETRY → running, SUCCESS → completed, FAILURE/REVOKED → failed; unknown
native values stay unknown. Preserve the received native spelling and date.

## UniProt

Assignment: exact record accession, or exact search query with optional size and
assigned cursor. Record and search are distinct requests. Search size is 1–500;
omitted size becomes 10 in the actual prepared operation, while the original
assignment remains unchanged.

Handoff: a validated retained immediate response for the requested record/page.
There is no remote job. Search coverage retains returned count, reported total,
release and continuation availability. The actual opaque cursor stays host-side
at this boundary; a separate result assignment can request the returned cursor.
An empty results selector publishes retained original response without HTTP.

| Available action | What it obtains or establishes | Inputs | Conditions and limits |
| --- | --- | --- | --- |
| api.uniprot.record | One record response for the assigned accession. | Empty arguments; original accession. | Only present for a record assignment. Source protein identity is distinct from the annotation target. |
| api.uniprot.search | One page of the assigned search. | Empty arguments; original query/size/cursor. | Only present for a search assignment. Actual Link continuation is not a manufactured page number or full-population claim. |

The common role permits explicit wait for generic API assignments. A service
instruction does not require waiting when an immediate query is already useful.
No collect operation belongs to this launch role.

## NCBI BLAST

Assignment: supplied sequence and explicit `blastn`, `blastp`, `blastx`, `tblastn`
or `tblastx`; database; optional hit-list size. Query units must match the selected
program: protein for blastp/tblastn, nucleotide for blastn/blastx/tblastx. Omitted
hit-list size becomes 50 in the prepared request. It is a requested maximum hit
list, not a completeness guarantee for the database population.

Handoff: a validated original submission response with an actual RID establishes
launch's usable monitoring/results handoff. RTOE is a provider-reported estimate;
launch does not need to wait for READY. The opaque RID stays in the host binding.
Status and JSON2 result acquisition remain different operations downstream.

| Available action | What it obtains or establishes | Inputs | Conditions and limits |
| --- | --- | --- | --- |
| api.blast.prepare | Resolve and validate original sequence/settings locally. | Empty arguments; original sequence/program/database/hit-list. | No HTTP. Preparation is optional because submit also resolves inputs. |
| api.blast.submit | One native original submission response. | Empty arguments; original request. | Requires configured contact/rate-state prerequisites. Retain original uncertain outcome; do not replace a possibly submitted job. A later not-sent attempt is only supported where the actual selected-operation contract permits it. |
| api.blast.status | Catalog-declared single observation of an original RID. | Empty arguments; an original RID binding is required. | Current generic launch dispatch supplies no native handle to this operation, and successful submit closes launch. Show this qualification; do not promise it can run before a handle exists or invent a continuing post-handoff launch turn. |

The existing shared explicit wait can be available. `api.blast.fetch` is not a
launch operation. Stated service limits are at least 10 seconds between contacts
and 60 seconds between polls of one RID; received dynamic delay feedback remains
dated/qualified. Contact configured is a boolean, never the email address.

## BV-BRC Data API, current inspected v1

Assignment: selected collection, typed AND-combined field/operator/value
predicates, selected fields, ordered sort specification, limit and offset.
Currently the concrete request schema permits genome, genome_feature and
protein_family_ref; this is implementation coverage, not the common episode's
permanent scope. Operators eq/ne/gt/lt use scalars; in uses a nonempty scalar
array. Preserve literals exactly. Omissions remain recorded; effective default
limit is 25 and offset is 0. A configured request timeout is a transport limit,
not a scientific execution-duration estimate or episode stopping budget.

Handoff: a validated retained native row-array response for the original assigned
page. The source's Content-Range is retained verbatim, reported total can be
unknown, and returned row count determines the next offset. A complete response
body does not establish acquisition of all matching records.

| Available action | What it obtains or establishes | Inputs | Conditions and limits |
| --- | --- | --- | --- |
| api.bvbrc.query | One immediate original assigned public-data page. | Empty arguments; exact collection/filters/fields/sort/page. | No remote task, queue or status-poll operation. No query rewriting or added filters. A malformed/incomplete body is distinct from zero returned rows. |

The shared explicit wait can be available, but no service polling requirement
is implied. `api.bvbrc.result` belongs to results acquisition. A future Data API
v2 owner supplies its own exact request-field meanings under the same common
projection. This record owns no v2 schema. BV-BRC AppService and Workspace
operations are not available merely because the Data API works.

## Existing internal lookup rows

These use the current `response_type=request_context` envelope. Do not change
the typed response contract or silently treat lookup responses as actual actions.

| Lookup | Required fields | Meaning and limit |
| --- | --- | --- |
| own_attempts | view, category (string or null), decision_indices (integer array or null), offset ≥ 0, limit ≥ 1 | Page this episode's prior attempts. Category uses the exact operation category, such as tool/api.hmmer.status. Returned selection/status/gain are actual; outcome fingerprints are not response detail. |
| own_attempt_detail | view, decision_index ≥ 0, pointer, offset ≥ 0, limit ≥ 1 | Read exact selected-input detail of a prior own attempt. Pointer is the existing JSON pointer into selected inputs, not an arbitrary database or artifact path. Slice unit and continuation remain explicit. |
| composition_information | view, operation, arguments | Invoke only the actually declared information operation inside this unfinished decision. Examples are launch.instructions.search/entry/read/select and knowledge.search/entry/read. Actual input fields come from that operation's existing schema. No service invocation is permitted here. |
| child_options | view, role = null for this launch_api role | Current generic lookup can report an empty child list. It does not create a child capability. Omit this irrelevant row from routine choices; retain original response-schema behavior. |

Instruction reads use a readable entry/section key and zero-based line offset
plus line count. These are existing necessary lookup operands, distinct from
host library digests and receipt IDs. Search text is exact metadata matching,
not a model-written database query. `launch.instructions.select` pins the exact
chosen instruction sections; it does not amend this episode's original native
request or automatically replace the child's frozen selected tool information.

The wait action's declared condition keeps its existing typed fields. A timer
can be expressed through `reconsider_at` with no event handles. Event waits are
only presented when an actually received permitted event target exists; no
opaque API RID is repurposed into a wait handle. This does not add a new clock
query or a hidden delay to rendering.
