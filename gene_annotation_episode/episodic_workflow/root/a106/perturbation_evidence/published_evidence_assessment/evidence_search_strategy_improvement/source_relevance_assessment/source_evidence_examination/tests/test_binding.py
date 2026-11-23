"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set and its children; no module of the episode imports another episode folder; the
episode's own forms and functions behave on real data; its commissions are admitted by the real forms of the three
children (read by name at test time, never imported by the episode). Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildCall, EpisodeBinding, ToolCall
from method_loop import FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceEvidenceExamination
OWN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
             'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
             'tests/__init__.py', 'tests/test_binding.py', 'tests/test_model_run.py'}
CHILDREN = ('table_evidence_extraction', 'source_coverage_improvement', 'passage_evidence_extraction')
ROOT = 'gene_annotation_episode.episodic_workflow.root'
EMPTY = {'intervention_assessments': [], 'a106_subscores': []}
SRC = 'source_' + 'a' * 24
PAGE = {'version': 'page_assignment', 'source_ref': SRC, 'representation': 'original', 'artifact_ref': 'art_1',
        'question_context_refs': ['ctx_1'], 'prior_delivery_refs': []}
TASK = {'kind': 'verified_source_leads', 'evidence_axis': 'A106', 'credit_unit': 1.0}
ASSIGNMENT = {**PAGE, 'literature_task': TASK, 'proposed_annotation_ref': 'hyp_1',
              'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': [SRC, 'art_1', 'hyp_1']}


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
    assert dict(EPISODE.child_slots) == {name: EPISODE.binding_path + '/' + folder for name, folder in (
        ('literature_table', 'table_evidence_extraction'), ('literature_ordered', 'source_coverage_improvement'),
        ('literature_targeted', 'passage_evidence_extraction'))}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_children_and_its_child_folders():
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


def test_the_commission_form_admits_a_page_assignment_and_refuses_an_unknown_field_and_any_other_task():
    form = EPISODE.assignment_form
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {})
    assert parent_input['page'] == PAGE and parent_input['task_key'] == 'A106:verified_source_leads'
    assert set(form.record_refs(admitted)) == {'ctx_1', SRC, 'art_1', 'hyp_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    for task in ({'kind': 'source_answer', 'answer_kind': 'assessment', 'evidence_axis': 'A106', 'credit_unit': 1.0,
                  'source_refs': [SRC]},
                 {'kind': 'source_answer', 'answer_kind': 'screening', 'evidence_axis': 'A106', 'credit_unit': 1.0,
                  'examined': []}):
        with pytest.raises(ValueError, match='literature_original_task_invalid'):
            EPISODE.read_from_parent({**admitted, 'literature_task': task}, {})


def test_the_controller_is_built_from_the_parent_input_alone():
    parent_input = EPISODE.read_from_parent(ASSIGNMENT, {})
    controller = EPISODE.yield_controller(0, {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}, parent_input)
    assert type(controller).__name__ == 'AccumulationYieldController'


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    assert not form.fields['literature_source_lead_dispositions'].required
    assert 'literature_screening_answers' not in form.fields
    summary = {'a106_findings': EMPTY}
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())
    assert result['credit'] == 2.5 and result['finding'] == EMPTY
    form.admit(result, 'test')


def test_the_credit_counts_nothing_without_a_relevant_lead_and_the_ceiling_is_one_unit_for_a_leaf_only():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit and EPISODE.ceiling is credit_module.ceiling
    summary = {'task': {'kind': 'verified_source_leads', 'credit_unit': 2.0}, 'task_key': 'A106:verified_source_leads',
               'source_leads': [], 'proposed_annotation_ref': 'hyp_1'}
    assert credit_module.credit(summary, None) == 0
    for slot in EPISODE.child_slots:
        assert credit_module.ceiling(summary, None, slot, None, None) == 2.0
    assert credit_module.ceiling(summary, None, 'assess_content', None, None) == 0.0
    with pytest.raises(ValueError, match='ceiling_unknown_action_type'):
        credit_module.ceiling(summary, None, 'reason', None, None)


def input_summary(consumed=(), assessed=True):
    """The input-list part of the summary over a real source: a prose section, an HTML table and more prose; the
    candidates ``consumed`` (ids) have been handed out."""
    page_content = importlib.import_module('gene_annotation_episode.episodic_workflow.episode_support.literature.'
                                           'readers.perturbation_evidence.literature_page_content')
    content = (('Methods. ' + 'The knockout strain was grown in medium. ' * 80 + '\n')
               + '<table><tr><td>strain</td><td>growth</td></tr><tr><td>KO</td><td>1</td></tr></table>\n'
               + ('Results. ' + 'Growth was reduced in the mutant. ' * 80)).encode('utf-8')
    candidates = page_content.page_candidates(content)
    left = [item for item in candidates if item['candidate_id'] not in consumed]
    return {'content_candidates': candidates, 'consumed_candidate_ids': list(consumed),
            'unconsumed_table_ids': [i['candidate_id'] for i in left if i['candidate_type'] == page_content.SOURCE_TABLE],
            'unconsumed_chunk_ids': [i['candidate_id'] for i in left if i['candidate_type'] == page_content.PROSE_CHUNK],
            'report_windows': page_content.report_windows(candidates, {item['candidate_id'] for item in left}),
            'input_list': [item['candidate_id'] for item in left],
            'content_assessment_ref': 'art_assessment' if assessed else None}


