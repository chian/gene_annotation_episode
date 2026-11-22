"""Coupling_oxygen_product converter: turns the grader's result into what the A105 reaction_coupling sheet takes (DRAFT 2026-11-22 for the owner to correct; nothing was run).

Hand-built, private to coupling_oxygen_product, deterministic. Input: the result of grade_coupling_oxygen_product.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'reaction_coupling'), the sheet itself (grade_assay run on it), the dependence keys the
merger needs, the qualitative effect when no effect is available, and for every sheet component that an oxygen-and-product coupling cannot honestly fill, the reason it
stays null. The experiment: one enzyme reaction in one vessel; the dissolved oxygen read with an electrode or optode, the claimed product identified and counted by another
measurement over the same interval; the result is the product made per oxygen consumed (one per O2 for CsiD/LhgO), with the oxygen that went to hydrogen peroxide accounted for.

Quantities filled
-----------------
effect            ONE coupling quantity in the anchor unit 'fraction': the productive fraction (the share of the consumed oxygen that ends in the claimed product, the reaction's
                  coefficient applied) or, when no coefficient is available, the bare product per oxygen. The grader gives the candidates (its docstring): the paper's own stated number,
                  or exact arithmetic on its stated numbers (a percent over 100, the reciprocal of an oxygen per product, the product over the oxygen of the two sides in the same kind of
                  unit, the coefficient times the bare ratio), marked origin 'derived'. The one used is chosen by the class order (literature_reaction_coupling_direction.
                  select_coupling_effect, the productive fraction first). quantity_kind of the extraction names its kind ('productive_fraction' or 'stoichiometric_ratio'), which the direction
                  function reads. A value above 1 is not clipped: the stoichiometry criterion judges it (diagnostic), the direction reads it at the strong end.
effect_variance   variance of that effect, in fraction_squared, only for a REPORTED effect with a stated spread: standard_error -> se^2; standard_deviation -> sd^2 / n and only when the
                  replicates criterion is supported; confidence_interval -> not converted. A derived effect has no stated spread and no variance. Otherwise null.
Every other role stays null, with a reason (NULL_REASONS): the amounts of oxygen and product are two measurements kept in the record, not an attribution fraction; no recovery, no
condition pair, no predictions.
qualitative_effect  only when NO effect is available: statement 'interaction_detected' (read "coupled product formation detected"), 'interaction_not_detected' (read "no product formed above the
                  paper's own control or detection limit") or 'interaction_not_stated' (unknown, never opposition), with the refs of the fact that states it; direction_field_support is the
                  quote support of that one fact (coupling_detected_above_control). A stated effect fixes the direction; the statement is then not used. A result stated in words alone counts
                  less than a measured one by the contract's stated_strength (STATED_ONLY_STRENGTH); this converter does not reimplement it.
dependence        analyte_preparation_ref = the enzyme preparation, dataset_ref = the dataset; immobilized_preparation_ref and surface_ref are None (nothing is immobilized; the electrode only
                  delivers a reading).

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
calibration_applicability  electrode_calibration + product_calibration
background_alternatives    oxygen_drift + no_enzyme_oxygen_control
attribution_supported      enzyme_dependence
reporter_specificity       substrate_independent_oxygen + peroxide_accounting   (the oxygen that something other than the claimed reaction used)
product_identity           product_identity
stoichiometry              stoichiometry
matched_windows            same_vessel + window_overlap
assertion_relevance        native_reaction
condition_scope            purified_enzyme
sampling_basis             replicates
variance_correspondence    supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity, matrix_interference) are not selected: no member is measured for them. The thresholds are judged here, not in the grader (it
records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). OWNER RULE (step 3 of
A105_EXPERIMENT_SOP.md): each value is a researched value of THIS method made gradual: a degree of 1.0 up to its full-agreement limit, falling to 0 at its zero-agreement limit on the
scale the judge names (never a step), and conflicting (no degree) at or beyond that limit, where the paper's own numbers show the standard is not met. A value not stated is unknown, never
0 and never opposition; a short count is a partial degree, never conflicting. A sheet criterion that is supported carries the smallest degree of its members that have one. Quote support
(literature_quote_support.apply_support) is applied to each member and lowers the degree of a supported member, never its status. Combined status: any conflicting -> conflicting; else any
unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is not selected.

THE VALUES BELOW ARE A FIRST DRAFT FOR THE OWNER (2026-11-22): every number is EXPERT_REVIEW, owner to confirm, and every literature figure is from the drafter's memory of oxygen-electrode
practice and the oxygenase literature, NOT web-verified, NOT checked against a method paper. The owner's questions are asked of each value (Q1 failure caught, Q2 general or lab-specific,
Q3 absolute or relative, Q4 how badly a wrong value misleads and whether the shape fits, Q5 consistency with the other assays).
-----------------------------------------------------------------------------------------------------------------------------------------
AIR_FULL_LOW_UM 180 / AIR_ZERO_LOW_UM 90 and AIR_FULL_HIGH_UM 400 / AIR_ZERO_HIGH_UM 900, judged on the log of the value (electrode_calibration).
  Q1 a calibration whose stated air-saturated oxygen is not the oxygen of air-saturated buffer at the temperature used: every oxygen rate and amount scales with it, so a wrong value shifts the
  whole ratio by the same factor. Q2 general physics: air-saturated water holds about 400 uM at 5 degrees C, 284 uM at 20, 258 at 25, 214 at 37 degrees C, and salts and glycerol lower it by up to
  about a tenth to a fifth (tables of oxygen solubility, Benson and Krause 1984, from memory); the full window 180 to 400 uM covers 37 degrees C in a salty or glycerol buffer up to near
  5 degrees C. Q3 absolute (the paper states its own temperature and buffer, which the identity block records; the window is wide enough for any usual assay). Q4 the error of the rate is the
  ratio of the used to the true value, so the degree falls on the log scale; the zero ends are half the lowest and twice the highest value (a stated value there is not air-saturated
  buffer, for example pure oxygen or a percent of oxygen); at or beyond them the paper's own number shows the calibration is not the one the field names (conflicting). Q5 a physical
  plausibility ramp of the same kind as the absorbance and enzyme-ratio ramps of spectro_direct.
DRIFT_FULL_PERCENT 5 / DRIFT_ZERO_PERCENT 80, judged on the log of 1 / (1 - share) (oxygen_drift).
  Q1 a rate so small against the electrode drift that the subtracted baseline decides the result. Q2 general: a Clark electrode or an optode drifts by a few percent of a moderate rate at most
  (instrument manuals, from memory); the drift is measured on the same trace and subtracted, so it is easier to correct than a substrate blank, which is a separate reaction. Q3 relative to
  the paper's own rate (the passage states the percent). Q4 the net rate is the test rate minus the drift, so an error in the drift is multiplied by test / net = 1 / (1 - share): 1.05 at 5 percent,
  5 at 80 percent; the degree is linear in the log of that multiplier between the ends; at or beyond 80 percent (the drift is four fifths of the signal) the rate is the baseline's (conflicting).
  Q5 the same multiplier as the no-substrate share below, with the looser zero end because the drift is read from the same trace.
NO_SUBSTRATE_FULL_PERCENT 10 / NO_SUBSTRATE_ZERO_PERCENT 90, judged on the log of 1 / (1 - share) (substrate_independent_oxygen).
  Q1 oxygen taken up by something other than the claimed reaction (the enzyme or its co-substrate reacting with oxygen without the substrate; for CsiD and LhgO the uncoupled uptake that makes oxygen
  uptake alone a weak evidence). Q2 general (inventory section 4): subtracting a small separate blank is accurate; as it approaches the signal the net rate loses its meaning. Q3 relative to the paper's own
  uptake with the substrate (the passage states the percent). Q4 the same multiplier 1 / (1 - share) (1.11 at 10 percent, 10 at 90 percent), the net rate being the difference of two reactions; at or
  beyond 90 percent the net rate is a tenth of the gross and any error of the blank is magnified tenfold (conflicting). Q5 the same shape as the drift, with the stricter ends because the blank is a
  second reaction with its own error.
COUPLING_FRACTION_FULL 1.25 / COUPLING_FRACTION_ZERO 2.0, judged on the log of the productive fraction (stoichiometry).
  Q1 a product or oxygen number that is wrong or from unmatched sides: more product than the oxygen consumed allows (a productive fraction above 1). The CsiD note: values beyond the stoichiometric bounds
  are diagnostics, not clipped; here the diagnostic is carried by the criterion, not by the direction. Q2 general: two independent measurements each good to about 10 percent (an electrode against an
  authentic-standard product assay) differ by up to a quarter at two standard errors (square root of 2 x 10 percent x 2, about 28 percent), so a productive fraction up to 1.25 is within error (from memory,
  from the usual accuracy of an oxygen electrode and a chromatographic calibration). Q3 relative to the paper's own coefficient (a productive fraction is the coefficient times product per oxygen, so the
  bound is 1 whatever the reaction). Q4 an error in a ratio is multiplicative, so the log scale; at 2.0 the product is double what the oxygen allows (conflicting: the paper's own numbers contradict the
  reaction account). A productive fraction below 1 is not judged here: it is the effect itself. Q5 a log ratio like the fold ramps of the other classes.
WINDOW_RATIO_FULL 0.5 / WINDOW_RATIO_ZERO 0.05, judged on the log of the shorter window over the longer (window_overlap).
  Q1 a product accumulated over a long interval set against an oxygen rate read over a short part of the trace (30 minutes against the first 2): the two sides then average over different regimes
  (substrate depletion, enzyme inactivation, a growing uncoupled share). Q2 practice: a product sampled over the whole run against a rate over the linear part is common; both starting at the
  start of the reaction, windows within a factor of two are comparable (from memory); a factor of twenty is not. Q3 relative (the paper's own two lengths; a start time is not collected, so the
  windows are taken to start together, which is the usual case). Q4 the averaged rate of a progress curve bends with the length of the window, so a factor between the lengths is the natural scale; the
  degree falls on the log of the ratio between a factor of two and a factor of twenty; at or beyond twenty the sides are different experiments (conflicting). Q5 the same idea as the series and
  consumption curves of the activity types.
REPLICATES_FULL_CREDIT 3, degree min(1, sqrt(n / 3)) (replicates).
  Q1 a coupling from one experiment, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the
  variance. Q5 exactly the shared replicate rule (owner's rule).
Facts with no number (the controls, the enzyme dependence, the peroxide accounting, the product identity and calibration, the same vessel, the native substrate and the purified enzyme): the paper's own
statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the oxygen and product amounts and rates themselves (the
effect already carries them; an amount has no common scale); the peroxide share (a stated share shows the accounting was done, which the criterion reads; its closure against the product would need
both numbers at once and is a grader gap, below); the temperature and pH (the claim carries no condition and the identity block records them).
Grader gaps (facts that would sharpen the judgement but are not collected; adding them changes the grader, form and passages and needs a real-model run): the start times of the two windows; the
oxygen balance (product plus peroxide plus water against the oxygen consumed) as one closure number; the electrode's response time and the chamber's oxygen leak; the oxygen consumption large enough
against the noise as a number of its own.

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this experiment, decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? A dimensionless product per oxygen (or a productive fraction) from two separate measurements; absolute, but each side needs its own calibration (the electrode,
  the product standard) and the sides must belong together (one vessel, one window).
  Is there a reference range we would trust if the paper stated less? Partly: a monooxygenase or dioxygenase has an expected stoichiometry (one product per O2 for CsiD/LhgO), which makes a stated ratio near
  it plausible, but oxygen uptake alone can be uncoupled chemistry, so a ratio without an identified product is weak. Not as firm as a KD range.
  What does an unstated control or calibration do to the number's meaning? An unstated electrode calibration and drift correction are routine and small (benign); an unstated product identity is the dominant false
  positive (the oxygen goes elsewhere and the product is inferred); unmatched vessels or windows make the ratio uninterpretable; an unstated no-substrate control or peroxide accounting leaves oxygen used by something
  else (a real gap, often omitted).
  If we assume it is fine and are wrong, how badly does the score mislead? For identity, windows and side consumption badly (the ratio is of unrelated numbers); for calibration and drift, by a factor only.
  Consistent with KD? Below it: default 0.80 (two measurements to match, against one for KD); the sheet criteria that guard against a false coupling are lower (product_identity 0.55, matched_windows 0.65,
  reporter_specificity 0.65); the benign ones are higher (calibration_applicability 0.85, background_alternatives 0.80, sampling_basis 0.90). stoichiometry, attribution_supported, assertion_relevance and
  condition_scope take the default.
"""
from math import log, sqrt

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_reaction_coupling_direction import select_coupling_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_coupling_oxygen_product_converted_v1'
CRITERIA_MAP = {'calibration_applicability': ('electrode_calibration', 'product_calibration'), 'background_alternatives': ('oxygen_drift', 'no_enzyme_oxygen_control'),
                'attribution_supported': ('enzyme_dependence',), 'reporter_specificity': ('substrate_independent_oxygen', 'peroxide_accounting'), 'product_identity': ('product_identity',),
                'stoichiometry': ('stoichiometry',), 'matched_windows': ('same_vessel', 'window_overlap'), 'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',),
                'sampling_basis': ('replicates',)}
