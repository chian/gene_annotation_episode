"""Read native numerical routes from retained draft evidence-axis records.

This module does not install an annotation policy, aggregate different native
scales, or call a model. A dataset analysis and an extracted published experiment
use the same input. Original experiment/measurement identities deduplicate their
representations; source records and witness chains remain available in output.
The rejected overall categorical recipes remain readable historical metadata,
but cannot supply a number. The narrowly justified HGT explanation is separate
from those withdrawn assurance/plausibility ladders.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math

from jsonschema import Draft202012Validator
from method_loop.durable import canonical

from .domain import ATOM
from .evidence_axis_contracts import (
    SCORING_VERSION, TEXT, obj, rows, judgment_schema,
    validate_axis_judgment, validate_evidence_axis_entry,
)


def _copy(value):
    try:
        return json.loads(canonical(value))
    except ValueError as error:
        if 'Out of range float' in str(error):
            raise ValueError('evidence_axis_native_number_nonfinite') from error
        raise


_TEXTS = {**rows(TEXT), 'uniqueItems': True}
_NULL_TEXT = {'type': ['string', 'null'], 'pattern': r'\S'}
_FACT = obj({
    'metric_id': TEXT,
    'observation': TEXT,
    'measurement_index': {'type': 'integer', 'minimum': 0},
    'native_field': TEXT,
    'native_value': deepcopy(ATOM['anyOf'][0]),
    'declared_native_unit': _NULL_TEXT,
    'direction': {'enum': ['higher', 'lower', 'target_dependent', 'not_ordered']},
    'source': TEXT,
    'source_subjects': _TEXTS,
    'subjects': _TEXTS,
    'dependencies': _TEXTS,
    'method': obj({'provider': TEXT, 'recorded_source_version': _NULL_TEXT,
                   'request_record': _NULL_TEXT}),
})
# Provider/version alone do not establish matching parameters, reference data or
# the same scientific comparison. An actual extractor may supply these facts;
# the evaluator never synthesizes them from a source/provider label.
_FACT['properties']['comparison_context'] = obj({
    'method': TEXT, 'version': TEXT, 'parameters': TEXT,
    'reference_set': _NULL_TEXT, 'comparison': TEXT,
})


def evidence_unit_schema(entry):
    """The same formal input for literature extraction and dataset analysis.

    experiment_id identifies the ORIGINAL experiment, not a publication or a
    database row. measurement_id identifies the original measurement within it.
    Their cross-representation identity must be established by the caller; this
    evaluator does not guess that two similar experiments are identical.
    """
    entry = validate_evidence_axis_entry(entry)
    return obj({
        'experiment_id': TEXT,
        'representation_id': TEXT,
        'origin': {'enum': ['literature', 'dataset']},
        'measurements': rows(obj({'measurement_id': TEXT, 'fact': _FACT})),
        'judgment': judgment_schema(entry),
        'witnesses': {**_TEXTS, 'minItems': 1},
    })


def validate_evidence_unit(entry, value, *, resolve_witness=None):
    entry, value = validate_evidence_axis_entry(entry), _copy(value)
    if not Draft202012Validator(evidence_unit_schema(entry)).is_valid(value):
        raise ValueError('evidence_axis_scoring_input_invalid')
    validate_axis_judgment(entry, value['judgment'], resolve_witness=resolve_witness)
    metrics = {row['metric_id']: row for row in entry['native_measurements']}
    identities = set()
    witnesses = list(value['witnesses'])
    for measurement in value['measurements']:
        fact = measurement['fact']
        metric = metrics.get(fact['metric_id'])
        identity = measurement['measurement_id'], fact['metric_id']
        if identity in identities:
            raise ValueError('evidence_axis_measurement_identity_duplicate')
        identities.add(identity)
        if metric is None or fact['direction'] != metric['direction']:
            raise ValueError('evidence_axis_native_metric_mismatch')
        if (fact['declared_native_unit'] is not None
                and fact['declared_native_unit'] not in metric['units']):
            raise ValueError('evidence_axis_native_unit_mismatch')
        number = fact['native_value']['value']
        if isinstance(number, bool) or not math.isfinite(number):
            raise ValueError('evidence_axis_native_number_nonfinite')
        uncertainty = fact['native_value'].get('uncertainty')
        if uncertainty is not None and not math.isfinite(uncertainty['magnitude']):
            raise ValueError('evidence_axis_native_number_nonfinite')
        witnesses.extend([fact['observation'], fact['source'], *fact['subjects'],
                          *fact['source_subjects'], *fact['dependencies']])
        if fact['method']['request_record'] is not None:
            witnesses.append(fact['method']['request_record'])
    if resolve_witness is not None and any(not resolve_witness(ref) for ref in witnesses):
        raise ValueError('evidence_axis_witness_unavailable')
    return value


def _interval(atom):
    value, bound = atom['value'], atom.get('bound')
    if bound in ('less_than', 'less_or_equal'):
        return None, value, False, bound == 'less_or_equal'
    if bound in ('greater_than', 'greater_or_equal'):
        return value, None, bound == 'greater_or_equal', False
    return value, value, True, True


def _bounds(interval):
    low, high, low_closed, high_closed = interval
    return {'lower': low, 'upper': high,
            'lower_inclusive': low_closed, 'upper_inclusive': high_closed}


def _measurement_interval(fact, metrics):
    low, high, low_closed, high_closed = _interval(fact['native_value'])
    declared = metrics[fact['metric_id']].get('valid_range', {})
    minimum, maximum = declared.get('minimum'), declared.get('maximum')
    if minimum is not None and (low is None or minimum > low):
        low, low_closed = minimum, True
    if maximum is not None and (high is None or maximum < high):
        high, high_closed = maximum, True
    if low is not None and high is not None and (
            low > high or low == high and not (low_closed and high_closed)):
        return None
    return low, high, low_closed, high_closed


def _decide_zero(atom, *, nonpositive):
    # A source's unspecified +/- is not a CI. An approximate point does not
    # establish an exact zero or a hard inequality around that point.
    if 'qualifier' in atom or 'uncertainty' in atom:
        return 'unknown'
    low, high, low_closed, high_closed = _interval(atom)
    if nonpositive:
        if high is not None and high <= 0:
            return 'met'
        if low is not None and (low > 0 or low == 0 and not low_closed):
            return 'not_met'
    else:
        if low == high == 0:
            return 'met'
        if ((low is not None and (low > 0 or low == 0 and not low_closed))
                or (high is not None and (high < 0 or high == 0 and not high_closed))):
            return 'not_met'
    return 'unknown'


def _native_test(test, measurements, metrics):
    facts = [row['fact'] for row in measurements if row['fact']['metric_id'] in test['metric_ids']]
    if {row['metric_id'] for row in facts} != set(test['metric_ids']):
        return 'unknown'
    if any(_measurement_interval(fact, metrics) is None for fact in facts):
        return 'conflicted'
    operation = test['operation']
    if operation == 'all_metrics_available':
        return 'met'
    if operation == 'same_method':
        if any('comparison_context' not in fact for fact in facts):
            return 'unknown'
        known = {canonical(fact['comparison_context']) for fact in facts}
        return 'met' if len(known) == 1 else 'not_met'
    states = [_decide_zero(fact['native_value'], nonpositive=operation == 'all_nonpositive')
              for fact in facts]
    return 'not_met' if 'not_met' in states else ('unknown' if 'unknown' in states else 'met')


def _merge_experiment(entry, units):
    metric_definitions = {row['metric_id']: row for row in entry['native_measurements']}
    measurements, measurement_conflicts = {}, set()
    for unit in units:
        for row in unit['measurements']:
            key = row['measurement_id'], row['fact']['metric_id']
            existing = measurements.get(key)
            # Custody may differ between a paper and a dataset representation.
            # The original measurement's value, unit and biological objects may
            # not be averaged or silently selected when they disagree.
            semantic = {name: row['fact'][name] for name in
                        ('native_value', 'declared_native_unit', 'direction',
                         'subjects', 'source_subjects')}
            if 'comparison_context' in row['fact']:
                semantic['comparison_context'] = row['fact']['comparison_context']
            if existing is None:
                measurements[key] = {**_copy(row), 'representations': [], '_semantic': semantic}
                existing = measurements[key]
            elif existing['_semantic'] != semantic:
                measurement_conflicts.add(key)
            existing['representations'].append({
                'representation_id': unit['representation_id'], 'origin': unit['origin'],
                'fact': _copy(row['fact'])})
    outcomes, grades, criterion_conflicts, derivations = {}, {}, [], {}
    for definition in entry['judgment_criteria']:
        name = definition['criterion_id']
        supplied = {row['outcome'] for unit in units for row in unit['judgment']['criteria']
                    if row['criterion_id'] == name} - {'unknown'}
        state = next(iter(supplied)) if len(supplied) == 1 else 'unknown'
        if len(supplied) > 1:
            state = 'conflicted'
        test = definition['deterministic_test']
        if test is not None:
            relevant_conflicts = any(key[1] in test['metric_ids'] for key in measurement_conflicts)
            derived = ('conflicted' if relevant_conflicts else
                       _native_test(test, list(measurements.values()), metric_definitions))
            derivations[name] = {'test': _copy(test), 'native_outcome': derived,
                                 'reported_outcomes': sorted(supplied)}
            if derived == 'conflicted' or (state != 'unknown' and derived not in ('unknown', state)):
                state = 'conflicted'
            elif state == 'unknown':
                state = derived
            # An exact numeric test that cannot decide does not become true
            # through a model's unsupported numerical judgment.
            elif derived == 'unknown':
                state = 'unknown'
        outcomes[name] = state
        if state == 'conflicted':
            criterion_conflicts.append(name)
    for definition in entry['qualitative_grading']:
        name = definition['criterion_id']
        supplied = {row['grade'] for unit in units for row in unit['judgment']['qualitative_grades']
                    if row['criterion_id'] == name} - {'unknown'}
        grades[name] = (next(iter(supplied)) if len(supplied) == 1 else
                        ('conflicted' if supplied else 'unknown'))
    return (list(measurements.values()), measurement_conflicts, outcomes, grades,
            criterion_conflicts, derivations)


def _base(route, *, reason=None, status='unavailable', interval=None, measurements=()):
    result = {'route_id': route['route_id'], 'operation': route['operation'],
              'polarity': route['polarity'], 'score_unit': route['score_unit'],
              'direction': route['direction'], 'interpretation': route['interpretation'],
              'status': status, 'reason': reason, 'score': None, 'score_bounds': None,
              'measurements': [{key: _copy(value) for key, value in row.items() if key != '_semantic'}
                               for row in measurements]}
    if interval is not None:
        result['score_bounds'] = _bounds(interval)
        if interval[0] is not None and interval[0] == interval[1]:
            result['score'] = interval[0]
    return result


def _score_native(route, measurements, conflicts, metrics):
    relevant = [row for row in measurements if row['fact']['metric_id'] in route['metric_ids']]
    if any((row['measurement_id'], row['fact']['metric_id']) in conflicts for row in relevant):
        return [_base(route, status='conflicted', reason='conflicting_native_representations',
                      measurements=relevant)]
    if {row['fact']['metric_id'] for row in relevant} != set(route['metric_ids']):
        return [_base(route, reason='native_measurement_missing', measurements=relevant)]
    if any(row['fact']['declared_native_unit'] is None for row in relevant):
        return [_base(route, reason='native_unit_unresolved', measurements=relevant)]
    if any(_measurement_interval(row['fact'], metrics) is None for row in relevant):
        return [_base(route, reason='native_value_outside_declared_range', measurements=relevant)]
    if route['operation'] == 'ratio':
        if len(relevant) != 2:
            return [_base(route, reason='ambiguous_native_operands', measurements=relevant)]
        numerator, denominator = [next(row for row in relevant if row['fact']['metric_id'] == metric)
                                  for metric in route['metric_ids']]
        if numerator['fact']['declared_native_unit'] != denominator['fact']['declared_native_unit']:
            return [_base(route, reason='ratio_operand_units_differ', measurements=relevant)]
        n, d = numerator['fact']['native_value'], denominator['fact']['native_value']
        low_n, high_n, nc_low, nc_high = _measurement_interval(numerator['fact'], metrics)
        low_d, high_d, dc_low, dc_high = _measurement_interval(denominator['fact'], metrics)
        # These are subset-count fractions k/n, not arbitrary divisions of
        # activities or affinities. No numeric normalization is inferred.
        if (low_n is None or low_n < 0 or low_d is None or low_d < 0
                or low_d == 0 and dc_low or high_d == 0):
            return [_base(route, reason='ratio_requires_nonnegative_numerator_positive_denominator',
                          measurements=relevant)]
        if high_d is not None and (low_n > high_d or low_n == high_d and not (nc_low and dc_high)):
            return [_base(route, reason='ratio_numerator_exceeds_denominator', measurements=relevant)]
        low = 0 if high_d is None else low_n / high_d
        high = None if high_n is None or low_d == 0 else high_n / low_d
        if high is None or high > 1:
            high = 1
            nc_high, dc_low = True, True
        interval = (low, high, nc_low and dc_high if high_d is not None else False,
                    nc_high and dc_low if high is not None else False)
        if all('bound' not in atom for atom in (n, d)):
            if n['value'] > d['value']:
                return [_base(route, reason='ratio_numerator_exceeds_denominator', measurements=relevant)]
            interval = (n['value']/d['value'], n['value']/d['value'], True, True)
        elif low_n == high_n == 0:
            interval = (0, 0, True, True)
        status = 'scored' if interval[0] == interval[1] else 'bounded'
        return [_base(route, status=status, interval=interval, measurements=relevant)]
    results = []
    for measurement in relevant:
        atom = measurement['fact']['native_value']
        interval = _measurement_interval(measurement['fact'], metrics)
        if route['operation'] == 'neg_log10':
            # A displayed zero commonly reflects underflow. It has no finite
            # log score without an actual source-reported positive threshold.
            if atom['value'] <= 0:
                results.append(_base(route, reason='zero_without_positive_reported_threshold',
                                     measurements=[measurement])); continue
            low, high, low_closed, high_closed = interval
            interval = ((-math.log10(high) if high is not None else None),
                        (-math.log10(low) if low is not None and low > 0 else None),
                        high_closed if high is not None else False,
                        low_closed if low is not None and low > 0 else False)
        status = 'scored' if interval[0] == interval[1] else 'bounded'
        results.append(_base(route, status=status, interval=interval, measurements=[measurement]))
    return results


def _withdrawal_reason(route, qualitative_definitions):
    if route['operation'] == 'ordinal':
        return 'categorical_scoring_route_withdrawn'
    if route['operation'] == 'grade':
        definition = qualitative_definitions[route['grade_criterion']]
        if definition['kind'] != 'hgt_environment_explanation':
            return 'categorical_scoring_route_withdrawn'
    return None


def _score_route(route, measurements, conflicts, outcomes, grades, metrics,
                 qualitative_definitions):
    withdrawal = _withdrawal_reason(route, qualitative_definitions)
    if withdrawal is not None:
        # Missing or satisfied criteria cannot revive a rejected point schedule.
        # In particular, an old zero base band is not a measured zero component.
        return [_base(route, reason=withdrawal)]
    eligibility = [outcomes[name] for name in route['eligible_when']]
    if 'conflicted' in eligibility:
        return [_base(route, status='conflicted', reason='eligibility_conflicted')]
    if 'not_met' in eligibility:
        return [_base(route, status='ineligible', reason='eligibility_not_met')]
    if 'unknown' in eligibility:
        return [_base(route, reason='eligibility_unknown')]
    operation = route['operation']
    if operation in ('identity', 'neg_log10', 'ratio'):
        return _score_native(route, measurements, conflicts, metrics)
    if operation == 'grade':
        grade = grades[route['grade_criterion']]
        if grade == 'conflicted':
            return [_base(route, status='conflicted', reason='grade_conflicted')]
        if grade == 'unknown':
            values = route['grade_scores'].values()
            return [_base(route, status='partial', reason='grade_unknown',
                          interval=(min(values), max(values), True, True))]
        value = route['grade_scores'][grade]
        return [_base(route, status='scored', interval=(value, value, True, True))]
    raise ValueError('evidence_axis_scoring_route_unimplemented')


def score_axis(entry, evidence_units, *, resolve_witness=None):
    """Evaluate retained native routes and explicitly identify withdrawn recipes.

    ``score`` is null for an interval or unavailable information. Ineligibility
    and missing evidence are not zero-strength observations. Duplicate original
    experiments are returned once, never summed. Criteria/facts which disagree
    are reported as conflicts; other independent routes remain usable.
    """
    entry = validate_evidence_axis_entry(entry)
    if 'scoring_rubric' not in entry:
        raise ValueError('evidence_axis_scoring_rubric_unbound')
    if not isinstance(evidence_units, (list, tuple)):
        raise ValueError('evidence_axis_scoring_inputs_required')
    groups, representation_ids = {}, set()
    for unit in evidence_units:
        unit = validate_evidence_unit(entry, unit, resolve_witness=resolve_witness)
        if unit['representation_id'] in representation_ids:
            raise ValueError('evidence_axis_representation_duplicate')
        representation_ids.add(unit['representation_id'])
        groups.setdefault(unit['experiment_id'], []).append(unit)
    experiments = []
    metrics = {row['metric_id']: row for row in entry['native_measurements']}
    qualitative_definitions = {row['criterion_id']: row for row in entry['qualitative_grading']}
    withdrawn = [{'route_id': route['route_id'], 'reason': reason}
                 for route in entry['scoring_rubric']['routes']
                 if (reason := _withdrawal_reason(route, qualitative_definitions)) is not None]
    for experiment_id, units in groups.items():
        (measurements, conflicts, outcomes, grades, criterion_conflicts,
         derivations) = _merge_experiment(entry, units)
        route_results = []
        for route in entry['scoring_rubric']['routes']:
            route_results.extend(_score_route(route, measurements, conflicts, outcomes, grades,
                                              metrics, qualitative_definitions))
        experiments.append({'experiment_id': experiment_id,
            'representations': _copy(units), 'criterion_outcomes': outcomes,
            'qualitative_grades': grades, 'criterion_conflicts': criterion_conflicts,
            'criterion_derivations': derivations,
            'routes': route_results})
    return {'version': SCORING_VERSION, 'status': 'proposed', 'axis_id': entry['id'],
            'withdrawn_routes': withdrawn,
            'experiment_count': len(experiments), 'representation_count': len(representation_ids),
            'experiments': experiments, 'annotation_aggregate': None,
            'annotation_aggregate_status': 'not_defined_by_per_axis_rubric',
            'witness_validation': ('resolved' if resolve_witness is not None else 'caller_owned')}


__all__ = ['evidence_unit_schema', 'validate_evidence_unit', 'score_axis']
