"""Distribution_nmr converter: turns the grader's result into what the A105 product_distribution sheet takes.

Hand-built, private to distribution_nmr, deterministic. FIRST DRAFT 2026-11-22, owner to confirm; every number below is EXPERT_REVIEW and every literature
figure is from the drafter's memory, NOT web-verified and NOT checked against a method paper. Input: the result of grade_distribution_nmr. Output: the sheet's
input (the 'extraction' grade_assay takes, with assay_type 'product_distribution'), the sheet itself (grade_assay run on it), the dependence keys the merger
needs, the qualitative effect when no effect is stated, and for every sheet component that an NMR product mixture cannot honestly fill, the reason it stays null.
Built on the structure of the spectro_direct converter (the first type built outside the binding class).

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity (literature_row_contract.PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS): the share of the named
                  species among the products (fraction), the ratio of two products (dimensionless), the share at equilibrium (fraction) or the ratio at equilibrium
                  (dimensionless). Several may be stated; the one used is the best-determined, in the class order PRODUCT_DISTRIBUTION_EFFECT_ORDER
                  (literature_product_distribution_direction.select_product_distribution_effect). A percent is multiplied by its exact factor 0.01 (UNIT_FACTORS,
                  FIXED_BY_DEFINITION): the value is the paper's, only its unit spelling changes. quantity_kind of the extraction names the kind of the effect, which
                  the direction function reads. A share of exactly 0 is never an effect operand (the extraction refuses a number that is not above 0): "not
                  detected" is the fact claimed_product_detected, handed on as the qualitative effect.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it: standard_error -> se^2;
                  standard_deviation -> sd^2 / n and only when the replicates criterion is supported; confidence_interval and range -> not converted (a confidence
                  interval needs its level and degrees of freedom, a range is no variance). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
recovery          the stated total recovery (the sum of the quantified species over the amount started with) as a fraction; null with a reason when not stated.
Every other role stays null, with a reason (NULL_REASONS): attributed signal and total signal (the share is the effect already; keeping it in the effect avoids
counting it twice), condition test and reference, the assertion and alternative predictions.
qualitative_effect  only when NO effect is stated: the paper's own statement whether the spectrum showed the product the experiment tests for. Statement
                  'interaction_detected' (read "product detected"), 'interaction_not_detected' (read "product not detected") or 'interaction_not_stated', with the
                  refs of the fact that states it. direction_field_support is then the quote support of that one fact. A result stated in words alone already counts
                  less than a measured one (the contract's stated_strength); nothing of that is repeated here.
direction_field_support  the quote support of the field that fixes the direction: the chosen effect operand, or the fact claimed_product_detected, or None.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
species_identity          shares_from_resolved_signals + species_assigned_with_standards
response_factors          relaxation_delay (NMR has no detector response curve: the integrals are in proportion to the amounts only when every integrated nucleus has
                          relaxed fully between scans, so the delay against the longest T1 is what answers "are species-specific responses calibrated or equal")
common_denominator        denominator_and_coverage
background_alternatives   no_enzyme_spectrum
attribution_supported     inactive_enzyme_spectrum
calibration_applicability minor_signal_to_noise
equilibrium_state         stable_composition, SELECTED ONLY when the effect is an equilibrium quantity (equilibrium_fraction or equilibrium_ratio). The sheet requires it
                          for those two kinds and treats it as optional for the two product kinds; the weight counts every selected criterion (an unknown one at the
                          type's unknown weight), so a product share read from a reaction that is not claimed to be at equilibrium must not carry an unknown
                          equilibrium criterion. A paper that states a product share does not claim an equilibrium by that.
sampling_basis            replicates
assertion_relevance       native_reaction
condition_scope           purified_enzyme
variance_correspondence   supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity, matrix_interference) are not selected. The thresholds are judged here, not in the grader (it records
facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Each judgement is a
researched value of THIS method made gradual (SOP step 3): full agreement at the researched good value, falling smoothly to zero at a researched no-longer-meaningful
value on the scale the physics of the method gives (never a step), unknown when the paper states nothing, never conflicting for a short count. A value at or beyond a
zero end that the paper itself states is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported carries the smallest degree
of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined
status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all
not_applicable is not selected.

How the class decisions apply here (owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None (no immobilized enzyme,
no surface, no electrode). Qualitative statements keep the existing vocabulary. Direction and strength of a stated share or ratio:
literature_product_distribution_direction (the share of the claimed product, larger is stronger); controls, relaxation, signal-to-noise and the rest lower the WEIGHT only.
One record states the share of ONE named species (the identity block's partner); the other species of the reaction are other records of the same experiment.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads and
whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
RELAXATION_FULL_T1 5 -> RELAXATION_ZERO_T1 1 (the delay over the longest T1, when the paper states both), judged on the magnetization not recovered, exp(-delay / T1).
  Q1 integrals that are not in proportion to the amounts: a nucleus that relaxes slowly is only partly recovered between scans, so its species is under-counted against
  a fast-relaxing one and the shares are biased. Q2 general: quantitative NMR practice is a delay of at least five times the longest T1 of the integrated nuclei (99.3 percent
  of the magnetization back after a 90 degree pulse; Bharti and Roy 2012, Trends Anal Chem 35:5, and the qNMR guidance of Pauli and co-workers; from memory, to verify).
  Q3 relative to the paper's own T1, which the record carries when stated. Q4 the physics gives the shape: after a 90 degree pulse the recovered fraction is
  1 - exp(-delay / T1), so a species whose T1 is the longest is under-counted by exp(-delay / T1): 0.7 percent at five T1, 5 percent at three, 14 percent at two, 37 percent at one.
  The degree is linear in that shortfall between the two ends (0.88 at three T1, 0.64 at two). The zero end is a delay equal to the longest T1, where more than a third of
  the slowest species is missing; a paper that states a delay at or below its own longest T1 shows the shares are not quantitative (conflicting). A flip angle below 90 degrees
  (the Ernst angle) allows a shorter delay and is not collected, so the zero end is conservative for such spectra. Q5 the same idea as the other bias curves (a degree linear
  in a bias that grows with the departure from the researched value).
T1_REFERENCE_S 4.0 (the delay alone, when the paper states no T1): the delay over this assumed longest T1, on the same curve, never conflicting.
  Q1 the same bias, when the paper states the delay but not the T1. Q2 practice: the longest T1 of the protons of small metabolites in aqueous buffer, and of the 31P
  of phosphate esters, is about one to a few seconds at the usual fields (from memory); 4 s is the conservative end, so a delay of 20 s is the usual "5 x T1". 13C
  of non-protonated carbons relaxes far more slowly (tens of seconds) and 31P of inorganic phosphate and 19F vary; the record keeps the nucleus as a choice, but a choice carries
  no span, so no criterion rests on it and the one reference value serves all nuclei: a 13C spectrum with a delay of 20 s and no stated T1 is read generously. Q3 absolute (a
  stated delay), and relative to the paper's own T1 when it is stated, which then wins. Q4 a wrong reference moves the degree of a stated delay and is never conflicting (the
  paper's own numbers do not show the standard unmet when the T1 is assumed); the value is an assumption and the degree can reach 0 (supported, degree 0) but not oppose.
  Q5 an assumed reference gives no conflict, as the other criteria whose number has no paper-stated partner.
SNR_FULL 250 -> SNR_ZERO 3 (the signal-to-noise ratio of the smallest integrated signal), judged on the logarithm of the ratio.
  Q1 a minor species whose integral is within the noise: its share and its detection are not a measurement. Q2 general: a signal-to-noise ratio of about 250 gives an
  integration uncertainty below about one percent (Malz and Jancke 2005, J Pharm Biomed Anal 38:813; from memory, to verify), and 3 is the detection limit and 10 the
  quantification limit (ICH Q2; from memory). The zero end is the detection limit: at or below it the signal is not distinguished from the noise. Q3 absolute, for the
  smallest integrated signal the paper states. Q4 the relative error of an integral goes as 1 / (signal-to-noise), so the degree falls by equal steps for equal factors of the
  error: linear in the logarithm of the ratio (0.27 at 10, 0.48 at 25, 0.64 at 50, 0.79 at 100). At the quantification limit the degree is therefore low but not nil; a paper that
  states a ratio at or below 3 for the signal it integrates shows its own share is within the noise (conflicting). Q5 a log scale like the other ratios of the binding assays.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a distribution from one tube, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice). Q3 absolute count; several spectra of one sample are
  technical and the independence fact decides. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (assignment by standards, resolved signals, the denominator and its coverage, the two controls, the equilibrium evidence, the native substrate, the purified
enzyme and the relaxation fact): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to soften.
NOT judged, and why: the field strength and the number of scans (the signal-to-noise ratio carries what they buy); the chemical shifts (the assignment fact carries identity);
the temperature and pH (the claim carries no condition, and the identity block records them); the share value itself (the direction function reads it on its scale).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this method, owner to confirm:
  What does it measure; absolute or relative? The shares of the species of one mixture, read in one spectrum: relative within the spectrum but self-normalising (one
  denominator), and with full relaxation response-factor free, so a share is as absolute as an NMR integral is.
  Is there a reference range we would trust if the paper stated less? Partly: a species is identified by its chemical shift (a structural identity no chromatographic retention
  gives), and a quantitative-NMR share of a major species is reliable under typical practice; the weakness is the minor species and the delays that papers rarely state.
  What does an unstated control or calibration do to the number's meaning? An unstated delay biases the magnitude of a share but rarely the existence of a species; an unstated
  no-enzyme or inactive-enzyme spectrum is the dominant risk of the class: an equilibrium or a spontaneous reaction gives its own distribution without the enzyme, and a
  contaminating enzyme was found in the one real case (the isomerase case, PMC12051542), so what the mixture says about THIS enzyme is open.
  If we assume it is fine and are wrong, how badly does the score mislead? The direction survives a biased share; a mixture produced without the studied enzyme is counted as its
  product: a wrong direction for a weak claim.
  Consistent with the others? Below the KD anchor 0.90 and level with spectro_direct 0.85 for the default.
  default 0.85; species_identity 0.90 (assignment by chemical shift is the usual practice and a structural identity); response_factors 0.80 (the delay is rarely stated and a
  short one biases a share); common_denominator 0.80 (an unassigned signal or a species left out of the total moves every share); background_alternatives 0.75 and
  attribution_supported 0.70 (the main risk of the class, above); equilibrium_state 0.70 (a composition counted as final that was still moving); sampling_basis 0.90 (benign when
  unstated: a single tube is usual for NMR, and the share of a major species varies little); calibration_applicability, assertion_relevance and condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_product_distribution_direction import select_product_distribution_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_distribution_nmr_converted_v1'
CRITERIA_MAP = {'species_identity': ('shares_from_resolved_signals', 'species_assigned_with_standards'), 'response_factors': ('relaxation_delay',),
                'common_denominator': ('denominator_and_coverage',), 'background_alternatives': ('no_enzyme_spectrum',), 'attribution_supported': ('inactive_enzyme_spectrum',),
                'calibration_applicability': ('minor_signal_to_noise',), 'equilibrium_state': ('stable_composition',), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
RELAXATION_FULL_T1 = 5.0  # EXPERT_REVIEW, owner to confirm: delay of at least five times the longest T1 (99.3 percent of the magnetization recovered after a 90 degree pulse; quantitative-NMR practice, from memory, not verified); full agreement from it.
RELAXATION_ZERO_T1 = 1.0  # EXPERT_REVIEW, owner to confirm: a delay equal to the longest T1 leaves 37 percent of the slowest species unrecovered, so the shares are not quantitative (no agreement; conflicting when the paper states both numbers); the degree falls linearly in the unrecovered magnetization exp(-delay / T1) from the full end to here.
T1_REFERENCE_S = 4.0  # EXPERT_REVIEW, owner to confirm, from memory, not verified: longest T1 assumed (seconds) when the paper states the delay and no T1: the conservative end of the T1 of the protons of small metabolites in water and of the 31P of phosphate esters (about one to a few seconds); a delay of 20 s is then five T1. Never conflicting, because the T1 is an assumption.
SNR_FULL = 250.0  # EXPERT_REVIEW, owner to confirm: signal-to-noise ratio of the smallest integrated signal at which the integration uncertainty is below about one percent (Malz and Jancke 2005, from memory, not verified); full agreement from it.
SNR_ZERO = 3.0  # EXPERT_REVIEW, owner to confirm: the detection limit (signal-to-noise 3, ICH Q2, from memory): at or below it the integrated signal is not distinguished from the noise (no agreement; conflicting); the degree rises linearly in the logarithm of the ratio, because the relative error of an integral goes as 1 / (signal-to-noise).
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: a percent is a hundredth; a ratio is already dimensionless; the stated number is the paper's.
    'product_fraction': ('fraction', {'fraction': 1.0, 'percent': 0.01}),
    'product_fraction_ratio': ('dimensionless', {'dimensionless': 1.0}),
    'equilibrium_fraction': ('fraction', {'fraction': 1.0, 'percent': 0.01}),
    'equilibrium_ratio': ('dimensionless', {'dimensionless': 1.0}),
}
RECOVERY_FACTORS = {'fraction': 1.0, 'percent': 0.01}  # FIXED_BY_DEFINITION: the recovery in the unit 'fraction' the sheet takes.
KIND_WITHOUT_EFFECT = 'product_fraction'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'attributed_signal': 'a_product_share_is_the_effect_not_an_attribution_fraction', 'total_signal': 'a_product_share_is_the_effect_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_distribution_nmr_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_distribution_nmr_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment',
                'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "product detected" / "product not detected" / "product not stated" for this class


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _unrecovered(ratio):
    """The share of the magnetization not recovered between scans after a 90 degree pulse, for a delay of ``ratio`` times T1."""
    return math.exp(-ratio)


def _relaxation_degree(ratio):
    """1.0 at RELAXATION_FULL_T1, 0 at RELAXATION_ZERO_T1, linear in the unrecovered magnetization between them (negative below the zero end, above 1 beyond the full end)."""
    return (_unrecovered(RELAXATION_ZERO_T1) - _unrecovered(ratio)) / (_unrecovered(RELAXATION_ZERO_T1) - _unrecovered(RELAXATION_FULL_T1))


def _judge_relaxation(native):
    refs = native['relaxation_refs']
    if native['longest_t1_s'] is not None:      # both numbers are the paper's: a delay at or below the T1 is the paper showing the shares are not quantitative
        degree = _relaxation_degree(native['relaxation_delay_s'] / native['longest_t1_s'])
        return _verdict('conflicting', refs) if degree <= 0 else _verdict('supported', refs, min(1.0, degree))
    degree = _relaxation_degree(native['relaxation_delay_s'] / T1_REFERENCE_S)      # the T1 is an assumption: never conflicting
    return _verdict('supported', refs, min(1.0, max(0.0, degree)))


def _judge_signal_to_noise(native):
    refs = native['signal_to_noise_refs']
    degree = math.log(native['signal_to_noise_minor'] / SNR_ZERO) / math.log(SNR_FULL / SNR_ZERO)
    return _verdict('conflicting', refs) if degree <= 0 else _verdict('supported', refs, min(1.0, degree))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('relaxation_delay', 'relaxation_recorded_for_the_sheet'): _judge_relaxation, ('minor_signal_to_noise', 'signal_to_noise_recorded_for_the_sheet'): _judge_signal_to_noise,
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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'distribution_nmr_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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


def convert_distribution_nmr(graded):
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
        quantity_kind, effect_support = chosen, effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'distribution_nmr_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
    recovery = native['quantities']['total_recovery']
    if recovery['status'] == 'point':
        quantities['recovery'] = _operand(recovery['value'] * RECOVERY_FACTORS[recovery['unit']], 'fraction', 'distribution_nmr_total_recovery:' + ref, recovery['source_refs'], recovery['origin'], 'total_recovery')
    else:
        null_components['recovery'] = 'total_recovery_not_given'
    null_components.update({role: reason for role, reason in NULL_REASONS.items()})
    interpretations = {}
    for sheet_criterion, members in CRITERIA_MAP.items():
        if sheet_criterion == 'equilibrium_state' and not quantity_kind.startswith('equilibrium_'):
            continue      # optional for the two product kinds: a product share claims no equilibrium, so no unknown equilibrium criterion may lower its weight
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
    converted = {'version': VERSION, 'experiment_type': 'distribution_nmr', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
                 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no stated quantity: the experiment's stated yes/no result stands (the spectrum showed the product, or did not), scored like any stated result (literature_direction, the qualitative path)
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs'])}
        if native['interaction'] is not None:
            converted['direction_field_support'] = native['interaction_support']      # the support class of the fact claimed_product_detected, the one field the statement is derived from
    return converted
