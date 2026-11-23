"""The HPC job execution episode is exactly the ten-file private binding, and its pure pieces work on a real
assignment. No remote service is contacted: the command itself needs the ``job_access`` service, which is
BLOCKED-ON-JOB-SERVICE (see docs/axis_restructure_20261117/carry_over_blocked)."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from yield_control import CompletionYieldController

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.'
           'hpc_work_planning.execution_job_submission.hpc_job_execution')
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}
WORKSPACE = '/lus/flare/projects/BioReason-Aurora-Test/chian/runs/job'


def module(name):
    return importlib.import_module(PACKAGE + '.' + name)


def assignment():
    return {'version': 'practical_assignment', 'assignment_id': 'a1', 'resource_kind': 'hpc',
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
    assert parent_input['yield_class'] == 'practical_hpc_handoff'
    assert parent_input['credit_target'] == 3.0
    assert {item['key']: item['satisfied'] for item in parent_input['initial_validations']} == {'cwd': False}


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
        0.0, {'task_yield_profiles': {'launch_hpc:practical_hpc_handoff': {'cutoff': 0.5, 'parameters': {}}}},
        parent_input)
    assert isinstance(controller, CompletionYieldController) and controller.target == 3.0
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required'):
        module('yield_estimator').yield_controller(0.0, {'task_yield_profiles': {}}, parent_input)


def test_no_completion_proof_exists_before_a_command_receipt_or_before_the_completion_keys_are_satisfied():
    proof = module('messages.internal_summary').completion_proof
    assert proof(assignment(), {'satisfied_keys': ['handoff']}, []) is None
    receipt = {'validations': [], 'run_id': 'r', 'episode_id': 'e', 'operation_key': 'k'}
    assert proof(assignment(), {'satisfied_keys': []}, [receipt]) is None
    assert proof(assignment(), {'satisfied_keys': ['handoff']}, [receipt]) is None


def test_the_return_carries_the_finding_and_every_selectable_field_and_is_admitted_by_the_form():
    final = module('messages.final_to_parent')
    summary = {'assignment': assignment(), 'receipts': [], 'receipt_refs': [], 'completion': None,
               'progress': {'satisfied_keys': []}, 'last_outcome': None}
    selectable = [name for name, spec in final.RETURN_FORM.fields.items() if not spec.required]
    result = final.final_to_parent(summary, {'credit': 0.0, 'ended_by': 'yield_stop', 'units_consumed': 0},
                                   selectable)
    assert result['credit'] == 0.0 and result['execution_completed'] is False
    assert result['finding']['receipts'] == 0 and result['execution_result_refs'] == []
    final.RETURN_FORM.admit(result, 'return')
