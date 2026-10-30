# Proposed common-sheet functions and typed IO (future implementation)

These are targeted design interfaces, not installed operations or adopted policy. One coordinator owns future shared compiler/version/schema integration. This217 workload writes no production files. Existing215 within-assay covariance work is outside these contracts and is not to be modified by this workload.

## Scientific input and sheet interface

`bind_common_a105_assessment(request, *, read_received_component, read_received_source) -> BoundAssessment`

Inputs are explicitly selected information, not permission to dereference another child's private sheet. `read_received_component(selector)` returns exactly one requested already received row under its registered version. Validate exact selection, namespace/version, actual source references, component meaning, units, status and primitive dependencies. Preserve a failure and valid other rows when one selection is unusable. A source/paper identifier alone confers no numerical possession.

A proposed request is closed and contains:

- `version = a105_common_assessment_request_v1`.
- `assertion`: source/supplied scoped `subject`, `construct`, `substrate`, `product_or_ligand`, `system`, condition witnesses; `resolution` in `identified_product_formation`, `saturation_turnover`, `low_substrate_efficiency`, `binding_occupancy_alternative`; `question` in `existence`, `relative_effect`, `named_alternative`; an optional source-supported numerical threshold has its own selector, unit and meaning. No hidden threshold is supplied.
- `arms`: exactly the nominated reference/test arm for the requested comparison. Each contains actual assay/endpoint/denominator/preparation/sampling-unit references, intended-variable witness and additional-difference witnesses. Missing arms/context remain explicit nulls with reasons. A generic paper ID cannot stand for an assay.
- `selected_estimates`: role-labelled selectors for `product_test`, `product_reference`, `reporter_test`, `reporter_reference`, `kcat_test`, `kcat_reference`, `Km_test`, `Km_reference`, `Kd_test`, `Kd_reference`; unused roles null. Later correction inputs use explicit same-scale `background`, `recovery`, `active_fraction` and `nuisance_response` selectors per arm. No duplicated nominal E or E=1 is manufactured for already normalized rates.
- `relationships`: witnessed restricted meanings for `subject_link` (`same_construct_supported`, `intended_variant`, `different`, `unknown`, `conflicting`), `endpoint_link` (`same_estimand`, `reporter_product_pair`, `binding_to_occupancy`, `different_estimands`, `unknown`, `conflicting`), `normalization_link`/`preparation_link`/`conditions_link` (`compatible_supported`, `different_with_declared_model`, `incompatible`, `unknown`, `conflicting`), `sampling_link` (`paired_units_supported`, `independent_units_supported`, `shared_units`, `unknown`, `conflicting`). Validation requires witnesses and meaningful field relationships, not merely syntactically valid JSON.
- `numerical_model`: `none` or `one_site_equilibrium_sensitivity`. The latter declares free-substrate values per arm (exact numerical values/units/origin), source method links, and *separate* assumptions: equilibrium, one site, free-versus-total treatment, binding/catalysis applicability, proportionality of turnover to occupancy, fixed post-binding rate in the alternative, equal recovery, equal active fraction, equal nuisance response. Each assumption has `supported`, `stipulated_sensitivity`, `unknown`, `conflicting` status and source/supplied-model reference. Stipulated equalities are model assumptions, not fictitious measured 1s. This paper's S=2000µM is reported for NADH but **stipulated** for the product sensitivity case.
- `joint_covariance_selector`: null or an actually received joint uncertainty block with ordered exact estimate owners, canonical units, basis `joint_covariance_of_selected_estimates`, numerical origin, known/estimated/unknown status and all symmetric matrix entries. Blocks must not be completed by assuming unreported cross terms zero. Primitive uncertainties already inside an upstream derived estimate must not be added a second time.
- `requested_cells`: unique selected common-cell names, so return does not silently expand the assignment.

`BoundAssessment` freezes those meanings, exact source-selected/derived numeric owners, exact fractions where possible, scientific relationship status and specific missing/unsupported reasons. Models return role/relationship selections, not arithmetic or freeform confidence. Source witnesses bind numeric strings to the proper row, column, units and footnotes. The calculator below receives no IO callbacks, no model and no credit/controller function.

`calculate_common_a105_assessment(bound: BoundAssessment) -> CommonA105Section`

Closed output: assertion/contrast/assay bindings; requested `cells`; dependency/dependence links; unresolved requirements; `annotation_credit=null`. A cell has `component`, `value`, `exact_value`, `conditional_value`, `unit`, `status` (`populated`, `conditional_scenario`, `unavailable`), `meaning` from the fixed definition, `formula_kind`, `operand_keys`, `model_keys`, `source_missing_reasons`, `relationship_reasons`, `implementation_reasons`, `origin` (`reported`, `derived`, `proposed_sensitivity`, `synthetic`), variance/model basis and contribution identity. Proposed source-based calculations have derived numbers with proposed model origins, not synthetic paper measurements. A contribution ID identifies reuse; it is not an assay count.

