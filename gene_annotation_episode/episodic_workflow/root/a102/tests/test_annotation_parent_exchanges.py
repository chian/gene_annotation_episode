"""Actual A102 nominal exchanges and original/current typed return boundaries."""
import json
import pytest
from .annotation_parent_exchange_checks import HOMES, INITIAL, parent_host, paired

@pytest.mark.parametrize('home', HOMES)
@pytest.mark.parametrize('scenario', ('request-valid', 'saved-valid', 'saved-failure'))
def test_original_private_nominal_exchange(tmp_path, home, scenario):
    with parent_host(tmp_path, home) as host:
        result = paired(host, host.role, scenario)
    assert result.events.index('validate_child_choice') < result.events.index('expanded_form')
    assert result.events.index('expanded_form') < result.events.index('for_child')
    assert result.has_unit and len(result.built) == 1
    assert json.loads(result.action['action']) == result.selection
    if scenario == 'saved-valid':
        assert result.error is None and result.result == INITIAL
        assert result.deliveries == [{'returned': INITIAL}, {'returned': INITIAL}]
        assert len(result.attempts) == 1 and result.attempts[0]['failure'] is None
        assert result.owners[-1][1] == 'admit_return'
    elif scenario == 'saved-failure':
        assert result.error[0] == 'ReportDeliveryError'
        assert len(result.attempts) == 1 and result.attempts[0]['failure'] is not None
        assert result.source_outcome['status'] == 'failed' and result.source_index == 7
        assert result.source_outcome['feedback']['category'] == 'child_execution'
        assert result.result == result.replayed == {'original_credit': 0.375}
        assert result.events.count('original_credit_port') == 1
        assert result.deliveries[0] == result.deliveries[1]
        assert 'build' not in result.events[result.events.index('replay_begin') + 1:]
    else:
        assert result.error is None and result.attempts == []

@pytest.mark.parametrize('home', ('resource_work_submission', 'scientific_process/resource_work_submission'))
@pytest.mark.parametrize('scenario', ('initial-invalid', 'prepare-error', 'return-valid', 'return-invalid', 'mutable-global', 'expanded-error'))
def test_original_private_parent_error_order_and_live_providers(tmp_path, home, scenario):
    with parent_host(tmp_path, home) as host:
        result = paired(host, host.role, scenario, custom_registry=scenario == 'expanded-error')
    if scenario == 'expanded-error':
        assert result.expanded_failure and result.events[-1] == 'expanded_form'
        assert result.owners == [] and 'for_child' not in result.events and 'custom_roles' not in result.events
    elif scenario in ('initial-invalid', 'prepare-error', 'mutable-global'):
        assert result.error is not None and not result.built
        assert result.action is None and result.attempts == []
        assert result.injected is (scenario == 'prepare-error')
        assert result.parse_failure is (scenario == 'mutable-global')
    elif scenario == 'return-valid':
        assert result.result == INITIAL and result.error is None
        assert result.owners[-1][1] == 'admit_unowned_return'
    else:
        assert result.error[0] == 'ReportDeliveryError'
        assert result.source_outcome['status'] == 'failed'
        assert result.result == result.replayed == {'original_credit': 0.375}
