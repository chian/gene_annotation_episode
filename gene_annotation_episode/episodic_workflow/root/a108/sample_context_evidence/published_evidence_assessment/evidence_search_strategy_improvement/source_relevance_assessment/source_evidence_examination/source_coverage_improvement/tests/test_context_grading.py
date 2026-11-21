"""The A108 extraction of this episode, run through the real runner on a real Store.

The run is linked with the public API (``link``) and stepped with ``next_decision`` and ``run_unit``: the Episode is
entered as ``run()`` enters it (its yield controller built from ``credit`` of the initial summary), its first decision is the
episode's own ``decide`` (the model is not asked), and the ``extract`` action then runs as a real journaled tool unit on real
held records: the typed commit, its grading with the subscoring sheet saved in the same unit, and the source lead. The saved
sheet, the features code reads from it, the credit and the return admitted by ``RETURN_FORM`` are checked. Nothing is
faked."""
import asyncio
import importlib
import json

from method_loop import UNBOUNDED
from episode_runtime import BindingRegistry, ModelRequest, RunJournal, ToolCall, link
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    GRADING_FEATURES, GRADING_INSTRUCTIONS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_grading_storage import (
    CELLS)
from gene_annotation_episode.model_provider import ModelProvider, load_config

from .a108_world import (PAPER, SERVICES, SETTINGS, extraction, held_world, reading_assignment, saved, source_lead,
                         window)

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceCoverageImprovement
PATH = EPISODE.binding_path


def windows(world):
    """The paper cut in two at its Results sentence: the windows to read in document order."""
    cut = PAPER.encode().index(b'Results.')
    return {'spans': [window(world, 0, cut), window(world, cut)]}


def linked(directory, world):
    collaborators = {'store': world['store'], 'model_provider': ModelProvider(load_config(), directory / 'model_calls',
                                                                             directory),
                     'continuation': {PATH: SETTINGS}, 'services': SERVICES}
    entry = {'assignment': reading_assignment(world, windows(world)), 'message': {'objective': 'extract'},
             'selection': []}
    return link(BindingRegistry([EPISODE()]), PATH, entry, run_id='a108-extract', journal=RunJournal(
        directory / 'journal.sqlite3'), collaborators=collaborators)


def envelope(world, arguments):
    return {'arguments': arguments, 'scope': world['scope'], 'page_source_ref': world['paper']['id'],
            'proposed_annotation_ref': world['claim']['id'],
            'assignment': reading_assignment(world, windows(world))}


def test_the_first_decision_shows_the_first_window_and_offers_only_the_extraction(tmp_path):
    world = held_world(tmp_path)
    run = linked(tmp_path, world)
    request = asyncio.run(run.next_decision())
    view = run.view
    assert view.controller_state is not None and view.units_consumed == 0
    summary = EPISODE.internal_summary(view)
    assert EPISODE.credit(summary, view.records) == 0
    assert summary['finding'] == {'grading_sheets': [], 'aggregation_cells': [], 'assessment_refs': [],
                                  'observation_refs': []}
    cut = PAPER.encode().index(b'Results.')
    assert summary['input_list'] == [[0, cut], [cut, len(PAPER.encode())]] and summary['consumed_inputs'] == []
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    shown = request.context['window']
    assert (shown['start'], shown['end']) == (0, cut)
    assert ''.join(segment['text'] for segment in shown['segments']).startswith('Methods.')
    for segment in shown['segments']:
        assert PAPER.encode()[segment['start']:segment['end']].decode() == segment['text']
    assert 'tools' not in request.context and 'Results.' not in json.dumps(request.context['window'])
    assert GRADING_INSTRUCTIONS in request.instructions
    options = json.dumps(request.output_schema)
    assert '"extract"' in options and 'source_lead' in options
    for name in ('source_read', 'source_locate', 'grading_populate', 'aggregate_populate', '"reason"'):
        assert name not in options.replace('"const": "reason"', '')
    assert EPISODE.offered_actions(summary, None) == ['extract']
    world['store'].close()


def test_the_extraction_saves_the_sheet_and_the_lead_in_one_unit_and_consumes_the_window(tmp_path):
    world = held_world(tmp_path)
    run = linked(tmp_path, world)
    asyncio.run(run.next_decision())
    outcome = asyncio.run(run.run_unit(ToolCall('extract', envelope(world, extraction(world)))))
    assert outcome['outcome']['status'] in ('completed', 'partial'), outcome['outcome']
    processing = outcome['outcome']['evidence_processing']
    assert processing['kind'] == 'graded' and len(processing['gradings']) == 1
    sheet_ref = processing['gradings'][0]['result']['sheet_ref']
    view = run.view
    records = view.records
    assert records.holds(sheet_ref) and records.receipt(sheet_ref)['how'] == 'produced'
    sheet = saved(world['store'], sheet_ref)['sheet']
    assert sheet['cells']['evidence_amount']['value'] == 1 and sheet['cells']['support_count']['value'] == 1
    rows = records.table(CELLS).select({'sheet_ref': sheet_ref})
    assert [row['component'] for row in rows] == ['evidence_amount']

    summary = EPISODE.internal_summary(view)
    cut = PAPER.encode().index(b'Results.')
    assert summary['input_list'] == [[cut, len(PAPER.encode())]] and summary['consumed_inputs'] == [[0, cut]]
    finding = summary['finding']
    assert len(finding['grading_sheets']) == 1 and len(finding['assessment_refs']) == 1
    features = finding['grading_sheets'][0]
    assert set(features) == set(GRADING_FEATURES)
    assert features['sheet_refs'] == [sheet_ref] and features['assertion_refs'] == [world['claim']['id']]
    assert (features['support_count'], features['conflict_count'], features['evidence_amount'],
            features['net_support'], features['unresolved_count']) == (1, 0, 1, 1, 0)
    assert records.get(finding['assessment_refs'][0])['investigation_finding']['status'] == 'retained'
    assert summary['lead_return'] == {'relevant_lead_count': 1, 'lead_source_refs': [world['paper']['id']]}
    assert EPISODE.credit(summary, records) == 1.0
    assert EPISODE.ceiling(summary, records, 'extract', None, None) == UNBOUNDED

    selection = ('literature_source_lead_dispositions', 'literature_a108_grading_cells')
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0}, selection)
    form = EPISODE.return_form.select(selection)
    assert form.admit(result, 'return') == json.loads(json.dumps(result))
    assert {sheet_ref, world['claim']['id'], rows[0]['id']} <= set(form.record_refs(result))
    assert 'investigation_finding' not in json.dumps(result) and 'Strain QX-7' not in json.dumps(result)
    world['store'].close()


def test_an_invalid_extraction_is_the_units_outcome_and_still_consumes_its_window(tmp_path):
    world = held_world(tmp_path)
    run = linked(tmp_path, world)
    asyncio.run(run.next_decision())
    arguments = extraction(world)
    arguments['source_lead'] = {**source_lead(world), 'relevance_rationale': '   '}
    outcome = asyncio.run(run.run_unit(ToolCall('extract', envelope(world, arguments))))
    assert outcome['outcome']['status'] == 'invalid'
    summary = EPISODE.internal_summary(run.view)
    cut = PAPER.encode().index(b'Results.')
    assert summary['input_list'] == [[cut, len(PAPER.encode())]]
    assert summary['finding']['grading_sheets'] == [] and EPISODE.credit(summary, run.view.records) == 0
    world['store'].close()
