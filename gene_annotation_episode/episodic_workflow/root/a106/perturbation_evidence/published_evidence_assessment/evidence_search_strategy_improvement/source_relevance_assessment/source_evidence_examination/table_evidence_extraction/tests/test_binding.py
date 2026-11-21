"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set; no module imports another episode folder; the episode's own forms and functions
behave on real data. Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from gene_annotation_episode.domain import ContractError
from method_loop import FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').TableEvidenceExtraction
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
NONE = {'literature_populations': [], 'literature_evidence_origins': {}}
COMMIT_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['terms'],
                 'properties': {'terms': {'type': 'array'}}}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
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
    page = {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'original',
            'artifact_ref': 'art_1', 'question_context_refs': [], 'prior_delivery_refs': []}
    table = {'source_ref': 'src_1', 'sheet_key': 'rId1', 'offset': 0, 'limit': 20, 'header_row': 1,
             'where': {'column': 'B', 'match': 'contains', 'value': 'Km'}}
    window = {'source_ref': 'src_1', 'representation': 'original', 'offset': 0, 'limit': 10}
    task = {'kind': 'verified_source_leads', 'evidence_axis': 'A106', 'credit_unit': 1.0}
    assignment = {'version': 'reading_assignment_v1', 'page': page, 'selection': table,
                  'literature_task': task, 'proposed_annotation_ref': 'hyp_1',
                  'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['src_1', 'art_1']}
    admitted = form.admit(assignment, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'read'})
    assert parent_input['selection'] == table and parent_input['page'] == page
    assert parent_input['task_key'] == 'A106:verified_source_leads'
    assert set(form.record_refs(admitted)) == {'src_1', 'art_1'}
    by_window = form.admit({**assignment, 'selection': window}, 'test')
    assert EPISODE.read_from_parent(by_window, {})['selection'] == window
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**assignment, 'extra': 1}, 'test')
    with pytest.raises(ValueError, match='literature_reading_source_mismatch'):
        EPISODE.read_from_parent({**admitted, 'selection': {**table, 'source_ref': 'src_2'}}, {})
    with pytest.raises(ValueError, match='literature_reading_representation_mismatch'):
        EPISODE.read_from_parent({**by_window, 'selection': {**window, 'representation': 'text'}}, {})
    with pytest.raises(ValueError, match='literature_reading_window_selection_invalid'):
        EPISODE.read_from_parent({**by_window, 'selection': {**window, 'header_row': 1}}, {})


def test_a_table_selection_restricts_source_xlsx_rows_to_its_sheet():
    task = importlib.import_module(PACKAGE + '.task')
    source = 'source_' + 'a' * 24
    table = {'source_ref': source, 'sheet_key': 'rId1', 'offset': 0, 'limit': 20}
    arguments = {'source_ref': source, 'sheet_key': 'rId2', 'offset': 0, 'limit': 5, 'header_row': None,
                 'where': None}
    with pytest.raises(ContractError, match='literature_table_sheet_mismatch'):
        task.admitted(None, 'source.xlsx.rows', arguments, {}, source, table)


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    summary = {'a106_findings': {'intervention_assessments': [], 'a106_subscores': []}}
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())
    assert result['credit'] == 2.5 and result['finding'] == summary['a106_findings']
    form.admit(result, 'test')


def test_the_credit_is_real_code_and_counts_nothing_without_a_validated_lead():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    assert 'NotImplementedError' not in (FOLDER / 'credit.py').read_text()
    summary = {'task': {'kind': 'verified_source_leads', 'credit_unit': 2.0}, 'task_key': 'A106:verified_source_leads',
               'source_leads': [], 'proposed_annotation_ref': 'hyp_1'}
    assert credit_module.credit(summary, None) == 0


