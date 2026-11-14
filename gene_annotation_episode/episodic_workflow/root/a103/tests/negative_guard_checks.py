"""Actual A103 constructors/Store and parser-dispatch checks; no live operations.

The supplied service port grants ordinary visibility, deliberately testing that
visibility cannot replace original typed receipt qualification. Malformed stored
records are negative fixtures, never claimed as authentic historical receipts.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from gene_annotation_episode.workflow_budget import active_budget
from gene_annotation_episode.episodic_workflow.root.a103.communication import plain
from gene_annotation_episode.episodic_workflow.root.a103.episode_bindings import BindingContext
from gene_annotation_episode.episodic_workflow.root.a103.state import Store

HOMES = ('execution_job_submission/api_job_execution', 'execution_job_submission/hpc_job_execution', 'execution_job_submission/local_job_execution', 'execution_job_submission', 'execution_result_acquisition', 'hpc_work_planning/execution_job_submission/api_job_execution', 'hpc_work_planning/execution_job_submission/hpc_job_execution', 'hpc_work_planning/execution_job_submission/local_job_execution', 'hpc_work_planning/execution_job_submission', 'hpc_work_planning/execution_result_acquisition', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission', 'hpc_work_planning/hpc_allocation_execution/execution_result_acquisition', 'scientific_process/execution_job_submission/api_job_execution', 'scientific_process/execution_job_submission/hpc_job_execution', 'scientific_process/execution_job_submission/local_job_execution', 'scientific_process/execution_job_submission', 'scientific_process/execution_result_acquisition', 'scientific_process/hpc_work_planning/execution_job_submission/api_job_execution', 'scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution', 'scientific_process/hpc_work_planning/execution_job_submission/local_job_execution', 'scientific_process/hpc_work_planning/execution_job_submission', 'scientific_process/hpc_work_planning/execution_result_acquisition', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition')
VERSIONS = ('native_blast_bundle_v1', 'native_blast_database_bundle_v1', 'native_blast_masking_bundle_v1', 'native_blast_standard_database_bundle_v1', 'native_blast_utility_bundle_v1', 'native_hmmer_bundle_v1', 'native_hmmer_preparation_bundle_v1', 'native_infernal_bundle_v1', 'native_infernal_preparation_bundle_v1', 'native_protein_structure_bundle_v1', 'native_rna_structure_bundle_v1')
CONFIG = {'kind': 'api', 'service': 'bvbrc_appservice',
    'execution_contract': 'bvbrc_appservice_execution_v1',
    'endpoints': {'AppService': 'https://app.example.invalid/rpc',
        'Workspace': 'https://workspace.example.invalid/rpc'}, 'scientific_adapters': []}


def forbidden(*args, **kwargs):
    raise AssertionError('negative receipt diagnostic cannot execute provider/native work')


def caught(call):
    try:
        return {'status': 'returned', 'value': plain(call())}
    except Exception as error:
        return {'status': 'raised', 'type': type(error).__module__ + '.' + type(error).__qualname__,
            'message': str(error)}


def source(store, provider, version):
    artifact = store.artifact('{}', 'application/json')
    return store.put('source', {'provider': provider, 'accession': None, 'uri': None,
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': artifact,
        'version': version, 'retrieved_at': None}, origin='tool')['id']


def observe(home, store, directory):
    cls = import_module('gene_annotation_episode.episodic_workflow.root.a103.'
        + home.replace('/', '.') + '.episode').ExecutionEpisode
    services = SimpleNamespace(reference_in_context=lambda context, reference, namespace: True)
    binding = cls(services, store=store, directory=directory, run_id='negative-guard-run',
        resources={'selected-api': deepcopy(CONFIG)}, initial_information={},
        tool_registry=SimpleNamespace(store=store, clients={}), handoff_unit=2,
        acquired_record_unit=3, log_window_bytes=32, log_roles=[])
    # Real saved context identity is required by the original typed readers,
    # even when the candidate source is ordinary and no child result exists.
    from gene_annotation_episode.episodic_workflow.root.a103.episode_journal import Journal
    from gene_annotation_episode.episodic_workflow.root.a103.episode_receipts import EpisodeReceipts
    from gene_annotation_episode.episodic_workflow.root.a103.method_loop.identities import EpisodeRef
    run_id = 'negative-guard-run'
    path = (('annotation', 'root'),)
    scope = store.validate_scope()
    request = {'message': {'scope': plain(scope), 'episode_assignment': {}}}
    context = BindingContext(run_id, EpisodeRef(run_id, path).episode_id,
        'annotation', path, scope, {}, request)
    journal = Journal(store, run_id)
    journal.save('runtime_episodes', {'episode_id': context.episode_id,
        'path': json.dumps(plain(path)), 'request': json.dumps(request),
        'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
    EpisodeReceipts(store, run_id).bind(context.episode_id)
    result = {'constructor': {'status': 'returned'}, 'bundles': {}}
    for version in VERSIONS:
        reference = source(store, 'episode.execution_result', version)
        selection = {'run_id': context.run_id, 'episode_id': context.episode_id,
            'known_record_refs': [reference], 'initial_known_record_refs': []}
        calls = []
        original = binding._read_result
        def read(*args, **kwargs):
            calls.append(args[0])
            return original(*args, **kwargs)
        with patch.object(binding, '_read_result', read):
            received = caught(lambda: binding._received(context, selection, _handoff_read=forbidden))
            received_calls = list(calls)
            calls.clear()
            resolved = caught(lambda: binding.resolve(context, reference, 'source'))
        result['bundles'][version] = {'reference': reference, 'received': received,
            'received_generic_parser_calls': received_calls, 'resolve': resolved,
            'resolve_generic_parser_calls': list(calls)}
    for label, provider in (('practical', 'episode.practical_receipt'),
            ('api_handoff', 'episode.api_service_handoff'), ('ordinary', 'synthetic.ordinary_source')):
        reference = source(store, provider, None)
        result[label] = caught(lambda: binding.resolve(context, reference, 'source'))
    return result


def run_probe(output):
    output = Path(output).resolve()
    assert output.is_relative_to(Path(active_budget()['run_directory']).resolve())
    output.mkdir(parents=True, exist_ok=True)
    axis = Path(__file__).resolve().parents[1]
    repository = axis.parents[3]
    def hashes():
        return {str(path.relative_to(repository)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(axis.rglob('*.py')) if 'tests' not in path.relative_to(axis).parts}
    report = {'version': 'a103_negative_guard_actual_probe_v1', 'source_hashes': hashes(),
        'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'one_store_reused': True, 'actual_positive_custody': False,
        'controlled_ports': ['ordinary source visibility only'],
        'owners': {}, 'diagnostic_completed': False}
    destination = output / 'negative-guard-probe.json'
    def retain():
        destination.write_text(json.dumps(report, indent=2) + '\n')
    retain()
    with patch('subprocess.Popen', forbidden), patch('socket.socket.connect', forbidden), patch('socket.socket.connect_ex', forbidden):
        with Store(output / 'state') as store:
            store.create_problem(raw_sequence='ATGGCT', molecule='dna')
            for home in HOMES:
                try:
                    report['owners'][home] = observe(home, store, output / 'bindings' / home)
                except Exception as error:
                    report['owners'][home] = {'constructor': {'status': 'raised',
                        'type': type(error).__module__ + '.' + type(error).__qualname__, 'message': str(error)}}
                retain()
    assert hashes() == report['source_hashes']
    report['diagnostic_completed'] = True
    retain()
    return report
