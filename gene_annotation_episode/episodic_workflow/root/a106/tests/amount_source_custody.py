"""Actual transitional A106 amount capture, preserving original saved metadata.

This characterizes the current implementation before historical-label repair.
It does not relabel this record as an original release or authorize new labels.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import traceback
from .scientific_source_custody import science


def capture(directory):
    from .amount_source_fixtures import setup
    from ..literature_implementation_sources import source_file
    directory.mkdir(parents=True, exist_ok=False)
    source_manifest = []
    for name in ('literature_amount_inputs.py', 'literature_amount_calculations.py',
                 'literature_amount_storage.py', 'literature_rate_native_inputs.py',
                 'literature_partner_source_fields.py'):
        source = source_file(name)
        data = source.read_bytes()
        target = directory/'actual_source_before'/name
        target.parent.mkdir(exist_ok=True); target.write_bytes(data)
        source_manifest.append({'name': name, 'actual_path': str(source),
                                'sha256': hashlib.sha256(data).hexdigest()})
    (directory/'source_manifest.json').write_text(json.dumps(source_manifest, indent=2)+'\n')
    try:
        store, context, arguments = setup(directory/'amount_store')
        try:
            repository = science('literature_amount_storage').LiteratureAmountRepository(store, context.run_id)
            outcome = repository.populate(context, arguments, 'actual-before-label-repair')
            assert outcome['status'] == 'completed'
            reference = outcome['result']['sheet_ref']
            saved = repository.read(reference)
            components = ['amount_ratio', 'conditional_mass_denominator_factor']
            rows = repository.project_cells([reference], permitted_record_refs=outcome['record_refs'], components=components)
            # Original fixture science/qualification, not a manufactured finding.
            assert [row['value'] for row in rows] == [5/7, 1.4]
            assert rows[0]['comparison_kind'] == 'stock_target_mass_estimate_over_total_mass_estimate'
            assert rows[0]['numerator']['amount_role'] == 'target_mass_estimate'
            assert rows[0]['denominator']['amount_role'] == 'total_protein_mass_estimate'
            assert rows[0]['variance_status'] == 'unknown'
            assert all(row['mass_factor_applied_to_rate'] is False for row in rows)
            assert len(saved['sheet']['cells']) == 12
            assert not store.list('observation') and not store.list('assessment')
            inputs = science('literature_amount_inputs')
            dependency = deepcopy(saved['extraction']['lexical_dependency'])
            assert dependency == inputs.LEXICAL_DEPENDENCY
            record = {'run_id': context.run_id, 'outcome': outcome, 'saved': saved,
                'components': components, 'projected': rows, 'observed_lexical_dependency': dependency,
                'current_release027_declaration': deepcopy(inputs._RELEASED027_LEXICAL_DEPENDENCY),
                'classification': 'Actual current pre-repair producer capture; not a genuine original-release Store.'}
        finally:
            store.close()
    except BaseException:
        (directory/'capture_failure.json').write_text(json.dumps({'capture_complete': False,
            'traceback': traceback.format_exc(), 'source_manifest': source_manifest}, indent=2)+'\n')
        raise
    raw = json.dumps(record, sort_keys=True, allow_nan=False).encode()
    (directory/'original_results.json').write_bytes(raw)
    (directory/'original_results.sha256').write_text(hashlib.sha256(raw).hexdigest()+'\n')
    print(json.dumps({'actual_amount_stores': 1, 'immutable_results_sha256': hashlib.sha256(raw).hexdigest(),
        'observed_lexical_dependency': dependency, 'classification': record['classification']}))


def check(directory):
    from ..state import Store
    raw = (directory/'original_results.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (directory/'original_results.sha256').read_text().strip()
    record = json.loads(raw)
    with Store(directory/'amount_store') as store:
        repository = science('literature_amount_storage').LiteratureAmountRepository(store, record['run_id'])
        reference = record['outcome']['result']['sheet_ref']
        source = store.get(reference)
        allowed = {source['artifact_ref'], source['request_ref']}
        get = store.get_artifact
        def retained_only(ref):
            assert ref in allowed, 'Amount cold read must not reacquire scientific source bytes'
            return get(ref)
        store.get_artifact = retained_only
        store.db.execute('PRAGMA query_only=ON')
        changes = store.db.total_changes
        saved = repository.read(reference)
        assert saved == record['saved']
        assert saved['extraction']['lexical_dependency'] == record['observed_lexical_dependency']
        assert repository.project_cells([reference], permitted_record_refs=record['outcome']['record_refs'],
            components=record['components']) == record['projected']
        assert store.db.total_changes == changes
    assert (directory/'original_results.json').read_bytes() == raw
    print(json.dumps({'actual_amount_store_reopened': True, 'original_payload_and_labels_unchanged': True,
        'source_reacquisition': False, 'database_writes_during_read': False,
        'classification': record['classification']}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('capture', 'check'))
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    assert args.directory.resolve().is_relative_to((Path.cwd()/'runs').resolve())
    (capture if args.operation == 'capture' else check)(args.directory)


if __name__ == '__main__':
    main()
