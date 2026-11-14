"""Operational role boundaries with controlled API/native ports and original outcomes."""
import asyncio
from copy import deepcopy
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

PACKAGE='gene_annotation_episode.episodic_workflow.root.a101'
ROOT=Path(__file__).resolve().parents[1]
HOMES=sorted(str(p.parent.relative_to(ROOT)) for p in ROOT.rglob('episode.py')
    if 'tests' not in p.parts and ('class ExecutionEpisode(' in p.read_text() or 'class ResourceEpisode(' in p.read_text()))


@pytest.fixture(params=HOMES)
def binding(request):
    module=importlib.import_module(PACKAGE+'.'+request.param.replace('/','.')+'.episode')
    cls=getattr(module,'ExecutionEpisode',None) or module.ResourceEpisode
    value=object.__new__(cls)
    value.services=SimpleNamespace(capabilities=lambda:[],annotation_task_required=lambda:True)
    value.private_yield_binding=False
    value._contract_information_profile=None
    value.adapters={}
    value._validate_request=lambda assignment: {'version':'api_service_assignment_v1','service':'fixture'}
    value._target=lambda context: {'resource_kind':'api','assignment':{'version':'api_service_assignment_v1'}}
    value._delegate=lambda context: SimpleNamespace(instructions=lambda context:'Original delegated instructions')
    value._practical_context=lambda context:context
    return value


def test_declared_role_preserves_goal_and_action_interfaces(binding):
    role,=binding.roles
    context=SimpleNamespace(role=role,scope={},assignment={},path=((role,'fixture'),))
    assert binding.instructions(context)
    assert set(binding.permitted_common_actions(context)) <= {'tool','reason','child','wait','redeliver_report'}
    assert isinstance(binding.child_roles(role),tuple)
    if hasattr(binding,'yield_controller'):
        with pytest.raises(ValueError,match='execution_private_yield_binding_not_enabled'):
            binding.yield_controller(context,0,'epoch')


def test_actual_outgoing_reference_contract_preserves_scientific_parent(binding):
    if type(binding).__name__!='ExecutionEpisode':
        pytest.skip('Not applicable to this predefined role')
    parent=SimpleNamespace(path=(('scientific_process','parent'),))
    role,=binding.roles
    expected=('execution_handoff_refs',) if role=='launch' else ('execution_result_refs',) if role=='results' else ()
    assert binding.required_return_sources(parent,role)==expected
    assert binding.required_return_sources(None,role)==()


@pytest.mark.parametrize('status',['completed','partial','invalid','failed','unavailable'])
def test_selected_delegated_operation_keeps_actual_outcome_and_key(binding,status):
    role,=binding.roles
    if role=='launch':
        pytest.skip('Not applicable to this predefined role')
    captured=[]
    async def delegated(context,name,arguments,key):
        captured.append((context,name,deepcopy(arguments),key))
        return {'status':status,'record_refs':[],'changed_record_refs':[],'result':{'original':True}}
    context=SimpleNamespace(role=role,scope={'original':'scope'},assignment={})
    adapter=SimpleNamespace(execute=delegated)
    binding.api_execution=adapter
    binding._adapter=lambda assignment:adapter
    binding._delegate=lambda context:adapter
    binding._practical_context=lambda context:context
    binding._check_parent_inputs=lambda context:None
    binding.catalog=lambda context:[{'name':'fixture.original','input_schema':{'type':'object','properties':{},'additionalProperties':False}}]
    binding._target=lambda context:{'resource_kind':'api','assignment':{}}
    inactive=SimpleNamespace(applies=lambda context:False)
    binding.local_file_sources=inactive
    binding.native_blast_masking_results=inactive
    binding.native_blast_utility_results=inactive
    result=asyncio.run(binding.execute(context,'fixture.original',{},'original-key'))
    assert result=={'status':status,'record_refs':[],'changed_record_refs':[],'result':{'original':True}}
    assert captured==[(context,'fixture.original',{},'original-key')]


def test_launch_invalid_operation_keeps_original_failure_boundary(binding):
    role,=binding.roles
    if role!='launch':
        pytest.skip('Not applicable to this predefined role')
    context=SimpleNamespace(role=role,scope={},assignment={},path=((role,'fixture'),))
    binding.catalog=lambda context:[]
    if type(binding).__name__=='ResourceEpisode':
        with pytest.raises(ValueError,match='tool_not_owned_by_resource_role'):
            asyncio.run(binding.execute(context,'unavailable',{},'original-key'))
    else:
        binding.local_file_sources=SimpleNamespace(applies=lambda context:False)
        result=asyncio.run(binding.execute(context,'unavailable',{},'original-key'))
        assert result['status']=='invalid'
        assert result['feedback']['code']=='execution_operation_not_available'
