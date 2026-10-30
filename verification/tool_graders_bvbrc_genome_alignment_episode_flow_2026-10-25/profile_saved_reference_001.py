"""One bounded saved-reference diagnostic on a private original-state copy.

No Workflow is run. The sample deadline belongs only to this diagnostic process.
The original pytest process and its Store are never written or signalled.
"""
import cProfile
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pstats
import shutil
import signal
import sqlite3
import sys
import time
import traceback


EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]

import pytest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_genome_alignment_saved_structure import scientific_barrier
from test_public_search import Client


SOURCE = EVIDENCE / 'runs/mauve-v4-d00v9ick'
SNAPSHOT = EVIDENCE / 'diagnostic-snapshot-001'
SNAPSHOT.mkdir()
(SNAPSHOT / 'state').mkdir()
with sqlite3.connect(f'file:{SOURCE / "state/state.sqlite3"}?mode=ro', uri=True) as original:
    with sqlite3.connect(SNAPSHOT / 'state/state.sqlite3') as copied:
        original.backup(copied)
shutil.copytree(SOURCE / 'state/artifacts', SNAPSHOT / 'state/artifacts')
shutil.copytree(SOURCE / 'run', SNAPSHOT / 'run')


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def content_hashes():
    return {str(path.relative_to(SNAPSHOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for root in (SNAPSHOT / 'run', SNAPSHOT / 'state/artifacts')
        for path in root.rglob('*') if path.is_file()}


original_hashes = json.loads((SOURCE / 'SOURCE_HASHES_BEFORE.json').read_text())
changed_sources = [name for name, value in original_hashes.items()
    if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != value]
assert not changed_sources, changed_sources
bindings = json.loads((SOURCE / 'CONFIGURED_BINDINGS.json').read_text())
configuration = next(row['configuration'] for row in bindings['configured_episode_bindings']
    if row['binding_id'] == 'execution_episodes')


class SampleComplete(Exception):
    pass


profiler = cProfile.Profile()
sampled_stack = []


def stop_sample(signum, frame):
    profiler.disable()
    sampled_stack.extend(traceback.format_stack(frame))
    raise SampleComplete()


with Store(SNAPSHOT / 'state') as store:
    row = store.db.execute("SELECT run_id,episode_id,state FROM runtime_episodes "
        "WHERE json_extract(path,'$[#-1][0]')='results'").fetchone()
    assert row['state'] == 'yielded'
    family = ExecutionEpisodes(None, store=store, run_id=row['run_id'], directory=SNAPSHOT / 'run',
        tool_registry=ToolRegistry(store, clients=Client()), **configuration)
    store.db.execute('PRAGMA query_only=ON')
    assert store.db.execute('PRAGMA query_only').fetchone()[0] == 1
    context = family.api_execution.appservice.custody.context(row['episode_id'])
    form = json.loads(store.db.execute('SELECT form FROM runtime_forms WHERE episode_id=?',
        (context.episode_id,)).fetchone()[0])
    reference = form['numbers'][0]['field']
    namespace = 'bvbrc_genome_alignment_field'
    tables = ('runtime_actions', 'runtime_observations', 'runtime_model_calls',
        'runtime_report_attempts', 'runtime_record_receipts')
    counts_before = {table: store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] for table in tables}
    files_before = content_hashes()
    write(SNAPSHOT / 'IMMUTABLE_FILES_BEFORE.json', files_before)
    status, answer, error = 'complete', None, None
    signal.signal(signal.SIGALRM, stop_sample)
    with pytest.MonkeyPatch.context() as patch:
        blocked = scientific_barrier(patch)
        started_at = datetime.now(timezone.utc).isoformat()
        started, cpu_started = time.monotonic(), time.process_time()
        try:
            profiler.enable()
            signal.setitimer(signal.ITIMER_REAL, 30)
            answer = family.resolve(context, reference, namespace)
        except SampleComplete:
            status = '30-second diagnostic sample ended; reference resolution unfinished'
        except BaseException as caught:
            status = 'diagnostic failed'
            error = {'type': type(caught).__name__, 'message': str(caught), 'traceback': traceback.format_exc()}
        finally:
            profiler.disable()
            signal.setitimer(signal.ITIMER_REAL, 0)
            elapsed, cpu_elapsed = time.monotonic() - started, time.process_time() - cpu_started
    profiler.dump_stats(str(EVIDENCE / 'diagnostic-001.prof'))
    stats = pstats.Stats(profiler)
    with (EVIDENCE / 'diagnostic-001-profile.txt').open('w') as stream:
        pstats.Stats(profiler, stream=stream).sort_stats('cumtime').print_stats(100)
    (EVIDENCE / 'diagnostic-001-stack.txt').write_text(''.join(sampled_stack))
    files_after = content_hashes()
    counts_after = {table: store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] for table in tables}
    relevant = []
    for (filename, line, name), (primitive, calls, own, cumulative, callers) in stats.stats.items():
        if ('bvbrc_genome_alignment_returns.py' in filename or 'bvbrc_appservice_publication.py' in filename
                or 'bvbrc_appservice_saved_results.py' in filename or 'bvbrc_appservice_custody.py' in filename):
            relevant.append({'file': filename, 'line': line, 'function': name,
                'primitive_calls': primitive, 'calls': calls, 'own_seconds': own,
                'cumulative_seconds': cumulative})
    receipt = {'status': status, 'error': error, 'answer': answer, 'started_at': started_at,
        'elapsed_seconds': elapsed, 'cpu_seconds': cpu_elapsed,
        'total_profile_calls': stats.total_calls, 'primitive_profile_calls': stats.prim_calls,
        'source_run': str(SOURCE.relative_to(ROOT)), 'private_snapshot': str(SNAPSHOT.relative_to(ROOT)),
        'original_run_written_or_signalled': False, 'workflow_executed': False,
        'cold_process_one_reference': True, 'reference': reference, 'namespace': namespace,
        'counts_before': counts_before, 'counts_after': counts_after,
        'query_only': store.db.execute('PRAGMA query_only').fetchone()[0] == 1,
        'immutable_snapshot_files_unchanged': files_before == files_after,
        'changed_original_source_paths': changed_sources,
        'configured_adapter_pins': configuration['resources']['selected-api']['scientific_adapters'],
        'blocked_scientific_aliases': blocked,
        'relevant_profile_functions': sorted(relevant, key=lambda row: -row['cumulative_seconds'])}
    write(EVIDENCE / 'diagnostic-001-receipt.json', receipt)
    print(json.dumps({key: receipt[key] for key in ('status', 'answer', 'elapsed_seconds', 'cpu_seconds',
        'total_profile_calls', 'query_only', 'immutable_snapshot_files_unchanged', 'error')}, indent=2))
    assert files_before == files_after and counts_before == counts_after
    assert error is None, error
