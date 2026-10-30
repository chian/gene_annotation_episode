# A110 component-to-source trace

All rows are proposed sheet components. A source supplies measured quantities or a stated model, not permission to replace the user's template. The DOI correction is separate from the scientific experiment. Full per-source definitions, inspection coverage and required resets are in the two conversion files and `authority_reads.md`.

| Numerical component | Inspected source/location | Numerical content obtained | Origin | Use, limits and shared evidence |
|---|---|---|---|---|
| Reverse reaction ratio | [Wang et al., 10.1128/JB.00612-10](https://doi.org/10.1128/JB.00612-10), Fig. 3B/caption and Methods | About 1 µmol H2 per 2.2 µmol NADPH supplied; y=5/11 | Source amounts; derived ratio | A110 stoichiometry. Supplied ≠ directly measured consumed. Same readout may support A105; no duplicate activity-magnitude score |
| Forward reaction ratio | Same, Fig. 4A/caption and Methods | 0.10 µmol net NAD(P)H increase per 0.11 µmol NADH supplied; y=10/11 | Source amounts; derived ratio | A110 net cofactor/electron account. Net signal is not NADPH alone |
| Stoichiometric cross-checks | Same, Figs. 3A and 4B | 1/1.1 and 0.10/0.22 ratios | Derived from reported approximate numbers | Kept as constraints/checks on the same reactions, not extra independent replicates |
| Atom/charge/electron balance | Same, overall reaction and discussion | Fd supplies 2 e−, NADH supplies 2, two NADP+ accept 4; formal charge equality | Derived algebra on author reaction | D=0 on declared relative redox basis; no positive empirical bonus |
| Assay interference distinction | Same, Table 1 and corresponding text | 8 versus 23 U/mg with identified interference in one rate method | Reported rates and limitation | Prevents scoring these rates as a stoichiometric contradiction. Rate magnitude belongs to A105 |
| Native pathway allocation | Same, Fig. 6 | 5−(2+2.5+0.5)=0 Fd equivalents | Author-proposed pathway; derived residual | Zero algebraic residual does not measure branch capacity or actual flux; empirical resource cell remains unknown |
| Energy ceiling | Same, Discussion | Conditional 100 kJ/mol and 60–80 kJ/mol ATP → [1.25,1.666667] ATP/turnover | Author scenario plus derived division | Demonstrates energy-budget denominator; not measured native energetic support |
| Correction coverage | [10.1128/JB.02550-14](https://doi.org/10.1128/JB.02550-14), complete correction | Affiliation correction only | Publisher correction | No numerical experiment change; not another experiment |
| Precursor enrichment | [Kazemzadeh Ferizhendi et al., 10.1073/pnas.2321242121](https://doi.org/10.1073/pnas.2321242121), isotope-label Methods | p=A175/(A175+A173)=.64±.012; two injections | Reported technical measurement | Intracellular donor enrichment is a separate missing input. ± type not asserted to be SD/CI |
| Label-count predictions | Same, SI Fig. S3 E–G, p above | Binomial distributions for m=2,3,4; three-oxygen expected count 1.92 | Author theoretical construction; numerical derivation | Expected distribution, not measured product fractions |
| Restricted isotope ratios | Same, Fig. 4D means, matching mutant without added 4-HB | Image-derived B727 [43,47], B729 [8,11], L727 [3,5], L729 [14,17] pmol/mg wet cells | Coarse visual extraction; explicitly bounded | Four visible bars only. Natural baseline enters ratio b. No absent peak filled with zero; not biological confidence intervals |
| Isotope replication and calibration | Same, Fig. 4 caption and LC-MS Methods | n=3 independent experiments; means/SD; UQ8 6.25–50 pmol standards; UQ10 internal standard | Reported design/calibration | Replicate areas, covariance and recovery error not obtained; no count bonus |
| Matched biological comparison | Same, Fig. 4 and SI Table S1 | FBE748 MG1655-derived ΔaroD ΔubiIH; 10 µM shikimate; separate 100 µM 4-HB arm | Source design quantities | Keeps experimental comparability separate from isotope-source isolation. Do not use WT or other mutant backgrounds as its baseline |
| Open electron sink | Same, proposed mechanism Fig. 5 and Discussion | Two-electron oxidation obligation; acceptor unidentified | Author mechanism; derived half-reaction bookkeeping | Oxygen donor support does not close the net electron/resource budget. Molecular partners/A108 environment do not get duplicated |
| Signed contrast s, alternative minimum, physical-question weights | Neither paper provides these scores | s=(e_a−e_c)/(e_a+e_c); min over declared alternatives; fixed sum weights | Proposed scoring transformation | Explicit numerical choice for feedback; no probability claim |
| Resource coverage and conservation compilation | Neither paper provides these scores | f=min(1,z/v*); s_supply=2f−1; C=(1−D)Σw s−D | Proposed scoring transformation | Fully specified arithmetic; native resource measurements missing in these cases; no pathway completeness gate |

No synthetic observations populate either source case. Synthetic arithmetic checks test normalization, contradiction, duplicate portrayal and boundary behavior only; they are marked separately in `arithmetic_results.json`.

## Coverage and missing-data summary

NfnAB: complete main Methods/Results/Table 1/figure captions/Discussion were inspected, followed by the separate full affiliation correction. Raw plot points were not digitized, and source references were not followed. Missing categories include actual consumption/recovery, between-preparation n/variance and native pathway flux capacities.

UbiUV: complete main text/captions and main Fig. 4; supplement pages 1–9 and Fig. S3 page 5 were inspected. Supplement pages 10 onward were not inspected. Missing categories include raw isotope replicates/covariance, all baseline bins, donor-pool enrichment/exchange, isotope-specific recovery, full net electron acceptor and native capacity/demand measurements.

The rejected earlier case-report grades were not reused. Seed record inspection was metadata-only. No scientific calculation was run for the annotation target, and no source fact was promoted to an accepted A110 score.

Additive budget trace: NfnAB Fig. 3B also supplies U_NADPH≈2.2 µmol and reported endpoint v*≈1 µmol H2. The proposed coupled stoichiometry requires a=2, so its narrowly scoped supplied-amount budget gives z=1.1 µmol H2, f=1 and s_supply=1. The calculated 0.2 µmol surplus is not measured residual substrate. These are derived/model quantities from the same reverse-reaction observation, with separate compilation weight zero; they do not fill native pathway resource-capacity cells. The independent arithmetic record is `budget_arithmetic_results.json`.
