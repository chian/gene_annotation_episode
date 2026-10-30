"""Retain complete source-binding examples and verify no-acquisition replay."""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('xmfa_source_test_inputs', ROOT/'tests/test_xmfa_sources.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
from gene_annotation_episode.xmfa_sources import bind_xmfa_sources, validate_xmfa_bindings_for_document


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(name, value):
    path = OUT/name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')
    return {'path': str(path.relative_to(ROOT)), 'sha256': digest(path.read_bytes())}


def forbidden(*args, **kwargs):
    raise AssertionError('source replay may not acquire, parse native bytes or execute work')


def main():
    files = [ROOT/p for p in (
        'gene_annotation_episode/xmfa_sources.py',
        'gene_annotation_episode/xmfa_source_contracts.py',
        'gene_annotation_episode/xmfa_formats.py',
        'gene_annotation_episode/xmfa_format_contracts.py',
        'tests/test_xmfa_sources.py')]
    before = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in files}
    native_before = {str(p.relative_to(ROOT)): digest(p.read_bytes())
                     for p in fixtures.BASE.iterdir() if p.is_file()}
    document = fixtures.native_document()
    inputs = fixtures.supplied()
    cases = [('combined_native', document, inputs, 'retained_native_with_explicit_fixture_invocation')]
    cases.append(('separate_native', fixtures.native_document('separate.xmfa'),
                  fixtures.supplied('multiple_files_concatenated'),
                  'retained_native_with_explicit_fixture_invocation'))
    for name in ('unknown_invocation', 'partial_input_population', 'source_mismatch',
                 'entry_content_swap', 'distinct_original_occurrences',
                 'conflicting_original_maps', 'missing_map_evidence', 'missing_source_bytes'):
        supplied = deepcopy(inputs)
        if name == 'unknown_invocation':
            supplied['invocation']['mode'] = 'unknown'
        elif name == 'partial_input_population':
            supplied['files'][0]['record_completeness'] = 'partial'
        elif name == 'source_mismatch':
            row = supplied['files'][0]['records'][0]
            row['sequence'] = 'A' + row['sequence'][1:]
        elif name == 'entry_content_swap':
            rows = supplied['files'][0]['records']
            rows[0]['sequence'], rows[2]['sequence'] = rows[2]['sequence'], rows[0]['sequence']
        elif name in ('distinct_original_occurrences', 'conflicting_original_maps'):
            supplied['original_maps'] = [fixtures.mapping(supplied),
                fixtures.mapping(supplied, occurrence=1 if name == 'distinct_original_occurrences' else 0,
                                 offset=20)]
        elif name == 'missing_map_evidence':
            supplied['original_maps'] = [fixtures.mapping(supplied)]
            supplied['original_maps'][0]['evidence'] = []
        elif name == 'missing_source_bytes':
            supplied['files'] = []
        cases.append((name, document, supplied, 'synthetic_supplied_operand_counterexample_on_native_xmfa'))
    results = []
    for name, doc, supplied, provenance in cases:
        operands = json.loads(json.dumps({'document': doc, 'inputs': supplied,
                                         'source_comparison': 'case_insensitive_iupac_exact'}))
        answer = bind_xmfa_sources(**operands)
        expected_status = 'ok' if name in ('combined_native', 'separate_native',
                                          'distinct_original_occurrences') else 'partial'
        assert answer['status'] == expected_status
        if name == 'combined_native':
            assert [m['source_length'] for m in answer['members']] == [50, 41, 49]
            assert sum(c['state'] == 'match' for c in answer['source_checks']) == 7
        if name == 'separate_native':
            assert [m['source_length'] for m in answer['members']] == [50, 49, 41]
        records = [write('saved_examples/'+name+'-inputs.json', operands),
                   write('saved_examples/'+name+'-answer.json', answer)]
        saved_input = json.loads((ROOT/records[0]['path']).read_text())
        saved_answer = json.loads((ROOT/records[1]['path']).read_text())
        original = deepcopy(saved_input)
        with ExitStack() as locked:
            for target in ('builtins.open', 'pathlib.Path.open', 'pathlib.Path.read_bytes',
                           'socket.socket', 'socket.create_connection', 'subprocess.Popen',
                           'gene_annotation_episode.xmfa_formats.parse_mauve_xmfa',
                           'gene_annotation_episode.phylogeny_formats.parse_aligned_fasta'):
                locked.enter_context(patch(target, forbidden))
            replay = bind_xmfa_sources(**saved_input)
            assert replay == saved_answer
            assert validate_xmfa_bindings_for_document(saved_input['document'], saved_answer) == saved_answer
            assert saved_input == original
        assert all(digest((ROOT/r['path']).read_bytes()) == r['sha256'] for r in records)
        results.append({'case': name, 'provenance': provenance, 'status': answer['status'],
            'source_lengths': [m['source_length'] for m in answer['members']],
            'checks': {state: sum(c['state'] == state for c in answer['source_checks'])
                       for state in ('match', 'mismatch', 'not_checked', 'absent_zero')},
            'requirements': sorted({r['reason_code'] for r in answer['requirements']}),
            'exact_no_io_saved_replay': True, 'artifacts': records})
    after = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in files}
    assert before == after
    assert native_before == {str(p.relative_to(ROOT)): digest(p.read_bytes())
                            for p in fixtures.BASE.iterdir() if p.is_file()}
    record = {'scope': 'Pure source binding and saved relationship validation; native inputs plus declared fixture invocation, no live task custody or aligner/service/episode execution.',
              'case_count': len(results), 'cases': results, 'source_before': before,
              'source_after': after, 'source_unchanged': True, 'retained_native_inputs_unchanged': True}
    write('SOURCE_REPLAY_003.json', record)
    print(json.dumps({'saved_cases': len(results), 'exact_no_io_replays': len(results),
                      'source_unchanged': True, 'retained_native_inputs_unchanged': True}))


if __name__ == '__main__':
    main()
