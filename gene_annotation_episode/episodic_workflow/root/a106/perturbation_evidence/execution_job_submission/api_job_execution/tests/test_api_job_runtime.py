"""The A106 API job binding runs one BV-BRC AppService job on the generic runner.

Real bindings, the run's shared Store, the real episode_runtime registry, journal and linker, a real
``ModelProvider`` (never called), the real AppService service and its real HTTP client. The client talks
only to a local 127.0.0.1 server that answers each JSON-RPC call with a test-written native body in the
scheduler's documented native shape (the repository holds no captured BV-BRC exchange); no model,
external network or HPC is used. The units are driven through the source's own admission and execution.
"""
import asyncio
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
from threading import Thread

import pytest

from episode_runtime import BindingRegistry, LinkError, RunJournal, link
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.execution_job_submission.\
    api_job_execution.episode import ExecutionEpisode
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.held_inputs import AppServiceInputError, read_receipt
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.bvbrc_appservice_native_sources import NATIVE_VERSION
from gene_annotation_episode.episodic_workflow.episode_support.readers.expression_and_perturbation.bvbrc_proteome_bundle_resolution import _submitted_record
from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.execution_job_submission.\
    api_job_execution.runtime_source import _effect_rows
from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.published_evidence_assessment.\
    execution_job_submission.api_job_execution.episode import ExecutionEpisode as LiteratureExecutionEpisode
from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.perturbation_evidence.job_provider import HANDLE_PREFIX, JobProvider
from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.episode_contract import a106_progress_provider
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.practical_execution_records import digest
from gene_annotation_episode.episodic_workflow.episode_support.tools.perturbation_evidence.tools import ToolRegistry
from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store
from yield_control import CompletionYieldController

PATH = ExecutionEpisode.binding_path
PREFIX = 'api.bvbrc_appservice.'
MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}
CONTINUATION = {'cutoff': 0.001, 'parameters': {'uncertainty_alpha': 0.05}}
# A TnSeq job (one of A106's two AppService applications); every value is explicit test input.
PARAMETERS = {'output_path': '/synthetic@bvbrc/home/Selected folder', 'output_file': 'Original name',
              'reference_genome_id': '123.4', 'recipe': 'gumbel',
              'read_files': {'condition-a': {'replicates': [{'read1': '/synthetic@bvbrc/home/reads.fastq'}]}}}
REQUEST = {'version': 'bvbrc_appservice_request_v1', 'effect_contract': 'selected_api_effects_v1',
           'required_application_id': 'TnSeq', 'parameters': PARAMETERS, 'start_parameters': {},
           'definition_inputs': [], 'input_bindings': [], 'workspace_targets': []}


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


def linked(tmp_path, store, url, binding_class=ExecutionEpisode):
    binding = binding_class({'store': store}, tool_registry=ToolRegistry(store),
                            resources={'bvbrc': configuration(url)})
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    scope = {'subject_refs': list(store.problem()['subject_refs'])}
    provider = ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)
    run = link(BindingRegistry([binding]), binding.binding_path,
               {'objective': 'Carry the assigned TnSeq job to its usable handoff',
                'assignment': {'scope': scope, 'resource_id': 'bvbrc', 'request': REQUEST}},
               run_id='run', journal=RunJournal(tmp_path / 'journal.sqlite'),
               collaborators={'store': store, 'model_provider': provider,
                              'continuation': {binding.binding_path: CONTINUATION}})
    return run


def unit(source, position, operation, arguments):
    selection, prepared = source.admit(position, {'selection': {'operation': PREFIX + operation,
                                                                'arguments': arguments}}, source.action_schema())
    return asyncio.run(source._execute(position, selection, prepared))


def test_api_job_requires_its_continuation_settings(tmp_path):
    with Store(tmp_path / 'state') as store:
        binding = ExecutionEpisode({'store': store}, tool_registry=ToolRegistry(store),
                                   resources={'bvbrc': configuration('http://127.0.0.1:9')})
        with pytest.raises(LinkError, match='collaborator_required:' + PATH + ':continuation'):
            link(BindingRegistry([binding]), PATH, {'objective': 'x', 'assignment': {}}, run_id='run',
                 journal=RunJournal(tmp_path / 'journal.sqlite'), collaborators={'store': store, 'model_provider': None})


def test_api_job_resource_must_be_an_admitted_appservice_configuration(tmp_path):
    with Store(tmp_path / 'state') as store:
        with pytest.raises(ContractError, match='a106_api_job_resource_not_admitted:bvbrc'):
            ExecutionEpisode({'store': store}, tool_registry=ToolRegistry(store),
                             resources={'bvbrc': {'service': 'ncbi_blast'}})


