"""ITC converter: turns the ITC grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to ITC, deterministic. Input: the result of grade_itc.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the sheet
itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR converter fills), the dependence keys the
merger needs, and for every sheet component an ITC KD cannot honestly fill,
the reason it stays null.

Quantities filled
-----------------
effect            the ITC KD in nM (point operand), only when the source
                  gave a KD as a point value. Otherwise null.
effect_variance   variance of that KD estimate, nM_squared, only when the
                  source's spread allows it: standard_error -> se^2;
                  standard_deviation -> sd^2 / n, and only when the
                  replicate_titrations_independent criterion is supported;
                  confidence_interval -> not converted (needs its level and
                  degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).

Dependence keys handed to the merger (same four keys as the SPR converter):
analyte_preparation_ref = the syringe preparation, immobilized_preparation_ref
= the cell preparation (the partner held in the vessel), surface_ref = None
(ITC has no surface), dataset_ref = the dataset.

Criteria mapping (ITC criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              heat_of_dilution_control + buffer_matching
binding_regime                c_value_window + injections_sufficient +
                              temperature_stated_and_controlled
binding_parameter_definition  fit_model_appropriate + thermodynamic_consistency
binding_species               concentration_accuracy_and_active_fraction
calibration_applicability     stoichiometry_consistency
sampling_basis                replicate_titrations_independent
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and
hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps
each such criterion and reason to its judgement):
concentration_accuracy_and_active_fraction judged on n / expected n (full
agreement from N_OVER_EXPECTED_MIN to N_OVER_EXPECTED_MAX), unknown when a
fact is unknown; c_value_window judged on c (full agreement from C_VALUE_MIN to
C_VALUE_MAX); injections_sufficient conflicting below MIN_INJECTIONS;
temperature_stated_and_controlled conflicting outside TEMPERATURE_MIN_K to
TEMPERATURE_MAX_K, else by the control answer (yes supported, unknown unknown,
not_applicable not applicable); replicate_titrations_independent conflicting
below MIN_REPLICATE_TITRATIONS, else supported when the independence is yes,
else unknown; stoichiometry_consistency judged on the fitted n (full agreement
from STOICHIOMETRY_MIN) and on its distance from a multiple of STOICHIOMETRY_STEP
(full agreement up to STOICHIOMETRY_STEP_TOLERANCE), unknown when the free fit is
not stated yes; thermodynamic_consistency judged on the gap of the two free
energies (full agreement up to DG_TOLERANCE_KJ_PER_MOL). A continuous comparison
is supported with a degree of 1.0 at its full-agreement limit, falling linearly
to 0 at its zero-agreement limit (the *_ZERO_* constants), and conflicting (no
degree) at or beyond that limit; counts and the temperature range get no degree.
A sheet criterion that is supported carries the smallest degree of its members
that have one (the sheet reads no degree; it travels with the interpretation and
the merger carries it per result).
Combined status: any conflicting -> conflicting; else any unknown -> unknown;
else supported. not_applicable members are dropped; a sheet criterion whose
members are all not_applicable is not selected. Sheet criteria with no ITC
counterpart are not selected.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_itc_converted_v1'
CRITERIA_MAP = {'binding_controls': ('heat_of_dilution_control', 'buffer_matching'), 'binding_regime': ('c_value_window', 'injections_sufficient', 'temperature_stated_and_controlled'), 'binding_parameter_definition': ('fit_model_appropriate', 'thermodynamic_consistency'), 'binding_species': ('concentration_accuracy_and_active_fraction',), 'calibration_applicability': ('stoichiometry_consistency',), 'sampling_basis': ('replicate_titrations_independent',)}
N_OVER_EXPECTED_MIN = 0.7  # EXPERT_REVIEW: fitted n / expected n below this suggests an inactive fraction or a concentration error; full agreement from it.
N_OVER_EXPECTED_ZERO_MIN = 0.3  # EXPERT_REVIEW: fitted n under a third of the expected n is mostly inactive protein or a gross concentration error (no agreement); falls linearly from N_OVER_EXPECTED_MIN.
N_OVER_EXPECTED_MAX = 1.3  # EXPERT_REVIEW: fitted n / expected n above this suggests a concentration error or non-specific heat; full agreement up to it.
N_OVER_EXPECTED_ZERO_MAX = 2.0  # EXPERT_REVIEW: fitted n at twice the expected n or more is another stoichiometry or a gross concentration error (no agreement); falls linearly from N_OVER_EXPECTED_MAX.
C_VALUE_MIN = 1.0  # EXPERT_REVIEW: below c = 1 the curve is too flat and KD is poorly determined; full agreement from it.
C_VALUE_ZERO_MIN = 0.1  # EXPERT_REVIEW: at c = 0.1 the isotherm is a nearly straight line and KD is not determined (no agreement); falls linearly from C_VALUE_MIN.
C_VALUE_MAX = 1000.0  # EXPERT_REVIEW: above c = 1000 the curve is a step and only a limit on KD is determined; full agreement up to it.
C_VALUE_ZERO_MAX = 10000.0  # EXPERT_REVIEW: at c = 10000 the curve is a step with no usable shape (no agreement); falls linearly from C_VALUE_MAX.
MIN_INJECTIONS = 15  # EXPERT_REVIEW: fewest injections for a defined binding isotherm.
TEMPERATURE_MIN_K = 278.15  # EXPERT_REVIEW: lowest temperature (5 C) for a plausible calorimeter experiment (a range of plausibility, no degree).
TEMPERATURE_MAX_K = 323.15  # EXPERT_REVIEW: highest temperature (50 C) for a plausible calorimeter experiment (a range of plausibility, no degree).
MIN_REPLICATE_TITRATIONS = 3  # EXPERT_REVIEW: fewest independent replicate titrations.
STOICHIOMETRY_MIN = 0.4  # EXPERT_REVIEW: a fitted n below this is not a meaningful stoichiometry; full agreement from it.
STOICHIOMETRY_ZERO_MIN = 0.2  # EXPERT_REVIEW: half of STOICHIOMETRY_MIN, a fitted n this small is noise (no agreement); falls linearly from STOICHIOMETRY_MIN.
STOICHIOMETRY_STEP = 0.5  # EXPERT_REVIEW: the step of a simple stoichiometry (n is expected near a multiple of one half).
STOICHIOMETRY_STEP_TOLERANCE = 0.15  # EXPERT_REVIEW: fitted n must lie this close (absolute) to a multiple of STOICHIOMETRY_STEP; full agreement up to it.
STOICHIOMETRY_STEP_ZERO = 0.25  # EXPERT_REVIEW: half the step, the farthest a number can be from a multiple of it (exactly between two simple ratios; no agreement); falls linearly from STOICHIOMETRY_STEP_TOLERANCE.
DG_TOLERANCE_KJ_PER_MOL = 2.0  # EXPERT_REVIEW: allowed gap between dG from KD and dG from dH - T dS; full agreement up to it.
DG_ZERO_KJ_PER_MOL = 10.0  # EXPERT_REVIEW: a gap of 10 kJ/mol is about a 60-fold error in KD at room temperature, so the KD and the enthalpy-entropy pair describe different binding (no agreement); falls linearly from DG_TOLERANCE_KJ_PER_MOL.
NULL_REASONS = {'recovery': 'itc_has_no_matrix_recovery_measurement', 'attributed_signal': 'itc_heat_of_dilution_control_is_not_an_attribution_fraction', 'total_signal': 'itc_heat_of_dilution_control_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_itc_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_itc_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _graded(refs, *limits):
    """Each limit is (value, full_agreement_limit, zero_agreement_limit). Conflicting when any value is at or beyond its zero limit; else supported with the smallest degree, 1.0 at the full limit falling linearly to 0 at the zero limit."""
    degrees = [(zero - value) / (zero - full) for value, full, zero in limits]
    if min(degrees) <= 0:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, *degrees))


def _judge_n_over_expected(native):
    ratio = native['n_over_expected']
    verdict = _graded(native['n_over_expected_refs'], (ratio, N_OVER_EXPECTED_MIN, N_OVER_EXPECTED_ZERO_MIN), (ratio, N_OVER_EXPECTED_MAX, N_OVER_EXPECTED_ZERO_MAX))
    return _verdict('unknown', []) if verdict['status'] == 'supported' and native['concentration_facts_unknown'] else verdict


def _judge_c_value(native):
    return _graded(native['c_value_refs'], (native['c_value'], C_VALUE_MIN, C_VALUE_ZERO_MIN), (native['c_value'], C_VALUE_MAX, C_VALUE_ZERO_MAX))


def _judge_injections(native):
    return _verdict('supported' if native['injection_count'] >= MIN_INJECTIONS else 'conflicting', native['injection_refs'])


def _judge_temperature(native):
    refs = native['temperature_refs']
    if not TEMPERATURE_MIN_K <= native['temperature_K'] <= TEMPERATURE_MAX_K:
        return _verdict('conflicting', refs)
    control = native['temperature_control']
    return _verdict('supported' if control == 'yes' else 'not_applicable' if control == 'not_applicable' else 'unknown', refs)


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATE_TITRATIONS:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


def _judge_stoichiometry(native):
    n = native['stoichiometry_n']
    distance = abs(n - math.floor(n / STOICHIOMETRY_STEP + 0.5) * STOICHIOMETRY_STEP)
    verdict = _graded(native['stoichiometry_refs'], (n, STOICHIOMETRY_MIN, STOICHIOMETRY_ZERO_MIN), (distance, STOICHIOMETRY_STEP_TOLERANCE, STOICHIOMETRY_STEP_ZERO))
    return _verdict('unknown', []) if verdict['status'] == 'supported' and native['stoichiometry_free'] != 'yes' else verdict


def _judge_free_energies(native):
    return _graded(native['dg_refs'], (native['dg_gap_kJ_per_mol'], DG_TOLERANCE_KJ_PER_MOL, DG_ZERO_KJ_PER_MOL))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('concentration_accuracy_and_active_fraction', 'n_over_expected_recorded_for_the_sheet'): _judge_n_over_expected, ('c_value_window', 'c_value_recorded_for_the_sheet'): _judge_c_value,
          ('injections_sufficient', 'injection_count_recorded_for_the_sheet'): _judge_injections, ('temperature_stated_and_controlled', 'temperature_recorded_for_the_sheet'): _judge_temperature,
          ('replicate_titrations_independent', 'replicate_count_recorded_for_the_sheet'): _judge_replicates, ('stoichiometry_consistency', 'stoichiometry_recorded_for_the_sheet'): _judge_stoichiometry,
          ('thermodynamic_consistency', 'free_energy_gap_recorded_for_the_sheet'): _judge_free_energies}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}


def _variance(graded):
    """Return (variance_nM_squared or None, reason or None, refs)."""
    native = graded['native']
    spread = native['quantities']['kd_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, 'kd_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = spread['value'] * _SCALES[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicate_titrations_independent')['status'] != 'supported':
            return None, 'sd_needs_independent_titrations_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_itc(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    kd = native['quantities']['kd']
    if native['kd_nM'] is None:
        null_components['effect'] = 'kd_not_given_as_a_point_value'
    else:
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'itc_kd:' + ref, kd['source_refs'], kd['origin'], 'kd')
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'itc_kd_variance:' + ref, variance_refs, 'derived', 'kd_spread')
    null_components.update(NULL_REASONS)
    interpretations = {}
    for sheet_criterion, members in CRITERIA_MAP.items():
        graded_members = [m for m in (_criterion(graded, name) for name in members) if m['status'] != 'not_applicable']      # the sheet's own judgement can also be not_applicable (the temperature control)
        if not graded_members:
            continue
        statuses = [m['status'] for m in graded_members]
        status = 'conflicting' if 'conflicting' in statuses else 'unknown' if 'unknown' in statuses else 'supported'
        refs = list(dict.fromkeys(r for m in graded_members for r in m['support_refs']))
        interpretations[sheet_criterion] = {'status': status, 'support_refs': refs if status == 'supported' else []}
        degrees = [m['degree'] for m in graded_members if 'degree' in m]
        if status == 'supported' and degrees:
            interpretations[sheet_criterion]['degree'] = min(degrees)      # the weakest member: a degree of a member is not averaged away
        supports = [s for name in members if _criterion(graded, name)['status'] != 'not_applicable' for s in native['support'][name]]
        interpretations[sheet_criterion] = apply_support(interpretations[sheet_criterion], supports)      # weak quote support lowers the degree of a supported criterion, never its status
    if variance is not None:
        interpretations['variance_correspondence'] = {'status': 'supported', 'support_refs': variance_refs}
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['syringe_preparation_ref'], 'immobilized_preparation_ref': preparations['cell_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    return {'version': VERSION, 'experiment_type': 'itc', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': kd['support'] if native['kd_nM'] is not None else None}
