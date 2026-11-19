"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set (plus its child episode folders); no module imports an episode folder outside its own
tree; the episode's own forms and functions behave on real data, and its commission is admitted by the real
assignment form of each child. Nothing here is faked."""
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
         'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
PAGE = {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'text', 'artifact_ref': 'art_1',
        'question_context_refs': [], 'prior_delivery_refs': []}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts
            and path.relative_to(FOLDER).parts[0] not in CHILDREN}


def child(name, module):
    return importlib.import_module(PACKAGE + '.' + name + '.' + module)


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


def test_the_commission_form_admits_a_page_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    assignment = {**PAGE, 'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['src_1', 'art_1']}
    admitted = form.admit(assignment, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'examine'})
    assert parent_input['page'] == PAGE and parent_input['scope'] == {'subject_refs': ['sub_1']}
    assert set(form.record_refs(admitted)) == {'src_1', 'art_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**assignment, 'extra': 1}, 'test')


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    summary = {'report': None, 'report_source_held': {}, 'literature_assignment': PAGE}
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())
    assert result['credit'] == 2.5 and result['finding']['written'] is False
    assert result['finding']['source_refs'] == ['src_1'] and result['finding']['entry_count'] == 0
    form.admit(result, 'test')
    report = {'entries': [{'source_ref': 'src_1', 'claim_kind': 'reported_domain_assignment',
                           'subject_relation': 'target_itself', 'measured': False}]}
    written = EPISODE.final_to_parent({**summary, 'report': report},
                                      {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 0.5}, ())
    finding = form.admit(written, 'test')['finding']
    assert finding['entry_count'] == 1 and finding['claim_count_reported_domain_assignment'] == 1
    assert finding['unresolved_correspondence_count'] == 0
    assert all(spec.type != 'text' for spec in form.fields['finding'].form.fields.values())


def test_the_credit_is_the_native_correspondence_projector_and_never_a_stub():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    assert credit_module.A101SequenceCredit().as_record()['kind'] == 'a101_native_sequence_correspondence'
    assert 'NotImplementedError' not in (FOLDER / 'credit.py').read_text()


def test_the_model_is_offered_the_access_tools_the_children_and_the_report():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered({'tool_registry': {}})
    assert 'execution_estimate' not in names and names[-1] == 'report' and len(names) == 15
    assert set(names) <= set(EPISODE.tools)
    schema = task.selection_schema(names)
    assert len(schema['properties']['selection']['anyOf']) == len(names) + len(CHILDREN)
    assert 'execution_estimate' in task.offered({'tool_registry': {'native_statistics': object()}})


WINDOW = {'source_ref': 'src_1', 'representation': 'text', 'offset': 0, 'limit': 10}
SELECTIONS = {'passage_evidence_extraction': {'spans': [WINDOW]}, 'source_coverage_improvement': WINDOW,
              'table_evidence_extraction': {'source_ref': 'src_1', 'sheet_key': 'rId1', 'offset': 0, 'limit': 5}}


@pytest.mark.parametrize('slot', CHILDREN)
def test_the_commission_of_each_child_is_admitted_by_the_childs_own_forms(slot):
    summary = {'literature_assignment': PAGE, 'scope': {'subject_refs': ['sub_1']},
               'held_record_refs': ['art_1', 'src_1']}
    message = EPISODE.msg_to_child(slot, {'selection': SELECTIONS[slot]}, summary)
    child_episode = [value for value in vars(child(slot, 'episode')).values()
                     if isinstance(value, type) and issubclass(value, EpisodeBinding) and value is not EpisodeBinding][0]
    admitted = child_episode.assignment_form.admit(dict(message.assignment), slot)
    child_episode.read_from_parent(admitted, dict(message.message))
    child_episode.return_form.select(message.selection)
    assert child_episode.binding_path == EPISODE.child_slots[slot]
    result = child_episode.final_to_parent({'report': None}, {'ended_by': 'yield_stop', 'units_consumed': 0,
                                                              'credit': 1.0}, message.selection)
    admitted_result = child_episode.return_form.select(message.selection).admit(result, slot)
    report = EPISODE.read_from_child(slot, admitted_result, summary, None)
    assert report == {'slot': slot, 'credit': 1.0, 'finding': admitted_result['finding']}
    assert report['finding']['written'] is False and report['finding']['entries'] == []

