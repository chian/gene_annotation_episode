"""Authenticate the first-stage count implementation, not unfinished rendering."""
import ast
import hashlib
import json
from pathlib import Path
import runpy
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
OWNER = OUT.parent / 'a105_source_count_words_055'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def functions(path):
    return {node.name: ast.dump(node) for node in ast.parse(path.read_text()).body if isinstance(node, ast.FunctionDef)}


def main():
    artifacts = load(OWNER / 'ARTIFACT_MANIFEST_008.json')
    for name, row in artifacts.items():
        path = OWNER / name
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], name
    owned = load(OWNER / 'STAGE_008_MANIFEST.json')['owned_files']
    reconstructed = OUT / 'reconstructed_008'
    reconstructed.mkdir(exist_ok=False)
    for name, row in owned.items():
        assert (ROOT / name).stat().st_size == row['bytes']
        assert digest(ROOT / name) == row['sha256'] == digest(OWNER / 'snapshot_008' / name)
        if row['baseline_sha256'] is not None:
            baseline = OWNER / 'baseline_001' / name
            assert digest(baseline) == row['baseline_sha256']
            target = reconstructed / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(baseline.read_bytes())
    patch = subprocess.run(['patch', '-p1', '--batch', '-i', str(OWNER / 'STAGE_008.patch')],
        cwd=reconstructed, capture_output=True, text=True)
    assert patch.returncode == 0, patch.stdout + patch.stderr
    assert {p.relative_to(reconstructed).as_posix() for p in reconstructed.rglob('*') if p.is_file()} == set(owned)
    for name, row in owned.items():
        assert digest(reconstructed / name) == row['sha256']
    storage = 'gene_annotation_episode/literature_kinetic_storage.py'
    assert functions(OWNER / 'baseline_001' / storage)['_witness_label'] == functions(reconstructed / storage)['_witness_label']
    old_inputs = functions(OWNER / 'baseline_001/gene_annotation_episode/literature_kinetic_inputs.py')
    new_inputs = functions(reconstructed / 'gene_annotation_episode/literature_kinetic_inputs.py')
    unchanged = [name for name in old_inputs if name not in ('kinetic_arguments_schema', '_uncertainty')]
    assert all(new_inputs[name] == old_inputs[name] for name in unchanged)
    # Execute the fully inspected synthetic comparison into new parent-owned
    # output, never into the owner's immutable generation.
    script = (OWNER / 'verify_numeric_preservation_008.py').read_text()
    needle = 'OUT / "baseline_001/gene_annotation_episode/literature_kinetic_inputs.py"'
    assert script.count(needle) == 1
    script = script.replace(needle, 'Path(' + repr(str(OWNER / 'baseline_001/gene_annotation_episode/literature_kinetic_inputs.py')) + ')')
    copy = OUT / 'verify_numeric_preservation_008.py'
    with copy.open('x') as stream:
        stream.write(script)
    before = {name: digest(ROOT / name) for name in owned}
    runpy.run_path(str(copy), run_name='__main__')
    assert load(OUT / 'NUMERIC_PRESERVATION_008.json') == load(OWNER / 'NUMERIC_PRESERVATION_008.json')
    assert {name: digest(ROOT / name) for name in owned} == before
    receipt = {'passed': True, 'artifact_entries_verified': len(artifacts), 'owned_files_verified_and_reconstructed': len(owned),
        'unchanged_old_input_functions': len(unchanged), 'accepted054_display_helper_AST_exact': True,
        'canonical_and_full045_comparisons_reproduced': 33,
        'source_generation_unchanged_during_numeric_audit': before,
        'stage_manifest_sha256': digest(OWNER / 'STAGE_008_MANIFEST.json'),
        'artifact_manifest_sha256': digest(OWNER / 'ARTIFACT_MANIFEST_008.json'),
        'native_renderer_and_final_connected_verification_complete': False,
        'scope': 'Frozen008 reader/validator/storage contract and numerical preservation only; not A105 or model-backed completion'}
    with (OUT / 'RECEIPT_008.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'source_generation_unchanged_during_numeric_audit'}))


if __name__ == '__main__':
    main()
