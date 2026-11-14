"""Saved-release compatibility cannot authorize a different scientific operand."""
from copy import deepcopy
import pytest
from .scientific_attestation_replay import science
from .test_literature_controlled_response_v3_inputs import Fixture

@pytest.mark.parametrize('owner', ('axis', 'pilot'))
@pytest.mark.parametrize('case_index', (0, 6))
def test_saved_full_source_projection_rejects_changed_calculation_operand(owner, case_index):
    fixture = Fixture(case_index)
    module = science(owner, 'literature_controlled_response_v3_inputs')
    result = module.read_controlled_response_v3_inputs(fixture.args, read_source=fixture.source)
    retained = deepcopy(result)
    assert module.validate_controlled_response_v3_extraction(fixture.args, result) == retained
    changed = deepcopy(result)
    role = module.shared.PRIMITIVE_ORDER[2]
    operand = changed['calculation_inputs']['arms'][role]
    assert type(operand['value']) in (int, float)
    operand['value'] += 1
    assert changed['implementation_dependencies'] == retained['implementation_dependencies']
    with pytest.raises(module.shared.ExperimentalContractError, match='saved_source_projection_mismatch'):
        module.validate_controlled_response_v3_extraction(fixture.args, changed)
    assert result == retained
