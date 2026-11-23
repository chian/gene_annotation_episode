"""SEC grader: judges ONE size-exclusion chromatography (SEC, gel filtration; with or without multi-angle light scattering, SEC-MALS) complex experiment (two proteins are mixed and run on a size-exclusion column; the complex elutes earlier than either component alone, in a co-elution peak that shows both partners on SDS-PAGE; SEC-MALS gives the molar mass of the complex; mostly qualitative or semi-quantitative, occasionally an apparent KD from peak areas) by its own standards.

Hand-built and private to this method (it shares no grading logic with the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down or EMSA graders).
Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_sec_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_sec_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration, each reading its thresholds
by name from that file.

A criterion returns 'supported' or 'conflicting' only with support refs (the quoted spans of the stated fields it rests on);
``_result`` refuses to build one without them. Where only a fact with no span would decide, the criterion returns 'unknown' (or
'not_applicable' when no apparent KD is reported and the criterion needs one) with a declared reason.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown;
else all 'not_applicable' -> not_applicable; else supported. elution_shift, mals_mass, stoichiometry, resin_interaction, complex_stable_on_column,
monodispersity and replicates have their own rules (declared).

An SEC has two outcomes. With a titration it reports an apparent KD (native 'kd_nM'); without one it reports only the complex peak, its shift and its
mass. The native values carry the qualitative statement of the record, 'interaction' ('detected' when a complex peak is stated, 'not_detected' when it is
stated not to be, else None), with the spans that state it ('interaction_refs'); the converter hands it to the merger as the experiment's qualitative
effect when the record has no apparent KD.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs (shift_ml/shift_refs,
stoichiometry_ratio/stoichiometry_refs, salt_mM/salt_refs, load_over_kd/load_refs, polydispersity/polydispersity_refs, replicate_count/replicate_independent/replicate_refs,
the mass fields) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the SEC converter judges it.

Support: native 'support' holds, for each criterion, the supports ('direct', 'implied', 'about_something_else') of the stated fields it reads
(its declared 'reads'), copied from the record and not judged here; the converter judges them.

Native values retained: every record quantity as given, plus kd_nM, loaded_nM, loaded_mL (the injected volume), column_mL (the stated column volume) with loaded_refs and column_refs (recorded for the sheet beside the shift and the load), salt_mM, shift_ml, mass_measured, mass_theoretical, mass_deviation_percent (signed; facts only, the grader judges no mass threshold; None when the two masses are not both stated), mass_support_refs, load_over_kd, interaction,
interaction_refs, preparations, column_type, detection and spread_kind.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_criteria import (
    ML_PER_VOLUME_UNIT, MM_PER_SALT_UNIT, NM_PER_UNIT, PERCENT_PER_FRACTION, SEC_CRITERIA)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_sec_grade'
CRITERIA = tuple(criterion['id'] for criterion in SEC_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact complex_peak_detected
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


def _fact_unless_no_kd(record, native, name):
    """The fact decides; an unknown fact is not applicable when no apparent KD is reported (there is no constant for the criterion to bias)."""
    item = record['facts'][name]
    status, reason = _shared_rule([item['answer']])
    if status == 'unknown' and native['kd_nM'] is None:
        return _result('not_applicable', NO_KD, [])
    return _result(status, reason, item['source_refs'])


def _column(record, native):
    """Record the stated column volume (mL) with its refs: the scale of the peak width, read by the sheet beside the shift and the dilution on the column."""
    operand = record['quantities']['column_volume']
    if operand['status'] == 'point':
        native.update({'column_mL': operand['value'], 'column_refs': _refs(operand)})


def _complex_peak_observed(record, native):
    return _one_fact(record, 'complex_peak_detected')


def _elution_shift(record, native):
    shift = _value(record, 'elution_volume_shift')
    if shift is not None:
        refs = _refs(record['quantities']['elution_volume_shift'])
    else:
        earlier, complex_volume = _value(record, 'component_elution_volume_earlier'), _value(record, 'complex_elution_volume')
        if earlier is None or complex_volume is None:
            return _result('unknown', 'elution_shift_not_given', [])
        shift = earlier - complex_volume
        refs = _refs(record['quantities']['component_elution_volume_earlier'], record['quantities']['complex_elution_volume'])
    native.update({'shift_ml': shift, 'shift_refs': refs})
    _column(record, native)
    return _result('unknown', 'elution_shift_recorded_for_the_sheet', [])


def _components_alone(record, native):
    return _one_fact(record, 'components_run_alone')


def _complex_composition(record, native):
    return _one_fact(record, 'complex_peak_analysed_by_sds_page')


def _titration_depletion(record, native):
    return _one_fact(record, 'free_peak_decreases_with_titration')


def _mals_mass(record, native):
    measured, theoretical = _value(record, 'complex_mass_measured'), _value(record, 'complex_mass_theoretical')
    if measured is None or theoretical is None:
        return _one_fact(record, 'mals_mass_matches_complex')
    native.update({'mass_measured': measured, 'mass_theoretical': theoretical, 'mass_deviation_percent': (measured - theoretical) / theoretical * PERCENT_PER_FRACTION,
                   'mass_support_refs': _refs(record['quantities']['complex_mass_measured'], record['quantities']['complex_mass_theoretical'])})
    return _result('unknown', 'mass_deviation_recorded_for_the_sheet', [])


def _stoichiometry(record, native):
    if native['kd_nM'] is None:
        return _result('not_applicable', NO_KD, [])
    ratio = _value(record, 'stoichiometry_ratio')
    if ratio is None:
        return _result('unknown', 'stoichiometry_not_given', [])
    native.update({'stoichiometry_ratio': ratio, 'stoichiometry_refs': _refs(record['quantities']['stoichiometry_ratio'])})
    return _result('unknown', 'stoichiometry_recorded_for_the_sheet', [])


def _column_calibration(record, native):
    return _one_fact(record, 'column_calibrated_with_standards')


def _resin_interaction(record, native):
    item = record['facts']['buffer_rules_out_resin_interaction']
    status, reason = _shared_rule([item['answer']])
    if status != 'unknown':
        return _result(status, reason, item['source_refs'])
    salt = native['salt_mM']
    if salt is None:
        return _result('unknown', 'fact_unknown', [])
    native['salt_refs'] = _refs(record['quantities']['salt_concentration'])
    return _result('unknown', 'salt_recorded_for_the_sheet', [])


def _complex_stable_on_column(record, native):
    loaded, kd = native['loaded_nM'], native['kd_nM']
    if loaded is None or kd is None:
        return _fact_unless_no_kd(record, native, 'complex_stable_on_column')
    native['load_over_kd'] = loaded / kd
    native['load_refs'] = _refs(record['quantities']['loaded_concentration'], record['quantities']['kd'])
    _column(record, native)
    if native['loaded_mL'] is not None:
        native['loaded_refs'] = _refs(record['quantities']['loaded_volume'])
    return _result('unknown', 'load_over_kd_recorded_for_the_sheet', [])


def _monodispersity(record, native):
    polydispersity = _value(record, 'polydispersity')
    if polydispersity is None:
        return _one_fact(record, 'aggregation_absent')
    native.update({'polydispersity': polydispersity, 'polydispersity_refs': _refs(record['quantities']['polydispersity'])})
    return _result('unknown', 'polydispersity_recorded_for_the_sheet', [])


def _single_component_control(record, native):
    return _one_fact(record, 'single_component_control_done')


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


EVALUATORS = {'complex_peak_observed': _complex_peak_observed, 'elution_shift': _elution_shift, 'components_alone': _components_alone, 'complex_composition': _complex_composition, 'titration_depletion': _titration_depletion, 'mals_mass': _mals_mass, 'stoichiometry': _stoichiometry, 'column_calibration': _column_calibration, 'resin_interaction': _resin_interaction, 'complex_stable_on_column': _complex_stable_on_column, 'monodispersity': _monodispersity, 'single_component_control': _single_component_control, 'replicates': _replicates}


def grade_sec(record):
    """Grade one SEC experiment record. Returns the criterion answers and native values."""
    complex_peak = record['facts']['complex_peak_detected']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'column_type': record['column_type'], 'detection': record['detection'], 'spread_kind': record['spread_kind'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'interaction': INTERACTION.get(complex_peak['answer']), 'interaction_refs': list(complex_peak['source_refs']) if complex_peak['answer'] in INTERACTION else [], 'kd_nM': _scaled(record, 'kd', NM_PER_UNIT), 'loaded_nM': _scaled(record, 'loaded_concentration', NM_PER_UNIT), 'salt_mM': _scaled(record, 'salt_concentration', MM_PER_SALT_UNIT), 'loaded_mL': _scaled(record, 'loaded_volume', ML_PER_VOLUME_UNIT), 'loaded_refs': [], 'column_mL': None, 'column_refs': [], 'shift_ml': None, 'shift_refs': [], 'stoichiometry_ratio': None, 'stoichiometry_refs': [], 'salt_refs': [], 'load_refs': [], 'polydispersity': None, 'polydispersity_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': [], 'mass_measured': None, 'mass_theoretical': None, 'mass_deviation_percent': None, 'mass_support_refs': [], 'load_over_kd': None}
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    native['support'] = criterion_supports(record, SEC_CRITERIA)      # kept for the sheet: the grader does not judge it
    return {'version': VERSION, 'experiment_type': 'sec', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
