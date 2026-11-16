"""Pure-provider fixtures and retained numerical records; no new native runs."""
from copy import deepcopy
import hashlib
import itertools
from pathlib import Path

import pytest
import scipy

from gene_annotation_episode.episodic_workflow.root.library import bvbrc_metacats_provider_contracts as c
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_metacats_inputs import extract_metacats_sheet
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_metacats_grader import calculate_metacats
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_metacats_associations import extract_metacats_associations
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_metacats_association_contracts import group_id
from gene_annotation_episode.episodic_workflow.root.library import bvbrc_metacats_formats as formats
from test_bvbrc_metacats_associations import metacats_fixture, extracted, auto_fixture
from test_bvbrc_alignment_associations import binding

BACKEND = {'name': 'scipy_chi2_integer_df_logtail_v1', 'version': scipy.__version__}


def run_record():
    return {'original_task_id': 'retained-local-component-execution', 'settings': [], 'commands': [], 'versions': [], 'conflicts': [], 'completeness': 'unknown'}


def sheet_from(operands, inputs=(), *, read_outcomes=(), run=None):
    categories = extract_metacats_associations(**operands)
    assert categories['value'] is not None, categories
    aid = operands['analysis']['alignment_id']
    alignment = next((d['value'] for d in operands['documents'] if d['kind'] == 'alignment' and d['value']['alignment_id'] == aid), None)
    populations = {'alignments': [], 'composition': [], 'taxonomy': [], 'leaves': []}
    if alignment is not None:
        populations['alignments'].append({'population_id': 'whole', 'alignment_id': aid,
            'row_indices': list(range(len(alignment['rows']))),
            'columns_0based': list(range(max((len(r['sequence']) for r in alignment['rows']), default=0))),
            'completeness': alignment['completeness'], 'evidence': []})
    parsed = extract_metacats_sheet(analysis=operands['analysis'], inputs=tuple(inputs), documents=operands['documents'],
        read_outcomes=tuple(read_outcomes), run=run or run_record(), associations=operands['associations'], populations=populations,
        category_associations=categories['value'], parameters={'source_dialect': 'retained_bvbrc_metacats'})
    assert parsed['value'] is not None, parsed
    return parsed['value']


def simple_sheet(data='>a\nAC\n>b\nAT\n', meta='id\tgroup\na\tB\nb\tC\n', categories=('category',)):
    operands, original = metacats_fixture(data=data, meta=meta, categories=categories)
    return sheet_from(operands, original['inputs'])


def requests(sheet, *, native=True, biological=True, epsilon=.001, multiplicity=True, native_tables=False):
    selected = []
    for category in sheet['categories']:
        cat = category['category_id']
        for basis, enabled in (('native', native), ('biological', biological)):
            if not enabled:
                continue
            prefix = basis + ':' + cat
            gp = next((p for p in sheet['biological_group_populations'] if p['category_id'] == cat), None)
            groups = [p['group_id'] for p in gp['groups']] if basis == 'biological' else [p['group_id'] for p in sheet['native_group_columns'] if p['category_id'] == cat and p['group_id'] is not None]
            pair = [list(p) for p in itertools.combinations(groups, 2)]
            count = {'kind': basis + '_group_counts', 'request_id': prefix + ':counts', 'population_id': 'whole', 'category_id': cat, 'case_policy': 'preserve'}
            if basis == 'native':
                count.update(terminal_mask='native_terminal_dash_to_hash', native_input_hash_policy='exclude_hash')
            else:
                count.update(group_population_id=gp['group_population_id'], terminal_gap_policy='exclude_terminal_dash', original_hash_policy='exclude_hash')
            stat = {'kind': basis + '_statistics', 'request_id': prefix + ':statistics', 'counts_request_id': count['request_id'],
                'alphabet': 'aa', 'epsilon': epsilon, 'nucleotide_padding': 'ACGT_at_variable_sites',
                'omnibus_continuity': 'r_default_2x2_min_delta', 'pair_df_policy': 'native_source' if basis == 'native' else 'standard_pair',
                'selected_pairs': pair, 'distribution_backend': deepcopy(BACKEND)}
            if basis == 'native':
                stat['pair_zero_policy'] = 'retain_math_and_native_zero_to_one'
            selected += [count, stat,
                {'kind': basis + '_effects', 'request_id': prefix + ':effects', 'counts_request_id': count['request_id'], 'selected_pairs': pair, 'zero_margin_policy': 'drop_for_raw_effect_only'},
                {'kind': 'expected_adequacy', 'request_id': prefix + ':adequacy', 'statistics_request_id': stat['request_id'], 'statistics_kind': 'native_reproduction' if basis == 'native' else 'biological'}]
            if multiplicity:
                selected.append({'kind': 'multiplicity', 'request_id': prefix + ':holm',
                    'family': {'family_id': prefix + ':whole-family', 'analysis_ids': [sheet['analysis']['analysis_id']], 'category_ids': [cat],
                        'test_kind': 'omnibus', 'eligibility': 'variable_site_positive_df', 'population_state': 'complete', 'total_test_count': None, 'assumption': None,
                        'p_value_basis': 'source_mathematical_recalculation' if basis == 'native' else 'biological_mathematical_recalculation',
                        'evidence': [], 'selection': 'all_eligible', 'tests': []},
                    'p_values': {'kind': 'statistical_results', 'statistics_request_ids': [stat['request_id']], 'field': 'mathematical_p'},
                    'method': 'holm', 'alpha': .05, 'dependence_assumption': 'none_required_between_tests'})
    return {'version': c.VERSION, 'requests': selected}