## Bounded initial cell definitions

| Cell | Function of actual selected operands | Required scientific meaning |
|---|---|---|
| `product_reference_contrast` | P_test/P_ref | Same product/normalization; an unknown nuisance difference is a retained qualification, not a numerical C=1. This is a descriptive observed contrast.|
| `reporter_reference_contrast` | H_test/H_ref | Same reporter/normalization. It is not a product-function score.|
| `productive_use_reference_contrast` | (P_test/H_test)/(P_ref/H_ref) | Pair links and units; dependent on all four source estimates.|
| `saturation_turnover_reference_contrast` | kcat_test/kcat_ref | Same fitted catalytic parameter and denominator; no pool with Table3 rate.|
| `low_substrate_efficiency_reference_contrast` | (kcat_test/Km_test)/(kcat_ref/Km_ref) | Corresponding fitted parameters and kinetic-model interpretation. Low-substrate limit, not a claim about the actual unknown in vivo S.|
| `occupancy_reference`, `occupancy_test` | theta_j=S_j/(S_j+Kd_j) | Positive Kd/free S and declared one-site model/applicability; conditional when stipulated.|
| `occupancy_reference_contrast` | Rtheta=theta_test/theta_ref | Separate S allowed; same-S simplification only for actually shared S.|
| `binding_only_prediction_error` | d=P_test/P_ref−Rtheta | Same scope as the named alternative; a signed discrepancy, not a significance or causal fraction.|
| `post_binding_residual_ratio` | Ra=(P_test/P_ref)/Rtheta | Full model assumptions retained. Other causes remain unresolved.|
| `binding_only_log_residual` | D=ln(P_test/P_ref)−ln(Rtheta) | Strictly positive eligible point operands; exact fractions for rational precursor, explicit floating log.|
| `binding_only_residual_variance` | J Sigma J^T | Actual joint owner block, matching estimand/covariance basis. No distribution assumed.|
| `binding_only_standardized_residual` | D/sqrt(V_D) | Positive applicable V_D, source/model qualifications retained.|
| `binding_only_squared_standardized_residual` | D²/V_D | Same contribution; statistical reference distribution requires its own supported assumptions. Not a probability/overall grade.|

For same free S, order `(P_test,P_ref,Kd_test,Kd_ref,S)` gives

`J_D=(1/P_test, −1/P_ref, 1/(S+Kd_test), −1/(S+Kd_ref), 1/(S+Kd_test)−1/(S+Kd_ref))`.

If S is stipulated fixed, its conditional derivative is omitted, with no implication that the *actual assay* has no uncertainty. If separate S values are selected, use their actual separate derivatives/owners; do not merge them by equality of displayed numbers. If P/H derived views are selected, chain through upstream primitive Jacobians or receive a covariance explicitly owned by those derived estimates. Shared WT and Kd references create nonzero shared contributions. Unknown cross-covariance leaves variance unavailable while means survive.

`validate_common_a105_section(saved, *, original_source_authentication)` checks immutable source bindings and exact dependent arithmetic on save/read; ordinary reconstruction must not rerun scientific interpretation, reacquire sources or replace the scenario. Pure structural validation alone does not authenticate a saved source witness. Persist the original section through the ordinary existing LiteratureEpisodes operation and parent-requested form, with versioned schema compatibility; render only requested admitted numerical facts and qualifications as concise STEERING. No second composing model call. This path is future implementation, untested here.

## Validity/isolation/comparability continuation

The broader common sheet must also bind existing calibration-loss, amount and within-assay compiler sections to the same assay/estimate population. This is explicit unfinished integration. It must distinguish a standard's individual-reading relative loss from a selected mean's covariance, active fraction from culture yield, and nuisance response excluding the intended mutation from that mutation's effect. Missing relationships prevent a combined physical correction; they must not be treated as default equality. Unsupported nonlinear response models require another specific model, not a forced multiplicative correction.

The proposal does not prescribe mandatory assays, required evidence quotas, episode order or numerical stopping criteria. It defines useful calculations for selected questions. Actual future verification must cover source row/column/denominator binding, missing and ND limits, wrong endpoints, shared controls/WT, unequal and conditional S, conflicting preparation links, estimated/unknown covariance, save/replay, exact typed child-to-parent delivery and duplicate representations. Controlled fixtures cannot be reported as model-backed literature work.
