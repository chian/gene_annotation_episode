"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode with children (its child episode folder aside); no module of the folder
imports another episode folder; the episode's own forms and functions behave on real data. Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildMessage, EpisodeBinding
from method_loop import FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').ExperimentalActivityEvidence
CHILDREN = ('literature',)
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py', 'tests/grading_world.py',
         'tests/test_decision_schema.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
OPTION = {'version': 'experimental_activity_evidence_option_ref_v1', 'library_id': 'a' * 64,
          'entry_sha256': 'b' * 64}
SCOPE = {'subject_refs': ['sub_1']}


def own_files():
    return {path for path in FOLDER.rglob('*') if path.is_file() and '__pycache__' not in path.parts
            and path.relative_to(FOLDER).parts[0] not in CHILDREN}


def assignment():
    return {'selection': {'version': 'experimental_activity_evidence_selection_v1',
                          'evidence_axis': {**OPTION, 'slot': 'evidence_axis', 'option_id': 'A105'},
                          'thought_pattern': {**OPTION, 'slot': 'thought_pattern', 'option_id': 'P1'},
                          'child_tool_info': [{'name': 'source.read', 'resources': 'api'}]},
            'proposed_annotation_ref': 'hyp_1', 'evidence_refs': ['sub_1', 'hyp_1'], 'constraints': {},
            'context': {'evidence_task': {'version': 'evidence_axis_task_v1', 'kind': 'whole_axis_findings',
                                          'evidence_axis': 'A105', 'credit_unit': 1.0}},
            'scope': SCOPE}


def parent_input():
    return EPISODE.read_from_parent(EPISODE.assignment_form.admit(assignment(), 'test'), {'purpose': 'x'})


def summary(**changes):
    parent = parent_input()
    value = {**{name: parent[name] for name in ('selection', 'proposed_annotation_ref', 'evidence_refs',
                                                'constraints', 'evidence_task', 'revision_origin', 'scope')},
             'held_record_refs': ['hyp_1', 'sub_1'], 'investigations': [], 'assessment_refs': [], 'sheet_refs': [],
             'no_applicable_evidence': [], 'child_returns': [], 'child_finding_refs': [], 'child_sheet_refs': [],
             'progress': {'credit': 0.0}, 'committed_record_refs': []}
    value.update(changes)
    return value


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert EPISODE.binding_path == 'experimental_activity_evidence'
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {
        'experimental_activity_evidence': 'experimental_activity_evidence',
        'literature': 'experimental_activity_evidence/literature'}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_children_and_its_child_folder():
    assert {str(path.relative_to(FOLDER)) for path in own_files()} == FILES
    assert {path.name for path in FOLDER.iterdir() if path.is_dir() and path.name != '__pycache__'} == {
        'messages', 'tests', *CHILDREN}


def test_no_module_of_the_folder_imports_another_episode_folder():
    for path in own_files():
        if path.suffix != '.py':
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module
                assert not any(module == PACKAGE + '.' + child or module.startswith(PACKAGE + '.' + child + '.')
                               for child in CHILDREN), str(path.relative_to(FOLDER)) + ' imports ' + module


def test_the_yield_controller_is_the_accumulation_controller_from_the_settings():
    controller = EPISODE.yield_controller(2.0, {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.1}},
                                          parent_input())
    assert type(controller).__name__ == 'AccumulationYieldController' and controller.cost == 0.1


def test_the_credit_is_real_code_over_the_finding_progress_projection():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    assert 'NotImplementedError' not in (FOLDER / 'credit.py').read_text()
    assert credit_module.credit_binding(1.0)['policy']['finding_unit'] == 1.0


def test_the_model_is_offered_the_selected_tools_the_lookups_the_revision_and_the_reasoning():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered(summary())
    assert names == ['source.read', 'process.search', 'process.entry', 'process.sources', 'process.revise', 'reason']
    schema = {'type': 'object', 'additionalProperties': False, 'required': ['terms'],
              'properties': {'terms': {'type': 'array'}}}
    entries = task.catalog(names, schema)
    assert {entry['name'] for entry in entries} <= set(EPISODE.tools)
    assert 'evidence_processing' in [entry for entry in entries if entry['name'] == 'reason'][0]['input_schema']['properties']
    assert len(task.selection_schema(names, schema)['properties']['selection']['anyOf']) == len(names) + 2
    assert set(task.CHILD_ARGUMENTS) == set(EPISODE.child_slots)
    assert task.empty_commit({'terms': []}, schema) and not task.empty_commit({'terms': [{}]}, schema)
    assert set(task.TOOL_NAMES.values()) <= set(EPISODE.tools)
    unknown = summary(selection={**assignment()['selection'], 'child_tool_info': [
        {'name': 'material.read', 'resources': 'local'}]})
    with pytest.raises(ValueError, match='a105_selected_tools_not_in_the_tool_library:material.read'):
        task.offered(unknown)

