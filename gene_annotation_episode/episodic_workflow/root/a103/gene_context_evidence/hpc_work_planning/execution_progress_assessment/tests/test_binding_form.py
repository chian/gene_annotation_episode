"""The real episode module: its class definition checks run at import, its folder holds the ten-file set, it imports
no other episode folder, and its message and controller functions behave as carried."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.hpc_work_planning.'
           'execution_progress_assessment')
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
             'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}


def _episode():
    return importlib.import_module(PACKAGE + '.episode').ExecutionProgressAssessment


def test_importing_episode_runs_the_class_definition_checks():
    episode = _episode()
    assert episode.__bases__ == (EpisodeBinding,)
    assert episode.binding_path == 'gene_context_evidence/hpc_work_planning/execution_progress_assessment'
    assert dict(episode.child_slots) == {'monitor': episode.binding_path}
    assert set(episode.tools) == {'progress_observe', 'progress_read', 'progress_log'}
    assert tuple(episode.services) == ('job_access',)


def test_folder_holds_exactly_the_ten_file_set():
    files = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*.py')
             if '__pycache__' not in path.parts and 'tests' not in path.relative_to(FOLDER).parts}
    assert files == TEN_FILES


def test_no_module_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in path.parts or 'tests' in relative.parts:
            continue
        depth = len(relative.parts)  # a relative import of this level or deeper leaves the folder
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
    form = importlib.import_module(PACKAGE + '.messages.final_to_parent').RETURN_FORM.as_record()
    fields = form['fields'] if 'fields' in form else form
    assert fields['credit']['required'] and fields['finding']['required']
    for name in ('monitoring_progress_refs', 'monitoring_target_handle', 'monitoring_execution_state',
                 'monitoring_result_available', 'monitoring_observed_at_unix_seconds',
                 'monitoring_committed_record_refs', 'monitoring_dependency_handles'):
        assert fields[name]['required'] is False


def test_assignment_form_admits_the_monitor_assignment_and_refuses_more_fields_than_offered():
    form = importlib.import_module(PACKAGE + '.messages.read_from_parent').ASSIGNMENT_FORM
    assignment = {'version': 'monitor_assignment_v1', 'target_handle': 'job_1',
                  'requested_fields': ['execution_status'], 'known_progress_refs': [],
                  'permitted_committed_record_types': [], 'information_unit': 1.0}
    assert form.admit(assignment, 'assignment')['target_handle'] == 'job_1'
    with pytest.raises(FormError):
        form.admit({**assignment, 'requested_fields': ['private_reasoning']}, 'assignment')


def test_yield_controller_is_accumulation_and_needs_its_own_settings():
    module = importlib.import_module(PACKAGE + '.yield_estimator')
    controller = module.yield_controller(0.0, {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.1}}, {})
    assert isinstance(controller, AccumulationYieldController)
    with pytest.raises(ValueError, match='monitor_private_yield_binding_not_enabled'):
        module.yield_controller(0.0, {}, {})
    with pytest.raises(ValueError, match='monitor_information_yield_values_invalid'):
        module.yield_controller(0.0, {'cost': 0.5, 'parameters': {'uncertainty_alpha': 1.5}}, {})


def test_commission_of_a_child_monitor_names_an_exposed_direct_dependency_and_no_wider_record_types():
    module = importlib.import_module(PACKAGE + '.messages.msg_to_child')
    summary = {'target_handle': 'job_1', 'requested_fields': ['execution_status'],
               'permitted_committed_record_types': ['source'], 'information_unit': 1.0,
               'launch_instructions': None,
               'monitor_direct_dependencies': [{'handle': 'job_2', 'kind': 'job', 'relation_ref': 'rel',
                                                'observed_at': '2026-01-01T00:00:00+00:00', 'state': 'pending'}]}
    message = module.msg_to_child('monitor', {'dependency_handle': 'job_2'}, summary)
    assert message.assignment['target_handle'] == 'job_2'
    assert message.assignment['permitted_committed_record_types'] == ['source']
    with pytest.raises(ValueError, match='monitor_child_target_not_exposed_direct_dependency'):
        module.msg_to_child('monitor', {'dependency_handle': 'job_9'}, summary)
    with pytest.raises(ValueError, match='monitor_child_expands_permitted_record_types'):
        module.msg_to_child('monitor', {'dependency_handle': 'job_2',
                                        'permitted_committed_record_types': ['source', 'assessment']}, summary)


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
