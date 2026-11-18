"""Private scientific task connections with explicit controlled operation ports.

Actual libraries, binding, assignment and admission are supplied by the existing
required fixture. Unit-level task state/journal ports are controlled; these tests
do not prove autonomous science or complete saved-workflow restoration.
"""
import asyncio
from contextlib import nullcontext
from copy import deepcopy
import importlib
import json
from types import SimpleNamespace

import pytest
from gene_annotation_episode.episodic_workflow.root.tests.scientific_head_boundaries import ScientificHeadBoundaryChecks

AXIS = 'a107'

class TestPrivateScientificHead(ScientificHeadBoundaryChecks):
    axis = AXIS

    def task(self, scientific):
        task_type = self.module('partner_presence_evidence.task').ScientificTask
        task = object.__new__(task_type)
        task.path = scientific.context.path; task.scope = scientific.context.scope
        task.episode_id = scientific.context.episode_id; task.calls = 0
        task._execution_context = task._delivery_resolution_ref = None
        task._selection_view = None; task.last_outcome = task.last_outcome_index = task.feedback = None
        task.report_values = {'status': 'unresolved'}; task.report_basis = []
        task.interpret_schema = scientific.form; task.checkpoint = lambda: None
        task.request = SimpleNamespace(goal=SimpleNamespace(as_record=lambda: {'objective': scientific.invocation['objective']}),
            message=SimpleNamespace(as_record=lambda: scientific.request['message']),
            report_contract=SimpleNamespace(schema=scientific.form, decision=scientific.invocation['purpose']))
        return task

    @pytest.mark.parametrize('status', ['completed', 'partial', 'invalid', 'failed', 'unavailable'])
    def test_actual_binding_outcome_reaches_task_credit_once_and_replays(self, scientific, status):
        task = self.task(scientific); saved = {}; receipts = []; credits = []
        scientific.outcome['status'] = status
        async def execute(source, name, arguments, **kw):
            return await scientific.binding.execute(scientific.context, name, arguments, kw['operation_key'])
        async def score(source, index, result):
            assert not hasattr(scientific.binding, 'automatic_score_judgments')
            return result
        def credit(source):
            credits.append(source.episode_id)
            return scientific.binding.credit_view(scientific.context, None)
        task.workflow = SimpleNamespace(run_id=scientific.context.run_id, execution_binding=None,
            pending_work=lambda source: [],
            partner_presence_evidence_binding=scientific.binding, binding_context=lambda source: scientific.context,
            journal=SimpleNamespace(row=lambda table, episode, index: saved.get(index),
                save=lambda table, row: saved.__setitem__(row['decision_index'], deepcopy(row)), measure=lambda *args: nullcontext()),
            execute=execute, receive_native_outcome=lambda *args: None,
            receive_outcome=lambda source, selection, result, index: receipts.append((index, result['status'])),
            automatic_score_updates=score, source_credit_view=credit, controller_value=lambda source,index,value: (index,value))
        selection = {'kind': 'tool', 'tool': 'fixture.inspect', 'arguments': {'record': scientific.target}}
        assert asyncio.run(task.execute(selection, 3)) == (3, 0)
        first = deepcopy(saved)
        assert asyncio.run(task.execute(selection, 3)) == (3, 0)
        assert first == saved and len(scientific.calls) == 1
        assert receipts == [(3,status)] and credits == [task.episode_id]
        assert json.loads(saved[3]['action']) == selection
        assert json.loads(saved[3]['result']) == {**scientific.outcome, 'pending_work_after_action': []}

    def test_next_revisits_actual_outcome_with_same_goal_and_progress_definition(self, scientific):
        task = self.task(scientific); seen = []; units = [object(), object()]
        scientific.services.workflow = SimpleNamespace(receipts=None, store=scientific.store)
        task.workflow = SimpleNamespace(run_id=scientific.context.run_id, inprocess_replay=None, execution_binding=None,
            journal=SimpleNamespace(row=lambda *args: None, elapsed_view=lambda *args: {},
                db=SimpleNamespace(execute=lambda *args: SimpleNamespace(fetchone=lambda: None))),
            store=SimpleNamespace(read_snapshot=nullcontext, get=lambda ref: None),
            working_state=lambda source: {'subjects': [], 'scope': scientific.context.scope},
            local_outcome_preview=lambda outcome, **kw: deepcopy(outcome),
            source_credit_view=lambda source: scientific.binding.credit_view(scientific.context, None),
            source_credit_binding=lambda source: {'kind': 'whole_axis_findings'}, receipt_projection=lambda source: False,
            pending_work=lambda source: [], delivery_status=lambda episode: [], controller_binding={},
            catalog=lambda scope, **kw: scientific.binding.catalog(scientific.context),
            knowledge=SimpleNamespace(context=lambda: {}), job_episode_options=lambda source: [], extra_report_sources=lambda source: {},
            is_scientific_source=lambda source: False, specialist=lambda source: scientific.binding,
            binding_context=lambda source: scientific.context, tools=object(), action_schema=lambda source: {})
        async def call(context, schema):
            index=task.calls; task.calls += 1; seen.append(deepcopy(self.module('communication').plain(context))); return {},index,context,schema
        task.call=call; task.apply_response=lambda response,index,context,schema: units[index]
        view=SimpleNamespace(units_consumed=0, child_reports=[], controller_state={}, model_inputs=lambda value,**kw:value)
        assert asyncio.run(task.next(view)) is units[0]
        task.last_outcome={'status':'unavailable','record_refs':[],'feedback':{'code':'original_missing_operand'}}
        task.last_outcome_index=0;task.feedback=task.last_outcome['feedback']
        assert asyncio.run(task.next(view)) is units[1]
        assert seen[0]['goal'] == seen[1]['goal'] == {'objective': scientific.invocation['objective']}
        assert seen[0]['credit_binding'] == seen[1]['credit_binding'] == {'kind':'whole_axis_findings'}
        assert seen[1]['last_local_outcome'] == task.last_outcome
        assert seen[1]['current_credit'] == 0 and seen[1]['current_report_update'] == {'status':'unresolved'}

    def test_custom_instruction_service_precedes_private_default(self, scientific):
        task=self.task(scientific); calls=[]
        task.workflow=SimpleNamespace(services=SimpleNamespace(instructions=lambda source, context: calls.append((source,context)) or 'custom supplied instructions'))
        context={'original':'context'}
        assert task.instructions(context)=='custom supplied instructions'
        assert calls==[(task,context)]

    def test_default_service_selects_the_concrete_task_composer(self,scientific,monkeypatch):
        task=self.task(scientific);calls=[];workflow=SimpleNamespace()
        def composer(source,context):calls.append((source,context));return 'concrete private default'
        monkeypatch.setattr(type(task),'instruction_composer',staticmethod(composer))
        task.workflow=workflow;context={'original':'input'}
        service=self.module('episode_services').WorkflowServices(workflow)
        assert service.instructions(task,context)=='concrete private default'
        assert calls==[(task,context)]

    @pytest.mark.parametrize('published', [True,False])
    @pytest.mark.parametrize('protocol', [None,'decision_exchange_v1'])
    @pytest.mark.parametrize('wait,native', [(False,False),(True,False),(True,True)])
    def test_default_composer_preserves_publication_and_actual_wait_settings(self, scientific,published,protocol,wait,native):
        task=self.task(scientific); original=self.module('runtime_prompt')
        binding=SimpleNamespace(replaces_default_instructions=published, instructions=lambda context:'private scientific guidance')
        workflow=SimpleNamespace(specialist=lambda source:binding,binding_context=lambda source:scientific.context,
            is_job_source=lambda source:False, permits_common_action=lambda source,action:wait if action=='wait' else action=='reason',
            native_event_information=object() if native else None,decision_protocol=protocol,
            knowledge=SimpleNamespace(instructions='\nselected tool instructions'),launch_instructions=SimpleNamespace(instructions='\nselected launch instructions'))
        task.workflow=workflow; context={'tool_knowledge':{},'launch_instruction_library':{}}
        expected=original.instructions(task,context)
        assert type(task).instruction_composer(task,context)==expected
        service=self.module('episode_services').WorkflowServices(workflow)
        assert service.instructions(task,context)==expected
        assert ('A pending_child_ handle' in expected)==wait
        assert ('The separate native_event_targets input' in expected)==(wait and native)

    def ordinary_state(self):
        scope={'subject_refs':['subject_fixture']}
        return {'goal':{'objective':'Retain the actual unresolved question'},'scope':scope,
            'working_state':{'subjects':[],'scope':scope},'tools':[],
            'requested_form':None,'controller':{},'current_credit':0,'current_report_update':{},
            'last_local_outcome':{'status':'unavailable','feedback':{'code':'no_controlled_measurement'},'record_refs':[]},
            'feedback':{'status':'unavailable','detail':'Target correspondence remains unresolved.'}}


    def test_declared_renderer_and_legacy_provider_receive_exact_original_operands(self,scientific):
        task=self.task(scientific);calls=[];state=self.ordinary_state();schema={'type':'object'}
        async def complete(*args,**kwargs):calls.append((args,kwargs));return {'status':'unresolved'}
        # Real original ModelConnection methods and identity guards remain;
        # only the serial worker-operation port is controlled, so no model runs.
        provider=object.__new__(self.module('providers').ModelConnection)
        provider.worker_lock=asyncio.Lock();provider._complete_serial=complete
        task.workflow=SimpleNamespace(provider=provider,specialist=lambda source:scientific.binding)
        operands=(task.episode_id,'REASONING','instructions',state,schema)
        assert asyncio.run(task.decision_completion()(*operands))=={'status':'unresolved'}
        assert calls==[(operands,{'prompt_renderer':scientific.binding.decision_prompt_renderer})]
        calls.clear();task.workflow.provider=SimpleNamespace(complete=complete,complete_with_presentation=complete)
        selected=task.decision_completion()
        def changed(*args,**kwargs):raise AssertionError('captured original complete was replaced')
        task.workflow.provider.complete=changed
        assert asyncio.run(selected(*operands))=={'status':'unresolved'}
        assert calls==[(operands,{})]


