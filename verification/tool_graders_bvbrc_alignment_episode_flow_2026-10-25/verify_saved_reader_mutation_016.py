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
snapshot = EVIDENCE / 'diagnostic-snapshot-016'
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
    call = lambda: read_latest_adapter_result(publications, context, adapter_ids=('bvbrc_msa', 'bvbrc_metacats'))
    initial = call()
    binding = initial[0]['publication']['adapter_result']['sheet_content']
    artifact = store.get(binding['artifact_ref'])
    sheet_path = store.path / 'artifacts' / artifact['sha256'][:2] / artifact['sha256']
    original_bytes = sheet_path.read_bytes()
    assert hashlib.sha256(original_bytes).hexdigest() == binding['sha256']
    publication_reads.clear()
    sheet_path.write_bytes(original_bytes + b' ')
    failure = None
    try:
        call()
    except ValueError as error:
        failure = {'class': type(error).__name__, 'code': str(error)}
    finally:
        sheet_path.write_bytes(original_bytes)
    assert failure is not None
    rejected_reads = list(publication_reads)
    assert rejected_reads == [initial[0]['reference']]
    restored = call()
    assert canonical(initial) == canonical(restored)
    projected = project_alignment_facts(restored[0], requested_sources=requested_sources(schema),
        sheet_set=restored[1], component_set=restored[2])
    assert projected == {name: saved_facts[name] for name in requested_sources(schema)}
    counts_after = {t: store.db.execute('SELECT count(*) FROM ' + t).fetchone()[0] for t in tables}
    assert counts_before == counts_after
    receipt = {'status': 'actual_copied_sheet_mutation_rejected_without_fallback',
        'source_run': str(source.relative_to(ROOT)), 'copied_state_query_only': True,
        'mutation': 'one whitespace byte appended only to copied Store sheet artifact, then original copied bytes restored',
        'original_artifact_sha256': binding['sha256'], 'restored_artifact_sha256': hashlib.sha256(sheet_path.read_bytes()).hexdigest(),
        'rejected_publication_reads': rejected_reads, 'observed_failure': failure,
        'restored_body_sheet_components_identical': True, 'restored_facts_equal_actual_frozen_facts': True,
        'counts_before': counts_before, 'counts_after': counts_after,
        'changed_original_source_paths': changed, 'publication_pins': sorted(publication_pins),
        'network_native_parser_calculator_forbidden': True,
        'helper_sha256': hashlib.sha256((ROOT / 'gene_annotation_episode/bvbrc_appservice_saved_results.py').read_bytes()).hexdigest()}
    (EVIDENCE / 'saved-reader-mutation-016.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))
