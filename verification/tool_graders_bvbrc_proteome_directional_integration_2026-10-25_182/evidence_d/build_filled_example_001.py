"""Retained public native bytes and controlled bundle labels; no service job."""
from hashlib import sha256
import json
from pathlib import Path
import socket
import subprocess

from gene_annotation_episode import bvbrc_proteome_bundle_adapter_v2 as adapter
from gene_annotation_episode.bvbrc_proteome_bundle_v2_contracts import validate_saved_provider_v2
from gene_annotation_episode.execution_contracts import digest


def forbidden(*args, **kwargs):
    raise AssertionError('pure retained example attempted network or process work')


evidence = Path(__file__).resolve().parent
specimen = json.loads((evidence / 'package_input_001.json').read_text())
files = specimen.pop('artifact_files')
specimen['artifact_bytes'] = {ref: (evidence / path).read_bytes() for ref, path in files.items()}
target = {'document_id': 'retained_2221', 'query_ordinal': 1, 'subject_ordinal': 0}
specimen['requested_form'] = adapter.requested_form_schema({
    'coverage': {'kind': 'directional_coverage', 'scope': 'query',
        'document_id': target['document_id'], 'query_ordinal': 1, 'metric': 'any_displayed_subject_query_paired_union'},
    'symbol_identity': {'kind': 'directional_fraction', 'scope': 'subject',
        **target, 'metric': 'compatible_unique_pair_symbol_identity'},
    'resolved_identity': {'kind': 'directional_fraction', 'scope': 'subject',
        **target, 'metric': 'compatible_unique_pair_resolved_identity'},
    'expectation': {'kind': 'directional_native_decimal', 'scope': 'hsp',
        **target, 'hsp_ordinal': 1, 'metric': 'expect'},
})
socket.create_connection = socket.socket = subprocess.run = subprocess.Popen = forbidden
pin = adapter.implementation_sha256()
result = adapter.consume_bundle(**specimen)
assert pin == adapter.implementation_sha256()
sheet, components = validate_saved_provider_v2(result['sheet'], result['components'],
    parameters=specimen['parameters'], requested_form=specimen['requested_form'],
    original_task=specimen['bundle']['original_task'], bundle_sha256=digest(specimen['bundle']), bundle=specimen['bundle'])
assert sheet == result['sheet'] and components == result['components']
subject = components['directional']['components']['reports'][0]['queries'][1]['subjects'][0]
assert subject['coverage']['query_trace_paired_union']['coverage']['value'] == {
    'numerator': 529, 'denominator': 600, 'decimal': '0.881666666666666667'}
assert subject['compatible_unique_pair_symbol_identity']['value'] == {
    'numerator': 468, 'denominator': 529, 'decimal': '0.884688090737240076'}
assert subject['compatible_unique_pair_resolved_identity']['value'] == {
    'numerator': 468, 'denominator': 468, 'decimal': '1.000000000000000000'}
assert subject['compatible_pair_counts']['unresolved_pairs']['value'] == 61
assert subject['hsps'][1]['native_scores']['expect']['value'] == '2e-66'
payload = {'provenance': json.loads((evidence / 'package_input_provenance_001.json').read_text()),
    'verification_phase': 'development_public_fixture_not_service_run',
    'implementation_sha256': pin, 'native_sha256': sha256(specimen['artifact_bytes']['directional']).hexdigest(),
    'input': {'bundle': specimen['bundle'], 'parameters': specimen['parameters'],
        'requested_form': specimen['requested_form'], 'supplied_values': specimen['supplied_values']},
    'provider_result': result}
path = evidence / 'FILLED_NATIVE_EXAMPLE_001.json'
assert not path.exists(), 'retained development evidence must not be overwritten'
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
print(json.dumps({'status': result['status'], 'implementation_sha256': pin, 'file': str(path),
    'sha256': sha256(path.read_bytes()).hexdigest(), 'facts': result['facts']}, indent=2))
