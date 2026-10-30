# R7 sequence-masking implementation handoff — interfaces 001

This is an implementation proposal for `dustmasker`, `segmasker`, and
`windowmasker`, not a replacement goal, scope amendment, completion claim, or
runtime instruction. The original user attachment remains authoritative. No
production code, application imports, native executables, tests, services, or
database reads were run to prepare it.

## 1. Fixed ownership and first concrete binding

Use one **raw-sequence masking** sheet/calculator for the three mask operations.
Use a separate **WindowMasker statistics artifact** parser/typed validator for
statistics creation and supplied statistics. Neither produces function confidence,
annotation credit, complexity significance, homology support, or a new score
channel. A masked fraction is a description of this output, not a quality score.

The first native binding offers exactly these supplied-data modes:

| Program / mode | Input | Selected native output |
| --- | --- | --- |
| dustmasker / mask | One uncompressed nucleotide FASTA artifact | `interval`, or `fasta` with explicit soft/hard choice |
| segmasker / mask | One uncompressed protein FASTA artifact | `interval`, or soft `fasta` |
| windowmasker / mask | One uncompressed nucleotide FASTA plus one explicitly supplied ASCII statistics artifact | `interval`, or soft `fasta` |
| windowmasker / create_counts | One uncompressed nucleotide reference FASTA | ASCII statistics (`-mk_counts -sformat ascii`) |

Both WindowMasker modes are selected operations. Creating counts never follows
automatically from requesting a mask. The episode can later select a mask job
whose `statistics` operand is the artifact actually returned by the counts job.
It can also supply existing statistics whose producer/reference are unknown.
The background reference need not be the masking target.

The current first binding does **not** advertise BLAST database input, remote
seqid input, list-file input, identifier filters, compressed streams, statistics
conversion, binary/optimized statistics, ASN.1/XML masks, or DUST `acclist`.
They are documented native capabilities, not installed/bound/tested capabilities.
In particular, `acclist` omits zero-mask records and can make duplicate/generated
headers ambiguous; do not advertise it until its occurrence association has a
tested contract. This is an explicit format limit, not a requirement to implement
all native modes before any of the three operations can work.

Only a configured local supplied-data binding is proposed now. No API or HPC
binding is inferred. Root must run native and application work in the existing
20 GiB RAM / 4 GiB scratch / zero-swap / no-wall-cap runner. Database-scale work
stays off the local machine.

## 2. Shared definitions to reuse

* `hmmer_search_grader._union(intervals)` already merges overlapping/adjacent
  zero-based half-open pairs and returns `{"intervals": [...], "positions": n}`.
  The new calculator calls it; it does not copy/reimplement the algorithm.
* `genomic_overlap_calculations._ratio(numerator, denominator, missing_reason)`
  already returns numerator, denominator, value and missing reason, with zero
  denominators undefined. The new calculator calls it after its own typed input
  validation. Do not relabel its output as a score.
* `material_parsing.records` / `domain.parse_sequences` supply existing normalized
  sequence/ordinal/locator semantics. They uppercase sequence text. Preserve the
  original input and output case **before** normalization. Do not infer masks from
  an already uppercased parsed sequence.
* The HMMER `alimask` sheet concerns alignment columns and MM/model-map annotations;
  its denominator and inherited-mask semantics differ. Do not put raw DNA/protein
  masks into that sheet. Genomic overlap comparisons likewise have a different
  question and namespace. Only the existing union and ratio primitives are shared.
* Existing BLAST pairwise/database identification graders remain untouched. Native
  mask outputs are not HSPs, alignment identity, or search sensitivity estimates.

Direct use of the two existing pure helpers is the narrow implementation choice
for this workload. A later public-helper extraction requires a separate concrete
need; it is not a blocker or permission to refactor completed graders now.

## 3. Exact pure-core files and signatures

One fresh core owner owns these NEW files and their focused tests:

```python
# gene_annotation_episode/sequence_masking_contracts.py
validate_sequence_masking_record(kind: str, value: dict) -> dict
# kind: Operation, Occurrence, InputRecord, Custody, ParsedMaskOutput,
#       SequenceMaskingSheet, SequenceMaskingComponents, StatisticsBinding,
#       WindowMaskerStatistics, Failure, Check

# gene_annotation_episode/sequence_masking_inputs.py
parse_masking_input_fasta(content: bytes, *, occurrence: dict,
                         molecule: str) -> dict
parse_sequence_masking_output(content: bytes, *, format: str,
    occurrence: dict, input_records: list[dict], operation: dict,
    custody: dict) -> dict
populate_sequence_masking_sheet(*, operation: dict, inputs: list[dict],
    parsed_output: dict, statistics: dict | None,
    native_outcome: dict) -> dict

# gene_annotation_episode/sequence_masking_calculations.py
calculate_sequence_masking_components(sheet: dict) -> dict

# gene_annotation_episode/windowmasker_statistics.py
parse_windowmasker_statistics(content: bytes, *, occurrence: dict,
    format: str, reference_binding: dict | None) -> dict
validate_windowmasker_statistics(statistics: dict) -> list[dict]
```

