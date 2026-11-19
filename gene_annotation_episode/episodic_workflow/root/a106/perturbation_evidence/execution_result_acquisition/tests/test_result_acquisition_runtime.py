"""The A106 results bindings acquire a launched AppService job's results from its returned handoff.

Real bindings, the run's shared Store, the real episode_runtime registry, journal and linker, a real
``ModelProvider`` (never called), the real AppService services and their real HTTP client. The API job binding
first carries the job to its usable handoff; its own return is the results episode's assignment. The client
talks only to a local 127.0.0.1 server that answers each JSON-RPC call with a test-written native body in the
service's documented native shape and serves the downloaded object's bytes (the repository holds no captured
BV-BRC exchange); no model, external network or HPC is used. Units are driven through each source's own
admission and execution.
"""
import asyncio
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
from threading import Thread

import pytest

from episode_runtime import BindingRegistry, LinkError, RunJournal, link
from method_loop import END_YIELD_STOP, EpisodeRecord
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.episode_contract import RETURN_FORM
from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.execution_job_submission.\
    api_job_execution.episode import ExecutionEpisode as ApiJobEpisode
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.held_inputs import AppServiceInputError, read_receipt
from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.execution_result_acquisition.\
    episode import ExecutionEpisode
from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.published_evidence_assessment.\
    execution_result_acquisition.episode import ExecutionEpisode as LiteratureExecutionEpisode
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.perturbation_evidence.appservice_publication import read_publication
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_repositories import LiteratureContext, LiteratureRepositories
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation import bvbrc_intervention_contracts as contracts
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.bvbrc_application_facts import FACT_SOURCE, encode_field
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.literature_intervention_inputs import \
    read_application_operand
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.tests.intervention_analysis_fixtures import TRANSIT
from gene_annotation_episode.episodic_workflow.episode_support.tools.perturbation_evidence.tools import ToolRegistry
from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store
from yield_control import CompletionYieldController

PATH = ExecutionEpisode.binding_path
PREFIX = 'api.bvbrc_appservice.'
MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}
CONTINUATION = {'cutoff': 0.001, 'parameters': {'uncertainty_alpha': 0.05}}
FOLDER = '/synthetic@bvbrc/home/Selected folder/.Original name'
# A TnSeq job (one of A106's two AppService applications) with one output target; every value is test input.
PARAMETERS = {'output_path': '/synthetic@bvbrc/home/Selected folder', 'output_file': 'Original name',
              'reference_genome_id': '123.4', 'recipe': 'gumbel',
              'read_files': {'condition-a': {'replicates': [{'read1': '/synthetic@bvbrc/home/reads.fastq'}]}}}
REQUEST = {'version': 'bvbrc_appservice_request_v1', 'effect_contract': 'selected_api_effects_v1',
           'required_application_id': 'TnSeq', 'parameters': PARAMETERS, 'start_parameters': {},
           'definition_inputs': [], 'input_bindings': [],
           'workspace_targets': [{'target_id': 'fitness', 'path': FOLDER + '/fitness.tsv', 'type': 'txt',
                                  'purpose': 'output_parent', 'input_binding_id': None, 'metadata': {},
                                  'allow_overwrite': False, 'allow_create_parents': True}]}
FORMAT = {'format': 'tsv', 'version': None, 'mode': None, 'producer_source_ref': None, 'transformation_evidence': []}
SELECTOR = {'version': 'bvbrc_appservice_result_selector_v1', 'endpoint': 'requested_artifacts',
            'requirements': [{'requirement_id': 'fitness', 'role': 'fitness_table', 'required': True,
                              'declared_format': FORMAT, 'producer_rule_evidence': None, 'exact_object': None}],
            'adapter': None, 'requested_schema': {'type': 'object', 'properties': {}, 'additionalProperties': False},
            'supplied_metadata': [], 'supplied_capabilities': []}
CONTENT = b'locus\tfitness\nb0001\t-0.42\n'
OBJECT_UUID = '0f9a1c2e-3b4d-4e5f-8a6b-7c8d9e0f1a2b'
SUBMITTED = {'id': 7301, 'application_id': 'TnSeq', 'state_code': 'Q', 'params': json.dumps(PARAMETERS),
             'output_path': PARAMETERS['output_path'], 'output_file': PARAMETERS['output_file']}