def test_prepare_submit_and_status_carry_the_original_job_to_a_handoff_and_its_failure(tmp_path):
    submitted = {'id': 7301, 'application_id': 'TnSeq', 'state_code': 'Q', 'params': json.dumps(PARAMETERS),
                 'output_path': PARAMETERS['output_path'], 'output_file': PARAMETERS['output_file']}
    observed = {'7301': {'id': '7301', 'app': 'TnSeq', 'status': 'failed', 'parameters': PARAMETERS,
                         'submit_time': '2026-11-18 12:00:00', 'start_time': '', 'completed_time': None,
                         'elapsed_time': ''}}
    results = {'AppService.start_app2': [submitted], 'AppService.query_tasks': [observed]}
    with Store(tmp_path / 'state') as store, appservice(results) as (url, received):
        run = linked(tmp_path, store, url)
        source = run.episode.source
        opened = run.episode.grain.controller(source._bound.path)
        assert isinstance(opened, CompletionYieldController) and opened.state().stop is False
        assert source.credit() == 0.0

        # A receipt this episode does not hold is rejected before acquisition.
        with pytest.raises(AppServiceInputError, match='appservice_receipt_not_held_by_this_episode'):
            source.admit(0, {'selection': {'operation': PREFIX + 'status', 'arguments': {'handoff_ref': 'other'}}},
                         source.action_schema())

        preparation = unit(source, 0, 'prepare',
                           {'definition': {'kind': 'packaged', 'required_application_id': 'TnSeq'}})
        assert preparation['status'] == 'completed' and preparation['receipt']['contract'] == 'PreparationReceipt'
        assert received == [] and source.credit() == 0.0

        submission = unit(source, 1, 'submit', {'preparation_receipt_ref': preparation['receipt']['ref'],
                                                'input_evidence_refs': []})
        assert submission['status'] == 'completed', submission['feedback']
        assert submission['receipt']['contract'] == 'TaskHandoff' and submission['receipt']['state'] == 'submitted'
        assert [row['state'] for row in submission['effects']] == ['confirmed']
        assert received[0]['method'] == 'AppService.start_app2'
        assert received[0]['params'] == ['TnSeq', PARAMETERS, {}]
        handoff = read_receipt(store, submission['receipt']['ref'], 'TaskHandoff')
        assert handoff['original_task']['task_id'] == '7301' and handoff['usable_handoff'] is True
        assert source.credit() == 1.0

        # The original submission is issued once: a second submit is rejected before acquisition.
        with pytest.raises(AppServiceInputError, match='effect_slot_already_issued'):
            source.admit(2, {'selection': {'operation': PREFIX + 'submit', 'arguments': {
                'preparation_receipt_ref': preparation['receipt']['ref'], 'input_evidence_refs': []}}},
                source.action_schema())

        status = unit(source, 2, 'status', {'handoff_ref': submission['receipt']['ref']})
        assert status['receipt']['contract'] == 'TaskObservation' and status['receipt']['state'] == 'failed'
        assert received[1] == {**received[1], 'method': 'AppService.query_tasks', 'params': [['7301']]}
        assert source.credit() == 0.0
        assert len(received) == 2

        # The submission's response is retained with the native-source record the proteome bundle reader checks.
        task = handoff['original_task']
        record = store.get(task['submission_source_ref'])
        assert record['provider'] == 'bvbrc_appservice.submit' and record['version'] == NATIVE_VERSION
        raw = store.get_artifact(record['request_ref'])
        assert record['request_ref'] == 'artifact_' + hashlib.sha256(raw).hexdigest()
        retained = json.loads(raw)
        assert retained['origin']['operation_key'] == task['submission_operation_key']
        assert retained['snapshot']['content_ref'] == record['artifact_ref']
        assert retained['prepared']['native_operands']['call']['rpc_request']['params'] == received[0]['params']
        _submitted_record(raw, task)
        other = {**task, 'submitted_parameters': {**task['submitted_parameters'], 'recipe': 'resampling'}}
        with pytest.raises(ValueError, match='submission_identity_conflict'):
            _submitted_record(raw, other)


def test_both_a106_api_job_bindings_run_the_same_job_kind(tmp_path):
    results = {'AppService.enumerate_apps': [[{'id': 'TnSeq', 'parameters': []}]]}
    with Store(tmp_path / 'state') as store, appservice(results) as (url, received):
        source = linked(tmp_path, store, url, LiteratureExecutionEpisode).episode.source
        catalog = unit(source, 0, 'enumerate_apps', {})
        assert catalog['status'] == 'completed' and catalog['receipt']['contract'] == 'CatalogReceipt'
        assert received[0]['method'] == 'AppService.enumerate_apps' and catalog['effects'] == []
        assert source._bound.binding_path == LiteratureExecutionEpisode.binding_path


