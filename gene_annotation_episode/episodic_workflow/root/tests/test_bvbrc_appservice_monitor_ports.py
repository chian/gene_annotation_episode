"""Explicit AppService monitor selection through the existing monitor ports.

The strict API reader below is synthetic. These checks exercise real Store,
monitor, provider, descriptor and retained-log paths, but establish neither
native AppService transport nor its complete host custody/episode integration.
"""
import asyncio
import base64
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest
from method_loop.durable import DurableExecutionStore, content_digest

from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_monitoring import FIELDS, MonitorEpisodes, ProgressProvider
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_progress import ExecutionProgressProvider
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_bvbrc_appservice import CONFIG, original_request, original_task, result_selector


RUN = 'monitor-ports-run'
STAMP = '2026-10-24T12:00:00+00:00'
NATIVE = ('query_tasks', 'stdout', 'stderr')
LOG_BYTES = b'complete retained response\x00\n'


def observation(target, native_operation='query_tasks', *, log=LOG_BYTES):
    selected_log = native_operation in ('stdout', 'stderr')
    return {'observed_at': STAMP, 'state': 'unknown' if selected_log else 'running',
        'returncode': None, 'failure_code': None, 'result_available': False,
        'measurements': [],
        'outputs': [{'role': native_operation, 'available': True,
            'bytes': len(log), 'writer_closed': False}] if selected_log else [],
        'logs': [{'role': native_operation, 'path': 'task_info/task-123/'+native_operation,
            'offset': 0, 'observed_size': len(log),
            'bytes_base64': base64.b64encode(log).decode()}] if selected_log else [],
        'provenance_refs': [target['handle']],
        'native': {'service': target['assignment']['service'],
            'native_operation': native_operation,
            'qualification_codes': ['execution_state_not_observed',
                'signature_redacted_representation'] if selected_log else []}}


class StrictAPIReader:
    """Require the exact frozen selected monitor action at the final port."""
    def __init__(self, store, target, body, configuration):
        self.store, self.target, self.body = store, target, body
        self.calls, self.handoff_reads = [], 0
        self.log_bytes = LOG_BYTES
        self.services = {'synthetic-api': BVBRCAppServiceService(
            SimpleNamespace(store=store), configuration)}

    def scope(self, handle):
        if handle != self.target['handle']:
            raise ValueError('not_a_synthetic_handoff')
        return deepcopy(self.target['scope'])

    def read_target(self, handle, scope):
        if handle != self.target['handle']:
            raise ValueError('not_a_synthetic_handoff')
        assert plain(scope) == self.target['scope']
        return deepcopy(self.target)

    def _read_handoff(self, handle, scope):
        self.read_target(handle, scope)
        self.handoff_reads += 1
        return deepcopy(self.body)

    def observe_target(self, target, *, operation_key, native_operation=None,
                       observation_context=None):
        assert target == self.target
        assert native_operation in NATIVE
        assert isinstance(observation_context, BindingContext)
        context = observation_context
        assert context.run_id == RUN and context.role == 'monitor'
        assert context.assignment['target_handle'] == target['handle']
        prefix = RUN+':'+context.episode_id+':'
        assert operation_key.startswith(prefix)
        index = int(operation_key.removeprefix(prefix))
        selected = self.store.db.execute('SELECT action FROM runtime_actions WHERE '
            'run_id=? AND episode_id=? AND decision_index=?',
            (RUN, context.episode_id, index)).fetchone()
        assert selected is not None
        action = json.loads(selected['action'])
        assert action['kind'] == 'tool' and action['tool'] == 'progress.observe'
        assert set(action['arguments']) == {'requested_fields', 'native_operation'}
        assert action['arguments']['native_operation'] == native_operation
        assert set(action['arguments']['requested_fields']) <= set(context.assignment['requested_fields'])
        self.calls.append({'target': deepcopy(target), 'operation_key': operation_key,
            'native_operation': native_operation, 'observation_context': context})
        return observation(target, native_operation, log=self.log_bytes)


