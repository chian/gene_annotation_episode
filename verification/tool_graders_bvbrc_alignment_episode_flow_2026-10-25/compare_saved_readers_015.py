"""Compare saved-result readers on copied actual run009 state; no Workflow claim."""
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
snapshot = EVIDENCE / 'diagnostic-snapshot-015'
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

import importlib
import subprocess
from gene_annotation_episode.bvbrc_alignment_returns import project_alignment_facts, requested_sources
from gene_annotation_episode.bvbrc_appservice_saved_results import read_latest_adapter_result
from gene_annotation_episode.execution_contracts import canonical, digest

subprocess.run = forbidden
subprocess.Popen = forbidden

with Store(snapshot / 'state') as store:
    row = store.db.execute("SELECT run_id,episode_id FROM runtime_episodes WHERE json_extract(path,'$[#-1][0]')='results'").fetchone()
    family = ExecutionEpisodes(None, store=store, run_id=row['run_id'], directory=snapshot / 'run',
        resources={'selected-api': config}, initial_information={}, tool_registry=ToolRegistry(store, clients=Client()),
        handoff_unit=2, acquired_record_unit=3, log_window_bytes=8192, log_roles=('stdout', 'stderr'))
    for module_name, names in {
        'bvbrc_alignment_bundle_resolution': ('_parse', 'resolve_bundle', 'consume_bundle', 'calculate_msa', 'calculate_metacats'),
        'bvbrc_msa_grader': ('calculate_msa',),
        'bvbrc_metacats_grader': ('calculate_metacats',),
        'bvbrc_analysis_transport': ('BVBRCAnalysisClient',),
        'phylogeny_formats': ('parse_aligned_fasta', 'parse_newick'),
        'bvbrc_msa_formats': ('parse_msa_frequency_table',),
        'bvbrc_metacats_formats': ('parse_metacats_metadata', 'parse_metacats_chisq_table'),
        'bvbrc_metacats_input_formats': ('parse_metacats_input_fasta',),
        'xmfa_formats': ('parse_mauve_xmfa',),
    }.items():
        module = importlib.import_module('gene_annotation_episode.' + module_name)
        for name in names:
            if hasattr(module, name):
                setattr(module, name, forbidden)
    store.db.execute('PRAGMA query_only=ON')
    context = family.api_execution.appservice.custody.context(row['episode_id'])
    schema = context.request['report_contract']['measurements']['schema']
    saved_facts = json.loads(store.db.execute('SELECT facts FROM runtime_forms WHERE episode_id=?',
        (context.episode_id,)).fetchone()[0])
    publication_pins = {json.loads(path.read_text())['adapter_implementation_sha256']
        for path in (snapshot / 'run/api-service-execution').glob('**/publication_inputs.json')}
    assert publication_pins == {msa.implementation_sha256()}
    tables = ('runtime_actions', 'runtime_model_calls', 'runtime_observations', 'runtime_report_attempts', 'runtime_forms', 'runtime_record_receipts')
    counts_before = {t: store.db.execute('SELECT count(*) FROM ' + t).fetchone()[0] for t in tables}
    publications = family.api_execution.appservice.publications
    original_read, original_content = publications.read, publications._content
    publication_reads, content_reads = [], []
    def counted_read(reference, *args, **kwargs):
        publication_reads.append(reference)
        return original_read(reference, *args, **kwargs)
    def counted_content(binding, origin, kind, stamp):
        content_reads.append({'kind': kind, 'source_ref': binding['source_ref']})
        return original_content(binding, origin, kind, stamp)
    publications.read = counted_read
    publications._content = counted_content
    results, measurements = {}, []
    for name, call in (
        ('old_cold', lambda: family.api_execution.alignment_returns._latest(context)),
        ('new_after_old', lambda: read_latest_adapter_result(publications, context, adapter_ids=('bvbrc_msa', 'bvbrc_metacats'))),
        ('old_warm', lambda: family.api_execution.alignment_returns._latest(context)),
        ('new_warm', lambda: read_latest_adapter_result(publications, context, adapter_ids=('bvbrc_msa', 'bvbrc_metacats'))),
    ):
        publication_reads.clear()
        content_reads.clear()
        started, cpu_started = time.monotonic(), time.process_time()
        result = call()
        measurement = {'name': name, 'elapsed_seconds': time.monotonic() - started,
            'cpu_seconds': time.process_time() - cpu_started, 'publication_reads': list(publication_reads),
            'content_reads': list(content_reads), 'body_sha256': digest(result[0]),
            'sheet_sha256': digest(result[1]), 'components_sha256': digest(result[2])}
        results[name] = result
        measurements.append(measurement)
        print(json.dumps({'name': name, 'elapsed_seconds': measurement['elapsed_seconds'],
            'publication_read_count': len(publication_reads)}), flush=True)
    original = results['old_cold']
    assert all(canonical(value) == canonical(original) for value in results.values())
    projected = project_alignment_facts(original[0], requested_sources=requested_sources(schema),
        sheet_set=original[1], component_set=original[2])
    assert projected == {name: saved_facts[name] for name in requested_sources(schema)}
    new = results['new_warm']
    assert projected == project_alignment_facts(new[0], requested_sources=requested_sources(schema),
        sheet_set=new[1], component_set=new[2])
    counts_after = {t: store.db.execute('SELECT count(*) FROM ' + t).fetchone()[0] for t in tables}
    assert counts_before == counts_after
    receipt = {'status': 'equal_reads_and_projection', 'source_run': str(source.relative_to(ROOT)),
        'copied_state_query_only': True, 'network_native_parser_calculator_forbidden': True,
        'measurements': measurements, 'saved_requested_facts': projected,
        'counts_before': counts_before, 'counts_after': counts_after,
        'changed_original_source_paths': changed, 'publication_pins': sorted(publication_pins),
        'helper_sha256': hashlib.sha256((ROOT / 'gene_annotation_episode/bvbrc_appservice_saved_results.py').read_bytes()).hexdigest(),
        'configured_adapter_pins': config['scientific_adapters']}
    (EVIDENCE / 'saved-reader-comparison-015.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': receipt['status'], 'actual_source_ref': original[0]['source_ref'],
        'unchanged_record_counts': counts_after}), flush=True)
