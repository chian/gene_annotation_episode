"""Read only the declared frozen engineering action; no model or paper reads."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.literature_ratio_source_storage import LiteratureRatioSourceRepository
from gene_annotation_episode.state import Store

root = Path(__file__).resolve().parents[3]
failure = root / 'verification/literature_reference_evidence_2026-10-25_001/a105_ratio_episode_integration_077/implementation_005/NATIVE_CUSTODY_FAILURE_001.json'
declared = json.loads(failure.read_text())
path = Path(declared['preserved_db'])
store = Store.__new__(Store)
store.path, store._savepoint = path.parent, 0
store.db = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
store.db.row_factory = sqlite3.Row
store.db.execute('PRAGMA query_only=ON')
try:
    run, episode, index = (declared[k] for k in ('run_id', 'episode_id', 'decision_index'))
    action = dict(store.db.execute('SELECT decision_index,action,result FROM runtime_actions '
        'WHERE run_id=? AND episode_id=? AND decision_index=?', (run, episode, index)).fetchone())
    native = dict(store.db.execute('SELECT * FROM tool_operations WHERE operation_key=?',
        (f'{run}:{episode}:{index}',)).fetchone())
    runtime_result, native_result = json.loads(action['result']), json.loads(native['result'])
    stripped = {key: value for key, value in runtime_result.items() if key != 'pending_work_after_action'}
    assert canonical(stripped) == canonical(native_result)
    assert set(runtime_result) - set(native_result) == {'pending_work_after_action'}
    context = SimpleNamespace(episode_id=episode, scope=json.loads(native['scope']))
    repo = LiteratureRatioSourceRepository(store, run)
    try:
        receipt = repo._own_view_receipt(context, native_result['result']['view_ref'])
        outcome = {'status': 'accepted', 'receipt': receipt}
    except ContractError as error:
        outcome = {'status': 'rejected', 'code': str(error)}
    assert store.db.total_changes == 0
    output = {'evidence_class': 'frozen077 actual selected Workflow engineering action; no paper/model',
        'preserved_db': str(path), 'read_only': True, 'total_changes': store.db.total_changes,
        'runtime_action': action, 'tool_operation': native,
        'runtime_result_sha256': hashlib.sha256(canonical(runtime_result).encode()).hexdigest(),
        'native_result_sha256': hashlib.sha256(canonical(native_result).encode()).hexdigest(),
        'runtime_minus_declared_addition_equals_native': True,
        'native_storage_sha256': hashlib.sha256((root / 'gene_annotation_episode/literature_ratio_source_storage.py').read_bytes()).hexdigest(),
        'outcome': outcome}
    Path(sys.argv[1]).write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({'output': sys.argv[1], 'outcome': outcome, 'total_changes': store.db.total_changes}))
finally:
    store.close()
