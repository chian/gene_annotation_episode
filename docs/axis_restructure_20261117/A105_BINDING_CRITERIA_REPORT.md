# A105 binding assays: criteria, values, curves and unknown weights (2026-11-21)

All 25 assays are present in the parts (spr, itc, bli, gci, fp, fret, mst, trp, fcs, elisa, alpha, radioligand, spa, pulldown, emsa, sec, dialysis, auc, dsf, cetsa, bret, y2h, split_reporter, pla, proximity). None is missing.

## How to read this

1. A degree runs from the zero end (degree 0) to full agreement (degree 1.0); between the two ends it follows the curve named in the "Shape between" column.
2. A conflicting criterion counts 0 in the weight.
3. An unknown criterion counts the type's unknown weight (WEIGHT_UNKNOWN_BY_TYPE, or its per-criterion override); a not-applicable criterion is dropped.
4. The result's weight is the mean over its applicable criteria.
5. The score is the log ratio from the strength anchors (QUALITATIVE_LOG_RATIO x strength) times that weight.

## Values for the owner to confirm

Every row is taken from the "owner to confirm" lists of the five parts. Where a part says that no value is marked in the code but names a caveat, a from-memory citation or an open owner decision, the row says so in the reason column.

| Assay | Name | Value | Reason |
|---|---|---|---|
| itc | C_VALUE_ZERO_MIN_SATURATED | 0.01 | Plateau shift of the low-c zero end (Turnbull and Daranas 2003); cited from memory and not checked. No value is marked owner to confirm in the code. |
| itc | method sources in the docstring | not a number | Cited from memory and not checked. |
| gci | IMMOBILIZATION_MAX and zero end | 2000 and 4000 pg/mm2 | A protein-protein default; the right level depends on the masses. Stated caveat, not marked owner to confirm. |
| gci | assumed instrument noise | 0.1 pg/mm2 | Taken conservatively (the vendor claims lower). Stated caveat, not marked owner to confirm. |
| fp | SLOW_KON_PER_M_PER_S | 1.0e5 | Slow end of association rates for a labelled tracer and a protein (about 1e5 to 1e7 per M per s; Schreiber, Haran and Zhou 2009, cited from memory). Sets T_SLOW = 100 x T_FAST, where the incubation degree reaches 1. Slower gated binding (1e3 to 1e4) is treated as rare. DECISION A 2026-11-21: T_FAST kept, SLOW_KON new, 5 min floor now proportional. |
| fret | Z_PRIME_MIN | 0.5 | HTS limit for a robust assay. |
| fret | Z_PRIME_ZERO | 0.0 | Bands touch. |
| fret | DONOR_LIFETIME_US | terbium 2000, europium 600 | Lanthanide lifetimes. |
| fret | REFERENCE_LIFETIME_US | 1000 | The lifetime MIN_INTEGRATION_US was set for. |
| fret | INTEGRATION_NOISE_EXPONENT | 0.5 | Counting noise. |
| fret | HILL_FIT_PARAMETERS | 4 | A Hill fit frees one more parameter. |
| fret | TIGHT_BINDING_FULL_OVER_KD and TIGHT_BINDING_ZERO_OVER_KD | 10 and 100 | Curve rounding at equivalence. |
| fret | APPROACH_FULL_HALF_LIVES and APPROACH_ZERO_HALF_LIVES | 5 and 1 | Approach to equilibrium. |
| fret | EQUILIBRATION_REFERENCE_NM | 2 | Constant at which 15 minutes is five half-lives. |
| fret | KON_SLOW_PER_M_S | 1e5 | Slow association; cited from memory. |
| fret | shape of labelled over KD | log of the depletion bias | The docstring marks the change of the labelled-over-KD shape to the log of the depletion bias as owner to confirm. |
| fret | incubation cliff | a curve | The docstring marks the change of the incubation cliff into a curve as owner to confirm. |
| mst | MIN_INCUBATION_MIN | 10 | Five half-lives of koff 0.01 per s with a margin. |
| mst | EQUILIBRATION_REFERENCE_NM | 10 | The KD behind that 10 minutes. |
| mst | KON_FAST_PER_M_S | 1e6 | Fast protein association. |
| mst | KON_SLOW_PER_M_S | 1e5 | Slow association; from memory. |
| trp | ARTEFACT_FULL_OVER_CHANGE | 0.2 | One fifth of the smallest fully usable change. |
| trp | HILL_FIT_PARAMETERS | 3 | Parameter count of a Hill fit. |
| trp | MIN_INCUBATION_MIN | 2 | Mixing floor, now proportional. |
| trp | INCUBATION_ZERO_AGREEMENT_MIN | 1 | Decides nothing since 2026-11-21, kept for the owner. |
| trp | FAST_KON_PER_M_PER_S | 1e8 | Fast end for small ligands. |
| trp | SLOW_KON_PER_M_PER_S | 1e5 | Slow end; citation from memory. |
| fcs | PARTICLE_NUMBER_LOW_ZERO_AGREEMENT and PARTICLE_NUMBER_HIGH_ZERO_AGREEMENT | 0.01 and 100 | A decade beyond the window. |
| fcs | MAX_COUNT_RATE_KHZ and COUNT_RATE_ZERO_KHZ | 1000 and 10000 | Detector linear range, 50 ns dead time. |
| fcs | LABELLED_LOW_ZERO_AGREEMENT_NM and LABELLED_HIGH_ZERO_AGREEMENT_NM | 0.03 and 300 | Same decades in nM. |
| fcs | TIGHT_BINDING_FULL_OVER_KD and TIGHT_BINDING_ZERO_OVER_KD | 10 and 100 | Curve rounding against the noise of an amplitude fraction. |
| fcs | DEPLETION_BIAS_SLOPE | 0.5 | Apparent KD about KD + labelled/2. |
| fcs | SERIES_PRECISION_EXPONENT | 0.5 | Each point is its own estimate. |
| fcs | KON_MAX_PER_M_S | 1e8 | Diffusion limit. |
| fcs | KON_SLOW_PER_M_S | 1e5 | Slow association; from memory. |
| fcs | EQUILIBRATION_HALF_LIVES | 5 | 97 percent of equilibrium. |
| fcs | ACQUISITION_NOISE_EXPONENT | 0.5 | Noise falls as sqrt of time. |
| fcs | REFERENCE_DIFFUSION_TIME_US and REFERENCE_BRIGHTNESS_KHZ | 1000 and 10 | The conditions behind 60 s. |
| fcs | symmetry of the mass-consistency curve | symmetric | The docstring leaves open that aggregation (a complex slower than expected) is worse than a faster-than-expected one. |
| fcs | unknown weight | 0.80 (override calibration_applicability 0.75) | The docstring leaves open that the unknown weight for FCS is for the owner to set. |
| elisa | KON_SLOW_PER_M_S | 1e4 | New, slow end for coated-well partners; from memory. The incubation is a curve (Decision A, 2026-11-21) with KON_FAST_PER_M_S 1e6, EQUILIBRATION_REFERENCE_NM 1 and EQUILIBRATION_REFERENCE_MIN 30 kept from the old rule. |
| alpha | SLOW_ASSOCIATION_RATE_PER_M_S | 1e5 | Slow end of association without electrostatic steering; cited from memory. FAST_ASSOCIATION_RATE_PER_M_S 1e6 and EQUILIBRATION_REFERENCE_NM 1.0 are marked EXPERT_REVIEW only. |
| radioligand | REFERENCE_KD_NM | 1.0 | The KD for which 30 minutes stands; the needed time grows as 1 / KD; new. |
| spa | KON_FAST_PER_M_S | 1e8 | Fastest plausible association rate; from memory. |
| spa | KON_SLOW_PER_M_S | 1e5 | Slow association rate; from memory. |
| spa | EQUILIBRIUM_HALF_TIMES in T_FAST and T_SLOW | 5 | t_eq = 5 x ln2 / (kon x KD); marked "owner to confirm". |
| emsa | SLOW_ASSOCIATION_RATE_PER_M_PER_S | 1e6 | Slow end of association for a protein on a DNA site; cited from memory; two decades below the fast end. |
| sec | STOICHIOMETRY_ZERO_FOLD | 2.0 | SEC keeps its 2:1 zero end (population reading); AUC uses 1.5. The code says "the difference is for the owner to settle". |
| auc | STOICHIOMETRY_ZERO_AGREEMENT_FOLD | 1.5 | Differs from the SEC zero fold 2.0; the SEC file says the difference is for the owner to settle. |
| dialysis | Decision C (2026-11-21), concentration_series span: LOW_FACTOR 0.5 to LOW_ZERO_AGREEMENT_FACTOR 1.0, HIGH_FACTOR 4.0 to HIGH_ZERO_AGREEMENT_FACTOR 1.0 | linear in occupancy x / (1 + x) instead of in x | Same ends, no new constants. This is the occupancy scale the other assays use; no dialysis-specific reason for linear in x was found. |
| cetsa | Tm fall not counted as engagement | ruling needed | The criterion asks for a rise and a computed fall stays conflicting, although thermal proteome profiling counts a destabilised target as a hit. Counting a fall would need a signed shift field, a direction fact and an owner ruling. |
| bret | FIT_R_SQUARED_ZERO_AGREEMENT | 0.50 | Lowered from 0.80 because cell BRET scatter in x gives R squared near 0.8 for a valid curve ("owner to confirm"). |
| bret | unknown weight of the bystander test (background_alternatives) | 0.70 (type value, no override) | "Central, owner to decide". |
| y2h | REPORTER_FOLD_ZERO_AGREEMENT | 2 | Conflicting at 2-fold or below is kept; the owner is asked whether, now that the spread is collected, the zero end should move to a fold of 1 (no larger than the control). |
| y2h | ONE_OF_TWO_SHARE | 0.5 | The observed fraction, no literature value; owner asked whether to use a researched fraction. |
| split_reporter | per-reporter full value for signal_to_background | 10 (now one value; lower for a split fluorescent protein) | An owner or expert question, not a gap. |
| pla | REDUCTION_ZERO_AGREEMENT_PERCENT | 20 | Conflicting at a fall of 20 percent or less: "the most consequential number here (owner question, kept)", because without the depletion a small fall could be a failed knockdown rather than a cross-reactive antibody. |
| proximity | EXPRESSION_ZERO_AGREEMENT | 10 | "The expert zero end (no standard value; EXPERT_REVIEW)"; not marked owner to confirm by name. |
| proximity | FOLD_FULL_AGREEMENT_UNMATCHED | 8 | "Expert judgment, no standard value"; not marked owner to confirm by name. |

Assays with no owner-to-confirm value in their part: spr, bli, pulldown. (spr, bli and pulldown state that every researched value is marked EXPERT_REVIEW.)

## Shared rules stated at the top of each part

The five parts open with rules that apply to all assays in the part. They are copied here unchanged, so that the assay sections below can be read without the parts.

### Part 0: SPR, ITC, BLI, GCI, FP

All numbers are copied from the converter files (`literature_<assay>_converter.py`) and `literature_row_contract.py` as they are now. Rules shared by all five:

- "Degree" is 1.0 at full agreement and falls to 0 at "zero at". For a continuous value, a value at or beyond "zero at" is conflicting (no degree). Counts never conflict.
- A sheet criterion made of several members carries the smallest degree of its members. Any conflicting member makes it conflicting. Else any unknown member makes it unknown.
- Weak quote support multiplies a supported degree: implied by 0.7, about_something_else by 0.3.
- Quantitative strength: s = smoothstep(p) / (1 + r^2). p is the position of log10 of the constant between the noise end (0) and the strong end (1). r = sqrt(variance) / effect (0 when no spread). log_ratio = QUALITATIVE_LOG_RATIO x s.
- Spread: standard_error gives variance = se^2. standard_deviation gives sd^2 / n, only when replicates are supported (independent). confidence_interval is not converted. Otherwise no variance.
- Roles never filled by any of these five (the same reasons in every converter): recovery (no matrix recovery measurement), attributed signal and total signal (the control is not an attribution fraction), condition test and reference (no matched nuisance-condition response), assertion and alternative prediction (belong to the target assertion, not the experiment), effect degrees of freedom (no Student-t model selected).



### Part 1: FRET, MST, Trp quenching, FCS, ELISA

Source: the converter, criteria and grader files of each assay in `episode_support/literature/grading/experimental_activity_evidence/`, and `literature_row_contract.py`. Every number below is copied from that code as it is now.

How a degree works, for all five assays. A judged member gets a degree of 1.0 at the "full agreement" value and 0 at the "zero" value. "Conflicting" means the paper's own number is at or past the zero value, so the sheet takes the standard as not met. "Never conflicting" means the member can only lower the degree. A sheet criterion that is supported carries the smallest degree of its members. Weak quote support multiplies the degree by 0.7 (implied) or 0.3 (about something else).

How the effect becomes a strength (OWNER_DECISION 15, same for all five). p = (log10 effect - log10 noise end) / (log10 strong end - log10 noise end), clipped to 0..1. s = (3p^2 - 2p^3) / (1 + r^2), where r = sqrt(variance) / effect (r = 0 when no spread is stated). log ratio = QUALITATIVE_LOG_RATIO x s. A quantitative result never opposes; only a stated non-detection opposes, at the full QUALITATIVE_LOG_RATIO value. The criteria never change this direction; they lower the weight only.

How the spread enters the variance (same rule in all five). Standard error: variance = se^2. Standard deviation: variance = sd^2 / n, only when the replicates member is supported (n independent titrations or experiments). Confidence interval: not converted, so no variance. No spread or no stated spread kind: no variance.

Weight rule (OWNER_DECISION 4): weight = sum of criterion values / number of applicable criteria. Supported counts its degree (1.0 if none). Conflicting counts 0. Unknown counts the unknown weight below. Not applicable is dropped. The WEIGHT_UNKNOWN (0.9) constant is the general default; each assay below has its own value.



### Part 2: binding assays alpha, radioligand, spa, pulldown, emsa

All numbers are copied from the files in `gene_annotation_episode/episodic_workflow/episode_support/literature/grading/experimental_activity_evidence/` as they are now (`literature_<assay>_converter.py`, `_grader.py`, `literature_row_contract.py`).

Common rules (the same in all five assays, from the code):
- A "degree" is 1.0 at the full-agreement value and 0 at the zero-agreement value. "Conflicting" means the paper's own number is at or past the zero value, so the criterion counts against. "Supported with degree 0" means weak, but not against.
- A sheet criterion takes the smallest degree of its members. Any conflicting member makes it conflicting; else any unknown member makes it unknown.
- Thin quote support multiplies a supported degree by 1.0 (direct), 0.7 (implied) or 0.3 (about something else).
- Quantitative effect strength: s = smoothstep(p) / (1 + r^2). Here p is the position of log10 of the constant between the noise end (0) and the strong end (1), clipped to [0, 1]. r = sqrt(variance) / constant (0 if no spread is stated). The log ratio is QUALITATIVE_LOG_RATIO times s. A quantitative effect never opposes; only a stated non-detection opposes.
- A stated spread becomes a variance only so: standard error -> se^2; standard deviation -> sd^2 / n (only when the replicates are stated independent); confidence interval -> not converted.
- The unknown weight is the weight an unstated criterion still counts. No unknown weight is used inside any degree.



### Part 3: SEC, dialysis, AUC, DSF, CETSA

Source: `literature_<assay>_converter.py` (the curves and constants), `literature_<assay>_criteria.py` and `literature_<assay>_grader.py` (what is read), and `literature_row_contract.py` (QUALITATIVE_LOG_RATIO, QUANTITATIVE_STRENGTH_ANCHORS, WEIGHT_UNKNOWN_BY_TYPE, WEIGHT_UNKNOWN_BY_CRITERION). All values were read from the files as they are now.

How the measured effect is scored for every assay below (`literature_direction.py`, function `strength`): the position p of log10 of the constant (in nM) between the noise end (p = 0) and the strong end (p = 1) is clipped to 0..1. The strength is s = (3p^2 - 2p^3) / (1 + r^2), with r = sqrt(variance) / constant (r = 0 when no variance). The log ratio is QUALITATIVE_LOG_RATIO[type] * s. When there is no constant, the statement (detected or not detected) gets the full QUALITATIVE_LOG_RATIO[type]. The variance comes from the paper's spread: a standard error gives se^2; a standard deviation gives sd^2 / n and only when the replicates criterion allows it; a confidence interval is not converted.

How a sheet criterion is combined (all five converters): any member conflicting gives conflicting; else any unknown gives unknown; else supported with the smallest degree of its members. A member that is not applicable is dropped. Quote support lowers a degree: direct 1.0, implied 0.7, about_something_else 0.3.

Every numeric constant in these five converters carries the tag EXPERT_REVIEW (an expert proposal), except the ones tagged FIXED_BY_DEFINITION. The phrase "owner to confirm" itself appears twice (see the lists below).


### Part 4: BRET, yeast two-hybrid, split reporter, PLA, proximity labelling

Read from the code as it is now (files in `.../literature/grading/experimental_activity_evidence/`: `literature_<assay>_converter.py`, `_criteria.py`, `_grader.py`, and `literature_row_contract.py`).

Rules shared by all five (from the converters):
- Every number below is an EXPERT_REVIEW constant (a proposal), unless the text says otherwise.
- A "degree" is the credit of one judged member, from 0 to 1. A sheet criterion that is supported carries the smallest degree of its members.
- "Linear" means a straight line between "full agreement" and "zero". At or beyond the zero end the member is conflicting (no degree), unless the row says "never conflicting".
- A count (replicates, cells, points) below its full-credit value gives partial credit and is never conflicting.
- Quote support: a member whose weakest quote is "implied" gets a degree of 0.7, one that is "about something else" gets 0.3 (multiplied with its own degree). Direct quotes change nothing. Support never changes a status.
- Yes/no facts follow one rule: any "no" is conflicting, else any "unknown" is unknown, else supported (a few exceptions are named below).
- Replicates, all five assays: independence stated yes gives degree min(1, sqrt(n / 3)); independence not stated gives unknown; independence stated no gives conflicting (from the grader).
- Direction and size of the result: a stated detection supports and a stated non-detection opposes, each with the type's QUALITATIVE_LOG_RATIO. A quantitative result (BRET and split reporter only) never opposes. Strength s = (3p^2 - 2p^3) / (1 + r^2), where p = (log10 KD - log10 noise_end) / (log10 strong_end - log10 noise_end) clipped to 0..1 (a smaller KD is stronger), and r = standard error of the KD divided by the KD. Then log ratio = QUALITATIVE_LOG_RATIO x s. If s is 0 the result is neutral.



