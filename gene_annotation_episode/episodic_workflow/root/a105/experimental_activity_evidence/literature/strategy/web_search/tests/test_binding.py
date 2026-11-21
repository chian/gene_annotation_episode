"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode with a child (its child episode folder aside); no module of the folder
imports another episode folder; the episode's own forms and functions behave on real data. Nothing here is faked."""
import ast
import importlib
import json
import types
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import UNBOUNDED, FormError

from .grading_world import SEARCH_RESPONSE

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceRelevanceAssessment
CHILDREN = ('page',)
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py', 'tests/grading_world.py', 'tests/test_grading.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
PAGE = {'source_ref': 'src_1', 'representation': 'text', 'artifact_ref': 'art_1', 'prior_delivery_refs': []}


def own_files():
    return {path for path in FOLDER.rglob('*') if path.is_file() and '__pycache__' not in path.parts
            and path.relative_to(FOLDER).parts[0] not in CHILDREN}


def assignment():
    task = {'version': 'literature_local_task_v1', 'kind': 'verified_source_leads', 'evidence_axis': 'A105',
            'credit_unit': 1.0}
    return {'version': 'search_assignment_v1', 'question_context_refs': ['ctx_1'], 'search_query_ref': 'src_1',
            'literature_task': task, 'proposed_annotation_ref': 'hyp_1',
            'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['src_1', 'art_1', 'ctx_1']}


def summary_of():
    given = assignment()
    search = {name: given[name] for name in ('version', 'question_context_refs', 'search_query_ref')}
    return {'search': search, 'task': given['literature_task'], 'task_key': 'A105:verified_source_leads',
            'proposed_annotation_ref': 'hyp_1', 'scope': given['scope'],
            'held_record_refs': ['art_1', 'ctx_1', 'src_1'], 'sheet_state_refs': []}


class HeldSources:
    def __init__(self, sources):
        self.sources = sources

    def get(self, ref):
        return self.sources[ref]


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


def test_the_commission_form_admits_a_search_assignment_with_one_query_and_refuses_an_unknown_field_and_any_other_task():
    form = EPISODE.assignment_form
    given = assignment()
    admitted = form.admit(given, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'assess'})
    assert parent_input['search']['search_query_ref'] == 'src_1'
    assert parent_input['task_key'] == 'A105:verified_source_leads' and 'page' not in parent_input
    assert set(form.record_refs(admitted)) == {'src_1', 'art_1', 'ctx_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**given, 'search_refs': ['src_1']}, 'test')
    with pytest.raises(Exception, match='representation_error'):
        EPISODE.read_from_parent({**admitted, 'literature_task': {**given['literature_task'], 'kind': 'source_answer'}},
                                 {})


def test_the_yield_controller_is_the_accumulation_controller():
    parent = EPISODE.read_from_parent(EPISODE.assignment_form.admit(assignment(), 'test'), {})
    settings = {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}
    assert type(EPISODE.yield_controller(0, settings, parent)).__name__ == 'AccumulationYieldController'


def test_the_return_declares_the_articles_its_pages_examined_and_returns_them_when_selected():
    final = importlib.import_module(PACKAGE + '.messages.final_to_parent')
    summary = {'scores': [], 'features': [], 'examined_article_refs': ['src_1'], 'sheet_state_refs': []}
    result = final.final_to_parent(summary, {'credit': 1.0}, ['examined_article_refs'])
    assert result['examined_article_refs'] == ['src_1']
    assert EPISODE.return_form.admit(result, 'test')['examined_article_refs'] == ['src_1']
    assert 'examined_article_refs' not in final.final_to_parent(summary, {'credit': 1.0}, [])


def test_a_search_result_is_one_distinct_hit_of_a_result_list_with_a_pmcid():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.search_result_assessment import (
        ranked_hits)
    second = {'resultList': {'result': [{'pmcid': 'PMC300', 'title': 'repeated'}, {'pmcid': 'PMC400', 'pmid': '7',
                                                                                   'title': 'new', 'pubYear': 2020}]}}
    hits = ranked_hits([json.dumps(SEARCH_RESPONSE), json.dumps(second)])
    # no PMCID: not an item; the same PMCID or the same DOI: one publication; the rank counts the distinct items
    assert [(hit['pmcid'], hit['provider_rank']) for hit in hits] == [('PMC100', 1), ('PMC300', 2), ('PMC400', 3)]
    assert hits[2]['year'] == '2020' and hits[2]['journal'] == '' and hits[0]['journal'] == 'Journal of Tests'


def test_the_listed_hits_follow_the_search_hits_each_paper_once_and_a_listed_paper_without_full_text_is_not_offered():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.search_result_assessment import (
        ranked_hits)
    from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_record_publications import (
        listed_without_full_text, merge_listed)
    search = ranked_hits([json.dumps({'resultList': {'result': [
        {'pmcid': 'PMC1', 'pmid': '11', 'doi': '10.1/a', 'title': 'first'},
        {'pmcid': 'PMC2', 'pmid': '22', 'title': 'second'}]}})])

    def listed(pmcid, pmid, doi, title):
        return {'pmcid': pmcid, 'pmid': pmid, 'doi': doi, 'title': title, 'journal': '', 'year': '', 'abstract': ''}

    # PMC2 is listed under a different identifier set that shares its PMID; PMC9 is listed for two records; the last
    # listed paper has no PMCID (no full text), so it cannot be opened
    merged = merge_listed(search, [listed('PMC2', '22', None, 'second'), listed('PMC9', '99', None, 'ninth'),
                                   listed('PMC9', '99', None, 'ninth'), listed(None, '55', '10.1/z', 'closed')])
    assert [(hit['pmcid'], hit['provider_rank']) for hit in merged] == [('PMC1', 1), ('PMC2', 2), ('PMC9', 3)]
    assert listed_without_full_text([listed(None, '55', '10.1/z', 'closed')]) == 1


def test_the_page_of_a_search_result_is_filled_by_code_from_its_source_record():
    summary_module = importlib.import_module(PACKAGE + '.messages.internal_summary')
    held = HeldSources({'src_text': {'text_ref': 'art_text', 'artifact_ref': 'art_orig'},
                        'src_orig': {'text_ref': None, 'artifact_ref': 'art_orig'}})
    assert summary_module.page_of(held, 'src_text') == {'source_ref': 'src_text', 'representation': 'text',
                                                        'artifact_ref': 'art_text', 'prior_delivery_refs': []}
    assert summary_module.page_of(held, 'src_orig') == {'source_ref': 'src_orig', 'representation': 'original',
                                                        'artifact_ref': 'art_orig', 'prior_delivery_refs': []}


def test_the_model_is_offered_only_the_pick_of_an_unprocessed_hit_and_no_read_search_or_reasoning_tool():
    task = importlib.import_module(PACKAGE + '.task')
    assert set(EPISODE.tools) == {task.RUN_SEARCH, task.LIST, task.ASSESS, task.FETCH}
    schema = task.selection_schema({'input_list': ['PMC1', 'PMC2']})
    options = schema['properties']['selection']['anyOf']
    assert len(options) == 1
    pick = options[0]['properties']
    assert pick['kind'] == {'const': 'tool'} and pick['tool'] == {'const': task.FETCH}
    # the pick names the hit and nothing else: no objective, no experiment type; a processed hit is not selectable
    assert list(pick['arguments']['properties']) == ['hit'] and pick['arguments']['properties']['hit'] == {
        'enum': ['PMC1', 'PMC2']}
    assert task.hit_tools([]) == []
    assert set(task.CHILD_ARGUMENTS) == set(EPISODE.child_slots) == set(task.CHILD_SLOTS)


def test_the_page_commission_is_one_paper_with_the_fixed_objective_and_the_sheet_states():
    to_child = importlib.import_module(PACKAGE + '.messages.msg_to_child')
    summary = {**summary_of(), 'sheet_state_refs': ['state_1']}
    message = to_child.msg_to_child('page', {'hit': 'PMC1', 'page': PAGE}, summary)
    assert message.objective == 'evidence_location_unknown'
    assert set(message.selection) == {'sheet_state_refs', 'literature_source_lead_dispositions'}
    assert message.assignment['source_ref'] == 'src_1' and message.assignment['artifact_ref'] == 'art_1'
    assert message.assignment['sheet_state_refs'] == ['state_1']
    assert 'search_query_ref' not in message.assignment


def sheet_records(states):
    """A custody reader over sheet states ``{ref: (assertion_ref, [(log_ratio, weight), ...])}``, as the page persists them
    (the fields the measure reads: the row's assertion_ref and each member result's log_ratio and weight)."""
    held = {ref: json.dumps({'row': {'assertion_ref': assertion, 'row_ref': row_ref, 'support': support,
                                     'opposition': opposition}})
            for ref, (assertion, row_ref, support, opposition) in states.items()}
    return types.SimpleNamespace(get_artifact=lambda ref: held[ref])


def test_the_credit_is_the_evidence_the_held_sheet_adds_over_the_given_sheet_additive_and_weighed_by_distance_and_only_the_page_can_raise_it():
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
    offered = types.SimpleNamespace(settings={})
    run_search_summary = {'pending_search': 'src_1', 'pending_listing': None}
    assert credit_module.ceiling(run_search_summary, None, 'run_search', None, offered) == 0.0
    page_summary = {'pending_search': None, 'pending_listing': None, 'search_assessment_ref': 'a', 'search_result_candidates': ['x'],
                    'pending_page': {'hit': 'PMC1'}, 'input_list': []}
    assert credit_module.ceiling(page_summary, None, 'page', None, offered) is UNBOUNDED
