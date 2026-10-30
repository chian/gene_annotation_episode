# Chromatin result host and completed-action proof

Additive implementation contract, 2026-10-27. The original user attachment
remains authoritative. This divides the remaining C4 work; it changes neither
the scientific records nor the goal. Read that attachment and repeat its full
objective/principles reset as required. Do not read GOAL.md.

## Ownership and exact consumers

Root owns `native_chromatin_interaction_results.py` and shared registration.
A fresh receipt owner owns `chromatin_interaction_result_receipts.py`, its
dedicated tests and verification packet. A separate fresh owner will implement
447's operands/returns contracts. Existing C1/C2/C3 and446 capture retain their
files. No owner edits scoring, literature, messages, other tools or accounting.

The host is `NativeChromatinInteractionResults(owner)`, exposed as
`owner.native_chromatin_interaction_results`. It implements 447 section5's
exact six public ports, plus `execute`, `facts`, `credit_view` and `completion`
with the existing results-host calling convention. The return authority is
`owner.native_chromatin_interaction_returns` implementing447's exact ports.
The existing results role still owns status/collect decisions. No new episode,
operation sequence, private model loop or authority database is introduced.

## Receipt helper ports used by root

`ChromatinInteractionResultReceipts(owner)` owns the original selected action's
immutable controls and their reconciliation with existing runtime records.
Its public/integration ports are:

```python
action_directory(episode_id, operation_key) -> Path
_context(context, *, allow_unsaved=False) -> dict  # exact original assignment
_target(context, assignment, target) -> dict
locked_action(context, *, target, tool_name, arguments, operation_key)
    # async context manager -> Action(intent: dict, directory: Path)
require_action(action) -> None
read_staged(action) -> dict | None
read_handoff(action) -> dict
observation(action) -> dict
native_snapshot(action, observation) -> dict
capture_control(action, name, value, format_name) -> NativeFileIdentity
origins(context, assignment) -> list[dict]  # exact completed receipts
sheet_evidence(action, receipt) -> dict | None
acquisition_population(receipt) -> str | None
publication(receipt, *, originals=None) -> tuple[dict, bool]
publish(action, receipt) -> dict
read_completed(*, episode_id, operation_key, scope) -> dict
completed_receipts(context) -> list[dict]
owns_reference(reference) -> bool
baseline_populations(context, references) -> set[str]
```

Module helpers used by root: `VERSION`, `require(condition, code=...)`,
`same(left,right)`, strict `decode(raw, *, newline=False, canonical_bytes=True)`,
`read_control(path)`, `immutable(path,value)`, `unique(rows)`, `empty_facts()`,
`empty_files()`, `qualified_files(capture,execution)`, `closure_value(receipt)`
and `outcome(receipt)`. These must not import overlap scientific contracts.
Reuse existing general Store/native capture/runtime primitives. Private control
I/O is not scientific parsing or another observation.

Receipt has exactly:
`version,intent,handoff_proof,original_origins,observation,native,
source_action_file,writer_closure_file,capture,worker_plan,worker_capture,
worker_execution,qualified_files,sheet_evidence,projection,host_failures,facts,
acquired_population,delivery_complete`.
VERSION is `native_chromatin_interaction_acquired_result_v1`.
Intent fields are `version,run_id,episode_id,path,scope,assignment,
original_request_sha256,operation_key,tool_name,arguments,target`; version is
`chromatin_interaction_result_intent_v1`. `arguments` is exactly `{}` and tool
is `execution.results.status` or `execution.results.collect`.
Control directory is the existing execution-results root, then
`digest([run_id,episode_id])/native-chromatin-interaction-actions/digest(key)`.

Handoff proof fields are `source_record,body,assignment_snapshot,start_receipt`.
Native snapshot fields are `original_plan,plan_file,handle,handle_file,request,
request_raw,request_file,started_marker,started_marker_file,driver_started`.
They qualify the actual C3 original reservation, original selected start action,
its recorded practical receipt and exact requested resource. No authority is
granted by a private path or file existing. Missing started marker means unknown
unless the original terminal native receipt affirmatively proves startup failed.

## Worker and sheet publication boundary

Do not copy overlap's WorkerExecution shape: C3's actual execution record has
`version,plan_file,intent,terminal,quiescent,policy,returncode,metadata,failure,
handle_file,request_file,stdout_file,stderr_file`; its version is
`chromatin_worker_execution_v1`. Its intent contains the exact plan, command,
environment, immutable source/interpreter/dependency pins and fixed policy.
Qualify those recorded relationships without rereading software or science on
historical replay. Successful finite worker return requires returncode0,
no failure, terminal/quiescent true and the actual fixed local policy/cgroup
evidence. C3 `WorkerCapture`, `WorkerResult` and plan validators supply shapes.
Current acquisition additionally calls `validate_prepared_chromatin_worker`.

`QualifiedFiles` contains `sheet,components,projection,diagnostics` (file or null)
and `tables`, an ordered list of `{table_key,file}` rows (file or null).
Only exact verified declared captures qualify. Table rows retain every declared
key, even when absent or unavailable; never deduplicate them by byte identity.
No failure for one table may suppress all other table roles.

