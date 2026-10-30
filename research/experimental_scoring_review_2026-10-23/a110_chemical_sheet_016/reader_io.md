# A110 exact sheet fields and targeted populators — UNIMPLEMENTED

These are future IO contracts for populating the proposed numerical sheet, not installed tools or a generic extraction framework. There is no reader implementation in this workload. Publication text and datasets must fill the same quantity cells; deterministic calculation follows extraction. Model judgment, if needed to identify a claim, reaction or experimental unit in prose, must retain its source and uncertainty and cannot substitute a number for missing measurements.

The investigation prompt is separate and is not defined here. Host references and provenance are not proposed model-facing prompt content. A reference to an existing A105/A106/A107/A108 measurement preserves dependence; it is not a new measurement or duplicated score.

## Shared typed records

| Record.field | Exact type and allowed contents | Meaning/validation |
|---|---|---|
| `Origin.kind` | enum `reported_measurement`, `derived_from_reported`, `derived_from_plot`, `author_proposed_model`, `proposed_scoring_transform`, `synthetic_arithmetic_check` | Distinguishes data, calculation and proposal; synthetic checks cannot populate empirical cells |
| `Origin.source` | nullable source reference with DOI/URL/artifact path and table/figure/page/row locator | Required for reported or plotted values; DOI itself is not a score |
| `Origin.input_refs` | unique list of quantity/model references | Required for a derived value; exposes all shared measurements |
| `Quantity.value` | finite real or null | Nominal value, never a disguised category |
| `Quantity.unit` | explicit unit string and dimensional vector | Examples `mol H2/mol NADPH supplied`, `pmol UQ8/mg wet cells`, `mol e-/mol turnover`, `kJ/mol ATP`, dimensionless fraction |
| `Quantity.denominator_ref` | reference or null | Actual measured or declared denominator, including supplied versus consumed distinction |
| `Quantity.lower`, `.upper` | ordered finite real endpoints or null; an explicitly unbounded endpoint uses a bound flag | Not inferred from significant digits |
| `Quantity.uncertainty_kind` | enum `none_exact`, `reported_sd`, `reported_se`, `reported_ci`, `reported_range`, `reported_unspecified_plusminus`, `plot_extraction_bound`, `model_parameter_bound`, `joint_parameter_domain`, `unknown` | Prevents relabeling technical variation or coarse figure reading as biological CI |
| `Quantity.confidence_level` | real in (0,1) or null | Set only for an actual confidence/credible statement with its meaning |
| `Quantity.n` | nonnegative integer or null | Only with a declared `sample_unit`; unknown n stays null |
| `Quantity.sample_unit` | enum `independent_experiment`, `biological_preparation`, `culture`, `technical_injection`, `timepoint`, `source_summary`, `not_applicable`, `unknown` | Paper/laboratory count is not a substitute |
| `Quantity.covariance_ref` | covariance-array reference or null | Array axes must map to actual quantities/units; null means unknown covariance, not independence |
| `Quantity.missing_reason` | enum `not_missing`, `not_measured`, `not_reported`, `not_retrieved`, `nonidentifiable`, `invalid_denominator`, `unmapped_subject_relation`, `outside_declared_scope` | Does not numerically grade the source |
| `Subject` | supplied-material reference with exact file/record/region/snippet boundaries; assayed-subject reference; relation references | A searchable public name or initial annotation is optional; no fabricated whole sequence from snippets |
| `Dependence` | experiment reference, preparation reference, technical-unit references, observation references, shared-axis references | Actual identity determines deduplication, not numerical equality |

A value with no uncertainty does not acquire a zero-width scientific interval merely because a nominal number exists. Exact algebraic values can use `none_exact`; approximate source ratios use unknown or reported uncertainty. Units must be compatible before division, correction or error comparison. Signed fluxes and directions are preserved.

## Sheet-specific input records

### A. Account and question definitions

`Account` contains:

- `subject`, `account_text`, `scope` (one of `specified_reaction`, `specified_atom_source`, `specified_pathway_budget`), and `reaction_direction` (`forward`, `reverse`, `reversible_with_named_test_direction`).
- `turnover_basis`: species/amount defining one reaction turnover, with explicit units.
- `questions[]`: unique physical question references, type (`scalar_stoichiometry`, `isotope_distribution`, `resource_budget`), component weight real ≥0, and declared alternatives. Weights sum exactly to one within the declared component set or carry a precise rational representation. A repeated view of a question does not get another weight.
- `balance_scope`: elements, charge basis, redox half-reactions and whether the requested net is fully closed. The source's open mechanism is retained as open.
- `target_relation`: actual measured correspondence references and unresolved relationship fields. No ordinal applicability score.