class OldAPIReader:
    """The old keyword-only signature intentionally accepts no new kwargs."""
    def __init__(self, target):
        self.target, self.calls = target, []
        self.services = {'synthetic-api': SimpleNamespace(
            service=target['assignment']['service'], capabilities=lambda: [],
            result_catalog=lambda request, selector: [])}

    def read_target(self, handle, scope):
        if handle != self.target['handle']:
            raise ValueError('not_a_synthetic_handoff')
        assert plain(scope) == self.target['scope']
        return deepcopy(self.target)

    def observe_target(self, target, *, operation_key):
        assert target == self.target
        self.calls.append(operation_key)
        return observation(target)


@pytest.fixture
def harness(tmp_path):
    with Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        scope = store.validate_scope({'subject_refs': store.problem()['subject_refs']})
        journal = Journal(store, RUN)
        tools = ToolRegistry(store)
        def build(service='bvbrc_appservice'):
            request = original_request() if service == 'bvbrc_appservice' else (
                {'mode': 'genome_distance'} if service == 'bvbrc_minhash' else {'program': 'blastp'})
            assignment = {'version': 'api_service_assignment_v1', 'service': service,
                'resource_id': 'synthetic-api', 'endpoint': 'usable_handoff',
                'request': request, 'constraints': {}}
            called = ('api.bvbrc_appservice.submit' if service == 'bvbrc_appservice'
                else 'api.bvbrc.minhash.search' if service == 'bvbrc_minhash' else 'api.blast.submit')
            body = {'scope': scope, 'assignment': assignment, 'episode_id': 'launch-child',
                'receipt': {'tool_name': called, 'name': called,
                    'operation_key': RUN+':launch-child:3', 'state': 'submitted'},
                'snapshot': {'media_type': 'application/json'}}
            if service == 'bvbrc_appservice':
                source = store._caller_source({'version': 'bvbrc_appservice_retained_receipt_v1',
                    'contract': 'TaskHandoff', 'value': {'synthetic_fixture': True}},
                    'episode.bvbrc_appservice_receipt')
                body['task_handoff'] = {'original_task': original_task(request),
                    'definition_evidence': {'content': {'source_ref': source['id'],
                        'artifact_ref': source['artifact_ref'], 'artifact_field': 'artifact_ref'},
                        'pointer': '/synthetic_definition'}}
                configuration = deepcopy(CONFIG)
            else:
                source = store._caller_source(body, 'synthetic_old_handoff')
                configuration = {'kind': 'api', 'service': service}
            target = {'version': 'execution_target_v1', 'handle': source['id'],
                'run_id': RUN, 'resource_id': 'synthetic-api', 'resource_kind': 'api',
                'execution_id': 'task-123', 'request_sha256': digest(assignment),
                'origin_episode_id': 'launch-child', 'assignment': assignment, 'scope': scope}
            api = (StrictAPIReader(store, target, body, configuration)
                if service == 'bvbrc_appservice' else OldAPIReader(target))
            resources = {'synthetic-api': configuration}
            native = ExecutionProgressProvider(store, run_id=RUN, directory=tmp_path/service,
                resources=resources, api_execution=api, log_window_bytes=8192,
                log_roles=('stdout', 'stderr'))
            progress = ProgressProvider(store, DurableExecutionStore(tmp_path/('durable-'+service)),
                run_id=RUN, job_provider=native)
            workflow = SimpleNamespace(run_id=RUN, store=store, tools=tools,
                progress_provider=progress)
            workflow.progress_selection = lambda context: {'known_progress_refs':
                list(dict.fromkeys([*context.assignment['known_progress_refs'],
                    *progress.received_progress_refs(context.episode_id)]))}
            services = WorkflowServices(workflow)
            monitor = MonitorEpisodes(services)
            value = {'version': 'monitor_assignment_v1', 'target_handle': target['handle'],
                'requested_fields': list(FIELDS), 'known_progress_refs': [],
                'permitted_committed_record_types': []}
            request = {'message': {'scope': scope, 'episode_assignment': value}}
            context = BindingContext(RUN, 'monitor-'+service, 'monitor',
                (('annotation', 'root'), ('monitor', service)), scope, value, request)
            with store.transaction():
                journal.save('runtime_episodes', {'episode_id': context.episode_id,
                    'path': canonical(plain(context.path)), 'request': canonical(request),
                    'initial_credit': 0, 'state': 'running'})
            return SimpleNamespace(store=store, scope=scope, journal=journal,
                target=target, api=api, native=native, progress=progress, services=services,
                monitor=monitor, context=context)
        yield build


