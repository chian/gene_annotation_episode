"""DSF grader: judges ONE thermal shift (differential scanning fluorimetry, DSF, and nanoDSF) experiment (a protein is heated while its unfolding is followed with a dye such as SYPRO Orange or by its intrinsic fluorescence; the melting temperature Tm is read alone and with a ligand; the ligand-induced shift delta Tm shows binding only indirectly; mostly qualitative, occasionally an apparent KD from a series of ligand concentrations) by its own standards.

Hand-built and private to this method (it shares no grading logic with the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis or AUC graders).
Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_dsf_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_dsf_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration, each reading its thresholds
by name from that file.

A criterion returns 'supported' or 'conflicting' only with support refs (the quoted spans of the stated fields it rests on);
``_result`` refuses to build one without them. Where only a fact with no span would decide, the criterion returns 'unknown' (or
'not_applicable' when no KD is reported and the criterion needs one) with a declared reason.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown;
else all 'not_applicable' -> not_applicable; else supported. The other criteria have their own rules (declared).

A thermal shift has two outcomes. With a series of ligand concentrations it can report an apparent KD (native 'kd_nM'); without one it reports only the shift of the Tm. The native values carry the
qualitative statement of the record, 'interaction' ('detected' when the ligand is stated to raise the Tm, 'not_detected' when the Tm is stated not to change, else None), with the spans that state it ('interaction_refs'); the converter hands it to the merger as the
experiment's qualitative effect when the record has no KD.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs (thermal_shift_c/thermal_shift_refs, shift_over_spread/shift_spread_refs,
concentration_count/concentration_count_refs, low_over_kd/high_over_kd/range_refs, heating_rate_c_per_min/heating_rate_refs, replicate_count/replicate_independent/replicate_refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet'; the DSF converter judges it.

Support: native 'support' holds, for each criterion, the supports ('direct', 'implied', 'about_something_else') of the stated fields it reads
(its declared 'reads'), copied from the record and not judged here; the converter judges them.

Native values retained: every record quantity as given, plus kd_nM, lowest_nM, highest_nM, protein_nM, shift_ligand_nM, shift_concentration_over_kd, shift_concentration_refs, tm_spread_c, tm_spread_independent, kd_over_protein, thermal_shift_c (signed; the stated shift, else the Tm with the ligand minus the Tm without, None when neither is known), thermal_shift_refs, shift_over_spread (signed),
shift_spread_refs, low_over_kd, high_over_kd, interaction, interaction_refs, preparations, readout, tm_method and spread_kind.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dsf_criteria import (
    DSF_CRITERIA, NM_PER_UNIT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_dsf_grade'
CRITERIA = tuple(criterion['id'] for criterion in DSF_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact thermal_shift_observed
NO_KD = 'no_apparent_kd_reported'


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


def _shift(record):
    """(signed shift in degrees Celsius, refs) from the stated shift, else from the two stated Tm values; (None, []) when neither is stated."""
    stated = _value(record, 'delta_tm')
    if stated is not None:
        return stated, _refs(record['quantities']['delta_tm'])
    apo, ligand = _value(record, 'tm_apo'), _value(record, 'tm_ligand')
    if apo is None or ligand is None:
        return None, []
    return ligand - apo, _refs(record['quantities']['tm_apo'], record['quantities']['tm_ligand'])


def _shift_observed(record, native):
    return _one_fact(record, 'thermal_shift_observed')


def _shift_size(record, native):
    shift, refs = _shift(record)
    if shift is None:
        return _result('unknown', 'thermal_shift_not_given', [])
    native.update({'thermal_shift_c': shift, 'thermal_shift_refs': refs})
    at, kd = native['shift_ligand_nM'], native['kd_nM']
    if at is not None and kd is not None:
        native.update({'shift_concentration_over_kd': at / kd, 'shift_concentration_refs': _refs(record['quantities']['shift_ligand_concentration'], record['quantities']['kd'])})
    return _result('unknown', 'thermal_shift_recorded_for_the_sheet', [])


def _shift_over_spread(record, native):
    shift, refs = _shift(record)
    spread = _value(record, 'tm_spread')
    if shift is None or spread is None:
        return _result('unknown', 'shift_over_spread_not_given', [])
    basis = record['facts']['tm_spread_over_independent_experiments']
    native.update({'shift_over_spread': shift / spread, 'tm_spread_c': spread, 'tm_spread_independent': basis['answer'],
                   'shift_spread_refs': _refs({'source_refs': refs}, record['quantities']['tm_spread'], *([basis] if basis['answer'] != 'unknown' else []))})
    return _result('unknown', 'shift_over_spread_recorded_for_the_sheet', [])


def _protein_alone_control(record, native):
    return _one_fact(record, 'protein_alone_control_done')


def _ligand_alone_control(record, native):
    return _one_fact(record, 'ligand_alone_control_done')


def _curve_quality(record, native):
    return _one_fact(record, 'melt_curve_sigmoidal')


def _dose_dependence(record, native):
    return _one_fact(record, 'shift_dose_dependent')


def _concentration_series(record, native):
    item = record['facts']['ligand_titration_measured']
    count = _value(record, 'ligand_concentration_count')
    if item['answer'] == 'no':      # a single-concentration screen: recorded as one concentration (or the stated count), judged on the sheet side
        native.update({'concentration_count': 1 if count is None else count, 'concentration_count_refs': _refs(item)})
        return _result('unknown', 'single_concentration_recorded_for_the_sheet', [])
    if count is None:
        return _one_fact(record, 'ligand_titration_measured')
    native.update({'concentration_count': count, 'concentration_count_refs': _refs(record['quantities']['ligand_concentration_count'])})
    return _result('unknown', 'concentration_count_recorded_for_the_sheet', [])


def _concentration_range(record, native):
    if native['kd_nM'] is None:
        return _result('not_applicable', NO_KD, [])
    lowest, highest = native['lowest_nM'], native['highest_nM']
    if lowest is None or highest is None:
        return _result('unknown', 'concentration_range_not_given', [])
    native.update({'low_over_kd': lowest / native['kd_nM'], 'high_over_kd': highest / native['kd_nM'],
                   'range_refs': _refs(record['quantities']['ligand_concentration_lowest'], record['quantities']['ligand_concentration_highest'], record['quantities']['kd'])})
    protein = native['protein_nM']
    if protein is not None:
        native.update({'kd_over_protein': native['kd_nM'] / protein, 'range_refs': _refs({'source_refs': native['range_refs']}, record['quantities']['protein_concentration'])})
    return _result('unknown', 'concentration_range_recorded_for_the_sheet', [])


def _heating_rate(record, native):
    rate = _value(record, 'heating_rate')
    if rate is None:
        return _result('unknown', 'heating_rate_not_given', [])
    native.update({'heating_rate_c_per_min': rate, 'heating_rate_refs': _refs(record['quantities']['heating_rate'])})
    return _result('unknown', 'heating_rate_recorded_for_the_sheet', [])


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


EVALUATORS = {'shift_observed': _shift_observed, 'shift_size': _shift_size, 'shift_over_spread': _shift_over_spread, 'protein_alone_control': _protein_alone_control, 'ligand_alone_control': _ligand_alone_control, 'curve_quality': _curve_quality, 'dose_dependence': _dose_dependence, 'concentration_series': _concentration_series, 'concentration_range': _concentration_range, 'heating_rate': _heating_rate, 'replicates': _replicates}


def grade_dsf(record):
    """Grade one DSF experiment record. Returns the criterion answers and native values."""
    shifted = record['facts']['thermal_shift_observed']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'readout': record['readout'], 'tm_method': record['tm_method'], 'spread_kind': record['spread_kind'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'interaction': INTERACTION.get(shifted['answer']), 'interaction_refs': list(shifted['source_refs']) if shifted['answer'] in INTERACTION else [], 'kd_nM': _scaled(record, 'kd', NM_PER_UNIT), 'lowest_nM': _scaled(record, 'ligand_concentration_lowest', NM_PER_UNIT), 'highest_nM': _scaled(record, 'ligand_concentration_highest', NM_PER_UNIT), 'protein_nM': _scaled(record, 'protein_concentration', NM_PER_UNIT), 'shift_ligand_nM': _scaled(record, 'shift_ligand_concentration', NM_PER_UNIT), 'shift_concentration_over_kd': None, 'shift_concentration_refs': [], 'tm_spread_c': None, 'tm_spread_independent': None, 'kd_over_protein': None, 'thermal_shift_c': None, 'thermal_shift_refs': [], 'shift_over_spread': None, 'shift_spread_refs': [], 'concentration_count': None, 'concentration_count_refs': [], 'low_over_kd': None, 'high_over_kd': None, 'range_refs': [], 'heating_rate_c_per_min': None, 'heating_rate_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    native['support'] = criterion_supports(record, DSF_CRITERIA)      # kept for the sheet: the grader does not judge it
    return {'version': VERSION, 'experiment_type': 'dsf', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
