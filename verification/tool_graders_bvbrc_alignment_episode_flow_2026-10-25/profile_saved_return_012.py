"""Read-only profile of actual run009's saved result admission on a copied store.

This is a diagnostic replay, not a second Workflow run or integration success.
The 30-second sampling alarm stops only this diagnostic; it never touches009.
"""
import cProfile
import hashlib
import json
from pathlib import Path
import pstats
import shutil
import signal
import socket
import sqlite3
import sys
import time
import traceback


EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]

from gene_annotation_episode import bvbrc_msa_bundle_adapter as msa
from gene_annotation_episode import bvbrc_metacats_bundle_adapter as metacats
from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_public_search import Client


source = EVIDENCE / 'runs/msa_dna-_7cous9_'
snapshot = EVIDENCE / 'diagnostic-snapshot-012'
snapshot.mkdir()
shutil.copytree(source / 'run', snapshot / 'run')
(snapshot / 'state').mkdir()
shutil.copytree(source / 'state/artifacts', snapshot / 'state/artifacts')
with sqlite3.connect('file:' + str(source / 'state/state.sqlite3') + '?mode=ro', uri=True) as original:
    with sqlite3.connect(snapshot / 'state/state.sqlite3') as copied:
        original.backup(copied)

def forbidden(*args, **kwargs):
    raise AssertionError('Saved admission diagnostic attempted network I/O')

socket.socket.connect = forbidden
saved_sources = json.loads((source / 'SOURCE_HASHES_BEFORE.json').read_text())
changed = {name: value for name, value in saved_sources.items()
    if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != value}
assert not changed, changed
native = json.loads(next((snapshot / 'run/api-service-execution').glob('**/native_source.json')).read_text())
base = native['transport']['effective_url'].rsplit('/', 1)[0]
config = {'kind': 'api', 'service': 'bvbrc_appservice', 'execution_contract': 'bvbrc_appservice_execution_v1',
    'endpoints': {'AppService': base + '/app', 'Workspace': base + '/workspace'},
    'scientific_adapters': [{'adapter_id': module.ADAPTER_ID, 'adapter_version': '1',
        'implementation_sha256': module.implementation_sha256()} for module in (msa, metacats)]}


class SampleComplete(Exception):
    pass


profiler = cProfile.Profile()
sampled_stack = []

def stop_sample(signum, frame):
    profiler.disable()
    sampled_stack.extend(traceback.format_stack(frame))
    raise SampleComplete()


with Store(snapshot / 'state') as store:
    row = store.db.execute("SELECT run_id,episode_id FROM runtime_episodes WHERE json_extract(path,'$[#-1][0]')='results'").fetchone()
    family = ExecutionEpisodes(None, store=store, run_id=row['run_id'], directory=snapshot / 'run',
        resources={'selected-api': config}, initial_information={}, tool_registry=ToolRegistry(store, clients=Client()),
        handoff_unit=2, acquired_record_unit=3, log_window_bytes=8192, log_roles=('stdout', 'stderr'))
    store.db.execute('PRAGMA query_only=ON')
    context = family.api_execution.appservice.custody.context(row['episode_id'])
    form = json.loads(store.db.execute('SELECT form FROM runtime_forms WHERE episode_id=?',
        (context.episode_id,)).fetchone()[0])
    schema = context.request['report_contract']['measurements']['schema']
    publication_pins = {json.loads(path.read_text())['adapter_implementation_sha256']
        for path in (snapshot / 'run/api-service-execution').glob('**/publication_inputs.json')}
    assert publication_pins == {msa.implementation_sha256()}
    warmup_started = time.monotonic()
    family.api_execution.alignment_returns.facts(context, schema)
    warmup_seconds = time.monotonic() - warmup_started
    count = 0
    references = []
    def resolve(reference, namespace):
        global count
        references.append({'reference': reference, 'namespace': namespace})
        answer = family.resolve(context, reference, namespace)
        count += 1
        return answer
    signal.signal(signal.SIGALRM, stop_sample)
    started, cpu_started = time.monotonic(), time.process_time()
    status = 'complete'
    try:
        profiler.enable()
        signal.alarm(30)
        validate_form(form, schema, resolve)
        family.validate_received_report(context, form, schema)
    except SampleComplete:
        status = '30-second diagnostic sample completed; full replay unfinished'
    finally:
        profiler.disable()
        signal.alarm(0)
    profiler.dump_stats(str(EVIDENCE / 'diagnostic-012.prof'))
    with (EVIDENCE / 'diagnostic-012-profile.txt').open('w') as stream:
        pstats.Stats(profiler, stream=stream).sort_stats('cumtime').print_stats(100)
    (EVIDENCE / 'diagnostic-012-stack.txt').write_text(''.join(sampled_stack))
    receipt = {'status': status, 'source_run': str(source.relative_to(ROOT)),
        'actual_saved_form': True, 'copied_state_query_only': True, 'network_forbidden': True,
        'elapsed_seconds': time.monotonic() - started, 'cpu_seconds': time.process_time() - cpu_started,
        'warmup_seconds': warmup_seconds, 'completed_reference_resolutions': count, 'references_started': references,
        'changed_original_source_paths': changed, 'configured_adapter_pins': config['scientific_adapters'],
        'publication_pins': sorted(publication_pins)}
    (EVIDENCE / 'diagnostic-012-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))
