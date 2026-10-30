# hmmstat numerical component — root workload265 /261H1

Implemented pure ports are parse_hmmstat_summary, populate_hmmstat_sheet and
calculate_hmmstat_components. The first two are in hmmer_statistics_data.py;
the calculator and explicit native_hmmstat_parameters helper are in
hmmer_statistics_calculations.py. No execution, resource selection, scientific
observation, annotation scoring, local yield or episode behavior changed.
Production execution/capture/library/result-return integration is still required.

## Exact data boundary

The H1 contract remains unchanged. Operation has program=hmmstat,mode=summary,
engine_version and empty settings. Payload maps use roles -> lists of
{occurrence,content:bytes}; M1's exact eight-field occurrence is retained. One
input models artifact and one output summary (or actual stdout) are required.
Identical stdout/summary aliases remain separate occurrences but are parsed once.
The full supplied M1 envelope is verified by pure re-extraction of supplied model
bytes; a changed token/value/extraction identity cannot silently replace it.

parse_hmmstat_summary returns schema=hmmer_statistics_summary_v1, occurrence,
rows,population,issues. Each row has record_key,locator,tokens,values,states.
Locator is artifact_ref,record_ordinal,byte_start,byte_end,line_start,line_end;
byte intervals are zero-based half-open and lines one-based inclusive. Record
key is occurrence_id#summary/ordinal. Values/states have exactly ten fields:
idx,name,accession,nseq,eff_nseq,M,relent,info,p_relE,compKL. tokens preserves their
original ten string values. Counts are integers; other numeric fields finite
numbers. Missing accession '-' is null/missing. Native -1 counts are null with
native_missing_sentinel state; nan/inf are null/nonfinite with original tokens.
Malformed rows retain tokens and null invalid fields. Earlier valid rows survive.

population has decoded_count,complete,state(decoded/partial/invalid). Empty
complete bytes mean zero parsed rows; absent output means no summary object.
Native nonfinite statistics do not erase a known row population. Wrong size/hash,
invalid identity, malformed rows or partial capture remain explicit issues.

Sheet fields are exactly schema=hmmer_statistics_sheet_v1,operation,
artifact_occurrences,model_extraction,summary,native_rows,associations,issues.
summary retains extraction schema,occurrence,population; its rows are stored only
in native_rows. model_extraction retains every native probability/header/position
without replacing data by a mean. Associations have native_record_key,
model_record_keys,state(validated/conflicting/unresolved),fields. Native idx joins
original model ordinal, then NAME,ACC,LENG,NSEQ,EFFN are checked (printed EFFN uses
0.0051 rounding allowance). Repeated labels at different ordinals remain distinct.
Duplicate/nonsequential idx, mismatched metadata, modified extraction and bad
summary source identity cannot acquire a validated association.

## Exact calculation boundary

Calculator envelope is schema=hmmer_statistics_components_v1,operation,
parameters,model_components,rows,checks,issues. Parameters are explicit
background,length_probability,probability_tolerance,summary_rounding_tolerance.
Finite JSON is required; invalid finite parameters leave dependent values
unavailable. No parameter is silently reacquired from a native executable.

model_components is the complete M1 calculator result. Each tool-specific row
has record_key,native_record_keys,components,positions,composition,
native_comparisons. components retains mean_match_entropy,
mean_match_relative_entropy,sequence_count,effective_sequence_count,
effective_sequence_ratio,background_entropy,mean_match_information,
occupancy_sum,entry_occupancy_sum,weighted_emission_relative_entropy,
mean_entry_transition_term,position_relative_entropy,composition_weight_sum,
composition_relative_entropy. Every number uses {value,state,unit,inputs}.

positions retains every position's occupancy,relative_entropy,entry_transition_term.
composition retains weights/probabilities as ordered {symbol,component} rows.
native_comparisons retains native_record_key,field,native_value,difference,
native_parameters_match. Difference is calculated minus original native value;
it never overwrites that value. Inputs name exact model fields, positions,
distributions and parameters; denominators are retained separately. No uncertainty
estimate is manufactured for these deterministic calculations.

The exact source formulas and denominator populations are in H1. Complete native
functions hmmstat.c, modelstats.c's MeanMatchInfo/MeanMatchRelativeEntropy/
MeanPositionRelativeEntropy/CompositionKLD, p7_hmm_CalculateOccupancy and
p7_AminoFrequencies were read. The implementation follows the actual information
sign and transition formula, including the source's MM log inside the MI term.
Raw probability vectors remain unnormalized. Only the derived weighted composition
is normalized, by its separately stored actual mass. Zero-weight logarithmic
terms contribute0; positive weight with required log0 is nonfinite. M<2 leaves
position-relative entropy unavailable but preserves other computable statistics.

native_hmmstat_parameters('3.4',alphabet) explicitly supplies the native versioned
amino constants or uniform DNA/RNA values and p1=350/351. The calculator itself
does not call this helper to fill omitted parameters. Native agreement applies
only to matching parameters/version; alternate selected parameters remain
recalculable with native comparison not_applicable rather than a false defect.

## Executed verification and numerical examples

check001/receipt.json records34 passing tests in0.35s, through existing local_jobs
with20GiB RAM/4GiB scratch/wall_seconds=null. Relevant source hashes matched
before/after and were rechecked against current files. examples001/receipt.json
records successful generation of four full sheets/calculation files plus
examples/REPORT.json and exact native artifact hashes. No native HMMER command
was regenerated for this numerical component; these are259's retained outputs.

| Native example | Statistic | Native printed | Independently calculated |
| --- | --- | ---: | ---: |
| DNA | mean match relative entropy |1.01|1.0074921672642938|
| DNA | mean match information |1.01|1.0074865751199864|
| DNA | position relative entropy |0.89|0.8906422345697793|
| DNA | composition divergence |0.01|0.006355823477963574|
| Protein | mean match relative entropy |4.38|4.376066019802603|
| Annotated protein | position relative entropy |2.43|2.430431773646602|

All four protein/DNA/RNA/annotated native pairs agree at native printed precision.
Tests additionally cover identical model occurrences, wrong labels/counts/digests,
altered M1 extraction, repeated native idx, empty/missing/partial output, unknown
binary decoding, sentinel/nonfinite values, changed parameters under forbidden
I/O/network/subprocess sentinels, missing background, invalid p1, single-position
denominator, zero-log input, incomplete models and unknown native version.

Limits: HMMER2/binary body decoding is unavailable through M1; actual produced
summary values remain retained without invented model-body equivalence. Native
float/ASCII rounding is preserved. These tests do not establish library selection,
production job execution or typed episode returns. No evidence-axis or W05 work
was performed. The original objective/all16 principles and H1 were reread after
source study and before this handoff. Earlier permanent records remain unchanged.
