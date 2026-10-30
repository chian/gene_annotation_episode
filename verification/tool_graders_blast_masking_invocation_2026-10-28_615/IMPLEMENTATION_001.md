# Masking invocation and original-byte custody

Implementation plan for the assigned producer only. The original user attachment
remains authoritative. This does not change the goal or add scientific scoring.

The five new modules implement the approved 610 interfaces: pure job/schema and
single-argv compilation; four-field configured local tool information; one-command
producer; existing native_lifecycle reservation; authenticated Store capture.
Core Operation validation/schema and FASTA parsing are imported. No masking math,
native defaults, executable discovery, automatic counts/retry, API/HPC binding,
prompt template, dispatch change or progress-row edit belongs here.

## Frozen remaining nested fields

ProducerFailure is closed: `stage` is software/inputs/preflight/execution/outputs;
`code` is one of the module's exported FAILURE_CODES; `role` is a selected input
or output role or null; `ordinal` is 0 for a named role and null otherwise;
`diagnostic_artifact_ref` is null in the native bundle. Native stderr remains an
explicit original artifact. No exception text is inserted into a failure code.

CaptureFailure is closed: `stage="custody"`, `code` is a closed exported capture
code, `direction` input/output or null, `role` selected role or null, `ordinal`
0 or null, `relative_path` confined path or null, `diagnostic_artifact_ref` retained
Store artifact or null. Changed/unsealed bytes remain diagnostic artifacts and
never enter the authenticated artifacts list.

Capture has exactly version=`native_blast_masking_capture_v1`, bundle_artifact_ref
(nullable), bundle_validated (bool), artifacts (list), failures (list). Each artifact
has exactly direction, role, ordinal, format, relative_path, artifact_ref, sha256,
size_bytes. Successful custody is `bundle_validated and not failures`; native
success remains the separate bundle returncode/failures. Missing bytes have no
fabricated artifact. Failed native commands may have entirely valid captures.

Input staged filenames are `inputs/<role>.fa` for FASTA and
`inputs/statistics.ascii` for statistics. Bundle input descriptors preserve the
approved original/expected/staged/final identities. Output descriptors always
include every selected output, with paired null sha256/size_bytes when unavailable.
Original mutation is represented explicitly, never authenticated as the input.

The occurrence identity helper is
`masking_occurrence_id(identity, direction, role, ordinal=0)` and returns
`native_blast_masking:<attempt_id>:<direction>:<role>:<ordinal>`. Record keys are
that occurrence plus the core's `#/records/<ordinal>` suffix. The producer uses
these stable occurrences for preflight and generated-statistics associations.
The result owner replaces preflight artifact identities with the captured Store
artifact refs before parsing. Counts generation binds the actual reference input,
statistics output and producer attempt after a successful sealed output;
producer_source_ref stays null to avoid a source-content self-reference.
Window mask jobs preserve their explicitly supplied StatisticsBinding; its
statistics occurrence is the supplied original occurrence, not the new target
or a rewritten provenance claim. Root validates any received producer source.

Prepared is owned by result publication; producer publication reads the closed
field `source_grading_artifact_ref` (nullable artifact ref) and requires only that
field from Prepared. The result owner defines the complete closed Prepared record
and returns it to root. Producer publication validates and retains this artifact
without parsing numerical values. `prepared=None` is allowed before preparation.

## Verification

Compiler/schema tests cover all four modes, selected/null options, path aliases,
resource/binding/program mismatch, and caller allocation. Custody tests exercise
the real producer with controlled saved bytes (explicitly synthetic process
outcomes), invalid substrate/digest, partial output, sealed replay, uncertain
unsealed replay, changed inputs and exact retained artifacts. One tiny actual
producer invocation per four modes is justified to verify this new compiled
driver path, not to repeat 612 parser arithmetic. They use only runner-staged
explicit native executables and supplied tiny FASTA/ASCII statistics.

All imports/tests/native execution use 529 check068_blast_masking_invocation,
check005 dependencies, 20 GiB RAM, 4 GiB scratch, zero swap and no wall cap.
No database BLAST, network/HPC/auth or model calls. Source and native outcomes
are reported separately from root's later complete Workflow/return verification.