All functions are deterministic and offline. They do not read files, execute a
program, acquire resources, search, create database records, or call models.
`validate_sequence_masking_record` returns a finite JSON deep copy, rejects
unknown keys, bool-as-int, NaN/infinity and invalid cross-field relationships.
Bad caller/schema arguments raise `ContractError` with a stable machine code.
Malformed **native content** returns retained parseable rows plus typed failures;
it does not discard the whole artifact or turn missing measurements into zero.

### Common field shapes

All shapes below are closed. `?` means an explicit nullable field, not an absent
field. Native text is retained as data, never used as instructions. Host identifiers,
paths, hashes and tracking stay out of rendered TASK/STEERING.

```text
Occurrence = {
  occurrence_id: nonempty string, direction: "input"|"output",
  role: "sequences"|"reference_sequences"|"statistics"|"mask"|"stdout"|"stderr",
  ordinal: integer>=0, artifact_ref: nonempty string,
  sha256: 64 lowercase hex, size_bytes: integer>=0,
  completeness: "complete"|"partial"|"unknown"
}
Failure = {
  stage: "input"|"parse"|"association"|"native"|"statistics"|"calculation"|"custody",
  code: restricted machine string, occurrence_id: string?,
  record_key: string?, line_number: integer>=1?
}
Check = {
  name: restricted check name, status: "pass"|"fail"|"unknown"|"not_applicable",
  record_key: string?, reason: restricted machine string?
}
Operation = {
  version: "sequence_masking_operation_v1",
  program: "dustmasker"|"segmasker"|"windowmasker",
  mode: "mask"|"create_counts", engine_version: nonempty recorded string,
  input_format: "fasta", output_format: "interval"|"fasta"|"ascii_statistics",
  masking_style: "soft"|"hard"|"interval"|"not_applicable",
  parse_seqids: bool, requested_parameters: closed program/mode object
}
InputRecord = {
  record_key: occurrence_id + "#/records/" + decimal record_ordinal,
  occurrence: Occurrence, record_ordinal: integer>=0,
  byte_offset: integer>=0, native_header: string,
  molecule: "dna"|"protein", original_sequence: string,
  normalized_sequence: uppercase string, length: integer>=0
}
```

`length` counts ungapped raw-sequence symbols, not bytes or aligned columns.
Input normalization removes FASTA layout whitespace, preserving the original
case string and raw artifact. Initial native jobs reject empty records, gaps,
unsupported symbols and RNA-as-DNA substitution rather than silently changing
the supplied substrate. The pure parser can retain such records as invalid with
typed failures. Allowed native alphabet compatibility must be established by the
tiny native oracle; IUPAC DNA and supported protein symbols are not a license to
silently replace unsupported input. Duplicate headers remain separate occurrences.

```text
InputParse = {
  version: "sequence_masking_input_v1", occurrence: Occurrence,
  records: list[InputRecord], checks: list[Check], failures: list[Failure]
}
Custody = {
  producer_kind: "authenticated_native"|"supplied_artifact",
  sequence_order: list[record_key],
  order_basis: "native_fasta_iteration"|"caller_declared"|"unknown",
  output_complete: bool,
  native_returncode: integer?,
  record_bindings: list[{output_record_ordinal: integer>=0,
                         input_record_key: record_key,
                         basis: "native_fasta_iteration"|"caller_declared"}]
}
```

The host creates `authenticated_native` only after qualifying the original job,
attempt, selected FASTA, sealed output bytes, and observed return code. The core
never authenticates a caller just because its JSON says so. Successful, complete
FASTA/interval output with the expected nonempty input population can use source-
established native iteration order, including duplicate headers. Native-generated
headers are retained and are not required to equal the raw input header. Imported
artifacts use an explicit declaration and retain that qualification. No fuzzy name,
first-match, or count-only cross-artifact association is allowed.

