# A105 source amount components: engineering proposal 027

Proposal only; no production implementation or scientific credit is claimed.
The source is the retained HFP case025 packet. No second paper was opened.
The ten evidence axes and the full active goal remain unchanged.

## Exact reader boundary

`amount_arguments_schema()` defines closed selected-operation arguments;
`read_amount_inputs(arguments, *, read_source)` verifies custody and extracts
the nominated quantities. Scientific meanings are episode interpretations;
their exact quotations are not proofs of attribution or experimental linkage.
Scientific numbers must come from selected source bytes. Model-supplied numbers
are offsets only.

Top-level fields:

- `source_ref`, `source_kind` (primary_source, retained_extraction,
  synthetic_fixture), nullable `experiment` witness.
- `comparison_kind`: witnessed interpretation with values
  `stock_target_mass_estimate_over_total_mass_estimate`,
  `between_arm_nominal_molar_amount`, `unknown`, `conflicting`.
- `pair_relationship`: witnessed interpretation `supported`, `unknown`,
  `conflicting`. A supported answer requires an actual same-stock relationship
  for the stock comparison or an actual between-arm experiment relationship for
  the nominal comparison. Equal labels, values or units are insufficient.
- `intended_change`: nullable witness; between-arm interpretation must identify
  what is deliberately changed before treating amount as a comparability issue.
- `quantities`: closed nullable numerator and denominator quantity objects.
- `covariance_source_ref`: nullable source reference. Covariance is never
  inferred from absent information, a replicate count, an approximation label
  or an untyped error bar.

Each quantity has nullable witnessed literals `subject`, `construct`,
`preparation`, `stock`, `method`, `reported_basis`, `condition`, and
`measurement_identity`; a nullable `measurement` with exact number selector
and nullable unit witness; witnessed `amount_role` (target_mass_estimate,
total_protein_mass_estimate, nominal_molecule_amount, unknown/conflicting),
`amount_kind` (measured, estimated, nominal, unknown/conflicting), and
`qualification` (point, approximate, unknown/conflicting). An optional reported
uncertainty statement and its witnessed kind preserve SD/SEM/CI/untyped
meanings without turning them into covariance.

Witness fields are exactly source_ref, representation, start, end, quote.
Offsets on the source are UTF-8 bytes; offsets inside a verified quote are
Unicode characters. The numeric selector contains witness, number_start,
number_end. Numeric limits and directly adjoining approximation syntax are
parsed from full source context. The explicit qualification witness also
captures prose such as 'an approximate concentration of 5', where the
qualifier is not immediately adjacent to the number.

Canonical dimensions are mass concentration (`mg/ml`) and molar concentration
(`uM`). Supported scale aliases will be explicit. No molecular weight, reaction
volume or conversion between these two physical dimensions is invented.
Missing or unsupported units leave the converted individual value unavailable
while preserving its native token and exact witness. Limits retain thresholds
and comparators; they never populate point-valued arithmetic.

Physical source-token keys identify the exact numeric location; a separately
witnessed physical-observation identity can connect duplicate representations.
Equal values are not identity or independence. A duplicate observation assigned
incompatible roles cannot manufacture a comparison or independent information.

## Exact numerical sheet boundary

`populate_amount_components(extraction)` populates the following components.
Every cell retains status, unavailable_reason, unit, origin, approximation,
conditional assumptions and operand identities. No aggregate is calculated.

| Cell | Calculation | Meaning |
| --- | --- | --- |
| numerator_amount | source numerator with supported unit conversion | Actual numerator quantity |
| denominator_amount | source denominator with supported unit conversion | Actual denominator quantity |
| amount_difference | n-d | Signed difference of supported comparable amounts/estimates |
| amount_ratio | n/d | Explicitly oriented amount or estimate comparison |
| reciprocal_amount_ratio | d/n | Reciprocal description of the same comparison |
| conditional_mass_denominator_factor | d/n | Conversion factor usable only for the supported target/total same-stock mass-estimate relationship |
| amount_difference_variance | (1,-1) Sigma (1,-1)^T | Propagated variance of the difference |
| amount_difference_standard_uncertainty | sqrt(previous) | Standard uncertainty of that difference |
| amount_ratio_variance | (1/d,-n/d²) Sigma (1/d,-n/d²)^T | First-order variance of the ratio |
| amount_ratio_standard_uncertainty | sqrt(previous) | First-order standard uncertainty of the ratio |
| reciprocal_amount_ratio_variance | (-d/n²,1/n) Sigma (-d/n²,1/n)^T | First-order variance of the reciprocal |
| reciprocal_amount_ratio_standard_uncertainty | sqrt(previous) | First-order standard uncertainty of the reciprocal |

