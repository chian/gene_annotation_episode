"""Transport_oocyte_two_electrode converter: turns the grader's result into what the A105 transport_response sheet takes. DRAFT of 2026-11-22, owner to correct.

Hand-built, private to transport_oocyte_two_electrode, deterministic. Input: the result of grade_transport_oocyte_two_electrode. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'transport_response'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for every sheet
component that an oocyte voltage clamp cannot honestly fill, the reason it stays null. Modelled on literature_spectro_direct_converter.py; the class core is the
transport_response one (the effect quantities and their order are those of literature_transport_response_direction.py, not the activity ones).

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: the apparent Km of the substrate-induced current (uM) or the fold of that current over the
                  paper's own control oocytes (dimensionless). Both may be stated; the one used is the best-determined, in the class order TRANSPORT_EFFECT_ORDER
                  (literature_transport_response_direction.select_transport_effect: the Km first, because it needs neither the amount of protein in the oocyte nor a
                  control's background). A stated value in another unit of the record's vocabulary is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION):
                  the value is the paper's, only its unit spelling changes. quantity_kind of the extraction names the kind of the effect (KIND_OF_QUANTITY: 'transport_parameter'
                  for the Km, 'transport_rate_ratio' for the fold), which the direction function reads. A stated current is NOT an effect: its size depends on how much
                  protein the oocyte made (a batch-to-batch figure), so it is context, judged only as a clamp-range and a background criterion. The fold is not worked
                  out from a current and a control current (only a stated fold is used; see the registration note for the option).
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n of the oocytes, and only when the oocyte count is stated (in oocyte papers the n of a mean is the number of
                  oocytes; a converted variance only ever lowers the strength, never raises it); confidence_interval -> not converted (needs its level and degrees of freedom).
                  Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery, attributed signal/total signal (the current over the control current is judged as the
background criterion and not entered as an attributed fraction), condition test/reference, the assertion and alternative predictions.
qualitative_effect  only when NO effect is stated and the paper states whether it saw a substrate-induced current above its own control: statement
                  'interaction_detected' (read "transport detected") or 'interaction_not_detected' (read "transport not detected"), with the refs of the fact that states it
                  and direction_field_support taken from the support of that one fact. A stated effect fixes the direction; the statement is then not used. Remark for the
                  owner: a current is charge flow, so an electroneutral transporter gives none, and "no current was detected" is weaker evidence against transport than
                  against a channel; the class decision keeps the one vocabulary and its one magnitude for both directions.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives   uninjected_control + background_current
membrane_system           uninjected_control + leak_subtracted
attribution_supported     inactive_mutant_control + expression_confirmed
transport_endpoint        same_oocyte_baseline
transport_driving_force   clamp_conditions
transport_specificity     non_substrate_control + ion_dependence
transport_response_model  substrate_range
calibration_applicability clamp_current_range
sampling_basis            replicates + oocytes_recorded
assertion_relevance       native_substrate + substrate_uptake_confirmed (does this endpoint, a charge flow, address "the protein moves the substrate")
variance_correspondence   supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each
such criterion and reason to its judgement). Each judgement is a researched value of THIS assay made gradual (SOP step 3): full agreement at the researched good
value, falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the assay gives (never a step), unknown when the paper states
nothing, never conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper itself shows against the standard). A sheet criterion
that is supported carries the smallest degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported
criterion and never changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped;
a sheet criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (measurement_identity, matrix_interference,
condition_scope) are not selected.

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the batch of injected oocytes is analyte_preparation_ref; there is no vesicle batch and
the electrodes are not a shared sample, so immobilized_preparation_ref and surface_ref stay None. Qualitative statements keep the existing vocabulary
(interaction_detected reads "transport detected"). Direction and strength of a stated Km or fold: literature_transport_response_direction (the Km smaller is stronger,
the fold larger is stronger); controls, the clamp range and the rest lower the WEIGHT only.

THE VALUES BELOW ARE A FIRST DRAFT FOR THE OWNER (2026-11-22): every number is EXPERT_REVIEW, owner to confirm, and every literature figure is from the drafter's memory
of oocyte electrophysiology practice, NOT web-verified and NOT checked against a method paper; verify before relying on any of them.
Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads and
whether the shape fits, Q5 consistency with the other assays).
-----------------------------------------------------------------------------------------------------------------------------------
CURRENT_OVER_CONTROL_FULL 10 -> CURRENT_OVER_CONTROL_ZERO 1, judged linearly in the share of the current that is not the control's, 1 - 1 / ratio.
  Q1 a substrate-induced current of the oocytes with the protein that is hardly larger than that of the water-injected or uninjected oocytes: the oocyte's own carriers and
  channels (oocytes carry endogenous amino-acid, nucleoside and other carriers and chloride channels, and some respond to a substrate) could make all of it. Q2 general: the
  control oocytes of the same batch are the standard of the method; a signal ten times the control leaves the endogenous part at 10 percent, about the oocyte-to-oocyte
  spread of expression, from memory, not verified; the exact 10 is a judgement. Q3 relative to the paper's own control, which the grader records (both currents). Q4 the
  share 1 - 1 / ratio is the fraction of the signal that is the protein's (the sheet's attributed fraction (U - B) / U): 0.9 at 10-fold, 0.5 at 2-fold, 0 at 1-fold, so the
  degree is linear in what is attributed and falls fastest near the control. At or below a ratio of 1 the paper's own numbers show the protein adds nothing over the
  control (conflicting). Q5 the same idea as the other background judgements (a bias that grows with the departure from the researched value); it is a weight criterion, not
  the strength scale (the fold anchors of the contract, 1 to 30, decide the strength of a STATED fold).
CLAMP_CURRENT_FULL_UA 2 -> CLAMP_CURRENT_ZERO_UA 20, judged linearly in the current, the voltage error being proportional to it.
  Q1 an oocyte whose current is so large that the clamp does not hold the stated voltage: the voltage error is the current times the series resistance (the bath and
  ground electrode and the electrode pair, about 1 kOhm in a standard oocyte bath; from memory, to verify), so the stated driving force is not the real one, and the
  amplifier cannot pass more than about 10 uA (the usual two-electrode amplifiers). Q2 general: oocyte clamp practice keeps currents to a few uA (from memory, not
  verified); the series resistance is bath- and amplifier-specific. Q3 absolute (uA); the grader records the paper's own number. Q4 the error in mV is about the current in uA
  at 1 kOhm: 2 mV at 2 uA (negligible against the roughly 25 to 60 mV that changes a carrier's current e-fold or tenfold), 20 mV at 20 uA (a large share of the driving force and
  twice what the amplifier can pass); linear because the error is proportional to the current. At or beyond 20 uA the clamp did not hold (conflicting). Q5 a bias that grows
  with the departure from the researched value, as the absorbance range of spectro_direct.
MIN_SUBSTRATE_CONCENTRATIONS 6, SUBSTRATE_CONCENTRATIONS_ZERO 2.
  Q1 a Km fitted to too few substrate concentrations to show the hyperbola holds. Q2 general: a concentration-response curve of about six to eight concentrations over about two
  decades (oocyte papers perfuse ascending concentrations over one oocyte, from memory), the exact 6 is a judgement. Q3 absolute (a count). Q4 the hyperbola has two
  parameters (Km and the largest current), so two concentrations are used up by the fit and leave no residual degree of freedom (supported with degree 0, never
  conflicting); the degree rises linearly with count - 2. Q5 the same count curve as spectro_direct (a two-parameter hyperbola).
LOW_FACTOR 0.2 -> LOW_ZERO_FACTOR 1.0, HIGH_FACTOR 10 -> HIGH_ZERO_FACTOR 1.0 (the lowest and highest substrate over the Km).
  Q1 a series that does not bracket the Km, so Km and the largest current trade off (no saturation) or the curvature is unseen (no low end). Q2 general: 0.2 to 10 times the Km
  (enzyme-kinetic practice, which a carrier current follows at a fixed voltage), from memory. Q3 relative to the paper's own Km (the grader records both ratios). Q4 the
  current is I / Imax = S / (S + Km), so both ends are judged linearly in the fractional saturation S / (S + Km) (1/6 at 0.2 Km, 10/11 at 10 Km; 1/2 at the Km, the zero end of
  both). Q5 SOP rule d: the top is 10 where the plateau is a free amplitude known only by reaching it; here the largest current differs from oocyte to oocyte with the amount
  of protein, so it is free; the high concentrations an oocyte tolerates (osmolarity, non-specific currents at tens of mM) are a practical limit that the curve already
  shows as partial credit.
MIN_BATCHES 3, degree min(1, sqrt(n / 3)).
  Q1 a result from the oocytes of one frog or one injection day: expression level and the oocyte's own background differ strongly from batch to batch (a known
  feature of the oocyte), so more oocytes of one batch do not average it. Q2 general (the oocyte-electrophysiology practice of repeating on at least two to three
  batches, from memory; the triplicate rule of the owner). Q3 absolute count; it counts only when independence is stated yes. Q4 precision of a mean (1 / sqrt(n)). Q5
  exactly the shared replicate rule.
OOCYTES_FULL_CREDIT 6, degree min(1, sqrt(n / 6)).
  Q1 a mean from a handful of oocytes of one batch. Q2 practice: five to ten oocytes per condition, the oocyte-to-oocyte coefficient of variation of the current about 30 to
  50 percent, so six oocytes give a standard error of about 15 percent (from memory, not verified); lab-specific. Q3 absolute; kept. Q4 the count limits only the
  within-batch precision, so a wrong 6 misleads little; sqrt(n / 6) is steep at a few oocytes (2 oocytes 0.58) and gentle near 6. Q5 the same precision shape as the object counts of
  co-localization (sqrt(n / full)), with its own researched full number.
Facts with no number (the controls, the baseline, the leak, the ion dependence, the substrate uptake, the inactive mutant, the expression, the native substrate, the clamp
conditions): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the
size of the Km itself and of the fold (the strength scale reads them); the voltage (the claim carries no condition, and the identity block records the temperature); the
current direction (kept for the reviewer).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this assay, decided
2026-11-22, owner to confirm:
  What does it measure; absolute or relative? A membrane current of one oocyte, an absolute electrical quantity (nA) of the clamp; but what it means (a carrier of the
  substrate, rather than the oocyte's own channels, or a leak) rests on controls, and its size is relative to the amount of protein the oocyte made. The Km is
  intensive and well defined.
  Is there a reference range we would trust if the paper stated less (as for KD)? The Km range of carriers is well known (the anchors), but the oocyte background is not: it
  differs by batch and by substrate.
  What does an unstated control or calibration do to the number's meaning? An unstated water-injected control is usually benign (it is the universal practice of the
  method), but where it was not done a host current is counted as the protein's; the clamp amplifier and the baseline are instrument and routine (benign).
  If we assume it is fine and are wrong, how badly does the score mislead? A host or leak current counted as the protein's, or charge flow counted as substrate flow: the
  direction of "transports" is wrong; worse than a KD's magnitude, less than a pull-down band.
  Consistent with KD? The default 0.80 is under the KD anchor 0.90 and under spectro_direct 0.85 (a rate of a purified enzyme: no host background).
  default 0.80. background_alternatives 0.70 and transport_specificity 0.70 (the controls that separate the protein's current from the host's and the substrate's from
  another ion's), assertion_relevance 0.65 (a current is charge, not the substrate; an uncoupled leak or an electroneutral mode makes the gap real), attribution_supported
  0.75, sampling_basis 0.85, transport_driving_force 0.85, transport_endpoint 0.90 (the same-oocyte baseline is how the current is defined in this method),
  calibration_applicability 0.90 (the clamp is calibrated by the instrument; large currents are the exception that the criterion catches when stated).
  membrane_system and transport_response_model take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_response_direction import select_transport_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_transport_oocyte_two_electrode_converted_v1'
CRITERIA_MAP = {'background_alternatives': ('uninjected_control', 'background_current'), 'membrane_system': ('uninjected_control', 'leak_subtracted'),
                'attribution_supported': ('inactive_mutant_control', 'expression_confirmed'), 'transport_endpoint': ('same_oocyte_baseline',),
                'transport_driving_force': ('clamp_conditions',), 'transport_specificity': ('non_substrate_control', 'ion_dependence'),
                'transport_response_model': ('substrate_range',), 'calibration_applicability': ('clamp_current_range',), 'sampling_basis': ('replicates', 'oocytes_recorded'),
                'assertion_relevance': ('native_substrate', 'substrate_uptake_confirmed')}
NA_PER_UA = 1000.0  # FIXED_BY_DEFINITION: 1 uA is 1000 nA.
CURRENT_OVER_CONTROL_FULL = 10.0  # EXPERT_REVIEW, owner to confirm: the current of the oocytes with the protein over that of the paper's own control oocytes taken as leaving the oocyte's own contribution at 10 percent of the signal, about the oocyte-to-oocyte spread of expression (from memory, not verified); full agreement from it.
CURRENT_OVER_CONTROL_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: a current no larger than the control's: the protein adds nothing the control does not already show (no agreement; conflicting); the degree falls linearly in the share of the signal that is not the control's, 1 - 1 / ratio (the attributed fraction), from the full end to here.
CLAMP_CURRENT_FULL_UA = 2.0  # EXPERT_REVIEW, owner to confirm: the largest substrate-induced current (uA) at which the voltage error (current times a series resistance of about 1 kOhm, from memory, to verify) is about 2 mV, negligible against the 25 to 60 mV that changes a carrier's current e-fold to tenfold; full agreement up to it.
CLAMP_CURRENT_ZERO_UA = 20.0  # EXPERT_REVIEW, owner to confirm: at 20 uA the same estimate gives about 20 mV of error and twice what the usual two-electrode amplifiers can pass (about 10 uA, from memory): the clamp did not hold the stated voltage (no agreement; conflicting); the degree falls linearly in the current (the error is proportional to it) from the full end to here.
MIN_SUBSTRATE_CONCENTRATIONS = 6  # EXPERT_REVIEW, owner to confirm: fewest substrate concentrations of a usable concentration-response curve (about six to eight over about two decades, from memory); full agreement from it.
SUBSTRATE_CONCENTRATIONS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: the hyperbola has two parameters (Km, largest current), so two concentrations are used up by the fit and leave no residual degree of freedom (degree 0, supported, never conflicting: a short series is weaker evidence); between this and MIN_SUBSTRATE_CONCENTRATIONS the degree rises linearly with the residual degrees of freedom (count - 2).
LOW_FACTOR = 0.2  # EXPERT_REVIEW, owner to confirm: the lowest substrate should be at most this multiple of the Km (the current is 1/6 of its largest value there); full agreement up to it.
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: lowest substrate at the Km itself leaves the lower half of the hyperbola undefined (no agreement); falls from LOW_FACTOR linearly in the fractional saturation S / (S + Km).
HIGH_FACTOR = 10.0  # EXPERT_REVIEW, owner to confirm: the highest substrate should be at least this multiple of the Km (the current is 10/11 of its largest value); the largest current is a free amplitude (it differs from oocyte to oocyte) known only by reaching it (SOP rule d: 10 for a free plateau); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: highest substrate at the Km itself never reaches saturation (no agreement); falls from HIGH_FACTOR linearly in the fractional saturation S / (S + Km).
MIN_BATCHES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent batches of oocytes (different donor frogs or injection days); full agreement from it. Below it the degree is min(1, sqrt(n / MIN_BATCHES)): the standard error of a mean over n independent batches falls as 1 / sqrt(n); never conflicting for a stated count.
OOCYTES_FULL_CREDIT = 6  # EXPERT_REVIEW, owner to confirm: number of oocytes recorded that gets full credit (five to ten per condition is usual; with an oocyte-to-oocyte coefficient of variation of 30 to 50 percent, six give a standard error of about 15 percent; from memory, not verified). Gradual: below it the degree is sqrt(n / 6), never conflicting.
# The anchor unit of each effect quantity (the class's transport anchors, TRANSPORT_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (1 mM is 1000 uM; 1 nM is 0.001 uM; a fold is a dimensionless ratio); the stated number is the paper's.
    'transport_km': ('uM', {'nM': 1.0e-3, 'uM': 1.0, 'mM': 1.0e3}),
    'fold_over_control': ('dimensionless', {'fold': 1.0}),
}
RECORD_FIELD = {'transport_km': 'km', 'fold_over_control': 'fold_over_control'}   # the record quantity of each effect quantity
# The quantity_kind (QUANTITY_KINDS['transport_response']) that names the kind of each effect quantity; literature_transport_response_direction reads it back.
KIND_OF_QUANTITY = {'transport_km': 'transport_parameter', 'fold_over_control': 'transport_rate_ratio'}
KIND_WITHOUT_EFFECT = 'transport_rate'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'a_voltage_clamp_current_has_no_matrix_recovery_measurement', 'attributed_signal': 'the_current_over_the_control_current_is_judged_as_a_criterion_not_entered_as_an_attributed_fraction',
                'total_signal': 'the_current_over_the_control_current_is_judged_as_a_criterion_not_entered_as_an_attributed_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_two_electrode_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_two_electrode_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment',
                'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENT = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected'}   # read "transport detected" / "transport not detected" for this class


def _verdict(status, refs, degree=None):
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError('a ' + status + ' judgement needs support refs')
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


def _attributed_share(ratio):
    """The share 1 - 1 / ratio of a signal that is not the control's, for the signal over the control as a ratio."""
    return 1.0 - 1.0 / ratio


