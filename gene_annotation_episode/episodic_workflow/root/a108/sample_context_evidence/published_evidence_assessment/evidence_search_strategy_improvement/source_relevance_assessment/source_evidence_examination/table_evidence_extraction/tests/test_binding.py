"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set; no module imports another episode folder; the episode's own forms, controllers and
functions behave on real data. Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController, CompletionYieldController

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').TableEvidenceExtraction
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
COMMIT_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['terms'],
                 'properties': {'terms': {'type': 'array'}}}
SRC, SRC2 = 'source_' + 'a' * 24, 'source_' + 'b' * 24
ART, HYP, SUB = 'artifact_' + 'c' * 24, 'hypothesis_' + 'd' * 24, 'input_' + 'e' * 24
PAGE = {'version': 'page_assignment_v1', 'source_ref': SRC, 'representation': 'original',
        'artifact_ref': ART, 'question_context_refs': [], 'prior_delivery_refs': []}
TABLE = {'source_ref': SRC, 'sheet_key': 'rId1', 'offset': 0, 'limit': 20, 'header_row': 1,
         'where': {'column': 'B', 'match': 'contains', 'value': 'pH'}}
WINDOW = {'source_ref': SRC, 'representation': 'original', 'offset': 0, 'limit': 10}
LEADS_TASK = {'version': 'literature_local_task_v1', 'kind': 'verified_source_leads', 'evidence_axis': 'A108',
              'credit_unit': 1.0}
ASSESSMENT_TASK = {'version': 'literature_local_task_v1', 'kind': 'source_answer', 'answer_kind': 'assessment',
                   'evidence_axis': 'A108', 'credit_unit': 2.0, 'source_refs': [SRC]}
SCREENING_TASK = {'version': 'literature_local_task_v1', 'kind': 'source_answer', 'answer_kind': 'screening',
                  'evidence_axis': 'A108', 'credit_unit': 2.0,
                  'examined': [{'source_ref': SRC, 'artifact_ref': ART, 'start': 0, 'end': 10}]}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts}


def assignment(task=LEADS_TASK, selection=TABLE, **more):
    return {'version': 'reading_assignment_v1', 'page': PAGE, 'selection': selection, 'literature_task': task,
            'proposed_annotation_ref': HYP, 'scope': {'subject_refs': [SUB]},
            'received_record_refs': [SRC, ART], **more}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert EPISODE.binding_path.startswith('sample_context_evidence/')
    assert dict(EPISODE.child_slots) == {}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_without_children():
    assert files() == FILES
    assert not (FOLDER / 'messages' / 'msg_to_child.py').exists()
    assert not (FOLDER / 'messages' / 'read_from_child.py').exists()


def test_no_module_of_the_folder_imports_another_episode_folder():
    own = PACKAGE
    for path in FOLDER.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == own or module.startswith(own + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module


def test_the_commission_form_admits_a_table_or_a_window_selection_and_refuses_the_rest():
    form = EPISODE.assignment_form
    admitted = form.admit(assignment(), 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'read'})
    assert parent_input['selection'] == TABLE and parent_input['page'] == PAGE
    assert parent_input['task_key'] == 'A108:verified_source_leads'
    assert parent_input['requested_a108_grading_components'] == []
    assert set(form.record_refs(admitted)) == {SRC, ART}
    by_window = form.admit(assignment(selection=WINDOW), 'test')
    assert EPISODE.read_from_parent(by_window, {})['selection'] == WINDOW
    requested = form.admit(assignment(requested_a108_grading_components=['support_count', 'evidence_amount']),
                           'test')
    assert EPISODE.read_from_parent(requested, {})['requested_a108_grading_components'] == [
        'support_count', 'evidence_amount']
    with pytest.raises(FormError, match='unknown_field'):
        form.admit(assignment(extra=1), 'test')
    with pytest.raises(FormError):
        form.admit(assignment(requested_a108_grading_components=['not_a_component']), 'test')
    with pytest.raises(Exception, match='literature_reading_source_mismatch'):
        EPISODE.read_from_parent({**admitted, 'selection': {**TABLE, 'source_ref': SRC2}}, {})
    with pytest.raises(Exception, match='literature_reading_representation_mismatch'):
        EPISODE.read_from_parent({**by_window, 'selection': {**WINDOW, 'representation': 'text'}}, {})
    with pytest.raises(Exception, match='literature_reading_window_selection_invalid'):
        EPISODE.read_from_parent({**by_window, 'selection': {**WINDOW, 'header_row': 1}}, {})


