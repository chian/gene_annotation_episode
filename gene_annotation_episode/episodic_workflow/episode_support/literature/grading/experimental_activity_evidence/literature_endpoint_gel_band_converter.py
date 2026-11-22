"""Endpoint_gel_band converter: turns the grader's result into what the A105 endpoint_conversion sheet takes (DRAFT 2026-11-22, owner to correct).

Hand-built, private to endpoint_gel_band, deterministic. Input: the result of grade_endpoint_gel_band. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'endpoint_conversion'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for every
sheet component that a gel end point cannot honestly fill, the reason it stays null. Built from the spectro_direct converter (the template of the
activity_rate class) with the endpoint_conversion class core in place of the activity core: no enzyme mass is handed over (every anchor of the class is in a
unit that is produced here by an exact factor).

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit 'fraction': the share converted net of the paper's own control (quantity_kind 'conversion_difference') when the
                  passage states that corrected value itself, else the share converted as stated (quantity_kind 'conversion_fraction'). The choice is the class order
                  ENDPOINT_EFFECT_ORDER (literature_endpoint_conversion_direction.select_endpoint_effect; the reason is in the contract). Nothing is subtracted here:
                  the corrected share is the paper's own. A stated value in percent is multiplied by its exact factor (FRACTION_PER_UNIT, FIXED_BY_DEFINITION): the value is
                  the paper's, only its unit spelling changes. A share stated as 0 cannot be an effect (the strength scale is logarithmic and a conversion of 0 is no
                  conversion): no effect is filled and the statement of the paper (the fact conversion_detected_above_control) stands as the qualitative result. A
                  corrected share stated as 0 means the test is no better than the control: no effect is filled at all (the raw share is not used in its place).
effect_variance   variance of that effect, in fraction_squared, only when the passage's spread of THAT quantity allows it: standard_error -> se^2;
                  standard_deviation -> sd^2 / n and only when the replicates criterion is supported; confidence_interval -> not converted (needs its level and degrees
                  of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).
qualitative_effect  only when NO effect is filled: the paper's own statement whether it saw a product band above its control lane: statement 'interaction_detected' (read
                  "conversion detected"), 'interaction_not_detected' (read "conversion not detected") or 'interaction_not_stated', with the refs of the fact that states it.
                  direction_field_support is then the quote support of that one fact. A stated effect fixes the direction; the statement is then not used. Its strength
                  as a result in words alone (the contract's stated_strength) is not applied here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives   spontaneous_reaction_control + substrate_purity_control + control_lane_background
attribution_supported     enzyme_dependence
product_identity          product_identity
calibration_applicability densitometry_linear_range
conversion_denominator    same_lane_fraction
endpoint_alignment        endpoint_time_defined + lanes_same_time
assertion_relevance       native_reaction
condition_scope           purified_enzyme
sampling_basis            replicates
variance_correspondence   supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity, matrix_interference) are not selected: a purified-enzyme gel lane has no matrix or detector-interference
question of its own, and the substrate, product and denominator of the share are asked by conversion_denominator and product_identity.
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Each judgement is a researched value of THIS assay made gradual (SOP step 3): full agreement at the researched good value, falling
linearly to zero at a researched no-longer-meaningful value (never a step), unknown when the paper states nothing, never conflicting for a short count. A value at or beyond
its zero end is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported carries the smallest degree of its members that have
one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined status: any conflicting ->
conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is not selected.

How the class decisions apply here (owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None (no immobilized enzyme, no
surface). Qualitative statements keep the existing vocabulary. Direction and strength of a stated share: literature_endpoint_conversion_direction (a larger share is stronger);
controls, lanes and the rest lower the WEIGHT only. Pooling: the class is not pooled.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads and whether
the shape fits, Q5 consistency with the other assays). Every literature statement is from memory and not verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
CONTROL_RATIO_FULL 0.05 -> CONTROL_RATIO_ZERO 1.0, judged on the control share over the test share (control_lane_background).
  Q1 a band that is in the control lane as much as in the test lane: spontaneous breakdown of the substrate, a product-containing substrate preparation, or a contaminating
  activity, not the enzyme. Q2 general: a no-enzyme lane of a clean substrate shows a few percent at most (nucleic-acid and protein substrates break down slowly in buffer; a
  radiolabelled nucleotide stock carries a few percent of breakdown product), and a densitometry reading of a lane is good to a few percent of the lane signal (from memory;
  not a method paper's value), so a control share up to 5 percent of the test share is inside the reading noise. Q3 relative to the paper's own test share, which the grader
  records beside the control. Q4 the share of the test conversion that the enzyme can claim is 1 - control / test, so the degree is linear in the ratio, from 1 at 0.05 to 0
  at 1 (the control is as strong as the test: the paper's own lanes show no enzyme dependence, conflicting). Never opposition for a small control. Q5 the same idea as the
  replicate and series ramps of the other assays: a bias that grows with the departure from the researched value.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a share from one gel, whose experiment-to-experiment spread (loading, exposure, preparation) is unseen. Q2 general (three independent gels or reactions is the usual minimum
  of a quantified gel figure). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the control lanes, the enzyme dependence, the identification of the band, the linear range of the detection, the same-lane share, the stop of the
reaction, the same time of the compared lanes, the native substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is conflicting, silence
is unknown. They have no researched value to soften. NOT judged, and why: the exposure or the linear range as a number (a paper rarely states it, so it is a fact); the length
of the incubation (the strength scale and the control read it, and the claim carries no time); the pH and the temperature (the identity block records them).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this assay, owner to confirm:
  What does it measure; absolute or relative? The share of a substrate converted at one time, read as the product band over the substrate plus the product bands of one lane:
  a relative readout within the lane (loading cancels), absolute as a share of the substrate. It is semi-quantitative: densitometry is linear only inside a range, and the band
  is identified by where it runs, not by what it is.
  Is there a reference range we would trust if the paper stated less (as for KD)? Partly: gel figures of this kind usually have a no-enzyme lane and a mutant lane, and the
  share within a lane is the usual convention, but a saturated band or a contaminating activity in the preparation is not seen in a sentence.
  What does an unstated control or calibration do to what the number means? An unstated no-enzyme or mutant lane leaves open spontaneous breakdown and a contaminating enzyme
  (the leading false positive of a gel end point); an unstated linear range changes the size of the share, not its existence; an unstated stop of the reaction shifts the time,
  not the existence.
  If we assume it is fine and are wrong, how badly does the score mislead? A background or a contaminating activity counted as the enzyme's gives a wrong direction for a weak
  band and a wrong size for a strong one: less severe than a pull-down band, more than a KD.
  Consistent with KD and the other assays? Below spectro_direct (0.85, an absolute rate with a trusted reference range) and level with EMSA (0.75, the other gel readout).
  default 0.75. background_alternatives 0.70, attribution_supported 0.70, product_identity 0.70 (the controls and the identity of a band by mobility alone are what separate a
  product from a breakdown or a contaminating activity). calibration_applicability 0.80 (a saturated band is a real risk but the share within a lane is self-normalizing),
  conversion_denominator 0.85 and sampling_basis 0.85 (the same-lane share and triplicate gels are the usual convention, benign when unstated). endpoint_alignment, assertion_relevance
  and condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_conversion_direction import select_endpoint_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_endpoint_gel_band_converted_v1'
CRITERIA_MAP = {'background_alternatives': ('spontaneous_reaction_control', 'substrate_purity_control', 'control_lane_background'), 'attribution_supported': ('enzyme_dependence',),
                'product_identity': ('product_identity',), 'calibration_applicability': ('densitometry_linear_range',), 'conversion_denominator': ('same_lane_fraction',),
                'endpoint_alignment': ('endpoint_time_defined', 'lanes_same_time'), 'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',),
                'sampling_basis': ('replicates',)}
CONTROL_RATIO_FULL = 0.05  # EXPERT_REVIEW, owner to confirm (from memory, not verified): a control lane share up to 5 percent of the test share is inside the reading noise of gel and TLC densitometry (a clean substrate breaks down by a few percent at most; a lane reads to a few percent); full agreement up to it.
CONTROL_RATIO_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: a control lane as strong as the test lane shows no enzyme dependence (no agreement, conflicting); the share of the test conversion that the enzyme can claim is 1 - control / test, so the degree falls linearly in the ratio from CONTROL_RATIO_FULL to here.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm (from memory): fewest independent experiments (separate gels) behind a quantified share; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
FRACTION_PER_UNIT = {'percent': 0.01, 'fraction': 1.0}  # FIXED_BY_DEFINITION: a percent is a hundredth; a fraction is itself.
EFFECT_UNIT = 'fraction'      # the anchor unit of both effect quantities (literature_row_contract.ENDPOINT_STRENGTH_ANCHORS)
# The effect quantity -> (the record quantity that states it, the record quantity that states its spread). The key is also its quantity_kind (QUANTITY_KINDS['endpoint_conversion']).
EFFECT_FIELDS = {'conversion_difference': ('net_conversion_percent', 'net_conversion_spread'), 'conversion_fraction': ('conversion_percent', 'conversion_spread')}
KIND_WITHOUT_EFFECT = 'conversion_fraction'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'a_gel_end_point_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_converted_share_is_not_an_attribution_fraction', 'total_signal': 'a_converted_share_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_an_endpoint_gel_band_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_endpoint_gel_band_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "conversion detected" / "conversion not detected" / "conversion not stated" for this class


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


def _judge_control(native):
    return _graded(native['control_refs'], (native['control_fraction'] / native['test_fraction'], CONTROL_RATIO_FULL, CONTROL_RATIO_ZERO))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('control_lane_background', 'control_background_recorded_for_the_sheet'): _judge_control, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _stated_effect(native, quantity, ref):
    """The stated quantity as an effect operand in the anchor unit, or None when it is not stated or is 0 (its 'support' is the extraction's)."""
    operand = native['quantities'][EFFECT_FIELDS[quantity][0]]
    if operand['status'] != 'point' or operand['value'] == 0:
        return None
    return _operand(operand['value'] * FRACTION_PER_UNIT[operand['unit']], EFFECT_UNIT, 'endpoint_gel_band_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], EFFECT_FIELDS[quantity][0], operand['support'])


def _variance(graded, quantity):
    """Return (variance in fraction_squared or None, reason or None, refs) of the spread of ``quantity``."""
    native = graded['native']
    spread = native['quantities'][EFFECT_FIELDS[quantity][1]]
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, EFFECT_FIELDS[quantity][1] + '_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = spread['value'] * FRACTION_PER_UNIT[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_endpoint_gel_band(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    net = native['quantities']['net_conversion_percent']
    net_is_zero = net['status'] == 'point' and net['value'] == 0      # the test is no better than the control: not an effect, and the raw share is not used in its place
    stated = {} if net_is_zero else {quantity: _stated_effect(native, quantity, ref) for quantity in EFFECT_FIELDS}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'net_conversion_is_zero_so_the_test_is_no_better_than_the_control' if net_is_zero else 'no_conversion_share_given_as_a_positive_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_endpoint_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = chosen, effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, EFFECT_UNIT + '_squared', 'endpoint_gel_band_' + chosen + '_variance:' + ref, variance_refs, 'derived', EFFECT_FIELDS[chosen][1])
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'endpoint_conversion', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'endpoint_gel_band', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no effect: the paper's own statement of a product above its control lane stands (owner, 2026-11-22), scored like any stated result (literature_direction, the qualitative path)
        result['qualitative_effect'] = {'statement': STATEMENTS[native['conversion']], 'support_refs': list(native['conversion_refs'])}
        if native['conversion'] is not None:
            result['direction_field_support'] = native['conversion_support']      # the support class of the fact conversion_detected_above_control, the one field the statement is derived from
    return result
