# Additive model-sensitivity clarification

This adds a useful inverse question to the frozen217 proposal. It changes no goal, source record, frozen proposal or accepted formula. It uses the same retained paper and the same explicitly conditional one-site equilibrium model. No second paper was opened.

**The 2mM scenario does not rule out binding-only loss in the actual product assay.** The paper explicitly gives 2mM for NADH loss but does not supply that linkage for Table3 product formation. An inverse calculation makes the consequence of that missing scientific information concrete.

Under equal-other-response, equal free S and binding-only turnover,

`R_P = (S+Kd_WT)/(S+Kd_mutant)`

and therefore

`S_required = (R_P*Kd_mutant−Kd_WT)/(1−R_P)`.

| Central displayed product comparison | Conditional free substrate required to explain that ratio by occupancy alone |
|---|---:|
| T252N versus WT: R_P=92/206, Kd_N=34, Kd_WT=1.8µM |24.1859649123µM|
| Double mutant versus WT: R_P=132/206, Kd_double=12µM |16.3945945946µM|

These are inverse model predictions, **not estimates of what the authors used**. The binding-only model can reproduce either central product ratio at a positive free substrate value, so the missing product-assay concentration matters. At stipulated2mM the same model leaves the residuals in the main proposal; at the inverse value it leaves zero residual by construction. Neither case proves a mechanism. Binding/catalysis temperature and preparation transfer, active fraction, recovery, background and other response remain unresolved.

Different inverse values for the two mutants do not establish statistically significant inconsistency or require different actual concentrations. That would need the same compatible assay/model scope and actual joint uncertainty, neither established here. T252A has no numerical ND limit and cannot supply an analogous inverse substrate estimate.

If adopted after discussion, an optional `binding_only_required_free_substrate` cell can accompany the proposed common-sheet residual. It needs the same product/Kd owners and explicit model, returns a conditional model value, preserves negative/nonphysical solutions instead of clamping them, and returns specific unavailable reasons for R_P=1, nonpoint/ND operands, unknown/incompatible normalization or unsupported model. It cannot create source facts, an actual assay correction or an overall evidence grade.

`check_model_and_inverse_001.py` independently forward-substitutes the exact inverse values and checks all five analytic log-residual derivatives in both comparisons using central finite differences. Ten derivative comparisons passed. It also verifies the direct occupancy and simplified residual expressions agree. These are standalone design-arithmetic checks, not production calculator, source-reader, model-backed literature or LiteratureEpisodes verification. The main159-witness/rational oracle remains unchanged.
