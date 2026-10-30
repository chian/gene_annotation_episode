"""Twenty additional native modes through the production preparation Workflow.

The shared fixture supplies explicitly scripted decisions. These tests execute
the original selected jobs, acquire their full outputs, inspect the retained
numerical data, and authenticate the actual parent forms. Generated data and
preparation measurements do not become scientific observations.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import socket
import subprocess

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.native_infernal_preparation_contracts import compile_native_infernal_preparation_job
from gene_annotation_episode.native_infernal_preparation_worker import recalculate_infernal_preparation
from gene_annotation_episode.numerical import NumericBand
from test_native_infernal_preparation_driver import CASES, POLICY, native_job
from test_native_infernal_preparation_results_integration import (
    PREFIX, assert_accounting, choice_for, result_form, run_case,
)


# This explicit list prevents new or dropped driver modes from silently changing
# what this integration workload claims. The seven base cases live in the
# shared integration file; its descriptor-only matrix does not execute them.
MODE_CASES = [
    ('cmbuild', 'refine'),
    ('cmconvert', 'legacy_ascii'),
    ('cmconvert', 'maximum_likelihood_hmm'),
    ('cmconvert', 'filter_hmm'),
    ('cmconvert', 'binary'),
    ('cmemit', 'sample_unaligned'),
    ('cmemit', 'sample_aligned'),
    ('cmfetch', 'key_file'),
    ('cmfetch', 'index'),
    ('cmcalibrate', 'forecast'),
    ('cmcalibrate', 'memory_estimate'),
    ('cmcalibrate', 'split_commands'),
    ('cmcalibrate', 'partition_scores'),
    ('cmcalibrate', 'merge_scores'),
    ('cmstat', 'scores_at_evalue'),
    ('cmstat', 'scores_at_pvalue'),
    ('cmstat', 'evalues_at_score'),
    ('cmstat', 'evalues_at_ga'),
    ('cmstat', 'evalues_at_nc'),
    ('cmstat', 'evalues_at_tc'),
]
BASE_CASES = {('cmbuild', 'build'), ('cmcalibrate', 'calibrate'), ('cmconvert', 'ascii'),
    ('cmemit', 'consensus'), ('cmfetch', 'single_key'), ('cmpress', 'press'), ('cmstat', 'summary')}
assert len(MODE_CASES) == len(set(MODE_CASES)) == 20
assert set(MODE_CASES) | BASE_CASES == {(r['program'], r['mode']) for r in CASES}
assert not set(MODE_CASES) & BASE_CASES


def mode_choice(job):
    choice = choice_for(job)
    program, mode = job['program'], job['mode']
    projection = choice['projection']
    if program == 'cmbuild':
        quantities = ['paired_consensus_numerator', 'consensus_length_denominator', 'paired_consensus_fraction']
        checks = ['paired_topology_coherent', 'build_header_counts_consistent']
    elif program == 'cmconvert':
        quantities = ['input_model_count', 'output_model_count', 'output_artifact_count', 'output_byte_count']
        checks = ['output_set_complete', 'output_format', 'conversion_semantics', 'output_population_complete']
    elif program == 'cmfetch':
        quantities = ['input_model_count', 'output_model_count', 'requested_key_count', 'satisfied_key_count',
            'missing_key_count', 'output_artifact_count']
        checks = (['requested_keys_satisfied'] if mode == 'key_file' else
            ['source_binding', 'attempt_binding', 'companion_stem', 'index_content_decoded'])
    elif program == 'cmemit':
        quantities = ['residue_count', 'canonical_count', 'gc_count', 'gc_denominator',
            'gc_fraction_canonical', 'gap_count', 'column_count', 'gap_fraction',
            'row_count', 'expected_sequence_count', 'actual_sequence_count']
        checks = ['cmemit_sequence_count_matches']
    elif program == 'cmcalibrate':
        quantities = {
            'forecast': ['predicted_seconds'], 'memory_estimate': ['predicted_bytes'],
            'split_commands': ['total_calibration_chunk_count', 'actual_calibration_nt'],
            'partition_scores': ['total_calibration_chunk_count', 'partition_chunk_count', 'actual_calibration_nt'],
            'merge_scores': ['actual_calibration_nt', 'mu_extrap_calculated', 'mu_extrap_residual'],
        }[mode]
        checks = {
            'forecast': [], 'memory_estimate': [], 'split_commands': ['split_command_count_consistent'],
            'partition_scores': ['partition_score_count_consistent', 'partition_request_binding'],
            'merge_scores': ['partition_request_binding', 'partition_population_complete', 'calibration_length_consistent'],
        }[mode]
    else:
        quantities = ['effective_random_hit_count', 'score_at_evalue', 'score_at_pvalue',
            'evalue_at_score', 'native_conversion_residual', 'native_rounding_half_width']
        checks = ['native_conversion_consistent', 'native_cutoff_consistent']
    projection['quantities'] = ['components.' + name for name in quantities]
    projection['checks'] = checks
    if (program, mode) == ('cmcalibrate', 'split_commands'):
        # The actual number here is a native count, reported by stdout and
        # independently counted from the inert commands file. No duration or
        # calibration population is manufactured for this writing operation.
        projection.update(collection='native_rows', quantities=['values.command_count'], checks=[])
    return choice


def present(cell, expected=None, *, unit=None, basis=None):
    assert cell['state'] == 'present' and type(cell['value']) in (int, float), cell
    if expected is not None:
        assert cell['value'] == pytest.approx(expected), cell
    if unit is not None:
        assert cell['unit'] == unit, cell
    if basis is not None:
        assert cell['basis'] == basis, cell
    return cell['value']


def read_retained(case):
    body = case.outcomes[0]['result']
    prepared = body['prepared']
    assert prepared is not None and prepared['graded'], body['failures']
    bundle = json.loads(case.store.get_artifact(prepared['bundle_artifact_ref']))
    grading = json.loads(case.store.get_artifact(prepared['grading_artifact_ref']))
    sheet = json.loads(case.store.get_artifact(prepared['sheet_artifact_ref']))
    calculations = json.loads(case.store.get_artifact(prepared['calculations_artifact_ref']))
    assert grading['sheet'] == sheet and grading['calculations'] == calculations
    assert grading['operation'] == sheet['operation'] == calculations['operation'] == bundle['operation']
    return body, bundle, sheet, calculations


def assert_native_custody(case, bundle):
    program, mode = case.job['program'], case.job['mode']
    assert bundle['requested_job'] == case.request == case.plan['requested_job']
    assert (bundle['program'], bundle['mode']) == (program, mode)
    assert case.plan['policy'] == POLICY.to_dict()
    assert bundle['returncode'] == 0 and bundle['failures'] == []
    assert bundle['software']['actual_sha256'] == case.job['software']['sha256']
    root = Path(case.plan['attempt_directory'])
    inputs = {}
    assert len(bundle['inputs']) == len(case.job['operands'])
    for row, original in zip(bundle['inputs'], case.job['operands']):
        inputs.setdefault(row['role'], []).append(str(root / row['relative_path']))
        raw = (root / row['relative_path']).read_bytes()
        assert raw == Path(original['path']).read_bytes()
        assert len(raw) == row['expected_size_bytes'] == row['staged_size_bytes'] == row['final_size_bytes']
        assert hashlib.sha256(raw).hexdigest() == row['expected_sha256'] == row['staged_sha256'] == row['final_sha256']
    compiled = compile_native_infernal_preparation_job(case.job, input_paths=inputs, output_directory=str(root))
    assert bundle['realized_argv'] == compiled['argv']
    assert bundle['operation'] == compiled['operation']
    assert bundle['realized_argv'][1:1 + len(case.job['options'])] == case.job['options']
    selected_flags = {
        ('cmbuild', 'refine'): '--refine', ('cmconvert', 'legacy_ascii'): '-1',
        ('cmconvert', 'maximum_likelihood_hmm'): '--mlhmm', ('cmconvert', 'filter_hmm'): '--fhmm',
        ('cmconvert', 'binary'): '-b', ('cmemit', 'sample_unaligned'): '-u',
        ('cmemit', 'sample_aligned'): '-a', ('cmfetch', 'key_file'): '-f', ('cmfetch', 'index'): '--index',
        ('cmcalibrate', 'forecast'): '--forecast', ('cmcalibrate', 'memory_estimate'): '--memreq',
        ('cmcalibrate', 'split_commands'): '--split', ('cmcalibrate', 'partition_scores'): '--part',
        ('cmcalibrate', 'merge_scores'): '--merge', ('cmstat', 'scores_at_evalue'): '-E',
        ('cmstat', 'scores_at_pvalue'): '-P', ('cmstat', 'evalues_at_score'): '-T',
        ('cmstat', 'evalues_at_ga'): '--cut_ga', ('cmstat', 'evalues_at_nc'): '--cut_nc',
        ('cmstat', 'evalues_at_tc'): '--cut_tc',
    }
    assert selected_flags[program, mode] in bundle['realized_argv']
    occurrences = case.outcomes[0]['result']['prepared']['occurrences']
    for occurrence in occurrences:
        raw = case.store.get_artifact(occurrence['artifact_ref'])
        assert raw == (root / occurrence['relative_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == occurrence['sha256']
        assert len(raw) == occurrence['size_bytes']
        assert occurrence['completeness'] == 'complete'
    output_occurrences = {(r['role'], r['ordinal']): r for r in occurrences
        if r['direction'] == 'output'}
    assert {r['role'] for r in bundle['artifacts']} == {r['role'] for r in case.job['outputs']}
    for row in bundle['artifacts']:
        occurrence = output_occurrences[row['role'], 0]
        raw = case.store.get_artifact(occurrence['artifact_ref'])
        assert raw == (root / row['relative_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row['sha256'] == occurrence['sha256']
        assert len(raw) == row['size_bytes'] == occurrence['size_bytes']
        assert occurrence['completeness'] == 'complete'
    return output_occurrences


def assert_parent_selection(case, choice, body, sheet, calculations):
    parent, received = assert_accounting(case)
    form = case.returned[0]
    failures_requested = case.job['mode'] in {'key_file', 'merge_scores'}
    expected_fields = {'completed', 'rows', 'artifacts', 'population'}
    if failures_requested:
        expected_fields.add('failures')
    assert set(form) == expected_fields
    assert case.forms[0] == result_form(failures=failures_requested)
    assert form['completed'] is body['complete'] is True, body['failures']
    assert form['population'] == [body['population']]
    collection = choice['projection']['collection']
    source_rows = calculations['rows'] if collection == 'calculations' else sheet[collection]
    assert body['population']['collection'] == collection
    assert body['population']['total_records'] == len(source_rows)
    assert body['population']['returned_records'] == len(form['rows'])
    assert body['population']['omitted_records'] == max(0, len(source_rows) - choice['projection']['rows']['limit'])
    assert body['population']['missing_record_keys'] == body['population']['missing_artifacts'] == []
    assert body['population']['returned_artifact_count'] == len(case.job['outputs'])
    saved_rows = {r['record_key']: r for r in source_rows}
    requested = choice['projection']['quantities']
    for row in form['rows']:
        assert row['source_ref'] == body['source_ref']
        assert [q['path'] for q in row['quantities']] == requested
        assert set(c['name'] for c in row['checks']) == set(choice['projection']['checks'])
        saved_checks = {check['check']: check['outcome'] for check in saved_rows[row['record_key']].get('checks', [])}
        assert all(check['outcome'] == saved_checks.get(check['name'], 'unknown') for check in row['checks'])
        for quantity in row['quantities']:
            cell = saved_rows[row['record_key']]
            for name in quantity['path'].split('.'):
                cell = cell.get(name) if cell is not None else None
            if cell is not None:
                assert {k: quantity[k] for k in ('value', 'state', 'basis', 'unit')} == {
                    k: cell[k] for k in ('value', 'state', 'basis', 'unit')}
            else:
                assert quantity['value'] is None and quantity['state'] == 'missing'
    fact_fields = expected_fields - {'completed'}
    facts = case.owner.native_infernal_preparation_returns.received_facts(parent, case.forms[0])
    assert facts == {PREFIX + name: form[name] for name in fact_fields}
    assert {r['fact_source'] for r in received} == {PREFIX + name for name in fact_fields}
    if failures_requested:
        assert_failure_return(case, body, parent)
    else:
        assert case.owner.native_infernal_preparation_returns.received_facts(parent,
            result_form(failures=True))[PREFIX + 'failures'] == []
    known = set(case.flow.receipts.known(parent.episode_id))
    resolve = case.flow.resolver(case.scope, context=parent)
    for name in ('sheet_artifact_ref', 'calculations_artifact_ref'):
        withheld = body['prepared'][name]
        assert withheld not in known
        assert not resolve(withheld, 'artifact')
        assert not case.owner.resolve_received_reference(parent, withheld, 'artifact')
    assert [u['controller_step']['marginal_credit'] for u in case.result_records[0]['units']] == [2]
    assert case.result_records[0]['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
    assert tuple(case.record.controller_state.history) == (0, 0)
    assert case.owner.completion_for_action(case.contexts[0], body['operation_key'])
    descriptors = case.owner.resource_tool_contracts()
    entry, = [r for r in descriptors if r['name'] == 'native.' + case.job['program'] + '.' + case.job['mode']]
    assert entry['description'] and entry['instructions'] and entry['resources'] == 'local'
    assert entry['invocation_route'] == {'kind': 'commission', 'routes': [
        {'entry_role': 'launch', 'resource_id': 'here', 'resource_role': 'launch_local'}]}
    Draft202012Validator(entry['input_schema']).validate(case.request)
    described = case.owner.job_progress_provider.targets.describe_target(case.provider.handoff, case.scope, selector=choice)
    assert described['service_or_program'] == case.job['program'] and described['operation'] == case.job['mode']
    assert described['acquisition_operations'] == ['execution.results.status', 'execution.results.collect']
    # The provider receives its model-service role (REASONING); episode roles
    # belong to the durable runtime path, not that transport argument.
    actual_roles = [json.loads(case.flow.journal.row('runtime_episodes', episode_id)['path'])[-1][0]
        for episode_id, _, _ in case.provider.calls]
    assert actual_roles == ['annotation', 'launch', 'launch_local', 'annotation', 'results']


def assert_failure_return(case, body, parent):
    failures = case.returned[0]['failures']
    assert failures
    # Repeated diagnostics from grading and publication are the same fact,
    # while distinct input occurrences retain their own diagnostic identity.
    assert len(failures) == len({json.dumps(row, sort_keys=True) for row in failures})
    assert {(row['stage'], row['code'], row['record_key']) for row in failures} == {
        (row['stage'], row['code'], row['record_key']) for row in body['failures']}
    for row in failures:
        assert set(row) == {'handoff_ref', 'source_ref', 'stage', 'code', 'record_key', 'affected'}
        assert row['handoff_ref'] == case.provider.handoff
        assert row['source_ref'] == body['source_ref']
        assert case.owner.resolve_received_reference(parent, row['code'],
            'native_infernal_preparation_failure_code')
        assert case.owner.resolve_received_reference(parent, row['record_key'],
            'native_infernal_preparation_failure_record')
    if case.job['mode'] == 'key_file':
        row, = failures
        assert row['stage'] == 'association'
        assert row['code'] == 'artifact_key_request_unsatisfied'
        assert row['affected'] == {'direction': 'input', 'role': 'keys', 'ordinal': 0}
        assert row['record_key'].endswith('#/inputs/1#key_request/0')
    else:
        assert len(failures) == 10
        metadata = [row for row in failures if row['stage'] == 'metadata']
        calculations = [row for row in failures if row['stage'] == 'calculation']
        assert len(metadata) == 2 and len(calculations) == 8
        for ordinal in (0, 1):
            affected = {'direction': 'input', 'role': 'partition_scores', 'ordinal': ordinal}
            row, = [r for r in metadata if r['affected'] == affected]
            assert row['code'] == 'native_infernal_preparation_partition_request_binding_unavailable'
            assert row['record_key'].endswith('#/inputs/' + str(ordinal + 1))
            partition_rows = [r for r in calculations if r['affected'] == affected]
            assert len(partition_rows) == 4
            assert all(r['code'] == 'infernal_statistics_calculation_partition_request_missing'
                for r in partition_rows)
            assert {r['record_key'] for r in partition_rows} == {
                row['record_key'] + '#partition/' + str(index) for index in range(4)}


def assert_mode_numbers(case, bundle, sheet, calculations):
    program, mode = case.job['program'], case.job['mode']
    rows = calculations['rows']
    by_key = {r['record_key']: r for r in rows}
    if program == 'cmbuild':
        build, = [r for r in sheet['native_rows'] if r['kind'] == 'build']
        for field, answer in [('nseq', 3), ('alignment_length', 12), ('consensus_length', 12), ('base_pairs', 4), ('bifurcations', 0)]:
            present(build['values'][field], answer)
        components = by_key[build['record_key']]['components']
        present(components['paired_consensus_numerator'], 8, unit='nt')
        present(components['consensus_length_denominator'], 12, unit='nt')
        present(components['paired_consensus_fraction'], 2 / 3, unit='fraction')
        refined, = [r for r in sheet['output_records'] if r['kind'] == 'training_alignment']
        present(refined['values']['row_count'], 3)
        present(refined['values']['column_count'], 12)
        assert any(r['kind'] == 'build_refinement' for r in sheet['native_rows'])
    elif program in {'cmconvert', 'cmfetch'}:
        aggregate, = [r for r in rows if 'input_model_count' in r['components']]
        values = aggregate['components']
        # The retained missing-key example deliberately contains two distinct
        # tRNA training models; other selected examples contain one 12-nt CM.
        present(values['input_model_count'], 2 if mode == 'key_file' else 1)
        present(values['output_artifact_count'], 3)
        if mode == 'binary':
            assert values['output_model_count']['value'] is None
            assert values['output_model_count']['state'] == 'missing'
            assert not [r for r in sheet['output_records'] if r['kind'] == 'model']
            assert any(r['code'] == 'model_opaque_content' for r in sheet['issues'])
        elif mode == 'index':
            assert values['output_model_count']['value'] is None
            assert values['output_model_count']['state'] == 'not_measured'
            outcomes = {r['check']: r['outcome'] for r in aggregate['checks']}
            assert outcomes['source_binding'] == outcomes['attempt_binding'] == outcomes['companion_stem'] == 'pass'
            assert outcomes['index_content_decoded'] == 'unknown'
        else:
            present(values['output_model_count'], 1)
            model, = [r for r in sheet['output_records'] if r['kind'] == 'model']
            if mode in {'maximum_likelihood_hmm', 'filter_hmm'}:
                assert model['model_type'] == 'hmm'
                present(model['filter_hmm']['fields']['LENG'], 12)
                assert model['fields']['CLEN']['value'] is None
            else:
                present(model['fields']['CLEN'], 72 if mode == 'key_file' else 12)
            if mode == 'legacy_ascii':
                assert model['filter_hmm'] is None and all(v is None for v in model['calibration'].values())
            if mode == 'key_file':
                present(values['requested_key_count'], 2)
                present(values['satisfied_key_count'], 1)
                present(values['missing_key_count'], 1)
                requests = [r for r in sheet['native_rows'] if r['kind'] == 'key_request']
                assert [(r['requested_key'], r['outcome']) for r in requests] == [('absent_key', 'missing'), ('tRNA5', 'satisfied')]
                assert any(r['check'] == 'requested_keys_satisfied' and r['outcome'] == 'fail' for r in aggregate['checks'])
                assert any(r['name'] == 'requested_keys_satisfied' and r['outcome'] == 'fail'
                    for returned in case.returned[0]['rows'] for r in returned['checks'])
    elif program == 'cmemit':
        sequences = [r for r in sheet['output_records'] if r['kind'] == 'generated_sequence']
        assert len(sequences) == 2
        assert [r['sequence'] for r in sequences] == (
            ['GCGCUAAGCGC', 'GCGCUAAAGCGC'] if mode == 'sample_unaligned' else
            ['GCGC-UAAGCGC', 'GCGCUAAAGCGC'])
        for sequence in sequences:
            assert sequence['origin'] == 'generated_sample' and len(sequence['model_keys']) == 1
            text = sequence['sequence'].upper()
            gc, canonical = sum(text.count(s) for s in 'GC'), sum(text.count(s) for s in 'ACGTU')
            components = by_key[sequence['record_key']]['components']
            present(components['residue_count'], len(text.replace('-', '').replace('.', '').replace('_', '')), unit='nt')
            present(components['canonical_count'], canonical, unit='nt')
            present(components['gc_count'], gc, unit='nt')
            present(components['gc_denominator'], canonical, unit='nt')
            present(components['gc_fraction_canonical'], gc / canonical, unit='fraction')
            if mode == 'sample_aligned':
                gaps = sum(text.count(s) for s in '-._')
                present(components['gap_count'], gaps, unit='column')
                present(components['column_count'], 12, unit='column')
                present(components['gap_fraction'], gaps / 12, unit='fraction')
            else:
                assert components['column_count']['value'] is components['gap_fraction']['value'] is None
        populations = [r['components'] for r in rows if r['components'].get('expected_sequence_count', {}).get('state') == 'present']
        assert populations
        for components in populations:
            present(components['expected_sequence_count'], 2)
            present(components['actual_sequence_count'], 2)
        if mode == 'sample_aligned':
            alignment, = [r for r in sheet['output_records'] if r['kind'] == 'generated_alignment']
            present(alignment['values']['row_count'], 2)
            assert all(len(r['sequence']) == alignment['values']['column_count']['value'] for r in sequences)
            assert alignment['annotations']['gc']
    elif program == 'cmcalibrate':
        if mode in {'forecast', 'memory_estimate'}:
            kind, component, native_field, factor, unit = (
                ('forecast', 'predicted_seconds', 'predicted_seconds', 1, 'second') if mode == 'forecast' else
                ('memory', 'predicted_bytes', 'predicted_mb', 1e6, 'byte'))
            predictions = [r for r in sheet['native_rows'] if r['kind'] == 'resource_estimate'
                and r['values'][native_field]['state'] == 'present']
            assert predictions
            if mode == 'memory_estimate':
                assert [(r['values']['cpu_count']['value'], r['values']['predicted_mb']['value'])
                    for r in predictions] == [(1, 72.1), (4, 288.4)]
            for prediction in predictions:
                native_value = present(prediction['values'][native_field], basis='native_prediction')
                assert native_value >= 0
                present(by_key[prediction['record_key']]['components'][component], native_value * factor,
                    unit=unit, basis='native_prediction')
        elif mode == 'split_commands':
            commands = [r for r in sheet['native_rows'] if r['kind'] == 'resource_estimate'
                and r['values']['command_count']['state'] == 'present']
            assert len(commands) == 2
            assert len({r['locator']['artifact_ref'] for r in commands}) == 2
            for row in commands:
                present(row['values']['command_count'], 2)
            assert all(r['quantities'][0]['value'] == 2 for r in case.returned[0]['rows'])
            assert '--split' in bundle['realized_argv']
            assert not list(Path(case.plan['attempt_directory']).rglob('partition.1'))
        elif mode == 'partition_scores':
            partitions = [r for r in sheet['native_rows'] if r['kind'] == 'partition']
            assert len(partitions) == 4
            assert [r['values']['score_count']['value'] for r in partitions] == [3149, 3035, 4409, 3812]
            for partition in partitions:
                present(partition['values']['score_count'], len(partition['series']))
                assert partition['series'] and all(s['x']['state'] == 'present' for s in partition['series'])
                components = by_key[partition['record_key']]['components']
                present(components['total_calibration_chunk_count'], 2)
                present(components['partition_chunk_count'], 1)
                present(components['actual_calibration_nt'], 10000, unit='nt')
            assert calculations['parameters']['partition_requests'][0]['partition_index'] == 1
        else:
            model, = [r for r in sheet['output_records'] if r['kind'] == 'model']
            expected_hits = {'ECMGC': 6330, 'ECMGI': 6207, 'ECMLC': 8366, 'ECMLI': 7127}
            for algorithm, expected_count in expected_hits.items():
                calibration = model['calibration'][algorithm]
                present(calibration['calibration_dbsize_nt'], 20000, unit='nt')
                present(calibration['random_hit_count'], expected_count)
            assert 'partition_requests' not in calculations['parameters']
            assert any(f['code'] == 'native_infernal_preparation_partition_request_binding_unavailable'
                for f in case.outcomes[0]['result']['failures'])
            assert any(c['check'] == 'partition_request_binding' and c['outcome'] == 'unknown'
                for r in rows for c in r['checks'])
    else:
        statistics = [r for r in sheet['native_rows'] if r['kind'] == 'model_statistic']
        assert len(statistics) == 4
        model, = [r for r in sheet['input_records'] if r['kind'] == 'model']
        fits = {f['algorithm']: f for f in model['calibration'].values() if f is not None}
        expected_native = {
            'scores_at_evalue': [45.32, 36.71, 41.88, 42.23],
            'scores_at_pvalue': [4.14, 2.60, 2.66, 2.18],
            'evalues_at_score': [4406.56, 1593.45, 1859.13, 1697.07],
        }
        if mode in expected_native:
            field = 'threshold_bits' if mode.startswith('scores_at_') else 'evalue'
            assert [r['values'][field]['value'] for r in statistics] == expected_native[mode]
        for statistic in statistics:
            fields, values = statistic['values'], by_key[statistic['record_key']]['components']
            fit = fits[statistic['identity']['algorithm']]
            scale, location = fit['lambda']['value'], fit['mu_extrap']['value']
            denominator = 10000000 / fit['calibration_dbsize_nt']['value'] * fit['random_hit_count']['value']
            present(values['effective_random_hit_count'], denominator)
            if mode == 'scores_at_evalue':
                present(values['score_at_evalue'], location - math.log(.01 / denominator) / scale, unit='bit')
            elif mode == 'scores_at_pvalue':
                present(values['score_at_pvalue'], location - math.log(.01) / scale, unit='bit')
            elif mode == 'evalues_at_score':
                present(values['evalue_at_score'], denominator * math.exp(-scale * max(0, 10 - location)), unit='expected_count')
            else:
                assert model['fields'][mode[-2:].upper()]['value'] is None
                assert fields['threshold_bits']['value'] is None and fields['evalue']['value'] is None
                assert values['evalue_at_score']['value'] is None


@pytest.mark.parametrize('program,mode', MODE_CASES, ids=['-'.join(r) for r in MODE_CASES])
def test_remaining_native_preparation_modes_through_workflow(tmp_path, monkeypatch, program, mode):
    job = native_job(program, mode)
    choice = mode_choice(job)
    case = run_case(tmp_path, program, mode, selectors=[choice],
        form_options={'failures': mode in {'key_file', 'merge_scores'}})
    try:
        body, bundle, sheet, calculations = read_retained(case)
        (tmp_path / 'NUMERICAL_EXAMPLE.json').write_text(json.dumps({
            'program': program, 'mode': mode, 'selector': choice,
            'native_argv': bundle['realized_argv'], 'returncode': bundle['returncode'],
            'sheet_artifact_ref': body['prepared']['sheet_artifact_ref'],
            'calculations_artifact_ref': body['prepared']['calculations_artifact_ref'],
            'sheet_issues': sheet['issues'], 'calculation_issues': calculations['issues'],
            'typed_return': case.returned[0], 'failures': body['failures'],
            'scientific_observation_count': case.store.count('observation'),
        }, indent=2) + '\n')
        assert_native_custody(case, bundle)
        assert_parent_selection(case, choice, body, sheet, calculations)
        assert_mode_numbers(case, bundle, sheet, calculations)
        original = deepcopy(sheet)
        def forbidden(*args, **kwargs):
            raise AssertionError('saved-sheet recalculation performed acquisition, parsing or native execution')
        with monkeypatch.context() as guard:
            guard.setattr(socket, 'socket', forbidden)
            guard.setattr(subprocess, 'Popen', forbidden)
            guard.setattr('gene_annotation_episode.native_infernal_preparation_worker.grade_infernal_preparation', forbidden)
            guard.setattr('gene_annotation_episode.infernal_preparation_statistics.populate_infernal_statistics_sheet', forbidden)
            guard.setattr('gene_annotation_episode.infernal_preparation_artifacts.populate_infernal_artifact_sheet', forbidden)
            guard.setattr('gene_annotation_episode.infernal_preparation_emission.populate_cmemit_sheet', forbidden)
            assert recalculate_infernal_preparation(sheet, parameters=calculations['parameters']) == calculations
            adjustment = {'scores_at_evalue': {'evalue': .001}, 'scores_at_pvalue': {'pvalue': .001},
                'evalues_at_score': {'search_space_mb': 20}}.get(mode) if program == 'cmstat' else None
            if adjustment is not None:
                recalculated = recalculate_infernal_preparation(sheet, parameters={**calculations['parameters'], **adjustment})
                old = {r['record_key']: r for r in calculations['rows']}
                original_rows = {r['record_key']: r for r in sheet['native_rows']}
                model, = [r for r in sheet['input_records'] if r['kind'] == 'model']
                fits = {f['algorithm']: f for f in model['calibration'].values() if f is not None}
                component = {'scores_at_evalue': 'score_at_evalue', 'scores_at_pvalue': 'score_at_pvalue',
                    'evalues_at_score': 'evalue_at_score'}[mode]
                for row in recalculated['rows']:
                    before = old[row['record_key']]['components'][component]['value']
                    scale = fits[original_rows[row['record_key']]['identity']['algorithm']]['lambda']['value']
                    expected = before * 2 if mode == 'evalues_at_score' else before + math.log(10) / scale
                    present(row['components'][component], expected)
                (tmp_path / 'RECALCULATED_EXAMPLE.json').write_text(json.dumps(recalculated, indent=2) + '\n')
        assert sheet == original and case.store.count('observation') == 0
    finally:
        case.store.close()
