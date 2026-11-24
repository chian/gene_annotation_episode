"""The A107 result acquisition episode is a private binding in the ten-file form, reads a real assignment, offers the
operations of a plain file result, prices acquisitions by requested-byte coverage and reports through its real
return form. The plain file results of a job are run for real in ``test_plain_results.py``; the forms and the pure
functions are checked here."""
import ast
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController, BoundedQualityYieldController

from .. import credit as credit_file
from .. import episode as episode_module
from .. import task as task_file
from ..episode import ExecutionResultAcquisition
from ..goal import BINDING_PATH
from ..messages.final_to_parent import FINDING_FORM, RETURN_FORM, final_to_parent
from ..messages.read_from_parent import ASSIGNMENT_FORM, read_from_parent
from ..yield_estimator import yield_controller

FOLDER = Path(episode_module.__file__).parent
PACKAGE = episode_module.__name__.rsplit('.', 1)[0]
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}


def test_the_class_inherits_only_the_system_episode_type():
    assert ExecutionResultAcquisition.__bases__ == (EpisodeBinding,)
    assert ExecutionResultAcquisition.binding_path == BINDING_PATH
    assert BINDING_PATH == 'partner_presence_evidence/execution_result_acquisition'
    assert dict(ExecutionResultAcquisition.child_slots) == {}
    assert tuple(ExecutionResultAcquisition.services) == ('job_access',)
    assert set(ExecutionResultAcquisition.tools) == {'execution_results_status', 'execution_results_collect',
                                                     'execution_results_read'}


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


def test_the_return_form_declares_credit_and_finding_and_only_controlled_selectable_fields():
    required = {name for name, spec in RETURN_FORM.fields.items() if spec.required}
    assert required == {'credit', 'finding'}
    selectable = {name: spec.type for name, spec in RETURN_FORM.fields.items() if not spec.required}
    assert selectable == {'execution_handoff_refs': 'record_refs', 'execution_job_record_refs': 'record_refs',
                          'execution_result_refs': 'record_refs', 'execution_completed': 'boolean'}
    # The finding is counts, a flag and one fixed vocabulary: no open text, record or list.
    assert {name: spec.type for name, spec in FINDING_FORM.fields.items()} == {
        'execution_completed': 'boolean', 'acquisitions': 'integer',
        'failure_count': 'integer', 'job_state': 'text', 'results_not_available': 'integer',
        'windows_acquired': 'integer', 'bytes_acquired': 'integer'}
    assert 'finished' in FINDING_FORM.fields['job_state'].options


def _target(**changes):
    value = {'version': 'execution_target', 'handle': 'handoff_1', 'run_id': 'run', 'resource_id': 'local',
             'resource_kind': 'local', 'execution_id': 'exec_1', 'request_sha256': '0' * 64,
             'origin_episode_id': 'episode_1',
             'assignment': {'resource_id': 'local', 'resource_kind': 'local', 'workspace': '/work/space',
                            'requested_job': {'argv': ['/bin/true'], 'environment': {}}, 'endpoint': 'usable_handoff',
                            'constraints': {}},
             'scope': {}}
    value.update(changes)
    return value


def _assignment(**changes):
    value = {'version': 'execution_results_assignment', 'handoff_ref': 'handoff_1',
             'selector': {'paths': ['/work/space/out.txt'], 'path': '/work/space/logs/log.txt', 'offset': 10,
                          'limit': 90},
             'target': _target(), 'acquired_record_unit': 2.0}
    value.update(changes)
    return value


def _admitted(**changes):
    return ASSIGNMENT_FORM.admit(_assignment(**changes), 'assignment')


def test_the_assignment_is_read_once_and_gives_the_intervals_the_names_and_the_unit():
    parent_input = read_from_parent(_admitted(), {})
    assert parent_input['requested'] == {'/work/space/out.txt': [0, None], '/work/space/logs/log.txt': [10, 90]}
    # The job service names a result file by its path inside the job's directory.
    assert parent_input['result_names'] == {'/work/space/out.txt': 'out.txt',
                                            '/work/space/logs/log.txt': 'logs/log.txt'}
    assert parent_input['acquired_record_unit'] == 2.0 and parent_input['target']['handle'] == 'handoff_1'


def test_a_wrong_commission_fails():
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit(_assignment(version='other'), 'assignment')
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit(_assignment(scientific_task={'scientific_question': 'free text'}), 'assignment')
    with pytest.raises(ValueError, match='execution_result_target_conflict'):
        read_from_parent(_admitted(handoff_ref='another'), {})
    with pytest.raises(ValueError, match='execution_results_paths_required'):
        read_from_parent(_admitted(selector={'offset': 1}), {})
    with pytest.raises(ValueError, match='practical_write_outside_workspace'):
        read_from_parent(_admitted(selector={'paths': ['/elsewhere/out.txt']}), {})
    with pytest.raises(ValueError, match='explicit_positive_operational_credit_units_required'):
        read_from_parent(_admitted(acquired_record_unit=0), {})


