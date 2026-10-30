# First source-only A106 implementation: fixed paired interface

Adopted goal and latest scope govern; no target correspondence or W05. Root has
independently read Cas2 original scientific text/figures and completed the FULL
post-paper reset including current A105696lines,A106sheet003,reader_io003 and
latest user direction LAST. CAS2_PARENT_REVIEW001 records the case conversion.
Previous turn was progress. No additional paper is opened for these workloads.

## Scientific meaning and printed example

Cas2 is a cas-free BL21-AI reconstitution/variant-replacement case, not a native
WT/deletion/complement triple. Its PCR endpoint lacks quantitative calibration.
Its restoration/effect/overall source numbers remain null. Selected spacer-list
fractions do not become rates or reliability. Source design and numerical
availability are required interpretation fields, not categorical grades.

For a genuinely matched, calibrated nonnegative ratio-scale endpoint:
D=W−K; theta=(W−K)/(W+K); raw=(R−K)/(W−K);
r=clip(1−abs(R−W)/abs(W−K),0,1);
C=min(A_reference,A_restored)/max(A_reference,A_restored), for an explicitly
nominated nuisance amount comparison outside the intended change;
Ipert=clip(1−B_pert/abs(W−K),0,1);
Irest=clip(1−B_rest/abs(R−K),0,1); I=min(Ipert,Irest);
q_reference=s*theta*r*C*I. Each exponent1. This is the explicit proposed
SOURCE-ONLY conventional point index; no H term is set to1 or calculated.
It is not probability/annotation credit. Missing operands remain unknown.

Synthetic W100,K20,R90,A_reference100,A_restored90,B_pert8,B_rest7 gives
D80,theta2/3,raw=r.875,C=.9,Ipert=Irest=I=.9,q_reference=.4725.
These are not Cas2 measurements. Same W/K/R are reused by the formulas, not
independent proofs. Overshoot raw is unrestricted; agreement r is clipped.

## Pure calculator workload — fresh worker1 owns only new files

gene_annotation_episode/literature_perturbation_calculations.py and
tests/test_literature_perturbation_calculations.py.
Export VERSION=a106_source_restoration_v1,PRIMITIVE_ORDER,COMPONENTS,
populate_source_restoration(inputs).

Exact inputs:
{values:{W,K,R,A_reference,A_restored,B_pert,B_rest},
 measurement_keys:{same7},endpoint_unit,exposure_unit,design,
 measurement_status,same_endpoint_scope,amount_role,orientation,origin}.
Numbers finite nonnegative|null; bool forbidden. measurement_keys strings|null;
same nonnull key requires same values and unit; do not infer independence.
endpoint_unit enum events_per_100000_cells|fraction|CFU_per_mL|minutes|per_min;
exposure_unit enum molecules_per_cell|normalized_signal|fraction|mg_per_mL.
design native_deletion_restoration|selective_perturbation_restoration|
cas_free_reconstitution|variant_replacement|other_explicit|unknown|conflicting.
measurement_status validated_ratio_scale|qualitative_only|unknown|conflicting;
same_endpoint_scope yes|no|unknown|conflicting;
amount_role nuisance|intended_change|unknown;
orientation +1|-1|null (int only);
origin reported|graph_derived|derived|synthetic.

Return version,inputs,primitive_order,cells.
Cells in order reference_endpoint,perturbed_endpoint,restored_endpoint,
perturbation_difference,symmetric_effect,restoration_fraction_raw,
restoration_agreement,amount_comparability,perturbation_isolation,
restoration_isolation,effect_isolation,reference_restoration_index,
reference_index_lower,reference_index_upper.
Each exact value,unit,status,formula,origin,unavailable_reason,conditional_on.
Native endpoint cells use endpoint_unit; other numeric cells dimensionless exceptD.
Only validated same-endpoint data can fill derived endpoint contrasts. Missing
W/K leaves those unknown. Restoration cells require the first2 explicit
restoration designs and W/K/R; other designs preserve native/two-arm cells but
restoration unavailable. Reusing one actual observation as W/K or R does not
establish distinct perturbation/restoration arms: dependent contrast/repair cells
unavailable with role_measurement_not_distinct, native values survive.
C only amount_role=nuisance; intended change is not a second nuisance penalty.
I requires actual supplied nonnegative B bounds, never defaults. Zero
denominators preserve explicit unknowns. Orientation needed only final index.
Final source point remains null unless every component it uses is identified.
Do not claim an exact zero product from an undefined factor. Native invalid
negative/bool/nonfinite/malformed fields raise ExperimentalContractError.

