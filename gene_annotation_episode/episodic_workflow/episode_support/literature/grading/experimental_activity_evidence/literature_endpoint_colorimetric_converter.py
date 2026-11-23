"""Endpoint_colorimetric converter: turns the grader's result into what the A105 endpoint_conversion sheet takes.

Hand-built, private to endpoint_colorimetric, deterministic. Input: the result of grade_endpoint_colorimetric. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'endpoint_conversion'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for every
sheet component that a stopped colorimetric end point cannot honestly fill, the reason it stays null. DRAFT (owner to correct): written 2026-11-22 from the
endpoint_conversion class core (docs/axis_restructure_20261117/A105_ENDPOINT_CONVERSION_INVENTORY.md) and the class direction module
literature_endpoint_conversion_direction.py, which needs the class block of the registration note (ENDPOINT_STRENGTH_ANCHORS, ENDPOINT_EFFECT_ORDER,
ENDPOINT_QUANTITY_OF_KIND in the contract) before it can be imported.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its kind (ENDPOINT_STRENGTH_ANCHORS): conversion_difference (fraction: the share converted
                  minus the paper's own control, either stated as the net conversion or the exact difference of the stated conversion and the stated
                  control conversion), conversion_fraction (fraction: the share converted as stated) or endpoint_amount (uM: the product concentration
                  at the end point, or a stated product amount over the stated reaction volume). Several may be stated; the one used is the best
                  determined, in the class order ENDPOINT_EFFECT_ORDER (literature_endpoint_conversion_direction.select_endpoint_effect). A percent
                  becomes a fraction by the exact factor 0.01, a concentration unit becomes uM by its exact factor (FIXED_BY_DEFINITION): the value is
                  the paper's, only its unit spelling changes. A share above 1 (a stated 102 percent) is read as 1: a share converted cannot exceed
                  all of the substrate, and a value just above it is the read noise around complete conversion. completion_time and
                  completion_time_ratio are not filled: a fixed-time stopped assay reports neither (they belong to endpoint_time_course_completion).
                  A CONVERSION NOT ABOVE THE PAPER'S OWN CONTROL (the net conversion, or the conversion minus the control conversion, at or below zero)
                  is not an effect: no effect is filled and no raw conversion or amount stands in for it (the colour of the test is then background);
                  the qualitative statement of the paper decides the direction.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). The difference of two stated values and a product
                  amount over a volume have no stated spread of their own, so their variance stays null (variance_correspondence asks for the variance of
                  THIS estimate). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery, attributed signal/total signal, condition test/reference, the assertion and alternative
predictions.
qualitative_effect  only when NO effect is stated: statement 'interaction_detected' (read "conversion detected"), 'interaction_not_detected' (read
                  "conversion not detected") or 'interaction_not_stated' (read "conversion not stated"), with the refs of the fact conversion_detected_above_control
                  that states it. direction_field_support is the support class of that one fact (None when no statement is made). A stated effect fixes the
                  direction and the statement is then not used. A result stated in words alone already counts less than a measured one (the contract's
                  stated_strength); nothing of that is repeated here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives    spontaneous_reaction_control + enzyme_borne_signal
calibration_applicability  standard_curve_in_buffer + standard_curve_range + standard_curve_points
matrix_interference        reagent_interference_checked
attribution_supported      enzyme_dependence
product_identity           product_identity
endpoint_alignment         endpoint_time_stated + reaction_stopped + same_time_for_arms
conversion_denominator     denominator_stated + denominator_measured
sampling_basis             replicates
assertion_relevance        native_reaction
condition_scope            purified_enzyme
variance_correspondence    supported only when a variance was computed
measurement_identity is not selected (as in spectro_direct): the substrate, the product class and the units are the identity block's and the denominator and
the time are asked above. The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in
'_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Each judgement is a researched value of THIS method made gradual:
full agreement at the researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics gives (never a
step), unknown when the paper states nothing, never conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper itself
shows against the standard). A sheet criterion that is supported carries the smallest degree of its members that have one. Quote support
(literature_quote_support.apply_support) lowers the degree of a supported member and never changes a status. Combined status: any conflicting ->
conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped.

Range review (Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads
and whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every number is EXPERT_REVIEW,
owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
STANDARD_HIGH_FULL 1.0 -> STANDARD_HIGH_ZERO 3.0, judged on the log of the product read over the highest standard.
  Q1 an amount read beyond the top of the standard curve: the colour of the reagents saturates or drifts there, so the amount is an extrapolation.
  Q2 general: malachite green-molybdate, DNS, DTNB, Nessler and hydroxamate reagents all have a working range, and a sample above about 1.5 to 2 times the
  top standard is normally diluted and read again (from memory, not verified); at 3 times it the number is an uncalibrated extrapolation. Q3 relative to the
  paper's own curve (the grader records both and their ratio): right. Q4 the curvature error grows with the distance in multiples of the amount, so the
  degree falls linearly in the log of the ratio from 1 (read by interpolation, full) to 3 (conflicting). A reaction that was diluted into the colour reagent
  has a read amount in the curve's own terms only when the passage says so (product_read_on_curve is that field, not the concentration in the reaction), so
  the ratio is not distorted by the dilution. Q5 the same shape as the stopped_colorimetric activity type; the ends are the same because the reagent chemistry is.
STANDARD_LOW_FULL 1.0 -> STANDARD_LOW_ZERO 0.3, judged on the log of the product read over the lowest standard.
  Q1 an amount read below the lowest standard, near the blank, where the intercept of the curve and the noise of the blank dominate. Q2 general: the lowest
  standard of a curve is normally set at or above the quantitation limit, and the ICH Q2 relation puts the detection limit (3.3 sigma / slope) at about a
  third of the quantitation limit (10 sigma / slope), so a read amount at 0.3 of the lowest standard cannot be told from the blank (from memory, not
  verified). Q3 relative to the paper's own curve, as above. Q4 the relative error of an amount grows in inverse proportion to it, so the ramp is linear in the
  log of the ratio from 1 (full) to 0.3 (the detection limit: conflicting). Q5 mirror of the top end.
MIN_STANDARD_POINTS 6, STANDARD_POINTS_ZERO 2.
  Q1 a standard curve with too few standards to show that the colour is a straight line of the amount, so the amount read from it carries an unseen error.
  Q2 general: six to eight standards including a blank is the usual practice; ICH Q2 asks for at least five concentrations for linearity (from memory, not
  verified); the exact 6 is a judgement. Q3 absolute (a count). Q4 a straight line has two parameters, so two standards leave no residual degree of freedom
  (degree 0, supported, never conflicting: a short curve is weaker evidence, not wrong evidence); each added standard is one more point the line must pass
  through, so the degree rises linearly with count - 2. Q5 the same residual-degree-of-freedom count as the other curve fits (SPR steady-state, saturation curve).
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 an end point from one experiment, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice). Q3 absolute count. Q4 precision of
  a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the controls, the standard curve in buffer, the reagent check, the enzyme dependence, the product identification, the stop, the same
time, the measured substrate, the native substrate and the purified enzyme) and the two stated numbers (the time and the initial substrate): the paper's own
statement decides; yes or stated is supported, no is conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the
incubation time against the half-time of the reaction (the paper rarely states a half-time and the time is the paper's own choice of end point); the
conversion itself (it is the effect and its strength is on the class scale, ENDPOINT_STRENGTH_ANCHORS); the colour development time and the wavelength (a
reagent protocol detail the passage seldom states and the standard curve made in the same buffer and steps already covers); the pH and the temperature
(the claim carries no condition and the identity block records them); the control level against the test level (the effect is already the difference
between them, and a test no better than its control is not an effect).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this
assay, owner to confirm:
  What does it measure; absolute or relative? The amount of a product CLASS (phosphate, reducing ends, a thiol, ammonia) that a reagent turns into colour,
  read from a standard curve: absolute when the curve is made in the reaction matrix, but it names a class, not a product.
  Is there a reference range we would trust if the paper stated less? Partly: a conversion or an amount in the range these reagents read is plausible
  for a purified enzyme on its own substrate, but the range is far less well known than the range of kcat or KD.
  What does an unstated control or calibration do to the number's meaning? The classic false positive of colour assays is the reagent reacting with the
  substrate, the buffer or the enzyme preparation (free phosphate in ATP or in a protein preparation, thiols in a buffer additive, ammonium in a stock); an
  unstated blank leaves that open and it can be most of the signal for a weak conversion. An unstated standard curve in the reaction buffer is usually
  benign (the amount is off by a factor, not meaningless). An unstated time or stop is benign (an end point has a time).
  If we assume it is fine and are wrong, how badly does the score mislead? A background or a contaminating activity counted as the enzyme's gives the
  wrong direction for a small conversion; less severe than a pull-down band and more than a KD.
  Consistent with KD and with the stopped_colorimetric rate type (0.80)? The default 0.80 is level with it; the criteria that guard against a false
  conversion are lower, the benign ones are higher.
  default 0.80. background_alternatives 0.70 (the blanks are what separates conversion from reagent chemistry), attribution_supported 0.70 (a product class and
  a possible contaminating activity), matrix_interference 0.70 (phosphate or reducing agents in the buffer can blind or fake the reagent), product_identity 0.60
  (the colour cannot name the product, and an unstated independent identification leaves a contaminating phosphatase, ATPase or deaminase open), endpoint_alignment
  0.85 (a stop and a time are the usual practice of an end point), sampling_basis 0.90 (triplicates are usual). calibration_applicability, conversion_denominator,
  assertion_relevance and condition_scope take the default (a nominal substrate concentration is the usual denominator and is off by a weighing error, not by
  a factor).
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_conversion_direction import select_endpoint_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS, apply_support

VERSION = 'a105_endpoint_colorimetric_converted'
CRITERIA_MAP = {'background_alternatives': ('spontaneous_reaction_control', 'enzyme_borne_signal'),
                'calibration_applicability': ('standard_curve_in_buffer', 'standard_curve_range', 'standard_curve_points'),
                'matrix_interference': ('reagent_interference_checked',), 'attribution_supported': ('enzyme_dependence',), 'product_identity': ('product_identity',),
                'endpoint_alignment': ('endpoint_time_stated', 'reaction_stopped', 'same_time_for_arms'), 'conversion_denominator': ('denominator_stated', 'denominator_measured'),
                'sampling_basis': ('replicates',), 'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
MAXIMUM_FRACTION = 1.0  # FIXED_BY_DEFINITION: a share of the substrate converted cannot exceed all of it; a stated value above it is read as 1.
STANDARD_HIGH_FULL = 1.0  # EXPERT_REVIEW, owner to confirm: the product read at or under the top standard is read by interpolation on the paper's own curve; full agreement up to it.
STANDARD_HIGH_ZERO = 3.0  # EXPERT_REVIEW, owner to confirm, from memory, not verified: the colour reagents (malachite green-molybdate, DNS, DTNB, Nessler, hydroxamate) flatten or drift beyond their working range and a sample more than about 1.5 to 2 times the top standard is normally diluted; at three times it the amount is an uncalibrated extrapolation (no agreement); falls from STANDARD_HIGH_FULL linearly in the log of the ratio, because the curvature error grows with the distance in multiples of the amount.
STANDARD_LOW_FULL = 1.0  # EXPERT_REVIEW, owner to confirm: the product read at or over the lowest standard is read by interpolation on the paper's own curve; full agreement from it.
STANDARD_LOW_ZERO = 0.3  # EXPERT_REVIEW, owner to confirm, from memory, not verified: ICH Q2 puts the detection limit (3.3 sigma / slope) at about a third of the quantitation limit (10 sigma / slope) and the lowest standard is normally set at or above the quantitation limit, so an amount at 0.3 of it cannot be told from the blank (no agreement); falls from STANDARD_LOW_FULL linearly in the log of the ratio, because the relative error of an amount grows in inverse proportion to it.
MIN_STANDARD_POINTS = 6  # EXPERT_REVIEW, owner to confirm: fewest standards of a usable calibration curve (six to eight including a blank is the usual practice; ICH Q2 asks at least five for linearity, from memory, not verified); full agreement from it.
STANDARD_POINTS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: a straight-line calibration has two parameters, so two standards leave no residual degree of freedom (degree 0, supported, never conflicting: a short curve is weaker evidence); between this and MIN_STANDARD_POINTS the degree rises linearly with the residual degrees of freedom (count - 2).
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
FRACTION_PER_UNIT = {'percent': 0.01, 'fraction': 1.0}   # FIXED_BY_DEFINITION: a percent is a hundredth; the anchor unit of the conversion quantities is fraction.
UM_PER_UNIT = {'nM': 1.0e-3, 'uM': 1.0, 'mM': 1.0e3}   # FIXED_BY_DEFINITION: the factor of each concentration unit to uM, the anchor unit of endpoint_amount.
PMOL_PER_UNIT = {'pmol': 1.0, 'nmol': 1.0e3, 'umol': 1.0e6}   # FIXED_BY_DEFINITION: the factor of each amount unit to pmol.
UL_PER_UNIT = {'uL': 1.0, 'mL': 1.0e3}   # FIXED_BY_DEFINITION: the factor of each volume unit to uL; 1 pmol in 1 uL is 1 uM.
ANCHOR_UNIT = {'conversion_difference': 'fraction', 'conversion_fraction': 'fraction', 'endpoint_amount': 'uM'}   # ENDPOINT_STRENGTH_ANCHORS units of the three kinds this type fills
# The stated spread that belongs to each source of the effect (its native_component), with the factors to the anchor unit; a derived effect has none.
SPREAD_OF = {'net_conversion': ('net_conversion_spread', FRACTION_PER_UNIT), 'conversion': ('conversion_spread', FRACTION_PER_UNIT),
             'product_concentration': ('product_concentration_spread', UM_PER_UNIT)}
NULL_REASONS = {'recovery': 'an_endpoint_colorimetric_has_no_matrix_recovery_measurement', 'attributed_signal': 'an_endpoint_conversion_is_not_an_attribution_fraction', 'total_signal': 'an_endpoint_conversion_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_an_endpoint_colorimetric_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_endpoint_colorimetric_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENT = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "conversion detected" / "conversion not detected" / "conversion not stated" for this class


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


def _graded(refs, *limits):
    """Each limit is (value, full_agreement_limit, zero_agreement_limit), all on the criterion's own scale. Conflicting when any value is at or beyond its zero limit; else supported with the smallest degree, 1.0 at the full limit falling linearly on that scale to 0 at the zero limit."""
    degrees = [_share(value, full, zero) for value, full, zero in limits]
    if min(degrees) <= 0:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, *degrees))


