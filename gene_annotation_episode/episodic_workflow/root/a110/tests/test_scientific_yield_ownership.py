"""Own scientific projector and original yield guard/constructor preservation.

Library admission is a controlled port; actual private credit selection,
original finding-progress class, configuration and numerical constructors run.
No fitting workload, scientific acquisition, or autonomous iteration runs.
"""
from __future__ import annotations
from copy import deepcopy
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
PREFIX='gene_annotation_episode.episodic_workflow.root.a110'
def module(name):return importlib.import_module(PREFIX+'.'+name)
constants=module('scientific_process.scientific_assignment_contracts')
FIXTURE=json.loads((Path(__file__).parent/'fixtures/organization_original/scientific_yield_method.json').read_text())
def original_callback():
    namespace=dict(vars(module('scientific_process.yield_estimator')))
    exec(compile(FIXTURE['yield_controller'],'<original-own-axis-scientific-yield>','exec'),namespace)
    return namespace['yield_controller']
def setup(kind='accumulation',*,parameters=None,cutoff=0.125,declared=True):
    projector=module('scientific_process.task_projector').original_task_projector({})
    assert type(projector) is module('investigation_progress').ScientificFindingProgress
    assert projector.policy.finding_unit==1 and projector.yield_method=='accumulation'
    task=constants.AXIS+':'+projector.as_record()['kind']
    declaration={'kind':kind,'cutoff':cutoff,'parameters':{'uncertainty_alpha':0.05} if parameters is None else parameters,'credit_definition':projector.as_record()}
    library=SimpleNamespace(as_record=lambda:{},headers=lambda:[],resolve=lambda reference:{'entry_version':constants.INSTRUCTION_VERSION})
    binding=module('scientific_process.episode').ScientificProcessEpisode(SimpleNamespace(),library=library,tool_library=library,child_roles=('scientific_process',),yield_bindings={task:declaration} if declared else None)
    selection={'version':constants.SELECTION_VERSION,'evidence_axis':{'option_id':constants.AXIS}}
    binding._original_selection=lambda context:selection
    context=SimpleNamespace(role=constants.ROLE,assignment={'proposed_annotation_ref':'hypothesis_controlled','context':{}})
    actual=binding.credit_projector(context)
    assert type(actual) is type(projector) and actual.as_record()==projector.as_record()
    return binding,context,task
@pytest.mark.parametrize('initial_credit',(0,2.5,-0.25))
def test_actual_accumulation_controller_preserves_original_identity_and_settings(initial_credit):
    compared=[]
    for old in (True,False):
        binding,context,task=setup()
        callback=original_callback() if old else type(binding).yield_controller
        controller=callback(binding,context,initial_credit,'original-epoch')
        assert type(controller) is module('numerical').YieldController
        compared.append((controller.epoch,controller.initial_credit,controller.cost,controller.settings.as_record(),controller.estimator.scores))
    assert compared[0]==compared[1]
@pytest.mark.parametrize('kind',('bounded_quality','completion'))
def test_original_constructor_accepts_other_declarations_but_private_projector_rejects(kind):
    binding,context,task=setup(kind)
    assert binding._yield_bindings[task]['kind']==kind
    for callback in (original_callback(),type(binding).yield_controller):
        with pytest.raises(constants.ContractError) as caught:callback(binding,context,0,'original-epoch')
        assert str(caught.value)=='scientific_yield_method_credit_mismatch:'+task
@pytest.mark.parametrize('failure',('role','missing_task','credit_definition','missing_annotation','invalid_task_context'))
def test_original_private_admission_failures_remain_exact(failure):
    observed=[]
    for old in (True,False):
        binding,context,task=setup()
        if failure=='role':context.role='literature'
        elif failure=='missing_task':binding._yield_bindings={}
        elif failure=='credit_definition':binding._yield_bindings[task]['credit_definition']['policy']['finding_unit']=7
        elif failure=='missing_annotation':context.assignment.pop('proposed_annotation_ref')
        elif failure=='invalid_task_context':context.assignment['context']={'a110_task':{'name':'unrecognized'}}
        callback=original_callback() if old else type(binding).yield_controller
        with pytest.raises(constants.ContractError) as caught:callback(binding,context,0,'original-epoch')
        observed.append((type(caught.value),str(caught.value)))
    assert observed[0]==observed[1]
@pytest.mark.parametrize('kind',('accumulation','bounded_quality','completion'))
def test_original_configuration_still_validates_numerical_operands(kind):
    with pytest.raises(constants.ContractError):setup(kind,parameters={'uncertainty_alpha':-1})
    with pytest.raises(constants.ContractError):setup(kind,cutoff=-1)
def test_original_absent_private_declaration_keeps_legacy_return():
    binding,context,_=setup(declared=False)
    assert original_callback()(binding,context,0,'original-epoch') is None
    assert binding.yield_controller(context,0,'original-epoch') is None