def test_the_families_that_are_in_no_place_now_raise_where_their_old_class_was_called():
    with pytest.raises(NotImplementedError, match='unplaced:LocalFileSourceResults.selector'):
        read_from_parent(_admitted(selector={'version': 'local_file_source_selector', 'files': []}), {})
    api = _target(resource_kind='api', assignment={'version': 'api_service_assignment', 'service': 'ncbi_blast'})
    with pytest.raises(NotImplementedError, match='unplaced:api_execution.validate_result_selector'):
        read_from_parent(_admitted(target=api, selector={'version': 'x'}), {})
    typed = {**_target()['assignment'], 'requested_job': {'native_hmmer': {'program': 'phmmer'}}}
    with pytest.raises(Exception, match='native_hmmer_result_selector_invalid'):
        read_from_parent(_admitted(target=_target(assignment=typed), selector={'paths': ['/work/space/o']}), {})
    infernal = {**_target()['assignment'], 'requested_job': {'native_infernal': {}}}
    with pytest.raises(NotImplementedError, match='unplaced:native_infernal.result_selector'):
        read_from_parent(_admitted(target=_target(assignment=infernal), selector={'paths': ['/work/space/o']}), {})


def test_the_yield_controller_is_accumulation_for_an_unbounded_selector_and_bounded_for_a_finite_one():
    unbounded = read_from_parent(_admitted(selector={'paths': ['/work/space/out.txt']}), {})
    settings = {'results_yield_profiles': {'native_unbounded_local': {'cutoff': 0.1, 'parameters': {}}},
                'task_yield_profiles': {'results:native_finite_local': {'cutoff': 0.2, 'parameters': {}}}}
    assert isinstance(yield_controller(0.0, settings, unbounded), AccumulationYieldController)
    finite = read_from_parent(_admitted(selector={'path': '/work/space/log.txt', 'offset': 0, 'limit': 50}), {})
    controller = yield_controller(0.0, settings, finite)
    assert isinstance(controller, BoundedQualityYieldController) and controller.maximum_credit == 2.0
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required'):
        yield_controller(0.0, {**settings, 'task_yield_profiles': {}}, finite)
    with pytest.raises(ValueError, match='results_original_task_yield_profile_required'):
        yield_controller(0.0, {**settings, 'results_yield_profiles': {}}, unbounded)


def _window(path, offset, size, total):
    return {'path': path, 'artifact_ref': 'artifact_of_' + path, 'offset': offset, 'returned_bytes': size,
            'size_bytes': total, 'sha256': '0' * 64}


def _summary(**changes):
    value = {'acquired_record_unit': 2.0,
             'requested': {'/a': [0, 100], '/b': [0, None]},
             'job': {'closed': True, 'last_observed_state': 'finished'},
             'fetched_files': {'/a': {'ref': 'artifact_of_/a', 'bytes': 100}},
             'results': [{'ref': 'r0', 'artifact_ref': 'b0', 'initial': True,
                          'windows': [_window('/a', 0, 25, 100)]},
                         {'ref': 'r1', 'artifact_ref': 'b1', 'initial': False,
                          'windows': [_window('/a', 20, 30, 100), _window('/b', 0, 40, 80)]}]}
    value.update(changes)
    return value


def test_the_credit_counts_each_new_requested_byte_position_once_as_the_mean_over_paths():
    summary = _summary()
    # /a: bytes 0-25 were already known, 20-50 now cover 25 new positions of 100; /b: 40 of the file's 80 bytes
    expected = 2.0 * (0.25 + 0.5) / 2
    assert credit_file.credit(summary, None) == pytest.approx(expected)
    assert credit_file.credit({**summary, 'results': summary['results'][:1]}, None) == 0.0


def test_the_operations_offered_follow_the_job():
    names = lambda summary: [entry['name'] for entry in task_file._catalog(summary)]
    assert names(_summary(job={'closed': False}, fetched_files={})) == ['execution_results_status',
                                                                         'execution_results_collect']
    assert names(_summary()) == ['execution_results_status', 'execution_results_read']
    read = task_file._catalog(_summary())[1]
    assert read['input_schema']['properties']['path'] == {'enum': ['/a']}
    assert names(_summary(fetched_files={})) == ['execution_results_status']        # a cancelled job


def _closed_summary(**changes):
    value = {'execution_progress': {'execution_handoff_refs': ['handoff_1'],
                                    'execution_job_record_refs': ['row_check', 'row_closure'],
                                    'execution_result_refs': ['r1', 'b1', 'artifact_of_/a', 'artifact_of_/b'],
                                    'execution_completed': False},
             'execution_completed': False,
             'acquisitions': [
                 {'tool': 'execution_results_collect', 'status': 'failed', 'failure_code': 'results_not_available'},
                 {'tool': 'execution_results_status', 'status': 'completed', 'state': 'finished',
                  'result_available': True},
                 {'tool': 'execution_results_collect', 'status': 'completed', 'result_ref': 'r1', 'windows': []},
                 {'tool': 'execution_results_read', 'status': 'invalid', 'window': {},
                  'failure_code': 'execution_results_selector_conflict'}]}
    return _summary(**{**value, **changes})


def test_the_return_is_the_credit_the_counts_and_the_selected_references():
    summary = _closed_summary()
    completion = {'ended_by': 'yield_stop', 'units_consumed': 4, 'credit': 1.5}
    names = ['execution_handoff_refs', 'execution_result_refs', 'execution_completed']
    result = final_to_parent(summary, completion, names)
    assert result['credit'] == 1.5
    assert result['finding'] == {'execution_completed': False, 'acquisitions': 2,
                                 'failure_count': 2, 'job_state': 'finished', 'results_not_available': 1,
                                 'windows_acquired': 2, 'bytes_acquired': 70}
    assert result['execution_result_refs'] == ['r1', 'b1', 'artifact_of_/a', 'artifact_of_/b']
    assert set(result) == {'credit', 'finding', *names}
    RETURN_FORM.select(names).admit(result, 'result')
    every = [name for name in RETURN_FORM.fields if name not in ('credit', 'finding')]
    RETURN_FORM.select(every).admit(final_to_parent(summary, completion, every), 'return')
