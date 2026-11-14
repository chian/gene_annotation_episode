"""Closed MetaCATS sheets, explicit requests and detached saved-result checks.

No validator calls a parser, calculator, service, filesystem or native program.
Native numeric tokens are checked against retained documents. Mathematical
results retain their existing contracts and are tied to the original request.
"""
from __future__ import annotations

from copy import deepcopy
from functools import wraps
import hashlib
import json
import math
from urllib.parse import quote

from . import bvbrc_alignment_provider_contracts as common
from . import bvbrc_metacats_association_contracts as association
from . import bvbrc_metacats_calculation_contracts as native
from . import bvbrc_metacats_biological_contracts as biological
from . import phylogeny_calculation_contracts as shared
from .bvbrc_metacats_adequacy import validate_expected_count_adequacy
from .bvbrc_alignment_values import diagnostic, requirement, numeric_cell, validate_native_number

PREFIX = 'bvbrc_metacats_provider_'
VERSION = 'bvbrc_metacats_components_v1'
SHEET_KEYS = {'schema_version', 'tool', 'analysis', 'inputs', 'run', 'documents',
    'read_outcomes', 'associations', 'populations', 'native_observations',
    *association.SET_KEYS}
COMMON_KINDS = {'alignment', 'ungapped_map', 'original_coverage', 'function_composition', 'taxonomy'}
COUNT_KINDS = {'native_group_counts', 'biological_group_counts'}
STAT_KINDS = {'native_statistics', 'biological_statistics'}
EFFECT_KINDS = {'native_effects', 'biological_effects'}
REQUEST_FIELDS = {
    'alignment': {'population_id', 'alphabet', 'case_policy', 'pairs'},
    'ungapped_map': {'alignment_id', 'row_indices'},
    'original_coverage': {'population_id'}, 'function_composition': {'population_id'},
    'taxonomy': {'population_id', 'rank'},
    'native_group_counts': {'population_id', 'category_id', 'case_policy', 'terminal_mask', 'native_input_hash_policy'},
    'biological_group_counts': {'population_id', 'category_id', 'group_population_id', 'case_policy', 'terminal_gap_policy', 'original_hash_policy'},
    'native_statistics': {'counts_request_id', 'alphabet', 'epsilon', 'nucleotide_padding', 'omnibus_continuity', 'pair_df_policy', 'pair_zero_policy', 'selected_pairs', 'distribution_backend'},
    'biological_statistics': {'counts_request_id', 'alphabet', 'epsilon', 'nucleotide_padding', 'omnibus_continuity', 'pair_df_policy', 'selected_pairs', 'distribution_backend'},
    'native_effects': {'counts_request_id', 'selected_pairs', 'zero_margin_policy'},
    'biological_effects': {'counts_request_id', 'selected_pairs', 'zero_margin_policy'},
    'expected_adequacy': {'statistics_request_id', 'statistics_kind'},
    'multiplicity': {'family', 'p_values', 'method', 'alpha', 'dependence_assumption'},
}


def require(condition, code):
    if not condition:
        raise ValueError(PREFIX + code)


