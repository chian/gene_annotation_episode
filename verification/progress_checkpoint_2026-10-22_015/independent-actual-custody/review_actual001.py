"""Independent actual custody review: files + one NEW checkpoint readonly DB.

No application imports, original DB/sidecar opens, active working DB opens,
constructors, provider events, model calls or native/public execution.
"""
from pathlib import Path
import hashlib
import json
import os
import sqlite3
from collections import Counter

import jsonschema

OUT = Path(__file__).resolve().parent
RUN = Path('/home/chia/gene_annotation_episode_runs/configured_api_prechoice_001')
WORK = RUN/'workspace'
CHECKPOINT = WORK/'checkpoint/state.sqlite3'
ORIGINAL_RUN = Path('/home/chia/repos/gene_annotation_episode/cases/gene_001/runs/configured_development_002')
SCHEMA = Path('/home/chia/repos/gene_annotation_episode/verification/scientific_checkpoint_custody_plan_2026-10-22_001/SCHEMAS004.json')
SCOPE = Path('/home/chia/repos/gene_annotation_episode/docs/CONFIGURED_API_CALLER_ACTUAL_SCOPE_2026-10-22_001.md')
CODE = Path('/tmp/gene-annotation-configured-caller-20261022-006/gene_annotation_episode')
READSET, CHECKS = {}, []


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def check(condition, name, **details):
    if not condition:
        raise AssertionError(name)
    CHECKS.append({'check': name, **details})


def file(path, purpose):
    path = Path(path).absolute()
    assert not path.is_relative_to(ORIGINAL_RUN), 'original run files are outside this readset'
    assert path != WORK/'state.sqlite3', 'active working database must not be opened'
    assert path not in (Path(str(WORK/'state.sqlite3')+'-wal'), Path(str(WORK/'state.sqlite3')+'-shm'))
    for part in (path, *path.parents):
        assert not part.is_symlink(), 'unexpected symlink'
    raw = path.read_bytes()
    st = path.stat()
    item = {'path': str(path), 'sha256': sha(raw), 'bytes': len(raw), 'mode': st.st_mode & 0o777,
        'device': st.st_dev, 'inode': st.st_ino, 'purposes': [purpose]}
    if str(path) in READSET:
        previous = READSET[str(path)]
        assert previous['sha256'] == item['sha256'] and previous['bytes'] == item['bytes']
        item['purposes'] = sorted(set(previous['purposes']) | {purpose})
    READSET[str(path)] = item
    return raw


def scoped(relative):
    value = Path(relative)
    assert not value.is_absolute() and '..' not in value.parts
    path = WORK/value
    assert path.is_relative_to(WORK)
    return path


def witness(descriptor, purpose, *, relative=False):
    path = scoped(descriptor['path']) if relative else Path(descriptor['path'])
    raw = file(path, purpose)
    check(sha(raw) == descriptor['sha256'] and len(raw) == descriptor['bytes'], purpose)
    return raw