PERCENT = 100.0                # FIXED_BY_DEFINITION: a percent is a hundredth.
AIR_FULL_LOW_UM = 180.0        # EXPERT_REVIEW, owner to confirm: lowest air-saturated oxygen of a usual assay (37 degrees C in a salty or glycerol buffer, about 200 uM less a tenth); full agreement from it up to AIR_FULL_HIGH_UM. From memory, not verified.
AIR_ZERO_LOW_UM = 90.0         # EXPERT_REVIEW, owner to confirm: half the lowest; a stated value at or below it is not air-saturated buffer (no agreement); the degree rises linearly in the log of the value from here to AIR_FULL_LOW_UM (the rate scales with the assumed value).
AIR_FULL_HIGH_UM = 400.0       # EXPERT_REVIEW, owner to confirm: air-saturated water at 5 degrees C holds about 400 uM; full agreement up to it. From memory, not verified.
AIR_ZERO_HIGH_UM = 900.0       # EXPERT_REVIEW, owner to confirm: about twice the 0 degree C value; a stated value at or beyond it is not air-saturated buffer (no agreement); the degree falls linearly in the log of the value from AIR_FULL_HIGH_UM to here.
DRIFT_FULL_PERCENT = 5.0       # EXPERT_REVIEW, owner to confirm: drift of an electrode or optode at most a few percent of a moderate rate; full agreement up to it (the net rate then amplifies a drift error by 1.05).
DRIFT_ZERO_PERCENT = 80.0      # EXPERT_REVIEW, owner to confirm: at four fifths of the rate the net rate is a fifth of the gross and a drift error is multiplied five-fold (no agreement); the degree falls linearly in the log of 1 / (1 - share) from DRIFT_FULL_PERCENT to here.
NO_SUBSTRATE_FULL_PERCENT = 10.0   # EXPERT_REVIEW, owner to confirm: oxygen uptake without the substrate at most a tenth of the uptake with it; full agreement up to it (inventory section 4; the multiplier 1 / (1 - share) is 1.11). From memory, not verified.
NO_SUBSTRATE_ZERO_PERCENT = 90.0   # EXPERT_REVIEW, owner to confirm: at nine tenths the net rate is a tenth of the gross and a blank error is multiplied ten-fold (no agreement); the degree falls linearly in the log of 1 / (1 - share) from NO_SUBSTRATE_FULL_PERCENT to here.
COUPLING_FRACTION_FULL = 1.25  # EXPERT_REVIEW, owner to confirm: a productive fraction up to a quarter above the stoichiometric bound of 1 is within the error of an oxygen electrode against a calibrated product assay (about 10 percent each, two standard errors); full agreement up to it. From memory, not verified.
COUPLING_FRACTION_ZERO = 2.0   # EXPERT_REVIEW, owner to confirm: twice the product that the oxygen consumed allows: the numbers contradict the reaction account (no agreement); the degree falls linearly in the log of the fraction from COUPLING_FRACTION_FULL to here.
WINDOW_RATIO_FULL = 0.5        # EXPERT_REVIEW, owner to confirm: the shorter window at least half of the longer (both started with the reaction): comparable averages; full agreement from it.
WINDOW_RATIO_ZERO = 0.05       # EXPERT_REVIEW, owner to confirm: the shorter window a twentieth of the longer: the two sides average over different regimes (no agreement); the degree falls linearly in the log of the ratio from WINDOW_RATIO_FULL to here.
REPLICATES_FULL_CREDIT = 3     # EXPERT_REVIEW, owner to confirm: number of independent experiments that gets full credit. Gradual: below it the degree is sqrt(n / 3) (owner rule: replicates mean precision in every assay; 1 -> about 0.58, 2 -> about 0.82, full from three); never conflicting for a stated count.
UNIT_FACTORS = {'percent': 1.0 / PERCENT, 'fraction': 1.0, 'mol/mol': 1.0}   # FIXED_BY_DEFINITION: the spread's unit to the anchor unit 'fraction'
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "coupled product formation detected" / "no product formed above the paper's own control or detection limit" / "not stated"
KIND_WITHOUT_EFFECT = 'productive_fraction'   # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'a_coupling_has_no_matrix_recovery_measurement', 'attributed_signal': 'oxygen_and_product_are_two_measurements_not_an_attribution_fraction',
                'total_signal': 'oxygen_and_product_are_two_measurements_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_coupling_record',
                'condition_reference': 'no_matched_nuisance_condition_response_in_a_coupling_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment',
                'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError('a ' + status + ' judgement needs support refs')
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _linear(value):
    """The identity scale, for a quantity whose error is additive."""
    return value


