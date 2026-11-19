"""The A101 local job execution episode is a private binding in the ten-file form, reads a real assignment, and
reports through its real return form. No unit is run: running one needs the ``job_access`` service, which does not
exist yet (BLOCKED-ON-JOB-SERVICE), and nothing here stands in for it."""
import ast
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import CompletionYieldController

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.practical_execution_credit import (
    project_practical_credit)
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.practical_execution_records import (
    assess_validations)

from .. import credit as credit_file
from .. import episode as episode_module
from .. import task as task_file
from ..episode import LocalJobExecution
from ..goal import BINDING_PATH
from ..messages.final_to_parent import NOT_DECLARABLE, RETURN_FORM, final_to_parent
from ..messages.read_from_parent import ASSIGNMENT_FORM, read_from_parent
from ..yield_estimator import yield_controller

FOLDER = Path(episode_module.__file__).parent
PACKAGE = episode_module.__name__.rsplit('.', 1)[0]
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}


def test_the_class_inherits_only_the_system_episode_type():
    assert LocalJobExecution.__bases__ == (EpisodeBinding,)
    assert LocalJobExecution.binding_path == BINDING_PATH
    assert BINDING_PATH == 'sequence_homology_evidence/execution_job_submission/local_job_execution'
    assert dict(LocalJobExecution.child_slots) == {}
    assert tuple(LocalJobExecution.services) == ('job_access',)
    assert set(LocalJobExecution.tools) == {'exec_command'}


def test_the_folder_holds_exactly_the_ten_files():
    found = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
             if path.is_file() and '__pycache__' not in path.parts and 'tests' not in path.relative_to(FOLDER).parts}
    assert found == TEN_FILES


def test_no_module_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        if '__pycache__' in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert node.level <= (1 if path.parent == FOLDER else 2) or 'tests' in path.parts, (path, node.module)
                modules = [node.module or '']
            for module in modules:
                assert '.episodic_workflow.root' not in module or module.startswith(PACKAGE), (path, module)


def test_the_return_form_declares_credit_and_finding_and_the_old_fact_sources_as_selectable():
    required = {name for name, spec in RETURN_FORM.fields.items() if spec.required}
    assert required == {'credit', 'finding'}
    for name in ('practical_completed', 'practical_receipt_digests', 'practical_receipt_refs',
                 'execution_handoff_refs', 'execution_result_refs', 'execution_completed', 'execution_result_origin',
                 'execution_blast_hsps', 'execution_hmmer_domain_rows', 'execution_blast_database_search_rows',
                 'execution_blast_standard_database_search_rows', 'execution_hmmer_preparation_rows',
                 'execution_blast_pairwise_hsp_rows', 'execution_bvbrc_pages'):
        assert name in RETURN_FORM.fields and not RETURN_FORM.fields[name].required
    assert RETURN_FORM.fields['practical_receipt_refs'].type == 'record_refs'
    # the masking and utility sources have dotted names: a form field name is a lowercase identifier
    assert len(NOT_DECLARABLE) == 21 and not set(NOT_DECLARABLE) & set(RETURN_FORM.fields)


def _assignment(**changes):
    value = {'version': 'practical_assignment_v1', 'assignment_id': 'a1', 'resource_id': 'local',
             'resource_kind': 'local', 'workspace': '/work/space', 'endpoint': 'usable_handoff',
             'requested_job': {'argv': ['/bin/true'], 'environment': {}},
             'progress_requirements': [
                 {'key': 'cwd', 'credit': 1.0, 'predicate': {'kind': 'context_cwd', 'path': '/work/space/run'}},
                 {'key': 'handoff', 'credit': 4.0, 'predicate': {'kind': 'requested_job_handoff'}}],
             'completion_keys': ['handoff'],
             'initial_context': {'revision': 0, 'cwd': '/work/space', 'environment': {}},
             'inventory_snapshot': {}, 'constraints': {}}
    value.update(changes)
    return value


def test_the_assignment_is_read_once_and_gives_the_completion_target_and_the_yield_profile():
    assignment = ASSIGNMENT_FORM.admit(_assignment(), 'assignment')
    parent_input = read_from_parent(assignment, {})
    assert parent_input['completion_target'] == 5.0
    assert parent_input['assignment']['completion_keys'] == ['handoff']
    settings = {'task_yield_profiles': {'launch_local:practical_local_handoff': {'cutoff': 0.5, 'parameters': {}}}}
    controller = yield_controller(0.0, settings, parent_input)
    assert isinstance(controller, CompletionYieldController) and controller.target == 5.0
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required'):
        yield_controller(0.0, {'task_yield_profiles': {}}, parent_input)