def select(h, native_operation, *, index=0, fields=FIELDS):
    arguments = {'requested_fields': list(fields)}
    if native_operation is not None:
        arguments['native_operation'] = native_operation
    key = RUN+':'+h.context.episode_id+':'+str(index)
    with h.store.transaction():
        h.journal.save('runtime_actions', {'episode_id': h.context.episode_id,
            'decision_index': index,
            'action': canonical({'kind': 'tool', 'tool': 'progress.observe', 'arguments': arguments}),
            'result': None, 'credit': None})
    return key, arguments


@pytest.mark.parametrize('native_operation', NATIVE)
def test_exact_selection_and_context_reach_strict_api_once_and_replay(harness, native_operation, monkeypatch):
    h = harness()
    key, arguments = select(h, native_operation)
    outcome = asyncio.run(h.monitor.execute(h.context, 'progress.observe', arguments, key))
    assert outcome['status'] == 'completed'
    assert len(h.api.calls) == 1
    assert h.api.calls[0]['operation_key'] == key
    assert h.api.calls[0]['target'] == h.target
    assert h.api.calls[0]['native_operation'] == native_operation
    assert h.api.calls[0]['observation_context'] is h.context
    selected = h.store.db.execute('SELECT selection,signature FROM runtime_progress_selections '
        'WHERE run_id=? AND operation_key=?', (RUN, key)).fetchone()
    value = json.loads(selected['selection'])
    assert value['native_operation'] == native_operation
    assert value['observation_context'] == h.context.as_record()
    assert selected['signature'] == content_digest(value)
    expected = {'operation': 'observe', 'handle': h.target['handle'], 'fields': list(FIELDS),
        'scope': h.scope, 'native_operation': native_operation,
        'observation_context': h.context.as_record()}
    native_row = h.store.db.execute('SELECT signature FROM runtime_execution_progress_operations '
        'WHERE run_id=? AND operation_key=?', (RUN, key)).fetchone()
    assert native_row['signature'] == digest({'selection': expected, 'provider': h.native.as_record()})
    def forbid(*args, **kwargs):
        pytest.fail('replay must not open the target or call the native reader')
    monkeypatch.setattr(h.progress, '_target', forbid)
    monkeypatch.setattr(h.native.targets, 'read_target', forbid)
    monkeypatch.setattr(h.api, 'observe_target', forbid)
    assert h.services.observe_progress(h.target['handle'], FIELDS, h.scope, operation_key=key,
        native_operation=native_operation, observation_context=h.context) == outcome['result']
    raw = h.native.observe(h.target['handle'], FIELDS, h.scope, operation_key=key,
        native_operation=native_operation, observation_context=h.context)
    assert raw['execution_status'] == outcome['result']['execution_status']
    assert h.store.db.execute('SELECT count(*) FROM runtime_progress_selections').fetchone()[0] == 1
    assert h.store.db.execute('SELECT count(*) FROM runtime_execution_progress_operations').fetchone()[0] == 1


@pytest.mark.parametrize('native_operation', [None, '', 'status', 'task_info', 'STDOUT', 3, ['stdout']])
def test_new_target_rejects_missing_or_invalid_native_selection_without_observation(harness, native_operation):
    h = harness()
    key, arguments = select(h, native_operation)
    outcome = asyncio.run(h.monitor.execute(h.context, 'progress.observe', arguments, key))
    assert outcome['status'] == 'invalid'
    assert outcome['progress_refs'] == [] and h.api.calls == []
    assert h.store.db.execute('SELECT count(*) FROM runtime_progress_selections').fetchone()[0] == 0


def test_missing_native_choice_rejected_at_direct_provider_and_reader_ports(harness):
    h = harness()
    for call in (
        lambda: h.native.observe(h.target['handle'], FIELDS, h.scope, operation_key='direct'),
        lambda: h.native.targets.observe_target(h.target, operation_key='direct'),
        lambda: h.progress.observe(h.target['handle'], FIELDS, h.scope, operation_key='direct')):
        with pytest.raises(ContractError, match='native_operation_required'):
            call()
    assert h.api.calls == []


