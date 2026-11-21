"""Real checks of the A108 sample-context evidence binding: importing ``episode.py`` runs the system's class-definition
checks, the folder holds exactly the ten-file set, no module imports another episode folder, the assignment form admits
the head's assignment, the yield controller is accumulation, the offered action schema is a valid strict output schema
over a real Store's reasoning schema, and each commission is admitted by the form of the child it names. No provider, no
model answers and no fake pieces: only the episode's own functions, the system's forms and a real ``Store``."""
import ast
import importlib
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from episode_runtime import ChildMessage, EpisodeBinding

MODULE = 'gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence'
CHILD_MODULE = MODULE + '.published_evidence_assessment'
FOLDER = Path(__file__).resolve().parent.parent
CHILDREN = {'published_evidence_assessment'}
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}
EPISODE_PACKAGE = 'gene_annotation_episode.episodic_workflow.root'


def folder_files():
    found = set()
    for path in FOLDER.rglob('*'):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in relative.parts or relative.parts[0] in ({'tests'} | CHILDREN) or path.is_dir():
            continue
        found.add(relative.as_posix())
    return found


def test_the_class_passes_the_definition_checks():
    episode = importlib.import_module(MODULE + '.episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1
    assert classes[0].__bases__ == (EpisodeBinding,)
    goal = importlib.import_module(MODULE + '.goal')
    assert classes[0].binding_path == goal.BINDING_PATH == 'sample_context_evidence'
    assert MODULE.endswith(goal.BINDING_PATH.replace('/', '.'))
    assert dict(classes[0].child_slots) == {
        'sample_context_evidence': 'sample_context_evidence',
        'published_evidence_assessment': 'sample_context_evidence/published_evidence_assessment'}


def test_the_folder_holds_exactly_the_ten_file_set():
    assert folder_files() == FILES
    for child in CHILDREN:
        assert (FOLDER / child).is_dir()


def test_no_module_imports_another_episode_folder():
    for relative in sorted(folder_files()):
        tree = ast.parse((FOLDER / relative).read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for name in names:
                if name.startswith(EPISODE_PACKAGE):
                    assert name == MODULE or name.startswith(MODULE + '.'), (relative, name)
                    assert not any(name.startswith(MODULE + '.' + child) for child in CHILDREN), (relative, name)
            if isinstance(node, ast.ImportFrom) and node.level > len(Path(relative).parts):
                raise AssertionError((relative, 'relative import above the episode folder'))


def ref(kind, digit):
    return kind + '_' + digit * 24


LIBRARY = 'a' * 64
SHA = 'b' * 64
AXIS = {'version': 'sample_context_evidence_option_ref_v1', 'library_id': LIBRARY, 'slot': 'evidence_axis',
        'option_id': 'A108', 'entry_sha256': SHA}
THOUGHT = {'version': 'sample_context_evidence_option_ref_v1', 'library_id': LIBRARY, 'slot': 'thought_pattern',
           'option_id': 'P01', 'entry_sha256': SHA}
SELECTORS = {'version': 'sample_context_evidence_selection_v3', 'evidence_axis': AXIS, 'thought_pattern': THOUGHT,
             'child_tool_info': [{'name': 'source.read', 'resources': 'local'}]}
TASK = {'version': 'evidence_axis_task_v1', 'kind': 'whole_axis_findings', 'evidence_axis': 'A108', 'credit_unit': 2}
SUBJECT, HYPOTHESIS = ref('input', '1'), ref('hypothesis', '1')
SCOPE = {'subject_refs': [SUBJECT]}


def assignment():
    return {'selection': SELECTORS, 'proposed_annotation_ref': HYPOTHESIS, 'evidence_refs': [ref('source', '3')],
            'constraints': {}, 'context': {'evidence_task': TASK}, 'scope': SCOPE,
            'received_record_refs': [HYPOTHESIS, SUBJECT]}


def parent_input():
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    return from_parent.read_from_parent(from_parent.ASSIGNMENT_FORM.admit(assignment(), 'assignment'),
                                        {'purpose': 'x'})


def test_the_assignment_admits_the_head_assignment_and_read_from_parent_reads_it():
    value = parent_input()
    assert value['evidence_task'] == TASK and value['revision_origin'] is None
    assert value['selection'] == SELECTORS and value['message'] == {'purpose': 'x'}
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    wrong = {**assignment(), 'context': {'evidence_task': {**TASK, 'evidence_axis': 'A105'}}}
    with pytest.raises(ValueError, match='original_axis_finding_task_required'):
        from_parent.read_from_parent(from_parent.ASSIGNMENT_FORM.admit(wrong, 'assignment'), {})


def test_the_yield_controller_is_accumulation():
    yield_file = importlib.import_module(MODULE + '.yield_estimator')
    controller = yield_file.yield_controller(0.0, {}, parent_input())
    assert type(controller).__name__ == 'AccumulationYieldController'


def summary_of():
    value = parent_input()
    source = ref('source', '3')
    return {'selection': value['selection'], 'scope': value['scope'], 'evidence_task': value['evidence_task'],
            'proposed_annotation_ref': HYPOTHESIS, 'evidence_refs': value['evidence_refs'],
            'constraints': value['constraints'], 'context': value['context'],
            'received_record_refs': value['received_record_refs'], 'proposed_annotation_subject_refs': [SUBJECT],
            'held_source_custody': {source: {'artifact_ref': ref('artifact', '4'), 'text_ref': None,
                                             'stdout_ref': None, 'stderr_ref': None, 'parent_source_refs': []}}}


def test_the_recursion_is_commissioned_with_its_own_form():
    to_child = importlib.import_module(MODULE + '.messages.msg_to_child')
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    final = importlib.import_module(MODULE + '.messages.final_to_parent')
    message = to_child.msg_to_child('sample_context_evidence', {
        'objective': 'o', 'purpose': 'p', 'scope': SCOPE, 'selection': {**SELECTORS},
        'evidence_refs': [ref('source', '3')], 'revision_origin': None, 'return_fields': []}, summary_of())
    assert isinstance(message, ChildMessage) and message.objective == 'o'
    assert message.selection == ('committed_record_refs',)
    assert 'revision_origin' not in message.assignment
    assert message.assignment['proposed_annotation_ref'] == HYPOTHESIS
    from_parent.ASSIGNMENT_FORM.admit(message.assignment, 'assignment')
    assert set(message.selection) <= set(final.RETURN_FORM.fields)


def test_the_literature_commission_is_admitted_by_the_child_form():
    to_child = importlib.import_module(MODULE + '.messages.msg_to_child')
    child_form = importlib.import_module(CHILD_MODULE + '.messages.read_from_parent')
    child_return = importlib.import_module(CHILD_MODULE + '.messages.final_to_parent')
    source = ref('source', '3')
    task = {'version': 'literature_local_task_v1', 'evidence_axis': 'A108', 'credit_unit': 2,
            'kind': 'source_answer', 'answer_kind': 'assessment', 'source_refs': [source]}
    message = to_child.msg_to_child('published_evidence_assessment', {
        'objective': 'o', 'purpose': 'p', 'scope': SCOPE, 'assignment': {
            'question_context_refs': [ref('context', '5')], 'source_refs': [source], 'literature_task': task,
            'requested_a108_grading_components': [], 'requested_a108_aggregation_components': []},
        'return_fields': ['literature_screening_answers']}, summary_of())
    child_form.ASSIGNMENT_FORM.admit(message.assignment, 'assignment')
    assert message.assignment['received_record_refs'] == [
        source, ref('artifact', '4'), ref('hypothesis', '1'), ref('input', '1'), ref('context', '5')]
    assert message.selection == ('literature_screening_answers',)
    assert set(message.selection) <= set(child_return.RETURN_FORM.fields)
    with pytest.raises(LookupError):
        to_child.msg_to_child('nobody', {'scope': SCOPE}, summary_of())


def test_the_offered_action_schema_is_a_valid_strict_output_schema(tmp_path):
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sample_context_evidence.action_transport import (
        generation_schema)
    task = importlib.import_module(MODULE + '.task')
    with Store(tmp_path / 'state') as store:
        summary = {**summary_of(), 'reasoning_schema': store.reasoning_schema(), 'process': {
            'evidence_axis_entry_version': 'evidence_axis_instruction_v1',
            'child_tool_info': [{'name': 'source.read', 'resources': 'local', 'description': 'd',
                                 'instructions': 'i'}]}}
    names = task.offered(summary, {})
    assert names == ['process_search', 'process_entry', 'process_sources', 'process_tools', 'process_revise',
                     'source_read', 'reason', 'sample_context_evidence', 'published_evidence_assessment']
    schema = task.selection_schema(summary, names)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator.check_schema(generation_schema(schema))
    assert set(task.TOOLS) >= set(names) - set(task.CHILD_SLOTS)
    for name in ('process.search', 'process.revise'):
        with pytest.raises(Exception, match='scientific_primitive_uses_common_tool_name'):
            task.selected_tools({'child_tool_info': [{'name': name}]})
    with pytest.raises(Exception, match='scientific_selected_tool_not_callable:material.read'):
        task.selected_tools({'child_tool_info': [{'name': 'material.read'}]})


