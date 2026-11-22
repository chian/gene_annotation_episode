"""Distribution_chiral converter: turns the grader's result into what the A105 product_distribution sheet takes (DRAFT 2026-11-22, owner to confirm).

Hand-built, private to distribution_chiral, deterministic. Input: the result of grade_distribution_chiral. Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'product_distribution'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for every sheet component that a chiral analysis cannot
honestly fill, the reason it stays null. Copied in shape from literature_spectro_direct_converter.py (the template built outside the binding class); the class core is the
product_distribution one (A105_PRODUCT_DISTRIBUTION_INVENTORY.md sections 2, 4 and 6), not the activity one.

Quantities filled
-----------------
effect            ONE stated quantity, the same stereochemical fact in up to three spellings, never three results. The order of preference is the excess, then the enantiomer
                  ratio, then the diastereomer ratio (EFFECT_ORDER). The effect is read FOR the claimed product: the record's partner is the major isomer the result is stated for.
                    enantiomeric_excess  ->  quantity_kind 'product_fraction', unit 'fraction': the major enantiomer's share of the two, f = (1 + ee) / 2 (exact for two enantiomers;
                                              a percent is a hundredth, FIXED_BY_DEFINITION). origin 'derived'.
                    enantiomer_ratio     ->  quantity_kind 'product_fraction_ratio', unit 'dimensionless': the major over the minor enantiomer as stated.
                    diastereomer_ratio   ->  the same kind and unit: the major over the minor diastereomer as stated.
                  The complement (the minor isomer's share) is NOT derived: the minor isomer is a different partner.
effect_variance   variance of that effect, in the unit of the effect squared, only when the passage's spread of THAT quantity allows it: standard_error -> se^2; standard_deviation ->
                  sd^2 / n and only when the replicates criterion is supported; confidence_interval -> not converted (needs its level and degrees of freedom). The spread of an excess
                  is turned into the spread of the share by the exact factor 1/2 (f = (1 + ee) / 2 is linear in ee). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery, attributed signal/total signal, condition test/reference, the assertion and alternative predictions.
qualitative_effect  only when NO effect is stated: the paper's own statement whether the stereo-isomeric product was formed (the fact product_detected): statement
                  'interaction_detected' (read "product detected"), 'interaction_not_detected' (read "product not detected") or 'interaction_not_stated', with the refs of the fact
                  that states it. direction_field_support is then the quote support of that one fact (None when it is not stated). A stated effect fixes the direction; the statement
                  is then not used. A result stated in words alone already counts less than a measured one (the contract's stated_strength); nothing is re-implemented here.
A quantitative result never opposes. Opposition comes only from the paper itself stating that the product was not detected.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
species_identity           racemic_standard_run + configuration_assigned_by_standard
response_factors           isomer_response_factors (not applicable for enantiomers: equal response by symmetry, so the sheet criterion is then not selected)
common_denominator         isomer_pair_one_measurement
background_alternatives    no_enzyme_control + product_configurational_stability
attribution_supported      inactive_enzyme_control
calibration_applicability  peak_resolution + minor_isomer_detection
sampling_basis             replicates
assertion_relevance        native_substrate
condition_scope            purified_enzyme
variance_correspondence    supported only when a variance was computed
Sheet criteria with no counterpart here are not selected: measurement_identity (selected by no method criterion), matrix_interference (a chiral analysis of a reaction mixture has
none of its own in this form), equilibrium_state (optional for the two product_* kinds; this type reports no equilibrium). The thresholds are judged here, not in the grader (it
records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Each judgement is a researched
value of THIS method made gradual (SOP step 3): full agreement at the researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the scale the
physics of the method gives (never a step), unknown when the paper states nothing, never conflicting for a short count. A value at or beyond its zero end is conflicting (what the
paper itself shows against the standard). A sheet criterion that is supported carries the smallest degree of its members that have one. Quote support
(literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is not selected.

How the class decisions apply here (DRAFT 2026-11-22, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None (no immobilized
enzyme, no electrode). Qualitative statements keep the existing vocabulary, read "product detected / not detected / not stated". Direction and strength of a stated share or ratio:
literature_product_distribution_direction (larger is stronger); controls, the racemic standard, resolution and the rest lower the WEIGHT only. An excess gives a share of at least 0.5
(a racemate is half the claimed enantiomer), so the share of the claimed isomer sits high on its scale for any ee; the excess itself, and how well it was measured, are carried by the weight.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads and whether the
shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
PEAK_RESOLUTION_FULL 1.5 -> PEAK_RESOLUTION_ZERO 0.5, judged linearly in the overlap of two equal Gaussian peaks, Q(2 Rs).
  Q1 two isomer peaks that run into each other, so that the area of one is counted in the other and the excess is misread (a pure single isomer reads as a mixture). Q2 general: a
  resolution of 1.5 is the usual definition of baseline separation (pharmacopoeial and chromatography texts, from memory), and the chiral-method practice is Rs of 1.5 or more for an excess
  measurement. Q3 absolute (a dimensionless number the paper states). Q4 the physics gives the shape: for two equal Gaussian peaks the area of one beyond the valley midpoint is Q(2 Rs), the
  upper tail of the normal curve at 2 Rs: 0.14 percent at Rs 1.5, 2.3 percent at 1.0, 6.7 percent at 0.75, 16 percent at 0.5. A pure single isomer would read about 99.7 percent ee at the
  full end and about 68 percent ee at the zero end, where the excess cannot be read (conflicting). The degree is linear in that overlap (an additive error of the share): 0.96 at Rs 1.2,
  0.86 at 1.0, 0.58 at 0.75. Real peaks tail and are unequal, so the real overlap is larger; the Gaussian case is the best case. Q5 the same idea as the other bias ramps (a bias that grows
  with the departure from the researched value, linear in the bias).
DETECTION_RATIO_FULL 3 -> DETECTION_RATIO_ZERO 1, the minor isomer's share over the detection limit, judged linearly in the LOG of the ratio.
  Q1 an excess so high that the minor isomer it implies is as small as the method can see, so the figure is a bound set by the limit and not a measurement ("99.8% ee" with a 0.5% limit).
  Q2 general: the limit of detection is a signal-to-noise of about 3 and the limit of quantification about 10 (ICH Q2(R1), from memory), a factor of about 3 apart; a minor isomer share
  quoted as a number should be at least about the quantification limit, so three times the detection limit is full agreement and a share at the limit itself is no measurement (conflicting).
  Q3 relative to the paper's own limit and its own minor share: right, and the grader records both. Q4 the relative error of a small peak rises as its signal-to-noise falls, so the scale is
  the log of the ratio (error proportional to 1 / ratio); a paper that states a quantification limit instead of a detection limit is judged conservatively. Q5 a log-ratio ramp like the
  other ratio judgements of the binding assays.
DETECTION_LIMIT_FULL 0.01 -> DETECTION_LIMIT_ZERO 0.10, the detection limit as a share of the total, judged linearly in the LOG of the limit, only when NO minor isomer is seen (an excess of 100 percent).
  Q1 a "single enantiomer" statement whose method could not have seen a few percent of the other isomer. Q2 practice: chiral HPLC and GC with UV or flame ionization detection usually quantify a
  minor enantiomer down to about 0.1 to 0.5 percent of the total (from memory); 1 percent is a generous full end. Q3 relative to the paper's own limit. Q4 with no minor isomer seen the excess is
  only bounded below by 1 - 2 L: L = 1 percent gives at least 98 percent ee, L = 10 percent only at least 80 percent, which is no longer a statement of high selectivity (conflicting at L = 10
  percent); the log scale because detection limits are quoted in orders of magnitude. Q5 the same log ramp as the ratio above.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 an excess from one reaction, whose preparation-to-preparation spread is unseen (enzyme activity, background racemization and work-up vary between reactions). Q2 general (triplicate
  practice; many chiral papers report one reaction, which this makes a partial, not a failed, credit). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the
  variance. Q5 exactly the shared replicate rule.
Facts with no number (the racemic standard, the configuration assignment, the response-factor check, the no-enzyme control, the inactive-enzyme control, the configurational stability, the native
substrate, the purified enzyme): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the size of
the excess itself (it is the effect: the direction function reads it on the share scale); the technique and the configuration (choices, recorded for the reviewer); the column, mobile phase and
temperature (the claim carries no condition).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this method, drafted 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The share of one stereo-isomer among two, read as the ratio of two peak areas of the same compound: a ratio, not an absolute amount, but one that needs
  no calibration for enantiomers (equal response by symmetry) and is well defined.
  Is there a reference range we would trust if the paper stated less (as for KD)? Largely yes: an excess measured by chiral chromatography with a racemic standard is among the most routine and
  reproducible numbers in enzymology and asymmetric catalysis; what a paper may omit are the standard and the resolution, which most real analyses did include.
  What does an unstated control or calibration do to what the number means? An unstated racemic standard leaves the peak assignment unproved (a wrong peak or a coeluting impurity gives a false
  excess); an unstated no-enzyme control leaves a chemical route open, but that route usually gives a racemate and so lowers the excess, it does not fake it; an unstated configurational stability
  hides racemization after the enzyme, which again lowers the excess; an unstated resolution or replicate count is benign in a published analysis.
  If we assume it is fine and are wrong, how badly does the score mislead? A wrong peak assignment (identity) misleads most; background and racemization mislead in the cautious direction.
  Consistent with KD? The default 0.85 is just under the KD anchor 0.90, level with spectro_direct; the criteria that guard the identity of the species and the enzyme's own contribution are lower.
  default 0.85. species_identity 0.75 (an unstated racemic standard is a real gap: the assignment of both peaks). background_alternatives 0.80 (a chemical background or racemization lowers the
  excess, so assuming it fine errs on the cautious side). attribution_supported 0.80 (the inactive-enzyme control, as in spectro_direct). common_denominator 0.90 (by construction two isomers
  over their sum), sampling_basis 0.90 (benign when unstated, as in spectro_direct). calibration_applicability, assertion_relevance, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_distribution_chiral_criteria import ISOMERS_IN_A_PAIR, PERCENT_PER_FRACTION
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_distribution_chiral_converted_v1'
CRITERIA_MAP = {'species_identity': ('racemic_standard_run', 'configuration_assigned_by_standard'), 'response_factors': ('isomer_response_factors',),
                'common_denominator': ('isomer_pair_one_measurement',), 'background_alternatives': ('no_enzyme_control', 'product_configurational_stability'),
                'attribution_supported': ('inactive_enzyme_control',), 'calibration_applicability': ('peak_resolution', 'minor_isomer_detection'),
                'sampling_basis': ('replicates',), 'assertion_relevance': ('native_substrate',), 'condition_scope': ('purified_enzyme',)}
PEAK_RESOLUTION_FULL = 1.5  # EXPERT_REVIEW, owner to confirm: Rs 1.5 is baseline separation of two peaks (chromatography texts, from memory, not verified): two equal Gaussian peaks overlap by 0.14 percent; full agreement from it.
PEAK_RESOLUTION_ZERO = 0.5  # EXPERT_REVIEW, owner to confirm: at Rs 0.5 each of two equal Gaussian peaks puts 16 percent of its area on the wrong side of the valley, so a pure single isomer would read about 68 percent ee (no agreement); the degree falls linearly in the overlap Q(2 Rs) from the full end to here (the Gaussian case is the best case; real peaks tail).
DETECTION_RATIO_FULL = 3.0  # EXPERT_REVIEW, owner to confirm: the minor isomer's share should be at least about three times the detection limit (ICH Q2(R1): limit of quantification about 10 over noise against about 3 for detection, from memory, not verified); full agreement from it.
DETECTION_RATIO_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: a minor share at the detection limit itself is a trace, not a measurement, so the excess is a bound set by the limit (no agreement); the degree falls linearly in the log of the ratio from the full end to here.
DETECTION_LIMIT_FULL = 0.01  # EXPERT_REVIEW, owner to confirm: when no minor isomer was seen, a detection limit of 1 percent of the total (the excess is then at least 98 percent) is a generous good value (chiral HPLC and GC usually reach 0.1 to 0.5 percent, from memory, not verified); full agreement up to it.
DETECTION_LIMIT_ZERO = 0.10  # EXPERT_REVIEW, owner to confirm: a detection limit of 10 percent bounds the excess only to at least 80 percent, no longer a statement of high selectivity (no agreement); the degree falls linearly in the log of the limit from the full end to here.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
EFFECT_ORDER = ('enantiomeric_excess', 'enantiomer_ratio', 'diastereomer_ratio')   # the best-determined first: the excess names the major isomer's share directly; the two ratios need the direction of the ratio to be right
# The quantity_kind (QUANTITY_KINDS['product_distribution']) of each effect quantity and the unit of the effect in that kind; literature_product_distribution_direction reads the kind back.
KIND_OF_QUANTITY = {'enantiomeric_excess': 'product_fraction', 'enantiomer_ratio': 'product_fraction_ratio', 'diastereomer_ratio': 'product_fraction_ratio'}
UNIT_OF_KIND = {'product_fraction': 'fraction', 'product_fraction_ratio': 'dimensionless'}
KIND_WITHOUT_EFFECT = 'product_fraction'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'a_chiral_analysis_reports_no_recovery_of_the_starting_amount', 'attributed_signal': 'an_isomer_share_is_the_effect_not_an_attribution_fraction', 'total_signal': 'an_isomer_share_is_the_effect_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_distribution_chiral_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_distribution_chiral_record',
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


def _log(value, full, zero):
    """A ratio limit on the log scale, for _graded."""
    return math.log(value), math.log(full), math.log(zero)


def _overlap(resolution):
    """The share of one of two equal Gaussian peaks of resolution Rs that lies beyond the valley midpoint: the upper tail of the normal curve at 2 Rs."""
    return 0.5 * math.erfc(math.sqrt(2.0) * resolution)


def _judge_resolution(native):
    return _graded(native['peak_resolution_refs'], (_overlap(native['peak_resolution']), _overlap(PEAK_RESOLUTION_FULL), _overlap(PEAK_RESOLUTION_ZERO)))


def _judge_detection(native):
    refs, minor, limit = native['detection_refs'], native['minor_share'], native['detection_limit']
    if minor == 0:      # no minor isomer was seen (an excess of 100 percent): the excess is bounded by the limit alone, so the limit is judged
        return _graded(refs, _log(limit, DETECTION_LIMIT_FULL, DETECTION_LIMIT_ZERO))
    return _graded(refs, _log(minor / limit, DETECTION_RATIO_FULL, DETECTION_RATIO_ZERO))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('peak_resolution', 'peak_resolution_recorded_for_the_sheet'): _judge_resolution, ('minor_isomer_detection', 'detection_limit_recorded_for_the_sheet'): _judge_detection,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _as_fraction(value, unit):
    """A share stated in percent or as a fraction, as a fraction (a percent is a hundredth, FIXED_BY_DEFINITION)."""
    return value / PERCENT_PER_FRACTION if unit == 'percent' else value


def _stated_effect(native, quantity, ref):
    """The stated quantity as an effect operand in the unit of its kind, or None when not stated (its 'support' is the extraction's). An excess becomes the major
    enantiomer's share (1 + ee) / 2; a ratio is the stated number."""
    operand = native['quantities'][quantity]
    if operand['status'] != 'point':
        return None
    kind = KIND_OF_QUANTITY[quantity]
    if quantity == 'enantiomeric_excess':
        value, origin = (1 + _as_fraction(operand['value'], operand['unit'])) / ISOMERS_IN_A_PAIR, 'derived'
    else:
        value, origin = operand['value'], operand['origin']
    return _operand(value, UNIT_OF_KIND[kind], 'distribution_chiral_' + kind + ':' + ref, operand['source_refs'], origin, quantity, operand['support'])


def _variance(graded, quantity, ref):
    """Return (variance in the unit of the effect squared or None, reason or None, refs) of the spread of ``quantity``."""
    native = graded['native']
    spread = native['quantities'][quantity + '_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, quantity + '_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    if quantity == 'enantiomeric_excess':      # f = (1 + ee) / 2 is linear in ee, so the spread of the share is half the spread of the excess
        sd = _as_fraction(spread['value'], spread['unit']) / ISOMERS_IN_A_PAIR
    else:
        sd = spread['value']
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_distribution_chiral(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {quantity: _stated_effect(native, quantity, ref) for quantity in EFFECT_ORDER}
    chosen = next((quantity for quantity in EFFECT_ORDER if stated[quantity] is not None), None)
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if chosen is None:
        null_components['effect'] = 'no_isomer_excess_or_ratio_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        effect = stated[chosen]
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_QUANTITY[chosen], effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_OF_KIND[quantity_kind] + '_squared', 'distribution_chiral_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    result = {'version': VERSION, 'experiment_type': 'distribution_chiral', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if chosen is None:      # no stated excess or ratio: the experiment's stated yes/no result stands, scored like any stated result (literature_direction, the qualitative path)
        result['qualitative_effect'] = {'statement': STATEMENTS[native['product']], 'support_refs': list(native['product_refs'])}
        if native['product'] is not None:
            result['direction_field_support'] = native['product_support']      # the support class of the fact product_detected, the one field the statement is derived from
    return result
