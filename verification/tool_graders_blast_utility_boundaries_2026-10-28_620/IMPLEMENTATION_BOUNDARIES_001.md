# Remaining R7 utility boundaries — implementation proposal 620/001

This is additive implementation evidence for the ten named utilities below. It
does not change the supplied goal, complete an inventory row, authorize a native
workload, or define an episode prompt. No production implementation is included.
The original user attachment was read in full. Its objective and all ten
operating principles were reread verbatim after each tool's examination and
again after additional native-source examination. GOAL.md was not read.

## 1. Established availability and coverage

All ten executable files are present under
`resources/software/ncbi-blast-2.17.0+/bin`. Under the existing 529 runner,
`check079_blast_utility_help` executed exactly `-help` and `-version` for each.
All 20 commands returned zero; one capture test passed in 0.61 seconds. Every
program reports package BLAST 2.17.0, build July 1, 2025. `makembindex` reports
its program version without the trailing `+`. This establishes native CLI
availability, not database preparation, conversion, extraction, integrity,
episode integration, or a remote deployment.

The collected receipt is terminal and quiescent, return code zero, with unchanged
source, dependency, standard-library, binary and native-library pins. The actual
limits were 20 GiB RAM, 4 GiB scratch, zero swap and no wall cap. Observed scratch
was 878,411,776 bytes. Retained stdout/stderr, exact argv, identities and receipts
are in `retained_native_help/` and `runner_evidence/`. No database bytes were read,
no BLAST search ran, and no API/HPC/authentication operation was attempted.
Public source/document retrieval was limited to NCBI documentation and its
official GitHub source; it was not a molecular-data/service acquisition.

The fixed rows in `research/tool_grader_inventory_2026-10-24/WORK_STATUS.json`
remain pending for all ten. Source/catalog occurrences do not establish bound
operations. Current package/library searches and retained 572 evidence establish
these reusable paths and specific gaps:

| Utility | Existing reuse | Missing public boundary |
| --- | --- | --- |
| blast_formatter | Existing BLAST report readers and scientific sheets/calculators | Archive conversion invocation/custody and typed requested return |
| blast_formatter_vdb | Same report readers; existing VDB dataset/metadata contracts | VDB archive conversion with actual offline subject context and requested return |
| blast_vdb_cmd | `blast_vdb_inputs.parse_blast_vdb_member_sequences`; existing VDB metadata consumer | Authentic helper invocation, retained native helper output and standalone requested return |
| blastdb_aliastool | Practical command/receipt machinery | Alias/list mode contracts, dependencies and validated artifacts |
| blastdbcheck | Practical execution and typed outcome machinery | Actual native check scope/diagnostic parser and requested qualified validation return |
| blastdbcmd | Supplied FASTA parsing and sequence identity mechanisms | Selected database/entry/range/format bindings and native inspection/extraction returns |
| convert2blastmask | Raw-sequence masking sheet/calculator and sequence parsers | Mask conversion reader, identity-preserving association and prepared-mask return |
| makeblastdb | Existing standard/additional prepared-database manifest validators | Producer of actual database files, preparation receipt and usable manifest |
| makembindex | Practical execution/artifact mechanisms | Index family producer, database-volume relationship and qualified index return |
| makeprofiledb | Existing RPS/DELTA manifests; scoremat parser and PSSM calculators | Actual profile-database preparation, per-input disposition and usable manifest |

The existing VDB four-column parser has retained 312/check_007 component evidence
(66 tests, zero failures/errors/skips); this task did not rerun it. Its current
contract is exact `%i\t%a\t%l\t%s`, explicitly selected entries, dataset snapshot,
filtered-read/reference choices, return code and producer completion. It rejects
`entry=all`. Keep that proven port. Native help shows additional VDB modes; it
does not make those modes covered by this parser.

## 2. Actual analysis relationships and shared ownership

These utilities perform supporting transformations and inspections. Their common
authority is typed artifacts and deterministic validation. They get no annotation
confidence, function probability, synthetic scientific score or new yield scale.

1. **Report conversion:** both formatters populate one `BlastReportConversion`
   contract. Compatible report formats go through the existing BLAST readers.
   Any later scientific calculation uses the original analysis-specific sheet;
   conversion is not a new independent BLAST observation.
2. **Sequence acquisition from a prepared database:** `blastdbcmd` and
   `blast_vdb_cmd` use one `SequenceExtraction` contract and common length,
   identity, selection and completeness validators. Their native parsers and
   operand metadata differ. VDB-specific associations remain explicit fields.
3. **Database artifact construction/inspection:** `makeblastdb`,
   `makeprofiledb`, `makembindex`, aliases and database-info modes share one
   `DatabaseArtifactSet` custody/dependency contract. A discriminated detail
   record retains sequence database, profile database, index, alias and ID-list
   meanings. Shared structure does not erase their different native formats.
4. **Native validation:** `blastdbcheck` and deterministic artifact checks use
   one `ValidationObservation` shape. Native sampled/full checks, file custody,
   syntax validation and extraction agreement remain different check kinds.
   A count of passed checks is not an integrity probability.
