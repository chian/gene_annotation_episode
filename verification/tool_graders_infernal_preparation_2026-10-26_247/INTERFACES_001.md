# Infernal preparation interfaces and parallel ownership — 247

This additive implementation contract freezes the handoffs proposed in work246.
It does not change the immutable goal or claim completion of any inventory row.
The full goal attachment remains authoritative. Read its objective and all16
design principles verbatim after substantial native/source study, after each
tool, and before closure; then reread this contract and the relevant complete
sections of work246/IMPLEMENTATION_CONTRACT_PROPOSAL_001.md. Never substitute a
summary for that reset. The seven rows remain supporting operations with no
independent annotation confidence. No literature, W05, new episodes, hidden
commands, retries or scientific observations about a target gene are introduced.

## Ownership and dependencies

All paths below are relative to gene_annotation_episode/ unless specified.

* A owns new infernal_preparation_models.py and infernal_preparation_artifacts.py,
  tests/test_infernal_preparation_models.py and
  tests/test_infernal_preparation_artifacts.py, and verification/..._248/.
  Deliver current/legacy CM and standalone HMM parsing, explicit opaque binary
  handling, cmconvert, cmfetch and cmpress sheets and validation calculations.
* B owns new infernal_preparation_statistics.py and
  infernal_preparation_calculations.py, tests/test_infernal_preparation_statistics.py
  and tests/test_infernal_preparation_calculations.py, and verification/..._249/.
  Deliver cmbuild, all six cmcalibrate modes and all seven cmstat modes, including
  separate complete native sidecar arrays and saved-data calculations.
* C owns new infernal_preparation_emission.py and
  infernal_preparation_emission_calculations.py,
  tests/test_infernal_preparation_emission.py and
  tests/test_infernal_preparation_emission_calculations.py, and verification/..._250/.
  Deliver cmemit sample_unaligned, sample_aligned and consensus, model/sequence
  associations, generated-data numerical components and validation.
* Root owns infernal_preparation_schema.py, native_infernal_preparation_contracts.py,
  native_infernal_preparation_worker.py, infernal_preparation_result_views.py,
  all changes to existing files, execution integration and integration tests.

A's ModelExtraction below is the only A→B/C dependency. B/C can code against this
exact shape immediately, with an explicit synthetic fixture, then test A's actual
output once available. All three deliver Sheet and Calculations below to root's
pure worker and projection. No agent changes another owner's files or inventory.
If a native fact needs a contract addition, send the exact proposed field/type,
meaning and consumer to root; do not silently broaden shared dictionaries.

## Common data and helper API

These are finite JSON data, not a scoring language. All dict keys below are exact.
Text, bytes and iterable text may be supplied to readers; no paths, subprocess,
network, model or Store access occurs in parsers/calculators. Retained full native
artifacts remain separate from these extracted data. Values must never be rounded
to fit a prompt; only a requested projection is rendered later.

Operation = {program, mode, engine_version, settings}. Programs/modes are exactly
those in work246 sections3–9. settings uses actual CLI flag spellings as keys,
with finite number/string/bool values, including verified resolved defaults.
Input/output path flags are absent: artifacts name those roles. Parsers may not
guess unprovided settings. Root validates allowed flags by program/mode before
execution; retain original argv separately in the execution bundle.

Artifact = {role, format, artifact_ref, sha256, size_bytes, completeness}.
completeness is complete/partial/unknown. Format names are the actual formats
listed below. sha256 is a lower-case64hex digest and size_bytes is an integer>=0.
Acquisition supplies capture completeness, distinct from grammar validity.

Locator = {artifact_ref, record_ordinal, line_start, line_end, byte_start, byte_end}.
record_ordinal is integer>=0 or null. Lines are one-based inclusive or both null;
bytes are zero-based half-open or both null. Decoders must not invent offsets.
FieldInput = {locator: Locator, field: string}. This identifies the exact field
used, including a native tag; it is internal provenance, not model-facing prose.

Value = {value, state, basis, unit, inputs, native_token}.
value is finite int/float or null; bool is never a number.
state = present/missing/not_measured/failed/truncated/incompatible/invalid.
Only present has a number. basis = native_reported/model_header/derived/native_prediction.
unit = count/nt/column/bit/bit_per_position/inverse_bit/fraction/second/MB/byte/
       log2_odds/dimensionless/index/expected_count.
inputs is a list of FieldInput; native_token is original string or null. A native
printed zero stays present. Missing native tokens do not silently become zeros.

