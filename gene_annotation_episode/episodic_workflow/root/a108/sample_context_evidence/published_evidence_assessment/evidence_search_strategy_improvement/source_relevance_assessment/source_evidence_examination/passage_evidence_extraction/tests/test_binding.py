"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode without children; no module imports another episode folder; the
episode's own forms and functions behave on real data. Nothing here is faked."""
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
COMMIT_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['terms'],
                 'properties': {'terms': {'type': 'array'}}}
PAGE = {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'text', 'artifact_ref': 'art_1',
        'question_context_refs': [], 'prior_delivery_refs': []}
WINDOW = {'source_ref': 'src_1', 'representation': 'text', 'offset': 0, 'limit': 10}
TASK = {'kind': 'verified_source_leads', 'evidence_axis': 'A108', 'credit_unit': 1.0}


def assignment(**changes):
    return {'version': 'reading_assignment_v1', 'page': PAGE, 'selection': {'spans': [WINDOW]},
            'literature_task': TASK, 'proposed_annotation_ref': 'hyp_1', 'scope': {'subject_refs': ['sub_1']},
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


def test_the_commission_form_admits_a_reading_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    admitted = form.admit(assignment(), 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'read'})
    assert parent_input['spans'] == [WINDOW] and parent_input['page'] == PAGE
    assert parent_input['task_key'] == 'A108:verified_source_leads'
    assert set(form.record_refs(admitted)) == {'src_1', 'art_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**assignment(), 'extra': 1}, 'test')
    other = {**admitted, 'selection': {'spans': [{**WINDOW, 'source_ref': 'src_2'}]}}
    with pytest.raises(ValueError, match='literature_reading_source_mismatch'):
        EPISODE.read_from_parent(other, {})
    with pytest.raises(ValueError, match='literature_original_task_invalid'):
        EPISODE.read_from_parent({**admitted, 'literature_task': {**TASK, 'evidence_axis': 'A106'}}, {})


def test_the_return_declares_credit_and_finding_as_required_and_the_facts_as_selectable():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    selectable = {name for name, spec in form.fields.items() if not spec.required}
    assert selectable == {'literature_screening_answers', 'literature_source_lead_dispositions'}


def test_the_credit_is_real_code_and_counts_nothing_without_a_validated_lead():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    assert 'NotImplementedError' not in (FOLDER / 'credit.py').read_text()
    summary = {'task': {'kind': 'verified_source_leads', 'credit_unit': 2.0}, 'task_key': 'A108:verified_source_leads',
               'source_leads': [], 'proposed_annotation_ref': 'hyp_1'}
    assert credit_module.credit(summary, None) == 0
    screening = {'task': {'kind': 'source_answer', 'answer_kind': 'screening', 'credit_unit': 2.0},
                 'task_key': 'A108:source_answer:screening', 'no_applicable_evidence': [],
                 'proposed_annotation_ref': 'hyp_1'}
    assert credit_module.credit(screening, None) == 0


def test_the_controller_is_chosen_from_the_commissioned_task_and_its_target_is_the_credit_unit():
    settings = {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}
    leads = EPISODE.yield_controller(0, settings, {'task': TASK})
    assert isinstance(leads, AccumulationYieldController)
    answer = {'kind': 'source_answer', 'answer_kind': 'assessment', 'credit_unit': 3.0, 'source_refs': ['src_1']}
    assert isinstance(EPISODE.yield_controller(0, settings, {'task': answer}), CompletionYieldController)


def test_the_model_is_offered_the_access_tools_the_populations_and_the_graded_reasoning():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered({'tool_registry': {}})
    assert 'execution_estimate' not in names and names[-1] == 'reason'
    assert {'grading_populate', 'aggregate_populate'} <= set(names) and len(names) == 15
    assert set(names) <= set(EPISODE.tools)
    for leads in (False, True):
        schema = task.selection_schema(names, COMMIT_SCHEMA, leads)
        assert len(schema['properties']['selection']['anyOf']) == len(names)
        task.generation_schema(schema)
    reason = [entry for entry in task.catalog(names, COMMIT_SCHEMA, True) if entry['name'] == 'reason'][0]
    assert 'source_lead' in reason['input_schema']['properties']
    assert 'evidence_processing' in reason['input_schema']['properties']
    assert 'source_lead' not in task.reason_schema(COMMIT_SCHEMA, False)['properties']
    assert 'execution_estimate' in task.offered({'tool_registry': {'native_statistics': object()}})
    assert task.empty_commit({'terms': []}, COMMIT_SCHEMA) and not task.empty_commit({'terms': [{}]}, COMMIT_SCHEMA)
