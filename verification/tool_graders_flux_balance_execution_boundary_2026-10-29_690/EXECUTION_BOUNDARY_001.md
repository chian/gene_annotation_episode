# FBA execution and retained-result implementation boundary

Read-only trace and proposed interfaces, 690/003, 2026-10-29. This is preparation
for parallel coding, not a goal/scope amendment or a claim of integrated FBA
execution. The authoritative supplied goal and complete operating principles
were read; GOAL.md was not read. No production source, prompts, tool information,
progress rows or old verification evidence were edited. No application imports,
tests, native jobs, installs or downloads were run. Only this new packet was
written. The full trace below is based on actual callers and source, not module
descriptions. INSPECTION_001.json identifies inspection hashes and coverage.

The only later goal exclusion applied is blast_formatter/blast_formatter_vdb.
Nothing here removes unfinished work or turns a source descriptor into a working
operation. The original API/local/HPC episode distinctions and caller allocation
remain intact. This next FBA binding is the selected local source-derived
Cobra/GLPK operation; it does not imply an API or HPC FBA deployment.

## 1. Concrete blockers and reusable outputs

1. G4: the released689 reader accepted typed Files only through the eight native
   roles. Legitimate selected prior Files could not bind. Root's adopted011 and
   clarification012 now define the separate supplied-prior-byte parser extension.
   Root is implementing it; this packet does not own the reader. See the prior
   proposal and HOST_AND_LAUNCH_INTERFACE_001.md for the independent host custody.
2. A normal parent selection precedes the resource child's selected start key.
   Current producer v1 requires its original environment to contain the final
   operation-key-dependent lifecycle path. That is an exact integration gap.
   HOST_AND_LAUNCH_INTERFACE_001.md specifies a proposed versioned explicit
   selected/realized environment carrier; no selected job bytes may be rewritten.
3. NMF's five-role capture/result interfaces and fit-success predicates are not
   FBA interfaces. FBA requires eight independent roles, four source states,
   prior Files outside that role set, failed/partial attempt retention, explicit
   calculation parameters, and requested qualified delivery independent of
   optimality. Copying NMF's `original_fit_acquired` or `analysis_complete` would
   introduce the wrong semantics.
4. New files alone cannot integrate a tool. The shared registration table in
   section 4 names every identified consumer in this analogous path. Root must
   own those shared edits and requested-return exports while the two independent
   owners below write disjoint files.

Existing numerical exports are final interfaces to reuse:

```python
parse_fba_capture(payloads: dict, *, expected: dict,
                  prior_sources: list[dict] | None = None) -> dict  # adopted011/012
populate_flux_balance_sheet(*, bundle: dict) -> dict
validate_flux_balance_sheet(sheet: dict) -> dict
calculate_flux_balance_sheet(sheet: dict, *, parameters: dict) -> dict
normalize_fba_solver_status(raw: str | None) -> str
```

The first is the full supplied-byte reader, not host authority. The second
populates the sole shared sheet. The calculator alone owns numerical arithmetic.
No result binding gets another sheet, solver-status mapping or scientific
formula. A saved sheet uses the same calculator with new explicit parameters.

## 2. Actual analogous NMF call trace

All paths in this section are under gene_annotation_episode unless qualified.
Line anchors refer to the inspection snapshot, not a stable cross-version API.

### 2.1 Selection, context and input custody

`execution_service_setup.ExecutionServiceFactory` constructs/persists the
configured resource map, units and progress log selection. It constructs
`ExecutionEpisodes` and the existing monitor binding. Its resource map is data;
construction does not discover a resource or launch software.

`ExecutionEpisodes.__init__:94–301` validates each configured NMF software binding,
requires NMF local resource kind, constructs LocalPracticalOperations, progress
target reader/provider, NativeExpressionNMFResults and ExpressionNMFReturns.
`_request_schema:317–414` includes the exact configured native NMF requested-job
schema in a resource's permitted alternatives. `assignment_schema:416–486`
retains the launch requests, immutable input versions and results selector.

`practical_execution_records.REQUESTED_JOB_SCHEMA:54–82` is a separate shared
closed requested-job union, and `ASSIGNMENT_SCHEMA:98–107`/`validate_assignment:236–397`
validate practical source snapshots and saved receipts as well as new selection.
The NMF branch:274–280 requires a local resource and explicit resource_id. FBA
needs both schema-union and validator registration here; changing only the
ExecutionEpisodes constructor would still fail this earlier boundary. Any adopted
optional environment-selection member also needs explicit closed-schema support.

