# Closed helper types completing proposal642/001

This is an unfrozen proposal clarification. It supplies the explicit parser and
new-output shapes referenced by642/001; root owns the common schema freeze.
Every object below is closed, every listed field is required, integers exclude
booleans, numbers are finite, and absent facts use the indicated null rather
than defaults. Strings are native facts or constrained references, not findings
or instructions. Existing UtilityFailure/ValidationObservation are reused.

## Operation and identity alignment

All nine new operation pairs use `blast_utility_operation_v2`, alongside643's
VDB branches under the single common Operation union and validator. The current
five operation_v1 branches remain exact; no separate VDB/preparation validator
duplicates common fields. Common fields remain `version,program,mode,
input_occurrence_ids,database_key,molecule,parameters`. parameters is exactly the
corresponding closed object in642/001.

Operation.database_key names the single selected source DB for bound seqid
conversion, subset/volume alias, DB-based index or show_filters, and is null for
unbound conversion, list inspection, multi-DB aggregation, FASTA index and profile
creation. A source_database_key/seqid_database_key parameter, when present, must
agree with it. Aggregate dependency entries retain every selected database key.
The result's prepared-artifact database_key is the existing worker's durable
output identity, distinct from source input DB keys.

For preparation identity, reuse the existing additional
`native_blast_database_contracts.DATABASE_IDENTITY_SCHEMA` structure and values:
namespace/value/version/release/scope/preparation_type/source. Classic aliases
use sequence_database; RPS/DELTA use rps/delta; identifier lists, index artifacts,
COBALT and unclassified VDB aliases use unknown. Their exact known preparation
operation is already in kind/detail. This avoids introducing unnecessary
identity enum values or changing search manifests. In particular, alias result
identity and standard prepared projection both retain sequence_database; do not
rewrite an identity's preparation_type during projection. This clarification
replaces642/001's initial proposal for additional identity enum values.

## Parser document types

Every parser returns:

```
{version: blast_preparation_document_v1,
 kind: list|alias|seqid_info|aliastool_diagnostics|index_diagnostics|
       profile_aux|profile_diagnostics,
 occurrence_id: string,
 native_fields: [NativeField],
 rows: [<kind-specific row>],
 checks: [ValidationObservation], failures: [UtilityFailure]}
```

Only alias, seqid_info and aliastool_diagnostics may populate native_fields in
this initial port. Alias native_fields use TITLE/NSEQ/LENGTH only when correctly
located; LENGTH has value_basis=native_reported and never native_reported_exact.
The exact raw field is also retained in the alias row. Empty unknown lines do
not become zero. Type branches are:

* list: `{ordinal,line_number,token_ordinal,original_token,start_byte,end_byte}`.
  Offsets are zero-based half-open spans of the original UTF-8 bytes. Grammar is
  the selected blast_database_lines or profile_whitespace_tokens. A list parser
  validates lexical facts; the population owner validates the exact selected
  input/DB join. It does not remove repeated entries. Unrepresentable native
  whitespace tokens fail explicitly, not via guessed shell quoting.
* alias: `{row_ordinal,line_number,native_key,value_lexeme,tokens}`. tokens are
  `[{ordinal,value,native_lexeme}]`, preserving quoted DBLIST/VDBLIST order and
  restriction-file tokens. native_key/value_lexeme are exact native text. Known
  semantic keys are TITLE, DBLIST, VDBLIST, GILIST, SEQIDLIST, TAXIDLIST, NSEQ and
  LENGTH. Other keys are retained but do not establish compatibility or an
  invented interpretation. Alias document in kind detail is this whole parsed
  document, not an untyped bag of effective values.
* seqid_info: rows=[], native_fields are the located title, stored ID count,
  created-at text and optional DB date/length/volume fields. File-only inspection
  of a previously DB-bound list can preserve its native volume/length text with
  molecule unknown; it cannot invent a live DatabaseBinding from a basename.
* aliastool_diagnostics: `{line_number,category,native_lexeme,native_count}` where
  category is converted_gi_count|created_alias_sequence_count|native_error|unknown;
  native_count is nonnegative integer or null, non-null only for a recognized
  count. GI converted count uses identifier_list_converted_count, not stored-ID
  count. Add the pure port
  `parse_blast_aliastool_diagnostics(contents: bytes, *, occurrence: dict) -> dict`.
* index_diagnostics: `{line_number,category,native_lexeme,parameter_observation,
  native_output_reference}`. category is parameter_adjusted|parameter_ignored|
  member_created|empty_member_removed|native_error|unknown. Parameter observation
  and native_output_reference are nullable, present only for the relevant
  category. A removed empty member is not an available artifact. The source
  path is joined to actual captured members before assigning occurrence IDs.
