"""Evidence-axis definitions and closed judgment contracts.

Native numbers are host facts. An episode judges only the declared criteria and
cites actual witnesses. Validation keeps historical draft records readable; it
does not authorize their numeric recipes. The evaluator separately withdraws
rejected categorical routes. These contracts do not choose annotation-wide
aggregation, applicability weights, model calls, actions or stopping rules.
"""
from __future__ import annotations

from copy import deepcopy
import json

from jsonschema import Draft202012Validator
from method_loop.durable import canonical

from .domain import METRIC_NAMES, OBSERVATION_KINDS


VERSION = 'evidence_axis_entry_v1'
SLOT = 'evidence_axis'
TEXT = {'type': 'string', 'pattern': r'\S'}
CODE = {'type': 'string', 'pattern': r'^[a-z][a-z0-9_]*$'}
WITNESS = {'type': 'string', 'format': 'reference'}


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}


def rows(items, *, minimum=0):
    return {'type': 'array', 'items': items, 'minItems': minimum}


def texts(*, minimum=0):
    return {**rows(TEXT, minimum=minimum), 'uniqueItems': True}


_SOURCE = obj({key: TEXT for key in
    ('case_group', 'case_id', 'source_url', 'source_locator', 'observation', 'limit')})
_BINDING = obj({
    'kind': {'enum': ['recorded_measurement', 'retained_native_field', 'unbound']},
    'measurement_name': {'enum': [None, *METRIC_NAMES]},
    'json_pointer': {'type': ['string', 'null'], 'pattern': r'^(?:$|/(?:[^~]|~[01])*)$'},
})
_MEASUREMENT = obj({
    'metric_id': CODE,
    'name': TEXT,
    'native_field': {'type': ['string', 'null'], 'pattern': r'\S'},
    'observation_kinds': {**rows({'enum': OBSERVATION_KINDS}, minimum=1), 'uniqueItems': True},
    'units': texts(minimum=1),
    'direction': {'enum': ['higher', 'lower', 'target_dependent', 'not_ordered']},
    'method_requirements': texts(minimum=1),
    'comparison_limits': texts(minimum=1),
    'binding': _BINDING,
})
_MEASUREMENT['properties']['valid_range'] = obj({
    'minimum': {'type': ['number', 'null']},
    'maximum': {'type': ['number', 'null']},
})
_TEST = {'anyOf': [{'type': 'null'}, obj({
    'operation': {'enum': ['all_metrics_available', 'same_method', 'all_zero', 'all_nonpositive']},
    'metric_ids': {**rows(CODE, minimum=1), 'uniqueItems': True},
})]}
_CRITERION = obj({
    'criterion_id': CODE,
    'question': TEXT,
    'required_metric_ids': {**rows(CODE), 'uniqueItems': True},
    'required_evidence': {**rows(CODE, minimum=1), 'uniqueItems': True},
    'outcomes': obj({key: TEXT for key in ('met', 'not_met', 'unknown')}),
    'deterministic_test': _TEST,
})
_QUALITATIVE = obj({
    'criterion_id': CODE,
    'kind': {'enum': ['hgt_environment_explanation', 'organism_function_plausibility',
                     'experimental_interpretation_without_numeric_measure']},
    'reason_no_native_metric': TEXT,
    'ordered_levels': rows(obj({'code': CODE, 'meaning': TEXT}), minimum=2),
})
_CHAIN_FIELDS = ('source_subject', 'source_property', 'correspondence',
                 'target_hypothesis', 'limitations')
