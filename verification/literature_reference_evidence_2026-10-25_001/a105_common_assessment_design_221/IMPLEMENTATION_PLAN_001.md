# Common A105 assessment: proposed compiler extension

Read/plan handoff only. No production code, existing tests, scientific policy or historical records were changed. The original supplied goal remains authoritative; this document is implementation planning evidence. Ten axes remain; only A105 is addressed here. Full A105 quality compilation, other literature responsibilities, W05, target transfer, final credit and continuation remain unfinished/outside this increment.

## Scientific conversion after this owner's post-paper reset

The source is Kim, Heo and Ortiz de Montellano (2008), PMC2577879. I read the complete retained primary text and inspected the original HTML tables. Purified Pseudomonas putida P450cam WT, T252N, T252N/V253T and T252A are assayed in separate arms with Pd/PdR partners. The intended variant change is distinct from unknown tagging/preparation/active-fraction differences. Culture and purification yields do not specify assay molecular amount. Product formation, NADH consumption, spectral binding and fitted kinetic parameters have different endpoint and population owners.

The common sheet must evaluate the functional assertion at its requested resolution. Table2 double-mutant saturation kcat/WT is 165/124 = 1.330645..., while its low-substrate efficiency contrast is (165/388)/(124/30) = 0.1028849.... These are different functional distinctions. Table3 native product contrasts are 92/206 and 132/206. Source Table3 rates must not be pooled with fitted Table2 kcat, whose WT central value is 124 rather than 206. Native ± tokens in Tables2/4 have unspecified parameter-uncertainty meaning; Fig5 plotted triplicate SD does not supply Table3 or cross-parameter covariance.

For explicitly stipulated shared free S=2000 µM and one-site occupancy, the binding-only predictions are 0.9841691... and 0.9949304..., while product/occupancy residuals are 0.4537858... and 0.6440417.... These decimals are the previously independently checked root219 oracles, not newly executed production results. Product-assay S and binding/catalysis applicability are unknown. The model can match the central product contrasts at shared free S=24.1859649... or 16.3945946... µM; those are fitted sensitivity points, not measured concentrations or validation. No rejection, p-value, causal fraction or overall grade follows.

The useful numerical combination is R_P = R_H R_rho and, under the named occupancy alternative, R_P = R_theta R_a, equivalently log R_P = log R_theta + D. These are model/measurement relationships. Product identity addresses reporter ambiguity; it does not measure a contamination fraction. Additional same-endpoint background B, applicable recovery k, active fraction f and nuisance response c could support a separately declared correction:

`a_test/a_ref = [(P_test-B_test)/(P_ref-B_ref)] * (k_ref/k_test) * (f_ref/f_test) * (c_ref/c_test) * (theta_ref/theta_test)`.

Each factor must have actual applicable operands and its own population/model relationship. For this paper B/k/f/c are unknown. Unknown factors cannot become numerical ones; the occupancy sensitivity is not this fully corrected physical result. A validity loss from individual standard readings also cannot be injected as covariance of a different selected mean.

Attribution means isolation of the measured effect; comparability concerns nuisance differences excluding the intended change; endpoint relevance concerns the asserted function; measurement validity and repeatability concern the selected measurement/model. Separate software populators feed one logical A105 sheet. They are not separate universal scores or independent experiments.

## Existing route and concrete limitations

The existing operation is `literature.assay.components.populate`, provided by `LiteratureEpisodes._population_catalog`, dispatched to `LiteratureCompiledAssayRepository.populate`. The repository currently supports v1/v2 request, input, sheet and record contracts, with distinct exact typed return namespaces, the same operation table, and per-version received tables. It binds upstream operands through `fact_cells` and snapshots exactly selected rows. A source ID or private sheet ID is insufficient numerical possession. `read` authenticates immutable request/payload/outcome relationships and projects the original saved cells; it does not repopulate arithmetic.

The current compiler's role set q/g/k/E/u/v and input allowlist do not include product212 rows, native kinetic rows, binding Kd or cross-arm contrast semantics. Simply adding generic ratios would not establish common scientific assessment. Its existing native per_min bypass must not be turned into q=concentration-rate and fictitious E=1.

