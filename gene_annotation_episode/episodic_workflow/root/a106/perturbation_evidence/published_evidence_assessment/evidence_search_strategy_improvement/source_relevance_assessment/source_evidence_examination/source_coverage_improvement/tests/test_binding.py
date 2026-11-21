"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set; no module imports another episode folder; the episode's own forms and functions
behave on real data. Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError

from gene_annotation_episode.episodic_workflow.episode_support.literature.storage import literature_population_route as route

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceCoverageImprovement
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py', 'tests/test_input_list.py',
         'tests/a106_world.py', 'tests/test_a106_grading.py', 'tests/test_model_run.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
NONE = {'literature_populations': [], 'literature_evidence_origins': {}}
COMMIT_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['terms'],
                 'properties': {'terms': {'type': 'array'}}}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts}


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
    own = PACKAGE
    for path in FOLDER.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == own or module.startswith(own + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module


def test_the_commission_form_admits_a_reading_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    page = {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'text', 'artifact_ref': 'art_1',
            'question_context_refs': [], 'prior_delivery_refs': []}
    window = {'source_ref': 'src_1', 'representation': 'text', 'offset': 0, 'limit': 10}
    task = {'kind': 'verified_source_leads', 'evidence_axis': 'A106', 'credit_unit': 1.0}
    assignment = {'version': 'reading_assignment_v1', 'page': page, 'selection': window,
                  'literature_task': task, 'proposed_annotation_ref': 'hyp_1',
                  'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['src_1', 'art_1']}
    admitted = form.admit(assignment, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'read'})
    assert parent_input['window'] == window and parent_input['page'] == page
    assert parent_input['task_key'] == 'A106:verified_source_leads'
    assert set(form.record_refs(admitted)) == {'src_1', 'art_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**assignment, 'extra': 1}, 'test')
    other = {**admitted, 'selection': {**window, 'source_ref': 'src_2'}}
    with pytest.raises(ValueError, match='literature_reading_source_mismatch'):
        EPISODE.read_from_parent(other, {})


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    summary = {'a106_findings': {'intervention_assessments': [], 'a106_subscores': []}}
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())
    assert result['credit'] == 2.5 and result['finding'] == summary['a106_findings']
    form.admit(result, 'test')


def test_the_credit_is_real_code_and_counts_nothing_without_a_validated_lead():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    assert 'NotImplementedError' not in (FOLDER / 'credit.py').read_text()
    summary = {'task': {'kind': 'verified_source_leads', 'credit_unit': 2.0}, 'task_key': 'A106:verified_source_leads',
               'source_leads': [], 'proposed_annotation_ref': 'hyp_1'}
    assert credit_module.credit(summary, None) == 0


def test_the_model_is_offered_the_access_tools_the_graders_the_judgment_and_the_reasoning():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered(NONE, None)
    assert 'execution_estimate' not in names and names[-2:] == ['literature_a106_score_judgment', 'reason'] and len(names) == 17
    opened = task.offered(NONE, 'literature_intervention_grading_populate')
    assert opened[-3:] == ['literature_intervention_grading_populate', 'literature_a106_score_judgment', 'reason']
    assert set(names) <= set(EPISODE.tools)
    for leads in (False, True):
        schema = task.selection_schema(names, COMMIT_SCHEMA, leads, NONE)
        assert len(schema['properties']['selection']['anyOf']) == len(names)
    reason = [entry for entry in task.catalog(names, COMMIT_SCHEMA, True, NONE) if entry['name'] == 'reason'][0]
    assert 'source_lead' in reason['input_schema']['properties']
    assert 'source_lead' not in task.reason_schema(COMMIT_SCHEMA, False)['properties']
    assert 'execution_estimate' in task.offered({**NONE, 'tool_registry': {'native_statistics': object()}}, None)
    assert task.empty_commit({'terms': []}, COMMIT_SCHEMA) and not task.empty_commit({'terms': [{}]}, COMMIT_SCHEMA)


def test_the_population_operations_of_the_old_catalogue_are_tools_and_optional_ones_follow_the_settings():
    task = importlib.import_module(PACKAGE + '.task')
    always = set(route.population_entries(NONE))
    assert len(always) == 25 and always <= set(EPISODE.tools) and set(route.POPULATION_NAMES) <= set(EPISODE.tools)
    assert 'literature_a106_finalize' in always and 'literature_intervention_grading_populate' in always
    assert 'literature_gel_populate' not in always and 'literature_channel_populate' not in always
    settings = {'literature_populations': ['channel', 'gel'], 'literature_evidence_origins': {'gel': 'reported_source'}}
    assert {'literature_channel_populate', 'literature_gel_populate'} <= set(route.population_entries(settings))
    with pytest.raises(ValueError):
        route.population_entries({'literature_populations': ['gel'], 'literature_evidence_origins': {}})
    offered = task.offered(settings, 'literature_gel_populate')
    entries = task.catalog(offered, COMMIT_SCHEMA, False, settings)
    assert [entry['name'] for entry in entries] == offered
    arguments = {'sheet_ref': 'sheet_in', 'nested': [{'source_ref': 'src_a'}, {'metadata_source_ref': 'src_b'}]}
    assert route.population_sources('literature.a106.finalize', arguments) == {'sheet_in', 'src_a', 'src_b'}
    assert route.population_sources('literature.rate.populate', arguments) == {'src_a', 'src_b'}


def test_the_selectable_answers_are_counts_and_references_and_are_admitted():
    form = EPISODE.return_form
    summary = {'a106_findings': {'intervention_assessments': [], 'a106_subscores': []},
               'no_applicable_evidence': [{'start': 0, 'end': 4}], 'screening_answers': [],
               'source_lead_dispositions': [{'source_ref': 'src_1', 'disposition': 'relevant'},
                                            {'source_ref': 'src_2', 'disposition': 'not_relevant'}]}
    both = ('literature_screening_answers', 'literature_source_lead_dispositions')
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0}, both)
    assert result['literature_screening_answers'] == {'examined_span_count': 1, 'commissioned_spans_covered': False}
    assert result['literature_source_lead_dispositions'] == {'relevant_lead_count': 1, 'lead_source_refs': ['src_1']}
    form.select(both).admit(result, 'return')
    assert form.select(both).record_refs(result) == ('src_1',)