def by_id(components, identity):
    return next(r for r in components['results'] if r['request_id'] == identity)


def test_biological_success_without_r_does_not_disappear_with_native_failure():
    sheet = simple_sheet(); result = calculate_metacats(sheet, requests(sheet))
    assert by_id(result, 'biological:category:counts')['value']['sites'][1]['observed_counts'] == [[1, 0], [0, 1]]
    assert by_id(result, 'native:category:counts')['value'] is None
    assert by_id(result, 'native:category:statistics')['requirements'][0]['reason_code'] == 'alignment_calculation_dependency_unavailable'
    assert by_id(result, 'biological:category:statistics')['value']['omnibus'][0]['df']['value'] == 1


def test_missing_original_member_is_only_biological_identity_qualification():
    operands, _ = metacats_fixture()
    operands['associations'] = {k: [] for k in c.common.ASSOCIATION_KEYS}
    sheet = sheet_from(operands)
    result = calculate_metacats(sheet, requests(sheet, native=False))
    count = by_id(result, 'biological:category:counts')
    assert count['status'] == 'ok' and count['value']['sites'][1]['observed_counts'] == [[1, 0], [0, 1]]
    assert any(d['code'] == 'biological_group_original_member_identity_unknown' for d in count['diagnostics'])


@pytest.mark.parametrize('mutation', ['extra', 'bool', 'negative', 'duplicate', 'unknown', 'wrong_kind', 'cycle', 'old_native_plan'])
def test_closed_parameters_and_dependencies_reject_misuse(mutation):
    p = requests(simple_sheet(), native=False)
    if mutation == 'extra': p['requests'][0]['extra'] = True
    if mutation == 'bool': p['requests'][1]['epsilon'] = True
    if mutation == 'negative': p['requests'][1]['epsilon'] = -1
    if mutation == 'duplicate': p['requests'].append(deepcopy(p['requests'][0]))
    if mutation == 'unknown': p['requests'][1]['counts_request_id'] = 'unknown'
    if mutation == 'wrong_kind': p['requests'][1]['counts_request_id'] = p['requests'][2]['request_id']
    if mutation == 'cycle': p['requests'][1]['counts_request_id'] = p['requests'][1]['request_id']
    if mutation == 'old_native_plan': p['requests'][-1]['p_values'] = {'kind': 'native_observations', 'observation_ids': [], 'test_association_ids': []}
    with pytest.raises(ValueError, match='bvbrc_metacats_provider_'):
        c.validate_metacats_parameters(p)


def test_dependency_evaluation_does_not_change_original_request_order():
    sheet = simple_sheet(); parameters = requests(sheet, native=False); parameters['requests'].reverse()
    result = calculate_metacats(sheet, parameters)
    assert [r['request_id'] for r in result['results']] == [r['request_id'] for r in parameters['requests']]
    assert all(r['value'] is not None for r in result['results'])