def test_the_model_is_offered_the_access_tools_the_graders_the_judgment_and_the_reasoning():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered(NONE, None)
    assert 'execution_estimate' not in names and names[-2:] == ['literature_a106_score_judgment', 'reason']
    assert len(names) == 17 and 'open_population' in names
    opened = task.offered(NONE, 'literature_intervention_grading_populate')
    assert opened[-3:] == ['literature_intervention_grading_populate', 'literature_a106_score_judgment', 'reason']
    assert set(opened) <= set(EPISODE.tools) and 'literature_a106_finalize' in EPISODE.tools
    assert set(names) <= set(EPISODE.tools)
    for leads in (False, True):
        schema = task.selection_schema(names, COMMIT_SCHEMA, leads, NONE)
        assert len(schema['properties']['selection']['anyOf']) == len(names)
    reason = [entry for entry in task.catalog(names, COMMIT_SCHEMA, True, NONE) if entry['name'] == 'reason'][0]
    assert 'source_lead' in reason['input_schema']['properties']
    assert 'source_lead' not in task.reason_schema(COMMIT_SCHEMA, False)['properties']
    assert 'execution_estimate' in task.offered({**NONE, 'tool_registry': {'native_statistics': object()}}, None)
    assert task.empty_commit({'terms': []}, COMMIT_SCHEMA) and not task.empty_commit({'terms': [{}]}, COMMIT_SCHEMA)


def test_the_input_list_is_the_unprocessed_spans_of_the_selection_and_shrinks_with_read_and_commit():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence import (
        literature_input_spans as spans)
    window = {'source_ref': 'src_1', 'representation': 'original', 'offset': 100, 'limit': 100}

    def read(offset, limit, status='completed', **more):
        arguments = {'source_ref': 'src_1', 'representation': 'original', 'offset': offset, 'limit': limit, **more}
        return {'kind': 'tool', 'tool': 'source_read', 'arguments': {'arguments': arguments},
                'outcome': {'status': status}}
    commit = {'kind': 'tool', 'tool': 'reason', 'arguments': {'arguments': {}}, 'outcome': {'status': 'completed'}}
    assert spans.consumed_and_remaining(window, []) == ([], [[100, 200]])
    assert spans.consumed_and_remaining(window, [read(100, 50)]) == ([], [[100, 200]])   # read, not yet committed
    assert spans.consumed_and_remaining(window, [read(100, 50, status='invalid'), commit]) == ([], [[100, 200]])
    assert spans.consumed_and_remaining(window, [read(120, 30), commit]) == ([[120, 150]], [[100, 120], [150, 200]])
    assert spans.consumed_and_remaining(window, [read(0, 500), commit]) == ([[0, 500]], [])
    assert spans.consumed_and_remaining(window, [read(100, 100, representation='text'), commit])[1] == [[100, 200]]
    consumed, _ = spans.consumed_and_remaining(window, [read(100, 100), commit])
    assert spans.is_consumed_read(window, 'source_read', {'source_ref': 'src_1', 'representation': 'original',
                                                          'offset': 110, 'limit': 20}, consumed)
    assert not spans.is_consumed_read(window, 'source_read', {'source_ref': 'src_1', 'representation': 'original',
                                                              'offset': 190, 'limit': 20}, consumed)
    table = {'source_ref': 'src_1', 'sheet_key': 'rId1', 'offset': 0, 'limit': 20, 'header_row': 1}
    rows = {'kind': 'tool', 'tool': 'source_xlsx_rows', 'outcome': {'status': 'completed'},
            'arguments': {'arguments': {'source_ref': 'src_1', 'sheet_key': 'rId1', 'offset': 0, 'limit': 10,
                                        'header_row': 1, 'where': None}}}
    assert spans.consumed_and_remaining(table, [rows, commit]) == ([[0, 10]], [[10, 20]])


def test_the_selectable_answers_are_counts_and_references_and_are_admitted():
    form = EPISODE.return_form
    summary = {'a106_findings': {'intervention_assessments': [], 'a106_subscores': []},
               'no_applicable_evidence': [{'start': 0, 'end': 4}], 'screening_answers': [],
               'source_lead_dispositions': [{'source_ref': 'src_1', 'disposition': 'relevant'},
                                            {'source_ref': 'src_2', 'disposition': 'not_relevant'}]}
    both = ('literature_screening_answers', 'literature_source_lead_dispositions')
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0}, both)
    assert result['literature_screening_answers'] == {'examined_span_count': 1, 'commissioned_spans_covered': False}
    assert result['literature_source_lead_dispositions'] == {'relevant_lead_count': 1, 'lead_source_refs': ['src_1']}
    form.select(both).admit(result, 'return')
    assert form.select(both).record_refs(result) == ('src_1',)
