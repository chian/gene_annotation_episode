"""Index retained E321 evidence without modifying any original test receipt."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).parent


def file_record(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest())


def sources(names):
    return [file_record(ROOT / 'gene_annotation_episode' / (name + '.py')) for name in names]


def main():
    selected = [PACKET / name for name in sys.argv[1:]]
    if not selected:
        raise ValueError('explicit completed check directories are required')
    checks = []
    for path in sorted(PACKET.glob('check_*/receipt.json')):
        receipt = json.loads(path.read_text())
        output = (path.parent / 'stdout.txt').read_text()
        checks.append(dict(receipt=file_record(path), returncode=receipt['returncode'],
            summary=output.strip().splitlines()[-1] if output.strip() else '',
            stdout=file_record(path.parent / 'stdout.txt'),
            stderr=file_record(path.parent / 'stderr.txt')))
    cases = []
    retained_names = {'capture.json', 'preparation.json', 'publication.json',
        'manifest.json', 'request.json', 'inputs.json', 'collection.json',
        'sheets.json', 'calculations.json', 'rows.ndjson', 'row-index.json',
        'metric-definitions.json', 'worker-manifest.json',
        'diagnostics.json', 'native-convergence.json', 'invalid-request.json',
        'invalid-request-diagnostics.json', 'projection-return-union.json',
        'distinct-calculations.json', 'convergence-child-return.json',
        'zero-hits-return.json'}
    for check in selected:
        if json.loads((check / 'receipt.json').read_text())['returncode'] != 0:
            raise ValueError('selected final check must have a successful retained receipt')
        for case in sorted((check / 'tmp').glob('test_*')):
            if not case.is_dir() or case.is_symlink():
                continue
            files = sorted(p for p in case.rglob('*') if p.is_file()
                and not p.is_symlink() and p.name in retained_names)
            publications = []
            for path in files:
                if path.name != 'publication.json':
                    continue
                body = json.loads(path.read_text())
                publications.append(dict(path=str(path.relative_to(ROOT)),
                    complete=body['complete'],
                    acquisition_complete=body['acquisition_complete'],
                    projection_complete=body['projection_complete'],
                    native_execution_successful=body['native_execution_successful'],
                    rows_by_family=body['rows_by_family'], failures=body['failures']))
            cases.append(dict(path=str(case.relative_to(ROOT)),
                retained_output_files=[file_record(p) for p in files],
                store_databases=[file_record(p) for p in sorted(case.rglob('state.sqlite3'))],
                selected_publications=publications))
    evidence = dict(version='native_blast_database_episode_binding_evidence_v1',
        verification_kind='controlled_synthetic_native_and_pbs_fixtures',
        live_hpc_verified=False, native_scientific_executable_run=False,
        resource_policy=dict(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3,
            wall_seconds=None),
        final_checks=[str(p.relative_to(ROOT)) for p in selected],
        owned_production=sources(['native_blast_database_acquisition',
            'native_blast_database_result_publication', 'native_blast_database_results',
            'native_blast_database_returns']),
        shared_integration=sources(['execution_episodes', 'execution_progress',
            'practical_execution_records', 'practical_execution_operations',
            'practical_pbs_operations', 'domain', 'state', 'evidence_geometry',
            'evidence_axis_contracts', 'infernal_result_presentation',
            'blast_result_views', 'alignment_site_native']),
        consumed_dependencies=sources(['native_blast_database_metadata',
            'native_blast_database_result_worker', 'native_blast_database_result_views',
            'native_blast_database_convergence', 'communication']),
        tests=[file_record(ROOT / 'tests' / ('test_' + name + '.py')) for name in
            ['native_blast_database_acquisition', 'native_blast_database_results',
             'native_blast_database_returns', 'native_blast_database_episode_binding']],
        all_retained_checks=checks, retained_cases=cases)
    path = PACKET / 'HANDOFF_EVIDENCE_001.json'
    with path.open('x') as stream:
        json.dump(evidence, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(dict(output=str(path), retained_check_count=len(checks),
        final_case_count=len(cases), bytes=path.stat().st_size)))


if __name__ == '__main__':
    main()
