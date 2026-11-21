"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set and its child folder; no module of the episode imports another episode folder; the
episode's own forms and functions behave on real data; its commission is admitted by the real form of the page
child (read by name at test time, never imported by the episode). Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildCall, EpisodeBinding
from method_loop import FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceRelevanceAssessment
OWN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
             'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
             'tests/__init__.py', 'tests/test_binding.py'}
CHILDREN = ('source_evidence_examination',)
ROOT = 'gene_annotation_episode.episodic_workflow.root'
NONE = {'literature_populations': [], 'literature_evidence_origins': {}}
EMPTY = {'intervention_assessments': [], 'a106_subscores': []}
COMMIT_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['terms'],
                 'properties': {'terms': {'type': 'array'}}}
SRC = 'source_' + 'a' * 24
ART = 'artifact_' + 'c' * 24
CTX = 'record_' + 'd' * 24
TASK = {'kind': 'verified_source_leads', 'evidence_axis': 'A106', 'credit_unit': 1.0}
ASSIGNMENT = {'version': 'search_assignment_v1', 'question_context_refs': ['ctx_1'], 'search_result_refs': [SRC],
              'literature_task': TASK, 'proposed_annotation_ref': 'hyp_1', 'scope': {'subject_refs': ['sub_1']},
              'received_record_refs': [SRC, 'hyp_1']}
PAGE = {'source_ref': SRC, 'representation': 'original', 'artifact_ref': ART, 'question_context_refs': [CTX],
        'prior_delivery_refs': []}


def child_module(name, module):
    return importlib.import_module(PACKAGE + '.' + name + '.' + module)


def own_files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts
            and path.relative_to(FOLDER).parts[0] not in CHILDREN}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {'literature_page': EPISODE.binding_path + '/source_evidence_examination'}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_children_and_its_child_folder():
    assert own_files() == OWN_FILES
    assert {path.name for path in FOLDER.iterdir() if path.is_dir() and path.name != '__pycache__'} \
        == {'messages', 'tests', *CHILDREN}


def test_no_module_of_the_episode_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        relative = path.relative_to(FOLDER)
        if relative.parts[0] in CHILDREN or relative.parts[0] == 'tests':
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT), str(relative) + ' imports ' + module


def test_the_commission_form_admits_a_search_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'search'})
    assert parent_input['search'] == {'version': 'search_assignment_v1', 'question_context_refs': ['ctx_1'],
                                      'search_result_refs': [SRC]}
    assert parent_input['task_key'] == 'A106:verified_source_leads'
    assert set(form.record_refs(admitted)) == {'ctx_1', SRC, 'hyp_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    with pytest.raises(ValueError, match='literature_finite_task_credit_unit_required'):
        EPISODE.read_from_parent({**admitted, 'literature_task': {**TASK, 'credit_unit': 0}}, {})
    with pytest.raises(ValueError, match='literature_original_task_invalid'):
        EPISODE.read_from_parent({**admitted, 'literature_task': {**TASK, 'evidence_axis': 'A105'}}, {})


def test_the_controller_is_built_from_the_parent_input_alone():
    parent_input = EPISODE.read_from_parent(ASSIGNMENT, {})
    settings = {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}
    controller = EPISODE.yield_controller(0, settings, parent_input)
    assert type(controller).__name__ == 'AccumulationYieldController'
    answer = {**ASSIGNMENT, 'literature_task': {'kind': 'source_answer', 'answer_kind': 'screening',
                                                'evidence_axis': 'A106', 'credit_unit': 2.0,
                                                'examined': [{'source_ref': SRC, 'artifact_ref': 'art_1',
                                                              'start': 0, 'end': 5}]}}
    controller = EPISODE.yield_controller(0, settings, EPISODE.read_from_parent(answer, {}))
    assert type(controller).__name__ == 'CompletionYieldController'


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    assert not form.fields['literature_source_lead_dispositions'].required
    assert not form.fields['literature_screening_answers'].required
    summary = {'a106_findings': EMPTY, 'no_applicable_evidence': [], 'screening_answers': [],
               'source_lead_dispositions': [{'source_ref': SRC, 'disposition': 'relevant'}]}
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())
    assert result == {'credit': 2.5, 'finding': EMPTY}
    form.admit(result, 'test')
    both = ('literature_screening_answers', 'literature_source_lead_dispositions')
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0}, both)
    assert result['literature_source_lead_dispositions'] == {'relevant_lead_count': 1, 'lead_source_refs': [SRC]}
    assert result['literature_screening_answers'] == {'examined_span_count': 0, 'commissioned_spans_covered': False}
    form.select(both).admit(result, 'return')


