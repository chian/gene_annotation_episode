"""Pure contract reuse must not cache mutable values or bypass changed inputs."""
from copy import deepcopy

import pytest

from gene_annotation_episode import bvbrc_appservice_contracts as contracts
from test_bvbrc_appservice_contracts import input_binding, request


@pytest.fixture(autouse=True)
def isolated_cache():
    with contracts._VALIDATION_CACHE_LOCK:
        contracts._VALIDATED_CONTRACTS.clear()
    yield
    with contracts._VALIDATION_CACHE_LOCK:
        contracts._VALIDATED_CONTRACTS.clear()


def supplied_request():
    value = request()
    value['parameters'] = {'file': '/exact/source'}
    value['input_bindings'] = [input_binding('workspace_object', '/exact/source')]
    return value


def test_identical_complete_value_reuses_validation_and_returns_detached_copy(monkeypatch):
    supplied = supplied_request()
    first = contracts.validate_request(supplied)

    def forbidden(*args, **kwargs):
        raise AssertionError('identical pure relationship validation repeated')

    monkeypatch.setattr(contracts, '_walk', forbidden)
    second = contracts.validate_request(deepcopy(supplied))
    first['parameters']['file'] = 'changed returned object'
    second['input_bindings'][0]['members'].append({'changed': True})
    assert contracts.validate_request(supplied) == supplied_request()


def test_changed_nested_operand_still_checks_exact_relationship():
    supplied = supplied_request()
    contracts.validate_request(supplied)
    supplied['parameters']['file'] = '/different/source'
    for _ in range(2):
        with pytest.raises(contracts.ContractValidationError, match='input_parameter_value_conflict'):
            contracts.validate_request(supplied)
    supplied['input_bindings'][0]['workspace_path'] = '/different/source'
    assert contracts.validate_request(supplied) == supplied


@pytest.mark.parametrize('replacement', [True, 1.0, '1'])
def test_cached_integer_does_not_accept_other_json_types(replacement):
    contracts.validate_contract('Range', [1, 3])
    with pytest.raises(contracts.ContractValidationError, match='contract_shape_invalid'):
        contracts.validate_contract('Range', [replacement, 3])


def test_current_schema_is_part_of_reuse_key(monkeypatch):
    value = {'source_ref': 'source:input', 'artifact_field': 'artifact_ref',
             'artifact_ref': 'artifact:input', 'sha256': 'a'*64, 'byte_count': 4}
    contracts.validate_contract('ContentBinding', value)
    changed = deepcopy(contracts._DEFINITIONS['ContentBinding'])
    changed['properties']['byte_count']['minimum'] = 5
    monkeypatch.setitem(contracts._DEFINITIONS, 'ContentBinding', changed)
    with pytest.raises(contracts.ContractValidationError, match='contract_shape_invalid'):
        contracts.validate_contract('ContentBinding', value)


@pytest.mark.parametrize('bad,code', [
    ({1: 'value'}, 'nonstring_json_key'), ((1, 2), 'not_plain_json'),
    ({'value': float('nan')}, 'nonfinite_number'),
])
def test_plain_finite_json_checks_run_before_cache_lookup(bad, code):
    contracts.validate_contract('Json', {'1': 'value'})
    contracts.validate_contract('Json', [1, 2])
    with pytest.raises(contracts.ContractValidationError, match=code):
        contracts.validate_contract('Json', bad)


def test_cache_retains_only_digests_and_is_bounded():
    for index in range(contracts._VALIDATION_CACHE_SIZE + 2):
        contracts.validate_contract('Json', {'private_example': str(index)})
    with contracts._VALIDATION_CACHE_LOCK:
        assert len(contracts._VALIDATED_CONTRACTS) == contracts._VALIDATION_CACHE_SIZE
        assert all(type(key) is bytes and len(key) == 32 and value is None
                   for key, value in contracts._VALIDATED_CONTRACTS.items())