For partial output, the host/core must not guess missing positions in the output
population. Explicitly proved bindings can retain usable rows; unbound blocks stay
in `unassigned_records`. A following header closes a prior interval block; EOF on
an unsealed/failed output does not prove the last block complete or unmasked.

### Parsed mask output and common sheet

```text
MaskRecord = {
  output_record_ordinal: integer>=0, input_record_key: record_key?,
  native_header: string, output_locator: {byte_offset: integer>=0,
                                        line_start: integer>=1, line_end: integer>=1},
  native_intervals: list[{start: integer>=0, end_inclusive: integer>=0,
                         line_number: integer>=1}],
  intervals_half_open: list[[integer>=0, integer>=0]],
  output_sequence: string?,
  association: "authenticated_native_order"|"caller_declared"|"unresolved",
  completeness: "complete"|"partial"|"unknown",
  measurement: "exact_mask"|"hard_mask_ambiguous"|"unavailable",
  failures: list[Failure]
}
ParsedMaskOutput = {
  version: "sequence_masking_parsed_output_v1", format: "interval"|"fasta",
  occurrence: Occurrence, custody: Custody,
  records: list[MaskRecord], unassigned_records: list[MaskRecord],
  checks: list[Check], failures: list[Failure]
}
NativeOutcome = {
  returncode: integer?, state: "succeeded"|"failed"|"incomplete"|"unknown",
  output_complete: bool
}
SequenceMaskingSheet = {
  version: "sequence_masking_sheet_v1", operation: Operation,
  inputs: list[InputRecord], parsed_output: ParsedMaskOutput,
  statistics: WindowMaskerStatistics?, native_outcome: NativeOutcome,
  checks: list[Check], failures: list[Failure]
}
```

The parser owns native syntax, preserving original endpoints, source locators,
case, unassigned records and native score/parameter lexemes. The calculator owns
interval union, cardinality and fractions. The parser only converts coordinates
and extracts runs of lowercase letters; it does not deduplicate/merge native rows
or calculate a fraction. Original outputs are always retained separately.

For `interval`, the native writer uses **zero-based inclusive** `START - END`.
`[s,e]` becomes `[s,e+1)` and must satisfy `0 <= s <= e < input.length`.
For soft FASTA, lowercase positions are the output mask, represented as half-open
runs. Check length and normalized sequence compatibility with the selected input.
The native reader/writer does not preserve input lowercase as an existing mask;
do not subtract it or apply `alimask --append` semantics. Sequence substitutions,
truncation or incompatible native normalization invalidate exact mask inference.

For DUST hard FASTA, newly changed non-N positions can be identified. Pre-existing
N positions cannot reveal whether they were selected for masking. An otherwise
compatible output is a valid prepared sequence with an ambiguous total mask:
`measurement="hard_mask_ambiguous"`. If the input has no N and changes are only
to N, exact changed-to-N positions can establish the exact mask. Do not report
every output N as masked or equate a successful transformation with mask quality.

### Numerical components, units and missing values

```text
Count = {value: integer>=0?, unit: "nt"|"aa"|"intervals"|"records",
         missing_reason: restricted machine string?}
Fraction = {numerator: integer>=0?, denominator: integer>=0?,
            value: finite number in [0,1]?, missing_reason: machine string?}
RecordComponents = {
  record_key: record_key, unit: "nt"|"aa",
  input_length: Count,
  native_interval_count: Count,
  merged_interval_count: Count,
  merged_intervals_half_open: list[[integer,integer]]?,
  masked_positions: Count, unmasked_positions: Count,
  masked_fraction: Fraction,
  changed_positions: Count,
  checks: list[Check], failures: list[Failure]
}
SequenceMaskingComponents = {
  version: "sequence_masking_components_v1",
  analysis: "sequence_masking_preparation", records: list[RecordComponents],
  checks: list[Check], failures: list[Failure]
}
```

* `input_length`: exact selected normalized raw-sequence length; nt for DUST and
  WindowMasker, aa for SEG. An unassociated record has no input denominator.
* `native_interval_count`: number of retained native interval rows, including
  duplicates, only for interval output; FASTA has no native interval-row count.
* `merged_interval_count`: count of shared-union components for an exact mask.
* `masked_positions`: shared-union cardinality, never the sum of overlapping rows.
* `unmasked_positions`: input length minus exact masked positions.
* `masked_fraction`: exact masked positions / the same input record length.
  Empty denominator is undefined. No bin-level, database-size, alignment-column,
  or total-batch denominator is substituted.
