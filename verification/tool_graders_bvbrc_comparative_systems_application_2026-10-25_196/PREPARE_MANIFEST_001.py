#!/usr/bin/env python3
"""Derive review artifacts from complete source maps; never alter production."""
from collections import Counter
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IMPL = ROOT / 'verification/tool_graders_bvbrc_comparative_systems_implementation_2026-10-25_186'
PROTEOME = ROOT / 'verification/tool_graders_bvbrc_proteome_directional_integration_2026-10-25_182'
CONTRACT = ROOT / 'verification/tool_graders_bvbrc_comparative_systems_contract_2026-10-25_185'
CANDIDATE = IMPL / 'candidate'
AUTHORITY = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(name, data):
    with (HERE / name).open('x') as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def snapshot():
    paths = {CANDIDATE / 'pyproject.toml'}
    for name in ('gene_annotation_episode', 'method_loop', 'tests', 'research', 'verification'):
        paths.update(p for p in (CANDIDATE / name).rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo'))
    assert not any(p.is_symlink() for p in paths)
    return {str(p.relative_to(CANDIDATE)): sha(p) for p in sorted(paths)}


def category(name):
    if name == 'pyproject.toml':
        return 'package_configuration'
    if name.startswith('tests/fixtures/'):
        return 'fixture'
    if name.startswith('tests/'):
        return 'test_module'
    if name.endswith('.json'):
        return 'packaged_schema'
    if name.startswith('gene_annotation_episode/') and name.endswith('.py'):
        return 'runtime_module'
    raise ValueError('unreviewed_delta_category:' + name)


def main():
    baseline = read(IMPL / 'BASELINE_001.json')
    composition = read(IMPL / 'PROTEOME_COMPOSITION_RECEIPT_001.json')
    final = read(IMPL / 'package_verification_002/source_after.json')
    assert len(baseline) == 935 and len(final) == 1045
    assert final == snapshot() == read(IMPL / 'final_workflow_001/source_before.json')
    assert final == read(IMPL / 'package_verification_002/source_before.json')
    assert len(composition['files']) == 25 and composition['all25_exact_source_files_copied']
    before = dict(baseline)
    for row in composition['files']:
        assert baseline.get(row['path']) == row['before_sha256']
        before[row['path']] = row['after_sha256']
    assert len(before) == 952
    assert before == read(PROTEOME / 'FREEZE_001.json')['sources']
    assert sha(PROTEOME / 'FREEZE_001.json') == composition['source_freeze_sha256']
    assert not set(before) - set(final)
    files, patch, shared = [], [], []
    for name in sorted(final):
        if final[name] == before.get(name):
            continue
        source = CANDIDATE / name
        old = PROTEOME / 'candidate' / name
        previous = old.read_bytes() if name in before else b''
        if name in before:
            assert sha(old) == before[name]
        text = source.read_text()
        lines = list(difflib.unified_diff(previous.decode().splitlines(True), text.splitlines(True),
                     fromfile='post182/' + name, tofile='candidate186/' + name))
        patch.extend(lines)
        row = {'path': name, 'change': 'changed' if name in before else 'new',
               'category': category(name), 'before_sha256': before.get(name),
               'candidate_sha256': final[name], 'byte_count': source.stat().st_size}
        files.append(row)
        if name in before:
            shared.append({**row, 'added_lines': sum(s.startswith('+') and not s.startswith('+++') for s in lines),
                           'removed_lines': sum(s.startswith('-') and not s.startswith('---') for s in lines)})
    assert len(files) == 99 and sum(row['change'] == 'new' for row in files) == 93
    assert {r['path'] for r in shared} == {
        'gene_annotation_episode/api_service_execution.py',
        'gene_annotation_episode/bvbrc_appservice_adapters.py',
        'gene_annotation_episode/bvbrc_appservice_host.py',
        'gene_annotation_episode/bvbrc_appservice_publication.py',
        'gene_annotation_episode/execution_episodes.py', 'pyproject.toml'}
    with (HERE / 'DELTA_001.patch').open('x') as stream:
        stream.write(''.join(patch))
    pinned = [AUTHORITY, ROOT / 'AGENTS.md', HERE / 'APPLICATION_CONTRACT_001.md',
              IMPL / 'BASELINE_001.json', IMPL / 'PROTEOME_COMPOSITION_RECEIPT_001.json',
              PROTEOME / 'BASELINE_001.json', PROTEOME / 'FREEZE_001.json',
              PROTEOME / 'FREEZE_INDEPENDENT_001.json', PROTEOME / 'FREEZE_INDEPENDENT_002.json',
              PROTEOME / 'PRODUCTION_REVIEW_001.json', PROTEOME / 'APPLY_001.py',
              PROTEOME / 'PACKAGE_PROBE_001.py',
              PROTEOME / 'package_verification_001/receipt.json',
              PROTEOME / 'package_verification_001/installed_result.json']
    for name in ('REVIEW_CONTRACT_001.md', 'NUMERICAL_SHEET_AND_INTERFACES_001.md',
                 'DATA_POPULATION_HANDOFF_001.md', 'BINDING_AND_WORKLOADS_001.md',
                 'SCHEMA_DECISIONS_001.md', 'HANDOFF_CLOSURE_002.md',
                 'FINAL_MAPPING_AND_PARENT_BOUNDARY_003.md', 'HANDOFF_SCHEMAS_001.json'):
        pinned.append(CONTRACT / name)
    for name in ('IMPLEMENTATION_HANDOFF_001.md', 'DATA_EXTRACTOR_HANDOFF_002.md',
                 'INTEGRATION_BOUNDARY_CLOSURE_003.md', 'REFERENCE_BINDING_CLOSURE_004.md',
                 'PROJECTION_FAILURE_CONTEXT_CLOSURE_005.md',
                 'evidence_n/N_HANDOFF_001.md', 'evidence_c_review/C_REVIEW_HANDOFF_001.md',
                 'evidence_d/HANDOFF_D_001.md', 'evidence_p/P_HANDOFF_003.md', 'evidence_i/I_HANDOFF_001.md',
                 'evidence_n_review/ROOT_REVIEW_001.json', 'evidence_n_review/N_C_AFTER_001.json',
                 'evidence_n_review/N_C_AFTER_001.log', 'evidence_n_review/N_C_AFTER_001.xml',
                 'evidence_d/COMMANDS_AND_RESULTS_001.json', 'evidence_d/SOURCE_HASHES_001.json',
                 'evidence_d/pytest_attempt_005.log', 'evidence_p/P_TERMINAL_RECEIPT_003.json',
                 'evidence_p/P_OWNED_FILE_MANIFEST_003.json', 'evidence_p/P_VERIFICATION_INPUTS_003.json',
                 'evidence_p/pytest_013.log', 'evidence_p/FILLED_PROVIDER_INPUT_003.json',
                 'evidence_p/FILLED_PROVIDER_RESULT_003.json',
                 'evidence_i/FINAL_TERMINAL_001.json', 'evidence_i/FINAL_TERMINAL_002.json',
                 'evidence_i/FINAL_SOURCE_BEFORE_001.json', 'evidence_i/FINAL_SOURCE_AFTER_001.json',
                 'evidence_i/FINAL_SOURCE_BEFORE_002.json', 'evidence_i/FINAL_SOURCE_AFTER_002.json',
                 'evidence_i/I_OWNED_FILE_MANIFEST_001.json', 'evidence_i/SHARED_DELTA_AUDIT_001.json',
                 'evidence_i/PROTEOME_PRESERVATION_001.json', 'evidence_i/LATEST_FAILURE_REASON_001.json',
                 'evidence_i/LATEST_HISTORY_TEST_FIX_003.patch',
                 'evidence_i/pytest_012.log', 'evidence_i/pytest_012.xml',
                 'evidence_i/pytest_013.log', 'evidence_i/pytest_013.xml',
                 'PACKAGE_PROBE_002.py', 'VERIFY_WORKFLOW_001.py', 'VERIFY_PACKAGE_001.py',
                 'VERIFY_PACKAGE_PROBE_002.py', 'package_verification_001/receipt.json',
                 'package_verification_001/source_before.json', 'package_verification_001/source_after.json',
                 'package_verification_001/installed_stderr.log', 'package_verification_001/build.log',
                 'package_verification_002/receipt.json', 'package_verification_002/source_before.json',
                 'package_verification_002/source_after.json', 'package_verification_002/installed_result.json',
                 'final_workflow_001/source_before.json', 'final_workflow_001/command.json'):
        pinned.append(IMPL / name)
    specimen = read(IMPL / 'evidence_p/FILLED_PROVIDER_INPUT_003.json')
    for binding in specimen['byte_files'].values():
        path = (IMPL / 'evidence_p' / binding['path']).resolve()
        assert path.is_relative_to(IMPL / 'evidence_p')
        assert sha(path) == binding['sha256'] and path.stat().st_size == binding['byte_count']
        pinned.append(path)
    wheel, = (IMPL / 'package_verification_001/wheel').glob('*.whl')
    pinned.append(wheel)
    evidence = {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p): sha(p)
                for p in sorted(set(pinned))}
    preservation = []
    for row in composition['files']:
        name = row['path']
        preserved = final[name] == row['after_sha256']
        preservation.append({'path': name, 'proteome_sha256': row['after_sha256'],
            'candidate_sha256': final[name], 'byte_identical': preserved,
            'composition': 'unchanged' if preserved else 'explicit_shared_file_delta'})
    assert sum(row['byte_identical'] for row in preservation) == 21
    manifest = {'version': 'comparative_systems_application_manifest_v1',
        'created_at': datetime.now(timezone.utc).isoformat(), 'production_applied': False,
        'root': str(ROOT), 'candidate': str(CANDIDATE),
        'provider_sha256': '118aae7a8a9470b9a7cb2e0f081853ac6730c98e1710ac9018a312312699b68f',
        'proteome_v1_sha256': '4a38563301a75481c9fc8cfcde77e0a09b9d8e08f3c0562e9635c18692e44a20',
        'proteome_v2_sha256': '7dbdd8cfbc5193d149af6bfd314e0199ff074a1d671a39e1395a785b22b10ce9',
        'baseline_sources': baseline, 'expected_post182_sources': before, 'candidate_sources': final,
        'counts': {'baseline': len(baseline), 'expected_post182': len(before), 'candidate': len(final),
                   'new': 93, 'changed': 6, 'deleted': 0, 'delta': len(files),
                   'categories': dict(sorted(Counter(row['category'] for row in files).items()))},
        'files': files, 'shared_files': shared, 'proteome_composition': preservation,
        'delta_patch_sha256': sha(HERE / 'DELTA_001.patch'), 'pinned_evidence': evidence,
        'future_prerequisites': ['proteome182 successful application and final host terminal success',
                                 'comparative186 final_workflow_001 terminal success'],
        'evidence_limits': ['Controlled native/synthetic inputs and transport, no live service proof',
            'I012 retains 31 passes and one fixture failure; I013 verifies the correction and completion rule',
            'I013 exit_code remains null; final JUnit and vanished original PIDs are the retained terminal evidence',
            'Package001 build passed, installed probe failed; package002 corrected tuple inputs and passed']}
    save('DELTA_MANIFEST_001.json', manifest)
    print(json.dumps({'counts': manifest['counts'], 'manifest_sha256': sha(HERE / 'DELTA_MANIFEST_001.json')}))


if __name__ == '__main__':
    main()
