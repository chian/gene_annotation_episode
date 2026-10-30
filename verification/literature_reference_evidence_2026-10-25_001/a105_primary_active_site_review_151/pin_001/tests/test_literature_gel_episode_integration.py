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
from gene_annotation_episode.literature_gel_storage import LiteratureGelRepository
from gene_annotation_episode.literature_gel_native_contracts import gel_cells_schema
from gene_annotation_episode.literature_gel_prompt import GEL_TASK
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
from gene_annotation_episode.tools import ToolRegistry
from literature_gel_worker_fixture_107 import make_case, run_case, OPERATION, SOURCE


def test_opt_in_default_contracts_original_descriptor_and_exact_selectors():
    base = Path(__file__).resolve().parents[1]/'verification/literature_reference_evidence_2026-10-25_001'
    old = json.loads((base/'a105_ratio_episode_integration_077/BASELINE_DEFAULT_CONTRACTS_001.json').read_text())
    disabled = LiteratureEpisodes(None,rate_population=True)
    assert _population_catalog()==old['population_catalog']
    assert disabled._rate_fact_sources()==old['fact_sources']
    enabled = LiteratureEpisodes(None,rate_population=True,gel_population=True)
    for role in enabled.roles:
        current = enabled.assignment_schema(role)
        for field in ('requested_gel_components','requested_gel_views',
                'requested_gel_component_keys'):
            current['properties'].pop(field)
        assert current==disabled.assignment_schema(role)==old['assignment_schemas'][role]
    assert len(_population_catalog(gel_population=True))==20
    both=LiteratureEpisodes(None,rate_population=True,controlled_response_population=True,gel_population=True)
    assert len(_population_catalog(controlled_response_population=True,gel_population=True))==21
    from gene_annotation_episode.literature_controlled_response_storage import controlled_response_cells_schema
    assert both._rate_fact_sources()['literature_controlled_response_component_cells']['report_schema']==controlled_response_cells_schema()
    assert both._rate_fact_sources()[SOURCE]['report_schema']==gel_cells_schema()
    assert LiteratureEpisodes(None,**both.as_record()['configuration']).as_record()==both.as_record()
    assert enabled._rate_fact_sources()[SOURCE]['report_schema']==gel_cells_schema()
    validate_closed_schema(obj({'arbitrary_name': gel_cells_schema()}))
    record = enabled.as_record()
    assert LiteratureEpisodes(None,**record['configuration']).as_record()==record
    assert 'gel_population' not in disabled.as_record()['configuration']
    fixture = LiteratureEpisodes(None,rate_population=True,gel_population=True,
        gel_evidence_origin='synthetic_fixture').as_record()
    assert fixture['configuration']['gel_descriptor']['evidence_origin']=='synthetic_fixture'
    changed_profile=deepcopy(fixture['configuration']);changed_profile['gel_evidence_origin']='reported_source'
    with pytest.raises(ValueError,match='implementation_binding'):LiteratureEpisodes(None,**changed_profile)
    changed = deepcopy(record['configuration']); changed['gel_descriptor']['native_schema_sha256']='f'*64
    with pytest.raises(ValueError,match='implementation_binding'):LiteratureEpisodes(None,**changed)
    for args in ({'gel_population':1},{'gel_population':True},
            {'gel_descriptor':{}},{'gel_evidence_origin':'synthetic_fixture'},
            {'gel_evidence_origin':'wrong'}):
        with pytest.raises(ValueError):LiteratureEpisodes(None,**args)


