"""Retained selected484 NMF output; no native fitting in result tests.

Tests execute only through the489 bounded verification runner. Worker component
tests are distinct from root488's complete Workflow integration.
"""
from copy import deepcopy
import json
import math
import os
from pathlib import Path

import pytest

from gene_annotation_episode.expression_nmf_common import digest
from gene_annotation_episode.expression_nmf_result_contracts import validate_expression_nmf_result_selector, validate_projection
from gene_annotation_episode.expression_nmf_result_worker import execute_expression_nmf_worker
from gene_annotation_episode.expression_nmf_return_views import FACT_SOURCES, expression_nmf_fact_sources
from gene_annotation_episode.native_expression_nmf_capture import capture_expression_nmf_native_files
from gene_annotation_episode.native_expression_nmf_preparation import (
    build_native_expression_nmf_worker_plan, build_saved_expression_nmf_worker_plan,
    prepare_expression_nmf_result_worker, validate_prepared_expression_nmf_worker)
from gene_annotation_episode.native_expression_nmf_storage import read_json
from gene_annotation_episode.native_file_capture import capture_native_file, retained_native_file
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.state import Store

REPO = Path(os.environ['NMF489_REPO'])
NATIVE = REPO / 'verification/tool_graders_expression_nmf_native_grader_2026-10-27_484/check003'
POLICY = LocalJobPolicy(21474836480, 4294967296, None)


def selector(view='fit_diagnostics', saved=None, **extra):
    selection = {'view': view, 'row_window': {'offset': 0, 'limit': 100}}
    if view == 'fit_diagnostics':
        selection['fields'] = ['native_reconstruction_error', 'native_n_iter', 'fit_call_count', 'sse', 'cell_count', 'rmse', 'mae']
    selection.update(extra)
    return {'version': 'expression_nmf_result_selector_v1', 'mode': 'native_result' if saved is None else 'saved_sheet_recalculation',
        'projection': selection, 'saved_sheet_file': deepcopy(saved)}


def native_plan(store, root, selected=None):
    original = read_json(NATIVE / 'selected-native-plan.json')
    control = store.artifact(b'{"test":"component control only"}', 'application/json')
    captured = capture_expression_nmf_native_files(store, original_plan=original, source_action_receipt_ref=control,
        writer_closure_receipt_ref=control, driver_started=True)
    return build_native_expression_nmf_worker_plan(directory=str(root), original_plan=original, capture=captured,
        selector=selected or selector())


@pytest.mark.parametrize('patch', [
    {'saved_sheet_file': {'artifact_ref': 'artifact_'+'0'*64, 'sha256': '0'*64, 'size_bytes': 0, 'format': 'expression_nmf_sheet_v1'}},
    {'mode': 'saved_sheet_recalculation'},
    {'projection': {'view': 'gene_loadings', 'row_window': {'offset': 0, 'limit': 2}}},
    {'projection': {'view': 'fit_diagnostics', 'fields': ['sse'], 'gene_positions': [0], 'row_window': {'offset': 0, 'limit': 2}}},
    {'projection': {'view': 'fit_diagnostics', 'fields': ['sse'], 'filter': {'field': 'signed_residual', 'minimum': 0}, 'row_window': {'offset': 0, 'limit': 2}}},
])
def test_closed_selected_request_rejects_conflicts(patch):
    with pytest.raises(ValueError):
        validate_expression_nmf_result_selector({**selector(), **patch})