`prepare_assignment:829–931` validates original launch jobs/versions, admits the
specific NMF input, selects the native result selector when applicable, and
requires each resource child to match its actual launch parent's request.
`_match_request` compares that original requested job, resource, constraints and
allocation; it is not a place to fill in a different job or choose another
approach. `_check_parent_inputs:977–1005` returns to the original parent
commission and `_versions` on child initialization/action validation.

`expression_nmf_operands.validate_expression_nmf_job_inputs:61–81` is the concrete
received-artifact admission path. `_received_context:25–58` authenticates saved
or constructing BindingContext, original parent identity, scope and the entire
frozen receipt-inheritance chain. Admission requires a received artifact_ref,
protected-reference access, exact Store metadata and canonical Store artifact
path. It returns admitted identities without new receipt grants. FBA cannot
copy its one-matrix assumption: model plus explicitly selected prior sources
need the exact binding in HOST_AND_LAUNCH_INTERFACE_001.md.

`execution_input_versions.validate_execution_input_versions` has NMF/ATAC/
fluorescence-specific metadata-only exceptions only for exact admitted selected
artifacts. Ordinary versions retain existing scope and content validation. A
new FBA branch must be similarly narrow and must not make every File or source
artifact an admitted input. Original version-row meanings are unchanged.

### 2.2 Selected start and physical invocation

`ExecutionEpisodes.execute:1695–1763` dispatches resource roles to
`PracticalResourceEpisodes.execute`, after original context/input validation.
That owner validates a selected practical tool, calls `PracticalState.begin`,
returns the saved outcome on replay, otherwise executes it, assesses actual
facts, calls `finish`, and publishes PracticalReceiptInformation. Invalid
selection feedback does not manufacture a completed-action observation.

`LocalPracticalOperations._execute:1230–1647` has explicit native NMF branches
for selected start/status/failure/output paths. `_expression_nmf_plan:640–651`
and `_job_fact:667–784` authenticate the original attempt. `_handle:371–441`
reserves through `prepare_local_expression_nmf` and uses the existing native
handle. It does not identify native execution from a generic argv alone.

`native_expression_nmf_local.prepare_local_expression_nmf:44–87` requires the
pending original practical.job.start while holding the practical-state lock.
It checks allocation, derives `.episode-operations/digest(run,episode)/digest(key)`,
freezes the original run plan and invoke.json, and calls `native.prepare_job`.
`local_expression_nmf_plan:90–132` checks the original assignment/request hashes,
control paths, request bytes/hash, policy and owner/started markers. It neither
launches nor polls. A prepared descriptor is not executed work.

`native_lifecycle.prepare_job:78–150` writes the complete request and publishes
the handle last without submission. `start_prepared:153–198` freezes submitting
state before one systemd-run. `resume_start:217–262` resumes that same handshake
and verifies memory/swap/runtime constraints before release; a submitting or
released handle does not cause resubmission. `_local_job_worker:86–133` verifies
request bytes, enforces file/scratch limits, and invokes the chosen command in
the existing cgroup. Its temporary path realization is explicit in the host/env
report. These process handshakes/enforcement reads are not an episode decision
loop or a monitoring credit source.

`native_expression_nmf_driver.execute_expression_nmf_plan:136–166` validates the
original plan, writes owner/started evidence, checks realized environment and
selected software bytes, verifies original input bytes, then calls
`retain_expression_nmf_artifacts`. That calls the original NMF fit once, saves
original input, parsed/prepared arrays, factors when available and manifest.
The manifest preserves original request hash and actual native identity.

For FBA the existing producer instead writes selected_request, original_model,
loaded/effective model and problem, one original `model.optimize()` invocation,
solution, source CSV when an actual basic point exists, native diagnostics/log
and manifest. The inspected driver calls optimize once at line214. Failure
before solve legitimately records zero calls; after attempted solve it preserves
one and partial diagnostics. This trace does not repeat or re-prove producer688's
native verification. Its final files are still independently owned there.

### 2.3 Observation and handoff

`PracticalReceiptInformation.publish:148–172` stores the actual action receipt
and original assignment snapshot as Store artifacts with a source record.
`read:174–197` checks provider/origin, content-derived source identity, unique
accession, scope, selected runtime action and saved outcome. This is actual
handoff authority; merely finding a path or artifact with expected-looking JSON
is not equivalent.

`execution_progress.ExecutionTargetReader._native:252–472` authenticates that
source/receipt/assignment and reconstructs the exact execution target. The NMF
branch:380–388 checks original attempt key/digest and execution directory.
`read_target:474–495` routes actual native versus API sources. `usable_handoff`
uses original endpoint evidence; `returnable_handoff:1127–1143` additionally
allows specified failed native attempts so partial work can be collected. FBA
needs that explicit failed-attempt registration.

