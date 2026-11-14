"""Validate a supplied pairwise reference against the original submitted FASTA.

All operands are already retained and authenticated by the execution host.
This module validates their scientific associations only. It has no storage,
network, execution or score-calculation effects.
"""
from __future__ import annotations

import hashlib
import json
import re

from .blast_search import PROGRAM_UNITS


class _Unavailable(ValueError):
    def __init__(self, code, path):
        self.code, self.path = code, path


def _need(condition, code, path):
    if not condition:
        raise _Unavailable(code, path)


def _same(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def _tokens(pointer):
    _need(type(pointer) is str and (pointer == '' or pointer.startswith('/'))
          and re.search(r'~(?![01])', pointer) is None,
          'homology_subject_source_pointer_invalid', '/subject_binding')
    return [] if pointer == '' else [part.replace('~1', '/').replace('~0', '~') for part in pointer[1:].split('/')]


def _read(source_ref, pointer, values, *, content=None):
    """Resolve only an exact source and an explicitly supplied ancestor value."""
    target = _tokens(pointer)
    found, identities = [], []
    for row in values:
        evidence = row['evidence']
        if evidence['content']['source_ref'] != source_ref:
            continue
        identities.append(evidence['content'])
        if content is not None and not _same(content, evidence['content']):
            raise _Unavailable('homology_subject_source_content_conflict', pointer)
        base = _tokens(evidence['pointer'])
        if target[:len(base)] != base:
            continue
        value = row['value']
        for token in target[len(base):]:
            if type(value) is dict and token in value:
                value = value[token]
            elif (type(value) is list and re.fullmatch(r'0|[1-9][0-9]*', token)
                  and int(token) < len(value)):
                value = value[int(token)]
            else:
                break
        else:
            found.append(value)
    _need(found, 'homology_subject_source_value_unavailable', pointer)
    _need(all(_same(identities[0], row) for row in identities)
          and all(_same(found[0], row) for row in found),
          'homology_subject_source_value_conflict', pointer)
    return found[0]


def _read_evidence(evidence, values):
    _need(type(evidence) is dict and set(evidence) == {'content', 'pointer'},
          'homology_subject_member_evidence_required', '/subject_binding')
    return _read(evidence['content']['source_ref'], evidence['pointer'], values, content=evidence['content'])


def _single_fasta(text, molecule):
    _need(type(text) is str and bool(text), 'homology_subject_reference_bytes_required', '/input_bindings')
    records, identifier, pieces = [], None, []
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith('>'):
            if identifier is not None:
                records.append((identifier, ''.join(pieces)))
            fields = line[1:].split()
            _need(fields, 'homology_subject_fasta_invalid', '/input_bindings')
            identifier, pieces = fields[0], []
        else:
            _need(identifier is not None, 'homology_subject_fasta_invalid', '/input_bindings')
            # Line wrapping/whitespace is FASTA syntax. No gap removal, case
            # conversion, sequence substitution or biological normalization.
            sequence = ''.join(line.split())
            alphabet = r'[A-Za-z*]+' if molecule == 'aa' else r'[ACGTURYSWKMBDHVNacgturyswkmbdhvn]+'
            _need(re.fullmatch(alphabet, sequence) is not None,
                  'homology_subject_fasta_normalization_unproved', '/input_bindings')
            pieces.append(sequence)
    if identifier is not None:
        records.append((identifier, ''.join(pieces)))
    _need(len(records) == 1, 'homology_subject_database_not_single_sequence', '/input_bindings')
    _need(bool(records[0][1]), 'homology_subject_fasta_invalid', '/input_bindings')
    return records[0]


def _reference_input(bundle, subject, values):
    parameters = bundle['original_task']['submitted_parameters']
    source = parameters.get('db_source')
    _need(source in {'fasta_data', 'fasta_file'}, 'homology_subject_database_selection_unproved', '/original_task/submitted_parameters')
    pointer = '/db_' + source
    operand = parameters.get(pointer[1:])
    candidates = [row for row in bundle['input_bindings'] if row['parameter_pointer'] == pointer]
    _need(len(candidates) == 1, 'homology_subject_reference_input_unavailable', '/input_bindings')
    original = candidates[0]
    _need(len(original['members']) == 1, 'homology_subject_database_not_single_sequence', '/input_bindings')
    member = original['members'][0]
    _need(member['member_id'] == subject['member_ref'], 'homology_subject_member_conflict', '/subject_binding/member_ref')
    input_source = original['content'] or (member['evidence'] or {}).get('content')
    _need(input_source is not None and subject['source_ref'] == input_source['source_ref'],
          'homology_subject_source_conflict', '/subject_binding/source_ref')
    if source == 'fasta_data':
        _need(original['kind'] in {'inline_parameter', 'supplied_link'}
              and _same(original['inline_value'], operand),
              'homology_subject_submitted_operand_conflict', pointer)
        text = operand
        if original['link_evidence'] is not None:
            _need(_same(_read_evidence(original['link_evidence'], values), text),
                  'homology_subject_submitted_operand_conflict', pointer)
    else:
        _need(original['kind'] == 'retained_bytes' and original['content'] is not None,
              'homology_subject_reference_bytes_required', pointer)
        _need(original['workspace_path'] == operand, 'homology_subject_submitted_operand_conflict', pointer)
        candidates = [row['value'] for row in values if type(row['value']) is dict
                      and set(row['value']) == {'content', 'text'}
                      and _same(row['value']['content'], original['content'])]
        _need(candidates, 'homology_subject_reference_bytes_required', pointer)
        _need(all(_same(candidates[0], row) for row in candidates),
              'homology_subject_source_value_conflict', pointer)
        text = candidates[0]['text']
        _need(type(text) is str, 'homology_subject_reference_bytes_required', pointer)
        raw = text.encode('utf-8')
        _need(hashlib.sha256(raw).hexdigest() == original['content']['sha256']
              and len(raw) == original['content']['byte_count'],
              'homology_subject_reference_bytes_conflict', pointer)
    return original, member, text


def _validate(bundle, subject, database, values, queries):
    path = '/subject_binding'
    fields = {'source_ref', 'member_ref', 'subject_ref', 'sequence_sha256', 'length', 'molecule',
              'database_membership', 'native_hit_links'}
    _need(type(subject) is dict and set(subject) == fields,
          'homology_subject_binding_required', path)
    _need(all(type(subject[key]) is str and subject[key] for key in ('source_ref', 'member_ref', 'subject_ref'))
          and type(subject['length']) is int and subject['length'] > 0
          and type(subject['sequence_sha256']) is str and re.fullmatch(r'[a-f0-9]{64}', subject['sequence_sha256']) is not None
          and subject['molecule'] in {'aa', 'nt'}, 'homology_subject_binding_invalid', path)
    original, member, text = _reference_input(bundle, subject, values)
    identifier, sequence = _single_fasta(text, subject['molecule'])
    actual = {'length': len(sequence), 'sequence_sha256': hashlib.sha256(sequence.encode('ascii')).hexdigest(),
              'molecule': {'protein': 'aa', 'dna': 'nt', 'rna': 'nt'}.get(member['molecule'])}
    _need(actual['molecule'] is not None and all(_same(subject[key], value) for key, value in actual.items())
          and all(_same(member[key], actual[key]) for key in ('length', 'sequence_sha256')),
          'homology_subject_sequence_identity_conflict', path)
    program = bundle['original_task']['submitted_parameters'].get('blast_program')
    _need(program in PROGRAM_UNITS and PROGRAM_UNITS[program][1] == subject['molecule'],
          'homology_subject_program_molecule_conflict', path + '/molecule')
    membership = subject['database_membership']
    _need(type(membership) is dict and set(membership) == {'source_ref', 'pointer', 'member_count'}
          and type(membership['member_count']) is int and membership['member_count'] == 1,
          'homology_subject_membership_invalid', path + '/database_membership')
    members = _read(membership['source_ref'], membership['pointer'], values)
    _need(type(members) is list and len(members) == 1 and type(members[0]) is dict,
          'homology_subject_database_not_single_sequence', path + '/database_membership')
    row = _read_evidence(member['evidence'], values)
    _need(type(row) is dict and _same(row, members[0]),
          'homology_subject_membership_member_conflict', path + '/database_membership')
    expected = {'member_id': member['member_id'], 'length': len(sequence), 'sequence_sha256': actual['sequence_sha256'],
                'molecule': member['molecule'], 'sequence': sequence, 'supplied_id': identifier}
    _need(all(key in row and _same(row[key], value) for key, value in expected.items()),
          'homology_subject_membership_sequence_conflict', path + '/database_membership')
    _need(subject['subject_ref'] == member['member_id'] or row.get('subject_ref') == subject['subject_ref'],
          'homology_subject_entity_link_unproved', path + '/subject_ref')
    parameters = bundle['original_task']['submitted_parameters']
    _need(_same(database.get('requested_selection'), {key: value for key, value in parameters.items() if key.startswith('db_')}),
          'homology_subject_database_selection_conflict', '/database_binding/requested_selection')
    inventory_ref = database.get('input_or_database_sequence_inventory_ref')
    _need(inventory_ref is None or inventory_ref == membership['source_ref'],
          'homology_subject_database_inventory_conflict', '/database_binding/input_or_database_sequence_inventory_ref')
    inventory = database.get('actual_database_members')
    if inventory is not None:
        _need(type(inventory) is list and len(inventory) == 1 and type(inventory[0]) is dict
              and inventory[0].get('identifier') == member['member_id'],
              'homology_subject_database_inventory_conflict', '/database_binding/actual_database_members')
        item = inventory[0]
        _need(all(key not in item or _same(item[key], value)
                  for key, value in {**actual, 'sequence': sequence, 'supplied_id': identifier}.items()),
              'homology_subject_database_inventory_conflict', '/database_binding/actual_database_members')
        if 'source_ref' in item or 'pointer' in item:
            _need('source_ref' in item and 'pointer' in item and _same(_read(item['source_ref'], item['pointer'], values), row),
                  'homology_subject_database_inventory_conflict', '/database_binding/actual_database_members')
    _need(type(queries) is list and len(queries) == 1 and queries[0].get('normalized_result') is not None,
          'homology_pairwise_native_query_unavailable', '/queries')
    query = queries[0]
    normalized = query['normalized_result']
    _need(normalized['search']['program'] == program, 'homology_subject_native_program_conflict', '/queries/0')
    hits = normalized['hits']
    _need(len(hits) <= 1, 'homology_subject_native_population_conflict', '/queries/0/hits')
    links = subject['native_hit_links']
    _need(type(links) is list, 'homology_subject_native_link_invalid', path + '/native_hit_links')
    mappings = row.get('native_hits', [])
    _need(type(mappings) is list, 'homology_subject_native_mapping_invalid', path + '/database_membership')
    if 'native_hit' in row:
        mappings = [*mappings, row['native_hit']]
    for mapping in mappings:
        _need(type(mapping) is dict and set(mapping) in (
                  {'report_index', 'hit_index', 'description_index', 'id'},
                  {'report_index', 'hit_index', 'description_index', 'id', 'length'})
              and all(type(mapping[key]) is int and mapping[key] >= 0 for key in ('report_index', 'hit_index', 'description_index'))
              and mapping['report_index'] == query['report_index']
              and type(mapping['id']) is str and bool(mapping['id'])
              and ('length' not in mapping or _same(mapping['length'], subject['length'])),
              'homology_subject_native_mapping_invalid', path + '/database_membership')
        matches = [description for hit in hits if hit['hit_index'] == mapping['hit_index']
                   for description in hit['descriptions']
                   if description['source_locator']['description_index'] == mapping['description_index']]
        _need(len(matches) == 1 and matches[0].get('id') == mapping['id'],
              'homology_subject_native_identity_conflict', path + '/database_membership')
    if not hits:
        _need(not links, 'homology_subject_native_link_invalid', path + '/native_hit_links')
        return
    _need(bool(links), 'homology_subject_native_link_required', path + '/native_hit_links')
    for link in links:
        _need(type(link) is dict and set(link) == {'report_index', 'hit_index', 'description_index'}
              and all(type(value) is int and value >= 0 for value in link.values())
              and link['report_index'] == query['report_index'],
              'homology_subject_native_link_invalid', path + '/native_hit_links')
        selected_hits = [hit for hit in hits if hit['hit_index'] == link['hit_index']]
        _need(len(selected_hits) == 1, 'homology_subject_native_link_invalid', path + '/native_hit_links')
        hit = selected_hits[0]
        _need(hit['length'] is None or _same(hit['length'], subject['length']),
              'homology_subject_native_length_conflict', path + '/length')
        descriptions = [description for description in hit['descriptions']
                        if description['source_locator']['description_index'] == link['description_index']]
        _need(len(descriptions) == 1, 'homology_subject_native_link_invalid', path + '/native_hit_links')
        native_id = descriptions[0].get('id')
        matches = [mapping for mapping in mappings if type(mapping) is dict
                   and all(_same(mapping.get(key), value) for key, value in link.items())]
        if matches:
            _need(len(matches) == 1 and matches[0].get('id') == native_id
                  and ('length' not in matches[0] or _same(matches[0]['length'], subject['length'])),
                  'homology_subject_native_identity_conflict', path + '/native_hit_links')
        else:
            _need(native_id == identifier, 'homology_subject_native_identity_conflict', path + '/native_hit_links')


def validate_pairwise_subject(bundle, *, subject, database, supplied_values, queries):
    """Return specific unavailable associations; never invent a subject proof."""
    try:
        _validate(bundle, subject, database, supplied_values, queries)
    except _Unavailable as error:
        return [{'code': error.code, 'path': error.path}]
    except (KeyError, TypeError, ValueError, AttributeError, IndexError, OverflowError, RecursionError):
        return [{'code': 'homology_subject_binding_input_invalid', 'path': '/subject_binding'}]
    return []


__all__ = ['validate_pairwise_subject']