5. **Mask conversion:** `convert2blastmask` must feed the existing
   `SequenceMaskingSheet` / `calculate_sequence_masking_components`, with an
   additive conversion operation variant and a format-specific maskinfo reader.
   Do not copy its union, count or fraction calculation. Do not pretend the
   conversion executable ran DUST/SEG/WindowMasker. The declared upstream
   algorithm/options are retained provenance, not an authenticated masking run.

The masking core currently restricts `program` to three masking executables and
derives molecule from that name. An exclusive later core owner must add an
explicit conversion/molecule variant preserving existing variants and saved
recalculation. This plan does not edit those files while root integrates them.

## 3. Shared typed records and numerical meanings

The following are proposed closed records. Nullable fields are present with
`null` and a reason; absence is not zero. No raw exception or unrestricted
findings prose crosses the requested-return boundary. Native text remains in
retained artifacts. Internal IDs, hashes, host paths and tracking stay outside
model-facing TASK/STEERING.

```text
ArtifactOccurrence = {
  occurrence_id, direction: input|output, role, ordinal >= 0,
  artifact_ref, sha256, size_bytes >= 0, native_format,
  completeness: complete|partial|unknown
}
NativeOutcome = {
  started: bool, returncode: int?,
  state: succeeded|failed|incomplete|unknown,
  writer_closed: bool, inventory_complete: bool
}
NativeField = {
  field_name: declared field enum, value: declared scalar/list type,
  native_lexeme: string?, occurrence_id, locator,
  meaning: declared meaning enum, unit: declared unit enum,
  population_ref: string?, missing_reason: closed code?
}
ValidationObservation = {
  check_id, kind: custody|syntax|identity|selection|native_integrity|native_compatibility,
  status: pass|fail|unknown|not_applicable,
  subject_refs: list[declared refs], method: closed method enum,
  population_ref: string?, native_fields: list[NativeField],
  reason: closed code?, evidence_refs: list[artifact/record refs]
}
UtilityFailure = {
  stage: request|input|native|capture|parse|association|validation|projection,
  code: closed code, occurrence_id: string?, record_key: string?,
  native_returncode: int?, diagnostic_artifact_ref: string?
}
UtilityResult = {
  schema: blast_utility_result_v1, program, mode,
  operation_ref, original_outcome: NativeOutcome,
  artifacts: list[ArtifactOccurrence],
  payload_kind: report_conversion|sequence_extraction|database_artifacts|integrity|mask_conversion,
  payload: corresponding closed record,
  checks: list[ValidationObservation], failures: list[UtilityFailure],
  status: complete|partial|failed|unavailable
}
```

The occurrence role enum is `archive`, `sequence_input`, `extracted_sequences`,
`database_manifest`, `database_file`, `database_metadata`, `profile_list`,
`profile_input`, `mask_input`, `mask_output`, `identifier_list`, `alias_file`,
`index_file`, `stdout`, `stderr`, `diagnostics`, `offline_configuration`.
Native-field names are selected by payload, not arbitrary new measurements:
`database_title`, `database_format_version`, `database_created_at_native`,
`database_sequence_count`, `database_residue_count`, `database_bytes`,
`database_file_names`, `database_volume_names`, `database_mask_algorithms`,
`sequence_id`, `accession`, `oid`, `sequence_length`, `sequence_hash_native`,
`taxid`, `leaf_taxids`, `taxonomy_names_native`, `membership_integer`, `pig`,
`profile_count`, `checked_sequence_count`, `checked_oid`, `index_oid_start`,
`index_oid_stop`, `identifier_count`, `mask_algorithm_id`, `mask_algorithm_program`,
`mask_algorithm_options`, `mask_list_more`. Each mode declares the supported
subset, the exact native locator and its scalar/list type. Unrecognized metadata
remains in the retained raw artifact, never squeezed into a recognized field.

Validation method enums are `identity_digest`, `family_inventory`,
`native_format_parser`, `explicit_reference_join`, `selected_record_match`,
`sequence_length_agreement`, `mask_interval_bounds`, `native_full_check`,
`native_sample_check`, `native_compatibility_check`. The corresponding subject
references and evidence must agree with the actual method. A source parser alone
cannot claim a native compatibility check.

Use the existing finite-JSON and reference validators, rejecting bool-as-int,
NaN/infinity, duplicate occurrence identities, unselected operands, path escape
and incompatible fields. Same artifact bytes can occur in different roles;
content identity does not replace occurrence identity.

Numerical fields are deliberately small and factual:

| Field | Exact source/calculation | Unit/population and missing behavior |
| --- | --- | --- |
| `size_bytes` | Retained file's measured byte count | Bytes for that file; not sequence length |
| `returned_symbol_count` | Length of the parsed ungapped returned sequence | nt or aa for this exact returned record; null if sequence unavailable/invalid |
| `native_reported_length` | Exact `%l` or native metadata value | Preserve the native length meaning; full sequence vs extracted fragment must be established for the chosen mode, never guessed |
| `input_record_count` | Number of complete parsed input occurrences | Records in the selected artifact; malformed/unread records remain failures |
| `returned_record_count` | Number of parsed complete native record occurrences | Returned population, including distinct duplicate occurrences; not full database size |
| `requested_entry_count` | Length of the explicitly retained selector occurrence list | Requests, not unique hits; duplicates remain requests |
| `native_database_sequence_count` | Exact native `-info`/metadata field or explicit native generation receipt | Native database or alias population identified by that observation; not function prevalence |
| `native_database_residue_count` | Exact native metadata field | nt/aa with exact-vs-approximate basis retained; never inferred from file size |
| `native_profile_count` | Reported count with source locator | Profiles included in that database when native scope proves it; not submitted SMP-list length by assumption |
| `native_checked_sequence_count` | Native diagnostic value only | Actual checked population; selected random/stride/end count does not prove this number |
| `masked_positions`, `masked_fraction` | Existing masking calculator, after valid record association | Union cardinality / same supplied sequence length; no probability interpretation |