SCORING_VERSION = 'evidence_axis_scoring_v1'
_SCORING_ROUTE = obj({
    'route_id': CODE,
    'operation': {'enum': ['identity', 'neg_log10', 'ratio', 'grade', 'ordinal']},
    'metric_ids': {**rows(CODE), 'uniqueItems': True},
    'eligible_when': {**rows(CODE), 'uniqueItems': True},
    'score_unit': TEXT,
    'direction': {'enum': ['higher', 'lower', 'not_ordered']},
    'polarity': {'enum': ['supporting', 'opposing', 'non_discriminating']},
    'interpretation': TEXT,
    'grade_criterion': {'anyOf': [CODE, {'type': 'null'}]},
    'grade_scores': {'type': 'object', 'propertyNames': CODE,
                     'additionalProperties': {'type': 'number'}},
    'bands': rows(obj({'score': {'type': 'number'},
                      'requires': {**rows(CODE), 'uniqueItems': True}})),
})
_SCORING = obj({
    'version': {'const': SCORING_VERSION},
    'status': {'const': 'proposed'},
    'routes': rows(_SCORING_ROUTE, minimum=1),
})
_ENTRY = obj({
    'entry_version': {'const': VERSION},
    'id': {'type': 'string', 'pattern': r'^A[0-9]+$'},
    'slot': {'const': SLOT},
    'name': TEXT,
    'description': TEXT,
    'native_measurements': rows(_MEASUREMENT),
    'judgment_criteria': rows(_CRITERION, minimum=1),
    'qualitative_grading': rows(_QUALITATIVE),
    'transfer_chain': obj({name: TEXT for name in _CHAIN_FIELDS}),
    'evidence': rows(_SOURCE, minimum=1),
})
# Older immutable definitions remain readable without a scoring proposal.
_ENTRY['properties']['scoring_rubric'] = _SCORING


def entry_schema():
    return deepcopy(_ENTRY)


def _detach(value):
    return json.loads(canonical(value))


def validate_evidence_axis_entry(value):
    value = _detach(value)
    if not Draft202012Validator(_ENTRY).is_valid(value):
        raise ValueError('evidence_axis_entry_invalid')
    metrics = {row['metric_id']: row for row in value['native_measurements']}
    criteria = {row['criterion_id']: row for row in value['judgment_criteria']}
    grades = {row['criterion_id']: row for row in value['qualitative_grading']}
    if (len(metrics) != len(value['native_measurements'])
            or len(criteria) != len(value['judgment_criteria'])
            or len(grades) != len(value['qualitative_grading'])):
        raise ValueError('evidence_axis_duplicate_identity')
    for row in metrics.values():
        if 'valid_range' in row:
            import math
            lower, upper = (row['valid_range'][key] for key in ('minimum', 'maximum'))
            if (any(isinstance(number, bool) or not math.isfinite(number)
                    for number in (lower, upper) if number is not None)
                    or lower is not None and upper is not None and lower > upper):
                raise ValueError('evidence_axis_native_range_invalid')
        binding = row['binding']
        if binding['kind'] == 'recorded_measurement':
            if binding['measurement_name'] is None or binding['json_pointer'] is not None:
                raise ValueError('evidence_axis_measurement_binding_invalid')
        elif binding['kind'] == 'retained_native_field':
            if binding['measurement_name'] is not None or row['native_field'] is None:
                raise ValueError('evidence_axis_native_binding_invalid')
        elif binding['measurement_name'] is not None or binding['json_pointer'] is not None:
            raise ValueError('evidence_axis_unbound_metric_has_no_extractor')
    for row in criteria.values():
        if not set(row['required_metric_ids']) <= metrics.keys():
            raise ValueError('evidence_axis_criterion_metric_unknown')
        test = row['deterministic_test']
        if test is not None and not set(test['metric_ids']) <= metrics.keys():
            raise ValueError('evidence_axis_test_metric_unknown')
    for row in grades.values():
        if row['criterion_id'] not in criteria:
            raise ValueError('evidence_axis_grade_criterion_unknown')
        codes = [level['code'] for level in row['ordered_levels']]
        if len(codes) != len(set(codes)) or 'unknown' in codes:
            raise ValueError('evidence_axis_grade_levels_invalid')
    if 'scoring_rubric' in value:
        validate_scoring_rubric(value['scoring_rubric'], metrics=metrics,
                                criteria=criteria, grades=grades)
    return value


def scoring_rubric_schema():
    return deepcopy(_SCORING)


