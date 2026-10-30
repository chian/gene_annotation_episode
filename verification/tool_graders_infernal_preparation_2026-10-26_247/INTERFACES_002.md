# Additive interface corrections — 247/002

These additions resolve concrete missing fields found by the three coding
workloads. INTERFACES_001 remains the permanent original freeze. No goal, scope,
episode or scoring change is made. Original objective/all16-principle resets
remain required. Root's infernal_preparation_schema.py helpers are now present.

## A: selected positional key and authenticated artifact bindings

Operation.settings permits the additional key `key` ONLY for cmfetch, containing
the exact selected positional single_key string. It is not a native flag and
must not be turned into an invented native key-file artifact.

The input role `request`, format `infernal_request_json`, may contain the actual
retained original requested job. It is required for a single_key key_request
locator: the request, not the model file, is the source of that requested key.
Null native line/byte locations are appropriate there; ordinal0 is the first
request. The compiler/worker validates correspondence between the original
request, operation.settings.key and selected argv. A reader must not claim the
key was read from model bytes. Missing request provenance yields an explicit
issue; do not manufacture a locatable request row from another artifact.

A validation parameters permit exactly `artifact_bindings`, a list of:

    {artifact_ref, artifact_sha256, source_artifact_ref, source_sha256,
     expected_attempt_id, actual_attempt_id, staged_source_stem,
     actual_relative_path, regular_file}

References/stems/paths/attempt IDs are strings, digests lower-case64hex, and
regular_file boolean. Root supplies these only from validated selected invocation
and capture facts. The pure validator does not access paths. For supplied old
indices, expected producer attempt refers to that selected producer, not the
current invocation. Output suffixes are .ssi/.i1m/.i1i/.i1f/.i1p as appropriate.
Checks compare actual digest/source to sheet artifacts, exact attempt, selected
stem/suffix and regular-file facts; a quartet has the same original source,
producer and stem. Missing binding facts remain unknown. These checks establish
the captured association, not decoded binary index-entry integrity.

## B: source populations, partition requests and build refinement

calibration.identity is now exactly {algorithm,source,name}, with actual native
name or null, and source stdout/model_header. This preserves the native token
needed for an association without inventing a model match.

Additional kind `training_alignment` has exactly:

    {kind,record_key,locator,format,name,accession,content_validation,
     sequence_names,values}

format is the actual supplied format; name/accession are native strings or null;
content_validation is parsed/partial/invalid; sequence_names is the ordered list
of original row names, including duplicates. values has exactly row_count,
column_count,checksum,rf_column_count as Value cells, units count,column,
dimensionless,column respectively. Digital checksum is computed only with a
known compatible alphabet and coherent actual sequence matrix. Missing/malformed
RF/SS_cons is a separate fact; full original annotations remain retained. Input,
processed and refined alignments retain separate artifact and record identities.

Additional kind `build_refinement` uses B's common row envelope. identity is
exactly {name,input_alignment_index,native_index,iteration}; name string/null,
indices are native integers/null, preserved without silently converting printed
indices to input ordinals. values has exactly bit_score_sum (bit) and
fractional_difference (fraction). Missing '-' stays missing. series is empty.
These are native optimization iterations, never episode observations or a new
continuation rule.

B calculation parameters also permit `partition_requests`, a list of:

    {artifact_ref,source_model_artifact_ref,source_model_sha256,
     partition_index,partition_count,requested_megabases,settings}

Artifact references are strings, source digest lower-case64hex, partition values
positive integers and requested_megabases finite positive number. settings uses
original selected native flag spellings with finite scalar values. Root binds
these supplied facts to actual captured original partition requests; command
text inside a score file is never their authority. Compare complete unique p=1..P,
exact original model bytes/order, finite array lengths and relevant simulation/
fit settings. The selected --part index naturally varies; --split/--merge are
operation choices, not presumed differing simulation. Seed semantics must be
explicit and compatible. Missing partition_requests means unknown provenance,
not success or an instruction to acquire/launch missing partitions.

## C: incomplete model populations and emission expectations

The ModelExtraction population_complete flag is carried into the saved sheet
through a closed `cmemit_model_population_incomplete` issue when false. Expected
model/sample counts cannot be calculated from a partial decoded model list.

An embedding length and a post-truncation output length can describe different
stages. Preserve both selected settings and actual sequence/interval facts.
Validate against the actual documented/source-tested order of native operations,
not an assumption that every -e combination guarantees the final length. A
native discrepancy, if established, remains explicit; do not repair sequence data.
Trace bytes remain retained independently. Decoding a new trace family requires
a separate exact row contract and native example, not an untyped added dictionary.
