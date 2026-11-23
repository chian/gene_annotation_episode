"""Coupling_atp_product grader: judges ONE nucleotide-hydrolysis-to-product coupling experiment (ATP or GTP hydrolysis measured by phosphate release,
the pyruvate kinase / lactate dehydrogenase coupled assay, [gamma-32P] release or chromatography, in the same reaction as the product it drives) by its own standards.

Hand-built and private to coupling_atp_product. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_coupling_atp_product_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_coupling_atp_product_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(basal_share, consumed_percent, link_refs, replicate_count, each with its refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact coupled_product_detected ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying
whether it saw the product formed above its own control. It is recorded in native as 'coupling' with its refs and its support (class decision of 2026-11-22,
owner to confirm: 'interaction_detected' reads "coupled product formation detected"). It is only used by the converter when no link is stated.

Native values retained: every record quantity as given, the choices and the preparations, and basal_share, consumed_percent, link_refs, replicate_count,
replicate_independent, coupling, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_coupling_atp_product_criteria import (
    COUPLING_ATP_PRODUCT_CRITERIA, RATE_UNIT_SCALE)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_coupling_atp_product_grade'
CRITERIA = tuple(criterion['id'] for criterion in COUPLING_ATP_PRODUCT_CRITERIA)
COUPLING = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact coupled_product_detected
CHOICE_NAMES = ('spread_kind', 'nucleotide', 'hydrolysis_readout')


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


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
        raise ValueError(f'a {status} result needs support refs: {reason}')
    return {'status': status, 'reason': reason, 'support_refs': refs if status in ('supported', 'conflicting') else []}


def _one_fact(record, name):
    item = record['facts'][name]
    status, reason = _shared_rule([item['answer']])
    return _result(status, reason, item['source_refs'])


def _no_enzyme_control(record, native):
    return _one_fact(record, 'no_enzyme_control')


def _reagent_blank(record, native):
    return _one_fact(record, 'reagent_blank_done')


def _basal_rate_accounted(record, native):
    return _one_fact(record, 'basal_rate_subtracted')


def _basal_share(record, native):
    basal, total = record['quantities']['basal_rate'], record['quantities']['nucleotide_rate']
    if basal['status'] != 'point' or total['status'] != 'point':
        return _result('unknown', 'basal_or_total_rate_missing', [])
    basal_kind, basal_scale = RATE_UNIT_SCALE[basal['unit']]
    total_kind, total_scale = RATE_UNIT_SCALE[total['unit']]
    if basal_kind != total_kind:
        return _result('unknown', 'rate_units_not_comparable', [])
    native['basal_share'] = basal['value'] * basal_scale / (total['value'] * total_scale)
    native['basal_refs'] = _refs(basal, total)
    return _result('unknown', 'basal_share_recorded_for_the_sheet', [])


def _reporter_capacity(record, native):
    names = ('coupling_enzymes_in_excess', 'signal_in_linear_range')
    answers = [record['facts'][n]['answer'] for n in names]
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', 'reporter_capacity_stated', refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _nucleotide_supply(record, native):
    regenerated = record['facts']['nucleotide_regenerated']
    consumed = record['quantities']['nucleotide_consumed_percent']
    if regenerated['answer'] == 'yes':
        return _result('supported', 'nucleotide_regenerated_stated', regenerated['source_refs'])
    if consumed['status'] == 'point':
        native.update({'consumed_percent': consumed['value'], 'consumed_refs': _refs(consumed)})
        return _result('unknown', 'consumed_recorded_for_the_sheet', [])
    return _result('unknown', 'nucleotide_supply_not_stated', [])


def _hydrolysis_dependence(record, native):
    return _one_fact(record, 'product_requires_hydrolysis')


def _product_identity(record, native):
    return _one_fact(record, 'product_identified')


def _product_calibration(record, native):
    return _one_fact(record, 'product_calibrated')


def _nucleotide_calibration(record, native):
    return _one_fact(record, 'nucleotide_side_calibrated')


def _same_mixture(record, native):
    return _one_fact(record, 'same_mixture')


def _same_window(record, native):
    return _one_fact(record, 'same_window')


def _coefficient_stated(record, native):
    coefficient = record['quantities']['stoichiometric_coefficient']
    if coefficient['status'] != 'point':
        return _result('unknown', 'coefficient_not_stated', [])
    return _result('supported', 'coefficient_stated', _refs(coefficient))


def _coupling_within_bound(record, native):
    quantities = record['quantities']
    fraction, coefficient = quantities['productive_fraction'], quantities['stoichiometric_coefficient']
    cost, ratio = quantities['nucleotides_per_product'], quantities['stoichiometric_ratio']
    if fraction['status'] == 'point':
        native['link_refs'] = _refs(fraction)
    elif coefficient['status'] == 'point' and (cost['status'] == 'point' or ratio['status'] == 'point'):
        native['link_refs'] = _refs(coefficient, *(item for item in (cost, ratio) if item['status'] == 'point'))
    else:
        return _result('unknown', 'productive_fraction_not_available', [])
    return _result('unknown', 'link_recorded_for_the_sheet', [])


def _replicates(record, native):
    count = _value(record, 'replicate_count')
    independent = record['facts']['independent_replicates']
    refs = _refs(record['quantities']['replicate_count'], independent)
    if independent['answer'] == 'no':
        return _result('conflicting', 'replicates_not_independent', refs)
    if count is None:
        return _result('unknown', 'replicate_count_or_independence_unknown', [])
    native.update({'replicate_count': count, 'replicate_independent': independent['answer'], 'replicate_refs': refs})
    return _result('unknown', 'replicate_count_recorded_for_the_sheet', [])


def _native_reaction(record, native):
    return _one_fact(record, 'native_substrate')


def _purified_enzyme(record, native):
    return _one_fact(record, 'purified_enzyme')


EVALUATORS = {'no_enzyme_control': _no_enzyme_control, 'reagent_blank': _reagent_blank, 'basal_rate_accounted': _basal_rate_accounted, 'basal_share': _basal_share,
              'reporter_capacity': _reporter_capacity, 'nucleotide_supply': _nucleotide_supply, 'hydrolysis_dependence': _hydrolysis_dependence,
              'product_identity': _product_identity, 'product_calibration': _product_calibration, 'nucleotide_calibration': _nucleotide_calibration,
              'same_mixture': _same_mixture, 'same_window': _same_window, 'coefficient_stated': _coefficient_stated, 'coupling_within_bound': _coupling_within_bound,
              'replicates': _replicates, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_coupling_atp_product(record):
    """Grade one nucleotide-hydrolysis-to-product coupling record. Returns the criterion answers and native values."""
    detected = record['facts']['coupled_product_detected']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              **{name: record[name] for name in CHOICE_NAMES}, 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'coupling': COUPLING.get(detected['answer']), 'coupling_refs': list(detected['source_refs']) if detected['answer'] in COUPLING else [], 'coupling_support': detected['support'],
              'basal_share': None, 'basal_refs': [], 'consumed_percent': None, 'consumed_refs': [], 'link_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, COUPLING_ATP_PRODUCT_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'coupling_atp_product', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
