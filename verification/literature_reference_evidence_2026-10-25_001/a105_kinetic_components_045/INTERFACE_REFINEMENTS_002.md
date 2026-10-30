# Released045 pure interface refinements002

Parent released the new pure module/test ownership after reading001, with
specific source-identity and covariance binding refinements. This additive
record preserves001 and states the actual implementation interface.

Public API remains `populate_kinetic_contrast(inputs, model=None)` and
`kinetic_operand_keys(inputs)`. All001 root/operand keys and enum values remain.
CI metadata additionally retains `confidence_level`, nullable finite in(0,1),
and valid only with statistic `ci`. CI magnitude must be null; intervals are
endpoints, never silently interpreted as plus/minus widths. Every uncertainty
object therefore has exactly statistic,magnitude,interval,confidence_level,
count,repetition_basis,estimate_basis. Missing magnitude/interval is retained as
missing metadata, not converted into a model.

## Exact identities

Each source numeric locator is the exact tuple:

    (source_ref,artifact_ref,representation,start,end).

The same locator cannot create two operands by changing measurement_id or
physical_measurement_id. Likewise equal nonnull physical_measurement_id or
equal measurement_id means a reused selected observation. Reused identities
with disagreeing parameter/value/qualification/subject/context/uncertainty
meaning produce `conflicting_source_observation`; agreeing reused readings
produce `reused_source_observation`. Both prevent pair calculation while
retaining individually selected raw values/qualifications. No fuzzy string
comparison establishes molecular or preparation identity.

`kinetic_operand_keys` returns a dict with `numerator` and `denominator`.
An absent operand or null physical_measurement_id has a null key. Otherwise:

    key='kinetic_estimate_'+sha256(
        json.dumps({"version":"kinetic_estimate_identity_v1",
                    "operand":THE_ENTIRE_VALIDATED_CLOSED_OPERAND},
                   sort_keys=True,ensure_ascii=False,allow_nan=False,
                   separators=(',',':')).encode('utf-8')).hexdigest()

Thus changed parameter kind, estimate, source location, selected scientific
context, uncertainty representation or physical owner cannot silently reuse a
covariance keyed for a different selection. This is an exact estimate binding,
not a global physical-measurement identity. The separate physical IDs remain
in inputs/output for cross-comparison dependence and cannot be inferred from
the hash. Distinct hashes never establish independent evidence.

## Optional model and provenance

The001 closed model additionally includes `source`: the same closed exact
locator shape as operand source, or null only when variance_status is unknown.
Known/estimated covariance has a nonnull source location and requires two
nonnull exact estimate keys in numerator,denominator order. An unknown-status
model may have covariance=null and its unresolved expected null owner keys;
it cannot authorize variance or S. Any supplied covariance, even unknown-status,
must be finite symmetric PSD2x2. No source bytes are read here: source custody,
literal/model derivation truth and model applicability remain reader/scientific
responsibilities. A locator is not proof of scientific validity.

Returned sheet fields: version,axis,evaluation_scope,contrast_meaning,inputs,
model,measurement_keys,physical_measurement_ids,cells,variance_status,
independent_preparation_count,annotation_credit,interpretation_limits.
`inputs`/`model` are detached validated copies. Evaluation scope is
`source_kinetic_parameter_contrast`; mathematical direction is
`numerator_parameter_exceeds_denominator`. No joint score is returned.

All cells have exactly value,unit,status,formula,origin,unavailable_reason,
approximate,conditional_on,threshold,relation. Threshold is nonnull only for
raw censored parameters; their value is null. Formula and reason strings come
from finite constants. Raw point origins remain the supplied origins; numerical
arithmetic is derived; the bounded source_signed_index origin is proposed.
The signed profile formula is conditional, not an adopted reliability policy.

Pair reasons preserve the earliest concrete unavailable input/relationship;
later absent covariance/model checks do not overwrite it. Raw uncertainty and
preparation identities are never upgraded. Unknown preparation stays null.

No existing file, scientific TASK, catalog, storage, selected operation, runtime
counter or historical state changes under this release.
