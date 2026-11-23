"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode with a child (its child episode folder aside); no module of the folder
imports another episode folder; the episode's own forms and functions behave on real data. Nothing here is faked."""
import ast
import importlib
import json
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import UNBOUNDED, FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').EvidenceSearchStrategyImprovement
CHILDREN = ('web_search',)
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
    return {'version': 'strategy_assignment', 'question_context_refs': ['ctx_1'],
            'literature_task': task, 'proposed_annotation_ref': 'hyp_1',
            'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['art_1', 'ctx_1']}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
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


def test_the_commission_form_admits_a_strategy_assignment_and_refuses_an_unknown_field_and_any_other_task():
    form = EPISODE.assignment_form
    given = assignment()
    admitted = form.admit(given, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'assess'})
    assert parent_input['strategy']['question_context_refs'] == ['ctx_1']
    assert parent_input['task_key'] == 'A105:verified_source_leads' and 'page' not in parent_input
    assert set(form.record_refs(admitted)) == {'art_1', 'ctx_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**given, 'search_refs': ['src_1']}, 'test')
    with pytest.raises(Exception, match='representation_error'):
        EPISODE.read_from_parent({**admitted, 'literature_task': {**given['literature_task'], 'kind': 'a105_assembly'}},
                                 {})


def test_the_yield_controller_is_the_accumulation_controller():
    parent = EPISODE.read_from_parent(EPISODE.assignment_form.admit(assignment(), 'test'), {})
    settings = {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}
    assert type(EPISODE.yield_controller(0, settings, parent)).__name__ == 'AccumulationYieldController'


def sheet_records(states):
    """A custody reader over sheet states ``{ref: (assertion_ref, [(log_ratio, weight), ...])}``, as the page persists them
    (the fields the measure reads: the row's assertion_ref and each member result's log_ratio and weight)."""
    import types
    held = {ref: json.dumps({'row': {'assertion_ref': assertion, 'row_ref': row_ref, 'support': support,
                                     'opposition': opposition}})
            for ref, (assertion, row_ref, support, opposition) in states.items()}
    return types.SimpleNamespace(get_artifact=lambda ref: held[ref])


def test_the_credit_is_the_evidence_the_held_sheet_adds_over_the_given_sheet_additive_and_weighed_by_distance_and_writing_a_query_earns_nothing():
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
    assert credit_module.ceiling(summary, None, 'write_search', None, None) == 0.0
    assert credit_module.ceiling(summary, None, 'web_search', None, None) is UNBOUNDED


def test_the_model_is_offered_the_writing_of_a_query_and_the_child_over_the_unhanded_queries_only():
    task = importlib.import_module(PACKAGE + '.task')
    assert set(EPISODE.tools) == {'write_search'}
    written = task.write_search_entry()
    assert list(written['input_schema']['properties']) == ['query', 'size', 'cursor']
    schema = task.selection_schema({'input_list': ['src_1']})
    options = schema['properties']['selection']['anyOf']
    assert len(options) == 1 + len(task.CHILD_SLOTS)
    child = options[-1]['properties']['arguments']
    # ONE query by reference: a query handed out is done and no longer offered
    assert child['properties']['search_query_ref'] == {'enum': ['src_1']}
    assert len(task.selection_schema({'input_list': []})['properties']['selection']['anyOf']) == 1
    assert task.valid_slots([]) == [] and task.valid_slots(['src_1']) == list(task.CHILD_SLOTS)
    assert set(task.CHILD_ARGUMENTS) == set(EPISODE.child_slots) == set(task.CHILD_SLOTS)


def test_the_commission_to_the_web_search_hands_one_query_by_reference_and_selects_what_it_returns():
    to_child = importlib.import_module(PACKAGE + '.messages.msg_to_child')
    task = assignment()['literature_task']
    summary = {'task': task, 'task_key': 'A105:verified_source_leads', 'strategy': {'question_context_refs': []},
               'proposed_annotation_ref': 'hyp_1', 'sheet_state_refs': [], 'scope': {},
               'held_record_refs': [], 'all_examined_article_refs': ['src_9', 'src_8']}
    message = to_child.msg_to_child('web_search', {'objective': 'x', 'search_query_ref': 'src_1'}, summary)
    assert set(message.selection) == {'examined_article_refs', 'sheet_state_refs',
                                      'literature_source_lead_dispositions'}
    # the query travels as the reference of the strategy's record, never as query text
    assert message.assignment['search_query_ref'] == 'src_1' and 'search_refs' not in message.assignment
    assert 'PopZ' not in json.dumps(message.assignment) and set(message.assignment) == {
        'version', 'question_context_refs', 'search_query_ref', 'literature_task', 'proposed_annotation_ref',
        'sheet_state_refs', 'examined_article_refs', 'scope', 'received_record_refs'}
    # every article examined so far (the ones this episode was given and its children's) goes to each commission
    assert message.assignment['examined_article_refs'] == ['src_9', 'src_8']


def test_the_articles_examined_are_the_ones_given_and_the_ones_the_web_search_children_returned():
    summary_module = importlib.import_module(PACKAGE + '.messages.internal_summary')
    given = {'examined_article_refs': ['src_given']}
    child = {'kind': 'child', 'slot': 'web_search', 'arguments': {'search_query_ref': 'src_1'},
             'report': {'examined_article_refs': ['src_a', 'src_b']}}
    again = {**child, 'report': {'examined_article_refs': ['src_b', 'src_c']}}
    assert summary_module.examined_article_refs(given, [child, again]) == (['src_a', 'src_b', 'src_c'],
                                                                           ['src_given', 'src_a', 'src_b', 'src_c'])


def test_the_return_declares_the_articles_its_pages_examined_and_returns_them_when_selected():
    final = importlib.import_module(PACKAGE + '.messages.final_to_parent')
    summary = {'scores': [], 'features': [], 'examined_article_refs': ['src_1'], 'sheet_state_refs': []}
    result = final.final_to_parent(summary, {'credit': 1.0}, ['examined_article_refs'])
    assert result['examined_article_refs'] == ['src_1']
    assert EPISODE.return_form.admit(result, 'test')['examined_article_refs'] == ['src_1']
    assert 'examined_article_refs' not in final.final_to_parent(summary, {'credit': 1.0}, [])
