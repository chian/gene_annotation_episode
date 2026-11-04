"""Extract supplied biological groups separately from authentic native identities.

No R column order is invented from metadata. Unknown joins keep useful groups,
native documents and explicit requirements; this module computes no statistics.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from itertools import combinations
import re
from urllib.parse import quote

from . import bvbrc_alignment_provider_contracts as common
from . import bvbrc_metacats_association_contracts as c
from .bvbrc_alignment_values import diagnostic, requirement


def _append_unique(target, values):
    for value in values:
        if value not in target:
            target.append(deepcopy(value))


def _metadata_members(plans, docs, associations):
    output = []
    row_members = {(r['alignment_id'], r['row_index']): r for r in associations['row_members']}
    for plan in plans:
        metadata = docs[plan['metadata']]['value']; alignment = docs[plan['alignment']]['value']
        index = plan['id_column_index_0based']; tokens = Counter(r['cells'][index] for r in metadata['rows'] if index < len(r['cells']))
        by_token = defaultdict(list)
        for row in alignment['rows']:
            by_token[row[plan['alignment_identity']]].append(row)
        for row in metadata['rows']:
            present = index < len(row['cells']); token = row['cells'][index] if present else ''
            matched = by_token[token] if present else []
            keys = []
            for match in matched:
                linked = row_members.get((alignment['alignment_id'], match['row_index']))
                if linked is not None:
                    _append_unique(keys, linked['member_keys'])
            state = ('resolved' if len(matched) == 1 and tokens[token] == 1 else 'conflicting') if matched else 'missing'
            output.append({'metadata_document_id': metadata['document_id'], 'metadata_row_index': row['row_index'],
                'id_column_index_0based': index, 'raw_member_token': token, 'member_keys': keys,
                'alignment_rows': [{'alignment_id': alignment['alignment_id'], 'row_index': r['row_index']} for r in matched],
                'state': state, 'evidence': deepcopy(plan['evidence'])})
    return output


def _native_tests(analysis, docs, columns, exported, r_evidence, explicit):
    results = []; explicit = {(r['table_id'], r['row_index']): r for r in explicit}
    by_category = defaultdict(list)
    for column in columns:
        by_category[column['category_id']].append(column)
    for tid in analysis['chisq_table_ids'] + analysis['pair_table_ids'] + analysis['raw_r_table_ids']:
        wrapper = docs[tid]; document = wrapper['value']; category = document['category_id']
        cols = {r['r_column_index_0based']: r for r in by_category[category]}
        is_raw = wrapper['kind'] == 'metacats_raw_r'
        kind = document['kind'] if is_raw else ('omnibus' if wrapper['kind'] == 'metacats_chisq' else 'pairwise')
        rows = (document['omnibus_rows'] if kind == 'omnibus' else document['pair_rows']) if is_raw else document['rows']
        prepared = []
        for row in rows:
            pos = row.get('position_1based') if 'position_1based' in row else row['position']['value'] if row['position']['state'] == 'available' else None
            selected, wrong = [], False
            if kind == 'omnibus':
                if category in r_evidence and r_evidence[category]['completeness'] == 'complete':
                    selected = sorted(cols)
            elif is_raw:
                if all(row[k]['state'] == 'available' for k in ('column_a_1based', 'column_b_1based')):
                    selected = [row[k]['value'] - 1 for k in ('column_a_1based', 'column_b_1based')]
            else:
                candidates = set()
                for source_tid in analysis['chisq_table_ids']:
                    maps = [g for g in exported if g['table_id'] == source_tid and g['category_id'] == category and g['state'] in ('resolved', 'wrong_native_label')]
                    maps.sort(key=lambda r: r['heading_index_0based'])
                    for a, b in combinations(maps, 2):
                        if a['raw_heading_token'] + ',' + b['raw_heading_token'] == row['raw_groups_token']:
                            candidates.add((a['r_column_index_0based'], b['r_column_index_0based'], a['state'] == 'wrong_native_label' or b['state'] == 'wrong_native_label'))
                if len(candidates) == 1:
                    a, b, wrong = candidates.pop(); selected = [a, b]
            # Distinct pairs at a site are distinct native tests. Reversing
            # columns does not make a repeated pair an independent test.
            identity = (pos, tuple(sorted(selected))) if kind == 'pairwise' else (pos,)
            prepared.append((row, pos, selected, wrong, identity))
        frequency = Counter(item[4] for item in prepared)
        for row, pos, selected, wrong, identity in prepared:
            if (tid, row['row_index']) in explicit:
                results.append(deepcopy(explicit[(tid, row['row_index'])])); continue
            available = len(selected) >= 2 and len(selected) == len(set(selected)) and all(i in cols and cols[i]['state'] != 'unresolved' and cols[i]['group_id'] is not None for i in selected)
            groups = [cols[i]['group_id'] for i in selected] if available else []
            available = available and len(groups) == len(set(groups))
            alignment = analysis['alignment_id']; column = pos - 1 if pos is not None else None
            bound = max((len(r['sequence']) for r in docs[alignment]['value']['rows']), default=0) if alignment is not None else 0
            position_ok = column is not None and 0 <= column < bound and frequency[identity] == 1
            state = ('wrong_native_label' if wrong or any(cols[i]['state'] == 'wrong_native_label' for i in selected) else 'resolved') if available and position_ok else 'missing'
            results.append({'association_id': tid + '/rows/' + str(row['row_index']) + '/association', 'category_id': category,
                'table_id': tid, 'row_index': row['row_index'], 'test_kind': kind, 'alignment_id': alignment,
                'column_0based': column if position_ok else None, 'group_ids': groups if available else [],
                'r_columns_0based': selected if available else [], 'raw_groups_token': row.get('raw_groups_token'),
                'test_id': 'native_test:' + quote(tid, safe='') + '/' + str(row['row_index']) if state != 'missing' else None,
                'state': state, 'evidence': deepcopy(r_evidence.get(category, {}).get('evidence', []))})
    return results


def extract_metacats_associations(*, analysis: dict, documents: tuple[dict, ...], associations: dict, declarations: dict) -> dict:
    try:
        declarations = c.validate_metacats_association_declarations(declarations, analysis=analysis, documents=documents, associations=associations)
        docs, alignments, members, records = c.context(analysis, documents, associations)
        result = {key: [] for key in c.SET_KEYS}
        def need(category, reason, role='metacats_group_association'):
            identity = analysis['analysis_id'] + '/' + quote(category, safe='') + '/' + reason
            record = requirement(identity, kind='scientific_metadata', role=role, reason_code=reason)
            if record not in result['requirements']:
                result['requirements'].append(record)
                result['diagnostics'].append(diagnostic(c.PREFIX + reason, path='/categories'))
        result['metadata_members'] = _metadata_members(declarations['metadata_joins'], docs, associations)
        result['auto_group_entries'] = deepcopy(declarations['auto_group_entries'])
        plans = {p['category_id']: p for p in declarations['categories']}; groups = {}
        def add_group(category, raw, *, evidence=(), metadata_row=None, keys=(), bindings=()):
            gid = c.group_id(category, raw)
            if gid not in groups:
                groups[gid] = {'group_id': gid, 'category_id': category, 'raw_group_value': raw,
                    'metadata_row_indices': [], 'member_keys': [], 'source_group_bindings': [],
                    'membership_completeness': 'unknown', 'evidence': []}
            group = groups[gid]
            if metadata_row is not None:
                _append_unique(group['metadata_row_indices'], [metadata_row])
            _append_unique(group['evidence'], evidence); _append_unique(group['member_keys'], keys); _append_unique(group['source_group_bindings'], bindings)
            return gid
        row_members = {(r['alignment_id'], r['row_index']): r for r in associations['row_members']}
        metadata_by_doc_row = defaultdict(list)
        for row in result['metadata_members']:
            metadata_by_doc_row[(row['metadata_document_id'], row['metadata_row_index'])].append(row)
        for category in analysis['category_ids']:
            plan = plans.get(category)
            result['categories'].append({'category_id': category, 'metadata_document_id': plan['metadata'] if plan else None,
                'metadata_column_index_0based': plan['metadata_column_index_0based'] if plan else None,
                'raw_heading_token': plan['raw_heading_token'] if plan else None,
                'native_category_ordinal_1based': plan['native_category_ordinal_1based'] if plan else None,
                'native_output_stem': plan['native_output_stem'] if plan else None, 'input_mode': analysis['mode'], 'group_ids': [],
                'state': 'resolved' if plan else 'missing', 'evidence': deepcopy(plan['evidence']) if plan else []})
            if plan and plan['metadata'] is not None:
                for row in docs[plan['metadata']]['value']['rows']:
                    column = plan['metadata_column_index_0based']
                    if column >= len(row['cells']):
                        need(category, 'metadata_category_cell_absent'); continue
                    linked = metadata_by_doc_row[(plan['metadata'], row['row_index'])]; keys = []
                    for relation in linked:
                        _append_unique(keys, relation['member_keys'])
                    add_group(category, row['cells'][column], evidence=plan['evidence'], metadata_row=row['row_index'], keys=keys)
            if analysis['mode'] == 'auto':
                for entry in declarations['auto_group_entries']:
                    add_group(category, entry['raw_group_value'], evidence=entry['evidence'], keys=entry['member_keys'])
                    if not entry['member_keys']:
                        need(category, 'auto_fetched_sequence_association_required')
            if not plan:
                need(category, 'category_definition_required')
        for source in declarations['group_sources']:
            add_group(source['category_id'], source['raw_group_value'], bindings=source['bindings'])
        for plan in declarations['biological_group_populations']:
            if plan['kind'] == 'explicit':
                for group in plan['population']['groups']:
                    add_group(plan['population']['category_id'], group['raw_group_value'], evidence=group['evidence'])
        for assignment in declarations['explicit_memberships']:
            if assignment['group_id'] is not None:
                add_group(assignment['category_id'], c.group_value(assignment['group_id'], assignment['category_id']), evidence=assignment['evidence'], keys=[assignment['member_key']] if assignment['member_key'] is not None else [])
        for mapping in declarations['native_group_maps']:
            for entry in mapping['entries']:
                add_group(mapping['category_id'], entry['raw_group_value'], evidence=entry['evidence'])
        for source in declarations['r_columns']:
            for column in source['columns']:
                if column['group_id'] is not None:
                    add_group(source['category_id'], c.group_value(column['group_id'], source['category_id']), evidence=column['evidence'])
        explicit = {(r['category_id'], r['alignment_id'], r['row_index']): r for r in declarations['explicit_memberships']}
        transforms = {t['transformation_id']: t for t in associations['transformations']}
        metadata_for_assignment = {}
        if analysis['alignment_id'] is not None:
            alignment = alignments[analysis['alignment_id']]
            for category in analysis['category_ids']:
                plan = plans.get(category)
                for row in alignment['rows']:
                    ref = alignment['alignment_id'], row['row_index']; link = row_members.get(ref)
                    key = link['member_keys'][0] if link and link['state'] in ('resolved', 'native_duplicate_merge') and len(link['member_keys']) == 1 else None
                    candidates, sources, conflict, ev = [], [], False, []
                    if plan and plan['metadata'] is not None:
                        for relation in result['metadata_members']:
                            if relation['metadata_document_id'] == plan['metadata'] and {'alignment_id': ref[0], 'row_index': ref[1]} in relation['alignment_rows']:
                                source = c.native_row(docs[plan['metadata']]['value'], relation['metadata_row_index']); col = plan['metadata_column_index_0based']
                                if col < len(source['cells']):
                                    candidates.append(c.group_id(category, source['cells'][col])); sources.append(relation['metadata_row_index'])
                                conflict |= relation['state'] != 'resolved'; _append_unique(ev, relation['evidence'])
                    if analysis['mode'] == 'auto' and link:
                        entries = [e for e in declarations['auto_group_entries'] if any(k in link['member_keys'] for k in e['member_keys'])]
                        rules = [transforms[t] for t in link['transformation_ids'] if transforms[t]['kind'] == 'native_duplicate_merge']
                        if len(rules) == 1 and rules[0]['rule'] == 'overwrite_last' and entries:
                            entries = [entries[-1]]
                        for entry in entries:
                            candidates.append(c.group_id(category, entry['raw_group_value'])); _append_unique(ev, entry['evidence'])
                    assignment_key = category, ref[0], ref[1]
                    if assignment_key in explicit:
                        biological = deepcopy(explicit[assignment_key])
                        if biological['state'] == 'resolved' and (conflict or any(g != biological['group_id'] for g in candidates)):
                            biological['state'] = 'conflicting'
                        _append_unique(biological['evidence'], ev)
                    else:
                        identities = list(dict.fromkeys(candidates))
                        state = 'conflicting' if conflict or len(identities) > 1 else ('resolved' if identities else 'missing')
                        biological = {'category_id': category, 'alignment_id': ref[0], 'row_index': ref[1], 'member_key': deepcopy(key),
                            'group_id': identities[0] if len(identities) == 1 else None, 'state': state, 'evidence': ev}
                    result['biological_assignments'].append(biological)
                    metadata_for_assignment[assignment_key] = sources[0] if len(sources) == 1 else None
                    if biological['state'] != 'resolved':
                        need(category, 'biological_row_membership_' + biological['state'])
                    elif biological['member_key'] is not None:
                        _append_unique(groups[biological['group_id']]['member_keys'], [biological['member_key']])
        else:
            for category in analysis['category_ids']:
                need(category, 'alignment_rows_required')
        for plan in declarations['biological_group_populations']:
            if plan['kind'] == 'explicit':
                result['biological_group_populations'].append(deepcopy(plan['population'])); continue
            category = plan['category_id']; cat = plans[category]; metadata = docs[cat['metadata']]['value']
            observed = {g['group_id'] for g in groups.values() if g['category_id'] == category and any(
                relation['alignment_rows'] for index in g['metadata_row_indices']
                for relation in metadata_by_doc_row[(cat['metadata'], index)])}
            selected = []
            for row in metadata['rows']:
                col = cat['metadata_column_index_0based']
                if col < len(row['cells']):
                    raw = row['cells'][col]; gid = c.group_id(category, raw)
                    if (plan['include_metadata_only'] or gid in observed) and gid not in [g['group_id'] for g in selected]:
                        selected.append({'group_id': gid, 'raw_group_value': raw, 'evidence': deepcopy(plan['evidence'])})
            result['biological_group_populations'].append({'group_population_id': plan['group_population_id'], 'category_id': category,
                'groups': selected, 'completeness': metadata['completeness'], 'evidence': deepcopy(plan['evidence'])})
        native_maps = {m['category_id']: m for m in declarations['native_group_maps']}; r_evidence = {m['category_id']: m for m in declarations['r_columns']}
        for category in analysis['category_ids']:
            if not any(p['category_id'] == category for p in result['biological_group_populations']):
                need(category, 'biological_group_population_required')
            if category not in r_evidence:
                need(category, 'native_r_column_identity_required', 'native_r_columns')
            mapping = native_maps.get(category, {'entries': []})
            for source in r_evidence.get(category, {}).get('columns', []):
                mapped = [e for e in mapping['entries'] if e['native_group_ordinal'] == source['native_group_ordinal']]
                choices = set(e['group_id'] for e in mapped)
                if source['group_id'] is not None:
                    choices.add(source['group_id'])
                gid = next(iter(choices)) if len(choices) == 1 else None
                resolved = gid is not None and source['native_group_ordinal'] is not None
                result['native_group_columns'].append({'category_id': category, **deepcopy(source), 'group_id': gid,
                    'exported_heading_index_0based': None, 'exported_label_token': None, 'state': 'resolved' if resolved else 'unresolved',
                    'evidence': deepcopy(source['evidence']) + deepcopy(r_evidence[category]['evidence'])})
                if not resolved:
                    need(category, 'native_r_group_association_unresolved')
        explicit_exports = {(r['table_id'], r['heading_index_0based']): r for r in declarations['exported_group_joins']}
        for tid in analysis['chisq_table_ids']:
            document = docs[tid]['value']
            for index, token in enumerate(document['group_heading_tokens']):
                result['exported_groups'].append(deepcopy(explicit_exports.get((tid, index), {'category_id': document['category_id'],
                    'table_id': tid, 'heading_index_0based': index, 'raw_heading_token': token, 'group_id': None,
                    'r_column_index_0based': None, 'state': 'missing', 'evidence': []})))
        column_lookup = {(r['category_id'], r['r_column_index_0based']): r for r in result['native_group_columns']}
        for exported in result['exported_groups']:
            if exported['state'] in ('resolved', 'wrong_native_label'):
                column = column_lookup.get((exported['category_id'], exported['r_column_index_0based']))
                if column is None:
                    exported.update(state='missing', r_column_index_0based=None)
                elif column['state'] == 'unresolved' or column['group_id'] != exported['group_id']:
                    exported['state'] = 'conflicting'
        for column in result['native_group_columns']:
            linked = [e for e in result['exported_groups'] if e['category_id'] == column['category_id'] and e['r_column_index_0based'] == column['r_column_index_0based'] and e['state'] in ('resolved', 'wrong_native_label')]
            meanings = {(e['heading_index_0based'], e['raw_heading_token'], e['group_id']) for e in linked}
            if len(meanings) == 1:
                index, label, gid = meanings.pop()
                if gid == column['group_id']:
                    column['exported_heading_index_0based'] = index; column['exported_label_token'] = label
                    if label != groups[gid]['raw_group_value']:
                        column['state'] = 'wrong_native_label'
        for bio in result['biological_assignments']:
            category = bio['category_id']; gid = bio['group_id']; native = native_maps.get(category, {'entries': []})
            ordinals = {e['native_group_ordinal'] for e in native['entries'] if e['group_id'] == gid}
            ordinal = next(iter(ordinals)) if len(ordinals) == 1 else None
            mapped = [e for e in result['exported_groups'] if e['category_id'] == category and e['group_id'] == gid and e['state'] in ('resolved', 'wrong_native_label')]
            labels = {e['raw_heading_token'] for e in mapped}; label = next(iter(labels)) if len(labels) == 1 else None
            key = category, bio['alignment_id'], bio['row_index']; metadata_index = metadata_for_assignment.get(key)
            raw_group = groups[gid]['raw_group_value'] if gid is not None else None
            if metadata_index is not None:
                raw_group = c.native_row(docs[plans[category]['metadata']]['value'], metadata_index)['cells'][plans[category]['metadata_column_index_0based']]
            result['native_group_assignments'].append({'category_id': category, 'alignment_id': bio['alignment_id'], 'row_index': bio['row_index'],
                'member_key': deepcopy(bio['member_key']), 'metadata_row_index': metadata_index,
                'metadata_column_index': plans[category]['metadata_column_index_0based'] if metadata_index is not None else None,
                'raw_group_value': raw_group,
                'native_group_ordinal': ordinal, 'displayed_group_label': label,
                'state': ('resolved' if ordinal is not None else 'native_unlabeled') if bio['state'] == 'resolved' else bio['state'], 'evidence': deepcopy(bio['evidence'])})
        for category in result['categories']:
            cid = category['category_id']; category['group_ids'] = [g['group_id'] for g in groups.values() if g['category_id'] == cid]
            assignments = [a for a in result['biological_assignments'] if a['category_id'] == cid]
            completeness = 'complete' if analysis['alignment_id'] is not None and alignments[analysis['alignment_id']]['completeness'] == 'complete' and all(a['state'] == 'resolved' for a in assignments) else 'partial'
            for group in groups.values():
                if group['category_id'] == cid:
                    group['membership_completeness'] = completeness
        result['groups'] = list(groups.values())
        result['native_test_associations'] = _native_tests(analysis, docs, result['native_group_columns'], result['exported_groups'], r_evidence, declarations['native_test_joins'])
        for native in result['native_test_associations']:
            if native['state'] in ('resolved', 'wrong_native_label'):
                cols = [column_lookup.get((native['category_id'], i)) for i in native['r_columns_0based']]
                if any(col is None or col['state'] == 'unresolved' for col in cols):
                    native.update(state='conflicting', test_id=None)
                    if any(col is None for col in cols):
                        native['r_columns_0based'] = []
        for row in result['exported_groups'] + result['native_test_associations']:
            if row['state'] in ('missing', 'conflicting'):
                need(row['category_id'], 'native_output_group_identity_unresolved')
            elif row['state'] == 'wrong_native_label':
                result['diagnostics'].append(diagnostic(c.PREFIX + 'wrong_native_label', path='/exported_groups'))
        validated = c.validate_metacats_association_set(result, analysis=analysis, documents=documents, associations=associations)
        return {'status': 'partial' if result['requirements'] or result['diagnostics'] else 'ok', 'value': validated, 'diagnostics': deepcopy(result['diagnostics'])}
    except (ValueError, KeyError, TypeError, IndexError, UnicodeError) as exc:
        code = str(exc).removeprefix(c.PREFIX).removeprefix(common.PREFIX) if isinstance(exc, ValueError) else 'shape_invalid'
        if not re.fullmatch(r'[A-Za-z0-9_]+', code):
            code = 'declarations_invalid'
        return {'status': 'invalid', 'value': None, 'diagnostics': [diagnostic(c.PREFIX + code, severity='error')]}


__all__ = ['extract_metacats_associations']
