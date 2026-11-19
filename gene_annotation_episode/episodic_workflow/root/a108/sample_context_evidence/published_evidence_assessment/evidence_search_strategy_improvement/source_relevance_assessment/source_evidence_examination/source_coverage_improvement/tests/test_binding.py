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
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceCoverageImprovement
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py', 'tests/a108_world.py',
         'tests/test_context_grading.py', 'tests/test_model_run.py'}
SOURCE = 'source_' + 'a' * 24
ARTIFACT = 'artifact_' + 'a' * 24
ROOT = 'gene_annotation_episode.episodic_workflow.root'
COMMIT_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['terms'],
                 'properties': {'terms': {'type': 'array'}}}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts}


def assignment(task):
    page = {'version': 'page_assignment_v1', 'source_ref': SOURCE, 'representation': 'text', 'artifact_ref': ARTIFACT,
            'question_context_refs': [], 'prior_delivery_refs': []}
    window = {'source_ref': SOURCE, 'representation': 'text', 'offset': 0, 'limit': 10}
    return {'version': 'reading_assignment_v1', 'page': page, 'selection': window, 'literature_task': task,
            'proposed_annotation_ref': 'hyp_1', 'scope': {'subject_refs': ['sub_1']},
            'received_record_refs': [SOURCE, ARTIFACT]}


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


def test_the_commission_form_admits_a_reading_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    task = {'kind': 'verified_source_leads', 'evidence_axis': 'A108', 'credit_unit': 1.0, 'version':
            'literature_local_task_v1'}
    admitted = form.admit(assignment(task), 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'read'})
    assert parent_input['window'] == admitted['selection'] and parent_input['page'] == admitted['page']
    assert parent_input['task_key'] == 'A108:verified_source_leads'
    assert set(form.record_refs(admitted)) == {SOURCE, ARTIFACT}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**assignment(task), 'extra': 1}, 'test')
    other = {**admitted, 'selection': {**admitted['selection'], 'source_ref': 'source_' + 'c' * 24}}
    with pytest.raises(ValueError, match='literature_reading_source_mismatch'):
        EPISODE.read_from_parent(other, {})


def test_a_screening_task_must_name_spans_on_the_page_artifact():
    span = {'source_ref': SOURCE, 'artifact_ref': 'artifact_' + 'b' * 24, 'start': 0, 'end': 5}
    task = {'kind': 'source_answer', 'answer_kind': 'screening', 'evidence_axis': 'A108', 'credit_unit': 2.0,
            'version': 'literature_local_task_v1', 'examined': [span]}
    admitted = EPISODE.assignment_form.admit(assignment(task), 'test')
    with pytest.raises(ValueError, match='literature_task_screening_artifact_mismatch'):
        EPISODE.read_from_parent(admitted, {})


def test_the_return_declares_credit_and_finding_as_required_and_the_controlled_fields_as_selectable():
    fields = EPISODE.return_form.fields
    assert fields['credit'].required and fields['finding'].required and 'finding_refs' not in fields
    for name in ('literature_a108_grading_cells', 'literature_a108_aggregation_cells', 'literature_screening_answers',
                 'literature_source_lead_dispositions'):
        assert not fields[name].required
    assert fields['literature_a108_grading_cells'].type == 'record_refs'


def test_the_credit_is_real_code_and_counts_nothing_without_a_validated_lead():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    assert 'NotImplementedError' not in (FOLDER / 'credit.py').read_text()
    summary = {'task': {'kind': 'verified_source_leads', 'credit_unit': 2.0}, 'task_key': 'A108:verified_source_leads',
               'source_leads': [], 'proposed_annotation_ref': 'hyp_1'}
    assert credit_module.credit(summary, None) == 0


def test_the_model_is_offered_the_access_tools_the_coupled_reasoning_and_the_two_sheet_populations():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered({'tool_registry': {}})
    assert 'execution_estimate' not in names and len(names) == 15
    assert 'reason' in names and set(task.POPULATE_NAMES) <= set(names)
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
