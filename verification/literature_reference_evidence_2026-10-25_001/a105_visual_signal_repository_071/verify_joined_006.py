"""Execute only explicit synthetic engineering fixtures from the coherent pin."""
from __future__ import annotations
import ast
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

pin = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).resolve()
sys.path[:0] = [str(pin / 'tests'), str(pin)]
from test_literature_ratio_source_storage import native_case, owned, repository
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.literature_ratio_source_storage import _calculator_implementation_descriptor

store, context, selection, native = native_case(output / 'joined_fixture_006', known=True)
repo = repository(store, context)
outcome = repo.populate(context, selection, 'selected-joined-fixture')
reference = outcome['result']['sheet_ref']
saved = repo.read(reference)
calculation = json.loads(store.get_artifact(saved['calculation_artifact_ref']))
implementation_descriptor = _calculator_implementation_descriptor()
assert calculation['calculator_implementation_sha256'] == hashlib.sha256(canonical(implementation_descriptor).encode()).hexdigest()
owner = owned(context, outcome)
cells = repo.fact_cells(owner, [reference], components=['reported_ratio'])
parent = replace(owner, episode_id='fixture-parent', role='literature', path=(('literature', 'synthetic-parent'),), assignment={})
repo.receive_cells(parent, cells, 'manual-engineering-fixture-receipt')
artifact_refs = {store.get(ref)['artifact_ref'] for ref in saved['input_source_refs']}
artifact_refs.update(value for item in saved['extraction']['views'] for key, value in item['metadata'].items()
    if key in ('original_artifact_ref', 'image_artifact_ref'))
fixture = {'run_id': context.run_id, 'episode_id': parent.episode_id, 'scope': plain(context.scope),
    'received': list(parent.received_record_refs), 'sheet_ref': reference, 'cells': cells,
    'banned_artifacts': sorted(artifact_refs), 'observations': [], 'selection': selection}
fixture_path = output / 'READONLY_FIXTURE_006.json'
fixture_path.write_text(json.dumps(fixture, indent=2) + '\n')
(output / 'ACTUAL_JOINED_OUTPUT_006.json').write_text(json.dumps({
    'evidence_class': 'synthetic engineering source bytes and inserted journal/context/receipt fixtures',
    'not_established': ['selected LiteratureEpisode', 'genuine C1/C4 admission', 'model image interpretation',
        'primary-source measurements', 'calibration', 'uncertainty reader', 'full axis', 'annotation credit'],
    'native_image_toolregistry_outcome': native, 'population_outcome': outcome,
    'saved_payload': saved, 'calculation_artifact': calculation,
    'calculator_implementation_descriptor': implementation_descriptor,
    'requested_parent_cells': cells, 'runtime_observations': []}, indent=2) + '\n')
store.close()
# Reuse the exact fresh-process assertion body exercised by the pinned test.
tree = ast.parse((pin / 'tests/test_literature_ratio_source_readonly.py').read_text())
script = next(node.value.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == 'script' for target in node.targets))
probe = output / 'readonly_probe_006.py'; probe.write_text(script)
process = subprocess.run([sys.executable, str(probe), str(output / 'joined_fixture_006'), str(fixture_path)],
    cwd=pin, env={**os.environ, 'PYTHONPATH': str(pin)}, text=True, capture_output=True)
(output / 'READONLY_STDOUT_006.txt').write_text(process.stdout)
(output / 'READONLY_STDERR_006.txt').write_text(process.stderr)
if process.returncode:
    raise SystemExit(process.returncode)
proof = json.loads(process.stdout)
(output / 'READONLY_PROOF_006.json').write_text(json.dumps(proof, indent=2) + '\n')
imports = {}
for name, module in sorted(sys.modules.items()):
    if name == 'gene_annotation_episode' or name.startswith('gene_annotation_episode.') or name == 'method_loop' or name.startswith('method_loop.'):
        path = Path(module.__file__).resolve()
        if not path.is_relative_to(pin):
            raise AssertionError('import escaped coherent pin: ' + str(path))
        imports[name] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
(output / 'IMPORT_PROOF_006.json').write_text(json.dumps(imports, indent=2) + '\n')
print(json.dumps({'joined_source_origin': saved['extraction']['evidence_origin'],
    'native_record_version': saved['version'], 'extraction_version': saved['extraction']['version'],
    'reported_ratio': saved['sheet']['cells']['reported_ratio']['value'],
    'difference_from_reference': saved['sheet']['cells']['difference_from_reference']['value'],
    'log_reported_ratio': saved['sheet']['cells']['log_reported_ratio']['value'],
    'first_fresh_projection_total_changes': proof['total_changes'], 'imports_inside_pin': len(imports),
    'observations': [], 'custody_receipt_class': 'explicit engineering fixture; not connected C4'}))