* `changed_positions`: case-insensitive input/output symbol differences when
  a compatible, equal-length FASTA pair exists. Soft masking normally changes
  case only and thus has zero symbol substitutions. Interval output has no
  output sequence and this quantity is not applicable. It is not total masking.

Where a record is partial, malformed, unassociated or hard-mask ambiguous, exact
masked count/fraction are null with the precise missing reason. Retained valid
interval rows remain available in the sheet; do not extrapolate them to a full
record. A complete, authenticated interval header with no rows yields exactly
zero masked positions and fraction zero for nonempty input. A missing file/header
does not. Native failure does not erase well-formed, explicitly associated closed
records; preserve their qualification and keep overall execution failure separate.
No batch-average score is added. Additional exact requested aggregations can be
recomputed later from the full retained sheet without changing native parameters.

Illustration only (not a native result): input length 12, native inclusive rows
`0-3`, `2-5`, `8-8` give merged half-open `[0,6)`, `[8,9)`, masked count 7,
unmasked count 5, fraction `7/12`, three native rows and two merged intervals.

## 4. WindowMasker statistics interface

```text
StatisticsBinding = {
  kind: "generated"|"supplied",
  statistics_occurrence_id: nonempty string,
  reference_occurrence_ids: list[nonempty string],
  producer_source_ref: string?, producer_attempt_id: string?,
  provenance: "authenticated_generation"|"caller_declared"|"unknown"
}
WindowMaskerStatistics = {
  version: "windowmasker_statistics_v1", occurrence: Occurrence,
  format: "ascii_statistics", reference_binding: StatisticsBinding?,
  format_version: string?, algorithm_version: string?,
  unit_length: integer in [1,16]?,
  metadata_lines: list[{line_number: integer>=1, text: string}],
  unit_counts: list[{line_number: integer>=1, unit_code_hex: string,
                    unit_code: integer>=0, native_count: integer>=0}],
  thresholds: {t_low: integer?, t_extend: integer?,
               t_threshold: integer?, t_high: integer?},
  percentiles: list[{line_number: integer>=1, count: integer>=0,
                     percentage: finite number, percentage_lexeme: string}],
  checks: list[Check], failures: list[Failure]
}
```

ASCII parsing retains comments/metadata, all unit rows and all thresholds; no
sampling or top-N reduction. Codes are hexadecimal native unit codes, with range
`0 <= unit_code < 4**unit_length`; do not invent a sequence decoding convention.
`native_count` is an integer native statistic whose generation thresholds may
clip values and omit low-count units. It is **not** a normalized probability,
genome proportion, complete count matrix, or evidence for gene function. An absent
unit is not a measured zero. Do not infer a missing genome-size denominator.

Checks include syntax, one unit length, unique code rows, native ordering, code
range, integer counts, threshold presence and permitted values, metadata parameter
agreement where recorded, percentile syntax/range, complete output custody and
declared reference relationship. Missing `##pct` is permitted by some native files;
it does not mean percentile overrides were applied. Preserve native warnings and
mark their effective values unknown unless original native metadata proves them.

The `generated` binding requires original recorded generation input occurrence(s),
output occurrence and attempt. The host validates that relation. A caller's claim
is `caller_declared`, never promoted by the parser. Supplied external statistics
can have unknown reference provenance; masks still describe the native output,
qualified by that provenance. This is not an automatic scientific rejection gate.

## 5. Producer and result ports

The resource adapter uses `requested_job.native_blast_masking` and the existing
`launch`, `launch_local` and `results` roles. Proposed native interface names:

```python
# NEW native_blast_masking_contracts.py
validate_native_blast_masking_job(value: dict) -> dict
compile_native_blast_masking_job(job: dict, *, input_paths: dict,
                               output_directory: str) -> list[str]
requested_job_from_native_blast_masking(job: dict) -> dict
validate_native_blast_masking_requested_job(value: dict) -> dict

# NEW native_blast_masking_tool_info.py
validate_native_blast_masking_bindings(rows: list[dict]) -> list[dict]
native_blast_masking_tool_contracts(bindings: list[dict], *,
                                  resource_kind: str, resource_id: str) -> list[dict]

# NEW native_blast_masking_local.py
prepare_local_blast_masking(...same owner/attempt/local-policy port as
                            native_blast_local.prepare_local_blast...) -> dict
local_blast_masking_plan(path: str) -> dict

# NEW native_blast_masking_acquisition.py
is_native_blast_masking_target(target: dict) -> bool
capture_native_blast_masking(...same retained-original capture port as
                            native_blast_acquisition.capture_native_blast...) -> dict

# NEW native_blast_masking_result_worker.py
run(plan: dict) -> dict
# tasks are separately selected parse_calculate and project_saved;
# no native executable, acquisition, model call or Store write inside either.
```

