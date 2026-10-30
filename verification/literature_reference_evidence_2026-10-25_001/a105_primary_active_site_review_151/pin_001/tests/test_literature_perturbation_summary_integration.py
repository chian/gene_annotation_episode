"""Constructed selected A106 summary operations and exact typed possession."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_perturbation_storage import LiteraturePerturbationRepository, perturbation_cells_schema
from gene_annotation_episode.literature_perturbation_summary_storage import (
    LiteraturePerturbationSummaryProjection, perturbation_summary_cells_schema,
)
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider
from test_literature_perturbation_summary import source_data, paired_data, arguments, TEXT, graph_data, IMAGE

REQUESTED=["perturbation_difference","W_mean_variance","perturbation_mean_variance","perturbation_variance_upper","reference_restoration_index"]
FORM=obj({"measurements":perturbation_summary_cells_schema()})


def source(store,body,parents=()):
    artifact=store.artifact(body,'application/octet-stream')
    return store.put('source',{'provider':'constructed_a106_summary','accession':None,'uri':None,
        'artifact_ref':artifact,'text_ref':None,'request_ref':None,'version':None,'retrieved_at':None,
        'parent_source_refs':list(parents)},origin='caller')


def fixture(path,*,paired=False,graph=False):
    store=Store(path);store.create_problem(raw_sequence='ATGGCT',molecule='dna')
    root=source(store,TEXT);refs=[root['id']]
    data=paired_data() if paired else source_data()
    if graph:
        data,images=graph_data()
        image=source(store,images[IMAGE],parents=[root['id']]);refs.append(image['id'])
        data['measurements']['W']['graph']['source_ref']=image['id']
    retained=source(store,canonical(data),parents=[root['id']]);refs.append(retained['id'])
    args=arguments();args.update(source_ref=root['id'],data_source_ref=retained['id'])
    for witness in args['interpretation_witnesses']:witness['source_ref']=root['id']
    args['literals']['molecule']={**args['interpretation_witnesses'][0]}
    assignment={'version':'literature_assignment_v1','question_context_refs':[],'source_refs':refs,
        'requested_perturbation_summary_components':REQUESTED}
    context=BindingContext('summary-fixture-run','summary-child','literature',(('literature','fixture'),),
        store.validate_scope(),assignment,{},tuple(refs))
    return store,context,args


def binding_for(store,context):
    host=SimpleNamespace(store=store,run_id=context.run_id,tools=ToolRegistry(store))
    binding=LiteratureEpisodes(WorkflowServices(host),rate_population=True)
    host.episode_bindings=EpisodeBindingRegistry((binding,))
    return binding


@pytest.mark.parametrize('paired',[False,True])
def test_selected_summary_saved_exact_subset_no_source_recalculation_and_read_only(tmp_path,monkeypatch,paired):
    store,context,args=fixture(tmp_path,paired=paired)
    with store:
        binding=binding_for(store,context)
        outcome=asyncio.run(binding.execute(context,'literature.perturbation.populate',args,'selected'))
        assert outcome['status']=='completed',outcome.get('feedback')
        current=replace(context,received_record_refs=(*context.received_record_refs,*outcome['record_refs']))
        sheet=outcome['result']['sheet_ref'];repo=LiteraturePerturbationRepository(store,context.run_id).summary_projection()
        facts=binding.facts(current,{'committed_record_refs':[sheet]})
        assert facts['literature_perturbation_cells']==[]
        form=form_with_facts({},FORM,facts);binding.validate_report(current,form,FORM)
        assert [r['component'] for r in form['measurements']]==REQUESTED
        assert form['measurements'][1]['value']==pytest.approx(4/3 if paired else 1)
        assert form['measurements'][2]['value']==(pytest.approx(1/3) if paired else None)
        assert form['measurements'][-1]['value'] is None
        parent=replace(current,episode_id='summary-parent',role='annotation',assignment={},path=(('annotation','root'),))
        binding.received_form_references(parent,form,FORM,'manual-fixture-admission')
        assert repo.received_cells(parent)==form['measurements']
        parent=replace(parent,received_record_refs=(sheet,*[v for v in repo.read(sheet)['experimental_bindings'].values() if v]))
        assert repo.fact_cells(parent,[sheet],components=['K_summary_value'])==[]
        private=repo.project_cells([sheet],permitted_record_refs=current.received_record_refs,components=['K_summary_value'])
        with pytest.raises(ContractError,match='cell_not_received'):
            repo.validate_fact_values(parent,private)
        assert [r['component'] for r in repo.fact_cells(parent,[sheet],components=REQUESTED)]==REQUESTED
        bad=deepcopy(form['measurements']);bad[0]['value']=99
        with pytest.raises(ContractError,match='differs_from_saved'):
            repo.validate_returned_values(bad,permitted_record_refs=current.received_record_refs)
        saved=store.get(sheet);allowed={saved['artifact_ref'],saved['request_ref']}
        get_artifact=store.get_artifact
        def saved_only(reference):
            assert reference in allowed,'read-only replay cannot open source data or images'
            return get_artifact(reference)
        def forbidden(*a,**kw):raise AssertionError('no parser, arithmetic or mutation during replay')
        monkeypatch.setattr(store,'get_artifact',saved_only)
        monkeypatch.setattr('gene_annotation_episode.literature_perturbation_storage.read_perturbation_inputs',forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_perturbation_storage.populate_source_summary_restoration',forbidden)
        store.db.execute('pragma query_only=ON');before=store.db.total_changes
        assert LiteraturePerturbationRepository(store,context.run_id).populate(context,args,'selected')==outcome
        assert repo.received_cells(parent)==form['measurements']
        assert repo.project_cells([sheet],permitted_record_refs=current.received_record_refs,components=REQUESTED)==form['measurements']
        assert store.db.total_changes==before


def test_graph_bytes_need_actual_receipt_and_assigned_source_before_decoding(tmp_path,monkeypatch):
    store,context,args=fixture(tmp_path,graph=True)
    with store:
        image_ref=context.received_record_refs[1]
        missing=replace(context,received_record_refs=tuple(r for r in context.received_record_refs if r!=image_ref))
        repo=LiteraturePerturbationRepository(store,context.run_id)
        get_artifact=store.get_artifact
        image_artifact=store.get(image_ref)['artifact_ref']
        def no_decode(reference):
            assert reference!=image_artifact,'unpossessed image bytes must never be opened'
            return get_artifact(reference)
        monkeypatch.setattr(store,'get_artifact',no_decode)
        with pytest.raises(ContractError,match='not_received'):repo.populate(missing,args,'denied')
        monkeypatch.setattr(store,'get_artifact',get_artifact)
        out=repo.populate(context,args,'selected')
        saved=repo.read(out['result']['sheet_ref'])
        assert saved['extraction']['summary_data']['graphs']['W']['source_ref']==image_ref
        assert out['result']['cells']['W_summary_value']['value']==pytest.approx(100)
        assert store.db.execute('select count(*) from literature_perturbation_operations').fetchone()[0]==1


def test_new_projection_discovery_is_ddl_free_on_old_read_only_database(tmp_path):
    store,context,_=fixture(tmp_path)
    with store:
        LiteraturePerturbationRepository(store,context.run_id)
        assert store.db.execute("select 1 from sqlite_master where name='literature_perturbation_summary_received'").fetchone() is None
        store.db.execute('pragma query_only=ON');before=store.db.total_changes
        projection=LiteraturePerturbationSummaryProjection(store,context.run_id)
        assert projection.received_cells(context)==[]
        assert store.db.total_changes==before
        assert store.db.execute("select 1 from sqlite_master where name='literature_perturbation_summary_received'").fetchone() is None


def test_summary_operation_in_ordinary_child_admits_exact_form_once_without_extra_observation(tmp_path):
    store,context,args=fixture(tmp_path/'state',paired=True)
    received=[]
    try:
        commission={'selection':{'kind':'episode_child','role':'literature','assignment':plain(context.assignment),
            'goal':'Measure source perturbation precision under actual retained summary relationships',
            'scope':plain(context.scope),'purpose':'Return requested summary cells with uncertainty meanings',
            'schema_json':json.dumps(FORM),'initial_report_json':'{}'},'report_update':{}}
        action={'selection':{'kind':'tool','tool':'literature.perturbation.populate','arguments':args},'report_update':{}}
        def receive(inputs):
            form,=inputs['child_reports'];received.append(form)
            assert [r['component'] for r in form['measurements']]==REQUESTED
            assert form['measurements'][2]['value']==pytest.approx(1/3)
            row=store.get(args['source_ref']);start=TEXT.index(b'Constructed')
            commit={name:[] for name in store.reasoning_schema()['required']}
            commit['source_subjects']=[{'alias':'source_subject','reference_type':'assay','source_ref':row['id'],
                'label':'Constructed','anchor':{'source_ref':row['id'],'artifact_ref':row['artifact_ref'],
                    'start':start,'end':start+11,'quote':'Constructed'}}]
            return {'selection':{'kind':'reason','commit':commit},'report_update':{}}
        scorer=ScientificFindingProgress(FindingProgressPolicy(1))
        result=asyncio.run(run_workflow(store,ToolRegistry(store),provider=ScriptedProvider([commission,action,receive]),
            run_dir=tmp_path/'run',controller_factory=lambda path,initial:FixtureController(str(path),initial,2 if len(path)==1 else 1),
            project_credit=scorer,initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True),),binding_definitions={'credit':scorer.as_record()}))
        assert len(received)==1 and result['credit']==0
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0]==3
        assert store.db.execute('select count(*) from literature_perturbation_operations').fetchone()[0]==1
        assert store.db.execute('select count(*) from literature_perturbation_summary_received').fetchone()[0]==1
        assert not store.list('observation') and not store.list('assessment')
        manifest=json.loads((tmp_path/'run'/'run.json').read_text())
        run=manifest['run_id']
        parent_row,=store.db.execute('select * from runtime_episodes where json_array_length(path)=1').fetchall()
        request=json.loads(parent_row['request'])
        parent=BindingContext(run,parent_row['episode_id'],'annotation',
            tuple(tuple(p) for p in json.loads(parent_row['path'])),plain(context.scope),
            request['message'].get('episode_assignment',{}),request,
            tuple(EpisodeReceipts(store,run).known(parent_row['episode_id'])))
        source_artifacts={store.get(ref)['artifact_ref'] for ref in context.received_record_refs}
        store.close()
        def forbidden(*a,**kw):raise AssertionError('read-only reconstruction must not parse, calculate, model or mutate')
        reopened=Store.__new__(Store);reopened.path=(tmp_path/'state').resolve();reopened._savepoint=0
        reopened.db=sqlite3.connect((reopened.path/'state.sqlite3').as_uri()+'?mode=ro',uri=True,isolation_level=None)
        reopened.db.row_factory=sqlite3.Row;reopened.db.execute('pragma query_only=ON')
        reopened.db.create_function('library_scope_record',2,reopened._scope_filter_record)
        old_get=reopened.get_artifact
        def saved_only(ref):
            assert ref not in source_artifacts,'no original source bytes on first read-only reconstruction'
            return old_get(ref)
        from unittest.mock import patch
        with patch.object(reopened,'get_artifact',saved_only), patch.object(reopened,'put',forbidden), patch.object(reopened,'artifact',forbidden), patch.object(reopened,'transaction',forbidden), patch('gene_annotation_episode.literature_perturbation_storage.read_perturbation_inputs',forbidden), patch('gene_annotation_episode.literature_perturbation_storage.populate_source_summary_restoration',forbidden), patch('gene_annotation_episode.providers.ModelConnection',forbidden):
            from gene_annotation_episode.episode_composition import compose_episode_bindings
            from gene_annotation_episode.episode_journal import Journal
            services=WorkflowServices(SimpleNamespace(store=reopened,run_id=run))
            journal=Journal.__new__(Journal);journal.store=reopened;journal.db=reopened.db;journal.run_id=run
            composition=compose_episode_bindings(services,store=reopened,journal=journal,
                execution_backend=None,descriptors=manifest['episode_bindings'],job_episodes=None,
                resource_estimator=None,role_credit_bindings={})
            binding,=composition.bindings
            rows=binding.received_report_facts(parent)['literature_perturbation_summary_cells']
            assert rows==received[0]['measurements']
            projection=services.literature_perturbation_repository().summary_projection()
            assert projection.fact_cells(parent,[rows[0]['sheet_ref']],components=['K_summary_value'])==[]
            assert reopened.db.total_changes==0
        reopened.close()
    finally:store.close()
