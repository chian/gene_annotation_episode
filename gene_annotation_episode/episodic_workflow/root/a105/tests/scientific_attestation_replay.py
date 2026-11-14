"""Capture/reopen real controlled-source results across an implementation relocation.

Disposable states belong beneath the caller's runs directory. The reusable
producer and replay checks remain here with their original required fixtures.
This helper does not relabel any saved fingerprint, result or operation.
"""
import argparse
from copy import deepcopy
import hashlib
from importlib import import_module
import json
from pathlib import Path

AXIS = 'gene_annotation_episode.episodic_workflow.root.a105'
PILOT = AXIS + '.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination'


def science(owner, name):
    prefix = PILOT if owner == 'pilot' else AXIS
    locator = import_module(prefix + ('.implementation_sources' if owner == 'pilot' else '.literature_implementation_sources')).source_file
    return import_module('.'.join(locator(name + '.py').relative_to(Path.cwd()).with_suffix('').parts))


def capture(directory, case_index=0):
    from .test_literature_controlled_response_v2_inputs import Fixture as V2Fixture
    from .test_literature_controlled_response_v3_inputs import Fixture as V3Fixture
    from .test_literature_controlled_response_storage_v3 import native_case
    directory.mkdir(parents=True, exist_ok=False)
    rows = []
    for owner in ('axis', 'pilot'):
        for version, fixture_class in ((2, V2Fixture), (3, V3Fixture)):
            fixture = fixture_class(case_index)
            module = science(owner, f'literature_controlled_response_v{version}_inputs')
            result = getattr(module, f'read_controlled_response_v{version}_inputs')(fixture.args, read_source=fixture.source)
            before = deepcopy(result)
            assert getattr(module, f'validate_controlled_response_v{version}_extraction')(fixture.args, result) == result == before
            rows.append({'kind': 'extraction', 'owner': owner, 'version': version, 'case_index': case_index, 'arguments': fixture.args, 'result': result})
        store, context, args, _ = native_case(directory / (owner + '_store'), index=case_index)
        try:
            module = science(owner, 'literature_controlled_response_storage')
            repo = module.LiteratureControlledResponseRepository(store, context.run_id, evidence_origin='synthetic_fixture')
            outcome = repo.populate_v3(context, args, 'actual-before-relocation')
            saved = repo.read(outcome['result']['sheet_ref'])
            rows.append({'kind': 'saved_store', 'owner': owner, 'case_index': case_index, 'run_id': context.run_id, 'outcome': outcome, 'saved': saved})
        finally:
            store.close()
    content = json.dumps(rows, sort_keys=True, allow_nan=False).encode()
    (directory / 'original_results.json').write_bytes(content)
    (directory / 'original_results.sha256').write_text(hashlib.sha256(content).hexdigest() + '\n')
    print(json.dumps({'captured_extractions': 4, 'actual_saved_stores': 2, 'immutable_results_sha256': hashlib.sha256(content).hexdigest()}))


def check(directory):
    from ..state import Store
    content = (directory / 'original_results.json').read_bytes()
    assert hashlib.sha256(content).hexdigest() == (directory / 'original_results.sha256').read_text().strip()
    rows = json.loads(content)
    verified = []
    for row in rows:
        if row['kind'] == 'extraction':
            version = row['version']
            module = science(row['owner'], f'literature_controlled_response_v{version}_inputs')
            result = deepcopy(row['result'])
            assert getattr(module, f'validate_controlled_response_v{version}_extraction')(row['arguments'], result) == result == row['result']
        else:
            with Store(directory / (row['owner'] + '_store')) as store:
                module = science(row['owner'], 'literature_controlled_response_storage')
                repo = module.LiteratureControlledResponseRepository(store, row['run_id'], evidence_origin='synthetic_fixture')
                ref = row['outcome']['result']['sheet_ref']
                record = store.get(ref)
                allowed = {record['artifact_ref'], record['request_ref']}
                original_get = store.get_artifact
                def retained_only(reference):
                    assert reference in allowed, 'Saved reopening must not reacquire scientific source bytes'
                    return original_get(reference)
                store.get_artifact = retained_only
                before = store.db.total_changes
                assert repo.read(ref) == row['saved']
                assert repo.project_cells([ref], permitted_record_refs=[ref], components=row['outcome']['result']['component_keys']) == row['outcome']['result']['cells']
                assert store.db.total_changes == before
        verified.append({'owner': row['owner'], 'kind': row['kind'], 'version': row.get('version', 3)})
    assert (directory / 'original_results.json').read_bytes() == content
    print(json.dumps({'verified': verified, 'saved_payloads_operations_and_hashes_unchanged': True}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('capture', 'check'))
    parser.add_argument('directory', type=Path)
    parser.add_argument('--case-index', type=int, default=0)
    args = parser.parse_args()
    assert args.directory.resolve().is_relative_to((Path.cwd() / 'runs').resolve())
    if args.operation == 'capture':
        capture(args.directory, args.case_index)
    else:
        check(args.directory)


if __name__ == '__main__':
    main()
