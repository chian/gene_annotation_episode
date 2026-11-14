"""Capture actual A106 source results, then reopen unchanged across relocation.

These retained fixtures execute genuine own-axis producers. Controlled text and
pixels remain engineered examples; the reported-curve fixture uses its original
retained workbook and source qualification. No historical metadata is invented.
"""
import argparse
from copy import deepcopy
import hashlib
from importlib import import_module
import json
from pathlib import Path
import traceback

AXIS = 'gene_annotation_episode.episodic_workflow.root.a106'


def science(name):
    """Resolve the actual declared source owner before or after its exact move."""
    from ..literature_implementation_sources import source_file
    from .. import literature_implementation_sources
    axis = Path(literature_implementation_sources.__file__).parent
    path = source_file(name+'.py')
    relative = path.relative_to(axis)
    assert relative in (Path(name+'.py'), Path('library')/(name+'.py'))
    return import_module(AXIS+'.'+'.'.join(relative.with_suffix('').parts))


def _write_capture(directory, rows, kind):
    content = json.dumps(rows, sort_keys=True, allow_nan=False).encode()
    (directory/'original_results.json').write_bytes(content)
    (directory/'original_results.sha256').write_text(hashlib.sha256(content).hexdigest()+'\n')
    print(json.dumps({'kind': kind, 'captured_records': len(rows),
        'immutable_results_sha256': hashlib.sha256(content).hexdigest(),
        'scope': 'Actual prechange controlled capture, not a historical release Store or full workflow.'}))


def _failed_capture(directory, kind, rows):
    # Preserve a failed live gate as evidence. Never stamp a partial attempt as a
    # completed capture or patch source pins to make a producer run.
    (directory/'capture_failure.json').write_text(json.dumps({'kind': kind,
        'completed_records': rows, 'traceback': traceback.format_exc(),
        'capture_complete': False}, indent=2, allow_nan=False)+'\n')


def capture_controlled(directory):
    from .controlled_v2_fixtures import Fixture as V2Fixture
    from .controlled_v3_fixtures import Fixture as V3Fixture
    from .controlled_storage_fixtures import native_case
    directory.mkdir(parents=True, exist_ok=False)
    rows = []
    try:
        # Original case0 is text; case6 carries real constructed image pixels.
        for case_index in (0, 6):
            for version, fixture_class in ((2, V2Fixture), (3, V3Fixture)):
                fixture = fixture_class(case_index)
                module = science(f'literature_controlled_response_v{version}_inputs')
                result = getattr(module, f'read_controlled_response_v{version}_inputs')(
                    fixture.args, read_source=fixture.source)
                original = deepcopy(result)
                assert getattr(module, f'validate_controlled_response_v{version}_extraction')(
                    fixture.args, result) == result == original
                rows.append({'kind': 'extraction', 'version': version, 'case_index': case_index,
                    'arguments': fixture.args, 'result': result})
            store, context, arguments, _ = native_case(directory/f'case_{case_index}_store', index=case_index)
            try:
                repository = science('literature_controlled_response_storage').LiteratureControlledResponseRepository(
                    store, context.run_id, evidence_origin='synthetic_fixture')
                outcome = repository.populate_v3(context, arguments, 'actual-a106-before-relocation')
                saved = repository.read(outcome['result']['sheet_ref'])
                rows.append({'kind': 'controlled_store', 'case_index': case_index, 'run_id': context.run_id,
                    'outcome': outcome, 'saved': saved})
            finally:
                store.close()
    except BaseException:
        _failed_capture(directory, 'controlled', rows)
        raise
    _write_capture(directory, rows, 'controlled')


def capture_rate(directory):
    from .reported_curve_fixtures import setup
    directory.mkdir(parents=True, exist_ok=False)
    rows = []
    try:
        store, context, arguments, *_ = setup(directory/'rate_store')
        try:
            repository = science('literature_rate_observation_storage').LiteratureReportedCurveRepository(store, context.run_id)
            outcome = repository.populate(context, arguments, 'actual-a106-before-roster-relocation')
            saved = repository.read(outcome['result']['sheet_ref'])
            rows.append({'kind': 'rate_store', 'run_id': context.run_id, 'outcome': outcome, 'saved': saved})
        finally:
            store.close()
    except BaseException:
        _failed_capture(directory, 'reported_curve', rows)
        raise
    _write_capture(directory, rows, 'reported_curve')


def check(directory):
    from ..state import Store
    content = (directory/'original_results.json').read_bytes()
    assert hashlib.sha256(content).hexdigest() == (directory/'original_results.sha256').read_text().strip()
    rows = json.loads(content)
    verified = []
    for row in rows:
        if row['kind'] == 'extraction':
            version = row['version']
            module = science(f'literature_controlled_response_v{version}_inputs')
            value = deepcopy(row['result'])
            assert getattr(module, f'validate_controlled_response_v{version}_extraction')(
                row['arguments'], value) == value == row['result']
        else:
            controlled = row['kind'] == 'controlled_store'
            assert controlled or row['kind'] == 'rate_store'
            path = directory/(f"case_{row['case_index']}_store" if controlled else 'rate_store')
            with Store(path) as store:
                if controlled:
                    repository = science('literature_controlled_response_storage').LiteratureControlledResponseRepository(
                        store, row['run_id'], evidence_origin='synthetic_fixture')
                else:
                    repository = science('literature_rate_observation_storage').LiteratureReportedCurveRepository(store, row['run_id'])
                reference = row['outcome']['result']['sheet_ref']
                record = store.get(reference)
                allowed = {record['artifact_ref'], record['request_ref']}
                original_get = store.get_artifact
                def retained_only(ref):
                    assert ref in allowed, 'Saved reopening must not reacquire scientific source bytes'
                    return original_get(ref)
                store.get_artifact = retained_only
                store.db.execute('PRAGMA query_only=ON')
                changes = store.db.total_changes
                assert repository.read(reference) == row['saved']
                options = {'components': row['outcome']['result']['component_keys']} if controlled else {}
                assert repository.project_cells([reference], permitted_record_refs=[reference], **options) == row['outcome']['result']['cells']
                assert store.db.total_changes == changes
        verified.append({key: row[key] for key in ('kind', 'case_index', 'version') if key in row})
    assert (directory/'original_results.json').read_bytes() == content
    print(json.dumps({'verified': verified, 'saved_results_unmodified': True,
        'scientific_source_reacquisition': False, 'database_writes_during_reopen': False}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('capture-controlled', 'capture-rate', 'check'))
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    assert args.directory.resolve().is_relative_to((Path.cwd()/'runs').resolve())
    {'capture-controlled': capture_controlled, 'capture-rate': capture_rate, 'check': check}[args.operation](args.directory)


if __name__ == '__main__':
    main()
