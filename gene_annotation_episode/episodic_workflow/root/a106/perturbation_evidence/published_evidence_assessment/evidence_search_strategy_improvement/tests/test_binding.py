"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set and its child folder; no module of the episode imports another episode folder; the
episode's own forms and functions behave on real data; its commission is admitted by the real form of the search
child (read by name at test time, never imported by the episode). Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildCall, EpisodeBinding
from method_loop import UNBOUNDED, FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').EvidenceSearchStrategyImprovement
OWN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
             'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
             'tests/__init__.py', 'tests/test_binding.py'}
CHILDREN = ('source_relevance_assessment',)
ROOT = 'gene_annotation_episode.episodic_workflow.root'
EMPTY = {'intervention_assessments': [], 'a106_subscores': []}
SRC = 'source_' + 'a' * 24
QUERY = 'source_' + 'b' * 24
OTHER = 'source_' + 'c' * 24
CTX = 'record_' + 'd' * 24
TASK = {'kind': 'verified_source_leads', 'evidence_axis': 'A106', 'credit_unit': 1.0}
ASSIGNMENT = {'version': 'strategy_assignment', 'question_context_refs': [CTX],
              'literature_task': TASK, 'proposed_annotation_ref': 'hyp_1', 'scope': {'subject_refs': ['sub_1']},
              'received_record_refs': [CTX, 'hyp_1']}


def child_module(name, module):
    return importlib.import_module(PACKAGE + '.' + name + '.' + module)


def own_files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts
            and path.relative_to(FOLDER).parts[0] not in CHILDREN}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {'literature_search': EPISODE.binding_path + '/source_relevance_assessment'}


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


