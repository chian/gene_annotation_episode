"""Execution forecasts for planning, separate from credit and continuation.

Only typed execution statistics and an optional measured job sample enter here.
No scientific Store, episode score/history, controller or scheduler is available.
"""
from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping
from dataclasses import asdict
import hashlib
import json
import math
import re

from .run_statistics import (CONDITIONS, VERSION as STATISTICS_VERSION, ExecutionClass,
    REPORTED_RESULT_VERSION, REPORTED_RESULT_PHASE, REPORTED_RESULT_MEASURE, REPORTED_RESULT_UNIT,
    _timestamp)
from .communication import REFERENCE_FORMATS, ReportBoundaryError


VERSION = 'resource_tool_duration_estimator_v2'
METHOD = 'exact_class_current_condition_successful_duration_mean'
REPORTED_VERSION = 'resource_tool_duration_estimator_v3'
REPORTED_METHOD = 'exact_exposed_configuration_current_condition_reported_duration_mean_v1'
REPORTED_COMPATIBILITY = 'same_exposed_technical_configuration_unknown_remote_revision'
OUTCOMES = ('succeeded', 'failed', 'cancelled', 'resource_limit', 'unknown')
FORECAST_REFERENCE_FIELDS = {
    'job_execution_estimate': 'estimate_ref',
    'execution_class': 'execution_class_ref',
    'execution_expectation': 'expectation_ref',
    'execution_proposal': 'proposal_ref',
}


