"""Actual commissioning-parent to improvement integration boundaries."""
import pytest
from ..annotation_improvement.tests.improvement_host_checks import improvement_host
from .improvement_exchange_checks import paired

@pytest.mark.parametrize('parent_role', ('annotation', 'improvement'))
@pytest.mark.parametrize('scenario', ('request-valid', 'initial-invalid', 'return-valid', 'return-invalid',
    'saved-valid', 'saved-failure', 'mutable-global', 'expanded-error'))
def test_original_current_unregistered_child_boundary(tmp_path, parent_role, scenario):
    with improvement_host(tmp_path, root_role='annotation') as host:
        result = paired(host, parent_role, scenario)
    if scenario == 'request-valid':
        assert result['has_unit'] and result['error'] is None and len(result['built']) == 1
        assert ('resolver', 'improvement') in result['events']
        assert ('validate_report', {'qualification': 'unresolved'}, 'improvement') in result['events']
    elif scenario == 'initial-invalid':
        assert result['error'] is not None and not result['has_unit'] and result['action'] is None
    elif scenario == 'mutable-global':
        assert result['parse_error'] and not result['has_unit']
    elif scenario == 'expanded-error':
        assert result['expanded_error'] and not result['has_unit']
    elif scenario in ('return-invalid', 'saved-failure'):
        assert result['error'][0] == 'ReportDeliveryError'
        assert result['result'] == result['replayed'] == {'original_credit': 0.375}
        assert result['source_outcome']['status'] == 'failed'
    else:
        assert result['error'] is None and result['result'] == {'qualification': 'unresolved'}
        assert len(result['attempts']) == 1


@pytest.mark.parametrize('parent_role', ('annotation', 'improvement'))
def test_custom_registry_retains_original_unregistered_fallback(tmp_path, parent_role):
    with improvement_host(tmp_path, root_role='annotation') as host:
        result = paired(host, parent_role, 'request-valid', custom_registry=True)
    assert result['has_unit'] and result['error'] is None and result['owners'] == []


def test_improvement_registered_private_child_keeps_original_registry_error(tmp_path):
    with improvement_host(tmp_path, root_role='annotation') as host:
        result = paired(host, 'improvement', 'request-valid', unsupported_registered=True)
    assert result['error'][0] == 'LookupError'
    assert 'episode_role_not_bound:improvement' in result['error'][1]
    assert result['action'] is None and not result['has_unit']


def test_bound_scientific_retains_original_unfilled_child_rejection(tmp_path):
    with improvement_host(tmp_path, root_role='annotation') as host:
        result = paired(host, 'annotation', 'request-valid', scientific_bound=True)
    assert result['error'] == ('ValueError', 'scientific_child_requires_filled_process')
    assert 'expanded_form' not in result['events'] and result['action'] is None


@pytest.mark.parametrize('parent_role', ('annotation', 'improvement'))
@pytest.mark.parametrize('callback', ('expanded', 'initial', 'contract'))
def test_original_late_kind_callback_mutation_preserves_order_and_locals(tmp_path, parent_role, callback):
    with improvement_host(tmp_path, root_role='annotation') as host:
        result = paired(host, parent_role, 'request-valid', late_kind=callback)
    assert not result['has_unit'] and result['built'] == []
    if callback == 'expanded':
        assert result['error'][0] == 'LookupError'
        assert 'episode_role_not_bound:improvement' in result['error'][1]
        assert result['events'][-1] == 'expanded_mutated_episode_child'
        assert result['mutated_kind'] == 'episode_child' and result['action'] is None
    elif callback == 'initial':
        assert result['late_error'] and result['error'][0] == 'RuntimeError'
        assert result['mutated_kind'] == 'job_child' and result['action'] is None
        assert result['events'][-1][0] == 'actual_job_assign'
        assert ('validate_report', {'qualification': 'unresolved'}, 'improvement') in result['events']
    else:
        assert result['error'][0] == 'UnboundLocalError' and 'specialist' in result['error'][1]
        assert result['mutated_kind'] == 'episode_child'
        assert result['events'][-1] == 'contract_mutated_episode_child'
