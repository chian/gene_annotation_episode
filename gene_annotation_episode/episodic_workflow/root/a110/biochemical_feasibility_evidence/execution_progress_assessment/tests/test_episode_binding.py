"""The execution progress assessment episode of A110 is one private binding in the ten-file form."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from yield_control import AccumulationYieldController

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.'
           'execution_progress_assessment')
BINDING_PATH = 'biochemical_feasibility_evidence/execution_progress_assessment'
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
             'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}


def episode_class():
    module = importlib.import_module(PACKAGE + '.episode')
    classes = [value for value in vars(module).values()
               if isinstance(value, type) and value.__module__ == module.__name__]
    assert len(classes) == 1
    return classes[0]


def test_the_class_inherits_only_the_episode_binding():
    cls = episode_class()
    assert cls.__bases__ == (EpisodeBinding,)
    assert cls.binding_path == BINDING_PATH
    assert dict(cls.child_slots) == {'monitor': BINDING_PATH}
    assert set(cls.services) == {'job_access', 'native_events'}


def test_the_folder_holds_exactly_the_ten_files():
    found = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*.py')
             if '__pycache__' not in path.parts and 'tests' not in path.relative_to(FOLDER).parts}
    assert found == TEN_FILES


def test_no_module_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        if '__pycache__' in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            names = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                     else [node.module or ''] if isinstance(node, ast.ImportFrom) and node.level == 0 else [])
            for name in names:
                assert '.episodic_workflow.root.' not in name, (str(path), name)


def test_the_commission_of_a_dependency_monitor_fits_this_episodes_own_forms():
    cls = episode_class()
    snapshot = {'version': 'progress_snapshot_v1', 'progress_ref': 'progress_' + 'a' * 24,
                'target_handle': 'dependent'}
    summary = {'information_unit': 1.0, 'launch_instructions': None, 'permitted_committed_record_types': ['source'],
               'monitor_direct_dependencies': [{'handle': 'dependent', 'kind': 'job'}],
               'progress_snapshots': {snapshot['progress_ref']: snapshot}}
    arguments = {'dependency_handle': 'dependent', 'requested_fields': ['execution_status'],
                 'known_progress_refs': [snapshot['progress_ref']], 'permitted_committed_record_types': ['source']}
    message = cls.msg_to_child('monitor', arguments, summary)
    admitted = cls.assignment_form.admit(message.assignment, 'assignment')
    parent_input = cls.read_from_parent(admitted, message.message)
    assert parent_input['target_handle'] == 'dependent'
    assert parent_input['known_progress_snapshots'] == {snapshot['progress_ref']: snapshot}
    selected = cls.return_form.select(message.selection)
    assert {'credit', 'finding', 'monitoring_progress_refs', 'monitoring_progress_snapshots'} <= set(selected.fields)


def test_a_wrong_dependency_commission_fails_with_its_error():
    cls = episode_class()
    summary = {'information_unit': 1.0, 'launch_instructions': None, 'permitted_committed_record_types': [],
               'monitor_direct_dependencies': [], 'progress_snapshots': {}}
    arguments = {'dependency_handle': 'other', 'requested_fields': [], 'known_progress_refs': [],
                 'permitted_committed_record_types': []}
    with pytest.raises(ValueError, match='monitor_child_target_not_exposed_direct_dependency'):
        cls.msg_to_child('monitor', arguments, summary)


def test_the_controller_is_the_accumulation_controller_from_the_settings():
    cls = episode_class()
    controller = cls.yield_controller(0.0, {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.1}}, {})
    assert isinstance(controller, AccumulationYieldController)


def test_a_non_positive_information_unit_is_refused_when_the_assignment_is_read():
    cls = episode_class()
    assignment = {'version': 'monitor_assignment_v1', 'target_handle': 'target',
                  'requested_fields': ['execution_status'], 'known_progress_refs': [],
                  'permitted_committed_record_types': [], 'information_unit': 0.0}
    with pytest.raises(ValueError, match='explicit_positive_monitoring_information_unit_required'):
        cls.read_from_parent(cls.assignment_form.admit(assignment, 'assignment'), {})


def test_credit_of_nothing_received_is_zero():
    cls = episode_class()
    summary = {'progress_snapshots': {}, 'information_unit': 1.0, 'received_progress_refs': [],
               'known_progress_refs': [], 'target_handle': 'target'}
    assert cls.credit(summary, None) == 0.0


def test_the_return_carries_the_finding_and_every_selectable_field_and_is_admitted_by_the_form():
    cls = episode_class()
    observation = {'target_handle': 'target', 'execution_status': {'lifecycle_state': 'executing'},
                   'result_available': False, 'observed_at': '2026-11-19T10:00:00+00:00',
                   'dependencies': [{'handle': 'dependency_1'}], 'committed_record_refs': ['rec_1']}
    summary = {'target_handle': 'target', 'latest_target_observation': observation,
               'received_progress_refs': ['progress_1'], 'committed_record_refs': ['rec_1'],
               'progress_snapshots': {'progress_1': observation}, 'newly_informative_received_snapshot_count': 1}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 2, 'credit': 1.0}
    selectable = [name for name, spec in cls.return_form.fields.items() if not spec.required]
    result = cls.final_to_parent(summary, completion, selectable)
    assert result['credit'] == 1.0 and result['finding']['execution_state'] == 'executing'
    assert result['monitoring_execution_state'] == {'value': 'executing'}
    assert result['monitoring_dependency_handles'] == ['dependency_1']
    assert result['monitoring_observed_at_unix_seconds']['value'] == 1795082400.0
    cls.return_form.admit(result, 'return')
    unobserved = {**summary, 'latest_target_observation': None, 'received_progress_refs': [],
                  'committed_record_refs': [], 'progress_snapshots': {},
                  'newly_informative_received_snapshot_count': 0}
    bare = cls.final_to_parent(unobserved, completion, selectable)
    assert bare['monitoring_execution_state'] == {'value': None} and bare['finding']['observed'] is False
    cls.return_form.admit(bare, 'return')


class WithoutJobs:
    """A real service object that offers no job operation: the job services are not built yet."""


def test_the_real_runner_reaches_the_next_decision_and_fails_where_the_job_service_is_missing(tmp_path):
    import asyncio
    import json

    from episode_runtime import BindingRegistry, RunJournal, link
    from gene_annotation_episode.model_provider import ModelProvider, load_config
    from gene_annotation_episode.state import Store

    cls = episode_class()
    store = Store(tmp_path / 'store')
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    try:
        assignment = {'version': 'monitor_assignment_v1', 'target_handle': 'target',
                      'requested_fields': ['execution_status'], 'known_progress_refs': [],
                      'permitted_committed_record_types': [], 'information_unit': 1.0}
        collaborators = {'store': store,
                         'model_provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path),
                         'continuation': {cls.binding_path: {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.1}}},
                         'services': {'job_access': WithoutJobs, 'native_events': WithoutJobs}}
        linked = link(BindingRegistry([cls()]), cls.binding_path,
                      {'assignment': assignment, 'message': {}, 'selection': []}, run_id='next_decision',
                      journal=journal, collaborators=collaborators)
        with pytest.raises(NotImplementedError, match='BLOCKED-ON-JOB-SERVICE: job_access'):
            asyncio.run(linked.run())
        assert 'BLOCKED-ON-JOB-SERVICE' in json.dumps(journal.run_failure('next_decision'))
    finally:
        store.close()
