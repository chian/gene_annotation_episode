"""Coupling_mass_balance grader: judges ONE mass-balance (closure) experiment (substrate consumed against the sum of the identified products, by HPLC, GC, MS or NMR) by its own standards.

DRAFT of 2026-11-22 for the owner to correct. Hand-built and private to coupling_mass_balance. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_coupling_mass_balance_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_coupling_mass_balance_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(closure, zero_time_closure, detection_limit_share, replicate_count, each with its refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The closure. The effect of this experiment is the closure: the share of the substrate consumed that the identified products account for. The grader
fixes which number is the closure, and only by arithmetic that the units define: the stated closure (a percent turned into a fraction); when none
is stated, the stated sum of the products over the substrate consumed (both in units of one kind, concentrations or amounts, turned into nM or nmol); when
that is missing too, one minus the stated residual over the substrate consumed (the residual below the substrate consumed). The origin is recorded
('reported' for a stated closure, 'derived' for the two others) with the refs of every field used and the weakest support among them. Nothing is judged.

The qualitative statement of the experiment is the fact product_formation_detected ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying
whether the substrate was converted to the product or products (or that no product was formed above its own control or detection limit). It is recorded in
native as 'detection' with its refs and its support (class decision for reaction_coupling: 'interaction_detected' reads "coupled product formation detected").
It is only used by the converter when no closure is available.

Native values retained: every record quantity as given, the preparations and the three choices, and closure, closure_origin, closure_component, closure_refs,
closure_support, zero_time_closure, zero_time_refs, detection_limit_share, detection_limit_refs, replicate_count, replicate_independent, replicate_refs, detection,
each with its refs (None or empty when not available).
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_coupling_mass_balance_criteria import COUPLING_MASS_BALANCE_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS, criterion_supports

VERSION = 'a105_coupling_mass_balance_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in COUPLING_MASS_BALANCE_CRITERIA)
DETECTION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact product_formation_detected
PERCENT_PER_FRACTION = 100.0   # FIXED_BY_DEFINITION: a percent is a hundredth.
FRACTION_OF_UNIT = {'fraction': 1.0, 'percent': 1.0 / PERCENT_PER_FRACTION}   # FIXED_BY_DEFINITION: exact unit spelling of a share.
# FIXED_BY_DEFINITION: the kind of a unit (concentrations and amounts cannot be set against each other without a volume) and its exact factor to nM or nmol.
KIND_AND_SCALE = {'nM': ('concentration', 1.0), 'uM': ('concentration', 1.0e3), 'mM': ('concentration', 1.0e6),
                  'pmol': ('amount', 1.0e-3), 'nmol': ('amount', 1.0), 'umol': ('amount', 1.0e3)}
WHOLE = 1.0   # FIXED_BY_DEFINITION: the whole of the substrate consumed (a closure of 1 accounts for all of it).


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _share(record, name):
    """The stated share (closure, closure at zero time) as a fraction, or None."""
    operand = record['quantities'][name]
    return operand['value'] * FRACTION_OF_UNIT[operand['unit']] if operand['status'] == 'point' else None


def _amount(record, name):
    """(kind of unit, value in nM or nmol) of a stated concentration or amount, or None."""
    operand = record['quantities'][name]
    if operand['status'] != 'point':
        return None
    kind, scale = KIND_AND_SCALE[operand['unit']]
    return kind, operand['value'] * scale


def _refs(*items):
    refs = []
    for item in items:
        refs += item['source_refs']
    return list(dict.fromkeys(refs))


def _weakest(*items):
    return max((item['support'] for item in items), key=SUPPORTS.index)


def _closure(record):
    """The closure the record gives or fixes by unit arithmetic: {'value', 'origin', 'component', 'refs', 'support'} or None."""
    quantities = record['quantities']
    stated = _share(record, 'closure')
    if stated is not None:
        return {'value': stated, 'origin': 'reported', 'component': 'closure', 'refs': _refs(quantities['closure']), 'support': quantities['closure']['support']}
    consumed, products, residual = (_amount(record, name) for name in ('substrate_consumed', 'products_total', 'balance_residual'))
    if consumed is None:
        return None
    if products is not None and products[0] == consumed[0]:
        used = (quantities['products_total'], quantities['substrate_consumed'])
        return {'value': products[1] / consumed[1], 'origin': 'derived', 'component': 'products_total_over_substrate_consumed', 'refs': _refs(*used), 'support': _weakest(*used)}
    if residual is not None and residual[0] == consumed[0] and residual[1] < consumed[1]:
        used = (quantities['balance_residual'], quantities['substrate_consumed'])
        return {'value': WHOLE - residual[1] / consumed[1], 'origin': 'derived', 'component': 'one_minus_balance_residual_over_substrate_consumed', 'refs': _refs(*used), 'support': _weakest(*used)}
    return None


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


def _product_identity(record, native):
    return _one_fact(record, 'product_identified')


def _species_calibration(record, native):
    return _one_fact(record, 'each_species_calibrated')


def _method_recovery(record, native):
    zero_time = _share(record, 'zero_time_closure')
    if zero_time is not None:
        native.update({'zero_time_closure': zero_time, 'zero_time_refs': _refs(record['quantities']['zero_time_closure'])})
        return _result('unknown', 'zero_time_closure_recorded_for_the_sheet', [])
    internal = record['facts']['internal_standard']
    if internal['answer'] == 'yes':
        return _result('supported', 'internal_standard_stated', internal['source_refs'])
    return _result('unknown', 'recovery_not_shown', [])


def _minor_species_detectability(record, native):
    limit, consumed = _amount(record, 'detection_limit'), _amount(record, 'substrate_consumed')
    if limit is None or consumed is None:
        return _result('unknown', 'detection_limit_or_consumed_missing', [])
    if limit[0] != consumed[0]:
        return _result('unknown', 'detection_limit_and_consumed_in_different_kinds_of_unit', [])
    native.update({'detection_limit_share': limit[1] / consumed[1], 'detection_limit_refs': _refs(record['quantities']['detection_limit'], record['quantities']['substrate_consumed'])})
    return _result('unknown', 'detection_limit_recorded_for_the_sheet', [])


def _blank_controls(record, native):
    names = ('zero_time_sample', 'no_enzyme_control')
    answers = [record['facts'][n]['answer'] for n in names]
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', 'blank_control_stated', refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _inactive_enzyme(record, native):
    return _one_fact(record, 'inactive_enzyme_control')


def _product_coverage(record, native):
    return _one_fact(record, 'all_products_quantified')


def _volatile_loss(record, native):
    return _one_fact(record, 'volatile_loss_excluded')


def _reaction_equation(record, native):
    return _one_fact(record, 'reaction_equation_stated')


def _closure_bound(record, native):
    if native['closure'] is None:
        return _result('unknown', 'closure_not_available', [])
    return _result('unknown', 'closure_recorded_for_the_sheet', [])


def _matched_windows(record, native):
    names = ('same_mixture', 'same_window')
    status, reason = _shared_rule([record['facts'][n]['answer'] for n in names])
    return _result(status, reason, _refs(*(record['facts'][n] for n in names)))


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


EVALUATORS = {'product_identity': _product_identity, 'species_calibration': _species_calibration, 'method_recovery': _method_recovery,
              'minor_species_detectability': _minor_species_detectability, 'blank_controls': _blank_controls, 'inactive_enzyme': _inactive_enzyme,
              'product_coverage': _product_coverage, 'volatile_loss': _volatile_loss, 'reaction_equation': _reaction_equation, 'closure_bound': _closure_bound,
              'matched_windows': _matched_windows, 'replicates': _replicates, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_coupling_mass_balance(record):
    """Grade one mass-balance record. Returns the criterion answers and native values."""
    detected = record['facts']['product_formation_detected']
    closure = _closure(record)
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'balance_basis': record['balance_basis'], 'analysis_method': record['analysis_method'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'closure': None if closure is None else closure['value'], 'closure_origin': None if closure is None else closure['origin'],
              'closure_component': None if closure is None else closure['component'], 'closure_refs': [] if closure is None else closure['refs'],
              'closure_support': None if closure is None else closure['support'],
              'detection': DETECTION.get(detected['answer']), 'detection_refs': list(detected['source_refs']) if detected['answer'] in DETECTION else [], 'detection_support': detected['support'],
              'zero_time_closure': None, 'zero_time_refs': [], 'detection_limit_share': None, 'detection_limit_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, COUPLING_MASS_BALANCE_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'coupling_mass_balance', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
