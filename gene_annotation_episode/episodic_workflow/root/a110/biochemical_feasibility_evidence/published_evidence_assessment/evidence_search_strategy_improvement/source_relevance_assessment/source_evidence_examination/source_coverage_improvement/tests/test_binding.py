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
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
FEATURES_MODULE = importlib.import_module('gene_annotation_episode.episodic_workflow.episode_support.findings.'
                                          'biochemical_feasibility_evidence.investigation_finding_features')
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py',
         'tests/test_reaction_grading.py', 'tests/test_input_list.py', 'tests/test_model_run.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
COMMIT_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['terms'],
                 'properties': {'terms': {'type': 'array'}}}
PAGE = {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'text', 'artifact_ref': 'art_1',
        'question_context_refs': [], 'prior_delivery_refs': []}
WINDOW = {'source_ref': 'src_1', 'representation': 'text', 'offset': 0, 'limit': 10}
ASSIGNMENT = {'version': 'reading_assignment_v1', 'page': PAGE, 'selection': WINDOW,
              'scope': {'subject_refs': ['sub_1']}, 'finding_unit': 1.0, 'received_record_refs': ['src_1', 'art_1']}


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
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'read'})
    assert parent_input['window'] == WINDOW and parent_input['page'] == PAGE and parent_input['finding_unit'] == 1.0
    assert set(form.record_refs(admitted)) == {'src_1', 'art_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    other = {**admitted, 'selection': {**WINDOW, 'source_ref': 'src_2'}}
    with pytest.raises(ValueError, match='literature_reading_source_mismatch'):
        EPISODE.read_from_parent(other, {})
    with pytest.raises(ValueError, match='explicit_positive_finding_unit_required'):
        EPISODE.read_from_parent({**admitted, 'finding_unit': 0}, {})


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    features = FEATURES_MODULE.validate_features({
        'retained_finding_count': 0, 'count_by_evidence_type': dict.fromkeys(FEATURES_MODULE.EVIDENCE_TYPE_VALUES, 0),
        'strengthening_count': 0, 'weakening_count': 0, 'mixed_or_nondiscriminating_count': 0, 'direct_count': 0,
        'qualified_count': 0, 'independent_source_count': 0, 'uncertainty_reported_count': 0, 'controlled_count': 0,
        'arm_agreement': 'none', 'inactive_count_by_reason': dict.fromkeys(FEATURES_MODULE.INACTIVE_REASONS, 0),
        'finding_refs': [], 'finding_record_refs': []})
    summary = {'investigation_finding': features, 'reaction_sheets': []}
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())
    assert result['credit'] == 2.5 and result['finding']['reaction_sheets'] == []
    assert form.admit(result, 'test') == result
    text_fields = [name for name, spec in FINAL.FINDING_FORM.fields.items() if spec.type == 'text']
    assert all(hasattr(FINAL.FINDING_FORM.fields[name], 'options') for name in text_fields)



def test_the_model_is_offered_the_access_tools_the_reaction_graders_and_the_reasoning_and_every_tool_is_declared():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered({})
    assert 'execution_estimate' not in names and 'report' not in EPISODE.tools
    assert names[-3:] == ['literature_reaction_populate', 'literature_reaction_source_populate', 'reason']
    assert len(names) == 17 and set(names) <= set(EPISODE.tools)
    schema = task.selection_schema(names, COMMIT_SCHEMA)
    assert len(schema['properties']['selection']['anyOf']) == len(names)
    assert 'execution_estimate' in task.offered({'tool_registry': {'native_statistics': object()}})
    assert task.empty_commit({'terms': []}, COMMIT_SCHEMA) and not task.empty_commit({'terms': [{}]}, COMMIT_SCHEMA)


def test_the_requested_reaction_components_select_the_reaction_lead():
    form = EPISODE.assignment_form
    plain = EPISODE.read_from_parent(form.admit(ASSIGNMENT, 'test'), {})
    assert plain['requested_reaction_components'] == []
    requested = EPISODE.read_from_parent(form.admit({**ASSIGNMENT, 'requested_reaction_components':
                                                     ['reaction_comparison']}, 'test'), {})
    assert requested['requested_reaction_components'] == ['reaction_comparison']
    with pytest.raises(FormError):
        form.admit({**ASSIGNMENT, 'requested_reaction_components': ['not_a_cell']}, 'test')
