"""The A104 execution job submission episode is a private binding in the ten-file form, reads a real launch
assignment, and its commissions are admitted by the real forms of the three launch children."""
import ast
import re
from importlib import import_module
from pathlib import Path

import pytest

from episode_runtime import ChildMessage, EpisodeBinding
from method_loop import FormError
from yield_control import BoundedQualityYieldController

from .. import episode as episode_module
from ..credit import credit
from ..episode import ExecutionJobSubmission
from ..goal import BINDING_PATH
from ..messages.final_to_parent import RETURN_FORM, final_to_parent
from ..messages.msg_to_child import msg_to_child
from ..messages.read_from_parent import ASSIGNMENT_FORM, read_from_parent
from ..yield_estimator import yield_controller

FOLDER = Path(episode_module.__file__).parent
PACKAGE = episode_module.__name__.rsplit('.', 1)[0]
CHILDREN = ('api_job_execution', 'hpc_job_execution', 'local_job_execution')
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
             'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}


def _own_files():
    for path in sorted(FOLDER.rglob('*')):
        relative = path.relative_to(FOLDER)
        if (path.is_file() and '__pycache__' not in relative.parts and relative.parts[0] not in CHILDREN
                and relative.parts[0] != 'tests'):
            yield path, relative


def test_the_class_inherits_only_the_system_episode_type():
    assert ExecutionJobSubmission.__bases__ == (EpisodeBinding,)
    assert ExecutionJobSubmission.binding_path == BINDING_PATH
    assert PACKAGE.endswith(BINDING_PATH.replace('/', '.'))
    assert dict(ExecutionJobSubmission.child_slots) == {
        'launch_api': BINDING_PATH + '/api_job_execution', 'launch_local': BINDING_PATH + '/local_job_execution',
        'launch_hpc': BINDING_PATH + '/hpc_job_execution'}
    assert tuple(ExecutionJobSubmission.services) == ('job_access',)
    assert set(ExecutionJobSubmission.tools) == {'execution_capabilities'}


def test_the_folder_holds_exactly_the_ten_files():
    assert {str(relative) for _, relative in _own_files()} == TEN_FILES


def test_no_module_imports_another_episode_folder():
    for path, relative in _own_files():
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                assert node.level <= (1 if len(relative.parts) == 1 else 0), (relative, node.module)
                modules = [node.module or '']
            elif isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            else:
                continue
            for module in modules:
                assert '.episodic_workflow.root' not in module and not module.startswith('..'), (relative, module)


def test_the_return_form_declares_credit_finding_and_the_job_identity_as_required():
    required = {name for name, spec in RETURN_FORM.fields.items() if spec.required}
    assert required == {'credit', 'finding', 'execution_handoff_refs', 'execution_completed'}
    for name in ('execution_result_refs', 'execution_file_source_refs', 'execution_file_capture_outcomes',
                 'execution_blast_hsps', 'execution_blast_pairwise_result_refs'):
        assert name in RETURN_FORM.fields and not RETURN_FORM.fields[name].required


def _practical(resource_id, kind):
    return {'version': 'practical_assignment_v1', 'assignment_id': 'a-' + resource_id, 'resource_id': resource_id,
            'resource_kind': kind, 'workspace': '/work/space', 'endpoint': 'usable_handoff',
            'requested_job': {'argv': ['/bin/true'], 'environment': {}},
            'progress_requirements': [
                {'key': 'handoff', 'credit': 4.0, 'predicate': {'kind': 'requested_job_handoff'}}],
            'completion_keys': ['handoff'],
            'initial_context': {'revision': 0, 'cwd': '/work/space', 'environment': {}},
            'inventory_snapshot': {}, 'constraints': {}}


def _api(resource_id):
    return {'version': 'api_execution_assignment_v1', 'resource_id': resource_id, 'service': 'ebi_hmmer',
            'subject_ref': 'subject_x', 'algorithm': 'phmmer', 'database': 'swissprot', 'parameters': {},
            'page_size': 10, 'endpoint': 'usable_handoff', 'constraints': {}}


def _assignment(**changes):
    value = {'version': 'execution_launch_assignment_v1',
             'requests': {'hpc1': _practical('hpc1', 'hpc'), 'local1': _practical('local1', 'local'),
                          'api1': _api('api1')},
             'immutable_input_versions': [], 'constraints': {}, 'handoff_unit': 2.0, 'acquired_record_unit': 1.0,
             'scientific_task': {'scientific_question': 'q', 'selected_tool_info': {'tool': 't'}},
             'record_refs': ['subject_x']}
    value.update(changes)
    return value


def _parent_input(**changes):
    return read_from_parent(ASSIGNMENT_FORM.admit(_assignment(**changes), 'assignment'), {})


def test_the_assignment_is_read_once_and_names_the_permitted_requests():
    parent_input = _parent_input()
    assert {rid: entry['slot'] for rid, entry in parent_input['permitted'].items()} == {
        'hpc1': 'launch_hpc', 'local1': 'launch_local', 'api1': 'launch_api'}
    assert parent_input['permitted']['api1']['yield_class'] == 'api_ebi_hmmer_phmmer_swissprot_handoff'
    assert parent_input['permitted']['hpc1']['yield_class'] == 'practical_hpc_handoff'
    constrained = _parent_input(constraints={'allowed_kinds': ['hpc']})
    assert set(constrained['permitted']) == {'hpc1'}
    assert set(_parent_input(constraints={'resource_id': 'local1'})['permitted']) == {'local1'}


