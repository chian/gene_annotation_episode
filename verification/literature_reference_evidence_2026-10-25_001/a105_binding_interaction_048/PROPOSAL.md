# Four-cell reported binding-parameter interaction: proposal, awaiting review

This proposal is based only on the parent's closed scientific brief and the complete existing binding reader, calculator, model, model-input, prompt, and storage paths. No paper, retained paper-specific packet, actual-observation file, or live provider/model state was consulted. The active goal, repository instructions, W04 amendment, and current 039/040 direction were read. This is one A105 component; it makes no claim of whole-axis coverage or a final grader count.

## Scientific meaning

Compare relative ligand discrimination between two separately assayed protein subjects/states under their actual reported protocols. Parameter kind is uniformly `ic50` or uniformly `reported_hill_kd`, already normalized to nM. The calculator does not equate these parameter kinds or convert them into intrinsic affinity, activity, thermodynamic energy, contamination, or mutation-only effects.

The fixed role order is `reference_subject_reference_ligand`, `reference_subject_test_ligand`, `test_subject_reference_ligand`, `test_subject_test_ligand` (abbreviated rr, rt, tr, tt below). The reference ligand is the common comparison ligand in each separately assayed subject; the test ligand is the same selected alternative across subjects. Exact constructs, states, preparations, assays and source physical observations remain attached to each role. A shared self-control used in later interactions retains its original physical identity.

## Closed input and source bindings

Proposed pure entry point: `populate_binding_interaction(inputs, model=None)`. No source acquisition, Store read, prompt, catalog, operation, model call, or routing is added.

`inputs` has exactly `version`, `parameter_kind`, `unit`, `operands`, `relationships`. Version is `binding_interaction_inputs_v1`; unit is `nM`. `operands` has exactly the four role keys, each null or a closed normalized record:

- `value`, `relation` (`eq`, `lt`, `le`, `gt`, `ge`, `unreported`), `reported_spread`, `origin`, and `source` use the existing binding reader's normalized row meanings. Values/thresholds must be finite positive numbers; no fabricated values for `unreported`.
- `subject`, `construct`, `state`, `preparation`, `experiment`, `ligand`, `tracer`, `readout`, `normalization`, `conditions` preserve exact source labels (null where source does not establish them).
- `physical_fit_id` is a nonempty supplied source interpretation or null. It is never invented from construct, row order, equal values, or a hash of labels. The exact source token locator is retained separately.
- `uncertainty` has exactly `statistic` (`sd`, `sem`, `confidence_interval`, `unspecified`, `unreported`), `basis` (`fit_to_averaged_curve`, `between_independent_fitted_parameters`, `unknown`), `interval` (null or two finite endpoints), `confidence_level` (null or source-supplied probability), `exact_count` (null or positive integer), `minimum_count` (null or positive integer), `repetition_basis` (`biological_preparations`, `technical_measurements`, `assay_occasions`, `unspecified`). Exact and minimum counts must be consistent. Neither count nor spread supplies a covariance. A reported symmetric spread is retained without changing SD to SEM or choosing a denominator.

`source` uses the complete existing binding normalized source shape: `source_ref`, `artifact_ref`, `representation`, `table_id`, `row_index`, `locator`, `expression`; nonvisual locator has row/column, and visual locator names original source/artifact and exact image region. This module validates the declared closed representation only; it cannot attest custody, interpretation, or receipt. Future storage integration must establish these from actual selected/received sources.

`relationships` has exactly `within_reference_subject`, `within_test_subject`, `ligand_correspondence`, `parameter_definition`, `separate_assays`, `common_conditions`. Each is a closed `{status, sources}` object with status `supported`, `unknown`, or `conflicting` and a list of the same exact source locators. Supported/conflicting relationships require at least one source. The first five declare the scientific operand mappings needed for the full interaction; common conditions are optional and never inferred. If common conditions are unknown/different, valid arithmetic still describes the actual reported protocols, with that qualification. A conflicting common-condition claim is retained as a qualification, never silently accepted as a matched-condition interpretation.

Every operand receives a deterministic key for its complete exact normalized record. Model owners must match these keys in fixed role order; source token identity and declared physical-fit identity are separately retained. Reusing a token or physical fit for distinct roles cannot manufacture an interaction. Such reuse invalidates affected derived contrasts while retaining source values and specific reasons. Across calls the module preserves identities and makes no new independence or evidence-count claim.

## Numerical sheet

The returned closed sheet has version, parameter kind, unit, detached inputs, operand keys/physical identities, numerical `cells`, and finite qualifications. Each cell has its actual operands/formula, numeric value or printed threshold, units, relation, status and explicit reason when unavailable. All these cells are dependent views of the same four observations, never additive independent support.

