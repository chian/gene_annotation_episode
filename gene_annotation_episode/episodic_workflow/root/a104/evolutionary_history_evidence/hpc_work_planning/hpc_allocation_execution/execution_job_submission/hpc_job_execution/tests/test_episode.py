"""The A104 HPC job execution episode is a private binding in the ten-file form, and reads a real assignment."""
import ast
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import CompletionYieldController

from .. import episode as episode_module
from ..episode import HPCJobExecution
from ..goal import BINDING_PATH
from ..messages.final_to_parent import RETURN_FORM
from ..messages.read_from_parent import ASSIGNMENT_FORM, read_from_parent
from ..yield_estimator import yield_controller

FOLDER = Path(episode_module.__file__).parent
PACKAGE = episode_module.__name__.rsplit('.', 1)[0]
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}


def test_the_class_inherits_only_the_system_episode_type():
    assert HPCJobExecution.__bases__ == (EpisodeBinding,)
    assert HPCJobExecution.binding_path == BINDING_PATH
    assert PACKAGE.endswith(BINDING_PATH.replace('/', '.'))
    assert dict(HPCJobExecution.child_slots) == {}
    assert tuple(HPCJobExecution.services) == ('job_access',)
    assert set(HPCJobExecution.tools) == {'exec_command'}


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
                 'execution_handoff_refs', 'execution_result_refs', 'execution_completed',
                 'execution_blast_hsps'):
        assert name in RETURN_FORM.fields and not RETURN_FORM.fields[name].required


def _assignment(**changes):
    value = {'version': 'practical_assignment', 'assignment_id': 'a1', 'resource_id': 'hpc',
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


def test_the_assignment_is_read_once_and_gives_the_completion_target():
    assignment = ASSIGNMENT_FORM.admit(_assignment(), 'assignment')
    parent_input = read_from_parent(assignment, {})
    assert parent_input['completion_target'] == 4.0
    assert parent_input['assignment']['completion_keys'] == ['handoff']
    settings = {'task_yield_profiles': {'launch_hpc:practical_hpc_handoff': {'cutoff': 0.5, 'parameters': {}}}}
    controller = yield_controller(0.0, settings, parent_input)
    assert isinstance(controller, CompletionYieldController) and controller.target == 4.0


def test_a_request_class_without_a_yield_profile_fails():
    assignment = ASSIGNMENT_FORM.admit(_assignment(), 'assignment')
    parent_input = read_from_parent(assignment, {})
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required:launch_hpc:practical_hpc_handoff'):
        yield_controller(0.0, {'task_yield_profiles': {}}, parent_input)


def test_a_wrong_commission_fails():
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit(_assignment(resource_kind='local'), 'assignment')
    with pytest.raises(ValueError):
        read_from_parent(ASSIGNMENT_FORM.admit(_assignment(completion_keys=['unknown']), 'assignment'), {})


# Credit, summary and return over real receipts. The receipt is built by the library's own assessment and
# validation functions; no command is run (the job service is not built), so no tool outcome is produced here.
from method_loop import EpisodeView

from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.practical_execution_records import (
    RECEIPT_VERSION, assess_validations, digest, validate_receipt)

from ..credit import credit
from ..messages.final_to_parent import final_to_parent
from ..messages.internal_summary import internal_summary


def _view(parent_input, outcomes=()):
    return EpisodeView(grain=None, key='k', path=None, units_consumed=len(outcomes), updates=(),
                       controller_state=None, episode_ref=None, request=None, parent_input=parent_input,
                       outcomes=tuple(outcomes), records=None)


def _parent_input():
    return read_from_parent(ASSIGNMENT_FORM.admit(_assignment(), 'assignment'), {})


def _cd_unit(parent_input):
    """One command that changed the working directory into the required directory and handed nothing off."""
    assignment = parent_input['assignment']
    before = assignment['initial_context']
    after = {'revision': 1, 'cwd': '/work/space/run', 'environment': {}}
    outcome = {'facts': {}, 'native_outcome': {}}
    receipt = validate_receipt({
        'version': RECEIPT_VERSION, 'run_id': 'r', 'episode_id': 'e', 'assignment_sha256': digest(assignment),
        'operation_key': 'op1', 'tool_name': 'exec_command', 'arguments': {'cmd': 'cd run'},
        'context_before': before, 'context_after': after, 'outcome': outcome,
        'validations': assess_validations(assignment, outcome, after, tool_name='exec_command'),
        'started_at': '2026-01-01T00:00:00+00:00', 'finished_at': '2026-01-01T00:00:01+00:00'})
    return {'arguments': {'arguments': {'cmd': 'cd run', 'workdir': '/work/space/run', 'env': {}}},
            'outcome': {'status': 'completed', 'receipt': receipt, 'receipt_ref': 'ref1',
                        'operation_ref': digest('op1')}}


def test_credit_and_return_before_any_command():
    summary = internal_summary(_view(_parent_input()))
    assert credit(summary, None) == 0.0
    result = final_to_parent(summary, {'credit': 0.0}, [])
    assert result['credit'] == 0.0 and result['finding']['practical_completed'] is False
    assert result['finding']['unsatisfied_keys'] == ['cwd', 'handoff']
    RETURN_FORM.admit(result, 'return')


def test_credit_is_the_sum_of_the_satisfied_requirements_after_a_command():
    parent_input = _parent_input()
    summary = internal_summary(_view(parent_input, [_cd_unit(parent_input)]))
    assert credit(summary, None) == 1.0
    result = final_to_parent(summary, {'credit': 1.0}, ['practical_receipt_refs', 'practical_completed'])
    assert result['practical_receipt_refs'] == ['ref1'] and result['practical_completed'] is False
    assert result['finding']['satisfied_keys'] == ['cwd'] and result['finding']['commands_run'] == 1
    RETURN_FORM.admit(result, 'return')


def test_a_launch_returns_credit_finding_and_every_selectable_fact_and_is_admitted():
    from ..messages.final_to_parent import FAMILY_SOURCES, final_to_parent as returned
    summary = {'execution_completion': None, 'receipts': [{'outcome': {'status': 'ok'}}],
               'receipt_refs': ['receipt_1'], 'handoff_refs': ['receipt_1'],
               'execution_progress': {'satisfied_keys': [], 'requirements': [{'key': 'k1', 'satisfied': False}]},
               'commands': [{'failure': 'exit 1'}], 'assignment': {'endpoint': 'usable_handoff'}}
    every = tuple(name for name in RETURN_FORM.fields if name not in ('credit', 'finding'))
    result = returned(summary, {'credit': 1.0}, every)
    assert result['credit'] == 1.0 and result['practical_completed'] is False
    assert result['execution_handoff_refs'] == ['receipt_1'] and result['finding']['unsatisfied_keys'] == ['k1']
    assert all(result[name] == [] for name in FAMILY_SOURCES)
    RETURN_FORM.admit(result, 'return')
    RETURN_FORM.admit(returned(summary, {'credit': 1.0}, ()), 'return')
