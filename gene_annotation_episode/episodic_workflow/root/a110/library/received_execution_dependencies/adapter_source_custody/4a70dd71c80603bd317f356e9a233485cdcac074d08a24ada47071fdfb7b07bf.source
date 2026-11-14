"""Pure, closed group/metadata/native-identity association contracts.

Original input authentication belongs to the adapter. These functions validate
only supplied occurrences, physical rows, categories and native observations.
"""
from __future__ import annotations

from copy import deepcopy
from functools import wraps
from itertools import combinations
from urllib.parse import quote, unquote

from . import bvbrc_alignment_provider_contracts as c
from .bvbrc_metacats_biological_contracts import validate_biological_group_population

PREFIX = 'bvbrc_metacats_association_'
SET_KEYS = ('categories', 'groups', 'metadata_members', 'auto_group_entries', 'biological_assignments',
    'biological_group_populations', 'native_group_assignments', 'native_group_columns', 'exported_groups',
    'native_test_associations', 'requirements', 'diagnostics')
DECL_KEYS = ('version', 'analysis_id', 'metadata_joins', 'categories', 'explicit_memberships',
    'auto_group_entries', 'group_sources', 'biological_group_populations', 'native_group_maps',
    'r_columns', 'exported_group_joins', 'native_test_joins')


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
            raise ValueError(PREFIX + str(exc).removeprefix(c.PREFIX)) from exc
        except (KeyError, TypeError, IndexError, OverflowError, UnicodeError, RecursionError) as exc:
            raise ValueError(PREFIX + 'shape_invalid') from exc
    return checked


def group_id(category, raw):
    c.text(category); c.text(raw, empty=True)
    return 'metacats_group:' + quote(category, safe='') + '/' + quote(raw, safe='')


def group_value(identity, category):
    c.text(identity); prefix = 'metacats_group:' + quote(category, safe='') + '/'
    require(identity.startswith(prefix), 'group_category_conflict')
    raw = unquote(identity[len(prefix):], errors='strict')
    require(group_id(category, raw) == identity, 'group_identity_noncanonical')
    return raw


def context(analysis, documents, associations):
    c.shape(analysis, ('analysis_id', 'mode', 'alignment_id', 'metadata_document_id', 'category_ids', 'adjusted_matrix_ids', 'chisq_table_ids', 'pair_table_ids', 'raw_r_table_ids', 'output_role_evidence'))
    c.text(analysis['analysis_id']); require(analysis['mode'] in ('files', 'groups', 'auto'), 'input_mode_invalid')
    c.strings(analysis['category_ids']); c.evidence(analysis['output_role_evidence'])
    docs, alignments, _ = c.document_maps(documents)
    for field, kind in (('alignment_id', 'alignment'), ('metadata_document_id', 'metadata')):
        c.text(analysis[field], nullable=True)
        require(analysis[field] is None or analysis[field] in docs and docs[analysis[field]]['kind'] == kind, 'analysis_document_unknown')
    for field, kind in (('adjusted_matrix_ids', 'adjusted_matrix'), ('chisq_table_ids', 'metacats_chisq'), ('pair_table_ids', 'metacats_pair'), ('raw_r_table_ids', 'metacats_raw_r')):
        c.strings(analysis[field])
        require(all(i in docs and docs[i]['kind'] == kind and docs[i]['value']['category_id'] in analysis['category_ids'] for i in analysis[field]), 'analysis_native_document_conflict')
    c.shape(associations, c.ASSOCIATION_KEYS)
    for rows in associations.values():
        c.array(rows)
    members = c.unique(associations['original_members'], lambda m: c.member_key(m['key']))
    records = c._source_records(associations['source_records'])
    transforms = c._transformations(associations['transformations'], members, alignments)
    c._row_members(associations['row_members'], members, alignments, transforms)
    c._semantic_assignments(associations, members, records)
    return docs, alignments, members, records


