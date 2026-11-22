"""Distribution_radio_tlc converter: turns the grader's result into what the A105 product_distribution sheet takes. DRAFT 2026-11-22 (owner to correct), built
from the shape of literature_spectro_direct_converter.py and, for a result stated in words, literature_spr_converter.py.

Hand-built, private to distribution_radio_tlc, deterministic. Input: the result of grade_distribution_radio_tlc. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'product_distribution'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for every
sheet component that a radiolabelled distribution cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: the share of the claimed product among the labelled products (product_fraction,
                  'fraction') or the ratio of the claimed product to one other species (product_fraction_ratio, 'dimensionless'). Both may be stated; the one used
                  is the best-determined, in the class order PRODUCT_DISTRIBUTION_EFFECT_ORDER (literature_product_distribution_direction.select_product_distribution_effect).
                  A stated share in percent is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION): the value is the paper's, only its unit spelling
                  changes. quantity_kind of the extraction names the kind of the effect (KIND_OF_QUANTITY), which the direction function reads. The effect is read FOR the
                  claimed product: the share is the share of the partner of the identity block, the ratio has the partner on top. The complement (one minus the share)
                  is never derived: the other species is another partner. This method states no equilibrium quantity (a radiolabelled lane after a time is an end point,
                  not an equilibrium), so the two equilibrium kinds of the class are not filled.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval and range -> not converted (they need their level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
recovery          the recovery of the applied radioactivity (lane_recovery), as a fraction, when it is stated; the sheet reads it as a diagnostic (recovery minus one).
Every other role stays null, with a reason (NULL_REASONS): attributed signal and total signal (the share is the effect; counting it again as an attribution
fraction would count it twice), condition test and reference, the assertion and alternative predictions.
qualitative_effect  only when NO share or ratio is stated: statement 'interaction_detected' (read "product detected": the passage says the claimed product was
                  found among the labelled products), 'interaction_not_detected' (read "product not detected": it says the product was not found) or
                  'interaction_not_stated', with the refs of the fact claimed_product_detected, the one fact the statement is derived from; direction_field_support is
                  that fact's quote support (None when not stated). A stated share or ratio fixes the direction by its graded strength; the statement is then not used. A
                  quantitative result never opposes; only the paper's own "not found" opposes. How little a bare statement counts (STATED_ONLY_STRENGTH) is the contract's;
                  it is not repeated here.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the enzyme preparation, immobilized_preparation_ref = None
and surface_ref = None (no immobilized enzyme, no electrode; the plate is not a surface reference), dataset_ref = the dataset.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
species_identity           species_assigned_with_standards
common_denominator         label_retained_by_all_products + shares_of_one_lane_total + lane_recovery_stated
response_factors           equal_label_per_molecule + detection_efficiency_matched
matrix_interference        spots_resolved + background_beside_smallest_band
calibration_applicability  within_linear_range_of_imager
background_alternatives    substrate_blank_lane
attribution_supported      inactive_enzyme_lane
sampling_basis             replicates
assertion_relevance        native_reaction
condition_scope            purified_enzyme
variance_correspondence    supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity, equilibrium_state) are not selected: equilibrium_state is optional for the two product kinds of the class
(literature_assay_grading._required_criteria) and this method states no equilibrium. The thresholds are judged here, not in the grader (it records facts only and hands
them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Each judgement is a researched value of THIS
method made gradual (SOP step 3): full agreement at the researched good value, falling linearly on the scale the physics of the method gives to zero at a researched
no-longer-meaningful value (never a step), unknown when the paper states nothing, never conflicting for a short count. A value at or beyond its zero end is conflicting (what
the paper itself shows against the standard). A sheet criterion that is supported carries the smallest degree of its members that have one. Quote support
(literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined status: any conflicting -> conflicting; else any
unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is not selected.

THE VALUES BELOW ARE A FIRST DRAFT FOR THE OWNER (2026-11-22): every number is EXPERT_REVIEW, owner to confirm, and every literature figure is from the drafter's memory of
radio-TLC practice, NOT web-verified and NOT checked against a method paper. The owner's questions are asked of each value (Q1 failure caught, Q2 general or lab-specific,
Q3 absolute or relative, Q4 how badly a wrong value misleads and whether the shape fits, Q5 consistency with the other assays).
------------------------------------------------------------------------------------------------------------------------------------------------------------------------
LANE_RECOVERY_FULL 0.9 -> LANE_RECOVERY_ZERO 0.5 (the counts of the whole lane over the counts applied), linear in the recovery.
  Q1 radioactivity that never reached a counted spot (label left at the origin, label lost in the solvent front, a volatile product or tritiated water that evaporated, label
  stuck to the plate) so that the shares are shares of only a part of the label. Q2 general: a closure of about 90 to 110 percent of the applied activity is the usual
  acceptance of a chromatographic radio-assay (radiochemical purity and mass-balance practice), from memory, not verified; a recovery above the full end is not judged
  (a high value is a counting matter that the spread already carries). Q3 relative to the paper's own applied counts, which is what the passage states. Q4 the physics gives the
  shape: if the unaccounted share u = 1 - recovery all belonged to the product, its share would change by up to u, so the worst-case error of a share is u and is linear in the
  recovery; the degree is linear in it between a worst-case error of 10 points (full) and 50 points (zero: half the label is unseen, and a share of what is seen can be anything).
  At or below the zero end the paper's own number shows the lane is mostly unaccounted for (conflicting). A closure is not an independent mass balance (the sheet's own wording);
  it only bounds the error of the share. Q5 the same idea as the other count and ratio curves: an error that grows with the departure.
BACKGROUND_FULL 0.1 -> BACKGROUND_ZERO 1.0 (the background over the counts of the smallest quantified species), linear in the ratio.
  Q1 a background (plate blank, cosmic and chemiluminescent signal, carry-over from the neighbouring lane) that inflates a small spot, so that a minor product's share is too large.
  Q2 arithmetic, not lab practice: counts of the smallest species s over a background b, an unsubtracted background raises it by exactly b / s, so the share of the smallest species
  (the one most often the claimed product) is off by that fraction in the worst case (the background wholly unsubtracted); a subtracted background leaves only its own uncertainty,
  which the paper's spread carries, so the worst case is the conservative reading. 0.1 (a tenth) is a ten percent worst-case error; 1.0 is a factor-of-two worst-case error (a spot
  no brighter than the background beside it is not quantified; the usual detection convention asks for a signal several times the background noise, from memory, not verified).
  Q3 relative to the paper's own smallest species, with both numbers stated. Q4 the error is proportional to the ratio, so the degree is linear in it (the shape fits). At or beyond the
  zero end the paper's own numbers show the smallest species is as small as the background (conflicting). Q5 the same worst-case-error idea as the lane recovery above.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a share from one experiment, whose preparation-to-preparation spread is unseen (the lanes of one plate from one reaction are technical repeats: they share the reaction). Q2 general
  (triplicate practice). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the standards, the label retained, the shares of one lane total, the equal label per molecule, the matched detection, the resolved spots, the linear range, the
no-enzyme lane, the inactive-enzyme lane, the native substrate, the purified enzyme, the background subtracted when no numbers are given): the paper's own statement decides; yes is
supported, no is conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the isotope and the readout (recorded as choices; a 3H share on a plate is
harder to count than a 32P one, which the detection-efficiency fact carries); the specific radioactivity of the substrate (it limits how small a product can be seen, which the
background ratio carries); the Rf values (the standards decide the assignment, not the number).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this method, decided 2026-11-22,
owner to confirm:
  What does it measure; absolute or relative? The share of the label among the separated species of one lane: a RELATIVE readout within the lane (it needs no calibration of the
  absolute counts), absolute as a share of the labelled products once the label per molecule and the detection are equal.
  Is there a reference range we would trust if the paper stated less (as for KD)? No for the share itself (it is whatever the reaction gives); yes for the practice: a labelled
  substrate with a co-run standard is the usual way a product is named on a plate.
  What does an unstated control or calibration do to what the number means? An unstated blank is the dominant false product (a radiochemical impurity of the labelled substrate is
  often a few percent and runs where a product runs), so it can turn background into a "product" for a minor species; an unstated standard leaves a spot named by position or by earlier
  work (a wrong assignment names the wrong product, the claim itself); an unstated equal label or detection is benign for one isotope on one plate and misleading for tritium or for a
  product that lost part of the label.
  If we assume it is fine and are wrong, how badly does the score mislead? A mis-assigned spot or a counted impurity gives the wrong product a share (the direction of the claim is wrong
  for a minor product); a response bias gives the right product a wrong size. Less severe than a pull-down band, more than a KD.
  Consistent with KD? The default 0.80 is under the KD anchor 0.90 and under spectro_direct 0.85 (a share has more ways to be wrong than a rate of a defined substrate).
  default 0.80. species_identity 0.70 (position on a plate is the only name; unsaid standards are a real gap). background_alternatives 0.70 (the blank and the zero-time lane separate
  an impurity of the labelled substrate from a product). response_factors 0.85 and calibration_applicability 0.85 and sampling_basis 0.85 (benign when unstated: counts of one isotope
  on one plate are comparable, the linear range is usually kept, triplicates are usual). The other criteria take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_product_distribution_direction import select_product_distribution_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_distribution_radio_tlc_converted_v1'
CRITERIA_MAP = {'species_identity': ('species_assigned_with_standards',),
                'common_denominator': ('label_retained_by_all_products', 'shares_of_one_lane_total', 'lane_recovery_stated'),
                'response_factors': ('equal_label_per_molecule', 'detection_efficiency_matched'),
                'matrix_interference': ('spots_resolved', 'background_beside_smallest_band'),
                'calibration_applicability': ('within_linear_range_of_imager',),
                'background_alternatives': ('substrate_blank_lane',),
                'attribution_supported': ('inactive_enzyme_lane',),
                'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_reaction',),
                'condition_scope': ('purified_enzyme',)}
LANE_RECOVERY_FULL = 0.9  # EXPERT_REVIEW, owner to confirm: recovery of the applied radioactivity in the counted spots of the lane taken as a full closure (about 90 to 110 percent is the usual acceptance of a chromatographic radio-assay, from memory, not verified); the worst-case error of a share is the unaccounted share, 10 points here; full agreement from it.
LANE_RECOVERY_ZERO = 0.5  # EXPERT_REVIEW, owner to confirm: half the applied radioactivity unaccounted for: the worst-case error of a share is 50 points, a share of what is seen can be anything (no agreement; conflicting at or below it); the degree falls linearly in the recovery from LANE_RECOVERY_FULL, because the worst-case error is the unaccounted share.
BACKGROUND_FULL = 0.1  # EXPERT_REVIEW, owner to confirm: background over the counts of the smallest quantified species at a tenth: an unsubtracted background raises that species by exactly this fraction (worst case 10 percent); full agreement up to it.
BACKGROUND_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: background as large as the smallest species: the worst-case error is a factor of two and a spot no brighter than its background is not quantified (no agreement; conflicting at or beyond it); the degree falls linearly in the ratio from BACKGROUND_FULL, because the worst-case error is the ratio.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: a percent is a hundredth of a fraction; a ratio has no unit to convert; the stated number is the paper's.
    'product_fraction': ('fraction', {'fraction': 1.0, 'percent': 0.01}),
    'product_fraction_ratio': ('dimensionless', {'dimensionless': 1.0}),
}
# The quantity_kind (QUANTITY_KINDS['product_distribution']) that names the kind of each effect quantity; literature_product_distribution_direction reads it back.
KIND_OF_QUANTITY = {'product_fraction': 'product_fraction', 'product_fraction_ratio': 'product_fraction_ratio'}
KIND_WITHOUT_EFFECT = 'product_fraction'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'attributed_signal': 'a_product_share_is_the_effect_not_an_attribution_fraction', 'total_signal': 'a_product_share_is_the_effect_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_distribution_radio_tlc_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_distribution_radio_tlc_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "product detected" / "product not detected" / "product not stated" for this class


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


def _judge_lane_recovery(native):
    return _graded(native['lane_recovery_refs'], (native['lane_recovery_fraction'], LANE_RECOVERY_FULL, LANE_RECOVERY_ZERO))


def _judge_background(native):
    return _graded(native['background_refs'], (native['background_over_smallest_species'], BACKGROUND_FULL, BACKGROUND_ZERO))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('lane_recovery_stated', 'lane_recovery_recorded_for_the_sheet'): _judge_lane_recovery,
          ('background_beside_smallest_band', 'background_recorded_for_the_sheet'): _judge_background,
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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'distribution_radio_tlc_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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
    return None, kind + '_not_converted', []


def convert_distribution_radio_tlc(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {quantity: _stated_effect(native, quantity, ref) for quantity in UNIT_FACTORS}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_product_share_or_ratio_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_product_distribution_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_QUANTITY[chosen], effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'distribution_radio_tlc_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
    if native['lane_recovery_fraction'] is None:
        null_components['recovery'] = 'lane_recovery_not_given'
    else:
        recovery = native['quantities']['lane_recovery']
        quantities['recovery'] = _operand(native['lane_recovery_fraction'], 'fraction', 'distribution_radio_tlc_lane_recovery:' + ref, recovery['source_refs'], recovery['origin'], 'lane_recovery')
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
    result = {'version': VERSION, 'experiment_type': 'distribution_radio_tlc', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no stated share or ratio: the paper's own yes/no result stands, scored like any stated result (literature_direction, the qualitative path)
        result['qualitative_effect'] = {'statement': STATEMENTS[native['product']], 'support_refs': list(native['product_refs'])}
        if native['product'] is not None:
            result['direction_field_support'] = native['product_support']      # the support class of the fact claimed_product_detected, the one field the statement is derived from
    return result
