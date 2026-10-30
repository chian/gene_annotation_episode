"""Read-only verification and token-free derived export of the selected run.

No application module, Store, HTTP client or execution port is imported.
The original SQLite database is opened mode=ro/query_only with one transaction.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3


ROOT = Path(__file__).resolve().parent
WORKING = Path('/tmp/hmmer-real-service-fixed-target-20261022-001')
PHASES = ROOT/'phase-evidence'
PIN = '9007ce019b0df13f122cdc53772b45e56684a39755b2e79c9027de2a451fbd1c'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(body):
    return hashlib.sha256(body).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True)+'\n')


def inventory(directory):
    result = {}
    for path in sorted(directory.rglob('*')):
        assert not path.is_symlink(), 'Symlink in working custody'
        if path.is_file():
            body = path.read_bytes()
            result[str(path.relative_to(directory))] = {'sha256': sha(body), 'size': len(body)}
    return result


def redact_headers(value):
    """Derived JSON only; original bytes and content-addresses remain private."""
    forbidden = {'set-cookie', 'cookie', 'authorization', 'proxy-authorization'}
    if isinstance(value, dict):
        return {key: '<omitted sensitive header>' if key.lower() in forbidden else
                redact_headers(item) for key, item in value.items()}
    if isinstance(value, list):
        if len(value) == 2 and isinstance(value[0], str) and value[0].lower() in forbidden:
            return [value[0], '<omitted sensitive header>']
        return [redact_headers(item) for item in value]
    return value


def main():
    original_before = inventory(WORKING)
    binding = load(PHASES/'selected-binding.json')
    assert binding['sources']['runtime_implementation_sha256'] == PIN
    assert sha((PHASES/'verify_hmmer_service.py').read_bytes()) == '562c1f705ffeb924091c76c0d9cc2b75c3e5fd60635cac9f51237fa1f5f4dc7a'
    phase_rows, selected = [], []
    for directory in sorted((PHASES/'invocations').iterdir()):
        intent, after = load(directory/'intent.json'), load(directory/'sources-after.json')
        assert intent['sources'] == binding['sources'] == after['identity']
        assert after['unchanged'] is True
        assert intent['arguments']['expected_runtime_pin'] == PIN
        assert intent['script_sha256'] == sha((PHASES/'verify_hmmer_service.py').read_bytes())
        result = load(directory/'result.json')['result']
        outcome = load(directory/'selected-outcome.json') if (directory/'selected-outcome.json').exists() else None
        if outcome is not None:
            assert result['outcome'] == outcome
        phase_rows.append({'directory': directory.name, 'arguments': intent['arguments'],
            'selected_at': intent['selected_at'], 'all_128_source_hashes_preserved': True})
        selected.append(outcome)
    assert [row['arguments']['phase'] for row in phase_rows] == [
        'prepare-order', 'submit_once', 'status_once', 'result_once', 'publish', 'submit_once']
    submit, status, result, publication, replay = selected[1:]
    assert submit == replay, 'Submit replay changed the original immutable receipt'
    assert submit['observed_at'] == replay['observed_at'] == '2026-10-22T06:11:14.189648+00:00'
    assert submit['receipt_ref'] == 'provider_operation_0f3df1f711be460c6f3e4fb6'
    job = binding['order']['job_ref']
    assert job == 'provider_job_cb683b6c3936f1045d8a9477'
    remote = submit['remote_id']
    assert remote == '9f1d2433-cca8-43b5-8c52-d7d3927dee6f'
    assert len(set(publication['record_refs'])) == len(publication['record_refs']) == 11
    assert publication['result']['page'] == 1 and publication['result']['page_size'] == 2
    assert publication['result']['page_count'] == 2 and publication['result']['projection_failures'] == []
    assert len(publication['result']['publication_rows']) == 6
    assert status['state'] == result['state'] == 'SUCCESS' and result['result_cached']

    seed = load(WORKING/'fixed-target-seed.json')
    assert seed == binding['seed']
    assert sha((WORKING/'fixed-target-seed.json').read_bytes()) == binding['seed_receipt_sha256']
    assert len(seed['initial_known_record_refs']) == seed['verification']['initial_known_record_ref_count'] == 11
    assert seed['fixed_identity']['protein_sequence_sha256'] == binding['protein_sha256']
    assert seed['fixed_identity']['target_ref'] == 'input_a5c60b96717424cdf5138420'
    assert seed['fixed_identity']['problem_ref'] == 'problem_9d89f9abcb43930a1bb557f1'
    assert seed['verification']['sqlite_reader_bookkeeping']['authoritative_bytes_unchanged']

    # This is the only SQLite connection. No source/original/active Store is opened.
    db = sqlite3.connect((WORKING/'state.sqlite3').as_uri()+'?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')
    try:
        tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        counts = {name: db.execute('SELECT count(*) FROM "'+name+'"').fetchone()[0] for name in tables}
        assert counts['provider_jobs'] == counts['public_search_orders'] == counts['public_search_order_scopes'] == 1
        assert counts['public_search_claims'] == counts['public_search_results'] == counts['public_search_publications'] == 1
        assert counts['public_search_operations'] == counts['public_search_selections'] == 3
        assert not any(name.startswith('runtime_') for name in tables)
        records = {row['id']: json.loads(row['data']) for row in db.execute('SELECT * FROM records')}
        inputs = {row['id']: json.loads(row['data']) for row in db.execute('SELECT * FROM inputs')}
        members = {row['id']: json.loads(row['data']) for row in db.execute('SELECT * FROM material_members')}
        artifacts = {row['id']: dict(row) for row in db.execute('SELECT * FROM artifacts')}
        problem = json.loads(db.execute('SELECT data FROM problem').fetchone()[0])
        assert sha(canonical(problem).encode()) == seed['source']['problem_sha256']
        assert sha(canonical(inputs[seed['fixed_identity']['target_ref']]).encode()) == seed['source']['target_sha256']
        all_records = {**records, **inputs, **members,
            **{ref: {**row, 'record_type': 'artifact'} for ref, row in artifacts.items()}}
        for row in seed['intake_records']:
            assert sha(canonical(all_records[row['reference']]).encode()) == row['content_sha256']
        assert records[binding['product_ref']] == binding['product_record']
        assert not any(row['record_type'] in {'hypothesis', 'assessment', 'annotation', 'interpretation_account', 'native_execution'}
            for row in records.values())
        job_row = dict(db.execute('SELECT * FROM provider_jobs').fetchone())
        assert job_row['id'] == job and job_row['remote_id'] == remote and job_row['state'] == 'returned'
        assert json.loads(job_row['request']) == binding['request']
        assert json.loads(db.execute('SELECT data FROM public_search_orders').fetchone()[0]) == binding['order']
        assert json.loads(db.execute('SELECT data FROM public_search_order_scopes').fetchone()[0]) == binding['order_scope']
        assert json.loads(db.execute('SELECT data FROM public_search_registries').fetchone()[0]) == binding['registry']
        receipt_rows = {row['operation_key']: json.loads(row['data']) for row in db.execute('SELECT * FROM public_search_operations')}
        for receipt in (submit, status, result):
            assert receipt_rows[receipt['operation_key']] == receipt
            assert receipt['job_ref'] == job and receipt['remote_id'] == remote
            assert receipt['registry_ref'] == binding['registry']['registry_ref']
            assert receipt['request_sha256'] == binding['order']['request_sha256']
        cached = dict(db.execute('SELECT * FROM public_search_results').fetchone())
        assert cached['page'] == 1 and cached['page_size'] == 2
        assert cached['receipt_ref'] == result['receipt_ref'] and cached['snapshot_ref'] == result['snapshot_ref']
        assert json.loads(db.execute('SELECT data FROM public_search_publications').fetchone()[0]) == publication
        claims = [json.loads(row[0]) for row in db.execute('SELECT data FROM public_search_claims')]
        assert claims[0]['operation_key'] == submit['operation_key'] and claims[0]['retry_of'] is None
    finally:
        db.rollback()
        db.close()

    def artifact(ref):
        row = artifacts[ref]
        path = WORKING/'artifacts'/row['sha256'][:2]/row['sha256']
        body = path.read_bytes()
        assert row['id'] == 'artifact_'+row['sha256'] and sha(body) == row['sha256'] and len(body) == row['size']
        return body

    assert sha(artifact(binding['order']['request_ref'])) == binding['order']['request_sha256']
    assert artifact(binding['order']['request_ref']) == canonical(binding['request']).encode()
    assert sha(artifact(binding['order']['query_fasta_ref'])) == binding['submitted_fasta_sha256']
    assert len(artifact(binding['product_record']['sequence_ref'])) == 253
    assert sha(artifact(binding['product_record']['sequence_ref'])) == binding['protein_sha256']
    assert sha(canonical(binding['client_binding']).encode()) == binding['registry']['client_binding_sha256']
    assert sha(canonical(binding['scope']).encode()) == binding['order_scope']['scope_sha256']

    captures, raw_result = [], None
    for directory in sorted((WORKING/'public-search-http-captures').iterdir()):
        if directory.name == 'locks':
            continue
        assert {path.name for path in directory.iterdir()} == {'manifest.json', 'response.entity'}
        manifest = load(directory/'manifest.json')
        entity = (directory/'response.entity').read_bytes()
        assert manifest['client_failure'] is None and manifest['job_ref'] == job
        assert manifest['registry_ref'] == binding['registry']['registry_ref']
        assert sha(entity) == manifest['snapshot']['content_sha256'] and len(entity) == manifest['snapshot']['content_bytes']
        receipt = receipt_rows[manifest['operation_key']]
        assert manifest['selection_sha256'] == receipt['selection_sha256']
        native = json.loads(entity)
        if manifest['operation'] == 'submit':
            assert native['id'] == remote
            assert manifest['snapshot']['request']['database'] == 'pdb'
            assert manifest['snapshot']['request']['input'].encode() == artifact(binding['order']['query_fasta_ref'])
        elif manifest['operation'] == 'status':
            assert native['task']['status'] == 'SUCCESS' and native['id'] == remote
            assert native['algo'] == 'phmmer' and native['database']['id'] == 'pdb'
        else:
            raw_result = native
            assert native['status'] == 'SUCCESS' and native['page_count'] == 2
        captures.append({'operation': manifest['operation'], 'operation_key': manifest['operation_key'],
            'receipt_ref': receipt['receipt_ref'], 'http_status': manifest['snapshot']['transport']['status'],
            'retrieved_at': manifest['snapshot']['retrieved_at'], 'observed_at': receipt['observed_at'],
            'entity_sha256': sha(entity), 'entity_bytes': len(entity),
            'requested_method': manifest['snapshot']['transport']['request']['method'],
            'requested_url': manifest['snapshot']['transport']['request']['url'],
            'effective_url': manifest['snapshot']['transport'].get('effective_url')})
    assert len(captures) == 3 and raw_result is not None
    hits = raw_result['result']['hits']
    assert len(hits) == 2
    pub = publication['result']
    body = json.loads(artifact(records[pub['publication_ref']]['artifact_ref']))
    assert body['publication_rows'] == pub['publication_rows']
    assert body['registry_ref'] == binding['registry']['registry_ref'] and body['job_ref'] == job
    assert body['request_sha256'] == binding['order']['request_sha256']
    assert body['acquisition_receipt_ref'] == result['receipt_ref']
    assert body['selector'] == {'version': 'public_search_result_selector_v1', 'provider': 'hmmer',
        'first_page': 1, 'last_page': 1, 'page_size': 2}
    assert body['source_ref'] == pub['source_ref']
    raw_body = artifact(records[pub['source_ref']]['artifact_ref'])
    result_capture = next(row for row in captures if row['operation'] == 'result')
    assert sha(raw_body) == result_capture['entity_sha256']
    assert raw_result == json.loads(raw_body)
    refs_by_hit = {row['hit_ordinal']: row['record_ref'] for row in pub['publication_rows'] if row['record_type'] == 'reference'}
    seen = set()
    for row in pub['publication_rows']:
        assert row['record_ref'] in publication['record_refs'] and row['record_ref'] not in seen
        seen.add(row['record_ref'])
        assert row['source_ref'] == pub['source_ref'] and row['job_ref'] == job
        assert row['subject_ref'] == binding['product_ref'] and row['provider'] == 'hmmer'
        assert row['registry_ref'] == binding['registry']['registry_ref']
        assert row['request_sha256'] == binding['order']['request_sha256']
        assert row['acquisition_receipt_ref'] == result['receipt_ref']
        assert row['publication_operation_key'] == body['operation_key']
        assert row['page'] == 1 and row['page_size'] == 2
        record = records[row['record_ref']]
        assert record['record_type'] == row['record_type'] and record['source_ref'] == pub['source_ref']
        assert 0 <= row['hit_ordinal'] < len(hits)
        if row['record_type'] == 'reference':
            assert row['domain_ordinal'] is None
        else:
            assert record['subject_refs'] == [binding['product_ref']]
            assert record['source_subject_refs'] == [refs_by_hit[row['hit_ordinal']]]
            assert 0 <= row['domain_ordinal'] < len(hits[row['hit_ordinal']]['domains'])
    assert Counter(row['record_type'] for row in pub['publication_rows']) == {'reference': 2, 'observation': 4}
    assert [len(hit['domains']) for hit in hits] == [3, 1]

    save(ROOT/'exports/problem.json', problem)
    save(ROOT/'exports/scientific-records.json', {'inputs': inputs, 'records': records, 'material_members': members})
    save(ROOT/'exports/operation-receipts.json', list(receipt_rows.values()))
    save(ROOT/'exports/submission-claims.json', claims)
    save(ROOT/'exports/order.json', binding['order'])
    save(ROOT/'exports/scope.json', binding['order_scope'])
    save(ROOT/'exports/request.json', binding['request'])
    save(ROOT/'exports/registry.json', binding['registry'])
    save(ROOT/'exports/result-publication.json', publication)
    save(ROOT/'exports/provider-job.derived.json', {'version': 'credential_free_job_projection_v1',
        'row': {key: value for key, value in job_row.items() if key not in {'submission', 'latest_status', 'result'}},
        'omitted_serialized_snapshot_fields': ['submission', 'latest_status', 'result'],
        'original_snapshot_receipts': [receipt['receipt_ref'] for receipt in (submit, status, result)]})

    omissions, derived, safe_files = [], [], []
    for name, descriptor in original_before.items():
        path = WORKING/name
        raw = path.read_bytes()
        if name == 'state.sqlite3' or name.endswith(('-wal', '-shm')):
            omissions.append({'path': name, **descriptor, 'reason': 'Raw database may retain session-cookie transport; private custody only',
                'private_custody': str(path)})
            continue
        if name.startswith('public-search-http-captures/locks/'):
            omissions.append({'path': name, **descriptor, 'reason': 'Local lock bookkeeping, not required for derived evidence',
                'private_custody': str(path)})
            continue
        if b'sessionid=' in raw.lower():
            omissions.append({'path': name, **descriptor, 'reason': 'Contains Set-Cookie sessionid; private custody only',
                'private_custody': str(path)})
            sanitized = redact_headers(json.loads(raw))
            target = ROOT/'derived-transport'/(sha(name.encode())+'.redacted.json')
            save(target, {'version': 'credential_free_transport_derivative_v1',
                'original_relative_path': name, 'original_sha256': descriptor['sha256'],
                'original_size': descriptor['size'], 'redaction': 'Sensitive HTTP header values omitted',
                'derived_value': sanitized})
            derived.append({'original_path': name, 'original_sha256': descriptor['sha256'],
                'derived_path': str(target.relative_to(ROOT)), 'derived_sha256': sha(target.read_bytes()),
                'derived_size': target.stat().st_size})
        else:
            target = ROOT/'working-safe'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(raw)
            safe_files.append({'path': name, **descriptor})
    for ref in artifacts:
        artifact(ref)  # Verify every actual original artifact even if omitted.
    original_after = inventory(WORKING)
    # Only a read-only SQLite connection was used. Record any engine bookkeeping
    # separately, never equate this with a generic no-bookkeeping guarantee.
    changes = {name: {'before': original_before.get(name), 'after': original_after.get(name)}
        for name in sorted(set(original_before)|set(original_after)) if original_before.get(name) != original_after.get(name)}
    assert original_after['state.sqlite3'] == original_before['state.sqlite3']
    assert all(name in {'state.sqlite3-wal', 'state.sqlite3-shm'} for name in changes)
    save(ROOT/'WORKING_CUSTODY.json', {'source': str(WORKING), 'before': original_before,
        'after': original_after, 'observed_reader_bookkeeping': changes,
        'raw_database_preserved': original_after['state.sqlite3'] == original_before['state.sqlite3'],
        'publication_kind': 'Partial credential-free derived export; not a complete byte-identical database/replay capsule',
        'safe_original_files': safe_files, 'intentionally_omitted': omissions, 'derived_files': derived})
    summary = {'verified_at': datetime.now(timezone.utc).isoformat(), 'source_pin': PIN,
        'phases': phase_rows, 'all_six_source_guards_match': True,
        'submit_replay_exact': submit == replay, 'submit_original_observed_at': submit['observed_at'],
        'submit_receipt_ref': submit['receipt_ref'], 'status_receipt_ref': status['receipt_ref'],
        'result_receipt_ref': result['receipt_ref'], 'job_ref': job, 'remote_id': remote,
        'public_operation_receipt_count': counts['public_search_operations'], 'public_capture_count': len(captures),
        'submission_claim_count': counts['public_search_claims'], 'captures': captures,
        'raw_result_hits': len(hits), 'raw_domains_by_hit': [len(hit['domains']) for hit in hits],
        'published_record_reference_count': len(publication['record_refs']), 'publication_witness_rows': len(pub['publication_rows']),
        'publication_witness_types': dict(Counter(row['record_type'] for row in pub['publication_rows'])),
        'publication_witness_references': [row['record_ref'] for row in pub['publication_rows']],
        'projection_failures': pub['projection_failures'], 'acquired_pages': [1], 'page_count': pub['page_count'],
        'all_reported_pages_acquired': False, 'seed_initial_reference_count': len(seed['initial_known_record_refs']),
        'seed_record_counts_across_tables': seed['verification']['record_counts'],
        'final_record_type_counts': dict(Counter(row['record_type'] for row in records.values())),
        'table_counts': counts, 'seed_source_preservation': seed['verification']['sqlite_reader_bookkeeping'],
        'working_sqlite_reader_bookkeeping': changes,
        'additional_phase_http_model_native_or_scoring_calls_during_publication': 0,
        'complete_raw_replay_capsule_published': False}
    save(ROOT/'VALIDATION.json', summary)
    print(json.dumps({key: summary[key] for key in ('public_operation_receipt_count', 'public_capture_count',
        'submit_replay_exact', 'raw_result_hits', 'raw_domains_by_hit', 'publication_witness_rows',
        'published_record_reference_count', 'seed_initial_reference_count', 'working_sqlite_reader_bookkeeping')}, indent=2))
    print(json.dumps({'safe_working_files': len(safe_files), 'omitted_original_files': len(omissions),
        'derived_transport_files': len(derived)}, indent=2))


if __name__ == '__main__':
    main()
