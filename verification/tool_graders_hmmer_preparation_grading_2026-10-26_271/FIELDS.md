# D1 closed composition interface

This documents the ordinary Python composition functions, not a second scoring
language. Component readers populate numerical sheets; component calculators
calculate quantities from them. D1 selects and validates this composition.

## Input contract

`operation` is exactly `program,mode,engine_version,settings`. The supported
producer contract is HMMER3.4. Program and mode must be one of P1's 26 exact pairs.
Settings are an original finite JSON object and are preserved without rewriting.

`inputs` and `outputs` map a permitted role to an ordered list of exact
`{occurrence,content}` objects. Content is `bytes`. The occurrence has exactly
`occurrence_id,direction,role,ordinal,artifact_ref,sha256,size_bytes,completeness`.
It must satisfy M1's occurrence contract and match the direction, role, actual
byte size, and digest. Identities are globally unique. Per-role ordinals strictly
increase and need not be contiguous: absence never renumbers later artifacts.
Same bytes in different occurrences retain separate identities.

`formats` maps every supplied occurrence identity to exactly one P1-permitted
declared native format. No extra or missing identities are allowed. Role/format
compatibility uses P1 `operand_contract` and `output_contract`. Original
`--informat` for source alignment/sequences and `--outformat` for masked output
must agree with the explicit declaration; D1 does not enable autodetection or
conversion. Missing required roles are accepted as partial supplied data. An
existing zero-byte artifact keeps its occurrence; absent roles are not created.

`metadata` is a finite JSON object. Optional keys are program-specific:

| Programs | Optional metadata |
| --- | --- |
| hmmconvert, hmmfetch, hmmpress | `artifact_bindings` |
| makehmmerdb, hmmerfm-exactmatch | `producer_contract`, `source_binding` |
| Other preparation programs | none |

Explicit null optional values are retained. Non-null A1 binding records have
exactly `artifact_occurrence_id,source_occurrence_id,source_sha256,producer_attempt_id,staged_source_stem,actual_relative_path`.
F1 producer metadata has exactly `format,engine_version,byte_order,uint8_bytes,uint16_bytes,uint32_bytes,uint64_bytes,int32_bytes`.
F1 source binding has exactly `database_occurrence_id,source_occurrence_ids,source_sha256s,producer_attempt_id`;
the source identity/hash lists have the same nonzero cardinality. Strings,
digests, and integer widths have validated shapes. Relationship mismatches or
unsupported recorded producer representations remain component diagnostics.
Unrelated metadata keys are errors, not silently discarded information.

`native_abi` is null or P1's exact eleven-field recorded object:
`byte_order,float_format,bytes_per_float,uint8_bytes,uint16_bytes,uint32_bytes,uint64_bytes,int32_bytes,c_int_bytes,c_long_bytes,c_float_bytes`.
Byte order is little/big. Float format is ieee754_binary64/unsupported. Widths
are positive integers; binary64 requires eight bytes. Only the first three
fields reach S1. F1 never obtains ABI from this argument: it consumes only
`metadata.producer_contract`. No host ABI is inferred.

`parameters` is an explicit finite JSON object with the following optional keys.
Unknown keys raise an error. Domain validation of a known numerical parameter
belongs to its calculator, preserving unaffected quantities.

| Component | Allowed parameter keys |
| --- | --- |
| A1 | probability_tolerance, expected_revision |
| B1 | background, probability_tolerance, summary_rounding_tolerance |
| E1 | consensus_thresholds, probability_rounding_tolerance |
| S1 | fixed_lambda, fit_tolerance, solver_iteration_limit, rounding_tolerance, tail_masses, filter_criterion |
| H1 | background, length_probability, probability_tolerance, summary_rounding_tolerance |
| F1 | alphabet_normalization, coordinate_policy, exhaustive_literal_check |

H1 receives only the supplied keys. The caller can explicitly use
`native_hmmstat_parameters(version, alphabet)`; D1 never calls that helper to
replace absent background or length probability. Each calculator records its
own resolved parameters separately from the original request.

## Dispatch and stored result

