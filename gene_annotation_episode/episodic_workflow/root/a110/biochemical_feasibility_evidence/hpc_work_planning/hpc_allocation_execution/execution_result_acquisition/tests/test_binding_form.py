"""The real episode module: its class definition checks run at import, its folder holds the ten-file set, it imports
no other episode folder, and its message, credit and controller functions behave as carried. Acquisition itself
needs the job service, which does not exist yet (BLOCKED-ON-JOB-SERVICE), and is not run here."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController, BoundedQualityYieldController

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.hpc_work_planning.'
           'hpc_allocation_execution.execution_result_acquisition')
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}
PROFILES = {'results_yield_profiles': {'native_unbounded_hpc': {'cutoff': 0.1, 'parameters': {}}},
            'task_yield_profiles': {'results:native_finite_hpc': {'cutoff': 0.1, 'parameters': {}}}}


def _module(name):
    return importlib.import_module(PACKAGE + '.' + name)


def _assignment(selector):
    return {'version': 'execution_results_assignment', 'handoff_ref': ['rec_handoff'], 'selector': selector,
            'resource_kind': 'hpc', 'acquired_record_unit': 2.0}


def test_importing_episode_runs_the_class_definition_checks():
    episode = _module('episode').ExecutionResultAcquisition
    assert episode.__bases__ == (EpisodeBinding,)
    assert episode.binding_path == ('biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution/'
                                    'execution_result_acquisition')
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


def test_return_form_declares_credit_and_finding_required_and_facts_selectable():
    fields = _module('messages.final_to_parent').RETURN_FORM.as_record()
    fields = fields['fields'] if 'fields' in fields else fields
    for name in ('credit', 'finding', 'execution_result_refs', 'execution_completed'):
        assert fields[name]['required']
    for name in ('execution_handoff_refs', 'execution_file_source_refs', 'execution_file_capture_outcomes',
                 'execution_result_origin'):
        assert fields[name]['required'] is False


def test_assignment_form_admits_the_results_assignment_and_refuses_more_fields():
    module = _module('messages.read_from_parent')
    assignment = _assignment({'path': '/run/out.log', 'offset': 10, 'limit': 100})
    assert module.ASSIGNMENT_FORM.admit(assignment, 'assignment')['handoff_ref'] == ['rec_handoff']
    with pytest.raises(FormError):
        module.ASSIGNMENT_FORM.admit({**assignment, 'private': 1}, 'assignment')


def test_read_from_parent_reads_the_requested_windows_and_refuses_typed_selectors():
    module = _module('messages.read_from_parent')
    parent = module.read_from_parent(_assignment({'paths': ['/a', '/b'], 'offset': 5}), {})
    assert parent['windows'] == [{'path': '/a', 'start': 5, 'length': None}, {'path': '/b', 'start': 5, 'length': None}]
    assert parent['handoff_ref'] == 'rec_handoff' and parent['constraints'] == {}
    with pytest.raises(NotImplementedError, match='no carried home'):
        module.read_from_parent(_assignment({'version': 'local_file_source_selector'}), {})
    with pytest.raises(ValueError, match='results_original_selector_has_no_requested_bytes'):
        module.read_from_parent(_assignment({'offset': 3}), {})
    with pytest.raises(ValueError, match='execution_results_selector_conflict'):
        module.read_from_parent(_assignment({'path': '/a', 'paths': ['/a']}), {})


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


def test_the_return_carries_the_finding_and_every_selectable_field_and_is_admitted_by_the_form():
    module = _module('messages.final_to_parent')
    window = {'path': '/a', 'offset': 0, 'returned_bytes': 10, 'size_bytes': 10}
    body = {'observation': {'state': 'completed', 'returncode': 0}, 'windows': [window], 'failures': [],
            'captured_files': []}
    summary = {'handoff_refs': ['rec_handoff'], 'windows': [{'path': '/a', 'start': 0, 'length': 10}],
               'results': [body], 'result_refs': ['rec_result'], 'result_artifact_refs': ['art_result'],
               'acquired_selector_fraction': 1.0}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0}
    selectable = [name for name, spec in module.RETURN_FORM.fields.items() if not spec.required]
    result = module.final_to_parent(summary, completion, selectable)
    assert result['credit'] == 1.0 and result['execution_completed'] is True
    assert result['execution_result_refs'] == ['rec_result'] and result['finding']['window_count'] == 1
    assert result['execution_result_origin']['value']['content_location'] == 'current_resource_filesystem'
    module.RETURN_FORM.admit(result, 'return')
    empty = module.final_to_parent({**summary, 'results': [], 'result_refs': [], 'result_artifact_refs': []},
                                   completion, ('execution_result_origin',))
    assert empty['execution_result_origin'] == {'value': None} and empty['execution_completed'] is False
    module.RETURN_FORM.admit(empty, 'return')
