"""SPR grader: judges ONE surface plasmon resonance experiment by SPR's own standards.

Hand-built and private to SPR. Deterministic; no model call, no store access.
Input: the record of one SPR experiment (forms/.../literature_spr_record.py).
Output: for each SPR criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_spr_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration, each reading its thresholds
by name from that file.

The grader holds NO threshold that judges goodness. Where a number would be
compared with a limit it records the number with its refs (concentration_count
and the two ratios over the KD, chi2_over_rmax, rmax_ratio, replicate_count,
kd_from_rates_nM, steady_kinetic_fold, each with its refs) and returns
'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs; the
SPR converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable):
any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. Criteria made of several
facts use this rule over their facts.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out
per criterion (native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

Native values retained: every record quantity as given, plus kd_nM,
kd_from_rates_nM, rmax_theoretical, rmax_ratio, chi2_over_rmax, chi2_over_noise_squared, kd_analysis,
concentration_low_over_kd, concentration_high_over_kd, concentration_count,
steady_kinetic_fold, replicate_count, replicate_independent, fit_bivalent_answer
and the refs of each (concentration_refs, fit_refs, rmax_refs, replicate_refs,
kinetic_refs, steady_kinetic_refs), preparations, spread_kind and fit_model.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_criteria import NM_PER_M, SPR_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_spr_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in SPR_CRITERIA)


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _nm(record, name):
    value = _value(record, name)
    return None if value is None else value * _SCALES[record['quantities'][name]['unit']]


def _refs(*items):
    refs = []
    for item in items:
        refs += item['source_refs']
    return list(dict.fromkeys(refs))


def _answers(record, names):
    return [record['facts'][name]['answer'] for name in names]


def _shared_rule(answers):
    if 'no' in answers:
        return 'conflicting', 'fact_answered_no'
    if 'unknown' in answers:
        return 'unknown', 'fact_unknown'
    if all(a == 'not_applicable' for a in answers):
        return 'not_applicable', 'fact_not_applicable'
    return 'supported', 'facts_answered_yes'


def _result(status, reason, refs):
    return {'status': status, 'reason': reason, 'support_refs': refs if status in ('supported', 'conflicting') else []}


def _reference_subtraction(record, native):
    names = ('reference_surface', 'double_referencing')
    answers = _answers(record, names)
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', 'reference_subtraction_stated', refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _concentration_series(record, native):
    kd = native['kd_nM']
    series = record['concentration_series']
    values = series['value']
    if kd is None or values is None:
        return _result('unknown', 'kd_or_series_missing', [])
    scale = _SCALES[series['unit']]
    nm = [v * scale for v in values]
    native['concentration_count'] = len(nm)
    native['concentration_low_over_kd'] = min(nm) / kd
    native['concentration_high_over_kd'] = max(nm) / kd
    how = record['facts']['kd_analysis']
    native['kd_analysis'] = how['answer']
    native['concentration_refs'] = _refs(series, record['quantities']['kd'], how)
    return _result('unknown', 'concentration_series_recorded_for_the_sheet', [])


def _fit_model(record, native):
    model = record['fit_model']
    bivalent = record['facts']['analyte_bivalent_or_oligomeric']
    residuals = record['facts']['residuals_reported']
    chi2 = _value(record, 'chi_squared')
    rmax = _value(record, 'rmax')
    noise = _value(record, 'baseline_noise')
    refs = _refs(bivalent, residuals, record['quantities']['chi_squared'], record['quantities']['rmax'], record['quantities']['baseline_noise'])
    if chi2 is not None and rmax is not None:
        native['chi2_over_rmax'] = chi2 / rmax
    if chi2 is not None and noise is not None:
        native['chi2_over_noise_squared'] = chi2 / (noise * noise)
    if model is None:
        return _result('unknown', 'fit_model_not_stated', [])
    if model == '1:1_langmuir' and bivalent['answer'] == 'yes':
        return _result('conflicting', 'one_to_one_model_for_bivalent_or_oligomeric_analyte', refs)
    if native['chi2_over_rmax'] is not None or native['chi2_over_noise_squared'] is not None:
        native.update({'fit_bivalent_answer': bivalent['answer'], 'fit_refs': refs})
        return _result('unknown', 'chi_squared_recorded_for_the_sheet', [])
    if residuals['answer'] != 'yes':
        return _result('unknown', 'no_residual_evidence', [])
    if model == '1:1_langmuir' and bivalent['answer'] != 'no':
        return _result('unknown', 'bivalence_or_oligomer_state_unknown_for_one_to_one_model', [])
    return _result('supported', 'model_stated_with_residual_evidence', refs)


def _rmax_consistency(record, native):
    names = ('rmax', 'immobilization_level', 'analyte_mass', 'ligand_mass', 'stoichiometry')
    values = [_value(record, n) for n in names]
    if any(v is None for v in values):
        return _result('unknown', 'rmax_operand_missing', [])
    rmax, level, analyte, ligand, stoichiometry = values
    theoretical = analyte / ligand * level * stoichiometry
    native['rmax_theoretical'] = theoretical
    native['rmax_ratio'] = rmax / theoretical
    native['rmax_refs'] = _refs(*(record['quantities'][n] for n in names))
    return _result('unknown', 'rmax_ratio_recorded_for_the_sheet', [])


def _mass_transport(record, native):
    item = record['facts']['mass_transport']
    status = {'checked_not_limited': 'supported', 'checked_limited': 'conflicting'}.get(item['answer'], 'unknown')
    return _result(status, 'mass_transport_' + item['answer'], item['source_refs'])


def _baseline_regeneration(record, native):
    names = ('baseline_drift', 'regeneration')
    status, reason = _shared_rule(_answers(record, names))
    return _result(status, reason, _refs(*(record['facts'][n] for n in names)))


def _replicates(record, native):
    count = _value(record, 'replicate_count')
    independent = record['facts']['independent_surfaces']
    refs = _refs(record['quantities']['replicate_count'], independent)
    if independent['answer'] == 'no':
        return _result('conflicting', 'replicates_not_independent', refs)
    if count is None:
        return _result('unknown', 'replicate_count_or_independence_unknown', [])
    native.update({'replicate_count': count, 'replicate_independent': independent['answer'], 'replicate_refs': refs})
    return _result('unknown', 'replicate_count_recorded_for_the_sheet', [])


def _immobilized_activity(record, native):
    item = record['facts']['immobilized_activity']
    status, reason = _shared_rule([item['answer']])
    return _result(status, reason, item['source_refs'])


def _kinetic_consistency(record, native):
    kd, kon, koff = native['kd_nM'], _value(record, 'kon'), _value(record, 'koff')
    if kd is None or kon is None or koff is None:
        return _result('unknown', 'kd_kon_or_koff_missing', [])
    native['kd_from_rates_nM'] = koff / kon * NM_PER_M
    native['kinetic_refs'] = _refs(*(record['quantities'][n] for n in ('kd', 'kon', 'koff')))
    return _result('unknown', 'kd_from_rates_recorded_for_the_sheet', [])


def _steady_state_vs_kinetic(record, native):
    steady, kd = _nm(record, 'kd_steady_state'), native['kd_nM']
    if steady is None or kd is None:
        if record['facts']['single_estimate_method']['answer'] == 'yes':
            return _result('not_applicable', 'single_estimate_method', record['facts']['single_estimate_method']['source_refs'])
        return _result('unknown', 'steady_state_or_kinetic_kd_missing', [])
    native['steady_kinetic_fold'] = max(steady, kd) / min(steady, kd)
    native['steady_kinetic_refs'] = _refs(record['quantities']['kd_steady_state'], record['quantities']['kd'])
    return _result('unknown', 'estimate_fold_recorded_for_the_sheet', [])


EVALUATORS = {'reference_subtraction': _reference_subtraction, 'concentration_series': _concentration_series, 'fit_model': _fit_model, 'rmax_consistency': _rmax_consistency, 'mass_transport': _mass_transport, 'baseline_regeneration': _baseline_regeneration, 'replicates': _replicates, 'immobilized_activity': _immobilized_activity, 'kinetic_consistency': _kinetic_consistency, 'steady_state_vs_kinetic': _steady_state_vs_kinetic}


def grade_spr(record):
    """Grade one SPR experiment record. Returns the criterion answers and native values."""
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'], 'fit_model': record['fit_model'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'kd_nM': _nm(record, 'kd'), 'kd_from_rates_nM': None, 'rmax_theoretical': None, 'rmax_ratio': None, 'chi2_over_rmax': None, 'chi2_over_noise_squared': None, 'kd_analysis': None, 'concentration_count': None, 'concentration_low_over_kd': None, 'concentration_high_over_kd': None, 'concentration_refs': [], 'fit_bivalent_answer': None, 'fit_refs': [], 'rmax_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': [], 'kinetic_refs': [], 'steady_kinetic_fold': None, 'steady_kinetic_refs': []}
    native['support'] = criterion_supports(record, SPR_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'spr', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
