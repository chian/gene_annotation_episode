# Proposed common boundary — preparation only

These are proposed coding contracts, not installed production capabilities. The
ten original A-L076 rows remain separate. No preparation output creates a
biological observation or annotation-confidence score. Generated samples and
simulation scores remain generated/model-derived. Parent-selected jobs,
resources, options, typed returns and continuation retain their existing owners.

## Data envelope and custody

Proposed `Operation = {program, mode, engine_version, settings}` preserves actual
arguments, with a finite program/mode registry. `ArtifactOccurrence =
{occurrence_id, direction: input|output, role, ordinal, artifact_ref, sha256,
size_bytes, format, completeness: complete|partial|unknown}`. Identical content
hashes may share retained bytes but NEVER merge occurrences or roles. Record keys
are `(occurrence_id, kind, record_ordinal)`, not names, accessions or hashes alone.
Locators retain byte intervals [start,end), one-based inclusive line intervals,
and record ordinal. Each quantity keeps `{value|null, state, basis, unit,
native_token|null, inputs:[locator+field]}`; states are present, missing,
not_measured, failed, truncated, incompatible, invalid. Zero is a present value.
Unsupported/opaque formats have unknown decoded populations, not zero records.

`PreparationSheet = {schema, operation, artifact_occurrences, input_records,
output_records, native_rows, associations, issues}`. Associations explicitly join
input/output record occurrences, with relation and validated/unresolved/conflicting
status. Original order alone establishes a join only where the native contract
guarantees it and identities/lengths/alphabet agree. Native duplicate names remain
separate occurrences and may prevent unique key resolution. Retain complete files,
including model bodies, alignments, sidecars, stdout and stderr; projections are
separate small requested typed facts.

`CalculationResult = {schema, operation, parameters, rows, checks, issues}`.
Numerical parameters/tolerances/background distributions are explicit saved data.
Checks use pass/fail/unknown/not_applicable, never numeric confidence. Issues use
closed codes, stage, severity, occurrence/record/field references. Failed or partial
native runs retain valid partial rows. An absent file, zero-byte file, empty decoded
population, malformed record and unsupported decoder remain distinct.

## Pure functions and integration handoff

Suggested common reader port:
`extract_hmmer_models(content: bytes, *, occurrence, format, engine_version=None)
 -> {records, issues, population_complete}`. HMMER3/f ASCII amino/DNA/RNA is the
first complete body contract; other HMMER3 revisions, HMMER2 and binary formats
must be explicit versions, not aliases. Store emission/transition tokens plus
decoded probabilities and annotations. HMMER3 ASCII stores negative natural-log
probabilities; `*` means probability zero. Do not treat these as bit scores.

Each tool-specific parser and calculator listed in its report is a separate
function. Suggested dispatch ports:
`grade_hmmer_preparation(*, operation, inputs: role->list[Payload], outputs:
role->list[Payload], parameters) -> {sheet, calculations}` and
`recalculate_hmmer_preparation(sheet, *, parameters) -> CalculationResult`.
Payloads supply occurrence descriptors and complete bytes. These functions do no
network calls, subprocesses, conversion, resource choice, retries or LLM work.

Use existing `PracticalResourceEpisodes` / `LocalPracticalOperations` selected
`practical.job.start` and existing native lifecycle. A proposed separate
`native_hmmer_preparation` request/compiler/driver family should reserve/stage
exact inputs, execute one chosen native command and seal the original attempt.
`NativeHMMERResults` is a search-result implementation that publishes observations;
do NOT route preparation through its search-observation publication. Reuse the
preparation-specific pattern in `NativeInfernalPreparationResults.execute`,
`prepare_native_infernal_preparation_grading`, occurrence normalization and typed
preparation returns. New HMMER names must remain distinct from Infernal APIs.
`execution.results.collect` consumes a sealed original attempt and invokes a
separate proposed HMMER preparation worker, then requested deterministic
projection/validation. Never rerun a tool to make a saved sheet recalculable.

Resource prerequisites: exact executable/version/digest; complete local supplied
inputs and requested output locations; caller-owned allocation. Native examples
here used local_jobs, 21474836480 bytes RAM, 4294967296 bytes scratch and
wall_seconds=null. No API or HPC deployment/binding was verified. Native logs'
CPU/elapsed values are program-reported execution diagnostics, separate from
local_jobs systemd-service-wall timing. A new resource attempt requires a new
explicit selection. Prepared binaries/indexes are validated against their exact
source occurrence and attempt, not a matching filename alone.

## Reuse limits already established

`native_hmmer_contracts` supports six searches/alignment, not these ten tools.
`native_hmmer_result_worker._profiles` extracts search metadata; it is not a
complete probability-body reader. `infernal_preparation_models` accepts only
HMMER3/f nucleotide HMM framing and embeds it in CM semantics; it rejects amino.
Its quantities/locators/missing states are reusable concepts, not an adequate
HMMER model decoder. `infernal_preparation_schema` artifact identity requires
unique refs; the newer preparation publication occurrence layer is the relevant
place to preserve duplicate-byte roles. Do not bypass that distinction.
