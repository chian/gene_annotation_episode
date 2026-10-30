# Selected preparation/report producer integration

Implementation contract, 2026-10-28. This closes the specific unconnected
producer boundary in proposal573 section5, using verified P589/R590 functions.
It does not change the original user goal, any historical job, or scoring.
Check044 verifies the current P/R modules and authentic upstream FACS CSV report
extraction:256 passes. It does not verify this new integration.

## Ownership and exact dependencies

Owner A edits `native_fluorescence_contracts.py`,
`native_fluorescence_driver.py`, `fluorescence_execution_common.py`, and the
schema-selection portion of `native_fluorescence_tool_info.py`. A may add narrowly
named native-fluorescence contract/driver helper modules to keep pure validation
separate from I/O. A owns new `tests/test_native_fluorescence_prepared.py` and
its local fixture helpers. Report exact added paths. Do not edit P/R, common
sheet/calculator, result worker/receipts, episode/controller code or prompt text.

P/R public signatures and closed records are frozen in573 section5 and013–017.
Import their validators/functions; do not duplicate their numerical work or
invent another form. In particular, use per-kind DomainIdentity projections,
actual parent EventParseResult, `make_fluorescence_report_binding`, and017 units.
R imports the existing native `_input` validator; use local imports where needed
to prevent a module cycle. Other owners consume the contracts below in parallel.

## Job, capability and software contracts

Implement `native_fluorescence_job_v2` with exactly the existing Job fields plus
`preparations:[PreparationRequest]` and `report_inputs:[ReportInput]`. Preserve
v1 keys/validation and saved records. Keep the public legacy `JOB_SCHEMA` for
consumers that explicitly need v1; add a v2 schema and a version-discriminated
requested-job alternative. V1 cannot acquire the new fields by normalization.

The new binding is exactly the old operation/mode/parsers/software fields plus
`version:"native_fluorescence_binding_v2"`, `preparation_methods:[method]` and
`report_profiles:[profile]`. V1 remains the existing unversioned closed shape.
Methods/profiles are unique declared subsets of the frozen P/R capabilities.
Each bound input schema exposes only that binding's real methods/profiles,
parsers and pinned software; do not combine capabilities from different rows.
Tool information text is root-owned; change only schema selection here and
report its now-outdated unavailable-preparation wording for root to correct.

Validate topology in listed order. A preparation can consume one original
input or an earlier preparation, never itself or a later request. Validate
declared sample/domain/channel/gate joins without creating a fictional executed
Domain. Input, prepared and report keys must not collide. V2 native comparison
requests address exact declared ReportField keys; definitions.native_reports
stays empty for both versions. No input argument supplies a reported number.

Support_inputs exactly cover selected recipe files, separate matrix artifacts,
association files, analyte associations, and comparison evidence. Original event
and report files belong to their own roles rather than duplicate support roles.
Recipe bytes must parse to the exact selected recipe before executing it. Matrix
source and dataset are explicit; for a separate support FCS artifact use a
mechanical source key derived from its preparation index, not an inferred sample.
This key identifies the support artifact only; it authorizes no biological join.

Software validation/actual verification must cover all selected implementation
and installed dependency files. Scaling needs actual FlowIO1.4.0 and NumPy;
compensation additionally needs actual FlowUtils1.2.2 and its NumPy dependency.
R parsers use their actual pure implementation. Preserve v1 closure validation;
require added modules only where imported/selected. No hidden installation,
unverified source fallback or arbitrary callable/command in a recipe.

## Closed outputs consumed by owner B

Use exactly PreparedBatch, ReportBatch and NativeManifest v2 shapes in573
section5. Keep these public signatures:

```
validate_fluorescence_prepared_batch(value, *, original_plan,
    preparation_index, parent_batch_file) -> dict
validate_fluorescence_report_batch(value, *, original_plan, report_index) -> dict
run_fluorescence_driver(plan) -> NativeManifest
```

PreparedBatch binds its original plan/software, exact selected preparation,
actual parent batch identity, recipe identity, resolved parameters/data identities,
assembled parse/status/problems. The envelope validator checks those declared
relationships; it does not pretend to have read external data/parameters. Owner
B separately validates those retained payloads against the actual parent parse.
`preparation_request_sha256` uses P's core.digest(request).
ReportBatch binds its original plan/software, report_input, actual report and
selected association identity plus R's parse. `report_input_sha256`, original
plan and software digests use the existing control digest, as original batches do.
Numerical data/parameters and all parse batch files use core canonical bytes
plus LF. The manifest uses existing control canonical bytes plus LF.

Output order is existing event_input, support_input, event_batch roles, followed
by report_input:i, then for each preparation its preparation_parameters:i,
prepared_data:i, prepared_batch:i, then report_batch:i, and final manifest.
Paths/formats are exactly573 section5. The existing role-driven NativeCapture
shape stays unchanged. Actual run plan outputs declare the versioned manifest.

Execute only the explicitly listed work inside the existing finite driver.
Retain original/support/report bytes before their dependent operation. Preserve
the actual original parse and every closed prepared envelope before proceeding
to another selected request. No gate statistics or shared-score calculation
belongs in the producer. No retry, resource substitution or autonomous schedule.

If required recipe/parent payload is unavailable, no preparation is executed;
its manifest entry has absent payload identities and unavailable status, with
specific failures. If P returns a qualified failure after valid input binding,
retain its actual parameters and failed/unavailable assembled parse envelope.
For a missing report input, preserve its failure and absence in the manifest;
do not call the parser on fabricated empty bytes. Missing association bytes are
passed as None to R, preserving actual report numbers and qualifications.

NativeManifest v2 retains all v1 fields plus the preparations/reports rows from
573. Nullable identities describe actually absent payloads. Add only the five
specified control failure codes: preparation_unavailable,
preparation_incompatible, preparation_failed, report_batch_unavailable,
report_batch_invalid. Extend indexed role validation to the declared new roles;
indices resolve to preparations or report_inputs, not the event-input collection.
Keep detailed scientific problems in P/R's existing typed records.

## Verification and handoff

Cover both operation names, v1 preservation, actual selected gain/time scaling,
compensation, scale→compensate lineage, reports with valid/missing associations,
exact source bytes, missing support, malformed/tampered recipes, unavailable
backend, partial inputs and surviving earlier envelopes. Assert no common
calculator invocation in the producer and no undeclared preparation.
Provide current file hashes, selectors and required staged native dependencies.

All application imports/native computation/tests use root's existing bounded
20GiB RAM/4GiB scratch/zero-swap runner, without a wall limit. Host inspection
is stdlib/source only. Read the user attachment goal and relevant complete
consumers first. After substantial source examination/tool work, reread its
objective and entire operating principles verbatim, then this contract before
handoff. Neither component tests nor this work closes the whole tool inventory row.
