"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode with a child; no module of the folder imports another episode folder;
the episode's own forms, commission, credit, controller and tool offer behave on real data. Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildMessage, EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController, CompletionYieldController

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').PublishedEvidenceAssessment
CHILDREN = ('evidence_search_strategy_improvement',)
BINDING_PATH = 'structural_homology_evidence/published_evidence_assessment'
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
SCREENING_TASK = {'version': 'literature_local_task_v1', 'evidence_axis': 'A105', 'kind': 'source_answer',
                  'answer_kind': 'screening', 'credit_unit': 2.0,
                  'examined': [{'source_ref': 'src_1', 'artifact_ref': 'art_1', 'start': 0, 'end': 100}]}
LEADS_TASK = {'version': 'literature_local_task_v1', 'evidence_axis': 'A105', 'kind': 'verified_source_leads',
              'credit_unit': 1.0}
ASSIGNMENT = {'version': 'literature_assignment_v1', 'question_context_refs': ['ctx_1'],
              'source_refs': ['src_1', 'src_2'], 'literature_task': SCREENING_TASK,
              'proposed_annotation_ref': 'hyp_1', 'scope': {'subject_refs': ['sub_1']},
              'received_record_refs': ['hyp_1']}
STRATEGY = {'question_context_refs': ['ctx_1'], 'prior_search_refs': ['src_1']}


def own_files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts and path.relative_to(FOLDER).parts[0] not in CHILDREN}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH == BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {'literature_strategy': BINDING_PATH + '/evidence_search_strategy_improvement'}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_a_child():
    assert own_files() == FILES
    for child in CHILDREN:
        assert (FOLDER / child / 'episode.py').is_file()


def test_no_module_of_the_folder_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        if path.relative_to(FOLDER).parts[0] in CHILDREN:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module


def test_the_commission_form_admits_a_literature_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'strategy'})
    assert parent_input['source_refs'] == ['src_1', 'src_2']
    assert parent_input['task_key'] == 'A105:source_answer:screening'
    assert set(form.record_refs(admitted)) >= {'src_1', 'src_2', 'ctx_1', 'hyp_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    with pytest.raises(ValueError, match='literature_original_task_invalid'):
        EPISODE.read_from_parent({**admitted, 'literature_task': {**SCREENING_TASK, 'kind': 'other'}}, {})
    with pytest.raises(ValueError, match='literature_finite_task_credit_unit_required'):
        EPISODE.read_from_parent({**admitted, 'literature_task': {**LEADS_TASK, 'credit_unit': 0}}, {})


def test_the_return_declares_credit_and_finding_as_required_and_the_fact_sources_as_selectable():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    for name in ('literature_screening_answers', 'literature_source_lead_dispositions'):
        assert not form.fields[name].required


def test_the_return_carries_credit_the_finding_and_each_selectable_field_as_counts_and_references():
    span = {'source_ref': 'src_1', 'artifact_ref': 'art_1', 'start': 0, 'end': 100, 'representation': 'text'}
    summary = {'structure_sheets': [], 'no_applicable_evidence': [span],
               'screening_answers': [{'proposed_annotation_ref': 'hyp_1', 'disposition': 'no_applicable_evidence',
                                      'examined': [span], 'annotation_support': 'not_assessed'}],
               'source_lead_dispositions': [{'source_ref': 'src_1', 'disposition': 'relevant',
                                             'relevance_rationale': 'model text that never leaves the episode'},
                                            {'source_ref': 'src_2', 'disposition': 'not_relevant'}]}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}
    names = ('literature_screening_answers', 'literature_source_lead_dispositions')
    result = EPISODE.final_to_parent(summary, completion, names)
    assert result == {'credit': 2.5, 'finding': {'structure_sheets': []},
                      'literature_screening_answers': {'examined_span_count': 1, 'commissioned_spans_covered': True},
                      'literature_source_lead_dispositions': {'relevant_lead_count': 1, 'lead_source_refs': ['src_1']}}
    form = EPISODE.return_form.select(names)
    form.admit(result, 'return')
    assert form.record_refs(form.admit(result, 'return')) == ('src_1',)
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**result, 'literature_source_lead_dispositions': {
            **result['literature_source_lead_dispositions'], 'relevance_rationale': 'text'}}, 'return')
    with pytest.raises(FormError, match='must_be_integer'):
        form.admit({**result, 'literature_screening_answers': {'examined_span_count': '1',
                                                               'commissioned_spans_covered': True}}, 'return')
    uncovered = EPISODE.final_to_parent({**summary, 'screening_answers': []}, completion, names)
    assert uncovered['literature_screening_answers']['commissioned_spans_covered'] is False
    plain = EPISODE.final_to_parent(summary, completion, ())
    assert set(plain) == {'credit', 'finding'}
    EPISODE.return_form.select(()).admit(plain, 'return')


