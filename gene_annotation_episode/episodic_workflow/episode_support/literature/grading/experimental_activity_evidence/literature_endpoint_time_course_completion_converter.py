"""Endpoint_time_course_completion converter: turns the grader's result into what the A105 endpoint_conversion sheet takes.

Hand-built, private to endpoint_time_course_completion, deterministic (DRAFT 2026-11-22; nothing was run; every number is EXPERT_REVIEW, owner to confirm, and every literature
statement is from the drafter's memory, not verified). Input: the result of grade_endpoint_time_course_completion. Output: the sheet's input (the 'extraction' grade_assay takes,
with assay_type 'endpoint_conversion'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for every sheet component that a time to completion
cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity (literature_row_contract.ENDPOINT_STRENGTH_ANCHORS): the completion time ratio (reference time over test time,
                  dimensionless) or the completion time (minutes). Only an EXACT value can be the effect: the fact completion_time_is_exact (or completion_time_ratio_is_exact) must be
                  yes. A bound ("more than 18 h", "less than 10 min", "more than 100-fold") is never turned into a point (the direction function needs a point and raises on a bound; the
                  owner's open question 4 of the inventory is whether a bound should be read at its limit); a time whose exactness the passage leaves unstated is not taken either. The
                  order is the class's ENDPOINT_EFFECT_ORDER (literature_endpoint_conversion_direction.select_endpoint_effect): a STATED ratio first; else the ratio DERIVED from the two
                  stated times (reference over test, origin 'derived') but only when both times are exact AND the passage says the same completion state was used in both arms (a
                  ratio of times read against different end points is not a ratio); else the bare completion time. The conversion fraction, difference and the amount of the class
                  are not this type's results (they are the other types' end points at a fixed time).
                  A stated value in another unit of the record's vocabulary is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION): the value is the paper's, only its unit
                  spelling changes (s and h to min; fold to dimensionless).
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it: standard_error -> se^2; standard_deviation ->
                  sd^2 / n and only when the replicates criterion is supported; confidence_interval -> not converted (needs its level and degrees of freedom). A derived ratio has none.
Every other role stays null, with a reason (NULL_REASONS).
qualitative_effect  only when NO effect is filled: statement 'interaction_detected' (read "conversion detected"), 'interaction_not_detected' (read "conversion not detected") or
                  'interaction_not_stated', taken from the one fact conversion_detected_above_control, with the refs of that fact; direction_field_support is the support class of that
                  fact (None when it is not stated). A bound is therefore still evidence in words ("the reaction was not complete after 18 h" is not a detection by itself; only the fact
                  decides). A filled effect fixes the direction and the statement is not used. The result stated in words counts less than a measured one by the contract
                  (stated_strength), not here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
measurement_identity      completion_criterion (the passage says what state was complete or at equilibrium, so the time identifies a defined end point)
endpoint_alignment        matched_endpoint + samples_stopped + sampling_resolution (the same end state in both arms, samples that show the time they were taken, a sampling grid finer than the time)
background_alternatives   spontaneous_course_control (a time course without the enzyme or with an inactive enzyme)
attribution_supported     enzyme_dependence + contaminating_activity (the time follows the enzyme; a contaminating enzyme is examined: the lesson of the old HFP isomerisation case)
product_identity          product_identity + mass_balance
conversion_denominator    initial_substrate
condition_scope           matched_loading + matched_temperature + purified_enzyme
assertion_relevance       native_reaction
sampling_basis            replicates
variance_correspondence   supported only when a variance was computed
NOT SELECTED, and why: calibration_applicability (this type reads a TIME from a pattern of the signal, not an amount from a calibration; the detector's own calibration is the business of the end-point types at a fixed time) and
matrix_interference (a time to completion in a matrix is not judged here; add a fact if a real paper needs it). A sheet criterion with no counterpart is not selected and the sheet reports it as not selected.
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such criterion
and reason to its judgement). Each judgement is a researched value of THIS method made gradual (SOP step 3): full agreement at the researched good value, falling smoothly to zero at a
researched no-longer-meaningful value on the scale the physics of the method gives (never a step), unknown when the paper states nothing, never conflicting for a coarse grid or
a short count. A sheet criterion that is supported carries the smallest degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the
degree of a supported member and never changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are
dropped; a sheet criterion whose members are all not_applicable is not selected.

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None (no immobilized
enzyme, no electrode). Qualitative statements keep the existing vocabulary, read for this class ("conversion detected"). Direction and strength of a stated time or ratio:
literature_endpoint_conversion_direction (smaller time is stronger; the ratio larger is stronger; log scale between the quantity's own noise end and strong end); controls, blanks and
the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads and whether
the shape fits, Q5 consistency with the other assays). Every literature statement is from memory and not verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
SAMPLING_FULL_FRACTION 0.1 -> SAMPLING_ZERO_FRACTION 1.0, judged linearly in the sampling interval over the completion time.
  Q1 a completion time read off a coarse grid: completion is only known to lie between the last sample before it and the sample that showed it, so the time carries the interval as
  its uncertainty (a "completion at 4 h" from samples at 0, 4 and 24 h is anywhere from 0 to 4 h). Q2 general (the resolution of any sampled readout is the sampling step); the 0.1 is a
  practice estimate. Q3 relative to the paper's own time, which the grader records beside the interval: right. Q4 the relative error of the time is about the interval over the time,
  so the degree is linear in it; an error of 10 percent moves a ratio by 0.04 decades of the three-decade scale (about 1 percent of the strength), so it is the full end; at an interval
  equal to the time, the completion could be anywhere in its own first interval and the time is in effect a bound (no agreement). It is a grid, not a violation: the degree reaches 0 and the
  criterion is supported with degree 0, never conflicting (SOP consistency rule 2). Q5 the same idea as a short count: a coarse input lowers the degree, never conflicts.
LOADING_FULL_FOLD 1.5 -> LOADING_ZERO_FOLD 1000, judged linearly in the log of the fold difference between the two arms' enzyme loadings.
  Q1 a ratio of times that is a ratio of loadings: the time to a given conversion is about inversely proportional to the enzyme amount (in the first-order regime t = -ln(1 - f) / (kcat/Km [E]);
  with the substrate saturating t = f [S] / (kcat [E]); for the approach to equilibrium the rate constant is again proportional to [E]), so an arm with ten times more enzyme finishes about ten
  times sooner without the enzyme being any better. Q2 general kinetics (Cornish-Bowden, Fundamentals of Enzyme Kinetics; Copeland, Enzymes), from memory; the 1.5 is a practice estimate of how far two
  nominally equal loadings differ (pipetting, nominal against measured concentration, a stock re-measured), about a tenth of the three decades of the ratio scale. Q3 relative to the paper's own loadings:
  right, the grader records the fold difference only when both loadings are in the same kind of unit. Q4 a loading difference of f takes log10 f decades out of the ratio's range of the scale (noise end 1,
  strong end 1000: the contract's ENDPOINT_STRENGTH_ANCHORS), so the degree falls linearly in log f from 1.5 to the whole three decades; at 1000-fold the loading can explain any ratio on the scale
  (conflicting: the paper's own numbers show the comparison is not like for like). Q5 a log-ratio ramp like the other fold-gap judgements of the other classes. The fact alone (same loading, no numbers) is
  supported without a degree, and a fact stated no is the grader's conflicting.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a completion time from one run, whose run-to-run spread is unseen (an NMR or HPLC time course is often run once). Q2 general (triplicate practice). Q3 absolute count. Q4 precision of a mean
  (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the end state stated, the same end state, stopped samples, the controls, the enzyme dependence, the contaminating activity, the product identity, the mass balance, the
starting amount, the same temperature, the purified enzyme, the native substrate): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched
value to soften. NOT judged, and why: the completion time's own value (it is the effect, graded by the direction function on its scale); the end state chosen (completion_criterion is recorded for the
reviewer, a choice carries no span and no criterion rests on it); the detection method (recorded only).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this method, decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The time to a stated state, read from a sampled progress curve: relative, because it depends on the enzyme and substrate amounts, the temperature and on
  what the paper calls complete; it is an absolute number only when the loading and the end state are given.
  Is there a reference range we would trust if the paper stated less (as for KD)? No: a bare time to completion has no trusted range without its loading (the same enzyme gives minutes or days
  by amount alone), unlike kcat or a KD.
  What does an unstated control or definition do to what the number means? An unstated end state or an unstated sampling grid leaves the time uninterpreted; an unstated no-enzyme course is a real gap
  because completion times of hours or days are exactly where slow spontaneous chemistry competes (the old HFP case: a contaminating enzyme decided it); an unstated starting amount, a replicate count or
  a product standard is common practice when the substrate vanishes and the product appears together.
  If we assume it is fine and are wrong, how badly does the score mislead? The magnitude of a ratio can be wrong by a loading factor or the existence of the activity by a contaminant: more than for
  a KD, less than for a pure artefact such as a pull-down band.
  Consistent with KD / spectro_direct (0.85)? Lower, because the readout is relative.
  default 0.70. measurement_identity 0.55 (no stated end state: the time identifies no defined estimate). endpoint_alignment 0.60 (the central criterion of a time ratio: different end states or grids
  make the arms not comparable). background_alternatives 0.65 (long times invite spontaneous chemistry). attribution_supported 0.60 (a contaminating enzyme is the classic false positive of a long
  conversion and papers rarely examine it). conversion_denominator 0.85 and sampling_basis 0.85 (benign when unstated: it is optional for a time and a repeat changes the precision, not the existence).
  product_identity 0.75 (the substrate disappearing is usually seen together with the product). condition_scope, assertion_relevance take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_conversion_direction import select_endpoint_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_time_course_completion_criteria import MIN_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SUPPORT_WEAKEST_ORDER
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_endpoint_time_course_completion_converted'
CRITERIA_MAP = {'measurement_identity': ('completion_criterion',), 'endpoint_alignment': ('matched_endpoint', 'samples_stopped', 'sampling_resolution'),
                'background_alternatives': ('spontaneous_course_control',), 'attribution_supported': ('enzyme_dependence', 'contaminating_activity'),
                'product_identity': ('product_identity', 'mass_balance'), 'conversion_denominator': ('initial_substrate',),
                'condition_scope': ('matched_loading', 'matched_temperature', 'purified_enzyme'), 'assertion_relevance': ('native_reaction',), 'sampling_basis': ('replicates',)}
SAMPLING_FULL_FRACTION = 0.1  # EXPERT_REVIEW, owner to confirm: sampling interval at most this fraction of the completion time (a time known to about 10 percent; about 0.04 decades of the three-decade ratio scale); full agreement up to it. A practice estimate, from memory, not verified.
SAMPLING_ZERO_FRACTION = 1.0  # EXPERT_REVIEW, owner to confirm: interval as long as the time itself: completion could lie anywhere in its own first interval, so the time is in effect a bound (no agreement); the degree falls linearly in the interval over the time from the full end to here, reaches 0 and is never conflicting (a coarse grid is weaker evidence, not evidence against).
LOADING_FULL_FOLD = 1.5  # EXPERT_REVIEW, owner to confirm: two arms whose enzyme loadings differ by at most this fold count as the same loading (pipetting, nominal against measured concentration; about 0.18 decades of the three-decade ratio scale); full agreement up to it. A practice estimate, from memory, not verified.
LOADING_ZERO_FOLD = 1000.0  # EXPERT_REVIEW, owner to confirm: the time to a given conversion is about inversely proportional to the enzyme amount, so a loading difference of this fold (the whole three decades of the class's completion_time_ratio scale, noise end 1 to strong end 1000) can explain any ratio on the scale by itself (no agreement, conflicting); the degree falls from LOADING_FULL_FOLD linearly in the log of the fold.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent time courses; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
KEY = 'endpoint_time_course_completion_'
# The anchor unit of each effect quantity (literature_row_contract.ENDPOINT_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (60 s is 1 min; 1 h is 60 min; a fold is the dimensionless ratio itself); the stated number is the paper's.
    'completion_time': ('min', MIN_PER_UNIT),
    'completion_time_ratio': ('dimensionless', {'fold': 1.0}),
}
# The exactness fact that says whether each effect quantity is a value (yes) or a bound (no) or unstated (unknown).
EXACT_FACT = {'completion_time': 'completion_time_is_exact', 'completion_time_ratio': 'completion_time_ratio_is_exact'}
# The quantity_kind (QUANTITY_KINDS['endpoint_conversion']) that names the kind of each effect quantity; the direction function reads it back.
KIND_OF_QUANTITY = {'completion_time': 'completion_time', 'completion_time_ratio': 'completion_time_ratio'}
KIND_WITHOUT_EFFECT = 'completion_time'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'a_time_to_completion_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_time_to_completion_is_not_an_attribution_fraction', 'total_signal': 'a_time_to_completion_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_time_course_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_time_course_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "conversion detected" / "conversion not detected" / "conversion not stated" for this class


def _verdict(status, refs, degree=None):
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError('a ' + status + ' judgement needs support refs')
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _share(value, full, zero):
    """1.0 at the full-agreement limit, 0 at the zero-agreement limit, linear in between (either orientation; not capped)."""
    return (zero - value) / (zero - full)


def _judge_sampling(native):
    # a coarse grid lowers the degree to 0 at most and never conflicts; linear in the interval over the time
    degree = max(0.0, min(1.0, _share(native['sampling_interval_over_time'], SAMPLING_FULL_FRACTION, SAMPLING_ZERO_FRACTION)))
    return _verdict('supported', native['sampling_refs'], degree)


def _judge_loading(native):
    # the log of the fold difference between the two loadings; conflicting at or beyond the zero end (the loading alone can explain the ratio)
    degree = _share(math.log(native['loading_fold']), math.log(LOADING_FULL_FOLD), math.log(LOADING_ZERO_FOLD))
    if degree <= 0:
        return _verdict('conflicting', native['loading_refs'])
    return _verdict('supported', native['loading_refs'], min(1.0, degree))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('sampling_resolution', 'sampling_recorded_for_the_sheet'): _judge_sampling, ('matched_loading', 'loading_recorded_for_the_sheet'): _judge_loading,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _weakest(*supports):
    held = [support for support in supports if support is not None]
    return min(held, key=SUPPORT_WEAKEST_ORDER.index) if held else None


def _stated_effect(native, quantity, ref):
    """The stated quantity as an effect operand in its anchor unit, or None when it is not stated or not stated as an exact value (a bound is never an effect).
    Its 'support' is the weakest of the quantity's and of the exactness fact's."""
    operand = native['quantities'][quantity]
    exact = native['facts'][EXACT_FACT[quantity]]
    if operand['status'] != 'point' or exact['answer'] != 'yes':
        return None
    unit, factors = UNIT_FACTORS[quantity]
    return _operand(operand['value'] * factors[operand['unit']], unit, KEY + quantity + ':' + ref, list(dict.fromkeys([*operand['source_refs'], *exact['source_refs']])), operand['origin'], quantity,
                    _weakest(operand['support'], exact['support']))


def _derived_ratio(native, ref):
    """The reference time over the test time as a ratio (dimensionless), only when both times are exact values AND the passage says the same completion state was used in both arms;
    otherwise None. Its refs are those of the two times and the three facts; its support is the weakest of them."""
    facts = [native['facts'][name] for name in ('same_completion_criterion_in_arms', 'completion_time_is_exact', 'reference_time_is_exact')]
    if native['reference_over_completion'] is None or any(item['answer'] != 'yes' for item in facts):
        return None
    held = (native['quantities']['completion_time'], native['quantities']['reference_completion_time'], *facts)
    refs = list(dict.fromkeys([*native['ratio_refs'], *(r for item in facts for r in item['source_refs'])]))
    return _operand(native['reference_over_completion'], 'dimensionless', KEY + 'completion_time_ratio_derived:' + ref, refs, 'derived', 'completion_time_ratio', _weakest(*(item['support'] for item in held)))


def _variance(graded, quantity, effect, ref):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of ``quantity``."""
    native = graded['native']
    if effect['origin'] == 'derived':
        return None, 'ratio_derived_from_two_times_has_no_stated_spread', []
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


