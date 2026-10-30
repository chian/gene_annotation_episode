# Infernal original-result acquisition: workload 223

This is implementation of boundary 5's acquisition portion from workload 221.
It does not alter the immutable goal or delegate scientific grading. Read the
entire original goal attachment before work and reread its objective and all
16 design principles after substantial native study and before closure. Read
AGENTS.md and all mandatory execution design records before changing behavior.

## Exclusive ownership

- New gene_annotation_episode/native_infernal_acquisition.py
- New tests/test_native_infernal_acquisition.py and a dedicated fixture directory
- This verification directory

Do not modify existing shared files, producer files, contracts, numerical
graders, inventory, prompts, design records or other workloads. Root owns all
shared runtime integration. Workload 222 owns the original producer and bridge.

## Inputs and dependencies

Read native_hmmer_acquisition.py completely for the existing acquisition/source
mechanism, not as scientific authority. Read native_infernal_contracts.py and
workload 222's producer/bridge, plus the complete called material/state helpers.

The producer has version native_infernal_bundle_v1 and exact fields: version,
identity, requested_job, program, table_format, software, realized_argv,
environment, inputs, operand_bindings, returncode, artifacts, failures,
started_at, finished_at. See 222's WORKLOAD_001.md for each nested field.
local_infernal_plan(assignment, execution_id) returns the exact frozen run plan.
compile_native_infernal_job resolves the selected original operands/output paths.
The existing state store retains full immutable artifacts and source records.

## Public functions and exact handoff

- is_native_infernal_target(target) -> bool: recognize the explicit original
  requested_job.native_infernal branch for local/HPC; recognition does not claim
  an HPC binding. Capture below supports only actual local attempts.
- validate_original_bundle(bundle, plan) -> finite independent validated bundle.
  No I/O. Check original identity, requested job, software, program/table format,
  bindings, staged inputs, compiled argv/environment, selected output roles and
  paths, typed actual hashes/sizes/failures, and sealed timestamps. Successful
  complete attempts must retain every selected output. Failed native attempts
  may retain only the outputs actually produced. Preserve their failures.
- capture_local_bundle(store, *, target, directory) -> {
  version: native_infernal_capture_v1, bundle_artifact_ref: str|null,
  bundle_validated: bool, artifacts: list, invalid_artifacts: list,
  failures: list, complete: bool }.
  Each artifact row is {role, format, relative_path, artifact_ref}; each failure
  is {stage, code, record_key:null}. Capture the complete original manifest plus
  all actual selected input/output bytes, validating actual size/hash. Retain
  mismatched captured bytes separately, never grade them as validated outputs.
  This is an explicitly selected acquisition, with no execution/retry/resource
  decisions, network access, parser, calculator, model call, or extra credit.
  complete describes capture completeness, not scientific success. Validate
  paths/symlinks and immutable capture identity. Saved replay must validate its
  stored artifacts/associations without reacquiring or rerunning the original.
- original_source_payload(*, bundle, capture, prepared) -> existing source
  payload: provider episode.execution_result, accession native_infernal_ plus
  original identity digest, uri null, artifact_ref bundle artifact, text_ref
  null, request_ref null, version native_infernal_bundle_v1, retrieved_at actual
  finished_at, auxiliary_artifact_refs sorted unique captured input/output and
  invalid artifact refs plus prepared.source_grading_artifact_ref when present.
- publish_original_source(store, *, bundle, capture, prepared) -> source id.
- Export ORIGIN using existing execution_result acquisition qualification
  meanings, and VERSION = native_infernal_capture_v1.

Root's upcoming native_infernal_results.py and publication module consume these
exact functions/fields. They alone choose the original requested projection,
call grading, and publish numerical observations. Coordinate interface changes
with root and 222 before editing contracts; no inference from program names.

## Required verification

Use exact synthetic sealed-bundle fixtures and, when 222 has sealed a real
case, one actual native producer bundle. Verify complete inputs and outputs,
same-original-job validation, wrong identity/hash/size/role/path, symlink escape,
missing outputs, partial failed native output, retained mismatched bytes,
source identity independent of projection, and saved replay without acquisition
or execution. Preserve measured zero and unknown values. Report precisely what
was tested and what remains unverified. Local test processes use the existing
20 GiB RAM / 4 GiB scratch / no wall-cap policy.
