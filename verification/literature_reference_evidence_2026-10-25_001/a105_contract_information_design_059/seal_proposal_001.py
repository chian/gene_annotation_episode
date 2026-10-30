"""Seal proposal artifacts; read-only checks of declared current dependencies."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def fingerprint(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def main():
    baseline = json.loads((OUT / 'INPUT_BASELINE_001.json').read_bytes())
    for name, row in baseline.items():
        assert fingerprint(ROOT / 'gene_annotation_episode' / name) == row, name
    previous = OUT.parent / 'a105_model_execution_design_057'
    previous_manifest = json.loads((previous / 'DELIVERY_MANIFEST_001.json').read_bytes())
    for name, row in previous_manifest.items():
        assert fingerprint(previous / name) == row, name
    first = json.loads((OUT / 'PROBE_RECEIPT_001.json').read_bytes())
    second = json.loads((OUT / 'PROBE_RECEIPT_002.json').read_bytes())
    assert first['all_schema_graphs_roundtrip_exact']
    assert second['rendered_text_roundtrip_contracts'] == 37
    assert second['synthetic_edge_case_roundtrip_exact']
    receipt = {'status': 'sealed_proposal_only_pending_root_review',
        'proposal': fingerprint(OUT / 'PROPOSAL_001.md'), 'owned_directory_only': True,
        'dependencies_exact_at_delivery': len(baseline), '057_manifest_entries_verified': len(previous_manifest),
        'probe001_exit_code': 0, 'probe002_exit_code': 0, 'rendered_actual_contracts_roundtrip_exact': 37,
        'scientific_sources': 0, 'model_calls': 0, 'completed_actions': 0, 'controller_observations': 0,
        'production_or_test_edits': False, 'implementation_release_presumed': False,
        'capability_narrowing_or_experiment_router': False,
        'limitations': ['No runtime/decoder/compiler/pending-exchange/C4 integration installed',
            'No configured-provider acceptance or model extraction', 'No full A105/goal completion']}
    save('DELIVERY_RECEIPT_001.json', receipt)
    files = {str(path.relative_to(OUT)): fingerprint(path) for path in sorted(OUT.rglob('*'))
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc'}
    save('MANIFEST_001.json', files)
    print(json.dumps({'status': receipt['status'], 'artifacts': len(files),
        'manifest_sha256': fingerprint(OUT / 'MANIFEST_001.json')['sha256'],
        'proposal_sha256': receipt['proposal']['sha256'], 'unchanged_dependencies': len(baseline)}))


if __name__ == '__main__':
    main()
