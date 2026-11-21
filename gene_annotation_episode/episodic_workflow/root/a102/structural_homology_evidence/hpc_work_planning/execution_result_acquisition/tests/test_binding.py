"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode without children; no module imports another episode folder; the
episode's own form, credit, coverage, controller and return behave on real data. The acquisition itself runs on a
real job in ``test_plain_results.py``. Nothing here is faked and nothing contacts a remote service."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController, BoundedQualityYieldController

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').ExecutionResultAcquisition
CREDIT = importlib.import_module(PACKAGE + '.credit')
SUMMARY = importlib.import_module(PACKAGE + '.messages.internal_summary')
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py', 'tests/plain_world.py',
         'tests/test_plain_results.py', 'tests/test_branch_execution_result_acquisition_model_run.py'}
EPISODE_FILES = sorted(name for name in FILES if not name.startswith('tests/'))
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
FINISHED = {'detail': {'state': 'finished'}}


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


def test_the_episode_files_hold_no_stub_no_model_written_command_and_no_old_runner_text():
    for name in EPISODE_FILES:
        source = (FOLDER / name).read_text()
        for unwanted in ('NotImplementedError(\'BLOCKED', 'BLOCKED-ON-JOB-SERVICE', 'exec_command', 'observe_target',
                         'read_file', 'KNOWLEDGE_INSTRUCTIONS', 'LAUNCH_INSTRUCTIONS', 'time_accounting',
                         'yield_table', 'base64'):
            assert unwanted not in source, name + ' holds ' + unwanted


def test_the_commission_form_admits_the_native_assignment_and_read_from_parent_derives_the_inputs():
    parent_input = EPISODE.read_from_parent(admitted(known_result_refs=['artifact_1']), {})
    assert parent_input['assignment'] == {'version': 'execution_results_assignment_v1',
                                          'handoff_ref': 'source_handoff', 'selector': ASSIGNMENT['selector']}
    assert parent_input['requested'] == {PATH: [0, 100]}
    assert parent_input['known_result_refs'] == ['artifact_1'] and parent_input['acquired_record_unit'] == 2.0
    assert parent_input['resource_kind'] == 'hpc'
    assert set(parent_input) == {'assignment', 'requested', 'known_result_refs', 'acquired_record_unit',
                                 'resource_kind'}
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


def test_the_return_declares_credit_and_finding_as_required_and_controlled_fields_only():
    fields = EPISODE.return_form.fields
    assert fields['credit'].required and fields['finding'].required
    assert set(fields) == {'credit', 'finding', 'execution_handoff_refs', 'execution_job_record_refs',
                           'execution_result_refs', 'execution_completed'}
    for name in ('execution_handoff_refs', 'execution_job_record_refs', 'execution_result_refs',
                 'execution_completed'):
        assert not fields[name].required
    finding = fields['finding'].form.fields
    types = {name: field.type for name, field in finding.items()}
    assert types == {'execution_completed': 'boolean', 'acquisitions': 'integer', 'failure_count': 'integer',
                     'job_state': 'text', 'results_not_available': 'integer', 'windows_acquired': 'integer',
                     'bytes_acquired': 'integer'}
    with pytest.raises(FormError):
        fields['finding'].form.admit({'execution_completed': True, 'acquisitions': 1, 'failure_count': 0,
                                      'job_state': 'the job looked fine to me', 'results_not_available': 0,
                                      'windows_acquired': 1, 'bytes_acquired': 1}, 'finding')


def window(offset, count, size=100, path=PATH):
    return {'path': path, 'offset': offset, 'returned_bytes': count, 'size_bytes': size}


def result(ref, windows, *, initial=False):
    return {'ref': ref, 'artifact_ref': 'artifact_' + ref, 'initial': initial, 'windows': windows}


def summary(results, requested=None):
    return {'requested': {PATH: [0, 100]} if requested is None else requested, 'results': results,
            'acquired_record_unit': 2.0}


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


def test_credit_is_not_bounded():
    assert CREDIT.credit({**summary([result('a', [window(0, 100)])]), 'acquired_record_unit': 5.0}, None) == 5.0


def test_completion_needs_the_closure_of_a_finished_job_and_every_requested_byte_without_a_gap():
    assert SUMMARY._complete({PATH: [0, 100]}, FINISHED, []) is False
    assert SUMMARY._complete({PATH: [0, 100]}, FINISHED, [result('a', [window(0, 100)])]) is True
    assert SUMMARY._complete({PATH: [0, 100]}, None, [result('a', [window(0, 100)])]) is False
    assert SUMMARY._complete({PATH: [0, 100]}, {'detail': {'state': 'failed'}},
                             [result('a', [window(0, 100)])]) is False
    assert SUMMARY._complete({PATH: [0, 100]}, FINISHED, [result('a', [window(0, 40)]),
                                                          result('b', [window(60, 40)])]) is False
    assert SUMMARY._complete({PATH: [0, 100]}, FINISHED, [result('a', [window(0, 60)]),
                                                          result('b', [window(50, 50)])]) is True
    assert SUMMARY._complete({PATH: [10, 20]}, FINISHED, [result('a', [window(10, 20)])]) is True
    assert SUMMARY._complete({PATH: [0, None]}, FINISHED, [result('a', [window(0, 40, size=40)])]) is True


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
