# NlpI binding: first paper-specific scoring-sheet research return

New research proposal, not an adopted sheet, reader, or annotation-credit rule. One newly reread primary paper from the retained corpus; not a newly discovered paper. First sheet of ten remains incomplete.

## Experimental definitions and measured facts

Source: [Banzhaf et al., 2020, Figures 2 and 4; binding and purification Methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC7049810/). E. coli proteins were recombinantly produced in BL21(λDE3); the binding assays used purified, soluble NlpI lacking its membrane anchor. There is no wild-type/deletion organism comparison in this row. Labelled MepS, NlpI, and PBP4 coexist in the ternary condition; PBP4 addition is the intended change. MST buffer: 25 mM HEPES, 150 mM NaCl, 0.05% Triton X-100, pH 7.5. Preformation: 3 μM NlpI plus 30 μM PBP4. Exact tracer concentration and tag/variant assignment for every plotted sample remain unresolved here.

Figure 2A reports mean ± SD, three independent experiments: NlpI–MepS apparent Kd 145 ± 52 nM; NlpI–PBP4 177 ± 49 nM; PBP7 apparent EC50 422 ± 25 nM with Hill coefficient approximately 3. Figure 2C prints normalized fluorescence ×1,000: MepS 894 ± 0.82; MepS/PBP4 900 ± 4.23; MepS/NlpI 914 ± 3.11; MepS/NlpI/PBP4 943 ± 2.25; MepS/NlpI/BSA 913 ± 3.09. Its experiments number 3–6. Denaturation and pull-down controls are reported. Supplementary PDF access failed; its detailed data were not read.

## Moving those measurements into the user's sheet

These belong to part 2, numerical scoring cells. The prompt remains part 1, and future readers that extract means, SDs, concentration metadata and sample identities would populate these exact cells as part 3. No reader is implemented here.

The emerging, narrowly measured statement is that adding PBP4 to a purified NlpI/MepS mixture produces a binding-related assay response beyond the PBP4/MepS control. A separate row describes the pairwise apparent affinity. Neither row scores cell-wall synthesis, activation, organism fitness, or membrane-localized assembly. Perturbation, restoration and growth results are parked for A106.

### Comparability outside the changed variable

The PBP4 concentration change is the test variable and receives no mismatch penalty. The relevant nuisance differences include tracer concentration, NlpI concentration, salt, pH, temperature, tag/label state, solvent, and active preparation fraction. A shared nominal recipe establishes equality only for the specified recipe values; it does not establish equal active concentrations or labeling behavior.

Proposed continuous calculation for the measurable nuisance differences:

`C = exp[-0.5 × sum_j((beta_j × delta_j / tau)^2)]`.

Here `delta_j = ln(x_test,j / x_control,j)` for positive concentration or activity quantities; pH uses an ordinary difference. `beta_j` is a measured sensitivity of log binding response to that nuisance variable, from a matched nuisance titration. `tau` is a declared scoring tolerance in log-response units, not a measured uncertainty. Only nuisance terms enter. The sum assumes the named differences are not duplicating the same physical alteration; correlated changes instead require a covariance-aware joint discrepancy. Discrete construct differences need measured interchangeability or separately scoped interpretation; they are not assigned a category number.

For identical stated salt and pH, their discrepancy terms are zero and their factor is 1. That is a partial result, not a total comparability score. Missing tracer/activity measurements and sensitivity coefficients leave the complete C unknown.

Synthetic illustration: if salt differs from 150 to 165 mM, measured elasticity is assumed to be beta = 1, and the proposed tolerance is tau = ln(2), then C_salt = exp[-0.5(ln(165/150)/ln(2))²] = 0.99059. These invented sensitivity/tolerance inputs illustrate the arithmetic; they are not NlpI results. A sensitivity twice as large changes the penalty continuously. Thus 10% concentration mismatch is not automatically 10% loss of relevance.

### Isolation of the measured increment

Let `F_NP` denote tracer plus NlpI plus PBP4, `F_N` tracer plus NlpI, `F_P` tracer plus PBP4, and `F_0` tracer alone. All F operands are on the same ×1,000 normalized-fluorescence scale.

The observed increment is `A = F_NP − F_N = 943 − 914 = 29`.

The measured comparator increment is `B = F_P − F_0 = 900 − 894 = 6`.

The interaction contrast is `D = A − B = 23`. Proposed isolation cell:

`I_additive = clip(sign(A) × D / abs(A), 0, 1) = 23/29 = 0.79310`.

This is the fraction of the observed increment remaining after the explicitly measured comparator increment under an additive-background model. It is not a probability of binding, molecular purity, or a ternary-complex fraction. Preserve A, B, D and their signs beside the score. A = 0 leaves the ratio undefined. If the background effect changes when NlpI is present, that additive model is inadequate; the fraction is then a model-dependent diagnostic, not a populated attribution fact.

The BSA comparison has increment 913 − 914 = −1. It interrogates a different generic-protein effect. Do not add its absolute value as a second background penalty without a model showing distinct additive contributions. Do not count the BSA and PBP4 comparisons as independent demonstrations of the same binding event.

For uncertainty, D uses contrast vector a = (+1, −1, −1, +1), so `Var(D) = a' Sigma a`. Exact sample pairing, covariances and group sample counts are unavailable in this review. Assuming independent SDs only as a diagnostic gives `sqrt(2.25² + 3.11² + 4.23² + 0.82²) = 5.77061`; this is neither the SE of D nor a justified hypothesis-test statistic. The mean contrast is calculable; its defensible interval still requires sample-level operands.

### Measurement validity, signal and precision are distinct cells

