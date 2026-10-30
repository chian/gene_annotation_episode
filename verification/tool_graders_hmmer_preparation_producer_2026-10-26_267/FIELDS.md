# P1 producer ports and exact retained shapes

This component records one explicitly selected HMMER 3.4 command. Its only
production files are the four `native_hmmer_preparation_*` modules and their
four tests. It does not choose a resource, dispatch on reservation, retry,
grade a result, publish an observation or construct an episode return.

## Public functions

`native_hmmer_preparation_contracts`:

- `validate_native_hmmer_preparation_job(value) -> Job`
- `compile_native_hmmer_preparation_job(job, *, input_paths=None,
  output_directory='.') -> Compiled`
- `requested_job_from_hmmer_preparation(job) -> RequestedJob`
- `validate_native_hmmer_preparation_requested_job(value) -> RequestedJob`
- `operand_contract(program, mode) -> (required_roles, optional_roles)` and
  `output_contract(program, mode) -> (required_roles, optional_roles)`; values
  are permitted format sets.
- `native_options(job) -> dict` preserves selected flag spelling and parses
  its exact typed value. `parse_ranges(value)` returns ordered inclusive pairs.

`native_hmmer_preparation_job_schema`:

- `preparation_job_schema(program=None, mode=None)`
- `preparation_requested_job_schema(program=None, mode=None)`
- `NATIVE_HMMER_PREPARATION_REQUESTED_JOB_SCHEMA`

The schemas are finite field/role/mode shapes. The pure validators additionally
enforce cardinality, exact ordinals, path ownership, native option relationships,
finite JSON values and exact compiler equality. Schema acceptance alone is not
permission to invoke arbitrary native arguments.

`native_hmmer_preparation_driver`:

- `validate_preparation_plan(value) -> Plan`
- `run_native_hmmer_preparation(plan) -> Bundle`
- `validate_preparation_bundle_files(bundle, directory) -> Bundle`
- `native_abi() -> dict` observes this producer's ABI; it is never a default
  for an imported database.

`native_hmmer_preparation_local`:

- `prepare_local_hmmer_preparation(state, operation_key, *, root, policy)
  -> native_lifecycle.NativeJobHandle`
- `local_hmmer_preparation_plan(assignment, execution_id) -> Plan`

Reservation uses existing `native_lifecycle.prepare_job` and does not start
the selected command. Dispatch/status/acquisition belong to existing consumers.

## Job, compiler and request

Exact Job fields:

```text
version = 'native_hmmer_preparation_job_v1'
program, mode
software = {executable:absolute_path, sha256, engine_version:'3.4'}
environment = {selected_name: selected_string, ...}
operands = [{role, ordinal, path:absolute_path, format, sha256,
             size_bytes, artifact_ref:null|string}, ...]
options = [exact selected native token strings, ...]
outputs = [{role, format, relative_path}, ...]
key = single hmmfetch key, otherwise null
input_metadata = {} or explicit FM fields described below
grading_parameters = finite JSON object, interpreted by the separate calculator
```

Ordinal starts at zero within each input role, preserving occurrence order.
Every role has one operand except `source_sequences`, which may have multiple.
Optional `ssi` must be explicitly supplied. Original model/SSI paths may be
independent Store object paths; staged model/SSI stems must match. An ambient
caller SSI is never discovered or copied. RequestedJob.argv is a logical input
representation; execution always uses the selected producer driver and its
realized staged compilation, never direct execution of that logical argv.

Compiler result is exactly `{argv, environment, outputs, working_copies,
operation}`. `working_copies` rows are
`{operand_role, operand_ordinal, destination, mutable:false}`.
`operation` is `{program, mode, engine_version, settings}`. Settings preserve
native flag spellings, declared format mappings and verified resolved defaults.
Path flags are represented by the typed outputs/operands and realized argv.
CPU count is not guessed from a native default. Selected `HMMER_NCPU` is
preserved; a selected `--cpu` has native precedence. Seed zero remains zero.

RequestedJob is exactly `{argv, environment, native_hmmer_preparation:Job}`.
Its argv/environment must exactly equal pure compilation. No file reads or
native calls happen during validation/compilation.

Alimask's mode-specific range selector is the sole mode flag carrying selected
data in `options`: exactly one of `--alirange`, `--modelrange`, `--model2ali`,
`--ali2model` with its unchanged range string. The compiler does not duplicate
it. All other owned mode/path flags are emitted by the compiler.

