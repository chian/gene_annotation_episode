"""Controlled synthetic selected work, exact return custody and cold recovery."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts, plain
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_compiled_assay_prompt import COMPILED_ASSAY_TASK
from gene_annotation_episode.literature_compiled_assay_storage import (
    LiteratureCompiledAssayRepository, compiled_assay_cells_schema, REQUESTED, COMPONENTS, NAMESPACE,
)
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_compiled_assay_185 import setup, populate, CONTEXT_TEXT, readonly, forbid
from test_literature_assay_inputs import witness
from test_runtime import FixtureController, ScriptedProvider

REQUEST = ['measured_endpoint_per_selected_amount','calibrated_measured_endpoint_per_selected_amount','corrected_activity']
FORM = obj({'numerical_sections':compiled_assay_cells_schema()})


def binding_for(store,ctx,enabled=True):
    host=SimpleNamespace(store=store,run_id=ctx.run_id,tools=ToolRegistry(store))
    binding=LiteratureEpisodes(WorkflowServices(host),rate_population=True,compiled_assay_population=enabled,active_site_population=True)
    host.episode_bindings=EpisodeBindingRegistry((binding,))
    return binding


def test_disabled_catalog_and_assignment_are_unchanged_and_enabled_contract_is_selected(tmp_path):
    store,ctx,args,_=setup(tmp_path)
    with store:
        disabled=binding_for(store,ctx,False)
        baseline=LiteratureEpisodes(disabled.services,rate_population=True,active_site_population=True)
        assert disabled.catalog(ctx)==baseline.catalog(ctx)
        assert disabled.assignment_schema('literature')==baseline.assignment_schema('literature')
        assert NAMESPACE not in disabled.fact_sources('literature')
        assert 'compiled_assay_population' not in disabled.as_record()['configuration']
        enabled=binding_for(store,ctx)
        assert 'literature.assay.components.populate' in {row['name'] for row in enabled.catalog(ctx)}
        assert REQUESTED in enabled.assignment_schema('literature')['properties']
        descriptor=enabled.as_record()
        assert LiteratureEpisodes(enabled.services,**descriptor['configuration']).as_record()==descriptor
        context=replace(ctx,assignment={**plain(ctx.assignment),REQUESTED:REQUEST})
        result=asyncio.run(enabled.execute(context,'literature.assay.components.populate',args,'selected-binding'))
        assert result['status']=='completed',result
        current=replace(context,received_record_refs=(*context.received_record_refs,*result['record_refs']))
        form=form_with_facts({},FORM,enabled.facts(current,{'committed_record_refs':result['record_refs']}))
        assert [row['component'] for row in form['numerical_sections']]==REQUEST
        enabled.validate_report(current,form,FORM)
        omitted=replace(current,assignment={k:v for k,v in current.assignment.items() if k!=REQUESTED})
        with pytest.raises(ReportBoundaryError,match='unrequested|subset_mismatch'):
            enabled.validate_report(omitted,form,FORM)


def test_exact_subset_admission_no_hidden_expansion_and_changed_return_rejection(tmp_path):
    store,ctx,args,_=setup(tmp_path)
    with store:
        repo,outcome,saved=populate(store,ctx,args)
        ref=outcome['result']['sheet_ref']
        rows=repo.project_cells([ref],permitted_record_refs=[ref],components=['corrected_activity'])
        parent=replace(ctx,episode_id='parent',role='annotation',path=(('annotation','parent'),),assignment={},received_record_refs=(ref,))
        repo.receive_cells(parent,rows,'synthetic-exact-return')
        assert repo.fact_cells(parent,[ref],components=COMPONENTS)==rows
        altered=deepcopy(rows);altered[0]['value']=999
        with pytest.raises(ContractError,match='differs_from_saved'):
            repo.validate_fact_values(parent,altered)
        private=repo.project_cells([ref],permitted_record_refs=[ref],components=['net_rate'])
        with pytest.raises(ContractError,match='not_received'):
            repo.validate_fact_values(parent,private)
        assert not any('row' in dep for dep in rows[0]['dependencies'])


def test_full_task_and_terse_numeric_views_recur_without_host_ids_or_duplicate_rows(tmp_path):
    store,ctx,args,_=setup(tmp_path)
    with store:
        _,outcome,saved=populate(store,ctx,args)
        rows=outcome['result']['cells']
        chosen=[row for row in rows if row['component'] in REQUEST]
        state={'literature_experimental_work':{'version':'literature_experimental_task_v1'},
            'literature_assignment':{REQUESTED:REQUEST},'working_state':{},'last_local_outcome':{'result':{'view':'compiled_assay_components','cells':chosen}},
            'child_reports':[{'numbers':chosen,'interpretation':'partial'}]}
        task,steering=render_literature_experimental_prompt(state,'Compile the synthetic enzyme activity.').split('\n\nSTEERING\n')
        assert COMPILED_ASSAY_TASK in task
        assert '0.907029' in steering and 'joint uncertainty propagation is unimplemented' in steering
        assert saved['input_source_ref'] not in steering and 'artifact_' not in steering
        assert 'selected_source_component_' not in steering and 'physical_source_span_' not in steering
        assert 'retained dependency identity' in steering and 'canonical measurement' in steering
        prior={'result':{'view':'records','records':[{'outcome':state['last_local_outcome'],'admitted_report':{'numbers':chosen}}]}}
        after=render_literature_experimental_prompt(state,'Compile the synthetic enzyme activity.',lookup_results=[prior])
        assert COMPILED_ASSAY_TASK in after.split('\n\nSTEERING\n')[0]
        from gene_annotation_episode.literature_compiled_assay_render import render_received
        rendered=[]
        render_received(rendered,[*chosen,*chosen],section=lambda p,t,c:p.append(t+'\n'+c),table=lambda h,r:'\n'.join('|'.join(map(str,row)) for row in r))
        assert '\n'.join(rendered).count('Compiled source assay 1')==1
        assert sum(row['component']=='corrected_activity' for row in chosen)==1


def disable_science(monkeypatch):
    for module,names in {
        'literature_compiled_assay_storage':('read_compiled_assay_inputs','populate_compiled_assay'),
        'literature_compiled_assay_inputs':('read_compiled_assay_inputs','_quantity','_covariance'),
        'literature_compiled_assay_calculations':('populate_compiled_assay','populate_corrected_activity'),
        'literature_activity_calculations':('populate_corrected_activity',),
        'literature_optical_storage':('read_optical_rate_operands','calculate_nadh_optical_rate'),
        'literature_active_site_storage':('read_active_site_inputs','populate_active_site_components'),
        'literature_active_site_inputs':('unit_scale','_derived_quantity','validate_active_site_extraction'),
        'literature_calibration_recovery_inputs':('read_calibration_recovery_inputs',),
        'literature_calibration_recovery_calculations':('populate_calibration_recovery',),
        'literature_assay_inputs':('read_assay_inputs',),
    }.items():
        for name in names:monkeypatch.setattr('gene_annotation_episode.'+module+'.'+name,forbid)


def hashes(path):
    return {str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}


def test_selected_original_component_operations_compile_return_and_cold_factory_exactly(tmp_path,monkeypatch):
    proof=Path(os.environ['COMPILED_ASSAY_PROOF_DIR']) if os.environ.get('COMPILED_ASSAY_PROOF_DIR') else tmp_path/'proof'
    proof.mkdir(parents=True,exist_ok=False)
    store,ctx,args,outputs=setup(proof/'state')
    # Existing setup outputs prepare input contracts only. Runtime receives the
    # original synthetic sources; it selects and records its own five operations.
    raw_refs=[ref for ref in ctx.received_record_refs if store.get(ref)['record_type']=='source' and store.get(ref)['origin']=='caller']
    assignment={'version':'literature_assignment_v1','question_context_refs':[],'source_refs':raw_refs,
        REQUESTED:REQUEST,'requested_calibration_recovery_components':['recovery'],
        'requested_active_site_components':['active_site_concentration'],'requested_optical_components':['net_rate']}
    child={'selection':{'kind':'episode_child','role':'literature','assignment':assignment,
        'goal':'Compile the synthetic reference activity from its compatible saved experimental components.',
        'scope':plain(ctx.scope),'purpose':'Return the requested partial normalizations and fully corrected source activity, retaining dependence and limitations.',
        'schema_json':json.dumps(FORM),'initial_report_json':'{}'},'report_update':{}}
    selected={};prompts=[];forms=[];controllers=[]
    def work(tool,arguments,previous=None):
        def select(inputs):
            prompt=render_literature_experimental_prompt(inputs,'Compile the synthetic reference assay.')
            assert COMPILED_ASSAY_TASK in prompt.split('\n\nSTEERING\n')[0]
            prompts.append(prompt)
            if previous:
                selected[previous]=inputs['last_local_outcome']['result']['sheet_ref']
            value=arguments() if callable(arguments) else arguments
            return {'selection':{'kind':'tool','tool':tool,'arguments':value},'report_update':{}}
        return select
    def compiled_arguments():
        value=deepcopy(args)
        for role in ROLES:
            family={'q':'optical','g':'assay','k':'recovery','E':'active','u':'assay','v':'assay'}[role]
            value['operands'][role]['sheet_ref']=selected[family]
        return value
    def integrate(inputs):
        form,=inputs['child_reports'];forms.append(deepcopy(form))
        assert [row['component'] for row in form['numerical_sections']]==REQUEST
        assert form['numerical_sections'][-1]['value']==pytest.approx(.9070294784580499)
        prompt=render_literature_experimental_prompt(inputs,'Evaluate the returned experimental evidence.')
        assert COMPILED_ASSAY_TASK in prompt.split('\n\nSTEERING\n')[0]
        assert 'recorded_dependency_keys' not in prompt.split('\n\nSTEERING\n')[1]
        commit={name:[] for name in store.reasoning_schema()['required']}
        source=store.get(args['source_ref']);w=witness(CONTEXT_TEXT,'enzyme P',source=args['source_ref'])
        commit['source_subjects']=[{'alias':'synthetic_source_enzyme','reference_type':'assay','source_ref':args['source_ref'],'label':'enzyme P',
            'anchor':{'source_ref':args['source_ref'],'artifact_ref':source['artifact_ref'],'start':w['start'],'end':w['end'],'quote':'enzyme P'}}]
        return {'selection':{'kind':'reason','commit':commit},'report_update':{}}
    def controller(path,initial):
        value=FixtureController(str(path),initial,2 if len(path)==1 else 5);controllers.append(value);return value
    from gene_annotation_episode.literature_compiled_assay_inputs import ROLES
    provider=ScriptedProvider([child,
        work('literature.assay.populate',outputs['assay']['arguments']),
        work('literature.optical.populate',outputs['optical']['arguments'],'assay'),
        work('literature.calibration.recovery.populate',outputs['recovery']['arguments'],'optical'),
        work('literature.active_site.populate',outputs['active']['arguments'],'recovery'),
        work('literature.assay.components.populate',compiled_arguments,'active'),integrate])
    scorer=ScientificFindingProgress(FindingProgressPolicy(1))
    summary=asyncio.run(run_workflow(store,ToolRegistry(store),provider=provider,run_dir=proof/'run',controller_factory=controller,
        project_credit=scorer,initial_known_record_refs=raw_refs,
        episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,active_site_population=True,compiled_assay_population=True,
            reference_parent_sources=[args['source_ref']]),),binding_definitions={'credit':scorer.as_record()}))
    assert len(forms)==1 and summary['credit']==0
    assert [c.scores for c in controllers]==[[0,0],[0,0,0,0,0]]
    assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==7
    run_id,parent_id=store.db.execute('SELECT run_id,episode_id FROM literature_compiled_assay_received').fetchone()
    assert store.db.execute('SELECT count(*) FROM literature_compiled_assay_operations WHERE run_id=?',(run_id,)).fetchone()[0]==1
    descriptors=json.loads(store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?',(run_id,)).fetchone()[0])['episode_bindings']
    receiver=replace(ctx,run_id=run_id,episode_id=parent_id,role='annotation',path=(('annotation',parent_id),),assignment={},
        received_record_refs=tuple(row['sheet_ref'] for row in forms[0]['numerical_sections']))
    source_ref=forms[0]['numerical_sections'][0]['sheet_ref']; compiled=LiteratureCompiledAssayRepository(store,run_id).read(source_ref)
    allowed={row[field] for row in store.list('source') if row['origin']=='tool' for field in ('artifact_ref','request_ref')}
    for name,value in [('ORIGINAL_ADMITTED_FORM_001.json',forms[0]),('SAVED_SHEET_001.json',compiled),('BINDING_DESCRIPTOR_001.json',descriptors),('CHILD_TASKS_001.json',prompts)]:
        (proof/name).write_text(json.dumps(value,indent=2)+'\n')
    store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');store.close();before=hashes(proof/'state')
    disable_science(monkeypatch)
    with readonly(proof/'state') as cold:
        raw=cold.get_artifact
        def saved_only(ref):
            assert ref in allowed,'cold recovery cannot read scientific source bytes'
            return raw(ref)
        monkeypatch.setattr(cold,'get_artifact',saved_only)
        host=SimpleNamespace(store=cold,run_id=run_id,tools=None);services=WorkflowServices(host)
        restored=compose_episode_bindings(services,store=cold,journal=SimpleNamespace(store=cold,run_id=run_id),execution_backend=None,
            descriptors=descriptors,job_episodes=None,resource_estimator=None,role_credit_bindings={})
        binding,=restored.bindings;host.episode_bindings=EpisodeBindingRegistry(restored.bindings)
        assert binding.received_report_facts(receiver)[NAMESPACE]==forms[0]['numerical_sections']
        assert binding._compiled_assay_repository().read(source_ref)==compiled
        assert cold.db.total_changes==0
    assert before==hashes(proof/'state')
    (proof/'PROOF_RESULT_001.json').write_text(json.dumps({'provider':'controlled synthetic ScriptedProvider','actual_model_science':False,
        'source_component_operations':4,'compiled_operations':1,'ordinary_runtime_observations':7,'targets':0,
        'original_typed_admission':True,'full_task_recurred':len(prompts)==5,'source_parsers_calculators_disabled_before_factory':True,
        'cold_exact_form':True,'sqlite_mode':'ro&immutable=1; closed checkpointed writer','database_writes':0,'byte_preservation':True,
        'a105_adequacy_claim':False},indent=2)+'\n')
