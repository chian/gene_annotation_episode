"""The A103 result acquisition binding acquires a launched BV-BRC AppService job's results from its returned handoff.

Real bindings, the run's shared Store, the real episode_runtime registry, journal and linker, a real
``ModelProvider`` (never called), A103's own AppService services and their real HTTP client. The A103 API job
binding first carries the job to its usable handoff; its own admitted return is the results episode's assigned
handoff. The client talks only to a local 127.0.0.1 server that answers each JSON-RPC call with a test-written
native body in the service's documented native shape and serves the downloaded object's bytes (the repository
holds no captured BV-BRC exchange); no model, external network or HPC is used. Units are driven through each
source's own admission and execution.
"""
import asyncio
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
from threading import Thread

import pytest

from episode_runtime import BindingRegistry, RunJournal, link
from method_loop import END_YIELD_STOP, EpisodeRecord
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.tools.gene_context_evidence.evidence_operations import A103ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.contract_binding import RETURN_FORM
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.execution_job_submission.\
    api_job_execution.episode import ExecutionEpisode as ApiJobEpisode
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.held_inputs import AppServiceInputError, read_receipt
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.execution_result_acquisition.\
    episode import ExecutionEpisode
from gene_annotation_episode.episodic_workflow.episode_support.tools.gene_context_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.gene_context_evidence.appservice_publication import read_publication
from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store

PREFIX = 'api.bvbrc_appservice.'
MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}
CONTINUATION = {'cutoff': 0.001, 'parameters': {'uncertainty_alpha': 0.05}}
FOLDER = '/synthetic@bvbrc/home/Selected folder/.Original name'
# A Homology job (A103's AppService application) with one output target; every value is explicit test input.
PARAMETERS = {'input_type': 'aa', 'input_source': 'fasta_data', 'input_fasta_data': '>query\nMKTAYIAKQRQISFVK\n',
              'db_type': 'faa', 'db_source': 'precomputed_database', 'db_precomputed_database': 'bacteria-archaea',
              'blast_program': 'blastp', 'output_path': '/synthetic@bvbrc/home/Selected folder',
              'output_file': 'Original name'}
REQUEST = {'version': 'bvbrc_appservice_request_v1', 'effect_contract': 'selected_api_effects_v1',
           'required_application_id': 'Homology', 'parameters': PARAMETERS, 'start_parameters': {},
           'definition_inputs': [], 'input_bindings': [],
           'workspace_targets': [{'target_id': 'hits', 'path': FOLDER + '/blast_out.txt', 'type': 'txt',
                                  'purpose': 'output_parent', 'input_binding_id': None, 'metadata': {},
                                  'allow_overwrite': False, 'allow_create_parents': True}]}
FORMAT = {'format': 'tsv', 'version': None, 'mode': None, 'producer_source_ref': None, 'transformation_evidence': []}
SELECTOR = {'version': 'bvbrc_appservice_result_selector_v1', 'endpoint': 'requested_artifacts',
            'requirements': [{'requirement_id': 'hits', 'role': 'homology_hits', 'required': True,
                              'declared_format': FORMAT, 'producer_rule_evidence': None, 'exact_object': None}],
            'adapter': None, 'requested_schema': {'type': 'object', 'properties': {}, 'additionalProperties': False},
            'supplied_metadata': [], 'supplied_capabilities': []}
CONTENT = b'query\tsubject\tevalue\nq1\ts1\t1e-30\n'
OBJECT_UUID = '0f9a1c2e-3b4d-4e5f-8a6b-7c8d9e0f1a2b'
SUBMITTED = {'id': 7301, 'application_id': 'Homology', 'state_code': 'Q', 'params': json.dumps(PARAMETERS),
             'output_path': PARAMETERS['output_path'], 'output_file': PARAMETERS['output_file']}
COMPLETED = {'7301': {'id': '7301', 'app': 'Homology', 'status': 'completed', 'parameters': PARAMETERS,
                      'submit_time': '2026-11-18 12:00:00', 'start_time': '2026-11-18 12:01:00',
                      'completed_time': '2026-11-18 12:30:00', 'elapsed_time': '1740'}}
METADATA = ['blast_out.txt', 'txt', FOLDER, '2026-11-18T12:30:00Z', OBJECT_UUID, 'synthetic@bvbrc', len(CONTENT),
            {}, {}, 'o', 'n', '']


@pytest.fixture(autouse=True)
def local_only(monkeypatch):
    connect = socket.create_connection

    def only_loopback(address, *args, **kwargs):
        assert address[0] == '127.0.0.1', 'No live service calls are permitted'
        return connect(address, *args, **kwargs)

    monkeypatch.setattr(socket, 'create_connection', only_loopback)
    monkeypatch.setenv('no_proxy', '127.0.0.1')


