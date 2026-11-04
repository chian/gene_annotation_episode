"""Independent saved-sheet numerical oracles; no native reader is invoked."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess
import pytest
from gene_annotation_episode.bvbrc_fastqutils_contracts import FastqUtilsContractError, json_sha256, validate_contract
from gene_annotation_episode.bvbrc_fastqutils_identity import join_ref, metadata_ref
from gene_annotation_episode.bvbrc_fastqutils_retention import calculate_retention
from gene_annotation_episode.bvbrc_fastqutils_consistency import calculate_report_consistency
FIXTURES = Path(__file__).parent / 'fixtures/bvbrc_fastqutils/reports'


def saved(which='native'):
    sheet = json.loads((FIXTURES / f'saved_{which}_sheet.json').read_text())
    params = json.loads((FIXTURES / f'saved_{which}_components.json').read_text())['parameters']
    job = next(j for j in params['calculations'] if j['method'] == 'retention_v1')
    return sheet, job, params


def run(sheet, job, function=calculate_retention):
    params = {'version': 'fastqutils_calculators_v2', 'analysis_id': sheet['analysis_id'], 'calculations': [job]}
    rows = function(sheet, job=job, parameters_sha256=json_sha256(params))
    for row in rows: validate_contract('Component', row)
    return {row['metric']: row for row in rows}


def replace_cell(sheet, reference, **updates):
    for rows in [sheet['measurements']] + [d['cells'] for d in sheet['documents']]:
        for cell in rows:
            if cell['id'] == reference: cell.update(deepcopy(updates))


def replace_population(sheet, reference, **updates):
    for rows in [sheet['populations']] + [d['populations'] for d in sheet['documents']]:
        for pop in rows:
            if pop['id'] == reference: pop.update(deepcopy(updates))


def declare(sheet, job, relation):
    source = json.loads((FIXTURES / 'saved_assumed_sheet.json').read_text())['supplied_metadata'][0]
    source['value']['relation'] = relation
    for name, reference in zip(('before', 'after'), job['population_refs']):
        source['value'][name] = {'selection': 'record', 'record_ref': reference}
    sheet['supplied_metadata'].append(deepcopy(source))
    job['lineage_basis'] = {'basis': 'explicit_source_bound_declaration', 'metadata_id': source['metadata_id'],
        'evidence': deepcopy(source['evidence']), 'declaration': deepcopy(source['value']), 'native_lineage_ref': None}
    job['lineage_ref'] = None


def test_native_report_numerical_oracle_and_corrected_meanings():
    sheet, job, params = saved()
    rows = calculate_retention(sheet, job=job, parameters_sha256=json_sha256(params))
    assert {r['metric']: r['value'] for r in rows} == {'native_report_retention_fraction': .75, 'removed_count': 2, 'removed_fraction': .25}
    for row in rows:
        assert row['meaning'] == 'native_report_derived' and row['uncertainty'] == 'native_reporting_precision'
        assert row['lineage_basis'] == job['lineage_basis']
        assert row['operand_measurement_refs'] == job['operand_measurement_refs']
    assert all(s['observed_state'] == 'unknown' for s in sheet['stages'])


def test_source_bound_assumption_exact_and_no_recipe_completion():
    sheet, job, _ = saved('assumed'); original = deepcopy(sheet); rows = run(sheet, job)
    assert {r['metric']: r['value'] for r in rows.values()} == {'read_retention_fraction': .75, 'removed_count': 2, 'removed_fraction': .25}
    for row in rows.values():
        assert row['lineage_basis'] == job['lineage_basis']
        assert row['meaning'] == 'derived_descriptive' and row['uncertainty'] == 'not_estimated'
        assert 'explicit_lineage_assumption' in row['diagnostic_codes']
    assert sheet == original
    assert all(s['observed_state'] == 'unknown' for s in sheet['stages'])


def test_base_retention_actual_base_denominator():
    sheet, job, _ = saved('assumed'); selected = [m for m in sheet['measurements'] if m['metric'] == 'fastq_base_count']
    job.update(comparison_kind='base_retention', operand_measurement_refs=[m['id'] for m in selected], population_refs=[m['population_ref'] for m in selected])
    declaration = sheet['supplied_metadata'][0]['value']
    for name, pop in zip(('before', 'after'), job['population_refs']): declaration[name] = {'selection': 'record', 'record_ref': pop}
    job['lineage_basis']['declaration'] = deepcopy(declaration)
    rows = run(sheet, job)
    assert rows['base_retention_fraction']['value'] == .75 and rows['base_retention_fraction']['denominator'] == 32
    assert rows['removed_count']['value'] == 8 and rows['removed_count']['unit'] == 'bases'


def test_pair_retention_counted_pair_cells_never_halved_reads():
    sheet, job, _ = saved('assumed'); selected = []
    for i, p_ref in enumerate(job['population_refs']):
        p = deepcopy(next(p for p in sheet['populations'] if p['id'] == p_ref))
        p.update(id=metadata_ref('population', sheet['analysis_id'], f'pair_{i}'), kind='verified_read_pairs', population_key='verified_read_pairs', population_ordinal=i)
        sheet['populations'].append(p)
        cell = deepcopy(next(c for c in sheet['measurements'] if c['id'] == job['operand_measurement_refs'][i]))
        cell.update(id=join_ref('cell', sheet['analysis_id'], f'pair_{i}', [p_ref]), metric='verified_pair_count', population_ref=p['id'], value=(4, 3)[i], native_token=None, unit='pairs')
        sheet['measurements'].append(cell); selected.append(cell)
    job.update(comparison_kind='pair_retention', population_refs=[c['population_ref'] for c in selected], operand_measurement_refs=[c['id'] for c in selected])
    for name, p_ref in zip(('before', 'after'), job['population_refs']): sheet['supplied_metadata'][0]['value'][name] = {'selection': 'record', 'record_ref': p_ref}
    job['lineage_basis']['declaration'] = deepcopy(sheet['supplied_metadata'][0]['value'])
    rows = run(sheet, job)
    assert rows['pair_retention_fraction']['value'] == .75 and rows['pair_retention_fraction']['denominator'] == 4
    assert rows['removed_count']['value'] == 1 and rows['removed_count']['unit'] == 'pairs'


def test_zero_denominator_retains_zero_removed_count():
    sheet, job, _ = saved()
    for ref in job['operand_measurement_refs']: replace_cell(sheet, ref, value=0, native_token='0')
    rows = run(sheet, job)
    assert rows['removed_count']['value'] == 0 and rows['removed_count']['state'] == 'available'
    for metric in ('removed_fraction', 'native_report_retention_fraction'):
        assert rows[metric]['value'] is None and rows[metric]['state'] == 'undefined'
        assert rows[metric]['denominator'] == 0 and 'zero_denominator' in rows[metric]['diagnostic_codes']


def test_after_greater_than_before_is_incompatible_not_clamped():
    sheet, job, _ = saved(); replace_cell(sheet, job['operand_measurement_refs'][1], value=9, native_token='9')
    rows = run(sheet, job)
    assert all(r['value'] is None and r['state'] == 'incompatible' for r in rows.values())
    assert rows['removed_count']['numerator'] == -1 and rows['native_report_retention_fraction']['numerator'] == 9


@pytest.mark.parametrize('scope,expected', [('partial', 'truncated'), ('unknown', 'missing')])
def test_incomplete_scope_prevents_whole_population_ratio(scope, expected):
    sheet, job, _ = saved(); replace_population(sheet, job['population_refs'][0], scope=scope)
    assert all(r['value'] is None and r['state'] == expected for r in run(sheet, job).values())


@pytest.mark.parametrize('which', ['population', 'operand'])
def test_omitted_job_input_never_uses_hidden_sheet_measurements(which):
    sheet, job, _ = saved(); key = 'population_refs' if which == 'population' else 'operand_measurement_refs'; job[key] = job[key][:1]
    rows = run(sheet, job)
    assert all(r['value'] is None for r in rows.values())
    assert all(set(r['operand_measurement_refs']) <= set(job['operand_measurement_refs']) for r in rows.values())
    assert all(set(r['population_refs']) <= set(job['population_refs']) for r in rows.values())


def test_wrong_population_incompatible_despite_available_counts():
    sheet, job, _ = saved(); job['population_refs'][1] = next(p['id'] for p in sheet['populations'] if p['population_key'] == 'fastq_reads')
    assert all(r['value'] is None and r['state'] == 'incompatible' for r in run(sheet, job).values())


def test_native_edge_cannot_be_reused_in_reverse():
    sheet, job, _ = saved(); job['population_refs'].reverse(); job['operand_measurement_refs'].reverse()
    assert all(r['value'] is None and 'incompatible_population' in r['diagnostic_codes'] for r in run(sheet, job).values())


@pytest.mark.parametrize('basis', [None, {'basis': 'unknown', 'metadata_id': None, 'evidence': None, 'declaration': None, 'native_lineage_ref': None}])
def test_unknown_lineage_missing_not_assumed(basis):
    sheet, job, _ = saved(); job['lineage_basis'] = basis; job['lineage_ref'] = None
    assert all(r['state'] == 'missing' and r['value'] is None for r in run(sheet, job).values())


def test_assumption_cannot_point_to_wrong_population_or_evidence():
    sheet, job, _ = saved('assumed'); job['lineage_basis']['evidence']['pointer'] = '/wrong'
    assert all(r['state'] == 'incompatible' for r in run(sheet, job).values())
    sheet, job, _ = saved('assumed'); declaration = sheet['supplied_metadata'][0]['value']; declaration['before']['population_ordinal'] = 1
    job['lineage_basis']['declaration'] = deepcopy(declaration)
    assert all(r['state'] == 'incompatible' for r in run(sheet, job).values())


def consistency_job():
    sheet, job, _ = saved()
    report = next(c for c in sheet['measurements'] if c['metric'] == 'hostile_reads_out'); observed = next(c for c in sheet['measurements'] if c['metric'] == 'fastq_read_count')
    job.update(calculation_id='consistency', method='report_consistency_v1', comparison_kind='report_count_consistency', operand_measurement_refs=[report['id'], observed['id']], population_refs=[report['population_ref'], observed['population_ref']])
    declare(sheet, job, 'same_population'); return sheet, job


def test_signed_report_difference_preserves_negative_value():
    sheet, job = consistency_job(); replace_cell(sheet, job['operand_measurement_refs'][0], value=1, native_token='1')
    row = run(sheet, job, calculate_report_consistency)['report_count_difference']
    assert row['value'] == -1 and row['state'] == 'available'
    assert row['numerator'] is None and row['denominator'] is None
    assert 'count_inconsistent' in row['diagnostic_codes']
    assert row['operand_measurement_refs'] == job['operand_measurement_refs']
    by_id = {cell['id']: cell for cell in sheet['measurements']}
    assert [by_id[ref]['value'] for ref in row['operand_measurement_refs']] == [1, 2]
    assert row['lineage_basis'] == job['lineage_basis']


def test_report_difference_zero_is_observed():
    sheet, job = consistency_job(); replace_cell(sheet, job['operand_measurement_refs'][0], value=2, native_token='2')
    row = run(sheet, job, calculate_report_consistency)['report_count_difference']; assert row['value'] == 0 and row['state'] == 'available'


def test_consistency_rejects_before_after_as_same_population():
    sheet, job, _ = saved(); job.update(method='report_consistency_v1', comparison_kind='report_count_consistency')
    row = run(sheet, job, calculate_report_consistency)['report_count_difference']; assert row['value'] is None and row['state'] == 'incompatible'


def test_consistency_rejects_wrong_populations_and_units():
    sheet, job = consistency_job(); job['population_refs'].reverse()
    assert run(sheet, job, calculate_report_consistency)['report_count_difference']['state'] == 'incompatible'
    sheet, job = consistency_job(); bases = next(c for c in sheet['measurements'] if c['metric'] == 'fastq_base_count')
    job['operand_measurement_refs'][1] = bases['id']; job['population_refs'][1] = bases['population_ref']
    assert run(sheet, job, calculate_report_consistency)['report_count_difference']['state'] == 'incompatible'


def test_rounded_percent_cannot_be_count_operand():
    sheet, job, _ = saved(); percent = next(c for c in sheet['measurements'] if c['metric'] == 'hostile_removed_proportion'); job['operand_measurement_refs'][0] = percent['id']
    assert all(r['value'] is None and r['state'] == 'incompatible' for r in run(sheet, job).values())


def test_saved_recalculation_without_io_and_parameter_identity(monkeypatch):
    sheet, job, params = saved(); saved_text = json.dumps(sheet)
    expected = calculate_retention(sheet, job=job, parameters_sha256=json_sha256(params)); sheet = json.loads(saved_text)
    def fail(*args, **kwargs): raise AssertionError('recalculation attempted I/O')
    monkeypatch.setattr('builtins.open', fail); monkeypatch.setattr(Path, 'open', fail)
    monkeypatch.setattr(socket, 'socket', fail); monkeypatch.setattr(subprocess, 'Popen', fail)
    assert calculate_retention(sheet, job=job, parameters_sha256=json_sha256(params)) == expected
    changed = deepcopy(params); changed['calculations'][-1]['calculation_id'] = 'recalculated'
    later = calculate_retention(sheet, job=changed['calculations'][-1], parameters_sha256=json_sha256(changed))
    assert [r['value'] for r in later] == [r['value'] for r in expected]
    assert {r['id'] for r in later}.isdisjoint(r['id'] for r in expected)
    assert json.dumps(sheet) == saved_text


def test_bad_arguments_contract_failure():
    sheet, job, _ = saved()
    with pytest.raises(FastqUtilsContractError): calculate_retention(sheet, job=job, parameters_sha256='bad')
    wrong = deepcopy(job); wrong['comparison_kind'] = None
    with pytest.raises(FastqUtilsContractError): run(sheet, wrong)
    with pytest.raises(FastqUtilsContractError): calculate_report_consistency(sheet, job=job, parameters_sha256='0' * 64)


def test_contradictory_matching_assumptions_cannot_choose_convenient_relation():
    sheet, job, _ = saved('assumed')
    contradict = deepcopy(sheet['supplied_metadata'][0]); contradict['metadata_id'] = 'contradiction'
    contradict['value']['relation'] = 'same_population'; sheet['supplied_metadata'].append(contradict)
    assert all(r['value'] is None and r['state'] == 'incompatible' for r in run(sheet, job).values())


def test_retention_zero_numerator_is_observed_zero_and_count_survives_absent_quality_metadata():
    sheet, job, _ = saved('assumed'); replace_cell(sheet, job['operand_measurement_refs'][1], value=0, native_token='0')
    rows = run(sheet, job)
    assert rows['read_retention_fraction']['value'] == 0
    assert rows['removed_count']['value'] == 8 and rows['removed_fraction']['value'] == 1
    assert all(p['quality_encoding'] == 'unknown' for p in sheet['populations'])


def test_consistency_missing_selected_operand_stays_missing():
    sheet, job = consistency_job(); job['operand_measurement_refs'] = job['operand_measurement_refs'][:1]
    row = run(sheet, job, calculate_report_consistency)['report_count_difference']
    assert row['value'] is None and row['state'] == 'missing'
    assert row['operand_measurement_refs'] == job['operand_measurement_refs']
