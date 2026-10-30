# Infernal bounded grading worker: workload 224

Read the entire original goal attachment and AGENTS.md first. Preserve the
verbatim objective/all 16 principle reread after substantial native/source
study and before closure. This implements numerical integration, not a new
episode, acquisition, native execution, literature grader or annotation score.

## Exclusive owned files

- New gene_annotation_episode/native_infernal_result_worker.py
- New tests/test_native_infernal_result_worker.py and own fixture directory
- This verification directory

Root owns all shared files, result views and runtime integration. Worker 223
owns acquisition. Producer 222 is finished. Numerical workers 219/220 own their
pure parser/calculator modules; coordinate any discovered defect with them/root.

## Exact interfaces

Root has written infernal_native_result_views.py. Read it completely. It defines
five families, exact metric enums, collection mapping, selector validator and
projected_measurements(score, metrics, *, family). Do not invent metrics.

Implement run(plan) -> manifest and CLI python -m
gene_annotation_episode.native_infernal_result_worker PLAN_PATH. Plan is exactly
{version:native_infernal_grading_plan_v1, bundle, artifacts, directory, selector,
failures}. Each captured artifact has {role,format,relative_path,artifact_ref,
kind:input|output,path}. Inputs have already been acquired and hash-validated.
Read only those captured paths, never original producer/input paths. Do not
invoke tools, network, a model, new resource decisions or Store inside worker.
Root's publication layer invokes it once under existing LocalJobPolicy.

Output files under the supplied directory:
- sheet.json: the complete infernal_search_sheet_v1 or cmalign_sheet_v1, plus
  publication_inputs with original supplied_metadata, parsed_records, exact
  operand_bindings and captured artifact descriptors excluding local paths.
- scores.json: complete separate pure calculator output.
- selected-rows.ndjson: requested rows in original native order, no implicit
  ranking, threshold, top-hit choice or change of grading parameters.
- diagnostics.json: full structured diagnostics, including associations.
- worker-result.json: manifest {version:native_infernal_worker_result_v1,
  sheet_schema:string|null,scores_schema:string|null,numerical_complete:bool,
  failures:[{stage,code,record_key:string|null}]}.

The selected row is exactly {version:native_infernal_selected_row_v1, family,
native_ordinal,record_key,locator,sequence_name,model_name,strand,origin,population,
column_index,pair_columns,invalid,measurements,unavailable,observation_measurements,
subject_operand,subject_intervals,related_operands}. sequence_name/model_name
nullable; strand native +|-|null; origin newly_aligned|inherited|unknown|null;
population all|newly_aligned|inherited|reported|included|null; column_index
zero-based|null; pair_columns two zero-based integers|null. Metrics use the exact
views helper. observation_measurements holds all available family quantities,
independent of the requested metric subset, so projections do not change the
underlying scientific observation identity. No timing enters those observations.

Compact subject/related operand: {operand_role,record_ordinal,artifact_ref,name,
accession,kind,alphabet,length,sequence_sha256,locator,binding}; kind is
nucleotide_sequence or covariance_model; sequence hash is original uppercase
input sequence SHA256, null for model. Model length is CLEN. binding is the exact
explicit original operand_binding only when ordinal AND supplied native name/
accession validate; otherwise null with a specific diagnostic. Subjects must
come from an unambiguous native-to-input association, never an arbitrary first
name match. subject_intervals is a list of actual zero-based half-open physical
input intervals; empty if unknown. Related models are family references, not
physical reference-residue coordinates. Alignment column/pair populations can
return typed numbers without an invented single subject; then subject_operand
is null, subject_intervals empty. Retain all source membership in the full sheet.

## Source inputs and scientific modes

Consume actual FASTA, Infernal ASCII model records (CM block plus HMM filter),
optional mapali Stockholm, and actual selected outputs. Read complete producer
and pure grader implementations. No fake original ordinals from tblout query
positions: no-hit queries and duplicate names make that unsafe. Parse actual
input model name/accession/CLEN and original sequence bytes. Search metadata
passed to 219 must not add occurrence unless native output really establishes
it; unique names/accessions can join, duplicates stay unresolved. Preserve
supplied metadata separately and report conflicts with actual input fields.

Search: populate_infernal_search_sheet(artifacts, operation={program,
native_version,settings}, sequence_metadata=..., model_metadata=...); artifacts
are retained tblout with explicit actual table_format and completeness. Calculate
using only original job.grading_parameters. Parse native_options into settings
without changing them, including oskip and native score/threshold modes.

Alignment: populate_cmalign_sheet(..., operation, sequences, model,
inherited_alignment). Map selected native flags to settings.matchonly, global,
notrunc, sub, algorithm optacc|cyk|sample, mapali and other actual options. EL
sidecar is optional for global mode. --mapali can produce headerless insert/EL
tables; only explicit model identity permits association. Inherited row prefix,
new row order and same-name collisions require the pure grader's actual mapping
checks. Do not infer equality from names. T/U, X/N, I/A are native normalization
for output matching, while original input identity remains separately retained.

Search aggregate keys come from aggregate_id; hit keys from hit_id; alignment
keys from record_key. Preserve native IDs as stored row keys; root will provide
any necessary distinct host identifier in its publication layer rather than
changing raw sheet row identity. Missing requested keys produce selection
failures. Invalid/partial cells preserve useful values and specific missingness.
Keep uncertainty and dependency limits; never claim spans are residue pairing,
rendered model gaps are deletions, or repeated files are independent evidence.

## Verification and handoff

Use 222's three successful retained producer examples and failure example,
219/220's real outputs and synthetic edge cases when needed. Check numerical
values for all five projection families, original option interpretation, correct
input binding, duplicate names, wrong metadata, source-selected rows, missing
and partial data, and operation without Store/network/native execution. Test
processes use local_jobs.run_local_job with explicit 20GiB RAM/4GiB scratch/no
wall cap. Do not rerun scientific tools to populate already saved examples.
Report exact tests, source hashes, selected example rows, and remaining limits.
