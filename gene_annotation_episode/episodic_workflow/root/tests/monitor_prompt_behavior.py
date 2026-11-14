"""Monitor-owned instructions and explicit rendering with controlled providers."""
import asyncio
import importlib
from types import SimpleNamespace
import pytest


def axis_of(home):
    return home.split('.root.')[0]+'.root.'+home.split('.root.')[1].split('.')[0]


def renderer_state():
    return {'monitor_assignment':{'version':'monitor_assignment_v1'},
        'requested_form':{'properties':{'answer':{'x-source':'requested_result'}}},
        'available_report_facts':{'requested_result':{'meaning':'Requested original meaning'},
            'monitoring_progress_refs':{'meaning':'Actual delivered progress'},
            'unrequested_result':{'meaning':'Unrequested scientific definition'}}}


class MonitorPromptChecks:
    """Instruction checks shared by every axis; each home's test class adds its own provider and renderer checks."""
    def setup(self,*,protocol=None,wait=False,native=False):
        module=importlib.import_module(self.home+'.episode')
        axis=axis_of(self.home)
        runtime_prompt=importlib.import_module(axis+'.runtime_prompt')
        # The axis's actual instruction dispatch: it selects the task's private composer.
        services_type=importlib.import_module(axis+'.episode_services').WorkflowServices
        binding=module.MonitorEpisode(object())
        task=object.__new__(binding.decision_source_type)
        task.episode_id='monitor';task.path=(('monitor','original'),)
        context=SimpleNamespace(role='monitor')
        task.workflow=SimpleNamespace(specialist=lambda source:binding,binding_context=lambda source:context,
            is_job_source=lambda source:False,permits_common_action=lambda source,action:wait if action=='wait' else False,
            native_event_information=object() if native else None,decision_protocol=protocol,
            knowledge=SimpleNamespace(instructions='\nOriginal tool-library guidance.'),
            launch_instructions=SimpleNamespace(instructions='\nOriginal launch-library guidance.'),
            services=SimpleNamespace(instructions=lambda source,context:services_type.instructions(None,source,context)))
        return task,binding,context,runtime_prompt

    @pytest.mark.parametrize('protocol',[None,'decision_exchange_v1'])
    def test_instructions_follow_monitor_goal_and_original_report_contract(self,protocol):
        task,binding,context,original=self.setup(protocol=protocol)
        text=task.instructions({'tool_knowledge':{},'launch_instruction_library':{}})
        assert text.startswith(binding.instructions(context))
        assert 'one typed reasoning commitment' not in text
        assert 'same_source_claim_as_ref' not in text
        assert 'assessment.investigation_finding' not in text
        start=original.INSTRUCTIONS.index('A commissioned child returns ONLY')
        end=original.INSTRUCTIONS.index('On a fresh provider conversation,')
        assert original.INSTRUCTIONS[start:end] in text
        start=original.INSTRUCTIONS.index('resource_tool_estimates, when supplied,')
        end=original.INSTRUCTIONS.index('Define local rows with a bare alias,')
        assert original.INSTRUCTIONS[start:end] in text
        start=original.INSTRUCTIONS.index('current_evidence_vector contains')
        end=original.INSTRUCTIONS.index('When working_state.record_view')
        assert original.INSTRUCTIONS[start:end] in text
        assert 'Do not execute native provider tools. The host executes your selected action.' in text
        assert 'Original tool-library guidance.' in text and 'Original launch-library guidance.' in text
        assert ('Use request_context exchanges' in text)==(protocol=='decision_exchange_v1')
        assert ('On a fresh provider conversation,' in text)==(protocol is None)

    @pytest.mark.parametrize('wait,native',[(False,False),(False,True),(True,False),(True,True)])
    def test_wait_instructions_preserve_actual_capability(self,wait,native):
        task,_,_,_=self.setup(wait=wait,native=native)
        text=task.instructions({})
        assert ('A pending_child_ handle' in text)==wait
        assert ('The separate native_event_targets input' in text)==(wait and native)
        assert 'pending_child_delivery' in text


