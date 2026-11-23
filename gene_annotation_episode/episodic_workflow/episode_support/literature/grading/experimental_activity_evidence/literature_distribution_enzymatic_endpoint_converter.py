"""Distribution_enzymatic_endpoint converter: turns the grader's result into what the A105 product_distribution sheet takes. DRAFT (2026-11-22), owner to correct.

Hand-built, private to distribution_enzymatic_endpoint, deterministic. Input: the result of grade_distribution_enzymatic_endpoint. Output: the sheet's input
(the 'extraction' grade_assay takes, with assay_type 'product_distribution'), the sheet itself (grade_assay run on it), the dependence keys the merger needs,
and for every sheet component that an end-point determination cannot honestly fill, the reason it stays null. Modelled on literature_spectro_direct_converter.py;
the class core is the product_distribution class's (literature_product_distribution_direction.py, A105_PRODUCT_DISTRIBUTION_INVENTORY.md), not the activity class's.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its kind (PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS): the share of the claimed product (product_fraction,
                  fraction), the ratio of the claimed product to another species (product_fraction_ratio, dimensionless), its share at equilibrium
                  (equilibrium_fraction) or the equilibrium ratio (equilibrium_ratio). Several may be stated; the one used is the best-determined, in the class order
                  PRODUCT_DISTRIBUTION_EFFECT_ORDER (literature_product_distribution_direction.select_product_distribution_effect). A stated value in another unit of
                  the record's vocabulary is turned by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION: a percent is a hundredth): the value is the paper's, only
                  its unit spelling changes. The share of another species is never derived as one minus the stated share: the other species is a different partner.
                  quantity_kind of the extraction names the kind of the effect (KIND_OF_QUANTITY), which the direction function reads.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval and range -> not converted (a confidence interval needs its level and degrees of freedom, a range is not a spread of the mean).
                  Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
recovery          the stated closure of the analyses (total_recovery) as a fraction (exact factor 0.01 for a percent), when it is stated; otherwise null.
Every other role stays null, with a reason (NULL_REASONS): attributed signal/total signal (the share is the effect itself, kept once), condition test/reference, the
assertion and alternative predictions.
qualitative_effect  only when NO effect is filled: the paper's own statement whether the enzymatic analysis found the claimed product. statement
                  'interaction_detected' (read "product detected"), 'interaction_not_detected' (read "product not detected") or 'interaction_not_stated', with the refs
                  of the fact claimed_product_detected that states it; direction_field_support is the quote support of that one fact (None when not stated). A stated
                  effect fixes the direction; the statement is then not used. A result stated in words alone counts less than a measured one: the contract's
                  stated_strength does that, nothing here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
species_identity          analysis_enzyme_specificity (the species are identified by the specificity of their own analysis enzymes)
response_factors          standard_curve_per_species (each species is in molar units by its own calibration; there is no detector response to correct)
common_denominator        denominator_and_coverage + closure (a species with no assay is missing from the denominator; the recovery shows how much is missing)
calibration_applicability analysis_run_to_completion + signals_inside_standard_curve + reporter_absorbance_range
matrix_interference       cross_reactivity + first_enzyme_quenched (another species read by the analysis enzyme; the first enzyme still working in the analysis)
background_alternatives   reagent_blank + no_enzyme_sample + products_stable_until_analysis
attribution_supported     inactive_enzyme_sample
equilibrium_state         stable_composition (required by the sheet only for the two equilibrium kinds)
sampling_basis            replicates
assertion_relevance       native_reaction
condition_scope           purified_enzyme
variance_correspondence   supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity: not selected by a method criterion) are not selected.
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Each judgement is a researched value of THIS assay made gradual (SOP step 3): full agreement at the researched good value, falling
smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the assay gives (never a step), unknown when the paper states nothing, never
conflicting for a short count. A value at or beyond the zero end of a ramp that the paper's own numbers fix (a cross-reactivity, a recovery, an absorbance) is
conflicting (what the paper itself shows against the standard). A sheet criterion that is supported carries the smallest degree of its members that have one. Quote support
(literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined status: any conflicting -> conflicting; else any
unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is not selected.

How the class decisions apply here (owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref; immobilized_preparation_ref and surface_ref stay None
(no type of this class has an immobilized enzyme, a surface or an electrode). Qualitative statements keep the existing vocabulary. Direction and strength of a stated share or
ratio: literature_product_distribution_direction (larger is stronger, a quantitative result never opposes); controls, blanks, the denominator, the closure, the equilibrium
evidence and the rest lower the WEIGHT only. The class is not pooled (the effect is one of four quantities in two units).

THE VALUES BELOW ARE A FIRST DRAFT FOR THE OWNER (2026-11-22): every number is EXPERT_REVIEW, owner to confirm, and every literature statement is from the drafter's memory of
the method literature (Bergmeyer, Methods of Enzymatic Analysis; the instrument and validation guidelines), NOT web-verified and NOT checked against a method paper; verify
before relying on any of them. The owner's questions are asked of each value (Q1 failure caught, Q2 general or lab-specific, Q3 absolute or relative, Q4 how badly a wrong
value misleads and whether the shape fits, Q5 consistency with the other assays).
-----------------------------------------------------------------------------------------------------------------------------------
CROSS_REACTIVITY_FULL_PERCENT 1 -> CROSS_REACTIVITY_ZERO_PERCENT 10 (cross_reactivity), judged linearly in the log of the percent.
  Q1 the analysis enzyme of one species also reads another species, so the reading is the species plus a share of its neighbour and the share is wrong (hexokinase on glucose
  and fructose, a dehydrogenase on a second alcohol or hydroxy acid are the classical cases). Q2 general: specificity of the analysis enzyme is the whole point of an enzymatic
  analysis (Bergmeyer; from memory), and a response of about 1 percent of the response to its own species is usually described as specific. Q3 relative to the analysis enzyme's own
  response, which the passage states itself; right. Q4 the error of a reading is the cross-reactivity c times the amount of the neighbour, so for a species at a share s beside a
  neighbour at 1 - s the relative error is c (1 - s) / s: at c = 1 percent it is 1 percent for equal shares and 9 percent for a species at a tenth, which is where the class's own noise end
  (one percent) and strong end (nine tenths) lie, so full agreement is the class's noise end; at c = 10 percent (a ninth) a species at a tenth of its neighbour is read almost twice over (an error of 90 percent)
  (no agreement, conflicting: the paper itself shows the analysis does not isolate the species). The error is proportional to c and c runs over one decade between the ends,
  so the degree falls linearly in log c. Q5 a log-ratio ramp like the other ratio judgements of the assays.
RECOVERY_FULL_DEVIATION_PERCENT 5 -> RECOVERY_ZERO_DEVIATION_PERCENT 30 (closure), judged linearly in the deviation of the recovery from 100 percent.
  Q1 the species the analyses found do not add up to what the reaction started with, so a species is missing from the denominator (no assay for it, loss on standing, a side
  reaction) or a species is over-read (cross-reaction), and the shares refer to a part of the mixture. A closure is not an independent mass balance (the sheet's own wording);
  it shows how much the denominator covers. Q2 general: the analyses of an enzymatic end-point method are accurate to a few percent each (recoveries of 95 to 105 percent are the
  usual acceptance of enzymatic analyses and of ICH Q2 accuracy for an assay, from memory), and the sum of several determinations has the sum of their errors, so 5 percent
  is full agreement. Q3 relative to the paper's own starting amount, which it states. Q4 the deviation is an additive share of the material that is missing or over-counted, so the
  degree is linear in it; at 30 percent (about a third unaccounted for, or over-counted) the denominator covers a minority of what happened (no agreement, conflicting). A
  recovery above 100 percent is judged by the same deviation: an over-read is as damaging to a share as a missing species. Q5 an additive ramp like the proportion ramps of the
  imaging assays; no other assay judges a closure.
ABSORBANCE_FULL 1.0 -> ABSORBANCE_ZERO 3.0 (reporter_absorbance_range), STRAY_LIGHT 0.01, judged on the bias of the apparent absorbance.
  Q1 Beer-Lambert fails at high absorbance: stray light puts a floor under the transmitted intensity, the apparent absorbance bends over and the amount read from NAD(P)H at 340 nm
  (or a dye) is underestimated, most for the species with the most reporter. Q2 general: keep the absorbance of an end-point analysis below about 1 (photometry texts and the
  recommendation to dilute a sample that gives a larger change, from memory); a stray light of 1 percent is the conservative end of the instruments in use (a good UV-visible
  spectrophotometer has 0.1 percent or less, a plate reader more); instrument-specific. Q3 absolute (absorbance units), and the passage states it. Q4 the apparent absorbance is
  -log10((10^-A + s) / (1 + s)), so the underestimate is about 4 percent at A = 1, 15 percent at 2, 35 percent at 3; the degree is linear in that bias between the two ends; at or
  beyond A = 3 a third of the signal is lost (conflicting). A low absorbance is not judged: the paper's own spread already carries it. Q5 the same bias shape as the absorbance judgement
  of the direct spectrophotometric assay; the bias here shifts each species' share by its own amount, so it is a weight question, never a direction.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a distribution from one reaction, whose reaction-to-reaction spread is unseen (several analyses of one sample are technical and do not count). Q2 general (triplicate practice).
  Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the specificity of the analysis enzymes, the standards of each species, the readings inside the standards, the completion of the analysis, the quench of the
first enzyme, the reagent blank, the no-enzyme and inactive-enzyme samples, the stability of the species until the analysis, the shared denominator and the coverage of the species by
assays, the equilibrium evidence, the native substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no
researched value to soften. NOT judged, and why: the reporter signal (recorded; the physics is the same for each reporter and the absorbance range judges the absorbing ones); the pH and the
temperature (the claim carries no condition, and the identity block records the temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this assay, decided 2026-11-22,
owner to confirm:
  What does it measure; absolute or relative? The concentration of each species, in molar units, by its own specific analysis against its own standards, and the share or ratio
  of them: absolute, and molar by construction (there is no detector response to correct, unlike area percent).
  Is there a reference range we would trust if the paper stated less (as for KD)? Partly: enzymatic analyses are standardised and the stoichiometry of the analysis reaction is exact, so an
  unstated calibration is nearly always there; a share of a minor species is not trusted without the specificity and the closure, because the mixture has no second view.
  What does an unstated control or calibration do to what the number means? An unstated standard curve, completion or blank is benign typical practice (the method cannot give a
  concentration without them); an unstated specificity or quench is the method's own classical failure (an analysis enzyme that also reads the neighbour, a first enzyme that goes on
  working), and an unstated coverage hides a species that has no assay; an unstated no-enzyme sample leaves spontaneous interconversion (anomerisation, keto-enol, racemisation) open.
  If we assume it is fine and are wrong, how badly does the score mislead? The share is off by the cross-read amount or by the missing species: a wrong magnitude, and for a minor product
  next to a major one a false product (the direction is wrong); worse than a KD, less than a pull-down band.
  Consistent with KD? Below the KD anchor 0.90 and just under spectro_direct 0.85: several determinations must each be right and their errors add in a share.
  default 0.80. species_identity 0.75 and matrix_interference 0.70 (the specificity of the analysis enzymes is what this method rests on), common_denominator 0.75 (a species with no
  assay), background_alternatives 0.75 (spontaneous interconversion and loss on standing), equilibrium_state 0.65 (a single end point read as an equilibrium), calibration_applicability 0.85,
  response_factors 0.90, sampling_basis 0.90 (benign when unstated). attribution_supported, assertion_relevance, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_product_distribution_direction import select_product_distribution_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_distribution_enzymatic_endpoint_converted'
CRITERIA_MAP = {'species_identity': ('analysis_enzyme_specificity',), 'response_factors': ('standard_curve_per_species',), 'common_denominator': ('denominator_and_coverage', 'closure'),
                'calibration_applicability': ('analysis_run_to_completion', 'signals_inside_standard_curve', 'reporter_absorbance_range'),
                'matrix_interference': ('cross_reactivity', 'first_enzyme_quenched'), 'background_alternatives': ('reagent_blank', 'no_enzyme_sample', 'products_stable_until_analysis'),
                'attribution_supported': ('inactive_enzyme_sample',), 'equilibrium_state': ('stable_composition',), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
CROSS_REACTIVITY_FULL_PERCENT = 1.0  # EXPERT_REVIEW, owner to confirm: response of the analysis enzyme to another species at most 1 percent of its response to its own species (the class's own noise end of a share, from memory of the usual meaning of 'specific'); full agreement up to it.
CROSS_REACTIVITY_ZERO_PERCENT = 10.0  # EXPERT_REVIEW, owner to confirm: at 10 percent (a ninth, the class's strong end of a share 0.9 beside 0.1) a species at a tenth of its neighbour is read almost twice over, an error of 90 percent (no agreement); the degree falls from the full end linearly in the log of the percent, because the error is proportional to it and it runs over one decade.
RECOVERY_FULL_DEVIATION_PERCENT = 5.0  # EXPERT_REVIEW, owner to confirm: the analyses add up to within 5 percent of the starting amount (accuracy of enzymatic analyses and ICH Q2 recoveries of 95 to 105 percent, the errors of the several determinations add; from memory); full agreement up to it.
RECOVERY_ZERO_DEVIATION_PERCENT = 30.0  # EXPERT_REVIEW, owner to confirm: about a third of the material missing or over-counted: the denominator covers a minority of what happened (no agreement); the degree falls linearly in the deviation from 100 percent, an additive share of the material.
ABSORBANCE_FULL = 1.0  # EXPERT_REVIEW, owner to confirm: keep the absorbance of the reporter at most about 1 (photometry practice, from memory); full agreement up to it (the apparent-absorbance bias there is about 4 percent at 1 percent stray light).
ABSORBANCE_ZERO = 3.0  # EXPERT_REVIEW, owner to confirm: at an absorbance of 3 a stray light of 1 percent loses about a third of the signal (no agreement); the degree falls linearly in the bias of the apparent absorbance from the full end to here.
STRAY_LIGHT = 0.01  # EXPERT_REVIEW, owner to confirm: the fraction of stray light in the transmitted intensity; 1 percent is the conservative end of the spectrophotometers and plate readers in use (a good UV-visible instrument has 0.1 percent or less).
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (a percent is a hundredth); the stated number is the paper's.
    'product_fraction': ('fraction', {'fraction': 1.0, 'percent': 1.0 / PERCENT_PER_FRACTION}),
    'product_fraction_ratio': ('dimensionless', {'dimensionless': 1.0}),
    'equilibrium_fraction': ('fraction', {'fraction': 1.0, 'percent': 1.0 / PERCENT_PER_FRACTION}),
    'equilibrium_ratio': ('dimensionless', {'dimensionless': 1.0}),
}
# The quantity_kind (QUANTITY_KINDS['product_distribution']) that names the kind of each effect quantity; the four are named alike.
KIND_OF_QUANTITY = {'product_fraction': 'product_fraction', 'product_fraction_ratio': 'product_fraction_ratio', 'equilibrium_fraction': 'equilibrium_fraction', 'equilibrium_ratio': 'equilibrium_ratio'}
KIND_WITHOUT_EFFECT = 'product_fraction'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'attributed_signal': 'a_product_share_is_the_effect_itself_not_an_attribution_fraction', 'total_signal': 'a_product_share_is_the_effect_itself_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_distribution_enzymatic_endpoint_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_distribution_enzymatic_endpoint_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENT = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "product detected" / "product not detected" / "product not stated" for this class


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


def _apparent_absorbance_bias(absorbance):
    """The relative shortfall of the apparent absorbance, -log10((10^-A + s) / (1 + s)), against the true A, for the stray light STRAY_LIGHT."""
    return 1.0 - -math.log10((10.0 ** -absorbance + STRAY_LIGHT) / (1.0 + STRAY_LIGHT)) / absorbance


def _judge_cross_reactivity(native):
    return _graded(native['cross_reactivity_refs'], _log(native['cross_reactivity_percent'], CROSS_REACTIVITY_FULL_PERCENT, CROSS_REACTIVITY_ZERO_PERCENT))


def _judge_closure(native):
    # the deviation of the recovery from the whole, in percent (a recovery above 100 percent is as far from closing as the same amount below it)
    deviation = abs(native['total_recovery_percent'] - PERCENT_PER_FRACTION)
    return _graded(native['recovery_refs'], (deviation, RECOVERY_FULL_DEVIATION_PERCENT, RECOVERY_ZERO_DEVIATION_PERCENT))


def _judge_absorbance(native):
    return _graded(native['absorbance_refs'], (_apparent_absorbance_bias(native['absorbance_max']), _apparent_absorbance_bias(ABSORBANCE_FULL), _apparent_absorbance_bias(ABSORBANCE_ZERO)))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('cross_reactivity', 'cross_reactivity_recorded_for_the_sheet'): _judge_cross_reactivity, ('closure', 'recovery_recorded_for_the_sheet'): _judge_closure,
          ('reporter_absorbance_range', 'absorbance_recorded_for_the_sheet'): _judge_absorbance, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'distribution_enzymatic_endpoint_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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


def convert_distribution_enzymatic_endpoint(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {quantity: _stated_effect(native, quantity, ref) for quantity in UNIT_FACTORS}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_product_distribution_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_product_distribution_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_QUANTITY[chosen], effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'distribution_enzymatic_endpoint_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
    recovery = native['quantities']['total_recovery']
    if recovery['status'] == 'point':
        quantities['recovery'] = _operand(recovery['value'] / PERCENT_PER_FRACTION if recovery['unit'] == 'percent' else recovery['value'], 'fraction',
                                          'distribution_enzymatic_endpoint_total_recovery:' + ref, recovery['source_refs'], recovery['origin'], 'total_recovery')
    else:
        null_components['recovery'] = 'total_recovery_not_given'
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'product_distribution', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'distribution_enzymatic_endpoint', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no stated quantity: the paper's own statement of whether the analysis found the product fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['interaction']], 'support_refs': list(native['interaction_refs'])}
        result['direction_field_support'] = native['interaction_support']
    return result
