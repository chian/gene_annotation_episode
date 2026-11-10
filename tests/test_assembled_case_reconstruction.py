"""Ordinary assembled root and detached worker reconstruction.

The current publication is inspected honestly as A0/P19. Construction uses a
separately identified, invented A/P fixture. Scientific projectors and resources
are production implementations; provider decisions and the two-action stopping
rule are explicit engineering fixtures, never a scientific demonstration.
"""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import sys

import pytest

from method_loop.archive import ArchivedRecord
from method_loop.durable import DurableExecutionError, canonical, content_digest
from gene_annotation_episode import assembled_case_policy
from gene_annotation_episode import independent_execution as independent
from gene_annotation_episode import tool_configuration
from gene_annotation_episode.case_execution import (
    prepare_case_run, prepared_case_bindings, run_prepared_case,
)
from gene_annotation_episode.domain import obj
from gene_annotation_episode.homology_jobs import HomologyJobs
from gene_annotation_episode.investigation_progress import ScientificFindingProgress
from gene_annotation_episode.providers import ModelConnection
from gene_annotation_episode.runtime import Workflow, assemble_workflow
from gene_annotation_episode.scientific_process_reports import SELECTION_REPORT_VERSION
from gene_annotation_episode.state import Store
from test_assembled_case_policy import parameters as assembled_parameters
from test_assembled_service_setup import PUBLICATION, RETRIEVAL, ROOT_ROLES
from test_case_execution import prepared
from test_homology_episode_runtime import Provider
from test_scientific_process_library import synthetic_support_entry


OPERATIONAL_ROLES = ('launch', 'launch_api', 'launch_local', 'launch_hpc', 'results')
SELECTED_TOOLS = ['sequence.inspect', 'translation.codes']

# Snapshot this explicit caller wrapper through the real case policy loader.
# Only the numerical fixture controller differs from assembled_case_policy.
FIXTURE_POLICY = '''from dataclasses import replace
from gene_annotation_episode.assembled_case_policy import create_policy as assembled_policy
from gene_annotation_episode.numerical import YieldController, YieldEstimate, NumericBand

def create_policy(parameters):
    original = assembled_policy(parameters)
    def fixture_estimate(history, settings, contexts):
        return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= 2 else 1), settings,
            {'kind':'assembled_engineering_fixture_only'})
    # The caller's policy retains its explicit controller parameters below;
    # the fixture extracts only the existing YieldParameters fields.
    def controller(path, initial):
        settings = {name: parameters['policy']['controller'][name]
            for name in ('window_size','subsample_size','uncertainty_alpha')}
        return YieldController(str(path), initial, 0, settings,
            estimate_with_context=fixture_estimate)
    return replace(original, controller_factory=controller,
        controller_definition={'version':'assembled_engineering_fixture_controller_v1',
            'stop_after_completed_actions':2,'cost':0,
            'scientific_policy_unchanged':True})
'''

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
        result = {'thread': {'id':'assembled-fixture-thread'}, 'model':params['model'],
            'reasoningEffort':params['config']['model_reasoning_effort']}
    elif method == 'turn/start':
        # The published scientific prompt is prose. This controlled transport
        # consumes its recorded semantic input and verifies the exact wire text;
        # prompt-presentation assertions live in test_scientific_process_prompt_delivery.
        requests = (log.parent/'run/providers').glob('*/session-*/call-*/request.json')
        request = json.loads(max(requests, key=lambda path: path.stat().st_mtime_ns).read_text())
        assert request['input'] == params['input']
        context = request['context']
        selected = [row['name'] for row in context['scientific_process']['selection']['child_tool_info']]
        assert selected == ['sequence.inspect','translation.codes']
        names = {entry['name'] for entry in context['tools']}
        assert set(selected) <= names and 'source.archive.extract' not in names
        assert context['scientific_process']['permitted_children'] == [
            'scientific_process','literature','launch','monitor','results']
        assert context['current_credit'] == 0 and 'annotation_score' not in context
        previous = context['last_local_outcome']
        if previous is None:
            action = {'kind':'tool','tool':'sequence.inspect',
                'arguments':{'subject_ref':context['scope']['subject_refs'][0]}}
            state = 'unknown'
        else:
            assert previous['status'] == 'completed'
            assert previous['result']['length'] == 762
            action = {'kind':'tool','tool':'translation.codes','arguments':{}}
            state = 'measured'
        with log.open('a') as stream:
            stream.write(json.dumps({'pid':os.getpid(),'context':context})+'\n')
        response = {'selection':action, 'report_update':{'finding_state':state}}
        emit({'id':message['id'],'result':{'turn':{'id':'assembled-fixture-turn'}}})
        emit({'method':'item/completed','params':{'threadId':params['threadId'],
            'item':{'type':'agentMessage','text':json.dumps(response)}}})
        emit({'method':'turn/completed','params':{'threadId':params['threadId'],
            'turn':{'id':'assembled-fixture-turn','status':'completed'}}})
        continue
    else:
        raise AssertionError(method)
    emit({'id':message['id'],'result':result})