No new ratio calculator is needed for ID-list, database, archive, integrity or
index operations. Future requested ratios must name a real denominator and use
the existing shared numerical authority. Native uncertainties are retained if
provided; these utilities do not supply a confidence interval by default.

Numeric option meanings also remain native: `nmer` is word length in nucleotide
symbols, `stride` is the distance between stored nucleotide positions,
`word_size_hint` is expected search word length, `volume_size_mb` is the native
MB target, `max_smp_per_volume` is a profile-file count, `threshold` is the
native lookup-table word score, `scale` is the native PSSM score scale, and
gap-open/extend values are native score penalties. DELTA `observation_threshold`
concerns native independent-observation support for retaining a domain. Requested
options are parameters, not newly observed measurements, statistical uncertainty,
or function-confidence components.

## 4. Exact mode and artifact boundaries

### 4.1 blast_formatter and blast_formatter_vdb

Proposed first mode: `format_archive`. Input is one retained ASN.1 BLAST archive
(outfmt 11), not a ZIP file, plus the original search descriptor and any subject
context the actual formatter needs. Retain original program, search mode,
query/round identities, database or pairwise-subject identities, native result
provenance and reporting limits. A formatted program name cannot replace those
identities. `blast_formatter_vdb` uses the same conversion record and carries the
original VDB dataset snapshot/offline configuration instead of a new score.

`BlastReportConversion` fields:

```text
archive_occurrence_id, original_search_ref,
original_program, original_mode, original_query_refs, original_dataset_refs,
context_bindings: list[{role, supplied_occurrence_id, original_operand_ref}],
requested_format_code, declared_fields, delimiter,
formatting_options: {max_target_seqs?, num_descriptions?, num_alignments?,
                    show_gis, parse_deflines, html, line_length?, sorthits?, sorthsps?},
output_occurrence_ids, output_relationships: list[{parent_file, child_file, native_link}],
parser: json2|declared_tabular|unavailable,
parsed_report_ref?, original_to_output_record_bindings,
coverage: complete_archive|selected_reports|unknown,
checks, failures
```

For the first semantic binding, select single-file JSON15 or declared tabular6/7.
These reuse `blast_grading_inputs.parse_blast_json` /
`parse_blast_tabular`; a utility adapter retains parse results and issues rather
than recalculating identity/coverage or probabilities. Existing collection and
program/round selectors remain authoritative for multi-query/iterative work.
The formatter output limit and archive completeness remain separate facts.

Other native output formats, including XML, ASN.1 Seq-align, JSON Seq-align,
multiple-file JSON/XML, SAM, HTML and organism reports, remain named native
capabilities until their actual output family and validation port are bound.
They are not silently fed into the existing JSON2 parser. If a future raw-format
binding is offered, it can truthfully return preserved opaque bytes and
`semantic_validation=unavailable`; it cannot claim report decoding.

The source loads subjects/database context when formatting; an archive is not
assumed self-contained. A missing context returns `subject_context_unavailable`,
preserves any partial output and makes no network fallback. `-rid` is a distinct
remote retrieval mode, mutually exclusive with `-archive`; it is not part of the
first offline binding and requires an explicitly configured service path.

### 4.2 blastdbcmd and blast_vdb_cmd

`SequenceExtraction` fields:

```text
database_binding, selector_occurrences,
selection: {kind: specific_entries|all_entries|taxids|ipg|references,
            target_only?, get_dups?, taxid_expansion?, include_filtered_reads?,
            reference_selection?},
requested_outfmt, declared_fields,
records: list[{
  record_key, output_occurrence_id, native_row_ordinal, native_locator,
  matched_selector_ordinals, association: exact|explicit|unresolved,
  native_identifiers: list[{namespace, value, version?}], native_oid?, native_title?,
  original_sequence_ref?, molecule: dna|rna|protein|unknown,
  native_reported_length?, native_length_basis: full_sequence|returned_sequence|unknown,
  returned_sequence?, normalized_sequence?, returned_symbol_count?,
  range: {requested_start_1based?, requested_stop_1based?,
          effective_start_0based?, effective_end_exclusive?, strand?},
  native_taxonomy_fields, native_mask_fields,
  completeness: complete|partial|unknown, native_parser_record_ref?, checks, failures
}],
missing_selector_ordinals, unexpected_records,
population_completeness: complete_selection|partial_selection|unknown,
native_parser_payload_ref?, checks, failures
```

