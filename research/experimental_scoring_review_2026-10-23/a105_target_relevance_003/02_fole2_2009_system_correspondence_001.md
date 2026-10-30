# A105 relevance packet 02: measured system response and structural correspondence

New research note, 2026-10-23. Source: Sankaran et al. (2009), *Zinc-Independent Folate Biosynthesis: Genetic, Biochemical, and Structural Investigations Reveal New Metal Dependence for GTP Cyclohydrolase IB*, [DOI 10.1128/JB.00287-09](https://doi.org/10.1128/JB.00287-09), [PMC2772490](https://pmc.ncbi.nlm.nih.gov/articles/PMC2772490/). This is an original-corpus `replacement_folE2` source newly read by this worker, not a newly discovered publication. HTML and extracted full text are retained beside this note. No scorer, reader, episode or annotation has been changed.

## Define the experiment and denominator before scoring

The molecular assay uses recombinant B. subtilis GCYH-IB, expressed in E. coli, purified and demetallated. Metal activation assays contain 2 µM apoenzyme, 100 µM GTP, HEPES pH 8.0/KCl, with 10-minute metal preincubation at 37°C. Fluorescence-based activity is normalized to Mn-supported activity. The comparison deliberately changes metal species AND concentration: each metal's optimum, not an equal-concentration experiment. These are separate reactions, not mixed enzymes. EDTA/no-metal observations address metal dependence; they do not quantify contaminant activity. Exact expression vector/strain and the previously described fluorescence procedure are not fully specified here.

The kinetic fit uses 0.5 µM protein, 0.5 mM MnCl2, DTT and 3–50 µM GTP under initial-velocity conditions. Structural experiments instead use N. gonorrhoeae GCYH-IB; its reported B. subtilis sequence identity is 35%, with biochemical similarity asserted but data unshown. Therefore a structural result and a kinetic result do not share an assayed molecule. Growth/complementation is A106 and is not scored here.

## Source numbers retained with their meanings

| Observation | Source location | Reported number |
|---|---|---:|
| Mn-supported reference activity | Table 2 | 100% at 500 µM Mn(II) |
| Zn-supported activity relative to that reference | Table 2 | 14 ± 1% at 50 µM Zn(II) |
| Fe- and Mg-supported relative activities | Table 2 | 75 ± 8% at 1,000 µM Fe(II); 43 ± 4% at 100 µM Mg(II) |
| Mn-condition GTP kinetic fit | Results, metal requirements | kcat = 0.0011 s^-1; Km = 9.87 µM |
| Ng IB versus Ec IA structural alignment | Results, structural comparison | RMSD 3.2 Å over 94 Cα atoms |
| Ng IB versus urate oxidase structural alignment | Results, T-fold | RMSD 3.4 Å over 197 Cα atoms |
| Ng IB versus Ne IB structural alignment | Results, T-fold | RMSD 1.6 Å over 238 Cα atoms; sequence identity 56% |
| Ng protein sequence length | Results, crystal structure | 257 residues |

The primary article's Figure 3 caption defines its error bars as SD over four sets of triplicate assays. It does not explicitly assign that uncertainty definition to Table 2. The kinetic-fit uncertainty and parameter covariance are not reported in the inspected text. Do not silently convert any of these into SE or independent preparation counts.

## Numerical source-to-target calculations

### 1. Same molecule, measured change in assay system

Declare the source condition as the Table 2 Mn recipe and the comparison/target condition as the Table 2 Zn recipe. This is a correspondence between two specified assay systems for the same enzyme, not a claim that physiological metal availability equals an assay recipe.

The measured response ratio and its log are:

```
r_metal = activity_Zn_recipe / activity_Mn_recipe = 14/100 = 0.14
d_metal = log(r_metal) = -1.9661128564
normalized_activity_Zn = normalized_activity_Mn * r_metal = 1 * 0.14 = 0.14
```

The product is an actual quantitative relationship between the two measured recipes. It is NOT an 0.14 overall relevance grade and NOT evidence that Zn supports only 14% of the enzyme's physiological function. The mean shift says how to predict this assay endpoint after this specific system change. It can be combined with an independently estimated molecular difference `r_molecule` by multiplication ONLY if the source-to-target model accounts for interaction between molecule and metal: `a_target = a_source * r_molecule * r_metal`. In this same-molecule comparison `r_molecule = 1` is a factual cancellation.

For source and target estimates A and B with standard uncertainties u_A and u_B, measured on the same normalization scale:

```
Var(log(B/A)) = (u_B/B)^2 + (u_A/A)^2 - 2*Cov(A,B)/(A*B)
```

Table 2's reference is a normalization denominator, not an independently measured error-free 100. Its shared covariance must be obtained from the assay data. If the reported ±1 is the uncertainty of the already-normalized RATIO, its numerator/denominator noise is already included and must not be added again. Its unspecified meaning prevents an actual likelihood score from this publication alone. A conditional arithmetic illustration, not the paper's uncertainty: if 0.01 were a standard uncertainty of the ratio estimate, `Var(d_metal) ≈ (0.01/0.14)^2 = 0.0051020408`.

### 2. Relevant substrate exposure, with an experimentally fitted response

For the SAME B. subtilis protein under the reported Mn kinetic conditions, use the Michaelis–Menten fit to compare two substrate exposures within the assayed range. The underlying model is `a(S) = kcat*S/(Km+S)`. Declare source S = 50 µM and target S = 10 µM. These are model-derived activities from the published fit, not reconstructed observed points:

| Calculated quantity | Formula | Result |
|---|---|---:|
| Source saturation fraction | 50/(9.87+50) | 0.8351428094 |
| Target saturation fraction | 10/(9.87+10) | 0.5032712632 |
| Exposure response ratio | [10/(9.87+10)]/[50/(9.87+50)] | 0.6026170106 |
| Source turnover | 0.0011 × 50/(9.87+50) | 0.0009186570904 s^-1 |
| Target turnover | 0.0011 × 10/(9.87+10) | 0.0005535983895 s^-1 |
| Log response difference | log(0.6026170106) | -0.5064734241 |

The change in substrate concentration is not itself a fractional penalty such as 10/50. Its effect follows the measured response curve. `kcat` cancels from the ratio because the same fit applies to both predictions. For fixed S values, the derivative of the log ratio with respect to Km is `1/(Km+50)-1/(Km+10) = -0.03362427013 µM^-1`. Thus the Km uncertainty contribution is `0.00113059154 * Var(Km)`; measured substrate uncertainties and covariances add through the same gradient. The publication does not fill those uncertainty cells.

The source and target rates above are two outputs of one fit, so they are not independent activity experiments. A valid rate prediction and its uncertainty retain that shared fit. The Table 2 Zn/Mn ratio was measured at 100 µM GTP. It cannot simply multiply the Mn-only 10/50 µM substrate ratio to predict Zn at 10 µM: the Zn-specific Km or a joint substrate×metal response is missing. This is a concrete experimental-comparability gap, separate from whether the fluorescence signal belongs to this enzyme.

### 3. Structural correspondence without a sequence-only restriction

The reported comparisons populate numerical structure cells even where a sequence-only relation would be misleading:

| Pair | RMSD, Å | Aligned Cα count | Coverage of the 257-residue Ng reference |
|---|---:|---:|---:|
| Ng IB / Ec IA | 3.2 | 94 | 94/257 = 0.3657587549 |
| Ng IB / urate oxidase | 3.4 | 197 | 197/257 = 0.7665369650 |
| Ng IB / Ne IB | 1.6 | 238 | 238/257 = 0.9260700389 |

These RMSDs compare different matched sets. They cannot be treated as an already-normalized score of identical chemical function or multiplied indiscriminately by sequence identity. The urate-oxidase match illustrates why the binding/catalytic site and chemical endpoint must enter any numerical mapping. The article's proposed ligand pose is a docking model, not an observed substrate-bound complex. No numeric target activity is manufactured from it.

A quantitative correspondence model can use native structural scores, explicitly mapped site differences and sequence/evolutionary data jointly to predict a molecular activity contrast and its residual error. The separate proposal specifies the regression, uncertainty and data requirements. For this source, paired B. subtilis/Ng molecular rates under common conditions remain unavailable, so a numerical Bs→Ng transfer is not filled merely because the paper calls their properties similar. Neither must absent global sequence identity veto usable structural or direct molecular evidence.

## Isolation, uncertainty, complements, and combination

The source assay's own reliability requires the calibration from fluorescence to product, background, quantitative enzyme amount, product identification, and the uncertainties/covariance of the fitted kinetics. The current primary article refers parts of that method to an earlier source; this review did not independently inspect that earlier paper. No 1.0 isolation or product-specificity component is therefore assigned. Metal depletion/reconstitution isolates a requirement of this preparation more directly than growth does, but it does not by itself quantify contaminating enzyme activity.

The sheet separates: (a) the measured source activity and source uncertainty; (b) specific molecular/system response corrections such as the above ratios; (c) error in those corrections and any residual transfer error. If `z_s = log(a_s)` and `d` is the log response difference, `z_t = z_s + d`, with variance `V_t = V_s + V_d + 2 Cov(z_s,d)`. Independent component differences add; their ratios multiply. Shared normalizations, fits, molecules, or experimental outcomes enter once with covariance. The numerical evidence comparison then uses the target prediction and V_t, not an extra intuitive relevance multiplier.

Complementary measurements with defined jobs are: paired rates for the two orthologs under common preparations/conditions; metal×substrate kinetic fits when both change; measured target-system free metal/substrate distributions for physiological extrapolation; and direct calibration/product validation to quantify source assay reliability. None is imposed as a mandatory assay itinerary. If only intrinsic catalytic capability is claimed at the measured conditions, unknown native metal concentrations are not an invented zero or automatic loss of that molecular finding.

## Reset and inspection provenance

Browser PMC access returned a CAPTCHA and Europe PMC was inaccessible. Direct HTTPS retrieval of PMC HTML succeeded and was preserved in `folE2_2009.html`; the text extraction is `folE2_2009.txt`. This worker read complete Methods, Results, Tables 1–3, figure captions and Discussion, plus the article's abstract/introduction. Citation-list entries were not separately reviewed as papers. No numerical values were digitized from Figure 3 and no raw experimental data were reanalysed.

After completing that one paper read and BEFORE the interpretation/calculations above, the worker reloaded/read the complete authority set in four untruncated outputs: AGENTS.md; GOAL.md; EPISODE_STRUCTURE.md; TIME_AWARE_ESTIMATION.md; TOOL_KNOWLEDGE.md; TASK_AND_STEERING.md; TASK_AND_STEERING amendment; EVIDENCE_AXIS_REVIEW amendment; VERBATIM_DIRECTION.md; VERBATIM_RECOVERY_002.md; EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS amendment; scoring_sheet_numeric_review_002.md; local research AGENTS.md; A105_REVIEW_ASSIGNMENTS; and active goal attachment last. The worker's latest assignment remains A105 source-to-target relevance, with individual numerical components and explicit arithmetic, no A106 growth score, and no architecture/production changes.

All source facts, algebraically derived values, conditional uncertainty illustration and proposed scoring formulas remain distinguished. This source packet does not complete A105 or its target-relevance component by itself.
