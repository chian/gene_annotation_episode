"""The real binding: importing ``episode.py`` runs the class-definition checks, so the import is the check. The
pure functions of the episode are run on real values."""
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
    assert cls.binding_path == ('evolutionary_history_evidence/hpc_work_planning/'
                                'execution_result_acquisition')
    assert PACKAGE.endswith(cls.binding_path.replace('/', '.'))
    assert dict(cls.child_slots) == {}
    assert cls.services == ('job_access',)
    assert set(cls.tools) == {'execution_results_status', 'execution_results_collect', 'execution_results_read'}


def test_the_folder_holds_exactly_the_ten_files():
    names = {path.name for path in FOLDER.iterdir() if path.name != '__pycache__'}
    assert names == TEN_FILES
    assert {path.name for path in (FOLDER / 'messages').iterdir() if path.name != '__pycache__'} == MESSAGE_FILES


def test_no_module_imports_another_episode_folder():
    own = PACKAGE
    for path in FOLDER.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and node.level == 0 else [])
            for module in modules:
                assert not module.startswith('gene_annotation_episode.episodic_workflow.root') or (
                    module == own or module.startswith(own + '.')), (path, module)
            if isinstance(node, ast.ImportFrom) and node.level > 1:
                pytest.fail('a relative import leaves the folder: %s' % path)


def test_the_return_form_declares_credit_finding_and_the_selectable_sources(episode):
    form = episode.ExecutionResultAcquisition.return_form
    assert {name for name, spec in form.fields.items() if spec.required} == {
        'credit', 'finding', 'execution_result_refs', 'execution_completed'}
    assert form.fields['credit'].type == 'number'
    assert form.select(['execution_handoff_refs']).fields['execution_handoff_refs'].required
    with pytest.raises(FormError):
        form.select(['execution_result_refs'])


def test_the_assignment_form_names_the_original_fields(episode):
    fields = episode.ExecutionResultAcquisition.assignment_form.fields
    assert fields['version'].value == 'execution_results_assignment_v1'
    assert fields['handoff_ref'].type == 'record_refs' and fields['selector'].type == 'record'
    assert fields['initial_result_refs'].type == 'record_refs' and not fields['initial_result_refs'].required


def test_read_from_parent_turns_the_selector_into_requested_windows(episode):
    read = _module('messages.read_from_parent').read_from_parent
    path = WORKSPACE + '/out.log'
    other = WORKSPACE + '/err.log'
    parent_input = read(_assignment({'paths': [other], 'path': path, 'offset': 10, 'limit': 20}), {'purpose': 'x'})
    assert parent_input['requested'] == {other: [0, None], path: [10, 20]}
    assert parent_input['handoff_refs'] == ['source_handoff']
    with pytest.raises(ValueError, match='practical_write_outside_workspace'):
        read(_assignment({'path': '/etc/passwd'}), {})
    with pytest.raises(ValueError, match='execution_results_paths_required'):
        read(_assignment({'offset': 3}), {})
    with pytest.raises(NotImplementedError, match='BLOCKED-ON-JOB-SERVICE'):
        read(_assignment({'version': 'bvbrc_minhash_result_selector_v2'}), {})


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


def test_completion_needs_every_requested_byte_of_a_successful_observation():
    summary = _module('messages.internal_summary')
    path = WORKSPACE + '/out.log'
    done = {'state': 'completed', 'returncode': 0}
    body = {'observation': done, 'windows': [_window(path, 0, 60, 100), _window(path, 60, 40, 100)]}
    assert summary.native_results_complete([body], {path: [0, None]})
    assert not summary.native_results_complete([{**body, 'observation': {'state': 'completed', 'returncode': 1}}],
                                               {path: [0, None]})
    assert not summary.native_results_complete([{**body, 'windows': [_window(path, 0, 60, 100)]}],
                                               {path: [0, None]})
    assert summary.native_results_complete([{**body, 'windows': [_window(path, 0, 60, 100)]}], {path: [0, 50]})


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
    with pytest.raises(ValueError, match='results_original_task_yield_profile_required'):
        controller(0.0, {}, finite)


def test_the_return_carries_the_system_credit_every_selectable_fact_and_is_admitted():
    final = _module('messages.final_to_parent')
    path = WORKSPACE + '/out.log'
    summary = {'handoff_refs': ['source_handoff'], 'result_refs': ['source_r'], 'completed': True,
               'requested_paths': [{'path': path, 'offset': 0, 'limit': None}], 'window_count': 1, 'failure_count': 0,
               'observation_states': [{'state': 'completed', 'returncode': 0}], 'acquired_record_unit': 2.0}
    every = [name for name in final.RETURN_FORM.fields if name not in ('credit', 'finding')]
    result = final.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 1.0}, every)
    assert result['credit'] == 1.0 and result['finding']['complete'] is True
    assert result['execution_result_refs'] == ['source_r'] and result['execution_handoff_refs'] == ['source_handoff']
    final.RETURN_FORM.admit(result, 'return')
