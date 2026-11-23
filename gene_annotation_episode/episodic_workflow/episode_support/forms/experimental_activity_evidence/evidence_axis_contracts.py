"""Evidence-axis definitions and closed judgment contracts.

Native numbers are host facts. An episode judges only the declared criteria and
cites actual witnesses. The evaluator withdraws rejected categorical routes. These contracts do not choose annotation-wide
aggregation, applicability weights, model calls, actions or stopping rules.
"""
from __future__ import annotations

import json

from jsonschema import Draft202012Validator
from method_loop.jsonvalue import canonical

from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import METRIC_NAMES, OBSERVATION_KINDS


VERSION = 'evidence_axis_entry'
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
SCORING_VERSION = 'evidence_axis_scoring'
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
_ENTRY['properties']['scoring_rubric'] = _SCORING


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


def validate_scoring_rubric(value, *, metrics, criteria, grades):
    """Validate the structure of a scoring rubric."""
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


__all__ = ['VERSION', 'SLOT', 'validate_evidence_axis_entry', 'SCORING_VERSION', 'validate_scoring_rubric']