def _log(value, full, zero):
    """A ratio limit on the log scale, for _graded."""
    return math.log(value), math.log(full), math.log(zero)


def _judge_standard_range(native):
    # each end that the paper gives keeps its own ramp; the product read is judged against every end that is stated
    limits = []
    if native['product_over_standard_high'] is not None:
        limits.append(_log(native['product_over_standard_high'], STANDARD_HIGH_FULL, STANDARD_HIGH_ZERO))
    if native['product_over_standard_low'] is not None:
        limits.append(_log(native['product_over_standard_low'], STANDARD_LOW_FULL, STANDARD_LOW_ZERO))
    return _graded(native['standard_range_refs'], *limits)


def _judge_standard_points(native):
    # the count only lowers the degree, never conflicts (a short curve is weaker evidence); linear in the residual degrees of freedom of a straight line
    return _verdict('supported', native['standard_points_refs'], max(0.0, min(1.0, _share(native['standard_points'], MIN_STANDARD_POINTS, STANDARD_POINTS_ZERO))))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('standard_curve_range', 'standard_range_recorded_for_the_sheet'): _judge_standard_range, ('standard_curve_points', 'standard_points_recorded_for_the_sheet'): _judge_standard_points,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _fraction(operand):
    """A stated share converted as a fraction: the exact unit factor, and never above all of the substrate."""
    return min(operand['value'] * FRACTION_PER_UNIT[operand['unit']], MAXIMUM_FRACTION)


