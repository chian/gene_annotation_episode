# Conditional experimental partner components

The Pdx source read and post-paper reset are recorded in
primary_pdx_partner_015/PARENT_RESET_001.json. This additive contract develops
experimental reference evidence for A105 and partner-requirement rationale for
later A107 use. Genomic presence, coexpression, target correspondence and W05
remain outside it. No axis or whole goal is completed here.

Fresh coding owner: gene_annotation_episode/literature_partner_calculations.py
and tests/test_literature_partner_calculations.py only. Coordinator owns source
conversion, this contract, example records and review. Do not change existing
calculators, episodes, storage, prompts, live runs, pins or historical records.

## Scientific conversion and exact numerical sheet

Retain each arm's actual subject, partner, presence/absence, endpoint, unit,
normalization identity, declared nonpartner condition factors, measurement
identity, native value/limit and reported spread meaning. A condition factor is
an extracted experimental attribute, not a numerical quality grade. Completeness
is a source interpretation; byte equality cannot establish scientific validity.

For compatible arms W (partner present), O (partner omitted), A (partner added
back), populate:

| Component | Formula | Meaning |
| --- | --- | --- |
| reference_rate | W | Original present-partner endpoint |
| omitted_rate | O | Original absent-partner endpoint |
| addback_rate | A | Original addback endpoint |
| partner_loss | W-O | Matched removal contrast, in endpoint units |
| partner_loss_fraction | (W-O)/W | Fractional dependence in that specific assay |
| addback_gain | A-O | Matched addback contrast, in endpoint units |
| addback_fraction | (A-O)/(W-O) | Fraction of removal contrast restored |
| restored_reference_fraction | (A-O)/W | Restoration above omission, relative to W |

These are numerical experimental components, not a probability, final annotation
score or universal necessity label. No clipping: inhibition, overshoot and
negative differences survive. With a nonzero W-O, the last cell is exactly the
product partner_loss_fraction * addback_fraction; calculate its primitive formula
directly so shared O is not treated as two independent inputs. It can remain
defined when W=O makes addback_fraction undefined. Never infer a missing factor
as zero or one. Existing A106 nuisance-corrected index is a different quantity;
do not duplicate or silently adopt its C/I conventions here.

Native Pdx W=774 (spread58), O=284 (spread33), both pmol/min/mg, describes a
cross-condition comparison: W has glutamine plus Pdx2; O has ammonium sulfate
without Pdx2. The same-condition removal endpoint is missing. Normalization
identity and spread kind remain unresolved. All derived partner cells therefore
remain unavailable; the two native values survive. A missing addback is not a
third measurement. Qualitative glutaminase nondetection is not an observed zero.

## Pure function contract

Export VERSION='literature_partner_components_v1', COMPONENTS (the eight names
above in table order), and populate_partner_components(inputs). Use only standard
library plus existing ExperimentalContractError. No I/O, SQL, network or models.

Closed inputs exactly {version:'literature_partner_inputs_v1',arms:{reference,
omitted,addback}}. Each arm is null or exactly:

```
subject_ref: nonempty string|null
partner_ref: nonempty string|null
partner_state: present|absent|unreported
endpoint_ref: nonempty string|null
normalization_ref: nonempty string|null
unit: pmol/min/mg|nmol/min/mg|umol/min/mg|per_min|per_s|uM/min|nM/min|unreported
conditions: {
  coverage: complete|partial|unreported,
  factors: [{factor:nonempty string,level:finite number|nonempty string|null,
             unit:nonempty string}]
}
measurement: {
  measurement_id: nonempty string|null,
  status: observed|upper_bound|unreported,
  value: finite nonnegative number|null,
  origin: reported|graph_derived|synthetic,
  spread: {kind:SD|SEM|CI|unspecified|unreported,magnitude:nonnegative finite|null}
}
```

Factor names are unique, and their order has no scientific meaning. Numeric bool
is invalid. No null numeric point for observed/upper_bound; unreported requires
null. Unreported unit permits only unreported measurement. Unreported spread
requires null magnitude; other kinds require magnitude. A scalar CI magnitude
is retained exactly as supplied (not converted to endpoints/SD); no inference
uses any spread. CI's detailed interval interpretation remains unimplemented.
Unreported coverage requires an empty factor list. Complete coverage requires a
nonempty list with all levels known. No unit conversion or condition equivalence
inferred here; differing factor sets, levels or units are differences.