Each `Alternative` contains a chemical model identity, the prediction formula, parameter references, source/author/proposal origin, and the exact comparison it addresses. `unknown` is not converted into a zero prediction. Separate alternatives sharing parameters retain that dependence.

### B. Scalar chemical measurement

`ScalarMeasurement` contains `experiment_ref`, `subject_ref`, `direction`, `numerator:Quantity`, `denominator:Quantity`, `ratio_kind` (`formed_per_consumed`, `formed_per_supplied`, `net_signal_per_supplied`, `other_explicit`), `background:Quantity`, `recovery:Quantity`, `intended_fraction:Quantity`, `other_component_response:Quantity`, `comparability_terms[]` and `measurement_equation_ref`.

Each `comparability_term` has `covariate_name`, actual test/reference values and units, measured response coefficient β with units of outcome/covariate, its experiment reference and uncertainty. If no calibration connects a condition difference to the measured quantity, the correction is unknown. An exact chemically invariant prediction can explicitly state why a covariate does not enter that prediction; it cannot assert that every assay effect is invariant.

`replicate_values[]` contains independently measured corrected quantities where available. Otherwise use source mean, SD and n with their actual experimental unit; absent operands remain null. For NfnAB the source-specific reader would fill supplied-substrate denominators and approximate ratios, leaving recovery and between-preparation statistics unresolved.

### C. Isotope measurements

`IsotopeMeasurement` contains:

- `experiment_ref`, matched condition references, assayed subject and actual genotype/background, precursor addition and units.
- `ion_windows[]`: exact mass bounds, adduct identity, charge, calibration method and index j. Do not mix UQ8 ammonium-adduct calibration with a different uncorrected response.
- `baseline_amounts[experiment][window]` and `labeled_amounts[experiment][window]`: `Quantity` arrays, including blanks, recoveries, LOD information and covariance.
- `precursor_label_fraction:Quantity`, its exact numerator/denominator and technical replication; separately `intracellular_donor_fraction:Quantity` or a bounded mixing/exchange model. These fields must not be silently equated.
- `oxygen_count_models[]`: integer m≥0 with reaction/atom mapping; formula `binomial(m,k)p^k(1−p)^(m−k)` when independent label draws are actually the proposed model.
- `window_truncation`: exact selected j range and normalization meaning; unmeasured bins remain null, not zero.
- `comparability_corrections` and `isolation_model` as distinct fields, with shared parameter references.

For the restricted Fig. 4D illustration only four amounts are image-derived. The full `baseline_amounts` and replicated array are not filled. A reader cannot treat the illustrative midpoint as a reported datum or a plotted SD as an extraction bound.

### D. Stoichiometry and conservation

`Species` contains unique identity, formula counts by element (nonnegative integers or explicit symbolic invariant skeleton), charge as integer/rational or specified symbolic base plus redox difference, protonation convention, compartment and source/model origin. `StoichiometricTerm` has species reference and signed rational coefficient. `HalfReaction` contains explicit donor/acceptor electron counts with the same turnover basis.

`BalanceInput` contains terms, elements, paired half-reactions, `closed_account:boolean`, missing species/acceptor references and cancellation rules. Reversed direction changes every coefficient consistently. Unidentified electron acceptors are missing terms, not zero coefficients. Open half-reactions can have calculated residuals without receiving the closed-account D.

### E. Resource/pathway budget

`BudgetInput` contains reaction/stoichiometry references; named target output; required amount/rate v* and unit/time/compartment; measured available resource amounts/rates; competing consumption; regeneration reactions; measured bounds l/u and their uncertainty; shared-resource matrix G/h; observed accumulation rates; and declared alternate pathways.

Each bound records whether it is measured, derived from measurement, author-proposed or merely unconstrained. Missing upper bounds may define an unbounded model but do not establish measured sufficiency. If capacities are wholly unknown, f spans [0,1]. Target production has a declared nonnegative direction. An infeasible model returns its contradictory constraint references; it does not manufacture biological absence.

An optional `NativeModelResult` retains solver/model identity, exact objective and units, stoichiometric network, constraints, measured versus assumed bounds, optimization status, tolerances and result. It is not available merely because this record is defined. No native model result populated the present examples.

## Exact numerical outputs