@pytest.mark.parametrize('alternatives,names,views,expected',[
    (False,['direct_competitor_sensitive_shift'],['comparison'],['comparison:declared:direct_competitor_sensitive_shift']),
    (False,['shifted_display_fraction'],['lane'],[
        'lane:declared:baseline:shifted_display_fraction', 'lane:declared:protein:shifted_display_fraction',
        'lane:declared:competitor:shifted_display_fraction']),
    (False,['sum_darkness'],['raw_region'],[
        'raw:declared:'+lane+':'+region+':sum_darkness'
        for lane in ('baseline','protein','competitor')
        for region in ('background','whole','band:shifted','band:free')]),
    (True,['direct_competitor_sensitive_shift'],['comparison'],[
        'comparison:declared:direct_competitor_sensitive_shift',
        'comparison:same%3Aregion%20%2F%20%CE%B1:direct_competitor_sensitive_shift']),
    (False,[],[],[]),
])
def test_selected_operation_original_return_requested_subset_and_one_observation_per_action(
        tmp_path,alternatives,names,views,expected):
    store,case = make_case(tmp_path/'state',alternatives=alternatives,names=names,views=views)
    try:
        result,provider,controllers = asyncio.run(run_case(store,case,tmp_path/'run'))
        assert result['credit']==0
        parent, = [state for state in provider.contexts if state.get('child_reports')]
        form, = parent['child_reports']; rows = form['requested_response']
        assert [row['component_key'] for row in rows]==expected
        if alternatives and len(rows)==2:
            assert rows[0]['cell']['value']==rows[1]['cell']['value']
            assert rows[0]['component_key']!=rows[1]['component_key']
        assert all(row['origin']=='synthetic' for row in rows)
        assert REFERENCE_PARENT_TASK in provider.presented[-1] and GEL_TASK not in provider.presented[-1]
        child_texts = [text for state,text in zip(provider.contexts,provider.presented) if 'literature_assignment' in state]
        assert len(child_texts)==3 and all(GEL_TASK in text for text in child_texts)
        attempt, = store.db.execute('SELECT * FROM runtime_report_attempts')
        assert attempt['failure'] is None and json.loads(attempt['form'])==form
        action, = store.db.execute("SELECT * FROM runtime_actions WHERE json_extract(action,'$.tool')=?",(OPERATION,))
        outcome = json.loads(action['result'])
        assert 'pending_work_after_action' in outcome
        original, = store.db.execute('SELECT * FROM literature_gel_operations')
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
            received, = store.db.execute('SELECT * FROM literature_gel_component_received')
            assert json.loads(received['cells'])==rows
            run = json.loads((tmp_path/'run/run.json').read_text())['run_id']
            repo = LiteratureGelRepository(store,run,evidence_origin='synthetic_fixture')
            assert all(ref in parent['visible_record_refs'] for ref in repo.cell_record_refs(rows))
    finally:store.close()


def actual_context(store,case,run,episode_id):
    row = store.db.execute('SELECT * FROM runtime_episodes WHERE run_id=? AND episode_id=?',(run,episode_id)).fetchone()
    request = json.loads(row['request'])
    return BindingContext(run,episode_id,json.loads(row['path'])[-1][0],
        tuple(tuple(p) for p in json.loads(row['path'])),case['scope'],request['message'].get('episode_assignment',{}),
        request,tuple(EpisodeReceipts(store,run).known(episode_id)))


