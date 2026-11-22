"""Distribution_optical_equilibrium converter: turns the grader's result into what the A105 product_distribution sheet takes.

Hand-built, private to distribution_optical_equilibrium, deterministic. FIRST DRAFT 2026-11-22, owner to confirm; every number below is EXPERT_REVIEW and every
literature figure is from the drafter's memory, NOT web-verified and NOT checked against a method paper. Input: the result of grade_distribution_optical_equilibrium.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'product_distribution'), the sheet itself (grade_assay run on it), the dependence
keys the merger needs, the qualitative effect when no effect is stated, and for every sheet component that an optical equilibrium cannot honestly fill, the reason
it stays null. Built on the structure of the spectro_direct converter (the first type built outside the binding class) and of the distribution_nmr converter (the
class's first type).

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity (literature_row_contract.PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS): the share of the named species
                  in the mixture at equilibrium (equilibrium_fraction, fraction) or the ratio at equilibrium (equilibrium_ratio, dimensionless). An optical plateau gives
                  an equilibrium composition only, so the product-share kinds are never filled. Both may be stated; the one used is the best-determined, in the class order
                  PRODUCT_DISTRIBUTION_EFFECT_ORDER (literature_product_distribution_direction.select_product_distribution_effect). A percent is multiplied by its exact
                  factor 0.01 (UNIT_FACTORS, FIXED_BY_DEFINITION): the value is the paper's, only its unit spelling changes. quantity_kind of the extraction names the kind
                  of the effect, which the direction function reads. A share of exactly 0 is never an effect operand (the extraction refuses a number that is not above 0):
                  "not formed" is the fact claimed_product_detected, handed on as the qualitative effect. An equilibrium constant with a unit has no kind and stays unavailable.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it: standard_error -> se^2;
                  standard_deviation -> sd^2 / n and only when the replicates criterion is supported; confidence_interval and range -> not converted (a confidence
                  interval needs its level and degrees of freedom, a range is no variance). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery (nothing is separated, so no recovery is measured), attributed signal and total signal (the share is
the effect already; keeping it in the effect avoids counting it twice), condition test and reference, the assertion and alternative predictions.
qualitative_effect  only when NO effect is stated: the paper's own statement whether the signal showed the product the experiment tests for. Statement
                  'interaction_detected' (read "product detected"), 'interaction_not_detected' (read "product not detected") or 'interaction_not_stated', with the refs of
                  the fact that states it. direction_field_support is then the quote support of that one fact. A result stated in words alone already counts less than a
                  measured one (the contract's stated_strength); nothing of that is repeated here.
direction_field_support  the quote support of the field that fixes the direction: the chosen effect operand, or the fact claimed_product_detected, or None.
quantity_kind     'equilibrium_fraction' also when no effect is stated: the type always reports an equilibrium, so the sheet's equilibrium_state criterion is required (it is
                  filled below, and an unknown one lowers the weight at its own unknown weight).

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
species_identity          pure_species_spectra (the species are told apart by their spectra only, so the pure-species spectra under the assay conditions are the identity)
response_factors          extinction_coefficient_stated (the extinction coefficient and its wavelength turn the plateau signal into amounts; with the pure spectra it is the
                          calibration of the species' responses)
common_denominator        denominator_and_coverage (every absorbing species accounted for; the constant that of the single step tested, not a composite of coupled equilibria)
calibration_applicability absorbance_range (the detector's linear range)
background_alternatives   no_enzyme_sample
attribution_supported     inactive_enzyme_sample (an equilibrium composition is the same with or without the enzyme, so it is the approach in time of the active enzyme and not
                          of an inactive one that ties the composition to this enzyme)
equilibrium_state         plateau_stability + equilibrium_from_both_sides (the sheet requires it for the two equilibrium kinds, and this type's effect is always one of them)
sampling_basis            replicates
assertion_relevance       native_reaction
condition_scope           purified_enzyme
variance_correspondence   supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity, matrix_interference) are not selected. The thresholds are judged here, not in the grader (it records
facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Each judgement is a
researched value of THIS method made gradual (SOP step 3): full agreement at the researched good value, falling smoothly to zero at a researched no-longer-meaningful
value on the scale the physics of the method gives (never a step), unknown when the paper states nothing, never conflicting for a short count. A value at or beyond a zero
end that the paper itself states is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported carries the smallest degree of its
members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined status: any
conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is not
selected.

How the class decisions apply here (owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None (no immobilized enzyme,
no surface, no electrode). Qualitative statements keep the existing vocabulary. Direction and strength of a stated composition:
literature_product_distribution_direction (the share of the claimed species, larger is stronger); controls, the plateau, the spectra and the rest lower the WEIGHT only. The
composition of an equilibrium does not depend on the enzyme: it shows where the reaction lies, not that this enzyme makes the product, and the attribution criterion with its
controls carries that. One record states the composition as seen from ONE named species (the identity block's partner); the other side is the same measurement.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads and
whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
PLATEAU_CHANGE_FULL_PERCENT 1 -> PLATEAU_CHANGE_ZERO_PERCENT 10 (the change of the signal over the plateau window, in percent of the signal), linear.
  Q1 a "plateau" that is still a point on the way: the composition read from a signal that still moves is not the end state, so the share is biased towards the starting side.
  Q2 general: a reading of a good spectrophotometer repeats to about one percent of the reading in the usual range (instrument practice, from memory), so a change below one
  percent cannot be told from noise and counts as a stable plateau; the window and the rate constant are not collected, so the change over the window stated is the paper's
  own number (the window is the paper's choice, and "less than 1 percent in 30 minutes" is the usual wording). Q3 relative to the signal, which the passage states as a
  percent; right. Q4 the physics gives the least error: for a first-order approach the signal still to come is the change seen in the window divided by 1 - exp(-k t), at least
  the change seen, so the composition is off by at least the percent of the signal that is still moving; the degree is linear in that least error because the error of the
  composition grows in proportion to it. The zero end, ten percent, is a signal still moving by a tenth of itself: the composition is not an equilibrium (conflicting when the
  paper states it). Q5 a bias that grows with the departure from the researched value, as the other bias curves (the share consumed in spectro_direct, the relaxation delay in
  distribution_nmr).
ABSORBANCE_FULL 1.0 -> ABSORBANCE_ZERO 3.0, STRAY_LIGHT 0.01, judged on the bias of the apparent absorbance.
  Q1 Beer-Lambert fails at high absorbance: stray light puts a floor under the transmitted intensity, the apparent absorbance bends over, so the absorbance of the plateau and
  of the fully converted reference (from which the composition is the ratio) are compressed unequally and the share is biased. Q2 general: keep the absorbance below about 1
  (instrument manuals and photometry texts), from memory; a stray light of 1 percent is the conservative end of the instruments in use (a good UV-visible spectrophotometer has
  about 0.1 percent or less, a plate reader more). Q3 absolute (absorbance units), and the grader records the highest absorbance of the paper itself; it is for an absorbance
  reading, a fluorescence intensity is never given here. Q4 the apparent absorbance is -log10((10^-A + s) / (1 + s)), so the shortfall is 1 - A_apparent / A: about 4 percent
  at A = 1, 15 percent at 2, 35 percent at 3; the degree is linear in that bias between the two ends. At or beyond A = 3 a third of the signal is lost (conflicting). The
  composition is a ratio of absorbances and the shortfall partly cancels in the ratio, so the end is conservative. Q5 the same curve as spectro_direct: the physics of the
  detector does not depend on what the absorbance is used for.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 an equilibrium composition from one mixture, whose mixture-to-mixture spread is unseen. Q2 general (triplicate practice). Q3 absolute count; repeated reads of one mixture
  are technical and the independence fact decides. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the pure-species spectra, the species accounted for and the one-step constant, the two controls, the reverse approach and the concentration series, the
native substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to soften.
NOT judged, and why: the wavelength and the extinction coefficient's value (the paper's own constant, stated with its wavelength; a wrong constant would show as an implausible
composition, which the strength scale already reads); how close the composition is to 0 or 1 (an optical signal change near the ends is small, but the paper's own spread
already carries it); the temperature and pH (the claim carries no condition, and the identity block records them).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this method, owner to confirm:
  What does it measure; absolute or relative? Where the equilibrium of the reaction lies, as the share of each species of one mixture. Absolute, because a composition is a state
  function (it is the same from either side and for any catalyst), but it rests on the extinction coefficients of the species, so only as good as those.
  Is there a reference range we would trust if the paper stated less? Partly: the extinction coefficients of the common chromophores (NADH 6220 M^-1 cm^-1 at 340 nm) are well
  known and a spectrophotometer at an absorbance below about 1 is routine; what a paper rarely states is what makes the composition an equilibrium and which species absorb.
  What does an unstated control or calibration do to the number's meaning? An unstated plateau, reverse approach or pure-species spectrum can turn a stalled reaction, a second
  absorbing species or a composite constant into a "composition"; an unstated no-enzyme or inactive-enzyme sample leaves open that the plateau shows nothing about THIS enzyme.
  If we assume it is fine and are wrong, how badly does the score mislead? The direction survives a biased share; a composition counted as the equilibrium of the claimed step that
  was not: a wrong magnitude, and for a weak claim a wrong direction. The species are told apart by their spectra only, so the identity risk is higher than for NMR.
  Consistent with the others? Below the NMR default of 0.85 (no structural identity) and below spectro_direct's 0.85: 0.75.
  default 0.75. species_identity 0.70 (identity by spectrum only: an overlapping species or a contaminant); response_factors 0.85 (the extinction coefficients of the common
  chromophores are known, so an unstated one is read from the literature and off by a factor, not meaningless); common_denominator 0.70 (an unaccounted absorbing species or a
  composite constant moves the share); background_alternatives 0.70 and attribution_supported 0.65 (the equilibrium is the same without the enzyme and a contaminating enzyme was
  found in the one real case of the class, PMC12051542); equilibrium_state 0.65 (the defining evidence of the type: a stalled reaction counted as an equilibrium);
  calibration_applicability 0.85 and sampling_basis 0.85 (benign when unstated: an absorbance below about 1 is routine and triplicates are usual); assertion_relevance and
  condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_product_distribution_direction import select_product_distribution_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_distribution_optical_equilibrium_converted_v1'
CRITERIA_MAP = {'species_identity': ('pure_species_spectra',), 'response_factors': ('extinction_coefficient_stated',), 'common_denominator': ('denominator_and_coverage',),
                'calibration_applicability': ('absorbance_range',), 'background_alternatives': ('no_enzyme_sample',), 'attribution_supported': ('inactive_enzyme_sample',),
                'equilibrium_state': ('plateau_stability', 'equilibrium_from_both_sides'), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
PLATEAU_CHANGE_FULL_PERCENT = 1.0  # EXPERT_REVIEW, owner to confirm: a good spectrophotometer repeats a reading to about one percent (instrument practice, from memory, not verified), so a change of the signal below it over the plateau window cannot be told from noise; full agreement up to it.
PLATEAU_CHANGE_ZERO_PERCENT = 10.0  # EXPERT_REVIEW, owner to confirm: a signal still moving by a tenth of itself over the window leaves the composition off by at least that (for a first-order approach the signal still to come is at least the change seen): not an equilibrium (no agreement; conflicting when the paper states it); the degree falls linearly in the change, because the least error of the composition grows in proportion to it.
ABSORBANCE_FULL = 1.0  # EXPERT_REVIEW, owner to confirm: keep the absorbance at most about 1 (photometry practice, from memory, not verified); full agreement up to it (the apparent-absorbance bias there is about 4 percent at 1 percent stray light).
ABSORBANCE_ZERO = 3.0  # EXPERT_REVIEW, owner to confirm: at an absorbance of 3 a stray light of 1 percent loses about a third of the signal (no agreement); the degree falls linearly in the bias of the apparent absorbance from the full end to here.
STRAY_LIGHT = 0.01  # EXPERT_REVIEW, owner to confirm: the fraction of stray light in the transmitted intensity; 1 percent is the conservative end of the spectrophotometers and plate readers in use (a good UV-visible instrument has 0.1 percent or less), from memory, not verified.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: a percent is a hundredth; a ratio is already dimensionless; the stated number is the paper's.
    'equilibrium_fraction': ('fraction', {'fraction': 1.0, 'percent': 0.01}),
    'equilibrium_ratio': ('dimensionless', {'dimensionless': 1.0}),
}
KIND_WITHOUT_EFFECT = 'equilibrium_fraction'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing): the type always reports an equilibrium, so equilibrium_state stays required
NULL_REASONS = {'recovery': 'an_optical_equilibrium_separates_nothing_so_no_recovery_is_measured', 'attributed_signal': 'a_composition_is_the_effect_not_an_attribution_fraction', 'total_signal': 'a_composition_is_the_effect_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_distribution_optical_equilibrium_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_distribution_optical_equilibrium_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment',
                'effect_degrees_of_freedom': 'no_student_t_model_selected'}
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


def _apparent_absorbance_bias(absorbance):
    """The relative shortfall of the apparent absorbance, -log10((10^-A + s) / (1 + s)), against the true A, for the stray light STRAY_LIGHT."""
    return 1.0 - -math.log10((10.0 ** -absorbance + STRAY_LIGHT) / (1.0 + STRAY_LIGHT)) / absorbance


def _judge_plateau(native):
    return _graded(native['plateau_refs'], (native['plateau_change_percent'], PLATEAU_CHANGE_FULL_PERCENT, PLATEAU_CHANGE_ZERO_PERCENT))


def _judge_absorbance(native):
    return _graded(native['absorbance_refs'], (_apparent_absorbance_bias(native['absorbance_max']), _apparent_absorbance_bias(ABSORBANCE_FULL), _apparent_absorbance_bias(ABSORBANCE_ZERO)))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('plateau_stability', 'plateau_change_recorded_for_the_sheet'): _judge_plateau, ('absorbance_range', 'absorbance_recorded_for_the_sheet'): _judge_absorbance,
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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'distribution_optical_equilibrium_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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


def convert_distribution_optical_equilibrium(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {quantity: _stated_effect(native, quantity, ref) for quantity in UNIT_FACTORS}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_equilibrium_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_product_distribution_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = chosen, effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'distribution_optical_equilibrium_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    converted = {'version': VERSION, 'experiment_type': 'distribution_optical_equilibrium', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
                 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no stated quantity: the experiment's stated yes/no result stands (the signal showed the product, or did not), scored like any stated result (literature_direction, the qualitative path)
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs'])}
        if native['interaction'] is not None:
            converted['direction_field_support'] = native['interaction_support']      # the support class of the fact claimed_product_detected, the one field the statement is derived from
    return converted