def convert_endpoint_time_course_completion(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {'completion_time_ratio': _stated_effect(native, 'completion_time_ratio', ref) or _derived_ratio(native, ref), 'completion_time': _stated_effect(native, 'completion_time', ref)}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_completion_time_or_ratio_given_as_an_exact_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_endpoint_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_QUANTITY[chosen], effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, effect, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', KEY + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
    null_components.update({role: reason for role, reason in NULL_REASONS.items()})
    interpretations = {}
    for sheet_criterion, members in CRITERIA_MAP.items():
        # the support of the quotes (kept by the grader) gives or lowers the degree of a supported member; it never changes a status
        graded_members = [apply_support(_criterion(graded, m), native['support'][m]) for m in members if graded['criteria'][m]['status'] != 'not_applicable']
        if not graded_members:
            continue
        statuses = [m['status'] for m in graded_members]
        status = 'conflicting' if 'conflicting' in statuses else 'unknown' if 'unknown' in statuses else 'supported'
        refs = list(dict.fromkeys(r for m in graded_members for r in m['support_refs']))
        interpretations[sheet_criterion] = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
        degrees = [m['degree'] for m in graded_members if 'degree' in m]
        if status == 'supported' and degrees:
            interpretations[sheet_criterion]['degree'] = min(degrees)      # the weakest member: a degree of a member is not averaged away
    if quantities['effect_variance'] is not None:
        interpretations['variance_correspondence'] = {'status': 'supported', 'support_refs': quantities['effect_variance']['source_refs']}
    extraction = {'version': INPUT_VERSION, 'assay_type': 'endpoint_conversion', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'endpoint_time_course_completion', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no exact time or ratio: the paper's own statement of conversion above its control stands, scored like any stated result (literature_direction, the qualitative path)
        result['qualitative_effect'] = {'statement': STATEMENTS[native['conversion']], 'support_refs': list(native['conversion_refs'])}
        if native['conversion'] is not None:
            result['direction_field_support'] = native['conversion_support']      # the support class of the fact conversion_detected_above_control, the one field the statement is derived from
    return result
