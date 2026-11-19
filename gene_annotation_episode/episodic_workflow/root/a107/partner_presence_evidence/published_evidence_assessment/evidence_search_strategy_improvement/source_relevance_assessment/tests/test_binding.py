"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set (plus its child episode folder); no module imports an episode folder outside its own
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
CHILDREN = {'literature_page': 'source_evidence_examination'}
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
SOURCE, ARTIFACT = 'source_' + 'a' * 24, 'artifact_' + 'b' * 24
ASSIGNMENT = {'version': 'search_assignment_v1', 'question_context_refs': [], 'search_result_refs': [SOURCE],
              'scope': {'subject_refs': []}, 'finding_unit': 1.0, 'received_record_refs': [SOURCE, ARTIFACT]}
PAGE = {'version': 'page_assignment_v1', 'source_ref': SOURCE, 'representation': 'text', 'artifact_ref': ARTIFACT,
        'question_context_refs': [], 'prior_delivery_refs': []}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts
            and path.relative_to(FOLDER).parts[0] not in CHILDREN.values()}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {slot: EPISODE.binding_path + '/' + name for slot, name in CHILDREN.items()}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_a_child():
    assert files() == FILES


def test_no_module_of_the_folder_imports_an_episode_folder_outside_its_own_tree():
    for path in FOLDER.rglob('*.py'):
        if '__pycache__' in path.parts or path.relative_to(FOLDER).parts[0] in CHILDREN.values():
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module
                assert not module.startswith(PACKAGE + '.' + CHILDREN['literature_page']), \
                    str(path.relative_to(FOLDER)) + ' imports its child ' + module


def test_the_commission_form_admits_a_search_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {})
    assert parent_input['search_result_refs'] == [SOURCE] and parent_input['finding_unit'] == 1.0
    assert parent_input['partner_components'] is None
    assert set(form.record_refs(admitted)) == {SOURCE, ARTIFACT}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'extra': 1}, 'test')


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert set(form.fields) == {'credit', 'finding'}
    counts = {'matched_sheet_count': 0, 'matched_loss_sheet_count': 0, 'distinct_experiment_count': 0}
    summary = {'partner_sheets': [], 'partner_agreement': counts}
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())
    assert result == {'credit': 2.5, 'finding': {'partner_sheets': [], **counts}}
    form.admit(result, 'test')


def test_credit_and_finding_cannot_be_selected():
    with pytest.raises(FormError):
        EPISODE.return_form.select(('credit',))


def test_the_credit_is_real_code_and_the_controller_is_accumulation():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    assert 'NotImplementedError' not in (FOLDER / 'credit.py').read_text()
    controller = EPISODE.yield_controller(0.0, {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.1}}, {})
    assert type(controller).__name__ == 'AccumulationYieldController'


def test_the_model_can_name_the_child_and_the_acquisition_tools():
    task = importlib.import_module(PACKAGE + '.task')
    assert set(task.CHILD_SLOTS) == set(CHILDREN) and set(task.CHILD_SELECTIONS) == set(CHILDREN)
    assert set(task.TOOLS) >= {'state_query', 'public_literature_search', 'public_pmc_asset'}
    assert 'report_finding' not in task.TOOLS
    assert set(EPISODE.tools) == set(task.TOOLS)


def test_the_commission_of_the_child_passes_the_page_the_scope_and_the_held_records():
    summary = {'scope': {'subject_refs': []}, 'finding_unit': 1.0, 'partner_components': ['removal'],
               'held_record_refs': [ARTIFACT, SOURCE]}
    message = EPISODE.msg_to_child('literature_page', {'selection': PAGE}, summary)
    assert message.assignment == {**PAGE, 'scope': summary['scope'], 'finding_unit': 1.0,
                                  'received_record_refs': [ARTIFACT, SOURCE],
                                  'literature_partner_components': ['removal']}
    assert message.selection == ()
    with pytest.raises(ValueError, match='unsupported_literature_child_slot'):
        EPISODE.msg_to_child('other', {'selection': PAGE}, summary)
    finding = {'partner_sheets': [], 'matched_sheet_count': 0, 'matched_loss_sheet_count': 0,
               'distinct_experiment_count': 0}
    assert EPISODE.read_from_child('literature_page', {'credit': 1.0, 'finding': finding}, summary, None) == {
        'slot': 'literature_page', 'credit': 1.0, **finding}