def _weakest(*supports):
    return max(supports, key=SUPPORTS.index)


def _difference(native):
    """The conversion above the paper's own control as (fraction, refs, origin, component, support): the net conversion the paper states, else the exact
    difference of the stated conversion and the stated control conversion; None when neither is given."""
    quantities = native['quantities']
    net, test, control = quantities['net_conversion'], quantities['conversion'], quantities['control_conversion']
    if net['status'] == 'point':
        return _fraction(net), net['source_refs'], net['origin'], 'net_conversion', net['support']
    if test['status'] == 'point' and control['status'] == 'point':
        return (_fraction(test) - _fraction(control), list(dict.fromkeys([*test['source_refs'], *control['source_refs']])), 'derived', 'conversion_minus_control',
                _weakest(test['support'], control['support']))
    return None


def _amount(native, ref):
    """The product at the end point as a concentration in uM: the stated concentration, else the stated amount over the stated reaction volume (pmol per uL is uM); None when neither is given."""
    quantities = native['quantities']
    concentration, amount, volume = quantities['product_concentration'], quantities['product_amount'], quantities['reaction_volume']
    key = 'endpoint_colorimetric_endpoint_amount:' + ref
    if concentration['status'] == 'point':
        return _operand(concentration['value'] * UM_PER_UNIT[concentration['unit']], 'uM', key, concentration['source_refs'], concentration['origin'], 'product_concentration', concentration['support'])
    if amount['status'] == 'point' and volume['status'] == 'point':
        value = amount['value'] * PMOL_PER_UNIT[amount['unit']] / (volume['value'] * UL_PER_UNIT[volume['unit']])
        return _operand(value, 'uM', key, list(dict.fromkeys([*amount['source_refs'], *volume['source_refs']])), 'derived', 'product_amount_over_reaction_volume', _weakest(amount['support'], volume['support']))
    return None