Issue = {stage, code, severity, artifact_ref, record_key, field}.
stage = format/extraction/association/validation/calculation;
severity = error/warning/information; final three fields are strings or null.
Each owned module declares its finite ISSUE_CODES and CHECK_NAMES sets; root
will import their union for result validation. Codes name concrete failures,
never arbitrary native prose. Useful siblings survive a malformed record.

Root will provide these exact helpers in infernal_preparation_schema.py:

    locator(artifact_ref, record_ordinal=None, *, line_start=None, line_end=None,
            byte_start=None, byte_end=None) -> Locator
    field_input(location, field) -> FieldInput
    value(number=None, *, state=None, basis="native_reported", unit="count",
          inputs=(), native_token=None) -> Value
    issue(code, *, stage="extraction", severity="error", artifact_ref=None,
          record_key=None, field=None) -> Issue
    record_key(artifact_ref, kind, ordinal) -> str
    new_sheet(operation, artifacts) -> Sheet
    new_calculations(operation, parameters) -> Calculations
    check(name, outcome, inputs=()) -> {check, outcome, inputs}
    validate_common_sheet(sheet) -> None  # raises ValueError for invalid envelope

record_key deterministically uses artifact_ref + "#" + kind + "/" + decimal
ordinal; no names are used for identity. Check outcome is pass/fail/unknown/
not_applicable. Parser-specific complete-record validation belongs to its owner;
validate_common_sheet validates only the common shape/finite values, not scientific
correctness. Invalid API arguments raise ValueError/TypeError. Bad native content
returns structured issues and retained useful records, not an invented result.

Payload = {artifact: Artifact, content: str|bytes}. Input/output role maps are
ALWAYS dict[str, list[Payload]], even with one item. This removes the proposal's
single-or-list ambiguity. No independently sorted inputs are joined.

Sheet = {schema:"infernal_preparation_sheet_v1", operation, artifacts,
         input_records, output_records, native_rows, associations, issues}.
artifacts is a list[Artifact]; records and issues are lists. Model records use
the exact shape below. Other rows use the closed family shapes below.
Association = {relation, input_keys, output_keys, status} with relation
built_from/calibrated_from/converted_from/fetched_from/indexed_from/generated_from/
inspected, lists of actual record keys, and status validated/unresolved/conflicting.
No association can be validated from name equality alone without checking native
record context, selected operation and expected population/order.

Calculations = {schema:"infernal_preparation_calculations_v1", operation,
                parameters, rows, issues}.
rows = [{record_key, components, checks}], components is a module-declared closed
map of names→Value, checks is a list of the check shape above. Each owner exports
COMPONENT_NAMES (frozenset) and ROW_FIELDS (mapping kind→frozenset of exact keys).
These are data validation declarations, never executable scoring expressions.

## Exact model handoff, owned by A

extract_infernal_models(content, *, artifact, format, engine_version=None)
returns ModelExtraction = {artifact, format, records, issues, population_complete}.
population_complete is true only for a complete capture with valid complete
grammar and decoded record boundaries. Opaque formats have no invented model
records and population_complete=false. A emits artifact-level issues for their
known limits. Opaque output itself can still be a successfully acquired artifact.

ModelRecord = {
  kind:"model", record_key, locator, format, writer_version, model_type,
  name, accession, description, alphabet, content_validation,
  fields, flags, null_background, calibration, efp7gf, filter_hmm, topology,
  source_fields
}.
model_type = cm/hmm; textual attributes are native strings or null.
content_validation = parsed_headers_and_boundaries/partial/invalid.
fields has EXACT keys CLEN,W,NSEQ,EFFN,STATES,NODES,CKSUM,GA,TC,NC with Value cells.
Units: CLEN/W nt, NSEQ/EFFN/STATES/NODES count, CKSUM dimensionless, GA/TC/NC bit.
Missing fields are explicitly missing cells, including unavailable fields in HMM.
flags has EXACT RF,CONS,MAP keys with actual native string or null.
null_background is list[Value] with unit log2_odds in native alphabet order;
these are not normalized probabilities. source_fields has date:list[str],
commands:list[str], other_headers:list[{tag:str,tokens:list[str]}].

calibration has EXACT keys ECMLC,ECMGC,ECMLI,ECMGI; values are null or {
  algorithm, locator, lambda, mu_orig, mu_extrap, calibration_dbsize_nt,
  random_hit_count, tail_probability_mass
}.
All six numerical fields are Value. Algorithm correspondence:
ECMLC→cm_local_cyk, ECMGC→cm_glocal_cyk, ECMLI→cm_local_inside,
ECMGI→cm_glocal_inside. lambda inverse_bit; mu values bit; dbsize nt;
hit count count; tail mass fraction. Preserve native tokens/precision.

