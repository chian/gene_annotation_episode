"""Dialysis converter: turns the dialysis grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_dialysis.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding'), the sheet itself (grade_assay run on it), the
dependence keys the merger needs, the qualitative effect when the experiment reports no constant, and for every sheet component that a dialysis
cannot honestly fill, the reason it stays null.

Two cases (the contract of the earlier types is unchanged)
---------------------------------------------------------
QUANTITATIVE: the record has a KD (else a Ki). Then the converter fills the numeric effect as the earlier quantitative types do (quantity_kind 'binding_parameter'):
  effect            the KD in nM (point operand, measurement key dialysis_kd), else the Ki in nM (dialysis_ki), as the radioligand converter takes its constant. A Bmax is not a
                    binding constant and is never the effect.
  effect_variance   variance of that constant, nM_squared, only when the source's spread (kd_spread for a KD, ki_spread for a Ki) allows it: standard_error -> se^2;
                    standard_deviation -> sd^2 / n, and only when the replicates criterion is fully supported (at least MIN_REPLICATES independent experiments, degree 1.0);
                    confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
  effect_precision  the sheet computes 1 / variance from the above.
  There is no qualitative_effect: the result enters the merger's pool and is not counted a second time as a qualitative result.
QUALITATIVE: the record has neither a KD nor a Ki (a percent bound, a percent unbound or a fraction bound at one or more concentrations, or a Bmax alone). Then, exactly as the pull-down,
EMSA and SEC converters do (quantity_kind 'relative_binding_response'), NO effect and no variance are filled: the sheet's measured_effect, effect_variance and effect_precision cells
are unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is invented: no KD, and neither the percent bound nor the fraction unbound is put
into the effect (they are not on the nM scale). What the experiment does contribute is carried beside the sheet, in 'qualitative_effect'
({'statement', 'support_refs', 'percent_bound'}):
  statement          'interaction_detected' (binding is observed), 'interaction_not_detected' (binding is stated not to be observed, or the stated percent bound is below the minimum)
                     or 'interaction_not_stated'
  support_refs       the spans of the fact or of the stated fraction that decides it (empty when not stated)
  percent_bound      the percent of the total ligand that was bound (stated, or from the percent unbound, the fraction bound or the fraction unbound), or None
The scoring reads 'qualitative_effect': its statement fixes the direction (literature_direction.py) and its support refs join the row (literature_row.py).

Criteria mapping (dialysis criteria -> sheet criteria), declared in CRITERIA_MAP
-------------------------------------------------------------------------------
binding_controls              buffer_only_control + protein_retained + device_adsorption + ligand_stability (the controls that show the ligand crosses the membrane, the protein does
                              not, nothing is lost to the device and nothing is degraded)
binding_regime                equilibrium + ligand_depletion + protein_level + concentration_series + volume_shift (equilibrium, the sites not used up, a protein concentration at which a
                              fraction is measurable, a series that brackets the KD, no volume shift)
binding_parameter_definition  binding_observed + fit_model (what the response is: a bound fraction, and the model of the fit)
calibration_applicability     recovery + free_measured_directly + free_fraction_measurable (the measurement of the free ligand: a mass balance, a direct measurement, a free fraction that is measurable)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each
such criterion and reason to its judgement). OWNER RULE (2026-11-21, A105_EXPERIMENT_SOP.md step 3): every researched value below is KEPT as a named EXPERT_REVIEW
constant with its reason, and is the end of a gradual curve, not a pass/fail step. Linear ramps (supported with a degree of 1.0 up to, or from, the full-agreement limit,
falling linearly to 0 at the zero-agreement limit, conflicting at or beyond it): recovery (both sides of the mass balance), device_adsorption, volume_shift (a stated shift),
ligand_depletion (bound over protein, scaled by the paper's own sites per protein), protein_level (protein over KD), free_fraction_measurable (percent unbound) and the low
and high end of concentration_series. Other shapes, each chosen for dialysis (the reasons are in the judges and in the answers below):
  binding_observed            the direction is decided at MIN_PERCENT_BOUND (below it conflicting, 'interaction_not_detected'); above it the degree rises linearly from 0 at
                              MIN_PERCENT_BOUND to 1 at QUANTIFIED_PERCENT_BOUND, so a fraction just above the detection limit is detected with little credit.
  equilibrium                 the exponential approach to equilibrium (HALF_LIVES_AT_MIN_EQUILIBRATION half-lives at MIN_EQUILIBRATION_H): steep near the
                              zero-agreement time, gentle near the researched one; conflicting at or below EQUILIBRATION_ZERO_AGREEMENT_H.
  concentration_series count  rises linearly in the residual degrees of freedom of the one-site fit, from 0 at FIT_PARAMETERS to 1 at MIN_CONCENTRATIONS; a short series is
                              supported with that low degree, never conflicting; the degree is the weakest of the count, the low end and the high end.
  replicates                  sqrt(n / MIN_REPLICATES), capped at 1 (precision of the mean over n independent experiments); never conflicting for a stated count;
                              independence not stated is unknown (a stated no is the grader's conflicting).
  volume_shift (salt)         degree salt / (MIN_SALT_MM scaled by the protein concentration over PLASMA_PROTEIN_NM), capped at 1; unknown at or below
                              SALT_ZERO_AGREEMENT_MM; never conflicting. No unknown weight inside the degree.
A sheet criterion that is supported carries the smallest degree of its members that have one (the sheet reads no degree; it travels with the interpretation and the merger
carries it per result).

The owner's five questions, answered per researched value (2026-11-21; citations from memory, not web-checked; Q1 what it protects against, Q2 general or lab-specific,
Q3 absolute or relative and whether the relative quantity is in the grader facts, Q4 how badly a wrong value misleads and whether the shape reflects it, Q5 consistency)
---------------------------------------------------------------------------------------------------------------------------------------------------------------------
MIN_PERCENT_BOUND 5, QUANTIFIED_PERCENT_BOUND 15 (binding_observed)
  Q1 a 'binding' that is only the difference of two measurements within their error (free vs total). Q2 depends on the detector: scintillation counting is precise to a few
  percent, LC-MS/MS is validated to +-15 percent (FDA Bioanalytical Method Validation 2018), so 5 percent is the detection end for a precise detector and inside the error of
  a typical LC-MS/MS one; 15 percent = 3 x 5 is the quantification end (ICH Q2(R1): LOQ 10 sigma / LOD 3.3 sigma = 3). Q3 should be relative to the paper's stated spread of
  the percent bound: NOT in the grader facts (grader gap). Q4 was a step to full credit at 5 percent: a 6 percent bound read by LC-MS/MS was a full-weight 'binds';
  CHANGED: the statement still flips at 5 (a direction is binary) but the degree starts at 0 there, so the row weight is continuous across the flip. Q5 like the other
  qualitative statements (pull-down, EMSA): the statement is binary; its credit is graded.
MIN_PERCENT_UNBOUND 1, FREE_FRACTION_ZERO_AGREEMENT_PERCENT 0 (free_fraction_measurable)
  Q1 a free concentration at the limit of quantification, so the percent unbound (and a KD from it) is noise. Q2 general: FDA In Vitro Drug Interaction guidance (2020)
  takes fu below 1 percent as not reliably measured. Q3 truly relative to the detector's LLOQ over the free concentration: the LLOQ is NOT in the grader facts (grader gap).
  Q4 the relative error of the free fraction grows as 1/fu, so the credit linear in fu is the right shape. KEPT. Q5 a ratio ramp like protein_level.
MIN_EQUILIBRATION_H 4, EQUILIBRATION_ZERO_AGREEMENT_H 1, HALF_LIVES_AT_MIN_EQUILIBRATION 5 (equilibrium)
  Q1 a free fraction read before the two chambers equilibrated. Q2 4 to 6 h is the validated rapid equilibrium dialysis protocol (Waters et al. 2008, J Pharm Sci 97:4586);
  a macro cell or cassette needs longer (often overnight), so 4 h is device-specific and lenient for slow devices. Q3 relative to the device's equilibration half-time:
  device_type is in the native values but no per-device half-time is researched (EXPERT_REVIEW item, not a grader gap); the paper's own time course is the relative check
  and the grader already lets it decide. Q4 the approach is exponential, so the old linear ramp under-credited 2 to 3 h (82 to 93 percent equilibrated); CHANGED to the
  exponential approach (steep near 1 h, gentle near 4 h); values kept; a 1 h dialysis (about 58 percent of the way) stays conflicting. Q5 the same approach-to-equilibrium
  shape as the radioligand incubation, without its unknown weight inside the degree.
MIN_RECOVERY_PERCENT 80, RECOVERY_ZERO_AGREEMENT_PERCENT 50, MAX_RECOVERY_PERCENT 120, RECOVERY_HIGH_ZERO_AGREEMENT_PERCENT 150 (recovery)
  Q1 ligand lost to (or gained by) the device, degradation, evaporation or an analytical error biasing the free concentration. Q2 general: 80 to 120 percent acceptance
  (Waters 2008; Di et al. 2012, J Pharm Sci 101:1327). Q3 already relative (percent of the paper's own total). Q4 the old judge read only the low side: a 160 percent
  mass balance got full credit; CHANGED: the high side of the same researched window was added, symmetric in the deviation (20 accepted, 50 failed). Linear is right (the
  bias of the free fraction is about proportional to the unaccounted ligand). Q5 like the SPR Rmax window (both sides).
MAX_ADSORPTION_PERCENT 15, ADSORPTION_ZERO_AGREEMENT_PERCENT 40, DEVICE_SHARE_OF_BOUND_FULL 0.2, DEVICE_SHARE_OF_BOUND_ZERO 1.0 (device_adsorption)
  Q1 ligand bound to the membrane or device counted as protein-bound. Q2 10 to 15 percent is the usual nonspecific-binding limit; it matters most in ultrafiltration, where
  the filter takes free ligand out of the filtrate (Lee et al. 2003, Pharm Res 20:1015); in equilibrium dialysis with both chambers measured it mostly lowers the recovery.
  Q3 the harm is relative: the false bound is about adsorption x fraction unbound, to be read against the stated percent bound (in the native values); CHANGED: for an
  ultrafiltration the degree is also the weaker with the share of the stated bound the device could account for (full at 0.2, conflicting at 1.0, where the device accounts
  for all of it), in addition to the absolute ramp, which is KEPT. Whether the stated adsorption was corrected for is NOT handed to the sheet (grader gap). Q4 a 5 percent
  filter loss against a 5 percent bound was full credit; now nearly none. Q5 'a signal no larger than the paper's own control' is conflicting in every binding assay.
MAX_VOLUME_SHIFT_PERCENT 10, VOLUME_SHIFT_ZERO_AGREEMENT_PERCENT 30 (volume_shift, a stated shift)
  Q1 concentrations of the two chambers changed by osmotic or Donnan water flow. Q2 general (Tozer et al. 1983, J Pharm Sci 72:1442; Boudinot and Jusko 1984,
  J Pharm Sci 73:774). Q3 already relative (percent of the paper's own chamber volume). Q4 the bias of the free fraction is about proportional to the shift; linear right. KEPT.
MIN_SALT_MM 100, SALT_ZERO_AGREEMENT_MM 0, PLASMA_PROTEIN_NM 600000 (volume_shift, the salt when no shift is stated)
  Q1 a Donnan shift of ions and water that the salt did not screen. Q2 100 to 150 mM is general for PLASMA-level protein (about 0.6 mM albumin); it is not a rule for a
  dilute purified protein. Q3 the Donnan excess goes as the protein's charge x its concentration / the salt: the protein concentration IS in the native values, the charge
  (pI with the buffer pH) and the buffer's own ionic strength are NOT (grader gap). Q4 the old degree fell only to WEIGHT_UNKNOWN (the unknown weight inside a degree,
  forbidden) and penalised 1 uM protein in 20 mM salt as if it were plasma; CHANGED: the full-agreement salt is MIN_SALT_MM x protein / PLASMA_PROTEIN_NM (plasma level
  when the protein is not stated), the degree salt / that (one over the relative Donnan bias), unknown at no salt (the buffer ions are not recorded). Q5 the SEC salt is
  unknown below its zero too; neither uses the unknown weight inside a degree.
MAX_BOUND_OVER_PROTEIN 1, BOUND_OVER_PROTEIN_ZERO_AGREEMENT 3 (ligand_depletion)
  Q1 more ligand bound than there are sites (nonspecific binding, aggregation or a concentration error). Q2 general for a one-site protein; a multi-site protein (albumin,
  fatty acids) binds more. Q3 relative to the paper's own sites per protein: Bmax as a ratio, or Bmax in nM over the protein, both in the native values; CHANGED: the limits
  are multiplied by those sites when more than one (never stricter than the researched one site). Q4 a two-site protein at 2.5 bound per protein was 0.25; now 0.875.
  Linear kept.
MIN_PROTEIN_OVER_KD 0.2, PROTEIN_OVER_KD_ZERO_AGREEMENT 0.05 (protein_level)
  Q1 a protein too dilute for a measurable fraction bound. Q2 follows from the binding isotherm: at 0.05 x KD about 5 percent of a trace ligand binds (MIN_PERCENT_BOUND), at
  0.2 x KD about 17 percent (QUANTIFIED_PERCENT_BOUND). Q3 already relative (the paper's protein over its own KD). Q4 the fraction bound is near-linear in protein / KD at
  these ratios, so linear is right. KEPT.
MIN_CONCENTRATIONS 6, FIT_PARAMETERS 2, LOW_FACTOR 0.5 / LOW_ZERO_AGREEMENT_FACTOR 1.0, HIGH_FACTOR 4 / HIGH_ZERO_AGREEMENT_FACTOR 1.0 (concentration_series)
  Q1 a KD and a Bmax not both defined by the series (too few points, or a series that does not bracket the KD; Klotz 1982, Science 217:1247: Bmax needs about 80 percent
  occupancy, HIGH_FACTOR 4). Q2 general saturation design; each dialysis point is a separate cell, so 6 rather than the 8 of radioligand. Q3 the ends are already relative
  (over the paper's KD). Q4 the count was conflicting at 2 or fewer: a short series is weaker evidence, not evidence against; CHANGED to supported with degree 0 there
  (as SPR's CONCENTRATIONS_ZERO); the span ramps (conflicting when the series does not reach the KD at all) KEPT.
  Decision C (2026-11-21, owner to confirm; no new constants): both ends of the span are now judged linearly in the one-site occupancy x / (1 + x), not in x, between the same
  ends (LOW 0.5 -> 1.0 = occupancy 1/3 -> 1/2; HIGH 4 -> 1.0 = occupancy 4/5 -> 1/2). Q1 same. Q2 the occupancy scale is the one the sixteen other assays use. Q3 relative
  to the KD, collected by the grader (low and high over KD). Q4 in x, a highest concentration at 2 x KD (occupancy 0.67) earned 1/3 and 3 x KD (0.75) earned 2/3, though the
  plateau is mostly reached; in occupancy they earn (0.667 - 0.5) / 0.3 = 0.556 and 0.833, while a lowest concentration at 0.75 x KD earned 0.5 and now earns
  (0.5 - 0.4286) / (0.5 - 0.3333) = 0.429. The conflicting boundary stays at the KD. Q5 consistent with the other assays. No dialysis-specific reason for linear-in-x was found
  (the ligand is judged as total concentration over the KD, as elsewhere). How far past the KD is asked for is unchanged.
MIN_REPLICATES 3 (replicates); SINGLE_EXPERIMENT removed
  Q1 errors that only separate experiments show (protein or plasma lot, membrane lot, day-to-day calibration). Q2 general (triplicate independent experiments). Q3 absolute
  count. Q4/Q5 the old linear (n - 1) / 2 ramp made one experiment conflicting, unlike every other binding assay; CHANGED to sqrt(n / MIN_REPLICATES) (1: 0.58, 2: 0.82),
  never conflicting for a stated count. The variance sd^2 / n is still built only at full agreement (n >= MIN_REPLICATES: an sd from one or two degrees of freedom is too
  unstable to set the precision of the pooled effect).
Grader gaps closed (2026-11-21, range review follow-up; the grader, record, extraction form and passages now collect these):
  percent_bound_spread (standard deviation of the percent bound): binding_observed reads its ramp against the paper's own noise (LOD_SIGMAS, LOQ_SIGMAS; ICH Q2(R1)); the
    researched 5 and 15 stay as the floor. Direction still decided at MIN_PERCENT_BOUND. Not stated: the researched ramp as before.
  detection_lloq (detector's lower limit of quantification): free_fraction_measurable also judges the free concentration over it (FREE_OVER_LLOQ_FULL / _ZERO; FDA BMV 2018),
    the weaker of that and the percent-unbound ramp. The free concentration is the stated one, else total x percent unbound.
  adsorption_corrected (fact adsorption_checked_and_corrected, now handed with a stated adsorption): a stated and corrected adsorption leaves ADSORPTION_CORRECTION_RESIDUAL of
    itself as bias; an uncorrected or unstated correction counts whole (as before).
  NOT added: the protein's net charge (pI with the buffer pH) and the buffer's own ionic strength for the Donnan scale (volume_shift salt): a methods paragraph almost never
    states them and a model may not work them out (quote only), so the field would be unavailable almost always; the plasma-albumin charge assumption stays. Per-device
    equilibration half-time: a research item (the device_type is in native), not a grader fact.

Unknown weight: none of the degrees above uses the row weight of an unknown criterion (WEIGHT_UNKNOWN is no longer imported). The per-assay unknown weight is decided in
literature_row_contract (WEIGHT_UNKNOWN_BY_TYPE['dialysis']; A105_ASSAY_CALIBRATION_DETAILS.md proposes 0.85, calibration_applicability 0.80), not here.
The qualitative statement, when the fact binding_detected is not stated and a fraction is, is the sheet's reading of the judgement of binding_observed: supported is
'interaction_detected', conflicting (the percent bound below MIN_PERCENT_BOUND) is 'interaction_not_detected', with the refs of the fraction, exactly as before.
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0,
implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose
weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree (the
continuous comparisons above); direct leaves it unchanged. Support never changes a status. variance_correspondence takes the weakest support of the
spread (and of the replicate count for a standard deviation).
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported, assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the ligand, immobilized_preparation_ref = the protein,
surface_ref = None (a membrane or a device is not a surface reference), dataset_ref = the dataset.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_criteria import NM_PER_UNIT, PERCENT_FULL
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_grader import BOUND_FROM

VERSION = 'a105_dialysis_converted_v1'
BINDING_CONSTANTS = ('kd', 'ki')
CRITERIA_MAP = {'binding_controls': ('buffer_only_control', 'protein_retained', 'device_adsorption', 'ligand_stability'), 'binding_regime': ('equilibrium', 'ligand_depletion', 'protein_level', 'concentration_series', 'volume_shift'), 'binding_parameter_definition': ('binding_observed', 'fit_model'), 'calibration_applicability': ('recovery', 'free_measured_directly', 'free_fraction_measurable'), 'sampling_basis': ('replicates',)}
MIN_PERCENT_BOUND = 5.0  # EXPERT_REVIEW: smallest percent of the total ligand bound that shows binding; below about 5 percent the free and the total concentration differ by no more than the error of the two measurements (a few percent each), so no binding is shown. It decides the qualitative statement (detected or not) and is the zero end of the credit of a detected binding.
QUANTIFIED_PERCENT_BOUND = 15.0  # EXPERT_REVIEW: percent bound from which the binding is not only detected but quantified, full credit; three times MIN_PERCENT_BOUND, the ratio of the limit of quantification to the limit of detection (ICH Q2(R1): 10 sigma over 3.3 sigma). Between the two the credit rises linearly (the bound fraction is a difference of two measurements whose error does not change with it, so its signal-to-noise grows linearly).
LOD_SIGMAS = 3.3  # EXPERT_REVIEW: multiple of the paper's own standard deviation of the percent bound at which a percent bound is distinguished from zero (the limit of detection, ICH Q2(R1): 3.3 sigma). Used only when the paper states that standard deviation; the detection end is the larger of this and MIN_PERCENT_BOUND, so a noisy measurement moves the ramp up and a precise one never below the researched 5 percent.
LOQ_SIGMAS = 10.0  # EXPERT_REVIEW: multiple of the same standard deviation at which the percent bound is quantified, full credit (ICH Q2(R1): limit of quantification 10 sigma); the larger of this and QUANTIFIED_PERCENT_BOUND. 10 / 3.3 is about the 3 of QUANTIFIED_PERCENT_BOUND / MIN_PERCENT_BOUND.
FREE_OVER_LLOQ_FULL = 3.0  # EXPERT_REVIEW: free ligand concentration over the detector's stated lower limit of quantification for full agreement: the low quality-control sample of a validated bioanalytical method sits within 3 times the LLOQ (FDA Bioanalytical Method Validation 2018), where accuracy and precision are within 15 percent, so a free concentration of 3 x LLOQ or more is measured as well as the method is validated to.
FREE_OVER_LLOQ_ZERO = 1.0  # EXPERT_REVIEW: free concentration over the LLOQ at or below which the free ligand is not quantified (conflicting: the paper's own numbers show the free concentration at or under its detector's limit); between the two the degree rises linearly (the relative error of a concentration near the limit grows as the limit over the concentration, 20 percent at the LLOQ itself in the same guidance, 15 percent from 3 x LLOQ).
ADSORPTION_CORRECTION_RESIDUAL = 0.15  # EXPERT_REVIEW: share of a stated adsorption that remains as bias when the paper says it was checked and corrected: the correction is itself a measurement with the accuracy of the bioanalytical method, +-15 percent (FDA Bioanalytical Method Validation 2018), so 15 percent of the stated loss stays uncorrected. Not applied when the paper does not state the correction (the stated adsorption then counts whole).
MIN_PERCENT_UNBOUND = 1.0  # EXPERT_REVIEW: smallest percent unbound that is a measurable free fraction, for full agreement; below 1 percent the free concentration is near the limit of quantification of the detector and the percent unbound (and so the KD) is not reliable by dialysis.
FREE_FRACTION_ZERO_AGREEMENT_PERCENT = 0.0  # EXPERT_REVIEW: percent unbound at or below which the sheet takes the free fraction as not measurable (conflicting); no free ligand at all; in between the degree rises linearly.
MIN_EQUILIBRATION_H = 4.0  # EXPERT_REVIEW: shortest time (hours) that is taken as reaching equilibrium without a time course, for full agreement; 4 to 6 hours is the usual protocol of rapid equilibrium dialysis for plasma protein binding, and a shorter time is too short for most proteins (large proteins and tight binders need longer).
EQUILIBRATION_ZERO_AGREEMENT_H = 1.0  # EXPERT_REVIEW: time to equilibrium (hours) at or below which the sheet takes the binding as not at equilibrium (conflicting); within an hour a dialysis of a protein and a small ligand is far from equilibrium (about 58 percent of the way on the fastest device, see HALF_LIVES_AT_MIN_EQUILIBRATION).
HALF_LIVES_AT_MIN_EQUILIBRATION = 5.0  # EXPERT_REVIEW: half-lives of the approach to equilibrium that MIN_EQUILIBRATION_H stands for (the 4 h rapid equilibrium dialysis protocol is validated as within a few percent of equilibrium, 1 - 0.5^5 = 97 percent; the same five half-lives as the radioligand incubation). The free ligand crosses the membrane by first-order diffusion, so the share of equilibrium reached at t hours is 1 - 0.5^(5 t / 4); the degree is that share scaled to 0 at EQUILIBRATION_ZERO_AGREEMENT_H and 1 at MIN_EQUILIBRATION_H.
MIN_RECOVERY_PERCENT = 80.0  # EXPERT_REVIEW: smallest recovery (percent of the total ligand found in both chambers) of an acceptable mass balance, for full agreement (the usual acceptance is 80 to 120 percent; Waters et al. 2008, Di et al. 2012); below it the lost ligand biases the free concentration.
RECOVERY_ZERO_AGREEMENT_PERCENT = 50.0  # EXPERT_REVIEW: recovery (percent) at or below which the sheet takes the mass balance as failed (conflicting); when half of the ligand is lost the free concentration cannot be trusted; in between the degree rises linearly.
MAX_RECOVERY_PERCENT = 120.0  # EXPERT_REVIEW: largest recovery (percent) of an acceptable mass balance, for full agreement: the upper end of the same 80 to 120 percent acceptance; above it more ligand is found than was put in (evaporation, a volume shift, an analytical or a calibration error) and the free concentration is biased as much as by a loss.
RECOVERY_HIGH_ZERO_AGREEMENT_PERCENT = 150.0  # EXPERT_REVIEW: recovery (percent) at or above which the sheet takes the mass balance as failed (conflicting): an excess of 50 percent, the same deviation from 100 as RECOVERY_ZERO_AGREEMENT_PERCENT; in between the degree falls linearly.
MAX_ADSORPTION_PERCENT = 15.0  # EXPERT_REVIEW: largest nonspecific binding of the ligand to the membrane and the device (percent of the ligand) that does not bias the result, for full agreement; 10 to 15 percent is the usual limit, above it the apparent binding is inflated.
ADSORPTION_ZERO_AGREEMENT_PERCENT = 40.0  # EXPERT_REVIEW: adsorption (percent of the ligand) from which the sheet takes the binding as dominated by the device (conflicting); in between the degree falls linearly.
DEVICE_SHARE_OF_BOUND_FULL = 0.2  # EXPERT_REVIEW: for an ultrafiltration (the filter takes free ligand out of the filtrate, so the free fraction is read low by the adsorption): the largest share of the stated bound ligand that the adsorption could account for (adsorption x percent unbound / percent bound), for full agreement; the same 20 percent of the ligand the recovery acceptance tolerates.
DEVICE_SHARE_OF_BOUND_ZERO = 1.0  # EXPERT_REVIEW: share at or above which the adsorption alone could account for all of the stated binding (conflicting: the paper's own numbers show no binding beyond the device's loss); in between the degree falls linearly.
MAX_VOLUME_SHIFT_PERCENT = 10.0  # EXPERT_REVIEW: largest volume shift of the protein chamber (percent) that can be left uncorrected, for full agreement; above 10 percent the concentrations on the two sides differ by the shift (osmotic flow, Donnan effect) and the free fraction is biased.
VOLUME_SHIFT_ZERO_AGREEMENT_PERCENT = 30.0  # EXPERT_REVIEW: volume shift (percent) from which the sheet takes the concentrations of the two sides as no longer comparable (conflicting); in between the degree falls linearly.
MIN_SALT_MM = 100.0  # EXPERT_REVIEW: smallest concentration (mM) of monovalent salt that is taken to keep the Donnan effect small when the passage does not say the volume shift was corrected or measured (physiological buffers hold about 150 mM; at low ionic strength a charged protein shifts salt and water across the membrane); the full-agreement limit of the salt for a protein at PLASMA_PROTEIN_NM.
PLASMA_PROTEIN_NM = 600000.0  # EXPERT_REVIEW: the protein level MIN_SALT_MM is researched for: plasma, about 40 g/L albumin of 66.5 kDa, 0.6 mM. The Donnan excess of small ions goes as the protein's charge x its concentration over the salt, so the salt that keeps it as small scales with the protein concentration (the charge per molecule taken as albumin's, since it is not recorded); a protein not stated is taken at this level (the plasma protein binding case).
SALT_ZERO_AGREEMENT_MM = 0.0  # EXPERT_REVIEW: no salt stated at all: the buffer's own ions (not recorded) then decide the screening, so the salt says nothing about the shift (unknown, never a conflict: a low salt does not show a shift).
MAX_BOUND_OVER_PROTEIN = 1.0  # EXPERT_REVIEW: largest ratio of the bound ligand concentration to the protein concentration, for full agreement (the owner's rule: the bound ligand must not exceed the protein; for a one-site protein a larger ratio means the sites are used up and the ligand is depleted). Multiplied by the paper's own sites per protein (Bmax as a ratio, or Bmax in nM over the protein) when it states more than one.
BOUND_OVER_PROTEIN_ZERO_AGREEMENT = 3.0  # EXPERT_REVIEW: ratio of the bound ligand to the protein (per stated site, as above) from which the sheet takes the sites as exceeded beyond what several sites per protein could explain (conflicting); in between the degree falls linearly.
MIN_PROTEIN_OVER_KD = 0.2  # EXPERT_REVIEW: smallest ratio of the protein concentration to the KD at which a fraction bound can be measured, for full agreement; at 0.2 times the KD about 17 percent of a trace of ligand is bound (protein / (protein + KD)), above the 5 percent that shows binding.
PROTEIN_OVER_KD_ZERO_AGREEMENT = 0.05  # EXPERT_REVIEW: protein over KD at or below which the sheet takes the fraction bound as not measurable (conflicting); at 0.05 times the KD about 5 percent of a trace of ligand is bound, the minimum that shows binding; in between the degree rises linearly.
MIN_CONCENTRATIONS = 6  # EXPERT_REVIEW: fewest ligand concentrations of a saturation series for a KD (the usual series have six to ten; KD and Bmax are not both defined with fewer); the full-agreement limit of the count.
FIT_PARAMETERS = 2  # EXPERT_REVIEW: free parameters of the one-site fit of a dialysis saturation series (the KD and the Bmax: the bound ligand against the free ligand, Bmax * L / (KD + L)); with this many concentrations or fewer the curve passes through every point and nothing checks the fit: degree 0, supported, never conflicting (a short series is weaker evidence, not evidence against).
LOW_FACTOR = 0.5  # EXPERT_REVIEW: the lowest total ligand concentration must be at most this multiple of the KD for full agreement (about a third of the sites occupied, the usual design starts below the KD).
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: lowest total ligand concentration (multiple of the KD) from which the sheet takes the low end of the curve as not sampled (conflicting); at the KD half of the sites are already occupied.
HIGH_FACTOR = 4.0  # EXPERT_REVIEW: the highest total ligand concentration must be at least this multiple of the KD for full agreement (about 80 percent of the sites occupied, so that the plateau is defined by data).
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: highest total ligand concentration (multiple of the KD) at or below which the sheet takes the plateau as not reached (conflicting); at the KD only half of the sites are occupied.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days or preparations); cells or wells of one experiment do not count; full agreement from it. Below it (owner rule: replicates mean precision in every assay) the degree is sqrt(n / MIN_REPLICATES): the standard error of the mean over n independent experiments falls as 1 / sqrt(n); 1 experiment about 0.58, 2 about 0.82; never conflicting for a stated count.
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'recovery': 'a_dialysis_recovery_is_a_mass_balance_not_a_matrix_recovery', 'attributed_signal': 'a_dialysis_bound_fraction_is_not_an_attribution_fraction', 'total_signal': 'a_dialysis_bound_fraction_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_dialysis_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_dialysis_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _at_most(value, full, zero, refs):
    """Supported with degree 1.0 up to the full-agreement limit, falling linearly to 0 at the zero-agreement limit; conflicting from there on (a larger value is worse)."""
    if value >= zero:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, (zero - value) / (zero - full)))


def _at_least(value, full, zero, refs):
    """The same for a value that must not fall below its limit (a smaller value is worse)."""
    if value <= zero:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, (value - zero) / (full - zero)))


def _weakest(refs, *verdicts):
    """Conflicting when any verdict is; else supported with the smallest degree."""
    if any(v['status'] == 'conflicting' for v in verdicts):
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(v['degree'] for v in verdicts))


def _judge_binding_observed(native):
    # The direction is binary and is decided at MIN_PERCENT_BOUND (below it conflicting: the qualitative statement is 'interaction_not_detected').
    # Above it the credit rises linearly from 0 to 1 at QUANTIFIED_PERCENT_BOUND, so a fraction just above the detection limit is detected with little
    # credit and the row weight does not jump where the statement flips.
    # When the paper states the standard deviation of its percent bound, the ramp is read against that noise too: it starts at the larger of MIN_PERCENT_BOUND and
    # LOD_SIGMAS x that deviation and is full at the larger of QUANTIFIED_PERCENT_BOUND and LOQ_SIGMAS x it (a noisier measurement never raises the degree).
    # The direction (the qualitative statement) stays decided at MIN_PERCENT_BOUND alone: a percent bound within the noise is weak evidence, not evidence of no binding.
    percent, refs = native['percent_bound'], native['percent_bound_refs']
    if percent < MIN_PERCENT_BOUND:
        return _verdict('conflicting', refs)
    start, full = MIN_PERCENT_BOUND, QUANTIFIED_PERCENT_BOUND
    spread = native['percent_bound_spread']
    if spread is not None:
        start, full = max(start, LOD_SIGMAS * spread), max(full, LOQ_SIGMAS * spread)
        refs = list(dict.fromkeys([*refs, *native['percent_bound_spread_refs']]))
    return _verdict('supported', refs, max(0.0, min(1.0, (percent - start) / (full - start))))


def _approach(half_lives):
    """Share of the equilibrium reached after this many half-lives of a first-order approach."""
    return 1.0 - 0.5 ** half_lives


def _judge_equilibrium(native):
    # Shape: the exponential approach to equilibrium (see HALF_LIVES_AT_MIN_EQUILIBRATION), scaled to 0 at the zero-agreement time and 1 at the
    # researched time: concave, so 3 h loses little and 1.5 h loses most. Conflicting at or below EQUILIBRATION_ZERO_AGREEMENT_H, as before.
    hours, refs = native['equilibration_h'], native['equilibration_refs']
    if hours <= EQUILIBRATION_ZERO_AGREEMENT_H:
        return _verdict('conflicting', refs)
    reached = _approach(HALF_LIVES_AT_MIN_EQUILIBRATION * hours / MIN_EQUILIBRATION_H)
    floor = _approach(HALF_LIVES_AT_MIN_EQUILIBRATION * EQUILIBRATION_ZERO_AGREEMENT_H / MIN_EQUILIBRATION_H)
    return _verdict('supported', refs, min(1.0, (reached - floor) / (_approach(HALF_LIVES_AT_MIN_EQUILIBRATION) - floor)))


def _judge_recovery(native):
    # both sides of the researched 80 to 120 percent window: a loss and an excess bias the free concentration alike
    refs, recovery = native['recovery_refs'], native['recovery_percent']
    return _weakest(refs, _at_least(recovery, MIN_RECOVERY_PERCENT, RECOVERY_ZERO_AGREEMENT_PERCENT, refs), _at_most(recovery, MAX_RECOVERY_PERCENT, RECOVERY_HIGH_ZERO_AGREEMENT_PERCENT, refs))


def _judge_adsorption(native):
    # The absolute ramp always; for an ultrafiltration also the share of the stated bound ligand the filter's loss of free ligand could account for
    # (adsorption x percent unbound / percent bound), the weaker of the two. In an equilibrium dialysis with both chambers measured the loss mostly
    # lowers the recovery (judged there), so only the absolute ramp applies.
    # A paper that says the adsorption was checked and corrected leaves only ADSORPTION_CORRECTION_RESIDUAL of the stated loss as bias; both the ramp and the share use that.
    refs, adsorbed = native['adsorption_refs'], native['adsorption_percent']
    if native['adsorption_corrected'] == 'yes':
        refs, adsorbed = list(dict.fromkeys([*refs, *native['adsorption_corrected_refs']])), adsorbed * ADSORPTION_CORRECTION_RESIDUAL
    absolute = _at_most(adsorbed, MAX_ADSORPTION_PERCENT, ADSORPTION_ZERO_AGREEMENT_PERCENT, refs)
    unbound = native['percent_unbound']
    if native['separation_method'] != 'ultrafiltration' or unbound is None or unbound >= PERCENT_FULL:
        return absolute
    refs = list(dict.fromkeys([*refs, *native['percent_unbound_refs']]))
    share = adsorbed * unbound / PERCENT_FULL / (PERCENT_FULL - unbound)
    return _weakest(refs, absolute, _at_most(share, DEVICE_SHARE_OF_BOUND_FULL, DEVICE_SHARE_OF_BOUND_ZERO, refs))


def _judge_volume_shift(native):
    return _at_most(native['volume_shift_percent'], MAX_VOLUME_SHIFT_PERCENT, VOLUME_SHIFT_ZERO_AGREEMENT_PERCENT, native['volume_shift_refs'])


def _judge_salt(native):
    # Shape: the Donnan excess of small ions (and the water that follows them) goes as the protein's charge x its concentration over the salt. The
    # researched MIN_SALT_MM is for plasma-level protein (PLASMA_PROTEIN_NM), so the salt that keeps the excess as small is MIN_SALT_MM scaled by the
    # stated protein over that level (plasma level when the protein is not stated); below it the credit is one over the relative excess, salt / that
    # salt. A low salt only fails to rule a shift out and never shows one, so it is never conflicting; no salt stated is unknown (the buffer's own
    # ions, not recorded, then decide). No unknown weight enters the degree.
    salt, refs = native['salt_mM'], native['salt_refs']
    if salt <= SALT_ZERO_AGREEMENT_MM:
        return _verdict('unknown', refs)
    protein = PLASMA_PROTEIN_NM if native['protein_nM'] is None else native['protein_nM']
    return _verdict('supported', refs, min(1.0, salt / (MIN_SALT_MM * protein / PLASMA_PROTEIN_NM)))


def _sites_per_protein(native):
    """The paper's own number of sites per protein (Bmax as a ratio, or Bmax in a concentration over the protein), with its refs; (None, []) when not stated."""
    bmax = native['quantities']['bmax']
    if bmax['status'] != 'point':
        return None, []
    if bmax['unit'] == 'ratio':
        return bmax['value'], list(bmax['source_refs'])
    return bmax['value'] * NM_PER_UNIT[bmax['unit']] / native['protein_nM'], list(bmax['source_refs'])