def test_original_saved_descriptor_replay_and_exact_parent_subset_without_readers(tmp_path,monkeypatch):
    store,case = make_case(tmp_path/'state',alternatives=True)
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
        repo = binding._gel_repository()
        expected = repo.received_cells(parent)
        display=binding._gel_display_context(parent)
        assert display['literature_gel_return_bindings']==repo.semantic_bindings(expected)
        # Another globally present repository output grants this parent no
        # additional meaning records. It is not a manually seeded native proof.
        content=b'Private constructed experiment Z.'
        artifact=store.artifact(content)
        private_source=store.put('source',{'provider':'constructed107-private','accession':None,'uri':None,
            'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,'version':None,'retrieved_at':None,
            'parent_source_refs':[]},origin='caller')['id']
        arguments=deepcopy(case['arguments'])
        arguments['selection']['context']['experiment']={'state':'known','value':content.decode(),
            'witnesses':[{'source_ref':private_source,'representation':'text','start':0,'end':len(content),'quote':content.decode()}]}
        private_context=replace(child,episode_id='private-repository-fixture',
            received_record_refs=(*child.received_record_refs,private_source))
        private=repo.populate(private_context,arguments,'private-repository-only')
        private_meaning=private['result']['cells'][0]['scientific_context']['global']['experiment']['value_ref']
        assert private_meaning not in parent.received_record_refs
        assert private_meaning not in binding._gel_display_context(parent)['literature_gel_return_records']
        meanings=[m for row in expected for m in row['scientific_context']['global'].values() if m['value_ref'] is not None]
        for meaning in meanings:
            assert display['literature_gel_return_records'][meaning['value_ref']]==store.get(meaning['value_ref'])
        from gene_annotation_episode.domain import ContractError
        missing=meanings[0]['value_ref']
        with pytest.raises(ContractError,match='gel_semantic_display_record_not_received'):
            binding._gel_display_context(replace(parent,received_record_refs=tuple(r for r in parent.received_record_refs if r!=missing)))
        def forbidden(*args,**kwargs):raise AssertionError('saved replay acquired, decoded, counted or calculated')
        monkeypatch.setattr('gene_annotation_episode.literature_gel_inputs.read_gel_inputs',forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_gel_calculations.populate_gel_components',forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_figure_measurements.read_mean_bar_ordinates',forbidden,raising=False)
        monkeypatch.setattr('PIL.Image.open',forbidden)
        before = store.db.total_changes
        actual = asyncio.run(binding.execute(child,OPERATION,json.loads(action['action'])['arguments'],
            run+':'+child.episode_id+':'+str(action['decision_index'])))
        original = json.loads(action['result']); original.pop('pending_work_after_action')
        assert actual==original and repo.received_cells(parent)==expected and store.db.total_changes==before
        sheet = expected[0]['sheet_ref']
        # A globally present private raw cell is not a parent's received fact.
        assert repo.fact_cells(parent,[sheet],components=['raw:declared:protein:band:shifted:sum_darkness'])==[]
        assert binding.received_report_facts(parent)[SOURCE]==expected
    finally:store.close()


def test_actual_independent_worker_original_c1_c4_form_and_saved_parent_decision(tmp_path):
    store,case = make_case(tmp_path/'state',alternatives=True)
    try:
        _,provider,_ = asyncio.run(run_case(store,case,tmp_path/'run',durable=True))
        parent, = [state for state in provider.contexts if state.get('child_reports')]
        rows = parent['child_reports'][0]['requested_response']
        assert [row['component_key'] for row in rows]==[
            'comparison:declared:direct_competitor_sensitive_shift',
            'comparison:same%3Aregion%20%2F%20%CE%B1:direct_competitor_sensitive_shift']
        worker_text = json.loads((tmp_path/'run/worker107-presentation.json').read_text())
        assert len(worker_text)==3 and all(GEL_TASK in text for text in worker_text)
        assert REFERENCE_PARENT_TASK in provider.presented[-1]
        attempt, = store.db.execute('SELECT * FROM runtime_report_attempts')
        assert attempt['failure'] is None
        assert json.loads(attempt['form'])==parent['child_reports'][0]
        assert json.loads(attempt['contract'])['measurements']['schema']['properties']['requested_response']==gel_cells_schema()
        paths = {row['episode_id']:json.loads(row['path']) for row in store.db.execute('SELECT * FROM runtime_episodes')}
        counts = {1:0,2:0}
        for row in store.db.execute('SELECT episode_id FROM runtime_observations'):
            counts[len(paths[row['episode_id']])]+=1
        assert counts=={1:3,2:2}
    finally:store.close()


