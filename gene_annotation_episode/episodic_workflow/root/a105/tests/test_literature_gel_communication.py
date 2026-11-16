"""Exact registered subdocument validation, separate from model-authored fields."""
from copy import deepcopy
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.communication import ReportBoundaryError, form_with_facts, _validate_form_semantics, generation_schema, interpretation_schema, validate_closed_schema, validate_form
from gene_annotation_episode.episodic_workflow.root.a105.domain import obj
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_gel_native_contracts import gel_cells_schema
SOURCE = 'literature_gel_component_cells'

def form_schema():
    return obj({'numbers': gel_cells_schema(), 'interpretation': {'type': 'string', 'enum': ['unknown', 'supported']}})

def test_exact_native_contract_is_unchanged_and_facts_remain_host_owned():
    schema = form_schema()
    original = deepcopy(schema)
    assert validate_closed_schema(schema) == schema
    assert interpretation_schema(schema) == obj({'interpretation': {'type': 'string', 'enum': ['unknown', 'supported']}})
    assert form_with_facts({'interpretation': 'unknown'}, schema, {SOURCE: []}) == {'numbers': [], 'interpretation': 'unknown'}
    assert validate_form({'numbers': [], 'interpretation': 'unknown'}, schema) == {'numbers': [], 'interpretation': 'unknown'}
    generation_schema(interpretation_schema(schema))
    assert schema == original
    with pytest.raises(ReportBoundaryError, match='Interpretations'):
        form_with_facts({'interpretation': 'unknown', 'numbers': []}, schema, {SOURCE: []})

@pytest.mark.parametrize('mutation', [lambda s: s['properties']['numbers'].update(description='changed native contract'), lambda s: s['properties']['numbers']['items']['properties']['sheet_ref'].update(type='number'), lambda s: s['properties']['numbers']['$defs'].pop('Science')])
def test_registered_native_contract_cannot_be_mutated(mutation):
    schema = form_schema()
    mutation(schema)
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(schema)

def test_native_contract_cannot_be_nested_and_parent_shape_stays_closed():
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(obj({'nested': obj({'numbers': gel_cells_schema()})}))
    schema = form_schema()
    for payload in ({'numbers': []}, {'numbers': [], 'interpretation': 'unknown', 'extra': 0}, {'numbers': {}, 'interpretation': 'unknown'}, {'numbers': [{}], 'interpretation': 'unknown'}, {'numbers': [], 'interpretation': 'unrestricted text'}):
        with pytest.raises(ReportBoundaryError):
            validate_form(payload, schema)


def test_semantic_local_resource_conditional_fixture_and_external_ref_rejection():
    native = {'type': 'array', 'items': {'allOf': [obj({'kind': {'enum': ['source', 'other']}, 'value': {'type': 'string'}}), {'if': {'properties': {'kind': {'const': 'source'}}}, 'then': {'properties': {'value': {'$ref': '#/$defs/Reference'}}}}]}, '$defs': {'Reference': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}}}
    actual = [{'kind': 'source', 'value': 'source_test'}]
    from jsonschema import Draft202012Validator
    Draft202012Validator(native).validate(actual)
    with pytest.raises(ReportBoundaryError, match='unavailable'):
        _validate_form_semantics(actual, native, lambda *_: False, resource=native)
    native['items']['allOf'][1]['then']['properties']['value'] = {'$ref': 'https://invalid.example/remote-schema'}
    with pytest.raises(ReportBoundaryError, match='external'):
        _validate_form_semantics(actual, native, lambda *_: False, resource=native)
    original = form_schema()
    original['properties']['numbers']['items'] = {'$ref': 'https://invalid.example/remote-schema'}
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(original)

