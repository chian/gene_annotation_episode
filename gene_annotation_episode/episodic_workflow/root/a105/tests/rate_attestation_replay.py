"""Actual retained reported-curve sheets across receipt-roster relocation."""
import argparse
import hashlib
import json
from pathlib import Path
from .scientific_attestation_replay import science


def capture(directory):
    from .test_literature_reported_curve_binding_231 import setup
    directory.mkdir(parents=True, exist_ok=False)
    rows = []
    for owner in ('axis', 'pilot'):
        store, context, arguments, *_ = setup(directory / (owner + '_store'))
        try:
            module = science(owner, 'literature_rate_observation_storage')
            repository = module.LiteratureReportedCurveRepository(store, context.run_id)
            outcome = repository.populate(context, arguments, 'actual-before-roster-relocation')
            saved = repository.read(outcome['result']['sheet_ref'])
            rows.append({'owner': owner, 'run_id': context.run_id, 'outcome': outcome, 'saved': saved})
        finally:
            store.close()
    raw = json.dumps(rows, sort_keys=True, allow_nan=False).encode()
    (directory / 'original_results.json').write_bytes(raw)
    (directory / 'original_results.sha256').write_text(hashlib.sha256(raw).hexdigest() + '\n')
    print(json.dumps({'actual_saved_stores': len(rows), 'immutable_results_sha256': hashlib.sha256(raw).hexdigest()}))


def check(directory):
    from ..state import Store
    raw = (directory / 'original_results.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (directory / 'original_results.sha256').read_text().strip()
    for row in json.loads(raw):
        with Store(directory / (row['owner'] + '_store')) as store:
            module = science(row['owner'], 'literature_rate_observation_storage')
            repository = module.LiteratureReportedCurveRepository(store, row['run_id'])
            ref = row['outcome']['result']['sheet_ref']
            record = store.get(ref)
            allowed = {record['artifact_ref'], record['request_ref']}
            original_get = store.get_artifact
            def retained_only(reference):
                assert reference in allowed, 'No workbook/source reread during saved reopening'
                return original_get(reference)
            store.get_artifact = retained_only
            before = store.db.total_changes
            assert repository.read(ref) == row['saved']
            assert repository.project_cells([ref], permitted_record_refs=[ref]) == row['outcome']['result']['cells']
            assert store.db.total_changes == before
    assert (directory / 'original_results.json').read_bytes() == raw
    print(json.dumps({'verified_actual_stores': 2, 'unchanged_results_and_source_rosters': True}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('capture', 'check'))
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    assert args.directory.resolve().is_relative_to((Path.cwd() / 'runs').resolve())
    (capture if args.operation == 'capture' else check)(args.directory)


if __name__ == '__main__':
    main()
