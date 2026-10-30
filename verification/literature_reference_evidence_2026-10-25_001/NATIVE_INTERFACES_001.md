# Source-native A105 increment: scope, cells and ownership

The current adopted GOAL_VERBATIM.txt controls. Post-paper parent reset completed
2026-10-25 for the original CsiD source and retained source-worker packet. The
full authority set was reread across the compaction boundary. Truncated attempts
at VERBATIM recovery and A105 section8 were repeated successfully. The original
source was read before this reset; no additional primary source is opened here.

## Numerical sheet revision

The native source route accepts a single reported measurement. It does not invent
reference/test arms. Quantity roles are specific_activity and apparent_km. The
native numerical cells are reported_value, reported_spread and
relative_reported_spread=spread/abs(value). The last measures the reported
spread relative to its point only; unknown ± meaning is not a coefficient of
variation, SEM, likelihood or probability. Separate quantity/analyte bindings
prevent mixing Km and rate or transferring uncertainty from another panel.

The existing source correction model remains a=(q-g)*v/(k*E*u), with primitive
order q,g,k,E,u,v and full explicitly supplied covariance. Its corrected effect,
variance, precision, known-normal source presence S and proposed tanh(S/2) are
scoring components. Missing operands remain null. A specific activity is already
normalized and cannot silently substitute for q (unnormalized rate), E or a
product-specific endpoint. Native CsiD has none of that complete correction
boundary, so the correction score remains unavailable while measured values
survive. No target transfer or final annotation credit is included.

## Reader interface (fresh worker ownership)

New literature_prose_reader.py and tests/test_literature_prose_reader.py only.
read_jats_quantity(source, *, section_id, paragraph_id, expected_subject,
                   quantity, analyte=None)
source exact keys source_ref,artifact_ref,xml (UTF8 str),representation
(primary_jats|synthetic_fixture). Return version a105_jats_quantity_v1,
subject,quantity,analyte,value,unit,uncertainty{kind,magnitude,count,sampling_basis},
origin,normalization,source{source_ref,artifact_ref,representation,section_id,
paragraph_id,paragraph_text,expression,expression_start,expression_end}.
quantity is specific_activity or apparent_km; analyte required only for Km.
Supported literal syntax is intentionally finite, no numbers supplied by model.
Reject ambiguity, wrong selectors/subject, missing/unsupported expression,
malformed/nonfinite input, XML entities/DTD; exclude nested figure/table captions
and their text, preserving direct paragraph context. ± is always unspecified;
no SD/SEM/n is borrowed. Exact uncertainty/normalization/source proof retained.
Activity units base umol/min/mg (nmol/min/mg conversion allowed); Km base uM
(nM/mM allowed). Specific activity normalization mg_assayed_preparation;
Km normalization none. Explicit source value origin reported or synthetic.

## Calculator interface (fresh worker ownership)

New literature_activity_calculations.py and tests/test_literature_activity_calculations.py only.
populate_corrected_activity(inputs): exact keys values,covariance,
variance_status,distinct_residual_variance,observation_model.
values exact q,g,k,E,u,v each finite number|null. All quantities already in
consistent declared units: q,g,u,v uM/min; E uM; k dimensionless.
covariance full6x6|null; variance_status known|estimated|unknown;
distinct_residual_variance finite nonnegative|null on per_min squared scale;
observation_model known_normal_nonnegative_presence|none.
Return version a105_corrected_activity_v1, primitive_order, inputs, cells.
Cells corrected_activity(per_min), effect_variance(per_min_squared),
effect_standard_uncertainty(per_min), effect_precision(min_squared),
source_profile_log_ratio(dimensionless), source_presence_index(dimensionless).
Each cell value/unit/status/formula/origin/unavailable_reason/conditional_on.
Use full J covariance Jt; never infer zero covariance or residual. Validate
symmetry/positive semidefinite; reject impossible denominators. Signed effect
retained; nonnegative presence truncation only at likelihood. S/B available only
explicit known variance + supported model, never from untyped source ±.

## Coordinator ownership and ordinary integration

Coordinator owns new native repository/storage, binding/service integration,
source-bound typed returns and assembled verification. Existing rate repository
helpers may be parameterized without changing existing sheet semantics. Native
cells use a separate fact-source/assignment field; no fabricated comparison
references. Saved original XML and exact expression anchors are retained;
replay/reconstruction read committed results without reacquisition/refitting.
No tool-grader changes, credit changes, extra model composer, private loop,
new episode types or synthetic controller observations.
