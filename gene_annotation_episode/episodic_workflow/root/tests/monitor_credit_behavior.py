"""Controlled monitor credit selection and exact caller callback preservation."""
from copy import deepcopy
import asyncio
from contextlib import nullcontext
import importlib
from types import SimpleNamespace
import pytest


def progress(reference, *, target='target', returned=False, committed=()):
    return {'version':'progress_snapshot_v1','progress_ref':reference,'target_handle':target,
        'observed_at':'2026-11-11T00:00:00Z','execution_status':{'version':'execution_status_v1',
            'handle':target,'lifecycle_state':'returned' if returned else 'executing',
            'liveness':'not_live' if returned else 'live','failure':None},
        'result_available':returned,'dependencies':[],'committed_record_refs':list(committed),
        'log_windows':[],'provenance_refs':[],'measurements':[]}


def received_fixture(axis):
    context_type=importlib.import_module(axis+'.episode_bindings').BindingContext
    context=context_type('run','monitor','monitor',(('monitor','original'),),{'subject_refs':['input']},{},{})
    values={'baseline':progress('baseline'),'repeat':progress('repeat'),
        'returned':progress('returned',returned=True),'record':progress('record',returned=True,committed=['actual_record']),
        'other':progress('other',target='other')}
    values['repeat'].update(observed_at='2026-11-11T00:01:00Z',log_windows=[{'actual_bytes':987}],provenance_refs=['new_representation'])
    reads=[]
    def read(reference,scope):
        assert scope==context.scope
        reads.append(reference);return deepcopy(values[reference])
    selection={'run_id':'run','episode_id':'monitor','initial_progress_refs':['baseline'],
        'known_progress_refs':['repeat','returned','returned','record','other']}
    return context,selection,SimpleNamespace(read_progress=read),reads


