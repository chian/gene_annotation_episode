from copy import deepcopy
from decimal import Decimal
import hashlib
import json

import pytest

from gene_annotation_episode.bvbrc_alignment_values import (
    native_number, validate_native_number, numeric_cell, validate_numeric_cell,
    document_id, diagnostic, requirement)


ARTIFACT = {'raw_artifact_ref': 'a', 'source_ref': 's', 'sha256': 'a' * 64}
LOCATION = {'artifact': ARTIFACT, 'byte_start_0based': 0, 'byte_end_0based_exclusive': 10,
            'line_start_1based': 1, 'line_end_1based_inclusive': 1, 'xml_path': None}


@pytest.mark.parametrize('token,state,kind,value', [
    ('0', 'available', 'finite', 0), ('-0', 'available', 'finite', 0),
    ('-3.25', 'available', 'finite', -3.25), ('1e-300', 'available', 'finite', 1e-300),
    ('1e-9999', 'failed', 'underflow', None), ('1e9999', 'failed', 'overflow', None),
    (' NA ', 'not_measured', 'native_na', None), ('', 'missing', 'blank', None),
    (' \t', 'missing', 'blank', None), ('NaN', 'failed', 'nonfinite', None),
    ('-Inf', 'failed', 'nonfinite', None), ('oops', 'failed', 'malformed', None)])
def test_native_syntax_is_not_a_judgement(token, state, kind, value):
    actual = native_number(token, source_location=LOCATION)
    assert (actual['state'], actual['token_kind'], actual['value']) == (state, kind, value)
    assert actual['raw_token'] == token
    assert validate_native_number(actual) == actual
    assert actual['source_location'] is not LOCATION


def test_integer_precision_and_invalid_field_values_are_preserved():
    value = native_number('9007199254740993', source_location=LOCATION, integer=True)
    assert value['value'] == 9007199254740993
    assert validate_native_number(value) == value
    huge = native_number('1e400', source_location=LOCATION, integer=True)
    assert huge['value'] == int(Decimal('1e400'))
    assert validate_native_number(huge) == huge
    for token, kwargs in [('1.5', {'integer': True}), ('-3', {'minimum': 0}),
                          ('1.01', {'maximum': 1}),
                          ('1.00000000000000000000001', {'maximum': 1})]:
        actual = native_number(token, source_location=LOCATION, **kwargs)
        assert actual['state'] == 'incompatible'
        assert actual['value'] == float(token)
        assert validate_native_number(actual) == actual


@pytest.mark.parametrize('replacement', [0, 1, None, True])
def test_saved_native_token_tampering_is_rejected(replacement):
    value = native_number('1e-9999', source_location=LOCATION)
    value.update(value=replacement, state='available', token_kind='finite')
    with pytest.raises(ValueError):
        validate_native_number(value)


def test_unknown_ratio_retains_zero_denominator_and_counts_are_not_ratios():
    cell = numeric_cell(None, state='missing', unit='fraction', origin='calculated',
        population_id='p', method_id='ratio', numerator=0, denominator=0, requirement_ids=['r'])
    assert cell['numerator'] == cell['denominator'] == 0
    assert cell['value'] is None
    count = numeric_cell(0, state='available', unit='observations', origin='calculated',
                         population_id='p', method_id='count')
    assert count['numerator'] is count['denominator'] is None
    assert validate_numeric_cell(cell) == cell
    assert validate_numeric_cell(count) == count


@pytest.mark.parametrize('field,replacement', [('value', float('nan')), ('value', True),
    ('value', None), ('state', 'missing'), ('denominator', float('inf')), ('extra', 3)])
def test_invalid_saved_cell_fails(field, replacement):
    value = numeric_cell(3, state='available', unit='observations', origin='calculated',
                         population_id='p', method_id='count')
    value[field] = replacement
    with pytest.raises(ValueError):
        validate_numeric_cell(value)


def test_document_identity_depends_on_parameters_and_is_canonical():
    params = {'layout': 'current', 'alphabet': 'aa'}
    expected = hashlib.sha256(json.dumps({'artifact': ARTIFACT, 'parameters': params},
        sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    assert document_id('table', artifact=ARTIFACT, parameters=params) == 'table:' + expected
    assert document_id('table', artifact=ARTIFACT, parameters=dict(reversed(list(params.items())))) == 'table:' + expected
    assert document_id('table', artifact=ARTIFACT, parameters={**params, 'alphabet': 'na'}) != 'table:' + expected


def test_common_host_records_validate_without_host_or_io():
    assert diagnostic('code')['phase'] == 'association'
    req = requirement('r', kind='input_bytes', role='alignment', source_refs=['s'], reason_code='missing')
    assert set(req) == {'requirement_id', 'kind', 'role', 'source_refs', 'reason_code'}
    with pytest.raises(ValueError):
        diagnostic('code', phase='calculation')
    with pytest.raises(ValueError):
        diagnostic('code', evidence_refs=['s', 's'])


def test_outputs_detach_inputs_and_keep_negative_values():
    uncertainty = {'kind': 'confidence_interval', 'lower': -4, 'upper': 2, 'value': None, 'method_id': 'reported'}
    before = deepcopy(uncertainty)
    actual = numeric_cell(-2, state='available', unit='difference', origin='calculated',
        population_id='p', method_id='signed_difference', uncertainty=uncertainty)
    actual['uncertainty']['upper'] = 99
    assert uncertainty == before
    assert actual['value'] == -2
