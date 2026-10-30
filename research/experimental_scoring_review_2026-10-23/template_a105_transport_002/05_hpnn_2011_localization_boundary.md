# A105 transport: HpnN localization is not a measured transport rate

Research proposal, 2026-10-23. Source: Doughty et al., *The RND-family transporter, HpnN, is required for hopanoid localization to the outer membrane of Rhodopseudomonas palustris TIE-1*, [PNAS 108:E1045–E1051, DOI 10.1073/pnas.1104209108](https://pmc.ncbi.nlm.nih.gov/articles/PMC3215060/). Full main article read; supplementary PDF access returned HTTP 403. The particular supplementary numerical purity information is not claimed to have been inspected.

## Experimental definitions

The assayed organisms are separate R. palustris TIE-1 wild-type, clean ΔhpnN (Rpal_4254) deletion, and ΔhpnN complemented with multicopy pDMD5 cultures. Rpal_4267 is a separate RND-family protein present in the organism; a separate deletion is reported but not pooled with the HpnN contrast. Wild-type and deleted HpnN do not coexist merely because curves/bars are compared. Other biosynthetic and transport proteins do coexist in each cell. Mother and swarmer populations differ biologically, and the organism has outer, cytoplasmic, and inner cytoplasmic membranes.

For the Fig.4 genotype comparison, the intended change is HpnN genetic status. Whole-cell and fractionated-membrane hopanoid composition is measured by GC-MS and normalized to total lipid extract (TLE). The multicopy complement additionally changes expression level and stimulates C30 hopanoid production. An expression amount was not measured in the inspected paper. The observed phenotype and its restoration are A106 evidence; a steady-state membrane distribution alone is not a measured molecular transport rate for A105.

## Exact numerical observations and denominators

| Source location | Reported quantity | Numerical meaning |
| --- | --- | --- |
| Results, HpnN essential for BHT localization | 12.5 ± 1 µg/mg TLE total hopanoids | Hopanoid mass divided by extracted total lipid mass; not fraction of all cellular hopanoids transported |
| Same Results/Fig.4 | Whole-cell BHT 8.1 ± 0.7 µg/mg TLE | BHT mass per whole-cell TLE mass |
| Same Results | C30 hopanoids 3.8 ± 0.3 whole cell; 8.7 ± 2.8 outer membrane, µg/mg TLE | Different fraction-specific TLE denominators |
| Same Results, referring to Summary Figure | Cytoplasmic/inner-cytoplasmic BHT 4.4 ± 1.9 WT; 11.89 ± 2.0 ΔhpnN, µg/mg TLE | Internal-membrane BHT concentration, not translocation flux |
| Fig.4 legend | SD of three independent cultures | Independent biological replication for this panel; not three technical readings |
| Cell-cycle Results/Fig.5 | Swarmer BHT below approximately 1 µg/mg TLE detection limit; approximately 20 µg/mg TLE in mother cells | Censored concentration versus measured concentration; different cell types |
| Fig.5 legend | Three independent cultures analyzed for BHT, plotted representative culture | Not a plotted mean with a reported between-culture SD |

Calculated values, not paper-reported scores: internal BHT concentration ratio `11.89/4.4 = 2.70227`; difference `11.89−4.4 = 7.49 µg/mg TLE`. If the cited errors are applicable independent SDs, propagated ratio dispersion is approximately 1.252 and difference dispersion is 2.7586 µg/mg TLE. Neither is a confidence interval for a molecular transport coefficient. Pooling may require covariance and paired-culture information. The outer-membrane/whole-cell C30 concentration ratio is `8.7/3.8 = 2.28947`; it is enrichment per unit TLE, not 229% transport recovery.

## Conversion to the user's numerical sheet

**Comparability outside the intended variable.** TLE normalization addresses lipid-mass loading, but the denominators differ between membrane fractions and may change with lipid biosynthesis or fraction recovery. Equal µg/mg TLE does not establish equal absolute molecules, membrane area, cell number, or transporter abundance. The genotype and associated causal attribution stay A106. For an A105 membrane-movement assay, nuisance corrections require fraction masses `M_OM,M_CM,M_ICM` (mg TLE), recovery fractions `r_j`, and measured cross-contamination coefficients `P_jk`; none should be replaced by a flat similarity grade.

The directly relevant calculation would be absolute lipid amount `h_j = c_j × M_j/r_j`, where `c_j` is µg hopanoid per mg TLE. With cross-contamination, the measurement model is `y_j = Σ_k P_jk h_k + b_j`; infer the true compartment vector only when `P` is measured and sufficiently identifiable. A marker for inner-membrane contamination (phytadiene, derived from phytol) was used, but the inspected main text does not give a numerical mixing coefficient or detection bound. Absence of a visible marker peak does not set `P_jk = 0` exactly. The matrix and recovery correction would enter once, as corrections to absolute amounts, with their uncertainty propagated.

**Isolation of observed transport.** A mass distribution can arise from synthesis, degradation, retention, partitioning, export, or translocation. A proposed A105 amount balance is

`Δh_OM = ∫(J_CM→OM − J_OM→CM + synthesis_OM − degradation_OM − shedding_OM)dt`.

Thus the differential outward flux requires time-resolved absolute compartment amounts and the other terms. Fig.4 provides a concentration endpoint, not that derivative. The paper specifically reports altered whole-cell biosynthesis in the complement, demonstrating why assuming equal production is unsafe. No isolated HpnN reconstitution, tracer translocation time course, orientation measurement, or gradient-response relationship is established in this source. A105 molecular flux remains unknown, not zero. The localization contrast is retained for the separately scoped A106 causal sheet.

**Detection limits and signal.** For the reported synchronized-cell comparison, `c_swarmer/c_mother < 1/20 = 0.05` is a derived concentration-ratio upper bound conditional on the stated limit and roughly 20-µg/mg mother value. It is not a measured zero, not a 95% bound, and not a transport efficiency. Raw peak area, calibration curves, extraction recovery, and detection-limit construction are necessary to turn it into a likelihood or a propagated numerical interval. Cell separation may contaminate the trace swarmer BHT with mother cells, as the authors state; the corresponding mixture proportion is missing.

**How components combine.** Calibrated chromatographic signal becomes mass by the calibration slope, then background subtraction, recovery division, compartment-mixture correction, and multiplication by actual fraction masses give comparable absolute amounts. Their finite-time differences, corrected for biosynthesis/degradation/shedding, would give movement. These are explicit operations with physically defined operands. There is no legitimate numerical product converting the present concentration endpoint into HpnN turnover. A proposed isolation bound `F_movement = max(0, [Δh_OM − b_other − z u_Δh]/Δh_OM)` would require a separately measured upper bound `b_other` on nontransport accumulation, a nonzero positive amount change, and valid uncertainty; all are absent here. Multiplying an already background-subtracted amount by the same background fraction would double-count its correction.

**Relatedness and target/system relevance.** This source directly establishes lipid localization in a hopanoid-producing organism under the tested growth/cell-cycle conditions. Its broader RND phylogeny includes transporters of other substrates, and the paper itself rejects a simple HpnN-to-eukaryotic-sterol-transport evolutionary claim. Substrate identity, membrane topology, cellular hopanoid biosynthetic capacity, compartment access, and actual correspondence of assayed and target proteins must be retained. A percentage sequence match or an unmeasured generic transfer weight cannot manufacture an A105 transport observation absent from the source.

## Required complementary measurements and reader fields

For this assay family, readers would need compartment-specific calibrated analyte amounts, TLE masses, extraction recovery, marker-derived contamination matrix and its errors, cell-type mixture fractions, sampling times, pool production/degradation terms, protein abundance, and actual transport-active protein amount. The sheet can compute recovered fraction `h_OM/Σ_j h_j` only when all absolute amounts refer to the same original sample and recovery/contamination are addressed. This is a measurable localization fraction, still not transport turnover. The retained paper lacks the essential inputs for a completed A105 molecular transport row; its useful contribution here is a numerical boundary case that prevents concentration enrichment from being scored as molecular flux.

## Authority reset performed

After this article and the unsuccessful supplementary-access attempt, before interpretation, all required documents were reread completely: AGENTS.md; GOAL.md; docs/EPISODE_STRUCTURE.md; docs/TIME_AWARE_ESTIMATION.md; docs/TOOL_KNOWLEDGE.md; docs/TASK_AND_STEERING.md; docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md; docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md; publication2026-10-23-002/VERBATIM_DIRECTION.md and VERBATIM_RECOVERY_002.md; docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md; verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md; local SOURCE_CORRECTIONS.md; local AGENTS.md; A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md; TEN_SCORING_SHEETS_GOAL_2026-10-23_001.md; and finally the complete latest user attachment /home/chia/.codex/attachments/9a858f85-d1dc-4f59-b574-9988cc09dee2/pasted-text-1.txt. Each output was untruncated. No earlier paper evidence packet was reread as a batch.
