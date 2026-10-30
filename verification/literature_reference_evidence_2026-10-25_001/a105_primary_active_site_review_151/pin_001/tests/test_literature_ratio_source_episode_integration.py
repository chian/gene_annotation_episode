"""Actual selected LiteratureEpisodes with constructed source bytes and choices."""
import asyncio
from copy import deepcopy
from functools import partial
import json
from pathlib import Path

import pytest

from gene_annotation_episode.communication import validate_closed_schema
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
from gene_annotation_episode.literature_ratio_source_storage import LiteratureRatioSourceRepository, ratio_source_cells_schema
from gene_annotation_episode.literature_ratio_source_prompt import SOURCE_RATIO_TASK
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
from literature_ratio_source_worker_fixture_077 import make_case, run_case

DESIGN=Path(__file__).resolve().parents[1]/'verification/literature_reference_evidence_2026-10-25_001/a105_ratio_episode_integration_077'


def test_exact_default_contracts_opt_in_schemas_and_constructor_semantics():
    old=json.loads((DESIGN/'BASELINE_DEFAULT_CONTRACTS_001.json').read_text())
    disabled=LiteratureEpisodes(None,rate_population=True)
    assert _population_catalog()==old['population_catalog']
    assert disabled._rate_fact_sources()==old['fact_sources']
    enabled=LiteratureEpisodes(None,rate_population=True,ratio_source_population=True,
        ratio_source_evidence_origin='synthetic_fixture')
    for role in enabled.roles:
        assert disabled.assignment_schema(role)==old['assignment_schemas'][role]
        modified=enabled.assignment_schema(role);modified['properties'].pop('requested_ratio_source_components')
        assert modified==old['assignment_schemas'][role]
    assert len(_population_catalog(ratio_source_population=True))==20
    assert len(enabled._rate_fact_sources())==19
    assert enabled._rate_fact_sources()['literature_ratio_source_cells']['report_schema']==ratio_source_cells_schema()
    validate_closed_schema(obj({'arbitrary_field':ratio_source_cells_schema()}))
    for args in ({'ratio_source_population':1},{'ratio_source_population':True},
            {'ratio_source_evidence_origin':'synthetic_fixture'},{'ratio_source_evidence_origin':'wrong'}):
        with pytest.raises(ValueError):LiteratureEpisodes(None,**args)
    assert 'ratio_source_population' not in disabled.as_record()['configuration']
    assert enabled.as_record()['configuration']['ratio_source_evidence_origin']=='synthetic_fixture'


@pytest.mark.parametrize('mode',['point','conflict','unreadable','different','unknown'])
def test_actual_selected_view_population_typed_subset_parent_decision_and_observations(tmp_path,mode):
    store,case=make_case(tmp_path/'state')
    try:
        result,provider,controllers=asyncio.run(run_case(store,case,tmp_path/'run',mode=mode))
        assert result['credit']==0
        parents=[state for state in provider.contexts if state.get('child_reports')]
        assert len(parents)==1
        form,=parents[0]['child_reports'];rows=form['requested_signal']
        assert [row['component'] for row in rows]==['reported_ratio']
        row=rows[0]
        if mode=='point':assert row['value']==.64
        elif mode=='conflict':
            assert row['value'] is None and row['value_candidates']==[1,1.12] and row['known_source_conflict']
        else:assert row['value'] is None and not row['point_candidate_set_complete']
        assert row['source_origins']==['synthetic']
        parent_text=provider.presented[-1]
        assert REFERENCE_PARENT_TASK in parent_text and SOURCE_RATIO_TASK not in parent_text
        steering=parent_text.split('\n\nSTEERING\n',1)[1]
        for label in ('K426A','1–253','37 °C','pH 7.4'):assert label in steering
        for hidden in ('128.000','200.000','difference_from_reference','log_reported_ratio','sheet_ref','view_ref'):
            assert hidden not in steering
        assert row['sheet_ref'] not in steering
        assert row['subject_ref'] not in steering
        child_texts=[text for state,text in zip(provider.contexts,provider.presented) if 'literature_assignment' in state]
        assert len(child_texts)==3 and all(SOURCE_RATIO_TASK in text for text in child_texts)
        assert 'requested_ratio_source_components' in child_texts[0]
        saved=LiteratureRatioSourceRepository(store,json.loads((tmp_path/'run/run.json').read_text())['run_id'],
            evidence_origin='synthetic_fixture').read(row['sheet_ref'])
        assert len(saved['sheet']['cells'])==7
        assert len(saved['extraction']['views'])==1
        assert saved['extraction']['views'][0]['metadata']['frame']==1
        # Actual successful runtime form, original contract and exact subset;
        # no manual journal/action/receive fixture is inserted here.
        attempt,=store.db.execute('SELECT * FROM runtime_report_attempts')
        assert json.loads(attempt['form'])==form and attempt['failure'] is None
        received,=store.db.execute('SELECT * FROM literature_ratio_source_received')
        assert json.loads(received['cells'])==rows and received['operation_key'].endswith(':0:typed_form')
        paths={r['episode_id']:json.loads(r['path']) for r in store.db.execute('SELECT * FROM runtime_episodes')}
        identities=[]
        for r in store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index'):
            value=json.loads(r['observation'])
            identities.append((len(paths[r['episode_id']]),r['unit_index'],value['decision_index'],value['label']))
        assert sorted(identities)==[(1,0,0,'child_0'),(1,1,1,'reason:1'),(2,0,0,'tool:0'),(2,1,1,'tool:1')]
        assert all(score==0 for controller in controllers.values for score in controller.scores)
        assert not store.list('observation') and not store.list('assessment')
    finally:store.close()


