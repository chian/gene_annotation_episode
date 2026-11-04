"""Biological membership is independently useful without native R identity."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.bvbrc_metacats_associations import extract_metacats_associations
from gene_annotation_episode import bvbrc_metacats_association_contracts as c
from gene_annotation_episode.bvbrc_metacats_formats import parse_metacats_metadata, parse_metacats_adjusted_matrix, parse_metacats_chisq_table, parse_metacats_pair_table, parse_metacats_raw_r_table
from gene_annotation_episode.bvbrc_metacats_biological_calculators import biological_group_counts
from test_bvbrc_alignment_associations import artifact, evidence, common_fixture, value_of, forbid_io, binding, alignment


def metadata(text, name='metadata'):
    raw = text.encode(); parsed = parse_metacats_metadata(raw, artifact=artifact(raw, name), delimiter='tab', header='present', encoding='utf-8')
    assert parsed['value'] is not None, parsed
    return {'kind': 'metadata', 'value': parsed['value']}


def metacats_fixture(data='>a\nAC\n>b\nAT\n', meta='id\tgroup\na\tB\nb\tC\n', categories=('category',)):
    original = common_fixture(data); associations = value_of(original)
    md = metadata(meta); documents = original['documents'] + (md,)
    analysis = {'analysis_id': 'analysis', 'mode': 'files', 'alignment_id': 'aligned#alignment',
        'metadata_document_id': md['value']['document_id'], 'category_ids': list(categories), 'adjusted_matrix_ids': [],
        'chisq_table_ids': [], 'pair_table_ids': [], 'raw_r_table_ids': [], 'output_role_evidence': []}
    declarations = {'version': 'bvbrc_metacats_context_v1', 'analysis_id': 'analysis',
        'metadata_joins': [{'metadata': md['value']['document_id'], 'id_column_index_0based': 0, 'alignment': 'aligned#alignment',
            'alignment_identity': 'member_label', 'case_policy': 'preserve', 'duplicate_policy': 'retain_unresolved', 'evidence': []}],
        'categories': [{'category_id': cat, 'metadata': md['value']['document_id'], 'metadata_column_index_0based': i + 1,
            'raw_heading_token': md['value']['header_tokens'][i + 1], 'native_category_ordinal_1based': i + 1,
            'native_output_stem': cat, 'input_mode': 'files', 'group_identity_rule': 'exact_category_value', 'evidence': []} for i, cat in enumerate(categories)],
        'explicit_memberships': [], 'auto_group_entries': [], 'group_sources': [],
        'biological_group_populations': [{'kind': 'observed_metadata_groups', 'group_population_id': cat + '-groups', 'category_id': cat,
            'order': 'first_metadata_occurrence', 'include_metadata_only': True, 'evidence': []} for cat in categories],
        'native_group_maps': [], 'r_columns': [], 'exported_group_joins': [], 'native_test_joins': []}
    return {'analysis': analysis, 'documents': documents, 'associations': associations, 'declarations': declarations}, original


def extracted(operands):
    result = extract_metacats_associations(**operands)
    assert result['value'] is not None, result
    return result['value']


def counts(operands, result, category='category'):
    alignment = next(d['value'] for d in operands['documents'] if d['kind'] == 'alignment' and d['value']['alignment_id'] == operands['analysis']['alignment_id'])
    population = {'population_id': 'all', 'alignment_id': alignment['alignment_id'], 'row_indices': list(range(len(alignment['rows']))),
        'columns_0based': list(range(alignment['observed_column_count'])), 'completeness': 'complete', 'evidence': []}
    return biological_group_counts(alignment, analysis_id='analysis', population=population, category_id=category,
        assignments=tuple(r for r in result['biological_assignments'] if r['category_id'] == category),
        group_population=next(p for p in result['biological_group_populations'] if p['category_id'] == category),
        case_policy='preserve', terminal_gap_policy='exclude_terminal_dash', original_hash_policy='exclude_hash')


def test_biological_group_population_and_counts_do_not_require_r():
    operands, _ = metacats_fixture(); value = extracted(operands)
    assert [a['state'] for a in value['biological_assignments']] == ['resolved', 'resolved']
    assert value['native_group_columns'] == []
    assert [a['state'] for a in value['native_group_assignments']] == ['native_unlabeled', 'native_unlabeled']
    result = counts(operands, value)
    assert result['status'] == 'ok'
    assert result['sites'][1]['observed_counts'] == [[1, 0], [0, 1]]
    assert any(r['reason_code'] == 'native_r_column_identity_required' for r in value['requirements'])


def test_repeated_headings_blank_absent_commas_and_independent_categories():
    operands, _ = metacats_fixture(meta='id\tgroup\tgroup\na\t\tA,B\nb\tC\n', categories=('first', 'second'))
    value = extracted(operands)
    assert c.group_id('first', '') in [g['group_id'] for g in value['groups']]
    assert c.group_id('second', 'A,B') in [g['group_id'] for g in value['groups']]
    first = [r for r in value['biological_assignments'] if r['category_id'] == 'first']
    second = [r for r in value['biological_assignments'] if r['category_id'] == 'second']
    assert [r['state'] for r in first] == ['resolved', 'resolved']
    assert [r['state'] for r in second] == ['resolved', 'missing']
    assert all(g['group_id'] != c.group_id('second', '') for g in value['groups'])


def test_duplicate_metadata_ids_remain_unresolved_without_poisoning_other_rows():
    operands, _ = metacats_fixture(meta='id\tgroup\na\tB\na\tC\nb\tC\n')
    value = extracted(operands)
    assert [r['state'] for r in value['biological_assignments']] == ['conflicting', 'resolved']
    assert len(value['metadata_members']) == 3


def auto_fixture(conflict=True, fetched=True):
    operands, original = metacats_fixture()
    operands['analysis'].update(mode='auto', metadata_document_id=None)
    decl = operands['declarations']; decl['metadata_joins'] = []
    decl['categories'][0].update(metadata=None, metadata_column_index_0based=None, raw_heading_token=None, input_mode='auto')
    groups = ['same', 'other']
    decl['biological_group_populations'] = [{'kind': 'explicit', 'population': {'group_population_id': 'requested', 'category_id': 'category',
        'groups': [{'group_id': c.group_id('category', g), 'raw_group_value': g, 'evidence': []} for g in groups], 'completeness': 'complete', 'evidence': []}}]
    member = operands['associations']['original_members'][0]['key']
    decl['auto_group_entries'] = [{'input_binding_id': 'original-auto-request', 'entry_index_0based': i, 'original_parameter_pointer': f'/auto_groups/{i}',
        'feature_id': 'feature:one', 'raw_group_value': 'other' if conflict and i == 1 else 'same',
        'member_keys': [member] if fetched else [], 'evidence': [evidence('auto', f'/{i}')]} for i in range(2)]
    return operands


@pytest.mark.parametrize('conflict', [False, True])
def test_auto_duplicate_entries_keep_original_order_and_identity(conflict):
    operands = auto_fixture(conflict=conflict); value = extracted(operands)
    assert len(value['auto_group_entries']) == 2
    assert value['biological_assignments'][0]['state'] == ('conflicting' if conflict else 'resolved')
    assert operands['associations']['original_members'][0]['feature_ids'] == []
    assert value['biological_assignments'][1]['state'] == 'missing'


def test_auto_zero_fetched_members_retains_known_request_and_group_provenance():
    operands = auto_fixture(fetched=False); value = extracted(operands)
    assert len(value['auto_group_entries']) == 2
    assert all(row['state'] == 'missing' for row in value['biological_assignments'])
    assert any(r['reason_code'] == 'auto_fetched_sequence_association_required' for r in value['requirements'])


def test_explicit_conflict_is_evidence_but_duplicate_row_is_invalid():
    operands, _ = metacats_fixture(); key = operands['associations']['original_members'][0]['key']
    assignment = {'category_id': 'category', 'alignment_id': 'aligned#alignment', 'row_index': 0, 'member_key': key,
        'group_id': None, 'state': 'conflicting', 'evidence': []}
    operands['declarations']['explicit_memberships'] = [assignment]
    assert extracted(operands)['biological_assignments'][0]['state'] == 'conflicting'
    operands['declarations']['explicit_memberships'].append(deepcopy(assignment))
    assert extract_metacats_associations(**operands)['status'] == 'invalid'


def test_group_mode_uses_explicit_membership_and_keeps_original_resource_identity():
    operands = auto_fixture(False); operands['analysis']['mode'] = 'groups'
    decl = operands['declarations']; decl['categories'][0]['input_mode'] = 'groups'; decl['auto_group_entries'] = []
    operands['associations']['source_records'].append({'source_record_id': 'group-record', 'kind': 'parent_declaration', 'evidence': evidence('group')})
    decl['group_sources'] = [{'category_id': 'category', 'raw_group_value': 'same', 'bindings': [{'input_binding_id': 'requested-feature-groups',
        'group_id': '/real/workspace/group-A', 'source_record_id': 'group-record', 'evidence': [evidence('group')]}]}]
    decl['explicit_memberships'] = [{'category_id': 'category', 'alignment_id': 'aligned#alignment', 'row_index': 0,
        'member_key': operands['associations']['original_members'][0]['key'], 'group_id': c.group_id('category', 'same'), 'state': 'resolved', 'evidence': [evidence('group')]}]
    value = extracted(operands)
    assert value['groups'][0]['source_group_bindings'][0]['group_id'] == '/real/workspace/group-A'
    assert value['biological_assignments'][0]['state'] == 'resolved'


def test_saved_metadata_row_group_and_source_forgeries_are_rejected():
    operands, _ = metacats_fixture(); value = extracted(operands)
    for path in ('row', 'group', 'category', 'source'):
        bad = deepcopy(value)
        if path == 'row':
            bad['biological_assignments'][0]['row_index'] = 99
        elif path == 'group':
            bad['groups'][0]['raw_group_value'] = 'forged'
        elif path == 'category':
            bad['biological_assignments'][0]['category_id'] = 'foreign'
        else:
            bad['metadata_members'][0]['metadata_document_id'] = 'foreign'
        with pytest.raises(ValueError, match='bvbrc_metacats_association_'):
            c.validate_metacats_association_set(bad, **{k: operands[k] for k in ('analysis', 'documents', 'associations')})


def test_saved_replay_and_calculation_no_io(monkeypatch):
    operands, _ = metacats_fixture(); value = extracted(operands); before = counts(operands, value)
    saved = json.loads(json.dumps({'operands': operands, 'value': value}))
    forbid_io(monkeypatch)
    assert c.validate_metacats_association_set(saved['value'], **{k: saved['operands'][k] for k in ('analysis', 'documents', 'associations')}) == value
    assert extract_metacats_associations(**saved['operands'])['value'] == value
    assert counts(saved['operands'], saved['value']) == before


def native_fixture(case):
    root = Path(__file__).resolve().parents[1]
    base = Path('verification/tool_graders_bvbrc_metacats_native_execution_2026-10-25/cases') / case
    original_path = base / 'original.fasta'; source = (root / original_path).read_text()
    mdpath = base / 'metadata.tsv'; mdtext = (root / mdpath).read_text()
    operands, common_operands = metacats_fixture(source, mdtext, categories=('comparison',))
    doc = alignment(source, str(original_path)); inp = binding(source, str(original_path))
    decl = common_operands['declarations']['common']
    decl['input_sequences'][0].update(input_binding_id=str(original_path), document=doc['value']['alignment_id'])
    decl['automatic_row_joins'][0].update(alignment=doc['value']['alignment_id'], input_binding_ids=[str(original_path)])
    common_operands.update(inputs=(inp,), documents=(doc,))
    operands['associations'] = value_of(common_operands)
    md = metadata(mdtext, str(mdpath))
    operands['documents'] = (doc, md)
    operands['analysis'].update(alignment_id=doc['value']['alignment_id'], metadata_document_id=md['value']['document_id'])
    d = operands['declarations']; d['metadata_joins'][0].update(metadata=md['value']['document_id'], alignment=doc['value']['alignment_id'])
    d['categories'][0]['metadata'] = md['value']['document_id']
    for filename, kind, reader, extra in [
        ('output/comparison.txt', 'adjusted_matrix', parse_metacats_adjusted_matrix, {}),
        ('output/comparison-chisqTable.tsv', 'metacats_chisq', parse_metacats_chisq_table, {'layout': 'current_filtered_tsv'}),
        ('output/comparison-mcTable.tsv', 'metacats_pair', parse_metacats_pair_table, {'layout': 'current_filtered_tsv'}),
        ('output/retained_raw/comparison-chisqTable.txt', 'metacats_raw_r', parse_metacats_raw_r_table, {'layout': 'r_write_table_single_result_string', 'kind': 'omnibus'}),
        ('output/retained_raw/comparison-mcTable.txt', 'metacats_raw_r', parse_metacats_raw_r_table, {'layout': 'r_write_table_single_result_string', 'kind': 'pairwise'}),
    ]:
        path = base / filename; raw = (root / path).read_bytes()
        parsed = reader(raw, artifact=artifact(raw, str(path)), category_id='comparison', encoding='ascii', **extra)
        assert parsed['value'] is not None, parsed
        operands['documents'] += ({'kind': kind, 'value': parsed['value']},)
        field = {'adjusted_matrix': 'adjusted_matrix_ids', 'metacats_chisq': 'chisq_table_ids', 'metacats_pair': 'pair_table_ids', 'metacats_raw_r': 'raw_r_table_ids'}[kind]
        operands['analysis'][field].append(parsed['value'].get('document_id', parsed['value'].get('table_id')))
    old = root / 'verification/tool_graders_bvbrc_msa_metacats_implementation_2026-10-25' / ('EXAMPLES_002' if case == 'twelve_groups' else 'EXAMPLES_001') / (case + '-inputs.json')
    saved = json.loads(old.read_text()); columns = saved['counts_arguments']['group_order']
    native_map = []
    # These are the retained fixture's explicit metadata/native-ordinal
    # associations. The extractor never sorts metadata to construct R tokens.
    if case == 'metadata_only_first_group':
        native_map.append({'raw_group_value': 'A', 'native_group_ordinal': 1, 'group_id': c.group_id('comparison', 'A'), 'evidence': deepcopy(columns[0]['evidence'])})
    for col in columns:
        native_map.append({'raw_group_value': col['group_id'], 'native_group_ordinal': col['native_group_ordinal'],
            'group_id': c.group_id('comparison', col['group_id']), 'evidence': deepcopy(col['evidence'])})
    d['native_group_maps'] = [{'category_id': 'comparison', 'entries': native_map, 'completeness': 'complete', 'evidence': deepcopy(columns[0]['evidence'])}]
    d['r_columns'] = [{'category_id': 'comparison', 'adjusted_matrix': operands['analysis']['adjusted_matrix_ids'][0], 'interpreter_version': 'R 4.3.3',
        'columns': [{**{k: deepcopy(col[k]) for k in ('r_column_index_0based', 'r_group_token', 'native_group_ordinal', 'evidence')},
            'group_id': c.group_id('comparison', col['group_id'])} for col in columns], 'completeness': 'complete', 'evidence': deepcopy(columns[0]['evidence'])}]
    table = next(x['value'] for x in operands['documents'] if x['kind'] == 'metacats_chisq')
    for index, col in enumerate(columns):
        label = table['group_heading_tokens'][index]
        d['exported_group_joins'].append({'category_id': 'comparison', 'table_id': table['table_id'], 'heading_index_0based': index,
            'raw_heading_token': label, 'group_id': c.group_id('comparison', col['group_id']), 'r_column_index_0based': col['r_column_index_0based'],
            'state': 'resolved' if label == col['group_id'] else 'wrong_native_label', 'evidence': deepcopy(col['evidence'])})
    return operands, common_operands


def test_distinct_native_pairs_at_same_site_remain_resolved():
    operands, _ = native_fixture('twelve_groups'); value = extracted(operands)
    pairs = [r for r in value['native_test_associations'] if r['test_kind'] == 'pairwise']
    assert len(pairs) >= 2
    assert all(r['state'] in ('resolved', 'wrong_native_label') for r in pairs)
    assert len({tuple(sorted(r['r_columns_0based'])) for r in pairs}) > 1


def test_duplicate_native_site_and_pair_remains_unresolved():
    operands, _ = native_fixture('twelve_groups')
    wrapper = next(d for d in operands['documents'] if d['kind'] == 'metacats_raw_r' and d['value']['kind'] == 'pairwise')
    old_id = wrapper['value']['table_id']
    raw = b'"resultMC"\n"1" "MGC Multiple Comparison Result:\n Site1 \t 1 \t 1 \t 2 \n Site1 \t 1 \t 1 \t 2 \n Site1 \t 1 \t 1 \t 3 \n"\n'
    parsed = parse_metacats_raw_r_table(raw, artifact=artifact(raw, 'synthetic-duplicate-pair'), category_id='comparison',
        layout='r_write_table_single_result_string', kind='pairwise', encoding='ascii')
    assert parsed['value'] is not None, parsed
    wrapper['value'] = table = parsed['value']
    operands['analysis']['raw_r_table_ids'] = [table['table_id'] if tid == old_id else tid for tid in operands['analysis']['raw_r_table_ids']]
    value = extracted(operands)
    tests = [r for r in value['native_test_associations'] if r['table_id'] == table['table_id']]
    assert [r['state'] for r in tests[:2]] == ['missing', 'missing']
    assert any(r['state'] == 'resolved' for r in tests[2:])
    tests[0].update(state='resolved', column_0based=0, test_id='forged-unique-test')
    with pytest.raises(ValueError, match='native_test_identity_duplicate'):
        c.validate_metacats_association_set(value, **{k: operands[k] for k in ('analysis', 'documents', 'associations')})


def comma_pair_fixture(ambiguous=False):
    groups = ['A,B', 'C', 'A', 'B,C'] if ambiguous else ['A,B', 'C']
    operands, original = metacats_fixture(''.join(f'>s{i}\nA\n' for i in range(len(groups))),
        'id\tgroup\n' + ''.join(f's{i}\t{group}\n' for i, group in enumerate(groups)))
    raw = ('ID\tSite1\tGroup\n' + ''.join(f's{i}\tA\t{i + 1}\n' for i in range(len(groups)))).encode()
    parsed = parse_metacats_adjusted_matrix(raw, artifact=artifact(raw, 'synthetic-comma-matrix'), category_id='category', encoding='ascii')
    assert parsed['value'] is not None, parsed
    operands['documents'] += ({'kind': 'adjusted_matrix', 'value': parsed['value']},)
    operands['analysis']['adjusted_matrix_ids'] = [parsed['value']['document_id']]
    raw = ('Position\tChi-square_value\tP-value\tDegrees_of_freedom\tFewer_5\t' + '\t'.join(groups) + '\n').encode()
    parsed = parse_metacats_chisq_table(raw, artifact=artifact(raw, 'synthetic-comma-chisq'), category_id='category', layout='current_filtered_tsv', encoding='ascii')
    assert parsed['value'] is not None, parsed
    table = parsed['value']; operands['documents'] += ({'kind': 'metacats_chisq', 'value': table},)
    operands['analysis']['chisq_table_ids'] = [table['table_id']]
    raw = b'Position\tMultiple_comparison_p-value\tGroups\n1\t0.5\tA,B,C\n'
    parsed = parse_metacats_pair_table(raw, artifact=artifact(raw, 'synthetic-comma-pair'), category_id='category', layout='current_filtered_tsv', encoding='ascii')
    assert parsed['value'] is not None, parsed
    operands['documents'] += ({'kind': 'metacats_pair', 'value': parsed['value']},)
    operands['analysis']['pair_table_ids'] = [parsed['value']['table_id']]
    columns = [{'r_column_index_0based': i, 'r_group_token': str(i + 1), 'native_group_ordinal': i + 1,
        'group_id': c.group_id('category', group), 'evidence': [evidence('synthetic-comma-native-columns')]} for i, group in enumerate(groups)]
    operands['declarations']['r_columns'] = [{'category_id': 'category', 'adjusted_matrix': operands['analysis']['adjusted_matrix_ids'][0],
        'interpreter_version': 'synthetic-test-only', 'columns': columns, 'completeness': 'complete', 'evidence': [evidence('synthetic-comma-native-columns')]}]
    operands['declarations']['exported_group_joins'] = [{'category_id': 'category', 'table_id': table['table_id'], 'heading_index_0based': i,
        'raw_heading_token': group, 'group_id': c.group_id('category', group), 'r_column_index_0based': i, 'state': 'resolved',
        'evidence': [evidence('synthetic-comma-native-columns')]} for i, group in enumerate(groups)]
    return operands, original


@pytest.mark.parametrize('ambiguous', [False, True])
def test_comma_pair_uses_whole_string_and_unique_actual_identity(ambiguous):
    operands, _ = comma_pair_fixture(ambiguous); value = extracted(operands)
    pair = value['native_test_associations'][0]
    assert pair['raw_groups_token'] == 'A,B,C'
    assert pair['state'] == ('missing' if ambiguous else 'resolved')
    if not ambiguous:
        assert pair['group_ids'] == [c.group_id('category', 'A,B'), c.group_id('category', 'C')]


def groups_fixture(merged=False):
    operands = auto_fixture(False); original = common_fixture()
    operands['analysis']['mode'] = 'groups'; decl = operands['declarations']
    decl['categories'][0]['input_mode'] = 'groups'; decl['auto_group_entries'] = []
    ev = evidence('synthetic-requested-groups', '/both-groups/feature:one')
    common = original['declarations']['common']
    common['source_records'] = [{'source_record_id': 'shared-feature', 'kind': 'feature', 'evidence': ev},
        {'source_record_id': 'requested-groups', 'kind': 'parent_declaration', 'evidence': ev}]
    key = operands['associations']['original_members'][0]['key']
    common['member_entities'] = [{'member_key': key, 'subject': {'kind': 'feature', 'id': 'feature:one', 'source_record_id': 'shared-feature'}, 'evidence': [ev]}]
    if merged:
        ref = {'alignment_id': 'aligned#alignment', 'row_index': 0}
        common['automatic_row_joins'] = []
        common['transformations'] = [{'transformation_id': 'supplied-overwrite', 'kind': 'native_duplicate_merge',
            'input_members': [key], 'input_rows': [], 'output_rows': [ref], 'native_key': 'feature:one', 'rule': 'overwrite_last', 'evidence': [ev]}]
        common['row_joins'] = [{'association_id': 'merged', **ref, 'member_keys': [key], 'transformation_ids': ['supplied-overwrite'],
            'state': 'native_duplicate_merge', 'basis': 'transformation_record', 'evidence': [ev]}]
    operands['associations'] = value_of(original)
    decl['group_sources'] = [{'category_id': 'category', 'raw_group_value': group, 'bindings': [{'input_binding_id': 'requested-feature-groups',
        'group_id': '/workspace/' + group, 'source_record_id': 'requested-groups', 'evidence': [ev]}]} for group in ('same', 'other')]
    decl['explicit_memberships'] = [{'category_id': 'category', 'alignment_id': 'aligned#alignment', 'row_index': 0, 'member_key': key,
        'group_id': c.group_id('category', 'other') if merged else None, 'state': 'resolved' if merged else 'conflicting', 'evidence': [ev]}]
    return operands, original


@pytest.mark.parametrize('merged', [False, True])
def test_group_mode_shared_feature_keeps_conflict_or_supplied_merge(merged):
    operands, _ = groups_fixture(merged); value = extracted(operands)
    assert [g['source_group_bindings'][0]['group_id'] for g in value['groups']] == ['/workspace/same', '/workspace/other']
    assert value['biological_assignments'][0]['state'] == ('resolved' if merged else 'conflicting')


def test_actual_retained_native_wrong_exported_headings_keep_b_c_counts():
    operands, _ = native_fixture('metadata_only_first_group'); value = extracted(operands)
    assert [r['r_group_token'] for r in value['native_group_columns']] == ['2', '3']
    assert [r['group_id'] for r in value['native_group_columns']] == [c.group_id('comparison', 'B'), c.group_id('comparison', 'C')]
    assert [r['state'] for r in value['native_group_columns']] == ['wrong_native_label', 'wrong_native_label']
    assert [r['raw_heading_token'] for r in value['exported_groups']] == ['A', 'B', 'C']
    pairs = [r for r in value['native_test_associations'] if r['table_id'] in operands['analysis']['pair_table_ids']]
    assert pairs[0]['raw_groups_token'] == 'A,B' and pairs[0]['state'] == 'wrong_native_label'
    assert pairs[0]['group_ids'] == [c.group_id('comparison', 'B'), c.group_id('comparison', 'C')]
    numerical = counts(operands, value, 'comparison')
    assert numerical['sites'][1]['observed_counts'] == [[6, 0, 0], [0, 6, 0]]
    chisq = next(d['value'] for d in operands['documents'] if d['kind'] == 'metacats_chisq')
    assert chisq['rows'][0]['chi_square']['value'] == 8.33055648117294
    assert chisq['rows'][0]['p_value']['value'] == 0.00389837142433717


def test_twelve_groups_use_actual_corrected_space_padded_r_tokens():
    operands, _ = native_fixture('twelve_groups'); value = extracted(operands)
    assert [r['r_group_token'] for r in value['native_group_columns']] == [f'{i:2d}' for i in range(1, 13)]
    assert len(value['biological_group_populations'][0]['groups']) == 12
    forged = deepcopy(operands); forged['declarations']['r_columns'][0]['adjusted_matrix'] = 'unrelated'
    assert extract_metacats_associations(**forged)['status'] == 'invalid'
    assert any('TWELVE_GROUP_ORDER_CHECK_001' in e['content']['artifact_ref'] for e in value['native_group_columns'][0]['evidence'])


def test_original_hash_and_generated_terminal_mask_remain_different_documents():
    operands, _ = metacats_fixture(data='>a\nA#-\n>b\nAC-\n')
    value = extracted(operands); result = counts(operands, value)
    assert operands['documents'][0]['value']['rows'][0]['sequence'] == 'A#-'
    assert result['sites'][1]['observed_counts'] == [[0, 1]]
    assert result['sites'][2]['observed_counts'] == []


def test_conflicting_native_map_retains_biological_and_scalar_results():
    operands, _ = native_fixture('metadata_only_first_group')
    mapping = operands['declarations']['native_group_maps'][0]
    contradictory = deepcopy(mapping['entries'][0]); contradictory.update(native_group_ordinal=2)
    mapping['entries'].append(contradictory)
    value = extracted(operands)
    assert all(r['state'] == 'resolved' for r in value['biological_assignments'])
    assert value['native_group_columns'][0]['state'] == 'unresolved'
    assert value['exported_groups'][0]['state'] == 'conflicting'
    assert counts(operands, value, 'comparison')['sites'][1]['observed_counts'] == [[6, 0, 0], [0, 6, 0]]
    chisq = next(d['value'] for d in operands['documents'] if d['kind'] == 'metacats_chisq')
    assert chisq['rows'][0]['chi_square']['value'] == 8.33055648117294


def test_native_pair_group_token_is_joined_whole_and_saved_swap_rejected():
    operands, _ = native_fixture('metadata_only_first_group'); value = extracted(operands)
    native = next(r for r in value['native_test_associations'] if r['table_id'] in operands['analysis']['pair_table_ids'])
    native['group_ids'].reverse(); native['r_columns_0based'].reverse()
    with pytest.raises(ValueError, match='pair_export_identity_ambiguous'):
        c.validate_metacats_association_set(value, **{k: operands[k] for k in ('analysis', 'documents', 'associations')})


def test_conflicting_metadata_groups_remain_in_selected_observed_population():
    operands, _ = metacats_fixture(meta='id\tgroup\na\tX\na\tY\nb\tZ\nunmatched\tA\n')
    operands['declarations']['biological_group_populations'][0]['include_metadata_only'] = False
    value = extracted(operands)
    assert [g['raw_group_value'] for g in value['biological_group_populations'][0]['groups']] == ['X', 'Y', 'Z']
    assert counts(operands, value)['status'] == 'partial'


def test_auto_native_overwrite_requires_actual_explicit_merge_record():
    operands = auto_fixture(True); common = operands['associations']; row = common['row_members'][0]
    ref = {'alignment_id': row['alignment_id'], 'row_index': row['row_index']}
    common['transformations'] = [{'transformation_id': 'observed-merge', 'kind': 'native_duplicate_merge',
        'input_members': deepcopy(row['member_keys']), 'input_rows': [], 'output_rows': [ref], 'native_key': 'feature:one',
        'rule': 'overwrite_last', 'evidence': [evidence('observed-merge')]}]
    row.update(state='native_duplicate_merge', basis='transformation_record', transformation_ids=['observed-merge'])
    value = extracted(operands)
    assert value['biological_assignments'][0]['state'] == 'resolved'
    assert value['biological_assignments'][0]['group_id'] == c.group_id('category', 'other')
    assert len(value['auto_group_entries']) == 2
