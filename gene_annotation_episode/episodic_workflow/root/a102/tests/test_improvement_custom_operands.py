"""Custom selection operands retain original callback and admission behavior."""
import pytest
from ..annotation_improvement.tests.improvement_host_checks import improvement_host
from .improvement_custom_operand_checks import paired


@pytest.mark.parametrize('operand', ('key', 'kind'))
def test_original_custom_selection_operand_callback_order(tmp_path, operand):
    with improvement_host(tmp_path, root_role='annotation') as host:
        result = paired(host, 'annotation', 'request-valid', custom_operand=operand)
    assert result['has_unit'] and result['error'] is None
    assert result['owners'] == []
    assert result['events'].count('validate_child_choice') == 1
    assert any(type(event) is tuple and event[0] == 'custom_string_equal'
        for event in result['events'])
    assert len(result['built']) == 1
    assert result['built'][0]['path'][-1][0] == 'improvement'
    assert result['selection']['kind'] == result['mutated_kind'] == 'child'