COMPLETED = {'7301': {'id': '7301', 'app': 'TnSeq', 'status': 'completed', 'parameters': PARAMETERS,
                      'submit_time': '2026-11-18 12:00:00', 'start_time': '2026-11-18 12:01:00',
                      'completed_time': '2026-11-18 12:30:00', 'elapsed_time': '1740'}}
METADATA = ['fitness.tsv', 'txt', FOLDER, '2026-11-18T12:30:00Z', OBJECT_UUID, 'synthetic@bvbrc', len(CONTENT),
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
def appservice(results, content=CONTENT, files=None):
    """A loopback AppService/Workspace endpoint: each JSON-RPC method answers with ``results[method]`` (consumed in
    order), ``GET /download/fitness.tsv`` serves the object's bytes (``content``) and ``files`` maps any other
    GET path to the bytes it serves."""
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
            if files is not None and self.path in files:
                self._send(files[self.path], 'text/plain')
                return
            assert self.path == '/download/fitness.tsv'
            self._send(content, 'text/tab-separated-values')

    host = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=host.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    thread.start()
    try:
        yield 'http://127.0.0.1:' + str(host.server_port), received
    finally:
        host.shutdown()
        host.server_close()
        thread.join()


def configuration(url, adapters=()):
    return {'kind': 'api', 'service': 'bvbrc_appservice', 'execution_contract': 'bvbrc_appservice_execution_v1',
            'endpoints': {'AppService': url + '/app', 'Workspace': url + '/ws'}, 'scientific_adapters': list(adapters)}


def provider(tmp_path, run_id):
    return ModelProvider(MODEL_CONFIG, tmp_path / ('model_calls_' + run_id), tmp_path)


def handoff_return(tmp_path, store, url, scope):
    """The API job binding's own admitted return after it prepared and submitted the job."""
    binding = ApiJobEpisode({'store': store}, tool_registry=ToolRegistry(store), resources={'bvbrc': configuration(url)})
    run = link(BindingRegistry([binding]), binding.binding_path,
               {'objective': 'Carry the assigned TnSeq job to its usable handoff',
                'assignment': {'scope': scope, 'resource_id': 'bvbrc', 'request': REQUEST}},
               run_id='launch', journal=RunJournal(tmp_path / 'launch.sqlite'),
               collaborators={'store': store, 'model_provider': provider(tmp_path, 'launch'),
                              'continuation': {binding.binding_path: CONTINUATION}})
    source = run.episode.source

    def unit(position, operation, arguments):
        selection, prepared = source.admit(position, {'selection': {'operation': PREFIX + operation,
                                                                    'arguments': arguments}}, source.action_schema())
        return asyncio.run(source._execute(position, selection, prepared))
    preparation = unit(0, 'prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'TnSeq'}})
    submission = unit(1, 'submit', {'preparation_receipt_ref': preparation['receipt']['ref'], 'input_evidence_refs': []})
    assert submission['receipt']['contract'] == 'TaskHandoff', submission['feedback']
    record = EpisodeRecord(scope_level=run.episode.grain.name, scope_key='launch', units_consumed=2,
                           ended_by=END_YIELD_STOP, unit_records=(), controller_state=None,
                           request=source._bound.request)
    return RETURN_FORM.admit(source.result(record).as_record(), 'launch_return')


def linked(tmp_path, store, url, scope, child_return, binding_class=ExecutionEpisode, selector=SELECTOR,
           adapters=()):
    binding = binding_class({'store': store}, tools={}, resources={'bvbrc': configuration(url, adapters)})
    return link(BindingRegistry([binding]), binding.binding_path,
                {'objective': 'Acquire the fitness table of the launched TnSeq job',
                 'assignment': {'scope': scope, 'handoffs': [{'request_id': 'tnseq', 'slot': 'launch_api',
                                                              'child_return': child_return, 'selector': selector}]}},
                run_id='results', journal=RunJournal(tmp_path / 'results.sqlite'),
                collaborators={'store': store, 'model_provider': provider(tmp_path, 'results'),
                               'continuation': {binding.binding_path: CONTINUATION}})


def unit(source, position, operation, arguments, request_id='tnseq'):
    selection, prepared = source.admit({'selection': {'request_id': request_id, 'operation': PREFIX + operation,
                                                      'arguments': arguments}}, source.action_schema())
    return asyncio.run(source._execute(position, selection, prepared))


def scope_of(store):
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    return {'subject_refs': list(store.problem()['subject_refs'])}


def test_results_binding_requires_its_continuation_settings(tmp_path):
    with Store(tmp_path / 'state') as store:
        binding = ExecutionEpisode({'store': store}, tools={}, resources={'bvbrc': configuration('http://127.0.0.1:9')})
        with pytest.raises(LinkError, match='collaborator_required:' + PATH + ':continuation'):
            link(BindingRegistry([binding]), PATH, {'objective': 'x', 'assignment': {}}, run_id='run',
                 journal=RunJournal(tmp_path / 'journal.sqlite'), collaborators={'store': store, 'model_provider': None})


def test_results_are_acquired_from_the_returned_handoff(tmp_path):
    results = {'AppService.start_app2': [SUBMITTED], 'AppService.query_tasks': [COMPLETED],
               'Workspace.get': [[[METADATA]]]}
    with Store(tmp_path / 'state') as store, appservice(results) as (url, received):
        scope = scope_of(store)
        child_return = handoff_return(tmp_path, store, url, scope)
        handoff_ref = child_return['finding']['handoff_ref']
        results['Workspace.get_download_url'] = [[url + '/download/fitness.tsv']]
        run = linked(tmp_path, store, url, scope, child_return)
        source = run.episode.source
        opened = run.episode.grain.controller(source._bound.path)
        assert isinstance(opened, CompletionYieldController) and opened.state().stop is False
        assert source.credit == 0

        # Only the returned handoff binds the original job; anything else is rejected before acquisition.
        with pytest.raises(AppServiceInputError, match='original_task_mismatch'):
            source.admit({'selection': {'request_id': 'tnseq', 'operation': PREFIX + 'status',
                                        'arguments': {'handoff_ref': 'other'}}}, source.action_schema())

        status = unit(source, 0, 'status', {'handoff_ref': handoff_ref})
        assert status['status'] == 'completed', status['feedback']
        assert status['receipt']['contract'] == 'TaskObservation'
        assert read_receipt(store, status['receipt']['ref'], 'TaskObservation')['state'] == 'completed'

        metadata = unit(source, 1, 'workspace_metadata',
                        {'objects': [{'kind': 'original_target', 'target_id': 'fitness'}], 'options': {}})
        assert metadata['status'] == 'completed', metadata['feedback']
        row = read_receipt(store, metadata['receipt']['ref'], 'WorkspaceReceipt')['rows'][0]
        assert row['uuid'] == OBJECT_UUID and row['size'] == len(CONTENT)
        selected = {'kind': 'receipt_row', 'receipt_ref': metadata['receipt']['ref'], 'row_pointer': row['pointer']}

        capability = unit(source, 2, 'download_capability',
                          {'objects': [selected], 'generation': 0, 'predecessor_receipt_ref': None})
        assert capability['status'] == 'completed', capability['feedback']
        assert capability['receipt']['contract'] == 'CapabilityReceipt'
        assert [row['state'] for row in capability['effects']] == ['confirmed']
        # The capability's effect slot is issued once: the same generation is rejected before acquisition.
        with pytest.raises(AppServiceInputError, match='effect_slot_already_issued'):
            source.admit({'selection': {'request_id': 'tnseq', 'operation': PREFIX + 'download_capability',
                                        'arguments': {'objects': [selected], 'generation': 0,
                                                      'predecessor_receipt_ref': None}}}, source.action_schema())
        assert source.credit == 0

        download = unit(source, 3, 'download', {
            'capability': {'kind': 'acquired', 'receipt_ref': capability['receipt']['ref'], 'input_index': 0},
            'object': selected, 'byte_range': None, 'requirement_ids': ['fitness'], 'role': 'fitness_table',
            'declared_format': FORMAT, 'max_bytes': 4096})
        assert download['status'] == 'completed', download['feedback']
        assert download['receipt']['contract'] == 'AcquisitionReceipt' and download['receipt']['usable'] is True
        acquisition = read_receipt(store, download['receipt']['ref'], 'AcquisitionReceipt')
        assert acquisition['original_handoff_ref'] == handoff_ref
        assert store.get_artifact(acquisition['artifact']['raw_artifact_ref']) == CONTENT
        assert acquisition['artifact']['task_association']['task_id'] == '7301'
        assert source.credit == 1
        assert received == ['AppService.start_app2', 'AppService.query_tasks', 'Workspace.get',
                            'Workspace.get_download_url', 'GET /download/fitness.tsv']

        # The usable acquisition is published as the handoff's acquired bundle on the shared Store.
        publication = download['publication']
        assert publication['status'] == 'ok' and publication['code'] is None, publication
        assert publication['record_refs'] == [publication['publication_ref']]
        body = read_publication(store, publication['publication_ref'])
        assert body['version'] == 'bvbrc_appservice_acquired_bundle_v1'
        assert body['bundle']['acquisition_receipt_refs'] == [download['receipt']['ref']]
        assert store.get_artifact(body['bundle']['artifacts'][0]['raw_artifact_ref']) == CONTENT
        assert body['publication']['adapter_result'] is None

        record = EpisodeRecord(scope_level=run.episode.grain.name, scope_key='results', units_consumed=4,
                               ended_by=END_YIELD_STOP, unit_records=(), controller_state=None,
                               request=source._bound.request)
        returned = RETURN_FORM.admit(source.result(record).as_record(), 'results_return')
        assert returned['credit'] == 1 and returned['finding']['acquired_request_ids'] == ['tnseq']
        assert download['receipt']['ref'] in returned['finding']['record_refs']
        assert publication['publication_ref'] in returned['finding']['record_refs']


def test_a_published_tnseq_acquisition_is_read_as_application_outcomes(tmp_path):
    """The selected TnSeq adapter's publication supplies the literature grader's ``bvbrc_application_outcomes``."""
    parameters = {'version': contracts.PARAMETERS_VERSION, 'analysis_id': 'tnseq-fitness', 'application_id': 'TnSeq',
                  'documents': [{'document_id': 'fitness', 'requirement_id': 'fitness',
                                 'representation': 'transit_resampling'}]}
    form = contracts.requested_form_schema([{'field': 'measurements', 'selection': {
        'version': contracts.SELECTION_VERSION, 'document_id': 'fitness', 'kind': 'records', 'ordinals': None,
        'offset': 0, 'limit': 100, 'member_names': None}}])
    selector = {**SELECTOR, 'adapter': {'adapter_id': 'bvbrc_tnseq', 'adapter_version': '1',
                                        'parameters': parameters}, 'requested_schema': form}
    metadata = [*METADATA[:6], len(TRANSIT), *METADATA[7:]]
    results = {'AppService.start_app2': [SUBMITTED], 'AppService.query_tasks': [COMPLETED],
               'Workspace.get': [[[metadata]]]}
    # The task reports its result object (job_result_id); its Workspace metadata carries that task association.
    files = {'/app/task_info/7301/job_result_id': (OBJECT_UUID + '\n').encode()}
    with Store(tmp_path / 'state') as store, appservice(results, TRANSIT, files) as (url, _):
        scope = scope_of(store)
        child_return = handoff_return(tmp_path, store, url, scope)
        results['Workspace.get_download_url'] = [[url + '/download/fitness.tsv']]
        source = linked(tmp_path, store, url, scope, child_return, selector=selector,
                        adapters=[{'adapter_id': 'bvbrc_tnseq', 'adapter_version': '1'}]).episode.source
        handoff_ref = child_return['finding']['handoff_ref']
        unit(source, 0, 'status', {'handoff_ref': handoff_ref})
        info = unit(source, 1, 'task_info', {'handoff_ref': handoff_ref, 'file': 'job_result_id'})
        assert info['status'] == 'completed', info['feedback']
        metadata_unit = unit(source, 2, 'workspace_metadata', {'objects': [
            {'kind': 'task_info_object', 'receipt_ref': info['receipt']['ref']}], 'options': {}})
        assert metadata_unit['status'] == 'completed', metadata_unit['feedback']
        row = read_receipt(store, metadata_unit['receipt']['ref'], 'WorkspaceReceipt')['rows'][0]
        selected = {'kind': 'receipt_row', 'receipt_ref': metadata_unit['receipt']['ref'],
                    'row_pointer': row['pointer']}
        capability = unit(source, 3, 'download_capability',
                          {'objects': [selected], 'generation': 0, 'predecessor_receipt_ref': None})
        download = unit(source, 4, 'download', {
            'capability': {'kind': 'acquired', 'receipt_ref': capability['receipt']['ref'], 'input_index': 0},
            'object': selected, 'byte_range': None, 'requirement_ids': ['fitness'], 'role': 'fitness_table',
            'declared_format': FORMAT, 'max_bytes': 4096})
        assert download['status'] == 'completed' and download['receipt']['usable'] is True, download['feedback']
        publication = download['publication']
        assert publication['status'] == 'ok' and publication['adapter_status'] == 'ok', publication
        reference = publication['publication_ref']
        assert len(publication['record_refs']) == 3 and set(publication['record_refs']) <= set(download['record_refs'])
        body = read_publication(store, reference)
        assert body['publication']['adapter_result']['adapter_id'] == 'bvbrc_tnseq'

        repositories = LiteratureRepositories(store, 'literature', (), {})
        field = encode_field('tnseq-fitness', 'measurements')

        def context(received):
            return LiteratureContext(run_id='literature', episode_id='literature', role='literature', path=(),
                                     scope=scope, assignment={}, request={}, received_record_refs=tuple(received))
        with pytest.raises(ContractError, match='literature_sheet_not_received'):
            repositories.intervention_source_cells(context([]), FACT_SOURCE, reference, [field])
        received = context(download['record_refs'])
        rows = repositories.intervention_source_cells(received, FACT_SOURCE, reference, [field])
        assert [(row['source_ref'], row['field']) for row in rows] == [(reference, field)]
        operand = read_application_operand(
            {'kind': 'application_analysis', 'sheet_ref': reference, 'field': field,
             'representation': 'transit_resampling', 'row_ordinal': 0, 'feature_id': 'geneA',
             'metric': 'log2_fold_change'},
            read_cells=lambda namespace, sheet, fields: repositories.intervention_source_cells(
                received, namespace, sheet, fields))
        assert operand['value'] == -1.95 and operand['unit'] == 'log2_ratio' and operand['source_refs'] == [reference]


def test_a_handoff_that_is_not_usable_is_not_assigned(tmp_path):
    with Store(tmp_path / 'state') as store, appservice({'AppService.start_app2': [SUBMITTED]}) as (url, _):
        scope = scope_of(store)
        child_return = handoff_return(tmp_path, store, url, scope)
        with pytest.raises(ContractError, match='a106_result_acquisition_handoff_not_usable:tnseq'):
            linked(tmp_path, store, url, scope, {**child_return, 'credit': 0.0})


def test_the_literature_results_binding_acquires_from_its_own_handoff(tmp_path):
    results = {'AppService.start_app2': [SUBMITTED], 'AppService.query_tasks': [COMPLETED]}
    with Store(tmp_path / 'state') as store, appservice(results) as (url, received):
        scope = scope_of(store)
        child_return = handoff_return(tmp_path, store, url, scope)
        source = linked(tmp_path, store, url, scope, child_return, LiteratureExecutionEpisode).episode.source
        status = unit(source, 0, 'status', {'handoff_ref': child_return['finding']['handoff_ref']})
        assert status['status'] == 'completed' and status['receipt']['contract'] == 'TaskObservation'
        assert source._bound.binding_path == LiteratureExecutionEpisode.binding_path
        assert received == ['AppService.start_app2', 'AppService.query_tasks']