| Cell | Meaning and exact operands | Units |
| --- | --- | --- |
| `parameter_rr` | Supplied rr point or printed limit | nM |
| `parameter_rt` | Supplied rt point or printed limit | nM |
| `parameter_tr` | Supplied tr point or printed limit | nM |
| `parameter_tt` | Supplied tt point or printed limit | nM |
| `reference_subject_ratio` | rt / rr, the reported ligand-parameter ratio in the reference subject | 1 |
| `test_subject_ratio` | tt / tr, the corresponding ratio in the test subject | 1 |
| `interaction_ratio` | D = (rt / rr) / (tt / tr) | 1 |
| `log_interaction` | e = -ln(rr) + ln(rt) + ln(tr) - ln(tt) | 1 |
| `log_interaction_variance` | V = c' C c, c = (-1, 1, 1, -1) | 1 |
| `log_interaction_standard_uncertainty` | sqrt(V), conditional on the supplied covariance | 1 |
| `signed_profile_log_ratio` | S = e abs(e) / (2V), for the explicit known-normal point model only | 1 |
| `signed_index` | B = tanh(S/2), a bounded dependent representation of S | 1 |

Positive D above one means the test subject has a smaller test/reference reported parameter ratio than the reference subject. This direction is descriptive of that declared parameter; it is not an overall annotation score or reliability measure. No W05 credit or cross-component sum is introduced.

## Partial, censored and unavailable behavior

Individual parameters survive missing/conflicting other operands. Each within-subject ratio requires only its own valid pair and the appropriate within-subject mapping; it survives an unavailable four-cell interaction. Full interaction additionally requires all five core relationships supported, both ligand roles mapped consistently, a uniform parameter kind, and no role-reused source/physical fit.

A source-reported threshold is a separate threshold field, never an observed point. For each contrast, a denominator reverses a source limit's arithmetic direction. If every censored operand then pushes the contrast in the same direction, compute the corresponding product/ratio of printed thresholds, strict if any contributor is strict. This is labeled only `reported_limit_arithmetic`; it is neither a confidence interval nor an identified true-parameter bound. Opposite-direction limits leave the contrast direction uninformative and do not produce a ratio-of-threshold bound. Log threshold arithmetic preserves the same direction. Censoring never supplies a point for S or B.

Unknown source values, relationships and models produce explicit null cells and reasons, not zero. Logs are computed directly from source operands rather than from potentially overflowed D. Range failure of one representation leaves other representable cells intact.

## Optional observation model

`model` is null or a closed object with `version`, `parameter_kind`, `measurement_order`, `measurement_keys`, `log_basis`, `distribution`, `variance_status`, `log_covariance`, `source`. Version is `binding_interaction_log_model_v1`; order/owners match the four actual selected operands; log basis is `natural_log_nM`; distribution is `normal` or `unspecified`; variance status is `known`, `estimated`, or `unknown`. Known/estimated covariance requires all four source physical-fit IDs and a full actual symmetric 4-by-4 matrix. Unknown covariance is null. Source is an exact supported locator, not a generated receipt. No identity/default independence matrix is supplied.

Validate positive semidefiniteness and c' C c without jitter or invented tolerance using exact rational arithmetic on the supplied finite numbers. Singular covariance may be valid; V=0 is retained but does not generate infinite S. Estimated covariance may populate V and sqrt(V), but cannot populate the known-normal S/B. Unknown distribution/variance leaves S/B null. Fit spreads, minimum counts and repeated preparations never get promoted to a known-normal covariance.

S/B requires four uncensored positive points, actual exact model owners, known covariance, normal log observation model and V>0. This first finite design does not implement a censored joint likelihood. It explicitly reports that the reporting event/joint model is absent or unsupported rather than treating printed thresholds as statistical observations. No source-limit arithmetic is labeled a statistical success.

## Exclusive ownership and verification

After parent acknowledgment, create only `gene_annotation_episode/literature_binding_interaction_calculations.py`, `tests/test_literature_binding_interaction_calculations.py`, and artifacts in this 048 directory. Existing modules and all shared integration, storage, prompt, catalog and runtime files remain outside this workload.

Use synthetic inputs only, including rr=5, rt=40, tr=2, tt=4 giving D=4. Check exact cells and scope, partial pairs, missing/conflicting mapping, same-direction and opposite-direction multiple source limits, strictness, source/physical aliases, source-owner mismatch, preservation of shared identities across calls, known versus estimated/unknown covariance, correlations/PSD/zero V, stable log arithmetic, immutable inputs and an independent constrained-normal calculation of S. These establish a pure component, not installed operation/custody or whole A105 behavior.