def _saturation(ratio):
    """Fractional saturation S / (S + Km) of a substrate S given as S / Km: where on the hyperbola it sits."""
    return ratio / (1 + ratio)


def _judge_background(native):
    return _graded(native['control_refs'], (_attributed_share(native['current_over_control']), _attributed_share(CURRENT_OVER_CONTROL_FULL), _attributed_share(CURRENT_OVER_CONTROL_ZERO)))


def _judge_clamp_current(native):
    return _graded(native['current_refs'], (native['current_nA'] / NA_PER_UA, CLAMP_CURRENT_FULL_UA, CLAMP_CURRENT_ZERO_UA))


def _judge_series(native):
    # the two ratios keep their ramps (conflicting at their zero end), judged on the fractional saturation; the lower end is judged only when the series
    # has one distinct from its upper end (one concentration is a short series, not a badly placed one). The count only lowers the degree, never conflicts.
    refs = native['concentration_refs']
    low, high = native['concentration_low_over_km'], native['concentration_high_over_km']
    limits = [(_saturation(high), _saturation(HIGH_FACTOR), _saturation(HIGH_ZERO_FACTOR))]
    if low < high:
        limits.append((_saturation(low), _saturation(LOW_FACTOR), _saturation(LOW_ZERO_FACTOR)))
    verdict = _graded(refs, *limits)
    if verdict['status'] == 'conflicting':
        return verdict
    count_degree = max(0.0, min(1.0, _share(native['concentration_count'], MIN_SUBSTRATE_CONCENTRATIONS, SUBSTRATE_CONCENTRATIONS_ZERO)))
    return _verdict('supported', refs, min(verdict['degree'], count_degree))


