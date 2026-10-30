"""One read-only production call on a copied, closed host GeneTree fixture.

This is diagnostic instrumentation only. It creates no Workflow, scientific
result, new journal record, acquisition, model request, or production patch.
"""
from __future__ import annotations

import cProfile
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import pstats
import shutil
import sqlite3
import sys
import time

sys.dont_write_bytecode = True
REPO = Path('/home/chia/repos/gene_annotation_episode')
OUT = REPO / 'verification/tool_graders_bvbrc_phylogeny_return_cost_2026-10-25'
ORIGINAL = Path('/tmp/pytest-of-chia/pytest-1391/test_configured_native_publica0')
COPY = OUT / 'retained_gene_tree_fixture'
sys.path.insert(0, str(REPO))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def tree_manifest(directory):
    rows = []
    for path in sorted(directory.rglob('*')):
        assert not path.is_symlink(), ('unexpected_fixture_symlink', str(path))
        if path.is_file():
            before = path.stat()
            raw = path.read_bytes()
            after = path.stat()
            assert (before.st_size, before.st_mtime_ns, before.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ino)
            rows.append({'path': str(path.relative_to(directory)), 'bytes': len(raw),
                         'sha256': sha(raw), 'mtime_ns': before.st_mtime_ns})
    return rows


def active_descriptors(directory):
    found, unreadable = [], []
    prefix = str(directory) + '/'
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal():
            continue
        try:
            descriptors = list((proc / 'fd').iterdir())
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError:
            unreadable.append(int(proc.name))
            continue
        for fd in descriptors:
            try:
                target = os.readlink(fd)
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                continue
            if target.startswith(prefix):
                found.append({'pid': int(proc.name), 'fd': fd.name, 'target': target})
    return {'references': found, 'unreadable_pid_count': len(unreadable),
            'host_pid': 1025365, 'host_fd_directory_readable': os.access('/proc/1025365/fd', os.R_OK)}


assert ORIGINAL.is_dir() and not (OUT / 'one_received_facts.prof').exists(), 'require original and no prior profiled call'
fds_before = active_descriptors(ORIGINAL)
assert not fds_before['references'], 'fixture_has_open_file_descriptors'
assert not list((ORIGINAL / 'state').glob('state.sqlite3-*')), 'fixture_has_wal_or_shared_memory'
original_before = tree_manifest(ORIGINAL)
if not COPY.exists():
    shutil.copytree(ORIGINAL, COPY)
original_after_copy = tree_manifest(ORIGINAL)
assert original_before == original_after_copy, 'original_fixture_changed_during_copy'
copy_before = tree_manifest(COPY)
assert copy_before == original_before, 'fixture_copy_changed_bytes_or_metadata'
fds_after_copy = active_descriptors(ORIGINAL)
assert not fds_after_copy['references'], 'original_fixture_reopened_during_copy'
json_save('input_manifest.json', {'original_path': str(ORIGINAL), 'profiled_copy_path': str(COPY),
    'closure_evidence': {'fds_before': fds_before, 'fds_after_copy': fds_after_copy,
        'no_wal_or_shm': True, 'original_manifest_unchanged_during_copy': True,
        'caution': 'Fixture Store closed after completed first pytest mode. Manual runtime_episodes rows retain state=active by test design; this is not a closed Workflow or a scientific run.'},
    'files': original_before})

blocked_events = []
permitted_existing_lock_opens = []


def blocked(*args, **kwargs):
    raise AssertionError('diagnostic_forbids_acquisition_science_execution_or_model')


def audit(event, args):
    if event.startswith(('socket.', 'subprocess.')) or event in {
        'os.system', 'os.exec', 'os.posix_spawn', 'os.spawn', 'os.fork', 'os.forkpty'}:
        blocked_events.append(event)
        raise AssertionError('diagnostic_forbidden_process_or_network:' + event)
    if event == 'open':
        path, mode, flags = args
        writes = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if writes and not isinstance(path, int):
            target = Path(path).resolve()
            if not target.is_relative_to(OUT):
                raise AssertionError('diagnostic_write_outside_owned_directory')
            if target.is_relative_to(COPY):
                if (target.is_relative_to(COPY / 'selected-api-effects')
                        and target.name == '.lock' and mode == 'a'
                        and target.exists() and target.stat().st_size == 0):
                    # Inspected SelectedAPIEffects._locked/read acquire a
                    # lock and read; no bytes or states are written here.
                    permitted_existing_lock_opens.append(str(target.relative_to(COPY)))
                else:
                    raise AssertionError('diagnostic_write_to_retained_input')


sys.addaudithook(audit)

# Load production classes without constructing service clients or a Workflow.
from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.api_selected_effects import SelectedAPIEffects
from gene_annotation_episode.bvbrc_appservice_host import BVBRCAppServiceHost
from gene_annotation_episode.bvbrc_phylogeny_returns import BVBRCPhylogenyReturns
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.state import Store
import gene_annotation_episode.runtime  # Original transport-normalization reader is used by custody.