class CompleteDecisionChecks:
    """Monitors whose task exposes complete_decision(instructions, context, schema)."""
    def test_declared_renderer_reaches_capable_provider(self):
        task,binding,_,_=self.setup()
        calls=[]
        async def complete(*args,**kwargs):
            calls.append((args,kwargs))
            renderer=kwargs['prompt_renderer']
            return {'wire':renderer(args[3],args[2])}
        task.workflow.provider=SimpleNamespace(complete_with_presentation=complete,
            complete=lambda *args:pytest.fail('Private presentation was not sent'))
        state={'monitor_assignment':{'version':'monitor_assignment_v1','target_handle':'target'},'current_credit':0}
        result=asyncio.run(task.complete_decision('monitor instructions',state,{'type':'object'}))
        assert calls[0][1]['prompt_renderer'] is binding.decision_prompt_renderer
        assert calls[0][0]==('monitor','REASONING','monitor instructions',state,{'type':'object'})
        assert 'Actual monitor state' in result['wire'] and 'target' in result['wire']

    def test_legacy_provider_keeps_original_structured_arguments(self):
        task,_,_,_=self.setup()
        calls=[]
        async def complete(*args):
            calls.append(args);return {'original':'response'}
        task.workflow.provider=SimpleNamespace(complete=complete)
        state={'monitor_assignment':{'version':'monitor_assignment_v1'}};schema={'type':'object'}
        assert asyncio.run(task.complete_decision('monitor instructions',state,schema))=={'original':'response'}
        assert calls==[('monitor','REASONING','monitor instructions',state,schema)]


class DecisionCompletionChecks:
    """Monitors whose task exposes decision_completion(), returning the five-operand provider call."""
    def test_legacy_provider_keeps_original_structured_arguments(self):
        task,_,_,_=self.setup()
        calls=[]
        async def complete(*args):
            calls.append(args);return {'original':'response'}
        task.workflow.provider=SimpleNamespace(complete=complete)
        state={'monitor_assignment':{'version':'monitor_assignment_v1'}};schema={'type':'object'}
        complete_private_decision=task.decision_completion()
        assert asyncio.run(complete_private_decision('monitor','REASONING','monitor instructions',state,schema))=={'original':'response'}
        assert calls==[('monitor','REASONING','monitor instructions',state,schema)]


class DirectRendererChecks:
    """Monitors whose binding renderer is the monitor prompt renderer itself."""
    def test_renderer_retains_requested_facts_without_unrequested_science(self):
        _,binding,_,_=self.setup()
        state=renderer_state()
        text=binding.decision_prompt_renderer(state,'Original monitor instructions',lookup_results=[{'status':'unavailable'}])
        assert 'Requested original meaning' in text and 'Actual delivered progress' in text
        assert 'Unrequested scientific definition' not in text
        assert 'unavailable' in text


class SelectedRendererChecks:
    """Monitors whose binding renderer is a context presenter that selects the monitor prompt renderer."""
    def test_renderer_retains_requested_facts_without_unrequested_science(self):
        _,binding,_,_=self.setup()
        state=renderer_state()
        assert binding.decision_prompt_renderer.presentation_protocol=='episode_context_presentation_v1'
        _,renderer_for=importlib.import_module(self.home+'.presentation_selection').task_presentation_selection()
        renderer=renderer_for(state)
        assert renderer is importlib.import_module(axis_of(self.home)+'.library.monitor_prompt').render_monitor_prompt
        text=renderer(state,'Original monitor instructions',lookup_results=[{'status':'unavailable'}])
        assert 'Requested original meaning' in text and 'Actual delivered progress' in text
        assert 'Unrequested scientific definition' not in text
        assert 'unavailable' in text


class MonitorPromptBehaviorChecks(MonitorPromptChecks,CompleteDecisionChecks,DirectRendererChecks):
    """A102, A103, A107 and A110 monitor homes."""


class MonitorDecisionCompletionPromptChecks(MonitorPromptChecks,DecisionCompletionChecks,DirectRendererChecks):
    """A101 and A106 monitor homes."""


class MonitorContextPresenterPromptChecks(MonitorPromptChecks,DecisionCompletionChecks,SelectedRendererChecks):
    """A104 monitor homes."""
