"""The real episode module: its class definition checks run at import, its folder holds the ten-file set, it imports
no other episode folder, and its message, report and controller functions behave as carried."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController, CompletionYieldController

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.'
           'execution_progress_assessment')
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
             'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}
SETTINGS = {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.1}}


def _episode():
    return importlib.import_module(PACKAGE + '.episode').ExecutionProgressAssessment


def _snapshot(handle='job_1'):
    return {'target_handle': handle, 'progress_ref': 'progress_1', 'observed_at': '2026-01-01T00:00:00+00:00',
            'execution_status': {'lifecycle_state': 'executing'}, 'result_available': False, 'dependencies': [],
            'committed_record_refs': []}


def test_importing_episode_runs_the_class_definition_checks():
    episode = _episode()
    assert episode.__bases__ == (EpisodeBinding,)
    assert episode.binding_path == 'sequence_homology_evidence/execution_progress_assessment'
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
                 'monitoring_committed_record_refs', 'monitoring_dependency_handles',
                 'monitoring_progress_snapshots'):
        assert fields[name]['required'] is False


def test_assignment_form_admits_the_monitor_assignment_and_refuses_more_fields_than_offered():
    module = importlib.import_module(PACKAGE + '.messages.read_from_parent')
    assignment = {'version': 'monitor_assignment_v1', 'target_handle': 'job_1',
                  'requested_fields': ['execution_status'], 'known_progress_refs': [],
                  'permitted_committed_record_types': [], 'information_unit': 1.0}
    admitted = module.ASSIGNMENT_FORM.admit(assignment, 'assignment')
    assert admitted['target_handle'] == 'job_1'
    with pytest.raises(FormError):
        module.ASSIGNMENT_FORM.admit({**assignment, 'requested_fields': ['private_reasoning']}, 'assignment')
    assert module.read_from_parent(admitted, {})['blast_status_target'] is False
    blast = module.ASSIGNMENT_FORM.admit({**assignment, 'target_description': {
        'resource_kind': 'api', 'service_or_program': 'ncbi_blast'}}, 'assignment')
    assert module.read_from_parent(blast, {})['blast_status_target'] is True


def test_yield_controller_is_accumulation_and_completion_for_a_blast_status_target():
    module = importlib.import_module(PACKAGE + '.yield_estimator')
    plain = {'blast_status_target': False, 'information_unit': 1.0}
    blast = {'blast_status_target': True, 'information_unit': 1.0}
    assert isinstance(module.yield_controller(0.0, SETTINGS, plain), AccumulationYieldController)
    controller = module.yield_controller(0.0, SETTINGS, blast)
    assert isinstance(controller, CompletionYieldController) and controller.target == 1.0
    with pytest.raises(ValueError, match='monitor_private_yield_binding_not_enabled'):
        module.yield_controller(0.0, {}, plain)
    with pytest.raises(ValueError, match='monitor_information_yield_values_invalid'):
        module.yield_controller(0.0, {'cost': 0.5, 'parameters': {'uncertainty_alpha': 1.5}}, plain)
    with pytest.raises(ValueError, match='completion_cutoff_must_be_below_target'):
        module.yield_controller(0.0, {'cost': 2.0, 'parameters': {'uncertainty_alpha': 0.1}}, blast)


def test_commission_of_a_child_monitor_names_an_exposed_direct_dependency_and_no_wider_record_types():
    module = importlib.import_module(PACKAGE + '.messages.msg_to_child')
    summary = {'target_handle': 'job_1', 'requested_fields': ['execution_status'],
               'permitted_committed_record_types': ['source'], 'information_unit': 1.0,
               'launch_instructions': None,
               'monitor_direct_dependencies': [{'handle': 'job_2', 'kind': 'job', 'relation_ref': 'rel'}]}
    message = module.msg_to_child('monitor', {'dependency_handle': 'job_2'}, summary)
    assert message.assignment['target_handle'] == 'job_2'
    assert message.assignment['permitted_committed_record_types'] == ['source']
    with pytest.raises(ValueError, match='monitor_child_target_not_exposed_direct_dependency'):
        module.msg_to_child('monitor', {'dependency_handle': 'job_9'}, summary)
    with pytest.raises(ValueError, match='monitor_child_expands_permitted_record_types'):
        module.msg_to_child('monitor', {'dependency_handle': 'job_2',
                                        'permitted_committed_record_types': ['source', 'assessment']}, summary)


def test_the_return_carries_the_recorded_facts_and_every_selectable_field():
    module = importlib.import_module(PACKAGE + '.messages.final_to_parent')
    summary = {'target_handle': 'job_1', 'received_progress_refs': ['progress_1'],
               'latest_target_observation': _snapshot(), 'committed_record_refs': [],
               'progress_snapshots': {'progress_1': _snapshot()}, 'newly_informative_received_snapshot_count': 1}
    selection = ('monitoring_progress_refs', 'monitoring_execution_state', 'monitoring_observed_at_unix_seconds')
    result = module.final_to_parent(summary, {'credit': 1.0}, selection)
    assert result['credit'] == 1.0 and result['monitoring_progress_refs'] == ['progress_1']
    assert result['monitoring_execution_state'] == {'value': 'executing'}
    module.RETURN_FORM.select(selection).admit(result, 'result')
    every = tuple(name for name in module.RETURN_FORM.fields if name not in ('credit', 'finding'))
    everything = module.final_to_parent(summary, {'credit': 1.0}, every)
    module.RETURN_FORM.admit(everything, 'return')
    assert everything['monitoring_progress_snapshots'] == {'progress_1': _snapshot()}
    unobserved = module.final_to_parent({**summary, 'latest_target_observation': None}, {'credit': 0.0}, every)
    module.RETURN_FORM.admit(unobserved, 'return')
    assert unobserved['monitoring_execution_state'] == {} and unobserved['monitoring_dependency_handles'] == []
