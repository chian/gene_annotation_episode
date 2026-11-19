"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode without children; no module imports another episode folder; the
episode's own form, credit, controller, report and blocked transport behave on real data. Nothing here is faked
and nothing contacts a remote service."""
import ast
import asyncio
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import CompletionYieldController

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').HpcJobExecution
TASK = importlib.import_module(PACKAGE + '.task')
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
WORKSPACE = '/lus/flare/projects/BioReason-Aurora-Test/chian/runs'
SHA = 'a' * 64
RESOURCE = {'kind': 'pbs_ssh', 'workspace': WORKSPACE, 'ssh_argv': ['ssh', 'alcf-bastion'],
            'python_executable': '/usr/bin/python3', 'account': 'BioReason-Aurora-Test',
            'scheduler': {'kind': 'pbs'}}
ASSIGNMENT = {
    'version': 'practical_assignment_v1', 'assignment_id': 'job_1', 'resource_id': 'aurora', 'resource_kind': 'hpc',
    'workspace': WORKSPACE, 'endpoint': 'usable_handoff',
    'requested_job': {'argv': ['run_search', '--query', 'q'], 'environment': {'A': 'b'}},
    'progress_requirements': [
        {'key': 'in_workspace', 'credit': 1.0, 'predicate': {'kind': 'context_cwd', 'path': WORKSPACE + '/job'}},
        {'key': 'handoff', 'credit': 3.0, 'predicate': {'kind': 'requested_job_handoff'}}],
    'completion_keys': ['handoff'],
    'initial_context': {'revision': 0, 'cwd': WORKSPACE, 'environment': {}},
    'inventory_snapshot': {}, 'constraints': {}}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {}
    assert tuple(EPISODE.services) == ('job_access',) and set(EPISODE.tools) == {'exec_command'}


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


def test_the_commission_form_admits_one_hpc_assignment_and_read_from_parent_derives_the_continuation_inputs():
    form = EPISODE.assignment_form
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'purpose': 'submit'})
    assert parent_input['task_yield_class'] == 'practical_hpc_handoff'
    assert parent_input['completion_target'] == 4.0
    assert parent_input['assignment']['resource_id'] == 'aurora' and parent_input['message'] == {'purpose': 'submit'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    with pytest.raises(FormError, match='resource_kind'):
        form.admit({**ASSIGNMENT, 'resource_kind': 'local'}, 'test')
    with pytest.raises(ValueError, match='unknown_practical_completion_key'):
        EPISODE.read_from_parent({**admitted, 'completion_keys': ['nothing']}, {})


def test_the_return_declares_credit_and_finding_as_required_and_the_old_fact_sources_as_selectable():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    for name in ('practical_completed', 'practical_receipt_digests', 'practical_receipt_refs',
                 'execution_handoff_refs', 'execution_result_refs', 'execution_file_source_refs',
                 'execution_file_capture_outcomes', 'execution_completed', 'execution_result_origin'):
        assert not form.fields[name].required


def _summary(receipts):
    from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.practical_execution_credit import (
        project_practical_credit)
    summary_module = importlib.import_module(PACKAGE + '.messages.internal_summary')
    initial = summary_module.assess_validations(ASSIGNMENT, {'facts': {}}, ASSIGNMENT['initial_context'],
                                                checked_at=summary_module.INITIAL_CHECKED_AT)
    progress = project_practical_credit(ASSIGNMENT, initial, receipts)
    return {'assignment': ASSIGNMENT, 'initial_validations': initial, 'receipts': receipts, 'progress': progress,
            'receipt_refs': ['artifact_' + str(index) for index in range(len(receipts))], 'handoff_refs': [],
            'completion_proof': summary_module.completion_proof(ASSIGNMENT, progress['satisfied_keys'], receipts)}


def _receipt(satisfied):
    validations = [{'key': 'in_workspace', 'satisfied': satisfied[0],
                    'predicate': ASSIGNMENT['progress_requirements'][0]['predicate']},
                   {'key': 'handoff', 'satisfied': satisfied[1],
                    'predicate': ASSIGNMENT['progress_requirements'][1]['predicate']}]
    return {'run_id': 'r', 'episode_id': 'e', 'assignment_sha256': SHA, 'operation_key': 'op', 'validations': validations,
            'outcome': {'facts': {}}}


def test_credit_is_the_sum_of_the_satisfied_requirement_credits_and_is_not_bounded():
    assert EPISODE.credit(_summary([]), None) == 0.0
    assert EPISODE.credit(_summary([_receipt((True, False))]), None) == 1.0
    assert EPISODE.credit(_summary([_receipt((True, True))]), None) == 4.0      # the completion target: every requirement satisfied
    assert EPISODE.credit(_summary([_receipt((True, True)), _receipt((False, False))]), None) == 0.0   # signed loss
    source = (FOLDER / 'credit.py').read_text()
    assert 'NotImplementedError' not in source and 'min(' not in source and 'max(' not in source


def test_the_completion_proof_needs_every_completion_key_and_the_endpoint_in_the_last_receipt():
    assert _summary([_receipt((True, False))])['completion_proof'] is None
    assert _summary([_receipt((False, True))])['completion_proof']['validation_keys'] == ['handoff']
    assert _summary([_receipt((False, True)), _receipt((True, False))])['completion_proof'] is None


def test_the_controller_is_the_completion_controller_toward_the_credit_every_requirement_earns():
    parent_input = EPISODE.read_from_parent(EPISODE.assignment_form.admit(ASSIGNMENT, 'test'), {})
    settings = {'task_yield_profiles': {'launch_hpc:practical_hpc_handoff':
                                        {'cutoff': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}}}
    controller = EPISODE.yield_controller(0.0, settings, parent_input)
    assert isinstance(controller, CompletionYieldController) and controller.target == 4.0
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required:launch_hpc:practical_hpc_handoff'):
        EPISODE.yield_controller(0.0, {'task_yield_profiles': {}}, parent_input)


def test_the_selection_schema_and_its_strict_transport_build_and_the_resource_refuses_a_workdir_outside_its_workspace():
    schema = TASK.selection_schema()
    assert len(schema['properties']['selection']['anyOf']) == 1 and TASK.generation_schema(schema)
    terminal = TASK.terminal({'resource': RESOURCE, 'coordinator_workspace': '/tmp/coordinator'})
    command = {'cmd': 'qstat -x', 'workdir': WORKSPACE + '/job', 'env': {}}
    terminal.validate_action(ASSIGNMENT, 'exec_command', command)
    with pytest.raises(ValueError, match='execution_workdir_outside_workspace'):
        terminal.validate_action(ASSIGNMENT, 'exec_command', {**command, 'workdir': '/home/chian'})
    with pytest.raises(ValueError, match='invalid_exec_command_arguments'):
        terminal.validate_action(ASSIGNMENT, 'exec_command', {'cmd': 'qstat'})


def test_running_a_command_is_blocked_on_the_job_access_service_and_says_which_call_it_wanted():
    with pytest.raises(NotImplementedError, match=r'BLOCKED-ON-JOB-SERVICE: job_access; wanted call'):
        asyncio.run(TASK.run_command(ASSIGNMENT, {'cmd': 'qstat', 'workdir': WORKSPACE, 'env': {}}, None))


def test_the_return_carries_credit_the_finding_and_every_selectable_fact_and_the_form_admits_it():
    summary = _summary([_receipt((True, True))])
    completion = {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 4.0}
    names = tuple(name for name in EPISODE.return_form.fields if name not in ('credit', 'finding'))
    result = EPISODE.final_to_parent(summary, completion, names)
    assert result['credit'] == 4.0 and result['practical_completed'] is True
    assert result['execution_result_origin'] == {} and result['execution_result_refs'] == []
    EPISODE.return_form.admit(result, 'return')
