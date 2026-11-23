"""Execution forecasts for planning, separate from credit and continuation.

Only typed execution statistics and an optional measured job sample enter here.
No scientific Store, episode score/history, controller or scheduler is available.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import math
import re

from gene_annotation_episode.episodic_workflow.episode_support.calculations.run_statistics import CONDITIONS, EXECUTION_PHASE_BACKENDS, VERSION as STATISTICS_VERSION, ExecutionClass


VERSION = 'resource_tool_duration_estimator'
METHOD = 'exact_class_current_condition_successful_duration_mean'
OUTCOMES = ('succeeded', 'failed', 'cancelled', 'resource_limit', 'unknown')


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
    'phase': {'type': ['string', 'null'], 'enum': [None, *EXECUTION_PHASE_BACKENDS]},
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


def report_source():
    return {'type': 'array', 'meaning': ('Frozen resource/tool execution forecasts from recorded statistics and selected samples. '
        'Expected total duration is conditional on successful completion of the exact class under the current recorded condition. '
        'Outcome support describes that same condition; null support means unknown, and zero counts mean observed empty history. '
        'Observed minimum/maximum are historical ranges, not calibrated prediction intervals. '
        'Local service wall time does not separately measure queue wait or program runtime. '
        'CPU is the configured allocation; memory/scratch fields are limits, not measured consumption. '
        'No credit, action choice, remaining duration or stop/schedule decision is derived here.'),
        'report_schema': {'type': 'array', 'items': deepcopy(ESTIMATE_SCHEMA), 'x-source': 'resource_tool_estimates'}}


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
            or data['expectation_method'] != 'empirical_complete_duration_mean_by_condition_and_outcome'):
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


class ResourceToolEstimator:
    """A pure, independently bound forecasting component; it has no stop rule."""
    def as_record(self):
        return {'version': VERSION, 'method': METHOD}

    @classmethod
    def from_record(cls, record):
        if record != cls().as_record():
            raise ValueError('unsupported_resource_tool_estimator')
        return cls()

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

    def _project(self, context, *, job_ref, sample, prospective):
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