class MonitorCreditBehaviorChecks:
    def setup(self):
        binding=importlib.import_module(self.home+'.episode').MonitorEpisode
        axis=self.home.split('.root.')[0]+'.root.'+self.home.split('.root.')[1].split('.')[0]
        return binding,axis

    @pytest.mark.parametrize('unit',[.125,2.5])
    def test_private_calculator_selection_preserves_received_information(self,unit):
        binding_type,axis=self.setup();context,selection,reader,reads=received_fixture(axis)
        binding=binding_type(object())
        projector=binding.information_credit(reader,information_unit=unit)
        library=importlib.import_module(axis+'.library.progress_information_credit')
        assert type(projector) is library.ProgressInformationCredit
        result=projector(context,selection)
        assert result['credit']==result['monitoring_information_credit']==3*unit
        assert result['newly_informative_received_snapshot_count']==3
        assert [r['progress_ref'] for r in result['monitoring_information_contributions']]==['returned','record','other']
        assert result['known_progress_refs']==['repeat','returned','record','other']
        assert reads==['baseline','repeat','returned','record','other']
        assert binding.information_unit is None  # External unit is not replaced by optional yield configuration.
        assert result['monitoring_information_binding']==projector.as_record()

    def test_caller_credit_callback_and_its_shape_remain_unchanged(self):
        binding_type,axis=self.setup();context,selection,_,_=received_fixture(axis)
        expected={'credit':{'mode':'annotation_axis_credit','caller_value':'original'},'qualification':'original'}
        calls=[]
        def project(actual_context,actual_selection):
            calls.append((actual_context,actual_selection));return expected
        services=importlib.import_module(axis+'.episode_services').WorkflowServices(
            SimpleNamespace(role_credit_projectors={'monitor':project}))
        binding=binding_type(services)
        assert binding.credit_view(context,selection) is expected
        assert calls==[(context,selection)] and binding.credit_kind('monitor')=='monitoring'

    def test_unit_is_an_explicit_operand_even_with_private_yield(self):
        binding_type,axis=self.setup();_,_,reader,_=received_fixture(axis)
        binding=binding_type(object(),information_unit=2,
            yield_settings={'kind':'information_accumulation','cutoff':.25,'uncertainty_alpha':.05})
        with pytest.raises(TypeError):binding.information_credit(reader)
        assert binding.information_credit(reader,information_unit=.5).information_unit==.5
        assert binding.information_unit==2 and binding.yield_settings['cutoff']==.25

    @pytest.mark.parametrize('unit',[None,0,float('inf')])
    def test_original_unit_validation_is_retained(self,unit):
        binding_type,axis=self.setup();_,_,reader,_=received_fixture(axis)
        with pytest.raises(ValueError,match='explicit_positive_monitoring_information_unit_required'):
            binding_type(object()).information_credit(reader,information_unit=unit)

    def test_actual_outcome_reaches_runtime_projection_and_replay_once(self):
        from gene_annotation_episode.episodic_workflow.root.tests.monitor_task_behavior import MonitorTaskBehaviorChecks
        helper=MonitorTaskBehaviorChecks();helper.home=self.home
        task,binding,_,runtime=helper.setup_task()
        _,axis=self.setup();context,selection,reader,reads=received_fixture(axis)
        project=binding.information_credit(reader,information_unit=.25)
        delivered=[];saved={};executed=[];controller_inputs=[]
        results=[{'status':'completed','progress_refs':['repeat'],'record_refs':[],'changed_record_refs':[]},
            {'status':'completed','progress_refs':['returned'],'record_refs':[],'changed_record_refs':[]},
            {'status':'unavailable','progress_refs':[],'record_refs':[],'changed_record_refs':[]}]
        async def execute(source,name,arguments,**kwargs):
            executed.append(kwargs['operation_key']);return deepcopy(results[len(executed)-1])
        def receive(source,selected,result,index):delivered.extend(result['progress_refs'])
        def observe(source,index,credit):
            controller_inputs.append((index,credit));return {'decision_index':index,'credit':credit}
        workflow=SimpleNamespace(run_id='run',execution_binding=None,wait_inputs_version=None,
            completed_action_inputs_version=None,pending_work=lambda source: {'version': 'pending_work_v2', 'captured_at': '2026-11-01T00:00:00+00:00', 'items': []},native_timing_information=None,
            journal=SimpleNamespace(row=lambda table,episode,index:saved.get(index),
                save=lambda table,row:saved.__setitem__(row['decision_index'],row),measure=lambda *args:nullcontext()),
            execute=execute,receive_native_outcome=lambda *args:None,receive_outcome=receive,
            is_job_source=lambda source:False,specialist=lambda source:binding,binding_context=lambda source:context,
            record_selection=lambda episode:{'run_id':'run','episode_id':'monitor'},
            progress_selection=lambda source:{'initial_progress_refs':['baseline'],'known_progress_refs':list(delivered)},
            role_credit_projectors={'monitor':project},controller_value=observe)
        workflow.source_credit_view=lambda source:runtime.Workflow.source_credit_view(workflow,source)
        if axis.endswith('.root.a103'):
            # A103's source_credit_view first resolves a legacy parent through the bound roles.
            workflow.episode_bindings=SimpleNamespace(roles=('monitor',))
            workflow.legacy_parent_for_path=lambda path:runtime.Workflow.legacy_parent_for_path(workflow,path)
        binding.services=importlib.import_module(axis+'.episode_services').WorkflowServices(workflow)
        task.workflow=workflow
        selected={'kind':'tool','tool':'progress.observe','arguments':{'requested_fields':['execution_status']}}
        for index in range(3):asyncio.run(task.execute(selected,index))
        original_reads=list(reads)
        replay=asyncio.run(task.execute(selected,2))
        assert controller_inputs==[(0,0.0),(1,.25),(2,.25),(2,.25)]
        assert reads==original_reads  # Replay reconstructs the saved input without projecting again.
        assert executed==['run:monitor:0','run:monitor:1','run:monitor:2']
        assert replay=={'decision_index':2,'credit':.25}
        assert delivered==['repeat','returned'] and reads
