"""Native p3-sra metadata and pure saved-result paths; no live service claim."""
from copy import deepcopy
import importlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.bvbrc_fastqutils_contracts import (
    FastqUtilsContractError, _definition_closure, _LEGACY_CUTADAPT_DEFS,
    canonical_json, make_requested_schema, validate_requested_form,
)
from gene_annotation_episode.bvbrc_fastqutils_native import parse_fastqutils_artifact
from gene_annotation_episode.bvbrc_fastqutils_returns import (
    FACT_SOURCES, decode_return_value, project_fastqutils_return_facts,
)
from gene_annotation_episode.bvbrc_fastqutils_sra_native import parse_sra_metadata
from gene_annotation_episode.bvbrc_fastqutils_sra_specs import SRA_FIELDS
from test_bvbrc_fastqutils_report_formats import context
from test_bvbrc_fastqutils_provider import f
from test_bvbrc_fastqutils_returns import saved_fixture

FIXTURES = Path(__file__).parent / 'fixtures/bvbrc_fastqutils/sra'


def parse(raw, **kwargs):
    return parse_fastqutils_artifact(raw, context=context(raw, 'sra_metadata', **kwargs))


def one(doc, metric):
    rows = [r for r in doc['cells'] if r['metric'] == metric]
    assert len(rows) == 1
    return rows[0]


def test_real_source_output_preserves_quantities_and_native_field_spans():
    raw = (FIXTURES / 'native_selected_run.json').read_bytes()
    doc = parse(raw, identity='supplied_native_artifact')
    assert doc['parse_scope'] == 'complete'
    assert {r['metric']: r['value'] for r in doc['cells']} == {
        'sra_reported_total_bases': 2673129532,
        'sra_reported_total_spots': 35172757,
        'sra_reported_archive_bytes': 937094000,
        'sra_reported_read_length': 76.0,
        'sra_reported_read_types_per_spot': 1,
    }
    assert all(p['scope'] == 'unknown' for p in doc['populations'])
    assert not doc['native_lineage'] and not doc['sequence_records']
    labels = {r['locator']['field']: r['value'] for r in doc['labels']}
    assert labels['run_id'] == labels['accession'] == 'SRR6263255'
    assert labels['exp_id'] == 'SRX3369480'
    assert labels['sample_id'] == 'SRS2667047'
    assert labels['study_id'] == 'SRP124452'
    for cell in doc['cells']:
        loc = cell['locator']
        assert raw[loc['byte_start']:loc['byte_end']].decode() == cell['native_token']
    assert 'sra_read_types_basis_unproven' in one(doc, 'sra_reported_read_types_per_spot')['diagnostic_codes']
    assert 'sra_read_length_basis_unproven' in one(doc, 'sra_reported_read_length')['diagnostic_codes']
    assert doc['artifact']['producer_version'] is None


@pytest.mark.parametrize('name', ['native_selected_run', 'native_all_returned_runs',
    'missing_statistics_and_layout', 'missing_first_size_attribute',
    'reported_zeros', 'two_rows_same_experiment'])
def test_every_source_executed_case_keeps_each_original_rows_quantities(name):
    raw = (FIXTURES / (name + '.json')).read_bytes()
    original = json.loads(raw)
    doc = parse(raw, identity='supplied_native_artifact' if name.startswith('native_') else 'source_executed_synthetic')
    assert len(doc['populations']) == len(original)
    for index, row in enumerate(original):
        values = {c['metric']: c['value'] for c in doc['cells'] if c['section_ordinal'] == index}
        assert values == {SRA_FIELDS[k][0]: v for k, v in row.items() if k in SRA_FIELDS}
        labels = {r['locator']['field']: r['value'] for r in doc['labels'] if r['section_ordinal'] == index}
        assert labels['run_id'] == row['run_id']
        assert labels['sample_id'] == row['sample_id']
    assert 'estimated_size' not in {r['locator']['field'] for r in doc['cells']}


@pytest.mark.parametrize('token,state,value', [
    ('0', 'available', 0), ('-1', 'malformed', None), ('1.0', 'malformed', None),
    ('true', 'malformed', None), ('"3"', 'malformed', None),
    ('null', 'not_measured', None), ('NaN', 'malformed', None),
    ('[]', 'malformed', None), ('{}', 'malformed', None),
    ('9223372036854775808', 'malformed', None),
])
def test_counter_types_do_not_turn_categories_or_missingness_into_measurements(token, state, value):
    raw = ('[{"run_id":"R","accession":"R","total_spots":' + token + '}]').encode()
    cell = one(parse(raw), 'sra_reported_total_spots')
    assert (cell['state'], cell['value']) == (state, value)
    assert cell['native_token'] == token


def test_missing_counter_is_absent_not_a_zero_or_synthesized_size():
    doc = parse(b'[{"run_id":"R","accession":"R","n_reads":1}]')
    assert [r['metric'] for r in doc['cells']] == ['sra_reported_read_types_per_spot']


def test_duplicate_numeric_key_is_malformed_but_text_duplicates_and_siblings_are_retained():
    raw = b'[{"run_id":"R","accession":"R","sample_id":"A","sample_id":"B","total_spots":2,"total_spots":3,"size":10}]'
    doc = parse(raw)
    assert one(doc, 'sra_reported_total_spots')['state'] == 'malformed'
    assert one(doc, 'sra_reported_archive_bytes')['value'] == 10
    assert [r['value'] for r in doc['labels'] if r['locator']['field'] == 'sample_id'] == ['A', 'B']
    assert any(r['code'] == 'metadata_value_conflict' for r in doc['diagnostics'])