efp7gf is null or {locator, location:Value, scale:Value}; location bit,
scale inverse_bit. Do not conflate it with a CM algorithm or filter STATS row.
filter_hmm is null or HMMHeader = {
  locator, writer_version, name, accession, description, alphabet, fields, stats
}.
HMMHeader.fields has EXACT LENG,MAXL,NSEQ,EFFN,CKSUM keys (Value cells; first two
nt, next two count, last dimensionless).
stats is list[{locator, mode, algorithm, location:Value, scale:Value}], retaining
actual native mode/algorithm tokens (e.g. LOCAL/FORWARD); location bit and scale
inverse_bit. No algorithm association is inferred from array position.
For a standalone HMM, model_type=hmm and filter_hmm contains this actual header;
CM-only fields stay missing. The name does not claim it was a CM's filter.
topology has EXACT base_pair_nodes,bifurcation_nodes,total_nodes,total_states,
all Value count cells. Values are decoded facts or missing, never copied from
a model name or file count. A supplies whole CM+filter record locator and exact
filter locator separately. A name/accession is a checked attribute, not identity.

Format enum for model artifacts: infernal_cm_ascii, infernal_cm_legacy_ascii,
infernal_cm_binary, hmmer_hmm_ascii, infernal_ssi, infernal_i1f, infernal_i1p.
Other role formats: stockholm, fasta, pfam, afa, a2m, clustal, phylip,
infernal_stdout, infernal_stderr, infernal_calibration_hfile,
infernal_calibration_sfile, infernal_calibration_qqfile,
infernal_calibration_ffile, infernal_calibration_xfile,
infernal_partition_scores, infernal_commands, infernal_trace, key_file.
Do not select formats by filename or resource label.

## Public pure functions and sheet rows

A implements the four exact A signatures from work246 section2. The populate
function receives role maps above. Models use role models; optional keys role
keys; supplied index role ssi. Converted/fetched outputs use converted_models,
converted_hmms,fetched_models; press roles i1m,i1i,i1f,i1p; index role ssi.
stdout/stderr roles identify corresponding retained output. A's key_request row
keys are kind,record_key,locator,requested_key,request_ordinal,
matched_input_model_keys,output_model_keys,match_kind,outcome. Match/outcome enums
are work246 section7. artifact_operation keys are kind,record_key,locator,
operation,artifact_refs,values,content_validation. Its values keys are
model_count,indexed_name_count,indexed_accession_count,byte_count; cells absent
from native output remain missing. content_validation=parsed/opaque_header_only/
partial/invalid. Validated output format and key/index findings belong to checks.
A components: input_model_count,output_model_count,requested_key_count,
satisfied_key_count,missing_key_count,ambiguous_key_count,output_artifact_count,
output_byte_count. No score masquerades as support for biological function.

B implements its six exact signatures from work246 section2, using role maps
above. Model roles models/calibrated_models/built_models; input alignment role
alignment; processed_alignment/refined_alignment are distinct output roles;
sidecar roles hfile,sfile,qqfile,ffile,xfile,partition_scores,commands.
model_order in sidecar parsing is ordered list[ModelRecord], never names alone.

B's nonmodel rows have exact common keys kind,record_key,locator,model_keys,
identity,values,series. model_keys is list[str]; series is empty except full
calibration/partition arrays. identity is a closed map per kind:
build:{native_index,name,description};
calibration:{algorithm,source};
calibration_series:{algorithm,series_kind,model_ordinal};
resource_estimate:{estimate_kind,name};
partition:{partition_index,partition_count,algorithm,model_ordinal};
model_statistic:{native_index,name,accession,model_family,algorithm,mode}.
Nullable attributes stay null. Do not infer a model key from an unmatched name.
Native row values, all Value cells, are closed per kind:
build: nseq,eff_nseq,alignment_length,consensus_length,base_pairs,bifurcations,
       cm_relative_entropy,hmm_relative_entropy;
calibration: lambda,mu_orig,mu_extrap,calibration_dbsize_nt,random_hit_count,
             tail_probability_mass;
resource_estimate: predicted_seconds,predicted_mb,cpu_count,command_count;
partition: score_count,requested_megabases,total_chunks,partition_chunks;
model_statistic: nseq,eff_nseq,consensus_length,max_hit_length,base_pairs,
                 bifurcations,cm_relative_entropy,hmm_relative_entropy,
                 threshold_bits,evalue,pvalue,search_space_nt;
