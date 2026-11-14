"""Finished native work retains value until its original result is collected."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode import hpc_prediction as prediction
from gene_annotation_episode.hpc_episodes import HPCEpisodes
from gene_annotation_episode.hpc_monitoring import DEFAULT_POLICY, MonitorCronController
from hpc_helpers import commission, resources
from test_hpc_episode_design import context


@pytest.fixture(autouse=True)
def snapshot_clock(monkeypatch):
    # Evaluate the retained partial-work forecast at its observation time;
    # calendar passage must not expire this mathematical fixture's allocation.
    observed = json.loads((Path(__file__).parent/'fixtures/hpc/'
        'completed-unit-before-pbs-finish.json').read_text())['telemetry']['observed_at']
    monkeypatch.setattr('gene_annotation_episode.hpc_episodes.time.time', lambda: observed)


def pending(tmp_path, *, partial=False):
    telemetry = json.loads((Path(__file__).parent/'fixtures/hpc/'
        'completed-unit-before-pbs-finish.json').read_text())['telemetry']
    c = commission()
    c['candidates'][0]['units'][0]['unit_id'] = 'scientific_result'
    if partial:
        c['obligations']['second-work'] = deepcopy(c['obligations']['original-work'])
        other = deepcopy(c['candidates'][0]['units'][0])
        other.update(unit_id='other-unit', obligation_id='second-work')
        c['candidates'][0]['units'].append(other)
        telemetry.update(state='running', phase='R', completed_fraction=.5,
            current_unit_id='other-unit')
    binding = HPCEpisodes(None, store=None, run_id='test-run', directory=tmp_path,
        resources=resources(), commissions={'commission': c})
    parent = context()
    binding.initialize(parent)
    ledger = binding.state(parent)
    original = prediction.predict(prediction.prior_model(c['model']), {'size': 10})
    plan = {'plan_id': 'pending-original', 'candidate_id': c['candidates'][0]['id'],
        'original_prediction': original}
    ledger.put('plan', plan)
    ledger.put('forecast', {'plan_id': plan['plan_id'], 'issued_at': 100.})
    ledger.put('monitor', {'plan_id': plan['plan_id'], 'forecast_ref': 'observed-original',
        'conditional_prediction': prediction.update(original, telemetry)})
    MonitorCronController(ledger).attach(plan, 'original-job', DEFAULT_POLICY)
    return binding, parent, ledger, telemetry


def test_ready_output_remains_unresolved_while_scheduler_is_exiting(tmp_path):
    binding, parent, ledger, telemetry = pending(tmp_path)
    evidence = binding.continuation_for_action(parent, 'test-run:ready:0')['evidence']
    assert telemetry['state'] == 'unknown' and telemetry['phase'] == 'E'
    assert evidence['pending_action'] == 'collect'
    assert evidence['expected_continuation_credit'] == 10
    assert evidence['valuation']['value_kind'] == 'unresolved_acceptance_upper_bound'
    assert evidence['pending_by_obligation'] == {'original-work': 10}
    assert ledger.credit_view()['credit'] == 0
    assert evidence['earned_wait_credit'] == 0


def test_partial_ready_output_keeps_other_work_prediction_separate(tmp_path):
    binding, parent, ledger, telemetry = pending(tmp_path, partial=True)
    evidence = binding.continuation_for_action(parent, 'test-run:ready:1')['evidence']
    assert evidence['pending_action'] == 'collect'
    assert evidence['pending_by_obligation']['original-work'] == 10
    assert 0 < evidence['pending_by_obligation']['second-work'] <= 10
    assert evidence['expected_continuation_credit'] == pytest.approx(
        sum(evidence['pending_by_obligation'].values()))
    assert ledger.credit_view()['credit'] == 0


def test_collected_rejected_result_is_not_an_unread_output_opportunity(tmp_path):
    binding, parent, ledger, telemetry = pending(tmp_path)
    ledger.put('result', {'plan_id': 'pending-original',
        'unit': {'unit_id': 'scientific_result'}, 'document': {'quality': .1}})
    evidence = binding.continuation_for_action(parent, 'test-run:ready:2')['evidence']
    assert evidence.get('pending_action') != 'collect'
    assert evidence['expected_continuation_credit'] == 0
    assert ledger.credit_view()['credit'] == 0
