"""The extraction of the chunks of this episode, run through the real runner's public API on a real Store (no model is
asked: the answers are the ones a model would give): each chunk is consumed by the one extraction that reads it, the unit
saves the perturbation sheet through the population route from the quoted bytes, and the return is admitted."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import ModelRequest, Rejected
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_perturbation_storage import (
    PROVIDER as PERTURBATION_PROVIDER)

from .leaf_world import SECOND, SETTINGS, TEXT, answer, held_world, linked_run, silent_answer

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').PassageEvidenceExtraction
PATH = EPISODE.binding_path


def start(tmp_path, run_id, chunks=2):
    store, entry, names = held_world(tmp_path, chunks=chunks)
    linked, _, _ = linked_run(tmp_path, [EPISODE()], PATH, entry, store, run_id, {PATH: SETTINGS})
    return store, linked, names


def test_the_chunks_are_the_input_list_and_each_extraction_consumes_the_first(tmp_path):
    store, linked, names = start(tmp_path, 'a106-passage-input-list')
    request = asyncio.run(linked.next_decision())
    view = linked.view
    summary = EPISODE.internal_summary(view)
    assert summary['input_list'] == [[0, len(TEXT)], [len(TEXT) + 1, len(TEXT) + len(SECOND)]]
    assert summary['chunk'] == TEXT.decode()
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    assert request.context['chunk'] == summary['chunk']
    assert EPISODE.offered_actions(summary, None) == ['extract']
    assert EPISODE.credit(summary, view.records) == 0
    assert EPISODE.ceiling(summary, view.records, 'extract', None, None) == 1.0

    first = asyncio.run(linked.run_unit(EPISODE.action(answer(), summary, view.records, None)))
    assert first['outcome']['status'] == 'completed', first['outcome']
    sheet_ref = first['outcome']['result']['sheet_ref']
    reader = linked.view.records
    assert reader.receipt(sheet_ref)['how'] == 'produced' and reader.get(sheet_ref)['provider'] == PERTURBATION_PROVIDER
    summary = EPISODE.internal_summary(linked.view)
    assert summary['input_list'] == [[len(TEXT) + 1, len(TEXT) + len(SECOND)]]
    assert summary['chunk'] == SECOND.decode()[1:] and summary['sheet_refs'] == [sheet_ref]
    assert summary['lead_source_refs'] == [names['source']]
    assert EPISODE.credit(summary, reader) == 1.0

    # The quotation of the first chunk is not in the second: refused before any unit exists.
    with pytest.raises(Rejected):
        EPISODE.action(answer(), summary, reader, None)
    # A chunk that reports nothing is a returned outcome of the route; it consumes the chunk and adds no sheet.
    second = asyncio.run(linked.run_unit(EPISODE.action(silent_answer(), summary, reader, None)))
    assert second['outcome']['status'] == 'invalid', second['outcome']
    summary = EPISODE.internal_summary(linked.view)
    assert summary['input_list'] == [] and summary['sheet_refs'] == [sheet_ref]
    with pytest.raises(LookupError, match='leaf_input_list_empty'):
        EPISODE.decide(summary, None, None)

    completion = {'ended_by': 'yield_stop', 'units_consumed': 2, 'credit': EPISODE.credit(summary, reader)}
    selection = ('literature_source_lead_dispositions', 'record_refs')
    result = EPISODE.final_to_parent(summary, completion, selection)
    assert EPISODE.return_form.select(selection).admit(result, 'return') == result
    assert result['record_refs'] == [sheet_ref] and result['finding'] == {'intervention_assessments': [],
                                                                          'a106_subscores': []}
    assert TEXT.decode() not in json.dumps(result)
    store.close()


def test_the_chunks_the_commission_counts_are_the_yield_estimators_items(tmp_path):
    store, entry, _ = held_world(tmp_path)
    parent_input = EPISODE.read_from_parent(EPISODE.assignment_form.admit(entry['assignment'], 'test'), {})
    assert EPISODE.yield_controller(0.0, SETTINGS, parent_input).items == 2
    store.close()