First standard extraction: specific entries from an explicitly selected prepared
database with fixed tabular fields `%o\t%i\t%a\t%l\t%s`, plus FASTA when
explicit occurrence bindings are supplied. Do not let native `-db nr` default
choose a database. First VDB extraction uses the existing exact four-column
parser with the original `extraction_context`; translate its retained records
into the same extraction record, preserving the original parser result. Do not
generalize that parser to `all`, reference dumping, or arbitrary columns by
silently changing its established input contract.

Range requests are native one-based inclusive; normalized coordinates are
zero-based half-open relative to the original sequence. Native `%l`, returned
symbol count and requested/effective endpoints remain distinct. A range past
the end, reverse strand, missing member, duplicate ID or multiple definition
lines needs its own authentic oracle before that mode is advertised. Never
associate independently sorted sequences and IDs or silently select the first
duplicate accession. Native IDs such as `gnl|SRR|...` and `gnl|SRA|...` are
retained literally; only demonstrated exact aliases join.

Inspection modes use `DatabaseInspection`, not this extraction record:

```text
mode: info|metadata|tax_info|list|paths|paths_all|show_search_path|show_filters,
database_bindings, native_metadata_occurrence,
native_fields: list[NativeField], databases_or_paths: list[exact typed rows],
mask_algorithms: list[{native_algorithm_id, native_name, native_options, source}],
scope: selected_database|selected_directory|selected_vdb_closure,
completeness, checks, failures
```

`blastdbcmd -metadata` native JSON is a different schema from the repository's
prepared database manifest. Parse and retain the native document; project only
validated facts into the shared artifact descriptor. `-info -exact_length`
establishes a different length measurement from a possibly approximate native
total. `%h` is the native sequence hash, not a repository SHA256. Taxonomy name
arrays are not zipped into accession associations. Directory/list output is a
selected discovery result, not a deployment or completeness claim outside that
directory. No inspection parser enumerates files or opens a database itself.

### 4.3 makeblastdb, makeprofiledb, makembindex and blastdb_aliastool

All use `DatabaseArtifactSet`:

```text
kind: sequence_database|profile_database|megablast_index|database_alias|identifier_list,
logical_identity: {namespace, value, version?, release?, scope?},
native_prefixes, molecule: dna|protein|unknown,
producer: {program, mode, software_ref, original_operation_ref},
input_occurrence_ids, output_occurrence_ids,
dependencies: list[{dependency_key, kind, identity, occurrence_ids,
                    native_reference, resolution_basis: explicit|native_recorded}],
inventory_complete: bool,
native_metadata: list[NativeField], detail: kind-specific record,
usable_prepared_manifest_ref?, compatibility: validated|unverified|incompatible,
checks, failures
```

Every file family is inventoried in the original fresh attempt directory after
writer closure. Keep all native components, volumes, metadata and selected
sidecars; three traditional extensions alone do not define a complete v5
database. Do not include unrelated pre-existing files in a new output family.
No pure parser resolves a path by inspecting today's filesystem. Alias/database
dependencies must be supplied as typed original identities and file occurrences.

**makeblastdb / create_sequence_database.** First bind explicit plain FASTA,
`dbtype`, output prefix, `blastdb_version` 4 or 5, title, `parse_seqids`,
`hash_index`, optional taxid or taxid-map artifact, maximum file size and explicit
mask artifacts. Preserve requested taxonomy associations and native outcomes;
the taxonomy map is not functional annotation. A mask file must bind by exact
sequence identifiers and recorded algorithm metadata. Keep native assigned mask
IDs separate from convert2blastmask's input algorithm ID. Further native input
types `asn1_txt`, `asn1_bin`, `blastdb` stay explicitly unbound pending readers.

Detail fields: `input_type`, `dbtype`, `database_format_version`,
`parse_seqids`, `hash_index`, `max_file_size_requested`, `taxid_binding`,
`mask_bindings`, `native_metadata_ref`, `native_counts`. The producer supplies
the existing standard prepared-database manifest shape, and for protein consumers
the existing additional-database shape, by projection from this one artifact set.
Reuse the existing `_database` relationship validators and schema definitions;
an export wrapper can expose them without copying the validators or creating a
fictional BLAST-search job. Existing search calculators are not changed.

**makeprofiledb / create_profile_database.** Explicitly retain the ordered list
artifact and every referenced SMP/PssmWithParameters artifact with identity,
ordinal and text/binary format. Never pass a list file whose dependencies are
unretained arbitrary paths. First scientific-consumer bindings are `rps` and
`delta`, using their existing preparation types and prepared manifests. Native
`cobalt` is a separate profile preparation type; it cannot be mislabeled RPS
or silently accepted by the current search manifest validator.

Detail fields: `profile_type: rps|delta|cobalt`, `scoremat_format`,
`profile_inputs: [{list_ordinal, input_occurrence_id, native_model_ids,
                   pssm_sheet_ref?, disposition: included|excluded|unknown,
                   reason?, native_evidence_refs}]`,
`threshold`, `force_threshold`, `create_index`, `database_format_version`,
`max_smp_per_volume`, `gapopen`, `gapextend`, `scale`, `matrix`,
`observation_threshold`, `exclude_invalid`, `taxid_binding`, `native_counts`.
Keep requested parameters and native effective values separate: scoring options
may be ignored when input PSSMs already contain scores. DELTA filtering can
exclude models; do not infer every SMP was included from a zero exit code.
Reuse `read_blast_pssm(..., format="scoremat_asn_text", ...)` and
`calculate_blast_pssm_components` for supported retained text measurements.
Binary input is not established as parsed by that reader. The preparation result
does not produce independent profile-scoring mathematics.