def _judge_depletion(native):
    # The researched limits are for one site per protein; a paper that states more sites per protein (its own Bmax) scales them, never below one site.
    refs = native['bound_over_protein_refs']
    sites, site_refs = _sites_per_protein(native)
    if sites is None or sites <= 1.0:
        return _at_most(native['bound_over_protein'], MAX_BOUND_OVER_PROTEIN, BOUND_OVER_PROTEIN_ZERO_AGREEMENT, refs)
    return _at_most(native['bound_over_protein'], MAX_BOUND_OVER_PROTEIN * sites, BOUND_OVER_PROTEIN_ZERO_AGREEMENT * sites, list(dict.fromkeys([*refs, *site_refs])))


def _judge_protein_level(native):
    return _at_least(native['protein_over_kd'], MIN_PROTEIN_OVER_KD, PROTEIN_OVER_KD_ZERO_AGREEMENT, native['protein_over_kd_refs'])


def _judge_free_fraction(native):
    # The percent unbound against the researched fraction limits, and, when the paper states the detector's limit of quantification, the free concentration
    # against that limit (the paper's own scale); the weaker of the two counts. Either alone is judged alone.
    verdicts = []
    if native['percent_unbound'] is not None:
        verdicts.append(_at_least(native['percent_unbound'], MIN_PERCENT_UNBOUND, FREE_FRACTION_ZERO_AGREEMENT_PERCENT, native['percent_unbound_refs']))
    if native['free_over_lloq'] is not None:
        verdicts.append(_at_least(native['free_over_lloq'], FREE_OVER_LLOQ_FULL, FREE_OVER_LLOQ_ZERO, native['free_over_lloq_refs']))
    refs = list(dict.fromkeys(ref for verdict_refs in (native['percent_unbound_refs'] if native['percent_unbound'] is not None else [], native['free_over_lloq_refs'] if native['free_over_lloq'] is not None else []) for ref in verdict_refs))
    return _weakest(refs, *verdicts)


