"""Real checks of the A108 published evidence assessment binding: importing ``episode.py`` runs the system's
class-definition checks, the folder holds exactly the ten-file set, no module imports another episode folder, the
assignment form admits a literature assignment with its one task kind, the yield controller is accumulation, the
episode offers its model only the read of held records and the strategy child (no search, fetch or read of a paper, no
reasoning commit) and the commission carries what the child's own form names."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildMessage, EpisodeBinding

MODULE = ('gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.'
          'published_evidence_assessment')
FOLDER = Path(__file__).resolve().parent.parent
CHILDREN = {'evidence_search_strategy_improvement'}
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


CONTEXT = 'context_111111111111111111111111'
HYPOTHESIS, SUBJECT = 'hypothesis_111111111111111111111111', 'input_111111111111111111111111'
LEADS_TASK = {'version': 'literature_local_task', 'evidence_axis': 'A108', 'credit_unit': 2,
              'kind': 'verified_source_leads'}


def assignment(task=None):
    return {'version': 'literature_assignment', 'question_context_refs': [CONTEXT],
            'literature_task': task or LEADS_TASK,
            'proposed_annotation_ref': HYPOTHESIS, 'scope': {'subject_refs': [SUBJECT]},
            'received_record_refs': [HYPOTHESIS]}


def parent_input(task=None):
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    return from_parent.read_from_parent(from_parent.ASSIGNMENT_FORM.admit(assignment(task), 'assignment'),
                                        {'purpose': 'x'})


def test_the_assignment_admits_a_literature_assignment_and_read_from_parent_reads_it():
    value = parent_input()
    assert value['task_key'] == 'A108:verified_source_leads'
    assert 'source_refs' not in value and value['message'] == {'purpose': 'x'}


def test_every_other_task_kind_is_a_wrong_commission():
    for task in ({**LEADS_TASK, 'kind': 'source_answer', 'answer_kind': 'assessment', 'source_refs': [CONTEXT]},
                 {**LEADS_TASK, 'kind': 'source_answer', 'answer_kind': 'screening',
                  'examined': [{'source_ref': CONTEXT, 'artifact_ref': CONTEXT, 'start': 0, 'end': 1}]}):
        with pytest.raises(Exception):
            parent_input(task)


def test_the_yield_controller_is_accumulation():
    yield_file = importlib.import_module(MODULE + '.yield_estimator')
    assert type(yield_file.yield_controller(0.0, {}, parent_input())).__name__ == 'AccumulationYieldController'


def summary_of():
    value = parent_input()
    return {'literature_assignment': {'version': 'literature_assignment',
                                      'question_context_refs': value['question_context_refs'],
                                      'literature_task': value['task'], 'proposed_annotation_ref': HYPOTHESIS},
            'task': value['task'], 'proposed_annotation_ref': HYPOTHESIS, 'scope': value['scope'],
            'received_record_refs': value['received_record_refs'], 'proposed_annotation_subject_refs': [SUBJECT]}


def test_the_commission_names_the_records_and_the_fields_it_wants():
    to_child = importlib.import_module(MODULE + '.messages.msg_to_child')
    child_form = importlib.import_module(MODULE + '.evidence_search_strategy_improvement.messages.read_from_parent')
    message = to_child.msg_to_child('evidence_search_strategy_improvement', {'objective': 'o'}, summary_of())
    assert isinstance(message, ChildMessage) and message.objective == 'o'
    assert message.selection == ('literature_source_lead_dispositions',)
    assert message.assignment['version'] == 'strategy_assignment'
    assert 'prior_search_refs' not in message.assignment and 'source_refs' not in message.assignment
    assert message.assignment['received_record_refs'] == [CONTEXT, HYPOTHESIS, SUBJECT]
    child_form.ASSIGNMENT_FORM.admit(message.assignment, 'assignment')
    with pytest.raises(LookupError):
        to_child.msg_to_child('nobody', {'objective': 'o'}, summary_of())


def test_the_model_is_offered_only_the_read_of_held_records_and_the_strategy_child(tmp_path):
    from episode_runtime import ModelRequest
    from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sample_context_evidence.action_transport import (
        generation_schema)
    from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
        admitted_by_provider, violations)
    task = importlib.import_module(MODULE + '.task')
    assert set(task.TOOLS) == {'state_query'} and set(task.CHILD_SLOTS) == CHILDREN
    names = task.offered_actions(None, None)
    assert names == ['state_query', 'evidence_search_strategy_improvement']
    schema = task.selection_schema()
    assert {option['properties']['tool']['const'] for option in schema['properties']['selection']['anyOf']} == set(names)
    credit = importlib.import_module(MODULE + '.credit')
    assert [credit.ceiling(None, None, name, None, None) for name in names] == [0.0, credit.UNBOUNDED]
    request = ModelRequest('REASONING', task.GOAL, {}, generation_schema(schema))
    _, provider_schema = admitted_by_provider(request, tmp_path / 'provider')
    assert violations(provider_schema) == []


def test_a_childs_returned_credit_and_its_leads_earn_nothing_only_a_held_graded_sheet_does():
    credit = importlib.import_module(MODULE + '.credit')
    summary = {'task': dict(LEADS_TASK), 'finding': {'grading_sheets': []}, 'returned_lead_source_refs': ['source_1'],
               'child_reports': [{'credit': 5.0}]}
    assert credit.credit(summary, None) == 0
