"""ELISA converter: turns the ELISA grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_elisa.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp and FCS converters fill), the
dependence keys the merger needs, and for every sheet component that a plate
assay cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            the reported binding constant in nM (point operand): the
                  apparent KD of a saturation titration, or, when the record has
                  no KD, the Ki of a competition (the measurement key names it:
                  elisa_kd or elisa_ki). Neither given leaves effect null; an EC50
                  or an IC50 alone is a half-maximal concentration, not a
                  dissociation constant (it depends on the coating, the detection
                  and the competing ligand) and is not carried into the effect.
                  With no effect operand the result is the experiment's stated yes/no
                  result (fact binding_detected): 'qualitative_effect' carries its
                  statement (interaction_detected, interaction_not_detected, or
                  interaction_not_stated when the passage states neither) and the
                  spans that state it.
effect_variance   variance of that constant, nM_squared, only when the
                  source's spread (kd_spread for a KD, ki_spread for a Ki)
                  allows it: standard_error -> se^2; standard_deviation ->
                  sd^2 / n, and only when the replicates criterion is
                  supported (n independent experiments); confidence_interval
                  -> not converted (needs its level and degrees of freedom).
                  Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).

Dependence keys handed to the merger (the same four keys as the other
converters): analyte_preparation_ref = the titrant,
immobilized_preparation_ref = the coated partner, surface_ref = None (the plate is
not a surface reference), dataset_ref = the dataset.

Criteria mapping (ELISA criteria -> sheet criteria), declared in CRITERIA_MAP
------------------------------------------------------------------------------
binding_controls              blank_subtraction + specificity_control + avidity +
                              coated_protein_activity + detection_interference
binding_regime                saturation + concentration_series + equilibrium +
                              wash_dissociation + direct_vs_competition
binding_parameter_definition  fit_model
calibration_applicability     signal_window + detector_range (the plateau over the
                              background and the linear range of the reader: this
                              method's counterpart of the SPR Rmax check)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Each researched value is kept as an EXPERT_REVIEW constant with its reason, and none of them is a pass/fail cut: the degree
reaches full credit at the researched value and falls smoothly (no step) towards a researched zero-agreement value, giving partial credit in between; at or past the
zero-agreement value the paper's own number shows the standard is not met (conflicting, no degree). A criterion at or better than its researched value is judged
exactly as before the softening.
  signal_window          (kept ramp, log scale since the 2026-11-21 range review) plateau over background: full at MIN_SIGNAL_OVER_BACKGROUND, falling with the log
                         of the ratio to SIGNAL_WINDOW_ZERO_AGREEMENT (a plateau that is the background).
  direct_vs_competition  (kept ramp, log scale since the review) fold gap of the KD and the Ki: full up to AGREEMENT_FACTOR, falling with the log of the fold to
                         AGREEMENT_ZERO_FACTOR.
  concentration_series   (kept ramps, occupancy scale since the review) lowest concentration over the constant LOW_FACTOR -> LOW_ZERO_AGREEMENT_FACTOR, highest
                         HIGH_FACTOR -> HIGH_ZERO_AGREEMENT_FACTOR, each linear in the one-site occupancy x / (1 + x) reached there;
                         (softened) the count: full at MIN_CONCENTRATIONS, falling linearly in the residual degrees of freedom of the paper's stated fit model to its
                         number of free parameters (FIT_FREE_PARAMETERS_BY_MODEL; CONCENTRATIONS_ZERO_AGREEMENT, the four-parameter curve, when the model is
                         four-parameter, 'other' or not stated; no credit there, never conflicting: a short series is weaker evidence, not evidence against). The
                         smallest of the three degrees counts; with the span not recorded the criterion is unknown (a count alone does not say whether the constant
                         is bracketed).
  detector_range         (softened) plateau absorbance: full at or below MAX_LINEAR_OD, falling with the stray-light error (which grows as 10 to the power of the
                         absorbance) to zero at MAX_READABLE_OD, the end of a plate reader's photometric range. A readout stated as chemiluminescence or
                         fluorescence has no absorbance range to judge: unknown (since the review).
  replicates             (softened) independent experiments (independence yes): degree min(1, sqrt(n / MIN_REPLICATES)), the precision of the mean constant over n
                         independent plates or days; never conflicting for a stated count; independence not stated: unknown; stated no: the grader's conflicting.
  equilibrium            (a curve since the 2026-11-21 decision A; only when the paper's own equilibrium fact is unknown) with t the stated incubation and the reported
                         constant: T_FAST = EQUILIBRATION_REFERENCE_MIN x EQUILIBRATION_REFERENCE_NM / constant (the old limit without its floor), d_kon =
                         log(t / T_FAST) / log(KON_FAST_PER_M_S / KON_SLOW_PER_M_S) clipped to 1, d_floor = min(1, t / MIN_INCUBATION_MIN); supported with
                         degree min(d_floor, d_kon) and the refs of the incubation and the constant; conflicting only at t <= T_FAST (d_kon <= 0); no
                         constant stated: unknown (also below the floor).

Range review (2026-11-21, SOP step 3; Q1 what it catches, Q2 general practice or lab/instrument-specific, Q3 absolute or relative and whether the
relative quantity is in the grader facts, Q4 how badly a wrong value misleads and whether the shape fits, Q5 consistency with the other binding assays)
-------------------------------------------------------------------------------------------------------------------------------------------------------
MIN_SIGNAL_OVER_BACKGROUND 5 -> SIGNAL_WINDOW_ZERO_AGREEMENT 1.
  Q1 a plateau within the scatter of the blank wells (or a "binding" that is plate background), so the bottom, the top and the constant are undefined.
  Q2 general immunoassay practice (Assay Guidance Manual, Immunoassay Methods chapter; Crowther, The ELISA Guidebook, 2nd ed. 2009): with a
  well-to-well CV of about 10 percent proportional to the signal, Z' = 1 - 3 CV (r + 1) / (r - 1) is 0.55 at r = 5, just past the 0.5 of an
  excellent assay (Zhang, Chung and Oldenburg 1999 J Biomol Screen 4:67); lower than AlphaScreen's 10 because blank wells read 0.05 to 0.1 OD and
  the reader caps the top near 2 to 3 OD, so ELISA windows of 10 to 40 are the usual ceiling. MISTAKE DECLARED: the old comment's reason ("a few
  well-scatter units" below 5x) was wrong arithmetic (0.3 OD over a 0.06 OD blank is about 40 blank SDs); replaced by the Z' reason.
  Q3 already relative to the paper's own blank; the better scale, the window over the blank's SD, needs the blank SD or CV (GAP below).
  Q4 a window is a fold: going from 1 to 2 separates no curve from a visible one ((r - 1) / (r + 1), which sets Z', goes 0 -> 0.33), 4 to 5
  changes little (0.60 -> 0.67); the linear ramp did the reverse (S/B 2 got 0.25). CHANGED: linear -> log of the ratio (2x 0.43, 3x 0.68),
  values kept. Q5 now the same shape as AlphaScreen's signal window.
MAX_LINEAR_OD 2 -> MAX_READABLE_OD 4, linear in 10^OD.
  Q1 a plateau read outside the reader's linear range, whose top is compressed. MISTAKE DECLARED: the old comment said this "raises the apparent
  KD"; a concave compression makes the curve reach half its (lowered) top at a LOWER concentration, so the apparent constant reads TIGHTER
  (a magnitude error towards stronger binding); comment corrected. At OD above about 3 the colour of a stopped TMB or OPD reaction can also be
  substrate-limited, so the "plateau" may be chemistry, not saturation. Q2 instrument-specific but common to microplate photometers (specification
  0 to 4 OD, about 1 percent to 2 OD, a few percent to 3 OD; immunoassay guidance keeps the top below about 2 OD). Q3 absolute is right: it is
  a property of the reader, not of the paper; a paper's own stated reader range would be better (rarely stated; GAP below). Q4 stray light of
  about 1e-4 bends the reading by about 1.4 percent at 3 OD and 7.5 percent at 4 OD, and the substrate limit adds to it near the top: the
  10^OD shape is gentle to 3 OD (0.91) and steep towards 4, as it should be. KEPT (values and shape). Two fixes: (a) MISTAKE DECLARED: 10.0 **
  OD overflowed (OverflowError) for any plateau above about 308 "OD" (for example counts mislabelled as OD), crashing the conversion; the zero
  end is now checked first. (b) The OD scale applies only to an absorbance readout: readout_signal stated chemiluminescence or fluorescence ->
  unknown (the record's unit vocabulary holds only OD, so such a number would not be an absorbance). Q5 no other binding assay reads absorbance.
MIN_CONCENTRATIONS 8 -> CONCENTRATIONS_ZERO_AGREEMENT 4 (now per stated model: FIT_FREE_PARAMETERS_BY_MODEL).
  Q1 too few points for the fitted curve, so the constant is set by the model, not the data. Q2 general dose-response practice (Sebaugh 2011
  Pharm Stat 10:128; Assay Guidance Manual: 8 to 12 points; a 12-column plate row is the usual series). Q3 the count is absolute, but the zero end
  is the number of free parameters of the model the paper itself states (fit_model is in the grader facts): a one-site (1:1) fit with the blank
  subtracted has 2 (Bmax, KD), a Hill fit 3, a one-site competition 3 (top, bottom, IC50), a four-parameter logistic 4. CHANGED: zero end 4 for
  every model -> the stated model's count (4PL, 'other' and unstated keep 4, the stricter end); 8 kept as full credit for every model, because
  ELISA well noise (5 to 10 percent CV, not at equilibrium) needs more points than a biosensor's (SPR full at 5). A 1:1 fit to 5 points now
  scores 0.5, not 0.25. Q4 linear in residual degrees of freedom, as SPR, AlphaScreen. Q5 never conflicting for a short series (kept); SPR also
  takes the zero end from the stated analysis; AlphaScreen keeps a fixed 4 (flagged).
LOW_FACTOR 0.2 -> LOW_ZERO_AGREEMENT_FACTOR 1.0, HIGH_FACTOR 10 -> HIGH_ZERO_AGREEMENT_FACTOR 1.0.
  Q1 a series that does not reach the lower baseline or the upper plateau, so the fit extrapolates them. Q2 general binding practice (0.1x to 10x
  the constant; Hulme and Trevethick 2010 Br J Pharmacol 161:1219; Jarmoskaite et al. 2020 eLife 9:e57264). Q3 relative to the paper's own
  constant (concentration_low_over_constant and concentration_high_over_constant are in the grader facts): right. Q4 what each end shows is the
  occupancy reached there, x / (1 + x): 5x already shows 83 percent, so the linear-in-x ramp gave 5x only 0.44 (steep where little changes) and
  the low end at 0.6x 0.5 (too lenient: 37.5 percent of the curve is unseen). CHANGED: linear in x -> linear in occupancy (5x 0.81, 2x 0.41;
  0.6x 0.375), values kept. Q5 now the same shape as SPR, AlphaScreen and CETSA; HIGH_FACTOR 10 kept (SPR uses 5; on the occupancy scale the gap
  costs 0.19), because a plate titration's top is also where non-specific adsorption rises, so the plateau must be seen clearly.
MIN_INCUBATION_MIN 30 (with the new EQUILIBRATION_REFERENCE_NM 1).
  Q1 a constant read before the binding reached equilibrium (an apparent affinity too weak, worst for tight binders). Q2 30 minutes to 2 hours is
  protocol practice (Crowther 2009), not physics: the reaction needs about five half-lives, 5 ln2 / (kon (C + KD)) (Jarmoskaite et al. 2020),
  which scales with 1 / KD; on a coated well the solution must also reach the surface by diffusion (unstirred, about 0.5 mm in 30 minutes for a
  protein), so the plate needs at least the protocol time even when the reaction is fast. Q3 relative to the paper's own constant (constant_nM is
  in the grader facts) for the reaction; the transport part needs the well volume, shaking and the coated amount (GAP below). Q4 the old absolute
  30 minutes never flagged a 2-hour step for a 10 pM constant (about two days needed at a fast kon of 1e6 per M per s). CHANGED: the conflict
  limit is MIN_INCUBATION_MIN x max(1, EQUILIBRATION_REFERENCE_NM / constant): 30 minutes is kept as the floor (protocol and transport, so every
  case the old rule flagged is still flagged) and lengthened for constants tighter than 1 nM. Still no degree (no full-credit end). Q5
  AlphaScreen uses the same reaction scale without the floor (a homogeneous assay has no surface to reach); no unknown weight is used.
DECISION A (2026-11-21), the incubation time as a curve: MIN_INCUBATION_MIN 30 (floor) + EQUILIBRATION_REFERENCE_NM 1 / _MIN 30 + KON_FAST_PER_M_S 1e6 -> KON_SLOW_PER_M_S 1e4 (NEW).
  Q1 as above, plus the cliff itself: below the needed time conflicting, above it unknown, so 29 and 31 minutes at 1 nM scored very differently and a
  step 100 times too short for a slow pair scored the same as a long one. Q2 the researched fast end (1e6, T_FAST) is kept; the slow end 1e4 is a
  judgement (from memory: Schreiber, Haran and Zhou 2009; Foote and Eisen 1995), owner to confirm. Q3 relative to the paper's own constant
  (constant_nM and now constant_refs are in the grader facts) for the reaction; the floor stays absolute (transport needs the well volume and shaking, a
  GAP kept). The constant may be an EC50 or IC50 when no KD or Ki is reported (the grader's order); a half-maximal concentration scales the time
  only roughly, as before. Q4 association rates span decades, so the degree is the log share of the plausible rates the incubation covers: gentle
  over two decades, zero only where even the fastest rate has not equilibrated; the floor is proportional (a 15-minute step scores 0.5 of the floor)
  and the smaller of the two counts. Q5 AlphaScreen and the other binding assays take the same reaction scale; no unknown weight is inside a degree.
  The old conflict limit is the zero end (kept: t <= T_FAST conflicts, so at exactly 1 nM a 30-minute step is now conflicting where it was unknown),
  and the old floor no longer conflicts alone: no constant and a short step is unknown. Worked: 1 nM (T_FAST 30, T_SLOW 3000 minutes) t 60 -> 0.15,
  t 120 -> 0.30, t 1440 (overnight) -> 0.84; 10 pM (T_FAST 3000, T_SLOW 300000) 24 h conflicting, 6000 minutes 0.15; 1 uM (T_FAST 0.03, T_SLOW 3)
  t 30 -> 1.0, t 15 -> 0.5 (the floor alone), t 1 -> 0.033.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a constant from one plate, whose plate-to-plate and day-to-day spread (the larger part of an ELISA's error: inter-assay CV above intra-assay
  CV) is unseen. Q2 general (Vaux, Fidler and Cumming 2012 EMBO Rep 13:291: independent repeats, not wells). Q3 absolute count. Q4 precision of
  the mean (1 / sqrt(n)), the same sd^2 / n as the variance; 2 experiments keep 0.82. KEPT. Q5 exactly the shared replicate rule.
AGREEMENT_FACTOR 3 -> AGREEMENT_ZERO_FACTOR 10.
  Q1 a saturation KD and a competition Ki that describe different events (avidity of the coat, detection interference, a wrong Cheng-Prusoff
  input). Q2 general (Cheng and Prusoff 1973 Biochem Pharmacol 22:3099; orthogonal estimates agree to two- to threefold); the 3 and 10 are a
  judgement, shared with FP, FRET, MST and AlphaScreen. Q3 already relative (the paper's two constants); the tracer concentration and its KD
  behind the Ki would let the sheet check the conversion (GAP below). Q4 binding constants are log-normal and the strength anchors are on the log
  scale; linear in fold was too lenient between the ends (6-fold 0.57 linear, 0.42 log). CHANGED: linear -> log of the fold, values kept.
  Q5 now as SPR, BLI and AlphaScreen.
ABSORBANCE_BASE 10: FIXED_BY_DEFINITION, not reviewed.
Unknown weight: WEIGHT_UNKNOWN_BY_TYPE['elisa'] 0.70 (binding_controls 0.65, binding_regime 0.65) in literature_row_contract.py; no degree here uses it.
Grader gaps of the range review, and what was done (2026-11-21, gap pass):
  ADDED (form field, grader fact, converter judgement, extraction field, passages):
  - the plate reader's stated linear range (detector_linear_limit, OD): detector_range is now relative to the paper's own stated limit when it gives
    one (full credit up to it, then the same 10^OD stray-light shape to MAX_READABLE_OD, a stated limit above MAX_READABLE_OD is cut to it); with no
    stated limit the researched MAX_LINEAR_OD stays. Whether the stated plateau is raw or blank-subtracted was NOT added: papers rarely say, and
    the blank is a small fraction of a plateau of 1 OD or more (error below 0.1 OD).
  - koff and the total wash duration (koff, wash_duration): wash_dissociation is judged when the fact is not stated: retained = exp(-koff * t),
    degree linear in koff * t from full at WASH_RETAINED_FULL to 0 (conflicting) at WASH_RETAINED_ZERO (EXPERT_REVIEW constants above). A stated
    fact still decides first. Not added: a dissociation time course or the detection step time (the number of 1/e lifetimes needs one koff and one time).
  - the displaced ligand's concentration and its KD (tracer_concentration, tracer_kd): the grader computes the Cheng-Prusoff Ki from the IC50
    (arithmetic of stated numbers); direct_vs_competition then also compares the KD with that Ki when no Ki is reported, and a reported Ki with the
    Cheng-Prusoff Ki (the paper's own conversion); the weaker of the folds counts, same log scale and AGREEMENT constants.
  NOT ADDED, with the reason:
  - the blank wells' SD or CV (signal over noise or Z'): a Z' needs the SD of the plateau wells too, a binding paper almost never states either, and
    the fold over the paper's own blank (already recorded, with the researched Z' reason) is the same judgement at the typical 10 percent CV.
  - a chemiluminescent or fluorescent signal in its own unit and the reader's saturation level: the level is instrument-specific (counts or RLU
    without a shared scale), so no scale would be researched; such a readout stays unknown for detector_range, as it is.
  - the well volume, shaking and the coated amount per well (transport time, titrant depletion): three numbers a paper almost never gives, and the
    coating concentration is already recorded; the equilibrium floor and its scaling with 1 / KD stay.
  - whether a baseline term was fitted in a 1:1 fit: rarely stated, and it moves the zero end of the count by one point, which changes the degree of
    a 5-point series by 0.25 at most.
A degree is attached when it is below full credit (and, as before, always for the kept ramps); a sheet criterion that is supported carries the smallest degree of its
members that have one (the sheet reads no degree; it travels with the interpretation and the merger carries it per result).
Quote support (literature_quote_support.py, SUPPORT_DEGREE: direct 1.0, implied 0.7, about_something_else 0.3, defined once there with the
reason of each): a supported sheet criterion whose members read a stated field with support 'implied' or 'about_something_else' (the grader's
native['support'], per member) has its degree multiplied by the weakest factor; where it had no degree the degree becomes that factor; 'direct' leaves it as it
is. The variance_correspondence reads the support of the spread, its kind and, for a standard deviation, the replicate count. Support never
changes a status, and a conflicting or unknown criterion keeps no degree.
Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet
criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported,
assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_elisa_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_elisa_converted_v1'
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
BINDING_CONSTANTS = ('kd', 'ki')
CRITERIA_MAP = {'binding_controls': ('blank_subtraction', 'specificity_control', 'avidity', 'coated_protein_activity', 'detection_interference'), 'binding_regime': ('saturation', 'concentration_series', 'equilibrium', 'wash_dissociation', 'direct_vs_competition'), 'binding_parameter_definition': ('fit_model',), 'calibration_applicability': ('signal_window', 'detector_range'), 'sampling_basis': ('replicates',)}
MIN_SIGNAL_OVER_BACKGROUND = 5.0  # EXPERT_REVIEW: smallest ratio of the plateau absorbance to the background absorbance for the curve to have a defined bottom and top; with a well-to-well CV of about ten percent proportional to the signal, Z' = 1 - 3 CV (r + 1) / (r - 1) is 0.55 at r = 5, just past the 0.5 of an excellent assay (Zhang, Chung and Oldenburg 1999 J Biomol Screen 4:67); blank wells read about 0.05 to 0.1 OD and the reader caps the top near 2 to 3 OD, so ELISA windows of 10 to 40 are the usual ceiling.
SIGNAL_WINDOW_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: plateau-over-background ratio at or below which the sheet takes the curve as having no window at all (conflicting); a ratio of 1 is a plateau that is the background; in between the degree rises with the log of the ratio (a window is a fold: the first doubling separates no curve from a visible one).
MAX_LINEAR_OD = 2.0  # EXPERT_REVIEW: highest absorbance (OD) of a plateau read as inside the linear range of a plate reader; the response of a plate reader departs from the Beer-Lambert line above about 2 OD, and a curve read above it is compressed at the top, so it reaches half its lowered top at a lower concentration: the apparent KD or EC50 reads tighter than it is.
MAX_READABLE_OD = 4.0  # EXPERT_REVIEW: absorbance (OD) at which a plateau carries no agreement (conflicting): the photometric range of microplate absorbance readers ends at about 4 OD (typical specification 0 to 4 OD, linearity about 1 percent to 2 OD and a few percent to 3 OD); at 4 OD one part in ten thousand of the light reaches the detector, the size of the reader's stray light, so the reading no longer follows the absorbance.
WASH_RETAINED_FULL = 0.9  # EXPERT_REVIEW: share of the bound complex still on the plate after the ligand-free washes (exp(-koff * wash time)) at or above which the loss is not judged: a 10 percent loss is inside the 5 to 10 percent well-to-well CV of a plate readout and the curve shape is kept (separation-step dissociation is the known bias of non-equilibrium readouts, Hulme and Trevethick 2010 Br J Pharmacol 161:1219). Below it the degree falls linearly in koff * t (the number of 1/e lifetimes elapsed).
WASH_RETAINED_ZERO = 0.1  # EXPERT_REVIEW: share retained at or below which the sheet takes the washes as having removed the complex (conflicting): with only 10 percent left (2.3 lifetimes, about 3.3 half-lives) the signal reports only the slowest-dissociating part of the population, not the equilibrium occupancy; the physics of a first-order decay, no literature cut. No unknown weight is used.
SECONDS_PER_MINUTE = 60.0  # FIXED_BY_DEFINITION: koff is recorded per second and the wash duration in minutes.
ABSORBANCE_BASE = 10.0  # FIXED_BY_DEFINITION: absorbance is the base-10 logarithm of the incident over the transmitted light, so the transmitted light is ABSORBANCE_BASE to the power of minus the absorbance.
ABSORBANCE_READOUTS = (None, 'absorbance')  # the readout_signal values for which a plateau in OD is an absorbance the reader's photometric range applies to (not stated: the OD unit says absorbance); a stated chemiluminescence or fluorescence readout has no absorbance range.
MIN_CONCENTRATIONS = 8  # EXPERT_REVIEW: fewest titrant concentrations for a usable titration (a four-parameter curve has four free parameters, and the bottom, the top and the transition are not all defined with fewer than eight points; usual series have eight to twelve dilutions, Sebaugh 2011 Pharm Stat 10:128). Kept as full credit for every fit model: ELISA wells scatter by 5 to 10 percent and the readout is not at equilibrium, so even a two-parameter fit needs more points than a biosensor series (SPR full at 5).
CONCENTRATIONS_ZERO_AGREEMENT = 4  # EXPERT_REVIEW: number of concentrations at or below which the series carries no credit (degree 0, supported, never conflicting: a short series is weaker evidence, not evidence against) for a four-parameter fit, an 'other' model or no stated model: the four free parameters of the four-parameter curve named in MIN_CONCENTRATIONS; a series of four points or fewer is fitted exactly, with no residual left to show the bottom, the top and the transition.
FIT_FREE_PARAMETERS_BY_MODEL = {'1:1': 2, 'hill': 3, 'four_parameter_logistic': CONCENTRATIONS_ZERO_AGREEMENT, 'competitive_binding': 3}  # EXPERT_REVIEW: the free parameters of the fit model the paper states, the zero end of the count (the points the fit uses up): one-site (1:1) specific binding with the blank subtracted fits Bmax and KD (2); a Hill fit adds the slope (3); a one-site competition fits the top, the bottom and the IC50 with the slope fixed (3); the four-parameter logistic fits bottom, top, midpoint and slope (4). Any other or unstated model takes CONCENTRATIONS_ZERO_AGREEMENT (the stricter end).
LOW_FACTOR = 0.2  # EXPERT_REVIEW: the lowest concentration must be at most this multiple of the reported constant (the bottom baseline of the curve must be defined; one-site occupancy there 17 percent; 0.1x with a factor of 2 slack, Hulme and Trevethick 2010 Br J Pharmacol 161:1219).
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the constant at or above which the lowest concentration leaves no bottom baseline (conflicting); at the constant the curve is already half way up. In between the degree is linear in the one-site occupancy x / (1 + x) at the lowest concentration (the share of the curve the series leaves unseen).
HIGH_FACTOR = 10.0  # EXPERT_REVIEW: the highest concentration must be at least this multiple of the reported constant, because the plateau is only known by reaching it (about 90 percent saturation); a plate titration's top is also where non-specific adsorption rises, so the plateau must be seen clearly.
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the constant at or below which the highest concentration does not reach even half the curve (conflicting). In between the degree is linear in the one-site occupancy x / (1 + x) at the highest concentration (most of the plateau is seen by 2x to 5x).
MIN_INCUBATION_MIN = 30.0  # EXPERT_REVIEW (the floor, kept): the usual binding step is 30 minutes to two hours (Crowther, The ELISA Guidebook 2009); on a coated well the solution must also reach the surface by diffusion, about 0.5 mm in 30 minutes for a protein in an unstirred well, so this is a floor even for a fast reaction. Since the 2026-11-21 curve the floor is proportional, d_floor = min(1, t / MIN_INCUBATION_MIN), and never conflicting by itself.
EQUILIBRATION_REFERENCE_NM = 1.0  # EXPERT_REVIEW (kept): the constant at which EQUILIBRATION_REFERENCE_MIN is five half-lives of the approach to equilibrium at C = KD (Jarmoskaite et al. 2020 eLife 9:e57264): 5 ln2 / (2 kon KD) = 1733 s, about 29 minutes, with kon = KON_FAST_PER_M_S. The time needed scales as 1 / KD.
EQUILIBRATION_REFERENCE_MIN = 30.0  # EXPERT_REVIEW (the old number, kept): the five-half-lives time at EQUILIBRATION_REFERENCE_NM and KON_FAST_PER_M_S (1733 s, rounded to the 30 minutes the assay always used), so T_FAST = EQUILIBRATION_REFERENCE_MIN x EQUILIBRATION_REFERENCE_NM / constant_nM, the old conflict limit without its floor (a weak constant now gives a short T_FAST, the floor being the separate proportional d_floor).
KON_FAST_PER_M_S = 1e6  # EXPERT_REVIEW (kept): the fast end of typical protein-protein association, the rate behind T_FAST (Schreiber, Haran and Zhou 2009 Chem Rev 109:839; the formula and number are the assay's old ones).
KON_SLOW_PER_M_S = 1e4  # EXPERT_REVIEW, NEW, owner to confirm (from memory, not re-read): the slow end of association for the typical ELISA partners (antibody-antigen, receptor-ligand, protein-protein on a coated well). Without electrostatic steering proteins associate at about 1e5 to 1e6 per M per s and a conformational gate lowers that to 1e4 or below (Schreiber, Haran and Zhou 2009 Chem Rev 109:839); antibody-antigen on-rates measured by SPR sit mostly between 1e4 and 1e6 (Foote and Eisen 1995 PNAS 92:10, from memory), and the apparent rate onto a coated well is lower still as the titrant must reach the coating. 1e4 is two decades under the fast end; a rate under 1e4 is rare for these partners. T_SLOW = T_FAST x KON_FAST / KON_SLOW (a factor 100); the curve's log span is log(KON_FAST / KON_SLOW).
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate plates, dilution series or days); technical wells of one plate do not count. Below it (owner rule: replicates mean precision in every assay) the degree is min(1, sqrt(n / MIN_REPLICATES)): the plate-to-plate and day-to-day spread is the larger part of an ELISA's error (inter-assay CVs above intra-assay CVs), and the standard error of the mean constant over n independent experiments falls as 1 / sqrt(n) (the same sd^2 / n this converter uses for the variance); 1 experiment about 0.58, 2 about 0.82; never conflicting for a stated count.
AGREEMENT_FACTOR = 3.0  # EXPERT_REVIEW: allowed fold gap between a saturation-titration KD and a competition Ki (a Ki depends on the concentration and the affinity of the ligand it competes with, so the standard is looser than for two direct estimates).
AGREEMENT_ZERO_FACTOR = 10.0  # EXPERT_REVIEW: fold gap of the KD and the Ki at or beyond which the sheet takes them as disagreeing (conflicting); an order of magnitude is more than the competing ligand can explain and points to different binding events; in between the degree falls with the log of the fold (binding constants are log-normal and the strength anchors are on the log scale: 6-fold 0.42).
NULL_REASONS = {'recovery': 'an_elisa_has_no_matrix_recovery_measurement', 'attributed_signal': 'an_elisa_specificity_control_is_not_an_attribution_fraction', 'total_signal': 'an_elisa_specificity_control_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_elisa_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_elisa_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _degree(value, full, zero):
    """How far the value agrees: 1.0 at the full-agreement limit (and beyond it), falling linearly to 0 at the zero-agreement limit; zero or less at or past it. Either direction (zero below or above full)."""
    return (value - zero) / (full - zero)


def _log_degree(value, full, zero):
    """The same as _degree on the log of a fold (a ratio of two signals or of two constants): 1.0 at full, 0 at zero, either direction, not capped; 0 or less for a value at or below 0."""
    if value <= 0:
        return 0.0 if full > zero else 1.0
    return math.log(value / zero) / math.log(full / zero)


def _occupancy(over_constant):
    """The one-site occupancy at a concentration given as a multiple of the constant: x / (1 + x) (the fraction of the binding curve reached there)."""
    return over_constant / (1 + over_constant)


def _degree_verdict(degree, refs):
    if degree <= 0:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, degree))


def _partial(degree):
    """The degree to attach to a softened criterion: None at full credit (judged exactly as before the softening), else the partial degree."""
    return None if degree >= 1 else degree


def _judge_signal_window(native):
    # On the log of the ratio: a window is a fold over the paper's own blank, and the first doubling separates no curve from a visible one (range review).
    return _degree_verdict(_log_degree(native['signal_over_background'], MIN_SIGNAL_OVER_BACKGROUND, SIGNAL_WINDOW_ZERO_AGREEMENT), native['signal_window_refs'])


def _judge_plateau(native):
    # Shape for a plate reader: the error of an absorbance reading comes from the stray light against the transmitted light, which falls as
    # ABSORBANCE_BASE ** -OD, so the error grows as ABSORBANCE_BASE ** OD. The degree is linear on that scale: barely lowered just above
    # MAX_LINEAR_OD (about 0.91 at 3 OD, where readers still read within a few percent) and falling fast towards MAX_READABLE_OD.
    # The zero end is checked first (ABSORBANCE_BASE ** OD overflows for a number above about 308), and a readout stated as other than absorbance
    # has no photometric range to judge (range review).
    if native['readout_signal'] not in ABSORBANCE_READOUTS:
        return _verdict('unknown', [])
    od = native['plateau_absorbance']
    refs = list(dict.fromkeys([*native['plateau_refs'], *native['linear_limit_refs']]))
    if od >= MAX_READABLE_OD:
        return _verdict('conflicting', refs)
    # The linear limit is the paper's own stated reader limit when it gives one (relative to what the paper states), else the researched
    # MAX_LINEAR_OD; a stated limit above the photometric range of a plate reader cannot be taken beyond MAX_READABLE_OD.
    stated = native['detector_linear_limit']
    full = MAX_LINEAR_OD if stated is None else min(stated, MAX_READABLE_OD)
    if od <= full:
        return _verdict('supported', refs)
    degree = _degree(ABSORBANCE_BASE ** od, ABSORBANCE_BASE ** full, ABSORBANCE_BASE ** MAX_READABLE_OD)
    return _verdict('supported', refs, _partial(min(1.0, degree)))


def _judge_wash_loss(native):
    # The share of the complex that survives the washes is exp(-koff * t) (first-order dissociation into ligand-free buffer). The degree is linear in
    # koff * t (the number of 1/e lifetimes elapsed): full while at least WASH_RETAINED_FULL of the complex is kept, 0 (conflicting) when only
    # WASH_RETAINED_ZERO is kept; in between partial. A faster koff or a longer wash never raises it.
    elapsed = native['koff_per_s'] * native['wash_min'] * SECONDS_PER_MINUTE
    degree = _degree(elapsed, -math.log(WASH_RETAINED_FULL), -math.log(WASH_RETAINED_ZERO))
    return _degree_verdict(degree, native['wash_loss_refs'])


def _judge_equilibrium(native):
    # A curve on the log of the association rate (the paper's own equilibrium fact is unknown). The time for five half-lives is
    # T = T_FAST x (KON_FAST_PER_M_S / kon), T_FAST = EQUILIBRATION_REFERENCE_MIN x EQUILIBRATION_REFERENCE_NM / constant (the old conflict limit
    # without its floor). d_kon = log(t / T_FAST) / log(KON_FAST / KON_SLOW): the share of the plausible rates (on the log scale) for which the
    # incubation t covers the five half-lives. At or below T_FAST not even the fastest plausible association has equilibrated: conflicting (the
    # zero end). d_floor = min(1, t / MIN_INCUBATION_MIN) is the proportional diffusion-to-the-well floor, never conflicting by itself.
    # No constant: no scale, so unknown (a time alone is not the paper against equilibrium), also below the floor.
    constant, minutes = native['constant_nM'], native['incubation_min']
    if constant is None or constant <= 0:
        return _verdict('unknown', [])
    fast_minutes = EQUILIBRATION_REFERENCE_MIN * EQUILIBRATION_REFERENCE_NM / constant
    refs = list(dict.fromkeys([*native['incubation_refs'], *native['constant_refs']]))
    if minutes <= fast_minutes:
        return _verdict('conflicting', refs)
    d_kon = math.log(minutes / fast_minutes) / math.log(KON_FAST_PER_M_S / KON_SLOW_PER_M_S)
    return _verdict('supported', refs, _partial(min(1.0, minutes / MIN_INCUBATION_MIN, d_kon)))


def _judge_concentration_series(native):
    # Shape of the count for a plate titration: the paper's stated fit model uses FIT_FREE_PARAMETERS_BY_MODEL of the points for its parameters
    # (CONCENTRATIONS_ZERO_AGREEMENT for a four-parameter, other or unstated model); every further point is one residual degree of freedom that shows
    # the bottom, the top and the transition, so the degree rises linearly with the residual degrees of freedom to 1.0 at MIN_CONCENTRATIONS.
    # The count only lowers the degree: none at or below the model's parameters, never conflicting (a short series is weaker evidence).
    # The two ends: linear in the one-site occupancy reached there; conflicting at or past their zero ends (the paper's own series then stops at or
    # before half of the curve).
    parameters = FIT_FREE_PARAMETERS_BY_MODEL.get(native['fit_model'], CONCENTRATIONS_ZERO_AGREEMENT)
    count_degree = max(0.0, _degree(native['concentration_count'], MIN_CONCENTRATIONS, parameters))
    low, high = native['concentration_low_over_constant'], native['concentration_high_over_constant']
    if low is None:
        return _verdict('unknown', [])      # the span can only be judged from the list and the constant
    degrees = (_degree(_occupancy(low), _occupancy(LOW_FACTOR), _occupancy(LOW_ZERO_AGREEMENT_FACTOR)),
               _degree(_occupancy(high), _occupancy(HIGH_FACTOR), _occupancy(HIGH_ZERO_AGREEMENT_FACTOR)))
    if min(degrees) <= 0:
        return _verdict('conflicting', native['concentration_span_refs'])
    return _verdict('supported', native['concentration_span_refs'], min(1.0, count_degree, *degrees))


def _judge_estimates(native):
    # On the log of the fold: binding constants are log-normal (range review). Two folds can be recorded: the KD against the Ki (reported, else
    # Cheng-Prusoff from the IC50), and the reported Ki against the Cheng-Prusoff Ki (the paper's own conversion): the weaker of the two counts,
    # both on the same AGREEMENT_FACTOR scale (the conversion check relative to the tracer concentration and KD the paper states).
    folds = [(native[name], native[refs]) for name, refs in (('estimate_fold', 'estimate_refs'), ('conversion_fold', 'conversion_refs')) if native[name] is not None]
    degrees = [_log_degree(fold, AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR) for fold, _ in folds]
    return _degree_verdict(min(degrees), list(dict.fromkeys(ref for _, refs in folds for ref in refs)))


def _judge_replicates(native):
    # Shape: min(1, sqrt(n / MIN_REPLICATES)), the precision of the mean constant over n independent experiments relative to the researched count
    # (see MIN_REPLICATES); never conflicting for a stated count.
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], _partial(min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES))))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('signal_window', 'signal_window_recorded_for_the_sheet'): _judge_signal_window, ('detector_range', 'plateau_recorded_for_the_sheet'): _judge_plateau,
          ('equilibrium', 'incubation_recorded_for_the_sheet'): _judge_equilibrium, ('concentration_series', 'concentration_series_recorded_for_the_sheet'): _judge_concentration_series,
          ('wash_dissociation', 'wash_loss_recorded_for_the_sheet'): _judge_wash_loss, ('direct_vs_competition', 'estimates_recorded_for_the_sheet'): _judge_estimates, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


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
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def _variance_supports(native, constant_name):
    """The supports of the stated fields the variance rests on: the spread of the constant, its kind and, for a standard deviation, the replicate count."""
    quantities = native['quantities']
    names = [constant_name + '_spread'] + (['replicate_count'] if native['spread_kind'] == 'standard_deviation' else [])
    found = [quantities[name]['support'] for name in names] + [native['choice_support']['spread_kind']]
    return [support for support in found if support is not None]


def convert_elisa(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    constant_name = _binding_constant(native)
    if constant_name is None:
        only_half_maximal = native['ec50_nM'] is not None or native['ic50_nM'] is not None
        null_components['effect'] = 'only_a_half_maximal_concentration_given_not_a_binding_constant' if only_half_maximal else 'neither_kd_nor_ki_given_as_a_point_value'
    else:
        constant = native['quantities'][constant_name]
        quantities['effect'] = _operand(native[constant_name + '_nM'], 'nM', 'elisa_' + constant_name + ':' + ref, constant['source_refs'], constant['origin'], constant_name)
    variance, variance_reason, variance_refs = _variance(graded, constant_name)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'elisa_variance:' + ref, variance_refs, 'derived', constant_name + '_spread')
    null_components.update(NULL_REASONS)
    interpretations = {}
    for sheet_criterion, members in CRITERIA_MAP.items():
        graded_members = [_criterion(graded, m) for m in members if graded['criteria'][m]['status'] != 'not_applicable']
        if not graded_members:
            continue
        statuses = [m['status'] for m in graded_members]
        status = 'conflicting' if 'conflicting' in statuses else 'unknown' if 'unknown' in statuses else 'supported'
        refs = list(dict.fromkeys(r for m in graded_members for r in m['support_refs']))
        interpretations[sheet_criterion] = {'status': status, 'support_refs': refs if status == 'supported' else []}
        degrees = [m['degree'] for m in graded_members if 'degree' in m]
        if status == 'supported' and degrees:
            interpretations[sheet_criterion]['degree'] = min(degrees)      # the weakest member: a degree of a member is not averaged away
        supports = [s for m in members if graded['criteria'][m]['status'] != 'not_applicable' for s in native['support'][m]]
        interpretations[sheet_criterion] = apply_support(interpretations[sheet_criterion], supports)      # thin quote support lowers a supported degree
    if variance is not None:
        interpretations['variance_correspondence'] = apply_support({'status': 'supported', 'support_refs': variance_refs}, _variance_supports(native, constant_name))
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['titrant_preparation_ref'], 'immobilized_preparation_ref': preparations['fixed_partner_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    converted = {'version': VERSION, 'experiment_type': 'elisa', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': native['quantities'][constant_name]['support'] if constant_name is not None else None}
    if quantities['effect'] is None:      # no effect operand: the experiment's stated yes/no result stands (owner, 2026-11-22), scored like any stated result (literature_direction, the qualitative path)
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs'])}
        if native['interaction'] is not None:
            converted['direction_field_support'] = native['interaction_support']      # the support class of the fact binding_detected
    return converted