The complete ordinary binding reader, calculator and storage were read. They accept only `ic50` and `reported_hill_kd`; `direct_binding_isotherm` in the design enum does not expand this parameter meaning. Native comparisons are ligand comparisons within one subject/state/experiment. The interaction reader inspected separately also declares IC50/reported-Hill-Kd meanings; it is image/four-cell specific and is not recommended for this spectral-Kd case. No claim of a newly installed spectral-Kd reader is made.

The complete kinetic input/calculation/storage/validation path was read. Its supported parameter meanings are Km/kcat/catalytic_efficiency. Its comparison requires same_molecule_and_construct; the WT/mutant contrast must retain intended_variant rather than mislabeling that relationship. Nevertheless `numerator_parameter` and `denominator_parameter` native rows survive an unsupported pair contrast. These selected rows carry their own value/unit, kind, subject/context references, measurement and unit anchors, qualifier and reported uncertainty. They can supply individual kcat and Km estimates to the common compiler without invoking the old comparison or opening the private full sheet.

Root has identified an independent215 validator defect: integer off-diagonal entries 10**17 and 10**17+1 can compare equal after floating conversion. My current compiler reads are the pre-fix215 baseline. The authorized exact-symmetry repair and its independent verification must land before common implementation uses those helpers. This plan neither changes nor accepts that defective baseline.

## Proposed exact compatibility contract

Retain the same selected compiler operation and provider. Add an explicit new branch; never reinterpret an old request or migrate saved output:

| Boundary | Proposed exact identifier |
| --- | --- |
| Request discriminator | `population_version = a105_common_assessment_population_v1` |
| Scientific request version | `version = a105_common_assessment_request_v1` |
| Bound input | `a105_common_assessment_inputs_v1` |
| Scientific sheet | `a105_common_assessment_sheet_v1` |
| Saved compiler record | `literature_compiled_assay_record_v3` |
| Exact typed return source | `literature_compiled_assay_v3_cells` |
| Parent-selected components | `requested_compiled_assay_components_v3` |
| Operation result view | existing `compiled_assay_components`, plus explicit sheet/record version |

The numerical contracts distinguish v1/v2/v3 by exact schema and original saved record version. V3 is a common-assessment request branch, not a claim that arbitrary v2 inputs now possess common assertion bindings. Existing v1/v2 schemas, saved values, request defaults, typed declarations and durability remain unchanged. The new type is one versioned compiler return; it must not be reported as another grader or another unrelated scientific module.

`compiled_assay_operation_schema()` becomes a closed anyOf of the two existing requests and the common branch. Storage chooses its branch from the explicit discriminator before validation and looks up original requested components for that branch. Reusing an operation key for different version/work remains invalid.

## Proposed shared scientific IO

Put the pure new reader/schema functions in existing `literature_compiled_assay_inputs.py`, and pure numerical functions in existing `literature_compiled_assay_calculations.py`:

`common_assessment_population_schema()`

`read_common_assessment_inputs(request, *, read_source, read_component, read_record)`

`populate_common_assessment(bound_inputs)`

The reader receives no model/credit/controller callback. The calculator receives no IO callback. Initial assembly, including validation of dependent arithmetic, happens once in the selected operation. Cold saved reads use structural bindings and immutable original selection/artifact/outcome authentication, with no reader, calculator, interpretation, acquisition or receipt insertion. This corrects the ambiguous217 phrase about checking dependent arithmetic “on save/read”: scientific calculation belongs to population, not cold read.

Request contains separately closed blocks:

