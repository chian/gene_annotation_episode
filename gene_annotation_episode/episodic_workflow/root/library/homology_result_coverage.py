"""Original captured parser inventory, publication coverage and witnesses."""
import json
import sqlite3
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.materials import artifact_path
from .phmmer_grading_worker import VERSION as GRADING_VERSION


def _execution_context(provenance):
    """Only actual physical-job identities constrain job-bound captures."""
    keys = ('job_ref', 'registry_ref')
    if provenance is None:
        return None
    if not isinstance(provenance, dict):
        raise ContractError('native_result_requires_complete_execution_context')
    if not any(key in provenance for key in keys):
        return None
    if any(type(provenance.get(key)) is not str or not provenance[key] for key in keys):
        raise ContractError('native_result_requires_complete_execution_context')
    return {key: provenance[key] for key in keys}


def _termination_seen(path):
    """Retained one-query output contains its query/program terminators."""
    terminated, completed, continued = False, False, False
    with path.open('rb') as stream:
        while chunk := stream.readline(65536):
            full_line = not continued and (chunk.endswith(b'\n') or len(chunk) < 65536)
            continued = not chunk.endswith(b'\n')
            if full_line:
                line = chunk.strip()
                completed = completed or terminated and line == b'[ok]'
                terminated = terminated or line == b'//'
    return completed


def _error_counts(db):
    """A calculator failure cannot change observed native completion facts."""
    total, grading = db.execute("SELECT count(*),coalesce(sum("
        "json_extract(data,'$.phase')='tool_grading'),0) FROM errors").fetchone()
    return total-grading, grading


def _parse_inventory(directory):
    """Freeze what this completed parser attempt actually committed."""
    path = directory/'measurements.sqlite'
    if not path.is_file():
        return {'parsed_row_count': None, 'native_error_count': None, 'grading_error_count': None,
                'parser_finished': False}
    db = sqlite3.connect(path.as_uri()+'?mode=rw', uri=True)
    try:
        rows = db.execute('SELECT count(*) FROM measurements').fetchone()[0]
        errors, grading_errors = _error_counts(db)
    except sqlite3.Error:
        return {'parsed_row_count': None, 'native_error_count': None, 'grading_error_count': None,
                'parser_finished': False}
    finally:
        db.close()
    summary_path = directory/'summary.json'
    try:
        summary = json.loads(summary_path.read_text()) if summary_path.is_file() else None
    except (ValueError, OSError):
        summary = None
    return {'parsed_row_count': rows, 'native_error_count': errors, 'grading_error_count': grading_errors,
        'parser_finished': bool(isinstance(summary, dict) and summary.get('version') == GRADING_VERSION
            and summary.get('rows') == rows and summary.get('errors') == errors+grading_errors)}


def _snapshot(store, snapshot_ref, *, query_ref, scope, execution_context):
    if store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='homology_result_snapshots'").fetchone() is None:
        raise ContractError('native_result_snapshot_does_not_resolve_for_query')
    saved = store.db.execute('SELECT * FROM homology_result_snapshots WHERE source_ref=? AND query_ref=?',
        (snapshot_ref, query_ref)).fetchone()
    if saved is None:
        raise ContractError('native_result_snapshot_does_not_resolve_for_query')
    store.validate_scope(scope)
    if store.roots(query_ref) and not store.scope_covers(store.coverage(query_ref), scope):
        raise ContractError('homology_query_outside_assigned_scope')
    snapshot = json.loads(saved['body'])
    # This is the retained capture's source, never today's physical output.
    source = store.get(snapshot['execution_source_ref'])
    with artifact_path(store, source['artifact_ref']).open() as stream:
        actual_context = _execution_context(json.load(stream))
    if actual_context != _execution_context(execution_context):
        raise ContractError('native_result_snapshot_execution_context_mismatch')
    return saved, snapshot, actual_context


def _native_complete(snapshot):
    inventory = snapshot.get('parse_inventory', {})
    errors = inventory.get('native_error_count')
    terminated = snapshot.get('native_termination_seen')
    if snapshot['parse_execution']['failure'] or errors or terminated is False:
        return False
    if inventory.get('parser_finished') is True and terminated is True and errors == 0:
        return True
    return None


def recorded_coverage(store, snapshot_ref, *, query_ref, scope, execution_context=None):
    """Read captured parse facts and published native ordinals, without work.

    Native ordinals start at one; intervals are [start, end). Acquiring all
    parsed rows can include only a valid prefix of an incomplete native set.
    Historical snapshots without captured inventory keep unknowns as null.
    """
    _, snapshot, actual_context = _snapshot(store, snapshot_ref, query_ref=query_ref, scope=scope,
        execution_context=execution_context)
    intervals, acquired = None, None
    if snapshot.get('publication_witness_version') == 'native_row_publication_v1':
        intervals, acquired = [], 0
        for (ordinal,) in store.db.execute(
                'SELECT ordinal FROM homology_result_witnesses WHERE snapshot_ref=? ORDER BY ordinal', (snapshot_ref,)):
            acquired += 1
            if intervals and intervals[-1][1] == ordinal:
                intervals[-1][1] += 1
            else:
                intervals.append([ordinal, ordinal+1])
    inventory = snapshot.get('parse_inventory', {})
    parsed = inventory.get('parsed_row_count')
    errors = inventory.get('native_error_count')
    finished = inventory.get('parser_finished')
    terminated = snapshot.get('native_termination_seen')
    failure = snapshot['parse_execution']['failure']
    return {'snapshot_ref': snapshot_ref, 'query_ref': query_ref,
        'execution_source_ref': snapshot['execution_source_ref'], 'native_source_ref': snapshot['native_source_ref'],
        'execution_context': actual_context, 'status': 'available' if parsed is not None else 'unavailable',
        'parsed_row_count': parsed, 'acquired_row_count': acquired, 'acquired_ordinal_intervals': intervals,
        'all_parsed_rows_acquired': acquired == parsed if parsed is not None and acquired is not None else None,
        'parser_finished': finished, 'native_error_count': errors, 'parse_execution_failure': failure,
        'native_termination_seen': terminated, 'native_result_complete': _native_complete(snapshot)}