**makembindex / create_index.** `old_style_index` and `legacy` are distinct
booleans. Modern/new-style indexes require `iformat=blastdb`, enumerate database
volumes, write `.idx` volumes and `.shd` beside each source volume, and ignore
`-output`. Therefore stage the explicitly selected database closure into a new
attempt-owned writable location; never build into the caller's immutable
database or infer that `-output` confines writes. Record original-to-staged
volume identities. Old-style FASTA input remains a separate declared mode.

Detail fields: `old_style_index`, `legacy_offset_format`, `input_format`,
`database_volume_bindings`, `selected_mask_algorithm`, `idmap`, `nmer`, `stride`,
`word_size_hint`, `volume_size_mb`, `native_effective_options`,
`index_volume_bindings: [{database_volume_ref, output_occurrence_ids,
                        native_oid_start?, native_oid_stop_exclusive?}]`.
Keep ignored/clamped options and warnings. The retained source explicitly warns
that stride/word-size hint have no effect under legacy format and clamps too-low
word-size hint in the other mode. A present index is not proof that a search
used it. Search-based usability verification remains a configured remote task.

**blastdb_aliastool.** Keep these separate modes in one invocation contract:
`convert_gi_list`, `convert_seqid_list`, `inspect_seqid_list`,
`create_subset_alias`, `aggregate_databases`, `aggregate_vdb`,
`aggregate_volumes`. The first three concern identifier-list artifacts; the
others create virtual database dependency graphs, not independent sequences.
Retain raw input-list order/duplicates plus the actual native converted artifact;
do not guess how native sorting/deduplication changes count semantics.

Detail fields: `alias_molecule`, `alias_title`, `database_dependencies`,
`restriction: none|gi_list|seqid_list|taxid_list|oid_mask`,
`restriction_occurrence_id?`, `oid_mask_bits?`, `declared_volume_count?`,
`native_alias_fields`, `identifier_list_kind: gi|seqid|null`,
`identifier_list_info`, `native_counts`. Resolve DBLIST/VDBLIST and list-file
references only against explicitly supplied dependency identities. The native
help says aggregate molecule matching is not validated by the native tool;
our typed inputs must preserve and validate the declared molecule relationship.
An alias is usable only with its retained/referenced database closure. Do not
count alias members as independent biology or infer full membership from title.

### 4.4 blastdbcheck

Input is an explicit selected database manifest, not implicit current directory.
First bind one database. Directory/recursive checking is a separate scope with
an explicit discovered database population. Retain full stdout/stderr and exit
state. Select checks explicitly; no automatic additional native invocation is
hidden in a result parser or database builder.

`DatabaseIntegrity` fields:

```text
database_bindings,
methods: {full, stride?, random_count?, ends_count?, no_isam,
          legacy_file_checks, require_taxids, cdd_delta},
sampling: {requested_method, requested_count?, native_sampled_oids?,
           observed_checked_count?, population_count?, realized_seed?},
native_diagnostics: list[{locator, category, database_ref?, native_oid?,
                         status: pass|fail|unknown, native_fields}],
scope: all_sequences|selected_sample|unknown,
native_returncode, checks, failures
```

`full` is incompatible with stride/random/ends. Preserve combinations the native
CLI permits without inventing a cadence or sample policy. When sampled OIDs,
seed or actual checked count are absent, leave them unknown. A sampled pass is
not a full-database pass. Nonzero exit from missing files, invalid arguments or
unreadable resources is an execution/availability failure, not automatically a
scientific finding of corrupt sequences. Unknown diagnostics remain retained
native data with unsupported-parser qualification.

### 4.5 convert2blastmask

First identity-preserving mode: `convert_mask`, supplied lowercase FASTA with
explicit molecule, `parse_seqids`, declared upstream masking algorithm/options,
and `maskinfo_xml` or `maskinfo_asn1_text`. Add a new native-format reader into
the existing mask sheet. Retain complete maskinfo root, native algorithm ID,
algorithm program code, options, all Seq-id alternatives, packed interval
endpoints, native mask-list ordering and `more` flags. Native endpoints are
zero-based inclusive; convert once to half-open coordinates.

Important differences from the three masking executables:

* Conversion extracts the input lowercase mask; it does not run a complexity
  detector or discard input lowercase.
* Native source only emits masked records. Empty output/mask list must be
  interpreted against the complete supplied input and successful original
  conversion, never by assuming one output block per input.
* Its `interval` writer emits bare intervals without headers. Multi-record
  interval output cannot establish occurrence association. Restrict an initial
  interval binding to one explicitly bound input record, or return unresolved
  records; do not borrow the masker native-order mapping.
* Source also accepts header-plus-interval input by creating dummy internal
  sequence symbols. Those symbols are not measured sequence or a valid length
  denominator. Keep that input mode unbound until the caller supplies exact
  source-sequence associations/lengths; never publish the dummy length.
* The native writer is given algorithm ID zero. A later makeblastdb can assign
  database mask IDs; preserve both identities and the conversion relationship.