For the named optical-artifact weakness, propose `M_optical = clip(1 − abs(A_after_denaturation)/abs(A_before_denaturation), 0, 1)`, retaining both measured amplitudes. It quantifies disappearance of the same concentration-associated optical contrast after a treatment that abolishes binding. It does not eliminate every aggregation or labeling explanation. The required numerical post-denaturation contrasts are unavailable here, so this cell stays unknown; prose saying the control was done does not become 0.75 or 1.

For technical signal separation, propose `S = D²/(D² + sigma_technical²)`, retaining sign(D), D and its units. `sigma_technical` must come from independent technical blank/calibration variation for this contrast. This maps a continuously measured signal/noise ratio to [0,1]; it is not a probability. The present SDs do not establish a separate technical-noise variance, so S is unpopulated for this ternary comparison.

For affinity reproducibility, native `CV_K = SD(K)/mean(K)` is 52/145 = 0.35862 for the MepS apparent Kd and 49/177 = 0.27684 for the PBP4 apparent Kd. Proposed precision cell `P_K = 1/(1 + CV_K²)` yields 0.88605 and 0.92882. This measures relative dispersion of the reported affinity estimates, not correctness of the binding model. The number of independent experiments remains 3; this does not establish three independent protein preparations. An affinity SD cannot also be entered as a second independent consistency bonus.

A lower Kd is not automatically stronger annotation evidence. PBP7's EC50 and Hill coefficient must retain their meanings: an EC50 from a cooperative curve is not interchangeable with a 1:1 dissociation constant, and a Hill coefficient is not the number of molecules in a complex. Stoichiometry needs its own quantitative measurement.

### Explicit proposed compilation

For one defined binding contrast, with all cells actually measured, a candidate numerical compilation is:

`B_assay = 100 × C × M_optical × I_additive × (0.5 × S + 0.5 × P_D)`.

`P_D = 1/(1 + (SD_between_preparations(D)/mean(D))²)` is precision for that same contrast. It cannot be borrowed from the pairwise Kd row. The 100 scale and equal 0.5 weights are proposal choices, not source measurements. C addresses comparability; M addresses a specific assay artifact; I discounts the measured mixed contribution; the weighted signal/precision term describes resolution of the retained contrast. Shared observations enter one joint row with covariance, not multiple independent experiment credits. If technical and preparation variances cannot be separated, use a single measured resolution term instead of multiplying or averaging two names for the same variance. No complete B_assay is reported for NlpI because its required numerical operands are incomplete.

Fully synthetic arithmetic illustration, unrelated to ybhP or the paper: salt inputs as above give C = 0.99059; a pre-denaturation amplitude of 40 and residual 2 give M = 0.95; 50 total increment minus 10 measured background gives I = 0.8 and D = 40; technical noise SD 5 gives S = 1600/1625 = 0.98462; independently estimated preparation SD 6 gives P_D = 1/(1 + (6/40)²) = 0.97800. The proposed score is 100 × 0.99059 × 0.95 × 0.8 × (0.98462 + 0.97800)/2 = 73.87748. This is an inspectable mathematical proposal, not an overall expert grade encoded as a number.

For a target annotation, this experimental score still requires the separately measured relationship between the actual assayed construct and the supplied target, plus compatibility with the target system. A possible explicit combination is `B_target = B_assay × T_molecule × C_system`, but those factors must themselves be populated from actual correspondence measurements or a specifically scoped justified judgment when none applies. This paper supplies no ybhP correspondence, and no target score is assigned. Treating the soluble-domain result as automatically equivalent to native membrane scaffolding would skip that missing relationship.

## Complementarity and unresolved work

Reciprocal labeling and a label-free binding measurement would address fluorophore dependence. Quantified pull-down background can address retention without the MST optical signal; it does not automatically share the same numerical endpoint or supply an independent affinity estimate. A directly measured bound fraction and species-resolved mass/stoichiometry would address the distinction between a fluorescence shift and ternary occupancy. Comparable independent preparations would supply between-preparation variance. Native membrane-tethered versus soluble constructs would address system-transfer compatibility.

The exact tag/variant assignment deserves primary supplementary verification: the Methods mention unlabelled MepS(C68A), whereas the plotted tracer is labelled MepS. Do not silently assume that every affinity or complex experiment used the same MepS construct. The source access retained the primary HTML and Figure 2 image; the attempted appendix download returned HTML, not a PDF, and is preserved under an explicitly non-PDF filename.

## Actual read/reset provenance

Primary sections newly inspected: direct-binding Results through pairwise/ternary/synthase associations; corresponding Figure 2 visual and captions; recombinant production/purification, MST, denaturation, fixed-concentration complex, AUC and pull-down Methods. Neighboring phenotype/activity paragraphs were encountered but not converted into A105 binding scores. No raw MST fits, new assay, native-complex experiment, source-data spreadsheet, or appendix analysis was performed.

After the primary read and before this summary, the complete following documents were reloaded and read: root AGENTS.md; GOAL.md; docs/EPISODE_STRUCTURE.md; docs/TIME_AWARE_ESTIMATION.md; docs/TOOL_KNOWLEDGE.md; docs/TASK_AND_STEERING.md; docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md; docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md; publications/2026-10-23-002/VERBATIM_DIRECTION.md and VERBATIM_RECOVERY_002.md under research/slotted_process_library; docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md; verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md; local AGENTS.md; full A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md. SOURCE_CORRECTIONS.md was reread too. One combined read truncated 18 tokens in the numerical toy table, so that whole numerical document, local AGENTS.md and assignment brief were immediately read again without truncation, with current human directions last. The initial multi-case index inventory is not counted as a paper review.

Arithmetic was recomputed with Python standard-library operations; no repository test suite or scientific run was executed. All outputs are new files within template_a105_binding_001. No existing record or implementation was changed.
