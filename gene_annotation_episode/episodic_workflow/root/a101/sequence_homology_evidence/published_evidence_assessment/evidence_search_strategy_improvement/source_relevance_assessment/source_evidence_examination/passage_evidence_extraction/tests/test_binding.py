"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set; no module imports another episode folder; the episode's own forms and functions
behave on real data; and the episode, linked with the real runner, journal and Store, offers the controlled
``report`` at its first decision, runs a report unit and returns the controlled finding. Nothing here is faked: the
model is not asked (the run's caller names the unit through ``EpisodeRun.run_unit``)."""
import ast
import asyncio
import importlib
import json
from pathlib import Path

import pytest

from episode_runtime import BindingRegistry, EpisodeBinding, ModelRequest, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from method_loop import FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').PassageEvidenceExtraction
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'


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
    assignment = {'version': 'reading_assignment_v1', 'page': page, 'selection': {'spans': [window]},
                  'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['src_1', 'art_1']}
    admitted = form.admit(assignment, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'read'})
    assert parent_input['spans'] == [window] and parent_input['page'] == page
    assert set(form.record_refs(admitted)) == {'src_1', 'art_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**assignment, 'extra': 1}, 'test')
    other = {**admitted, 'selection': {'spans': [{**window, 'source_ref': 'src_2'}]}}
    with pytest.raises(ValueError, match='literature_reading_source_mismatch'):
        EPISODE.read_from_parent(other, {})


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    summary = {'report': None, 'report_source_held': {},
               'literature_assignment': {'page': {'source_ref': 's', 'representation': 'text'},
                                         'selection': {'spans': [{'source_ref': 's', 'representation': 'text'}]}}}
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())
    assert result['credit'] == 2.5 and result['finding']['written'] is False
    form.admit(result, 'test')


def test_the_credit_is_the_native_correspondence_projector_and_never_a_stub():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    assert credit_module.A101SequenceCredit().as_record()['kind'] == 'a101_native_sequence_correspondence'
    source = (FOLDER / 'credit.py').read_text()
    assert 'NotImplementedError' not in source


def test_the_model_is_offered_the_access_tools_and_the_report_and_every_tool_is_declared():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered({'tool_registry': {}})
    assert 'execution_estimate' not in names and names[-1] == 'report' and len(names) == 15
    assert set(names) <= set(EPISODE.tools)
    schema = task.selection_schema(names)
    assert len(schema['properties']['selection']['anyOf']) == len(names)
    assert 'execution_estimate' in task.offered({'tool_registry': {'native_statistics': object()}})


PATH = EPISODE.binding_path
SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}, 'tool_registry': {}}
TEXT = 'The homolog GeneY (68% identity over the full length) was shown to hydrolyse ATP in vitro.'


def world(directory):
    """A real Store with a protein problem and one held paper source; the reading assignment passes the source and
    its artifact."""
    store = Store(directory / 'store')
    store.create_problem(raw_sequence='MKTAYIAKQRQISFVKSHFSRQ', molecule='protein')
    scope = {'subject_refs': list(store.problem()['subject_refs'])}
    artifact = store.artifact(TEXT)
    paper = store.put('source', {'provider': 'synthetic_literature_fixture', 'accession': None, 'uri': None,
                                 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None,
                                 'retrieved_at': None}, origin='caller')
    page = {'version': 'page_assignment_v1', 'source_ref': paper['id'], 'representation': 'text',
            'artifact_ref': artifact, 'question_context_refs': [], 'prior_delivery_refs': []}
    window = {'source_ref': paper['id'], 'representation': 'text', 'offset': 0, 'limit': len(TEXT)}
    assignment = {'version': 'reading_assignment_v1', 'page': page, 'selection': {'spans': [window]},
                  'scope': scope, 'received_record_refs': [*scope['subject_refs'], paper['id'], artifact]}
    return store, {'assignment': assignment, 'message': {'objective': 'read'}, 'selection': []}, paper['id']


def linked(directory, store, entry):
    collaborators = {'store': store,
                     'model_provider': ModelProvider(load_config(), directory / 'model_calls', directory),
                     'continuation': {PATH: SETTINGS}, 'services': {}}
    return link(BindingRegistry([EPISODE()]), PATH, entry, run_id='a101-passage-report',
                journal=RunJournal(directory / 'journal.sqlite3'), collaborators=collaborators)


def test_the_linked_episode_offers_the_controlled_report_runs_it_and_returns_the_controlled_finding(tmp_path):
    task = importlib.import_module(PACKAGE + '.task')
    store, entry, paper = world(tmp_path)
    run = linked(tmp_path, store, entry)

    async def steps():
        decision = await run.next_decision()
        initial = run.view
        report = {'entries': [{'source_ref': paper, 'claim_kind': 'reported_homolog_function',
                               'subject_relation': 'aligned_homolog', 'measured': True, 'offset': 0,
                               'limit': len(TEXT), 'function': 'ATPase'}]}
        outcome = await run.run_unit(ToolCall('report', report))
        return decision, initial, outcome, run.view
    decision, initial, outcome, view = asyncio.run(steps())

    assert isinstance(decision, ModelRequest) and decision.role == 'REASONING'
    tools = {row['name']: row for row in decision.context['tools']}
    assert tools['report']['input_schema'] == task.REPORT_SCHEMA
    item = task.REPORT_SCHEMA['properties']['entries']['items']
    assert set(item['properties']) == {'source_ref', 'claim_kind', 'subject_relation', 'measured', 'function',
                                       'offset', 'limit'}
    assert not any(word in json.dumps(task.REPORT_SCHEMA) for word in ('interpretation', 'qualification',
                                                                      'statement'))
    assert task.REPORT_GUIDANCE in decision.instructions
    assert initial.units_consumed == 0
    summary = EPISODE.internal_summary(initial)
    assert summary['report'] is None and EPISODE.credit(summary, initial.records) == 0

    assert outcome['tool'] == 'report' and outcome['outcome']['report']['entries'][0]['source_ref'] == paper
    summary = EPISODE.internal_summary(view)
    assert summary['report_source_held'] == {paper: True}
    completion = {'ended_by': 'yield_stop', 'units_consumed': view.units_consumed, 'credit': 0.0}
    result = EPISODE.final_to_parent(summary, completion, ())
    form = EPISODE.return_form.select(())
    admitted = form.admit(result, 'return')
    assert admitted == result
    finding = admitted['finding']
    assert finding['written'] is True and finding['entry_count'] == 1
    assert finding['claim_count_reported_homolog_function'] == 1 and finding['unresolved_correspondence_count'] == 0
    assert finding['entries'] == [{'source_refs': [paper], 'claim_kind': 'reported_homolog_function',
                                   'subject_relation': 'aligned_homolog', 'measured': True, 'offset': 0,
                                   'limit': len(TEXT), 'function': 'ATPase'}]
    assert form.record_refs(admitted) == (paper,)
    store.close()
