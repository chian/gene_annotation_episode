"""Nmr_timecourse converter: turns the grader's result into what the A105 activity_rate sheet takes.

Hand-built, private to nmr_timecourse, deterministic. Input: the result of grade_nmr_timecourse. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'activity_rate'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, the
enzyme's molar mass the direction function needs, and for every sheet component that an activity measurement cannot honestly fill, the
reason it stays null. Built on the shape of the first activity_rate type (spectro_direct); the copy is private (DRAFT 2026-11-22, no run yet).

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: catalytic efficiency kcat/Km (M^-1s^-1), turnover kcat (s^-1),
                  specific activity (U/mg) or the rate over the paper's own control (fold). Several may be stated; the one used is the
                  best-determined, in the class order ACTIVITY_EFFECT_ORDER (literature_activity_direction.select_activity_effect). A stated
                  value in another unit of the record's vocabulary is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION): the
                  value is the paper's, only its unit spelling changes. A bare rate in concentration per time (uM/min from an integral slope)
                  is none of the four and fills no effect (reported to the owner as a class gap, not derived here).
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted. Otherwise null.
Every other role stays null, with a reason (NULL_REASONS).
enzyme_mass_g_per_mol   the enzyme's molar mass in g/mol (the stated mass in kDa times 1000), or None.
qualitative_effect  only when NO effect is stated and the paper states whether it saw activity above its own control: statement
                  'interaction_detected' (read "activity detected") or 'interaction_not_detected' (read "activity not detected"), with the
                  refs of the fact that states it, and direction_field_support the support of that one fact. A stated effect fixes the
                  direction; the statement is then not used. A statement in words alone counts the contract's stated_strength; that is not
                  re-implemented here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives   spontaneous_reaction_control + pre_reaction_spectrum
attribution_supported     enzyme_dependence + product_assignment
calibration_applicability  quantitation_reference + signal_to_noise + relaxation
rate_regime               initial_rate_regime + progress_curve_points + enzyme_substrate_ratio
kinetic_model             substrate_range
normalization_basis       active_enzyme_amount
sampling_basis            replicates
assertion_relevance       native_reaction
condition_scope           purified_enzyme
variance_correspondence   supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in
'_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Each judgement is a researched value of THIS assay made
gradual (SOP step 3): full agreement at the researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the
scale the physics of the assay gives (never a step), unknown when the paper states nothing, never conflicting for a short count. A value at or
beyond its zero end is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported carries the smallest
degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and never
changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are
dropped; a sheet criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (measurement_identity,
matrix_interference, partner_perturbation) are not selected. (The product being seen by its chemical shift is a strength of the method:
product_assignment sits under attribution_supported; matrix_interference is not selected because overlap with other resonances is not a
field the record asks for.)

How the class decisions apply here (2026-11-21, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys
stay None (no immobilized enzyme, no electrode). Qualitative statements keep the existing vocabulary. Direction and strength of a stated
rate: literature_activity_direction (same paradigm as binding, larger is stronger); controls, blanks and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a
wrong value misleads and whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not
verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
CONSUMED_FULL_PERCENT 10 -> CONSUMED_ZERO_PERCENT 90, judged on the bias of the average rate.
  Q1 an "initial rate" that is really the average over a progress curve that has already bent, so the rate is too low. Q2 general: initial
  velocity means at most about 10 percent of the substrate consumed (Cornish-Bowden, Fundamentals of Enzyme Kinetics; Copeland, Enzymes), from
  memory. An NMR time course is often fitted whole with the integrated rate equation (progress-curve analysis); such a paper states no share
  consumed for an initial rate and is not judged here (the field stays unavailable). Q3 relative to the paper's own substrate, which the passage
  states as a share. Q4 the physics gives the shape: for a first-order progress curve (the worst case) the rate averaged over the window is
  f / -ln(1 - f) of the initial rate: 0.95 at 10 percent, 0.72 at 50, 0.39 at 90. The degree is linear in that bias between the two ends; at or
  beyond 90 percent the "rate" is an end point (conflicting). Q5 the same value and shape as in the other activity types.
ENZYME_RATIO_FULL 0.01 -> ENZYME_RATIO_ZERO 1.0, judged on the log of E / (S + Km).
  Q1 the steady-state rate law holds only while the enzyme is small against the substrate plus the Km. Q2 general: the validity parameter of the
  reduced equation is E0 / (S0 + Km) (Segel and Slemrod 1989, SIAM Rev 31:446), the error of the rate is of that order. NMR uses micromolar
  enzyme (the method is insensitive) against millimolar substrate, so the ratio is usually 0.001 to 0.01 and a paper that states it near 1 is
  one that needed the signal at the cost of the rate law. Q3 relative to the paper's own S and Km; the grader records all three. Q4 an error of
  about the value of the ratio, linear in its log. Q5 as in the other activity types.
SNR_FULL 150 -> SNR_ZERO 3, judged on the relative integral error 1 / SNR.
  Q1 an integral that is mostly noise: the amount, and so the slope, is wrong by the noise. Q2 general: a signal-to-noise ratio of about 150 or more
  gives an integral uncertainty near or under 1 percent (Malz and Jancke 2005, J Pharm Biomed Anal 38:813, who ask for 150; some sources ask
  for 250), and a signal-to-noise ratio of 3 is the detection limit, where a peak can hardly be told from noise, from memory. Q3 absolute
  (a ratio); the paper states it for its own resonance. Q4 the relative error of an integral goes as 1 / SNR (Bharti and Roy 2012, TrAC 35:5,
  from memory): 0.7 percent at 150, 10 percent at 10, 33 percent at 3. The degree is linear in that error between the ends, so it is high
  (0.9) at S/N 30 and 0.71 at 10; at or below 3 the resonance is at the detection limit (conflicting). The ratio is stated for a spectrum, and a
  slope over many spectra is better than one of them, so this is a conservative reading. Q5 the same idea as the absorbance range of
  spectro_direct (a bias that grows with the departure from the researched value), on this method's own error law.
RELAXATION_RATIO_FULL 5 -> RELAXATION_RATIO_ZERO 0.2, judged on the recovered fraction 1 - exp(-delay / T1).
  Q1 the nuclei had not relaxed between scans, so the integral is saturated and species with different T1 are weighted wrongly: the
  amounts, and so the rate, are biased. Q2 general: a delay of five times the longest T1 recovers 99.3 percent of the magnetization (quantitative
  NMR practice asks for five to seven T1; Bharti and Roy 2012; Malz and Jancke 2005), from memory. Q3 relative to the paper's own T1; the
  grader records both numbers and the converter reads their ratio. Q4 the recovered fraction is 1 - exp(-ratio): 0.86 at 2, 0.63 at 1, 0.18
  at 0.2. The degree is linear in it between the ends, so it is 0.95 at three T1, 0.84 at two and 0.56 at one. The zero end is a delay of a
  fifth of T1 (18 percent recovered): the paper then shows an acquisition far from quantitative (conflicting). It is not set higher because a
  reduced flip angle (Ernst angle), which the record does not ask for, makes a short delay legitimate; a short delay is therefore only
  conflicting at the far end. Q5 consistent with the other ramps (full at the researched good value, a physical bias towards the zero end).
MIN_TIME_POINTS 6, TIME_POINTS_ZERO 2.
  Q1 a slope fitted to too few spectra. Q2 general: about five or six points on the linear part of a progress curve (Copeland), from memory;
  the exact 6 is a judgement. Q3 absolute (a count). Q4 a straight line has two parameters (slope, intercept), so two points leave no residual
  degree of freedom (degree 0, supported, never conflicting); each added point is one more the line must pass through: the degree rises
  linearly with count - 2 (4 give 1/2, 5 give 3/4). Q5 the same residual-degree-of-freedom count as the substrate series.
MIN_SUBSTRATE_CONCENTRATIONS 5, SUBSTRATE_CONCENTRATIONS_ZERO 2.
  Q1 a Km fitted to too few substrate concentrations to show the hyperbola holds. Q2 general: a saturation curve of about six to eight
  concentrations (Cornish-Bowden; Copeland), from memory; for NMR it is five because each concentration is a whole time course in the
  magnet (an hour or more of spectrometer time and millimolar substrate), so five is the practical full value. Q3 absolute (a count). Q4 the
  Michaelis-Menten equation has two parameters, so two concentrations leave no residual degree of freedom (degree 0, never conflicting); the
  degree rises linearly with count - 2 (3 give 1/3, 4 give 2/3). Q5 the same residual-degree-of-freedom count as spectro_direct, with the
  method's own full value.
LOW_FACTOR 0.5 -> LOW_ZERO_FACTOR 4.0, HIGH_FACTOR 10 -> HIGH_ZERO_FACTOR 1.0 (the lowest and highest substrate over the Km).
  Q1 a series that does not bracket the Km, so Km and Vmax trade off (no saturation) or the curvature is unseen (no low end). Q2 general:
  0.2 to 10 times the Km (the references above), from memory; the low end is raised to 0.5 for NMR because the method cannot read a
  substrate below about 50 to 100 uM at a useful signal-to-noise ratio, so for an enzyme with a Km under 100 uM the lowest concentration
  cannot be 0.2 Km; the top stays 10 because Vmax is a free amplitude known only by reaching it (SOP rule d). Q3 relative to the paper's own
  Km (the grader records both ratios). Q4 the rate is v / Vmax = S / (S + Km), so both ends are judged linearly in the fractional saturation
  S / (S + Km): the low end is full at 0.5 Km (1/3) and zero at 4 Km (0.8; with nothing below 4 Km the curve is flat and defines kcat, not Km),
  so a lowest concentration at the Km itself keeps 0.64; the high end is full at 10 Km (10/11) and zero at the Km itself (1/2). Q5 the same
  idea and shape as spectro_direct; only the low end is moved, for a stated physical reason (the method's concentration floor).
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a rate from one time course, whose sample-to-sample spread is unseen. Q2 general (triplicate practice; NMR time courses are costly and
  duplicates are common, so unstated replicates are weighed low, below). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same
  sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the controls, the pre-reaction spectrum, the enzyme dependence, the product assignment, the quantitation reference, the
active-site determination, the native substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is conflicting
(an internal standard stated as not used is not, see the criteria file), silence is unknown. They have no researched value to soften. NOT
judged, and why: the nucleus and the spectrometer field (the signal-to-noise ratio carries what they give); the pH, the temperature and the
deuterated solvent (the claim carries no condition, the identity block records the temperature; a deuterium solvent isotope effect of a
few fold changes the magnitude, not the existence of the activity).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered
for this assay, decided 2026-11-22 (DRAFT), owner to confirm:
  What does it measure; absolute or relative? The amounts of substrate and product over time by integrals of assigned resonances, turned into an
  absolute rate by an internal standard (or a known starting amount): absolute, and species-specific.
  Is there a reference range we would trust if the paper stated less (as for KD)? Yes, the same range of kcat and kcat/Km as for every
  activity type; a stated rate from an assigned product on a purified enzyme is standard evidence of catalysis.
  What does an unstated control or calibration do to the number's meaning? The spectra show the substrate and the product separately, so a
  spontaneous change or a contaminant is often visible in the same series; an unstated blank is benign more often than for a dye. An unstated
  relaxation delay, standard or signal-to-noise ratio is a real way for the integral to be wrong (saturation, a lost standard, noise) and is
  common in short methods text; an unstated product assignment is benign when the product is the expected one.
  If we assume it is fine and are wrong, how badly does the score mislead? A rate too low or too high by a bias of tens of percent, not a false
  activity; less severe than a dye background.
  Consistent with KD and with spectro_direct? The default 0.85 equals spectro_direct; the criterion overrides differ where NMR differs.
  default 0.85. background_alternatives 0.80 (a little above spectro_direct's 0.75: the spectra show a spontaneous change or an impurity).
  attribution_supported 0.90 (above spectro_direct's 0.80: the product is seen by its chemical shift). calibration_applicability 0.80 (below
  spectro_direct's 0.90: the amounts rest wholly on integrals, whose relaxation, noise and reference a short methods text often leaves out).
  normalization_basis 0.90 (benign, as for spectro_direct). sampling_basis takes the default 0.85 (an NMR time course is often run once).
  rate_regime, kinetic_model, assertion_relevance, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_activity_direction import select_activity_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_nmr_timecourse_converted_v1'
CRITERIA_MAP = {'background_alternatives': ('spontaneous_reaction_control', 'pre_reaction_spectrum'), 'attribution_supported': ('enzyme_dependence', 'product_assignment'),
                'calibration_applicability': ('quantitation_reference', 'signal_to_noise', 'relaxation'),
                'rate_regime': ('initial_rate_regime', 'progress_curve_points', 'enzyme_substrate_ratio'),
                'kinetic_model': ('substrate_range',), 'normalization_basis': ('active_enzyme_amount',), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
GRAMS_PER_MOL_PER_KDA = 1000.0  # FIXED_BY_DEFINITION: 1 kDa is 1000 g/mol.
CONSUMED_FULL_PERCENT = 10.0  # EXPERT_REVIEW, owner to confirm: at most about 10 percent of the substrate consumed in the window of an initial rate (Cornish-Bowden; Copeland, from memory); full agreement up to it.
CONSUMED_ZERO_PERCENT = 90.0  # EXPERT_REVIEW, owner to confirm: at 90 percent consumed the rate averaged over a first-order progress curve (the worst case) is 0.39 of the initial rate: an end point, not a rate (no agreement); the degree falls linearly in the bias 1 - f / -ln(1 - f) of the average rate from the full end to here.
ENZYME_RATIO_FULL = 0.01  # EXPERT_REVIEW, owner to confirm: the validity parameter E / (S + Km) of the steady-state rate law (Segel and Slemrod 1989, from memory) at 0.01, about 1 percent error; full agreement up to it.
ENZYME_RATIO_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: enzyme as large as substrate plus Km: the steady-state law does not describe the reaction (no agreement); falls from ENZYME_RATIO_FULL linearly in the log of the ratio, because the error of the rate is proportional to it.
SNR_FULL = 150.0  # EXPERT_REVIEW, owner to confirm, from memory not verified: a signal-to-noise ratio of about 150 gives an integral uncertainty near 1 percent (Malz and Jancke 2005, J Pharm Biomed Anal 38:813); full agreement from it.
SNR_ZERO = 3.0  # EXPERT_REVIEW, owner to confirm, from memory not verified: a signal-to-noise ratio of 3 is the detection limit, where the integral is as large as the noise (no agreement); the degree falls linearly in the relative integral error 1 / SNR from the full end to here.
RELAXATION_RATIO_FULL = 5.0  # EXPERT_REVIEW, owner to confirm, from memory not verified: a relaxation delay of five times the longest T1 recovers 99.3 percent of the magnetization (quantitative NMR practice asks five to seven T1); full agreement from it.
RELAXATION_RATIO_ZERO = 0.2  # EXPERT_REVIEW, owner to confirm: a delay of a fifth of T1 recovers 18 percent (no agreement); not set higher because a reduced flip angle, which the record does not ask for, makes a short delay legitimate; the degree falls linearly in the recovered fraction 1 - exp(-delay / T1) from the full end to here.
MIN_TIME_POINTS = 6  # EXPERT_REVIEW, owner to confirm, from memory not verified: about five or six spectra on the linear part of a progress curve fix its slope (Copeland); full agreement from it.
TIME_POINTS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: a straight line has two parameters (slope, intercept), so two points leave no residual degree of freedom (degree 0, supported, never conflicting); between this and MIN_TIME_POINTS the degree rises linearly with the residual degrees of freedom (count - 2).
MIN_SUBSTRATE_CONCENTRATIONS = 5  # EXPERT_REVIEW, owner to confirm: fewest substrate concentrations of a usable saturation curve for NMR (five: each concentration is a whole time course in the magnet; a plain assay uses six to eight, Cornish-Bowden; Copeland, from memory); full agreement from it.
SUBSTRATE_CONCENTRATIONS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: the Michaelis-Menten equation has two parameters (Km, Vmax), so two concentrations leave no residual degree of freedom (degree 0, supported, never conflicting); between this and MIN_SUBSTRATE_CONCENTRATIONS the degree rises linearly with count - 2.
LOW_FACTOR = 0.5  # EXPERT_REVIEW, owner to confirm: the lowest substrate should be at most this multiple of the Km (v is 1/3 of Vmax there); raised from 0.2 of an optical assay because NMR cannot read a substrate below about 50 to 100 uM; full agreement up to it.
LOW_ZERO_FACTOR = 4.0  # EXPERT_REVIEW, owner to confirm: nothing measured below 4 Km (v is 0.8 of Vmax) leaves the curvature unseen, so kcat but not Km is defined (no agreement); falls from LOW_FACTOR linearly in the fractional saturation S / (S + Km).
HIGH_FACTOR = 10.0  # EXPERT_REVIEW, owner to confirm: the highest substrate should be at least this multiple of the Km (v is 10/11 of Vmax); Vmax is a free amplitude known only by reaching it (SOP rule d: 10 for a free plateau); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: highest substrate at the Km itself never reaches saturation (no agreement); falls from HIGH_FACTOR linearly in the fractional saturation S / (S + Km).
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate time courses; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.ACTIVITY_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (1 U = 1 umol/min; mM^-1 is 1000 M^-1; uM^-1 is 1e6 M^-1; 1 nmol is 1e-3 umol; 60 s is 1 min); the stated number is the paper's.
    'catalytic_efficiency': ('M^-1s^-1', {'M^-1 s^-1': 1.0, 'mM^-1 s^-1': 1.0e3, 'uM^-1 s^-1': 1.0e6}),
    'turnover': ('s^-1', {'s^-1': 1.0, 'min^-1': 1.0 / SECONDS_PER_MINUTE}),
    'specific_activity': ('U/mg', {'U/mg': 1.0, 'umol/min/mg': 1.0, 'nmol/min/mg': 1.0e-3}),
    'rate_over_control': ('fold', {'fold': 1.0}),
}
# The quantity_kind (QUANTITY_KINDS['activity_rate']) that names the kind of each effect quantity; literature_activity_direction.ACTIVITY_QUANTITY_OF_KIND reads it back.
KIND_OF_QUANTITY = {'catalytic_efficiency': 'catalytic_efficiency', 'turnover': 'turnover', 'specific_activity': 'rate', 'rate_over_control': 'rate_ratio'}
KIND_WITHOUT_EFFECT = 'rate'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'nmr_timecourse_has_no_matrix_recovery_measurement', 'attributed_signal': 'an_integral_rate_is_not_an_attribution_fraction', 'total_signal': 'an_integral_rate_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_an_nmr_timecourse_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_nmr_timecourse_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENT = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected'}   # read "activity detected" / "activity not detected" for this class


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _share(value, full, zero):
    """1.0 at the full-agreement limit, 0 at the zero-agreement limit, linear in between (either orientation; not capped)."""
    return (zero - value) / (zero - full)


def _graded(refs, *limits):
    """Each limit is (value, full_agreement_limit, zero_agreement_limit), all on the criterion's own scale. Conflicting when any value is at or beyond its zero limit; else supported with the smallest degree, 1.0 at the full limit falling linearly on that scale to 0 at the zero limit."""
    degrees = [_share(value, full, zero) for value, full, zero in limits]
    if min(degrees) <= 0:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, *degrees))