`sheet_evidence` reads the currently retained sheet once at first publication,
validates its complete C1 record and the actual captured components/projection
associations, then freezes a compact witness in `sheet-evidence.json`:
`version,sheet_file,request_sha256,populations,data_tables`.
Version is `chromatin_interaction_sheet_evidence_v1`. `populations` contains
exact `PopulationExtraction` projections of the sheet populations (the existing
fields, without `element_anchor_rows` or `pair_rows`). `data_tables` retains
every exact TableDescriptor, including absent roles, and original order.
The full sheet and components remain retained separately; they are not copied
into receipts or model context. On recovery/historical reads, compare the frozen
witness to the exact completed action and controls rather than opening lost
scientific files or recalculating anything. Initial witness creation cannot
accept caller-authored descriptors. Root calls this port for both native and
saved work whenever a sheet qualifies.

At that first boundary require exact original request digest/population order,
all five role descriptors per population, table-key/role/file joins to the
worker's complete output declarations, source sheet digest for components and
projection, exact selected parameters, population selection, fields and page/key
selection. The projection preserves requested order; do not invent a sorting
restriction absent from the accepted ResultSelector. Calculations remain C2.

Public `SavedSheetBundle` is `{sheet,tables}` with tables exactly the nonnull
descriptor files, in descriptor order. Publish it only when each required file
qualified against the corresponding table-key output. Absent native roles are
not invented files; a lost attachment to an existing saved sheet is not an
authorized smaller bundle. Complete/partial numerical projections are separate
from availability of this whole saved bundle. A source digest inside a numerical
projection alone never grants access to sheet or table artifacts.

## Original and saved result handling

Root authenticates original handoff and records one current resource observation
for the selected action. Collection opens producer paths only after the actual
original writer is terminal and quiescent. It persists446's exact NativeCapture,
then uses C3 `build_native_chromatin_worker_plan` and the ordinary bounded worker.
Status records its observation but produces no scientific publication. Replay
uses original controls and does not poll, capture, submit or calculate again.

Saved selection authenticates the complete received bundle through447's
`authenticate_received_saved_bundle`, obtaining every exact completed-action
origin. Read those exact receipts and require their matching bundle and target;
no arbitrary first artifact or unrelated source can supply it. All relevant
origins must agree on original handoff/run/resource/scope. The saved worker sees
only RetainedSheetBundle and selector; native input/software paths are not used.
Check each retained input at new use. A current NativeFileCaptureError becomes
a located input_unavailable/artifact_digest_mismatch failure, no implicit retry.

`facts` contains exactly the three current chromatin FACT_SOURCES. Publication
selects only sources requested by the original parent form. Failures are located
to the selected populations/rows or shared acquisition/execution requirement;
private failures about unrelated populations are retained but not displayed.
Do not use nonexistent expected_value/observed_value fields in C1 Failure.

## Acquisition, practical completion and continuation

Use the existing caller-owned `acquired_record_unit`; do not add numerical units,
scientific-confidence formulas or per-file/table/row bonuses. One original
native job's newly acquired numerical population counts once under that existing
unit. Its identity is `digest(original_plan.identity)`, independent of projection
or recalculation parameters. No count for status, logs, malformed-only output,
private receipt creation, recalculation or repeated delivery.

An acquired population requires a qualified original sheet plus actual retained
bins/contact data authenticated by a complete bundle or independent population
seal and the original closed writer. Preserve partial acquired native rows when
later populations fail. A valid complete sparse population containing no stored
contacts still counts as acquired data only with explicit validated absence/
complete-read proof; missing contacts never masquerade as a zero matrix. Retain
the exact evidence used for this predicate in the sheet witness and native
capture/control proof. Numerical signs and desirability cannot affect it.

Practical completion requires the requested delivery and successful complete
original acquisition. An unavailable scientific value caused by valid but
incompatible references, zero denominator, absent normalization or insufficient
windows is a qualified answer, not a scientific acceptance gate. Missing native
files/unfinished writer/partial original acquisition do not establish completion.
Saved recalculation can complete from an authenticated complete original witness
even if an intervening projection failed, but never repairs a partial original
acquisition by reinterpreting it. All historical origins remain inspectable.
Require a projection to exist and requested saved bundles to qualify; completion
does not require positive values, all measurements being defined or crossing a
scientific threshold.

Baseline subtraction uses the existing frozen inheritance/report prefixes and
the exact originally acquired native population, including explicit received
saved-bundle associations. Historical reads and credit remain metadata-only
after later byte loss. Original completed action outcomes/observations and
forecasts never change. The ordinary practical completion proof drives exact
zero future expectation; add no synthetic turn or stopping rule.

## Verification responsibilities

Receipt owner: actual Store/runtime action+form+receipt records, explicit
completed-vs-staged proof, wrong parent/run/scope/handoff rejection, malformed
controls, exact multiple-table joins and duplicates, lost-byte historical
survival, original vs saved acquisition/endpoint rules and frozen baseline.
Strict doubles for external host/returns ports must be labeled and cannot be
claimed as actual complete Workflow. Root separately joins production components
and verifies full Workflow, partial survival, selected returns and replay.

All executable tests use existing local_jobs/native_lifecycle,20GiB RAM,4GiB
scratch,zero swap,no wall limit, immutable source/binary pins and original live
handles. Retain failed attempts. Do not increase the308-tool tally on component
evidence. Print concrete numerical results and limits in the conversation.