def test_a_wrong_assignment_fails():
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit(_assignment(version='execution_launch_assignment_v0'), 'assignment')
    with pytest.raises(ValueError, match='execution_resource_identity_conflict'):
        _parent_input(requests={'other': _practical('hpc1', 'hpc')})
    with pytest.raises(ValueError, match='invalid_execution_launch_assignment'):
        _parent_input(requests={})
    with pytest.raises(ValueError, match='invalid_execution_resource_constraints'):
        _parent_input(constraints={'allowed_kinds': 'hpc'})
    with pytest.raises(ValueError, match='explicit_positive_operational_credit_units_required'):
        _parent_input(handoff_unit=0)


def test_the_controller_is_bounded_by_the_requests_still_without_a_handoff():
    parent_input = _parent_input()
    classes = sorted(entry['yield_class'] for entry in parent_input['permitted'].values())
    key = 'launch:' + '+'.join(classes)
    settings = {'task_yield_profiles': {key: {'cutoff': 0.5, 'parameters': {}}}}
    controller = yield_controller(0.0, settings, parent_input)
    assert isinstance(controller, BoundedQualityYieldController) and controller.maximum_credit == 6.0
    received = _parent_input(received_handoff_resources=['api1'])
    assert yield_controller(0.0, settings, received).maximum_credit == 4.0
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required:' + re.escape(key)):
        yield_controller(0.0, {'task_yield_profiles': {}}, parent_input)


def test_a_launch_with_every_request_already_handed_off_has_no_controller():
    """The old exact-zero estimator is not carried; no controller of the system has maximum 0."""
    done = _parent_input(received_handoff_resources=['hpc1', 'local1', 'api1'])
    for initial in (0.0, 1.0):
        with pytest.raises(ValueError, match='launch_every_original_request_already_has_a_handoff'):
            yield_controller(initial, {'task_yield_profiles': {}}, done)


def _summary(**changes):
    parent_input = _parent_input()
    value = {'assignment': parent_input['assignment'], 'record_refs': parent_input['record_refs'],
             'handoff_unit': 2.0, 'acquired_record_unit': 1.0, 'scientific_task': parent_input['scientific_task'],
             'received_handoff_resources': [], 'permitted': parent_input['permitted'], 'capabilities': None,
             'launches': [], 'handoff_refs': [], 'handoff_resources': [], 'controller': None, 'units_consumed': 0}
    value.update(changes)
    return value


def test_the_credit_counts_each_new_handoff_resource_once_and_is_not_bounded():
    assert credit(_summary(), None) == 0.0
    assert credit(_summary(handoff_resources=['hpc1']), None) == 2.0
    assert credit(_summary(handoff_resources=['hpc1', 'local1', 'api1'], received_handoff_resources=['api1']),
                  None) == 4.0
    assert credit(_summary(handoff_resources=['a', 'b', 'c', 'd', 'e']), None) == 10.0


@pytest.mark.parametrize('slot, resource_id, child, selected', [
    ('launch_hpc', 'hpc1', 'hpc_job_execution', ('execution_handoff_refs', 'execution_completed')),
    ('launch_local', 'local1', 'local_job_execution', ('execution_handoff_refs', 'execution_completed')),
    ('launch_api', 'api1', 'api_job_execution', ())])
def test_each_commission_is_admitted_by_the_real_form_of_its_child(slot, resource_id, child, selected):
    message = msg_to_child(slot, {'resource_id': resource_id}, _summary())
    assert isinstance(message, ChildMessage) and message.selection == selected
    form = import_module(PACKAGE + '.' + child + '.messages.read_from_parent')
    admitted = form.ASSIGNMENT_FORM.admit(message.assignment, 'assignment')
    parent_input = form.read_from_parent(admitted, dict(message.message))
    assert parent_input['record_refs' if 'record_refs' in parent_input else 'input_refs'] == ['subject_x']
    returned = import_module(PACKAGE + '.' + child + '.messages.final_to_parent')
    returned.RETURN_FORM.select(message.selection)


def test_a_commission_for_an_unknown_slot_fails():
    with pytest.raises(ValueError, match='execution_launch_slot_unknown:launch_nowhere'):
        msg_to_child('launch_nowhere', {'resource_id': 'hpc1'}, _summary())


def test_the_result_is_admitted_by_the_return_form_and_carries_the_system_credit():
    summary = _summary(handoff_resources=['hpc1'], handoff_refs=['ref_b', 'ref_a'],
                       launches=[{'slot': 'launch_hpc', 'resource_id': 'hpc1', 'completed': True,
                                  'handoff_refs': ['ref_a', 'ref_b'], 'credit': 4.0, 'finding': {}}])
    result = final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 2, 'credit': 2.0},
                             ('execution_result_refs',))
    assert result['credit'] == 2.0 and result['execution_completed'] is True
    assert result['execution_handoff_refs'] == ['ref_a', 'ref_b'] and result['execution_result_refs'] == []
    RETURN_FORM.admit(result, 'return')
    every = tuple(name for name in RETURN_FORM.fields if name not in ('credit', 'finding'))
    full = final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 2, 'credit': 2.0}, every)
    assert full['execution_blast_hsps'] == [] and full['execution_blast_pairwise_result_refs'] == []
    RETURN_FORM.admit(full, 'return')
