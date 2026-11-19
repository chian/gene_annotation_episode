"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set; no module imports another episode folder; the episode's own forms and functions
behave on real data. Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').TableEvidenceExtraction
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
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


def test_the_commission_form_admits_a_table_or_a_window_selection_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    page = {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'original',
            'artifact_ref': 'art_1', 'question_context_refs': [], 'prior_delivery_refs': []}
    table = {'source_ref': 'src_1', 'sheet_key': 'rId1', 'offset': 0, 'limit': 20, 'header_row': 1,
             'where': {'column': 'B', 'match': 'contains', 'value': 'kinase'}}
    window = {'source_ref': 'src_1', 'representation': 'original', 'offset': 0, 'limit': 10}
    task = {'kind': 'verified_source_leads', 'evidence_axis': 'A104', 'credit_unit': 1.0}
    assignment = {'version': 'reading_assignment_v1', 'page': page, 'selection': table,
                  'literature_task': task, 'proposed_annotation_ref': 'hyp_1',
                  'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['src_1', 'art_1']}
    admitted = form.admit(assignment, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'read'})
    assert parent_input['selection'] == table and parent_input['page'] == page
    assert parent_input['task_key'] == 'A104:verified_source_leads'
    assert set(form.record_refs(admitted)) == {'src_1', 'art_1'}
    by_window = form.admit({**assignment, 'selection': window}, 'test')
    assert EPISODE.read_from_parent(by_window, {})['selection'] == window
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**assignment, 'extra': 1}, 'test')
    for wrong, code in (({**table, 'source_ref': 'src_2'}, 'literature_reading_source_mismatch'),
                        ({**table, 'representation': 'original'}, 'literature_reading_selection_shape_invalid'),
                        ({**window, 'header_row': 1}, 'literature_reading_selection_shape_invalid'),
                        ({**window, 'representation': 'text'}, 'literature_reading_representation_mismatch')):
        with pytest.raises(ValueError, match=code):
            EPISODE.read_from_parent({**admitted, 'selection': wrong}, {})


def test_the_return_is_credit_and_controlled_features_only():
    final = importlib.import_module(PACKAGE + '.messages.final_to_parent')
    form = final.RETURN_FORM
    assert form.fields['credit'].required and form.fields['finding'].required
    summary = {'assay_sheets': [], 'assessments': [], 'sheet_record_refs': [], 'proposed_annotation_ref': 'hyp_1',
               'screening_answers': [], 'no_applicable_evidence': [], 'source_lead_dispositions': []}
    result = final.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())
    assert result == {'credit': 2.5, 'finding': {'assay_sheets': [], 'assessments': [], 'assay_count': 0,
                                                 'assessment_count': 0, 'assay_count_with_evidence_ratio': 0,
                                                 'sheet_record_refs': []}}
    form.admit(result, 'return')
    leads = [{'source_ref': 'src_1', 'disposition': 'relevant'}, {'source_ref': 'src_2', 'disposition': 'not_relevant'}]
    selection = (final.SCREENING, final.LEADS)
    selected = final.final_to_parent({**summary, 'source_lead_dispositions': leads}, {'credit': 1.0}, selection)
    assert selected[final.LEADS] == {'relevant_lead_count': 1, 'lead_source_refs': ['src_1']}
    assert selected[final.SCREENING] == {'answered': False, 'examined_span_count': 0, 'examined_byte_total': 0}
    assert form.select(selection).record_refs(form.select(selection).admit(selected, 'return')) == ('src_1',)
    for nested in (final.SHEET_FORM, final.ASSESSMENT_FORM):
        assert all(spec.type != 'text' or hasattr(spec, 'options') for spec in nested.fields.values())


def test_the_credit_is_real_code_and_counts_nothing_without_a_validated_lead():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    assert 'NotImplementedError' not in (FOLDER / 'credit.py').read_text()
    summary = {'task': {'kind': 'verified_source_leads', 'credit_unit': 2.0}, 'task_key': 'A104:verified_source_leads',
               'source_leads': [], 'proposed_annotation_ref': 'hyp_1'}
    assert credit_module.credit(summary, None) == 0


def test_the_model_is_offered_the_access_tools_the_reasoning_and_the_report_and_every_tool_is_declared():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered({})
    assert 'execution_estimate' not in names and names[-1] == 'reason' and 'report' not in names and len(names) == 15
    assert set(names) <= set(EPISODE.tools)
    for leads in (False, True):
        schema = task.selection_schema(names, COMMIT_SCHEMA, leads)
        assert len(schema['properties']['selection']['anyOf']) == len(names)
    reason = [entry for entry in task.catalog(names, COMMIT_SCHEMA, True) if entry['name'] == 'reason'][0]
    assert 'source_lead' in reason['input_schema']['properties']
    assert 'source_lead' not in task.reason_schema(COMMIT_SCHEMA, False)['properties']
    assert 'execution_estimate' in task.offered({'tool_registry': {'native_statistics': object()}})
    assert task.empty_commit({'terms': []}, COMMIT_SCHEMA) and not task.empty_commit({'terms': [{}]}, COMMIT_SCHEMA)


def test_the_sheet_key_lock_refuses_another_sheet_and_accepts_the_assigned_one():
    task = importlib.import_module(PACKAGE + '.task')
    from gene_annotation_episode.domain import ContractError
    source = 'source_' + 'a' * 24
    arguments = {'source_ref': source, 'sheet_key': 'rId2', 'offset': 0, 'limit': 5, 'header_row': None,
                 'where': None}
    with pytest.raises(ContractError, match='literature_table_sheet_mismatch'):
        task.admitted(None, 'source.xlsx.rows', arguments, {}, source, 'rId1')
