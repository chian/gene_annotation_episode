"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set and its children; no module of the episode imports another episode folder; the
episode's own forms and functions behave on real data; its commissions are admitted by the real forms of the three
children (read by name at test time, never imported by the episode). Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildCall, EpisodeBinding
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
NONE = {'literature_populations': [], 'literature_evidence_origins': {}}
EMPTY = {'intervention_assessments': [], 'a106_subscores': []}
COMMIT_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['terms'],
                 'properties': {'terms': {'type': 'array'}}}
SRC = 'source_' + 'a' * 24
PAGE = {'version': 'page_assignment_v1', 'source_ref': SRC, 'representation': 'original', 'artifact_ref': 'art_1',
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


def test_the_commission_form_admits_a_page_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'examine'})
    assert parent_input['page'] == PAGE and parent_input['task_key'] == 'A106:verified_source_leads'
    assert set(form.record_refs(admitted)) == {'ctx_1', SRC, 'art_1', 'hyp_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    outside = {**admitted, 'literature_task': {'kind': 'source_answer', 'answer_kind': 'assessment',
                                               'evidence_axis': 'A106', 'credit_unit': 1.0,
                                               'source_refs': ['source_' + 'b' * 24]}}
    with pytest.raises(ValueError, match='literature_task_outside_assigned_source'):
        EPISODE.read_from_parent(outside, {})


def test_the_controller_is_built_from_the_parent_input_alone():
    parent_input = EPISODE.read_from_parent(ASSIGNMENT, {})
    settings = {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}
    controller = EPISODE.yield_controller(0, settings, parent_input)
    assert type(controller).__name__ == 'AccumulationYieldController'
    answer = {**ASSIGNMENT, 'literature_task': {'kind': 'source_answer', 'answer_kind': 'screening',
                                                'evidence_axis': 'A106', 'credit_unit': 2.0,
                                                'examined': [{'source_ref': SRC, 'artifact_ref': 'art_1',
                                                              'start': 0, 'end': 5}]}}
    controller = EPISODE.yield_controller(0, settings, EPISODE.read_from_parent(answer, {}))
    assert type(controller).__name__ == 'CompletionYieldController'


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    assert not form.fields['literature_source_lead_dispositions'].required
    assert not form.fields['literature_screening_answers'].required
    summary = {'a106_findings': EMPTY}
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())
    assert result['credit'] == 2.5 and result['finding'] == EMPTY
    form.admit(result, 'test')


def test_the_credit_is_real_code_and_counts_nothing_without_a_validated_lead():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    assert 'NotImplementedError' not in (FOLDER / 'credit.py').read_text()
    summary = {'task': {'kind': 'verified_source_leads', 'credit_unit': 2.0}, 'task_key': 'A106:verified_source_leads',
               'source_leads': [], 'proposed_annotation_ref': 'hyp_1'}
    assert credit_module.credit(summary, None) == 0


def test_the_model_is_offered_the_access_tools_the_graders_the_reasoning_and_the_three_investigations():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered(NONE, None)
    assert 'execution_estimate' not in names and names[-2:] == ['literature_a106_score_judgment', 'reason']
    assert len(names) == 17
    opened = task.offered(NONE, 'literature_a106_finalize')
    assert 'literature_a106_finalize' in opened and set(opened) <= set(EPISODE.tools)
    assert set(names) <= set(EPISODE.tools)
    for leads in (False, True):
        schema = task.selection_schema(names, COMMIT_SCHEMA, leads, NONE, input_summary())
        assert len(schema['properties']['selection']['anyOf']) == len(names) + 3
        task.generation_schema(schema)
    assert [entry['slot'] for entry in task.commissions(input_summary())] == list(EPISODE.child_slots)
    reason = [entry for entry in task.catalog(names, COMMIT_SCHEMA, True, NONE) if entry['name'] == 'reason'][0]
    assert 'source_lead' in reason['input_schema']['properties']
    assert 'source_lead' not in task.reason_schema(COMMIT_SCHEMA, False)['properties']
    assert 'execution_estimate' in task.offered({**NONE, 'tool_registry': {'native_statistics': object()}}, None)
    assert task.empty_commit({'terms': []}, COMMIT_SCHEMA) and not task.empty_commit({'terms': [{}]}, COMMIT_SCHEMA)


def input_summary(consumed=()):
    """The input-list part of the summary over a real source: a prose section, an HTML table and more prose; the
    candidates ``consumed`` (ids) have been handed out."""
    internal = importlib.import_module(PACKAGE + '.messages.internal_summary')
    content = (('Methods. ' + 'The knockout strain was grown in medium. ' * 80 + '\n') + '<table><tr><td>strain</td><td>growth</td></tr><tr><td>KO</td><td>1</td></tr></table>\n'
               + ('Results. ' + 'Growth was reduced in the mutant. ' * 80)).encode('utf-8')
    candidates = internal.page_candidates(content)
    left = [item for item in candidates if item['candidate_id'] not in consumed]
    return {'content_candidates': candidates, 'consumed_candidate_ids': list(consumed),
            'unconsumed_table_ids': [i['candidate_id'] for i in left if i['candidate_type'] == internal.SOURCE_TABLE],
            'unconsumed_chunk_ids': [i['candidate_id'] for i in left if i['candidate_type'] == internal.PROSE_CHUNK],
            'report_windows': internal.report_windows(candidates, {item['candidate_id'] for item in left}),
            'input_list': [item['candidate_id'] for item in left]}


