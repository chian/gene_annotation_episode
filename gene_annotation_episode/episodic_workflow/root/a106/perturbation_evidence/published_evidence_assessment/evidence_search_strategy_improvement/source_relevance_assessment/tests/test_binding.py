"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set and its child folder; no module of the episode imports another episode folder; the
episode's own forms and functions behave on real data; its commission is admitted by the real form of the page
child (read by name at test time, never imported by the episode). Nothing here is faked."""
import ast
import importlib
import json
from pathlib import Path

import pytest

from episode_runtime import ChildCall, EpisodeBinding, ToolCall
from method_loop import UNBOUNDED, FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceRelevanceAssessment
OWN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
             'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
             'tests/__init__.py', 'tests/test_binding.py'}
CHILDREN = ('source_evidence_examination',)
ROOT = 'gene_annotation_episode.episodic_workflow.root'
EMPTY = {'intervention_assessments': [], 'a106_subscores': []}
SRC = 'source_' + 'a' * 24
QUERY = 'source_' + 'b' * 24
ART = 'artifact_' + 'c' * 24
TEXT = 'artifact_' + 'e' * 24
CTX = 'record_' + 'd' * 24
TASK = {'kind': 'verified_source_leads', 'evidence_axis': 'A106', 'credit_unit': 1.0}
ASSIGNMENT = {'version': 'search_assignment_v1', 'question_context_refs': [CTX], 'search_query_ref': QUERY,
              'literature_task': TASK, 'proposed_annotation_ref': 'hyp_1', 'scope': {'subject_refs': ['sub_1']},
              'received_record_refs': [CTX, QUERY, 'hyp_1']}
RESPONSE = json.dumps({'resultList': {'result': [
    {'pmcid': 'PMC1', 'pmid': '1', 'doi': '10.1/a', 'title': 'First', 'pubYear': '2020', 'abstractText': 'a',
     'journalInfo': {'journal': {'title': 'J1'}}},
    {'pmid': '2', 'title': 'No full text'},
    {'pmcid': 'PMC2', 'pmid': '3', 'doi': '10.1/b', 'title': 'Second', 'pubYear': '2021', 'abstractText': 'b',
     'journalInfo': {'journal': {'title': 'J2'}}}]}, 'nextCursorMark': 'next'}).encode()


class Records:
    """The reading side of a Store the summary helpers take: one retained search response and one article source."""
    sources = {
        'source_' + '1' * 24: {'provider': 'europepmc', 'uri': 'https://www.ebi.ac.uk/europepmc/webservices/rest/search',
                               'accession': None, 'text_ref': None, 'artifact_ref': ART},
        SRC: {'provider': 'europepmc', 'uri': 'https://x/PMC1', 'accession': 'PMC1', 'text_ref': TEXT,
              'artifact_ref': ART, 'stdout_ref': None, 'stderr_ref': None}}

    def get(self, reference):
        return self.sources[reference]

    def get_artifact(self, reference):
        return RESPONSE


def child_module(name, module):
    return importlib.import_module(PACKAGE + '.' + name + '.' + module)


def own_files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts
            and path.relative_to(FOLDER).parts[0] not in CHILDREN}


def stage(**more):
    """A summary at one stage of the search (only what ``decide`` and ``offered_actions`` read)."""
    return {'pending_page': None, 'pending_search': False, 'unassessed_candidates': [], 'input_list': ['PMC1'],
            'search': {'search_query_ref': QUERY}, 'search_cursor': None, 'scope': {'subject_refs': ['sub_1']},
            'jev_search_goal': {'g': 1}, **more}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {'literature_page': EPISODE.binding_path + '/source_evidence_examination'}
    assert set(EPISODE.tools) == {'run_search', 'assess_search_results', 'fetch_search_hit'}      # no read tool


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_children_and_its_child_folder():
    assert own_files() == OWN_FILES
    assert {path.name for path in FOLDER.iterdir() if path.is_dir() and path.name != '__pycache__'} \
        == {'messages', 'tests', *CHILDREN}


def test_no_module_of_the_episode_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        relative = path.relative_to(FOLDER)
        if relative.parts[0] in CHILDREN or relative.parts[0] == 'tests':
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT), str(relative) + ' imports ' + module


def test_the_commission_form_admits_a_search_assignment_with_one_query_and_refuses_the_rest():
    form = EPISODE.assignment_form
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'search'})
    assert parent_input['search'] == {'version': 'search_assignment_v1', 'question_context_refs': [CTX],
                                      'search_query_ref': QUERY}
    assert parent_input['task_key'] == 'A106:verified_source_leads'
    assert set(form.record_refs(admitted)) == {CTX, QUERY, 'hyp_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    with pytest.raises(FormError, match='unknown_field'):      # no returned source is handed to the search
        form.admit({**ASSIGNMENT, 'search_result_refs': [SRC]}, 'test')
    with pytest.raises(ValueError, match='literature_finite_task_credit_unit_required'):
        EPISODE.read_from_parent({**admitted, 'literature_task': {**TASK, 'credit_unit': 0}}, {})
    with pytest.raises(ValueError, match='literature_original_task_invalid'):
        EPISODE.read_from_parent({**admitted, 'literature_task': {**TASK, 'evidence_axis': 'A105'}}, {})
    with pytest.raises(ValueError, match='literature_original_task_invalid'):
        EPISODE.read_from_parent({**admitted, 'literature_task': {**TASK, 'kind': 'source_answer'}}, {})


def test_the_controller_is_the_accumulation_controller_built_from_the_parent_input_alone():
    controller = EPISODE.yield_controller(0, {}, EPISODE.read_from_parent(ASSIGNMENT, {}))
    assert type(controller).__name__ == 'AccumulationYieldController'


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    assert not form.fields['literature_source_lead_dispositions'].required
    assert 'literature_screening_answers' not in form.fields
    summary = {'a106_findings': EMPTY, 'source_lead_dispositions': [{'source_ref': SRC, 'disposition': 'relevant'}]}
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())
    assert result == {'credit': 2.5, 'finding': EMPTY}
    form.admit(result, 'test')
    selection = ('literature_source_lead_dispositions',)
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0}, selection)
    assert result['literature_source_lead_dispositions'] == {'relevant_lead_count': 1, 'lead_source_refs': [SRC]}
    form.select(selection).admit(result, 'return')


def test_the_credit_counts_the_relevant_leads_and_the_ceilings_are_zero_but_the_one_page_of_one_paper():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit and EPISODE.ceiling is credit_module.ceiling
    summary = {'task': {'kind': 'verified_source_leads', 'credit_unit': 2.0}, 'task_key': 'A106:verified_source_leads',
               'source_leads': [], 'proposed_annotation_ref': 'hyp_1'}
    assert credit_module.credit(summary, None) == 0
    for name in ('run_search', 'assess_search_results', 'fetch_search_hit'):
        assert credit_module.ceiling(summary, None, name, None, None) == 0.0
    assert credit_module.ceiling(summary, None, 'literature_page', None, None) == 2.0 != UNBOUNDED
    with pytest.raises(ValueError, match='ceiling_unknown_action_type'):
        credit_module.ceiling(summary, None, 'reason', None, None)


def test_the_hits_of_the_retained_response_are_ranked_and_picked_one_at_a_time():
    summary_module = importlib.import_module(PACKAGE + '.messages.internal_summary')
    records = Records()
    response = 'source_' + '1' * 24
    hits = summary_module.search_hits([response], records)
    assert [(hit['pmcid'], hit['provider_rank']) for hit in hits] == [('PMC1', 1), ('PMC2', 2)]
    assert summary_module.next_cursor([response], records) == 'next' and summary_module.next_cursor([], records) is None
    picks = [{'kind': 'tool', 'tool': 'fetch_search_hit', 'arguments': {'arguments': {'hit': 'PMC1'}},
              'outcome': {'status': 'failed', 'feedback': {'code': '404'}}}]
    assert summary_module.consumed_hits(picks) == ['PMC1']      # a pick is done, whatever its fetch came to
    assert summary_module.hit_fetches(picks) == [{'hit': 'PMC1', 'status': 'failed', 'provider_status': '404'}]
    assert summary_module.pending_page(picks[-1], records) is None      # a failed fetch commissions no page
    obtained = [{**picks[0], 'outcome': {'status': 'completed', 'feedback': None, 'result': {'source_ref': SRC}}}]
    pending = summary_module.pending_page(obtained[-1], records)
    assert pending == {'hit': 'PMC1', 'page': {
        'source_ref': SRC, 'representation': 'text', 'artifact_ref': TEXT, 'prior_delivery_refs': [],
        'custody': [SRC, ART, TEXT]}}


def test_each_decision_is_the_unit_of_its_stage_and_the_model_is_asked_only_to_pick_a_hit():
    task = importlib.import_module(PACKAGE + '.task')
    page = {'hit': 'PMC1', 'page': {'source_ref': SRC}}
    call = task.decide(stage(pending_page=page), None, None)
    assert isinstance(call, ChildCall) and call.slot == 'literature_page' and call.arguments == page
    assert task.offered_actions(stage(pending_page=page), None) == ['literature_page']
    call = task.decide(stage(pending_search=True, search_cursor='next'), None, None)
    assert isinstance(call, ToolCall) and call.name == 'run_search'
    assert call.arguments['arguments'] == {'search_query_ref': QUERY, 'cursor': 'next'}
    assert task.offered_actions(stage(pending_search=True), None) == ['run_search']
    call = task.decide(stage(unassessed_candidates=[{'result_id': 'PMC1'}]), None, None)
    assert isinstance(call, ToolCall) and call.name == 'assess_search_results'
    assert call.arguments['results'] == [{'result_id': 'PMC1'}] and call.arguments['goal'] == {'g': 1}
    assert task.offered_actions(stage(unassessed_candidates=[{'result_id': 'PMC1'}]), None) == ['assess_search_results']
    assert task.offered_actions(stage(), None) == ['fetch_search_hit']
    schema = task.selection_schema(['PMC1', 'PMC2'])
    task.generation_schema(schema)
    picked = task.validate_selection({'selection': {'kind': 'tool', 'tool': 'fetch_search_hit',
                                                    'arguments': {'hit': 'PMC2'}}}, schema)
    assert picked['arguments'] == {'hit': 'PMC2'}
    with pytest.raises(Exception):      # a hit already picked is no longer offered
        task.validate_selection({'selection': {'kind': 'tool', 'tool': 'fetch_search_hit',
                                               'arguments': {'hit': 'PMC1'}}}, task.selection_schema(['PMC2']))
    call = task.action({'selection': {'kind': 'tool', 'tool': 'fetch_search_hit', 'arguments': {'hit': 'PMC2'}}},
                       stage(input_list=['PMC1', 'PMC2']), None, None)
    assert call.name == 'fetch_search_hit' and call.arguments['arguments'] == {'hit': 'PMC2'}


def test_the_commission_is_admitted_by_the_form_of_the_page_child_and_selects_what_the_task_counts():
    parent_input = EPISODE.read_from_parent(ASSIGNMENT, {})
    summary = {'task': parent_input['task'], 'search': parent_input['search'],
               'proposed_annotation_ref': parent_input['proposed_annotation_ref'], 'scope': parent_input['scope']}
    page = {'hit': 'PMC1', 'page': {'source_ref': SRC, 'representation': 'text', 'artifact_ref': TEXT,
                                    'prior_delivery_refs': [], 'custody': [SRC, ART, TEXT]}}
    message = EPISODE.msg_to_child('literature_page', ChildCall('literature_page', page).arguments, summary)
    read = child_module('source_evidence_examination', 'messages.read_from_parent')
    admitted = read.ASSIGNMENT_FORM.admit(message.assignment, 'commission')
    assert set(read.ASSIGNMENT_FORM.record_refs(admitted)) == {SRC, ART, TEXT, CTX, 'hyp_1'}
    assert admitted['literature_task']['credit_unit'] == 1.0
    assert (admitted['source_ref'], admitted['representation'], admitted['artifact_ref']) == (SRC, 'text', TEXT)
    assert read.read_from_parent(admitted, {})['page']['source_ref'] == SRC
    child_return = child_module('source_evidence_examination', 'messages.final_to_parent').RETURN_FORM
    selected = child_return.select(message.selection)
    assert set(message.selection) == {'literature_source_lead_dispositions'}
    assert 'credit' in selected.fields and 'finding' in selected.fields
    returned = {'credit': 1.0, 'finding': EMPTY,
                'literature_source_lead_dispositions': {'relevant_lead_count': 1, 'lead_source_refs': [SRC]}}
    selected.admit(returned, 'return')
    assert EPISODE.read_from_child('literature_page', returned, summary, None) == {
        'slot': 'literature_page', 'credit': 1.0, 'finding': EMPTY, 'lead_source_refs': [SRC]}
    with pytest.raises(KeyError):      # a paper whose page the code did not fill is a wrong commission: it fails
        EPISODE.msg_to_child('literature_page', {'hit': 'PMC1', 'page': {'source_ref': SRC}}, summary)
