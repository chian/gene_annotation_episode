"""Real pinned bedtools cases, with separately labeled synthetic failure paths.

Run this module only within the retained local_jobs verification boundary.
Source refs in these component fixtures grant no episode-scope authority.
"""
from copy import deepcopy
from importlib import import_module
import json
import os
from pathlib import Path
import subprocess

import pytest

from gene_annotation_episode import native_genomic_overlap_driver as driver
from gene_annotation_episode.native_genomic_overlap_contracts import BATCH_FILENAME, OWNER_FILENAME, STARTED_FILENAME
from gene_annotation_episode.genomic_overlap_calculations import calculate_genomic_overlap_components
from gene_annotation_episode.genomic_overlap_result_views import project_genomic_overlap_result

f = import_module('verification.tool_graders_genomic_overlap_native_driver_2026-10-27_427.fixture_helpers')


@pytest.fixture(autouse=True)
def restore_process_environment():
    original = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(original)


def files(plan, bundle):
    return {row['specification']['file_key']: Path(plan['attempt_directory']) / row['declaration']['relative_path']
        for row in bundle['files']}


def spy_calls(monkeypatch):
    calls, original = [], driver._native_call
    def selected(argv, **kwargs):
        calls.append(list(argv))
        return original(argv, **kwargs)
    monkeypatch.setattr(driver, '_native_call', selected)
    return calls


def test_real_three_sets_native_tokens_g1_answers_and_saved_recalculation(tmp_path, monkeypatch):
    plan = f.make_plan(tmp_path)
    calls = spy_calls(monkeypatch)
    bundle = driver.run_genomic_overlap_driver(plan)
    assert bundle['batch_status'] == 'complete'
    assert len(calls) == 4 and calls[0] == [str(f.BEDTOOLS), '--version']
    assert all(argv[1] == 'intersect' and argv[-2:] == ['-wo', '-sorted'] and len(argv) == 8 for argv in calls[1:])
    paths = files(plan, bundle)
    assert paths['s0:canonical'].read_bytes() == b'chr1\t0\t10\ts0_r0\nchr1\t5\t15\ts0_r1\n'
    assert paths['p0:stdout'].read_bytes() == b'chr1\t0\t10\ts0_r0\tchr1\t7\t12\ts1_r0\t3\nchr1\t5\t15\ts0_r1\tchr1\t7\t12\ts1_r0\t5\n'
    sheet, components = f.g1_result(plan, bundle)
    metrics = [row['unfiltered'] for row in components['pairs']]
    assert [row['native_pair_count'] for row in metrics] == [2, 1, 1]
    assert [row['pairwise_overlap_bp_sum'] for row in metrics] == [8, 5, 2]
    assert [row['intersection_union_bp'] for row in metrics] == [5, 5, 2]
    assert [row['combined_union_bp'] for row in metrics] == [15, 20, 13]
    assert [row['jaccard_bp']['value'] for row in metrics] == pytest.approx([1/3, 1/4, 2/13])
    selector = {'version': 'genomic_overlap_result_selector_v1', 'mode': 'native_result',
        'comparison_keys': ['AB', 'AC', 'BC'], 'saved_sheet_file': None,
        'parameters': f.parameters(), 'projection': {'kind': 'pair_metrics',
            'offset': 0, 'limit': 3, 'measurement_fields': ['unfiltered.jaccard_bp'], 'occurrence_keys': []}}
    projection = project_genomic_overlap_result(sheet, components, selector=selector)
    assert [row['comparison_key'] for row in projection['pair_rows']] == ['AB', 'AC', 'BC']
    assert [row['measurements'] for row in projection['pair_rows']] == [
        {'unfiltered.jaccard_bp': row['jaccard_bp']} for row in metrics]
    assert projection['set_rows'] == projection['occurrence_rows'] == []
    assert projection['page'] == {'offset': 0, 'limit': 3, 'total_rows': 3, 'returned_rows': 3}
    (tmp_path / 'ACTUAL_NATIVE_G1.json').write_text(json.dumps({'evidence': 'actual_pinned_bedtools_on_synthetic_inputs',
        'plan': plan, 'batch': bundle, 'sheet': sheet, 'components': components,
        'selector': selector, 'projection': projection}, indent=2) + '\n')
    before = Path(plan['attempt_directory'], BATCH_FILENAME).read_bytes()
    monkeypatch.setattr(driver, '_native_call', lambda *a, **k: pytest.fail('native replay'))
    assert driver.run_genomic_overlap_driver(plan) == bundle
    assert Path(plan['attempt_directory'], BATCH_FILENAME).read_bytes() == before
    selected = calculate_genomic_overlap_components(sheet, parameters=f.parameters(4))
    assert selected['pairs'][0]['selected']['selected_pair_count'] == 1
    assert selected['pairs'][0]['selected']['a_region_overlap_fraction']['value'] == 1/2
    assert components['pairs'][0]['selected']['selected_pair_count'] == 2