`ConstraintOutput` contains corrected quantities; correction amounts and uncertainty by mechanism; claim/alternative predictions; absolute residuals; `e_claim`, `e_alternative`; `signed_contrast`; its interval and uncertainty kind; all pairwise alternative values; conservative question minimum; observation/dependence references; and an explicit `conditional_assumptions[]` list. If available, keep separate observed per-unit variability and uncertainty of the mean.

`BudgetOutput` contains z with units/status; v*; f; `s_supply=2f−1`; their bounds; all active/shared constraints; and unsupported or unmeasured bounds. No “pathway present” pseudo-score exists.

`BalanceOutput` contains canceled terms; element R/P/r/d arrays; charge numerator/denominator/residual; electron donation/acceptance/residual; D or its bounds; scope and any open terms. A numerically balanced author hypothesis retains that hypothesis origin.

`CompilationOutput` contains original question weights; original per-question values/bounds; S; D; C; conditional nominal C separately from unconditional bounds; exact unknown cells with their retained weights; and source/derived/proposed origins. No source records are credited merely for being present. No unknown weight is renormalized away.

## Future functions and their concrete IO

All entries below are **UNIMPLEMENTED**, including deterministic arithmetic as an application reader/scorer. The separate research check script only demonstrates formulas on manually entered examples.

| Proposed function | Exact input | Exact output | Deterministic versus extraction boundary |
|---|---|---|---|
| `read_chemical_amounts` | Selected source passage/table/plot or calibrated assay dataset, specific experimental comparison and quantity definitions | `ScalarMeasurement` plus origins/missing fields | Parsing tables/data can be deterministic; identifying the measured versus supplied quantity in prose may require a cited interpretation |
| `read_isotope_amounts` | Defined ion windows, per-experiment raw areas/calibration and blank/recovery datasets, or selected literature figures/tables | `IsotopeMeasurement` | Dataset integration follows stated method; plotted extraction remains labeled and bounded; no invented raw replicates |
| `apply_measurement_model` | Scalar/isotope quantities and the explicitly selected measurement equation with measured nuisance parameters | Corrected quantities and separate comparability/isolation terms, joint domain | Deterministic algebra where the model is established; unresolved parameters stay unresolved |
| `predict_chemical_quantity` | Account/alternative reaction model, stoichiometry, measurement operator and parameter domain | c/a predictions in exactly the measurement units | Deterministic model evaluation; it cannot invent an alternative mechanism or its parameters |
| `summarize_constraint_errors` | Experiment-level corrected quantities or mean/SD/n, predictions, dependence identity and joint domain | e values, s values and bounded uncertainty | Deterministic; one chemical vector remains one observation |
| `calculate_conservation` | `BalanceInput` | `BalanceOutput` | Deterministic atom/charge/electron algebra; unknown chemical identities cannot be “balanced” by assumed species |
| `read_pathway_constraints` | Actual flux/capacity/uptake/resource datasets or selected reported numerical tables and reaction definitions | `BudgetInput` | Extracts measured constraints and separately marks assumed/modelled bounds; gene presence alone never produces capacity |
| `calculate_pathway_budget` | `BudgetInput` or fully specified `NativeModelResult` | `BudgetOutput` | Deterministic linear algebra/optimization once all declared data/model choices exist; no available execution capability is implied |
| `compile_a110_sheet` | Fixed account/question weights, numerical constraint outputs, budget outputs, balance output and shared-observation mapping | `CompilationOutput` | Deterministic weighted sum/penalty/bounds; does not wire W05 or decide episode continuation |

## Exact edge behavior

For relaxed error intervals A=[aL,aU] and C=[cL,cU], the conservative lower score is `(aL−cU)/(aL+cU)` if the denominator is positive, otherwise 0. The upper is `(aU−cL)/(aU+cL)` if positive, otherwise 0. This defines the zero-denominator bound cases without adding an epsilon. Unknown errors with no finite domain yield the general [−1,1] range.

Fractions require nonnegative inputs and a positive total. Ratios require the actual positive denominator; interval denominators containing zero do not yield a bounded nominal ratio. For the restricted isotope ratio p=1, the first bin denominator is zero and the output is `invalid_denominator`, with the full vector formulation still available. Negative net chemical changes retain their direction rather than being clamped before comparison.

A material-resource and an energy subquestion may be separate weighted constraints only if their definitions do not duplicate the same bottleneck already incorporated into a joint budget. If energy already constrains the single network budget, its residual remains visible there and is not scored again as a separate resource observation. The broad NfnAB three-block illustration uses a non-energy resource-capacity block and a distinct energy-account block, both unmeasured.

These declarations are targeted to the sheet's actual numerical cells. They do not amount to implementation, source reader validation, user acceptance or axis completion.
