# Barcode B4 additive public ports

The original attachment remains authoritative. This freezes implementation
records before their consumers are written;493/CONTRACT.md is unchanged.

The selector, three fact sources, class ports and plan fields are exactly those
in CONTRACT.md. The internal native capture has exactly `version` =
`barcode_native_capture_v1`, `original_plan_sha256`, `files`,
`source_action_receipt_ref`, `writer_closure_receipt_ref`, `driver_started`
(true/false/null), and `failures`. `files` retains every original plan output in
order, each with `role,relative_path,format,retained`. `retained` is null or
`{file: ArtifactFile,path: absolute Store path}`. Host capture does no scientific
decoding; the bounded worker qualifies declared manifest roles and exact bytes.

Worker result has exactly `version` = `barcode_worker_result_v1`, `mode`,
`plan_sha256`, `selector`, `outputs`, `failures`, `input_identity` (null or
`{sha256,size_bytes}`), `request_sha256` (null or SHA256), `sample_key` (null or
recorded sample key), `native_binding` (boolean), `native_outcome` (null or
ok/partial/failed), `native_stages` (null or the491 stage map),
`count_population_extent` (unknown/complete/prefix),
`original_population_acquired`, `count_population_complete`, and
`requested_delivery_complete` (three separate booleans).

`outputs` has exactly four ordered `{role,declaration}` rows: sheet,
calculations, projection, diagnostics. Declarations use the existing
NativeFileDeclaration shape and CONTRACT.md filenames/formats. Missing output
has state absent and null SHA/size. `worker-result.json` is separate.
Diagnostics has `version` = `barcode_result_diagnostics_v1`, `plan_sha256`,
`failures`. Failures use491 BarcodeIssueV1 unchanged; transport failures locate
existing fields (artifacts, manifest, reads, writer_closed or the affected
table), using missing_artifact, artifact_identity_mismatch,
native_execution_failed, resource_limit_exceeded or invalid_saved_sheet as
appropriate. No transport code is inserted into the scientific sheet.

A complete validated read population, including genuinely empty/no-match
input, is acquired once. A validated nonempty prefix is useful partial
acquisition, but cannot complete required full-population delivery. Later native
distance/cluster failure does not erase independently validated counts. Saved
calculation never acquires an original population. Requested-delivery completion
checks the selected numerical fields and row-family availability; available,
zero_denominator and scientifically applicable not_applicable states can finish.
Missing_input, invalid or partial_population required cells cannot finish. An
issues-empty test is expressly not used. Full original acquisition and requested
delivery remain separate so a failed projection can be repaired from its saved
sheet without native analysis.

Prepared capture has exactly `version` = `barcode_worker_capture_v1`,
`plan_file`, `execution_receipt_file`, `worker_result_file` (nullable), `result`
(nullable worker result), `outputs` (ordered existing NativeFileCapture rows),
and `failures`. No result means outputs is empty. Execution receipt uses the
existing NMF mechanical fields with version `barcode_worker_execution_v1`:
`plan_file,intent,terminal,quiescent,policy,returncode,metadata,failure,handle_file,
request_file,stdout_file,stderr_file,handle,request,request_raw`. Intent has
`version` = `barcode_worker_intent_v1`, `plan,policy,command,environment,
source_pins,interpreter,dependencies,python_version,python_home,runtime_files,
native_library_pins`. Source, interpreter, dependencies, stdlib and executable
native-library bytes are pinned before and after the original bounded handle.

NativeBarcodeResults owns immutable selected-action controls and stores only
qualified file identities plus small projections in receipts. BarcodeReturns
authenticates original immediate-child forms and frozen forwarding prefixes.
Private measurement contribution origins prevent duplicate acquisition credit
and do not grant sheet/native operands. New saved use verifies that the exact
received sheet's retained bytes currently exist; historical delivery reads only
its recorded controls and metadata. Shared runtime consumes the class ports,
not these internal record details.
