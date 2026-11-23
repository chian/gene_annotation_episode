"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set, its child folder and the two child folders no longer commissioned (to be deleted); no
module of the episode imports another episode folder; the episode's own forms and functions behave on real data; its
commission is admitted by the real form of its child (read by name at test time, never imported by the episode).
Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildCall, EpisodeBinding
from method_loop import UNBOUNDED, FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').PublishedEvidenceAssessment
OWN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
             'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
             'tests/__init__.py', 'tests/test_binding.py'}
CHILDREN = ('evidence_search_strategy_improvement',)
# No longer commissioned (the launch and the results of an execution are no part of the literature shape); their
# folders are left to be deleted.
ORPHANED = ('execution_job_submission', 'execution_result_acquisition')
ROOT = 'gene_annotation_episode.episodic_workflow.root'
EMPTY = {'intervention_assessments': [], 'a106_subscores': []}
CTX = 'record_' + 'd' * 24
SRC = 'source_' + 'a' * 24
TASK = {'kind': 'verified_source_leads', 'evidence_axis': 'A106', 'credit_unit': 1.0}
ASSIGNMENT = {'version': 'literature_assignment', 'question_context_refs': ['ctx_1'],
              'literature_task': TASK, 'proposed_annotation_ref': 'hyp_1', 'scope': {'subject_refs': ['sub_1']},
              'received_record_refs': ['ctx_1', 'hyp_1']}


def child_module(name, module):
    return importlib.import_module(PACKAGE + '.' + name + '.' + module)


def own_files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts
            and path.relative_to(FOLDER).parts[0] not in (*CHILDREN, *ORPHANED)}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert EPISODE.binding_path == 'perturbation_evidence/published_evidence_assessment'
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {
        'literature_strategy': EPISODE.binding_path + '/evidence_search_strategy_improvement'}
    assert tuple(EPISODE.services) == ()


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_children_and_its_child_folder():
    assert own_files() == OWN_FILES
    assert {path.name for path in FOLDER.iterdir() if path.is_dir() and path.name != '__pycache__'} \
        >= {'messages', 'tests', *CHILDREN}


def test_no_module_of_the_episode_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        relative = path.relative_to(FOLDER)
        if relative.parts[0] in (*CHILDREN, *ORPHANED) or relative.parts[0] == 'tests':
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.level:      # relative: only within this episode's folder
                assert node.level == len(relative.parts), str(relative)
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT), str(relative) + ' imports ' + module


def test_the_commission_form_admits_a_literature_assignment_and_refuses_an_unknown_field_or_another_task():
    form = EPISODE.assignment_form
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'literature'})
    assert parent_input['literature'] == {'version': 'literature_assignment', 'question_context_refs': ['ctx_1']}
    assert parent_input['task_key'] == 'A106:verified_source_leads'
    assert set(form.record_refs(admitted)) == {'ctx_1', 'hyp_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    with pytest.raises(FormError, match='unknown_field'):      # no paper is handed to the chain
        form.admit({**ASSIGNMENT, 'source_refs': [SRC]}, 'test')
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'requested_rate_components': []}, 'test')
    with pytest.raises(ValueError, match='literature_finite_task_credit_unit_required'):
        EPISODE.read_from_parent({**admitted, 'literature_task': {**TASK, 'credit_unit': 0}}, {})
    with pytest.raises(ValueError, match='literature_original_task_invalid'):
        EPISODE.read_from_parent({**admitted, 'literature_task': {**TASK, 'evidence_axis': 'A105'}}, {})
    for other in ({'kind': 'source_answer', 'answer_kind': 'screening'}, {'kind': 'source_answer'}):
        with pytest.raises(ValueError, match='literature_original_task_invalid'):
            EPISODE.read_from_parent({**admitted, 'literature_task': {**TASK, **other}}, {})


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


