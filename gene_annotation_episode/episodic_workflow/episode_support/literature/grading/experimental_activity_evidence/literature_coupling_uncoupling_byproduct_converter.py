"""Coupling_uncoupling_byproduct converter: turns the grader's result into what the A105 reaction_coupling sheet takes.
DRAFT 2026-11-22 (class reaction_coupling), copied from the shape of literature_spectro_direct_converter.py; every value is for the owner and an expert to correct.

Hand-built, private to coupling_uncoupling_byproduct, deterministic. Input: the result of grade_coupling_uncoupling_byproduct. Output: the sheet's input (the
'extraction' grade_assay takes, with assay_type 'reaction_coupling' and quantity_kind 'productive_fraction'), the sheet itself (grade_assay run on it), the
dependence keys the merger needs, and for every sheet component that a by-product assay cannot honestly fill, the reason it stays null.

Quantity filled
---------------
effect            the PRODUCTIVE FRACTION, a share of the consumed cofactor that ended in the claimed product, in the anchor unit 'fraction'
                  (COUPLING_STRENGTH_ANCHORS['productive_fraction']). It comes from one of two routes, in this order:
                    1. the productive fraction the passage states (a percent is divided by 100: FIXED_BY_DEFINITION);
                    2. the productive fraction BY DIFFERENCE, 1 minus the uncoupled share, only when the passage states the uncoupled share (as a fraction, or as
                       a by-product per cofactor with the coefficient) AND states that the by-product accounts for all the cofactor that did not go to the
                       product (the fact uncoupling_routes_accounted is yes). The value is exact arithmetic on the paper's own numbers and carries
                       origin 'derived'. Without that fact the by-product is only one of the routes (a water-forming oxidase route and a superoxide route
                       also exist for a monooxygenase), so no difference is taken. An uncoupled share at or above 1 leaves no positive productive share:
                       no effect is filled (a computed zero is not a stated "no product"; only the paper's own statement opposes).
                  The class direction function (literature_reaction_coupling_direction.coupling_direction_and_ratio) reads it; select_coupling_effect
                  chooses among stated quantities of COUPLING_EFFECT_ORDER (here one candidate: the by-product ratio is not product per partner and is never offered).
effect_variance   variance of that effect, in 'fraction_squared', only when the passage's spread of the SOURCE quantity allows it: standard_error -> se^2;
                  standard_deviation -> sd^2 / n and only when the replicates criterion is supported; confidence_interval -> not converted. The spread of the
                  source is the spread of the effect: the productive fraction's own spread for route 1, the uncoupled fraction's spread for route 2 (1 minus a
                  number has the same spread), the by-product-per-cofactor spread over the coefficient for the ratio. Otherwise null.
Every other role stays null, with a reason (NULL_REASONS).
qualitative_effect  only when NO effect is filled and the paper states whether it saw coupled product formation above its own control: statement
                  'interaction_detected' (read "coupled product formation detected") or 'interaction_not_detected' (read "no product formed above the control or
                  detection limit": wholly uncoupled), with the refs of the fact that states it. direction_field_support is then the support of that one fact.
                  A filled effect fixes the direction; the statement is then not used. A result stated in words alone counts less than a measured one by the
                  contract's stated_strength (not re-implemented here).

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
measurement_identity       same_preparation
calibration_applicability  standard_series + standard_recovery
matrix_interference        reductant_interference_excluded
background_alternatives    no_enzyme_blank + blank_signal_share
attribution_supported      inactive_enzyme_control + substrate_dependent_turnover
assertion_relevance        native_reaction
condition_scope            purified_enzyme
sampling_basis             replicates
product_identity           product_identity (the product measured too)
stoichiometry              uncoupled_share + productive_share_bound + uncoupling_routes_accounted
matched_windows            same_mixture_and_window
reporter_specificity       byproduct_identity_control + byproduct_not_consumed (the by-product assay IS this type's reporter)
variance_correspondence    supported only when a variance was computed
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose
members are all not_applicable is not selected. A sheet criterion that is supported carries the smallest degree of its members that have one. Quote support
(literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status.

The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps
each such criterion and reason to its judgement). Each judgement is a researched value of THIS assay made gradual (SOP step 3): full agreement at the researched good
value, falling linearly on the scale the physics gives to zero at a researched no-longer-meaningful value (never a step), unknown when the paper states nothing,
never conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper itself shows against the standard).

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None
(nothing immobilized, no surface). Qualitative statements keep the existing vocabulary. Direction and strength: literature_reaction_coupling_direction (a LARGER
productive fraction is stronger; a measured result never opposes); controls, blanks, the coefficient, the reporter checks and the other sheet criteria lower the
WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value
misleads and whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every number is EXPERT_REVIEW,
owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
BLANK_FULL_PERCENT 10 -> BLANK_ZERO_PERCENT 100 (the no-enzyme blank as a share of the signal), linear in the share.
  Q1 a by-product signal that the reagents and the cofactor make without the enzyme (NADPH slowly reduces oxygen, Amplex Red and peroxidase auto-oxidize, the
  ferrous ion of the xylenol orange assay oxidizes in air), so that the net by-product is a small difference of two large numbers. Q2 general practice: a blank
  of about a tenth of the signal or less is subtracted without loss (from memory; the manufacturers' guides of the Amplex Red peroxide assay and the FOX assay ask for a
  reagent blank, not for a number: 10 percent is a judgement); lab- and reagent-specific. Q3 relative to the paper's own signal, which the passage states as a
  share. Q4 the net signal is (1 - b) of the total, and for a fixed noise of the two readings the signal-to-noise of the net by-product falls in proportion to
  (1 - b): the degree is linear in b from 1 at 10 percent to 0 at 100 percent, where the blank is as large as the signal (nothing is left: conflicting). Q5 the same
  idea as the consumed-substrate and the blank judgements of the other assays: a bias that grows with the departure from the researched value. The class core
  names the same two ends (10 and 100 percent).
RECOVERY_FULL_LOW 0.9 / RECOVERY_ZERO_LOW 0.5 (the recovery of a known by-product added to the complete mixture), symmetric on the log scale.
  Q1 a reporter that does not see all of the by-product in the real mixture (the peroxide is lost to the enzyme's own catalase-like or peroxidase activity, the
  reporter is exhausted, the signal is quenched: under-recovery) or sees more (a reductant or the substrate gives a signal: over-recovery). Q2 general: a spiked
  recovery between 90 and 110 percent is the usual full agreement of an analytical recovery check (from memory; analytical method validation guidance asks 80 to 120
  percent for a complex matrix), lab-specific beyond that. Q3 relative to the amount the paper itself added. Q4 an error of a factor f in the recovery is an error of a
  factor f in the by-product and so in the uncoupled share; the log of the recovery is the natural scale and under- and over-recovery by the same factor
  mislead the share equally, so the degree is linear in |ln recovery| from the full end (ln of 1 / 0.9, which includes 1.1) to the zero end (ln 2, which includes 0.5),
  where the signal is off by a factor of 2 and the paper's own spike shows the assay does not measure the by-product (conflicting). Q5 the same band as the class core (0.9 to 1.1
  full, 0.5 or 2 zero) and as the dialysis mass-balance recovery (80 to 120 percent, a little wider).
SHARE_FULL_MAX 1.1 -> SHARE_ZERO 1.5 (the stated uncoupled share, and the stated productive share, against what the chemistry allows), linear in the share.
  Q1 more by-product (or more product) than the cofactor consumed can give: the reaction cannot make more than one hydrogen peroxide per NAD(P)H (two electrons each) or
  two superoxide, so a share above 1 is a failed measurement or a wrong coefficient, a diagnostic and not a value to clip (the CsiD note of the class inventory). Q2 the
  bound is chemistry (not lab-specific); the 1.1 is the combined error of two optical assays (the cofactor at 340 nm and the by-product reagent, each a few percent to ten
  percent: from memory); the 1.5 is a judgement: an excess of half is more than the two errors can make together and points to another source of the by-product
  or of the electrons (a regenerating system, a second reductant, or a superoxide counted as peroxide after dismutation). Q3 relative to the cofactor the paper itself
  consumed (the share is the paper's own ratio). Q4 a share just above 1 is probably noise (a small loss of degree); the degree falls linearly from 1 at 1.1 to 0 at 1.5, and a
  share at or above 1.5 shows the stated stoichiometry is not met (conflicting). The low side is not judged here: a low uncoupled share is a well-coupled enzyme, not
  a failure, and a low productive share is read by the strength scale. Q5 the same two ends are used for the stated productive share, so the by-difference route and the
  stated route are judged alike.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a ratio from one experiment, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice). Q3 absolute count. Q4 precision of a mean
  (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the controls, the by-product identity controls, the standard series, the routes accounted, the product measured too, the same mixture and window, the native
substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to soften.
NOT judged, and why: the window overlap as a number (the passage rarely gives both windows; the facts same_mixture and same_window stand for it); the absolute amounts of cofactor and
by-product (no criterion reads them; the paper's own ratio or share is the extraction target); the pH and the temperature (the claim carries no condition, and the identity block
records the temperature). The by-difference route takes the difference of two quantities that can be close (an uncoupled share of 0.95 leaves a productive share of 0.05 that the two
assays' errors, about 0.1, cannot resolve): the stated spread lowers the strength when it is given; with no spread stated nothing lowers it here (reported to the owner as an open point).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this assay, drafted
2026-11-22, owner to confirm:
  What does it measure; absolute or relative? A dimensionless ratio of two absolute amounts, the by-product formed and the cofactor consumed; each side needs its own
  calibration (a peroxide standard curve, an extinction coefficient), so the ratio is absolute but only as good as both calibrations.
  Is there a reference range we would trust if the paper stated less (as for KD)? No: the uncoupled share of a monooxygenase runs from a few percent to nearly all of the cofactor
  (well-coupled native substrate against a poor one; Denisov et al. 2005 Chem Rev, from memory), so there is no prior that holds for an unstated detail.
  What does an unstated control or calibration do to what the number means? The peroxide reagents are known for artefacts (reductants and thiols, direct reaction with the
  cofactor, light, loss of the peroxide to the enzyme), so an unstated reporter check is not benign: a false by-product is a false uncoupling, and by difference a false
  productive share; the cofactor side (absorbance at 340 nm) is benign.
  If we assume it is fine and are wrong, how badly does the score mislead? The magnitude of the productive share, by the same factor; and, when the product is not measured
  and the other routes are not counted, the direction of the claim is carried by a number that does not identify the product at all.
  Consistent with KD (0.90) and with spectro_direct (0.85)? Lower: 0.75, with the readout needing two calibrations and no trusted reference range (the same level as the fret and mst relative readouts).
  type default 0.75. product_identity 0.55 (an unstated product measurement most likely means none was made: the ratio then does not identify the product). stoichiometry 0.60
  (an unstated accounting of the other routes usually means only one route was measured, and the difference then overstates the coupling). reporter_specificity 0.65 and
  matrix_interference 0.65 (reagent artefacts are common and the checks are often unstated). background_alternatives 0.70 and attribution_supported 0.70 (autoxidation of the
  cofactor and a contaminating iron or heme are real, the blank is ordinary practice). matched_windows 0.65 (the cofactor loss and the by-product are often measured separately).
  measurement_identity 0.80, calibration_applicability 0.85 (a standard curve is usual), sampling_basis 0.90 (triplicates are usual and benign); assertion_relevance and condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_reaction_coupling_direction import select_coupling_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SUPPORT_WEAKEST_ORDER
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_coupling_uncoupling_byproduct_converted_v1'
CRITERIA_MAP = {'measurement_identity': ('same_preparation',), 'calibration_applicability': ('standard_series', 'standard_recovery'), 'matrix_interference': ('reductant_interference_excluded',),
                'background_alternatives': ('no_enzyme_blank', 'blank_signal_share'), 'attribution_supported': ('inactive_enzyme_control', 'substrate_dependent_turnover'),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',), 'sampling_basis': ('replicates',), 'product_identity': ('product_identity',),
                'stoichiometry': ('uncoupled_share', 'productive_share_bound', 'uncoupling_routes_accounted'), 'matched_windows': ('same_mixture_and_window',),
                'reporter_specificity': ('byproduct_identity_control', 'byproduct_not_consumed')}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
BLANK_FULL_PERCENT = 10.0  # EXPERT_REVIEW, owner to confirm: the no-enzyme blank at most about a tenth of the signal is subtracted without loss (reagent-guide practice, from memory, not verified); full agreement up to it.
BLANK_ZERO_PERCENT = 100.0  # EXPERT_REVIEW, owner to confirm: a blank as large as the signal leaves no net by-product (no agreement, conflicting); the degree falls linearly in the share, because the signal-to-noise of the net signal is proportional to 1 minus the blank share.
RECOVERY_FULL_LOW = 0.9  # EXPERT_REVIEW, owner to confirm: a recovery of a known added amount between 0.9 and 1.1 (taken on the log scale as |ln recovery| up to ln(1 / 0.9)) is a full agreement (analytical recovery practice, from memory, not verified).
RECOVERY_ZERO_LOW = 0.5  # EXPERT_REVIEW, owner to confirm: a recovery of 0.5, or its mirror 2 (|ln recovery| = ln 2), is a signal off by a factor of 2: the reporter does not measure the by-product (no agreement, conflicting); linear in |ln recovery| between the ends, because an error by a factor f in the recovery is an error by the factor f in the share.
SHARE_FULL_MAX = 1.1  # EXPERT_REVIEW, owner to confirm: the most by-product (or product) per cofactor the chemistry allows is 1 (one peroxide per NAD(P)H, in the coefficient's own unit); 1.1 is the combined error of two optical assays (from memory); full agreement up to it.
SHARE_ZERO = 1.5  # EXPERT_REVIEW, owner to confirm: an excess of half over the chemistry's bound is more than two assay errors can make (another source of the by-product or of the electrons, or a wrong coefficient): the stated stoichiometry is not met (no agreement, conflicting); the degree falls linearly in the share.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
PRODUCTIVE_UNIT = 'fraction'  # the anchor unit of the effect (literature_row_contract.COUPLING_STRENGTH_ANCHORS['productive_fraction'])
QUANTITY_KIND = 'productive_fraction'  # the quantity_kind (QUANTITY_KINDS['reaction_coupling']) of the effect, and of an extraction that fills none
SPREAD_FACTORS = {'fraction': 1.0, 'percent': 1.0 / PERCENT_PER_FRACTION, 'mol_per_mol': 1.0}  # FIXED_BY_DEFINITION: exact factors from the unit of a spread to the unit 'fraction' (a ratio's own factor is applied by the coefficient).
NULL_REASONS = {'recovery': 'the_recovery_of_the_byproduct_standard_is_judged_as_a_criterion_not_as_a_recovery_deviation', 'attributed_signal': 'the_uncoupled_share_is_stoichiometry_not_an_attribution_fraction_of_one_signal',
                'total_signal': 'the_uncoupled_share_is_stoichiometry_not_an_attribution_fraction_of_one_signal', 'condition_test': 'no_matched_nuisance_condition_response_in_a_coupling_uncoupling_byproduct_record',
                'condition_reference': 'no_matched_nuisance_condition_response_in_a_coupling_uncoupling_byproduct_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment',
                'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENT = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected'}   # read "coupled product formation detected" / "no product formed above the control" for this class


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


def _judge_blank(native):
    return _graded(native['blank_refs'], (native['blank_percent'], BLANK_FULL_PERCENT, BLANK_ZERO_PERCENT))


def _judge_recovery(native):
    return _graded(native['recovery_refs'], (abs(math.log(native['recovery_fraction'])), -math.log(RECOVERY_FULL_LOW), -math.log(RECOVERY_ZERO_LOW)))


def _judge_uncoupled_share(native):
    return _graded(native['uncoupled_share_refs'], (native['uncoupled_share'], SHARE_FULL_MAX, SHARE_ZERO))


def _judge_productive_share(native):
    return _graded(native['productive_share_refs'], (native['productive_share'], SHARE_FULL_MAX, SHARE_ZERO))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('blank_signal_share', 'blank_share_recorded_for_the_sheet'): _judge_blank, ('standard_recovery', 'recovery_recorded_for_the_sheet'): _judge_recovery,
          ('uncoupled_share', 'uncoupled_share_recorded_for_the_sheet'): _judge_uncoupled_share, ('productive_share_bound', 'productive_share_recorded_for_the_sheet'): _judge_productive_share,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _weakest(supports):
    return min((support for support in supports if support is not None), key=SUPPORT_WEAKEST_ORDER.index)


def _effect(graded):
    """Return (effect operand with 'support' or None, spread quantity name, divisor of the spread, reason when None).
    The stated productive fraction, else the productive fraction by difference (only when the by-product is stated to account for all the uncoupling)."""
    native = graded['native']
    ref = graded['experiment_ref']
    productive = native['quantities']['productive_fraction']
    if productive['status'] == 'point':
        value = productive['value'] * SPREAD_FACTORS[productive['unit']]
        operand = _operand(value, PRODUCTIVE_UNIT, 'coupling_uncoupling_byproduct_productive_fraction:' + ref, productive['source_refs'], productive['origin'], 'productive_fraction', productive['support'])
        return operand, 'productive_fraction_spread', 1.0, None
    share, routes = native['uncoupled_share'], native['routes_accounted']
    if share is None:
        return None, None, None, 'no_productive_fraction_and_no_uncoupled_share_given'
    if routes['answer'] != 'yes':
        return None, None, None, 'by_product_not_stated_to_account_for_all_uncoupling_so_no_difference_is_taken'
    if share >= 1.0:
        return None, None, None, 'uncoupled_share_at_or_above_one_leaves_no_positive_productive_share'
    refs = list(dict.fromkeys([*native['uncoupled_share_refs'], *routes['refs']]))
    support = _weakest([*native['uncoupled_share_supports'], routes['support']])
    operand = _operand(1.0 - share, PRODUCTIVE_UNIT, 'coupling_uncoupling_byproduct_productive_by_difference:' + ref, refs, 'derived', 'productive_fraction_by_difference', support)
    if native['uncoupled_share_source'] == 'uncoupled_fraction':
        return operand, 'uncoupled_fraction_spread', 1.0, None
    return operand, 'byproduct_per_cofactor_spread', native['quantities']['byproduct_coefficient']['value'], None


def _variance(graded, spread_quantity, divisor):
    """Return (variance in fraction_squared or None, reason or None, refs) of the spread of the source quantity of the effect."""
    native = graded['native']
    spread = native['quantities'][spread_quantity]
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, spread_quantity + '_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = spread['value'] * SPREAD_FACTORS[spread['unit']] / divisor
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_coupling_uncoupling_byproduct(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    effect, spread_quantity, divisor, no_effect_reason = _effect(graded)
    effect_support = None
    if effect is None:
        null_components['effect'] = no_effect_reason
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_coupling_effect({'productive_fraction': effect})
        effect_support = effect['support']
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        variance, variance_reason, variance_refs = _variance(graded, spread_quantity, divisor)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, PRODUCTIVE_UNIT + '_squared', 'coupling_uncoupling_byproduct_' + chosen + '_variance:' + ref, variance_refs, 'derived', spread_quantity)
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'reaction_coupling', 'assertion_ref': native['assertion_ref'], 'quantity_kind': QUANTITY_KIND, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'coupling_uncoupling_byproduct', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None and native['coupled'] is not None:      # no effect: the paper's own statement of coupled product formation above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['coupled']], 'support_refs': list(native['coupled_refs'])}
        result['direction_field_support'] = native['coupled_support']
    return result