'''


class BeforeRoot(Exception):
    pass


def forbidden(*args, **kwargs):
    raise AssertionError('A reconstruction check cannot start transport or native work')


def invented_ap_source(directory):
    """A/P only: invented contract operands, not adopted support definitions."""
    directory.mkdir()
    (directory/'entries').mkdir()
    evidence = {'case_group':'invented_contract_fixture', 'case_id':'invented_fixture',
        'source_url':'https://example.org/invented-fixture', 'source_locator':'fixture',
        'observation':'Invented interface material.',
        'limit':'No biological evidence or adopted scientific-support option.'}
    bodies = [
        synthetic_support_entry([evidence]),
        {'id':'P01', 'slot':'thought_pattern', 'name':'Invented contrast fixture',
         'description':'Engineering construction boundary only.', 'evidence':[evidence],
         'use_when':'Fixture alternatives remain.', 'live_alternatives':['First','Second'],
         'decision_guidance':['Interpret the preceding actual outcome.'],
         'outcome_contingencies':[{'if_observed':'Equal outcomes',
             'then_consider':'Retain both alternatives.'}], 'boundary':'No fixed itinerary.'},
    ]
    entries, rows = [], []
    for body in bodies:
        evidence_id = 'E-'+body['id']+'-01'
        relative = 'entries/'+body['id']+'.json'
        (directory/relative).write_text(canonical(body)+'\n')
        entries.append({**{key:body[key] for key in ('id','slot','name','description')},
            'detail_path':relative, 'source_evidence_ids':[evidence_id]})
        rows.append({'evidence_id':evidence_id, 'option_id':body['id'], **evidence})
    index = {'format':'research_three_slot_options_v1', 'status':'Invented A/P fixture only',
        'slots':[{'slot':slot,'catalog':name,'count':1} for slot,name in (
            ('annotation_distinction','annotations.json'), ('thought_pattern','thoughts.json'))],
        'entries':entries}
    (directory/'index.json').write_text(canonical(index)+'\n')
    (directory/'option_sources.json').write_text(canonical({
        'meaning':'Invented instruction provenance only', 'rows':rows})+'\n')


def initialize_case(tmp_path, monkeypatch, *, invented=False, wired=False):
    """Real caller publication, interrupted before root creation or transport."""
    case, configuration, policy = prepared(tmp_path)
    source = tmp_path/'invented-a-p'
    if invented:
        invented_ap_source(source)
        policy.write_text(FIXTURE_POLICY)
    else:
        policy.write_bytes(Path(assembled_case_policy.__file__).read_bytes())
    transport, turns = tmp_path/'assembled_transport.py', tmp_path/'assembled-turns.jsonl'
    compile(TRANSPORT,str(transport),'exec')
    transport.write_text(TRANSPORT)
    configuration['models']['connection']['command'] = [sys.executable, str(transport), str(turns)]
    # Real configured roles, with an explicit engineering protocol executable.
    configuration['models']['FAST'] = {'model':'gpt-6-luna','reasoning_effort':'none'}
    configuration['models']['REASONING'] = {'model':'gpt-6-sol','reasoning_effort':'medium'}
    directory = tmp_path/'run'
    manifest = prepare_case_run(case, directory, configuration)
    parameters = assembled_parameters()
    if wired:
        parameters['services'].update(version='assembled_case_services_v2',
            log_roles=['stdout', 'stderr'],
            execution_resources={'here': {'kind': 'local', 'workspace': str(tmp_path/'project'),
                'policy': {'memory_bytes': 128 * 1024 ** 2, 'scratch_bytes': 8 * 1024 ** 2}}, 'ebi': {'kind': 'hmmer_api'}},
            initial_execution_information={})
    parameters['policy']['operational']['registry_ref'] = manifest['registry_configuration']['registry_ref']
    if invented:
        parameters['services']['source_directory'] = str(source)
    connection = ModelConnection(manifest['configuration']['models'], tmp_path/'unopened-provider', directory)
    with monkeypatch.context() as patched:
        patched.setattr(Workflow, 'build', lambda *a, **k: (_ for _ in ()).throw(BeforeRoot()))
        patched.setattr(ModelConnection, '__aenter__', forbidden)
        patched.setattr(ModelConnection, 'complete', forbidden)
        patched.setattr(HomologyJobs, 'order', forbidden)
        patched.setattr(HomologyJobs, 'submit', forbidden)
        with pytest.raises(BeforeRoot):
            # These assignment/reconstruction fixtures intentionally retain the
            # original bare-action scripted transport, including detached turns.
            asyncio.run(run_prepared_case(directory, policy_file=policy,
                parameters=parameters, provider=connection, decision_protocol=None))
    saved = json.loads((directory/'run.json').read_text())
    settings = {key:value for key,value in saved.items() if key != 'run_id'}
    return {'case':case, 'workspace':case/'workspace', 'directory':directory,
        'manifest':manifest, 'settings':settings, 'run_id':saved['run_id'],
        'parameters':parameters, 'source':source if invented else PUBLICATION,
        'policy':policy, 'turns':turns}


def test_case_entrypoint_forwards_explicit_and_default_decision_protocols(tmp_path, monkeypatch):
    from gene_annotation_episode import case_execution
    from gene_annotation_episode.runtime import _DEFAULT_DECISION_PROTOCOL
    from test_case_execution import PARAMETERS

    case, configuration, policy = prepared(tmp_path)
    directory = tmp_path/'forwarded_run'
    prepare_case_run(case, directory, configuration)
    received = []

    async def inspect(store, tools, **options):
        received.append(options['decision_protocol'])
        return {'protocol_forwarded': True}

    monkeypatch.setattr(case_execution, 'run_workflow', inspect)
    for protocol in (_DEFAULT_DECISION_PROTOCOL, None, 'decision_exchange_v1'):
        option = {} if protocol is _DEFAULT_DECISION_PROTOCOL else {'decision_protocol': protocol}
        result = asyncio.run(run_prepared_case(directory, policy_file=policy,
            parameters=PARAMETERS, provider=Provider([]), **option))
        assert result == {'protocol_forwarded': True}
        assert received[-1] is protocol


def reopen(fixture, store, options, provider):
    return assemble_workflow(store, tool_configuration.build_tools(store,
        fixture['manifest']['configuration']), provider, fixture['directory'],
        fixture['run_id'], fixture['settings'],
        **{key:value for key,value in options.items() if key != 'binding_definitions'})


def form_schema(workflow):
    return obj({'finding_state':{'type':'string','enum':['unknown','measured']},
        'records':{'type':'array','items':{'type':'string','format':'reference'},
            'x-source':'committed_record_refs'},
        'local_credit':{'type':'number','x-source':'credit'},
        'process_results':workflow.report_sources('scientific_process')[
            'scientific_process_results']['report_schema']})


def commission_fixture(tmp_path, monkeypatch, *, wired=False):
    fixture = initialize_case(tmp_path, monkeypatch, invented=True, wired=wired)
    directory, settings = fixture['directory'], fixture['settings']
    with Store(fixture['workspace']) as store, prepared_case_bindings(store, directory) as (_, options):
        provider = Provider([])
        workflow = reopen(fixture, store, options, provider)
        binding = independent.make_runtime_binding(store, directory, kind='fixed_case')
        workflow.configure_execution(binding)
        scope = {'subject_refs':[fixture['manifest']['target_ref']]}
        root = workflow.build('annotation', 'root', settings['goal'], scope)
        library = workflow.scientific_process_binding.library
        selection = {'version':'scientific_process_selection_v3',
            'evidence_axis':library.reference('A01'), 'thought_pattern':library.reference('P01'),
            'child_tool_info':[{'name': name, 'resources': 'local'} for name in SELECTED_TOOLS]}
        schema = form_schema(workflow)
        action = {'kind':'episode_child', 'role':'scientific_process',
            'goal':'Investigate the invented construction contract through actual local measurements.',
            'scope':scope, 'purpose':'Return the exact original bounded measurement form.',
            'schema_json':canonical(schema), 'initial_report_json':'{"finding_state":"unknown"}',
            'assignment':{'selection':selection,
                'evidence_refs':[fixture['manifest']['target_ref']],
                'constraints':{'engineering_fixture_only':True},
                'context':{'investigation':'Actual sequence measurement contract fixture.'}}}
        provider.script = iter([{'selection':action,'report_update':{}}])
        # Use the ordinary saved decision response and selected commission path.
        async def select():
            context = {'visible_record_refs':[], 'scope':scope}
            response, index, actual_context, action_contract = await root.source.call(
                context, workflow.action_schema(root.source))
            return root.source.apply_response(response, index, actual_context, action_contract)
        deferred = asyncio.run(select())
        assert root.source.feedback is None, root.source.feedback
        spec, = workflow.commissions.recover_selected(root.source.episode_id)
        # C1 is entered only for an already published original commission.
        # Publication records identity; it starts no worker or model transport.
        workflow.execution_backend.commission(spec)
        assert deferred.decision_index == 0
        child_id = spec['child']['episode_id']
        frozen = workflow.receipts.manifest(child_id)
        known = list(workflow.receipts.known(child_id))
        # Received later by the parent: never part of the child's frozen prefix.
        later = fixture['manifest']['context_source_ref']
        workflow.receipts.receive(root.source.episode_id, [later], kind='own_action', source_index=7)
        fixture.update(spec=spec, action=action, schema=schema, frozen=frozen,
            known=known, later=later, root_request=root.request.as_record(), selection=selection)
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 1
    return fixture


def observations(store, episode_id):
    return [json.loads(row[0]) for row in store.db.execute(
        'SELECT observation FROM runtime_observations WHERE episode_id=? ORDER BY unit_index',
        (episode_id,))]


def wait_for_worker_exit(identity):
    """Engineering cleanup evidence, without changing an episode's decisions."""
    async def exited():
        try:
            descriptor = os.pidfd_open(identity['pid'])
        except ProcessLookupError:
            return
        loop = asyncio.get_running_loop()
        ready = loop.create_future()
        loop.add_reader(descriptor, lambda: None if ready.done() else ready.set_result(None))
        try:
            await asyncio.wait_for(ready, 5)
        finally:
            loop.remove_reader(descriptor)
            os.close(descriptor)
    asyncio.run(exited())


def assert_assembled(workflow, fixture):
    settings = fixture['settings']
    wired = fixture['parameters']['services']['version'] == 'assembled_case_services_v2'
    assert workflow.episode_bindings.as_record() == settings['episode_bindings']
    assert [row['binding_id'] for row in settings['episode_bindings']] == [
        'scientific_process','literature','execution_episodes' if wired else 'resource_episodes','monitor']
    assert workflow.annotation_child_roles == ROOT_ROLES
    assert tuple(grain.name for grain in workflow.tree.allowed_children('annotation')) == ROOT_ROLES
    assert tuple(grain.name for grain in workflow.tree.allowed_children('scientific_process')) == ROOT_ROLES
    assert 'monitor' not in {grain.name for grain in workflow.tree.allowed_children('literature')}
    assert set(workflow.role_credit_projectors) == {*OPERATIONAL_ROLES,'monitor'}
    assert type(workflow.project_credit) is ScientificFindingProgress
    assert workflow.project_credit is workflow.project_child_credit
    assert workflow.project_annotation_score is None
    assert workflow.project_credit.policy.finding_unit == fixture['parameters']['policy'][
        'scientific_progress']['finding_unit']
    assert workflow.scientific_process_binding.tool_retrieval == RETRIEVAL
    actual = workflow.tools.catalog()
    actual = [{'name':name,**value} for name,value in actual.items()]
    assert workflow.scientific_process_binding.tool_library.catalog() == sorted(actual,key=lambda row:row['name'])
    assert not any(row['name'].startswith('process.') for row in actual)
    assert workflow.progress_provider.job_provider.store is workflow.store
    if wired:
        assert workflow.progress_provider.job_provider.targets.api_execution.tools is workflow.tools
        assert workflow.episode_application_services_binding['inputs'] == 'actual_tool_registry_v1'
    else:
        assert workflow.progress_provider.job_provider.jobs is workflow.job_episodes.jobs
    assert workflow.episode_job_progress_provider_binding == settings['episode_job_progress_provider']
    resource = workflow.role_credit_projectors['launch']
    if wired:
        assert all(workflow.role_credit_projectors[role].__self__ is resource.__self__ for role in OPERATIONAL_ROLES)
        assert resource.__self__.store is workflow.store
        assert resource.__self__.run_id == fixture['run_id']
    else:
        assert all(workflow.role_credit_projectors[role] is resource for role in OPERATIONAL_ROLES)
        assert resource.reader.store is workflow.store and resource.reader.jobs is workflow.job_episodes.jobs
        assert resource.reader.run_id == fixture['run_id']
    monitor = workflow.role_credit_projectors['monitor']
    assert monitor.progress_provider.store is workflow.store
    assert monitor.progress_provider.run_id == fixture['run_id']


def test_actual_publication_ordinary_caller_freezes_a0_p19_without_adoption(tmp_path, monkeypatch):
    fixture = initialize_case(tmp_path, monkeypatch)
    settings = fixture['settings']
    assert settings['episode_application_services']['version'] == 'episode_application_services_v2'
    assert settings['episode_application_services']['inputs'] == 'actual_tool_catalog_v1'
    assert settings['episode_application_services']['definition'] == fixture['parameters']['services']
    assert settings['models'] == fixture['manifest']['configuration']['models']
    assert settings['annotation_child_roles'] == list(ROOT_ROLES)
    assert settings['execution_expectations']['homology']['planning_roles'] == ['annotation','scientific_process']
    assert settings['episode_record_receipts'] == {'version':'explicit_store_record_receipts_v1','enabled':True}
    assert settings['episode_execution']['version'] == 'durable_episode_application_v1'
    with Store(fixture['workspace']) as store, prepared_case_bindings(store, fixture['directory']) as (_, options):
        workflow = reopen(fixture,store,options,Provider([]))
        assert_assembled(workflow,fixture)
        headers = workflow.scientific_process_binding.library.headers()
        assert len(headers) == 19 and all(row['option_ref']['slot'] == 'thought_pattern' for row in headers)
        with pytest.raises(ValueError,match='scientific_process_option_unknown'):
            workflow.scientific_process_binding.library.reference('A01')
        root = workflow.build('annotation','root',settings['goal'],
            {'subject_refs':[fixture['manifest']['target_ref']]})
        schema = workflow.action_schema(root.source)['properties']['selection']['anyOf']
        choices = [(row['properties']['kind']['const'],row['properties'].get('role',{}).get('const'))
            for row in schema]
        assert [role for kind,role in choices if kind == 'episode_child'] == list(ROOT_ROLES)
        assert not any(kind in {'child','job_child'} for kind,_ in choices)
        assert workflow.job_episode_options(root.source) is None
        with pytest.raises(ValueError,match='scientific_process_result_library_invalid'):
            workflow.report_sources('scientific_process')
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
        assert options['job_episodes'].jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
    assert not fixture['turns'].exists()


@pytest.mark.parametrize('wired', [False, True])
def test_c1_reopens_original_assembled_map_scope_form_and_frozen_scientific_inputs(tmp_path,monkeypatch,wired):
    fixture = commission_fixture(tmp_path,monkeypatch,wired=wired)
    spec = fixture['spec']
    fixture['policy'].write_text('raise AssertionError("Use the saved caller source")\n')
    (fixture['source']/'entries/A01.json').write_text('{"changed_staging_source":true}\n')
    (fixture['case']/'target.fna').unlink()
    entered,released = [],[]
    async def enter(provider):
        entered.append(provider)
        return provider
    async def release(provider,episode_id):
        released.append(episode_id)
    monkeypatch.setattr(ModelConnection,'__aenter__',enter)
    monkeypatch.setattr(ModelConnection,'complete',forbidden)
    monkeypatch.setattr(ModelConnection,'release',release)
    monkeypatch.setattr(HomologyJobs,'order',forbidden)
    monkeypatch.setattr(HomologyJobs,'submit',forbidden)
    async def inspect():
        async with independent.open_commission(spec) as runtime:
            episode = runtime['episode']
            workflow = episode.source.workflow
            assert_assembled(workflow,fixture)
            assert episode.request.as_record() == spec['child']['request']
            assert episode.request.report_contract.schema == fixture['schema']
            assert episode.request.message.as_record()['knowledge_inheritance'] == fixture['frozen']
            known = set(workflow.receipts.known(episode.source.episode_id))
            assert set(fixture['known']) <= known and fixture['later'] not in known
            frame = workflow.scientific_process_binding.decision_context(
                workflow.binding_context(episode.source),{})['scientific_process']
            assert frame['selection'] == fixture['selection']
            assert frame['permitted_children'] == list(ROOT_ROLES)
            names = {row['name'] for row in workflow.catalog(episode.source.scope,source=episode.source)}
            assert set(SELECTED_TOOLS) <= names and 'source.archive.extract' not in names
            assert workflow.source_credit_view(episode.source)['credit'] == 0
            assert observations(workflow.store,episode.source.episode_id) == []
    asyncio.run(inspect())
    assert len(entered) == 1 and released == [spec['child']['episode_id']]
    assert not fixture['turns'].exists()


def rewrite_settings(fixture,spec,settings):
    (fixture['directory']/'run.json').write_text(canonical({'run_id':fixture['run_id'],**settings})+'\n')
    with Store(fixture['workspace']) as store:
        with store.transaction():
            store.db.execute('UPDATE runtime_runs SET settings=? WHERE run_id=?',
                (canonical(settings),fixture['run_id']))
    spec['runtime_binding']['settings_sha256'] = content_digest(settings)


@pytest.mark.parametrize('changed',[
    'service_protocol','root_roles','service_units','role_units','reader_registry',
    'retrieval_configuration','assignment','scope','input_digest','requested_form',
    'saved_slot_body','map_missing','map_added','map_schema',
])
def test_changed_assembled_operands_fail_before_provider_transport(tmp_path,monkeypatch,changed):
    fixture = commission_fixture(tmp_path,monkeypatch)
    spec,settings = deepcopy(fixture['spec']),deepcopy(fixture['settings'])
    if changed == 'assignment':
        spec['child']['request']['message']['episode_assignment']['constraints']['changed'] = True
    elif changed == 'scope':
        spec['child']['scope']['segments'] = [{'target_ref':fixture['manifest']['target_ref'],
            'start':0,'end':30,'unit':'nt'}]
    elif changed == 'input_digest':
        assert spec['input_versions']
        spec['input_versions'][0]['content_sha256'] = '0'*64
    elif changed == 'requested_form':
        spec['child']['request']['report_contract']['measurements']['schema'][
            'properties']['finding_state']['enum'].append('changed')
    elif changed == 'saved_slot_body':
        path = fixture['directory']/'scientific-process-library/entries/A01.json'
        path.write_text(path.read_text()+' ')
    elif changed.startswith('map_'):
        original = tool_configuration.build_tools
        def changed_tools(*args,**kwargs):
            tools = original(*args,**kwargs)
            actual = tools.catalog
            def catalog(*args,**kwargs):
                value = deepcopy(actual(*args,**kwargs))
                if changed == 'map_missing':
                    del value['translation.codes']
                elif changed == 'map_added':
                    value['forged.additional.contract'] = deepcopy(value['translation.codes'])
                else:
                    value['translation.codes']['input_schema'] = {'type':'null'}
                return value
            tools.catalog = catalog
            return tools
        monkeypatch.setattr(tool_configuration,'build_tools',changed_tools)
    else:
        if changed == 'service_protocol':
            settings['episode_application_services'].pop('inputs')
            settings['episode_application_services']['version'] = 'episode_application_services_v1'
        elif changed == 'root_roles':
            settings['annotation_child_roles'].append('job_launch')
        elif changed == 'service_units':
            settings['episode_application_services']['definition']['handoff_unit'] = 99
        elif changed == 'role_units':
            settings['episode_role_credit_bindings']['launch_local']['definition']['handoff_unit'] = 99
        elif changed == 'reader_registry':
            settings['episode_job_progress_provider']['registry_ref'] = 'execution_registry_changed'
        else:
            settings['episode_bindings'][0]['configuration']['tool_retrieval']['model']['model'] = 'changed'
        rewrite_settings(fixture,spec,settings)
    entered = []
    async def enter(provider):
        entered.append(provider)
        raise AssertionError('Deterministic reconstruction mismatch reached provider transport')
    monkeypatch.setattr(ModelConnection,'__aenter__',enter)
    monkeypatch.setattr(ModelConnection,'complete',forbidden)
    monkeypatch.setattr(HomologyJobs,'order',forbidden)
    monkeypatch.setattr(HomologyJobs,'submit',forbidden)
    async def inspect():
        with pytest.raises((DurableExecutionError,ValueError)) as failure:
            async with independent.open_commission(spec):
                raise AssertionError('Changed original operands reconstructed successfully')
        if isinstance(failure.value,DurableExecutionError):
            assert failure.value.failure['code'] in {'identity_conflict','unavailable_binding'}
    asyncio.run(inspect())
    assert entered == [] and not fixture['turns'].exists()
    with Store(fixture['workspace']) as store:
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 1


def test_real_detached_assembled_worker_original_form_single_parent_receipt_and_replay(tmp_path,monkeypatch):
    fixture = commission_fixture(tmp_path,monkeypatch)
    spec,directory = fixture['spec'],fixture['directory']
    fixture['policy'].write_text('raise AssertionError("Use the original policy snapshot")\n')
    (fixture['source']/'entries/P01.json').unlink()
    with Store(fixture['workspace']) as store, prepared_case_bindings(store,directory) as (_,options):
        workflow = reopen(fixture,store,options,Provider([]))
        workflow.configure_execution(spec['runtime_binding'])
        root = workflow.build('annotation','root',fixture['settings']['goal'],spec['child']['scope'])
        assert root.request.as_record() == fixture['root_request']
        started = workflow.dispatch_commission(root.source,0,spec)
        assert started['execution_identity']['pid'] != os.getpid()
        async def returned():
            await asyncio.wait_for(workflow.execution_backend.wait_events({
                'version':'event_condition_v1','events':[{'handle':spec['handle'],
                    'event':'returned','after_cursor':0}],'reconsider_at':None}),30)
        asyncio.run(returned())
        backend = workflow.execution_backend
        status = backend.status(spec['handle'])
        result = backend.load_return(spec['handle'],status['return_id'])
        assert result['outcome'] == 'closed' and result['failure'] is None,result
        assert result['completion']['units_consumed'] == 2
        form = result['form']
        assert set(form) == set(fixture['schema']['properties'])
        assert form['finding_state'] == 'measured'
        assert form['local_credit'] == 0 and 'support' not in form
        assert {store.get(ref)['record_type'] for ref in form['records']} == {'source','observation'}
        process, = form['process_results']
        expected_selection = {**fixture['selection'], 'version': SELECTION_REPORT_VERSION,
            'source_version': fixture['selection']['version']}
        assert process['selection'] == expected_selection
        assert process['completed_actions'] == 2 and process['origin_kind'] == 'ordinary_child'
        assert observations(store,root.source.episode_id) == []
        before = list(store.db.execute('SELECT * FROM runtime_record_receipts WHERE episode_id=?',
            (root.source.episode_id,)))
        root.source.restore()
        slot = workflow.next_return(root.source)
        assert slot['kind'] == 'child_return' and slot['sequence'] == 0
        assert slot['original_decision_index'] == 0
        received = [dict(row) for row in store.db.execute(
            "SELECT * FROM runtime_record_receipts WHERE episode_id=? AND receipt_kind='child_form'",
            (root.source.episode_id,))]
        assert {row['record_ref'] for row in received} >= set(form['records'])
        # The current assembled root owns reasoning and child commissions.
        # Record an explicit unresolved claim as its second zero-progress action
        # while checking that it receives only the original child form.
        def after_return(context):
            assert context['child_reports'] == [form]
            commit = {key: [] for key in store.reasoning_schema()['required']}
            commit['hypotheses'] = [{'alias': 'fixture_unresolved_family',
                'subject_refs': [fixture['manifest']['target_ref']], 'predicate': 'functional_family',
                'value': {'type': 'enum', 'value': 'unresolved'}, 'context_refs': []}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        workflow.provider.script = iter([after_return])
        closed = asyncio.run(root.run_async(workflow.context))
        asyncio.run(root.build_result(closed))
        parent_rows = observations(store,root.source.episode_id)
        assert len(parent_rows) == 2
        assert [row['decision_index'] for row in parent_rows] == [0,1]
        assert [row['step']['marginal_credit'] for row in parent_rows] == [0,0]
        assert len(observations(store,spec['child']['episode_id'])) == 2
        assert store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_completion_slots WHERE episode_id=? '
            "AND json_extract(slot,'$.kind')='child_return'",(root.source.episode_id,)).fetchone()[0] == 1
        assert backend.status(spec['handle'])['acknowledgment_id'] == slot['child_return']['admission_id']
        assert workflow.next_return(root.source) is None
        after = [dict(row) for row in store.db.execute(
            "SELECT * FROM runtime_record_receipts WHERE episode_id=? AND receipt_kind='child_form'",
            (root.source.episode_id,))]
        assert after == received
        assert len(list(store.db.execute('SELECT * FROM runtime_record_receipts WHERE episode_id=?',
            (root.source.episode_id,)))) >= len(before)
        assert workflow.context.runtime._controllers == {}
        assert workflow.context._active_episodes == {}
        assert backend.start(spec['handle'])['execution_identity'] == started['execution_identity']
        assert backend.load_return(spec['handle'],result['return_id']) == result
        wait_for_worker_exit(started['execution_identity'])
        assert backend.status(spec['handle'])['liveness'] == 'not_live'
        operations = [row[0] for row in store.db.execute('SELECT name FROM tool_operations '
            'WHERE operation_key LIKE ? ORDER BY name',(fixture['run_id']+':%',))]
        assert operations == sorted(SELECTED_TOOLS)
        assert options['job_episodes'].jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
        assert store.count('assessment') == store.count('annotation') == 0
        frozen = workflow.receipts.manifest(spec['child']['episode_id'])
        assert frozen == fixture['frozen']
        assert fixture['later'] not in workflow.receipts.known(spec['child']['episode_id'])
        for field in ('episode_archive','result_archive','facts_archive'):
            descriptor = result[field]
            assert ArchivedRecord(directory/'archive'/descriptor['file'],descriptor['sha256'],
                descriptor['index_sha256']).load()
        evidence = {'version':'assembled_case_engineering_verification_v1',
            'implementation_sha256':spec['runtime_binding']['implementation_sha256'],
            'settings_sha256':spec['runtime_binding']['settings_sha256'],
            'worker_identity':started['execution_identity'], 'return_id':result['return_id'],
            'original_request':spec['child']['request'], 'form':form,
            'parent_observations':parent_rows,
            'child_observations':observations(store,spec['child']['episode_id']),
            'parent_child_receipts':received, 'configured_model_science':False,
            'native_jobs_submitted':0, 'adopted_support_options':0}
        (tmp_path/'verification.json').write_text(canonical(evidence)+'\n')
    calls = [json.loads(line) for line in fixture['turns'].read_text().splitlines()]
    assert len(calls) == 2 and all(call['pid'] != os.getpid() for call in calls)
    assert all(call['context']['requested_form'] == fixture['schema'] for call in calls)
    assert all(call['context']['scientific_process']['selection'] == fixture['selection'] for call in calls)
    retired = list((directory/'providers').glob('*/retired-sessions/*.json'))
    assert len(retired) == 1
    assert json.loads(retired[0].read_text())['remaining_active_workers'] == 0