`observe_target:1145–1163` calls the selected resource operations' original
`observe_execution`, with `_native_identity` from the authenticated handoff.
The NMF branch of `LocalPracticalOperations.observe_execution:863–883` reads the
same native handle, terminal/return-code facts and measured elapsed duration.
`expression_nmf_observed_files` supplies actual file availability/sizes and
selected log windows; `read_expression_nmf_output` is confined to declared
outputs/stdout/stderr. No liveness-to-progress or unknown-to-success conversion
is made. FBA needs the same bounded actual-log mechanism with its eight outputs.

`ExecutionProgressProvider.observe:1289–1423` saves a selected operation once,
replays it before touching native status, records exact actual status/log sources
and requested windows, and deduplicates snapshots ignoring read timestamps.
It supplies typed progress data to the existing monitor. It does not choose
monitor cadence, result collection, retry or cancellation. No FBA-specific
monitoring loop or grading episode is needed.

### 2.4 Result selection, writer closure and retained capture

`ExecutionEpisodes._target`, `_selector`, `catalog` and `execute` route an
original NMF target to the actual NMF result owner and restrict status/collect
operations. `NativeExpressionNMFResults.execute:181–203` locks the exact selected
result action through `ExpressionNMFResultReceipts.locked_action`. The receipt
intent binds run/episode/request/assignment/scope/selector/tool/arguments/key;
`read_staged` restores that immutable result before any new observation.

`ExpressionNMFResultReceipts` reuses concrete GenomicOverlapResultReceipts
mechanics: `_selected`, `locked_action`, `require_action`, `file_metadata`,
`_artifact_value`, `capture_control`, `validate_observation`, `observation`.
They enforce selected runtime actions, one action directory/lock, exact immutable
controls, Store File metadata and saved observation identity. Its NMF-specific
`intent`, `_target`, `read_handoff`, `validate_handoff`, `native_snapshot` and
`validate_native` join the actual original commission/start/source record to the
native attempt. Use those primitive mechanics or an explicitly shared narrow
extraction; do not inherit unrelated overlap scientific meaning.

For status, `_original:131–158` records only the actual observation. For collect,
terminal AND quiescent is required. Failure here preserves the selected result
receipt with writer_not_closed; it does not read mutable outputs as final data.
`native_snapshot:212–281` retains original plan, native handle, exact wrapper
request bytes/hash and started marker. It then freezes source-action and writer-
closure controls. Marker absence plus actual native execution_failure can prove
not-started; otherwise absence remains unknown.

`capture_expression_nmf_native_files:18–39` streams each of its five declared
files using `native_file_capture.capture_native_file` into Store custody, and
obtains each canonical retained path through `retained_native_file`. It does not
parse scientific data or grant episode authority. Generic capture uses anchored
no-follow regular-file reads, content hash/size, stable streaming and explicit
missing/conflict outcomes. FBA must capture every observed role independently,
including bytes the manifest calls incompatible. Do not use a manifest's absent
claim to erase an actually observed file.

### 2.5 Bounded finite parsing, sole sheet/calculator and result custody

`build_native_expression_nmf_worker_plan` receives original plan + capture +
selector; saved mode receives only the explicitly received retained sheet +
selector. `prepare_expression_nmf_result_worker:188–273` validates exact caller
policy, freezes plan/intent, snapshots implementation/runtime dependencies,
reserves one worker handle, resumes that handle, waits for terminal/quiescent,
and captures actual worker execution and outputs. Replay validates capture.json
and returns its original evidence. It does not reopen the original scientific
fit. A result worker is finite selected tool work, not a new episode.

The snapshot imports `_source_closure`, `_dependencies`, `_copy_exact` from
native_atac_differential_preparation. `_source_closure` follows application
imports through AST. `_dependencies` inspects actual selected validation package
files; it does not install them. `_copy_exact` verifies immutable copied bytes.
Reuse the pinned677/529 environment and explicit retained dependencies; no
worker setup here authorizes downloads or new native software.

`expression_nmf_result_worker._native:90–144` copies retained five-role inputs to
fixed incoming names and calls `expression_nmf_artifacts.load_expression_nmf_artifacts`.
It checks execution/software/input/parameter associations, populates the shared
NMF sheet, and `execute_expression_nmf_worker:147–196` calls the sole calculator
and deterministic projection. FBA should not copy the matrix loader or stage a
new Cobra model. It can read retained bytes directly and call parse_fba_capture,
populate_flux_balance_sheet, calculate_flux_balance_sheet, and root's projector.
Saved FBA mode must have no producer plan/model/Cobra/GLPK import or native-solve
path; its only operand is the authenticated saved sheet.