def test_production_worker_restores_original_gel_descriptor_before_transport(tmp_path,monkeypatch):
    from gene_annotation_episode import independent_execution as worker
    from gene_annotation_episode.runtime import run_workflow, assemble_workflow
    from gene_annotation_episode.tool_configuration import build_tools
    from gene_annotation_episode.communication import plain
    from literature_gel_worker_fixture_107 import binding_factory, Provider
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
            assert binding.gel_population and binding.gel_evidence_origin=='synthetic_fixture'
            assert binding.as_record()==settings['episode_bindings'][0]
            assert binding._gel_repository().descriptor()==binding._gel_descriptor
            assert workflow.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==0
    asyncio.run(inspect());assert len(entered)==1
    changed=deepcopy(spec);changed['runtime_binding']['implementation_sha256']='f'*64
    async def reject():
        async with worker.open_commission(changed):raise AssertionError('changed implementation accepted')
    with pytest.raises(Exception,match='identity_conflict'):asyncio.run(reject())
    assert len(entered)==1


import os
import subprocess
import sys
from gene_annotation_episode.episode_admission import ReceiverBindingV1, admit_return
from gene_annotation_episode.runtime import TypedReportContract
from method_loop.durable import DurableExecutionStore

READONLY = r'''
import json,sqlite3,sys
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
from gene_annotation_episode.state import Store
from gene_annotation_episode.literature_gel_storage import LiteratureGelRepository
from gene_annotation_episode import literature_gel_inputs as inputs
from gene_annotation_episode import literature_gel_calculations as calculations
from gene_annotation_episode import providers
fixture=json.loads(Path(sys.argv[2]).read_text())
def forbidden(*a,**kw):raise AssertionError('forbidden source/reader/image/counter/model/population/receive/mutation')
store=Store.__new__(Store);store.path=Path(sys.argv[1]);store._savepoint=0
store.db=sqlite3.connect(store.path.joinpath('state.sqlite3').resolve().as_uri()+'?mode=ro',uri=True,isolation_level=None)
store.db.row_factory=sqlite3.Row
store.db.execute('PRAGMA query_only=ON')
store.db.create_function('library_scope_record',2,store._scope_filter_record)
get=store.get_artifact;reads=[]
def saved_only(ref):
 if ref in fixture['banned']:raise AssertionError('original source/image bytes accessed')
 reads.append(ref);return get(ref)
store.get_artifact=saved_only
for name in ('artifact','put','transaction','register_material','parse_material'):setattr(store,name,forbidden)
inputs.read_gel_inputs=forbidden;inputs._decode=forbidden
calculations.populate_gel_components=forbidden;calculations._calculate=forbidden
Image.open=forbidden;providers.ModelConnection=forbidden
repo=LiteratureGelRepository(store,fixture['run'],evidence_origin='synthetic_fixture');repo.receive_cells=forbidden
context=SimpleNamespace(run_id=fixture['run'],episode_id=fixture['parent'],role='annotation',assignment={},
 path=fixture['path'],scope=fixture['scope'],received_record_refs=fixture['known'])
assert store.db.total_changes==0
actual=repo.fact_cells(context,[fixture['sheet']],components=fixture['keys'])
assert actual==fixture['admitted']
assert repo.fact_cells(context,[fixture['sheet']],components=['raw:declared:protein:band:shifted:sum_darkness'])==[]
assert repo.received_cells(context)==actual
# Parent has no scientific child assignment; possession is validated by its
# original admitted subset, not by inventing a broad parent request here.
repo.validate_returned_values(actual,permitted_record_refs=context.received_record_refs)
bindings=repo.semantic_bindings(actual)
assert bindings==fixture['bindings']
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
services=WorkflowServices(SimpleNamespace(store=store,run_id=fixture['run']))
binding=LiteratureEpisodes(services,**fixture['binding']['configuration'])
assert binding.as_record()==fixture['binding']
display=binding._gel_display_context(context)
assert display['literature_gel_return_bindings']==bindings
for row in actual:
 meanings=[*row['scientific_context']['global'].values(),*[lane[key] for lane in row['scientific_context']['lanes'] for key in ('subject','construct','endpoint','condition','control_role')]]
 for meaning in meanings:
  if meaning['value_ref'] is not None:assert display['literature_gel_return_records'][meaning['value_ref']]==store.get(meaning['value_ref'])
assert [list(r) for r in store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')]==fixture['observations']
assert store.db.total_changes==0
print(json.dumps({'mode':'ro','total_changes':store.db.total_changes,'first_projection':actual,
 'saved_artifact_reads':len(reads),'observation_count':len(fixture['observations']),
 'evidence_class':'connected scripted107 engineering fixture; no live model'}))
store.close()
'''


