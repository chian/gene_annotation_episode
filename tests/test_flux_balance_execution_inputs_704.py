"""Original selected launch/local custody with synthetic scientific metadata.

Real Store, commission, inheritance, immutable capture and matching primitives
are used. No supplied synthetic model is scientifically parsed or executed.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
from types import MethodType, SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.flux_balance_execution_inputs import FluxBalanceExecutionInputs
from gene_annotation_episode.native_flux_balance_contracts import (
    DRIVER_MODULE, POLICY, RUN_PLAN_FILENAME, SOURCE_FUNCTION_SHA256, flux_balance_environment,
)
from gene_annotation_episode.state import Store
from test_bvbrc_appservice_custody import SavedRecords
from test_flux_balance_operands_694 import software

pytestmark = pytest.mark.skipif('HMMER529_ATTEMPT' not in os.environ, reason='requires bounded529')


@pytest.fixture
def selected(tmp_path, monkeypatch):
    from gene_annotation_episode import native_lifecycle
    def forbidden(*args, **kwargs): raise AssertionError('input custody attempted native work')
    for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'collect', 'wait_job'):
        monkeypatch.setattr(native_lifecycle, name, forbidden)
    with Store(tmp_path / 'store') as store:
        records = SavedRecords(store)
        raw = b'synthetic opaque model bytes; never scientifically read'
        artifact = store.artifact(raw)
        sha = hashlib.sha256(raw).hexdigest()
        source = store.put('source', {'provider': 'synthetic704', 'accession': 'supplied-model',
            'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'uri': None,
            'version': None, 'retrieved_at': None}, origin='tool', scope=records.scope)['id']
        records.receipts.receive(records.root.episode_id, [source], kind='initial')
        sw = software()
        workspace = tmp_path / 'work'; workspace.mkdir()
        request = {'argv': [sw['python']['path'], '-B', '-S', '-m', DRIVER_MODULE, RUN_PLAN_FILENAME],
            'environment': flux_balance_environment(sw, attempt_directory=str(workspace / 'selected/flux-balance-attempt'),
                lifecycle_directory=str(workspace / 'selected')),
            'native_flux_balance': {'version': 'native_flux_balance_job_v1',
                'operation': 'perform_flux_balance_analysis', 'mode': 'steady_state_linear_fba',
                'source_alias': 'biomni.tool.systems_biology.perform_flux_balance_analysis',
                'source_function_sha256': SOURCE_FUNCTION_SHA256,
                'model_input': {'file': {'path': str(store.path / 'artifacts' / sha[:2] / sha),
                    'sha256': sha, 'size_bytes': len(raw)}, 'artifact_ref': artifact, 'format': 'cobra_json',
                    'original_loader_selection': 'json_file', 'repository_identifier': None,
                    'acquisition_receipt_file': None}, 'constraints': None,
                'objective': {'kind': 'model_default', 'reaction_id': None},
                'solver_options': {'feasibility_tolerance': None, 'optimality_tolerance': None,
                    'integrality_tolerance': None}, 'software': sw, 'output_prefix': 'outputs',
                'flux_output_name': 'flux.csv'}}
        assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'original704',
            'resource_kind': 'local', 'resource_id': 'selected-local', 'workspace': str(workspace),
            'endpoint': 'usable_handoff', 'requested_job': request,
            'native_flux_balance_execution': {'version': 'flux_balance_execution_selection_v1',
                'environment_realization': 'operation_scoped_tmp_and_cache_v1'},
            'progress_requirements': [{'key': 'handoff', 'credit': 1,
                'predicate': {'kind': 'requested_job_handoff'}}], 'completion_keys': ['handoff'],
            'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
            'inventory_snapshot': {}, 'constraints': {'allocation': deepcopy(POLICY)}}
        versions = [{'reference': source, 'version': None, 'content_sha256': sha}]
        launch = {'version': 'execution_launch_assignment_v1', 'requests': {'selected-local': deepcopy(assignment)},
            'immutable_input_versions': versions, 'constraints': {'allowed_resource_ids': ['selected-local'],
                'allowed_kinds': ['local']}}
        parent = records.child(records.root, 'launch', launch, 0)
        access = []
        owner = SimpleNamespace(store=store, run_id=records.run_id, directory=tmp_path / 'run',
            resources={'selected-local': {'kind': 'local'}},
            resolve_received_reference=lambda context, ref, namespace: access.append((ref, namespace)))
        owner._permitted = MethodType(ExecutionEpisodes._permitted, owner)
        owner._match_request = MethodType(ExecutionEpisodes._match_request, owner)
        inputs = owner.flux_balance_inputs = FluxBalanceExecutionInputs(owner)
        def child(*, saved=True, changes=None):
            value = deepcopy(assignment)
            if changes: changes(value)
            return records.child(parent, 'launch_local', value, 0, save=saved, action=saved)
        yield SimpleNamespace(store=store, records=records, owner=owner, inputs=inputs,
            parent=parent, assignment=assignment, versions=versions, child=child, access=access,
            source=source, artifact=artifact, workspace=workspace)


def _state(f, context):
    return SimpleNamespace(run_id=context.run_id, episode_id=context.episode_id,
        assignment=plain(context.assignment))


def _overwrite(path, value, *, newline=False):
    path.chmod(0o600)
    path.write_text(canonical(value) + ('\n' if newline else ''))


def test_admission_is_read_only_and_does_not_turn_source_into_artifact_grant(selected, monkeypatch):
    f = selected
    before = list(f.store.db.iterdump())
    monkeypatch.setattr(f.store, 'get_artifact', lambda *_: pytest.fail('host read scientific bytes'))
    binding = f.inputs.validate_selected(f.parent, f.assignment, input_versions=f.versions)
    assert binding['episode_id'] == f.parent.episode_id
    assert binding['model']['witnesses'][0]['reference'] == f.source
    assert ExecutionEpisodes._flux_balance_inputs(f.owner, f.parent, f.assignment) == [f.source]
    assert list(f.store.db.iterdump()) == before
    assert not f.owner.directory.exists()


@pytest.mark.parametrize('saved', [False, True])
def test_resource_owns_its_actual_binding_and_same_original_control_on_reopen(selected, saved):
    f = selected; context = f.child(saved=saved)
    result = f.inputs.initialize(context)
    binding = result['receipt']['binding']
    assert binding['episode_id'] == context.episode_id != f.parent.episode_id
    assert binding['request_sha256'] == digest(context.request)
    assert binding['assignment_sha256'] == digest(context.assignment)
    assert binding['input_versions'] == f.versions
    assert result['file']['artifact_ref'] == 'artifact_' + digest(result['receipt'])
    before = deepcopy(result)
    result['receipt']['binding']['input_versions'].clear()
    assert f.inputs.initialize(context) == before
    assert f.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0
    if saved:
        snapshot = list(f.store.db.iterdump())
        assert f.inputs.for_start(_state(f, context)) == before
        assert list(f.store.db.iterdump()) == snapshot
    else:
        with pytest.raises(ValueError, match='saved_context_required'):
            f.inputs.for_start(_state(f, context))


def test_frozen_witness_survives_changed_source_without_a_current_source_read(selected, monkeypatch):
    f = selected; context = f.child()
    result = f.inputs.initialize(context)
    record = f.store.get(f.source);record['accession'] = 'changed later'
    f.store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(record), f.source))
    original = f.store.get
    def without_source(ref):
        assert ref != f.source, 'frozen input rebound to current source'
        return original(ref)
    monkeypatch.setattr(f.store, 'get', without_source)
    assert f.inputs.initialize(context) == result
    assert f.inputs.for_start(_state(f, context)) == result


@pytest.mark.parametrize('fault', ['assignment', 'scope', 'goal', 'purpose', 'schema_json', 'initial_report_json', 'missing'])
def test_original_resource_commission_required(selected, fault):
    f = selected; context = f.child()
    row = f.records.journal.row('runtime_actions', f.parent.episode_id, 0)
    selection = json.loads(row['action'])
    if fault == 'missing':
        f.store.db.execute('DELETE FROM runtime_actions WHERE episode_id=?', (f.parent.episode_id,))
        f.store.db.execute('DELETE FROM runtime_model_calls WHERE episode_id=?', (f.parent.episode_id,))
    else:
        if fault == 'assignment': selection['assignment']['assignment_id'] = 'another'
        elif fault == 'scope': selection['scope'] = {'subject_refs': []}
        elif fault == 'goal': selection['goal'] = 'another objective'
        elif fault == 'purpose': selection['purpose'] = 'another return meaning'
        elif fault == 'schema_json': selection['schema_json'] = '{}'
        else: selection['initial_report_json'] = '{"changed":true}'
        f.store.db.execute('UPDATE runtime_actions SET action=? WHERE episode_id=?',
            (canonical(selection), f.parent.episode_id))
    with pytest.raises(ValueError): f.inputs.initialize(context)
    assert not f.inputs._directory(context).exists()


@pytest.mark.parametrize('fault', ['wrong_parent', 'changed_assignment', 'resource', 'scope', 'inheritance'])
def test_original_context_and_launch_job_cannot_be_replaced(selected, fault):
    f = selected
    if fault == 'changed_assignment': context = f.child(changes=lambda x: x.update(assignment_id='not-parent-job'))
    elif fault == 'resource': context = f.child(changes=lambda x: x.update(resource_id='another-resource'))
    else:
        context = f.child()
        if fault == 'wrong_parent':
            context = replace(context, path=(*context.path[:-2],
                ('scientific_process', context.path[-2][1]), context.path[-1]))
        elif fault == 'scope': context = replace(context, scope={'subject_refs': []})
        else:
            f.store.db.execute('UPDATE runtime_receipt_inheritance SET through_receipt_index=999999 WHERE episode_id=?',
                (context.episode_id,))
    with pytest.raises(ValueError): f.inputs.initialize(context)


@pytest.mark.parametrize('fault', ['descriptor', 'receipt', 'captured_bytes', 'missing_receipt', 'missing_descriptor', 'symlink'])
def test_original_control_and_its_captured_file_must_agree(selected, fault, tmp_path):
    f = selected; context = f.child();result = f.inputs.initialize(context)
    root = f.inputs._directory(context)
    if fault == 'descriptor':
        value = deepcopy(result['file']);value['size_bytes'] += 1
        _overwrite(root / 'input-binding-file.json', value)
    elif fault == 'receipt':
        value = deepcopy(result['receipt']);value['binding']['request_sha256'] = 'f' * 64
        _overwrite(root / 'input-binding.json', value)
    elif fault == 'captured_bytes':
        sha = result['file']['sha256'];path = f.store.path / 'artifacts' / sha[:2] / sha
        path.chmod(0o600);path.write_bytes(b'changed captured internal control')
    elif fault == 'missing_receipt': (root / 'input-binding.json').unlink()
    elif fault == 'missing_descriptor': (root / 'input-binding-file.json').unlink()
    else:
        path = root / 'input-binding.json';raw = path.read_bytes();path.unlink()
        target = tmp_path / 'elsewhere';target.write_bytes(raw);path.symlink_to(target)
    with pytest.raises((ValueError, OSError)): f.inputs.for_start(_state(f, context))
    if fault != 'missing_descriptor':
        with pytest.raises((ValueError, OSError)): f.inputs.initialize(context)


def test_interrupted_descriptor_capture_uses_same_original_receipt(selected, monkeypatch):
    f = selected; context = f.child();original = f.inputs.initialize(context)
    (f.inputs._directory(context) / 'input-binding-file.json').unlink()
    monkeypatch.setattr(f.inputs, 'validate_selected', lambda *_a, **_k: pytest.fail('rebound original witnesses'))
    assert f.inputs.initialize(context) == original


@pytest.mark.parametrize('fault', ['missing', 'both_missing', 'wrong_state_run', 'wrong_state_assignment'])
def test_selected_start_requires_original_saved_context_and_initialized_control(selected, fault):
    f = selected; context = f.child();state = _state(f, context)
    if fault != 'missing': f.inputs.initialize(context)
    if fault == 'both_missing':
        for path in f.inputs._directory(context).iterdir(): path.unlink()
    elif fault == 'wrong_state_run': state.run_id = 'another-run'
    elif fault == 'wrong_state_assignment': state.assignment['assignment_id'] = 'another'
    with pytest.raises(ValueError): f.inputs.for_start(state)
    if fault == 'both_missing':
        with pytest.raises(ValueError, match='original_control_missing'): f.inputs.initialize(context)
