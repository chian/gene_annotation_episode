"""Actual new caller/source loader and numerical detached reconstruction.

Only synthetic records, invented A/P instructions and scripted JSON-RPC run.
The actual YieldController owns closure; no public/native/model work occurs.
"""
import asyncio
from copy import deepcopy
import hashlib
from itertools import repeat
import json
import os
from pathlib import Path
import sys

import pytest

from gene_annotation_episode import api_planning_case_policy as caller_policy
from gene_annotation_episode import case_execution, independent_execution, tool_configuration
from gene_annotation_episode.api_timing_records import ApiTimingBinding
from gene_annotation_episode.case_execution import prepare_case_run, prepared_case_bindings, run_prepared_case
from gene_annotation_episode.credit import CreditPolicy
from gene_annotation_episode.domain import canonical, obj
from gene_annotation_episode.homology_jobs import HomologyJobs
from gene_annotation_episode.numerical import YieldController
from gene_annotation_episode.providers import ModelConnection
from gene_annotation_episode.public_search_operations import hmmer_client_binding_sha256
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.runtime import Workflow, assemble_workflow
from gene_annotation_episode.state import Store
from method_loop.archive import ArchivedRecord
from method_loop.durable import DurableExecutionError, DurableExecutionStore, content_digest
from test_api_execution_planning_connected import MARKER, synthetic_ap_source
from test_api_timing_reconstruction import BOOTSTRAP, fixture_tools
from test_assembled_case_reconstruction import wait_for_worker_exit
from test_assembled_service_setup import RETRIEVAL, ROOT_ROLES
from test_case_execution import prepared
from test_hmmer_api_progress import local_service
from test_homology_episode_runtime import Provider
from test_resource_receipt_reconstruction import BeforeRoot
from test_runtime import ScriptedProvider