def test_a_wrong_commission_fails():
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit(_assignment(resource_kind='hpc'), 'assignment')
    with pytest.raises(ValueError):
        read_from_parent(ASSIGNMENT_FORM.admit(_assignment(completion_keys=['unknown']), 'assignment'), {})


def _settings(tmp_path):
    return {'resources': {'local': {'kind': 'local', 'workspace': str(tmp_path),
                                    'policy': {'memory_bytes': 1 << 30, 'scratch_bytes': 1 << 30}}},
            'coordinator_workspace': str(tmp_path / 'coordinator')}


def test_the_local_transport_refuses_a_workspace_outside_the_configured_one(tmp_path):
    settings = _settings(tmp_path)
    inside = read_from_parent(ASSIGNMENT_FORM.admit(_assignment(workspace=str(tmp_path / 'w'), initial_context={
        'revision': 0, 'cwd': str(tmp_path / 'w'), 'environment': {}},
        progress_requirements=[{'key': 'handoff', 'credit': 4.0, 'predicate': {'kind': 'requested_job_handoff'}}],
        completion_keys=['handoff']), 'assignment'), {})['assignment']
    task_file._operations(settings, inside).validate_action(
        inside, 'exec_command', {'cmd': 'true', 'workdir': str(tmp_path / 'w'), 'env': {}})
    outside = {**inside, 'workspace': '/elsewhere', 'initial_context': {**inside['initial_context'],
                                                                      'cwd': '/elsewhere'}}
    with pytest.raises(ValueError, match='execution_workspace_configuration_conflict'):
        task_file._operations(settings, outside)
    with pytest.raises(ValueError, match='execution_workdir_outside_workspace'):
        task_file._operations(settings, inside).validate_action(
            inside, 'exec_command', {'cmd': 'true', 'workdir': '/elsewhere', 'env': {}})


def test_a_resource_with_an_unplaced_native_binding_raises(tmp_path):
    settings = _settings(tmp_path)
    settings['resources']['local']['native_blast'] = {}
    inside = read_from_parent(ASSIGNMENT_FORM.admit(_assignment(), 'assignment'), {})['assignment']
    with pytest.raises(NotImplementedError, match='unplaced:validate_primary_resource_bindings'):
        task_file._resource_configuration(settings, inside)


def _summary_without_commands():
    assignment = read_from_parent(ASSIGNMENT_FORM.admit(_assignment(), 'assignment'), {})['assignment']
    initial = assess_validations(assignment, {'facts': {}}, assignment['initial_context'],
                                 checked_at='1970-01-01T00:00:00+00:00')
    progress = project_practical_credit(assignment, initial, [])
    return {'assignment': assignment, 'initial_validations': initial, 'receipts': [], 'receipt_refs': [],
            'handoff_refs': [], 'commands': [], 'execution_progress': progress, 'execution_completion': None}


def test_the_credit_is_the_practical_credit_over_the_receipts():
    summary = _summary_without_commands()
    assert credit_file.credit(summary, None) == summary['execution_progress']['credit'] == 0.0


def test_the_return_reports_the_finding_the_selected_facts_and_checks_them_against_the_recorded_facts():
    summary = _summary_without_commands()
    result = final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 0.0},
                             ['practical_completed', 'execution_handoff_refs', 'execution_blast_hsps',
                              'execution_hmmer_domain_rows'])
    assert result['credit'] == 0.0
    assert result['finding']['practical_completed'] is False and result['finding']['commands_run'] == 0
    assert result['execution_handoff_refs'] == [] and result['execution_blast_hsps'] == []
    RETURN_FORM.select(['practical_completed', 'execution_handoff_refs', 'execution_blast_hsps',
                        'execution_hmmer_domain_rows']).admit(result, 'result')
    every = [name for name in RETURN_FORM.fields if name not in ('credit', 'finding')]
    everything = final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 0.0}, every)
    RETURN_FORM.admit(everything, 'return')
    assert everything['execution_result_origin'] == {}
