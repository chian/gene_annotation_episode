"""Trp converter: turns the Trp grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_trp.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR, ITC, BLI, GCI, FP, FRET and MST converters fill), the
dependence keys the merger needs, and for every sheet component that an intrinsic
fluorescence titration cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            the reported KD in nM (point operand; the measurement key is
                  trp_kd). No KD leaves effect null. A Stern-Volmer constant Ksv
                  alone is a quenching efficiency, not a dissociation constant,
                  and is not carried into the effect; a KD whose curve was fitted
                  with the Stern-Volmer equation is not carried either (the fit
                  gives Ksv, so the number is not a KD).
effect_variance   variance of that constant, nM_squared, only when the
                  source's spread (kd_spread) allows it: standard_error -> se^2;
                  standard_deviation -> sd^2 / n, and only when the replicates
                  criterion is supported (n independent titrations);
                  confidence_interval -> not converted (needs its level and
                  degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).

Dependence keys handed to the merger (the same four keys as the other
converters): analyte_preparation_ref = the ligand (the titrant),
immobilized_preparation_ref = the protein held at a constant concentration,
surface_ref = None (a titration in solution has no surface), dataset_ref = the dataset.

Criteria mapping (Trp criteria -> sheet criteria), declared in CRITERIA_MAP
----------------------------------------------------------------------------
binding_controls              inner_filter + dilution + buffer_blank + ligand_fluorescence +
                              specificity_control + photobleaching + quenching_mechanism
binding_regime                saturation + concentration_series + protein_concentration + equilibrium
binding_parameter_definition  fit_model + excitation_selectivity
calibration_applicability     signal_amplitude (the size of the fluorescence change: this
                              method's counterpart of the SPR Rmax check)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in
'_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Continuous comparisons give a degree: supported with degree 1.0 up to
the full-agreement limit, falling linearly to 0 at the zero-agreement limit, conflicting at or beyond it (signal_amplitude against MIN_FLUORESCENCE_CHANGE_PERCENT /
FLUORESCENCE_CHANGE_ZERO_AGREEMENT_PERCENT; inner_filter's ligand absorbance, when no correction is stated, against MAX_UNCORRECTED_ABSORBANCE / ABSORBANCE_ZERO_AGREEMENT; dilution's
added volume, when no correction is stated, against MAX_UNCORRECTED_DILUTION_PERCENT / DILUTION_ZERO_AGREEMENT_PERCENT; protein_concentration against PROTEIN_MAX_OVER_KD /
PROTEIN_ZERO_AGREEMENT_OVER_KD unless tight binding is handled; concentration_series' lowest and highest concentration against LOW_FACTOR / LOW_ZERO_AGREEMENT_FACTOR and HIGH_FACTOR /
HIGH_ZERO_AGREEMENT_FACTOR, the weaker of the two, after a count of at least MIN_CONCENTRATIONS (a count below it is conflicting; a count without a span is unknown)). Counts, yes/no
facts and limits with no supported side carry no degree: excitation_selectivity is supported at a wavelength of at least TRP_SELECTIVE_EXCITATION_MIN_NM and unknown below it (the
tyrosine also excited is not a conflict); replicates conflicting below MIN_REPLICATES, else supported when the independence is yes, else unknown; equilibrium from an incubation
shorter than MIN_INCUBATION_MIN is conflicting, otherwise unknown (a long incubation alone does not show equilibrium). A sheet criterion that is supported carries the smallest
degree of its members that have one.
Quote support (literature_quote_support.py, SUPPORT_DEGREE direct 1.0 / implied 0.7 / about_something_else 0.3): when any stated field a member criterion reads has
support 'implied' or 'about_something_else', a supported sheet criterion gets the weakest support degree as its degree (the product with its degree where it had one);
support never changes a status, and a conflicting or unknown criterion keeps no degree.
Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet
criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported,
assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_criteria import NM_PER_UNIT

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_trp_converted_v1'
CRITERIA_MAP = {'binding_controls': ('inner_filter', 'dilution', 'buffer_blank', 'ligand_fluorescence', 'specificity_control', 'photobleaching', 'quenching_mechanism'), 'binding_regime': ('saturation', 'concentration_series', 'protein_concentration', 'equilibrium'), 'binding_parameter_definition': ('fit_model', 'excitation_selectivity'), 'calibration_applicability': ('signal_amplitude',), 'sampling_basis': ('replicates',)}
MIN_FLUORESCENCE_CHANGE_PERCENT = 5.0  # EXPERT_REVIEW: smallest change of the protein's fluorescence (percent) between the free protein and the saturated complex; the reading noise of a steady-state fluorimeter, pipetting and photobleaching together are a few percent, so a smaller change cannot be told from them; the full-agreement limit.
FLUORESCENCE_CHANGE_ZERO_AGREEMENT_PERCENT = 1.0  # EXPERT_REVIEW: change (percent) at or below which it is smaller than the reading noise of one measurement, conflicting.
TRP_SELECTIVE_EXCITATION_MIN_NM = 295.0  # EXPERT_REVIEW: smallest excitation wavelength (nm) that excites tryptophan almost alone; below it (280 nm) tyrosine is excited as well, so the change cannot be attributed to tryptophan (unknown, no degree).
MAX_UNCORRECTED_ABSORBANCE = 0.05  # EXPERT_REVIEW: largest ligand absorbance (AU, at the excitation or emission wavelength, at the highest ligand concentration) for which no inner-filter correction is needed; the inner-filter correction factor 10^((A_ex + A_em) / 2) is about 6 percent at an absorbance of 0.05 and 12 percent at 0.1, which is as large as the smallest usable signal; the full-agreement limit.
ABSORBANCE_ZERO_AGREEMENT = 0.3  # EXPERT_REVIEW: ligand absorbance (AU) at or above which an uncorrected measurement loses half of the light (10^0.3 is about 2), so the fluorescence change is mostly the inner filter, conflicting.
MAX_UNCORRECTED_DILUTION_PERCENT = 5.0  # EXPERT_REVIEW: largest total volume added (percent of the starting volume) for which the dilution of the protein may be left uncorrected; the dilution lowers the fluorescence by the same percentage, which at 5 percent is as large as the smallest usable signal; the full-agreement limit.
DILUTION_ZERO_AGREEMENT_PERCENT = 50.0  # EXPERT_REVIEW: added volume (percent) at or above which the protein is diluted by a third or more, an effect far larger than any usable signal, conflicting when not corrected.
MIN_CONCENTRATIONS = 8  # EXPERT_REVIEW: fewest ligand concentrations for a usable titration (a fluorescence titration is a series of additions; with fewer than eight the two baselines and the transition of a saturation curve are not all defined); a count, no degree.
LOW_FACTOR = 0.2  # EXPERT_REVIEW: the lowest ligand concentration must be at most this multiple of the KD (the free-protein baseline of the curve must be defined); the full-agreement limit.
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the KD at or above which the lowest concentration leaves the curve with no free-protein baseline at all (half the protein is already bound), conflicting.
HIGH_FACTOR = 10.0  # EXPERT_REVIEW: the highest ligand concentration must be at least this multiple of the KD, because the saturation plateau is only known by reaching it (about 90 percent saturation); the full-agreement limit.
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the KD at or below which the highest concentration reaches no more than half saturation, so the plateau is not seen at all, conflicting.
PROTEIN_MAX_OVER_KD = 1.0  # EXPERT_REVIEW: the protein may be at most this multiple of the KD for the 1:1 hyperbola to give the KD (above it the apparent KD is raised by depletion of the free ligand); the full-agreement limit.
PROTEIN_ZERO_AGREEMENT_OVER_KD = 10.0  # EXPERT_REVIEW: protein over KD at or above which the apparent KD is dominated by the protein concentration (an order of magnitude of depletion), conflicting unless tight binding is handled.
MIN_INCUBATION_MIN = 2.0  # EXPERT_REVIEW: an incubation after each addition shorter than this (minutes) is too short to call a complex at equilibrium without a time course (mixing and thermal equilibration of a cuvette alone take about a minute, and slower binders need longer); conflicting below it, unknown otherwise (no degree).
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent titrations (separate dilution series or preparations); a count, no degree.
NULL_REASONS = {'recovery': 'a_fluorescence_titration_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_specificity_control_is_not_an_attribution_fraction', 'total_signal': 'a_specificity_control_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_fluorescence_titration_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_fluorescence_titration_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _agreement(value, full, zero):
    """The degree of agreement of a measured value: 1.0 at or better than the full-agreement limit, falling linearly to 0 at the zero-agreement limit (either direction); None at or beyond it."""
    fraction = (value - zero) / (full - zero)
    return None if fraction <= 0 else min(1.0, fraction)


def _scaled(value, full, zero, refs):
    degree = _agreement(value, full, zero)
    return _verdict('conflicting', refs) if degree is None else _verdict('supported', refs, degree)


def _judge_signal(native):
    return _scaled(native['fluorescence_change_percent'], MIN_FLUORESCENCE_CHANGE_PERCENT, FLUORESCENCE_CHANGE_ZERO_AGREEMENT_PERCENT, native['change_refs'])


def _judge_excitation(native):
    return _verdict('supported' if native['excitation_nm'] >= TRP_SELECTIVE_EXCITATION_MIN_NM else 'unknown', native['excitation_refs'])      # a short excitation also excites tyrosine: not a conflict


def _judge_absorbance(native):
    return _scaled(native['ligand_absorbance'], MAX_UNCORRECTED_ABSORBANCE, ABSORBANCE_ZERO_AGREEMENT, native['absorbance_refs'])


def _judge_dilution(native):
    return _scaled(native['added_volume_percent'], MAX_UNCORRECTED_DILUTION_PERCENT, DILUTION_ZERO_AGREEMENT_PERCENT, native['added_volume_refs'])


def _judge_protein(native):
    if native['tight_binding_handled']:
        return _verdict('supported', native['protein_refs'])      # the quadratic or tight-binding analysis does not depend on the protein over the KD
    return _scaled(native['protein_over_kd'], PROTEIN_MAX_OVER_KD, PROTEIN_ZERO_AGREEMENT_OVER_KD, native['protein_refs'])


def _judge_series(native):
    if native['concentration_count'] < MIN_CONCENTRATIONS:
        return _verdict('conflicting', native['count_refs'])
    if native['concentration_low_over_constant'] is None:
        return _verdict('unknown', [])                               # the span can only be judged from the list and the KD
    refs = native['series_refs']
    low = _agreement(native['concentration_low_over_constant'], LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR)
    high = _agreement(native['concentration_high_over_constant'], HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR)
    if low is None or high is None:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(low, high))


def _judge_incubation(native):
    return _verdict('conflicting' if native['incubation_min'] < MIN_INCUBATION_MIN else 'unknown', native['incubation_refs'])


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('signal_amplitude', 'fluorescence_change_recorded_for_the_sheet'): _judge_signal, ('excitation_selectivity', 'excitation_recorded_for_the_sheet'): _judge_excitation,
          ('inner_filter', 'ligand_absorbance_recorded_for_the_sheet'): _judge_absorbance, ('dilution', 'added_volume_recorded_for_the_sheet'): _judge_dilution,
          ('protein_concentration', 'protein_over_kd_recorded_for_the_sheet'): _judge_protein, ('concentration_series', 'series_recorded_for_the_sheet'): _judge_series,
          ('equilibrium', 'incubation_recorded_for_the_sheet'): _judge_incubation, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}


def _binding_constant(native):
    """'kd' when the record carries a KD whose curve was not fitted with the Stern-Volmer equation, else None."""
    return 'kd' if native['kd_nM'] is not None and native['fit_model'] != 'stern_volmer' else None


def _variance(graded, constant_name):
    """Return (variance_nM_squared or None, reason or None, refs)."""
    native = graded['native']
    if constant_name is None:
        return None, 'no_effect_to_carry_a_variance', []
    spread = native['quantities']['kd_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, 'kd_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = spread['value'] * NM_PER_UNIT[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_titrations_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_trp(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    constant_name = _binding_constant(native)
    if constant_name is None:
        if native['kd_nM'] is not None:
            null_components['effect'] = 'the_kd_was_fitted_with_the_stern_volmer_equation_which_gives_a_quenching_constant'
        elif native['quantities']['ksv']['status'] == 'point':
            null_components['effect'] = 'only_a_stern_volmer_quenching_constant_given_not_a_dissociation_constant'
        else:
            null_components['effect'] = 'no_kd_given_as_a_point_value'
    else:
        constant = native['quantities'][constant_name]
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'trp_kd:' + ref, constant['source_refs'], constant['origin'], constant_name)
    variance, variance_reason, variance_refs = _variance(graded, constant_name)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'trp_variance:' + ref, variance_refs, 'derived', 'kd_spread')
    null_components.update(NULL_REASONS)
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
    if variance is not None:
        interpretations['variance_correspondence'] = {'status': 'supported', 'support_refs': variance_refs}
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['titrant_preparation_ref'], 'immobilized_preparation_ref': preparations['fixed_partner_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    return {'version': VERSION, 'experiment_type': 'trp_quenching', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': native['quantities'][constant_name]['support'] if constant_name is not None else None}
