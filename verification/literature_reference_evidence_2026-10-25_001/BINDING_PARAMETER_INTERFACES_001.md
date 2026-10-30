# Binding-parameter extraction and source numerical components

Current GOAL_VERBATIM.txt controls. Parent independently read the retained original
article BioC projection (article_clean.txt, complete 440 lines), original Table3
image, and full source-worker SOURCE_AND_COMPONENTS_001.md for IscR2013. Parent
then reread the complete authority set/current A105 sheet/native+assay contracts
and adopted goal, with current user instructions last. Truncated initial source
read was replaced by complete consecutive portions. No second paper was opened.

This additive correction qualifies current A105 sheet section8: the self competitor
is 32 ±2 nM. The table footnote describes SD from a logistic fit to averaged
titrations, not an identified sample SD/SEM of individual fitted IC50s. The literal
>510 is preserved; its limit mechanism is unstated. These are IC50s, not Kd.

## Experiment, numerical cells and combination

E. coli apo-IscR competition with 5nM labeled hya tracer; unlabeled competitor
changes DNA within each protein's series. WT/E43A are separate preparations,
not a protein mixture; labeled tracer and competitor coexist. WT22nM and E43A20nM
are unequal nominal protein inputs. Do not import structural 3CA/tag/truncation
into the binding preparation. Same-protein self/mutant competitor ratios retain
the common protocol; cross-protein ratios require the unequal-input qualification.

Numerical components: reference_parameter, test_parameter, reference_reported_spread,
test_reported_spread, reference_relative_spread, test_relative_spread,
native_parameter_ratio=test/reference, log_native_parameter_ratio=ln(test/reference),
source_profile_log_ratio and source_signed_index. Ratio/log are alternative forms
of the same contrast; not independent proofs or multiplied quality factors.

For WT hya7CtoG/hya, threshold arithmetic >510/32=>15.9375 and log>2.768674822919.
For E43A, point17/11=1.545454545455 and log=.435318071258. WT spread2/32=.0625.
Across-protein log contrast is eWT-eE43A (>2.333356751661 at these printed inputs),
but is not an intrinsic affinity change or supported correction for protein input.
Uncertainty combination requires an applicable joint model including shared
denominators/covariance. Fit-to-average spread alone does not supply that model.

Outputs explicitly distinguish reported-limit arithmetic from parameter
identification and confidence bounds. The latter two are unavailable here;
unknown true-parameter uncertainty is not a zero denominator variance. Missing
spread, exact n, preparation independence, limit mechanism and covariance stay
unknown. No likelihood/index is implemented in this first descriptive path;
return reason binding_observation_model_unimplemented, never fabricate a score.
That required statistical extension remains unfinished work, distinct from real
source inputs that were not reported. Keep all native partial cells.

## Fresh reader worker: exclusive ownership

Own ONLY gene_annotation_episode/literature_binding_reader.py and
tests/test_literature_binding_reader.py. Synthetic fixtures only; no papers/packets.
Export read_binding_parameter_table(source,*,expected_subject,expected_state,
 expected_experiment,reference_ligand,test_ligand,parameter_kind).

Source exact keys source_ref,artifact_ref,text,representation. representation is
retained_visual_transcription|primary_table|synthetic_fixture. text is strict JSON
binding_parameter_table_v1 with exact keys version,table_id,parameter_kind,unit,
uncertainty_basis,minimum_experiment_count,rows. parameter_kind ic50|reported_hill_kd;
unit nM|uM|mM (Unicode µM/μM aliases allowed), canonical nM. uncertainty_basis
fit_to_averaged_curve|between_independent_fitted_parameters|unknown. Count null
or positive integer is a minimum reported experiment count, never exact n or
independent preparation count. Do not invent a spread type beyond the input basis.