* profile_aux: `{native_profile_ordinal,sequence_length,karlin_k,
  length_line_number,k_line_number}`. Ordinals are contiguous native aux order;
  lengths are nonnegative integers, K finite numeric. Matrix/gap/scale header
  observations are supplied as the `parameter_observations` member of this
  document branch, required only for profile_aux. Native source writes matrix,
  gap open, gap extend on lines1–3, four placeholder lines4–7, scale on line8,
  then length/K pairs. Preserve raw bytes including placeholders. Authentic
  successful single-input native aux coverage is now provided by sealed102d
  (see the additive evidence record); multi-volume coverage remains unverified.
* profile_diagnostics: `{line_number,category,native_reference,native_lexeme}`.
  category is excluded_low_observations|excluded_invalid|missing_frequency_ratios|
  missing_weighted_frequencies|missing_independent_observations|missing_core_blocks|
  profile_size_conflict|parameter_conflict|native_error|unknown. native_reference
  is string|null; an unlocated error cannot mark every submitted profile failed.
  Repeated matching source references remain ambiguous unless native provides
  enough order/context. The original native nonzero exit remains a separate fact.

ParameterObservation's `parameter` enum is nmer|ws_hint|stride|legacy|
old_style_index|output_prefix for index; matrix|gap_open|gap_extend|scale|
word_score_threshold for profile. Numeric value types follow the parameter;
matrix/output_prefix are strings and the two boolean parameters are booleans.
`effect=ignored` carries null value, with native source line; effective requires
non-null value and located native evidence; unknown requires null value and a
missing_reason. `scope_key` refers to the exact index build, volume or profile
entry, never an invented globally effective default.

NativeField additions are closed typed values with the existing location,
value_basis, missing_reason and unit contract:

| field_name | non-null value type | unit |
| --- | --- | --- |
| identifier_list_title | string | text |
| identifier_list_count | nonnegative integer | identifiers |
| identifier_list_converted_count | nonnegative integer | identifier_occurrences |
| identifier_list_created_at_native | string | text |
| identifier_list_database_created_at_native | string | text |
| identifier_list_database_length | nonnegative integer | nt, aa or symbols |
| identifier_list_database_volumes | array of strings | paths |

Unknown native volume basis uses symbols, with no fabricated molecule. Native
date text has no added timezone. An alias NSEQ/LENGTH field belongs to that
alias document, not a sum recomputed from supplied databases. The check102c
example establishes why LENGTH must not acquire exact extracted-length meaning.

## New output selection and materialization population

New job output rows have exactly:

```
{output_key,role,path_kind,relative_path,format,population,database_key}
```

output_key is unique nonempty text. role is stdout|stderr|identifier_list|
database_family|index_family|statistics. population is file|prefix_members|
staged_database_members. file requires path_kind=file and database_key=null;
family populations require path_kind=prefix. staged_database_members requires
the exact selected copied database_key; other rows require null database_key.
Streams are file/text except inspect_seqid_list stdout, whose format is
blast_seqid_list_info_text. Converted-list file format matches its conversion.
database_family uses blastdb_family, index_family uses blast_index_family,
statistics uses text. Collection maps native members to the common occurrence
roles defined in642/001, without fabricating a file for the prefix itself.

For new style index, one selected index_family scope names the staged DB native
prefix; complete copied DB closure and selected native volume path mapping
determine the owned inventory namespace. Distinct volume namespaces can use
separate output_keys. Only newly created members become native output artifacts;
all original/staged source DB files remain explicit input dependencies. No file
may belong to two scopes. New-job bundle artifact rows carry exactly the old
artifact fields plus output_key. All files in the selected owned scope are
captured; unknown sidecars use an unknown format and retained native path.

The new materializations object is always present, using empty arrays where
unneeded. Every list_files row must correspond to one selected file-list
operation reference. DatabaseEntry/Materialization list token order is exact;
token_ordinal=0 for one-name-per-line grammar. No implicit source→destination
path mapping is derived by stripping directory names. Common qualified input
occurrences include originals and retained realized lists/copies as distinct
occurrences, and each MaterializationReceipt joins uniquely by original path,
realized native path, role and expected/staged/final digest. A common input
occurrence keeps its own artifact_ref; source and realized identities cannot be
merged merely because bytes happen to match.

Existing public signatures retained exactly, with only the new context keyword:

```
populate_database_artifact_set(*, operation, inputs, outputs, database_key,
 identity, software, argv, native_paths, dependency_bindings, native_metadata,
 outcome, preparation_context=None) -> dict
validate_database_artifact_relationships(record: dict) -> dict
project_prepared_blast_database(record: dict, *, contract: str,
 preparation_receipt: dict, input_manifest: dict|None,
 metadata_manifests: list[dict]) -> dict
compile_native_blast_utility_job(job: dict, *, input_paths: dict,
 database_paths: dict, output_directory: str) -> list[str]
```

The new preparation_context is `{database_bindings,materializations,documents}`.
The new population function derives dependency/native metadata from selection
and parsed native documents; supplied dependency_bindings/native_metadata must
agree, preventing a second authority. Projection contract is explicitly standard
or additional according to the supported manifest branch. Existing standard
calls remain exact. No caller supplies effective parameters or native profile
dispositions as an unauthenticated independent result.
