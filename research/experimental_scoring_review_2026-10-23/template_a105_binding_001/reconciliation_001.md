# Reconciliation of the two completed binding reviews

This is a new arithmetic proposal within part 2 of the user's three-part template. It preserves the two immutable paper summaries. No proposal is treated as accepted scoring. No reader, investigation prompt, production scorer, library publication or scientific run is changed. Zero of the ten scoring sheets are complete.

## What the two cases require the same cells to mean

Both reviews concern an explicitly named molecular binding measurement. Their measured endpoints differ: an MST fluorescence contrast and a DNA-binding response curve. A cell's numerical meaning must therefore be defined through the actual response and controls, rather than through a paper-wide label such as strong evidence. The arithmetic below proposes shared meanings with assay-specific operands; it does not add another evidence axis or episode type.

| Proposed sheet component | Exact native operands and calculation | Meaning and actual population status |
| --- | --- | --- |
| Experimental comparability C | For each nuisance j, measured difference delta_j; response sensitivity beta_j; declared response tolerance tau. C = exp[−0.5 sum_j(beta_j delta_j/tau)²]. Concentration ratios use log differences, pH/temperature use native differences. Correlated changes need a joint discrepancy instead of repeated penalties. | Similarity outside the intended changed variable. Both papers lack the full response-sensitivity/active-concentration operands. Matching stated buffer values contribute exactly zero discrepancy for those values alone. |
| Isolation I | A = observed increment; B = matched background increment; D = A − B. I = clip(sign(A) D / abs(A),0,1), with A = 0 undefined. | The retained measured increment under a stated additive model. NlpI's printed means give 23/29 = 0.79310 conditionally; this is not a complex-occupancy fraction. RbkR lacks extracted calibrated amplitudes. |
| Measurement validity M for a named weakness | Example optical control: M = clip(1 − abs(artifact contrast)/abs(total contrast),0,1). Artifact and total must have the same scale and an experimental relationship supporting the subtraction. | Measured size of a specified artifact. It is not a generic assessment of the whole experiment. Actual control magnitudes are missing in the reviews; a control-description sentence does not populate M. |
| Signal separation S | D and separately estimated technical variance v_t in the same squared units. S = D²/(D² + v_t), retaining sign(D) separately. | Resolution of the measured contrast against technical variation. The required variance partition is missing from the reviewed source extracts. |
| Repeat dispersion P | For the same response or fitted parameter, repeat SD s and mean m: CV = s/abs(m); P = 1/(1 + CV²). Experiment identities and variance level accompany the operands. | Relative repeat variability, not a probability. NlpI's affinity summaries populate P for reported independent experiments, not automatically independent preparations. P for a different endpoint cannot be borrowed. |
| Preference Q | Named comparison of two commensurable midpoint concentrations: R = K_alternative/K_selected; Q = (R−1)/(R+1). Keep its sign and the raw ratio. | Preference for that stated comparison, not overall binding reliability. RbkR response-midpoint ratio 144/41 gives Q = 0.55676 for relative effector potency, not direct flavin-binding affinity. |
| Consistency K across independent matched experiments | x_i = log K_i; n independent matched experiment estimates; s_x² = sum_i(x_i−mean x)²/(n−1); known within-estimate variances v_i. tau_between² = max(0,s_x²−mean v_i); K = exp[−tau_between²/(2 tau_allowed²)]. | Excess between-experiment disagreement beyond measured estimation noise. No matched cross-assay input set was obtained. Differences in temperature, pH, endpoint or fragments are not automatically inconsistency. |

The transforms, tolerance scales and combination weights are proposed choices. Their inputs are continuous measured quantities, not verbal grades translated into fractions. Native quantities remain alongside each transform so the meaning is inspectable.

## Explicit composition without inventing a paper score

For a single named binding comparison, the proposed arithmetic example is:

`B = 100 × C × M × I × (0.5 S + 0.5 P)`.

C, M and I describe distinct restrictions on interpreting the response; the weighted term describes signal resolution and repeated-measurement dispersion. The sum and multipliers are explicit. Equal weights and the 100-point scale are proposed, not accepted or measured. All factors retain their component values; the product does not replace the sheet.

When multiple genuinely independent matched experiments jointly estimate the same quantity, pool their native estimates with their uncertainty and then apply K to that combined contribution. Do not add a second bonus for experiment count after n has already entered its sampling uncertainty. An extended expression is `B_matched = B_joint × K`; K is not applied if it merely repeats the same variability already used in P. Measurement of a separate preference qualifies a separate comparison, for example `B_preference = 100 × C × M × I × P_ratio × Q`, with controls and uncertainty for that precise ratio. It is not an independent occurrence of binding to add to B.

There are two fully specified synthetic arithmetic examples in the paper returns:

- NlpI-style interaction contrast: C = 0.9905909354; M = 0.95; I = 0.8; D = 40; technical SD = 5; independent preparation SD = 6. S = 0.9846153846, P = 0.9779951100 and B = 73.8774782944.
- RbkR-style normalized DNA response: C = 0.98; M = 0.96; A = 0.80; B_background = 0.10; D = 0.70; I = 0.875; technical SD = 0.05; independent preparation SD = 0.07. S = 0.9949238579, P = 0.9900990099 and B = 81.7035412374.

Every number in those two compiled examples is synthetic except the form of the measurement problem. Neither is an actual score for either paper or for ybhP. The actual papers populate selected cells and expose specific missing operands; complete products are not claimed.

## Qualifications added during reconciliation

These qualify the proposals in paper_01_nlpi_001.md and paper_02_rbkr_001.md without replacing those files.

