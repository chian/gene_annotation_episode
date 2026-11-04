"""Engineering MACS2 form boundaries, without native work or receipt claims.

The presentation fixture supplies literal native-format examples, not an
authenticated producer. These controls exercise the real closed-schema,
semantic-reference, scientific projection and frozen-value validators only.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from gene_annotation_episode import macs2_peak_components as components
from gene_annotation_episode import macs2_peak_result_contracts as contracts
from gene_annotation_episode import macs2_peak_result_worker as worker
from gene_annotation_episode import native_macs2_peak_execution as native
from gene_annotation_episode.communication import (
    ReportBoundaryError, validate_closed_schema, validate_form,
)
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.state import Store
from test_macs2_peak_presentation import SOURCE, _packet


def _forbidden(*args, **kwargs):
    raise AssertionError('typed return validation attempted private or scientific work')


@pytest.fixture(autouse=True)
def no_scientific_or_private_work(monkeypatch):
    monkeypatch.setattr(Store, 'get_artifact', _forbidden)
    for name in ('prepare_local_macs2_peak', 'run_macs2_peak'):
        monkeypatch.setattr(native, name, _forbidden)
    monkeypatch.setattr(worker, 'run_macs2_peak_result_job', _forbidden)
    for name in ('build_macs2_peak_components', 'native_peak_counts', 'project_native_peak_window'):
        monkeypatch.setattr(components, name, _forbidden)
    for name in ('project_macs2_peak_values', 'native_peak_counts', 'project_native_peak_window'):
        monkeypatch.setattr(contracts, name, _forbidden)
    monkeypatch.setattr('socket.create_connection', _forbidden)


def _schema(*fields):
    fields = fields or ('peaks',)
    registered = contracts.macs2_peak_fact_sources()[contracts.FACT_SOURCE]['report_schema']
    return dict(type='object', properties={field: deepcopy(registered) for field in fields},
        required=list(fields), additionalProperties=False)


def _references(form, schema):
    # This is the production reference-projection method in isolation. It does
    # not construct a binding, receive references or claim producer authority.
    return ScientificProcessEpisodes.received_form_references(
        SimpleNamespace(), object(), form, schema, 'engineering-projection')


@pytest.mark.parametrize('length', [0, 1, 2])
def test_exact_registered_macs2_form_accepts_owned_schema_and_only_source_semantics(length):
    schema = _schema()
    form = dict(peaks=[_packet() for _ in range(length)])
    before = canonical(dict(schema=schema, form=form))
    resolved = []

    def resolver(reference, namespace):
        resolved.append((reference, namespace))
        return (reference, namespace) == (SOURCE, 'source')

    assert validate_closed_schema(schema) == schema
    assert validate_form(form, schema, resolver) == form
    assert resolved == [(SOURCE, 'source')] * length
    assert canonical(dict(schema=schema, form=form)) == before
    if length:
        row = form['peaks'][0]
        assert row['peak_window']['rows'][1]['row']['display_score'] == 1045
        assert row['reported_numbers']['control_redundant_rate']['value'] == 0.0
        assert row['reported_numbers']['pvalue_cutoff']['value'] is None
        assert row['peak_window']['rows'][0]['row']['start1'] == 2910
        assert row['peak_window']['rows'][1]['row']['start0'] == 2909


@pytest.mark.parametrize('fault', ['version', 'missing_id', 'extra_constraint', 'reference_namespace', 'nested'])
def test_counterfeit_or_nested_macs2_schema_is_rejected(fault):
    schema = _schema()
    node = schema['properties']['peaks']
    if fault == 'version':
        node['$defs']['Macs2PeakReturn']['properties']['version']['const'] = 'counterfeit'
    elif fault == 'missing_id':
        del node['$id']
    elif fault == 'extra_constraint':
        node['minItems'] = 0
    elif fault == 'reference_namespace':
        node['$defs']['Macs2PeakReturn']['properties']['source_ref']['x-reference-namespace'] = 'artifact'
    else:
        schema = dict(type='object', properties={'nested': schema}, required=['nested'], additionalProperties=False)
    with pytest.raises(ReportBoundaryError) as caught:
        validate_closed_schema(schema)
    assert caught.value.diagnostic['code'] == 'invalid_schema'


@pytest.mark.parametrize('fault', [
    'boolean_count', 'float_count', 'boolean_ordinal', 'float_ordinal',
    'boolean_offset', 'float_offset', 'missing_number', 'extra_private_file', 'null_source',
])
def test_malformed_and_integer_impostor_macs2_values_fail_before_resolver(fault):
    packet = _packet()
    if fault in ('boolean_count', 'float_count'):
        packet['native_peak_counts'][0]['count'] = True if fault == 'boolean_count' else 1.0
    elif fault in ('boolean_ordinal', 'float_ordinal'):
        packet['peak_window']['rows'][0]['row']['row_ordinal'] = False if fault == 'boolean_ordinal' else 0.0
    elif fault in ('boolean_offset', 'float_offset'):
        packet['peak_window']['row_window']['offset'] = False if fault == 'boolean_offset' else 0.0
    elif fault == 'missing_number':
        del packet['reported_numbers']['d_bp']
    elif fault == 'extra_private_file':
        packet['private_file'] = dict(artifact_ref='artifact_' + 'c' * 64)
    else:
        packet['source_ref'] = None
    resolved = []
    with pytest.raises(ReportBoundaryError) as caught:
        validate_form(dict(peaks=[packet]), _schema(), lambda *args: resolved.append(args) or True)
    assert caught.value.diagnostic == dict(category='report_format',
        code='macs2_peak_return_invalid', field='peaks')
    assert resolved == []


def test_unavailable_source_is_rejected_without_resolving_opaque_native_identities():
    resolved = []
    with pytest.raises(ReportBoundaryError) as caught:
        validate_form(dict(peaks=[_packet()]), _schema(), lambda *args: resolved.append(args) or False)
    assert resolved == [(SOURCE, 'source')]
    assert caught.value.diagnostic['code'] == 'unknown_reference'
    assert caught.value.diagnostic['field'] == 'report.peaks[0].source_ref'


def test_scientific_reference_hook_projects_only_unique_result_sources():
    packet = _packet()
    schema = _schema('first', 'second')
    form = dict(first=[packet, deepcopy(packet)], second=[deepcopy(packet)])
    before = canonical(form)
    assert _references(form, schema) == [SOURCE]
    assert canonical(form) == before
    # Provenance contains a real-looking Artifact id, but it is not a File
    # receipt or an independently delivered native Source.
    assert packet['peak_window']['rows'][0]['source']['artifact_ref'] != SOURCE


@pytest.mark.parametrize('fault', ['not_array', 'bad_row', 'forged_schema'])
def test_scientific_reference_hook_validates_before_projecting(fault):
    form, schema = dict(peaks=[_packet()]), _schema()
    if fault == 'not_array':
        form['peaks'] = form['peaks'][0]
    elif fault == 'bad_row':
        form['peaks'][0]['peak_window']['rows'][0]['row']['row_ordinal'] = True
    else:
        schema['properties']['peaks']['minItems'] = 0
    with pytest.raises(ValueError):
        _references(form, schema)


def test_unrelated_scientific_reference_hook_and_frozen_report_keep_old_empty_behavior():
    schema = dict(type='object', properties={'count': {'type': 'integer'}},
        required=['count'], additionalProperties=False)
    assert _references(dict(count=0), schema) == []
    binding = SimpleNamespace(services=SimpleNamespace(molecular_frozen_facts=_forbidden))
    assert ScientificProcessEpisodes._validate_molecular_report(
        binding, object(), dict(count=0), schema) is None


def _frozen_binding(frozen, calls):
    def facts(context, *, fact_source):
        calls.append((context, fact_source))
        return deepcopy(frozen)
    return SimpleNamespace(services=SimpleNamespace(molecular_frozen_facts=facts))


def test_scientific_frozen_macs2_report_matches_original_without_private_reads():
    packet, calls, context = _packet(), [], object()
    original = canonical(packet)
    assert ScientificProcessEpisodes._validate_molecular_report(
        _frozen_binding([packet], calls), context, dict(peaks=[deepcopy(packet)]), _schema()) is None
    assert calls == [(context, contracts.FACT_SOURCE)]
    assert canonical(packet) == original


@pytest.mark.parametrize('fault', ['native_value', 'source', 'row_order', 'omitted_group', 'duplicate_group'])
def test_shape_valid_changed_macs2_facts_keep_structured_frozen_mismatch(fault):
    packet, actual, calls = _packet(), [_packet()], []
    if fault == 'native_value':
        actual[0]['peak_window']['rows'][1]['row']['display_score'] = 1046
    elif fault == 'source':
        actual[0]['source_ref'] = 'source_' + 'f' * 24
    elif fault == 'row_order':
        actual[0]['peak_window']['rows'].reverse()
    elif fault == 'omitted_group':
        actual = []
    else:
        actual.append(deepcopy(packet))
    # The numerical forgery is a valid DTO; rejection below must compare the
    # retained facts rather than merely reject its shape or integer types.
    for row in actual:
        assert contracts.validate_macs2_peak_return(row) == row
    with pytest.raises(ReportBoundaryError) as caught:
        ScientificProcessEpisodes._validate_molecular_report(
            _frozen_binding([packet], calls), object(), dict(peaks=actual), _schema())
    assert caught.value.diagnostic == dict(category='report_format',
        code='macs2_peak_frozen_source_mismatch', field='peaks')
    assert 'retained native peak measurement facts' in str(caught.value)
    assert len(calls) == 1


def test_missing_frozen_macs2_group_uses_registered_label_and_code():
    calls = []
    with pytest.raises(ReportBoundaryError) as caught:
        ScientificProcessEpisodes._validate_molecular_report(
            _frozen_binding(None, calls), object(), dict(peaks=[_packet()]), _schema())
    assert caught.value.diagnostic == dict(category='report_format',
        code='macs2_peak_facts_not_frozen', field='peaks')
    assert 'native MACS2 peak measurement facts' in str(caught.value)
    assert len(calls) == 1
