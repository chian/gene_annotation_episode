"""Copy checkable actual saved examples; perform no scientific calculations."""
from pathlib import Path
import hashlib
import json
import sqlite3
import sys


def main():
    check = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    check_receipt = json.loads((check / 'receipt.json').read_bytes())
    if not check_receipt['sources_unchanged']:
        raise ValueError('unchanged_source_check_required')
    examples = []
    for case_path in sorted(check.rglob('CASE.json')):
        case = json.loads(case_path.read_bytes())
        state = case_path.parent / 'state'
        db = sqlite3.connect('file:' + str(state / 'state.sqlite3') + '?mode=ro', uri=True)
        def artifact(reference, *, decode=False):
            sha, size = db.execute('SELECT sha256,size FROM artifacts WHERE id=?', (reference,)).fetchone()
            path = state / 'artifacts' / sha[:2] / sha
            raw = path.read_bytes()
            if len(raw) != size or hashlib.sha256(raw).hexdigest() != sha:
                raise ValueError('saved_example_digest_mismatch')
            return json.loads(raw) if decode else {'reference': reference, 'path': str(path), 'sha256': sha, 'size_bytes': size}
        saved = []
        for outcome, returned in zip(case['outcomes'], case['returned'], strict=True):
            body = outcome['result']
            bundle = artifact(body['capture']['bundle_artifact_ref'], decode=True)
            prepared = body['prepared']
            saved.append({'original_result_receipt': body,
                'native_bundle': bundle, 'native_artifact_locators': [
                    {'role': row['role'], **artifact(row['artifact_ref'])} for row in body['capture']['artifacts']],
                'sheet': artifact(prepared['sheet_artifact_ref'], decode=True),
                'components': artifact(prepared['components_artifact_ref'], decode=True),
                'requested_return': returned,
                'worker_receipt': artifact(prepared['worker_receipt_artifact_ref'], decode=True)})
        examples.append({'case_path': str(case_path), 'operation': case['operation'], 'mode': case['mode'],
            'verification_scope': case['scope'], 'native_plan': case['native_plan'],
            'requested_forms': {'results': case['results_form'], 'scientific_parent': case['science_form']},
            'results': saved, 'forwarded': case['forwarded'], 'closed_histories': case['histories'],
            'earlier_empty_source_zero_expectation_fixture': case['earlier_empty_source_zero_expectation_fixture'],
            'failed_local_closure_horizon_fixture': case['failed_local_closure_horizon_fixture']})
        db.close()
    if not examples:
        raise ValueError('actual_workflow_examples_required')
    value = {'schema': 'rna_integration_actual_examples_v1', 'check_directory': str(check),
        'complete_check_output': (check / 'stdout.txt').read_text(),
        'check_receipt': check_receipt, 'examples': examples}
    output.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'output': str(output), 'case_count': len(examples),
        'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