def _log(value, full, zero):
    """A ratio limit on the log scale, for _graded."""
    return math.log(value), math.log(full), math.log(zero)


def _saturation(ratio):
    """Fractional saturation S / (S + Km) of a substrate S given as S / Km: where on the hyperbola it sits."""
    return ratio / (1 + ratio)


def _average_rate_bias(fraction):
    """The shortfall 1 - f / -ln(1 - f) of the rate averaged over a first-order progress curve that has consumed the fraction f of the substrate."""
    return 1.0 - fraction / -math.log1p(-fraction)


def _recovered(ratio):
    """The fraction of the magnetization recovered after a delay of ``ratio`` times T1."""
    return 1.0 - math.exp(-ratio)


def _judge_regime(native):
    refs = native['consumed_refs']
    fraction, zero = native['consumed_percent'] / PERCENT_PER_FRACTION, CONSUMED_ZERO_PERCENT / PERCENT_PER_FRACTION
    if fraction >= zero:
        return _verdict('conflicting', refs)
    return _graded(refs, (_average_rate_bias(fraction), _average_rate_bias(CONSUMED_FULL_PERCENT / PERCENT_PER_FRACTION), _average_rate_bias(zero)))


def _judge_enzyme_ratio(native):
    return _graded(native['enzyme_ratio_refs'], _log(native['enzyme_over_substrate_plus_km'], ENZYME_RATIO_FULL, ENZYME_RATIO_ZERO))