1. **Assertion:** actually assayed subject/construct, substrate/product-or-ligand, system and condition witnesses; resolution `identified_product_formation`, `saturation_turnover`, `low_substrate_efficiency` or `binding_occupancy_alternative`; question `existence`, `relative_effect` or `named_alternative`. It need not predate investigation. No target-transfer information or hidden threshold.
2. **Contrast and arms:** nominated test/reference, actual assay, endpoint, denominator, preparation and sampling-unit references or explicit unknowns; intended variable and witnessed additional differences. A generic publication ID cannot serve as an assay or measurement population.
3. **Estimate selections:** nullable role selections for product/cofactor/kcat/Km/Kd per arm, and separately optional same-scale background, recovery, active_fraction and nuisance_response. Each tagged selection is either a precisely received native component or a witnessed source-parameter selection; no generic supplied-number dictionary.
4. **Scoped relationships:** restricted witnessed subject/endpoint/normalization/preparation/condition/sampling links for the actual involved estimates, not one global comparability C. `intended_variant` is distinct from `same_construct_supported`. Native descriptive comparison does not require invented nuisance equality; causal/model corrections require their own supported relationships or explicit sensitivity stipulations. `unknown`/`conflicting` remain meaningful.
5. **Model:** none or an explicit one-site equilibrium sensitivity. Free S is selected per arm from actual source or supplied model material, with its own estimate/physical owner and status. Shared S is an explicit shared owner, never inferred from equal values. Equilibrium, one site, free-vs-total treatment, Kd applicability, turnover proportionality and held-equal other responses are independently witnessed `supported`, `stipulated_sensitivity`, `unknown` or `conflicting` meanings.
6. **Joint uncertainty selections:** optional received source block(s) with exact ordered estimate owners, units, dependency keys, covariance basis/origin and known/estimated/unknown status. A scalar mean's original raw-reading spread is not substituted. Actual signed cross terms are required wherever the requested estimand needs them; separate marginal blocks do not provide zero cross terms. No double addition of covariance already owned by a derived estimate.
7. **Requested cells:** unique component names, constrained by the parent-selected requested component list; the return cannot expand the assignment.

### Actual numbers entering the common assembly

**Product/cofactor:** after218 publishes and freezes its selected path, accept only its exact registered version of `reported_product_activity` / `reported_cofactor_activity` (and, if useful, the descriptive ratio) through `fact_cells`. Preserve exact_value, native-zero/ND qualification, source identity, measurement/model keys and input origins. Do not read `saved['sheet']['extraction']` to obtain an unreceived other arm. Derived ratios require either their received primitive Jacobians or covariance explicitly owned by those derived estimates; the first bounded implementation can prefer received native P/H rows and avoid deriving nonexistent primitive information.

**kcat/Km:** accept only native `numerator_parameter` / `denominator_parameter` rows from `literature_kinetic_cells`, never old ratio/log/profile rows as substitutes. Determine the selected native side from the component. Match role's kind and canonical unit with that side's metadata. Validate row membership, status, relation, qualification and the actual selected subject/context/measurement population. Keep the existing kinetic family unchanged. Exact original source numeral/unit anchors may be authenticated at first assembly through the selected row's own public bindings; this does not authorize reading the other side's numeric values or private extraction. If exact source-token conversion cannot be established, retain only the saved canonical decimal as that explicit numeric origin or return a specific exact-input limitation; do not claim original-source exactness. For the current integer central kcat/Km case the anchors establish exact rational operands.

**Spectral Kd:** add a narrow prospective source-parameter role inside this common compiler, not a separate operation or a relabelled kinetic/Hill input. Select central value, original unit, quantity/header and row/construct witnesses, spectral-titration method and reported spread/its actual meaning. Reuse generic custody, full-token parsing and association helpers only under the new explicit `spectral_binding_dissociation_constant` meaning. Preserve `reported_Kd` with unspecified fit/model details; the one-site occupancy use is a separate conditional model. A ±2 token remains reported spread with unknown statistic; it does not create variance 4. The source reader must bind row/column/header/footnote relationships, not merely authenticate occurrence of “34.”

**Corrections:** only select existing applicable recovery/amount/active-site/within-assay rows and their own received meaning. Do not infer active fraction from amount ratio or culture yield. A generic recovery requires correct analyte/matrix/endpoint/population; a nuisance response must exclude the intended variant. Full corrected-ratio cells stay unavailable without all actual applicable operands and explicit response factorization. If no bound selected row supplies a correction's exact needed meaning, return `implementation_reasons` rather than inventing a conversion.

