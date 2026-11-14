"""Actual A110 original native fact schemas and semantic admission boundaries.

All failure rows are controlled records of unavailable/failed operations. They
are neither successful scientific measurements nor evidence of native execution.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.root.a110 import communication
from gene_annotation_episode.episodic_workflow.root.a110 import flux_balance_return_views as fba
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import atac_differential_return_views as atac
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import chromatin_interaction_return_views as chromatin
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import genomic_overlap_return_views as genomic

FAMILIES = [
    (atac, 'atac_differential_failures', 'atac_fact_sources', 'validate_atac_fact_values'),
    (chromatin, 'chromatin_interaction_failures', 'chromatin_fact_sources', 'validate_chromatin_fact_values'),
    (genomic, 'genomic_overlap_failures', 'genomic_overlap_fact_sources', 'validate_genomic_overlap_fact_values'),
    (fba, 'flux_balance_failures', 'fba_fact_sources', 'validate_fba_fact_values'),
]


def form(node, field='failures'):
    return {'type': 'object', 'properties': {field: node}, 'required': [field], 'additionalProperties': False}


def failure(source):
    if source == 'atac_differential_failures':
        return {'code': 'native_nonzero_exit', 'stage': 'execution', 'step_key': None, 'file_key': None,
            'binding_key': None, 'artifact_ref': None, 'locator': None, 'field_path': None,
            'requirement': 'original_native_outcome', 'partial_artifact_refs': []}
    if source == 'chromatin_interaction_failures':
        return {'code': 'native_nonzero_exit', 'stage': 'execution', 'input_key': None, 'population_key': None,
            'element_key': None, 'pair_key': None, 'artifact_ref': None, 'locator': None, 'field_path': None,
            'partial_artifact_refs': [], 'requirement': 'original_native_outcome'}
    if source == 'genomic_overlap_failures':
        return {'code': 'native_nonzero_exit', 'stage': 'native', 'set_key': None, 'comparison_key': None,
            'artifact_ref': None, 'locator': None, 'field_path': None, 'expected_value': 0,
            'observed_value': 2, 'partial_artifact_refs': [], 'requirement': 'original_native_output'}
    assert source == 'flux_balance_failures'
    return {'code': 'solver_exception', 'stage': 'solve', 'field': None, 'source_row_index': None,
            'reaction_position': None, 'metabolite_position': None, 'variable_position': None, 'constraint_position': None}


@pytest.mark.parametrize('module,source,catalog,validator', FAMILIES)
def test_empty_original_failure_field_is_a_valid_no_rows_result(module, source, catalog, validator):
    schema = form(getattr(module, catalog)()[source]['report_schema'])
    assert communication.validate_form({'failures': []}, schema) == {'failures': []}


@pytest.mark.parametrize('module,source,catalog,validator', FAMILIES)
def test_located_failed_outcome_is_retained_exactly(module, source, catalog, validator):
    schema = form(getattr(module, catalog)()[source]['report_schema'])
    row = failure(source)
    before = deepcopy(row)
    assert getattr(module, validator)(source, [row]) == [before]
    assert communication.validate_form({'failures': [row]}, schema) == {'failures': [before]}
    assert row == before


@pytest.mark.parametrize('module,source,catalog,validator', FAMILIES)
def test_malformed_failure_is_not_admitted_as_absence(module, source, catalog, validator):
    schema = form(getattr(module, catalog)()[source]['report_schema'])
    row = failure(source)
    del row['code']
    with pytest.raises(communication.ReportBoundaryError) as caught:
        communication.validate_form({'failures': [row]}, schema)
    assert caught.value.diagnostic['field'] == 'failures'


@pytest.mark.parametrize('module,source,catalog,validator', FAMILIES)
def test_changed_registered_schema_is_rejected(module, source, catalog, validator):
    node = deepcopy(getattr(module, catalog)()[source]['report_schema'])
    node['description'] = 'controlled forged schema'
    with pytest.raises(communication.ReportBoundaryError) as caught:
        communication.validate_closed_schema(form(node))
    assert caught.value.diagnostic['code'] == 'invalid_schema'


@pytest.mark.parametrize('module,source,catalog,validator', FAMILIES)
def test_native_fact_binding_must_remain_at_top_level(module, source, catalog, validator):
    node = getattr(module, catalog)()[source]['report_schema']
    with pytest.raises(communication.ReportBoundaryError) as caught:
        communication.validate_closed_schema(form(form(node), 'nested'))
    assert caught.value.diagnostic['code'] == 'invalid_schema'


@pytest.mark.parametrize('module,source,catalog,validator', FAMILIES)
def test_original_semantic_validator_is_called_and_failure_identity_kept(module, source, catalog, validator, monkeypatch):
    schema = form(getattr(module, catalog)()[source]['report_schema'])
    error = ValueError('controlled_original_semantic_failure')
    calls = []
    def reject(actual_source, value):
        calls.append((actual_source, value))
        raise error
    monkeypatch.setattr(module, validator, reject)
    with pytest.raises(communication.ReportBoundaryError) as caught:
        communication.validate_form({'failures': []}, schema)
    assert calls == [(source, [])]
    assert caught.value.__cause__ is error
    assert caught.value.diagnostic == {'category': 'report_format', 'code': 'invalid_form', 'field': 'failures'}


@pytest.mark.parametrize('allowed', [True, False])
def test_genomic_saved_schema_resolves_local_definitions_and_actual_reference_namespace(allowed):
    digest = 'a' * 64
    file = {'artifact_ref': 'artifact_' + digest, 'sha256': digest, 'size_bytes': 1,
            'format': 'genomic_region_overlap_sheet_v1'}
    schema = form(genomic.genomic_overlap_fact_sources()[genomic.SAVED_SOURCE]['report_schema'], 'saved')
    seen = []
    def resolve(reference, namespace):
        seen.append((reference, namespace))
        return allowed
    if allowed:
        assert communication.validate_form({'saved': [file]}, schema, resolve) == {'saved': [file]}
    else:
        with pytest.raises(communication.ReportBoundaryError) as caught:
            communication.validate_form({'saved': [file]}, schema, resolve)
        assert caught.value.diagnostic['code'] == 'unknown_reference'
    assert seen == [(file['artifact_ref'], 'artifact')]
