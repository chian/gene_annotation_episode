# Source assay interpretation and correction handoff — increment003

Current adopted goal is GOAL_VERBATIM.txt. This is the next paired extraction /
numerical-sheet implementation, not another evidence axis or episode type.

## Scientific meaning and proposed prompt

For the selected experimental source, identify the actual assayed molecule,
organism/genotype/construct, preparation/system and condition from source-bound
literal labels. Interpret the measured endpoint and replacement/coexistence /
single-preparation arrangement through closed allowed answers, citing actual
source passages. Unknown labels/relations remain unknown. An exact quote
establishes source custody, not automatic correctness of an interpretation.

Identify q (reported net sample-minus-blank endpoint rate), g (a separately
quantified contaminating contribution), k (reported recovery ratio), E (assayed
molecule concentration), u/v (same-endpoint test/reference condition controls,
excluding the deliberately tested difference). Assign a numerical source span
only when it has that meaning. Missing inputs are null. No-inhibitor controls
are not blanks, purified protein is not measured zero contamination, and a
reported per-mg specific activity is not unnormalized q or molar E.

All arithmetic is deterministic. Parse exact literal numeric spans and their
units; q/g/u/v convert only within concentration-rate dimensions, E within
concentration, k is an explicitly reported dimensionless ratio. Do not convert
mass to molarity without the missing molecular amount relationship. The finite
first path accepts reported q; it does not infer q from an unlabelled trace.
Native raw sample/blank assembly remains a later targeted reader.

Numerical cells: net_rate(q),contaminant_rate(g),attributed_rate(q-g),recovery(k),
protein_amount(E),condition_test_rate(u),condition_reference_rate(v),
condition_response(u/v),corrected_activity((q-g)*v/(k*E*u)), full propagated
variance/SE/precision, conditional source S and proposed tanh(S/2). No extra
comparability or isolation multiplier after correcting the effect/uncertainty.
Missing model inputs preserve usable primitive and partial arithmetic cells.
The effect concerns the interpreted source endpoint; it is not function probability,
target transfer, reaction identity, final annotation credit or stopping authority.

## Shared contracts before delegated coding

New literature_assay_inputs.py and tests/test_literature_assay_inputs.py owned
ONLY by fresh input-reader worker. No primary papers/retained packets; synthetic
fixtures only. Root owns repository, binding/service/typed-return integration,
prompt changes, assembled tests and primary-source future integration.

Function assay_arguments_schema() returns tool JSON schema (REF allowed).
Function read_assay_inputs(arguments, *, read_source) returns detached dictionary:
{version:a105_assay_inputs_v1,source_ref,assay,primitive_order,values,
 primitive_observations,covariance,variance_status,distinct_residual_variance,
 observation_model,source_refs}. read_source(source_ref,representation) ->
{artifact_ref:str,content:bytes}. It is a caller adapter for already acquired
received sources; no network, parsing loops, state writes or controller.

arguments exact keys:
source_ref, assay, primitives, covariance_source_ref,
distinct_residual_variance, variance_status, observation_model, model_witnesses.

Literal witness exact keys source_ref,representation(original|text),start,end,
quote; start/end UTF8 bytes, quote exactly matches retained bytes (not decoded
character offsets). A literal field is witness|null; its value is quote, not an
unrestricted supplied summary. Assay exact keys molecule,organism,genotype,
construct,preparation,condition,intended_variable (each literal witness|null), endpoint,arrangement.
endpoint={value:oxygen_consumption|product_formation|substrate_depletion|
ligand_binding|transport_flux|growth|abundance|other_measured_endpoint|unknown|
conflicting,witnesses:[witness...]}; arrangement={value:single_preparation|
replacement|coexistence|not_applicable|unknown|conflicting,witnesses:[witness...]}.
Known answer requires >=1 witness; conflicting requires >=2. Unknown may have
witnesses or empty. Retain kind=source_interpretation explicitly.

primitives exact q,g,k,E,u,v each measurement|null. Measurement exact keys:
witness,number_start,number_end,unit_start,unit_end (offsets Unicode characters
WITHIN witness.quote). Numeric token has no arbitrary words, inequalities or ±;
point may be signed; unknown/censored values are not points. Reject a cut inside
a larger numeric token and source censor/approximation symbols or explicit
less/greater-than phrases; a threshold is not an observed point. unit token is read
from source, not supplied separately. q/g/u/v accepted uM/min,mM/min,nM/min and
explicit Unicode µ/μ aliases. E accepts uM,mM,nM with aliases. k accepts literal
fraction,dimensionless,1 or empty token (zero-length unit range) for reported
recovery ratio. Parse finite decimals/scientific notation and reject nonzero
underflow. Returned observations retain witness,raw numeric/unit tokens,value,
canonical unit,multiplier,role and deterministic measurement_key. The same exact
source measurement retains one measurement_key across roles. Equal numbers in
different anchors remain distinct, not independent. Reused measurements require
their identical covariance rows/columns after conversion whenever covariance is
supplied; missing covariance preserves arithmetic but cannot create a score. No new model call.

Source provenance callbacks validate actual receipt/scope/representation. All
witnesses must originate from the root source or a source explicitly referenced
by the argument, with root inclusion preserved in returned source_refs. Scientific
experiment linkage is the source interpretation, not inferred from common paper.

covariance_source_ref null or received source containing UTF8 JSON exact keys:
version=a105_primitive_covariance_v1,primitive_order=[q,g,k,E,u,v],
primitive_measurement_keys=[measurement_key for each of the six primitives],
primitive_units=[native unit token for each primitive],covariance=6x6 numbers,
origin=reported|derived|synthetic. Full 6 primitive ownership list, no covariance
when primitive missing. Validate exact key/order/unit/ownership; apply product
of primitive unit multipliers to each covariance entry. Reject nonfinite,
asymmetric/indefinite via existing calculator (repository responsibility).
This is a finite retained covariance boundary, not an original-paper covariance
reader. It may not infer independence from repeated representation or counts.

variance_status=known|estimated|unknown and observation_model=none|
known_normal_nonnegative_presence. Non-default status/model requires >=1 actual
model_witness. Retain assumptions as conditional interpretations, not empirical
proof from any matching quote. distinct_residual_variance is measurement|null,
unit per_min_squared|min^-2|min−2. This is already corrected-scale distinct
residual; do not infer zero when absent. Selected operation passes returned
values/covariance/status/residual/model to existing populate_corrected_activity.

Public failures use ExperimentalContractError(code,field). Schema validation is
closed, bool/nonfinite/numeric-point errors explicit. Preserve unknowns rather
than completing a source likelihood from unsupported ± or default covariance.

## Additional disjoint workloads

Fresh aspect-prompt worker owns ONLY new literature_assay_prompt.py and
 tests/test_literature_assay_prompt.py. Export ASSAY_TASK, a substantive recurring
source-interpretation instruction block. Root includes it in existing detailed
TASK. No papers/packets or runtime changes. The prompt asks the concrete endpoint,
subject/arrangement/control/denominator questions above, defines allowed answers
and scientific limits, and nominates exact source operands without model arithmetic.
It is not the full scoring sheet or a tool manual.

Fresh source worker owns ONLY verification/.../primary_yeag/ new files. Read the
original YeaG source PMC4664914 for corrected Fig3 recovery-growth vs Fig6 survival,
and apply required full post-paper authority reset before component proposals.
Deliver exact original-source measurement/context anchors, numerical operands,
scoring bearing and limits; no runtime or old-record edits. This is research for
a contrasting case, not implementation of A106 or target transfer. Root reviews
it with its own post-paper reset before interpretation/expansion.