Worker outputs are four declared controls: sheet, calculations, projection,
diagnostics plus worker-result.json. Here `capture_declared_native_files` can
be reused: these worker JSON outputs have present/absent declarations. It cannot
be used unchanged as the FBA native four-state manifest adapter. Worker execution
and output-capture failures are operational qualifications, separate from FBA
scientific infeasibility/missing numerical cells.

`NativeExpressionNMFResults._worker:89–129` opens Store in the worker thread,
uses shielded finite preparation, validates returned custody, retains execution,
and reads only the verified projection for host publication. It does not decode
scientific matrices on the host. FBA host similarly consumes verified small
projection/diagnostic/control data while the bounded worker owns decoding and
arithmetic. Cancellation/recovery retains the same worker action/handle.

### 2.6 Publication, authority, requested returns, credit and completion

`ExpressionNMFResultReceipts.publication:359–390` consults the actual original
report schema. It emits only requested projection/saved-sheet/failure sources.
Unrequested native files are not granted to ancestors. `publish`,
`read_completed`, `completed_receipts` bind this publication to the selected
runtime outcome and immutable receipt. `own_fact_groups` and `facts` aggregate
those actual receipts; a parser result alone never becomes parent knowledge.

`ExpressionNMFReturns` reuses EpisodeReturnRecords and AppServiceCustody's
selected commission/attempt checks. `_commission` authenticates immediate child
role, original request/return contract and scope. `_received` uses actual
successful immediate-child report attempts. `_historical` and `_closure_prefix`
preserve the frozen original receipt prefix, so later child facts cannot be
smuggled into a closed return. `record_admission` grants only requested saved File
references. `authenticate_received_saved_sheet:280–315` requires an actual
previous typed returned File plus original receipt inheritance, not Store
existence. Root separately owns the new FBA typed return design; these are the
required custody hooks, not a request to copy NMF field semantics.

`NativeExpressionNMFResults.credit_view:247–257` counts new unique acquired
populations relative to inherited baseline, with caller acquired_record_unit.
Repeated collection and saved recalculation do not become another native
acquisition. This is operational credit, distinct from scientific/monitoring
credit and annotation support. FBA must preserve one original-attempt population
and distinguish inherited model/request bytes from newly acquired attempt facts.
Do not copy NMF's fit-eligibility requirement or award a unit per retained file,
parser, worker, publication, calculation or report.

`completion:259–269` returns the existing practical_completion_v1 proof for the
actual completed selected delivery. `ExecutionEpisodes._proof_for_action`,
`completion_for_action`, `verify_completion` route to that owner; the generic
filesystem acquisition fallback is explicitly bypassed for NMF. FBA must get the
same explicit bypass. `runtime:2992–2998` attaches proof to the actual completed
own action. `_observe:557–625` preserves original contexts and associates it with
that unit. `PracticalYieldEstimator:103–132` verifies the same proof and immediately
returns NumericBand.exact(0), preserving raw history and the final actual gain.
No extra zero turn, model-composed completion, new gate or continuation rule is
necessary. FBA's requested qualified negative/failure delivery must not be blocked
merely because the solver did not report optimal.

## 3. Minimum independent file ownership and exact proposed ports

Freeze common shapes before coding. These are proposed exports, not existing
APIs. A future owner must not edit producer688's four files or the root's reader
and shared schema/calculator files without a separate explicit assignment.

| Owner | Exclusive new files | Concrete inputs and outputs |
| --- | --- | --- |
| A: original selection/local capture | flux_balance_operands.py; flux_balance_execution_contracts.py; native_flux_balance_local.py; native_flux_balance_observations.py; native_flux_balance_capture.py | Original practical assignment/context/versions, authenticated received inputs, existing producer plan and lifecycle; outputs frozen input witness control, original local reservation, actual observation/output windows and retained eight-role capture. |
| B: retained result handling | flux_balance_result_worker.py; native_flux_balance_preparation.py; flux_balance_result_receipts.py; native_flux_balance_results.py | A's immutable capture/plan/witness identity, root's selector/projector/return exports, sole readers/sheet/calculator; outputs bounded worker files, exact result receipt, requested facts, operational acquisition population and practical completion proof. |
| Root: shared integration and requested returns | Existing shared registration files in section 4; new flux_balance_result_contracts.py, flux_balance_result_views.py, flux_balance_return_views.py, flux_balance_returns.py | Freezes requested return meanings and selector/projection/fact schemas; wires actual original-job/context/resource/result/return/credit paths. |
| Existing producer/parser owners | native_flux_balance_contracts/storage/cobra_glpk/driver; flux_balance_readers; shared flux_balance_contracts/sheet/calculations | Remain independent. Environment v2 requires an adopted producer/schema extension, not A silently relaxing current v1. |