The mass-factor cell is an alias of the reciprocal in the specified scientific
relationship, not another independent contribution. No extra uncertainty or
replication is manufactured by presenting alternative arithmetic on the same
operands. Difference of target/total estimates is not contaminant concentration.
Ratio values exceeding one stay visible and are never clamped to purity or a
probability. A zero denominator makes only its affected division unavailable.

The HFP stock yields approximate n=5 mg/ml, d=7 mg/ml, n-d=-2 mg/ml,
n/d=0.7142857142857143 and d/n=1.4. These estimates use different methods.
The conditional factor 1.4 could multiply a same-stock rate whose denominator
is proven to be total protein mass. No existing rate is converted by this
helper. Already target-normalized rates must not receive this factor again.

The one-pot comparison yields nominal n=8.4 uM HFP, d=8.8 uM IMP,
n-d=-0.4 uM, n/d=0.9545454545454545 and d/n=1.0476190476190477. Its
mass-denominator factor is unavailable as not applicable. These amount
comparability values establish neither an amount-response model nor active
concentration or causal isolation. All uncertainty cells remain unknown for025.

## Covariance and missingness

The optional retained covariance source has version `a105_amount_covariance_v1`,
ordered owner keys for numerator/denominator, exact raw units, finite symmetric
positive-semidefinite 2x2 covariance, origin reported/derived/synthetic and
variance_status known/estimated. Unit scaling applies to both matrix axes.
Owner mismatches, asymmetric or indefinite covariance and incompatible unit
bases are rejected; no covariance repair or jitter is introduced. Shared
observations require compatible covariance rows/columns. Cross terms remain
signed; independence is never substituted for missing covariance.

Each individual usable quantity survives an unknown comparison or missing
other arm. Unknown/conflicting scientific relationships, mismatched dimensions,
missing required stock/basis/subject meanings and censored inputs leave paired
cells unavailable with specific reasons. Approximation is retained on computed
nominal descriptions; it is not SE or an interval. Unknown qualification must
remain explicit and cannot silently become a precise point observation.
First-order nonlinear uncertainty propagation is conditional mathematics, not
an exact sampling distribution, confidence interval or annotation probability.

## Ownership and connected consumers

After parent agreement the initial owner creates only
literature_amount_inputs.py, literature_amount_calculations.py,
literature_amount_prompt.py, new test_literature_amount_* tests and this artifact
directory. Agent024 retains all shared native-rate/C7/renderer ownership.

Later integration requires a separately assigned literature_amount_storage.py
with selected-operation signature/replay, direct-source receipt authorization,
page descendant-source validation, immutable saved quantities/cells/bindings,
saved-only reconstruction and exact received-subset validation. Proposed
provider is literature.a105.amount_population; operation
literature.amount.populate; source projection literature_amount_cells.

After024 releases shared files, the assigned owner must wire C7 catalog,
dispatch, requested_amount_components, implementation hash, source-ancestry
checks, fact source/routes, typed return validation/admission and persisted
received subsets; WorkflowServices.literature_amount_repository; and recurring
AMOUNT_TASK plus compact received-amount rendering. Closed rows must preserve
both subjects/preparations/stocks, amount roles/bases, quantity dimension,
comparison kind, approximation, covariance status and unavailable reasons.
Every property remains required in the closed projection. Source identities
stay outside model-facing bookkeeping; scientific meanings survive the return.

Tests must include real retained025 operands, mismatched units/bases, unrelated
stocks, already target-normalized semantics, censoring, approximation, missing
relationships, ratios over one, duplicate representations and nonzero correlated
covariance. Pure-calculator success does not establish the selected repository
operation, ordinary episode typed delivery or saved-only reconstruction.

No new paper, acquisition, configured-model run, pin/state/history modification,
tool grader, final-credit aggregation or controller change is authorized here.
