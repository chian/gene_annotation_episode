# Bounded result-worker preparation and capture

Additive workload434, 2026-10-27. The pure worker432 and native capture433 are
separate components. Root retains selected-action/received-input authority,
original native lifecycle qualification, final result receipts and typed
episode delivery. This component executes one finite calculation using the
existing native_lifecycle. It owns no episode decisions or scientific formula.

## Prior interface clarifications

In011 the intended existing export is `validate_genomic_overlap_batch`.
`validate_genomic_overlap_batch_manifest` was a naming error, not a new alias.
If native_file_capture raises a storage/retention failure before returning an
identity, propagate that typed error. Do not fabricate an identity or report
producer absence. A returned actual capture can retain its identity when a
subsequent retention check fails.

Store deduplicates equal bytes. The same artifact_ref/SHA/size/path may carry
different per-role format labels (for example empty stdout and stderr). Check
formats against each role and compare shared-path content identities without
requiring equal format labels. No duplicate artifact or alternate path is
invented to avoid this real Store behavior.

## Exclusive ownership and ports

Own `gene_annotation_episode/native_genomic_overlap_preparation.py`,
`tests/test_native_genomic_overlap_preparation.py` and packet434 verification.
Read but do not edit worker432, capture433, shared host hooks or other modules.

```python
build_native_genomic_overlap_worker_plan(*, directory: str,
    original_plan: dict, batch: dict | None, files: list[dict],
    selector: dict, source_action_receipt_ref: str,
    writer_closure_receipt_ref: str, driver_state: str,
    failures: list[dict]) -> dict
build_saved_genomic_overlap_worker_plan(*, directory: str,
    sheet: dict, selector: dict) -> dict
prepare_genomic_overlap_worker(store, *, plan: dict,
    policy: LocalJobPolicy) -> dict
validate_prepared_genomic_overlap_worker(store, value: object, *,
    plan: dict) -> dict
capture_genomic_overlap_worker_outputs(store, *, directory: str,
    plan_file: dict, execution_receipt_file: dict) -> dict
```

Both builders construct the exact frozen428 WorkerPlan, validate it through432
and return a detached value without I/O. Prepare, validate and capture return
the exact frozen428 WorkerCapture: version, plan_file, execution_receipt_file,
worker_result_file nullable, result nullable, outputs NativeFileCapture[], and
failures G1 Failure[]. No additional public WorkerCapture field is introduced.

## Actual execution and immutable recovery

Preparation requires policy exactly20GiB RAM/4GiB scratch/no wall; zero swap is
verified through the existing lifecycle. The selected original WorkerPlan is
written as canonical no-LF plan.json in its own confined directory. Preserve
exclusive immutable intent/publication and one preparation lock. Use existing
native_lifecycle prepare_job/start_prepared/resume_start/wait_job; no direct
subprocess, new workflow loop or scientific tool invocation. Never restart an
unknown/live original handle or treat observation timeout as terminal failure.
An interrupted caller can recover the same prepared reservation. A terminal
worker failure is retained and is not an automatic retry.

Pin and execute an immutable snapshot of the actual imported project source
closure and interpreter; retain source filenames, SHA and size plus actual
command/environment/request/handle. Source snapshots may reuse the existing
verification discipline, but production cannot import verification files. The
snapshot supplies worker432 and G1/G2/G3a, not a second calculator. Reopening a
completed preparation never snapshots today's sources or runs another worker.

The internal closed WorkerExecution record has exactly:

- version: `genomic_overlap_worker_execution_v1`
- plan_file: actual NativeFileIdentity
- outcome: returned or failed
- returncode: actual integer for returned, null for failed
- metadata: original LocalJobResult.metadata for returned, null for failed
- failure: null for returned; otherwise {code, phase, diagnostic, operational}
  copied from the original known terminal AcquisitionError
- handle_file, request_file, stdout_file, stderr_file: actual NativeFileIdentity
  or null when those files were never produced/captured
