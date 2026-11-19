"""What a unit that did not finish wrote (third audit, T9): nothing of it is visible through ``view.records`` or
``records``; the rerun's tool is told and may take it over; a row the attempt rewrote is put back; and a cut
between the Store's commit and the journal's receipt is recovered from the Store. Real Store, journal and runner;
every interruption is a real exception."""
import sqlite3

import pytest

from episode_runtime import CustodyError
from episode_runtime.recording import Custody, UnitPosition
from episode_runtime.store_ledger import StoreLedger
from episode_runtime.work_tables import WorkRows
from method_loop import EpisodeRef

from .probe_world import again, outcomes, probe_path, run, tool, world  # noqa: F401 - ``world`` is the fixture


def produced(world, run_id):
    return [row['ref'] for row in world['journal'].receipts(run_id, probe_path(run_id)) if row['how'] == 'produced']


def recover(world, run_id):
    """Build the Episode's custody as a resume does (which abandons what its unfinished unit wrote)."""
    path, rows = probe_path(run_id), WorkRows(world['store'])
    return Custody(world['journal'], StoreLedger(world['store'], rows), run_id, path,
                   EpisodeRef(run_id, path).episode_id, UnitPosition(world['journal'], run_id, path))


def cut(world, run_id, plan, message):
    world['switch'].fail = True
    with pytest.raises(RuntimeError, match=message):
        run(world, run_id, plan)
    world['switch'].fail = False


def test_an_abandoned_record_the_rerun_took_over_is_held_and_the_summary_reads_it(world):
    cut(world, 'taken', [tool('leave', reclaim=True), tool('bump')], 'cut after the marker was written')
    marker, = produced(world, 'taken')
    result = again(world, 'taken')
    first = outcomes(world, 'taken')[0]
    assert first['outcome'] == {'abandoned': [marker], 'read_by_the_tool': ['marker of ' + world['journal'].attempts(
        'taken', probe_path('taken'))[0][2]], 'held': [True], 'summary_read': marker}
    assert first['produced'] == [marker] == produced(world, 'taken')
    assert result['record'].units_consumed == 2
    assert again(world, 'taken')['result'].as_record() == result['result'].as_record()


def test_an_abandoned_record_the_rerun_did_not_take_over_is_read_by_nothing_else(world):
    """The rerun names the abandoned record for the summary without taking it over. The tool itself read it; the
    summary is refused at once, in the same unit, and every resume fails the same way (the episode names a record
    it does not hold). Nothing completes with a record that is later lost."""
    cut(world, 'left', [tool('leave', reclaim=False), tool('bump')], 'cut after the marker was written')
    marker, = produced(world, 'left')
    journal, path = world['journal'], probe_path('left')
    for _ in range(2):
        with pytest.raises(CustodyError, match='record_not_held'):
            again(world, 'left')
        assert journal.units('left', path) == [] and produced(world, 'left') == []
        assert [(label, state) for _, label, _, state in journal.attempts('left', path)] == [
            ('tool:leave:0', 'began')]
        assert journal.abandoned('left', path, 0) == [marker]
        assert 'CustodyError: record_not_held' in journal.run_failure('left')
    assert journal.times_begun('left', path, 0) == 3


def test_what_an_unfinished_unit_wrote_is_abandoned_before_the_unit_is_decided_again(world):
    """From the moment a run is resumed the Episode does not hold what its unfinished unit produced, so the
    decision for that unit is rebuilt from the state the first attempt was decided on."""
    cut(world, 'early', [tool('bump'), tool('leave', reclaim=False)], 'cut after the marker was written')
    marker, = produced(world, 'early')
    custody = recover(world, 'early')
    assert not custody.holds(marker) and marker not in custody.refs() and custody.abandoned() == ()
    with pytest.raises(CustodyError, match='record_not_held'):
        custody.require_readable(marker)
    with pytest.raises(CustodyError, match='record_not_held'):
        custody.require_unit_readable(marker)                # no tool of the unit is running
    assert produced(world, 'early') == [] and world['journal'].abandoned('early', probe_path('early'), 1) == [marker]


