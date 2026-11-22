"""Coupling_cofactor_product grader: judges ONE cofactor-consumption / identified-product coupling experiment (NAD(P)H consumption read at 340 nm or by HPLC, paired with a
product identified and counted by chromatography or mass spectrometry in the same reaction; coupling percent = coefficient x product / cofactor) by its own standards.

Hand-built and private to coupling_cofactor_product. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_coupling_cofactor_product_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_coupling_cofactor_product_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(absorbance_max, recovery_percent, background_over_test, link_value, replicate_count, each with its refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. A supported or conflicting result always carries the refs of the spans it rests on (``_result`` raises without them).

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

THE COUPLING VALUE ('link'). The experiment's measured result is the link between the consumed cofactor and the formed product. The grader finds the one value the
converter will use as the experiment's effect and records it, with exact arithmetic only (no judgement, no threshold): in this order
  1. the stated productive fraction (reported);
  2. the reaction's stated coefficient times the product per cofactor (derived), where the product per cofactor is, in this order, the stated ratio, the reverse of the
     stated cofactor per product, the product amount over the cofactor amount, the product rate over the cofactor rate (an amount or a rate is compared with another only
     inside one unit family of the record's UNIT_SCALE: a concentration and an amount, or a rate per mg and a rate per reaction, are not);
  3. the product per cofactor itself, when no coefficient is stated (a bare ratio, read by the sheet as one product per cofactor).
It is recorded in native as 'link' = {quantity ('productive_fraction' or 'stoichiometric_ratio'), value (a number, the anchor unit 'fraction' of the class), origin
('reported' or 'derived'), refs (the spans of every stated field it rests on), support (the weakest support of those fields), spread and spread_refs (the stated spread of the
quantity, only for a reported value), sources (the field names)} or None when nothing is stated or derivable.

The qualitative statement of the experiment is the fact coupled_product_detected ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying whether the
product was formed above its own control or detection limit while the cofactor was consumed. It is recorded in native as 'coupling' with its refs and its support
(class decision of 2026-11-22: 'interaction_detected' reads "coupled product formation detected"). It is only used by the converter when no coupling value is found.

Native values retained: every record quantity as given, spread_kind, link, link_value, link_refs, absorbance_max, recovery_percent, background_over_test,
replicate_count, replicate_independent, coupling, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_coupling_cofactor_product_record import UNIT_SCALE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_coupling_cofactor_product_criteria import (
    COUPLING_COFACTOR_PRODUCT_CRITERIA)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SUPPORT_WEAKEST_ORDER
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_coupling_cofactor_product_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in COUPLING_COFACTOR_PRODUCT_CRITERIA)
COUPLING = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact coupled_product_detected
PERCENT_PER_FRACTION = 100.0   # FIXED_BY_DEFINITION: a percent is a hundredth.


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _fraction(record, name):
    """A stated fraction-or-percent or mol-per-mol quantity as a plain number (a percent divided by its hundred), or None."""
    value = _value(record, name)
    if value is None:
        return None
    return value / PERCENT_PER_FRACTION if record['quantities'][name]['unit'] == 'percent' else value


def _side(record, name):
    """(family, value in the family's base unit) of a stated amount or rate, or None."""
    value = _value(record, name)
    if value is None:
        return None
    family, factor = UNIT_SCALE[record['quantities'][name]['unit']]
    return family, value * factor


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


def _quotient(record, numerator, denominator):
    """The numerator over the denominator of two stated amounts (or two stated rates) of one unit family, or None."""
    top, bottom = _side(record, numerator), _side(record, denominator)
    if top is None or bottom is None or top[0] != bottom[0]:
        return None
    return top[1] / bottom[1]


def _product_per_cofactor(record):
    """(value, the names of the fields it rests on, origin) of the moles of product per mole of cofactor, or None."""
    if _value(record, 'stoichiometric_ratio') is not None:
        return _value(record, 'stoichiometric_ratio'), ('stoichiometric_ratio',), 'reported'
    if _value(record, 'cofactor_per_product') is not None:
        return 1 / _value(record, 'cofactor_per_product'), ('cofactor_per_product',), 'derived'
    for product, cofactor in (('product_formed', 'cofactor_consumed'), ('product_rate', 'cofactor_rate')):
        quotient = _quotient(record, product, cofactor)
        if quotient is not None:
            return quotient, (product, cofactor), 'derived'
    return None


def _candidate(record, quantity, value, names, origin, spread_name):
    operands = [record['quantities'][name] for name in names]
    supports = [operand['support'] for operand in operands if operand['support'] is not None]
    spread = _fraction(record, spread_name) if spread_name is not None else None
    return {'quantity': quantity, 'value': value, 'origin': origin, 'refs': _refs(*operands), 'support': min(supports, key=SUPPORT_WEAKEST_ORDER.index), 'sources': list(names),
            'spread': spread, 'spread_refs': _refs(record['quantities'][spread_name]) if spread is not None else []}


def _link(record):
    """The coupling value of the experiment (see the module docstring), or None."""
    if _value(record, 'productive_fraction') is not None:
        return _candidate(record, 'productive_fraction', _fraction(record, 'productive_fraction'), ('productive_fraction',), 'reported', 'productive_fraction_spread')
    found = _product_per_cofactor(record)
    if found is None:
        return None
    ratio, names, origin = found
    coefficient = _value(record, 'stoichiometric_coefficient')
    if coefficient is not None:
        return _candidate(record, 'productive_fraction', coefficient * ratio, (*names, 'stoichiometric_coefficient'), 'derived', None)
    return _candidate(record, 'stoichiometric_ratio', ratio, names, origin, 'stoichiometric_ratio_spread' if origin == 'reported' else None)


def _product_identified(record, native):
    return _one_fact(record, 'product_identified')


def _product_calibrated(record, native):
    return _one_fact(record, 'product_calibrated')


def _extinction_coefficient_stated(record, native):
    if _value(record, 'extinction_coefficient') is None or _value(record, 'wavelength') is None:
        return _result('unknown', 'extinction_coefficient_or_wavelength_missing', [])
    return _result('supported', 'extinction_coefficient_and_wavelength_stated', _refs(record['quantities']['extinction_coefficient'], record['quantities']['wavelength']))


def _absorbance_range(record, native):
    value = _value(record, 'absorbance_max')
    if value is None:
        return _result('unknown', 'absorbance_not_stated', [])
    native.update({'absorbance_max': value, 'absorbance_refs': _refs(record['quantities']['absorbance_max'])})
    return _result('unknown', 'absorbance_recorded_for_the_sheet', [])


def _calibration_recovery(record, native):
    value = _value(record, 'calibration_recovery')
    if value is None:
        return _result('unknown', 'recovery_not_stated', [])
    native.update({'recovery_percent': value, 'recovery_refs': _refs(record['quantities']['calibration_recovery'])})
    return _result('unknown', 'recovery_recorded_for_the_sheet', [])


def _coefficient_stated(record, native):
    if _value(record, 'stoichiometric_coefficient') is None:
        return _result('unknown', 'coefficient_not_stated', [])
    return _result('supported', 'coefficient_stated', _refs(record['quantities']['stoichiometric_coefficient']))


def _stoichiometric_bound(record, native):
    link = native['link']
    if link is None:
        return _result('unknown', 'no_coupling_value_stated', [])
    native.update({'link_value': link['value'], 'link_refs': list(link['refs'])})
    return _result('unknown', 'link_recorded_for_the_sheet', [])


def _same_enzyme_preparation(record, native):
    return _one_fact(record, 'same_preparation')


def _same_reaction_mixture(record, native):
    return _one_fact(record, 'same_mixture')


def _same_window(record, native):
    return _one_fact(record, 'same_window')


def _no_substrate_oxidation(record, native):
    control = record['facts']['no_substrate_control']
    refs = _refs(record['quantities']['no_substrate_cofactor_rate'], record['quantities']['cofactor_rate'], control)
    if control['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    background, test = _side(record, 'no_substrate_cofactor_rate'), _side(record, 'cofactor_rate')
    if background is not None and test is not None and background[0] == test[0]:
        native.update({'background_over_test': background[1] / test[1], 'background_refs': refs})
        return _result('unknown', 'background_recorded_for_the_sheet', [])
    if control['answer'] == 'yes':
        return _result('supported', 'no_substrate_control_stated', control['source_refs'])
    return _result('unknown', 'no_substrate_control_not_stated', [])


def _byproduct_accounted(record, native):
    return _one_fact(record, 'byproduct_accounted')


def _spontaneous_oxidation_control(record, native):
    return _one_fact(record, 'no_enzyme_control')


def _background_subtracted(record, native):
    return _one_fact(record, 'background_subtracted')


def _inactive_enzyme_control(record, native):
    return _one_fact(record, 'inactive_enzyme_control')


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


EVALUATORS = {'product_identified': _product_identified, 'product_calibrated': _product_calibrated, 'extinction_coefficient_stated': _extinction_coefficient_stated,
              'absorbance_range': _absorbance_range, 'calibration_recovery': _calibration_recovery, 'coefficient_stated': _coefficient_stated,
              'stoichiometric_bound': _stoichiometric_bound, 'same_enzyme_preparation': _same_enzyme_preparation, 'same_reaction_mixture': _same_reaction_mixture,
              'same_window': _same_window, 'no_substrate_oxidation': _no_substrate_oxidation, 'byproduct_accounted': _byproduct_accounted,
              'spontaneous_oxidation_control': _spontaneous_oxidation_control, 'background_subtracted': _background_subtracted,
              'inactive_enzyme_control': _inactive_enzyme_control, 'replicates': _replicates, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_coupling_cofactor_product(record):
    """Grade one cofactor-consumption / identified-product coupling record. Returns the criterion answers and native values."""
    detected = record['facts']['coupled_product_detected']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'link': _link(record),
              'coupling': COUPLING.get(detected['answer']), 'coupling_refs': list(detected['source_refs']) if detected['answer'] in COUPLING else [], 'coupling_support': detected['support'],
              'link_value': None, 'link_refs': [], 'absorbance_max': None, 'absorbance_refs': [], 'recovery_percent': None, 'recovery_refs': [], 'background_over_test': None, 'background_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, COUPLING_COFACTOR_PRODUCT_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'coupling_cofactor_product', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