1. **I is a model-dependent signal-isolation cell.** The 23/29 example is not a physically measured percentage attributable to ternary binding. If the comparator effect changes in the mixed condition, an additive subtraction is invalid and the component cannot be populated as attribution. This is the main distinction between a computed contrast and the biological explanation of that contrast.

2. **The independent unit must be named.** P from repeated fitted affinities describes that repeat level. P from separate cultures/preparations describes preparation variation. A technical triplicate cannot silently become a preparation replicate. If the desired cell is precision of the mean rather than repeat dispersion, use its actual standard error or interval width in a separately named cell; do not relabel SD as SE. Both cannot be credited as independent replication.

3. **The proposed curve-residual validity factor needs protection against reusing noise.** Paper 2 offers M_model = 1/(1 + (RMSE/span)²). If raw RMSE is mostly technical noise already included in S, multiplying both applies two penalties to the same variation. A more specific candidate is to assess systematic lack of fit after accounting for independently measured noise: e_systematic² = max(0, RMSE² − v_technical)/span²; M_systematic = 1/(1 + e_systematic²/tau_model²), with tau_model a declared tolerated relative model error. This remains a proposal and requires actual residuals, independent noise and a stated physical model. A flexible empirical fit does not validate unidentifiable Kd, stoichiometry, or active fraction.

4. **Optical and molecular attribution controls must not be silently reused.** If the optical control supplies B in D = A−B, it should enter I once; multiplying an M computed from that identical B would count the correction twice. M may then address a separate measured weakness such as concentration calibration or systematic model error. Similarly, the negative-DNA curve supplies site isolation, not another independent specificity experiment.

5. **Unknown is not zero or a default category.** Source access limitations, missing covariance, missing active fraction and unresolved units produce specific missing operands. They do not imply no binding, nor do they permit a replacement 0.25/0.5/0.75 reliability grade. A hypothetical fully populated example supplies the requested arithmetic while preserving those limits.

6. **Binding quantity and support strength remain different.** Strong affinity does not automatically give a higher reliability score. Concentration controls, background, precision and model adequacy determine whether the affinity measurement is persuasive. If the question concerns occupancy at a relevant free-ligand concentration, calculate occupancy using an explicitly justified binding model and retain the measured concentration; do not make unbounded 1/Kd the annotation score.

## Relation to the organism or supplied target

Experimental comparability compares the tested conditions with each other. Target relevance compares the actual assayed molecule and system with the supplied annotation material. They are distinct operations. A prospective target contribution can combine the assay score with separately populated molecule-correspondence and system-compatibility components, but neither paper establishes a relationship to ybhP.

This review does not provide a finished general transfer formula. Required work is specific: define how original sequence/structure comparison scores, binding-site correspondence, construct changes, ligand/DNA identity, cofactor state and condition-response measurements populate those numerical components; identify shared evidence so transfer does not duplicate the activity measurement. No sequence-only restriction or generic qualitative H fallback is proposed. A broad protein-family relationship cannot silently transfer the identity of a DNA target, native complex, effector ligand, or downstream regulatory sign.

For system compatibility, the nuisance-response calculation can be used with differences between assay and target conditions when those conditions and sensitivities are actually measured. For membrane anchoring or altered protein constructs, a matched biochemical comparison can supply an observed response ratio with uncertainty. Absent such evidence, the precise unresolved relationship must remain visible; no claim is made that its score has been solved by this binding review.

## Exact coverage and remaining papers

Completed primary rereads: NlpI, PMC7049810; RbkR, PMC5397151. Each received the complete post-paper authority reset, including all original user quotations and current correction/assignment text. Startup authority reading was separate. NlpI's reset included a repair read of a document with an 18-token truncated passage; the repaired whole document and latest instructions were read in full. RbkR's reset was untruncated. Reread source packets do not count as new discoveries. Both Figure 2 (NlpI) and Figure 4 (RbkR) were visually inspected; arithmetic was recomputed with Python. No raw fit, scientific experiment, code test suite, reader execution or production investigation was run.

The initial case-index inventory covered eight groups and thirteen primary source links, but it is not counted as thirteen paper reviews. These eleven seed papers remain unreviewed in this assignment:

| Group | Remaining primary paper(s) |
| --- | --- |
| cellular_popZ | [PMC2745220](https://pmc.ncbi.nlm.nih.gov/articles/PMC2745220/); [PMC2614312](https://pmc.ncbi.nlm.nih.gov/articles/PMC2614312/) |
| cellular_yabA | [PMC1413692](https://pmc.ncbi.nlm.nih.gov/articles/PMC1413692/) |
| reg_iscR_state_target_specificity | [PMC2709974](https://pmc.ncbi.nlm.nih.gov/articles/PMC2709974/); [PMC3447993](https://pmc.ncbi.nlm.nih.gov/articles/PMC3447993/); [PMC4108476](https://pmc.ncbi.nlm.nih.gov/articles/PMC4108476/); [PMC3676455](https://pmc.ncbi.nlm.nih.gov/articles/PMC3676455/); [PMC12594620](https://pmc.ncbi.nlm.nih.gov/articles/PMC12594620/) |
| organism_04_gcsr | [PMC4894688](https://pmc.ncbi.nlm.nih.gov/articles/PMC4894688/) |
| organism_15_nifi | [PMC94954](https://pmc.ncbi.nlm.nih.gov/articles/PMC94954/) |
| organism_16_malr | [PMC3911195](https://pmc.ncbi.nlm.nih.gov/articles/PMC3911195/) |

No absence of A105 binding measurements in the remaining papers is claimed from the index alone. No additional paper was begun after the parent's direction to complete this two-paper reconciliation. Production scoring and all existing records remain untouched by this work.
