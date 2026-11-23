"""Transport_planar_bilayer converter: turns the grader's result into what the A105 transport_response sheet takes.

Hand-built, private to transport_planar_bilayer, deterministic. Input: the result of grade_transport_planar_bilayer. Output: the sheet's input (the
'extraction' grade_assay takes, with assay_type 'transport_response'), the sheet itself (grade_assay run on it), the dependence keys the merger needs,
and for every sheet component that a bilayer recording cannot honestly fill, the reason it stays null. It follows the shape of
literature_spectro_direct_converter.py, with the transport_response class core (the Km, turnover, unitary conductance, charge rate, fold and rate per
mass of literature_transport_response_direction.py) in place of the activity class core.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: the unitary conductance (pS) or the charge rate of one channel (elementary
                  charge equivalents per second). Both may be stated; the one used is the best-determined, in the class order TRANSPORT_EFFECT_ORDER
                  (literature_transport_response_direction.select_transport_effect; the conductance comes first, because the driving force is already
                  removed from it). A stated value in another unit of the record's vocabulary is multiplied by its exact factor (UNIT_FACTORS,
                  FIXED_BY_DEFINITION). quantity_kind of the extraction names the kind of the effect (TRANSPORT_KIND_OF_QUANTITY of the contract), which
                  the direction function reads. A unitary current, the holding voltage, the reversal potential, the permeability ratio, the event count
                  and the noise are never an effect: they are judged under their criteria, or kept as context.
effect_variance   variance of the conductance, in pS squared, only when the passage's spread allows it: standard_error -> se^2; standard_deviation ->
                  sd^2 / n (n the independent bilayers) and only when the replicates criterion is supported; confidence_interval -> not converted (needs
                  its level and degrees of freedom). Otherwise null. The charge rate has no spread field in the record, so its variance stays null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).
qualitative_effect  only when NO effect is stated: statement 'interaction_detected' (read "transport detected"), 'interaction_not_detected' (read
                  "transport not detected") or 'interaction_not_stated', with the refs of the fact transport_detected_above_control that states it, and
                  direction_field_support taken from the quote support of that one fact. A stated effect fixes the direction; the statement is then not used.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives   protein_free_control
membrane_system           bilayer_integrity + protein_free_control + purified_protein
attribution_supported     protein_free_control + blocker_control
calibration_applicability signal_over_noise
condition_scope           purified_protein
transport_driving_force   solutions_stated + driving_force_correction
transport_endpoint        driving_force_correction
transport_specificity     bi_ionic_gradient + ion_preference
sampling_basis            replicates + events_analysed
variance_correspondence   supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity, matrix_interference, assertion_relevance, transport_response_model) are not selected;
transport_response_model is optional for every kind this converter fills (a conductance, a charge rate or none).
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES
maps each such criterion and reason to its judgement). Each judgement is a researched value of THIS assay made gradual (SOP step 3): full agreement at the
researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the assay gives (never a step),
unknown when the paper states nothing, never conflicting for a short count. A value at or beyond its zero end is conflicting where the paper's own numbers
show against the standard (the stated conductance against its own current and driving force; an amplitude no larger than the noise), and is degree 0 and
still supported where it shows only less than the best (a channel that is not selective still passes the ion). A sheet criterion that is supported carries
the smallest degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and
never changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a
sheet criterion whose members are all not_applicable is not selected.

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the purified protein preparation is analyte_preparation_ref; the
proteoliposome batch fused into the bilayer is immobilized_preparation_ref; the bilayer cup or aperture is not a sample preparation that results share, so
surface_ref is None; dataset_ref as always. (The extraction leaves all four None, since no passage states one.) Qualitative statements keep the existing
vocabulary read for this class. Direction and strength of a stated conductance: literature_transport_response_direction (larger is stronger, ends 1 pS and
100 pS); controls, blanks and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a
wrong value misleads and whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not
verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
DRIVING_FORCE_FULL_FACTOR 1.1 -> DRIVING_FORCE_ZERO_FACTOR 3.0, judged on |ln(stated conductance / (current / |V - Vrev|))|.
  Q1 a "conductance" that is really the current over the holding voltage, or over a wrong driving force. The Fluc case of the old review: dividing
  1.8 pA by 0.200 V gives 9 pS, dividing by the driving force of 0.253 V gives 7.1 pS, a factor 1.27 (from memory, not verified). Q2 general:
  the single-channel conductance is the slope of the unitary current against the driving force, g = i / (V - Vrev) (Hille, Ion Channels of Excitable
  Membranes; Sakmann and Neher, Single-Channel Recording), from memory. Q3 relative to the paper's own current and voltages, which the grader records.
  Q4 the factor between a current over V and a current over V - Vrev is |V / (V - Vrev)|; it is 3 when the reversal potential is two thirds of the
  holding voltage, a gross error; a value stated to two digits and a chord against a slope conductance of a channel that rectifies differ by about 10
  percent and more, so full agreement is kept up to 1.1 and the degree falls linearly in the log of the factor (a ratio of two values has multiplicative
  error). At or beyond a factor of 3 the stated conductance is not this current's conductance (conflicting). Q5 a log-ratio ramp like the other ratio
  judgements (the fold gaps of the binding assays).
SIGNAL_OVER_NOISE_FULL 5.0 -> SIGNAL_OVER_NOISE_ZERO 1.0, judged linearly in the ratio of the unitary current to the rms noise.
  Q1 single-channel steps that are not told from the baseline noise, so that the stated size is partly noise. Q2 general: events are detected reliably
  when the amplitude is several times the rms noise (half-amplitude threshold detection; Colquhoun and Sigworth in Single-Channel Recording, from memory;
  the exact 5 is a judgement). Q3 relative to the paper's own noise, which the grader records. Q4 the threshold sits at half the amplitude, so it lies at
  a / (2 sigma) standard deviations of a Gaussian baseline: 2.5 at a ratio of 5 (about 0.6 percent of baseline points above it), 0.5 at a ratio of 1
  (almost a third); a z score is linear in the ratio, so the degree is linear in the ratio. At or below a ratio of 1 the step is no larger than the
  noise (conflicting). Q5 no other class has it; the ramp shape (linear in the quantity whose error is additive) is that of the Pearson coefficient of the
  co-localization.
PERMEABILITY_FULL_RATIO 10.0 -> PERMEABILITY_ZERO_RATIO 1.0, judged on the log of the ratio, supported even at the zero end.
  Q1 a channel that passes the ion but also passes the other ion as well, so the reversal potential does not identify the carrier. Q2 general: a
  permeability ratio is called selective from about 10 (anion against cation channels, from memory) and ion-selective channels of the K+ or Fluc kind
  reach 100 or more (Fluc P_F/P_Cl above about 100, from the old review; from memory, not verified). Q3 relative to the other ion of the paper's own
  comparison; the record keeps whether the named ion is the preferred one (the grader records it) and the judgement is made only when the paper says it is
  (the ratio has no orientation otherwise: unknown). Q4 the ratio comes from the shift of the reversal potential, P_A / P_B = exp(dVrev F / RT), so a
  fixed shift of the reversal potential is a fixed factor and the degree is linear in the log of the ratio (59 mV is a factor ten of a monovalent
  ion at 25 C). A ratio of 1 means no selectivity, not that the ion is not passed, so the zero end gives degree 0 and stays supported, never
  conflicting (only the paper saying the channel prefers the other ion is conflicting, in the grader). Q5 the log-ratio ramp of the other ratio judgements.
EVENTS_FULL_CREDIT 30, degree min(1, sqrt(n / 30)).
  Q1 a unitary size read from a handful of events. Q2 practice: an amplitude histogram needs tens of events to place its peak, and about thirty make the
  mean of a roughly normal amplitude distribution stable (from memory; lab-specific). Q3 absolute count. Q4 the standard error of the mean amplitude
  falls as 1 / sqrt(n), so the degree is the precision relative to that at 30 events; events of one bilayer are not independent replicates (they only
  fix the amplitude), which is why this count is kept apart from the bilayer count. Q5 the shared precision shape of the counts.
BILAYERS_FULL_CREDIT 3, degree min(1, sqrt(n / 3)).
  Q1 a channel property read from one bilayer, whose insertion, orientation and lipid film vary between bilayers. Q2 general (triplicate practice; at
  least three bilayers, ideally from two protein preparations; from memory). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n
  used for the variance. Q5 exactly the shared replicate rule (the independent unit here is the bilayer, not the event).
Facts with no number (the protein-free bilayer, the integrity of the bilayer, the stated solutions, the driving-force correction, the bi-ionic gradient, the
blocker, the purified protein): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to
soften. NOT judged, and why: the holding voltage and the reversal potential alone (they are the paper's own conditions; they only enter the comparison of the
conductance); the open probability and the gating (not collected); the temperature and the lipid (the claim carries no condition, and the identity block records
the temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered
for this assay, decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The current of single molecules across a defined bilayer, and from it the unitary conductance and, by the
  reversal potential, the ion that carries it: absolute and intensive (a conductance in pS needs no amount of protein), in a system of protein, lipid and
  two solutions only.
  Is there a reference range we would trust if the paper stated less (as for KD)? Yes for the size of channels (a few pS to a few hundred pS), so a stated
  conductance is read on a well-known scale; no reference range for the identity of the ion.
  What does an unstated control or calibration do to the number's meaning? An unstated protein-free bilayer is usually benign when the bilayer is quiet,
  but the dominant false positive of this assay is a contaminating channel or pore-forming peptide in the preparation, which a protein-free bilayer
  does not show and a blocker or a purified protein would; an unstated driving force correction changes the size (a factor about 1.3 in the Fluc case), not the
  existence; an unstated amplifier setting or filter is benign for an amplitude well above the noise.
  If we assume it is fine and are wrong, how badly does the score mislead? A contaminant counted as the protein's channel gives a wrong direction (worse
  than a wrong KD size); a wrong driving force gives a wrong size only.
  Consistent with KD? The default 0.85 is just under the KD anchor 0.90, as for spectro_direct (a channel record has a few more ways to be wrong than a KD
  by a label-free method). The criteria that guard against a contaminant weigh less; the benign ones weigh as much as the anchor.
  default 0.85. background_alternatives 0.75 (a real gap: the protein-free bilayer is what separates the protein from a contaminant or a leaky bilayer).
  attribution_supported 0.75 (a contaminating channel is the main way to be wrong; a protein-free bilayer, a blocker or a purified protein answer it).
  transport_specificity 0.80 (the ion that carries the current is established only by a bi-ionic reversal potential, and charge flow is not ion flow).
  transport_driving_force 0.90, calibration_applicability 0.90, sampling_basis 0.90 (benign when unstated: the usual recording solutions are known, a wrong
  driving force changes the size and not the existence, amplifier and filter practice is standard, three bilayers are usual). membrane_system,
  transport_endpoint, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import TRANSPORT_KIND_OF_QUANTITY
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_response_direction import select_transport_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_transport_planar_bilayer_converted'
CRITERIA_MAP = {'background_alternatives': ('protein_free_control',), 'membrane_system': ('bilayer_integrity', 'protein_free_control', 'purified_protein'),
                'attribution_supported': ('protein_free_control', 'blocker_control'), 'calibration_applicability': ('signal_over_noise',),
                'condition_scope': ('purified_protein',), 'transport_driving_force': ('solutions_stated', 'driving_force_correction'),
                'transport_endpoint': ('driving_force_correction',), 'transport_specificity': ('bi_ionic_gradient', 'ion_preference'),
                'sampling_basis': ('replicates', 'events_analysed')}
DRIVING_FORCE_FULL_FACTOR = 1.1  # EXPERT_REVIEW, owner to confirm: the stated conductance may differ from the current over the driving force by this factor (two-digit rounding of three stated numbers, and a chord against a slope conductance of a channel that rectifies; from memory, not verified); full agreement up to it.
DRIVING_FORCE_ZERO_FACTOR = 3.0  # EXPERT_REVIEW, owner to confirm: a factor of 3 is what dividing by the holding voltage instead of the driving force gives when the reversal potential is two thirds of the holding voltage (the Fluc case is a factor 1.27): the stated number is not this current's conductance (no agreement); the degree falls linearly in the log of the factor from the full end to here.
SIGNAL_OVER_NOISE_FULL = 5.0  # EXPERT_REVIEW, owner to confirm: unitary current over the rms noise at which half-amplitude threshold detection puts the threshold 2.5 standard deviations of the baseline above it (about 0.6 percent of the baseline points; Colquhoun and Sigworth, Single-Channel Recording, from memory, not verified); full agreement from it.
SIGNAL_OVER_NOISE_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: a step no larger than the rms noise cannot be told from the baseline (the half-amplitude threshold is 0.5 standard deviations from the baseline: no agreement); the degree rises linearly in the ratio (a z score of the threshold is linear in it).
PERMEABILITY_FULL_RATIO = 10.0  # EXPERT_REVIEW, owner to confirm: a permeability ratio of about ten (a reversal-potential shift of about 59 mV for a monovalent ion at 25 C) is the usual start of what is called selective (from memory, not verified); full agreement from it.
PERMEABILITY_ZERO_RATIO = 1.0  # EXPERT_REVIEW, owner to confirm: a ratio of 1 is no selectivity between the two ions (it does not say the ion is not passed, so the criterion stays supported at degree 0); the degree rises linearly in the log of the ratio (P ratio = exp(dVrev F / RT)).
# EXPERT_REVIEW, owner to confirm: number of single-channel events behind the stated size that gets full credit; about thirty make the mean of a roughly normal amplitude distribution stable (from memory, not verified). Gradual:
# below it the degree is sqrt(n / 30), the precision of the mean over n events relative to that over thirty. Events of one bilayer are not replicates. Fewer events are weaker evidence, not evidence against.
EVENTS_FULL_CREDIT = 30
# EXPERT_REVIEW, owner to confirm: number of independent bilayers that gets full credit (triplicate practice; ideally from two protein preparations; from memory, not verified).
# Gradual: below it the degree is sqrt(n / 3) (owner rule: replicates mean precision in every assay); 1 -> about 0.58, 2 -> about 0.82, full from three.
BILAYERS_FULL_CREDIT = 3
# The anchor unit of each effect quantity (literature_row_contract.TRANSPORT_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (1 nS is 1000 pS); the stated number is the paper's. 'charges_per_s' is the anchor 'elementary_charge_equivalents_per_s' itself.
    'unitary_conductance': ('pS', {'pS': 1.0, 'nS': 1.0e3}),
    'charge_rate': ('elementary_charge_equivalents_per_s', {'charges_per_s': 1.0}),
}
KIND_WITHOUT_EFFECT = 'electrical_conductance'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'a_bilayer_recording_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_unitary_current_is_not_an_attribution_fraction', 'total_signal': 'a_unitary_current_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_bilayer_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_bilayer_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENT = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "transport detected" / "transport not detected" / "transport not stated" for this class


def _verdict(status, refs, degree=None):
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError('a ' + status + ' judgement needs support refs')
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _degree(value, full, zero, scale=lambda x: x):
    """1.0 at ``full`` (or beyond it), falling linearly in ``scale`` to 0 at ``zero`` (the limits may lie on either side of each other); None at or beyond ``zero``.
    ``scale`` is monotone, so the side test is made on the value itself (before a log could see a value at or below 0)."""
    if (value - zero) * (full - zero) <= 0:
        return None
    return min(1.0, (scale(value) - scale(zero)) / (scale(full) - scale(zero)))


def _judge_driving_force(native):
    # the log of the factor between the stated conductance and the one the current and the driving force give, from the full factor to the zero factor
    refs = native['driving_force_refs']
    gap = abs(math.log(native['stated_conductance_pS'] / native['current_over_driving_force_pS']))
    degree = _degree(gap, math.log(DRIVING_FORCE_FULL_FACTOR), math.log(DRIVING_FORCE_ZERO_FACTOR))
    return _verdict('conflicting', refs) if degree is None else _verdict('supported', refs, degree)


def _judge_noise(native):
    refs = native['noise_refs']
    degree = _degree(native['amplitude_over_noise'], SIGNAL_OVER_NOISE_FULL, SIGNAL_OVER_NOISE_ZERO)
    return _verdict('conflicting', refs) if degree is None else _verdict('supported', refs, degree)


def _judge_permeability(native):
    if native['named_ion_preferred'] != 'yes':
        return _verdict('unknown', native['permeability_refs'])      # the ratio has no orientation unless the paper says the named ion is the preferred one (a stated no is the grader's conflicting)
    degree = _degree(native['permeability_ratio'], PERMEABILITY_FULL_RATIO, PERMEABILITY_ZERO_RATIO, math.log)
    return _verdict('supported', native['permeability_refs'], 0.0 if degree is None else degree)      # no selectivity is not evidence against the ion being passed


def _judge_events(native):
    # the precision of the mean over n events relative to that over the researched number (standard error ~ 1 / sqrt(n)); full credit at EVENTS_FULL_CREDIT
    return _verdict('supported', native['event_refs'], min(1.0, math.sqrt(native['event_count'] / EVENTS_FULL_CREDIT)))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / BILAYERS_FULL_CREDIT)))      # precision of the mean, see BILAYERS_FULL_CREDIT


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('driving_force_correction', 'driving_force_recorded_for_the_sheet'): _judge_driving_force, ('signal_over_noise', 'amplitude_over_noise_recorded_for_the_sheet'): _judge_noise,
          ('ion_preference', 'permeability_ratio_recorded_for_the_sheet'): _judge_permeability, ('events_analysed', 'event_count_recorded_for_the_sheet'): _judge_events,
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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'transport_planar_bilayer_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


def _variance(graded, quantity, ref):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of ``quantity``."""
    native = graded['native']
    if quantity != 'unitary_conductance':
        return None, quantity + '_has_no_spread_field', []
    spread = native['quantities']['unitary_conductance_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, 'unitary_conductance_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    unit, factors = UNIT_FACTORS[quantity]
    sd = spread['value'] * factors[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['bilayer_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_bilayers_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_transport_planar_bilayer(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {quantity: _stated_effect(native, quantity, ref) for quantity in UNIT_FACTORS}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_conductance_or_charge_rate_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_transport_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = TRANSPORT_KIND_OF_QUANTITY[chosen], effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'transport_planar_bilayer_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
    null_components.update({role: reason for role, reason in NULL_REASONS.items()})
    interpretations = {}
    for sheet_criterion, members in CRITERIA_MAP.items():
        graded_members = [apply_support(_criterion(graded, m), native['support'][m]) for m in members if graded['criteria'][m]['status'] != 'not_applicable']      # weak quote support lowers the degree of a supported member, never its status
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'transport_response', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    converted = {'version': VERSION, 'experiment_type': 'transport_planar_bilayer', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
                 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no stated quantity: the paper's own yes/no result stands, scored like any stated result (literature_direction, the qualitative path)
        converted['qualitative_effect'] = {'statement': STATEMENT[native['transport']], 'support_refs': list(native['transport_refs'])}
        if native['transport'] is not None:
            converted['direction_field_support'] = native['transport_support']      # the support class of the fact transport_detected_above_control, the one field the statement is derived from
    return converted
