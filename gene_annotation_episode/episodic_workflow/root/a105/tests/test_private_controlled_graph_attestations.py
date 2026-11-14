"""Pixel counter provenance stays bound to the exact saved source release."""
from copy import deepcopy
import pytest
from .scientific_attestation_replay import science
from .test_literature_controlled_response_v2_inputs import Fixture as V2Fixture
from .test_literature_controlled_response_v3_inputs import Fixture as V3Fixture

@pytest.mark.parametrize('owner', ('axis', 'pilot'))
@pytest.mark.parametrize('version, fixture_class', ((2, V2Fixture), (3, V3Fixture)))
def test_actual_saved_graph_rejects_unknown_pixel_counter_hash(owner, version, fixture_class):
    fixture = fixture_class(6)
    module = science(owner, f'literature_controlled_response_v{version}_inputs')
    result = getattr(module, f'read_controlled_response_v{version}_inputs')(fixture.args, read_source=fixture.source)
    validate = getattr(module, f'validate_controlled_response_v{version}_extraction')
    retained = deepcopy(result)
    assert validate(fixture.args, result) == retained
    changed = deepcopy(result)
    altered = []
    def change_counter(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == 'counter_module_sha256':
                    value[key] = '0' * 64
                    altered.append(key)
                else:
                    change_counter(item)
        elif isinstance(value, list):
            for item in value:
                change_counter(item)
    change_counter(changed)
    assert altered
    with pytest.raises(module.shared.ExperimentalContractError, match='saved_graph_image_identity_mismatch'):
        validate(fixture.args, changed)
    assert result == retained
