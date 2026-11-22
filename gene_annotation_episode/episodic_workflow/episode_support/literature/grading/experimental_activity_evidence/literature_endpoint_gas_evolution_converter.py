"""Endpoint_gas_evolution converter: turns the grader's result into what the A105 endpoint_conversion sheet takes. DRAFT of 2026-11-22, owner to correct.

Hand-built, private to endpoint_gas_evolution, deterministic. Input: the result of grade_endpoint_gas_evolution. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'endpoint_conversion'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for every sheet
component that a gas end point cannot honestly fill, the reason it stays null. The method: an enzyme reaction in a closed vessel, a gas product that collects
in the headspace, read by gas chromatography or manometry at a stated time.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity (literature_row_contract.ENDPOINT_STRENGTH_ANCHORS): the control-corrected percent of the
                  theoretical yield the paper itself states (kind conversion_difference, fraction), the percent of the theoretical yield (conversion_fraction,
                  fraction) or the gas amount per liquid volume (endpoint_amount, uM). Several may be stated; the one used is the best-determined, in the class
                  order ENDPOINT_EFFECT_ORDER (literature_endpoint_conversion_direction.select_endpoint_effect; the reason is in the contract). A percent is a
                  hundredth (exact). A gas amount in nmol over the liquid volume in mL is micromolar (exact: nmol per mL is umol per L); it is an effect only when
                  the passage states the liquid volume, because the amount of a gas in a vessel has no concentration without it. A stated percent above 100 is not
                  a share of the substrate (a fraction cannot exceed 1, the direction function raises on it): it is not used as an effect, its place is taken by
                  the next stated quantity, and the criterion yield_not_above_theoretical records it. quantity_kind of the extraction names the kind of the effect.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery, attributed signal/total signal, condition test/reference, the assertion
and alternative predictions.
qualitative_effect  only when NO effect is stated: the paper's own statement whether it saw gas above its own control (the fact gas_detected_above_control):
                  statement 'interaction_detected' (read "conversion detected"), 'interaction_not_detected' (read "conversion not detected") or
                  'interaction_not_stated', with the refs of the fact that states it. direction_field_support is the quote support of that one fact. A stated
                  effect fixes the direction; the statement is then not used. A result stated in words alone counts less than a measured one: that is the
                  contract's stated_strength, not done here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
measurement_identity      vessel_volumes
calibration_applicability calibration_gas + calibration_range + detection_margin
matrix_interference       dissolved_gas   (the inventory draft put this one under conversion_denominator; the part of a gas that stays dissolved is a sample and
                          matrix matter of the numerator, not of the denominator, and the sheet's conversion_denominator question asks about the measured initial
                          amount: owner to confirm)
background_alternatives   spontaneous_gas_control + zero_time_gas + leak_control + signal_over_control
attribution_supported     enzyme_dependence
product_identity          gas_identity
endpoint_alignment        time_point_stated + same_time_for_compared_arms
conversion_denominator    yield_denominator + yield_not_above_theoretical
sampling_basis            replicates
assertion_relevance       native_reaction
condition_scope           purified_enzyme
variance_correspondence   supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in
'_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Each judgement is a researched value of THIS assay made
gradual (SOP step 3): full agreement at the researched good value, falling linearly on the scale the physics of the quantity gives to zero at a researched
no-longer-meaningful value (never a step), unknown when the paper states nothing, never conflicting for a short count. A value at or beyond its zero end
is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported carries the smallest degree of its members that have
one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined status: any
conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all
not_applicable is not selected. Sheet criteria with no counterpart here (partner_perturbation is not in this class) are not selected.

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None
(no immobilized enzyme, no electrode). Qualitative statements keep the existing vocabulary. Direction and strength of a stated end point:
literature_endpoint_conversion_direction (larger is stronger; controls, blanks, calibration and the rest lower the WEIGHT only). The time of the sheet's
endpoint_alignment question reads two arms; a single arm with a stated time is supported by time_point_stated, and the second member is then unknown unless the
passage says the arms were read together.

THE VALUES BELOW ARE A FIRST DRAFT FOR THE OWNER: every number is EXPERT_REVIEW, owner to confirm, and every one is from the drafter's memory of gas-chromatographic
and manometric practice, NOT web-verified and NOT checked against a method paper; verify before relying on any of them. The owner's questions are asked of each
value (Q1 failure caught, Q2 general or lab-specific, Q3 absolute or relative, Q4 how badly a wrong value misleads and whether the shape fits, Q5 consistency
with the other assays).
------------------------------------------------------------------------------------------------------------------------------------------------------------
CALIBRATION_ZERO_RATIO_ABOVE 10 / CALIBRATION_ZERO_RATIO_BELOW 0.1, full at 1 (the edge of the calibration), judged on the log of the amount over the standard.
  Q1 a gas amount read outside the amounts the calibration was made with: above the top standard the detector may no longer be linear (a thermal-conductivity
  detector bends at percent levels of H2 in the carrier), below the bottom one the blank, the adsorption on the vessel and the stopper and the integration of a
  small peak decide. Q2 general practice: a calibration is evidence only for the amounts it brackets; standards are usually a decade or half-decade series
  (from memory, not verified); the zero end of a decade is a judgement. Q3 relative to the paper's own calibration range, which the grader records. Q4 a reading
  a decade outside is not shown by the calibration at all (no agreement, conflicting); the error of an extrapolation grows with the distance on the log scale,
  so the degree falls linearly in the log of the ratio, from 1 at the edge. A reading inside the range is full agreement. Q5 the log-ratio ramp of the other
  ratio judgements of the class (the fold ramps of the binding assays).
DETECTION_MARGIN_FULL_RATIO 3 / DETECTION_MARGIN_ZERO_RATIO 1, judged on the relative noise 1 / (amount over detection limit).
  Q1 a gas amount that is not clearly above the noise of the reading, so the amount is mostly noise and the "gas formed" may be a blank. Q2 general: the
  detection limit is about 3.3 standard deviations of the blank over the slope and the quantification limit about 10 (ICH Q2(R1), from memory), so the
  quantification limit is about three times the detection limit; at three times the limit the amount is quantified. Q3 relative to the paper's own detection
  limit, recorded by the grader. Q4 the relative noise of a reading of x with a noise sigma is sigma / x, which is 1 / (x over the limit) in units of the
  limit's noise; the degree falls linearly in it from full at 1/3 to none at 1 (a reading at the detection limit is not distinguished from the blank:
  conflicting). Q5 no other class has a detection limit; a stated amount at or under the paper's own limit is what the paper itself shows against the standard.
CONTROL_NET_SHARE_FULL 0.9 / CONTROL_NET_SHARE_ZERO 0, judged on the net share 1 - control / test.
  Q1 a control vessel whose gas is as large as the test vessel's: the gas does not come from the enzyme. Q2 arithmetic and practice: the net share of the test
  gas is what the enzyme gives; with a control at a tenth of the test the correction changes the result by at most a tenth, which no one treats as
  a problem (blank at most a tenth of the signal; from memory, not verified); lab-specific. Q3 relative to the paper's own control, recorded by the grader.
  Q4 the net share is an additive scale (the share of the gas that is not the control's), so the degree is linear in it: full at 0.9, none at 0 (control equal
  to the test: conflicting, the paper's own numbers show no enzyme gas); a control larger than the test is also beyond the zero end. Q5 the same idea as the
  signal over its own control in the other assays (a signal no larger than the control is conflicting).
YIELD_FULL_RATIO 1.1 / YIELD_ZERO_RATIO 2.0, judged on the ratio of the gas found to the theoretical yield (linear).
  Q1 more gas than the substrate can give: a gas source other than the stated substrate (a contaminant, the buffer, the reductant), a wrong stoichiometry or a
  wrong substrate amount. A yield below the theoretical is a normal incomplete conversion and is not judged. Q2 general: a headspace gas chromatographic
  amount has a precision of a few percent and the calibration and the substrate amount a few percent more, so a yield up to about 110 percent reads as
  complete conversion (from memory, not verified); twice the possible gas is a factor no measurement error gives. Q3 relative to the paper's own theoretical
  yield (or its own percent of it), recorded by the grader. Q4 an excess is an additive error, so the degree is linear in the ratio from full at 1.1 to none at
  2.0; at or beyond 2.0 the paper's own numbers show a source of gas beyond the substrate (conflicting). Q5 no other class has a yield ceiling.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a gas amount from one vessel, whose vessel-to-vessel spread (leaks, stopper, injection) is unseen. Q2 general (triplicate practice). Q3 absolute count.
  Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule; repeated injections from one vessel are
  not replicates.
Facts with no number (the controls, the zero-time sample, the leak check, the enzyme dependence, the gas identity, the calibration gas, the dissolved gas,
the same time for the arms, the measured substrate, the native substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is
conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the gas species and the readout method (recorded choices; a
choice holds no span in the merged record); the headspace-to-liquid ratio (how much gas stays dissolved depends on the gas, and the species is a choice, so
the grader cannot compute it; the paper's statement that the dissolved part was counted is the fact dissolved_gas); the pH and the temperature (the claim
carries no condition, and the identity block records the temperature); anaerobic technique (no criterion: it applies to oxygen-sensitive enzymes only, and
asking for it would count an aerobic assay as lacking it).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered
for this assay, decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The total amount of one named gas formed in a closed vessel at one time, from a chromatographic or manometric
  reading calibrated with known gas amounts: an absolute amount of substance, or a percent of a theoretical amount.
  Is there a reference range we would trust if the paper stated less (as for KD)? Partly: headspace gas chromatography of H2, CO2, CH4 and N2O is routine
  with a precision of a few percent when calibrated, so an unstated calibration is usually benign; the amount that results depends on the stated vessel.
  What does an unstated control or calibration do to the number's meaning? An unstated no-enzyme vessel, zero-time sample or leak check is the main gap:
  gas can come from a reductant and a metal without the enzyme, from the chamber or the buffer before the reaction, or be lost through the stopper; a leak
  lowers the amount and does not make a false gas. An unstated calibration in the same vessel or an unstated dissolved part changes the size of the amount
  (strongly for CO2 and N2O, whose solubility and bicarbonate hold much of the gas) and not that gas formed.
  If we assume it is fine and are wrong, how badly does the score mislead? A non-enzymatic or contaminant gas counted as the enzyme's is a wrong direction for a
  weak amount and a wrong size for a strong one; a wrong calibration is a size error only; less severe than a pull-down band (a pure artefact) and about the
  same as a spectrophotometric blank.
  Consistent with KD? The default 0.85 equals the spectro_direct default and is just under the KD anchor 0.90 (an absolute amount from a calibrated reading, with a
  few more ways to be wrong than a KD by a label-free method); the criteria that guard against a false gas are lower, the benign ones equal or above it.
  default 0.85. background_alternatives 0.75 (a real gap: the control vessels and the zero-time sample separate enzyme gas from chemistry and contamination).
  attribution_supported 0.80 (a contaminating activity or a second source of the gas; typical practice shows dependence on the enzyme but papers often leave it
  unsaid). matrix_interference 0.80 (the dissolved part is small for H2, CH4 and O2 and large for CO2 and N2O; the species is a choice, so one middle value).
  endpoint_alignment 0.90, measurement_identity 0.90, sampling_basis 0.90 (benign when unstated: a headspace is read at a stated time of the reaction, the vessel
  is the one the amount is reported for, triplicates are usual). calibration_applicability, conversion_denominator, product_identity, assertion_relevance and
  condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_conversion_direction import select_endpoint_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_gas_evolution_criteria import NMOL_PER_UNIT, PERCENT_PER_FRACTION
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_endpoint_gas_evolution_converted_v1'
CRITERIA_MAP = {'measurement_identity': ('vessel_volumes',), 'calibration_applicability': ('calibration_gas', 'calibration_range', 'detection_margin'),
                'matrix_interference': ('dissolved_gas',), 'background_alternatives': ('spontaneous_gas_control', 'zero_time_gas', 'leak_control', 'signal_over_control'),
                'attribution_supported': ('enzyme_dependence',), 'product_identity': ('gas_identity',), 'endpoint_alignment': ('time_point_stated', 'same_time_for_compared_arms'),
                'conversion_denominator': ('yield_denominator', 'yield_not_above_theoretical'), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
ML_PER_UNIT = {'uL': 1.0e-3, 'mL': 1.0}   # FIXED_BY_DEFINITION: 1 uL is 0.001 mL; nmol per mL is umol per L, that is micromolar.
MAX_FRACTION = 1.0   # FIXED_BY_DEFINITION: a share of the substrate cannot exceed 1 (the direction function raises on a larger fraction).
RANGE_EDGE_RATIO = 1.0   # FIXED_BY_DEFINITION: the amount equal to the highest or the lowest standard is at the edge of the calibration range; full agreement from there inward.
CALIBRATION_ZERO_RATIO_ABOVE = 10.0  # EXPERT_REVIEW, owner to confirm: amount over the highest standard at which the calibration no longer says anything (a decade of extrapolation; detector linearity ends, from memory, not verified); the degree falls linearly in the log of the ratio from 1 at the edge. At or beyond it: conflicting.
CALIBRATION_ZERO_RATIO_BELOW = 0.1  # EXPERT_REVIEW, owner to confirm: amount over the lowest standard at which the calibration no longer says anything (a decade below it; blank, adsorption and small-peak integration decide, from memory, not verified); linear in the log of the ratio from 1 at the edge. At or beyond it: conflicting.
DETECTION_MARGIN_FULL_RATIO = 3.0  # EXPERT_REVIEW, owner to confirm: amount over the detection limit from which the amount is quantified (quantification limit about 10 sigma over detection limit about 3.3 sigma, ICH Q2(R1), from memory, not verified); full agreement from it.
DETECTION_MARGIN_ZERO_RATIO = 1.0  # EXPERT_REVIEW, owner to confirm: amount at the detection limit, not distinguished from the blank (no agreement, conflicting); the degree falls linearly in the relative noise 1 / ratio from the full end to here.
CONTROL_NET_SHARE_FULL = 0.9  # EXPERT_REVIEW, owner to confirm: net share 1 - control / test from which the control changes the result by at most a tenth (blank at most a tenth of the signal; from memory, not verified); full agreement from it.
CONTROL_NET_SHARE_ZERO = 0.0  # EXPERT_REVIEW, owner to confirm: net share 0, the control as large as the test (no enzyme gas shown: conflicting); the degree is linear in the net share, an additive scale, from the full end to here.
YIELD_FULL_RATIO = 1.1  # EXPERT_REVIEW, owner to confirm: gas found over the theoretical yield up to which the result reads as complete conversion (headspace chromatography precision and calibration error of a few percent each, from memory, not verified); full agreement up to it. A lower yield is not judged.
YIELD_ZERO_RATIO = 2.0  # EXPERT_REVIEW, owner to confirm: gas found at twice the theoretical yield, a factor no measurement error gives: a source of gas beyond the stated substrate (no agreement, conflicting); linear in the ratio (an additive excess) from the full end to here.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate vessels or experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent vessels falls as 1 / sqrt(n); never conflicting for a stated count.
# The record quantity that states each effect kind (literature_row_contract.ENDPOINT_EFFECT_ORDER), its spread, and the anchor unit of the kind (ENDPOINT_STRENGTH_ANCHORS).
EFFECT_SOURCE = {'conversion_difference': ('net_conversion_percent', 'net_conversion_spread', 'fraction'),
                 'conversion_fraction': ('conversion_percent', 'conversion_spread', 'fraction'),
                 'endpoint_amount': ('gas_amount', 'gas_amount_spread', 'uM')}
KIND_WITHOUT_EFFECT = 'conversion_fraction'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NOT_STATED = 'not_stated'
NULL_REASONS = {'recovery': 'a_gas_end_point_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_gas_amount_is_not_an_attribution_fraction', 'total_signal': 'a_gas_amount_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_gas_end_point_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_gas_end_point_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "conversion detected" / "conversion not detected" for this class


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


def _judge_control(native):
    # the net share of the test gas that is not the control's: additive scale, linear
    return _graded(native['control_refs'], (1.0 - native['control_over_test'], CONTROL_NET_SHARE_FULL, CONTROL_NET_SHARE_ZERO))


def _judge_range(native):
    # inside the calibration: full agreement; outside: linear in the log of the ratio to the nearest standard, from 1 at the edge to the zero ratio
    refs = native['calibration_refs']
    above, below = native['amount_over_calibration_high'], native['amount_over_calibration_low']
    if above > RANGE_EDGE_RATIO:
        return _graded(refs, _log(above, RANGE_EDGE_RATIO, CALIBRATION_ZERO_RATIO_ABOVE))
    if below < RANGE_EDGE_RATIO:
        return _graded(refs, _log(below, RANGE_EDGE_RATIO, CALIBRATION_ZERO_RATIO_BELOW))
    return _verdict('supported', refs, 1.0)


def _judge_margin(native):
    # the relative noise of the reading, 1 / (amount over the detection limit), is the scale
    return _graded(native['detection_refs'], (1.0 / native['amount_over_detection_limit'], 1.0 / DETECTION_MARGIN_FULL_RATIO, 1.0 / DETECTION_MARGIN_ZERO_RATIO))


def _judge_yield(native):
    # an excess over the theoretical yield is an additive error: linear in the ratio; a lower yield is full agreement
    return _graded(native['yield_refs'], (native['yield_over_theoretical'], YIELD_FULL_RATIO, YIELD_ZERO_RATIO))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('signal_over_control', 'control_recorded_for_the_sheet'): _judge_control, ('calibration_range', 'calibration_range_recorded_for_the_sheet'): _judge_range,
          ('detection_margin', 'detection_margin_recorded_for_the_sheet'): _judge_margin, ('yield_not_above_theoretical', 'yield_recorded_for_the_sheet'): _judge_yield,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _anchored(native, name, unit):
    """The number of the record quantity ``name`` in the anchor unit ``unit`` by an exact factor; None when it is not stated or (for an amount) the liquid volume is not."""
    operand = native['quantities'][name]
    if operand['status'] != 'point':
        return None
    if unit == 'fraction':
        return operand['value'] / PERCENT_PER_FRACTION
    liquid = native['quantities']['liquid_volume']
    if liquid['status'] != 'point':
        return None
    return operand['value'] * NMOL_PER_UNIT[operand['unit']] / (liquid['value'] * ML_PER_UNIT[liquid['unit']])


def _stated_effect(native, kind, ref):
    """(the stated quantity of this effect kind as an effect operand in its anchor unit, None) or (None, why it is not usable). Its 'support' is the extraction's."""
    name, _, unit = EFFECT_SOURCE[kind]
    operand = native['quantities'][name]
    value = _anchored(native, name, unit)
    if operand['status'] != 'point':
        return None, NOT_STATED
    if value is None:
        return None, 'liquid_volume_not_stated_so_the_gas_amount_has_no_concentration'
    if unit == 'fraction' and value > MAX_FRACTION:
        return None, 'stated_percent_above_100_is_not_a_share_of_the_substrate'
    if unit == 'fraction':
        return _operand(value, unit, 'endpoint_gas_evolution_' + kind + ':' + ref, operand['source_refs'], operand['origin'], name, operand['support']), None
    refs = list(dict.fromkeys([*operand['source_refs'], *native['quantities']['liquid_volume']['source_refs']]))
    return _operand(value, unit, 'endpoint_gas_evolution_' + kind + ':' + ref, refs, 'derived', name, operand['support']), None


