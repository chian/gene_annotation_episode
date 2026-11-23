"""Transport_ssm_electrophysiology converter: turns the grader's result into what the A105 transport_response sheet takes.

Hand-built, private to transport_ssm_electrophysiology, deterministic. Input: the result of grade_transport_ssm_electrophysiology. Output: the sheet's
input (the 'extraction' grade_assay takes, with assay_type 'transport_response'), the sheet itself (grade_assay run on it), the dependence keys the
merger needs, and for every sheet component that an SSM measurement cannot honestly fill, the reason it stays null. The structure is that of the
spectro_direct converter; the class core (the effect quantities and their order) is the transport_response one
(literature_row_contract.TRANSPORT_STRENGTH_ANCHORS, TRANSPORT_EFFECT_ORDER; literature_transport_response_direction).

What the method is. A substrate concentration jump over proteoliposomes adsorbed on a gold sensor under a lipid layer gives a transient current when the
protein moves net charge (an electrogenic carrier or pump). The current is capacitively coupled, the voltage is not clamped, and the amplitude depends on how much
protein sits on the sensor. So the usable effects are the apparent Km (a ratio of peak currents, intensive) and the fold over the empty-liposome sensor; the peak
current (nA) and the charge (nC) are context, not effects. A transient current shows electrogenic translocation, not the net transport of every substrate: an
absent current is not an absent transport (an electroneutral transporter gives none), which is why the stated electrogenic fact is a criterion.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: the apparent Km (uM; kind transport_parameter) or the fold over the paper's own control
                  (dimensionless; kind transport_rate_ratio). Both may be stated; the one used is the best-determined, in the class order TRANSPORT_EFFECT_ORDER
                  (literature_transport_response_direction.select_transport_effect: the Km first, because it needs neither the amount of protein nor a normalizer).
                  A stated value in another unit of the record's vocabulary is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION); 'fold' is read as
                  'dimensionless'. The peak current, the charge and the decay time are not effects of the class and are not filled (no anchors, the amplitude depends on the
                  protein on the sensor).
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it: standard_error -> se^2; standard_deviation
                  -> sd^2 / n (n the sensor count) and only when the sensors criterion is supported; confidence_interval -> not converted (needs its level and degrees of
                  freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).
qualitative_effect  only when NO effect is stated: statement 'interaction_detected' (read "transport detected"), 'interaction_not_detected' (read "transport not detected") or
                  'interaction_not_stated', with the refs of the fact transport_detected_above_control that states it; direction_field_support is then the quote support of
                  that one fact (None when it is not stated). A stated effect fixes the direction and its own support; the statement is then not used. A result stated in
                  words alone already counts less than a measured one (the contract's stated_strength); it is not re-implemented here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives    empty_liposome_control + buffer_artefact
membrane_system            empty_liposome_control + sensor_quality
attribution_supported      inactive_protein_control
assertion_relevance        electrogenic_stated + native_substrate
calibration_applicability  reference_normalization + time_resolution
transport_endpoint         endpoint_stated
transport_driving_force    solutions_matched
transport_specificity      specificity_control
transport_response_model   substrate_range
sampling_basis             sensors + preparations
variance_correspondence    supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity, matrix_interference, condition_scope) are not selected. The thresholds are judged here, not in the grader (it records
facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Each judgement is a researched
value of THIS method made gradual (SOP step 3): full agreement at the researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the scale
the physics gives (never a step), unknown when the paper states nothing, never conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper
itself shows against the standard). A sheet criterion that is supported carries the smallest degree of its members that have one. Quote support
(literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is not selected.

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the purified protein or membrane preparation is analyte_preparation_ref, the proteoliposome
batch on the sensor is immobilized_preparation_ref, the gold sensor is surface_ref (inventory section 6). Qualitative statements keep the existing vocabulary. Direction and strength of a
stated Km or fold: literature_transport_response_direction (the class anchors); controls, the exchange time, the series and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or method-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads and whether
the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
SOLUTION_EXCHANGE_MS 10, DECAY_FULL_RATIO 0.1 -> DECAY_ZERO_RATIO 1.0, judged on the fraction of the peak that survives the exchange.
  Q1 a peak that is the solution exchange and not the transport: the activating solution reaches the sensor in a finite time (a rise of the order of ten milliseconds, from
  memory, the least certain number here), so a transient that decays as fast as the exchange is cut and its peak and charge are too small and set by the flow. Q2 method-specific
  (the SSM time resolution is limited by the exchange of solutions over the sensor: Schulz, Garcia-Celma and Fendler 2008, Methods 46:97; Bazzone, Barthmes and Fendler 2017,
  Methods Enzymol 594:31; from memory). Q3 relative to the paper's own decay time, which the grader records; the exchange time is an instrument property taken as 10 ms (not
  stated by most papers). Q4 for a transient that decays with time constant tau, seen through a first-order rise of time constant t, the peak is the fraction r^(r/(1-r)) of the
  true peak, r = t / tau: 0.96 at r = 0.01, 0.77 at r = 0.1, 0.58 at r = 0.33 and 1/e = 0.37 at r = 1. The degree is linear in that fraction between r = 0.1 (full: a Km is a ratio of
  peaks, so a constant loss of about a fifth cancels; the typical transient decays in tens to hundreds of milliseconds) and r = 1 (zero: the peak is the exchange, no agreement;
  at or beyond it the paper shows the standard is not met, conflicting). Q5 a bias that grows with the departure from the good value, like the regime and absorbance curves of spectro_direct.
MIN_SUBSTRATE_CONCENTRATIONS 6, SUBSTRATE_CONCENTRATIONS_ZERO 2.
  Q1 a Km fitted to too few concentrations to show the hyperbola holds. Q2 general for a saturation curve (about six to eight concentrations spanning 0.2 to 10 times the Km;
  Cornish-Bowden; Copeland; NCBI Assay Guidance Manual), from memory; an SSM sensor carries many jumps, so six is easily reached. Q3 absolute (a count). Q4 the hyperbola has two parameters (Km and
  the maximal current), so two concentrations are used up by the fit and leave no residual degree of freedom (supported with degree 0, never conflicting); the degree rises
  linearly with count - 2. Q5 the same residual-degree-of-freedom count as spectro_direct and the SPR steady-state KD.
LOW_FACTOR 0.2 -> LOW_ZERO_FACTOR 1.0, HIGH_FACTOR 10 -> HIGH_ZERO_FACTOR 1.0 (the lowest and highest jump concentration over the Km).
  Q1 a series that does not bracket the Km, so the Km and the maximal current trade off. Q2 general (the references above), from memory. Q3 relative to the paper's own Km (the grader records
  both ratios). Q4 the peak current is I / Imax = S / (S + Km) if it follows the hyperbola, so both ends are judged linearly in the fractional saturation S / (S + Km) (1/6 at 0.2 Km, 10/11 at 10 Km; 1/2 at the Km, the zero end of
  both). Q5 SOP working rule d: the top is 10 where the maximal amplitude is a free value known only by reaching it; here it is free (it changes with the protein on each sensor).
MIN_SENSORS 3, degree min(1, sqrt(n / 3)).
  Q1 a result from one sensor, whose amount of protein and membrane quality are one draw (the sensor-to-sensor spread of the amplitude is large). Q2 general (triplicate practice; a sensor is
  the sampling unit, not a jump: repeated jumps on one sensor are not replicates). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
MIN_PREPARATIONS 2, degree min(1, sqrt(n / 2)).
  Q1 a result from one reconstitution, so a preparation artefact (the lipid-to-protein ratio, a partly inactive batch) cannot be told from the protein. Q2 practice (reconstitution is laborious; two
  independent preparations are the usual minimum shown, from memory). Q3 absolute count. Q4 the same 1 / sqrt(n) precision; the full-credit number is lower than for the sensors because a preparation costs more. Q5 the shared replicate rule with its own researched minimum.
Facts with no number (the controls, the specificity controls, the solutions, the sensor check, the reference jump, the electrogenic and native-substrate statements, the endpoint): the paper's own
statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the size of the peak current or of the charge (it depends on the protein
on the sensor and has no scale of its own: it is context); the pH and the temperature (the claim carries no condition, and the identity block records the temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this assay, decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? A transient capacitively coupled current of net charge movement of one defined preparation: the amplitude is RELATIVE (it depends on the amount of protein on the sensor),
  the Km and the fold are the usable numbers.
  Is there a reference range we would trust if the paper stated less? No (as for no binding range): there is no typical SSM amplitude and the Km of a carrier spans decades.
  What does an unstated control or calibration do to the number's meaning? The solution-exchange artefact is a known false current: a jump over an empty sensor gives a transient too, so an unstated empty-liposome or
  artefact control can leave the current without an owner; an unstated reference jump leaves the amplitudes not comparable between sensors (a Km from un-normalized peaks is a mixture); an unstated sensor check, solution
  match or endpoint is an ordinary gap.
  If we assume it is fine and are wrong, how badly does the score mislead? A false transport (the artefact counted as the protein's current) for a weak signal, a wrong Km for a strong one; more than a KD by a label-free method, less than a band in a pull-down.
  Consistent with KD? The default 0.70 is well under the KD anchor 0.90 and level with the 0.70 of ELISA and the thermal shift (a relative readout that rests on its controls).
  default 0.70. background_alternatives 0.60 (the exchange artefact is the dominant false positive), transport_specificity 0.60 (charge flow is not identified-ion flow; a blocker, a non-substrate or an ion substitution is what ties it to the substrate),
  attribution_supported 0.75 (an inactive protein control is the stronger form and often left out; the empty liposome already covers part), calibration_applicability 0.70 (a reference jump on the same sensor decides whether Km and fold compare),
  transport_endpoint 0.85 and sampling_basis 0.80 (benign when unstated: the peak current is the usual readout; sensors in triplicate are usual). membrane_system, assertion_relevance, transport_driving_force and transport_response_model take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import TRANSPORT_KIND_OF_QUANTITY
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_response_direction import select_transport_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_transport_ssm_electrophysiology_converted'
CRITERIA_MAP = {'background_alternatives': ('empty_liposome_control', 'buffer_artefact'), 'membrane_system': ('empty_liposome_control', 'sensor_quality'),
                'attribution_supported': ('inactive_protein_control',), 'assertion_relevance': ('electrogenic_stated', 'native_substrate'),
                'calibration_applicability': ('reference_normalization', 'time_resolution'), 'transport_endpoint': ('endpoint_stated',),
                'transport_driving_force': ('solutions_matched',), 'transport_specificity': ('specificity_control',),
                'transport_response_model': ('substrate_range',), 'sampling_basis': ('sensors', 'preparations')}
MS_PER_UNIT = {'ms': 1.0, 's': 1000.0}  # FIXED_BY_DEFINITION: a second is a thousand milliseconds.
PEAK_FRACTION_AT_EQUAL_TIMES = math.exp(-1.0)  # FIXED_BY_DEFINITION: the limit of r^(r/(1-r)) as r goes to 1 (a transient decaying as fast as the exchange keeps 1/e of its peak).
SOLUTION_EXCHANGE_MS = 10.0  # EXPERT_REVIEW, owner to confirm: time in which the solution at the sensor is exchanged, of the order of ten milliseconds (SSM method papers, from memory, not verified; the least certain number here); an instrument property that most papers do not state.
DECAY_FULL_RATIO = 0.1  # EXPERT_REVIEW, owner to confirm: exchange time over decay time at which the agreement is full: the peak keeps 0.77 of its true size (r^(r/(1-r)) at r = 0.1), a loss that cancels in a Km (a ratio of peaks); a decay of 100 ms or slower at a 10 ms exchange.
DECAY_ZERO_RATIO = 1.0  # EXPERT_REVIEW, owner to confirm: a decay as fast as the exchange: the peak is the exchange and not the transport (no agreement; at or beyond it conflicting); between the two ratios the degree falls linearly in the surviving fraction of the peak.
MIN_SUBSTRATE_CONCENTRATIONS = 6  # EXPERT_REVIEW, owner to confirm: fewest jump concentrations of a usable saturation curve (about six to eight, Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory); full agreement from it.
SUBSTRATE_CONCENTRATIONS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: the hyperbola has two parameters (Km, maximal current), so two concentrations are used up by the fit and leave no residual degree of freedom (degree 0, supported, never conflicting); between this and MIN_SUBSTRATE_CONCENTRATIONS the degree rises linearly with the residual degrees of freedom (count - 2).
LOW_FACTOR = 0.2  # EXPERT_REVIEW, owner to confirm: the lowest jump concentration should be at most this multiple of the Km (the current is 1/6 of the maximum there); full agreement up to it.
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: lowest concentration at the Km itself leaves the lower half of the hyperbola undefined (no agreement); falls from LOW_FACTOR linearly in the fractional saturation S / (S + Km).
HIGH_FACTOR = 10.0  # EXPERT_REVIEW, owner to confirm: the highest concentration should be at least this multiple of the Km (the current is 10/11 of the maximum); the maximal current is a free amplitude that changes with the protein on each sensor (SOP rule d: 10 for a free plateau); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: highest concentration at the Km itself never reaches saturation (no agreement); falls from HIGH_FACTOR linearly in the fractional saturation S / (S + Km).
MIN_SENSORS = 3  # EXPERT_REVIEW, owner to confirm: fewest independent sensors; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_SENSORS)): the standard error of a mean over n independent sensors falls as 1 / sqrt(n); never conflicting for a stated count.
MIN_PREPARATIONS = 2  # EXPERT_REVIEW, owner to confirm: fewest independent proteoliposome preparations (two reconstitutions are the usual shown minimum, from memory); full agreement from it; below it min(1, sqrt(n / MIN_PREPARATIONS)); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.TRANSPORT_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (1 mM is 1000 uM; 1 nM is 1e-3 uM; a stated n-fold is the ratio n, the sheet's 'dimensionless'); the stated number is the paper's.
    'transport_km': ('uM', {'nM': 1.0e-3, 'uM': 1.0, 'mM': 1.0e3}),
    'fold_over_control': ('dimensionless', {'fold': 1.0}),
}
RECORD_QUANTITY = {'transport_km': 'km', 'fold_over_control': 'fold_over_control'}   # the record's name of each effect quantity (its spread is that name + '_spread')
KIND_WITHOUT_EFFECT = 'electrical_current'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing): what the method reads is a current
NULL_REASONS = {'recovery': 'an_ssm_current_has_no_matrix_recovery_measurement', 'attributed_signal': 'an_ssm_current_is_not_an_attribution_fraction', 'total_signal': 'an_ssm_current_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_transport_ssm_electrophysiology_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_transport_ssm_electrophysiology_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "transport detected" / "transport not detected" / "transport not stated" for this class


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


def _saturation(ratio):
    """Fractional saturation S / (S + Km) of a concentration S given as S / Km: where on the hyperbola it sits."""
    return ratio / (1 + ratio)


def _peak_fraction(ratio):
    """The fraction r^(r/(1-r)) of its true peak that a transient keeps when it is seen through a first-order exchange of time constant t, r = t / tau (0 < r < 1)."""
    return ratio ** (ratio / (1.0 - ratio))


def _judge_decay(native):
    refs = native['decay_time_refs']
    ratio = SOLUTION_EXCHANGE_MS / (native['decay_time_value'] * MS_PER_UNIT[native['decay_time_unit']])
    if ratio >= DECAY_ZERO_RATIO:
        return _verdict('conflicting', refs)
    return _graded(refs, (_peak_fraction(ratio), _peak_fraction(DECAY_FULL_RATIO), PEAK_FRACTION_AT_EQUAL_TIMES))


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


def _judge_sensors(native):
    if native['sensor_independent'] != 'yes':
        return _verdict('unknown', native['sensor_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['sensor_refs'], min(1.0, math.sqrt(native['sensor_count'] / MIN_SENSORS)))      # precision of the mean, see MIN_SENSORS


def _judge_preparations(native):
    if native['preparation_independent'] != 'yes':
        return _verdict('unknown', native['preparation_refs'])
    return _verdict('supported', native['preparation_refs'], min(1.0, math.sqrt(native['preparation_count'] / MIN_PREPARATIONS)))      # precision of the mean, see MIN_PREPARATIONS


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('time_resolution', 'decay_time_recorded_for_the_sheet'): _judge_decay, ('substrate_range', 'substrate_series_recorded_for_the_sheet'): _judge_series,
          ('sensors', 'sensor_count_recorded_for_the_sheet'): _judge_sensors, ('preparations', 'preparation_count_recorded_for_the_sheet'): _judge_preparations}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _stated_effect(native, quantity, ref):
    """The stated quantity as an effect operand in its anchor unit, or None when not stated (its 'support' is the extraction's)."""
    operand = native['quantities'][RECORD_QUANTITY[quantity]]
    if operand['status'] != 'point':
        return None
    unit, factors = UNIT_FACTORS[quantity]
    return _operand(operand['value'] * factors[operand['unit']], unit, 'transport_ssm_electrophysiology_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], RECORD_QUANTITY[quantity], operand['support'])


def _variance(graded, quantity, ref):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of ``quantity``."""
    native = graded['native']
    spread = native['quantities'][RECORD_QUANTITY[quantity] + '_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, RECORD_QUANTITY[quantity] + '_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    unit, factors = UNIT_FACTORS[quantity]
    sd = spread['value'] * factors[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['sensor_count']
        if _criterion(graded, 'sensors')['status'] != 'supported':
            return None, 'sd_needs_independent_sensors_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_transport_ssm_electrophysiology(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {quantity: _stated_effect(native, quantity, ref) for quantity in UNIT_FACTORS}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_km_or_fold_over_control_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_transport_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = TRANSPORT_KIND_OF_QUANTITY[chosen], effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'transport_ssm_electrophysiology_' + chosen + '_variance:' + ref, variance_refs, 'derived', RECORD_QUANTITY[chosen] + '_spread')
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
    result = {'version': VERSION, 'experiment_type': 'transport_ssm_electrophysiology', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no stated Km or fold: the experiment's stated yes/no result stands, scored like any stated result (literature_direction, the qualitative path)
        result['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs'])}
        if native['interaction'] is not None:
            result['direction_field_support'] = native['interaction_support']      # the support class of the fact transport_detected_above_control, the one field the statement is derived from
    return result
