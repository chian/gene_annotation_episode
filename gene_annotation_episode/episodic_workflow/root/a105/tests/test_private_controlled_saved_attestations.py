"""Current controlled results retain strict saved dependency authentication."""
from copy import deepcopy
import pytest
from .scientific_attestation_replay import science
from .test_literature_controlled_response_v2_inputs import Fixture as V2Fixture
from .test_literature_controlled_response_v3_inputs import Fixture as V3Fixture

@pytest.mark.parametrize('owner', ('axis', 'pilot'))
@pytest.mark.parametrize('version, fixture_class', ((2, V2Fixture), (3, V3Fixture)))
def test_actual_saved_controlled_result_rejects_unknown_dependency_hash(owner, version, fixture_class):
    fixture = fixture_class(0)
    module = science(owner, f'literature_controlled_response_v{version}_inputs')
    result = getattr(module, f'read_controlled_response_v{version}_inputs')(fixture.args, read_source=fixture.source)
    validate = getattr(module, f'validate_controlled_response_v{version}_extraction')
    retained = deepcopy(result)
    assert validate(fixture.args, result) == retained
    changed = deepcopy(result)
    pins = changed['implementation_dependencies']['expected_module_fingerprints']
    pins[next(iter(pins))] = '0' * 64
    with pytest.raises(module.shared.ExperimentalContractError, match='saved_dependency_contract_mismatch'):
        validate(fixture.args, changed)
    assert result == retained