def validate_scoring_rubric(value, *, metrics, criteria, grades):
    """Validate retained draft structure, including withdrawn historical rules.

    Readability is separate from execution: accepting an old ordinal/grade
    descriptor here does not authorize converting its categories into numbers.
    """
    import math
    if not Draft202012Validator(_SCORING).is_valid(value):
        raise ValueError('evidence_axis_scoring_rubric_invalid')
    routes = value['routes']
    if len({row['route_id'] for row in routes}) != len(routes):
        raise ValueError('evidence_axis_scoring_route_duplicate')
    for route in routes:
        operation = route['operation']
        count = {'identity': 1, 'neg_log10': 1, 'ratio': 2,
                 'grade': 0, 'ordinal': 0}[operation]
        if len(route['metric_ids']) != count or not set(route['metric_ids']) <= metrics.keys():
            raise ValueError('evidence_axis_scoring_metrics_invalid')
        if not set(route['eligible_when']) <= criteria.keys():
            raise ValueError('evidence_axis_scoring_eligibility_unknown')
        if operation == 'grade':
            criterion = route['grade_criterion']
            if criterion not in grades:
                raise ValueError('evidence_axis_scoring_grade_unknown')
            codes = {row['code'] for row in grades[criterion]['ordered_levels']}
            if set(route['grade_scores']) != codes:
                raise ValueError('evidence_axis_scoring_grade_coverage_invalid')
        elif route['grade_criterion'] is not None or route['grade_scores']:
            raise ValueError('evidence_axis_scoring_unexpected_grade')
        if operation == 'ordinal':
            bands = route['bands']
            if not bands or bands[0]['requires']:
                raise ValueError('evidence_axis_scoring_base_band_required')
            previous, previous_score = set(), -math.inf
            for band in bands:
                required = set(band['requires'])
                if (not required <= criteria.keys() or not previous <= required
                        or band['score'] <= previous_score):
                    raise ValueError('evidence_axis_scoring_bands_invalid')
                previous, previous_score = required, band['score']
        elif route['bands']:
            raise ValueError('evidence_axis_scoring_unexpected_bands')
        scores = [*route['grade_scores'].values(), *(band['score'] for band in route['bands'])]
        if any(isinstance(score, bool) or not math.isfinite(score) for score in scores):
            raise ValueError('evidence_axis_scoring_nonfinite_score')
    return _detach(value)


def observation_kinds(entry):
    entry = validate_evidence_axis_entry(entry)
    return sorted({kind for metric in entry['native_measurements']
                   for kind in metric['observation_kinds']})


def judgment_schema(entry):
    """Numbers are deliberately absent from the model's judgment fields."""
    entry = validate_evidence_axis_entry(entry)
    criteria = []
    for row in entry['judgment_criteria']:
        missing = sorted(set(row['required_metric_ids']) | set(row['required_evidence']))
        criteria.append(obj({
            'criterion_id': {'const': row['criterion_id']},
            'outcome': {'enum': ['met', 'not_met', 'unknown']},
            'witnesses': {**rows(WITNESS), 'uniqueItems': True},
            'missing_inputs': {**rows({'enum': missing}), 'uniqueItems': True},
        }))
    grades = []
    for row in entry['qualitative_grading']:
        grades.append(obj({
            'criterion_id': {'const': row['criterion_id']},
            'grade': {'enum': [*(level['code'] for level in row['ordered_levels']), 'unknown']},
            'witnesses': {**rows(WITNESS), 'uniqueItems': True},
        }))
    return obj({
        'criteria': rows({'anyOf': criteria}),
        'qualitative_grades': (rows({'anyOf': grades}) if grades else
            {'type': 'array', 'items': {'type': 'null'}, 'maxItems': 0}),
        'evidence_chain': obj({name: {**rows(WITNESS), 'uniqueItems': True}
                               for name in _CHAIN_FIELDS}),
    })