def _occupancy(over_kd):
    """One-site occupancy of a ligand at this multiple of the KD: x / (1 + x), the share of the binding curve reached (0.5 at the KD, 0.8 at 4 x KD)."""
    return over_kd / (1.0 + over_kd)


def _judge_concentration_series(native):
    # Shape of the count: linear in the residual degrees of freedom of the one-site fit (count - FIT_PARAMETERS). Each dialysis cell of the series
    # is a separate equilibrium with its own free and total measurement; every cell beyond the two the KD and the Bmax take is one more independent
    # check that the bound ligand saturates, and the variance of the fitted KD falls about as one over those degrees of freedom: the researched six
    # leave four, five leave three (0.75), at two or fewer the curve is only drawn through the points (degree 0). A short series is weaker evidence,
    # not evidence against: the count never makes the criterion conflicting (the span ramps still can).
    count_refs = native['concentration_count_refs']
    degrees = []
    if native['concentration_count'] is not None:
        degrees.append(max(0.0, min(1.0, (native['concentration_count'] - FIT_PARAMETERS) / (MIN_CONCENTRATIONS - FIT_PARAMETERS))))
    if native['concentration_low_over_kd'] is None:
        return _verdict('unknown', [])      # the span cannot be read: a count alone has nothing to bracket
    refs = native['concentration_span_refs']
    # Both ends are judged on the one-site occupancy x / (1 + x) of the ligand over the KD (the share of the binding curve covered), between the same
    # researched ends (LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR taken through the same map); the occupancy map is
    # increasing, so the conflicting boundaries (at the KD) do not move. No dialysis-specific reason for linear-in-x was found: the series is still
    # a ligand-over-KD ratio read against the one-site isotherm, as in the sixteen other assays.
    low = _at_most(_occupancy(native['concentration_low_over_kd']), _occupancy(LOW_FACTOR), _occupancy(LOW_ZERO_AGREEMENT_FACTOR), refs)
    high = _at_least(_occupancy(native['concentration_high_over_kd']), _occupancy(HIGH_FACTOR), _occupancy(HIGH_ZERO_AGREEMENT_FACTOR), refs)
    if 'conflicting' in (low['status'], high['status']):
        return _verdict('conflicting', refs)
    refs = list(dict.fromkeys([*refs, *count_refs])) if degrees else refs      # a count that set the degree is cited with the span
    return _verdict('supported', refs, min(low['degree'], high['degree'], *degrees))


