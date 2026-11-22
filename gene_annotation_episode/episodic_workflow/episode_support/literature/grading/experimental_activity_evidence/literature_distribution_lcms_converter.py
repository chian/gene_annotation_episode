"""Distribution_lcms converter: turns the grader's result into what the A105 product_distribution sheet takes. DRAFT 2026-11-22, owner to confirm.

Hand-built, private to distribution_lcms, deterministic. Input: the result of grade_distribution_lcms. Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'product_distribution'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for every sheet component that an LC-MS product
profile cannot honestly fill, the reason it stays null. Built on the structure of literature_spectro_direct_converter.py (SOP steps 1 to 8); it uses the product_distribution
class core (docs/axis_restructure_20261117/A105_PRODUCT_DISTRIBUTION_INVENTORY.md) and not the activity class core.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: the share of the claimed product among the products (fraction) or the ratio of the claimed product to
                  another product (dimensionless). Both may be stated; the one used is the best-determined, in the class order PRODUCT_DISTRIBUTION_EFFECT_ORDER
                  (literature_product_distribution_direction.select_product_distribution_effect; the reason is in the contract): the share first, because it names its own product and
                  denominator and needs no choice of numerator. A share stated in percent is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION): the value is the paper's,
                  only its unit spelling changes. A ratio is never turned into a share and a share never into a ratio (that would be exact only for two species). A share stated as 0 is not an
                  effect operand (a zero is never an effect): it is the paper's own statement that the product was not found (see qualitative_effect). quantity_kind of the extraction
                  names the kind of the effect (KIND_OF_QUANTITY), which the direction function reads. The equilibrium kinds are not filled by this type.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it: standard_error -> se^2; standard_deviation -> sd^2 / n and
                  only when the replicates criterion is supported; confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
recovery          the total recovery (closure) as a fraction (a percent times its exact factor), only when the passage states it. It is the sheet's diagnostic and is not a validity
                  multiplier; a share normalised to 100 percent is not a recovery.
Every other role stays null, with a reason (NULL_REASONS): attributed signal and total signal (the quantity kind already is the share, so it stays in the effect and is not counted
twice), condition test and reference, the assertion and alternative predictions.
Preparations: the enzyme preparation is analyte_preparation_ref; no type of this class has an immobilized enzyme, a surface or an electrode, so immobilized_preparation_ref and surface_ref
are None (the record carries them as None and they are handed on as they are).
qualitative_effect  only when NO effect is stated: statement 'interaction_detected' (read "product detected": the claimed product is among the products) or 'interaction_not_detected'
                  (read "product not detected"), with the refs of the field that states it: a product share stated as 0 gives not detected, with that share's own quote and support;
                  else the fact claimed_product_detected gives its own answer, quote and support. direction_field_support is then the support of that one field. A stated effect fixes the
                  direction and the statement is then not used. Nothing stated: no qualitative_effect (the direction is unknown). A bare statement counts the type's QUALITATIVE_LOG_RATIO
                  times the contract's stated_strength (the contract's rule; not done here).

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
species_identity          species_assigned_with_standards
response_factors          calibration_per_species
common_denominator        shared_denominator_and_closure
matrix_interference       matrix_effect_addressed + sample_handling
calibration_applicability calibration_range_covers_signals
background_alternatives   no_enzyme_reaction
attribution_supported     inactive_enzyme_reaction
sampling_basis            replicates
assertion_relevance       native_reaction
condition_scope           purified_enzyme
variance_correspondence   supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity, equilibrium_state) are not selected: measurement_identity is not selected by a method criterion (as for the activity
types) and equilibrium_state is optional for the two product_* kinds this type fills (literature_assay_grading._required_criteria).
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such criterion and
reason to its judgement). Each judgement is a researched value of THIS method made gradual (SOP step 3): full agreement at the researched good value, falling smoothly to zero at a
researched no-longer-meaningful value on the scale the physics of the method gives (never a step), unknown when the paper states nothing, never conflicting for a short count. A value at
or beyond its zero end is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported carries the smallest degree of its members that have one.
Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined status: any conflicting -> conflicting; else any
unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is not selected.

How the class decisions apply here (2026-11-22, owner to confirm). Direction and strength of a stated share or ratio: literature_product_distribution_direction (the position on the
quantity's own log scale between the class ends, lowered by the stated spread; a LARGER share is stronger; a quantitative result never opposes). Response factors, the shared denominator,
the matrix effect, the controls and the replicates lower the WEIGHT only and never the direction.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads and whether the shape
fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
LOQ_FULL_MULTIPLE 10 -> LOQ_ZERO_MULTIPLE 1, the product concentration over the lower limit of quantification, judged on the relative noise error 1 / x.
  Q1 a product amount at or near the limit of quantification is quantified with the poorest accuracy the method accepts, so a share built on it is poorly determined (and a trace
  product is the case where a contaminant, carry-over or spontaneous peak is easiest to mistake for the enzyme's product). Q2 general guideline practice for LC-MS/MS quantification
  (from memory: the FDA bioanalytical method validation guidance 2018 and the EMA guideline 2011 accept accuracy within 20 percent and precision at most 20 percent at the lower limit of
  quantification and 15 percent elsewhere; ICH Q2 defines the limit of quantification at a signal-to-noise ratio of about 10); they are rules for drug assays, used here by analogy for a
  product profile. Q3 relative to the paper's own limit, which the grader records together with the paper's own concentration; right. Q4 the noise part of the relative error of an
  ion-signal measurement falls about as the inverse of the signal (about 20 percent at the limit, about 2 percent at ten times the limit); the degree is linear in that error between the two
  ends, (1 - 1/x) / (1 - 1/10): 0 at the limit, 0.56 at twice, 0.74 at three times, 1 from ten times. It is steep just above the limit and flat above ten times, which is how the error falls.
  A concentration at or below the paper's own limit is conflicting: the paper itself states a number it cannot quantify. Q5 the same idea as the other ramps built on a bias or error
  that grows with the departure from the researched value (the spectro_direct consumed and absorbance curves).
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a product profile from one reaction, whose reaction-to-reaction spread (enzyme preparation, quench timing, injection) is unseen. Q2 general (triplicate practice; validation guidance
  uses at least three or five replicates per level, from memory). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared
  replicate rule (square root of n over the full-credit number).
Facts with no number (the standards, the per-species calibration, the shared denominator, the matrix effect, the sample handling, the calibration range when no numbers are given, the controls,
the native substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to soften.
NOT judged, and why: the total recovery (a diagnostic of the sheet, not a validity multiplier, and a share normalised to 100 percent can sum to 100 whatever the recovery); the ionisation mode,
the fraction basis and the spread kind (plain choices kept for the reviewer; a choice holds no span after the merge, and what the basis means for the share is carried by the facts of calibration);
the peak resolution of isomers (not collected: papers rarely state it, and a quote must say it); the pH and the temperature (the claim carries no condition, and the identity block records them).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this method, decided 2026-11-22,
owner to confirm:
  What does it measure; absolute or relative? The ion signal of each separated species, read as a share of the summed signal: RELATIVE unless each species is calibrated on its own
  (an authentic standard with its own curve, or an isotope-labelled internal standard); the ionisation efficiency differs between species, sometimes by orders of magnitude, and the matrix
  changes it again, so an ion-signal share is not a molar share.
  Is there a reference range we would trust if the paper stated less (as for KD)? No for the size of a share: there is no general range of what share a product has. Yes for the presence
  of a product: a mass and a retention time are specific, so a detected product is usually really there.
  What does an unstated control or calibration do to what the number means? An unstated per-species calibration is the dominant gap: the share can be off by a multiple, not by a few
  percent (weight 0.60). An unstated ion-suppression check is common and changes the signal by tens of percent (0.65). An unstated no-enzyme blank matters more than for an absolute
  rate because the method is so sensitive that a spontaneous product or a contaminant ion is seen (0.70). An unstated calibration range or limit of quantification and unstated
  replicates are usual practice and change the precision, not the meaning (0.80 and 0.90).
  If we assume it is fine and are wrong, how badly does the score mislead? The direction (the product is made) mostly survives, because the species is identified by mass; the size of its
  share can be badly off. Less severe than a pull-down band (a pure artefact), more than a KD (a magnitude only).
  Consistent with KD? The default 0.75 is well under the KD anchor 0.90 and under the activity types (0.85), whose rate is absolute by construction; level with the other relative readouts.
  default 0.75. response_factors 0.60. matrix_interference 0.65. background_alternatives 0.70. calibration_applicability 0.80. sampling_basis 0.90. species_identity, common_denominator,
  attribution_supported, assertion_relevance and condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_product_distribution_direction import select_product_distribution_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_distribution_lcms_converted_v1'
CRITERIA_MAP = {'species_identity': ('species_assigned_with_standards',), 'response_factors': ('calibration_per_species',), 'common_denominator': ('shared_denominator_and_closure',),
                'matrix_interference': ('matrix_effect_addressed', 'sample_handling'), 'calibration_applicability': ('calibration_range_covers_signals',),
                'background_alternatives': ('no_enzyme_reaction',), 'attribution_supported': ('inactive_enzyme_reaction',), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
LOQ_FULL_MULTIPLE = 10.0  # EXPERT_REVIEW, owner to confirm: the product concentration at ten times the lower limit of quantification has a noise error of about a tenth of the 20 percent accepted at the limit (FDA 2018 and EMA 2011 bioanalytical guidance, from memory, not verified; ICH Q2 puts the limit at a signal-to-noise ratio of about 10); full agreement from it.
LOQ_ZERO_MULTIPLE = 1.0  # EXPERT_REVIEW, owner to confirm: the product concentration at or below the paper's own limit of quantification is a number the method cannot quantify (no agreement, conflicting); the degree falls from LOQ_FULL_MULTIPLE linearly in the relative noise error 1 / x (the noise part of the error of an ion signal falls about as the inverse of the signal), not in the log.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate reactions; full agreement from it (triplicate practice; validation guidance asks for three to five replicates per level, from memory, not verified). Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent reactions falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
FRACTION_PER_UNIT = {'fraction': 1.0, 'percent': 0.01}  # FIXED_BY_DEFINITION: a percent is a hundredth; the stated number is the paper's.
UNIT_FACTORS = {
    'product_fraction': ('fraction', FRACTION_PER_UNIT),
    'product_fraction_ratio': ('dimensionless', {'dimensionless': 1.0}),
}
# The quantity_kind (QUANTITY_KINDS['product_distribution']) that names the kind of each effect quantity; literature_product_distribution_direction reads it back.
KIND_OF_QUANTITY = {'product_fraction': 'product_fraction', 'product_fraction_ratio': 'product_fraction_ratio'}
KIND_WITHOUT_EFFECT = 'product_fraction'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'attributed_signal': 'a_product_share_is_the_effect_and_is_not_counted_twice_as_an_attribution_fraction', 'total_signal': 'a_product_share_is_the_effect_and_is_not_counted_twice_as_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_distribution_lcms_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_distribution_lcms_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENT = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected'}   # read "product detected" / "product not detected" for this class


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


def _judge_limit_of_quantification(native):
    # the relative noise error of an ion signal goes as 1 / x, x the product concentration over the limit: judged linearly in that error between the two researched ends
    return _graded(native['loq_refs'], (1.0 / native['product_over_loq'], 1.0 / LOQ_FULL_MULTIPLE, 1.0 / LOQ_ZERO_MULTIPLE))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('calibration_range_covers_signals', 'concentration_over_limit_recorded_for_the_sheet'): _judge_limit_of_quantification,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _stated_effect(native, quantity, ref):
    """The stated quantity as an effect operand in its anchor unit, or None when it is not stated as a positive point value (a zero share is not an effect; its 'support' is the extraction's)."""
    operand = native['quantities'][quantity]
    if operand['status'] != 'point' or operand['value'] <= 0:
        return None
    unit, factors = UNIT_FACTORS[quantity]
    return _operand(operand['value'] * factors[operand['unit']], unit, 'distribution_lcms_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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


def convert_distribution_lcms(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {quantity: _stated_effect(native, quantity, ref) for quantity in UNIT_FACTORS}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_product_share_or_ratio_given_as_a_positive_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_product_distribution_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_QUANTITY[chosen], effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'distribution_lcms_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
    recovery = native['quantities']['total_recovery']
    if recovery['status'] == 'point':
        quantities['recovery'] = _operand(recovery['value'] * FRACTION_PER_UNIT[recovery['unit']], 'fraction', 'distribution_lcms_total_recovery:' + ref, recovery['source_refs'], recovery['origin'], 'total_recovery')
    else:
        null_components['recovery'] = 'total_recovery_not_given'
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'product_distribution', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'distribution_lcms', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no stated positive share or ratio: the paper's own statement of the product (a share of 0, or the fact claimed_product_detected) fixes the direction
        share = native['quantities']['product_fraction']
        if share['status'] == 'point' and share['value'] == 0:
            result['qualitative_effect'] = {'statement': STATEMENT['not_detected'], 'support_refs': list(share['source_refs'])}
            result['direction_field_support'] = share['support']
        elif native['product'] is not None:
            result['qualitative_effect'] = {'statement': STATEMENT[native['product']], 'support_refs': list(native['product_refs'])}
            result['direction_field_support'] = native['product_support']
    return result
