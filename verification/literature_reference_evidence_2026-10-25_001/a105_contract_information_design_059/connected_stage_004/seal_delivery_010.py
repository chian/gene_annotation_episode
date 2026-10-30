"""Seal final source, complete runtime pin and detached actual receipts."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import platform
import sys

STAGE = Path(__file__).absolute().parent
ROOT = next(p for p in STAGE.parents if (p / '.venv/bin/python').exists())

def fp(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

pin = STAGE / 'pin_010'
manifest = json.loads((pin / 'PIN_MANIFEST.json').read_text())
for name, row in manifest.items(): assert fp(pin / name) == row, name
sources = json.loads((STAGE / 'SOURCE_RECEIPT_010.json').read_text())
for name, row in sources['files'].items():
    assert fp(ROOT / name) == row, name
    assert fp(STAGE / 'snapshot_010' / name) == row, name
    assert fp(STAGE / 'reconstructed_010' / name) == row, name
frozen = {
 'gene_annotation_episode/schema_information_text.py': '5b4ca71e09952b5673a765b1998d5c7a15c5bc72fa3eb957693ab4b54b6f2e64',
 'gene_annotation_episode/episode_contract_information.py': 'ac152800cfd851017150aedecbdd43b42dcfd6556803f5ecf998805ae653e242',
 'tests/test_schema_information_text.py': '84158e92104fa41a6f2a6319317f6223213490afb149d0d5fa46d58c5c3ac67d',
 'tests/test_episode_contract_information.py': '1f71eeaedd6d810676adacfbdfb7732d7613a80af50599610af8e4779498fc72'}
for name, expected in frozen.items(): assert fp(ROOT / name)['sha256'] == expected, name
checks = STAGE / 'checks_010'
terminal = json.loads((checks / 'TERMINAL_RECEIPT_004.json').read_text())
assert terminal['exit_code'] == 0
assert '190 passed in 204.37s' in (checks / 'TERMINAL_004.log').read_text()
worker = json.loads((checks / 'WORKER_RECEIPT_004.json').read_text())
assert worker['pytest_exit_code'] == 0 and worker['verified_pin_entries'] == len(manifest)
assert worker['actual_contracts'] == 37 and worker['actual_forms'] == 18
versions = {}
for name in ('jsonschema', 'numpy', 'scipy', 'biopython', 'pillow'):
    try: versions[name] = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError: versions[name] = None
receipt = {'state': 'final connected implementation sealed for parent review; no configured-model release',
    'source_files': sources['files'], 'source_patch': fp(STAGE / 'IMPLEMENTATION_010.patch'),
    'correction_from_005_patch': fp(STAGE / 'CORRECTION_FROM_005_010.patch'),
    'pin_manifest': fp(pin / 'PIN_MANIFEST.json'), 'pin_entries': len(manifest),
    'pure_stage003_files_unchanged': frozen, 'final_focused_tests': {'passed': 190, 'failed': 0, 'seconds': 204.37, 'exit_code': 0},
    'broader_pre_correction_pin005': {'passed':315,'failed':5,'seconds':656.39},
    'broader_pre_correction_pin006': {'passed':316,'failed':5,'seconds':752.00},
    'baseline_failure_comparison': 'Four exact root-tool/history failures reproduced with all eight originals over identical dependencies; fifth absent-paper-packet failure also reproduced before source bytes.',
    'complete_request_cases': worker['complete_request_cases'], 'actual_contracts':37, 'actual_forms':18,
    'application_imports_verified_from_pin':len(worker['verified_imports']),
    'actual_configured_model_calls':0, 'scientific_papers_opened':0, 'scientific_routing_implemented':False,
    'runtime_assets': 'Complete application/shared-loop package files, defaults, knowledge/launch libraries, schema JSON, vendor provenance/licenses; external dependencies supplied by unchanged project virtualenv. Real paper test packets and case inputs deliberately absent.',
    'environment': {'entrypoint':str(ROOT/'.venv/bin/python'), 'python':platform.python_version(),
                    'executable':sys.executable,'packages':versions},
    'unchanged_boundaries':'No sheet/A101/W05/controller/model/default/root boundary/shared-test/reader/calculator/application/C1/C4/durable/method_loop edits',
    'artifact_ownership_note':'One accidental empty temporary file outside the owned stage was immediately removed; no existing outside file was changed.'}
with (STAGE / 'DELIVERY_RECEIPT_010.json').open('x') as stream:
    json.dump(receipt, stream, indent=2);stream.write('\n')
selected = []
for name in ['BASELINE_004.json','CONNECTED_API_005.md','HANDOFF_010.md','INSPECTION_010.md',
 'IMPLEMENTATION_010.patch','CORRECTION_FROM_005_010.patch','SOURCE_RECEIPT_010.json','DELIVERY_RECEIPT_010.json',
 'prepare_pin_010.py','run_connected_checks_010.py','launch_checks_010.py','package_sources_010.py',
 'capture_saved_examples_010.py','measure_wire_serialization_010.py','seal_delivery_010.py',
 'BASELINE_REGRESSION_TERMINAL_008.log','BASELINE_REGRESSION_RECEIPT_008.json',
 'BASELINE_MISSING_PACKET_TERMINAL_009.log','BASELINE_MISSING_PACKET_RECEIPT_009.json',
 'checks_006/TERMINAL_004.log','checks_006/TERMINAL_RECEIPT_004.json',
 'checks_007/TERMINAL_004.log','checks_007/TERMINAL_RECEIPT_004.json']:
    selected.append(STAGE / name)
for directory in ('baseline','snapshot_010','reconstructed_010','pin_010'):
    selected.extend(path for path in (STAGE / directory).rglob('*') if path.is_file() and '__pycache__' not in path.parts)
for path in checks.rglob('*'):
    if not path.is_file() or 'pytest_work' in path.parts: continue
    rel = path.relative_to(checks)
    if rel.parts[0] == 'measurements' and len(rel.parts) > 3: continue
    selected.append(path)
sealed = {str(path.relative_to(STAGE)): fp(path) for path in sorted(set(selected))}
with (STAGE / 'MANIFEST_010.json').open('x') as stream:
    json.dump(sealed, stream, indent=2, sort_keys=True);stream.write('\n')
print(json.dumps({'sealed_entries':len(sealed),'manifest':fp(STAGE/'MANIFEST_010.json'),
    'final_focused_passed':190,'actual_contracts':37,'actual_forms':18,'complete_requests':6,'actual_configured_model_calls':0}))