@pytest.mark.parametrize('third,dispositions,extents', [
    (b'', ['native_succeeded', 'analytic_empty', 'analytic_empty'], ['complete'] * 3),
    (b'chr1\t10\t10\n', ['native_succeeded', 'invalid_input', 'invalid_input'], ['complete', 'unavailable', 'unavailable']),
    (b'chr1\t10\t20\nchr1\t30\t30\n', ['native_succeeded', 'invalid_input', 'invalid_input'], ['complete', 'unavailable', 'unavailable']),
])
def test_real_empty_or_invalid_third_preserves_ab(tmp_path, monkeypatch, third, dispositions, extents):
    plan = f.make_plan(tmp_path, data=[*f.DEFAULT_DATA[:2], third])
    calls = spy_calls(monkeypatch)
    bundle = driver.run_genomic_overlap_driver(plan)
    assert [row['disposition'] for row in bundle['pairs']] == dispositions
    assert len(calls) == 2
    paths = files(plan, bundle)
    assert not paths['p1:stdout'].exists() and not paths['p2:stderr'].exists()
    assert paths['s2:canonical'].exists() == (third == b'')
    sheet, result = f.g1_result(plan, bundle)
    assert [row['result_extent'] for row in result['pairs']] == extents
    assert result['pairs'][0]['unfiltered']['pairwise_overlap_bp_sum'] == 8
    if third == b'':
        assert [row['unfiltered']['jaccard_bp']['value'] for row in result['pairs']] == pytest.approx([1/3, 0, 0])
        assert result['pairs'][1]['unfiltered']['b_region_overlap_fraction']['value'] is None
        assert paths['s2:canonical'].read_bytes() == b''
    else:
        assert result['pairs'][1]['unfiltered']['native_pair_count'] is None
        assert sheet['sets'][2]['invalid_records']


@pytest.mark.parametrize('change', ['missing', 'mismatch', 'symlink', 'fifo'])
def test_unavailable_third_preserves_independent_ab(tmp_path, change):
    plan = f.make_plan(tmp_path)
    path = Path(plan['requested_job']['native_genomic_overlap']['inputs'][2]['path'])
    if change == 'mismatch':
        path.write_bytes(b'foreign\t0\t20\n')
    else:
        path.unlink()
        if change == 'symlink':
            path.symlink_to(Path(plan['requested_job']['native_genomic_overlap']['inputs'][0]['path']))
        elif change == 'fifo':
            os.mkfifo(path)
    bundle = driver.run_genomic_overlap_driver(plan)
    assert bundle['batch_status'] == 'partial'
    assert [row['disposition'] for row in bundle['pairs']] == ['native_succeeded', 'input_unavailable', 'input_unavailable']
    assert all(row['manifest'] is None for row in bundle['pairs'][1:])
    paths = files(plan, bundle)
    assert not paths['s2:original'].exists()
    if change == 'mismatch':
        assert paths['s2:rejected'].read_bytes() == b'foreign\t0\t20\n'
        assert bundle['sets'][2]['measured_fingerprint'] is not None
    else:
        assert bundle['sets'][2]['measured_fingerprint'] is None
    _, result = f.g1_result(plan, bundle)
    assert result['pairs'][0]['unfiltered']['jaccard_bp']['value'] == 1/3
    assert result['pairs'][1]['unfiltered']['native_pair_count'] is None