def commission_arguments(slot, summary):
    table = summary['unconsumed_table_ids'][0]
    return {'literature_table': {'candidate_id': table}, 'literature_ordered': {},
            'literature_targeted': {'candidate_ids': [summary['unconsumed_chunk_ids'][0], table]}}[slot]


COMMISSIONS = {
    'literature_table': 'table_evidence_extraction',
    'literature_ordered': 'source_coverage_improvement',
    'literature_targeted': 'passage_evidence_extraction',
}


@pytest.mark.parametrize('slot', sorted(COMMISSIONS))
def test_each_commission_is_admitted_by_the_form_of_the_child_it_names(slot):
    folder = COMMISSIONS[slot]
    task = importlib.import_module(PACKAGE + '.task')
    held = input_summary()
    arguments = commission_arguments(slot, held)
    task.validate_selection({'selection': {'kind': 'child', 'slot': slot, 'arguments': arguments}},
                            task.selection_schema(task.offered(NONE, None), COMMIT_SCHEMA, True, NONE, held))
    summary = importlib.import_module(PACKAGE + '.messages.internal_summary')
    parent_input = EPISODE.read_from_parent(ASSIGNMENT, {})
    commission_summary = {'page': parent_input['page'], 'task': parent_input['task'],
                          'proposed_annotation_ref': parent_input['proposed_annotation_ref'],
                          'scope': parent_input['scope'], 'received_record_refs': parent_input['received_record_refs'],
                          'content_candidates': held['content_candidates'], 'report_windows': held['report_windows']}
    assert summary.internal_summary is EPISODE.internal_summary
    message = EPISODE.msg_to_child(slot, ChildCall(slot, arguments).arguments, commission_summary)
    assert message.message == {} and message.objective == task_messages().OBJECTIVES[slot]
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
    read = EPISODE.read_from_child(slot, returned, commission_summary, None)
    assert read == {'slot': slot, 'credit': 1.0, 'finding': EMPTY, 'lead_source_refs': [SRC]}


def test_the_input_list_shrinks_as_candidates_are_handed_out_and_a_consumed_candidate_cannot_be_commissioned():
    task = importlib.import_module(PACKAGE + '.task')
    internal = importlib.import_module(PACKAGE + '.messages.internal_summary')
    held = input_summary()
    table = held['unconsumed_table_ids'][0]
    chunk = held['unconsumed_chunk_ids'][0]
    parent_input = EPISODE.read_from_parent(ASSIGNMENT, {})
    commission_summary = {**held, 'page': parent_input['page'], 'task': parent_input['task'],
                          'proposed_annotation_ref': 'hyp_1', 'scope': parent_input['scope'],
                          'received_record_refs': parent_input['received_record_refs']}
    message = EPISODE.msg_to_child('literature_targeted', {'candidate_ids': [chunk, table]}, commission_summary)
    outcome = {'kind': 'child', 'message': {'assignment': message.assignment}}
    consumed = internal.consumed_candidates([outcome], held['content_candidates'])
    assert set(consumed) == {chunk, table}
    after = input_summary(consumed)
    assert after['input_list'] == [item for item in held['input_list'] if item not in consumed]
    assert chunk not in after['unconsumed_chunk_ids'] and after['unconsumed_table_ids'] == []
    assert [entry['slot'] for entry in task.commissions(after)] == ['literature_ordered', 'literature_targeted']
    with pytest.raises(Exception):
        task.validate_selection({'selection': {'kind': 'child', 'slot': 'literature_table',
                                               'arguments': {'candidate_id': table}}},
                                task.selection_schema([], COMMIT_SCHEMA, False, NONE, after))
    with pytest.raises(Exception):
        task.validate_selection({'selection': {'kind': 'child', 'slot': 'literature_targeted',
                                               'arguments': {'candidate_ids': [chunk]}}},
                                task.selection_schema([], COMMIT_SCHEMA, False, NONE, after))
    everything = input_summary([item['candidate_id'] for item in held['content_candidates']])
    assert everything['input_list'] == [] and task.commissions(everything) == []
    ordered = EPISODE.msg_to_child('literature_ordered', {}, commission_summary)
    windows = internal.consumed_candidates([{'kind': 'child', 'message': {'assignment': ordered.assignment}}],
                                           held['content_candidates'])
    assert set(windows) == set(held['unconsumed_chunk_ids'][:len(windows)]) and windows


def task_messages():
    return importlib.import_module(PACKAGE + '.messages.msg_to_child')


def test_the_selectable_answers_are_counts_and_references_and_are_admitted():
    form = EPISODE.return_form
    summary = {'a106_findings': EMPTY, 'no_applicable_evidence': [], 'screening_answers': [],
               'source_lead_dispositions': [{'source_ref': SRC, 'disposition': 'relevant'}]}
    both = ('literature_screening_answers', 'literature_source_lead_dispositions')
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0}, both)
    assert result['literature_source_lead_dispositions'] == {'relevant_lead_count': 1, 'lead_source_refs': [SRC]}
    form.select(both).admit(result, 'return')
