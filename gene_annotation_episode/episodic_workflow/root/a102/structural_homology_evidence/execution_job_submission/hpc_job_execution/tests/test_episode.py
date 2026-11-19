"""The HPC job execution episode is exactly the ten-file private binding, and its pure pieces work on a real
assignment. No remote service is contacted: the command itself needs the ``job_access`` service, which is
BLOCKED-ON-JOB-SERVICE (see docs/axis_restructure_20261117/carry_over_blocked)."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from yield_control import CompletionYieldController

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.'
           'execution_job_submission.hpc_job_execution')
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}
WORKSPACE = '/lus/flare/projects/BioReason-Aurora-Test/chian/runs/job'
PROFILE = 'launch_hpc:practical_hpc_handoff'


def module(name):
    return importlib.import_module(PACKAGE + '.' + name)


def assignment():
    return {'version': 'practical_assignment_v1', 'assignment_id': 'a1', 'resource_kind': 'hpc',
            'workspace': WORKSPACE, 'endpoint': 'usable_handoff',
            'requested_job': {'argv': ['qsub', 'job.sh'], 'environment': {}},
            'progress_requirements': [
                {'key': 'handoff', 'credit': 2.0, 'predicate': {'kind': 'requested_job_handoff'}},
                {'key': 'cwd', 'credit': 1.0, 'predicate': {'kind': 'context_cwd', 'path': WORKSPACE + '/work'}}],
            'completion_keys': ['handoff'],
            'initial_context': {'revision': 0, 'cwd': WORKSPACE, 'environment': {}},
            'inventory_snapshot': {}, 'constraints': {}, 'resource_id': 'aurora'}


def test_the_episode_is_one_class_over_the_system_type_and_the_folder_has_the_ten_files():
    episode = module('episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1 and classes[0].__bases__ == (EpisodeBinding,)
    assert classes[0].binding_path == module('goal').BINDING_PATH
    assert classes[0].binding_path == 'structural_homology_evidence/execution_job_submission/hpc_job_execution'
    assert classes[0].child_slots == {} and not hasattr(classes[0], 'msg_to_child')
    found = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*.py')
             if '__pycache__' not in path.parts and 'tests' not in path.relative_to(FOLDER).parts}
    assert found == TEN_FILES


def test_no_module_of_the_folder_imports_another_episode_folder():
    own = 'gene_annotation_episode.episodic_workflow.root.'
    for path in FOLDER.rglob('*.py'):
        if '__pycache__' in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            names = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                     else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for name in names:
                assert not name.startswith(own), (path, name)


def test_the_assignment_is_admitted_and_read_into_the_parent_input():
    from_parent = module('messages.read_from_parent')
    admitted = from_parent.ASSIGNMENT_FORM.admit(assignment(), 'assignment')
    parent_input = from_parent.read_from_parent(admitted, {})
    assert parent_input['assignment']['endpoint'] == 'usable_handoff'
    assert {item['key']: item['satisfied'] for item in parent_input['initial_validations']} == {'cwd': False}
    assert from_parent.read_from_parent(admitted, {}) == parent_input


def test_a_non_hpc_assignment_fails():
    from_parent = module('messages.read_from_parent')
    with pytest.raises(ValueError):
        from_parent.read_from_parent({**assignment(), 'resource_kind': 'local'}, {})


def test_credit_counts_the_satisfied_requirements_and_the_controller_is_a_completion_controller():
    from_parent = module('messages.read_from_parent')
    parent_input = from_parent.read_from_parent(assignment(), {})
    summary = {**parent_input, 'receipts': []}
    assert module('credit').credit(summary, None) == 0.0
    controller = module('yield_estimator').yield_controller(
        0.0, {'task_yield_profiles': {PROFILE: {'cutoff': 0.5, 'parameters': {}}}}, parent_input)
    assert isinstance(controller, CompletionYieldController) and controller.target == 3.0
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required'):
        module('yield_estimator').yield_controller(0.0, {'task_yield_profiles': {}}, parent_input)


def test_the_model_transport_of_the_command_schema_builds():
    task = module('task')
    schema = task.strict_output_schema(task.ACTION_SCHEMA, **task.TRANSPORT)
    assert schema['type'] == 'object'
    assert set(task.TOOLS) == {'exec_command'} and task.SERVICES == ('job_access',) and task.CHILD_SLOTS == {}
    form = module('messages.final_to_parent').RETURN_FORM
    assert {'credit', 'finding'} <= set(form.fields)


def test_final_to_parent_returns_credit_and_finding():
    import importlib
    final_to_parent = importlib.import_module(__package__.rsplit('.', 1)[0] + '.messages.final_to_parent').final_to_parent
    summary = {'receipts': [], 'receipt_refs': [], 'completion': None, 'last_outcome': None,
               'assignment': {'endpoint': 'usable_handoff'}, 'progress': {'satisfied_keys': []}}
    result = final_to_parent(summary, {'credit': 1.5}, ['practical_completed', 'execution_result_refs'])
    assert result['credit'] == 1.5
    assert result['finding']['completed'] is False
    assert result['practical_completed'] is False and result['execution_result_refs'] == []
