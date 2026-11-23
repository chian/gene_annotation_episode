"""Caller-owned selection of statistical inputs for particular episode types.

This is not an estimator, credit projector, job monitor or report composer.
Only the fixed run-statistics interface crosses from global history. Decisions
and completed-action contexts persist the returned snapshots locally for replay.
"""
from dataclasses import asdict
from pathlib import Path
import sqlite3

from gene_annotation_episode.episodic_workflow.episode_support.calculations.biochemical_feasibility_evidence.run_statistics import ExecutionClass, RunHistory


VERSION = "episode_execution_expectation_binding"


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