def save(name, value):
    with (OUT/name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


schema_bytes = file(SCHEMA, 'adopted closed schema')
check(sha(schema_bytes) == 'b000697eb19d68140f14f2e8f7d30c13b60653a6e443c0508c6ec1519b7d6112', 'exact adopted schema hash')
schema = json.loads(schema_bytes)
file(SCOPE, 'actual execution scope')
file(CODE/'domain.py', 'read canonical/identity source, without import')
file(CODE/'state.py', 'read Store.get/put source, without import')


def validate(kind, value):
    jsonschema.Draft202012Validator({'$defs': schema['$defs'], '$ref': '#/$defs/'+kind}).validate(value)
    CHECKS.append({'check': 'closed '+kind+' schema'})


result_bytes = file(RUN/'caller-inputs/C_RESULT001.json', 'actual C result')
operator_bytes = file(RUN/'caller-inputs/C_OPERATOR_VERIFICATION001.json', 'operator custody verification')
result, operator = json.loads(result_bytes), json.loads(operator_bytes)
validate('result', result)
check(result['destination_workspace'] == str(WORK), 'exact destination')
receipt_bytes = witness(result['receipt'], 'actual receipt descriptor')
receipt = json.loads(receipt_bytes)
validate('receipt', receipt)
check(result['receipt'] == operator['receipt'], 'operator/result receipt descriptor equality')
check(operator['result'] == {'path': str(RUN/'caller-inputs/C_RESULT001.json'), 'sha256': sha(result_bytes), 'bytes': len(result_bytes)}, 'operator result witness')
check(receipt['destination_workspace'] == str(WORK), 'receipt destination equality')
check(receipt['source']['run_id'] == 'run_a9cae64280ed405594a79255d659f917', 'exact original run id')
check(receipt['source']['implementation_sha256'] == 'a192366fa67def7bbeb7b7ef87330e402f4244c154d2dd635444f5e98265383a', 'original source implementation pin')
check(operator['execution_implementation_pin'] == '209ff0d8ca80a6ee2a592f997933115e2f688f8ccc90e6db35e40146dabb613f', 'actual C implementation pin witness')
check(len(result['initial_known_record_refs']) == 200 and result['initial_known_record_refs'] == receipt['initial_known_record_refs'], 'exact 200 inherited refs')
check(result['initial_known_record_refs'] == sorted(set(result['initial_known_record_refs'])), 'inherited refs sorted unique')
check(len(receipt['caller_initial_known_record_refs']) == 198 == operator['caller_selected_refs'], 'exact 198 caller refs')
lineage_refs = {receipt['lineage']['observation_source_ref'], receipt['lineage']['index_source_ref']}
check(result['lineage_source_refs'] == {'observations': receipt['lineage']['observation_source_ref'], 'index': receipt['lineage']['index_source_ref']}, 'exact lineage handles')
check(set(result['initial_known_record_refs']) == set(receipt['caller_initial_known_record_refs']) | lineage_refs, 'exact caller/lineage union')
check(receipt['initial_known_record_refs_sha256'] == sha(canonical(result['initial_known_record_refs']).encode()), 'inherited list canonical hash')

for name in ('preservation',):
    p = receipt['source'][name]
    for key in ('database', 'wal', 'shm'):
        check(p[key+'_before'] == p[key+'_after'], 'recorded scientific '+key+' witnesses equal')
    check(p['wal_before'] is None or p['wal_before']['bytes'] == 0, 'recorded scientific empty WAL')
p = receipt['source']['execution_inventory']['native_registry_preservation']
for key in ('database', 'wal', 'shm'):
    check(p[key+'_before'] == p[key+'_after'], 'recorded native '+key+' witnesses equal')
check(p['wal_before'] is None or p['wal_before']['bytes'] == 0, 'recorded native empty WAL')

inventories = {}
for name, kind in (('table_manifest', 'table_manifest'), ('artifact_manifest', 'artifact_manifest'),
        ('committed_reference_manifest', 'committed_reference_manifest')):
    value = json.loads(witness(receipt['checkpoint'][name], 'checkpoint '+name, relative=True))
    validate(kind, value)
    inventories[name] = value
implementation = json.loads(witness(receipt['source']['implementation_file_manifest'], 'source implementation inventory', relative=True))
validate('implementation_file_manifest', implementation)
check(implementation['implementation_sha256'] == receipt['source']['implementation_sha256'], 'implementation inventory pin matches source witness')

checkpoint_bytes = witness(receipt['checkpoint']['database'], 'immutable new checkpoint hash', relative=True)
check(sha(checkpoint_bytes) == receipt['source']['preservation']['database_before']['sha256'], 'checkpoint matches recorded original source main bytes')
check(len(checkpoint_bytes) == 211947520, 'checkpoint actual byte size')
del checkpoint_bytes
checkpoint_stat, working_stat = CHECKPOINT.stat(), (WORK/'state.sqlite3').stat()
check((checkpoint_stat.st_dev, checkpoint_stat.st_ino) != (working_stat.st_dev, working_stat.st_ino), 'current working/checkpoint inodes distinct')

authority = {}
destinations = set()
for item in receipt['source']['authority_files']:
    relative = item['checkpoint_relative_path']
    check(relative.startswith('checkpoint/authority/') and relative not in destinations, 'unique authority mapping')
    destinations.add(relative)
    data = witness({'path': relative, 'sha256': item['sha256'], 'bytes': item['bytes']}, 'authority copy '+Path(relative).name, relative=True)
    authority[relative] = data
check(len(authority) == 9, 'nine declared authority copies')
launch = json.loads(authority['checkpoint/authority/case-launch.json'])
case = json.loads(authority['checkpoint/authority/case/case.json'])
check(launch['configuration']['workspace'] == receipt['source']['workspace'], 'old case-launch workspace retained as provenance')
check(case['target_ref'] == receipt['fixed_identity']['target_ref'] and case['problem_ref'] == receipt['fixed_identity']['problem_ref'], 'fixed case target/problem')
for name, expected in case['target_files'].items():
    check(sha(authority['checkpoint/authority/case/'+name]) == expected, 'declared target file hash '+name)

artifacts = inventories['artifact_manifest']
for item in artifacts['artifacts']:
    check(item['id'] == 'artifact_'+item['sha256'], 'original artifact id/hash consistency')
    witness({'path': item['relative_path'], 'sha256': item['sha256'], 'bytes': item['bytes']}, 'original artifact '+item['id'], relative=True)
check(artifacts['count'] == len(artifacts['artifacts']) == receipt['preserved_counts']['artifacts'] == 144, 'all 144 original artifacts')
check(sum(item['bytes'] for item in artifacts['artifacts']) == artifacts['total_bytes'] == receipt['preserved_counts']['artifact_bytes'] == 4201310, 'original artifact byte total')

db = sqlite3.connect(CHECKPOINT.as_uri()+'?mode=ro&immutable=1', uri=True)
db.row_factory = sqlite3.Row
try:
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')
    records, manifest_rows = {}, []
    for table in ('inputs', 'records'):
        for row in db.execute('SELECT id,data FROM '+table+' ORDER BY id COLLATE BINARY'):
            value = json.loads(row['data'])
            check(value['id'] == row['id'], 'committed stored id equality')
            records[row['id']] = value
            manifest_rows.append({'reference': row['id'], 'record_type': value['record_type'],
                'source_table': table, 'data_raw_utf8_sha256': sha(row['data'].encode()),
                'data_raw_utf8_bytes': len(row['data'].encode())})
    committed = inventories['committed_reference_manifest']
    check(manifest_rows == committed['records'], 'full raw committed-reference manifest matches checkpoint')
    check(committed['input_count'] == 1 and committed['record_count'] == 192 and len(records) == 193, '193 actual committed inputs and records')
    check(set(records) <= set(receipt['caller_initial_known_record_refs']), 'all committed refs explicitly caller inherited')
    extras = set(receipt['caller_initial_known_record_refs'])-set(records)
    extra_kinds = Counter()
    for ref in extras:
        found = False
        for table in ('material_members', 'artifacts'):
            if db.execute('SELECT 1 FROM '+table+' WHERE id=?', (ref,)).fetchone():
                extra_kinds[table] += 1
                found = True
                break
        check(found, 'extra caller reference directly resolves in checkpoint')
    native = [ref for ref, value in records.items() if value['record_type'] == 'native_execution']
    check(len(native) == 4 and set(native) <= set(result['initial_known_record_refs']), 'all four native execution receipts inherited')
    original_artifact_ids = {item['id'] for item in artifacts['artifacts']}
    check(all(records[ref]['measurement_artifact_ref'] in original_artifact_ids for ref in native), 'all native receipt artifact files retained')
    revisions = list(db.execute('SELECT record_type,key_ref,revision,record_ref FROM current_revisions'))
    check(all(row['record_ref'] in records and row['record_ref'] in result['initial_known_record_refs'] for row in revisions), 'all current revision refs inherited')
    counts = {name: db.execute('SELECT count(*) FROM '+name).fetchone()[0] for name in
        ('runtime_runs', 'runtime_episodes', 'runtime_actions', 'runtime_observations', 'runtime_model_calls')}
    check(counts == operator['old_runtime_counts'] == {'runtime_runs': 1, 'runtime_episodes': 1,
        'runtime_actions': 179, 'runtime_observations': 175, 'runtime_model_calls': 180}, 'exact old runtime counts in immutable checkpoint')
    run = db.execute('SELECT run_id,settings FROM runtime_runs').fetchone()
    check(run['run_id'] == receipt['source']['run_id'] and sha(run['settings'].encode()) == receipt['source']['settings_raw_utf8_sha256'], 'original raw settings witness')
    pending = list(db.execute('SELECT * FROM runtime_model_calls WHERE response IS NULL'))
    check(len(pending) == 1, 'sole old pending call')
    pending = pending[0]
    check(sha(pending['request'].encode()) == receipt['source']['pending']['request_raw_utf8_sha256'] == '21e2407799ae840e2192619396d1c74ee823fc445dab2a13aab5e940816ad16c', 'exact old pending raw request witness')
    check(pending['call_index'] == receipt['source']['pending']['call_index'] == db.execute('SELECT max(call_index) FROM runtime_model_calls').fetchone()[0], 'original pending index remains latest')
    check(db.execute('SELECT 1 FROM runtime_actions WHERE decision_index=?', (pending['call_index'],)).fetchone() is None, 'no selected old action at pending call')
    target = records[receipt['fixed_identity']['target_ref']]
    check(target['length'] == 762 and target['sequence_ref'] == receipt['fixed_identity']['target_sequence_artifact_ref'], '762-nt target identity retained')
    observations = [dict(row) for row in db.execute('SELECT * FROM runtime_observations ORDER BY unit_index')]
    actions = {row[0] for row in db.execute('SELECT decision_index FROM runtime_actions')}
    check(all(ref not in records for ref in lineage_refs), 'two lineage source IDs are new to checkpoint')
    revision_record_count = sum(v['record_type'] in {'assessment', 'annotation', 'interpretation_account'} for v in records.values())
finally:
    db.close()

def artifact(reference, purpose):
    checksum = reference.removeprefix('artifact_')
    data = file(WORK/'artifacts'/checksum[:2]/checksum, purpose)
    check(sha(data) == checksum, purpose+' digest')
    return data

stream = artifact(receipt['lineage']['observation_artifact_ref'], 'new original-observation stream')
index_bytes = artifact(receipt['lineage']['index_artifact_ref'], 'new observation index')
index = json.loads(index_bytes)
validate('observation_index', index)
check(index_bytes == canonical(index).encode(), 'index canonical bytes without LF')
check(stream == b''.join(row['observation'].encode()+b'\n' for row in observations), 'all 175 original raw TEXT rows plus separate LF exactly preserved')
check(index['record_count'] == len(index['rows']) == len(observations) == 175, '175 indexed observations')
check(index['observation_artifact_sha256'] == sha(stream) and index['observation_artifact_bytes'] == len(stream), 'stream hash/byte witnesses')
check(index['observation_source_ref'] == receipt['lineage']['observation_source_ref'], 'index source linkage')
offset, seen = 0, set()
for row, indexed in zip(observations, index['rows']):
    raw = row['observation'].encode()
    value = json.loads(raw)
    check(indexed['raw_text_utf8_offset'] == offset and indexed['raw_text_utf8_bytes'] == len(raw)
        and indexed['raw_text_utf8_sha256'] == sha(raw), 'raw row index offset/size/hash')
    check(indexed['unit_index'] == row['unit_index'] and indexed['unit_ref'] == value['unit_ref'], 'original unit identity preserved')
    check(indexed['decision_index_present'] == ('decision_index' in value)
        and indexed['decision_index'] == value.get('decision_index'), 'missing/null/known decision preserved')
    decision = indexed['decision_index']
    if decision is not None:
        check(decision in actions and decision not in seen, 'known decision has distinct actual old action')
        seen.add(decision)
    check(indexed['delimiter_bytes'] == 1 and indexed['delimiter_hex'] == '0a', 'separate LF delimiter')
    offset += len(raw)+1
check(offset == len(stream), 'entire raw stream covered without trailing unindexed bytes')

metadata = {'version': 'scientific_checkpoint_lineage_source_v1',
    'meaning': 'prior_run_lineage_not_new_local_observations', 'source_run_id': receipt['source']['run_id'],
    'source_episode_id': receipt['source']['episode_id'],
    'source_implementation_sha256': receipt['source']['implementation_sha256'],
    'source_settings_raw_utf8_sha256': receipt['source']['settings_raw_utf8_sha256'],
    'source_pending_request_raw_utf8_sha256': receipt['source']['pending']['request_raw_utf8_sha256'],
    'source_table_manifest_sha256': receipt['checkpoint']['table_manifest']['sha256'],
    'source_artifact_manifest_sha256': receipt['checkpoint']['artifact_manifest']['sha256'],
    'original_observation_count': 175, 'fixed_target_ref': receipt['fixed_identity']['target_ref']}
for kind, payload_ref, expected_ref, parents in (
        ('original_observations', receipt['lineage']['observation_artifact_ref'], receipt['lineage']['observation_source_ref'], []),
        ('observation_index', receipt['lineage']['index_artifact_ref'], receipt['lineage']['index_source_ref'], [receipt['lineage']['observation_source_ref']])):
    body = {**metadata, 'kind': kind}
    validate('lineage_source_metadata', body)
    raw = canonical(body).encode()
    request_ref = 'artifact_'+sha(raw)
    check(artifact(request_ref, 'lineage metadata '+kind) == raw, 'actual closed lineage metadata bytes '+kind)
    payload = {'provider': 'caller.scientific_checkpoint_fork', 'accession': receipt['fork_id'],
        'uri': None, 'artifact_ref': payload_ref, 'text_ref': payload_ref, 'request_ref': request_ref,
        'version': 'scientific_checkpoint_fork_v1', 'retrieved_at': None,
        'operand_refs': [receipt['fixed_identity']['target_ref']], 'parent_source_refs': parents}
    validate('lineage_source_input', payload)
    actual_id = 'source_'+sha(canonical({'origin': 'caller', 'record': payload}).encode())[:24]
    check(actual_id == expected_ref, 'recomputed actual source identity '+kind)
    validate('lineage_source_output', {**payload, 'id': actual_id, 'record_type': 'source', 'origin': 'caller'})

identity_material = {'source_run_id': receipt['source']['run_id'],
    'source_settings_raw_utf8_sha256': receipt['source']['settings_raw_utf8_sha256'],
    'source_pending_request_raw_utf8_sha256': receipt['source']['pending']['request_raw_utf8_sha256'],
    'source_table_manifest_sha256': receipt['checkpoint']['table_manifest']['sha256'],
    'source_artifact_manifest_sha256': receipt['checkpoint']['artifact_manifest']['sha256'],
    'destination_workspace': str(WORK), 'caller_initial_known_record_refs': sorted(receipt['caller_initial_known_record_refs'])}
check(receipt['fork_id'] == 'scientific_checkpoint_'+sha(canonical(identity_material).encode())[:24], 'fork identity material matches receipt')
check(sha(file(CHECKPOINT, 'checkpoint after readonly inspection')) == receipt['checkpoint']['database']['sha256'], 'checkpoint unchanged by independent inspection')

save('READSET001.json', {'files': list(READSET.values()), 'sqlite_connections': [
    {'uri': CHECKPOINT.as_uri()+'?mode=ro&immutable=1', 'query_only': True, 'closed_explicitly': True}],
    'working_database_observation': {'path': str(WORK/'state.sqlite3'), 'operation': 'stat only',
        'device': working_stat.st_dev, 'inode': working_stat.st_ino, 'hash_not_read': True}})
save('CHECKS001.json', CHECKS)
summary = {'status': 'passed', 'scope': 'independent actual custody handoff review before scientific launch',
    'result_sha256': sha(result_bytes), 'receipt_sha256': sha(receipt_bytes),
    'inherited_refs': 200, 'caller_refs': 198, 'new_lineage_sources': 2,
    'committed_input_and_record_refs': 193, 'additional_resolvable_caller_refs': dict(extra_kinds),
    'all_committed_revisions_covered': True, 'revision_records_inherited': revision_record_count,
    'current_revision_rows_covered': len(revisions), 'native_receipts_covered': 4,
    'original_runtime_counts': counts, 'authority_files_checked': 9,
    'original_artifact_files_checked': 144, 'original_artifact_bytes_checked': 4201310,
    'raw_observations_checked': 175, 'checkpoint_sha256': receipt['checkpoint']['database']['sha256'],
    'checkpoint_bytes': 211947520, 'working_and_checkpoint_inodes_distinct': True,
    'readset_files': len(READSET), 'check_count': len(CHECKS),
    'working_publication_hash': {'meaning': 'historical at custody publication',
        'descriptor': receipt['workspace_database_at_publication'], 'current_hash_not_read_or_claimed_equal': True},
    'limits': ['Only the NEW immutable checkpoint was opened through SQLite; no original DB or sidecar opened.',
        'No active working database content or current logical state was inspected.',
        'Original zero-write guards are internally consistent saved witnesses, not a new resampling of original DBs.',
        'New lineage source payload identities were recomputed from retained artifacts; current working rows were not queried.',
        'No application imports/constructors, new work, scoring, model/native/public calls or authority writes.',
        'No scientific conclusion or overall-goal completion follows from custody correctness.']}
save('RESULTS001.json', summary)
print(json.dumps(summary, sort_keys=True))