def category_plan(row, analysis, docs):
    c.shape(row, ('category_id', 'metadata', 'metadata_column_index_0based', 'raw_heading_token', 'native_category_ordinal_1based', 'native_output_stem', 'input_mode', 'group_identity_rule', 'evidence'))
    require(row['category_id'] in analysis['category_ids'] and row['input_mode'] == analysis['mode'] and row['group_identity_rule'] == 'exact_category_value', 'category_scope_invalid')
    c.text(row['metadata'], nullable=True); c.integer(row['metadata_column_index_0based'], nullable=True)
    c.text(row['raw_heading_token'], empty=True, nullable=True); c.integer(row['native_category_ordinal_1based'], minimum=1, nullable=True)
    c.text(row['native_output_stem'], empty=True, nullable=True); c.evidence(row['evidence'])
    if row['metadata'] is not None:
        require(row['metadata'] in docs and docs[row['metadata']]['kind'] == 'metadata', 'category_metadata_unknown')
        require(row['metadata'] == analysis['metadata_document_id'], 'category_original_metadata_conflict')
        require(row['metadata_column_index_0based'] is not None, 'category_column_missing')
        headers = docs[row['metadata']]['value']['header_tokens']; column = row['metadata_column_index_0based']
        if headers is not None:
            require(column < len(headers) and row['raw_heading_token'] == headers[column], 'category_heading_conflict')
        else:
            require(row['raw_heading_token'] is None, 'category_heading_without_header')
    else:
        require(row['metadata_column_index_0based'] is None and row['raw_heading_token'] is None, 'category_metadata_missing')


def assignment(row, analysis, alignments, members):
    c.shape(row, ('category_id', 'alignment_id', 'row_index', 'member_key', 'group_id', 'state', 'evidence'))
    require(row['category_id'] in analysis['category_ids'] and row['alignment_id'] == analysis['alignment_id'], 'assignment_scope_invalid')
    c.row_ref({k: row[k] for k in ('alignment_id', 'row_index')}, alignments); c.evidence(row['evidence'])
    require(row['state'] in ('resolved', 'missing', 'conflicting'), 'assignment_state_invalid')
    c.text(row['group_id'], nullable=True)
    if row['group_id'] is not None:
        group_value(row['group_id'], row['category_id'])
    require(row['state'] != 'resolved' or row['group_id'] is not None, 'resolved_group_missing')
    require(row['state'] != 'missing' or row['group_id'] is None, 'missing_group_conflict')
    if row['member_key'] is not None:
        require(c.member_key(row['member_key']) in members, 'assignment_member_unknown')


def group_source(row, members, records):
    c.shape(row, ('input_binding_id', 'group_id', 'source_record_id', 'evidence'))
    c.text(row['input_binding_id']); c.text(row['group_id']); c.text(row['source_record_id']); c.evidence(row['evidence'])
    require(row['source_record_id'] in records, 'group_source_record_unknown')


def auto_entries(rows, analysis, members):
    c.unique(rows, lambda r: (r['input_binding_id'], r['entry_index_0based'])); prior = {}
    require(not rows or analysis['mode'] == 'auto', 'auto_input_mode_conflict')
    for row in rows:
        c.shape(row, ('input_binding_id', 'entry_index_0based', 'original_parameter_pointer', 'feature_id', 'raw_group_value', 'member_keys', 'evidence'))
        c.text(row['input_binding_id']); c.integer(row['entry_index_0based']); c.pointer(row['original_parameter_pointer'])
        c.text(row['feature_id']); c.text(row['raw_group_value'], empty=True); c.key_list(row['member_keys'], members); c.evidence(row['evidence'])
        require(row['entry_index_0based'] > prior.get(row['input_binding_id'], -1), 'auto_entry_order_invalid')
        prior[row['input_binding_id']] = row['entry_index_0based']
        # Entry membership is explicit. Its fetched sequence binding may be a
        # separate binding from the original auto_groups parameter.


