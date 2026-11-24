"""The real episode module: its class definition checks run at import, its folder holds the ten-file set, it imports
no other episode folder, and its forms and controller are the ones it declares. What the episode does on a job is
in ``test_monitor_units.py`` (stepped, real jobs) and the branch model-run test."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.gene_context_evidence.'
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
    assert episode.binding_path == 'gene_context_evidence/execution_progress_assessment'
    assert dict(episode.child_slots) == {'monitor': episode.binding_path}
    assert set(episode.tools) == {'progress_observe', 'progress_read', 'progress_log', 'progress_wait'}
    assert tuple(episode.services) == ('job_access', 'estimate_table', 'native_events')


def test_folder_holds_exactly_the_ten_file_set():
    files = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*.py')
             if '__pycache__' not in path.parts and 'tests' not in path.relative_to(FOLDER).parts}
    assert files == TEN_FILES


def test_no_module_imports_another_episode_folder_and_none_holds_a_stub():
    for path in FOLDER.rglob('*.py'):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in path.parts or 'tests' in relative.parts:
            continue
        source = path.read_text()
        assert 'NotImplementedError' not in source and 'BLOCKED-' not in source, relative
        depth = len(relative.parts)  # a relative import of this level or deeper leaves the folder
        for node in ast.walk(ast.parse(source)):
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


def test_return_form_requires_credit_finding_and_the_check_rows_and_every_field_is_controlled():
    module = importlib.import_module(PACKAGE + '.messages.final_to_parent')
    fields = module.RETURN_FORM.as_record()
    assert [name for name, field in fields.items() if field['required']] == ['credit', 'finding', 'check_refs']
    # No open field: a number, a record of a declared form, or record references; no text but a fixed vocabulary.
    assert {field['type'] for field in fields.values()} == {'number', 'record', 'record_refs'}
    assert all('form' in field for field in fields.values() if field['type'] == 'record')
    finding = fields['finding']['form']
    assert {name: field['type'] for name, field in finding.items()} == {
        'observed': 'boolean', 'state': 'text', 'result_available': 'boolean', 'observed_at_unix_seconds': 'number'}
    assert finding['state']['options'] == ['queued', 'running', 'finished', 'failed', 'cancelled', 'unknown']
    with pytest.raises(FormError):
        module.RETURN_FORM.admit({'credit': 1.0, 'finding': {'observed': True, 'state': 'looks stalled to me'},
                                  'check_refs': []}, 'return')


def test_assignment_form_names_the_job_by_record_references_only():
    form = importlib.import_module(PACKAGE + '.messages.read_from_parent').ASSIGNMENT_FORM
    fields = form.as_record()
    assert {name for name, field in fields.items() if field['type'] == 'record_refs'} == {
        'handoff_refs', 'known_progress_refs', 'dependency_handoff_refs'}
    assert 'target_handle' not in fields
    assignment = {'version': 'monitor_assignment', 'handoff_refs': ['row_1'], 'known_progress_refs': ['row_2'],
                  'dependency_handoff_refs': [], 'requested_fields': ['execution_status'], 'information_unit': 1.0}
    assert form.record_refs(form.admit(assignment, 'assignment')) == ('row_1', 'row_2')
    with pytest.raises(FormError):
        form.admit({**assignment, 'target_handle': 'job_1'}, 'assignment')


def test_yield_controller_is_accumulation_and_needs_its_own_settings():
    module = importlib.import_module(PACKAGE + '.yield_estimator')
    controller = module.yield_controller(0.0, {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.1}}, {})
    assert isinstance(controller, AccumulationYieldController)
    with pytest.raises(ValueError, match='monitor_private_yield_binding_not_enabled'):
        module.yield_controller(0.0, {}, {})
    with pytest.raises(ValueError, match='monitor_information_yield_values_invalid'):
        module.yield_controller(0.0, {'cost': 0.5, 'parameters': {'uncertainty_alpha': 1.5}}, {})
