"""Retained primary YeaG inputs; scripted decisions, not live model inference."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import ReportBoundaryError,form_with_facts,plain
from gene_annotation_episode.domain import ContractError,canonical,obj
from gene_annotation_episode.episode_bindings import BindingContext,EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy,ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_ratio_storage import LiteratureRatioRepository,ratio_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController,ScriptedProvider

PRIMARY=Path(__file__).resolve().parents[1]/'verification/literature_reference_evidence_2026-10-25_001/primary_yeag'
COMPONENTS=['reported_ratio','difference_from_reference','calibrated_amount_ratio','source_signed_index']
FORM=obj({'measurements':ratio_cells_schema()})


def setup_store(path,variant='K426A',*,visual=True):
    store=Store(path)
    store.create_problem(raw_sequence='ATGGCT',molecule='dna')
    def source(content,provider,parents=()):
        artifact=store.artifact(content,'application/octet-stream')
        return store.put('source',{'provider':provider,'accession':None,'uri':None,
            'artifact_ref':artifact,'text_ref':None,'request_ref':None,'version':None,'retrieved_at':None,
            'parent_source_refs':list(parents)},origin='caller')
    original=(PRIMARY/'PMC4664914_original.xml').read_bytes()
    paper=source(original,'retained_primary_jats')
    image=source((PRIMARY/'srep17524-f3.jpg').read_bytes(),'retained_primary_figure',[paper['id']])
    # Explicit manual transcription of PRINTED labels inspected in the original
    # figure. This is neither OCR nor numerical densitometry of the bands.
    labels={'K116A':('0.64',[161,539,193,557],[100,539,129,557]),
            'R232A':('0.48',[207,539,242,557],[100,539,129,557]),
            'K426A':('1.12',[533,539,567,557],[478,539,510,557]),
            'Y382stop':('0.96',[577,539,611,557],[478,539,510,557])}
    label,box,reference_box=labels[variant]
    visual_record={'version':'relative_visual_signal_v1','subject':'YeaG','variant':variant,
        'reference':'wild-type levels','observations':[{'printed_label':label,'reference_printed_label':'1.0',
            'original_source_ref':image['id'],'original_artifact_ref':image['artifact_ref'],
            'image_region':box,'reference_image_region':reference_box}]}
    transcription=source(canonical(visual_record),'retained_visual_transcription',[image['id']])
    start=original.index(b'<p>We were able')
    end=original.index(b'</p>',start)+4
    witness={'source_ref':paper['id'],'representation':'original','start':start,'end':end,
             'quote':original[start:end].decode('utf-8')}
    refs=[paper['id'],image['id'],transcription['id']]
    args={'source_ref':paper['id'],'source_kind':'primary_jats','section_id':'sec2','paragraph_index':1,
        'subject':'YeaG','variant':variant,'reference_literal':'wild-type levels',
        'visual_source_refs':[transcription['id']] if visual else [],'signal_kind':'protein_band',
        'reference_role':'tagged_wt_complementation','arrangement':'replacement','interpretation_witnesses':[witness]}
    assignment={'version':'literature_assignment_v1','question_context_refs':[],'source_refs':refs,
                'requested_ratio_components':COMPONENTS}
    context=BindingContext('primary-ratio-run','ratio-child','literature',(('literature','case'),),
        store.validate_scope(),assignment,{},refs)
    return store,context,args,visual_record


def binding_for(store,context):
    host=SimpleNamespace(store=store,run_id=context.run_id,tools=ToolRegistry(store))
    binding=LiteratureEpisodes(WorkflowServices(host),rate_population=True)
    host.episode_bindings=EpisodeBindingRegistry((binding,))
    return binding


@pytest.mark.parametrize('variant,expected', [('K116A',[.64]),('R232A',[.48]),('K426A',[1.,1.12]),('Y382stop',[.96])])
def test_primary_source_ratios_keep_actual_reference_conflicts_and_unknown_calibration(tmp_path,variant,expected):
    store,context,args,_=setup_store(tmp_path,variant)
    try:
        binding=binding_for(store,context)
        result=asyncio.run(binding.execute(context,'literature.ratio.populate',args,'selected'))
        assert result['status']=='completed',result
        ref=result['result']['sheet_ref']
        current=replace(context,received_record_refs=(*context.received_record_refs,*result['record_refs']))
        form=form_with_facts({},FORM,binding.facts(current,{'committed_record_refs':[ref]}))
        binding.validate_report(current,form,FORM)
        rows=form['measurements']
        assert rows[0]['value_candidates']==expected
        assert rows[0]['value']==(None if len(expected)>1 else expected[0])
        assert rows[0]['status']==('conflicting' if len(expected)>1 else 'populated')
        assert rows[0]['candidate_basis']=='received_source_representations'
        assert rows[0]['reference_role']=='tagged_wt_complementation'
        assert rows[0]['arrangement']=='replacement'
        assert rows[0]['uncertainty_kind']=='unreported'
        assert rows[0]['independent_preparation_count'] is None
        assert rows[0]['source_origins']==['reported','visual_transcription']
        assert store.get(rows[0]['comparison_reference_ref'])['label']=='wild-type levels'
        assert rows[2]['value'] is None and rows[2]['unavailable_reason']=='amount_calibration_unreported'
        assert rows[3]['value'] is None
        wrong=deepcopy(form)
        wrong['measurements'][0]['value_candidates']=[9]
        with pytest.raises(ReportBoundaryError,match='differs_from_saved'):
            binding.validate_report(current,wrong,FORM)
        parent=replace(current,role='annotation',episode_id='parent',path=(('annotation','root'),),assignment={})
        binding.received_form_references(parent,form,FORM,'admitted')
        assert binding.received_report_facts(parent)['literature_ratio_cells']==rows
    finally:
        store.close()


def test_reopen_restores_original_candidates_and_checks_actual_source_receipts(tmp_path,monkeypatch):
    store,context,args,_=setup_store(tmp_path)
    repo=LiteratureRatioRepository(store,context.run_id)
    outcome=repo.populate(context,args,'selected')
    saved=repo.read(outcome['result']['sheet_ref'])
    store.close()
    def forbidden(*args,**kwargs):raise AssertionError('must not reparse/recalculate')
    monkeypatch.setattr('gene_annotation_episode.literature_ratio_storage.read_jats_relative_percent',forbidden)
    monkeypatch.setattr('gene_annotation_episode.literature_ratio_storage.populate_relative_signal',forbidden)
    with Store(tmp_path) as reopened:
        restored=LiteratureRatioRepository(reopened,context.run_id)
        assert restored.populate(context,args,'selected')==outcome
        assert restored.read(outcome['result']['sheet_ref'])==saved
        with pytest.raises(ContractError,match='not_received'):
            restored.populate(replace(context,received_record_refs=(args['source_ref'],)),args,'selected')


def test_selected_primary_ratio_child_returns_conflict_once_without_new_science_credit(tmp_path):
    store,context,args,_=setup_store(tmp_path/'state')
    controllers,received=[],[]
    try:
        child={'selection':{'kind':'episode_child','role':'literature','assignment':plain(context.assignment),
            'goal':'Evaluate the actual source relative-protein-signal comparison and preserve conflicting representations',
            'scope':plain(context.scope),'purpose':'Return relative signal components with exact denominator and unknown calibration',
            'schema_json':json.dumps(FORM),'initial_report_json':'{}'},'report_update':{}}
        work={'selection':{'kind':'tool','tool':'literature.ratio.populate','arguments':args},'report_update':{}}
        def receive(inputs):
            form,=inputs['child_reports']
            received.append(form)
            assert form['measurements'][0]['value_candidates']==[1,1.12]
            assert form['measurements'][0]['value'] is None
            source=store.get(args['source_ref'])
            raw=store.get_artifact(source['artifact_ref'])
            start=raw.index(b'YeaG')
            commit={key:[] for key in store.reasoning_schema()['required']}
            commit['source_subjects']=[{'alias':'reported_source','reference_type':'assay',
                'source_ref':source['id'],'label':'YeaG','anchor':{'source_ref':source['id'],
                    'artifact_ref':source['artifact_ref'],'start':start,'end':start+4,'quote':'YeaG'}}]
            return {'selection':{'kind':'reason','commit':commit},'report_update':{}}
        def controller(path,initial):
            result=FixtureController(str(path),initial,2 if len(path)==1 else 1)
            controllers.append(result)
            return result
        scorer=ScientificFindingProgress(FindingProgressPolicy(1))
        summary=asyncio.run(run_workflow(store,ToolRegistry(store),provider=ScriptedProvider([child,work,receive]),
            run_dir=tmp_path/'run',controller_factory=controller,project_credit=scorer,
            initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True),),
            binding_definitions={'credit':scorer.as_record()}))
        assert summary['credit']==0
        assert len(received)==1
        assert [row.scores for row in controllers]==[[0,0],[0]]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==3
        assert store.db.execute('SELECT count(*) FROM literature_ratio_operations').fetchone()[0]==1
    finally:
        store.close()


def test_visual_annotation_must_bind_the_actual_received_image_and_valid_region(tmp_path):
    store,context,args,visual=setup_store(tmp_path)
    try:
        source=store.get(args['visual_source_refs'][0])
        bad=deepcopy(visual)
        bad['observations'][0]['image_region']=[1,1,100000,100000]
        artifact=store.artifact(canonical(bad),'application/json')
        fields={key:source[key] for key in ('provider','accession','uri','text_ref','request_ref','version','retrieved_at','parent_source_refs')}
        fields['artifact_ref']=artifact
        wrong=store.put('source',fields,origin='caller')
        allowed=replace(context,received_record_refs=(*context.received_record_refs,wrong['id']))
        result=asyncio.run(binding_for(store,context).execute(allowed,'literature.ratio.populate',
            {**args,'visual_source_refs':[wrong['id']]},'wrong-box'))
        assert result['status']=='invalid'
        assert result['feedback']['code']=='retained_visual_region_outside_image'
        assert store.db.execute('SELECT count(*) FROM literature_ratio_operations').fetchone()[0]==0
        denied=asyncio.run(binding_for(store,context).execute(
            replace(context,received_record_refs=(args['source_ref'],)),
            'literature.ratio.populate',args,'foreign-image'))
        assert denied['status']=='invalid'
        assert denied['feedback']['code']=='literature_source_not_received'
    finally:store.close()
