"""Actual scientific parent request selection through Workflow.build.

Reuses the permanent original-envelope helper/fixture. Real registry, typed
contracts and identities run; acquisition stops at the child source constructor.
Receipt/materialization are controlled; no restoration or science is claimed.
"""
from __future__ import annotations
import importlib
from pathlib import Path
import pytest
PREFIX='gene_annotation_episode.episodic_workflow.root.a110'
helper=importlib.import_module(PREFIX+'.tests.test_parent_owned_request_assembly')
CASES=(('launch','scientific_process/execution_job_submission'),('results','scientific_process/execution_result_acquisition'),('scientific_process','scientific_process'))
def setup(child_home,role,**kwargs):
    value=helper.setup('scientific_process',child_home,role,**kwargs)
    # The original helper bypasses constructors. Supply the exact ordinary
    # configuration operand required by registry recursive admission; the
    # genuine child_roles method and same-home registry selection still run.
    parent=value.workflow.episode_bindings.for_path(value.kwargs['parent_path'])
    parent._child_roles=('scientific_process',)
    return value
@pytest.mark.parametrize('role,child_home',CASES)
def test_actual_private_request_selection_preserves_all_original_fields_and_once_effects(role,child_home):
    old=setup(child_home,role)
    expected=helper.original_envelope(old.runtime)(old.workflow,*old.args,**old.kwargs)
    live=setup(child_home,role)
    with pytest.raises(helper.EnvelopeCaptured):live.runtime.Workflow.build(live.workflow,*live.args,**live.kwargs)
    assert live.captures==[{'path':expected[0],'request':old.runtime._plain(expected[4].as_record()),'scope':old.args[3]}]
    assert live.events==old.events and [e[0] for e in live.events]==['materialize','bind']
    assert live.selectors==[role]
    assert live.assemblies==[PREFIX+'.scientific_process.to_child_'+child_home.rsplit('/',1)[-1]]
    if role=='scientific_process':
        reference=importlib.import_module(PREFIX+'.scientific_process_records').scientific_invocation_ref(live.workflow.run_id,expected[0])
        assert live.captures[0]['request']['message']['scientific_invocation_ref']==reference
        assert live.workflow.episode_bindings.for_path(expected[0]) is live.workflow.episode_bindings.for_path(live.kwargs['parent_path'])
    else:assert 'scientific_invocation_ref' not in live.captures[0]['request']['message']
@pytest.mark.parametrize('role,child_home',CASES)
@pytest.mark.parametrize('failure',('materialize','bind','typed_declaration','invalid_parent'))
def test_original_failure_type_message_and_effect_order(role,child_home,failure):
    observations=[]
    for old in (True,False):
        value=setup(child_home,role,fail_port=failure)
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
@pytest.mark.parametrize('role,child_home',CASES)
def test_original_incoming_assignment_identity_and_real_both_endpoints(role,child_home):
    value=setup(child_home,role)
    parent=value.workflow.episode_bindings.for_path(value.kwargs['parent_path']);assignment={'original':['typed','supplied']}
    assert parent.prepare_child_request(object(),role,assignment) is assignment
    child=value.workflow.episode_bindings.for_path((*value.kwargs['parent_path'],(role,'child_fixed')))
    assert child.binding_path==child_home
    child_dir=Path(importlib.import_module(PREFIX+'.'+child_home.replace('/','.')+'.episode').__file__).parent
    assert (child_dir/'from_parent.py').is_file() and (child_dir/'to_parent.py').is_file()
    receiver=parent.execution_child_report_receiver(role)
    assert receiver.__module__==PREFIX+'.scientific_process.from_child_'+child_home.rsplit('/',1)[-1]

@pytest.mark.parametrize('stop',('launch','results',None))
def test_public_preparation_preserves_original_role_comparison_order(stop):
    value=setup('scientific_process/execution_job_submission','launch')
    parent=value.workflow.episode_bindings.for_path(value.kwargs['parent_path']);events=[]
    class ComparisonFailure(Exception):pass
    class OriginalRoleOperand:
        def __eq__(self,other):
            events.append(other)
            if other==stop:raise ComparisonFailure('original comparison failure')
            return False
    assignment={'original':'same object'}
    if stop is None:
        assert parent.prepare_child_request(object(),OriginalRoleOperand(),assignment) is assignment
    else:
        with pytest.raises(ComparisonFailure,match='original comparison failure'):
            parent.prepare_child_request(object(),OriginalRoleOperand(),assignment)
    expected=['monitor','launch','results']
    assert events==expected if stop is None else events==expected[:expected.index(stop)+1]
