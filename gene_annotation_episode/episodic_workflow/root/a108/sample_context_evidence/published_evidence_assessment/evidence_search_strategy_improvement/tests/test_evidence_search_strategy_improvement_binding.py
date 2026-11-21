"""Real checks of the A108 evidence search strategy improvement binding: importing ``episode.py`` runs the system's
class-definition checks, the folder holds exactly the ten-file set, no module imports another episode folder, the
assignment form admits a strategy assignment with its one task kind and no search, the yield controller is
accumulation, the model is offered only the writing of a search and, while a written search is not yet handed out, the
search child (by reference), and the commission carries the one search by reference."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildMessage, EpisodeBinding

MODULE = ('gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.'
          'published_evidence_assessment.evidence_search_strategy_improvement')
FOLDER = Path(__file__).resolve().parent.parent
CHILDREN = {'source_relevance_assessment'}
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
    assert classes[0].binding_path == goal.BINDING_PATH
    assert MODULE.endswith(goal.BINDING_PATH.replace('/', '.'))
    assert dict(classes[0].child_slots) == {name: goal.BINDING_PATH + '/' + name for name in CHILDREN}


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


SEARCH, OTHER = 'source_111111111111111111111111', 'source_222222222222222222222222'
CONTEXT = 'context_111111111111111111111111'
HYPOTHESIS, SUBJECT = 'hypothesis_111111111111111111111111', 'input_111111111111111111111111'
LEADS_TASK = {'version': 'literature_local_task_v1', 'evidence_axis': 'A108', 'credit_unit': 2,
              'kind': 'verified_source_leads'}


def assignment(task=None):
    return {'version': 'strategy_assignment_v1', 'question_context_refs': [CONTEXT],
            'literature_task': task or LEADS_TASK,
            'proposed_annotation_ref': HYPOTHESIS, 'scope': {'subject_refs': [SUBJECT]},
            'received_record_refs': [HYPOTHESIS]}


def parent_input(task=None):
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    return from_parent.read_from_parent(from_parent.ASSIGNMENT_FORM.admit(assignment(task), 'assignment'),
                                        {'purpose': 'x'})


def test_the_assignment_admits_a_strategy_assignment_without_a_search_and_read_from_parent_reads_it():
    value = parent_input()
    assert value['task_key'] == 'A108:verified_source_leads'
    assert 'prior_search_refs' not in value and value['message'] == {'purpose': 'x'}
    with pytest.raises(Exception):
        parent_input({**LEADS_TASK, 'kind': 'source_answer', 'answer_kind': 'assessment', 'source_refs': [SEARCH]})


def test_the_yield_controller_is_accumulation():
    yield_file = importlib.import_module(MODULE + '.yield_estimator')
    assert type(yield_file.yield_controller(0.0, {}, parent_input())).__name__ == 'AccumulationYieldController'


def summary_of(input_list=()):
    value = parent_input()
    return {'literature_assignment': {'version': 'strategy_assignment_v1',
                                      'question_context_refs': value['question_context_refs'],
                                      'literature_task': value['task'], 'proposed_annotation_ref': HYPOTHESIS},
            'task': value['task'], 'proposed_annotation_ref': HYPOTHESIS, 'scope': value['scope'],
            'received_record_refs': value['received_record_refs'], 'proposed_annotation_subject_refs': [SUBJECT],
            'input_list': list(input_list)}


def test_the_commission_carries_the_one_search_by_reference():
    to_child = importlib.import_module(MODULE + '.messages.msg_to_child')
    child_form = importlib.import_module(MODULE + '.source_relevance_assessment.messages.read_from_parent')
    message = to_child.msg_to_child('source_relevance_assessment', {'objective': 'o', 'search_query_ref': SEARCH},
                                    summary_of([SEARCH]))
    assert isinstance(message, ChildMessage) and message.objective == 'o'
    assert message.selection == ('literature_source_lead_dispositions',)
    assert message.assignment['version'] == 'search_assignment_v1'
    assert message.assignment['search_query_ref'] == SEARCH
    assert message.assignment['received_record_refs'] == [SEARCH, CONTEXT, HYPOTHESIS, SUBJECT]
    child_form.ASSIGNMENT_FORM.admit(message.assignment, 'assignment')
    with pytest.raises(LookupError):
        to_child.msg_to_child('nobody', {'objective': 'o'}, summary_of())


def test_the_search_child_is_offered_only_while_a_written_search_remains(tmp_path):
    from episode_runtime import ModelRequest
    from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sample_context_evidence.action_transport import (
        generation_schema)
    from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
        admitted_by_provider, violations)
    task = importlib.import_module(MODULE + '.task')
    credit = importlib.import_module(MODULE + '.credit')
    assert set(task.TOOLS) == {'write_search'} and set(task.CHILD_SLOTS) == CHILDREN
    assert task.offered_actions(summary_of(), None) == ['write_search']
    names = task.offered_actions(summary_of([SEARCH]), None)
    assert names == ['write_search', 'source_relevance_assessment']
    assert [credit.ceiling(None, None, name, None, None) for name in names] == [0.0, credit.UNBOUNDED]
    schema = task.selection_schema([SEARCH])
    child = [option for option in schema['properties']['selection']['anyOf']
             if option['properties']['tool']['const'] == 'source_relevance_assessment'][0]
    assert child['properties']['arguments']['properties']['search_query_ref']['enum'] == [SEARCH]
    request = ModelRequest('REASONING', task.GOAL, {}, generation_schema(schema))
    _, provider_schema = admitted_by_provider(request, tmp_path / 'provider')
    assert violations(provider_schema) == []


def test_a_childs_returned_credit_and_its_leads_earn_nothing_only_a_held_graded_sheet_does():
    credit = importlib.import_module(MODULE + '.credit')
    summary = {'task': dict(LEADS_TASK), 'finding': {'grading_sheets': []}, 'returned_lead_source_refs': ['source_1'],
               'child_reports': [{'credit': 5.0}]}
    assert credit.credit(summary, None) == 0