This first finite path does NOT accept joint uncertainty inputs; last2 bound
cells are null/joint_uncertainty_unreported, not infinite precision or a claim
that uncertainty work is complete. No SD/SEM/confidence/Cas2 PCR conversion,
necessity counterevidence or cross-experiment aggregation is implemented here.
Those remain required separate work. Index origin proposed; condition
source_restoration_convention. C/I convention outputs proposed; raw effects
derived. Use stable rational/intermediate arithmetic and explicit final range
failure, not preventable overflow, jitter or fabricated zero.

## Pure source-input worker2 owns only new files

gene_annotation_episode/literature_perturbation_inputs.py and
tests/test_literature_perturbation_inputs.py.
Exports perturbation_population_schema(),read_perturbation_inputs(arguments,*,read_source).
Reuse _Sources for actual literal witnesses and _json_source-style strict parsing,
including lexical numeric underflow. No network/state/episode/prompt/paper reads;
synthetic fixtures only. read_source(ref,representation)->{artifact_ref,content}.

Selected operation arguments exact:
{source_ref,data_source_ref,source_kind,literals,design,measurement_status,
 same_endpoint_scope,amount_role,orientation,interpretation_witnesses}.
source_kind primary_source|retained_extraction|graph_extraction|synthetic_fixture;
data_source_ref source|null. All enums as above; orientation literal int±1|null.
literals exact molecule,recipient,donor,experiment,reference_arm,perturbed_arm,
restored_arm,partner,endpoint,normalization,condition,intended_change, each
nullable exact existing witness{source_ref,representation,start,end,quote}.
interpretation_witnesses list exact witnesses; any nonunknown design/status/
scope/amount or nonnull orientation requires>=1actual witness. Custody does not
prove scientific interpretation. Return literals as {value:quote,witness}|null.

data_source_ref holds original UTF8 JSON exact:
{version:a106_source_measurements_v1,endpoint_unit,exposure_unit,origin,
 uncertainty_basis:unreported,measurements:{all7 roles}}.
Each role exact{value:finite nonnegative|null,measurement_id:nonempty string|null}.
Known value requires ID. Unknown value may retain ID but computed key=null.
Physical key full SHA256 compact sorted JSON ensure_ascii=False/allow_nan=False
over{source_ref,artifact_ref,measurement_id}; same ID is an explicit source
declaration, not an inferred equal-value match. Preserve raw entry and units.
Actual first-path data origin reported|graph_derived|synthetic; no forged model
numbers are operation arguments. This is an explicit retained-data boundary,
not an original gel/PCR calibration reader. Primary Cas2 has no data source.
qualitative_only cannot accept known W/K/R values: explicit
qualitative_endpoint_has_no_numeric_values. Other uncalibrated status preserves
native supplied points but cannot generate derived endpoint effects.

Return exact {version:a106_perturbation_inputs_v1,source_ref,source_kind,
data_source_ref,literals,design,measurement_status,same_endpoint_scope,
amount_role,orientation,interpretation_witnesses,primitive_order,values,
measurement_keys,primitive_observations,endpoint_unit,exposure_unit,
data_origin,uncertainty_basis,source_refs}.
Without data source values/keys/observations allnull; endpoint_unit=fraction,
exposure_unit=fraction are placeholder dimensional codes ONLY for unavailable
cells, never measured values; data_origin=null,uncertainty_basis=unreported.
Source_refs includes root and every directly read source; callbacks own actual
receipt/scope/page authorization. Reject malformed extra fields/duplicate JSON/
nonfinite/underflow/negative values/wrong units. Preserve partial source meaning.

## Root ownership after interfaces

Repository/storage, shared LiteratureEpisodes/WorkflowServices, typed
literature_perturbation_cells/requested_perturbation_components, separate recurring
aspect TASK, original-source negative and synthetic numeric examples, saved
replay, assembled tests/progress. Existing method_loop/controller/credit, original
case Store/live pin and other-session tool graders remain unchanged.
No new episode type, private loop, final aggregation or paper-as-overall-grade.
