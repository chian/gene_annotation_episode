"""Synthetic and retained-native source tests; no live native execution."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path

import pytest

from gene_annotation_episode.genomic_overlap_contracts import (
    canonical_genomic_overlap_sheet_sha256, genomic_overlap_schema,
    validate_genomic_overlap_record,
)
from gene_annotation_episode.genomic_overlap_inputs import (
    build_genomic_overlap_sheet, extract_overlap_reference_metadata,
    parse_bedtools_intersect_wo, parse_region_set,
)

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / 'verification/tool_graders_genomic_overlap_contract_2026-10-27_418'
WORKED = json.loads((PACKET / 'WORKED_EXAMPLE.json').read_text())
PARAMETERS = {'version': 'genomic_overlap_calculation_parameters_v1', 'minimum_overlap_bp': 1,
              'minimum_a_fraction': {'numerator': 0, 'denominator': 1},
              'minimum_b_fraction': {'numerator': 0, 'denominator': 1}}


def identity(raw, format):
    sha = hashlib.sha256(raw).hexdigest()
    return {'artifact_ref': 'synthetic:' + sha, 'sha256': sha, 'size_bytes': len(raw), 'format': format}


def inputs(contents, *, formats=None, references=None):
    formats = formats or ['bed_outer_span_v1'] * len(contents)
    references = references or [None] * len(contents)
    specs, parsed = [], []
    for i, (raw, format, ref) in enumerate(zip(contents, formats, references)):
        key = chr(ord('A') + i)
        spec = {'set_key': key, 'display_label': None, 'reference': deepcopy(ref), 'format': format,
                'source': {'kind': 'bed_artifact' if format == 'bed_outer_span_v1' else 'coordinate_rows_artifact',
                           'source_ref': 'synthetic:' + key, 'file': identity(raw, format)}}
        specs.append(spec)
        parsed.append(parse_region_set(raw, specification=spec, set_position=i))
    comparisons = [{'comparison_key': f'comparison_{ordinal}', 'ordinal': ordinal,
                    'a_set_key': specs[i]['set_key'], 'b_set_key': specs[j]['set_key']}
                   for ordinal, (i, j) in enumerate((i, j) for i in range(len(specs)) for j in range(i + 1, len(specs)))]
    request = {'version': 'genomic_overlap_request_v1', 'operation': 'analyze_genomic_region_overlap',
               'mode': 'unstranded_outer_span', 'region_sets': specs, 'comparisons': comparisons,
               'output_prefix': 'synthetic'}
    return request, parsed


def receipt(pair, sets, raw, *, derivation='supplied_native_output'):
    by_key = {s['set_key']: s for s in sets}
    analytic = derivation == 'validated_empty_input'
    uninvoked = analytic or derivation == 'not_executed_invalid_input'
    return {'version': 'genomic_overlap_native_pair_receipt_v1', 'comparison_key': pair['comparison_key'],
            'identity': None, 'derivation': derivation, 'outcome': 'not_executed' if uninvoked else 'unknown',
            'software': None, **{side: {'set_key': pair[side + '_set_key'],
                'original_file': deepcopy(by_key[pair[side + '_set_key']]['source_file']), 'canonical_file': None}
                for side in ('a', 'b')}, 'realized_argv': [], 'environment': {}, 'returncode': None,
            'started_at': None, 'finished_at': None, 'stdout': None if uninvoked else identity(raw, 'bedtools_intersect_wo_bed4_v1'),
            'stderr': None, 'writer_closed': None, 'capture_extent': 'complete' if raw is not None or analytic else 'unavailable',
            'issues': [], 'native_result_extent': 'complete' if raw is not None or analytic else 'unavailable',
            'completeness_basis': 'validated_empty_input' if analytic else 'unavailable' if uninvoked else 'supplied_full_output_declaration',
            'completeness_source_refs': ['synthetic:complete-table'] if not uninvoked else []}


def parsed_pairs(request, sets, raw, *, changes=None, derivation='supplied_native_output', pair_index=0):
    pair = request['comparisons'][pair_index]
    metadata = receipt(pair, sets, raw, derivation=derivation)
    metadata.update(deepcopy(changes or {}))
    return parse_bedtools_intersect_wo(raw, pair=pair, sets={s['set_key']: s for s in sets}, native=metadata)


def sheet_from(request, sets, pairs):
    references = extract_overlap_reference_metadata(specifications=request['region_sets'],
        sets={s['set_key']: s for s in sets}, comparisons=request['comparisons'])
    return build_genomic_overlap_sheet(request=request, sets=sets, native_pairs=pairs, reference_relations=references)


def make_sheet(a, b, native, *, references=None, formats=None, changes=None, derivation='supplied_native_output'):
    request, sets = inputs([a, b], formats=formats, references=references)
    pair = parsed_pairs(request, sets, native, changes=changes, derivation=derivation)
    return sheet_from(request, sets, [pair])


def reference(assembly=None, *, label=None, contigs=()):
    return {'assembly_accession_version': assembly, 'assembly_label': label,
            'sequence_dictionary': None, 'contigs': list(contigs), 'source_refs': ['synthetic:reference']}


def contig(length=None, accession=None, sha=None):
    return {'chromosome': 'chr1', 'length_bp': length, 'sequence_accession_version': accession,
            'sequence_sha256': sha, 'source_refs': ['synthetic:contig']}


def test_reviewed_schema_definitions_and_worked_records():
    original = json.loads((PACKET / 'DATA_CONTRACT.json').read_text())
    assert genomic_overlap_schema('Sheet')['$defs'] == original['$defs']
    for field, name in WORKED['schemas'].items():
        values = WORKED[field] if name.endswith('[]') else [WORKED[field]]
        for value in values:
            assert validate_genomic_overlap_record(name.removesuffix('[]'), value) == value
    assert canonical_genomic_overlap_sheet_sha256(WORKED['sheet']) == WORKED['components']['source_sheet_sha256']


@pytest.mark.parametrize('change', [
    lambda x: x.update(extra=1), lambda x: x.update(minimum_overlap_bp=True),
    lambda x: x.update(minimum_overlap_bp=1.0), lambda x: x.update(minimum_overlap_bp=float('nan')),
    lambda x: x['minimum_a_fraction'].update(denominator=float('inf')),
])
def test_schema_is_strict_finite_and_closed(change):
    value = deepcopy(PARAMETERS)
    change(value)
    with pytest.raises(ValueError):
        validate_genomic_overlap_record('Parameters', value)


def test_schema_and_records_are_detached():
    value = validate_genomic_overlap_record('Parameters', PARAMETERS)
    value['minimum_a_fraction']['numerator'] = 1
    assert PARAMETERS['minimum_a_fraction']['numerator'] == 0
    schema = genomic_overlap_schema('Parameters')
    schema['$defs'].clear()
    assert genomic_overlap_schema('Parameters')['$defs']
    with pytest.raises(ValueError):
        genomic_overlap_schema('CallerFormula')


def test_exact_worked_input_pair_sheet_chain_and_supplied_output():
    raw = {r['key']: r['utf8_text'].encode() for r in WORKED['raw_artifacts']}
    request = WORKED['request']
    sets = [parse_region_set(io.BytesIO(raw[name]), specification=spec, set_position=i)
            for i, (name, spec) in enumerate(zip(('input_a', 'input_b'), request['region_sets']))]
    assert sets == WORKED['parsed_sets']
    parsed = parse_bedtools_intersect_wo(raw['native'], pair=request['comparisons'][0],
        sets={s['set_key']: s for s in sets}, native=WORKED['native_pair_metadata'])
    assert parsed == WORKED['parsed_pairs']
    assert sheet_from(request, sets, [parsed]) == WORKED['sheet']
    supplied = parse_bedtools_intersect_wo(raw['native'], pair=request['comparisons'][0],
        sets={s['set_key']: s for s in sets}, native=WORKED['supplied_output_metadata_example'])
    assert supplied['result_extent'] == 'complete'
    assert supplied['receipt']['identity'] is None
    assert supplied['receipt']['returncode'] is None


def test_headers_variable_width_duplicates_and_original_sort_identity():
    raw = b'# source\n\ntrack name=x\nbrowser position chr1\nchr2\t20\t30\tsame\nchr1\t5\t10\tsame\t7\t+\nchr1\t5\t10\tsame\t7\t+\nchr1\t0\t3\n'
    _, sets = inputs([raw, b''])
    a = sets[0]
    assert a['result_extent'] == 'complete'
    assert a['input_data_row_count'] == 4
    assert [r['kind'] for r in a['ignored_records']] == ['comment', 'blank', 'track_header', 'browser_header']
    assert a['canonical_order'] == ['r3', 'r1', 'r2', 'r0']
    assert [r['native_token'] for r in a['regions']] == ['s0_r0', 's0_r1', 's0_r2', 's0_r3']
    assert a['coordinate_groups'][1]['occurrence_keys'] == ['r1', 'r2']
    assert a['full_record_groups'][1]['occurrence_keys'] == ['r1', 'r2']
    assert a['regions'][0]['name'] == a['regions'][1]['name'] == 'same'
    for record in a['regions']:
        loc = record['locator']
        assert raw[loc['byte_start']:loc['byte_end']].endswith(b'\n')


def test_coordinate_array_extra_json_values_and_invalid_ordinal_survive():
    raw = json.dumps([['chr1', 4, 8, {'extra': True}, None, 1], ['chr1', True, 8],
                      ['chr1', 0, 3, 'name', 42, '-'], ['chr1', 0, 3, 'name', 42, '-', {'a': 1}]]).encode()
    _, sets = inputs([raw, b'[]'], formats=['coordinate_rows_v1'] * 2)
    a = sets[0]
    assert a['result_extent'] == 'partial' and a['input_data_row_count'] == 4
    assert [r['occurrence_key'] for r in a['regions']] == ['r0', 'r2', 'r3']
    assert a['regions'][0]['original_fields'][3] == {'extra': True}
    assert a['regions'][0]['name'] is None and a['regions'][0]['raw_strand'] is None
    assert a['regions'][1]['raw_strand'] == '-'
    assert a['invalid_records'][0]['locator'] == {'kind': 'array_index', 'index': 1}
    assert a['coordinate_groups'][1]['occurrence_keys'] == ['r2', 'r3']
    assert len(a['full_record_groups']) == 3


@pytest.mark.parametrize('line,code', [
    (b'chr1\t-1\t2\n', 'invalid_coordinate'), (b'chr1\t1.0\t2\n', 'invalid_coordinate'),
    (b'chr1\t2\t2\n', 'zero_width_interval'), (b'chr1\t3\t2\n', 'invalid_coordinate'),
    (b'chr1\t0\t9223372036854775808\n', 'invalid_coordinate'),
    (b'chr 1\t0\t2\n', 'invalid_chromosome_token'), (b'chr\x00\t0\t2\n', 'invalid_chromosome_token'),
    (b'chr1 0 2\n', 'unsupported_input_format'), (b'\xff\t0\t2\n', 'unsupported_input_format'),
])
def test_invalid_input_does_not_become_complete_empty(line, code):
    request, sets = inputs([line + b'chr1\t5\t7\n', b''])
    a = sets[0]
    assert a['result_extent'] == 'partial' and a['input_data_row_count'] == 2
    assert a['regions'][0]['occurrence_key'] == 'r1'
    assert code in {i['code'] for i in a['invalid_records'][0]['issues']}
    assert a['invalid_records'][0]['locator']['line_number'] == 1


def test_missing_empty_short_changed_and_oversize_bytes_are_distinct():
    request, sets = inputs([b'chr1\t0\t3\nchr1\t5\t7\n', b''])
    spec = request['region_sets'][0]
    assert sets[1]['result_extent'] == 'complete'
    missing = parse_region_set(None, specification=spec, set_position=0)
    assert missing['result_extent'] == 'unavailable' and missing['input_data_row_count'] is None
    short = parse_region_set(b'chr1\t0\t3\nchr1\t5', specification=spec, set_position=0)
    assert short['result_extent'] == 'partial' and short['input_data_row_count'] is None
    assert [r['occurrence_key'] for r in short['regions']] == ['r0']
    changed = parse_region_set(b'chr1\t1\t3\nchr1\t5\t7\n', specification=spec, set_position=0)
    assert changed['result_extent'] == 'partial' and changed['input_data_row_count'] == 2
    assert changed['issues'][0]['code'] == 'input_digest_mismatch'
    excess = parse_region_set(b'chr1\t0\t3\nchr1\t5\t7\nmore', specification=spec, set_position=0)
    assert excess['result_extent'] == 'unavailable' and excess['parsed_byte_count'] == 0


def test_json_partial_prefix_and_stream_failure_retain_whole_rows():
    full = b'[["chr1",0,5],["chr1",8,10]]'
    request, _ = inputs([full, b'[]'], formats=['coordinate_rows_v1'] * 2)
    parsed = parse_region_set(full[:-4], specification=request['region_sets'][0], set_position=0)
    assert parsed['result_extent'] == 'partial' and parsed['input_data_row_count'] is None
    assert len(parsed['regions']) == 1
    class Broken:
        first = True
        def read(self, size):
            if self.first:
                self.first = False
                return b'[["chr1",0,5],'
            raise OSError('synthetic broken supplied stream')
    parsed = parse_region_set(Broken(), specification=request['region_sets'][0], set_position=0)
    assert len(parsed['regions']) == 1 and parsed['result_extent'] == 'partial'
    with pytest.raises(ValueError):
        parse_region_set(io.StringIO('[]'), specification=request['region_sets'][0], set_position=0)


ROW = b'chr1\t0\t10\ts0_r0\tchr1\t7\t12\ts1_r0\t3\n'


@pytest.mark.parametrize('bad,code', [
    (ROW.replace(b'\t3\n', b'\t4\n'), 'overlap_width_conflict'),
    (ROW.replace(b's0_r0', b'foreign'), 'native_pair_identity_conflict'),
    (ROW.replace(b'chr1\t0\t10', b'chr1\t1\t10'), 'native_pair_identity_conflict'),
    (ROW.replace(b'\t3\n', b'\tbad\n'), 'native_output_malformed'),
    (ROW.replace(b'\t3\n', b'\t3\textra\n'), 'native_output_malformed'),
    (ROW, 'duplicate_native_pair'),
])
def test_native_invalid_rows_are_located_and_valid_subset_retained(bad, code):
    request, sets = inputs([b'chr1\t0\t10\n', b'chr1\t7\t12\n'])
    result = parsed_pairs(request, sets, ROW + bad)
    assert result['result_extent'] == 'partial' and len(result['valid_pairs']) == 1
    failure = next(i for i in result['rejected_rows'][0]['issues'] if i['code'] == code)
    assert failure['locator']['line_number'] == 2
    assert failure['locator']['byte_start'] == len(ROW)
    if code == 'overlap_width_conflict':
        assert failure['observed_value'] == 4 and failure['expected_value'] == 3


@pytest.mark.parametrize('changes', [
    {'returncode': 1, 'outcome': 'failed'}, {'writer_closed': False},
    {'native_result_extent': 'partial', 'completeness_basis': 'partial_native_result'},
    {'capture_extent': 'partial'}, {'completeness_source_refs': []},
])
def test_unproven_empty_native_table_does_not_become_no_hit(changes):
    request, sets = inputs([b'chr1\t0\t10\n', b'chr1\t10\t20\n'])
    result = parsed_pairs(request, sets, b'', changes=changes)
    assert result['result_extent'] == 'partial'
    assert result['issues']


def test_missing_native_table_and_changed_digest_are_not_empty_success():
    request, sets = inputs([b'chr1\t0\t10\n', b'chr1\t7\t12\n'])
    pair = request['comparisons'][0]
    native = receipt(pair, sets, ROW)
    missing = parse_bedtools_intersect_wo(None, pair=pair, sets={s['set_key']: s for s in sets}, native=native)
    assert missing['result_extent'] == 'unavailable'
    native['stdout']['sha256'] = '0' * 64
    changed = parse_bedtools_intersect_wo(ROW, pair=pair, sets={s['set_key']: s for s in sets}, native=native)
    assert changed['result_extent'] == 'partial' and len(changed['valid_pairs']) == 1
    assert changed['issues'][0]['code'] == 'artifact_digest_mismatch'


def test_analytic_empty_has_no_native_artifact():
    request, sets = inputs([b'', b'chr1\t0\t10\n'])
    parsed = parsed_pairs(request, sets, None, derivation='validated_empty_input')
    assert parsed['result_extent'] == 'complete' and parsed['receipt']['stdout'] is None
    sheet_from(request, sets, [parsed])
    request2, sets2 = inputs([b'chr1\t0\t10\n', b'chr1\t0\t10\n'])
    with pytest.raises(ValueError, match='analytic_empty'):
        parsed_pairs(request2, sets2, None, derivation='validated_empty_input')


@pytest.mark.parametrize('references,expected', [
    ([None, None], 'unknown'),
    ([reference(label='assembly'), reference(label='assembly')], 'unknown'),
    ([reference('GCF_000001.1'), reference('GCF_000001.1')], 'same_supplied_reference'),
    ([reference('GCF_000001.1'), reference('GCF_000001.2')], 'different_supplied_references'),
    ([reference('GCF_000001.1', contigs=[contig(20)]), reference('GCF_000001.1', contigs=[contig(21)])], 'conflicting_metadata'),
    ([reference(contigs=[contig(20, 'NC_001.1')]), reference(contigs=[contig(20, 'NC_001.1')])], 'same_supplied_reference'),
    ([reference(contigs=[contig(5)]), None], 'conflicting_metadata'),
])
def test_reference_qualification_preserves_geometry_inputs(references, expected):
    sheet = make_sheet(b'chr1\t0\t10\n', b'chr1\t7\t12\n', ROW, references=references)
    assert sheet['reference_relations'][0]['relation'] == expected
    assert sheet['comparisons'][0]['result_extent'] == 'complete'
    assert sheet['sets'][0]['regions'][0]['end'] == 10
    if expected == 'conflicting_metadata':
        assert sheet['reference_relations'][0]['issues']


def test_invalid_third_set_keeps_independent_valid_pair():
    request, sets = inputs([b'chr1\t0\t10\n', b'chr1\t7\t12\n', b'chr1\t3\t3\n'])
    pairs = [parsed_pairs(request, sets, ROW)]
    for index in (1, 2):
        pairs.append(parsed_pairs(request, sets, None, derivation='not_executed_invalid_input', pair_index=index))
    sheet = sheet_from(request, sets, pairs)
    assert [pair['result_extent'] for pair in sheet['comparisons']] == ['complete', 'unavailable', 'unavailable']
    assert sheet['sets'][2]['invalid_records'][0]['issues'][0]['code'] == 'zero_width_interval'


@pytest.mark.parametrize('mutation', [
    lambda s: s['sets'].reverse(),
    lambda s: s['sets'][0]['canonical_order'].reverse(),
    lambda s: s['sets'][0]['regions'][0].update(start=1),
    lambda s: s['sets'][0]['regions'][0].update(native_token='s3_r0'),
    lambda s: s['sets'][0]['coordinate_groups'][0]['occurrence_keys'].append('r1'),
    lambda s: s['comparisons'][0]['valid_pairs'][0].update(native_overlap_bp=4),
    lambda s: s['comparisons'][0]['valid_pairs'][0]['a'].update(set_key='B'),
    lambda s: s['comparisons'][0]['receipt']['a']['original_file'].update(sha256='0' * 64),
    lambda s: s['request']['comparisons'][0].update(ordinal=1),
])
def test_builder_rejects_semantic_record_forgery(mutation):
    sheet = deepcopy(WORKED['sheet'])
    mutation(sheet)
    with pytest.raises(ValueError):
        build_genomic_overlap_sheet(request=sheet['request'], sets=sheet['sets'],
            native_pairs=sheet['comparisons'], reference_relations=sheet['reference_relations'])


def test_saved_input_outputs_are_detached():
    request = deepcopy(WORKED['request'])
    sets = deepcopy(WORKED['parsed_sets'])
    pairs = [deepcopy(WORKED['parsed_pairs'])]
    sheet = sheet_from(request, sets, pairs)
    sheet['sets'][0]['regions'][0]['original_fields'][0] = 'changed'
    assert sets[0]['regions'][0]['original_fields'][0] == 'chr1'
    assert request == WORKED['request']


def test_untouched_retained_native_tokens_are_explicitly_incompatible():
    native_root = ROOT / 'verification/tool_graders_genomic_overlap_native_2026-10-27_421/run002/work'
    a, b = [(native_root / f'overlapping_a.{side}.bed').read_bytes() for side in ('A', 'B')]
    raw = (native_root / 'overlapping_a.stdout').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '363d108caac15ca99a4850892b890693fd2b9f1b9d16e41c9a566e05cecf9edb'
    request, sets = inputs([a, b])
    parsed = parsed_pairs(request, sets, raw)
    assert not parsed['valid_pairs'] and parsed['result_extent'] == 'partial'
    assert {i['code'] for i in parsed['issues']} == {'native_pair_identity_conflict'}


def test_coordinate_rows_reject_structurally_valid_ignored_bed_record():
    request, sets = inputs([b'[]', b'[]'], formats=['coordinate_rows_v1'] * 2)
    sets[0]['ignored_records'].append({'kind':'blank','locator':{'kind':'array_index','index':0}})
    with pytest.raises(ValueError,match='no_bed_headers'):
        extract_overlap_reference_metadata(specifications=request['region_sets'],
            sets={s['set_key']:s for s in sets},comparisons=request['comparisons'])


def test_supplied_canonical_identity_is_checked_without_requiring_one():
    raw = next(r['utf8_text'].encode() for r in WORKED['raw_artifacts'] if r['key']=='native')
    native = deepcopy(WORKED['supplied_output_metadata_example'])
    native['a']['canonical_file']['sha256'] = '0' * 64
    result = parse_bedtools_intersect_wo(raw,pair=WORKED['request']['comparisons'][0],
        sets={s['set_key']:s for s in WORKED['parsed_sets']},native=native)
    assert result['result_extent'] == 'partial' and len(result['valid_pairs']) == 2
    issue = result['issues'][0]
    assert issue['code'] == 'artifact_digest_mismatch'
    assert issue['field_path'] == '/receipt/a/canonical_file/sha256'
    sheet_from(WORKED['request'],WORKED['parsed_sets'],[result])
    forged = deepcopy(WORKED['parsed_pairs'])
    forged['receipt']['a']['canonical_file']['sha256'] = '0' * 64
    with pytest.raises(ValueError,match='canonical_file_identity'):
        sheet_from(WORKED['request'],WORKED['parsed_sets'],[forged])


def test_saved_bed_locations_partition_parsed_bytes():
    sets = deepcopy(WORKED['parsed_sets'])
    sets[0]['regions'][1]['locator']['byte_start'] = 20
    with pytest.raises(ValueError,match='location_partition'):
        sheet_from(WORKED['request'],sets,[WORKED['parsed_pairs']])


@pytest.mark.parametrize('argv', [
    ['bedtools','intersect','-a','A','-b','B','-wo'],
    ['/supplied/bin/bedtools','intersect','-wo','-b','B','-sorted','-a','A'],
    ['/supplied/bin/intersectBed','-b','B','-wo','-a','A'],
])
def test_supplied_equivalent_invocation_order_and_unsorted_are_compatible(argv):
    request, sets = inputs([b'chr1\t0\t10\n',b'chr1\t7\t12\n'])
    parsed = parsed_pairs(request,sets,ROW,changes={'realized_argv':argv})
    assert parsed['result_extent'] == 'complete' and not parsed['issues']
    sheet_from(request,sets,[parsed])


@pytest.mark.parametrize('tail', [
    ['-s'],['-split'],['-f','0.5'],['-F','0.1'],['-r'],['-unknown'],['-a','other'],
])
def test_explicit_native_restrictions_are_partial_without_discarding_rows(tail):
    argv = ['bedtools','intersect','-a','A','-b','B','-wo'] + tail
    request, sets = inputs([b'chr1\t0\t10\n',b'chr1\t7\t12\n'])
    parsed = parsed_pairs(request,sets,ROW,changes={'realized_argv':argv})
    assert parsed['result_extent'] == 'partial' and len(parsed['valid_pairs']) == 1
    failure = parsed['issues'][0]
    assert failure['code'] == 'unsupported_input_format' and failure['stage'] == 'parse'
    assert failure['field_path'] == '/receipt/realized_argv'
    assert failure['expected_value'] == 'unstranded_outer_span' and failure['observed_value'] == argv
    sheet_from(request,sets,[parsed])
