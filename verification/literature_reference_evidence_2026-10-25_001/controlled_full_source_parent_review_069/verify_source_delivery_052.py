"""Verify final073 sealed source tranche and its exact additive scope."""
from pathlib import Path
import difflib
import hashlib
import json
import runpy
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = HERE.parent
OWNED = BASE / 'a105_controlled_source_reader_073'
PIN = OWNED / 'pin_002'
sys.path.insert(0, str(PIN))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((OWNED / 'MANIFEST_002.json').read_bytes())
for name, row in manifest['files'].items():
    assert sha(OWNED / name) == row['sha256'], name
actual = {str(p.relative_to(OWNED)) for p in OWNED.rglob('*') if p.is_file()
          and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts}
assert actual == set(manifest['files']) | {'MANIFEST_002.json', 'SHA256SUMS_002.txt'}
pin_manifest = json.loads((OWNED / 'PIN_MANIFEST_002.json').read_bytes())
for name, row in pin_manifest.items():
    assert sha(PIN / name) == row['sha256'], name
freeze = json.loads((OWNED / 'PRODUCTION_FREEZE_002.json').read_bytes())
patch = ''
for name, row in freeze['files'].items():
    assert sha(ROOT / name) == sha(PIN / name) == row['sha256'], name
    before = OWNED / 'before_001' / name
    original = before.read_text() if before.exists() else ''
    patch += ''.join(difflib.unified_diff(original.splitlines(True), (ROOT / name).read_text().splitlines(True),
        fromfile='a/' + name if original else '/dev/null', tofile='b/' + name))
assert patch == (OWNED / 'IMPLEMENTATION_002.patch').read_text()
assert sha(ROOT / 'gene_annotation_episode/literature_controlled_response_owner_calculations.py') == freeze['owner076']['sha256']
execution = json.loads((OWNED / 'PIN_EXECUTION_RECEIPT_002.json').read_bytes())
for row in execution['actual_imports']:
    assert sha(PIN / row['path']) == row['sha256'], row
assert '625 passed' in (OWNED / 'PIN_TEST_RUN_002.txt').read_text()
detached = json.loads((OWNED / 'DETACHED_SAVED_VALIDATION_002.json').read_bytes())
assert detached['actual_saved_extractions'] == detached['canonical_JSON_saved_extractions'] == 14
assert detached['all_equal'] and detached['source_callbacks_native_literal_readers_decoders_counters_populators_disabled']

from gene_annotation_episode import literature_controlled_response_v2_inputs as reader
from jsonschema import Draft202012Validator
declarations = [
    (reader.controlled_response_v2_arguments_schema, 'a105_controlled_graph_design_061/SELECTION_SCHEMA_V2_001.json'),
    (reader._graph_schema, 'a105_controlled_graph_design_061/GRAPH_RESULT_SCHEMA_002.json'),
    (reader._sheet_schema, 'a105_controlled_adapter_design_065/OWNER_OUTPUT_SCHEMA_004.json'),
    (reader._extraction_schema, 'a105_controlled_full_source_design_069/EXTRACTION_SCHEMA_V2_001.json')]
for factory, relative in declarations:
    schema = factory()
    assert schema == json.loads((BASE / relative).read_bytes())
    Draft202012Validator.check_schema(schema)
# Reexecute the original root counterexample using final pinned APIs, without
# overwriting the preserved failure generated from the earlier code identity.
Fixture = runpy.run_path(str(PIN / 'tests/test_literature_controlled_response_v2_inputs.py'))['Fixture']
f = Fixture(0)
e = f.read()
assert reader.validate_controlled_response_v2_extraction(json.loads(json.dumps(f.args, sort_keys=True)),
    json.loads(json.dumps(e, sort_keys=True))) == e
root_cases = json.loads((HERE / 'ACTUAL_SOURCE_ROOT_CASES_052_002.json').read_bytes())
assert root_cases['canonical_saved_validation_under_forbidden_entrypoints'] == 4
for name, row in root_cases['actual_imports'].items():
    p = Path(row['path']).resolve()
    assert p.is_relative_to(PIN) and sha(p) == row['sha256']
receipt = {'scope': 'Accepted073 source Tranche S only; full literature goal incomplete',
    'manifest_sha256': sha(OWNED / 'MANIFEST_002.json'), 'sealed_payloads_checked': len(manifest['files']),
    'pin_files_checked': len(pin_manifest), 'exact_three_file_delta_rebuilt': True,
    'exact_runtime_schema_reconstructions': len(declarations),
    'recorded_focused_pinned_tests': 625, 'recorded_actual_source_cases': 14,
    'recorded_detached_original_and_canonical_passes': 28,
    'recorded_import_files_reverified': len(execution['actual_imports']),
    'root_original_canonical_counterexample_now_passes': True,
    'root_additional_full_source_cases': 4, 'root_additional_canonical_sentinel_passes': 4,
    'root_probe_correction': 'Unknown control identity cannot cancel; wrong root expectation preserved and corrected without implementation edit',
    'current_final_source_hashes': freeze['files'],
    'remaining': ['V3 joint alternatives/reconciliation/mixed-origin/group identity semantics',
        'Component-local partial/native and full controlled-source selected native integration',
        'Actual C1/C4/parent/source-free runtime integration', 'Primary/configured-model and broader scientific coverage']}
with (HERE / 'SOURCE_DELIVERY_ROOT_RECEIPT_052.json').open('x') as stream:
    json.dump(receipt, stream, indent=2); stream.write('\n')
print(json.dumps({k:v for k,v in receipt.items() if k != 'current_final_source_hashes'}))
