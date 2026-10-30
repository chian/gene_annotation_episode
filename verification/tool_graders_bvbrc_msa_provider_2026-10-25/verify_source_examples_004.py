"""Retain complete source-byte operands and demonstrate pure saved replay."""
from copy import deepcopy
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode import bvbrc_msa_xmfa_inputs as provider

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('source_examples', ROOT / 'tests/test_bvbrc_msa_xmfa_inputs.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode_operands(operands):
    value = deepcopy(operands)
    value['artifact_bytes'] = {k: base64.b64encode(v).decode('ascii') for k, v in value['artifact_bytes'].items()}
    return value


def decode_operands(value):
    value = deepcopy(value)
    value['artifact_bytes'] = {k: base64.b64decode(v, validate=True) for k, v in value['artifact_bytes'].items()}
    return value


def forbidden(*args, **kwargs):
    raise AssertionError('saved source example attempted I/O, subprocess or forbidden reparse')


sources = [ROOT / 'gene_annotation_episode' / name for name in (
    'bvbrc_msa_xmfa_inputs.py', 'bvbrc_alignment_provider_contracts.py', 'bvbrc_alignment_associations.py',
    'xmfa_sources.py', 'xmfa_source_contracts.py', 'xmfa_format_contracts.py', 'phylogeny_formats.py')]
before = {str(p.relative_to(ROOT)): hash_file(p) for p in sources}
retained = {str(p.relative_to(ROOT)): hash_file(p) for p in fixture.NATIVE.iterdir() if p.is_file()}
cases = []
for case in ('combined_native', 'separate_native'):
    document, operands = fixture.native_operands(case)
    cases.append((case, document, operands, 'retained_native_bytes_with_explicit_fixture_invocation'))
document, operands = fixture.native_operands('separate_native')
operands['artifact_bytes'].pop('canFam2.fa')
cases.append(('one_missing_source', document, operands, 'synthetic_missing_source_on_retained_native_example'))
document, operands = fixture.native_operands()
operands['inputs']['files'][0]['records'][0]['sequence'] = 'A' + operands['inputs']['files'][0]['records'][0]['sequence'][1:]
cases.append(('contradictory_json_sequence', document, operands, 'synthetic_counterexample_on_retained_native_bytes'))
document, operands = fixture.native_operands()
fixture.add_maps(operands)
cases.append(('distinct_original_occurrences', document, operands, 'synthetic_explicit_original_maps_on_retained_native_bytes'))
document, operands = fixture.native_operands()
fixture.add_maps(operands)
operands['inputs']['original_maps'][0]['original_member']['occurrence_index'] = 8
cases.append(('unknown_original_occurrence', document, operands, 'synthetic_counterexample_on_retained_native_bytes'))
document, operands = fixture.native_operands()
operands['source_readers'] = ()
cases.append(('missing_reader', document, operands, 'synthetic_missing_declaration_on_retained_native_bytes'))
document, operands = fixture.native_operands()
operands['inputs']['files'][0]['record_completeness'] = 'partial'
cases.append(('partial_record_population', document, operands, 'synthetic_partial_declaration_on_retained_native_bytes'))
cases.extend([
    ('raw_dna', None, fixture.raw_operands(), 'synthetic_raw_bytes'),
    ('raw_empty', None, fixture.raw_operands(b'', sequence='', line_end=1), 'synthetic_empty_raw_bytes'),
    ('raw_invalid_space', None, fixture.raw_operands(b'AC GT', sequence='ACGT', line_end=1), 'synthetic_invalid_raw_bytes'),
    ('utf8_layout', None, fixture.fasta_operands('>séquence\r\nAC G\r\nTT\n'.encode(), encoding='utf-8'), 'synthetic_utf8_layout_bytes'),
])
operands = fixture.fasta_operands(); operands['inputs']['files'][0]['format'] = 'GenBank'; operands['source_readers'] = ()
cases.append(('unbound_genbank', None, operands, 'synthetic_unbound_format_declaration'))

directory = HERE / 'source_examples_004'
directory.mkdir(exist_ok=False)
records = []
for name, document, operands, provenance in cases:
    encoded = {'document': document, 'operands': encode_operands(operands),
        'artifact_bytes_encoding': 'base64', 'provenance': provenance}
    input_path = directory / (name + '.inputs.json')
    with input_path.open('x') as stream:
        json.dump(encoded, stream, indent=2, allow_nan=False); stream.write('\n')
    loaded = json.loads(input_path.read_text())
    selected = decode_operands(loaded['operands'])
    verification = provider.verify_xmfa_source_inputs(**selected)
    record = (None if document is None else provider.extract_msa_xmfa_bindings(document,
        verification=verification, source_comparison='case_insensitive_iupac_exact', evidence=()))
    answer = {'verification': verification, 'binding': record}
    answer_path = directory / (name + '.answer.json')
    with answer_path.open('x') as stream:
        json.dump(answer, stream, indent=2, allow_nan=False); stream.write('\n')
    restored = json.loads(answer_path.read_text())
    with patch('builtins.open', forbidden), patch.object(Path, 'open', forbidden), \
         patch.object(Path, 'read_bytes', forbidden), patch.object(Path, 'read_text', forbidden), \
         patch.object(socket, 'socket', forbidden), patch.object(socket, 'create_connection', forbidden), \
         patch.object(subprocess, 'Popen', forbidden):
        assert provider.verify_xmfa_source_inputs(**selected) == restored['verification']
        with patch.object(provider, 'parse_aligned_fasta', forbidden), \
             patch('gene_annotation_episode.xmfa_formats.parse_mauve_xmfa', forbidden):
            assert provider.validate_msa_xmfa_source_verification(restored['verification'],
                associations=selected['associations']) == restored['verification']
            if document is not None:
                assert provider.extract_msa_xmfa_bindings(document, verification=restored['verification'],
                    source_comparison='case_insensitive_iupac_exact', evidence=()) == restored['binding']
                assert provider.validate_msa_xmfa_binding_record(restored['binding'], document=document,
                    associations=selected['associations']) == restored['binding']
    records.append({'case': name, 'provenance': provenance, 'status': verification['status'],
        'verified_files': len(verification['verified_inputs']['files']),
        'verified_maps': len(verification['verified_inputs']['original_maps']),
        'source_lengths': None if record is None or record['bindings'] is None else
            [m['source_length'] for m in record['bindings']['members']],
        'requirements': sorted({r['reason_code'] for r in verification['requirements']}),
        'supplied_byte_replay_without_acquisition': True,
        'saved_validation_and_binding_without_parsing_or_acquisition': True,
        'artifacts': [{'path': str(p.relative_to(ROOT)), 'sha256': hash_file(p)} for p in (input_path, answer_path)]})
after = {str(p.relative_to(ROOT)): hash_file(p) for p in sources}
assert before == after
assert retained == {str(p.relative_to(ROOT)): hash_file(p) for p in fixture.NATIVE.iterdir() if p.is_file()}
report = {'scope': 'Complete source-byte verification operands/results only; not full MSA sheet/episode/live execution.',
    'cases': records, 'case_count': len(records), 'source_before': before, 'source_after': after,
    'source_unchanged': True, 'retained_native_inputs_unchanged': True}
with (HERE / 'SOURCE_EXAMPLE_REPLAY_004.json').open('x') as stream:
    json.dump(report, stream, indent=2); stream.write('\n')
print(json.dumps({'cases': len(records), 'saved_no_parse_replay': True, 'source_unchanged': True,
    'retained_native_inputs_unchanged': True, 'complete_tool': False}))
