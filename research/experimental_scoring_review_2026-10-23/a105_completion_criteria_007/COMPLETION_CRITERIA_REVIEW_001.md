# A105: finite remaining work against the seven sheet criteria

2026-10-23. Source-free review of the numerical proposals and field contracts.
No primary paper or paper-specific packet was read. Published coverage below is
**documented coverage**, not independent source verification. No formula is
adopted and no sheet or goal is marked complete. Completion remains **0/10**.
The fixed list remains A105, A101, A102, A103, A104, A106, A107, A108, A110,
A111; A109 is removed and A106 perturbation evidence stays outside A105.

The single-source calculation is defined. The calibrated multi-source
calculation is also defined under its stated model. The substantive unresolved
calculation is the intended combination of **uncalibrated source-to-target
indexes**: the alternatives already have arithmetic, but their different
meanings have not been resolved. Missing real calibration inputs do not make the
conditional mathematics undefined or require an experiment on every target.

## Criterion status

| Goal criterion | Status in inspected documents | Exact residual |
|---|---|---|
| 1. Inputs, units, denominators, calculations, uncertainty and missing data | Defined for the single-source port in [cell contract, scope/inputs through missing cells](../a105_sheet_cells_005/SHEET_CELL_CONTRACT_001.md); the calibrated route defines its contrast, primitive covariance, GLS calculation and uncertainty in [bridge §§1–2, 6](../a105_correlated_bridge_006/CORRELATED_RESPONSE_PROPOSAL_001.md). | No essential arithmetic omission found in those scoped chains. Carry their model distinctions and exact operands into the broader sheet contract under criterion 6. Unknown empirical uncertainty remains null or explicitly conditional; no invented df, correlation or target response is needed. |
| 2. Explicit component combination; separate comparability and isolation | Present. [Joined sheet §2A–C](../a105_sheet_construction_001/A105_JOINED_NUMERICAL_SHEET_001.md) combines correction operands, propagated variance, S/B and numerical correspondence. Bridge `z=y-c-d+X beta` and its covariance keep condition comparability and attribution separate. | Resolve what the uncalibrated multi-source operand is intended to measure. M and K are mathematically specified alternatives; neither is an accepted target-evidence aggregation. A calibrated common-target fit does not answer that uncalibrated choice. |
| 3. Contrasting published filled examples with checked arithmetic and distinct origins | Documented for reaction/oxygen consumption, transport and binding in the [joined source table](../a105_sheet_construction_001/A105_JOINED_NUMERICAL_SHEET_001.md#published-examples-informing-the-numerical-cells) and [progress 003, source conversions/checks](../SCORING_SHEETS_PROGRESS_2026-10-23_003.md). Reported inputs, graph-derived rates, calculations and synthetic transformations are distinguished. | No arbitrary extra paper count is warranted. Present existing examples using the finalized field names, including their unknown dependent outputs. A complete synthetic chain must not be relabeled a fully observed published chain. This review did not independently verify the source inspections or published values. |
| 4. Shared evidence, replication, contradiction and nondetection | Defined for source likelihoods and calibrated pooling: original identities once; joint likelihood before optimization; covariance; independent preparations distinct from shared molecular mapping; signed opposition; censor likelihood. See [contribution: combining/nondetection](../a105_contribution_math_003/CONTRIBUTION_PROPOSAL_001.md) and [bridge §§4–7](../a105_correlated_bridge_006/CORRELATED_RESPONSE_PROPOSAL_001.md). | If the wanted uncalibrated output is cumulative evidence, its treatment of shared source-to-target information is still unspecified. M can describe a roster average without claiming independence; K does not become dependence-adjusted accumulation merely by retaining a dependence label. |
| 5. Components traced to inspected sources | The joined table gives source identifiers/locations, numerical components and preserved limits, with links to conversion records. Synthetic calculations identify their synthetic origin. | No missing source category is established by this source-free review. Preserve the existing trace and inspection limits when presenting the finalized cells; do not claim this review rechecked papers. |
| 6. Exact fields for targeted population, separately from prompts/readers | Exact populated paths exist for the single-source presence model in [contract/record](../a105_sheet_cells_005/SHEET_CELL_CONTRACT_001.md). Other models have field tables and the calibrated fixture has exact numerical arrays in [bridge arithmetic](../a105_correlated_bridge_006/arithmetic_001.json). | A small contract crosswalk remains: identify each calculation/route and bind its equation operands to named nullable cells. The current detailed port starts at an upstream corrected activity and is explicitly single-source; generic `measurement_model_inputs`/`likelihood_operands` alone do not tell a reader which alternative operands to fill. No production reader or universal assay schema is required here. |
| 7. Print formulas, examples and choices; incorporate feedback | [Progress 003, unresolved boundary](../SCORING_SHEETS_PROGRESS_2026-10-23_003.md) records the printed average-versus-cumulative comparison and unanswered questions. The joined sheet prints the other proposed choices. | Print the final joined proposal with the new calibrated example, corrected sensitivity interpretation, field/scope choices and existing source examples. Incorporate actual feedback. Do not treat an unanswered question as approval. |

These statuses concern the research deliverable. They do not claim that a
reader, scorer, library entry or scientific consumer has been implemented.

## Exact finite residual checklist

- [ ] **State the intended uncalibrated multi-source output and settle its
  calculation through user judgment.** The existing formulas are
  `M=sum(D_i)/N` and
  `K=[product(1+D_i)-product(1-D_i)]/[product(1+D_i)+product(1-D_i)]`.
  [The multiple-source addendum](../a105_multiple_sources_005/INTERPRETATION_AND_ARITHMETIC_ADDENDUM_002.md)
  correctly explains that M changes the estimand to an average represented-source
  index, while K's growth has no supplied dependence-sensitive evidence meaning.
  With one strong positive D, adding a weaker positive changes M from
  **0.771222064 to 0.537929863**, or K to **0.871181485**. Neither answer is a
  bug in its printed arithmetic. If the chosen meaning requires cumulative
  support after shared information is accounted for, an explicit numerical
  combination and required dependence operands remain research work. Do not
  silently select M, K, an effective sample size, a cluster discount or a maximum.

- [ ] **Finish the field crosswalk and output-scope declaration.** Preserve the
  existing fixed-normal single-source port. Map the other equations' actual
  operands—paired `n, mean, SD`; censor event/limit/noise; native transport or
  binding parameters and their qualifier/units; calibrated mapping, primitive
  order/covariance and residual terms—to their named cells. Existing bridge JSON
  already supplies the calibrated numerical arrays; it needs a declared contract
  connection, not reimplementation. State which model/route is being used, the
  parameter regions and the returned value's scope. A physically nonnegative
  presence score and a signed specificity score must not share the same fixed
  presence equation by accident. Preserve missing/conditional/bounds-only states
  and source provenance. A short mapping table plus populated examples is enough.

- [ ] **Print the resulting usable proposal and the remaining numerical choices,
  then incorporate feedback.** Show the existing source examples with their
  exact available cells and explicit unknown outputs, the complete synthetic
  chain, one calibrated multi-source example, and the M/K contrast. This is
  presentation and research-design work; code execution is not needed to make
  those choices reviewable. No source should be reopened just to repeat a count.

The field crosswalk and the review presentation can be prepared before the
pending answer. Choosing the intended aggregation meaning belongs to the user;
writing the consequences into a concrete formula/contract belongs to the
research task. They are different kinds of remaining work.

## What still needs judgment, rather than an implementation task

| Choice | Existing concrete proposal | What is actually missing |
|---|---|---|
| Multi-source meaning | M roster average; K cumulative index; calibrated common-target likelihood where its actual inputs exist | User's intended meaning is unanswered. If dependence-sensitive uncalibrated accumulation is required, its numerical rule is not yet supplied. |
| Extra penalty after measured condition/attribution correction | Current calculation applies the correction and its covariance once | The earlier question remains unanswered. No additional penalty is needed to calculate the existing proposal. If requested, its distinct evaluated quantity, inputs and formula must be supplied; do not count the same correction twice. |
| Contribution scale | `S=sup(H+) log L-sup(H-) log L`; `B=tanh(S/2)` | Adoption of the normalized best-fit contrast; this is already defined arithmetic, not a probability. |
| Correspondence convention | Explicit native components, equal-family arithmetic R, or printed shifted-harmonic alternative | Election of normalization/weights/shape; no overall intuitive relevance grade. |
| Missing correspondence | Conditional observed-family point plus full-family identification bounds | Whether the contribution uses the conditional point or retains only bounds; never an automatic midpoint. |
| Nonnegative output | `c=max(0,D)` after compatible combination, retaining signed D | Whether support-only output is the intended meaning; its loss of negative ordering is already exposed. |

These choices are not runtime approval gates. A choice that changes the proposal
requires its new numerical consequences; the current defined version remains a
proposal until the user's feedback is incorporated.

## One molecular statement versus a whole annotation

The current `c_A105` is for **one declared molecular statement about the supplied
target and conditions**. It is not an automatic reduction over every molecular
claim in an annotation. A statement can be compound when its logical meaning
and joint data model are supplied. The [coordinate proposal, compound section](../a105_annotation_coordinate_004/ANNOTATION_COORDINATE_PROPOSAL_001.md#a-compound-annotation-differs-from-one-positive-assay)
defines `H+={theta1>0 AND theta2>0}` versus its complement, works the constrained
comparison, and leaves a required unmeasured endpoint unknown. Other endpoints
remain separately scoped; dimensionless B values do not make them commensurate.

The finite sheet requirement is to declare that scope and retain separate
statement-scoped records. The current goal does not require inventing a reducer
for arbitrary whole-annotation claim collections. Annotation-wide claim assembly
and consuming the sheet remain W05 responsibilities. **If a delivery instead
claims one A105 scalar for an entire annotation containing several molecular
claims, that scalar is currently undefined:** naming it “wiring” would not supply
its numerical semantics. State the narrower delivered scope rather than imply
that broader result.

## Empirical absences and corrected sensitivity are not new completion gates

Real response coefficients, their supported domains, finite-sample uncertainty,
shared-target/family residuals and cross-covariance are absent where the records
say they are absent. The calibrated equations specify what to do when supplied;
otherwise the corresponding result stays unknown or conditional. No target
experiment, universal calibration dataset, exact zero covariance, mandatory
modality or extra paper quota follows from this review.

The [sensitivity addendum](../a105_correlated_bridge_006/SENSITIVITY_CONSTRAINT_ADDENDUM_001.md)
resolves an important apparent contradiction: the marginal-only rho interval is
not a permissible modification of already known covariance components. When
`C=.10 I+R`, `diag(R)=.15`, `R>=0`, the ten-source equal-effect example has
`V in [.010,.160]`, `S in [2,32]` and
`B in [.761594155956,.999999999999975]`. Restricting residual correlation to
exchangeable nonnegative values narrows S to `[2,12.8]`. These are different
declared allowed sets, not competing estimates; no endpoint or midpoint is the
observed score. No remaining mathematical contradiction was found in that
corrected treatment.

## Checks and inspection limits

This review independently recalculated 22 numerical relationships: the supplied
single-source record, the three-source GLS point/variance/S/B, and the three
known-component sensitivity endpoints. Results are in
[ARITHMETIC_REVIEW_001.json](ARITHMETIC_REVIEW_001.json). It reproduces
`D=0.6165950427623814` and the calibrated `B=0.7456307045069298`.
It did not rerun every historical checker or validate any empirical model.

Primary papers/packets inspected: **0**. Production tests/scientific runs: **0**.
The parent's later TriA conversion and later checker reruns were reported to
this reviewer but not independently inspected or used to claim new coverage.
[AUTHORITY_AND_SCOPE_001.md](AUTHORITY_AND_SCOPE_001.md) records the actual reads.
Reader implementation, nullable runtime changes, ten-axis parameter choice and
annotation-path verification are outside this numerical-sheet research review.

Additive scope and notation clarification:
[OUTPUT_SCOPE_ADDENDUM_002.md](OUTPUT_SCOPE_ADDENDUM_002.md) specifies the exact
row produced, the unresolved same-statement source aggregation, and the essential
missing reducer if a whole-annotation A105 scalar is promised. It also makes
explicit that `R>=0` above means positive semidefinite, not entrywise nonnegative.
