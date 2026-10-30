"""Retained native427 bytes with explicitly synthetic worker custody/authority.

No test invokes bedtools. Native-format evidence comes from the pinned packet427
fixtures. Deliberate loss, tampering, synthetic seals and fabricated transport
identities below test the pure worker boundary; they grant no episode authority.
Run only through this workload's bounded local_jobs verification runner.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time

import pytest

from gene_annotation_episode import genomic_overlap_result_worker as worker
from gene_annotation_episode.genomic_overlap_contracts import canonical_genomic_overlap_sheet_sha256
from gene_annotation_episode.native_genomic_overlap_contracts import genomic_overlap_output_files


PACKET = Path(__file__).resolve().parents[1] / 'verification/tool_graders_genomic_overlap_result_worker_2026-10-27_432'


def canonical(value, newline=False):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode() + (b'\n' if newline else b'')


def identity(raw, format_name, name):
    return {'artifact_ref': 'synthetic-worker-transport:' + name,
        'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw), 'format': format_name}


def retained(tmp_path, raw, format_name, name):
    path = tmp_path / 'retained' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {'file': identity(raw, format_name, name), 'path': str(path)}


def parameters(minimum=1):
    return {'version': 'genomic_overlap_calculation_parameters_v1', 'minimum_overlap_bp': minimum,
        'minimum_a_fraction': {'numerator': 0, 'denominator': 1},
        'minimum_b_fraction': {'numerator': 0, 'denominator': 1}}


def make_plan(tmp_path, case='three'):
    fixture = PACKET / 'fixtures' / case
    original = json.loads((fixture / 'plan.json').read_bytes())
    request = original['requested_job']['native_genomic_overlap']['request']
    bundle_path = fixture / 'native/bundle.json'
    batch = json.loads(bundle_path.read_bytes()) if bundle_path.exists() else None
    files = []
    for index, spec in enumerate(genomic_overlap_output_files(request)[:-1]):
        path = fixture / 'native' / spec['relative_path']
        source = retained(tmp_path, path.read_bytes(), spec['format'], f'file-{index}') if path.exists() else None
        if batch:
            declaration = batch['files'][index]['declaration']
            capture = {'declared': declaration, 'observed': source['file'] if source else None,
                'outcome': 'verified' if source else 'declared_absent' if declaration['state'] == 'absent' else 'unavailable',
                'failure': None if source or declaration['state'] == 'absent' else 'capture_file_unavailable'}
        else:
            capture = None
        files.append({'specification': spec, 'declaration_source': 'batch' if batch else 'none',
                      'capture': capture, 'retained': source})
    if batch is None:
        by_path = {row['specification']['relative_path']: row for row in files}
        for row in files:
            if row['specification']['role'] == 'pair_manifest' and row['retained']:
                manifest = json.loads(Path(row['retained']['path']).read_bytes())
                for declared in manifest['files']:
                    target = by_path[declared['declaration']['relative_path']]
                    target['declaration_source'] = 'pair'
                    source = target['retained']
                    target['capture'] = {'declared': declared['declaration'],
                        'observed': source['file'] if source else None,
                        'outcome': 'verified' if source else 'unavailable',
                        'failure': None if source else 'capture_file_unavailable'}
    return {'version': 'genomic_overlap_result_worker_plan_v1', 'mode': 'native_result',
        'directory': str(tmp_path / 'output'), 'original_plan': original,
        'batch': retained(tmp_path, bundle_path.read_bytes(), 'genomic_overlap_native_batch_v1', 'batch') if batch else None,
        'files': files, 'selector': {'version': 'genomic_overlap_result_selector_v1', 'mode': 'native_result',
            'comparison_keys': [p['comparison_key'] for p in request['comparisons']], 'saved_sheet_file': None,
            'parameters': parameters(), 'projection': {'kind': 'pair_metrics', 'offset': 0, 'limit': 100,
                'measurement_fields': ['unfiltered.jaccard_bp'], 'occurrence_keys': []}},
        'source_action_receipt_ref': 'synthetic-original-selected-action',
        'writer_closure_receipt_ref': 'synthetic-observed-terminal-writer-closure',
        'driver_state': 'sealed_batch' if batch else 'unsealed_attempt', 'failures': []}


def row(plan, key):
    return next(r for r in plan['files'] if r['specification']['file_key'] == key)


def lose(plan, key, *, physical=False):
    value = row(plan, key)
    if physical:
        Path(value['retained']['path']).unlink()
    else:
        value['retained'] = None


def corrupt(plan, key):
    path = Path(row(plan, key)['retained']['path'])
    path.write_bytes(b'corrupt retained representation\n')


def load_outputs(plan):
    root = Path(plan['directory'])
    return tuple(json.loads((root / name).read_bytes()) for name in
                 ('sheet.json', 'components.json', 'projection.json', 'diagnostics.json'))


def saved_plan(tmp_path, native, minimum=4):
    source = Path(native['directory']) / 'sheet.json'
    sheet = retained(tmp_path, source.read_bytes(), 'genomic_region_overlap_sheet_v1', 'saved-sheet')
    selector = deepcopy(native['selector'])
    selector.update(mode='saved_sheet_recalculation', saved_sheet_file=sheet['file'])
    selector['parameters'] = parameters(minimum)
    return {'version': 'genomic_overlap_result_worker_plan_v1', 'mode': 'saved_sheet_recalculation',
            'directory': str(tmp_path / 'recalculated'), 'sheet': sheet, 'selector': selector}


@pytest.fixture(autouse=True)
def no_native_or_network(monkeypatch):
    def prohibited(*args, **kwargs):
        pytest.fail('result worker attempted network or native execution')
    monkeypatch.setattr(subprocess, 'Popen', prohibited)
    monkeypatch.setattr(subprocess, 'run', prohibited)
    monkeypatch.setattr(socket, 'create_connection', prohibited)


def test_actual_native_bytes_exact_answers_order_declarations_and_no_lf(tmp_path, monkeypatch):
    plan = make_plan(tmp_path)
    before = deepcopy(plan)
    allowed = {r['retained']['path'] for r in plan['files'] if r['retained']} | {plan['batch']['path']}
    read, calls = worker._read, []
    def supplied_only(path):
        assert path in allowed
        calls.append(path)
        return read(path)
    monkeypatch.setattr(worker, '_read', supplied_only)
    calculate = worker.calculate_genomic_overlap_components
    calculations = []
    def once(sheet, **kwargs):
        calculations.append(kwargs)
        return calculate(sheet, **kwargs)
    monkeypatch.setattr(worker, 'calculate_genomic_overlap_components', once)
    result = worker.run_genomic_overlap_result_worker(plan)
    assert plan == before and len(calculations) == 1
    assert result['state'] == 'produced' and not result['failures']
    sheet, components, projection, diagnostics = load_outputs(plan)
    assert [p['comparison_key'] for p in sheet['comparisons']] == ['AB', 'AC', 'BC']
    assert [p['unfiltered']['pairwise_overlap_bp_sum'] for p in components['pairs']] == [8, 5, 2]
    assert [p['unfiltered']['intersection_union_bp'] for p in components['pairs']] == [5, 5, 2]
    assert [p['unfiltered']['combined_union_bp'] for p in components['pairs']] == [15, 20, 13]
    assert [p['unfiltered']['jaccard_bp']['value'] for p in components['pairs']] == pytest.approx([1/3, 1/4, 2/13])
    assert all(list(p['measurements']) == ['unfiltered.jaccard_bp'] for p in projection['pair_rows'])
    assert [p['batch_pair_index'] for p in diagnostics['pairs']] == [0, 1, 2]
    assert [r['role'] for r in result['outputs']] == ['sheet', 'components', 'projection', 'diagnostics']
    for output in result['outputs']:
        declaration = output['declaration']
        raw = (Path(plan['directory']) / declaration['relative_path']).read_bytes()
        assert not raw.endswith(b'\n') and raw == canonical(json.loads(raw))
        assert hashlib.sha256(raw).hexdigest() == declaration['sha256']
        assert len(raw) == declaration['size_bytes']
        assert 'artifact_ref' not in declaration
    digest = result['source_sheet_sha256']
    assert digest == canonical_genomic_overlap_sheet_sha256(sheet) == result['outputs'][0]['declaration']['sha256']
    assert digest == components['source_sheet_sha256'] == projection['source_sheet_sha256']
    assert sheet['comparisons'][0]['receipt']['a']['canonical_file'] == sheet['comparisons'][1]['receipt']['a']['canonical_file']
    (tmp_path / 'ACTUAL_RETAINED_NATIVE_RESULT.json').write_bytes(canonical({'evidence':
        'actual_native427_bytes_with_synthetic_worker_transport_only', 'result': result,
        'unfiltered': [p['unfiltered'] for p in components['pairs']], 'projection': projection}))


@pytest.mark.parametrize('case,expected', [
    ('no_hit', (0, 0, 0)), ('duplicates', (4, 20, 5)), ('long', (1, 1, 1)), ('variable', (4, 50, 50)),
])
def test_actual_retained_native_populations(tmp_path, case, expected):
    plan = make_plan(tmp_path, case)
    worker.run_genomic_overlap_result_worker(plan)
    sheet, components, _, _ = load_outputs(plan)
    metrics = components['pairs'][0]['unfiltered']
    assert tuple(metrics[k] for k in ('native_pair_count', 'pairwise_overlap_bp_sum', 'intersection_union_bp')) == expected
    assert sheet['comparisons'][0]['result_extent'] == 'complete'
    if case == 'no_hit':
        assert sheet['comparisons'][0]['receipt']['stdout']['size_bytes'] == 0
        assert metrics['jaccard_bp']['value'] == 0


@pytest.mark.parametrize('case', ['empty_c', 'invalid_c', 'partial_c', 'missing_c', 'wrong_c', 'missing_binary'])
def test_original_native_failure_and_analytic_meanings_survive(tmp_path, case):
    plan = make_plan(tmp_path, case)
    worker.run_genomic_overlap_result_worker(plan)
    sheet, components, _, _ = load_outputs(plan)
    if case == 'missing_binary':
        assert all(p['receipt']['outcome'] == 'not_executed' for p in sheet['comparisons'])
        assert all(p['receipt']['derivation'] == 'bedtools_intersect' for p in sheet['comparisons'])
        assert all(p['unfiltered']['jaccard_bp']['value'] is None for p in components['pairs'])
        assert all(s['region_count'] is not None for s in components['sets'])
    else:
        assert components['pairs'][0]['unfiltered']['jaccard_bp']['value'] == 1/3
        expected = 'validated_empty_input' if case == 'empty_c' else (
            'not_executed_invalid_input' if case in ('invalid_c', 'partial_c') else 'bedtools_intersect')
        assert [p['receipt']['derivation'] for p in sheet['comparisons'][1:]] == [expected] * 2
        assert all(p['receipt']['outcome'] == 'not_executed' and p['receipt']['stdout'] is None
                   for p in sheet['comparisons'][1:])
        values = [p['unfiltered']['jaccard_bp']['value'] for p in components['pairs'][1:]]
        assert values == ([0, 0] if case == 'empty_c' else [None, None])


@pytest.mark.parametrize('case', ['three', 'empty_c'])
@pytest.mark.parametrize('change,basis', [
    ('missing_original', 'retained_parsed_set'), ('corrupt_original', 'retained_parsed_set'),
    ('missing_parsed', 'reparsed_retained_original'), ('corrupt_parsed', 'reparsed_retained_original'),
])
def test_missing_or_corrupt_representation_uses_exact_other_map(tmp_path, case, change, basis):
    plan = make_plan(tmp_path, case)
    if change.startswith('missing'):
        lose(plan, 's2:original' if change.endswith('original') else 's2:parsed')
    else:
        corrupt(plan, 's2:original' if change.endswith('original') else 's2:parsed')
    worker.run_genomic_overlap_result_worker(plan)
    sheet, components, _, diagnostics = load_outputs(plan)
    assert diagnostics['sets'][2]['basis'] == basis
    assert diagnostics['sets'][2]['failures']
    assert sheet['sets'][2]['issues'] == []
    assert [p['result_extent'] for p in components['pairs']] == ['complete'] * 3
    assert components['pairs'][0]['unfiltered']['jaccard_bp']['value'] == 1/3


@pytest.mark.parametrize('physical', [False, True])
def test_original_empty_c_loses_both_maps_ab_survives_and_saved_recalculation(tmp_path, physical):
    native = make_plan(tmp_path / 'native', 'empty_c')
    worker.run_genomic_overlap_result_worker(native)
    old_sheet = Path(native['directory'], 'sheet.json').read_bytes()
    old_result = Path(native['directory'], 'worker-result.json').read_bytes()
    plan = deepcopy(native)
    plan['directory'] = str(tmp_path / 'lost-result')
    lose(plan, 's2:original', physical=physical)
    lose(plan, 's2:parsed', physical=physical)
    plan['selector']['comparison_keys'] = ['AB']
    worker.run_genomic_overlap_result_worker(plan)
    sheet, components, projection, diagnostics = load_outputs(plan)
    assert [p['result_extent'] for p in components['pairs']] == ['complete', 'unavailable', 'unavailable']
    assert [p['comparison_key'] for p in sheet['comparisons']] == ['AB', 'AC', 'BC']
    assert components['pairs'][0]['unfiltered']['jaccard_bp']['value'] == 1/3
    assert components['sets'][2]['region_count'] is None and components['sets'][2]['union_bp'] is None
    assert components['sets'][2]['input_data_row_count'] is None and components['sets'][2]['valid_region_count'] == 0
    for p in components['pairs'][1:]:
        assert p['unfiltered']['jaccard_bp'] == {'numerator': None, 'denominator': None,
            'value': None, 'missing_reason': 'unavailable_input'}
        assert p['observed']['interpretation'] == 'unavailable'
    for p in sheet['comparisons'][1:]:
        assert p['receipt']['derivation'] == 'validated_empty_input'
        assert p['receipt']['native_result_extent'] == 'complete'
        assert p['receipt']['capture_extent'] == 'unavailable'
    assert projection['failures'] == [] and len(projection['pair_rows']) == 1
    assert diagnostics['sets'][2]['basis'] == 'unavailable'
    assert Path(native['directory'], 'sheet.json').read_bytes() == old_sheet
    assert Path(native['directory'], 'worker-result.json').read_bytes() == old_result
    saved = saved_plan(tmp_path / 'saved', plan)
    worker.run_genomic_overlap_result_worker(saved)
    new_sheet, new_components, _, _ = load_outputs(saved)
    assert new_sheet == sheet and new_components['pairs'][0]['selected']['selected_pair_count'] == 1


@pytest.mark.parametrize('key,expected_extent,lower_bound', [
    ('p0:stdout', 'unavailable', None), ('p0:stderr', 'partial', 8), ('s0:canonical', 'partial', 8),
])
def test_capture_loss_preserves_original_success_and_qualified_lower_bounds(tmp_path, key, expected_extent, lower_bound):
    plan = make_plan(tmp_path)
    lose(plan, key)
    worker.run_genomic_overlap_result_worker(plan)
    sheet, components, _, _ = load_outputs(plan)
    parsed, pair = sheet['comparisons'][0], components['pairs'][0]
    assert parsed['receipt']['outcome'] == 'succeeded' and parsed['receipt']['returncode'] == 0
    assert parsed['receipt']['native_result_extent'] == 'complete'
    assert parsed['result_extent'] == expected_extent and pair['unfiltered']['jaccard_bp']['value'] is None
    assert pair['observed']['observed_pairwise_bp_sum'] == lower_bound
    assert components['pairs'][2]['result_extent'] == 'complete'


def test_canonical_corruption_cannot_support_lower_bound(tmp_path):
    plan = make_plan(tmp_path)
    corrupt(plan, 's0:canonical')
    worker.run_genomic_overlap_result_worker(plan)
    sheet, components, _, _ = load_outputs(plan)
    assert len(sheet['comparisons'][0]['valid_pairs']) == 2
    assert components['pairs'][0]['observed']['interpretation'] == 'unavailable'
    assert components['pairs'][2]['unfiltered']['jaccard_bp']['value'] == 2/13


def test_missing_redundant_pair_seal_keeps_embedded_facts_exact(tmp_path):
    plan = make_plan(tmp_path)
    lose(plan, 'p0:manifest')
    worker.run_genomic_overlap_result_worker(plan)
    _, components, _, diagnostics = load_outputs(plan)
    assert components['pairs'][0]['result_extent'] == 'complete'
    assert diagnostics['pairs'][0]['manifest_origin'] == 'batch'
    assert diagnostics['pairs'][0]['failures']


def test_retained_synthetic_nonzero_keeps_partial_rows_and_independent_pairs(tmp_path):
    plan = make_plan(tmp_path, 'synthetic_nonzero')
    worker.run_genomic_overlap_result_worker(plan)
    sheet, components, _, _ = load_outputs(plan)
    assert sheet['comparisons'][0]['receipt']['returncode'] == 7
    assert sheet['comparisons'][0]['receipt']['outcome'] == 'failed'
    assert components['pairs'][0]['unfiltered']['jaccard_bp']['value'] is None
    assert components['pairs'][0]['observed']['observed_pairwise_bp_sum'] == 3
    assert components['pairs'][0]['observed']['interpretation'] == 'lower_bound_subset'
    assert [p['result_extent'] for p in components['pairs']] == ['partial', 'complete', 'complete']


def test_actual_killed_native_attempt_preserves_first_independent_seal(tmp_path, monkeypatch):
    plan = make_plan(tmp_path, 'killed')
    assert plan['batch'] is None
    # This actual interrupted fixture contains a large third map. Expose
    # measured stage duration in the bounded runner without changing its data.
    def trace(name, function):
        def measured(*args, **kwargs):
            started = time.monotonic()
            print(json.dumps({'large_fixture_stage': name, 'state': 'started'}), flush=True)
            result = function(*args, **kwargs)
            print(json.dumps({'large_fixture_stage': name, 'state': 'finished',
                              'elapsed_seconds': time.monotonic() - started}), flush=True)
            return result
        return measured
    for name in ('parse_region_set', 'parse_bedtools_intersect_wo',
                 'build_genomic_overlap_sheet', 'calculate_genomic_overlap_components',
                 'project_genomic_overlap_result'):
        monkeypatch.setattr(worker, name, trace(name, getattr(worker, name)))
    worker.run_genomic_overlap_result_worker(plan)
    sheet, components, _, diagnostics = load_outputs(plan)
    assert diagnostics['pairs'][0]['manifest_origin'] == 'pair'
    assert components['pairs'][0]['result_extent'] == 'complete'
    assert components['pairs'][0]['unfiltered']['jaccard_bp']['value'] == 1/3
    assert all(p['receipt']['outcome'] == 'unknown' for p in sheet['comparisons'][1:])
    assert all(p['unfiltered']['jaccard_bp']['value'] is None for p in components['pairs'][1:])


def test_lost_batch_uses_independent_seals_and_exact_originals(tmp_path):
    plan = make_plan(tmp_path)
    plan['batch'] = None  # Original sealed_batch history is preserved.
    worker.run_genomic_overlap_result_worker(plan)
    _, components, _, diagnostics = load_outputs(plan)
    assert plan['driver_state'] == 'sealed_batch'
    assert [p['manifest_origin'] for p in diagnostics['pairs']] == ['pair'] * 3
    assert [p['result_extent'] for p in components['pairs']] == ['complete'] * 3


def test_lone_parsed_map_without_batch_is_diagnostic_only(tmp_path):
    plan = make_plan(tmp_path, 'empty_c')
    plan['batch'] = None
    lose(plan, 's2:original')
    worker.run_genomic_overlap_result_worker(plan)
    _, components, _, diagnostics = load_outputs(plan)
    assert diagnostics['sets'][2]['basis'] == 'unavailable'
    assert components['pairs'][0]['unfiltered']['jaccard_bp']['value'] == 1/3
    assert [p['result_extent'] for p in components['pairs']] == ['complete', 'unavailable', 'unavailable']


def test_no_driver_and_started_without_metadata_stay_distinct(tmp_path):
    base = make_plan(tmp_path)
    for state in ('not_started', 'unsealed_attempt'):
        plan = deepcopy(base)
        plan['directory'] = str(tmp_path / state)
        plan.update(batch=None, driver_state=state)
        for r in plan['files']:
            r.update(declaration_source='none', capture=None, retained=None)
        worker.run_genomic_overlap_result_worker(plan)
        sheet, components, _, _ = load_outputs(plan)
        assert all(s['result_extent'] == 'unavailable' for s in sheet['sets'])
        expected = 'not_executed' if state == 'not_started' else 'unknown'
        assert all(p['receipt']['outcome'] == expected for p in sheet['comparisons'])
        assert all(p['unfiltered']['native_pair_count'] is None for p in components['pairs'])


@pytest.mark.parametrize('raw,code', [
    (b'chr1\t0\t10\ts0_r0\tchr1\t7\t12\ts1_r0\t4\n', 'overlap_width_conflict'),
    (b'chr1\t0\t10\tforeign\tchr1\t7\t12\ts1_r0\t3\n', 'native_pair_identity_conflict'),
    (b'chr1\t0\t10\ts0_r0\tchr1\t7\t12\ts1_r0\t3\n' * 2, 'duplicate_native_pair'),
])
def test_synthetic_unsealed_malformed_rows_are_located_without_exact_totals(tmp_path, raw, code):
    plan = make_plan(tmp_path)
    plan.update(batch=None, driver_state='unsealed_attempt')
    for r in plan['files']:
        r.update(declaration_source='none', capture=None)
    lose(plan, 'p0:manifest')
    r = row(plan, 'p0:stdout')
    r['retained'] = retained(tmp_path, raw, r['specification']['format'], 'synthetic-unsealed-stdout')
    # Other actual independent seals still require their original declarations.
    for ordinal in (1, 2):
        manifest = json.loads(Path(row(plan, f'p{ordinal}:manifest')['retained']['path']).read_bytes())
        by_path = {r['specification']['relative_path']: r for r in plan['files']}
        for declared in manifest['files']:
            target = by_path[declared['declaration']['relative_path']]
            target.update(declaration_source='pair', capture={'declared': declared['declaration'],
                'observed': target['retained']['file'], 'outcome': 'verified', 'failure': None})
    worker.run_genomic_overlap_result_worker(plan)
    sheet, components, _, _ = load_outputs(plan)
    assert any(f['code'] == code for f in sheet['comparisons'][0]['issues'])
    assert components['pairs'][0]['unfiltered']['native_pair_count'] is None
    assert components['pairs'][1]['result_extent'] == 'complete'


def test_synthetic_canonical_publication_failure_is_not_reclassified_analytic(tmp_path):
    plan = make_plan(tmp_path, 'synthetic_canonical_failure')
    original_batch = json.loads(Path(plan['batch']['path']).read_bytes())
    worker.run_genomic_overlap_result_worker(plan)
    sheet, _, _, _ = load_outputs(plan)
    for original, current in zip(original_batch['pairs'], sheet['comparisons']):
        if original['disposition'] == 'native_unavailable':
            assert current['receipt']['derivation'] == 'bedtools_intersect'
            assert current['receipt']['outcome'] == 'not_executed'


def test_saved_mode_reads_only_unchanged_sheet_and_changes_selected_values(tmp_path, monkeypatch):
    native = make_plan(tmp_path / 'native')
    worker.run_genomic_overlap_result_worker(native)
    original_raw = Path(native['directory'], 'sheet.json').read_bytes()
    original_components = Path(native['directory'], 'components.json').read_bytes()
    saved = saved_plan(tmp_path / 'saved', native)
    saved['selector']['projection']['measurement_fields'] = ['selected.selected_pair_count', 'selected.a_region_overlap_fraction']
    shutil.rmtree(tmp_path / 'native/retained')
    read = worker._read
    def sheet_only(path):
        assert path == saved['sheet']['path']
        return read(path)
    monkeypatch.setattr(worker, '_read', sheet_only)
    monkeypatch.setattr(worker, 'parse_region_set', lambda *a, **k: pytest.fail('saved mode reparse'))
    monkeypatch.setattr(worker, 'parse_bedtools_intersect_wo', lambda *a, **k: pytest.fail('saved mode native read'))
    monkeypatch.setattr(worker, 'validate_genomic_overlap_run_plan', lambda *a, **k: pytest.fail('saved mode original plan'))
    result = worker.run_genomic_overlap_result_worker(saved)
    _, components, projection, diagnostics = load_outputs(saved)
    assert result['state'] == 'produced'
    assert Path(saved['directory'], 'sheet.json').read_bytes() == original_raw
    assert Path(native['directory'], 'components.json').read_bytes() == original_components
    assert [p['selected']['selected_pair_count'] for p in components['pairs']] == [1, 1, 0]
    assert components['pairs'][0]['selected']['a_region_overlap_fraction']['value'] == 1/2
    assert all(set(p['measurements']) == set(saved['selector']['projection']['measurement_fields']) for p in projection['pair_rows'])
    assert diagnostics['sets'] == diagnostics['pairs'] == []
    (tmp_path / 'SAVED_RECALCULATION.json').write_bytes(canonical({'source_sheet_sha256': result['source_sheet_sha256'],
        'source_sheet_preserved': True, 'selected_counts': [p['selected']['selected_pair_count'] for p in components['pairs']],
        'AB_selected_occurrence_fraction': components['pairs'][0]['selected']['a_region_overlap_fraction']}))


@pytest.mark.parametrize('change', ['missing', 'corrupt', 'lf', 'duplicate', 'nonfinite', 'schema'])
def test_saved_invalid_input_has_no_fabricated_scientific_outputs(tmp_path, change):
    native = make_plan(tmp_path / 'native')
    worker.run_genomic_overlap_result_worker(native)
    saved = saved_plan(tmp_path / 'saved', native)
    path = Path(saved['sheet']['path'])
    if change == 'missing':
        path.unlink()
    elif change == 'corrupt':
        path.write_bytes(b'broken')
    else:
        raw = path.read_bytes()
        if change == 'lf':
            raw += b'\n'
        elif change == 'duplicate':
            raw = b'{"version":1,"version":2}'
        elif change == 'nonfinite':
            raw = b'{"value":NaN}'
        else:
            raw = b'{}'
        path.write_bytes(raw)
        saved['sheet']['file'] = identity(raw, 'genomic_region_overlap_sheet_v1', 'invalid-saved-' + change)
        saved['selector']['saved_sheet_file'] = saved['sheet']['file']
    result = worker.run_genomic_overlap_result_worker(saved)
    assert result['state'] == 'unavailable' and result['source_sheet_sha256'] is None
    assert [r['declaration']['state'] for r in result['outputs']] == ['absent'] * 3 + ['present']
    assert result['failures']


@pytest.mark.parametrize('mutation', ['extra', 'bool', 'order', 'capture', 'path', 'source', 'selector', 'overlap', 'mode', 'alias'])
def test_api_plan_validation_is_strict_and_has_no_io(tmp_path, monkeypatch, mutation):
    plan = make_plan(tmp_path)
    if mutation == 'extra': plan['extra'] = True
    elif mutation == 'bool': plan['selector']['parameters']['minimum_overlap_bp'] = True
    elif mutation == 'order': plan['files'][4], plan['files'][8] = plan['files'][8], plan['files'][4]
    elif mutation == 'capture': row(plan, 's0:original')['capture']['observed']['sha256'] = '0' * 64
    elif mutation == 'path': row(plan, 's0:original')['retained']['path'] += '/../bad'
    elif mutation == 'source': row(plan, 's0:original')['declaration_source'] = 'none'
    elif mutation == 'selector': plan['selector']['comparison_keys'] = ['BC', 'AB']
    elif mutation == 'overlap': row(plan, 's0:original')['retained']['path'] = plan['directory'] + '/file'
    elif mutation == 'mode': plan['selector']['mode'] = 'saved_sheet_recalculation'
    else: row(plan, 's1:original')['retained']['path'] = row(plan, 's0:original')['retained']['path']
    monkeypatch.setattr(worker, '_read', lambda *a, **k: pytest.fail('validator performed I/O'))
    with pytest.raises(ValueError):
        worker.validate_genomic_overlap_result_worker_plan(plan)
    assert not Path(plan['directory']).exists()


@pytest.mark.parametrize('kind', ['file_symlink', 'directory_symlink', 'fifo'])
def test_nonregular_retained_sources_are_not_followed(tmp_path, kind):
    plan = make_plan(tmp_path)
    r = row(plan, 's2:original')
    path = Path(r['retained']['path'])
    original = path.read_bytes()
    path.unlink()
    if kind == 'file_symlink':
        other = tmp_path / 'elsewhere'
        other.write_bytes(original)
        path.symlink_to(other)
    elif kind == 'directory_symlink':
        target = tmp_path / 'other-directory'
        target.mkdir()
        (target / 'file').write_bytes(original)
        link = tmp_path / 'linked-directory'
        link.symlink_to(target, target_is_directory=True)
        r['retained']['path'] = str(link / 'file')
    else:
        os.mkfifo(path)
    worker.run_genomic_overlap_result_worker(plan)
    _, components, _, diagnostics = load_outputs(plan)
    assert components['pairs'][1]['result_extent'] == 'complete'
    assert diagnostics['sets'][2]['original_file'] is None
    assert diagnostics['sets'][2]['basis'] == 'retained_parsed_set'


def test_detached_validation_immutable_replay_and_conflicting_publication(tmp_path):
    plan = make_plan(tmp_path)
    checked = worker.validate_genomic_overlap_result_worker_plan(plan)
    checked['selector']['parameters']['minimum_overlap_bp'] = 9
    assert plan['selector']['parameters']['minimum_overlap_bp'] == 1
    result = worker.run_genomic_overlap_result_worker(plan)
    before = {p.name: p.read_bytes() for p in Path(plan['directory']).iterdir()}
    assert worker.run_genomic_overlap_result_worker(plan) == result
    returned = worker.validate_genomic_overlap_result_worker_result(result)
    returned['outputs'][0]['declaration']['sha256'] = '0' * 64
    assert returned != result
    plan['selector']['parameters']['minimum_overlap_bp'] = 4
    with pytest.raises(ValueError, match='output_conflict'):
        worker.run_genomic_overlap_result_worker(plan)
    assert {p.name: p.read_bytes() for p in Path(plan['directory']).iterdir()} == before


def test_result_schema_rejects_fabricated_identities_and_dependency_conflicts(tmp_path):
    plan = make_plan(tmp_path)
    result = worker.run_genomic_overlap_result_worker(plan)
    for change in ('identity', 'order', 'hash', 'state', 'diagnostics', 'sheet_dependency'):
        bad = deepcopy(result)
        if change == 'identity': bad['outputs'][0]['declaration']['artifact_ref'] = 'invented'
        elif change == 'order': bad['outputs'].reverse()
        elif change == 'hash': bad['source_sheet_sha256'] = '0' * 64
        elif change == 'state': bad['state'] = 'partial'
        else:
            i = 3 if change == 'diagnostics' else 0
            bad['outputs'][i]['declaration'].update(state='absent', sha256=None, size_bytes=None)
            if i == 0: bad['source_sheet_sha256'] = None
        with pytest.raises(ValueError):
            worker.validate_genomic_overlap_result_worker_result(bad)


def test_cli_requires_single_canonical_no_lf_plan(tmp_path):
    plan = make_plan(tmp_path)
    path = tmp_path / 'worker-plan.json'
    path.write_bytes(canonical(plan))
    assert worker.main([str(path)]) == 0
    path.write_bytes(canonical(plan, newline=True))
    with pytest.raises(ValueError, match='noncanonical'):
        worker.main([str(path)])
    for arguments in ([], [str(path), str(path)]):
        with pytest.raises(ValueError):
            worker.main(arguments)


def test_unexpected_calculator_error_does_not_become_empty_science(tmp_path, monkeypatch):
    plan = make_plan(tmp_path)
    def bug(*args, **kwargs):
        raise ValueError('unexpected programming defect')
    monkeypatch.setattr(worker, 'calculate_genomic_overlap_components', bug)
    with pytest.raises(ValueError, match='programming defect'):
        worker.run_genomic_overlap_result_worker(plan)
    assert not Path(plan['directory'], 'worker-result.json').exists()


def rewrite_unsealed_json(plan, key, value, tmp_path, *, newline=True):
    """Synthetic transport mutation, never an original authenticated seal."""
    r = row(plan, key)
    r.update(declaration_source='none', capture=None,
        retained=retained(tmp_path, canonical(value, newline=newline), r['specification']['format'],
                          'synthetic-' + key.replace(':', '-')))


def test_entire_parsed_record_must_equal_exact_original_reparse(tmp_path):
    plan = make_plan(tmp_path)
    plan['batch'] = None
    parsed = json.loads(Path(row(plan, 's2:parsed')['retained']['path']).read_bytes())
    # G1 permits unique group identifiers, so this is structurally valid but
    # differs from the exact original-byte parser output.
    parsed['coordinate_groups'][0]['group_key'] = 'synthetic-different-group'
    rewrite_unsealed_json(plan, 's2:parsed', parsed, tmp_path)
    worker.run_genomic_overlap_result_worker(plan)
    sheet, components, _, diagnostics = load_outputs(plan)
    assert diagnostics['sets'][2]['basis'] == 'reparsed_retained_original'
    assert any(f['code'] == 'original_attempt_mismatch' for f in diagnostics['sets'][2]['failures'])
    assert sheet['sets'][2]['coordinate_groups'][0]['group_key'] == 'C:coordinate:0'
    assert all(p['result_extent'] == 'complete' for p in components['pairs'])


def test_synthetic_conflicting_independent_seals_cannot_choose_canonical_bytes(tmp_path):
    plan = make_plan(tmp_path)
    plan['batch'] = None
    manifest = json.loads(Path(row(plan, 'p1:manifest')['retained']['path']).read_bytes())
    manifest['files'][0]['declaration']['sha256'] = '0' * 64
    rewrite_unsealed_json(plan, 'p1:manifest', manifest, tmp_path)
    worker.run_genomic_overlap_result_worker(plan)
    sheet, components, _, diagnostics = load_outputs(plan)
    for pair in components['pairs'][:2]:
        assert pair['unfiltered']['jaccard_bp']['value'] is None
        assert pair['observed']['interpretation'] == 'unavailable'
    assert components['pairs'][2]['unfiltered']['jaccard_bp']['value'] == 2/13
    assert sheet['comparisons'][0]['receipt']['a']['canonical_file'] is None
    assert any(f['code'] == 'original_attempt_mismatch' and f['set_key'] == 'A'
               for f in diagnostics['failures'])


@pytest.mark.parametrize('change', ['foreign_identity', 'missing_lf'])
def test_rejected_independent_seal_never_establishes_original_success(tmp_path, change):
    plan = make_plan(tmp_path)
    plan['batch'] = None
    manifest = json.loads(Path(row(plan, 'p0:manifest')['retained']['path']).read_bytes())
    if change == 'foreign_identity':
        manifest['identity']['attempt_id'] = 'synthetic-unrelated-attempt'
    rewrite_unsealed_json(plan, 'p0:manifest', manifest, tmp_path, newline=change != 'missing_lf')
    worker.run_genomic_overlap_result_worker(plan)
    sheet, components, _, diagnostics = load_outputs(plan)
    assert sheet['comparisons'][0]['receipt']['outcome'] == 'unknown'
    assert diagnostics['pairs'][0]['manifest_origin'] == 'none'
    assert diagnostics['pairs'][0]['failures']
    assert components['pairs'][0]['unfiltered']['jaccard_bp']['value'] is None
    assert components['pairs'][2]['result_extent'] == 'complete'


def test_capture_declaration_must_join_original_batch(tmp_path):
    plan = make_plan(tmp_path)
    r = row(plan, 's2:parsed')
    # Self-consistent new capture bytes cannot override the original declaration.
    raw = b'{}\n'
    r['retained'] = retained(tmp_path, raw, r['specification']['format'], 'synthetic-replacement')
    r['capture']['observed'] = r['retained']['file']
    r['capture']['declared'].update(sha256=r['retained']['file']['sha256'], size_bytes=len(raw))
    worker.run_genomic_overlap_result_worker(plan)
    _, components, _, diagnostics = load_outputs(plan)
    assert diagnostics['sets'][2]['basis'] == 'reparsed_retained_original'
    assert any(f['code'] == 'original_attempt_mismatch' for f in diagnostics['sets'][2]['failures'])
    assert components['pairs'][1]['result_extent'] == 'complete'


def test_host_current_capture_failure_remains_diagnostic_after_map_recovery(tmp_path):
    plan = make_plan(tmp_path)
    r = row(plan, 's2:original')
    index = plan['files'].index(r)
    failure = worker._failure('input_unavailable', 'capture', set_key='C',
        artifact_ref=r['retained']['file']['artifact_ref'], field_path=f'/files/{index}/retained',
        requirement='complete_input')
    plan['failures'].append(failure)
    lose(plan, 's2:original')
    worker.run_genomic_overlap_result_worker(plan)
    sheet, components, projection, diagnostics = load_outputs(plan)
    assert failure in diagnostics['failures']
    assert sheet['sets'][2]['issues'] == []
    assert all(p['result_extent'] == 'complete' for p in components['pairs'])
    assert projection['failures'] == []


def test_host_canonical_conflict_is_not_erased_by_original_artifact_alias(tmp_path):
    plan = make_plan(tmp_path)
    canonical_row = row(plan, 's0:canonical')
    index = plan['files'].index(canonical_row)
    # A field location remains authoritative even when an artifact reference
    # also occurs in another representation's provenance.
    failure = worker._failure('artifact_digest_mismatch', 'capture', set_key='A',
        artifact_ref=row(plan, 's0:original')['retained']['file']['artifact_ref'],
        field_path=f'/files/{index}/retained', requirement='matching_file_identity')
    plan['failures'].append(failure)
    lose(plan, 's0:canonical')
    worker.run_genomic_overlap_result_worker(plan)
    sheet, components, _, _ = load_outputs(plan)
    assert failure in sheet['comparisons'][0]['receipt']['issues']
    assert components['pairs'][0]['observed']['interpretation'] == 'unavailable'
    assert components['pairs'][2]['result_extent'] == 'complete'


@pytest.mark.parametrize('key', ['s0:rejected', 'p0:manifest'])
def test_host_missing_diagnostic_file_does_not_downgrade_qualified_pair(tmp_path, key):
    plan = make_plan(tmp_path)
    r = row(plan, key)
    if key == 's0:rejected':
        plan['batch'] = None  # Exact independent seals and originals survive.
    else:
        lose(plan, key)  # Exact batch retains the redundant original pair seal.
    index = plan['files'].index(r)
    failure = worker._failure('native_output_unavailable', 'capture',
        set_key=r['specification']['set_key'], comparison_key=r['specification']['comparison_key'],
        field_path=f'/files/{index}/retained', requirement='original_native_output')
    plan['failures'].append(failure)
    worker.run_genomic_overlap_result_worker(plan)
    sheet, components, projection, diagnostics = load_outputs(plan)
    assert failure in diagnostics['failures']
    assert failure not in sheet['comparisons'][0]['receipt']['issues']
    assert all(p['result_extent'] == 'complete' for p in components['pairs'])
    assert projection['failures'] == []


def test_analytic_current_canonical_loss_is_diagnostic_without_native_stream_loss(tmp_path):
    plan = make_plan(tmp_path, 'empty_c')
    lose(plan, 's2:canonical')
    worker.run_genomic_overlap_result_worker(plan)
    _, components, projection, diagnostics = load_outputs(plan)
    assert all(p['result_extent'] == 'complete' for p in components['pairs'])
    assert projection['failures'] == []
    assert any(f['set_key'] == 'C' for f in diagnostics['pairs'][1]['failures'])
    native_paths = {f'/files/{index}/retained' for index, r in enumerate(plan['files'])
                    if r['specification']['role'] in ('overlap_stdout', 'overlap_stderr')}
    assert not any(f['field_path'] in native_paths
                   for f in diagnostics['pairs'][1]['failures'])


@pytest.mark.parametrize('kind', ['set_metrics', 'occurrence_rows'])
def test_requested_projection_kind_fields_filter_and_page_survive_worker(tmp_path, kind):
    plan = make_plan(tmp_path)
    plan['selector']['comparison_keys'] = ['AB']
    projection = plan['selector']['projection']
    projection.update(kind=kind, offset=1, limit=1,
        measurement_fields=['union_bp'] if kind == 'set_metrics' else ['span_bp'])
    if kind == 'occurrence_rows':
        projection['occurrence_keys'] = [{'set_key': 'B', 'occurrence_key': 'r0'},
                                         {'set_key': 'A', 'occurrence_key': 'r1'}]
    worker.run_genomic_overlap_result_worker(plan)
    _, _, output, _ = load_outputs(plan)
    rows = output['set_rows'] if kind == 'set_metrics' else output['occurrence_rows']
    assert len(rows) == 1 and rows[0]['set_key'] == 'B'
    assert rows[0]['measurements'] == ({'union_bp': 5} if kind == 'set_metrics' else {'span_bp': 5})
    assert output['pair_rows'] == []
    assert output['page']['returned_rows'] == 1 and output['page']['offset'] == 1


def test_interrupted_publication_retains_closed_files_without_complete_claim(tmp_path, monkeypatch):
    plan = make_plan(tmp_path)
    link = os.link
    def interrupt(source, destination, **kwargs):
        if destination == 'components.json':
            raise OSError('synthetic publication interruption')
        return link(source, destination, **kwargs)
    monkeypatch.setattr(os, 'link', interrupt)
    with pytest.raises(OSError, match='publication interruption'):
        worker.run_genomic_overlap_result_worker(plan)
    directory = Path(plan['directory'])
    assert (directory / 'sheet.json').is_file()
    assert (directory / '.components.json.writing').is_file()
    assert not (directory / 'worker-result.json').exists()
    before = (directory / 'sheet.json').read_bytes()
    monkeypatch.setattr(os, 'link', link)
    plan['directory'] = str(tmp_path / 'fresh-result')
    assert worker.run_genomic_overlap_result_worker(plan)['state'] == 'produced'
    assert (directory / 'sheet.json').read_bytes() == before


def test_actual_store_deduplication_preserves_distinct_role_formats(tmp_path):
    # Actual Store custody, with the original selected-action authority still
    # explicitly synthetic as in the other worker transport plans.
    from gene_annotation_episode.native_file_capture import capture_native_file, retained_native_file
    from gene_annotation_episode.state import Store
    plan = make_plan(tmp_path, 'empty_c')
    with Store(tmp_path / 'actual-store') as store:
        for r in plan['files']:
            if r['retained'] is None:
                continue
            source = Path(r['retained']['path'])
            actual = capture_native_file(store, directory=str(source.parent),
                relative_path=source.name, format=r['specification']['format'])
            r['retained'] = {'file': actual, 'path': str(retained_native_file(store, actual))}
            r['capture']['observed'] = actual
        source = Path(plan['batch']['path'])
        actual = capture_native_file(store, directory=str(source.parent),
            relative_path=source.name, format=plan['batch']['file']['format'])
        plan['batch'] = {'file': actual, 'path': str(retained_native_file(store, actual))}
        original = row(plan, 's2:original')['retained']
        canonical_set = row(plan, 's2:canonical')['retained']
        assert original['path'] == canonical_set['path']
        assert original['file']['artifact_ref'] == canonical_set['file']['artifact_ref']
        assert original['file']['format'] != canonical_set['file']['format']
        (tmp_path / 'ACTUAL_STORE_WORKER_PLAN.json').write_bytes(canonical(plan))
        result = worker.run_genomic_overlap_result_worker(plan)
    assert result['state'] == 'produced' and result['failures'] == []
    sheet, components, _, _ = load_outputs(plan)
    assert all(p['result_extent'] == 'complete' for p in components['pairs'])
    assert [p['unfiltered']['jaccard_bp']['value'] for p in components['pairs']] == [1/3, 0, 0]
    assert sheet['comparisons'][1]['receipt']['b']['canonical_file']['format'] == 'bed4_occurrence_v1'