def test_the_commission_form_admits_a_strategy_assignment_and_refuses_an_unknown_field_or_another_task():
    form = EPISODE.assignment_form
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'strategy'})
    assert parent_input['strategy'] == {'version': 'strategy_assignment', 'question_context_refs': [CTX]}
    assert parent_input['task_key'] == 'A106:verified_source_leads'
    assert set(form.record_refs(admitted)) == {CTX, 'hyp_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    with pytest.raises(FormError, match='unknown_field'):      # no prior search is handed to a strategy
        form.admit({**ASSIGNMENT, 'prior_search_refs': [SRC]}, 'test')
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


def test_the_credit_counts_the_relevant_leads_and_the_ceiling_is_unbounded_for_the_search_only():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit and EPISODE.ceiling is credit_module.ceiling
    summary = {'task': {'kind': 'verified_source_leads', 'credit_unit': 2.0}, 'task_key': 'A106:verified_source_leads',
               'source_leads': [], 'proposed_annotation_ref': 'hyp_1'}
    assert credit_module.credit(summary, None) == 0
    assert credit_module.ceiling(summary, None, 'literature_search', None, None) is UNBOUNDED
    for name in ('state_query', 'write_search'):
        assert credit_module.ceiling(summary, None, name, None, None) == 0.0
    with pytest.raises(ValueError, match='ceiling_unknown_action_type'):
        credit_module.ceiling(summary, None, 'reason', None, None)


def test_the_model_writes_one_query_reads_held_records_and_commissions_the_search_with_a_written_query_only():
    task = importlib.import_module(PACKAGE + '.task')
    assert set(EPISODE.tools) == {'state_query', 'write_search'} and task.offered() == list(EPISODE.tools)
    assert [entry['name'] for entry in task.catalog()] == ['state_query', 'write_search']
    # The search child is offered only while a written query not yet handed out remains.
    assert task.commissions([]) == []
    assert [entry['slot'] for entry in task.commissions([QUERY])] == list(EPISODE.child_slots)
    assert len(task.selection_schema([])['properties']['selection']['anyOf']) == 2
    assert len(task.selection_schema([QUERY])['properties']['selection']['anyOf']) == 3
    task.generation_schema(task.selection_schema([QUERY]))
    assert task.offered_actions({'input_list': []}, None) == ['state_query', 'write_search']
    assert task.offered_actions({'input_list': [QUERY]}, None) == ['state_query', 'write_search', 'literature_search']
    schema = task.commission_arguments([QUERY])
    assert schema['properties'] == {'search_query_ref': {'enum': [QUERY]}}      # one query, by reference
    task.validate_selection({'selection': {'kind': 'child', 'slot': 'literature_search',
                                           'arguments': {'search_query_ref': QUERY}}},
                            task.selection_schema([QUERY]))
    with pytest.raises(Exception):      # a query already handed out is no longer offered
        task.validate_selection({'selection': {'kind': 'child', 'slot': 'literature_search',
                                               'arguments': {'search_query_ref': QUERY}}},
                                task.selection_schema([OTHER]))
    with pytest.raises(Exception):      # one query, no paper
        task.validate_selection({'selection': {'kind': 'child', 'slot': 'literature_search',
                                               'arguments': {'search_query_ref': QUERY, 'search_result_refs': [SRC]}}},
                                task.selection_schema([QUERY]))
    written = task.validate_selection(
        {'selection': {'kind': 'tool', 'tool': 'write_search',
                       'arguments': {'query': 'rpoB knockout rescue', 'size': 25}}}, task.selection_schema([]))
    assert written['tool'] == 'write_search'


def test_the_commission_is_admitted_by_the_form_of_the_search_child_and_selects_what_the_task_counts():
    parent_input = EPISODE.read_from_parent(ASSIGNMENT, {})
    summary = {'task': parent_input['task'], 'strategy': parent_input['strategy'],
               'proposed_annotation_ref': parent_input['proposed_annotation_ref'], 'scope': parent_input['scope']}
    arguments = ChildCall('literature_search', {'search_query_ref': QUERY}).arguments
    message = EPISODE.msg_to_child('literature_search', arguments, summary)
    read = child_module('source_relevance_assessment', 'messages.read_from_parent')
    admitted = read.ASSIGNMENT_FORM.admit(message.assignment, 'commission')
    assert set(read.ASSIGNMENT_FORM.record_refs(admitted)) == {CTX, QUERY, 'hyp_1'}
    assert admitted['search_query_ref'] == QUERY and admitted['literature_task']['credit_unit'] == 1.0
    assert read.read_from_parent(admitted, {})['search']['search_query_ref'] == QUERY
    child_return = child_module('source_relevance_assessment', 'messages.final_to_parent').RETURN_FORM
    selected = child_return.select(message.selection)
    assert set(message.selection) == {'literature_source_lead_dispositions'}
    assert 'credit' in selected.fields and 'finding' in selected.fields
    returned = {'credit': 1.0, 'finding': EMPTY,
                'literature_source_lead_dispositions': {'relevant_lead_count': 1, 'lead_source_refs': [SRC]}}
    selected.admit(returned, 'return')
    assert EPISODE.read_from_child('literature_search', returned, summary, None) == {
        'slot': 'literature_search', 'credit': 1.0, 'finding': EMPTY, 'lead_source_refs': [SRC]}
    assert EPISODE.read_from_child('literature_search', {'credit': 0.0, 'finding': EMPTY}, summary, None) == {
        'slot': 'literature_search', 'credit': 0.0, 'finding': EMPTY}


def test_the_input_list_is_the_written_queries_not_yet_handed_to_a_search():
    summary_module = importlib.import_module(PACKAGE + '.messages.internal_summary')
    written = [{'kind': 'tool', 'tool': 'write_search', 'outcome': {'status': 'completed', 'result': {'search_ref': ref}}}
               for ref in (QUERY, OTHER)]
    failed = {'kind': 'tool', 'tool': 'write_search', 'outcome': {'status': 'failed'}}
    assert summary_module.written_searches([*written, failed]) == [QUERY, OTHER]
    children = [{'kind': 'child', 'slot': 'literature_search', 'arguments': {'search_query_ref': QUERY}}]
    assert summary_module.consumed_searches(children) == [QUERY]
    assert summary_module.consumed_searches([]) == []