The invocation owner must resolve the two `...same port...` signatures from the
complete existing modules before coding those files; HANDOFF_001.md pins exact
existing functions and all dispatch consumers. Core coding does not depend on
those resource adapter arguments. No resource-specific sheet/calculator exists.

The producer's small sealed manifest contains version
`native_blast_masking_bundle_v1`, original requested job, exact executable identity,
run/episode/resource/execution/attempt identity, selected argv, original input
descriptors, staged/final identities, explicit output descriptors, stdout/stderr,
return code and typed failures. Use the existing native lifecycle/immutable capture
patterns. Never auto retry an unsealed attempt or resolve an absent executable by
searching another environment. Preserve partial originals before calculation.

Each `inputs` descriptor contains role, ordinal, format, absolute source path,
artifact reference, expected SHA256/size and exact record occurrence associations.
Each `outputs` descriptor contains role, native format and confined relative path.
The job is a single native command with one selected output. It does not execute
both mask formats or create counts unless those are separately selected jobs.

The result worker consumes authenticated retained byte descriptors and the exact
Operation, Custody, StatisticsBinding and NativeOutcome above. It writes the full
sheet, full calculations (or full statistics plus checks), and a separate immutable
selected projection. Requested projection fields are drawn from those frozen
outputs. Returning them must not reparse/recalculate/reexecute or widen the
parent's requested form. Original artifacts remain available for a later explicit
saved-data recalculation; changing DUST/SEG/Window native thresholds requires a
new episode-selected native job, not a calculator setting.

`sequence_masking_result_views.py` will own these sources:
`execution.masking_status`, `execution.masking_artifacts`,
`execution.masking_quantities`, `execution.masking_checks`,
`execution.masking_statistics`, `execution.masking_failures`.
Status uses closed values complete/partial/failed/unavailable. Quantities use the
finite components above plus source/record/quantity references; statistics returns
only requested native fields/rows, with its original artifact available. Failures
use the closed shape above; arbitrary exception prose remains a diagnostic artifact.
The result receipt authenticates the original source/attempt/selector. Reuse
`EpisodeReturnRecords` for immediate-child return admission and field restrictions.
No new domain scientific-observation marker is needed.

Publication and return are preparation facts and artifact references. The existing
operational acquisition credit counts the original result once, not the number of
records/intervals/quantities/checks. Parsing and projection add no observations.
Scientific/monitoring credit stay separate. The ordinary practical completion proof
sets future expected yield to exact zero after the requested endpoint is validated.
There is no mask-fraction threshold, acceptance score or extra completion turn.

## 6. Independent coding workloads and required outputs

1. **Core owner:** the four pure-core files in section 3 plus
   `tests/test_sequence_masking.py` and `tests/test_windowmasker_statistics.py`.
   Required outputs are the exact schemas/functions above, parsers for the first
   bound formats, shared-calculator calls, saved-sheet recalculation, and tests
   covering overlap, duplication, empty-vs-missing, case, ambiguous hard N,
   malformed partial rows, mixed input occurrences and clipped statistics.
   No runtime dispatch, source publication, native commands or progress edits.
2. **Invocation owner:** new native_blast_masking_contracts/tool_info/driver/local/
   acquisition modules; exact producer manifest; pure compiler/contract tests.
   Required output to the result owner is an authenticated retained bundle plus
   retained files, Operation, Custody, NativeOutcome and StatisticsBinding.
   Do not edit shared execution modules while root is integrating other families.
3. **Result owner:** new native_blast_masking_result_worker/results/returns modules,
   result publication module, sequence_masking_result_views and presentation;
   focused saved-result/return tests. Required inputs are core schema/functions and
   the producer's explicit bundle shape, not “all R7 work”. Use the existing
   results episode, frozen projection and immediate-child boundary machinery.
4. **Root integration owner:** shared execution/communication/receipt dispatch
   edits identified in HANDOFF_001.md, native tiny oracles, full selected
   child-owned episode -> requested return checks and additive fixed-row accounting.
   Native compatibility differences must be sent back as precise input/output
   contract corrections, preserving raw fixtures. No hidden alternative invocation.

Each coding task receives the original user attachment, AGENTS.md, this concrete
contract and the mandatory verbatim reread requirement. Read complete affected
consumers before editing. Source-derived fixtures must be labelled synthetic;
only outputs actually run by root can count as native verification.
