"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks, so the import is
the class-definition check; the folder holds exactly the ten-file set of an episode without children; no module
imports another episode folder; the episode's own forms, credit, coverage, controller and return behave on real
data. Nothing contacts a remote service."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import ChoiceField, FormError
from yield_control import AccumulationYieldController, BoundedQualityYieldController

PACKAGE = __name__.rsplit('.tests.', 1)[0]
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py', 'tests',
             'messages'}
MESSAGE_FILES = {'__init__.py', 'read_from_parent.py', 'internal_summary.py', 'final_to_parent.py'}
WORKSPACE = '/lus/flare/projects/work'
REQUIRED = {'credit', 'finding'}
SELECTABLE = {'execution_handoff_refs', 'execution_job_record_refs', 'execution_result_refs',
              'execution_result_artifact_refs', 'execution_completed'}
SELECTED = ['execution_handoff_refs', 'execution_result_refs', 'execution_completed']
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


def test_the_return_form_declares_credit_finding_and_controlled_fields_only(episode):
    form = episode.ExecutionResultAcquisition.return_form
    assert {name for name, spec in form.fields.items() if spec.required} == REQUIRED
    assert {name for name, spec in form.fields.items() if not spec.required} == SELECTABLE
    assert form.fields['credit'].type == 'number'
    # No open field: counts, booleans, one fixed vocabulary and record references.
    finding = _module('messages.final_to_parent').FINDING_FORM
    assert {name: spec.type for name, spec in finding.fields.items()} == {
        'execution_completed': 'boolean', 'acquisitions': 'integer', 'failure_count': 'integer',
        'job_state': 'text', 'results_not_available': 'integer', 'windows_acquired': 'integer',
        'bytes_acquired': 'integer'}
    assert isinstance(finding.fields['job_state'], ChoiceField)
    assert finding.fields['job_state'].options == ('not_observed', 'queued', 'running', 'finished', 'failed',
                                                    'cancelled', 'unknown')
    assert {spec.type for name, spec in form.fields.items() if name not in ('credit', 'finding')} == {
        'record_refs', 'boolean'}
    assert form.select(['execution_job_record_refs']).fields['execution_job_record_refs'].required
    for removed in ('execution_result_origin', 'execution_file_capture_outcomes', 'execution_blast_hsps'):
        with pytest.raises(FormError):
            form.select([removed])


def test_the_assignment_form_names_the_handoff_row_the_selector_and_the_job_directory(episode):
    fields = episode.ExecutionResultAcquisition.assignment_form.fields
    assert fields['handoff_ref'].type == 'record_refs' and fields['selector'].type == 'record'
    assert fields['resource_kind'].options == ('local', 'hpc') and fields['workspace'].type == 'text'
    assert fields['initial_result_refs'].type == 'record_refs' and not fields['initial_result_refs'].required
    assert fields['initial_result_artifact_refs'].type == 'record_refs'
    with pytest.raises(FormError):                                    # an API target is no commission of this child
        episode.ExecutionResultAcquisition.assignment_form.admit(
            {**_assignment({'paths': [WORKSPACE + '/out.log']}), 'resource_kind': 'api'}, 'assignment')


def test_read_from_parent_turns_the_selector_into_requested_windows_and_result_names(episode):
    read = _module('messages.read_from_parent').read_from_parent
    path = WORKSPACE + '/out.log'
    other = WORKSPACE + '/logs/err.log'
    parent_input = read(_assignment({'paths': [other], 'path': path, 'offset': 10, 'limit': 20}), {})
    assert parent_input['requested'] == {other: [0, None], path: [10, 20]}
    assert parent_input['result_names'] == {other: 'logs/err.log', path: 'out.log'}
    assert parent_input['assignment']['handoff_ref'] == 'source_handoff'
    assert parent_input['assignment']['resource_kind'] == 'hpc' and parent_input['initial_result_refs'] == []
    assert 'scientific_task' not in parent_input
    with pytest.raises(ValueError, match='practical_write_outside_workspace'):
        read(_assignment({'path': '/etc/passwd'}), {})
    with pytest.raises(ValueError, match='execution_results_paths_required'):
        read(_assignment({'offset': 3}), {})
    with pytest.raises(ValueError):                                   # a typed selector is not a plain file selector
        read(_assignment({'version': 'bvbrc_minhash_result_selector_v2'}), {})
    with pytest.raises(ValueError):                                   # exactly one handoff row
        read({**_assignment({'path': path}), 'handoff_ref': ['source_a', 'source_b']}, {})