def test_the_credit_counts_the_relevant_leads_and_the_ceiling_is_unbounded_for_the_strategy_only():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit and EPISODE.ceiling is credit_module.ceiling
    assert 'NotImplementedError' not in (FOLDER / 'credit.py').read_text()
    summary = {'task': {'kind': 'verified_source_leads', 'credit_unit': 2.0}, 'task_key': 'A106:verified_source_leads',
               'source_leads': [], 'proposed_annotation_ref': 'hyp_1'}
    assert credit_module.credit(summary, None) == 0
    assert credit_module.ceiling(summary, None, 'literature_strategy', None, None) is UNBOUNDED
    assert credit_module.ceiling(summary, None, 'state_query', None, None) == 0.0
    with pytest.raises(ValueError, match='ceiling_unknown_action_type'):
        credit_module.ceiling(summary, None, 'reason', None, None)
    with pytest.raises(ValueError, match='literature_task_kind_not_carried'):
        credit_module.credit({**summary, 'task': {'kind': 'source_answer', 'credit_unit': 2.0}}, None)


def test_the_model_is_offered_the_reading_of_held_records_and_the_strategy_child_only():
    task = importlib.import_module(PACKAGE + '.task')
    assert task.offered() == ['state_query'] and set(EPISODE.tools) == {'state_query'}
    assert {entry['name'] for entry in task.catalog()} == {'state_query'}      # no search, fetch, read or reason
    assert task.offered_actions({}, None) == ['state_query', 'literature_strategy']
    assert task.offered_slots() == list(EPISODE.child_slots) == ['literature_strategy']
    schema = task.selection_schema()
    assert len(schema['properties']['selection']['anyOf']) == 2
    task.generation_schema(schema)
    assert 'You cannot search, fetch or read a paper' in task.instructions()


def test_the_strategy_commission_is_admitted_by_the_form_of_the_child_and_selects_what_the_task_counts():
    task = importlib.import_module(PACKAGE + '.task')
    child_task = {'version': 'literature_local_task', 'evidence_axis': 'A106', 'kind': 'verified_source_leads'}
    arguments = {'question_context_refs': [CTX], 'literature_task': child_task}
    task.validate_selection({'selection': {'kind': 'child', 'slot': 'literature_strategy', 'arguments': arguments}},
                            task.selection_schema())
    with pytest.raises(Exception):      # no prior search or source is part of the commission
        task.validate_selection({'selection': {'kind': 'child', 'slot': 'literature_strategy',
                                               'arguments': {**arguments, 'prior_search_refs': [SRC]}}},
                                task.selection_schema())
    parent_input = EPISODE.read_from_parent(ASSIGNMENT, {})
    summary = {'task': parent_input['task'], 'proposed_annotation_ref': parent_input['proposed_annotation_ref'],
               'scope': parent_input['scope']}
    message = EPISODE.msg_to_child('literature_strategy', ChildCall('literature_strategy', arguments).arguments,
                                   summary)
    read = child_module('evidence_search_strategy_improvement', 'messages.read_from_parent')
    admitted = read.ASSIGNMENT_FORM.admit(message.assignment, 'commission')
    assert set(read.ASSIGNMENT_FORM.record_refs(admitted)) == {CTX, 'hyp_1'}
    assert admitted['literature_task']['credit_unit'] == 1.0
    assert read.read_from_parent(admitted, {})['strategy'] == {'version': 'strategy_assignment',
                                                               'question_context_refs': [CTX]}
    child_return = child_module('evidence_search_strategy_improvement', 'messages.final_to_parent').RETURN_FORM
    selected = child_return.select(message.selection)
    assert set(message.selection) == {'literature_source_lead_dispositions'}
    assert 'credit' in selected.fields and 'finding' in selected.fields
    returned = {'credit': 1.0, 'finding': EMPTY,
                'literature_source_lead_dispositions': {'relevant_lead_count': 1, 'lead_source_refs': [SRC]}}
    selected.admit(returned, 'return')
    report = EPISODE.read_from_child('literature_strategy', returned, summary, None)
    assert report == {'slot': 'literature_strategy', 'credit': 1.0, 'finding': EMPTY, 'lead_source_refs': [SRC]}
    with pytest.raises(KeyError):      # a slot this episode does not offer is a wrong commission: it fails
        EPISODE.msg_to_child('launch', arguments, summary)
