"""Pure extraction of original occurrences and selected alignment joins.

Supplied original strings stay in InputBinding. No artifact is invented for an
inline input, and no resource, job, acquisition or statistical score is chosen.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import re

from . import bvbrc_alignment_provider_contracts as c
from .bvbrc_alignment_values import diagnostic, requirement


def _diag(code, path='', *, error=False):
    return diagnostic(c.PREFIX + code, path=path, severity='error' if error else 'qualification')


def _need(scope, reason, *, role='original_member_association', kind='scientific_metadata'):
    return requirement(scope + '/' + reason, kind=kind, role=role, reason_code=reason)


def _result(value, diagnostics):
    return {'status': 'invalid' if value is None else ('partial' if diagnostics or value.get('requirements') else 'ok'),
        'value': value, 'diagnostics': deepcopy(diagnostics)}


@c.closed
def input_member_occurrence_subject_id(input_binding_id: str, member_id: str, occurrence_index: int) -> str:
    """Canonical semantic identity; the three separately encoded parts survive."""
    return c.occurrence_id(input_binding_id, member_id, occurrence_index)


def _member(binding, label, occurrence, molecule, *, source=None, document=None, encoding='utf-8', host=None, supplied_evidence=()):
    seq = source['sequence'] if source is not None else None
    try:
        digest = hashlib.sha256(seq.encode(encoding)).hexdigest() if seq is not None else host['sequence_sha256']
    except UnicodeError:
        digest = None
    evidence = deepcopy(list(supplied_evidence))
    if host is not None and host['evidence'] is not None and host['evidence'] not in evidence:
        evidence.append(deepcopy(host['evidence']))
    return {'key': {'input_binding_id': binding['binding_id'], 'member_id': label, 'occurrence_index': occurrence},
        'host_member_id': host['member_id'] if host is not None else None,
        'original_input_pointer': host['member_pointer'] if host is not None else binding['parameter_pointer'],
        'source_document_id': document, 'source_row_index': source['row_index'] if source is not None else None,
        'raw_header': source['raw_header'] if source is not None else None,
        'member_label': source['member_label'] if source is not None else None,
        'sequence_sha256': digest, 'original_length': len(seq) if seq is not None else host['length'],
        'molecule': molecule, 'feature_ids': [], 'genome_ids': [], 'source_record_ids': [], 'evidence': evidence}


def extract_inline_fasta_members(binding: dict, *, id_rule: str, encoding: str, molecule: str) -> dict:
    """Parse actual supplied FASTA with Unicode character and physical-line ranges."""
    try:
        c.input_map((binding,))
        c.require(binding['kind'] == 'inline_parameter' and type(binding['inline_value']) is str, 'inline_input_invalid')
        c.require(id_rule == 'first_whitespace_token' and encoding in ('ascii', 'utf-8') and molecule in c.MOLECULES, 'inline_parameters_invalid')
    except ValueError as exc:
        return _result(None, [_diag(str(exc).removeprefix(c.PREFIX), error=True)])
    value = {'input_binding_id': binding['binding_id'], 'parameter_pointer': binding['parameter_pointer'],
        'id_rule': id_rule, 'encoding': encoding, 'completeness': 'complete', 'rows': [], 'members': [], 'requirements': [], 'diagnostics': []}
    rows, diagnostics, current = value['rows'], value['diagnostics'], None
    original = binding['inline_value']
    try:
        original.encode(encoding)
    except UnicodeError:
        diagnostics.append(_diag('inline_encoding_invalid', '/encoding', error=True))
    for line_index, match in enumerate(re.finditer(r'[^\r\n]*(?:\r\n|\r|\n|$)', original), 1):
        if match.start() == len(original):
            break
        line = match.group().rstrip('\r\n')
        if line.startswith('>'):
            label = line[1:].split()
            current = {'row_index': len(rows), 'raw_header': line[1:], 'member_label': label[0] if label else '', 'sequence': '',
                'character_start_0based': match.start(), 'character_end_0based_exclusive': match.end(),
                'line_start_1based': line_index, 'line_end_1based_inclusive': line_index}
            rows.append(current)
            if not label:
                diagnostics.append(_diag('inline_header_empty', f'/rows/{current["row_index"]}', error=True))
        elif current is not None:
            current['character_end_0based_exclusive'] = match.end(); current['line_end_1based_inclusive'] = line_index
            if line.strip():
                if ' ' in line or '\t' in line:
                    diagnostics.append(_diag('inline_sequence_layout_whitespace_removed', f'/rows/{current["row_index"]}/sequence'))
                seq = line.replace(' ', '').replace('\t', '')
                if re.fullmatch(r'[A-Za-z*.?\-#]*', seq) is None:
                    diagnostics.append(_diag('inline_sequence_symbol_invalid', f'/rows/{current["row_index"]}/sequence', error=True))
                current['sequence'] += seq
        elif line.strip():
            diagnostics.append(_diag('inline_header_missing', '/rows', error=True))
    counts = Counter(r['member_label'] for r in rows); seen = Counter()
    host = {m['member_id']: m for m in binding['members']}
    for row in rows:
        label = row['member_label']
        if not label:
            continue
        member = _member(binding, label, seen[label], molecule, source=row, encoding=encoding,
            host=host.get(label) if counts[label] == 1 else None)
        value['members'].append(member); seen[label] += 1
        if not row['sequence']:
            diagnostics.append(_diag('inline_sequence_empty', f'/rows/{row["row_index"]}/sequence', error=True))
    if not rows:
        diagnostics.append(_diag('inline_no_rows', '/rows', error=True))
    if any(d['severity'] == 'error' for d in diagnostics):
        value['completeness'] = 'partial'
    return _result(value, diagnostics)


def _input_records(bindings, docs, common):
    originals, inline, requirements, diagnostics = [], [], [], []
    selected = {row['input_binding_id']: row for row in common['input_sequences']}
    for bid, binding in bindings.items():
        selection = selected.get(bid); bound, represented = set(), set()
        if selection is not None and selection['kind'] == 'inline_fasta':
            result = extract_inline_fasta_members(binding, **{k: selection[k] for k in ('id_rule', 'encoding', 'molecule')})
            c.require(result['value'] is not None, 'inline_parameters_invalid')
            record = result['value']
            for member in record['members']:
                for fact in selection['evidence']:
                    if fact not in member['evidence']:
                        member['evidence'].append(deepcopy(fact))
            originals.extend(record['members']); inline.append(record)
            requirements.extend(record['requirements']); diagnostics.extend(record['diagnostics'])
            represented.update(m['key']['member_id'] for m in record['members'])
            bound.update(m['host_member_id'] for m in record['members'] if m['host_member_id'] is not None)
        elif selection is not None:
            document = docs[selection['document']]['value']; seen = Counter()
            if document['completeness'] != 'complete':
                diagnostics.append(_diag('original_document_incomplete', '/original_members'))
            host = {m['member_id']: m for m in binding['members']}
            joins = {j['source_row_index']: j['host_member_id'] for j in selection['host_member_joins']}
            for row in document['rows']:
                label = row['member_label']
                if not label:
                    diagnostics.append(_diag('original_member_label_missing', '/original_members')); continue
                h = host[joins[row['row_index']]] if row['row_index'] in joins else None
                originals.append(_member(binding, label, seen[label], selection['molecule'], source=row,
                    document=document['alignment_id'], encoding=document['encoding'], host=h, supplied_evidence=selection['evidence']))
                represented.add(label); seen[label] += 1
                if h is not None:
                    bound.add(h['member_id'])
        for host in binding['members']:
            if host['member_id'] not in bound and host['member_id'] not in represented:
                originals.append(_member(binding, host['member_id'], 0, host['molecule'] or 'unknown', host=host))
        if selection is None and binding['members']:
            requirements.append(_need(bid, 'original_sequence_content_unavailable', role='original_sequence', kind='input_bytes'))
    for member in originals:
        member['source_record_ids'] = [r['source_record_id'] for r in common['source_records'] if r['evidence'] in member['evidence']]
        derived = c.entity_arrays(c.member_key(member['key']), common['member_entities'], common['feature_genomes'])
        for field in ('feature_ids', 'genome_ids', 'source_record_ids'):
            for identity in derived[field]:
                if identity not in member[field]:
                    member[field].append(identity)
    return originals, inline, requirements, diagnostics


def _source_sequence(member, docs, inline):
    if member['source_document_id'] is not None:
        return docs[member['source_document_id']]['value']['rows'][member['source_row_index']]['sequence']
    if member['source_row_index'] is not None:
        return inline[member['key']['input_binding_id']]['rows'][member['source_row_index']]['sequence']
    return None


def _automatic_joins(plan, members, docs, inline, transforms):
    alignment = docs[plan['alignment']]['value']
    eligible = [m for m in members if m['key']['input_binding_id'] in plan['input_binding_ids']]
    by_value, output_values = defaultdict(list), []
    def normalize(value, output=False):
        if value is None:
            return None
        if plan['method'] == 'exact_unique_sequence' and output and plan['gap_policy'] == 'remove_alignment_dash':
            value = value.replace('-', '')
        return value.upper() if plan['case_policy'] == 'uppercase' else value
    for member in eligible:
        operand = member['raw_header'] if plan['method'] == 'exact_unique_header' else _source_sequence(member, docs, inline)
        if plan['method'] == 'exact_unique_sequence' and operand is not None:
            for tid in plan['transformation_ids']:
                tr = transforms[tid]
                if member['key'] in tr['input_members']:
                    if tr['kind'] == 'uppercase':
                        operand = operand.upper()
                    elif tr['kind'] == 'remove_symbols':
                        operand = ''.join(s for s in operand if s not in tr['symbols'])
        key = normalize(operand)
        if key is not None:
            by_value[key].append(member)
    for row in alignment['rows']:
        output_values.append(normalize(row['raw_header'] if plan['method'] == 'exact_unique_header' else row['sequence'], True))
    counts = Counter(output_values); results = []
    for row, token in zip(alignment['rows'], output_values):
        candidates = by_value.get(token, []); resolved = len(candidates) == 1 and counts[token] == 1
        refs = {'alignment_id': alignment['alignment_id'], 'row_index': row['row_index']}
        tids = [tid for tid in plan['transformation_ids'] if refs in transforms[tid]['output_rows'] and all(m in [x['key'] for x in candidates] for m in transforms[tid]['input_members'])]
        results.append({'association_id': alignment['alignment_id'] + '/rows/' + str(row['row_index']) + '/original', **refs,
            'member_keys': [deepcopy(m['key']) for m in candidates], 'transformation_ids': tids,
            'state': 'resolved' if resolved else ('conflicting' if candidates else 'missing'),
            'basis': plan['method'], 'evidence': deepcopy(plan['evidence'])})
    return results


def extract_alignment_associations(*, inputs: tuple[dict, ...], documents: tuple[dict, ...], declarations: dict) -> dict:
    try:
        declarations = c.validate_alignment_association_declarations(declarations, inputs=inputs, documents=documents)
        common = declarations['common']; bindings = c.input_map(inputs); docs, _, _ = c.document_maps(documents)
        members, inline, requirements, diagnostics = _input_records(bindings, docs, common)
        value = {key: [] for key in c.ASSOCIATION_KEYS}
        value.update(original_members=members, inline_inputs=inline, requirements=requirements, diagnostics=diagnostics,
            transformations=deepcopy(common['transformations']), correspondences=deepcopy(common['correspondences']),
            feature_genomes=deepcopy(common['feature_genomes']), source_records=deepcopy(common['source_records']), member_entities=deepcopy(common['member_entities']),
            functions=deepcopy(declarations['functions']['assignments']) if declarations['functions'] else [],
            function_equivalences=deepcopy(declarations['functions']['equivalences']) if declarations['functions'] else [],
            taxonomy=deepcopy(declarations['taxonomy']['assignments']) if declarations['taxonomy'] else [])
        rows = deepcopy(common['row_joins']); explicit = {(r['alignment_id'], r['row_index']) for r in rows}
        transforms = {t['transformation_id']: t for t in value['transformations']}
        for plan in common['automatic_row_joins']:
            rows.extend(r for r in _automatic_joins(plan, members, docs, {x['input_binding_id']: x for x in inline}, transforms)
                if (r['alignment_id'], r['row_index']) not in explicit)
        value['row_members'] = rows
        for row in rows:
            if row['state'] != 'resolved':
                reason = 'original_member_ambiguous' if row['state'] in ('conflicting', 'native_duplicate_merge') else 'original_member_missing'
                requirements.append(_need(row['association_id'], reason)); diagnostics.append(_diag(reason, '/row_members'))
        def dependence(kind, operand_members=(), alignment_rows=(), document_ids=(), source_record_ids=()):
            value['dependence_groups'].append({'group_id': common['analysis_id'] + '/dependence/' + str(len(value['dependence_groups'])),
                'kind': kind, 'member_keys': [deepcopy(m['key']) for m in operand_members], 'alignment_rows': list(alignment_rows),
                'document_ids': list(document_ids), 'source_record_ids': list(source_record_ids), 'evidence': []})
        for kind, getter in (('duplicate_original_label', lambda m: (m['key']['input_binding_id'], m['key']['member_id'])),
                             ('identical_sequence', lambda m: m['sequence_sha256'])):
            buckets = defaultdict(list)
            for m in members:
                if getter(m) is not None:
                    buckets[getter(m)].append(m)
            for group in buckets.values():
                if len(group) > 1:
                    dependence(kind, group)
        for member in members:
            related = [{'alignment_id': r['alignment_id'], 'row_index': r['row_index']} for r in rows if member['key'] in r['member_keys'] and r['state'] in ('resolved', 'native_duplicate_merge')]
            if len(related) > 1:
                dependence('same_original_member', [member], related)
        host_groups = defaultdict(list)
        for member in members:
            if member['host_member_id'] is not None:
                host_groups[(member['key']['input_binding_id'], member['host_member_id'])].append(member)
        for related in host_groups.values():
            if len(related) > 1:
                dependence('same_original_member', related)
        for record in common['source_records']:
            related = [m for m in members if record['source_record_id'] in m['source_record_ids']]
            if len(related) > 1:
                dependence('same_source_record', related, source_record_ids=[record['source_record_id']])
        artifacts = defaultdict(list)
        for identity, document in docs.items():
            a = document['value']['artifact']; artifacts[(a['source_ref'], a['raw_artifact_ref'], a['sha256'])].append(identity)
        for ids in artifacts.values():
            if len(ids) > 1:
                dependence('repeated_artifact', document_ids=ids)
        return _result(c.validate_association_set(value, inputs=inputs, documents=documents), diagnostics)
    except (ValueError, KeyError, TypeError, IndexError, UnicodeError) as exc:
        code = str(exc).removeprefix(c.PREFIX) if isinstance(exc, ValueError) else 'shape_invalid'
        return _result(None, [_diag(code if code and re.fullmatch(r'[A-Za-z0-9_]+', code) else 'declarations_invalid', error=True)])


__all__ = ['input_member_occurrence_subject_id', 'extract_inline_fasta_members', 'extract_alignment_associations']