@pytest.mark.parametrize('reclaim', [False, True])
def test_a_row_rewritten_by_an_abandoned_attempt_is_put_back_and_the_rerun_is_told(world, reclaim):
    run_id = 'rewritten_' + str(reclaim)
    plan = [tool('row_write', k='a', v=1), tool('row_write', k='a', v=2, fail=True, reclaim=reclaim),
            tool('read_rows')]
    cut(world, run_id, plan, 'cut after the row was written')
    rows = WorkRows(world['store'])
    ref = outcomes(world, run_id)[0]['outcome']['row']
    assert (rows.row(ref)['v'], rows.row(ref)['revision'], rows.row(ref)['unit']) == (2, 2, 1)   # it was committed
    recover(world, run_id)
    assert (rows.row(ref)['v'], rows.row(ref)['revision'], rows.row(ref)['unit']) == (1, 1, 0)   # and is put back
    again(world, run_id)
    first, second, third = outcomes(world, run_id)
    assert second['outcome'] == {'before': [[1, 1, 0]], 'told': [{'written': [2, 2], 'prior': [1, 1]}], 'row': ref,
                                 'value': 2, 'revision': 2, 'row_unit': 1, 'resumed': True}
    assert second['produced'] == [ref] and third['outcome'] == {'rows': [['a', 2, 2, 1]]}
    assert produced(world, run_id) == [ref] and world['journal'].receipts(run_id, probe_path(run_id))[-1]['unit'] == 0


def test_a_row_created_by_an_abandoned_attempt_is_removed_and_the_rerun_is_told(world):
    cut(world, 'created', [tool('row_write', k='n', v=7, fail=True), tool('read_rows')],
        'cut after the row was written')
    ref, = produced(world, 'created')
    rows = WorkRows(world['store'])
    assert rows.row(ref)['v'] == 7
    custody = recover(world, 'created')
    assert rows.row(ref) is None and not custody.holds(ref)
    again(world, 'created')
    first, second = outcomes(world, 'created')
    assert first['outcome'] == {'before': [], 'told': [{'written': [7, 1], 'prior': None}], 'row': ref, 'value': 7,
                                'revision': 1, 'row_unit': 0, 'resumed': True}
    assert second['outcome'] == {'rows': [['n', 7, 1, 0]]} and produced(world, 'created') == [ref]
    assert world['journal'].abandoned('created', probe_path('created'), 0) == [ref]


def test_a_cut_between_the_store_commit_and_the_journal_receipt_is_recovered_from_the_store(world):
    """The Store commits a unit's writes together with its own receipts of them. Here the journal refuses the
    copy of those receipts (its database aborts the insert), so the run ends with records in the Store and no
    receipt in the journal. The resume writes the journal's copy from the Store, the unit that did not finish is
    abandoned as usual, and its rerun is told what the abandoned attempt wrote."""
    journal, store, path = world['journal'], world['store'], probe_path('cut')
    journal.db.execute("CREATE TEMP TRIGGER cut_receipts BEFORE INSERT ON receipts WHEN NEW.how='produced' "
                       "BEGIN SELECT RAISE(ABORT, 'the journal write was cut'); END")
    with pytest.raises(sqlite3.DatabaseError, match='the journal write was cut'):
        run(world, 'cut', [tool('write_tx')])
    journal.db.execute('DROP TRIGGER cut_receipts')
    source, = [row for row in store.list('source') if row['accession'] == 'CUT']
    written = [source['artifact_ref'], source['id']]
    assert produced(world, 'cut') == [] and journal.abandoned('cut', path, 0) == []
    ledger = StoreLedger(store, WorkRows(store))
    assert ledger.receipts('cut', path) == [(written[0], 0, False), (written[1], 0, False)]
    again(world, 'cut')
    outcome = outcomes(world, 'cut')[0]
    assert outcome['outcome'] == {'artifact': written[0], 'source': written[1], 'resumed': True, 'told': written}
    assert journal.abandoned('cut', path, 0) == written
    # The rerun wrote the same content again: it is produced by the rerun and held.
    assert outcome['produced'] == written == produced(world, 'cut')
    assert ledger.receipts('cut', path) == [(written[0], 0, False), (written[1], 0, False)]


def test_a_rolled_back_transaction_leaves_no_receipt_in_the_store_either(world):
    run(world, 'rolled', [tool('transactions')])
    kept = outcomes(world, 'rolled')[0]['outcome']['kept']
    store = world['store']
    assert [ref for ref, _, _ in StoreLedger(store, WorkRows(store)).receipts('rolled', probe_path('rolled'))] == kept
    assert produced(world, 'rolled') == kept