def test_native_context_is_required_and_is_internal_only(harness):
    h = harness()
    key, arguments = select(h, 'query_tasks')
    for context in (None, h.context.as_record()):
        with pytest.raises(ContractError, match='observation_context_required'):
            h.services.observe_progress(h.target['handle'], FIELDS, h.scope, operation_key=key,
                native_operation='query_tasks', observation_context=context)
    result = asyncio.run(h.monitor.execute(h.context, 'progress.observe', arguments, key))
    assert result['status'] == 'completed'
    assert 'observation_context' not in canonical(result)
    assert 'observation_context' not in canonical(h.monitor.catalog(h.context))


@pytest.mark.parametrize('change', ['native_operation', 'context', 'fields', 'target'])
def test_changed_selection_conflicts_in_both_durable_provider_layers(harness, change):
    h = harness()
    key, arguments = select(h, 'stdout')
    assert asyncio.run(h.monitor.execute(h.context, 'progress.observe', arguments, key))['status'] == 'completed'
    operation, context, fields, target = 'stdout', h.context, list(FIELDS), h.target['handle']
    if change == 'native_operation':
        operation = 'stderr'
    elif change == 'context':
        context = replace(context, episode_id='another-monitor')
    elif change == 'fields':
        fields = ['execution_status']
    else:
        target = 'different-target'
    for provider in (h.progress, h.native):
        with pytest.raises(ContractError, match='operation_identity_conflict'):
            provider.observe(target, fields, h.scope, operation_key=key,
                native_operation=operation, observation_context=context)
    assert len(h.api.calls) == 1


@pytest.mark.parametrize('service', ['ncbi_blast', 'bvbrc_minhash'])
def test_old_targets_keep_exact_schema_signature_and_keyword_omission(harness, service):
    h = harness(service)
    key, arguments = select(h, None)
    catalog = h.monitor.catalog(h.context)
    expected_schema = obj({'requested_fields': {'type': 'array',
        'items': {'enum': list(FIELDS)}, 'uniqueItems': True}})
    assert catalog[0]['input_schema'] == expected_schema
    for native in NATIVE:
        result = asyncio.run(h.monitor.execute(h.context, 'progress.observe',
            {**arguments, 'native_operation': native}, key))
        assert result['status'] == 'invalid'
    outcome = asyncio.run(h.monitor.execute(h.context, 'progress.observe', arguments, key))
    assert outcome['status'] == 'completed' and h.api.calls == [key]
    old_selection = {'target_handle': h.target['handle'], 'requested_fields': list(FIELDS),
        'scope': h.scope, 'permitted_committed_record_types': []}
    selected = h.store.db.execute('SELECT selection,signature FROM runtime_progress_selections '
        'WHERE run_id=? AND operation_key=?', (RUN, key)).fetchone()
    assert selected['selection'] == canonical(old_selection)
    assert selected['signature'] == content_digest(old_selection)
    old_native = {'operation': 'observe', 'handle': h.target['handle'], 'fields': list(FIELDS), 'scope': h.scope}
    native_row = h.store.db.execute('SELECT signature FROM runtime_execution_progress_operations '
        'WHERE run_id=? AND operation_key=?', (RUN, key)).fetchone()
    assert native_row['signature'] == digest({'selection': old_native, 'provider': h.native.as_record()})
    for provider in (h.progress, h.native):
        with pytest.raises(ContractError, match='native_operation_not_supported'):
            provider.observe(h.target['handle'], FIELDS, h.scope, operation_key=key+':new',
                native_operation='stdout', observation_context=h.context)
    with pytest.raises(ContractError, match='native_operation_not_supported'):
        h.native.targets.observe_target(h.target, operation_key=key+':direct',
            native_operation='stdout', observation_context=h.context)
    assert h.api.calls == [key]


