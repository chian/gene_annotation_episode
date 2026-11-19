"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set (plus its child episode folders); no module imports an episode folder outside its own
tree; the episode's own forms and functions behave on real data. Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceRelevanceAssessment
CHILDREN = ('source_evidence_examination',)
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
ASSIGNMENT = {'version': 'search_assignment_v1', 'question_context_refs': ['ctx_1'], 'search_result_refs': ['src_1']}
PAGE = {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'text', 'artifact_ref': 'art_1',
        'question_context_refs': [], 'prior_delivery_refs': []}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts
            and path.relative_to(FOLDER).parts[0] not in CHILDREN}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {name: EPISODE.binding_path + '/' + name for name in CHILDREN}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_children():
    assert files() == FILES


def test_no_module_of_the_folder_imports_an_episode_folder_outside_its_own_tree():
    own = PACKAGE
    for path in FOLDER.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == own or module.startswith(own + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module
    for path in FOLDER.glob('*.py'):     # and this episode's own files import none of its children either
        for node in ast.walk(ast.parse(path.read_text())):
            modules = [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else []
            assert not any(module.startswith(own) for module in modules), path.name


def test_the_commission_form_admits_a_search_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    assignment = {**ASSIGNMENT, 'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['ctx_1', 'src_1']}
    admitted = form.admit(assignment, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'assess'})
    assert parent_input['assignment'] == ASSIGNMENT and parent_input['scope'] == {'subject_refs': ['sub_1']}
    assert set(form.record_refs(admitted)) == {'ctx_1', 'src_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**assignment, 'extra': 1}, 'test')


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    summary = {'report': None, 'report_source_held': {}}
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())
    assert result == {'credit': 2.5, 'finding': {'merits_examination_refs': [], 'assessed_source_count': 0}}
    form.admit(result, 'test')
    report = {'assessments': [{'source_ref': 'src_1', 'merits_examination': True},
                              {'source_ref': 'src_2', 'merits_examination': False}]}
    written = EPISODE.final_to_parent({'report': report, 'report_source_held': {'src_1': True}},
                                      {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 0.5}, ())
    assert form.admit(written, 'test')['finding'] == {'merits_examination_refs': ['src_1'],
                                                      'assessed_source_count': 2}
    assert form.record_refs(written) == ('src_1',)


def test_the_credit_is_the_native_correspondence_projector_and_never_a_stub():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    assert credit_module.A101SequenceCredit().as_record()['kind'] == 'a101_native_sequence_correspondence'
    assert 'NotImplementedError' not in (FOLDER / 'credit.py').read_text()


def test_the_model_is_offered_the_access_and_acquisition_tools_the_child_and_the_report():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered({'tool_registry': {}})
    assert 'execution_estimate' not in names and names[-1] == 'report' and len(names) == 15 - 1 + 7 + 1
    assert set(names) <= set(EPISODE.tools)
    schema = task.selection_schema(names)
    assert len(schema['properties']['selection']['anyOf']) == len(names) + len(CHILDREN)
    assert 'execution_estimate' in task.offered({'tool_registry': {'native_statistics': object()}})
    ncbi = [entry for entry in task.catalog(names) if entry['name'] == 'public_ncbi_search'][0]
    assert ncbi['input_schema']['properties']['database'] == {'enum': ['pubmed']}


def test_the_commission_of_the_child_carries_the_page_this_scope_and_the_held_records():
    summary = {'scope': {'subject_refs': ['sub_1']}, 'held_record_refs': ['art_1', 'src_1']}
    message = EPISODE.msg_to_child('source_evidence_examination', {'page': PAGE}, summary)
    assert message.assignment == {**PAGE, 'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['art_1', 'src_1']}
    assert tuple(message.selection) == ()
    finding = {'source_refs': ['src_1'], 'written': False, 'entry_count': 0}
    report = EPISODE.read_from_child('source_evidence_examination', {'credit': 1.0, 'finding': finding},
                                     summary, None)
    assert report == {'slot': 'source_evidence_examination', 'credit': 1.0, 'finding': finding}