calibration_series: tail_probability_mass,lambda,mu_orig,tail_hit_count.
Fields irrelevant to a mode are incompatible/not_measured, not zeros.
series contains ordered {index:int,x:Value,y:Value} rows. Univariate score arrays
use x=score bits and y=not_measured. Preserve delimiters/series_kind distinctions
from work246; raw full sidecars remain retained independently.

B components: paired_consensus_fraction,paired_consensus_numerator,
consensus_length_denominator,mu_extrap_calculated,mu_extrap_residual,
actual_calibration_nt,partition_chunk_count,predicted_seconds,predicted_bytes,
effective_random_hit_count,score_at_evalue,score_at_pvalue,evalue_at_score,
native_conversion_residual,native_rounding_half_width.
parameters keys initially search_space_mb,evalue,pvalue,score_bits,
rounding_absolute_tolerance,requested_megabases,partition_index,partition_count.
Omitted optional parameters use explicit corresponding sheet facts or produce
missing; no guessed metadata. No artificial acceptance threshold. All formulas,
units and missing conditions are exactly work246 sections3,4,9. A's full model
calibration values are a separate source from rounded stdout, never overwritten.

C implements the two exact C signatures from work246 section2. models is the
exact ModelExtraction above; output is ONE Payload; trace is null or ONE Payload.
sheet input_records stores actual ModelRecords; output_records stores generated
sequence/alignment rows. No target-subject field is allowed.
generated_sequence keys: kind,record_key,locator,model_keys,origin,name,
description,sequence,alphabet,residue_sha256,sample_index,embedded_interval,
alignment_key,values. origin=generated_sample/generated_consensus;
embedded_interval=null or {start:int,end:int} (zero-based half-open);
alignment_key=null or actual generated_alignment record_key.
values: residue_count,canonical_count,gc_count,ambiguity_count,gap_count,
column_count. Case-preserving sequence is retained; uppercase residue digest
is a separate derived identity and never replaces sequence content.
generated_alignment keys: kind,record_key,locator,model_keys,origin,format,
sequence_keys,annotations,values. annotations has EXACT gf,gs,gr,gc keys with
ordered records {tag,value,name,locator,block_index,sequence_key}, preserving
repetitions and row/column associations. tag/value are original strings; name is
null for GF/GC; block_index is zero-based or null for GF/GS; sequence_key is an
actual generated_sequence key only after an unambiguous GS/GR association,
otherwise null. Each annotation's locator describes its actual native line.
values: row_count,column_count. Non-Stockholm annotations absent in that format
remain not_measured. Native trace is retained even before its decoder exists.
C components: residue_count,canonical_count,gc_count,ambiguity_count,
gc_fraction_canonical,gc_denominator,gap_count,column_count,gap_fraction,
row_count,expected_sequence_count,actual_sequence_count.
parameters={} initially: composition formulas have no tunable assumptions.
Expected counts derive only from verified operation settings and model population.

## Verification and production consumers

Use work246's retained actual artifacts and NATIVE_EVIDENCE_001.json. Preserve
their bytes and receipts. Tiny additional native examples may be created only
through existing local_jobs with20GiB RAM/4GiB scratch and no wall cap; no install,
network/HPC, opaque shell or new submission is needed for these pure modules.
Own numerical tests must check independently known numbers, malformed/partial
populations, repeated identities, absent metadata, saved-sheet recalculation,
and no subprocess/network/model calls by extraction or calculation. Test A's
real ModelExtraction in B/C before handoff. Explicitly list unobserved modes.

Root's worker dispatch calls these exact populate/calculation functions on a
captured selected invocation. Root's preparation views select closed requested
numerical cells and actual artifact references; NativeInfernal supporting results
and authenticated return handlers carry them through the existing results→
scientific_process→annotation boundaries without creating search/alignment
observations. Exact current consumers are enumerated in work246 section10; root
must read their complete affected paths before changing them. Scientific
native_infernal_job_v1 validation remains unchanged. Preparation gets its own
explicit job/plan/bundle/capture discriminator under the existing episode types.

No pure-module handoff counts as full production integration. Native rc0, capture
completion, successful parsing and satisfaction of the original practical job
are separate facts. Missing fetch keys can fail the requested job with rc0.
Generated sequences remain generated samples. Forecasts stay predictions;
calibration statistics and file/index creation do not earn scientific confidence.