targets = {
    'phylogeny_formats': ['parse_newick', 'parse_aligned_fasta', 'parse_relaxed_phylip', 'parse_phyloxml'],
    'phylogeny_calculators': ['alignment_components', 'tree_components', 'function_composition', 'compare_unrooted_relationships'],
    'bvbrc_gene_tree_inputs': ['extract_gene_tree_sheet'],
    'bvbrc_codon_tree_inputs': ['extract_codon_tree_sheet'],
    'bvbrc_gene_tree_grader': ['calculate_gene_tree'],
    'bvbrc_codon_tree_grader': ['calculate_codon_tree'],
    'bvbrc_gene_tree_bundle_adapter': ['consume_bundle'],
    'bvbrc_codon_tree_bundle_adapter': ['consume_bundle'],
    'bvbrc_phylogeny_bundle_resolution': ['parse_reader'],
    'bvbrc_phylogeny_bundle_projection': ['consume_bundle'],
}
loaded = {name: importlib.import_module('gene_annotation_episode.' + name) for name in targets}
adapter = loaded['bvbrc_gene_tree_bundle_adapter']
pin = {'adapter_id': adapter.ADAPTER_ID, 'adapter_version': adapter.ADAPTER_VERSION,
       'implementation_sha256': adapter.implementation_sha256()}
forbidden_identities = {id(getattr(loaded[name], function)) for name, names in targets.items() for function in names}
patched = []
for module_name, module in list(sys.modules.items()):
    if module_name.startswith('gene_annotation_episode.'):
        for name, value in list(vars(module).items()):
            if id(value) in forbidden_identities:
                setattr(module, name, blocked)
                patched.append(module_name + '.' + name)

# Store.__init__ creates tables and changes PRAGMAs. Bypass only construction,
# retain the actual unmodified Store readers and open the copied DB read-only.
store = Store.__new__(Store)
store.path = COPY / 'state'
store.db = sqlite3.connect((store.path / 'state.sqlite3').as_uri() + '?mode=ro&immutable=1', uri=True,
                           isolation_level=None)
store.db.row_factory = sqlite3.Row
store._savepoint = 0
store.db.create_function('library_scope_record', 2, store._scope_filter_record)
store.db.execute('PRAGMA query_only=ON')

tables = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]


