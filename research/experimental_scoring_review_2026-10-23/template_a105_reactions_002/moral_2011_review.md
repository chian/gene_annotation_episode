# Moral et al. 2011: quantitative calibration and reaction isolation for A105

New research note, 2026-10-23. This is a component proposal for the user's numerical scoring sheet, not an adopted scoring policy, completed sheet, or production reader. Reported measurements, derived arithmetic, conditional calculations, and proposed formulas are identified below. No perturbation or organism-performance evidence enters this A105 example.

## Source and completed reading

Moral ME, Tu C, Richards NGJ, Silverman DN. **Membrane inlet for mass spectrometric measurement of catalysis by enzymatic decarboxylases.** Analytical Biochemistry 418(1), 73–77 (2011). DOI [10.1016/j.ab.2011.06.031](https://doi.org/10.1016/j.ab.2011.06.031); PMID 21782782; [PMC3164234](https://pmc.ncbi.nlm.nih.gov/articles/PMC3164234/).

Inspected the complete main text, its Methods, Results, Discussion, Table 1, all figure captions, and Figures 2–5 visually. Local custody: `moral_2011_main.html`, `moral_2011_main.txt`, and `moral_2011_fig2.jpg` through `moral_2011_fig5.jpg`. The supplementary file was not recovered. `moral_2011_supp.doc` is an HTML access-failure response, and `moral_2011_supp_epmc.zip` is an XML error response; neither is usable supplementary evidence. Supplement-only replicate details or low-concentration plots are not claimed inspected.

The explicit gap motivating this additional paper was numerical assay calibration and measurable mixed-reaction contributions. This is a separate primary source cited by Kellett et al. 2013 for the membrane-inlet method. It supplies measurements for its own apparatus and experimental conditions, not the missing detection limit of Kellett's FrsA experiments.

## Experimental definitions before any scoring

| Item | Actual comparison and limitation |
| --- | --- |
| Biological subject | Wild-type oxalate decarboxylase, OxDC, from **Bacillus subtilis**, expressed from a polyhistidine-tagged pET32a construct in **E. coli BL21(DE3)**; Ni-NTA and G25 purification. This is not FrsA or the project's ybhP target. |
| Intended molecular inference | Oxalate decarboxylation produces one CO2 and one formate per oxalate. OxDC also has a small oxidase reaction producing two CO2 and one H2O2 while consuming one O2 per oxalate. A CO2 signal therefore combines two chemical pathways. |
| Mixture/coexistence | One recombinant wild-type enzyme preparation, with two catalytic activities of that preparation. No deliberately co-mingled wild-type/mutant population. The chemical partition does not establish that every detected activity comes from the named protein rather than a contaminant. |
| Main method comparison | Continuous MIMS measurement of CO2 versus a quenched, formate-dehydrogenase-coupled endpoint assay. Detector/readout method is the intended changed variable; additional reaction-mixture and timing differences must be considered separately. |
| Shared conditions | The main assays use 50 mM acetate, pH 4.2, 0.2% Triton X-100, and 1.4 μM OxDC. MIMS is at 25°C; coupled experiments are at 23–25°C. |
| Additional differences | MIMS uses potassium 13C2-oxalate, 99% labeled, and a 2 mL reaction. Coupled assays use a 100 μL reaction, include 0.5 mM o-phenylenediamine, and are quenched with NaOH before formate measurement. The text does not explicitly establish the isotope label in the coupled assays or identical enzyme aliquots/batches. Do not assume either. The substrate series also differ. |
| Endpoints | MIMS mass-45 ion current calibrated to CO2 concentration and initial production rate. Coupled assay: formate converted to NADH, then A340 after incubation with NAD+ and formate dehydrogenase. Product concentration, concentration/time, and turnover/time have different denominators. |
| Enzyme denominator | Total measured enzyme concentration, not active-site titration. ICP-MS measured 1.4 Mn ions per enzyme monomer; there are two Mn sites and the occupied-site distribution is unknown. **1.4/2 is not a measured active-enzyme fraction.** |
| Controls | Carbonate standards, formate standards in prequenched assay matrix, O2 calibration and a zero-O2 check, and N2 stability. O2 without enzyme showed negligible decay, but the text supplies no numerical blank variance. |
| Error meanings | Table 1 uncertainties are standard errors from Michaelis–Menten fitting. Calibration percentages are reported standard deviations from three experiments. Neither is automatically between-preparation reproducibility. |

Source locations: Methods, “Enzyme and materials,” “Membrane inlet mass spectrometry,” and “Coupled assay”; Results, calibration, oxygen and kinetic analysis; Table 1 and Figures 2–5.

## 1. Calibration uncertainty is numerical and concentration dependent

**Reported:** known carbonate introduced into an acidic solution, approximately pH 2, gives a linear CO2 calibration. The paper states that 99.9% of carbonate is CO2 in that calibration solution. The Figure 3 least-squares correlation coefficient is 0.999; the paper does not label it R². Calibration was repeated three times. The author-reported lower detection limit is 10 μM, with SD 22% over three experiments. The instrument was tested down to 5 μM. The paper does not define the lower limit by a specified false-positive probability or blank-SD rule.

**Derived numerical cells:**

| Calibration concentration | Reported relative SD | Derived absolute SD | Relative variance contribution, SD²/mean² | Reciprocal relative variance |
| --- | ---: | ---: | ---: | ---: |
| 10 μM | 0.22 | 2.2 μM | 0.0484 | 20.6612 |
| 400 μM | 0.10 | 40 μM | 0.0100 | 100 |
| 3,000 μM | 0.08 | 240 μM | 0.0064 | 156.25 |
| 4,800 μM | 0.03 | 144 μM | 0.0009 | 1,111.11 |

These numbers quantify calibration dispersion at the demonstrated concentrations. They are not enzyme-activity support scores or percentages of correct annotation. In particular, 10/2.2 = 4.545 is concentration divided by its reported calibration SD, **not** a measured sample-versus-null signal-to-noise ratio. A standard's dispersion does not supply the blank distribution or the false-negative curve.

**Proposed use in the numerical sheet:** if an assay's response is calibrated with a slope `m`, the calibrated rate is `v = (s − b)/m`, where `s` is observed signal/time and `b` is the matched background signal/time. Its uncertainty contains the calibration term, including covariance where standards and samples share a measurement:

`Var(log v) ≈ Var(s − b)/(s − b)² + Var(m)/m² − 2 Cov(s − b,m)/[(s − b)m]`.

The relative-variance cells above show why calibration precision must be evaluated at the relevant response range. They must not be substituted wholesale for `Var(m)/m²`: estimating a fitted slope and estimating a concentration from that slope are different calculations. Raw calibration responses and fit covariance would populate the actual term. If the parameter of interest is a mean of three independent calibration measurements, its random variance may be SD²/3; that does not reduce a shared systematic bias, and the source does not establish that all error here is independent random error.

In a total variance `V = V_signal + V_calibration + V_comparability + V_isolation + V_correspondence + covariance terms`, calibration enters by addition once. A displayed precision-retention multiplier `C_cal = V_without_cal/(V_without_cal + V_calibration)` can be useful, but `C_cal / V_without_cal = 1/V`; one must not then apply `C_cal` again to an estimate already weighted by `1/V`.

**Missing/complementary measurements:** replicate blanks and spikes in the actual reaction matrix; recovery at several concentrations; calibration slope/intercept covariance; preparation/date identities; and a detection/quantification rule with its error rates. A high correlation coefficient does not supply these.

**FrsA restriction:** this source's approximately pH-2, mass-44 carbonate calibration and its apparatus do not establish a 10 μM detection limit for the 2013 mass-45 FrsA experiment at pH 7, 37°C, and 500 mM KCl. The detector channel, CO2 speciation, matrix, temperature, instrument and measurement interval require calibration. The threshold remains unknown for that FrsA experiment.

## 2. A measured detector delay yields a quantitative comparability correction

**Reported:** CO2 step response has a first-order half-time of about 4 seconds. Reaction traces show an initial approximately 8–12-second response delay. This comes from the apparatus response, not a reported induction period of the enzyme. Source: Results and Figure 4.

**Derived, conditional response model:** let `τ = 4/ln(2) = 5.77078 s`. For a constant true product-production rate `v`, starting at time zero with a first-order detector,

`C_observed(t) = v [t − τ(1 − exp(−t/τ))]`.

Thus the instantaneous measured slope is multiplied by

`q_slope(t) = 1 − exp(−t/τ)`,

while an origin-to-time endpoint slope is multiplied by

`q_endpoint(t) = 1 − [τ/t](1 − exp(−t/τ))`.

| Time after mixing | Derived instantaneous-slope factor | Derived origin-to-time slope factor |
| --- | ---: | ---: |
| 8 s | 0.750000 | 0.458989 |
| 12 s | 0.875000 | 0.579214 |
| 20 s | 0.968750 | 0.720478 |

These are calculations under a constant-production model using the reported response time, not digitized enzyme rates. They show that nominally equal readout times need not measure equal fractions of the underlying rate. An 8/12 time ratio is not an experimental relevance score; the measured response function supplies the quantitative effect.

**Placement and combination:** when comparing an early MIMS rate with a rate from another method, `v_corrected = v_observed/q` adjusts the endpoint to a common response definition. Its uncertainty includes the uncertainty in `q`, estimated from repeated step-response measurements and the actual fitting window. With log-rate variables, `V_corrected = V_observed + Var(log q) − 2Cov(log v_observed,log q)`. A correction for detector loss is not followed by a second multiplication by `q` as a reliability penalty. Alternatively, convolve the reaction model with the detector-response model and fit the original trace; the correction and uncertainty are then already in that likelihood.

**Limit:** the paper's reported fit uses a specified approximately 5–10% portion of the reaction progress, so these examples do not show that the published 71 s⁻¹ requires any particular numerical correction. Substrate depletion, enzyme inactivation and mixing may violate the constant-rate illustration. Actual fit windows, trace data and replicated response-time uncertainty are needed for a correction of the reported kinetics.

## 3. Simultaneous products isolate chemical pathways through stoichiometric arithmetic

Define blank-corrected, calibrated rates in the same concentration/time units:

- `C`: CO2 production rate.
- `O`: positive O2 consumption rate.
- `d`: oxalate decarboxylation rate.
- `o`: oxalate oxidation rate.

For the two stated reactions, assuming no other relevant sources or sinks,

`C = d + 2o`, `O = o`, and therefore `d = C − 2O`.

The fraction of the **CO2 signal** attributable to decarboxylation is

`I_reaction = d/C = 1 − 2O/C`.

This is a chemical-signal isolation component with a defined denominator. It is different from the fraction of **oxalate turnover** due to decarboxylation. It is also different from protein attribution.

**Reported:** at 50 mM oxalate and air-saturated O2, oxidation accounts for 0.3–0.5% of overall catalytic degradation of oxalate. Source: Results and Discussion comparing O2 consumption with CO2 production. The text supplies this interval, not raw paired calibrated slopes or an uncertainty distribution.

Let `f = o/(d + o)` denote that reported oxalate-turnover fraction. Then

`O/C = f/(1 + f)` and `I_reaction = (1 − f)/(1 + f)`.

**Derived:**

| Reported oxidation fraction of oxalate turnover | Derived O2/CO2 rate ratio | Derived decarboxylation fraction of CO2 signal |
| --- | ---: | ---: |
| 0.003 | 0.00299103 | 0.99401795 |
| 0.005 | 0.00497512 | 0.99004975 |

Using `1 − f` would use the wrong denominator for correction of the CO2 signal. The explicit interpretation here follows the Discussion's overall-oxalate-degradation denominator; recovery of raw slopes would remove dependence on that verbal denominator.

**Placement and combination:** the isolated rate enters the molecular-activity estimate as `a = (C − 2O)/E`, equivalently `a = C I_reaction/E`, where `E` is enzyme concentration. Its variance is

`Var(d) = Var(C) + 4 Var(O) − 4 Cov(C,O)`.

One may display `I_reaction` as the measured mixed-contribution multiplier, but do not subtract `2O` and then multiply by `I_reaction` again. If `f` is used, its uncertainty and its covariance with the CO2 estimate must propagate. The reported interval is not a standard deviation or a probability distribution.

**Conditional arithmetic, not a corrected published estimate:** if the 0.3–0.5% partition also applies to the fitted saturation rate of 71 s⁻¹, multiplying by the derived isolation fraction gives 70.2935–70.5753 s⁻¹. The corresponding 2 s⁻¹ fit SE alone would scale to 1.9801–1.9880 s⁻¹, before uncertainty in `f`. The partition was measured at a specified substrate/O2 condition, so applying it to a complete substrate-series fit is an additional assumption. Its 0.6–1.0% CO2 contribution cannot by itself explain the 71 versus 44 s⁻¹ method difference below.

**What this does not isolate:** simultaneous O2/CO2 measures separate reactions under this chemical model. It does not prove both arise from the intended protein, exclude other O2 sinks or CO2 sources, establish occupied catalytic-site fraction, or remove shared calibration uncertainty. Quantitative formate, H2O2 and oxalate balances, paired blanks, fractionated protein/activity profiles, and active-site titration would address different remaining weaknesses. These are complements, not automatically independent supporting experiments.

## 4. Assay agreement must compare effect sizes and uncertainties, not prose

**Reported Table 1** (errors are fit standard errors):

| Parameter | MIMS | Coupled formate assay |
| --- | ---: | ---: |
| Km | 4.0 ± 0.5 mM | 3.9 ± 0.4 mM |
| kcat | 71 ± 2 s⁻¹ | 44 ± 1 s⁻¹ |
| kcat/Km | 18 ± 1 mM⁻¹ s⁻¹ | 11 ± 1 mM⁻¹ s⁻¹ |

**Derived method contrasts:** the kcat ratio is `71/44 = 1.61364`; the absolute difference is `27 s⁻¹`. Assuming independent fit errors only, the difference SE is `sqrt(2² + 1²) = 2.23607 s⁻¹` and the standardized difference is `12.0748`, with squared residual `145.8`. The log ratio is `0.478490`, with approximate fit-only SE `sqrt((2/71)² + (1/44)²) = 0.0361942`. Km differs by `0.1 mM`, with fit-only standardized difference `0.156174`. The efficiency ratio is `18/11 = 1.63636`.

The authors describe the kinetic parameters as in reasonable agreement. The sheet should preserve the numerical differences: substrate-affinity estimates agree much more closely than turnover estimates on their reported fit-error scales. This is not a claim of a formal between-preparation p-value: unknown method systematic effects, temperature and reagent differences, shared preparations and fit/calibration covariance prevent that interpretation.

**Intended comparison versus comparability:** changing the measurement method is deliberate. Differences in reaction composition, temperature, isotope, sampling/time integration and enzyme aliquot are additional changes. The observed ratio therefore estimates the difference between these complete assay configurations; it does not isolate an intrinsic “MIMS bias.” Which part is due to the detector versus the extra reagent or sample handling is unmeasured.

**Proposed sheet roles:**

1. Retain the log contrast, its full variance, and its denominator as a numerical consistency residual. In a general set of comparable measurements, `Q = (a − Xβ)ᵀ Σ⁻¹(a − Xβ)` exposes disagreement with the declared shared-parameter model. Table 1 supplies only a partial covariance matrix.
2. Do not average away the discrepancy. A naive fit-error-only inverse-variance mean is `49.4 ± 0.8944 s⁻¹`; that apparent precision hides the unresolved method difference. It is a diagnostic of the inappropriate pooling model, not this note's recommended activity estimate.
3. A separately measured bridge `K_method = rate_configuration_B/rate_configuration_A` could map later observations to a declared reference configuration. Its variance would enter the comparability term. Deriving a bridge from this very pair, then using the same pair as an independent successful validation of that bridge, would double count the data.
4. Use paired independent preparations measured by both methods, a factorial control for the extra reagent, matched temperature and reaction matrices, and complete time courses to separate method, preparation and condition effects. A measured temperature coefficient or response surface converts a temperature mismatch to expected rate impact; `23/25` does not.

## 5. Combined numerical component interface, with honest missing values

For a positive reaction rate from preparation `j`, a proposed standardized molecular-activity quantity is

`a_j = [C_j − 2O_j − h_j] / [E_j K_j]`.

Here `C_j − 2O_j` isolates the intended reaction; `h_j` is an independently measured remaining contribution to that reaction from an unintended catalyst; `E_j` is the declared enzyme denominator; and `K_j` is the measured response ratio mapping nuisance conditions to reference conditions. If total active-site concentration rather than total protein is used for `E_j`, do not apply the active fraction again. A same-condition comparison does not need a condition correction, but an absent bridge across different conditions is not numerically set to 1.

For positive quantities, define `ell_j = log(a_j)`. The sheet retains measured variance components and their covariance, so a scalar shorthand is

`V_j = V_signal,j + V_calibration,j + V_comparability,j + V_isolation,j + V_correspondence,j + covariance_terms`.

The exact calculation uses the Jacobian and the full input covariance, `V_j = J_j Σ_inputs,j J_jᵀ`, rather than treating overlapping cells as independent. Independent preparation likelihoods can multiply; equivalently log likelihood contributions can sum. Correlated channels from one reaction use a joint likelihood. If a common molecular parameter is justified, generalized least squares gives

`ell_combined = (1ᵀ Σ⁻¹ ell)/(1ᵀ Σ⁻¹ 1)` and `Var(ell_combined) = 1/(1ᵀ Σ⁻¹ 1)`.

These are explicit sums/products with measurable operands, not an overall verbal relevance grade. A downstream annotation comparison can use the joint likelihood ratio of declared molecular-function models, `S = log L(data | function 1) − log L(data | alternative)`. Choosing and calibrating those models is a remaining sheet-level decision; no annotation-support probability follows from a rate, a correlation coefficient or a paper count alone.

For this paper, the known numerical cells include the calibration dispersion, response time, reaction-partition interval, and method contrasts above. The missing inputs prevent calculation of a complete total variance, a target-system correspondence component, or an annotation likelihood ratio. Neither a FrsA nor ybhP correspondence is established. This source is a worked method example, not new evidence that either target has OxDC activity.

| Exact reader-populated input | Unit / uncertainty meaning | Numerical output or operation |
| --- | --- | --- |
| Standard concentrations, response replicates, blank responses, calibration model and fit covariance | Concentration and instrument response; distinguish SD, SEM and fit SE | Calibrated concentration/rate and calibration variance at the sample response |
| Step-response trace and its fitting model | Seconds and concentration; replicated uncertainty in half-time | `τ`, response convolution, or window-specific `q` and variance |
| Paired CO2/O2 slopes, channel calibrations, blanks and covariance | Same concentration/time units | `d = C − 2O`, `I_reaction = d/C`, and `Var(d)` |
| Enzyme amount, concentration assay, active-site measurement if available | μM total protein or μM active sites; keep denominator explicit | `d/E` and concentration uncertainty; no purity-to-activity shortcut |
| Matched nuisance-response measurements and experimental settings | Native rate response versus pH, temperature, salt, etc. | `K_j` and propagated bridge uncertainty; unknown where unmeasured |
| Paired method rates and preparation identities | Same molecular endpoint and units | Log method contrast, covariance, and consistency residual |
| Independent unintended-catalyst contribution | Concentration/time with its uncertainty | Subtract `h_j` once; identity of the catalyst remains separate from chemical partition |
| Evidence linking assayed subject to annotation target | Actual relation measurements and their defined model | Target correspondence remains unknown in this example |

## Shared evidence and source-to-component map

| Inspected primary location | Component justified | Dependence that must be retained |
| --- | --- | --- |
| Calibration Results and Figure 3 | Concentration-specific calibration uncertainty; stated detection limit with its definition limits | Same fitted calibration is shared by all rates using it; do not count correlation and calibration dispersion as independent experiments |
| Response Results and Figure 4 | Measured detector response for comparison of rate windows | Correction and corrected-rate uncertainty concern the same trace; a delay factor is not another support multiplier |
| Reaction equations, Results and Figure 2; Discussion | Stoichiometric reaction-isolation calculation using simultaneous CO2 and O2 | Same reaction and enzyme preparation; shared drift and channel calibration can produce covariance |
| Table 1 and Methods | Quantitative disagreement of complete assay configurations; need for nuisance bridges | Km, kcat and kcat/Km are not three independent activity experiments; method/preparation covariance is unresolved |
| Enzyme/materials Methods | Denominator limitation from metal occupancy | Measured Mn count is not measured catalytic-site occupancy or activity purity |

No metadata field is turned into a numeric category score. The independent scientific contribution here is the calibration/method investigation; multiple calculations from its same measurements do not create multiple independent experiments.

## Per-paper authority reset actually completed

After the complete main-paper/figure read, a combined authority-read output was truncated. It was not accepted as a completed reset. The affected files were reread separately in full, then the entire remaining required set was read in full without truncation, before the interpretations and arithmetic in this note:

1. `AGENTS.md` and `GOAL.md`.
2. `docs/EPISODE_STRUCTURE.md` and `docs/TIME_AWARE_ESTIMATION.md`.
3. `docs/TOOL_KNOWLEDGE.md` and `docs/TASK_AND_STEERING.md`.
4. `docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md`.
5. `docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md`.
6. `research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md` and `VERBATIM_RECOVERY_002.md`.
7. `docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md`.
8. `verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md`.
9. `research/experimental_scoring_review_2026-10-23/AGENTS.md`.
10. `research/experimental_scoring_review_2026-10-23/A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md`.
11. `research/experimental_scoring_review_2026-10-23/TEN_SCORING_SHEETS_GOAL_2026-10-23_001.md`.
12. Latest activated user goal, read last: `/home/chia/.codex/attachments/9a858f85-d1dc-4f59-b574-9988cc09dee2/pasted-text-1.txt`.

The parent's later direction explicitly forbids transferring this method paper's threshold into the missing FrsA detection-limit field. Parent handoff is a ready-path notification only until a particular paper packet is requested. Arithmetic was evaluated with Python 3 and retained in `moral_2011_derived_arithmetic.json`; these checks establish calculations, not production readers or scientific replication.