def test_an_issued_submission_interrupted_before_its_outcome_is_never_issued_again(tmp_path):
    with Store(tmp_path / 'state') as store, appservice({}) as (url, received):
        source = linked(tmp_path, store, url).episode.source
        preparation = unit(source, 0, 'prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'TnSeq'}})
        selection, prepared = source.admit(1, {'selection': {'operation': PREFIX + 'submit', 'arguments': {
            'preparation_receipt_ref': preparation['receipt']['ref'], 'input_evidence_refs': []}}},
            source.action_schema())
        # The journal state an interrupted run leaves: the submission's intent recorded, no outcome.
        key = 'run:' + source._bound.episode_id + ':1'
        source._bound.recorder.recorded('intent.1', lambda: _effect_rows(prepared, key, '2026-11-18T00:00:00+00:00'))
        outcome = asyncio.run(source._execute(1, selection, prepared))
        assert outcome['status'] == 'failed' and outcome['feedback']['code'] == 'issued_outcome_unknown'
        assert received == [] and source.credit() == 0.0
        # Its effect slot stays issued: the submission cannot be selected again.
        with pytest.raises(AppServiceInputError, match='effect_slot_already_issued'):
            source.admit(2, {'selection': {'operation': PREFIX + 'submit', 'arguments': {
                'preparation_receipt_ref': preparation['receipt']['ref'], 'input_evidence_refs': []}}},
                source.action_schema())


def test_the_handoff_records_its_admitted_scope_and_the_a106_progress_provider_watches_its_task(tmp_path):
    submitted = {'id': 7301, 'application_id': 'TnSeq', 'state_code': 'Q', 'params': json.dumps(PARAMETERS),
                 'output_path': PARAMETERS['output_path'], 'output_file': PARAMETERS['output_file']}
    observed = {'7301': {'id': '7301', 'app': 'TnSeq', 'status': 'in-progress', 'parameters': PARAMETERS,
                         'submit_time': '2026-11-18 12:00:00', 'start_time': '2026-11-18 12:01:00',
                         'completed_time': None, 'elapsed_time': ''}}
    results = {'AppService.start_app2': [submitted], 'AppService.query_tasks': [observed]}
    with Store(tmp_path / 'state') as store, appservice(results) as (url, received):
        source = linked(tmp_path, store, url).episode.source
        provider = a106_progress_provider(store, run_id='run')
        jobs = JobProvider(store, run_id='run')
        assert jobs.jobs() == {}
        preparation = unit(source, 0, 'prepare',
                           {'definition': {'kind': 'packaged', 'required_application_id': 'TnSeq'}})
        submission = unit(source, 1, 'submit', {'preparation_receipt_ref': preparation['receipt']['ref'],
                                                'input_evidence_refs': []})
        handoff_ref = submission['receipt']['ref']

        # The retained receipt records the admitted scope itself beside the typed value's scope digest.
        stored = json.loads(store.get_artifact(store.get(handoff_ref)['artifact_ref']))
        assert stored['scope'] == source._scope
        assert stored['value']['receipt']['origin']['scope_sha256'] == digest(source._scope)

        (handle,) = jobs.jobs()
        assert handle.startswith(HANDLE_PREFIX)
        assert jobs.scope(handle) == source._scope
        target = provider.describe_target(handle, source._scope)
        assert target['task_id'] == '7301' and target['handoff_ref'] == handoff_ref
        assert provider.direct_dependencies(handle, source._scope) == []
        first = provider.observe(handle, ['execution_status', 'committed_record_refs'], source._scope,
                                 permitted_committed_record_types=['source'], operation_key='watch.0')
        assert first['execution_status']['lifecycle_state'] == 'pending'
        assert first['execution_status']['execution_id'] == '7301'
        assert first['committed_record_refs'] == [handoff_ref] and first['result_available'] is False

        status = unit(source, 2, 'status', {'handoff_ref': handoff_ref})
        assert status['receipt']['contract'] == 'TaskObservation' and status['receipt']['state'] == 'running'
        second = provider.observe(handle, ['execution_status', 'committed_record_refs'], source._scope,
                                  permitted_committed_record_types=['source'], operation_key='watch.1')
        assert second['execution_status']['lifecycle_state'] == 'executing'
        assert second['committed_record_refs'] == [handoff_ref, status['receipt']['ref']]
        assert len(received) == 2

        with pytest.raises(KeyError):
            jobs.scope(HANDLE_PREFIX + 'unknown')
