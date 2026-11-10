# A110 source conversion 02: UbiU/UbiV oxygen-donor account

Status: PROPOSED numerical conversion for feedback; no adopted axis score. Primary source: Kazemzadeh Ferizhendi et al., *An organic O donor for biological hydroxylation reactions*, DOI [10.1073/pnas.2321242121](https://doi.org/10.1073/pnas.2321242121), [PMC10990095](https://pmc.ncbi.nlm.nih.gov/articles/PMC10990095/). Source numbers, image-derived numbers, author hypotheses and new score transformations are separated below.

The useful contrast with NfnAB is an atom-source experiment whose evidence does not identify the full electron acceptor or establish pathway flux capacity. A numerical donor constraint must not silently become a complete chemical-resource account.

## What is compared

The isotope experiment uses *E. coli* FBE748, an MG1655-derived ΔaroD ΔubiIH strain. Table S1 defines the strain construction. It is not the BW25113 background of some other aro mutants in this paper. Endogenous UbiU/UbiV remain present. There is no purified-enzyme comparison or wild-type/mutant Ubi protein mixture in this isotope measurement.

The matched comparison is anaerobic LB with 10 µM unlabeled shikimate versus 10 µM C4-[18O]shikimate in that same mutant. The separate 100 µM 4-hydroxybenzoate treatment is not pooled into that comparison; the MG1655 WT bar is also not its baseline. The intended changed variable is precursor isotope. The measured endpoint is the UQ8 mass-isotopologue pattern, with quantities in pmol per mg wet cells. The central bars in Fig. 4D are means, with SD for three independent experiments; individual values and their covariance were not obtained.

Comparability concerns matching genotype, medium, supplementation, extraction and instrument response. Isolation concerns whether label in a downstream UQ oxygen reports the prephenate donor, including possible dilution, exchange and indirect label redistribution. Those are different questions. A gene-deletion/rescue result elsewhere in the paper belongs to A106; it is not an additional isotope observation or A110 score. Molecular partner and coexpression evidence belongs to A107.

## Source-populated numerical cells

| Cell | Origin and exact denominator | Value | Numerical use and limitation |
|---|---|---:|---|
| Supplied precursor 18O fraction, p | Reported Methods: shikimate ion areas A175/(A175+A173) | 0.64 ± 0.012 | Parameter for label-count predictions; two injections, 3 and 9 µL. The type of the ± quantity is not explicitly identified; it is not a biological CI |
| Unlabeled precursor fraction | Derived 1−p | 0.36 | Complements the supplied reagent composition, not a measurement of the intracellular prephenate pool |
| Independent isotope experiments | Reported Fig. 4 caption | 3 | Retains replication extent; does not multiply score by 3 |
| Donor-label count if three oxygens are transferred independently | Derived Binomial(m=3,p=.64); source SI Fig. S3 supplies this theoretical construction | [0.046656, 0.248832, 0.442368, 0.262144] for k=0,1,2,3 | Probabilities of label counts under that model, not measured UQ fractions |
| Mean label count under that model | Derived m×p | 1.92 18O atoms/UQ8 | Prediction, not measured incorporation |
| Sensitivity to reported precursor variation | Derived m×0.012 | 0.036 18O atoms/UQ8 | Propagates only the reported technical variation; no biological confidence meaning |
| Two- and four-oxygen alternatives | Derived Binomial(m,p), same supplied p | m=2: [0.1296, 0.4608, 0.4096]; m=4: [0.01679616, 0.11943936, 0.31850496, 0.37748736, 0.16777216] | Named chemical alternatives; not an exhaustive set of mechanisms |

The source's extraction uses a UQ10 internal standard and a UQ8 calibration series of 6.25–50 pmol. That identifies the calibration method, but does not provide a numerical recovery error, isotope-specific response error or replicate covariance for this sheet. The isotope-ion windows and the quantitative calibration/adduct must stay associated with their actual method; ion intensity is not automatically molar amount across different adducts.

## An explicitly limited, checked numerical contrast from the plotted means

To show the calculation without inventing raw data, four visible central bar heights in Fig. 4D were read with deliberately coarse extraction intervals. These intervals describe visual reading of the mean bar, **not SD, confidence intervals, limits of detection or raw replicates**. No unshown higher-mass baseline is filled with zero.

| Matching treatment | Ion label on plot | Image-derived interval, pmol/mg wet cells | Midpoint used only for the illustrative point calculation |
|---|---:|---:|---:|
| 10 µM unlabeled shikimate, no added 4-HB | 727 | [43,47] | 45 |
| Same | 729 | [8,11] | 9.5 |
| 10 µM labeled shikimate, no added 4-HB | 727 | [3,5] | 4 |
| Same | 729 | [14,17] | 15.5 |

Let b=B729/B727 be the unlabeled baseline ratio and y=L729/L727 the labeled ratio. These ratios use only the first two bins; an unreported high-mass baseline tail cannot enter these bins through a positive two-mass-unit shift. If m oxygen atoms receive label independently from an intracellular donor pool with fraction p, the first two bin probabilities satisfy f1/f0=mp/(1−p). Consequently:

    b = 9.5/45 = 19/90 = 0.211111
    y = 15.5/4 = 31/8 = 3.875
    prediction(m) = b + m p/(1−p), for p<1.

This is a derived measurement-model prediction. It assumes equal responses, preservation of the labeled oxygen into the donor pool and p_pool=p_supplied. The last equality is not measured by this experiment. At p=1, the denominator bin is predicted absent; the ratio method is undefined and a count/intensity model is required. The proposed score must not quietly replace that denominator with an epsilon.

For claim m=3, c=5.544444; alternatives m=0,2,4 predict a=0.211111,3.766667,7.322222. The proposed signed contrast is the same as in the NfnAB sheet:

    e_c=(y−c)^2; e_a=(y−a)^2
    s=(e_a−e_c)/(e_a+e_c), with 0/0 set to 0 for no discrimination.

| Restricted first-two-bin comparison | e_c | e_a | Proposed s at graph midpoints |
|---|---:|---:|---:|
| Three labeled donor oxygens versus no donor-label incorporation | 2.787044753 | 13.424081790 | 0.656156561 |
| Three versus two donor oxygens | 2.787044753 | 0.011736111 | −0.991613412 |
| Three versus four donor oxygens | 2.787044753 | 11.883341049 | 0.620044791 |

These are three views of **one statistic**, not three independent observations. The strongly negative midpoint against m=2 shows why selecting the no-label comparator alone would overstate what this reduced statistic establishes. The full paper uses the higher isotope peaks and additional evidence. This restricted calculation is not a reanalysis of that full pattern and does not refute the published three-oxygen interpretation.

With visual extraction bounds, y∈[2.8,5.666667] and b∈[0.170213,0.255814]. A technical sensitivity interval p∈[.628,.652] gives c3∈[5.234729,5.876504]. Interval error arithmetic defined in the joined sheet gives conservative s bounds:

| Comparator m | Bound from these extraction and technical sensitivity intervals only |
|---:|---:|
| 0 | [−0.187730,1] |
| 2 | [−1,1] |
| 4 | [−0.714186,1] |

The bounds retain the possibility of either sign. They are not biological confidence intervals, and they do not cover the unmeasured p_pool/p_supplied relationship. The point values therefore remain conditional demonstrations. They are **not used as the final full-pattern UbiUV contribution**.

## Full-pattern cell: calculation defined, required inputs missing

For each independent experiment i, retain calibrated unlabeled baseline bin amounts B_ij and labeled amounts L_ij for the same ion windows j. Use j=0,…,J, with j=0 the unlabeled monoisotopic window and +2 mass units per subsequent bin. Define b_ij=B_ij/Σ_j B_ij and y_ij=L_ij/Σ_j L_ij. For each proposed m:

    f_mk = binomial(m,k) p_pool^k (1−p_pool)^(m−k)
    u_mij = Σ_{k=0}^{min(m,j)} f_mk b_i,j−k
    μ_mij = u_mij / Σ_{j=0}^J u_mij
    e_mi = Σ_{j=0}^J (y_ij−μ_mij)^2.

The normalization explicitly conditions the prediction on the same measured window as the data. One vector is one observation; bins are not independent replicates. Averaging experiment-level errors gives e_m, then s_3,m=(e_m−e_3)/(e_m+e_3). All denominators must be positive. Calibration, isotope-pool mixing and nuisance corrections enter before the normalization. Unknown values retain intervals; they are not replaced by nominal source-label fractions or invisible zero bars.

Missing inputs for an empirical final cell: raw replicated B/L values in all measured bins, baseline tail values, uncertainty/covariance, isotope-specific recovery, and intracellular donor enrichment or a justified bound. The five visible labeled bars alone do not supply those inputs. No unknown operand in this formula is an undefined calculation.

The formula currently has no implemented reader or fitting tool. It is a sheet definition; no scientific program was run on the annotation target.

## What the donor result leaves open chemically

The authors propose prephenate-mediated hydroxylation coupled to decarboxylation, with phenylpyruvate and CO2, while leaving the oxidant/electron acceptor unidentified. A symbolic neutral-species half-reaction illustrates the omitted redox obligation:

    R−H + C10H10O6 → R−OH + C9H8O3 + CO2 + 2 H+ + 2 e−.

The formula counts are a **derived representation of the proposed chemistry**, not experimentally measured complete stoichiometry. It conserves C, O, H and charge, and explicitly produces two electrons per hydroxylation. A complete catalytic net needs an electron sink and its regeneration/supply account. It is incorrect to remove the electrons and call the donor result a closed redox mechanism. The molecule formulas use neutral species; a pH-specific ionic account needs the corresponding protonation states.

No resource-capacity measurement establishes how much prephenate, electron acceptor or regeneration flux is available per required UQ production flux. Presence of a plausible donor or another gene does not numerically fill that budget. Nor does chemically balanced bookkeeping prove that UbiUV performs the isolated reaction. These remain missing sheet cells, without imposing a mandatory experiment or pathway-completeness gate.

## Inspection, artifacts and reset

Inspected: complete main text through Methods and all main figure captions; main Fig. 4 image; supplement pages 1–9 including Figs. S1–S3 captions, strain/plasmid/primer Tables S1–S3 and the beginning of synthesis methods; Fig. S3 on supplement page 5 viewed. Supplement pages 10 onward, including S4–S22 chemical-characterization material, were not inspected. No reference paper was read.

The original `PMC10990095_SI.pdf` download is an HTML error/anti-bot response, not a valid PDF. It is preserved as a failed retrieval artifact. The Europe PMC supplementary ZIP and extracted `PMC10990095_SI_valid.pdf` are the valid inspection source. No claim rests on the failed download.

Complete authority rereads occurred after the main/SI packet and again after the retained Fig. 4 check, before conversion. All outputs were complete. The latest goal and human reminder were last. See `authority_reads.md` for the actual complete set and read records.
