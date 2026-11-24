"""The extraction of the table region of this episode, run through the real runner's public API on a real Store (no model is
asked: the answer is the one a model would give): the region is consumed by the one extraction that reads it, the unit saves
the perturbation sheet through the population route from the quoted bytes, and the return is admitted."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import ModelRequest, Rejected
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_perturbation_storage import (
    PROVIDER as PERTURBATION_PROVIDER)

from .leaf_world import SETTINGS, TEXT, answer, held_world, linked_run

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').TableEvidenceExtraction
PATH = EPISODE.binding_path


def test_the_table_region_is_the_input_list_and_its_extraction_consumes_it(tmp_path):
    store, entry, names = held_world(tmp_path)
    linked, _, _ = linked_run(tmp_path, [EPISODE()], PATH, entry, store, 'a106-table-input-list', {PATH: SETTINGS})
    request = asyncio.run(linked.next_decision())
    view = linked.view
    summary = EPISODE.internal_summary(view)
    assert summary['input_list'] == [[0, len(TEXT)]] and summary['table'] == TEXT.decode()
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    assert request.context['table'] == summary['table'] and 'table states a value' in request.instructions
    assert EPISODE.offered_actions(summary, None) == ['extract']
    assert EPISODE.credit(summary, view.records) == 0
    assert EPISODE.ceiling(summary, view.records, 'extract', None, None) == 1.0

    refused = {**answer(), 'literals': {**answer()['literals'], 'molecule': {'quote': 'not in the table'}}}
    with pytest.raises(Rejected):
        EPISODE.action(refused, summary, view.records, None)

    done = asyncio.run(linked.run_unit(EPISODE.action(answer(), summary, view.records, None)))
    assert done['outcome']['status'] == 'completed', done['outcome']
    sheet_ref = done['outcome']['result']['sheet_ref']
    reader = linked.view.records
    assert reader.receipt(sheet_ref)['how'] == 'produced' and reader.get(sheet_ref)['provider'] == PERTURBATION_PROVIDER
    summary = EPISODE.internal_summary(linked.view)
    assert summary['input_list'] == [] and summary['sheet_refs'] == [sheet_ref]
    assert summary['lead_source_refs'] == [names['source']] and EPISODE.credit(summary, reader) == 1.0
    with pytest.raises(LookupError, match='leaf_input_list_empty'):
        EPISODE.decide(summary, None, None)

    completion = {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': EPISODE.credit(summary, reader)}
    selection = ('literature_source_lead_dispositions', 'record_refs')
    result = EPISODE.final_to_parent(summary, completion, selection)
    assert EPISODE.return_form.select(selection).admit(result, 'return') == result
    assert result['record_refs'] == [sheet_ref] and TEXT.decode() not in json.dumps(result)
    store.close()


def test_the_one_table_region_is_the_yield_estimators_item(tmp_path):
    store, entry, _ = held_world(tmp_path)
    parent_input = EPISODE.read_from_parent(EPISODE.assignment_form.admit(entry['assignment'], 'test'), {})
    assert EPISODE.yield_controller(0.0, SETTINGS, parent_input).items == 1
    store.close()