def _judge_replicates(native):
    if native['batch_independent'] != 'yes':
        return _verdict('unknown', native['batch_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['batch_refs'], min(1.0, math.sqrt(native['batch_count'] / MIN_BATCHES)))      # precision of the mean, see MIN_BATCHES


def _judge_oocytes(native):
    return _verdict('supported', native['oocyte_refs'], min(1.0, math.sqrt(native['oocyte_count'] / OOCYTES_FULL_CREDIT)))      # precision of the mean over n oocytes, see OOCYTES_FULL_CREDIT


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('background_current', 'control_current_recorded_for_the_sheet'): _judge_background, ('clamp_current_range', 'current_recorded_for_the_sheet'): _judge_clamp_current,
          ('substrate_range', 'substrate_series_recorded_for_the_sheet'): _judge_series, ('replicates', 'batch_count_recorded_for_the_sheet'): _judge_replicates,
          ('oocytes_recorded', 'oocyte_count_recorded_for_the_sheet'): _judge_oocytes}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _stated_effect(native, quantity, ref):
    """The stated quantity as an effect operand in its anchor unit, or None when not stated (its 'support' is the extraction's)."""
    operand = native['quantities'][RECORD_FIELD[quantity]]
    if operand['status'] != 'point':
        return None
    unit, factors = UNIT_FACTORS[quantity]
    return _operand(operand['value'] * factors[operand['unit']], unit, 'transport_oocyte_two_electrode_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], RECORD_FIELD[quantity], operand['support'])


def _variance(graded, quantity):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of ``quantity``."""
    native = graded['native']
    spread = native['quantities'][RECORD_FIELD[quantity] + '_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, RECORD_FIELD[quantity] + '_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    unit, factors = UNIT_FACTORS[quantity]
    sd = spread['value'] * factors[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['oocyte_count']
        if count['status'] != 'point':
            return None, 'sd_needs_the_oocyte_count_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_transport_oocyte_two_electrode(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {quantity: _stated_effect(native, quantity, ref) for quantity in UNIT_FACTORS}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_transport_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_transport_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_QUANTITY[chosen], effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'transport_oocyte_two_electrode_' + chosen + '_variance:' + ref, variance_refs, 'derived', RECORD_FIELD[chosen] + '_spread')
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'transport_response', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'transport_oocyte_two_electrode', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None and native['transport'] is not None:      # no stated quantity: the paper's own statement of a current above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['transport']], 'support_refs': list(native['transport_refs'])}
        result['direction_field_support'] = native['transport_support']      # the support class of the fact transport_detected_above_control, the one field the statement is derived from
    return result
