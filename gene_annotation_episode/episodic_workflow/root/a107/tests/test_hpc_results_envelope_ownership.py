"""Real HPC Results parent selection and original typed request boundary.

No HPC execution. Uses permanent original-envelope fixture and real registry;
child acquisition stops at its source constructor and side effects are controlled.
"""
from __future__ import annotations
import importlib
from pathlib import Path
import pytest
PREFIX='gene_annotation_episode.episodic_workflow.root.a107'
helper=importlib.import_module(PREFIX+'.tests.test_parent_owned_request_assembly')
HOMES=('hpc_work_planning','hpc_work_planning/hpc_allocation_execution','scientific_process/hpc_work_planning','scientific_process/hpc_work_planning/hpc_allocation_execution')
@pytest.mark.parametrize('home',HOMES)
def test_actual_hpc_results_owner_preserves_request_and_ordered_side_effects(home):
    child=home+'/execution_result_acquisition';old=helper.setup(home,child,'results')
    expected=helper.original_envelope(old.runtime)(old.workflow,*old.args,**old.kwargs)
    live=helper.setup(home,child,'results')
    with pytest.raises(helper.EnvelopeCaptured):live.runtime.Workflow.build(live.workflow,*live.args,**live.kwargs)
    assert live.captures==[{'path':expected[0],'request':old.runtime._plain(expected[4].as_record()),'scope':old.args[3]}]
    assert live.events==old.events and [e[0] for e in live.events]==['materialize','bind']
    assert live.selectors==['results']
    assert live.assemblies==[PREFIX+'.'+home.replace('/','.')+'.to_child_execution_result_acquisition']
@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('failure',('materialize','bind','typed_declaration','invalid_parent'))
def test_original_hpc_results_errors_and_side_effect_order(home,failure):
    observations=[]
    for old in (True,False):
        value=helper.setup(home,home+'/execution_result_acquisition','results',fail_port=failure)
        if failure=='typed_declaration':value.kwargs['report_contract_declaration']={}
        if failure=='invalid_parent':value.kwargs['parent']=object()
        try:
            if old:helper.original_envelope(value.runtime)(value.workflow,*value.args,**value.kwargs)
            else:value.runtime.Workflow.build(value.workflow,*value.args,**value.kwargs)
        except Exception as error:
            assert not isinstance(error,helper.EnvelopeCaptured)
            observations.append((type(error),str(error),getattr(error,'code',None),value.events))
        else:pytest.fail('original invalid request was accepted')
    assert observations[0]==observations[1]
@pytest.mark.parametrize('home',HOMES)
def test_hpc_results_assignment_identity_and_actual_endpoint_pair(home):
    value=helper.setup(home,home+'/execution_result_acquisition','results')
    owner=value.workflow.episode_bindings.for_path(value.kwargs['parent_path']);assignment={'original':['supplied','results']}
    assert owner.prepare_child_request(object(),'results',assignment) is assignment
    child=value.workflow.episode_bindings.for_path((*value.kwargs['parent_path'],('results','child_fixed')))
    assert child.binding_path==home+'/execution_result_acquisition'
    folder=Path(importlib.import_module(PREFIX+'.'+child.binding_path.replace('/','.')+'.episode').__file__).parent
    assert (folder/'from_parent.py').is_file() and (folder/'to_parent.py').is_file()
    assert owner.execution_child_report_receiver('results').__module__==PREFIX+'.'+home.replace('/','.')+'.from_child_execution_result_acquisition'

@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('stop',('results',None))
def test_public_preparation_keeps_original_role_comparison_order(home,stop):
    value=helper.setup(home,home+'/execution_result_acquisition','results')
    owner=value.workflow.episode_bindings.for_path(value.kwargs['parent_path']);events=[]
    class ComparisonFailure(Exception):pass
    class OriginalRoleOperand:
        def __eq__(self,other):
            events.append(other)
            if other==stop:raise ComparisonFailure('original comparison failure')
            return False
    assignment={'original':'same object'}
    if stop is None:assert owner.prepare_child_request(object(),OriginalRoleOperand(),assignment) is assignment
    else:
        with pytest.raises(ComparisonFailure,match='original comparison failure'):
            owner.prepare_child_request(object(),OriginalRoleOperand(),assignment)
    expected=['monitor','results'] if home.endswith('hpc_allocation_execution') else ['hpc_prediction','hpc_execution','monitor','results']
    assert events==expected
