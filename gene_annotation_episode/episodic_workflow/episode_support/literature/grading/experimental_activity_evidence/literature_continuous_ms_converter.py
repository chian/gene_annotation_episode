"""Continuous_ms converter: turns the grader's result into what the A105 activity_rate sheet takes.

Hand-built, private to continuous_ms, deterministic. Input: the result of grade_continuous_ms. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'activity_rate'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, the
enzyme's molar mass the direction function needs, and for every sheet component that an activity measurement cannot honestly fill, the
reason it stays null. A DRAFT (2026-11-22) built on the structure of spectro_direct: all numbers EXPERT_REVIEW, owner to confirm, and every
literature citation is from memory and NOT verified.

The assay: the reaction is followed live in the mass spectrometer (a membrane inlet for dissolved gases and volatile products such as CO2, O2 and
H2, or online electrospray); the ion current at the mass of the product is turned into a concentration with known standards and its initial slope
is the rate; an isotope label often gives the product a mass of its own. The past case is Moral et al. 2011 (Anal Biochem 418:73, oxalate
decarboxylase by MIMS against a formate-dehydrogenase-coupled end point).

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: catalytic efficiency kcat/Km (M^-1s^-1), turnover kcat (s^-1),
                  specific activity (U/mg) or the rate over the paper's own control (fold). Several may be stated; the one used is the
                  best-determined, in the class order ACTIVITY_EFFECT_ORDER (literature_activity_direction.select_activity_effect). A stated
                  value in another unit of the record's vocabulary is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION): the
                  value is the paper's, only its unit spelling changes. quantity_kind of the extraction names the kind of the effect
                  (KIND_OF_QUANTITY), which the direction function reads.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).
enzyme_mass_g_per_mol   the enzyme's molar mass in g/mol (the stated mass in kDa times 1000), or None.
qualitative_effect  the result stated in words. Only when NO effect is stated and the paper states whether it saw activity above its own control:
                  statement 'interaction_detected' (read "activity detected") or 'interaction_not_detected' (read "activity not detected"), with
                  the refs of the fact that states it. direction_field_support is the quote support of that one fact. A result stated in words
                  alone already counts less than a measured one (literature_row_contract.stated_strength); nothing is done about that here.
                  A stated effect fixes the direction; the statement is then not used.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives   spontaneous_reaction_control + substrate_independent_signal
attribution_supported     enzyme_dependence + product_identity
calibration_applicability  calibration_with_standards + calibration_linearity
matrix_interference       matrix_matched_calibration
rate_regime               initial_rate_regime + response_time_window + enzyme_substrate_ratio
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
partner_perturbation) are not selected.

Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None (no immobilized enzyme, no electrode). Qualitative
statements keep the existing vocabulary. Direction and strength of a stated rate: literature_activity_direction (larger is stronger); controls,
blanks and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a
wrong value misleads and whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not
verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
CALIBRATION_RESIDUAL_FULL 0.01 -> CALIBRATION_RESIDUAL_ZERO 0.2, judged on the log of 1 - R squared of the calibration line.
  Q1 an ion current converted to a concentration with a line that does not follow its standards, so the absolute rate (and so kcat and the
  specific activity) is off by the scatter of the line. Q2 general: bioanalytical practice asks for a calibration line with R squared of about 0.99
  or better (ICH M10 and FDA bioanalytical method validation, as used for mass spectrometry; from memory); the 0.2 end is a judgement. Q3 absolute (a
  number the paper states about its own line); the grader records it. Q4 1 - R squared is the share of the standards' variance the line leaves
  unexplained, and the relative scatter of a reading about that line goes as its square root: about 10 percent at 0.01 and about 45 percent at 0.2,
  where the line no longer fixes a rate; so the degree is linear in the LOG of 1 - R squared (the scatter spans decades and is multiplicative); at or
  beyond R squared 0.8 the paper's own line shows the standard is not met (conflicting). A line through two or three points has an R squared near 1
  without meaning much: the number of standards is not collected (a grader gap, below). Q5 a log-ratio ramp like the other ratio judgements; no
  other activity type has a calibration line.
WINDOW_FULL_OVER_TAU 20 -> WINDOW_ZERO_OVER_TAU 1, judged on the bias of the rate averaged over the window.
  Q1 an "initial rate" taken over a window that is short against the response time of the inlet: the ion current is a lagging copy of the reaction
  and the slope over the window is partly the lag. Q2 general physics of a first-order lag (the membrane of a MIMS probe: a response time of seconds to
  tens of seconds is usual; from memory) and a transfer delay for online electrospray, treated the same way as the worst case. Q3 relative to the
  paper's own response time (the time to 90 percent of a step, t90), which the grader collects with the window; tau = t90 / ln 10. Q4 a ramp through a
  first-order lag has, averaged over a window T that starts with the reaction, a slope short of the true slope by the fraction (tau / T) (1 - exp(-T / tau)):
  0.05 at T = 20 tau, 0.10 at 10 tau, 0.20 at 5 tau, 0.63 at T = tau. The degree is linear in that bias between its two ends; the full end is the bias of 5
  percent, the same bias as the 10 percent consumed end of the initial-rate judgement; the zero end T = tau is a bias of 63 percent, about the 61 percent
  of the 90 percent consumed end of that judgement; at or beyond it the window is only the lag (conflicting). It is a worst case: a rate taken from a
  window that starts after the lag is not biased, and the passage rarely says where the window starts (a grader gap, below), so the degree lowers the
  weight only. Q5 the same bias idea as the initial-rate and absorbance-range judgements of spectro_direct.
CONSUMED_FULL_PERCENT 10 -> CONSUMED_ZERO_PERCENT 90, judged on the bias of the average rate.
  Q1 an "initial rate" that is really the average over a progress curve that has already bent, so the rate is too low. Q2 general: initial
  velocity means at most about 10 percent of the substrate consumed (Cornish-Bowden, Fundamentals of Enzyme Kinetics; Copeland, Enzymes; NCBI Assay
  Guidance Manual, Basics of Enzymatic Assays), from memory. Q3 relative to the paper's own substrate, which the passage states as a share. Q4 for a
  first-order progress curve (the worst case) the rate averaged over the window is f / -ln(1 - f) of the initial rate: 0.95 at 10 percent, 0.72 at 50,
  0.39 at 90; the degree is linear in that bias. At or beyond 90 percent the rate is an end point (conflicting). Q5 as spectro_direct. A mass
  spectrometer reads the substrate or the product as it goes, so a stated share consumed is as usual here as there.
ENZYME_RATIO_FULL 0.01 -> ENZYME_RATIO_ZERO 1.0, judged on the log of E / (S + Km).
  Q1 the steady-state rate law holds only while the enzyme is small against the substrate plus the Km. Q2 general: the validity parameter E0 / (S0 + Km)
  of the quasi-steady-state equation (Segel and Slemrod 1989, SIAM Rev 31:446), from memory. Q3 relative to the paper's own S and Km. Q4 an error of
  about the value of the ratio: 1 percent at 0.01, unusable at 1; linear in the log of the ratio. Q5 as spectro_direct (the same physics; MIMS assays use
  micromolar enzyme against millimolar substrate, which is inside the full end).
MIN_SUBSTRATE_CONCENTRATIONS 6, SUBSTRATE_CONCENTRATIONS_ZERO 2.
  Q1 a Km fitted to too few substrate concentrations. Q2 general: a saturation curve of about six to eight concentrations spanning 0.2 to 10 times the Km
  (Cornish-Bowden; Copeland; NCBI Assay Guidance Manual), from memory. Q3 absolute (a count). Q4 two parameters (Km and Vmax) use up two concentrations and
  leave no residual degree of freedom (degree 0, never conflicting); the degree rises linearly with count - 2. Q5 as spectro_direct.
LOW_FACTOR 0.2 -> LOW_ZERO_FACTOR 1.0, HIGH_FACTOR 10 -> HIGH_ZERO_FACTOR 1.0 (the lowest and highest substrate over the Km).
  Q1 a series that does not bracket the Km. Q2 general: 0.2 to 10 times the Km (the references above), from memory. Q3 relative to the paper's own Km.
  Q4 v / Vmax = S / (S + Km): both ends are judged linearly in the fractional saturation. Q5 SOP working rule d: 10 where the plateau (Vmax) is a free
  amplitude known only by reaching it.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a rate from one experiment, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice). Q3 absolute count. Q4 precision of a
  mean (1 / sqrt(n)). Q5 exactly the shared replicate rule.
Facts with no number (the controls, the enzyme dependence, the signal specific to the product, the calibration with standards, the matrix-matched
calibration, the active-site determination, the native substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is
conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the value of the response time or of the window by
itself (only their ratio matters); the mode of the instrument (membrane inlet or electrospray) and the monitored mass, which are context; the pH and the
temperature (the claim carries no condition, and the identity block records the temperature).

Grader gaps (a needed fact the grader does not collect; adding it changes the record, the form and the passages and needs a real-model run): the number
of calibration standards; where the rate window starts against the start of the reaction (after the lag or at the mixing); the baseline drift of the ion
current beside the rate.

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered
for this assay, decided 2026-11-22 (draft), owner to confirm:
  What does it measure; absolute or relative? The rate of formation of a product (or loss of a substrate) read by its mass, turned into an absolute rate
  by calibration with standards: absolute when calibrated, and then kcat, Km and kcat/Km are well defined; relative (a fold over the baseline) when not.
  Is there a reference range we would trust if the paper stated less (as for KD)? Yes for the enzyme (the range of kcat and kcat/Km, Bar-Even et al.
  2011, from memory), but NOT for the instrument: unlike the extinction coefficient of NADH, no constant is known for a calibration of a given probe,
  so an unstated calibration leaves the absolute scale open.
  What does an unstated control or calibration do to the number's meaning? An unstated blank is benign for a strong rate but is the main false positive
  for a weak one (leak, drift and the enzyme preparation giving off the monitored species); an unstated calibration changes the magnitude by an unknown
  factor and not the existence of the activity; a mass is more specific to the product than an absorbance, so contamination of the signal is less likely.
  If we assume it is fine and are wrong, how badly does the score mislead? A magnitude wrong by a factor (calibration) is milder than a false activity
  (blank).
  Consistent with KD and with spectro_direct? The default 0.85 is the same as spectro_direct (a mass-specific signal is a little safer, an instrument
  calibration a little less standard: they cancel); the calibration and matrix criteria are lower (0.80); the attribution criterion is the default
  (the mass makes it less at risk); the blank is as there (0.75); normalization and sampling as there (0.90).
  default 0.85. background_alternatives 0.75. calibration_applicability 0.80. matrix_interference 0.80. normalization_basis 0.90, sampling_basis 0.90.
  rate_regime, kinetic_model, attribution_supported, assertion_relevance, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_activity_direction import select_activity_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_continuous_ms_converted'
CRITERIA_MAP = {'background_alternatives': ('spontaneous_reaction_control', 'substrate_independent_signal'), 'attribution_supported': ('enzyme_dependence', 'product_identity'),
                'calibration_applicability': ('calibration_with_standards', 'calibration_linearity'), 'matrix_interference': ('matrix_matched_calibration',),
                'rate_regime': ('initial_rate_regime', 'response_time_window', 'enzyme_substrate_ratio'), 'kinetic_model': ('substrate_range',),
                'normalization_basis': ('active_enzyme_amount',), 'sampling_basis': ('replicates',), 'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
GRAMS_PER_MOL_PER_KDA = 1000.0  # FIXED_BY_DEFINITION: 1 kDa is 1000 g/mol.
LN10 = math.log(10.0)  # FIXED_BY_DEFINITION: for a first-order lag the time to 90 percent of a step is tau ln 10, so a window over t90 times ln 10 is the window over tau.
CALIBRATION_RESIDUAL_FULL = 0.01  # EXPERT_REVIEW, owner to confirm: 1 - R squared of the calibration line at 0.01 (R squared 0.99, the usual bioanalytical expectation for a calibration line, from memory, not verified); full agreement up to it; the relative scatter of a reading is about 10 percent there.
CALIBRATION_RESIDUAL_ZERO = 0.2  # EXPERT_REVIEW, owner to confirm: 1 - R squared at 0.2 (R squared 0.8): the line leaves a fifth of the standards' variance unexplained, a relative scatter of about 45 percent, so it no longer fixes an absolute rate (no agreement); the degree falls linearly in the log of 1 - R squared from the full end to here, because the scatter spans decades.
WINDOW_FULL_OVER_TAU = 20.0  # EXPERT_REVIEW, owner to confirm: rate window over the time constant of the inlet at 20: a ramp through a first-order lag, averaged over the window, falls short of the true slope by 5 percent (the same bias as the 10 percent consumed end of the initial-rate judgement); full agreement from it.
WINDOW_ZERO_OVER_TAU = 1.0  # EXPERT_REVIEW, owner to confirm: window as long as the time constant: the averaged slope falls short by 63 percent (about the 61 percent of the 90 percent consumed end), the window is only the lag (no agreement); the degree falls linearly in the bias (tau / T)(1 - exp(-T / tau)) from the full end to here.
CONSUMED_FULL_PERCENT = 10.0  # EXPERT_REVIEW, owner to confirm: at most about 10 percent of the substrate consumed in the window of an initial rate (Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory); full agreement up to it.
CONSUMED_ZERO_PERCENT = 90.0  # EXPERT_REVIEW, owner to confirm: at 90 percent consumed the rate averaged over a first-order progress curve (the worst case) is 0.39 of the initial rate: an end point, not a rate (no agreement); the degree falls linearly in the bias 1 - f / -ln(1 - f) of the average rate from the full end to here.
ENZYME_RATIO_FULL = 0.01  # EXPERT_REVIEW, owner to confirm: the validity parameter E / (S + Km) of the steady-state rate law (Segel and Slemrod 1989, from memory) at 0.01, about 1 percent error; full agreement up to it.
ENZYME_RATIO_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: enzyme as large as substrate plus Km: the steady-state law does not describe the reaction (no agreement); falls from ENZYME_RATIO_FULL linearly in the log of the ratio, because the error of the rate is proportional to it.
MIN_SUBSTRATE_CONCENTRATIONS = 6  # EXPERT_REVIEW, owner to confirm: fewest substrate concentrations of a usable saturation curve (about six to eight, Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory); full agreement from it.
SUBSTRATE_CONCENTRATIONS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: the Michaelis-Menten equation has two parameters (Km, Vmax), so two concentrations are used up by the fit and leave no residual degree of freedom (degree 0, supported, never conflicting: a short series is weaker evidence); between this and MIN_SUBSTRATE_CONCENTRATIONS the degree rises linearly with the residual degrees of freedom (count - 2).
LOW_FACTOR = 0.2  # EXPERT_REVIEW, owner to confirm: the lowest substrate should be at most this multiple of the Km (v is 1/6 of Vmax there); full agreement up to it.
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: lowest substrate at the Km itself leaves the lower half of the hyperbola undefined (no agreement); falls from LOW_FACTOR linearly in the fractional saturation S / (S + Km).
HIGH_FACTOR = 10.0  # EXPERT_REVIEW, owner to confirm: the highest substrate should be at least this multiple of the Km (v is 10/11 of Vmax); Vmax is a free amplitude known only by reaching it (SOP rule d: 10 for a free plateau); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: highest substrate at the Km itself never reaches saturation (no agreement); falls from HIGH_FACTOR linearly in the fractional saturation S / (S + Km).
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
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
NULL_REASONS = {'recovery': 'continuous_ms_has_no_matrix_recovery_measurement', 'attributed_signal': 'an_ion_current_rate_is_not_an_attribution_fraction', 'total_signal': 'an_ion_current_rate_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_continuous_ms_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_continuous_ms_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENT = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected'}   # read "activity detected" / "activity not detected" for this class


def _verdict(status, refs, degree=None):
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError('a ' + status + ' judgement needs support refs')
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _linear(value):
    """The scale of a quantity whose error is additive."""
    return value


def _degree(value, full, zero, scale=_linear):
    """1.0 at ``full`` (or beyond it), falling linearly in ``scale`` to 0 at ``zero`` (the limits may lie on either side of each other); None at or beyond ``zero``.
    ``scale`` is monotone, so both side tests are made on the value itself, before the scale could see a value it cannot take (a log of 0)."""
    if (value - zero) * (full - zero) <= 0:
        return None
    if (value - full) * (zero - full) <= 0:
        return 1.0
    return (scale(value) - scale(zero)) / (scale(full) - scale(zero))


def _graded(refs, *limits):
    """Each limit is (value, full_agreement_limit, zero_agreement_limit[, scale]). Conflicting when any value is at or beyond its zero limit; else supported with the smallest degree."""
    degrees = [_degree(*limit) for limit in limits]
    if None in degrees:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(degrees))


def _saturation(ratio):
    """Fractional saturation S / (S + Km) of a substrate S given as S / Km: where on the hyperbola it sits."""
    return ratio / (1 + ratio)


def _average_rate_bias(fraction):
    """The shortfall 1 - f / -ln(1 - f) of the rate averaged over a first-order progress curve that has consumed the fraction f of the substrate."""
    return 1.0 - fraction / -math.log1p(-fraction)


def _lag_bias(window_over_tau):
    """The shortfall (tau / T)(1 - exp(-T / tau)) of the slope averaged over a window T from the start of a ramp read through a first-order lag of time constant tau."""
    return (1.0 - math.exp(-window_over_tau)) / window_over_tau


def _judge_calibration(native):
    return _graded(native['calibration_refs'], (1.0 - native['calibration_r_squared'], CALIBRATION_RESIDUAL_FULL, CALIBRATION_RESIDUAL_ZERO, math.log))


def _judge_regime(native):
    fraction = native['consumed_percent'] / PERCENT_PER_FRACTION
    return _graded(native['consumed_refs'], (fraction, CONSUMED_FULL_PERCENT / PERCENT_PER_FRACTION, CONSUMED_ZERO_PERCENT / PERCENT_PER_FRACTION, _average_rate_bias))


def _judge_response(native):
    window_over_tau = native['rate_window_over_response_time'] * LN10      # the recorded ratio is over t90; tau is t90 / ln 10
    return _graded(native['response_refs'], (window_over_tau, WINDOW_FULL_OVER_TAU, WINDOW_ZERO_OVER_TAU, _lag_bias))


def _judge_enzyme_ratio(native):
    return _graded(native['enzyme_ratio_refs'], (native['enzyme_over_substrate_plus_km'], ENZYME_RATIO_FULL, ENZYME_RATIO_ZERO, math.log))


def _judge_series(native):
    # the two ratios keep their ramps (conflicting at their zero end), judged on the fractional saturation; the lower end is judged only when the series
    # has one distinct from its upper end (one concentration is a short series, not a badly placed one). The count only lowers the degree, never conflicts.
    refs = native['concentration_refs']
    low, high = native['concentration_low_over_km'], native['concentration_high_over_km']
    limits = [(high, HIGH_FACTOR, HIGH_ZERO_FACTOR, _saturation)]
    if low < high:
        limits.append((low, LOW_FACTOR, LOW_ZERO_FACTOR, _saturation))
    verdict = _graded(refs, *limits)
    if verdict['status'] == 'conflicting':
        return verdict
    count_degree = max(0.0, min(1.0, (native['concentration_count'] - SUBSTRATE_CONCENTRATIONS_ZERO) / (MIN_SUBSTRATE_CONCENTRATIONS - SUBSTRATE_CONCENTRATIONS_ZERO)))
    return _verdict('supported', refs, min(verdict['degree'], count_degree))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('calibration_linearity', 'calibration_r_squared_recorded_for_the_sheet'): _judge_calibration, ('initial_rate_regime', 'consumed_recorded_for_the_sheet'): _judge_regime,
          ('response_time_window', 'response_time_recorded_for_the_sheet'): _judge_response, ('enzyme_substrate_ratio', 'enzyme_ratio_recorded_for_the_sheet'): _judge_enzyme_ratio,
          ('substrate_range', 'substrate_series_recorded_for_the_sheet'): _judge_series, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'continuous_ms_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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


def convert_continuous_ms(graded):
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
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'continuous_ms_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    result = {'version': VERSION, 'experiment_type': 'continuous_ms', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support,
              'enzyme_mass_g_per_mol': mass['value'] * GRAMS_PER_MOL_PER_KDA if mass['status'] == 'point' else None}
    if quantities['effect'] is None and native['activity'] is not None:      # no stated quantity: the paper's own statement of activity above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['activity']], 'support_refs': list(native['activity_refs'])}
        result['direction_field_support'] = native['activity_support']
    return result
