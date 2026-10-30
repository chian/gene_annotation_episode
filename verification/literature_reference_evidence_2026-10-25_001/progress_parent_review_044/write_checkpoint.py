"""Seal044 scientific acceptance; active source/information/delivery work stays open."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    prior_path = BASE / 'CHECKPOINT_043_ADDENDUM_001.json'
    prior = json.loads(prior_path.read_bytes())
    for name, expected in prior['files'].items():
        assert digest(ROOT / name) == expected, name
    audit = BASE / 'a105_model_saved_source_audit_060'
    manifest = json.loads((audit / 'MANIFEST_001.json').read_bytes())
    for name, row in manifest['files'].items():
        path = audit / name
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], name
    paths = [prior_path, Path(__file__), BASE / 'PROGRESS_044.md',
             BASE / 'MODEL_SOURCE_PARENT_COMPONENT_REVIEW_060.md',
             BASE / 'model_source_parent_reset_060/read_authority.py',
             BASE / 'model_source_parent_reset_060/READ_RECEIPT.json',
             BASE / 'model_source_parent_review_060/verify_scientific_audit_001.py',
             BASE / 'model_source_parent_review_060/SCIENTIFIC_REVIEW_RECEIPT_001.json',
             BASE / 'parent_launch_030/BOUNDARY_017.json',
             BASE / 'literature_model_run_030/pin_001/SOURCE_MANIFEST.json']
    for name in ('MANIFEST_001.json', 'FINAL_VERIFY_001.json', 'SCIENTIFIC_AUDIT_001.md',
                 'HANDOFF_001.md', 'READ_PROVENANCE_001.md', 'SOURCE_AND_ARITHMETIC_RECEIPT_001.json',
                 'CAPTURE_RECEIPT_001.json', 'IMPLEMENTATION_IDENTITIES_001.json'):
        paths.append(audit / name)
    for name in ('gene_annotation_episode/literature_rate_native_inputs.py',
                 'gene_annotation_episode/literature_rate_calculations.py',
                 'gene_annotation_episode/literature_experimental_contracts.py',
                 'gene_annotation_episode/literature_controlled_response_calculations.py',
                 'tests/test_literature_controlled_response_calculations.py'):
        paths.append(ROOT / name)
    files = {str(path.relative_to(ROOT)): digest(path) for path in sorted(set(paths))}
    output = {'checkpoint': '044', 'goal_complete': False,
              'previous_goal_execution': 'progress', 'current_goal_execution': 'progress',
              'prior043_addendum_frozen_entries_verified': len(prior['files']),
              'source_audit001_frozen_entries_verified': len(manifest['files']),
              'files': files,
              'scope': 'Root primary/packet read, OWN49-chunk reset and source-correct actual030 descriptive numerical contrasts accepted; first received family observed; original typed-delivery proof pending.',
              'active_unsealed_work': ['056 controlled-response text/JSON reader008',
                                       '059 connected opt-in information integration',
                                       '060 original model030 delivery_review_002'],
              'coverage_warning': 'No complete A105 reliability, source-free typed delivery acceptance, whole-modelrun closure, remaining scoped literature axes, routing or W05 claim.'}
    with (BASE / 'CHECKPOINT_044.json').open('x') as stream:
        json.dump(output, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'passed': True, 'prior043_addendum_verified': len(prior['files']),
                      'source_audit001_verified': len(manifest['files']), 'frozen_paths': len(files)}))


if __name__ == '__main__':
    main()