| Program | Modes | Reader → calculator |
| --- | --- | --- |
| alimask | mask_alignment, mask_model, model_to_alignment, alignment_to_model | B1 populate_hmmer_alignment_preparation_sheet → calculate_hmmer_alignment_preparation_components |
| hmmbuild | build_alignment, build_single_sequence_matrix | B1 same pair |
| hmmconvert | ascii, binary, legacy_hmmer2 | A1 populate_hmmer_artifact_sheet → calculate_hmmer_artifact_components |
| hmmfetch | single_key, key_file, index | A1 same pair |
| hmmpress | index | A1 same pair |
| hmmemit | sample_core_unaligned, sample_core_aligned, consensus_simple, consensus_thresholded, sample_profile | E1 populate_hmmemit_sheet → calculate_hmmemit_components |
| hmmsim | viterbi, msv, forward, hybrid | S1 populate_hmmsim_sheet → calculate_hmmsim_components |
| hmmstat | summary | H1 populate_hmmstat_sheet → calculate_hmmstat_components |
| makehmmerdb | build | F1 populate_hmmer_fm_sheet → calculate_hmmer_fm_components |
| hmmerfm-exactmatch | locations, count_only | F1 same pair |

M1 `extract_hmmer_models` consumes each actual model occurrence with its declared
format. A1 receives all model-role extractions including pressed binary models.
Conversion stdout is retained as an occurrence but is not another model
population. B1 build receives the output model envelope; mask receives None.
E1 and H1 receive the full original input envelope. S1 receives every original
input model occurrence. P1 singleton roles for B1/E1/H1 cannot silently choose
one of multiple supplied model artifacts. Missing model envelopes are None or
an empty extraction list, as the existing component port expects.

The returned finite JSON object has exactly eight fields:

| Field | Meaning |
| --- | --- |
| version | `native_hmmer_preparation_grading_v1` |
| operation | copied original operation, every setting retained |
| formats | exact supplied occurrence/format declarations |
| metadata | copied original applicable metadata |
| native_abi | copied original full ABI or null |
| requested_parameters | copied original requested parameters, not calculator defaults |
| sheet | complete component numerical sheet, with its existing schema and fields |
| calculations | complete component calculator result, including resolved parameters, rows, checks, and issues |

No opaque bytes object enters the return envelope. Existing component tokens,
native lines, decoded arrays, byte representations, occurrence facts, and
associations remain unchanged. E1 scalar cells retain their actual top-level row
positions; D1 does not normalize them into a new `components` object. No universal
confidence field, success flag, scoring language, or annotation credit is added.

## Saved recalculation and failures

`recalculate_hmmer_preparation` requires the exact sheet top-level field set and
its matching program/schema. Schemas are `hmmer_artifact_sheet_v1`,
`hmmer_alignment_preparation_sheet_v1`, `hmmer_emission_sheet_v1`,
`hmmer_simulation_sheet_v1`, `hmmer_statistics_sheet_v1`, and `hmmer_fm_sheet_v1`.
It copies the saved sheet, validates finite JSON and the new parameter keys,
then calls only that calculator. It returns the calculator's full result and
does not mutate the saved sheet, parse original bytes, or read references.
Calculator-specific saved shape, relationship, and numerical validations retain
their own checks and issues.

Malformed dispatcher handoffs raise `ContractError`, a `ValueError` subclass,
with a specific `native_hmmer_preparation_grading_<code>:<field>` message. Codes
cover finite JSON/object fields, program/mode/version, ABI, metadata, payload
roles, occurrences, digest/size/order/identity, formats, parameter keys, model
cardinality, and saved schema/program pairing. Malformed nested saved structures
that would raise KeyError/TypeError/IndexError/AttributeError/OverflowError are
reported as `saved_sheet_invalid` rather than causing reader or acquisition work.

Native missing/partial/empty/nonfinite/unsupported observations continue into
the selected component. Missing is never converted to numerical zero. A list of
issues does not make every quantity unusable: repeated alias labels and unknown
binary model probabilities, for example, coexist with meaningful occurrence
counts or measured byte totals. Custody authentication and original bundle
binding remain the caller's responsibility.
