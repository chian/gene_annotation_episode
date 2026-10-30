"""Describe the exact production delta without applying it."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = HERE / 'candidate_003'
SHARED = {
    'gene_annotation_episode/api_service_execution.py',
    'gene_annotation_episode/bvbrc_appservice_adapters.py',
    'gene_annotation_episode/bvbrc_appservice_host.py',
    'gene_annotation_episode/bvbrc_appservice_publication.py',
    'gene_annotation_episode/execution_episodes.py',
    'pyproject.toml',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


if __name__ == '__main__':
    manifest = json.loads((HERE / 'combined_source_before_003.json').read_bytes())
    assert len(manifest) == 1176
    rows = []
    shared_found = set()
    for relative, expected in sorted(manifest.items()):
        source = CANDIDATE / relative
        raw = source.read_bytes()
        assert sha(raw) == expected, relative
        path = Path(relative)
        owned_addition = (
            (path.parent == Path('gene_annotation_episode') and path.name.startswith('bvbrc_fastqutils_'))
            or (path.parent == Path('tests') and path.name.startswith('test_bvbrc_fastqutils_'))
            or (path.is_relative_to('tests/fixtures') and len(path.parts) > 2
                and path.parts[2].startswith('bvbrc_fastqutils')))
        if relative not in SHARED and not owned_addition:
            continue
        destination = ROOT / relative
        before = sha(destination.read_bytes()) if destination.exists() else None
        if relative in SHARED:
            assert before is not None and before != expected, relative
            shared_found.add(relative)
        else:
            assert before in (None, expected), ('unowned_existing_content', relative)
        if before != expected:
            rows.append(dict(path=relative, before_sha256=before,
                after_sha256=expected, bytes=len(raw),
                responsibility='shared_integration' if relative in SHARED else 'new_fastqutils'))
    assert shared_found == SHARED
    modules = [r for r in rows if Path(r['path']).parent == Path('gene_annotation_episode')
               and r['before_sha256'] is None]
    tests = [r for r in rows if Path(r['path']).parent == Path('tests')]
    assert len(modules) == 38 and len(tests) == 20
    record = dict(status='unapplied_exact_application_plan',
        source_manifest_sha256=sha((HERE / 'combined_source_before_003.json').read_bytes()),
        shared_existing_paths=sorted(SHARED), new_scientific_modules_and_assets=len(modules),
        new_test_modules=len(tests), changed_paths=len(rows), files=rows,
        consumer_inspection=dict(
            api_service_execution=['__init__','facts','credit_view','_completion',
                'completion_for_action','verify_completion','resolve'],
            bvbrc_appservice_host=['facts','completion','resolve'],
            execution_episodes=['resource_tool_contracts','received_report_facts',
                'resolve_received_reference','validate_received_report','_appservice_sources',
                'received_form_references','resolve'],
            earlier_complete_file_reads=['bvbrc_appservice_adapters.py',
                'bvbrc_appservice_publication.py','bvbrc_fastqutils_returns.py']),
        boundary_meaning='Selected AppService registration, actual acquired-byte provider, '
            'saved publication validation, practical requested-output completion, '
            'resource child tool information and both received-result boundaries.',
        limitations='This is an inspected delta, not an applied or tested production change. '
            '217 owns combined component/package evidence;218 owns new SAMstat episode proof. '
            'Revalidate every before/after hash at application; never overwrite concurrent edits.',
        production_changed=False, method_loop_changed=False,
        annotation_score_changed=False, historical_records_changed=False)
    with (HERE / 'APPLICATION_PLAN_001.json').open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({k:v for k,v in record.items() if k not in ('files','consumer_inspection')},sort_keys=True))