def test_malformed_bounded_sibling_does_not_erase_valid_run():
    raw = b'[{bad}, {"run_id":"R","accession":"R","total_bases":10}]'
    doc = parse(raw)
    assert doc['parse_scope'] == 'partial'
    assert one(doc, 'sra_reported_total_bases')['value'] == 10
    assert one(doc, 'sra_reported_total_bases')['section_ordinal'] == 1


def test_prefix_preserves_complete_first_row_without_inventing_tail():
    raw = b'[{"run_id":"R","accession":"R","total_bases":10}, {"run_id":'
    doc = parse(raw, scope='partial')
    assert doc['parse_scope'] == 'partial'
    assert one(doc, 'sra_reported_total_bases')['state'] == 'partial'
    assert len(doc['populations']) == 1


def test_unicode_locations_arrays_and_contradictory_identity():
    raw = json.dumps([dict(run_id='R', accession='different', sample_description='βμ',
        files=['R_1.fastq', 'R_2.fastq'], study_BioProject_ids=['X','Y'], total_bases=7)],
        ensure_ascii=False).encode()
    doc = parse(raw)
    cell = one(doc, 'sra_reported_total_bases')
    assert raw[cell['locator']['byte_start']:cell['locator']['byte_end']] == b'7'
    assert [r['value'] for r in doc['labels'] if r['locator']['field'].startswith('files/')] == ['R_1.fastq','R_2.fastq']
    codes = {r['code'] for r in doc['diagnostics']}
    assert {'metadata_value_conflict','sra_file_association_unproven',
            'sra_cross_reference_association_unproven'} <= codes
    assert all(p['association_ref'] is None for p in doc['populations'])


def test_duplicate_run_names_are_separate_rows_not_deduplicated():
    row = dict(run_id='R', accession='R', total_bases=5)
    doc = parse(json.dumps([row,row]).encode())
    assert len(doc['populations']) == 2 and len(doc['cells']) == 2
    assert len({r['id'] for r in doc['cells']}) == 2


def test_unknown_objects_remain_raw_and_never_become_stringified_labels():
    doc = parse(b'[{"run_id":"R","accession":"R","extra":{"secret":"value"},"total_bases":1}]')
    assert one(doc, 'sra_reported_total_bases')['value'] == 1
    assert all(r['locator']['field'] != 'extra' for r in doc['labels'])
    assert any(r['code'] == 'unsupported_report_section' for r in doc['diagnostics'])


def test_claimed_version_does_not_establish_deployed_producer():
    doc = parse(b'[{"run_id":"R","accession":"R","size":1}]', version='made-up-version')
    codes = {r['code'] for r in doc['diagnostics']}
    assert {'producer_version_unproven','supplied_version_assumption'} <= codes


def test_content_mismatch_raises_before_parsing():
    raw=b'[]';ctx=context(raw,'sra_metadata')
    with pytest.raises(FastqUtilsContractError, match='binding_conflict'):
        parse_sra_metadata(b'[{}]',context=ctx)


def test_provider_and_saved_return_preserve_metadata_and_numbers_without_reacquisition(monkeypatch):
    raw=(FIXTURES/'native_selected_run.json').read_bytes()
    data=f.build({'sra':(raw,'sra_metadata')})
    fields={name:f.selection('measurement',f.measurement('sra', metric,'sra_run'),
        availability='available_value') for name,(metric,*_) in SRA_FIELDS.items()}
    fields['requirements']=f.selection('requirements')
    result=f.run(data,fields)
    assert result['status']=='ok'
    assert [result['facts'][k]['records'][0]['payload']['value'] for k in SRA_FIELDS] == [2673129532,35172757,937094000,76.0,1]
    assert result['sheet']['documents'][0]['labels']
    body,sheet,components=saved_fixture(data,fields)
    expected=project_fastqutils_return_facts(body,requested_sources=FACT_SOURCES,sheet=sheet,components=components)
    attempts=[]
    def forbidden(*args,**kwargs):
        attempts.append(True)
        raise AssertionError('saved return reacquired or recomputed')
    for suffix in ('native','sra_native','metadata','sheet','calculators'):
        module=importlib.import_module('gene_annotation_episode.bvbrc_fastqutils_'+suffix)
        for name,value in vars(module).copy().items():
            if callable(value) and name.startswith(('parse_','extract_','populate_','calculate_')):
                monkeypatch.setattr(module,name,forbidden)
    monkeypatch.setattr('socket.socket.connect',forbidden)
    monkeypatch.setattr('subprocess.Popen',forbidden)
    actual=project_fastqutils_return_facts(body,requested_sources=FACT_SOURCES,sheet=sheet,components=components)
    assert actual==expected and not attempts
    values=[decode_return_value('measurement',r['value'])['records'][0]['payload']['value']
        for r in actual['bvbrc_fastqutils_measurements']]
    assert values == [2673129532,35172757,937094000,76.0,1]


def test_exact_cutadapt_generation_remains_valid_but_cannot_select_new_sra_metrics():
    field=f.selection('measurement',f.measurement('trim','cutadapt_processed_count','cutadapt_summary'))
    form={'version':'fastqutils_projection_v2','fields':[dict(field='count',selection=field)]}
    schema=make_requested_schema(form)
    old=deepcopy(schema);old['$defs']=_definition_closure('ProjectedField',_LEGACY_CUTADAPT_DEFS)
    before=canonical_json(old)
    assert validate_requested_form(old)==form and canonical_json(old)==before
    target=old['properties']['count']['x-bvbrc-fastqutils']['target']['selector']
    target.update(metric='sra_reported_total_spots',section_key='sra_run')
    with pytest.raises(FastqUtilsContractError,match='requested_form_invalid'):
        validate_requested_form(old)
