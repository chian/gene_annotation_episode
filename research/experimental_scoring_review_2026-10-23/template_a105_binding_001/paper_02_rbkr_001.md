# RbkR DNA binding: second paper-specific scoring-sheet research return

New part-2 research proposal. No prompt, reader, scorer, library or run is changed; no evidence-axis sheet is completed. This is a fresh primary reread of one retained source, not a newly discovered paper.

## Experimental definitions and source facts

[Rodionova et al., 2017, DNA-binding Methods, Results and Figure 4](https://pmc.ncbi.nlm.nih.gov/articles/PMC5397151/) study purified RbkR from Metallosphaera yellowstonensis, Pyrobaculum yellowstonensis and Thermoplasma acidophilum. Recombinant expression uses E. coli; my/py proteins have cleaved His–SUMO tags, while taRbkR has a C-terminal His tag. The protein homologs are assayed separately, not coexpressed together. Test variables are protein concentration, DNA sequence, or effector identity/concentration, depending on the comparison.

FPA uses 24°C, pH 6, 10 nM DNA and 50 mM KCl; pyRbkR EMSA uses 62°C, pH 8, 0.2 nM DNA and 200 mM NaCl. Controls include taRbkR 35-bp scrambled DNA, pyRbkR 62-bp altered DNA, and myRbkR 28-bp unrelated DNA versus 38/60-bp targets. Figure 4D uses pyRbkR 60 nM, DNA 15 nM and effectors 200 nM. Reported response EC50 values are FMN 41 ± 5 nM and riboflavin 144 ± 17 nM; taRbkR–DNA EC50 is approximately 16 nM. Figure errors describe triplicates, without establishing independent preparations. Methods/caption disagree on EMSA target length: 104/102 bp. myRbkR+CTP text says EC50 100–110 nM; Figure 4A's μM scale places half-rise near 1 μM. Neither inconsistency is resolved here.

## What each comparison can populate

The protein-concentration curves concern binding to specified DNA under specified conditions. The flavin curves concern change of the DNA-binding readout with added compound. The latter does not directly measure the dissociation constant of the compound–protein interaction. The structural occupancy observations are separate structural-axis evidence and supply no invented binding curve. Transcriptional direction and native consequences are not binding-score outputs. Genetic/restoration interpretation is parked for A106; catalytic data are outside this binding-only review.

Each candidate cell below belongs to the user's numerical sheet, part 2. Separate targeted readers would later populate its operands from experiments or datasets. They are not an instruction block to insert wholesale into the investigation prompt.

### Experimental comparability

For target versus altered DNA of the same length with one RbkR preparation, the DNA sequence difference is intended and receives no mismatch penalty. Protein concentration, active fraction, DNA molarity, label chemistry, buffer and temperature are nuisance quantities. A different-length negative fragment can change the fluorescence baseline, hydrodynamic response, nonspecific binding capacity and number of possible sites independently of the nominated operator.

The proposed comparability calculation from the first paper remains:

`C = exp[-0.5 × sum_j((beta_j × delta_j/tau)^2)]`.

Concentration or length differences use `delta_j = ln(x_test/x_control)`; temperature and pH use their native differences. beta_j is measured response sensitivity for that nuisance. tau is a declared tolerance for a nuisance-induced change in the chosen response metric. The intended DNA sequence or compound change is excluded. Different nuisance descriptions of the same change do not receive duplicate terms. A matched sensitivity experiment can quantify what the mismatch would do; its presence is not awarded a categorical point.

For demonstration only, beta_length = 1 and tau = ln(2) convert length 38/28 into 0.90751 and 60/28 into 0.54635. These are SYNTHETIC sensitivity assumptions applied to actual fragment lengths, not proposed paper scores. A measured negligible length sensitivity would instead give factors near 1. DNA length ratios alone do not establish their biological impact.

The FPA/EMSA differences are 38°C, 2 pH units and a 50-fold DNA concentration ratio, with additional salt, label and fragment differences. That makes the two measurements complementary under different conditions, not interchangeable numerical repeats. C for pooling their affinities remains unpopulated. A matched-condition bridge experiment, with response sensitivity measurements, would be the appropriate source of numerical corrections.

### Isolation of site-dependent binding signal

For one assay and fixed protein concentration, define normalized response per fragment:

`u = (FP − FP_free)/(FP_saturated − FP_free)`.

FP_free and FP_saturated must be experimentally established for that fragment and labeling arrangement; a missing plateau is not replaced by the largest observed value. This u is a normalized assay response, not automatically molecular occupancy. Conversion to bound fraction additionally requires validation of the optical mixture model and changes in brightness.

Let A = u_target and B = u_matched_negative at the same protein concentration. Define `D = A − B` and the proposed site-isolation cell `I_site = clip(D/A, 0, 1)` for A > 0. This measures the response retained after the selected negative-DNA comparison. It does not establish that every remaining response molecule has the nominated contact geometry. Target and negative traces must be jointly fit with sample covariance rather than treated as independent discoveries.

SYNTHETIC example: A = 0.80, B = 0.10, so D = 0.70 and I_site = 0.875. The genuine source graph shows why the needed control exists, but these example amplitudes are invented. Raw curve points, fragment-specific reference values, covariance and adequate saturation data were not extracted here, so the actual I_site remains unknown.

Effect isolation is also distinct from chemical purity. A reported mass purity cannot itself become the fraction of binding attributable to the named protein. In a linear, calibrated mixture model, an attribution fraction would be `I_protein = f_P a_P / (f_P a_P + sum_c f_c a_c)`, where f are component mass fractions and a are signal contributions per unit mass under the same assay. SYNTHETIC example: 90% target protein, 10% contaminant, and contaminant contribution per mass ten times larger gives I_protein = 0.9/(0.9 + 0.1×10) = 0.47368, not 0.90. This is a thought experiment, not a claim of contamination in RbkR. Purity measurements and response-specific attribution answer different questions.

### Validity of the binding model and signal

Finite ligand concentrations matter. If one DNA binding unit binds one protein binding unit and half the DNA is occupied at total protein concentration C50, mass balance gives `Kd = C50 − D_total/2`. Using 16 and 10 nM would give 11 nM and a depletion fraction `D_total/(2 C50) = 0.3125`. This is a CONDITIONAL model illustration from reported quantities, not a corrected RbkR Kd: protein oligomeric counting units, active fraction, response-to-occupancy mapping and site model must first be established. The primary result remains an apparent EC50.

With actual curves, define `e_model = RMSE(predicted response − observed response)/abs(fitted response span)` and a proposed validity component `M_model = 1/(1 + e_model²)`. The predictions must use the stated concentration/mass-balance/stoichiometry model; residuals and uncertainty remain visible. This component assesses fit adequacy relative to the observed span; it does not prove the model is unique. Compare a simple model and a mass-balance model using the same raw data and retained parameter uncertainty. Do not add their scores as separate experiments. A good empirical Hill fit still does not yield molecular stoichiometry.

For a specific optical-interference check on compound-dependent signal, define `M_optical = clip(1 − abs(D_compound_without_protein)/abs(D_compound_with_protein),0,1)`. This requires the same labelled DNA, compound concentrations, solvent and optical protocol. It evaluates the measured protein-independent optical change; its operands are absent from this review. Quantifying the protein recovered after effector incubation/ultrafiltration would separately test whether altered active concentration explains the comparison. Neither control becomes an automatic full-validity score merely because the method is mentioned.

Retain technical signal separation `S = D²/(D² + sigma_technical²)` and preparation precision `P_D = 1/(1 + (SD_between_preparations(D)/mean(D))²)` when the two variance sources are actually separated. Triplicates within a preparation cannot populate the latter. Exact signals, noise and independent preparation identifiers are missing here.

### Specificity of the effector response

The reported midpoint ratio is `R_effect = EC50_riboflavin/EC50_FMN = 144/41 = 3.51220`. It compares potencies for decreasing the DNA-binding readout under the tested conditions. It is not a direct flavin-affinity ratio.

For the narrow statement that FMN is more potent than riboflavin for this effect, a proposed preference component is `Q_effect = (R_effect − 1)/(R_effect + 1) = 103/185 = 0.55676`, retaining the signed raw ratio and chemical comparison. Q = 0 means equal midpoint potencies, not no DNA binding. Q approaching 1 means a large preference for the specified direction. Use the opposite sign to describe the reverse comparison; do not silently clip contradictory evidence into support. The ratio and Q are not separate evidence contributions.

A conditional relative-uncertainty diagnostic is `u_R = sqrt((17/144)² + (5/41)²) = 0.16973` if the two uncertainties are on the same independent scale. Proposed `P_R = 1/(1 + u_R²) = 0.97200`. Exact uncertainty meaning and covariance for these two fitted midpoints were not established in this read, so this is explicitly conditional arithmetic rather than a populated inferential precision score. With covariance, subtract `2 Cov(K1,K2)/(K1 K2)` inside the relative-variance expression.

### Explicit compilation and consistency

For a defined site-dependent binding contrast, propose:

`B_binding = 100 × C × M × I_site × (0.5 S + 0.5 P_D)`.

M represents the numerically assessed, relevant measurement weakness; if several distinct measured weaknesses must jointly be addressed, propose the product of their distinct validity factors, retaining every factor. A factor based on the same background already used in I_site is not multiplied again. Unknown factors remain unknown; no numerical grade is inferred from control prose. The scale and weights are declared proposals, not values supplied by a paper.

Fully SYNTHETIC arithmetic: matched-condition measurements give C = 0.98; an optical comparison gives M = 0.96; normalized target/control responses 0.80/0.10 give I_site = 0.875 and D = 0.70; independent technical SD 0.05 gives S = 0.99492; between-preparation SD 0.07 gives P_D = 0.99010. Then B_binding = 100 × 0.98 × 0.96 × 0.875 × (0.99492 + 0.99010)/2 = 81.70354. These are invented inputs illustrating compilation, not a RbkR score.

For the separate narrow effector-preference statement, propose `B_preference = 100 × C × M × I_effect × P_R × Q_effect`, with separate controls for I_effect and the exact effector comparison. Do not borrow the DNA-site isolation factor into an effector row merely because both occur in the same paper. Do not sum B_preference into B_binding as an independent binding occurrence. Its function is to qualify the measured binding behavior.

For genuinely repeated measurements of the same affinity under matched conditions, consistency can be quantified on log concentration: estimate excess between-experiment variance `tau_between² = max(0, variance_between(log K) − mean(within_variance(log K)))`, using a declared variance estimator and independent experiment units. Then propose `K_consistency = exp[-tau_between²/(2 tau_allowed²)]`, where tau_allowed is a stated tolerance, and multiply the combined matched-result contribution by this component. This is separate from within-preparation precision only when the variance partition is identifiable. FPA and EMSA here do not supply that matched design, so no consistency score is manufactured from their common positive conclusion.

No correspondence to ybhP or another supplied annotation target was measured here. Experimental relevance to such a target requires its own actual sequence/structure/determinant/system operands, not a species-name category. A prospective target contribution can multiply the measured assay contribution by separately populated molecule-correspondence and system-compatibility components; both remain unknown here.

## Useful consequences for the sheet and remaining operands

This case requires a named binding species, state, DNA/ligand, endpoint and concentration model. It cannot be represented by one paper-wide binding score. A native KD, an empirical binding EC50, an effector-response EC50, and a crystal occupancy retain distinct meanings. Strong site-dependent binding supports that measured interaction; its biological regulatory direction needs separate observations.

Needed inputs for actual scores: raw fluorescence values and free/saturated references; matched optical blank effects; exact concentration and active-fraction measurements; condition-response sensitivities; paired sample identities and covariance; midpoint uncertainty definitions; independent preparation identities; treatment/sham recovery; resolution of the myRbkR unit discrepancy and EMSA fragment lengths. These are specific remaining calculations and source checks, not a rationale for falling back to categorical reliability.

## Actual read/reset provenance

Newly read primary material: complete cloning/purification and DNA-binding Methods; the complete experimental dual-function Results section (with chemistry set aside); DNA-binding figures/captions; the structural passage needed to distinguish its experiment from the binding assay; the concluding limitation on native regulatory direction. Figure 4 was downloaded and visually inspected. No raw-curve digitization/fitting, assay repetition, structure analysis or supplemental ZIP analysis was performed. The printed uncertainty scale for individual effector midpoint estimates remains unverified.

After this source read and before the scoring summary, the whole authority set was reloaded in six untruncated sequential reads: root AGENTS.md; GOAL.md; docs/EPISODE_STRUCTURE.md; docs/TIME_AWARE_ESTIMATION.md; docs/TOOL_KNOWLEDGE.md; docs/TASK_AND_STEERING.md; docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md; docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md; research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md and VERBATIM_RECOVERY_002.md; docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md; verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md; local SOURCE_CORRECTIONS.md; whole local AGENTS.md; whole A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md, with current human instructions last. No newer task correction was received during that reset.

Arithmetic was independently recomputed with Python standard-library operations. All files are new in the assigned directory. Existing case records, source corrections, instructions, code, readers, libraries and runs were not modified.
