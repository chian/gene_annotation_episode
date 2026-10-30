"""Reproduce C1 saved-input examples; all task/receipt custody is SYNTHETIC.

This verification writer uses files only to load/write its saved examples. The
public extractor is replayed under forbidden I/O/native/model entry points.
No acquisition, service call, native scientific program or provider is run.
"""
from base64 import b64decode, b64encode
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.bvbrc_appservice_records import AppServiceRecords
from gene_annotation_episode.bvbrc_genome_alignment_inputs import extract_genome_alignment_inputs
from gene_annotation_episode.bvbrc_genome_alignment_input_contracts import validate_genome_alignment_inputs
from gene_annotation_episode.mauve_v4_calculators import calculate_mauve_v4_segments
from gene_annotation_episode.providers import ModelConnection
from test_bvbrc_genome_alignment_inputs import candidate
from test_bvbrc_genome_alignment_retained_records import fixture, inline, log_bytes, log_record
from test_mauve_v4_formats import OFFICIAL, parse
from test_mauve_v4_calculators import selection


PROVENANCE = ('SYNTHETIC original task, receipts, command log and custody. FASTA '
              'bytes are supplied fixture data. No authentic BV-BRC job or host '
              'possession is claimed. The separate native v4 file is retained '
              'upstream output with no relationship claimed to the synthetic task.')
OWNED = (
    'gene_annotation_episode/bvbrc_genome_alignment_inputs.py',
    'gene_annotation_episode/bvbrc_genome_alignment_retained_records.py',
    'tests/test_bvbrc_genome_alignment_inputs.py',
    'tests/test_bvbrc_genome_alignment_retained_records.py',
)


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def call(task, records, data, values):
    result = extract_genome_alignment_inputs(task, supplied_values=tuple(values),
        supplied_bytes=data, retained_records=tuple(records))
    assert validate_genome_alignment_inputs(result['value']) == result['value']
    assert result['requirements'] == result['value']['requirements']
    assert result['diagnostics'] == result['value']['diagnostics']
    return result


def forbidden(*args, **kwargs):
    raise AssertionError('pure C1 extractor attempted I/O, model or execution')


def main():
    genomes = ['123.1', '123.1']
    task, request, handoff, data = fixture(genomes,
        bindings=[inline('original-genome-array', '/genome_ids', genomes)])
    log = log_record(task, request, data, raw=log_bytes(genomes))
    supplied = candidate(task, data)
    saved = {'provenance': PROVENANCE, 'original_task': task,
        'retained_records': [handoff, log], 'supplied_values': [supplied],
        'supplied_bytes_base64': {key: b64encode(value).decode('ascii') for key, value in data.items()}}
    write('SYNTHETIC_SAVED_INPUTS_001.json', saved)
    # Read saved operands completely before installing the I/O prohibition.
    replay = json.loads((HERE / 'SYNTHETIC_SAVED_INPUTS_001.json').read_text())
    replay_data = {key: b64decode(value, validate=True) for key, value in replay['supplied_bytes_base64'].items()}
    before = deepcopy((replay['original_task'], replay['retained_records'], replay['supplied_values'], replay_data))
    expected = call(task, (handoff, log), data, (supplied,))
    with ExitStack() as stack:
        for target in ('builtins.open', 'pathlib.Path.open', 'pathlib.Path.read_text',
            'pathlib.Path.read_bytes', 'socket.socket', 'socket.create_connection',
            'subprocess.Popen', 'subprocess.run', 'os.system', 'urllib.request.urlopen'):
            stack.enter_context(patch(target, forbidden))
        for owner, name in ((ModelConnection, 'complete'), (PublicClients, '_http'),
                            (AppServiceRecords, 'read')):
            stack.enter_context(patch.object(owner, name, forbidden))
        actual = call(replay['original_task'], replay['retained_records'], replay_data, replay['supplied_values'])
        assert actual == expected
        assert before == (replay['original_task'], replay['retained_records'], replay['supplied_values'], replay_data)
        assert actual['value']['original_task'] is not replay['original_task']
        assert actual['value']['requirements'] is not actual['requirements']
    write('FILLED_EXTRACTION_001.json', {'provenance': PROVENANCE, 'extraction': actual})

    task2, request2, handoff2, data2 = fixture(recipe='mauveAligner')
    log2 = log_record(task2, request2, data2, raw=log_bytes(recipe='mauveAligner'))
    inputs2 = call(task2, (handoff2, log2), data2, (candidate(task2, data2),))['value']
    native_bytes = OFFICIAL.read_bytes()
    document = parse(native_bytes)['value']
    native = calculate_mauve_v4_segments(document,
        selection=selection(document, denominator='native_declared_length'), inputs=inputs2)
    staged = calculate_mauve_v4_segments(document,
        selection=selection(document, denominator='validated_staged_length'), inputs=inputs2)
    write('NATIVE_CONSUMER_EXAMPLE_001.json', {'provenance': PROVENANCE,
        'native_source_path': str(OFFICIAL.relative_to(ROOT)),
        'native_source_sha256': hashlib.sha256(native_bytes).hexdigest(),
        'input_extraction': inputs2, 'native_declared_denominators': native,
        'unresolved_staged_denominators': staged})
    summary = {'provenance': PROVENANCE, 'saved_input_purity': 'passed',
        'unchanged_input_values': True, 'detached_output': True,
        'original_genome_occurrences': [r['genome_id'] for r in actual['value']['genome_occurrences']],
        'original_parameter_pointers': [r['parameter_pointer'] for r in actual['value']['genome_occurrences']],
        'original_binding_ids': [r['input_binding_id'] for r in actual['value']['genome_occurrences']],
        'logged_unique_path_placeholders': sum(f['artifact'] is None for f in actual['value']['files']),
        'candidate_record_lengths': [[len(r['sequence']) for r in f['records']]
                                    for f in actual['value']['files'] if f['artifact'] is not None],
        'member_denominators': [m['source_length'] for m in actual['value']['member_bindings']],
        'genome_census_state': actual['value']['genome_census_state'],
        'native_v4_known_union_bases': [r['known_union_bases']['value'] for r in native['coverage']],
        'native_v4_declared_denominators': [r['denominator_bases']['value'] for r in native['coverage']],
        'native_v4_coverage_fractions': [r['coverage_fraction']['value'] for r in native['coverage']],
        'staged_coverage_fractions': [r['coverage_fraction']['value'] for r in staged['coverage']],
        'unimplemented_boundaries': ['authenticated host collection of retained_records',
            'provider forwarding and registration', 'complete selected episode return path',
            'live GenomeAlignment service execution', 'original staged-at-invocation byte identity',
            'original genome retrieval census', 'native contig/feature mapping',
            'internal BBCols interval to XMFA export mapping', 'deployed producer/build byte identity']}
    write('VERIFICATION_RESULTS_001.json', summary)
    hashes = {path: {'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
                     'bytes': (ROOT / path).stat().st_size} for path in OWNED}
    write('OWNED_SOURCE_HASHES_001.json', hashes)
    print(json.dumps(summary, indent=2))
    print(json.dumps(hashes, indent=2))


if __name__ == '__main__':
    main()
