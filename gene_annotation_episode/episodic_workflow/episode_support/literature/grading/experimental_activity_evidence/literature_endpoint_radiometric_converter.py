"""Endpoint_radiometric converter: turns the grader's result into what the A105 endpoint_conversion sheet takes.

Hand-built, private to endpoint_radiometric, deterministic. Input: the result of grade_endpoint_radiometric. Output: the sheet's input (the
'extraction' grade_assay takes, with assay_type 'endpoint_conversion'), the sheet itself (grade_assay run on it), the dependence keys the merger
needs, and for every sheet component that an end-point measurement cannot honestly fill, the reason it stays null. DRAFT built 2026-11-22 by the
SOP on the pattern of literature_spectro_direct_converter.py, for the endpoint_conversion class (A105_ENDPOINT_CONVERSION_INVENTORY.md; direction in
literature_endpoint_conversion_direction.py).

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity (literature_row_contract.ENDPOINT_STRENGTH_ANCHORS): the share converted
                  net of the paper's own control (conversion_difference, fraction), the share converted as stated (conversion_fraction, fraction),
                  or the product amount as a concentration (endpoint_amount, uM). Several may be stated; the one used is the best-determined, in the
                  class order ENDPOINT_EFFECT_ORDER (literature_endpoint_conversion_direction.select_endpoint_effect). quantity_kind of the extraction
                  names the kind of the effect. Exact conversions only (FIXED_BY_DEFINITION): a percent is a hundredth, a pmol is a thousandth of a
                  nmol, and an amount becomes a concentration only when the passage also states the reaction volume (1 nmol in 1 uL is 1000 uM).
                  The value is the paper's, only its unit spelling changes.
                  conversion_difference is taken from net_conversion when the passage states the corrected share itself; else, when the passage
                  states the share converted AND the share in its own control, it is their difference (origin 'derived': a subtraction of two
                  stated numbers, with the weaker of the two quote supports); when that difference is not above zero the test is no better than
                  the control, which is not an effect: NO effect is filled (reason in null_components) and the paper's words, if any, decide through
                  the qualitative path. A share stated with no control stays conversion_fraction (its noise end is higher, it holds the background).
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). For a derived difference the variances of the
                  two arms add and both spreads are needed. Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery, attributed signal/total signal, condition test/reference, the assertion
and alternative predictions.
qualitative_effect  only when NO effect is filled: statement 'interaction_detected' (read "conversion detected"), 'interaction_not_detected'
                  (read "conversion not detected") or 'interaction_not_stated' (read "conversion not stated"), with the refs of the fact
                  conversion_detected_above_control that states it, and direction_field_support taken from the quote support of that one fact.
                  A result stated in words alone already counts STATED_ONLY_STRENGTH of the type's value (literature_row_contract.stated_strength);
                  nothing is re-implemented here. A stated effect fixes the direction; the statement is then not used.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives    spontaneous_conversion_control + separation_background_control
calibration_applicability  counts_over_background + specific_radioactivity_stated
matrix_interference        counting_efficiency
attribution_supported      enzyme_dependence
product_identity           product_identity + label_in_product_position
endpoint_alignment         endpoint_time_and_stop + same_time_in_compared_arms
conversion_denominator     fraction_over_total_label
assertion_relevance        native_reaction
condition_scope            purified_enzyme
sampling_basis             replicates
variance_correspondence    supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity) are not selected.
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in
'_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Each judgement is a researched value of THIS method made
gradual (SOP step 3): full agreement at the researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the
scale the physics of the method gives (never a step), unknown when the paper states nothing, never conflicting for a short count. A value at or
beyond its zero end is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported carries the smallest
degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and never
changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are
dropped; a sheet criterion whose members are all not_applicable is not selected.

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys
stay None (no immobilized enzyme, no surface). Qualitative statements keep the existing vocabulary. Direction and strength of a stated result:
literature_endpoint_conversion_direction (same paradigm as binding and activity; a measured result supports by its graded strength and never
opposes); controls, blanks, the endpoint alignment and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a
wrong value misleads and whether the shape fits, Q5 consistency with the other assays). Every literature statement is from memory and not
verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
SIGNAL_OVER_BACKGROUND_FULL 10 -> SIGNAL_OVER_BACKGROUND_ZERO 1, judged on the log of the ratio of the test counts to the blank counts.
  Q1 a product count that is a small excess over the carry-over of the labelled substrate, the label impurity and the instrument background: the
  net count (test minus blank) then rests on a difference of two nearly equal numbers. Q2 general counting practice: a sample is "detected" when it
  lies about three standard deviations above the blank, and a quantity is read with confidence when the blank is a small part of the signal; a
  tenfold margin leaves the blank at a tenth of the signal (from memory, Knoll, Radiation Detection and Measurement, and the usual scintillation
  counting guides; not verified). Q3 relative to the paper's own blank, which the grader records. Q4 with the blank at a tenth of the test, a blank
  known to within 10 percent moves the net signal by about 1 percent, which is no longer decisive; at a ratio of 1 the test is no larger than the
  paper's own blank and the paper itself shows no signal (conflicting). The degree is linear in the log of the ratio, because a ratio is a quotient
  of two counts whose errors are multiplicative: 3 -> 0.48, 2 -> 0.30. Q5 the same log-ratio ramp as the enrichment and fold judgements of the
  binding assays (3 over 1 for the co-localization enrichment, a different method with its own full end).
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a conversion from one reaction, whose reaction-to-reaction spread (pipetting, incubation, separation, counting) is unseen. Q2 general
  (triplicate practice; Cumming, Fidler and Vaux 2007 J Cell Biol 177:7, from memory). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the
  same sd^2 / n used for the variance. Q5 exactly the shared replicate rule (the owner's rule: replicates mean precision in every assay).
Facts with no number (the controls, the carry-over control, the stop, the same time in the compared arms, the denominator over the total label, the
enzyme dependence, the identification of the product, the label position, the counting-efficiency correction, the native substrate and the purified
enzyme): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to soften.
NOT judged, and why: the incubation time and the enzyme amount (a conversion at a fixed time depends on both, and the paper's loading is its own
choice; the conversion itself is read on the effect scale and the direction function already lowers a weak conversion); the specific radioactivity
and the counting efficiency as numbers (only their statement is a criterion: a wrong constant shows as an implausible amount, which the strength scale
already reads); the radiochemical purity of the label (a supplier certificate, almost never quoted: it is not in the record); the pH and the
temperature (the claim carries no condition and the identity block records the temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered
for this method, decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The share of an added label that ended in the product at one time, read from counts: a ratio of counts
  of the same sample, so it is self-normalised and absolute with respect to the substrate; an amount needs the specific radioactivity.
  Is there a reference range we would trust if the paper stated less (as for KD)? Partly: radiolabelled end points are used for weak activities, where
  conversions of a few percent are common, and the strength scale already treats a few percent as noise.
  What does an unstated control or calibration do to the number's meaning? An unstated blank is the dominant false positive of this very sensitive
  method (carry-over of the substrate into the product fraction, spontaneous breakdown of the label, an enzyme-free reaction), so it is not benign. An
  unstated product identification leaves a second labelled species in the product spot open (the product is known only through the separation). An
  unstated counting correction or specific radioactivity changes the size by a factor, not the existence; the share over the total label is the usual
  convention; triplicates are usual.
  If we assume it is fine and are wrong, how badly does the score mislead? A carried-over or spontaneous label counted as the enzyme's product: the
  direction is wrong for a small conversion and the size is wrong for a large one; worse than a KD (a magnitude only), like the activity blank.
  Consistent with KD and with the activity radiometric type? The default 0.85 equals the activity class's radiometric type (an absolute amount of
  product from counts) and is under the KD anchor 0.90; the guards against a false conversion are lower, the benign details equal 0.90.
  default 0.85. background_alternatives 0.70 (the blank and the carry-over control are what separate conversion from carry-over). attribution_supported
  0.80 (a contaminating activity in a crude enzyme gives the same label movement). product_identity 0.75 (identity rests on the separation alone).
  calibration_applicability 0.90, matrix_interference 0.90, conversion_denominator 0.90, sampling_basis 0.90 (benign when unstated).
  endpoint_alignment, assertion_relevance and condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_conversion_direction import select_endpoint_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORT_DEGREE, apply_support

VERSION = 'a105_endpoint_radiometric_converted_v1'
CRITERIA_MAP = {'background_alternatives': ('spontaneous_conversion_control', 'separation_background_control'),
                'calibration_applicability': ('counts_over_background', 'specific_radioactivity_stated'), 'matrix_interference': ('counting_efficiency',),
                'attribution_supported': ('enzyme_dependence',), 'product_identity': ('product_identity', 'label_in_product_position'),
                'endpoint_alignment': ('endpoint_time_and_stop', 'same_time_in_compared_arms'), 'conversion_denominator': ('fraction_over_total_label',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',), 'sampling_basis': ('replicates',)}
FRACTION_DIVISOR = {'percent': 100.0, 'fraction': 1.0}  # FIXED_BY_DEFINITION: a percent is a hundredth of the whole.
UM_PER_UNIT = {'nM': 1.0e-3, 'uM': 1.0, 'mM': 1.0e3}  # FIXED_BY_DEFINITION: a concentration in micromolar.
NMOL_PER_UNIT = {'nmol': 1.0, 'pmol': 1.0e-3, 'umol': 1.0e3}  # FIXED_BY_DEFINITION: an amount in nanomoles.
UL_PER_UNIT = {'uL': 1.0, 'mL': 1.0e3}  # FIXED_BY_DEFINITION: a volume in microlitres.
UM_PER_NMOL_PER_UL = 1.0e3  # FIXED_BY_DEFINITION: 1 nmol in 1 uL is 1 mM, that is 1000 uM.
SIGNAL_OVER_BACKGROUND_FULL = 10.0  # EXPERT_REVIEW, owner to confirm: the test counts at least ten times the blank counts leave the blank at a tenth of the signal, so a blank known to 10 percent moves the net signal by about 1 percent (counting practice, from memory, not verified); full agreement from it.
SIGNAL_OVER_BACKGROUND_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: test counts no larger than the paper's own blank counts show no signal (no agreement, conflicting); the degree falls from SIGNAL_OVER_BACKGROUND_FULL linearly in the log of the ratio, because a ratio is a quotient of two counts whose errors are multiplicative.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.ENDPOINT_STRENGTH_ANCHORS).
ANCHOR_UNIT = {'conversion_difference': 'fraction', 'conversion_fraction': 'fraction', 'endpoint_amount': 'uM'}
KEY = 'endpoint_radiometric_'
KIND_WITHOUT_EFFECT = 'conversion_fraction'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'endpoint_radiometric_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_radiometric_endpoint_is_not_an_attribution_fraction', 'total_signal': 'a_radiometric_endpoint_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_an_endpoint_radiometric_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_endpoint_radiometric_record',
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


def _log(value, full, zero):
    """A ratio limit on the log scale, for _graded."""
    return math.log(value), math.log(full), math.log(zero)


def _judge_counts(native):
    return _graded(native['counts_refs'], _log(native['signal_over_background'], SIGNAL_OVER_BACKGROUND_FULL, SIGNAL_OVER_BACKGROUND_ZERO))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('counts_over_background', 'counts_recorded_for_the_sheet'): _judge_counts, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _fraction(operand):
    """(the stated share in fractions, its refs): the exact conversion of a percent."""
    return operand['value'] / FRACTION_DIVISOR[operand['unit']], operand['source_refs']


def _micromolar(native, operand):
    """(the stated amount or concentration in micromolar, its refs), or (None, []) when an amount in mol has no stated reaction volume."""
    unit = operand['unit']
    if unit in UM_PER_UNIT:
        return operand['value'] * UM_PER_UNIT[unit], operand['source_refs']
    volume = native['quantities']['reaction_volume']
    if volume['status'] != 'point':
        return None, []
    return (operand['value'] * NMOL_PER_UNIT[unit] / (volume['value'] * UL_PER_UNIT[volume['unit']]) * UM_PER_NMOL_PER_UL,
            list(dict.fromkeys([*operand['source_refs'], *volume['source_refs']])))


def _stated_share(native, name, ref):
    """The stated share as an operand in fractions, or None when not stated (its 'support' is the extraction's)."""
    operand = native['quantities'][name]
    if operand['status'] != 'point':
        return None
    value, refs = _fraction(operand)
    return _operand(value, 'fraction', KEY + name + ':' + ref, refs, operand['origin'], name, operand['support'])


def _stated_amount(native, ref):
    """The stated product amount as an operand in micromolar, or None when not stated or when an amount in mol has no stated reaction volume."""
    operand = native['quantities']['product_amount']
    if operand['status'] != 'point':
        return None
    value, refs = _micromolar(native, operand)
    if value is None:
        return None
    return _operand(value, 'uM', KEY + 'product_amount:' + ref, refs, operand['origin'], 'product_amount', operand['support'])


def _derived_difference(test, control, ref):
    """The share converted minus the share in the paper's own control (both stated, in fractions), with the weaker of the two quote supports; None when the test is not above the control."""
    value = test['value'] - control['value']
    if value <= 0:
        return None
    support = min(test['support'], control['support'], key=SUPPORT_DEGREE.get)
    return _operand(value, 'fraction', KEY + 'conversion_difference:' + ref, list(dict.fromkeys([*test['source_refs'], *control['source_refs']])), 'derived', 'conversion_minus_control_conversion', support)


def _variance(graded, spread_name, convert):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread ``spread_name``; ``convert`` gives the spread in the anchor unit and its refs."""
    native = graded['native']
    spread = native['quantities'][spread_name]
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, spread_name + '_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd, refs = convert(spread)
    if sd is None:
        return None, 'product_amount_needs_the_reaction_volume', []
    if kind == 'standard_error':
        return sd * sd, None, refs
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*refs, *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def _effect_variance(graded, chosen, basis):
    """The variance of the chosen effect from the spread that belongs to it (``basis`` says which stated share it came from)."""
    native = graded['native']
    if chosen == 'endpoint_amount':
        return _variance(graded, 'product_amount_spread', lambda spread: _micromolar(native, spread))
    if basis == 'difference':      # the two arms are independent measurements: their variances add
        test, control = _variance(graded, 'conversion_spread', _fraction), _variance(graded, 'control_conversion_spread', _fraction)
        if test[0] is None or control[0] is None:
            return None, 'difference_needs_the_spread_of_both_arms:' + (test[1] or control[1]), []
        return test[0] + control[0], None, list(dict.fromkeys([*test[2], *control[2]]))
    return _variance(graded, basis + '_spread', _fraction)


def convert_endpoint_radiometric(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    test, control, net = _stated_share(native, 'conversion', ref), _stated_share(native, 'control_conversion', ref), _stated_share(native, 'net_conversion', ref)
    stated, basis, no_effect_reason = {}, None, None
    if net is not None:
        stated['conversion_difference'], basis = net, 'net_conversion'
    elif test is not None and control is not None:
        difference = _derived_difference(test, control, ref)
        if difference is None:
            no_effect_reason = 'conversion_not_above_the_papers_own_control'
        else:
            stated['conversion_difference'], basis = difference, 'difference'
    elif test is not None:
        stated['conversion_fraction'], basis = test, 'conversion'
    amount = None if no_effect_reason else _stated_amount(native, ref)
    if amount is not None:
        stated['endpoint_amount'] = amount
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if not stated:
        null_components['effect'] = no_effect_reason or 'no_endpoint_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_endpoint_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = chosen, effect['support']
        variance, variance_reason, variance_refs = _effect_variance(graded, chosen, basis)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, ANCHOR_UNIT[chosen] + '_squared', KEY + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    result = {'version': VERSION, 'experiment_type': 'endpoint_radiometric', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no effect: the paper's own yes/no statement stands, scored like any stated result (literature_direction, the qualitative path)
        result['qualitative_effect'] = {'statement': STATEMENTS[native['conversion_statement']], 'support_refs': list(native['conversion_statement_refs'])}
        if native['conversion_statement'] is not None:
            result['direction_field_support'] = native['conversion_statement_support']      # the support class of the fact conversion_detected_above_control, the one field the statement is derived from
    return result
