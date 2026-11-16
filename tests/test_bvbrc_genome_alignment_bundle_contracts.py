"""Closed schemas, selector selection membership and canonical references."""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.root.library import bvbrc_genome_alignment_bundle_contracts as c
from test_bvbrc_genome_alignment_bundle_resolution import measurement


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
