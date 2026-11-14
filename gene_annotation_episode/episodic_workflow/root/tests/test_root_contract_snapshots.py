"""UNEXECUTED engineering protocol tests; no native scientific schema claims.

Promote only after actual root dependency closure. The numerical snapshot below
is deliberately an engineered persisted-message fixture, not scientific data.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.root import episode_contract_information as information
from gene_annotation_episode.episodic_workflow.root import literature_numerical_contracts as numerical
from gene_annotation_episode.schema_information_text import schema_fingerprint


def test_numerical_error_is_exact_root_information_error():
    assert numerical.ContractInformationError is information.ContractInformationError
    error = information.ContractInformationError('invalid_contract_name', 'role')
    assert error.code == 'invalid_contract_name' and error.field == 'role'
    assert str(error) == 'invalid_contract_name:role'


def test_operation_information_detaches_exact_supplied_schema():
    schema = {'type': 'object', 'properties': {'value': {'type': 'number'}},
              'required': ['value'], 'additionalProperties': False}
    outcome = information.operation_contract_information(catalog=[{
        'name': 'example.operation', 'description': 'Supplied engineering operation',
        'input_schema': schema}], operation='example.operation')
    assert outcome['status'] == 'completed'
    assert outcome['record_refs'] == outcome['changed_record_refs'] == []
    assert outcome['result']['input_schema'] == schema
    assert outcome['result']['schema_sha256'] == schema_fingerprint(schema)
    outcome['result']['input_schema']['properties']['value']['type'] = 'integer'
    assert schema['properties']['value']['type'] == 'number'


def _saved():
    source = 'literature_rate_cells'
    facts = {'scientific_process': {source: {'type': 'array',
        'meaning': 'Engineered snapshot boundary fixture, not scientific values',
        'report_schema': {'type': 'array', 'items': {'type': 'number'}, 'x-source': source}}}}
    types = {'scientific_process': {source: {'type': 'array'}}}
    schema = {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}
    return {numerical.SAVED_MEMBER: {'version': numerical.VERSION,
        'permitted_child_roles': ['scientific_process'], 'fact_sources_by_role': facts,
        'fact_sources_sha256': schema_fingerprint(facts), 'source_types_by_role': types,
        'source_types_sha256': schema_fingerprint(types),
        'action_schema_sha256': schema_fingerprint(schema)}, 'schema': schema}


def test_saved_numerical_snapshot_uses_original_record_without_current_factory(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('saved validation consulted a current scientific factory')
    monkeypatch.setattr(numerical, 'registered_schema', forbidden)
    monkeypatch.setattr(numerical, 'import_module', forbidden)
    saved = _saved()
    retained = deepcopy(saved)
    checked = numerical.validate_frozen_contracts(saved)
    assert checked == retained[numerical.SAVED_MEMBER]
    checked['fact_sources_by_role']['scientific_process'].clear()
    assert saved == retained


def test_saved_numerical_action_schema_drift_uses_canonical_error():
    saved = _saved()
    saved['schema']['description'] = 'changed after freeze'
    with pytest.raises(information.ContractInformationError) as caught:
        numerical.validate_frozen_contracts(saved)
    assert caught.value.code == 'original_literature_numerical_contracts_mismatch'
