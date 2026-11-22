"""Transport_patch_clamp converter: turns the grader's result into what the A105 transport_response sheet takes. DRAFT 2026-11-22, owner to correct.

Hand-built, private to transport_patch_clamp, deterministic. Input: the result of grade_transport_patch_clamp. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'transport_response'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, the qualitative
effect when no quantity is stated, and for every sheet component that a patch-clamp experiment cannot honestly fill, the reason it stays null. It is a
draft built on the shape of literature_spectro_direct_converter.py and literature_transport_cell_tracer_uptake_converter.py, with the class core of
transport_response (A105_TRANSPORT_RESPONSE_INVENTORY.md, sections 2 and 4; literature_transport_response_direction.py).

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: the unitary conductance (pS, kind electrical_conductance), the charge rate per channel
                  (elementary_charge_equivalents_per_s, kind charge_equivalent_rate) or the fold over the paper's own control (dimensionless, kind
                  transport_rate_ratio). Several may be stated; the one used is the best-determined, in the class order TRANSPORT_EFFECT_ORDER
                  (literature_transport_response_direction.select_transport_effect: unitary conductance, then charge rate, then fold over the control).
                  A stated value in another unit of the record's vocabulary is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION): the value is the
                  paper's, only its unit spelling changes (nS is 1000 pS; "charges/s" is the sheet's elementary charge equivalents per second; a stated "n-fold" is
                  the dimensionless ratio n). quantity_kind of the extraction names the kind of the effect (KIND_OF_QUANTITY), which the direction function reads.
                  A current, a current density, a reversal potential and a whole-cell conductance are not effects of this class and are not in the record (a Km is
                  not asked either: a dose-response of a current is kept for the oocyte type).
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it: standard_error -> se^2;
                  standard_deviation -> sd^2 / n with n the number of CELLS (cells are the sampling unit of the method, not sweeps), and only when the replicates
                  criterion is supported and a cell count is stated; confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery, attributed signal/total signal, condition test/reference (the current with and without the
substrate is a control FACT here, not a stated pair of values), the assertion and alternative predictions.
qualitative_effect  only when NO effect is stated: statement 'interaction_detected' (read "transport detected"), 'interaction_not_detected' (read "transport not
                  detected") or 'interaction_not_stated', with the refs of the fact transport_detected_above_control that states it; direction_field_support is the
                  quote support of that one fact. A stated effect fixes the direction; the statement is then not used. A result stated in words alone already counts
                  less than a measured one (the contract's stated_strength); this file does not repeat it.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives    host_cell_control + substrate_free_control
attribution_supported      inactive_mutant_control + blocker_control
calibration_applicability  series_resistance_error + seal_and_leak
assertion_relevance        native_substrate
membrane_system            host_cell_control + seal_and_leak
transport_endpoint         unitary_events_resolved + driving_force_correction
transport_driving_force    voltage_stated + reversal_potential_match
transport_specificity      ion_substitution + reversal_potential_match
sampling_basis             replicates
variance_correspondence    supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity, matrix_interference, condition_scope, transport_response_model) are not selected: the identity block
records the temperature and the pH; the host cell's own currents are the matrix and are carried by host_cell_control; no Km or concentration series is asked, and
the sheet makes transport_response_model optional for a conductance, a charge rate and a ratio kind (literature_assay_grading._required_criteria). A criterion may
sit under two sheet criteria (host_cell_control, seal_and_leak, reversal_potential_match): the same fact answers two questions of the sheet.
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps
each such criterion and reason to its judgement). Each judgement is a researched value of THIS method made gradual (SOP step 3): full agreement at the researched
good value, falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the method gives (never a step), unknown when the
paper states nothing, never conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper itself shows against the standard). A
sheet criterion that is supported carries the smallest degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the
degree of a supported criterion and never changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported.
not_applicable members are dropped; a sheet criterion whose members are all not_applicable is not selected.

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the cell culture (or transfection) that makes the protein is
analyte_preparation_ref; immobilized_preparation_ref and surface_ref stay None (the pipette is not a sample preparation that results share, and a cell has no
vesicle batch or sensor); dataset_ref as always. Qualitative statements keep the existing vocabulary, read "transport detected / not detected / not stated". Direction
and strength of a stated quantity: literature_transport_response_direction (same paradigm as binding and activity; larger is stronger for the conductance, the
charge rate and the fold); controls, recording quality and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value
misleads and whether the shape fits, Q5 consistency with the other assays). EVERY number below is EXPERT_REVIEW, owner to confirm, and every literature statement
is "from memory, not verified": none was checked against a paper in this draft.
-----------------------------------------------------------------------------------------------------------------------------------
SERIES_RESISTANCE_FULL_MOHM 5 -> SERIES_RESISTANCE_ZERO_MOHM 30, judged linearly in the resistance.
  Q1 a whole-cell current whose voltage was not the commanded one: the current of the cell makes a voltage drop I x Rs across the series (access) resistance,
  so the membrane sits at the wrong voltage, the current-voltage curve is bent and the reversal potential and conductances shift. Q2 general: the voltage error
  I x Rs is kept to a few millivolts in whole-cell practice (the usual limit is an error under about 5 mV, with cells excluded above 10 to 20 MOhm for
  heterologous cells; Sakmann and Neher, Single-Channel Recording, 2nd ed., 1995; the Axon Guide to Electrophysiology and Biophysics Laboratory Techniques;
  from memory). Q3 the error is relative to the paper's own current, but the current is not asked; the ends assume a whole-cell current of the order of 1 nA, the
  usual size in heterologous cells, so a larger current is judged too kindly and a smaller one too hard. Q4 a wrong end moves only the degree of this criterion,
  never a direction; the shape is linear because the error is proportional to Rs: 5 MOhm at 1 nA is 5 mV (full), 10 MOhm gives degree 0.8, 20 MOhm 0.4, and 30 MOhm
  is a 30 mV error, more than the voltage sensitivity of ordinary gating (a few to ten mV per e-fold) and beyond the usual exclusion limit: no agreement, so a
  stated value at or above it is conflicting. The compensation is not used to rescale the stated value (the percent of compensation is not asked, so a
  compensated recording with a high stated value is judged too hard; the fact series_resistance_compensated counts only when no value is stated). Q5 a bias that
  grows with the departure from the researched value, as in the consumed-substrate curve of spectro_direct.
SEAL_FULL_GOHM 1.0 -> SEAL_ZERO_GOHM 0.1, judged linearly in the leak conductance 1 / R.
  Q1 a leak current through the seal that is read as the current of the protein, which also adds noise and lets the cell's own voltage drift. Q2 general: the method
  is defined by the gigaohm seal (Hamill, Marty, Neher, Sakmann and Sigworth 1981, Pflugers Arch 391:85, from memory; seals of 1 to 100 GOhm are usual and a patch
  or whole-cell recording is usually accepted only above about 1 GOhm). Q3 the leak is relative to the current measured, which is not asked; absolute here, with
  the same 1 nA assumption as above. Q4 the leak current is V / Rseal, linear in the conductance 1 / Rseal, so the degree is linear in it: 1 GOhm is 1 nS, a leak of
  60 pA at -60 mV (full agreement); 0.1 GOhm is 10 nS, 600 pA at -60 mV, as large as a small whole-cell current and no longer a seal (no agreement, conflicting). A
  seal better than 1 GOhm is full (the degree is capped at 1). A wrong end moves only the degree. Q5 the same departure-grows-the-bias idea as the series resistance.
REVERSAL_FULL_MV 5 -> REVERSAL_ZERO_MV 60, judged linearly in the distance |reversal potential - Nernst potential|.
  Q1 a current that is charge flow but not the flow of the claimed ion: the reversal potential of a channel selective for the claimed ion lies at that ion's Nernst
  potential, and a distance means another ion carries the current (charge flow is kept apart from identified-ion flow). Q2 general: the Nernst potential is the
  reversal potential of a perfectly selective channel; liquid junction potentials and the error of the pipette and bath concentrations leave a few millivolts
  (a junction potential of up to about 10 mV is uncorrected in much work; Neher 1992, Methods Enzymol 207:123, from memory), so 5 mV is full; the Goldman-Hodgkin-Katz
  equation moves the reversal by about 58 mV per tenfold change in the ratio of permeabilities at room temperature (for a monovalent ion; from memory), so a
  distance of 60 mV means another ion is about ten times more permeant: the claimed ion no longer carries the current (no agreement, conflicting). A divalent
  ion has half the millivolts per decade, so the same distance is more decades; the valence is not asked and the ends are those of a monovalent ion. Q3 relative to
  the paper's own Nernst potential, which the grader records with the reversal potential: right. Q4 a wrong end moves only the degree of the two sheet criteria it feeds
  (specificity and driving force), never a direction; the distance is an additive scale in millivolts, so the ramp is linear. Q5 no other assay has a potential.
CELLS_FULL_CREDIT 5, degree min(1, sqrt(n / 5)).
  Q1 a result from one or two cells: the cell-to-cell spread of the current of transfected cells is large (expression varies several-fold; a coefficient of variation of
  0.5 or more is usual, from memory), and sweeps or traces of one cell are not independent. Q2 general: patch-clamp papers report n of about 5 to 15 cells per
  condition; five is the usual least (journal reporting practice, from memory). Q3 absolute count of cells (the sampling unit). Q4 precision of a mean goes as
  1 / sqrt(n): one cell 0.45, two 0.63, three 0.77, four 0.89, full from five; never conflicting for a stated count. Q5 the shared replicate rule, sqrt(n / full-credit number).
BATCHES_FULL_CREDIT 3, degree min(1, sqrt(m / 3)).
  Q1 all cells from one transfection or one dish share expression, passage and day, so they are not independent preparations. Q2 general (triplicate practice;
  Cumming, Fidler and Vaux 2007, J Cell Biol 177:7, from memory). Q3 absolute count of independent transfections, cultures or preparations. Q4 sqrt(m / 3): one 0.58,
  two 0.82, full from three. Q5 exactly the shared replicate rule and the number the other assays use.
  The replicates criterion takes the smaller of the two degrees that are stated, and only when independence is stated as yes; independence not stated gives unknown.
Facts with no number (the host-cell, mutant, substrate-free and blocker controls, the ion substitution, the single-channel resolution, the driving-force correction,
the leak subtraction, the compensation and the native substrate): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown (not
applicable for the two conductance facts when no conductance or charge rate is stated). They have no researched value to soften. NOT judged, and why: the size of the
conductance, the charge rate and the fold (they are the effect, graded on their own scale by the direction function, not a quality of the experiment); the holding
voltage's value (a convention, only its being stated counts); the temperature and the pH (the claim carries no condition, and the identity block records them).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this assay,
decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The membrane current of a cell under a clamped voltage: absolute in form (pS, pA), a direct electrical readout of charge
  movement, but its meaning rests on the control cells (the host has its own channels) and charge flow is not the flow of one ion.
  Is there a reference range we would trust if the paper stated less (as for KD)? Partly: the unitary conductances of ion channels (about 1 to 100 pS) are a well-known
  range and the anchors are built on it; a stated conductance with a stated ion substitution is a standard identification. The current of a cell depends on expression,
  which a paper may not state.
  What does an unstated control or calibration do to what the number means? An unstated host-cell control is the dominant false positive of the assay (endogenous
  channels and transporters of HEK or CHO cells can carry the whole current); an unstated ion substitution leaves the carrier unidentified (the current is charge flow,
  not the flow of the claimed ion); an unstated mutant or blocker leaves the attribution open. An unstated series resistance, seal or leak subtraction is benign:
  papers apply exclusion criteria that they do not always state, and the error is one of degree.
  If we assume it is fine and are wrong, how badly does the score mislead? A host current counted as the protein's, or the charge flow of another ion counted as the
  claimed ion's: the wrong direction for a weak current and a wrong size for a strong one; worse than a KD (a size only), less than a pull-down band (a pure artefact).
  Consistent with KD? The default 0.80 sits between spectro_direct (0.85, a purified enzyme) and transport_cell_tracer_uptake (0.75, whole cells with metabolism): a
  patch-clamp current is a direct electrical readout with a signature (reversal potential, block, ion dependence) that tracer uptake has not, but a host cell. The
  guards against a false transport are lower, the benign details are near the KD anchor.
  default 0.80. background_alternatives 0.65 (the host-cell control), attribution_supported 0.70 (mutant and blocker leave the current's owner open), transport_specificity
  0.60 (ion identity: charge flow is not ion flow), calibration_applicability 0.90 and sampling_basis 0.85 (benign when unstated); membrane_system, transport_endpoint,
  transport_driving_force and assertion_relevance take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_response_direction import select_transport_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_transport_patch_clamp_converted_v1'
CRITERIA_MAP = {'background_alternatives': ('host_cell_control', 'substrate_free_control'), 'attribution_supported': ('inactive_mutant_control', 'blocker_control'),
                'calibration_applicability': ('series_resistance_error', 'seal_and_leak'), 'assertion_relevance': ('native_substrate',),
                'membrane_system': ('host_cell_control', 'seal_and_leak'), 'transport_endpoint': ('unitary_events_resolved', 'driving_force_correction'),
                'transport_driving_force': ('voltage_stated', 'reversal_potential_match'), 'transport_specificity': ('ion_substitution', 'reversal_potential_match'),
                'sampling_basis': ('replicates',)}
SERIES_RESISTANCE_FULL_MOHM = 5.0  # EXPERT_REVIEW, owner to confirm: a series resistance up to about 5 MOhm gives a voltage error I x Rs of about 5 mV at a whole-cell current of 1 nA, the usual limit of whole-cell practice (Sakmann and Neher 1995; Axon Guide; from memory, not verified); full agreement up to it.
SERIES_RESISTANCE_ZERO_MOHM = 30.0  # EXPERT_REVIEW, owner to confirm: 30 MOhm gives a 30 mV error at 1 nA, more than the voltage sensitivity of ordinary gating and beyond the usual exclusion limit of 10 to 20 MOhm (from memory, not verified): no agreement (conflicting); the degree falls from SERIES_RESISTANCE_FULL_MOHM linearly in the resistance, because the error is proportional to it.
SEAL_FULL_GOHM = 1.0  # EXPERT_REVIEW, owner to confirm: the gigaohm seal that defines the method (Hamill et al. 1981; from memory, not verified); 1 GOhm is a leak conductance of 1 nS, 60 pA at -60 mV; full agreement from it up (a tighter seal is capped at full).
SEAL_ZERO_GOHM = 0.1  # EXPERT_REVIEW, owner to confirm: 0.1 GOhm is 10 nS, 600 pA at -60 mV, as large as a small whole-cell current and no longer a seal (no agreement, conflicting); the degree falls from SEAL_FULL_GOHM linearly in the leak conductance 1 / R, because the leak current is proportional to it.
REVERSAL_FULL_MV = 5.0  # EXPERT_REVIEW, owner to confirm: a measured reversal potential within about 5 mV of the Nernst potential of the claimed ion is as close as junction potentials and solution errors let a selective channel get (a junction potential of up to about 10 mV is uncorrected in much work; Neher 1992; from memory, not verified); full agreement up to it.
REVERSAL_ZERO_MV = 60.0  # EXPERT_REVIEW, owner to confirm: about 58 mV per tenfold change of the permeability ratio for a monovalent ion at room temperature (Goldman-Hodgkin-Katz; from memory, not verified), so 60 mV from the Nernst potential means another ion is about ten times more permeant (no agreement, conflicting); the degree falls from REVERSAL_FULL_MV linearly in millivolts, an additive scale. The valence is not asked (a divalent ion has half the millivolts per decade).
CELLS_FULL_CREDIT = 5  # EXPERT_REVIEW, owner to confirm: number of cells (the sampling unit) that gets full credit; patch-clamp papers report about 5 to 15 cells per condition and the cell-to-cell spread of transfected cells is large (from memory, not verified). Gradual: below it the degree is sqrt(n / 5), the precision of a mean over n cells relative to that over five; never conflicting for a stated count.
BATCHES_FULL_CREDIT = 3  # EXPERT_REVIEW, owner to confirm: number of independent transfections, cultures or preparations that gets full credit (triplicate practice; Cumming, Fidler and Vaux 2007; from memory, not verified). Gradual: below it the degree is sqrt(m / 3) (owner rule: replicates mean precision in every assay); 1 -> about 0.58, 2 -> about 0.82, full from three.
# The anchor unit of each effect quantity (the anchors of the class direction module) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (1 nS is 1e3 pS; charges per second are elementary charge equivalents per second; a stated "n-fold" is the ratio n); the stated number is the paper's.
    'unitary_conductance': ('pS', {'pS': 1.0, 'nS': 1.0e3}),
    'charge_rate': ('elementary_charge_equivalents_per_s', {'charges/s': 1.0}),
    'fold_over_control': ('dimensionless', {'fold': 1.0}),
}
# The name of each effect quantity in the class order TRANSPORT_EFFECT_ORDER (select_transport_effect reads these keys).
ANCHOR_QUANTITY = {'unitary_conductance': 'unitary_conductance', 'charge_rate': 'charge_rate', 'fold_over_control': 'fold_over_control'}
# The quantity_kind (QUANTITY_KINDS['transport_response']) that names the kind of each effect quantity; the direction function reads it back.
KIND_OF_QUANTITY = {'unitary_conductance': 'electrical_conductance', 'charge_rate': 'charge_equivalent_rate', 'fold_over_control': 'transport_rate_ratio'}
KIND_WITHOUT_EFFECT = 'transport_rate'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'a_patch_clamp_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_patch_clamp_value_is_not_an_attribution_fraction', 'total_signal': 'a_patch_clamp_value_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_patch_clamp_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_patch_clamp_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "transport detected" / "transport not detected" / "transport not stated" for this class


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


def _leak_conductance(gohm):
    """The leak conductance of a seal in nS: 1 / R with R in GOhm (1 / GOhm is exactly nS)."""
    return 1.0 / gohm


def _judge_series_resistance(native):
    return _graded(native['series_resistance_refs'], (native['series_resistance_mohm'], SERIES_RESISTANCE_FULL_MOHM, SERIES_RESISTANCE_ZERO_MOHM))


def _judge_seal(native):
    return _graded(native['seal_resistance_refs'], (_leak_conductance(native['seal_resistance_gohm']), _leak_conductance(SEAL_FULL_GOHM), _leak_conductance(SEAL_ZERO_GOHM)))


def _judge_reversal(native):
    return _graded(native['reversal_refs'], (abs(native['reversal_minus_nernst_mv']), REVERSAL_FULL_MV, REVERSAL_ZERO_MV))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    degrees = []
    if native['cell_count'] is not None:
        degrees.append(min(1.0, math.sqrt(native['cell_count'] / CELLS_FULL_CREDIT)))      # precision of the mean over n cells, see CELLS_FULL_CREDIT
    if native['batch_count'] is not None:
        degrees.append(min(1.0, math.sqrt(native['batch_count'] / BATCHES_FULL_CREDIT)))      # precision over m independent preparations, see BATCHES_FULL_CREDIT
    return _verdict('supported', native['replicate_refs'], min(degrees))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('series_resistance_error', 'series_resistance_recorded_for_the_sheet'): _judge_series_resistance, ('seal_and_leak', 'seal_recorded_for_the_sheet'): _judge_seal,
          ('reversal_potential_match', 'reversal_recorded_for_the_sheet'): _judge_reversal, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'transport_patch_clamp_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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
        count = native['quantities']['cell_count']
        if count['status'] != 'point' or _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_a_cell_count_and_independent_preparations_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_transport_patch_clamp(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {ANCHOR_QUANTITY[quantity]: _stated_effect(native, quantity, ref) for quantity in UNIT_FACTORS}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_transport_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        anchor, effect = select_transport_effect(stated)
        chosen = next(quantity for quantity, name in ANCHOR_QUANTITY.items() if name == anchor)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_QUANTITY[chosen], effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'transport_patch_clamp_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    result = {'version': VERSION, 'experiment_type': 'transport_patch_clamp', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no stated quantity: the paper's own statement of transport above its control fixes the direction (the support of the one fact it is derived from)
        result['qualitative_effect'] = {'statement': STATEMENTS[native['transport']], 'support_refs': list(native['transport_refs'])}
        if native['transport'] is not None:
            result['direction_field_support'] = native['transport_support']
    return result