Return exactly {version:VERSION,inputs:<deep copy>,cells:<eight cells>,
comparison_checks:{reference_omitted:<check>,addback_omitted:<check>}}.
Check exactly {status:matched|different|unresolved,differing_factors:[sorted
factor names],unavailable_reason:string|null}. Known factor differences are
reported even if other relationships remain unresolved. Pair qualification must
establish equal known subject, partner, endpoint, normalization, unit, complete
equal nonpartner conditions; partner states present/absent as appropriate; and
known distinct physical measurement IDs. Unknowns are specific unavailable
reasons. Distinct IDs do not assert statistical independence. Reuse of an ID with
conflicting measurement value/status/unit is a ContractError; equal-value same
IDs cannot establish a contrast. Different IDs with equal values can.

Cell exactly {value,lower,upper,unit,origin,bound_kind,status,unavailable_reason}.
Native observed cells: value=lower=upper (reported spread is separate, not an
interval); bound_kind=point_only_not_uncertainty. Native upper-bound cells:
value=null, lower=0, upper=limit, bound_kind=conditional_input_domain_not_CI,
status=bounded, unavailable_reason=censored_point_unreported. Retain the printed
limit; interpret it as an outer nonnegative domain, not an observed zero.
Native missing: all numbers null, status=unavailable, reason=arm_unreported or
measurement_unreported; preserve actual unit if any, otherwise null.

Derived cells are origin=derived. Exact point operands produce a point with
point_only_not_uncertainty; nontrivial censor domains give conditional input
bounds, null point, bounded status and censored_point_unreported. An algebraically
identified singleton may have a point while retaining conditional-domain meaning.
Missing/incompatible inputs give all numeric fields null, status=unavailable and
the specific reason. Fraction units are dimensionless; differences use shared
native unit, otherwise null. No unknown covariance is set to zero, no likelihood
or statistical interval is calculated. Raw spreads remain in returned inputs.

Use exact Fraction intermediates. For fractions require W's full domain strictly
positive; for addback_fraction require W-O's full domain excludes zero. Evaluate
all primitive box vertices (not products of separately bounded derived cells)
for the tight linear/linear-fractional image when the denominator has one sign.
These domains condition on all observed means being exact; they omit their
unquantified sampling uncertainty and are not confidence intervals. Outward-round
finite bounds; detect overflow/underflow per cell without erasing independently
representable cells. Do not make interval subtraction of one shared O twice.

Reject malformed closed fields, strings, booleans, nonfinite numbers, unsupported
enums and conflicting identities with stable ExperimentalContractError codes.
Preserve caller inputs. Return explicit reason codes for missing arms, unknown
identity/normalization/conditions, known factor differences, incorrect partner
states, duplicate physical measurements, zero/straddling denominator, unsupported
unit comparison, and numerical_model_range.

## Verification and remaining integration

Cover a matched three-arm synthetic W100,O20,A90: loss80, loss_fraction.8,
gain70, addback_fraction.875, restored_reference_fraction.7. A synthetic upper
bound O<=5 with W100,A90 gives loss[95,100], loss_fraction[.95,1], gain[85,90],
addback_fraction[85/95,.9], restored_reference_fraction[.85,.9]. Same O is shared.
Cover the Pdx crossed-condition case; missing addback; equal valid independent
values; exact duplicate IDs; nuisance amount changes; unreported denominator;
negative contrast; overshoot; censored W reaching zero; denominator straddling
zero; order invariance; large/small finite arithmetic; malformed schemas.

This workload implements the deterministic numerical core. Targeted source
reader, aspect-specific recurring TASK, selected storage, typed parent delivery,
reconstruction and actual model use remain explicit later work. Tests of this
core do not establish those paths. The original live run remains untouched.

## Identity clarification during implementation

The owner identified that W/O and A/O distinctness alone permits A to reuse W.
That cannot establish a separately observed addback. When reference and addback
have the same known physical measurement ID, retain native cells and the W/O
check, but all derived addback components (including addback_gain) are unavailable
with role_measurement_not_distinct. Three-arm fractions require three known
distinct IDs. If reference is missing or its ID is unknown, an otherwise qualified
A/O pair can still supply addback_gain; it cannot supply a three-arm fraction.
This clarifies the existing identity requirement without changing input fields.

## Parent review: absent origins and incomplete condition descriptions

An entirely missing arm has origin=null: no measurement was supplied. An existing
arm with an unreported value retains its declared origin. Native exact finite
integer literals may remain integers even beyond binary-float range; each derived
cell independently checks whether its output can be represented.

The earlier statement treating differing factor sets as actual differences was
too strong. A factor recorded on only one side is missing information, especially
under partial coverage. differing_factors reports only shared named factors with
known unequal levels or unequal unit representations. A known such difference
still produces status=different. Without a known shared difference, unequal
factor sets prevent matching and give status=unresolved and reason
condition_factor_scope_unresolved (other established identity/normalization
mismatches may take precedence). Missing level/attribute is not known absence.
Equal complete factor sets remain required for matched arithmetic. Unit comparison
is exact representation comparison, not proof of physical nonequivalence.