@pytest.mark.parametrize('interrupt_receive',[False,True])
def test_real_independent_c1_c4_recovery_replay_and_first_readonly(tmp_path,monkeypatch,interrupt_receive):
    store,case = make_case(tmp_path/'state',alternatives=True); directory=tmp_path/'run'
    original_service=WorkflowServices.literature_gel_repository; injected=[]
    if interrupt_receive:
        def service(self,**kwargs):
            repository=original_service(self,**kwargs)
            if not hasattr(repository,'_fixture_interrupt_installed'):
                repository._fixture_interrupt_installed=True; original=repository.receive_cells
                def receive(context,rows,key):
                    original(context,rows,key)
                    if context.role=='annotation' and not injected:
                        injected.append(key);raise OSError('constructed interruption after actual gel receive')
                repository.receive_cells=receive
            return repository
        monkeypatch.setattr(WorkflowServices,'literature_gel_repository',service)
    try:
        if interrupt_receive:
            with pytest.raises(OSError,match='after actual gel receive'):
                asyncio.run(run_case(store,case,directory,durable=True))
            assert injected
            assert store.db.execute('SELECT count(*) FROM literature_gel_component_received').fetchone()[0]==0
            assert store.db.execute('SELECT count(*) FROM literature_gel_operations').fetchone()[0]==1
        _,provider,_=asyncio.run(run_case(store,case,directory,durable=True,resume=interrupt_receive))
        spec=json.loads(store.db.execute('SELECT spec FROM runtime_commission_intents').fetchone()[0])
        backend=DurableExecutionStore(directory/'episode-execution')
        returned=backend.load_return(spec['handle'],backend.status(spec['handle'])['return_id'])
        assert returned['outcome']=='closed' and returned['failure'] is None and returned['completion']['units_consumed']==2
        parent,child,run=spec['parent']['episode_id'],spec['child']['episode_id'],spec['run_id']
        form,=provider.contexts[-1]['child_reports'];rows=form['requested_response']
        attempt,=store.db.execute('SELECT * FROM runtime_report_attempts')
        assert attempt['failure'] is None and attempt['parent_episode_id']==parent and attempt['child_episode_id']==child
        assert json.loads(attempt['form'])==returned['form']==form
        assert json.loads(attempt['contract'])==spec['child']['request']['report_contract']
        assert store.db.execute('SELECT count(*) FROM runtime_commission_intents').fetchone()[0]==1
        assert store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0]==1
        def forbidden(*a,**kw):raise AssertionError('admission replay called a callback')
        contract=spec['child']['request']['report_contract']
        typed=TypedReportContract(contract['decision'],contract['measurements']['schema'],forbidden)
        receiver=ReceiverBindingV1(store,Journal(store,run),0,typed,forbidden,forbidden,forbidden,forbidden)
        admission=json.loads(store.db.execute('SELECT admission FROM runtime_return_admissions').fetchone()[0])
        before=store.db.total_changes
        assert admit_return(spec,returned,receiver)==admission and store.db.total_changes==before
        repository=LiteratureGelRepository(store,run,evidence_origin='synthetic_fixture');saved=repository.read(rows[0]['sheet_ref'])
        fixture={'run':run,'parent':parent,'path':spec['parent']['path'],'scope':case['scope'],'known':list(EpisodeReceipts(store,run).known(parent)),
            'sheet':rows[0]['sheet_ref'],'keys':[row['component_key'] for row in rows],'admitted':rows,
            'bindings':repository.semantic_bindings(rows),
            'binding':json.loads((directory/'run.json').read_text())['episode_bindings'][0],
            'banned':[store.get(ref)['artifact_ref'] for ref in saved['input_source_refs']],
            'observations':[list(r) for r in store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')]}
        path=tmp_path/'readonly.json';path.write_text(json.dumps(fixture));store.close()
        process=subprocess.run([sys.executable,'-c',READONLY,str(tmp_path/'state'),str(path)],
            text=True,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1',
                'PYTHONPATH':str(Path(__file__).resolve().parents[1])})
        assert process.returncode==0,process.stdout+process.stderr
        proof=json.loads(process.stdout);assert proof['total_changes']==0 and proof['first_projection']==rows
    finally:store.close()


def test_ordinary_reforward_preserves_exact_alternative_and_cannot_expand_private_raw(tmp_path):
    from functools import partial
    from gene_annotation_episode.communication import plain
    from gene_annotation_episode.domain import obj
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.literature_gel_storage import gel_cells_schema
    from gene_annotation_episode.runtime import run_workflow
    from gene_annotation_episode.tools import ToolRegistry
    from literature_gel_worker_fixture_107 import Provider, scorer
    from test_runtime import ScriptedProvider, FixtureController
    store,case=make_case(tmp_path/'state',alternatives=True)
    form_schema=obj({'numbers':gel_cells_schema()})
    outer={'version':'literature_assignment_v1','question_context_refs':[],'source_refs':case['source_refs'],
        'requested_gel_components':['sum_darkness','direct_competitor_sensitive_shift','shifted_display_fraction'],
        'requested_gel_views':['raw_region','comparison','lane']}
    inner={'version':'strategy_assignment_v1','question_context_refs':[],'prior_search_refs':case['source_refs'],
        'requested_gel_components':['direct_competitor_sensitive_shift'],
        'requested_gel_views':['comparison'],
        'requested_gel_component_keys':['comparison:same%3Aregion%20%2F%20%CE%B1:direct_competitor_sensitive_shift']}
    def commission(role,assignment):
        return {'selection':{'kind':'episode_child','role':role,'assignment':assignment,
            'goal':'Evaluate the supplied controlled comparison alternatives','scope':plain(case['scope']),
            'purpose':'Return the requested controlled response alternative only','schema_json':json.dumps(form_schema),
            'initial_report_json':'{}'},'report_update':{}}
    received=[]
    def use(state):
        actual,=state['child_reports'];received.append(deepcopy(actual))
        assert [row['component_key'] for row in actual['numbers']]==['comparison:same%3Aregion%20%2F%20%CE%B1:direct_competitor_sensitive_shift']
        decision=Provider(store,case).reason()['response']
        return {name:decision[name] for name in ('selection','report_update')}
    provider=ScriptedProvider([commission('literature',outer),commission('literature_strategy',inner),
        {'selection':{'kind':'tool','tool':'literature.gel.populate','arguments':case['arguments']},'report_update':{}},
        use,use])
    try:
        result=asyncio.run(run_workflow(store,ToolRegistry(store),provider=provider,run_dir=tmp_path/'run',
            controller_factory=lambda path,initial:FixtureController(str(path),initial,1 if len(path)==3 else 2),
            project_credit=scorer(),initial_known_record_refs=case['source_refs'],episode_record_receipts=True,
            episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,gel_population=True,
                gel_evidence_origin='synthetic_fixture',reference_parent_sources=case['source_refs']),),
            binding_definitions={'credit':scorer().as_record()}))
        assert result['credit']==0 and received[0]==received[1]
        assert store.db.execute('SELECT count(*) FROM literature_gel_operations').fetchone()[0]==1
        assert store.db.execute('SELECT count(*) FROM literature_gel_component_received').fetchone()[0]==2
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==5
        run=json.loads((tmp_path/'run/run.json').read_text())['run_id']
        root=store.db.execute('SELECT episode_id FROM runtime_episodes WHERE json_array_length(path)=1').fetchone()[0]
        from test_literature_gel_episode_integration import actual_context
        context=actual_context(store,case,run,root)
        repository=LiteratureGelRepository(store,run,evidence_origin='synthetic_fixture')
        assert repository.fact_cells(context,[received[0]['numbers'][0]['sheet_ref']],components=['raw:declared:protein:band:shifted:sum_darkness'])==[]
    finally:store.close()


