"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode without children; no module imports another episode folder; the
episode's own form, credit, controller and return behave on real data. Nothing here is faked and nothing contacts
a remote service."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from yield_control import CompletionYieldController

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').HpcJobExecution
SUMMARY = importlib.import_module(PACKAGE + '.messages.internal_summary')
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
WORKSPACE = '/lus/flare/projects/x/job'
ASSIGNMENT = {
    'version': 'practical_assignment', 'assignment_id': 'job_1', 'resource_kind': 'hpc', 'workspace': WORKSPACE,
    'endpoint': 'usable_handoff', 'requested_job': {'argv': ['qsub', 'run.sh'], 'environment': {}},
    'progress_requirements': [
        {'key': 'cwd', 'credit': 1.0, 'predicate': {'kind': 'context_cwd', 'path': WORKSPACE + '/work'}},
        {'key': 'handoff', 'credit': 2.0, 'predicate': {'kind': 'requested_job_handoff'}}],
    'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': WORKSPACE, 'environment': {}},
    'inventory_snapshot': {}, 'constraints': {}, 'resource_id': 'aurora'}
SETTINGS = {'task_yield_profiles': {'launch_hpc:practical_hpc_handoff':
                                    {'cutoff': 0.5, 'parameters': {'uncertainty_alpha': 0.1}}}}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == 'evolutionary_history_evidence/execution_job_submission/hpc_job_execution'
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {}
    assert tuple(EPISODE.services) == ('job_access', 'launch_instructions')
    assert set(EPISODE.tools) == {'exec_command'}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_without_children():
    assert files() == FILES
    assert not (FOLDER / 'messages' / 'msg_to_child.py').exists()
    assert not (FOLDER / 'messages' / 'read_from_child.py').exists()


def test_no_module_of_the_folder_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module


def test_the_commission_form_admits_one_hpc_assignment_and_read_from_parent_requires_the_hpc_kind():
    admitted = EPISODE.assignment_form.admit(dict(ASSIGNMENT), 'test')
    parent_input = EPISODE.read_from_parent(admitted, {})
    assert parent_input['assignment_id'] == 'job_1' and parent_input['resource_id'] == 'aurora'
    with pytest.raises(ValueError, match='execution_resource_kind_conflict'):
        EPISODE.read_from_parent({**ASSIGNMENT, 'resource_kind': 'local'}, {})


def test_the_controller_is_the_completion_controller_toward_the_total_requirement_credit():
    parent_input = EPISODE.read_from_parent(dict(ASSIGNMENT), {})
    controller = EPISODE.yield_controller(0.0, SETTINGS, parent_input)
    assert isinstance(controller, CompletionYieldController) and controller.target == 3.0
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required:launch_hpc:practical_hpc_handoff'):
        EPISODE.yield_controller(0.0, {'task_yield_profiles': {}}, parent_input)


def test_credit_is_the_projected_requirement_credit_and_completion_needs_the_endpoint_receipt():
    assignment = EPISODE.read_from_parent(dict(ASSIGNMENT), {})
    baseline = SUMMARY.assess_validations(assignment, {'facts': {}}, assignment['initial_context'],
                                          checked_at=SUMMARY.BASELINE_CHECKED_AT)
    progress = SUMMARY.project_practical_credit(assignment, baseline, [])
    assert EPISODE.credit({'progress': progress}, None) == 0.0
    assert SUMMARY.project_completion(assignment, progress, []) is None


def test_the_return_declares_credit_and_finding_required_and_every_other_fact_selectable():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    assert all(not field.required for name, field in form.fields.items() if name not in ('credit', 'finding'))
    assert {'practical_completed', 'practical_receipt_digests', 'practical_receipt_refs', 'execution_handoff_refs',
            'execution_result_refs', 'execution_completed'} <= set(form.fields)
    assert not any('.' in name for name in form.fields)


def test_final_to_parent_returns_the_credit_the_finding_and_the_selected_recorded_facts():
    assignment = EPISODE.read_from_parent(dict(ASSIGNMENT), {})
    summary = {'assignment': assignment, 'receipts': [], 'receipt_refs': [], 'handoff_refs': [],
               'progress': {'satisfied_keys': []}, 'completion': None}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 0.0}
    selection = ('practical_completed', 'practical_receipt_refs', 'execution_handoff_refs')
    result = EPISODE.final_to_parent(summary, completion, selection)
    FINAL.RETURN_FORM.admit(result, 'return')
    assert result['credit'] == 0.0 and result['practical_completed'] is False
    assert result['finding']['commands_run'] == 0 and result['finding']['completed'] is False
    every = tuple(name for name in FINAL.RETURN_FORM.fields if name not in ('credit', 'finding'))
    full = EPISODE.final_to_parent({**summary, 'receipts': [{'outcome': {'native_outcome': {'failure': 'x'}}}]},
                                   completion, every)
    assert full['finding']['commands_failed'] == 1 and full['execution_result_refs'] == []
    assert all(full[name] == [] for name in FINAL.NATIVE_FAMILIES)
    FINAL.RETURN_FORM.admit(full, 'return')
