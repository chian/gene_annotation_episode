"""Actual finite result process, immutable control capture and original replay."""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_atac_differential_contracts import POLICY
from gene_annotation_episode.native_atac_differential_preparation import prepare_atac_result_worker, validate_prepared_atac_worker, build_saved_atac_worker_plan
from gene_annotation_episode.native_file_capture import capture_native_file, retained_native_file
from gene_annotation_episode.state import Store
from gene_annotation_episode import native_lifecycle as native
from test_atac_differential_result_worker import save_bundle, selector
from test_atac_differential_calculation_inputs import sheet


def retained_plan(tmp_path, store):
    local, public = save_bundle(tmp_path / 'inputs', sheet())
    for record in [local['sheet'], *local['tables']]:
        path = Path(record['path'])
        captured = capture_native_file(store, directory=str(path.parent), relative_path=path.name, format=record['file']['format'])
        assert captured == record['file']
        record['path'] = str(retained_native_file(store, captured))
    return build_saved_atac_worker_plan(directory=str(tmp_path / 'worker'), sheet_bundle=local, selector=selector(sheet(), bundle=public))


def test_actual_worker_is_bounded_frozen_and_replays_after_original_sources_removed(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        plan = retained_plan(tmp_path, store)
        capture = prepare_atac_result_worker(store, plan=plan, policy=LocalJobPolicy(**POLICY))
        execution = json.loads(retained_native_file(store, capture['execution_receipt_file']).read_bytes())
        assert execution['returncode'] == 0 and execution['terminal'] and execution['quiescent']
        assert execution['metadata']['verified_cgroup'] == dict(memory_max=21474836480, memory_swap_max=0, kill_mode='control-group', oom_policy='kill')
        assert capture['result']['state'] == 'produced'
        assert all(r['capture']['outcome'] == 'verified' for r in capture['outputs'])
        assert {r['distribution'] for r in execution['intent']['dependencies']} >= {'jsonschema', 'attrs', 'referencing', 'rpds-py', 'jsonschema-specifications'}
        assert 'numpy' not in {r['distribution'] for r in execution['intent']['dependencies']}
        assert Path(execution['intent']['environment']['PIP_CACHE_DIR']).is_relative_to(plan['directory'])
        before = Path(plan['directory'], 'worker.handle.json').read_bytes()
        for path in Path(plan['directory'], 'source_snapshot').rglob('*'):
            if path.is_dir():
                path.chmod(0o755)
        shutil.rmtree(Path(plan['directory'], 'source_snapshot'))
        shutil.rmtree(tmp_path / 'inputs')
        def forbidden(*a, **k):
            raise AssertionError('closed result replay attempted fresh preparation or native execution')
        monkeypatch.setattr(native, 'prepare_job', forbidden)
        monkeypatch.setattr(native, 'resume_start', forbidden)
        monkeypatch.setattr(native, 'status', forbidden)
        assert prepare_atac_result_worker(store, plan=plan, policy=LocalJobPolicy(**POLICY)) == capture
        assert validate_prepared_atac_worker(store, capture, plan=plan) == capture
        assert Path(plan['directory'], 'worker.handle.json').read_bytes() == before


def test_saved_preparation_requires_exact_policy_before_any_native_start(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        plan = retained_plan(tmp_path, store)
        monkeypatch.setattr(native, 'prepare_job', lambda *a, **k: pytest.fail('invalid allocation reached native dispatch'))
        with pytest.raises(ValueError, match='policy_mismatch'):
            prepare_atac_result_worker(store, plan=plan, policy=LocalJobPolicy(memory_bytes=1024, scratch_bytes=4294967296))


def test_missing_and_changed_saved_tables_reach_finite_worker_and_drain_remaining_streams(tmp_path):
    with Store(tmp_path / 'store') as store:
        plan = retained_plan(tmp_path, store)
        Path(plan['sheet_bundle']['tables'][0]['path']).unlink()
        Path(plan['sheet_bundle']['tables'][1]['path']).write_bytes(b'[malformed retained bytes]\n')
        capture = prepare_atac_result_worker(store, plan=plan, policy=LocalJobPolicy(**POLICY))
        assert capture['result']['state'] == 'partial'
        calculations = next(r for r in capture['outputs'] if r['role'] == 'calculations')
        value = json.loads(retained_native_file(store, calculations['capture']['observed']).read_bytes())
        assert [r['exhausted'] for r in value['stream_states']] == [False, False, True, True]
        assert {'saved_attachment_unavailable', 'calculation_stream_failed'} <= {r['code'] for r in value['failures']}
        assert all(r['extent'] == 'partial' for r in value['tables'])
        assert validate_prepared_atac_worker(store, capture, plan=plan) == capture


def test_saved_plan_rejects_input_output_overlap_and_mismatched_public_bundle(tmp_path):
    with Store(tmp_path / 'store') as store:
        plan = retained_plan(tmp_path, store)
        plan['directory'] = str(store.path)
        from gene_annotation_episode.atac_differential_result_worker import validate_atac_result_worker_plan
        with pytest.raises(ValueError, match='overlap'):
            validate_atac_result_worker_plan(plan)
        plan['directory'] = str(tmp_path / 'worker')
        plan['selector']['saved_sheet_bundle']['tables'][0]['track_key'] = 'wrong'
        with pytest.raises(ValueError, match='bundle_mismatch'):
            validate_atac_result_worker_plan(plan)
