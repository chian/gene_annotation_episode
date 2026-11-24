"""The A110 execution_job_submission episode is exactly the ten-file private binding, and its pure pieces work on
a real launch assignment. No remote service is contacted: the route children's commands need the ``job_access``
service, which is BLOCKED-ON-JOB-SERVICE (see docs/axis_restructure_20261117/carry_over_blocked)."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from yield_control import BoundedQualityYieldController

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.biochemical_feasibility_evidence.'
           'hpc_work_planning.execution_job_submission')
FOLDER = Path(__file__).resolve().parent.parent
CHILD_FOLDERS = ('hpc_job_execution', 'local_job_execution')
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
             'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}
HPC_WORKSPACE = '/lus/flare/projects/BioReason-Aurora-Test/chian/runs/job'
LOCAL_WORKSPACE = '/tmp/job'


def module(name):
    return importlib.import_module(PACKAGE + '.' + name)


def request(resource_id, kind, workspace):
    return {'version': 'practical_assignment', 'assignment_id': 'a-' + resource_id, 'resource_kind': kind,
            'workspace': workspace, 'endpoint': 'usable_handoff',
            'requested_job': {'argv': ['run', 'job.sh'], 'environment': {}},
            'progress_requirements': [
                {'key': 'handoff', 'credit': 2.0, 'predicate': {'kind': 'requested_job_handoff'}}],
            'completion_keys': ['handoff'],
            'initial_context': {'revision': 0, 'cwd': workspace, 'environment': {}},
            'inventory_snapshot': {}, 'constraints': {}, 'resource_id': resource_id}


def assignment(**extra):
    return {'version': 'execution_launch_assignment',
            'requests': {'aurora': request('aurora', 'hpc', HPC_WORKSPACE),
                         'laptop': request('laptop', 'local', LOCAL_WORKSPACE)},
            'immutable_input_versions': [], 'constraints': {}, 'handoff_unit': 1.5, **extra}


def parent_input(**extra):
    from_parent = module('messages.read_from_parent')
    return from_parent.read_from_parent(from_parent.ASSIGNMENT_FORM.admit(assignment(**extra), 'assignment'), {})


def test_the_episode_is_one_class_over_the_system_type_and_the_folder_has_the_ten_files():
    episode = module('episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1 and classes[0].__bases__ == (EpisodeBinding,)
    assert classes[0].binding_path == module('goal').BINDING_PATH
    assert dict(classes[0].child_slots) == dict(module('task').CHILD_SLOTS)
    found = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*.py')
             if '__pycache__' not in path.parts
             and path.relative_to(FOLDER).parts[0] not in ('tests', *CHILD_FOLDERS)}
    assert found == TEN_FILES


def test_no_module_of_the_folder_imports_another_episode_folder():
    own = 'gene_annotation_episode.episodic_workflow.root.'
    for path in FOLDER.rglob('*.py'):
        relative = path.relative_to(FOLDER).parts
        if '__pycache__' in path.parts or relative[0] in CHILD_FOLDERS:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            names = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                     else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for name in names:
                assert not name.startswith(own), (path, name)
            if isinstance(node, ast.ImportFrom) and node.level > 1:
                pytest.fail('relative import above the episode folder: ' + str(path))


def test_the_launch_assignment_is_admitted_and_read_into_the_parent_input():
    parent = parent_input(handed_off_resource_ids=['laptop'])
    assert parent['eligible'] == ['aurora', 'laptop']
    assert parent['handoff_unit'] == 1.5 and parent['handed_off_resource_ids'] == ['laptop']
    constrained = module('messages.read_from_parent').read_from_parent(
        {**assignment(), 'constraints': {'allowed_kinds': ['hpc']}}, {})
    assert constrained['eligible'] == ['aurora']


def test_a_request_under_the_wrong_resource_id_fails():
    bad = assignment()
    bad['requests']['aurora'] = request('elsewhere', 'hpc', HPC_WORKSPACE)
    with pytest.raises(ValueError, match='invalid_execution_request:aurora'):
        module('messages.read_from_parent').read_from_parent(bad, {})


def test_the_controller_is_bounded_by_the_requests_not_yet_handed_off():
    yield_file = module('yield_estimator')
    settings = {'task_yield_profiles': {
        'launch:practical_hpc_handoff+practical_local_handoff': {'cutoff': 0.1, 'parameters': {}}}}
    controller = yield_file.yield_controller(0.0, settings, parent_input(handed_off_resource_ids=['laptop']))
    assert isinstance(controller, BoundedQualityYieldController)
    assert controller.maximum_credit == 1.5
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required'):
        yield_file.yield_controller(0.0, {'task_yield_profiles': {}}, parent_input())


def test_credit_is_the_handoff_unit_for_each_new_handed_off_request():
    summary = {'handoff_unit': 1.5, 'initial_handed_off_resource_ids': ['laptop'],
               'handed_off_resource_ids': ['laptop', 'aurora']}
    assert module('credit').credit(summary, None) == 1.5


def test_the_commission_names_the_selected_request_and_the_return_fields():
    summary = parent_input(record_refs=['input_1'], scientific_task={'scientific_question': 'q'})
    hpc = module('messages.msg_to_child').msg_to_child('hpc_job_execution', {'resource_id': 'aurora'}, summary)
    assert hpc.assignment == summary['requests']['aurora']
    assert hpc.selection == ('execution_handoff_refs', 'execution_completed')
    local = module('messages.msg_to_child').msg_to_child('local_job_execution', {'resource_id': 'laptop'}, summary)
    assert local.assignment['record_refs'] == ['input_1'] and local.assignment['scientific_task']
    with pytest.raises(KeyError):
        module('messages.msg_to_child').msg_to_child('hpc_job_execution', {'resource_id': 'missing'}, summary)


def test_the_return_form_declares_credit_finding_and_the_selectable_facts():
    form = module('messages.final_to_parent').RETURN_FORM
    assert {name for name, spec in form.fields.items() if spec.required} == {'credit', 'finding'}
    assert {'execution_handoff_refs', 'execution_completed'} <= set(form.fields)


def test_the_return_is_the_credit_the_finding_and_each_selectable_fact_admitted_by_the_form():
    module_ = module('messages.final_to_parent')
    summary = {'handoff_refs': ['rec_1'], 'handed_off_resource_ids': ['aurora'], 'initial_handed_off_resource_ids': [],
               'commissioned': [{'resource_id': 'aurora', 'slot': 'hpc_job_execution', 'handoff_refs': ['rec_1'],
                                 'completed': True}]}
    completion = {'credit': 2.0, 'ended_by': 'yield_stop', 'units_consumed': 2}
    selectable = [name for name, spec in module_.RETURN_FORM.fields.items() if not spec.required]
    result = module_.final_to_parent(summary, completion, selectable)
    assert result['credit'] == 2.0 and result['execution_handoff_refs'] == ['rec_1']
    assert result['execution_completed'] is True and result['finding']['new_handoff_count'] == 1
    assert result['execution_result_refs'] == []
    module_.RETURN_FORM.admit(result, 'return')