### 3.1 A's exact launch/capture ports

```python
# flux_balance_operands.py: detailed shapes in host report
bind_flux_balance_job_inputs(store, context, assignment, *,
    input_versions: list[dict], reference_access) -> dict
validate_flux_balance_input_binding(store, value: dict, *,
    context, assignment, input_versions: list[dict], reference_access) -> dict
freeze_flux_balance_input_binding(store, *, binding: dict) -> dict
validate_flux_balance_input_binding_receipt(store, value: dict, *,
    context, assignment, input_versions: list[dict], reference_access) -> dict

# native_flux_balance_local.py
prepare_local_flux_balance(state, operation_key: str, *, root, policy,
    input_binding_receipt: dict, input_binding_file: dict) -> NativeJobHandle
local_flux_balance_plan(assignment: dict, execution_id: str) -> dict
# Above reads the original reservation, never dispatches/polls. The preparer
# requires the actual pending selected start, validates unchanged assignment,
# records exact input control identity, and calls only existing prepare_job.

# native_flux_balance_observations.py
flux_balance_observed_files(plan: dict, view: dict, *,
    log_window_bytes: int, log_roles) -> tuple[list[dict], list[dict], bool]
read_flux_balance_output(plan: dict, *, path: str, offset: int, limit: int) -> dict
# Match the existing observation/window return shape; use actual stdout/stderr,
# file sizes/availability and selected byte windows. No inferred throughput.

# native_flux_balance_capture.py
capture_flux_balance_native_files(store, *, original_plan: dict,
    source_action_receipt_ref: str, writer_closure_receipt_ref: str,
    input_binding_file: dict, prior_sources: list[dict],
    driver_started: bool | None) -> dict
# Caller authenticates the original start and terminal/quiescent writer first.
# This function captures actual bytes, never grants references or starts work.

# flux_balance_execution_contracts.py
validate_flux_balance_native_capture(value: dict, *, original_plan: dict) -> dict
```

The observation return must be the existing `(outputs, logs, available)` tuple
used by expression_nmf_observed_files, with its exact row meanings. `available`
means the manifest file is observed available, not verified scientific success. A must
publish concrete tests against that caller, not only a module import.

```
RetainedFile = {file: existing File, path: canonical absolute retained path}
FluxBalanceNativeCapture = {
  version: 'flux_balance_native_capture_v1',
  original_plan_sha256: digest(original_plan),
  files: [  # exactly eight rows, original producer order
    {role, relative_path, format, retained: RetainedFile|null}
  ],
  source_action_receipt_ref: artifact ref,
  writer_closure_receipt_ref: artifact ref,
  input_binding_file: File(format='flux_balance_input_binding_receipt_v1'),
  prior_sources: [RetainedFile],  # verified selected priors only, no new role
  driver_started: true|false|null,
  failures: [existing shared FBA Issue]
}
```

The eight rows are original_model, selected_request, effective_model,
effective_problem, solution, flux_csv, native_log, manifest. `relative_path` and
format equal `flux_balance_output_files(original_job)` exactly. prior_sources
remain in first selected-use order and do not expand the role namespace. A file
can serve multiple selected uses through the input witness control without being
read or retained twice. Every retained path is checked against Store custody.

Initial commission admission may validate a detached binding. Freeze its exact
original received prefix/control at selected start before native reservation;
do not change parent assignment bytes to insert a later File reference. The
start's original internal control and subsequent result handoff prove that join.
The preparer receives already authenticated binding evidence from the host, then
checks its bytes/identity; its dict input is not itself an authority credential.

### 3.2 B's worker contracts

```python
build_native_flux_balance_worker_plan(*, directory: str, original_plan: dict,
    capture: dict, selector: dict) -> dict
build_saved_flux_balance_worker_plan(*, directory: str,
    sheet: dict, selector: dict) -> dict
validate_flux_balance_worker_plan(value: dict) -> dict
validate_flux_balance_worker_result(value: dict) -> dict
execute_flux_balance_worker(plan: dict) -> dict
prepare_flux_balance_result_worker(store, *, plan: dict, policy) -> dict
validate_prepared_flux_balance_worker(store, value: dict, *, plan: dict) -> dict
```

Closed plan shapes:

```
Native: {version:'flux_balance_worker_plan_v1', mode:'native_result',
         directory, original_plan, capture:FluxBalanceNativeCapture, selector}
Saved:  {version:'flux_balance_worker_plan_v1', mode:'saved_sheet_recalculation',
         directory, sheet:RetainedFile, selector}
```

