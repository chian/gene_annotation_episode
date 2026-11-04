"""Actual caller setup and C1 resource reconstruction, with fixture decisions.

The subprocess uses the production independent-execution entrypoint and real
ModelConnection protocol. Its provider, credit operands and stopping rule are
explicit engineering fixtures. One tiny native search supplies a real receiving
interface; these checks perform no configured-model scientific investigation.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

import pytest

from method_loop.archive import ArchivedRecord
from method_loop.durable import (DurableExecutionError, DurableExecutionStore,
                                 canonical, content_digest, validate_commission)
from gene_annotation_episode import independent_execution as independent
from gene_annotation_episode.case_execution import (prepare_case_run,
    prepared_case_bindings, run_prepared_case)
from gene_annotation_episode.materials import artifact_path
from gene_annotation_episode.homology_jobs import HomologyJobs
from gene_annotation_episode.providers import ModelConnection
from gene_annotation_episode.resource_episodes import LAUNCH_VERSION, RESULTS_VERSION
from gene_annotation_episode.runtime import TypedReportContract, Workflow, assemble_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools
from test_case_execution import PARAMETERS, POLICY, prepared
from test_homology_episode_runtime import Provider
from test_homology_jobs import wait_terminal
from test_runtime import obj


UNITS = {'handoff_unit': 2.75, 'acquired_record_unit': 0.125}
ROLES = ('launch', 'launch_api', 'launch_local', 'launch_hpc', 'results')

# This source is snapshotted by the real caller policy loader. Construction logs
# inspect only configuration identities; they neither project nor execute work.
CASE_SETUP = '''
from dataclasses import replace
import json, os
from gene_annotation_episode.resource_service_setup import bind_resource_services

_original_create_policy = create_policy

def specialist_setup(store, *, run_id, directory, job_episodes, resource_estimator):
    application = bind_resource_services(store, run_id=run_id, directory=directory,
        job_episodes=job_episodes, resource_estimator=resource_estimator,
        handoff_unit=2.75, acquired_record_unit=0.125)
    projector = application.role_credit_bindings['launch_local']['project']
    assert projector.reader.store is store
    assert projector.reader.jobs is job_episodes.jobs
    assert projector.reader.run_id == run_id
    assert all(value['project'] is projector for value in application.role_credit_bindings.values())
    with (directory/'resource-factory.jsonl').open('a') as stream:
        stream.write(json.dumps({'pid': os.getpid(), 'run_id': run_id,
            'definition': projector.as_record(),
            'descriptors': list(application.episode_binding_descriptors)})+'\\n')
    return application

def create_policy(parameters):
    return replace(_original_create_policy(parameters),
        initial_known_record_refs=[], episode_record_receipts=True,
        episode_service_factory=specialist_setup,
        episode_service_binding={'version':'fixture_received_resource_setup_v1',
            'handoff_unit':2.75, 'acquired_record_unit':0.125})
'''


TRANSPORT = '''import json, os, sys
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
        result = {'thread': {'id': 'resource-fixture-thread'}, 'model': params['model'],
                  'reasoningEffort': params['config']['model_reasoning_effort']}
    elif method == 'turn/start':
        context = json.loads(params['input'][0]['text'])
        previous = context['last_local_outcome']
        assert context['role'] == 'launch_local'
        assert context['current_credit'] == (2.75 if previous else 0)
        if previous:
            assert previous['execution_handoff']['state'] == 'usable'
            assert previous['resource_information_refs']
        with log.open('a') as stream:
            stream.write(json.dumps({'pid': os.getpid(), 'context': context})+'\\n')
        response = {'selection': {'kind': 'tool',
            'tool': 'resource.capabilities' if previous else 'homology.check_handoff',
            'arguments': {}}, 'report_update': {'finding_state': 'checked' if previous else 'unknown'}}
        emit({'id': message['id'], 'result': {'turn': {'id': 'resource-fixture-turn'}}})
        emit({'method': 'item/completed', 'params': {'threadId': params['threadId'],
            'item': {'type': 'agentMessage', 'text': json.dumps(response)}}})
        emit({'method': 'turn/completed', 'params': {'threadId': params['threadId'],
            'turn': {'id': 'resource-fixture-turn', 'status': 'completed'}}})
        continue
    else:
        raise AssertionError(method)
    emit({'id': message['id'], 'result': result})
'''


class BeforeRoot(Exception):
    pass


def forbidden(*args, **kwargs):
    raise AssertionError('No provider transport, native recheck or new action is allowed')


def form_schema(workflow, role):
    return obj({'finding_state': {'type': 'string', 'enum': ['unknown', 'checked']},
        'execution': workflow.report_sources(role)['execution_handoff']['report_schema'],
        'local_credit': {'type': 'number', 'x-source': 'credit'}})


def original_spec(workflow, parent, child, *, inputs):
    assignment = child.request.message.as_record()['episode_assignment']
    selected = (assignment['handoff']['resource_selection'] if child.source.path[-1][0] == 'results'
        else assignment['resource_selection'])
    spec = {'version': 'episode_commission_v1',
        'handle': 'episode:resource_fixture_' + child.key,
        'operation_key': workflow.run_id + ':resource_fixture_' + child.key,
        'run_id': workflow.run_id,
        'parent': {'episode_id': parent.source.episode_id, 'goal_id': parent.goal.goal_id,
            'path': [list(part) for part in parent.source.path]},
        'child': {'episode_id': child.source.episode_id, 'role': child.source.path[-1][0],
            'key': child.key, 'path': [list(part) for part in child.source.path],
            'request': child.request.as_record(), 'scope': child.source.scope},
        'input_versions': inputs,
        'runtime_binding': independent.make_runtime_binding(workflow.store, workflow.directory,
            kind='fixed_case'),
        'constraints': {'scope': child.source.scope, 'fixture_only': True},
        'resource_selection': selected, 'expectation_snapshot_refs': []}
    return validate_commission(spec)


def fixture_commission(tmp_path, monkeypatch):
    case, configuration, policy = prepared(tmp_path)
    policy.write_text(POLICY + CASE_SETUP)
    transport, turns = tmp_path/'resource_transport.py', tmp_path/'resource-turns.jsonl'
    transport.write_text(TRANSPORT)
    configuration['models']['connection']['command'] = [sys.executable, str(transport), str(turns)]
    directory = tmp_path/'run'
    manifest = prepare_case_run(case, directory, configuration)
    with monkeypatch.context() as patched:
        patched.setattr(Workflow, 'build', lambda *a, **k: (_ for _ in ()).throw(BeforeRoot()))
        with pytest.raises(BeforeRoot):
            asyncio.run(run_prepared_case(directory, policy_file=policy,
                parameters={**PARAMETERS, 'stop_after': 2}, provider=Provider([])))
    saved = json.loads((directory/'run.json').read_text())
    run_id, settings = saved['run_id'], {key: value for key, value in saved.items() if key != 'run_id'}
    workspace = case/'workspace'
    with Store(workspace) as store, prepared_case_bindings(store, directory) as (_, options):
        workflow = assemble_workflow(store, build_tools(store, manifest['configuration']), Provider([]),
            directory, run_id, settings,
            **{key: value for key, value in options.items() if key != 'binding_definitions'})
        scope = {'subject_refs': [manifest['target_ref']]}
        root = workflow.build('annotation', 'root', settings['goal'], scope)
        query = json.loads((case/'evidence-refs.json').read_text())['product_ref']
        query_bytes = artifact_path(store, store.get(query)['sequence_ref']).read_bytes()
        launch = {'version': LAUNCH_VERSION, 'job_request': {'query_ref': query, 'cpu': 1},
            'immutable_input_versions': [{'reference': query, 'version': None,
                'content_sha256': hashlib.sha256(query_bytes).hexdigest()}],
            'constraints': {'allowed_kinds': ['local'], 'cpu': 1}, 'resource_selection': None,
            'software_knowledge_refs': [], 'resource_knowledge_refs': []}
        parent_contract = TypedReportContract('Return the original receiving interface',
            form_schema(workflow, 'launch'), workflow.resolver(scope, grain='launch'))
        parent = workflow.build('launch', 'launch_parent', 'Investigate the selected fixture job', scope,
            parent=root.goal, parent_path=root.source.path, contract=parent_contract,
            initial={'finding_state': 'unknown'}, episode_assignment=launch)
        binding = workflow.episode_bindings.for_role('launch_local')
        adapter, = binding.adapters.values()
        selected = {**deepcopy(launch), 'resource_selection': adapter._selection(1)}
        assignment = binding.prepare_assignment(workflow.binding_context(parent.source), 'launch_local',
            selected, scope, run_id + ':fixture_native_assignment')
        schema = form_schema(workflow, 'launch_local')
        contract = TypedReportContract('Return the exact original checked C9 interface', schema,
            workflow.resolver(scope, grain='launch_local'))
        child = workflow.build('launch_local', 'native_child', 'Establish the assigned receiving interfaces',
            scope, parent=parent.goal, parent_path=parent.source.path, contract=contract,
            initial={'finding_state': 'unknown'}, episode_assignment=assignment)
        inherited = workflow.receipts.manifest(child.source.episode_id)
        known = tuple(workflow.receipts.known(child.source.episode_id))
        # A later parent input must not be adopted by the reconstructed child.
        later = manifest['context_source_ref']
        workflow.receipts.receive(parent.source.episode_id, [later], kind='own_action', source_index=7)
        spec = original_spec(workflow, parent, child, inputs=[{'reference': query, 'version': None,
            'content_sha256': content_digest(store.get(query))}])
        assert spec['input_versions'][0]['content_sha256'] != launch['immutable_input_versions'][0]['content_sha256']
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
        for role in ROLES:
            projector = workflow.role_credit_projectors[role]
            assert projector.reader.store is store and projector.reader.jobs is options['job_episodes'].jobs
            assert projector.reader.run_id == run_id
            assert {key: projector.as_record()[key] for key in UNITS} == UNITS
    return {'spec': spec, 'directory': directory, 'workspace': workspace, 'turns': turns,
        'manifest': manifest, 'settings': settings, 'frozen': inherited, 'known': known,
        'later': later, 'query': query, 'parent_request': parent.request.as_record(),
        'root_request': root.request.as_record(), 'policy': policy}


def observations(store, episode_id):
    return [json.loads(row[0]) for row in store.db.execute(
        'SELECT observation FROM runtime_observations WHERE episode_id=? ORDER BY unit_index',
        (episode_id,))]


def load_return(backend, spec):
    async def wait():
        await asyncio.wait_for(backend.wait_events({'version': 'event_condition_v1',
            'events': [{'handle': spec['handle'], 'event': 'returned', 'after_cursor': 0}],
            'reconsider_at': None}), 30)
    asyncio.run(wait())
    status = backend.status(spec['handle'])
    return backend.load_return(spec['handle'], status['return_id'])


def test_production_resource_worker_restores_factory_receipts_exact_form_and_units(tmp_path, monkeypatch):
    fixture = fixture_commission(tmp_path, monkeypatch)
    spec, directory = fixture['spec'], fixture['directory']
    assignment = spec['child']['request']['message']['episode_assignment']
    job_ref = assignment['adapter_assignment']['job_ref']
    # The caller's current source is no longer authoritative after snapshotting.
    fixture['policy'].write_text('raise AssertionError("Use the original saved resource factory")\n')
    # Native setup is engineering scaffolding, not an episode action or credit.
    with Store(fixture['workspace']) as store, prepared_case_bindings(store, directory) as (_, options):
        jobs = options['job_episodes'].jobs
        jobs.configure(job_ref, 1)
        jobs.stage(job_ref)
        jobs.submit(job_ref)
        wait_terminal(jobs, job_ref)
    backend = DurableExecutionStore(directory/'episode-execution')
    backend.commission(spec)
    started = backend.start(spec['handle'])
    returned = load_return(backend, spec)
    assert started['execution_identity']['pid'] != os.getpid()
    assert returned['outcome'] == 'closed', returned
    assert returned['failure'] is None
    assert returned['completion']['units_consumed'] == 2
    assert set(returned['form']) == {'finding_state', 'execution', 'local_credit'}
    assert returned['form']['finding_state'] == 'checked'
    assert returned['form']['local_credit'] == UNITS['handoff_unit']
    handoff = returned['form']['execution']
    assert handoff['execution_handle'] == job_ref and handoff['state'] == 'usable'
    assert handoff['resource_selection'] == spec['resource_selection']
    assert handoff['submitted_input_versions'] == assignment['immutable_input_versions']
    assert handoff['monitoring']['contract_ref'] == 'homology.status.v1'
    assert handoff['results']['contract_ref'] == 'homology.results.v1'
    assert handoff['check_record_refs'] and handoff['checked_at']
    calls = [json.loads(line) for line in fixture['turns'].read_text().splitlines()]
    assert len(calls) == 2
    assert all(call['context']['scope'] == spec['child']['scope'] for call in calls)
    assert all(call['context']['goal'] == spec['child']['request']['goal'] for call in calls)
    assert calls[1]['context']['last_local_outcome']['execution_handoff'] == handoff
    factory_calls = [json.loads(line) for line in (directory/'resource-factory.jsonl').read_text().splitlines()]
    worker_setup, = [call for call in factory_calls if call['pid'] == started['execution_identity']['pid']]
    assert worker_setup['run_id'] == spec['run_id']
    assert worker_setup['descriptors'] == fixture['settings']['episode_bindings']
    assert {key: worker_setup['definition'][key] for key in UNITS} == UNITS
    assert worker_setup['definition']['reader'] == fixture['settings'][
        'episode_role_credit_bindings']['launch_local']['definition']['reader']
    with Store(fixture['workspace']) as store:
        assert observations(store, spec['parent']['episode_id']) == []
        child_observations = observations(store, spec['child']['episode_id'])
        assert [row['step']['marginal_credit'] for row in child_observations] == [2.75, 0]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 2
        request = json.loads(store.db.execute('SELECT request FROM runtime_episodes WHERE episode_id=?',
            (spec['child']['episode_id'],)).fetchone()[0])
        assert request == spec['child']['request']
        assert request['message']['knowledge_inheritance'] == fixture['frozen']
        proof, = calls[1]['context']['last_local_outcome']['resource_information_refs']
        from gene_annotation_episode.episode_receipts import EpisodeReceipts
        receipts = EpisodeReceipts(store, spec['run_id'])
        assert proof in receipts.known(spec['child']['episode_id'])
        assert fixture['later'] not in receipts.known(spec['child']['episode_id'])
        assert set(fixture['known']) <= set(receipts.known(spec['child']['episode_id']))
    for field in ('episode_archive', 'result_archive', 'facts_archive'):
        archive = returned[field]
        assert ArchivedRecord(directory/'archive'/archive['file'], archive['sha256'],
            archive['index_sha256']).load()
    assert backend.start(spec['handle'])['execution_identity'] == started['execution_identity']
    assert load_return(backend, spec) == returned
    retired = list((directory/'providers').glob('*/retired-sessions/*.json'))
    assert len(retired) == 1
    assert json.loads(retired[0].read_text())['remaining_active_workers'] == 0
    inspect_results_reconstruction(fixture, handoff, proof, monkeypatch)


def inspect_results_reconstruction(fixture, handoff, proof, monkeypatch):
    """An original assignment proof is results input, with no new observation."""
    directory, settings = fixture['directory'], fixture['settings']
    spec = fixture['spec']
    with Store(fixture['workspace']) as store, prepared_case_bindings(store, directory) as (_, options):
        workflow = assemble_workflow(store, build_tools(store, fixture['manifest']['configuration']),
            Provider([]), directory, spec['run_id'], settings,
            **{key: value for key, value in options.items() if key != 'binding_definitions'})
        scope = spec['child']['scope']
        root = workflow.build('annotation', 'root', settings['goal'], scope)
        binding = workflow.episode_bindings.for_role('results')
        assigned = binding.prepare_assignment(workflow.binding_context(root.source), 'results',
            {'version': RESULTS_VERSION, 'handoff': handoff, 'requested_data_selector': {}},
            scope, spec['run_id'] + ':fixture_results_assignment')
        contract = TypedReportContract('Return the original input handoff and acquisition qualification',
            form_schema(workflow, 'results'), workflow.resolver(scope, grain='results'))
        child = workflow.build('results', 'results_child', 'Acquire only the assigned fixture data',
            scope, parent=root.goal, parent_path=root.source.path, contract=contract,
            initial={'finding_state': 'unknown'}, episode_assignment=assigned)
        assert workflow.source_credit_view(child.source)['credit'] == 0
        assert proof in workflow.receipts.known(child.source.episode_id, baseline=True)
        results_spec = original_spec(workflow, root, child, inputs=spec['input_versions'])
        frozen = workflow.receipts.manifest(child.source.episode_id)
    entered, released = [], []

    async def enter(provider):
        entered.append(provider)
        return provider

    async def release(provider, episode_id):
        released.append(episode_id)

    with monkeypatch.context() as patched:
        patched.setattr(ModelConnection, '__aenter__', enter)
        patched.setattr(ModelConnection, 'release', release)
        patched.setattr(ModelConnection, 'complete', forbidden)
        for name in ('check_handoff', 'receive', 'status', 'handoff', '_handle'):
            patched.setattr(HomologyJobs, name, forbidden)

        async def inspect():
            async with independent.open_commission(results_spec) as runtime:
                episode = runtime['episode']
                source, reopened = episode.source, episode.source.workflow
                assert episode.request.as_record() == results_spec['child']['request']
                assert reopened.episode_record_receipts is True
                assert reopened.receipts.manifest(source.episode_id) == frozen
                assert proof in reopened.receipts.known(source.episode_id, baseline=True)
                credit = reopened.source_credit_view(source)
                assert credit['credit'] == 0 and credit['new_acquired_record_count'] == 0
                assert credit['new_handoff_count'] == 0
                projector = reopened.role_credit_projectors['results']
                assert projector.reader.store is reopened.store
                assert projector.reader.jobs is reopened.job_episodes.jobs
                assert projector.reader.run_id == results_spec['run_id']
                assert {key: projector.as_record()[key] for key in UNITS} == UNITS
                form = {'finding_state': 'unknown', 'execution': handoff, 'local_credit': 0}
                assert episode.request.report_contract.admit(form, audit_identifiers=(
                    source.episode_id, episode.goal.goal_id)).as_record() == form
                assert observations(reopened.store, source.episode_id) == []
        asyncio.run(inspect())
    assert len(entered) == 1 and released == [results_spec['child']['episode_id']]
    with Store(fixture['workspace']) as store:
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 2


@pytest.mark.parametrize('changed', ['assignment', 'scope', 'input_digest', 'receipt_mode',
    'factory_definition', 'reader_identity', 'role_units', 'inheritance'])
def test_changed_resource_reconstruction_operands_fail_before_transport(tmp_path, monkeypatch, changed):
    fixture = fixture_commission(tmp_path, monkeypatch)
    spec = deepcopy(fixture['spec'])
    if changed == 'assignment':
        spec['child']['request']['message']['episode_assignment']['job_request']['cpu'] = 2
    elif changed == 'scope':
        spec['child']['scope']['segments'] = [{'target_ref': fixture['manifest']['target_ref'],
            'start': 0, 'end': 30, 'unit': 'nt'}]
    elif changed == 'input_digest':
        spec['input_versions'][0]['content_sha256'] = '0'*64
    elif changed == 'inheritance':
        spec['child']['request']['message']['knowledge_inheritance']['parent_episode_id'] = 'episode_wrong'
        with Store(fixture['workspace']) as store:
            with store.transaction():
                store.db.execute('UPDATE runtime_episodes SET request=? WHERE episode_id=?',
                    (canonical(spec['child']['request']), spec['child']['episode_id']))
    else:
        settings = deepcopy(fixture['settings'])
        if changed == 'receipt_mode':
            settings.pop('episode_record_receipts')
        elif changed == 'factory_definition':
            settings['episode_application_services']['definition']['handoff_unit'] = 9
        elif changed == 'reader_identity':
            settings['episode_role_credit_bindings']['launch_local']['definition']['reader']['run_id'] = 'other_run'
        else:
            settings['episode_role_credit_bindings']['launch_local']['definition']['handoff_unit'] = 9
        (fixture['directory']/'run.json').write_text(canonical({'run_id': spec['run_id'], **settings}))
        with Store(fixture['workspace']) as store:
            with store.transaction():
                store.db.execute('UPDATE runtime_runs SET settings=? WHERE run_id=?',
                    (canonical(settings), spec['run_id']))
        spec['runtime_binding']['settings_sha256'] = content_digest(settings)
    entered = []

    async def transport(provider):
        entered.append(provider)
        raise AssertionError('Changed original inputs reached provider transport')

    monkeypatch.setattr(ModelConnection, '__aenter__', transport)

    async def inspect():
        with pytest.raises(DurableExecutionError) as error:
            async with independent.open_commission(spec):
                raise AssertionError('Changed original inputs reconstructed successfully')
        assert error.value.failure['code'] in {'identity_conflict', 'unavailable_binding'}
        affected = {'assignment': spec['child']['episode_id'], 'scope': spec['child']['episode_id'],
            'input_digest': fixture['query'], 'receipt_mode': 'episode_record_receipts',
            'factory_definition': 'episode_application_services',
            'reader_identity': 'episode_role_credit_bindings',
            'role_units': 'episode_role_credit_bindings', 'inheritance': spec['child']['episode_id']}
        assert error.value.failure['affected_refs'] == [affected[changed]]
    asyncio.run(inspect())
    assert entered == [] and not fixture['turns'].exists()
    with Store(fixture['workspace']) as store:
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
