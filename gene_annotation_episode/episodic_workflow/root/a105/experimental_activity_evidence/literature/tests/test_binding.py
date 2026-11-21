"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode with a child (its child episode folder aside); no module of the folder
imports another episode folder; the episode's own forms and functions behave on real data. Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildMessage, EpisodeBinding
from method_loop import FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').PublishedEvidenceAssessment
CHILDREN = ('strategy',)
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py', 'tests/grading_world.py', 'tests/test_grading.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
COMMIT_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['terms'],
                 'properties': {'terms': {'type': 'array'}}}
STRATEGY = {'prior_search_refs': ['src_1']}


def own_files():
    return {path for path in FOLDER.rglob('*') if path.is_file() and '__pycache__' not in path.parts
            and path.relative_to(FOLDER).parts[0] not in CHILDREN}


def assignment():
    task = {'version': 'literature_local_task_v1', 'kind': 'verified_source_leads', 'evidence_axis': 'A105',
            'credit_unit': 1.0}
    return {'version': 'literature_assignment_v1', 'question_context_refs': ['ctx_1'], 'source_refs': ['src_1'],
            'literature_task': task, 'proposed_annotation_ref': 'hyp_1',
            'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['src_1', 'art_1', 'ctx_1']}


def summary_of(requested=None, task=None):
    given = assignment()
    literature = {name: given[name] for name in ('version', 'question_context_refs', 'source_refs')}
    return {'literature': literature, 'task': task or given['literature_task'],
            'task_key': 'A105:verified_source_leads', 'proposed_annotation_ref': 'hyp_1', 'scope': given['scope'],
            'requested': requested or {}, 'held_record_refs': ['art_1', 'ctx_1', 'src_1']}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert EPISODE.binding_path == 'experimental_activity_evidence/literature'
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {slot: EPISODE.binding_path + '/' + slot for slot in CHILDREN}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_a_child_and_its_child_folder():
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


def test_the_commission_form_admits_a_literature_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    given = assignment()
    admitted = form.admit(given, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'assess'})
    assert parent_input['literature']['source_refs'] == ['src_1']
    assert parent_input['task_key'] == 'A105:verified_source_leads' and 'page' not in parent_input
    assert set(form.record_refs(admitted)) == {'src_1', 'art_1', 'ctx_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**given, 'extra': 1}, 'test')
    refused = {**admitted, 'literature_task': {**given['literature_task'], 'evidence_axis': 'A106'}}
    with pytest.raises(Exception, match='representation_error'):
        EPISODE.read_from_parent(refused, {})


def test_the_old_commission_rules_still_refuse_a_wrong_task():
    admitted = EPISODE.assignment_form.admit(assignment(), 'test')
    task = {'version': 'literature_local_task_v1', 'evidence_axis': 'A105', 'credit_unit': 1.0}
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import (
        ASSAY_TYPES)
    experiment = 'experiment_' + 'c' * 24
    duplicate = {**admitted, 'literature_task': {
        **task, 'kind': 'a105_experiments',
        'experiments': [{'experiment_ref': experiment, 'assay_type': ASSAY_TYPES[0]},
                        {'experiment_ref': experiment, 'assay_type': ASSAY_TYPES[0]}]}}
    with pytest.raises(Exception, match='literature_task_duplicate_experiment'):
        EPISODE.read_from_parent(duplicate, {})
    metrics = {**admitted, 'literature_task': {**task, 'kind': 'a105_assembly', 'experiment_refs': [experiment],
                                               'metrics': ['overall']}}
    with pytest.raises(Exception, match='literature_task_requested_metrics_mismatch'):
        EPISODE.read_from_parent(metrics, {})
    span = {'source_ref': 'source_' + 'a' * 24, 'artifact_ref': 'artifact_' + 'a' * 24, 'start': 5, 'end': 5}
    screening = {**admitted, 'literature_task': {**task, 'kind': 'source_answer', 'answer_kind': 'screening',
                                                 'examined': [span]}}
    with pytest.raises(Exception, match='literature_task_screening_span_invalid'):
        EPISODE.read_from_parent(screening, {})


def test_the_yield_controller_is_accumulation_for_leads_and_completion_with_the_commissioned_target_otherwise():
    parent = EPISODE.read_from_parent(EPISODE.assignment_form.admit(assignment(), 'test'), {})
    settings = {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}
    assert type(EPISODE.yield_controller(0, settings, parent)).__name__ == 'AccumulationYieldController'
    task = {'version': 'literature_local_task_v1', 'kind': 'a105_experiments', 'evidence_axis': 'A105',
            'credit_unit': 1.0, 'experiments': [{'experiment_ref': 'e1', 'assay_type': 'a'},
                                                {'experiment_ref': 'e2', 'assay_type': 'a'}]}
    controller = EPISODE.yield_controller(0, settings, {**parent, 'task': task})
    assert type(controller).__name__ == 'CompletionYieldController' and controller.target == 2.0


FLAGS = ('assay_grading_population', 'ratio_source_population', 'controlled_response_population', 'gel_population',
         'completion_time_population', 'product_partition_population', 'active_site_population',
         'parent_depletion_population', 'stoichiometric_balance_population', 'compiled_assay_population',
         'channel_population', 'ion_discrimination_population')
POPULATION_OFF = {'rate_population': False}


def mid_summary(**changes):
    value = {'assay_sheets': [], 'aggregation_sheets': [], 'proposed_annotation_ref': 'hyp_1',
             'no_applicable_spans': [], 'screening_covered': False, 'lead_source_refs': []}
    value.update(changes)
    return value


def test_the_credit_is_real_code_and_counts_the_answers():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    summary = {'task': {'kind': 'verified_source_leads', 'credit_unit': 2.0}, 'task_key': 'A105:verified_source_leads',
               'lead_source_refs': ['src_1', 'src_2'], 'own_lead_source_refs': ['src_2'],
               'child_returns': [{'credit': 0.5}, {'credit': 0.25}], 'proposed_annotation_ref': 'hyp_1'}
    # the credit the child returned plus credit_unit for each lead the episode's own reason units validated
    assert credit_module.credit(summary, None) == 2.75
    screening = {'task': {'kind': 'source_answer', 'answer_kind': 'screening', 'credit_unit': 3.0, 'examined': []},
                 'proposed_annotation_ref': 'hyp_1', 'screening_covered': True}
    assert credit_module.credit(screening, None) == 3.0


def test_the_model_is_offered_the_access_and_acquisition_tools_the_reasoning_and_the_child():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered(POPULATION_OFF)
    assert names[-1] == 'reason' and 'report' not in names
    entries = task.catalog(names, COMMIT_SCHEMA, True, POPULATION_OFF)
    assert {entry['name'] for entry in entries} <= set(EPISODE.tools)
    assert 'evidence_processing' in [entry for entry in entries if entry['name'] == 'reason'][0]['input_schema']['properties']
    for leads in (False, True):
        schema = task.selection_schema(names, COMMIT_SCHEMA, leads, POPULATION_OFF, ['src_1', 'src_2'])
        assert len(schema['properties']['selection']['anyOf']) == len(names) + len(task.CHILD_SLOTS)
        child = schema['properties']['selection']['anyOf'][-1]['properties']['arguments']
        assert child['properties']['strategy']['properties']['prior_search_refs']['items'] == {
            'enum': ['src_1', 'src_2']}
        empty = task.selection_schema(names, COMMIT_SCHEMA, leads, POPULATION_OFF, [])
        assert len(empty['properties']['selection']['anyOf']) == len(names)
    assert set(task.CHILD_ARGUMENTS) == set(EPISODE.child_slots) == set(task.CHILD_SLOTS)
    assert len(task.POPULATIONS) == 35 and set(task.TOOL_NAMES.values()) == set(EPISODE.tools) - {'reason'}
    assert len(task.offered({'rate_population': True, **{name: True for name in FLAGS}})) == len(names) + 35


def test_the_input_list_is_the_unconsumed_sources_and_a_consumed_source_is_not_offered():
    summary = importlib.import_module(PACKAGE + '.messages.internal_summary')
    task = importlib.import_module(PACKAGE + '.task')
    leads = {'kind': 'verified_source_leads'}
    read = {'kind': 'tool', 'tool': 'source_read', 'outcome': {'status': 'completed'},
            'arguments': {'arguments': {'source_ref': 'src_1'}, 'scope': {}}}
    invalid = {'kind': 'tool', 'tool': 'source_read', 'outcome': {'status': 'invalid'},
               'arguments': {'arguments': {'source_ref': 'src_2'}, 'scope': {}}}
    graded = {'kind': 'tool', 'tool': 'reason', 'outcome': {'status': 'completed'},
              'arguments': {'arguments': {'evidence_processing': {'kind': 'graded', 'gradings': [
                  {'arguments': '{"witness": {"source_ref": "src_3"}}'}]}}}}
    child = {'kind': 'child', 'slot': 'strategy', 'arguments': {'objective': 'o',
                                                                'strategy': {'prior_search_refs': ['src_4']}}}
    # a read is a look, not the work on the source: it consumes nothing, so src_1 can still go to the strategy child
    assert summary.consumed_inputs(leads, [read, invalid, graded, child], [], False) == ['src_3', 'src_4']
    span = {'source_ref': 'src_5', 'artifact_ref': 'art_5', 'start': 0, 'end': 10}
    screening = {'kind': 'source_answer', 'answer_kind': 'screening', 'examined': [span]}
    assert summary.consumed_inputs(screening, [read], [], False) == []
    assert summary.consumed_inputs(screening, [read], [{**span, 'end': 12, 'representation': 'text'}], False) == ['src_5']
    assert summary.consumed_inputs(screening, [], [], True) == ['src_5']
    # a consumed source is not in the schema the child commission is validated against
    schema = task.strategy_schema(['src_2'])
    assert schema['properties']['prior_search_refs']['items'] == {'enum': ['src_2']}

