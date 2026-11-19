"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode without children; no module imports another episode folder; the
episode's own form, credit, coverage, controller, report and blocked service calls behave on real data. Nothing here
is faked and nothing contacts a remote service."""
import ast
import asyncio
import base64
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController, BoundedQualityYieldController

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').ExecutionResultAcquisition
TASK = importlib.import_module(PACKAGE + '.task')
CREDIT = importlib.import_module(PACKAGE + '.credit')
SUMMARY = importlib.import_module(PACKAGE + '.messages.internal_summary')
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
ASSIGNMENT = {'version': 'execution_results_assignment_v1', 'handoff_ref': ['source_handoff'],
              'selector': {'path': '/lus/flare/projects/BioReason-Aurora-Test/chian/runs/job/out.log',
                           'offset': 0, 'limit': 100},
              'acquired_record_unit': 2.0, 'resource_kind': 'hpc'}
PATH = ASSIGNMENT['selector']['path']
SETTINGS = {'results_yield_profiles': {'native_unbounded_hpc': {'cutoff': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}},
            'task_yield_profiles': {'results:native_finite_hpc': {'cutoff': 0.1,
                                                                   'parameters': {'uncertainty_alpha': 0.1}}}}
ASSIGNMENT_SETTINGS_LOCAL = {'results:native_finite_local': {'cutoff': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts}


def admitted(**changes):
    return EPISODE.assignment_form.admit({**ASSIGNMENT, **changes}, 'test')


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {}
    assert tuple(EPISODE.services) == ('job_access',)
    assert set(EPISODE.tools) == {'execution_results_status', 'execution_results_collect', 'execution_results_read'}


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


def test_the_commission_form_admits_the_native_assignment_and_read_from_parent_derives_the_inputs():
    parent_input = EPISODE.read_from_parent(admitted(known_result_refs=['artifact_1']), {'purpose': 'fetch'})
    assert parent_input['assignment'] == {'version': 'execution_results_assignment_v1',
                                          'handoff_ref': 'source_handoff', 'selector': ASSIGNMENT['selector']}
    assert parent_input['requested'] == {PATH: [0, 100]}
    assert parent_input['known_result_refs'] == ['artifact_1'] and parent_input['acquired_record_unit'] == 2.0
    assert parent_input['resource_kind'] == 'hpc'
    assert parent_input['message'] == {'purpose': 'fetch'}
    assert EPISODE.read_from_parent(admitted(selector={'paths': ['/a', '/b']}), {})['requested'] == {
        '/a': [0, None], '/b': [0, None]}
    with pytest.raises(FormError, match='unknown_field'):
        EPISODE.assignment_form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    with pytest.raises(FormError):
        EPISODE.assignment_form.admit({**ASSIGNMENT, 'version': 'other'}, 'test')


def test_a_wrong_assignment_raises_where_it_is_read():
    with pytest.raises(ValueError, match='execution_results_one_handoff_required'):
        EPISODE.read_from_parent(admitted(handoff_ref=['a', 'b']), {})
    with pytest.raises(ValueError, match='explicit_positive_operational_credit_units_required'):
        EPISODE.read_from_parent(admitted(acquired_record_unit=0), {})
    with pytest.raises(ValueError, match='ambiguous_execution_results_selector'):
        EPISODE.read_from_parent(admitted(selector={'paths': [PATH], 'path': PATH}), {})
    with pytest.raises(ValueError, match='execution_results_paths_required'):
        EPISODE.read_from_parent(admitted(selector={'offset': 0}), {})
    with pytest.raises(NotImplementedError, match='result_selector_kind_not_carried:protein_structure_result_selector_v1'):
        EPISODE.read_from_parent(admitted(selector={'version': 'protein_structure_result_selector_v1'}), {})


def test_the_return_declares_credit_and_finding_as_required_and_the_old_fact_sources_as_selectable():
    fields = EPISODE.return_form.fields
    assert fields['credit'].required and fields['finding'].required
    for name in ('execution_file_source_refs', 'execution_file_capture_outcomes', 'execution_handoff_refs',
                 'execution_result_refs', 'execution_completed', 'execution_result_origin',
                 'execution_protein_structure_projections', 'execution_protein_structure_saved_sheets',
                 'execution_protein_structure_sequences', 'execution_protein_structure_failures'):
        assert not fields[name].required


def window(offset, count, size=100, path=PATH):
    return {'path': path, 'offset': offset, 'returned_bytes': count, 'size_bytes': size}


def result(ref, windows, *, initial=False, state='completed', returncode=0):
    return {'ref': ref, 'initial': initial, 'failures': 0, 'windows': windows,
            'observation': {'state': state, 'returncode': returncode}}


def summary(results, requested=None):
    requested = {PATH: [0, 100]} if requested is None else requested
    missing = SUMMARY.uncovered_paths(requested, results)
    return {'requested': requested, 'results': results, 'acquired_record_unit': 2.0, 'uncovered_paths': missing,
            'completed': not missing, 'facts': {**SUMMARY.facts({'handoff_ref': 'h'}, results, None),
                                                'execution_completed': not missing}}


def test_credit_is_the_unit_times_the_newly_covered_share_and_bytes_are_credited_once():
    assert EPISODE.credit(summary([]), None) == 0.0
    assert EPISODE.credit(summary([result('a', [window(0, 50)])]), None) == pytest.approx(1.0)
    overlapping = [result('a', [window(0, 50)]), result('b', [window(25, 50)])]
    assert EPISODE.credit(summary(overlapping), None) == pytest.approx(1.5)
    assert EPISODE.credit(summary(overlapping + [result('c', [window(0, 100)])]), None) == pytest.approx(2.0)


def test_bytes_the_parent_already_held_earn_nothing_and_an_open_ended_path_counts_up_to_the_observed_size():
    known = result('k', [window(0, 40)], initial=True)
    assert EPISODE.credit(summary([known]), None) == 0.0
    assert EPISODE.credit(summary([known, result('a', [window(40, 60)])]), None) == pytest.approx(1.2)
    open_ended = {PATH: [0, None]}
    assert EPISODE.credit(summary([result('a', [window(0, 30, size=60)])], open_ended), None) == pytest.approx(1.0)


def test_credit_is_not_bounded_and_the_file_has_no_stub():
    source = (FOLDER / 'credit.py').read_text()
    assert 'NotImplementedError' not in source
    unit = 5.0
    assert CREDIT.credit({**summary([result('a', [window(0, 100)])]), 'acquired_record_unit': unit}, None) == 5.0


def test_completion_needs_a_successful_attempt_observation_and_every_requested_byte_without_a_gap():
    assert SUMMARY.uncovered_paths({PATH: [0, 100]}, []) == [PATH]
    assert SUMMARY.uncovered_paths({PATH: [0, 100]}, [result('a', [window(0, 100)])]) == []
    assert SUMMARY.uncovered_paths({PATH: [0, 100]}, [result('a', [window(0, 100)], state='running',
                                                              returncode=None)]) == [PATH]
    assert SUMMARY.uncovered_paths({PATH: [0, 100]}, [result('a', [window(0, 40)]),
                                                      result('b', [window(60, 40)])]) == [PATH]
    assert SUMMARY.uncovered_paths({PATH: [0, 100]}, [result('a', [window(0, 60)]),
                                                      result('b', [window(50, 50)])]) == []
    assert SUMMARY.uncovered_paths({PATH: [10, 20]}, [result('a', [window(10, 20)])]) == []
    assert SUMMARY.uncovered_paths({PATH: [0, None]}, [result('a', [window(0, 40, size=40)])]) == []


def test_the_controller_is_bounded_for_a_finite_selector_and_accumulating_for_an_open_ended_one():
    parent_input = EPISODE.read_from_parent(admitted(), {})
    bounded = EPISODE.yield_controller(0.0, SETTINGS, parent_input)
    assert isinstance(bounded, BoundedQualityYieldController) and bounded.maximum_credit == 2.0
    open_input = EPISODE.read_from_parent(admitted(selector={'paths': [PATH]}), {})
    assert isinstance(EPISODE.yield_controller(0.0, SETTINGS, open_input), AccumulationYieldController)
    local = EPISODE.read_from_parent(admitted(resource_kind='local'), {})
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required:results:native_finite_local'):
        EPISODE.yield_controller(0.0, SETTINGS, local)
    assert isinstance(EPISODE.yield_controller(0.0, {**SETTINGS, 'task_yield_profiles': ASSIGNMENT_SETTINGS_LOCAL}, local),
                      BoundedQualityYieldController)
    with pytest.raises(FormError):
        EPISODE.assignment_form.admit({**ASSIGNMENT, 'resource_kind': 'api'}, 'test')
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required:results:native_finite_hpc'):
        EPISODE.yield_controller(0.0, {**SETTINGS, 'task_yield_profiles': {}}, parent_input)
    with pytest.raises(ValueError, match='results_original_task_yield_profile_required:native_unbounded_hpc'):
        EPISODE.yield_controller(0.0, {**SETTINGS, 'results_yield_profiles': {}}, open_input)


def test_the_selection_schema_and_its_strict_transport_build_and_the_windows_follow_the_request():
    schema = TASK.selection_schema()
    assert len(schema['properties']['selection']['anyOf']) == 3 and TASK.generation_schema(schema)
    requested = {PATH: (0, 100), '/b': (0, None)}
    assert TASK.requested_windows('execution_results_status', None, requested, 10) == []
    assert TASK.requested_windows('execution_results_collect', None, requested, 10) == [
        {'path': PATH, 'offset': 0, 'limit': 10}, {'path': '/b', 'offset': 0, 'limit': 10}]
    assert TASK.requested_windows('execution_results_collect', None, {PATH: (0, 4)}, 10) == [
        {'path': PATH, 'offset': 0, 'limit': 4}]
    inside = {'path': PATH, 'offset': 20, 'limit': 30}
    assert TASK.requested_windows('execution_results_read', inside, requested, 10) == [inside]
    for window_ in ({'path': '/other', 'offset': 0, 'limit': 1}, {'path': PATH, 'offset': 90, 'limit': 20}):
        with pytest.raises(ValueError, match='execution_results_selector_conflict'):
            TASK.requested_windows('execution_results_read', window_, requested, 10)


def test_a_result_body_is_validated_against_the_assignment_and_the_requested_windows():
    assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': 'h', 'selector': {'path': PATH}}
    data = b'abcde'
    body = {'version': TASK.RESULT_VERSION, 'run_id': 'r', 'episode_id': 'e', 'assignment': assignment,
            'operation_key': 'k', 'tool_name': 'execution_results_collect', 'arguments': {}, 'target': {},
            'observation': {'state': 'completed', 'returncode': 0},
            'windows': [{'path': PATH, 'offset': 0, 'returned_bytes': 5, 'size_bytes': 5,
                         'bytes_base64': base64.b64encode(data).decode()}], 'failures': [],
            'acquisition_origin': TASK.NATIVE_RESULT_ORIGIN}
    TASK.validate_result_body(body, run_id='r', assignment=assignment, requested={PATH: (0, None)})
    with pytest.raises(ValueError, match='execution_result_window_conflict'):
        TASK.validate_result_body(body, run_id='r', assignment=assignment, requested={PATH: (0, 3)})
    with pytest.raises(ValueError, match='execution_result_selector_conflict'):
        TASK.validate_result_body(body, run_id='r', assignment=assignment, requested={'/other': (0, None)})
    with pytest.raises(ValueError, match='invalid_execution_result_information'):
        TASK.validate_result_body({**body, 'run_id': 'x'}, run_id='r', assignment=assignment, requested={PATH: (0, None)})


def test_reading_the_handoff_and_the_job_access_calls_are_blocked_and_say_which_call_they_wanted():
    with pytest.raises(NotImplementedError, match=r'BLOCKED-ON-JOB-SERVICE: job ledger handoff record; wanted call'):
        TASK.handoff_target(None, 'source_handoff')
    with pytest.raises(NotImplementedError, match=r'BLOCKED-ON-JOB-SERVICE: job_access; wanted call.*observe_target'):
        asyncio.run(TASK.observe_target({}, None))
    with pytest.raises(NotImplementedError, match=r'BLOCKED-ON-JOB-SERVICE: job_access; wanted call.*read_file'):
        asyncio.run(TASK.read_window({}, {'path': PATH, 'offset': 0, 'limit': 1}, 'key', None))


def test_the_return_carries_credit_the_finding_and_every_selectable_fact_and_the_form_admits_it():
    state = {**summary([result('a', [window(0, 100)])]), 'requested': {PATH: [0, 100]}}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 2.0}
    names = tuple(name for name in EPISODE.return_form.fields if name not in ('credit', 'finding'))
    returned = EPISODE.final_to_parent(state, completion, names)
    assert returned['credit'] == 2.0 and returned['finding']['completed'] is True
    assert returned['execution_completed'] is True and returned['execution_result_refs'] == ['a']
    assert returned['execution_result_origin'] and returned['execution_file_source_refs'] == []
    EPISODE.return_form.admit(returned, 'return')
    EPISODE.return_form.admit(EPISODE.final_to_parent(state, completion, ()), 'return')