`input_metadata` permits `producer_contract` and `source_binding` for the two
FM tools only. Imported exactmatch requires its original `producer_contract`:

```text
{format:'hmmer_fm_3_4',engine_version:'3.4',byte_order:'little'|'big',
 uint8_bytes:1,uint16_bytes:2,uint32_bytes:4,uint64_bytes:8,int32_bytes:4}
source_binding = {database_occurrence_id,source_occurrence_ids:[...],
                  source_sha256s:[...],producer_attempt_id}
```

Source IDs/digests have equal nonzero cardinality. Exactmatch preflight compares
the source digest list to ordered supplied `source_sequences` operands. Full
occurrence lineage is validated by the result consumer. Makehmmerdb's original
recorded ABI permits the consumer to form its build contract as agreed in
261/FM_PRODUCER_CONSUMER_HANDOFF_001.md; this producer never relabels an imported
database using the current host.

## Modes, roles and formats

Every row additionally requires stdout and stderr. Their formats are
`hmmer_stdout` and `hmmer_stderr`, except the intentional conversion alias.

| Program | Exact modes | Required native output |
| --- | --- | --- |
| alimask | mask_alignment, mask_model, model_to_alignment, alignment_to_model | masked_alignment in mask modes; mapping on stdout otherwise |
| hmmbuild | build_alignment, build_single_sequence_matrix | models:hmmer3_ascii |
| hmmconvert | ascii, binary, legacy_hmmer2 | converted_models and stdout share one path and selected hmmer3_ascii/hmmer_binary/hmmer2_ascii format |
| hmmemit | sample_core_unaligned, sample_core_aligned, consensus_simple, consensus_thresholded, sample_profile | generated_alignment:stockholm for aligned samples; generated_sequences:fasta otherwise |
| hmmfetch | single_key, key_file, index | fetched_models:hmmer3_ascii or ssi:hmmer_ssi |
| hmmpress | index | binary_models:hmmer_binary, ssi_index:hmmer_ssi, msv_profiles:hmmer_h3f, remaining_profiles:hmmer_h3p |
| hmmsim | viterbi, msv, forward, hybrid | summary:hmmsim_summary via -o; scores:native_float64_vector via --xfile |
| hmmstat | summary | native stdout |
| makehmmerdb | build | fm_database:hmmer_fm_3_4 |
| hmmerfm-exactmatch | locations, count_only | hits:hmmerfm_exactmatch_hits |

Optional outputs: alimask `header:alimask_header` via `-o`; hmmbuild
`summary:hmmbuild_summary`, `resaved_alignment:stockholm`; hmmsim
`alignments:hmmsim_alignments`, `filter:hmmsim_filter`,
`survival:hmmsim_xy`, `expected_counts:hmmsim_xy`. Alimask mask output may be
Stockholm or Pfam. Press filenames must have one common stem and the native
`.h3m`, `.h3i`, `.h3f`, `.h3p` suffixes. Fetch index uses `.ssi`.

Model inputs permit `hmmer3_ascii`, `hmmer2_ascii`, `hmmer_binary`. Alignment
declarations permit Stockholm, Pfam, A2M, PSI-BLAST, SELEX, AFA, Clustal,
Clustal-like, interleaved PHYLIP and sequential PHYLIP using their exact lower
case native format identifiers. Sequence declarations additionally permit fasta,
embl, genbank, ddbj, uniprot, ncbi, daemon, hmmpgmd. The compiler passes native
`--informat` explicitly. These declarations do not claim every format was run
through this producer; see REPORT.md for actual coverage and limitations.

## Plan, attempt identity and filenames

Plan is exactly `{version:'native_hmmer_preparation_run_plan_v1',identity,
requested_job,attempt_directory,policy}`. Identity has exactly `run_id`,
`episode_id`, `resource_id`, `execution_id`, `attempt_id`, `operation_key`,
`requested_job_sha256`; hashes use existing canonical `native_infernal_digest`.
Policy is the explicit caller `{memory_bytes,scratch_bytes,wall_seconds}`.

The reservation root is
`workspace/.episode-operations/digest({run,episode})/digest(operation_key)`.
Local constants are `PLAN_NAME='hmmer-preparation-plan.json'`,
`ATTEMPT_NAME='hmmer-preparation-attempt'`, `INVOKE_NAME='invoke.json'`,
`HANDLE_NAME='native.json'`. The selected driver is the current Python executable
with `-m gene_annotation_episode.native_hmmer_preparation_driver <plan>`.

