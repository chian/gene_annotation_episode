"""Endpoint_nmr converter: turns the grader's result into what the A105 endpoint_conversion sheet takes. DRAFT, owner to correct.

Hand-built, private to endpoint_nmr, deterministic. Input: the result of grade_endpoint_nmr. Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'endpoint_conversion'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for every sheet component that an NMR end point
cannot honestly fill, the reason it stays null. Built from the structure of literature_spectro_direct_converter.py; the class core is the endpoint_conversion class
(G/literature_endpoint_conversion_direction.py and the class note runs/a105_class_drafts/registration/CLASS_endpoint_conversion.md).

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its kind, chosen by select_endpoint_effect in the class order ENDPOINT_EFFECT_ORDER:
                    conversion_difference  (fraction)  the control-corrected conversion: the paper's own net value, else the stated conversion minus the stated control
                                           conversion (both read at the same time), as an exact subtraction of two stated numbers (origin 'derived', its support the weaker
                                           of the two). A difference at or below zero is not an effect (the test is no better than the control): no effect is filled
                                           and the raw conversion is NOT used instead, because it holds the very background the control measured.
                    conversion_fraction    (fraction)  the stated conversion, used only when the paper states no control conversion (a raw value that cannot be
                                           separated from background is still the paper's number; the weight, not the direction, carries the missing control).
                    endpoint_amount        (uM)        the product concentration from the integrals against an internal standard.
                  Completion time and completion-time ratio are not stated by this type: a time to completion is read from a series of spectra and belongs to the
                  type that samples the reaction over time. A stated value in another unit is converted by its exact factor (FIXED_BY_DEFINITION: percent is a hundredth,
                  mM is 1000 uM); the value is the paper's. quantity_kind names the kind, which the class direction function reads.
effect_variance   variance of that effect in the anchor unit squared, only for conversion_fraction and only when the passage's spread belongs to it: standard_error ->
                  se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported; confidence_interval -> not converted (needs its level and
                  degrees of freedom). A control-corrected difference and an amount carry no stated spread of their own (the control has no spread of its own in the
                  record), so their variance is null: the spread of the raw value is not the spread of the difference.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery, attributed signal/total signal, condition test/reference, the assertion and alternative
predictions.
qualitative_effect  only when NO effect is stated: statement 'interaction_detected' (read "conversion detected"), 'interaction_not_detected' (read "conversion not
                  detected") or 'interaction_not_stated' (read "conversion not stated"), with the refs of the fact conversion_detected_above_control that states it; the
                  direction_field_support is the quote support of that one fact. A stated effect fixes the direction; the statement is then not used. A result stated
                  in words alone already counts STATED_ONLY_STRENGTH of the type's value (the contract's stated_strength): nothing is re-implemented here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives    spontaneous_reaction_control
attribution_supported      enzyme_dependence
product_identity           product_assignment + mass_balance
calibration_applicability  relaxation_delay + signal_to_noise + non_detection_limit   (sensitivity and response: whether the integrals are proportional to the amounts and the
                           signal could be read; the class core table had put the signal-to-noise ratio under variance_correspondence, but that criterion asks whether a
                           VARIANCE belongs to this estimate, which a noise level is not; it is filled below only when a variance was computed)
matrix_interference        signals_resolved
endpoint_alignment         time_alignment
conversion_denominator     integral_denominator
assertion_relevance        native_reaction
condition_scope            purified_enzyme
sampling_basis             replicates
variance_correspondence    supported only when a variance was computed
measurement_identity is not selected (no counterpart here; as in the template). The rule of the SOP: any member conflicting makes the sheet criterion conflicting, else any
unknown makes it unknown, else supported; not_applicable members are dropped; a supported sheet criterion carries the smallest degree of its members that have one. Quote
support (literature_quote_support.apply_support) lowers the degree of a supported member and never changes a status.

The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Each judgement is a researched value of THIS assay made gradual (SOP step 3): full agreement at the researched good value,
falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the assay gives (never a step), unknown when the paper states nothing,
never conflicting for a short count. A value at or beyond its zero end, where the paper's own number shows the standard is not met, is conflicting. Every literature
statement below is from memory, not verified; every number is EXPERT_REVIEW, owner to confirm.

How the class decisions apply here (owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None. Qualitative statements
keep the existing vocabulary. Direction and strength of a stated conversion: literature_endpoint_conversion_direction (larger is stronger, per-quantity anchors);
controls, blanks, alignment and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads and
whether the shape fits, Q5 consistency with the other assays).
-----------------------------------------------------------------------------------------------------------------------------------
RELAXATION_FULL 5 -> RELAXATION_ZERO 1 (delay over the longest T1), judged on the unrecovered share exp(-delay / T1).
  Q1 integrals that are not proportional to the amounts: after a 90-degree pulse a nucleus recovers 1 - exp(-d / T1) of its magnetisation in a delay d, so a slowly
  relaxing signal reads low against a fast one and the conversion is biased. Q2 general: a delay of at least five times the longest T1 (99.3 percent recovered) is the
  usual condition of quantitative NMR (qNMR practice, for example Bharti and Roy 2012; Pauli et al. 2012; from memory); a smaller flip angle allows a shorter delay (not
  asked). Q3 relative to the paper's own T1, which the grader records when stated; when the paper states the delay but no T1 the delay is read against TYPICAL_T1_S
  (below), a stated assumption. Q4 the physics gives the shape: the unrecovered share is 0.007 at 5, 0.018 at 4, 0.05 at 3, 0.14 at 2 and 0.37 at 1; the degree is linear in that
  share between the two ends, so it falls gently at first and faster later. The zero end is a delay as long as T1 (63 percent recovered): the slowest signal reads a third short
  of a fully relaxed one, so an integral ratio can be off by a factor 1.6 and the number is no longer a quantity. With a stated T1 a delay at or below it is conflicting
  (what the paper's own numbers show); with the typical T1 it is only a degree of 0 (the T1 is not the paper's). Q5 the same idea as the bias curves of the other assays: a
  bias that grows with the departure from the researched value.
TYPICAL_T1_S 5 (used only when the delay is stated and the T1 is not).
  Q1 the same. Q2 the longest 1H T1 of a small metabolite in water is a few seconds, up to about 5 s for slowly relaxing isolated protons (acetate, formate and aromatic
  protons can be longer; sugars about 1 to 3 s), from memory. Q3 an assumption, absolute. Q4 it is a judgement for a missing number: 1H and 31P of small molecules; it is
  lenient for 13C and for formate, which relax more slowly, and strict for sugars. The converter cannot read the nucleus (a choice holds no span in the merged record). Q5
  specific to NMR.
SIGNAL_TO_NOISE_FULL 250 -> SIGNAL_TO_NOISE_ZERO 10, judged on the log of the ratio.
  Q1 an integral that is mostly noise. Q2 general: a signal-to-noise ratio of about 250 to 1 gives an integration uncertainty under 1 percent (Malz and Jancke 2005, J Pharm
  Biomed Anal; from memory), and 10 to 1 is the limit of quantification (ICH Q2, from memory), below which a signal is seen but not measured. Q3 absolute, and the paper states
  it for the signal the conversion rests on. Q4 the relative uncertainty of an integral goes as 1 over the ratio, so each tenfold in ratio is tenfold in uncertainty; the degree is
  linear in the log of the ratio, steep where small changes matter. At or below 10 the number is conflicting (a conversion read from a signal under the limit of quantification).
  Q5 a log-ratio ramp like the other ratio judgements of the assays.
WINDOW_FULL 0.05 -> WINDOW_ZERO 1.0 (acquisition time over the end-point time), judged linearly. Used only when the reaction was not stopped before the spectrum.
  Q1 a reaction that runs on during the spectrum: the spectrum averages the conversion over the acquisition window, so it is the conversion at about the middle of the window,
  not at the stated time. Q2 general physics of in-tube NMR kinetics (a series of spectra is time-stamped at the middle of each acquisition), the researched value is a
  judgement: a window under about a twentieth of the time moves the time by under 2.5 percent. Q3 relative to the paper's own time, which the grader records. Q4 the
  relative error of the time is about window / (2 time) for a conversion growing with time, so the degree is linear in window / time from the full end to the zero end where the
  spectrum is the average of the whole reaction and is not an end point (conflicting). A reaction that has reached its plateau is insensitive, which this record cannot show
  (it does not state that the reaction was complete), so a long window over a short time is judged as stated. Q5 a bias that grows with the departure, as above.
DETECTION_LIMIT_FULL_PERCENT 2 -> DETECTION_LIMIT_ZERO_PERCENT 50, judged on the log of the limit. Used only for a result the paper states as not detected.
  Q1 a non-detection from a spectrum that could not have shown a small conversion says little. Q2 general: a minor species at 1 to 2 percent of the major signal is the
  practical floor of 1H NMR at good signal-to-noise (from memory); a limit of half the substrate excludes nothing. Q3 relative to the paper's own limit, which is stated.
  Q4 detection limits live on orders of magnitude, so the degree is linear in the log of the limit; at or beyond 50 percent the non-detection excludes no conversion that matters
  (conflicting, which removes the weight of the opposing result). Q5 specific to a negative result; no other class assay judges one.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a conversion from one reaction, whose reaction-to-reaction spread is unseen. Q2 general (triplicate practice); NMR reactions are often run once, which this makes visible
  as a partial degree and not as a failure. Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the two controls, the enzyme dependence, the product assignment, the mass balance, the resolved signals, the native substrate and the purified enzyme) and
the denominator: the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the
temperature and the pH (the claim carries no condition, and the identity block records the temperature); the enzyme and substrate loadings (NMR needs high amounts by its low
sensitivity; the weight of an unstated purified enzyme and native substrate already carries the realism question); the pulse angle and the repetition time beyond the delay (not asked;
a grader gap listed in the registration note).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this assay, owner to confirm:
  What does it measure; absolute or relative? The share of the substrate converted, read from integrals: an absolute fraction without a response factor or a calibration curve
  (a proton signal is proportional to the number of nuclei), identified by its chemical shift. Is there a reference range we would trust if the paper stated less? Yes for the
  quantity (a share between 0 and 1 against its own control, anchored in the class), no for the acquisition details: how well the integrals are proportional depends on
  details a short methods text often omits (delay, noise). What does an unstated control or calibration do to the number's meaning? An unstated blank matters because NMR
  reactions run at high enzyme and substrate loadings for hours, where spontaneous conversion and a contaminating activity are real (the HFP isomerisation was assigned to a
  contaminating enzyme in the old material); an unstated relaxation delay is usually benign for a ratio of similar protons but can bias by a factor; an unstated denominator is
  benign (the sum of the two integrals of one spectrum is the usual one). If we assume it is fine and are wrong, how badly does the score mislead? The conversion is overstated or
  attributed to the wrong enzyme: less severe than a pull-down band, more than a binding constant's magnitude. Consistent with KD? Level with spectro_direct at the default 0.85.
  default 0.85. background_alternatives 0.75 (the blank is what separates the enzyme from spontaneous chemistry at NMR loadings). attribution_supported 0.75 (a contaminating
  activity at high loading is the HFP kind of error). calibration_applicability 0.80 (delay, noise and detection limit are real ways for integrals to be wrong, and the amounts rest wholly
  on them). conversion_denominator 0.90 (benign when unstated). The rest take the default; sampling_basis takes the default and not 0.90, because an NMR reaction is often run once.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_conversion_direction import select_endpoint_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SUPPORT_WEAKEST_ORDER
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_endpoint_nmr_converted_v1'
CRITERIA_MAP = {'background_alternatives': ('spontaneous_reaction_control',), 'attribution_supported': ('enzyme_dependence',),
                'product_identity': ('product_assignment', 'mass_balance'), 'calibration_applicability': ('relaxation_delay', 'signal_to_noise', 'non_detection_limit'),
                'matrix_interference': ('signals_resolved',), 'endpoint_alignment': ('time_alignment',), 'conversion_denominator': ('integral_denominator',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',), 'sampling_basis': ('replicates',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
MICROMOLAR_PER_UNIT = {'uM': 1.0, 'mM': 1.0e3}  # FIXED_BY_DEFINITION: 1 mM is 1000 uM.
RELAXATION_FULL = 5.0  # EXPERT_REVIEW, owner to confirm: delay of at least five times the longest T1 (99.3 percent of the magnetisation recovered) is the usual condition of quantitative NMR (qNMR practice, from memory); full agreement from it.
RELAXATION_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: a delay as long as T1 recovers 63 percent, so the slowest signal reads a third short of a fully relaxed one and an integral ratio can be off by a factor 1.6 (no agreement); the degree falls from RELAXATION_FULL linearly in the unrecovered share exp(-delay / T1), because the integral bias is that share.
TYPICAL_T1_S = 5.0  # EXPERT_REVIEW, owner to confirm: the longest 1H T1 of a small metabolite in water, a few seconds up to about 5 s (from memory); used ONLY when the paper states the delay and no T1; an assumption for 1H and 31P, lenient for 13C and formate, strict for sugars.
SIGNAL_TO_NOISE_FULL = 250.0  # EXPERT_REVIEW, owner to confirm: about 250 to 1 gives an integration uncertainty under 1 percent (Malz and Jancke 2005, from memory); full agreement from it.
SIGNAL_TO_NOISE_ZERO = 10.0  # EXPERT_REVIEW, owner to confirm: 10 to 1 is the limit of quantification (ICH Q2, from memory): below it a signal is seen but not measured (no agreement); the degree falls from SIGNAL_TO_NOISE_FULL linearly in the log of the ratio, because the relative uncertainty of an integral goes as one over the ratio.
WINDOW_FULL = 0.05  # EXPERT_REVIEW, owner to confirm: an acquisition time of at most a twentieth of the end-point time moves the time the spectrum stands for by under 2.5 percent (the spectrum is stamped at the middle of the window); full agreement up to it.
WINDOW_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: an acquisition as long as the time itself averages the whole reaction, so the spectrum is not an end point (no agreement); the degree falls from WINDOW_FULL linearly in acquisition time over end-point time, because the relative error of the time grows with it.
DETECTION_LIMIT_FULL_PERCENT = 2.0  # EXPERT_REVIEW, owner to confirm: a minor species at 1 to 2 percent of the major signal is the practical floor of 1H NMR at good signal-to-noise (from memory); a non-detection with a limit at or under it excludes any conversion that matters; full agreement up to it.
DETECTION_LIMIT_ZERO_PERCENT = 50.0  # EXPERT_REVIEW, owner to confirm: a limit of half the substrate excludes no conversion that matters (no agreement); the degree falls from DETECTION_LIMIT_FULL_PERCENT linearly in the log of the limit, because detection limits are spread over orders of magnitude.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate reactions; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent reactions falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect kind (literature_row_contract.ENDPOINT_STRENGTH_ANCHORS) and the quantity_kind (QUANTITY_KINDS['endpoint_conversion']) that names it.
ANCHOR_UNIT = {'conversion_difference': 'fraction', 'conversion_fraction': 'fraction', 'endpoint_amount': 'uM'}
KIND_WITHOUT_EFFECT = 'conversion_fraction'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'endpoint_nmr_has_no_matrix_recovery_measurement', 'attributed_signal': 'an_nmr_conversion_is_not_an_attribution_fraction', 'total_signal': 'an_nmr_conversion_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_an_endpoint_nmr_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_endpoint_nmr_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "conversion detected" / "conversion not detected" / "conversion not stated" for this class


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


def _unrecovered(ratio):
    """The share of the magnetisation not recovered after a delay of ``ratio`` times T1: exp(-ratio)."""
    return math.exp(-ratio)


def _judge_relaxation(native):
    refs, delay, t1 = native['relaxation_refs'], native['relaxation_delay_s'], native['longest_t1_s']
    full, zero = _unrecovered(RELAXATION_FULL), _unrecovered(RELAXATION_ZERO)
    if t1 is not None:
        return _graded(refs, (_unrecovered(delay / t1), full, zero))      # the paper's own T1: a delay no longer than it is what the paper shows against the standard
    return _verdict('supported', refs, max(0.0, min(1.0, _share(_unrecovered(delay / TYPICAL_T1_S), full, zero))))      # an assumed T1 is not the paper's: a degree of 0 at worst, never conflicting


def _judge_signal_to_noise(native):
    return _graded(native['signal_to_noise_refs'], _log(native['signal_to_noise'], SIGNAL_TO_NOISE_FULL, SIGNAL_TO_NOISE_ZERO))


def _judge_window(native):
    return _graded(native['window_refs'], (native['acquisition_over_endpoint_time'], WINDOW_FULL, WINDOW_ZERO))


def _judge_detection_limit(native):
    return _graded(native['detection_refs'], _log(native['detection_limit_fraction'] * PERCENT_PER_FRACTION, DETECTION_LIMIT_FULL_PERCENT, DETECTION_LIMIT_ZERO_PERCENT))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('relaxation_delay', 'relaxation_delay_recorded_for_the_sheet'): _judge_relaxation, ('signal_to_noise', 'signal_to_noise_recorded_for_the_sheet'): _judge_signal_to_noise,
          ('time_alignment', 'acquisition_window_recorded_for_the_sheet'): _judge_window, ('non_detection_limit', 'detection_limit_recorded_for_the_sheet'): _judge_detection_limit,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _fraction(operand):
    """A stated share of the substrate as a fraction (its exact conversion from percent)."""
    return operand['value'] / PERCENT_PER_FRACTION if operand['unit'] == 'percent' else operand['value']


def _stated_effects(native, ref):
    """({effect kind: operand in its anchor unit or None}, reason) of the stated quantities; (None, reason) when the stated conversion is not above its own control."""
    q = native['quantities']
    conversion, control, net, amount = q['conversion'], q['control_conversion'], q['net_conversion'], q['product_concentration']
    stated = dict.fromkeys(('conversion_difference', 'conversion_fraction', 'endpoint_amount'))
    if net['status'] == 'point':
        stated['conversion_difference'] = _operand(_fraction(net), 'fraction', 'endpoint_nmr_conversion_difference:' + ref, net['source_refs'], net['origin'], 'net_conversion', net['support'])
    elif conversion['status'] == 'point' and control['status'] == 'point':
        difference = _fraction(conversion) - _fraction(control)
        if difference <= 0:
            return None, 'the_stated_conversion_is_not_above_the_stated_control'
        support = min((conversion['support'], control['support']), key=SUPPORT_WEAKEST_ORDER.index)
        stated['conversion_difference'] = _operand(difference, 'fraction', 'endpoint_nmr_conversion_difference:' + ref, list(dict.fromkeys(conversion['source_refs'] + control['source_refs'])), 'derived', 'conversion_difference', support)
    if conversion['status'] == 'point' and control['status'] != 'point':
        stated['conversion_fraction'] = _operand(_fraction(conversion), 'fraction', 'endpoint_nmr_conversion_fraction:' + ref, conversion['source_refs'], conversion['origin'], 'conversion', conversion['support'])
    if amount['status'] == 'point':
        stated['endpoint_amount'] = _operand(amount['value'] * MICROMOLAR_PER_UNIT[amount['unit']], 'uM', 'endpoint_nmr_endpoint_amount:' + ref, amount['source_refs'], amount['origin'], 'product_concentration', amount['support'])
    return stated, None


def _variance(graded, chosen, ref):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of the chosen effect."""
    native = graded['native']
    if chosen != 'conversion_fraction':
        return None, chosen + '_has_no_stated_spread_of_its_own', []
    spread = native['quantities']['conversion_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, 'conversion_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = _fraction(spread)
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_endpoint_nmr(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated, no_effect_reason = _stated_effects(native, ref)
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if stated is None or all(operand is None for operand in stated.values()):
        null_components['effect'] = no_effect_reason or 'no_endpoint_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_endpoint_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = chosen, effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, ANCHOR_UNIT[chosen] + '_squared', 'endpoint_nmr_' + chosen + '_variance:' + ref, variance_refs, 'derived', 'conversion_spread')
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
    result = {'version': VERSION, 'experiment_type': 'endpoint_nmr', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no stated quantity: the paper's own statement of conversion above its control fixes the direction (read "conversion detected" / "not detected")
        result['qualitative_effect'] = {'statement': STATEMENTS[native['conversion_statement']], 'support_refs': list(native['conversion_statement_refs'])}
        if native['conversion_statement'] is not None:
            result['direction_field_support'] = native['conversion_statement_support']      # the support class of the fact conversion_detected_above_control, the one field the statement is derived from
    return result
