"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode with children (its child episode folders aside); no module of the
folder imports another episode folder; the episode's own forms and functions behave on real data. Nothing here is
faked."""
import ast
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceEvidenceExamination
CHILDREN = ('table', 'report', 'chunk')
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py', 'tests/grading_world.py', 'tests/test_grading.py',
         'tests/test_branch_page_model_run.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
OBJECTIVE = {'objective': 'evidence_location_unknown'}


def own_files():
    return {path for path in FOLDER.rglob('*') if path.is_file() and '__pycache__' not in path.parts
            and path.relative_to(FOLDER).parts[0] not in CHILDREN}


def assignment():
    task = {'version': 'literature_local_task_v1', 'kind': 'verified_source_leads', 'evidence_axis': 'A105',
            'credit_unit': 1.0}
    return {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'text',
            'artifact_ref': 'art_1', 'question_context_refs': ['ctx_1'], 'prior_delivery_refs': [],
            'literature_task': task, 'proposed_annotation_ref': 'hyp_1',
            'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['src_1', 'art_1', 'ctx_1']}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {slot: EPISODE.binding_path + '/' + slot for slot in CHILDREN}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_children_and_its_child_folders():
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


def test_the_commission_form_admits_one_papers_assignment_and_every_other_task_is_a_wrong_commission():
    form = EPISODE.assignment_form
    given = assignment()
    admitted = form.admit(given, 'test')
    parent_input = EPISODE.read_from_parent(admitted, OBJECTIVE)
    assert parent_input['page']['source_ref'] == 'src_1' and parent_input['task_key'] == 'A105:verified_source_leads'
    assert set(form.record_refs(admitted)) == {'src_1', 'art_1', 'ctx_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**given, 'extra': 1}, 'test')
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**given, 'requested_assay_grading_components': []}, 'test')
    wrong_axis = {**admitted, 'literature_task': {**given['literature_task'], 'evidence_axis': 'A106'}}
    with pytest.raises(Exception, match='representation_error'):
        EPISODE.read_from_parent(wrong_axis, OBJECTIVE)
    for task in ({'kind': 'source_answer', 'answer_kind': 'assessment', 'source_refs': ['src_1']},
                 {'kind': 'a105_experiments', 'experiments': []}, {'kind': 'a105_assembly'}):
        other = {**admitted, 'literature_task': {**given['literature_task'], **task}}
        with pytest.raises(Exception, match='representation_error'):
            EPISODE.read_from_parent(other, OBJECTIVE)


def test_the_credit_is_the_filling_of_the_grading_sheet_and_nothing_else():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    task = {'kind': 'verified_source_leads', 'credit_unit': 2.0}
    none_yet = {'task': task, 'child_returns': [], 'sheet_update': None}
    assert credit_module.credit(none_yet, None) == 0.0
    updated = {'task': task, 'child_returns': [{'credit': 0.25}],
               'sheet_update': {'credit': [{'credit': 0.5}, {'credit': 0.25}]}}
    assert credit_module.credit(updated, None) == 1.5
    # what a leaf read or stated earns the page nothing until it is on the sheet
    leaf_only = {'task': task, 'child_returns': [{'credit': 0.5}, {'credit': 0.75}], 'sheet_update': None}
    assert credit_module.credit(leaf_only, None) == 0.0


class HeldArtifacts:
    def __init__(self, artifacts):
        self.artifacts = artifacts

    def get_artifact(self, ref):
        return self.artifacts[ref]


def test_a_source_is_the_lead_only_when_its_sheet_row_of_the_claim_is_measured_and_the_page_wrote_it():
    summary_module = importlib.import_module(PACKAGE + '.messages.internal_summary')
    given = HeldArtifacts({'state_given': '{"row": {"row_ref": "row:given"}}'})

    def update(*rows):
        return {'features': [{'assertion_ref': ref, 'status': status, 'sheet_ref': row} for ref, status, row in rows]}
    lead = summary_module.bearing_lead_sources
    assert lead(given, 'src_1', 'hyp_1', ['state_given'], None) == []
    assert lead(given, 'src_1', 'hyp_1', ['state_given'], update(('hyp_1', 'measured', 'row:new'))) == ['src_1']
    assert lead(given, 'src_1', 'hyp_1', [], update(('hyp_1', 'measured_zero', 'row:new'))) == ['src_1']
    assert lead(given, 'src_1', 'hyp_1', ['state_given'], update(('hyp_1', 'unknown', 'row:new'))) == []
    assert lead(given, 'src_1', 'hyp_1', ['state_given'], update(('hyp_1', 'measured', 'row:given'))) == []
    assert lead(given, 'src_1', 'hyp_1', ['state_given'], update(('hyp_2', 'measured', 'row:new'))) == []


def leaf_summary(**changes):
    task = {'version': 'literature_local_task_v1', 'kind': 'verified_source_leads', 'evidence_axis': 'A105',
            'credit_unit': 1.0}
    value = {'task': task, 'content_assessment_ref': 'assessment_1', 'report_windows': [[0, 10]],
             'unconsumed_chunk_ids': ['prose_chunk:0000'], 'unconsumed_table_ids': ['source_table:0001'],
             'unused_leaf_record_refs': [], 'sheet_class': 'ligand_binding'}
    value.update(changes)
    return value


def test_the_page_names_no_experiment_type_for_a_leaf_and_hands_the_sheet_class_of_the_claim():
    task_module = importlib.import_module(PACKAGE + '.task')
    to_child = importlib.import_module(PACKAGE + '.messages.msg_to_child')
    summary_module = importlib.import_module(PACKAGE + '.messages.internal_summary')
    summary = leaf_summary()
    assert set(task_module.child_arguments('report', summary)['properties']) == set()
    for slot in ('chunk', 'table'):
        assert set(task_module.child_arguments(slot, summary)['properties']) == {'candidate_id'}
    summary = {**summary, 'held_record_refs': ['src_1'], 'proposed_annotation_ref': 'hyp_1',
               'page': {'source_ref': 'src_1', 'representation': 'text'}, 'task_key': 'A105:verified_source_leads',
               'content_candidates': [{'candidate_id': 'prose_chunk:0000', 'start': 4, 'end': 20}]}
    message = to_child.msg_to_child('chunk', {'candidate_id': 'prose_chunk:0000'}, summary)
    assert message.assignment['sheet_class'] == 'ligand_binding' and 'experiment_type' not in message.assignment
    assert (message.assignment['offset'], message.assignment['limit']) == (4, 16)
    assert message.objective == 'find_applicable_evidence'
    report = to_child.msg_to_child('report', {}, summary)
    assert report.assignment['sheet_class'] == 'ligand_binding' and report.assignment['windows'] == [[0, 10]]
    assert summary_module.class_of_predicate('binds') == 'ligand_binding'
    assert summary_module.class_of_predicate('catalyzes') == 'activity_rate'


def test_the_page_assesses_first_then_updates_the_sheet_by_code_and_offers_the_model_only_leaf_children():
    task_module = importlib.import_module(PACKAGE + '.task')
    context = SimpleNamespace(settings={})
    assert task_module.offered_actions(leaf_summary(content_assessment_ref=None), context) == ['assess_content']
    assert task_module.offered_actions(leaf_summary(unused_leaf_record_refs=['leaf_1']), context) == ['update_sheet']
    assert task_module.offered_actions(leaf_summary(), context) == list(CHILDREN)
    assert task_module.offered_actions(leaf_summary(unconsumed_chunk_ids=[], unconsumed_table_ids=[],
                                                    report_windows=[]), context) == []
    assert set(task_module.TOOLS) == {'assess_content', 'update_sheet'}
    ungrouped = leaf_summary(unused_leaf_record_refs=['leaf_1'], leaf_record_refs=['leaf_1'], base_state_refs=[],
                             proposed_annotation_ref='hyp_1')
    decision = task_module.decide(ungrouped, None, context)
    assert decision.name == 'update_sheet' and decision.arguments['leaf_record_refs'] == ['leaf_1']
    brief = task_module.BRIEF + task_module.RETURN_GUIDANCE
    assert 'source_read' not in brief and 'reason' not in brief.replace('reasoning', '')


def test_the_page_offers_the_leaf_children_and_the_sheet_ceiling():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    task = {'kind': 'verified_source_leads', 'credit_unit': 2.0}
    summary = {'task': task, 'child_returns': [], 'sheet_update': None, 'unused_leaf_record_refs': ['leaf_1']}
    for slot in CHILDREN:
        assert credit_module.ceiling(summary, None, slot, None, None) == 2.0
    assert credit_module.ceiling(summary, None, 'update_sheet', None, None) == 2.0
    assert credit_module.ceiling(summary, None, 'assess_content', None, None) == 0.0
    with pytest.raises(ValueError, match='ceiling_unknown_action_type'):
        credit_module.ceiling(summary, None, 'reason', None, None)
