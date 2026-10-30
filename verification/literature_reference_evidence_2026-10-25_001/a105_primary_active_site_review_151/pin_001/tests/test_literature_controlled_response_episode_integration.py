"""Connected scripted episodes and typed custody; no live-model/scientific claim."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import validate_closed_schema
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
from gene_annotation_episode.literature_controlled_response_storage import (
    LiteratureControlledResponseRepository, controlled_response_cells_schema)
from gene_annotation_episode.literature_controlled_response_prompt import CONTROLLED_RESPONSE_TASK
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
from gene_annotation_episode.tools import ToolRegistry
from literature_controlled_response_worker_fixture_095 import make_case, run_case, OPERATION, SOURCE


def test_opt_in_default_contracts_original_descriptor_and_exact_selectors():
    base = Path(__file__).resolve().parents[1]/'verification/literature_reference_evidence_2026-10-25_001'
    old = json.loads((base/'a105_ratio_episode_integration_077/BASELINE_DEFAULT_CONTRACTS_001.json').read_text())
    disabled = LiteratureEpisodes(None,rate_population=True)
    assert _population_catalog()==old['population_catalog']
    assert disabled._rate_fact_sources()==old['fact_sources']
    enabled = LiteratureEpisodes(None,rate_population=True,controlled_response_population=True)
    for role in enabled.roles:
        current = enabled.assignment_schema(role)
        for field in ('requested_controlled_response_components','requested_controlled_response_views',
                'requested_controlled_response_component_keys'):
            current['properties'].pop(field)
        assert current==disabled.assignment_schema(role)==old['assignment_schemas'][role]
    assert len(_population_catalog(controlled_response_population=True))==20
    assert enabled._rate_fact_sources()[SOURCE]['report_schema']==controlled_response_cells_schema()
    validate_closed_schema(obj({'arbitrary_name': controlled_response_cells_schema()}))
    record = enabled.as_record()
    assert LiteratureEpisodes(None,**record['configuration']).as_record()==record
    assert 'controlled_response_population' not in disabled.as_record()['configuration']
    fixture = LiteratureEpisodes(None,rate_population=True,controlled_response_population=True,
        controlled_response_evidence_origin='synthetic_fixture').as_record()
    assert fixture['configuration']['controlled_response_descriptor']['evidence_origin']=='synthetic_fixture'
    changed_profile=deepcopy(fixture['configuration']);changed_profile['controlled_response_evidence_origin']='reported_source'
    with pytest.raises(ValueError,match='implementation_binding'):LiteratureEpisodes(None,**changed_profile)
    changed = deepcopy(record['configuration']); changed['controlled_response_descriptor']['native_schema_sha256']='f'*64
    with pytest.raises(ValueError,match='implementation_binding'):LiteratureEpisodes(None,**changed)
    for args in ({'controlled_response_population':1},{'controlled_response_population':True},
            {'controlled_response_descriptor':{}},{'controlled_response_evidence_origin':'synthetic_fixture'},
            {'controlled_response_evidence_origin':'wrong'}):
        with pytest.raises(ValueError):LiteratureEpisodes(None,**args)


@pytest.mark.parametrize('unresolved,names,views,expected',[
    (False,['controlled_response_difference'],['final'],['final:controlled_response_difference']),
    (False,['local_difference'],['local_difference'],['local:condition0-real:difference']),
    (False,['protein_condition1_response'],['native_raw'],['raw:protein_condition1:primary']),
    (True,['controlled_response_difference'],['conditional'],[
        'joint:0:controlled_response_difference','joint:1:controlled_response_difference']),
    (True,['protein_condition1_response'],['native_raw'],[
        'raw:protein_condition1:primary','raw:protein_condition1:companion:same%3Areading%20%2F%20%CE%B1']),
    (False,[],[],[]),
])
def test_selected_operation_original_return_requested_subset_and_one_observation_per_action(
        tmp_path,unresolved,names,views,expected):
    store,case = make_case(tmp_path/'state',unresolved=unresolved,names=names,views=views)
    try:
        result,provider,controllers = asyncio.run(run_case(store,case,tmp_path/'run'))
        assert result['credit']==0
        parent, = [state for state in provider.contexts if state.get('child_reports')]
        form, = parent['child_reports']; rows = form['requested_response']
        assert [row['component_key'] for row in rows]==expected
        if unresolved and len(rows)==2:
            assert rows[0]['cell']['value']==rows[1]['cell']['value']
            assert rows[0]['component_key']!=rows[1]['component_key']
        assert all(row['context']['source_kinds']==['synthetic_fixture'] for row in rows)
        assert REFERENCE_PARENT_TASK in provider.presented[-1] and CONTROLLED_RESPONSE_TASK not in provider.presented[-1]
        child_texts = [text for state,text in zip(provider.contexts,provider.presented) if 'literature_assignment' in state]
        assert len(child_texts)==3 and all(CONTROLLED_RESPONSE_TASK in text for text in child_texts)
        attempt, = store.db.execute('SELECT * FROM runtime_report_attempts')
        assert attempt['failure'] is None and json.loads(attempt['form'])==form
        action, = store.db.execute("SELECT * FROM runtime_actions WHERE json_extract(action,'$.tool')=?",(OPERATION,))
        outcome = json.loads(action['result'])
        assert 'pending_work_after_action' in outcome
        original, = store.db.execute('SELECT * FROM literature_controlled_response_operations')
        tool_portion = {k:v for k,v in outcome.items() if k!='pending_work_after_action'}
        assert json.loads(original['outcome'])==tool_portion
        paths = {row['episode_id']: json.loads(row['path']) for row in store.db.execute('SELECT * FROM runtime_episodes')}
        observations = []
        for row in store.db.execute('SELECT * FROM runtime_observations'):
            value = json.loads(row['observation'])
            observations.append((len(paths[row['episode_id']]),row['unit_index'],value['decision_index'],value['label']))
        assert sorted(observations)==[(1,0,0,'child_0'),(1,1,1,'reason:1'),(2,0,0,'tool:0'),(2,1,1,'tool:1')]
        assert all(score==0 for controller in controllers.values for score in controller.scores)
        assert not store.list('observation') and not store.list('assessment')
        if rows:
            received, = store.db.execute('SELECT * FROM literature_controlled_response_component_received')
            assert json.loads(received['cells'])==rows
            run = json.loads((tmp_path/'run/run.json').read_text())['run_id']
            repo = LiteratureControlledResponseRepository(store,run,evidence_origin='synthetic_fixture')
            assert all(ref in parent['visible_record_refs'] for ref in repo.cell_record_refs(rows))
    finally:store.close()


def actual_context(store,case,run,episode_id):
    row = store.db.execute('SELECT * FROM runtime_episodes WHERE run_id=? AND episode_id=?',(run,episode_id)).fetchone()
    request = json.loads(row['request'])
    return BindingContext(run,episode_id,json.loads(row['path'])[-1][0],
        tuple(tuple(p) for p in json.loads(row['path'])),case['scope'],request['message'].get('episode_assignment',{}),
        request,tuple(EpisodeReceipts(store,run).known(episode_id)))


def test_original_saved_descriptor_replay_and_exact_parent_subset_without_readers(tmp_path,monkeypatch):
    store,case = make_case(tmp_path/'state',unresolved=True)
    try:
        _,provider,_ = asyncio.run(run_case(store,case,tmp_path/'run'))
        manifest = json.loads((tmp_path/'run/run.json').read_text()); run = manifest['run_id']
        services = WorkflowServices(SimpleNamespace(store=store,run_id=run,tools=ToolRegistry(store)))
        descriptor = manifest['episode_bindings'][0]
        binding, = compose_episode_bindings(services,store=store,journal=Journal(store,run),execution_backend=None,
            descriptors=[descriptor],job_episodes=None,resource_estimator=None,role_credit_bindings={}).bindings
        assert binding.as_record()==descriptor
        action = store.db.execute("SELECT * FROM runtime_actions WHERE json_extract(action,'$.tool')=?",(OPERATION,)).fetchone()
        child = actual_context(store,case,run,action['episode_id'])
        parent_row = store.db.execute("SELECT * FROM runtime_episodes WHERE json_array_length(path)=1").fetchone()
        parent = actual_context(store,case,run,parent_row['episode_id'])
        repo = binding._controlled_response_repository()
        expected = repo.received_cells(parent)
        def forbidden(*args,**kwargs):raise AssertionError('saved replay acquired, decoded, counted or calculated')
        monkeypatch.setattr('gene_annotation_episode.literature_controlled_response_v3_inputs.read_controlled_response_v3_inputs',forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_controlled_response_v3_population.populate_controlled_response_v3',forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_controlled_response_local_calculations.populate_controlled_response_local',forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_figure_measurements.read_mean_bar_ordinates',forbidden,raising=False)
        monkeypatch.setattr('PIL.Image.open',forbidden)
        before = store.db.total_changes
        actual = asyncio.run(binding.execute(child,OPERATION,json.loads(action['action'])['arguments'],
            run+':'+child.episode_id+':'+str(action['decision_index'])))
        original = json.loads(action['result']); original.pop('pending_work_after_action')
        assert actual==original and repo.received_cells(parent)==expected and store.db.total_changes==before
        sheet = expected[0]['sheet_ref']
        # A globally present private raw cell is not a parent's received fact.
        assert repo.fact_cells(parent,[sheet],components=['raw:protein_condition1:primary'])==[]
        assert binding.received_report_facts(parent)[SOURCE]==expected
    finally:store.close()


def test_actual_independent_worker_original_c1_c4_form_and_saved_parent_decision(tmp_path):
    store,case = make_case(tmp_path/'state',unresolved=True)
    try:
        _,provider,_ = asyncio.run(run_case(store,case,tmp_path/'run',durable=True))
        parent, = [state for state in provider.contexts if state.get('child_reports')]
        rows = parent['child_reports'][0]['requested_response']
        assert [row['component_key'] for row in rows]==[
            'joint:0:controlled_response_difference','joint:1:controlled_response_difference']
        worker_text = json.loads((tmp_path/'run/worker095-presentation.json').read_text())
        assert len(worker_text)==3 and all(CONTROLLED_RESPONSE_TASK in text for text in worker_text)
        assert REFERENCE_PARENT_TASK in provider.presented[-1]
        attempt, = store.db.execute('SELECT * FROM runtime_report_attempts')
        assert attempt['failure'] is None
        assert json.loads(attempt['form'])==parent['child_reports'][0]
        assert json.loads(attempt['contract'])['measurements']['schema']['properties']['requested_response']==controlled_response_cells_schema()
        paths = {row['episode_id']:json.loads(row['path']) for row in store.db.execute('SELECT * FROM runtime_episodes')}
        counts = {1:0,2:0}
        for row in store.db.execute('SELECT episode_id FROM runtime_observations'):
            counts[len(paths[row['episode_id']])]+=1
        assert counts=={1:3,2:2}
    finally:store.close()


def test_production_worker_restores_original_controlled_descriptor_before_transport(tmp_path,monkeypatch):
    from gene_annotation_episode import independent_execution as worker
    from gene_annotation_episode.runtime import run_workflow, assemble_workflow
    from gene_annotation_episode.tool_configuration import build_tools
    from gene_annotation_episode.communication import plain
    from literature_controlled_response_worker_fixture_095 import binding_factory, Provider
    store,case=make_case(tmp_path/'state');directory=tmp_path/'run'
    class Interrupted:
        async def complete(self,*a,**kw):raise OSError('constructed pre-action interruption')
        async def release(self,*a):pass
    try:
        with pytest.raises(OSError,match='pre-action'):
            asyncio.run(run_workflow(store,build_tools(store),provider=Interrupted(),run_dir=directory,
                initial_known_record_refs=case['source_refs'],episode_binding_factories=(binding_factory(case),),
                episode_record_receipts=True,decision_protocol='decision_exchange_v1'))
        manifest=json.loads((directory/'run.json').read_text());run=manifest.pop('run_id');settings=manifest
        runtime_binding=worker.make_runtime_binding(store,directory)
        options=worker._standard_bindings(store,directory,settings);worker._check_bindings(options,settings)
        chooser=Provider(store,case)
        workflow=assemble_workflow(store,build_tools(store),chooser,directory,run,settings,
            episode_binding_descriptors=settings['episode_bindings'],
            **{key:value for key,value in options.items() if key!='binding_definitions'})
        workflow.configure_execution(runtime_binding)
        root=workflow.build('annotation','root',settings['goal'],plain(case['scope']))
        root.source.calls=1
        response,index,context,schema=asyncio.run(root.source.call({'goal':root.goal.as_record(),
            'scope':plain(case['scope']),'visible_record_refs':case['source_refs'],
            'tools':workflow.catalog(case['scope'],source=root.source),'child_reports':[]},workflow.action_schema(root.source)))
        assert root.source.apply_response(response,index,context,schema) is not None
        spec,=workflow.commissions.recover_selected(root.source.episode_id)
        workflow.execution_backend.commission(spec);original=deepcopy(spec)
    finally:store.close()
    entered=[]
    class ForbiddenModel:
        def __init__(self,*a,**kw):entered.append(self)
        async def __aenter__(self):return self
        async def __aexit__(self,*a):pass
        async def release(self,*a):pass
        async def complete(self,*a,**kw):raise AssertionError('production factory invoked transport')
    monkeypatch.setattr('gene_annotation_episode.providers.ModelConnection',ForbiddenModel)
    async def inspect():
        async with worker.open_commission(spec) as opened:
            episode=opened['episode'];workflow=episode.source.workflow
            assert episode.request.as_record()==original['child']['request']
            binding=workflow.episode_bindings.for_role('literature')
            assert binding.controlled_response_population and binding.controlled_response_evidence_origin=='synthetic_fixture'
            assert binding.as_record()==settings['episode_bindings'][0]
            assert binding._controlled_response_repository().descriptor()==binding._controlled_response_descriptor
            assert workflow.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==0
    asyncio.run(inspect());assert len(entered)==1
    changed=deepcopy(spec);changed['runtime_binding']['implementation_sha256']='f'*64
    async def reject():
        async with worker.open_commission(changed):raise AssertionError('changed implementation accepted')
    with pytest.raises(Exception,match='identity_conflict'):asyncio.run(reject())
    assert len(entered)==1


def test_unknown_and_conflicting_joint_assignments_cross_the_original_typed_boundary(tmp_path):
    def altered(fixture):
        fixture.args['joint_reading_assignments'][1]['admissibility']={'value':'unknown','witnesses':[]}
        companion=deepcopy(fixture.args['companion_readings'][0]);companion['reading_key']='conflicting explicit reading'
        fixture.args['companion_readings'].append(companion)
        joint=deepcopy(fixture.args['joint_reading_assignments'][1])
        joint['assignment']['protein_condition1']=companion['reading_key']
        joint['admissibility']={'value':'conflicting','witnesses':[
            fixture.witness('nmol/min'),fixture.witness('Construct: protein X.')]}
        fixture.args['joint_reading_assignments'].append(joint)
        scope=deepcopy(fixture.args['joint_scopes'][1]);scope['assignment_index']=2
        fixture.args['joint_scopes'].append(scope)
    store,case=make_case(tmp_path/'state',unresolved=True,alter_fixture=altered)
    try:
        _,provider,_=asyncio.run(run_case(store,case,tmp_path/'run'))
        parent,=[state for state in provider.contexts if state.get('child_reports')]
        rows=parent['child_reports'][0]['requested_response']
        assert [row['component_key'] for row in rows]==['joint:'+str(i)+':controlled_response_difference' for i in range(3)]
        assert [row['joint_scope_context']['effective_admissibility'] for row in rows]==['compatible','unknown','conflicting']
        assert rows[0]['cell']['value'] is not None
        for row,reason in zip(rows[1:],['unknown_joint_applicability','conflicting_joint_applicability']):
            assert row['cell']['status']=='unavailable' and reason in row['cell']['unavailable_reason']
            assert all(row['cell'][field] is None for field in ('value','lower','upper'))
            assert row['dependencies']['numeric_readings']==[] and row['dependencies']['model_readings']==[]
        assert rows[1]['reading_assignment']!=rows[2]['reading_assignment']
        steering=provider.presented[-1].split('\n\nSTEERING\n',1)[1]
        assert 'unknown' in steering and 'conflicting' in steering and 'normalization' in steering
        attempt,=store.db.execute('SELECT * FROM runtime_report_attempts')
        assert attempt['failure'] is None and json.loads(attempt['form'])==parent['child_reports'][0]
    finally:store.close()
