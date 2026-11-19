"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks, so the import is
the class-definition check; the folder holds exactly the ten-file set of an episode without children; no module
imports another episode folder; the episode's own form, credit, coverage, controller, report and blocked service
calls behave on real data. Nothing contacts a remote service."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController, BoundedQualityYieldController

PACKAGE = __name__.rsplit('.tests.', 1)[0]
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py', 'tests',
             'messages'}
MESSAGE_FILES = {'__init__.py', 'read_from_parent.py', 'internal_summary.py', 'final_to_parent.py'}
WORKSPACE = '/lus/flare/projects/work'
ROOT = 'gene_annotation_episode.episodic_workflow.root'


@pytest.fixture(scope='module')
def episode():
    return importlib.import_module(PACKAGE + '.episode')


def _module(name):
    return importlib.import_module(PACKAGE + '.' + name)


def _assignment(selector, **extra):
    return {'version': 'execution_results_assignment_v1', 'handoff_ref': ['source_handoff'], 'selector': selector,
            'resource_kind': 'hpc', 'workspace': WORKSPACE, 'acquired_record_unit': 2.0, **extra}


def test_the_class_inherits_only_the_episode_base(episode):
    cls = episode.ExecutionResultAcquisition
    assert cls.__bases__ == (EpisodeBinding,)
    assert cls.binding_path == 'partner_presence_evidence/hpc_work_planning/execution_result_acquisition'
    assert PACKAGE.endswith(cls.binding_path.replace('/', '.'))
    assert dict(cls.child_slots) == {}
    assert cls.services == ('job_access',)
    assert set(cls.tools) == {'execution_results_status', 'execution_results_collect', 'execution_results_read'}
    assert not hasattr(cls, 'msg_to_child') and not hasattr(cls, 'read_from_child')


def test_the_folder_holds_exactly_the_ten_files():
    names = {path.name for path in FOLDER.iterdir() if path.name != '__pycache__'}
    assert names == TEN_FILES
    assert {path.name for path in (FOLDER / 'messages').iterdir() if path.name != '__pycache__'} == MESSAGE_FILES


def test_no_module_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and node.level == 0 else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), (
                    path, module)
            if isinstance(node, ast.ImportFrom) and node.level > 1:
                pytest.fail('a relative import leaves the folder: %s' % path)


def test_the_return_form_declares_credit_finding_and_selectable_sources(episode):
    form = episode.ExecutionResultAcquisition.return_form
    assert {name for name, spec in form.fields.items() if spec.required} == {'credit', 'finding'}
    assert form.fields['credit'].type == 'number'
    assert form.select(['execution_result_refs', 'execution_result_artifact_refs']).fields[
        'execution_result_refs'].required
    with pytest.raises(FormError):
        form.select(['credit'])
    with pytest.raises(FormError):
        form.select(['no_such_field'])


def test_the_assignment_form_names_the_original_fields(episode):
    fields = episode.ExecutionResultAcquisition.assignment_form.fields
    assert fields['version'].value == 'execution_results_assignment_v1'
    assert fields['handoff_ref'].type == 'record_refs' and fields['selector'].type == 'record'
    assert not fields['constraints'].required
    assert fields['initial_result_refs'].type == 'record_refs' and not fields['initial_result_refs'].required


def test_read_from_parent_turns_the_selector_into_requested_windows():
    read = _module('messages.read_from_parent').read_from_parent
    path, other = WORKSPACE + '/out.log', WORKSPACE + '/err.log'
    parent_input = read(_assignment({'paths': [other], 'path': path, 'offset': 10, 'limit': 20}), {'purpose': 'x'})
    assert parent_input['requested'] == {other: [0, None], path: [10, 20]}
    assert parent_input['handoff_refs'] == ['source_handoff']
    with pytest.raises(ValueError, match='practical_write_outside_workspace'):
        read(_assignment({'path': '/etc/passwd'}), {})
    with pytest.raises(ValueError, match='execution_results_paths_required'):
        read(_assignment({'offset': 3}), {})
    with pytest.raises(ValueError, match='explicit_positive_operational_credit_units_required'):
        read(_assignment({'path': path}, acquired_record_unit=0.0), {})
    with pytest.raises(NotImplementedError, match='BLOCKED-ON-JOB-SERVICE'):
        read(_assignment({'version': 'native_blast_result_selector_v1'}), {})
    with pytest.raises(NotImplementedError, match='BLOCKED-ON-JOB-SERVICE'):
        read({**_assignment({'path': path}), 'resource_kind': 'api'}, {})


def _window(path, offset, count, size):
    return {'path': path, 'offset': offset, 'returned_bytes': count, 'size_bytes': size}


def test_credit_counts_each_new_byte_position_once():
    credit = _module('credit')
    path = WORKSPACE + '/out.log'
    initial = [{'windows': [_window(path, 0, 20, 100)]}]
    own = [{'windows': [_window(path, 10, 30, 100)]}, {'windows': [_window(path, 20, 30, 100)]}]
    summary = {'acquired_record_unit': 2.0, 'requested': {path: [0, 100]}, 'initial': initial, 'own': own}
    assert credit.credit(summary, None) == pytest.approx(2.0 * 30 / 100)
    assert credit.credit({**summary, 'own': []}, None) == 0.0


