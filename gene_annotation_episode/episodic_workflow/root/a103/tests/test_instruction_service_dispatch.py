"""Actual private task/service method dispatch with explicit instruction-only ports.

These cases use actual classes, without constructing scientific work, Store or
native jobs. The controlled binding supplies only its fixed instruction text.
"""
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch
import pytest
PREFIX='gene_annotation_episode.episodic_workflow.root.a103'
HOMES=tuple(h+'/api_job_execution' for h in (
 'execution_job_submission','hpc_work_planning/execution_job_submission',
 'hpc_work_planning/hpc_allocation_execution/execution_job_submission',
 'scientific_process/execution_job_submission','scientific_process/hpc_work_planning/execution_job_submission',
 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission'))
def own(name):return import_module(PREFIX+'.'+name)
class OriginalInstructionFailure(Exception):pass
class ExplicitNoneSource(own('runtime').DecisionSource):
 instruction_composer=None
def source_for(cls):
 source=object.__new__(cls)
 binding=SimpleNamespace(replaces_default_instructions=True,instructions=lambda context:'Original fixed API instruction port.')
 source.path=(('launch_api','original-commission'),)
 source.workflow=SimpleNamespace(is_job_source=lambda source:False,specialist=lambda source:binding,
  binding_context=lambda source:object(),permits_common_action=lambda source,action:action=='wait',
  knowledge=SimpleNamespace(instructions=' Original knowledge.'),
  launch_instructions=SimpleNamespace(instructions=' Original launch instructions.'),
  native_event_information=object(),decision_protocol=None)
 source.workflow.services=own('episode_services').WorkflowServices(source.workflow)
 return source
def observe(home):
 cls=own(home.replace('/','.')+'.task').APIJobTask;source=source_for(cls)
 context={'tool_knowledge':{},'launch_instruction_library':{}}
 private=own(home.replace('/','.')+'.instructions').instructions
 original=own('runtime').DecisionSource.instructions
 calls=[];sentinel=object()
 def returned(actual,passed):
  calls.append({'same_source':actual is source,'same_context':passed is context});return sentinel
 source.workflow.services=SimpleNamespace(instructions=returned)
 assert original(source,context) is sentinel and calls==[{'same_source':True,'same_context':True}]
 calls.clear();result=source.instructions(context)
 custom_return={'same_result':result is sentinel,'calls':list(calls),'unexpected_value':None if result is sentinel else result}
 failure=OriginalInstructionFailure('original instruction callback failure');calls.clear()
 def failed(actual,passed):
  calls.append({'same_source':actual is source,'same_context':passed is context});raise failure
 source.workflow.services=SimpleNamespace(instructions=failed)
 try:original(source,context)
 except OriginalInstructionFailure as error:assert error is failure
 else:raise AssertionError('original service exception must propagate')
 assert calls==[{'same_source':True,'same_context':True}];calls.clear()
 try:
  unexpected=source.instructions(context)
  custom_failure={'same_exception':False,'calls':list(calls),'unexpected_value':unexpected}
 except OriginalInstructionFailure as error:
  custom_failure={'same_exception':error is failure,'calls':list(calls),'unexpected_value':None}
 source.workflow.services=own('episode_services').WorkflowServices(source.workflow)
 expected=own('runtime_prompt').instructions(source,context)
 actual=source.instructions(context)
 assert actual==expected==private(source,context)
 declared=getattr(type(source),'instruction_composer',None) is private
 selected=[]
 def tracked(actual,passed):
  selected.append({'same_source':actual is source,'same_context':passed is context});return private(actual,passed)
 with patch.object(cls,'instruction_composer',staticmethod(tracked),create=True):
  tracked_result=source.instructions(context)
 assert tracked_result==expected
 return {'home':home,'task_type':cls.__module__+'.'+cls.__qualname__,
  'custom_return':custom_return,'custom_exception':custom_failure,
  'default_composition':{'equal_original':actual==expected,'text':actual},
  'private_composer':{'declared_exact_function':declared,'calls':selected}}
def observe_fallback(explicit_none=False):
 cls=ExplicitNoneSource if explicit_none else own('runtime').DecisionSource
 source=source_for(cls);context={'tool_knowledge':{}}
 assert getattr(type(source),'instruction_composer',None) is None
 expected=own('runtime_prompt').instructions(source,context)
 observed=source.instructions(context)
 assert observed==expected
 return {'explicit_none':explicit_none,'same_original_text':True,'text':observed}
@pytest.mark.parametrize('home',HOMES,ids=HOMES)
@pytest.mark.parametrize('boundary',('custom_return','custom_exception','default_composition','private_composer'))
def test_private_task_preserves_original_instruction_service(home,boundary):
 result=observe(home)[boundary]
 if boundary=='custom_return':assert result=={'same_result':True,'calls':[{'same_source':True,'same_context':True}],'unexpected_value':None}
 elif boundary=='custom_exception':assert result=={'same_exception':True,'calls':[{'same_source':True,'same_context':True}],'unexpected_value':None}
 elif boundary=='default_composition':assert result['equal_original'] is True
 else:assert result=={'declared_exact_function':True,'calls':[{'same_source':True,'same_context':True}]}
@pytest.mark.parametrize('explicit_none',(False,True),ids=('absent-composer','explicit-none-composer'))
def test_nonparticipant_keeps_original_service_fallback(explicit_none):
 assert observe_fallback(explicit_none)['same_original_text'] is True