def test_actual_runtime_digest_and_complete_alternate_wrapper_cannot_replace_selected_output(tmp_path):
    from dataclasses import replace
    from gene_annotation_episode.domain import ContractError, canonical
    from test_literature_gel_episode_integration import actual_context
    store,case=make_case(tmp_path/'state')
    try:
        asyncio.run(run_case(store,case,tmp_path/'run'))
        run=json.loads((tmp_path/'run/run.json').read_text())['run_id']
        action=store.db.execute("SELECT * FROM runtime_actions WHERE json_extract(action,'$.tool')='literature.gel.populate'").fetchone()
        context=actual_context(store,case,run,action['episode_id'])
        repository=LiteratureGelRepository(store,run,evidence_origin='synthetic_fixture')
        operation=store.db.execute('SELECT * FROM literature_gel_operations').fetchone()
        outcome=json.loads(operation['outcome']);original_runtime=json.loads(action['result'])
        assert 'pending_work_after_action' in original_runtime
        assert store.db.execute('SELECT count(*) FROM '+repository.runtime_binding_table).fetchone()[0]==1
        observations=[tuple(row) for row in store.db.execute('SELECT * FROM runtime_observations')]
        changed=deepcopy(original_runtime);changed['pending_work_after_action']={'gel_fixture_tampering':True}
        try:
            store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?',
                (canonical(changed),run,context.episode_id,action['decision_index']))
            with pytest.raises(ContractError,match='original_runtime_digest_mismatch'):
                repository.read(outcome['result']['sheet_ref'])
        finally:
            store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?',
                (action['result'],run,context.episode_id,action['decision_index']))
        # Produce a wholly coherent alternate adapter payload/request/source and
        # private operation outcome under the original operation key. This is
        # deliberate DB tampering in a test, never a manually seeded native
        # execution proof. The actual selected runtime record stays unchanged.
        arguments=deepcopy(case['arguments']);arguments['selection']['context']['organism']={'state':'unknown','value':None,'witnesses':[]}
        try:
            store.db.execute('DELETE FROM literature_gel_operations WHERE run_id=? AND episode_id=? AND operation_key=?',
                (run,context.episode_id,operation['operation_key']))
            alternate=repository.populate(context,arguments,operation['operation_key'])
            assert alternate['result']['payload_sha256']!=outcome['result']['payload_sha256']
            with pytest.raises(ContractError,match='original_runtime_mismatch'):
                repository.read(alternate['result']['sheet_ref'])
            with pytest.raises(ContractError,match='original_runtime_mismatch'):
                repository.fact_cells(replace(context,received_record_refs=(*context.received_record_refs,*alternate['record_refs'])),
                    [alternate['result']['sheet_ref']],components=['comparison:declared:direct_competitor_sensitive_shift'])
        finally:
            store.db.execute('DELETE FROM literature_gel_operations WHERE run_id=? AND episode_id=? AND operation_key=?',
                (run,context.episode_id,operation['operation_key']))
            store.db.execute('INSERT INTO literature_gel_operations VALUES(?,?,?,?,?)',tuple(operation))
        assert repository.read(outcome['result']['sheet_ref'])
        assert [tuple(row) for row in store.db.execute('SELECT * FROM runtime_observations')]==observations
        assert store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
            (run,context.episode_id,action['decision_index'])).fetchone()[0]==action['result']
    finally:store.close()


