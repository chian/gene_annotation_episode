"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set (its child episode folders are theirs); no module of the folder imports another
episode folder; the episode's own forms and functions behave on real data, and what ``msg_to_child`` builds is
admitted by the real child forms. Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceEvidenceExamination
CHILDREN = ('passage_evidence_extraction', 'source_coverage_improvement', 'table_evidence_extraction')
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py', 'tests/test_parent_grading.py', 'tests/test_model_run.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
ASSIGNMENT = {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'text',
              'artifact_ref': 'art_1', 'question_context_refs': [], 'prior_delivery_refs': [],
              'scope': {'subject_refs': ['sub_1']}, 'finding_unit': 1.0, 'received_record_refs': ['src_1', 'art_1']}
WINDOW = {'source_ref': 'src_1', 'representation': 'text', 'offset': 0, 'limit': 10}


def own_files(root=FOLDER):
    return {str(path.relative_to(FOLDER)) for path in root.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts
            and not any(part in CHILDREN for part in path.relative_to(FOLDER).parts)}


def summary():
    admitted = EPISODE.assignment_form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {})
    return {'page': parent_input['page'], 'scope': parent_input['scope'], 'finding_unit': 1.0,
            'received_record_refs': parent_input['received_record_refs']}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert set(EPISODE.child_slots) == set(CHILDREN)
    for slot in CHILDREN:
        assert EPISODE.child_slots[slot] == EPISODE.binding_path + '/' + slot


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_children():
    assert own_files() == FILES


def test_no_module_of_the_folder_imports_another_episode_folder():
    for path in (FOLDER / name for name in sorted(FILES) if name.endswith('.py')):
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module


def test_the_commission_form_admits_a_page_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'examine'})
    assert parent_input['page']['source_ref'] == 'src_1' and parent_input['finding_unit'] == 1.0
    assert set(form.record_refs(admitted)) == {'src_1', 'art_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    with pytest.raises(ValueError, match='explicit_positive_finding_unit_required'):
        EPISODE.read_from_parent({**admitted, 'finding_unit': 0}, {})


def empty_finding():
    module = importlib.import_module('gene_annotation_episode.episodic_workflow.episode_support.findings.'
                                     'biochemical_feasibility_evidence.investigation_finding_features')
    return module.validate_features({
        'retained_finding_count': 0, 'count_by_evidence_type': dict.fromkeys(module.EVIDENCE_TYPE_VALUES, 0),
        'strengthening_count': 0, 'weakening_count': 0, 'mixed_or_nondiscriminating_count': 0, 'direct_count': 0,
        'qualified_count': 0, 'independent_source_count': 0, 'uncertainty_reported_count': 0, 'controlled_count': 0,
        'arm_agreement': 'none', 'inactive_count_by_reason': dict.fromkeys(module.INACTIVE_REASONS, 0),
        'finding_refs': [], 'finding_record_refs': []})


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required and set(form.fields) == {
        'credit', 'finding'}
    empty = {'investigation_finding': empty_finding(), 'reaction_sheets': []}
    result = EPISODE.final_to_parent(empty, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())
    assert result['credit'] == 2.5 and result['finding']['reaction_sheets'] == []
    assert form.admit(result, 'test') == result


def test_the_model_is_offered_the_access_tools_the_reaction_graders_and_the_children():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered({})
    assert 'execution_estimate' not in names and len(names) == 16 and 'report' not in EPISODE.tools
    assert names[-2:] == ['literature_reaction_populate', 'literature_reaction_source_populate']
    assert 'reason' not in names and set(names) <= set(EPISODE.tools)
    schema = task.selection_schema(names)
    assert len(schema['properties']['selection']['anyOf']) == len(names) + len(CHILDREN)
    assert 'execution_estimate' in task.offered({'tool_registry': {'native_statistics': 'timing_statistics'}})


@pytest.mark.parametrize('slot, arguments', [
    ('passage_evidence_extraction', {'spans': [WINDOW]}),
    ('source_coverage_improvement', WINDOW),
    ('table_evidence_extraction', {'kind': 'window', **WINDOW}),
    ('table_evidence_extraction', {'kind': 'table', 'source_ref': 'src_1', 'sheet_key': 'rId1', 'offset': 0,
                                   'limit': 5, 'header_row': None, 'where': None}),
])
def test_the_commission_names_the_page_and_the_records_the_parent_holds(slot, arguments):
    message = EPISODE.msg_to_child(slot, arguments, {**summary(), 'requested_reaction_components': []})
    assert tuple(message.selection) == ()
    assert message.assignment['received_record_refs'] == ['src_1', 'art_1']
    assert message.assignment['finding_unit'] == 1.0 and message.assignment['scope'] == {'subject_refs': ['sub_1']}
    assert 'requested_reaction_components' not in message.assignment
    requested = EPISODE.msg_to_child(slot, arguments, {**summary(), 'requested_reaction_components': ['ratio_mean']})
    assert requested.assignment['requested_reaction_components'] == ['ratio_mean']
