"""Instruction-only actual private classes: explicit ports, no constructor claim."""
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch
import pytest
AXES=('a102','a103')
MONITORS=tuple(p+'execution_progress_assessment' for p in ('','gene_context_evidence/','hpc_work_planning/','hpc_work_planning/hpc_allocation_execution/','gene_context_evidence/hpc_work_planning/','gene_context_evidence/hpc_work_planning/hpc_allocation_execution/'))
WORK=('hpc_work_planning','gene_context_evidence/hpc_work_planning','hpc_work_planning/hpc_allocation_execution','gene_context_evidence/hpc_work_planning/hpc_allocation_execution')
PREDICTIONS=('hpc_work_planning/hpc_resource_prediction','gene_context_evidence/hpc_work_planning/hpc_resource_prediction')
HOMES=MONITORS+WORK+PREDICTIONS
MODES=('ordinary','exchange')
BOUNDARIES=('custom_return','custom_exception','subclass_return','subclass_exception','default_composition','private_composer','instance_shadow','delegation')
def own(axis,name):return import_module('gene_annotation_episode.episodic_workflow.root.'+axis+'.'+name)
class CallbackFailure(Exception):pass

def source_for(axis,cls,mode):
 source=object.__new__(cls);binding_context=object()
 binding=SimpleNamespace(replaces_default_instructions=True,instructions=lambda context:'Original fixed instruction port.')
 source.path=(('instruction_fixture','original-commission'),)
 source.workflow=SimpleNamespace(is_job_source=lambda source:False,specialist=lambda source:binding,
  binding_context=lambda source:binding_context,permits_common_action=lambda source,action:action=='wait',
  knowledge=SimpleNamespace(instructions=' Original knowledge.'),launch_instructions=SimpleNamespace(instructions=' Original launch instructions.'),
  native_event_information=object(),decision_protocol='decision_exchange_v1' if mode=='exchange' else None)
 source.workflow.services=own(axis,'episode_services').WorkflowServices(source.workflow)
 return source

def observe(axis,home,mode):
 name='ProgressMonitoringTask' if home in MONITORS else 'HPCWorkTask' if home in WORK else 'ResourcePredictionTask'
 cls=getattr(own(axis,home.replace('/','.')+'.task'),name);source=source_for(axis,cls,mode)
 decision_name='MonitorTaskDecision' if home in MONITORS else 'HPCWorkTaskDecision' if home in WORK else 'PredictionTaskDecision'
 decision=getattr(own(axis,home.replace('/','.')+'.task_decision'),decision_name)
 assert cls.instructions is decision.instructions
 context={'tool_knowledge':{},'launch_instruction_library':{}}
 private=own(axis,home.replace('/','.')+'.task_instructions').instructions
 original=own(axis,'runtime').DecisionSource.instructions;service_cls=own(axis,'episode_services').WorkflowServices
 expected=private(source,context);calls=[];sentinel=object();result={}
 def returned(actual,passed):
  calls.append({'same_source':actual is source,'same_context':passed is context});return sentinel
 failure=CallbackFailure('original callback exception')
 def failed(actual,passed):
  calls.append({'same_source':actual is source,'same_context':passed is context});raise failure
 class CustomServices(service_cls):
  def instructions(self,actual,passed):return self.callback(actual,passed)
 for kind in ('custom_return','custom_exception','subclass_return','subclass_exception'):
  callback=failed if kind.endswith('exception') else returned
  if kind.startswith('subclass'):
   service=CustomServices(source.workflow);service.callback=callback
  else:service=SimpleNamespace(instructions=callback)
  source.workflow.services=service;calls.clear()
  if kind.endswith('exception'):
   try:original(source,context)
   except CallbackFailure as error:assert error is failure
   else:raise AssertionError('original exception lost')
  else:assert original(source,context) is sentinel
  assert calls==[{'same_source':True,'same_context':True}];calls.clear()
  try:
   value=source.instructions(context)
   result[kind]={'identity':value is sentinel if kind.endswith('return') else False,'calls':list(calls),'unexpected_value':None if value is sentinel else value}
  except CallbackFailure as error:
   assert kind.endswith('exception');result[kind]={'identity':error is failure,'calls':list(calls),'unexpected_value':None}
 source.workflow.services=service_cls(source.workflow)
 # Generic text is intentionally not the monitor composer oracle.
 value=source.instructions(context);assert value==expected
 result['default_composition']={'same_private_text':True,'text':value}
 declared=getattr(type(source),'instruction_composer',None) is private;calls.clear()
 def tracked(actual,passed):
  calls.append({'same_source':actual is source,'same_context':passed is context});return private(actual,passed)
 with patch.object(cls,'instruction_composer',staticmethod(tracked),create=True):
  assert source.instructions(context)==expected
 result['private_composer']={'declared_exact_function':declared,'calls':list(calls)}
 calls.clear()
 def forbidden(*args):raise AssertionError('instance composer must not select the default service composer')
 source.instruction_composer=forbidden
 with patch.object(cls,'instruction_composer',staticmethod(tracked),create=True):
  assert source.instructions(context)==expected
 del source.instruction_composer
 result['instance_shadow']={'private_text_preserved':True,'calls':list(calls)}
 calls.clear()
 def delegate(actual,passed):
  calls.append({'same_source':actual is source,'same_context':passed is context})
  return service_cls.instructions(service_cls(source.workflow),actual,passed)
 source.workflow.services=SimpleNamespace(instructions=delegate)
 # Baseline delegates to private composition only when the caller enters service;
 # actual source still bypasses this callback before the proposed change.
 value=source.instructions(context);assert value==expected
 result['delegation']={'private_text_preserved':True,'calls':list(calls)}
 return {'axis':axis,'home':home,'mode':mode,'task_type':cls.__module__+'.'+cls.__qualname__,**result}

def observe_fallback(axis,mode,explicit_none):
 base=own(axis,'runtime').DecisionSource
 class NoneSource(base):instruction_composer=None
 cls=NoneSource if explicit_none else base;source=source_for(axis,cls,mode);context={'tool_knowledge':{}}
 assert getattr(type(source),'instruction_composer',None) is None
 expected=own(axis,'runtime_prompt').instructions(source,context)
 assert source.instructions(context)==expected
 return {'axis':axis,'mode':mode,'explicit_none':explicit_none,'same_original_text':True,'text':expected}

@pytest.mark.parametrize('axis,home,mode,boundary',[(a,h,m,b) for a in AXES for h in HOMES for m in MODES for b in BOUNDARIES],ids=[a+';home='+h+';mode='+m+';boundary='+b for a in AXES for h in HOMES for m in MODES for b in BOUNDARIES])
def test_existing_task_service_callback(axis,home,mode,boundary):
 result=observe(axis,home,mode)[boundary];calls=[{'same_source':True,'same_context':True}]
 if boundary in ('custom_return','custom_exception','subclass_return','subclass_exception'):assert result=={'identity':True,'calls':calls,'unexpected_value':None}
 elif boundary=='default_composition':assert result['same_private_text'] is True
 elif boundary=='private_composer':assert result=={'declared_exact_function':True,'calls':calls}
 else:assert result=={'private_text_preserved':True,'calls':calls}

@pytest.mark.parametrize('axis,mode,explicit_none',[(a,m,n) for a in AXES for m in MODES for n in (False,True)],ids=[a+';mode='+m+';composer='+('none' if n else 'absent') for a in AXES for m in MODES for n in (False,True)])
def test_generic_source_original_fallback(axis,mode,explicit_none):
 assert observe_fallback(axis,mode,explicit_none)['same_original_text'] is True
