"""Caller-owned selection of statistical inputs for particular episode types.

This is not an estimator, credit projector, job monitor or report composer.
Only the fixed run-statistics interface crosses from global history. Decisions
and completed-action contexts persist the returned snapshots locally for replay.
"""
from dataclasses import asdict
from copy import deepcopy
from pathlib import Path
import sqlite3
from types import MappingProxyType

from .run_statistics import ExecutionClass, RunHistory


VERSION = "episode_execution_expectation_binding_v3"


def capture_execution_scopes(path, scopes, *, assigned_execution_class_ref=None):
    """Freeze caller-bound exact scopes without creating a statistical store.

    This infrastructure helper captures only typed execution statistics. A
    missing history is information for the episode, never permission to stop
    its selected work. Existing snapshots are immutable and can be journaled
    with the decision that used them.
    """
    scopes = tuple(scopes)
    if any(type(scope) is not ExecutionClass for scope in scopes):
        raise TypeError('execution_expectations_require_typed_execution_classes')
    if len({scope.ref for scope in scopes}) != len(scopes):
        raise ValueError('duplicate_execution_expectation_class')
    if assigned_execution_class_ref is not None and assigned_execution_class_ref not in {scope.ref for scope in scopes}:
        raise ValueError('assigned_execution_class_not_in_supplied_scopes')
    metadata = {'version': VERSION, 'execution_classes': [asdict(scope) for scope in scopes]}
    if assigned_execution_class_ref is not None:
        metadata['assigned_execution_class_ref'] = assigned_execution_class_ref
    history = None
    try:
        history_path = Path(path).expanduser().resolve()
        if not history_path.is_file():
            return {**metadata, 'status': 'unavailable', 'code': 'history_unavailable', 'snapshots': []}
        history = RunHistory(history_path, create=False)
        snapshots = []
        for scope in scopes:
            ref = history.capture(scope)
            reader = history.reader(ref)
            try:
                snapshots.append({'ref': ref, 'data': reader.get(ref)})
            finally:
                reader.close()
        return {**metadata, 'status': 'available', 'code': None, 'snapshots': snapshots}
    except (OSError, sqlite3.Error):
        return {**metadata, 'status': 'unavailable', 'code': 'history_unavailable', 'snapshots': []}
    except (ValueError, KeyError, TypeError):
        return {**metadata, 'status': 'invalid_statistics', 'code': 'invalid_statistics', 'snapshots': []}
    finally:
        if history is not None:
            history.close()


