# B-L130 B1/B2 public data contract, revision 1

Implementation clarification of historical packet486; the original user goal is
unchanged. B1/B2 owns the five `barcode_*.py` modules and four assigned tests.
All public records are plain JSON-compatible dictionaries/lists, except complete
retained payloads are Python `bytes`. Runtime validators reject extra keys,
booleans used as integers, nonfinite numbers and inconsistent associations.
No schema interpreter, native execution, resource selection or model call exists
in these readers/calculators. This file freezes producer ports before tests finish.

## Shared helpers and exact request

`barcode_contracts.py` exports `canonical(value) -> bytes` (UTF-8 JSON,
`sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False`),
`digest(value) -> str` (SHA-256 of canonical JSON), `file_identity(raw, format)`
and `validate_request`, `validate_sample`, `validate_target_row`, `validate_file`,
`validate_manifest`, `validate_population`, `validate_sheet`,
`validate_parameters`, `validate_projection_request`, `issue`.

`ArtifactFile` has exactly `artifact_ref`, `sha256`, `size_bytes`, `format`.
`artifact_ref == 'artifact_' + sha256`; sha256 is lowercase 64-digit hex;
size_bytes is a nonnegative integer. Format is the exact version below.

`BarcodeRequestV1` has exactly:

```
version: 'barcode_request_v1'
operation: 'analyze_barcode_sequencing_data'
reads: ArtifactFile (format equals request.format)
format: 'fasta' | 'fastq_sanger'
compression: 'none' | 'gzip'
encoding: 'ascii' | 'utf-8'
sample: BarcodeSampleV1
extraction: BarcodeExtractionV1
min_count: integer >= 1
distance_mode: 'equal_length_hamming_count' | 'positional_disagreement_with_terminal_overhang'
cluster_method: 'average'
cut_criterion: 'cophenetic_distance'
cut_threshold: finite number >= 0
barcode_target_file: ArtifactFile(format='barcode_target_rows_v1') | null
```

The additive `encoding` field makes input decoding explicit; `fastq_sanger`
declares PHRED+33. No guessed encoding or extension-based dispatch.

Sample exact keys: `sample_key`, `input_file_key`, `condition_key`,
`biological_replicate_key`, `technical_replicate_key`, `dependence_group_key`,
`reference_library_key`. First two are nonempty strings; others nonempty
strings or null. Target row exact keys: `sample_key`, `barcode_sequence`,
`target_kind` (`gene|transcript|construct`), `target_key`,
`target_reference_release` (nonempty string or null), `mapping_source_ref`.
Mappings are exact; even duplicate mapping rows remain present and ambiguous.

Extraction common exact keys: `mode`, `orientation='as_read'`,
`case='sensitive'`, `match_policy='first'`,
`empty_match_policy='record_and_exclude'`.
For `mode='regex_search'` add exactly `pattern` (nonempty Python regex),
`flags` (unique list from `ASCII,MULTILINE,DOTALL,VERBOSE`),
`capture='whole_match'`. For `mode='literal_flanks'` add exactly
`flanking_seq_5prime` and `flanking_seq_3prime` (nonempty exact strings).
Literal extraction uses the first left flank having a following right flank;
the barcode starts after the left and ends before the first following right.

## Native artifacts and retained bytes

`ROLES` is the ordered tuple below. Every manifest contains one entry for each
role in that exact order; no other files can become scientific input implicitly.

| role | filename | format |
|---|---|---|
| input_reads | reads.bin | request.format |
| original_request | request.json | barcode_request_v1 |
| target_map | barcode_targets.json | barcode_target_rows_v1 |
| read_extractions | read_extractions.tsv | barcode_read_extractions_tsv_v1 |
| counts | barcode_counts.tsv | barcode_counts_tsv_v1 |
| population | barcode_population.json | barcode_population_v1 |
| distances | barcode_distances.tsv | barcode_distances_tsv_v1 |
| linkage | barcode_linkage.tsv | barcode_linkage_tsv_v1 |
| clusters | barcode_clusters.tsv | barcode_clusters_tsv_v1 |

