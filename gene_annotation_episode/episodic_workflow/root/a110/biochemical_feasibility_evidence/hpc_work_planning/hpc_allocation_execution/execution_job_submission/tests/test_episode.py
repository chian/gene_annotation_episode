"""The A110 execution job submission episode is a private binding in the ten-file form, reads a real launch
assignment, commissions the real forms of its two launch children and prices handoffs. Nothing here contacts a
resource."""
import ast
from pathlib import Path

import pytest

from episode_runtime import ChildMessage, EpisodeBinding
from method_loop import FormError
from yield_control import BoundedQualityYieldController

from .. import episode as episode_module
from ..credit import credit
from ..episode import ExecutionJobSubmission
from ..goal import BINDING_PATH
from ..hpc_job_execution.messages.read_from_parent import ASSIGNMENT_FORM as HPC_FORM
from ..local_job_execution.messages.read_from_parent import ASSIGNMENT_FORM as LOCAL_FORM
from ..messages.final_to_parent import RETURN_FORM, final_to_parent
from ..messages.msg_to_child import msg_to_child
from ..messages.read_from_child import read_from_child
from ..messages.read_from_parent import ASSIGNMENT_FORM, read_from_parent
from ..task import CHILD_SLOTS
from ..yield_estimator import yield_controller

FOLDER = Path(episode_module.__file__).parent
PACKAGE = episode_module.__name__.rsplit('.', 1)[0]
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
             'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}
CHILD_FOLDERS = ('hpc_job_execution', 'local_job_execution')
PROFILES = {'launch:practical_hpc_handoff+practical_local_handoff': {'cutoff': 0.5, 'parameters': {}}}


def test_the_class_inherits_only_the_system_episode_type():
    assert ExecutionJobSubmission.__bases__ == (EpisodeBinding,)
    assert ExecutionJobSubmission.binding_path == BINDING_PATH
    assert PACKAGE.endswith(BINDING_PATH.replace('/', '.'))
    assert dict(ExecutionJobSubmission.child_slots) == {
        'launch_local': BINDING_PATH + '/local_job_execution', 'launch_hpc': BINDING_PATH + '/hpc_job_execution'}
    assert tuple(ExecutionJobSubmission.services) == ('estimate_table',)
    assert set(ExecutionJobSubmission.tools) == {'execution_capabilities'}


def test_the_folder_holds_exactly_the_ten_files():
    found = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
             if path.is_file() and '__pycache__' not in path.parts
             and not {'tests', *CHILD_FOLDERS} & set(path.relative_to(FOLDER).parts)}
    assert found == TEN_FILES


def test_no_module_of_the_episode_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        relative = path.relative_to(FOLDER).parts
        if '__pycache__' in path.parts or 'tests' in relative or relative[0] in CHILD_FOLDERS:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert node.level <= (1 if path.parent == FOLDER else 2), (path, node.module)
                modules = [node.module or '']
            for module in modules:
                assert '.episodic_workflow.root' not in module, (path, module)


def test_the_return_form_declares_credit_and_finding_and_the_old_fact_sources():
    required = {name for name, spec in RETURN_FORM.fields.items() if spec.required}
    assert required == {'credit', 'finding', 'execution_handoff_refs', 'execution_completed'}
    for name in ('execution_result_refs', 'execution_file_source_refs', 'execution_file_capture_outcomes'):
        assert name in RETURN_FORM.fields and not RETURN_FORM.fields[name].required


def _request(resource_id, kind, **changes):
    value = {'version': 'practical_assignment', 'assignment_id': 'a_' + resource_id, 'resource_id': resource_id,
             'resource_kind': kind, 'workspace': '/work/space', 'endpoint': 'usable_handoff',
             'requested_job': {'argv': ['/bin/true'], 'environment': {}},
             'progress_requirements': [
                 {'key': 'handoff', 'credit': 4.0, 'predicate': {'kind': 'requested_job_handoff'}}],
             'completion_keys': ['handoff'],
             'initial_context': {'revision': 0, 'cwd': '/work/space', 'environment': {}},
             'inventory_snapshot': {}, 'constraints': {}}
    value.update(changes)
    return value


def _assignment(**changes):
    value = {'version': 'execution_launch_assignment',
             'requests': {'aurora': _request('aurora', 'hpc'), 'workstation': _request('workstation', 'local')},
             'immutable_input_versions': [], 'constraints': {}, 'handoff_unit': 2.0, 'acquired_record_unit': 1.0}
    value.update(changes)
    return value


