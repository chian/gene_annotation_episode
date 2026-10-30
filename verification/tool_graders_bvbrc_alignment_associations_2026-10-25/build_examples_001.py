"""Build complete, explicitly classified association examples; run no native job."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from test_bvbrc_alignment_associations import common_fixture, transformed_fixture, value_of, binding, evidence, artifact
from test_bvbrc_metacats_associations import metacats_fixture, auto_fixture, groups_fixture, comma_pair_fixture, native_fixture
from gene_annotation_episode import bvbrc_alignment_provider_contracts as ac
from gene_annotation_episode import bvbrc_metacats_association_contracts as mc
from gene_annotation_episode.bvbrc_alignment_associations import extract_alignment_associations, extract_inline_fasta_members
from gene_annotation_episode.bvbrc_metacats_associations import extract_metacats_associations
from gene_annotation_episode.bvbrc_metacats_biological_calculators import biological_group_counts
from gene_annotation_episode.bvbrc_msa_calculators import msa_native_entropy, msa_reference_differences


def population(alignment):
    return {'population_id': 'all-physical-rows-and-columns', 'alignment_id': alignment['alignment_id'],
        'row_indices': [r['row_index'] for r in alignment['rows']],
        'columns_0based': list(range(alignment['observed_column_count'])), 'completeness': 'complete', 'evidence': []}


def calculation(name, alignment, arguments):
    function = {'biological_group_counts': biological_group_counts, 'msa_native_entropy': msa_native_entropy,
        'msa_reference_differences': msa_reference_differences}[name]
    result = function(alignment, **arguments)
    return {'function': name, 'alignment': alignment, 'arguments': arguments, 'result': result}


EXAMPLES = []


def add(name, groups, common, meta=None, source_status='synthetic', native_case=None):
    record = {'name': name, 'required_example_groups': groups, 'source_status': source_status,
        'native_executed_this_workload': False, 'native_execution_case': native_case,
        'common_operands': deepcopy(common), 'common_result': extract_alignment_associations(**common),
        'metacats_operands': deepcopy(meta), 'metacats_result': None, 'calculations': [], 'downstream_operands': {}}
    if meta is not None:
        assert meta['associations'] == record['common_result']['value'], name
        record['metacats_result'] = result = extract_metacats_associations(**meta)
        if result['value'] is not None:
            al = next(d['value'] for d in meta['documents'] if d['kind'] == 'alignment' and d['value']['alignment_id'] == meta['analysis']['alignment_id'])
            for pop in result['value']['biological_group_populations']:
                category = pop['category_id']
                record['calculations'].append(calculation('biological_group_counts', al, {
                    'analysis_id': meta['analysis']['analysis_id'], 'population': population(al), 'category_id': category,
                    'assignments': [r for r in result['value']['biological_assignments'] if r['category_id'] == category],
                    'group_population': pop, 'case_policy': 'preserve', 'terminal_gap_policy': 'exclude_terminal_dash',
                    'original_hash_policy': 'exclude_hash'}))
    EXAMPLES.append(record)
    return record


for alphabet, data in [('dna', '>a\nAC\n>b\nAT\n'), ('protein', '>a\nMK\n>b\nML\n')]:
    operands = common_fixture(data, molecule=alphabet)
    rec = add('unique_' + alphabet, [1], operands)
    al = operands['documents'][-1]['value']
    rec['calculations'].append(calculation('msa_native_entropy', al, {'analysis_id': 'analysis', 'population': population(al),
        'alphabet': alphabet, 'case_policy': 'uppercase', 'terminal_gap': '-', 'observed_table': None,
        'native_rounding': 'binary64_fixed_2_ties_to_even'}))

operands = common_fixture()
for row in operands['documents'][-1]['value']['rows']:
    for column in range(len(row['sequence'])):
        operands['declarations']['common']['correspondences'].append({'alignment_id': 'aligned#alignment', 'row_index': row['row_index'],
            'column_0based': column, 'staged_ungapped_position_0based': column,
            'original_member': {'input_binding_id': 'original', 'member_id': row['member_label']},
            'original_interval_0based_half_open': [column, column + 1], 'strand': '+', 'translation_table': None,
            'transformation_id': None, 'evidence': [evidence('synthetic-identity-map')]})
rec = add('explicit_reference_identity', [1], operands)
al = operands['documents'][-1]['value']
reference = {'alignment_id': al['alignment_id'], 'row_index': 0, 'original_member': {'input_binding_id': 'original', 'member_id': 'a'},
    'native_ref_type': 'string', 'native_ref_string': '>a\nAC\n', 'identity_state': 'resolved', 'evidence': [evidence('synthetic-reference')]}
rec['downstream_operands']['reference'] = reference
rec['calculations'].append(calculation('msa_reference_differences', al, {'analysis_id': 'analysis', 'population': population(al),
    'reference': reference, 'member_row_indices': [1], 'alphabet': 'dna', 'case_policy': 'preserve',
    'original_correspondences': rec['common_result']['value']['correspondences']}))

operands = transformed_fixture()
rec = add('reverse_translation_concatenation', [1], operands)
keys = [m['key'] for m in rec['common_result']['value']['original_members']]
rec['downstream_operands']['segments'] = [{'segment_id': label, 'native_segment_token': label,
    'genome_id': None, 'genome_sequence_record_id': None, 'contig_id': None,
    'original_interval_0based_half_open': interval, 'strand': strand, 'input_member': key,
    'alignment_id': 'aligned#alignment', 'concatenated_interval_0based_half_open': output,
    'order_index': index, 'state': 'resolved', 'evidence': [evidence('synthetic-segment-map')]}
    for index, (label, interval, strand, key, output) in enumerate([('a', [0, 6], '-', keys[0], [0, 2]), ('b', [0, 3], '+', keys[1], [2, 3])])]

add('duplicate_physical_headers', [1, 8], common_fixture('>same\nAC\n>same\nAT\n'))
operands = common_fixture('>one\nAC\n>two\nAC\n', '>x\nAC\n>y\nAC\n')
operands['declarations']['common']['automatic_row_joins'][0]['method'] = 'exact_unique_sequence'
add('identical_sequences_ambiguous', [1, 8], operands)

inline = 'orphan\n>same details\r\nac g\r\ntt\n>same details\nAé\n>\nA!\n>empty\n'
operands = common_fixture(inline, output='>x\nA\n', inline=True)
operands['declarations']['common']['input_sequences'][0]['encoding'] = 'ascii'
rec = add('inline_full_text_and_physical_occurrences', [2], operands)
rec['downstream_operands']['inline_extraction'] = {'binding': operands['inputs'][0],
    'arguments': {'id_rule': 'first_whitespace_token', 'encoding': 'ascii', 'molecule': 'dna'},
    'result': extract_inline_fasta_members(operands['inputs'][0], id_rule='first_whitespace_token', encoding='ascii', molecule='dna')}

meta, common = metacats_fixture()
add('files_biology_without_r', [3, 4], common, meta)
for conflict, fetched in [(False, True), (True, True), (True, False)]:
    meta = auto_fixture(conflict=conflict, fetched=fetched)
    add('auto_' + ('conflict' if conflict else 'same_group') + ('_unfetched' if not fetched else ''), [3, 4], common_fixture(), meta)
for merged in (False, True):
    meta, common = groups_fixture(merged)
    add('groups_shared_feature_' + ('declared_overwrite' if merged else 'conflict'), [3, 4], common, meta)

meta, common = metacats_fixture(meta='id\tgroup\tgroup\na\t\tA,B\nb\tC\n', categories=('first', 'second'))
add('multiple_categories_blank_present_absent_comma', [7, 8], common, meta)
meta, common = metacats_fixture(meta='id\tgroup\na\tX\na\tY\nb\tZ\nunmatched\tA\n')
meta['declarations']['biological_group_populations'][0]['include_metadata_only'] = False
add('duplicate_metadata_ids_partial', [7, 8], common, meta)
for ambiguous in (False, True):
    meta, common = comma_pair_fixture(ambiguous)
    add('whole_comma_pair_' + ('ambiguous' if ambiguous else 'resolved'), [7, 8], common, meta)
meta, common = metacats_fixture(data='>a\nA#-\n>b\nAC-\n')
add('original_hash_and_terminal_dash_distinct', [7], common, meta)

for case, groups in [('metadata_only_first_group', [5]), ('twelve_groups', [6])]:
    meta, common = native_fixture(case)
    rec = add('retained_native_' + case, groups, common, meta,
        source_status='retained_native_execution_on_synthetic_original_sequences', native_case=case)
    rec['prior_execution_receipt'] = 'verification/tool_graders_bvbrc_metacats_native_execution_2026-10-25/NATIVE_RUNS_001.json'
    if case == 'metadata_only_first_group':
        failed = deepcopy(meta)
        failed['declarations']['native_group_maps'] = []
        failed['declarations']['r_columns'] = []
        failed['declarations']['exported_group_joins'] = []
        add('retained_native_no_r_identity', [5, 8], common, failed,
            source_status='retained_native_execution_with_deliberately_omitted_identity_evidence', native_case=case)

for label in ('wrong_original_content', 'wrong_version', 'foreign_transform'):
    operands = transformed_fixture() if label == 'foreign_transform' else common_fixture()
    if label == 'wrong_original_content':
        operands['inputs'][0]['content']['sha256'] = '0' * 64
    elif label == 'wrong_version':
        operands['declarations']['common']['version'] = 'unaccepted-version'
    else:
        operands['declarations']['common']['correspondences'][0]['transformation_id'] = 'foreign'
    rec = add('invalid_' + label, [7, 8], operands)
    assert rec['common_result']['status'] == 'invalid'

for label in ('category', 'row_member', 'original_metadata', 'source', 'r_version'):
    if label == 'source':
        meta, common = groups_fixture()
        meta['declarations']['group_sources'][0]['bindings'][0]['source_record_id'] = 'foreign'
    elif label == 'r_version':
        meta, common = comma_pair_fixture()
        meta['declarations']['r_columns'][0]['interpreter_version'] = ''
    else:
        meta, common = metacats_fixture()
        if label == 'category':
            meta['declarations']['categories'][0]['category_id'] = 'foreign'
        elif label == 'row_member':
            meta['declarations']['explicit_memberships'] = [{'category_id': 'category', 'alignment_id': 'aligned#alignment',
                'row_index': 0, 'member_key': meta['associations']['original_members'][1]['key'],
                'group_id': mc.group_id('category', 'B'), 'state': 'resolved', 'evidence': []}]
        else:
            meta['declarations']['metadata_joins'][0]['metadata'] = 'unrelated-original-metadata'
    rec = add('invalid_metacats_' + label, [7, 8], common, meta)
    assert rec['metacats_result']['status'] == 'invalid'

directory = OUT / 'EXAMPLES_001'
directory.mkdir(exist_ok=True)
manifest = []
for record in EXAMPLES:
    payload = (json.dumps(record, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
    path = directory / (record['name'] + '.json')
    assert not path.exists(), 'Add a new version instead of replacing saved examples'
    path.write_bytes(payload)
    manifest.append({'name': record['name'], 'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(payload).hexdigest(),
        'byte_count': len(payload), 'groups': record['required_example_groups'], 'source_status': record['source_status']})
(OUT / 'EXAMPLE_MANIFEST_001.json').write_text(json.dumps({'examples': manifest, 'native_jobs_run': 0,
    'scope': 'Pure extraction and existing calculators only; original request authentication remains adapter-owned.'}, indent=2) + '\n')
print(json.dumps({'examples_written': len(EXAMPLES), 'complete_serialized_bytes': sum(x['byte_count'] for x in manifest), 'native_jobs_run': 0}))