def test_shared_descriptor_factory_origin_and_replay_actual_saved_output(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from gene_annotation_episode.episode_bindings import BindingContext
    from gene_annotation_episode.tools import ToolRegistry
    store,case=make_case(tmp_path/'state')
    try:
        _,provider,_=asyncio.run(run_case(store,case,tmp_path/'run'))
        manifest=json.loads((tmp_path/'run/run.json').read_text());run=manifest['run_id']
        host=SimpleNamespace(store=store,run_id=run,tools=ToolRegistry(store))
        services=WorkflowServices(host)
        descriptor=manifest['episode_bindings'][0]
        rebuilt,=compose_episode_bindings(services,store=store,journal=Journal(store,run),
            execution_backend=None,descriptors=[descriptor],job_episodes=None,
            resource_estimator=None,role_credit_bindings={}).bindings
        assert rebuilt.as_record()==descriptor and rebuilt.ratio_source_population
        assert rebuilt._ratio_source_repository().evidence_origin=='synthetic_fixture'
        action=store.db.execute("SELECT * FROM runtime_actions WHERE json_extract(action,'$.tool')='literature.ratio.source.populate'").fetchone()
        req=store.db.execute('SELECT * FROM runtime_episodes WHERE episode_id=?',(action['episode_id'],)).fetchone()
        request=json.loads(req['request']);context=BindingContext(run,action['episode_id'],'literature',
            tuple(tuple(p) for p in json.loads(req['path'])),case['scope'],request['message']['episode_assignment'],request,
            tuple(provider.contexts[-2]['visible_record_refs']))
        # Use the actual durable receipts, not guessed context possession.
        from gene_annotation_episode.episode_receipts import EpisodeReceipts
        from dataclasses import replace
        context=replace(context,received_record_refs=tuple(EpisodeReceipts(store,run).known(action['episode_id'])))
        def forbidden(*a,**kw):raise AssertionError('saved replay reacquired or recalculated')
        monkeypatch.setattr('gene_annotation_episode.literature_ratio_source_inputs.read_relative_signal_source_inputs',forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_ratio_source_calculations.populate_relative_signal_v2',forbidden)
        before=store.db.total_changes
        actual=asyncio.run(rebuilt.execute(context,'literature.ratio.source.populate',json.loads(action['action'])['arguments'],
            run+':'+action['episode_id']+':'+str(action['decision_index'])))
        expected=json.loads(action['result']);expected.pop('pending_work_after_action',None)
        assert actual==expected and store.db.total_changes==before
    finally:store.close()


def test_actual_production_open_commission_restores_exact_descriptor_before_transport(tmp_path,monkeypatch):
    from gene_annotation_episode import independent_execution as worker
    from gene_annotation_episode.runtime import run_workflow, assemble_workflow
    from gene_annotation_episode.tool_configuration import build_tools
    from gene_annotation_episode.communication import plain
    from literature_ratio_source_worker_fixture_077 import binding_factory, Provider
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
        value=assemble_workflow(store,build_tools(store),chooser,directory,run,settings,
            episode_binding_descriptors=settings['episode_bindings'],
            **{key:item for key,item in options.items() if key!='binding_definitions'})
        value.configure_execution(runtime_binding)
        root=value.build('annotation','root',settings['goal'],plain(case['scope']))
        # Preserve the initial interrupted request. The actual new selected
        # decision is independently journaled and produces original C1 state.
        root.source.calls=1
        response,index,context,schema=asyncio.run(root.source.call({'goal':root.goal.as_record(),
            'scope':plain(case['scope']),'visible_record_refs':case['source_refs'],
            'tools':value.catalog(case['scope'],source=root.source),'child_reports':[]},value.action_schema(root.source)))
        assert root.source.apply_response(response,index,context,schema) is not None
        spec,=value.commissions.recover_selected(root.source.episode_id)
        value.execution_backend.commission(spec)
        original=deepcopy(spec)
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
            assert binding.ratio_source_population and binding.ratio_source_evidence_origin=='synthetic_fixture'
            assert binding.as_record()==settings['episode_bindings'][0]
            assert workflow.contract_information_profile(episode.source)=='operation_contract_information_v1'
            assert workflow.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==0
    asyncio.run(inspect());assert len(entered)==1
    changed=deepcopy(spec);changed['runtime_binding']['implementation_sha256']='f'*64
    async def reject():
        async with worker.open_commission(changed):raise AssertionError('changed implementation accepted')
    with pytest.raises(Exception,match='identity_conflict'):asyncio.run(reject())
    assert len(entered)==1