def _stated_effects(native, ref):
    """({kind: operand or None for the three kinds this type fills}, True when the paper's own control shows no conversion above it)."""
    difference = _difference(native)
    not_above_control = difference is not None and difference[0] <= 0
    if not_above_control:
        return dict.fromkeys(ANCHOR_UNIT), True
    test = native['quantities']['conversion']
    return {'conversion_difference': None if difference is None else _operand(difference[0], 'fraction', 'endpoint_colorimetric_conversion_difference:' + ref, difference[1], difference[2], difference[3], difference[4]),
            'conversion_fraction': None if test['status'] != 'point' else _operand(_fraction(test), 'fraction', 'endpoint_colorimetric_conversion_fraction:' + ref, test['source_refs'], test['origin'], 'conversion', test['support']),
            'endpoint_amount': _amount(native, ref)}, False


def _variance(graded, effect):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of the chosen effect."""
    native = graded['native']
    component = effect['native_component']
    if component not in SPREAD_OF:
        return None, component + '_has_no_stated_variance', []
    name, factors = SPREAD_OF[component]
    spread = native['quantities'][name]
    if spread['status'] != 'point':
        return None, name + '_not_given', []
    if native['spread_kind'] is None:
        return None, 'spread_kind_not_stated', []
    sd = spread['value'] * factors[spread['unit']]
    if native['spread_kind'] == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if native['spread_kind'] == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_endpoint_colorimetric(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated, not_above_control = _stated_effects(native, ref)
    quantity_kind, effect_support = 'conversion_fraction', None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'conversion_not_above_the_papers_own_control' if not_above_control else 'no_endpoint_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_endpoint_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = chosen, effect['support']
        variance, variance_reason, variance_refs = _variance(graded, effect)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, ANCHOR_UNIT[chosen] + '_squared', 'endpoint_colorimetric_' + chosen + '_variance:' + ref, variance_refs, 'derived', effect['native_component'] + '_spread')
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
        interpretations[sheet_criterion] = {'status': status, 'support_refs': refs if status == 'supported' else []}
        degrees = [m['degree'] for m in graded_members if 'degree' in m]
        if status == 'supported' and degrees:
            interpretations[sheet_criterion]['degree'] = min(degrees)      # the weakest member: a degree of a member is not averaged away
    if quantities['effect_variance'] is not None:
        interpretations['variance_correspondence'] = {'status': 'supported', 'support_refs': quantities['effect_variance']['source_refs']}
    extraction = {'version': INPUT_VERSION, 'assay_type': 'endpoint_conversion', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    converted = {'version': VERSION, 'experiment_type': 'endpoint_colorimetric', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
                 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no stated effect: the paper's own words, conversion detected above its control or not, stand (scored like any stated result, literature_direction, the qualitative path)
        converted['qualitative_effect'] = {'statement': STATEMENT[native['conversion_statement']], 'support_refs': list(native['conversion_statement_refs'])}
        if native['conversion_statement'] is not None:
            converted['direction_field_support'] = native['conversion_statement_support']      # the support class of the fact conversion_detected_above_control, the one field the statement is derived from
    return converted