- source_pins: ordered array of {path, sha256, size_bytes} for executed snapshot
- interpreter: {path, sha256, size_bytes} for the executed interpreter

Use format `genomic_overlap_worker_execution_v1` for its captured canonical
JSON. Other control formats name the actual existing native handle/request or
stdout/stderr format, without claiming scientific formats. Validate exact plan,
command/module, environment, cwd, handle/request digest and allocation joins.
Metadata returned success/failure comes from real lifecycle results, not guessed
zero exit status. Known unknown/live/quiescence failures propagate for recovery;
they must not be persisted as a completed failed worker. Actual terminal error
evidence and partial outputs survive. Caller cancellation does not select a new
retry or silently reprice completed work.

Record WorkerExecution only after the actual worker has ended/quiesced, and
capture it through native_file_capture. The host helper validates that retained
record before touching worker outputs. LocalJobResult metadata and any terminal
failure's operational evidence remain unchanged. Validate actual terminal
evidence using existing lifecycle semantics; do not invent an alternative
terminal detector. If the exact retained failure cannot prove quiescence,
return the existing unresolved lifecycle exception for recovery.

## Output capture and qualification

Use native_file_capture for every full-file copy and retained verification.
First capture worker-result.json, require canonical no-LF bytes and validate432
WorkerResult. Require mode/parameters equal the original selected plan. Then
capture its exact four declarations in order. Preserve declared absence,
missing present files and digest mismatches separately. A malformed result
remains a diagnostic identity; it does not declare or qualify output files.

If worker-result is missing or invalid, capture only existing fixed output
files as diagnostics. Do not synthesize NativeFileDeclarations. Return
result=null and outputs=[]; retain each actual diagnostic artifact identity in
located G1 Failure.artifact_ref/partial_artifact_refs (with field_path naming
the exact output role and copied observed identity where needed). This keeps
diagnostics under the selected action's WorkerCapture without another registry.

For valid declared outputs, verify actual identities, canonical encoding,
schema, sheet digest/size equality, parameters, component/projection sheet-hash
joins and requested projection kind/fields/page. Do not rerun interval math,
acquire metadata, open original native producer paths or synthesize numbers.
Any full semantic recalculation or G3a comparison over large records must stay
inside a bounded execution, not the unbounded host. Prefer the actual432
validated result and its original bounded execution proof to duplicate math.
If an unexpected verification need requires a new worker interface, report it
before changing432 or introducing a second calculation.

Successful preparation writes one immutable prepared.json WorkerCapture. Its
validation/replay uses only retained plan, execution and output artifacts; no
native producer, current interpreter/source comparison, status probe, recapture
or execution. Missing current artifacts produce typed retention failure and
never rewrite the original prepared record. The root's committed action remains
the authority; this helper's saved record alone grants no episode access.

## Consuming host and verification

Root will pass433's native captures through the native builder, or an actually
received exact saved sheet through the saved builder. Root calls prepare inside
its selected collect and stores the returned WorkerCapture in the ordinary
result receipt. Root admits only the actual qualified projection, with failure
facts when none exists. Internal parse/capture/calculation is not another turn.

Use a small actual native427 fixture plus actual Store capture, native and
saved worker plans, retained output hash joins, missing/malformed worker result,
partial/absent outputs, wrong plan/parameter/field joins, immutable replay and
changed-parameter saved calculation with producer/network/native calls disabled.
Use real existing local_jobs/native_lifecycle for worker execution and recovery;
label injected lifecycle failures separately. Do not repeat the very large
killed fixture already being tested by432 merely for this component.

Read full immutable goal, AGENTS and affected lifecycle/preparation/capture/
worker code. After substantial source/output work and before handoff reread the
objective and all sixteen principles verbatim, then exact accepted contracts.
Every test/calculation uses20GiB/4GiB/zero swap/no wall and readonly pinned
snapshots; preserve every attempt, logs, JUnit and receipts. No prompt, scoring,
literature or accounting edits. No full Workflow or whole-tool count claim.
