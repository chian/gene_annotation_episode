# A107 paper conversion 1 — YfgM and its available partners

Research proposal, not adopted scoring or an annotation result. Primary case selected from `cellular_yfgM` in the retained 142-group corpus. Source: Götzke et al., 2014, DOI [10.1074/jbc.M113.541672](https://doi.org/10.1074/jbc.M113.541672), [PMC4081946](https://pmc.ncbi.nlm.nih.gov/articles/PMC4081946/). Full Methods, Results, Discussion and figure captions were read in the retained HTML text; the numerical labels of Figure 4 were inspected in its image. No later YfgM paper was opened. The complete post-paper reset preceded this conversion; see `RESET_COVERAGE_001.json`.

## Experimental definitions

The source subject is E. coli YfgM. The comparison is native wild type versus strains with single chromosomal deletions, including ΔyfgM, ΔppiD, Δskp, ΔsurA and ΔdegP. The periplasmic-protein immunoblot in Figure 4 measures steady-state YfgM, PpiD, Skp and SurA, with a loading band, in each strain. Its denominator is the corresponding protein signal in the wild-type lane, set to 100%; it is not protein molecules per cell and not the fraction of total protein. YfgM and PpiD coexist in the wild-type material. In ΔyfgM, YfgM is removed rather than mixed with wild-type YfgM. The intended changed variable is the indicated deletion; compensatory protein changes and unequal loading are additional differences.

The general culture method gives LB, 37 °C and strain-dependent antibiotics, but Figure 4 does not separately provide a harvest OD, independent culture count, replicate measurements, uncertainty, or a named loading protein. Table 1 lists MC4100 and W3110 backgrounds; the Figure 4 caption itself does not resolve which background supplied each displayed lane. Do not silently borrow the ≥3 biological replicates reported for Figures 3 and 5. The Figure 1 IP uses M9 and OD600 0.6, whereas the BN-PAGE method uses LB and OD600 0.9; those are different preparations.

## Filled published numerical cells

These are printed Figure 4 values, not digitized band estimates. All are percentages relative to that row's wild-type signal.

| Row | WT | ΔyfgM | ΔppiD | Δskp | ΔsurA | ΔdegP |
|---|---:|---:|---:|---:|---:|---:|
| YfgM | 100 | 0 | 91 | 99 | 95 | 95 |
| PpiD | 100 | 99 | 0 | 102 | 89 | 94 |
| Skp | 100 | 131 | 128 | 0 | 145 | 107 |
| SurA | 100 | 95 | 64 | 83 | 0 | 44 |
| Loading band | 100 | 112 | 114 | 112 | 109 | 114 |

For the narrow question “is PpiD still available in ΔyfgM?”, the reported relative signal is 99/100 = **0.99**. If the displayed percentages are not already corrected by the loading band, a separately labeled derived sensitivity calculation is (99/112)/(100/100) = **0.8839285714**. It cannot replace the reported 0.99 because the text does not settle prior loading normalization. The corresponding Skp values are **1.31** reported and **131/112 = 1.1696428571** under the same conditional correction. SurA is **0.95** reported and **95/112 = 0.8482142857** conditionally corrected. The loading difference itself is **112/100 = 1.12**. These distinct quantities evaluate sample comparability; they do not establish co-expression correlation or causal contribution.

An abundance-comparability cell can use the explicit proposed transformation `C_amount = min(a, 1/a)` for a positive matched abundance ratio `a`; at a=0 the result is 0. The conditional PpiD comparison gives **0.8839285714** and Skp gives **112/131 = 0.8549618321**. This measures closeness of abundance, symmetrically for increases/decreases, without calling a 31% increase “more reliable”. It is useful only when the receiving inference requires matched abundance. It is not added to A107 as an independent experiment.

## Conversion into the A107 sheet

Figure 4 supplies observed protein availability and a quantitative warning against pooling engineered deletions as if they were independent native expression conditions. The steady-state panel has four molecular rows with distinct identities and one shared normalization. The WT lane contains YfgM, PpiD, Skp and SurA; that supports co-detection in displayed source material. It does not identify a statistical sample size for a co-detection rate or an association estimate. `n_independent`, Pearson/Spearman coefficient, its standard error, and adjusted association remain **null**. A reader must not compute a five- or six-point “native co-expression” coefficient from intervention lanes. The forced zeros would create a different estimand.

For a possible function involving YfgM–PpiD with SecYEG, the primary co-IP and BN-PAGE observations explain why those molecules are considered partners. Their binding/complex readouts belong to A105/A111 as appropriate; A107 reuses the relationship as context, without assigning another binding score. SecY/SecE/PpiD/YfgM co-migration and SecG IP do not show a quantitative correlation of expression. SurA and Skp are possible overlapping downstream chaperones, not established compulsory members of a five-member YfgM complex. Keep the partner requirement expression scoped to the candidate being considered.

The proposed A107 compilation separates genomic availability `G` from paired-expression support `E`: `edge = G * (1/2 + E/2)`. Here `G` is a numerical genomic/identity-supported availability operand and `E` is a measured co-detection/association operand defined fully in the main sheet. These equal coefficients are research conventions, not calibrated probabilities. For this paper alone, no complete homology search or quantitative native association input exists; the point edge coordinate is **unknown**, not 0.99. If genomic availability is independently established as G=1 in the exact source system, unknown E permits **[0.5,1]** as an identification range, not a confidence interval. Without G, the range is **[0,1]**. No gene-presence credit is fabricated from a protein's percentage label.

## Isolation and dependence

Genotype-specific loss of the matching band helps assign the measured band; it does not quantify antibody cross-reactivity or background. No blank intensity, detection limit, spike recovery or uncertainty is available for the Figure 4 numerical cells. Those operands remain missing. A separate native-condition expression series with independent cultures, paired target/partner measurements, known normalization, detection limits and batch/condition information would supply A107 association inputs. A genome record/alignment would supply genomic identification. Repeated figures, gel lanes or reanalysis do not create independent evidence.

SecY was not detected in the reciprocal YfgM/PpiD IP but was observed by another route in the same paper. This is assay-specific nondetection, not genomic absence or native lack of SecY. The different detergents and preparations must stay explicit. Likewise YidC's failure to co-purify in one supercomplex does not mean its gene or protein is absent. The paper therefore supplies contrasting positive availability and nondetection examples while leaving native expression statistics genuinely unknown.
