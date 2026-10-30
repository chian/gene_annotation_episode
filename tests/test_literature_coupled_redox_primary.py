"""Check retained primary-paper conversions; no model/native episode claims."""
import builtins
import hashlib
import json
import math
from pathlib import Path

from gene_annotation_episode.literature_rate_bound_calculations import populate_rate_table_bounds
from gene_annotation_episode.literature_rate_reader import read_rate_table
from gene_annotation_episode.literature_optical_validation import validate_optical_selection


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT/'verification/literature_reference_evidence_2026-10-25_001/coupled_redox_case_093'
DATA = CASE/'generation_002'


def load(name):
    return json.loads((DATA/name).read_text())


def test_all_mapped_rows_preserve_actual_primary_byte_custody_and_distinct_temperature():
    custody = load('PRIMARY_TABLE_CUSTODY.json')
    primary = (ROOT/custody['source_path']).read_bytes()
    assert hashlib.sha256(primary).hexdigest() == custody['source_sha256']
    for row in custody['rows']:
        for name in ('mixture_cell','value_cell','assay_heading'):
            witness = row[name]['witness']
            assert primary[witness['start']:witness['end']].decode() == witness['quote']
    assert len(custody['rows']) == 21
    parenthetical, = [row for row in custody['rows'] if row['parenthetical']]
    assert parenthetical['temperature_C'] == 37
    assert parenthetical['printed_marker'] == 'a'
    assert parenthetical['value_cell']['text'] == '7 (14)a'
    assert all(row['sampling_count'] is None for row in custody['rows'])
    assert custody['table_rows_are_reported_summaries_not_raw_replicates']


def test_actual_mapped_table_reader_reproduces_retained_operand_records():
    data = load('RATE_EXTRACTION.json'); custody = load('PRIMARY_TABLE_CUSTODY.json')
    text = (DATA/'MAPPED_TABLE.tsv').read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == custody['mapped_table_sha256']
    first = data['rows'][0]['source']
    result = read_rate_table(dict(source_ref=first['source_ref'],artifact_ref=first['artifact_ref'],
        text=text,representation='retained_extraction',delimiter='\t'),
        expected_subject=data['subject'],expected_experiment=data['experiment'])
    assert result == data
    assert {row['endpoint'] for row in data['rows']} == {'NADH oxidation','TTC reduction','H2 formation'}
    assert all(row['uncertainty']['count'] is None for row in data['rows'])


def test_detached_primary_rate_bounds_reconstruct_without_file_or_source_acquisition(monkeypatch):
    comparisons = load('POPULATED_CONTRASTS.json')
    data = load('RATE_EXTRACTION.json')
    def forbidden(*args,**kwargs):raise AssertionError('unexpected reacquisition')
    monkeypatch.setattr(builtins,'open',forbidden)
    for result in comparisons.values():
        expected = result['constraint']; selection = expected['comparison']
        assert populate_rate_table_bounds(data, **{key:selection[key] for key in (
            'reference_arm','test_arm','reference_condition','test_condition')}) == expected
    nadh = comparisons['nadh_crotonyl_omission']['constraint']['cells']
    assert math.isclose(nadh['rate_difference']['lower'],6.99) and not nadh['rate_difference']['lower_closed']
    assert math.isclose(nadh['fractional_decrease']['lower'],699/700) and not nadh['fractional_decrease']['lower_closed']
    assert comparisons['ttc_crotonyl_omission']['constraint']['cells']['fractional_decrease']['value'] == .95
    assert math.isclose(comparisons['h2_crotonyl_omission']['constraint']['cells']['fractional_decrease']['lower'],.998)


def test_actual_optical_partial_validates_detached_without_reading_or_recalculating(monkeypatch):
    import gene_annotation_episode.literature_optical_inputs as inputs
    import gene_annotation_episode.literature_optical_calculations as calculations
    result = load('OPTICAL_PARTIAL.json')
    def forbidden(*args,**kwargs):raise AssertionError('unexpected source read or recalculation')
    monkeypatch.setattr(builtins,'open',forbidden)
    monkeypatch.setattr(inputs,'read_optical_rate_operands',forbidden)
    monkeypatch.setattr(calculations,'calculate_nadh_optical_rate',forbidden)
    assert validate_optical_selection(result['selection'],result['extraction']) == result['selection']
    assert result['extraction']['calibration']['epsilon']['value'] == 6.2
    assert result['extraction']['calibration']['epsilon']['source_origin'] == 'reported'
    assert result['cells']['net_depletion_rate']['value'] is None
    assert result['calibration_recovery'] is result['path_length'] is None


def test_same_temperature_rates_for_different_readouts_do_not_become_a_stoichiometry_grade():
    result = load('CROSS_ENDPOINT_LIMIT.json')
    assert result['cells']['reference_rate']['value'] == 14
    assert result['cells']['test_rate']['value'] == 5
    assert result['cells']['retained_fraction']['value'] is None
    assert result['cells']['retained_fraction']['unavailable_reason'] == 'endpoint_mismatch'
    assert result['annotation_credit'] is None