`MaskConversion` contains `input_mask_basis: lowercase_input|supplied_intervals`,
`declared_upstream_algorithm`, `declared_upstream_options`,
`upstream_mask_result_ref?`, `native_maskinfo_ref`, `record_bindings`,
`sequence_masking_sheet_ref`, `sequence_masking_components_ref`, checks/failures.
Only exact associated complete records receive existing extent/fraction values.
For an illustrative supplied sequence `AAaaNNtt` (8 nt), lowercase positions
give intervals `[2,4)` and `[6,8)`, count 4 and fraction 4/8. This is a contract
example, not a native result and not a function-confidence score.

## 5. Pure functions, producer port and requested returns

Proposed callable ports, with one owner for each file listed in section 7:

```python
# blast_utility_contracts.py — pure closed records, no IO
validate_blast_utility_record(kind: str, value: dict) -> dict
validate_blast_utility_operation(value: dict) -> dict
validate_blast_utility_result(value: dict) -> dict

# blast_report_conversion.py — parser routing, no numerical implementation
parse_blast_report_conversion(content: bytes, *, occurrence: dict,
    operation: dict, original_search: dict, custody: dict) -> dict
validate_report_conversion_relationships(result: dict) -> list[dict]

# blast_database_extraction.py
parse_blastdbcmd_sequences(content: bytes, *, occurrence: dict,
    operation: dict, database_binding: dict, custody: dict) -> dict
adapt_blast_vdb_extraction(parsed: dict, *, occurrence: dict,
    operation: dict, database_binding: dict) -> dict
validate_sequence_extraction(result: dict) -> list[dict]

# blast_database_inspection.py
parse_blast_database_inspection(content: bytes, *, occurrence: dict,
    program: str, mode: str, native_version: str, selection: dict) -> dict
parse_blastdbcheck_diagnostics(stdout: bytes, stderr: bytes, *,
    occurrences: list[dict], operation: dict, outcome: dict) -> dict

# blast_database_preparation.py
populate_database_artifact_set(*, operation: dict, inputs: list[dict],
    outputs: list[dict], dependency_bindings: list[dict],
    native_metadata: list[dict], outcome: dict) -> dict
parse_blast_alias(content: bytes, *, occurrence: dict,
    declared_dependencies: list[dict], operation: dict) -> dict
validate_database_artifact_relationships(record: dict) -> list[dict]
project_prepared_blast_database(record: dict, *, contract: str) -> dict
# contract names existing standard/additional manifest schemas; unknown
# kind/format or incomplete inventory returns unavailable with a reason.

# blast_maskinfo_inputs.py — into the EXISTING mask sheet
parse_blast_maskinfo(content: bytes, *, occurrence: dict, native_format: str,
    input_records: list[dict], record_bindings: list[dict], custody: dict) -> dict
populate_mask_conversion(*, operation: dict, input_records: list[dict],
    parsed_maskinfo: dict, outcome: dict) -> dict
# calculate_sequence_masking_components(sheet) remains numerical authority.

# native_blast_utility_contracts.py
validate_native_blast_utility_job(value: dict) -> dict
compile_native_blast_utility_job(job: dict, *, input_paths: dict,
    database_paths: dict, output_directory: str) -> list[str]
requested_job_from_native_blast_utility(job: dict) -> dict
validate_native_blast_utility_requested_job(value: dict) -> dict
validate_native_blast_utility_bundle(value: dict, original_plan: dict) -> dict

# native_blast_utility_tool_info.py
validate_native_blast_utility_bindings(rows: list[dict]) -> list[dict]
native_blast_utility_tool_contracts(bindings: list[dict], *,
    resource_kind: str, resource_id: str) -> list[dict]

# local reservation and retained capture, same concrete practical ports
prepare_local_blast_utility(state, operation_key, *, root, policy)
local_blast_utility_plan(assignment: dict, execution_id: str) -> dict
capture_local_utility_bundle(store, *, target: dict, directory) -> dict
# remote capture consumes the existing selected reader/witness transport
capture_remote_utility_bundle(store, *, target: dict, reader,
    operation_key: str, directory) -> dict

# native_blast_utility_result_worker.py
run(plan: dict) -> dict
# exactly one selected saved-data stage: parse_validate or project_saved

# blast_utility_result_views.py
validate_blast_utility_selector(value: dict, *, operation: dict) -> dict
project_blast_utility_result(result: dict, *, source_ref: str,
    selector: dict) -> dict
```

One job is one selected native invocation. Its closed request contains program,
mode, actual configured executable identity, environment, typed operation,
input occurrences, database operands/dependencies and explicit output selections.
Compiler output is argv, never shell text. It does not search PATH, choose a
database, choose a resource, generate missing masks/PSSMs, retry, or invoke a
second utility for validation. Effective native defaults are not fabricated as
observed parameter values.

The sealed bundle retains original run/episode/resource/operation/attempt/native
handle identity; requested job; staged/final input identities; executable identity;
argv/environment; native start/finish/outcome; all output family members; full
logs; dependency closure; and specific failures. Acquisition validates that
bundle against the original target/attempt before retaining bytes. A checksum
match alone does not grant cross-episode access. Host/result manifests must bind
the current parent request to the exact original receipts, as in the existing
masking/BLAST acquisition and `EpisodeReturnRecords` machinery.