@pytest.mark.parametrize('invalid_utf8', [False, True])
def test_log_only_projection_stays_unknown_and_log_read_uses_retained_bytes(harness, invalid_utf8):
    h = harness()
    if invalid_utf8:
        h.api.log_bytes += b'\xff'
    key, arguments = select(h, 'query_tasks')
    earlier = asyncio.run(h.monitor.execute(h.context, 'progress.observe', arguments, key))
    assert earlier['result']['execution_status']['lifecycle_state'] == 'executing'
    earlier_copy = deepcopy(earlier)
    key, arguments = select(h, 'stdout', index=1)
    outcome = asyncio.run(h.monitor.execute(h.context, 'progress.observe', arguments, key))
    snapshot = outcome['result']
    assert snapshot['execution_status']['lifecycle_state'] is None
    assert snapshot['execution_status']['native']['state'] == 'unknown'
    assert snapshot['execution_status']['native']['native']['qualification_codes'] == [
        'execution_state_not_observed', 'signature_redacted_representation']
    assert snapshot['result_available'] is False and snapshot['measurements'] == []
    assert snapshot['execution_status']['native']['logs'] == []
    h.progress.receive_outcome(h.context.episode_id, outcome, h.scope, key)
    context = replace(h.context, assignment={**plain(h.context.assignment),
        'known_progress_refs': [snapshot['progress_ref']]})
    returned = asyncio.run(h.monitor.execute(context, 'progress.log',
        {'progress_ref': snapshot['progress_ref'], 'log_index': 0}, key+':log'))
    if invalid_utf8:
        assert returned['status'] == 'invalid'
        assert returned['feedback']['code'] == 'source_not_utf8_text'
    else:
        assert returned['status'] == 'completed', returned.get('feedback')
        assert returned['result']['text'].startswith('complete retained response')
    window, = snapshot['log_windows']
    assert h.store.get_artifact(window['artifact_ref']) == h.api.log_bytes
    assert len(h.api.calls) == 2 and earlier == earlier_copy
    assert h.progress.read_progress(earlier['result']['progress_ref'], h.scope) == earlier['result']


@pytest.mark.parametrize('fields', [['execution_status'], ['log_windows']])
def test_appservice_status_projection_never_contains_raw_log_bytes(harness, fields):
    h = harness()
    key, arguments = select(h, 'stdout', fields=fields)
    result = asyncio.run(h.monitor.execute(h.context, 'progress.observe', arguments, key))
    assert result['status'] == 'completed'
    snapshot = result['result']
    status = snapshot['execution_status']['native']
    assert status['state'] == 'unknown' and status['logs'] == []
    assert 'bytes_base64' not in canonical(snapshot)
    if fields == ['execution_status']:
        assert snapshot['log_windows'] == [] and status['outputs'] == []
    else:
        assert len(snapshot['log_windows']) == 1
    # Projection never destroys the original response or changes its capture.
    status_source = next(h.store.get(ref) for ref in snapshot['provenance_refs']
        if ref.startswith('source_') and h.store.get(ref)['provider'] == 'execution.progress.status')
    retained = json.loads(h.store.get_artifact(status_source['artifact_ref']))
    assert base64.b64decode(retained['observation']['logs'][0]['bytes_base64']) == LOG_BYTES
    assert len(h.api.calls) == 1


def test_descriptor_uses_authenticated_handoff_and_distinguishes_support_from_publication(harness):
    h = harness()
    descriptor = h.native.targets.describe_target(h.target['handle'], h.scope, selector=result_selector())
    assert h.api.handoff_reads == 1 and h.api.calls == []
    assert descriptor['called_operation'] == 'api.bvbrc_appservice.submit'
    assert descriptor['required_application_id'] == descriptor['native_application_id'] == 'Homology'
    assert descriptor['submitted_parameters'] == h.target['assignment']['request']['parameters']
    assert descriptor['definition_evidence'] == h.api.body['task_handoff']['definition_evidence']
    assert descriptor['selected_observation_schema']['properties']['native_operation']['enum'] == list(NATIVE)
    for value in NATIVE:
        validate_schema({'native_operation': value}, descriptor['selected_observation_schema'])
    assert descriptor['configured_scientific_adapters'] == []
    assert descriptor['log_format']['state_observed'] is False
    assert descriptor['log_format']['representation'] == 'signature_redacted_http_bytes'
    assert descriptor['native_states']['query_tasks_mapping']['running'] == 'running'
    assert descriptor['native_states']['log_observation_state'] == 'unknown'
    assert descriptor['progress_measurements']['derived_duration_seconds'] == []
    assert descriptor['progress_measurements']['timezone'] is None
    extractors = descriptor['extractors']
    for row in extractors:
        if row['operation'].startswith('api.') and row['operation'] != 'api.bvbrc_appservice.download':
            assert row['purpose'] == 'support'
            assert row['return_fact_sources'] == [] and row['implementation'].endswith('.decode')
    download, = [row for row in extractors if row['operation'] == 'api.bvbrc_appservice.download']
    assert download['scientific_parser'] is None
    assert download['scientific_publication_requires_explicit_bound_adapter']


