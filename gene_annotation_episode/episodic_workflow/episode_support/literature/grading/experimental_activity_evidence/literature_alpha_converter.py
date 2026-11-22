"""AlphaScreen converter: turns the AlphaScreen grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_alpha.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS and ELISA converters fill), the
dependence keys the merger needs, and for every sheet component that a bead assay cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            the reported binding constant in nM (point operand): the
                  apparent KD of a titration, or, when the record has
                  no KD, the Ki of a competition (the measurement key names it:
                  alpha_kd or alpha_ki). Neither given leaves effect null; an EC50
                  or an IC50 alone is a half-maximal concentration, not a
                  dissociation constant (it depends on the partner and bead
                  concentrations and on the competing pair) and is not carried into the effect.
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
immobilized_preparation_ref = the partner held at a constant concentration, surface_ref = None (the plate is
not a surface reference), dataset_ref = the dataset.

Criteria mapping (AlphaScreen criteria -> sheet criteria), declared in CRITERIA_MAP
------------------------------------------------------------------------------------
binding_controls              specificity_control + capture_artifacts + avidity +
                              interference_counter_screen + light_protection
binding_regime                partner_depletion + hook_effect + concentration_series +
                              equilibrium + direct_vs_competition
binding_parameter_definition  fit_model
calibration_applicability     signal_window + assay_quality + detector_range (the signal
                              over the background, the Z' factor and the linear range of the
                              reader: this method's counterpart of the SPR Rmax check)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). OWNER RULE (A105_EXPERIMENT_SOP step 3, 2026-11-21): the researched values below are kept; no pass/fail cut-off is made at them.
Each comparison is supported with a degree of 1.0 at or past its full-agreement value, falling smoothly to 0 at its zero-agreement value, and conflicting (no degree) at or
beyond that value, on the scale the quantity lives on (2026-11-21 review, the answers below):
  signal_window               the log of signal over background: log(S/B) / log(MIN_SIGNAL_OVER_BACKGROUND), 0 at SIGNAL_WINDOW_ZERO_AGREEMENT (S/B = 1).
  assay_quality               linear in Z' from Z_PRIME_ZERO_AGREEMENT (0) to MIN_Z_PRIME (0.5).
  concentration_series span   the occupancy of a one-site curve at the series' ends, occ(x) = x / (1 + x) with x the concentration over the constant: the lowest end
                              full at LOW_FACTOR and 0 at LOW_ZERO_AGREEMENT_FACTOR, the highest end full at HIGH_FACTOR and 0 at HIGH_ZERO_AGREEMENT_FACTOR.
  concentration_series count  linear in the residual degrees of freedom of the four-parameter curve: (n - FIT_FREE_PARAMETERS) / (MIN_CONCENTRATIONS - FIT_FREE_PARAMETERS),
                              1.0 at MIN_CONCENTRATIONS and above, 0 at FIT_FREE_PARAMETERS points or fewer; a short series is weaker evidence, supported with that low
                              degree, NEVER conflicting (as in SPR). The criterion's degree is the smallest of the count's and the two ends'.
  direct_vs_competition       the log of the fold gap of the KD and the Ki: log(AGREEMENT_ZERO_FACTOR / fold) / log(AGREEMENT_ZERO_FACTOR / AGREEMENT_FACTOR).
  replicates                  sqrt(n / MIN_REPLICATES) below MIN_REPLICATES (the standard error of the constant over n independent experiments relative to the one at the
                              researched count), supported with no degree at MIN_REPLICATES and above (the same credit as SPR's min(1, sqrt(n / MIN))); unknown when the
                              independence is not stated yes.
  partner_depletion           only when the fact is not stated: the log of the depletion bias b(r) = 1 + r / 2 of the constant (the apparent constant is about KD + partner / 2) for the largest
                              fixed-partner concentration over the constant r, (log b(10) - log b(r)) / (log b(10) - log b(1)): 1.0 at PARTNER_FULL_FACTOR (1) and below
                              (b = 1.5), 0 (conflicting) at PARTNER_ZERO_FACTOR (10) and above (b = 6).
  equilibrium                 a curve on the log scale of the association rate (the time the partners were together is the incubation before the beads plus the step after the beads,
                              when stated; the grader's incubation_min; t). T_FAST = MIN_INCUBATION_MIN x EQUILIBRATION_REFERENCE_NM / constant_nM (five association half-lives at the
                              fast association rate, the earlier conflict limit, kept as the zero end) and T_SLOW = T_FAST x FAST_ASSOCIATION_RATE / SLOW_ASSOCIATION_RATE (the same with a slow rate).
                              d = log(t / T_FAST) / log(T_SLOW / T_FAST): conflicting at t <= T_FAST (even the fastest plausible association has not equilibrated), 1.0 at t >= T_SLOW,
                              supported with that degree between. No constant: unknown (no scale; a time alone is not the paper against equilibrium). A stated equilibrium fact decides first.
                              There is no separate absolute floor: the 30 minutes is the reference point of the fast end, not a mixing or settling time, so no d_floor is added.
The unknown weight of an unstated criterion is NOT here: it is the row contract's WEIGHT_UNKNOWN_BY_TYPE['alphascreen'] (0.65; 0.60 for binding_controls and
binding_regime), chosen because an AlphaScreen readout is relative (counts from an amplified bead signal, no absolute calibration) and its meaning rests on in-paper
controls (specificity, counter-screen, hook). No degree below uses it.

Owner's questions, answered per researched value (2026-11-21 review; Q1 what it protects against, Q2 general or lab-specific, Q3 absolute or relative and is the
relative quantity in the grader facts, Q4 how badly a wrong value misleads and whether the shape follows, Q5 consistency with the other binding assays)
  MIN_SIGNAL_OVER_BACKGROUND 10 / SIGNAL_WINDOW_ZERO_AGREEMENT 1
    Q1 a curve whose top is within the scatter of the background, so its bottom, top and constant are not defined. Q2 general AlphaScreen practice (windows of tens to
    thousands are usual; Eglen et al. 2008 Curr Chem Genomics 1:2-10; S/B alone is a weak statistic, Iversen et al., NCBI Assay Guidance Manual), not lab-specific.
    Q3 already relative to the paper's own control (the background wells); the better scale, the window over the background's spread (signal-to-noise), needs a
    background SD that the grader does not record: DECLINED as a gap (papers rarely give the background SD, and the Z' factor, graded in assay_quality, already carries the
    controls' spread over the window). The bead capacity against the highest concentration (hook effect) is likewise not collected: no general bead capacity is
    researched (lot and coating specific), so the stated fact hook_effect_handled stays the judgement. Q4 a window is a fold, and what changes the meaning is the fold: going from 1 to 2 is the difference
    between no curve and a visible one, 9 to 10 changes almost nothing; the committed linear ramp did the opposite (S/B 3 got 0.22). CHANGED: linear -> log.
    Q5 ELISA's signal window is the same idea (its own value, 5); MST uses a signal-to-noise and FP an absolute window in mP.
  MIN_Z_PRIME 0.5 / Z_PRIME_ZERO_AGREEMENT 0
    Q1 positive and negative controls whose three-sigma bands overlap: the assay cannot tell bound from unbound. Q2 general (Zhang, Chung and Oldenburg 1999 J Biomol
    Screen 4:67-73: 0.5 excellent, 0 to 0.5 marginal, 0 or less unusable). Q3 Z' is itself relative to the paper's controls (their means and SDs): absolute limits on a
    relative statistic are right. Q4 Z' is linear in the ratio of the control spread to the window, so a linear ramp is linear in what the controls show; a titration
    fit is less hurt by a marginal Z' than a single-point screen, so 0 to 0.5 partial credit is not too harsh. KEPT.  Q5 no other binding converter grades Z'.
  MIN_CONCENTRATIONS 8 / FIT_FREE_PARAMETERS 4
    Q1 too few points to pin the bottom, top, midpoint and slope of the fitted curve, so the constant is set by the model, not the data. Q2 general dose-response
    practice for a four-parameter fit (Sebaugh 2011 Pharm Stat 10:128-134: points on both plateaus and across the transition; NCBI Assay Guidance Manual series of 8
    to 12). Q3 absolute count; the free parameters depend on the stated model (a one-site fit with free bottom and top has 3, a bell-shaped hook more), and fit_model
    is in the grader facts, but a per-model count is not researched here: 4 (the commonest, four-parameter logistic) is kept for expert review. Q4 the
    shape (linear in residual degrees of freedom) is the SPR one; the committed CONFLICTING at 4 points or fewer was wrong: a short series is weaker evidence, not the
    paper showing against binding. CHANGED: conflicting at <= 4 points -> supported with degree 0 there, never conflicting. Q5 now as SPR (CONCENTRATIONS_ZERO).
  LOW_FACTOR 0.2 / LOW_ZERO_AGREEMENT_FACTOR 1.0 and HIGH_FACTOR 10 / HIGH_ZERO_AGREEMENT_FACTOR 1.0
    Q1 a series that does not reach the lower baseline or the upper plateau, so the fit extrapolates them and the constant drifts. Q2 general binding practice (0.1x to
    10x the constant; Hulme and Trevethick 2010 Br J Pharmacol 161:1219-1237; Jarmoskaite et al. 2020 eLife 9:e57264). Q3 relative to the paper's own constant
    (concentration_low_over_constant, concentration_high_over_constant are in the grader facts): right. Q4 what each end shows is the occupancy reached there,
    x / (1 + x): 2x already shows 67 percent, 5x 83, 10x 91, so most of the upper plateau comes early; the committed linear ramp in x gave 5x only 0.44 (steep where
    little changes). CHANGED: linear in x -> linear in occupancy (5x now 0.81, 2x 0.41; the lowest end at 0.5x 0.5 instead of 0.625). Values KEPT. Q5 SPR, BLI, GCI,
    EMSA, SPA and radioligand use HIGH_FACTOR 5; FP, FRET, MST, Trp, FCS and ELISA use 10 as here; with the occupancy shape the gap between 5 and 10 costs 0.19, not
    0.56, so the two families now differ little (flagged for the other converters' review, not changed there).
  MIN_INCUBATION_MIN 30 (with the new EQUILIBRATION_REFERENCE_NM 1)
    Q1 a constant read before the binding reached equilibrium (too weak an apparent affinity, worst for tight binders). Q2 30 to 60 minutes is typical PROTOCOL
    practice (vendor protocols; Eglen et al. 2008), not physics: the time needed is about five half-lives of the approach, 5 ln2 / (kon (C + KD) ) (Jarmoskaite et
    al. 2020), so it scales with 1 / KD. Q3 it must be relative to the paper's own constant (constant_nM, in the grader facts); koff is not collected (a stated time course is the fact
    equilibrium_reached, which decides first). The time compared is now the total the partners were together: the incubation before the beads plus the step after the beads
    when stated (the partners keep binding on the beads); the step after the beads alone does not count, the time before it being unknown. Q4 the committed absolute 30 minutes misled both ways: a 20-minute incubation of a micromolar binder (at equilibrium in
    seconds) made binding_regime conflicting, while a 30-minute incubation of a 10 pM binder (hours needed) was not flagged. CHANGED: the conflict is made relative,
    30 minutes x (1 nM / constant): 30 minutes is five half-lives at 1 nM with a typical fast association rate (10^6 per M per s; Schreiber, Haran and Zhou 2009
    Chem Rev 109:839-860), so the researched value is kept as the reference point of the scale. No constant: unknown (no longer conflicting on time alone).
    2026-11-21 owner decision A, a cliff made a curve (CHANGED): the committed rule was conflicting below T_FAST and unknown above it, so a time far past the fast limit got no credit at all.
    Association rates of the partners an AlphaScreen titrates (proteins and peptides on tagged or biotinylated beads) span decades, so the time is judged on the log scale of the rate:
    zero at T_FAST (kept: the old conflict limit, kon 1e6 per M per s), full at T_SLOW (the same formula at kon 1e5 per M per s, SLOW_ASSOCIATION_RATE_PER_M_S), the log share between.
    Q1-Q4 as above; Q4 the shape is steep where it matters (a 60-minute read of a 1 nM binder gets 0.30, 100 minutes 0.52, 300 minutes full) and full only when even a
    slow associator has equilibrated. Q3 the constant, with its refs, is the paper's own. Weak and tight binders: constant 1000 nM (micromolar) T_FAST 0.03 min, T_SLOW 0.3 min: a 1 minute
    read is full, 0.02 minutes (1.2 s) conflicting, 0.1 minutes 0.52; constant 0.01 nM (10 pM) T_FAST 3000 min (50 h), T_SLOW 30000 min: a 60-minute read conflicting, 3000 minutes
    conflicting at the zero end, 10000 minutes 0.52, 30000 full. Q5 the same curve form in every binding assay (each with its own fast limit and slow rate).
    SLOW_ASSOCIATION_RATE_PER_M_S 1e5: owner to confirm (from memory of Schreiber, Haran and Zhou 2009: association without electrostatic steering about 1e5 to 1e6; 1e5 is its slow end;
    a conformationally gated partner can be slower still, but that is not the typical partner of this assay).
  PARTNER_FULL_FACTOR 1 / PARTNER_ZERO_FACTOR 10 (added 2026-11-21 for the grader gap: the fixed partner's concentration over the constant)
    Q1 a fixed partner well above the KD depletes the titrated one, so the half-maximal concentration (about KD + P/2) reports the partner concentration and not the affinity.
    Q2 general (Jarmoskaite et al. 2020 eLife 9:e57264: the fixed component well below the KD); the factors are the criterion's own standard (at or below the KD) and the
    point where the bias is sixfold. Q3 relative to the paper's own constant (partner_over_constant is now in the grader facts, from labelled_partner_concentration or
    tagged_partner_concentration; a cross-titration holds no partner constant and records none). Q4 the bias is a fold, so the log of the multiple; a stated yes or no
    in words still decides first (the number is used only when the paper does not say). Q5 the same log-of-a-fold shape as the signal window and the KD/Ki gap.
    2026-11-21 owner decision B (CHANGED): the scale is the log of the bias b(r) = 1 + r / 2 itself, not the log of r: degree = (log b(10) - log b(r)) / (log b(10) - log b(1)), the
    ends kept (r = 1, b = 1.5 full; r = 10, b = 6 zero). Same physics and ends as TRP, FP, MST and split reporter. No assay-specific reason against it was found (the docstring
    only chose the log of a fold). Worked: r 2 gave 0.699 on the log of r, now ln(6/2) / ln(4) = 0.793; r 5 gave 0.301, now ln(6/3.5) / ln(4) = 0.389.
  MIN_REPLICATES 3
    Q1 a constant from one experiment carries none of the between-experiment error (bead lot, light- and oxygen-sensitive chemistry, plate, day). Q2 general (Vaux,
    Fidler and Cumming 2012 EMBO Rep 13:291-296: independent repeats, not wells). Q3 absolute count; the precision it buys is relative (sqrt). Q4 a wrong count
    misleads mildly (2 experiments keep 0.82); the sqrt follows the standard error. KEPT. Q5 the same sqrt(n / MIN) as SPR.
  AGREEMENT_FACTOR 3 / AGREEMENT_ZERO_FACTOR 10
    Q1 a titration KD and a competition Ki that describe different events (tag or bead interference in one format, avidity). Q2 general (a Ki rests on the
    Cheng-Prusoff correction, Cheng and Prusoff 1973, and the tracer's own KD, so two- to three-fold is the usual agreement of orthogonal estimates); FP, FRET, MST and
    ELISA use the same 3 and 10. Q3 already relative (one of the paper's constants over the other); the stated spreads (kd_spread, ki_spread) could widen it, not done
    here. Q4 binding constants are log-normal and the strength anchors are on the log scale, so a fold gap is judged on the log of the fold; linear in fold
    was too lenient between the ends, where a gap from 3 to 4 fold is a third of an order of magnitude (4-fold 0.86 linear, 0.76 log; 6-fold 0.57 linear, 0.42
    log; the ends are unchanged). CHANGED: linear -> log of the fold. Q5 the
    others still use a linear fold ramp (flagged, not changed there).
A sheet criterion that is supported carries the smallest degree of its members that have one (the sheet reads no degree; it travels with the interpretation and the merger
carries it per result).
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

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_alphascreen_converted_v1'
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
BINDING_CONSTANTS = ('kd', 'ki')
CRITERIA_MAP = {'binding_controls': ('specificity_control', 'capture_artifacts', 'avidity', 'interference_counter_screen', 'light_protection'), 'binding_regime': ('partner_depletion', 'hook_effect', 'concentration_series', 'equilibrium', 'direct_vs_competition'), 'binding_parameter_definition': ('fit_model',), 'calibration_applicability': ('signal_window', 'assay_quality', 'detector_range'), 'sampling_basis': ('replicates',)}
MIN_SIGNAL_OVER_BACKGROUND = 10.0  # EXPERT_REVIEW: smallest signal-to-background ratio for the curve to have a defined bottom and top; the background of the amplified bead signal is a few hundred counts per second and usual windows are tens to thousands, so a ratio below ten leaves a curve whose bottom is within the scatter of the background.
SIGNAL_WINDOW_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: signal-to-background ratio at or below which the sheet takes the curve as having no window at all (conflicting); a ratio of 1 is a top signal that is the background; in between the degree rises with the log of the ratio (a window is a fold: the first doubling matters most).
MIN_Z_PRIME = 0.5  # EXPERT_REVIEW: smallest Z' factor of the controls; 0.5 is the usual limit of an excellent assay window (Zhang, Chung and Oldenburg, 1999), below it positive and negative controls overlap too much for the curve to be read.
Z_PRIME_ZERO_AGREEMENT = 0.0  # EXPERT_REVIEW: Z' factor at or below which the sheet takes the controls as not separated at all (conflicting); a Z' of 0 is the limit at which the three-sigma bands of the positive and negative controls touch (Zhang et al., 1999: below 0 the assay is not usable); in between the degree falls linearly.
MIN_CONCENTRATIONS = 8  # EXPERT_REVIEW: fewest titrant concentrations for a usable titration (a four-parameter curve has four free parameters, and the bottom, the top and the transition are not all defined with fewer than eight points; usual series have eight to twelve dilutions). Full credit from this count up; below it partial credit (see FIT_FREE_PARAMETERS), not a fail.
FIT_FREE_PARAMETERS = 4  # EXPERT_REVIEW: the free parameters of the four-parameter curve an AlphaScreen titration is fitted with (bottom, top, midpoint, slope; the reason of MIN_CONCENTRATIONS); with this many points or fewer the curve passes through every point and the series leaves no residual to define it, so the count's degree is 0 here (supported, never conflicting: a short series is weaker evidence, not evidence against) and rises linearly with each further point to 1.0 at MIN_CONCENTRATIONS.
LOW_FACTOR = 0.2  # EXPERT_REVIEW: the lowest concentration must be at most this multiple of the reported constant (the bottom baseline of the curve must be defined; one-site occupancy there 17 percent).
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the constant at or above which the lowest concentration leaves no bottom baseline (conflicting); at the constant the curve is already half way up. In between the degree is linear in the one-site occupancy x / (1 + x) at the lowest concentration.
HIGH_FACTOR = 10.0  # EXPERT_REVIEW: the highest concentration must be at least this multiple of the reported constant, because the plateau is only known by reaching it (about 90 percent saturation); a hook effect above the plateau does not lower this need.
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the constant at or below which the highest concentration does not reach even half the curve (conflicting). In between the degree is linear in the one-site occupancy x / (1 + x) at the highest concentration (most of the plateau is seen by 2x to 5x).
MIN_INCUBATION_MIN = 30.0  # EXPERT_REVIEW: usual protocols incubate the partners 30 to 60 minutes before the beads; this is the time five half-lives of the approach to equilibrium take at EQUILIBRATION_REFERENCE_NM, so it is the reference point of a scale that follows the paper's own constant: the time needed is MIN_INCUBATION_MIN x EQUILIBRATION_REFERENCE_NM / constant_nM (the approach rate kon (C + KD) is proportional to KD at C = KD). A stated incubation shorter than that conflicts.
PARTNER_FULL_FACTOR = 1.0  # EXPERT_REVIEW: the fixed partner at or below this multiple of the reported constant does not deplete the titrated partner enough to matter (the criterion's own standard: at or below the KD; the half-maximal concentration of a titration is about KD + P/2, so the constant is then at most 1.5 times too high, Jarmoskaite et al. 2020 eLife 9:e57264). Full credit at and below it.
PARTNER_ZERO_FACTOR = 10.0  # EXPERT_REVIEW: the fixed partner at or above this multiple of the constant makes the half-maximal concentration about KD + P/2 = 6 KD, so the number reports the partner concentration and not the affinity (conflicting). In between the degree falls with the log of the multiple (the bias factor 1 + P / (2 KD) is a fold, as the constants are log-normal).
FAST_ASSOCIATION_RATE_PER_M_S = 1e6  # EXPERT_REVIEW: the fast association rate behind MIN_INCUBATION_MIN x EQUILIBRATION_REFERENCE_NM / constant (the fast end of typical protein-protein association, Schreiber, Haran and Zhou 2009 Chem Rev 109:839-860); kept as the zero end of the incubation curve.
SLOW_ASSOCIATION_RATE_PER_M_S = 1e5  # EXPERT_REVIEW: the slow association rate for the typical partners of an AlphaScreen (proteins, peptides and tagged ligands on beads): association without electrostatic steering is about 1e5 to 1e6 per M per s, so 1e5 is the slow end (Schreiber, Haran and Zhou 2009 Chem Rev 109:839-860, cited from memory); the incubation is full once even this rate has had five half-lives. Owner to confirm.
EQUILIBRATION_REFERENCE_NM = 1.0  # EXPERT_REVIEW: the constant at which MIN_INCUBATION_MIN is five half-lives of the approach to equilibrium (Jarmoskaite et al. 2020 eLife 9:e57264): 5 ln2 / (2 kon KD) = 1733 s, about 29 minutes, with kon = 10^6 per M per s, the fast end of typical protein-protein association (Schreiber, Haran and Zhou 2009 Chem Rev 109:839-860). A faster-associating pair needs less; this is a conflict limit, so it should not be set slower.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate plates, dilution series or days); technical wells of one plate do not count. Full credit from this count up; below it partial credit sqrt(n / MIN_REPLICATES), not a fail.
AGREEMENT_FACTOR = 3.0  # EXPERT_REVIEW: allowed fold gap between a titration KD and a competition Ki (a Ki depends on the concentration and the affinity of the pair it competes with, so the standard is looser than for two direct estimates).
AGREEMENT_ZERO_FACTOR = 10.0  # EXPERT_REVIEW: fold gap of the KD and the Ki at or beyond which the sheet takes them as disagreeing (conflicting); an order of magnitude is more than the competing pair can explain and points to different binding events; in between the degree falls with the log of the fold (binding constants are log-normal).
NULL_REASONS = {'recovery': 'an_alphascreen_has_no_matrix_recovery_measurement', 'attributed_signal': 'an_alphascreen_specificity_control_is_not_an_attribution_fraction', 'total_signal': 'an_alphascreen_specificity_control_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_alphascreen_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_alphascreen_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _degree(value, full, zero):
    """How far the value agrees: 1.0 at the full-agreement limit (and beyond it), falling linearly to 0 at the zero-agreement limit; zero or less at or past it. Either direction (zero below or above full)."""
    return (value - zero) / (full - zero)


def _log_degree(value, full, zero):
    """The same as _degree on the log of a fold (a ratio of two signals or of two constants): 1.0 at full, 0 at zero, either direction, not capped."""
    return math.log(value / zero) / math.log(full / zero)


def _occupancy(over_constant):
    """The one-site occupancy at a concentration given as a multiple of the constant: x / (1 + x) (the fraction of the binding curve reached there)."""
    return over_constant / (1 + over_constant)


def _degree_verdict(degree, refs):
    if degree <= 0:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, degree))


def _judge_signal_window(native):
    # On the log of the ratio: a window is a fold over the paper's own background, and the first doubling separates no curve from a visible one (see the docstring).
    return _degree_verdict(_log_degree(native['signal_over_background'], MIN_SIGNAL_OVER_BACKGROUND, SIGNAL_WINDOW_ZERO_AGREEMENT), native['signal_window_refs'])


def _judge_z_prime(native):
    # Linear in Z': Z' is linear in the ratio of the controls' spread to their window, the thing the criterion is about.
    return _degree_verdict(_degree(native['z_prime'], MIN_Z_PRIME, Z_PRIME_ZERO_AGREEMENT), native['z_prime_refs'])


def _depletion_bias(partner_over_constant):
    """The fold by which the apparent constant exceeds the true one when the fixed partner is at this multiple of the constant: about KD + partner / 2 over KD."""
    return 1 + partner_over_constant / 2


def _judge_partner_depletion(native):
    # On the log of the bias of the half-maximal concentration, a fold b(r) = 1 + r / 2 (r the partner over the constant). Full at PARTNER_FULL_FACTOR and below, conflicting at
    # PARTNER_ZERO_FACTOR and above. Used only when the paper does not say in words whether the partner was below the KD (that statement decides, as for every one-fact criterion).
    return _degree_verdict(_log_degree(_depletion_bias(native['partner_over_constant']), _depletion_bias(PARTNER_FULL_FACTOR), _depletion_bias(PARTNER_ZERO_FACTOR)), native['partner_refs'])


def _judge_equilibrium(native):
    # A curve on the log scale of the association rate. T_FAST is the time five half-lives take at the fast rate for the paper's own constant (MIN_INCUBATION_MIN scaled by
    # EQUILIBRATION_REFERENCE_NM / constant), T_SLOW the same at the slow rate. At or below T_FAST not even the fastest plausible association has equilibrated: conflicting (the zero end);
    # at or above T_SLOW every plausible rate has: full; between, the share of the plausible rates (on the log scale) that the incubation covers. No separate floor for this assay.
    # With no constant there is no scale, and the time alone is not the paper showing against equilibrium: unknown.
    constant = native['constant_nM']
    if constant is None:
        return _verdict('unknown', [])
    t_fast = MIN_INCUBATION_MIN * EQUILIBRATION_REFERENCE_NM / constant
    t_slow = t_fast * FAST_ASSOCIATION_RATE_PER_M_S / SLOW_ASSOCIATION_RATE_PER_M_S
    refs = list(dict.fromkeys([*native['incubation_refs'], *native['quantities'][native['constant_name']]['source_refs']]))
    return _degree_verdict(math.log(native['incubation_min'] / t_fast) / math.log(t_slow / t_fast), refs)


def _judge_concentration_series(native):
    # The count: linear in the residual degrees of freedom of the four-parameter fit (n - FIT_FREE_PARAMETERS), 1.0 at MIN_CONCENTRATIONS, 0 at FIT_FREE_PARAMETERS or
    # fewer. Why this shape for an AlphaScreen: its constant comes from fitting a four-parameter (or bell-shaped) curve to the titration, and each point beyond the free
    # parameters is one more residual that pins the bottom, the top and the transition. A short series only lowers the degree: never conflicting (as SPR).
    # The two ends: linear in the one-site occupancy reached there (what the lowest point shows of the baseline, the highest of the plateau); conflicting at or past
    # their zero ends (the paper's own series then stops at or before half of the curve).
    count_degree = max(0.0, _degree(native['concentration_count'], MIN_CONCENTRATIONS, FIT_FREE_PARAMETERS))
    low, high = native['concentration_low_over_constant'], native['concentration_high_over_constant']
    if low is None:
        return _verdict('unknown', [])      # the span can only be judged from the list and the constant
    degrees = (_degree(_occupancy(low), _occupancy(LOW_FACTOR), _occupancy(LOW_ZERO_AGREEMENT_FACTOR)),
               _degree(_occupancy(high), _occupancy(HIGH_FACTOR), _occupancy(HIGH_ZERO_AGREEMENT_FACTOR)))
    if min(degrees) <= 0:
        return _verdict('conflicting', native['concentration_span_refs'])
    return _verdict('supported', native['concentration_span_refs'], min(1.0, count_degree, *degrees))


def _judge_estimates(native):
    # On the log of the fold: binding constants are log-normal (the strength anchors are on the log scale too).
    return _degree_verdict(_log_degree(native['estimate_fold'], AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR), native['estimate_refs'])


def _judge_replicates(native):
    # Below MIN_REPLICATES: sqrt(n / MIN_REPLICATES). Why this shape for an AlphaScreen: its largest error is between independent experiments (bead lot, the light- and
    # singlet-oxygen-sensitive chemistry, plate and day), so each independent experiment is one draw of that error and the standard error of the reported constant falls
    # as 1 / sqrt(n); the degree is the standard error at the researched count over the one at the stated count. A count is never a fail; unknown independence is unknown.
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])
    count = native['replicate_count']
    if count >= MIN_REPLICATES:
        return _verdict('supported', native['replicate_refs'])
    return _verdict('supported', native['replicate_refs'], math.sqrt(count / MIN_REPLICATES))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('signal_window', 'signal_window_recorded_for_the_sheet'): _judge_signal_window, ('assay_quality', 'z_prime_recorded_for_the_sheet'): _judge_z_prime,
          ('partner_depletion', 'partner_concentration_recorded_for_the_sheet'): _judge_partner_depletion, ('equilibrium', 'incubation_recorded_for_the_sheet'): _judge_equilibrium, ('concentration_series', 'concentration_series_recorded_for_the_sheet'): _judge_concentration_series,
          ('direct_vs_competition', 'estimates_recorded_for_the_sheet'): _judge_estimates, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


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


def convert_alpha(graded):
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
        quantities['effect'] = _operand(native[constant_name + '_nM'], 'nM', 'alpha_' + constant_name + ':' + ref, constant['source_refs'], constant['origin'], constant_name)
    variance, variance_reason, variance_refs = _variance(graded, constant_name)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'alpha_variance:' + ref, variance_refs, 'derived', constant_name + '_spread')
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
    converted = {'version': VERSION, 'experiment_type': 'alphascreen', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': native['quantities'][constant_name]['support'] if constant_name is not None else None}
    if quantities['effect'] is None:      # no effect operand: the experiment's stated yes/no result stands (owner, 2026-11-22), scored like any stated result (literature_direction, the qualitative path)
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs'])}
        if native['interaction'] is not None:
            converted['direction_field_support'] = native['interaction_support']      # the support class of the fact binding_detected
    return converted
