"""Actual native reference hooks keep foreign contexts from registry lineage.

These are controlled custody-port checks. Constructors are bypassed, no native
work runs, and synthetic port operands are not authenticated scientific records.
"""
from __future__ import annotations
from contextlib import nullcontext
from copy import deepcopy
import importlib
from types import SimpleNamespace
import pytest

AXIS = 'gene_annotation_episode.episodic_workflow.root.a110'
PREFIXES = ('', 'hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution',
    'scientific_process', 'scientific_process/hpc_work_planning',
    'scientific_process/hpc_work_planning/hpc_allocation_execution')
HOMES = ['/'.join(filter(None, (prefix, 'execution_job_submission', native)))
    for prefix in PREFIXES for native in ('local_job_execution', 'hpc_job_execution')]

def owner_and_context(home, role, assignment):
    from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import BindingContext
    module = importlib.import_module(AXIS + '.' + home.replace('/', '.') + '.episode')
    owner = object.__new__(module.ExecutionEpisode)
    owner.native_flux_balance_results = None
    owner.run_id = 'controlled-lineage'
    context = BindingContext(run_id=owner.run_id, episode_id='controlled-recipient', role=role,
        path=((role, 'controlled'),), scope={'subject_refs': []}, assignment=assignment, request={})
    return owner, context

@pytest.mark.parametrize('home', HOMES)
@pytest.mark.parametrize('role', ('launch', 'launch_local', 'launch_hpc', 'results'))
def test_actual_reference_hook_preserves_foreign_role_custody(home, role):
    request = {'resource_id': 'controlled-resource'}
    assignment = {'requests': {'controlled-resource': request}} if role == 'launch' else {'handoff_ref': 'retained-handoff'} if role == 'results' else request
    owner, context = owner_and_context(home, role, assignment)
    calls = []
    def flux_inputs(supplied, selected):
        assert supplied is context and selected == request
        calls.append('input')
        return ['retained-input', 'retained-input']
    def target(supplied):
        assert supplied is context
        calls.append('target')
        return {'controlled': 'target'}
    owner._flux_balance_inputs, owner._target = flux_inputs, target
    actual = owner.initial_references(context)
    if role in {'launch', 'launch_local'}:
        assert actual == ['retained-input'] and calls == ['input']
    elif role == 'results':
        assert actual == ['retained-handoff'] and calls == ['target']
    else:
        assert actual == [] and calls == []

@pytest.mark.parametrize('home', HOMES)
def test_actual_received_filter_uses_recipient_context_not_native_owner_role(home):
    assignment = {'handoff_ref': 'controlled-handoff'}
    owner, context = owner_and_context(home, 'results', assignment)
    selection = {'known_record_refs': ['same', 'foreign'], 'initial_known_record_refs': []}
    bodies = {'same': {'assignment': assignment}, 'foreign': {'assignment': {'handoff_ref': 'other'}}}
    owner.store = SimpleNamespace(read_snapshot=nullcontext,
        get=lambda reference: {'provider': 'episode.execution_result', 'version': 'controlled-port-result'})
    owner._selection = lambda supplied, selected: deepcopy(selection)
    owner._read_result = lambda reference, scope: deepcopy(bodies[reference])
    owner.job_progress_provider = SimpleNamespace(targets=SimpleNamespace(_handoff_reader=lambda: None))
    actual_selection, handoffs, received = owner._received(context)
    assert actual_selection == selection and handoffs == {} and received == {'same': bodies['same']}