def test_real_duplicates_remain_four_distinct_token_pairs(tmp_path):
    plan = f.make_plan(tmp_path, data=[b'chr1\t0\t10\n' * 2, b'chr1\t5\t15\n' * 2])
    bundle = driver.run_genomic_overlap_driver(plan)
    sheet, result = f.g1_result(plan, bundle)
    metrics = result['pairs'][0]['unfiltered']
    assert [metrics[k] for k in ('native_pair_count', 'pairwise_overlap_bp_sum', 'intersection_union_bp', 'combined_union_bp')] == [4, 20, 5, 15]
    assert metrics['jaccard_bp']['value'] == 1/3
    assert len(sheet['comparisons'][0]['valid_pairs']) == 4
    assert [row['locator']['line_number'] for row in sheet['sets'][0]['regions']] == [1, 2]


@pytest.mark.parametrize('second', [b'chr1\t10\t20\n', b'chr2\t0\t10\n'])
def test_real_nonempty_no_hit_is_present_empty_stdout(tmp_path, second):
    plan = f.make_plan(tmp_path, data=[b'chr1\t0\t10\n', second])
    bundle = driver.run_genomic_overlap_driver(plan)
    assert bundle['pairs'][0]['disposition'] == 'native_succeeded'
    path = files(plan, bundle)['p0:stdout']
    assert path.is_file() and path.read_bytes() == b''
    _, result = f.g1_result(plan, bundle)
    assert result['pairs'][0]['unfiltered']['native_pair_count'] == 0
    assert result['pairs'][0]['unfiltered']['a_region_overlap_fraction']['value'] == 0


@pytest.mark.parametrize('end', [2_000_000_000, 2**63 - 1])
def test_real_long_coordinates_retain_exact_width_one(tmp_path, end):
    plan = f.make_plan(tmp_path, data=[f'chr1\t0\t{end}\n'.encode(), f'chr1\t{end-1}\t{end}\n'.encode()])
    bundle = driver.run_genomic_overlap_driver(plan)
    _, result = f.g1_result(plan, bundle)
    assert result['pairs'][0]['unfiltered']['pairwise_overlap_bp_sum'] == 1
    assert result['pairs'][0]['unfiltered']['intersection_union_bp'] == 1
    assert files(plan, bundle)['p0:stdout'].read_bytes().endswith(b'\t1\n')


def test_real_variable_bed_columns_and_coordinate_json_preserve_all_fields(tmp_path):
    first = b'chr1\t0\t10\nchr1\t10\t20\tname\nchr1\t20\t30\tsix\t5\t-\nchr1\t30\t50\ttwelve\t0\t+\t30\t50\t0\t2\t3,3\t0,17\n'
    second = b'[["chr1",0,50,{"payload":17},5,"-",[1,2]]]'
    plan = f.make_plan(tmp_path, data=[first, second], formats=['bed_outer_span_v1', 'coordinate_rows_v1'])
    bundle = driver.run_genomic_overlap_driver(plan)
    paths = files(plan, bundle)
    assert paths['s0:original'].read_bytes() == first
    assert paths['s1:original'].read_bytes() == second
    parsed = json.loads(paths['s0:parsed'].read_bytes())
    assert [len(row['original_fields']) for row in parsed['regions']] == [3, 4, 6, 12]
    assert all(len(line.split(b'\t')) == 4 for line in paths['s0:canonical'].read_bytes().splitlines())
    _, result = f.g1_result(plan, bundle)
    assert result['pairs'][0]['unfiltered']['native_pair_count'] == 4
    assert result['pairs'][0]['unfiltered']['intersection_union_bp'] == 50