def test_new_target_requires_both_request_and_resource_version_markers(harness):
    h = harness()
    h.native.targets.resources['synthetic-api'].pop('execution_contract')
    with pytest.raises(ContractError, match='execution_target_unavailable_or_outside_scope'):
        h.native.targets.read_target(h.target['handle'], h.scope)
    h.native.targets.resources['synthetic-api']['execution_contract'] = 'bvbrc_appservice_execution_v1'
    h.api.target['assignment']['request'].pop('effect_contract')
    with pytest.raises(ContractError, match='execution_target_unavailable_or_outside_scope'):
        h.native.targets.read_target(h.target['handle'], h.scope)
    assert h.api.calls == []


def test_missing_appservice_binding_does_not_describe_a_different_service(harness):
    h = harness()
    h.api.services.clear()
    with pytest.raises(ContractError, match='bvbrc_appservice_service_not_bound'):
        h.native.describe_target(h.target['handle'], h.scope)
    assert h.api.calls == []


def test_saved_native_capture_survives_later_monitor_publication_failure(harness, monkeypatch):
    h = harness()
    key, arguments = select(h, 'stderr')
    validate = h.progress._validate_exposed
    def interrupt(*args, **kwargs):
        raise ContractError('synthetic_monitor_publication_interrupted')
    monkeypatch.setattr(h.progress, '_validate_exposed', interrupt)
    outcome = asyncio.run(h.monitor.execute(h.context, 'progress.observe', arguments, key))
    assert outcome['status'] == 'invalid' and len(h.api.calls) == 1
    assert h.store.db.execute('SELECT count(*) FROM runtime_execution_progress_operations').fetchone()[0] == 1
    assert h.store.db.execute('SELECT count(*) FROM runtime_progress_selections').fetchone()[0] == 0
    monkeypatch.setattr(h.progress, '_validate_exposed', validate)
    def forbid(*args, **kwargs):
        pytest.fail('capture recovery must not invoke the native API again')
    monkeypatch.setattr(h.api, 'observe_target', forbid)
    resumed = asyncio.run(h.monitor.execute(h.context, 'progress.observe', arguments, key))
    assert resumed['status'] == 'completed'
    assert resumed['result']['execution_status']['native']['native']['native_operation'] == 'stderr'
    assert resumed['result']['observed_at'] == STAMP
    assert h.store.db.execute('SELECT count(*) FROM runtime_progress_selections').fetchone()[0] == 1


def test_appservice_dependency_reads_original_authenticated_handoff_projection(harness):
    h = harness()
    key = RUN+':launch-child:3'
    assignment = h.target['assignment']
    request = {'message': {'scope': h.scope, 'episode_assignment': assignment}}
    context = BindingContext(RUN, 'launch-child', 'launch_api',
        (('annotation', 'root'), ('launch_api', 'launch')), h.scope, assignment, request)
    outcome = {'status': 'completed', 'record_refs': [h.target['handle']], 'changed_record_refs': []}
    with h.store.transaction():
        h.journal.save('runtime_episodes', {'episode_id': context.episode_id,
            'path': canonical(plain(context.path)), 'request': canonical(request),
            'initial_credit': 0, 'state': 'running'})
        h.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': 3,
            'action': canonical({'kind': 'tool', 'tool': 'api.bvbrc_appservice.submit', 'arguments': {}}),
            'result': canonical(outcome), 'credit': None})
    relationship = h.native.dependency_from_outcome(context, outcome, key)
    assert relationship['handle'] == h.target['handle'] and relationship['state'] == 'pending'
    assert h.api.handoff_reads == 2 and h.api.calls == []
    assert h.native.dependency_from_outcome(context, outcome, key) == relationship
