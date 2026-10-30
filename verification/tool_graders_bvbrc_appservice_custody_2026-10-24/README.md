# AppService input custody component

This is the narrowly owned custody implementation, not a claim that the complete
AppService service/host/publication path or any scientific grader is finished.
Only `gene_annotation_episode/bvbrc_appservice_custody.py`, its new test file and
this verification directory belong to this workload. Shared hosts, executor,
schemas, accounting, prompts, scientific scoring and permanent directions were
not changed here.

## Implemented interface

`AppServiceCustody(store, run_id, *, read_original_handoff=None)` subclasses the
existing `EpisodeReturnRecords`. Its five contracted methods are `possession`,
`initial_references`, `content`, `evidence` and `original_job_owner`. It reuses the
shared context and original immediate-child return machinery. It writes no
database rows, artifacts, observations, credit, or return values.

Possession requires an actual completed/partial own action, an original
successful typed child return with matching frozen facts, or an explicitly named
original assignment input possessed by its parent before that commission. A
source/hash in the Store, an inherited ledger prefix or an ephemeral
`received_record_refs` value cannot supply that proof. A strict integer `before`
index bounds completed actions and return selections. Existing frozen parent
receipt cutoffs additionally prevent a child commissioned earlier but returning
later from retroactively supplying a newer child's input. The cutoff constrains
time; it is never a substitute for action or typed-return proof.

The current `Workflow.selected`/`build` ordering initializes a child before
saving that child and its action/commission. The already saved parent
`runtime_model_calls.response.selection` is the authority during that interval.
The helper uses the runtime's original-schema response decoder and validates
the decoded selection against that saved schema. It compares the exact path and
index, role, assignment, normalized scope, goal, requested contract and initial
form. Any existing action or durable commission must also agree. Missing,
changed, schema-rejected or unrelated model selections cannot authorize an
unsaved child. No earlier action or synthetic observation was added to change
the runtime ordering.

Content reads validate the declared source-to-artifact field, content-addressed
source/artifact identities, actual retained bytes, byte count and SHA-256.
Matching bytes in a different field are insufficient. JSON extraction rejects
duplicate object members, nonfinite constants and overflowing floating values,
then follows only the exact RFC 6901 pointer. Source/reference delivery permits
this declared content use; it does not materialize or forward an internal sheet
or additional fact family.

Original ownership is the saved scientific-to-launch commission plus the exact
launch-assignment digest. Resource children of one launch keep that owner;
separate launch commissions keep separate owners. Results use their actually
possessed original handoff. The host callback must return its exact `reference`,
`original_job_owner` and original `launch_api` `origin_context` (a BindingContext
or exact `as_record()` value). Custody verifies the original completed selected
`api.bvbrc_appservice.submit` action and launch ancestry. Missing callback remains
`bvbrc_appservice_custody_original_handoff_reader_unbound`; no native task ID is
treated as possession or used to infer ownership.

Packaged definitions are resource configuration, not fabricated parent-delivered
sources. The tests use the actual packaged Homology envelope and C3 preparation
and verify that no source is added to initial custody. Retention of a selected
local extraction before action completion belongs to the consuming input binder,
which must prove that selected action and freeze the exact operands. Later
support/handoff publication is root-owned work.

Errors subclass ValueError and expose stable `.code` and `.diagnostics` fields
with prefix `bvbrc_appservice_custody_`, without embedding operand values.

## Verification boundaries

`PYTEST_FINAL.txt` is the final focused suite result. `RESULTS.json` records its
numerical outcome and the source hashes. Earlier logs preserve development
verification: the first assertions against C3's result and the caller-source
baseline were test mistakes, corrected without relaxing custody; an interrupted
run was restarted after correcting the baseline assertion.

Most cases deliberately construct saved records through actual Store, Journal,
EpisodeGoal, TypedReportContract, EpisodeReceipts and CommissionCoordinator
interfaces. They test real serialization/identity/receipt shapes with synthetic
operation histories, not executed AppService work. One case runs the actual
shared Workflow, existing BV-BRC Data API/result executor, completion and typed
return path with scripted choices and a clearly synthetic zero-count response.
The new custody helper accepts its actual own-action and reference-only return
records. This checks shared record compatibility; it is not full AppService
episode integration or live-service verification.

Concrete custody example: the retained synthetic bytes `{"native": [0, 1.25]}`
have length **21 bytes** and SHA-256
`5ae0e13915ed2a07800396ef95ca0d34d5e3962b9f54cc06f34c4a521cb5686c`.
The exact pointer `/native/1` extracts the floating value **1.25**. A forged
byte count, a different artifact field, missing/corrupt bytes, duplicate JSON,
an invalid array index or an unpossessed source is rejected. The owner tests
check **two resource children with one original owner** and **two deliberate
launch commissions with distinct original owners**. These are operational
validation examples, not scientific measurements or annotation scores.

No live request, credential use, HPC activity, local database BLAST, literature,
model execution, scientific calculation, new observation or credit change was
performed. Complete AppService invocation/publication and assembled episode
verification remain with the consuming root-owned integration. Native task and
output evidence must still come from that actual service path.

`INSPECTION.json` names the inspected complete consumer methods and documents.
`SOURCE_SHA256.json` records the immutable authority/contract, implementation,
shared validator, runtime schema and actual packaged Homology source hashes.
The final authority reset rereads the original objective and all sixteen design
principles verbatim from the attachment, then the exact custody contract.