def closed(function):
    @wraps(function)
    def checked(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except ValueError as exc:
            if str(exc).startswith(PREFIX):
                raise
            raise ValueError(PREFIX + 'dependency_contract_invalid') from exc
        except (KeyError, TypeError, IndexError, OverflowError, UnicodeError, RecursionError) as exc:
            raise ValueError(PREFIX + 'shape_invalid') from exc
    return checked


def shape(value, keys):
    require(type(value) is dict and set(value) == set(keys), 'shape_invalid')


def number(value, minimum=None, maximum=None, nullable=False):
    if nullable and value is None:
        return
    require(type(value) in (int, float) and math.isfinite(value), 'number_invalid')
    require(minimum is None or value >= minimum, 'number_below_minimum')
    require(maximum is None or value <= maximum, 'number_above_maximum')


def merge_reports(*collections):
    result = []
    by_id = {}
    for rows in collections:
        for row in rows:
            if 'requirement_id' in row:
                identity = row['requirement_id']
                require(identity not in by_id or by_id[identity] == row, 'requirement_identity_conflict')
                by_id[identity] = row
            if row not in result:
                result.append(deepcopy(row))
    return result


def need(analysis_id, request_id, reason, *, kind='scientific_metadata', source_refs=()):
    identity = 'metacats/' + '/'.join(quote(x, safe='') for x in (analysis_id, request_id, reason))
    return requirement(identity, kind=kind, role=request_id, source_refs=source_refs, reason_code=reason)


def _pairs(values, integer=False):
    common.array(values)
    seen = set()
    for pair in values:
        common.array(pair); require(len(pair) == 2, 'pair_invalid')
        for item in pair:
            common.integer(item) if integer else common.text(item)
        require((integer or pair[0] != pair[1]) and tuple(pair) not in seen, 'pair_duplicate_or_self')
        seen.add(tuple(pair))


def selector(row):
    shape(row, {'category_id', 'column_0based', 'kind', 'group_ids'})
    common.text(row['category_id']); common.integer(row['column_0based']); common.strings(row['group_ids'])
    require(row['kind'] in ('omnibus', 'pairwise'), 'test_kind_invalid')
    require(len(row['group_ids']) >= 2 and (row['kind'] != 'pairwise' or len(row['group_ids']) == 2), 'test_groups_invalid')
    return row['category_id'], row['column_0based'], row['kind'], tuple(row['group_ids'])


def test_selector(row):
    return row['category_id'], row['column_0based'], row['kind'], tuple(row['group_ids'])


def _family_plan(value):
    shape(value, {'family_id', 'analysis_ids', 'category_ids', 'test_kind', 'eligibility',
        'population_state', 'total_test_count', 'assumption', 'p_value_basis', 'evidence', 'selection', 'tests'})
    for key in ('analysis_ids', 'category_ids'):
        common.strings(value[key])
    common.text(value['family_id']); common.integer(value['total_test_count'], nullable=True)
    require(value['analysis_ids'] and value['category_ids'], 'family_scope_empty')
    require(value['test_kind'] in ('omnibus', 'pairwise') and value['eligibility'] == 'variable_site_positive_df', 'family_eligibility_invalid')
    require(value['population_state'] in ('complete', 'known_count_only', 'declared_upper_bound', 'unknown'), 'family_population_invalid')
    require(value['p_value_basis'] in ('native_unadjusted', 'source_mathematical_recalculation', 'biological_mathematical_recalculation'), 'family_basis_invalid')
    common.evidence(value['evidence'])
    assumption = value['assumption']
    if assumption is not None:
        shape(assumption, {'kind', 'count', 'evidence'}); common.integer(assumption['count']); common.evidence(assumption['evidence'])
        require(assumption['kind'] in ('independently_known_count', 'parent_declared_upper_bound') and assumption['count'] == value['total_test_count'], 'family_assumption_invalid')
    require(value['population_state'] != 'complete' or assumption is None, 'complete_family_assumption')
    if value['population_state'] in ('known_count_only', 'declared_upper_bound'):
        expected = 'independently_known_count' if value['population_state'] == 'known_count_only' else 'parent_declared_upper_bound'
        require(assumption is not None and assumption['kind'] == expected and assumption['evidence'], 'family_assumption_required')
    require(value['selection'] in ('all_eligible', 'explicit_tests'), 'family_selection_invalid')
    common.array(value['tests']); seen = set()
    for row in value['tests']:
        key = selector(row); require(key not in seen, 'test_selector_duplicate'); seen.add(key)
        require(row['category_id'] in value['category_ids'] and row['kind'] == value['test_kind'], 'test_selector_family_conflict')
    require(value['selection'] != 'all_eligible' or not value['tests'], 'all_eligible_with_tests')


def dependencies(request):
    kind = request['kind']
    if kind in STAT_KINDS | EFFECT_KINDS:
        return [request['counts_request_id']]
    if kind == 'expected_adequacy':
        return [request['statistics_request_id']]
    if kind == 'multiplicity':
        plan = request['p_values']
        return plan['statistics_request_ids'] if plan['kind'] == 'statistical_results' else plan['eligibility_statistics_request_ids']
    return []


@closed
def validate_metacats_parameters(parameters: dict) -> dict:
    shape(parameters, {'version', 'requests'}); require(parameters['version'] == VERSION, 'parameters_version_invalid')
    common.array(parameters['requests']); requests = common.unique(parameters['requests'], 'request_id')
    for row in requests.values():
        common.text(row['request_id']); kind = row['kind']; require(type(kind) is str and kind in REQUEST_FIELDS, 'request_kind_invalid')
        shape(row, REQUEST_FIELDS[kind] | {'kind', 'request_id'})
        for key in ('population_id', 'alignment_id', 'category_id', 'group_population_id', 'counts_request_id', 'statistics_request_id', 'rank'):
            if key in row:
                common.text(row[key])
        if kind == 'alignment':
            require(row['alphabet'] in ('dna', 'rna', 'protein', 'unknown') and row['case_policy'] in ('uppercase', 'literal'), 'alignment_parameters_invalid')
            _pairs(row['pairs'], integer=True)
        elif kind == 'ungapped_map':
            common.indices(row['row_indices'])
        elif kind in COUNT_KINDS:
            require(row['case_policy'] in ('preserve', 'uppercase'), 'count_parameters_invalid')
            expected = {'terminal_mask': 'native_terminal_dash_to_hash', 'native_input_hash_policy': 'exclude_hash'} if kind == 'native_group_counts' else {'terminal_gap_policy': 'exclude_terminal_dash', 'original_hash_policy': 'exclude_hash'}
            require(all(row[k] == v for k, v in expected.items()), 'count_parameters_invalid')
        elif kind in STAT_KINDS:
            number(row['epsilon'], minimum=0); _pairs(row['selected_pairs'])
            require(row['alphabet'] in ('na', 'aa') and row['nucleotide_padding'] == 'ACGT_at_variable_sites' and row['omnibus_continuity'] == 'r_default_2x2_min_delta', 'statistics_parameters_invalid')
            require(row['pair_df_policy'] in (('native_source', 'standard_pair') if kind == 'native_statistics' else ('standard_pair',)), 'pair_df_invalid')
            require(kind != 'native_statistics' or row['pair_zero_policy'] == 'retain_math_and_native_zero_to_one', 'pair_zero_policy_invalid')
            shape(row['distribution_backend'], {'name', 'version'})
            require(row['distribution_backend']['name'] == 'scipy_chi2_integer_df_logtail_v1', 'backend_invalid'); common.text(row['distribution_backend']['version'])
        elif kind in EFFECT_KINDS:
            _pairs(row['selected_pairs']); require(row['zero_margin_policy'] == 'drop_for_raw_effect_only', 'effect_parameters_invalid')
        elif kind == 'expected_adequacy':
            require(row['statistics_kind'] in ('native_reproduction', 'biological'), 'adequacy_kind_invalid')
        elif kind == 'multiplicity':
            _family_plan(row['family']); plan = row['p_values']
            require(type(plan) is dict and plan.get('kind') in ('statistical_results', 'native_tables'), 'p_value_plan_invalid')
            if plan['kind'] == 'statistical_results':
                shape(plan, {'kind', 'statistics_request_ids', 'field'}); common.strings(plan['statistics_request_ids'])
                require(plan['field'] == 'mathematical_p' and plan['statistics_request_ids'], 'p_value_plan_invalid')
                require(row['family']['p_value_basis'] != 'native_unadjusted', 'p_value_basis_conflict')
            else:
                shape(plan, {'kind', 'table_ids', 'eligibility_statistics_request_ids'})
                common.strings(plan['table_ids']); common.strings(plan['eligibility_statistics_request_ids'])
                require(plan['table_ids'] and row['family']['p_value_basis'] == 'native_unadjusted', 'p_value_basis_conflict')
            require(row['method'] in ('none', 'bonferroni', 'holm', 'bh', 'by'), 'multiplicity_method_invalid'); number(row['alpha'], minimum=0, maximum=1)
            require(row['dependence_assumption'] in ('none_required_between_tests', 'independent_or_positive_regression_dependence_assumed'), 'dependence_invalid')
    for row in requests.values():
        for dependency in dependencies(row):
            require(dependency in requests, 'dependency_unknown')
            target = requests[dependency]['kind']; kind = row['kind']
            if kind in STAT_KINDS | EFFECT_KINDS:
                require(target == ('native_group_counts' if kind.startswith('native_') else 'biological_group_counts'), 'dependency_kind_invalid')
            elif kind == 'expected_adequacy':
                require(target == ('native_statistics' if row['statistics_kind'] == 'native_reproduction' else 'biological_statistics'), 'dependency_kind_invalid')
            elif kind == 'multiplicity':
                expected = 'biological_statistics' if row['family']['p_value_basis'] == 'biological_mathematical_recalculation' else 'native_statistics'
                require(target == expected, 'dependency_kind_invalid')
    pending = set(requests); done = set()
    while pending:
        ready = {identity for identity in pending if set(dependencies(requests[identity])) <= done}
        require(ready, 'dependency_cycle'); pending -= ready; done |= ready
    return deepcopy(parameters)


def native_observations(sheet):
    """Enumerate original numerical fields without evaluating any statistic."""
    analysis = sheet['analysis']; documents = {common.document_identity(d): d for d in sheet['documents']}
    tests = {(r['table_id'], r['row_index']): r for r in sheet['native_test_associations']}
    exports = {(r['table_id'], r['heading_index_0based']): r for r in sheet['exported_groups']}
    columns = {(r['category_id'], r['r_column_index_0based']): r for r in sheet['native_group_columns']}
    output = []
    for tid in analysis['chisq_table_ids'] + analysis['pair_table_ids'] + analysis['raw_r_table_ids']:
        wrapper = documents[tid]; table = wrapper['value']; category = table['category_id']
        rows = table.get('rows')
        if rows is None:
            rows = table['omnibus_rows'] if table['kind'] == 'omnibus' else table['pair_rows']
        for row in rows:
            joined = tests.get((tid, row['row_index']))
            state = joined['state'] if joined else 'missing'
            pid = joined['test_id'] if joined else None
            gids = joined['group_ids'] if joined else []
            evidence = joined['evidence'] if joined else []
            def add(path, field, number, unit, nested=(), groups=None, association_state=None, proof=None):
                output.append({'observation_id': tid + '/rows/' + str(row['row_index']) + '/' + path,
                    'document_id': tid, 'row_index': row['row_index'], 'field': field, 'nested_indices': list(nested),
                    'number': deepcopy(number), 'unit': unit, 'population_id': pid, 'category_id': category,
                    'group_ids': deepcopy(gids if groups is None else groups),
                    'association_state': state if association_state is None else association_state,
                    'evidence': deepcopy(evidence if proof is None else proof)})
            for key, field, unit in (('chi_square', 'metacats_chi_square', 'chi_square'), ('p_value', 'metacats_p_value', 'probability'), ('df', 'metacats_df', 'degrees_of_freedom')):
                if key in row:
                    add(key, field, row[key], unit)
            collection = 'group_cells' if 'group_cells' in row else 'positional_groups'
            for i, group in enumerate(row.get(collection, [])):
                if collection == 'group_cells':
                    link = exports.get((tid, group['heading_index']))
                else:
                    link = columns.get((category, group['position_1based'] - 1))
                group_ids = [link['group_id']] if link and link['group_id'] is not None else []
                group_state = link['state'] if link else 'missing'
                if group_state == 'unresolved':
                    group_state = 'missing'
                for j, item in enumerate(group['symbol_counts']):
                    add(f'{collection}/{i}/symbol_counts/{j}/count', 'metacats_symbol_count', item['count'], 'observations',
                        (i, j), groups=group_ids, association_state=group_state, proof=link['evidence'] if link else [])
    return output


@closed
def validate_metacats_sheet(sheet: dict) -> dict:
    shape(sheet, SHEET_KEYS)
    require(sheet['schema_version'] == 'bvbrc_metacats_sheet_v1' and sheet['tool'] == 'C-L205-MetaCATS', 'sheet_identity_invalid')
    common.input_map(sheet['inputs']); docs, _, _ = common.document_maps(sheet['documents'])
    require(all(d['kind'] in ('alignment', 'metadata', 'adjusted_matrix', 'metacats_chisq', 'metacats_pair', 'metacats_raw_r') for d in sheet['documents']), 'document_provider_conflict')
    common.validate_run_record(sheet['run'])
    common.validate_association_set(sheet['associations'], inputs=sheet['inputs'], documents=sheet['documents'])
    association.validate_metacats_association_set({k: sheet[k] for k in association.SET_KEYS}, analysis=sheet['analysis'], documents=sheet['documents'], associations=sheet['associations'])
    common.validate_populations(sheet['populations'], documents=sheet['documents'], associations=sheet['associations'])
    require(not sheet['populations']['leaves'], 'metacats_tree_population_invalid')
    common.unique(sheet['read_outcomes'], 'read_id')
    for outcome in sheet['read_outcomes']:
        common.validate_reader_spec(outcome['reader'], provider='metacats')
        common.validate_reader_outcome(outcome, documents=sheet['documents'])
    common.reports(sheet)
    require(sheet['analysis']['analysis_id'] not in ('@families', '@requirements'), 'reserved_analysis_id')
    common.unique(sheet['native_observations'], 'observation_id')
    units = {'metacats_chi_square': 'chi_square', 'metacats_p_value': 'probability',
             'metacats_df': 'degrees_of_freedom', 'metacats_symbol_count': 'observations'}
    for observation in sheet['native_observations']:
        shape(observation, {'observation_id', 'document_id', 'row_index', 'field', 'nested_indices',
            'number', 'unit', 'population_id', 'category_id', 'group_ids', 'association_state', 'evidence'})
        common.text(observation['observation_id']); common.text(observation['document_id'])
        common.integer(observation['row_index']); common.array(observation['nested_indices'])
        for index in observation['nested_indices']:
            common.integer(index)
        common.text(observation['population_id'], nullable=True); common.text(observation['category_id'], nullable=True)
        common.strings(observation['group_ids']); common.evidence(observation['evidence'])
        validate_native_number(observation['number'])
        require(observation['field'] in units and observation['unit'] == units[observation['field']], 'native_observation_unit_conflict')
        require(observation['association_state'] in ('resolved', 'missing', 'conflicting', 'wrong_native_label'), 'native_observation_association_invalid')
    require(sheet['native_observations'] == native_observations(sheet), 'native_observation_document_conflict')
    for source in (sheet['associations'],):
        require(all(r in sheet['requirements'] for r in source['requirements']), 'sheet_requirement_omitted')
    return deepcopy(sheet)


def lookup_population(sheet, kind, identity):
    return next((p for p in sheet['populations'][kind] if p['population_id'] == identity), None)


def lookup_alignment(sheet, identity):
    return next((d['value'] for d in sheet['documents'] if d['kind'] == 'alignment' and d['value']['alignment_id'] == identity), None)


def coverage_operands(sheet, population):
    originals = {common.member_key(m['key']): m for m in sheet['associations']['original_members']}
    joins = {(r['alignment_id'], r['row_index']): r for r in sheet['associations']['row_members']}
    output = []
    for index in population['row_indices']:
        join = joins.get((population['alignment_id'], index))
        if join is None or join['state'] != 'resolved' or len(join['member_keys']) != 1:
            return None
        key = common.member_key(join['member_keys'][0])
        if sum(k[:2] == key[:2] for k in originals) != 1:
            return None
        original = originals[key]
        output.append({'row': {'alignment_id': population['alignment_id'], 'row_index': index},
            'member': {k: original['key'][k] for k in ('input_binding_id', 'member_id')},
            'original_length': original['original_length'], 'original_sequence_sha256': original['sequence_sha256'],
            'evidence': deepcopy(original['evidence'])})
    return output


def native_input_provenance(sheet, population):
    originals = {common.member_key(m['key']): m for m in sheet['associations']['original_members']}
    joins = {(r['alignment_id'], r['row_index']): r for r in sheet['associations']['row_members']}
    transforms = {t['transformation_id']: t for t in sheet['associations']['transformations']}
    documents = {common.document_identity(d): d['value'] for d in sheet['documents']}
    inline = {r['input_binding_id']: r for r in sheet['associations']['inline_inputs']}
    alignment = documents[population['alignment_id']]
    for index in population['row_indices']:
        join = joins.get((population['alignment_id'], index))
        if join is None or join['state'] != 'resolved' or len(join['member_keys']) != 1:
            return False
        member = originals[common.member_key(join['member_keys'][0])]
        if member['source_row_index'] is None or member['sequence_sha256'] is None:
            return False
        if any(transforms[t]['kind'] == 'native_terminal_dash_to_hash' for t in join['transformation_ids']):
            return False
        if member['source_document_id'] is not None:
            source = documents[member['source_document_id']]['rows'][member['source_row_index']]['sequence']
        else:
            source = inline[member['key']['input_binding_id']]['rows'][member['source_row_index']]['sequence']
        actual = alignment['rows'][index]['sequence']
        kinds = [transforms[t]['kind'] for t in join['transformation_ids']]
        if 'uppercase' in kinds:
            source = source.upper()
        # An unrecorded replacement of original terminal dashes by hashes must
        # not acquire original-hash provenance merely through a shared header.
        # The native count operation uses this supplied alignment, not an
        # automatically substituted original or reconstructed alignment.
        if actual.replace('-', '') != source.replace('-', ''):
            return False
    return True


def compile_family(sheet, request, outcomes):
    """Compile the declared family from saved results; never compute a p value.

    Returns (TestFamily, p cells, qualifications). Incomplete eligibility cannot
    substantiate a caller's complete-family assertion. Filtered rows never set
    the size of an all-eligible population by themselves.
    """
    plan, source = request['family'], request['p_values']
    require(plan['analysis_ids'] == [sheet['analysis']['analysis_id']], 'family_analysis_conflict')
    require(set(plan['category_ids']) <= set(sheet['analysis']['category_ids']), 'family_category_unknown')
    records, complete, qualifications = [], True, []
    statistics = []
    for identity in dependencies(request):
        outcome = outcomes[identity]
        if outcome['value'] is None or outcome['status'] == 'invalid':
            return None, None, [need(sheet['analysis']['analysis_id'], request['request_id'], 'alignment_calculation_dependency_unavailable')]
        statistics.append(outcome['value'])
    eligible = []
    excluded = set()
    for result in statistics:
        require(result['analysis_id'] == sheet['analysis']['analysis_id'], 'family_result_analysis_conflict')
        require(result['category_id'] in plan['category_ids'], 'family_result_category_conflict')
        complete &= not any(row['reason'] == 'unresolved' for row in result['exclusions'])
        eligible.extend(row for row in result['omnibus' if plan['test_kind'] == 'omnibus' else 'pairs'])
        for row in result['exclusions']:
            if row['test_kind'] == plan['test_kind'] and row['reason'] != 'unresolved':
                excluded.add((result['category_id'], row['column_0based'], row['test_kind'],
                    tuple(row['group_pair']) if row['group_pair'] is not None else None))
    if source['kind'] == 'statistical_results':
        records = [(test_selector(row), row['test_id'], deepcopy(row['mathematical_p'])) for row in eligible]
    else:
        docs = {common.document_identity(d): d for d in sheet['documents']}
        observations = {(o['document_id'], o['row_index']): o for o in sheet['native_observations'] if o['field'] == 'metacats_p_value'}
        joins = {(r['table_id'], r['row_index']): r for r in sheet['native_test_associations']}
        eligible_keys = {test_selector(row) for row in eligible}
        expected_categories = {result['category_id'] for result in statistics}
        if statistics:
            require(expected_categories == set(plan['category_ids']), 'family_category_population_missing')
        raw_complete = True
        observed_categories = set()
        for tid in source['table_ids']:
            require(tid in docs and docs[tid]['kind'] in ('metacats_chisq', 'metacats_pair', 'metacats_raw_r'), 'native_family_table_unknown')
            wrapper, table = docs[tid], docs[tid]['value']
            kind = table['kind'] if wrapper['kind'] == 'metacats_raw_r' else ('omnibus' if wrapper['kind'] == 'metacats_chisq' else 'pairwise')
            require(kind == plan['test_kind'] and table['category_id'] in plan['category_ids'], 'native_family_table_scope_conflict')
            raw_complete &= wrapper['kind'] == 'metacats_raw_r' and table['completeness'] == 'complete'
            rows = table.get('rows')
            if rows is None:
                rows = table['omnibus_rows'] if kind == 'omnibus' else table['pair_rows']
            # An empty retained table has no positive-df or explicit exclusion
            # evidence. Complete saved statistics can separately prove zero.
            if rows:
                observed_categories.add(table['category_id'])
            for row in rows:
                joined = joins.get((tid, row['row_index']))
                if joined is None or joined['state'] not in ('resolved', 'wrong_native_label'):
                    complete = False
                    continue
                key = (joined['category_id'], joined['column_0based'], joined['test_kind'], tuple(joined['group_ids']))
                if statistics:
                    if key not in eligible_keys:
                        exclusion = (key[0], key[1], key[2], key[3] if key[2] == 'pairwise' else None)
                        complete &= exclusion in excluded
                        continue
                elif 'df' not in row or row['df']['state'] != 'available':
                    complete = False
                    continue
                elif row['df']['value'] <= 0:
                    continue
                obs = observations[(tid, row['row_index'])]; native_number = obs['number']
                cell = numeric_cell(native_number['value'], state=native_number['state'], unit='probability',
                    origin='native_observation', population_id=joined['test_id'], method_id='metacats_native_unadjusted_p_v1', evidence=obs['evidence'])
                records.append((key, joined['test_id'], cell))
        if statistics:
            complete &= {key for key, _, _ in records} == eligible_keys
        else:
            complete &= raw_complete and observed_categories == set(plan['category_ids'])
    selectors, test_ids = {}, set()
    for key, identity, value in records:
        require(key not in selectors and identity not in test_ids, 'family_test_identity_ambiguous')
        selectors[key] = (identity, value); test_ids.add(identity)
    if plan['selection'] == 'explicit_tests':
        wanted = [selector(row) for row in plan['tests']]
        if any(key not in selectors for key in wanted):
            return None, None, [need(sheet['analysis']['analysis_id'], request['request_id'], 'metacats_test_family_incomplete')]
        records = [(key, *selectors[key]) for key in wanted]
        # Every explicitly selected test has its own positive-df proof. Omitted
        # unrelated tests do not turn this declared subset into a larger family.
        complete = True
    elif source['kind'] == 'statistical_results':
        require({r['category_id'] for r in statistics} == set(plan['category_ids']), 'family_category_population_missing')
    if plan['population_state'] == 'complete' and not complete:
        return None, None, [need(sheet['analysis']['analysis_id'], request['request_id'], 'metacats_test_family_incomplete')]
    identities = [identity for _, identity, _ in records]
    family = {k: deepcopy(v) for k, v in plan.items() if k not in ('selection', 'tests')}
    family['test_ids'] = identities
    if family['population_state'] == 'complete':
        require(family['total_test_count'] is None or family['total_test_count'] == len(identities), 'family_declared_count_conflict')
        family['total_test_count'] = len(identities)
    native.validate_test_family(family)
    if not complete:
        qualifications.append(need(sheet['analysis']['analysis_id'], request['request_id'], 'metacats_test_family_incomplete'))
    return family, [{'test_id': identity, 'value': value} for _, identity, value in records], qualifications


def _quantity(cell, *, population, unit, method=None, origin='derived'):
    shape(cell, {'value', 'state', 'unit', 'origin', 'numerator', 'denominator', 'population_ref', 'method', 'evidence', 'requirement_ids'})
    require(cell['population_ref'] == population and cell['unit'] == unit, 'quantity_population_or_unit_conflict')
    common.text(cell['method']); require(method is None or cell['method'] == method, 'quantity_method_conflict')
    require(cell['state'] in shared.STATES and cell['origin'] == origin, 'quantity_state_invalid')
    for key in ('value', 'numerator', 'denominator'):
        number(cell[key], nullable=True)
    require((cell['value'] is not None) == (cell['state'] == 'available'), 'quantity_availability_conflict')
    common.evidence(cell['evidence']); common.strings(cell['requirement_ids'])
    if unit == 'fraction' and cell['value'] is not None and cell['numerator'] is not None and cell['denominator'] not in (None, 0):
        require(cell['value'] == cell['numerator'] / cell['denominator'], 'quantity_ratio_conflict')


def _shared_result(value, request, sheet):
    kind = request['kind']
    if kind == 'ungapped_map':
        alignment = lookup_alignment(sheet, request['alignment_id']); require(alignment is not None, 'result_alignment_unknown')
        common.array(value)
        expected = [(i, j) for i in request['row_indices'] for j in range(len(alignment['rows'][i]['sequence']))]
        require([(r['row_index'], r['column_0based']) for r in value] == expected, 'coordinate_population_conflict')
        offsets = {i: 0 for i in request['row_indices']}
        for row in value:
            shape(row, {'alignment_id', 'row_index', 'column_0based', 'ungapped_position_0based'})
            require(row['alignment_id'] == request['alignment_id'], 'coordinate_alignment_conflict')
            symbol = alignment['rows'][row['row_index']]['sequence'][row['column_0based']]
            require(row['ungapped_position_0based'] == (None if symbol == '-' else offsets[row['row_index']]), 'coordinate_value_conflict')
            offsets[row['row_index']] += symbol != '-'
        return
    population_kind = 'composition' if kind == 'function_composition' else 'taxonomy' if kind == 'taxonomy' else 'alignments'
    population = lookup_population(sheet, population_kind, request['population_id']); require(population is not None, 'result_population_unknown')
    pid = population['population_id']
    require(value['population_id'] == pid, 'result_population_conflict')
    if kind == 'alignment':
        classifications = ('gap', 'canonical', 'ambiguity', 'stop', 'other_nongap')
        shape(value, {'population_id', 'alignment_id', 'member_count', 'site_count', 'cell_count', 'sites', 'rows', 'pairs', 'identical_sequence_groups',
            *(k + suffix for k in classifications for suffix in ('_cells', '_fraction'))})
        require(value['alignment_id'] == population['alignment_id'], 'result_alignment_conflict')
        for key, unit, method in (('member_count', 'rows', 'selected_row_count'), ('site_count', 'columns', 'selected_column_count'), ('cell_count', 'characters', 'selected_cell_count')):
            _quantity(value[key], population=pid, unit=unit, method=method)
        for key, expected in (('member_count', len(population['row_indices'])), ('site_count', len(population['columns_0based'])), ('cell_count', len(population['row_indices']) * len(population['columns_0based']))):
            require(value[key]['value'] is None or value[key]['value'] == expected, 'alignment_denominator_conflict')
        for key in classifications:
            _quantity(value[key + '_cells'], population=pid, unit='characters', method=key + '_symbol_count')
            _quantity(value[key + '_fraction'], population=pid, unit='fraction', method=key + '_cell_fraction')
        require([r['column_0based'] for r in value['sites']] == population['columns_0based'], 'site_population_conflict')
        for row in value['sites']:
            shape(row, {'column_0based', 'symbol_counts', *(k + '_count' for k in classifications), 'gap_fraction', 'canonical_fraction', 'canonical_majority_fraction', 'canonical_entropy_bits'})
            common.array(row['symbol_counts']); symbols = set()
            for item in row['symbol_counts']:
                shape(item, {'symbol', 'count'}); require(type(item['symbol']) is str and len(item['symbol']) == 1 and item['symbol'] not in symbols, 'site_symbol_invalid'); symbols.add(item['symbol']); common.integer(item['count'], minimum=1)
            for key in classifications:
                _quantity(row[key + '_count'], population=pid, unit='characters', method=key + '_symbol_count')
            for key in ('gap_fraction', 'canonical_fraction', 'canonical_majority_fraction', 'canonical_entropy_bits'):
                method = 'site_' + key if key in ('gap_fraction', 'canonical_fraction') else key
                _quantity(row[key], population=pid, unit='bits' if key.endswith('bits') else 'fraction', method=method)
        require([r['row_index'] for r in value['rows']] == population['row_indices'], 'row_population_conflict')
        for row in value['rows']:
            shape(row, {'row_index', 'nongap_count', 'matrix_occupancy'})
            _quantity(row['nongap_count'], population=pid, unit='characters', method='row_nongap_count')
            _quantity(row['matrix_occupancy'], population=pid, unit='fraction', method='row_matrix_occupancy')
        require([[r['row_a'], r['row_b']] for r in value['pairs']] == request['pairs'], 'pair_population_conflict')
        pair_keys = ('identical_positions', 'substitutions', 'both_gap_positions', 'a_gap_only_positions', 'b_gap_only_positions', 'unpaired_nongap_ambiguous_positions')
        for row in value['pairs']:
            shape(row, {'row_a', 'row_b', *pair_keys, 'identity_fraction'})
            for key in pair_keys:
                _quantity(row[key], population=pid, unit='columns', method='pairwise_' + key)
            _quantity(row['identity_fraction'], population=pid, unit='fraction', method='pairwise_canonical_identity')
        common.array(value['identical_sequence_groups']); seen = set()
        for row in value['identical_sequence_groups']:
            shape(row, {'row_indices', 'size'}); common.indices(row['row_indices'])
            require(len(row['row_indices']) > 1 and set(row['row_indices']) <= set(population['row_indices']) and not seen.intersection(row['row_indices']), 'identical_group_population_conflict'); seen.update(row['row_indices'])
            _quantity(row['size'], population=pid, unit='rows', method='identical_final_sequence_group_size')
    elif kind == 'original_coverage':
        shape(value, {'population_id', 'alignment_id', 'rows', 'missing_requirements', 'diagnostics'})
        require(value['alignment_id'] == population['alignment_id'], 'coverage_alignment_conflict')
        members = coverage_operands(sheet, population); require(members is not None, 'coverage_original_identity_missing')
        require([(r['row_index'], r['member']) for r in value['rows']] == [(r['row']['row_index'], r['member']) for r in members], 'coverage_member_conflict')
        common.reports({'requirements': value['missing_requirements'], 'diagnostics': value['diagnostics']})
        for row in value['rows']:
            shape(row, {'row_index', 'member', 'original_length', 'original_covered_positions', 'original_member_coverage'})
            for key in ('original_length', 'original_covered_positions', 'original_member_coverage'):
                _quantity(row[key], population=pid, unit='fraction' if key.endswith('coverage') else 'positions', origin='native_observed' if key == 'original_length' else 'derived')
    elif kind == 'function_composition':
        shape(value, {'population_id', 'unit', 'total_members', 'members_with_recorded_assignment', 'members_without_recorded_assignment', 'rows'})
        require(value['unit'] == population['unit'], 'composition_unit_conflict')
        for key in ('total_members', 'members_with_recorded_assignment', 'members_without_recorded_assignment'):
            _quantity(value[key], population=pid, unit='members')
        common.unique(value['rows'], 'function_key')
        allowed_functions = {r['function_key'] for r in sheet['associations']['functions']} | {r['canonical_function_key'] for r in sheet['associations']['function_equivalences']}
        for row in value['rows']:
            shape(row, {'function_key', 'member_subjects', 'assigned_members', 'fraction_all', 'fraction_recorded'})
            require(row['function_key'] in allowed_functions, 'composition_function_unknown')
            common.unique(row['member_subjects'], shared.subject)
            require(all(s in population['member_subjects'] for s in row['member_subjects']), 'composition_member_unknown')
            for key in ('assigned_members', 'fraction_all', 'fraction_recorded'):
                _quantity(row[key], population=pid, unit='members' if key == 'assigned_members' else 'fraction')
    else:
        keys = {'known_members': 'members', 'unknown_members': 'members', 'distinct_known_taxa': 'taxa', 'same_taxon_pairs': 'pairs', 'known_taxon_pairs': 'pairs', 'same_taxon_pair_fraction': 'fraction'}
        shape(value, {'population_id', 'rank', 'rows', *keys}); require(value['rank'] == request['rank'], 'taxonomy_rank_conflict')
        for key, unit in keys.items():
            _quantity(value[key], population=pid, unit=unit)
        common.unique(value['rows'], 'taxon_id')
        for row in value['rows']:
            shape(row, {'taxon_id', 'member_subjects', 'member_count'}); common.text(row['taxon_id'])
            common.unique(row['member_subjects'], shared.subject)
            require(all(s in population['member_subjects'] for s in row['member_subjects']), 'taxonomy_member_unknown')
            _quantity(row['member_count'], population=pid, unit='members')


def _calculated_cells(value, method):
    if type(value) is dict:
        if 'method_id' in value and 'population_id' in value and 'uncertainty' in value:
            require(value['origin'] == 'calculated' and value['method_id'] == method, 'calculated_cell_origin_or_method_conflict')
        for child in value.values():
            _calculated_cells(child, method)
    elif type(value) is list:
        for child in value:
            _calculated_cells(child, method)


def _identity(kind, payload):
    return kind + ':' + hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def _count_result(value, request, sheet):
    bio = request['kind'] == 'biological_group_counts'
    (biological.validate_biological_counts if bio else native.validate_group_counts)(value)
    population = lookup_population(sheet, 'alignments', request['population_id']); require(population is not None, 'count_population_unknown')
    alignment = lookup_alignment(sheet, population['alignment_id'])
    require(value['analysis_id'] == sheet['analysis']['analysis_id'] and value['category_id'] == request['category_id'] and value['population_id'] == population['population_id'] and value['alignment_id'] == population['alignment_id'], 'count_scope_conflict')
    params = {k: request[k] for k in (('case_policy', 'terminal_gap_policy', 'original_hash_policy') if bio else ('case_policy', 'terminal_mask', 'native_input_hash_policy'))}
    require(value['method_parameters'] == params, 'count_parameters_conflict')
    assignments = [r for r in sheet['biological_assignments' if bio else 'native_group_assignments'] if r['category_id'] == request['category_id'] and r['alignment_id'] == alignment['alignment_id']]
    if bio:
        group_population = next((p for p in sheet['biological_group_populations'] if p['group_population_id'] == request['group_population_id']), None)
        require(value['group_population'] == group_population, 'count_group_population_conflict')
    else:
        groups = [g for g in sheet['native_group_columns'] if g['category_id'] == request['category_id']]
        require(value['group_order'] == groups and groups and native_input_provenance(sheet, population), 'native_count_provenance_conflict')
    require([r['column_0based'] for r in value['sites']] == population['columns_0based'], 'count_site_population_conflict')
    for site in value['sites']:
        payload = {'analysis_id': value['analysis_id'], 'population': population, 'alignment_id': alignment['alignment_id'], 'artifact': alignment['artifact'], 'category_id': request['category_id'], 'column': site['column_0based'], 'parameters': params, 'assignments': sorted(assignments, key=lambda r: r['row_index'])}
        payload['group_population' if bio else 'group_order'] = value['group_population' if bio else 'group_order']
        require(site['table_id'] == _identity('biological_group_counts' if bio else 'metacats_counts_v2', payload), 'count_identity_conflict')
        rows = list(site['unresolved_row_indices'])
        for key in ('included_rows_by_group', 'excluded_terminal_rows_by_group', 'excluded_original_hash_rows_by_group'):
            rows += [i for group in site[key] for i in group]
        require(set(rows) == set(population['row_indices']), 'count_row_population_conflict')


def _dependent_result(value, request, dependency):
    kind = request['kind']; bio = kind.startswith('biological_')
    require(value['analysis_id'] == dependency['analysis_id'] and value['category_id'] == dependency['category_id'], 'result_dependency_scope_conflict')
    if kind in STAT_KINDS:
        (biological.validate_biological_statistics if bio else native.validate_statistics)(value)
        params = {k: deepcopy(v) for k, v in request.items() if k not in ('kind', 'request_id', 'counts_request_id')}
        require(value['method_parameters'] == params, 'statistics_parameters_conflict')
        sites = {s['table_id']: s for s in dependency['sites']}
        groups = [g['group_id'] for g in dependency['group_population']['groups' ]] if bio else [g['group_id'] for g in dependency['group_order']]
        seen = set()
        for row in value['omnibus'] + value['pairs']:
            require(row['raw_table_id'] in sites, 'statistics_count_unknown'); site = sites[row['raw_table_id']]
            require(row['column_0based'] == site['column_0based'] and row['raw_symbols'] == site['symbols'], 'statistics_count_conflict')
            require(row['group_ids'] == groups if row['kind'] == 'omnibus' else row['group_ids'] in request['selected_pairs'], 'statistics_groups_conflict')
            require(row['test_id'] == _identity('biological_group_test' if bio else 'metacats_test', {'raw_table_id': site['table_id'], 'kind': row['kind'], 'groups': row['group_ids'], 'parameters': params}), 'statistics_identity_conflict')
            require(bio or not row['native_observation_ids'], 'calculation_observation_identity_conflict')
            if not bio:
                expected_method = 'metacats_' + row['kind'] + '_' + params['alphabet'] + '_' + params['pair_df_policy'] + '_v1'
                require(row['method_id'] == expected_method, 'statistics_method_conflict')
                _calculated_cells(row, expected_method)
            seen.add((row['column_0based'], row['kind'], tuple(row['group_ids']) if row['kind'] == 'pairwise' else None))
        for row in value['exclusions']:
            key = (row['column_0based'], row['test_kind'], tuple(row['group_pair']) if row['group_pair'] is not None else None)
            require(key not in seen, 'statistics_duplicate_selection'); seen.add(key)
        expected = {(s['column_0based'], 'omnibus', None) for s in dependency['sites']} | {(s['column_0based'], 'pairwise', tuple(pair)) for s in dependency['sites'] for pair in request['selected_pairs']}
        require(seen == expected, 'statistics_population_incomplete')
    elif kind in EFFECT_KINDS:
        (biological.validate_biological_effects if bio else native.validate_effects)(value)
        require(value['zero_margin_policy'] == request['zero_margin_policy'], 'effect_parameters_conflict')
        require([(r['raw_table_id'], r['column_0based']) for r in value['sites']] == [(r['table_id'], r['column_0based']) for r in dependency['sites']], 'effect_site_population_conflict')
        for row in value['sites']:
            require([p['group_ids'] for p in row['pairs']] == request['selected_pairs'], 'effect_pair_population_conflict')
        if not bio:
            _calculated_cells(value, 'metacats_raw_descriptive_effect_v1')
    else:
        validate_expected_count_adequacy(value)
        require(value['statistics_kind'] == request['statistics_kind'], 'adequacy_statistics_kind_conflict')
        fields = ('test_id', 'raw_table_id', 'kind', 'column_0based', 'group_ids')
        require([{k: r[k] for k in fields} for r in value['rows']] == [{k: r[k] for k in fields} for r in dependency['omnibus'] + dependency['pairs']], 'adequacy_test_population_conflict')


@closed
def validate_metacats_components(components: dict, *, sheet: dict) -> dict:
    sheet = validate_metacats_sheet(sheet)
    shape(components, {'schema_version', 'analysis_id', 'parameters', 'results', 'requirements', 'diagnostics'})
    require(components['schema_version'] == VERSION and components['analysis_id'] == sheet['analysis']['analysis_id'], 'components_identity_conflict')
    parameters = validate_metacats_parameters(components['parameters']); common.reports(components)
    outcomes = common.unique(components['results'], 'request_id')
    require([r['request_id'] for r in components['results']] == [r['request_id'] for r in parameters['requests']], 'outcome_request_population_conflict')
    for request in parameters['requests']:
        outcome = outcomes[request['request_id']]
        shape(outcome, {'request_id', 'kind', 'status', 'value', 'requirements', 'diagnostics'})
        require(outcome['kind'] == request['kind'] and outcome['status'] in ('ok', 'partial', 'invalid'), 'outcome_kind_or_status_conflict')
        common.reports(outcome)
        require(all(r in components['requirements'] for r in outcome['requirements']) and all(d in components['diagnostics'] for d in outcome['diagnostics']), 'component_report_omitted')
        value, kind = outcome['value'], request['kind']
        unavailable = any(outcomes[d]['value'] is None or outcomes[d]['status'] == 'invalid' for d in dependencies(request))
        if value is None:
            require(outcome['status'] != 'ok' and outcome['requirements'], 'null_outcome_without_requirement')
            if unavailable:
                require(any(r['reason_code'] == 'alignment_calculation_dependency_unavailable' for r in outcome['requirements']), 'dependency_requirement_missing')
            continue
        require(not unavailable, 'result_from_unavailable_dependency')
        if kind in COMMON_KINDS:
            _shared_result(value, request, sheet)
        elif kind in COUNT_KINDS:
            _count_result(value, request, sheet)
        elif kind in STAT_KINDS | EFFECT_KINDS | {'expected_adequacy'}:
            _dependent_result(value, request, outcomes[dependencies(request)[0]]['value'])
        else:
            native.validate_multiplicity(value)
            family, p_values, qualifications = compile_family(sheet, request, outcomes)
            require(family is not None and value['family'] == family, 'multiplicity_family_conflict')
            require([{'test_id': row['test_id'], 'value': row['input_p']} for row in value['results']] == p_values, 'multiplicity_source_p_conflict')
            require(all(value[k] == request[k] for k in ('method', 'alpha', 'dependence_assumption')), 'multiplicity_parameters_conflict')
            for row in value['results']:
                _calculated_cells(row['adjusted_p'], 'metacats_' + request['method'] + '_v1')
            require(all(r in outcome['requirements'] for r in qualifications), 'family_qualification_omitted')
        if type(value) is dict and 'status' in value:
            require(outcome['status'] == value['status'] or outcome['status'] == 'partial' and value['status'] == 'ok' and outcome['requirements'], 'outcome_status_conflict')
            require(all(r in outcome['requirements'] for r in value['requirements']), 'outcome_requirement_omitted')
        require(outcome['status'] != 'ok' or not outcome['requirements'], 'outcome_ok_with_requirements')
    return deepcopy(components)


__all__ = ['validate_metacats_sheet', 'validate_metacats_parameters', 'validate_metacats_components']