Selector.mode must equal plan.mode; saved sheet File must equal the selector's
original saved_sheet_file and format flux_balance_sheet_v1. Native selector's
saved File is null. The root-owned selector must carry the complete explicit
CalculationParameters and requested projection; B must not invent defaults.
The native plan's prior_files and input binding identity come only from A's
capture. The saved plan has no original plan, native paths or prior-source
reacquisition: it is self-contained in the saved sheet's retained evidence.

B reads each exact retained File into bytes in the bounded worker, checks the
actual identity, and builds eight `{file, bytes, state}` entries for the existing
parser. A capture's null row means physically unavailable and becomes absent;
actual retained bytes are never represented as absent. For available native
manifest bytes, a narrow declaration adapter may read only finite duplicate-free
JSON envelope identity/sealed state and ManifestFile rows, validating each role,
path, format and identity against the original plan and captured bytes. Use its
present/truncated/incompatible state only for an agreeing declared actual file.
A declared absent file that actually exists, a wrong identity/format/path, or a
conflicting declaration yields incompatible with actual retained bytes and a
located issue. Missing actual bytes remain absent with their original conflicting
manifest declaration retained for the full parser to diagnose. Invalid/missing
manifest cannot supply successful outcome, call count or exact realization.
Observed complete captured bytes can still reach the independent role parser;
no partial JSON is silently completed. CSV's complete-row recovery stays in the
existing parser. This adapter is custody-state transport, not new scientific
parsing/arithmetic. The full original manifest always also reaches parse_fba_capture.

Native worker sequence is exactly:

```
bytes + expected original FBAAttemptIdentity + selected prior-source bytes
  -> parse_fba_capture
  -> populate_flux_balance_sheet(bundle=...)
  -> calculate_flux_balance_sheet(sheet, parameters=selector.calculation_parameters)
  -> root-owned project_flux_balance_result(sheet, calculations, selector=...)
```

Saved sequence begins at validate_flux_balance_sheet and uses the same last two
calls. It must not import native_flux_balance_driver/cobra_glpk, load a model,
call optimize, or acquire data. The source closure for the result worker must
make this absence verifiable.

Proposed worker-result closed control:

```
{version:'flux_balance_worker_result_v1', mode, plan_sha256, selector,
 outputs:[{role, declaration:{relative_path,format,state,sha256,size_bytes}}],
 failures:[Issue],
 native_association:'verified'|'unavailable'|'conflict'|'not_applicable',
 new_attempt_evidence_roles:[role],
 requested_projection_valid: bool}
```

Outputs are exactly sheet.json/flux_balance_sheet_v1,
calculations.json/flux_balance_calculations_v1,
projection.json/root-frozen projection format, diagnostics.json/
flux_balance_result_diagnostics_v1. Worker output state is present or absent;
absent pins are null. Native scientific source state remains four-valued inside
the sheet. `native_association` describes byte/attempt association checked by the
reader; it is not episode authority. Saved mode uses not_applicable and an empty
new_attempt_evidence_roles. `requested_projection_valid` asserts exact root
projection-schema validation, not scientific acceptance or practical completion.

`new_attempt_evidence_roles` is an ordered subset of effective_model,
effective_problem, solution, native_log, manifest actually acquired from the
original entered driver and usable as attempt evidence. original_model and
selected_request alone are inherited inputs, not new acquisition. The host must
validate this claim against its original binding/driver/capture and the actual
retained parser output before counting one acquisition population. It may not
count per role. Root must freeze whether a particular qualified failure delivery
satisfies the requested endpoint; neither B nor this flag can decide it from
solver optimality or from NMF's fit_call_count predicate.

Prepared capture/execution controls can retain NMF's exact mechanical shape:
plan_file, execution_receipt_file, worker_result_file, result, outputs, failures;
version these as FBA records. Preserve actual command/env/policy, handle and
request_raw/hash, terminal/quiescent, returncode/resource failure and captured
stdout/stderr. Validate a saved capture before any native lifecycle call.

### 3.3 B's host class and root's required return ports

`NativeFluxBalanceResults(owner)` must provide the same actual caller methods:
`applies(context)`, `retained_target(context,assignment,scope)`, async
`execute(context,target,tool_name,arguments,operation_key)`,
`own_fact_groups(context,*,verify_artifacts)`, `facts(context)`,
`resolve_own(context,reference,namespace)`, `owns_reference(reference)`,
`credit_view(context,receiver_selection)`, `completion(context)`.

`FluxBalanceResultReceipts(owner)` owns original intent/handoff/native snapshot,
A's input-witness join, worker plan/capture validation, immutable publication,
completed receipt reads, unique acquisition and baseline populations. Its
selected-action lock/control helpers are reusable from the existing receipt
mechanisms. Status never opens a worker; collect is the one finite selected
operation. Same-key recovery returns the same staged/completed receipt.

