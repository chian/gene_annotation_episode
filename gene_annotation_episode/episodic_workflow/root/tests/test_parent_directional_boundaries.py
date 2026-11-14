"""Connected preservation checks for the four existing parent edge forms."""
import json
import pytest
from parent_directional_boundary_checks import EDGES, INITIAL, parent_host, paired


@pytest.mark.parametrize('edge', EDGES)
@pytest.mark.parametrize('scenario', ('request-valid', 'initial-invalid', 'return-valid', 'return-invalid'))
def test_parent_directional_boundaries(tmp_path, edge, scenario):
    with parent_host(tmp_path) as host:
        result = paired(host, edge, scenario)
    assert result.events.index('expanded_form') > result.events.index('validate_child_choice')
    if 'for_child' in result.events:
        assert result.events.index('expanded_form') < result.events.index('for_child')
    if scenario == 'initial-invalid':
        assert result.error is not None
        assert not result.built and result.action is None and result.attempts == []
    else:
        assert result.has_unit and len(result.built) == 1
        assert json.loads(result.action['action']) == result.selection
        if scenario == 'return-invalid':
            assert result.error[0] == 'ReportDeliveryError'
            assert len(result.attempts) == 1 and result.attempts[0]['failure'] is not None
            assert result.source_outcome['status'] == 'failed'
            assert result.source_outcome['feedback']['category'] == 'child_execution'
            assert result.source_index == 7 and result.action['credit'] == 0.375
            assert result.result == {'original_credit': 0.375}
            assert not any(isinstance(event, tuple) and event[0] == 'receive_form' for event in result.events)
            assert result.events[-1] == 'original_credit_port'
            assert result.owners[-1][1] == 'admit_unowned_return'
        elif scenario == 'return-valid':
            assert result.error is None and result.result == INITIAL
            assert len(result.attempts) == 1 and result.attempts[0]['failure'] is None
            assert result.action['result'] is None and result.action['credit'] is None
            assert result.owners[-1][1] == 'admit_unowned_return'
        else:
            assert result.error is None and result.attempts == []


@pytest.mark.parametrize('edge', ('annotation-scientific', 'scientific-scientific'))
def test_scientific_prepare_error_order(tmp_path, edge):
    with parent_host(tmp_path) as host:
        result = paired(host, edge, 'prepare-error')
    assert result.injected and not result.built and result.action is None
    assert result.events.index('expanded_form') < result.events.index('for_child')
    assert result.events[-1][0] == 'prepare_invocation'


@pytest.mark.parametrize('edge', ('annotation-improvement', 'annotation-scientific'))
def test_custom_registry_expanded_form_precedes_callbacks(tmp_path, edge):
    with parent_host(tmp_path) as host:
        result = paired(host, edge, 'expanded-error', custom_registry=True)
    assert result.expanded_failure and result.events[-1] == 'expanded_form'
    assert 'custom_roles' not in result.events and 'for_child' not in result.events
    assert result.owners == [] and result.action is None