def _object(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


def _ref(namespace, nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string',
            'format': 'reference', 'x-reference-namespace': namespace}


ESTIMATE_SCHEMA = _object({
    'estimate_ref': _ref('job_execution_estimate'),
    'job_ref': _ref('homology_job', True),
    'proposal_ref': _ref('execution_proposal', True),
    'execution_class_ref': _ref('execution_class', True),
    'expectation_ref': _ref('execution_expectation', True),
    'current_condition_state': {'type': ['string', 'null'], 'enum': [None, *sorted(CONDITIONS)]},
    'sample_ref': _ref('job_sample', True),
    'status': {'type': 'string', 'enum': ['available', 'no_matching_history', 'history_unavailable', 'invalid_statistics']},
    'method': {'type': 'string', 'enum': [METHOD]},
    'phase': {'type': ['string', 'null'], 'enum': [None, 'reference_acquisition',
        'protein_homology_search', 'pairwise_sequence_alignment', 'spreadsheet_selection']},
    'cpu_threads': {'type': ['integer', 'null'], 'minimum': 1},
    'memory_limit_bytes': {'type': ['integer', 'null'], 'minimum': 1},
    'scratch_limit_bytes': {'type': ['integer', 'null'], 'minimum': 1},
    'successful_duration_samples': {'type': 'integer', 'minimum': 0},
    'outcome_support': {'type': ['array', 'null'], 'items': _object({
        'outcome': {'type': 'string', 'enum': list(OUTCOMES)},
        'attempt_count': {'type': 'integer', 'minimum': 0},
        'complete_duration_count': {'type': 'integer', 'minimum': 0},
        'lower_bound_count': {'type': 'integer', 'minimum': 0},
        'unmeasured_count': {'type': 'integer', 'minimum': 0},
        'max_lower_bound_seconds': {'type': ['number', 'null'], 'minimum': 0},
    })},
    'expected_total_seconds': {'type': ['number', 'null'], 'minimum': 0},
    'observed_min_seconds': {'type': ['number', 'null'], 'minimum': 0},
    'observed_max_seconds': {'type': ['number', 'null'], 'minimum': 0},
    'forecast_duration_measure': {'type': ['string', 'null'],
        'enum': [None, 'protected_service_wall_seconds', 'systemd_service_wall_seconds']},
    'elapsed_seconds': {'type': ['number', 'null'], 'minimum': 0},
    'timing_relation': {'type': 'string', 'enum': ['unknown', 'not_exceeding_observed_maximum', 'exceeds_observed_maximum', 'measurement_mismatch', 'execution_class_not_assigned']},
})


API_REPORT_ESTIMATE_SCHEMA = deepcopy(ESTIMATE_SCHEMA)
API_REPORT_ESTIMATE_SCHEMA['properties'].update({
    'method': {'type': 'string', 'enum': [REPORTED_METHOD]},
    'phase': {'type': ['string', 'null'], 'enum': [None, REPORTED_RESULT_PHASE]},
    'job_ref': {'type': 'null'}, 'sample_ref': {'type': 'null'},
    'elapsed_seconds': {'type': 'null'}, 'outcome_support': {'type': 'null'},
    'cpu_threads': {'type': 'null'}, 'memory_limit_bytes': {'type': 'null'},
    'scratch_limit_bytes': {'type': 'null'},
    'timing_relation': {'type': 'string', 'enum': ['unknown']},
    'forecast_duration_measure': {'type': ['string', 'null'], 'enum': [None, REPORTED_RESULT_MEASURE]},
    'observation_unit': {'type': 'string', 'enum': [REPORTED_RESULT_UNIT]},
    'reported_result_support': {'type': ['object', 'null'], **{
        key: value for key, value in _object({
            'reported_result_count': {'type': 'integer', 'minimum': 0}}).items() if key != 'type'}},
    'compatibility': {'type': 'string', 'enum': [REPORTED_COMPATIBILITY]},
})
API_REPORT_ESTIMATE_SCHEMA['required'] = list(API_REPORT_ESTIMATE_SCHEMA['properties'])


def report_source():
    return {'type': 'array', 'meaning': ('Frozen resource/tool execution forecasts from recorded statistics and selected samples. '
        'Expected total duration is conditional on successful completion of the exact class under the current recorded condition. '
        'Outcome support describes that same condition; null support means unknown, and zero counts mean observed empty history. '
        'Observed minimum/maximum are historical ranges, not calibrated prediction intervals. '
        'Local service wall time does not separately measure queue wait or program runtime. '
        'CPU is the configured allocation; memory/scratch fields are limits, not measured consumption. '
        'No credit, action choice, remaining duration or stop/schedule decision is derived here.'),
        'report_schema': {'type': 'array', 'items': deepcopy(ESTIMATE_SCHEMA), 'x-source': 'resource_tool_estimates'}}


def reported_report_source():
    return {'type': 'array', 'meaning': (
        'Frozen provider-reported search-duration forecasts for the exact exposed technical configuration '
        'and original current condition. Remote revision, allocation, corpus release and corpus sizes are unknown. '
        'Support counts logical provider-job reported results; internal physical attempts, retries and reliability '
        'are unknown. The named provider interval is not queue wait, HTTP time or job turnaround. '
        'Historical minimum/maximum are not calibrated prediction intervals. No action, credit or waiting rule is derived.'),
        'report_schema': {'type': 'array', 'items': deepcopy(API_REPORT_ESTIMATE_SCHEMA),
            'x-source': 'api_reported_execution_forecasts'}}


def _seconds(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('finite_nonnegative_duration_required')
    return float(value)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _support(data, scope):
    """Validate descriptive groups, then project only the current condition."""
    if (data['version'] != STATISTICS_VERSION or data['class_ref'] != scope.ref
            or data['execution_class'] != asdict(scope)
            or data['expectation_method'] != 'empirical_complete_duration_mean_by_condition_and_outcome_v1'):
        raise ValueError('execution_class_identity_mismatch')
    condition = data['current_condition']
    if condition['state'] not in CONDITIONS or condition['resource_id'] != scope.resource_id:
        raise ValueError('invalid_execution_condition')
    if type(data['history_through_sequence']) is not int or data['history_through_sequence'] < 0:
        raise ValueError('invalid_execution_history_sequence')
    if not isinstance(data['statistics'], list):
        raise ValueError('invalid_execution_statistics')
    groups = {}
    counts = ('attempt_count', 'complete_duration_count', 'lower_bound_count', 'unmeasured_count')
    for row in data['statistics']:
        group = (row['condition_state'], row['outcome'])
        if group[0] not in CONDITIONS or group[1] not in OUTCOMES or group in groups:
            raise ValueError('invalid_statistical_group')
        if any(type(row[key]) is not int or row[key] < 0 for key in counts):
            raise ValueError('invalid_duration_count')
        if row['attempt_count'] < 1 or row['attempt_count'] != sum(row[key] for key in counts[1:]):
            raise ValueError('invalid_attempt_count')
        if row['complete_duration_count']:
            low, mean, high = (_seconds(row[key]) for key in ('min_seconds', 'mean_seconds', 'max_seconds'))
            if not low <= mean <= high or row['outcome'] == 'unknown':
                raise ValueError('invalid_duration_summary')
        elif any(row[key] is not None for key in ('min_seconds', 'mean_seconds', 'max_seconds')):
            raise ValueError('unmeasured_summary_must_be_null')
        if row['lower_bound_count']:
            _seconds(row['max_lower_bound_seconds'])
        elif row['max_lower_bound_seconds'] is not None:
            raise ValueError('unobserved_lower_bound_must_be_null')
        groups[group] = row
    support = []
    for outcome in OUTCOMES:
        row = groups.get((condition['state'], outcome))
        support.append({'outcome': outcome, **{key: row[key] if row else 0 for key in counts},
            'max_lower_bound_seconds': row['max_lower_bound_seconds'] if row else None})
    return condition['state'], support, groups.get((condition['state'], 'succeeded'))


def _reported_support(data, scope):
    fields = {'version', 'class_ref', 'execution_class', 'history_through_sequence',
        'current_condition', 'observation_unit', 'statistics', 'expectation_method'}
    if (type(data) is not dict or set(data) != fields or data['version'] != REPORTED_RESULT_VERSION
            or data['class_ref'] != scope.ref or data['execution_class'] != asdict(scope)
            or data['observation_unit'] != REPORTED_RESULT_UNIT
            or data['expectation_method'] != 'empirical_reported_result_duration_mean_by_condition_v1'):
        raise ValueError('reported_result_class_identity_mismatch')
    condition = data['current_condition']
    if (type(condition) is not dict or set(condition) != {'ref', 'resource_id', 'state', 'reason', 'reported_at'}
            or type(condition['state']) is not str or condition['state'] not in CONDITIONS
            or condition['resource_id'] != scope.resource_id):
        raise ValueError('invalid_execution_condition')
    if condition['ref'] is None:
        if (condition['state'] != 'unspecified' or condition['reason'] is not None
                or condition['reported_at'] is not None):
            raise ValueError('invalid_execution_condition')
    else:
        if (type(condition['ref']) is not str
                or re.fullmatch('execution_condition_[0-9a-f]{64}', condition['ref']) is None
                or type(condition['reason']) is not str
                or condition['reason'] not in {'operator_report', 'outage', 'maintenance', 'recovered'}):
            raise ValueError('invalid_execution_condition')
        _timestamp(condition['reported_at'])
    sequence = data['history_through_sequence']
    if type(sequence) is not int or sequence < 0 or type(data['statistics']) is not list:
        raise ValueError('invalid_execution_history_sequence')
    groups, total = {}, 0
    for row in data['statistics']:
        if (type(row) is not dict or set(row) != {'condition_state', 'reported_result_count',
                'mean_seconds', 'min_seconds', 'max_seconds'}
                or type(row['condition_state']) is not str or row['condition_state'] not in CONDITIONS
                or row['condition_state'] in groups):
            raise ValueError('invalid_reported_result_group')
        count = row['reported_result_count']
        if type(count) is not int or count < 1:
            raise ValueError('invalid_reported_result_count')
        low, mean, high = (_seconds(row[key]) for key in ('min_seconds', 'mean_seconds', 'max_seconds'))
        if not low <= mean <= high or count == 1 and not low == mean == high:
            raise ValueError('invalid_reported_result_summary')
        total += count
        groups[row['condition_state']] = row
    if total > sequence or bool(total) != bool(sequence):
        raise ValueError('invalid_reported_result_history_sequence')
    return condition['state'], groups.get(condition['state'])


class ResourceToolEstimator:
    """A pure, independently bound forecasting component; it has no stop rule."""
    def __init__(self, *, reported_results=False):
        if type(reported_results) is not bool:
            raise ValueError('invalid_reported_result_estimator_configuration')
        self._reported_results = reported_results

    @classmethod
    def with_reported_results(cls):
        return cls(reported_results=True)

    def as_record(self):
        if self._reported_results:
            return {'version': REPORTED_VERSION, 'method': METHOD, 'reported_result_method': REPORTED_METHOD}
        return {'version': VERSION, 'method': METHOD}

    @classmethod
    def from_record(cls, record):
        if record == cls().as_record():
            return cls()
        if record == cls.with_reported_results().as_record():
            return cls.with_reported_results()
        raise ValueError('unsupported_resource_tool_estimator')

    def estimate(self, context, *, job_ref, sample=None):
        """Project frozen statistics for an existing assigned job."""
        return self._project(context, job_ref=job_ref, sample=sample, prospective=False)

    def estimate_context(self, context):
        """Project caller-bound scopes before any order or submission exists.

        Proposal identity names the exact execution configuration per row. It
        remains stable as history changes; expectation_ref identifies the frozen
        history actually used. Neither this method nor its inputs require a job.
        """
        if (isinstance(context, dict) and context.get('execution_classes') == []
                and context.get('snapshots') == []):
            return []
        return self._project(context, job_ref=None, sample=None, prospective=True)

    def estimate_reported_context(self, context):
        """Project only explicit logical-result support, never physical attempts."""
        if not self._reported_results:
            raise ValueError('reported_result_estimator_not_enabled')
        if (isinstance(context, dict) and context.get('execution_classes') == []
                and context.get('snapshots') == []):
            return []
        context = context if type(context) is dict else {}
        scopes, snapshots = context.get('execution_classes', []), context.get('snapshots', [])
        invalid = type(scopes) is not list or type(snapshots) is not list
        scopes = scopes if type(scopes) is list else []
        by_class = {}
        try:
            for snapshot in snapshots:
                if type(snapshot) is not dict or set(snapshot) != {'ref', 'data'}:
                    raise ValueError('invalid_execution_snapshot')
                ref = snapshot['data']['class_ref']
                if ref in by_class:
                    raise ValueError('duplicate_execution_snapshot')
                by_class[ref] = snapshot
            declared = {ExecutionClass(**scope).ref for scope in scopes}
            if len(declared) != len(scopes) or set(by_class) - declared:
                raise ValueError('execution_class_identity_mismatch')
        except (KeyError, TypeError, ValueError):
            invalid = True
        records = []
        for declared_scope in scopes or [None]:
            value = {'job_ref': None, 'proposal_ref': None, 'execution_class_ref': None,
                'expectation_ref': None, 'current_condition_state': None, 'outcome_support': None,
                'sample_ref': None, 'status': 'no_matching_history' if context.get('status') == 'available'
                    else 'history_unavailable', 'method': REPORTED_METHOD,
                'phase': None, 'cpu_threads': None, 'memory_limit_bytes': None, 'scratch_limit_bytes': None,
                'successful_duration_samples': 0, 'expected_total_seconds': None,
                'observed_min_seconds': None, 'observed_max_seconds': None,
                'forecast_duration_measure': None, 'elapsed_seconds': None, 'timing_relation': 'unknown',
                'observation_unit': REPORTED_RESULT_UNIT, 'reported_result_support': None,
                'compatibility': REPORTED_COMPATIBILITY}
            try:
                if declared_scope is None:
                    snapshot = None
                else:
                    scope = ExecutionClass(**declared_scope)
                    if scope.phase != REPORTED_RESULT_PHASE:
                        raise ValueError('reported_result_execution_class_required')
                    value.update(execution_class_ref=scope.ref,
                        proposal_ref='execution_proposal_'+_digest(asdict(scope)), phase=scope.phase,
                        forecast_duration_measure=scope.duration_measure)
                    snapshot = by_class.get(scope.ref)
                if invalid or context.get('status') == 'invalid_statistics':
                    raise ValueError('invalid_execution_context')
                if snapshot is not None:
                    expectation_ref = snapshot['ref']
                    if (type(expectation_ref) is not str
                            or re.fullmatch('execution_expectation_[0-9a-f]{64}', expectation_ref) is None
                            or expectation_ref != 'execution_expectation_'+_digest(snapshot['data'])):
                        raise ValueError('execution_snapshot_identity_mismatch')
                    value['expectation_ref'] = expectation_ref
                    condition, row = _reported_support(snapshot['data'], scope)
                    if context.get('status') == 'available':
                        count = row['reported_result_count'] if row else 0
                        value.update(current_condition_state=condition,
                            reported_result_support={'reported_result_count': count},
                            successful_duration_samples=count)
                        if row:
                            value.update(status='available', expected_total_seconds=_seconds(row['mean_seconds']),
                                observed_min_seconds=_seconds(row['min_seconds']),
                                observed_max_seconds=_seconds(row['max_seconds']))
                elif context.get('status') == 'available':
                    raise ValueError('missing_execution_snapshot')
            except (KeyError, TypeError, ValueError, OverflowError):
                value.update(status='invalid_statistics', current_condition_state=None,
                    reported_result_support=None, successful_duration_samples=0, expected_total_seconds=None,
                    observed_min_seconds=None, observed_max_seconds=None)
            value['estimate_ref'] = 'execution_estimate_'+_digest({'version': REPORTED_VERSION, 'estimate': value})[:24]
            records.append(value)
        return records

    def _project(self, context, *, job_ref, sample, prospective):
        if isinstance(context, dict) and isinstance(context.get('execution_classes'), list):
            if any(isinstance(scope, dict) and scope.get('phase') == REPORTED_RESULT_PHASE
                    for scope in context['execution_classes']):
                raise ValueError('native_estimator_requires_native_execution_classes')
        sample_ref = sample.get('sample_ref') if sample else None
        elapsed = sample.get('elapsed_seconds') if sample else None
        if elapsed is not None:
            elapsed = _seconds(elapsed)
        context = context if isinstance(context, dict) else {}
        scopes = context.get('execution_classes', [])
        snapshots = context.get('snapshots', [])
        invalid = not isinstance(scopes, list) or not isinstance(snapshots, list)
        scopes = scopes if isinstance(scopes, list) else []
        by_class = {}
        try:
            for snapshot in snapshots:
                ref = snapshot['data']['class_ref']
                if ref in by_class:
                    raise ValueError('duplicate_execution_snapshot')
                by_class[ref] = snapshot
            declared = {ExecutionClass(**scope).ref for scope in scopes}
            if len(declared) != len(scopes) or set(by_class) - declared:
                raise ValueError('execution_class_identity_mismatch')
        except (KeyError, TypeError, ValueError):
            invalid = True
        assigned_ref = context.get('assigned_execution_class_ref')
        if assigned_ref is None and len(scopes) == 1:
            # An assigned estimate with one explicitly supplied class retains
            # the existing measurement comparison semantics.
            try:
                assigned_ref = ExecutionClass(**scopes[0]).ref
            except (TypeError, ValueError):
                pass
        records = []
        for declared_scope in scopes or [None]:
            value = {'job_ref': job_ref, 'proposal_ref': None, 'execution_class_ref': None,
                'expectation_ref': None, 'current_condition_state': None, 'outcome_support': None,
                'sample_ref': sample_ref,
                'status': 'no_matching_history' if context.get('status') == 'available' else 'history_unavailable', 'method': METHOD,
                'phase': None, 'cpu_threads': None, 'memory_limit_bytes': None, 'scratch_limit_bytes': None,
                'successful_duration_samples': 0, 'expected_total_seconds': None,
                'observed_min_seconds': None, 'observed_max_seconds': None,
                'forecast_duration_measure': None, 'elapsed_seconds': elapsed, 'timing_relation': 'unknown'}
            try:
                if declared_scope is not None:
                    scope = ExecutionClass(**declared_scope)
                    snapshot = by_class.get(scope.ref)
                    value.update(execution_class_ref=scope.ref,
                        proposal_ref='execution_proposal_'+_digest(asdict(scope)) if prospective else None,
                        phase=scope.phase, cpu_threads=scope.cpu_threads,
                        memory_limit_bytes=scope.memory_bytes, scratch_limit_bytes=scope.scratch_bytes,
                        forecast_duration_measure=scope.duration_measure)
                else:
                    snapshot = None
                if invalid or context.get('status') == 'invalid_statistics':
                    raise ValueError('invalid_execution_context')
                if snapshot is not None:
                    expectation_ref = snapshot['ref']
                    if type(expectation_ref) is not str or re.fullmatch('execution_expectation_[0-9a-f]{64}', expectation_ref) is None:
                        raise ValueError('invalid_expectation_reference')
                    value['expectation_ref'] = expectation_ref
                    data = snapshot['data']
                    if expectation_ref != 'execution_expectation_'+_digest(data):
                        raise ValueError('execution_snapshot_identity_mismatch')
                    condition, support, row = _support(data, scope)
                    if context.get('status') == 'available':
                        value.update(current_condition_state=condition, outcome_support=support)
                    if context.get('status') == 'available' and row and row['complete_duration_count']:
                        count = row['complete_duration_count']
                        if type(count) is not int or count < 1:
                            raise ValueError('invalid_duration_count')
                        low, mean, high = (_seconds(row[key]) for key in ('min_seconds', 'mean_seconds', 'max_seconds'))
                        if not low <= mean <= high:
                            raise ValueError('invalid_duration_summary')
                        value.update(status='available', successful_duration_samples=count,
                            expected_total_seconds=mean, observed_min_seconds=low, observed_max_seconds=high)
                        if elapsed is not None:
                            value['timing_relation'] = ('execution_class_not_assigned' if assigned_ref != scope.ref else
                                'measurement_mismatch' if sample.get('duration_measure') != scope.duration_measure
                                else 'exceeds_observed_maximum' if elapsed > high else 'not_exceeding_observed_maximum')
                elif context.get('status') == 'available':
                    raise ValueError('missing_execution_snapshot')
            except (KeyError, TypeError, ValueError, OverflowError):
                value.update(status='invalid_statistics', successful_duration_samples=0, expected_total_seconds=None,
                    observed_min_seconds=None, observed_max_seconds=None, timing_relation='unknown',
                    current_condition_state=None, outcome_support=None)
            value['estimate_ref'] = 'execution_estimate_'+_digest({'version': VERSION, 'estimate': value})[:24]
            records.append(value)
        return records


def recorded_estimate(store, reference, job_ref=None, *, namespace='job_execution_estimate'):
    """Resolve a forecast against the existing authoritative decision journals.

    No new forecast, global read or separate mutable forecast ledger is made.
    """
    field_name = FORECAST_REFERENCE_FIELDS.get(namespace)
    if field_name is None:
        return None
    for table, field, path in (
            ('runtime_actions', 'result', '$.resource_tool_estimates'),
            ('runtime_model_calls', 'request', '$.context.resource_tool_estimates'),
            ('runtime_actions', 'result', '$.api_reported_execution_forecasts'),
            ('runtime_model_calls', 'request', '$.context.api_reported_execution_forecasts')):
        row = store.db.execute(f'''SELECT items.value FROM {table} records
            JOIN json_each(records.{field}, ?) items
            WHERE json_extract(items.value,?)=?
            AND (? IS NULL OR json_extract(items.value,'$.job_ref')=?) LIMIT 1''',
            (path, '$.'+field_name, reference, job_ref, job_ref)).fetchone()
        if row is not None:
            return json.loads(row[0])
    return None


def recorded_forecasts(store, *, run_id, episode_id):
    """Latest completed own action's original forecasts, without refreshing.

    Assigned-job actions can record a sample-based projection after work.
    Other actions retain the forecasts supplied with their selected decision.
    Both come from the same authoritative journals used for replay.
    """
    row = store.db.execute('''SELECT CASE
        WHEN json_type(actions.result,'$.resource_tool_estimates')='array'
        THEN json_extract(actions.result,'$.resource_tool_estimates')
        ELSE json_extract(calls.request,'$.context.resource_tool_estimates') END
        FROM runtime_actions actions LEFT JOIN runtime_model_calls calls
          ON calls.run_id=actions.run_id AND calls.episode_id=actions.episode_id
          AND calls.call_index=actions.decision_index
        WHERE actions.run_id=? AND actions.episode_id=?
          AND json_extract(actions.result,'$.status') IN ('completed','partial')
          AND (json_type(actions.result,'$.resource_tool_estimates')='array'
            OR json_type(calls.request,'$.context.resource_tool_estimates')='array')
        ORDER BY actions.decision_index DESC LIMIT 1''', (run_id, episode_id)).fetchone()
    return json.loads(row[0]) if row else []


def recorded_api_forecasts(store, *, run_id, episode_id):
    """Original API forecasts at the latest completed own-action boundary."""
    row = store.db.execute('''SELECT CASE
        WHEN json_type(actions.result,'$.api_reported_execution_forecasts')='array'
        THEN json_extract(actions.result,'$.api_reported_execution_forecasts')
        ELSE json_extract(calls.request,'$.context.api_reported_execution_forecasts') END
        FROM runtime_actions actions LEFT JOIN runtime_model_calls calls
          ON calls.run_id=actions.run_id AND calls.episode_id=actions.episode_id
          AND calls.call_index=actions.decision_index
        WHERE actions.run_id=? AND actions.episode_id=?
          AND json_extract(actions.result,'$.status') IN ('completed','partial')
          AND (json_type(actions.result,'$.api_reported_execution_forecasts')='array'
            OR json_type(calls.request,'$.context.api_reported_execution_forecasts')='array')
        ORDER BY actions.decision_index DESC LIMIT 1''', (run_id, episode_id)).fetchone()
    return json.loads(row[0]) if row else []


def validate_recorded_estimates(store, value, *, schema=None, job_ref=None, reference_resolver=None):
    """A forecast identity binds its supplied fields to the original record.

    This is factual communication validation. It does not reassess the estimate,
    choose a newer snapshot, or judge the scientific interpretation around it.

    Declared reference namespaces identify forecasts; parent field names are
    unrestricted. Schema-less callers compare only an actual recorded identity.
    """
    reference_namespaces = {field: namespace for namespace, field in FORECAST_REFERENCE_FIELDS.items()}
    reference_namespaces.update(job_ref='homology_job', sample_ref='job_sample')
    def visit(node, declared):
        if isinstance(node, Mapping):
            properties = declared.get('properties', {}) if declared is not None else {}
            identities = [name for name, field in properties.items()
                if field.get('format') in REFERENCE_FORMATS
                and field.get('x-reference-namespace') == 'job_execution_estimate'
                and node.get(name) is not None]
            if declared is None and node.get('estimate_ref') is not None and store is not None:
                if recorded_estimate(store, node['estimate_ref'], job_ref) is not None:
                    identities.append('estimate_ref')
            for name in identities:
                reference = node[name]
                actual = recorded_estimate(store, reference, job_ref) if store is not None else None
                fields = node.keys() & actual.keys() if actual is not None else ()
                # A differently declared reference remains the parent's field,
                # even if its name also appears in the native forecast record.
                fields = [key for key in fields if properties.get(key, {}).get('format') not in REFERENCE_FORMATS
                    or properties[key].get('x-reference-namespace') == reference_namespaces.get(key)]
                if (actual is None or any(node[key] != actual[key] for key in fields)
                        or reference_resolver is not None and not reference_resolver(reference, 'job_execution_estimate')):
                    raise ReportBoundaryError('Execution forecast differs from its recorded estimate',
                        code='estimate_fact_mismatch')
            for name, child in node.items():
                visit(child, properties.get(name) if declared is not None else None)
        elif isinstance(node, (list, tuple)):
            for child in node:
                visit(child, declared.get('items') if declared is not None else None)
    visit(value, schema)