def test_the_commissioned_task_is_checked_against_its_schema_and_the_assigned_page():
    form = EPISODE.assignment_form
    for task in (ASSESSMENT_TASK, SCREENING_TASK):
        assert EPISODE.read_from_parent(form.admit(assignment(task), 'test'), {})['task'] == task
    with pytest.raises(Exception, match='literature_task_outside_assigned_source'):
        EPISODE.read_from_parent(form.admit(assignment({**ASSESSMENT_TASK, 'source_refs': [SRC2]}), 'test'), {})
    with pytest.raises(Exception, match='literature_task_screening_span_invalid'):
        EPISODE.read_from_parent(form.admit(assignment(
            {**SCREENING_TASK, 'examined': [{**SCREENING_TASK['examined'][0], 'start': 5, 'end': 4}]}), 'test'), {})
    with pytest.raises(Exception):
        EPISODE.read_from_parent(form.admit(assignment({**LEADS_TASK, 'evidence_axis': 'A105'}), 'test'), {})


def test_a_table_selection_restricts_source_xlsx_rows_to_its_sheet():
    task = importlib.import_module(PACKAGE + '.task')
    source = 'source_' + 'a' * 24
    table = {'source_ref': source, 'sheet_key': 'rId1', 'offset': 0, 'limit': 20}
    arguments = {'source_ref': source, 'sheet_key': 'rId2', 'offset': 0, 'limit': 5, 'header_row': None,
                 'where': None}
    with pytest.raises(Exception, match='literature_table_sheet_mismatch'):
        task.admitted(None, 'source.xlsx.rows', arguments, {}, source, table)
    task.admitted(None, 'source.xlsx.rows', {**arguments, 'sheet_key': 'rId1'}, {}, source, table)


def test_the_return_declares_credit_and_finding_as_required_and_the_fact_sources_as_selectable():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    selectable = {name for name, field in form.fields.items() if not field.required}
    assert selectable == {'literature_screening_answers', 'literature_source_lead_dispositions',
                          'literature_a108_grading_cells', 'literature_a108_aggregation_cells'}


def test_the_credit_is_real_code_and_its_pure_parts_count_the_old_answers():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    assert 'NotImplementedError' not in (FOLDER / 'credit.py').read_text()
    summary = {'task': SCREENING_TASK, 'proposed_annotation_ref': HYP, 'no_applicable_evidence': []}
    assert credit_module.screening_answers(summary) == []
    spans = [{'source_ref': SRC, 'artifact_ref': ART, 'start': 0, 'end': 6},
             {'source_ref': SRC, 'artifact_ref': ART, 'start': 5, 'end': 10}]
    answers = credit_module.screening_answers({**summary, 'no_applicable_evidence': spans})
    assert len(answers) == 1 and answers[0]['disposition'] == 'no_applicable_evidence'
    gap = [spans[0], {**spans[1], 'start': 7}]
    assert credit_module.screening_answers({**summary, 'no_applicable_evidence': gap}) == []
    assert credit_module.credit_binding('A108:source_answer:screening', SCREENING_TASK)['credit_unit'] == 2.0


def test_the_controller_is_accumulation_for_leads_and_completion_with_the_credit_unit_for_an_answer():
    settings = {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}
    leads = EPISODE.yield_controller(0.0, settings, {'task': LEADS_TASK})
    assert type(leads) is AccumulationYieldController
    answer = EPISODE.yield_controller(0.0, settings, {'task': ASSESSMENT_TASK})
    assert type(answer) is CompletionYieldController and answer.target == 2.0


def test_the_model_is_offered_the_access_tools_the_population_tools_and_the_reasoning():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered({'tool_registry': {}})
    assert 'execution_estimate' not in names and names[-1] == 'reason' and len(names) == 15
    assert {'literature_a108_grading_populate', 'literature_a108_aggregate'} <= set(names)
    assert set(names) <= set(EPISODE.tools)
    for leads in (False, True):
        schema = task.selection_schema(names, COMMIT_SCHEMA, leads)
        assert len(schema['properties']['selection']['anyOf']) == len(names)
    reason = [entry for entry in task.catalog(names, COMMIT_SCHEMA, True) if entry['name'] == 'reason'][0]
    assert 'source_lead' in reason['input_schema']['properties']
    assert 'evidence_processing' in reason['input_schema']['properties']
    assert 'source_lead' not in task.reason_schema(COMMIT_SCHEMA, False)['properties']
    assert 'execution_estimate' in task.offered({'tool_registry': {'native_statistics': object()}})
    assert task.empty_commit({'terms': []}, COMMIT_SCHEMA) and not task.empty_commit({'terms': [{}]}, COMMIT_SCHEMA)
    assert 'nothing you write in prose is returned' in task.instructions(knowledge=None, leads=False)
    assert 'source_lead' in task.instructions(knowledge=None, leads=True)