@contextmanager
def appservice(results):
    """A loopback AppService/Workspace endpoint: each JSON-RPC method answers with ``results[method]`` (consumed in
    order) and ``GET /download/blast_out.txt`` serves the object's bytes."""
    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, body, media_type):
            self.send_response(200)
            self.send_header('Content-Type', media_type)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            rpc = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            received.append(rpc['method'])
            self._send(json.dumps({'version': '1.1', 'id': rpc['id'],
                                   'result': [results[rpc['method']].pop(0)]}).encode(), 'application/json')

        def do_GET(self):
            received.append('GET ' + self.path)
            assert self.path == '/download/blast_out.txt'
            self._send(CONTENT, 'text/tab-separated-values')

    host = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=host.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    thread.start()
    try:
        yield 'http://127.0.0.1:' + str(host.server_port), received
    finally:
        host.shutdown()
        host.server_close()
        thread.join()


def configuration(url):
    return {'kind': 'api', 'service': 'bvbrc_appservice', 'execution_contract': 'bvbrc_appservice_execution_v1',
            'endpoints': {'AppService': url + '/app', 'Workspace': url + '/ws'}, 'scientific_adapters': []}


def provider(tmp_path, run_id):
    return ModelProvider(MODEL_CONFIG, tmp_path / ('model_calls_' + run_id), tmp_path)