def _window(path, offset, count, size):
    return {'path': path, 'offset': offset, 'returned_bytes': count, 'size_bytes': size}


def test_credit_counts_each_new_byte_position_once():
    credit = _module('credit')
    path = WORKSPACE + '/out.log'
    requested = {path: [0, 100]}
    initial = [{'windows': [_window(path, 0, 20, 100)]}]
    own = [{'windows': [_window(path, 10, 30, 100)]}, {'windows': [_window(path, 20, 30, 100)]}]
    summary = {'acquired_record_unit': 2.0, 'requested': requested, 'initial': initial, 'own': own}
    assert credit.credit(summary, None) == pytest.approx(2.0 * 30 / 100)
    assert credit.credit({**summary, 'own': []}, None) == 0.0


def test_completion_needs_a_finished_job_and_every_requested_byte():
    summary = _module('messages.internal_summary')
    path = WORKSPACE + '/out.log'
    finished = {'detail': {'state': 'finished'}}
    result = {'windows': [_window(path, 0, 60, 100), _window(path, 60, 40, 100)]}
    assert summary.native_results_complete(finished, [result], {path: [0, None]})
    assert not summary.native_results_complete(None, [result], {path: [0, None]})
    assert not summary.native_results_complete({'detail': {'state': 'failed'}}, [result], {path: [0, None]})
    assert not summary.native_results_complete(finished, [{'windows': [_window(path, 0, 60, 100)]}],
                                               {path: [0, None]})
    assert summary.native_results_complete(finished, [{'windows': [_window(path, 0, 60, 100)]}], {path: [0, 50]})


def test_the_controller_follows_the_selector_and_the_settings(episode):
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


def _final_summary():
    path = WORKSPACE + '/out.log'
    facts = {'execution_handoff_refs': ['row_handoff'], 'execution_job_record_refs': ['row_check', 'row_closure'],
             'execution_result_refs': ['source_1'], 'execution_result_artifact_refs': ['artifact_1', 'artifact_file'],
             'execution_completed': True}
    return {'completed': True, 'job': {'last_observed_state': 'finished'}, 'execution_progress': facts,
            'own': [{'windows': [_window(path, 0, 60, 100), _window(path, 60, 40, 100)]}],
            'acquisitions': [{'tool': 'execution_results_status', 'status': 'completed'},
                             {'tool': 'execution_results_collect', 'status': 'failed',
                              'failure_code': 'results_not_available'},
                             {'tool': 'execution_results_read', 'status': 'invalid',
                              'failure_code': 'execution_results_selector_conflict'},
                             {'tool': 'execution_results_collect', 'status': 'completed'}]}


def test_final_to_parent_returns_the_completion_credit_the_counts_and_the_selected_references():
    final = _module('messages.final_to_parent')
    result = final.final_to_parent(_final_summary(), {'credit': 1.5}, SELECTED)
    assert result['credit'] == 1.5
    assert result['finding'] == {'execution_completed': True, 'acquisitions': 2, 'failure_count': 2,
                                 'job_state': 'finished', 'results_not_available': 1, 'windows_acquired': 2,
                                 'bytes_acquired': 100}
    assert result['execution_completed'] is True and result['execution_result_refs'] == ['source_1']
    assert set(result) == REQUIRED | set(SELECTED)
    assert final.RETURN_FORM.select(SELECTED).admit(result, 'return') == result
    every = sorted(SELECTABLE)
    full = final.final_to_parent(_final_summary(), {'credit': 1.5}, every)
    assert full['execution_job_record_refs'] == ['row_check', 'row_closure']
    assert full['execution_result_artifact_refs'] == ['artifact_1', 'artifact_file']
    assert final.RETURN_FORM.select(every).admit(full, 'return') == full
    unobserved = {**_final_summary(), 'job': {'last_observed_state': None}}
    assert final.final_to_parent(unobserved, {'credit': 0.0}, [])['finding']['job_state'] == 'not_observed'