def _parent_input(**changes):
    return read_from_parent(ASSIGNMENT_FORM.admit(_assignment(**changes), 'assignment'), {'purpose': 'launch'})


def test_the_assignment_is_read_once_and_gives_the_permitted_requests():
    parent_input = _parent_input()
    assert parent_input['permitted'] == {
        'aurora': {'slot': 'launch_hpc', 'kind': 'hpc', 'yield_class': 'practical_hpc_handoff'},
        'workstation': {'slot': 'launch_local', 'kind': 'local', 'yield_class': 'practical_local_handoff'}}
    constrained = _parent_input(constraints={'allowed_kinds': ['hpc']})
    assert set(constrained['permitted']) == {'aurora'}


def test_the_controller_is_bounded_by_the_requests_without_a_handoff():
    controller = yield_controller(0.0, {'task_yield_profiles': PROFILES}, _parent_input())
    assert isinstance(controller, BoundedQualityYieldController) and controller.maximum_credit == 4.0
    done = _parent_input(received_handoff_resources=['aurora'])
    assert yield_controller(0.0, {'task_yield_profiles': PROFILES}, done).maximum_credit == 2.0
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required'):
        yield_controller(0.0, {'task_yield_profiles': {}}, _parent_input())


def test_a_wrong_commission_fails():
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit({k: v for k, v in _assignment().items() if k != 'handoff_unit'}, 'assignment')
    with pytest.raises(ValueError, match='execution_resource_identity_conflict'):
        _parent_input(requests={'aurora': _request('other', 'hpc')})
    with pytest.raises(ValueError, match='invalid_execution_launch_assignment'):
        _parent_input(requests={})
    with pytest.raises(ValueError, match='explicit_positive_operational_credit_units_required'):
        _parent_input(handoff_unit=0.0)


def test_each_commission_is_admitted_by_the_real_form_of_its_child():
    summary = {'assignment': _parent_input()['assignment'], 'record_refs': [], 'scientific_task': None}
    local = msg_to_child('launch_local', {'resource_id': 'workstation'}, summary)
    hpc = msg_to_child('launch_hpc', {'resource_id': 'aurora'}, summary)
    assert isinstance(local, ChildMessage) and isinstance(hpc, ChildMessage)
    LOCAL_FORM.admit(local.assignment, 'assignment')
    HPC_FORM.admit(hpc.assignment, 'assignment')
    assert local.selection == hpc.selection == ('execution_handoff_refs', 'execution_completed')
    with pytest.raises(ValueError, match='execution_launch_slot_unknown'):
        msg_to_child('launch_api', {'resource_id': 'aurora'}, summary)


def test_credit_counts_each_new_resource_with_a_usable_handoff_once():
    summary = {'handoff_unit': 2.0, 'acquired_record_unit': 1.0, 'received_handoff_resources': ['workstation'],
               'handoff_resources': []}
    assert credit(summary, None) == 0.0
    summary['handoff_resources'] = ['aurora', 'workstation']
    assert credit(summary, None) == 2.0


def test_the_report_of_a_launch_child_is_its_handoff_and_completion():
    result = {'credit': 4.0, 'finding': {}, 'execution_handoff_refs': ['rec_1'], 'execution_completed': True}
    assert read_from_child('launch_hpc', result, {}, None) == {
        'handoff_refs': ['rec_1'], 'completed': True, 'credit': 4.0, 'finding': {}}


def test_the_return_carries_the_finding_and_every_selectable_field_and_is_admitted_by_the_form():
    summary = {'handoff_refs': ['rec_1'], 'handoff_resources': ['aurora'], 'received_handoff_resources': [],
               'launches': [{'slot': 'launch_hpc', 'resource_id': 'aurora', 'completed': True,
                             'handoff_refs': ['rec_1']}]}
    completion = {'credit': 2.0, 'ended_by': 'yield_stop', 'units_consumed': 2}
    selectable = [name for name, spec in RETURN_FORM.fields.items() if not spec.required]
    result = final_to_parent(summary, completion, selectable)
    assert result['credit'] == 2.0 and result['execution_handoff_refs'] == ['rec_1']
    assert result['execution_completed'] is True and result['finding']['new_handoff_count'] == 1
    assert result['execution_result_refs'] == []
    RETURN_FORM.admit(result, 'return')
