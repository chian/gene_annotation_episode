"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode without children; no module imports another episode folder; the
episode's own forms, credit and controller behave on real data. Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController, CompletionYieldController

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').PassageEvidenceExtraction
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
PAGE = {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'text', 'artifact_ref': 'art_1',
        'question_context_refs': [], 'prior_delivery_refs': []}
WINDOW = {'source_ref': 'src_1', 'representation': 'text', 'offset': 0, 'limit': 10}
SCREENING_TASK = {'version': 'literature_local_task_v1', 'evidence_axis': 'A105', 'kind': 'source_answer',
                  'answer_kind': 'screening', 'credit_unit': 2.0,
                  'examined': [{'source_ref': 'src_1', 'artifact_ref': 'art_1', 'start': 0, 'end': 100}]}
LEADS_TASK = {'version': 'literature_local_task_v1', 'evidence_axis': 'A105', 'kind': 'verified_source_leads',
              'credit_unit': 1.0}
ASSIGNMENT = {'version': 'reading_assignment_v1', 'page': PAGE, 'selection': {'spans': [WINDOW]},
              'literature_task': SCREENING_TASK, 'proposed_annotation_ref': 'hyp_1',
              'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['src_1', 'art_1', 'hyp_1']}


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
    for path in FOLDER.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module


def test_the_commission_form_admits_a_reading_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'read'})
    assert parent_input['spans'] == [WINDOW] and parent_input['page'] == PAGE
    assert parent_input['task_key'] == 'A105:source_answer:screening'
    assert set(form.record_refs(admitted)) >= {'src_1', 'art_1', 'hyp_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    other = {**admitted, 'selection': {'spans': [{**WINDOW, 'source_ref': 'src_2'}]}}
    with pytest.raises(ValueError, match='literature_reading_source_mismatch'):
        EPISODE.read_from_parent(other, {})
    with pytest.raises(ValueError, match='literature_original_task_invalid'):
        EPISODE.read_from_parent({**admitted, 'literature_task': {**SCREENING_TASK, 'kind': 'other'}}, {})


def test_the_return_declares_credit_and_finding_as_required_and_the_fact_sources_as_selectable():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    for name in ('literature_screening_answers', 'literature_source_lead_dispositions', 'literature_structure_cells'):
        assert not form.fields[name].required


def test_the_axis_has_no_report_form_validator_so_the_return_raises_where_the_old_one_called_it():
    summary = {'report': None, 'report_source_held': {},
               'literature_assignment': {'page': {'source_ref': 's', 'representation': 'text'},
                                         'selection': {'spans': [{'source_ref': 's', 'representation': 'text'}]}}}
    with pytest.raises(NotImplementedError, match='validate_form_not_built:A102'):
        EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())


def test_the_screening_credit_is_the_unit_when_the_own_declarations_cover_every_requested_span():
    summary = {'task': SCREENING_TASK, 'task_key': 'A105:source_answer:screening', 'proposed_annotation_ref': 'hyp_1',
               'no_applicable_evidence': [{'source_ref': 'src_1', 'artifact_ref': 'art_1', 'start': 0, 'end': 60,
                                           'representation': 'text'}]}
    assert EPISODE.credit(summary, None) == 0
    summary['no_applicable_evidence'].append({'source_ref': 'src_1', 'artifact_ref': 'art_1', 'start': 50,
                                              'end': 100, 'representation': 'text'})
    assert EPISODE.credit(summary, None) == 2.0
    credit_source = (FOLDER / 'credit.py').read_text()
    assert 'NotImplementedError' not in credit_source and 'min(' not in credit_source


def test_the_controller_follows_the_commissioned_task_kind():
    settings = {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}
    leads = EPISODE.yield_controller(0, settings, {'task': LEADS_TASK})
    screening = EPISODE.yield_controller(0, settings, {'task': SCREENING_TASK})
    assert isinstance(leads, AccumulationYieldController)
    assert isinstance(screening, CompletionYieldController)


def test_the_model_is_offered_the_access_tools_reasoning_and_the_report_and_every_tool_is_declared():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered({})
    assert 'execution_estimate' not in names and names[-2:] == ['reason', 'report'] and len(names) == 16
    assert set(names) <= set(EPISODE.tools)
    assert 'literature_structure_populate' in task.offered({'structure_population': True})
    with pytest.raises(NotImplementedError, match='literature_structure_population_not_built'):
        task.literature_structure_populate({}, None)


def test_the_selection_schema_and_its_strict_transport_build_for_every_offered_tool():
    task = importlib.import_module(PACKAGE + '.task')
    summary = {'task': LEADS_TASK, 'reasoning_schema': {'type': 'object', 'properties': {'terms': {'type': 'array'}},
                                                         'required': ['terms'], 'additionalProperties': False}}
    names = task.offered({})
    schema = task.selection_schema(names, summary)
    assert len(schema['properties']['selection']['anyOf']) == len(names)
    assert task.generation_schema(schema)
    reason = [entry for entry in task.catalog(names, summary) if entry['name'] == 'reason'][0]
    assert 'source_lead' in reason['input_schema']['required']