def test_completion_needs_every_requested_byte_of_a_successful_observation():
    summary = _module('messages.internal_summary')
    path = WORKSPACE + '/out.log'
    body = {'observation': {'state': 'completed', 'returncode': 0},
            'windows': [_window(path, 0, 60, 100), _window(path, 60, 40, 100)]}
    assert summary.native_results_complete([body], {path: [0, None]})
    assert not summary.native_results_complete(
        [{**body, 'observation': {'state': 'completed', 'returncode': 1}}], {path: [0, None]})
    assert not summary.native_results_complete([{**body, 'windows': [_window(path, 0, 60, 100)]}], {path: [0, None]})
    assert summary.native_results_complete([{**body, 'windows': [_window(path, 0, 60, 100)]}], {path: [0, 50]})


def test_the_controller_follows_the_selector_and_the_settings():
    controller = _module('yield_estimator').yield_controller
    path = WORKSPACE + '/out.log'
    profile = {'cutoff': 0.1, 'parameters': {}}
    settings = {'results_yield_profiles': {'native_unbounded_hpc': profile},
                'task_yield_profiles': {'results:native_finite_hpc': profile}}
    unbounded = {'assignment': {'resource_kind': 'hpc'}, 'requested': {path: [0, None]}, 'acquired_record_unit': 2.0}
    finite = {**unbounded, 'requested': {path: [0, 50]}}
    assert isinstance(controller(0.0, settings, unbounded), AccumulationYieldController)
    assert isinstance(controller(0.0, settings, finite), BoundedQualityYieldController)
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required'):
        controller(0.0, {}, finite)


def test_the_windows_of_each_tool_stay_inside_the_requested_ones():
    windows = _module('task').requested_windows
    path = WORKSPACE + '/out.log'
    requested = {path: (10, 100)}
    assert windows('execution_results_status', None, requested, 4096) == []
    assert windows('execution_results_collect', None, requested, 4096) == [{'path': path, 'offset': 10, 'limit': 100}]
    assert windows('execution_results_read', {'path': path, 'offset': 20, 'limit': 30}, requested, 4096) == [
        {'path': path, 'offset': 20, 'limit': 30}]
    with pytest.raises(ValueError, match='execution_results_selector_conflict'):
        windows('execution_results_read', {'path': path, 'offset': 90, 'limit': 30}, requested, 4096)


def test_the_report_is_the_recorded_facts_and_a_typed_family_has_no_value(episode):
    final = _module('messages.final_to_parent')
    path = WORKSPACE + '/out.log'
    summary = {'handoff_refs': ['source_handoff'], 'result_refs': ['source_r'], 'result_artifact_refs': ['artifact_r'],
               'completed': True, 'has_windows': True, 'requested_paths': [{'path': path, 'offset': 0, 'limit': None}],
               'window_count': 2, 'failure_count': 0, 'acquired_record_unit': 2.0, 'observation_states': [],
               'action_yields': None}
    result = final.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 1.0},
                                   ('execution_result_refs', 'execution_completed', 'execution_blast_hsps'))
    assert result['credit'] == 1.0 and result['finding']['acquired_selector_fraction'] == 0.5
    assert result['execution_result_refs'] == ['source_r'] and result['execution_blast_hsps'] == []
    form = episode.ExecutionResultAcquisition.return_form
    form.select(['execution_result_refs', 'execution_completed', 'execution_blast_hsps']).admit(result, 'a107 result acquisition return')
    every = tuple(sorted(name for name, field in form.fields.items() if not field.required))
    full = final.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 1.0}, every)
    form.select(every).admit(full, 'a107 result acquisition return')
    assert full['execution_result_origin']['content_location'] == 'current_resource_filesystem'
    none = final.final_to_parent({**summary, 'has_windows': False},
                                 {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 0.0},
                                 ('execution_result_origin',))
    assert none['execution_result_origin'] == {}


def test_the_handoff_and_job_access_are_blocked_until_the_service_exists():
    task = _module('task')
    with pytest.raises(NotImplementedError, match='BLOCKED-ON-JOB-SERVICE'):
        task._read_target(None, ['source_handoff'])


def test_action_turns_a_selected_operation_into_a_tool_call_and_rejects_the_rest():
    task = _module('task')
    from episode_runtime import Rejected, ToolCall
    path = WORKSPACE + '/out.log'
    assignment = _assignment({'path': path})
    summary = {'assignment': assignment, 'handoff_refs': ['source_handoff'], 'requested': {path: [0, None]},
               'completed': False}
    response = {'selection': {'kind': 'tool', 'tool': 'execution_results_read',
                              'arguments': {'path': path, 'offset': 0, 'limit': 10}}}
    call = task.action(response, summary, None, None)
    assert isinstance(call, ToolCall) and call.name == 'execution_results_read'
    assert call.arguments == {'operation': {'path': path, 'offset': 0, 'limit': 10}, 'assignment': assignment,
                              'handoff_refs': ['source_handoff'], 'requested': {path: [0, None]},
                              'completed': False}
    with pytest.raises(Rejected):
        task.action({'selection': {'kind': 'tool', 'tool': 'no_such_tool', 'arguments': {}}}, summary, None, None)
    with pytest.raises(Rejected):
        task.action({}, summary, None, None)
