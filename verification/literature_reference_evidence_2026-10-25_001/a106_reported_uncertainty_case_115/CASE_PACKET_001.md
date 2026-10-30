# One A106 case: YeaG perturbation, restoration and reported uncertainty

This is a source-grounded research handoff for the unchanged literature goal. It does not amend that goal, adopt a scoring policy, edit historical records or claim an implemented new reader.

Paper: Figueira et al., *Adaptation to sustained nitrogen starvation by Escherichia coli requires the eukaryote-like serine/threonine kinase YeaG*, Scientific Reports5,17524(2015), DOI10.1038/srep17524, PMC4664914. Read retained original primary XML, original Figures3/6 and the same-paper nine-page supplement. No new source was acquired. Own complete19-document post-paper reset preceded interpretation and arithmetic; provenance and exact source fragments are adjacent.

## Actual experimental objects

The principal quantitative comparison here is Figure6B at120h of sustained N starvation, with displayed endpoint **culturable CFU per mL**. It is not recovery lag, enzyme activity or a survival probability normalized to the initial population.

| Role | Actual arm |
| --- | --- |
| W | Wild-type carrying empty pBAD18; chromosomal yeaG remains present |
| K | ΔyeaG carrying empty pBAD18 |
| R | ΔyeaG carrying pBAD18-yeaG, expressing6xHis-YeaG under the arabinose-inducible promoter |

The supplement TableS2 labels the wild-type BW25113 and ΔyeaG JW1772-1/ΔyeaG780::km. Its description also uses “K-12 substr.MG1655” for those entries. Preserve the literal background identifiers and this ambiguity rather than silently resolving it. Main Methods establish E.coliK-12 derivatives. Source/construct identity is not inferred from an accession lookup.

R supplies a plasmid copy in a deletion background; endogenous and restored YeaG do **not** coexist in that arm. W instead expresses the chromosomal protein. The intended intervention is yeaG removal followed by complementation. Native versus induced expression,6xHis tagging and restoration amount remain relevant differences. An empty vector is present in both W and K; it is not a measured numerical nuisance bound.

Growth conditions:37°C/180rpm, Gutnick minimal medium with0.4%glucose and3mM NH4Cl for pre-starvation/recovery; pBAD18 expression is induced with0.1%arabinose; appropriate plasmid selection uses50µg/mL ampicillin. CFU is measured by serial dilution onto LB agar. Exact plating dilution/volume and per-experiment colony counts are not supplied in the inspected packet. Figure6B compares20min,72h and120h in N starvation. Counts across these times must not become independent experiments.

## The uncertainty distinction the reader must retain

| Panel | Endpoint | Source-reported spread/count |
| --- | --- | --- |
| Figure3A/B | Recovery-growth OD600 curves | SD,n=3 |
| Figure6A | Sustained-starvation CFU time course on a displayed log ordinate | SEM,n=3 |
| Figure6B | CFU/mL at20min,72h,120h; logarithmic display of raw CFU-density bars | SD,n=3 |

The general Statistical analysis section says means of3 independent experiments or more, with SEM unless specified otherwise. The panel-specific SD statements therefore take precedence for Figures3/6B. These identify experiment-level replication, not three colonies, three plating dilutions or three time points. Cross-arm pairing/block structure and cross-time covariance are not supplied.

Raw W/K/R replicate counts, exact point means and exact SD magnitudes are not listed numerically in the inspected primary/supplementary tables. The plotted bars contain usable approximate numerical information. The TableS1 summary concerns ΔyeaH/ΔyeaGH recovery-growth contrasts; it cannot supply missing YeaG survival W/K/R means.

## Conditional source components from the actual Figure6B120h display

The following are explicitly **graph-derived approximate readings**, not paper-reported numerical precision. **The raw-mean/SD/SE interpretation is conditional:** although Methods state mean averages and the panel labels CFU/mL with SD, the inspected material does not explicitly say whether the statistics were computed on raw or log-transformed counts. A logarithmic display alone does not resolve that question. Preserve the observed display coordinates, SD label and n3 without silently declaring a raw-scale sampling statistic. The values below show the useful calculation if raw arithmetic means and raw-CFU SD are established; they are not an unconditional recovered sampling summary. The ordinate has labelled ticks10^6 and10^9. The recipe nominates their pixel centers y807/y551 and the W/K/R mean upper-border centers y671.5/y730.5/y669.5; upper-SD-cap centers y659.5/y712/y657.5. Conversion is

