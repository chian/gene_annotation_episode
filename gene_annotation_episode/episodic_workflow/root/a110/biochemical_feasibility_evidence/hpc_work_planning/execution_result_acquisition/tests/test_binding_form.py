"""The real episode module: its class definition checks run at import, its folder holds the ten-file set, it imports
no other episode folder, and its message, credit and controller functions behave on real data. The acquisition
itself runs on a real job in ``test_plain_results.py``."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController, BoundedQualityYieldController

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.hpc_work_planning.'
           'execution_result_acquisition')
BINDING_PATH = 'biochemical_feasibility_evidence/hpc_work_planning/execution_result_acquisition'
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}
PROFILES = {'results_yield_profiles': {'native_unbounded_hpc': {'cutoff': 0.1, 'parameters': {}}},
            'task_yield_profiles': {'results:native_finite_hpc': {'cutoff': 0.1, 'parameters': {}}}}
FINISHED = {'detail': {'state': 'finished'}}


def _module(name):
    return importlib.import_module(PACKAGE + '.' + name)


def _assignment(selector):
    return {'version': 'execution_results_assignment_v1', 'handoff_ref': ['rec_handoff'], 'selector': selector,
            'resource_kind': 'hpc', 'acquired_record_unit': 2.0}


def test_importing_episode_runs_the_class_definition_checks():
    episode = _module('episode').ExecutionResultAcquisition
    assert episode.__bases__ == (EpisodeBinding,)
    assert episode.binding_path == BINDING_PATH
    assert dict(episode.child_slots) == {}
    assert set(episode.tools) == {'execution_results_status', 'execution_results_collect', 'execution_results_read'}
    assert tuple(episode.services) == ('job_access',)


def test_folder_holds_exactly_the_ten_file_set_without_child_message_files():
    files = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*.py')
             if '__pycache__' not in path.parts and 'tests' not in path.relative_to(FOLDER).parts}
    assert files == TEN_FILES


def test_no_module_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in path.parts or 'tests' in relative.parts:
            continue
        depth = len(relative.parts)
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                if node.level >= depth + 1:
                    raise AssertionError(str(relative) + ' imports outside its folder')
                names = [node.module or '']
            elif isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            else:
                continue
            for name in names:
                assert not name.startswith('gene_annotation_episode.episodic_workflow.root'), (relative, name)


def test_the_episode_files_hold_no_stub_no_model_written_command_and_no_old_runner_text():
    for name in sorted(TEN_FILES):
        source = (FOLDER / name).read_text()
        for unwanted in ('BLOCKED-ON-JOB-SERVICE', 'exec_command', 'observe_target', 'read_file', '_read_target',
                         'describe_result_target', 'LaunchInstructions', 'ToolKnowledge', 'time_accounting',
                         'credit_binding', 'already_completed'):
            assert unwanted not in source, name + ' holds ' + unwanted


def test_return_form_declares_credit_finding_and_the_results_required_and_controlled_fields_only():
    form = _module('messages.final_to_parent').RETURN_FORM
    assert set(form.fields) == {'credit', 'finding', 'execution_result_refs', 'execution_result_artifact_refs',
                                'execution_completed', 'execution_handoff_refs', 'execution_job_record_refs'}
    for name in ('credit', 'finding', 'execution_result_refs', 'execution_result_artifact_refs',
                 'execution_completed'):
        assert form.fields[name].required
    for name in ('execution_handoff_refs', 'execution_job_record_refs'):
        assert form.fields[name].required is False
    finding = form.fields['finding'].form
    assert {name: field.type for name, field in finding.fields.items()} == {
        'execution_completed': 'boolean', 'acquisitions': 'integer', 'failure_count': 'integer',
        'job_state': 'text', 'results_not_available': 'integer', 'windows_acquired': 'integer',
        'bytes_acquired': 'integer'}
    with pytest.raises(FormError):
        finding.admit({'execution_completed': True, 'acquisitions': 1, 'failure_count': 0,
                       'job_state': 'the job looked fine to me', 'results_not_available': 0,
                       'windows_acquired': 1, 'bytes_acquired': 1}, 'finding')


def test_assignment_form_admits_the_results_assignment_and_refuses_more_fields_and_another_kind():
    module = _module('messages.read_from_parent')
    assignment = _assignment({'path': '/run/out.log', 'offset': 10, 'limit': 100})
    assert module.ASSIGNMENT_FORM.admit(assignment, 'assignment')['handoff_ref'] == ['rec_handoff']
    with pytest.raises(FormError):
        module.ASSIGNMENT_FORM.admit({**assignment, 'private': 1}, 'assignment')
    with pytest.raises(FormError):
        module.ASSIGNMENT_FORM.admit({**assignment, 'constraints': {}}, 'assignment')
    with pytest.raises(FormError):
        module.ASSIGNMENT_FORM.admit({**assignment, 'resource_kind': 'api'}, 'assignment')


def test_read_from_parent_reads_the_requested_windows_and_refuses_typed_selectors():
    module = _module('messages.read_from_parent')
    parent = module.read_from_parent(_assignment({'paths': ['/a', '/b'], 'offset': 5}), {})
    assert parent['windows'] == [{'path': '/a', 'start': 5, 'length': None}, {'path': '/b', 'start': 5, 'length': None}]
    assert parent['assignment'] == {'version': 'execution_results_assignment_v1', 'handoff_ref': 'rec_handoff',
                                    'selector': {'paths': ['/a', '/b'], 'offset': 5}}
    assert set(parent) == {'assignment', 'windows', 'resource_kind', 'acquired_record_unit'}
    with pytest.raises(NotImplementedError, match='no carried home'):
        module.read_from_parent(_assignment({'version': 'local_file_source_selector_v1'}), {})
    with pytest.raises(ValueError, match='results_original_selector_has_no_requested_bytes'):
        module.read_from_parent(_assignment({'offset': 3}), {})
    with pytest.raises(ValueError, match='execution_results_selector_conflict'):
        module.read_from_parent(_assignment({'path': '/a', 'paths': ['/a']}), {})
    with pytest.raises(ValueError, match='results_assignment_requires_exactly_one_handoff'):
        module.read_from_parent({**_assignment({'path': '/a'}), 'handoff_ref': ['a', 'b']}, {})


def test_credit_counts_each_received_byte_position_once_times_the_unit():
    credit = _module('credit')
    requested = [{'path': '/a', 'start': 0, 'length': 100}]
    window = lambda offset, size: {'path': '/a', 'offset': offset, 'returned_bytes': size, 'size_bytes': 100}
    summary = {'acquired_record_unit': 2.0, 'windows': requested,
               'results': [{'windows': [window(0, 50)]}, {'windows': [window(25, 50)]}]}
    assert credit.credit(summary, None) == pytest.approx(2.0 * 0.75)
    assert credit.credit({**summary, 'results': []}, None) == 0.0


def test_yield_controller_is_accumulation_for_an_unbounded_selector_and_bounded_for_a_finite_one():
    module = _module('yield_estimator')
    parent = _module('messages.read_from_parent')
    unbounded = parent.read_from_parent(_assignment({'path': '/a'}), {})
    finite = parent.read_from_parent(_assignment({'path': '/a', 'limit': 10}), {})
    assert isinstance(module.yield_controller(0.0, PROFILES, unbounded), AccumulationYieldController)
    controller = module.yield_controller(0.0, PROFILES, finite)
    assert isinstance(controller, BoundedQualityYieldController) and controller.maximum_credit == 2.0
    with pytest.raises(ValueError, match='results_original_task_yield_profile_required'):
        module.yield_controller(0.0, {}, unbounded)


def test_completion_needs_the_closure_of_a_finished_job_and_every_requested_window_covered():
    module = _module('messages.internal_summary')
    requested = [{'path': '/a', 'start': 0, 'length': 100}]
    window = lambda offset, size: {'path': '/a', 'offset': offset, 'returned_bytes': size, 'size_bytes': 100}
    result = lambda *windows: {'windows': list(windows)}
    assert module.native_results_complete(requested, FINISHED, [result(window(0, 60)), result(window(50, 50))])
    assert not module.native_results_complete(requested, FINISHED, [result(window(0, 60))])
    assert not module.native_results_complete(requested, {'detail': {'state': 'failed'}}, [result(window(0, 100))])
    assert not module.native_results_complete(requested, None, [result(window(0, 100))])
    assert not module.native_results_complete(requested, FINISHED, [])
