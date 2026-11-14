"""Pure schema/alias bindings and original incoming target envelope checks."""
from copy import deepcopy
from importlib import import_module

import pytest

BASE = 'gene_annotation_episode.episodic_workflow.root.'


@pytest.mark.parametrize('axis', ['a101', 'a105', 'a106', 'a108'])
def test_fba_reflective_schemas_and_native_reader_import_keep_original_records(axis):
    prefix = BASE + axis + '.library.retained_input_authority.'
    contracts = import_module(prefix + 'flux_balance_contracts')
    for kind in ('Reaction', 'Unit', 'Number', 'Bound', 'Cell', 'Tolerance', 'Issue',
                 'NativeFBAResult', 'FluxBalanceCalculations', 'SolutionPayload', 'FBAJob'):
        schema = contracts.flux_balance_schema(kind)
        assert schema['x-fba-record'] == kind and schema['type'] == 'object'
        assert schema['additionalProperties'] is False
        original = deepcopy(schema); schema.clear()
        assert contracts.flux_balance_schema(kind) == original
    assert callable(import_module(prefix + 'native_flux_balance_results').NativeFluxBalanceResults)
    with pytest.raises(ValueError, match='schema_invalid:/kind'):
        contracts.flux_balance_schema('undeclared_record')


@pytest.mark.parametrize('axis', ['a101', 'a105', 'a106', 'a108'])
def test_nmf_retains_actual_shared_method_bindings_without_executing_actions(axis):
    prefix = BASE + axis + '.library.retained_input_authority.'
    shared = import_module(prefix + 'genomic_overlap_result_receipts').GenomicOverlapResultReceipts
    selected = import_module(prefix + 'expression_nmf_result_receipts').ExpressionNMFResultReceipts
    for name in ('locked_action', 'require_action', '_selected', 'file_metadata', '_artifact_value',
                 'capture_control', 'observation', 'validate_observation'):
        assert getattr(selected, name) is getattr(shared, name)
        assert callable(getattr(selected, name))
    assert callable(import_module(prefix + 'native_expression_nmf_results').NativeExpressionNMFResults)


def target(kind='local'):
    return {'version': 'execution_target_v1', 'handle': 'original-handle', 'run_id': 'original-run',
        'resource_id': 'original-resource', 'resource_kind': kind, 'execution_id': 'original-execution',
        'request_sha256': 'a' * 64, 'origin_episode_id': 'original-episode',
        'assignment': {'retained_input': 'unchanged'}, 'scope': {'subject_refs': []}}


@pytest.mark.parametrize('kind', ['api', 'local', 'hpc'])
def test_original_incoming_target_schema_does_not_expand_active_api_contract(kind):
    reader = import_module(BASE + 'a106.library.retained_input_authority.execution_target_contracts')
    active = import_module(BASE + 'a106.execution_contracts')
    value = target(kind); original = deepcopy(value)
    result = reader.validate_target(value)
    assert result == original and value == original and result is not value
    assert active.TARGET_SCHEMA['properties']['resource_kind']['enum'] == ['api']
    if kind == 'api':
        assert active.validate_target(value) == original
    else:
        with pytest.raises(ValueError, match='invalid_execution_target'):
            active.validate_target(value)


@pytest.mark.parametrize('field,value', [('resource_kind', 'unknown'), ('request_sha256', 'bad'),
    ('origin_episode_id', ''), ('extra', 'not-original')])
def test_original_incoming_target_validator_keeps_closed_identity_rejections(field, value):
    reader = import_module(BASE + 'a106.library.retained_input_authority.execution_target_contracts')
    malformed = target(); malformed[field] = value
    with pytest.raises(ValueError, match='invalid_execution_target'):
        reader.validate_target(malformed)
