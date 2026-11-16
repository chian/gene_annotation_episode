"""Private operational endpoint identity with actual saved counterparts and controlled ports."""
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

AXIS=__package__.rsplit('.tests',1)[0]
ROOT=Path(__file__).resolve().parents[1]
HOMES={}
for path in ROOT.rglob('episode.py'):
    if 'tests' in path.parts:continue
    text=path.read_text()
    if not any('class '+name+'(' in text for name in ('ScientificProcessEpisode','ExecutionEpisode','ResourceEpisode','MonitorEpisode')):continue
    module=import_module(AXIS+'.'+str(path.parent.relative_to(ROOT)).replace('/','.')+'.episode')
    cls=next(getattr(module,name) for name in ('ScientificProcessEpisode','ExecutionEpisode','ResourceEpisode','MonitorEpisode') if hasattr(module,name))
    HOMES[path.parent]=cls
CASES=[(str(parent.relative_to(ROOT)),str(child.relative_to(ROOT)),child_cls.roles[0])
    for parent in HOMES for child,child_cls in HOMES.items() if child.parent==parent]

@pytest.fixture(params=CASES)
def edge(request):
    parent,child,role=request.param
    binding=object.__new__(HOMES[ROOT/parent])
    binding.allowed_children=lambda *args:(role,)
    return parent,child,role,binding


def outgoing(edge):
    parent,child,role,binding=edge
    context=SimpleNamespace(role=binding.roles[0],scope={'subject_refs':['target']})
    source=SimpleNamespace(path=(('annotation','root'),(binding.roles[0],'parent')),
        scope=context.scope,episode_id='original-parent')
    selection={'kind':'episode_child','role':role,'scope':context.scope,
        'goal':'Improve the original execution outcome','purpose':'Return original qualified result',
        'assignment':{'original':'assignment'}}
    if role=='monitor':
        selection['assignment']={'version':'monitor_assignment_v1','target_handle':'original-target',
            'requested_fields':['execution_status'],'known_progress_refs':[],'permitted_committed_record_types':[]}
    calls=[]
    target=SimpleNamespace(binding_path=child,required_return_sources=lambda *args:(),
        prepare_assignment=lambda context,role,assignment,scope,key:
            calls.append((context,role,assignment,scope,key)) or {'admitted':'original'})
    schema={'type':'object','properties':{},'required':[],'additionalProperties':False}
    workflow=SimpleNamespace(run_id='original-run',store=SimpleNamespace(validate_scope=lambda scope,**kwargs:scope),
        expanded_contract_form=lambda *args:(schema,{'original':'declaration'}),
        episode_bindings=SimpleNamespace(for_child=lambda *args:target),binding_context=lambda source:context,
        child_initial_report_input=lambda *args:'{}',specialist=lambda source:binding,
        annotation_child_roles=None,services=SimpleNamespace(capabilities=lambda:()),
        launch_instructions=SimpleNamespace(materialize=lambda selected:None))
    return workflow,source,selection,context,target,calls,schema



def test_required_typed_result_is_checked_before_child_admission(edge):
    _,child,role,binding=edge
    workflow,source,selection,_,target,calls,_=outgoing(edge)
    target.required_return_sources=lambda *args:('original_qualified_result',)
    with pytest.raises(import_module(AXIS+'.domain').ContractError,match='child_return_requires_original_qualified_result'):
        binding.child_request_preparer_for_binding(role,child)(workflow,source,selection,7)
    assert calls==[]


def test_same_role_other_binding_cannot_enter_this_named_endpoint(edge):
    _,child,role,binding=edge
    workflow,source,selection,_,target,calls,_=outgoing(edge)
    target.binding_path='different_parent/different_child'
    with pytest.raises(ValueError,match='child_binding_path_conflict'):
        binding.child_request_preparer_for_binding(role,child)(workflow,source,selection,7)
    assert calls==[]



def test_original_hpc_handoff_requirement_precedes_native_assignment(edge):
    _,child,role,binding=edge
    if role not in {'launch','launch_hpc'}:
        pytest.skip('Original HPC handoff condition cannot apply to this fixed child role')
    workflow,source,selection,_,_,calls,_=outgoing(edge)
    source.path=(('hpc','original-planner'),) if role=='launch' else (
        ('hpc','original-planner'),('launch','original-parent'))
    with pytest.raises(import_module(AXIS+'.domain').ContractError,
            match='hpc_launch_requires_original_handoff_fact_in_return_form'):
        binding.child_request_preparer_for_binding(role,child)(workflow,source,selection,7)
    assert calls==[]
