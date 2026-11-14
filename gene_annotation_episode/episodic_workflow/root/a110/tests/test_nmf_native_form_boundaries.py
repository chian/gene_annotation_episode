"""Actual original A110 NMF form admission, independently of native execution."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.root.a110 import communication
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import expression_nmf_return_views as nmf
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.expression_nmf_common import SHEET_SCHEMA


def form(node, field='failures'):
    return {'type': 'object', 'properties': {field: node}, 'required': [field], 'additionalProperties': False}


def failure():
    return {'code': 'native_factorization_unavailable', 'stage': 'fit', 'field': None,
            'gene_position': None, 'sample_position': None, 'component_position': None}


def schema():
    return form(nmf.expression_nmf_fact_sources()[nmf.FAILURE_SOURCE]['report_schema'])


def test_nmf_empty_failure_field_remains_empty_rows():
    assert communication.validate_form({'failures': []}, schema()) == {'failures': []}


def test_nmf_failed_outcome_remains_exact_typed_failure():
    row = failure()
    assert nmf.validate_expression_nmf_fact_values(nmf.FAILURE_SOURCE, [row]) == [row]
    assert communication.validate_form({'failures': [row]}, schema()) == {'failures': [row]}


def test_malformed_nmf_failure_is_not_accepted_as_missing_evidence():
    row = failure()
    del row['code']
    with pytest.raises(communication.ReportBoundaryError) as caught:
        communication.validate_form({'failures': [row]}, schema())
    assert caught.value.diagnostic['field'] == 'failures'


def test_changed_original_nmf_schema_is_rejected():
    value = schema()
    value['properties']['failures']['description'] = 'controlled forged schema'
    with pytest.raises(communication.ReportBoundaryError) as caught:
        communication.validate_closed_schema(value)
    assert caught.value.diagnostic['code'] == 'invalid_schema'


def test_nmf_source_binding_cannot_move_below_top_level():
    with pytest.raises(communication.ReportBoundaryError) as caught:
        communication.validate_closed_schema(form(schema(), 'nested'))
    assert caught.value.diagnostic['code'] == 'invalid_schema'


def test_original_nmf_validator_dispatch_and_failure_identity(monkeypatch):
    value = schema()
    marker = ValueError('controlled_nmf_semantic_failure')
    calls = []
    def reject(source, rows):
        calls.append((source, rows))
        raise marker
    monkeypatch.setattr(nmf, 'validate_expression_nmf_fact_values', reject)
    with pytest.raises(communication.ReportBoundaryError) as caught:
        communication.validate_form({'failures': []}, value)
    assert calls == [(nmf.FAILURE_SOURCE, [])]
    assert caught.value.__cause__ is marker
    assert caught.value.diagnostic['field'] == 'failures'


@pytest.mark.parametrize('allowed', [True, False])
def test_nmf_saved_sheet_keeps_original_reference_authority(allowed):
    digest = 'a' * 64
    file = {'artifact_ref': 'artifact_' + digest, 'sha256': digest, 'size_bytes': 1, 'format': SHEET_SCHEMA}
    node = nmf.expression_nmf_fact_sources()[nmf.SAVED_SOURCE]['report_schema']
    seen = []
    def resolve(reference, namespace):
        seen.append((reference, namespace))
        return allowed
    if allowed:
        assert communication.validate_form({'saved': [file]}, form(node, 'saved'), resolve) == {'saved': [file]}
    else:
        with pytest.raises(communication.ReportBoundaryError) as caught:
            communication.validate_form({'saved': [file]}, form(node, 'saved'), resolve)
        assert caught.value.diagnostic['code'] == 'unknown_reference'
    assert seen == [(file['artifact_ref'], 'artifact')]