def _degree(value, full, zero, scale=_linear):
    """1.0 at ``full`` (or beyond it), falling linearly in ``scale`` to 0 at ``zero`` (the limits may lie on either side of each other); None at or beyond ``zero``.
    ``scale`` is monotone, so the side test is made on the value itself (before a log could see a value at or below 0)."""
    if (value - zero) * (full - zero) <= 0:
        return None
    return min(1.0, (scale(value) - scale(zero)) / (scale(full) - scale(zero)))


def _graded(refs, degree):
    return _verdict('conflicting', refs) if degree is None else _verdict('supported', refs, degree)


def _multiplier(percent):
    """The log of the multiplier 1 / (1 - share) that a blank or drift of ``percent`` of the rate gives to an error of its own (net = gross - blank)."""
    return -log(1.0 - percent / PERCENT)


def _judge_air_saturated(native):
    value = native['air_saturated_uM']
    if value < AIR_FULL_LOW_UM:
        degree = _degree(value, AIR_FULL_LOW_UM, AIR_ZERO_LOW_UM, log)
    elif value > AIR_FULL_HIGH_UM:
        degree = _degree(value, AIR_FULL_HIGH_UM, AIR_ZERO_HIGH_UM, log)
    else:
        degree = 1.0
    return _graded(native['air_saturated_refs'], degree)


