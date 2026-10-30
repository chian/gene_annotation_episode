"""Read-only byte/receipt audit of the separately frozen long-witness generation."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
RUN = OUT / 'controlled_long_001'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def main():
    terminal = load(RUN / 'TERMINAL_RECEIPT.json')
    manifest = load(RUN / 'PIN_MANIFEST.json')
    assert terminal['exit_code'] == 0 and terminal['pin_unchanged']
    assert terminal['pin_manifest_sha256'] == digest(RUN / 'PIN_MANIFEST.json')
    names = set(manifest['files'])
    for name, row in manifest['files'].items():
        path = RUN / 'pin' / name
        assert digest(path) == row['sha256'] and path.stat().st_size == row['bytes'], name
    assert {p.relative_to(RUN / 'pin').as_posix() for p in (RUN / 'pin').rglob('*') if p.is_file()} == names
    for name in ('run_long_witness_002.py', 'launch_long_witness_002.py'):
        assert digest(OUT / name) == digest(RUN / 'pin' / name)
    assert manifest['files']['gene_annotation_episode/literature_kinetic_storage.py']['sha256'] == '599606c6e40f00e587934b0a7fcd1c550b46253974dd5b123cfdde228245759e'
    old = load(RUN / 'PRESERVATION_BEFORE.json')
    for name, expected in old.items():
        assert digest(OUT / name) == expected, name
    assert set(load(OUT / 'FINAL_MANIFEST_001.json')) <= set(old)
    assert load(RUN / 'SOURCE_SELECTIONS.json') == load(OUT / 'controlled_001/SOURCE_SELECTIONS.json')
    verification = load(RUN / 'LONG_WITNESS_VERIFICATION.json')
    assert verification['status'] == 'passed' and verification['forbidden_calls'] == 0
    assert verification['full_sql_unchanged'] and verification['direct_mode_ro_before_any_repository_read']
    assert verification['actual_observations'] == 4 and verification['actual_credit'] == 0.0
    assert [r['original_anchor_characters'] for r in verification['long_anchor_preview_checks']] == [1003, 1472, 1003, 1472]
    assert all(r['preview_label_characters'] <= 512 and r['full_original_anchor_exact']
               and r['full_canonical_context_exact'] for r in verification['long_anchor_preview_checks'])
    receipt = {'status': 'passed', 'execution_pin_files': len(names), 'unmanifested_pin_files': 0,
        'old_manifest_and005_files_preserved': len(old), 'executed_worker_launcher_match_delivery': True,
        'original001_nominations_exact': True, 'accepted054_storage_pinned': True,
        'terminal_exit_code': terminal['exit_code'], 'actual_observations': verification['actual_observations'],
        'actual_credit': verification['actual_credit'], 'configured_model_run': False,
        'scope': 'Byte and terminal-receipt audit; no runtime rerun, scientific conversion or independent biological evidence'}
    with (OUT / 'LONG_DELIVERY_REVIEW_002.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