Each row exact keys subject,state,experiment,ligand,expression,locator. All labels
nonempty strings. expression is a complete source token: finite positive POINT,
POINT ± NONNEGATIVE_SPREAD, >POINT, >=POINT, <POINT, <=POINT (Unicode ≥≤ allowed),
or n.d. Unsupported/approximate/range/malformed tokens rejected; censoring cannot
carry a spread. No partial-token or nonfinite/underflow values. Unit is table unit.
Locator primary_table|synthetic_fixture: exact {row_index:nonnegative int,column:
nonempty string}. Retained visual locator exact {original_source_ref,
original_artifact_ref,image_region:[x0,y0,x1,y1]}; positive integer-coordinate box.
Host adapter later validates original image custody/dimensions. Reader proves
retained numerical tokens/coordinates, not pixel interpretation or source truth.

Select rows matching all requested subject/state/experiment/ligand/kind; preserve
multiple distinct locations and conflicting representations, do not choose first.
Return {version:binding_parameter_extraction_v1,parameter_kind,unit:nM,
uncertainty_basis,minimum_experiment_count,reference_rows,test_rows}.
Each normalized row exact {value:number|null,relation:eq|gt|ge|lt|le|unreported,
reported_spread:number|null,origin:reported|visual_transcription|synthetic,
source:{source_ref,artifact_ref,representation,table_id,row_index,locator,expression},
subject,state,experiment,ligand}. value and spread normalized nM. n.d.=unreported
with value/spread null. Missing arm empty list, no fabricated row. Preserve raw
expression and source position, never merge independent rows by equal value.
Use ExperimentalContractError(code,field), no state/model/network/calculator calls.

## Fresh calculator worker: exclusive ownership

Own ONLY gene_annotation_episode/literature_binding_calculations.py and
tests/test_literature_binding_calculations.py. Synthetic fixtures only.
Export populate_binding_contrast(extraction), consuming exact normalized output
above. Validate kinds/units/labels/relations/finite positive values/spreads and
preserve source identity. Never silently interpret ic50 as Kd.

Return {version:binding_parameter_sheet_v1,parameter_kind,unit:nM,reference_rows,
test_rows,uncertainty_basis,minimum_experiment_count,independent_preparation_count:null,
cells,annotation_credit:null}. Cells exactly ten components named above. Each has
value:number|null,relation:eq|gt|ge|lt|le|unreported,unit:nM|fraction|dimensionless,
status:populated|reported_limit|unavailable|conflicting,formula,origin:derived|
proposed,unavailable_reason:string|null,bound_kind:reported_limit_arithmetic|null,
confidence_bound:null,parameter_identification_bound:null.

Source point operands carry eq, reported limit operands literal relation and
reported_limit status. Reported spread and spread/abs(point) only for unique eq
operand with nonnull spread. Exact duplicate source/source-artifact/location/row
and expression collapses; same physical locator differing parsed values remains
conflict. Any multiple nonidentical surviving rows in an arm -> ambiguous arm,
partial unaffected arm survives, dependent point/limit unknown (no averaging).

Ratio/log supported finite cases: eq/eq =>eq; gt|ge|lt|le divided by eq =>same;
eq divided by gt|ge|lt|le =>inverted lt|le|gt|ge. Two censored operands unavailable
two_censored_operands_unsupported; this is a finite model limitation, not an
invented global [0,infinity] result. Unreported/missing/conflicting operands
retain partial components. Require positive values and finite result; reject
nonfinite/underflow calculations specifically. Compute log ratio robustly as
log(test)-log(reference) independently of ratio overflow. Actual equal source
measurement can yield descriptive ratio1/log0 without establishing independence.
Profile/index unavailable binding_observation_model_unimplemented. No interpretation,
private loop, source access, default covariance, grade or controller observation.

## Root integration ownership and remaining work

Root owns additive source-review provenance, exact primary retained visual input,
repository/binding/prompt integration, typed return and reconstruction checks.
Readers parse source numbers; aspect-specific episode interpretation establishes
subjects, experimental relationships and applicable comparisons with source
witnesses. Integration must preserve raw limit semantics/uncertainty basis and
source-original image lineage. No manual received-cell injection or extra report
model call. Preserve existing live_pin_004 and live_yeag_004 unchanged.