def _judge_drift(native):
    return _graded(native['drift_refs'], _degree(native['drift_percent'], DRIFT_FULL_PERCENT, DRIFT_ZERO_PERCENT, _multiplier))


def _judge_no_substrate(native):
    return _graded(native['no_substrate_refs'], _degree(native['no_substrate_percent'], NO_SUBSTRATE_FULL_PERCENT, NO_SUBSTRATE_ZERO_PERCENT, _multiplier))


def _judge_stoichiometry(native):
    return _graded(native['coupling_fraction_refs'], _degree(native['coupling_fraction'], COUPLING_FRACTION_FULL, COUPLING_FRACTION_ZERO, log))


def _judge_windows(native):
    return _graded(native['window_refs'], _degree(native['window_ratio'], WINDOW_RATIO_FULL, WINDOW_RATIO_ZERO, log))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated: the count alone does not say independent experiments (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, sqrt(native['replicate_count'] / REPLICATES_FULL_CREDIT)))      # precision of the mean, see REPLICATES_FULL_CREDIT


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('electrode_calibration', 'air_saturated_recorded_for_the_sheet'): _judge_air_saturated, ('oxygen_drift', 'drift_recorded_for_the_sheet'): _judge_drift,
          ('substrate_independent_oxygen', 'no_substrate_recorded_for_the_sheet'): _judge_no_substrate, ('stoichiometry', 'stoichiometry_recorded_for_the_sheet'): _judge_stoichiometry,
          ('window_overlap', 'windows_recorded_for_the_sheet'): _judge_windows, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _stated_effect(candidate, quantity, ref):
    """The grader's candidate of ``quantity`` as an effect operand in the anchor unit 'fraction' (its 'support' is the extraction's), or None when there is none."""
    if candidate is None:
        return None
    return _operand(candidate['value'], 'fraction', 'coupling_oxygen_product_' + quantity + ':' + ref, candidate['refs'], candidate['origin'], candidate['component'], candidate['support'])


