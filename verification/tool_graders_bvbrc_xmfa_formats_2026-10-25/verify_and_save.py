"""Offline component verification; no aligner, service, or episode is executed.

This verification harness alone reads/writes local fixtures. Production XMFA
reader/validator functions are exercised again with I/O and imports disabled.
"""
from contextlib import ExitStack
import builtins
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode import xmfa_formats
from gene_annotation_episode.xmfa_formats import parse_mauve_xmfa
from gene_annotation_episode.xmfa_format_contracts import validate_xmfa_document, CALLER_ERROR_CODES

OUT = Path(__file__).resolve().parent
BOUNDARY = ROOT / 'verification/tool_graders_bvbrc_msa_xmfa_boundaries_2026-10-25'
OWNED = [
    'gene_annotation_episode/xmfa_formats.py',
    'gene_annotation_episode/xmfa_format_contracts.py',
    'tests/test_xmfa_formats.py', 'tests/test_xmfa_format_contracts.py',
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def forbidden(*args, **kwargs):
    raise AssertionError('pure XMFA function attempted a forbidden side effect or import')


def main():
    receipts = json.loads((BOUNDARY / 'SOURCE_RECEIPTS.json').read_text())
    source_audit = []
    for receipt in receipts:
        if 'sha256' not in receipt:
            continue
        data = (BOUNDARY / receipt['path']).read_bytes()
        assert digest(data) == receipt['sha256'] and len(data) == receipt['bytes']
        source_audit.append({'path': str((BOUNDARY / receipt['path']).relative_to(ROOT)),
                             'bytes': len(data), 'sha256': digest(data)})
    assert len(source_audit) == 34
    cases = []
    for name in ('combined.xmfa', 'separate.xmfa', 'simple.xmfa', 'simple_short.xmfa'):
        path = BOUNDARY / 'native_examples' / name
        receipt = next(r for r in receipts if r.get('path') == 'native_examples/' + name)
        cases.append({'name': name, 'data': path.read_bytes(), 'encoding': 'ascii',
                      'raw_artifact_ref': str(path.relative_to(ROOT)), 'source_ref': receipt['url'],
                      'kind': 'retained_upstream_native_fixture_not_a_new_execution'})
    synthetic = {
        'no_final_newline.xmfa': ('#FormatVersion Mauve1\n>1:1-2 -\nAC\n>2:0-0 +\n--\n=', 'ascii'),
        'malformed_and_truncated.xmfa': ('#FormatVersion Mauve1\n>1:1-4 +\nAC\n>bad:1e0-2 ? exact comment\nA.\n', 'ascii'),
        'utf8_crlf.xmfa': ('# comment é\r\n#FormatVersion Mauve1\r\n#Sequence1File\tpath β with spaces.fa\r\n>1:2-3 - naïve\r\nAc\r\n=', 'utf-8'),
        'unknown_version.xmfa': ('#FormatVersion Future2\n>1:1-1 +\nA\n=', 'ascii'),
        'empty.xmfa': ('', 'ascii'),
        'invalid_encoding.xmfa': (b'\xff', 'utf-8'),
    }
    for name, (text, encoding) in synthetic.items():
        data = text if type(text) is bytes else text.encode(encoding)
        path = OUT / 'synthetic_inputs' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        cases.append({'name': name, 'data': data, 'encoding': encoding,
                      'raw_artifact_ref': str(path.relative_to(ROOT)),
                      'source_ref': 'explicit_synthetic_format_counterexample:' + name,
                      'kind': 'explicit_synthetic_format_counterexample'})
    rows = []
    for case in cases:
        case['artifact'] = {'raw_artifact_ref': case['raw_artifact_ref'], 'source_ref': case['source_ref'],
                            'sha256': digest(case['data'])}
        case['result'] = parse_mauve_xmfa(case['data'], artifact=case['artifact'],
            dialect='mauve1', alphabet='dna', encoding=case['encoding'])
        target = 'filled_documents/' + case['name'] + '.parse_result.json'
        save(target, case['result'])
        # Load the saved result before the no-I/O replay below.
        case['saved'] = json.loads((OUT / target).read_text())
        assert case['saved'] == case['result']
        doc = case['result']['value']
        rows.append({'name': case['name'], 'kind': case['kind'], 'bytes': len(case['data']),
            'sha256': case['artifact']['sha256'], 'saved_result': target,
            'status': case['result']['status'], 'completeness': doc['completeness'] if doc else None,
            'block_count': len(doc['blocks']) if doc else None,
            'block_widths': [b['alignment_column_count'] for b in doc['blocks']] if doc else None,
            'diagnostics': [d['code'] for d in case['result']['diagnostics']]})
    expected_widths = [[49, 1, 1, 41, 1, 1], [52, 22], [5670, 4420, 4970, 1470, 1470], [240, 46]]
    assert [row['block_widths'] for row in rows[:4]] == expected_widths
    first = cases[0]['result']['value']['blocks'][0]['records']
    assert [r['nongap_character_count'] for r in first] == [48, 0, 47]
    assert [r['gapped_character_count'] for r in first] == [49, 49, 49]
    assert [r['interval_0based_half_open'] for r in first] == [[1, 49], None, [1, 48]]
    assert cases[3]['result']['value']['completeness'] == 'truncated'
    replayed = 0
    with ExitStack() as stack:
        targets = [(xmfa_formats, 'parse_mauve_xmfa'), (builtins, 'open'), (io, 'open'),
            (os, 'open'), (os, 'system'), (Path, 'open'), (Path, 'read_text'), (Path, 'read_bytes'),
            (socket, 'socket'), (socket, 'create_connection'), (subprocess, 'Popen'),
            (subprocess, 'run'), (subprocess, 'check_output'), (builtins, '__import__')]
        for obj, name in targets:
            stack.enter_context(patch.object(obj, name, forbidden))
        for case in cases:
            # Captured pure reader entrypoint; module entrypoint is disabled so
            # a validator cannot use it to replace saved-document validation.
            actual = parse_mauve_xmfa(case['data'], artifact=case['artifact'], dialect='mauve1',
                alphabet='dna', encoding=case['encoding'])
            assert actual == case['saved']
            if case['saved']['value'] is not None:
                assert validate_xmfa_document(case['saved']['value']) == case['saved']['value']
                replayed += 1
    save('SOURCE_HASH_AUDIT.json', {'retained_source_count': len(source_audit), 'all_hashes_and_sizes_match': True,
        'sources': source_audit})
    summary = {'kind': 'pure_xmfa_format_component_verification', 'examples': rows,
        'no_io_native_parser_cases': len(cases), 'no_io_saved_document_replays': replayed,
        'caller_error_suffixes': sorted(CALLER_ERROR_CODES),
        'new_native_aligner_runs': 0, 'service_submissions': 0, 'hpc_jobs': 0,
        'episode_path_verified': False, 'msa_complete': False,
        'owned_implementation_files': [{'path': name, 'bytes': (ROOT / name).stat().st_size,
                                        'sha256': digest((ROOT / name).read_bytes())} for name in OWNED]}
    save('VERIFICATION.json', summary)
    print(json.dumps({'native_files': 4, 'synthetic_cases': len(synthetic),
        'unchanged_retained_sources': len(source_audit), 'no_io_parser_cases': len(cases),
        'no_io_saved_document_replays': replayed, 'native_block_counts': [r['block_count'] for r in rows[:4]]}))


if __name__ == '__main__':
    main()