def validate_axis_judgment(entry, value, *, resolve_witness=None):
    entry, value = validate_evidence_axis_entry(entry), _detach(value)
    if not Draft202012Validator(judgment_schema(entry)).is_valid(value):
        raise ValueError('evidence_axis_judgment_invalid')
    for field, definitions in (('criteria', entry['judgment_criteria']),
                               ('qualitative_grades', entry['qualitative_grading'])):
        ids = [row['criterion_id'] for row in value[field]]
        if len(ids) != len(set(ids)) or set(ids) != {row['criterion_id'] for row in definitions}:
            raise ValueError('evidence_axis_judgment_criterion_coverage_invalid')
    witnesses = [witness for values in value['evidence_chain'].values() for witness in values]
    for row in value['criteria']:
        if row['outcome'] == 'unknown':
            if not row['missing_inputs']:
                raise ValueError('evidence_axis_unknown_requires_missing_inputs')
        elif row['missing_inputs'] or not row['witnesses']:
            raise ValueError('evidence_axis_decided_criterion_requires_witnesses')
        witnesses.extend(row['witnesses'])
    for row in value['qualitative_grades']:
        if row['grade'] != 'unknown' and not row['witnesses']:
            raise ValueError('evidence_axis_grade_requires_witnesses')
        witnesses.extend(row['witnesses'])
    if resolve_witness is not None and any(not resolve_witness(ref) for ref in witnesses):
        raise ValueError('evidence_axis_witness_unavailable')
    return value


def native_metric_facts(entry, store, *, observation_refs, received_record_refs):
    """Copy actual received native numbers; never manufacture or rank values.

    The current implementation binds existing typed observation measurements.
    A declared retained-field/unbound quantity remains unavailable until its
    actual native extractor is bound; this function does not guess JSON paths,
    relabel another metric or run a provider. Source metadata retains its
    recorded meaning rather than claiming a database or software release.
    """
    entry = validate_evidence_axis_entry(entry)
    if (not isinstance(observation_refs, (list, tuple))
            or not isinstance(received_record_refs, (list, tuple, set, frozenset))
            or any(not isinstance(ref, str) for ref in (*observation_refs, *received_record_refs))):
        raise ValueError('evidence_axis_received_inputs_required')
    received = set(received_record_refs)
    if not set(observation_refs) <= received:
        raise ValueError('evidence_axis_observation_not_received')
    observations = []
    for reference in dict.fromkeys(observation_refs):
        row = store.get(reference)
        if row.get('record_type') != 'observation':
            raise ValueError('evidence_axis_observation_required')
        observations.append(row)
    facts, unavailable = [], []
    for metric in entry['native_measurements']:
        binding = metric['binding']
        if binding['kind'] != 'recorded_measurement':
            unavailable.append({'metric_id': metric['metric_id'],
                'reason': 'native_extractor_unbound'})
            continue
        found = False
        for observation in observations:
            if observation['kind'] not in metric['observation_kinds']:
                continue
            for index, measurement in enumerate(observation['measurements']):
                if (measurement['name'] != binding['measurement_name']
                        or measurement['value'].get('type') != 'number'):
                    continue
                source = store.get(observation['source_ref'])
                if source.get('record_type') != 'source':
                    raise ValueError('evidence_axis_measurement_source_required')
                native = _detach(measurement['value'])
                facts.append({'metric_id': metric['metric_id'],
                    'observation': observation['id'], 'measurement_index': index,
                    'native_field': measurement['name'], 'native_value': native,
                    'declared_native_unit': (metric['units'][0] if len(metric['units']) == 1 else None),
                    'direction': metric['direction'], 'source': source['id'],
                    'source_subjects': _detach(observation['source_subject_refs']),
                    'subjects': _detach(observation['subject_refs']),
                    'dependencies': _detach(observation['dependencies']),
                    'method': {'provider': source['provider'], 'recorded_source_version': source['version'],
                               'request_record': source['request_ref']}})
                found = True
        if not found:
            unavailable.append({'metric_id': metric['metric_id'],
                'reason': 'native_measurement_not_present'})
    return {'native_facts': facts, 'unavailable': unavailable}


__all__ = ['VERSION', 'SLOT', 'entry_schema', 'validate_evidence_axis_entry',
           'observation_kinds', 'judgment_schema', 'validate_axis_judgment', 'native_metric_facts',
           'SCORING_VERSION', 'scoring_rubric_schema', 'validate_scoring_rubric']