## Numerical sheet cells and uncertainty

First populate the217 bounded cell set: native P, H, productive-use, same-parameter kcat and low-substrate kcat/Km reference contrasts; per-arm occupancy; occupancy contrast; signed prediction error; post-binding residual ratio; log residual; and, only with applicable joint uncertainty, its variance/standardized/squared-standardized residual. Add optional full corrected ratio only under the stated actual-operand model. Keep numerical values separate from metadata supporting eligibility.

Each returned cell has fixed component/formula/meaning; native or conditional numerical domain; exact rational where applicable; explicit float-log/root origin where needed; value vs conditional_value; fixed unit; status `populated`, `conditional_scenario` or `unavailable`; source_missing_reasons, relationship_reasons and implementation_reasons; operand/model owners; dependence/contribution identity; and estimator-specific uncertainty metadata. No generic confidence or numeric category weight.

The shared-S log-residual gradient is `(1/Pt, -1/Pr, 1/(S+Kdt), -1/(S+Kdr), 1/(S+Kdt)-1/(S+Kdr))`. With separate S owners, use derivatives `-1/St+1/(St+Kdt)` and `1/Sr-1/(Sr+Kdr)` separately. Stipulated fixed S has conditional fixed-input propagation, not a claim that the physical S has zero uncertainty. Preserve reused WT/standard/measurement owners across comparisons. Covariance is JΣJᵀ for the actual requested component. Estimated covariance stays estimated. Positive variance is required for standardized residuals; no distribution or p-value is assumed. Table3 absence of covariance leaves those cells unavailable while means survive.

Exact matrix equality/owner checks precede any floating numerical range/PSD calculation. Use the repaired215 helper only if its input semantics actually match; do not reuse its hardcoded q/g/k/E/u/v owner meanings for new physical roles. Tests must include integer off-diagonal values distinguishable exactly but indistinguishable as floats, repeated owners and signed covariance.

A different endpoint can be complementary without being an inconsistent repeat. Store simultaneous dependence links (shared primitive, same sampling unit, complementary endpoint, unknown independence). Same-estimand disagreement requires matching estimand/subject/scope or an explicit supported model. This increment provides the binding and numerical residual; broad contradiction compilation/design coverage remains explicitly unfinished. No evidence count follows from module count, transformed cells or distinct printed numbers.

## Full selected consumer path to implement after exclusive release

| Stage | Actual existing consumer and required extension |
| --- | --- |
| Capability and saved implementation | `LiteratureEpisodes._population_catalog`, constructor flags and binding descriptor retain compiled_assay_population; catalog exposes the added request branch under the same operation. Save exact schemas/code binding without changing old saved contracts. |
| Parent assignment | Existing commission schema gains `requested_compiled_assay_components_v3`; retain the parent-defined requested typed form and source scope. No mandatory child arrangement. |
| Initial and subsequent decision | `initial_decision_context`, `decision_context`, compiler work marker and contract lookup relevance supply substantive common TASK when selected/relevant; no sheet dump. |
| Selection and execution | Existing `_tool_arguments` recursively checks all source/model/covariance/selected-sheet references against the assigned page; `execute` retains its same selected-operation dispatch. V3 storage uses read_source plus exact upstream `fact_cells`, not private sheet projection. |
| Populate/save | Existing compiler repository branch reads and computes once, snapshots selected rows/source metadata, stores request/extraction/sheet/output and durable original outcome in one transaction. Structured scientific partials survive; unauthorized scope/receipt claims remain structured action failures. |
| Cold read/replay | New record branch authenticates content-addressed source/request/payload, original selected operation/signature/outcome and structural bindings. Preserve source metadata/current registry relationships without reacquisition, arithmetic, interpretation, new receive or state installation. |
| Fact projection and admission | `_rate_fact_sources`, `_population_routes`, `_rate_facts`, `receive_report`, `validate_received_report`, version filtering and exact requested-subset checks route v3 to its projection. Add the new record version explicitly; no fallthrough to v1/v2. Select only rows the reporting episode owns or actually received. |
| Reference custody | Compiler `cell_record_refs` and LiteratureEpisodes report reference collection include assertion/assay/selected numeric/model/covariance bindings that the closed row declares. IDs remain outside model-facing prose. |
| Exact type | `communication.py` source branch and `literature_numerical_contracts.py` register the exact v3 schema. Saved frozen contracts keep their original snapshots; no current-factory replacement of old contracts. |
| TASK/STEERING | Existing compiler prompt/render and experimental prompt relevance/local-outcome/child-return paths handle v3 explicitly. The root will first print the full reusable comparison TASK for feedback. Keep recurring detailed work instructions separate from concise returned numerical facts/qualifications. Contract lookup remains abstracted through numerical-return presentation; no raw internal scoring schema in prompts. |
| Scientific parent | The parent's original requested form receives exact admitted rows and needed qualifications, not an extra model report, private child history or unrequested native values. Ordinary own-action/child-return accounting stays unchanged; no new credit/controller code. |