`bundle.json` format `barcode_bundle_v1` is the manifest and does not hash itself.
Exact manifest keys:
`version='barcode_bundle_v1'`, `request_sha256=digest(request)`,
`input_sha256=request.reads.sha256`, `sample_key`, `attempt_key` (nonempty),
`writer_closed` (bool), `status` (`ok|partial|failed`), `stages`, `files`, `issues`.
`stages` has exactly `input,extract,count,distance,cluster`; each value is
`complete|prefix|failed|not_run|not_enough_barcodes`.
Each `files` row has exactly `role,filename,file`, where file is its ArtifactFile
or null for an artifact never produced. `target_map` is null iff request mapping
is null. Original input and request are exact retained bytes.
Target-map JSON is exactly `{version:'barcode_target_rows_v1',rows:[TargetRow...]}`.

`BarcodeRetainedFilesV1` exact keys:
`version='barcode_retained_files_v1'`, `attempt_key`, `writer_closed`,
`manifest={file:ArtifactFile(format='barcode_bundle_v1'),data:bytes}`,
`artifacts=[{role,file:ArtifactFile,data:bytes},...]`.
Only captured artifacts appear; manifest identity, complete length/hash, role,
attempt and writer closure are checked before admission. Capture cannot silently
admit stale files or replace producer hashes. No arbitrary directory is read.

TSV is UTF-8 with a mandatory exact header, tabs, LF/CRLF, standard CSV quoting
and no blank records. Nullable cells use the exact text `null`; boolean cells
are `true|false`. Unmatched barcode is null; an empty match is an empty string.
Columns, in exact order:

```
read_extractions:
record_ordinal read_id sample_key read_length status barcode_sequence start0 end0
counts:
sample_key barcode_sequence barcode_length read_count passes_min_count
distances:
sample_key i j barcode_i barcode_j shared_position_count terminal_overhang_count shared_mismatch_count distance_count distance_mode state
linkage:
merge_index left_node right_node distance leaf_count
clusters:
sample_key barcode_sequence read_count cluster_id
```

Read ordinals are contiguous 1-based occurrences; IDs may repeat. Extracted rows
have a nonempty barcode and exact half-open slice; unmatched rows have null
barcode/start/end; empty matches retain `''` and equal start/end. `state` for
distance is `available|invalid`; strict unequal-length Hamming has null
distance_count and `invalid` state, while all three positional counts remain.
Distance rows appear in lexicographic `(i,j)` condensed order (`i<j`) over the
declared distance population; exact barcode keys must match indices. Counts and
clusters may appear in any order and are joined by exact barcode/sample keys.
Counts are all prefilter strings, positive integer counts, exact lengths and
threshold booleans. No rounded frequency is authoritative. Cluster IDs are
positive integers with categorical meaning. Linkage leaf nodes are 0..K-1;
merge node K+merge_index; merge_index is contiguous 0-based; children must be
distinct currently active nodes; leaf_count is exact. Heights retain float repr.

Population JSON exact keys:
`version='barcode_population_v1'`, `request_sha256`, `input_sha256`, `sample_key`,
`extent='complete'|'prefix'`, `total_parsed_records`, `last_complete_ordinal`,
`extracted_records`, `unmatched_records`, `empty_match_records`,
`distinct_barcodes`, `retained_barcode_count`, `retained_read_count`,
`barcode_order` (all strings in first extracted-occurrence order),
`distance_population` (postfilter strings in that same order).
Read counts are counts of occurrences, never molecules. Extent qualifies every
denominator. Later distance/cluster failure must preserve valid count artifacts.

Issue exact keys: `code`, `stage`, `sample_key`, `barcode_key`, `record_ordinal`,
`artifact_ref`, `field`, `requirement`. Unused associations are null.
`issue(code, stage, *, sample_key=None, barcode_key=None, record_ordinal=None,
artifact_ref=None, field=None, requirement='none')` constructs a validated record.
Stage is `input|extract|count|distance|cluster|capture|join|projection`.
Required producer issue codes include `input_format_mismatch`, `malformed_fastq`,
`malformed_fasta`, `invalid_encoding`, `invalid_compression`,
`invalid_extraction_configuration`, `empty_barcode_match`,
`unequal_length_hamming`, `missing_distance_population`,
`distance_matrix_incomplete`, `invalid_linkage_membership`,
`resource_limit_exceeded`, `native_execution_failed`, `not_enough_barcodes`.
Requirement is `none|complete_read_population|native_distance_population|
native_linkage|sample_metadata|target_mapping|original_input|original_request|
closed_attempt|matching_artifact|corrected_input|valid_extraction|valid_native_output`.
Fields are closed in barcode_contracts.py; omitted/default null is valid.

