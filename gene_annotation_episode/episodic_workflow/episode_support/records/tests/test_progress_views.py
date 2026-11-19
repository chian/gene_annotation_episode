"""Progress views shown to a model, over a real progress clock and a real yield controller state."""
import pytest

from episode_runtime import ProgressClock, RunJournal
from episode_runtime.journal import EpisodeRecorder
from yield_control import BoundedQualityYieldController

from gene_annotation_episode.episodic_workflow.episode_support.records.credit_observation import credit_observation
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import (
    time_accounting, yield_table)


@pytest.fixture
def clock(tmp_path):
    return ProgressClock(EpisodeRecorder(RunJournal(tmp_path / 'journal.sqlite3'), 'run', (('episode', 'key'),)),
                         run_id='run', episode_id='episode-id')


def test_time_accounting_presents_the_recorded_receipt_unchanged(clock):
    assert time_accounting(None)['status'] == 'no_completed_unit'
    receipt = clock.receipt(0)
    view = time_accounting(receipt)
    assert view['position'] == 0
    assert view['elapsed_seconds'] == receipt['elapsed_seconds']
    assert view['status'] == receipt['status']
    assert view['includes_idle_time'] is True and view['is_compute_consumption'] is False
    assert time_accounting(clock.receipt(0)) == view  # recorded once, read back
    with pytest.raises(ValueError, match='progress_receipt'):
        time_accounting({'elapsed_seconds': 1.0})


def test_yield_table_shows_the_controller_state_unchanged(clock):
    controller = BoundedQualityYieldController('episode-id', 0.0, 0.05, 10.0)
    for position, credit in enumerate((3.0, 5.0)):
        controller.observe('unit', credit_observation(credit, clock.receipt(position)))
    table = yield_table(controller.state(), forecast_unit='next_action')
    assert table['current_credit'] == 5.0 and table['initial_credit'] == 0.0
    assert table['marginal_credits'] == [3.0, 2.0] and table['completed_units'] == 2
    assert table['continuation_cost'] == 0.05
    assert table['stop_requested'] is controller.state().stop
    assert table['expected_next_gain'] == controller.state().estimate.expected_next_gain.as_record()
    assert table['forecast_unit'] == 'next_action'
    with pytest.raises(TypeError, match='yield_control_state'):
        yield_table({'current_credit': 1}, forecast_unit='next_action')
    with pytest.raises(ValueError, match='forecast_unit'):
        yield_table(controller.state(), forecast_unit='')
