"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode without children; no module imports another episode folder; the
episode's own forms and functions behave on real data. Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').PassageEvidenceExtraction
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py', 'tests/grading_world.py',
         'tests/test_grading.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
COMMIT_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['terms'],
                 'properties': {'terms': {'type': 'array'}}}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts}


def assignment():
    page = {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'text', 'artifact_ref': 'art_1',
            'question_context_refs': [], 'prior_delivery_refs': []}
    window = {'source_ref': 'src_1', 'representation': 'text', 'offset': 0, 'limit': 10}
    task = {'kind': 'verified_source_leads', 'evidence_axis': 'A105', 'credit_unit': 1.0}
    return {'version': 'reading_assignment_v1', 'page': page, 'selection': {'spans': [window]},
            'literature_task': task, 'proposed_annotation_ref': 'hyp_1',
            'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['src_1', 'art_1']}, window


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
    for path in FOLDER.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module


def test_the_commission_form_admits_a_reading_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    given, window = assignment()
    admitted = form.admit(given, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'read'})
    assert parent_input['spans'] == [window] and parent_input['task_key'] == 'A105:verified_source_leads'
    assert set(form.record_refs(admitted)) == {'src_1', 'art_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**given, 'extra': 1}, 'test')
    other = {**admitted, 'selection': {'spans': [{**window, 'source_ref': 'src_2'}]}}
    with pytest.raises(ValueError, match='literature_reading_source_mismatch'):
        EPISODE.read_from_parent(other, {})
    refused = {**admitted, 'literature_task': {**given['literature_task'], 'evidence_axis': 'A106'}}
    with pytest.raises(ValueError, match='literature_original_task_invalid'):
        EPISODE.read_from_parent(refused, {})


def test_the_yield_controller_is_accumulation_for_leads_and_completion_with_the_commissioned_target_otherwise():
    given, _ = assignment()
    parent = EPISODE.read_from_parent(EPISODE.assignment_form.admit(given, 'test'), {})
    settings = {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}
    assert type(EPISODE.yield_controller(0, settings, parent)).__name__ == 'AccumulationYieldController'
    task = {'kind': 'a105_experiments', 'evidence_axis': 'A105', 'credit_unit': 1.0,
            'experiments': [{'experiment_ref': 'e1', 'assay_type': 'a'}, {'experiment_ref': 'e2', 'assay_type': 'a'}]}
    parent = {**parent, 'task': task}
    controller = EPISODE.yield_controller(0, settings, parent)
    assert type(controller).__name__ == 'CompletionYieldController' and controller.target == 2.0


POPULATION_OFF = {'rate_population': False}
POPULATION_ON = {'rate_population': True, **{name: name == 'assay_grading_population' for name in (
    'assay_grading_population', 'ratio_source_population', 'controlled_response_population', 'gel_population',
    'completion_time_population', 'product_partition_population', 'active_site_population',
    'parent_depletion_population', 'stoichiometric_balance_population', 'compiled_assay_population',
    'channel_population', 'ion_discrimination_population')}}


def passage_summary(**changes):
    value = {'assay_sheets': [], 'aggregation_sheets': [], 'proposed_annotation_ref': 'hyp_1',
             'no_applicable_spans': [], 'screening_covered': False, 'lead_source_refs': []}
    value.update(changes)
    return value


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    assert set(form.fields) == {'credit', 'finding', 'literature_screening_answers',
                                'literature_source_lead_dispositions'}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}
    result = EPISODE.final_to_parent(passage_summary(), completion, ())
    assert result['credit'] == 2.5 and result['finding']['assessment_count'] == 0
    form.admit(result, 'return')


def test_every_selectable_field_returns_counts_and_references_only():
    summary = passage_summary(no_applicable_spans=[{'source_ref': 's'}], screening_covered=False,
                              lead_source_refs=['source_1', 'source_2'])
    selection = ('literature_screening_answers', 'literature_source_lead_dispositions')
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0},
                                     selection)
    assert result['literature_screening_answers'] == {'examined_span_count': 1, 'commissioned_spans_covered': False}
    assert result['literature_source_lead_dispositions']['relevant_lead_count'] == 2
    EPISODE.return_form.select(selection).admit(result, 'return')


def test_the_credit_is_real_code_and_counts_nothing_without_an_answer():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    assert 'NotImplementedError' not in (FOLDER / 'credit.py').read_text()
    summary = {'task': {'kind': 'verified_source_leads', 'credit_unit': 2.0}, 'task_key': 'A105:verified_source_leads',
               'lead_source_refs': [], 'proposed_annotation_ref': 'hyp_1'}
    assert credit_module.credit(summary, None) == 0
    screening = {'task': {'kind': 'source_answer', 'answer_kind': 'screening', 'credit_unit': 3.0,
                          'examined': [{'source_ref': 's', 'artifact_ref': 'a', 'start': 0, 'end': 10}]},
                 'proposed_annotation_ref': 'hyp_1', 'screening_covered': True}
    assert credit_module.credit(screening, None) == 3.0


def test_the_model_is_offered_the_access_tools_the_populations_under_their_flags_and_the_reasoning():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered(POPULATION_OFF)
    assert names[-1] == 'reason' and 'report' not in names and len(names) == 11
    on = task.offered(POPULATION_ON)
    assert 'literature.assay_grading.populate' in on and 'literature.a105.aggregate' in on
    assert 'literature.gel.populate' not in on
    entries = task.catalog(on, COMMIT_SCHEMA, True, POPULATION_ON)
    assert {entry['name'] for entry in entries} <= set(EPISODE.tools)
    assert 'evidence_processing' in [entry for entry in entries if entry['name'] == 'reason'][0]['input_schema']['properties']
    for leads in (False, True):
        schema = task.selection_schema(names, COMMIT_SCHEMA, leads, POPULATION_OFF)
        assert len(schema['properties']['selection']['anyOf']) == len(names)
    assert len(task.POPULATIONS) == 35 and set(task.TOOL_NAMES.values()) == set(EPISODE.tools) - {'reason'}
    with pytest.raises(KeyError):
        task.offered({})
