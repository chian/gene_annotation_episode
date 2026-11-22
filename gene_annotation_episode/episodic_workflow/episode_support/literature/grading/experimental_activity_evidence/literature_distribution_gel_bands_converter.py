"""Distribution_gel_bands converter: turns the grader's result into what the A105 product_distribution sheet takes (DRAFT 2026-11-22, owner to correct).

Hand-built, private to distribution_gel_bands, deterministic. Input: the result of grade_distribution_gel_bands. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'product_distribution'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for every sheet
component that a gel cannot honestly fill, the reason it stays null. Built on the shape of the spectro_direct converter with the class core of
product_distribution (docs/axis_restructure_20261117/A105_PRODUCT_DISTRIBUTION_INVENTORY.md) in place of the activity core.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: the share of the claimed product (fraction) or the ratio of its share to another product's
                  (dimensionless). Both may be stated; the one used is the best-determined, in the class order PRODUCT_DISTRIBUTION_EFFECT_ORDER
                  (literature_product_distribution_direction.select_product_distribution_effect). A percent is multiplied by its exact factor (UNIT_FACTORS,
                  FIXED_BY_DEFINITION): the value is the paper's, only its unit spelling changes. quantity_kind of the extraction names the kind of the effect
                  (KIND_OF_QUANTITY), which the direction function reads. The two equilibrium kinds are not filled: a gel of this type states a distribution of products,
                  not an equilibrium.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it: standard_error -> se^2;
                  standard_deviation -> sd^2 / n and only when the replicates criterion is supported; confidence_interval and range -> not converted (they need their level
                  and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
recovery          the total recovery of the lane as a fraction (the sheet takes its deviation from 1 as a diagnostic), or null when not stated.
Every other role stays null, with a reason (NULL_REASONS): attributed signal and total signal (the share is the effect and is not counted twice as an attribution
fraction), condition test and reference, the assertion and alternative predictions.
qualitative_effect  only when NO effect is stated and the paper states whether the named product was found: statement 'interaction_detected' (read "product detected")
                  or 'interaction_not_detected' (read "product not detected"), with the refs of the fact that states it; direction_field_support is the support of that one
                  fact. A stated effect fixes the direction; the statement is then not used. A result stated in words alone counts less than a measured one through the
                  contract's stated_strength; that is not done here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
species_identity          size_markers + band_resolution
response_factors          equal_response
common_denominator        denominator_coverage
calibration_applicability linear_range + minor_band_limit + lane_signal_accounted
matrix_interference       reaction_quenched + background_subtraction
background_alternatives   background_lane
attribution_supported     inactive_enzyme_lane
assertion_relevance       native_reaction + single_hit_regime
condition_scope           purified_enzyme
sampling_basis            replicates
variance_correspondence   supported only when a variance was computed
Not selected (as in the other types): measurement_identity (no method criterion decides it), equilibrium_state (optional for the two product kinds this type fills).
Deviation from the inventory entry, reported: the inventory maps native_substrate to condition_scope; its own section 3.10 says assertion_relevance is read from
native_substrate and the match of the stated product to the claim, and that is what is done here (as in spectro_direct), purified_enzyme alone goes to condition_scope.

The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Each judgement is a researched value of THIS method made gradual (SOP step 3): full agreement at the researched good value, falling
smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the method gives (never a step), unknown when the paper states nothing, never
conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported
carries the smallest degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and never
changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose
members are all not_applicable is not selected.

How the class decisions apply here (owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None (no immobilized enzyme,
no surface, no electrode). Qualitative statements keep the existing vocabulary, read "product detected / not detected". Direction and strength of a stated share:
literature_product_distribution_direction (the share of the claimed product, larger is stronger); controls, response factors, the denominator and the rest lower the WEIGHT
only. The enzyme-lane facts, size markers, quench and the like have no researched number to soften: the paper's own statement decides (yes supported, no conflicting,
silence unknown).

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads and
whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
DETECTION_FULL_RATIO 3 -> DETECTION_ZERO_RATIO 1, judged on the log of (share of the claimed product) / (the paper's stated detection limit).
  Q1 a claimed product whose share is only near the smallest share the gel can show may be background, a smear, a degradation product or an impurity of the substrate,
  and its share is poorly measured. Q2 general: in analytical validation the detection limit is about 3.3 sigma of the blank over the slope and the quantification limit about
  10 sigma (ICH Q2, from memory), so the quantification limit is about 3 times the detection limit; below it a band is seen but not measured. Q3 relative to the paper's own
  stated limit and its own share: right, the grader records both. Q4 the relative uncertainty of a signal at k times the detection limit is about 0.3 / k (30 percent at the
  limit, 10 percent at 3 times it, 3 percent at 10 times it), so the degree is linear in the log of k between the two ends: 3 gives 1, 2 gives 0.63, 1.5 gives 0.37. A share at
  or below its own detection limit is a number the paper itself shows is not a measurement (conflicting). Q5 a log-ratio ramp like the other ratio judgements.
RECOVERY_FULL_DEVIATION 0.10 -> RECOVERY_ZERO_DEVIATION 0.50, judged linearly in |recovery - 1|.
  Q1 signal held in the well, in a smear, off the gel or lost in loading means the counted bands are not the whole lane, and a band hidden there is a product that does not
  enter the share. Q2 general: the replicate scatter of densitometry of a gel is of the order of 5 to 10 percent (from memory), so a deviation up to 0.10 cannot be told from
  that scatter; the lab-specific part is the exact 0.10. Q3 relative to the paper's own lane or input total, which the passage states as a share; right. Q4 if a share u of the
  lane is not in the counted bands, the share of the claimed product among all products can lie anywhere in an interval whose width is at most u, so the error grows linearly
  with the deviation and the degree is linear in it: a deviation of 0.2 gives 0.75, 0.3 gives 0.50. At 0.5, half of the signal is unaccounted and the share is not determined
  (conflicting). A recovery above 1 (more signal than the input) is a deviation in the same way. Q5 a bias that grows with the departure, as in the other assays.
SINGLE_HIT_FULL_CONVERSION 0.20 -> SINGLE_HIT_ZERO_CONVERSION 0.90, judged linearly in the share of the cut molecules that were cut more than once.
  Q1 a distribution of cleavage sites or product lengths read at high conversion is not the primary distribution: molecules cut a second time move signal from long to short
  fragments and from one site to the next. Q2 general: cleavage mapping and footprinting are run under single-hit conditions, no more than about 20 to 30 percent of the substrate
  cut (from memory); the exact 0.20 is a judgement. Q3 relative to the paper's own conversion, which the passage states; right. Q4 the worst case is a substrate with many equal,
  independent sites (a substrate with one site has no second cut, so this is a bound, not a measurement): with c the converted share the mean number of cuts per molecule is
  m = -ln(1 - c) and the share of cut molecules cut more than once is 1 - m (1 - c) / c: 0.05 at c = 0.1, 0.107 at 0.2, 0.17 at 0.3, 0.31 at 0.5, 0.74 at 0.9. The degree is
  linear in that share between the two ends, so it falls gently at first and faster later (c = 0.5 gives 0.69). At or beyond c = 0.9 three quarters of the cut molecules are cut
  again (conflicting). Q5 the same idea as the progress-curve bias of spectro_direct: a bias that grows with the departure from the researched value.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a share from one reaction, whose reaction-to-reaction spread is unseen. Q2 general (triplicate practice for gel densitometry; lanes of one gel are not replicates, which
  the independence fact carries). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (size markers, band resolution, equal response, denominator coverage, linear range, quench, background subtraction, the background lanes, the inactive
enzyme lane, the native substrate and the purified enzyme): the paper's own statement decides. NOT judged, and why: the gel percentage and the fragment size (the resolution of a
gel is stated by the paper as resolved or not, which is the fact band_resolution; the paper's gel percentage against its fragment size would need both stated for the same
band); the labelling choice (recorded for the reviewer; what it means for the share is the two response facts); the pH and the temperature (the claim carries no condition,
and the identity block records the temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this method, owner to
confirm:
  What does it measure; absolute or relative? The share of one product among the products of one lane: a ratio of band signals inside one lane, so loading cancels, but
  the signal per molecule is arbitrary (label or stain), so the share is a share of signal and equals a share of molecules only when the response per molecule is equal.
  Is there a reference range we would trust if the paper stated less (as for KD)? No for the share itself (any share of 0 to 1 is possible); yes for the practice: end-labelled
  products read on a phosphorimager and run beside a ladder are the usual form of this experiment, so a silent paper is most often in that practice.
  What does an unstated control or calibration do to the number's meaning? An unstated no-enzyme lane leaves the cleavage of a labile substrate (RNA breaks by itself) and the
  products already in the substrate preparation open: they are counted as products of the enzyme, the main false positive of a gel. An unstated response correction on a stained
  gel can distort a share by the ratio of the fragment lengths (a long fragment stains more); on an end-labelled gel it does not matter. Unstated size markers are almost
  always a reporting gap, not a missing marker. An unstated linear range matters little for a phosphorimager (a wide range) and more for a film or a stain.
  If we assume it is fine and are wrong, how badly does the score mislead? A background or a contaminating nuclease counted as the enzyme's product misleads the direction for
  a weak share and the magnitude for a strong one; a response error misleads the magnitude of a share only.
  Consistent with KD and EMSA? The default 0.75 is level with EMSA (the other gel readout, relative within a lane, needing in-lane controls) and below spectro_direct (0.85, an
  absolute rate). Overrides: response_factors 0.65 (the length bias of an unstated stain), common_denominator 0.70 (an unassigned band left out is unseen), background_alternatives
  0.65 (the leading false positive), attribution_supported 0.70 (a contaminating nuclease; the inactive-enzyme lane is often not reported), species_identity 0.85 (markers are
  almost universal), calibration_applicability 0.80 and sampling_basis 0.85 (usual practice, benign when unstated).
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_product_distribution_direction import select_product_distribution_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_distribution_gel_bands_converted_v1'
CRITERIA_MAP = {'species_identity': ('size_markers', 'band_resolution'), 'response_factors': ('equal_response',), 'common_denominator': ('denominator_coverage',),
                'calibration_applicability': ('linear_range', 'minor_band_limit', 'lane_signal_accounted'), 'matrix_interference': ('reaction_quenched', 'background_subtraction'),
                'background_alternatives': ('background_lane',), 'attribution_supported': ('inactive_enzyme_lane',), 'assertion_relevance': ('native_reaction', 'single_hit_regime'),
                'condition_scope': ('purified_enzyme',), 'sampling_basis': ('replicates',)}
DETECTION_FULL_RATIO = 3.0  # EXPERT_REVIEW, owner to confirm: a share three times the detection limit is at the quantification limit (about 10 sigma against 3.3 sigma, ICH Q2, from memory), a relative uncertainty of about 10 percent; full agreement from it.
DETECTION_ZERO_RATIO = 1.0  # EXPERT_REVIEW, owner to confirm: a share at its own detection limit is seen but not measured (relative uncertainty about 30 percent): no agreement; the degree falls from DETECTION_FULL_RATIO linearly in the log of the ratio, because the relative uncertainty is proportional to 1 / ratio.
RECOVERY_FULL_DEVIATION = 0.10  # EXPERT_REVIEW, owner to confirm: the replicate scatter of gel densitometry is about 5 to 10 percent (from memory), so a recovery within 0.10 of 1 cannot be told from it; full agreement up to it.
RECOVERY_ZERO_DEVIATION = 0.50  # EXPERT_REVIEW, owner to confirm: half of the lane signal unaccounted: the share of the claimed product can lie anywhere in an interval of width 0.5 (no agreement); the degree falls linearly in the deviation from RECOVERY_FULL_DEVIATION, because the width of the interval is the unaccounted share.
SINGLE_HIT_FULL_CONVERSION = 0.20  # EXPERT_REVIEW, owner to confirm: single-hit conditions of cleavage mapping, at most about 20 to 30 percent of the substrate cut (from memory); full agreement up to it (about 11 percent of the cut molecules cut twice in the worst case).
SINGLE_HIT_ZERO_CONVERSION = 0.90  # EXPERT_REVIEW, owner to confirm: at 90 percent converted, three quarters of the cut molecules of a many-site substrate are cut again (worst case): the distribution is not the primary one (no agreement); the degree falls linearly in the share of cut molecules cut more than once.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate reactions; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent reactions falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
SHARE_FACTORS = {'fraction': 1.0, 'percent': 0.01}   # FIXED_BY_DEFINITION: a percent is a hundredth of a fraction; the stated number is the paper's.
UNIT_FACTORS = {
    'product_fraction': ('fraction', SHARE_FACTORS),
    'product_fraction_ratio': ('dimensionless', {'dimensionless': 1.0}),
}
# The quantity_kind (QUANTITY_KINDS['product_distribution']) that names the kind of each effect quantity; literature_product_distribution_direction reads it back.
KIND_OF_QUANTITY = {'product_fraction': 'product_fraction', 'product_fraction_ratio': 'product_fraction_ratio'}
KIND_WITHOUT_EFFECT = 'product_fraction'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'attributed_signal': 'a_band_share_is_the_effect_not_an_attribution_fraction', 'total_signal': 'a_band_share_is_the_effect_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_distribution_gel_bands_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_distribution_gel_bands_record',
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


def _log(value, full, zero):
    """A ratio limit on the log scale, for _graded."""
    return math.log(value), math.log(full), math.log(zero)


def _cut_more_than_once(fraction):
    """The share of the cut molecules that were cut more than once, for a substrate of many equal independent sites of which the fraction ``fraction`` (below 1) was converted: 1 - m (1 - c) / c with m = -ln(1 - c) cuts per molecule."""
    return 1.0 - -math.log1p(-fraction) * (1.0 - fraction) / fraction


def _judge_detection(native):
    return _graded(native['limit_refs'], _log(native['share_over_detection_limit'], DETECTION_FULL_RATIO, DETECTION_ZERO_RATIO))


def _judge_recovery(native):
    return _graded(native['recovery_refs'], (abs(native['recovery_fraction'] - 1.0), RECOVERY_FULL_DEVIATION, RECOVERY_ZERO_DEVIATION))


def _judge_single_hit(native):
    refs, fraction = native['conversion_refs'], native['conversion_fraction']
    if fraction >= SINGLE_HIT_ZERO_CONVERSION:
        return _verdict('conflicting', refs)
    return _graded(refs, (_cut_more_than_once(fraction), _cut_more_than_once(SINGLE_HIT_FULL_CONVERSION), _cut_more_than_once(SINGLE_HIT_ZERO_CONVERSION)))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('minor_band_limit', 'limit_recorded_for_the_sheet'): _judge_detection, ('lane_signal_accounted', 'recovery_recorded_for_the_sheet'): _judge_recovery,
          ('single_hit_regime', 'conversion_recorded_for_the_sheet'): _judge_single_hit, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'distribution_gel_bands_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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


def convert_distribution_gel_bands(graded):
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
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'distribution_gel_bands_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
    recovery = native['quantities']['total_recovery']
    if recovery['status'] == 'point':
        quantities['recovery'] = _operand(recovery['value'] * SHARE_FACTORS[recovery['unit']], 'fraction', 'distribution_gel_bands_total_recovery:' + ref, recovery['source_refs'], recovery['origin'], 'total_recovery')
    else:
        null_components['recovery'] = 'total_recovery_not_stated'
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
    result = {'version': VERSION, 'experiment_type': 'distribution_gel_bands', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None and native['product'] is not None:      # no stated share: the paper's own statement that the named product was or was not found fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['product']], 'support_refs': list(native['product_refs'])}
        result['direction_field_support'] = native['product_support']
    return result
