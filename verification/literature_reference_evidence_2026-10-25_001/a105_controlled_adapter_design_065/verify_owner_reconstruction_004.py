"""Reconstruct inline-generated declarations in a NEW owned output directory.

The two original declaration/check sources are retained verbatim. Only their
top-level O output-directory assignment is replaced in the AST here. No schema,
fixture, expected number, model or production operation is patched. New owner
arithmetic is not executed; these are proposed shapes/hand-constructed outputs.
"""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
output = HERE / 'reconstructed_owner_declarations_004'
output.mkdir()
sources = []
for name in ('build_owner_declarations_003.py', 'build_owner_correction_004.py'):
    path = HERE / name
    raw = path.read_bytes()
    tree = ast.parse(raw, filename=str(path))
    replaced = 0
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'O' for t in node.targets):
            node.value = ast.Call(func=ast.Name(id='Path', ctx=ast.Load()),
                                  args=[ast.Constant(value=str(output))], keywords=[])
            replaced += 1
    assert replaced == 1, (name, replaced)
    ast.fix_missing_locations(tree)
    exec(compile(tree, str(path), 'exec'), {'__name__': '__declaration_reconstruction__'})
    sources.append({'path': name, 'sha256': hashlib.sha256(raw).hexdigest(),
                    'only_change': 'one top-level O output-directory assignment'})
rows = []
for path in sorted(output.iterdir()):
    raw = path.read_bytes()
    assert raw == (HERE / path.name).read_bytes(), path.name
    rows.append({'path': path.name, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
assert len(rows) == 11
receipt = {'sources': sources, 'files_reconstructed_byte_exact': rows,
           'new_owner_calculator_implemented_or_executed': False,
           'scope': 'closed declaration/shape reconstruction only; expected sheet remains HAND-CONSTRUCTED'}
with (HERE / 'RECONSTRUCTION_RECEIPT_004.json').open('x') as stream:
    json.dump(receipt, stream, indent=2, allow_nan=False)
    stream.write('\n')
print(json.dumps({'declaration_sources': len(sources), 'byte_exact_reconstructions': len(rows),
                  'new_owner_arithmetic_run': False}))