def test_original_hash_and_terminal_dash_exclusions_are_separate():
    sheet = simple_sheet('>a\nA#-\n>b\nAC-\n')
    result = calculate_metacats(sheet, requests(sheet, native=False))
    count = by_id(result, 'biological:category:counts')['value']
    assert count['sites'][1]['excluded_original_hash_rows_by_group'] == [[0], []]
    assert count['sites'][2]['excluded_terminal_rows_by_group'] == [[0], [1]]
    assert sheet['documents'][0]['value']['rows'][0]['sequence'] == 'A#-'


def test_cross_category_failure_preserves_independent_numerical_results():
    sheet = simple_sheet(meta='id\tgroup\tgroup\na\tA\tX\nb\tB\tY\n', categories=('first', 'second'))
    parameters = requests(sheet, native=False)
    next(r for r in parameters['requests'] if r['request_id'] == 'biological:second:counts')['group_population_id'] = 'unavailable'
    result = calculate_metacats(sheet, parameters)
    assert by_id(result, 'biological:first:statistics')['value']['omnibus']
    assert by_id(result, 'biological:second:counts')['value'] is None
    assert by_id(result, 'biological:second:statistics')['requirements'][0]['reason_code'] == 'alignment_calculation_dependency_unavailable'


def test_repeated_headings_blank_and_comma_groups_remain_category_specific():
    sheet = simple_sheet(meta='id\tgroup\tgroup\na\t\tA,B\nb\tC\tC\n', categories=('first', 'second'))
    assert [r['raw_heading_token'] for r in sheet['categories']] == ['group', 'group']
    assert [r['metadata_column_index_0based'] for r in sheet['categories']] == [1, 2]
    assert [(g['category_id'], g['raw_group_value']) for g in sheet['groups']] == [
        ('first', ''), ('first', 'C'), ('second', 'A,B'), ('second', 'C')]
    result = calculate_metacats(sheet, requests(sheet, native=False))
    for category in ('first', 'second'):
        assert by_id(result, 'biological:' + category + ':counts')['value']['sites'][1]['observed_counts'] == [[1, 0], [0, 1]]
    assert sheet['groups'][1]['group_id'] != sheet['groups'][3]['group_id']


@pytest.mark.parametrize('mode', ['groups', 'auto'])
def test_mode_provenance_and_zero_fetched_original_bindings(mode):
    operands = auto_fixture(False, fetched=False)
    original = binding('', name='original')
    original['content'] = None; original['kind'] = 'inline_parameter'; original['inline_value'] = ''
    # The already-extracted common sequences still use their actual original
    # binding; this additional requested group binding has no fetched members.
    fetched = binding('>a\nAC\n>b\nAT\n')
    requested = binding('', name='original-auto-request', inline=True); requested['inline_value'] = []
    if mode == 'groups':
        operands['analysis']['mode'] = 'groups'; operands['declarations']['categories'][0]['input_mode'] = 'groups'
        operands['declarations']['auto_group_entries'] = []
    sheet = sheet_from(operands, (fetched, requested))
    assert sheet['analysis']['mode'] == mode
    assert len(sheet['auto_group_entries']) == (2 if mode == 'auto' else 0)
    assert all(r['state'] == 'missing' for r in sheet['biological_assignments'])


def test_common_alignment_map_and_original_coverage_keep_separate_contracts():
    sheet = simple_sheet(); aid = sheet['analysis']['alignment_id']
    p = {'version': c.VERSION, 'requests': [
        {'kind': 'alignment', 'request_id': 'alignment', 'population_id': 'whole', 'alphabet': 'dna', 'case_policy': 'uppercase', 'pairs': [[0, 1]]},
        {'kind': 'ungapped_map', 'request_id': 'map', 'alignment_id': aid, 'row_indices': [0, 1]},
        {'kind': 'original_coverage', 'request_id': 'coverage', 'population_id': 'whole'}]}
    result = calculate_metacats(sheet, p)
    assert by_id(result, 'alignment')['value']['pairs'][0]['identity_fraction']['value'] == .5
    assert by_id(result, 'map')['value'][3]['ungapped_position_0based'] == 1
    assert by_id(result, 'coverage')['status'] == 'partial'
    assert 'population_ref' in by_id(result, 'alignment')['value']['member_count']