def test_nested_gel_sources_obey_actual_assigned_page_ancestry_before_decoding(tmp_path,monkeypatch):
    store,case=make_case(tmp_path/'state')
    try:
        run='constructed107-page-ancestry'
        services=WorkflowServices(SimpleNamespace(store=store,run_id=run,tools=ToolRegistry(store)))
        binding=LiteratureEpisodes(services,rate_population=True,gel_population=True,gel_evidence_origin='synthetic_fixture')
        root=store.get(case['root'])
        page={'version':'page_assignment_v1','source_ref':root['id'],'representation':'original',
            'artifact_ref':root['artifact_ref'],'question_context_refs':[],'prior_delivery_refs':[]}
        context=BindingContext(run,'constructed-page','literature_page',(('literature_page','selected'),),
            case['scope'],page,{},tuple(case['source_refs']))
        def forbidden(*a,**kw):raise AssertionError('outside-page source was decoded')
        monkeypatch.setattr('PIL.Image.open',forbidden)
        outcome=asyncio.run(binding.execute(context,OPERATION,case['arguments'],'constructed-page-attempt'))
        assert outcome['status']=='invalid'
        assert outcome['feedback']['code']=='literature_reading_outside_assigned_source'
        assert not outcome['record_refs']
        assert store.db.execute("SELECT count(*) FROM sqlite_master WHERE name='literature_gel_operations'").fetchone()[0]==0
    finally:store.close()


