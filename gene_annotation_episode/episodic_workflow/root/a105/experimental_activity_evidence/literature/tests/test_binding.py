"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode with a child (its child episode folder aside); no module of the folder
imports another episode folder; the episode's own forms and functions behave on real data. Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import UNBOUNDED, FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').PublishedEvidenceAssessment
CHILDREN = ('strategy',)
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py', 'tests/grading_world.py', 'tests/test_grading.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'


def own_files():
    return {path for path in FOLDER.rglob('*') if path.is_file() and '__pycache__' not in path.parts
            and path.relative_to(FOLDER).parts[0] not in CHILDREN}


def assignment():
    task = {'version': 'literature_local_task', 'kind': 'verified_source_leads', 'evidence_axis': 'A105',
            'credit_unit': 1.0}
    return {'version': 'literature_assignment', 'question_context_refs': ['ctx_1'],
            'literature_task': task, 'proposed_annotation_ref': 'hyp_1',
            'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['art_1', 'ctx_1']}


def summary_of():
    given = assignment()
    literature = {name: given[name] for name in ('version', 'question_context_refs')}
    return {'literature': literature, 'task': given['literature_task'],
            'task_key': 'A105:verified_source_leads', 'proposed_annotation_ref': 'hyp_1', 'scope': given['scope'],
            'held_record_refs': ['art_1', 'ctx_1'], 'sheet_state_refs': [], 'examined_article_refs': []}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert EPISODE.binding_path == 'experimental_activity_evidence/literature'
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {slot: EPISODE.binding_path + '/' + slot for slot in CHILDREN}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_a_child_and_its_child_folder():
    assert {str(path.relative_to(FOLDER)) for path in own_files()} == FILES
    assert {path.name for path in FOLDER.iterdir() if path.is_dir() and path.name != '__pycache__'} == {
        'messages', 'tests', *CHILDREN}


def test_no_module_of_the_folder_imports_another_episode_folder():
    for path in own_files():
        if path.suffix != '.py':
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module
                assert not any(module == PACKAGE + '.' + child or module.startswith(PACKAGE + '.' + child + '.')
                               for child in CHILDREN), str(path.relative_to(FOLDER)) + ' imports ' + module


def test_the_commission_form_admits_the_one_task_and_refuses_an_unknown_field_a_source_and_any_other_task():
    form = EPISODE.assignment_form
    given = assignment()
    admitted = form.admit(given, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'assess'})
    assert parent_input['literature']['question_context_refs'] == ['ctx_1']
    assert parent_input['task_key'] == 'A105:verified_source_leads' and 'page' not in parent_input
    assert set(form.record_refs(admitted)) == {'art_1', 'ctx_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**given, 'extra': 1}, 'test')
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**given, 'source_refs': ['src_1']}, 'test')
    refused = {**admitted, 'literature_task': {**given['literature_task'], 'evidence_axis': 'A106'}}
    with pytest.raises(Exception, match='representation_error'):
        EPISODE.read_from_parent(refused, {})
    for other in ({'kind': 'source_answer', 'answer_kind': 'assessment', 'source_refs': ['src_1']},
                  {'kind': 'a105_experiments', 'experiments': [{'experiment_ref': 'e1', 'assay_type': 'a'}]},
                  {'kind': 'a105_assembly', 'experiment_refs': ['e1'], 'metrics': ['overall']}):
        with pytest.raises(Exception, match='representation_error'):
            EPISODE.read_from_parent({**admitted, 'literature_task': {**given['literature_task'], **other}}, {})


def test_the_yield_controller_is_the_accumulation_controller():
    parent = EPISODE.read_from_parent(EPISODE.assignment_form.admit(assignment(), 'test'), {})
    settings = {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}
    assert type(EPISODE.yield_controller(0, settings, parent)).__name__ == 'AccumulationYieldController'