def _judge_series(native):
    # the two ratios keep their ramps (conflicting at their zero end), judged on the fractional saturation; the lower end is judged only when the series
    # has one distinct from its upper end (one concentration is a short series, not a badly placed one). The count only lowers the degree, never conflicts.
    refs = native['concentration_refs']
    low, high = native['concentration_low_over_km'], native['concentration_high_over_km']
    limits = [(_saturation(high), _saturation(HIGH_FACTOR), _saturation(HIGH_ZERO_FACTOR))]
    if low < high:
        limits.append((_saturation(low), _saturation(LOW_FACTOR), _saturation(LOW_ZERO_FACTOR)))
    verdict = _graded(refs, *limits)
    if verdict['status'] == 'conflicting':
        return verdict
    count_degree = max(0.0, min(1.0, _share(native['concentration_count'], MIN_SUBSTRATE_CONCENTRATIONS, SUBSTRATE_CONCENTRATIONS_ZERO)))
    return _verdict('supported', refs, min(verdict['degree'], count_degree))


def _judge_signal_to_noise(native):
    return _graded(native['signal_refs'], (1.0 / native['signal_to_noise'], 1.0 / SNR_FULL, 1.0 / SNR_ZERO))


def _judge_relaxation(native):
    return _graded(native['relaxation_refs'], (_recovered(native['relaxation_over_t1']), _recovered(RELAXATION_RATIO_FULL), _recovered(RELAXATION_RATIO_ZERO)))