def test_the_page_assesses_automatically_first_and_then_offers_only_leaves_and_no_tool_that_reads():
    task = importlib.import_module(PACKAGE + '.task')
    assert set(EPISODE.tools) == {'assess_content'}
    before = {**input_summary(assessed=False), 'page': PAGE, 'jev_goal': {}, 'jev_page_context': {},
              'information_needs': []}
    assert task.offered_actions(before, None) == ['assess_content']
    call = task.decide(before, None, None)
    assert isinstance(call, ToolCall) and call.name == 'assess_content'
    held = input_summary()
    assert task.offered_actions(held, None) == list(EPISODE.child_slots)
    assert [entry['slot'] for entry in task.child_options({**held, 'table_previews': {
        name: '' for name in held['unconsumed_table_ids']}})] == list(EPISODE.child_slots)
    task.generation_schema(task.selection_schema(held))
    assert len(task.selection_schema(held)['properties']['selection']['anyOf']) == 3


def commission_arguments(slot, summary):
    return {'literature_table': {'candidate_id': summary['unconsumed_table_ids'][0]}, 'literature_ordered': {},
            'literature_targeted': {'candidate_id': summary['unconsumed_chunk_ids'][0]}}[slot]


COMMISSIONS = {
    'literature_table': 'table_evidence_extraction',
    'literature_ordered': 'source_coverage_improvement',
    'literature_targeted': 'passage_evidence_extraction',
}


def commission_summary(held):
    parent_input = EPISODE.read_from_parent(ASSIGNMENT, {})
    return {'page': parent_input['page'], 'task': parent_input['task'],
            'proposed_annotation_ref': parent_input['proposed_annotation_ref'], 'scope': parent_input['scope'],
            'received_record_refs': parent_input['received_record_refs'],
            'content_candidates': held['content_candidates'], 'report_windows': held['report_windows']}


@pytest.mark.parametrize('slot', sorted(COMMISSIONS))
def test_each_commission_is_admitted_by_the_form_of_the_child_it_names(slot):
    folder = COMMISSIONS[slot]
    task = importlib.import_module(PACKAGE + '.task')
    held = input_summary()
    arguments = commission_arguments(slot, held)
    task.validate_schema({'selection': {'slot': slot, 'arguments': arguments}}, task.selection_schema(held))
    summary = commission_summary(held)
    message = EPISODE.msg_to_child(slot, ChildCall(slot, arguments).arguments, summary)
    assert message.message == {}
    assert message.objective == importlib.import_module(PACKAGE + '.messages.msg_to_child').OBJECTIVES[slot]
    child_form = child_module(folder, 'messages.read_from_parent').ASSIGNMENT_FORM
    admitted = child_form.admit(message.assignment, 'commission')
    assert child_form.record_refs(admitted)
    assert 'None' not in repr(admitted)
    child_return = child_module(folder, 'messages.final_to_parent').RETURN_FORM
    selected = child_return.select(message.selection)
    assert set(message.selection) == {'literature_source_lead_dispositions'}
    assert 'credit' in selected.fields and 'finding' in selected.fields
    returned = {'credit': 1.0, 'finding': EMPTY,
                'literature_source_lead_dispositions': {'relevant_lead_count': 1, 'lead_source_refs': [SRC]}}
    selected.admit(returned, 'return')
    assert EPISODE.read_from_child(slot, returned, summary, None) == {
        'slot': slot, 'credit': 1.0, 'finding': EMPTY, 'lead_source_refs': [SRC]}


def test_the_input_list_shrinks_as_candidates_are_handed_out_and_a_consumed_candidate_cannot_be_commissioned():
    task = importlib.import_module(PACKAGE + '.task')
    internal = importlib.import_module(PACKAGE + '.messages.internal_summary')
    held = input_summary()
    table, chunk = held['unconsumed_table_ids'][0], held['unconsumed_chunk_ids'][0]
    summary = commission_summary(held)
    message = EPISODE.msg_to_child('literature_targeted', {'candidate_id': chunk}, summary)
    consumed = internal.consumed_candidates([{'kind': 'child', 'message': {'assignment': message.assignment}}],
                                            held['content_candidates'])
    assert consumed == [chunk]
    message = EPISODE.msg_to_child('literature_table', {'candidate_id': table}, summary)
    consumed += internal.consumed_candidates([{'kind': 'child', 'message': {'assignment': message.assignment}}],
                                             held['content_candidates'])
    after = input_summary(consumed)
    assert after['input_list'] == [item for item in held['input_list'] if item not in consumed]
    assert after['unconsumed_table_ids'] == [] and chunk not in after['unconsumed_chunk_ids']
    assert task.available_slots(after) == ['literature_ordered', 'literature_targeted']
    with pytest.raises(Exception):
        task.validate_schema({'selection': {'slot': 'literature_table', 'arguments': {'candidate_id': table}}},
                             task.selection_schema(after))
    with pytest.raises(Exception):
        task.validate_schema({'selection': {'slot': 'literature_targeted', 'arguments': {'candidate_id': chunk}}},
                             task.selection_schema(after))
    everything = input_summary([item['candidate_id'] for item in held['content_candidates']])
    assert everything['input_list'] == [] and task.available_slots(everything) == []
    ordered = EPISODE.msg_to_child('literature_ordered', {}, summary)
    windows = internal.consumed_candidates([{'kind': 'child', 'message': {'assignment': ordered.assignment}}],
                                           held['content_candidates'])
    assert set(windows) == set(held['unconsumed_chunk_ids'][:len(windows)]) and windows