def native_family_request(sheet, *, kind='omnibus', tables='raw', eligibility=(), state='complete', selection='all_eligible', tests=None):
    category = sheet['analysis']['category_ids'][0]
    tids = sheet['analysis']['raw_r_table_ids'] if tables == 'raw' else sheet['analysis']['chisq_table_ids' if kind == 'omnibus' else 'pair_table_ids']
    docs = {c.common.document_identity(d): d for d in sheet['documents']}
    tids = [tid for tid in tids if docs[tid]['kind'] != 'metacats_raw_r' or docs[tid]['value']['kind'] == kind]
    return {'kind': 'multiplicity', 'request_id': 'native-observed-family',
        'family': {'family_id': 'actual-native-p', 'analysis_ids': [sheet['analysis']['analysis_id']], 'category_ids': [category],
            'test_kind': kind, 'eligibility': 'variable_site_positive_df', 'population_state': state, 'total_test_count': None,
            'assumption': None, 'p_value_basis': 'native_unadjusted', 'evidence': [], 'selection': selection, 'tests': tests or []},
        'p_values': {'kind': 'native_tables', 'table_ids': tids, 'eligibility_statistics_request_ids': list(eligibility)},
        'method': 'holm', 'alpha': .05, 'dependence_assumption': 'none_required_between_tests'}


@pytest.mark.parametrize('mode', ['known_count_only', 'declared_upper_bound'])
def test_declared_external_family_denominators_only_allow_documented_bonferroni(mode):
    sheet = simple_sheet(); parameters = requests(sheet, native=False)
    request = parameters['requests'][-1]
    request['family'].update(population_state=mode, total_test_count=10,
        assumption={'kind': 'independently_known_count' if mode == 'known_count_only' else 'parent_declared_upper_bound', 'count': 10,
            'evidence': [{'content': {'source_ref': 'declared', 'artifact_field': 'artifact_ref', 'artifact_ref': 'declared', 'sha256': 'a' * 64, 'byte_count': 0}, 'pointer': ''}]})
    request['method'] = 'bonferroni'
    result = calculate_metacats(sheet, parameters); value = by_id(result, request['request_id'])['value']
    assert value['results'][0]['adjusted_p']['value'] == min(1, value['results'][0]['input_p']['value'] * 10)
    request['method'] = 'holm'
    assert by_id(calculate_metacats(sheet, parameters), request['request_id'])['value']['results'][0]['adjusted_p']['value'] is None


def test_full_family_declared_count_conflict_is_explicit_failed_request():
    sheet = simple_sheet(); parameters = requests(sheet, native=False); parameters['requests'][-1]['family']['total_test_count'] = 100
    result = calculate_metacats(sheet, parameters)
    assert result['results'][-1]['status'] == 'invalid' and result['results'][-1]['value'] is None
    assert result['results'][1]['value']['omnibus']


def test_explicit_empty_selection_is_a_known_empty_subset():
    sheet = simple_sheet(); parameters = requests(sheet, native=False)
    parameters['requests'][-1]['family']['selection'] = 'explicit_tests'
    family = calculate_metacats(sheet, parameters)['results'][-1]['value']
    assert family['total_test_count'] == 0 and family['results'] == []