@pytest.mark.parametrize('which', ['python_hash', 'code_hash', 'bedtools_path', 'bedtools_hash', 'version'])
def test_wrong_or_unavailable_software_never_substitutes(tmp_path, monkeypatch, which):
    def change(value):
        if which == 'python_hash':
            value['python_sha256'] = 'a' * 64
        elif which == 'code_hash':
            value['implementation_files'][0]['sha256'] = 'a' * 64
        elif which == 'bedtools_path':
            value['bedtools_executable'] = str(tmp_path / 'missing-bedtools')
        elif which == 'bedtools_hash':
            value['bedtools_sha256'] = 'a' * 64
        else:
            value['bedtools_version'] = 'bedtools v0.0.0'
    plan = f.make_plan(tmp_path, software_change=change)
    calls = spy_calls(monkeypatch)
    bundle = driver.run_genomic_overlap_driver(plan)
    assert bundle['batch_status'] == 'failed'
    assert all(row['disposition'] == 'native_unavailable' and row['manifest'] is None for row in bundle['pairs'])
    assert len(calls) == (1 if which == 'version' else 0)
    assert bundle['software_verification']['state'] == 'failed'
    paths = files(plan, bundle)
    assert all(paths[f's{i}:original'].is_file() for i in range(3))
    if which in {'python_hash', 'code_hash'}:
        assert all(row['parse_extent'] is None for row in bundle['sets'])
        assert not paths['s0:parsed'].exists() and not paths['s0:canonical'].exists()


def test_all_analytic_empty_does_not_probe_bedtools(tmp_path, monkeypatch):
    plan = f.make_plan(tmp_path, data=[b'', b''], software_change=lambda s: s.update(bedtools_executable=str(tmp_path / 'missing')))
    monkeypatch.setattr(driver, '_native_call', lambda *a, **k: pytest.fail('empty algebra invoked native'))
    bundle = driver.run_genomic_overlap_driver(plan)
    assert bundle['batch_status'] == 'complete'
    assert bundle['software_verification']['state'] == 'not_needed'
    assert bundle['software_verification']['bedtools_observed'] is None
    assert not files(plan, bundle)['version_stdout'].exists()


def test_synthetic_nonzero_partial_first_pair_keeps_later_real_pairs(tmp_path, monkeypatch):
    plan = f.make_plan(tmp_path)
    original, invocations = driver._native_call, []
    def selected(argv, **kwargs):
        invocations.append(argv)
        if argv[1] == 'intersect' and len(invocations) == 2:
            # This helper is deliberately a synthetic subprocess failure. The
            # actual exit 7 and one complete output row are retained as such.
            payload = b'chr1\t0\t10\ts0_r0\tchr1\t7\t12\ts1_r0\t3\n'
            fake = [plan['requested_job']['argv'][0], '-B', '-c',
                'import os;os.write(1,' + repr(payload) + ');raise SystemExit(7)']
            return original(fake, **kwargs)
        return original(argv, **kwargs)
    monkeypatch.setattr(driver, '_native_call', selected)
    bundle = driver.run_genomic_overlap_driver(plan)
    assert bundle['batch_status'] == 'partial'
    assert [row['disposition'] for row in bundle['pairs']] == ['native_failed', 'native_succeeded', 'native_succeeded']
    assert len(invocations) == 4 and bundle['pairs'][0]['manifest']['returncode'] == 7
    _, result = f.g1_result(plan, bundle)
    assert result['pairs'][0]['unfiltered']['native_pair_count'] is None
    assert result['pairs'][0]['observed']['observed_pairwise_bp_sum'] == 3
    assert result['pairs'][0]['observed']['interpretation'] == 'lower_bound_subset'
    (tmp_path / 'SYNTHETIC_FAILURE.json').write_text(json.dumps({'label': 'synthetic_subprocess_failure_fixture', 'batch': bundle}) + '\n')


