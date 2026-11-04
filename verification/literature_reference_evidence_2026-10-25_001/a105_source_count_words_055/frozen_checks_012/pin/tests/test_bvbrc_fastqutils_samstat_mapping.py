"""Native SAMstat -> provider -> saved sheet/calculators -> closed typed facts.

The HTML fixtures were actually emitted by the pinned producers. Bundle and
publication wrappers here are synthetic: no Workspace custody or Workflow proof.
Adverse byte/saved-sheet mutations are explicitly synthetic counterexamples.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import re
import socket
import subprocess

import pytest

from gene_annotation_episode import bvbrc_fastqutils_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_fastqutils_calculators import calculate_fastqutils
from gene_annotation_episode.bvbrc_fastqutils_contracts import (
    FastqUtilsContractError, bytes_sha256, json_sha256, validate_contract, validate_sheet,
    validate_requested_form,
)
from gene_annotation_episode.bvbrc_fastqutils_identity import component_ref, native_ref
from gene_annotation_episode.bvbrc_fastqutils_resolution import resolve_calculation_inputs, resolve_documents
from gene_annotation_episode.bvbrc_fastqutils_samstat_mapping import calculate_samstat_report_mapping
from gene_annotation_episode.bvbrc_fastqutils_saved_codec import validate_saved_projection
from gene_annotation_episode.bvbrc_fastqutils_returns import (
    encode_return_value, decode_return_value, parent_form_schema, project_fastqutils_return_facts,
)
from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.bvbrc_appservice_publication import RESULT_VERSION
from gene_annotation_episode.execution_contracts import canonical, digest

FIXTURES = Path(__file__).parent / 'fixtures/bvbrc_fastqutils_samstat_mapping'
spec = importlib.util.spec_from_file_location('samstat_mapping_fixture_support',
    Path(__file__).parent / 'fixtures/bvbrc_fastqutils/bundle/fixture_support.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
METRICS = ('samstat_report_mapped_record_fraction', 'samstat_report_ge30_record_fraction')


def selected(ordinal, document='report', key='samstat_report_records'):
    return f.population(document, key, ordinal)


def request(ordinals=(0,), document='report', calculation_id='mapping'):
    return dict(calculation_id=calculation_id, method='samstat_report_mapping_v1',
                populations=[selected(n, document) for n in ordinals])


def fixture_data(family='current', name='mixed.sam.samstat.html', *, ordinals=None, raw=None):
    if raw is None:
        raw = (FIXTURES / family / name).read_bytes()
    data = f.build({'report': (raw, 'samstat_html')})
    data[3]['calculation_requests'] = [request(ordinals if ordinals is not None else ((1, 2) if family == 'legacy' else (0,)))]
    return data


def fields(availability='typed_state'):
    return {name: f.selection('component', dict(selection='semantic', calculation_id='mapping',
        metric=metric, threshold=None), availability=availability) for name, metric in zip(('mapped', 'high'), METRICS)}


def components(result):
    return result['components']['calculations']['components']


def validate_saved(result, data, selected_fields):
    validate_saved_projection(result['sheet'], result['components'],
        **{k: result[k] for k in ('facts', 'status', 'missing_requirements', 'diagnostics')},
        requested_form=f.schema(selected_fields), parameters=data[3],
        original_task=data[0]['original_task'], bundle=data[0])


def calculate(sheet, req):
    parameters = resolve_calculation_inputs(sheet, requests=[req])
    return calculate_fastqutils(sheet, parameters=parameters)


def synthetic_cell_change(sheet, ref, **changes):
    for rows in [sheet['measurements']] + [d['cells'] for d in sheet['documents']]:
        for row in rows:
            if row['id'] == ref:
                row.update(deepcopy(changes))


def context_for(document):
    artifact = document['artifact']
    return dict(analysis_id=document['analysis_id'], document_id=document['document_id'],
        task_ref=artifact['task_ref'], content=artifact['content_binding'], native_name=artifact['native_name'],
        declared_format=artifact['declared_format'], producer_version=artifact['producer_version'],
        transfer_scope=artifact['transfer_scope'], identity=artifact['identity'])


def synthetic_duplicate_count(sheet):
    doc = sheet['documents'][0]
    old = next(c for c in doc['cells'] if c['metric'] == 'samstat_alignment_bin_count'
               and c['population_ref'].endswith('%2F0'))
    cell = dict(deepcopy(old), id=native_ref('cell', context_for(doc), len(doc['cells'])))
    doc['cells'].append(deepcopy(cell))
    sheet['measurements'].append(deepcopy(cell))
    next(s for s in doc['sections'] if s['key'] == cell['section_key'] and s['ordinal'] == cell['section_ordinal'])['cell_refs'].append(cell['id'])
    validate_sheet(sheet)
    return cell


@pytest.mark.parametrize('family,ordinals,expected,bins', [
    ('legacy', (1, 2), ((10, 11), (5, 11)), [5, 2, 2, 1, 10, 0, 1, 0, 0, 1]),
    ('legacy', (1,), ((9, 10), (5, 10)), [5, 2, 2, 1, 10]),
    ('legacy', (2,), ((1, 1), (0, 1)), [0, 1, 0, 0, 1]),
    ('current', (0,), ((9, 10), (4, 10)), [4, 3, 2, 1, 10]),
    ('current', (1,), ((8, 9), (4, 9)), [4, 2, 2, 1]),
    ('current', (2,), ((1, 1), (0, 1)), [0, 1, 0, 0]),
    ('current', (1, 2), ((9, 10), (4, 10)), [4, 2, 2, 1, 0, 1, 0, 0]),
])
def test_native_numerical_oracles_and_exact_operands(family, ordinals, expected, bins):
    data = fixture_data(family, ordinals=ordinals)
    original = deepcopy(data)
    result = f.run(data, fields('available_value'))
    sheet = result['sheet']
    assert result['status'] == 'ok' and data == original
    values = {c['id']: c for c in sheet['measurements']}
    calculated = result['components']['calculations']
    job = calculated['parameters']['calculations'][0]
    assert [values[ref]['value'] for ref in job['operand_measurement_refs']] == bins
    assert job['comparison_kind'] is job['read_key_rule'] is job['lineage_ref'] is job['lineage_basis'] is None
    assert job['quality_thresholds'] == []
    for row, metric, (numerator, denominator) in zip(components(result), METRICS, expected):
        assert (row['metric'], row['numerator'], row['denominator'], row['value']) == (metric, numerator, denominator, numerator / denominator)
        assert row['state'] == 'available' and row['unit'] == 'fraction'
        assert row['meaning'] == 'native_report_derived' and row['uncertainty'] == 'not_estimated'
        assert row['threshold'] is row['lineage_basis'] is row['encoding_basis'] is None
        assert row['operand_measurement_refs'] == job['operand_measurement_refs']
        assert row['population_refs'] == job['population_refs']
        assert {'samstat_input_scope_unproven', 'samstat_report_population_only', 'samstat_mapq255_merged'} <= set(row['diagnostic_codes'])
        assert row['id'] == component_ref(sheet['analysis_id'], json_sha256(sheet), json_sha256(calculated['parameters']), 'mapping', metric, None)
    doc = sheet['documents'][0]
    assert doc['artifact']['sha256'] == bytes_sha256(data[1]['artifact_report'])
    assert all(p['scope'] == 'unknown' for p in doc['populations'])
    assert not doc['sequence_records'] and not doc['alignment_records'] and not doc['reference_dictionary']
    validate_saved(result, data, fields('available_value'))


def test_legacy_native_empty_keeps_zero_bins_undefined_ratios_and_nan_tokens():
    data = fixture_data('legacy', 'empty.sam.samstat.html', ordinals=(1,))
    result = f.run(data, fields())
    for row in components(result):
        assert row['state'] == 'undefined' and row['value'] is None
        assert row['numerator'] == row['denominator'] == 0
        assert 'zero_denominator' in row['diagnostic_codes']
    native = result['sheet']['measurements']
    assert len([c for c in native if c['metric'] == 'samstat_alignment_bin_count' and c['value'] == 0]) == 4
    assert all(c['native_token'] == '-nan' and c['value'] is None for c in native if c['metric'] == 'samstat_reported_bin_fraction')


@pytest.mark.parametrize('family,ordinal,count', [('legacy', 1, 10000), ('current', 0, 10)])
def test_native_prefix_has_finite_partial_report_fraction(family, ordinal, count):
    result = f.run(fixture_data(family, 'boundaries/peek10001.sam.samstat.html', ordinals=(ordinal,)), fields())
    assert all(r['state'] == 'partial' and r['value'] == 1 and r['denominator'] == count for r in components(result))
    assert all('samstat_native_prefix' in r['diagnostic_codes'] for r in components(result))


@pytest.mark.parametrize('damage', ['transfer', 'html_suffix'])
@pytest.mark.parametrize('family,ordinals,numerator,denominator', [('legacy', (1, 2), 10, 11), ('current', (0,), 9, 10)])
def test_complete_bins_survive_partial_report(family, ordinals, numerator, denominator, damage):
    raw = (FIXTURES / family / 'mixed.sam.samstat.html').read_bytes()
    data = fixture_data(family, ordinals=ordinals, raw=raw.replace(b'</html>', b'') if damage == 'html_suffix' else raw)
    if damage == 'transfer':
        data[0]['artifacts'][0]['transfer'].update(body_complete=False, object_complete='no')
    result = f.run(data, fields())
    row = components(result)[0]
    assert row['state'] == 'partial' and row['value'] == numerator / denominator
    assert 'partial_transfer' in row['diagnostic_codes']


@pytest.mark.parametrize('damage,state', [('missing', 'truncated'), ('duplicate', 'incompatible'), ('total', 'incompatible')])
def test_native_table_damage_preserves_actual_partial_operands(damage, state):
    raw = (FIXTURES / 'current/mixed.sam.samstat.html').read_bytes()
    row = next(row for row in re.findall(rb'<tr\b[^>]*>.*?</tr>', raw, re.S)
               if b'<th scope="row">Unmapped</th>' in row)
    if damage == 'missing': raw = raw.replace(row, b'', 1)
    elif damage == 'duplicate': raw = raw.replace(row, row + row, 1)
    else: raw = raw.replace(b'<dd>10</dd>', b'<dd>11</dd>', 1)
    result = f.run(fixture_data(raw=raw), fields())
    assert all(r['state'] == state and r['value'] is None for r in components(result))
    assert components(result)[0]['operand_measurement_refs']
    assert result['sheet']['documents'][0]['artifact']['sha256'] == bytes_sha256(raw)
    restored = json.loads(canonical(result['sheet']))
    replay = calculate(restored, request())
    assert replay['components'] == components(result)
    validate_saved(result, fixture_data(raw=raw), fields())


@pytest.mark.parametrize('damage', ['duplicate', 'hidden_duplicate', 'total', 'axis', 'count_state', 'cross_artifact'])
def test_saved_count_conflicts_cannot_be_hidden_or_relabelled(damage):
    data = fixture_data()
    sheet = f.sheet_for(data)
    initial = resolve_calculation_inputs(sheet, requests=data[3]['calculation_requests'])
    if damage in ('duplicate', 'hidden_duplicate'):
        synthetic_duplicate_count(sheet)
    else:
        cell = next(c for c in sheet['measurements'] if c['metric'] == ('samstat_alignment_total_count' if damage == 'total' else 'samstat_alignment_bin_count'))
        if damage == 'total': synthetic_cell_change(sheet, cell['id'], value=12, native_token='12')
        elif damage == 'axis': synthetic_cell_change(sheet, cell['id'], axis=dict(kind='mapq', label='wrong', lower=31, upper=255))
        elif damage == 'count_state': synthetic_cell_change(sheet, cell['id'], value=None, state='malformed', diagnostic_codes=['malformed_native'])
        elif damage == 'cross_artifact':
            # A valid cell from the same native report but a different mate is
            # explicitly substituted in the hand-made binding.
            wrong = next(c for c in sheet['measurements'] if c['metric'] == 'samstat_alignment_bin_count' and c['population_ref'] != cell['population_ref'])
            initial['calculations'][0]['operand_measurement_refs'][0] = wrong['id']
    params = initial if damage in ('hidden_duplicate', 'cross_artifact') else resolve_calculation_inputs(sheet, requests=data[3]['calculation_requests'])
    result = calculate_fastqutils(sheet, parameters=params)
    assert all(r['state'] == 'incompatible' and r['value'] is None for r in result['components'])
    assert result['requirements']


def test_native_legacy_duplicate_declaration_does_not_become_plain_missing():
    raw = (FIXTURES / 'legacy/mixed.sam.samstat.html').read_bytes()
    raw = raw.replace(b'var mappingtableval', b'var mappingtableval = [];\nvar mappingtableval', 1)
    result = f.run(fixture_data('legacy', raw=raw), fields())
    assert all(r['state'] == 'incompatible' and 'selection_ambiguous' in r['diagnostic_codes'] for r in components(result))
    assert calculate(json.loads(canonical(result['sheet'])), request((1, 2)))['components'] == components(result)


@pytest.mark.parametrize('family', ['legacy', 'current'])
def test_fastx_mode_is_incompatible_not_zero_mapping(family):
    data = fixture_data(family, 'qualities.fastq.samstat.html', ordinals=(1,) if family == 'legacy' else (0,))
    result = f.run(data, fields())
    assert all(r['state'] == 'incompatible' and r['value'] is None and not r['operand_measurement_refs'] for r in components(result))


@pytest.mark.parametrize('name,metric,has_population', [
    ('empty.sam.samstat.html', 'samstat_alignment_total_count', True),
    ('empty.fastq.samstat.html', 'samstat_reported_item_count', False),
])
def test_empty_current_does_not_invent_absent_alignment_bins(name, metric, has_population):
    result = f.run(fixture_data(name=name), fields())
    doc = result['sheet']['documents'][0]
    assert doc['cells'][0]['metric'] == metric and doc['cells'][0]['value'] == 0
    assert bool(doc['populations']) is has_population
    assert not any(c['metric'] == 'samstat_alignment_bin_count' for c in doc['cells'])
    assert all(r['state'] == 'missing' and r['value'] is None for r in components(result))
    if not has_population:
        assert all('source_row_absent' in r['diagnostic_codes'] for r in components(result))


@pytest.mark.parametrize('mode', ['unknown', 'FASTQ', 'contradictory'])
def test_saved_mode_labels_are_required_even_when_counts_exist(mode):
    data = fixture_data()
    sheet = f.sheet_for(data)
    doc = sheet['documents'][0]
    label = next(r for r in doc['labels'] if r['locator']['field'] == 'input_format')
    if mode == 'unknown': label['locator']['field'] = 'unclassified_input'
    elif mode == 'FASTQ': label['value'] = 'FASTQ'
    else:
        added = dict(deepcopy(label), id=native_ref('label', context_for(doc), len(doc['labels'])), value='FASTQ')
        doc['labels'].append(added)
        next(s for s in doc['sections'] if s['key'] == added['section_key'])['label_refs'].append(added['id'])
    result = calculate(sheet, data[3]['calculation_requests'][0])
    assert all(r['state'] == ('missing' if mode == 'unknown' else 'incompatible') and r['value'] is None for r in result['components'])


@pytest.mark.parametrize('case', ['all_plus_mate', 'same_identity', 'no_disjointness', 'cross_document', 'cross_version'])
def test_selected_populations_must_be_disjoint_mates_of_one_document(case):
    data = fixture_data()
    if case in ('cross_document', 'cross_version'):
        other = (FIXTURES / ('legacy' if case == 'cross_version' else 'current') / 'mixed.sam.samstat.html').read_bytes()
        data = f.build({'report': (data[1]['artifact_report'], 'samstat_html'), 'other': (other, 'samstat_html')})
    sheet = f.sheet_for(data)
    req = request((1, 2))
    if case == 'all_plus_mate': req = request((0, 1))
    elif case == 'same_identity':
        ref = next(p['id'] for p in sheet['populations'] if p['population_key'] == 'samstat_report_records' and p['population_ordinal'] == 1)
        req['populations'][1] = dict(selection='record', record_ref=ref)
    elif case == 'no_disjointness':
        for rows in [sheet['populations']] + [d['populations'] for d in sheet['documents']]:
            for p in rows: p['disjoint_from_refs'] = []
    else: req['populations'][1] = selected(2, 'other')
    result = calculate(sheet, req)
    assert all(r['state'] == 'incompatible' and r['value'] is None for r in result['components'])


def test_missing_selected_mate_does_not_silently_use_available_one():
    data = fixture_data('legacy', 'empty.sam.samstat.html', ordinals=(1, 2))
    result = f.run(data, fields())
    assert all(r['state'] == 'missing' and r['value'] is None for r in components(result))
    assert len(components(result)[0]['population_refs']) == 1


@pytest.mark.parametrize('binding,member,member_version', [
    ('samstat_html', 'samstat_html_2_5_0', None),
    ('samstat_html_2_5_0', 'samstat_html', None),
    ('samstat_html', 'samstat_html', '2.5.0'),
])
def test_compatible_generic_and_versioned_declarations_preserve_original_binding(binding, member, member_version):
    data = fixture_data()
    data[3]['documents'][0]['format'] = binding
    data[0]['artifacts'][0]['declared_format'].update(format=member, version=member_version)
    result = f.run(data, fields())
    assert result['sheet']['documents'][0]['artifact']['declared_format'] == binding
    assert result['sheet']['documents'][0]['artifact']['producer_version'] == '2.5.0'
    assert components(result)[0]['value'] == .9
    validate_saved(result, data, fields())


@pytest.mark.parametrize('case', ['two_formats', 'two_versions', 'format_version', 'requested_version'])
def test_conflicting_member_declarations_are_incompatible(case):
    data = fixture_data()
    member = data[0]['artifacts'][0]
    member['declared_format'].update(format='samstat_html_2_5_0', version='2.5.0')
    if case in ('two_formats', 'two_versions'):
        other = deepcopy(member)
        other['declared_format'].update(format='samstat_html_2_2_3' if case == 'two_formats' else 'samstat_html', version='2.2.3')
        data[0]['artifacts'].append(other)
    elif case == 'format_version': member['declared_format']['version'] = '2.2.3'
    else: data[3]['documents'][0]['producer_version'] = '2.2.3'
    contexts, resolutions, requirements = resolve_documents(data[0], artifact_bytes=data[1], parameters=data[3])
    assert contexts == [] and resolutions[0]['state'] == 'incompatible'
    assert requirements[0]['required_data'] == 'native_version'
    result = f.run(data, fields())
    assert all(r['state'] == 'incompatible' and 'unsupported_version' in r['diagnostic_codes'] for r in components(result))
    assert requirements[0]['id'] in result['components']['calculations']['parameters']['calculations'][0]['requirement_refs']
    validate_saved(result, data, fields())


def test_missing_artifact_keeps_resolution_reason_without_zero_bins():
    data = fixture_data()
    data[1].clear()
    result = f.run(data, fields())
    assert not result['sheet']['documents']
    assert all(r['state'] == 'missing' and r['value'] is None and 'missing_artifact' in r['diagnostic_codes'] for r in components(result))
    assert any(r['code'] == 'missing_artifact' and r['required_data'] == 'complete_native_bytes'
               for r in result['components']['calculations']['requirements'])
    validate_saved(result, data, fields())


@pytest.mark.parametrize('claim', ['format', 'version'])
def test_member_constraint_is_checked_against_actual_bytes(claim):
    data = fixture_data()
    data[0]['artifacts'][0]['declared_format'].update(
        format='samstat_html_2_2_3' if claim == 'format' else 'samstat_html', version='2.2.3' if claim == 'version' else None)
    result = f.run(data, fields())
    doc = result['sheet']['documents'][0]
    assert doc['artifact']['declared_format'] == 'samstat_html'
    assert doc['artifact']['actual_format'] == 'unknown' and doc['parse_scope'] == 'unsupported'
    assert not doc['cells'] and {'2.2.3', '2.5.0'} <= {r['value'] for r in doc['labels']}
    assert all(r['state'] == 'incompatible' for r in components(result))
    validate_saved(result, data, fields())


@pytest.mark.parametrize('damage', ['member_version', 'extra_conflicting_member', 'recognized_version', 'fake_error'])
def test_saved_declaration_and_recognition_tampering_rejected(damage):
    data = fixture_data()
    result = f.run(data, fields())
    validate_saved(result, data, fields())
    if damage == 'member_version': data[0]['artifacts'][0]['declared_format']['version'] = '2.2.3'
    elif damage == 'extra_conflicting_member':
        other = deepcopy(data[0]['artifacts'][0]); other['declared_format']['format'] = 'samstat_html_2_2_3'
        data[0]['artifacts'].append(other)
    else:
        artifact = result['sheet']['documents'][0]['artifact']
        if damage == 'recognized_version': artifact['producer_version'] = '2.2.3'
        else: artifact['actual_format'] = 'samstat_bvbrc_error_html'
        result['components']['calculations']['sheet_sha256'] = json_sha256(result['sheet'])
    with pytest.raises(FastqUtilsContractError):
        validate_saved(result, data, fields())


@pytest.mark.parametrize('cardinality,count', [('one_target', 1), ('exact_rows', 0), ('exact_rows', 2)])
def test_absent_caller_measurement_keeps_actual_failure_cause(cardinality, count):
    data = fixture_data(raw=(FIXTURES / 'caller_error.html').read_bytes())
    selector = f.measurement('report', 'samstat_alignment_bin_count', 'samstat_mapping', axis=dict(kind='all'))
    selected_fields = {'absent': f.selection('measurement', selector, cardinality=cardinality, count=count)}
    result = f.run(data, selected_fields)
    fact = result['facts']['absent']
    assert fact['matched_count'] == 0 and 'samstat_caller_failure' in fact['diagnostic_codes']
    referenced = [r for r in result['components']['native_requirements'] if r['id'] in fact['requirement_refs']]
    assert referenced and all(r['required_data'] == 'native_execution_evidence' for r in referenced)
    assert not result['sheet']['populations']
    validate_saved(result, data, selected_fields)


def test_svg_absence_is_scoped_to_actual_plot_arrays():
    data = fixture_data(name='mixed60.sam.samstat.html')
    selected_fields = {
        'array': f.selection('measurement', f.measurement('report', 'samstat_base_A_count', 'samstat_base_start', axis=dict(kind='all'))),
        'array_zero': f.selection('measurement', f.measurement('report', 'samstat_base_A_count', 'samstat_base_start', axis=dict(kind='all')), cardinality='exact_rows', count=0),
        'uniform_absent': f.selection('measurement', f.measurement('report', 'samstat_uniform_length', 'samstat_length')),
        'category_empty': f.selection('category', dict(selection='semantic', document_id='report', section_key='samstat_mapping', section_ordinal=0), cardinality='exact_rows', count=0),
        'metadata_absent': f.selection('association', dict(selection='semantic', document_id='report', input_pointer='/paired_end_libs/0', recipe_ordinal=0, mate='combined', branch='clean')),
        'wrong_section': f.selection('measurement', f.measurement('report', 'samstat_base_A_count', 'samstat_summary', axis=dict(kind='all'))),
    }
    result = f.run(data, selected_fields)
    for name in ('array', 'array_zero'):
        fact = result['facts'][name]
        assert 'samstat_svg_values_not_retained' in fact['diagnostic_codes'] and fact['requirement_refs']
    assert result['facts']['array_zero']['state'] == 'missing_value'
    assert result['facts']['category_empty']['state'] == 'satisfied'
    for name in ('uniform_absent', 'category_empty', 'metadata_absent', 'wrong_section'):
        assert 'samstat_svg_values_not_retained' not in result['facts'][name]['diagnostic_codes']
    validate_saved(result, data, selected_fields)


def test_saved_recalculation_and_typed_returns_without_science_or_io(monkeypatch):
    data = fixture_data()
    selected_fields = fields()
    result = f.run(data, selected_fields)
    original = canonical(result)
    old_parameters = deepcopy(result['components']['calculations']['parameters'])
    old_components = deepcopy(components(result))
    # The publication envelope is synthetic; every scientific field originates
    # in consume_bundle above, not a precompleted or mocked provider response.
    def content(value, source=None):
        sha = digest(value)
        return dict(source_ref=source or 'source_' + sha[:24], artifact_field='artifact_ref',
                    artifact_ref='artifact_' + sha, sha256=sha, byte_count=len(canonical(value).encode()))
    selector = f.oracle('RESULT_SELECTOR_PRE_DOWNLOAD_002.json')
    selector.update(requested_schema=f.schema(selected_fields), adapter=dict(adapter_id='bvbrc_fastqutils', adapter_version='2', parameters=data[3]))
    data[0]['requested_selector_sha256'] = digest(selector)
    saved = {k: deepcopy(result[k]) for k in ('adapter_id', 'adapter_version', 'status', 'facts', 'missing_requirements', 'diagnostics')}
    saved.update(sheet_content=content(result['sheet']), components_content=content(result['components']))
    source = 'source_' + digest(data[0])[:24]
    body = dict(version=RESULT_VERSION, source_ref=source, reference=source, record_refs=[source], assignment=dict(selector=selector),
        publication_inputs=dict(selector=selector, adapter=selector['adapter'], adapter_implementation_sha256=adapter.implementation_sha256()),
        bundle=data[0], publication=dict(bundle_content=content(data[0], source), result_record_refs=[source], adapter_result=saved))
    # Host schema requires UUIDs, so build them before storing the bundle hash.
    import uuid
    for member in data[0]['artifacts']:
        ident = str(uuid.uuid5(uuid.NAMESPACE_URL, member['workspace_object']['path']))
        member['workspace_object']['uuid'] = member['task_association']['output_uuid'] = ident
    body['publication']['bundle_content'] = content(data[0], source)
    expected = project_fastqutils_return_facts(body, requested_sources=('bvbrc_fastqutils_components',), sheet=result['sheet'], components=result['components'])
    schema = parent_form_schema(validate_requested_form(selector['requested_schema']))
    validate_form({key: expected[node['x-source']] for key, node in schema['properties'].items()}, schema, lambda *_: True)
    for fact in result['facts'].values():
        assert decode_return_value('component', encode_return_value('component', fact)) == fact
    def forbid(*args, **kwargs): raise AssertionError('saved calculation/return attempted parsing, source access or acquisition')
    monkeypatch.setattr('builtins.open', forbid)
    monkeypatch.setattr(Path, 'open', forbid)
    monkeypatch.setattr(socket, 'socket', forbid)
    monkeypatch.setattr(subprocess, 'Popen', forbid)
    for module_name, names in {
        'bvbrc_fastqutils_bundle_adapter': ('parse_fastqutils_artifact', 'populate_fastqutils_sheet', 'consume_bundle'),
        'bvbrc_fastqutils_native': ('parse_fastqutils_artifact',),
        'bvbrc_fastqutils_samstat_native': ('parse_samstat_html',),
        'bvbrc_fastqutils_samstat_svg': ('parse_samstat_html_2_5_0',),
        'bvbrc_fastqutils_samstat_legacy': ('parse_samstat_html_2_2_3',),
    }.items():
        module = __import__('gene_annotation_episode.' + module_name, fromlist=['unused'])
        for name in names: monkeypatch.setattr(module, name, forbid)
    restored = json.loads(canonical(result['sheet']))
    assert calculate_fastqutils(restored, parameters=old_parameters)['components'] == old_components
    later = calculate(restored, request((1,)))
    assert [r['value'] for r in later['components']] == [8 / 9, 4 / 9]
    assert {r['parameter_sha256'] for r in later['components']}.isdisjoint(r['parameter_sha256'] for r in old_components)
    assert canonical(result) == original
    # Return replay must not even invoke the numerical calculator.
    monkeypatch.setattr('gene_annotation_episode.bvbrc_fastqutils_calculators.calculate_fastqutils', forbid)
    assert project_fastqutils_return_facts(body, requested_sources=('bvbrc_fastqutils_components',), sheet=result['sheet'], components=result['components']) == expected


@pytest.mark.parametrize('change', ['hash', 'method', 'lineage', 'reference', 'threshold'])
def test_leaf_rejects_invalid_call_contracts(change):
    data = fixture_data()
    sheet = f.sheet_for(data)
    params = resolve_calculation_inputs(sheet, requests=data[3]['calculation_requests'])
    job = params['calculations'][0]
    sha = json_sha256(params)
    if change == 'hash': sha = 'bad'
    elif change == 'method': job['method'] = 'mapping_v1'
    elif change == 'lineage': job['lineage_ref'] = 'invented'
    elif change == 'reference': job['population_refs'][0] = 'invented'
    else: job['quality_thresholds'] = [30]
    with pytest.raises(FastqUtilsContractError):
        calculate_samstat_report_mapping(sheet, job=job, parameters_sha256=sha)