def native_row(document, index):
    rows = document.get('rows')
    if rows is None:
        rows = document['omnibus_rows'] if document['kind'] == 'omnibus' else document['pair_rows']
    matches = [r for r in rows if r['row_index'] == index]
    require(len(matches) == 1, 'native_row_unknown')
    return matches[0]


def exported(row, analysis, docs):
    c.shape(row, ('category_id', 'table_id', 'heading_index_0based', 'raw_heading_token', 'group_id', 'r_column_index_0based', 'state', 'evidence'))
    require(row['category_id'] in analysis['category_ids'] and row['table_id'] in analysis['chisq_table_ids'], 'exported_table_unknown')
    document = docs[row['table_id']]['value']; c.integer(row['heading_index_0based'])
    require(document['category_id'] == row['category_id'] and row['heading_index_0based'] < len(document['group_heading_tokens']) and row['raw_heading_token'] == document['group_heading_tokens'][row['heading_index_0based']], 'exported_heading_conflict')
    c.text(row['group_id'], nullable=True); c.integer(row['r_column_index_0based'], nullable=True); c.evidence(row['evidence'])
    require(row['state'] in ('resolved', 'wrong_native_label', 'missing', 'conflicting'), 'exported_state_invalid')
    if row['group_id'] is not None:
        raw = group_value(row['group_id'], row['category_id'])
        require(row['state'] != 'resolved' or raw == row['raw_heading_token'], 'exported_label_conflict')
        require(row['state'] != 'wrong_native_label' or raw != row['raw_heading_token'], 'wrong_label_without_difference')
    require(row['state'] not in ('resolved', 'wrong_native_label') or row['group_id'] is not None and row['r_column_index_0based'] is not None, 'exported_identity_missing')


def native_test(row, analysis, docs, alignments):
    c.shape(row, ('association_id', 'category_id', 'table_id', 'row_index', 'test_kind', 'alignment_id', 'column_0based', 'group_ids', 'r_columns_0based', 'raw_groups_token', 'test_id', 'state', 'evidence'))
    c.text(row['association_id']); require(row['category_id'] in analysis['category_ids'], 'test_category_unknown')
    require(row['table_id'] in analysis['chisq_table_ids'] + analysis['pair_table_ids'] + analysis['raw_r_table_ids'], 'test_table_unknown')
    document = docs[row['table_id']]['value']; require(document['category_id'] == row['category_id'], 'test_category_conflict')
    c.integer(row['row_index']); source = native_row(document, row['row_index'])
    expected_kind = ('omnibus' if docs[row['table_id']]['kind'] == 'metacats_chisq' else 'pairwise' if docs[row['table_id']]['kind'] == 'metacats_pair' else document['kind'])
    require(row['test_kind'] == expected_kind, 'test_kind_conflict')
    c.text(row['alignment_id'], nullable=True); c.integer(row['column_0based'], nullable=True)
    c.strings(row['group_ids']); c.indices(row['r_columns_0based']); c.text(row['raw_groups_token'], nullable=True, empty=True)
    c.text(row['test_id'], nullable=True); c.evidence(row['evidence']); require(row['state'] in ('resolved', 'missing', 'conflicting', 'wrong_native_label'), 'test_state_invalid')
    require(row['raw_groups_token'] == source.get('raw_groups_token'), 'test_groups_token_conflict')
    position = source.get('position_1based') if 'position_1based' in source else (source['position']['value'] if source['position']['state'] == 'available' else None)
    if row['alignment_id'] is not None:
        require(row['alignment_id'] == analysis['alignment_id'] and row['alignment_id'] in alignments, 'test_alignment_conflict')
    if row['column_0based'] is not None:
        require(position is not None and row['column_0based'] == position - 1 and row['alignment_id'] is not None, 'test_position_conflict')
        bound = max((len(r['sequence']) for r in alignments[row['alignment_id']]['rows']), default=0)
        require(row['column_0based'] < bound, 'test_column_outside_alignment')
    for gid in row['group_ids']:
        group_value(gid, row['category_id'])
    if row['state'] in ('resolved', 'wrong_native_label'):
        require(row['alignment_id'] is not None and row['column_0based'] is not None and row['test_id'] is not None and len(row['group_ids']) == len(row['r_columns_0based']) and len(row['group_ids']) >= 2, 'test_identity_missing')
        require(row['test_kind'] != 'pairwise' or len(row['group_ids']) == 2, 'pair_identity_invalid')
        def identity(record):
            position = record.get('position_1based') if 'position_1based' in record else record['position']['value'] if record['position']['state'] == 'available' else None
            if row['test_kind'] == 'omnibus':
                return (position,)
            if 'column_a_1based' in record:
                columns = tuple(sorted(record[k]['value'] for k in ('column_a_1based', 'column_b_1based'))) if all(record[k]['state'] == 'available' for k in ('column_a_1based', 'column_b_1based')) else None
                return position, columns
            return position, record['raw_groups_token']
        rows = document.get('rows', document.get('omnibus_rows' if row['test_kind'] == 'omnibus' else 'pair_rows', []))
        require(sum(identity(record) == identity(source) for record in rows) == 1, 'native_test_identity_duplicate')
    else:
        require(row['test_id'] is None, 'unresolved_test_identity')
    if 'column_a_1based' in source and row['r_columns_0based']:
        require(all(source[k]['state'] == 'available' for k in ('column_a_1based', 'column_b_1based')) and row['r_columns_0based'] == [source[k]['value'] - 1 for k in ('column_a_1based', 'column_b_1based')], 'raw_pair_column_conflict')


