"""The A103 API job binding runs one BV-BRC AppService job on the generic runner.

Real binding, the run's shared Store, the real episode_runtime registry, journal and linker, a real
``ModelProvider`` (never called), A103's own AppService service and its real HTTP client. The client talks only
to a local 127.0.0.1 server that answers each JSON-RPC call with a test-written native body in the scheduler's
documented native shape (the repository holds no captured BV-BRC exchange); no model, external network or HPC
is used. The units are driven through the source's own admission and execution. Each operation publishes the
``episode.api_job_receipt`` every A103 API job publishes, and the A103 job and progress providers watch the
AppService task from those receipts.
"""
import asyncio
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
from threading import Thread

import pytest

from episode_runtime import BindingRegistry, RunJournal, link
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.execution_job_submission.\
    api_job_execution.appservice_source import AppServiceJobExecutionSource, effect_rows
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.execution_job_submission.\
    api_job_execution.episode import ExecutionEpisode
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.held_inputs import AppServiceInputError, read_receipt
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.bvbrc_appservice_native_sources import NATIVE_VERSION
from gene_annotation_episode.episodic_workflow.episode_support.readers.expression_and_perturbation.bvbrc_proteome_bundle_resolution import _submitted_record
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.home import a103_progress_provider
from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.gene_context_evidence.job_provider import (
    API_HANDLE_PREFIX, API_RECEIPT_PROVIDER, JobProvider)
from gene_annotation_episode.episodic_workflow.episode_support.tools.gene_context_evidence.tools import ToolRegistry
from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store

RUN_ID = 'a103_appservice_job'
PREFIX = 'api.bvbrc_appservice.'
MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}
# A Homology job (A103's AppService application); every value is explicit test input.
PARAMETERS = {'input_type': 'aa', 'input_source': 'fasta_data', 'input_fasta_data': '>query\nMKTAYIAKQRQISFVK\n',
              'db_type': 'faa', 'db_source': 'precomputed_database', 'db_precomputed_database': 'bacteria-archaea',
              'blast_program': 'blastp', 'output_path': '/synthetic@bvbrc/home/Selected folder',
              'output_file': 'Original name'}
REQUEST = {'version': 'bvbrc_appservice_request_v1', 'effect_contract': 'selected_api_effects_v1',
           'required_application_id': 'Homology', 'parameters': PARAMETERS, 'start_parameters': {},
           'definition_inputs': [], 'input_bindings': [], 'workspace_targets': []}
SUBMITTED = {'id': 7301, 'application_id': 'Homology', 'state_code': 'Q', 'params': json.dumps(PARAMETERS),
             'output_path': PARAMETERS['output_path'], 'output_file': PARAMETERS['output_file']}


def observed(status):
    return {'7301': {'id': '7301', 'app': 'Homology', 'status': status, 'parameters': PARAMETERS,
                     'submit_time': '2026-11-18 12:00:00', 'start_time': '2026-11-18 12:01:00',
                     'completed_time': None, 'elapsed_time': ''}}


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
    """A loopback JSON-RPC endpoint answering each method with ``results[method]`` (a list, consumed in order)."""
    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            rpc = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            received.append(rpc)
            body = json.dumps({'version': '1.1', 'id': rpc['id'], 'result': [results[rpc['method']].pop(0)]}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

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


def linked(tmp_path, store, url):
    binding = ExecutionEpisode(tool_registry=ToolRegistry(store), configuration={
        'resources': {'bvbrc': configuration(url)}, 'continuation': {'cutoff': 0.001, 'uncertainty_alpha': 0.05}})
    store.create_problem(raw_sequence='MKTAYIAKQRQISFVK', molecule='protein')
    scope = {'subject_refs': list(store.problem()['subject_refs'])}
    run = link(BindingRegistry([binding]), binding.binding_path,
               {'scope': scope, 'resource_id': 'bvbrc', 'request': REQUEST},
               run_id=RUN_ID, journal=RunJournal(tmp_path / 'journal.sqlite'),
               collaborators={'store': store,
                              'model_provider': ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)})
    return run.episode.source


def unit(source, position, operation, arguments):
    selection, prepared = source.admit(position, {'selection': {'operation': PREFIX + operation,
                                                                'arguments': arguments}}, source.action_schema())
    return asyncio.run(source._execute(position, selection, prepared))


