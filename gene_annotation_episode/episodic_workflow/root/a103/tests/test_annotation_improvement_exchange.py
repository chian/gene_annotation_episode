"""Actual unregistered annotation parent commissions its existing improvement child."""
import pytest
from .parent_exchange_checks import parent_host, paired, INITIAL

SCENARIOS = ('request-valid', 'initial-invalid', 'expanded-error', 'return-valid',
             'return-invalid', 'saved-valid', 'saved-failure', 'mutable-global')


@pytest.mark.parametrize('scenario', SCENARIOS)
def test_annotation_to_existing_improvement(tmp_path, scenario):
    with parent_host(tmp_path, 'improvement') as host:
        result = paired(host, 'improvement', scenario)
    assert result.events.index('validate_child_choice') < result.events.index('expanded_form')
    assert 'for_child' not in result.events and 'prepare_assignment' not in result.events
    if scenario in ('initial-invalid', 'expanded-error', 'mutable-global'):
        assert result.error is not None and result.action is None and not result.built
        assert result.expanded_failure is (scenario == 'expanded-error')
        assert result.parse_failure is (scenario == 'mutable-global')
    else:
        assert result.has_unit and len(result.built) == 1
        assert result.built[0]['assignment'] is None and result.built[0]['process'] is None
        if scenario in ('return-invalid', 'saved-failure'):
            assert result.error[0] == 'ReportDeliveryError'
            assert result.action['credit'] == 0.375
            assert result.result == result.replayed == {'original_credit': 0.375}
            assert 'build' not in result.events[result.events.index('replay_begin') + 1:]
        elif scenario in ('return-valid', 'saved-valid'):
            assert result.error is None and result.result == INITIAL
            assert result.attempts[0]['failure'] is None
            if scenario == 'saved-valid':
                assert result.deliveries == [{'returned': INITIAL}, {'returned': INITIAL}]
        else:
            assert result.error is None


@pytest.mark.parametrize('mutation', ('expanded', 'initial', 'contract'))
def test_annotation_improvement_preserves_late_kind_errors(tmp_path, mutation):
    with parent_host(tmp_path, 'improvement') as host:
        result = paired(host, 'improvement', 'request-valid', mutation=mutation)
    assert result.error is not None and not result.built
    if mutation == 'contract':
        assert result.error[0] == 'UnboundLocalError'


@pytest.mark.parametrize('operand', ('mapping', 'key', 'kind'))
def test_annotation_improvement_custom_operand_callbacks(tmp_path, operand):
    with parent_host(tmp_path, 'improvement') as host:
        result = paired(host, 'improvement', 'expanded-error', operand=operand)
    assert result.expanded_failure and result.events[-1] == 'expanded_form'
    assert result.owners == [] and result.action is None
    assert any(isinstance(event, tuple) and event[0] in ('mapping_getitem', 'key_comparison', 'kind_comparison')
               for event in result.events)


def test_annotation_improvement_custom_registry_fallback(tmp_path):
    with parent_host(tmp_path, 'improvement') as host:
        result = paired(host, 'improvement', 'expanded-error', custom_registry=True)
    assert result.expanded_failure and result.owners == [] and result.selector_events == []
    assert result.constructor_events == ['custom_roles']
