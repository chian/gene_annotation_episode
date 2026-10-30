# A105 transport: pyruvate uptake in a heterogeneous VBNC population

Research proposal, 2026-10-23. Source: Vilhena et al., *Importance of Pyruvate Sensing and Transport for the Resuscitation of Viable but Nonculturable Escherichia coli K-12*, DOI [10.1128/JB.00610-18](https://pmc.ncbi.nlm.nih.gov/articles/PMC6349089/). The inspected local text and Fig.7 image are retained beside this file. No production policy is adopted.

## Experimental definitions and reported measurements

The Fig.7 assay compares separate cultures of E. coli K-12 MG1655 wild type and an isogenic ΔbtsSR ΔypdAB regulatory-network mutant after 120 days at 4°C. Wild-type and mutant proteins do not coexist in a single sample merely because two curves are plotted. Each cell nevertheless contains other transporters, regulatory proteins, and metabolic enzymes; each culture contains cells in different physiological states. Complementation with pCOLA-btsSR-ypdAB belongs to the paper's resuscitation experiments, not a purified-transporter uptake preparation.

The deliberately changed variable is the regulatory genotype. Changes in transporter abundance, physiology, and metabolism may be consequences of that perturbation. Its causal interpretation belongs to A106. A105 can record the actual measured cell-associated radiotracer movement without claiming that the genotype contrast identifies one purified transport activity.

Methods, “Pyruvate uptake”: 10^10 cells/mL in fresh LB at 15°C; 200 µL suspension plus 32 µL tracer solution gives 80 µM final [3-14C]pyruvate, specific radioactivity 10 Ci/mol. At stated times, 2.5 mL of 100 mM LiCl/100 mM KH2PO4 pH 6 stops the assay; 0.4-µm filtration, three washes, and scintillation counting follow. The low temperature is intended to limit pyruvate metabolism and loss as 14CO2. It is not a measurement proving those losses absent.

Results report approximately 0.33 nmol/mg protein within 20 s. Fig.7's ordinate is **amount**, nmol/mg protein, and the abscissa is seconds. This quantity is not a rate in nmol mg−1 s−1. The visual curve is not linear through all early points and contains nonzero time-zero signal; no exact numerical digitization is asserted here. The text's “no uptake” for the mutant must not be converted into an exact zero background: the figure displays residual signal. Raw counts, recovery, exact time-zero values, slope-fit coefficients, and their covariance are not supplied in the inspected text.

Table 1 supplies physiological and total-protein measurements:

| Population | Membrane-potential-positive cells | Respiration-positive cells | Total protein |
| --- | ---: | ---: | ---: |
| Wild type | 8 ± 0.7% | 9 ± 1% | 1.65 ± 0.05 mg/mL |
| ΔbtsSR ΔypdAB | 9 ± 0.3% | 6 ± 0.5% | 1.72 ± 0.03 mg/mL |

The exact statistical meaning of these table ± values is unresolved. General Methods discuss means/SEM; Fig.7 describes triplicates with “standard deviations of the mean,” which is not a precise SD-versus-SEM definition. Preserve the reported error description instead of silently converting it. Replicate experiments are at least three by general Methods; time points are not independent preparations. Proteomics used a Percoll-isolated viable fraction in other experiments; the uptake method does not establish that the Fig.7 suspension underwent that isolation.

## Conversion to numerical cells in the user's sheet

**Comparability outside the intended variable.** Total protein, active fraction, membrane energetics, temperature, substrate availability, and sampling/recovery can affect comparisons. Equal nominal cell counts or total protein are not proof of equal active transporter amount. Directly derived diagnostics are 1.65/1.72 = **0.9593023** for total-protein concentration, 8/9 = **0.8888889** for membrane-potential-positive fractions, and 9/6 = **1.5** for respiration-positive fractions. These are measured-condition comparisons, not relevance scores. The opposing physiological ratios prevent selecting one proxy as an unqualified “viability correction.” If the reported protein errors were independent standard uncertainties, propagation would give 0.9593023 ± 0.0335412; that conditional calculation does not resolve their actual error type.

A per-active-protein normalization requires

`M_active = M_total × f_active × (mean protein per active cell / mean protein per all cells)`.

The last ratio is missing. Therefore dividing total-protein-normalized uptake by 0.08 is not justified. A per-BtsT normalization additionally requires BtsT abundance and active/oriented fraction in the relevant membrane. The transport assay supplies neither. The valid numerator/denominator remains the observed tracer amount divided by measured total protein, with that scope explicitly retained.

If an experimentally established response function `g(x)` relates uptake per transporter to nuisance condition `x`, a proposed comparison cell is `C_x = min(g(x_A),g(x_B))/max(g(x_A),g(x_B))`. This evaluates expected response similarity for that measured nuisance; it is not the raw ratio `x_A/x_B`. It excludes the deliberately changed genotype and its intended effect. No such response function is measured for the mixed-population active fractions here, so this cell remains unknown. If instead measurements are standardized by `g(x_ref)/g(x_assay)`, do not also multiply their evidence by `C_x` as a second penalty for the same modeled difference.

**Isolation of the observed molecular movement.** The operative measurement is cell-associated radiocarbon after washing. A proposed mass-balance cell is

`n_entered = n_retained − n_surface − n_trapped_external + n_lost_as_CO2 + n_exported_after_entry`,

where each term is moles of the relevant labeled carbon (converted to pyruvate equivalents only with the labeled-carbon stoichiometry). This is a bookkeeping identity conditional on all relevant pathways being represented. Surface-binding, trapped-medium, carbon-loss, and export measurements are absent. A network-deletion curve is not an inert blank proving that those contributions equal the wild-type background. Its difference is useful A106 evidence, not an independently isolated A105 molecule-specific flux.

An interval-averaged uptake component would be

`J_[t1,t2] = {n_entered(t2) − n_entered(t1)} / {(t2−t1) M_total}`.

An initial-flux component requires fitting the validated initial linear interval and reporting its slope uncertainty. It cannot be obtained by dividing 0.33 by 20 while assuming the initial amount is zero. The nominal total external substrate pool is **80 nmol/mL × 0.232 mL = 18.56 nmol**, calculated from the reported final volume and concentration. This is an assay-capacity quantity, not observed uptake or transporter turnover.

**Signal, uncertainty, and consistency.** With calibrated per-time-point measurements, a proposed numerical cell is the resolved fraction `F_resolved = max(0, [Δn − b_unresolved − z u_Δn]/Δn)` for positive `Δn`, using an independently justified upper bound on unresolved positive nuisance signal and a stated one-sided quantile `z`. Its interval interpretation requires valid uncertainty assumptions; it is not a paper-reported confidence score. Here `Δn`, the nuisance bound, and covariance are missing, so it cannot be filled. Carbon loss is a different, negative bias and must enter the mass balance rather than being subtracted again as positive contamination. A ratio or lower bound should not be silently forced into [0,1] if its defining conditions fail.

The deterministic combination is subtraction of measured nuisance amounts, addition of independently measured losses, division by the stated denominator, and propagation through those same operations. If independent preparations supplied comparable slopes `J`, an uncertainty-weighted mean could be `(1ᵀΣ⁻¹J)/(1ᵀΣ⁻¹1)`, with variance `1/(1ᵀΣ⁻¹1)` and shared controls/calibrations in `Σ`. Technical repeats only estimate within-preparation variance. Repeated appearances of Table 1 or Fig.7 are not independent evidence. Multiplying the corrected slope by the same isolated-fraction factor again would count the subtraction twice.

**Target/system relation.** This experiment is directly about native E. coli cells after prolonged cold storage in a mixed physiological state. It does not establish the response of an arbitrary target protein, a purified BtsT molecule, an unstressed cell, or a different membrane. Native organism correspondence is a useful explicit relation but supplies no universal numerical transfer weight. A source-to-target response comparison requires target expression, membrane conditions, energetic state, substrate access and a validated relation between those measurements and uptake; these cannot be replaced by sequence similarity alone.

## Boundary and remaining operands

Growth, CFU recovery, resuscitation rescue, and genetic attribution remain A106. DNA/protein synthesis is not a transport-rate readout. A105 can retain the measured uptake curve and its normalization, but exact usable flux, cell-surface background, residual extracellular label, metabolic label loss, physiological-subpopulation protein mass, active transporter amount, and uncertainty type remain unresolved. Complementary measurements would address those specific terms; their absence is not encoded as zero activity or a categorical grade. The paper is particularly useful for showing why “equal total protein” and “same number of cells” do not settle experimental comparability.

## Per-paper authority reset provenance

After reading this paper and its Fig.7 image, before the above interpretation, the complete required set was actually reread: AGENTS.md; GOAL.md; docs/EPISODE_STRUCTURE.md; docs/TIME_AWARE_ESTIMATION.md (1–194, 195–388); docs/TOOL_KNOWLEDGE.md; docs/TASK_AND_STEERING.md; docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md; docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md; research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md and VERBATIM_RECOVERY_002.md (1–112, 113–215); docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md; verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md; local SOURCE_CORRECTIONS.md; local AGENTS.md; A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md; TEN_SCORING_SHEETS_GOAL_2026-10-23_001.md; and lastly the full latest user goal attachment /home/chia/.codex/attachments/9a858f85-d1dc-4f59-b574-9988cc09dee2/pasted-text-1.txt. The final combined authority output was context-truncated; every omitted document was reread in full in two shorter calls before interpretation. Bibliographic-only title/author/DOI verification followed; no new experimental evidence was opened after the reset.