## The 25 assay sections

### SPR (spr)

- Effect: the KD in nM, only when given as a point value. QUANTITATIVE_STRENGTH_ANCHORS spr: noise_end 1e6 nM, strong_end 1.0 nM. QUALITATIVE_LOG_RATIO spr: 1.5. The spread enters as the variance above (se^2 or sd^2/n), through r.
- Unknown weight: WEIGHT_UNKNOWN_BY_TYPE spr 0.90. No per-criterion override.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| binding_regime | concentration_series: number of concentrations | 5 or more | 1 if the paper says kinetic fit (or says nothing and kon and koff are stated); 2 if steady-state fit or no sign of kinetic fit | linear in count | No (low count only lowers the degree) | absolute count; zero end chosen by the paper's own statement of how KD was obtained |
| binding_regime | concentration_series: lowest concentration over KD (judged only when the series has a lower end distinct from its upper end) | at most 0.2 x KD | 1.0 x KD | linear in occupancy c/(c+KD) | Yes, at or beyond 1.0 x KD | the paper's own KD |
| binding_regime | concentration_series: highest concentration over KD | at least 5 x KD | 1.0 x KD | linear in occupancy c/(c+KD) | Yes, at or below 1.0 x KD | the paper's own KD |
| binding_regime | steady_state_vs_kinetic: fold gap of the two KDs (not applicable if single_estimate_method yes) | at most 2-fold | 10-fold | linear in log fold | Yes, at or beyond 10-fold | the paper's own two KDs |
| binding_parameter_definition | fit_model: chi-squared over Rmax | at most 0.10 | 0.30 | linear | Yes, at or beyond 0.30 | rule of thumb on the paper's own Rmax (not dimensionless) |
| binding_parameter_definition | fit_model: chi-squared over noise squared (only when the noise is stated; the weakest of the two counts) | at most 2 | 10 | linear in log ratio | Yes, at or beyond 10 | the paper's own baseline noise |
| binding_parameter_definition | kinetic_consistency: fold gap between koff/kon and KD, either way | at most 1.2-fold | 1.8-fold | linear in log fold | Yes, at or beyond 1.8-fold | the paper's own KD |
| calibration_applicability | rmax_consistency: observed Rmax over theoretical Rmax (low side) | at least 0.3 | 0.1 | linear | Yes, at or below 0.1 | the paper's own masses, immobilization level and stoichiometry |
| calibration_applicability | rmax_consistency: observed over theoretical (high side) | at most 1.2 | 2.0 | linear | Yes, at or beyond 2.0 | the same |
| sampling_basis | replicates: independent replicate count | 3 or more | none (1 run gives 0.58, 2 give 0.82) | min(1, sqrt(n / 3)) | No for a stated count. Independence stated no is conflicting. Independence not stated is unknown | absolute count |

- Facts that decide without a curve: reference_subtraction (reference surface or double referencing, either stated yes), mass_transport (checked_not_limited supported, checked_limited conflicting, not checked unknown), baseline_regeneration (baseline drift and regeneration both yes), immobilized_activity, independent surfaces (no is conflicting), and fit model 1:1 for a bivalent or oligomeric analyte (conflicting). A 1:1 model whose bivalence is not answered no is unknown. With no chi-squared, a stated model with residuals reported is supported.
- Owner to confirm: none marked in the code. Every researched value is marked EXPERT_REVIEW (proposal for the owner or an expert).
- Not collected:
  - whether the stoichiometry in the theoretical Rmax is stated or assumed, and the analyte class for the refractive-index increment: effect is small (the 1.2 slack covers it), and it would need a new curve with no researched ends.
  - the confidence-interval variance: needs its level and degrees of freedom.


### ITC (itc)

- Effect: the KD in nM, only when given as a point value. QUANTITATIVE_STRENGTH_ANCHORS itc: noise_end 1e5 nM, strong_end 10.0 nM. QUALITATIVE_LOG_RATIO itc: 1.5. The spread enters as the variance above; sd needs the replicate titrations to be independent.
- Unknown weight: WEIGHT_UNKNOWN_BY_TYPE itc 0.90. Override: binding_regime 0.85.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| binding_species | concentration_accuracy_and_active_fraction: fitted n over expected n (low side) | at least 0.7 | 0.3 | linear | Yes, at or below 0.3 | the paper's own expected n |
| binding_species | the same (high side) | at most 1.3 | 2.0 | linear | Yes, at or beyond 2.0 | the paper's own expected n |
| binding_regime | c_value_window: c = n x [cell] / KD (low side) | at least 1 | 0.1; or 0.01 when the titration reached its plateau (final ligand at least 10 x KD, shifted smoothly in log from final ligand = 1 x KD) | linear in log10(c) | Yes, at or beyond the zero end | the paper's own KD and cell concentration |
| binding_regime | c_value_window (high side) | at most 1000 | 10000 | linear in log10(c) | Yes, at or beyond 10000 | the same |
| binding_regime | injections_sufficient: injection count (not applicable for single-injection or continuous titration) | 15 or more | 3 | square root of (n - 3) / 12 | No (never conflicting) | absolute count |
| binding_regime | temperature_stated_and_controlled: temperature (low side) | at least 278.15 K (5 C) | 275.15 K (2 C) | linear | Yes, at or below 275.15 K | absolute (instrument limits) |
| binding_regime | temperature (high side) | at most 323.15 K (50 C) | 353.15 K (80 C) | linear | Yes, at or beyond 353.15 K | absolute (instrument limits) |
| binding_regime | temperature control answer | yes keeps the temperature degree; unknown makes it unknown; not_applicable drops it | none | none | no is conflicting (a fact) | none |
| binding_parameter_definition | thermodynamic_consistency: gap between dG from KD and dG from dH minus T dS | at most 2.0 kJ/mol | 10.0 kJ/mol | linear | Yes, at or beyond 10.0 kJ/mol | internal to the paper (absolute kJ/mol). Not applicable when dH is stated as corrected for buffer ionization |
| calibration_applicability | stoichiometry_consistency: when the paper states an expected n, only that n was fitted freely (supported, no degree; the size is judged once, in binding_species) | none | none | none | Fixed n is conflicting. Free fit not stated yes is unknown | the paper's expected n |
| calibration_applicability | stoichiometry_consistency: fitted n size (only when no expected n) | at least 0.4 | 0.2 | linear | Yes, at or below 0.2 | absolute |
| calibration_applicability | stoichiometry_consistency: distance of n from a multiple of 0.5 (only when no expected n) | at most 0.15 | 0.25 (no credit) | linear | No (ambiguity, not evidence against) | absolute |
| sampling_basis | replicate_titrations_independent: count | 3 or more | none (1 gives 0.58, 2 give 0.82) | min(1, sqrt(n / 3)) | No for a stated count. Independence no is conflicting. Not stated is unknown | absolute count |

- Facts that decide without a curve: heat_of_dilution_control (control performed, subtracted, baseline corrected, all yes; any no conflicts), buffer_matching (matched or stated procedure supported; stated not matched conflicting), concentrations_determined and active_fraction_determined (a no conflicts; unknown makes the n ratio unknown), fit_model_appropriate (model stated and residuals reported; one-set-of-sites model with heterogeneous sites yes is conflicting; heterogeneity not answered no is unknown), n fitted freely (fixed n conflicts), independent titrations.
- Owner to confirm: none marked in the code. Every researched value is marked EXPERT_REVIEW. Two values are cited from memory and not checked: the plateau shift of the low-c zero end (C_VALUE_ZERO_MIN_SATURATED 0.01, Turnbull and Daranas 2003) and the method sources in the docstring.
- Not collected: only the roles in the shared list above (no matrix recovery, no attribution fraction, no nuisance-condition response, no target prediction, no Student-t model).


### BLI (bli)

- Effect: the KD in nM, only when given as a point value. QUANTITATIVE_STRENGTH_ANCHORS bli: noise_end 1e5 nM, strong_end 1.0 nM. QUALITATIVE_LOG_RATIO bli: 1.4. The spread enters as the variance above; sd needs independent sensors.
- Unknown weight: WEIGHT_UNKNOWN_BY_TYPE bli 0.85. Override: binding_controls 0.80.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| calibration_applicability | loading_and_response: loading level of the partner | at most 2.0 nm | 4.0 nm | linear | Yes, at or beyond 4.0 nm | absolute. Both ends scale by (partner mass / 50 kDa) when the stated mass is above 50 kDa, never down |
| calibration_applicability | loading_and_response: maximum response | at least 0.05 nm | 0.01 nm | linear | Yes, at or below 0.01 nm | absolute; with a stated baseline noise N: zero at N, full at 5 x N |
| binding_regime | concentration_series: number of concentrations | 5 or more | 0 for a kinetic fit model (1:1, 2:1_bivalent_analyte, heterogeneous_ligand); 1 for steady_state, other or unstated | concave: 1 - ((5 - n) / (5 - zero))^2 (one concentration, kinetic: 0.36) | No | absolute count; the zero end follows the paper's fit model |
| binding_regime | concentration_series: lowest over KD, isotherm fit | at most 0.2 x KD | 1.0 x KD | linear in the ratio | Yes, at or beyond 1.0 x KD | the paper's own KD |
| binding_regime | concentration_series: lowest over KD, kinetic fit | at most 0.2 x KD | none: degree (1 + 0.2) / (1 + low) | free fraction | No | the paper's own KD |
| binding_regime | concentration_series: highest over KD | at least 5 x KD | 1.0 x KD | linear in the ratio | Yes, at or below 1.0 x KD | the paper's own KD |
| binding_regime | dissociation_window: decayed fraction 1 - exp(-koff x time) | at least 0.05 | 0.01 | linear | Yes, at or below 0.01 | absolute fraction |
| binding_regime | dissociation_window: decayed signal (fraction x maximum response), when the response is given | at least 0.05 nm | 0.01 nm | linear | Yes, at or below 0.01 nm | absolute; with stated noise N: zero at N, full at 5 x N |
| binding_regime | steady_state_vs_kinetic: fold gap | at most 2-fold | 10-fold | linear in log fold | Yes, at or beyond 10-fold | the paper's own two KDs |
| binding_parameter_definition | fit_model: fit R-squared | at least 0.95 | 0.80 | linear | Yes, at or below 0.80 | the paper's own data variance (instrument-software guidance) |
| binding_parameter_definition | kinetic_consistency: fold gap koff/kon vs KD, either way | at most 1.2-fold | 1.8-fold | linear in log fold | Yes, at or beyond 1.8-fold | the paper's own KD |
| sampling_basis | replicates: count on separate sensors | 3 or more | none (1 gives 0.58, 2 give 0.82) | min(1, sqrt(n / 3)) | No for a stated count. Independence no is conflicting. Not stated is unknown | absolute count |

- Facts that decide without a curve: reference_subtraction (reference sensor or buffer reference subtracted, either yes), nonspecific_binding_control, baseline_and_regeneration (both yes; single-use sensors are not applicable), avidity_and_mass_transport (either considered yes), immobilized_partner_active, loading step documented (no is conflicting; not yes makes loading_and_response unknown, as does a missing loading level or response), independent sensors, and a 1:1 model for a bivalent analyte (conflicting; bivalence not answered no is unknown).
- Owner to confirm: none marked in the code. Every researched value is marked EXPERT_REVIEW. SIGNAL_TO_NOISE_FULL (5) is derived from the fixed ends, no new number.
- Not collected:
  - chi-squared: the Octet X2 is software- and normalisation-specific, and the other binding assays' ends are not transferable. R-squared stays.
  - a koff-above-resolution check: would be a new criterion.
  - the analyte mass and a theoretical response from the loading: needs the stoichiometry and the active fraction of the loaded partner, which a passage rarely states, so a low response would be misread as bad quality.
  - the reference-sensor signal: it is subtracted before the noise is read, so the stated noise is the same fact and is stated more often.


### GCI (gci)

- Effect: the KD in nM, only when given as a point value. QUANTITATIVE_STRENGTH_ANCHORS gci: noise_end 1e6 nM, strong_end 1.0 nM. QUALITATIVE_LOG_RATIO gci: 1.4. The spread enters as the variance above; sd needs independent channels or chips.
- Unknown weight: WEIGHT_UNKNOWN_BY_TYPE gci 0.85. No per-criterion override.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| calibration_applicability | surface_level_and_response: immobilization level | at most 2000 pg/mm2 | 4000 pg/mm2 (degree 0) | linear | No (a dense small-molecule surface is normal) | absolute, a protein-protein proxy (masses not used for the level) |
| calibration_applicability | surface_level_and_response: maximum response | at least 1.0 pg/mm2 | 0.1 pg/mm2 | linear | Yes, at or below 0.1 pg/mm2 (even if the level is missing). Unknown when level or response is missing | absolute (assumed instrument noise about 0.1 pg/mm2) |
| calibration_applicability | rmax_consistency: observed over theoretical maximum response (low side) | at least 0.3 | 0.1 | linear | Yes, at or below 0.1 | the paper's own masses, level and stoichiometry |
| calibration_applicability | rmax_consistency (high side) | at most 1.2 | 2.0 | linear | Yes, at or beyond 2.0 | the same. No masses stated gives unknown |
| binding_regime | concentration_series: number of concentrations (not asked when waveRAPID is stated used) | 5 or more | 1 | concave: 1 - ((5 - n) / 4)^2 | No | absolute count |
| binding_regime | concentration_series: lowest over KD (not judged with waveRAPID) | at most 0.2 x KD | 1.0 x KD | linear in occupancy r/(1+r) | Yes, at or beyond 1.0 x KD | the paper's own KD |
| binding_regime | concentration_series: highest (or the one waveRAPID) concentration over KD | at least 5 x KD | 1.0 x KD | linear in occupancy r/(1+r) | Yes, at or below 1.0 x KD | the paper's own KD |
| binding_regime | dissociation_window: decayed fraction 1 - exp(-koff x time) | at least 0.05 | 0.01 | linear | Yes, at or below 0.01 | absolute fraction |
| binding_regime | dissociation_window: decayed signal (fraction x response in pg/mm2), when the response is given | at least 1.0 pg/mm2 | 0.1 pg/mm2 | linear | Yes, at or below 0.1 pg/mm2 | absolute |
| binding_regime | steady_state_vs_kinetic: fold gap | at most 2-fold | 10-fold | linear in log fold | Yes, at or beyond 10-fold | the paper's own two KDs |
| binding_parameter_definition | kinetic_consistency: fold gap koff/kon vs KD, either side | at most 1.2-fold | 1.8-fold | linear in log fold | Yes, at or beyond 1.8-fold | the paper's own KD |
| sampling_basis | replicates: count on separate channels or chips | 3 or more | none (1 gives 0.58, 2 give 0.82) | min(1, sqrt(n / 3)) | No for a stated count. Independence no is conflicting. Not stated is unknown | absolute count |

- Facts that decide without a curve: reference_subtraction (reference channel or double referencing, either yes), bulk_solvent_correction (not applicable in plain buffer), nonspecific_binding_control, baseline_and_regeneration (both yes; a surface used once is not applicable), mass_transport_checked, immobilized_partner_active, independent channels or chips, and fit_model (the model must be stated, with no number read: 1:1 for a bivalent analyte is conflicting, 1:1 with bivalence not answered no is unknown, any other stated model is supported).
- Owner to confirm: none marked in the code. Every researched value is marked EXPERT_REVIEW. Two values carry a stated caveat: IMMOBILIZATION_MAX 2000 and ZERO 4000 are a protein-protein default (the right level depends on the masses), and the 0.1 pg/mm2 noise is taken conservatively (the vendor claims lower).
- Not collected:
  - the stated baseline noise: papers almost never state it, so a relative scale would nearly always be unknown. The absolute 0.1 pg/mm2 stays.
  - a fit-quality number (chi-squared over Rmax or residuals): the Creoptix software reports none in the text of a paper, so the field would nearly always be unavailable. The global-fit count curve and the kinetic and steady-state agreement guard the fit.
  - a relative immobilization scale from the masses: the level stays on the absolute proxy.


### FP (fp)

