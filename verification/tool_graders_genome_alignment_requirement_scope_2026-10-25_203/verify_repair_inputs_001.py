"""Verify exact frozen data, source scope and configuration-only pin change."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import resource
import socket
import sys

OWN = Path(__file__).resolve().parent
BASELINE, CANDIDATE = OWN / 'baseline_candidate', OWN / 'repair_candidate'
OUT = OWN / 'repair_inputs_001'
OUT.mkdir(exist_ok=False)
sys.dont_write_bytecode = True
sys.path.insert(0, str(CANDIDATE))
resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))


def forbidden(*args, **kwargs):
    raise AssertionError('Pure retained-input verification attempted acquisition')


socket.socket.connect = forbidden
from gene_annotation_episode import bvbrc_genome_alignment_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_appservice_adapters import bind_adapters
from gene_annotation_episode.bvbrc_genome_alignment_sheet import validate_genome_alignment_data
from gene_annotation_episode.bvbrc_genome_alignment_calculators import calculate_genome_alignment_components


def write(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')
    path.chmod(0o444)


def entry(root, name):
    raw = (root / name).read_bytes()
    return {'path': name, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


before = json.loads((OWN / 'REPAIR_BEFORE_MANIFEST_001.json').read_text())['files']
assert all(entry(BASELINE, row['path']) == row for row in before)
old_outputs = json.loads((OWN / 'OUTPUT_HASHES_001.json').read_text())['output_files']
assert all(entry(OWN, row['path']) == row for row in old_outputs)
after = [entry(CANDIDATE, row['path']) for row in before]
changed = [row['path'] for old, row in zip(before, after) if old != row]
assert changed == ['gene_annotation_episode/bvbrc_genome_alignment_sheet.py'], changed
new_test = 'tests/test_genome_alignment_requirement_scope.py'
after.append(entry(CANDIDATE, new_test))
after.sort(key=lambda row: row['path'])
write(OWN / 'REPAIR_AFTER_MANIFEST_001.json', {'source': str(CANDIDATE.relative_to(OWN)),
    'files': after, 'changed_from_before': changed, 'added': [new_test]})
for row in after:
    (CANDIDATE / row['path']).chmod(0o444)

baseline_digest = hashlib.sha256()
for name in sorted(adapter._DEPENDENCIES):
    raw = (BASELINE / 'gene_annotation_episode' / name).read_bytes()
    baseline_digest.update(name.encode() + b'\0' + str(len(raw)).encode() + b'\0' + raw)
old_pin, new_pin = baseline_digest.hexdigest(), adapter.implementation_sha256()
assert old_pin == '42bea987a93cee2902278ba5a2adc047d1b334ffb6f99d7fb2f8f980d410962a'
assert old_pin != new_pin
config = {'adapter_id': adapter.ADAPTER_ID, 'adapter_version': adapter.ADAPTER_VERSION,
    'implementation_sha256': old_pin}
try:
    bind_adapters([config])
except ValueError as error:
    assert str(error) == 'appservice_adapter_implementation_conflict'
else:
    raise AssertionError('Stale configured pin was accepted')
config['implementation_sha256'] = new_pin
bound = bind_adapters([config])
assert bound[(adapter.ADAPTER_ID, adapter.ADAPTER_VERSION)] == (adapter, new_pin)

capture = OWN / 'capture_failure_001'
data = json.loads((capture / 'data_009.json').read_text())
original = deepcopy(data)
validated = validate_genome_alignment_data(data)
assert validated == data == original
assert validated is not data
publications = [json.loads(path.read_text()) for path in capture.rglob('publication_inputs.json')]
inputs = next(value for value in publications
    if value['current_operation']['arguments']['requirement_ids'] == ['native'])
plan = inputs['adapter']['parameters']['calculation_plan']
components = calculate_genome_alignment_components(validated, calculation_plan=plan)
assert data == original
native = components['outcomes'][0]['measurement']['value']
standalone = json.loads((OWN / 'probe_domains_001/native_components_standalone.json').read_text())
assert native == standalone
coverage = native['coverage'][0]
assert coverage['known_union_bases']['value'] == 690
assert coverage['denominator_bases']['value'] == 693
assert coverage['coverage_fraction']['value'] == 690 / 693
assert data['associations']['artifacts'][0]['artifact']['requirement_ids'] == ['native']
assert 'native' not in {row['requirement_id'] for row in data['requirements']}
write(OUT / 'components.json', components)
write(OUT / 'validated_exact_failure_data.json', validated)
receipt = {'baseline_files_unchanged': len(before), 'original_diagnostic_files_unchanged': len(old_outputs),
    'changed_source_paths': changed, 'added_test_paths': [new_test],
    'baseline_adapter_pin': old_pin, 'repair_adapter_pin': new_pin,
    'old_configured_pin_rejected': 'appservice_adapter_implementation_conflict',
    'new_configured_pin_bound': True, 'dependency_list_changed': False,
    'exact_failing_data_preserved_and_accepted': True, 'original_task_unchanged': True,
    'artifact_output_selection_ids': ['native'], 'scientific_requirement_count': len(data['requirements']),
    'native_measurement_equals_baseline_standalone': True,
    'union_bases': 690, 'denominator_bases': 693, 'coverage_fraction': 690 / 693,
    'network_scope': 'all socket connections forbidden', 'wall_time_limit': None}
write(OUT / 'receipt.json', receipt)
print(json.dumps(receipt, sort_keys=True))
