"""The real episode module: its class definition checks run at import, its folder holds the ten-file set (its child
episode folders and tests aside), it imports no other episode folder, and the message and controller functions run on the
real library values (the frozen option library fixture, the real forms and the real yield controllers). Nothing is faked
and no remote service is contacted."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildMessage, EpisodeBinding
from method_loop import FormError
from yield_control import BoundedQualityYieldController

from gene_annotation_episode.episodic_workflow.episode_support.configuration.gene_context_evidence.process_options import (
    GeneContextEvidenceLibrary)
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.credit import (
    A103ContextCredit)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.construction_records import (
    SELECTION_VERSION)

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence'
FOLDER = Path(__file__).resolve().parent.parent
LIBRARY_SOURCE = Path(__file__).resolve().parent / 'fixtures' / 'publication' / '2026-10-24-001'
CHILD_FOLDERS = ('execution_job_submission', 'execution_progress_assessment', 'execution_result_acquisition',
                 'hpc_work_planning', 'published_evidence_assessment', 'resource_result_acquisition',
                 'resource_work_submission')
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
             'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}
OLD_ASSIGNMENT_PROPERTIES = {'selection', 'proposed_annotation_ref', 'evidence_refs', 'constraints', 'context',
                             'revision_origin'}


def _episode():
    return importlib.import_module(PACKAGE + '.episode').GeneContextEvidence


def _own_files():
    """The files of this episode: not its child episode folders, not its tests."""
    for path in sorted(FOLDER.rglob('*.py')):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in path.parts or relative.parts[0] in ('tests', *CHILD_FOLDERS):
            continue
        yield path, relative


def test_importing_episode_runs_the_class_definition_checks():
    episode = _episode()
    assert episode.__bases__ == (EpisodeBinding,)
    assert episode.binding_path == 'gene_context_evidence'
    assert dict(episode.child_slots) == {
        'gene_context_evidence': 'gene_context_evidence',
        **{name: 'gene_context_evidence/' + name for name in CHILD_FOLDERS}}
    assert {'operation', 'reason', 'context_grade', 'process_library', 'tool_catalog'} <= set(episode.tools)
    assert 'report' not in episode.tools


def test_folder_holds_exactly_the_ten_file_set():
    assert {str(relative) for _, relative in _own_files()} == TEN_FILES
    assert (FOLDER / 'messages' / '__init__.py').is_file()
    # The folder holds only these files, its child episode folders and its tests.
    assert {path.name for path in FOLDER.iterdir() if path.name != '__pycache__'} == {
        'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py', '__init__.py', 'messages', 'tests',
        *CHILD_FOLDERS}


def test_no_module_imports_another_episode_folder():
    for path, relative in _own_files():
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


def test_assignment_form_has_one_field_per_old_property_and_the_new_fields():
    form = importlib.import_module(PACKAGE + '.messages.read_from_parent').ASSIGNMENT_FORM
    assert set(form.fields) == OLD_ASSIGNMENT_PROPERTIES | {'scope', 'scope_refs'}


def test_return_form_declares_credit_and_finding_required_and_the_fact_sources_selectable():
    form = importlib.import_module(PACKAGE + '.messages.final_to_parent').RETURN_FORM
    assert form.fields['credit'].type == 'number' and form.fields['credit'].required
    assert form.fields['finding'].required
    for name in ('committed_record_refs',):
        assert form.fields[name].required is False


@pytest.fixture(scope='module')
def selection(tmp_path_factory):
    library = GeneContextEvidenceLibrary.freeze(tmp_path_factory.mktemp('library') / 'frozen', source=LIBRARY_SOURCE)
    thought = next(header['option_ref'] for header in library.headers() if header['option_ref']['slot'] == 'thought_pattern')
    return {'version': SELECTION_VERSION, 'evidence_axis': library.reference('A103'), 'thought_pattern': thought,
            'child_tool_info': []}


def _assignment(selection):
    return {'selection': selection, 'proposed_annotation_ref': ['hypothesis_' + 'a' * 24],
            'evidence_refs': ['assessment_' + 'b' * 24], 'constraints': {}, 'context': {'a103_task': {'name': 'x'}},
            'scope': {'subject_refs': ['feature_' + 'c' * 24]}, 'scope_refs': ['feature_' + 'c' * 24]}


def test_read_from_parent_reads_the_assignment_of_the_real_library_selection(selection):
    module = importlib.import_module(PACKAGE + '.messages.read_from_parent')
    admitted = module.ASSIGNMENT_FORM.admit(_assignment(selection), 'assignment')
    parent = module.read_from_parent(admitted, {'purpose': 'test'})
    assert parent['proposed_annotation_ref'] == 'hypothesis_' + 'a' * 24
    assert parent['a103_task_name'] == 'x' and parent['selection'] == selection
    with pytest.raises(FormError):
        module.ASSIGNMENT_FORM.admit({**_assignment(selection), 'not_a_field': 1}, 'assignment')
    without = {key: value for key, value in _assignment(selection).items() if key != 'proposed_annotation_ref'}
    with pytest.raises(ValueError, match='scientific_task_proposed_annotation_required'):
        module.read_from_parent(module.ASSIGNMENT_FORM.admit(without, 'assignment'), {})
    with pytest.raises(ValueError, match='scientific_selection_evidence_axis_must_be_A103'):
        other = {**selection, 'evidence_axis': {**selection['evidence_axis'], 'option_id': 'A101'}}
        module.read_from_parent(module.ASSIGNMENT_FORM.admit(_assignment(other), 'assignment'), {})


def test_yield_controller_is_bounded_quality_from_the_declared_binding_and_refuses_a_mismatch():
    module = importlib.import_module(PACKAGE + '.yield_estimator')
    projector = A103ContextCredit()
    declaration = {'kind': 'bounded_quality', 'cutoff': 0.01, 'parameters': {'uncertainty_alpha': 0.1},
                   'credit_definition': projector.as_record()}
    settings = {'yield_bindings': {'A103:x': declaration, 'A103:' + projector.as_record()['kind']: declaration}}
    for name in ('x', None):
        controller = module.yield_controller(0.0, settings, {'a103_task_name': name})
        assert isinstance(controller, BoundedQualityYieldController)
    with pytest.raises(ValueError, match='scientific_yield_binding_missing_for_task'):
        module.yield_controller(0.0, settings, {'a103_task_name': 'unknown'})
    with pytest.raises(ValueError, match='scientific_yield_credit_definition_mismatch'):
        module.yield_controller(0.0, {'yield_bindings': {'A103:x': {**declaration, 'credit_definition': {'kind': 'other'}}}},
                                {'a103_task_name': 'x'})
    with pytest.raises(ValueError, match='scientific_yield_bindings_not_configured'):
        module.yield_controller(0.0, {}, {'a103_task_name': 'x'})


def test_msg_to_child_selects_the_old_required_return_sources_and_inherits_the_proposed_annotation():
    module = importlib.import_module(PACKAGE + '.messages.msg_to_child')
    summary = {'assignment': {'proposed_annotation_ref': 'hypothesis_' + 'a' * 24}, 'depth': 1}
    arguments = {'objective': 'o', 'purpose': 'p', 'assignment': {'proposed_annotation_ref': ['other']},
                 'child_values': {}, 'select': ['committed_record_refs']}
    message = module.msg_to_child('gene_context_evidence', arguments, summary)
    assert isinstance(message, ChildMessage)
    assert message.assignment['proposed_annotation_ref'] == ['hypothesis_' + 'a' * 24]
    assert message.selection == ('committed_record_refs',)
    nested = module.msg_to_child('gene_context_evidence', arguments, {**summary, 'depth': 2})
    assert nested.selection == ('committed_record_refs',)
    # The monitor is commissioned on a job this episode holds: the job is named by its rows, the objective is fixed
    # and no text of the model is passed (one outstanding job as ``job_records.outstanding_jobs`` lists it).
    job = {'job': 'job_' + '1' * 32, 'handoff_ref': 'row_' + 'a' * 64,
           'record_refs': ['row_' + 'a' * 64, 'row_' + 'b' * 64]}
    monitor = module.msg_to_child('execution_progress_assessment', {
        'handoff_ref': job['handoff_ref'], 'requested_fields': ['execution_status'], 'select': ['job_returncode'],
        'child_values': {'information_unit': 1.0}}, {**summary, 'outstanding_jobs': [job]})
    assert monitor.selection == ('job_returncode',) and monitor.message == {}
    assert monitor.assignment == {
        'version': 'monitor_assignment_v2', 'handoff_refs': [job['handoff_ref']],
        'known_progress_refs': [job['record_refs'][1]], 'dependency_handoff_refs': [],
        'requested_fields': ['execution_status'], 'information_unit': 1.0}
    child = importlib.import_module(PACKAGE + '.execution_progress_assessment.episode').ExecutionProgressAssessment
    child.assignment_form.admit(monitor.assignment, 'assignment')
    assert set(child.return_form.select(monitor.selection).fields) == {'credit', 'finding', 'check_refs',
                                                                        'job_returncode'}
    with pytest.raises(LookupError):
        module.msg_to_child('unknown_slot', arguments, summary)

