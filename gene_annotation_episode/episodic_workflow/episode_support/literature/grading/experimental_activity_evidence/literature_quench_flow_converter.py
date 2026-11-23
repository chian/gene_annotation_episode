"""Quench_flow converter: turns the grader's result into what the A105 activity_rate sheet takes.

Hand-built, private to quench_flow, deterministic. Input: the result of grade_quench_flow. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'activity_rate'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, the
enzyme's molar mass the direction function needs (None here: no specific activity is stated by this method), and for every sheet component that
a quench-flow experiment cannot honestly fill, the reason it stays null. Built 2026-11-22 as a first draft from the structure of the
spectro_direct converter; every number is EXPERT_REVIEW, owner to confirm, and every literature citation is from the drafter's memory, NOT verified.

Quantities filled
-----------------
effect            ONE stated rate per enzyme in s^-1, quantity_kind 'turnover': the steady-state turnover (k_ss or kcat after the burst) when the
                  passage states it, else the observed rate constant of the single-turnover or burst phase (k_obs, k_chem). The first is the
                  quantity the class anchors are built on (kcat). The second is the rate constant of a chemical step, which is never smaller
                  than kcat, so on the kcat scale it can only read generously; it is used because it is the one number the method exists to
                  measure and because, when the passage states no steady-state turnover, nothing better is stated. The class has no step-rate
                  kind (reported to the owner). A stated value in min^-1 is multiplied by its exact factor (FIXED_BY_DEFINITION): the value is
                  the paper's, only its unit spelling changes.
effect_variance   variance of that effect, in s^-1 squared, only when the passage's spread of THAT quantity allows it: standard_error -> se^2;
                  standard_deviation -> sd^2 / n and only when the replicates criterion is supported; confidence_interval -> not converted
                  (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).
enzyme_mass_g_per_mol   None: a quench-flow experiment states a rate per enzyme, not a specific activity, so the direction function needs no mass.
qualitative_effect  only when NO effect is stated and the paper states whether product formed above its own control (the zero-time or no-enzyme
                  control): statement 'interaction_detected' (read "activity detected") or 'interaction_not_detected' (read "activity not
                  detected"), with the refs of the fact that states it; direction_field_support is the quote support of that one fact. A stated
                  effect fixes the direction; the statement is then not used. A result stated in words alone already counts less than a
                  measured one (the contract's stated_strength); that is not repeated here.
A burst amplitude with no rate constant fills no effect: it is the share of the enzyme in the burst, not a rate.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives    zero_time_control + no_enzyme_control
matrix_interference        quench_efficiency (sample handling: the quench must stop the reaction before the product is counted)
attribution_supported      enzyme_dependence + product_identity
calibration_applicability  product_calibration
rate_regime                enzyme_substrate_ratio + time_range
kinetic_model              time_course_fit + time_points
normalization_basis        active_enzyme_amount + burst_stoichiometry
sampling_basis             replicates
assertion_relevance        native_reaction
condition_scope            purified_enzyme
variance_correspondence    supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in
'_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Each judgement is a researched value of THIS assay made
gradual (SOP step 3): full agreement at the researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the
scale the physics of the assay gives (never a step), unknown when the paper states nothing, never conflicting for a short count. A value at or
beyond its zero end of a ramp that has a conflicting end is conflicting (what the paper itself shows against the standard). A sheet criterion that
is supported carries the smallest degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of
a supported criterion and never changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported.
not_applicable members are dropped; a sheet criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here
(measurement_identity, partner_perturbation) are not selected.

How the class decisions apply here (2026-11-21, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys
stay None (no immobilized enzyme, no electrode). Qualitative statements keep the existing vocabulary. Direction and strength of a stated rate:
literature_activity_direction (larger is stronger); controls, blanks and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a
wrong value misleads and whether the shape fits, Q5 consistency with the other assays). The method literature behind all of it is, from memory and
not verified: K. A. Johnson, Methods Enzymol 134:677 (1986), and 249:38 (1995), on rapid quench kinetics and the design of burst and single-turnover
experiments; C. A. Fierke and G. G. Hammes, Methods Enzymol 249:3 (1995), on transient-state approaches; A. Fersht, Structure and Mechanism in Protein
Science (1999), chapter 4. Every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
SINGLE_TURNOVER_SUBSTRATE_OVER_ENZYME_FULL 0.1 -> SINGLE_TURNOVER_SUBSTRATE_OVER_ENZYME_ZERO 1.0, linear in the substrate over the enzyme.
  Q1 a "single turnover" run with so much substrate that the enzyme turns over more than once, so the exponential is the sum of a burst and a
  slower phase and its rate constant is not that of the chemical step. Q2 general: single-turnover conditions mean the enzyme in excess, and the
  textbook rule for a pseudo-first-order reaction is an excess of ten (Fersht; Johnson), from memory; tight binding of the substrate lets a smaller
  excess serve, which is why the ramp is gradual and not a cut at ten. Q3 relative to the paper's own concentrations, which the grader records
  (after mixing); right. Q4 the error of treating the reaction as pseudo-first-order grows in proportion to the substrate over the enzyme (about
  ten percent at one to ten), so the degree is linear in that ratio from full at 0.1 to zero at 1.0, where the substrate is as plentiful as the
  enzyme and nothing is in excess (at or beyond it: conflicting, the paper's own numbers contradict the single-turnover design it states). Q5 a
  ratio ramp in the same spirit as the enzyme over the substrate plus the Km of spectro_direct, with the ratio itself (not its log) because here the
  error is proportional to the ratio and the range is one decade.
MULTIPLE_TURNOVER_ENZYME_OVER_SUBSTRATE_FULL 0.1 -> MULTIPLE_TURNOVER_ENZYME_OVER_SUBSTRATE_ZERO 1.0, linear in the enzyme over the substrate.
  Q1 a burst experiment with so little substrate that the burst uses it up, so there is no steady-state line to separate the burst from, and the
  substrate falls during the burst. Q2 general: the burst design needs the substrate in excess of the enzyme by several fold, and the burst takes the
  share enzyme over substrate of the substrate (Johnson 1986, from memory); one tenth is the same share of substrate consumed as the ten percent of
  an initial rate (Cornish-Bowden; Copeland, from memory). Q3 relative to the paper's own concentrations: right. Q4 the share of substrate used by
  the burst is exactly the enzyme over the substrate (for a burst of one per enzyme), so the degree is linear in it between 0.1 (full) and 1.0
  (zero: the burst uses all the substrate; conflicting). Q5 the same share-consumed idea as the initial-rate ramp of spectro_direct.
FIRST_POINT_COMPLETED_FULL 0.10 -> FIRST_POINT_COMPLETED_ZERO 0.95, linear in the fraction of the phase done before the earliest time point.
  Q1 an earliest time point so late that much of the rise is over before it is measured, so the rate constant is extrapolated and the amplitude
  is cut off (the rate is faster than the instrument or the manual quench can resolve). Q2 general: a rate constant is defined when time points
  fall on its rise; the fraction of an exponential done at the first point is 1 - exp(-k t_first) (physics); a tenth is a point on the early rise,
  0.95 is three lifetimes, where the whole phase is over before the first point (from memory of the usual advice to span about 0.1 to 3 lifetimes).
  Q3 relative to the paper's own rate constant: right, and the grader records k t_first. Q4 the information in the rise falls with the fraction
  already done, so the ramp is linear in that fraction; at or beyond 0.95 nothing of the rise is seen (conflicting). Q5 no other assay of the class
  has a time window against a rate constant (stopped_flow will have the dead time).
LAST_POINT_COMPLETED_FULL 0.95 -> LAST_POINT_COMPLETED_ZERO 0.50, linear in the fraction of the phase done by the latest time point.
  Q1 a time course that stops before the phase is over, so the amplitude and the rate constant cannot be separated. Q2 general: about three lifetimes
  (95 percent) define the plateau or the start of the steady-state line (from memory); at one half-life (50 percent) the amplitude is an
  extrapolation. Q3 relative to the paper's own rate constant: right. Q4 the amplitude and the rate constant of an exponential fitted to less than a
  half-life are strongly correlated, so the ramp is linear in the fraction done between 0.95 and 0.5; at or before 0.5 it is conflicting. Q5 as
  above.
MIN_TIME_POINTS 10 -> TIME_POINTS_ZERO 3, linear in the residual degrees of freedom (n - 3 against 10 - 3).
  Q1 a rate constant fitted to a few time points, whose fit has no residual to show it is an exponential. Q2 general: a quench-flow time course
  usually has about eight to fifteen reaction times (Johnson 1995, from memory); ten is a judgement. Q3 absolute (a count). Q4 the burst equation has
  three parameters (amplitude, rate constant, steady-state rate) and the single exponential two: three points leave the burst fit no residual degree
  of freedom (degree 0, supported, never conflicting), and each added time point adds one. Q5 the same residual-degree-of-freedom count as the
  substrate series of spectro_direct (there two parameters, six concentrations).
BURST_PER_ENZYME_FULL 0.8 -> BURST_PER_ENZYME_ZERO 0.1, linear in the LOG of the amplitude per enzyme; supported at every value, never conflicting.
  Q1 a rate stated per total enzyme when only part of the enzyme is active (the burst makes about one product per active site, so an amplitude of
  0.3 per enzyme says about a third is active, or that only some sites react), so the rate per active site is higher than the rate per enzyme
  stated. Q2 general: a burst of about one per active site is the classic result of a fast chemical step with slow product release (Johnson), and
  active-site concentrations are often taken from the burst itself; half-of-the-sites reactivity gives one half, which is a real enzyme property, not
  a fault; the numbers are practice estimates, from memory. Q3 relative to the paper's own enzyme concentration: right. Q4 the rate per enzyme is
  off by the factor one over the amplitude per enzyme (25 percent at 0.8, tenfold at 0.1), so the ramp is linear in the log of the amplitude; a
  tenth is also where the burst can hardly be told from the zero-time product. An amplitude above one is not judged (the enzyme concentration may be
  low or the burst be real stoichiometry of a multisite enzyme; the converter has no ground to call it worse). No conflicting end: a small burst is a
  property of the enzyme sample, and a paper that reports it plainly is not shown wrong. Q5 the log-ratio shape of the other ratio ramps.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a rate from one experiment, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice; quench-flow experiments are
  costly and often few). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared
  replicate rule.
Facts with no number (the zero-time control, the no-enzyme control, the quench efficiency, the enzyme dependence, the product identity, the product
standard, the fit, the active-site determination, the native substrate and the purified enzyme): the paper's own statement decides; yes is
supported, no is conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the dead time and the quench
chemistry (a plain choice carries no span and the shortest time already shows the resolution); the temperature and the pH (the claim carries no
condition, and the identity block records the temperature); a burst amplitude above one per enzyme.

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered
for this assay, drafted 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? Product amounts (uM, or a fraction of the enzyme) against time at known concentrations, from which
  a rate constant and an amplitude are fitted: absolute, with the rate constants well defined.
  Is there a reference range we would trust if the paper stated less? Yes: the range of enzyme rate constants is the one the class anchors are built
  on (Bar-Even et al. 2011, from memory), and the method is run by specialist laboratories that know its controls.
  What does an unstated control or calibration do to the number's meaning? The product is separated and counted, so it is not an optical proxy:
  an unstated product identity or standard is usually benign. An unstated zero-time control or quench test is a real gap (a leaking quench gives a
  false burst), but the experiment is rarely published without it.
  If we assume it is fine and are wrong, how badly does the score mislead? A leaking quench or a background product inflates a fast rate or an
  amplitude; the direction survives unless the rate is weak.
  Consistent with KD and with spectro_direct? The default 0.85 equals spectro_direct (an absolute rate with a known reference range); the criteria
  that guard against a false product are lower (the control), the ones that product separation already settles are higher.
  default 0.85. background_alternatives 0.80 (the zero-time control separates a real burst from the product present at time zero and from quench
  leaks; common practice but often not said, above the 0.75 of the optical blank because the product itself is identified). attribution_supported
  0.90 (the product is separated and identified by the method itself). calibration_applicability 0.90 (a specific radioactivity or a standard curve
  is the routine). normalization_basis 0.90, sampling_basis 0.90 (benign when unstated, as for spectro_direct). matrix_interference 0.80 (the quench
  efficiency is the one test that a quench-flow experiment cannot do without, and a failed quench is the characteristic artefact of the method).
  rate_regime, kinetic_model, assertion_relevance, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_activity_direction import select_activity_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_quench_flow_converted'
CRITERIA_MAP = {'background_alternatives': ('zero_time_control', 'no_enzyme_control'), 'matrix_interference': ('quench_efficiency',),
                'attribution_supported': ('enzyme_dependence', 'product_identity'), 'calibration_applicability': ('product_calibration',),
                'rate_regime': ('enzyme_substrate_ratio', 'time_range'), 'kinetic_model': ('time_course_fit', 'time_points'),
                'normalization_basis': ('active_enzyme_amount', 'burst_stoichiometry'), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
SINGLE_TURNOVER_SUBSTRATE_OVER_ENZYME_FULL = 0.1  # EXPERT_REVIEW, owner to confirm: single turnover wants the enzyme in excess; the error of the pseudo-first-order reading is about the substrate over the enzyme, ten percent at one to ten (Fersht; Johnson 1986, from memory); full agreement up to it.
SINGLE_TURNOVER_SUBSTRATE_OVER_ENZYME_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: substrate as plentiful as the enzyme: nothing is in excess and the stated single-turnover design is contradicted by the paper's own concentrations (no agreement; conflicting); the degree falls linearly in the ratio from the full end to here.
MULTIPLE_TURNOVER_ENZYME_OVER_SUBSTRATE_FULL = 0.1  # EXPERT_REVIEW, owner to confirm: a burst takes the share enzyme over substrate of the substrate; one tenth is the ten percent of substrate consumed of an initial rate (Johnson 1986; Cornish-Bowden, from memory); full agreement up to it.
MULTIPLE_TURNOVER_ENZYME_OVER_SUBSTRATE_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: the burst uses all the substrate and no steady-state line remains (no agreement; conflicting); the degree falls linearly in the share consumed from the full end to here.
FIRST_POINT_COMPLETED_FULL = 0.10  # EXPERT_REVIEW, owner to confirm: at most a tenth of the phase done before the earliest time point, so points fall on the rise (physics of an exponential, 1 - exp(-k t); from memory of the usual advice to span about 0.1 to 3 lifetimes); full agreement up to it.
FIRST_POINT_COMPLETED_ZERO = 0.95  # EXPERT_REVIEW, owner to confirm: three lifetimes: the whole phase is over before the first point and the rate is unresolved (no agreement; conflicting); the degree falls linearly in the fraction done.
LAST_POINT_COMPLETED_FULL = 0.95  # EXPERT_REVIEW, owner to confirm: the latest point is three lifetimes out, so the plateau or the steady-state line is defined (from memory); full agreement from it.
LAST_POINT_COMPLETED_ZERO = 0.50  # EXPERT_REVIEW, owner to confirm: the latest point is one half-life out: the amplitude and the rate constant of the fit cannot be separated (no agreement; conflicting); the degree falls linearly in the fraction done between the two ends.
MIN_TIME_POINTS = 10  # EXPERT_REVIEW, owner to confirm: about eight to fifteen reaction times in a quench-flow time course (Johnson 1995, from memory); full agreement from it.
TIME_POINTS_ZERO = 3  # EXPERT_REVIEW, owner to confirm: the burst equation has three parameters (amplitude, rate constant, steady-state rate), so three points leave no residual degree of freedom (degree 0, supported, never conflicting); between this and MIN_TIME_POINTS the degree rises linearly with the residual degrees of freedom (count - 3).
BURST_PER_ENZYME_FULL = 0.8  # EXPERT_REVIEW, owner to confirm: a burst of at least four fifths of an enzyme's worth of product means the rate per enzyme is within 25 percent of the rate per active site (practice estimate, from memory); full agreement from it.
BURST_PER_ENZYME_ZERO = 0.1  # EXPERT_REVIEW, owner to confirm: a tenth: the rate per enzyme is tenfold under the rate per active site and the burst can hardly be told from the zero-time product (degree 0, supported, never conflicting); the degree falls linearly in the log of the amplitude from the full end to here.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The effect: rates per enzyme in s^-1 (the anchor unit of the class quantity 'turnover', literature_row_contract.ACTIVITY_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
EFFECT_UNIT = 's^-1'
RATE_FACTORS = {'s^-1': 1.0, 'min^-1': 1.0 / SECONDS_PER_MINUTE}   # FIXED_BY_DEFINITION: exact unit conversion (60 s is 1 min); the stated number is the paper's.
EFFECT_SOURCES = ('turnover', 'chemical_rate_constant')   # the record quantity the effect is read from, in order: the steady-state turnover (kcat) first
KIND_OF_EFFECT = 'turnover'   # the quantity_kind (QUANTITY_KINDS['activity_rate']) of the effect; literature_activity_direction.ACTIVITY_QUANTITY_OF_KIND reads it back
KIND_WITHOUT_EFFECT = 'rate'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'quench_flow_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_quenched_product_rate_is_not_an_attribution_fraction', 'total_signal': 'a_quenched_product_rate_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_quench_flow_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_quench_flow_record',
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


def _completed(rate_times_time):
    """The fraction of a first-order phase done at a time t, given k t: 1 - exp(-k t)."""
    return -math.expm1(-rate_times_time)


def _judge_ratio(native):
    refs, ratio = native['ratio_refs'], native['substrate_over_enzyme']
    if native['turnover_design'] == 'single_turnover':
        return _graded(refs, (ratio, SINGLE_TURNOVER_SUBSTRATE_OVER_ENZYME_FULL, SINGLE_TURNOVER_SUBSTRATE_OVER_ENZYME_ZERO))
    return _graded(refs, (1.0 / ratio, MULTIPLE_TURNOVER_ENZYME_OVER_SUBSTRATE_FULL, MULTIPLE_TURNOVER_ENZYME_OVER_SUBSTRATE_ZERO))


def _judge_time_range(native):
    # each end that is stated has its own ramp (conflicting at its zero end); the weaker of the two sets the degree
    limits = []
    if native['first_point_times_rate'] is not None:
        limits.append((_completed(native['first_point_times_rate']), FIRST_POINT_COMPLETED_FULL, FIRST_POINT_COMPLETED_ZERO))
    if native['last_point_times_rate'] is not None:
        limits.append((_completed(native['last_point_times_rate']), LAST_POINT_COMPLETED_FULL, LAST_POINT_COMPLETED_ZERO))
    return _graded(native['time_range_refs'], *limits)


def _judge_time_points(native):
    # residual degrees of freedom of the burst fit; a short course only lowers the degree, never conflicts
    return _verdict('supported', native['time_point_refs'], max(0.0, min(1.0, _share(native['time_point_count'], MIN_TIME_POINTS, TIME_POINTS_ZERO))))


def _judge_burst(native):
    # the rate per enzyme is off by one over the amplitude per enzyme: linear in the log of the amplitude; a small burst only lowers the degree
    amplitude = native['burst_per_enzyme']
    degree = (math.log(amplitude) - math.log(BURST_PER_ENZYME_ZERO)) / (math.log(BURST_PER_ENZYME_FULL) - math.log(BURST_PER_ENZYME_ZERO))
    return _verdict('supported', native['burst_refs'], max(0.0, min(1.0, degree)))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('enzyme_substrate_ratio', 'enzyme_ratio_recorded_for_the_sheet'): _judge_ratio, ('time_range', 'time_range_recorded_for_the_sheet'): _judge_time_range,
          ('time_points', 'time_point_count_recorded_for_the_sheet'): _judge_time_points, ('burst_stoichiometry', 'burst_amplitude_recorded_for_the_sheet'): _judge_burst,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _stated_effect(native, ref):
    """(the record quantity used, the effect operand in s^-1) for the first stated quantity of EFFECT_SOURCES, or (None, None) when none is stated (its 'support' is the extraction's)."""
    for source in EFFECT_SOURCES:
        operand = native['quantities'][source]
        if operand['status'] == 'point':
            return source, _operand(operand['value'] * RATE_FACTORS[operand['unit']], EFFECT_UNIT, 'quench_flow_' + source + ':' + ref, operand['source_refs'], operand['origin'], source, operand['support'])
    return None, None


def _variance(graded, source):
    """Return (variance in s^-1 squared or None, reason or None, refs) of the spread of the record quantity ``source``."""
    native = graded['native']
    spread = native['quantities'][source + '_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, source + '_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = spread['value'] * RATE_FACTORS[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_quench_flow(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    source, stated = _stated_effect(native, ref)
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if stated is None:
        null_components['effect'] = 'no_rate_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        _, effect = select_activity_effect({KIND_OF_EFFECT: stated})
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_EFFECT, effect['support']
        variance, variance_reason, variance_refs = _variance(graded, source)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, EFFECT_UNIT + '_squared', 'quench_flow_' + source + '_variance:' + ref, variance_refs, 'derived', source + '_spread')
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
        interpretations[sheet_criterion] = apply_support(interpretations[sheet_criterion], supports)      # weak quote support lowers the degree of a supported criterion, never its status
    if quantities['effect_variance'] is not None:
        interpretations['variance_correspondence'] = {'status': 'supported', 'support_refs': quantities['effect_variance']['source_refs']}
    extraction = {'version': INPUT_VERSION, 'assay_type': 'activity_rate', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'quench_flow', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support, 'enzyme_mass_g_per_mol': None}
    if quantities['effect'] is None and native['activity'] is not None:      # no stated rate: the paper's own statement of product above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['activity']], 'support_refs': list(native['activity_refs'])}
        result['direction_field_support'] = native['activity_support']
    return result