@pytest.mark.parametrize('token,state,token_kind', [('NA', 'not_measured', 'native_na'), ('bad', 'failed', 'malformed'), ('1e-999', 'failed', 'underflow'), ('0', 'available', 'finite')])
def test_synthetic_native_numbers_survive_unresolved_associations(token, state, token_kind):
    operands, original = metacats_fixture()
    raw = ('Position\tChi-square_value\tP-value\tDegrees_of_freedom\tFewer_5\tB\tC\n'
           f'2\t3.5\t{token}\t1\tY\t1 C\t1 T\nmalformed\n').encode()
    artifact = {'raw_artifact_ref': 'synthetic-native-tsv', 'source_ref': 'synthetic-native-tsv', 'sha256': hashlib.sha256(raw).hexdigest()}
    parsed = formats.parse_metacats_chisq_table(raw, artifact=artifact, layout='current_filtered_tsv', category_id='category', encoding='ascii')
    assert parsed['status'] == 'partial'
    operands['documents'] += ({'kind': 'metacats_chisq', 'value': parsed['value']},)
    operands['analysis']['chisq_table_ids'] = [parsed['value']['table_id']]
    sheet = sheet_from(operands, original['inputs'])
    observation = next(r for r in sheet['native_observations'] if r['field'] == 'metacats_p_value')
    assert observation['number']['raw_token'] == token and observation['number']['state'] == state
    assert observation['number']['token_kind'] == token_kind
    assert observation['association_state'] == 'missing' and observation['population_id'] is None
    assert next(d['value'] for d in sheet['documents'] if d['kind'] == 'metacats_chisq') == parsed['value']


def test_invalid_reader_and_empty_header_only_export_keep_independent_alignment():
    operands, original = metacats_fixture()
    raw = b'Position\tMultiple_comparison_p-value\tGroups\n'
    artifact = {'raw_artifact_ref': 'synthetic-empty', 'source_ref': 'synthetic-empty', 'sha256': hashlib.sha256(raw).hexdigest()}
    spec = {'reader': 'metacats_pair', 'layout': 'current_filtered_tsv', 'category_id': 'category', 'encoding': 'ascii'}
    parsed = formats.parse_metacats_pair_table(raw, artifact=artifact, **{k: v for k, v in spec.items() if k != 'reader'})
    operands['documents'] += ({'kind': 'metacats_pair', 'value': parsed['value']},)
    operands['analysis']['pair_table_ids'] = [parsed['value']['table_id']]
    invalid = {'read_id': 'unreadable-native', 'slot_id': 'unreadable-native', 'artifact': artifact, 'reader': spec,
        'status': 'invalid', 'document_ids': [], 'diagnostics': [{'code': 'bvbrc_metacats_native_header_conflict', 'phase': 'native_decode', 'path': '', 'severity': 'error', 'evidence_refs': ['synthetic-empty']}]}
    sheet = sheet_from(operands, original['inputs'], read_outcomes=[invalid])
    assert not sheet['native_observations'] and sheet['read_outcomes'][0]['status'] == 'invalid'
    result = calculate_metacats(sheet, requests(sheet, native=False))
    assert by_id(result, 'biological:category:statistics')['value']['omnibus']
    family = native_family_request(sheet, kind='pairwise', tables='filtered')
    assert calculate_metacats(sheet, {'version': c.VERSION, 'requests': [family]})['results'][0]['value'] is None


def test_unrecorded_terminal_hash_mask_cannot_claim_original_hash_provenance():
    sheet = simple_sheet('>a\nAC-\n>b\nAT-\n')
    population = sheet['populations']['alignments'][0]
    assert c.native_input_provenance(sheet, population)
    masked = deepcopy(sheet)
    alignment = next(d['value'] for d in masked['documents'] if d['kind'] == 'alignment' and d['value']['alignment_id'] == masked['analysis']['alignment_id'])
    alignment['rows'][0]['sequence'] = 'AC#'
    # The provenance predicate uses actual original sequence data; a common
    # header alone cannot explain a changed hash. No native rerun is selected.
    assert not c.native_input_provenance(masked, population)


