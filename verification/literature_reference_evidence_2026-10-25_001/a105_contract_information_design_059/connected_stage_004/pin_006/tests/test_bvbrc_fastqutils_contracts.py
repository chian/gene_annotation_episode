"""Typed input/identity boundaries using explicitly synthetic contract examples."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode import bvbrc_fastqutils_contracts as c
from gene_annotation_episode import bvbrc_fastqutils_identity as identity
from gene_annotation_episode.bvbrc_fastqutils_metric_specs import metric_spec, component_spec

HERE = Path(__file__).parent / 'fixtures/bvbrc_fastqutils/contracts'


def example(name):
    return json.loads((HERE / name).read_text())


def document():
    return example('EXPECTED_NATIVE_DOCUMENTS_002.json')[0]


def context(doc=None):
    doc = doc or document()
    a = doc['artifact']
    return {'analysis_id': doc['analysis_id'], 'document_id': doc['document_id'],
            'task_ref': a['task_ref'], 'content': a['content_binding'], 'native_name': a['native_name'],
            'declared_format': a['declared_format'], 'producer_version': a['producer_version'],
            'transfer_scope': a['transfer_scope'], 'identity': a['identity']}


def test_contract_examples_validate_without_parsing_or_scientific_calculation():
    for doc in example('EXPECTED_NATIVE_DOCUMENTS_002.json'):
        c.validate_native_document(doc)
    c.validate_metadata(example('EXPECTED_METADATA_002.json'))
    sheet = example('EXPECTED_SHEET_002.json')
    c.validate_sheet(sheet)
    c.validate_components(example('EXPECTED_COMPONENTS_002.json'), sheet=sheet)


def test_explicit_lineage_assumption_preserves_numeric_values_and_unknown_execution():
    sheet = example('ASSUMED_LINEAGE_SHEET_002.json')
    components = example('ASSUMED_LINEAGE_COMPONENTS_002.json')
    c.validate_components(components, sheet=sheet)
    rows = [r for r in components['components'] if r['metric'] == 'read_retention_fraction']
    assert len(rows) == 1 and rows[0]['value'] == .75
    assert rows[0]['lineage_basis']['basis'] == 'explicit_source_bound_declaration'
    assert all(r['observed_state'] == 'unknown' for r in sheet['stages'])
    changed = deepcopy(components)
    changed['components'][0]['lineage_basis']['declaration']['relation'] = 'same_population'
    with pytest.raises(c.FastqUtilsContractError):
        c.validate_components(changed, sheet=sheet)


@pytest.mark.parametrize('value', [float('nan'), float('inf'), float('-inf'), (1, 2), {1: 'value'}, b'bytes', '\ud800'])
def test_non_json_or_nonfinite_values_never_acquire_a_canonical_hash(value):
    with pytest.raises(c.FastqUtilsContractError, match='nonfinite_json'):
        c.json_sha256({'input': value})


def test_cyclic_input_and_non_string_mapping_keys_are_rejected():
    a = []; a.append(a)
    with pytest.raises(c.FastqUtilsContractError):
        c.validate_finite_json(a)
    assert c.canonical_json(0) != c.canonical_json(False) != c.canonical_json(0.0)


@pytest.mark.parametrize('wrong', [True, 1.0, -1])
def test_content_length_is_an_actual_nonnegative_integer(wrong):
    content = context()['content']
    content['byte_count'] = wrong
    with pytest.raises(c.FastqUtilsContractError):
        c.validate_contract('Host_ContentBinding', content)


def test_content_binding_checks_full_bytes_and_length_without_authentication_claim():
    raw = b'ACGT\n'
    content = dict(context()['content'], sha256=c.bytes_sha256(raw), byte_count=len(raw))
    assert c.checked_bytes(raw, content=content) == raw
    with pytest.raises(c.FastqUtilsContractError, match='binding_conflict'):
        c.checked_bytes(raw + b'N', content=content)
    content['sha256'] = '0' * 64
    with pytest.raises(c.FastqUtilsContractError, match='binding_conflict'):
        c.checked_bytes(raw, content=content)


def test_unknown_native_name_is_null_and_not_an_invented_filename():
    doc = document()
    doc['artifact']['native_name'] = None
    c.validate_native_document(doc)
    assert context(doc)['native_name'] is None


def test_sam_and_bam_quality_representations_are_distinct_from_declared_fastq_encoding():
    location = document()['cells'][0]['locator']
    for basis, encoding in [('native_sam_phred', 'phred33'), ('native_bam_phred', 'bam_phred')]:
        value = {'basis': basis, 'encoding': encoding, 'metadata_id': None, 'evidence': None,
                 'declaration': None, 'native_locator': location}
        c._encoding(value)
        value['encoding'] = 'unknown'
        with pytest.raises(c.FastqUtilsContractError):
            c._encoding(value)


@pytest.mark.parametrize('pointer', ['/a~1b/~0/0', '/unicode/α', ''])
def test_reference_roundtrip_preserves_rfc6901_pointer(pointer):
    ref = identity.encode_reference('label', 'analysis', pointer)
    assert identity.decode_reference(ref) == {'kind': 'label', 'analysis_id': 'analysis', 'pointer': pointer}
    with pytest.raises(c.FastqUtilsContractError):
        identity.decode_reference(ref, expected_kind='cell')


@pytest.mark.parametrize('reference', [
    'bvbrc_fastqutils_cell:analysis/%2fdata',
    'bvbrc_fastqutils_cell:%61nalysis/%2Fdata',
    'bvbrc_fastqutils_cell:analysis/%FF',
    'bvbrc_fastqutils_cell:analysis/%2Fbad~2escape',
    'bvbrc_fastqutils_cell:analysis/%2Fdata/extra',
    'bvbrc_fastqutils_unknown:analysis/%2Fdata',
])
def test_noncanonical_or_invalid_identity_is_rejected(reference):
    with pytest.raises(c.FastqUtilsContractError):
        identity.decode_reference(reference)


def test_pointer_dereference_uses_exact_keys_and_canonical_array_indices():
    value = {'a/b': {'~': [3, {'x': 4}]}}
    result = c.pointer_value(value, '/a~1b/~0/1')
    result['x'] = 9
    assert value['a/b']['~'][1]['x'] == 4
    for pointer in ['/a~1b/~0/01', '/a~1b/~0/-', '/a~1b/~0/2', '/a~2b']:
        with pytest.raises(c.FastqUtilsContractError):
            c.pointer_value(value, pointer)


def test_document_identity_survives_content_change_but_native_identity_does_not():
    first = context(); changed = deepcopy(first)
    changed['content']['sha256'] = 'f' * 64
    assert identity.document_ref(first['analysis_id'], first['document_id']) == identity.document_ref(
        changed['analysis_id'], changed['document_id'])
    assert identity.native_ref('cell', first, 0) != identity.native_ref('cell', changed, 0)
    assert identity.native_ref('cell', first, 0) != identity.native_ref('cell', first, 1)


def test_native_fact_cannot_change_owner_or_reuse_another_identity():
    for mutate in [lambda d: d['cells'][0].update(artifact_ref='foreign'),
                   lambda d: d['cells'][0].update(id=d['cells'][1]['id']),
                   lambda d: d['artifact'].update(content_ref='foreign')]:
        doc = document(); mutate(doc)
        with pytest.raises(c.FastqUtilsContractError):
            c.validate_native_document(doc)


def test_sheet_may_add_explicit_encoding_but_may_not_rewrite_native_measurements():
    sheet = example('EXPECTED_SHEET_002.json')
    c.validate_sheet(sheet)
    sheet['measurements'][0]['value'] += 1
    with pytest.raises(c.FastqUtilsContractError):
        c.validate_sheet(sheet)


def test_original_library_and_recipe_values_remain_the_actual_submitted_ones():
    metadata = example('EXPECTED_METADATA_002.json')
    metadata['libraries'][0]['submitted_value'] = {'read': 'different'}
    with pytest.raises(c.FastqUtilsContractError):
        c.validate_metadata(metadata)
    metadata = example('EXPECTED_METADATA_002.json')
    metadata['stages'][0]['observed_state'] = 'completed'
    with pytest.raises(c.FastqUtilsContractError):
        c.validate_metadata(metadata)


def test_repeated_declared_document_id_cannot_select_two_different_inputs():
    parameters = example('PROVIDER_PARAMETERS_002.json')
    parameters['documents'].append(deepcopy(parameters['documents'][0]))
    with pytest.raises(c.FastqUtilsContractError, match='duplicate_identity'):
        c.validate_parameters(parameters)


def test_requested_form_keeps_exact_types_and_field_selection():
    form = example('REQUESTED_FORM_002.json')
    schema = c.make_requested_schema(form)
    assert c.validate_requested_form(schema) == form
    changed = deepcopy(schema)
    changed['properties']['read_count']['$ref'] = '#/$defs/Host_Json'
    with pytest.raises(c.FastqUtilsContractError):
        c.validate_requested_form(changed)
    changed = deepcopy(schema); changed['additionalProperties'] = True
    with pytest.raises(c.FastqUtilsContractError):
        c.validate_requested_form(changed)


def test_requested_form_order_survives_actual_canonical_storage():
    from gene_annotation_episode.execution_contracts import canonical
    form = example('REQUESTED_FORM_002.json')
    schema = c.make_requested_schema(form)
    assert list(schema['properties']) != sorted(schema['properties'])
    restored = json.loads(canonical(schema))
    assert list(restored['properties']) == sorted(schema['properties'])
    assert restored['required'] == schema['required']
    assert c.validate_requested_form(restored) == form


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'extra', 'wrong_type', 'missing_array'])
def test_requested_form_order_must_name_every_exact_field_once(change):
    schema = c.make_requested_schema(example('REQUESTED_FORM_002.json'))
    if change == 'missing': schema['required'].pop()
    elif change == 'duplicate': schema['required'].append(schema['required'][0])
    elif change == 'extra': schema['required'].append('not_a_selected_field')
    elif change == 'wrong_type': schema['required'][0] = []
    else: schema.pop('required')
    with pytest.raises(c.FastqUtilsContractError, match='requested_form_invalid'):
        c.validate_requested_form(schema)


def test_requested_schema_and_registry_results_are_detached():
    form = example('REQUESTED_FORM_002.json')
    first = c.make_requested_schema(form)
    first['$defs']['ProjectedField']['properties']['matched_count']['type'] = 'string'
    second = c.make_requested_schema(form)
    assert second['$defs']['ProjectedField']['properties']['matched_count']['type'] == 'integer'
    one = metric_spec('fastq_read_count'); one['units'].append('invented')
    assert metric_spec('fastq_read_count')['units'] == ['reads']
    assert component_spec('removed_count')['meaning_by_comparison_kind']['native_report_retention'] == 'native_report_derived'


def test_component_binds_original_sheet_parameter_and_actual_operand_set():
    sheet = example('EXPECTED_SHEET_002.json')
    base = example('EXPECTED_COMPONENTS_002.json')
    for mutate in [lambda d: d.update(sheet_sha256='0' * 64),
                   lambda d: d['components'][0].update(parameter_sha256='0' * 64),
                   lambda d: d['components'][0]['operand_measurement_refs'].append('invented')]:
        changed = deepcopy(base); mutate(changed)
        with pytest.raises(c.FastqUtilsContractError):
            c.validate_components(changed, sheet=sheet)
