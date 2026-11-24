"""The A110 HPC job execution episode is a private binding in the ten-file form, reads a real assignment and prices
real receipts. Nothing here contacts a resource: the job-access service is not built (BLOCKED-ON-JOB-SERVICE)."""
import ast
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import CompletionYieldController

from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.practical_execution_records import (
    assess_validations, digest, validate_receipt)

from .. import episode as episode_module
from ..credit import credit
from ..episode import HpcJobExecution
from ..goal import BINDING_PATH
from ..messages.final_to_parent import RETURN_FORM, final_to_parent
from ..messages.internal_summary import completion_proof, returnable_handoff
from ..messages.read_from_parent import ASSIGNMENT_FORM, read_from_parent
from ..yield_estimator import yield_controller

FOLDER = Path(episode_module.__file__).parent
PACKAGE = episode_module.__name__.rsplit('.', 1)[0]
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}
PROFILES = {'launch_hpc:practical_hpc_handoff': {'cutoff': 0.5, 'parameters': {}}}


def test_the_class_inherits_only_the_system_episode_type():
    assert HpcJobExecution.__bases__ == (EpisodeBinding,)
    assert HpcJobExecution.binding_path == BINDING_PATH
    assert PACKAGE.endswith(BINDING_PATH.replace('/', '.'))
    assert dict(HpcJobExecution.child_slots) == {}
    assert tuple(HpcJobExecution.services) == ('job_access',)
    assert set(HpcJobExecution.tools) == {'exec_command'}
    assert not hasattr(HpcJobExecution, 'msg_to_child') and not hasattr(HpcJobExecution, 'read_from_child')


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
                 'execution_handoff_refs', 'execution_result_refs', 'execution_file_source_refs',
                 'execution_file_capture_outcomes', 'execution_completed'):
        assert name in RETURN_FORM.fields and not RETURN_FORM.fields[name].required


def _assignment(**changes):
    value = {'version': 'practical_assignment', 'assignment_id': 'a1', 'resource_id': 'aurora',
             'resource_kind': 'hpc', 'workspace': '/work/space', 'endpoint': 'usable_handoff',
             'requested_job': {'argv': ['/bin/true'], 'environment': {}},
             'progress_requirements': [
                 {'key': 'cwd', 'credit': 1.0, 'predicate': {'kind': 'context_cwd', 'path': '/work/space/run'}},
                 {'key': 'handoff', 'credit': 4.0, 'predicate': {'kind': 'requested_job_handoff'}}],
             'completion_keys': ['handoff'],
             'initial_context': {'revision': 0, 'cwd': '/work/space', 'environment': {}},
             'inventory_snapshot': {}, 'constraints': {}}
    value.update(changes)
    return value


def _parent_input():
    return read_from_parent(ASSIGNMENT_FORM.admit(_assignment(), 'assignment'), {'purpose': 'launch'})


def test_the_assignment_is_read_once_and_gives_the_completion_target():
    parent_input = _parent_input()
    assert parent_input['completion_target'] == 4.0
    assert parent_input['task_yield_class'] == 'practical_hpc_handoff'
    assert parent_input['assignment']['completion_keys'] == ['handoff']
    controller = yield_controller(0.0, {'task_yield_profiles': PROFILES}, parent_input)
    assert isinstance(controller, CompletionYieldController) and controller.target == 4.0


def test_a_request_class_without_a_yield_profile_fails():
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required:launch_hpc:practical_hpc_handoff'):
        yield_controller(0.0, {'task_yield_profiles': {}}, _parent_input())


def test_a_wrong_commission_fails():
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit(_assignment(resource_kind='local'), 'assignment')
    with pytest.raises(ValueError):
        read_from_parent(ASSIGNMENT_FORM.admit(_assignment(completion_keys=['unknown']), 'assignment'), {})
    with pytest.raises(ValueError):
        read_from_parent(ASSIGNMENT_FORM.admit(_assignment(
            requested_job={'native_flux_balance': {}}, native_flux_balance_execution={}), 'assignment'), {})


def _receipt(assignment, *, cwd):
    """A real receipt of a command that only changed the working directory (no scheduler submission)."""
    before = assignment['initial_context']
    after = {**before, 'cwd': cwd, 'revision': before['revision'] + 1}
    outcome = {'facts': {}}
    return validate_receipt({
        'version': 'practical_action_receipt', 'run_id': 'run', 'episode_id': 'ep',
        'assignment_sha256': digest(assignment),
        'operation_key': 'op_1', 'tool_name': 'exec_command', 'arguments': {'cmd': 'cd run', 'workdir': cwd,
                                                                            'env': {}},
        'context_before': before, 'context_after': after, 'outcome': outcome,
        'validations': assess_validations(assignment, outcome, after, tool_name='exec_command'),
        'started_at': '2026-11-19T10:00:00+00:00', 'finished_at': '2026-11-19T10:00:01+00:00'})


def test_credit_is_the_sum_of_the_satisfied_requirements_and_a_cwd_command_is_not_a_handoff():
    assignment = _parent_input()['assignment']
    initial = assess_validations(assignment, {'facts': {}}, assignment['initial_context'],
                                 checked_at='1970-01-01T00:00:00+00:00')
    summary = {'assignment': assignment, 'initial_validations': initial, 'receipts': []}
    assert credit(summary, None) == 0.0
    receipt = _receipt(assignment, cwd='/work/space/run')
    summary['receipts'] = [receipt]
    assert credit(summary, None) == 1.0
    assert completion_proof(assignment, ['cwd'], [receipt]) is None
    assert returnable_handoff(assignment, receipt) is False


def test_the_return_carries_the_finding_and_every_selectable_field_and_is_admitted_by_the_form():
    assignment = _parent_input()['assignment']
    summary = {'assignment': assignment, 'receipts': [], 'receipt_refs': [], 'handoff_refs': [],
               'completion_proof': None, 'progress': {'satisfied_keys': []}, 'last_outcome': None}
    completion = {'credit': 0.0, 'ended_by': 'yield_stop', 'units_consumed': 0}
    selectable = [name for name, spec in RETURN_FORM.fields.items() if not spec.required]
    result = final_to_parent(summary, completion, selectable)
    assert result['credit'] == 0.0 and result['practical_completed'] is False
    assert result['finding']['commands_run'] == 0 and result['execution_result_refs'] == []
    RETURN_FORM.admit(result, 'return')