def commission_summary(task):
    parent_input = EPISODE.read_from_parent(EPISODE.assignment_form.admit(ASSIGNMENT, 'test'), {})
    return {'literature_assignment': {key: parent_input[key] for key in
                                      ('version', 'question_context_refs', 'source_refs')}
            | {'literature_task': task, 'proposed_annotation_ref': 'hyp_1'},
            'task': task, 'proposed_annotation_ref': 'hyp_1', 'scope': parent_input['scope'],
            'received_record_refs': parent_input['received_record_refs'],
            'literature_source_custody': [{'source_ref': 'src_1', 'artifact_ref': 'art_1',
                                           'passed_record_refs': ['src_1', 'art_1', 'src_0']}]}


def test_the_commission_names_the_strategy_the_task_and_every_record_and_selects_the_answers_of_the_task():
    summary = commission_summary(SCREENING_TASK)
    message = EPISODE.msg_to_child('literature_strategy', {'strategy': STRATEGY}, summary)
    assert isinstance(message, ChildMessage)
    assert message.message == {} and message.objective == 'improve_search_strategy'
    assert message.assignment['prior_search_refs'] == ['src_1']
    assert message.assignment['literature_task'] == SCREENING_TASK
    assert message.assignment['version'] == 'strategy_assignment_v1'
    assert message.assignment['received_record_refs'] == ['ctx_1', 'hyp_1', 'src_1', 'art_1', 'src_0']
    assert tuple(message.selection) == ('literature_screening_answers',)
    leads = EPISODE.msg_to_child('literature_strategy', {'strategy': STRATEGY}, {**summary, 'task': LEADS_TASK})
    assert tuple(leads.selection) == ('literature_source_lead_dispositions',)
    with pytest.raises(KeyError):
        EPISODE.msg_to_child('literature_other', {'strategy': STRATEGY}, summary)
    with pytest.raises(KeyError):      # a source this episode holds no custody entry for: the commission fails
        EPISODE.msg_to_child('literature_strategy', {'strategy': {**STRATEGY, 'prior_search_refs': ['src_7']}}, summary)


def test_the_report_of_a_child_keeps_its_credit_structure_sheets_and_the_relevant_lead_sources():
    result = {'credit': 1.0, 'finding': {'structure_sheets': []},
              'literature_source_lead_dispositions': {'relevant_lead_count': 1, 'lead_source_refs': ['src_1']},
              'literature_screening_answers': {'examined_span_count': 2, 'commissioned_spans_covered': False}}
    report = EPISODE.read_from_child('literature_strategy', result, {}, None)
    assert report == {'slot': 'literature_strategy', 'credit': 1.0, 'structure_sheets': [],
                      'lead_source_refs': ['src_1'],
                      'screening': {'examined_span_count': 2, 'commissioned_spans_covered': False}}
    with pytest.raises(KeyError):
        EPISODE.read_from_child('literature_other', result, {}, None)


def test_the_screening_credit_is_the_unit_when_the_own_declarations_cover_every_requested_span():
    summary = {'task': SCREENING_TASK, 'task_key': 'A105:source_answer:screening', 'proposed_annotation_ref': 'hyp_1',
               'no_applicable_evidence': [{'source_ref': 'src_1', 'artifact_ref': 'art_1', 'start': 0, 'end': 60,
                                           'representation': 'text'}]}
    assert EPISODE.credit(summary, None) == 0
    summary['no_applicable_evidence'].append({'source_ref': 'src_1', 'artifact_ref': 'art_1', 'start': 50,
                                              'end': 100, 'representation': 'text'})
    assert EPISODE.credit(summary, None) == 2.0
    credit_source = (FOLDER / 'credit.py').read_text()
    assert 'min(' not in credit_source and 'max(' not in credit_source.replace('covered = max(covered, end)', '')
    with pytest.raises(ValueError, match='literature_task_kind_not_carried'):
        EPISODE.credit({'task': {**LEADS_TASK, 'kind': 'a105_experiments'}, 'task_key': 'A105:a105_experiments'}, None)


def test_the_controller_follows_the_commissioned_task_kind():
    settings = {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}
    leads = EPISODE.yield_controller(0, settings, {'task': LEADS_TASK})
    screening = EPISODE.yield_controller(0, settings, {'task': SCREENING_TASK})
    assert isinstance(leads, AccumulationYieldController)
    assert isinstance(screening, CompletionYieldController)


def test_the_acquisition_and_access_tools_and_the_strategy_child_are_in_the_selection_schema_and_its_transport():
    task = importlib.import_module(PACKAGE + '.task')
    summary = {'task': LEADS_TASK, 'reasoning_schema': {'type': 'object', 'properties': {'terms': {'type': 'array'}},
                                                         'required': ['terms'], 'additionalProperties': False}}
    names = task.offered({})
    assert 'execution_estimate' not in names and names[-2:] == ['structure_populate', 'reason']
    for name in ('public_literature_search', 'public_literature_read', 'public_ncbi_search', 'public_pmc_asset',
                 'public_sabiork_search', 'source_read', 'state_query'):
        assert name in names
    assert set(names) <= set(EPISODE.tools)
    schema = task.selection_schema(names, summary)
    assert len(schema['properties']['selection']['anyOf']) == len(names) + 1
    assert task.generation_schema(schema)
    assert task.INPUT_SCHEMAS['public.ncbi.search']['properties']['database'] == {'enum': ['pubmed']}
