"""Fresh readonly authentication of the original constructed failing view."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

from gene_annotation_episode.domain import canonical
from gene_annotation_episode.literature_ratio_source_storage import LiteratureRatioSourceRepository
from gene_annotation_episode.state import Store

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001'
HERE = Path(__file__).resolve().parent
evidence = json.loads((BASE / 'a105_ratio_episode_integration_077/implementation_005/NATIVE_CUSTODY_FAILURE_001.json').read_text())
store = Store.__new__(Store)
store.path = Path(evidence['preserved_db']).parent
store._savepoint = 0
store.db = sqlite3.connect(Path(evidence['preserved_db']).as_uri() + '?mode=ro', uri=True)
store.db.row_factory = sqlite3.Row
store.db.execute('PRAGMA query_only=on')
store.db.execute('BEGIN')
try:
    row = store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
        (evidence['run_id'], evidence['episode_id'], evidence['decision_index'])).fetchone()
    outcome = json.loads(row['result'])
    key = f"{evidence['run_id']}:{evidence['episode_id']}:{evidence['decision_index']}"
    native = store.db.execute('SELECT scope FROM tool_operations WHERE operation_key=?', (key,)).fetchone()
    context = SimpleNamespace(episode_id=evidence['episode_id'], scope=json.loads(native['scope']))
    banned = {outcome['result']['view'][k] for k in ('original_artifact_ref', 'image_artifact_ref')}
    get_artifact = store.get_artifact
    def saved_metadata_only(reference):
        assert reference not in banned, 'original/display image bytes reacquired'
        return get_artifact(reference)
    store.get_artifact = saved_metadata_only
    repository = LiteratureRatioSourceRepository(store, evidence['run_id'])
    receipt = repository._own_view_receipt(context, outcome['result']['view_ref'])
    assert receipt['result_sha256'] == hashlib.sha256(canonical(outcome).encode()).hexdigest()
    assert repository._own_view_receipt(context, outcome['result']['view_ref'], saved_receipt=receipt) == receipt
    readonly = {'query_only': store.db.execute('PRAGMA query_only').fetchone()[0], 'total_changes': store.db.total_changes}
    assert readonly == {'query_only': 1, 'total_changes': 0}
finally:
    store.close()
result = {'utc': datetime.now(timezone.utc).isoformat(),
    'actual_original_constructed_view_authenticates_after_repair': True,
    'saved_receipt_reauthenticates': True, 'digest_covers_full_original_runtime_outcome': True,
    'original_and_display_image_bytes_forbidden': True, 'readonly': readonly,
    'native_code_sha256': hashlib.sha256((ROOT / 'gene_annotation_episode/literature_ratio_source_storage.py').read_bytes()).hexdigest(),
    'scope': 'Fresh-process receipt authentication only, not population, typed return or C1/C4 proof',
    'goal_complete': False}
with (HERE / 'REPAIRED_ORIGINAL_VIEW_ROOT_RECEIPT_054.json').open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result))
