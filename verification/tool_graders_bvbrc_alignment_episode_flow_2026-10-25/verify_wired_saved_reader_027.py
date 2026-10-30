"""Read closed run009 through the wired saved reader, using only a private copy."""
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import time

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]

from gene_annotation_episode import bvbrc_msa_bundle_adapter as msa
from gene_annotation_episode import bvbrc_metacats_bundle_adapter as metacats
from gene_annotation_episode.bvbrc_alignment_returns import requested_sources
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_public_search import Client

source = EVIDENCE / 'runs/msa_dna-_7cous9_'
snapshot = EVIDENCE / 'diagnostic-snapshot-027'

def hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob('*')) if path.is_file()}

original_before = hashes(source)
saved_sources = json.loads((source / 'SOURCE_HASHES_BEFORE.json').read_text())
changed_since_original = {name: {'original': value,
    'current': hashlib.sha256((ROOT / name).read_bytes()).hexdigest() if (ROOT / name).is_file() else None}
    for name, value in saved_sources.items()
    if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != value}
current_files = ('bvbrc_alignment_returns.py', 'bvbrc_appservice_saved_results.py',
    'bvbrc_appservice_publication.py', 'bvbrc_appservice_custody.py',
    'api_service_execution.py', 'episode_return_records.py')
used_before = {name: hashlib.sha256((ROOT / 'gene_annotation_episode' / name).read_bytes()).hexdigest()
    for name in current_files}
snapshot.mkdir()
shutil.copytree(source / 'run', snapshot / 'run')
(snapshot / 'state').mkdir()
shutil.copytree(source / 'state/artifacts', snapshot / 'state/artifacts')
with sqlite3.connect('file:' + str(source / 'state/state.sqlite3') + '?mode=ro', uri=True) as original:
    with sqlite3.connect(snapshot / 'state/state.sqlite3') as copied:
        original.backup(copied)

def forbidden(*args, **kwargs):
    raise AssertionError('Wired saved-reader diagnostic attempted network, native execution, parsing or calculation')

socket.socket.connect = forbidden
subprocess.run = forbidden
subprocess.Popen = forbidden
native = json.loads(next((snapshot / 'run/api-service-execution').glob('**/native_source.json')).read_text())
base = native['transport']['effective_url'].rsplit('/', 1)[0]
config = {'kind': 'api', 'service': 'bvbrc_appservice', 'execution_contract': 'bvbrc_appservice_execution_v1',
    'endpoints': {'AppService': base + '/app', 'Workspace': base + '/workspace'},
    'scientific_adapters': [{'adapter_id': module.ADAPTER_ID, 'adapter_version': '1',
        'implementation_sha256': module.implementation_sha256()} for module in (msa, metacats)]}