class ExecutionExpectations:
    def __init__(self, path, *, by_grain=None, homology=None):
        by_grain = {} if by_grain is None else by_grain
        if not isinstance(by_grain, dict) or not by_grain and homology is None:
            raise ValueError("execution_expectations_require_caller_owned_episode_types")
        bindings = {}
        for name, scopes in by_grain.items():
            if type(name) is not str or not name.isidentifier():
                raise ValueError("invalid_execution_expectation_episode_type")
            if not isinstance(scopes, (tuple, list)) or not scopes or any(type(scope) is not ExecutionClass for scope in scopes):
                raise ValueError("execution_expectations_require_typed_execution_classes")
            if len({scope.ref for scope in scopes}) != len(scopes):
                raise ValueError("duplicate_execution_expectation_class")
            bindings[name] = tuple(scopes)
        self.path = Path(path).expanduser().resolve()
        self.by_grain = MappingProxyType(bindings)
        self._homology = None
        if homology is not None:
            from .execution_recording import HomologyStatistics
            if (not isinstance(homology, dict) or set(homology) != {'roles', 'planning_roles', 'registry_directory', 'registry_configuration', 'statistics'}
                    or not isinstance(homology['roles'], list)
                    or len(set(homology['roles'])) != len(homology['roles'])
                    or not set(homology['roles']) <= {'job_launch', 'job_monitor', 'job_results'}
                    or not isinstance(homology['planning_roles'], list)
                    or any(type(name) is not str or not name.isidentifier() for name in homology['planning_roles'])
                    or len(set(homology['planning_roles'])) != len(homology['planning_roles'])
                    or set(homology['planning_roles']) & {'job_launch', 'job_monitor', 'job_results'}
                    or not (homology['roles'] or homology['planning_roles'])):
                raise ValueError('invalid_assigned_homology_expectation_binding')
            statistics = HomologyStatistics(**homology['statistics'])
            if statistics.history_path != self.path:
                raise ValueError('assigned_expectations_must_use_configured_shared_history')
            # An owned copy of the data-only selector; no episode instructions,
            # statistical writer capability or arbitrary callback crosses here.
            import json
            self._homology = json.loads(json.dumps(homology, allow_nan=False))

    @property
    def homology(self):
        return deepcopy(self._homology)

    @classmethod
    def for_homology(cls, jobs, statistics, *, roles, planning_roles=()):
        from .execution_recording import HomologyStatistics
        from .homology_jobs import HomologyJobs
        if type(jobs) is not HomologyJobs or type(statistics) is not HomologyStatistics:
            raise TypeError('typed_homology_expectation_resources_required')
        return cls(statistics.history_path, homology={'roles': list(roles), 'planning_roles': list(planning_roles),
            'registry_directory': str(jobs.directory), 'registry_configuration': jobs.config,
            'statistics': statistics.as_record()})

    @property
    def planning_roles(self):
        return frozenset() if self._homology is None else frozenset(self._homology['planning_roles'])

    @property
    def episode_types(self):
        return frozenset(self.by_grain) | self.planning_roles | (
            frozenset() if self._homology is None else frozenset(self._homology['roles']))

    def applies(self, grain):
        return grain in self.episode_types

    def as_record(self):
        return {"version": VERSION, "path": str(self.path),
                "by_grain": {name: [asdict(scope) for scope in scopes]
                             for name, scopes in sorted(self.by_grain.items())}, "homology": self.homology}

    @classmethod
    def from_record(cls, record):
        if (not isinstance(record, dict) or set(record) != {"version", "path", "by_grain", "homology"}
                or record["version"] != VERSION):
            raise ValueError("unsupported_execution_expectation_binding")
        return cls(record["path"], by_grain={name: [ExecutionClass(**scope) for scope in scopes]
                                           for name, scopes in record["by_grain"].items()}, homology=record['homology'])

    def _assigned_class(self, assignment):
        from .execution_recording import HomologyStatistics, NativeStatistics
        from .homology_jobs import HomologyJobs
        if not isinstance(assignment, dict) or not {'job_ref', 'query_ref', 'cpu'} <= set(assignment):
            raise ValueError('job_assignment_unavailable')
        jobs = HomologyJobs(self.homology['registry_directory'])
        try:
            if jobs.config != self.homology['registry_configuration']:
                raise ValueError('assigned_execution_resources_changed')
            row = jobs._row(assignment['job_ref'])
            if (row['query_ref'] != assignment['query_ref'] or row['cpu'] != assignment['cpu']
                    or row['search_mode'] != assignment.get('search_mode', 'native_defaults')):
                raise ValueError('job_assignment_identity_mismatch')
            handle = jobs._handle(assignment['job_ref'])
            if handle.path.is_file():
                recorded = handle.read().get('statistics')
                if recorded is not None:
                    context = NativeStatistics.from_record(recorded)
                    if context.history_path != self.path:
                        raise ValueError('assigned_execution_history_changed')
                    return context.execution_class
            return HomologyStatistics(**self.homology['statistics']).execution_class(jobs, row)
        finally:
            jobs.close()

    def capture(self, grain, *, assignment=None, planning_scopes=()):
        """No child writes to history; infrastructure freezes statistical views.

        An inaccessible shared database is explicit missing context, not a zero
        duration, permission gate, cancellation or fabricated controller turn.
        No history database is silently created at a missing configured path.
        """
        scopes = list(self.by_grain.get(grain, ()))
        planning_scopes = tuple(planning_scopes)
        if planning_scopes and grain not in self.planning_roles:
            raise ValueError('prospective_execution_scopes_not_bound_to_episode_type')
        for scope in planning_scopes:
            if type(scope) is not ExecutionClass:
                raise TypeError('execution_expectations_require_typed_execution_classes')
            if scope.ref not in {item.ref for item in scopes}:
                scopes.append(scope)
        assigned = None
        if self.homology is not None and grain in self.homology['roles']:
            try:
                assigned = self._assigned_class(assignment)
                if assigned.ref not in {scope.ref for scope in scopes}:
                    scopes.append(assigned)
            except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
                return {'version': VERSION, 'execution_classes': [asdict(scope) for scope in scopes],
                        'status': 'unavailable', 'code': 'assigned_execution_class_unavailable', 'snapshots': []}
        return capture_execution_scopes(self.path, scopes,
            assigned_execution_class_ref=assigned.ref if assigned is not None else None)