## Numerical and result ports

Seven signatures from packet486 remain unchanged. Parse result exact keys:
`version='barcode_parse_result_v1'`, `status`, `request`, `manifest` (or null),
`population` (or null), `read_extractions`, `counts`, `distances`, `linkage`
(or null), `native_clusters`, `target_rows`, `issues`, `sources` (role/file rows).
Every valid table survives a later table failure. Sheet build exact keys:
`version='barcode_sheet_build_v1'`, `status`, `sheet`, `issues`.
Sheet exact keys: `version='barcode_sheet_v1'`, `status`, `request`, `sample`,
`population`, `read_extractions`, `counts`, `distances`, `linkage`,
`native_clusters`, `target_rows`, `issues`, `sources`.
Table dictionaries use the exact TSV column names with numerical values parsed.
Linkage exact keys: `version='barcode_linkage_v1'`, `barcode_keys`,
`distance_mode`, `method='average'`, `criterion='cophenetic_distance'`, `merges`.

Parameters exact keys: `version='barcode_calculation_parameters_v1'`,
`min_count`, `cluster_population` (ordered exact barcode strings),
`cut_threshold`, `target_aggregation='none'|'unique_mapping_only'`.
Requested cluster population must equal the recalculated threshold set; it can
reuse the saved tree only if exactly the original distance population. Otherwise
counts still calculate and clusters report `missing_distance_population`.

Projection request exact keys: `version='barcode_projection_request_v1'`,
`view='summary'|'barcodes'|'distances'|'clusters'|'targets'|'failures'`, `fields`,
`barcode_keys`, `cluster_ids`, `target_keys` (null or unique lists),
`top_k` (null or integer 1..1000), `include_sample` (bool).
The relevant key list or top_k is required for row views; selections are
validated and top-K sorts read_count descending with exact-key tie breaks.
Fields are fixed numerical field names for each view. Projections include
numerical value/state/units/denominator and population extent. Full data remain
in the sheet. No unrestricted findings or scientific-confidence field exists.

Legacy source exact keys: `version='barcode_legacy_source_v1'`, `file`,
`sample_key` (nullable), `min_count` (positive integer or null),
`total_records` (nonnegative integer or null), `extracted_records` (same),
`extent='unknown'|'prefix'|'complete'`. Known totals are explicitly supplied;
legacy TSVs cannot establish them. Count format is
`legacy_barcode_counts_tsv`; cluster format is `legacy_barcode_clusters_tsv`.
Legacy parsing retains original rounded frequencies and categorical `Lineage`
as `cluster_id` with the source identity, never inferred ancestry or a new tree.

Integration still needs B3 actual native outputs and B4 custody/publication.
These ports alone do not establish a complete scientific tool.

## Additive clarification, revision 2 (root review)

All exact target-map rows remain retained. Ambiguity and unique assignment use
the number of **distinct** explicit `(target_kind,target_key,target_reference_release)`
identities per sample/barcode, not the number of rows. Repeated representations
of the same exact identity neither create competing targets nor multiply reads.
Different reference releases remain distinct identities without inferred
equivalence. The earlier revision-1 statement that even duplicate rows are
ambiguous is superseded by this correction. `duplicate_target_mapping` may
qualify repeated representations while `ambiguous_target_mapping` denotes two
or more distinct identities.

The nullable text convention must preserve a literal sequence `null`.
`read_extractions.barcode_sequence` is decoded using `status`: `unmatched`
requires the null token and becomes Python null; `empty_match` requires the
empty string; `extracted` preserves exact nonempty text, including `null`.
Count, pair, cluster and mapping barcode fields are always literal strings.
Nullable numeric start/end/distance fields still use the null token directly.
Non-nucleotide symbols remain literal, with explicit qualification.

