"""Saved numerical projection and reversible communication, without host custody.

Actual executor custody/Workflow tests are separate. These synthetic envelopes
cannot prove transport, original commissioning or service deployment.
"""
from copy import deepcopy
import importlib.util
from pathlib import Path
import uuid

import pytest

from gene_annotation_episode import bvbrc_fastqutils_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_appservice_publication import AppServicePublications, RESULT_VERSION
from gene_annotation_episode.bvbrc_fastqutils_contracts import validate_requested_form
from gene_annotation_episode.bvbrc_fastqutils_returns import (
    FACT_SOURCES, BVBRCFastqUtilsReturns, encode_return_value, decode_return_value,
    fastqutils_fact_sources, parent_form_schema, project_fastqutils_return_facts,
)
from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.execution_contracts import canonical, digest

spec = importlib.util.spec_from_file_location('fastq_return_fixtures',
    Path(__file__).parent / 'fixtures/bvbrc_fastqutils/bundle/fixture_support.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


def content(value, source=None):
    sha = digest(value)
    return {'source_ref': source or 'source_' + sha[:24], 'artifact_field': 'artifact_ref',
        'artifact_ref': 'artifact_' + sha, 'sha256': sha,
        'byte_count': len(canonical(value).encode())}


def saved_fixture(data=None, fields=None):
    if data is None:
        data, fields = f.seven_family_data()
    bundle, raw, values, parameters = data
    # C's schema-only fixture changes the path without the parallel original
    # task association. This host-contract fixture explicitly declares the
    # same synthetic path on both sides before parsing, never after saving.
    for artifact in bundle['artifacts']:
        synthetic_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, 'synthetic-fastqutils:' + artifact['workspace_object']['path']))
        artifact['workspace_object']['uuid'] = synthetic_uuid
        artifact['task_association']['output_path'] = artifact['workspace_object']['path']
        artifact['task_association']['output_uuid'] = synthetic_uuid
    selected = f.oracle('RESULT_SELECTOR_PRE_DOWNLOAD_002.json')
    selected.update(requested_schema=f.schema(fields), adapter={
        'adapter_id': adapter.ADAPTER_ID, 'adapter_version': adapter.ADAPTER_VERSION,
        'parameters': parameters})
    bundle['requested_selector_sha256'] = digest(selected)
    result = f.run(data, fields)
    sheet, components = result['sheet'], result['components']
    saved = {key: deepcopy(result[key]) for key in
        ('adapter_id', 'adapter_version', 'status', 'facts', 'missing_requirements', 'diagnostics')}
    saved.update(sheet_content=content(sheet), components_content=content(components))
    source = 'source_' + digest(bundle)[:24]
    body = {'version': RESULT_VERSION, 'source_ref': source, 'reference': source, 'record_refs': [source],
        'assignment': {'selector': selected}, 'publication_inputs': {'selector': selected,
            'adapter': selected['adapter'], 'adapter_implementation_sha256': adapter.implementation_sha256()},
        'bundle': bundle, 'publication': {'bundle_content': content(bundle, source),
            'result_record_refs': [source], 'adapter_result': saved}}
    return body, sheet, components


@pytest.fixture
def retained():
    value = saved_fixture()
    projected(value)  # Adverse cases must start with a valid saved publication.
    return value


def projected(retained):
    body, sheet, components = retained
    return project_fastqutils_return_facts(body, requested_sources=FACT_SOURCES, sheet=sheet, components=components)


def forbid_science(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('saved communication attempted acquisition or scientific recalculation')
    for name, functions in {
        'bvbrc_fastqutils_bundle_adapter': ('consume_bundle', 'parse_fastqutils_artifact', 'calculate_fastqutils', 'populate_fastqutils_sheet'),
        'bvbrc_fastqutils_native': ('parse_fastqutils_artifact',),
        'bvbrc_fastqutils_calculators': ('calculate_fastqutils',),
        'bvbrc_fastqutils_sheet': ('populate_fastqutils_sheet',),
    }.items():
        module = __import__('gene_annotation_episode.' + name, fromlist=['unused'])
        for function in functions:
            monkeypatch.setattr(module, function, forbidden)
    monkeypatch.setattr('socket.socket.connect', forbidden)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)


def test_all_seven_families_retain_actual_numbers_through_closed_schema(retained, monkeypatch):
    expected = projected(retained)
    assert len(expected) == 7 and all(expected.values())
    body, _, _ = retained
    native = body['publication']['adapter_result']['facts']
    assert [native[key]['records'][0]['payload']['value'] for key in
        ('read_count', 'gc', 'errors', 'retained')] == [2, 5 / 9, .001, .75]
    form = validate_requested_form(body['publication_inputs']['selector']['requested_schema'])
    schema = parent_form_schema(form)
    returned = {name: expected[node['x-source']] for name, node in schema['properties'].items()}
    validate_form(returned, schema,
        lambda reference, namespace=None: BVBRCFastqUtilsReturns._has_reference(expected, reference, namespace))
    for name, field in native.items():
        kind = field['selection']['target']['kind']
        assert decode_return_value(kind, encode_return_value(kind, field)) == field
    forbid_science(monkeypatch)
    assert projected(retained) == expected


def test_record_and_semantic_selectors_roundtrip_without_mutating_original(retained):
    value = deepcopy(retained[0]['publication']['adapter_result']['facts']['read_count'])
    original = deepcopy(value)
    encoded = encode_return_value('measurement', value)
    selector = encoded['selection']['target']['selector']
    assert selector['selection'] == 'semantic' and selector['record_ref'] is None
    assert selector['rows'] == {'kind': 'all', 'ordinal': None}
    assert decode_return_value('measurement', encoded) == original == value
    record = deepcopy(value)
    record['selection']['target']['selector'] = {
        'selection': 'record', 'record_ref': value['records'][0]['record_ref']}
    encoded = encode_return_value('measurement', record)
    assert encoded['selection']['target']['selector']['document_id'] is None
    assert decode_return_value('measurement', encoded) == record


