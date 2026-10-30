# Additive generated trace and artifact-row clarification — 247/004

C's four new retained native trace examples permit extraction of score headers
without guessing node-level semantics. Add native_rows kind generated_trace,
exact keys {kind,record_key,locator,model_keys,sequence_keys,name,trace_family,values}.
model_keys/sequence_keys are actual unambiguously associated record-key lists;
name is the native header string or null. trace_family is cm_parsetree/hmm_trace.
values has EXACT score_bits and structure_score_bits (Value, unit bit).

Unaligned CM/HMM native traces have sequence header, SCORE, STRUCTURE SCORE,
full body and // terminator. Aligned CM traces have names/body/terminator with
unreported score headers; these cells stay not_measured. A genuinely empty
aligned HMM trace file has no records; do not invent an empty score. Preserve
native sentinels with their token and correct unavailable meaning where native
code establishes that meaning. A reported HMM number does not establish CM
structure evidence. The native body remains intact in its separate artifact;
node-level decoding is an explicitly unfinished format subcase.

C COMPONENT_NAMES also permits score_bits and structure_score_bits as separate
reported numerical components, with original provenance and no combined score.
This remains generated-data inspection, not observed evidence about a gene.

A's artifact_operation.operation is the full frozen Operation dict, equal to
sheet.operation. It is internal retained data and is not copied wholesale into
a prompt. An empty but captured stdout can have missing native counts; absent
stdout is different and must not receive an invented source record or locator.
