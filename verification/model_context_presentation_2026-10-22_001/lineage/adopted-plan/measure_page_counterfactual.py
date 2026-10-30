"""Planning-only read of one supplied pending input; never imports application code."""
from pathlib import Path
from urllib.parse import quote
from copy import deepcopy
import hashlib
import json
import sqlite3

DEST = Path('/tmp/scientific-context-proposal002-xmmw8Rca')
DB = Path('/home/chia/repos/gene_annotation_episode/cases/gene_001/runs/configured_development_002/workspace/state.sqlite3')
RUN = 'run_a9cae64280ed405594a79255d659f917'
EPISODE = 'episode_b14eea3b01b27015465bafe0cc229f7552fcd9baa33f601b82cc5a23d6c17ea8'
EXPECTED = '21e2407799ae840e2192619396d1c74ee823fc445dab2a13aab5e940816ad16c'

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def read():
    with sqlite3.connect('file:' + quote(str(DB)) + '?mode=ro', uri=True,
                        isolation_level=None, timeout=1) as db:
        db.execute('PRAGMA query_only=ON')
        row = db.execute('SELECT call_index, request FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND response IS NULL ORDER BY call_index DESC LIMIT 1', (RUN, EPISODE)).fetchone()
        settings = db.execute('SELECT settings FROM runtime_runs WHERE run_id=?', (RUN,)).fetchone()[0]
    return row, settings

(row, saved_settings) = read()
index, raw_request = row
assert hashlib.sha256(raw_request.encode()).hexdigest() == EXPECTED
request = json.loads(raw_request)
original = request['context']
settings = json.loads(saved_settings)
size = settings['restoration']['preview_size']
history = original['waiting_support']['own_completed_action_history']
start = max(0, len(history)-size)
page = deepcopy(history[start:]) if size else []
start = len(history)-len(page)
indices = [r['decision_index'] for r in page if type(r.get('decision_index')) is int]
catalog=original.get('tools')
availability=('available' if any(isinstance(t,dict) and t.get('name')=='episode.history' for t in catalog) else 'unavailable') if isinstance(catalog,list) else 'unknown'
reason=None if availability=='available' else ('episode_history_not_in_saved_catalog' if availability=='unavailable' else 'saved_tool_catalog_unavailable')
metadata = {
    'version': 'bounded_wait_history_page_v1',
    'run_id': RUN,
    'episode_id': EPISODE,
    'before_decision_index': index,
    'page_size_source': 'restoration.preview_size',
    'preview_size': size,
    'order': 'original_unit_index_ascending',
    'total_rows': len(history),
    'included_rows': len(page),
    'omitted_rows': start,
    'range': {'start': start, 'end_exclusive': len(history), 'unit': 'completed_own_action_history_position'},
    'first_unit_index': page[0]['unit_index'] if page else None,
    'last_unit_index': page[-1]['unit_index'] if page else None,
    'decision_indices': indices,
    'identity_fields': ['episode_id', 'unit_index', 'unit_ref', 'decision_index'],
    'included_rows_without_decision_identity': len(page)-len(indices),
    'included_rows_without_unit_ref': sum(r.get('unit_ref') is None for r in page),
    'raw_history_sha256': digest(history),
    'included_history_sha256': digest(page),
    'history_is_complete': not start,
    'history_lookup': {'availability':availability,'unavailable_reason':reason},
    'exact_included_records': {'tool': 'episode.history', 'arguments': {'view': 'records', 'decision_indices': indices}} if indices and availability=='available' else None,
    'discover_older_decisions': {'tool': 'episode.history', 'arguments': {'view': 'index', 'offset': 0, 'limit': max(1,size)}} if availability=='available' else None,
    'history_result_row_path': 'result.records[*].controller_observation',
    'history_result_step_path': 'result.records[*].controller_observation.step',
    'calculation_context': 'runtime_model_calls.request.context',
}
projected = deepcopy(original)
projected['waiting_support']['own_completed_action_history'] = page
projected['waiting_support']['own_completed_action_history_page'] = metadata
nonhistory = deepcopy(original)
nonhistory['waiting_support']['own_completed_action_history'] = []
check = deepcopy(projected)
check['waiting_support']['own_completed_action_history'] = []
del check['waiting_support']['own_completed_action_history_page']
assert canonical(nonhistory) == canonical(check)
assert canonical(page) == canonical(history[start:])

# The source request and raw full context are read only, and no model is called.
result = {
    'status': 'unimplemented_counterfactual_only',
    'source_request_sha256': EXPECTED,
    'call_index': index,
    'restoration': settings['restoration'],
    'original_context': {'default_json_chars':len(json.dumps(original, allow_nan=False)), 'sha256':digest(original)},
    'full_raw_rows':len(history),
    'presented_rows':len(page),
    'omitted_rows':start,
    'page_unit_indices':[r['unit_index'] for r in page],
    'page_decision_indices':indices,
    'all_page_unit_refs_present':all(r.get('unit_ref') is not None for r in page),
    'page_metadata':metadata,
    'counterfactual_context':{
        'default_json_chars':len(json.dumps(projected, allow_nan=False)),
        'compact_ascii_chars':len(json.dumps(projected,allow_nan=False,separators=(',',':'))),
        'sha256':digest(projected),
        'canonical_order_model_text_sha256':hashlib.sha256(json.dumps(json.loads(canonical(projected)),allow_nan=False).encode()).hexdigest(),
        'canonical_order_model_text_utf8_bytes':len(json.dumps(json.loads(canonical(projected)),allow_nan=False).encode()),
        'own_history_default_json_chars':len(json.dumps(page,allow_nan=False)),
        'page_metadata_default_json_chars':len(json.dumps(metadata,allow_nan=False)),
    },
    'checks': {'included_rows_exact':True,'nonhistory_fields_exact':True,'full_raw_context_not_modified':digest(original)==digest(request['context']), 'source_stored_request_unchanged': read()[0][1] == raw_request},
    'scope': 'Only the repeated own-completed-action model-history component is bounded; no universal size guarantee is asserted for unrelated inputs or one large original row.'
}
(DEST/'PAGE_COUNTERFACTUAL.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:result[k] for k in ('full_raw_rows','presented_rows','omitted_rows','original_context','counterfactual_context','checks')},indent=2))