@closed
def validate_metacats_association_declarations(value: dict, *, analysis: dict, documents: tuple[dict, ...], associations: dict) -> dict:
    c.shape(value, DECL_KEYS); docs, alignments, members, records = context(analysis, documents, associations)
    require(value['version'] == 'bvbrc_metacats_context_v1' and value['analysis_id'] == analysis['analysis_id'], 'declaration_scope_invalid')
    for key in DECL_KEYS[2:]:
        c.array(value[key])
    categories = c.unique(value['categories'], 'category_id')
    for row in value['categories']:
        category_plan(row, analysis, docs)
    c.unique(value['metadata_joins'], lambda r: (r['metadata'], r['alignment']))
    for row in value['metadata_joins']:
        c.shape(row, ('metadata', 'id_column_index_0based', 'alignment', 'alignment_identity', 'case_policy', 'duplicate_policy', 'evidence'))
        require(row['metadata'] in docs and docs[row['metadata']]['kind'] == 'metadata' and row['alignment'] == analysis['alignment_id'] and row['alignment'] in alignments, 'metadata_join_scope_invalid')
        require(row['metadata'] == analysis['metadata_document_id'], 'metadata_join_original_input_conflict')
        c.integer(row['id_column_index_0based']); c.evidence(row['evidence'])
        require(row['alignment_identity'] in ('raw_header', 'member_label') and row['case_policy'] == 'preserve' and row['duplicate_policy'] == 'retain_unresolved', 'metadata_join_policy_invalid')
    c.unique(value['explicit_memberships'], lambda r: (r['category_id'], r['alignment_id'], r['row_index']))
    row_members = {(r['alignment_id'], r['row_index']): r for r in associations['row_members']}
    for row in value['explicit_memberships']:
        assignment(row, analysis, alignments, members)
        if row['member_key'] is not None:
            require((row['alignment_id'], row['row_index']) in row_members and row['member_key'] in row_members[(row['alignment_id'], row['row_index'])]['member_keys'], 'assignment_row_member_conflict')
    auto_entries(value['auto_group_entries'], analysis, members)
    require(not value['group_sources'] or analysis['mode'] == 'groups', 'group_source_mode_conflict')
    c.unique(value['group_sources'], lambda r: (r['category_id'], r['raw_group_value']))
    for row in value['group_sources']:
        c.shape(row, ('category_id', 'raw_group_value', 'bindings')); require(row['category_id'] in analysis['category_ids'], 'group_source_category_unknown')
        c.text(row['raw_group_value'], empty=True); c.array(row['bindings'])
        for binding in row['bindings']:
            group_source(binding, members, records)
    population_ids = set()
    for row in value['biological_group_populations']:
        require(row['kind'] in ('explicit', 'observed_metadata_groups'), 'population_plan_kind_invalid')
        if row['kind'] == 'explicit':
            c.shape(row, ('kind', 'population')); population = row['population']
            require(population['category_id'] in analysis['category_ids'], 'population_category_unknown')
            validate_biological_group_population(population, category_id=population['category_id']); identity = population['group_population_id']
            for group in population['groups']:
                require(group['group_id'] == group_id(population['category_id'], group['raw_group_value']), 'population_group_identity_conflict')
        else:
            c.shape(row, ('kind', 'group_population_id', 'category_id', 'order', 'include_metadata_only', 'evidence'))
            c.text(row['group_population_id']); c.evidence(row['evidence']); identity = row['group_population_id']
            require(row['category_id'] in categories and categories[row['category_id']]['metadata'] is not None and row['order'] == 'first_metadata_occurrence' and type(row['include_metadata_only']) is bool, 'population_plan_invalid')
        require(identity not in population_ids, 'population_duplicate'); population_ids.add(identity)
    c.unique(value['native_group_maps'], 'category_id')
    for row in value['native_group_maps']:
        c.shape(row, ('category_id', 'entries', 'completeness', 'evidence')); require(row['category_id'] in analysis['category_ids'] and row['completeness'] in c.COMPLETENESS, 'native_map_scope_invalid')
        c.evidence(row['evidence']); c.array(row['entries'])
        c.unique(row['entries'], lambda e: (e['raw_group_value'], e['native_group_ordinal'], e['group_id']))
        for entry in row['entries']:
            c.shape(entry, ('raw_group_value', 'native_group_ordinal', 'group_id', 'evidence')); c.integer(entry['native_group_ordinal'], minimum=1); c.evidence(entry['evidence'])
            require(entry['group_id'] == group_id(row['category_id'], entry['raw_group_value']), 'native_map_group_conflict')
    c.unique(value['r_columns'], 'category_id')
    for row in value['r_columns']:
        c.shape(row, ('category_id', 'adjusted_matrix', 'interpreter_version', 'columns', 'completeness', 'evidence'))
        require(row['category_id'] in analysis['category_ids'] and row['adjusted_matrix'] in analysis['adjusted_matrix_ids'] and docs[row['adjusted_matrix']]['value']['category_id'] == row['category_id'], 'r_evidence_matrix_conflict')
        c.text(row['interpreter_version']); c.evidence(row['evidence']); require(bool(row['evidence']) and row['completeness'] in c.COMPLETENESS, 'r_evidence_missing')
        c.unique(row['columns'], 'r_column_index_0based')
        for column in row['columns']:
            c.shape(column, ('r_column_index_0based', 'r_group_token', 'native_group_ordinal', 'group_id', 'evidence'))
            c.integer(column['r_column_index_0based']); c.text(column['r_group_token']); c.integer(column['native_group_ordinal'], minimum=1, nullable=True); c.text(column['group_id'], nullable=True); c.evidence(column['evidence'])
            require(column['native_group_ordinal'] is None or column['r_group_token'].strip() == str(column['native_group_ordinal']), 'r_token_ordinal_conflict')
            if column['group_id'] is not None:
                group_value(column['group_id'], row['category_id'])
        if row['completeness'] == 'complete':
            require([r['r_column_index_0based'] for r in row['columns']] == list(range(len(row['columns']))), 'r_column_order_invalid')
    c.unique(value['exported_group_joins'], lambda r: (r['table_id'], r['heading_index_0based']))
    for row in value['exported_group_joins']:
        exported(row, analysis, docs)
    c.unique(value['native_test_joins'], 'association_id'); c.unique(value['native_test_joins'], lambda r: (r['table_id'], r['row_index']))
    for row in value['native_test_joins']:
        native_test(row, analysis, docs, alignments)
    return deepcopy(value)