def _variance(graded, candidate):
    """Return (variance in fraction_squared or None, reason or None, refs) of the spread of the chosen REPORTED effect."""
    native = graded['native']
    if candidate['spread'] is None:
        return None, 'derived_effect_has_no_stated_spread', []
    spread = native['quantities'][candidate['spread']]
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, candidate['spread'] + '_not_given', []
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


def convert_coupling_oxygen_product(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {quantity: _stated_effect(candidate, quantity, ref) for quantity, candidate in native['effect_candidates'].items()}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_coupling_quantity_given_or_derivable_from_stated_numbers'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_coupling_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = chosen, effect['support']
        variance, variance_reason, variance_refs = _variance(graded, native['effect_candidates'][chosen])
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, 'fraction_squared', 'coupling_oxygen_product_' + chosen + '_variance:' + ref, variance_refs, 'derived', native['effect_candidates'][chosen]['spread'])
    null_components.update(NULL_REASONS)
    interpretations = {}
    for sheet_criterion, members in CRITERIA_MAP.items():
        # the support of the quotes (kept by the grader) gives or lowers the degree of a supported member; it never changes a status
        graded_members = [apply_support(_criterion(graded, m), native['support'][m]) for m in members if graded['criteria'][m]['status'] != 'not_applicable']
        if not graded_members:
            continue
        statuses = [m['status'] for m in graded_members]
        status = 'conflicting' if 'conflicting' in statuses else 'unknown' if 'unknown' in statuses else 'supported'
        refs = list(dict.fromkeys(r for m in graded_members for r in m['support_refs']))
        interpretations[sheet_criterion] = {'status': status, 'support_refs': refs if status == 'supported' else []}
        degrees = [m['degree'] for m in graded_members if 'degree' in m]
        if status == 'supported' and degrees:
            interpretations[sheet_criterion]['degree'] = min(degrees)      # the weakest member: a degree of a member is not averaged away
    if quantities['effect_variance'] is not None:
        interpretations['variance_correspondence'] = {'status': 'supported', 'support_refs': quantities['effect_variance']['source_refs']}
    extraction = {'version': INPUT_VERSION, 'assay_type': 'reaction_coupling', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['analyte_preparation_ref'], 'immobilized_preparation_ref': None, 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    result = {'version': VERSION, 'experiment_type': 'coupling_oxygen_product', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no coupling number: the experiment's stated yes/no result stands (owner, 2026-11-22), scored like any stated result (literature_direction, the qualitative path)
        result['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs'])}
        if native['interaction'] is not None:
            result['direction_field_support'] = native['interaction_support']      # the support class of the fact coupling_detected_above_control, the one field the statement is derived from
    return result