Proposed requested sources are `execution.utility_status`,
`execution.utility_artifacts`, `execution.utility_sequences`,
`execution.utility_database_facts`, `execution.utility_checks`,
`execution.utility_failures`, and existing masking quantities when requested.
Each has closed field/enum meanings. No generic unrestricted result JSON is a
parent return. Publication and child return project saved calculated/validated
fields; they do not independently count masks, recompute alignment percentages,
re-read current databases, reformat native work or obtain new metadata.

## 6. Consumers, ownership and failure path

Concrete integration consumers to inspect in full before coding their edits:

* `scientific_tool_library.py`, `scientific_tool_retrieval.py` and
  `ExecutionEpisodes` tool-contract construction: expose only configured native
  utility bindings, route selected work to ordinary launch/resource children,
  and preserve the scientific three-slot selection.
* `practical_execution_records.py` requested-job union and assignment validator;
  `practical_service_setup.py` resource reconstruction; configuration and native
  reservation/start/status/collect in `practical_execution_operations.py`.
  HPC adds its corresponding explicit `practical_pbs_operations.py` preparation
  path only when a resource and workspace are actually configured.
* `execution_progress.py`: original receipt ancestry, native output descriptors,
  selected log windows and acquisition capabilities. Utility label/exit status
  alone must not manufacture progress information.
* `execution_episodes.py`: selector qualification, result execute/resolve/facts,
  original-target access, received report admission, typed received facts,
  operational credit and practical completion proof.
* `episode_return_records.py` plus utility result/return binding: immediate-child
  provenance and exact requested subsets, durable replay and closed delivery.
* Existing prepared-database consumers in
  `native_blast_standard_database_contracts/driver/acquisition/metadata.py` and
  `native_blast_database_contracts/driver/acquisition/metadata.py` consume the
  projected existing manifests. Existing scientific calculators stay unchanged.
  Formatter output routes by original analysis into existing BLAST parsers and
  their established result paths; VDB extracted members reach the existing
  `native_blast_database_metadata` VDB input binder.

State sequence is selected operation -> immutable intent -> actual native
outcome -> sealed original artifacts -> qualified capture -> parser/validator
or shared masking calculator -> immutable projection -> original requested
typed return. Infrastructure makes no episode-owned choice along this path.

Malformed caller/schema arguments fail before execution and add no completed
own-action observation. An executed native nonzero command retains its outcome
and partial artifacts. Truncated output, malformed rows, missing dependencies,
unresolved IDs, unavailable parser, unsupported native format, mismatched original
attempt and output inventory gaps have separate codes. Preserve valid complete
records independently of the overall execution state; do not promote them to a
complete-selection result. Partial metadata can describe a failed build without
producing a consumable prepared-database manifest.

Suggested initial failure codes: `input_identity_mismatch`,
`dependency_unavailable`, `subject_context_unavailable`, `database_kind_conflict`,
`native_start_failed`, `native_nonzero_exit`, `output_missing`,
`output_inventory_incomplete`, `native_format_unsupported`, `native_row_invalid`,
`record_association_unresolved`, `sequence_length_conflict`,
`selection_incomplete`, `original_attempt_conflict`, `semantic_validation_unavailable`.
Specify mode-specific code enums before coding; do not emit arbitrary exceptions
as typed findings.

One selected completed operation contributes one ordinary local observation.
Parsing, validation checks, byte counts and report construction add no synthetic
turns. Repeated capture/projection of the same original facts adds no progress.
Practical endpoint completion follows the existing validated requested endpoint
and immediate exact-zero expectation rule; native success is not a new scientific
acceptance gate. Scientific and monitoring credit remain separate.

## 7. Exclusive workloads and exact output dependencies

Freeze the shared record schemas above before parallel production coding. These
are future workloads; no agent is assigned by this proposal. Do not grant two
owners the same file or edit root's in-progress masking files.

| Workload | Exclusive files | Tools/modes | Required output/dependency |
| --- | --- | --- | --- |
| C: shared contract | New `blast_utility_contracts.py`, contract tests | All ten closed operation/payload variants | Delivers validators/schema IDs, exact enums and cross-field invariants to all other owners; no native execution |
| F: report conversion | New `blast_report_conversion.py`, its tests | Both formatters / format_archive | Consumes C records and existing report readers; delivers normalized conversion payload and retained parser issues |
| E: extraction/inspection | New `blast_database_extraction.py`, `blast_database_inspection.py`, focused tests | blastdbcmd, blast_vdb_cmd, blastdbcheck | Consumes C and original outcome/occurrences; delivers extraction, inspection and integrity payloads; retains existing VDB parser |
| P: preparation | New `blast_database_preparation.py`, tests | makeblastdb, makeprofiledb, makembindex, blastdb_aliastool | Consumes C plus explicit artifact/dependency inventories; delivers DatabaseArtifactSet and existing-manifest projectors |
| M: mask conversion | New `blast_maskinfo_inputs.py`, tests; later exclusive additive edits to existing masking contract/calculator | convert2blastmask | Consumes C, current final masking-core contract and authentic maskinfo examples; delivers parsed maskinfo and same-sheet/calculator adapter; no duplicate masking math |
| N: native invocation | New `native_blast_utility_contracts.py`, `native_blast_utility_tool_info.py`, `native_blast_utility_driver.py`, `native_blast_utility_local.py`, `native_blast_utility_acquisition.py`, tests | All selected modes, initially qualified local ones; configured remote later | Consumes C operation/output variants; delivers exact original bundle/capture port. Does not wait for all scientific parsers |
| R: saved results/returns | New `native_blast_utility_result_worker.py`, `native_blast_utility_result_publication.py`, `native_blast_utility_results.py`, `native_blast_utility_returns.py`, `blast_utility_result_views.py`, tests | Requested typed results for all ready payload variants | Consumes C, N authenticated bundle, and each delivered F/E/P/M payload adapter independently |
| Root integration | Existing shared dispatch/communication files named in section 6; fixed progress rows and additive evidence | Enabled supported modes only | Consumes N contract and R sources/receipt ports; owns connected Workflow and requested-return checks; no scientific-grader rewrite |