This is a concrete implementation trace, not a claim that v3 is installed or that all shared consumers have been fully re-audited. The complete compiler files and selected native product/kinetic/binding implementations were read. Shared episode/prompt/communication consumers were inspected at the actual relevant branches; their final changed complete functions must be reread after218/215 freeze before edits, since those owners still hold shared files.

## Ownership and verification sequence

1. Root prints the full reusable TASK and resolves this proposed IO with current human feedback. This is implementation review, not a runtime reviewer/gate.
2. Root completes/reviews the exact215 covariance fix and freezes the new baseline.218 finishes and freezes its product storage/render/typed route. Never edit these owners' files concurrently.
3. On explicit root release, a related221 followup can own only existing `literature_compiled_assay_inputs.py`, existing `literature_compiled_assay_calculations.py`, a new focused common-assessment test, and its new verification artifacts. Add pure closed request/extraction/schema/calculator functions without advertising an unbound operation. No edits occurred in this read/plan workload.
4. A separately exclusive integration owner handles existing compiler storage/prompt/render, shared `literature_episodes.py`, `communication.py`, `literature_numerical_contracts.py`, `literature_numerical_return_presentation.py`, `literature_experimental_prompt.py` and any saved-binding consumer actually changed. Read their complete affected functions on the frozen218/215 baseline first. Root can assign this related owner after release; this plan does not claim authority to edit them now.
5. Focused scientific verification: exact source table/row/header association; mutant labels and wrong endpoint denial; Km versus spectral Kd versus Hill Kd; native unsupported contrast still exposing selected parameter; actual product rows and selected-only receipt denial; ND/limits/unknown active fraction; separately owned vs shared S; conditional vs supported models; missing/conflicting relationships; exact signed/full joint uncertainty and integer symmetry defect; shared WT; full corrected ratio only with actual applicable factors; nonlinear/inapplicable correction partials. Compare current paper cells to root219 independent oracle, including synthetic joint-error-mode cases clearly labelled synthetic.
6. Connected selected-operation verification: same existing compiler name with v3 request; exact registered child form/parent-selected subset; model-free deterministic population; parent receives only requested rows; replay returns the original outcome; cold restart with source reading, acquisition, interpretation, calculator and receive methods trapped to fail; unchanged operation/receipt/action counts; original v1/v2 requests/results/restoration retained. Tampered immutable bytes or request/row/version/outcome relationships fail structurally without repair calculation.
7. Report actual controlled fixtures and actual model-backed execution separately. Pure tests do not complete selected integration, a complete common sheet, general reliability/validity/relevance compilation, contrast coverage, A105, W04 or the immutable full goal.

No tests or model-backed literature operations were executed by221. Two failed local inspection conveniences (`python` absent; `bs4` unavailable) were replaced by standard-library HTML table inspection without installation or scientific mutation. No private provider payloads were accessed.
