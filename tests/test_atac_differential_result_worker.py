"""Retained native formats and explicitly synthetic failures, without acquisition."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import shutil

import pytest

from gene_annotation_episode.atac_differential_result_contracts import canonical, SHEET_FORMAT, TABLE_FORMAT, ROLES
from gene_annotation_episode.atac_differential_result_worker import run_atac_result_worker, _calculate_sheet, _Tracked
from gene_annotation_episode.native_atac_differential_preparation import build_saved_atac_worker_plan, build_native_atac_worker_plan
from gene_annotation_episode.atac_differential_contracts import BEDGRAPH_COLUMNS
from gene_annotation_episode.atac_differential_inputs import iter_atac_track_table_rows, parse_macs2_peaks_xls
from gene_annotation_episode.atac_differential_sheet import build_atac_differential_sheet, select_atac_depth_counts
from gene_annotation_episode.native_atac_differential_capture import capture_atac_native_files
from gene_annotation_episode.state import Store
from test_atac_differential_calculation_inputs import sheet, track, replace_track, population, native_inputs_with_headers, alias_reorder_sheet
from test_atac_differential_inputs import NATIVE, artifact


def identity(raw, fmt):
    sha = hashlib.sha256(raw).hexdigest()
    return dict(artifact_ref='artifact_' + sha, sha256=sha, size_bytes=len(raw), format=fmt)


def selector(saved, *, kind='summary', cutoff=3, intervals=None, bundle=None):
    return dict(version='atac_differential_result_selector_v1', mode='saved_sheet_recalculation' if bundle else 'native_result',
        comparison_key=saved['comparison']['comparison_key'], intervals=population() if intervals is None else intervals,
        parameters=dict(pseudocount=0.01, cutoff_log10_lr=cutoff, minimum_length_bp=50, maximum_gap_bp=0),
        projection=dict(kind=kind, row_window=None if kind == 'summary' else dict(offset=0, limit=1000),
            run_keys=[r['run_key'] for r in saved['callpeak_bindings']] if kind == 'native_peak_rows' else [],
            categories=['condition1', 'condition2', 'common'] if kind in ('native_differential_rows', 'derived_regions') else []),
        saved_sheet_bundle=bundle)


def save_bundle(directory, saved, *, external=True):
    """Serialize all supplied scientific values; no original file refs are opened."""
    directory.mkdir(parents=True, exist_ok=True)
    saved = json.loads(canonical(saved))
    tables = []
    for role in ROLES:
        t = track(saved, role)
        if not external or t['state']['availability'] == 'missing':
            continue
        raw = b''.join(canonical(row) + b'\n' for row in t['rows'])
        file = identity(raw, TABLE_FORMAT)
        path = directory / (role + '.jsonl')
        path.write_bytes(raw)
        t['rows'] = dict(storage='retained_table', artifact_ref=file['artifact_ref'], format=TABLE_FORMAT,
            columns=list(BEDGRAPH_COLUMNS), row_count=t['readable_data_row_count'], sha256=file['sha256'],
            byte_count=file['size_bytes'], order='native_file_order', source_artifact_ref=t['artifact']['artifact_ref'])
        t['ordered_row_index'] = None
        tables.append(dict(track_key=t['binding_key'], file=file, path=str(path)))
    raw = canonical(saved)
    path = directory / 'saved-sheet.json'
    path.write_bytes(raw)
    local = dict(sheet=dict(file=identity(raw, SHEET_FORMAT), path=str(path)), tables=tables)
    public = dict(sheet=local['sheet']['file'], tables=[dict(track_key=r['track_key'], file=r['file']) for r in tables])
    return local, public


def saved_plan(directory, saved, **options):
    external = options.pop('external', True)
    local, public = save_bundle(directory / 'retained', saved, external=external)
    chosen = selector(saved, bundle=public, **options)
    return build_saved_atac_worker_plan(directory=str(directory / 'worker'), sheet_bundle=local, selector=chosen)


def read_outputs(plan):
    root = Path(plan['directory'])
    output = {name: json.loads((root / (name + '.json')).read_bytes()) for name in ('sheet', 'calculations', 'projection', 'diagnostics') if (root / (name + '.json')).exists()}
    for name in ('partitions', 'components', 'regions'):
        path = root / (name + '.jsonl')
        output[name] = [json.loads(line) for line in path.read_bytes().splitlines()] if path.exists() else None
    return output


def forbidden(*args, **kwargs):
    raise AssertionError('saved calculation attempted acquisition or native analysis')


@pytest.mark.parametrize('external', [False, True])
def test_explicit_retained_native_fifteen_scores_and_distinct_corrected_regions(tmp_path, monkeypatch, external):
    plan = saved_plan(tmp_path, sheet(), kind='derived_regions', external=external)
    oracle = json.loads((NATIVE / 'explicit_tracks/NATIVE_DIAGNOSTIC.json').read_bytes())['arrays'][0]
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    result = run_atac_result_worker(plan)
    assert result['state'] == 'produced' and not result['failures']
    output = read_outputs(plan)
    names = ('condition1_vs_background', 'condition2_vs_background', 'condition1_vs_condition2')
    assert [[r['scores']['likelihoods'][key]['native_float32']['value'] for key in names] for r in output['components']] == list(map(list, zip(*(oracle['native_' + name] for name in names))))
    regions = {r['category']: r for r in output['regions']}
    assert [(regions[c]['start'], regions[c]['end'], regions[c]['native_float32_mean_score']) for c in ('condition1', 'common', 'condition2')] == [(100, 200, 17.7408447265625), (200, 300, 5.425064273367752e-7), (300, 400, 12.148710250854492)]
    assert output['sheet']['native_differential'][0]['rows'][0]['reported_start0'] == 0
    assert output['sheet']['native_differential'][0]['rows'][0]['reported_score'] == 17.7408
    assert output['calculations']['depth_operands'] == dict(depth1=1, depth2=2, depth_unit='million_tags')
    assert all('count' not in d for d in output['sheet']['depth_selection']['conditions'])
    assert output['calculations']['summary']['partition_coverage'] == dict(all_four_observed_bp=500, unavailable_or_invalid_bp=0, extent='complete')
    assert output['projection']['total_rows'] == 3
    assert all(len(r) == 9 for path in (Path(plan['directory']) / 'tracks').glob('*.jsonl') for r in map(json.loads, path.read_bytes().splitlines())) if external else True
    assert output['sheet'] == json.loads(Path(plan['sheet_bundle']['sheet']['path']).read_bytes())
    changed_plan = deepcopy(plan)
    changed_plan['directory'] = str(tmp_path / 'changed-cutoff-worker')
    changed_plan['selector']['parameters']['cutoff_log10_lr'] = 20
    run_atac_result_worker(changed_plan)
    changed = read_outputs(changed_plan)
    assert changed['regions'] == [] and changed['sheet'] == output['sheet']
    assert len(output['regions']) == 3


def test_saved_native_sheet_cutoff_change_forbids_acquisition(tmp_path, monkeypatch):
    native_sheet = sheet(native=True)
    plan = saved_plan(tmp_path / 'selected', native_sheet, cutoff=1000, intervals=population(end=12000))
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    result = run_atac_result_worker(plan)
    output = read_outputs(plan)
    assert result['state'] == 'produced'
    assert output['calculations']['depth_operands'] == dict(depth1=100, depth2=200, depth_unit='tags')
    assert [r['reported_numbers']['treatment_total_tags']['value'] for r in output['sheet']['peaks_xls']] == [105, 200]
    assert [(r['rows'][0]['chromosome'], r['rows'][0]['length_bp'], r['rows'][0]['sequence_md5']) for r in output['sheet']['bam_references']] == [('chrToy', 12000, None)] * 2
    assert output['calculations']['summary']['partition_coverage'] == dict(all_four_observed_bp=8060, unavailable_or_invalid_bp=3940, extent='complete')
    assert [r['count'] for r in output['calculations']['summary']['derived_region_counts']] == [0, 0, 0]
    assert output['calculations']['summary']['native_region_counts'][2]['count'] == 0
    assert [track(output['sheet'], role)['rows']['row_count'] for role in ROLES] == [110, 35, 210, 69]
    assert output['sheet']['narrowpeaks'][1]['rows'][0]['display_score'] == 1045


@pytest.mark.parametrize('case', ['missing', 'zero', 'unit_mismatch', 'wrong_reference', 'missing_background', 'false_compatibility'])
def test_worker_keeps_missing_zero_and_independent_operands_distinct(tmp_path, case):
    saved = sheet()
    if case == 'missing':
        saved['depth_selection']['conditions'][0].update(state='missing', value=None, value_lexeme=None)
    elif case == 'zero':
        # Native measured zero is allowed. An explicitly declared fixture
        # depth must be positive; do not bypass that different contract.
        inputs = native_inputs_with_headers()
        run = inputs['callpeak_bindings'][0]
        raw = (NATIVE / 'bam_outputs/condition1_peaks.xls').read_bytes().replace(
            b'# tags after filtering in treatment: 100\n', b'# tags after filtering in treatment: 0\n')
        inputs['peaks_xls'][0] = parse_macs2_peaks_xls(raw,
            artifact=artifact(raw, run['artifact_roles']['peaks_xls'], 'macs2_peaks_xls_narrow', run['producer_ref']), callpeak=run)
        inputs['depth_selection'] = select_atac_depth_counts(inputs['peaks_xls'], conditions=('c1', 'c2'), callpeak_bindings=inputs['callpeak_bindings'])
        saved = build_atac_differential_sheet(**inputs)
    elif case == 'unit_mismatch':
        saved['depth_selection']['conditions'][1]['unit'] = 'tags'
    elif case == 'wrong_reference':
        track(saved, 'background2')['binding']['reference_id'] = 'other'
    elif case == 'missing_background':
        replace_track(saved, 'background2', None)
    else:
        saved['depth_selection']['compatible_population'] = False
        saved['reference_relation'] = 'conflicting'
    plan = saved_plan(tmp_path, saved)
    result = run_atac_result_worker(plan)
    output = read_outputs(plan)
    assert output['partitions']
    depth = output['calculations']['depth_operands']
    if case == 'unit_mismatch':
        assert depth == dict(depth1=None, depth2=None, depth_unit=None)
        assert output['components'] is None and output['regions'] is None
        assert output['calculations']['summary']['derived_region_counts'][0]['count'] is None
        assert any(r['code'] == 'calculation_input_unavailable' for r in result['failures'])
    elif case in ('missing', 'zero'):
        assert depth == (dict(depth1=None, depth2=2, depth_unit='million_tags') if case == 'missing' else dict(depth1=0, depth2=200, depth_unit='tags'))
        assert output['components'][0]['scores']['depth_factors']['condition1']['reason'] == ('operand_unavailable' if case == 'missing' else 'zero_depth')
    elif case in ('wrong_reference', 'missing_background'):
        values = output['components'][1]['scores']['likelihoods']
        assert values['condition1_vs_background']['native_float32']['value'] is not None
        assert values['condition1_vs_condition2']['native_float32']['value'] == 17.7408447265625
        assert values['condition2_vs_background']['native_float32']['value'] is None
    else:
        assert output['calculations']['eligibility']['depths'] == 'usable'
        assert all(v == 'usable' for v in output['calculations']['eligibility']['tracks'].values())


def test_native_wrong_header_disables_only_its_run_and_keeps_depths(tmp_path):
    saved = sheet(native=True)
    saved['bam_references'][0]['rows'][0]['length_bp'] = 12001
    plan = saved_plan(tmp_path, saved, intervals=population(end=12000))
    run_atac_result_worker(plan)
    output = read_outputs(plan)
    assert output['calculations']['eligibility']['tracks'] == dict(signal1='unavailable', background1='unavailable', signal2='usable', background2='usable')
    assert output['calculations']['depth_operands'] == dict(depth1=100, depth2=200, depth_unit='tags')
    assert output['components'][0]['scores']['likelihoods']['condition2_vs_background']['native_float32']['value'] is not None


@pytest.mark.parametrize('case', ['empty', 'missing', 'negative_null', 'overlap_outside'])
def test_raw_row_occurrences_and_invalid_values_survive_worker_roundtrip(tmp_path, case):
    # Deliberately synthetic counterexamples exercise worker serialization of
    # the accepted parser/bridge states, without a second numerical rule.
    raw = {
        'empty': b'', 'missing': None,
        'negative_null': b'chrToy\t0\t100\t-2\nchrToy\t100\t200\tnan\nchrToy\t200\t500\t1\n',
        'overlap_outside': b'chrToy\t0\t100\t1\nchrToy\t0\t100\t1\nchrToy\t50\t600\t7\n',
    }[case]
    saved = sheet()
    original = replace_track(saved, 'signal1', raw)
    original_rows = json.loads(canonical(original['rows']))
    plan = saved_plan(tmp_path, saved)
    run_atac_result_worker(plan)
    output = read_outputs(plan)
    report = track(output['sheet'], 'signal1')
    if case == 'missing':
        assert report['state']['availability'] == 'missing' and report['data_row_count'] is None
        assert not any(r['track_key'] == 'signal1' for r in plan['sheet_bundle']['tables'])
    else:
        table = next(r for r in plan['sheet_bundle']['tables'] if r['track_key'] == 'signal1')
        assert [json.loads(line) for line in Path(table['path']).read_bytes().splitlines()] == original_rows
        assert [json.loads(line) for line in Path(plan['directory'], 'tracks/0.jsonl').read_bytes().splitlines()] == original_rows
    if case in ('empty', 'missing'):
        assert all(r['values']['signal1'] is None and r['states']['signal1'] == 'missing' for r in output['components'])
        if case == 'empty':
            assert report['state']['availability'] == 'present' and report['data_row_count'] == 0
    elif case == 'negative_null':
        assert original_rows[0][7:] == [-2.0, '-2'] and original_rows[1][7:] == [None, 'nan']
        assert [r['states']['signal1'] for r in output['components'][:2]] == ['invalid', 'invalid']
        assert all(r['scores']['likelihoods']['condition2_vs_background']['native_float32']['value'] is not None for r in output['components'])
    else:
        assert len(original_rows) == 3 and original_rows[2][6] == 600
        assert any(r['states']['signal1'] == 'ambiguous' and r['source_rows']['signal1'] == [0, 1, 2] for r in output['components'])
        assert any(r['code'] == 'coordinate_outside_reference' for r in output['calculations']['issues'])


@pytest.mark.parametrize('kind', ['missing', 'checksum', 'malformed'])
def test_saved_attachment_failure_keeps_other_streams_and_valid_prefix(tmp_path, kind):
    plan = saved_plan(tmp_path, sheet(), intervals=population(end=200))
    bad = Path(plan['sheet_bundle']['tables'][0]['path'])
    if kind == 'missing':
        bad.unlink()
    elif kind == 'checksum':
        bad.write_bytes(bad.read_bytes().replace(b'"20"', b'"21"'))
    else:
        bad.write_bytes(bad.read_bytes() + b'not JSON\n')
    result = run_atac_result_worker(plan)
    output = read_outputs(plan)
    assert result['state'] == 'partial'
    assert any(p['code'] == 'calculation_stream_failed' for p in result['failures'])
    assert len(output['partitions']) == (0 if kind == 'missing' else 2)
    assert all(t['extent'] == 'partial' for t in output['calculations']['tables'])
    assert all(r['exhausted'] for r in output['calculations']['stream_states'] if r['track_key'] != 'signal1')
    assert not next(r for r in output['calculations']['stream_states'] if r['track_key'] == 'signal1')['exhausted']


def test_two_late_failures_drained_without_fabricating_open_region_end(tmp_path):
    plan = saved_plan(tmp_path, sheet(), intervals=population(100, 200), kind='derived_regions')
    for row in (plan['sheet_bundle']['tables'][0], plan['sheet_bundle']['tables'][3]):
        path = Path(row['path'])
        path.write_bytes(path.read_bytes() + b'bad late JSON\n')
    result = run_atac_result_worker(plan)
    output = read_outputs(plan)
    failures = [r for r in result['failures'] if r['code'] == 'calculation_stream_failed']
    assert len({r['artifact_ref'] for r in failures}) == 2
    assert len(output['components']) == 1 and output['regions'] == []
    assert output['projection']['row_extent'] == 'partial' and output['projection']['total_rows'] is None
    assert len([r for r in output['calculations']['issues'] if r['code'] == 'invalid_atac_track_table_row']) >= 2
    assert all(Path(plan['directory'], 'tracks', str(i) + '.jsonl').read_bytes() == Path(r['path']).read_bytes() for i, r in enumerate(plan['sheet_bundle']['tables']))


def test_retained_emitted_region_survives_later_failure(tmp_path):
    plan = saved_plan(tmp_path, sheet(), kind='derived_regions')
    bad = Path(plan['sheet_bundle']['tables'][0]['path'])
    bad.write_bytes(bad.read_bytes() + b'late malformed row\n')
    run_atac_result_worker(plan)
    output = read_outputs(plan)
    assert any(r['category'] == 'condition1' and r['start'] == 100 for r in output['regions'])
    assert all(t['extent'] == 'partial' for t in output['calculations']['tables'])
    assert output['projection']['row_extent'] == 'partial'


def test_alias_keeps_raw_tokens_and_projects_canonical_coordinates(tmp_path):
    saved = sheet()
    saved['reference']['contigs'][0]['chromosome'] = 'Toy'
    saved['reference']['aliases'] = [dict(source_chromosome='chrToy', target_chromosome='Toy', reference_id='fixture-toy', source_refs=['declared'])]
    plan = saved_plan(tmp_path, saved, intervals=population(chromosome='Toy'))
    run_atac_result_worker(plan)
    output = read_outputs(plan)
    assert {row['chromosome'] for row in output['components']} == {'Toy'}
    assert all(row[4] == 'chrToy' for p in (Path(plan['directory']) / 'tracks').glob('*.jsonl') for row in map(json.loads, p.read_bytes().splitlines()))


def test_alias_reorder_finalizes_every_other_source(tmp_path):
    saved = alias_reorder_sheet()
    plan = saved_plan(tmp_path, saved, intervals=[])
    result = run_atac_result_worker(plan)
    output = read_outputs(plan)
    assert result['state'] == 'partial'
    assert len([r for r in output['calculations']['issues'] if r['code'] == 'atac_projected_track_order_required']) == 4
    assert len(output['partitions']) == 0
    assert all(Path(plan['directory'], 'tracks', str(i) + '.jsonl').read_bytes() == Path(r['path']).read_bytes() for i, r in enumerate(plan['sheet_bundle']['tables']))


def test_empty_population_has_complete_zero_tables_and_invalid_parameters_reject_before_work(tmp_path):
    plan = saved_plan(tmp_path, sheet(), intervals=[])
    result = run_atac_result_worker(plan)
    output = read_outputs(plan)
    assert result['state'] == 'produced'
    assert output['partitions'] == output['components'] == output['regions'] == []
    assert all(r['exhausted'] for r in output['calculations']['stream_states'])
    plan['selector']['parameters']['pseudocount'] = 0
    with pytest.raises(ValueError):
        run_atac_result_worker(plan)


@pytest.mark.parametrize('case', ['wrong_key', 'wrong_identity', 'extra'])
def test_saved_bundle_must_match_every_actual_track_occurrence(tmp_path, case):
    plan = saved_plan(tmp_path, sheet())
    if case == 'wrong_key':
        plan['sheet_bundle']['tables'][0]['track_key'] = 'unrelated'
    elif case == 'wrong_identity':
        plan['sheet_bundle']['tables'][0]['file'] = plan['sheet_bundle']['tables'][1]['file']
    else:
        plan['sheet_bundle']['tables'].append(dict(plan['sheet_bundle']['tables'][0], track_key='extra'))
    plan['selector']['saved_sheet_bundle']['tables'] = [dict(track_key=r['track_key'], file=r['file']) for r in plan['sheet_bundle']['tables']]
    result = run_atac_result_worker(plan)
    assert result['state'] == 'partial'
    assert not (Path(plan['directory']) / 'calculations.json').exists()


def test_native_capture_worker_uses_actual_header_and_metadata_control_mock(tmp_path, monkeypatch):
    # Existing native result files are actual460 bytes. Command dispatch here is
    # explicitly mocked, so this is parser/capture integration, not live MACS2.
    from test_native_atac_differential_contracts import plan_fixture
    from test_native_atac_differential_producer import mock_commands
    from gene_annotation_episode.native_atac_differential_driver import run_atac_differential_driver
    mock_commands(monkeypatch)
    original = plan_fixture(tmp_path / 'native')
    run_atac_differential_driver(original)
    with Store(tmp_path / 'store') as store:
        captured = capture_atac_native_files(store, original_plan=original, source_action_receipt_ref='source_control_action',
            writer_closure_receipt_ref='source_control_terminal', driver_started=True)
        chosen = selector(dict(comparison=dict(comparison_key='comparison')), intervals=population(end=12000))
        plan = build_native_atac_worker_plan(directory=str(tmp_path / 'worker'), original_plan=original, selector=chosen, **captured_without_version(captured))
        result = run_atac_result_worker(plan)
    assert result['state'] == 'produced'
    output = read_outputs(plan)
    assert output['calculations']['depth_operands'] == dict(depth1=100, depth2=200, depth_unit='tags')
    assert output['calculations']['summary']['partition_coverage']['all_four_observed_bp'] == 8060
    assert [r['data_row_count'] for r in output['sheet']['tracks']] == [110, 35, 210, 69]
    assert all(r['input_ordinal'] == 0 and r['rows'][0]['length_bp'] == 12000 for r in output['sheet']['bam_references'])
    assert all(r['data_row_count'] == 1 and r['artifact']['producer_run_ref'].startswith('atac_header_inspection:')
        and r['artifact']['producer_source_ref'] == captured['bundle']['file']['artifact_ref'] for r in output['sheet']['bam_references'])
    assert len({r['artifact']['producer_run_ref'] for r in output['sheet']['bam_references']}) == 2
    assert output['sheet']['native_differential'][2]['data_row_count'] == 0
    example = os.environ.get('ATAC475_EXAMPLE')
    if example:
        Path(example).write_bytes(canonical(dict(provenance='actual retained native460 output with explicitly mocked producer command dispatch', **output)))


def captured_without_version(captured):
    return {key: value for key, value in captured.items() if key != 'version'}


def test_actual_mac2_outputs_and_saved_recalculation_after_native_capture_removed(tmp_path, monkeypatch):
    """Actual474 output, transported byte-for-byte; no mocked native measurements."""
    fixture = Path(os.environ['ATAC475_ACTUAL_NATIVE'])
    original = json.loads((fixture / 'native-success-plan.json').read_bytes())
    captured = json.loads((fixture / 'native-capture.json').read_bytes())
    native_directory = tmp_path / 'original-capture'
    # Relocate actual captures, preserving every original identity and role.
    # This isolated test can then remove its original native inputs safely.
    for record in [captured['bundle'], *(r['retained'] for r in captured['files'])]:
        if record is None:
            continue
        source = Path(record['path'])
        target = native_directory / 'artifacts' / record['file']['sha256'][:2] / record['file']['sha256']
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = source.read_bytes()
        assert identity(raw, record['file']['format']) == record['file']
        target.write_bytes(raw)
        record['path'] = str(target)
    chosen = selector(dict(comparison=dict(comparison_key=original['requested_job']['native_atac_differential']['request']['comparison_key'])),
        intervals=population(end=12000))
    plan = build_native_atac_worker_plan(directory=str(tmp_path / 'native-worker'), original_plan=original,
        selector=chosen, **captured_without_version(captured))
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    result = run_atac_result_worker(plan)
    output = read_outputs(plan)
    assert result['state'] == 'produced' and not result['failures']
    assert output['calculations']['depth_operands'] == dict(depth1=100, depth2=200, depth_unit='tags')
    assert [r['reported_numbers']['treatment_total_tags']['value'] for r in output['sheet']['peaks_xls']] == [105, 200]
    assert [t['rows']['row_count'] for t in output['sheet']['tracks']] == [110, 35, 210, 69]
    assert [r['rows'][0]['length_bp'] for r in output['sheet']['bam_references']] == [12000, 12000]
    assert output['calculations']['summary']['partition_coverage'] == dict(all_four_observed_bp=8060, unavailable_or_invalid_bp=3940, extent='complete')
    assert [r['count'] for r in output['calculations']['summary']['native_region_counts']] == [1, 1, 0]
    assert output['sheet']['comparison']['selected_parameters']['depth1_lexeme'] == '0.0001'
    assert output['sheet']['comparison']['selected_parameters']['depth2_lexeme'] == '0.0002'
    saved = tmp_path / 'saved'
    saved.mkdir()
    local = dict(sheet=None, tables=[])
    for row in result['outputs']:
        if row['role'] not in ('sheet', 'track_table'):
            continue
        source = Path(plan['directory']) / row['declaration']['relative_path']
        target = saved / ('sheet.json' if row['role'] == 'sheet' else row['table_key'] + '.jsonl')
        raw = source.read_bytes()
        target.write_bytes(raw)
        retained = dict(file=identity(raw, row['declaration']['format']), path=str(target))
        if row['role'] == 'sheet':
            local['sheet'] = retained
        else:
            local['tables'].append(dict(track_key=row['table_key'], **retained))
    public = dict(sheet=local['sheet']['file'], tables=[dict(track_key=r['track_key'], file=r['file']) for r in local['tables']])
    recalculation = build_saved_atac_worker_plan(directory=str(tmp_path / 'saved-worker'), sheet_bundle=local,
        selector=selector(output['sheet'], bundle=public, cutoff=1000, intervals=population(end=12000)))
    shutil.rmtree(native_directory)
    shutil.rmtree(plan['directory'])
    from gene_annotation_episode import atac_differential_result_worker as worker
    real_regular = worker._regular
    def only_saved(path):
        path = Path(path)
        assert path.is_relative_to(saved) or path.is_relative_to(recalculation['directory']), 'recalculation opened original native source'
        return real_regular(path)
    monkeypatch.setattr(worker, '_regular', only_saved)
    repeated = run_atac_result_worker(recalculation)
    changed = read_outputs(recalculation)
    assert repeated['state'] == 'produced'
    assert changed['sheet'] == output['sheet']
    assert [r['count'] for r in changed['calculations']['summary']['derived_region_counts']] == [0, 0, 0]
    assert changed['calculations']['depth_operands'] == output['calculations']['depth_operands']
    example = os.environ.get('ATAC475_ACTUAL_EXAMPLE')
    if example:
        Path(example).write_bytes(canonical(dict(provenance='actual MACS2 2.2.9.1 native474 output, retained transport; original native captures and first worker removed before saved-only recalculation',
            original_native_execution=original['identity'], native_sheet=output['sheet'], original_calculations=output['calculations'],
            original_regions=output['regions'], saved_recalculation=changed['calculations'])))


def test_native_failed_condition_preserves_second_peaks_and_depth(tmp_path, monkeypatch):
    from test_native_atac_differential_contracts import plan_fixture
    from test_native_atac_differential_producer import mock_commands
    from gene_annotation_episode.native_atac_differential_driver import run_atac_differential_driver
    mock_commands(monkeypatch, fail_first=True)
    original = plan_fixture(tmp_path / 'native')
    run_atac_differential_driver(original)
    with Store(tmp_path / 'store') as store:
        captured = capture_atac_native_files(store, original_plan=original, source_action_receipt_ref='source_control_action',
            writer_closure_receipt_ref='source_control_terminal', driver_started=True)
        chosen = selector(dict(comparison=dict(comparison_key='comparison'), callpeak_bindings=[dict(run_key='callpeak2')]),
            kind='native_peak_rows', intervals=population(end=12000))
        plan = build_native_atac_worker_plan(directory=str(tmp_path / 'worker'), original_plan=original, selector=chosen, **captured_without_version(captured))
        result = run_atac_result_worker(plan)
    output = read_outputs(plan)
    assert output['calculations']['depth_operands'] == dict(depth1=None, depth2=200, depth_unit='tags')
    assert output['sheet']['tracks'][0]['artifact']['producer_outcome'] == 'failed'
    assert output['sheet']['tracks'][1]['state']['availability'] == 'missing'
    assert output['sheet']['native_differential'][2]['data_row_count'] is None
    assert output['projection']['total_rows'] == 3 and output['projection']['row_extent'] == 'complete'
    assert any(r['code'] == 'native_nonzero_exit' for r in result['failures'])
