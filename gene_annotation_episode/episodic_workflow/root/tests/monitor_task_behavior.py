"""Controlled monitor task transitions; no model, native job or scientific grading."""
import asyncio
from contextlib import nullcontext
from copy import deepcopy
import importlib
import json
from types import SimpleNamespace

import pytest


PENDING_WORK={'version':'pending_work_v2','captured_at':'2026-11-01T00:00:00+00:00','items':[]}


class MonitorTaskBehaviorChecks:
    def setup_task(self):
        binding_type=importlib.import_module(self.home+'.episode').MonitorEpisode
        task_type=importlib.import_module(self.home+'.task').ProgressMonitoringTask
        axis=self.home.split('.root.')[0]+'.root.'+self.home.split('.root.')[1].split('.')[0]
        runtime=importlib.import_module(axis+'.runtime')
        assignment={'version':'monitor_assignment_v1','target_handle':'target',
            'requested_fields':['execution_status'],'known_progress_refs':[],
            'permitted_committed_record_types':[]}
        context=SimpleNamespace(run_id='run',episode_id='monitor',role='monitor',
            path=(('monitor','original'),),scope={},assignment=assignment,
            request={'goal':{'objective':'Resolve exposed progress'}})
        services=SimpleNamespace(reference_in_scope=lambda *args:True,
            describe_progress_target=lambda *args:None,dependencies=lambda *args:[],
            progress_selection=lambda *args:{'known_progress_refs':[]})
        binding=binding_type(services)
        task=object.__new__(task_type)
        task.episode_id='monitor';task.path=context.path;task.scope={}
        task.calls=0;task._execution_context=None;task._delivery_resolution_ref=None
        task.report_values={};task.report_basis=[];task.interpret_schema=runtime._object({})
        task.last_outcome=None;task.last_outcome_index=None;task.feedback=None
        task.request=SimpleNamespace(goal=SimpleNamespace(as_record=lambda:{'objective':'Resolve exposed progress'}),
            message=SimpleNamespace(as_record=lambda:{'episode_assignment':deepcopy(assignment)}),report_contract=None)
        task.checkpoint=lambda:None
        return task,binding,context,runtime

    @pytest.mark.parametrize('status',['completed','invalid','failed','unavailable'])
    def test_executed_outcomes_reenter_original_progress_and_replay_once(self,status):
        task,binding,context,runtime=self.setup_task()
        saved={};executions=[];receipts=[];projected=[]
        result={'status':status,'record_refs':[],'changed_record_refs':[],
            'feedback':{'category':'controlled_actual_outcome'}}
        async def execute(source,name,arguments,**kwargs):
            executions.append(kwargs['operation_key'])
            return deepcopy(result)
        async def score(source,index,result):
            # The actual runtime returns unchanged because this predefined
            # monitor declares no automatic scientific grading callbacks.
            assert not hasattr(binding,'automatic_score_judgments')
            return result
        def credit(source):
            projected.append('original_monitor_credit')
            return {'credit':2.5}
        task.workflow=SimpleNamespace(run_id='run',execution_binding=None,pending_work=lambda source:deepcopy(PENDING_WORK),
            journal=SimpleNamespace(
                row=lambda table,episode,index:saved.get(index),
                save=lambda table,row:saved.__setitem__(row['decision_index'],row),measure=lambda *args:nullcontext()),
            execute=execute,receive_native_outcome=lambda *args:None,
            receive_outcome=lambda source,selection,result,index:receipts.append((index,result['status'])),
            automatic_score_updates=score,source_credit_view=credit,
            controller_value=lambda source,index,credit:{'decision_index':index,'credit':credit})
        selection={'kind':'tool','tool':'progress.observe','arguments':{'requested_fields':['execution_status']}}
        assert runtime.observes_action_outcome('tool',status)
        first=asyncio.run(task.execute(selection,4))
        second=asyncio.run(task.execute(selection,4))
        assert first==second=={'decision_index':4,'credit':2.5}
        assert executions==['run:monitor:4'] and receipts==[(4,status)]
        assert projected==['original_monitor_credit']
        assert json.loads(saved[4]['action'])==selection
        assert json.loads(saved[4]['result'])=={**result,'pending_work_after_action':PENDING_WORK}

    def test_selected_wait_retains_last_observed_credit(self):
        task,binding,context,runtime=self.setup_task()
        saved={};waits=[];receipts=[]
        async def wait(source,condition,index):
            waits.append((condition,index))
            return {'status':'completed','record_refs':[],'changed_record_refs':[]}
        task.workflow=SimpleNamespace(run_id='run',execution_binding=None,pending_work=lambda source:deepcopy(PENDING_WORK),
            journal=SimpleNamespace(row=lambda table,episode,index:saved.get(index),
                save=lambda table,row:saved.__setitem__(row['decision_index'],row),measure=lambda *args:nullcontext()),
            perform_selected_wait=wait,receive_native_outcome=lambda *args:None,
            receive_outcome=lambda source,selection,result,index:receipts.append(index),
            last_observed_credit=lambda source:1.25,
            source_credit_view=lambda *args:pytest.fail('A wait must not reproject progress'),
            controller_value=lambda source,index,credit:credit)
        selection={'kind':'wait','condition':{'kind':'controlled_wait'}}
        assert asyncio.run(task.execute(selection,8))==1.25
        assert asyncio.run(task.execute(selection,8))==1.25
        assert waits==[(selection['condition'],8)] and receipts==[8]

    def test_decision_state_retains_objective_credit_and_actual_outcome(self):
        task,binding,context,runtime=self.setup_task()
        previous={'status':'invalid','record_refs':[],'feedback':{'code':'requested_field_unavailable'}}
        task.last_outcome=previous;task.last_outcome_index=2;task.feedback=previous['feedback']
        journal=SimpleNamespace(row=lambda *args:None,elapsed_view=lambda *args:{'elapsed_seconds':7},
            db=SimpleNamespace(execute=lambda *args:SimpleNamespace(fetchone=lambda:None)))
        task.workflow=SimpleNamespace(run_id='run',inprocess_replay=None,execution_binding=None,journal=journal,
            store=SimpleNamespace(read_snapshot=nullcontext,get=lambda ref:None),
            working_state=lambda source:{'records':[]},local_outcome_preview=lambda outcome,**kwargs:deepcopy(outcome),
            source_credit_view=lambda source:{'credit':2.5},receipt_projection=lambda source:False,
            source_credit_binding=lambda source:{'kind':'monitoring_information'},pending_work=lambda source:[],
            delivery_status=lambda episode:[],controller_binding={},catalog=lambda *args,**kwargs:binding.catalog(context),
            knowledge=SimpleNamespace(context=lambda:{}),job_episode_options=lambda source:[],
            extra_report_sources=lambda source:{},specialist=lambda source:binding,binding_context=lambda source:context,
            tools=object(),action_schema=lambda source:{})
        shown=[];unit=object()
        async def call(state,schema):
            index=task.calls;task.calls+=1;shown.append(deepcopy(state))
            return {},index,state,schema
        task.call=call
        task.apply_response=lambda *args:unit
        view=SimpleNamespace(units_consumed=0,controller_state={},child_reports=(),model_inputs=lambda state,**kwargs:state)
        assert asyncio.run(task.next(view)) is unit
        assert shown[0]['goal']=={'objective':'Resolve exposed progress'}
        assert shown[0]['current_credit']==2.5
        assert shown[0]['last_local_outcome']==previous and shown[0]['feedback']==previous['feedback']
        assert shown[0]['monitor_assignment']==context.assignment
        assert shown[0]['monitor_goal']['target_handle']=='target'
        assert shown[0]['monitor_received_progress_refs']==[]
        task.last_outcome={'status':'completed','record_refs':[]};task.last_outcome_index=3;task.feedback=None
        assert asyncio.run(task.next(view)) is unit
        assert shown[1]['last_local_outcome']==task.last_outcome and shown[1]['feedback'] is None

    def test_scientific_reason_is_rejected_before_acquisition(self):
        task,binding,context,runtime=self.setup_task()
        effects=[]
        assert 'reason' not in binding.permitted_common_actions(context)
        assert binding.child_roles('monitor')==('monitor',)
        task.record_effect=lambda index,state:effects.append((index,state))
        task.workflow=SimpleNamespace(journal=SimpleNamespace(row=lambda *args:None),decision_exchanges=None,
            execution_binding=None,permits_common_action=lambda source,action:action in binding.permitted_common_actions(context),
            selected=lambda *args:pytest.fail('Rejected scientific reason acquired a unit'))
        schema=runtime._object({'selection':{'anyOf':[runtime._object({'kind':{'const':'tool'},
            'tool':{'const':'progress.observe'},'arguments':runtime._object({})})]}, 'report_update':runtime._object({})})
        assert task.apply_response({'selection':{'kind':'reason','commit':{}},'report_update':{}},0,{},schema) is None
        assert effects==[(0,'rejected')] and task.feedback['status']=='invalid'

    def test_fresh_monitor_decision_dispatch_preserves_original_input(self,monkeypatch):
        task,binding,context,runtime=self.setup_task()
        work_report=importlib.import_module(runtime.__package__+'.episode_work_report')
        monkeypatch.setattr(work_report,'completed_action_reports',lambda *args,**kwargs:{'actual_attempts':[]})
        saved=[];sent=[]
        response={'selection':{'kind':'tool','tool':'progress.observe','arguments':{}},'report_update':{}}
        async def complete(*args):
            sent.append(args)
            return deepcopy(response)
        task.workflow=SimpleNamespace(journal=SimpleNamespace(row=lambda *args:None,
            save=lambda table,row:saved.append((table,deepcopy(row))),measure=lambda *args:nullcontext()),
            contract_information_profile=lambda source:None,resource_context=lambda source:None,
            shared_information_context=lambda source:None,
            launch_instructions=SimpleNamespace(context=lambda:{},materialize=lambda supplied:None,instructions=''),
            available_child_roles=lambda source:(),episode_bindings=SimpleNamespace(initial_decision_context=lambda context:{}),
            binding_context=lambda source:context,specialist=lambda source:binding,is_job_source=lambda source:False,
            execution_expectations=None,resource_estimator=None,
            native_estimation_context=lambda *args:None,native_event_information=None,
            permits_common_action=lambda source,action:False,
            freeze_literature_numerical_contracts=lambda *args:None,decision_protocol=None,receipts=None,
            provider=SimpleNamespace(has_session=lambda *args:True,complete=complete),
            services=SimpleNamespace(instructions=importlib.import_module(runtime.__package__+'.runtime_prompt').instructions))
        schema=runtime._object({'selection':{'anyOf':[runtime._object({'kind':{'const':'tool'},
            'tool':{'const':'progress.observe'},'arguments':runtime._object({})})]},'report_update':runtime._object({})})
        state={'monitor_assignment':context.assignment,'current_credit':2.5,'visible_record_refs':[],'pending_work':[]}
        actual,index,shown,original_schema=asyncio.run(task.call(state,schema))
        assert actual==response and index==0 and original_schema==schema
        assert len(sent)==1 and sent[0][:3]==('monitor','REASONING',task.instructions(shown))
        assert shown['monitor_assignment']==context.assignment and shown['current_credit']==2.5
        assert shown['completed_action_reports']=={'actual_attempts':[]}
        assert json.loads(saved[-1][1]['response'])==response