def handoff_return(tmp_path, store, url, scope):
    """The A103 API job binding's own admitted return after it prepared and submitted the job."""
    binding = ApiJobEpisode(tool_registry=ToolRegistry(store), configuration={
        'resources': {'bvbrc': configuration(url)}, 'continuation': {'cutoff': 0.001, 'uncertainty_alpha': 0.05}})
    run = link(BindingRegistry([binding]), binding.binding_path,
               {'scope': scope, 'resource_id': 'bvbrc', 'request': REQUEST},
               run_id='launch', journal=RunJournal(tmp_path / 'launch.sqlite'),
               collaborators={'store': store, 'model_provider': provider(tmp_path, 'launch')})
    source = run.episode.source

    def unit(position, operation, arguments):
        selection, prepared = source.admit(position, {'selection': {'operation': PREFIX + operation,
                                                                    'arguments': arguments}}, source.action_schema())
        return asyncio.run(source._execute(position, selection, prepared))
    preparation = unit(0, 'prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'Homology'}})
    submission = unit(1, 'submit', {'preparation_receipt_ref': preparation['appservice_receipt']['ref'],
                                    'input_evidence_refs': []})
    assert submission['appservice_receipt']['contract'] == 'TaskHandoff', submission['feedback']
    record = EpisodeRecord(scope_level=run.episode.grain.name, scope_key='launch', units_consumed=2,
                           ended_by=END_YIELD_STOP, unit_records=(), controller_state=None,
                           request=source._bound.request)
    return RETURN_FORM.admit(source.result(record).as_record(), 'launch_return')


def linked(tmp_path, store, url, scope, child_return, journal='results', **handoff):
    binding = ExecutionEpisode(tool_registry=A103ToolRegistry(store, a103_work_directory=tmp_path / 'work',
                                                              target_genomic_sources={}),
                               api_resources={'bvbrc': configuration(url)})
    return link(BindingRegistry([binding]), binding.binding_path,
                {'scope': scope, 'role_assignment': {'handoffs': [
                    {'request_id': 'homology', 'slot': 'api_job_execution', 'child_return': child_return,
                     **handoff}]}},
                run_id='results', journal=RunJournal(tmp_path / (journal + '.sqlite')),
                collaborators={'store': store, 'model_provider': provider(tmp_path, journal),
                               'continuation': {binding.binding_path: CONTINUATION}})


def unit(source, position, operation, arguments, request_id='homology'):
    selection, prepared = source.admit({'selection': {'action': 'appservice_result', 'request_id': request_id,
                                                      'operation': PREFIX + operation, 'arguments': arguments}},
                                       source.action_schema())
    return asyncio.run(source._execute(position, selection, prepared))


def scope_of(store):
    store.create_problem(raw_sequence='MKTAYIAKQRQISFVK', molecule='protein')
    return store.validate_scope({'subject_refs': list(store.problem()['subject_refs'])})


def test_results_are_acquired_from_the_returned_appservice_handoff(tmp_path):
    results = {'AppService.start_app2': [SUBMITTED], 'AppService.query_tasks': [COMPLETED],
               'Workspace.get': [[[METADATA]]]}
    with Store(tmp_path / 'state') as store, appservice(results) as (url, received):
        scope = scope_of(store)
        child_return = handoff_return(tmp_path, store, url, scope)
        handoff_ref = child_return['finding']['handoff_ref']
        results['Workspace.get_download_url'] = [[url + '/download/blast_out.txt']]
        run = linked(tmp_path, store, url, scope, child_return, selector=SELECTOR)
        source = run.episode.source
        assert source.credit == 0

        # Only the returned handoff binds the original job; anything else is rejected before acquisition.
        with pytest.raises(AppServiceInputError, match='original_task_mismatch'):
            source.admit({'selection': {'action': 'appservice_result', 'request_id': 'homology',
                                        'operation': PREFIX + 'status', 'arguments': {'handoff_ref': 'other'}}},
                         source.action_schema())

        status = unit(source, 0, 'status', {'handoff_ref': handoff_ref})
        assert status['status'] == 'completed', status['feedback']
        assert status['appservice_receipt']['contract'] == 'TaskObservation'
        assert read_receipt(store, status['appservice_receipt']['ref'], 'TaskObservation')['state'] == 'completed'

        metadata = unit(source, 1, 'workspace_metadata',
                        {'objects': [{'kind': 'original_target', 'target_id': 'hits'}], 'options': {}})
        assert metadata['status'] == 'completed', metadata['feedback']
        row = read_receipt(store, metadata['appservice_receipt']['ref'], 'WorkspaceReceipt')['rows'][0]
        assert row['uuid'] == OBJECT_UUID and row['size'] == len(CONTENT)
        selected = {'kind': 'receipt_row', 'receipt_ref': metadata['appservice_receipt']['ref'],
                    'row_pointer': row['pointer']}

        capability = unit(source, 2, 'download_capability',
                          {'objects': [selected], 'generation': 0, 'predecessor_receipt_ref': None})
        assert capability['status'] == 'completed', capability['feedback']
        assert capability['appservice_receipt']['contract'] == 'CapabilityReceipt'
        assert [row['state'] for row in capability['effects']] == ['confirmed']
        # The capability's effect slot is issued once: the same generation is rejected before acquisition.
        with pytest.raises(AppServiceInputError, match='effect_slot_already_issued'):
            source.admit({'selection': {'action': 'appservice_result', 'request_id': 'homology',
                                        'operation': PREFIX + 'download_capability',
                                        'arguments': {'objects': [selected], 'generation': 0,
                                                      'predecessor_receipt_ref': None}}}, source.action_schema())
        assert source.credit == 0

        download = unit(source, 3, 'download', {
            'capability': {'kind': 'acquired', 'receipt_ref': capability['appservice_receipt']['ref'],
                           'input_index': 0},
            'object': selected, 'byte_range': None, 'requirement_ids': ['hits'], 'role': 'homology_hits',
            'declared_format': FORMAT, 'max_bytes': 4096})
        assert download['status'] == 'completed', download['feedback']
        assert download['appservice_receipt']['contract'] == 'AcquisitionReceipt'
        assert download['appservice_receipt']['usable'] is True
        acquisition = read_receipt(store, download['appservice_receipt']['ref'], 'AcquisitionReceipt')
        assert acquisition['original_handoff_ref'] == handoff_ref
        assert store.get_artifact(acquisition['artifact']['raw_artifact_ref']) == CONTENT
        assert acquisition['artifact']['task_association']['task_id'] == '7301'
        assert source.credit == 1

        # The usable acquisition is published as the handoff's acquired bundle on the shared Store.
        publication = download['publication']
        assert publication['status'] == 'ok' and publication['code'] is None, publication
        assert publication['record_refs'] == [publication['publication_ref']]
        assert publication['publication_ref'] in download['record_refs']
        body = read_publication(store, publication['publication_ref'])
        assert body['version'] == 'bvbrc_appservice_acquired_bundle_v1'
        assert body['source_ref'] == body['reference'] == publication['publication_ref']
        assert body['bundle']['status'] == 'ok' and body['bundle']['original_task']['task_id'] == '7301'
        assert body['bundle']['acquisition_receipt_refs'] == [download['appservice_receipt']['ref']]
        assert store.get_artifact(body['bundle']['artifacts'][0]['raw_artifact_ref']) == CONTENT
        assert body['publication']['adapter_result'] is None
        assert body['assignment'] == {'original_handoff_ref': handoff_ref, 'selector': SELECTOR}
        assert received == ['AppService.start_app2', 'AppService.query_tasks', 'Workspace.get',
                            'Workspace.get_download_url', 'GET /download/blast_out.txt']

        record = EpisodeRecord(scope_level=run.episode.grain.name, scope_key='results', units_consumed=4,
                               ended_by=END_YIELD_STOP, unit_records=(), controller_state=None,
                               request=source._bound.request)
        returned = RETURN_FORM.admit(source.result(record).as_record(), 'results_return')
        assert returned['credit'] == 1 and returned['finding']['acquired_request_ids'] == ['homology']
        assert download['appservice_receipt']['ref'] in returned['finding']['evidence_refs']
        assert publication['publication_ref'] in returned['finding']['evidence_refs']


def test_an_appservice_handoff_requires_its_selector_and_a_usable_handoff(tmp_path):
    with Store(tmp_path / 'state') as store, appservice({'AppService.start_app2': [SUBMITTED]}) as (url, _):
        scope = scope_of(store)
        child_return = handoff_return(tmp_path, store, url, scope)
        with pytest.raises(ContractError, match='appservice_handoff_requires_a_selector:homology'):
            linked(tmp_path, store, url, scope, child_return)
        with pytest.raises(ContractError, match='appservice_handoff_not_usable:homology'):
            linked(tmp_path, store, url, scope, {**child_return, 'credit': 0.0}, journal='unusable',
                   selector=SELECTOR)