def test_the_credit_is_real_code_and_counts_nothing_without_a_validated_lead():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    assert 'NotImplementedError' not in (FOLDER / 'credit.py').read_text()
    summary = {'task': {'kind': 'verified_source_leads', 'credit_unit': 2.0}, 'task_key': 'A106:verified_source_leads',
               'source_leads': [], 'proposed_annotation_ref': 'hyp_1'}
    assert credit_module.credit(summary, None) == 0


def test_the_model_is_offered_the_access_and_acquisition_tools_the_reasoning_the_report_and_the_page_examination():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered(NONE, None)
    assert 'execution_estimate' not in names and names[-2:] == ['literature_a106_score_judgment', 'reason'] and len(names) == 39
    assert set(names) <= set(EPISODE.tools) and set(task.ACQUISITION_NAMES) <= set(names)
    assert len(task.ACQUISITION_NAMES) == 22 and 'public_literature_search' in names
    for leads in (False, True):
        schema = task.selection_schema(names, COMMIT_SCHEMA, leads, NONE, [SRC])
        assert len(schema['properties']['selection']['anyOf']) == len(names) + 1
        task.generation_schema(schema)
    assert [entry['slot'] for entry in task.commissions([SRC])] == list(EPISODE.child_slots)
    assert task.commissions([]) == []      # an empty input list offers no examination
    assert task.page_schema([SRC])['properties']['source_ref'] == {'enum': [SRC]}
    shown = {entry['name']: entry for entry in task.catalog(names, COMMIT_SCHEMA, True, NONE)}
    assert 'source_lead' in shown['reason']['input_schema']['properties']
    assert 'source_lead' not in task.reason_schema(COMMIT_SCHEMA, False)['properties']
    assert shown['public_ncbi_search']['input_schema']['properties']['database'] == {'enum': ['pubmed']}
    assert shown['public_ncbi_entrez']['description'] and shown['public_ncbi_geo']['description']
    assert 'execution_estimate' in task.offered({**NONE, 'tool_registry': {'native_statistics': object()}}, None)
    assert task.empty_commit({'terms': []}, COMMIT_SCHEMA) and not task.empty_commit({'terms': [{}]}, COMMIT_SCHEMA)


def test_the_commission_is_admitted_by_the_form_of_the_page_child_and_selects_what_the_task_counts():
    task = importlib.import_module(PACKAGE + '.task')
    child_task = {'version': 'literature_local_task_v1', 'evidence_axis': 'A106', 'kind': 'verified_source_leads'}
    arguments = {'page': PAGE, 'literature_task': child_task}
    task.validate_selection({'selection': {'kind': 'child', 'slot': 'literature_page', 'arguments': arguments}},
                            task.selection_schema(task.offered(NONE, None), COMMIT_SCHEMA, True, NONE, [SRC]))
    with pytest.raises(Exception):      # a consumed source is no longer offered: the schema admits no page for it
        task.validate_selection({'selection': {'kind': 'child', 'slot': 'literature_page', 'arguments': arguments}},
                                task.selection_schema(task.offered(NONE, None), COMMIT_SCHEMA, True, NONE,
                                                      ['source_' + 'b' * 24]))
    parent_input = EPISODE.read_from_parent(ASSIGNMENT, {})
    summary = {'task': parent_input['task'], 'proposed_annotation_ref': parent_input['proposed_annotation_ref'],
               'scope': parent_input['scope'], 'source_custody': {SRC: [SRC, ART]}}
    message = EPISODE.msg_to_child('literature_page', ChildCall('literature_page', arguments).arguments, summary)
    child_form = child_module('source_evidence_examination', 'messages.read_from_parent').ASSIGNMENT_FORM
    admitted = child_form.admit(message.assignment, 'commission')
    assert set(child_form.record_refs(admitted)) == {CTX, SRC, ART, 'hyp_1'}
    assert admitted['literature_task']['credit_unit'] == 1.0
    child_input = child_module('source_evidence_examination', 'messages.read_from_parent').read_from_parent(
        admitted, {})
    assert child_input['page']['source_ref'] == SRC
    child_return = child_module('source_evidence_examination', 'messages.final_to_parent').RETURN_FORM
    selected = child_return.select(message.selection)
    assert set(message.selection) == {'literature_source_lead_dispositions'}
    assert 'credit' in selected.fields and 'finding' in selected.fields
    with pytest.raises(KeyError):      # a source this episode does not hold is a wrong commission: it fails
        EPISODE.msg_to_child('literature_page', arguments, {**summary, 'source_custody': {}})
    returned = {'credit': 1.0, 'finding': EMPTY,
                'literature_source_lead_dispositions': {'relevant_lead_count': 1, 'lead_source_refs': [SRC]}}
    selected.admit(returned, 'return')
    read = EPISODE.read_from_child('literature_page', returned, summary, None)
    assert read == {'slot': 'literature_page', 'credit': 1.0, 'finding': EMPTY, 'lead_source_refs': [SRC]}
