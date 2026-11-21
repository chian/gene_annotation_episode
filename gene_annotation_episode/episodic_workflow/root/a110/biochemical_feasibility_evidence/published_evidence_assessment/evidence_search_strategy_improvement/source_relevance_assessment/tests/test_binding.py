"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set (its child episode folder is its own); no module of the folder imports another
episode folder; the episode's own forms and functions behave on real data, and what ``msg_to_child`` builds is
admitted by the real child form. Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceRelevanceAssessment
CHILD = 'source_evidence_examination'
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
ASSIGNMENT = {'version': 'search_assignment_v1', 'question_context_refs': ['ctx_1'],
              'search_result_refs': ['src_1'], 'scope': {'subject_refs': ['sub_1']}, 'finding_unit': 1.0,
              'received_record_refs': ['src_1', 'art_1', 'ctx_1']}
ARGUMENTS = {'source_ref': 'src_2', 'representation': 'text', 'artifact_ref': 'art_2',
             'question_context_refs': ['ctx_1'], 'prior_delivery_refs': []}


def own_files(root=FOLDER):
    return {str(path.relative_to(FOLDER)) for path in root.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts
            and CHILD not in path.relative_to(FOLDER).parts}


def summary():
    admitted = EPISODE.assignment_form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {})
    return {'assignment': parent_input['assignment'], 'scope': parent_input['scope'], 'finding_unit': 1.0,
            'received_record_refs': parent_input['received_record_refs'],
            'requested_reaction_components': [], 'input_list': ['src_1'], 'consumed_input_ids': [],
            'held_sources': {'src_1': {'artifact_ref': 'art_1', 'text_ref': None, 'stdout_ref': None,
                                       'stderr_ref': None, 'parent_source_refs': []},
                             'src_2': {'artifact_ref': 'art_2', 'text_ref': 'txt_2', 'stdout_ref': None,
                                       'stderr_ref': None, 'parent_source_refs': ['src_1']}}}


def child_class():
    module = importlib.import_module(PACKAGE + '.' + CHILD + '.episode')
    return next(value for name, value in vars(module).items()
                if isinstance(value, type) and issubclass(value, EpisodeBinding) and value is not EpisodeBinding)


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {CHILD: EPISODE.binding_path + '/' + CHILD}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_a_child():
    assert own_files() == FILES


def test_no_module_of_the_folder_imports_another_episode_folder():
    for path in (FOLDER / name for name in sorted(FILES) if name.endswith('.py')):
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module


def test_the_commission_form_admits_a_search_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'assess'})
    assert parent_input['assignment']['search_result_refs'] == ['src_1'] and parent_input['finding_unit'] == 1.0
    assert set(form.record_refs(admitted)) == {'src_1', 'art_1', 'ctx_1'}
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
    assert set(form.fields) == {'credit', 'finding'}
    assert form.fields['credit'].required and form.fields['finding'].required
    result = EPISODE.final_to_parent({'investigation_finding': empty_finding(), 'reaction_sheets': []},
                                     {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())
    assert result['credit'] == 2.5 and form.admit(result, 'test') == result
    text_fields = [name for name, spec in form.fields['finding'].form.fields.items() if spec.type == 'text']
    assert all(hasattr(form.fields['finding'].form.fields[name], 'options') for name in text_fields)


def test_the_model_is_offered_the_access_and_acquisition_tools_the_reaction_graders_and_the_child():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered({})
    assert 'execution_estimate' not in names and len(names) == 14 + 18 + 2 and 'report' not in EPISODE.tools
    assert names[-2:] == ['literature_reaction_populate', 'literature_reaction_source_populate']
    assert {'public_literature_search', 'public_pmc_asset', 'public_brenda_graph_search'} <= set(names)
    assert 'reason' not in names and set(names) <= set(EPISODE.tools)
    schema = task.selection_schema(names, summary())
    assert len(schema['properties']['selection']['anyOf']) == len(names) + 1
    child = schema['properties']['selection']['anyOf'][-1]['properties']['arguments']
    assert child['properties']['source_ref'] == {'enum': ['src_1']}
    assert len(task.selection_schema(names, {**summary(), 'input_list': []})['properties']['selection']['anyOf']) == len(names)
    assert 'execution_estimate' in task.offered({'tool_registry': {'native_statistics': object()}})


def test_what_the_commission_builds_is_admitted_by_the_real_child_form_and_names_the_source_closure():
    message = EPISODE.msg_to_child(CHILD, ARGUMENTS, summary())
    cls = child_class()
    admitted = cls.assignment_form.admit(message.assignment, 'commission')
    assert set(cls.assignment_form.record_refs(admitted)) >= {'src_2', 'art_2', 'txt_2', 'src_1', 'art_1', 'ctx_1'}
    cls.read_from_parent(admitted, message.message)
    cls.return_form.select(message.selection)
    with pytest.raises(FormError):
        cls.return_form.select(('not_a_selectable_field',))
    with pytest.raises(KeyError):
        EPISODE.msg_to_child(CHILD, {**ARGUMENTS, 'source_ref': 'src_9'}, summary())
    with pytest.raises(KeyError):
        EPISODE.msg_to_child('no_such_slot', ARGUMENTS, summary())


def test_an_examined_source_and_the_search_results_it_derives_from_are_consumed():
    module = importlib.import_module(PACKAGE + '.messages.internal_summary')
    held = summary()['held_sources']
    children = [{'arguments': {'source_ref': 'src_2'}}]
    assert module.consumed_search_results(children, held, {'src_1'}) == ['src_1']
    assert module.consumed_search_results([], held, {'src_1'}) == []


def test_a_child_return_becomes_the_parents_report_of_credit_and_controlled_finding():
    finding = {**empty_finding(), 'reaction_sheets': []}
    report = EPISODE.read_from_child(CHILD, {'credit': 1.0, 'finding': finding}, {}, None)
    assert report == {'slot': CHILD, 'credit': 1.0, 'finding': finding}


def test_the_commission_passes_the_requested_reaction_cells():
    plain = EPISODE.msg_to_child(CHILD, ARGUMENTS, summary())
    assert 'requested_reaction_components' not in plain.assignment
    requested = EPISODE.msg_to_child(CHILD, ARGUMENTS, {**summary(), 'requested_reaction_components': ['ratio_mean']})
    assert requested.assignment['requested_reaction_components'] == ['ratio_mean']

