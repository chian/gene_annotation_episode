"""Coupling_oxygen_product grader: judges ONE oxygen-uptake-with-product coupling experiment by its own standards (class reaction_coupling; one enzyme reaction in one
vessel, the dissolved oxygen read with an electrode or optode, the claimed product identified and counted by another measurement over the same interval; the result is
the product made per oxygen consumed, with the oxygen that went to hydrogen peroxide accounted for). DRAFT 2026-11-22 for the owner to correct; nothing was run.

Hand-built and private to coupling_oxygen_product. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_coupling_oxygen_product_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_coupling_oxygen_product_criteria.py (the single source).
This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs (air_saturated_uM, drift_percent,
no_substrate_percent, coupling_fraction, window_ratio, replicate_count, each with its refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet', and
no refs; the converter judges it. The only constants here are unit conversions, FIXED_BY_DEFINITION.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. A supported or conflicting result always carries support refs (``_result`` refuses it without them).

The effect candidates (native 'effect_candidates'). The coupling is the paper's number where it states one and exact arithmetic on its stated numbers where it does not.
Nothing is estimated and nothing is judged; each candidate says where it came from (origin 'reported' or 'derived'), the refs of every stated number it rests on, and the
weakest support of those numbers:
  productive_fraction   the stated productive fraction (a percent divided by 100); else the stoichiometric coefficient times the bare ratio below, when the coefficient is stated
  stoichiometric_ratio  the stated product per oxygen; else the exact reciprocal of a stated oxygen per product; else the product over the oxygen of the two sides stated in
                        the same kind of unit (both amounts, both concentrations, or both rates per the same basis), when the passage does not say the two sides were in different
                        vessels or windows (same_vessel or same_window stated as no): then the paper itself says the two numbers do not belong together and no ratio is made
The converter chooses between them with the class order (the productive fraction first). 'coupling_fraction' is the productive fraction candidate's value (None when none).

The qualitative statement of the experiment is the fact coupling_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying whether
it saw product formation coupled to oxygen consumption above its own control. It is recorded in native as 'interaction' with its refs and its support (class decision of
2026-11-22: 'interaction_detected' reads "coupled product formation detected"). It is only used by the converter when no effect is available.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion (native 'support': criterion id -> the
supports of the stated fields it reads) for the converter.

Native values retained: every record quantity as given, spread_kind, effect_candidates, coupling_fraction and coupling_fraction_refs, air_saturated_uM, drift_percent,
no_substrate_percent, peroxide_percent, window_ratio, replicate_count, replicate_independent, interaction, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_coupling_oxygen_product_criteria import COUPLING_OXYGEN_PRODUCT_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS, criterion_supports

VERSION = 'a105_coupling_oxygen_product_grade'
CRITERIA = tuple(criterion['id'] for criterion in COUPLING_OXYGEN_PRODUCT_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact coupling_detected_above_control
FRACTION_PER_PERCENT = 0.01      # FIXED_BY_DEFINITION: a percent is a hundredth.
SECONDS_PER_MINUTE = 60.0        # FIXED_BY_DEFINITION
MINUTES_PER_HOUR = 60.0          # FIXED_BY_DEFINITION
MIN_PER_UNIT = {'s': 1.0 / SECONDS_PER_MINUTE, 'min': 1.0, 'h': MINUTES_PER_HOUR}   # FIXED_BY_DEFINITION: the windows in minutes
UM_PER_UNIT = {'nM': 1.0e-3, 'uM': 1.0, 'mM': 1.0e3}                                  # FIXED_BY_DEFINITION: concentrations in uM
# FIXED_BY_DEFINITION: the units of the two sides, grouped by what they measure (a product and an oxygen number are divided only inside one group), each in the group's base unit:
# concentrations in uM, amounts in umol, concentration rates in uM/min, amount rates in umol/min, specific rates in umol/min/mg (1 U is 1 umol/min; 1 nmol/s is 0.06 umol/min).
UNIT_GROUPS = {
    'concentration': {'nM': 1.0e-3, 'uM': 1.0, 'mM': 1.0e3},
    'amount': {'pmol': 1.0e-6, 'nmol': 1.0e-3, 'umol': 1.0},
    'concentration_rate': {'nM/min': 1.0e-3, 'nM/s': 1.0e-3 * SECONDS_PER_MINUTE, 'uM/min': 1.0, 'uM/s': SECONDS_PER_MINUTE},
    'amount_rate': {'pmol/min': 1.0e-6, 'nmol/min': 1.0e-3, 'nmol/s': 1.0e-3 * SECONDS_PER_MINUTE, 'umol/min': 1.0},
    'specific_rate': {'pmol/min/mg': 1.0e-6, 'nmol/min/mg': 1.0e-3, 'umol/min/mg': 1.0, 'U/mg': 1.0},
}
SIDES = (('product_formed', 'oxygen_consumed'), ('product_rate', 'oxygen_rate'))   # the pairs of the two sides: amounts first, then rates


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


def _weakest(*operands):
    """The weakest support class among the stated operands (SUPPORTS runs from the strongest to the weakest)."""
    return max((operand['support'] for operand in operands), key=SUPPORTS.index)


def _candidate(value, operands, origin, component, spread):
    return {'value': value, 'refs': _refs(*operands), 'origin': origin, 'component': component, 'support': _weakest(*operands), 'spread': spread}


def _group_of(unit):
    return next(name for name, table in UNIT_GROUPS.items() if unit in table)


def _ratio_of_sides(record):
    """The product over the oxygen of the first pair of sides that are both stated points in the same group of units, with the two operands; None when there is none."""
    for product_name, oxygen_name in SIDES:
        product, oxygen = record['quantities'][product_name], record['quantities'][oxygen_name]
        if product['status'] == 'point' and oxygen['status'] == 'point' and _group_of(product['unit']) == _group_of(oxygen['unit']):
            table = UNIT_GROUPS[_group_of(product['unit'])]
            return (product['value'] * table[product['unit']]) / (oxygen['value'] * table[oxygen['unit']]), (product, oxygen)
    return None


def _effect_candidates(record):
    """{'productive_fraction': candidate or None, 'stoichiometric_ratio': candidate or None}, see the module docstring."""
    quantities = record['quantities']
    fraction, ratio = quantities['productive_fraction'], quantities['stoichiometric_ratio']
    per_product, coefficient = quantities['oxygen_per_product'], quantities['stoichiometric_coefficient']
    bare = None
    if ratio['status'] == 'point':
        bare = _candidate(ratio['value'], (ratio,), 'reported', 'stoichiometric_ratio', 'stoichiometric_ratio_spread')
    elif per_product['status'] == 'point':
        bare = _candidate(1.0 / per_product['value'], (per_product,), 'derived', 'oxygen_per_product', None)
    elif 'no' not in (record['facts']['same_vessel']['answer'], record['facts']['same_window']['answer']) and _ratio_of_sides(record) is not None:
        value, sides = _ratio_of_sides(record)
        bare = _candidate(value, sides, 'derived', 'product_formed' if sides[0] is quantities['product_formed'] else 'product_rate', None)
    productive = None
    if fraction['status'] == 'point':
        scale = FRACTION_PER_PERCENT if fraction['unit'] == 'percent' else 1.0
        productive = _candidate(fraction['value'] * scale, (fraction,), 'reported', 'productive_fraction', 'productive_fraction_spread')
    elif bare is not None and coefficient['status'] == 'point':
        productive = _candidate(coefficient['value'] * bare['value'], (coefficient,), 'derived', bare['component'], None)
        productive['refs'] = list(dict.fromkeys([*bare['refs'], *productive['refs']]))
        productive['support'] = max((bare['support'], productive['support']), key=SUPPORTS.index)
    return {'productive_fraction': productive, 'stoichiometric_ratio': bare}


def _electrode_calibration(record, native):
    item, saturated = record['facts']['electrode_calibrated'], record['quantities']['air_saturated_oxygen']
    if item['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', _refs(item, saturated))
    if saturated['status'] == 'point':
        native.update({'air_saturated_uM': saturated['value'] * UM_PER_UNIT[saturated['unit']], 'air_saturated_refs': _refs(saturated)})
        return _result('unknown', 'air_saturated_recorded_for_the_sheet', [])
    return _one_fact(record, 'electrode_calibrated')


def _oxygen_drift(record, native):
    item, drift = record['facts']['drift_subtracted'], record['quantities']['drift_percent']
    if item['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', _refs(item, drift))
    if drift['status'] == 'point':
        native.update({'drift_percent': drift['value'], 'drift_refs': _refs(drift)})
        return _result('unknown', 'drift_recorded_for_the_sheet', [])
    return _one_fact(record, 'drift_subtracted')


def _no_enzyme_oxygen_control(record, native):
    return _one_fact(record, 'no_enzyme_control')


def _enzyme_dependence(record, native):
    return _one_fact(record, 'inactive_enzyme_control')


def _substrate_independent_oxygen(record, native):
    item, uptake = record['facts']['no_substrate_control'], record['quantities']['no_substrate_oxygen_percent']
    if item['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', _refs(item, uptake))
    if uptake['status'] == 'point':
        native.update({'no_substrate_percent': uptake['value'], 'no_substrate_refs': _refs(uptake)})
        return _result('unknown', 'no_substrate_recorded_for_the_sheet', [])
    return _one_fact(record, 'no_substrate_control')


def _peroxide_accounting(record, native):
    item, peroxide = record['facts']['peroxide_accounted'], record['quantities']['peroxide_percent_of_oxygen']
    if peroxide['status'] == 'point':
        native.update({'peroxide_percent': peroxide['value'], 'peroxide_refs': _refs(peroxide)})
    if item['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', _refs(item, peroxide))
    if item['answer'] == 'yes' or peroxide['status'] == 'point':
        return _result('supported', 'peroxide_accounting_stated', _refs(item, peroxide))
    status, reason = _shared_rule([item['answer']])
    return _result(status, reason, [])


def _product_identity(record, native):
    return _one_fact(record, 'product_identified')


def _product_calibration(record, native):
    return _one_fact(record, 'product_calibrated')


def _stoichiometry(record, native):
    coefficient = record['quantities']['stoichiometric_coefficient']
    if coefficient['status'] != 'point':
        return _result('unknown', 'coefficient_not_stated', [])
    productive = native['effect_candidates']['productive_fraction']
    if productive is None:
        return _result('supported', 'coefficient_stated', _refs(coefficient))
    native.update({'coupling_fraction': productive['value'], 'coupling_fraction_refs': list(dict.fromkeys([*productive['refs'], *_refs(coefficient)]))})
    return _result('unknown', 'stoichiometry_recorded_for_the_sheet', [])


def _same_vessel(record, native):
    return _one_fact(record, 'same_vessel')


def _window_overlap(record, native):
    item = record['facts']['same_window']
    windows = [record['quantities'][name] for name in ('oxygen_window', 'product_window')]
    if item['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', _refs(item, *windows))
    if all(window['status'] == 'point' for window in windows):
        minutes = [window['value'] * MIN_PER_UNIT[window['unit']] for window in windows]
        native.update({'window_ratio': min(minutes) / max(minutes), 'window_refs': _refs(*windows)})
        return _result('unknown', 'windows_recorded_for_the_sheet', [])
    if item['answer'] == 'yes':
        return _result('supported', 'same_window_stated', item['source_refs'])
    status, reason = _shared_rule([item['answer']])
    return _result(status, 'window_not_stated' if status == 'unknown' else reason, [])


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


EVALUATORS = {'electrode_calibration': _electrode_calibration, 'oxygen_drift': _oxygen_drift, 'no_enzyme_oxygen_control': _no_enzyme_oxygen_control,
              'enzyme_dependence': _enzyme_dependence, 'substrate_independent_oxygen': _substrate_independent_oxygen, 'peroxide_accounting': _peroxide_accounting,
              'product_identity': _product_identity, 'product_calibration': _product_calibration, 'stoichiometry': _stoichiometry, 'same_vessel': _same_vessel,
              'window_overlap': _window_overlap, 'replicates': _replicates, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_coupling_oxygen_product(record):
    """Grade one oxygen-uptake-with-product coupling record. Returns the criterion answers and native values."""
    detected = record['facts']['coupling_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'interaction': INTERACTION.get(detected['answer']), 'interaction_refs': list(detected['source_refs']) if detected['answer'] in INTERACTION else [], 'interaction_support': detected['support'],
              'effect_candidates': _effect_candidates(record), 'coupling_fraction': None, 'coupling_fraction_refs': [], 'air_saturated_uM': None, 'air_saturated_refs': [],
              'drift_percent': None, 'drift_refs': [], 'no_substrate_percent': None, 'no_substrate_refs': [], 'peroxide_percent': None, 'peroxide_refs': [],
              'window_ratio': None, 'window_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, COUPLING_OXYGEN_PRODUCT_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'coupling_oxygen_product', 'experiment_ref': record['experiment_ref'],
            'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()},
            'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
