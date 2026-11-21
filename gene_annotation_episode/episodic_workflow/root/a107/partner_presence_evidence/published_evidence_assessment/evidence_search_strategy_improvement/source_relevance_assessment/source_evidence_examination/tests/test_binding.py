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
SLOTS = {'literature_table': 'table_evidence_extraction', 'literature_ordered': 'source_coverage_improvement',
         'literature_targeted': 'passage_evidence_extraction'}
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py', 'tests/test_model_run.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
SOURCE, ARTIFACT = 'source_' + 'a' * 24, 'artifact_' + 'b' * 24
PAGE = {'version': 'page_assignment_v1', 'source_ref': SOURCE, 'representation': 'text', 'artifact_ref': ARTIFACT,
        'question_context_refs': [], 'prior_delivery_refs': []}
ASSIGNMENT = {**PAGE, 'scope': {'subject_refs': []}, 'finding_unit': 1.0, 'received_record_refs': [SOURCE, ARTIFACT]}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts
            and path.relative_to(FOLDER).parts[0] not in SLOTS.values()}


def child_episode(name):
    module = importlib.import_module(PACKAGE + '.' + name + '.episode')
    return [value for value in vars(module).values()
            if isinstance(value, type) and issubclass(value, EpisodeBinding) and value is not EpisodeBinding][0]


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {slot: EPISODE.binding_path + '/' + name for slot, name in SLOTS.items()}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_children():
    assert files() == FILES


def test_no_module_of_the_folder_imports_an_episode_folder_outside_its_own_tree():
    for path in FOLDER.rglob('*.py'):
        if '__pycache__' in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module
    for path in FOLDER.glob('*.py'):     # this episode's own files import none of its children either
        for node in ast.walk(ast.parse(path.read_text())):
            modules = [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else []
            assert not any(module.startswith(PACKAGE) for module in modules), path.name


def test_the_commission_form_admits_a_page_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {})
    assert parent_input['page'] == PAGE and parent_input['finding_unit'] == 1.0
    assert parent_input['partner_components'] is None
    assert set(form.record_refs(admitted)) == {SOURCE, ARTIFACT}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'extra': 1}, 'test')


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert set(form.fields) == {'credit', 'finding'}
    summary = {'partner_sheets': [], 'partner_agreement': {'matched_sheet_count': 0, 'matched_loss_sheet_count': 0,
                                                           'distinct_experiment_count': 0}}
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())
    assert result == {'credit': 2.5, 'finding': {'partner_sheets': [], **summary['partner_agreement']}}
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


def test_the_model_can_name_each_child_with_the_selection_its_child_reads():
    task = importlib.import_module(PACKAGE + '.task')
    assert set(task.CHILD_SLOTS) == set(SLOTS) and set(task.child_selections(PAGE)) == set(SLOTS)
    assert set(task.TOOLS) == {'source_read', 'source_locate', 'literature_partner_populate',
                               'literature_partner_source_populate'}
    assert set(EPISODE.tools) == set(task.TOOLS)


WINDOW = {'source_ref': SOURCE, 'representation': 'text', 'offset': 0, 'limit': 10}
SELECTIONS = {'literature_targeted': {'spans': [WINDOW]}, 'literature_ordered': WINDOW,
              'literature_table': {'source_ref': SOURCE, 'sheet_key': 'rId1', 'offset': 0, 'limit': 5}}


@pytest.mark.parametrize('slot', SLOTS)
def test_the_commission_of_each_child_is_admitted_by_the_childs_own_forms(slot):
    summary = {'page': PAGE, 'scope': {'subject_refs': []}, 'finding_unit': 1.0, 'partner_components': ['removal'],
               'held_record_refs': [ARTIFACT, SOURCE]}
    message = EPISODE.msg_to_child(slot, {'selection': SELECTIONS[slot]}, summary)
    child = child_episode(SLOTS[slot])
    admitted = child.assignment_form.admit(dict(message.assignment), slot)
    child.read_from_parent(admitted, dict(message.message))
    child.return_form.select(message.selection)
    assert child.binding_path == EPISODE.child_slots[slot]
    finding = {'partner_sheets': [], 'matched_sheet_count': 0, 'matched_loss_sheet_count': 0,
               'distinct_experiment_count': 0}
    child.return_form.select(message.selection).admit({'credit': 1.0, 'finding': finding}, slot)
    assert EPISODE.read_from_child(slot, {'credit': 1.0, 'finding': finding}, summary, None) == {
        'slot': slot, 'credit': 1.0, **finding}


def test_the_input_list_shrinks_as_children_are_handed_candidates_and_offers_only_unconsumed_ones():
    task = importlib.import_module(PACKAGE + '.task')
    summary_file = importlib.import_module(PACKAGE + '.messages.internal_summary')
    content = ('First paragraph about the partner.\n\n' + 'x ' * 3000).encode('utf-8')
    candidates = summary_file.page_candidates(content)
    assert len(candidates) >= 2
    ids = [item['candidate_id'] for item in candidates]

    def state(consumed):
        left = [item for item in candidates if item['candidate_id'] not in consumed]
        return {'page': PAGE, 'input_list_basis': 'text', 'content_candidates': candidates,
                'unconsumed_candidate_ids': [item['candidate_id'] for item in left],
                'unconsumed_table_ids': []}

    full = task.candidate_selections(state([]))
    assert full['literature_ordered']['properties']['candidate_id']['enum'] == ids
    first = candidates[0]
    handed = [{'outcome': None, 'kind': 'child', 'arguments': {'selection': task.window_of(state([]), ids[0])}}]
    consumed = summary_file.consumed_candidates(handed, candidates)
    assert ids[0] in consumed and set(consumed) <= set(ids)
    assert task.window_of(state([]), ids[0])['limit'] == first['end'] - first['start']
    empty = task.candidate_selections(state(ids))
    assert set(empty) == {'literature_table'}
    assert summary_file.consumed_candidates(
        [{'arguments': {'selection': {'source_ref': SOURCE, 'sheet_key': 'rId1', 'offset': 0, 'limit': 5}}}],
        candidates) == []
    binary = task.candidate_selections({'page': PAGE, 'input_list_basis': 'not_utf8'})
    assert set(binary) == set(task.CHILD_SLOTS)