## Additive clarification, revision 3 (failed input custody)

The request retains the exact expected input and optional target-map identity.
A manifest `input_reads.file` or requested `target_map.file` may be null when
staging/input failed, provided status is partial/failed and an explicit
`missing_artifact` issue locates `field='reads'` or `field='target_rows'` (also
`barcode_target_file` for mapping), at stage input/capture/join. A null request
mapping still forbids an unrequested native target-map file. No identity or
captured bytes are fabricated. The revision-1 iff rule is superseded for failed
input custody. A parser cannot validate count-to-original-read associations
until the original read bytes become available.

## Calculator and projection record detail

`BarcodeComponentsV1` exact keys are `version='barcode_components_v1'`,
`status`, `sheet_sha256`, `parameters`, `sample_key`, `extent`, `summary`,
`barcodes`, `distances`, `clusters`, `targets`, `issues`. Summary is a fixed
field-to-measurement mapping; complete field sets are exported as
`SUMMARY_FIELDS`, `BARCODE_FIELDS`, `DISTANCE_FIELDS`, `CLUSTER_FIELDS`,
`TARGET_NUMERIC_FIELDS`, and `VIEW_FIELDS` in barcode_contracts.py.
Each measurement has exactly `value`, `state`, `units`, `denominator`,
`population`, `extent`, `source`, `uncertainty`. Source is observed/derived;
uncertainty is null because this method supplies no biological uncertainty.
Available/prefix cells retain full integer or floating precision. Other states
hold null. Every ratio retains the exact denominator and population.

Barcode component rows have `sample_key,barcode_sequence,retained,measurements`;
distance rows `sample_key,i,j,barcode_i,barcode_j,measurements`; cluster rows
`sample_key,cluster_id,barcode_keys,measurements`; target rows
`sample_key,target_kind,target_key,target_reference_release,barcode_keys,measurements`.
Target counts cover all prefilter extracted counts. A requested mapping that
was not captured remains missing, rather than claiming all reads unmapped.

Projection exact keys are `version='barcode_projection_v1'`, `status`,
`sheet_sha256`, `components_sha256`, `request`, `sample` (null unless requested),
`sample_key`, `extent`, `total_available_rows`, `selected_row_count`,
`returned_row_count`, `has_more`, `rows`, `issues`. It selects numerical fields
from the component rows and validates them against the saved sheet and explicit
parameters. Summary is one sample/measurements row; failures are issue rows.
Distance rows have no read-count abundance, so their optional bounded top-K
window uses declared `(i,j)` order; abundance rows use descending read counts
and exact-key ties. This clarifies the earlier general abundance-sorting sentence.

## Additive clarification, revision 4 (saved stage outcomes and decoding)

`BarcodeSheetV1` additionally retains `manifest` (the validated original native
manifest, or null for invalid/missing manifest). This preserves actual per-stage
outcomes alongside saved tables; a failed cluster stage and a stage never run
remain distinguishable after original native execution is unavailable.

`BarcodeTextLines(binary, *, encoding)` in barcode_formats.py is a shared finite
strict line reader for Biopython SeqIO. It accepts LF/CRLF/CR and implements
read(0), readline, iteration, seek and close. Unlike TextIOWrapper read-ahead, a
later invalid encoded line cannot erase earlier already emitted records. It
never infers records the selected native parser did not emit. Producer and
validator use the same decoding semantics; extraction and calculation ports
and file formats do not change.

## Validator precision, revision 5

Python regex inline flags cannot override the declared case-sensitive mode.
Global or nested/scoped IGNORECASE is rejected; Python rejects LOCALE in string
patterns. Named supported flags and literal symbols retain their declared
meaning. Native cluster IDs remain unchanged in `sheet.native_clusters`;
calculated saved-tree cuts use derived categorical IDs ordered by minimum leaf
ordinal, as stated by `recut_barcode_linkage`.

Input/extract/count stages allow complete/prefix/failed/not_run;
distance/cluster stages allow complete/failed/not_run/not_enough_barcodes.
Manifest status ok requires complete input/extract/count and complete or
not_enough_barcodes for the later stages. These checks reject inconsistent
records; they do not select or rerun work.
