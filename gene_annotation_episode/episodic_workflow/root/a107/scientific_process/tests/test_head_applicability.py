"""Real saved-cell annotation equivalence and scientific edge applicability.

Source population uses the original deterministic synthetic recipes. Typed cell
delivery uses the repository's explicit trusted manual admission API; this is
not a claim of a completed workflow or autonomous science.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import importlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import pytest
from gene_annotation_episode.episodic_workflow.root.tests.scientific_head_boundaries import ScientificHeadBoundaryChecks
from .original_applicability_fixture import OriginalReceivedEvidence, OriginalRegistry, setup_case
from . import original_applicability_fixture as originals

AXIS='a107'
def own(name):return importlib.import_module('gene_annotation_episode.episodic_workflow.root.'+AXIS+'.'+name)


class TestHeadApplicability:
    axis=AXIS
    module=ScientificHeadBoundaryChecks.module
    scientific=ScientificHeadBoundaryChecks.scientific

    def test_original_annotation_typed_sheet_and_validation(self, scientific, tmp_path):
        kwargs={'case':'matched'} if AXIS=='a107' else {'primary':False,'incomplete':True}
        store, source_context, arguments=setup_case(tmp_path/'received-cell-state',**kwargs)
        with store:
            host=SimpleNamespace(store=store,run_id=source_context.run_id,tools=own('tools').ToolRegistry(store))
            services=own('episode_services').WorkflowServices(host)
            source=own('scientific_process.published_evidence_assessment.episode').LiteratureEpisode(services)
            host.episode_bindings=own('episode_bindings').EpisodeBindingRegistry((source,))
            kind='partner' if AXIS=='a107' else 'reaction'
            outcome=asyncio.run(source.execute(source_context,'literature.'+kind+'.populate',arguments,'original-synthetic-population'))
            assert outcome['status']=='completed',outcome
            sheet=outcome['result']['sheet_ref']
            reports=own('component_axis_reports')
            field=next(iter(reports.cell_views(AXIS.upper())))
            repository=reports.repository(services,AXIS.upper(),field)
            cells=repository.project_cells([sheet],permitted_record_refs=outcome['record_refs'])[:1]
            assert len(cells)==1
            path=(('annotation','legacy_parent'),)
            episode=own('method_loop.identities').EpisodeRef(host.run_id,path).episode_id
            request={'message':{'scope':dict(source_context.scope),'episode_assignment':{}}}
            known=tuple(dict.fromkeys([*source_context.received_record_refs,*outcome['record_refs']]))
            context=own('episode_bindings').BindingContext(host.run_id,episode,'annotation',path,source_context.scope,{},request,known)
            journal=own('episode_journal').Journal(store,host.run_id)
            journal.save('runtime_episodes',{'episode_id':episode,'path':json.dumps(path),'request':json.dumps(request),
                'initial_credit':0,'state':'active','completion':None,'archive':None})
            host.receipts=own('episode_receipts').EpisodeReceipts(store,host.run_id)
            host.receipts.bind(episode,None);host.receipts.receive(episode,known,kind='initial')
            host.record_selection=lambda episode_id:own('runtime').Workflow.record_selection(host,episode_id)
            repository.receive_cells(context,cells,'explicit-manual-received-cell-fixture')
            current=scientific.binding;current.services=services
            original_type=type('OriginalHead',(OriginalReceivedEvidence,type(current)),{})
            original=object.__new__(original_type);original.__dict__.update(current.__dict__)
            before=OriginalRegistry((original,));after=own('episode_bindings').EpisodeBindingRegistry((current,))
            expected=before.received_report_facts(context)
            actual=after.received_report_facts(context)
            assert actual==expected and actual[reports.SCORING_FACT][AXIS.upper()]['numerical_results']
            sheet_view=actual[reports.SCORING_FACT][AXIS.upper()]
            assert sheet_view['combined_scientific_score'] is None
            returned=[cell for row in sheet_view['numerical_results'] for view in row['returned_views'].values() for cell in view]
            assert returned==cells
            schema=reports.report_schema(AXIS.upper())
            form={name:deepcopy(node['const']) if 'const' in node else [] if node.get('type')=='array' else 0
                for name,node in schema['properties'].items()}
            form[field]=cells
            assert before.validate_received_report(context,form,schema) is None
            assert after.validate_received_report(context,form,schema) is None
            corrupted=deepcopy(form);corrupted[field][0]['component']='not_an_original_component'
            def observe(call):
                try:call()
                except Exception as error:return type(error),str(error),getattr(error,'code',None)
                raise AssertionError('original typed validation must reject changed component identity')
            assert observe(lambda:before.validate_received_report(context,corrupted,schema))==observe(lambda:after.validate_received_report(context,corrupted,schema))
            scientific_path=context.path+(('scientific_process','role_guard'),)
            scientific_episode=own('method_loop.identities').EpisodeRef(context.run_id,scientific_path).episode_id
            scientific_context=replace(context,role='scientific_process',path=scientific_path,episode_id=scientific_episode)
            assert before.received_report_facts(scientific_context)==after.received_report_facts(scientific_context)=={}
            compatibility=own('scientific_process.received_evidence').ScientificReceivedEvidence
            assert type(current).received_report_facts is compatibility.received_report_facts
            assert type(current).validate_received_report is compatibility.validate_received_report

    @pytest.mark.parametrize('override',[None,False,'custom','property_error','property_callback','property_attribute_error','property_value_error','property_none','property_false'])
    @pytest.mark.parametrize('callback_name',['received_report_facts','validate_received_report'])
    def test_custom_callback_precedence_and_failure_identity(self,scientific,override,callback_name):
        events=[]
        if override=='custom':
            def value(self,*arguments):events.append('custom');return {'original_custom_fact':1}
        elif override=='property_error':
            def getter(self):events.append('property');raise RuntimeError('original_property_error')
            value=property(getter)
        elif override=='property_callback':
            def getter(self):
                events.append('property')
                def callback(*arguments):events.append('callback');return {'original_property_fact':1}
                return callback
            value=property(getter)
        elif override in {'property_attribute_error','property_value_error','property_none','property_false'}:
            def getter(self):
                events.append('property')
                if override=='property_attribute_error':raise AttributeError('original_property_missing')
                if override=='property_value_error':raise ValueError('original_property_invalid')
                return None if override=='property_none' else False
            value=property(getter)
        else:value=override
        base=type(scientific.binding)
        old_type=type('Before',(OriginalReceivedEvidence,base),{callback_name:value})
        new_type=type('After',(base,),{callback_name:value})
        def run(cls,registry):
            instance=object.__new__(cls);instance.__dict__.update(scientific.binding.__dict__)
            events.clear()
            arguments=(scientific.parent,) if callback_name=='received_report_facts' else (scientific.parent,{}, {})
            try:result=('return',getattr(registry((instance,)),callback_name)(*arguments))
            except Exception as error:result=('error',type(error),str(error))
            return result,list(events)
        assert run(old_type,OriginalRegistry)==run(new_type,own('episode_bindings').EpisodeBindingRegistry)

    @pytest.mark.parametrize('mode',['attribute_error','value_error','none','false','delegate','getattr','super'])
    def test_original_custom_lookup_and_super_resolution(self,scientific,mode):
        events=[]
        head=type(scientific.binding)
        original_head=type('OriginalHead',(OriginalReceivedEvidence,head),{})
        def customize(base):
            if mode=='super':
                class Custom(base):
                    def received_report_facts(self,context):
                        events.append('super')
                        return super().received_report_facts(context)
                return Custom
            if mode=='getattr':
                class Custom(base):
                    def __getattr__(self,name):
                        if name=='received_report_facts':
                            events.append('getattr')
                            raise ValueError('inherited_callback_must_be_found_first')
                        raise AttributeError(name)
                return Custom
            class Custom(base):
                def __getattribute__(self,name):
                    if name=='received_report_facts':
                        events.append('getattribute')
                        if mode=='attribute_error':raise AttributeError('original_custom_lookup_missing')
                        if mode=='value_error':raise ValueError('original_custom_lookup_invalid')
                        if mode=='none':return None
                        if mode=='false':return False
                    return super().__getattribute__(name)
            return Custom
        def observe(base,registry):
            cls=customize(base);instance=object.__new__(cls);instance.__dict__.update(scientific.binding.__dict__)
            registered=registry((instance,));events.clear()
            try:result=('return',registered.received_report_facts(scientific.parent))
            except Exception as error:result=('error',type(error),str(error))
            return result,list(events)
        assert observe(original_head,OriginalRegistry)==observe(head,own('episode_bindings').EpisodeBindingRegistry)

    @pytest.mark.parametrize('mode',['attribute_error','value_error','none','false','callable'])
    @pytest.mark.parametrize('callback_name',['received_report_facts','validate_received_report'])
    def test_original_custom_descriptor_semantics(self,scientific,mode,callback_name):
        events=[]
        class Descriptor:
            def __get__(self,instance,owner):
                events.append('descriptor')
                if mode=='attribute_error':raise AttributeError('original_descriptor_missing')
                if mode=='value_error':raise ValueError('original_descriptor_invalid')
                if mode=='none':return None
                if mode=='false':return False
                def callback(*arguments):events.append('descriptor_callback');return {'original_descriptor_fact':1}
                return callback
        head=type(scientific.binding)
        def observe(bases,registry):
            cls=type('DescriptorHead',bases,{callback_name:Descriptor()})
            instance=object.__new__(cls);instance.__dict__.update(scientific.binding.__dict__)
            registered=registry((instance,));events.clear()
            arguments=(scientific.parent,) if callback_name=='received_report_facts' else (scientific.parent,{}, {})
            try:result=('return',getattr(registered,callback_name)(*arguments))
            except Exception as error:result=('error',type(error),str(error))
            return result,list(events)
        assert observe((OriginalReceivedEvidence,head),OriginalRegistry)==observe((head,),own('episode_bindings').EpisodeBindingRegistry)

    def test_declared_compatibility_owner_has_original_mixin_position(self,scientific):
        bases=type(scientific.binding).__bases__
        compatibility=own('scientific_process.received_evidence').ScientificReceivedEvidence
        index=bases.index(compatibility)
        assert bases[index-1].__name__=='ScientificReportIntegrity'
        assert bases[index+1].__name__=='ScientificSourceReferences'
        assert not isinstance(SimpleNamespace(),compatibility)


@pytest.mark.parametrize('first',['scientific_process.received_evidence','scientific_process.episode','episode_bindings'])
def test_annotation_default_import_orders(first,tmp_path):
    # Sequential subprocesses remain descendants of the one test workflow.
    script='import importlib; p='+repr('gene_annotation_episode.episodic_workflow.root.'+AXIS+'.')+'; '+\
        'names='+repr([first,'scientific_process.received_evidence','scientific_process.episode','episode_bindings'])+'; '+\
        '[importlib.import_module(p+n) for n in names]'
    subprocess.run([sys.executable,'-B','-c',script],check=True,cwd=Path.cwd())


@pytest.mark.parametrize('child',['scientific_process','hpc_work_planning','published_evidence_assessment'])
def test_no_receipts_short_circuits_original_job_predicate(child,monkeypatch):
    module=own('scientific_process.from_child_'+child)
    def forbidden(*args):raise AssertionError('scientific parent is already known')
    workflow=SimpleNamespace(receipts=None,progress_provider=None,is_job_source=forbidden)
    assert module.receive_report(workflow,object(),{}, {},0)==[]


@pytest.mark.parametrize('child,role',[('scientific_process','scientific_process'),('hpc_work_planning','hpc'),('published_evidence_assessment','literature')])
@pytest.mark.parametrize('saved_extra',[False,True])
def test_directional_saved_envelope_keeps_actual_fields(child,role,saved_extra,monkeypatch):
    module=own('runtime');events=[]
    class Identity:
        @staticmethod
        def identity(*args,**kwargs):return SimpleNamespace(episode_id='controlled-child')
    class Goal:
        @staticmethod
        def child(parent,**kwargs):events.append(('goal',kwargs));return {'original_goal':kwargs}
    for target in (module,originals):
        monkeypatch.setattr(target,'Episode',Identity);monkeypatch.setattr(target,'EpisodeGoal',Goal)
        monkeypatch.setattr(target,'EpisodeRequest',lambda goal,message,contract:(goal,message,contract))
        monkeypatch.setattr(target,'Record',lambda message:message)
    workflow=SimpleNamespace(context=object(),grains={role:object(),'scientific_process':object()},run_id='r',
        inprocess_completion_order='original_order',scientific_process_binding=object(),receipts=None,
        launch_instructions=SimpleNamespace(materialize=lambda value:events.append(('launch',value))))
    assignment={'launch_instructions':None,'original_assignment':True}
    scientific={'filled_original_scientific_process':True} if role=='scientific_process' or saved_extra else None
    job={'original_saved_job_metadata':True} if saved_extra else None
    kwargs=dict(parent=object(),
        parent_path=(('scientific_process','parent'),),contract=SimpleNamespace(schema={}),initial={'status':'unresolved'},
        job_assignment=job,episode_assignment=assignment,scientific_process=scientific)
    captured={}
    class SourceConstructorReached(Exception):pass
    def source_type(actual_workflow,path,request,scope):
        assert actual_workflow is workflow
        captured.update(path=path,request=request,scope=scope)
        raise SourceConstructorReached
    workflow.episode_bindings=SimpleNamespace(roles=(role,),
        for_path=lambda path:SimpleNamespace(decision_source_type=source_type))
    # Observe the real build prelude at its existing source constructor. Later
    # admission/restoration is outside this original envelope comparison.
    with pytest.raises(SourceConstructorReached):
        module.Workflow.build(workflow,role,'child_0','original question',{},**kwargs)
    goal,message,contract=captured['request']
    result=(captured['path'],goal,message,SimpleNamespace(episode_id='controlled-child'),captured['request'])
    observed=list(events);events.clear()
    expected=getattr(originals,'original_assemble_'+child)(workflow,role,'child_0','original question',{},**kwargs)
    assert result==expected and observed==events
    message=result[2]
    assert message['episode_assignment']==assignment
    assert ('job_assignment' in message)==saved_extra
    assert ('scientific_process' in message)==(role=='scientific_process' or saved_extra)
    assert ('scientific_invocation_ref' in message)==(role=='scientific_process')
    assert message['initial_report']=={'status':'unresolved'}
    assert message['inprocess_completion_order']=={'version':'original_order'}
    assert events[-1]==('launch',None)
