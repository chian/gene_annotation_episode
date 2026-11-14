"""Actual twelve Launch envelopes and original opposite message endpoints.

Real registry, identities and typed contracts; controlled receipt/materialization
ports. Child construction stops at its original boundary, before native work.
"""
from __future__ import annotations
from copy import deepcopy
import importlib
from pathlib import Path
import pytest
PREFIX = 'gene_annotation_episode.episodic_workflow.root.a110'
helper = importlib.import_module(PREFIX + '.tests.test_parent_owned_request_assembly')
PARENTS = tuple('/'.join(filter(None, (prefix, 'execution_job_submission'))) for prefix in ('', 'hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution', 'scientific_process', 'scientific_process/hpc_work_planning', 'scientific_process/hpc_work_planning/hpc_allocation_execution'))
EDGES = tuple((home, home + '/' + child, role) for home in PARENTS for role, child in (('launch_local', 'local_job_execution'), ('launch_hpc', 'hpc_job_execution')))
CASES = ('original_fields', 'materialize', 'bind', 'typed_declaration', 'invalid_parent', 'public_identity')


def observations(parent_home, child_home, role, case, *, expected_private):
    if case == 'public_identity':
        value = helper.setup(parent_home, child_home, role)
        parent = value.workflow.episode_bindings.for_path(value.kwargs['parent_path'])
        assignment = {'not_yet_admitted': {'original': ['same', 'object']}}
        markers = []
        for actual in (role, 'not-an-admitted-child', None):
            assert parent.prepare_child_request(object(), actual, assignment) is assignment
            markers.append({'role': actual, 'same_object': True})
        comparisons = []
        class ObservedRole:
            def __eq__(self, other): comparisons.append(other); return False
        assert parent.prepare_child_request(object(), ObservedRole(), assignment) is assignment
        assert comparisons == ['launch_local', 'launch_hpc']
        class InvalidRole:
            def __eq__(self, other): raise ValueError('original-role-comparison-failure')
        with pytest.raises(ValueError, match='original-role-comparison-failure'):
            parent.prepare_child_request(object(), InvalidRole(), assignment)
        return {'identities': markers, 'original_comparisons': comparisons, 'original_invalid_role_error': 'original-role-comparison-failure'}
    old = helper.setup(parent_home, child_home, role, fail_port=case)
    live = helper.setup(parent_home, child_home, role, fail_port=case)
    for value in (old, live):
        if case == 'typed_declaration': value.kwargs['report_contract_declaration'] = {}
        if case == 'invalid_parent': value.kwargs['parent'] = object()
    if case == 'original_fields':
        expected = helper.original_envelope(old.runtime)(old.workflow, *old.args, **old.kwargs)
        with pytest.raises(helper.EnvelopeCaptured):
            live.runtime.Workflow.build(live.workflow, *live.args, **live.kwargs)
        assert live.captures == [{'path': expected[0], 'request': old.runtime._plain(expected[4].as_record()), 'scope': old.args[3]}]
        assert live.events == old.events and [event[0] for event in live.events] == ['materialize', 'bind']
        assert live.selectors == [role]
        actual_module = PREFIX + '.' + parent_home.replace('/', '.') + '.to_child_' + child_home.rsplit('/', 1)[-1]
        assert live.assemblies == ([actual_module] if expected_private else [])
        parent = live.workflow.episode_bindings.for_path(live.kwargs['parent_path'])
        child = live.workflow.episode_bindings.for_path(expected[0])
        assert child.binding_path == child_home
        child_dir = Path(importlib.import_module(PREFIX + '.' + child_home.replace('/', '.') + '.episode').__file__).parent
        assert (child_dir / 'from_parent.py').is_file() and (child_dir / 'to_parent.py').is_file()
        receiver = parent.execution_child_report_receiver(role)
        assert receiver.__module__ == PREFIX + '.' + parent_home.replace('/', '.') + '.from_child_' + child_home.rsplit('/', 1)[-1]
        assert 'scientific_invocation_ref' not in live.captures[0]['request']['message']
        return {'captured': live.captures, 'events': live.events, 'child_home': child.binding_path, 'receiving_owner': receiver.__module__}
    observed = []
    for original, value in ((True, old), (False, live)):
        try:
            if original: helper.original_envelope(value.runtime)(value.workflow, *value.args, **value.kwargs)
            else: value.runtime.Workflow.build(value.workflow, *value.args, **value.kwargs)
        except Exception as error:
            assert not isinstance(error, helper.EnvelopeCaptured)
            observed.append({'exception': type(error).__module__ + '.' + type(error).__qualname__, 'message': str(error), 'code': getattr(error, 'code', None), 'events': value.events})
        else: raise AssertionError('original_invalid_envelope_was_accepted')
    assert observed[0] == observed[1]
    return observed[1]


@pytest.mark.parametrize('parent_home,child_home,role', EDGES)
@pytest.mark.parametrize('case', CASES)
def test_actual_launch_envelope_preserves_original_boundaries(parent_home, child_home, role, case):
    observations(parent_home, child_home, role, case, expected_private=True)
