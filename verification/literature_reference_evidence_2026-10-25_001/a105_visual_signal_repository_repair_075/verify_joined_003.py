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
from test_literature_ratio_source_storage import multi_source_view_case, reverse_object_keys, owned, repository
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.literature_ratio_source_storage import _calculator_implementation_descriptor

store, context, selection, native = multi_source_view_case(output / 'joined_fixture_003')
repo = repository(store, context)
outcome = repo.populate(context, selection, 'selected-joined-fixture')
reference = outcome['result']['sheet_ref']
saved = repo.read(reference)
assert len(saved['extraction']['sources']) == 3
assert len(saved['extraction']['views']) == 2
assert [row['representation_id'] for row in saved['extraction']['representations']] == [row['representation_id'] for row in selection['representations']]
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
fixture_path = output / 'READONLY_FIXTURE_003.json'
fixture_path.write_text(json.dumps(fixture, indent=2) + '\n')
(output / 'ACTUAL_JOINED_OUTPUT_003.json').write_text(json.dumps({
    'evidence_class': 'synthetic engineering source bytes and inserted journal/context/receipt fixtures',
    'not_established': ['selected LiteratureEpisode', 'genuine C1/C4 admission', 'model image interpretation',
        'primary-source measurements', 'calibration', 'uncertainty reader', 'full axis', 'annotation credit'],
    'native_image_toolregistry_outcomes': native, 'population_outcome': outcome,
    'saved_payload': saved, 'calculation_artifact': calculation,
    'calculator_implementation_descriptor': implementation_descriptor,
    'requested_parent_cells': cells, 'runtime_observations': []}, indent=2) + '\n')
allowed_artifacts = {store.get(reference)['artifact_ref'], store.get(reference)['request_ref'], saved['calculation_artifact_ref'],
    *(store.get(item['metadata']['source_ref'])['request_ref'] for item in saved['extraction']['views'])}
get_artifact = store.get_artifact
def saved_only(reference):
    assert reference in allowed_artifacts
    return get_artifact(reference)
store.get_artifact = saved_only
from gene_annotation_episode import literature_ratio_source_inputs as inputs
from gene_annotation_episode import literature_ratio_source_calculations as calculations
def forbidden(*args, **kwargs): raise AssertionError('forbidden scientific replay')
inputs.read_relative_signal_source_inputs = forbidden
calculations.populate_relative_signal_v2 = forbidden
from PIL import Image
Image.open = forbidden
before = store.db.total_changes
assert repo.populate(context, reverse_object_keys(selection), 'selected-joined-fixture') == outcome
assert repo.read(reference) == saved
assert store.db.total_changes == before
store.close()
# Reuse the exact fresh-process assertion body exercised by the pinned test.
tree = ast.parse((pin / 'tests/test_literature_ratio_source_readonly.py').read_text())
script = next(node.value.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == 'script' for target in node.targets))
probe = output / 'readonly_probe_003.py'; probe.write_text(script)
process = subprocess.run([sys.executable, str(probe), str(output / 'joined_fixture_003'), str(fixture_path)],
    cwd=pin, env={**os.environ, 'PYTHONPATH': str(pin)}, text=True, capture_output=True)
(output / 'READONLY_STDOUT_003.txt').write_text(process.stdout)
(output / 'READONLY_STDERR_003.txt').write_text(process.stderr)
if process.returncode:
    raise SystemExit(process.returncode)
proof = json.loads(process.stdout)
(output / 'READONLY_PROOF_003.json').write_text(json.dumps(proof, indent=2) + '\n')
imports = {}
for name, module in sorted(sys.modules.items()):
    if name == 'gene_annotation_episode' or name.startswith('gene_annotation_episode.') or name == 'method_loop' or name.startswith('method_loop.'):
        path = Path(module.__file__).resolve()
        if not path.is_relative_to(pin):
            raise AssertionError('import escaped coherent pin: ' + str(path))
        imports[name] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
(output / 'IMPORT_PROOF_003.json').write_text(json.dumps(imports, indent=2) + '\n')
print(json.dumps({'joined_source_origin': saved['extraction']['evidence_origin'],
    'native_record_version': saved['version'], 'extraction_version': saved['extraction']['version'],
    'reported_ratio': saved['sheet']['cells']['reported_ratio']['value'],
    'generic_and_jats_source_count': len(saved['extraction']['sources']),
    'native_view_count': len(saved['extraction']['views']),
    'preserved_representation_order': [row['representation_id'] for row in saved['extraction']['representations']],
    'difference_from_reference': saved['sheet']['cells']['difference_from_reference']['value'],
    'log_reported_ratio': saved['sheet']['cells']['log_reported_ratio']['value'],
    'first_fresh_projection_total_changes': proof['total_changes'], 'imports_inside_pin': len(imports),
    'observations': [], 'custody_receipt_class': 'explicit engineering fixture; not connected C4'}))