with Store(snapshot / 'state') as store:
    row = store.db.execute("SELECT run_id,episode_id FROM runtime_episodes WHERE json_extract(path,'$[#-1][0]')='results'").fetchone()
    family = ExecutionEpisodes(None, store=store, run_id=row['run_id'], directory=snapshot / 'run',
        resources={'selected-api': config}, initial_information={}, tool_registry=ToolRegistry(store, clients=Client()),
        handoff_unit=2, acquired_record_unit=3, log_window_bytes=8192, log_roles=('stdout', 'stderr'))
    blocked = {
        'bvbrc_alignment_bundle_resolution': ('_parse', 'resolve_bundle', 'consume_bundle', 'calculate_msa', 'calculate_metacats'),
        'bvbrc_msa_grader': ('calculate_msa',), 'bvbrc_metacats_grader': ('calculate_metacats',),
        'bvbrc_analysis_transport': ('BVBRCAnalysisClient',),
        'phylogeny_formats': ('parse_aligned_fasta', 'parse_newick'),
        'bvbrc_msa_formats': ('parse_msa_frequency_table',),
        'bvbrc_metacats_formats': ('parse_metacats_metadata', 'parse_metacats_chisq_table'),
        'bvbrc_metacats_input_formats': ('parse_metacats_input_fasta',),
        'xmfa_formats': ('parse_mauve_xmfa',),
    }
    for module_name, names in blocked.items():
        module = importlib.import_module('gene_annotation_episode.' + module_name)
        for name in names:
            if hasattr(module, name):
                setattr(module, name, forbidden)
    store.db.execute('PRAGMA query_only=ON')
    context = family.api_execution.appservice.custody.context(row['episode_id'])
    schema = context.request['report_contract']['measurements']['schema']
    saved_facts = json.loads(store.db.execute('SELECT facts FROM runtime_forms WHERE episode_id=?',
        (context.episode_id,)).fetchone()[0])
    expected = tuple(json.loads((source / name).read_text()) for name in ('publication.json', 'sheet.json', 'components.json'))
    publication_pins = {json.loads(path.read_text())['adapter_implementation_sha256']
        for path in (snapshot / 'run/api-service-execution').glob('**/publication_inputs.json')}
    assert publication_pins == {msa.implementation_sha256(), metacats.implementation_sha256()}
    tables = ('runtime_actions', 'runtime_model_calls', 'runtime_observations', 'runtime_report_attempts', 'runtime_forms', 'runtime_record_receipts')
    counts_before = {t: store.db.execute('SELECT count(*) FROM ' + t).fetchone()[0] for t in tables}
    publications = family.api_execution.appservice.publications
    original_read = publications.read
    publication_reads = []
    def counted_read(reference, *args, **kwargs):
        publication_reads.append(reference)
        return original_read(reference, *args, **kwargs)
    publications.read = counted_read
    measurements = []
    def measured(name, call):
        publication_reads.clear()
        started, cpu_started = time.monotonic(), time.process_time()
        result = call()
        record = {'name': name, 'elapsed_seconds': time.monotonic() - started,
            'cpu_seconds': time.process_time() - cpu_started, 'publication_reads': list(publication_reads),
            'value_sha256': digest(result)}
        measurements.append(record)
        print(json.dumps({**record, 'publication_read_count': len(publication_reads)}), flush=True)
        return result
    returns = family.api_execution.alignment_returns
    for name in ('wired_cold', 'wired_warm'):
        actual = measured(name, lambda: returns._latest(context))
        assert canonical(actual) == canonical(expected)
        assert len(publication_reads) == 1
    actual_facts = measured('wired_requested_facts', lambda: returns.facts(context, schema))
    assert actual_facts == {name: saved_facts[name] for name in requested_sources(schema)}
    for role in ('scientific_process', 'annotation'):
        parent = store.db.execute("SELECT episode_id FROM runtime_episodes WHERE json_extract(path,'$[#-1][0]')=?", (role,)).fetchone()
        parent_context = family.api_execution.appservice.custody.context(parent['episode_id'])
        frozen = store.db.execute('SELECT facts FROM runtime_forms WHERE episode_id=?', (parent['episode_id'],)).fetchone()
        if role == 'scientific_process':
            parent_schema = parent_context.request['report_contract']['measurements']['schema']
            parent_saved = json.loads(frozen['facts'])
        else:
            admitted = store.db.execute('SELECT contract,form FROM runtime_report_attempts WHERE parent_episode_id=? AND form IS NOT NULL AND failure IS NULL', (parent['episode_id'],)).fetchone()
            parent_schema = json.loads(admitted['contract'])['measurements']['schema']
            admitted_form = json.loads(admitted['form'])
            parent_saved = {node['x-source']: admitted_form[name] for name, node in parent_schema['properties'].items() if node.get('x-source') in requested_sources(parent_schema)}
        received = measured(role + '_received_facts', lambda: returns.received_facts(parent_context, parent_schema))
        assert received == {name: parent_saved[name] for name in requested_sources(parent_schema)}
    counts_after = {t: store.db.execute('SELECT count(*) FROM ' + t).fetchone()[0] for t in tables}
    assert counts_before == counts_after

original_after = hashes(source)
assert original_before == original_after
used_after = {name: hashlib.sha256((ROOT / 'gene_annotation_episode' / name).read_bytes()).hexdigest()
    for name in current_files}
assert used_before == used_after
receipt = {'status': 'wired_reads_equal_original_frozen_facts', 'source_run': str(source.relative_to(ROOT)),
    'copied_state_query_only': True, 'network_native_parser_calculator_forbidden': True,
    'blocked_symbols': blocked, 'measurements': measurements, 'saved_requested_facts': actual_facts,
    'counts_before': counts_before, 'counts_after': counts_after,
    'original_files_before': original_before, 'original_files_after': original_after,
    'changed_sources_since_run009': changed_since_original, 'used_source_hashes': used_after,
    'configured_adapter_pins': config['scientific_adapters']}
(EVIDENCE / 'wired-saved-reader-027.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'status': receipt['status'], 'unchanged_record_counts': counts_after}), flush=True)