def sheet_records(states):
    """A custody reader over sheet states ``{ref: (assertion_ref, [(log_ratio, weight), ...])}``, as the page persists them
    (the fields the measure reads: the row's assertion_ref and each member result's log_ratio and weight)."""
    import json
    import types
    held = {ref: json.dumps({'row': {'assertion_ref': assertion, 'row_ref': row_ref, 'support': support,
                                     'opposition': opposition}})
            for ref, (assertion, row_ref, support, opposition) in states.items()}
    return types.SimpleNamespace(get_artifact=lambda ref: held[ref])


def test_the_credit_is_the_evidence_the_held_sheet_adds_over_the_given_sheet_additive_and_weighed_by_distance_and_the_ceilings_are_the_two_actions():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    # state ref -> (assertion, row_ref, support, opposition); a row's support and opposition already carry the distance weight
    records = sheet_records({'given': ('a1', 'r1', 1.0, 0.0), 'more': ('a1', 'r1', 1.5, 0.25),   # 'more' is a later state of r1
                             'second': ('a1', 'r2', 0.5, 0.25), 'other': ('a2', 'r9', 9.0, 1.0)})

    def held(refs, given):
        return {'sheet_state_refs': refs, 'given_sheet_state_refs': given, 'proposed_annotation_ref': 'a1',
                'child_returns': [{'credit': 7.0}]}
    assert credit_module.credit(held([], []), records) == 0.0                  # no sheet: nothing; a child's credit is not added
    assert credit_module.credit(held(['given'], []), records) == 1.0           # r1: 1.0 + 0.0
    assert credit_module.credit(held(['given', 'second'], []), records) == 1.75   # two rows add: 1.0 + (0.5 + 0.25)
    assert credit_module.credit(held(['given', 'more'], []), records) == 1.75     # the later state of r1 stands: 1.5 + 0.25, not added to 1.0
    assert credit_module.credit(held(['more', 'given'], []), records) == 1.0      # the last state listed stands
    assert credit_module.credit(held(['more'], ['given']), records) == 0.75       # 1.75 held minus the given 1.0
    assert credit_module.credit(held(['given', 'second'], ['given']), records) == 0.75   # only the new row adds
    assert credit_module.credit(held(['given', 'other'], ['given']), records) == 0.0      # another annotation adds nothing
    summary = held(['more'], ['given'])
    assert credit_module.ceiling(summary, None, 'state_query', None, None) == 0.0
    assert credit_module.ceiling(summary, None, 'strategy', None, None) is UNBOUNDED
    with pytest.raises(LookupError, match='no_such_action_type'):
        credit_module.ceiling(summary, None, 'reason', None, None)


def test_the_model_is_offered_the_reading_of_held_records_and_the_child_and_no_search_paper_or_reasoning_tool():
    task = importlib.import_module(PACKAGE + '.task')
    entries = task.catalog()
    assert [entry['name'] for entry in entries] == ['state_query'] and set(EPISODE.tools) == {'state_query'}
    schema = task.selection_schema()
    options = schema['properties']['selection']['anyOf']
    assert len(options) == 1 + len(task.CHILD_SLOTS)
    # the child is handed this episode's objective alone: no search and no paper is required to commission it
    assert list(options[-1]['properties']['arguments']['properties']) == ['objective']
    assert task.valid_slots() == list(task.CHILD_SLOTS)
    assert set(task.CHILD_ARGUMENTS) == set(EPISODE.child_slots) == set(task.CHILD_SLOTS)
    assert EPISODE.offered_actions(None, None) == ['state_query', 'strategy']


def test_the_strategy_commission_is_handed_no_search_and_no_source():
    msg = importlib.import_module(PACKAGE + '.messages.msg_to_child')
    message = msg.msg_to_child('strategy', {'objective': 'o'}, summary_of())
    assert message.objective == 'o'
    assert set(message.assignment) == {'version', 'question_context_refs', 'literature_task', 'proposed_annotation_ref',
                                       'sheet_state_refs', 'examined_article_refs', 'scope', 'received_record_refs'}
    assert message.assignment['version'] == 'strategy_assignment'
    assert set(message.selection) == {'sheet_state_refs', 'examined_article_refs',
                                      'literature_source_lead_dispositions'}
