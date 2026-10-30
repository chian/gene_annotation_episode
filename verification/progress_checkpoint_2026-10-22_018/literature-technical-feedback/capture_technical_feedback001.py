"""One bounded read-only technical diagnostic; no child scientific bodies.

Only SQL projections below reach output. Opaque hash UDFs consume original TEXT
inside the projection and never parse, retain or export it. No whole request,
response, argument or reasoning/commit body is selected into Python rows.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
import stat

OUT = Path(__file__).resolve().parent
LOCATOR = Path('/tmp/configured-literature-return-boundary-root-20261022-001/CAPTURE001.json')
DB = Path('/home/chia/gene_annotation_episode_runs/configured_literature_localization_001/workspace/state.sqlite3')
RUN = 'run_d1f1317290114adb95d8a1d58ad970c1'
CHILD = 'episode_267cad05b876f1333f2c094cc23c5ad87fd97243aeb837e8bddff8040d08ca7a'
SOURCE = Path('/tmp/gene-annotation-configured-caller-20261022-007/gene_annotation_episode/runtime.py')


def now():
    return datetime.now(timezone.utc).isoformat()


def file_meta(path, *, body_hash=False):
    try:
        item = path.lstat()
    except FileNotFoundError:
        return {'present': False}
    result = {'present': True, 'size': item.st_size, 'mode': stat.S_IMODE(item.st_mode),
              'mtime_ns': item.st_mtime_ns, 'inode': item.st_ino, 'device': item.st_dev}
    if body_hash:
        result['sha256'] = sha256(path.read_bytes()).hexdigest()
    return result


def safe_token(value):
    if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', value):
        return value
    return None


def safe_reference(value):
    if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.:/-]{0,255}', value):
        return value
    return None


def opaque_sha256(value):
    if value is None:
        return None
    if not isinstance(value, (str, bytes)):
        return None
    return sha256(value.encode('utf-8') if isinstance(value, str) else value).hexdigest()


def feedback_columns(expression, prefix):
    columns = [f"json_type({expression}) AS {prefix}_json_type",
               f"opaque_sha256({expression}) AS {prefix}_sha256"]
    for field in ('category', 'code', 'phase', 'exception_type', 'native_code'):
        columns.append(f"safe_token(json_extract({expression},'$.{field}')) AS {prefix}_{field}")
    columns.extend([
        f"safe_reference(json_extract({expression},'$.diagnostic_ref')) AS {prefix}_diagnostic_ref",
        f"safe_token(json_extract({expression},'$.detail.code')) AS {prefix}_detail_code",
        f"safe_token(json_extract({expression},'$.cause.code')) AS {prefix}_cause_code",
        f"safe_token(json_extract({expression},'$.native.statistics_export.code')) AS {prefix}_native_statistics_code",
        f"json_type({expression},'$.detail') AS {prefix}_detail_type"])
    return columns


def build_query():
    columns = [
        'a.decision_index', "safe_token(json_extract(a.action,'$.kind')) AS selected_kind",
        "safe_token(json_extract(a.action,'$.tool')) AS selected_tool",
        'opaque_sha256(a.action) AS action_text_sha256',
        "json_type(a.action,'$.arguments') AS arguments_json_type",
        "CASE WHEN json_extract(a.action,'$.kind')='tool' THEN opaque_sha256(json_extract(a.action,'$.arguments')) ELSE NULL END AS arguments_json_text_sha256",
        'a.result IS NULL AS result_missing', 'a.credit IS NULL AS credit_is_null',
        "safe_token(json_extract(a.result,'$.status')) AS outcome_status",
        "safe_reference(json_extract(a.result,'$.operation_ref')) AS operation_ref",
        'n.call_index AS next_call_index', 'n.purpose AS next_call_purpose',
        'CASE WHEN n.call_index IS NULL THEN NULL ELSE n.response IS NULL END AS next_response_missing',
        "safe_token(json_extract(n.request,'$.version')) AS next_request_version",
        "safe_token(json_extract(n.request,'$.context.last_local_outcome.status')) AS next_raw_last_outcome_status",
        "safe_reference(json_extract(n.request,'$.context.last_local_outcome.operation_ref')) AS next_raw_last_outcome_operation_ref",
        "safe_token(json_extract(n.request,'$.model_presentation.context.last_local_outcome.status')) AS next_model_last_outcome_status",
        "safe_reference(json_extract(n.request,'$.model_presentation.context.last_local_outcome.operation_ref')) AS next_model_last_outcome_operation_ref",
        "json_type(n.request,'$.model_presentation') AS next_model_presentation_type"]
    for expression, prefix in (
        ("json_extract(a.result,'$.feedback')", 'outcome_feedback'),
        ("json_extract(n.request,'$.context.feedback')", 'next_raw_feedback'),
        ("json_extract(n.request,'$.model_presentation.context.feedback')", 'next_model_feedback'),
        ("json_extract(n.request,'$.context.last_local_outcome.feedback')", 'next_raw_last_feedback'),
        ("json_extract(n.request,'$.model_presentation.context.last_local_outcome.feedback')", 'next_model_last_feedback')):
        columns.extend(feedback_columns(expression, prefix))
    return 'SELECT\n  ' + ',\n  '.join(columns) + '''
FROM runtime_actions a
LEFT JOIN runtime_model_calls n
  ON n.run_id=a.run_id AND n.episode_id=a.episode_id
 AND n.call_index=a.decision_index+1 AND n.call_index<=46
WHERE a.run_id=? AND a.episode_id=? AND a.decision_index BETWEEN 0 AND 45
ORDER BY a.decision_index'''


def dump(name, value):
    path = OUT / name
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def main():
    locator_before = file_meta(LOCATOR, body_hash=True)
    locator = json.loads(LOCATOR.read_text())
    assert locator['child_episode_id'] == CHILD and locator['run_id'] == RUN
    assert locator['input_paths'][0] == str(DB)
    source_before = file_meta(SOURCE, body_hash=True)
    original_paths = [DB, Path(str(DB)+'-wal'), Path(str(DB)+'-shm')]
    before = {str(path): file_meta(path) for path in original_paths}
    sql = build_query()
    started = now()
    conn = None
    rows = None
    error = None
    provenance = {'sqlite_uri': DB.as_uri()+'?mode=ro', 'immutable': False,
        'query_only': None, 'explicit_begin': False, 'connection_explicitly_closed': False,
        'total_changes': None, 'query': sql, 'parameters': [RUN, CHILD],
        'opaque_hash_representation': 'SHA256 of exact UTF8 SQL TEXT projection; original action TEXT or json_extract JSON text. NULL remains NULL.',
        'hash_function_body_handling': 'hash only; no JSON parsing/retention/printing; no whole model request/response hash or body query',
        'active_file_metadata_equality_claimed': False,
        'active_file_metadata_limit': 'Concurrent writers can change live DB/WAL/SHM. mode=ro/query_only and total_changes describe this reader only.'}
    try:
        conn = sqlite3.connect(provenance['sqlite_uri'], uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.create_function('safe_token', 1, safe_token, deterministic=True)
        conn.create_function('safe_reference', 1, safe_reference, deterministic=True)
        conn.create_function('opaque_sha256', 1, opaque_sha256, deterministic=True)
        conn.execute('PRAGMA query_only=ON')
        provenance['query_only'] = conn.execute('PRAGMA query_only').fetchone()[0]
        conn.execute('BEGIN')
        provenance['explicit_begin'] = True
        provenance['transaction_read_started_at'] = now()
        rows = [dict(row) for row in conn.execute(sql, (RUN, CHILD))]
        provenance['transaction_read_finished_at'] = now()
        provenance['total_changes'] = conn.total_changes
        assert provenance['query_only'] == 1 and provenance['total_changes'] == 0
        assert len(rows) <= 46 and all(0 <= row['decision_index'] <= 45 for row in rows)
    except BaseException as caught:
        error = {'exception_type': type(caught).__name__, 'message_sha256': sha256(str(caught).encode()).hexdigest()}
    finally:
        if conn is not None:
            if conn.in_transaction:
                conn.rollback()
            conn.close()
            provenance['connection_explicitly_closed'] = True
    after = {str(path): file_meta(path) for path in original_paths}
    locator_after = file_meta(LOCATOR, body_hash=True)
    source_after = file_meta(SOURCE, body_hash=True)
    assert locator_before == locator_after and source_before == source_after
    dump('CAPTURE001.json', {'version': 'bounded_literature_child_technical_feedback_v1',
        'started_at': started, 'finished_at': now(), 'run_id': RUN, 'child_episode_id': CHILD,
        'decision_bounds': [0, 45], 'next_call_maximum': 46,
        'rows': rows, 'error': error, 'provenance': provenance,
        'active_source_metadata_before': before, 'active_source_metadata_after': after})
    dump('READSET001.json', {'scope': file_meta(OUT/'SCOPE001.json', body_hash=True),
        'locator_before': locator_before, 'locator_after': locator_after,
        'runtime_path': str(SOURCE), 'runtime_before': source_before, 'runtime_after': source_after,
        'runtime_semantic_read_extent': 'DecisionSource.next/execute feedback and local_outcome_preview; no application import',
        'source_read_mode': 'only one read-only SQL transaction; no model/provider/scientific body query',
        'reader_closed': provenance['connection_explicitly_closed']})
    if error is not None:
        raise RuntimeError('Bounded capture failed; safe failure retained, no retry.')
    print(json.dumps({'rows': len(rows), 'connection_closed': provenance['connection_explicitly_closed'],
        'total_changes': provenance['total_changes']}, sort_keys=True))


if __name__ == '__main__':
    main()
