"""Authenticate the scoped publication fix and reconstruct its delivered patch."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
OWNER = OUT.parent / 'a105_kinetic_witness_publication_054'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((OWNER / 'MANIFEST_001.json').read_bytes())
    for name, row in manifest['artifacts'].items():
        path = OWNER / name
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], name
    for section in ('existing_changed_files', 'new_test_files', 'unchanged_protected_dependencies'):
        for name, expected in manifest[section].items():
            assert digest(ROOT / name) == expected, name
    baseline = OWNER / 'baseline_001/literature_kinetic_storage.py'
    old047 = OUT.parent / 'a105_kinetic_integration_047/snapshot_006/gene_annotation_episode/literature_kinetic_storage.py'
    old051 = OUT.parent / 'a105_kinetic_primary_example_051/controlled_005/pin/gene_annotation_episode/literature_kinetic_storage.py'
    assert baseline.read_bytes() == old047.read_bytes() == old051.read_bytes()
    reconstructed = OUT / 'reconstructed_001'
    reconstructed.mkdir(exist_ok=False)
    target = reconstructed / 'gene_annotation_episode/literature_kinetic_storage.py'
    target.parent.mkdir()
    target.write_bytes(baseline.read_bytes())
    patched = subprocess.run(['patch', '-p1', '--batch', '--forward', '-i', str(OWNER / 'IMPLEMENTATION_001.patch')],
        cwd=reconstructed, capture_output=True, text=True)
    assert patched.returncode == 0, patched.stdout + patched.stderr
    changed = {**manifest['existing_changed_files'], **manifest['new_test_files']}
    assert len(changed) == 2
    assert {p.relative_to(reconstructed).as_posix() for p in reconstructed.rglob('*') if p.is_file()} == set(changed)
    for name, expected in changed.items():
        assert digest(reconstructed / name) == expected == digest(OWNER / 'snapshot_001' / name), name
    old = ast.parse(baseline.read_text())
    new = ast.parse(target.read_text())
    helper, = [n for n in new.body if isinstance(n, ast.FunctionDef) and n.name == '_witness_label']
    new.body.remove(helper)
    replacements = 0
    class ReversePreview(ast.NodeTransformer):
        def visit_Call(self, node):
            nonlocal replacements
            if isinstance(node.func, ast.Name) and node.func.id == '_witness_label':
                assert len(node.args) == 1 and not node.keywords
                assert ast.unparse(node.args[0]) == "anchor['quote']"
                replacements += 1
                return node.args[0]
            return self.generic_visit(node)
    ReversePreview().visit(new)
    assert replacements == 1 and ast.dump(old) == ast.dump(new)
    dedicated = json.loads((OWNER / 'DEDICATED_TESTS_001.json').read_bytes())
    assert dedicated['exit_code'] == 0
    regression = (OWNER / 'KINETIC_REGRESSION_001.log').read_text()
    assert '293 passed in 67.01s' in regression
    assert [r['passed'] for r in manifest['tests']] == [19, 293]
    receipt = {'passed': True, 'manifest_artifacts': len(manifest['artifacts']), 'patch_files_reconstructed': 2,
        'original047_and051_storage_exact': True, 'unchanged_dependencies': len(manifest['unchanged_protected_dependencies']),
        'production_ast_change': 'one display helper plus one reference.label call; all other AST exact',
        'dedicated_tests': 19, 'kinetic_regressions': 293, 'counts_not_graders_or_independent_experiments': True,
        'manifest_sha256': digest(OWNER / 'MANIFEST_001.json'), 'configured_model_science': False}
    with (OUT / 'DELIVERY_RECEIPT_001.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
