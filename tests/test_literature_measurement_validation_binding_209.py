"""Controlled selected work, original-source facts and durable typed custody.

All model decisions here are explicitly scripted. No configured model science,
common A105 score or final-credit implementation is claimed.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, plain, validate_closed_schema, validate_form, form_with_facts
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
from gene_annotation_episode.literature_measurement_validation_storage import (
    LiteratureMeasurementValidationRepository, measurement_validation_cells_schema,
    COMPONENTS, NAMESPACE, REQUESTED, VIEW,
)
from gene_annotation_episode.literature_calibration_recovery_storage import LiteratureCalibrationRecoveryRepository
from gene_annotation_episode.literature_measurement_validation_prompt import MEASUREMENT_VALIDATION_TASK
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.episode_contract_information import return_contract_information
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_measurement_validation_205 import Source, original
from test_literature_calibration_recovery_binding_173 import rebind, OriginalRecoverySelection

REQUEST = ['reported_cv', 'relative_bias_squared', 'relative_squared_deviation_plugin',
    'relative_rms_percent', 'reported_zprime', 'control_band_ratio', 'raw_control_zprime']
FORM = obj({'numbers': measurement_validation_cells_schema()})


def setup(path, *, requested=REQUEST, primary=False, native_only=False):
    if primary:
        source, args, _pure_rows, _fields = original(1)
        recovery_args = OriginalRecoverySelection(source.reference, source.content).arguments('buffer')
    else:
        base = Source()
        text = base.text.replace('<article><p>', '<article><p>Buffer20mM at pH7.4, constructE2. ')
        source = Source(content=text.encode()); args = source.args()
        for field, text in [('analyte','NADPH'), ('matrix','Buffer20mM at pH7.4'),
                            ('method','optical WST8'), ('endpoint','WST8 endpoint'),
                            ('repetition','Repeated technical readings, count unknown')]:
            args['context'][field] = source.witness(text)
        recovery_args = {'source_ref':source.reference,'source_kind':'synthetic_fixture',
            **{name:None for name in ('experiment','analyte','matrix','endpoint','blank_treatment','expected_quantity_basis')},
            'control_kind':source.interpretation('reporter_standard','Prepared reporter standard'),
            'applicability':source.interpretation('unknown'),'spread_kind':source.interpretation('unknown'),
            'nominal':source.synthetic_number('nominal'),'measured':source.synthetic_number('measured'),
            'measured_spread':None,'shared_unit':source.witness('nmol'),'reported_recovery':None,
            'reported_recovery_unit':None}
    store=Store(path)
    manifest=store.path/'empty-inputs.json';manifest.write_text(json.dumps({'schema_version':1,'entries':[]}))
    store.create_problem(manifest_path=manifest)
    artifact=store.artifact(source.content,'application/xml')
    record=store.put('source',{'provider':'retained_PMC6454709' if primary else 'synthetic_precision_fixture',
        'accession':'PMC6454709' if primary else None,'uri':None,'artifact_ref':artifact,
        'text_ref':None,'request_ref':None,'version':None,'retrieved_at':None},origin='caller')
    args=rebind(args,source.reference,record['id']);recovery_args=rebind(recovery_args,source.reference,record['id'])
    assignment={'version':'literature_assignment_v1','question_context_refs':[],
        'source_refs':[record['id']],REQUESTED:list(requested)}
    ctx=BindingContext('validation209','child209','literature',(('literature','child209'),),
        store.validate_scope(),assignment,{},(record['id'],))
    if not native_only:
        recovery_context=replace(ctx,assignment={**assignment,'requested_calibration_recovery_components':['recovery','relative_bias']})
        prior=LiteratureCalibrationRecoveryRepository(store,ctx.run_id).populate(recovery_context,recovery_args,'prior_recovery')
        ref=prior['result']['sheet_ref'];ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,ref))
        for role in ('recovery','relative_bias'):
            args[role]={'namespace':'literature_calibration_recovery_cells','sheet_ref':ref,'component':role}
    return store,ctx,args


def binding_for(store,context,**configuration):
    host=SimpleNamespace(store=store,run_id=context.run_id,tools=ToolRegistry(store))
    binding=LiteratureEpisodes(WorkflowServices(host),rate_population=True,**configuration)
    host.episode_bindings=EpisodeBindingRegistry((binding,))
    return binding


def populated(store,ctx,args):
    repo=LiteratureMeasurementValidationRepository(store,ctx.run_id)
    out=repo.populate(ctx,args,'selected_validation')
    current=replace(ctx,received_record_refs=(*ctx.received_record_refs,*out['record_refs']))
    return repo,out,current


def test_original_source_two_precision_bases_and_conditional_error_are_distinct_rows(tmp_path):
    store,ctx,args=setup(tmp_path,primary=True)
    with store:
        repo,out,current=populated(store,ctx,args)
        rows=out['result']['cells']
        losses=[row for row in rows if row['component']=='relative_squared_deviation_plugin']
        assert [row['basis'] for row in losses]==['within_run','between_run']
        assert [row['conditional_value'] for row in losses]==pytest.approx([.00026049834505137914,.0004918212222823148])
        assert all(row['value'] is None and row['status']=='conditional' and row['origin']=='proposed' for row in losses)
        assert losses[0]['measurement_key']!=losses[1]['measurement_key']
        bias=[row for row in rows if row['component']=='relative_bias_squared']
        assert bias[0]['contribution_key']==bias[1]['contribution_key']
        assert bias[0]['input_measurement_keys']==bias[1]['input_measurement_keys']
        assert next(row for row in rows if row['component']=='reported_zprime')['value']==.99
        assert next(row for row in rows if row['component']=='raw_control_zprime')['interpretation']=='unimplemented'
        assert rows[0]['source_meanings']['analyte']['display_text']=='NADPH'
        assert repo.fact_cells(current,out['record_refs'],components=REQUEST)==rows
        assert repo.populate(ctx,args,'selected_validation')==out
        validate_form({'numbers':rows},FORM,lambda ref,namespace:bool(store.get(ref)))
        assert store.targets()==[] and not store.list('assessment') and not store.list('observation')


def test_selected_execution_default_empty_and_source_possession(tmp_path):
    store,ctx,args=setup(tmp_path,native_only=True,requested=[])
    with store:
        binding=binding_for(store,ctx)
        assert 'literature.measurement_validation.populate' in {r['name'] for r in binding.catalog(ctx)}
        assert 'measurement_validation_population' not in binding.as_record()['configuration']
        binding.validate_report(ctx,{'numbers':[]},FORM)
        missing=asyncio.run(binding.execute(replace(ctx,received_record_refs=()),'literature.measurement_validation.populate',args,'missing'))
        assert missing['feedback']['code']=='literature_source_not_received'
        out=asyncio.run(binding.execute(ctx,'literature.measurement_validation.populate',args,'empty'))
        assert out['status']=='completed' and out['result']['cells']==[]
        repo=binding._measurement_validation_repository()
        current=replace(ctx,received_record_refs=(*ctx.received_record_refs,*out['record_refs']))
        assert repo.fact_cells(current,out['record_refs'],components=COMPONENTS)==[]
        with pytest.raises(ContractError,match='component_not_selected'):
            repo.project_cells(out['record_refs'],permitted_record_refs=out['record_refs'],components=['reported_cv'])


def test_two_measurements_of_same_component_survive_admission_and_forward_only_possessed_rows(tmp_path):
    store,ctx,args=setup(tmp_path,requested=['reported_cv','relative_squared_deviation_plugin'])
    with store:
        repo,out,current=populated(store,ctx,args)
        selected=[row for row in out['result']['cells'] if row['component']=='reported_cv']
        parent=replace(current,role='annotation',episode_id='parent209',path=(('annotation','parent209'),),assignment={})
        repo.receive_cells(parent,selected,'trusted_fixture_admission')
        assert repo.received_cells(parent)==selected
        assert [row['basis'] for row in repo.fact_cells(parent,out['record_refs'],components=COMPONENTS)]==['within_run','between_run']
        unknown=[row for row in out['result']['cells'] if row['component']=='relative_squared_deviation_plugin']
        with pytest.raises(ContractError,match='cell_not_received'):
            repo.validate_fact_values(parent,unknown)
        repo.receive_cells(parent,selected,'trusted_fixture_admission')
        assert repo.received_cells(parent)==selected
        duplicate=[*selected,selected[0]]
        with pytest.raises(ContractError,match='duplicate_measurement_validation'):
            repo.receive_cells(parent,duplicate,'duplicate')


@pytest.mark.parametrize('mutation',['omitted_between','changed_basis','changed_conditional','unrequested_component','changed_measurement_key'])
def test_exact_original_requested_roster_and_values_are_validated(tmp_path,mutation):
    store,ctx,args=setup(tmp_path,requested=['reported_cv','relative_squared_deviation_plugin'])
    with store:
        repo,out,current=populated(store,ctx,args);rows=deepcopy(out['result']['cells'])
        if mutation=='omitted_between':rows=[row for row in rows if row['basis']!='between_run']
        elif mutation=='changed_basis':rows[0]['basis']='between_run'
        elif mutation=='changed_conditional':rows[1]['conditional_value']=.5
        elif mutation=='changed_measurement_key':rows[0]['measurement_key']='invented_physical_measurement'
        else:rows[0]['component']='cv_fraction'
        binding=binding_for(store,ctx)
        with pytest.raises((ReportBoundaryError,ContractError)):
            binding.validate_report(current,{'numbers':rows},FORM)


@pytest.mark.parametrize('field',['signature','outcome_value','outcome_omission','wrong_run'])
def test_saved_operation_and_return_values_are_authenticated(tmp_path,field):
    store,ctx,args=setup(tmp_path)
    with store:
        repo,out,_=populated(store,ctx,args);ref=out['result']['sheet_ref']
        if field=='signature':store.db.execute("UPDATE literature_measurement_validation_operations SET signature='{}'")
        elif field=='wrong_run':repo=LiteratureMeasurementValidationRepository(store,'different_run')
        else:
            changed=deepcopy(out)
            if field=='outcome_value':changed['result']['cells'][0]['value']=99
            else:changed['result']['cells']=changed['result']['cells'][:-1]
            store.db.execute('UPDATE literature_measurement_validation_operations SET outcome=?',(canonical(changed),))
        with pytest.raises(ContractError):repo.read(ref)


def test_no_recovery_possession_is_gained_from_a_globally_known_reference(tmp_path):
    store,ctx,args=setup(tmp_path)
    with store:
        repo=LiteratureMeasurementValidationRepository(store,ctx.run_id)
        other=replace(ctx,episode_id='unreceived_upstream',received_record_refs=(args['source_ref'],args['recovery']['sheet_ref']))
        with pytest.raises(ContractError,match='not_received'):
            repo.populate(other,args,'forbidden_upstream')


def test_scope_safe_quotes_keep_numeric_conditions_and_mask_statistics_without_sheet_dump(tmp_path):
    store,ctx,args=setup(tmp_path,requested=['relative_squared_deviation_plugin'])
    with store:
        # Deliberately broad source witness containing both nominated precision values.
        first=args['precision'][0]['number']['witness'];second=args['precision'][1]['number']['witness']
        raw=store.get_artifact(store.get(args['source_ref'])['artifact_ref'])
        args['context']['mean_definition']={'source_ref':args['source_ref'],'representation':'original',
            'start':first['start'],'end':second['end'],'quote':raw[first['start']:second['end']].decode()}
        repo,out,_=populated(store,ctx,args)
        text=json.dumps(out['result']['cells'])
        assert 'Buffer20mM at pH7.4' in text
        witness=out['result']['cells'][0]['source_meanings']['mean_definition']
        assert '.8' not in witness['display_text'] and '1.7' not in witness['display_text']
        assert witness['display_text'].count('[unrequested numerical operand]')==2
        state={'literature_experimental_work':{'version':'literature_experimental_task_v1'},
            'literature_assignment':plain(ctx.assignment),'last_local_outcome':out,
            'requested_form':FORM,'goal':{'objective':'Examine reference assay quantification.'}}
        task,steering=render_literature_experimental_prompt(state,'Inspect the selected evidence.').split('\n\nSTEERING\n',1)
        assert task.count(MEASUREMENT_VALIDATION_TASK)==1 and MEASUREMENT_VALIDATION_TASK not in steering
        assert 'episode-fact:'+NAMESPACE in task
        assert 'conditional_exact_value' not in task and 'relative_bias_squared' not in task
        assert 'Conditional value' in steering and 'cv_denominator_unknown' in steering
        assert out['result']['sheet_ref'] not in steering


@pytest.mark.parametrize('field',['experiment','mean_definition'])
def test_broad_table_with_unknown_recovery_spans_is_a_projection_partial_not_a_number_leak(tmp_path,field):
    store,ctx,args=setup(tmp_path,requested=['reported_zprime','control_band_ratio'])
    with store:
        raw=store.get_artifact(store.get(args['source_ref'])['artifact_ref'])
        start,end=raw.index(b'<table>'),raw.index(b'</table>')+len(b'</table>')
        args['context'][field]={'source_ref':args['source_ref'],'representation':'original',
            'start':start,'end':end,'quote':raw[start:end].decode()}
        repo,out,_=populated(store,ctx,args)
        rows=out['result']['cells'];assert len(rows)==2
        quote=rows[0]['source_meanings'][field]
        assert quote['status']=='numerical_scope_unresolved'
        assert quote['unavailable_reason']=='unrequested_numerical_scope_unresolved'
        assert '8.6' not in quote['display_text'] and '8.72' not in quote['display_text']
        assert rows[0]['source_meanings']['matrix']['display_text']=='Buffer20mM at pH7.4'
        assert repo.read(out['result']['sheet_ref'])['extraction']['context'][field]['value']==raw[start:end].decode()
        assert {row['component'] for row in rows}=={'reported_zprime','control_band_ratio'}


def test_original_text_alias_of_same_artifact_cannot_expand_unrequested_statistic(tmp_path):
    store,ctx,args=setup(tmp_path,requested=['reported_zprime'])
    with store:
        source=store.get(args['source_ref'])
        value={name:value for name,value in source.items() if name not in ('id','record_type','origin')}
        value.update(provider='synthetic_same_artifact_text_alias',text_ref=source['artifact_ref'])
        alias=store.put('source',value,origin='caller')['id']
        selected=deepcopy(args['precision'][0]['number']['witness'])
        selected.update(source_ref=alias,representation='text')
        args['context']['mean_definition']=selected
        current=replace(ctx,received_record_refs=(*ctx.received_record_refs,alias))
        repo,out,_=populated(store,current,args)
        meaning=out['result']['cells'][0]['source_meanings']['mean_definition']
        assert meaning['representation']=='text' and meaning['artifact_ref']==source['artifact_ref']
        assert meaning['display_text']=='[unrequested numerical operand]'
        assert meaning['status']=='unrequested_numbers_withheld'


@pytest.mark.parametrize('surface',['own','child','current','history','operation_lookup','return_lookup','parent_direct'])
def test_full_recurring_task_and_scoped_return_rendering_on_actual_surfaces(tmp_path,surface):
    store,ctx,args=setup(tmp_path,requested=['reported_cv'])
    with store:
        repo,out,_=populated(store,ctx,args);rows=out['result']['cells']
        state={'literature_experimental_work':{'version':'literature_experimental_task_v1'},
            'goal':{'objective':'Evaluate the assigned reference assay evidence.'},'requested_form':FORM}
        lookup=[]
        if surface=='own':state['last_local_outcome']=out
        elif surface=='child':state['child_reports']=[{'numbers':rows}]
        elif surface=='current':state['current_report_update']={'numbers':rows}
        elif surface=='history':lookup=[{'status':'completed','result':{'view':'records','records':[{'outcome':out}]}}]
        elif surface=='parent_direct':
            state['literature_experimental_work']['aspect']='reference_evidence_parent'
            state['reference_evidence_parent']={'version':'reference_evidence_parent_v1','source_refs':[args['source_ref']]}
            state['child_reports']=[{'numbers':rows}]
        else:
            state['contract_information_profile']=CONTRACT_INFORMATION_PROFILE
            if surface=='return_lookup':
                lookup=[return_contract_information(facts_by_role={'literature':{NAMESPACE:{'type':'array',
                    'meaning':'Selected source precision components.','report_schema':measurement_validation_cells_schema()}}},
                    permitted_child_roles=['literature'],role='literature',source=NAMESPACE)]
            else:
                from gene_annotation_episode.episode_contract_information import operation_contract_information
                lookup=[operation_contract_information(catalog=_population_catalog(),operation='literature.measurement_validation.populate')]
        prompt=render_literature_experimental_prompt(state,'Preserve the assigned scientific question.',lookup_results=lookup)
        task,steering=prompt.split('\n\nSTEERING\n',1)
        assert task.count(MEASUREMENT_VALIDATION_TASK)==1
        assert MEASUREMENT_VALIDATION_TASK not in steering
        if surface!='operation_lookup':assert 'conditional_exact_value' not in task
        if surface in ('own','child','current','history','parent_direct'):
            assert 'within_run' in steering and 'between_run' in steering
            assert 'Requested precision and control components' in steering
            assert all(row['measurement_key'] not in steering for row in rows)


def test_closed_exact_native_type_rejects_custom_loosened_fields(tmp_path):
    form=deepcopy(FORM)
    form['properties']['numbers']['items']['properties']['conditional_value']['type']='number'
    with pytest.raises(ReportBoundaryError,match='registered source'):
        validate_closed_schema(form)


@pytest.mark.parametrize('profile',[None,CONTRACT_INFORMATION_PROFILE],ids=['legacy','explicit_profile'])
def test_original_source_selected_loop_exact_alias_return_and_readonly_cold_composition(tmp_path,monkeypatch,profile):
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy,ScientificFindingProgress
    from gene_annotation_episode.runtime import run_workflow
    from test_runtime import FixtureController
    from test_contract_information_runtime_059 import PresentedProvider
    from test_runtime_decision_exchanges import select
    store,ctx,args=setup(tmp_path/'state',primary=True,native_only=True)
    source_ref=args['source_ref']; raw=store.get_artifact(store.get(source_ref)['artifact_ref'])
    recovery_args=OriginalRecoverySelection(source_ref,raw).arguments('buffer')
    assignment=plain(ctx.assignment);assignment['requested_calibration_recovery_components']=['recovery','relative_bias']
    compact=obj({'numbers':{'$ref':'episode-fact:'+NAMESPACE},
        'limits':{'type':'string','enum':['population_relationships_unknown']}})
    literal=obj({'numbers':measurement_validation_cells_schema(),
        'limits':{'type':'string','enum':['population_relationships_unknown']}})
    child={'selection':{'kind':'episode_child','role':'literature','assignment':assignment,
        'goal':'Evaluate reported NADPH precision and control separation with the possessed recovery control.',
        'scope':plain(ctx.scope),'purpose':'Return the requested numerical components and unresolved population relationships.',
        'schema_json':json.dumps(compact),'initial_report_json':json.dumps({'limits':'population_relationships_unknown'})},'report_update':{}}
    captured=[];prompts=[];controllers=[]
    def recovery(inputs):
        return {'selection':{'kind':'tool','tool':'literature.calibration.recovery.populate','arguments':recovery_args},
            'report_update':{'limits':'population_relationships_unknown'}}
    def validation(inputs):
        chosen=deepcopy(args)
        ref=inputs['last_local_outcome']['result']['sheet_ref']
        for role in ('recovery','relative_bias'):
            chosen[role]={'namespace':'literature_calibration_recovery_cells','sheet_ref':ref,'component':role}
        prompts.append(render_literature_experimental_prompt(inputs,'Evaluate the reference endpoint measurement.'))
        return {'selection':{'kind':'tool','tool':'literature.measurement_validation.populate','arguments':chosen},
            'report_update':{'limits':'population_relationships_unknown'}}
    def integrate(inputs):
        form,=inputs['child_reports'];captured.append(form)
        prompts.append(render_literature_experimental_prompt(inputs,'Evaluate what the received reference evidence establishes.'))
        loss=[row for row in form['numbers'] if row['component']=='relative_squared_deviation_plugin']
        assert [row['basis'] for row in loss]==['within_run','between_run']
        assert all(row['value'] is None and row['conditional_value'] is not None for row in loss)
        commit={name:[] for name in store.reasoning_schema()['required']}
        quote='human G6PD enzyme';start=raw.index(quote.encode())
        commit['source_subjects']=[{'alias':'actual_studied_reference','reference_type':'assay',
            'source_ref':source_ref,'label':quote,'anchor':{'source_ref':source_ref,
                'artifact_ref':store.get(source_ref)['artifact_ref'],'start':start,'end':start+len(quote.encode()),'quote':quote}}]
        return {'selection':{'kind':'reason','commit':commit},'report_update':{}}
    def controller(path,initial):
        value=FixtureController(str(path),initial,2);controllers.append(value);return value
    try:
        progress=ScientificFindingProgress(FindingProgressPolicy(1))
        class FixtureProvider(PresentedProvider):
            async def complete(self,episode_id,*arguments):
                self.active_episode=episode_id
                return await super().complete(episode_id,*arguments)
        def action(value):
            value=deepcopy(value)
            if profile is not None and value['selection']['kind']=='tool':
                value['selection']['arguments']=json.dumps(value['selection']['arguments'])
            return select(value)
        script=[child,recovery,validation,integrate]
        provider=FixtureProvider([])
        provider.script=iter([action(item) if isinstance(item,dict) else
            (lambda frame,f=item:action(f(provider.views[provider.active_episode]))) for item in script])
        summary=asyncio.run(run_workflow(store,ToolRegistry(store),provider=provider,run_dir=tmp_path/'run',
            controller_factory=controller,project_credit=progress,initial_known_record_refs=[source_ref],
            episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,
                reference_parent_sources=[source_ref],contract_information_profile=profile),),
            binding_definitions={'credit':progress.as_record()},decision_protocol='decision_exchange_v1'))
        assert len(captured)==1 and summary['credit']==0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==4
        assert store.db.execute('SELECT count(*) FROM literature_measurement_validation_operations').fetchone()[0]==1
        assert store.db.execute('SELECT count(*) FROM literature_calibration_recovery_operations').fetchone()[0]==1
        child_record=json.loads(store.db.execute('SELECT request FROM runtime_episodes WHERE json_array_length(path)=2').fetchone()[0])
        assert child_record['report_contract']['measurements']['schema']==literal
        assert child_record['message']['report_contract_declaration']['submitted_schema_json']==child['selection']['schema_json']
        row=store.db.execute('SELECT run_id,episode_id,cells FROM literature_measurement_validation_received').fetchone()
        exact_rows=json.loads(row['cells']);assert exact_rows==captured[0]['numbers']
        run_id,parent_id=row['run_id'],row['episode_id']
        binding=binding_for(store,replace(ctx,run_id=run_id),reference_parent_sources=[source_ref],contract_information_profile=profile)
        descriptor=binding.as_record();sheet_refs=list(dict.fromkeys(row['sheet_ref'] for row in exact_rows))
        receiver=BindingContext(run_id,parent_id,'annotation',(('annotation','root'),),ctx.scope,{}, {}, (source_ref,*sheet_refs))
        assert all(MEASUREMENT_VALIDATION_TASK in prompt.split('\n\nSTEERING\n',1)[0] for prompt in prompts)
        assert REFERENCE_PARENT_TASK in prompts[-1].split('\n\nSTEERING\n',1)[0]
        assert len(provider.rendered)==4
        for text in provider.rendered[1:]:
            task,steering=text.split('\n\nSTEERING\n',1)
            assert task.count(MEASUREMENT_VALIDATION_TASK)==1
            assert MEASUREMENT_VALIDATION_TASK not in steering
            assert 'conditional_exact_value' not in task
        assert [controller.scores for controller in controllers]==[[0,0],[0,0]]
        (tmp_path/'ORIGINAL_ADMITTED_FORM_209.json').write_text(json.dumps(captured[0],indent=2)+'\n')
        checkpoint=tuple(store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone());assert checkpoint==(0,0,0)
        state_path=store.path;store.close();store=None
        hashes=lambda:{str(p.relative_to(state_path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in state_path.rglob('*') if p.is_file()}
        before=hashes();cold=Store.__new__(Store);cold.path=state_path;cold._savepoint=0
        cold.db=sqlite3.connect((state_path/'state.sqlite3').as_uri()+'?mode=ro&immutable=1',uri=True,isolation_level=None)
        cold.db.row_factory=sqlite3.Row;cold.db.execute('PRAGMA query_only=ON')
        cold.db.create_function('library_scope_record',2,cold._scope_filter_record)
        statements=[];cold.db.set_trace_callback(statements.append)
        source_artifact=cold.get(source_ref)['artifact_ref'];get_artifact=cold.get_artifact
        def no_source(ref):
            assert ref!=source_artifact,'original scientific bytes must not be reacquired'
            return get_artifact(ref)
        def forbidden(*_a,**_kw):raise AssertionError('Scientific acquisition/calculation must not run during saved reconstruction')
        monkeypatch.setattr(cold,'get_artifact',no_source)
        for module,names in {
            'literature_measurement_validation_storage':['read_measurement_validation_inputs','populate_measurement_validation'],
            'literature_measurement_validation_inputs':['read_measurement_validation_inputs','validate_measurement_validation_extraction','_read_number','recovery_pair_reasons'],
            'literature_measurement_validation_calculations':['populate_measurement_validation','_root_percent'],
            'literature_calibration_recovery_inputs':['read_calibration_recovery_inputs'],
            'literature_calibration_recovery_calculations':['populate_calibration_recovery'],
        }.items():
            for name in names:monkeypatch.setattr('gene_annotation_episode.'+module+'.'+name,forbidden)
        monkeypatch.setattr(LiteratureMeasurementValidationRepository,'_implementation_receipt',forbidden)
        cold_host=SimpleNamespace(store=cold,run_id=run_id,tools=None);services=WorkflowServices(cold_host)
        monkeypatch.setattr(services,'execute_tool',forbidden)
        restored,=compose_episode_bindings(services,store=cold,journal=SimpleNamespace(store=cold,run_id=run_id),
            execution_backend=None,descriptors=[descriptor],job_episodes=None,resource_estimator=None,role_credit_bindings={}).bindings
        cold_host.episode_bindings=EpisodeBindingRegistry((restored,))
        assert restored.as_record()==descriptor
        assert restored.received_report_facts(receiver)[NAMESPACE]==exact_rows
        assert restored._measurement_validation_repository().fact_cells(receiver,sheet_refs,components=COMPONENTS)==exact_rows
        assert cold.db.total_changes==0 and cold.db.execute('PRAGMA query_only').fetchone()[0]==1
        cold.close();assert hashes()==before
        (tmp_path/'COLD_PROOF_209.json').write_text(json.dumps({'original_typed_rows':True,
            'original_closed_form':True,'source_and_science_blocked_before_composition':True,
            'connection':'mode=ro&immutable=1;query_only=ON','changed_rows':0,'state_files':before,
            'existing_idempotent_schema_checks':sum('CREATE TABLE IF NOT EXISTS' in sql.upper() for sql in statements),
            'ordinary_observations':4,'selected_validation_operations':1,'selected_recovery_operations':1,
            'actual_model_execution':False,'a105_adequacy_claim':False},indent=2)+'\n')
    finally:
        if store is not None:store.close()
