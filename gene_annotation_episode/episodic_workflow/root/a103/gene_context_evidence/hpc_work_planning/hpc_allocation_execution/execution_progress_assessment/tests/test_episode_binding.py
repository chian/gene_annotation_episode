"""The execution progress assessment episode of A103 is one private binding in the ten-file form."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from yield_control import AccumulationYieldController

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.hpc_work_planning.'
           'hpc_allocation_execution.execution_progress_assessment')
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
             'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}


def episode_module():
    return importlib.import_module(PACKAGE + '.episode')


def test_the_class_inherits_only_the_episode_binding():
    module = episode_module()
    classes = [value for value in vars(module).values() if isinstance(value, type) and value.__module__ == module.__name__]
    assert len(classes) == 1
    assert classes[0].__bases__ == (EpisodeBinding,)
    assert classes[0].binding_path == ('gene_context_evidence/hpc_work_planning/hpc_allocation_execution/'
                                       'execution_progress_assessment')
    assert dict(classes[0].child_slots) == {'monitor': classes[0].binding_path}


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


def test_the_commission_of_a_child_monitor_fits_this_episodes_own_forms():
    module = episode_module()
    cls = [value for value in vars(module).values() if isinstance(value, type) and value.__module__ == module.__name__][0]
    summary = {'target_handle': 'target', 'requested_fields': ['execution_status', 'dependencies'],
               'permitted_committed_record_types': ['source'], 'information_unit': 1.0, 'launch_instructions': None,
               'monitor_direct_dependencies': [{'handle': 'dependent', 'kind': 'job', 'relation_ref': 'r'}]}
    message = cls.msg_to_child('monitor', {'dependency_handle': 'dependent'}, summary)
    admitted = cls.assignment_form.admit(message.assignment, 'assignment')
    parent_input = cls.read_from_parent(admitted, message.message)
    assert parent_input['target_handle'] == 'dependent'
    selected = cls.return_form.select(message.selection)
    assert {'credit', 'finding', 'monitoring_progress_refs', 'monitoring_progress_snapshots'} <= set(selected.fields)
    with pytest.raises(ValueError, match='monitor_child_target_not_exposed_direct_dependency'):
        cls.msg_to_child('monitor', {'dependency_handle': 'other'}, summary)


def test_the_controller_is_the_accumulation_controller_from_the_settings():
    module = episode_module()
    cls = [value for value in vars(module).values() if isinstance(value, type) and value.__module__ == module.__name__][0]
    controller = cls.yield_controller(0.0, {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.1}}, {})
    assert isinstance(controller, AccumulationYieldController)
    with pytest.raises(ValueError, match='monitor_private_yield_binding_not_enabled'):
        cls.yield_controller(0.0, {}, {})


class WithoutJobs:
    """A real service object that offers no job operation: the job services are not built yet."""


def test_the_real_runner_reaches_the_next_decision_and_fails_where_the_job_service_is_missing(tmp_path):
    import asyncio
    import json

    from episode_runtime import BindingRegistry, RunJournal, link
    from gene_annotation_episode.model_provider import ModelProvider, load_config
    from gene_annotation_episode.state import Store

    module = episode_module()
    cls = [value for value in vars(module).values() if isinstance(value, type) and value.__module__ == module.__name__][0]
    store = Store(tmp_path / 'store')
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    try:
        assignment = {'version': 'monitor_assignment', 'target_handle': 'target', 'requested_fields': ['execution_status'],
                      'known_progress_refs': [], 'permitted_committed_record_types': [], 'information_unit': 1.0}
        collaborators = {'store': store, 'model_provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path),
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


def test_final_to_parent_returns_credit_finding_and_every_selectable_fact_and_the_form_admits_them():
    final = importlib.import_module(PACKAGE + '.messages.final_to_parent')
    latest = {'execution_status': {'lifecycle_state': 'executing'}, 'result_available': False,
              'observed_at': '2026-11-19T10:00:00Z', 'dependencies': [{'handle': 'dep_1'}]}
    summary = {'latest_target_observation': latest, 'received_progress_refs': ['progress_1'],
               'target_handle': 'target_1', 'committed_record_refs': ['reasoning_1'],
               'progress_snapshots': {'progress_1': {'state': 'executing'}},
               'newly_informative_received_snapshot_count': 1}
    selection = tuple(name for name in final.RETURN_FORM.fields if name not in ('credit', 'finding'))
    result = final.final_to_parent(summary, {'credit': 0.7}, selection)
    assert result['credit'] == 0.7 and result['finding']['execution_state'] == 'executing'
    assert result['monitoring_execution_state'] == {'value': 'executing'}
    assert result['monitoring_observed_at_unix_seconds'] == {'value': 1795082400.0}
    assert final.RETURN_FORM.admit(result, 'return') == result
    nothing = final.final_to_parent({**summary, 'latest_target_observation': None, 'received_progress_refs': []},
                                    {'credit': 0.0}, selection)
    assert nothing['monitoring_execution_state'] == {'value': None} and nothing['finding']['observed'] is False
    assert final.RETURN_FORM.admit(nothing, 'return') == nothing