@pytest.mark.parametrize('zero_delta',[False,True])
def test_actual_selected_direct_contrast_retains_cancellation_and_negative_signal(tmp_path,zero_delta):
    def alter(selected,comparison,sources):
        if zero_delta:
            comparison['protein_lane_id']='baseline'
        else:
            selected['roi_assignments'][0]['lanes'][0]['background']=[0,3,1,4]
    names=['background_corrected_band_darkness','direct_competitor_sensitive_shift','factorized_competitor_sensitive_shift']
    keys=['corrected:declared:baseline:shifted','comparison:declared:direct_competitor_sensitive_shift',
        'comparison:declared:factorized_competitor_sensitive_shift']
    store,case=make_case(tmp_path/'state',alter_fixture=alter,names=names,views=['corrected_band','comparison'],keys=keys)
    try:
        _,provider,_=asyncio.run(run_case(store,case,tmp_path/'run'))
        parent=next(state for state in provider.contexts if state.get('child_reports'))
        rows={r['component_key']:r for r in parent['child_reports'][0]['requested_response']}
        assert rows[keys[0]]['cell']['value']==(0 if zero_delta else -100)
        direct=rows[keys[1]];factorized=rows[keys[2]]
        assert direct['cell']['value']==pytest.approx(-.2 if zero_delta else .6)
        assert factorized['cell']['value'] is None
        assert factorized['cell']['unavailable_reason']==('zero_protein_associated_display_shift' if zero_delta else 'nonpositive_total_display_darkness')
        assert 'baseline_cancels_from_direct_form' in direct['cell']['qualifications']
        assert direct['cell']['confidence_interval'] is None
        assert all(d['source_dependency']['lane_id'] in ({'baseline','competitor'} if zero_delta else {'protein','competitor'})
            for d in direct['numerical_dependencies'])
        assert not store.list('assessment')
    finally:store.close()


def test_actual_selected_available_only_sensitivity_retains_unavailable_choice(tmp_path):
    def alter(selected,comparison,sources):
        selected['roi_assignments'][1]['lanes'][0]['bands'][0]['region']=None
    component='factorized_competitor_sensitive_shift'
    store,case=make_case(tmp_path/'state',alternatives=True,alter_fixture=alter,names=[component],views=['sensitivity'])
    try:
        _,provider,_=asyncio.run(run_case(store,case,tmp_path/'run'))
        parent=next(state for state in provider.contexts if state.get('child_reports'))
        row,=parent['child_reports'][0]['requested_response']
        assert row['component_key']=='sensitivity:'+component
        cell=row['cell'];info=cell['sensitivity']
        assert cell['value'] is None and cell['lower']==cell['upper']=={'numerator':'3','denominator':'5'}
        assert info['status']=='partial' and info['included_assignment_ids']==['declared']
        assert info['unavailable_assignment_ids']==['same:region / α']
        assert info['bounds_unavailable_assignments'] is False and info['sampling_confidence_level'] is None
        assert cell['confidence_interval'] is None
        assert 'partial' in provider.presented[-1] and 'same:region / α' not in provider.presented[-1]
    finally:store.close()