def prepare_and_submit(source):
    preparation = unit(source, 0, 'prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'Homology'}})
    assert preparation['status'] == 'completed', preparation['feedback']
    assert preparation['appservice_receipt']['contract'] == 'PreparationReceipt'
    submission = unit(source, 1, 'submit', {'preparation_receipt_ref': preparation['appservice_receipt']['ref'],
                                            'input_evidence_refs': []})
    assert submission['status'] == 'completed', submission['feedback']
    return preparation, submission


def test_prepare_submit_and_status_carry_the_original_job_to_a_handoff_and_its_failure(tmp_path):
    results = {'AppService.start_app2': [SUBMITTED], 'AppService.query_tasks': [observed('failed')]}
    with Store(tmp_path / 'state') as store, appservice(results) as (url, received):
        source = linked(tmp_path, store, url)
        assert type(source) is AppServiceJobExecutionSource and source.credit() == 0.0

        # A receipt this episode does not hold is rejected before acquisition.
        with pytest.raises(AppServiceInputError, match='appservice_receipt_not_held_by_this_episode'):
            source.admit(0, {'selection': {'operation': PREFIX + 'status', 'arguments': {'handoff_ref': 'other'}}},
                         source.action_schema())

        preparation, submission = prepare_and_submit(source)
        assert received[0]['method'] == 'AppService.start_app2'
        assert received[0]['params'] == ['Homology', PARAMETERS, {}]
        assert submission['appservice_receipt']['contract'] == 'TaskHandoff'
        assert [row['state'] for row in submission['effects']] == ['confirmed']
        handoff = read_receipt(store, submission['appservice_receipt']['ref'], 'TaskHandoff')
        assert handoff['original_task']['task_id'] == '7301' and handoff['usable_handoff'] is True
        assert source.credit() == 1.0

        # The original submission is issued once: a second submit is rejected before acquisition.
        with pytest.raises(AppServiceInputError, match='effect_slot_already_issued'):
            source.admit(2, {'selection': {'operation': PREFIX + 'submit', 'arguments': {
                'preparation_receipt_ref': preparation['appservice_receipt']['ref'], 'input_evidence_refs': []}}},
                source.action_schema())

        status = unit(source, 2, 'status', {'handoff_ref': submission['appservice_receipt']['ref']})
        assert status['appservice_receipt']['contract'] == 'TaskObservation'
        assert status['appservice_receipt']['state'] == 'failed'
        assert received[1] == {**received[1], 'method': 'AppService.query_tasks', 'params': [['7301']]}
        assert source.credit() == 0.0 and len(received) == 2


def test_a_submission_retains_the_native_source_record_the_proteome_bundle_reader_checks(tmp_path):
    with Store(tmp_path / 'state') as store, appservice({'AppService.start_app2': [SUBMITTED]}) as (url, received):
        source = linked(tmp_path, store, url)
        preparation, submission = prepare_and_submit(source)
        task = read_receipt(store, submission['appservice_receipt']['ref'], 'TaskHandoff')['original_task']
        record = store.get(task['submission_source_ref'])
        assert record['provider'] == 'bvbrc_appservice.submit' and record['version'] == NATIVE_VERSION
        raw = store.get_artifact(record['request_ref'])
        assert record['request_ref'] == 'artifact_' + hashlib.sha256(raw).hexdigest()
        retained = json.loads(raw)
        assert retained['version'] == NATIVE_VERSION
        assert retained['origin']['operation_key'] == task['submission_operation_key']
        assert retained['snapshot']['content_ref'] == record['artifact_ref']
        assert retained['prepared']['native_operands']['call']['rpc_request']['params'] == received[0]['params']
        # The proteome bundle reader accepts the submission against the handoff's original task ...
        _submitted_record(raw, task)
        # ... and refuses it for a task that was not the one submitted.
        other = {**task, 'submitted_parameters': {**task['submitted_parameters'], 'output_file': 'Other name'}}
        with pytest.raises(ValueError, match='submission_identity_conflict'):
            _submitted_record(raw, other)


def test_each_appservice_operation_publishes_the_api_job_receipt_the_job_provider_watches(tmp_path):
    results = {'AppService.start_app2': [SUBMITTED], 'AppService.query_tasks': [observed('completed')]}
    with Store(tmp_path / 'state') as store, appservice(results) as (url, received):
        source = linked(tmp_path, store, url)
        bound = source._bound
        jobs = JobProvider(store, run_id=RUN_ID)
        progress = a103_progress_provider(store, run_id=RUN_ID)
        assert jobs.jobs() == {}
        preparation, submission = prepare_and_submit(source)

        record = store.get(submission['receipt_ref'])
        assert record['provider'] == API_RECEIPT_PROVIDER
        body = json.loads(store.get_artifact(record['artifact_ref']))
        assert body['service'] == 'bvbrc_appservice' and body['resource_id'] == 'bvbrc'
        assert body['scope'] == source._scope
        assert body['receipt']['operation'] == PREFIX + 'submit'
        assert body['receipt']['event']['native_handle'] == {'task_id': '7301'}
        # The receipt names the retained native response and the typed TaskHandoff it produced.
        assert body['receipt']['response_refs'] == submission['record_refs']
        assert submission['appservice_receipt']['ref'] in body['receipt']['response_refs']

        (handle,) = jobs.jobs()
        assert handle.startswith(API_HANDLE_PREFIX) and jobs.scope(handle) == source._scope
        target = progress.describe_target(handle, source._scope)
        assert target == {**target, 'kind': 'api_job', 'execution_episode_id': bound.episode_id,
                          'resource_id': 'bvbrc', 'service': 'bvbrc_appservice', 'request': source._request,
                          'native_handle': {'task_id': '7301'},
                          'receipt_refs': [preparation['receipt_ref'], submission['receipt_ref']]}
        first = progress.observe(handle, ['execution_status', 'committed_record_refs'], source._scope,
                                 permitted_committed_record_types=['source'], operation_key='watch.0')
        assert first['execution_status']['lifecycle_state'] == 'pending'
        assert first['result_available'] is False
        assert submission['appservice_receipt']['ref'] in first['committed_record_refs']

        status = unit(source, 2, 'status', {'handoff_ref': submission['appservice_receipt']['ref']})
        assert status['appservice_receipt']['state'] == 'completed' and source.credit() == 1.0
        second = progress.observe(handle, ['execution_status', 'committed_record_refs'], source._scope,
                                  permitted_committed_record_types=['source'], operation_key='watch.1')
        assert second['execution_status']['lifecycle_state'] == 'returned'
        assert second['execution_status']['native']['state'] == 'completed'
        # A completed AppService task's result is in its workspace, for the result acquisition to read.
        assert second['result_available'] is True
        assert status['receipt_ref'] in second['committed_record_refs']
        assert len(received) == 2


def test_an_issued_submission_interrupted_before_its_outcome_is_never_issued_again(tmp_path):
    with Store(tmp_path / 'state') as store, appservice({}) as (url, received):
        source = linked(tmp_path, store, url)
        preparation = unit(source, 0, 'prepare',
                           {'definition': {'kind': 'packaged', 'required_application_id': 'Homology'}})
        arguments = {'preparation_receipt_ref': preparation['appservice_receipt']['ref'], 'input_evidence_refs': []}
        selection, prepared = source.admit(1, {'selection': {'operation': PREFIX + 'submit', 'arguments': arguments}},
                                           source.action_schema())
        # The journal state an interrupted run leaves: the submission's intent recorded, no outcome.
        key = RUN_ID + ':' + source._bound.episode_id + ':1'
        source._bound.recorder.recorded('intent.1', lambda: effect_rows(prepared, key, '2026-11-18T00:00:00+00:00'))
        outcome = asyncio.run(source._execute(1, selection, prepared))
        assert outcome['status'] == 'failed' and outcome['feedback']['code'] == 'issued_outcome_unknown'
        assert store.get(outcome['receipt_ref'])['provider'] == API_RECEIPT_PROVIDER
        assert received == [] and source.credit() == 0.0
        # Its effect slot stays issued: the submission cannot be selected again.
        with pytest.raises(AppServiceInputError, match='effect_slot_already_issued'):
            source.admit(2, {'selection': {'operation': PREFIX + 'submit', 'arguments': arguments}},
                         source.action_schema())
