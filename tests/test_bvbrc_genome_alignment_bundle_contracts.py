"""Closed schemas, selector selection membership and canonical references."""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import bvbrc_genome_alignment_bundle_contracts as c
from test_bvbrc_genome_alignment_bundle_resolution import arguments, measurement, member


def test_parameters_schema_covers_all_seven_exact_plan_variants():
    from test_bvbrc_genome_alignment_sheet import fixture_data, all_requests, plan
    data = fixture_data()
    value = {'schema_version': 'bvbrc_genome_alignment_parameters_v1', 'analysis_id': data['analysis_id'],
        'document_slots': data['document_slots'], 'calculation_plan': plan(all_requests())}
    schema = c.parameters_schema(); Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(value)
    assert c.validate_parameters(value) == value
    schema['properties'].clear(); assert c.parameters_schema()['properties']


@pytest.mark.parametrize('kind', c.REFERENCE_KINDS)
def test_canonical_reference_quoting_roundtrip(kind):
    reference = c.encode_reference(kind, 'analysis /%é', 'identity /%[]é')
    assert c.decode_reference(reference) == (kind, 'analysis /%é', 'identity /%[]é')
    assert len(c.REFERENCE_KINDS) == 13


@pytest.mark.parametrize('value', ['wrong:x/y', 'bvbrc_genome_alignment_unknown:x/y',
    'bvbrc_genome_alignment_field:x/%61', 'bvbrc_genome_alignment_field:x/a/b',
    'bvbrc_genome_alignment_field:x/%ZZ', 'bvbrc_genome_alignment_field:x/%ff',
    'bvbrc_genome_alignment_field:/a'])
def test_forged_or_noncanonical_references_reject(value):
    with pytest.raises(ValueError, match='reference_'): c.decode_reference(value)


def test_exact_requested_schema_and_required_permutation():
    fields = {'number': measurement(), 'status': {'kind': 'request_status', 'request_id': 'anchors'}}
    form = c.requested_form_schema(fields); Draft202012Validator.check_schema(form)
    form['required'].reverse(); assert c.validate_requested_form(form) == form
    altered = deepcopy(form); altered['properties']['number']['additionalProperties'] = True
    with pytest.raises(ValueError, match='requested_form_noncanonical'): c.validate_requested_form(altered)
    for required in ([], ['status', 'status'], ['number', 'status', 'unknown']):
        altered = deepcopy(form); altered['required'] = required
        with pytest.raises(ValueError, match='requested_required_conflict'): c.validate_requested_form(altered)


@pytest.mark.parametrize('change', ['extra', 'bool_index', 'namespace', 'wrong_family', 'unknown_field', 'symbol', 'unknown_request', 'outside'])
def test_selector_corruption_cannot_relax_selection(change):
    args = arguments(); selector = measurement()
    if change == 'extra': selector['arbitrary_pointer'] = '/data'
    elif change == 'bool_index': selector['metric']['member']['index'] = False
    elif change == 'namespace': selector['metric']['member']['namespace'] = 'other'
    elif change == 'wrong_family': selector = measurement(family='backbone_coverage', member=member(0, 'mauve_sidecar_member_0based'))
    elif change == 'unknown_field': selector['metric']['field'] = 'confidence'
    elif change == 'symbol': selector = measurement('pairs', 'xmfa_symbol', 'count', block_index=0, column_0based=0, symbol='?')
    elif change == 'unknown_request': selector['request_id'] = 'missing-request'
    else: selector['metric']['member']['index'] = 99
    with pytest.raises(ValueError):
        form = c.requested_form_schema({'x': selector})
        c._validate_selections(args['parameters'], form)


@pytest.mark.parametrize('change', ['extra', 'bad_reader', 'boolean', 'source_denominator', 'duplicate', 'float_inf'])
def test_parameter_cross_field_shape_and_plan_errors(change):
    p = arguments()['parameters']
    if change == 'extra': p['extra'] = 1
    elif change == 'bad_reader': p['document_slots'][0]['reader']['dialect'] = 'mauve1'
    elif change == 'boolean': p['calculation_plan']['requests'][0]['selection']['members'][0]['index'] = False
    elif change == 'source_denominator': p['calculation_plan']['requests'][0]['selection']['denominator'] = 'validated_staged_length'
    elif change == 'duplicate': p['calculation_plan']['requests'] *= 2
    else: p['calculation_plan']['requests'][0]['selection']['members'][0]['index'] = float('inf')
    with pytest.raises(ValueError): c.validate_parameters(p)


def test_every_fact_schema_has_required_closed_objects_and_exact_selector_set():
    assert set(c.FACT_SCHEMAS) == set(c.SELECTORS)
    def inspect(schema):
        if type(schema) is dict:
            if schema.get('type') == 'object':
                assert schema['additionalProperties'] is False
                assert set(schema['required']) == set(schema['properties'])
            for value in schema.values(): inspect(value)
        elif type(schema) is list:
            for value in schema: inspect(value)
    for schema in c.FACT_SCHEMAS.values():
        Draft202012Validator.check_schema(schema); inspect(schema)
