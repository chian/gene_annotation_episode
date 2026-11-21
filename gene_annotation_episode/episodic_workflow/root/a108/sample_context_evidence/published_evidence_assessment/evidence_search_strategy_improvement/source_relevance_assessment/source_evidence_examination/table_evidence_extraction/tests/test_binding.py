"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode without children; no module imports another episode folder; the
episode's own forms and functions behave on real data; and the one extraction runs through the real runner on the held
A108 world of the source coverage leaf's tests (a test fixture, shared). Nothing here is faked."""
import ast
import asyncio
import importlib
import json
from pathlib import Path

import pytest

from episode_runtime import BindingRegistry, EpisodeBinding, RunJournal, ToolCall, link
from method_loop import FormError
from yield_control import AccumulationYieldController
from gene_annotation_episode.model_provider import ModelProvider, load_config

from ...source_coverage_improvement.tests.a108_world import (SERVICES, SETTINGS, extraction, held_world,
                                                             reading_assignment, window)

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').TableEvidenceExtraction
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
PAGE = {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'original', 'artifact_ref': 'art_1',
        'question_context_refs': [], 'prior_delivery_refs': []}
REGION = {'source_ref': 'src_1', 'representation': 'original', 'offset': 5, 'limit': 20}
TASK = {'kind': 'verified_source_leads', 'evidence_axis': 'A108', 'credit_unit': 1.0}


def assignment(**changes):
    return {'version': 'reading_assignment_v1', 'page': PAGE, 'selection': REGION, 'literature_task': TASK,
            'proposed_annotation_ref': 'hyp_1', 'scope': {'subject_refs': ['sub_1']},
            'received_record_refs': ['src_1', 'art_1'], **changes}


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


def test_the_commission_form_admits_one_table_region_and_refuses_what_is_not_the_commission():
    form = EPISODE.assignment_form
    admitted = form.admit(assignment(), 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'read'})
    assert parent_input['spans'] == [REGION] and parent_input['page'] == PAGE
    assert parent_input['task_key'] == 'A108:verified_source_leads'
    assert parent_input['requested_a108_grading_components'] == []
    assert set(form.record_refs(admitted)) == {'src_1', 'art_1'}
    requested = form.admit(assignment(requested_a108_grading_components=['evidence_amount']), 'test')
    assert EPISODE.read_from_parent(requested, {})['requested_a108_grading_components'] == ['evidence_amount']
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**assignment(), 'extra': 1}, 'test')
    with pytest.raises(FormError):
        form.admit(assignment(selection={**REGION, 'sheet_key': 'rId1'}), 'test')
    with pytest.raises(FormError):
        form.admit(assignment(requested_a108_aggregation_components=['overall']), 'test')
    with pytest.raises(ValueError, match='literature_reading_source_mismatch'):
        EPISODE.read_from_parent({**admitted, 'selection': {**REGION, 'source_ref': 'src_2'}}, {})
    for kind in ({'kind': 'source_answer', 'answer_kind': 'assessment', 'source_refs': ['src_1']},
                 {'kind': 'source_answer', 'answer_kind': 'screening', 'examined': []}):
        with pytest.raises(ValueError, match='literature_original_task_invalid'):
            EPISODE.read_from_parent({**admitted, 'literature_task': {**TASK, **kind}}, {})


def test_the_return_declares_credit_and_finding_as_required_and_the_leads_and_cells_as_selectable():
    fields = EPISODE.return_form.fields
    assert fields['credit'].required and fields['finding'].required
    assert {name for name, spec in fields.items() if not spec.required} == {
        'literature_source_lead_dispositions', 'literature_a108_grading_cells'}


def test_the_credit_counts_nothing_without_a_graded_sheet_and_the_ceiling_of_the_extraction_is_unbounded():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit and EPISODE.ceiling is credit_module.ceiling
    summary = {'task': {**TASK, 'credit_unit': 2.0}, 'task_key': 'A108:verified_source_leads', 'source_leads': [],
               'proposed_annotation_ref': 'hyp_1', 'scope': {'subject_refs': ['sub_1']},
               'finding': {'grading_sheets': []}}
    assert credit_module.credit(summary, None) == 0
    assert credit_module.ceiling(summary, None, 'extract', None, None) == credit_module.UNBOUNDED
    assert credit_module.ceiling(summary, None, 'source_read', None, None) == 0.0


def test_the_controller_counts_the_one_region_to_do():
    controller = EPISODE.yield_controller(0, {'cost': 0.1, 'parameters': {}}, {'task': TASK, 'spans': [REGION]})
    assert isinstance(controller, AccumulationYieldController) and controller.items == 1


def test_the_one_action_is_the_extraction_and_the_model_has_no_tool_to_read_around():
    assert list(EPISODE.tools) == ['extract'] == EPISODE.offered_actions({}, None)
    assert tuple(EPISODE.services) == ()
    task = importlib.import_module(PACKAGE + '.task')
    assert task.TEXT == 'table'
    assert not hasattr(task, 'source_read') and not hasattr(task, 'literature_a108_aggregate')


def test_the_table_region_is_extracted_once_with_its_grading_and_cells_and_is_then_consumed(tmp_path):
    world = held_world(tmp_path)
    path = EPISODE.binding_path
    collaborators = {'store': world['store'], 'model_provider': ModelProvider(load_config(), tmp_path / 'calls', tmp_path),
                     'continuation': {path: SETTINGS}, 'services': SERVICES}
    entry = {'assignment': reading_assignment(world, window(world)), 'message': {'objective': 'extract'},
             'selection': ['literature_a108_grading_cells']}
    run = link(BindingRegistry([EPISODE()]), path, entry, run_id='a108-table',
               journal=RunJournal(tmp_path / 'journal.sqlite3'), collaborators=collaborators)
    request = asyncio.run(run.next_decision())
    assert request.context['table']['segments'] and 'tools' not in request.context
    envelope = {'arguments': extraction(world), 'scope': world['scope'], 'page_source_ref': world['paper']['id'],
                'proposed_annotation_ref': world['claim']['id'],
                'assignment': reading_assignment(world, window(world))}
    outcome = asyncio.run(run.run_unit(ToolCall('extract', envelope)))
    assert outcome['outcome']['status'] in ('completed', 'partial'), outcome['outcome']
    summary = EPISODE.internal_summary(run.view)
    assert summary['input_list'] == [] and len(summary['consumed_inputs']) == 1
    assert len(summary['finding']['grading_sheets']) == 1 and EPISODE.credit(summary, run.view.records) == 1.0
    assert len(summary['grading_cell_refs']) == 1
    result = EPISODE.final_to_parent(summary, {'ended_by': 'items', 'units_consumed': 1, 'credit': 1.0},
                                     ('literature_a108_grading_cells',))
    form = EPISODE.return_form.select(('literature_a108_grading_cells',))
    assert form.admit(result, 'return') == json.loads(json.dumps(result))
    world['store'].close()
