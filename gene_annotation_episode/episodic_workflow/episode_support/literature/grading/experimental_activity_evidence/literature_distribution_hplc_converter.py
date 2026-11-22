"""Distribution_hplc converter: turns the grader's result into what the A105 product_distribution sheet takes.

DRAFT 2026-11-22, owner to confirm. Hand-built, private to distribution_hplc, deterministic. Input: the result of grade_distribution_hplc. Output: the
sheet's input (the 'extraction' grade_assay takes, with assay_type 'product_distribution'), the sheet itself (grade_assay run on it), the dependence keys
the merger needs, and for every sheet component that an HPLC distribution cannot honestly fill, the reason it stays null. Built on the shape of
literature_spectro_direct_converter.py; the class core (four effect quantities, their order, the direction function) is the product_distribution
class's own (literature_product_distribution_direction.py).

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: the share of the claimed product (fraction), the ratio of the claimed product to one
                  other (dimensionless), the share of a species at equilibrium (fraction) or the ratio at equilibrium (dimensionless). Several may be stated;
                  the one used is the best-determined, in the class order PRODUCT_DISTRIBUTION_EFFECT_ORDER
                  (literature_product_distribution_direction.select_product_distribution_effect; the reason is in the contract). A percent is multiplied
                  by its exact factor 0.01 (UNIT_FACTORS, FIXED_BY_DEFINITION): the value is the paper's, only its unit spelling changes. quantity_kind
                  of the extraction names the kind of the effect (KIND_OF_QUANTITY), which the direction function reads. The complement of a share (one
                  minus the share) is NEVER derived: the other species is another partner.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported; confidence_interval and
                  range -> not converted (a confidence interval needs its level and degrees of freedom, a range is no spread of the estimate).
                  Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
recovery          the total recovery (closure) as a fraction, when the passage states it (the class decision of 2026-11-22: the sheet's recovery role takes it).
Every other role stays null, with a reason (NULL_REASONS): attributed signal/total signal (the share already is the effect, filling these would count it
twice), condition test/reference, the assertion and alternative predictions. This method has no immobilized enzyme and no electrode: the
dependence keys immobilized_preparation_ref and surface_ref are None.
qualitative_effect  only when NO effect is stated and the paper states whether the product it is about was found among the products: statement
                  'interaction_detected' (read "product detected") or 'interaction_not_detected' (read "product not detected"), with the refs of the fact
                  that states it and direction_field_support taken from that one fact's quote support. A stated effect fixes the direction; the statement
                  is then not used. A result stated in words alone counts less than a measured one (the contract's stated_strength), which is not
                  re-implemented here. A share of 0 never arrives (the form rejects a number that is not above 0); "not detected" is the fact.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
species_identity          species_assigned_with_standards
response_factors          response_factors_calibrated
common_denominator        shared_denominator_and_closure
matrix_interference       peak_resolution_recorded + reaction_stopped_before_injection
calibration_applicability calibration_range_covers_signals
background_alternatives   no_enzyme_injection + products_stable_through_workup
attribution_supported     inactive_enzyme_injection
equilibrium_state         equilibrium_evidence (required for the two equilibrium kinds, optional otherwise; the grader answers not_applicable when no
                          equilibrium result is stated, and a not_applicable member is dropped)
sampling_basis            replicates
assertion_relevance       native_reaction
condition_scope           purified_enzyme
variance_correspondence   supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES
maps each such criterion and reason to its judgement). Each judgement is a researched value of THIS method made gradual (SOP step 3): full agreement at
the researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the method gives (never a
step), unknown when the paper states nothing, never conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper
itself shows against the standard). A sheet criterion that is supported carries the smallest degree of its members that have one. Quote support
(literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined status: any conflicting ->
conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable
is not selected. Sheet criteria with no counterpart here (measurement_identity) are not selected.

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay
None. Qualitative statements keep the existing vocabulary. Direction and strength of a stated share: literature_product_distribution_direction (same
paradigm as binding, larger is stronger, a quantitative share never opposes); controls, response factors, the denominator, closure, the equilibrium
evidence and replicates lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value
misleads and whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every number is
EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
RESOLUTION_FULL 1.5 -> RESOLUTION_ZERO 0.5, judged on the log of the overlap of two equal Gaussian peaks.
  Q1 a product peak that shares area with its neighbour, so the share of the minor product is partly the other peak's. Q2 general: a resolution Rs of
  1.5 is baseline separation (the usual chromatographic criterion; ICH and USP system-suitability texts ask for about 1.5 to 2 between the critical
  pair), from memory. Q3 absolute and recorded by the paper itself for the nearest neighbour. Q4 the physics gives the shape: for two equal Gaussian
  peaks the area of one beyond the valley midpoint is Q(2 Rs) = 0.5 erfc(sqrt(2) Rs) of its total: 0.14 percent at Rs 1.5, 2.3 percent at 1.0, 6.7 percent
  at 0.75, 16 percent at 0.5. The error of a minor share is proportional to that overlap, so the degree is linear in its log between the two ends
  (0.41 at Rs 1.0, 0.68 at 1.25, 0.18 at 0.75); at or beyond Rs 0.5 (overlap 16 percent) the peaks are not separated (conflicting). Unequal peak sizes make
  the overlap worse for the minor peak; the equal-peak value is the generous case. A resolution above the full end is capped there (the overlap beyond it
  is below what any other source of error in the share leaves visible). Q5 a log ramp on an error that scales with the quantity, like the enzyme-ratio
  ramp of spectro_direct.
RECOVERY_FULL 0.95 -> RECOVERY_ZERO 0.5, judged on the absolute log of the recovery (so 0.95 and 1/0.95 count the same).
  Q1 material that is lost or not seen (a non-eluting or undetected product, an unassigned peak left out of the total), or over-counted (overlapping
  peaks, a wrong standard), so every share over the quantified total is off. Q2 general: method-validation practice accepts recoveries of about 95 to
  105 percent for the main components (ICH Q2 and AOAC practice, from memory); a recovery outside it is a sign that species are missing. Q3 relative to
  the amount the paper applied, which it states. Q4 an unseen amount U of the total bounds the error of any share: with half the material unseen the
  claimed product's true share could differ by a factor of two, so the zero end is a recovery of 0.5 (or 2). Linear in the absolute log of the recovery
  (0.92 at 0.90 or 1.11; 0.73 at 0.80 or 1.25; 0.52 at 0.70). Q5 a symmetric log ramp like the fold gaps of the binding assays. Closure is NOT an
  independent mass balance when the shares were normalized to 100 percent, so this number is judged only when the two denominator facts are both stated yes
  (a recovery with an unknown denominator stays unknown); a recovery cannot lift an unknown denominator.
SIGNAL_TO_NOISE_AT_LIMIT 3, SIGNAL_TO_NOISE_FULL 10 -> SIGNAL_TO_NOISE_ZERO 3, judged on the relative noise 1 / (signal to noise) of the stated share.
  Q1 a share so close to the detection limit that its number is mostly noise (a trace "product" that is a baseline fluctuation or carry-over). Q2 general:
  the limit of detection is the signal-to-noise ratio of about 3 and the limit of quantification about 10 (ICH Q2, from memory). Q3 relative to the
  paper's own limit and its own share. Q4 the stated share has the signal-to-noise ratio SIGNAL_TO_NOISE_AT_LIMIT * share / limit, and the relative
  uncertainty of the quantified area is the inverse of it: 10 percent at the full end (share 3.3 times the limit), 33 percent at the zero end (share equal
  to the limit, detected but not quantified). The degree is linear in that relative noise (0.71 at 2 times the limit, 0.48 at 1.5 times). Q5 the same
  idea as the replicate rule: a precision that grows with the departure.
NOT_DETECTED_LIMIT_FULL 0.01 -> NOT_DETECTED_LIMIT_ZERO 0.5, judged on the log of the detection limit, for a product stated as not detected with no share.
  Q1 a "not detected" that only excludes a large share (a detection limit of 20 percent proves nothing about a product that makes 5 percent). Q2 general: 1
  percent is the class noise end (the share below which a "product" is often an impurity), so a limit at or below it makes "not detected" conclusive for
  every share that would matter; 0.5 is a limit that excludes only a majority product. Q3 relative to the paper's own limit. Q4 the statement excludes
  every share above the limit, so the log of the limit is the scale of how much it excludes (0.41 at 0.1, 0.18 at 0.25); at or beyond 0.5 the statement
  excludes nothing that matters (conflicting for this criterion; the statement itself still opposes by the direction function and the weight falls). Q5 the
  same ends as the class noise end of PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a share from one reaction, whose reaction-to-reaction spread is unseen. Q2 general (triplicate practice). Q3 absolute count. Q4 precision of a mean
  (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule. Repeated injections of one sample are not replicates.
Facts with no number (identity by standard or by mass or NMR, response calibration, controls, quench, stability, equilibrium evidence, native substrate,
purified enzyme): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to soften.
NOT judged, and why: the share's own value (the direction function reads it on its scale); the spread (it is in the strength); the detector and the
fraction basis (plain choices carry no span, and the response-factor facts say what matters about them); the wavelength, the injection count and the
relative response factors themselves (the paper's own constants).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for
this method, decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The share of one species among those a reaction gives, from peak areas: relative by construction, absolute
  (an amount share) only when response factors or calibration curves are used.
  Is there a reference range we would trust if the paper stated less? Not as for KD or kcat: a product share is the paper's own number for its own
  conditions; what is trusted is that a product seen at more than about 1 percent and identified against a standard is really made.
  What does an unstated control or calibration do to the number's meaning? An unstated standard leaves the peak assigned by retention time alone, the
  dominant false positive (a different compound at the same time); an unstated response correction changes the magnitude (an area percent can be off by a
  factor) and not the existence; an unstated no-enzyme injection leaves spontaneous or substrate-borne peaks open; an unstated quench lets the
  distribution drift.
  If we assume it is fine and are wrong, how badly does the score mislead? Wrong identity gives a wrong direction; a wrong response factor a wrong
  magnitude; less severe than a pull-down band (a pure artefact), about as severe as a rate.
  Consistent with KD and spectro_direct? The default 0.80 is a little under spectro_direct (0.85): a peak has more ways to be wrong than an absorbance
  that follows the reaction; the criteria that guard a false product are lower, the benign ones equal or above the default.
  default 0.80. species_identity 0.70 (retention time alone is the main false positive of HPLC). background_alternatives 0.75 (spontaneous and substrate
  peaks). equilibrium_state 0.70 (a composition without the evidence of equilibrium is a single end point; counts only for the equilibrium kinds).
  calibration_applicability 0.85, matrix_interference 0.85, sampling_basis 0.90 (benign when unstated: the usual HPLC practice is calibrated, quenched,
  triplicate). response_factors, common_denominator, attribution_supported, assertion_relevance, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_product_distribution_direction import select_product_distribution_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_distribution_hplc_converted_v1'
CRITERIA_MAP = {'species_identity': ('species_assigned_with_standards',), 'response_factors': ('response_factors_calibrated',),
                'common_denominator': ('shared_denominator_and_closure',), 'matrix_interference': ('peak_resolution_recorded', 'reaction_stopped_before_injection'),
                'calibration_applicability': ('calibration_range_covers_signals',), 'background_alternatives': ('no_enzyme_injection', 'products_stable_through_workup'),
                'attribution_supported': ('inactive_enzyme_injection',), 'equilibrium_state': ('equilibrium_evidence',), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
RESOLUTION_FULL = 1.5  # EXPERT_REVIEW, owner to confirm: baseline separation of the product peak from its nearest neighbour (Rs 1.5; ICH and USP system-suitability practice, from memory, not verified); full agreement from it.
RESOLUTION_ZERO = 0.5  # EXPERT_REVIEW, owner to confirm: at Rs 0.5 two equal Gaussian peaks share about 16 percent of their area (no agreement); the degree falls linearly in the log of that overlap Q(2 Rs) from the full end to here.
RECOVERY_FULL = 0.95  # EXPERT_REVIEW, owner to confirm: total recovery within about 5 percent of the amount applied (method-validation practice of about 95 to 105 percent, ICH Q2 and AOAC, from memory, not verified); full agreement from it, and from its inverse above 1.
RECOVERY_ZERO = 0.5  # EXPERT_REVIEW, owner to confirm: half the material unseen (or twice counted) lets any share be off by a factor of two (no agreement); the degree falls linearly in the absolute log of the recovery from the full end to here.
SIGNAL_TO_NOISE_AT_LIMIT = 3.0  # EXPERT_REVIEW, owner to confirm: the limit of detection is the signal-to-noise ratio of about 3 (ICH Q2, from memory, not verified); the share at the limit therefore has this signal-to-noise ratio.
SIGNAL_TO_NOISE_FULL = 10.0  # EXPERT_REVIEW, owner to confirm: the limit of quantification, signal-to-noise about 10 (ICH Q2, from memory, not verified), a relative noise of 10 percent; full agreement from it.
SIGNAL_TO_NOISE_ZERO = 3.0  # EXPERT_REVIEW, owner to confirm: at signal-to-noise 3 the share is detected but not quantified, a relative noise of a third (no agreement); the degree falls linearly in the relative noise from the full end to here.
NOT_DETECTED_LIMIT_FULL = 0.01  # EXPERT_REVIEW, owner to confirm: a detection limit of 1 percent (the class noise end) makes "not detected" conclusive for every share that matters; full agreement up to it.
NOT_DETECTED_LIMIT_ZERO = 0.5  # EXPERT_REVIEW, owner to confirm: a detection limit of half the products excludes only a majority product (no agreement); the degree falls linearly in the log of the limit from the full end to here.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate reactions; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent reactions falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: a percent is a hundredth; a ratio is a plain number. The stated number is the paper's.
    'product_fraction': ('fraction', {'fraction': 1.0, 'percent': 0.01}),
    'product_fraction_ratio': ('dimensionless', {'dimensionless': 1.0}),
    'equilibrium_fraction': ('fraction', {'fraction': 1.0, 'percent': 0.01}),
    'equilibrium_ratio': ('dimensionless', {'dimensionless': 1.0}),
}
# The quantity_kind (QUANTITY_KINDS['product_distribution']) that names the kind of each effect quantity; the direction function reads it back.
KIND_OF_QUANTITY = {'product_fraction': 'product_fraction', 'product_fraction_ratio': 'product_fraction_ratio', 'equilibrium_fraction': 'equilibrium_fraction', 'equilibrium_ratio': 'equilibrium_ratio'}
KIND_WITHOUT_EFFECT = 'product_fraction'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing): an optional equilibrium criterion
NULL_REASONS = {'attributed_signal': 'a_product_share_is_the_effect_itself_not_an_attribution_fraction', 'total_signal': 'a_product_share_is_the_effect_itself_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_distribution_hplc_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_distribution_hplc_record',
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


def _peak_overlap(resolution):
    """The share of one of two equal Gaussian peaks of resolution Rs that lies beyond the valley midpoint: Q(2 Rs) = 0.5 erfc(sqrt(2) Rs)."""
    return 0.5 * math.erfc(math.sqrt(2.0) * resolution)


def _judge_resolution(native):
    # a resolution above the full end is read at the full end: its overlap is below what any other error of the share leaves visible
    resolution = min(native['peak_resolution'], RESOLUTION_FULL)
    return _graded(native['resolution_refs'], (math.log(_peak_overlap(resolution)), math.log(_peak_overlap(RESOLUTION_FULL)), math.log(_peak_overlap(RESOLUTION_ZERO))))


def _judge_closure(native):
    refs = native['closure_refs']
    verdict = _graded(refs, (abs(math.log(native['total_recovery'])), abs(math.log(RECOVERY_FULL)), abs(math.log(RECOVERY_ZERO))))
    if verdict['status'] == 'conflicting' or native['denominator_status'] == 'supported':
        return verdict
    return _verdict('unknown', refs)      # a recovery cannot lift an unknown denominator: closure is no independent mass balance


def _judge_detection_limit(native):
    refs, limit, share = native['limit_refs'], native['detection_limit'], native['limit_share']
    if share is None:      # a product stated as not detected: how much the limit excludes
        return _graded(refs, (math.log(limit), math.log(NOT_DETECTED_LIMIT_FULL), math.log(NOT_DETECTED_LIMIT_ZERO)))
    signal_to_noise = SIGNAL_TO_NOISE_AT_LIMIT * share / limit
    return _graded(refs, (1.0 / signal_to_noise, 1.0 / SIGNAL_TO_NOISE_FULL, 1.0 / SIGNAL_TO_NOISE_ZERO))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('peak_resolution_recorded', 'resolution_recorded_for_the_sheet'): _judge_resolution, ('shared_denominator_and_closure', 'closure_recorded_for_the_sheet'): _judge_closure,
          ('calibration_range_covers_signals', 'detection_limit_recorded_for_the_sheet'): _judge_detection_limit, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'distribution_hplc_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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


def convert_distribution_hplc(graded):
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
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'distribution_hplc_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
    recovery = native['quantities']['total_recovery']
    if recovery['status'] == 'point':
        quantities['recovery'] = _operand(recovery['value'] * UNIT_FACTORS['product_fraction'][1][recovery['unit']], 'fraction', 'distribution_hplc_total_recovery:' + ref, recovery['source_refs'], recovery['origin'], 'total_recovery')
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
    result = {'version': VERSION, 'experiment_type': 'distribution_hplc', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None and native['product'] is not None:      # no stated quantity: the paper's own statement of the product found or not found fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['product']], 'support_refs': list(native['product_refs'])}
        result['direction_field_support'] = native['product_support']
    return result
