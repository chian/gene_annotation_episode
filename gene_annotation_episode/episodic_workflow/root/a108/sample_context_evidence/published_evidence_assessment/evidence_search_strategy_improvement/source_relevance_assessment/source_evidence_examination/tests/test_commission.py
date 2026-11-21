"""The page on the real runner and a real Store: its first decision is the automatic ``assess_content`` unit (no model
call), its candidates and information needs come from the held paper, and each commission it makes for a leaf is admitted by
that leaf's own forms and carries one candidate. What a leaf returns is read by ``read_from_child`` as controlled data only.
Jev is not called here (the assessment unit needs the real key; ``test_model_run.py`` runs it)."""
import asyncio
import importlib

from episode_runtime import BindingRegistry, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config

from .a108_page import CONTINUATION, EPISODE, PATH, SERVICES, bindings, held_world, leads_task, page_assignment

BASE = EPISODE.__module__.rsplit('.', 1)[0]
TO_CHILD = importlib.import_module(BASE + '.messages.msg_to_child')
FROM_CHILD = importlib.import_module(BASE + '.messages.read_from_child')
TABLE = {'candidate_id': 'source_table:abc', 'candidate_type': 'source_table', 'index': 0, 'start': 10, 'end': 60,
         'parser_hint': 'markdown'}


def collaborators(directory, world, name):
    return {'store': world['store'], 'model_provider': ModelProvider(load_config(), directory / name, directory),
            'continuation': CONTINUATION, 'services': SERVICES}


def test_the_first_decision_is_the_automatic_assessment_and_each_commission_is_admitted_by_its_leaf(tmp_path):
    world = held_world(tmp_path)
    entry = {'assignment': page_assignment(world, leads_task()), 'message': {'objective': 'examine'},
             'selection': []}
    run = link(BindingRegistry(bindings()), PATH, entry, run_id='a108-page',
               journal=RunJournal(tmp_path / 'parent.sqlite3'), collaborators=collaborators(tmp_path, world, 'calls'))
    decision = asyncio.run(run.next_decision())
    assert isinstance(decision, ToolCall) and decision.name == 'assess_content'
    view = run.view
    summary = EPISODE.internal_summary(view)
    assert EPISODE.credit(summary, view.records) == 0
    assert EPISODE.offered_actions(summary, None) == ['assess_content']
    assert summary['finding'] == {'grading_sheets': [], 'aggregation_cells': [], 'assessment_refs': [],
                                  'observation_refs': []}
    assert summary['content_assessment_ref'] is None and summary['planner_context'] is None
    assert [item['candidate_type'] for item in summary['content_candidates']] == ['prose_chunk']
    needs = summary['information_needs']
    assert {item['table'] for item in needs} == {'physiology', 'environment', 'availability', 'localization'}
    assert {item['kind'] for item in needs} == {'observation', 'subject_identity'}
    assert decision.arguments['information_needs'] == needs

    summary = {**summary, 'content_candidates': [*summary['content_candidates'], TABLE]}
    chunk = summary['content_candidates'][0]
    slots = {'passage_evidence_extraction': {'candidate_id': chunk['candidate_id']},
             'table_evidence_extraction': {'candidate_id': TABLE['candidate_id']},
             'source_coverage_improvement': {}}
    for slot, arguments in slots.items():
        message = TO_CHILD.msg_to_child(slot, arguments, summary)
        assert message.objective == 'find_applicable_evidence'
        assert message.selection[0] == 'literature_source_lead_dispositions'
        leaf = importlib.import_module(BASE + '.' + slot + '.episode')
        leaf_class = next(value for value in vars(leaf).values()
                          if isinstance(value, type) and value.__module__ == leaf.__name__)
        admitted = leaf_class.assignment_form.admit(message.assignment, 'commission')
        # the passage leaf takes its one chunk and the coverage leaf its prose windows as spans; the table leaf one region
        window = admitted['selection'] if slot == 'table_evidence_extraction' else admitted['selection']['spans'][0]
        assert window['source_ref'] == world['paper']['id']
        if slot == 'passage_evidence_extraction':
            assert (window['offset'], window['limit']) == (chunk['start'], chunk['end'] - chunk['start'])
        elif slot == 'table_evidence_extraction':
            assert (window['offset'], window['limit']) == (TABLE['start'], TABLE['end'] - TABLE['start'])
        assert ('literature_a108_grading_cells' in message.selection) == (slot != 'passage_evidence_extraction')
    world['store'].close()


def test_what_a_leaf_returns_is_read_as_controlled_data_only():
    summary = {'literature_assignment': {'requested_a108_grading_components': ['evidence_amount']}}
    finding = {'grading_sheets': [], 'aggregation_cells': [], 'assessment_refs': [], 'observation_refs': []}
    result = {'credit': 1.0, 'finding': finding,
              'literature_source_lead_dispositions': {'relevant_lead_count': 1, 'lead_source_refs': ['source_1']},
              'literature_a108_grading_cells': ['cell_1']}
    report = FROM_CHILD.read_from_child('source_coverage_improvement', result, summary, None)
    assert report == {'slot': 'source_coverage_improvement', 'credit': 1.0, 'finding': finding,
                      'leads': {'relevant_lead_count': 1, 'lead_source_refs': ['source_1']},
                      'literature_a108_grading_cells': ['cell_1']}
