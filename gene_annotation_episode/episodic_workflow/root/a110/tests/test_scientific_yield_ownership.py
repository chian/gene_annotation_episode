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
@pytest.mark.parametrize('kind',('accumulation','bounded_quality','completion'))
def test_original_configuration_still_validates_numerical_operands(kind):
    with pytest.raises(constants.ContractError):setup(kind,parameters={'uncertainty_alpha':-1})
    with pytest.raises(constants.ContractError):setup(kind,cutoff=-1)
