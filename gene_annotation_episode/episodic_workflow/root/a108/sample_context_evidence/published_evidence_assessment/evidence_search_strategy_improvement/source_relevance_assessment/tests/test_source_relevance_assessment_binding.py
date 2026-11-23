"""Real checks of the A108 source relevance assessment binding (the search): importing ``episode.py`` runs the system's
class-definition checks, the folder holds exactly the ten-file set, no module imports another episode folder, the
assignment form admits a search assignment with ONE search by reference and its one task kind, the yield controller is
accumulation, the search runs before Jev measures and Jev measures before the model picks one unprocessed hit, a picked
hit is done, the page is commissioned by code on the fetched paper with a fixed objective, and the model has no read
tool and no reasoning commit."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildCall, ChildMessage, EpisodeBinding, ToolCall

MODULE = ('gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.'
          'published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment')
FOLDER = Path(__file__).resolve().parent.parent
CHILDREN = {'source_evidence_examination'}
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


SEARCH = 'source_111111111111111111111111'
ARTICLE, TEXT, ARTICLE_PARENT = ('source_222222222222222222222222', 'artifact_222222222222222222222222',
                                 'source_333333333333333333333333')
CONTEXT, HYPOTHESIS, SUBJECT = ('context_111111111111111111111111', 'hypothesis_111111111111111111111111',
                                'input_111111111111111111111111')
LEADS_TASK = {'version': 'literature_local_task', 'evidence_axis': 'A108', 'credit_unit': 2,
              'kind': 'verified_source_leads'}


def assignment(task=None):
    return {'version': 'search_assignment', 'question_context_refs': [CONTEXT], 'search_query_ref': SEARCH,
            'literature_task': task or LEADS_TASK, 'proposed_annotation_ref': HYPOTHESIS,
            'scope': {'subject_refs': [SUBJECT]}, 'received_record_refs': [SEARCH, HYPOTHESIS]}


def parent_input(task=None):
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    return from_parent.read_from_parent(from_parent.ASSIGNMENT_FORM.admit(assignment(task), 'assignment'),
                                        {'purpose': 'x'})


def test_the_assignment_admits_one_search_by_reference_and_read_from_parent_reads_it():
    value = parent_input()
    assert value['task_key'] == 'A108:verified_source_leads'
    assert value['search_query_ref'] == SEARCH and 'search_result_refs' not in value
    with pytest.raises(Exception):
        parent_input({**LEADS_TASK, 'kind': 'source_answer', 'answer_kind': 'assessment', 'source_refs': [SEARCH]})


def test_the_yield_controller_is_accumulation():
    yield_file = importlib.import_module(MODULE + '.yield_estimator')
    assert type(yield_file.yield_controller(0.0, {}, parent_input())).__name__ == 'AccumulationYieldController'


def summary_of(**fields):
    value = parent_input()
    summary = {'literature_assignment': {'version': 'search_assignment',
                                         'question_context_refs': value['question_context_refs'],
                                         'search_query_ref': SEARCH, 'literature_task': value['task'],
                                         'proposed_annotation_ref': HYPOTHESIS},
               'task': value['task'], 'proposed_annotation_ref': HYPOTHESIS, 'scope': value['scope'],
               'received_record_refs': value['received_record_refs'], 'question_context_refs': [CONTEXT],
               'proposed_annotation_subject_refs': [SUBJECT], 'pending_search': None, 'pending_page': None,
               'search_assessment_ref': 'artifact_444444444444444444444444',
               'search_result_candidates': [{'result_id': 'PMC1'}], 'input_list': ['PMC1', 'PMC2'],
               'held_source_custody': {
                   ARTICLE: {'artifact_ref': 'artifact_111111111111111111111111', 'text_ref': TEXT, 'stdout_ref': None,
                             'stderr_ref': None, 'parent_source_refs': [ARTICLE_PARENT]},
                   ARTICLE_PARENT: {'artifact_ref': 'artifact_333333333333333333333333', 'text_ref': None,
                                    'stdout_ref': None, 'stderr_ref': None, 'parent_source_refs': []}}}
    return {**summary, **fields}


def test_the_search_runs_then_jev_measures_then_the_model_picks_then_code_commissions_the_page():
    task = importlib.import_module(MODULE + '.task')
    credit = importlib.import_module(MODULE + '.credit')
    searching = summary_of(pending_search=SEARCH, search_assessment_ref=None)
    assert task.offered_actions(searching, None) == ['run_search']
    call = task.decide(searching, None, None)
    assert isinstance(call, ToolCall) and call.name == 'run_search'
    assert call.arguments['arguments'] == {'search_query_ref': SEARCH}
    measuring = summary_of(search_assessment_ref=None, jev_search_goal={'g': 1})
    assert task.offered_actions(measuring, None) == ['assess_search_results']
    assert task.decide(measuring, None, None).name == 'assess_search_results'
    page = {'hit': 'PMC1', 'page': {'source_ref': ARTICLE, 'representation': 'text', 'artifact_ref': TEXT,
                                    'prior_delivery_refs': []}}
    opening = summary_of(pending_page=page)
    assert task.offered_actions(opening, None) == ['source_evidence_examination']
    child = task.decide(opening, None, None)
    assert isinstance(child, ChildCall) and child.slot == 'source_evidence_examination' and child.arguments == page
    picking = summary_of()
    assert task.offered_actions(picking, None) == ['fetch_search_hit']
    schema = task.selection_schema(['PMC1', 'PMC2'])
    assert schema['properties']['selection']['anyOf'][0]['properties']['arguments']['properties']['hit']['enum'] == [
        'PMC1', 'PMC2']
    assert set(task.TOOLS) == {'run_search', 'assess_search_results', 'fetch_search_hit'}
    assert [credit.ceiling(None, None, name, None, None) for name in
            ('run_search', 'assess_search_results', 'fetch_search_hit', 'source_evidence_examination')] == [
        0.0, 0.0, 0.0, credit.UNBOUNDED]
    with pytest.raises(LookupError, match='no_hit_left_to_offer'):
        task.decide(summary_of(input_list=[]), None, None)


def test_a_hit_picked_is_done_and_the_page_is_built_from_the_source_record_alone():
    summary = importlib.import_module(MODULE + '.messages.internal_summary')
    outcomes = [{'kind': 'tool', 'tool': 'fetch_search_hit', 'arguments': {'arguments': {'hit': 'PMC1'}},
                 'outcome': {'status': 'completed', 'feedback': None, 'result': {'source_ref': ARTICLE}}},
                {'kind': 'tool', 'tool': 'fetch_search_hit', 'arguments': {'arguments': {'hit': 'PMC2'}},
                 'outcome': {'status': 'failed', 'feedback': {'code': 404}, 'result': None}}]
    assert summary.consumed_hits(outcomes) == ['PMC1', 'PMC2']
    assert summary.hit_fetches(outcomes)[1] == {'hit': 'PMC2', 'status': 'failed', 'provider_status': 404}

    class Records:
        def get(self, ref):
            return {'text_ref': TEXT, 'artifact_ref': 'artifact_111111111111111111111111'}
    assert summary.pending_page(outcomes[0], Records()) == {
        'hit': 'PMC1', 'page': {'source_ref': ARTICLE, 'representation': 'text', 'artifact_ref': TEXT,
                                'prior_delivery_refs': []}}
    assert summary.pending_page(outcomes[1], Records()) is None


def test_the_commission_is_the_page_of_one_paper_with_a_fixed_objective():
    to_child = importlib.import_module(MODULE + '.messages.msg_to_child')
    child_form = importlib.import_module(MODULE + '.source_evidence_examination.messages.read_from_parent')
    page = {'source_ref': ARTICLE, 'representation': 'text', 'artifact_ref': TEXT, 'prior_delivery_refs': []}
    message = to_child.msg_to_child('source_evidence_examination', {'hit': 'PMC1', 'page': page}, summary_of())
    assert isinstance(message, ChildMessage) and message.objective == 'evidence_location_unknown'
    assert message.selection == ('literature_source_lead_dispositions',)
    credit_module = importlib.import_module(MODULE + '.credit')
    held = {'task': dict(LEADS_TASK), 'finding': {'grading_sheets': []}, 'returned_lead_source_refs': ['source_1'],
            'child_reports': [{'credit': 5.0}]}
    assert credit_module.credit(held, None) == 0   # a child's credit and its leads earn nothing; only a held sheet does
    assert message.assignment['version'] == 'page_assignment'
    assert message.assignment['literature_task'] == LEADS_TASK
    assert message.assignment['received_record_refs'] == [
        ARTICLE, 'artifact_111111111111111111111111', TEXT, ARTICLE_PARENT, 'artifact_333333333333333333333333',
        CONTEXT, HYPOTHESIS, SUBJECT, SEARCH]
    child_form.ASSIGNMENT_FORM.admit(message.assignment, 'assignment')
    with pytest.raises(LookupError):
        to_child.msg_to_child('nobody', {'page': page}, summary_of())
