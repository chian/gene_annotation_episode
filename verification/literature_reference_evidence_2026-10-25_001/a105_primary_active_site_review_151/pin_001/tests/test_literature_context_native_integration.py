"""Native-context reader information through original ordinary typed returns."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from types import SimpleNamespace
import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy,ScientificFindingProgress
from gene_annotation_episode.literature_context_storage import context_semantic_cells_schema
from gene_annotation_episode.literature_context_native_storage import native_observations_schema
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_context_native_observations import native_fixture
from test_literature_context_meanings import reopen_read_only
from test_runtime import FixtureController,ScriptedProvider


@pytest.mark.parametrize('request_native',[True,False])
def test_actual_original_form_subset_own_parent_and_first_readonly_reconstruction(tmp_path,monkeypatch,request_native):
    store,context,args,sources,data=native_fixture(tmp_path/'state')
    with store:
        assignment=dict(version='literature_assignment_v1',question_context_refs=[],source_refs=list(context.received_record_refs),
            requested_context_components=['selected_point'],requested_context_native_positions=[0])
        fields={'chosen_context':context_semantic_cells_schema()}
        if request_native:fields['native_context']=native_observations_schema()
        form=obj(fields);captured={};empty={name:[] for name in store.reasoning_schema()['required']}
        root=sources['root'];quote=store.get_artifact(root['artifact_ref']).decode()
        def next_action(inputs,kind):
            captured[kind]=deepcopy(inputs)
            text=render_literature_experimental_prompt(inputs,'Constructed native contextual investigation')
            steering=text.split('\n\nSTEERING\n',1)[1]
            if kind=='own' or request_native:
                assert 'Native context observations' in steering
                assert 'source-reported measurement' in steering and 'technical' in steering
            if kind=='parent':
                report,=inputs['child_reports'];assert report['chosen_context'][0]['value']==.5
                if request_native:
                    row,=report['native_context'];assert row['observation_position']==0 and row['lower']==1
                    assert row['reported_count']==3 and row['replicate_kind']=='technical'
                    assert 'Culture B' not in steering
                else:
                    assert 'native_context' not in report and 'Native context observations' not in steering
            for private in ['private-glucose','context_literal_','context_native_measurement_']:
                assert private not in steering
            commit=deepcopy(empty);commit['source_subjects']=[dict(alias=kind,reference_type='assay',source_ref=root['id'],label='context' if kind=='own' else 'experiment',
                anchor=dict(source_ref=root['id'],artifact_ref=root['artifact_ref'],start=0,end=len(quote),quote=quote))]
            return dict(selection=dict(kind='reason',commit=commit),report_update={})
        provider=ScriptedProvider([
            dict(selection=dict(kind='episode_child',role='literature',assignment=assignment,goal='Evaluate the constructed glucose context evidence',
                scope=plain(context.scope),purpose='Return selected coverage and explicitly requested native observations',schema_json=json.dumps(form),initial_report_json='{}'),report_update={}),
            dict(selection=dict(kind='tool',tool='literature.context.populate',arguments=args),report_update={}),
            lambda inputs:next_action(inputs,'own'),lambda inputs:next_action(inputs,'parent')])
        scorer=ScientificFindingProgress(FindingProgressPolicy(1))
        result=asyncio.run(run_workflow(store,ToolRegistry(store),provider=provider,run_dir=tmp_path/'run',
            controller_factory=lambda path,initial:FixtureController(str(path),initial,2),project_credit=scorer,
            initial_known_record_refs=list(context.received_record_refs),episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,
                reference_parent_sources=[root['id']]),),binding_definitions={'credit':scorer.as_record()}))
        assert set(captured)=={'own','parent'}
        observations=[dict(r) for r in store.db.execute('select * from runtime_observations')];assert len(observations)==4
        assert store.db.execute('select count(*) from literature_context_operations').fetchone()[0]==1
        assert not store.list('observation') and not store.list('assessment')
        attempt,=store.db.execute('select * from runtime_report_attempts').fetchall()
        assert json.loads(attempt['form'])==captured['parent']['child_reports'][0]
        child=store.db.execute('select request from runtime_episodes where episode_id=?',(attempt['child_episode_id'],)).fetchone()
        assert json.loads(child['request'])['report_contract']['measurements']['schema']==form
        parent_row=store.db.execute('select * from runtime_episodes where json_array_length(path)=1').fetchone()
        request=json.loads(parent_row['request'])
        parent=BindingContext(result['run_id'],parent_row['episode_id'],'annotation',tuple(tuple(p) for p in json.loads(parent_row['path'])),
            plain(context.scope),{},request,tuple(captured['parent']['literature_received_fact_display']['received_refs']))
        sheet_ref=captured['parent']['child_reports'][0]['chosen_context'][0]['sheet_ref'];saved=store.get(sheet_ref)
        allowed={saved['artifact_ref'],saved['request_ref']};read=store.get_artifact;access=[]
        def saved_only(ref):
            assert ref in allowed;access.append(ref);return read(ref)
        def forbidden(*a,**kw):raise AssertionError('source/parser/calculator/model/mutation during read-only reconstruction')
        reopen_read_only(store)
        monkeypatch.setattr(store,'get_artifact',saved_only)
        for name in ['artifact','put','transaction','commit_reasoning']:monkeypatch.setattr(store,name,forbidden)
        monkeypatch.setattr('gene_annotation_episode.providers.ModelConnection',forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_context_storage.read_context_inputs',forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_context_storage.populate_context_compatibility',forbidden)
        binding=LiteratureEpisodes(WorkflowServices(SimpleNamespace(store=store,run_id=result['run_id'])),rate_population=True,
            reference_parent_sources=[root['id']])
        facts=binding.received_report_facts(parent)
        if request_native:
            assert facts['literature_context_native_observations']==captured['parent']['child_reports'][0]['native_context']
        else:assert 'literature_context_native_observations' not in facts
        restored=binding._received_fact_display_context(parent)
        assert restored['literature_received_fact_display']['records']==captured['parent']['literature_received_fact_display']['records']
        assert store.db.total_changes==0
        assert [dict(r) for r in store.db.execute('select * from runtime_observations')]==observations
        assert json.loads(store.db.execute('select form from runtime_report_attempts').fetchone()[0])==captured['parent']['child_reports'][0]