def test_synthetic_spawn_failure_does_not_create_no_hit_manifest(tmp_path, monkeypatch):
    plan = f.make_plan(tmp_path)
    original = driver._native_call
    def selected(argv, **kwargs):
        if argv[1] == 'intersect':
            raise driver._NativeSpawnError(FileNotFoundError(2, 'synthetic unavailable process'))
        return original(argv, **kwargs)
    monkeypatch.setattr(driver, '_native_call', selected)
    bundle = driver.run_genomic_overlap_driver(plan)
    assert all(row['manifest'] is None and row['disposition'] == 'native_unavailable' for row in bundle['pairs'])
    assert all(not files(plan, bundle)[f'p{i}:stdout'].exists() for i in range(3))


def test_synthetic_interruption_after_first_seal_never_resumes_suffix(tmp_path, monkeypatch):
    plan = f.make_plan(tmp_path)
    original = driver._native_call
    calls = []
    def selected(argv, **kwargs):
        calls.append(argv)
        if argv[1] == 'intersect' and len(calls) == 3:
            kwargs['stdout'].write_bytes(b'partial-second-output')
            raise KeyboardInterrupt('synthetic interruption')
        return original(argv, **kwargs)
    monkeypatch.setattr(driver, '_native_call', selected)
    with pytest.raises(KeyboardInterrupt):
        driver.run_genomic_overlap_driver(plan)
    root = Path(plan['attempt_directory'])
    assert (root / 'overlap/pairs/p0/manifest.json').is_file()
    assert (root / 'overlap/pairs/p1/overlap.wo.tsv').read_bytes() == b'partial-second-output'
    assert not (root / BATCH_FILENAME).exists()
    before = len(calls)
    with pytest.raises(ValueError, match='unsealed_native_attempt'):
        driver.run_genomic_overlap_driver(plan)
    assert len(calls) == before


@pytest.mark.parametrize('kind', ['changed_native', 'changed_canonical', 'missing_file', 'new_absent_file', 'owner_mismatch'])
def test_sealed_replay_rejects_changed_declarations_without_invocation(tmp_path, monkeypatch, kind):
    plan = f.make_plan(tmp_path)
    bundle = driver.run_genomic_overlap_driver(plan)
    paths = files(plan, bundle)
    if kind == 'missing_file':
        paths['p0:stdout'].unlink()
    elif kind == 'new_absent_file':
        paths['s0:rejected'].write_bytes(b'')
    elif kind == 'owner_mismatch':
        target = Path(plan['attempt_directory'], OWNER_FILENAME)
        target.chmod(0o644)
        target.write_bytes(b'{}\n')
    else:
        target = paths['p0:stdout' if kind == 'changed_native' else 's0:canonical']
        target.chmod(0o644)
        target.write_bytes(b'changed')
    monkeypatch.setattr(driver, '_native_call', lambda *a, **k: pytest.fail('invalid replay invoked native'))
    with pytest.raises((OSError, ValueError)):
        driver.run_genomic_overlap_driver(plan)


def test_owner_without_start_marker_is_unsealed(tmp_path):
    plan = f.make_plan(tmp_path)
    root = Path(plan['attempt_directory'])
    root.mkdir()
    driver._immutable(root / OWNER_FILENAME, plan)
    assert not (root / STARTED_FILENAME).exists()
    with pytest.raises(ValueError, match='unsealed_native_attempt'):
        driver.run_genomic_overlap_driver(plan)


@pytest.mark.parametrize('suffix', ['parsed-set.json', 'canonical.bed'])
def test_synthetic_normalization_publication_failure_retains_independent_results(tmp_path, monkeypatch, suffix):
    plan = f.make_plan(tmp_path)
    original = driver._publish
    def failed(temporary, destination):
        if destination.parent.name == 's2' and destination.name == suffix:
            raise OSError(5, 'synthetic serialization failure')
        return original(temporary, destination)
    monkeypatch.setattr(driver, '_publish', failed)
    bundle = driver.run_genomic_overlap_driver(plan)
    assert bundle['pairs'][0]['disposition'] == 'native_succeeded'
    assert all(row['disposition'] == 'native_unavailable' for row in bundle['pairs'][1:])
    assert bundle['sets'][2]['input_state'] == 'verified'
    assert bundle['sets'][2]['parse_extent'] == ('complete' if suffix == 'canonical.bed' else None)
    failure = bundle['failures'][bundle['sets'][2]['failure_indices'][0]]
    assert failure['code'] == 'seal_failed'
    assert failure['file_key'] == ('s2:canonical' if suffix == 'canonical.bed' else 's2:parsed')