@closed
def validate_metacats_association_set(value: dict, *, analysis: dict, documents: tuple[dict, ...], associations: dict) -> dict:
    c.shape(value, SET_KEYS); docs, alignments, members, records = context(analysis, documents, associations)
    for rows in value.values():
        c.array(rows)
    categories = c.unique(value['categories'], 'category_id'); groups = c.unique(value['groups'], 'group_id')
    require(set(categories) == set(analysis['category_ids']), 'category_population_conflict')
    for row in value['categories']:
        c.shape(row, ('category_id', 'metadata_document_id', 'metadata_column_index_0based', 'raw_heading_token', 'native_category_ordinal_1based', 'native_output_stem', 'input_mode', 'group_ids', 'state', 'evidence'))
        plan = {k: v for k, v in row.items() if k not in ('group_ids', 'state', 'metadata_document_id')}
        plan.update(metadata=row['metadata_document_id'], group_identity_rule='exact_category_value')
        category_plan(plan, analysis, docs); c.strings(row['group_ids']); require(row['state'] in ('resolved', 'missing', 'conflicting'), 'category_state_invalid')
        require(set(row['group_ids']) == {g['group_id'] for g in value['groups'] if g['category_id'] == row['category_id']}, 'category_groups_conflict')
    for row in value['groups']:
        c.shape(row, ('group_id', 'category_id', 'raw_group_value', 'metadata_row_indices', 'member_keys', 'source_group_bindings', 'membership_completeness', 'evidence'))
        require(row['category_id'] in categories and row['group_id'] == group_id(row['category_id'], row['raw_group_value']), 'group_identity_conflict')
        c.indices(row['metadata_row_indices']); c.key_list(row['member_keys'], members); c.evidence(row['evidence'])
        require(row['membership_completeness'] in c.COMPLETENESS, 'group_completeness_invalid'); c.array(row['source_group_bindings'])
        category = categories[row['category_id']]
        for index in row['metadata_row_indices']:
            require(category['metadata_document_id'] is not None, 'group_metadata_unknown')
            source = native_row(docs[category['metadata_document_id']]['value'], index); column = category['metadata_column_index_0based']
            require(column < len(source['cells']) and source['cells'][column] == row['raw_group_value'], 'group_metadata_value_conflict')
        for source in row['source_group_bindings']:
            group_source(source, members, records)
            require(analysis['mode'] == 'groups', 'group_source_mode_conflict')
    metadata = c.unique(value['metadata_members'], lambda r: (r['metadata_document_id'], r['metadata_row_index'], r['id_column_index_0based']))
    row_members = {(r['alignment_id'], r['row_index']): r for r in associations['row_members']}
    for row in value['metadata_members']:
        c.shape(row, ('metadata_document_id', 'metadata_row_index', 'id_column_index_0based', 'raw_member_token', 'member_keys', 'alignment_rows', 'state', 'evidence'))
        require(row['metadata_document_id'] in docs and docs[row['metadata_document_id']]['kind'] == 'metadata', 'metadata_document_unknown')
        source = native_row(docs[row['metadata_document_id']]['value'], row['metadata_row_index']); c.integer(row['id_column_index_0based'])
        c.text(row['raw_member_token'], empty=True); c.key_list(row['member_keys'], members); c.evidence(row['evidence'])
        present = row['id_column_index_0based'] < len(source['cells'])
        require(row['raw_member_token'] == (source['cells'][row['id_column_index_0based']] if present else ''), 'metadata_member_token_conflict')
        require(row['state'] in ('resolved', 'missing', 'conflicting', 'native_duplicate_merge'), 'metadata_member_state_invalid')
        refs = c.unique(row['alignment_rows'], lambda r: c.row_ref(r, alignments))
        require(all(a == analysis['alignment_id'] for a, _ in refs), 'metadata_alignment_scope_conflict')
        require(row['state'] != 'resolved' or present and len(refs) == 1, 'metadata_resolved_identity_invalid')
        for key in row['member_keys']:
            require(any(ref in row_members and key in row_members[ref]['member_keys'] for ref in refs), 'metadata_member_row_conflict')
        for ref in refs:
            actual = alignments[ref[0]]['rows'][ref[1]]
            require(row['raw_member_token'] in (actual['member_label'], actual['raw_header']), 'metadata_alignment_token_conflict')
    auto_entries(value['auto_group_entries'], analysis, members)
    biological = c.unique(value['biological_assignments'], lambda r: (r['category_id'], r['alignment_id'], r['row_index']))
    for row in value['biological_assignments']:
        assignment(row, analysis, alignments, members)
        require(row['group_id'] is None or row['group_id'] in groups, 'assignment_group_unknown')
        if row['member_key'] is not None:
            ref = row['alignment_id'], row['row_index']
            require(ref in row_members and row['member_key'] in row_members[ref]['member_keys'], 'assignment_row_member_conflict')
    c.unique(value['biological_group_populations'], 'group_population_id')
    for population in value['biological_group_populations']:
        require(population['category_id'] in categories, 'population_category_unknown')
        validate_biological_group_population(population, category_id=population['category_id'])
        for group in population['groups']:
            require(group['group_id'] in groups and groups[group['group_id']]['category_id'] == population['category_id'] and groups[group['group_id']]['raw_group_value'] == group['raw_group_value'], 'population_group_conflict')
    columns = c.unique(value['native_group_columns'], lambda r: (r['category_id'], r['r_column_index_0based']))
    for row in value['native_group_columns']:
        c.shape(row, ('category_id', 'r_column_index_0based', 'r_group_token', 'native_group_ordinal', 'group_id', 'exported_heading_index_0based', 'exported_label_token', 'state', 'evidence'))
        require(row['category_id'] in categories, 'column_category_unknown'); c.integer(row['r_column_index_0based']); c.text(row['r_group_token'])
        c.integer(row['native_group_ordinal'], minimum=1, nullable=True); c.text(row['group_id'], nullable=True)
        require(row['native_group_ordinal'] is None or row['r_group_token'].strip() == str(row['native_group_ordinal']), 'r_token_ordinal_conflict')
        c.integer(row['exported_heading_index_0based'], nullable=True); c.text(row['exported_label_token'], empty=True, nullable=True); c.evidence(row['evidence'])
        require(row['state'] in ('resolved', 'wrong_native_label', 'unresolved'), 'column_state_invalid')
        require(row['group_id'] is None or row['group_id'] in groups and groups[row['group_id']]['category_id'] == row['category_id'], 'column_group_unknown')
        require(row['state'] == 'unresolved' or row['group_id'] is not None and row['native_group_ordinal'] is not None, 'column_identity_missing')
        require((row['exported_heading_index_0based'] is None) == (row['exported_label_token'] is None), 'column_export_identity_incomplete')
        if row['state'] == 'wrong_native_label':
            require(row['exported_label_token'] is not None and row['exported_label_token'] != groups[row['group_id']]['raw_group_value'], 'column_wrong_label_conflict')
        if row['exported_heading_index_0based'] is not None:
            require(any(e['category_id'] == row['category_id'] and e['r_column_index_0based'] == row['r_column_index_0based']
                and e['heading_index_0based'] == row['exported_heading_index_0based'] and e['raw_heading_token'] == row['exported_label_token']
                and e['group_id'] == row['group_id'] for e in value['exported_groups']), 'column_export_reference_missing')
    c.unique(value['native_group_assignments'], lambda r: (r['category_id'], r['alignment_id'], r['row_index']))
    for row in value['native_group_assignments']:
        c.shape(row, ('category_id', 'alignment_id', 'row_index', 'member_key', 'metadata_row_index', 'metadata_column_index', 'raw_group_value', 'native_group_ordinal', 'displayed_group_label', 'state', 'evidence'))
        key = row['category_id'], row['alignment_id'], row['row_index']; require(key in biological, 'native_assignment_biological_unknown')
        bio = biological[key]; require(row['member_key'] == bio['member_key'], 'native_assignment_member_conflict')
        c.integer(row['metadata_row_index'], nullable=True); c.integer(row['metadata_column_index'], nullable=True); c.text(row['raw_group_value'], empty=True, nullable=True)
        c.integer(row['native_group_ordinal'], minimum=1, nullable=True); c.text(row['displayed_group_label'], empty=True, nullable=True); c.evidence(row['evidence'])
        require(row['state'] in ('resolved', 'missing', 'conflicting', 'native_unlabeled'), 'native_assignment_state_invalid')
        require(row['state'] != 'resolved' or bio['state'] == 'resolved' and row['native_group_ordinal'] is not None, 'native_assignment_identity_missing')
        if bio['group_id'] is not None and bio['state'] == 'resolved':
            require(row['raw_group_value'] == groups[bio['group_id']]['raw_group_value'], 'native_assignment_group_conflict')
        if row['metadata_row_index'] is not None:
            cat = categories[row['category_id']]; require(cat['metadata_document_id'] is not None and row['metadata_column_index'] == cat['metadata_column_index_0based'], 'native_assignment_metadata_conflict')
            source = native_row(docs[cat['metadata_document_id']]['value'], row['metadata_row_index'])
            require(row['metadata_column_index'] < len(source['cells']) and row['raw_group_value'] == source['cells'][row['metadata_column_index']], 'native_assignment_metadata_value_conflict')
    c.unique(value['exported_groups'], lambda r: (r['table_id'], r['heading_index_0based']))
    for row in value['exported_groups']:
        exported(row, analysis, docs)
        if row['group_id'] is not None:
            require(row['group_id'] in groups, 'exported_group_unknown')
        if row['r_column_index_0based'] is not None:
            key = row['category_id'], row['r_column_index_0based']; require(key in columns, 'exported_column_unknown')
            require(row['state'] not in ('resolved', 'wrong_native_label') or columns[key]['group_id'] == row['group_id'], 'exported_column_group_conflict')
    c.unique(value['native_test_associations'], 'association_id'); c.unique(value['native_test_associations'], lambda r: (r['table_id'], r['row_index']))
    for row in value['native_test_associations']:
        native_test(row, analysis, docs, alignments)
        require(set(row['group_ids']) <= set(groups), 'test_group_unknown')
        for index, col in enumerate(row['r_columns_0based']):
            key = row['category_id'], col; require(key in columns, 'test_column_unknown')
            if row['state'] in ('resolved', 'wrong_native_label'):
                require(columns[key]['state'] != 'unresolved' and columns[key]['group_id'] == row['group_ids'][index], 'test_column_group_conflict')
        if row['state'] in ('resolved', 'wrong_native_label'):
            if row['test_kind'] == 'omnibus':
                require(row['r_columns_0based'] == sorted(index for cat, index in columns if cat == row['category_id']), 'omnibus_column_population_conflict')
            elif docs[row['table_id']]['kind'] == 'metacats_pair':
                candidates = set()
                for tid in analysis['chisq_table_ids']:
                    exports = [e for e in value['exported_groups'] if e['table_id'] == tid and e['category_id'] == row['category_id'] and e['state'] in ('resolved', 'wrong_native_label')]
                    exports.sort(key=lambda e: e['heading_index_0based'])
                    for a, b in combinations(exports, 2):
                        if a['raw_heading_token'] + ',' + b['raw_heading_token'] == row['raw_groups_token']:
                            candidates.add((a['r_column_index_0based'], b['r_column_index_0based'], a['group_id'], b['group_id']))
                expected = tuple(row['r_columns_0based'] + row['group_ids'])
                require(candidates == {expected}, 'pair_export_identity_ambiguous')
    c.reports(value)
    return deepcopy(value)


__all__ = ['validate_metacats_association_declarations', 'validate_metacats_association_set']
