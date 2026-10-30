# CstA/YbdD: extracellular disappearance is an interval measurement

Source: *Identification of a Pyruvate Transporter in Escherichia coli K-12 Using High-Throughput Transposon Sequencing*, DOI [10.1128/JB.00771-17](https://pmc.ncbi.nlm.nih.gov/articles/PMC5847655/). Main Methods, Results and Discussion inspected; supplementary data not inspected. The paper's genetic claims are retained for A106, not scored as A105 transporter isolation.

## Experimental definitions and measured numbers

Tn-seq screening uses E. coli MG1655, while the endpoint uptake tests use BW25113 and deletion derivatives from the Keio collection or constructed by recombination. WT and mutant cultures are separate. CstA, YbdD, BtsT, other transporters and metabolism coexist in intact WT cells; deleting one does not purify the others. No purified CstA/YbdD translocation assay appears here.

The uptake Methods collect 10 mL exponentially growing cultures, wash twice in cold 1% NaCl, resuspend in 10 mL carbon-free M9, add 300 µM pyruvate and incubate 10 min at room temperature. Samples are centrifuged for 5 min at 4°C, and supernatant pyruvate is measured with a Cedex Bio HT Analyzer. Biological triplicates are specified. Cell number/OD or total protein of the resuspended assay population is not specified in that Methods subsection. Exact room temperature and a validated instantaneous stop are also not given.

Results/Fig. 5G reports normalized uptake relative to WT of 0.13, 0.20, 0.36, 0.25 and 0.05 for ΔcstA, ΔybdD, ΔbtsT, ΔcstAΔybdD and ΔcstAΔbtsT, respectively. These are genotype effects, not fractions of purified protein-specific transport. The source itself allows indirect regulation/metabolic feedback as alternatives in its final Discussion paragraph. Keep these comparisons in A106. Growth/3FP toxicity and Tn-seq frequencies likewise do not fill A105 flux cells.

## Numerical sheet conversion

The A105-relevant observation is extracellular pyruvate disappearance, with its measurement limitations. Let C0 and C10 be starting and 10-min extracellular concentrations in µM, V=0.010 L, and b be the matched cell-free extracellular loss in µmol during the same handling. Then

`D = (C0−C10)×V − b` µmol,

`J_interval = D/10` µmol/min for the complete assay population.

Because 1 µM = 1 µmol/L, the added pool is **300×0.010=3 µmol**. Complete disappearance with zero secretion and zero background would be at most **3/10=0.3 µmol/min** as a ten-minute population average. This is a derived ceiling from the assay setup, not an observed rate. Do not mistake it for a measured transporter capacity. Absolute C10 values and sample-level errors are not printed in the inspected text, so D and J_interval cannot be filled exactly here. The reported genotype percentages cannot reconstruct absolute amounts.

An initial flux `J0 = −V*dCout/dt at t≈0` requires early time points. A ten-minute endpoint does not establish constant slope, initial conditions or absence of induction/depletion during the interval. Delayed centrifugation adds an unknown effective reaction interval unless quenching is validated. No invented timing correction is applied.

**Comparability, excluding intended genotype difference:** per-cell rates need `Jcell = J_interval/Ncells`, or use measured total assay protein P for `Jprotein=J_interval/P`. A cross-condition ratio requires `Rper_cell = (D1/D0)×(N0/N1)` after the same background handling. Here N0/N1 is absent; equal harvested volume does not prove equal biomass. Temperature, pH and induction-state equivalence need measurements or an applicable response model before any quantitative correction. The source's Results calls the test pyruvate-induced, while the uptake Methods describe sorbitol growth and pyruvate addition only at assay start; preserve this discrepancy rather than assume overnight pyruvate induction.

**Isolation, separately:** the amount balance is

`−Δn_external = n_influx − n_efflux + n_external_chemical_loss + n_surface_retained + n_external_conversion`.

All terms have units µmol over the declared interval. A positive disappearance is not automatically an influx-only measurement. A cell-free control estimates chemical loss; surface extraction and extracellular enzyme controls address the other losses; no-added-pyruvate measurements address basal secretion only. Basal secretion cannot establish that pyruvate-stimulated efflux is zero. Intracellular recovery of identified pyruvate and metabolites would close the mass balance. These are complementary measurements with distinct purposes.

For an experimentally bounded non-influx loss b_other and standard error u_D, a proposed resolved fraction is

`Q_influx_lower = max(0, [D−b_other−z*u_D]/D)` for D>0,

where z is the declared coverage quantile and all b terms retain uncertainty. It is unknown here: b_other and u_D are absent. This component measures the fraction of the measured loss supported as influx under the stated bounds; it is not a genotype-attribution or source-to-target relevance score. Correcting D by these losses and then multiplying it by the same fraction would double count.

Uncertainty combines measured operands explicitly: `Var(D)=V²[Var(C0)+Var(C10)−2Cov(C0,C10)] + (C0−C10)²Var(V) + Var(b)`, with additional covariance terms when shared calibration or sample handling couples operands. Then `Var(J_interval)=Var(D)/10²` only if time is known exactly. Biological triplicates support an estimated SD/SE only when their individual values or correctly defined error bars are available. Significance stars alone do not provide that variance.

Target relevance remains separately unknown without a source-to-target correspondence and response relationship. Common organism name does not remove the MG1655/BW25113 distinction or the unmeasured substrate/energetic context. No blanket transfer coefficient is assigned. This case contributes the interval-versus-initial-rate cell, assay-population normalization and mass-balance isolation fields to the transport sheet, not a finished whole-axis score.

## Reset provenance

After inspecting the one paper, including repairing the truncated Results section from “To identify potential…” through Fig. 5, the following were reread completely before this interpretation: root AGENTS.md; GOAL.md; EPISODE_STRUCTURE.md; TIME_AWARE_ESTIMATION.md (1–194,195–388); TOOL_KNOWLEDGE.md; TASK_AND_STEERING.md; TASK_AND_STEERING amendment001; EVIDENCE_AXIS_REVIEW amendment001; VERBATIM_DIRECTION.md; VERBATIM_RECOVERY_002.md (1–112,113–215); EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS amendment001; scoring_sheet_numeric_review_002.md; SOURCE_CORRECTIONS.md; complete local AGENTS.md; A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md; TEN_SCORING_SHEETS_GOAL_2026-10-23_001.md; latest full goal attachment `/home/chia/.codex/attachments/9a858f85-d1dc-4f59-b574-9988cc09dee2/pasted-text-1.txt` last. No next paper was opened before writing this summary. No production changes.