def counts():
    return {name: store.db.execute('SELECT count(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0]
            for name in tables}


counts_before = counts()
rows = list(store.db.execute('SELECT run_id,episode_id,path,request,state FROM runtime_episodes ORDER BY episode_id'))
assert len({row['run_id'] for row in rows}) == 1
run_id = rows[0]['run_id']
contexts = []
for row in rows:
    path, request = json.loads(row['path']), json.loads(row['request'])
    message = request['message']
    contexts.append(BindingContext(run_id, row['episode_id'], path[-1][0], tuple(map(tuple, path)),
        message['scope'], message.get('episode_assignment', {}), request))
root, = [ctx for ctx in contexts if len(ctx.path) == 1]
science, = [ctx for ctx in contexts if ctx.role == 'scientific_process']
results, = [ctx for ctx in contexts if ctx.role == 'results']
schema = plain(science.request['report_contract']['measurements']['schema'])
science_form = store.db.execute('SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?',
                              (run_id, science.episode_id)).fetchone()
assert science_form is not None and science_form['form'] is not None
final_form = json.loads(science_form['form'])
expected = {schema['properties'][name]['x-source']: value for name, value in final_form.items()}
root_attempts = list(store.db.execute('SELECT child_episode_id,form,failure FROM runtime_report_attempts '
    'WHERE run_id=? AND parent_episode_id=?', (run_id, root.episode_id)))
assert len(root_attempts) == 1 and root_attempts[0]['child_episode_id'] == science.episode_id
assert root_attempts[0]['failure'] is None and json.loads(root_attempts[0]['form']) == final_form
assert counts_before['runtime_observations'] == 0
publications = []
for path in sorted(COPY.rglob('publication_inputs.json')):
    value = json.loads(path.read_bytes())
    assert value['adapter_implementation_sha256'] == pin['implementation_sha256'], 'retained_adapter_code_pin_conflict'
    publications.append({'path': str(path.relative_to(COPY)), 'sha256': sha(path.read_bytes()),
        'adapter_implementation_sha256': value['adapter_implementation_sha256'],
        'selector_sha256': digest(value['selector'])})
assert len(publications) == 2

# Exact original host configuration from test_api_bvbrc_appservice.CONFIG plus
# configured(gene). Its pin must equal every retained publication input above.
configuration = {'selected-api': {'kind': 'api', 'service': 'bvbrc_appservice',
    'execution_contract': 'bvbrc_appservice_execution_v1',
    'endpoints': {'AppService': 'https://app.example.invalid/rpc', 'Workspace': 'https://workspace.example.invalid/rpc'},
    'scientific_adapters': [pin]}}
api = APIServiceExecution.__new__(APIServiceExecution)
api.store, api.run_id = store, run_id
api.directory = COPY / 'api-service-execution' / digest(run_id)
api.configuration = deepcopy(configuration)
api.selected_effects = SelectedAPIEffects(COPY, run_id=run_id)
api.legacy = None
api.appservice = BVBRCAppServiceHost(api)
api.phylogeny_returns = BVBRCPhylogenyReturns(api)


def source_manifest():
    sources = set(REPO.glob('gene_annotation_episode/*.py')) | set(REPO.glob('gene_annotation_episode/*.json'))
    sources |= {REPO / 'tests' / name for name in (
        'test_bvbrc_phylogeny_host_integration.py', 'test_bvbrc_appservice_host.py',
        'test_bvbrc_appservice_custody.py', 'test_bvbrc_appservice_inputs.py',
        'test_bvbrc_phylogeny_returns.py', 'test_bvbrc_phylogeny_bundle_resolution.py', 'test_api_bvbrc_appservice.py')}
    for name, module in list(sys.modules.items()):
        if name.startswith(('method_loop', 'jsonschema', 'referencing')) and getattr(module, '__file__', None):
            path = Path(module.__file__).resolve()
            if path.suffix == '.py':
                sources.add(path)
    return [{'path': str(path), 'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size}
            for path in sorted(sources)]


sources_before = source_manifest()
json_save('source_hashes.json', sources_before)
scope = plain(root.scope)
json_save('profile_scope.json', {'call': 'BVBRCPhylogenyReturns.received_facts(root_context, original_science_schema)',
    'call_count': 1, 'run_id': run_id, 'root_episode_id': root.episode_id,
    'science_episode_id': science.episode_id, 'results_episode_id': results.episode_id,
    'scope': scope, 'requested_schema': schema, 'configuration': configuration,
    'original_configuration_source': 'tests/test_bvbrc_phylogeny_host_integration.py:configured + tests/test_api_bvbrc_appservice.py:CONFIG',
    'publications': publications, 'counts_before': counts_before,
    'episode_lifecycle_rows': [{'episode_id': row['episode_id'], 'state': row['state']} for row in rows],
    'blocked_scientific_callables_and_aliases': sorted(patched),
    'expected_requested_facts': expected})

profile = cProfile.Profile()
started = datetime.now(timezone.utc).isoformat()
wall_before, cpu_before = time.perf_counter(), time.process_time()
with store.read_snapshot():
    observed = profile.runcall(api.phylogeny_returns.received_facts, root, schema)
cpu_seconds, wall_seconds = time.process_time() - cpu_before, time.perf_counter() - wall_before
finished = datetime.now(timezone.utc).isoformat()
profile.dump_stats(str(OUT / 'one_received_facts.prof'))
stats = pstats.Stats(profile)
function_rows = []
for (filename, line, function), (primitive_calls, total_calls, own, cumulative, callers) in stats.stats.items():
    function_rows.append({'file': filename, 'line': line, 'function': function,
        'primitive_calls': primitive_calls, 'total_calls': total_calls,
        'own_seconds': own, 'cumulative_seconds': cumulative,
        'callers': [{'file': name[0], 'line': name[1], 'function': name[2], 'stats': list(value)}
                    for name, value in callers.items()]})
function_rows.sort(key=lambda item: item['cumulative_seconds'], reverse=True)
json_save('profile_functions.json', function_rows)
stream = io.StringIO()
pstats.Stats(profile, stream=stream).sort_stats('cumulative').print_stats(100)
(OUT / 'profile_cumulative.txt').write_text(stream.getvalue())
assert observed == expected, 'production_read_changed_requested_facts'
assert counts_before == counts(), 'reader_changed_table_counts'
assert source_manifest() == sources_before, 'source_changed_during_profile'
store.close()
assert tree_manifest(COPY) == copy_before, 'reader_changed_retained_copy'
assert tree_manifest(ORIGINAL) == original_before, 'original_fixture_changed_during_profile'
json_save('observed_facts.json', observed)
summary = {'status': 'completed', 'started_at_utc': started, 'finished_at_utc': finished,
    'profiled_call_count': 1, 'wall_seconds_with_profiler': wall_seconds,
    'cpu_seconds_with_profiler': cpu_seconds, 'pstats_total_seconds': stats.total_tt,
    'total_calls': stats.total_calls, 'primitive_calls': stats.prim_calls,
    'original_fixture_unchanged': True, 'profiled_copy_unchanged': True,
    'all_database_counts_unchanged': True, 'source_hashes_unchanged': True,
    'returned_values_equal_original_final_typed_form': True,
    'blocked_events': blocked_events, 'source_hashes_count': len(sources_before),
    'permitted_existing_zero_byte_lock_opens': len(permitted_existing_lock_opens),
    'limits': ['This is one retained GeneTree fact read, not the full host-test wall time.',
        'cProfile adds overhead; no unprofiled speed or optimized speed is measured.',
        'No new science, transport, model, runtime action, observation, or full Workflow ran.']}
json_save('profile_summary.json', summary)
print(json.dumps(summary, indent=2), flush=True)
