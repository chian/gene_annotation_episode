"""079 native receipt engineering checks with real ToolRegistry image.view outputs.

Images, selected literals, journal rows and pending snapshots are explicitly
constructed fixtures. These do not establish selected LiteratureEpisode/C1/C4
execution, model interpretation or experimental measurements.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from gene_annotation_episode.domain import ContractError, canonical
from test_literature_ratio_source_storage import native_case, repository


def pending_snapshot():
    return {'version': 'pending_work_v1', 'captured_at': '2026-10-27T00:00:00+00:00', 'items': []}


def runtime_result(store, native, *, pending=True):
    result = deepcopy(native)
    if pending:
        result['pending_work_after_action'] = pending_snapshot()
    store.db.execute('UPDATE runtime_actions SET result=? WHERE decision_index=4', (canonical(result),))
    return result


@pytest.mark.parametrize('pending', [False, True], ids=['legacy-original', 'runtime-pending-addition'])
def test_authentic_tool_portion_and_full_original_runtime_digest(tmp_path, monkeypatch, pending):
    store, context, selection, native = native_case(tmp_path)
    try:
        result = runtime_result(store, native, pending=pending)
        repo = repository(store, context)
        runtime_before = store.db.execute('SELECT result FROM runtime_actions WHERE decision_index=4').fetchone()[0]
        native_before = store.db.execute('SELECT result FROM tool_operations').fetchone()[0]
        outcome = repo.populate(context, selection, 'original-runtime')
        saved = repo.read(outcome['result']['sheet_ref'])
        receipt = saved['extraction']['views'][0]['own_action_receipt']
        assert receipt['result_sha256'] == hashlib.sha256(canonical(result).encode()).hexdigest()
        if pending:
            assert receipt['result_sha256'] != hashlib.sha256(canonical(native).encode()).hexdigest()
        assert saved['sheet']['cells']['reported_ratio']['value'] == .64
        assert store.db.execute('SELECT result FROM runtime_actions WHERE decision_index=4').fetchone()[0] == runtime_before
        assert store.db.execute('SELECT result FROM tool_operations').fetchone()[0] == native_before
        before = store.db.total_changes
        monkeypatch.setattr('gene_annotation_episode.literature_ratio_source_inputs.read_relative_signal_source_inputs',
            lambda *_a, **_k: pytest.fail('saved replay called reader'))
        monkeypatch.setattr('gene_annotation_episode.literature_ratio_source_calculations.populate_relative_signal_v2',
            lambda *_a, **_k: pytest.fail('saved replay called calculator'))
        assert repo.populate(context, selection, 'original-runtime') == outcome
        assert repo.read(outcome['result']['sheet_ref']) == saved
        assert store.db.total_changes == before
        assert not store.list('observation')
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
    finally:
        store.close()


@pytest.mark.parametrize('change', ['timestamp', 'items', 'remove'])
def test_saved_receipt_rejects_changed_original_pending_snapshot(tmp_path, change):
    store, context, selection, native = native_case(tmp_path)
    try:
        result = runtime_result(store, native)
        repo = repository(store, context)
        outcome = repo.populate(context, selection, 'saved-runtime')
        saved_receipt = repo.read(outcome['result']['sheet_ref'])['extraction']['views'][0]['own_action_receipt']
        if change == 'timestamp':
            result['pending_work_after_action']['captured_at'] = '2026-10-27T00:00:01+00:00'
        elif change == 'items':
            result['pending_work_after_action']['items'] = [{'constructed_tampering': True}]
        else:
            del result['pending_work_after_action']
        store.db.execute('UPDATE runtime_actions SET result=? WHERE decision_index=4', (canonical(result),))
        assert saved_receipt['result_sha256'] != hashlib.sha256(canonical(result).encode()).hexdigest()
        # A fresh receipt may authenticate the native tool portion. The saved
        # original receipt must still reject the changed full runtime snapshot.
        assert repo._own_view_receipt(context, native['result']['view_ref']) != saved_receipt
        before = store.db.total_changes
        with pytest.raises(ContractError, match='relative_signal_own_view_action_required'):
            repo.read(outcome['result']['sheet_ref'])
        with pytest.raises(ContractError, match='relative_signal_own_view_action_required'):
            repo.populate(context, selection, 'saved-runtime')
        assert store.db.total_changes == before
    finally:
        store.close()


@pytest.mark.parametrize('fault', [
    'runtime_extra', 'runtime_nested_extra', 'native_extra', 'native_pending', 'native_result',
    'native_operation', 'runtime_operation', 'native_arguments', 'native_scope',
    'action_extra', 'action_arguments', 'foreign_episode', 'copied_foreign_action', 'copied_foreign_operation',
    'runtime_visual', 'runtime_refs', 'paired_result_tampering',
])
def test_runtime_addition_does_not_relax_native_or_owner_authentication(tmp_path, fault):
    store, context, selection, native = native_case(tmp_path)
    try:
        result = runtime_result(store, native)
        if fault == 'runtime_extra':
            result['unrecognized_runtime_field'] = None
        elif fault == 'runtime_nested_extra':
            result['result']['pending_work_after_action'] = pending_snapshot()
        elif fault in ('native_extra', 'native_pending', 'native_result', 'paired_result_tampering'):
            changed = deepcopy(native)
            if fault == 'native_extra':
                changed['unrecognized_native_field'] = True
            elif fault == 'native_pending':
                changed['pending_work_after_action'] = pending_snapshot()
            else:
                changed['result']['unrecognized_result_field'] = True
                if fault == 'paired_result_tampering':
                    result['result'] = deepcopy(changed['result'])
            store.db.execute('UPDATE tool_operations SET result=?', (canonical(changed),))
        elif fault == 'native_operation':
            store.db.execute("UPDATE tool_operations SET id='operation_forged'")
        elif fault == 'runtime_operation':
            result['operation_ref'] = 'operation_forged'
        elif fault == 'native_arguments':
            store.db.execute("UPDATE tool_operations SET arguments='{}'")
        elif fault == 'native_scope':
            store.db.execute("UPDATE tool_operations SET scope='null'")
        elif fault in ('action_extra', 'action_arguments'):
            action = json.loads(store.db.execute('SELECT action FROM runtime_actions WHERE decision_index=4').fetchone()[0])
            if fault == 'action_extra':
                action['pending_work_after_action'] = pending_snapshot()
            else:
                action['arguments']['frame'] = 0
            store.db.execute('UPDATE runtime_actions SET action=? WHERE decision_index=4', (canonical(action),))
        elif fault == 'foreign_episode':
            context = replace(context, episode_id='foreign-episode')
        elif fault in ('copied_foreign_action', 'copied_foreign_operation'):
            # Copying an authentic action to a different owner cannot supply its
            # missing ToolRegistry operation under the new episode's exact key.
            store.db.execute("UPDATE runtime_actions SET episode_id='foreign-episode' WHERE decision_index=4")
            if fault == 'copied_foreign_operation':
                store.db.execute("UPDATE tool_operations SET operation_key='fixture-run:foreign-episode:4'")
            context = replace(context, episode_id='foreign-episode')
        elif fault == 'runtime_visual':
            result['visual_inputs'] = []
        else:
            result['record_refs'].reverse()
        store.db.execute('UPDATE runtime_actions SET result=? WHERE decision_index=4', (canonical(result),))
        repo = repository(store, context)
        with pytest.raises(ContractError, match='relative_signal_own_view_action'):
            repo.populate(context, selection, 'forged-runtime')
        assert store.db.execute('SELECT count(*) FROM literature_ratio_source_operations').fetchone()[0] == 0
        assert not store.list('observation')
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
    finally:
        store.close()


def test_augmented_receipt_first_saved_read_in_fresh_readonly_process(tmp_path):
    path = tmp_path / 'store'
    store, context, selection, native = native_case(path)
    try:
        runtime_result(store, native)
        repo = repository(store, context)
        outcome = repo.populate(context, selection, 'readonly-runtime')
        saved = repo.read(outcome['result']['sheet_ref'])
        fixture = {'run_id': context.run_id, 'sheet_ref': outcome['result']['sheet_ref'], 'saved': saved,
            'banned': list({value for row in saved['extraction']['views'] for key, value in row['metadata'].items()
                if key in ('original_artifact_ref', 'image_artifact_ref')})}
        fixture_path = tmp_path / 'fixture.json'
        fixture_path.write_text(json.dumps(fixture))
    finally:
        store.close()
    script = r'''
import json, sqlite3, sys
from pathlib import Path
from PIL import Image
from gene_annotation_episode.state import Store
from gene_annotation_episode.literature_ratio_source_storage import LiteratureRatioSourceRepository
from gene_annotation_episode import literature_ratio_source_inputs as inputs
from gene_annotation_episode import literature_ratio_source_calculations as calculations
fixture=json.loads(Path(sys.argv[2]).read_text())
def forbidden(*a,**k):raise AssertionError('reacquisition, decoder, population or mutation')
store=Store.__new__(Store);store.path=Path(sys.argv[1]);store._savepoint=0
store.db=sqlite3.connect(f'file:{store.path / "state.sqlite3"}?mode=ro',uri=True)
store.db.row_factory=sqlite3.Row;store.db.execute('PRAGMA query_only=ON')
store.db.create_function('library_scope_record',2,store._scope_filter_record)
get=store.get_artifact
def saved_only(reference):
 if reference in fixture['banned']:raise AssertionError('image source bytes read')
 return get(reference)
store.get_artifact=saved_only
for name in ('artifact','put','transaction','register_material','parse_material'):setattr(store,name,forbidden)
inputs.read_relative_signal_source_inputs=forbidden;calculations.populate_relative_signal_v2=forbidden;Image.open=forbidden
repo=LiteratureRatioSourceRepository(store,fixture['run_id'])
assert repo.read(fixture['sheet_ref'])==fixture['saved']
assert store.db.total_changes==0
assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==0
print('fresh readonly augmented receipt authenticated; zero changes, no source reads or observations')
store.close()
'''
    result = subprocess.run([sys.executable, '-c', script, str(path), str(fixture_path)],
        text=True, capture_output=True, env={**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1])})
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'fresh readonly augmented receipt authenticated' in result.stdout
