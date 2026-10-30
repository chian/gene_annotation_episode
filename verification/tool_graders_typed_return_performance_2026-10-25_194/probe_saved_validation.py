"""Read-only, bounded validation-cost evidence against the frozen 182 code.

This does not construct Store (its constructor writes), run Workflow, open any
native transport, or acquire the live runs' effect locks. All called validation
functions remain the original code. Wrappers count calls then call originals.
"""
from __future__ import annotations

from collections import Counter
from contextlib import closing
import cProfile
from datetime import datetime, timezone
import hashlib
import inspect
import json
from pathlib import Path
import pstats
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
BASE = ROOT / 'verification/tool_graders_bvbrc_proteome_directional_integration_2026-10-25_182'
CANDIDATE = BASE / 'candidate'
sys.path.insert(0, str(CANDIDATE))
sys.dont_write_bytecode = True

from gene_annotation_episode import communication, bvbrc_appservice_custody
from gene_annotation_episode.bvbrc_appservice_custody import AppServiceCustody, _references
from gene_annotation_episode.bvbrc_proteome_returns import BVBRCProteomeReturns
from gene_annotation_episode.state import Store


def digest(value):
    data = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


def records(db):
    return {table: [dict(row) for row in db.execute('SELECT * FROM ' + table + ' ORDER BY rowid')]
            for table in ('runtime_episodes', 'runtime_actions', 'runtime_forms', 'runtime_report_attempts')}


def hashes():
    files = [Path(__file__), *(CANDIDATE / 'gene_annotation_episode').rglob('*.py')]
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(set(files))}


def main():
    label = sys.argv[1]
    directory = {
        'workflow': BASE / 'final_workflow_001/temporary/test_actual_selected_tool_shar0',
        'host': BASE / 'final_host_001/temporary/test_actual_host_native_number1',
    }[label].resolve()
    output = OWN / (label + '_probe_001')
    output.mkdir()
    evidence = {'argv': sys.argv, 'cwd': str(Path.cwd()), 'python': sys.executable,
        'started_at': datetime.now(timezone.utc).isoformat(), 'input_directory': str(directory),
        'scope': 'Original _values and source-custody checks, not Workflow/full semantic publication replay',
        'sqlite_uri': (directory / 'state/state.sqlite3').as_uri() + '?mode=ro', 'probes': []}
    (output / 'command.json').write_text(json.dumps(evidence, indent=2) + '\n')
    schema_counts, schema_calls = Counter(), []
    original_schema = communication.validate_closed_schema

    def counted_schema(schema):
        plain_schema = communication.plain(schema)
        key = digest(plain_schema)
        caller = inspect.currentframe().f_back
        location = f'{Path(caller.f_code.co_filename).name}:{caller.f_code.co_name}:{caller.f_lineno}'
        start = time.perf_counter()
        try:
            return original_schema(schema)
        finally:
            seconds = time.perf_counter() - start
            schema_counts[key] += 1
            schema_calls.append({'schema_sha256': key, 'caller': location, 'seconds': seconds,
                                 'fields': len(plain_schema.get('properties', {}))})

    communication.validate_closed_schema = counted_schema
    bvbrc_appservice_custody.validate_closed_schema = counted_schema
    with closing(sqlite3.connect(evidence['sqlite_uri'], uri=True)) as db:
        db.row_factory = sqlite3.Row
        store = object.__new__(Store)
        store.path, store.db = directory / 'state', db
        before = records(db)
        evidence['input_records_before_sha256'] = digest(before)
        run_id = before['runtime_episodes'][0]['run_id']
        custody = AppServiceCustody(store, run_id)
        episodes = {row['episode_id']: row for row in before['runtime_episodes']}
        forms = [row for row in before['runtime_forms'] if row['form'] and
                 json.loads(episodes[row['episode_id']]['path'])[-1][0] == 'results']
        selected = max(forms, key=lambda row: len(row['form']))
        request = json.loads(episodes[selected['episode_id']]['request'])
        schema = request['report_contract']['measurements']['schema']
        form = json.loads(selected['form'])
        refs = list(_references(form, schema))
        evidence['input_form_sha256'] = digest(form)
        evidence['input_schema_sha256'] = digest(schema)
        evidence['reference_occurrences'] = dict(Counter(namespace for _, namespace in refs))
        evidence['unique_references_by_namespace'] = dict(Counter(namespace for _, namespace in set(refs)))
        evidence['source_hashes_before'] = hashes()
        original_ref = next(value for value, namespace in refs if namespace == 'execution_result')
        returned = object.__new__(BVBRCProteomeReturns)

        def profile(name, invoke):
            schema_counts.clear()
            schema_calls.clear()
            profiler = cProfile.Profile()
            start = time.perf_counter()
            status, result = 'completed', None
            try:
                result = profiler.runcall(invoke)
            except Exception as error:
                status = 'failed'
                result = {'type': type(error).__name__, 'message': str(error)}
            seconds = time.perf_counter() - start
            profiler.dump_stats(str(output / (name + '.prof')))
            with (output / (name + '.txt')).open('w') as stream:
                pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats('cumulative').print_stats(45)
            entry = {'name': name, 'status': status, 'seconds': seconds,
                     'result_sha256': digest(result), 'result': result if isinstance(result, str) or status == 'failed' else None,
                     'schema_validation_calls': len(schema_calls), 'unique_schema_count': len(schema_counts),
                     'schema_validation_seconds': sum(row['seconds'] for row in schema_calls),
                     'schema_counts': dict(schema_counts), 'schema_calls': list(schema_calls)}
            evidence['probes'].append(entry)
            (output / 'progress.json').write_text(json.dumps(evidence, indent=2) + '\n')
            print(json.dumps({key: value for key, value in entry.items() if key not in {'schema_calls', 'schema_counts'}}), flush=True)

        profile('values', lambda: returned._values(form, schema))
        context = custody.context(selected['episode_id'])
        profile('result_possession', lambda: custody.possession(context, original_ref))
        parent_id = next(row['parent_episode_id'] for row in before['runtime_report_attempts']
                         if row['child_episode_id'] == context.episode_id and row['form'] is not None)
        parent = custody.context(parent_id)
        profile('parent_possession', lambda: custody.possession(parent, original_ref))
        if label == 'workflow':
            root = custody.context(next(key for key, row in episodes.items() if len(json.loads(row['path'])) == 1))
            profile('root_possession', lambda: custody.possession(root, original_ref))
        after = records(db)
        evidence['input_records_after_sha256'] = digest(after)
        evidence['input_records_equal'] = before == after
        current_form = db.execute('SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?',
                                  (run_id, selected['episode_id'])).fetchone()[0]
        evidence['input_form_equal'] = json.loads(current_form) == form
        evidence['source_hashes_after'] = hashes()
        evidence['source_hashes_equal'] = evidence['source_hashes_before'] == evidence['source_hashes_after']
    evidence['finished_at'] = datetime.now(timezone.utc).isoformat()
    evidence['terminal_status'] = 'completed'
    (output / 'receipt.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps({'terminal_status': evidence['terminal_status'], 'input_records_equal': evidence['input_records_equal'],
                      'input_form_equal': evidence['input_form_equal'], 'source_hashes_equal': evidence['source_hashes_equal']}), flush=True)


if __name__ == '__main__':
    main()