The exact ports needed from root's independent requested-return design are:

```python
FBA_RESULT_SELECTOR_SCHEMA: dict
validate_flux_balance_result_selector(value: dict, *, job: dict | None = None) -> dict
project_flux_balance_result(sheet: dict, calculations: dict, *, selector: dict) -> dict
validate_flux_balance_projection(value: dict) -> dict
flux_balance_fact_sources() -> dict
requested_flux_balance_sources(schema: dict) -> tuple[str, ...]
validate_flux_balance_fact_values(source: str, values: list) -> list
# A frozen deterministic requested-delivery function, proposed signature:
evaluate_flux_balance_delivery(*, requested_sources, selector, projection,
    qualified_files, issues, original_association: bool) -> dict
# Closed return: {complete: bool, validation_keys: list[str]}.
```

Root must freeze the projection format name, fact-source names, selected cell
schema, ordered selection semantics, typed failure meanings and delivery predicate
before B codes them. These are specific missing exports, not a whole-tool blocker:
A can implement receipt/launch/capture against its frozen ports independently;
B can implement retained worker custody against a frozen selector/projector API.
This report does not settle the user-facing requested fields or alter prompts.

The host result receipt should retain NMF's useful closed mechanical fields,
versioned for FBA: intent, handoff_proof, original_origins, observation, native,
source_action_file, writer_closure_file, input_binding_file, capture, worker_plan,
worker_capture, worker_execution, qualified_files, projection, host_failures,
facts, acquired_population, delivery_complete. The input-binding File is also
joined to the actual original launch start, not merely equal to a worker's claim.
The completion proof covers this exact immutable receipt and selected key.

## 4. Shared consumers requiring explicit FBA registration

Root should own these shared edits together; neither A nor B should independently
patch them while the other writes a private interface.

| Consumer | Actual NMF hook / necessary FBA equivalent |
| --- | --- |
| execution_episodes.py constructor/configuration/as_record | Local FBA software binding validation; instantiate result/return owners; persist exact resource configuration. Historical return validation must not silently vanish when a current deployment is removed; examine the unconditional fluorescence/protein pattern rather than copy NMF's conditional construction blindly. |
| execution_episodes.py `_request_schema`, `assignment_schema`, `_validate_request`, `_launch` | Exact configured FBA job alternatives and adopted execution-selection carrier; no arbitrary native argv fallback. |
| execution_episodes.py `_versions`, `_expression_nmf_inputs` analogue, `prepare_assignment`, `initialize`, `_check_parent_inputs` | Actual selected model/prior witness admission, original immutable input versions/commission and unchanged caller constraints. |
| execution_input_versions.py | Narrow admitted-FBA-input metadata path; FBA protected-reference resolver; preserve source content_sha256 meaning. |
| practical_execution_records.py `REQUESTED_JOB_SCHEMA`, `ASSIGNMENT_SCHEMA`, `validate_assignment` | Add shared FBA requested-job alternative and local/resource-id validator; preserve saved snapshot/receipt validation and original fields. An adopted new execution-selection carrier must be explicitly allowed here without broadening arbitrary properties. |
| practical_execution_operations.py `validate_assignment`, `_handle`, plan helper, `_job_fact`, `_execute`, `observe_execution`, `read_output` | Explicit local FBA recognition/reservation/status/output/failure path, original attempt identity and allocator; never generic retry/new solve merely because an old wait ended. |
| execution_progress.py `describe_execution_target`, `ExecutionTargetReader._native`, `describe_target`, `_native_identity`, `returnable_handoff` | FBA original source/attempt identity; exact local plan; failed original attempt can return partial work; actual output/log extractor. `_native_identity` needs resource_id/requested_job hash if FBA helper requires them, as the existing masking/utility/fluorescence cases do. |
| execution_episodes.py `_target`, `_selector`, `decision_context`, `catalog`, `execute` | FBA native/saved selector, exact status/collect dispatcher, actual result owner. No scientific calculations in decision context. |
| execution_episodes.py `received_report_sources`, `received_report_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts` | FBA own versus received typed facts and original return witnesses. |
| execution_episodes.py `received_form_references`, `initial_references`, reference-access helper, `resolve`, `validate_report` | Admit only requested returned references and exact selected input refs; apply saved-sheet custody and protected-denial hooks before generic fallback. |
| execution_episodes.py `project_credit`, `_native_results_complete`, `_proof_for_action`, `completion_for_action`, `verify_completion` | One unique original acquisition, no duplicate saved credit, exact FBA requested-delivery proof and bypass of generic filesystem-success completion. |
| communication.py schema source check:125–221 | Register the exact complete top-level FBA fact schemas; caller-narrowed or nested fake source schema must fail. |
| communication.py native validation:593–650 and semantic visitor:686–745 | Recognize FBA registered schema documents, validate field values with root's FBA validator and preserve local $defs/reference semantics. |
| execution_episodes.py `resource_tool_contracts`:1187–1189 analogue; new execution information module | Later actual tool instructions and registered extractor names/typed fields. Needed for published capability, but prompt/tool-content edits are outside690. IDs/hashes stay internal. |
| execution_service_setup.py / practical_service_setup.py | Existing resource persistence can carry new validated configuration; audit validation/reconstruction with FBA. A new service factory or resource chooser is unnecessary. |
| runtime.py / practical_yield.py | Existing proof attachment/one-own-action observation/exact-zero mechanism is reusable. Registration must reach it; no independent FBA controller or synthetic turn is needed. |
| EpisodeReceipts / EpisodeReturnRecords / Store / native_lifecycle / native_file_capture | Reuse existing custody/control primitives. Their existence alone supplies neither FBA operation registration nor received source authority. No blanket namespace/grant change is justified. |