F, E and P can proceed independently after C is fixed. M's precise dependency
is the final current masking schema/calculator interface and identity-preserving
maskinfo fixtures, not completion of all R7 work. N can build invocation/custody
against C while those readers proceed. R can integrate each delivered adapter
without waiting for unrelated utilities. A live VDB fixture blocks only the
authentic VDB invocation/format test that needs it.

The producer, validators and result modules must not each own their own copy of
`DatabaseArtifactSet`, sequence-length logic, native outcomes, original-attempt
qualification or masking components. Changes to a shared definition have one
owner and an additive recorded contract revision before dependent coding.

## 8. Verification that is possible locally, and actual resource dependencies

All local application imports, tests, installations and native invocations must
use the existing 529 runner with 20 GiB/4 GiB/zero swap/no wall cap. No test here
may execute database BLAST on this machine. Tiny preparations and inspections
are different operations from database BLAST; they still require explicit tiny
inputs and bounded execution. The help capture is already successful and must
not be rerun merely to repeat evidence.

| Verification | Tiny local inputs sufficient? | Specific dependency/limit |
| --- | --- | --- |
| Formatter conversion | Yes, for an authentic supplied self-contained pairwise archive | No such archive was established in this review; reuse retained native archive if available. Do not rerun successful BLAST or create a database search just to obtain one. Database-backed archives need their exact prepared context |
| VDB formatter | Potentially, with a genuinely tiny supplied offline VDB archive and complete matching VDB data | No configured fixture/closure established; production VDB context requires the actual configured data resource. No accession-triggered download fallback |
| VDB member extraction | Potentially, with a tiny authentic supplied offline VDB dataset | Synthetic four-column parser tests cannot substitute for this. Exact VDB release/member/filter/reference context is required |
| Standard makeblastdb | Yes: a few supplied FASTA records, v4 and v5, optional explicit taxid/mask map | No database search. Retain every output; malformed/duplicate ID and partial build cases |
| blastdbcmd and blastdbcheck | Yes, on that same tiny retained database | Explicitly selected extraction/info/full/sampled checks. Their success does not establish a production database or HPC deployment |
| Alias/list conversion | GI/seqid conversion can use tiny supplied lists; alias tests use the tiny databases | Validate exact dependencies, molecule mismatch, duplicates/missing IDs, binary-list info and qualified native counts |
| convert2blastmask | Yes: supplied short nucleotide/protein FASTA plus zero-mask and duplicate-ID cases | Retain XML/text plus single-record interval output; prove omission and ID semantics before numerical projection |
| makembindex | Yes: tiny supplied nucleotide FASTA for selected old-style mode or tiny staged database for new-style mode | Writes beside staged database; validate volume/output closure. No local search-based index-use test |
| makeprofiledb | Yes: actual tiny supplied scoremat text records, with all dependencies | Reuse authentic retained PSSM fixtures; no fresh PSI-BLAST fit/search. RPS/DELTA input validity and exclusions must be observable; binary/COBALT modes stay separately qualified |
| Database-scale preparation/inspection/indexing and search-based compatibility | No | Requires a real configured appropriate remote resource and its actual executable/data deployment. Aurora location/account rules are constraints, not evidence of a configured binding |
| Formatter RID mode | No offline verification | Requires an explicitly selected/configured service and original RID; no new request, polling or authentication attempted here |

Required tests for every bound mode: exact argv/options and one invocation only;
authentic native output; complete/missing/failed/partial distinction; duplicate
and mismatched identities; retained output family closure; supplied-only replay;
native-parser fields equal published/requested fields; saved mask recalculation
equal shared components; forged current-attempt/ancestor receipt rejection;
immediate-child requested subset and closed replay; and source-only catalog vs
actual resource binding. Malformed native content must retain valid rows and
actionable failures. Recalculating or projecting after original native files
are unavailable must use saved artifacts and must not invoke a binary.

Open decisions for root before coding: select the first advertised modes from
the explicit list; freeze the mask-core extension with its current owner; locate
authentic archive/PSSM fixtures without repeating successful science; and choose
an actual configured resource for any VDB/production database requirement. None
of these uncertainty statements removes a named R7 row or permits a completion
claim. A source pin, help output and this proposal are implementation evidence.
