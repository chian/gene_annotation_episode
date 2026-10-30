# Comparative signal component: paired source extraction and numerical sheet

Current adopted goal GOAL_VERBATIM.txt controls. Parent reviewed original YeaG
Results sec2/sec5, Methods sec9/sec10/sec12/sec17, original Fig3/Fig6 images,
complete supplement text projection and complete retained case report/fields.
Then reread the complete mandated authority set/current A105 sheet/contracts and
latest adopted goal last before this component proposal. Exact percentages are
relative anti-His signals, not known molar amounts or molecular activity rates.

## Sheet meaning, example and scientific limits

Separate deletion-background WT/variant complementation strains are the source
arrangement. The reference for protein signal is tagged plasmid WT YeaG. This
is distinct from a physiological WT/empty-vector reference. The paper reports
K116A64%,R232A48%,K426A100%,Y382Stop96%; Fig3C prints K426A1.12. Do not average
those representations or infer independent assays. Fig3 growth n/SD does not
populate band-signal ratio uncertainty. Fig6 survival has a separate variant roster.

Common experimental comparability components: reported_ratio r,
difference_from_reference=r-1, log_reported_ratio=ln(r). These are alternative
representations of the same operand, not multiplied independent proofs. r may
supply a later applicable calibrated amount-response model; it is not itself
an overall reliability multiplier. Actual amount-adjusted functional effect and
source evidence remain unavailable without calibration, phenotype-response and
uncertainty. Preserve useful partial numerical components.

For K116A: r=.64,r-1=-.36,ln(r)=-.4462871026284195. For K426A: r candidates
{1,1.12}, difference candidates{0,.12}, log candidates{0,.11332868530700327};
point null with representation-conflict status. Candidate min/max are not a CI.
Absent means null; zero signal is not a zero molar amount or detected exact zero.
No target correspondence or annotation aggregation is implemented.

The source-rate correction model must not score growth, abundance or static
binding as a molecular turnover rate merely because numbers can be supplied.
Such endpoint/model incompatibility leaves dependent rate-model cells unavailable;
it does not stop an episode or erase raw source operands.

## Shared code interfaces and disjoint ownership before delegation

Fresh percentage-reader worker owns ONLY new literature_ratio_reader.py and
 tests/test_literature_ratio_reader.py. Synthetic fixtures only; no paper/packet.
read_jats_relative_percent(source,*,section_id,paragraph_index,expected_subject,
                          variant,reference_literal)
source exact source_ref,artifact_ref,xml,representation(primary_jats|synthetic_fixture).
Select unique sec ID, zero-based direct-child p index; preserve inline text and
exclude embedded captions/tables. This handles JATS paragraphs without IDs.
Finite supported syntax NUMBER% (source label containing exact standalone variant)
followed later in the same comparative sentence by 'of REFERENCE_LITERAL'.
Subject literal must be in selected paragraph. Reject ambiguity, inequalities,
unsupported percent syntax, wrong reference/subject/selectors. No model numbers.
Return {version:relative_signal_extraction_v1,subject,variant,reference,
observations:[{value:percent/100,origin:reported|synthetic,source:{source_ref,
artifact_ref,representation,section_id,paragraph_index,paragraph_text,expression,
expression_start,expression_end},uncertainty:{kind:unreported,magnitude:null,
count:null,sampling_basis:unspecified}}]}.
Aliases of the same literal observation preserve source selectors; equal values
in different locations do not establish independence. Use finite JATS declaration
and direct-text helpers from existing literature_prose_reader, no network.

Fresh calculator worker owns ONLY new literature_ratio_calculations.py and
 tests/test_literature_ratio_calculations.py. Synthetic fixtures only.
populate_relative_signal(observations) accepts finite list of exact rows
{value:number|null,origin:reported|synthetic|visual_transcription,source:dict,
uncertainty:{kind:unreported,magnitude:null,count:null,sampling_basis:unspecified}}.
Source may be native reader locator dict, or explicit retained visual transcription
locator {source_ref,artifact_ref,representation:retained_visual_transcription,
original_source_ref,original_artifact_ref,printed_label,image_region}.
Caller validates physical custody/declared comparison; calculator validates finite
values>=0, exact origin/uncertainty, consistent duplicates by canonical source dict
(same source identity with differing values -> conflict). Never infer independence.

Return {version:relative_signal_sheet_v1,scope:reported_relative_signal,
observations,cells,independent_preparation_count:null,annotation_credit:null}.
Cells exactly reported_ratio,difference_from_reference,log_reported_ratio,
calibrated_amount_ratio,amount_adjusted_effect,source_profile_log_ratio,
source_signed_index. Each cell value:number|null,value_candidates:[numbers],unit
fraction|dimensionless,status:populated|conflicting|unavailable,formula,origin
reported|synthetic|visual_transcription|derived|proposed,unavailable_reason,
conditional_on:[]. Multiple distinct received positive values -> conflicting
with transformed candidate set, no midpoint. Missing observations or any null
observation leaves dependent point unknown; retain known candidates. r=0 retains
reported native0 but log unavailable(no log pseudocount). No calibrated amount
or effect/index from signal alone; reasons amount_calibration_unreported,
response_model_unreported,uncertainty_model_unreported. No paper quality grade.

Root owns new runtime repository, binding/service/prompt integration, actual source
examples, model-parent presentation and final verification. Existing other-session
tool-grader files and permanent research records are untouched. The primitive
readers/calculators have no loop, state write, controller or model call.

## Explicit retained visual representation for the runtime operation

A received source artifact may contain JSON {version:relative_visual_signal_v1,
subject,variant,reference,observations:[{printed_label,original_source_ref,
original_artifact_ref,image_region:[x0,y0,x1,y1]}]}. This is a retained visual
transcription, not OCR, original densitometry, graph digitization or a measured
molar ratio. The root validates its lineage and actual received original image
artifact, then parses the printed decimal label deterministically. Its origin
visual_transcription survives the typed boundary. No model-supplied numeric
argument is accepted by the population operation.

The final typed cells retain comparison identity, original source references,
origin set, candidate set, representation-conflict status and unknown uncertainty.
A scientific parent can request a subset; forwarding does not expand private cells.
The existing ordinary LiteratureEpisodes and method_loop own all decisions.
