"""Selected endpoint integration with controlled choices, not model-backed science."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import form_with_facts, plain, validate_closed_schema, ReportBoundaryError
from gene_annotation_episode.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_figure_storage import figure_operation_schema
from gene_annotation_episode.literature_endpoint_signal_storage import (
    LiteratureEndpointSignalRepository, ENDPOINT_SIGNAL_CELLS_SCHEMA_V1, endpoint_signal_cells_schema,
    NAMESPACE, REQUESTED, VIEW, COMPONENTS)
from gene_annotation_episode.literature_endpoint_signal_prompt import ENDPOINT_SIGNAL_TASK
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_figure_prompt import FIGURE_TASK
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_endpoint_signal_components_241 import _paper

ROOT=Path(__file__).resolve().parents[1]
OWN=ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_endpoint_signal_binding_244'
SELECTED=['retained_fraction','retained_fraction_variance']


def setup(path, components=SELECTED):
    args, blobs = _paper()
    store=Store(path); manifest=path/'empty-manifest.json'
    manifest.write_text(json.dumps({'schema_version':1,'entries':[]}));store.create_problem(manifest_path=manifest)
    def source(raw, provider, *, text=None, parents=(), artifact=None):
        artifact=artifact or store.artifact(raw)
        return store.put('source',{'provider':provider,'accession':None,'uri':None,
            'artifact_ref':artifact,'text_ref':store.artifact(text) if text is not None else artifact,
            'request_ref':None,'version':None,'retrieved_at':None,'parent_source_refs':list(parents)},origin='caller')['id']
    article=source(blobs['source_kaster_primary','original'],'controlled_retained_original244',text=blobs['source_kaster_primary','text'])
    image=source(blobs['source_kaster_original_figure4','original'],'controlled_original_image244',parents=[article])
    def refs(value):
        if isinstance(value,dict):return {k:refs(v) for k,v in value.items()}
        if isinstance(value,list):return [refs(v) for v in value]
        return article if value=='source_kaster_primary' else image if value=='source_kaster_original_figure4' else value
    args=refs(args);args['requested_cells']=list(components)
    context=json.loads((OWN/'PAIRED_SELECTED_INPUT_002.json').read_text())['arguments']['return_context']
    request={'version':'literature_figure_endpoint_signal_population_v1','selection':args,'return_context':context}
    assignment={'version':'literature_assignment_v1','source_refs':[article,image],'question_context_refs':[],REQUESTED:list(components)}
    ctx=BindingContext('endpoint244','child244','literature',(('literature','child244'),),store.validate_scope(),assignment,{},(article,image))
    host=SimpleNamespace(store=store,run_id=ctx.run_id,tools=ToolRegistry(store))
    binding=LiteratureEpisodes(WorkflowServices(host),rate_population=True,reference_parent_sources=[article,image])
    host.episode_bindings=EpisodeBindingRegistry((binding,))
    return store,ctx,request,binding,source


def selected(store,ctx,args,binding):
    outcome=asyncio.run(binding.execute(ctx,'literature.figure.populate',args,'selected244'))
    assert outcome['status']=='completed',outcome
    current=replace(ctx,received_record_refs=(*ctx.received_record_refs,*outcome['record_refs']))
    schema=obj({'numbers':endpoint_signal_cells_schema()})
    rows=form_with_facts({},schema,binding.facts(current,{'committed_record_refs':outcome['record_refs']}))['numbers']
    binding.validate_report(current,{'numbers':rows},schema)
    return current,outcome,rows


def forbid(*a,**kw):raise AssertionError('Source/scientific/model/factory/receive/attestation work forbidden')


def test_exact_schema_discovery_selected_sheet_and_requested_rows(tmp_path):
    store,ctx,args,binding,_=setup(tmp_path/'state')
    try:
        before=store.db.total_changes
        assert figure_operation_schema()==json.loads((OWN/'EXACT_SCHEMAS_002.json').read_text())['operation_schema']
        assert endpoint_signal_cells_schema()==json.loads((OWN/'EXACT_SCHEMAS_002.json').read_text())['return_schema']
        assert REQUESTED in binding.assignment_schema('literature')['properties']
        assert NAMESPACE in binding.fact_sources('literature')
        assert 'literature.figure.populate' in {r['name'] for r in binding.catalog(ctx)}
        binding._endpoint_signal_repository().has_work(ctx)
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_endpoint_signal_operations'").fetchone()
        assert store.db.total_changes==before
        current,out,rows=selected(store,ctx,args,binding)
        assert [r['component'] for r in rows]==SELECTED
        assert rows[0]['value'] is None and rows[0]['conditional_value']==131/142
        assert rows[0]['exact_lower']=={'numerator':'128','denominator':'143'}
        assert rows[0]['relationships']['arrangement']['value']=='coexistence'
        assert rows[0]['sampling_window']=='finite_selected_late_point_no_physical_time_extracted'
        assert rows[1]['value'] is rows[1]['conditional_value'] is None
        assert rows[1]['unavailable_reasons']==['covariance_unreported']
        repo=binding._endpoint_signal_repository();saved=repo.read(out['result']['sheet_ref'])
        assert saved['extraction']['arguments']==args['selection']
        assert saved['sheet']['input_snapshot']==saved['extraction']
        assert saved['sheet']['requested_cells']==SELECTED
        assert saved['row_templates']==[{k:v for k,v in row.items() if k!='sheet_ref'} for row in rows]
        assert asyncio.run(binding.execute(ctx,'literature.figure.populate',args,'selected244'))==out
    finally:store.close()


@pytest.mark.parametrize('field',['unit','formula','meaning'])
def test_component_discriminator_and_exact_registered_form(tmp_path,field):
    store,ctx,args,binding,_=setup(tmp_path/'state')
    try:
        _,_,rows=selected(store,ctx,args,binding)
        bad=deepcopy(rows);bad[0][field]={'unit':'pixel^2','formula':'s*(a-t)','meaning':'Selected total reporter amplitude in direction-oriented native pixels.'}[field]
        with pytest.raises(ContractError):validate_schema(bad,ENDPOINT_SIGNAL_CELLS_SCHEMA_V1)
        altered=endpoint_signal_cells_schema();del altered['items']['allOf']
        with pytest.raises(ReportBoundaryError):validate_closed_schema(obj({'numbers':altered}))
    finally:store.close()


@pytest.mark.parametrize('components',[[],['additional_fraction','total_amplitude','retained_fraction']])
def test_order_and_empty_rosters(tmp_path,components):
    store,ctx,args,binding,_=setup(tmp_path/'state',components)
    try:
        _,out,rows=selected(store,ctx,args,binding)
        assert [r['component'] for r in rows]==components
        assert binding._endpoint_signal_repository().read(out['result']['sheet_ref'])['sheet']['requested_cells']==components
    finally:store.close()


@pytest.mark.parametrize('part',['primary','image','context','covariance','order'])
def test_source_custody_and_request_preflight(tmp_path,part):
    store,ctx,args,binding,source=setup(tmp_path/'state')
    try:
        alien=source(b'controlled unreceived source','controlled_unreceived244')
        if part=='primary':args['selection']['source_ref']=alien
        elif part=='image':args['selection']['image']['source_ref']=alien
        elif part=='context':args['selection']['context']['subject']['source_ref']=alien
        elif part=='covariance':args['selection']['covariance_source_ref']=alien
        else:args['selection']['requested_cells'].reverse()
        out=asyncio.run(binding.execute(ctx,'literature.figure.populate',args,'bad244'))
        assert out['status']=='invalid'
        assert out['feedback']['code']==('endpoint_assignment_request_roster_mismatch' if part=='order' else 'literature_source_not_received')
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_endpoint_signal_operations'").fetchone()
    finally:store.close()


def test_wrong_source_record_kind_returns_normal_repair_feedback(tmp_path):
    store,ctx,args,binding,_=setup(tmp_path/'state')
    try:
        artifact=store.get(args['selection']['source_ref'])['artifact_ref']
        for tool,arguments in [('source.read',{'source_ref':artifact,'representation':'original'}),
            ('source.locate',{'source_ref':artifact,'representation':'original','needle':'controlled'})]:
            result=asyncio.run(binding.execute(ctx,tool,arguments,'wrong_kind244'+tool))
            assert result['status']=='invalid' and result['feedback']
        args['selection']['source_ref']=artifact
        result=asyncio.run(binding.execute(replace(ctx,received_record_refs=(*ctx.received_record_refs,artifact)),
            'literature.figure.populate',args,'wrong_population_kind244'))
        assert result['status']=='invalid' and result['feedback']
    finally:store.close()


@pytest.mark.parametrize('meaning',['supported','unknown','conflicting','unsupported','explicit_conditional_scenario'])
def test_conditional_and_partial_meanings(tmp_path,meaning):
    store,ctx,args,binding,_=setup(tmp_path/'state')
    try:
        r=args['selection']['relationships']['baseline_applicability'];r['value']=meaning
        if meaning!='explicit_conditional_scenario':args['selection']['source_kind']='synthetic_fixture'
        if meaning=='supported':args['selection']['relationships']['fast_component_completion']['value']='supported'
        if meaning=='conflicting':r['image_regions'].append([60,30,204,185])
        _,_,rows=selected(store,ctx,args,binding)
        assert rows[0]['status']==('populated' if meaning=='supported' else 'conditional_scenario' if meaning=='explicit_conditional_scenario' else 'unavailable')
    finally:store.close()


def test_narrow_admission_private_receipt_access_and_public_originals(tmp_path):
    store,ctx,args,binding,source=setup(tmp_path/'state')
    try:
        current,out,rows=selected(store,ctx,args,binding);ref=out['result']['sheet_ref'];repo=binding._endpoint_signal_repository()
        parent=replace(current,episode_id='receiver244',path=(('literature','receiver244'),),assignment={**plain(ctx.assignment),REQUESTED:SELECTED[:1]})
        schema=obj({'numbers':endpoint_signal_cells_schema()})
        binding.received_form_references(parent,{'numbers':rows[:1]},schema,'controlled244')
        assert repo.fact_cells(parent,[ref],components=list(reversed(SELECTED)))==rows[:1]
        metadata=store.get(ref)
        aliases=[source(b'','controlled_receipt_alias244',artifact=metadata[k]) for k in ('artifact_ref','request_ref')]
        for target in [ref,*aliases]:
            receiver=replace(parent,received_record_refs=(*parent.received_record_refs,target))
            for tool,arguments in [('source.read',{'source_ref':target,'representation':'original','offset':0,'limit':512}),
                ('source.locate',{'source_ref':target,'representation':'original','needle':'initial','context_bytes':512})]:
                denied=asyncio.run(binding.execute(receiver,tool,arguments,'denied'+tool+target))
                assert denied['status']=='invalid' and denied['feedback']['code']=='literature_endpoint_receipt_private'
        owned=asyncio.run(binding.execute(current,'source.read',{'source_ref':ref,'limit':128,'representation':'original'},'owner244'))
        assert owned['status']=='completed' and owned['result']['text']
        located=asyncio.run(binding.execute(current,'source.locate',{'source_ref':ref,'representation':'original','needle':'row_templates','context_bytes':8},'owner_locate244'))
        assert located['status']=='completed' and located['result']['matches']
        public=asyncio.run(binding.execute(parent,'source.read',{'source_ref':args['selection']['source_ref'],'limit':32,'representation':'original'},'public244'))
        assert public['status']=='completed'
        raw=store.get_artifact(metadata['artifact_ref']);needle=b'"row_templates"';start=raw.index(needle)
        commit={key:[] for key in store.reasoning_schema()['required']}
        commit['source_subjects']=[{'alias':'private_receipt244','reference_type':'assay','source_ref':ref,'label':needle.decode(),
            'anchor':{'source_ref':ref,'artifact_ref':metadata['artifact_ref'],'start':start,'end':start+len(needle),'quote':needle.decode()}}]
        committed=store.commit_reasoning(commit,scope=plain(ctx.scope),operation_key='anchor244')
        alias=next(r for r in committed['record_refs'] if r.startswith('reference_'))
        denied=asyncio.run(binding.execute(parent,'state.query',{'refs':[alias]},'alias244'))
        assert denied['status']=='invalid' and denied['feedback']['code']=='literature_endpoint_receipt_private'
        denied=asyncio.run(binding.execute(parent,'state.query',{'kind':'reference','offset':0,'limit':100},'paged_alias244'))
        assert denied['status']=='invalid' and denied['feedback']['code']=='literature_endpoint_receipt_private'
        metadata_only=asyncio.run(binding.execute(parent,'state.query',{'refs':[ref]},'metadata244'))
        assert metadata_only['status']=='completed'
        public_alias=source(b'Controlled public source with numbers 617 and 647.','controlled_public_alias244')
        allowed=asyncio.run(binding.execute(parent,'source.read',{'source_ref':public_alias,'representation':'original'},'public_alias244'))
        assert allowed['status']=='completed'
    finally:store.close()


def test_full_task_and_no_unrequested_operand_hydration(tmp_path):
    store,ctx,args,binding,_=setup(tmp_path/'state')
    try:
        current,out,rows=selected(store,ctx,args,binding)
        state={'literature_experimental_work':{'version':'literature_experimental_task_v1','aspect':'source_experimental_evidence'},
            'literature_assignment':plain(ctx.assignment),'last_local_outcome':out,'child_reports':[{'numbers':rows[:1]}],
            'working_state':{},**binding._endpoint_signal_display_context(current)}
        prompt=render_literature_experimental_prompt(state,'Examine the requested finite endpoint correction.')
        task,steering=prompt.split('\n\nSTEERING\n')
        assert ENDPOINT_SIGNAL_TASK in task and FIGURE_TASK not in task
        assert '0.9225352112676056' in steering
        assert '∼0.6' not in steering and '"x"' not in steering and 'exact_covariance' not in steering
        assert 'retained_fraction_variance' not in steering
        for paragraph in ENDPOINT_SIGNAL_TASK.split('\n\n'):assert paragraph in task
    finally:store.close()


def test_failed_endpoint_history_keeps_task_and_withholds_original_input_dump(tmp_path):
    store,ctx,args,_,_=setup(tmp_path/'state')
    try:
        state={'literature_experimental_work':{'version':'literature_experimental_task_v1','aspect':'source_experimental_evidence'},
            'literature_assignment':plain(ctx.assignment),'working_state':{}}
        history={'status':'completed','result':{'view':'records','records':[{
            'selection':{'kind':'tool','tool':'literature.figure.populate','arguments':args},
            'outcome':{'status':'invalid','result':None,'feedback':{'code':'controlled_missing_source'}}}]}}
        prompt=render_literature_experimental_prompt(state,'Repair the selected source dependency.',lookup_results=[history])
        task,steering=prompt.split('\n\nSTEERING\n')
        assert ENDPOINT_SIGNAL_TASK in task
        assert 'controlled_missing_source' in steering
        assert '∼0.6' not in steering and 'support_region' not in steering and 'point_rgb' not in steering
    finally:store.close()


def test_union_contract_lookup_keeps_both_distinct_actual_tasks(tmp_path):
    from gene_annotation_episode.episode_contract_information import operation_contract_information
    store,ctx,_,binding,_=setup(tmp_path/'state')
    try:
        state={'literature_experimental_work':{'version':'literature_experimental_task_v1','aspect':'source_experimental_evidence'},
            'literature_assignment':plain(ctx.assignment),'working_state':{},'contract_information_profile':'operation_contract_information_v1'}
        lookup=operation_contract_information(catalog=binding.catalog(ctx),operation='literature.figure.populate')
        task=render_literature_experimental_prompt(state,'Choose the appropriate figure interpretation.',lookup_results=[lookup]).split('\n\nSTEERING\n')[0]
        assert ENDPOINT_SIGNAL_TASK in task and FIGURE_TASK in task
    finally:store.close()


def test_explicit_synthetic_zero_total_does_not_become_nondetection_or_fraction(tmp_path):
    from io import BytesIO
    from PIL import Image
    store,ctx,args,binding,source=setup(tmp_path/'state',['total_amplitude','retained_fraction'])
    try:
        primary=source(b'Explicit synthetic endpoint fixture, not a scientific observation.','controlled_synthetic_endpoint244')
        im=Image.new('RGB',(32,32),'black');stream=BytesIO();im.save(stream,format='PNG');im.close();raw=stream.getvalue()
        image=source(raw,'controlled_synthetic_endpoint_image244',parents=[primary])
        selection=args['selection'];selection['source_ref']=primary;selection['source_kind']='synthetic_fixture'
        selection['image'].update(source_ref=image,expected_sha256=hashlib.sha256(raw).hexdigest(),width=32,height=32,
            panel_region=[0,0,32,32],image_origin='synthetic')
        for role,x,y in [('initial',1,10),('baseline_at_addition',2,4),('late',3,10)]:
            p=selection['image']['points'][role];region=[x,y,x+1,y+1]
            p.update(x=x,y=y,y_enclosure=[y,y],support_region=region,semantic_witnesses=[],physical_estimate_owner=None)
            p['image_witness']['region']=region
        for value in selection['relationships'].values():value.update(witnesses=[],image_regions=[[0,0,32,32]])
        selection['relationships']['ordinate_direction']['value']='increases_downward'
        selection['context']={name:None for name in selection['context']}
        args['return_context']={name:[] for name in args['return_context']}
        assignment={**plain(ctx.assignment),'source_refs':[primary,image]}
        ctx=replace(ctx,assignment=assignment,received_record_refs=(*ctx.received_record_refs,primary,image))
        _,_,rows=selected(store,ctx,args,binding)
        assert rows[0]['value']==0 and rows[0]['status']=='populated'
        assert rows[1]['value'] is rows[1]['conditional_value'] is None
        assert 'zero_total_amplitude' in rows[1]['unavailable_reasons']
        assert rows[0]['source_kind']=='synthetic_fixture'
    finally:store.close()


def block_science(monkeypatch):
    from gene_annotation_episode import literature_endpoint_signal_inputs as inputs
    from gene_annotation_episode import literature_endpoint_signal_calculations as calculations
    from gene_annotation_episode import literature_endpoint_signal_storage as storage
    from gene_annotation_episode import literature_numerical_contracts as contracts
    for module,names in [(inputs,['read_endpoint_signal_inputs','validate_endpoint_signal_extraction','_image','_point','_covariance','endpoint_signal_population_schema','endpoint_signal_extraction_schema']),
        (calculations,['populate_endpoint_signal','endpoint_signal_sheet_schema']),
        (storage,['endpoint_signal_cells_schema','_project_once','_context_projection']),
        (contracts,['registered_schema']),
        (LiteratureEndpointSignalRepository,['populate','receive_cells','_original_implementation'])]:
        for name in names:monkeypatch.setattr(module,name,forbid)


def test_all_sources_keep_assigned_page_ancestry(tmp_path):
    store,ctx,args,binding,source=setup(tmp_path/'state')
    try:
        primary=args['selection']['source_ref']
        page={'version':'page_assignment_v1','source_ref':primary,'representation':'original',
            'artifact_ref':store.get(primary)['artifact_ref'],'question_context_refs':[],'prior_delivery_refs':[],REQUESTED:SELECTED}
        pagectx=replace(ctx,role='literature_page',path=(('literature_page',ctx.episode_id),),assignment=page)
        alien=source(store.get_artifact(store.get(args['selection']['image']['source_ref'])['artifact_ref']),'controlled_unrelated_image244')
        args['selection']['image']['source_ref']=alien
        pagectx=replace(pagectx,received_record_refs=(*pagectx.received_record_refs,alien))
        out=asyncio.run(binding.execute(pagectx,'literature.figure.populate',args,'page244'))
        assert out['status']=='invalid' and out['feedback']['code']=='literature_reading_outside_assigned_source'
    finally:store.close()


def test_context_role_alias_cannot_forward_corrected_ratio(tmp_path):
    store,ctx,args,binding,_=setup(tmp_path/'state')
    try:
        corrected=deepcopy(args['selection']['context']['correction_discussion'])
        args['selection']['context']['condition']=corrected
        args['return_context']['condition']=[{'start':corrected['start'],'end':corrected['end']}]
        out=asyncio.run(binding.execute(ctx,'literature.figure.populate',args,'context_alias244'))
        assert out['status']=='invalid' and out['feedback']['code']=='endpoint_context_overlaps_private_correction_result'
    finally:store.close()


@pytest.mark.parametrize('representation',['original','text'])
def test_context_artifact_alias_cannot_forward_corrected_ratio(tmp_path,representation):
    store,ctx,args,binding,source=setup(tmp_path/'state')
    try:
        primary=args['selection']['source_ref'];artifact=store.get(primary)['text_ref']
        alias=source(b'','controlled_public_text_artifact_alias244',artifact=artifact)
        corrected=deepcopy(args['selection']['context']['correction_discussion'])
        corrected.update(source_ref=alias,representation=representation)
        args['selection']['context']['condition']=corrected
        args['return_context']['condition']=[{'start':corrected['start'],'end':corrected['end']}]
        ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,alias))
        out=asyncio.run(binding.execute(ctx,'literature.figure.populate',args,'artifact_context_alias244'))
        assert out['status']=='invalid' and out['feedback']['code']=='endpoint_context_overlaps_private_correction_result'
        public=asyncio.run(binding.execute(ctx,'source.read',{'source_ref':alias,'representation':representation,
            'offset':corrected['start'],'limit':corrected['end']-corrected['start']},'explicit_public_alias244'))
        assert public['status']=='completed' and '0.6' in public['result']['text']
    finally:store.close()


@pytest.mark.parametrize('representation',['original','text'])
def test_covariance_artifact_alias_cannot_be_normal_return_context(tmp_path,representation):
    from gene_annotation_episode.domain import identity
    store,ctx,args,binding,source=setup(tmp_path/'state')
    try:
        image=args['selection']['image'];artifact=store.get(image['source_ref'])['artifact_ref']
        owners=[identity('endpoint_coordinate',{'source_ref':image['source_ref'],'artifact_ref':artifact,
            'x':image['points'][role]['x'],'y':image['points'][role]['y']}) for role in ('initial','baseline_at_addition','late')]
        covariance={'version':'a105_endpoint_signal_covariance_v1','basis':'joint_manual_reading_error',
            'primitive_order':['initial','baseline_at_addition','late'],'primitive_owners':owners,
            'primitive_units':['native_ordinate_pixel']*3,'covariance':[[4,1,0],[1,9,-1],[0,-1,16]],
            'variance_status':'known','origin':'synthetic','provenance_witnesses':[],
            'native_coordinate_basis_witnesses':[],'coordinate_units_status':'already_in_declared_native_coordinate_units'}
        raw=json.dumps(covariance).encode();cov=source(raw,'controlled_covariance_source244')
        alias=source(b'','controlled_covariance_alias244',artifact=store.get(cov)['artifact_ref'])
        token=b'joint_manual_reading_error';start=raw.index(token)
        args['selection']['covariance_source_ref']=cov
        args['selection']['context']['condition']={'source_ref':alias,'representation':representation,
            'start':start,'end':start+len(token),'quote':token.decode()}
        args['return_context']['condition']=[{'start':start,'end':start+len(token)}]
        ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,cov,alias))
        out=asyncio.run(binding.execute(ctx,'literature.figure.populate',args,'covariance_context_alias244'))
        assert out['status']=='invalid' and out['feedback']['code']=='endpoint_context_from_covariance_packet'
    finally:store.close()


@pytest.mark.parametrize('mode',['missing_baseline','already_applied','image_unavailable'])
def test_authorized_partials_preserve_meanings_and_total(tmp_path,mode):
    selected_names=['total_amplitude','retained_fraction']
    store,ctx,args,binding,_=setup(tmp_path/'state',selected_names)
    try:
        if mode=='missing_baseline':args['selection']['image']['points']['baseline_at_addition']=None
        elif mode=='already_applied':
            args['selection']['relationships']['correction_stage']['value']='already_applied'
            args['selection']['source_kind']='synthetic_fixture'
        else:args['selection']['image']['expected_sha256']='0'*64
        _,_,rows=selected(store,ctx,args,binding)
        assert rows[0]['value']==(None if mode=='image_unavailable' else 142)
        assert rows[1]['status']=='unavailable'
        assert rows[1]['source_context']['subject']['status']=='selected'
        if mode=='already_applied':assert 'correction_already_applied' in rows[1]['unavailable_reasons']
    finally:store.close()


@pytest.mark.parametrize('status',['known','unknown'])
def test_synthetic_reading_covariance_is_not_physical_uncertainty_or_matrix_return(tmp_path,status):
    from gene_annotation_episode.domain import identity
    store,ctx,args,binding,source=setup(tmp_path/'state')
    try:
        image=args['selection']['image'];artifact=store.get(image['source_ref'])['artifact_ref']
        owners=[identity('endpoint_coordinate',{'source_ref':image['source_ref'],'artifact_ref':artifact,
            'x':image['points'][role]['x'],'y':image['points'][role]['y']}) for role in ('initial','baseline_at_addition','late')]
        covariance={'version':'a105_endpoint_signal_covariance_v1','basis':'joint_manual_reading_error',
            'primitive_order':['initial','baseline_at_addition','late'],'primitive_owners':owners,
            'primitive_units':['native_ordinate_pixel']*3,'covariance':[[4,1,0],[1,9,-1],[0,-1,16]],
            'variance_status':status,'origin':'synthetic','provenance_witnesses':[],
            'native_coordinate_basis_witnesses':[],'coordinate_units_status':'already_in_declared_native_coordinate_units'}
        ref=source(json.dumps(covariance).encode(),'controlled_synthetic_covariance244',parents=[args['selection']['source_ref']])
        args['selection']['covariance_source_ref']=ref;ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,ref))
        _,out,rows=selected(store,ctx,args,binding)
        assert rows[1]['uncertainty']['origin']=='synthetic'
        assert rows[1]['uncertainty']['physical_uncertainty']=='unreported'
        assert rows[1]['conditional_value'] is not None if status=='known' else rows[1]['conditional_value'] is None
        saved=binding._endpoint_signal_repository().read(out['result']['sheet_ref'])
        assert (saved['sheet']['joint_propagation'] is not None)==(status=='known')
        assert 'covariance' not in rows[1] and 'exact_covariance' not in rows[1]
    finally:store.close()


def test_external_covariance_support_cannot_hydrate_unrequested_numbers(tmp_path):
    from gene_annotation_episode.domain import identity
    store,ctx,args,binding,source=setup(tmp_path/'state')
    try:
        raw_support=b'Explicit CONTROLLED synthetic uncertainty support: 713, 719, 727.'
        support=source(raw_support,'controlled_external_covariance_support244')
        witness={'source_ref':support,'representation':'original','start':0,'end':len(raw_support),'quote':raw_support.decode()}
        image=args['selection']['image'];artifact=store.get(image['source_ref'])['artifact_ref']
        owners=[identity('endpoint_coordinate',{'source_ref':image['source_ref'],'artifact_ref':artifact,
            'x':image['points'][role]['x'],'y':image['points'][role]['y']}) for role in ('initial','baseline_at_addition','late')]
        covariance={'version':'a105_endpoint_signal_covariance_v1','basis':'joint_manual_reading_error',
            'primitive_order':['initial','baseline_at_addition','late'],'primitive_owners':owners,
            'primitive_units':['native_ordinate_pixel']*3,'covariance':[[4,1,0],[1,9,-1],[0,-1,16]],
            'variance_status':'known','origin':'synthetic','provenance_witnesses':[witness],
            'native_coordinate_basis_witnesses':[],'coordinate_units_status':'already_in_declared_native_coordinate_units'}
        cov=source(json.dumps(covariance).encode(),'controlled_covariance_wire244')
        args['selection']['covariance_source_ref']=cov
        ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,support,cov))
        current,_,rows=selected(store,ctx,args,binding)
        support_artifact=store.get(support)['artifact_ref']
        assert any(loc['artifact_ref']==support_artifact for loc in rows[0]['withheld_locations'])
        commit={key:[] for key in store.reasoning_schema()['required']}
        commit['source_subjects']=[{'alias':'covariance_support244','reference_type':'assay','source_ref':support,
            'label':witness['quote'],'anchor':{'source_ref':support,'artifact_ref':support_artifact,
                'start':0,'end':len(raw_support),'quote':witness['quote']}}]
        result=store.commit_reasoning(commit,scope=plain(ctx.scope),operation_key='covariance_support244')
        record=store.get(result['record_refs'][0])
        state={'literature_experimental_work':{'version':'literature_experimental_task_v1','aspect':'source_experimental_evidence'},
            'literature_assignment':plain(ctx.assignment),'working_state':{'references':[record]},
            'current_report_basis_refs':[record['id']],'child_reports':[{'numbers':rows}],
            **binding._endpoint_signal_display_context(current)}
        steering=render_literature_experimental_prompt(state,'Evaluate the requested uncertainty.').split('\n\nSTEERING\n')[1]
        assert '713' not in steering and '719' not in steering and '727' not in steering
    finally:store.close()


@pytest.mark.parametrize('field',['row','sheet','schema','source','receipt','receipt_type'])
def test_saved_tampering_rejects_without_repair(tmp_path,monkeypatch,field):
    store,ctx,args,binding,_=setup(tmp_path/'state')
    try:
        _,out,_=selected(store,ctx,args,binding);repo=binding._endpoint_signal_repository();ref=out['result']['sheet_ref']
        artifact=store.get(ref)['artifact_ref'];original=repo._json
        def changed(reference):
            value=original(reference)
            if reference==artifact:
                if field=='row':value['row_templates'][0]['conditional_value']=.125
                elif field=='sheet':value['sheet']['cells'][0]['conditional_value']=.125
                elif field=='schema':del value['original_schemas']['rows']['items']['allOf']
                elif field=='source':value['input_artifact_ref']='artifact_'+'0'*64
                elif field=='receipt':value['original_implementation']['files']={}
                else:value['original_implementation']['files']=None
            return value
        monkeypatch.setattr(repo,'_json',changed);block_science(monkeypatch)
        with pytest.raises(ContractError):repo.read(ref)
    finally:store.close()


@pytest.mark.parametrize('profile',[None,'operation_contract_information_v1'])
def test_original_pending_alias_first_readonly_composer_has_no_factory_or_cache_dependency(tmp_path,monkeypatch,profile):
    from gene_annotation_episode.episode_composition import compose_episode_bindings
    from gene_annotation_episode.investigation_progress import ScientificFindingProgress,FindingProgressPolicy
    from gene_annotation_episode.runtime import Workflow
    from gene_annotation_episode import literature_numerical_contracts as contracts
    from test_runtime import FixtureController
    from test_contract_information_runtime_059 import PresentedProvider
    from test_literature_compiled_assay_185 import readonly
    import gene_annotation_episode.communication as communication
    store,ctx,_,_,_=setup(tmp_path/'state');sources=list(ctx.received_record_refs)
    literal=obj({'numbers':endpoint_signal_cells_schema()})
    submitted=obj({'numbers':{'$ref':'episode-fact:'+NAMESPACE}})
    provider=PresentedProvider([OSError('Controlled pending244 interruption')])
    workflow=Workflow(store,ToolRegistry(store),provider,tmp_path/'run',ctx.run_id,
        lambda path,initial:FixtureController(str(path),initial,2),ScientificFindingProgress(FindingProgressPolicy(1)),
        initial_known_record_refs=sources,episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,
            reference_parent_sources=sources,contract_information_profile=profile),),decision_protocol='decision_exchange_v1')
    root=workflow.build('annotation','root','Evaluate the selected experimental endpoint evidence.',plain(ctx.scope))
    with pytest.raises(OSError,match='pending244'):asyncio.run(root.run_async(workflow.context))
    episode=root.source.episode_id
    # This interrupted request belongs only to the explicitly controlled fixture.
    raw=workflow.journal.row('runtime_model_calls',episode,0)['request']
    descriptors=[workflow.episode_bindings.for_role('literature').as_record()]
    store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');store.close()
    block_science(monkeypatch)
    for name in ('report_sources','catalog','action_schema'):monkeypatch.setattr(Workflow,name,forbid)
    communication._compiled_schema_content.cache_clear()
    with readonly(tmp_path/'state') as cold:
        monkeypatch.setattr(cold,'get_artifact',forbid)
        host=SimpleNamespace(store=cold,run_id=ctx.run_id,tools=None)
        restored=compose_episode_bindings(WorkflowServices(host),store=cold,journal=SimpleNamespace(store=cold,run_id=ctx.run_id),
            execution_backend=None,descriptors=descriptors,job_episodes=None,resource_estimator=None,role_credit_bindings={})
        actual=cold.db.execute('SELECT request FROM runtime_model_calls WHERE episode_id=? AND call_index=0',(episode,)).fetchone()[0]
        assert actual==raw
        if profile is None:
            expanded=contracts.expand_numerical_form(json.dumps(submitted),child_role='literature',saved=json.loads(actual))
        else:
            from gene_annotation_episode.episode_contract_information import expand_fact_form
            record=Workflow.validate_contract_information(None,json.loads(actual))
            typed={role:{name:row for name,row in rows.items() if 'report_schema' in row}
                for role,rows in record['fact_sources_by_role'].items()}
            expanded=expand_fact_form(json.dumps(submitted),child_role='literature',facts_by_role=typed,
                permitted_child_roles=record['permitted_child_roles'])
        assert expanded['expanded_schema']==literal
        assert communication._compiled_schema_content.cache_info().currsize>0
        assert cold.db.total_changes==0
        assert not cold.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_endpoint_signal_operations'").fetchone()


def test_authentic_old_bar_v1_closed_data_is_unchanged(monkeypatch):
    from test_literature_compiled_assay_185 import readonly
    from gene_annotation_episode.literature_figure_storage import LiteratureFigureRepository
    import gene_annotation_episode.literature_figure_storage as legacy
    path=ROOT/'verification/literature_reference_evidence_2026-10-25_001/figure_examples_001/cropped_first/state'
    before={str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}
    with readonly(path) as cold:
        # These are the old explicitly scripted fixture's admitted typed form,
        # contract and source rows, not provider conversations or requests.
        row=cold.db.execute('SELECT run_id,parent_episode_id,form FROM runtime_report_attempts WHERE form IS NOT NULL AND failure IS NULL').fetchone()
        original=json.loads(row['form'])['measurements'];ref=original[0]['sheet_ref']
        metadata=cold.get(ref);allowed={metadata[k] for k in ('artifact_ref','request_ref')}
        get=cold.get_artifact
        def saved_only(reference):assert reference in allowed;return get(reference)
        monkeypatch.setattr(cold,'get_artifact',saved_only)
        monkeypatch.setattr(legacy,'read_figure_inputs',forbid)
        repo=LiteratureFigureRepository(cold,row['run_id'])
        saved=repo.read(ref)
        assert saved==json.loads(get(metadata['artifact_ref']))
        ctx=BindingContext(row['run_id'],row['parent_episode_id'],'annotation',(('annotation',row['parent_episode_id']),),
            cold.validate_scope(),{}, {},tuple([ref]))
        assert repo.received_cells(ctx)==original
        assert cold.db.total_changes==0
        assert cold.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==3
    after={str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}
    assert before==after


@pytest.mark.parametrize('profile,alias,nested',[(None,False,False),(None,True,False),('operation_contract_information_v1',True,False),(None,True,True)])
def test_selected_shared_loop_and_first_readonly_composer(tmp_path,monkeypatch,profile,alias,nested):
    from gene_annotation_episode.episode_composition import compose_episode_bindings
    from gene_annotation_episode.investigation_progress import ScientificFindingProgress,FindingProgressPolicy
    from gene_annotation_episode.runtime import run_workflow
    from test_runtime import FixtureController,ScriptedProvider
    from test_contract_information_runtime_059 import PresentedProvider
    from test_runtime_decision_exchanges import select as action
    from test_literature_compiled_assay_185 import readonly
    import gene_annotation_episode.communication as communication
    store,ctx,args,_,_=setup(tmp_path/'state');sources=list(ctx.received_record_refs)
    literal=obj({'numbers':endpoint_signal_cells_schema(),'limit':{'type':'string','enum':['attribution_unknown']}})
    submitted=obj({'numbers':{'$ref':'episode-fact:'+NAMESPACE},'limit':literal['properties']['limit']}) if alias else literal
    captured=[]
    def response(value):
        if not profile:return value
        value=deepcopy(value)
        if value['selection']['kind']=='tool':value['selection']['arguments']=json.dumps(value['selection']['arguments'])
        return action(value)
    def commission(role,assignment):return response({'selection':{'kind':'episode_child','role':role,'assignment':assignment,
        'goal':'Determine the requested conditional finite endpoint fraction and its available uncertainty.','scope':plain(ctx.scope),
        'purpose':'Return exactly requested endpoint scalars with necessary scientific limits.','schema_json':json.dumps(submitted),
        'initial_report_json':json.dumps({'limit':'attribution_unknown'})},'report_update':{}})
    def work(inputs):
        view=provider.views[provider.active_episode] if profile else inputs
        assert ENDPOINT_SIGNAL_TASK in render_literature_experimental_prompt(view,'Read the selected endpoint.').split('\n\nSTEERING\n')[0]
        return response({'selection':{'kind':'tool','tool':'literature.figure.populate','arguments':args},'report_update':{'limit':'attribution_unknown'}})
    def integrate(inputs):
        view=provider.views[provider.active_episode] if profile else inputs
        form,=view['child_reports'];captured.append(deepcopy(form))
        wanted=SELECTED[:1] if nested and len(captured)==2 else SELECTED
        assert [r['component'] for r in form['numbers']]==wanted
        assert ENDPOINT_SIGNAL_TASK in render_literature_experimental_prompt(view,'Evaluate returned endpoint evidence.').split('\n\nSTEERING\n')[0]
        commit={key:[] for key in store.reasoning_schema()['required']}
        witness=args['selection']['context']['subject']
        artifact=store.get(witness['source_ref'])['text_ref']
        commit['source_subjects']=[{'alias':'studied_reference244','reference_type':'assay',
            'source_ref':witness['source_ref'],'label':witness['quote'],
            'anchor':{'source_ref':witness['source_ref'],'artifact_ref':artifact,
                'start':witness['start'],'end':witness['end'],'quote':witness['quote']}}]
        return response({'selection':{'kind':'reason','commit':commit},'report_update':{'limit':'attribution_unknown'} if nested and len(captured)==1 else {}})
    outer=plain(ctx.assignment)
    if nested:outer[REQUESTED]=SELECTED[:1]
    script=[commission('literature',outer)]
    if nested:script.append(commission('literature_strategy',{'version':'strategy_assignment_v1','question_context_refs':[],'prior_search_refs':sources,REQUESTED:SELECTED}))
    script += [work,integrate,*([integrate] if nested else [])]
    class ControlledPresented(PresentedProvider):
        async def complete(self,episode_id,*a):self.active_episode=episode_id;return await super().complete(episode_id,*a)
    provider=ControlledPresented(script) if profile else ScriptedProvider(script)
    progress=ScientificFindingProgress(FindingProgressPolicy(1))
    try:
        asyncio.run(run_workflow(store,ToolRegistry(store),provider=provider,run_dir=tmp_path/'run',
            controller_factory=lambda path,initial:FixtureController(str(path),initial,2 if len(path)==1 or nested and len(path)==2 else 1),
            project_credit=progress,binding_definitions={'credit':progress.as_record()},initial_known_record_refs=sources,
            episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,reference_parent_sources=sources,contract_information_profile=profile),),
            **({'decision_protocol':'decision_exchange_v1'} if profile else {})))
        observations=5 if nested else 3
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==observations
        assert store.db.execute('SELECT count(*) FROM literature_endpoint_signal_operations').fetchone()[0]==1
        run_id,parent=store.db.execute('SELECT run_id,episode_id FROM literature_endpoint_signal_received ORDER BY rowid DESC LIMIT 1').fetchone()
        original=captured[-1];ref=original['numbers'][0]['sheet_ref'];repo=LiteratureEndpointSignalRepository(store,run_id);saved=repo.read(ref)
        descriptors=json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])['episode_bindings']
        allowed={store.get(ref)[key] for key in ('artifact_ref','request_ref')}
        receiver=replace(ctx,run_id=run_id,episode_id=parent,role='annotation',path=(('annotation',parent),),assignment={},
            received_record_refs=tuple(repo.cell_record_refs(original['numbers'])))
        for name,value in [('ORIGINAL_FORM_244.json',original),('ORIGINAL_SCHEMA_244.json',literal),('ORIGINAL_SHEET_244.json',saved),('ORIGINAL_DESCRIPTOR_244.json',descriptors)]:
            (tmp_path/name).write_text(json.dumps(value,indent=2)+'\n')
        store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');store.close()
        before={str(p.relative_to(tmp_path/'state')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (tmp_path/'state').rglob('*') if p.is_file()}
        block_science(monkeypatch);monkeypatch.setattr(type(provider),'complete',forbid)
        communication._compiled_schema_content.cache_clear()
        assert communication._compiled_schema_content.cache_info().currsize==0
        with readonly(tmp_path/'state') as cold:
            original_get=cold.get_artifact
            def saved_only(reference):assert reference in allowed,'Original scientific bytes forbidden';return original_get(reference)
            monkeypatch.setattr(cold,'get_artifact',saved_only)
            host=SimpleNamespace(store=cold,run_id=run_id,tools=None)
            restored=compose_episode_bindings(WorkflowServices(host),store=cold,journal=SimpleNamespace(store=cold,run_id=run_id),
                execution_backend=None,descriptors=descriptors,job_episodes=None,resource_estimator=None,role_credit_bindings={})
            host.episode_bindings=EpisodeBindingRegistry(restored.bindings);binding,=restored.bindings
            assert binding.received_report_facts(receiver)[NAMESPACE]==original['numbers']
            assert binding._endpoint_signal_repository().read(ref)==saved
            validate_closed_schema(literal)
            assert communication._compiled_schema_content.cache_info().currsize>0
            assert cold.db.total_changes==0
        after={str(p.relative_to(tmp_path/'state')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (tmp_path/'state').rglob('*') if p.is_file()}
        assert before==after
    finally:
        try:store.close()
        except Exception:pass