TEST_COST = 1000000
MINIMUM_WINDOW = 8
TRANSPORT = r'''import json, os, sys
from pathlib import Path
log = Path(sys.argv[1])
def emit(value):
    print(json.dumps(value), flush=True)
for line in sys.stdin:
    message = json.loads(line)
    method, params = message.get('method'), message.get('params', {})
    if 'id' not in message:
        continue
    if method == 'initialize':
        result = {}
    elif method == 'thread/start':
        assert params['model'] == 'gpt-6-sol'
        assert params['config']['model_reasoning_effort'] == 'medium'
        result = {'thread': {'id': 'new-caller-fixture-thread'}, 'model': params['model'],
            'reasoningEffort': params['config']['model_reasoning_effort']}
    elif method == 'turn/start':
        context = json.loads(params['input'][0]['text'])
        assert 'scientific_process' in context
        assert context['current_credit'] == 0 and context['annotation_score'] == 0
        previous = context['last_local_outcome']
        if previous is None:
            assert 'api_execution_proposal' not in context
            action = {'kind': 'tool', 'tool': 'execution.estimate',
                'arguments': context['scientific_process']['assignment']['context']['estimate_input']}
        else:
            proposal = context['api_execution_proposal']
            assert proposal['api_reported_execution_forecasts'][0]['expected_total_seconds'] is None
            action = {'kind': 'tool', 'tool': 'episode.history',
                'arguments': {'view': 'records', 'decision_indices': [0]}}
        with log.open('a') as stream:
            stream.write(json.dumps({'pid': os.getpid(), 'context': context}) + '\n')
        response = {'selection': action, 'report_update': {}}
        emit({'id': message['id'], 'result': {'turn': {'id': 'new-caller-fixture-turn'}}})
        emit({'method': 'item/completed', 'params': {'threadId': params['threadId'],
            'item': {'type': 'agentMessage', 'text': json.dumps(response)}}})
        emit({'method': 'turn/completed', 'params': {'threadId': params['threadId'],
            'turn': {'id': 'new-caller-fixture-turn', 'status': 'completed'}}})
        continue
    else:
        raise AssertionError(method)
    emit({'id': message['id'], 'result': result})
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def forbidden(*_args, **_kwargs):
    raise AssertionError('This fixture cannot execute transport, HTTP or native work')


def parameters(directory, manifest, client, source, initial):
    """Explicit fixture operands; only cost is a test continuation threshold."""
    registry = {'version': 'public_search_registry_v1',
        'registry_ref': 'execution_registry_' + 'c' * 32,
        'resource_id': 'new-caller-engineering-fixture', 'provider': 'hmmer',
        'client_binding_sha256': hmmer_client_binding_sha256(client)}
    timing = ApiTimingBinding(ledger_path=directory / 'api-timing.sqlite',
        history_path=Path(manifest['configuration']['history']),
        resource_id=registry['resource_id'], monitoring_information_unit=1)
    return {'policy': {
        'scientific': CreditPolicy().as_record(), 'scientific_child': 'received_findings',
        'scientific_progress': {'finding_unit': 1, 'initial_known_record_refs': list(initial),
            'loss_preview_size': 24},
        'operational': {'registry_ref': manifest['registry_configuration']['registry_ref'],
            'handoff_unit': 1, 'acquired_record_unit': 1},
        'monitoring': {'information_unit': 1, 'include_handoff_checks': True},
        'controller': {'cost': TEST_COST, 'window_size': MINIMUM_WINDOW, 'subsample_size': 4,
            'uncertainty_alpha': .05, 'cost_by_role': {'job_launch': .1, 'job_monitor': .1}}},
        'services': {'version': caller_policy.VERSION, 'source_directory': str(source),
            'tool_retrieval': deepcopy(RETRIEVAL), 'scientific_child_roles': list(ROOT_ROLES),
            'annotation_child_roles': list(ROOT_ROLES),
            'execution_planning_roles': ['annotation', 'scientific_process'],
            'handoff_unit': 1, 'acquired_record_unit': 1, 'monitoring_information_unit': 1,
            'literature_outcome_page_size': 8, 'monitor_outcome_page_size': 32,
            'log_window_bytes': 16384, 'log_roles': ['native_stderr', 'native_text'],
            'public_search_registry': registry, 'api_timing': timing.as_record(),
            'api_execution_planning': deepcopy(MARKER)}}


@pytest.fixture
def caller(tmp_path, monkeypatch):
    with local_service() as (http, client):
        monkeypatch.setenv('GENE_EPISODE_HTTP_FIXTURE_BASE', client.base)
        bootstrap = tmp_path / 'fixture-bootstrap'
        bootstrap.mkdir()
        (bootstrap / 'sitecustomize.py').write_text(BOOTSTRAP)
        monkeypatch.syspath_prepend(str(bootstrap))
        original_builder = tool_configuration.build_tools

        def builder(store, configuration=None):
            return fixture_tools(original_builder, store, configuration)

        monkeypatch.setattr(tool_configuration, 'build_tools', builder)
        monkeypatch.setattr(case_execution, 'build_tools', builder)
        case, configuration, _unused_fixture_policy = prepared(tmp_path)
        configuration['history'] = str(tmp_path / 'statistics.sqlite')
        configuration['local_jobs'] = {'memory_bytes': 20 * 1024**3,
                                       'scratch_bytes': 4 * 1024**3}
        configuration['restoration'] = {'preview_size': 24,
            'model_presentation': 'bounded_wait_history_v1'}
        configuration['models']['FAST'] = {'model': 'gpt-6-luna', 'reasoning_effort': 'none'}
        configuration['models']['REASONING'] = {'model': 'gpt-6-sol', 'reasoning_effort': 'medium'}
        transport, turns = tmp_path / 'transport.py', tmp_path / 'turns.jsonl'
        compile(TRANSPORT, str(transport), 'exec')
        transport.write_text(TRANSPORT)
        configuration['models']['connection']['command'] = [sys.executable, str(transport), str(turns)]
        source = synthetic_ap_source(tmp_path / 'invented-ap')
        directory = tmp_path / 'run'
        manifest = prepare_case_run(case, directory, configuration)
        workspace = case / 'workspace'
        with Store(workspace) as store:
            initial = sorted(row[0] for row in store.db.execute(
                'SELECT id FROM inputs UNION SELECT id FROM records'))
        supplied = tmp_path / 'supplied-policy.py'
        actual_policy = Path(caller_policy.__file__)
        original_policy_bytes = actual_policy.read_bytes()
        supplied.write_bytes(original_policy_bytes)
        assert supplied.read_bytes() == actual_policy.read_bytes()
        assert sha(supplied) == sha(actual_policy)
        arguments = parameters(directory, manifest, client, source, initial)
        with monkeypatch.context() as patched:
            patched.setattr(Workflow, 'build', lambda *_a, **_k: (_ for _ in ()).throw(BeforeRoot()))
            patched.setattr(ModelConnection, '__aenter__', forbidden)
            patched.setattr(ModelConnection, 'complete', forbidden)
            patched.setattr(HomologyJobs, 'order', forbidden)
            patched.setattr(HomologyJobs, 'submit', forbidden)
            with pytest.raises(BeforeRoot):
                asyncio.run(run_prepared_case(directory, policy_file=supplied,
                    parameters=arguments, provider=Provider([])))
        saved = json.loads((directory / 'run.json').read_text())
        policy_marker = json.loads((directory / 'policy-binding.json').read_text())
        snapshot = directory / policy_marker['snapshot_file']
        assert snapshot.read_bytes() == original_policy_bytes
        assert policy_marker['source_sha256'] == sha(actual_policy)
        assert not turns.exists() and http.calls == []
        fixture = {'directory': directory, 'workspace': workspace, 'case': case,
            'manifest': manifest, 'run_id': saved['run_id'],
            'settings': {key: value for key, value in saved.items() if key != 'run_id'},
            'parameters': arguments, 'initial': initial, 'builder': builder, 'turns': turns,
            'policy': supplied, 'snapshot': snapshot, 'http': http,
            'actual_policy': actual_policy, 'actual_policy_sha256': sha(actual_policy)}
        yield fixture
        assert actual_policy.read_bytes() == original_policy_bytes


def reopen(fixture, store, options, provider):
    return assemble_workflow(store, fixture['builder'](store, fixture['manifest']['configuration']),
        provider, fixture['directory'], fixture['run_id'], fixture['settings'],
        **{key: value for key, value in options.items() if key != 'binding_definitions'})


def observations(store, run_id, episode_id):
    return [json.loads(row[0]) for row in store.db.execute(
        'SELECT observation FROM runtime_observations WHERE run_id=? AND episode_id=? ORDER BY unit_index',
        (run_id, episode_id))]


def assert_owner(workflow, fixture):
    planner = workflow.tools.api_execution_planner
    adapter = next(adapter for adapter in workflow.episode_bindings.for_role('launch').adapters.values()
                   if adapter.capability()['kind'] == 'api')
    assert planner.ports is adapter.ports is workflow.api_timing_reader.ports
    assert planner.timing is adapter.timing is workflow.api_timing_reader.ledger
    assert planner.store is adapter.store is workflow.store
    assert planner.ports.operations.remote_searches is workflow.tools.remote_searches
    assert planner.ports.result_publisher.tools is workflow.tools
    assert planner.resource_estimator is workflow.resource_estimator
    assert planner.run_id == fixture['run_id']
    assert workflow.resource_estimator.as_record() == ResourceToolEstimator.with_reported_results().as_record()
    settings = fixture['settings']
    assert settings['episode_application_services']['inputs'] == 'actual_tool_registry_v1'
    assert settings['episode_application_services']['definition'] == fixture['parameters']['services']
    assert workflow.episode_application_services_binding == settings['episode_application_services']
    assert workflow.episode_bindings.as_record() == settings['episode_bindings']
    catalog = [{'name': name, **entry} for name, entry in workflow.tools.catalog().items()]
    assert workflow.scientific_process_binding.tool_library.catalog() == sorted(catalog, key=lambda row: row['name'])
    assert settings['models'] == fixture['manifest']['configuration']['models']
    assert settings['restoration'] == fixture['manifest']['configuration']['restoration']
    assert settings['scientific_knowledge']['initial_known_record_refs'] == fixture['initial']
    controller = workflow.controller_factory((('scientific_process', 'fixture'),), 0)
    assert type(controller) is YieldController
    assert controller.cost == TEST_COST
    assert controller.settings.window_size == MINIMUM_WINDOW
    assert controller.settings.subsample_size == 4 and controller.settings.uncertainty_alpha == .05
    assert controller.estimator.estimate_with_context is None
    return planner


def assert_no_work(workflow, fixture):
    assert fixture['http'].calls == []
    assert workflow.store.db.execute('SELECT count(*) FROM provider_jobs').fetchone()[0] == 0
    assert workflow.job_episodes.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
    assert workflow.store.count('native_execution') == 0


def commission(fixture):
    with Store(fixture['workspace']) as store, prepared_case_bindings(store, fixture['directory']) as (_, options):
        workflow = reopen(fixture, store, options, ScriptedProvider([]))
        assert_owner(workflow, fixture)
        scope = {'subject_refs': [fixture['manifest']['target_ref']]}
        root = workflow.build('annotation', 'root', fixture['settings']['goal'], scope)
        product = json.loads((fixture['case'] / 'evidence-refs.json').read_text())['product_ref']
        sequence = store.get_artifact(store.get(product)['sequence_ref'])
        adapter = next(adapter for adapter in workflow.episode_bindings.for_role('launch').adapters.values()
                       if adapter.capability()['kind'] == 'api')
        estimate = {'tool': 'public.hmmer.search',
            'arguments': {'subject_ref': product, 'algorithm': 'phmmer', 'database': 'fixture'},
            'resource_selection': adapter.information.selection(), 'constraints': {'allowed_kinds': ['api']},
            'immutable_input_versions': [{'reference': product, 'version': None,
                'content_sha256': hashlib.sha256(sequence).hexdigest()}]}
        library = workflow.scientific_process_binding.library
        form = obj({'forecasts': deepcopy(workflow.report_sources('scientific_process')[
            'api_reported_execution_forecasts']['report_schema'])})
        selection = {'kind': 'episode_child', 'role': 'scientific_process',
            'goal': 'Read timing support for an explicitly proposed fixture search', 'scope': scope,
            'purpose': 'Return the original recorded execution-duration forecast',
            'schema_json': canonical(form), 'initial_report_json': '{}',
            'assignment': {'selection': {'version': 'scientific_process_selection_v2',
                'annotation_ref': library.reference('A01'), 'thought_ref': library.reference('P01'),
                'tools': ['execution.estimate']}, 'evidence_refs': [product],
                'constraints': {'engineering_fixture_only': True}, 'context': {'estimate_input': estimate}}}
        runtime_binding = independent_execution.make_runtime_binding(store, fixture['directory'], kind='fixed_case')
        workflow.configure_execution(runtime_binding)
        workflow.provider = ScriptedProvider([{'selection': selection, 'report_update': {}}])
        response, index, context, action_schema = asyncio.run(root.source.call(
            {'visible_record_refs': [], 'scope': scope}, workflow.action_schema(root.source)))
        chosen = root.source.apply_response(response, index, context, action_schema)
        assert chosen.decision_index == 0
        spec, = workflow.commissions.recover_selected(root.source.episode_id)
        workflow.execution_backend.commission(spec)
        fixture.update(spec=deepcopy(spec), form=deepcopy(form), estimate=deepcopy(estimate),
            root_request=root.request.as_record(),
            frozen=workflow.receipts.manifest(spec['child']['episode_id']),
            initial_child_refs=list(workflow.receipts.known(spec['child']['episode_id'])),
            catalog=deepcopy(workflow.scientific_process_binding.tool_library.catalog()))
        assert not observations(store, fixture['run_id'], spec['parent']['episode_id'])
        assert not observations(store, fixture['run_id'], spec['child']['episode_id'])
        assert_no_work(workflow, fixture)
    return fixture['spec']


def test_saved_new_policy_reopens_exact_owners_without_transport(caller, monkeypatch):
    spec = commission(caller)
    caller['policy'].write_text('raise AssertionError("Only the saved private snapshot is authoritative")\n')
    assert sha(caller['actual_policy']) == caller['actual_policy_sha256']
    entered, released = [], []

    async def enter(provider):
        entered.append(provider)
        return provider

    async def release(provider, episode_id):
        released.append(episode_id)

    monkeypatch.setattr(ModelConnection, '__aenter__', enter)
    monkeypatch.setattr(ModelConnection, 'complete', forbidden)
    monkeypatch.setattr(ModelConnection, 'release', release)
    monkeypatch.setattr(HomologyJobs, 'order', forbidden)
    monkeypatch.setattr(HomologyJobs, 'submit', forbidden)
    with Store(caller['workspace']) as store:
        before = [tuple(row) for row in store.db.execute('SELECT * FROM runtime_model_calls ORDER BY call_index')]

    async def inspect():
        async with independent_execution.open_commission(spec) as runtime:
            child = runtime['episode']
            workflow = child.source.workflow
            assert_owner(workflow, caller)
            assert child.request.as_record() == spec['child']['request']
            assert child.request.report_contract.schema == caller['form']
            assert workflow.receipts.manifest(child.source.episode_id) == caller['frozen']
            assert list(workflow.receipts.known(child.source.episode_id)) == caller['initial_child_refs']
            assert set(caller['initial']) <= set(workflow.receipts.known(child.source.episode_id))
            names = {row['name'] for row in workflow.catalog(child.source.scope, source=child.source)}
            assert {'execution.estimate', 'episode.history'} <= names
            assert 'public.hmmer.search' not in names
            assert workflow.source_credit_view(child.source)['credit'] == 0
            assert workflow.source_credit_view(child.source)['monitoring_information_credit'] == 0
            assert not observations(workflow.store, caller['run_id'], child.source.episode_id)
            assert not observations(workflow.store, caller['run_id'], spec['parent']['episode_id'])
            assert_no_work(workflow, caller)

    asyncio.run(inspect())
    assert len(entered) == 1 and released == [spec['child']['episode_id']]
    assert not caller['turns'].exists()
    with Store(caller['workspace']) as store:
        assert [tuple(row) for row in store.db.execute('SELECT * FROM runtime_model_calls ORDER BY call_index')] == before


@pytest.mark.parametrize('changed', ['source', 'parameters', 'client', 'map', 'models', 'restoration'])
def test_changed_saved_caller_fails_before_transport(caller, monkeypatch, changed):
    spec = commission(caller)
    if changed == 'source':
        caller['snapshot'].write_bytes(caller['snapshot'].read_bytes() + b'\n')
    elif changed == 'parameters':
        marker_path = caller['directory'] / 'policy-binding.json'
        marker = json.loads(marker_path.read_text())
        marker['parameters']['services']['handoff_unit'] = 2
        marker_path.write_text(canonical(marker) + '\n')
        spec['runtime_binding']['arguments']['caller_binding_pins']['policy-binding.json'] = content_digest(marker)
    elif changed in {'client', 'map'}:
        original = caller['builder']

        def altered(store, configuration=None):
            tools = original(store, configuration)
            if changed == 'client':
                tools.remote_searches.clients.hmmer_fixture_binding = {
                    **tools.remote_searches.clients.hmmer_fixture_binding, 'transport_timeout_seconds': 6}
            else:
                actual_catalog = tools.catalog

                def catalog(*args, **kwargs):
                    result = deepcopy(actual_catalog(*args, **kwargs))
                    result['translation.codes']['input_schema'] = {'type': 'null'}
                    return result

                tools.catalog = catalog
            return tools

        monkeypatch.setattr(tool_configuration, 'build_tools', altered)
    else:
        settings = deepcopy(caller['settings'])
        if changed == 'models':
            settings['models']['FAST']['model'] = 'changed-fixture-model'
        else:
            settings['restoration']['preview_size'] = 25
        (caller['directory'] / 'run.json').write_text(canonical({'run_id': caller['run_id'], **settings}) + '\n')
        with Store(caller['workspace']) as store:
            store.db.execute('UPDATE runtime_runs SET settings=? WHERE run_id=?',
                (canonical(settings), caller['run_id']))
    entered = []

    async def enter(provider):
        entered.append(provider)
        raise AssertionError('A changed saved caller reached transport entry')

    monkeypatch.setattr(ModelConnection, '__aenter__', enter)
    monkeypatch.setattr(ModelConnection, 'complete', forbidden)
    monkeypatch.setattr(HomologyJobs, 'order', forbidden)
    monkeypatch.setattr(HomologyJobs, 'submit', forbidden)

    async def inspect():
        with pytest.raises((DurableExecutionError, ValueError)) as error:
            async with independent_execution.open_commission(spec):
                raise AssertionError('Changed original caller reconstructed successfully')
        if isinstance(error.value, DurableExecutionError):
            assert error.value.failure['code'] in {'identity_conflict', 'unavailable_binding'}
        else:
            assert changed == 'map' and str(error.value) == 'scientific_tool_catalog_changed'

    asyncio.run(inspect())
    assert not entered and not caller['turns'].exists() and caller['http'].calls == []
    with Store(caller['workspace']) as store:
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


def assert_numeric_closure(rows):
    assert len(rows) >= MINIMUM_WINDOW
    assert all(row['step']['marginal_credit'] == 0 for row in rows)
    assert all(row['step']['stop'] is False for row in rows[:-1])
    assert rows[-1]['step']['stop'] is True
    decision = rows[-1]['step']['decision']
    assert decision['continuation_cost'] == TEST_COST
    assert decision['projected_gain']['upper'] <= TEST_COST
    assert decision['decision_basis'] == 'current_estimator_marginal_credit_upper_bound'


def test_new_policy_detached_forecast_return_and_parent_receipt(caller):
    spec = commission(caller)
    caller['policy'].write_text('raise AssertionError("Use the saved actual caller snapshot")\n')
    directory = caller['directory']
    backend = DurableExecutionStore(directory / 'episode-execution')
    started = backend.start(spec['handle'])
    assert started['execution_identity']['pid'] != os.getpid()

    async def wait_return():
        # Only this test wait is bounded; timeout neither cancels nor reprices the child.
        await asyncio.wait_for(backend.wait_events({'version': 'event_condition_v1',
            'events': [{'handle': spec['handle'], 'event': 'returned', 'after_cursor': 0}],
            'reconsider_at': None}), 120)

    asyncio.run(wait_return())
    status = backend.status(spec['handle'])
    returned = backend.load_return(spec['handle'], status['return_id'])
    assert returned['outcome'] == 'closed' and returned['failure'] is None, returned
    forecast, = returned['form']['forecasts']
    assert forecast['reported_result_support'] == {'reported_result_count': 0}
    assert forecast['expected_total_seconds'] is None
    calls = [json.loads(line) for line in caller['turns'].read_text().splitlines()]
    assert len(calls) >= MINIMUM_WINDOW and all(row['pid'] != os.getpid() for row in calls)
    proposal = calls[1]['context']['api_execution_proposal']
    assert proposal['arguments'] == caller['estimate']['arguments']
    assert proposal['api_reported_execution_forecasts'] == [forecast]
    assert all(row['context']['api_execution_proposal'] == proposal for row in calls[1:])
    assert caller['http'].calls == []
    parent_contexts = []
    with Store(caller['workspace']) as store, prepared_case_bindings(store, directory) as (_, options):
        workflow = reopen(caller, store, options, ScriptedProvider([]))
        assert_owner(workflow, caller)
        workflow.configure_execution(spec['runtime_binding'])
        root = workflow.build('annotation', 'root', caller['settings']['goal'], spec['child']['scope'])
        assert root.request.as_record() == caller['root_request']
        child_rows = observations(store, caller['run_id'], spec['child']['episode_id'])
        assert_numeric_closure(child_rows)
        assert returned['completion']['units_consumed'] == len(child_rows) == len(calls)
        original = workflow.journal.row('runtime_actions', spec['child']['episode_id'], 0)
        assert json.loads(original['result'])['result'] == proposal
        assert not observations(store, caller['run_id'], root.source.episode_id)
        root.source.restore()
        slot = workflow.next_return(root.source)
        assert slot['kind'] == 'child_return' and slot['original_decision_index'] == 0

        def after_return(context):
            assert context['child_reports'] == [returned['form']]
            assert 'api_execution_proposal' not in context
            assert context['current_credit'] == context['monitoring_information_credit'] == 0
            parent_contexts.append(deepcopy(context))
            return {'selection': {'kind': 'tool', 'tool': 'episode.history',
                'arguments': {'view': 'index'}}, 'report_update': {}}

        workflow.provider.script = repeat(after_return)
        closed = asyncio.run(root.run_async(workflow.context))
        asyncio.run(root.build_result(closed))
        parent_rows = observations(store, caller['run_id'], root.source.episode_id)
        assert_numeric_closure(parent_rows)
        assert len(parent_contexts) == len(parent_rows) - 1
        assert parent_rows[0]['decision_index'] == 0
        assert len({row['decision_index'] for row in parent_rows}) == len(parent_rows)
        assert observations(store, caller['run_id'], spec['child']['episode_id']) == child_rows
        assert store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_completion_slots WHERE episode_id=? '
            "AND json_extract(slot,'$.kind')='child_return'", (root.source.episode_id,)).fetchone()[0] == 1
        assert backend.status(spec['handle'])['acknowledgment_id'] == slot['child_return']['admission_id']
        assert workflow.next_return(root.source) is None
        assert workflow.context.runtime._controllers == {} and workflow.context._active_episodes == {}
        assert_no_work(workflow, caller)
        assert workflow.receipts.manifest(spec['child']['episode_id']) == caller['frozen']
        assert workflow.scientific_process_binding.tool_library.catalog() == caller['catalog']
        for name in ('episode_archive', 'result_archive', 'facts_archive'):
            item = returned[name]
            assert ArchivedRecord(directory / 'archive' / item['file'], item['sha256'], item['index_sha256']).load()
        assert backend.start(spec['handle'])['execution_identity'] == started['execution_identity']
        assert backend.load_return(spec['handle'], status['return_id']) == returned
        receipts_before = [tuple(row) for row in store.db.execute(
            'SELECT * FROM runtime_record_receipts ORDER BY receipt_index')]
        credit_before = workflow.source_credit_view(root.source)
        workflow.receive_form(root.source, returned['form'], caller['form'], 0, redelivery=True)
        assert [tuple(row) for row in store.db.execute(
            'SELECT * FROM runtime_record_receipts ORDER BY receipt_index')] == receipts_before
        assert workflow.source_credit_view(root.source) == credit_before
        assert observations(store, caller['run_id'], root.source.episode_id) == parent_rows
        (directory.parent / 'reconstruction-proof.json').write_text(canonical({
            'runtime_binding': spec['runtime_binding'], 'returned': returned,
            'parent_observations': parent_rows, 'child_observations': child_rows,
            'parent_received_contexts': parent_contexts, 'zero_http_requests': caller['http'].calls == [],
            'actual_new_policy_source_sha256': caller['actual_policy_sha256'],
            'configured_model_science': False}) + '\n')
    wait_for_worker_exit(started['execution_identity'])
    assert backend.status(spec['handle'])['liveness'] == 'not_live'
    assert caller['http'].calls == []