def test_synthetic_canonical_failure_beside_empty_input_preserves_other_pair(tmp_path, monkeypatch):
    plan = f.make_plan(tmp_path, data=[b'', *f.DEFAULT_DATA[1:]])
    original = driver._publish
    def failed(temporary, destination):
        if destination.parent.name == 's1' and destination.name == 'canonical.bed':
            raise OSError(5, 'synthetic canonical publication failure')
        return original(temporary, destination)
    monkeypatch.setattr(driver, '_publish', failed)
    monkeypatch.setattr(driver, '_native_call', lambda *a, **k: pytest.fail('unavailable/empty work invoked native'))
    bundle = driver.run_genomic_overlap_driver(plan)
    assert bundle['batch_status'] == 'partial'
    assert [row['disposition'] for row in bundle['pairs']] == [
        'native_unavailable', 'analytic_empty', 'native_unavailable']
    assert bundle['sets'][1]['input_state'] == 'verified'
    assert bundle['sets'][1]['parse_extent'] == 'complete'
    paths = files(plan, bundle)
    assert json.loads(paths['s1:parsed'].read_bytes())['result_extent'] == 'complete'
    assert not paths['s1:canonical'].exists()
    assert paths['s1:canonical'].with_name('.canonical.bed.writing').is_file()
    failure = bundle['failures'][bundle['sets'][1]['failure_indices'][0]]
    assert failure['code'] == 'seal_failed' and failure['file_key'] == 's1:canonical'
    assert bundle['pairs'][0]['manifest'] is bundle['pairs'][2]['manifest'] is None
    assert bundle['pairs'][1]['manifest']['derivation'] == 'validated_empty_input'


def test_synthetic_original_publication_failure_preserves_unsealed_bytes(tmp_path, monkeypatch):
    plan = f.make_plan(tmp_path)
    original = driver._publish
    def failed(temporary, destination):
        if destination.parent.name == 's2' and destination.name == 'original.data':
            raise OSError(5, 'synthetic publication failure')
        return original(temporary, destination)
    monkeypatch.setattr(driver, '_publish', failed)
    with pytest.raises(OSError):
        driver.run_genomic_overlap_driver(plan)
    directory = Path(plan['attempt_directory'])
    assert (directory / 'overlap/sets/s0/parsed-set.json').is_file()
    assert (directory / 'overlap/sets/s2/.original.data.staging').read_bytes() == f.DEFAULT_DATA[2]
    assert not (directory / BATCH_FILENAME).exists()
    with pytest.raises(ValueError, match='unsealed_native_attempt'):
        driver.run_genomic_overlap_driver(plan)


def test_synthetic_progress_log_failure_does_not_claim_process_never_started(tmp_path, monkeypatch):
    plan = f.make_plan(tmp_path)
    original = driver._event
    def fail_log(stream, event, **values):
        if event == 'pair_started':
            raise OSError(5, 'synthetic log write failure')
        return original(stream, event, **values)
    monkeypatch.setattr(driver, '_event', fail_log)
    with pytest.raises(OSError):
        driver.run_genomic_overlap_driver(plan)
    directory = Path(plan['attempt_directory'])
    assert not (directory / BATCH_FILENAME).exists()
    assert (directory / 'overlap/pairs/p0/overlap.wo.tsv').read_bytes().count(b'\n') == 2
    with pytest.raises(ValueError, match='unsealed_native_attempt'):
        driver.run_genomic_overlap_driver(plan)