A final explicit-source `rg -l expression_nmf gene_annotation_episode method_loop`
pass found the shared practical_execution_records registration above in addition
to the other listed consumers. All NMF references outside its own scientific
modules fall within this table; generic downstream custody/runtime calls were
followed separately. No recursive verification-content search was used.

## 5. Failure, partial, replay and verification cases

These are required future checks, not tests run by690. Reuse the released689's73
passing-case evidence, root011/012 parser checks and the exact retained producer
artifacts from677/688; do not rerun a native solve for these boundary questions.
Current concurrently edited producer source hashes are inspection snapshots,
never relabelled as bytes used by an earlier frozen run.

| Case | Required behavior to verify |
| --- | --- |
| Complete original selection | Parent job/resource/allocation/versions/return contract remain exact through child context, start reservation, writer evidence, worker plan, result receipt and returned facts. |
| Input authority | Received direct artifact and selected source-field witness; reject forged/unreceived/out-of-scope/protected/later-prefix metadata, wrong original digest, path alias and source-primary/request_ref hash confusion. No grants or substitutions. |
| Future operation key | Existing v1 mismatch remains explicit; adopted new selection policy produces a separate original/realized binding. No child-key preassignment or original selected job mutation. |
| Prepared or unconfirmed start | No execution/scientific completion from descriptors; same original handle recovers; ambiguous submission does not launch again. |
| Writer still active | Status records actual observations; collect returns writer_not_closed and does not freeze mutable output as final. No new monitor loop. |
| Pre-solve failure / failed original attempt | Keep actual marker, source audit/request application/log/manifest and valid partial roles; zero solve calls remains zero. Failed handoff remains returnable where authenticated. |
| Infeasible/unbounded/limit/unknown solver status | Use existing normalization and calculator missing states. Do not invent a flux point, mark it optimal, or require optimality for a requested qualified result. |
| Missing/truncated/incompatible/native-role conflict | Preserve every actual captured file separately; full parser owns scientific qualification. Missing manifest cannot invent successful outcomes or calls. Complete CSV rows can survive independent JSON failure. |
| Missing/conflicting prior source | Contract011/012 issues retain independent native evidence; native role authority cannot be overwritten by extras. The host cannot silently replace provenance with paths. |
| Wrong original commission/start/selector/environment | Frozen controls and receipt joins reject publication as original selected delivery; independent captured bytes remain retained as qualified partial evidence. |
| Result worker crash/resource limit | Preserve actual worker execution and any verified files; never start another scientific solve, infer absent values as zero, or mark a merely prepared worker complete. |
| Same-key worker/result replay | Restore saved controls/outcome, no new status read/worker/native solve, no changed receipt, no extra credit or observation. |
| Saved sheet recalculation | Only exact actually received sheet plus explicit parameters; no original output paths/Cobra/model load/acquisition. Preserve original result provenance and initial observation history. |
| Requested projection/return | Only original requested typed fields cross; no full-sheet grant unless requested; source metadata/hashes remain transport. Forged schema, wrong relationship or unrelated sibling return fails. |
| Unique acquisition/closed history | Original attempt contributes at most one new operational population; inherited inputs, repeated collection and recalculation do not duplicate it. Scientific/monitoring/duration values remain distinct. |
| Practical endpoint | Actual original requested delivery proof attaches to the final real action; future expectation becomes exact zero immediately through PracticalYieldEstimator, preserving final gain and prior contexts. No zero-credit extra turn. |

No production readiness or integrated capability is asserted by this packet.
The two independent coding slices, root's typed-return/registration work, adopted
environment correction and their bounded verification remain concrete work.
