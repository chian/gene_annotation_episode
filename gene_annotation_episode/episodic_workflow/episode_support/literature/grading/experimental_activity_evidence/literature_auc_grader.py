"""AUC grader: judges ONE analytical ultracentrifugation (AUC: sedimentation velocity and sedimentation equilibrium) experiment (a protein, or a mixture of two proteins, is spun in an analytical ultracentrifuge; in velocity runs a complex sediments faster than either component alone and the fit gives its molar mass; in equilibrium runs a global fit of several concentrations and speeds gives the mass, the stoichiometry and, for a reversible association, the KD; mostly qualitative or semi-quantitative, occasionally a KD from a concentration series) by its own standards.

Hand-built and private to this method (it shares no grading logic with the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC or dialysis graders).
Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_auc_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_auc_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration, each reading its thresholds
by name from that file.

A criterion returns 'supported' or 'conflicting' only with support refs (the quoted spans of the stated fields it rests on);
``_result`` refuses to build one without them. Where only a fact with no span would decide, the criterion returns 'unknown' (or
'not_applicable' when no KD is reported and the criterion needs one) with a declared reason.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown;
else all 'not_applicable' -> not_applicable; else supported. The other criteria have their own rules (declared).

An AUC has two outcomes. With a concentration series it reports a KD (native 'kd_nM'); without one it reports only the complex species, its s, its mass and its
stoichiometry. The native values carry the qualitative statement of the record, 'interaction' ('detected' when a complex is stated, 'not_detected' when it is
stated not to be, else None), with the spans that state it ('interaction_refs'); the converter hands it to the merger as the experiment's qualitative
effect when the record has no KD.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs (shift_percent/shift_refs, the mass fields,
stoichiometry_ratio/stoichiometry_refs, concentration_count/concentration_count_refs, low_over_kd/high_over_kd/range_refs, fit_rmsd/fit_rmsd_unit/fit_refs,
replicate_count/replicate_independent/replicate_refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the AUC converter judges it.

Support: native 'support' holds, for each criterion, the supports ('direct', 'implied', 'about_something_else') of the stated fields it reads
(its declared 'reads'), copied from the record and not judged here; the converter judges them.

Native values retained: every record quantity as given, plus kd_nM, lowest_nM, highest_nM, shift_percent (signed), mass_measured, mass_theoretical, mass_deviation_percent (signed; facts only, the grader judges no mass threshold; None when the two masses are not both stated),
mass_support_refs, component_mass_larger and component_mass_smaller (kDa, recorded with the shift when both are stated), mass_smaller_component (kDa, recorded with the mass deviation when stated; the same operand as component_mass_smaller), concentration_count (1 for a stated 'no series' when no count is stated), low_over_kd, high_over_kd, interaction, interaction_refs, preparations, run_mode, analysis_model, detection and spread_kind.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_auc_criteria import (
    AUC_CRITERIA, NM_PER_UNIT, PERCENT_PER_FRACTION)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_auc_grade'
CRITERIA = tuple(criterion['id'] for criterion in AUC_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact complex_detected
NO_KD = 'no_apparent_kd_reported'
VELOCITY = 'sedimentation_velocity'


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _scaled(record, name, scale):
    value = _value(record, name)
    return None if value is None else value * scale[record['quantities'][name]['unit']]


def _refs(*items):
    refs = []
    for item in items:
        refs += item['source_refs']
    return list(dict.fromkeys(refs))


def _shared_rule(answers):
    if 'no' in answers:
        return 'conflicting', 'fact_answered_no'
    if 'unknown' in answers:
        return 'unknown', 'fact_unknown'
    if all(a == 'not_applicable' for a in answers):
        return 'not_applicable', 'fact_not_applicable'
    return 'supported', 'facts_answered_yes'


def _result(status, reason, refs):
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError('a ' + status + ' criterion needs support refs: ' + reason)
    return {'status': status, 'reason': reason, 'support_refs': refs if status in ('supported', 'conflicting') else []}


def _one_fact(record, name):
    item = record['facts'][name]
    status, reason = _shared_rule([item['answer']])
    return _result(status, reason, item['source_refs'])


def _equilibrium_fact(record, name):
    """The fact decides; an unknown fact is not applicable for a run stated as sedimentation velocity (it has no equilibrium)."""
    item = record['facts'][name]
    status, reason = _shared_rule([item['answer']])
    if status == 'unknown' and record['run_mode'] == VELOCITY:
        return _result('not_applicable', 'velocity_run_has_no_equilibrium_criterion', [])
    return _result(status, reason, item['source_refs'])


def _complex_observed(record, native):
    return _one_fact(record, 'complex_detected')


def _sedimentation_shift(record, native):
    complex_s, larger = _value(record, 'complex_sedimentation_coefficient'), _value(record, 'component_sedimentation_coefficient_larger')
    if complex_s is None or larger is None:
        return _result('unknown', 'sedimentation_shift_not_given', [])
    refs = _refs(record['quantities']['complex_sedimentation_coefficient'], record['quantities']['component_sedimentation_coefficient_larger'])
    mass_larger, mass_smaller = _value(record, 'component_mass_larger'), _value(record, 'component_mass_smaller')
    if mass_larger is not None and mass_smaller is not None:      # the partner size, which says how much faster the complex should sediment: recorded, judged on the sheet side
        native.update({'component_mass_larger': mass_larger, 'component_mass_smaller': mass_smaller})
        refs = _refs({'source_refs': refs}, record['quantities']['component_mass_larger'], record['quantities']['component_mass_smaller'])
    native.update({'shift_percent': (complex_s - larger) / larger * PERCENT_PER_FRACTION, 'shift_refs': refs})
    return _result('unknown', 'sedimentation_shift_recorded_for_the_sheet', [])


def _components_alone(record, native):
    return _one_fact(record, 'components_run_alone')


def _component_homogeneity(record, native):
    return _one_fact(record, 'components_monodisperse')


def _mass(record, native):
    measured, theoretical = _value(record, 'complex_mass_measured'), _value(record, 'complex_mass_theoretical')
    if measured is None or theoretical is None:
        return _one_fact(record, 'mass_matches_complex')
    refs = _refs(record['quantities']['complex_mass_measured'], record['quantities']['complex_mass_theoretical'])
    smaller = _value(record, 'component_mass_smaller')
    if smaller is not None:      # the size of one partner more or less, which says how far a wrong stoichiometry moves the mass: recorded, judged on the sheet side
        native['mass_smaller_component'] = smaller
        refs = _refs({'source_refs': refs}, record['quantities']['component_mass_smaller'])
    native.update({'mass_measured': measured, 'mass_theoretical': theoretical, 'mass_deviation_percent': (measured - theoretical) / theoretical * PERCENT_PER_FRACTION,
                   'mass_support_refs': refs})
    return _result('unknown', 'mass_deviation_recorded_for_the_sheet', [])


def _stoichiometry(record, native):
    if native['kd_nM'] is None:
        return _result('not_applicable', NO_KD, [])
    ratio = _value(record, 'stoichiometry_ratio')
    if ratio is None:
        return _result('unknown', 'stoichiometry_not_given', [])
    native.update({'stoichiometry_ratio': ratio, 'stoichiometry_refs': _refs(record['quantities']['stoichiometry_ratio'])})
    return _result('unknown', 'stoichiometry_recorded_for_the_sheet', [])


def _concentration_series(record, native):
    item = record['facts']['concentration_series_measured']
    count = _value(record, 'concentration_count')
    if count is None and item['answer'] == 'no':      # a stated 'no series' is a series of one: a count the sheet judges (low partial credit), not a fact against the experiment
        native.update({'concentration_count': 1, 'concentration_count_refs': list(item['source_refs'])})
        return _result('unknown', 'concentration_count_recorded_for_the_sheet', [])
    if count is None:
        return _one_fact(record, 'concentration_series_measured')
    native.update({'concentration_count': count, 'concentration_count_refs': _refs(record['quantities']['concentration_count'])})
    return _result('unknown', 'concentration_count_recorded_for_the_sheet', [])


def _concentration_range(record, native):
    if native['kd_nM'] is None:
        return _result('not_applicable', NO_KD, [])
    lowest, highest = native['lowest_nM'], native['highest_nM']
    if lowest is None or highest is None:
        return _result('unknown', 'concentration_range_not_given', [])
    native.update({'low_over_kd': lowest / native['kd_nM'], 'high_over_kd': highest / native['kd_nM'],
                   'range_refs': _refs(record['quantities']['loaded_concentration_lowest'], record['quantities']['loaded_concentration_highest'], record['quantities']['kd'])})
    return _result('unknown', 'concentration_range_recorded_for_the_sheet', [])


def _reversibility(record, native):
    return _one_fact(record, 'reversible_association_shown')


def _equilibrium_reached(record, native):
    return _equilibrium_fact(record, 'equilibrium_reached_shown')


def _multiple_speeds(record, native):
    return _equilibrium_fact(record, 'multiple_speeds_used')


def _fit_quality(record, native):
    item = record['facts']['fit_residuals_random']
    if item['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', item['source_refs'])
    rmsd = record['quantities']['fit_rmsd']
    if rmsd['status'] != 'point':
        return _one_fact(record, 'fit_residuals_random')
    native.update({'fit_rmsd': rmsd['value'], 'fit_rmsd_unit': rmsd['unit'], 'fit_refs': _refs(rmsd)})
    return _result('unknown', 'fit_rmsd_recorded_for_the_sheet', [])


def _buffer_correction(record, native):
    return _one_fact(record, 'buffer_density_viscosity_corrected')


def _non_binding_control(record, native):
    return _one_fact(record, 'non_binding_control_done')


def _replicates(record, native):
    count = _value(record, 'replicate_count')
    independent = record['facts']['independent_experiments']
    refs = _refs(record['quantities']['replicate_count'], independent)
    if independent['answer'] == 'no':
        return _result('conflicting', 'replicates_not_independent', refs)
    if count is None:
        return _result('unknown', 'replicate_count_or_independence_unknown', [])
    native.update({'replicate_count': count, 'replicate_independent': independent['answer'], 'replicate_refs': refs})
    return _result('unknown', 'replicate_count_recorded_for_the_sheet', [])


EVALUATORS = {'complex_observed': _complex_observed, 'sedimentation_shift': _sedimentation_shift, 'components_alone': _components_alone, 'component_homogeneity': _component_homogeneity, 'mass': _mass, 'stoichiometry': _stoichiometry, 'concentration_series': _concentration_series, 'concentration_range': _concentration_range, 'reversibility': _reversibility, 'equilibrium_reached': _equilibrium_reached, 'multiple_speeds': _multiple_speeds, 'fit_quality': _fit_quality, 'buffer_correction': _buffer_correction, 'non_binding_control': _non_binding_control, 'replicates': _replicates}


def grade_auc(record):
    """Grade one AUC experiment record. Returns the criterion answers and native values."""
    complex_found = record['facts']['complex_detected']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'run_mode': record['run_mode'], 'analysis_model': record['analysis_model'], 'detection': record['detection'], 'spread_kind': record['spread_kind'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'interaction': INTERACTION.get(complex_found['answer']), 'interaction_refs': list(complex_found['source_refs']) if complex_found['answer'] in INTERACTION else [], 'kd_nM': _scaled(record, 'kd', NM_PER_UNIT), 'lowest_nM': _scaled(record, 'loaded_concentration_lowest', NM_PER_UNIT), 'highest_nM': _scaled(record, 'loaded_concentration_highest', NM_PER_UNIT), 'shift_percent': None, 'shift_refs': [], 'stoichiometry_ratio': None, 'stoichiometry_refs': [], 'concentration_count': None, 'concentration_count_refs': [], 'low_over_kd': None, 'high_over_kd': None, 'range_refs': [], 'fit_rmsd': None, 'fit_rmsd_unit': None, 'fit_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': [], 'mass_measured': None, 'mass_theoretical': None, 'mass_deviation_percent': None, 'mass_support_refs': [], 'component_mass_larger': None, 'component_mass_smaller': None, 'mass_smaller_component': None}
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    native['support'] = criterion_supports(record, AUC_CRITERIA)      # kept for the sheet: the grader does not judge it
    return {'version': VERSION, 'experiment_type': 'auc', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