def test_native_retained_projection_and_metadata(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        plan = native_plan(store, tmp_path / 'worker')
        def forbidden(*args, **kwargs):
            pytest.fail('Result worker attempted native fitting or acquisition')
        monkeypatch.setattr('socket.socket', forbidden)
        monkeypatch.setattr('subprocess.Popen', forbidden)
        result = execute_expression_nmf_worker(plan)
        projection = read_json(tmp_path / 'worker/projection.json')
        values = {row['field']: row['value'] for row in projection['rows']}
        assert result['analysis_complete'] and result['original_fit_acquired'] and result['native_binding']
        assert values['native_n_iter'] == 17 and values['fit_call_count'] == 1 and values['cell_count'] == 9
        assert values['native_reconstruction_error'] == 0.0001383408514600178
        assert values['sse'] == pytest.approx(values['native_reconstruction_error']**2, rel=1e-10)
        assert values['rmse'] == pytest.approx(values['native_reconstruction_error']/3, rel=1e-10)
        sheet = read_json(tmp_path / 'worker/sheet.json')
        assert [row['label'] for row in sheet['genes']] == ['g', 'g', 'g3']
        assert [row['label'] for row in sheet['samples']] == ['A', 'B', 'B']
        assert sheet['column_denominators'] == [2, 6, 6]


@pytest.mark.parametrize('change', ['missing_factors', 'bad_bytes', 'wrong_input', 'reordered_axes', 'foreign_execution'])
def test_missing_and_foreign_native_artifacts_preserve_qualified_partial_work(tmp_path, change):
    with Store(tmp_path / 'store') as store:
        plan = native_plan(store, tmp_path / 'worker', selector('gene_loadings', gene_positions=[0, 1]))
        rows = {row['role']: row for row in plan['capture']['files']}
        if change == 'missing_factors':
            rows['factors']['retained'] = None
        elif change == 'bad_bytes':
            rows['factors']['retained']['file']['size_bytes'] += 1
        else:
            role = 'factors' if change == 'reordered_axes' else 'manifest'
            value = read_json(rows[role]['retained']['path'])
            if change == 'reordered_axes':
                value['axes']['genes'].reverse()
            elif change == 'wrong_input':
                value['input_identity']['sha256'] = '0' * 64
            else:
                value['execution']['identity']['episode_id'] = 'foreign-child'
            path = tmp_path / 'changed.json'
            path.write_text(json.dumps(value))
            file = capture_native_file(store, directory=str(tmp_path), relative_path=path.name, format=rows[role]['format'])
            rows[role]['retained'] = {'file': file, 'path': str(retained_native_file(store, file))}
        result = execute_expression_nmf_worker(plan)
        assert not result['analysis_complete'] and not result['original_fit_acquired']
        assert result['failures']
        assert read_json(tmp_path / 'worker/sheet.json')['raw_matrix'] == [[1, 2, 0], [0, 1, 3], [1, 3, 3]]
        if (tmp_path / 'worker/projection.json').exists():
            projected = read_json(tmp_path / 'worker/projection.json')
            assert projected['status'] == 'unavailable'


def test_saved_calculation_without_producer_or_native_environment(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        plan = native_plan(store, tmp_path / 'native')
        execute_expression_nmf_worker(plan)
        file = capture_native_file(store, directory=str(tmp_path / 'native'), relative_path='sheet.json', format='expression_nmf_sheet_v1')
        selected = selector('sample_contributions', saved=file, sample_positions=[1], component_positions=[1])
        saved = build_saved_expression_nmf_worker_plan(directory=str(tmp_path / 'saved'),
            sheet={'file': file, 'path': str(retained_native_file(store, file))}, selector=selected)
        def forbidden(*args, **kwargs):
            pytest.fail('Saved sheet attempted original native work, loading or acquisition')
        monkeypatch.setattr('gene_annotation_episode.expression_nmf_result_worker.load_expression_nmf_artifacts', forbidden)
        monkeypatch.setattr('socket.socket', forbidden)
        monkeypatch.setattr('subprocess.Popen', forbidden)
        result = execute_expression_nmf_worker(saved)
        projection = read_json(tmp_path / 'saved/projection.json')
        assert result['analysis_complete'] and not result['original_fit_acquired']
        assert projection['rows'][0]['sample_position'] == 1 and projection['rows'][0]['sample_label'] == 'B'
        assert projection['rows'][0]['component_contribution'] == pytest.approx(3.999880660570521)


def test_failed_projection_preserves_original_fit_for_saved_repair(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from gene_annotation_episode.expression_nmf_result_receipts import ExpressionNMFResultReceipts
    with Store(tmp_path / 'store') as store:
        selected = selector('sample_contributions', sample_positions=[99])
        plan = native_plan(store, tmp_path / 'native', selected)
        result = execute_expression_nmf_worker(plan)
        assert not result['analysis_complete'] and result['original_fit_acquired']
        assert result['failures'][0]['code'] == 'projection_selection_invalid'
        file = capture_native_file(store, directory=str(tmp_path / 'native'), relative_path='sheet.json', format='expression_nmf_sheet_v1')
        calculations = capture_native_file(store, directory=str(tmp_path / 'native'), relative_path='calculations.json',
            format='expression_nmf_calculations_v1')
        receipt = {'intent': {'assignment': {'selector': selected}},
            'observation': {'state': 'completed', 'returncode': 0, 'native': {'terminal': True, 'quiescent': True}},
            'worker_capture': {'result': result, 'failures': []},
            'qualified_files': {'sheet': file, 'calculations': calculations, 'projection': None}}
        reader = ExpressionNMFResultReceipts(SimpleNamespace(store=store))
        assert reader.original_acquisition_complete(receipt)
        saved = build_saved_expression_nmf_worker_plan(directory=str(tmp_path / 'saved'),
            sheet={'file': file, 'path': str(retained_native_file(store, file))},
            selector=selector('sample_contributions', saved=file, sample_positions=[1]))
        def forbidden(*args, **kwargs):
            pytest.fail('Saved repair attempted original acquisition')
        monkeypatch.setattr('gene_annotation_episode.expression_nmf_result_worker.load_expression_nmf_artifacts', forbidden)
        repaired = execute_expression_nmf_worker(saved)
        assert repaired['analysis_complete'] and not repaired['original_fit_acquired']


def test_actual_finite_worker_receipt_and_replay(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        plan = native_plan(store, tmp_path / 'worker')
        prepared = prepare_expression_nmf_result_worker(store, plan=plan, policy=POLICY)
        assert prepared['result']['analysis_complete'], prepared
        execution = read_json(retained_native_file(store, prepared['execution_receipt_file']))
        assert execution['metadata']['verified_cgroup']['memory_max'] == 21474836480
        assert execution['metadata']['verified_cgroup']['memory_swap_max'] == 0
        assert execution['metadata']['verified_cgroup']['runtime_max'] == 'infinity'
        assert execution['intent']['source_pins'] and execution['intent']['runtime_files'] and execution['intent']['dependencies']
        def forbidden(*args, **kwargs):
            pytest.fail('Completed replay attempted native work')
        monkeypatch.setattr('gene_annotation_episode.native_lifecycle.resume_start', forbidden)
        monkeypatch.setattr('gene_annotation_episode.native_lifecycle.status', forbidden)
        assert prepare_expression_nmf_result_worker(store, plan=plan, policy=POLICY) == prepared
        changed = deepcopy(prepared)
        changed['result']['analysis_complete'] = False
        with pytest.raises(ValueError):
            validate_prepared_expression_nmf_worker(store, changed, plan=plan)
        forged_execution = deepcopy(execution)
        forged_execution['metadata']['verified_cgroup']['memory_swap_max'] = 1
        (tmp_path / 'forged-execution.json').write_text(json.dumps(forged_execution))
        forged_file = capture_native_file(store, directory=str(tmp_path), relative_path='forged-execution.json',
            format='expression_nmf_worker_execution_v1')
        with pytest.raises(ValueError, match='allocation'):
            validate_prepared_expression_nmf_worker(store, {**prepared, 'execution_receipt_file': forged_file}, plan=plan)


@pytest.mark.parametrize('variant', ['exact_fixture', 'actual_nonconvergence'])
def test_saved_numeric_population_and_native_qualification(tmp_path, variant, monkeypatch):
    from gene_annotation_episode.expression_nmf_artifacts import load_expression_nmf_artifacts
    from gene_annotation_episode.expression_nmf_sheet import populate_nmf_sheet
    from gene_annotation_episode.native_expression_nmf_storage import immutable_json
    manifest = NATIVE / ('native-none' if variant == 'exact_fixture' else 'native-nonconvergence') / 'fit-manifest.json'
    original = read_json(NATIVE / 'selected-native-plan.json')['requested_job']['native_expression_nmf']['input']
    loaded = load_expression_nmf_artifacts(manifest, expected_input_identity={k: original[k] for k in ('sha256', 'size_bytes')})
    native = loaded['native_result']
    if variant == 'exact_fixture':
        native.update(W=[[1, 0], [0, 1], [1, 1]], H=[[1, 2, 0], [0, 1, 3]],
            source={'kind': 'supplied_factor_fixture', 'estimator': 'sklearn.decomposition.NMF'}, outcome='complete', warnings=[])
        native['diagnostics'].update(reconstruction_err_=0, n_iter_=0, fit_call_count=0)
    sheet = populate_nmf_sheet(input_data=loaded['input_data'], prepared_data=loaded['prepared_data'], native_result=native)
    assert sheet['calculation_eligible']
    with Store(tmp_path / 'store') as store:
        immutable_json(tmp_path / 'sheet.json', sheet)
        file = capture_native_file(store, directory=str(tmp_path), relative_path='sheet.json', format='expression_nmf_sheet_v1')
        selected = (selector('sample_contributions', saved=file, sample_positions=[1]) if variant == 'exact_fixture'
            else selector(saved=file))
        plan = build_saved_expression_nmf_worker_plan(directory=str(tmp_path / 'worker'),
            sheet={'file': file, 'path': str(retained_native_file(store, file))}, selector=selected)
        def forbidden(*a, **k):
            pytest.fail('Saved calculation attempted external work')
        monkeypatch.setattr('socket.socket', forbidden)
        monkeypatch.setattr('subprocess.Popen', forbidden)
        result = execute_expression_nmf_worker(plan)
        projected = read_json(tmp_path / 'worker/projection.json')
        assert result['analysis_complete'] and not result['original_fit_acquired']
        if variant == 'exact_fixture':
            assert [r['component_contribution'] for r in projected['rows']] == [4, 2]
            assert [r['contribution_fraction'] for r in projected['rows']] == [2/3, 1/3]
            calculations = read_json(tmp_path / 'worker/calculations.json')
            assert calculations['sse'] == calculations['rmse'] == calculations['mae'] == 0
            assert calculations['component_loading_sums'] == [2, 2]
        else:
            assert projected['native_outcome'] == 'qualified'
            assert projected['warning_codes'] == ['iteration_limit_warning']
            assert {r['field']: r['value'] for r in projected['rows']}['native_n_iter'] == 1
