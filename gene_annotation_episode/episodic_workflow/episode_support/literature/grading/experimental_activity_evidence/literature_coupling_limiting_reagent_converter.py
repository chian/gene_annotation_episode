"""Coupling_limiting_reagent converter: turns the grader's result into what the A105 reaction_coupling sheet takes. DRAFT 2026-11-22, owner to correct.

Hand-built, private to coupling_limiting_reagent, deterministic. Input: the result of grade_coupling_limiting_reagent. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'reaction_coupling'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for every sheet
component that a limiting-reagent endpoint cannot honestly fill, the reason it stays null. The shape follows literature_spectro_direct_converter.py (the activity_rate
template); the class core is the reaction_coupling one (A105_REACTION_COUPLING_INVENTORY.md sections 2, 4 and 6; literature_reaction_coupling_direction.py).

Quantities filled
-----------------
effect            ONE coupling quantity in the anchor unit 'fraction' (literature_reaction_coupling_direction.COUPLING_STRENGTH_ANCHORS), chosen in the class order
                  (select_coupling_effect: the productive fraction first, then the stoichiometric ratio). Each of the two comes from the paper's own number when it
                  is stated and otherwise from the measured equivalents of limiting reagent per product e by exact arithmetic, marked origin 'derived':
                    productive_fraction     stated productive_fraction; else coefficient / e  (the coefficient stated, e measured: the share of the limiting reagent
                                            that ended in product with the reaction's own coefficient applied; 2 NADPH per product measured against an expected 2 is 1)
                    stoichiometric_ratio    stated yield_over_limiting_reagent; else 1 / e  (the product per limiting reagent, no coefficient applied; 2 NADPH per product is 0.5)
                  A percent is divided by 100 (FIXED_BY_DEFINITION). quantity_kind of the extraction names the kind of the effect (KIND_OF_QUANTITY), which the
                  direction function reads. A ratio above 1 is not clipped: the direction reads it at the strong end and the criteria (reaction_coefficient)
                  show that it is beyond the stoichiometric bound.
effect_variance   variance of that effect, in 'fraction_squared', only when the passage's spread of the quantity the effect comes from allows it: standard_error -> se^2;
                  standard_deviation -> sd^2 / n and only when the replicates criterion is supported; confidence_interval -> not converted (needs its level and degrees
                  of freedom). A derived effect carries the spread of e through the derivative of its formula (the delta method): the slope is coefficient / e^2 for the
                  productive fraction and 1 / e^2 for the ratio. Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery, attributed signal/total signal, condition test/reference, the assertion and alternative predictions.
qualitative_effect  only when NO effect is available and the paper states whether it saw the claimed product formed from the limiting reagent above its own control: statement
                  'interaction_detected' (read "coupled product formation detected") or 'interaction_not_detected' (read "no product formed above the paper's own control or
                  detection limit"), with the refs of the fact that states it (coupled_product_detected). direction_field_support is the quote support of that one fact. A
                  stated effect fixes the direction; the statement is then not used. A result stated in words alone counts less than a measured one through the contract's
                  stated_strength, which is not re-implemented here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
matched_windows            same_reaction + completion_shown (one reaction, one end, the limiting reagent used up: both sides read at the same endpoint)
stoichiometry              reaction_coefficient + excess_of_other_reagents + no_regeneration (the coefficient, nothing else limiting, the limiting amount not refilled)
calibration_applicability  limiting_amount_verified + product_calibration
product_identity           product_identity
reporter_specificity       no_substrate_control. This type has no reporter, but the sheet refuses 'not_applicable' for a required criterion and its question is also
                           whether the partner is used by something other than the claimed reaction: here that is the limiting reagent used up by the enzyme with no substrate
                           (an oxidase side activity), so the criterion is filled and not left out.
background_alternatives    no_enzyme_control
attribution_supported      inactive_enzyme_control
sampling_basis             replicates + titration_points
assertion_relevance        native_reaction
condition_scope            purified_enzyme
variance_correspondence    supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity, matrix_interference) are not selected.
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Each judgement is a researched value of THIS method made gradual (SOP step 3): full agreement at the researched good value, falling
smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the method gives (never a step), unknown when the paper states nothing, never
conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported carries
the smallest degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a
status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all
not_applicable is not selected.

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None. Direction and strength
of a stated link: literature_reaction_coupling_direction (larger is stronger); controls, the coefficient, the endpoint and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads and whether the
shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
REMAINING_FULL_PERCENT 5 -> REMAINING_ZERO_PERCENT 50, judged linearly in the share of the limiting reagent left.
  Q1 an "endpoint" that is not one: if a share r of the limiting reagent is still there, the product per limiting reagent ADDED reads low by exactly that share,
  product / added = (1 - r) x product / used up, and the equivalents per product read high by 1 / (1 - r). Q2 general: an endpoint absorbance or a chromatographic peak is read to
  a few percent (a cofactor assay by absorbance with its extinction coefficient, pipetting of the limiting amount, a calibrated product peak), so a few percent left is inside the
  ordinary error of the number; from memory, a judgement. Q3 relative to the paper's own starting amount, which the passage states as a share; right. Q4 the bias is linear in r, so the
  degree is linear in r: 1 up to 5 percent, 0.5 at about 27 percent, and at 50 percent (half the limiting reagent unreacted, a factor 2 on the ratio) the reaction has not gone to
  completion and the claim that the product measures the limiting reagent fails (conflicting). Q5 the same idea as the consumed-substrate curve of the activity types: a bias that grows
  with the departure from the researched value.
EXCESS_FULL_FOLD 10 -> EXCESS_ZERO_FOLD 1, judged linearly in the share d = 1 / fold of the other reagent that the run uses up.
  Q1 a reagent that is called the excess but is nearly equal to the limiting reagent: neither limits cleanly, the rate of the last part of the reaction falls as the other reagent is
  used up (second-order tail), and the endpoint is approached only slowly. Q2 general: a ten-fold excess is the usual rule for a reagent to stay nearly constant over a run (pseudo-first-order
  practice, Cornish-Bowden, Fundamentals of Enzyme Kinetics, and Segel, Enzyme Kinetics, from memory); the 10 is a practice figure. Q3 relative to the paper's own limiting amount, which the
  passage gives as a fold. Q4 over the run the other reagent falls by the share d = 1 / fold (when it is used one for one with the limiting reagent; a coefficient above 1 on the limiting reagent
  would lower d, so this is the cautious reading); the rate constant of the limiting reagent changes by about that share; the degree is linear in d: 1 at ten-fold (d = 0.1), 0.56 at two-fold,
  0 at equal amounts (d = 1), where nothing is in excess; a fold at or below 1 is conflicting (the paper's own numbers show nothing is in excess). Q5 a depletion share, as the consumed-
  substrate curve of the activity types.
EQUIVALENTS_FULL_FACTOR 1.1 -> EQUIVALENTS_ZERO_FACTOR 2.0, judged linearly in |ln q|, q = the measured equivalents per product over the paper's own coefficient.
  Q1 a measured stoichiometry that does not match the reaction the paper itself writes: the limiting reagent is used by a side reaction (q above 1: more used than the reaction takes, for
  example NADPH oxidase activity) or the product is formed another way (q below 1) or the coefficient is wrong. Q2 general: the combined error of such an endpoint is about 10 percent (the limiting
  amount by its absorbance, about 2 to 3 percent; the product against its standard, about 5 percent; from memory, a judgement), so within 10 percent is agreement; a factor 2 is the step to the
  next whole stoichiometric number (1 against 2 equivalents), a different reaction. Q3 relative to the paper's own coefficient, which the grader records. Q4 deviations are multiplicative, so the
  scale is the log of the ratio and both directions count alike (a factor 1.5 gives a degree of 0.55); at a factor 2 or more the paper's own two numbers disagree (conflicting). Q5 a log-ratio ramp
  like the other ratio judgements of the binding assays (fold gaps).
MIN_TITRATION_POINTS 5, TITRATION_POINTS_ZERO 2.
  Q1 a titration of the limiting reagent that shows too few points to see the rise and the break. Q2 general (from memory, a judgement): a titration curve of product against added limiting reagent
  has two parameters, the slope of the rise and the position of the break, so two points are used up by the fit and leave no residual degree of freedom; about five points (three residual) show the
  line, the break and the plateau. Q3 absolute (a count); a single dose is not a titration and the criterion is unknown, not penalised, when no count is stated. Q4 the degree rises linearly with the
  residual degrees of freedom count - 2 (supported with degree 0 at 2 points, never conflicting). Q5 the same residual-degree-of-freedom count as the substrate series of the activity types.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a ratio from one experiment, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for
  the variance. Q5 exactly the shared replicate rule.
Facts with no number (the identity and calibration of the product, the same mixture and endpoint, the three controls, no regeneration, the verified limiting amount, the native substrate and the
purified enzyme): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the value of the
stated coefficient itself (it is the paper's account of the reaction; the strength scale reads the measured link, and the agreement of the two is judged above); the pH and the temperature (the claim carries no condition, and the identity
block records the temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this method, decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? Moles of product per mole of a limiting reagent used up: an absolute dimensionless number, fixed by the chemistry of the reaction (a coefficient that is
  usually a small whole number), with each side needing its own calibration.
  Is there a reference range we would trust if the paper stated less? Partly: the coefficient of a known reaction type is a small whole number (1 or 2), so a stated ratio is read against that; but a
  ratio of two measurements has no single reference range the way a KD or a kcat does.
  What does an unstated control or calibration do to the number's meaning? An unstated completion or an unstated excess changes the number (a ratio read at an unfinished reaction is off by the share
  left), but the usual practice is to run to completion; an unidentified product or an unmatched endpoint makes the ratio uninterpretable; an unstated no-substrate control leaves open that the limiting
  reagent was used by an oxidase side activity, which is common for NAD(P)H enzymes.
  If we assume it is fine and are wrong, how badly does the score mislead? A wrong ratio reads as coupling that is not there or hides a real one: more than a KD (a magnitude only), about as much as an
  activity from a blank-less rate.
  Consistent with KD and with spectro_direct (0.85)? A little lower than the continuous rate, because this number needs two measurements to agree.
  default 0.80. matched_windows 0.70 (unmatched endpoints make the ratio uninterpretable). product_identity 0.70 (an unidentified product is the Bcd/Etf kind of error: the cofactor lost without the claimed
  product). stoichiometry 0.75 (an unstated coefficient, excess or regeneration leaves open that nothing was limiting). reporter_specificity 0.70 (side use of the limiting reagent is common and
  usually unstated). sampling_basis 0.90 (benign when unstated: triplicates are usual and a single dose is a legitimate design). The other sheet criteria take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_reaction_coupling_direction import select_coupling_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS, apply_support

VERSION = 'a105_coupling_limiting_reagent_converted_v1'
CRITERIA_MAP = {'matched_windows': ('same_reaction', 'completion_shown'), 'stoichiometry': ('reaction_coefficient', 'excess_of_other_reagents', 'no_regeneration'),
                'calibration_applicability': ('limiting_amount_verified', 'product_calibration'), 'product_identity': ('product_identity',), 'reporter_specificity': ('no_substrate_control',),
                'background_alternatives': ('no_enzyme_control',), 'attribution_supported': ('inactive_enzyme_control',), 'sampling_basis': ('replicates', 'titration_points'),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
REMAINING_FULL_PERCENT = 5.0  # EXPERT_REVIEW, owner to confirm: up to about 5 percent of the limiting reagent left is inside the ordinary error of an endpoint absorbance or peak (a few percent; a judgement, from memory, not verified); full agreement up to it.
REMAINING_ZERO_PERCENT = 50.0  # EXPERT_REVIEW, owner to confirm: with half of the limiting reagent left the product per limiting reagent added is half the product per limiting reagent used up (a factor 2): no completion, no agreement; the degree falls linearly in the share left from the full end to here, because the bias of the ratio is that share.
EXCESS_FULL_FOLD = 10.0  # EXPERT_REVIEW, owner to confirm: a ten-fold excess of the other reagent keeps it within about 10 percent over the run (pseudo-first-order practice, Cornish-Bowden and Segel, from memory, not verified); full agreement from it.
EXCESS_ZERO_FOLD = 1.0  # EXPERT_REVIEW, owner to confirm: equal amounts: nothing is in excess, both reagents are used up together and neither limits cleanly (no agreement); the degree falls from EXCESS_FULL_FOLD linearly in the share 1 / fold of the other reagent used up by the run.
EQUIVALENTS_FULL_FACTOR = 1.1  # EXPERT_REVIEW, owner to confirm: the measured equivalents per product within a factor 1.1 of the paper's own coefficient (about the combined error of the limiting amount and the product: 2 to 3 and 5 percent; a judgement, from memory, not verified); full agreement within it.
EQUIVALENTS_ZERO_FACTOR = 2.0  # EXPERT_REVIEW, owner to confirm: a factor 2 is the step to the next whole stoichiometric number (1 against 2 equivalents): a different reaction or a side use of the limiting reagent (no agreement); the degree falls from EQUIVALENTS_FULL_FACTOR linearly in the log of the factor, because deviations of a ratio are multiplicative.
MIN_TITRATION_POINTS = 5  # EXPERT_REVIEW, owner to confirm: about five points of a titration of the limiting reagent show the rise, the break and the plateau (a judgement, from memory, not verified); full agreement from it.
TITRATION_POINTS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: the titration curve has two parameters (the slope of the rise and the break), so two points are used up by the fit and leave no residual degree of freedom (degree 0, supported, never conflicting: a short titration is weaker evidence); between this and MIN_TITRATION_POINTS the degree rises linearly with the residual degrees of freedom (count - 2).
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The exact factor from each unit of the record's vocabulary to the anchor unit 'fraction' (FIXED_BY_DEFINITION: a percent is a hundredth; a mole per mole is a pure ratio).
UNIT_FACTORS = {'fraction': 1.0, 'percent': 1.0 / PERCENT_PER_FRACTION, 'mol_per_mol': 1.0}
# The record field whose stated value is each effect quantity (the productive fraction is its own field; the stoichiometric ratio is the yield over the limiting reagent).
STATED_FIELD = {'productive_fraction': 'productive_fraction', 'stoichiometric_ratio': 'yield_over_limiting_reagent'}
# The quantity_kind (QUANTITY_KINDS['reaction_coupling']) that names the kind of each effect quantity; literature_reaction_coupling_direction.COUPLING_QUANTITY_OF_KIND reads it back.
KIND_OF_QUANTITY = {'productive_fraction': 'productive_fraction', 'stoichiometric_ratio': 'stoichiometric_ratio'}
KIND_WITHOUT_EFFECT = 'productive_fraction'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'a_limiting_reagent_endpoint_has_no_matrix_recovery_measurement', 'attributed_signal': 'the_coupling_ratio_is_the_effect_not_an_attribution_fraction', 'total_signal': 'the_coupling_ratio_is_the_effect_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_limiting_reagent_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_limiting_reagent_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENT = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected'}   # read "coupled product formation detected" / "no product formed above the paper's own control or detection limit" for this class


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


def _judge_remaining(native):
    return _graded(native['remaining_refs'], (native['remaining_percent'], REMAINING_FULL_PERCENT, REMAINING_ZERO_PERCENT))


def _judge_excess(native):
    # the share of the other reagent that the run uses up is 1 / fold: a fold at or below 1 is at or beyond the zero end
    return _graded(native['excess_refs'], (1.0 / native['excess_fold'], 1.0 / EXCESS_FULL_FOLD, 1.0 / EXCESS_ZERO_FOLD))


def _judge_equivalents(native):
    return _graded(native['equivalents_refs'], (abs(math.log(native['equivalents_over_coefficient'])), math.log(EQUIVALENTS_FULL_FACTOR), math.log(EQUIVALENTS_ZERO_FACTOR)))


def _judge_titration(native):
    # a short titration only lowers the degree, never conflicts
    return _verdict('supported', native['titration_refs'], max(0.0, min(1.0, _share(native['titration_points'], MIN_TITRATION_POINTS, TITRATION_POINTS_ZERO))))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('completion_shown', 'remaining_recorded_for_the_sheet'): _judge_remaining, ('excess_of_other_reagents', 'excess_recorded_for_the_sheet'): _judge_excess,
          ('reaction_coefficient', 'equivalents_recorded_for_the_sheet'): _judge_equivalents, ('titration_points', 'titration_points_recorded_for_the_sheet'): _judge_titration,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _stated(native, quantity, ref):
    """The effect quantity as the paper states it, in the anchor unit 'fraction', or None when the field is not stated (its 'support' is the extraction's)."""
    operand = native['quantities'][STATED_FIELD[quantity]]
    if operand['status'] != 'point':
        return None
    return _operand(operand['value'] * UNIT_FACTORS[operand['unit']], 'fraction', 'coupling_limiting_reagent_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], STATED_FIELD[quantity], operand['support'])


def _derived(native, quantity, ref):
    """The effect quantity worked out by exact arithmetic from the measured equivalents per product e (origin 'derived'), or None when its inputs are not stated: the productive fraction is
    coefficient / e (needs the coefficient too); the stoichiometric ratio is 1 / e. Its support is the weakest of the stated inputs'."""
    equivalents = native['quantities']['limiting_reagent_per_product']
    coefficient = native['quantities']['stoichiometric_coefficient']
    if equivalents['status'] != 'point':
        return None
    if quantity == 'productive_fraction':
        if coefficient['status'] != 'point':
            return None
        value, members = coefficient['value'] / equivalents['value'], (coefficient, equivalents)
    else:
        value, members = 1.0 / equivalents['value'], (equivalents,)
    refs = list(dict.fromkeys(r for member in members for r in member['source_refs']))
    return _operand(value, 'fraction', 'coupling_limiting_reagent_' + quantity + '_from_equivalents:' + ref, refs, 'derived', 'limiting_reagent_per_product', max((m['support'] for m in members), key=SUPPORTS.index))


def _candidate(native, quantity, ref):
    stated = _stated(native, quantity, ref)
    return stated if stated is not None else _derived(native, quantity, ref)


def _spread_variance(graded, field):
    """Return (variance of the stated field in its anchor unit squared or None, reason or None, refs) of the spread of ``field``."""
    native = graded['native']
    spread = native['quantities'][field + '_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, field + '_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = spread['value'] * UNIT_FACTORS[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def _variance(graded, quantity, effect):
    """Return (variance in 'fraction_squared' or None, reason or None, refs, native component) of the effect. A stated effect carries its own field's spread; a derived one carries the spread of
    the equivalents per product through the slope of its formula: coefficient / e^2 for the productive fraction, 1 / e^2 for the ratio."""
    native = graded['native']
    if effect['origin'] != 'derived':
        field = STATED_FIELD[quantity]
        return (*_spread_variance(graded, field), field + '_spread')
    variance, reason, refs = _spread_variance(graded, 'limiting_reagent_per_product')
    if variance is None:
        return variance, reason, refs, 'limiting_reagent_per_product_spread'
    numerator = native['quantities']['stoichiometric_coefficient']['value'] if quantity == 'productive_fraction' else 1.0
    slope = numerator / native['quantities']['limiting_reagent_per_product']['value'] ** 2
    return slope * slope * variance, None, refs, 'limiting_reagent_per_product_spread'


def convert_coupling_limiting_reagent(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    candidates = {quantity: _candidate(native, quantity, ref) for quantity in STATED_FIELD}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in candidates.values()):
        null_components['effect'] = 'no_coupling_quantity_given_or_derivable_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_coupling_effect(candidates)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_QUANTITY[chosen], effect['support']
        variance, variance_reason, variance_refs, variance_component = _variance(graded, chosen, effect)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, 'fraction_squared', 'coupling_limiting_reagent_' + chosen + '_variance:' + ref, variance_refs, 'derived', variance_component)
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'reaction_coupling', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'coupling_limiting_reagent', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None and native['detected'] is not None:      # no coupling quantity: the paper's own statement of product formed above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['detected']], 'support_refs': list(native['detected_refs'])}
        result['direction_field_support'] = native['detected_support']
    return result
