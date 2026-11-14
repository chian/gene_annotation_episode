"""Original A106 execution contracts admit only their actual API native child."""
from copy import deepcopy
from types import SimpleNamespace
import pytest

from .test_private_multi_parent_construction import full_workflow
from .private_analysis_exchange_fixtures import launch_assignment


@pytest.mark.parametrize('kind',['local','pbs_ssh'])
@pytest.mark.parametrize('mixed',[False,True])
def test_original_a106_configuration_cannot_hide_non_api_native_branch(full_workflow,kind,mixed):
    store,host=full_workflow
    binding=host.episode_bindings.for_child((('annotation','root'),),'launch')
    configuration=deepcopy(binding.as_record()['configuration'])
    configuration['resources']=({**configuration['resources'],'foreign-native':{'kind':kind}}
        if mixed else {'foreign-native':{'kind':kind}})
    configuration['initial_information']={}
    with pytest.raises(ValueError,match='explicit_execution_resources_required'):
        type(binding)(host.services,store=store,directory=host.directory,run_id=host.run_id,
            tool_registry=host.tools,**configuration)


def test_original_a106_actual_launch_declares_and_admits_only_api(full_workflow):
    store,host=full_workflow
    root=(('annotation','root'),)
    binding=host.episode_bindings.for_child(root,'launch')
    context=SimpleNamespace(role='launch',path=root+(('launch','launch'),),
        assignment=launch_assignment(),scope=store.validate_scope())
    assert binding.child_roles('launch')==('launch_api',)
    assert binding.allowed_children(context,())==('launch_api',)
    assert binding.child_request_preparer_for_binding('launch_local',binding.binding_path+'/local_job_execution') is None
    assert binding.child_request_preparer_for_binding('launch_hpc',binding.binding_path+'/hpc_job_execution') is None


def test_actual_launch_instructions_and_catalog_do_not_offer_missing_native_kinds(full_workflow):
    from importlib import import_module
    _,host=full_workflow
    binding=host.episode_bindings.for_child((('annotation','root'),),'launch')
    context=SimpleNamespace(role='launch',assignment=launch_assignment())
    package=type(binding).__module__.rsplit('.episode',1)[0]
    source=SimpleNamespace(workflow=SimpleNamespace(
        specialist=lambda source:binding,binding_context=lambda source:context,
        permits_common_action=lambda source,action:action in binding.permitted_common_actions(context),
        native_event_information=None,decision_protocol='explicit-offline-control'))
    prompt=import_module(package+'.task_instructions').instructions(source,{})
    assert binding.instructions(context) in prompt
    assert 'launch_local' not in prompt and 'launch_hpc' not in prompt
    assert [entry['name'] for entry in binding.catalog(context)]==['execution.capabilities']
