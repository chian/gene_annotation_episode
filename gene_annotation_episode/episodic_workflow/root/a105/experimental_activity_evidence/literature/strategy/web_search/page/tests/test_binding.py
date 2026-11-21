"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode with children (its child episode folders aside); no module of the
folder imports another episode folder; the episode's own forms and functions behave on real data. Nothing here is
faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildMessage, EpisodeBinding
from method_loop import FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceEvidenceExamination
CHILDREN = ('table', 'report', 'chunk')
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py', 'tests/grading_world.py', 'tests/test_grading.py',
         'tests/test_branch_page_model_run.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import (  # noqa: E402
    ASSAY_TYPES)

COMMIT_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['terms'],
                 'properties': {'terms': {'type': 'array'}}}


def own_files():
    return {path for path in FOLDER.rglob('*') if path.is_file() and '__pycache__' not in path.parts
            and path.relative_to(FOLDER).parts[0] not in CHILDREN}


def assignment():
    task = {'version': 'literature_local_task_v1', 'kind': 'verified_source_leads', 'evidence_axis': 'A105',
            'credit_unit': 1.0}
    return {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'text',
            'artifact_ref': 'art_1', 'question_context_refs': ['ctx_1'], 'prior_delivery_refs': [],
            'literature_task': task, 'proposed_annotation_ref': 'hyp_1',
            'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['src_1', 'art_1', 'ctx_1']}


def summary_of(requested=None, task=None):
    given = assignment()
    page = {name: given[name] for name in ('version', 'source_ref', 'representation', 'artifact_ref',
                                           'question_context_refs', 'prior_delivery_refs')}
    return {'page': page, 'task': task or given['literature_task'], 'task_key': 'A105:verified_source_leads',
            'proposed_annotation_ref': 'hyp_1', 'scope': given['scope'], 'requested': requested or {},
            'held_record_refs': ['art_1', 'ctx_1', 'src_1']}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {slot: EPISODE.binding_path + '/' + slot for slot in CHILDREN}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_children_and_its_child_folders():
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


def test_the_commission_form_admits_a_page_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    given = assignment()
    admitted = form.admit(given, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'evidence_location_unknown'})
    assert parent_input['page']['source_ref'] == 'src_1' and parent_input['task_key'] == 'A105:verified_source_leads'
    assert set(form.record_refs(admitted)) == {'src_1', 'art_1', 'ctx_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**given, 'extra': 1}, 'test')
    refused = {**admitted, 'literature_task': {**given['literature_task'], 'evidence_axis': 'A106'}}
    with pytest.raises(Exception, match='representation_error'):
        EPISODE.read_from_parent(refused, {'objective': 'evidence_location_unknown'})
    outside = {**admitted, 'literature_task': {'version': 'literature_local_task_v1', 'kind': 'source_answer',
                                               'answer_kind': 'assessment', 'evidence_axis': 'A105',
                                               'credit_unit': 1.0, 'source_refs': ['source_' + 'b' * 24]}}
    with pytest.raises(Exception, match='literature_task_outside_assigned_source'):
        EPISODE.read_from_parent(outside, {'objective': 'evidence_location_unknown'})
    duplicate = {**admitted, 'literature_task': {
        'version': 'literature_local_task_v1', 'kind': 'a105_experiments', 'evidence_axis': 'A105',
        'credit_unit': 1.0, 'experiments': [{'experiment_ref': 'experiment_' + 'c' * 24, 'assay_type': ASSAY_TYPES[0]},
                                            {'experiment_ref': 'experiment_' + 'c' * 24, 'assay_type': ASSAY_TYPES[0]}]}}
    with pytest.raises(Exception, match='literature_task_duplicate_experiment'):
        EPISODE.read_from_parent(duplicate, {'objective': 'evidence_location_unknown'})


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
    assert 'NotImplementedError' not in (FOLDER / 'credit.py').read_text()
    summary = {'task': {'kind': 'verified_source_leads', 'credit_unit': 2.0}, 'task_key': 'A105:verified_source_leads',
               'lead_source_refs': ['src_1', 'src_2'], 'proposed_annotation_ref': 'hyp_1'}
    assert credit_module.credit(summary, None) == 4.0
    screening = {'task': {'kind': 'source_answer', 'answer_kind': 'screening', 'credit_unit': 3.0,
                          'examined': [{'source_ref': 's', 'artifact_ref': 'a', 'start': 0, 'end': 10}]},
                 'proposed_annotation_ref': 'hyp_1', 'screening_covered': False}
    assert credit_module.credit(screening, None) == 0