- Effect: the reported constant in nM: the KD of a direct titration, or, when no KD is given, the Ki of a competition experiment. QUANTITATIVE_STRENGTH_ANCHORS fp: quantity "KD or Ki", noise_end 1e5 nM, strong_end 1.0 nM. QUALITATIVE_LOG_RATIO fp: 1.2. The spread enters as the variance above (kd_spread for a KD, ki_spread for a Ki); sd needs independent titrations.
- Unknown weight: WEIGHT_UNKNOWN_BY_TYPE fp 0.80. Overrides: binding_controls 0.75, binding_regime 0.75.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| calibration_applicability | assay_window: polarization window (bound minus free) | at least 70 mP | 20 mP | linear in 1 / window | Yes, at or below 20 mP | absolute (typical plate-reader noise) |
| calibration_applicability | assay_window over stated noise (only when the noise is stated; the weaker of the two counts) | at least 12 x noise (Z' about 0.5) | 3 x noise | linear in noise / window | Yes, at or below 3 x noise | the paper's own noise |
| binding_regime | tracer_concentration: tracer over KD (skipped when tight binding is handled) | at most 1 x KD | 10 x KD | linear in log of the depletion bias 1 + 0.5 x tracer/KD | Yes, at or beyond 10 x KD | the paper's own KD |
| binding_regime | concentration_series: number of concentrations | 8 or more | 3 (no credit) | linear in n - 3 | No | absolute count |
| binding_regime | concentration_series: lowest over the constant (the IC50 for a competitor series when given) | at most 0.2 x | 1.0 x | linear in occupancy x/(1+x) | Yes, at or beyond 1.0 x | the paper's own constant or IC50 |
| binding_regime | concentration_series: highest over the constant | at least 10 x | 1.0 x | linear in occupancy x/(1+x) | Yes, at or below 1.0 x | the paper's own constant or IC50 |
| binding_regime | equilibrium: incubation time (judged when equilibrium is not stated; needs the constant, else unknown) | full when the time covers 5 off-rate half-lives at the slow kon 1e5 /M/s, and is at least 5 min | at or below the time at the fast kon 1e7 /M/s | min(t / 5 min, log(t / T_FAST) / log(T_SLOW / T_FAST)), capped at 1 | Yes, at or below T_FAST | the paper's own constant (time = 5 x ln2 / (kon x constant)) |
| binding_regime | direct_vs_competition: fold gap between KD and Ki (not applicable if one estimate was made) | at most 3-fold | 10-fold | linear in log fold | Yes, at or beyond 10-fold | the paper's own two constants |
| binding_parameter_definition | intensity_change: total intensity change, direction not stated | at most 30 percent | 100 percent | linear in percent | Yes, at or beyond 100 percent | absolute |
| binding_parameter_definition | intensity_change, direction stated: bias of the apparent KD (increase p: 1 + p/100; fall p: 1/(1 - p/100)) | bias 1.3 (30 percent increase) | bias 2 (100 percent increase) | linear in log bias | Yes, at or beyond bias 2; a fall of 100 percent or more is conflicting | absolute |
| sampling_basis | replicates: independent titrations | 3 or more | none (1 gives 0.58, 2 give 0.82) | min(1, sqrt(n / 3)) | No for a stated count. Independence no is conflicting. Not yes is unknown | absolute count |

- Facts that decide without a curve: free_probe_baseline, specificity_control (nonspecific binding checked or unlabelled competitor displaces, either yes), surface_adsorption, equilibrium_reached (yes supported, no conflicting), intensity_change_checked (yes supported, no conflicting), tracer at or below KD when the numbers are missing (no is supported only if tight binding was handled), and fit_model (a competitive model for a direct titration, or a 1:1 or Hill model for a competition, is conflicting; otherwise a stated model is supported). Independent titrations no is conflicting.
- Owner to confirm (marked "owner to confirm" in the code):
  - SLOW_KON_PER_M_PER_S = 1.0e5: the slow end of association rates for a labelled tracer and a protein (about 1e5 to 1e7 per M per s; Schreiber, Haran and Zhou 2009, cited from memory). It sets T_SLOW = 100 x T_FAST, where the incubation degree reaches 1. Slower gated binding (1e3 to 1e4) is treated as rare. (The comment line also says DECISION A 2026-11-21: T_FAST kept, SLOW_KON new, 5 min floor now proportional.)
- Not collected:
  - Z' of the reads: derived from the same SDs as the noise, which is collected instead.
  - the protein and the tracer concentration of the competition plate: only needed to recompute a Ki from an IC50, which the sheet does not do. The paper's own Ki is the effect, judged by direct_vs_competition and tracer_concentration.

### FRET (fret)

- Effect: the KD of a direct titration in nM; if there is no KD, the Ki of a competition in nM. An EC50 or IC50 alone is not carried (it depends on the labelled concentrations). Strength anchors (QUANTITATIVE_STRENGTH_ANCHORS, quantity "KD or Ki"): noise end 1e5 nM, strong end 1.0 nM. QUALITATIVE_LOG_RATIO is 1.0. Spread: kd_spread for a KD, ki_spread for a Ki, as in the general rule above.
- Unknown weight: WEIGHT_UNKNOWN_BY_TYPE 0.75. Overrides: binding_controls 0.70, binding_parameter_definition 0.70, calibration_applicability 0.85.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| calibration_applicability (assay_window) | Highest over lowest acceptor/donor emission ratio (fold) | 2.0 (MIN_WINDOW_FOLD) | 1.0 | Linear | Yes, at the zero end | The paper's own free-state ratio |
| calibration_applicability (assay_window) | Z' factor, only if stated; the weaker of fold and Z' counts | 0.5 (Z_PRIME_MIN) | 0.0 (Z_PRIME_ZERO) | Linear | Yes | Absolute (it holds the paper's own scatter) |
| calibration_applicability (time_gating) | Delay after the flash, microseconds (time-resolved read only) | 50 (MIN_DELAY_US) | 5 (DELAY_ZERO_AGREEMENT_US) | Linear | Yes (not gated in effect) | Absolute (instrument and donor) |
| calibration_applicability (time_gating) | Integration window, microseconds, if stated; first scaled by 1000 / donor lifetime when the lanthanide is named (terbium 2000, europium 600; otherwise 1000) | 100 (MIN_INTEGRATION_US) | None; degree = (window / 100) ^ 0.5 | Square root | Never | The donor's own lifetime when the lanthanide is named |
| binding_regime (labelled_concentration), no tight-binding analysis | Labelled partner over KD (ratio r) | r = 1 (LABELLED_MAX_OVER_KD) | r = 10 (LABELLED_ZERO_AGREEMENT_OVER_KD) | Linear in ln(1 + r/2): bias 1.5 at full, 6 at zero | Yes | The paper's own KD |
| binding_regime (labelled_concentration), tight-binding analysis stated | Same ratio | r = 10 (TIGHT_BINDING_FULL_OVER_KD) | r = 100 (TIGHT_BINDING_ZERO_OVER_KD) | Linear in 1 / sqrt(r) between 10 and 100 | Yes | The paper's own KD |
| binding_regime (concentration_series) | Number of concentrations | 8 (MIN_CONCENTRATIONS) | 3 (SERIES_FIT_PARAMETERS); 4 for a Hill fit (HILL_FIT_PARAMETERS) | Linear in residual degrees of freedom | Never | Absolute (a count); zero end follows the paper's stated model |
| binding_regime (concentration_series) | Lowest concentration over the curve's midpoint | 0.2 (LOW_FACTOR) | 1.0 (LOW_ZERO_AGREEMENT_FACTOR) | Linear in occupancy x / (1 + x) | Yes | The curve's own midpoint: KD or EC50 for a direct titration; IC50 else Ki for a competition |
| binding_regime (concentration_series) | Highest concentration over the same midpoint | 10 (HIGH_FACTOR) | 1.0 (HIGH_ZERO_AGREEMENT_FACTOR) | Linear in occupancy x / (1 + x) | Yes | The same midpoint |
| binding_regime (equilibrium), koff stated | Incubation time against the paper's koff: fraction of approach reached, 1 - 2^(-t koff / ln 2) | 5 half-lives (APPROACH_FULL_HALF_LIVES) | 1 half-life (APPROACH_ZERO_HALF_LIVES) | Linear in the fraction reached | Yes | The paper's own koff |
| binding_regime (equilibrium), no koff | Incubation time t in minutes. T_FAST = 15 x 2 / constant_nM (MIN_INCUBATION_MIN x EQUILIBRATION_REFERENCE_NM) | T_SLOW = 10 x T_FAST (kon 1e6 down to 1e5) | T_FAST | Linear in ln(t / T_FAST) over ln(10) | Yes (t at or below T_FAST) | The paper's own KD or Ki; no constant gives unknown |
| binding_regime (direct_vs_competition) | Fold between the KD and the Ki | 3 (AGREEMENT_FACTOR) | 10 (AGREEMENT_ZERO_FACTOR) | Linear in ln(fold) | Yes | The paper's own two constants |
| sampling_basis (replicates) | Replicate count, independence stated yes | 3 (MIN_REPLICATES) | None; below 3 degree = sqrt(n / 3) | Square root | Never (independence not stated: unknown) | Absolute (a count) |

- Facts that decide without a curve (a stated yes or no): ratiometric_readout; spectral_crosstalk (crosstalk corrected, else both donor-only and acceptor-only controls); compound_interference; specificity_control (nonspecific-binding control or competitor displacement); labelling_scheme (labelling shown not to alter binding, else direct labelling); fit_model (a competition model for a direct titration, or a 1:1 or Hill model for a competition, conflicts); equilibrium_reached (when stated); labelled partner at or below KD (when no ratio can be formed); time gating with a fluorescent-protein or dye donor (conflicts); replicates stated not independent (conflicts).
- Owner to confirm in the code: Z_PRIME_MIN 0.5 (HTS limit for a robust assay); Z_PRIME_ZERO 0.0 (bands touch); DONOR_LIFETIME_US terbium 2000 and europium 600 (lanthanide lifetimes); REFERENCE_LIFETIME_US 1000 (lifetime MIN_INTEGRATION_US was set for); INTEGRATION_NOISE_EXPONENT 0.5 (counting noise); HILL_FIT_PARAMETERS 4 (Hill fit frees one more parameter); TIGHT_BINDING_FULL_OVER_KD 10 and TIGHT_BINDING_ZERO_OVER_KD 100 (curve rounding at equivalence); APPROACH_FULL_HALF_LIVES 5 and APPROACH_ZERO_HALF_LIVES 1 (approach to equilibrium); EQUILIBRATION_REFERENCE_NM 2 (constant at which 15 minutes is five half-lives); KON_SLOW_PER_M_S 1e5 (slow association, cited from memory). The docstring also marks as owner to confirm the change of the labelled-over-KD shape to the log of the depletion bias, and the change of the incubation cliff into a curve.
- Not collected, with the stated reason: ratio scatter as a raw SD (rarely stated, and a stated Z' already enters the window, so counting both would count the same scatter twice). Roles left null in the sheet: recovery (no matrix recovery measurement in FRET); attributed_signal and total_signal (a specificity control is not an attribution fraction); condition_test and condition_reference (no matched nuisance-condition response); assertion_prediction and alternative_prediction (belong to the target assertion, not the experiment); effect_degrees_of_freedom (no Student t model selected).


### MST (mst)

- Effect: the KD of a direct titration in nM; else the Ki of a competition in nM. An EC50 alone is not carried. Strength anchors (quantity "KD or Ki"): noise end 1e6 nM, strong end 1.0 nM. QUALITATIVE_LOG_RATIO is 1.2. Spread: as in the general rule above (kd_spread or ki_spread).
- Unknown weight: WEIGHT_UNKNOWN_BY_TYPE 0.75. Override: binding_controls 0.70.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| calibration_applicability (signal_amplitude), S/N stated | Signal-to-noise of the titration curve | 5 (MIN_SIGNAL_TO_NOISE) | 1 (SIGNAL_TO_NOISE_ZERO_AGREEMENT) | Linear | Yes | The paper's own scatter |
| calibration_applicability (signal_amplitude), no S/N but Fnorm amplitude and noise stated | Fnorm amplitude over Fnorm noise, judged on the S/N scale | 5 | 1 | Linear | Yes | The paper's own noise |
| calibration_applicability (signal_amplitude), neither S/N nor noise stated | Fnorm change, per mille | 5 (MIN_FNORM_AMPLITUDE_PERMILLE) | 1 (FNORM_AMPLITUDE_ZERO_AGREEMENT_PERMILLE) | Linear | Yes | Absolute (assumes about 1 per mille capillary noise) |
| binding_parameter_definition (readout_window) | F-hot time, seconds (thermophoresis readout only) | 1.0 (MIN_FHOT_S) | 0.0 (FHOT_ZERO_AGREEMENT_S) | Linear | Yes | Absolute (instrument timing) |
| binding_regime (labelled_concentration), no tight-binding analysis | Detected partner over KD (r) | r = 1 (LABELLED_MAX_OVER_KD) | r = 10 (LABELLED_ZERO_AGREEMENT_OVER_KD) | Linear in ln(1 + r/2) | Yes | The paper's own KD |
| binding_regime (labelled_concentration), tight binding handled | Same | Supported at any ratio, no degree | None | None | No | None |
| binding_regime (concentration_series) | Number of concentrations | 10 (MIN_CONCENTRATIONS) | 3 (CONCENTRATIONS_ZERO_AGREEMENT) | Linear in residual degrees of freedom | Never | Absolute (a count) |
| binding_regime (concentration_series) | Lowest concentration over the curve's midpoint (judged only when it differs from the highest) | 0.2 (LOW_FACTOR) | 1.0 (LOW_ZERO_AGREEMENT_FACTOR) | Linear in occupancy c / (c + midpoint) | Yes | The midpoint: the KD; KD + detected/2 when tight binding is handled; the EC50 for a Ki |
| binding_regime (concentration_series) | Highest concentration over the same midpoint | 10 (HIGH_FACTOR) | 1.0 (HIGH_ZERO_AGREEMENT_FACTOR) | Linear in occupancy | Yes | The same midpoint (needs the list; a count without a span is unknown) |
| binding_regime (equilibrium) | Incubation time t in minutes. T_FAST = 10 x 10 / constant_nM (MIN_INCUBATION_MIN x EQUILIBRATION_REFERENCE_NM); the constant is the KD, else the Ki | T_SLOW = 10 x T_FAST (kon 1e6 down to 1e5) | T_FAST | Linear in ln(t / T_FAST) over ln(10) | Yes (t at or below T_FAST) | The paper's own KD or Ki; none gives unknown |
| binding_regime (direct_vs_competition) | Fold between the KD and the Ki | 3 (AGREEMENT_FACTOR) | 10 (AGREEMENT_ZERO_FACTOR) | Linear in ln(fold) | Yes | The paper's own two constants |
| sampling_basis (replicates) | Replicate count, independence yes | 3 (MIN_REPLICATES) | Below 3: sqrt(n / 3) | Square root | Never (independence not stated: unknown) | Absolute (a count) |

- Facts that decide without a curve (a stated yes or no): initial_fluorescence (consistent, or check made); fluorescence_level (intensity in range); aggregation_adsorption (checked); specificity_control (nonspecific binding checked); labelling_scheme (labelling shown not to alter binding; label-free and unshown labels are unknown); fit_model (competition model for a direct titration, or 1:1 or Hill for a competition, conflicts); equilibrium_reached (when stated); detected partner at or below KD (when no ratio can be formed); readout of initial fluorescence (F-hot window then not applicable); replicates stated not independent (conflicts).
- Owner to confirm in the code: MIN_INCUBATION_MIN 10 (five half-lives of koff 0.01 per s with a margin); EQUILIBRATION_REFERENCE_NM 10 (the KD behind that 10 minutes); KON_FAST_PER_M_S 1e6 (fast protein association); KON_SLOW_PER_M_S 1e5 (slow association, from memory).
- Not collected, with the stated reason: a competition midpoint when no EC50 is stated (a paper reporting a Ki nearly always reports the IC50, and the probe KD is rarely stated; the cost is a wider-than-true span test for a Ki-alone paper); koff for the incubation scale (MST does not measure koff, a time course is a figure, and the equilibrium_reached fact carries the paper's claim). Roles left null in the sheet: recovery (no matrix recovery measurement); attributed_signal and total_signal (a specificity control is not an attribution fraction); condition_test and condition_reference (no matched nuisance response); assertion_prediction and alternative_prediction (belong to the target assertion); effect_degrees_of_freedom (no Student t model).


### Intrinsic tryptophan fluorescence quenching (trp_quenching)

- Effect: the reported KD in nM. A Stern-Volmer constant alone is not carried, and a KD fitted with the Stern-Volmer equation is not carried (the number is a quenching constant). Strength anchors (quantity "KD"): noise end 1e5 nM, strong end 10.0 nM. QUALITATIVE_LOG_RATIO is 1.0. Spread: kd_spread, as in the general rule above.
- Unknown weight: WEIGHT_UNKNOWN_BY_TYPE 0.70. Override: binding_controls 0.60.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| calibration_applicability (signal_amplitude) | Fluorescence change between free protein and saturated complex, percent | 5 (MIN_FLUORESCENCE_CHANGE_PERCENT) | 1 (FLUORESCENCE_CHANGE_ZERO_AGREEMENT_PERCENT) | Linear | Yes | Absolute (the paper's scatter is not collected) |
| binding_parameter_definition (excitation_selectivity) | Excitation wavelength, nm | 295 (TRP_SELECTIVE_EXCITATION_MIN_NM) | At or below 280 nm (TYROSINE_EXCITATION_NM) the degree stays at 0.58 (TRP_EXCITATION_SHARE_AT_280) | Linear from 295 down to 280 | Never | Absolute (residue absorption) |
| binding_controls (inner_filter), no correction stated, absorbance given | Ligand absorbance, AU | 0.05 (MAX_UNCORRECTED_ABSORBANCE) | 0.3 (ABSORBANCE_ZERO_AGREEMENT) | Linear | Yes | Absolute |
| binding_controls (inner_filter), as above and a quenching of stated size | Inner-filter loss 1 - 10^(-A/2), in percent, over the paper's stated change; the weaker of the two counts | 0.2 (ARTEFACT_FULL_OVER_CHANGE) | 1.0 (ARTEFACT_ZERO_OVER_CHANGE) | Linear in the share of the change | Yes (loss as large as the whole change) | The paper's own stated quenching (enhancement gets the absolute ramp only) |
| binding_controls (dilution), no correction stated, added volume given | Total volume added, percent of start | 5 (MAX_UNCORRECTED_DILUTION_PERCENT) | 50 (DILUTION_ZERO_AGREEMENT_PERCENT) | Linear | Yes | Absolute |
| binding_controls (dilution), as above and a quenching of stated size | Dilution loss v / (100 + v) over the paper's stated change; weaker counts | 0.2 | 1.0 | Linear in the share | Yes | The paper's own stated quenching |
| binding_regime (protein_concentration), no tight-binding analysis | Protein over KD (r) | r = 1 (PROTEIN_MAX_OVER_KD) | r = 10 (PROTEIN_ZERO_AGREEMENT_OVER_KD) | Linear in ln(1 + 0.5 r) | Yes | The paper's own KD |
| binding_regime (protein_concentration), tight binding handled | Same | Supported, no degree | None | None | No | None |
| binding_regime (concentration_series) | Number of concentrations | 8 (MIN_CONCENTRATIONS) | 2 (FIT_PARAMETERS); 3 for a Hill fit (HILL_FIT_PARAMETERS) | Linear in residual degrees of freedom | Never | Absolute; zero end follows the paper's stated model |
| binding_regime (concentration_series) | Lowest concentration over the midpoint (judged only when it differs from the highest; an unstated end is not judged) | 0.2 (LOW_FACTOR) | 1.0 (LOW_ZERO_AGREEMENT_FACTOR) | Linear in occupancy x / (1 + x) | Yes | The midpoint: the KD, or KD + 0.5 x protein with tight binding handled. No span at all: unknown |
| binding_regime (concentration_series) | Highest concentration over the same midpoint | 10 (HIGH_FACTOR) | 1.0 (HIGH_ZERO_AGREEMENT_FACTOR) | Linear in occupancy | Yes | The same midpoint |
| binding_regime (equilibrium) | Incubation t in minutes. T_FAST = 5 ln2 / (1e8 x KD) and T_SLOW = same at kon 1e5 (EQUILIBRATION_HALF_LIVES 5; FAST_KON 1e8, SLOW_KON 1e5), a 1000-fold gap. Degree = min(d_floor, d_kon) | d_kon = ln(t / T_FAST) / ln(T_SLOW / T_FAST), full at T_SLOW; d_floor = min(1, t / 2) (MIN_INCUBATION_MIN 2) | T_FAST (d_kon = 0) | Log share of association rates; floor proportional | Yes only at t at or below T_FAST; the floor alone never conflicts | The paper's own KD; no usable KD gives unknown |
| sampling_basis (replicates) | Replicate count, independence yes | 3 (MIN_REPLICATES) | Below 3: sqrt(n / 3) | Square root | Never (independence not stated: unknown) | Absolute (a count) |

- Facts that decide without a curve (a stated yes or no): inner_filter corrected (stated yes), or ligand absorbance negligible; dilution corrected (stated yes); buffer_blank_subtracted; ligand_only_control_measured; specificity_control (any one of a non-binding control, a tryptophan-analogue control, or signal localised to the binding site is enough); photobleaching_checked; signal_saturates; quenching_is_static (dynamic quenching conflicts); fit_model (a Stern-Volmer fit conflicts); equilibrium_reached (when stated); protein at or below KD (when no ratio can be formed); replicates stated not independent (conflicts).
- Owner to confirm in the code: ARTEFACT_FULL_OVER_CHANGE 0.2 (one fifth of the smallest fully usable change); HILL_FIT_PARAMETERS 3; MIN_INCUBATION_MIN 2 (mixing floor, now proportional); INCUBATION_ZERO_AGREEMENT_MIN 1 (decides nothing since 2026-11-21, kept for the owner); FAST_KON_PER_M_PER_S 1e8 (fast end for small ligands); SLOW_KON_PER_M_PER_S 1e5 (slow end, citation from memory).
- Not collected, with the stated reason: scatter or S/N of the readings (almost never stated in a quenching paper); ligand absorbance at each wavelength separately (rarely given; the larger value already gives a lower bound of the loss); whether the free-protein fluorescence was fitted (papers seldom state it and it moves the parameter count by one only); kon, koff or a time course (not reported in fluorescence-titration papers; equilibrium_reached carries the claim). Roles left null in the sheet: recovery; attributed_signal and total_signal; condition_test and condition_reference; assertion_prediction and alternative_prediction; effect_degrees_of_freedom (same reasons as above).


### FCS (fcs)

- Effect: the reported KD in nM (no Ki is carried). Strength anchors (quantity "KD"): noise end 1e5 nM, strong end 1.0 nM. QUALITATIVE_LOG_RATIO is 1.0. Spread: kd_spread, as in the general rule above.
- Unknown weight: WEIGHT_UNKNOWN_BY_TYPE 0.80. Override: calibration_applicability 0.75.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| calibration_applicability (diffusion_change) | Bound over free diffusion time (or free over bound coefficient) | 1.3 (MIN_DIFFUSION_RATIO); with a stated scatter of the free time the full value is 1 + 0.3 x max(scatter, 0.10) / 0.10 | 1.0 (DIFFUSION_RATIO_ZERO_AGREEMENT) | Linear | Yes | The paper's own scatter of the free diffusion time, when stated (it can only raise the requirement) |
| calibration_applicability (mass_consistency) | Fold between the reported diffusion ratio and the cube-root expectation from the mass ratio | Fold 1.5 (MASS_CONSISTENCY_FACTOR) | Fold 3.0 (MASS_CONSISTENCY_ZERO_FACTOR) | Linear in ln(fold), either direction | Yes | The paper's own mass ratio |
| calibration_applicability (acquisition) | Total acquisition time (one measurement x repeats), seconds | Needed time: 60 s (MIN_TOTAL_ACQUISITION_S) scaled by (free diffusion time / 1000 us) and by the squared ratio of signal factors m / (1 + m) at 10 kHz and 1000 us against the paper's own brightness and free time | None; degree = (total / needed) ^ 0.5 | Square root | Never (a short single measurement with repeats not given: unknown) | The paper's own brightness and free diffusion time (a missing one is taken at its reference) |
| binding_regime (saturation) | Largest fraction bound reached, percent | 80 (MIN_FRACTION_BOUND_MAXIMUM_PERCENT) | 20 (FRACTION_BOUND_ZERO_AGREEMENT_PERCENT) | Linear | Yes | Absolute (a fraction) |
| binding_regime (labelled_range), particle number | Particle number N in the confocal volume (stated, or concentration x volume x 0.6022) | Full from 0.1 to 10 (MIN_PARTICLE_NUMBER, MAX_PARTICLE_NUMBER) | 0.01 (PARTICLE_NUMBER_LOW_ZERO_AGREEMENT) and 100 (PARTICLE_NUMBER_HIGH_ZERO_AGREEMENT) | Linear in ln(N) outside the window | Yes | Absolute (instrument); the stated volume converts concentration to N |
| binding_regime (labelled_range), count rate | N x molecular brightness, kHz; the weaker of the two counts | 1000 (MAX_COUNT_RATE_KHZ) | 10000 (COUNT_RATE_ZERO_KHZ) | Linear in ln(rate) | Yes | Absolute (detector range) |
| binding_regime (labelled_range), no particle number and no volume | Labelled concentration, nM | Full from 0.3 to 30 (MIN_LABELLED_NM, MAX_LABELLED_NM) | 0.03 (LABELLED_LOW_ZERO_AGREEMENT_NM) and 300 (LABELLED_HIGH_ZERO_AGREEMENT_NM) | Linear in ln(concentration) | Yes | Absolute (assumes about half a femtolitre) |
| binding_regime (labelled_over_kd), no tight-binding analysis (or ratio at most 1) | Labelled partner over KD (r) | r = 1 (LABELLED_MAX_OVER_KD) | r = 10 (LABELLED_OVER_KD_ZERO_AGREEMENT) | Linear in ln(1 + 0.5 r) (DEPLETION_BIAS_SLOPE 0.5) | Yes | The paper's own KD |
| binding_regime (labelled_over_kd), tight-binding analysis and r above 1 | Same | Full up to r = 10 (TIGHT_BINDING_FULL_OVER_KD), no degree | r = 100 (TIGHT_BINDING_ZERO_OVER_KD) | Linear in r ^ -0.5 | Yes | The paper's own KD |
| binding_regime (concentration_series) | Number of concentrations | 8 (MIN_CONCENTRATIONS) | None; degree = (count / 8) ^ 0.5 (1 point 0.35, 3 points 0.61) | Square root | Never | Absolute (a count) |
| binding_regime (concentration_series) | Lowest concentration over the KD, as one-site percent bound low / (1 + low) | 0.2 x KD (LOW_FACTOR) | 1.0 x KD (LOW_ZERO_AGREEMENT_FACTOR) | Linear in occupancy | Yes | The paper's own KD (needs the list; none: unknown) |
| binding_regime (concentration_series) | Highest concentration over the KD, as one-site percent bound | 80 percent bound (about 4 x KD) | 20 percent bound (about 0.25 x KD) | Linear in percent bound | Yes | The paper's own KD |
| binding_regime (equilibrium) | Incubation t in minutes. T_FAST = 5 ln2 / (2 x 1e8 x KD) and T_SLOW at 1e5 (EQUILIBRATION_HALF_LIVES 5; KON_MAX_PER_M_S 1e8, KON_SLOW_PER_M_S 1e5); degree = min(d_floor, d_kon) | d_kon = ln(t / T_FAST) / ln(T_SLOW / T_FAST), full at T_SLOW; d_floor = min(1, t / 5) (MIN_INCUBATION_MIN 5) | T_FAST | Log share of rates; floor proportional | Yes only at t at or below T_FAST | The paper's own KD; no KD gives unknown |
| sampling_basis (replicates) | Replicate count, independence yes | 3 (MIN_REPLICATES) | Below 3: (n / 3) ^ 0.5 (REPLICATE_PRECISION_EXPONENT 0.5) | Square root | Never (independence not stated: unknown) | Absolute (a count) |

Where a degree is 1.0 or more, the converter attaches no degree (full credit).

- Facts that decide without a curve (a stated yes or no): confocal_volume_calibrated; triplet_state_modelled; brightness_change_accounted; crosstalk_corrected (an unstated fact is not applicable for a single-colour readout); background_corrected; aggregates_checked; photobleaching_or_saturation_checked; surface_adsorption_prevented; labelling_does_not_alter_binding; nonbinding_control_done; diffusion_model (a two-component fit with the free time fixed: yes supported, no conflicts; a one-component fit is supported when both reference values are given); fit_model (must be stated, with a reported KD); equilibrium_reached (when stated); labelled partner at or below KD (when no ratio can be formed); replicates stated not independent (conflicts). A brightness or cross-correlation readout makes diffusion_change, mass_consistency and diffusion_model not applicable.
- Owner to confirm in the code: PARTICLE_NUMBER_LOW_ZERO_AGREEMENT 0.01 and PARTICLE_NUMBER_HIGH_ZERO_AGREEMENT 100 (a decade beyond the window); MAX_COUNT_RATE_KHZ 1000 and COUNT_RATE_ZERO_KHZ 10000 (detector linear range, 50 ns dead time); LABELLED_LOW_ZERO_AGREEMENT_NM 0.03 and LABELLED_HIGH_ZERO_AGREEMENT_NM 300 (same decades in nM); TIGHT_BINDING_FULL_OVER_KD 10 and TIGHT_BINDING_ZERO_OVER_KD 100 (curve rounding against the noise of an amplitude fraction); DEPLETION_BIAS_SLOPE 0.5 (apparent KD about KD + labelled/2); SERIES_PRECISION_EXPONENT 0.5 (each point is its own estimate); KON_MAX_PER_M_S 1e8 (diffusion limit); KON_SLOW_PER_M_S 1e5 (slow association, from memory); EQUILIBRATION_HALF_LIVES 5 (97 percent of equilibrium); ACQUISITION_NOISE_EXPONENT 0.5 (noise falls as sqrt of time); REFERENCE_DIFFUSION_TIME_US 1000 and REFERENCE_BRIGHTNESS_KHZ 10 (the conditions behind 60 s). The docstring also leaves open that the mass-consistency curve is symmetric (aggregation, which makes the complex slower than expected, is worse than a faster-than-expected one), and that the unknown weight for FCS is for the owner to set.
- Not collected, with the stated reason: whether the bound diffusion time or the plateau was fixed (it would only move the plateau end, for which there is no researched shape; saturation and the span's high end already judge the plateau reach); a stated koff or time course (equilibrium titrations by FCS rarely report one, and the fastest-association time is the conservative bound already used). Roles left null in the sheet: recovery; attributed_signal and total_signal; condition_test and condition_reference; assertion_prediction and alternative_prediction; effect_degrees_of_freedom (same reasons as above).


### ELISA (elisa)

- Effect: the apparent KD of a saturation titration in nM; if there is no KD, the Ki of a competition in nM. An EC50 or IC50 alone is not carried (it depends on the coating, the detection and the competing ligand). Strength anchors (quantity "KD or Ki"): noise end 1e4 nM, strong end 1.0 nM. QUALITATIVE_LOG_RATIO is 0.8. Spread: kd_spread for a KD, ki_spread for a Ki, as in the general rule above (n counts independent experiments).
- Unknown weight: WEIGHT_UNKNOWN_BY_TYPE 0.70. Overrides: binding_controls 0.65, binding_regime 0.65.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| calibration_applicability (signal_window) | Plateau absorbance over background absorbance | 5 (MIN_SIGNAL_OVER_BACKGROUND) | 1 (SIGNAL_WINDOW_ZERO_AGREEMENT) | Linear in ln(ratio) | Yes | The paper's own blank wells |
| calibration_applicability (detector_range) | Plateau absorbance, OD (absorbance readouts only; chemiluminescence or fluorescence gives unknown) | 2.0 (MAX_LINEAR_OD), or the reader limit the paper states (cut to 4.0) | 4.0 (MAX_READABLE_OD) | Linear in 10 ^ OD | Yes (OD at or above 4) | The paper's own stated reader limit when given, else absolute |
| binding_regime (wash_dissociation) | koff x total wash time (when koff and wash duration are both stated) | Share retained 0.9 (WASH_RETAINED_FULL), koff x t = -ln 0.9 | Share retained 0.1 (WASH_RETAINED_ZERO), koff x t = -ln 0.1 | Linear in koff x t | Yes | The paper's own koff |
| binding_regime (equilibrium) | Incubation t in minutes. T_FAST = 30 x 1 / constant_nM (EQUILIBRATION_REFERENCE_MIN x EQUILIBRATION_REFERENCE_NM); the constant is the KD or Ki, else the EC50 or IC50 (rough). Degree = min(d_floor, d_kon) | d_kon = ln(t / T_FAST) / ln(100) (KON_FAST 1e6 down to KON_SLOW 1e4); d_floor = min(1, t / 30) (MIN_INCUBATION_MIN 30) | T_FAST | Log share of rates; floor proportional | Yes only at t at or below T_FAST | The paper's own constant; none gives unknown. The 30 minute floor is absolute (diffusion to the coated surface) |
| binding_regime (concentration_series) | Number of concentrations | 8 (MIN_CONCENTRATIONS) | Free parameters of the stated model: 1:1 gives 2, Hill 3, competitive_binding 3, four_parameter_logistic 4; other or unstated 4 (CONCENTRATIONS_ZERO_AGREEMENT) | Linear in residual degrees of freedom | Never | Absolute (a count); zero end follows the paper's stated model |
| binding_regime (concentration_series) | Lowest concentration over the reported constant | 0.2 (LOW_FACTOR) | 1.0 (LOW_ZERO_AGREEMENT_FACTOR) | Linear in occupancy x / (1 + x) | Yes | The paper's own constant (needs the list; none: unknown) |
| binding_regime (concentration_series) | Highest concentration over the reported constant | 10 (HIGH_FACTOR) | 1.0 (HIGH_ZERO_AGREEMENT_FACTOR) | Linear in occupancy | Yes | The paper's own constant |
| binding_regime (direct_vs_competition) | Fold between the KD and the Ki (reported, else Cheng-Prusoff Ki from the IC50, the displaced ligand's concentration and its KD); also the reported Ki against the Cheng-Prusoff Ki; the weaker of the folds counts | 3 (AGREEMENT_FACTOR) | 10 (AGREEMENT_ZERO_FACTOR) | Linear in ln(fold) | Yes | The paper's own constants |
| sampling_basis (replicates) | Independent experiments (separate plates or days; technical wells of one plate do not count), independence yes | 3 (MIN_REPLICATES) | Below 3: sqrt(n / 3) | Square root | Never (independence not stated: unknown) | Absolute (a count) |

- Facts that decide without a curve (a stated yes or no): saturation_reached; blank_subtracted; nonspecific_binding_checked; avidity_excluded; coated_protein_active; detection_does_not_interfere; signal_in_linear_range (when stated); wash_dissociation_considered (when stated); equilibrium_reached (when stated); fit_model (a competitive-binding model for a saturation titration conflicts, a one-site or Hill model for a competition conflicts, a four-parameter logistic fits both; none stated, or a model with no reported constant: unknown); single_estimate_method (makes direct_vs_competition not applicable); replicates stated not independent (conflicts).
- Owner to confirm in the code: KON_SLOW_PER_M_S 1e4 (new, slow end for coated-well partners, from memory). The docstring also marks the incubation as a curve (Decision A, 2026-11-21) with KON_FAST_PER_M_S 1e6, EQUILIBRATION_REFERENCE_NM 1 and EQUILIBRATION_REFERENCE_MIN 30 kept from the old rule.
- Not collected, with the stated reason: the blank wells' SD or CV (a Z' needs the plateau SD too and binding papers almost never state either; the fold over the blank gives the same judgement at the usual 10 percent CV); a chemiluminescent or fluorescent signal in its own unit and the reader's saturation level (instrument-specific, so no scale could be researched; stays unknown); well volume, shaking and coated amount (papers almost never give them); whether a baseline term was fitted (rarely stated, and it moves the zero end by one point); whether the stated plateau is raw or blank-subtracted (papers rarely say, and the error is below 0.1 OD); a dissociation time course or the detection step time. Roles left null in the sheet: recovery (an ELISA has no matrix recovery measurement); attributed_signal and total_signal (a specificity control is not an attribution fraction); condition_test and condition_reference (no matched nuisance response); assertion_prediction and alternative_prediction (belong to the target assertion); effect_degrees_of_freedom (no Student t model).

### AlphaScreen (alphascreen)

- Effect: the reported KD in nM (apparent KD of a titration), else the Ki of a competition. An EC50 or IC50 alone is not carried (a half-maximal concentration is not a dissociation constant). Strength anchors (QUANTITATIVE_STRENGTH_ANCHORS, "KD or Ki", nM): noise_end 1e4, strong_end 1.0. QUALITATIVE_LOG_RATIO 0.8, also the maximum for a quantitative result. Spread: a standard error enters as se^2; a standard deviation as sd^2 / n only if the replicates criterion is supported (independent experiments stated yes). Then r = sqrt(variance) / KD lowers s.
- Unknown weight: type 0.65. Overrides: binding_controls 0.60, binding_regime 0.60.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| calibration_applicability | signal over background (stated, or maximum / background) | 10 (MIN_SIGNAL_OVER_BACKGROUND) | 1 (SIGNAL_WINDOW_ZERO_AGREEMENT) | log of the ratio | yes, at 1 or below | the paper's own background wells |
| calibration_applicability | Z' factor | 0.5 (MIN_Z_PRIME) | 0 (Z_PRIME_ZERO_AGREEMENT) | linear in Z' | yes, at 0 or below | the paper's own controls |
| binding_regime | number of titrant concentrations | 8 (MIN_CONCENTRATIONS) | 4 (FIT_FREE_PARAMETERS), degree 0 | linear in (n - 4) / (8 - 4) | no, never; 4 or fewer is supported with degree 0 | absolute count |
| binding_regime | lowest concentration over the constant | 0.2 (LOW_FACTOR) | 1.0 (LOW_ZERO_AGREEMENT_FACTOR) | linear in one-site occupancy x/(1+x) | yes, at 1.0 or above | the paper's own KD or Ki |
| binding_regime | highest concentration over the constant | 10 (HIGH_FACTOR) | 1.0 (HIGH_ZERO_AGREEMENT_FACTOR) | linear in occupancy x/(1+x) | yes, at 1.0 or below | the paper's own KD or Ki |
| binding_regime | fixed partner concentration over the constant (only when "partner below KD" is not stated) | 1 (PARTNER_FULL_FACTOR) | 10 (PARTNER_ZERO_FACTOR) | log of the bias b = 1 + r/2 (b = 1.5 at 1, b = 6 at 10) | yes, at 10 or above | the paper's own constant |
| binding_regime | time the partners were together (incubation before beads plus step after beads, when stated) | T_SLOW = T_FAST x 1e6 / 1e5 | T_FAST = 30 min (MIN_INCUBATION_MIN) x 1 nM (EQUILIBRATION_REFERENCE_NM) / constant in nM | log of the time between T_FAST and T_SLOW | yes, at T_FAST or less | the paper's own constant. No constant: unknown |
| binding_regime | fold gap of titration KD and competition Ki | 3 (AGREEMENT_FACTOR) | 10 (AGREEMENT_ZERO_FACTOR) | log of the fold | yes, at 10 or above | one of the paper's constants over the other |
| sampling_basis | number of independent experiments | 3 (MIN_REPLICATES) | n = 0 | sqrt(n / 3), below 3 | no on the count (a stated "not independent" conflicts); independence not stated: unknown | absolute count |

- Facts that decide without a curve: specificity control (nonspecific_binding_checked), capture does not alter binding, avidity excluded, counter-screen done, light protected (all binding_controls); hook effect handled; signal in the linear range of the reader (calibration_applicability); a stated "partner below KD" and a stated "equilibrium reached" decide before the numbers above; fit model stated against the format (competition model for a saturation titration, or a direct model for a competition, conflicts); independent experiments stated no (conflicting); single estimate method (not applicable for the KD/Ki gap). For every fact, any "no" conflicts, else any "unknown" gives unknown.
- Owner to confirm in the code: SLOW_ASSOCIATION_RATE_PER_M_S = 1e5 (slow end of association without electrostatic steering; cited from memory). The related constants FAST_ASSOCIATION_RATE_PER_M_S 1e6 and EQUILIBRATION_REFERENCE_NM 1.0 are marked EXPERT_REVIEW only.
- Not collected: EC50 or IC50 alone as the effect (a half-maximal concentration is not a dissociation constant); a confidence interval as a variance (needs level and degrees of freedom); the background standard deviation (papers rarely give it; Z' carries the spread); bead capacity against the highest concentration (lot specific; the hook-effect fact stands); the number of free parameters per fit model (4 kept for all); the stated KD and Ki spreads widening the agreement test; matrix recovery, attribution fraction, matched nuisance condition, assertion prediction and Student-t model (not meaningful for this assay).


### Radioligand binding (radioligand)

- Effect: the KD of the radioligand from a saturation experiment, else the Ki of a competition, in nM. An IC50 alone is not carried. Anchors (KD or Ki, nM): noise_end 1e4, strong_end 0.1. QUALITATIVE_LOG_RATIO 1.4. Spread: as in the common rules; a standard deviation from a single experiment (SINGLE_EXPERIMENT = 1) is not turned into a variance.
- Unknown weight: type 0.85. Overrides: binding_controls 0.90, binding_regime 0.80, calibration_applicability 0.80.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| binding_controls | excess of the cold displacer over its own Kd (stated, or concentration / its Kd; over the radioligand KD only when the displacer is the unlabelled radioligand) | 100 (MIN_NONSPECIFIC_EXCESS) | 1 (NONSPECIFIC_EXCESS_ZERO_AGREEMENT) | log of the excess | yes, at 1 or below | the displacer's own Kd |
| binding_regime | incubation time, no off-rate stated | 30 min (MIN_INCUBATION_MIN) x max(1, 1 nM / KD in nM) (REFERENCE_KD_NM 1.0) | 0 minutes | first-order approach 1 - 0.5^h with h = 5 x t / needed time, over its value at 5 half-lives (HALF_LIVES_AT_MIN_INCUBATION 5) | no, never | the paper's own KD (30 min if no KD stated) |
| binding_regime | incubation time, off-rate (koff) stated | 5 half-lives of ln2 / koff | 0 minutes | same approach curve | no, never | the paper's own koff |
| binding_regime | number of radioligand concentrations | 8 (MIN_CONCENTRATIONS) | 2 (SATURATION_FIT_PARAMETERS), degree 0 | linear in (n - 2) / (8 - 2) | no, never | absolute count |
| binding_regime | lowest radioligand concentration over KD | 0.25 (LOW_FACTOR) | 1.0 (LOW_ZERO_AGREEMENT_FACTOR) | linear in occupancy x/(1+x) | yes, at 1.0 or above | the paper's own KD |
| binding_regime | highest radioligand concentration over KD | 5.0 (HIGH_FACTOR) | 1.0 (HIGH_ZERO_AGREEMENT_FACTOR) | linear in occupancy x/(1+x) | yes, at 1.0 or below | the paper's own KD |
| binding_regime | radioligand concentration over its KD in a competition | 1.0 (MAX_RADIOLIGAND_OVER_KD) | 10 (RADIOLIGAND_OVER_KD_ZERO_AGREEMENT) | linear in occupancy x/(1+x) | yes, at 10 or above | the paper's own KD |
| binding_parameter_definition | Hill slope | 0.8 to 1.2 (MIN_HILL, MAX_HILL) | 0.5 below (MIN_HILL_ZERO_AGREEMENT), 1.5 above (MAX_HILL_ZERO_AGREEMENT) | linear in the slope on each side | yes, at 0.5 or below, 1.5 or above | absolute slope |
| binding_parameter_definition | fold gap of reported Ki and Ki recomputed by Cheng-Prusoff from the paper's IC50, radioligand and KD | 1.5 (CHENG_PRUSOFF_FACTOR) | 5.0 (CHENG_PRUSOFF_ZERO_FACTOR) | log of the fold | yes, at 5 or above | the paper's own numbers |
| calibration_applicability | percent of added radioligand bound | 10 (MAX_PERCENT_BOUND) | 50 (PERCENT_BOUND_ZERO_AGREEMENT) | log of the KD bias 1 + f / (2 (1 - f)), f = percent / 100. A stated "depletion corrected" yes gives degree 1.0 | yes, at 50 or above | the paper's own total added |
| calibration_applicability | non-specific percent of total binding at the top concentration | 50 (MAX_NONSPECIFIC_FRACTION) | 90 (NONSPECIFIC_FRACTION_ZERO_AGREEMENT) | log of non-specific over specific, p / (100 - p) | yes, at 90 or above | the paper's own total |
| sampling_basis | number of independent experiments | 3 (MIN_REPLICATES) | n = 0 | sqrt(n / 3) | no on the count; independence not stated: unknown | absolute count |

- Facts that decide without a curve: non-specific binding determined; radioligand purity checked; filter binding checked (not applicable for scintillation proximity or centrifugation); wash dissociation considered (not applicable for scintillation proximity); non-linear fit used; Cheng-Prusoff applied with its own KD (a "no" conflicts); fit model (competition model for a saturation format conflicts); stated "equilibrium reached" (decides first); "ligand depletion checked" (used only if no percent bound is stated); independent experiments stated no (conflicting).
- Owner to confirm in the code: REFERENCE_KD_NM = 1.0 (the KD for which 30 minutes stands; the needed time grows as 1 / KD; new).
- Not collected: IC50 alone as the effect; confidence interval as variance; the radioligand concentration at which the percent bound holds (one overall figure is usual); receptor over KD (no volume basis for receptor amount); the concentration at which the non-specific percent is stated (top concentration is the worst case, so errors are lenient); an association time course; the competitor's own kinetics (hemi-equilibrium stays unseen); the standard error of the Hill slope (a wide error would not rescue a slope outside 0.8 to 1.2); matrix recovery, attribution fraction, matched nuisance condition, assertion prediction, Student-t model.


### Scintillation proximity assay (spa)

- Effect: the KD of the radioligand from a saturation experiment, else the Ki, in nM. IC50 alone is not carried. Anchors (KD or Ki, nM): noise_end 1e5, strong_end 0.1. QUALITATIVE_LOG_RATIO 1.2. Spread: a standard deviation becomes a variance only with independent experiments stated yes and at least SD_MIN_EXPERIMENTS = 2 experiments.
- Unknown weight: type 0.80. Override: calibration_applicability 0.75. (The converter docstring still says "0.9 kept"; the row contract value is 0.80.)

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| binding_controls | excess of the cold ligand over its own affinity (stated, or concentration / its KD or Ki; over the radioligand KD only if it is the unlabelled radioligand) | 100 (MIN_NONSPECIFIC_EXCESS) | 10 (NONSPECIFIC_EXCESS_ZERO_AGREEMENT) | linear in occupancy x/(1+x) | yes, at 10 or below | the cold ligand's own affinity |
| binding_controls | signal of the beads-and-radioligand control (no target), percent of total (percent stated; if not stated, the fact decides) | 20 (MAX_BEAD_ONLY_FRACTION) | 50 (BEAD_ONLY_ZERO_AGREEMENT) | linear in percent | yes, at 50 or above | the paper's own total signal |
| binding_regime | incubation time with a stated association half-time | 5 half-times (EQUILIBRIUM_HALF_TIMES) | 0 minutes | fraction of plateau 1 - 2^-r over its value at 5 | no, never | the paper's own association half-time |
| binding_regime | incubation time, no half-time stated | degree is the smaller of d_floor = min(1, t / 30 min) (MIN_INCUBATION_MIN) and d_kon = log(t / T_FAST) / log(KON_FAST / KON_SLOW); full when both are 1 | d_kon = 0 at t = T_FAST = 5 x ln2 / (KON_FAST_PER_M_S 1e8 x KD) | log of the time between T_FAST and T_SLOW (T_SLOW = T_FAST x 1e8 / 1e5); floor proportional | yes, at T_FAST or less. No KD: unknown | the paper's own KD |
| binding_regime | number of radioligand concentrations | 8 (MIN_CONCENTRATIONS) | 2 (SATURATION_FIT_PARAMETERS), degree 0 | linear in (n - 2) / (8 - 2) | no, never | absolute count |
| binding_regime | lowest concentration over KD | 0.25 (LOW_FACTOR) | 1.0 (LOW_ZERO_AGREEMENT_FACTOR) | linear in occupancy | yes, at 1.0 or above | the paper's own KD |
| binding_regime | highest concentration over KD | 5.0 (HIGH_FACTOR) | 1.0 (HIGH_ZERO_AGREEMENT_FACTOR) | linear in occupancy | yes, at 1.0 or below | the paper's own KD |
| binding_regime | radioligand over KD in a competition | 1.0 (MAX_RADIOLIGAND_OVER_KD) | 10 (RADIOLIGAND_OVER_KD_ZERO_AGREEMENT) | linear in occupancy x/(1+x) | yes, at 10 or above | the paper's own KD |
| binding_parameter_definition | Hill slope | 0.8 to 1.2 (MIN_HILL, MAX_HILL) | 0.5 below (HILL_LOW_ZERO_AGREEMENT), 2.0 above (HILL_HIGH_ZERO_AGREEMENT) | linear in the slope on each side | yes, at 0.5 or below, 2.0 or above | absolute slope |
| binding_parameter_definition | fold gap of reported Ki and Cheng-Prusoff Ki | 1.5 (CHENG_PRUSOFF_FACTOR) | 5.0 (CHENG_PRUSOFF_ZERO_AGREEMENT_FACTOR) | linear in the fold | yes, at 5 or above | the paper's own numbers |
| calibration_applicability | percent of radioligand bound (if not stated, the fact decides) | 10 (MAX_PERCENT_BOUND) | 30 (PERCENT_BOUND_ZERO_AGREEMENT) | linear in percent | yes, at 30 or above | the paper's own added amount |
| calibration_applicability | non-specific percent of total at the top concentration | 50 (MAX_NONSPECIFIC_FRACTION) | 80 (NONSPECIFIC_FRACTION_ZERO_AGREEMENT) | linear in percent | yes, at 80 or above | the paper's own total |
| sampling_basis | number of independent experiments | 3 (MIN_REPLICATES) | n = 0 | sqrt(n / 3) | no on the count; independence not stated: unknown | absolute count |

- Facts that decide without a curve: non-specific binding determined; non-proximity signal checked; radioligand purity checked; homogeneous no-wash format; quench interference checked; bead settling controlled; non-linear fit used; Cheng-Prusoff applied with its own KD (a "no" conflicts); fit model (competition model for a saturation format conflicts); stated "equilibrium reached" (decides first); independent experiments stated no (conflicting).
- Owner to confirm in the code: KON_FAST_PER_M_S = 1e8 (fastest plausible association rate; from memory); KON_SLOW_PER_M_S = 1e5 (slow association rate; from memory); the use of EQUILIBRIUM_HALF_TIMES = 5 in T_FAST and T_SLOW (t_eq = 5 x ln2 / (kon x KD); marked "owner to confirm").
- Not collected: IC50 alone as the effect; confidence interval as variance; the well volume (receptor over KD route needs several unit-matched fields); the concentration at which the non-specific or bead-only percent was read; the standard error of the Hill slope; a settling-time curve (settling is bead and plate specific; only the fact and the stated settling time stay); matrix recovery, attribution fraction, matched nuisance condition, assertion prediction, Student-t model.


### Pull-down / co-IP (pulldown)

- Effect: none quantitative. A pull-down reports no binding constant, so no effect and no variance are filled (QUANTITATIVE_STRENGTH_ANCHORS has no pulldown entry). The experiment gives a qualitative statement: interaction detected (supports), interaction not detected (opposes), or not stated. The log ratio is QUALITATIVE_LOG_RATIO 0.7 for either. The stated fold enrichment is kept beside the statement (not put in the effect) and is judged as a criterion. Its stated spread (SEM, or SD) limits the enrichment degree, not the effect.
- Unknown weight: type 0.70. Overrides: binding_controls 0.55, binding_species 0.60, sampling_basis 0.80. (The converter docstring still speaks of "about 0.5" and a pending 0.9; the row contract values are those above.)

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| binding_regime | NaCl in the wash buffer | 150 mM (MIN_WASH_NACL_MM) | 50 mM (WASH_NACL_ZERO_AGREEMENT_MM), degree 0 | linear in sqrt(salt) | no, never | absolute (ionic screening) |
| binding_regime | detergent in the wash buffer (percent); the wash degree is the weaker of salt and detergent | 0.05 percent (MIN_WASH_DETERGENT_PERCENT) | 0 percent (WASH_DETERGENT_ZERO_AGREEMENT_PERCENT), degree 0 | linear in percent | no, never | absolute |
| binding_regime | number of washes | 3 (MIN_WASHES) | 0 (WASH_COUNT_ZERO_AGREEMENT) | linear in the count | yes, at 0 washes stated | absolute count |
| binding_regime | incubation time of bait with prey | 30 min (MIN_INCUBATION_MIN). Full at any time if the prey is stated detected | 5 min (INCUBATION_ZERO_AGREEMENT_MIN), degree 0 | linear in log of the time | no, never | absolute |
| binding_parameter_definition | fold enrichment over the control | 3 (MIN_FOLD_ENRICHMENT) | 1 (ENRICHMENT_ZERO_AGREEMENT_FOLD) | linear in log of the fold; also limited by (fold - 1) / SE / 2 when a spread is stated (SPREAD_Z_FULL 2; SEM as stated, SD / sqrt(count) when the count is stated, else SD), the weaker of the two counts | yes, at 1 or below | the paper's own control signal and its own spread |
| sampling_basis | number of independent experiments | 3 (MIN_REPLICATES) | n = 0 | sqrt(n / 3) | no on the count; independence not stated: unknown | absolute count |

- Facts that decide without a curve: prey detected in eluate (sets the statement and the direction); negative control (prey found in the negative control conflicts; negative control not done conflicts; prey absent supports); positive control (only matters for a prey not detected; "no" then conflicts; a detected prey is full); bait-minus control done; input lane shown; reciprocal done; competition disrupts interaction; survives nuclease; specificity validated; endogenous expression levels; direct interaction shown (yes supports, otherwise unknown); quantification with normalization; independent experiments stated no (conflicting).
- Owner to confirm in the code: no value is marked "owner to confirm". (All are marked EXPERT_REVIEW.)
- Not collected: any binding constant, KD, fold or percent of input as an effect (not on the nM scale and cannot be pooled); KCl or the buffer's own ionic strength (only NaCl is recorded); the detergent identity and its critical micelle concentration (percent kept absolute); the bead-bed volume over the wash volume; the association rate of the complex; matrix recovery, attribution fraction, matched nuisance condition, assertion prediction, Student-t model.


### EMSA gel shift (emsa)

- Effect: two cases. (1) With an apparent KD (a titration): the KD in nM; anchors ("apparent KD", nM) noise_end 1e4, strong_end 1.0; QUALITATIVE_LOG_RATIO 0.7 is the maximum. A standard error enters as se^2; a standard deviation as sd^2 / n, only with independent experiments stated yes and at least MIN_EXPERIMENTS_FOR_A_SPREAD = 2 gels. (2) With no KD (a shift is shown): no effect or variance; the statement (shifted band stated, no shift stated, not stated) gives +/- 0.7. The stated percent shifted at the highest protein is kept but not put in the effect.
- Unknown weight: type 0.75. Override: binding_controls 0.60.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| binding_controls | competitor excess in a specific competition where the shift was NOT abolished (a "no") | competition judged only by the stated "no": competitor at least 50x probe (MIN_COMPETITOR_EXCESS), or, when protein and probe are stated, competitor / protein at least 5 (MIN_COMPETITOR_OVER_PROTEIN) | below those: unknown (not a test) | step, no degree | yes, a "no" with a large enough competitor | the probe, or the protein of the competition lane |
| binding_regime | incubation time (stated KD, no stated time course) | T_SLOW = 5 x ln2 / (2 x 1e6 x KD) (SLOW_ASSOCIATION_RATE_PER_M_PER_S) | T_FAST = 5 x ln2 / (2 x 1e8 x KD) (FAST_ASSOCIATION_RATE_PER_M_PER_S), EQUILIBRATION_HALF_LIVES = 5 | log of the time between T_FAST and T_SLOW | yes, at T_FAST or less. No KD: unknown | the paper's own KD |
| binding_regime | probe concentration over KD (a quadratic fit that solves probe depletion: supported, no degree) | 1 (MAX_PROBE_OVER_KD) | 10 (PROBE_OVER_KD_ZERO_AGREEMENT) | log of the bias b = 1 + r/2 | yes, at 10 or above | the paper's own KD |
| binding_regime | lowest protein concentration over KD | 0.25 (LOW_FACTOR) | 1 (LOW_ZERO_AGREEMENT_FACTOR) | linear in occupancy x/(1+x) | yes, at 1 or above | the paper's own KD |
| binding_regime | highest protein concentration over KD | 5 (HIGH_FACTOR) | 1 (HIGH_ZERO_AGREEMENT_FACTOR) | linear in occupancy x/(1+x) | yes, at 1 or below | the paper's own KD |
| binding_regime | number of protein lanes (needs a KD) | 6 (MIN_TITRATION_POINTS) | 2 or fewer (TITRATION_FIT_PARAMETERS 2): degree 0.2 | (n - 2 + 1) / (6 - 2 + 1): 3 lanes 0.4, 4 0.6, 5 0.8 | no, never | absolute count |
| binding_parameter_definition | number of shifted species (needs a KD) | 1 (MAX_SHIFTED_SPECIES) | more than 1 with a one-site fit (one_site, quadratic) | step, no degree | yes (several species with a one-site model); not applicable with no KD | absolute count against the model |
| binding_parameter_definition | probe over KD for a stated one-site fit | 1 | 10 | log of the bias b = 1 + r/2 (same as probe_concentration) | yes, at 10 or above | the paper's own KD |
| calibration_applicability | percent of probe shifted at the highest protein (percent of the fitted plateau when stated, capped at 100) | 80 (MIN_FRACTION_SHIFTED_HIGHEST) | 50 (FRACTION_SHIFTED_ZERO_AGREEMENT) | linear in percent | yes, at 50 or below | 100 percent of the probe, or the paper's own fitted plateau |
| sampling_basis | number of independent gels | 3 (MIN_REPLICATES) | n = 0 | sqrt(n / 3) | no on the count; independence not stated: unknown | absolute count |

- Facts that decide without a curve: shift detected; shift not abolished by a non-specific competitor; mutant probe does not shift; probe-alone lane shown; non-specific protein control done; protein identity (supershift or purified protein: any yes supports; no conflicts); free probe quantified; complex survives the gel run; the stated "equilibrium reached" (decides first); the stated "probe at or below KD" and "protein range brackets KD" (used when the numbers are missing, and not applicable with no KD); fit model stated (supported); independent experiments stated no (conflicting).
- Owner to confirm in the code: SLOW_ASSOCIATION_RATE_PER_M_PER_S = 1e6 (slow end of association for a protein on a DNA site; cited from memory; two decades below the fast end).
- Not collected: an association rate or time course of equilibration (EMSA papers almost never give one); the incubation temperature (it changes kon and koff by much less than the assumed range of kon); the plateau shifted fraction as an effect and the shifted fraction at the top as an effect (not on the nM scale); confidence interval as variance; matrix recovery, attribution fraction, matched nuisance condition, assertion prediction, Student-t model.

### SEC (sec)

- Effect: an apparent KD from peak areas, in nM (key sec_kd), when a titration gives one. With no KD, no effect is filled and the statement is the complex peak seen or not seen (QUALITATIVE_LOG_RATIO sec = 0.8). Strength anchors: noise_end = 1e4 nM, strong_end = 10 nM. Spread: a standard error is squared; a standard deviation becomes sd^2 / n only when the replicates criterion is supported and n is at least 2 (MIN_COUNT_FOR_A_SPREAD = 2). The strength is divided by 1 + r^2.
- Unknown weight: WEIGHT_UNKNOWN_BY_TYPE sec = 0.75. Overrides: binding_regime = 0.60, calibration_applicability = 0.90.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| binding_parameter_definition (elution_shift) | Shift of the complex peak below the earlier-eluting component: the stated shift, else that component's elution volume minus the complex's (mL) | MIN_ELUTION_SHIFT_ML 0.3 mL x Ve / REFERENCE_ELUTION_VOLUME_ML 13.0 (Ve = stated elution volume of the earlier component); if Ve is not stated but the column volume is: 0.3 x column volume / REFERENCE_COLUMN_VOLUME_ML 24.0; if neither: 0.3 mL | ELUTION_SHIFT_ZERO_ML = 0.0 mL | Smoothstep x^2(3 - 2x) | Yes, at a shift of 0 or less | The paper's own component control (its elution volume) or its column volume |
| binding_parameter_definition (mals_mass) | MALS mass of the complex peak against the theoretical mass: deviation % = (measured - theoretical) / theoretical x 100 | Absolute deviation at most MASS_FULL_AGREEMENT_PERCENT 10.0 | MASS_ZERO_AGREEMENT_PERCENT 50.0; when the smaller component's own MALS mass is stated: that mass in percent of the complex, kept between MASS_RESOLVABLE_PERCENT 20.0 and 50.0 | Linear | Yes, at the zero end or beyond | The paper's own theoretical mass (and the smaller partner's mass when stated) |
| binding_parameter_definition (stoichiometry) | Stated molar ratio, only when an apparent KD is reported; fold = max(r, 1/r) | Fold at most 1 + STOICHIOMETRY_TOLERANCE 0.1 = 1.1 | STOICHIOMETRY_ZERO_FOLD 2.0 | Linear in the share of 1:1 complexes, (2.0 - fold) / (2.0 - 1.1) | Yes, at fold 2.0 or more | Absolute (1:1) |
| binding_controls (resin_interaction) | Running-buffer monovalent salt (mM), used only when the yes/no fact is not stated | MIN_SALT_MM 100.0 | SALT_ZERO_MM 50.0 | Linear in the square root of the salt | Yes, at 50 mM or less | Absolute |
| binding_controls (monodispersity) | Mw/Mn polydispersity of the peak, when stated | MAX_POLYDISPERSITY 1.05 | POLYDISPERSITY_ZERO 1.125 (a peak of equal masses of a species and its dimer; SECOND_SPECIES_MASS_MULTIPLE = 2.0) | Linear in the dimer's share of the mass, which is derived from Mw/Mn | Yes, at 1.125 or more | Absolute (ratio of the peak's own averages) |
| binding_regime (complex_stable_on_column) | Injected concentration over the apparent KD; injected volume and column volume when stated | Credit 1.0 from MIN_LOAD_OVER_KD 10.0 at COLUMN_DILUTION_FOLD 10.0 | No zero end; the credit goes toward 0 only as the load goes to 0 | Fraction of 1:1 complex that survives the dilution, relative to its value at load/KD 10 and dilution 10. With the injected volume stated, dilution = sqrt(peak^2 + sample^2) / sample, peak = PEAK_VOLUME_FRACTION_OF_COLUMN 0.10 x column volume (24 mL if not stated) | Never | The paper's own KD, and its own volumes |
| sampling_basis (replicates) | Count of independent experiments, and whether they are independent | MIN_REPLICATES 3 | None | sqrt(min(n, 3) / 3): 1 gives 0.58, 2 gives 0.82. Independence not stated gives unknown | Only when independence is stated "no" (the grader's rule) | Absolute count |

- Facts that decide without a curve (a stated yes or no): complex_peak_observed (complex_peak_detected), components_alone, complex_composition (SDS-PAGE of the peak), titration_depletion, column_calibration (calibration_applicability), single_component_control. The same yes/no facts also decide mals_mass, resin_interaction, complex_stable_on_column and monodispersity when the number is not stated.
- Values marked "owner to confirm" in the code:
  - STOICHIOMETRY_ZERO_FOLD = 2.0: SEC keeps its 2:1 zero end (population reading); AUC uses 1.5. The code says "the difference is for the owner to settle".
  - No other SEC value carries that phrase. All others are EXPERT_REVIEW proposals.
- Not collected, with the stated reason:
  - Matrix recovery: an SEC has no matrix recovery measurement.
  - Attributed signal and total signal: a complex peak is not an attribution fraction.
  - Condition test and condition reference: no matched nuisance-condition response in an SEC record.
  - Assertion prediction and alternative prediction: the prediction belongs to the target assertion, not the experiment.
  - Effect degrees of freedom: no Student t model selected.
  - Effect and variance when no KD is reported: a qualitative assay reports no binding constant.
  - Buffer pH, the protein's pI and the buffer's own ions (resin interaction): judged not worth collecting; the pI is not in a passage and the buffer ions add little to 100 to 150 mM salt.
  - Off-rate and run time (complex stability): rarely stated for an SEC; a slowly dissociating complex survives regardless.
  - Not asked by the method: elution volume of the later-eluting component alone, mass of the larger component alone, flow rate, temperature, incubation, column type, detector, and the statement that only this method was used.

### Equilibrium dialysis and ultrafiltration (dialysis)

- Effect: the KD in nM (key dialysis_kd), else the Ki in nM (dialysis_ki). A Bmax is never the effect. With neither, no effect is filled; the statement comes from the percent bound (detected, or not detected below MIN_PERCENT_BOUND). QUALITATIVE_LOG_RATIO dialysis = 1.2. Strength anchors: noise_end = 1e5 nM, strong_end = 10 nM. Spread: a standard error is squared; a standard deviation becomes sd^2 / n only when the replicates degree is 1.0 (at least 3 independent experiments); a confidence interval is not converted. The strength is divided by 1 + r^2.
- Unknown weight: WEIGHT_UNKNOWN_BY_TYPE dialysis = 0.85. Override: calibration_applicability = 0.80.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| binding_parameter_definition (binding_observed) | Percent bound (stated, or 100 minus percent unbound, or fraction x 100); its SD when stated | QUANTIFIED_PERCENT_BOUND 15.0, or LOQ_SIGMAS 10.0 x SD if larger | MIN_PERCENT_BOUND 5.0, or LOD_SIGMAS 3.3 x SD if larger (the degree is 0 at this point) | Linear. The statement flips at 5.0 | Yes, below 5.0 percent (statement "not detected") | The paper's own SD of the percent bound, floored at 5 and 15 |
| binding_regime (equilibrium) | Time to equilibrium in hours (when the yes/no fact is not stated) | MIN_EQUILIBRATION_H 4.0 | EQUILIBRATION_ZERO_AGREEMENT_H 1.0 | Exponential approach, 1 - 0.5^(5 t / 4), scaled to 0 at 1 h and 1 at 4 h (HALF_LIVES_AT_MIN_EQUILIBRATION 5.0) | Yes, at 1 h or less | Absolute. Not applicable for ultrafiltration or ultracentrifugation when the fact is not stated |
| calibration_applicability (recovery) | Recovery, percent of total ligand in both chambers | 80.0 (MIN_RECOVERY_PERCENT) to 120.0 (MAX_RECOVERY_PERCENT) | 50.0 (RECOVERY_ZERO_AGREEMENT_PERCENT) low side; 150.0 (RECOVERY_HIGH_ZERO_AGREEMENT_PERCENT) high side | Linear on each side | Yes, at 50 or less, or 150 or more | The paper's own total ligand |
| binding_controls (device_adsorption) | Adsorption to membrane and device, percent; whether it was corrected; percent unbound; separation method | MAX_ADSORPTION_PERCENT 15.0 | ADSORPTION_ZERO_AGREEMENT_PERCENT 40.0 | Linear. If corrected, the stated adsorption is first multiplied by ADSORPTION_CORRECTION_RESIDUAL 0.15. For ultrafiltration the weaker of this and a second ramp on the share = adsorption x unbound / 100 / (100 - unbound): full at DEVICE_SHARE_OF_BOUND_FULL 0.2, zero at DEVICE_SHARE_OF_BOUND_ZERO 1.0 | Yes, at 40 percent or more, or share 1.0 or more | Adsorption is absolute; the share is relative to the paper's own percent bound |
| binding_regime (volume_shift, stated shift) | Volume shift of the protein chamber, percent | MAX_VOLUME_SHIFT_PERCENT 10.0 | VOLUME_SHIFT_ZERO_AGREEMENT_PERCENT 30.0 | Linear | Yes, at 30 percent or more | The paper's own chamber volume |
| binding_regime (volume_shift, salt, when no shift is stated) | Salt (mM), protein concentration | Salt at least MIN_SALT_MM 100.0 x protein / PLASMA_PROTEIN_NM 600000.0 (protein in nM; plasma level assumed if protein not stated) | No zero; unknown when salt is 0 or less (SALT_ZERO_AGREEMENT_MM 0.0) | Degree = salt / that full salt | Never | Scaled to the paper's own protein concentration |
| binding_regime (ligand_depletion) | Bound ligand over protein concentration | MAX_BOUND_OVER_PROTEIN 1.0 | BOUND_OVER_PROTEIN_ZERO_AGREEMENT 3.0 | Linear. Both limits are multiplied by the paper's own sites per protein (from Bmax) when that is above 1 | Yes, at the zero end or more | The paper's own sites per protein |
| binding_regime (protein_level) | Protein concentration over KD (only when a KD is stated) | MIN_PROTEIN_OVER_KD 0.2 | PROTEIN_OVER_KD_ZERO_AGREEMENT 0.05 | Linear | Yes, at 0.05 or less | The paper's own KD |
| calibration_applicability (free_fraction_measurable) | Percent unbound; free concentration over the detector's stated LLOQ | Percent unbound 1.0 (MIN_PERCENT_UNBOUND); free over LLOQ 3.0 (FREE_OVER_LLOQ_FULL) | Percent unbound 0.0 (FREE_FRACTION_ZERO_AGREEMENT_PERCENT); free over LLOQ 1.0 (FREE_OVER_LLOQ_ZERO) | Linear; the weaker of the two counts | Yes, at the zero ends or below | Percent unbound is absolute; free over LLOQ is relative to the paper's own detector limit |
| binding_regime (concentration_series: count) | Number of ligand concentrations | MIN_CONCENTRATIONS 6 | FIT_PARAMETERS 2 (degree 0 at 2 or fewer) | Linear in (n - 2) / (6 - 2) | Never from the count | Absolute count |
| binding_regime (concentration_series: low end) | Lowest total ligand over KD, judged as occupancy x / (1 + x) | LOW_FACTOR 0.5 (occupancy 1/3) | LOW_ZERO_AGREEMENT_FACTOR 1.0 (occupancy 1/2) | Linear in occupancy | Yes, at lowest >= 1.0 x KD | The paper's own KD |
| binding_regime (concentration_series: high end) | Highest total ligand over KD, as occupancy | HIGH_FACTOR 4.0 (occupancy 4/5) | HIGH_ZERO_AGREEMENT_FACTOR 1.0 (occupancy 1/2) | Linear in occupancy | Yes, at highest <= 1.0 x KD | The paper's own KD |
| sampling_basis (replicates) | Count of independent experiments, and independence | MIN_REPLICATES 3 | None | sqrt(n / 3), capped at 1: 1 gives 0.58, 2 gives 0.82. Independence not stated gives unknown | Only when independence is stated "no" | Absolute count |

The concentration_series degree is the smallest of the count, the low end and the high end. When no span can be read it is unknown.

- Facts that decide without a curve (a stated yes or no): buffer_only_control, protein_retained, ligand_stability (binding_controls); free_measured_directly (calibration_applicability); fit_model (supported when a model is stated and a constant is reported; unknown otherwise). The yes/no facts for binding_observed, equilibrium, recovery, device_adsorption, volume_shift, protein_level also decide when their numbers are not stated.
- Values marked "owner to confirm" in the code:
  - Decision C (2026-11-21), concentration_series span: both ends are judged linearly in the occupancy x / (1 + x) instead of in x, between the same ends (LOW_FACTOR 0.5 to 1.0, HIGH_FACTOR 4.0 to 1.0). No new constants. Reason: this is the occupancy scale the other assays use; no dialysis-specific reason for linear in x was found.
- Not collected, with the stated reason:
  - Matrix recovery in the sheet sense: a dialysis recovery is a mass balance, not a matrix recovery.
  - Attributed signal and total signal: a bound fraction is not an attribution fraction.
  - Condition test and condition reference: no matched nuisance-condition response in a dialysis record.
  - Assertion prediction and alternative prediction: belong to the target assertion, not the experiment.
  - Effect degrees of freedom: no Student t model selected.
  - Effect and variance when no KD or Ki: a qualitative assay reports no binding constant.
  - Protein net charge (pI with buffer pH) and the buffer's own ionic strength for the Donnan scale: a methods paragraph almost never states them; the plasma-albumin charge is assumed.
  - Per-device equilibration half-time: a research item; device type is kept but no half-time is researched.

### Analytical ultracentrifugation (auc)

- Effect: the KD in nM (key auc_kd), from a concentration series or a global equilibrium fit. With no KD, no effect is filled; the statement is complex seen or not seen, with the sedimentation shift carried beside it. QUALITATIVE_LOG_RATIO auc = 1.2. Strength anchors: noise_end = 1e5 nM, strong_end = 10 nM. Spread: a standard error is squared; a standard deviation becomes sd^2 / n only when replicates is supported and n is at least 2; a confidence interval is not converted. The strength is divided by 1 + r^2.
- Unknown weight: WEIGHT_UNKNOWN_BY_TYPE auc = 0.85. Override: binding_regime = 0.75.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| binding_parameter_definition (sedimentation_shift) | Percent by which the complex's s exceeds the larger component's s | SHIFT_FULL_AGREEMENT_PERCENT 10.0. When both component masses are stated: SHIFT_FULL_FRACTION_OF_EXPECTED 0.5 x the expected rise ((M_larger + M_smaller) / M_larger)^(2/3) - 1, capped at 10.0 and never below SHIFT_FULL_MIN_OVER_ZERO 2 x 2.0 = 4.0 | SHIFT_ZERO_AGREEMENT_PERCENT 2.0 | 1 - (1 - share)^SHIFT_EASE_POWER (2): steep at the noise floor, flat at full | Yes, at 2.0 percent or less | The paper's own larger-component control, and the partner's size when both masses are stated |
| binding_parameter_definition (mass) | Measured against theoretical mass of the complex, absolute deviation % | MASS_FULL_AGREEMENT_PERCENT 10.0. With the smaller component's mass stated: min(10.0, MASS_FULL_FRACTION_OF_ZERO 0.2 x zero) | MASS_ZERO_AGREEMENT_PERCENT 50.0. With the smaller component's mass stated: min(50.0, smaller mass / theoretical complex mass x 100) | Linear | Yes, at the zero end or beyond | The paper's own theoretical mass and smaller partner |
| binding_parameter_definition (stoichiometry) | Stated molar ratio, only when a KD is reported; fold = max(r, 1/r) | STOICHIOMETRY_FULL_AGREEMENT_FOLD 1.1 | STOICHIOMETRY_ZERO_AGREEMENT_FOLD 1.5 | Linear in the fold | Yes, at 1.5 or more | Absolute (1:1) |
| binding_regime (concentration_series) | Number of loading concentrations; a stated "no series" counts as 1 | MIN_CONCENTRATIONS 3 | None | count / 3, capped at 1 (1 gives 1/3, 2 gives 2/3) | Never | Absolute count |
| binding_regime (concentration_range) | Lowest and highest loading concentration over the KD (only with a KD); judged as saturation c / (c + KD) | Low end 0.2 x KD (LOW_OVER_KD_FULL_AGREEMENT, saturation 1/6); high end 5.0 x KD (HIGH_OVER_KD_FULL_AGREEMENT, saturation 5/6) | Low end 1.0 (LOW_OVER_KD_ZERO_AGREEMENT); high end 1.0 (HIGH_OVER_KD_ZERO_AGREEMENT); saturation 1/2 | Linear in saturation; the weaker end decides | Yes, when the series does not reach below (or above) the KD | The paper's own KD |
| calibration_applicability (fit_quality) | Fit rmsd with its unit; whether residuals are random | AU 0.005; fringes 0.003 (FIT_RMSD_FULL_AGREEMENT) | AU 0.02; fringes 0.012 (FIT_RMSD_ZERO_AGREEMENT), four times the noise | Linear | Yes, at the zero end or more; also when residuals are stated not random | Absolute (optical noise of the instrument) |
| sampling_basis (replicates) | Count of independent experiments, and independence | MIN_REPLICATES 3 | None | sqrt(min(n, 3) / 3): 1 gives 0.58, 2 gives 0.82. Independence not stated gives unknown | Only when independence is stated "no" | Absolute count |

- Facts that decide without a curve (a stated yes or no): complex_observed (complex_detected), components_alone, component_homogeneity, non_binding_control (binding_controls); reversibility, equilibrium_reached (not applicable for a velocity-only run), multiple_speeds (binding_regime); buffer_correction (calibration_applicability). The yes/no facts for mass, concentration_series and fit_quality decide when their numbers are not stated.
- Values marked "owner to confirm" in the code:
  - No AUC value carries that phrase. STOICHIOMETRY_ZERO_AGREEMENT_FOLD 1.5 differs from the SEC zero fold 2.0, and the SEC file says the difference is for the owner to settle.
- Not collected, with the stated reason:
  - Matrix recovery: an AUC run has no matrix recovery measurement.
  - Attributed signal and total signal: a complex species is not an attribution fraction.
  - Condition test and condition reference: no matched nuisance-condition response in an AUC record.
  - Assertion prediction and alternative prediction: belong to the target assertion, not the experiment.
  - Effect degrees of freedom: no Student t model selected.
  - Effect and variance when no KD: a qualitative assay reports no binding constant.
  - Equimolar dilution series for the concentration range: the scale shift is smaller than the factor-2 slack already kept, and the design would be unreliable to extract.
  - Rmsd relative to loading signal or the paper's stated noise: the paper rarely states either, so the field would almost always be unavailable; the absolute optics noise is the physically right scale.

### Differential scanning fluorimetry, thermal shift (dsf)

- Effect: an apparent KD in nM (key dsf_kd), from the Tm or its shift against ligand concentration. With no KD, no effect is filled; the statement is a Tm rise seen or not seen, with the shift in degrees C carried beside it. QUALITATIVE_LOG_RATIO dsf = 0.6. Strength anchors: noise_end = 1e5 nM, strong_end = 10 nM. Spread: a standard error is squared; a standard deviation becomes sd^2 / n only when replicates is supported and n is at least SD_MIN_EXPERIMENTS 2; a confidence interval is not converted. The strength is divided by 1 + r^2.
- Unknown weight: WEIGHT_UNKNOWN_BY_TYPE dsf = 0.70. Overrides: binding_controls = 0.80, binding_regime = 0.65.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| binding_parameter_definition (shift_size) | Signed Tm shift in degrees C (stated, or Tm with ligand minus Tm alone); ligand concentration of the shift and the KD when stated | SHIFT_FULL_AGREEMENT_C 2.0. When the concentration of the shift and a KD are both stated, the span (2.0 - 0.5) is multiplied by min(1, ln(1 + x) / ln(1 + 5.0)), x = concentration over KD (SHIFT_REFERENCE_OVER_KD 5.0) | SHIFT_ZERO_AGREEMENT_C 0.5 (degree 0, still supported) | Linear | Yes, only at a shift of 0 or a fall | Absolute; relative to the KD when the concentration of the shift is stated |
| binding_parameter_definition (shift_over_spread) | Shift over the stated SD of the Tm. A wells-only SD is replaced by sqrt(sd^2 + BETWEEN_EXPERIMENT_TM_SD_C 0.5^2) | SHIFT_OVER_SPREAD_FULL_AGREEMENT 3.0 | SHIFT_OVER_SPREAD_ZERO_AGREEMENT 1.0 | Linear | Yes, at 1.0 or less | The paper's own SD of the Tm |
| binding_regime (concentration_series) | Number of ligand concentrations; a stated "no titration" counts as 1 | No KD reported: MIN_CONCENTRATIONS 3. KD reported: MIN_CONCENTRATIONS_FOR_KD 5 | None | No KD: (n / 3)^1.0 (CONCENTRATION_CREDIT_POWER). KD: (n / 5)^2.0 (KD_CONCENTRATION_CREDIT_POWER), so 4 gives 0.64, 3 gives 0.36, 1 gives 0.04 | Never | Absolute count; depends on whether a KD is reported |
| binding_regime (concentration_range) | Lowest and highest ligand over the KD (only with a KD); KD over protein concentration when stated | Low end 0.2 (LOW_OVER_KD_FULL_AGREEMENT); high end 5.0 (HIGH_OVER_KD_FULL_AGREEMENT); KD over protein at least KD_OVER_PROTEIN_FULL_AGREEMENT 1.0 | Low end 1.0; high end 1.0 (occupancy 1/2) | Linear in occupancy x / (1 + x); the KD-over-protein degree is min(1, KD / protein); the weakest counts | Yes, when the series does not reach past the KD on a side. The protein term never conflicts | The paper's own KD and protein concentration |
| calibration_applicability (heating_rate) | Heating rate, degrees C per minute | HEATING_RATE_FULL_AGREEMENT 2.0 | HEATING_RATE_ZERO_AGREEMENT 10.0 | Linear | Yes, at 10.0 or more | Absolute |
| sampling_basis (replicates) | Count of independent experiments, and independence | MIN_REPLICATES 3 | None | sqrt(min(n, 3) / 3): 1 gives 0.58, 2 gives 0.82. Independence not stated gives unknown | Only when independence is stated "no" | Absolute count |

- Facts that decide without a curve (a stated yes or no): shift_observed (thermal_shift_observed), protein_alone_control, ligand_alone_control, curve_quality (melt_curve_sigmoidal), dose_dependence (shift_dose_dependent). The tm_spread_over_independent_experiments answer chooses whether the between-experiment SD is added.
- Values marked "owner to confirm" in the code:
  - None carries that phrase.
- Not collected, with the stated reason:
  - Matrix recovery: a thermal shift has no matrix recovery measurement.
  - Attributed signal and total signal: a thermal shift is not an attribution fraction.
  - Condition test and condition reference: no matched nuisance-condition response in a DSF record.
  - Assertion prediction and alternative prediction: belong to the target assertion, not the experiment.
  - Effect degrees of freedom: no Student t model selected.
  - Effect and variance when no KD: a qualitative assay reports no binding constant.
  - Unfolding enthalpy for the shift scale: rarely stated, so the size end stays absolute unless the concentration of the shift and the KD are both stated.

### Cellular thermal shift assay (cetsa)

- Effect: the apparent engagement EC50 of the isothermal dose response, in nM (key cetsa_apparent_kd). It is not an equilibrium KD; it depends on heating temperature and time. With no EC50, no effect is filled; the statement is engagement seen or not seen, with the Tm shift carried beside it. QUALITATIVE_LOG_RATIO cetsa = 0.6. Strength anchors: noise_end = 1e5 nM, strong_end = 10 nM. Spread: a standard error is squared; a standard deviation becomes sd^2 / n only when replicates is supported and n is at least SD_MIN_EXPERIMENTS 2; a confidence interval is not converted. The strength is divided by 1 + r^2.
- Unknown weight: WEIGHT_UNKNOWN_BY_TYPE cetsa = 0.65. Override: binding_controls = 0.55.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| binding_parameter_definition (thermal_shift) | Tm shift in degrees C (stated, else the difference of the two Tm values); SD of the Tm when stated | TM_SHIFT_FULL_AGREEMENT_C 3.0. Second degree, shift over SD: SHIFT_OVER_SPREAD_FULL_AGREEMENT 3.0 | TM_SHIFT_ZERO_AGREEMENT_C 0.5 (degree 0, still supported). Second degree: SHIFT_OVER_SPREAD_ZERO_AGREEMENT 1.0. A technical-replicate-only SD becomes sqrt(sd^2 + BETWEEN_EXPERIMENT_TM_SD_C 1.0^2) | Linear; with an SD stated the weaker of the two degrees counts | Yes, at a shift of 0 or a fall; also at shift over SD of 1.0 or less | Absolute for the shift; relative to the paper's own SD of the Tm when stated |
| binding_regime (temperature_series) | Number of heating temperatures; range ends and stated Tm values when given | MIN_TEMPERATURES 5; margin of each Tm from each end of the range TEMPERATURE_MARGIN_FULL_C 5.0 | Margin TEMPERATURE_MARGIN_ZERO_C 0.0 | Count: (n / 5)^2.0 (TEMPERATURE_CREDIT_POWER). Margin: linear. The weakest counts | Yes, when a stated Tm lies at or beyond an end of the range. Never from the count | Count absolute; margin relative to the paper's own range |
| binding_regime (isothermal_window) | Isothermal temperature minus the Tm of the unbound target | Distance at most ISOTHERMAL_WINDOW_FULL_C 5.0 | ISOTHERMAL_WINDOW_ZERO_C 12.0 | Linear in the distance | Yes, at 12.0 or more | The paper's own Tm of the unbound target |
| binding_regime (dose_response) | Number of compound concentrations | No EC50: MIN_CONCENTRATIONS 3. EC50 reported: MIN_CONCENTRATIONS_FOR_EC50 5 | None | No EC50: (n / 3)^1.0 (CONCENTRATION_CREDIT_POWER). EC50: (n / 5)^2.0 (EC50_CONCENTRATION_CREDIT_POWER) | Never from the count | Absolute count |
| binding_regime (concentration_range) | Lowest and highest concentration over the EC50 (only with an EC50) | Low end 0.2 (LOW_OVER_EC50_FULL_AGREEMENT); high end 5.0 (HIGH_OVER_EC50_FULL_AGREEMENT) | Low end 1.0; high end 1.0 (occupancy 1/2) | Linear in occupancy x / (1 + x); the weaker end decides | Yes, when the series does not reach past the EC50 on a side | The paper's own EC50 |
| sampling_basis (replicates) | Count of independent experiments, and independence | MIN_REPLICATES 3 | None | (n / 3)^REPLICATE_CREDIT_POWER 0.5: 1 gives 0.58, 2 gives 0.82. Independence not stated gives unknown | Only when independence is stated "no" | Absolute count |

- Facts that decide without a curve (a stated yes or no): engagement_observed (target_engagement_shown), vehicle_control, loading_control, negative_control, specificity_control, total_level_control (binding_controls); cell_integrity (calibration_applicability). The yes/no facts for temperature_series, isothermal_window and dose_response decide when their numbers are not stated; each is not applicable when the stated format has no such part (melt curve only or isothermal only).
- Values marked "owner to confirm" in the code:
  - None carries that phrase. The converter does flag one decision for the owner: a Tm fall is not counted as engagement (the criterion asks for a rise, and a computed fall stays conflicting), although thermal proteome profiling counts a destabilised target as a hit. Counting a fall would need a signed shift field, a direction fact and an owner ruling.
- Not collected, with the stated reason:
  - Matrix recovery: a CETSA run has no matrix recovery measurement.
  - Attributed signal and total signal: a CETSA stabilisation is not an attribution fraction.
  - Condition test and condition reference: no matched nuisance-condition response in a CETSA record.
  - Assertion prediction and alternative prediction: belong to the target assertion, not the experiment.
  - Effect degrees of freedom: no Student t model selected.
  - Effect and variance when no EC50: a qualitative assay reports no binding constant.
  - Compound concentration of the melt curve (to scale the shift): not worth it; a melt curve is run at one usually saturating dose and reports no EC50, so the ratio is almost never stated, and CETSA shifts do not rank affinity.
  - Cellular target concentration for a titration limit: almost never stated.

### BRET (bret)

- Effect: when the paper gives an apparent KD, that KD in nM is the measured effect (KD first; if there is none, the Ki in nM). It is a cell-based apparent constant, not a constant of purified proteins. Anchors: noise_end = 1e5 nM (strength 0), strong_end = 1.0 nM (strength 1); the position is on log10. QUALITATIVE_LOG_RATIO = 0.5, so the largest log ratio from a constant is 0.5. Spread enters as a variance: a standard error is squared; a standard deviation is squared and divided by n, only when the replicates are stated independent; a confidence interval is not used; no spread means no variance (r = 0). If the paper gives no KD and no Ki (only a BRET ratio or BRET50, which are not nM), no effect is filled and the stated detected or not detected counts with log ratio 0.5.
- Unknown weight: type 0.70. Overrides: binding_controls 0.60, binding_regime 0.60. The sheet criterion background_alternatives (the bystander test) has no override, so it takes 0.70.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| binding_parameter_definition (bret50_specificity) | BRET50 of the negative control pair divided by BRET50 of the pair (BRET50_CONTROL) | 3 | 1 | linear in the quotient | Yes, at 1 or below | The paper's own negative control |
| binding_parameter_definition (bret50_specificity, spread part) | When both BRET50 spreads are stated: ln(control / pair) divided by its standard error (SIGNIFICANCE) | 3 | 1 | linear; the weaker of this and the quotient decides | Yes, at 1 or below | The paper's own noise (SD is divided by sqrt(n) if replicates are independent; a confidence interval is not used) |
| binding_parameter_definition (signal_over_control) | BRET ratio of the pair divided by that of the negative control (SIGNAL) | 3 | 1 | linear in the quotient | Yes, at 1 or below | The paper's own negative control; if ratios are raw (background not subtracted) and the donor-only ratio is stated, the quotient is (pair - donor) / (control - donor). A pair no larger than the donor alone is the zero end; a control no larger than the donor alone gives full credit |
| binding_parameter_definition (signal_over_control, spread part) | When both ratio spreads are stated: (pair - control) divided by the standard error of the difference | 3 | 1 | linear; the weaker decides | Yes, at 1 or below | The paper's own noise |
| binding_regime (titration_points) | Number of acceptor-to-donor ratios or tracer concentrations | 8 points | 2 points | linear in the residual degrees of freedom (points minus 2) | Never (degree 0 at 2 or fewer) | Absolute count (two-parameter curve) |
| binding_regime (ratio_range, low end) | Lowest ratio divided by BRET50 | 0.2 | 1.0 | linear in the share of plateau reached, x / (1 + x) | Yes, at the zero end | The paper's own BRET50; not applicable if no BRET50 |
| binding_regime (ratio_range, high end) | Highest ratio divided by BRET50 | 5 | 1.0 | linear in x / (1 + x); the weaker of low and high decides | Yes, at the zero end | The paper's own BRET50 |
| binding_regime (tracer_regime) | Tracer concentration divided by the tracer's own KD, only for a Ki | 1 | 10 | linear in log10 of the quotient | Never (degree 0 at 10 or more) | The tracer's own KD stated in the paper; not applicable without a Ki |
| calibration_applicability (fit_quality) | R squared of the fit | 0.95 | 0.50 | linear in R squared | Yes, at 0.50 or below | Absolute |
| sampling_basis (replicates) | Number of independent experiments (transfections) | 3 | none (1 gives about 0.58, 2 about 0.82) | min(1, sqrt(n / 3)) | Only if independence is stated no (grader); a low count never | Absolute count |

- Facts that decide without a curve: interaction_detected (sets the statement), donor_only_control_done, acceptor_only_control_done, negative_control_pair_used and negative_control_no_specific_signal (binding_controls), fusion_orientation_swapped (binding_controls), expression_levels_measured, saturation_shown (not applicable for a displacement or ligand-induced run if not stated), tracer_displaced_by_competitor (not applicable for a titration or ligand-induced run if not stated), background_subtracted (calibration_applicability), independent_experiments. The bystander test (background_alternatives) uses hyperbola_preferred_over_linear and bret_constant_across_expression: any "no" is conflicting, else any "yes" is supported (one test is enough), else unknown.
- Values marked "owner to confirm" in the code:
  - FIT_R_SQUARED_ZERO_AGREEMENT = 0.50: lowered from 0.80 because cell BRET scatter in x gives R squared near 0.8 for a valid curve ("owner to confirm").
  - Unknown weight of the bystander test (background_alternatives) = 0.70 (type value, no override): "central, owner to decide".
- Not collected, with the stated reason:
  - Expression level as a number: declined; donor luminescence and fluorescence counts are instrument- and gain-specific, so no value is comparable between papers (the saturation curve, the negative pair and the bystander tests protect against the same problem).
  - A BRET ratio or a BRET50 as an effect: not put in the effect, because a BRET50 is an acceptor-to-donor ratio, not a concentration, and a BRET ratio is not on the nM scale.
  - Matrix recovery, attribution fractions, nuisance-condition response, target prediction, degrees of freedom: not filled (stated null reasons in NULL_REASONS).


### Yeast two-hybrid (y2h)

- Effect: none. Y2H reports growth or reporter activity, not a binding constant (Miller units are not a KD and are not on the nM scale), so there is no effect, no variance and no strength anchors. Only the stated detected or not detected counts, with QUALITATIVE_LOG_RATIO = 0.4 (the weakest direct-binding value, shared with split reporter). The reporter fold (pair over negative control) is carried beside the result and judged as a quality, not used as the effect size.
- Unknown weight: type 0.60. Overrides: binding_controls 0.50, binding_species 0.80, sampling_basis 0.80.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| binding_parameter_definition (reporter_fold) | Beta-galactosidase activity of the pair divided by that of the negative control | 10-fold | 2-fold | linear in the log of the fold | Yes, at 2-fold or below | The paper's own negative control. Not applicable if the paper states no interaction, or if the read-out is growth |
| binding_parameter_definition (reporter_fold, spread part) | When a spread is stated: (fold - 2) divided by the standard error of the fold, divided by 2 (SPREAD_Z_FULL = 2) | full at 2 standard errors | at the 2-fold level | linear; the weaker of the fold ramp and this decides | Only through the fold ramp | The paper's own spread (SEM as stated; SD divided by sqrt(n) if n is stated, else SD as stated; errors of the two activities combined as relative errors) |
| binding_parameter_definition (growth_titre) | Dilution factor of the most dilute growing spot, pair over negative control | 100 | 1 | linear in the log of the ratio | Yes, at 1 or below | The paper's own negative control. Not applicable if the read-out is the reporter fold or the paper states no interaction |
| binding_controls (bait_autoactivation) | 3-AT concentration of the bait-alone test (mM) against the scoring 3-AT concentration (mM), when the bait alone is stated inactive | test at or below the scoring concentration | none (degree = scoring / test above that) | scoring / test | Never | The paper's own scoring concentration |
| binding_controls (reciprocal_orientation) | Stated "no" (pair seen in only one orientation) | not applicable (a fixed share) | none | degree 0.5 (ONE_OF_TWO_SHARE) | Never | Not relative |
| binding_parameter_definition (reporter_concordance) | Stated "no" (only one reporter active) | not applicable (a fixed share) | none | degree 0.5 (ONE_OF_TWO_SHARE) | Never | Not relative |
| binding_controls (positive_control) | Stated "no" (the known positive pair did not activate) | not applicable | not applicable | no curve | Yes, when the paper does not state the pair interacts (then conflicting); if the pair is stated to interact, supported | Absolute |
| sampling_basis (replicates) | Number of independent experiments (transformations) | 3 | none (1 gives about 0.58, 2 about 0.82) | min(1, sqrt(n / 3)); degree attached only below 1 | Only if independence is stated no (grader) | Absolute count |

- Facts that decide without a curve: interaction_detected (sets the statement; interaction_observed is not applicable when it is "no"), bait_alone_inactive (when no 3-AT numbers are stated), prey_alone_inactive, non_interacting_control_done, nonselective_growth_shown, positive_control_done and reciprocal_orientation_tested and more_than_one_reporter_activated (when yes), fusion_expression_verified (binding_species), independent_experiments.
- Values marked "owner to confirm" in the code (worded in the code as "owner question"):
  - REPORTER_FOLD_ZERO_AGREEMENT = 2: conflicting at 2-fold or below is kept; the owner is asked whether, now that the spread is collected, the zero end should move to a fold of 1 (no larger than the control).
  - ONE_OF_TWO_SHARE = 0.5: the observed fraction, no literature value; owner asked whether to use a researched fraction.
- Not collected, with the stated reason:
  - Binding constant or any effect size: Y2H reports growth or reporter activity, never a constant.
  - Rescaling the fold by the positive-control window: considered and rejected; the window measures the reporter's sensitivity, while the question is whether the pair stands out of the background noise.
  - Matrix recovery, attribution fractions, nuisance-condition response, target prediction, degrees of freedom: not filled (NULL_REASONS).


### Split reporter (split_reporter)

- Effect: when the paper gives an apparent KD (a titration or reversible kinetics such as NanoBiT), that KD in nM is the measured effect (labelled as derived from the split reporter). Anchors: noise_end = 1e5 nM (strength 0), strong_end = 10.0 nM (strength 1), on log10. QUALITATIVE_LOG_RATIO = 0.4, so the largest log ratio from a constant is 0.4. Spread enters as a variance as for BRET (standard error squared; standard deviation squared over n only when replicates are independent; confidence interval not used). With no KD, no effect is filled and the stated detected or not detected counts with log ratio 0.4; the stated signal over the negative control is carried but not used as the effect.
- Unknown weight: type 0.65. Overrides: binding_controls 0.55, binding_regime 0.60.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| binding_parameter_definition (signal_to_background) | Stated signal over background | 10-fold | 2-fold | linear in the log of the fold | Yes, at 2-fold or below | The paper's own background |
| binding_parameter_definition (negative_control_ratio) | Stated signal over the negative control pair | 5-fold | 1.5-fold | linear in the log of the fold | Yes, at 1.5-fold or below; also conflicting if the paper states the fusions were not at matched expression (expression_matched_to_control "no") | The paper's own negative pair |
| binding_regime (fusion_orientations) | Number of orientations that gave a signal (else "only one orientation" = 1, else the number tested) | 2 | 0 | degree = n / 2, at most 1 (one orientation gives 0.5) | Never | Absolute count |
| binding_regime (titration_series) | Number of titration concentrations, only with a KD | 5 | 2 | linear: (n - 2) / (5 - 2) | Never (degree 0 at 2 or fewer) | Absolute count |
| binding_regime (titration_range, high end) | Highest concentration divided by the paper's KD, only with a KD | 5 | 1.0 | linear in occupancy r / (1 + r) | Yes, at the zero end | The paper's own apparent KD |
| binding_regime (titration_range, low end) | Lowest concentration divided by the paper's KD (judged only if the lowest is below the highest) | 0.2 | 1.0 | linear in occupancy r / (1 + r); the weakest part decides | Yes, at the zero end | The paper's own apparent KD |
| binding_regime (titration_range, fixed partner) | Concentration of the constant partner divided by the KD (bias = 1 + 0.5 x quotient) | quotient 1 | quotient 10 | linear in the log of the bias | Yes, at 10 or above (the KD is then only an upper bound) | The paper's own apparent KD |
| sampling_basis (replicates) | Number of independent experiments | 3 | none (1 gives about 0.58, 2 about 0.82) | min(1, sqrt(n / 3)) | Only if independence is stated no (grader) | Absolute count |

- Facts that decide without a curve: interaction_detected (sets the statement), fragment_alone_control_negative, unrelated_pair_control_negative, binding_mutant_control_negative, positive_control_done (all binding_controls), saturable_titration_shown, complementation_reversible (binding_regime), expression_verified and background_subtracted (calibration_applicability), independent_experiments. A stated "no" for expression_matched_to_control is conflicting (see table).
- Values marked "owner to confirm" in the code (worded in the code as "owner question"):
  - Per-reporter full value for signal_to_background (now one value, 10; lower for a split fluorescent protein): an owner or expert question, not a gap.
  - No constant is marked "owner to confirm" by name in this assay's code.
- Not collected, with the stated reason:
  - Spread of the background or a Z' for signal_to_background: declined; a paper almost never states it for a split-reporter result, and it would add a new researched cut.
  - Expression ratio of the test and control fusions: declined; rarely stated, and a graded scale would be a new unreasoned number (only the yes/no fact expression_matched_to_control is kept).
  - Which control the negative-control ratio is over (fragment alone, unrelated pair, binding mutant): declined; the three controls have their own facts, and a different credit per control kind has no researched value.
  - Matrix recovery, attribution fractions, nuisance-condition response, target prediction, degrees of freedom: not filled (NULL_REASONS).


### Proximity ligation assay (pla)

- Effect: none. A PLA reports puncta per cell, never a binding constant, so there is no effect, no variance and no strength anchors. Only the stated detected or not detected counts, with QUALITATIVE_LOG_RATIO = 0.5. The puncta fold over the control is carried beside the result and judged as a quality.
- Unknown weight: type 0.55. Overrides: binding_controls 0.50, calibration_applicability 0.50, binding_regime 0.70, sampling_basis 0.80.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| binding_parameter_definition (puncta_enrichment) | Puncta per cell of the test divided by those of the negative control | 3-fold | 1-fold | linear in the log of the fold. A control of 0 puncta with a test above 0 is full credit; a test of 0 is conflicting | Yes, at 1-fold or below | The paper's own negative control |
| binding_parameter_definition (puncta_enrichment, spread part) | When both spreads and their kind are stated: (test - control) divided by the standard error of the difference, divided by 2 (SPREAD_Z_FULL = 2) | full at 2 standard errors | 0 (no difference) | linear; the weaker of this and the fold decides | Only through the fold ramp | The paper's own spread (SD is divided by sqrt(replicates) if stated, else used as it is) |
| binding_controls (specificity_control) | Fall in percent of the specific puncta after knockdown, knockout or competition: (test - knockdown) / (test - control). If the control is not stated or the test is not above it, the fall of the total puncta (test - knockdown) / test | 70 percent | 20 percent | linear in the percent | Yes, at 20 percent or below (an increase counts as a negative fall); a stated "no" is also conflicting | The paper's own puncta. When the measured protein depletion (percent) is stated, both ends are multiplied by depletion / 100 (depletion capped at 100) |
| sampling_basis (cells_counted) | Number of cells counted | 50 cells | none (1 cell gives about 0.14, 10 cells about 0.45, 25 cells about 0.71) | min(1, sqrt(n / 50)) | Never | Absolute count |
| sampling_basis (replicates) | Number of independent experiments | 3 | none (1 gives about 0.58, 2 about 0.82) | min(1, sqrt(n / 3)) | Only if independence is stated no (grader) | Absolute count |

- Facts that decide without a curve: proximity_signal_detected (sets the statement), single_antibody_controls_negative, no_primary_control_negative, positive_control_pair_done (binding_controls), puncta_in_expected_compartment (binding_regime), primary_antibodies_different_species (binding_parameter_definition), antibodies_validated, quantification_blinded, statistical_test_done (calibration_applicability), independent_experiments. The amplification time is recorded and not judged.
- Values marked "owner to confirm" in the code (worded in the code as "owner question"):
  - REDUCTION_ZERO_AGREEMENT_PERCENT = 20 (conflicting at a fall of 20 percent or less): "the most consequential number here (owner question, kept)", because without the depletion a small fall could be a failed knockdown rather than a cross-reactive antibody.
  - No constant is marked "owner to confirm" by name in this assay's code.
- Not collected, with the stated reason:
  - Which negative control the count is (single-antibody or no-primary): not added; both already have their own fact, and a correction by control kind would need a number no method paper gives.
  - Kind of manipulation (knockdown, knockout, competition): not added; where it matters its effect is the measured depletion, and a competing peptide has no depletion to measure.
  - Cells counted per condition or in total: not added; it would need the number of conditions, and the effect of the count is small.
  - The p-value: not added; a test over cells is pseudoreplicated, so it adds nothing the fold in standard errors and the replicate count do not already say, and it has no researched scale.
  - Per-cell SD of puncta: not collected (listed as a gap; the cell count stays absolute).
  - Binding constant: a puncta count is never a KD and never pools with one.
  - Matrix recovery, attribution fractions, nuisance-condition response, target prediction, degrees of freedom: not filled (NULL_REASONS).


### Proximity labelling (proximity)

- Effect: none. An enrichment is never a KD and never pools, so there is no effect, no variance and no strength anchors. Only the stated enriched (detected) or not enriched (not detected) counts, with QUALITATIVE_LOG_RATIO = 0.5. "Detected" here means proximity (about 10 to 20 nm in living cells), not direct binding. The fold enrichment is carried beside the result and judged as a quality.
- Unknown weight: type 0.60. Overrides: binding_parameter_definition 0.55, calibration_applicability 0.85, sampling_basis 0.80.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| binding_parameter_definition (enrichment_magnitude) | Fold enrichment of the candidate over the control (a log2 value is converted to a ratio) | 4-fold; 8-fold if the paper states the control does not match the bait (fold_over_matched_control "no", FOLD_FULL_AGREEMENT_UNMATCHED) | 1-fold | linear in the log of the fold | Yes, at 1-fold or below | The paper's own control. Not applicable if the candidate is stated not enriched |
| binding_parameter_definition (enrichment_significance) | False discovery rate in percent (a fraction is converted to percent) | 1 percent | 10 percent | linear in the rate | Yes, at 10 percent or above; a stated "no" for statistical_test_used is also conflicting | Absolute (the rate is already self-calibrated). Not applicable if the candidate is stated not enriched |
| binding_regime (expression_level) | Expression of the fusion divided by the endogenous bait | 2 | 10 | linear in the log of the ratio (low expression is not penalised) | Yes, at 10 or above; a stated "no" for bait_expression_checked is also conflicting | The paper's own endogenous bait |
| sampling_basis (replicates) | Number of independent experiments (cultures) | 3 | none (1 gives about 0.58, 2 about 0.82) | min(1, sqrt(n / 3)) | Only if independence is stated no (grader) | Absolute count |

- Facts that decide without a curve: candidate_enriched (sets the statement; a stated yes or no both make proximity_observed supported), ligase_only_control, unlabeled_control, unrelated_bait_control (binding_controls), bait_localization_checked (binding_regime), orthogonal_validation (binding_parameter_definition), biotinylation_confirmed and streptavidin_capture (calibration_applicability), independent_experiments. If no fold, rate or ratio is stated, the related yes/no fact decides (statistical_test_used, bait_expression_checked).
- Values marked "owner to confirm" in the code:
  - EXPRESSION_ZERO_AGREEMENT = 10: "the expert zero end (no standard value; EXPERT_REVIEW)"; not marked owner to confirm by name.
  - FOLD_FULL_AGREEMENT_UNMATCHED = 8: "expert judgment, no standard value"; not marked owner to confirm by name.
  - No constant is marked "owner to confirm" by that wording in this assay's code; the two above are the ones the code itself calls unstandardised.
- Not collected, with the stated reason:
  - Whether the stated rate is the candidate's own or the hit-list cut-off: not done; both bound the false calls from above (the stated rate errs on the strict side), and a correction needs a number with no standard value.
  - Isobaric (TMT) ratio compression: not done; it understates the true fold, so a stated fold that clears the ramp is conservative, and no honest correction exists without an unreasoned factor.
  - Labelling time: not done; the harm of a long labelling is what the controls and the fold already measure, and the right time depends on the enzyme.
  - Binding constant: an enrichment is never a KD.
  - Matrix recovery, attribution fractions, nuisance-condition response, target prediction, degrees of freedom: not filled (NULL_REASONS).



### Microscopy co-localization / recruitment (colocalization)

- Effect: none. A fraction of scored objects, a Pearson coefficient or an enrichment is never a KD and never pools, so there is no effect, no variance and no strength anchors. Only the stated co-localized or recruited (detected) or not (not detected) counts, with QUALITATIVE_LOG_RATIO = 0.5. "Detected" here means nearness (within about 250 nm with diffraction-limited imaging), not contact. The enrichment is carried beside the result. Draft of 2026-11-22; every number below is EXPERT_REVIEW, owner to confirm, from the drafter's memory and not web-verified. The five files were written and read but not run.
- Unknown weight: type 0.60. Overrides: binding_controls 0.50, calibration_applicability 0.60, binding_regime 0.70, sampling_basis 0.80.

| Sheet criterion | What is read from the paper | Full agreement at | Zero at | Shape between | Can it conflict | Relative to what |
|---|---|---|---|---|---|---|
| binding_parameter_definition (colocalization_readout, fraction) | Percent of the scored cells, foci or droplets that show the co-localization | 80 percent | 10 percent | linear in the percent | Only when every stated readout number is at or below its zero end (the best degree of the stated numbers counts) | Absolute (no unrelated-protein fraction collected) |
| binding_parameter_definition (colocalization_readout, Pearson) | Pearson coefficient of the two channels | 0.7 | 0.2 | linear | As above | Absolute (a coefficient reads low for a small focus in a large cell, hence the best-of rule) |
| binding_parameter_definition (colocalization_readout, enrichment) | Signal at the partner's site over the signal elsewhere (partition coefficient) | 3 | 1 | linear in the log of the ratio | As above | The paper's own surroundings |
| binding_controls (specificity_control) | Facts: an unrelated protein or the tag alone is not recruited; the localization is lost without the partner | yes on either (one stated control is a control) | a stated no on either | fact rule | Yes, any no | The paper's own controls |
| binding_regime (directness) | Facts: a binding-region mutant no longer co-localizes; the protein follows the partner when it is moved; the facts heterologous_host and purified_proteins (either yes gives a supported reading by itself) | a yes fact, or a heterologous host or purified proteins stated | a stated no on either fact | fact rule; the native host alone is unknown, never conflicting | Yes, a stated no on a fact | The paper's own mutants |
| calibration_applicability (expression_validity) | Facts: near-native expression (not applicable for purified proteins); the tagged protein is functional or the tag does not change the localization | yes on both | a stated no on either | shared fact rule | Yes, any no | The paper's own checks |
| sampling_basis (objects_counted) | Number of cells, foci or droplets scored; the quantification fact (a stated no, one representative image, conflicts) | 100 objects | none (10 objects give about 0.32, 50 about 0.71) | min(1, sqrt(n / 100)) | Only through the fact stated no | Absolute count |
| sampling_basis (replicates) | Number of independent experiments | 3 | none (1 gives about 0.58, 2 about 0.82) | min(1, sqrt(n / 3)) | Only if independence is stated no (grader) | Absolute count |

- Facts that decide without a curve: colocalization_observed (sets the statement; a stated yes or no both make the criterion supported), the facts of specificity_control, directness and expression_validity, quantified_over_many_cells (sampling_basis).
- Values confirmed by the owner on 2026-11-22 (from memory, not checked against sources): all of them: ENRICHMENT_FULL_AGREEMENT 3 / ENRICHMENT_ZERO_AGREEMENT 1, PEARSON_FULL_AGREEMENT 0.7 / PEARSON_ZERO_AGREEMENT 0.2, FRACTION_FULL_AGREEMENT_PERCENT 80 / FRACTION_ZERO_AGREEMENT_PERCENT 10, OBJECTS_COUNTED_FULL_CREDIT 100, REPLICATES_FULL_CREDIT 3, and the contract values (QUALITATIVE_LOG_RATIO 0.5, type weight 0.60, criterion weights).
- Not collected, with the stated reason:
  - Fraction or Pearson coefficient of the unrelated protein under the same conditions: not collected; the fact unrelated_protein_not_recruited carries it as yes or no.
  - Imaging mode: recorded for the reviewer, not judged; diffraction-limited imaging limits the claim to nearness, which the type weight carries.
  - Pearson significance test per image (Costes randomisation): not collected; no stated number to judge.
  - Binding constant: a fraction, a coefficient or an enrichment is never a KD.
  - Matrix recovery, attribution fractions, nuisance-condition response, target prediction, degrees of freedom: not filled (NULL_REASONS).