`CFU(y)=10^[6+3*(807-y)/(807-551)]`.

The original image, its hash, all coordinates, detected line/color diagnostics, source unchanged check and the reproducible conditional arithmetic are retained. This is a manually nominated case reading and calculation, **not a new implemented production graph reader**.

| Cell | W | K | R |
| --- | ---: | ---: | ---: |
| Central CFU/mL display, interpreted conditionally as a raw arithmetic mean | ≈3.9×10^7 | ≈7.9×10^6 | ≈4.1×10^7 |
| Conditional raw-CFU SD, upper endpoint minus central value | ≈1.5×10^7 | ≈5.1×10^6 | ≈1.6×10^7 |
| Estimated SE of mean, SD/√3 under the reported independent-experiment basis | ≈8.5×10^6 | ≈2.9×10^6 | ≈9.0×10^6 |

If the spread is defined on raw CFU, both central and error endpoints must first be mapped into raw units before subtraction. If instead the source statistic is mean(log CFU) with log-SD, that log-SD is the ordinate difference and backtransformed central/error endpoints do not identify the raw arithmetic mean/SD. GRAPH_COMPONENTS_002.json retains both conditional interpretations; neither is selected as paper-established. Any resulting variance estimates remain estimated sampling quantities, not known population variances.

| Existing source-effect component | Calculation | Conditional graph reading |
| --- | --- | ---: |
| Perturbation difference D | W-K | ≈3.1×10^7CFU/mL |
| Symmetric effect theta | (W-K)/(W+K) | ≈0.66 |
| Restoration fraction | (R-K)/(W-K) | ≈1.07 |
| Proposed restoration agreement r | clip(1-abs(R-W)/abs(W-K),0,1) | ≈0.93 |

Overshoot stays in the raw fraction. Under the explicitly conditional raw-mean interpretation, applying the current unmodified pure point calculator reproduces these four calculations. It does not prove native source/episode execution. The scientific claim is the contribution of YeaG to this CFU-density phenotype under sustained N starvation; these numbers do not establish a direct catalytic mechanism.

All256 joint ±1pixel choices for the two shared axis anchors, three mean centers and three upper-error endpoints yield D≈[2.9,3.3]×10^7,theta≈[0.643,0.680],raw restoration≈[1.000,1.146],agreement≈[0.854,1.000]. These are **reading-choice sensitivity ranges only**, not confidence intervals, biological replication or comprehensive digitization-error bounds.

## Dependence and unavailable components

For the stated endpoint difference, `Var(D)=Var(W)+Var(K)-2Cov(W,K)`. Independent experiments within arms do not establish zero cross-arm covariance. Under the raw-scale interpretation, with the nominal graph-derived SE estimates and unknown cross-arm correlation, the algebraic range of the plug-in variance is approximately[3.1×10^13,1.3×10^14](CFU/mL)^2. That is not a confidence interval for the true variance. The shared K also appears in R-K and the restoration denominator: it must remain one measurement, even if cross-arm covariance were later established as zero.

The measurements do not supply native-versus-restored protein amounts or measured endpoint-scale nuisance bounds B_pert/B_rest. Figure3C compares plasmid-expressed WT-sequence and variant proteins, not native chromosomal W against the restored R of this survival experiment. No C=1 or B=0 is inferred. Thus `reference_restoration_index=s*theta*r*C*I` and its sampling interval remain unavailable; a useful measured effect is preserved without an invented causal probability.

Keep recovery-growth Figure3 and survival Figure6 separate. K116A/R232A appear in Figure3 but not the Figure6B variant panel. Figure3's text reports K426A as100% of WT-sequence signal, while the original Figure3C image prints1.12 under that band. Preserve this representation conflict additively; do not alter the existing correction record or select the more convenient value. It does not fill the missing native/restored amount comparison here.

## Concrete minimum extension

The source has reported SD/SEM/n; the current input contract cannot represent them because `uncertainty_basis` accepts only`unreported`. That is an implementation gap, not absent paper uncertainty. Add per-observation summary/uncertainty fields and separate numerical variance/contrast cells, while preserving existing point outputs. The added summary-scale/uncertainty-scale distinctions are necessary before selecting either variance calculation. Exact proposed fields, arithmetic, missingness and typed-handoff limits are in PROPOSED_FIELDS_AND_CALCULATIONS_001.md. STATISTIC_SCALE_QUALIFICATION_002.md identifies the corrected assumption in the initial analysis artifacts. No source parser, calculator, schema, prompt or runtime file was edited by115.
