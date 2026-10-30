# A107 paper conversion 2 — NlpI partner quantities and nondetection

Research proposal only. Retained corpus group: `causal_nlpI_scaffolding`. Source: Banzhaf et al., DOI [10.15252/embj.2019102246](https://doi.org/10.15252/embj.2019102246), [PMC7049810](https://pmc.ncbi.nlm.nih.gov/articles/PMC7049810/). Inspected primary Results and figure captions, the relevant Discussion, strain/growth definitions, complete TPP sample preparation, identification and analysis Methods, and the actual Figure 6 image (`paper02_figure6_actual.jpg`). The file named `paper02_fig6.jpg` is the CDN's g006 image, which is **Figure 5**, not Figure 6; it is preserved and is not used for numerical table extraction. The full authority reset preceded this conversion.

## Experimental definitions and reported quantities

The primary proteomics comparison is E. coli BW25113 wild type versus ΔnlpI, with a separate ΔnlpIΔmepS comparison. Cultures grow aerobically at 37 °C to OD578 about 0.5; aliquots undergo a temperature gradient before soluble-protein measurements. NlpI does not coexist with wild-type NlpI in the deletion samples. Changes after deletion are A106 measurements, and thermostability is not transcript co-expression. Two TPP replicates are reported; temperature aliquots are not independent biological cultures. The paper distinguishes abundance and stability scores and removes knocked-out genes' scores. The Fig. 1 caption's local FDR <0.01 differs from the Methods' <0.05 plus absolute score ≥10; retain both stated locations rather than silently selecting one.

Figure 6A contains a **published derived** partner-quantity table. The molecule estimates originate from Li et al. ribosome profiling, as explicitly cited by this paper; that earlier primary study was not independently inspected here. They are not measurements made by Banzhaf et al. and not a second replication of the TPP. Its periplasmic concentration conversion assumes 3.33×10^-16 L per cell and approximately 5 nM per molecule. No uncertainty is supplied in this figure.

| Molecule | Published molecules per generation | Published periplasmic concentration, µM | Recalculation using the figure's rounded 5 nM/molecule, µM |
|---|---:|---:|---:|
| PBP1A | 554 | 2.8 | 2.770 |
| PBP1B | 512 | 2.6 | 2.560 |
| LpoA | 513 | 2.6 | 2.565 |
| LpoB | 1490 | 7.4 | 7.450 |
| NlpI | 389 | 1.9 | 1.945 |
| PBP4 | 441 | 2.2 | 2.205 |
| PBP7 | 1005 | 5.0 | 5.025 |
| MepA | 625 | 3.1 | 3.125 |
| MepH | 265 | 1.3 | 1.325 |
| MepM | 341 | 1.7 | 1.705 |
| MepS | 3931 | 19.7 | 19.655 |

Differences between rounded recalculation and the printed one-decimal values are retained, including LpoB 7.45 versus printed 7.4. One should not infer precision or apply decimal-rounding assumptions to repair the paper. MepS has an explicit qualification that abundance decreases in the presence of NlpI. Ribosome-derived synthesis and steady-state available protein are therefore different operands. The table's projected concentrations do not by themselves quantify how much free protein is available for a specific complex.

## Numerical conversion and its limits

For a declared 1:1 NlpI:PBP4 *availability illustration*, the published molecule-count ratio is 441/389 = **1.1336760925** and `min(1,441/389)=1`. For a declared 1:1 NlpI:MepM comparison it is 341/389 = **0.8766066838**. The latter is a fractional stoichiometric supply cell, not a 0.877 probability of the function. If stoichiometry is unknown, the scored supply remains null; the explicit 1:1 illustrations are not assertions about the physiological complex. For MepS, using 3931/389 = **10.1053984576** as an available-protein ratio would conflate production and degradation, so that derived ratio is retained only as a warning, not used in the coordinate.

Comparability is separately visible: these count-based estimates concern a rich-medium profiling source; the native pull-down extract and TPP samples have their own preparation and genotype definitions. The molecule-count study's exact matching of strain/condition to the current target is unverified. No single transfer multiplier is assigned to that mismatch. The native-data extension must retain its own organism, sample definitions and date.

Isolation is a different issue. Protein-quantity ratios do not isolate direct physical interaction, and recombinant binding or trimer reconstitution does not measure in-cell co-expression. The binding experiments motivate alternative partner relations (MepS–NlpI–PBP4 and MepS–NlpI–PBP7), not a compulsory conjunction of all hydrolases in the paper. PBP1A/LpoA with PBP4 describes a further specifically scoped complex. Do not flatten those possibilities into one averaged partner list or substitute binding affinities for expression coefficients.

MepS was not detected in the extracts for the reported affinity pull-downs even though the study contains other evidence involving MepS. This is an important A107 nondetection case: without a calibrated detection limit and recovery, assign neither zero molecular abundance nor a missing gene. The contrast with YfgM's displayed WT partner bands supplies numerical and experimental examples of how available quantities, detection, and sample definitions differ.

## Contribution to the common A107 combination

The main proposal uses identified genomic availability `G`, a measured paired-expression term `E`, and `edge = G(1/2 + E/2)` before applying the candidate's required/alternative partner logic. Concentration/supply measurements can populate the expression-availability input only when their units, biological units, stoichiometry and source-to-target relationship are settled. This paper alone does not supply native paired-expression coefficients with independent sample identities, nor a target-genome homology result. Therefore its complete candidate coordinate is **unknown**, with a possible-value range determined by the unknown operands; this is not permission to invent a point score from the partner catalog.

The separately dated public-expression extension is required to populate an actual statistical association cell. This conversion neither claims native association from the TPP perturbation effect nor labels Figure 6's copied count estimates as a new biological replication. Needed readers and exact downstream formulas are specified in `A107_NUMERICAL_SHEET_001.md`.