def _judge_replicates(native):
    # Shape: sqrt(n / MIN_REPLICATES), capped at 1. The errors of a dialysis that one experiment cannot show (the protein or plasma preparation, the lot
    # of membranes and their nonspecific binding, the day-to-day calibration of the LC-MS/MS or the counter) average down over independent experiments
    # as 1 / sqrt(n) (the same sd^2 / n this converter uses for the variance), so the degree is the precision at n relative to that at the researched
    # count. One experiment is a real measurement: weaker, never conflicting. Independence not stated is unknown (a stated no is the grader's conflicting).
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(max(native['replicate_count'], 0) / MIN_REPLICATES)))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('binding_observed', 'percent_bound_recorded_for_the_sheet'): _judge_binding_observed, ('equilibrium', 'equilibration_time_recorded_for_the_sheet'): _judge_equilibrium,
          ('recovery', 'recovery_recorded_for_the_sheet'): _judge_recovery, ('device_adsorption', 'adsorption_recorded_for_the_sheet'): _judge_adsorption,
          ('volume_shift', 'volume_shift_recorded_for_the_sheet'): _judge_volume_shift, ('volume_shift', 'salt_recorded_for_the_sheet'): _judge_salt,
          ('ligand_depletion', 'bound_over_protein_recorded_for_the_sheet'): _judge_depletion, ('protein_level', 'protein_over_kd_recorded_for_the_sheet'): _judge_protein_level,
          ('free_fraction_measurable', 'percent_unbound_recorded_for_the_sheet'): _judge_free_fraction, ('free_fraction_measurable', 'free_over_lloq_recorded_for_the_sheet'): _judge_free_fraction, ('concentration_series', 'concentration_series_recorded_for_the_sheet'): _judge_concentration_series,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _interaction(graded):
    """(the qualitative statement of the record, its refs): the grader's own when the fact binding_detected states it; else, when a stated fraction decides, the sheet's reading of the judgement of binding_observed."""
    native = graded['native']
    if graded['reasons']['binding_observed'] == 'percent_bound_recorded_for_the_sheet':
        return ('detected' if _criterion(graded, 'binding_observed')['status'] == 'supported' else 'not_detected'), list(native['percent_bound_refs'])
    return native['interaction'], list(native['interaction_refs'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}


def _binding_constant(native):
    """The name of the binding constant the effect carries (kd, else ki), or None."""
    return next((name for name in BINDING_CONSTANTS if native[name + '_nM'] is not None), None)


def _variance(graded, constant_name):
    """Return (variance_nM_squared or None, reason or None, refs)."""
    native = graded['native']
    if constant_name is None:
        return None, 'no_effect_to_carry_a_variance', []
    name = constant_name + '_spread'
    spread = native['quantities'][name]
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, name + '_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = spread['value'] * NM_PER_UNIT[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        replicates = _criterion(graded, 'replicates')
        # sd^2 / n is a variance of the estimate only from the researched MIN_REPLICATES independent experiments (full agreement); fewer give a partial
        # degree to sampling_basis, but an sd from one or two degrees of freedom is too unstable to set the precision of the pooled effect.
        if replicates['status'] != 'supported' or replicates['degree'] < 1.0:
            return None, 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_dialysis(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    constant_name = _binding_constant(native)
    quantitative = constant_name is not None
    if quantitative:
        constant = native['quantities'][constant_name]
        quantities['effect'] = _operand(native[constant_name + '_nM'], 'nM', 'dialysis_' + constant_name + ':' + ref, constant['source_refs'], constant['origin'], constant_name)
    variance, variance_reason, variance_refs = _variance(graded, constant_name)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'dialysis_variance:' + ref, variance_refs, 'derived', constant_name + '_spread')
    if not quantitative:
        null_components['effect'] = 'qualitative_assay_reports_no_binding_constant'
        null_components['effect_variance'] = 'qualitative_assay_reports_no_binding_constant'
    null_components.update(NULL_REASONS)
    interpretations = {}
    for sheet_criterion, members in CRITERIA_MAP.items():
        # the support of the quotes (kept by the grader) gives or lowers the degree of a supported member; it never changes a status
        graded_members = [apply_support(_criterion(graded, m), native['support'][m]) for m in members if graded['criteria'][m]['status'] != 'not_applicable']
        if not graded_members:
            continue
        statuses = [m['status'] for m in graded_members]
        status = 'conflicting' if 'conflicting' in statuses else 'unknown' if 'unknown' in statuses else 'supported'
        refs = list(dict.fromkeys(r for m in graded_members for r in m['support_refs']))
        interpretations[sheet_criterion] = {'status': status, 'support_refs': refs if status == 'supported' else []}
        degrees = [m['degree'] for m in graded_members if 'degree' in m]
        if status == 'supported' and degrees:
            interpretations[sheet_criterion]['degree'] = min(degrees)      # the weakest member: a degree of a member is not averaged away
    if variance is not None:
        variance_fields = [constant_name + '_spread'] + (['replicate_count'] if native['spread_kind'] == 'standard_deviation' else [])
        interpretations['variance_correspondence'] = apply_support({'status': 'supported', 'support_refs': variance_refs}, [native['quantities'][n].get('support') for n in variance_fields if native['quantities'][n].get('support')])
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter' if quantitative else 'relative_binding_response', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['ligand_preparation_ref'], 'immobilized_preparation_ref': preparations['protein_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    converted = {'version': VERSION, 'experiment_type': 'dialysis', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': None}
    if quantitative:
        converted['direction_field_support'] = native['quantities'][constant_name]['support']      # the support class of the binding-constant operand, the field that fixes the effect
    else:
        interaction, interaction_refs = _interaction(graded)
        converted['qualitative_effect'] = {'statement': STATEMENTS[interaction], 'support_refs': interaction_refs, 'percent_bound': native['percent_bound']}
        if interaction is not None:
            if graded['reasons']['binding_observed'] == 'percent_bound_recorded_for_the_sheet':
                # the statement is the sheet's reading of the stated fraction: the support class of the first stated field the percent bound is taken from
                converted['direction_field_support'] = next(native['quantities'][name]['support'] for name, _ in BOUND_FROM if native['quantities'][name]['status'] == 'point')
            else:
                converted['direction_field_support'] = native['support']['binding_observed'][0]      # the fact binding_detected states it (first of the criterion's reads; its support is set whenever it is answered yes or no)
    return converted