Driver constants are `OWNER_NAME='.native-hmmer-preparation-owner.json'`,
`BUNDLE_NAME='bundle.json'`, `INPUT_DIRECTORY='inputs'`,
`MODEL_STAGING_PATH='inputs/models.hmm'`,
`SSI_STAGING_PATH='inputs/models.hmm.ssi'`. Other operands use
`inputs/<role>/<ordinal>`. The private press/index source copy is the selected
output stem with its native output suffix removed. The caller model is never
used as the writable index stem. TMPDIR/TMP/TEMP point to attempt `tmp`;
XDG_CACHE_HOME points to attempt `cache`.

## Bundle rows and failure meaning

Exact bundle fields are `version='native_hmmer_preparation_bundle_v1'`,
`identity`, `requested_job`, `program`, `mode`, `operation`, `software`,
`realized_argv`, `environment`, `inputs`, `working_copies`, `returncode`,
`artifacts`, `failures`, `started_at`, `finished_at`, `native_abi`.

```text
software = {executable,expected_sha256,actual_sha256:null|sha256,
            declared_engine_version}
inputs[] = {role,ordinal,format,original_path,relative_path,artifact_ref,
            expected_sha256,expected_size_bytes,
            staged_sha256,staged_size_bytes,final_sha256,final_size_bytes}
working_copies[] = {operand_role,operand_ordinal,relative_path,mutable,
                   source_sha256,initial_sha256,initial_size_bytes,
                   final_sha256,final_size_bytes}
artifacts[] = {role,format,relative_path,size_bytes,sha256}
failures[] = {stage,code,role:null|string,detail:closed_typed_object}
```

Measurements are paired nulls when unavailable; an existing empty file has
size zero and the real empty-byte SHA256. Nonzero execution preserves complete
valid prefixes and all other existing output files. `returncode:null` means the
native command did not start; it is not a successful empty scientific result.
Timestamps are original aware ISO timestamps. Existing lifecycle timing remains
service wall time, not native CPU time or queue time.

Native ABI exact fields: `byte_order`, `float_format`, `bytes_per_float`,
`uint8_bytes`, `uint16_bytes`, `uint32_bytes`, `uint64_bytes`, `int32_bytes`,
`c_int_bytes`, `c_long_bytes`, `c_float_bytes`. Observed C-double scores use
`float_format='ieee754_binary64'`, `bytes_per_float=8`; unsupported observed
representations use `unsupported`, never a fabricated IEEE label. Binary HMM
payloads contain C floats separately; `bytes_per_float` here describes the
native hmmsim score-vector C double.

`FAILURE_CODES` is the closed prefixed code set; `_FAILURES` gives exact stage
and detail field types. `PREFLIGHT_REASONS` is the closed reason set.
`PREFLIGHT_FAILURE_CONTEXT` gives per-code role/program/reason sets, keyed by
unprefixed code. The eight codes are invalid_alimask_input,
unsupported_alimask_model_map, unsafe_alimask_range, invalid_exactmatch_queries,
incompatible_fm_abi, invalid_fm_database, invalid_model_format,
source_binding_digest_mismatch. Preflight relationship validation additionally
requires:

- unsafe_alimask_range: alignment_to_model, an actually selected pair and
  start greater than the recorded last match column;
- source_binding_digest_mismatch: an original binding exists and its ordered
  hashes differ from the actual selected source operand hashes;
- incompatible_fm_abi: the reason identifies a real difference between the
  supplied contract and this original bundle's recorded ABI;
- invalid_fm_database: issue_codes is a sorted unique list of F1's closed
  extraction codes, retained in full.

Exactmatch uses `hmmer_fm_data.extract_hmmer_fm_database` only for supplied-index
structural preconditions. It requires compatible DNA reader metadata, complete
population/body and no issues. It never calls a calculator. Complete framed but
invalid arrays are rejected; complete flags alone are insufficient.

An existing sealed attempt validates and returns its original bundle without
another native call. Missing bundle/handle or changed ownership leaves an
explicit uncertain existing attempt. It does not authorize replacement work.
Retained complete directories may move; original identity/argv/environment stay
unchanged. A different selected repair needs its own operation identity.
