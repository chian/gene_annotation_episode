"""Actual Launch-owned envelopes preserve original request and typed failures.

The permanent original-envelope fixture defines expected behavior. Actual own-axis
registry, identities and typed serialization run; receipt/materialization ports
are controlled and a sentinel stops before a child constructor or native work.
"""
from __future__ import annotations
import importlib
import json
from pathlib import Path
import pytest
PREFIX = 'gene_annotation_episode.episodic_workflow.root.a107'
helper = importlib.import_module(PREFIX + '.tests.test_parent_owned_request_assembly')
PREFIXES = ('', 'hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution', 'scientific_process', 'scientific_process/hpc_work_planning', 'scientific_process/hpc_work_planning/hpc_allocation_execution')
CASES = [(('/'.join(filter(None, (prefix, 'execution_job_submission')))), child, role)
    for prefix in PREFIXES for child, role in (('api_job_execution', 'launch_api'), ('local_job_execution', 'launch_local'), ('hpc_job_execution', 'launch_hpc'))]

@pytest.mark.parametrize('parent_home,child,role', CASES)
def test_actual_launch_envelope_keeps_original_identity_fields_and_once_effects(parent_home, child, role):
    child_home = parent_home + '/' + child
    old = helper.setup(parent_home, child_home, role)
    expected = helper.original_envelope(old.runtime)(old.workflow, *old.args, **old.kwargs)
    live = helper.setup(parent_home, child_home, role)
    with pytest.raises(helper.EnvelopeCaptured):
        live.runtime.Workflow.build(live.workflow, *live.args, **live.kwargs)
    assert live.captures == [{'path': expected[0], 'request': old.runtime._plain(expected[4].as_record()), 'scope': old.args[3]}]
    assert live.events == old.events and [event[0] for event in live.events] == ['materialize', 'bind']
    assert live.selectors == [role]
    assert live.assemblies == [PREFIX + '.' + parent_home.replace('/', '.') + '.to_child_' + child]
    assert 'scientific_invocation_ref' not in live.captures[0]['request']['message']

@pytest.mark.parametrize('parent_home,child,role', CASES)
@pytest.mark.parametrize('failure', ('materialize', 'bind', 'typed_declaration', 'invalid_parent'))
def test_original_failure_type_message_and_effect_order(parent_home, child, role, failure):
    observations = []
    for original in (True, False):
        value = helper.setup(parent_home, parent_home + '/' + child, role, fail_port=failure)
        if failure == 'typed_declaration': value.kwargs['report_contract_declaration'] = {}
        if failure == 'invalid_parent': value.kwargs['parent'] = object()
        try:
            if original: helper.original_envelope(value.runtime)(value.workflow, *value.args, **value.kwargs)
            else: value.runtime.Workflow.build(value.workflow, *value.args, **value.kwargs)
        except Exception as error:
            assert not isinstance(error, helper.EnvelopeCaptured)
            observations.append((type(error), str(error), getattr(error, 'code', None), value.events))
        else: pytest.fail('original invalid request was accepted')
    assert observations[0] == observations[1]

@pytest.mark.parametrize('parent_home,child,role', CASES)
def test_compatibility_identity_and_actual_private_return_dispatch(parent_home, child, role):
    value = helper.setup(parent_home, parent_home + '/' + child, role)
    parent = value.workflow.episode_bindings.for_path(value.kwargs['parent_path'])
    assignment = {'original': ['unadmitted', 'identity']}
    assert parent.prepare_child_request(object(), role, assignment) is assignment
    assert parent.prepare_child_request(object(), 'unknown-original-role', assignment) is assignment
    selected = value.workflow.episode_bindings.for_child(value.kwargs['parent_path'], role)
    assert selected.binding_path == parent_home + '/' + child
    assert selected is value.workflow.episode_bindings.for_path((*value.kwargs['parent_path'], (role, 'child_fixed')))
    assert parent.execution_child_report_receiver(role) is importlib.import_module(PREFIX + '.' + parent_home.replace('/', '.') + '.from_child_' + child).receive_report
    assert getattr(selected, 'prepare_assignment').__func__.__module__ == PREFIX + '.' + selected.binding_path.replace('/', '.') + '.from_parent'
    assert getattr(selected, 'validate_report').__func__.__module__ == PREFIX + '.' + selected.binding_path.replace('/', '.') + '.to_parent'

@pytest.mark.parametrize('parent_home', list(dict.fromkeys(home for home, _, _ in CASES)))
@pytest.mark.parametrize('match,fail', [('launch_api', None), ('launch_local', None), ('launch_hpc', None), (None, None), (None, 'launch_api'), (None, 'launch_hpc')])
def test_direct_callback_keeps_original_comparison_order_and_errors(parent_home, match, fail):
    fixture = json.loads((Path(__file__).parent / 'fixtures/organization_original/a107_launch_identity_callbacks.json').read_bytes())
    original = fixture['homes'][parent_home]
    namespace = {}
    exec(compile(original['source'], original['original_source_path'], 'exec'), namespace)
    value = helper.setup(parent_home, parent_home + '/local_job_execution', 'launch_local')
    parent = value.workflow.episode_bindings.for_path(value.kwargs['parent_path'])
    observations = []
    for use_original in (True, False):
        events = []
        class Role:
            def __eq__(self, other):
                events.append(other)
                if other == fail: raise ValueError('original_role_comparison_failure:' + other)
                return other == match
        assignment = {'retained': ['original', 'identity']}
        try:
            result = namespace['prepare_child_request'](None, object(), Role(), assignment) if use_original else parent.prepare_child_request(object(), Role(), assignment)
        except ValueError as error:
            observations.append(('error', type(error), str(error), events))
        else:
            assert result is assignment
            observations.append(('same_assignment', events))
    assert observations[0] == observations[1]
