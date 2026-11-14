"""Commissioning-parent boundaries for the existing improvement child."""
import pytest
from . import test_implicit_annotation_parent as original
from .improvement_exchange_checks import paired, exchange, received, refused_choice, INITIAL


@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    monkeypatch.setattr('subprocess.Popen', original.forbidden)
    monkeypatch.setattr('socket.socket.connect', original.forbidden)
    monkeypatch.setattr('socket.socket.connect_ex', original.forbidden)


@pytest.mark.parametrize('parent_role', ('annotation', 'improvement'))
@pytest.mark.parametrize('scenario', ('request-valid', 'initial-invalid', 'return-valid', 'return-invalid',
    'saved-valid', 'saved-failure', 'mutable-global', 'expanded-error'))
def test_original_current_improvement_typed_request_and_return(tmp_path, parent_role, scenario):
    _, result = paired(tmp_path, exchange, parent_role, scenario)
    if scenario == 'request-valid':
        assert result['has_unit'] and result['error'] is None and len(result['built']) == 1
        assert ('validate', INITIAL, 'improvement') in result['events']
    elif scenario == 'initial-invalid':
        assert result['error'] is not None and not result['has_unit'] and result['action'] is None
    elif scenario == 'mutable-global':
        assert result['parse_error'] and not result['has_unit'] and result['action'] is None
    elif scenario == 'expanded-error':
        assert result['expanded_error'] and not result['has_unit'] and result['action'] is None
    elif scenario in ('return-invalid', 'saved-failure'):
        assert result['error'][0] == 'ReportDeliveryError'
        assert len(result['attempts']) == 1 and result['attempts'][0]['failure'] is not None
        if scenario == 'saved-failure': assert result['deliveries'][0] == result['deliveries'][1]
    else:
        assert result['error'] is None and result['returned'] == INITIAL
        assert len(result['attempts']) == 1
        assert any(name.endswith('from_child_annotation_improvement') for name, _ in result['owners'])
        if scenario == 'saved-valid': assert result['deliveries'][0] == result['deliveries'][1]


@pytest.mark.parametrize('parent_role', ('annotation', 'improvement'))
@pytest.mark.parametrize('callback', ('expanded', 'initial', 'contract'))
def test_original_late_selection_kind_mutations_remain_visible(tmp_path, parent_role, callback):
    _, result = paired(tmp_path, exchange, parent_role, 'request-valid', callback=callback)
    if callback == 'expanded':
        assert result['error'] == ('LookupError', 'episode_role_not_bound:improvement')
        assert result['events'][-1] == 'expanded_kind' and result['action'] is None
        assert result['mutated_kind'] == 'episode_child' and not result['has_unit']
    elif callback == 'initial':
        assert result['job_error'] and result['error'][0] == 'RuntimeError'
        assert result['events'][-1][0] == 'assign' and result['action'] is None
        assert result['mutated_kind'] == 'job_child' and not result['has_unit']
    else:
        # These actual axes do not consume A102's conditionally assigned
        # specialist local after TypedReportContract. Preserve their own result.
        assert result['error'] is None and result['has_unit']
        assert result['mutated_kind'] == 'episode_child' and 'contract_kind' in result['events']
        assert result['action'] is not None and len(result['built']) == 1


@pytest.mark.parametrize('parent_role', ('annotation', 'improvement'))
def test_actual_custom_registry_retains_original_fallback(tmp_path, parent_role):
    _, result = paired(tmp_path, exchange, parent_role, 'request-valid', custom=True)
    assert result['error'] is None and result['has_unit'] and result['owners'] == []


@pytest.mark.parametrize('kind', ('scientific', 'registered'))
def test_original_scientific_and_registered_child_refusals(tmp_path, kind):
    paired(tmp_path, refused_choice, kind)


@pytest.mark.parametrize('parent_role', ('annotation', 'improvement'))
def test_actual_recursive_redelivery_keeps_original_progress(tmp_path, parent_role):
    paired(tmp_path, received, parent_role)


@pytest.mark.parametrize('operand', ('key', 'kind', 'role'))
def test_original_custom_operand_callbacks_precede_expansion_error(tmp_path, operand):
    from .improvement_exchange_checks import custom_operand_order
    old, current = paired(tmp_path, custom_operand_order, operand)
    assert old['owners'] == current['owners'] == []
    assert current['original_error'] and current['action'] is None
    assert current['events'].count('validate_child_choice') == 1
    assert current['events'][-1] == 'expanded'
    if operand in ('key', 'kind'):
        assert any(isinstance(event, tuple) and event[0] == 'custom_string_equal'
                   for event in current['events'])
    else:
        # With annotation_child_roles=None, original validation accepts this
        # role without comparing it before the expansion callback raises.
        assert current['events'] == ('validate_child_choice', 'expanded')
