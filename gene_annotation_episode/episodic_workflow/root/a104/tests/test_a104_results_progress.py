"""Actual acquired windows -> receipt -> credit -> original finite-byte yield.

Only the original filesystem observation/read ports are controlled. A reported
state of 'succeeded' is deliberately not the exact 'completed'/returncode=0
proof required by this implementation. Acquired-byte progress stays qualified.
"""
import asyncio
from copy import deepcopy

import pytest

from .test_a104_results_native_receipts import native_receipt
from .test_a104_results_preservation import binding_home, frame, own_module


def configured_owner(case):
    frame = case.frame
    prior = frame.owner
    configuration = deepcopy(prior.as_record()['configuration'])
    configuration.update(require_private_yield=True,
        task_yield_profiles={'results:native_finite_hpc': {'cutoff': 1.0, 'parameters': {}}})
    # This supplies the original required credit-cost fixture operand through
    # the actual constructor; it adds no application stopping rule or budget.
    frame.owner = type(prior)(prior.services, store=frame.store, run_id=frame.run_id,
        directory=prior.directory, tool_registry=None, **configuration)
    frame.owner.job_progress_provider = prior.job_progress_provider
    def no_ordinary_source_is_a_handoff(*args, **kwargs):
        raise AssertionError('ordinary fixture sources cannot become native handoffs')
    frame.owner.job_progress_provider.targets._handoff_reader = lambda: no_ordinary_source_is_a_handoff
    frame.owner.job_progress_provider.targets.usable_handoff = no_ordinary_source_is_a_handoff
    return frame.owner


@pytest.mark.parametrize('mode,expected_credit', [('bytes', 1.0), ('unavailable', 0.0), ('invalid', 0.0)])
def test_actual_returned_windows_connect_to_original_credit_and_yield(native_receipt, mode, expected_credit):
    case = native_receipt
    frame = case.frame
    owner = configured_owner(case)
    case.result['mode'] = mode
    before_view = owner.credit_view(frame.child, None)
    assert before_view['credit'] == 0.0
    controller = owner.yield_controller(frame.child, before_view['credit'], 'controlled-original-results-epoch')
    assert controller.cost == owner.task_yield_profiles['results:native_finite_hpc']['cutoff']
    returned = asyncio.run(owner._execute_native_results(frame.child, case.target,
        case.selected['tool'], case.arguments, case.key))
    reference, = returned['record_refs']
    # A completed information acquisition can retain a failed byte window.
    assert returned['status'] == 'completed'
    frame.journal.save('runtime_actions', {'episode_id': frame.child.episode_id, 'decision_index': 2,
        'result': own_module('runtime')._json(returned), 'credit': None})
    frame.receipts.receive(frame.child.episode_id, [reference], kind='own_action', source_index=2)
    selection = owner._selection(frame.child)
    assert reference in selection['known_record_refs'] and reference not in selection['initial_known_record_refs']
    view = owner.credit_view(frame.child, selection)
    assert view['credit'] == view['operational_credit'] == expected_credit
    assert view['new_handoff_count'] == 0
    assert view['new_acquired_selector_fraction'] == expected_credit
    assert view['new_acquired_record_count'] == int(expected_credit > 0)
    assert view['operational_credit_binding']['qualification'] == 'original_selector_byte_position_union_current_filesystem_version_unverified'
    assert owner.completion_for_action(frame.child, case.key) is None
    frame.journal.save('runtime_actions', {'episode_id': frame.child.episode_id, 'decision_index': 2,
        'credit': view['credit']})
    step = controller.observe('original-completed-result-action', {'credit': view['credit']})
    assert controller.estimator.scores == (expected_credit,)
    assert step.credit == expected_credit
    if mode == 'bytes':
        assert step.estimate.expected_next_gain.as_record() == own_module('numerical').NumericBand.exact(0).as_record()
    else:
        assert returned['result']['windows'] == [] and len(returned['result']['failures']) == 1
    # Reading/replaying the exact action does not duplicate bytes or progress.
    assert asyncio.run(owner._execute_native_results(frame.child, case.target,
        case.selected['tool'], case.arguments, case.key)) == returned
    assert owner.credit_view(frame.child, owner._selection(frame.child)) == view
    assert len(case.observed) == len(case.reads) == 1
    assert controller.estimator.scores == (expected_credit,)


