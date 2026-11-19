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
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py', 'tests/grading_world.py',
         'tests/test_grading.py'}
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
    task = {'kind': 'verified_source_leads', 'evidence_axis': 'A105', 'credit_unit': 1.0}
    assignment = {'version': 'reading_assignment_v1', 'page': page, 'selection': table,
                  'literature_task': task, 'proposed_annotation_ref': 'hyp_1',
                  'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['src_1', 'art_1']}
    admitted = form.admit(assignment, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'read'})
    assert parent_input['selection'] == table and parent_input['page'] == page
    assert parent_input['task_key'] == 'A105:verified_source_leads'
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


def table_summary(**changes):
    value = {'assay_sheets': [], 'aggregation_sheets': [], 'proposed_annotation_ref': 'hyp_1',
             'no_applicable_spans': [], 'screening_covered': False, 'lead_source_refs': []}
    value.update(changes)
    return value


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    assert set(form.fields) == {'credit', 'finding', 'literature_screening_answers',
                                'literature_source_lead_dispositions'}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}
    result = EPISODE.final_to_parent(table_summary(), completion, ())
    assert result['credit'] == 2.5 and result['finding']['assay_sheets'] == []
    assert result['finding']['assay_count'] == 0
    form.admit(result, 'return')


def test_every_selectable_field_returns_counts_and_references_only():
    summary = table_summary(no_applicable_spans=[{'source_ref': 's'}], screening_covered=True,
                            lead_source_refs=['source_1'])
    selection = ('literature_screening_answers', 'literature_source_lead_dispositions')
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0},
                                     selection)
    assert result['literature_screening_answers'] == {'examined_span_count': 1, 'commissioned_spans_covered': True}
    assert result['literature_source_lead_dispositions'] == {'relevant_lead_count': 1,
                                                             'lead_source_refs': ['source_1']}
    admitted = EPISODE.return_form.select(selection).admit(result, 'return')
    assert list(EPISODE.return_form.select(selection).record_refs(admitted)) == ['source_1']


def test_the_credit_is_real_code_and_counts_nothing_without_a_validated_lead():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    summary = {'task': {'kind': 'verified_source_leads', 'credit_unit': 2.0}, 'task_key': 'A105:verified_source_leads',
               'lead_source_refs': [], 'proposed_annotation_ref': 'hyp_1'}
    assert credit_module.credit(summary, None) == 0
    assert credit_module.credit({**summary, 'lead_source_refs': ['source_1']}, None) == 2.0


def test_the_model_is_offered_the_access_tools_and_the_reasoning_and_every_tool_is_declared():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered()
    assert names[-1] == 'reason' and 'report' not in names and len(names) == 11
    assert set(names) == set(EPISODE.tools)
    for leads in (False, True):
        schema = task.selection_schema(names, COMMIT_SCHEMA, leads)
        assert len(schema['properties']['selection']['anyOf']) == len(names)
    reason = [entry for entry in task.catalog(names, COMMIT_SCHEMA, True) if entry['name'] == 'reason'][0]
    assert 'source_lead' in reason['input_schema']['properties']
    evidence = [entry for entry in task.catalog(names, COMMIT_SCHEMA, False) if entry['name'] == 'reason'][0]
    assert 'evidence_processing' in evidence['input_schema']['properties']
    assert 'source_lead' not in evidence['input_schema']['properties']


def test_a_screening_commission_earns_its_credit_unit_when_the_declared_spans_cover_every_requested_span():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_reasoning import (
        spans_cover)
    credit_module = importlib.import_module(PACKAGE + '.credit')
    examined = [{'source_ref': 's', 'artifact_ref': 'a', 'start': 0, 'end': 100}]
    task = {'kind': 'source_answer', 'answer_kind': 'screening', 'credit_unit': 3.0, 'examined': examined}
    spans = [{'source_ref': 's', 'artifact_ref': 'a', 'start': 0, 'end': 60},
             {'source_ref': 's', 'artifact_ref': 'a', 'start': 50, 'end': 100}]
    assert spans_cover(task, spans) and not spans_cover(task, spans[:1])
    summary = {'task': task, 'task_key': 'A105:source_answer:screening', 'proposed_annotation_ref': 'hyp_1',
               'screening_covered': True}
    assert credit_module.credit(summary, None) == 3.0
    assert credit_module.credit({**summary, 'screening_covered': False}, None) == 0


def test_the_controller_kind_follows_the_commissioned_task():
    from yield_control import AccumulationYieldController, CompletionYieldController, YieldParameters
    controller = importlib.import_module(PACKAGE + '.yield_estimator').yield_controller
    settings = {'cost': 0.5, 'parameters': YieldParameters(uncertainty_alpha=0.1)}
    leads = {'task': {'kind': 'verified_source_leads', 'credit_unit': 2.0}}
    assert isinstance(controller(0.0, settings, leads), AccumulationYieldController)
    experiments = {'task': {'kind': 'a105_experiments', 'credit_unit': 2.0,
                            'experiments': [{'experiment_ref': 'e1'}, {'experiment_ref': 'e2'}]}}
    assert isinstance(controller(0.0, settings, experiments), CompletionYieldController)
