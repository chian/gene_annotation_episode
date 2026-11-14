"""Changed existing recursive Scientific parent edge; completed child suites stay separate."""
import json
import pytest
from .recursive_scientific_parent_checks import ROLES, SCENARIOS, INITIAL, parent_host, paired


@pytest.mark.parametrize('role', ROLES)
@pytest.mark.parametrize('scenario', SCENARIOS)
def test_original_and_private_parent_exchange(tmp_path, role, scenario):
    with parent_host(tmp_path) as host:
        result = paired(host, role, scenario)
    assert result.events.index('validate_child_choice') < result.events.index('expanded_form')
    # Own original binding selector resolves the counterpart before expanded form.
    assert result.events.index('validate_child_choice') < result.events.index('for_child')
    assert result.events.index('for_child') < result.events.index('expanded_form')
    if scenario in ('initial-invalid', 'prepare-error', 'mutable-global'):
        assert result.error is not None and not result.built
        assert result.action is None and result.attempts == []
        assert result.injected is (scenario == 'prepare-error')
        assert result.parse_failure is (scenario == 'mutable-global')
    else:
        assert result.has_unit and len(result.built) == 1
        assert json.loads(result.action['action']) == result.selection
        if scenario in ('return-invalid', 'saved-failure'):
            assert result.error[0] == 'ReportDeliveryError'
            assert len(result.attempts) == 1 and result.attempts[0]['failure'] is not None
            assert result.source_outcome['status'] == 'failed'
            assert result.source_outcome['feedback']['category'] == 'child_execution'
            assert result.source_index == 7 and result.action['credit'] == 0.375
            assert result.result == result.replayed == {'original_credit': 0.375}
            assert result.events.count('original_credit_port') == 1
            assert 'build' not in result.events[result.events.index('replay_begin') + 1:]
            assert not any(isinstance(event, tuple) and event[0] == 'receive_form' for event in result.events)
            if scenario == 'saved-failure':
                assert len(result.deliveries) == 2 and result.deliveries[0] == result.deliveries[1]
                assert result.owners[-1][1] == 'admit_return'
        elif scenario in ('return-valid', 'saved-valid'):
            assert result.error is None and result.result == INITIAL
            assert len(result.attempts) == 1 and result.attempts[0]['failure'] is None
            assert result.action['result'] is None and result.action['credit'] is None
            if scenario == 'saved-valid':
                assert result.deliveries == [{'returned': INITIAL}, {'returned': INITIAL}]
                assert result.owners[-1][1] == 'admit_return'
            else:
                assert result.owners[-1][1] == 'admit_unowned_return'
        else:
            assert result.error is None and result.attempts == []


@pytest.mark.parametrize('role', ROLES)
def test_custom_registry_preserves_original_error_order(tmp_path, role):
    with parent_host(tmp_path) as host:
        result = paired(host, role, 'expanded-error', custom_registry=True)
    assert result.expanded_failure and result.events[-1] == 'expanded_form'
    assert 'custom_roles' not in result.events
    assert result.events.count('for_child') == 1
    assert result.owners == [] and result.action is None


@pytest.mark.parametrize('scenario', ('typed-progress', 'typed-error', 'typed-redelivery'))
def test_original_and_private_typed_receiving(tmp_path, scenario):
    with parent_host(tmp_path) as host:
        result = paired(host, 'scientific_process', scenario)
    assert len(result.built) == 1 and result.attempts == []
    assert json.loads(result.action['action']) == result.selection
    assert result.action['result'] is None and result.action['credit'] is None
    assert result.owners[-1][1] == 'receive_report'
    progress = [event for event in result.events if isinstance(event, tuple) and event[0] == 'typed_progress']
    receipts = [event for event in result.events if isinstance(event, tuple) and event[0] == 'typed_receipt']
    assert len(progress) == 1
    if scenario == 'typed-error':
        assert result.injected and result.error[0] == 'RuntimeError'
        assert receipts == []
    else:
        assert result.error is None and result.result == []
        if scenario == 'typed-redelivery':
            assert len(receipts) == 1
            assert receipts[0][2] == {'kind': 'report_redelivery', 'source_index': 7}
        else:
            assert receipts == []
