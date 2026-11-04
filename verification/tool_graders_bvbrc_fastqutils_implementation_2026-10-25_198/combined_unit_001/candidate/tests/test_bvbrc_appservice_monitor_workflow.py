"""AppService monitoring through the actual shared Workflow and typed return.

Only decisions, root/monitor continuation and native response bytes are fixtures.
The ordinary launch/API/monitor episodes, custody, journal, endpoint estimator,
progress projections, admission and recovery are production implementations.
No live service, model, detached worker, HPC job or scientific grading runs here.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
import hashlib
import json

import pytest
from method_loop.archive import iter_json

from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.bvbrc_appservice_monitor import AppServiceMonitor, PROVIDER
from gene_annotation_episode.episode_monitoring import MonitorEpisodes
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_bvbrc_appservice import CONFIG, PREFIX
from test_bvbrc_appservice_custody import request
from test_bvbrc_appservice_inputs import NativeClient
from test_bvbrc_appservice_native_monitor import assignment as monitor_assignment, STAMP
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import child, form
from test_practical_runtime import selected
from test_public_search import Client


LOG = b'loading reference\x00\xff\nmatched two sequences\n'
LOG_STAMP = '2026-10-24T12:00:01+00:00'
WINDOW_BYTES = 12
FIELDS = ['execution_status', 'measurements', 'log_windows']
TIMING = {'submit_time': '2026-10-24 11:59:00', 'start_time': '0000-00-00 00:00:00',
          'completed_time': None, 'elapsed_time': '01:02:03'}
GOAL = 'Obtain original task status, native timing and a bounded stdout window'


def _forbidden(*args, **kwargs):
    raise AssertionError('controlled monitor Workflow attempted a new native/model call')


class Responses(NativeClient):
    """Complete, explicitly synthetic native responses for three primitives."""

    def rpc(self, command):
        if command['method'] == 'AppService.start_app2':
            self.value = {'id': '123', 'application_id': 'Homology', 'state_code': 'Q'}
        elif command['method'] == 'AppService.query_tasks':
            assert command['params'] == [['123']]
            self.value = {'123': {'id': '123', 'app': 'Homology', 'status': 'running', **TIMING}}
        else:
            raise AssertionError(command)
        return super().rpc(command)

    def task_info(self, task_id, file):
        assert (task_id, file) == ('123', 'stdout')
        snapshot = super().task_info(task_id, file)
        return replace(snapshot, content=LOG, retrieved_at=LOG_STAMP, transport={
            **snapshot.transport, 'received_body_bytes': len(LOG),
            'headers': {'content-length': str(len(LOG))},
            'duration_measure': 'client_http_request_turnaround', 'http_turnaround_seconds': .125})


def _controllers(path, initial):
    # These two explicitly scripted fixture roles close after two own actions.
    # Launch/API roles use the actual practical completion estimator installed
    # by Workflow.controller, not this test's action-count rule.
    role = path[-1][0]
    def estimate(history, parameters, contexts):
        return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= 2 else 1),
            parameters, {'fixture': 'root_and_monitor_continuation_only'})
    return YieldController(str(path), initial, 0, YieldParameters(100, 50),
        estimate_with_context=estimate if role in {'annotation', 'monitor'} else None)


def _monitor_form():
    sources = MonitorEpisodes(None).fact_sources('monitor')
    properties = {name: deepcopy(sources[source]['report_schema']) for name, source in {
        'progress': 'monitoring_progress_refs', 'target': 'monitoring_target_handle',
        'latest_state': 'monitoring_execution_state',
        'latest_observed_at': 'monitoring_observed_at_unix_seconds',
        'result_available': 'monitoring_result_available'}.items()}
    return {'type': 'object', 'properties': properties,
        'required': list(properties), 'additionalProperties': False}


def _run(workflow, scope):
    episode = workflow.build('annotation', 'root', GOAL, scope)
    async def perform():
        record = await episode.run_async(workflow.context)
        await episode.build_result(record)
        return record
    return asyncio.run(perform())


def _rows(store, table, columns, order):
    return [tuple(row) for row in store.db.execute(
        'SELECT ' + columns + ' FROM ' + table + ' ORDER BY ' + order)]


def test_shared_workflow_native_monitor_typed_return_and_interrupted_recovery(tmp_path, monkeypatch):
    native = Responses()
    original_constructor = BVBRCAppServiceService.__init__
    def configured(self, *args, **kwargs):
        original_constructor(self, *args, **kwargs)
        self.client = native
    monkeypatch.setattr(BVBRCAppServiceService, '__init__', configured)
    monkeypatch.setattr('socket.create_connection', _forbidden)
    monkeypatch.setattr('socket.socket.connect', _forbidden)
    monkeypatch.setattr('socket.socket.connect_ex', _forbidden)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', _forbidden)

    factory = ExecutionServiceFactory({'selected-api': CONFIG}, {}, 2, 3, .5,
        log_window_bytes=WINDOW_BYTES, log_roles=('stdout',))
    api_assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'selected-api',
        'service': 'bvbrc_appservice', 'request': request(),
        'endpoint': 'usable_handoff', 'constraints': {}}
    launch = launch_assignment({'selected-api': api_assignment})
    handoff_form, requested_monitor_form = form('execution_handoff_refs'), _monitor_form()

    def host(store, choices):
        workflow = Workflow(store, ToolRegistry(store, clients=Client()), choices, tmp_path / 'run',
            'appservice-monitor-shared-workflow', controller_factory=_controllers,
            project_credit=lambda *_: 0, episode_service_factory=factory,
            episode_service_binding=factory.as_record(), episode_service_inputs='actual_tool_registry_v1',
            annotation_child_roles=('launch', 'monitor'),
            episode_record_receipts=True, initial_known_record_refs=[])
        choices.workflow = workflow
        return workflow

    class Choices:
        def __init__(self):
            self.counts, self.contexts, self.released = {}, [], []

        def last(self, episode_id):
            row = self.workflow.store.db.execute('SELECT result FROM runtime_actions '
                'WHERE run_id=? AND episode_id=? AND result IS NOT NULL '
                'ORDER BY decision_index DESC LIMIT 1', (self.workflow.run_id, episode_id)).fetchone()
            return json.loads(row['result'])['result']

        async def complete(self, episode_id, role, instructions, current, schema):
            assert current.get('feedback') is None, current.get('feedback')
            self.contexts.append((episode_id, deepcopy(current)))
            count = self.counts[episode_id] = self.counts.get(episode_id, 0) + 1
            execution = current.get('execution_assignment', {})
            if execution.get('version') == 'execution_launch_assignment_v1':
                assert count == 1
                return child('launch_api', api_assignment, scope, handoff_form)
            if execution.get('version') == 'api_service_assignment_v1':
                if count == 1:
                    return selected(PREFIX + 'prepare', {'definition': {
                        'kind': 'packaged', 'required_application_id': 'Homology'}})
                assert count == 2
                return selected(PREFIX + 'submit', {'preparation_receipt_ref':
                    self.last(episode_id)['support_receipt_ref'], 'input_evidence_refs': []})
            if 'monitor_assignment' in current:
                assert current['monitor_assignment']['target_handle'] == self.handoff
                catalog = {entry['name']: entry for entry in current['tools']}
                assert catalog['progress.observe']['input_schema']['properties']['native_operation']['enum'] == [
                    'query_tasks', 'stdout', 'stderr']
                if count == 1:
                    return selected('progress.observe', {'requested_fields': ['execution_status', 'measurements'],
                        'native_operation': 'query_tasks'})
                assert count == 2
                previous = self.last(episode_id)
                assert previous['execution_status']['lifecycle_state'] == 'executing'
                assert previous['execution_status']['native']['native']['native_timing'] == TIMING
                assert previous['log_windows'] == []
                return selected('progress.observe', {'requested_fields': ['execution_status', 'log_windows'],
                    'native_operation': 'stdout'})
            assert current['tools'] == []  # Scientific root never receives execution tools.
            if count == 1:
                return child('launch', launch, scope, handoff_form)
            assert count == 2
            received = current['child_reports'][-1]
            assert received['completed']
            assert received['yield']['expected_next_gain'] == NumericBand.exact(0).as_record()
            self.handoff, = received['references']
            return child('monitor', monitor_assignment(self.handoff, FIELDS), scope, requested_monitor_form)

        async def release(self, episode_id):
            self.released.append(episode_id)

    project = AppServiceMonitor._project
    def interrupt_after_retained_response(self, intent, response, snapshot, service):
        if intent['native_operation'] == 'stdout':
            assert snapshot.content == LOG and response['failure'] is None
            raise KeyboardInterrupt('controlled interruption after original stdout response retention')
        return project(self, intent, response, snapshot, service)

    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='ACGT', molecule='dna')['subject_refs']
        scope = {'subject_refs': [target]}
        choices = Choices()
        workflow = host(store, choices)
        monkeypatch.setattr(AppServiceMonitor, '_project', interrupt_after_retained_response)
        with pytest.raises(KeyboardInterrupt, match='after original stdout response retention'):
            _run(workflow, scope)
        monkeypatch.setattr(AppServiceMonitor, '_project', project)
        incomplete = store.db.execute("SELECT episode_id,decision_index,action,result FROM runtime_actions "
            "WHERE json_extract(action,'$.arguments.native_operation')='stdout'").fetchone()
        assert incomplete['result'] is None
        monitor_id = incomplete['episode_id']
        stdout_key = f'{workflow.run_id}:{monitor_id}:{incomplete["decision_index"]}'
        api = workflow.progress_provider.job_provider.targets.api_execution
        stdout_dir = api.directory / 'observations' / digest(stdout_key)
        assert (stdout_dir / 'response.json').is_file() and not (stdout_dir / 'observation.json').exists()
        retained = json.loads((stdout_dir / 'response.json').read_text())
        assert api._load_snapshot(retained['snapshot']).content == LOG
        before = _rows(store, 'runtime_observations', 'episode_id,unit_index,observation', 'episode_id,unit_index')
        assert len(before) == 5  # Root launch, launch child, prepare+submit, status.
        assert len(choices.contexts) == 7
        calls = deepcopy(native.calls)
        assert [row[1]['method'] if row[0] == 'rpc' else row[0] for row in calls] == [
            'AppService.start_app2', 'AppService.query_tasks', 'task_info']
        assert calls[-1] == ('task_info', '123', 'stdout')

    # Reopen the actual durable Store. Every model choice and native response
    # already exists; recovery must neither decide again nor issue again.
    monkeypatch.setattr(native, 'rpc', _forbidden)
    monkeypatch.setattr(native, 'task_info', _forbidden)
    with Store(tmp_path / 'state') as store:
        resumed_choices = Choices()
        monkeypatch.setattr(resumed_choices, 'complete', _forbidden)
        workflow = host(store, resumed_choices)
        record = _run(workflow, scope)
        archived = json.loads(''.join(iter_json(record.as_record())))
        launch_record, monitor_record = [unit['child'] for unit in archived['units']]
        api_record = launch_record['units'][0]['child']
        assert record.units_consumed == monitor_record['units_consumed'] == api_record['units_consumed'] == 2
        assert launch_record['units_consumed'] == 1
        assert monitor_record['episode_id'] == monitor_id
        for completed in (launch_record, api_record):
            assert completed['ended_by'] == 'yield_stop'
            assert completed['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
            assert completed['units'][-1]['controller_step']['marginal_credit'] == 2
        assert [unit['controller_step']['marginal_credit'] for unit in api_record['units']] == [0, 2]
        observations = _rows(store, 'runtime_observations', 'episode_id,unit_index,observation', 'episode_id,unit_index')
        assert len(observations) == 7 and all(row in observations for row in before)
        own = [json.loads(row[2]) for row in observations if row[0] == monitor_id]
        assert [row['decision_index'] for row in own] == [0, 1]
        assert [row['step']['marginal_credit'] for row in own] == [.5, .5]
        assert all('practical_completion' not in row['credit'] for row in own)
        assert store.count('annotation') == store.count('observation') == 0

        root_id = archived['episode_id']
        returned = json.loads(workflow.journal.row('runtime_forms', monitor_id)['form'])
        admitted = store.db.execute('SELECT form,contract,failure FROM runtime_report_attempts '
            'WHERE parent_episode_id=? AND decision_index=1', (root_id,)).fetchone()
        assert admitted['failure'] is None and json.loads(admitted['form']) == returned
        assert set(returned) == set(requested_monitor_form['properties'])
        assert returned['target'] == choices.handoff
        assert returned['latest_state'] is None  # stdout did not observe current state.
        assert returned['latest_observed_at'] == datetime.fromisoformat(LOG_STAMP).timestamp()
        assert returned['result_available'] is False and len(returned['progress']) == 2
        assert workflow.progress_provider.received_progress_refs(root_id) == returned['progress']
        snapshots = [workflow.progress_provider.read_progress(ref, scope) for ref in returned['progress']]
        status, log = snapshots
        assert all(row['target_handle'] == choices.handoff for row in snapshots)
        assert status['observed_at'] == STAMP and status['execution_status']['execution_id'] == '123'
        assert status['execution_status']['lifecycle_state'] == 'executing'
        native_status = status['execution_status']['native']['native']
        assert native_status['state_observed'] is True and native_status['native_status'] == 'running'
        assert native_status['native_timing'] == TIMING
        assert native_status['timing_representation'] == {
            'timestamp_timezone': None, 'elapsed_time_unit': 'SQL_TIMEDIFF'}
        assert native_status['transport']['duration_measure'] == 'client_http_request_turnaround'
        assert native_status['transport']['http_turnaround_seconds'] == .25
        assert status['measurements'] == status['log_windows'] == []
        native_log = log['execution_status']['native']['native']
        assert native_log['state_observed'] is False and 'native_timing' not in native_log
        assert 'execution_state_not_observed' in native_log['qualification_codes']
        assert log['execution_status']['lifecycle_state'] is None and log['measurements'] == []
        assert log['execution_status']['native']['logs'] == []
        for fields in (native_status, native_log):
            assert fields['handle'] == {'task_id': '123'}
            assert not {'task_records', 'parameters', 'text', 'data', 'bytes_base64'} & fields.keys()
        assert native_log['log_offset_basis'] == 'retained_response_bytes'
        assert native_log['transport']['received_body_bytes'] == len(LOG)
        assert native_log['transport']['body_complete'] is True
        assert native_log['transport']['http_turnaround_seconds'] == .125
        source = store.get(native_log['source_ref'])
        assert source['provider'] == PROVIDER and source['parent_source_refs'] == [choices.handoff]
        assert store.get_artifact(source['artifact_ref']) == LOG
        window, = log['log_windows']
        assert store.get_artifact(window['artifact_ref']) == LOG[-WINDOW_BYTES:]
        assert (window['start_byte'], window['end_byte']) == (0, WINDOW_BYTES)
        assert window['content_sha256'] == hashlib.sha256(LOG[-WINDOW_BYTES:]).hexdigest()
        log_source = store.get(window['source_ref'])
        metadata = json.loads(store.get_artifact(log_source['request_ref']))
        assert metadata['role'] == 'stdout'
        assert metadata['original_start_byte'] == len(LOG) - WINDOW_BYTES
        assert metadata['original_end_byte'] == metadata['observed_file_size'] == len(LOG)

        # The typed parent contract and each monitor choice are original saved
        # records, including the exact field subset and native primitive.
        request_record = json.loads(workflow.journal.row('runtime_episodes', monitor_id)['request'])
        assert request_record['report_contract']['measurements']['schema'] == requested_monitor_form
        api = workflow.progress_provider.job_provider.targets.api_execution
        handoff = api.appservice.read_handoff(choices.handoff, scope)['task_handoff']
        assert handoff['original_task']['task_id'] == '123'
        assert handoff['original_task']['submission_operation_key'] == f'{workflow.run_id}:{api_record["episode_id"]}:1'
        assert handoff['original_job_owner']['run_id'] == workflow.run_id
        assert handoff['original_job_owner']['launch_episode_id'] == launch_record['episode_id']
        assert handoff['original_job_owner']['parent_commission_operation_key'] == f'{workflow.run_id}:{root_id}:0'
        for index, (choice, fields) in enumerate([
                ('query_tasks', ['execution_status', 'measurements']),
                ('stdout', ['execution_status', 'log_windows'])]):
            row = workflow.journal.row('runtime_actions', monitor_id, index)
            expected = {'kind': 'tool', 'tool': 'progress.observe',
                'arguments': {'native_operation': choice, 'requested_fields': fields}}
            assert json.loads(row['action']) == expected
            key = f'{workflow.run_id}:{monitor_id}:{index}'
            intent = json.loads((api.directory / 'observations' / digest(key) / 'intent.json').read_text())
            assert intent['operation_key'] == key and intent['native_operation'] == choice
            assert intent['arguments'] == expected['arguments']
            assert intent['observation_context']['role'] == 'monitor'
            assert intent['observation_context']['request'] == request_record
            assert intent['prepared']['bound_inputs']['resolved']['original_task'] == handoff['original_task']
            assert intent['prepared']['bound_inputs']['original_job_owner'] == handoff['original_job_owner']
            assert json.loads(row['result'])['result'] == snapshots[index]

        # Closed-history replay also performs no implicit polling at admission,
        # report construction, estimator refresh or final closure.
        forms = _rows(store, 'runtime_forms', 'episode_id,facts,form', 'episode_id')
        again_choices = Choices()
        monkeypatch.setattr(again_choices, 'complete', _forbidden)
        again = host(store, again_choices)
        replayed = _run(again, scope)
        assert json.loads(''.join(iter_json(replayed.as_record()))) == archived
        assert _rows(store, 'runtime_observations', 'episode_id,unit_index,observation', 'episode_id,unit_index') == observations
        assert _rows(store, 'runtime_forms', 'episode_id,facts,form', 'episode_id') == forms
        assert native.calls == calls
        assert resumed_choices.contexts == again_choices.contexts == []
