"""EMSA grader: judges ONE electrophoretic mobility shift assay (EMSA, gel shift) experiment (a labelled nucleic acid probe incubated with a protein and run on a native gel; the complex migrates more slowly; qualitative, or a titration giving an apparent KD) by its own standards.

Hand-built and private to this method (it shares no grading logic with the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA or pull-down graders).
Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_emsa_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_emsa_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(specific_competitor_excess, incubation_min, probe_over_kd, protein_low_over_kd/protein_high_over_kd, titration_point_count, fraction_shifted_percent,
shifted_species_count, replicate_count/replicate_independent, each with its *_refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet' and no refs; the EMSA converter (literature_emsa_converter.py) judges it, and holds the classification of the fit models
as one-site or not. A fact stated as no stays the grader's own conflicting.

A criterion returns 'supported' or 'conflicting' only with support refs (the quoted spans of the stated fields it rests on);
``_result`` refuses to build one without them. Where only a fact with no span or a model with no reported constant would decide, the
criterion returns 'unknown' (or 'not_applicable' when no apparent KD is reported) with a declared reason.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown;
else all 'not_applicable' -> not_applicable; else supported. specific_competition, protein_identity, equilibrium, probe_concentration,
protein_range, titration_points, saturation, single_complex, fit_model and replicates have their own rules (declared).

An EMSA has two outcomes. With a titration it reports an apparent KD (native 'kd_nM'); without one it reports only the shift. The native
values carry the qualitative statement of the record, 'interaction' ('detected' when a shifted band is stated, 'not_detected' when it is
stated not to be, else None), with the spans that state it ('interaction_refs'); the converter hands it to the merger as the experiment's
qualitative effect when the record has no apparent KD.

Support: native 'support' holds, for each criterion, the supports ('direct', 'implied', 'about_something_else') of the stated fields it reads
(its declared 'reads'), copied from the record and not judged here; the converter judges them.

Native values retained: every record quantity as given, plus kd_nM, probe_nM, protein_low_nM, protein_high_nM, incubation_min, probe_over_kd,
protein_low_over_kd, protein_high_over_kd, interaction, interaction_refs, preparations, probe_type, probe_label, gel_type,
nonspecific_competitor_type, spread_kind and fit_model.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_criteria import (
    EMSA_CRITERIA, MIN_PER_UNIT, NM_PER_UNIT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_emsa_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in EMSA_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact shift_detected
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


def _shift_observed(record, native):
    return _one_fact(record, 'shift_detected')


def _specific_competition(record, native):
    item = record['facts']['shift_abolished_by_specific_competitor']
    excess = _value(record, 'specific_competitor_excess')
    if item['answer'] == 'no' and excess is not None:
        native.update({'specific_competitor_excess': excess, 'specific_competition_refs': list(item['source_refs'])})
        return _result('unknown', 'competition_excess_recorded_for_the_sheet', [])
    status, reason = _shared_rule([item['answer']])
    return _result(status, reason, item['source_refs'])


def _nonspecific_competition(record, native):
    return _one_fact(record, 'shift_not_abolished_by_nonspecific_competitor')


def _mutant_probe(record, native):
    return _one_fact(record, 'mutant_probe_does_not_shift')


def _probe_alone_lane(record, native):
    return _one_fact(record, 'probe_alone_lane_shown')


def _nonspecific_protein_control(record, native):
    return _one_fact(record, 'nonspecific_protein_control_done')


def _protein_identity(record, native):
    items = [record['facts'][name] for name in ('supershift_confirms_protein_identity', 'protein_purified')]
    answers = [item['answer'] for item in items]
    if 'yes' in answers:
        return _result('supported', 'protein_identity_confirmed', _refs(*(item for item in items if item['answer'] == 'yes')))
    if 'unknown' in answers:
        return _result('unknown', 'protein_identity_unknown', [])
    if 'no' in answers:
        return _result('conflicting', 'protein_identity_not_confirmed', _refs(*(item for item in items if item['answer'] == 'no')))
    return _result('not_applicable', 'fact_not_applicable', [])


def _free_probe_quantified(record, native):
    return _one_fact(record, 'free_probe_quantified')


def _equilibrium(record, native):
    item = record['facts']['equilibrium_reached']
    status, reason = _shared_rule([item['answer']])
    if status != 'unknown':
        return _result(status, reason, item['source_refs'])
    if native['incubation_min'] is None:
        return _result('unknown', 'fact_unknown', [])
    native['incubation_refs'] = list(record['quantities']['incubation_time']['source_refs'])
    return _result('unknown', 'incubation_recorded_for_the_sheet', [])


def _complex_stability(record, native):
    return _one_fact(record, 'complex_survives_gel_run')


def _probe_concentration(record, native):
    probe, kd = native['probe_nM'], native['kd_nM']
    if probe is None or kd is None:
        return _fact_unless_no_kd(record, native, 'probe_at_or_below_kd')
    native['probe_over_kd'] = probe / kd
    native['probe_over_kd_refs'] = _refs(record['quantities']['probe_concentration'], record['quantities']['kd'])
    return _result('unknown', 'probe_over_kd_recorded_for_the_sheet', [])


def _protein_range(record, native):
    low, high, kd = native['protein_low_nM'], native['protein_high_nM'], native['kd_nM']
    if low is None or high is None or kd is None:
        return _fact_unless_no_kd(record, native, 'protein_range_brackets_kd')
    native['protein_low_over_kd'], native['protein_high_over_kd'] = low / kd, high / kd
    native['protein_range_refs'] = _refs(*(record['quantities'][name] for name in ('protein_concentration_lowest', 'protein_concentration_highest', 'kd')))
    return _result('unknown', 'protein_range_recorded_for_the_sheet', [])


def _titration_points(record, native):
    if native['kd_nM'] is None:
        return _result('not_applicable', NO_KD, [])
    count = _value(record, 'titration_point_count')
    if count is None:
        return _result('unknown', 'titration_point_count_not_given', [])
    native.update({'titration_point_count': count, 'titration_point_refs': _refs(record['quantities']['titration_point_count'])})
    return _result('unknown', 'titration_points_recorded_for_the_sheet', [])


def _saturation(record, native):
    if native['kd_nM'] is None:
        return _result('not_applicable', NO_KD, [])
    percent = _value(record, 'fraction_shifted_highest')
    if percent is None:
        return _result('unknown', 'fraction_shifted_not_given', [])
    native.update({'fraction_shifted_percent': percent, 'fraction_shifted_refs': _refs(record['quantities']['fraction_shifted_highest'])})
    return _result('unknown', 'fraction_shifted_recorded_for_the_sheet', [])


def _single_complex(record, native):
    count = _value(record, 'shifted_species_count')
    if count is None:
        return _result('unknown', 'shifted_species_count_not_given', [])
    native.update({'shifted_species_count': count, 'shifted_species_refs': _refs(record['quantities']['shifted_species_count']),
                   'shifted_species_kd_refs': _refs(record['quantities']['shifted_species_count'], record['quantities']['kd'])})
    return _result('unknown', 'shifted_species_recorded_for_the_sheet', [])


def _fit_model(record, native):
    if native['kd_nM'] is None:
        return _result('not_applicable', NO_KD, [])
    model = record['fit_model']
    if model is None:
        return _result('unknown', 'fit_model_not_stated', [])
    # the model is a statement about how the reported constant was obtained: the span of the constant is its support (the model has no span of its own)
    refs = _refs(record['quantities']['kd'])
    if model == 'one_site' and native['probe_nM'] is not None:
        native['fit_model_probe_refs'] = _refs(record['quantities']['kd'], record['quantities']['probe_concentration'])      # the quotient is native['probe_over_kd'], set by probe_concentration
        return _result('unknown', 'one_site_probe_over_kd_recorded_for_the_sheet', [])
    return _result('supported', 'model_stated', refs)


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


EVALUATORS = {'shift_observed': _shift_observed, 'specific_competition': _specific_competition, 'nonspecific_competition': _nonspecific_competition, 'mutant_probe': _mutant_probe, 'probe_alone_lane': _probe_alone_lane, 'nonspecific_protein_control': _nonspecific_protein_control, 'protein_identity': _protein_identity, 'free_probe_quantified': _free_probe_quantified, 'equilibrium': _equilibrium, 'complex_stability': _complex_stability, 'probe_concentration': _probe_concentration, 'protein_range': _protein_range, 'titration_points': _titration_points, 'saturation': _saturation, 'single_complex': _single_complex, 'fit_model': _fit_model, 'replicates': _replicates}


def grade_emsa(record):
    """Grade one EMSA experiment record. Returns the criterion answers and native values."""
    shift = record['facts']['shift_detected']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'probe_type': record['probe_type'], 'probe_label': record['probe_label'], 'gel_type': record['gel_type'], 'nonspecific_competitor_type': record['nonspecific_competitor_type'], 'spread_kind': record['spread_kind'], 'fit_model': record['fit_model'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'interaction': INTERACTION.get(shift['answer']), 'interaction_refs': list(shift['source_refs']) if shift['answer'] in INTERACTION else [], 'kd_nM': _scaled(record, 'kd', NM_PER_UNIT), 'probe_nM': _scaled(record, 'probe_concentration', NM_PER_UNIT), 'protein_low_nM': _scaled(record, 'protein_concentration_lowest', NM_PER_UNIT), 'protein_high_nM': _scaled(record, 'protein_concentration_highest', NM_PER_UNIT), 'incubation_min': _scaled(record, 'incubation_time', MIN_PER_UNIT), 'probe_over_kd': None, 'protein_low_over_kd': None, 'protein_high_over_kd': None, 'specific_competitor_excess': None, 'specific_competition_refs': [], 'incubation_refs': [], 'probe_over_kd_refs': [], 'protein_range_refs': [], 'titration_point_count': None, 'titration_point_refs': [], 'fraction_shifted_percent': None, 'fraction_shifted_refs': [], 'shifted_species_count': None, 'shifted_species_refs': [], 'shifted_species_kd_refs': [], 'fit_model_probe_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    native['support'] = criterion_supports(record, EMSA_CRITERIA)      # kept for the sheet: the grader does not judge it
    return {'version': VERSION, 'experiment_type': 'emsa', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
