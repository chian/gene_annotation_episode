"""Credit observations as controller inputs: real progress clock, real journal, real yield controllers.

Each unit's observation carries the episode's own credit (signed, unbounded) at its recorded progress receipt;
a yield_control controller fits it, and the journaled record restores to the same observation.
"""
import pytest

from episode_runtime import ProgressClock, RunJournal
from episode_runtime.journal import EpisodeRecorder
from method_loop import ClosedRecord
from yield_control import AccumulationYieldController, STATUS_INSUFFICIENT, STATUS_NORMAL

from gene_annotation_episode.episodic_workflow.episode_support.records.credit_observation import (
    credit_observation, restore_credit_observation)

PATH = (('episode', 'key'),)


@pytest.fixture
def clock(tmp_path):
    return ProgressClock(EpisodeRecorder(RunJournal(tmp_path / 'journal.sqlite3'), 'run', PATH),
                         run_id='run', episode_id='episode-id')


def test_observation_is_the_closed_controller_input_a_yield_controller_fits(clock):
    controller = AccumulationYieldController('episode-id', 0.0, 0.01)
    steps = [controller.observe('unit:' + str(position),
                                credit_observation(credit, clock.receipt(position), {'kind': 'tool'}))
             for position, credit in enumerate((2.5, 4.0, 3.0))]
    assert [step.marginal_credit for step in steps] == [2.5, 1.5, -1.0]
    assert controller.state().current_credit == 3.0
    receipt = clock.receipt(2)
    if receipt['status'] == 'available':
        assert steps[-1].estimate.expected_next_gain.status_code == STATUS_NORMAL
    else:
        assert steps[-1].estimate.expected_next_gain.status_code == STATUS_INSUFFICIENT


def test_credit_is_never_bounded_and_record_restores_unchanged(clock):
    observation = credit_observation(1e9, clock.receipt(0), {'received_record_refs': ['record:1']})
    assert isinstance(observation, ClosedRecord)
    record = observation.as_record()
    assert record['credit'] == 1e9
    assert record['estimation_context'] == {'progress_time': clock.receipt(0)}
    assert record['facts'] == {'received_record_refs': ['record:1']}
    assert restore_credit_observation(record).as_record() == record
    assert credit_observation(-7, clock.receipt(1)).as_record()['credit'] == -7


@pytest.mark.parametrize('credit', [float('nan'), float('inf'), True, '1', None])
def test_non_finite_credit_raises(clock, credit):
    with pytest.raises(ValueError, match='finite_number'):
        credit_observation(credit, clock.receipt(0))


def test_a_receipt_is_required(clock):
    with pytest.raises(ValueError, match='progress_receipt'):
        credit_observation(1.0, {'elapsed_seconds': 3.0})
    record = credit_observation(1.0, clock.receipt(0)).as_record()
    with pytest.raises(ValueError, match='credit_estimation_context_facts'):
        restore_credit_observation({**record, 'extra': 1})
    with pytest.raises(ValueError, match='its_progress_receipt'):
        restore_credit_observation({**record, 'estimation_context': {}})