@pytest.mark.parametrize('change', ['inactive', 'missing_key', 'extra_key', 'wrong_family', 'nan', 'record_fields'])
def test_communication_codec_rejects_ambiguous_or_changed_selector_values(retained, change):
    value = encode_return_value('measurement', retained[0]['publication']['adapter_result']['facts']['read_count'])
    selector = value['selection']['target']['selector']
    if change == 'inactive': selector['record_ref'] = 'not-inactive'
    elif change == 'missing_key': selector.pop('record_ref')
    elif change == 'extra_key': selector['invented'] = None
    elif change == 'wrong_family': value['records'][0]['kind'] = 'component'
    elif change == 'nan': value['records'][0]['payload']['value'] = float('nan')
    else: selector['rows']['ordinal'] = 0
    with pytest.raises((ValueError, KeyError, TypeError)):
        decode_return_value('measurement', value)


@pytest.mark.parametrize('change', ['field', 'value', 'source', 'pin', 'selector', 'parameters',
    'sheet', 'components', 'native_failures', 'generic_failures'])
def test_original_saved_selection_and_values_cannot_be_relabelled(retained, change):
    body, sheet, components = deepcopy(retained)
    saved = body['publication']['adapter_result']
    if change == 'field': saved['facts']['invented'] = saved['facts'].pop('read_count')
    elif change == 'value': saved['facts']['read_count']['records'][0]['payload']['value'] = 999
    elif change == 'source': body['source_ref'] = 'source_' + '0' * 24
    elif change == 'pin': body['publication_inputs']['adapter_implementation_sha256'] = 'not-a-pin'
    elif change == 'selector': body['bundle']['requested_selector_sha256'] = '0' * 64
    elif change == 'parameters': body['publication_inputs']['adapter']['parameters']['analysis_id'] = 'other'
    elif change == 'sheet': sheet['analysis_id'] = 'other'
    elif change == 'components': components['calculations']['components'][0]['value'] = 999
    elif change == 'native_failures': components['native_diagnostics'].append({
        'code': 'invented_native_diagnostic', 'record_refs': [], 'source_refs': []})
    else: saved['diagnostics'].append({'code': 'invented', 'phase': 'native_decode',
        'path': '', 'severity': 'qualification', 'evidence_refs': []})
    with pytest.raises((ValueError, KeyError, TypeError)):
        projected((body, sheet, components))


def test_cardinality_excess_preserves_all_records_through_parent_grammar():
    data = f.build({'reads': (b'@a\nAC\n+\nII\n@b\nACGT\n+\nIIII\n', 'fastq')})
    fields = {'lengths': f.selection('measurement', f.measurement(metric='fastq_length_histogram_count',
        section='fastq_summary', axis={'kind': 'all'}), cardinality='exact_rows', count=1)}
    body, sheet, components = saved_fixture(data, fields)
    native = body['publication']['adapter_result']['facts']['lengths']
    assert native['state'] == 'cardinality_mismatch' and len(native['records']) == 2
    facts = projected((body, sheet, components))
    schema = parent_form_schema(validate_requested_form(body['publication_inputs']['selector']['requested_schema']))
    returned = {name: facts[node['x-source']] for name, node in schema['properties'].items()}
    validate_form(returned, schema, lambda *_: True)
    assert len(returned['facts_0'][0]['value']['records']) == 2


def test_missing_target_preserves_null_payload_and_unknown_scope():
    data = f.build({'reads': (f.fastq(['a']), 'fastq')})
    data[3]['documents'].append({'document_id': 'not_acquired',
        'selection': {'kind': 'output_requirement', 'requirement_id': 'missing_reads'},
        'format': 'fastq', 'producer_version': None})
    fields = {'absent': f.selection('measurement', f.measurement(document='not_acquired'))}
    body, sheet, components = saved_fixture(data, fields)
    native = body['publication']['adapter_result']['facts']['absent']
    assert native['matched_count'] == 0 and native['records'][0]['payload'] is None
    facts = projected((body, sheet, components))
    encoded = facts['bvbrc_fastqutils_measurements'][0]['value']
    assert decode_return_value('measurement', encoded) == native


def test_partial_sheet_gets_return_reference_without_claiming_completion(retained):
    body, _, _ = retained
    bundle = body['bundle']
    for row in bundle['artifacts']:
        row['transfer'].update(body_complete=False, object_complete='no')
    bundle['status'] = 'partial'
    saved = body['publication']['adapter_result']
    saved['status'] = 'partial'
    inputs = body['publication_inputs']
    content_binding = body['publication']['bundle_content']
    assert AppServicePublications._result_references(inputs, bundle, content_binding, saved) == [body['source_ref']]
    assert AppServicePublications._requested_status(inputs, bundle, content_binding, saved)[0] == 'partial'
    saved['sheet_content'] = None
    assert AppServicePublications._result_references(inputs, bundle, content_binding, saved) == []


def test_schema_descriptors_are_isolated_and_empty_selection_is_no_work():
    before = fastqutils_fact_sources()
    changed = fastqutils_fact_sources()
    changed[FACT_SOURCES[0]]['report_schema']['items']['properties'].clear()
    assert fastqutils_fact_sources() == before
    assert project_fastqutils_return_facts(None, requested_sources=(), sheet=None, components=None) == {}
    with pytest.raises(ValueError):
        project_fastqutils_return_facts(None, requested_sources=('invented',), sheet=None, components=None)
