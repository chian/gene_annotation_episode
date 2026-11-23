"""Endpoint_optical_plateau converter: turns the grader's result into what the A105 endpoint_conversion sheet takes. DRAFT 2026-11-22, owner to correct.

Hand-built, private to endpoint_optical_plateau, deterministic. Input: the result of grade_endpoint_optical_plateau. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'endpoint_conversion'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for every
sheet component that an optical end point cannot honestly fill, the reason it stays null. It copies the structure of the spectro_direct converter and
uses the endpoint_conversion class core (literature_endpoint_conversion_direction, ENDPOINT_EFFECT_ORDER, ENDPOINT_STRENGTH_ANCHORS).

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: the conversion net of the paper's own control (conversion_difference, fraction), the
                  conversion as stated (conversion_fraction, fraction), the time to the plateau (completion_time, min) or the product amount (endpoint_amount, uM).
                  Several may be stated; the one used is the best-determined, in the class order ENDPOINT_EFFECT_ORDER
                  (literature_endpoint_conversion_direction.select_endpoint_effect). A stated value in another unit of the record's vocabulary is multiplied
                  by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION: percent to fraction, s and h to min, nM and mM to uM): the value is the paper's, only
                  its unit spelling changes. A conversion above complete conversion (more than 1 as a fraction, for example a stated 104 percent) is the paper's
                  own reading error of a plateau, not an effect on a scale that ends at 1: it is not used as the effect (null reason
                  'conversion_above_complete_conversion_is_not_an_effect'); the other stated quantities or the qualitative statement then decide. No completion
                  time ratio is filled: this method states one time to plateau, and a comparison of two times is the time-course-completion type's.
                  quantity_kind of the extraction names the kind of the effect (KIND_OF_QUANTITY), which the direction function reads.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery, attributed signal/total signal, condition test/reference, the assertion and
alternative predictions.
qualitative_effect  only when NO effect is filled and the paper states whether it saw conversion above its own control: statement
                  'interaction_detected' (read "conversion detected") or 'interaction_not_detected' (read "conversion not detected"), with the refs of the fact
                  that states it, and direction_field_support taken from that fact's quote support. A stated effect fixes the direction; the statement is then
                  not used. The result stated in words alone counts less than a measured one by the contract's stated_strength: not re-implemented here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
measurement_identity       readout_stated
calibration_applicability  calibration_basis + calibration_agreement + signal_linear_range
matrix_interference        inner_filter_check
background_alternatives    baseline_control + baseline_level
attribution_supported      enzyme_dependence
endpoint_alignment         plateau_reached + control_same_window
conversion_denominator     initial_substrate_determined + conversion_within_full_scale
product_identity           product_identity
sampling_basis             replicates
assertion_relevance        native_reaction
condition_scope            purified_enzyme
variance_correspondence    supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps
each such criterion and reason to its judgement). Each judgement is a researched value of THIS method made gradual (SOP step 3): full agreement at the
researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the method gives (never a step),
unknown when the paper states nothing, never conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper itself shows
against the standard). A sheet criterion that is supported carries the smallest degree of its members that have one. Quote support
(literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined status: any conflicting ->
conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is not
selected. Every sheet criterion of the class has a counterpart except those the sheet marks optional and this method cannot say anything about.

How the class decisions apply here (owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None. Qualitative
statements keep the existing vocabulary. Direction and strength of a stated conversion: literature_endpoint_conversion_direction (larger is stronger for the
conversion and the amount, smaller for the time); controls, blanks, the plateau and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value
misleads and whether the shape fits, Q5 consistency with the other assays). Every literature statement is from memory and not verified; every number is
EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
BASELINE_FULL_RATIO 0.05 -> BASELINE_ZERO_RATIO 1.0, judged linearly on the ratio of the control to the test (the control conversion over the test
conversion, and the no-enzyme signal change over the test signal change; the worse of the two stated ones counts).
  Q1 a plateau signal that is mostly the substrate's own drift (autohydrolysis, photobleaching, spontaneous reduction or oxidation of the chromophore,
  light-induced fluorescence change) and not the enzyme's. Q2 general: an end point is a difference of two reads, so the share of the signal the
  control already shows is the share of the signal the subtraction (or its omission) can mislead; a few percent is within the reading error of one end
  point (pipetting and the reader, from memory). Q3 relative to the paper's own test value, which the grader records beside the control: right.
  Q4 the share of the signal that is not the enzyme's rises in proportion to the ratio, so the degree is linear in it; at a ratio of 1 the control
  shows as much as the test and no enzyme-dependent signal is left (the SOP's "no larger than the paper's own control": conflicting). Q5 the same idea as
  the consumed-share ramp of spectro_direct: a bias that grows with the departure from the researched value.
CALIBRATION_FULL_FACTOR 1.15 -> CALIBRATION_ZERO_FACTOR 2.0, judged linearly on |ln r|, r the full-conversion signal change over the one the extinction
coefficient predicts (extinction coefficient times path length times starting substrate concentration).
  Q1 a full-conversion reference that does not agree with the paper's own extinction coefficient, path length and substrate concentration: one of the
  three is wrong, or the reaction does not go to the stated product. Q2 general: the agreement of a calibration with its prediction is limited by
  pipetting of the substrate (a few percent), the path length of a plate (several percent, and about a factor of 2 when a plate path length is taken as
  1 cm), and the dependence of the extinction coefficient on pH and temperature (several percent for NADH at 340 nm, large for a nitrophenol near its pKa),
  from memory; about 15 percent either way is the practical agreement. Q3 relative to the paper's own prediction, which the grader records: right.
  Q4 a ratio and its inverse are equally wrong, so the ramp is on the log; the zero end is a factor of 2, where the conversion read from the signal is off
  by as much as the signal itself (conflicting, because the paper's own numbers disagree). Q5 a log-ratio ramp like the enzyme-ratio ramp of spectro_direct.
FULL_SCALE_FULL_RATIO 1.10 -> FULL_SCALE_ZERO_RATIO 1.5, judged linearly on the test signal change over the full-conversion signal change.
  Q1 a test signal change larger than complete conversion allows: a conversion over 100 percent, which shows the signal is not only the stated reaction
  (a side reaction, turbidity or precipitation, drift) or the denominator is wrong. Q2 general: the ratio cannot exceed 1 physically; two separate reads
  each with a few percent error, plus the baseline, give up to about 10 percent of overshoot (from memory). Q3 relative to the paper's own full-conversion
  change, which the grader records: right. Q4 one-sided, linear in the ratio, because the share of the signal that is not conversion grows in proportion; at
  1.5 half again as much signal as complete conversion can give is not a conversion of this substrate (conflicting). A ratio far BELOW 1 is not judged:
  a small conversion is a result the strength scale reads, not a fault of the experiment. Q5 one-sided like the baseline ramp.
ABSORBANCE_FULL 1.0 -> ABSORBANCE_ZERO 3.0, STRAY_LIGHT 0.01, judged on the bias of the apparent absorbance.
  Q1 Beer-Lambert fails at high absorbance: stray light puts a floor under the transmitted intensity, the apparent absorbance bends over and an absorbance
  change (here the plateau height) is underestimated, so the conversion read from it is too low. Q2 general: keep the absorbance below about 1
  (instrument manuals and photometry texts), from memory; a stray light of 1 percent is the conservative end of the instruments in use. Q3 absolute
  (absorbance units), and the grader records the highest absorbance of the paper itself. Q4 the apparent absorbance is -log10((10^-A + s) / (1 + s)), so
  the underestimate is about 4 percent at A = 1, 15 percent at 2, 35 percent at 3; the degree is linear in that bias between the two ends. Q5 the same
  judgement as spectro_direct, a private copy.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a conversion from one experiment, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice). Q3 absolute count. Q4 precision
  of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the controls, the same time of the control, the calibration basis, the inner-filter check, the enzyme dependence, the plateau, the
substrate determination, the product identity, the native substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is
conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the extinction coefficient's value (it is the paper's own
constant, and its agreement with the full-conversion reference is judged above); the time to plateau (a bare time depends on the enzyme loaded; it is only
an effect, on its own scale); the pH and the temperature (the claim carries no condition, and the identity block records the temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this
method, owner to confirm:
  What does it measure; absolute or relative? The share of the substrate converted at the end of a continuous optical trace. Absolute only through a
  calibration: an extinction coefficient and a path length, or a full-conversion reference. Without either, the signal change is in instrument units and a
  fraction cannot be read from it.
  Is there a reference range we would trust if the paper stated less (as for KD)? Only for the common chromophores (NAD(P)H 6220 M^-1 cm^-1 at 340 nm,
  p-nitrophenol at 405 nm at a stated pH, from memory): the extinction coefficient is then known to a few percent; for a fluorescence readout there is none
  (the gain and the plate are the paper's own).
  What does an unstated control or calibration do to the number's meaning? An unstated baseline is the main false positive of a small signal (drift is
  usually small against a large signal, but the grader cannot tell which this is); an unstated full-conversion reference or extinction coefficient leaves the
  fraction uninterpretable for a fluorescence trace and a few percent off for a common chromophore. A plateau alone does not show completion (it is also
  where an enzyme has died, a product inhibits or an equilibrium lies), which is why the plateau and the calibration are separate questions.
  If we assume it is fine and are wrong, how badly does the score mislead? A baseline or drift counted as conversion gives a false positive, and a wrong
  calibration gives a wrong magnitude; both are worse than a KD whose size alone is wrong, and a plateau read as completion overstates the conversion.
  Consistent with KD and the other types? Below spectro_direct (0.85: a continuous trace shows its own linearity and a stated rate) and at the fluorogenic
  level or a little under it: an end point is one number with no trace to check. default 0.75; calibration_applicability 0.65 (an unstated calibration
  leaves a signal change that is not a conversion); background_alternatives 0.65 (the baseline is what separates conversion from drift); attribution_supported
  0.70 and product_identity 0.65 (a chromophore change names a reaction only when the product is identified, and a plateau is not completion); matrix_interference
  0.70 (inner filter and quenching bend the signal at high substrate); sampling_basis 0.85 (triplicate practice is usual and benign). measurement_identity,
  endpoint_alignment, conversion_denominator, assertion_relevance and condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_conversion_direction import select_endpoint_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_endpoint_optical_plateau_converted'
CRITERIA_MAP = {'measurement_identity': ('readout_stated',), 'calibration_applicability': ('calibration_basis', 'calibration_agreement', 'signal_linear_range'),
                'matrix_interference': ('inner_filter_check',), 'background_alternatives': ('baseline_control', 'baseline_level'), 'attribution_supported': ('enzyme_dependence',),
                'endpoint_alignment': ('plateau_reached', 'control_same_window'), 'conversion_denominator': ('initial_substrate_determined', 'conversion_within_full_scale'),
                'product_identity': ('product_identity',), 'sampling_basis': ('replicates',), 'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
BASELINE_FULL_RATIO = 0.05  # EXPERT_REVIEW, owner to confirm: a control showing up to about 5 percent of the test is within the reading error of one end point (pipetting and reader, from memory); full agreement up to it.
BASELINE_ZERO_RATIO = 1.0  # EXPERT_REVIEW, owner to confirm: a control as large as the test leaves no enzyme-dependent signal (the paper's own control shows as much as the test: no agreement, conflicting); the degree falls linearly in the ratio, because the share of the signal that is not the enzyme's grows in proportion.
CALIBRATION_FULL_FACTOR = 1.15  # EXPERT_REVIEW, owner to confirm: the full-conversion signal agrees with the extinction coefficient times path length times substrate concentration within about 15 percent (pipetting, plate path length, pH and temperature dependence of the extinction coefficient, from memory); full agreement within this factor either way.
CALIBRATION_ZERO_FACTOR = 2.0  # EXPERT_REVIEW, owner to confirm: a factor of 2 off (a plate path length taken as 1 cm is about this much) means the extinction coefficient, the path length, the substrate amount or the reaction is wrong (no agreement, conflicting); the degree falls linearly in |ln ratio| from CALIBRATION_FULL_FACTOR to here.
FULL_SCALE_FULL_RATIO = 1.10  # EXPERT_REVIEW, owner to confirm: two separate reads and the baseline each carry a few percent, so a test signal up to about 10 percent over complete conversion is still within the reading error (from memory); full agreement up to it.
FULL_SCALE_ZERO_RATIO = 1.5  # EXPERT_REVIEW, owner to confirm: half again as much signal as complete conversion can give is not a conversion of this substrate (a side reaction, turbidity or a wrong denominator; no agreement, conflicting); the degree falls linearly in the ratio from FULL_SCALE_FULL_RATIO to here. A ratio below 1 is not judged.
ABSORBANCE_FULL = 1.0  # EXPERT_REVIEW, owner to confirm: keep the absorbance at most about 1 (photometry practice, from memory); full agreement up to it (the apparent-absorbance bias there is about 4 percent at 1 percent stray light).
ABSORBANCE_ZERO = 3.0  # EXPERT_REVIEW, owner to confirm: at an absorbance of 3 a stray light of 1 percent loses about a third of the signal (no agreement); the degree falls linearly in the bias of the apparent absorbance from the full end to here.
STRAY_LIGHT = 0.01  # EXPERT_REVIEW, owner to confirm: the fraction of stray light in the transmitted intensity; 1 percent is the conservative end of the spectrophotometers and plate readers in use (a good UV-visible instrument has 0.1 percent or less).
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
FULL_CONVERSION = 1.0  # FIXED_BY_DEFINITION: complete conversion is a fraction of 1, the end of the scale (ENDPOINT_STRENGTH_ANCHORS 'maximum'); a stated conversion above it is not used as the effect.
MINUTES_PER_HOUR = 60.0  # FIXED_BY_DEFINITION.
# The anchor unit of each effect quantity (literature_row_contract.ENDPOINT_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (a percent is a hundredth; 60 s is 1 min; 1 h is 60 min; 1 nM is 1e-3 uM; 1 mM is 1e3 uM); the stated number is the paper's.
    'conversion_difference': ('fraction', {'percent': 0.01, 'fraction': 1.0}),
    'conversion_fraction': ('fraction', {'percent': 0.01, 'fraction': 1.0}),
    'completion_time': ('min', {'s': 1.0 / SECONDS_PER_MINUTE, 'min': 1.0, 'h': MINUTES_PER_HOUR}),
    'endpoint_amount': ('uM', {'nM': 1.0e-3, 'uM': 1.0, 'mM': 1.0e3}),
}
FRACTION_KINDS = ('conversion_difference', 'conversion_fraction')
# The record field that states each effect quantity (its spread field is the name plus '_spread').
EFFECT_FIELD = {'conversion_difference': 'net_conversion_percent', 'conversion_fraction': 'conversion_percent', 'completion_time': 'time_to_plateau', 'endpoint_amount': 'product_amount'}
# The quantity_kind (QUANTITY_KINDS['endpoint_conversion']) that names the kind of each effect quantity; literature_endpoint_conversion_direction.ENDPOINT_QUANTITY_OF_KIND reads it back.
KIND_OF_QUANTITY = {'conversion_difference': 'conversion_difference', 'conversion_fraction': 'conversion_fraction', 'completion_time': 'completion_time', 'endpoint_amount': 'endpoint_amount'}
KIND_WITHOUT_EFFECT = 'conversion_fraction'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'an_optical_plateau_has_no_matrix_recovery_measurement', 'attributed_signal': 'an_optical_plateau_is_not_an_attribution_fraction', 'total_signal': 'an_optical_plateau_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_an_optical_plateau_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_optical_plateau_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENT = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected'}   # read "conversion detected" / "conversion not detected" for this class


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


def _judge_baseline(native):
    ratios = [ratio for ratio in (native['control_over_test'], native['baseline_over_signal']) if ratio is not None]
    return _graded(native['baseline_refs'], *((ratio, BASELINE_FULL_RATIO, BASELINE_ZERO_RATIO) for ratio in ratios))


def _judge_calibration_agreement(native):
    return _graded(native['calibration_refs'], (abs(math.log(native['full_over_expected'])), math.log(CALIBRATION_FULL_FACTOR), math.log(CALIBRATION_ZERO_FACTOR)))


def _judge_full_scale(native):
    return _graded(native['full_scale_refs'], (native['signal_over_full'], FULL_SCALE_FULL_RATIO, FULL_SCALE_ZERO_RATIO))


def _judge_absorbance(native):
    return _graded(native['absorbance_refs'], (_apparent_absorbance_bias(native['absorbance_max']), _apparent_absorbance_bias(ABSORBANCE_FULL), _apparent_absorbance_bias(ABSORBANCE_ZERO)))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('baseline_level', 'baseline_level_recorded_for_the_sheet'): _judge_baseline, ('calibration_agreement', 'calibration_agreement_recorded_for_the_sheet'): _judge_calibration_agreement,
          ('conversion_within_full_scale', 'full_scale_recorded_for_the_sheet'): _judge_full_scale, ('signal_linear_range', 'absorbance_recorded_for_the_sheet'): _judge_absorbance,
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
    field = EFFECT_FIELD[quantity]
    operand = native['quantities'][field]
    if operand['status'] != 'point':
        return None
    unit, factors = UNIT_FACTORS[quantity]
    return _operand(operand['value'] * factors[operand['unit']], unit, 'endpoint_optical_plateau_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], field, operand['support'])


def _variance(graded, quantity, ref):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of ``quantity``."""
    native = graded['native']
    spread = native['quantities'][EFFECT_FIELD[quantity] + '_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, EFFECT_FIELD[quantity] + '_spread_not_given', []
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


def convert_endpoint_optical_plateau(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    given = {quantity: _stated_effect(native, quantity, ref) for quantity in UNIT_FACTORS}
    beyond = [quantity for quantity in FRACTION_KINDS if given[quantity] is not None and given[quantity]['value'] > FULL_CONVERSION]
    stated = {quantity: None if quantity in beyond else operand for quantity, operand in given.items()}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'conversion_above_complete_conversion_is_not_an_effect' if beyond else 'no_endpoint_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_endpoint_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_QUANTITY[chosen], effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'endpoint_optical_plateau_' + chosen + '_variance:' + ref, variance_refs, 'derived', EFFECT_FIELD[chosen] + '_spread')
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'endpoint_conversion', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'endpoint_optical_plateau', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None and native['conversion'] is not None:      # no usable quantity: the paper's own statement of conversion above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['conversion']], 'support_refs': list(native['conversion_refs'])}
        result['direction_field_support'] = native['conversion_support']
    return result