def test_common_function_and_taxon_components_keep_explicit_population_identities():
    sheet = simple_sheet()
    evidence = {'content': {'source_ref': 'synthetic-feature-metadata', 'artifact_field': 'artifact_ref', 'artifact_ref': 'synthetic-feature-metadata', 'sha256': 'a' * 64, 'byte_count': 0}, 'pointer': ''}
    subjects = [{'kind': 'feature', 'id': f'f{i}', 'source_record_id': f's{i}'} for i in range(2)]
    for i, subject in enumerate(subjects):
        sheet['associations']['source_records'].append({'source_record_id': f's{i}', 'kind': 'feature', 'evidence': evidence})
        sheet['associations']['functions'].append({'assignment_id': f'a{i}', 'subject': subject, 'function_key': 'enzyme', 'function_label': 'supplied assignment', 'source_record_id': f's{i}', 'evidence': [evidence]})
        sheet['associations']['taxonomy'].append({'subject': subject, 'taxon_id': f't{i}', 'rank': 'species', 'lineage': [], 'source_record_id': f's{i}', 'evidence': [evidence]})
    population = {'population_id': 'features', 'unit': 'feature', 'member_subjects': subjects, 'assignment_completeness': 'complete', 'membership_completeness': 'complete', 'evidence': [evidence]}
    sheet['populations']['composition'] = [population]
    sheet['populations']['taxonomy'] = [{**deepcopy(population), 'population_id': 'taxa'}]
    parameters = {'version': c.VERSION, 'requests': [
        {'kind': 'function_composition', 'request_id': 'functions', 'population_id': 'features'},
        {'kind': 'taxonomy', 'request_id': 'taxa', 'population_id': 'taxa', 'rank': 'species'}]}
    result = calculate_metacats(sheet, parameters)
    assert result['results'][0]['value']['rows'][0]['assigned_members']['value'] == 2
    assert result['results'][1]['value']['distinct_known_taxa']['value'] == 2
    assert c.validate_metacats_components(result, sheet=sheet) == result


@pytest.mark.parametrize('mode', ['groups', 'auto'])
def test_explicit_fetched_group_and_auto_membership_feeds_biological_calculation(mode):
    operands = auto_fixture(False, fetched=True)
    decl = operands['declarations']; original_members = operands['associations']['original_members']
    decl['auto_group_entries'][1].update(member_keys=[original_members[1]['key']], feature_id='feature:two', raw_group_value='other')
    if mode == 'groups':
        operands['analysis']['mode'] = 'groups'; decl['categories'][0]['input_mode'] = 'groups'; decl['auto_group_entries'] = []
        proof = {'content': {'source_ref': 'synthetic-groups', 'artifact_field': 'artifact_ref', 'artifact_ref': 'synthetic-groups', 'sha256': 'b' * 64, 'byte_count': 0}, 'pointer': ''}
        operands['associations']['source_records'].append({'source_record_id': 'group-record', 'kind': 'parent_declaration', 'evidence': proof})
        decl['group_sources'] = [{'category_id': 'category', 'raw_group_value': raw, 'bindings': [{'input_binding_id': 'requested-groups', 'group_id': '/workspace/' + raw,
            'source_record_id': 'group-record', 'evidence': [proof]}]} for raw in ('same', 'other')]
        decl['explicit_memberships'] = [{'category_id': 'category', 'alignment_id': operands['analysis']['alignment_id'], 'row_index': i,
            'member_key': member['key'], 'group_id': group_id('category', ('same', 'other')[i]), 'state': 'resolved', 'evidence': [proof]} for i, member in enumerate(original_members)]
    sheet = sheet_from(operands, (binding('>a\nAC\n>b\nAT\n'),))
    result = calculate_metacats(sheet, requests(sheet, native=False))
    assert by_id(result, 'biological:category:counts')['value']['sites'][1]['observed_counts'] == [[1, 0], [0, 1]]
    assert sheet['analysis']['mode'] == mode
    if mode == 'groups':
        assert sheet['groups'][0]['source_group_bindings'][0]['group_id'] == '/workspace/same'
    else:
        assert [r['feature_id'] for r in sheet['auto_group_entries']] == ['feature:one', 'feature:two']


def test_structurally_contradictory_sheet_request_returns_invalid_parse_result():
    sheet = simple_sheet()
    operands = {k: sheet[k] for k in ('analysis', 'inputs', 'documents', 'read_outcomes', 'run', 'associations', 'populations')}
    operands['category_associations'] = {k: sheet[k] for k in c.association.SET_KEYS}
    operands['analysis'] = {**sheet['analysis'], 'alignment_id': 'not-a-retained-document'}
    result = extract_metacats_sheet(**operands, parameters={'source_dialect': 'retained_bvbrc_metacats'})
    assert result['status'] == 'invalid' and result['value'] is None and result['diagnostics'][0]['severity'] == 'error'
