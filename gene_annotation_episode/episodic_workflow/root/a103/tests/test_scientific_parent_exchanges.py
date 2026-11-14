"""Changed A103 scientific parent edges; existing child suites stay separate."""
import json
import pytest
from .scientific_parent_exchange_checks import ROLES, SCENARIOS, INITIAL, parent_host, paired


@pytest.mark.parametrize('role', ROLES)
@pytest.mark.parametrize('scenario', SCENARIOS)
def test_original_and_private_parent_exchange(tmp_path, role, scenario):
    with parent_host(tmp_path) as host:
        result = paired(host, role, scenario)
    assert result.events.index('validate_child_choice') < result.events.index('expanded_form')
    assert result.events.index('expanded_form') < result.events.index('for_child')
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
    assert 'custom_roles' not in result.events and 'for_child' not in result.events
    assert result.owners == [] and result.action is None
