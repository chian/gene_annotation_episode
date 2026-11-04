"""Actual native bytes through provider and pure return codecs, not host custody."""
import importlib
from pathlib import Path

import pytest

from gene_annotation_episode.bvbrc_fastqutils_contracts import canonical_json, validate_requested_form
from gene_annotation_episode.bvbrc_fastqutils_returns import (
    BVBRCFastqUtilsReturns, FACT_SOURCES, decode_return_value, parent_form_schema,
    project_fastqutils_return_facts,
)
from gene_annotation_episode.communication import validate_form
from test_bvbrc_fastqutils_returns import saved_fixture
from test_bvbrc_fastqutils_provider import f

_NATIVE_RELATIVE = Path('verification/tool_graders_bvbrc_fastqutils_remaining_formats_2026-10-25_204/native_examples_001/trimgalore_single')
ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / _NATIVE_RELATIVE / 'synthetic.fastq_trimming_report.txt').is_file())
NATIVE = ROOT / _NATIVE_RELATIVE


def fixture(report_bytes=None):
    native = (NATIVE / 'synthetic.fastq_trimming_report.txt').read_bytes() if report_bytes is None else report_bytes
    data = f.build({'trim': (native, 'trim_galore_report_0_6_10'),
                    'final': ((NATIVE / 'synthetic_trimmed.fq').read_bytes(), 'fastq')})
    original = data[0]['original_task']['submitted_parameters']
    original.update(recipe=['TRIM'], paired_end_libs=[], single_end_libs=[{'read': '/synthetic/input.fastq'}], srr_libs=[])
    data[3]['calculation_requests'] = [{
        'calculation_id': 'cutadapt_bases', 'method': 'retention_v1',
        'comparison_kind': 'native_report_retention',
        'before_population': f.population('trim', 'cutadapt_input_bases'),
        'after_population': f.population('trim', 'cutadapt_output_bases'),
        'before_measurement': f.measurement('trim', 'cutadapt_processed_bases', 'cutadapt_summary'),
        'after_measurement': f.measurement('trim', 'cutadapt_written_bases', 'cutadapt_summary'),
    }]
    fields = {}
    for name, doc, metric, section in (
        ('cutadapt_input_reads', 'trim', 'cutadapt_processed_count', 'cutadapt_summary'),
        ('cutadapt_output_reads', 'trim', 'cutadapt_written_count', 'cutadapt_summary'),
        ('cutadapt_output_bases', 'trim', 'cutadapt_written_bases', 'cutadapt_summary'),
        ('trimgalore_input_reads', 'trim', 'trim_processed_count', 'trim_summary'),
        ('final_reads', 'final', 'fastq_read_count', 'fastq_summary'),
        ('final_bases', 'final', 'fastq_base_count', 'fastq_summary'),
    ):
        fields[name] = f.selection('measurement', f.measurement(doc, metric, section), availability='available_value')
    fields['cutadapt_base_retention'] = f.selection('component', {
        'selection': 'semantic', 'calculation_id': 'cutadapt_bases',
        'metric': 'native_report_retention_fraction', 'threshold': None}, availability='available_value')
    fields['requirements'] = f.selection('requirements')
    return data, fields


def value(result, name):
    return result['facts'][name]['records'][0]['payload']['value']


def test_native_cutadapt_and_final_output_remain_distinct_through_provider():
    data, fields = fixture()
    before = canonical_json([data[0], data[3], fields])
    result = f.run(data, fields)
    assert result['status'] == 'ok'
    assert {name: value(result, name) for name in fields if name != 'requirements'} == {
        'cutadapt_input_reads': 4, 'cutadapt_output_reads': 4,
        'cutadapt_output_bases': 28, 'trimgalore_input_reads': 4,
        'final_reads': 3, 'final_bases': 24, 'cutadapt_base_retention': 28/58,
    }
    assert canonical_json([data[0], data[3], fields]) == before
    doc = next(d for d in result['sheet']['documents'] if d['document_id'] == 'trim')
    assert doc['artifact']['producer_name'] == 'Trim Galore'
    assert doc['artifact']['producer_version'] is None  # Caller expectation remains unknown.
    assert [r['value'] for r in doc['labels'] if r['kind'] == 'producer_version'] == ['0.6.10', '4.9']
    assert all(s['observed_state'] == 'unknown' for s in result['sheet']['stages'])
    assert all(e['task_stage_ref'] is None and e['scope'] == 'artifact_local'
               for e in result['sheet']['native_lineage'])
    assert all(d['artifact']['identity'] == 'unknown' for d in result['sheet']['documents'])