def _judge_time_points(native):
    # a short count only lowers the degree, never conflicts
    degree = max(0.0, min(1.0, _share(native['time_point_count'], MIN_TIME_POINTS, TIME_POINTS_ZERO)))
    return _verdict('supported', native['time_point_refs'], degree)


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('initial_rate_regime', 'consumed_recorded_for_the_sheet'): _judge_regime, ('enzyme_substrate_ratio', 'enzyme_ratio_recorded_for_the_sheet'): _judge_enzyme_ratio,
          ('substrate_range', 'substrate_series_recorded_for_the_sheet'): _judge_series, ('signal_to_noise', 'signal_to_noise_recorded_for_the_sheet'): _judge_signal_to_noise,
          ('relaxation', 'relaxation_recorded_for_the_sheet'): _judge_relaxation, ('progress_curve_points', 'time_points_recorded_for_the_sheet'): _judge_time_points,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _stated_effect(native, quantity, ref):
    """The stated quantity as an effect operand in its anchor unit, or None when not stated (its 'support' is the extraction's)."""
    operand = native['quantities'][quantity]
    if operand['status'] != 'point':
        return None
    unit, factors = UNIT_FACTORS[quantity]
    return _operand(operand['value'] * factors[operand['unit']], unit, 'nmr_timecourse_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


def _variance(graded, quantity, ref):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of ``quantity``."""
    native = graded['native']
    spread = native['quantities'][quantity + '_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, quantity + '_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    unit, factors = UNIT_FACTORS[quantity]
    sd = spread['value'] * factors[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_nmr_timecourse(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {quantity: _stated_effect(native, quantity, ref) for quantity in UNIT_FACTORS}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_activity_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_activity_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_QUANTITY[chosen], effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'nmr_timecourse_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
    null_components.update({role: reason for role, reason in NULL_REASONS.items()})
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
        interpretations[sheet_criterion] = apply_support(interpretations[sheet_criterion], supports)      # weak quote support lowers the degree of a supported criterion, never its status
    if quantities['effect_variance'] is not None:
        interpretations['variance_correspondence'] = {'status': 'supported', 'support_refs': quantities['effect_variance']['source_refs']}
    extraction = {'version': INPUT_VERSION, 'assay_type': 'activity_rate', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    mass = native['quantities']['enzyme_mass']
    result = {'version': VERSION, 'experiment_type': 'nmr_timecourse', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support,
              'enzyme_mass_g_per_mol': mass['value'] * GRAMS_PER_MOL_PER_KDA if mass['status'] == 'point' else None}
    if quantities['effect'] is None and native['activity'] is not None:      # no stated quantity: the paper's own statement of activity above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['activity']], 'support_refs': list(native['activity_refs'])}
        result['direction_field_support'] = native['activity_support']
    return result
