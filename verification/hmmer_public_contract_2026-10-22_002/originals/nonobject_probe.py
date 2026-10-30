"""Local fixture proof only: no network, model, native job or result fetch."""
import asyncio
import hashlib
import json
from pathlib import Path
import sys

checkout = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(checkout))
sys.path.insert(0, str(checkout/'tests'))

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.provider_jobs import HMMER_IDENTITY_VERSION, validate_remote_identity
from test_hmmer_api_operations import JOB, setup


async def main():
    destination = Path(__file__).resolve().parent
    request = {'identity_version': HMMER_IDENTITY_VERSION,
        'algorithm': 'phmmer', 'database': 'swissprot'}
    pure = []
    for payload in (None, [], 'malformed object', 1):
        try:
            validate_remote_identity(payload, request, JOB)
        except Exception as error:
            pure.append({'input': payload, 'exception_type': type(error).__name__, 'detail': str(error)})
    # Present result.stats identities remain checked independently of outer shape.
    identities = []
    for field, bad in [('id', '00000000-0000-4000-8000-000000000001'),
                       ('algo', 'hmmscan'), ('database', 'different_database')]:
        try:
            validate_remote_identity({'status': 'SUCCESS', 'result': {'stats': {field: bad}, 'hits': []}},
                request, JOB, result=True)
        except AcquisitionError as error:
            identities.append({'field': field, 'code': error.code})
    store, client, operations, order = setup(destination/'isolated-nonobject-fixture')
    with store:
        # This is the imported FixtureClient's in-memory reply, never a public POST.
        submitted = await operations.submit_once(order['job_ref'], operation_key='fixture-submit')
        assert submitted['outcome'] == 'completed'
        client.status_body = []
        failures = []
        for attempt in range(2):
            try:
                await operations.status_once(order['job_ref'], operation_key='fixture-array-status')
            except Exception as error:
                failures.append({'attempt': attempt+1, 'exception_type': type(error).__name__, 'detail': str(error)})
        capsule = operations._capsule_path('fixture-array-status')
        entity = (capsule/'response.entity').read_bytes()
        observed = operations.inspect(order['job_ref'])
        rows = [row[0] for row in store.db.execute(
            'SELECT operation_key FROM public_search_operations ORDER BY rowid')]
        result = {'meaning': 'Actual unchanged selected status operation on an explicit in-memory fixture; not external service data.',
            'pure_validate_remote_identity_nonobjects': pure,
            'present_result_stats_identity_checks': identities,
            'status_attempts': failures, 'fixture_calls': client.calls,
            'fixture_submit_calls': len([call for call in client.calls if call[0] == 'submit']),
            'fixture_status_calls': len([call for call in client.calls if call[0] == 'status']),
            'fixture_result_calls': len([call for call in client.calls if call[0] == 'result']),
            'network_requests': 0, 'saved_operation_keys': rows,
            'captured_entity': entity.decode(), 'captured_entity_sha256': hashlib.sha256(entity).hexdigest(),
            'capture_retained': capsule.is_dir(), 'transaction_still_open': store.db.in_transaction,
            'authoritative_state': observed['state'], 'remote_id': observed['remote_id']}
        assert len(failures) == 2 and all(row['exception_type'] == 'AttributeError' for row in failures)
        assert result['fixture_status_calls'] == 1 and result['fixture_result_calls'] == 0
        assert rows == ['fixture-submit'] and not store.db.in_transaction
        assert result['authoritative_state'] == 'accepted' and entity == b'[]'
        (destination/'nonobject-probe-result.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result, indent=2))


asyncio.run(main())