def _variance(graded, kind, ref):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of the quantity of ``kind``."""
    native = graded['native']
    name, spread_name, unit = EFFECT_SOURCE[kind]
    spread = native['quantities'][spread_name]
    kind_of_spread = native['spread_kind']
    if spread['status'] != 'point':
        return None, spread_name + '_not_given', []
    if kind_of_spread is None:
        return None, 'spread_kind_not_stated', []
    sd = _anchored(native, spread_name, unit)
    refs = spread['source_refs'] if unit == 'fraction' else list(dict.fromkeys([*spread['source_refs'], *native['quantities']['liquid_volume']['source_refs']]))
    if kind_of_spread == 'standard_error':
        return sd * sd, None, refs
    if kind_of_spread == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*refs, *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_endpoint_gas_evolution(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    found = {kind: _stated_effect(native, kind, ref) for kind in EFFECT_SOURCE}
    stated = {kind: operand for kind, (operand, why) in found.items()}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        unusable = [why for operand, why in found.values() if why != NOT_STATED]
        null_components['effect'] = unusable[0] if unusable else 'no_gas_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_endpoint_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = chosen, effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, EFFECT_SOURCE[chosen][2] + '_squared', 'endpoint_gas_evolution_' + chosen + '_variance:' + ref, variance_refs, 'derived', EFFECT_SOURCE[chosen][1])
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
    result = {'version': VERSION, 'experiment_type': 'endpoint_gas_evolution', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no stated quantity: the paper's own statement of gas above its control fixes the direction (owner, 2026-11-22), scored like any stated result (literature_direction, the qualitative path)
        result['qualitative_effect'] = {'statement': STATEMENTS[native['gas']], 'support_refs': list(native['gas_refs'])}
        if native['gas'] is not None:
            result['direction_field_support'] = native['gas_support']      # the support class of the fact gas_detected_above_control, the one field the statement is derived from
    return result
