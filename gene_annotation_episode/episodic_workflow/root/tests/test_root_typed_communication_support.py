"""Real finite-JSON and ordinary typed form boundaries without science factories."""
from copy import deepcopy
from types import MappingProxyType

import pytest

from gene_annotation_episode.episodic_workflow.root import boundary_validation as boundary
from gene_annotation_episode.episodic_workflow.root import communication
from gene_annotation_episode.episodic_workflow.root import episode_contract_information as information


def _schema():
    return {'type': 'object', 'properties': {'status': {'type': 'string', 'enum': ['ready', 'pending']},
        'values': {'type': 'array', 'items': {'type': 'number'}}},
        'required': ['status', 'values'], 'additionalProperties': False}


def test_finite_parser_preserves_null_for_exchange_but_object_parser_rejects_it():
    assert boundary.parse_json_value('null') is None
    assert boundary.parse_json_object('{"values":[1,2.5],"ready":true}') == {
        'values': [1, 2.5], 'ready': True}
    with pytest.raises(boundary.ModelOutputError) as caught:
        boundary.parse_json_object('null')
    assert caught.value.raw_response == 'null'
    assert caught.value.diagnostic['category'] == 'non_object_json'


@pytest.mark.parametrize('text,category', [
    ('{"same":1,"same":2}', 'duplicate_json_key'),
    ('{"value":NaN}', 'nonfinite_json_number'),
    ('{"value":Infinity}', 'nonfinite_json_number'),
    ('{"value":1e999}', 'nonfinite_json_number'),
    ('{"value":', 'malformed_json'),
])
def test_parser_keeps_actual_invalid_response_and_category(text, category):
    with pytest.raises(boundary.ModelOutputError) as caught:
        boundary.parse_json_value(text)
    assert type(caught.value) is boundary.ModelOutputError
    assert caught.value.raw_response == text
    assert caught.value.diagnostic['category'] == category


def test_typed_form_and_compiled_schema_detach_immutable_inputs():
    schema = _schema()
    before = deepcopy(schema)
    compiled = communication.validate_closed_schema(schema)
    compiled['properties']['values']['items']['type'] = 'integer'
    assert schema == before
    payload = MappingProxyType({'status': 'ready', 'values': (1.0, 2.5)})
    checked = communication.validate_form(payload, schema)
    assert checked == {'status': 'ready', 'values': [1.0, 2.5]}
    checked['values'].append(9)
    assert payload['values'] == (1.0, 2.5) and schema == before


@pytest.mark.parametrize('payload,code', [
    ({'status': 'ready'}, 'required'),
    ({'status': 'ready', 'values': [], 'extra': True}, 'additionalProperties'),
    ({'status': 'unexpected', 'values': []}, 'enum'),
    ({'status': 'ready', 'values': [float('nan')]}, 'nonfinite_number'),
])
def test_typed_form_rejects_invalid_values_with_canonical_error(payload, code):
    with pytest.raises(communication.ReportBoundaryError) as caught:
        communication.validate_form(payload, _schema())
    assert type(caught.value) is information.ReportBoundaryError
    assert caught.value.diagnostic['code'] == code


def test_real_reference_registry_controls_form_admission():
    schema = {'type': 'object', 'properties': {'source': {'type': 'string',
        'format': 'reference', 'x-reference-namespace': 'source'}},
        'required': ['source'], 'additionalProperties': False}
    resolver = communication.reference_resolver({'source': {'source_original'}})
    assert communication.validate_form({'source': 'source_original'}, schema, resolver) == {
        'source': 'source_original'}
    with pytest.raises(communication.ReportBoundaryError) as caught:
        communication.validate_form({'source': 'source_unreceived'}, schema, resolver)
    assert caught.value.diagnostic == {'category': 'report_format',
                                       'code': 'unknown_reference', 'field': 'report.source'}
