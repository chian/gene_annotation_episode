"""The input list of the source coverage improvement episode: the commissioned windows in document order, each consumed by
the one extraction that reads it, run through the real runner's public API on a real Store (no model is asked: the answers
are the ones a model would give)."""
import asyncio
import importlib
import pytest

from episode_runtime import ModelRequest, Rejected

from .a106_world import SECOND, SETTINGS, TEXT, answer, held_world, linked_run

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceCoverageImprovement
PATH = EPISODE.binding_path


def start(tmp_path, run_id):
    store, entry, names = held_world(tmp_path)
    linked, _, _ = linked_run(tmp_path, [EPISODE()], PATH, entry, store, run_id, {PATH: SETTINGS})
    return store, linked, names


def silent_answer():
    """An answer for the second window, which reports no experiment: nothing stated, only the unit it can quote."""
    form = answer()
    form['literals'] = dict.fromkeys(form['literals'])
    form.update(design='unknown', measurement_status='unknown', same_endpoint_scope='unknown', amount_role='unknown',
                orientation=None, interpretation_witnesses=[])
    form['source_measurements'] = {'endpoint_unit': {'quote': 'window'}, 'exposure_unit': None,
                                   'measurements': dict.fromkeys(form['source_measurements']['measurements'])}
    return form


def test_the_windows_are_the_input_list_and_each_extraction_consumes_the_first(tmp_path):
    store, linked, names = start(tmp_path, 'a106-report-input-list')
    request = asyncio.run(linked.next_decision())
    view = linked.view
    summary = EPISODE.internal_summary(view)
    assert summary['input_list'] == [[0, len(TEXT)], [len(TEXT) + 1, len(TEXT) + len(SECOND)]]
    assert summary['windows_total'] == 2 and summary['window'] == TEXT.decode()
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    assert request.context['window'] == summary['window']
    assert EPISODE.offered_actions(summary, None) == ['extract']
    assert EPISODE.credit(summary, view.records) == 0
    assert EPISODE.ceiling(summary, view.records, 'extract', None, None) == 1.0

    first = asyncio.run(linked.run_unit(EPISODE.action(answer(), summary, view.records, None)))
    assert first['outcome']['status'] == 'completed', first['outcome']
    summary = EPISODE.internal_summary(linked.view)
    assert summary['input_list'] == [[len(TEXT) + 1, len(TEXT) + len(SECOND)]]
    assert summary['window'] == SECOND.decode()[1:] and summary['sheet_refs'] == [first['outcome']['result']['sheet_ref']]
    assert summary['lead_source_refs'] == [names['source']]
    assert EPISODE.credit(summary, linked.view.records) == 1.0
    assert EPISODE.ceiling(summary, linked.view.records, 'extract', None, None) == 0.0

    # The quotation of the first window is not in the second: the answer is refused before any unit exists.
    with pytest.raises(Rejected):
        EPISODE.action(answer(), summary, linked.view.records, None)
    # A window that reports nothing is a returned outcome of the route; it consumes the window, and no sheet is added.
    second = asyncio.run(linked.run_unit(EPISODE.action(silent_answer(), summary, linked.view.records, None)))
    assert second['outcome']['status'] == 'invalid', second['outcome']
    summary = EPISODE.internal_summary(linked.view)
    assert summary['input_list'] == [] and len(summary['sheet_refs']) == 1
    assert EPISODE.credit(summary, linked.view.records) == 1.0
    with pytest.raises(LookupError, match='leaf_input_list_empty'):
        EPISODE.decide(summary, None, None)
    store.close()


def test_the_windows_the_commission_counts_are_the_yield_estimators_items(tmp_path):
    store, entry, _ = held_world(tmp_path)
    parent_input = EPISODE.read_from_parent(EPISODE.assignment_form.admit(entry['assignment'], 'test'), {})
    assert EPISODE.yield_controller(0.0, SETTINGS, parent_input).items == 2
    store.close()