def test_native_values_reach_closed_original_parent_form_and_saved_replay(monkeypatch):
    data, fields = fixture()
    body, sheet, components = saved_fixture(data, fields)
    before = canonical_json([body, sheet, components])
    facts = project_fastqutils_return_facts(body, requested_sources=FACT_SOURCES,
                                         sheet=sheet, components=components)
    selected = body['publication_inputs']['selector']
    form = validate_requested_form(selected['requested_schema'])
    schema = parent_form_schema(form)
    returned = {name: facts[node['x-source']] for name, node in schema['properties'].items()}
    validate_form(returned, schema,
        lambda reference, namespace=None: BVBRCFastqUtilsReturns._has_reference(facts, reference, namespace))
    selected_values = []
    for row in facts['bvbrc_fastqutils_measurements']:
        decoded = decode_return_value('measurement', row['value'])
        selected_values.append(decoded['records'][0]['payload']['value'])
    assert selected_values == [4, 4, 28, 4, 3, 24]
    attempts = []
    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError('Saved Cutadapt return invoked acquisition or scientific work')
    for suffix in ('native', 'trim_reader', 'cutadapt_reader', 'fastq_reader', 'metadata',
                   'sheet', 'calculators', 'retention', 'bundle_adapter'):
        module = importlib.import_module('gene_annotation_episode.bvbrc_fastqutils_' + suffix)
        for name, function in list(vars(module).items()):
            if callable(function) and (name.startswith(('parse_', 'populate_', 'extract_', 'calculate_'))
                                      or name in ('append_cutadapt_report', 'consume_bundle')):
                monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr('socket.socket.connect', forbidden)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)
    monkeypatch.setattr('subprocess.Popen', forbidden)
    assert project_fastqutils_return_facts(body, requested_sources=FACT_SOURCES,
        sheet=sheet, components=components) == facts
    assert not attempts and canonical_json([body, sheet, components]) == before


def test_recipe_and_basename_do_not_invent_lineage_to_final_fastq():
    data, fields = fixture()
    request = data[3]['calculation_requests'][0]
    request.update(after_population=f.population('final', 'fastq_bases'),
                   after_measurement=f.measurement('final', 'fastq_base_count', 'fastq_summary'))
    fields['cutadapt_base_retention']['availability_requirement'] = 'typed_state'
    result = f.run(data, fields)
    assert value(result, 'cutadapt_base_retention') is None
    record = result['facts']['cutadapt_base_retention']['records'][0]
    assert 'lineage_asserted_only' in record['diagnostic_codes']
    assert value(result, 'final_bases') == 24


@pytest.mark.parametrize('damage', ['wrong_cutadapt_version', 'partial_transfer'])
def test_partial_or_unsupported_embedded_report_preserves_final_fastq(damage):
    raw = (NATIVE / 'synthetic.fastq_trimming_report.txt').read_bytes()
    if damage == 'wrong_cutadapt_version':
        raw = raw.replace(b'This is cutadapt 4.9', b'This is cutadapt 4.8')
    data, fields = fixture(raw)
    if damage == 'partial_transfer':
        data[0]['artifacts'][0]['transfer']['object_complete'] = 'no'
    result = f.run(data, fields)
    assert result['status'] == 'partial'
    assert value(result, 'final_reads') == 3 and value(result, 'final_bases') == 24
    assert value(result, 'cutadapt_base_retention') is None
    if damage == 'partial_transfer':
        assert value(result, 'cutadapt_output_reads') == 4
        assert result['facts']['cutadapt_output_reads']['records'][0]['state'] == 'partial'
    else:
        assert result['facts']['cutadapt_output_reads']['records'][0]['payload'] is None
        assert value(result, 'trimgalore_input_reads') == 4
