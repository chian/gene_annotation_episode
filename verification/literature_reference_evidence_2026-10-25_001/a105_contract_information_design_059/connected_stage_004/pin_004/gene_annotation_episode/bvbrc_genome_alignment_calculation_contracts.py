"""Closed GenomeAlignment plans and structural checks for saved components.

Native structure validators inspect saved types, states and associations. This
module binds those values to the exact saved request, document and C witnesses;
full numerical validation remains on the producer path. Saved checks do not
authenticate arbitrary caller-authored science or rederive its quantities.
"""
from copy import deepcopy
import hashlib
import json
import math

from .bvbrc_alignment_values import diagnostic, requirement
from .bvbrc_appservice_contracts import validate_contract
from . import mauve_v4_calculation_contracts as v4c
from . import mauve_v4_format_contracts as v4f
from . import mauve_backbone_contracts as bc
from . import xmfa_calculation_contracts as xc
from .xmfa_source_contracts import validate_xmfa_source_bindings
from .xmfa_format_contracts import _artifact

PREFIX = 'bvbrc_genome_alignment_provider_'
DIAGNOSTIC_CODES = frozenset(PREFIX + s for s in (
    'document_missing document_ambiguous document_incompatible selection_target_missing '
    'selection_target_incompatible source_inputs_missing secondary_document_missing').split())
TARGET_ERRORS = {
    'mauve_v4_segments': frozenset('mauve_v4_' + s for s in (
        'selection_member_unknown selection_record_unknown selection_column_outside_record '
        'selection_population_incomplete').split()),
    'mauve_backbone': frozenset('mauve_backbone_' + s for s in (
        'selection_member_unknown selection_record_unknown selection_population_incomplete').split()),
    'mauve_bbcols': frozenset('mauve_bbcols_' + s for s in (
        'selection_record_unknown selection_population_incomplete').split()),
    'xmfa_alignment': frozenset(('xmfa_selection_member_unknown',
        'xmfa_selection_block_outside_document', 'xmfa_selection_column_outside_block')),
    'xmfa_coverage': frozenset(('xmfa_selection_member_unknown',
        'xmfa_selection_block_outside_document', 'xmfa_selection_column_outside_block')),
    'xmfa_coordinates': frozenset(('xmfa_cell_block_outside_document',
        'xmfa_cell_record_outside_block', 'xmfa_cell_column_outside_record')),
    'xmfa_inverse_coordinates': frozenset(('xmfa_query_member_unknown', 'xmfa_query_outside_source')),
}
MISSING_TARGET_ERRORS = frozenset((
    'mauve_v4_selection_member_unknown', 'mauve_v4_selection_record_unknown',
    'mauve_backbone_selection_member_unknown', 'mauve_backbone_selection_record_unknown',
    'mauve_bbcols_selection_record_unknown', 'xmfa_selection_member_unknown',
    'xmfa_selection_block_outside_document', 'xmfa_cell_block_outside_document',
    'xmfa_cell_record_outside_block', 'xmfa_query_member_unknown'))
KIND_FORMAT = {k: ('mauve1_xmfa' if k.startswith('xmfa_') else
    'mauve_v4' if k == 'mauve_v4_segments' else k) for k in TARGET_ERRORS}
ROLE_FORMATS = {'genome_alignment_primary': ('mauve_v4', 'mauve1_xmfa'),
    'genome_alignment_backbone': ('mauve_backbone',),
    'genome_alignment_bbcols': ('mauve_bbcols',)}
SELECTION_VALIDATORS = {'mauve_v4_segments': v4c.validate_mauve_v4_selection,
    'mauve_backbone': bc.validate_mauve_backbone_selection,
    'mauve_bbcols': bc.validate_mauve_bbcols_selection,
    'xmfa_alignment': xc.validate_xmfa_selection, 'xmfa_coverage': xc.validate_xmfa_selection}
COMPONENT_VALIDATORS = {'mauve_v4_segments': v4c.validate_mauve_v4_component_structure,
    'mauve_backbone': bc.validate_mauve_backbone_component_structure,
    'mauve_bbcols': bc.validate_mauve_bbcols_component_structure,
    'xmfa_alignment': xc.validate_xmfa_alignment_component_structure,
    'xmfa_coverage': xc.validate_xmfa_coverage_component_structure,
    'xmfa_coordinates': xc.validate_xmfa_coordinates,
    'xmfa_inverse_coordinates': xc.validate_xmfa_inverse_coordinates}


def _require(condition, code='schema_invalid'):
    if not condition:
        raise ValueError(PREFIX + code)


def _shape(value, keys):
    _require(type(value) is dict and set(value) == set(keys))


def _array(value):
    _require(type(value) is list)


def _text(value, *, nullable=False):
    _require(nullable and value is None or type(value) is str and bool(value))


def _uint(value, *, minimum=0):
    _require(type(value) is int and value >= minimum)


def _enum(value, choices):
    _require(type(value) is str and value in choices)


def _finite(value, ancestors=None):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        _require(math.isfinite(value), 'nonfinite_value')
        return
    _require(type(value) in (list, dict))
    ancestors = set() if ancestors is None else ancestors
    _require(id(value) not in ancestors)
    ancestors.add(id(value))
    if type(value) is dict:
        _require(all(type(k) is str for k in value))
        items = value.values()
    else:
        items = value
    for item in items:
        _finite(item, ancestors)
    ancestors.remove(id(value))


def _same(a, b):
    """JSON equality that does not confuse Boolean, integer and float fields."""
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if type(a) is list:
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return a == b


def _key(artifact):
    return tuple(artifact[k] for k in ('raw_artifact_ref', 'source_ref', 'sha256'))


def _reports(value):
    _require(type(value) is dict and 'requirements' in value and 'diagnostics' in value)
    for field, contract in (('requirements', 'AcquisitionRequirement'), ('diagnostics', 'Diagnostic')):
        _array(value[field])
        for row in value[field]:
            validate_contract(contract, row)
            code = row['reason_code' if field == 'requirements' else 'code']
            if code.startswith(PREFIX):
                _require(code in DIAGNOSTIC_CODES)
            elif code.startswith('mauve_v4_'):
                _require(code in v4c.CODES)
            elif code.startswith(('mauve_backbone_', 'mauve_bbcols_', 'bvbrc_genome_alignment_')) and not code.startswith('bvbrc_genome_alignment_bundle_'):
                _require(code in bc.ALLOWED_CODES)
            elif code.startswith('xmfa_'):
                _require(code[5:] in xc.DIAGNOSTIC_SUFFIXES)
    _require(len({r['requirement_id'] for r in value['requirements']}) == len(value['requirements']),
             'requirement_identity_conflict')


def _union(groups, field):
    result, by_id = [], {}
    for group in groups:
        for row in group[field]:
            if field == 'requirements':
                rid = row['requirement_id']
                _require(rid not in by_id or _same(by_id[rid], row), 'requirement_identity_conflict')
                if rid not in by_id:
                    result.append(deepcopy(row)); by_id[rid] = row
            elif row not in result:
                result.append(deepcopy(row))
    return result


def _links(value, ids):
    if type(value) is dict:
        if 'requirement_ids' in value:
            _array(value['requirement_ids'])
            _require(all(type(r) is str and r in ids for r in value['requirement_ids']),
                     'requirement_reference_unknown')
        for child in value.values():
            _links(child, ids)
    elif type(value) is list:
        for child in value:
            _links(child, ids)


def _slots(document_slots):
    _require(type(document_slots) is tuple, 'argument_invalid')
    result = {}
    for slot in document_slots:
        _finite(slot)
        _shape(slot, ('slot_id', 'role', 'source_ref', 'raw_artifact_ref', 'reader'))
        _text(slot['slot_id']); _text(slot['source_ref'], nullable=True)
        _text(slot['raw_artifact_ref'], nullable=True); _enum(slot['role'], ROLE_FORMATS)
        reader = slot['reader']
        _require(type(reader) is dict and type(reader.get('format')) is str)
        fmt = reader['format']
        _require(fmt in ROLE_FORMATS[slot['role']], 'slot_reader_conflict')
        fields = ('format', 'encoding') + (('dialect', 'alphabet') if fmt == 'mauve1_xmfa' else
            ('dialect',) if fmt in ('mauve_backbone', 'mauve_bbcols') else ())
        _shape(reader, fields); _enum(reader['encoding'], ('ascii', 'utf-8'))
        if fmt == 'mauve1_xmfa':
            _require(reader['dialect'] == 'mauve1' and reader['alphabet'] == 'dna', 'slot_reader_conflict')
        elif fmt in ('mauve_backbone', 'mauve_bbcols'):
            _require(reader['dialect'] == (bc.BACKBONE_DIALECT if fmt == 'mauve_backbone' else bc.BBCOLS_DIALECT),
                     'slot_reader_conflict')
        _require(slot['slot_id'] not in result, 'slot_id_duplicate')
        result[slot['slot_id']] = slot
    return result


def validate_genome_alignment_calculation_plan(value: dict, *, document_slots: tuple[dict, ...]) -> dict:
    slots = _slots(document_slots); _finite(value)
    _shape(value, ('schema_version', 'requests'))
    _require(value['schema_version'] == 'bvbrc_genome_alignment_calculation_plan_v1')
    _array(value['requests']); seen = set()
    tails = {'mauve_v4_segments': ('selection', 'use_inputs'),
        'mauve_backbone': ('selection', 'use_inputs'),
        'mauve_bbcols': ('selection', 'xmfa_document_slot_id'),
        'xmfa_alignment': ('selection', 'selected_pairs', 'case_policy'),
        'xmfa_coverage': ('selection', 'basis', 'use_source_bindings'),
        'xmfa_coordinates': ('cells', 'use_source_bindings'),
        'xmfa_inverse_coordinates': ('queries', 'use_source_bindings')}
    for request in value['requests']:
        _require(type(request) is dict and type(request.get('kind')) is str)
        kind = request['kind']; _require(kind in tails, 'request_kind_conflict')
        _shape(request, ('request_id', 'kind', 'document_slot_id', *tails[kind]))
        _text(request['request_id']); _text(request['document_slot_id'])
        _require(request['request_id'] not in seen, 'request_id_duplicate'); seen.add(request['request_id'])
        _require(request['document_slot_id'] in slots, 'slot_unknown')
        _require(slots[request['document_slot_id']]['reader']['format'] == KIND_FORMAT[kind], 'request_kind_conflict')
        if kind in SELECTION_VALIDATORS:
            selection = request['selection']
            _require(type(selection) is dict and 'document_id' not in selection, 'selection_invalid')
            SELECTION_VALIDATORS[kind](selection | {'document_id': 'prospective:document'})
        if 'use_inputs' in request:
            _require(type(request['use_inputs']) is bool)
            _require(request['use_inputs'] or selection['denominator'] != 'validated_staged_length', 'selection_invalid')
        if 'use_source_bindings' in request:
            _require(type(request['use_source_bindings']) is bool)
        if kind == 'mauve_bbcols':
            secondary = request['xmfa_document_slot_id']; _text(secondary, nullable=True)
            _require(not selection['calculate_bound_block_fraction'] or secondary is not None, 'selection_invalid')
            if secondary is not None:
                _require(secondary in slots, 'slot_unknown')
                _require(slots[secondary]['reader']['format'] == 'mauve1_xmfa', 'request_kind_conflict')
        elif kind == 'xmfa_alignment':
            _enum(request['case_policy'], ('preserve', 'uppercase'))
            xc._pairs(request['selected_pairs'], selection['member_numbers'])
        elif kind == 'xmfa_coverage':
            _enum(request['basis'], xc.BASES)
        elif kind == 'xmfa_coordinates':
            _array(request['cells']); refs = [xc.ref(cell, cell=True) for cell in request['cells']]
            _require(len(refs) == len(set(refs)), 'selection_invalid')
        elif kind == 'xmfa_inverse_coordinates':
            _array(request['queries']); refs = []
            for query in request['queries']:
                _shape(query, ('member_number', 'position_0based'))
                _uint(query['member_number'], minimum=1); _uint(query['position_0based'])
                refs.append((query['member_number'], query['position_0based']))
            _require(len(refs) == len(set(refs)), 'selection_invalid')
    return deepcopy(value)


def _indexes(data):
    return ({s['slot_id']: s for s in data['document_slots']},
        {r['slot_id']: r for r in data['slot_resolutions']},
        {p['document']['document_id']: p['document'] for p in data['parsed_artifacts'] if p['document'] is not None})


def _source_available(data, request):
    return (request.get('use_source_bindings', False) and data['inputs'] is not None
            and data['inputs']['xmfa_source_inputs'] is not None)


def _call(data, request, resolutions):
    resolution = resolutions[request['document_slot_id']]
    if resolution['state'] != 'resolved':
        return None
    kind = request['kind']; result = {'kind': kind}
    if 'selection' in request:
        result['selection'] = deepcopy(request['selection']) | {'document_id': resolution['document_id']}
    if kind in ('mauve_v4_segments', 'mauve_backbone'):
        result['inputs_used'] = request['use_inputs'] and data['inputs'] is not None
    elif kind == 'mauve_bbcols':
        secondary = resolutions.get(request['xmfa_document_slot_id'])
        result['xmfa_document_id'] = secondary['document_id'] if secondary and secondary['state'] == 'resolved' else None
        result['associations_used'] = data['associations'] is not None
    elif kind == 'xmfa_alignment':
        result.update(selected_pairs=deepcopy(request['selected_pairs']), case_policy=request['case_policy'])
    else:
        if kind == 'xmfa_coverage':
            result['basis'] = request['basis']
        else:
            field = 'cells' if kind == 'xmfa_coordinates' else 'queries'
            result[field] = deepcopy(request[field])
        result['source_binding_document_id'] = resolution['document_id'] if _source_available(data, request) else None
    return result


def _cause(data, request, index, reason, *, slot_id=None, affected=None):
    """A deterministic dependency record, with no numerical interpretation."""
    slots, resolutions, _ = _indexes(data)
    sid = slot_id if slot_id is not None else request['document_slot_id']
    slot, resolution = slots[sid], resolutions[sid]
    code = PREFIX + reason
    refs = [] if resolution['artifact'] is None else [resolution['artifact']['source_ref']]
    if not refs:
        refs = list(dict.fromkeys(a['source_ref'] for a in resolution['candidate_artifacts']))
    if not refs and slot['source_ref'] is not None:
        refs = [slot['source_ref']]
    payload = [data['analysis_id'], request['request_id'], sid, code, affected]
    rid = 'ga_req:' + hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'),
        ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    kind = ('output_bytes' if reason == 'document_missing' else 'input_bytes' if reason == 'source_inputs_missing'
            else 'scientific_metadata' if reason == 'secondary_document_missing' else 'parser_binding')
    return {'requirements': [requirement(rid, kind=kind, role=slot['role'], source_refs=refs, reason_code=code)],
        'diagnostics': [diagnostic(code, path='/calculation_plan/requests/' + str(index), evidence_refs=refs)]}


def _request_reports(data, request, index, call):
    _, resolutions, _ = _indexes(data)
    primary = resolutions[request['document_slot_id']]
    groups = [primary]
    if primary['state'] != 'resolved':
        reason = {'missing': 'document_missing', 'ambiguous': 'document_ambiguous', 'incompatible': 'document_incompatible'}[primary['state']]
        groups.append(_cause(data, request, index, reason))
    else:
        groups.extend({'requirements': [], 'diagnostics': p['diagnostics']} for p in data['parsed_artifacts']
                      if p['document'] is not None and p['document']['document_id'] == primary['document_id'])
        missing_inputs = (request.get('use_inputs', False) and data['inputs'] is None or
            request.get('use_source_bindings', False) and not _source_available(data, request))
        if missing_inputs:
            groups.append(_cause(data, request, index, 'source_inputs_missing'))
        if request['kind'] == 'mauve_bbcols' and request['xmfa_document_slot_id'] is not None:
            secondary = resolutions[request['xmfa_document_slot_id']]
            groups.append(secondary)
            if secondary['state'] != 'resolved':
                groups.append(_cause(data, request, index, 'secondary_document_missing',
                                     slot_id=request['xmfa_document_slot_id']))
    return {field: _union(groups, field) for field in ('requirements', 'diagnostics')}


def _positive(number):
    return number['value'] if number is not None and number['state'] == 'available' and type(number['value']) is int and number['value'] > 0 else None


def _native_members(document):
    result = []
    rows = list(document['metadata']) + [r for b in document['blocks'] for r in b['records']]
    for row in rows:
        number = _positive(row['member_number'])
        if number is not None and number not in result:
            result.append(number)
    return result


def _target_failure(document, call, binding):
    """Inspect target identity/bounds only; never recompute a measurement."""
    kind = call['kind']; sel = call.get('selection')
    if kind == 'mauve_v4_segments':
        count = v4f.scalar(document['metadata'], 'sequence_count')
        observed = {r['member_index_token']['value'] for r in document['metadata'] if v4f.available(r['member_index_token'])}
        records = {(i['interval_index'], s['segment_index']): s for i in document['intervals'] for s in i['segments']}
        observed.update(j for s in records.values() for j in range(len(s['native_starts'])))
        if any(not (m['index'] < count if count is not None else m['index'] in observed) for m in sel['members']):
            return 'mauve_v4_selection_member_unknown'
        for chosen in sel['segments']:
            key = chosen['interval_index'], chosen['segment_index']
            if key not in records:
                return 'mauve_v4_selection_record_unknown'
            native = records[key]; token = native['native_width' if native['kind'] == 'gapped_rows' else 'native_length']
            width = token['value'] if v4f.available(token) else None
            ranges = chosen['column_ranges_0based_half_open']
            if ranges and (width is None or any(b > width for a, b in ranges)):
                return 'mauve_v4_selection_column_outside_record'
        if sel['population_scope'] == 'all_observed_document_segments':
            if {(s['interval_index'], s['segment_index']) for s in sel['segments']} != set(records):
                return 'mauve_v4_selection_population_incomplete'
            for chosen in sel['segments']:
                native = records[chosen['interval_index'], chosen['segment_index']]
                token = native['native_width' if native['kind'] == 'gapped_rows' else 'native_length']
                width = token['value'] if v4f.available(token) else None
                ranges = chosen['column_ranges_0based_half_open']
                if (not ranges if width else bool(ranges)) or ranges and (
                    ranges[0][0] != 0 or ranges[-1][1] != width or any(a[1] != b[0] for a, b in zip(ranges, ranges[1:]))):
                    return 'mauve_v4_selection_population_incomplete'
    elif kind in ('mauve_backbone', 'mauve_bbcols'):
        if any(i >= len(document['rows']) for i in sel['row_indices']):
            return kind + '_selection_record_unknown'
        if sel['population_scope'] == 'all_observed_document_rows' and set(sel['row_indices']) != set(range(len(document['rows']))):
            return kind + '_selection_population_incomplete'
        if kind == 'mauve_backbone':
            known = {c['member_index_token']['value'] for c in document['columns'] if bc._available(c['member_index_token'], 0)}
            if any(m['index'] not in known for m in sel['members']):
                return 'mauve_backbone_selection_member_unknown'
    elif kind in ('xmfa_alignment', 'xmfa_coverage'):
        if not set(sel['member_numbers']) <= set(_native_members(document)):
            return 'xmfa_selection_member_unknown'
        for chosen in sel['block_columns']:
            if chosen['block_index'] >= len(document['blocks']):
                return 'xmfa_selection_block_outside_document'
            bound = max((len(r['sequence']) for r in document['blocks'][chosen['block_index']]['records']), default=0)
            if any(c >= bound for c in chosen['columns_0based']):
                return 'xmfa_selection_column_outside_block'
    elif kind == 'xmfa_coordinates':
        for cell in call['cells']:
            if cell['block_index'] >= len(document['blocks']):
                return 'xmfa_cell_block_outside_document'
            block = document['blocks'][cell['block_index']]
            if cell['record_index'] >= len(block['records']):
                return 'xmfa_cell_record_outside_block'
            if cell['column_0based'] >= len(block['records'][cell['record_index']]['sequence']):
                return 'xmfa_cell_column_outside_record'
    else:
        members = {} if binding is None else {m['member_number']: m for m in binding['members']}
        for query in call['queries']:
            if query['member_number'] not in _native_members(document):
                return 'xmfa_query_member_unknown'
            member = members.get(query['member_number'])
            if member is not None and member['source_length'] is not None and query['position_0based'] >= member['source_length']:
                return 'xmfa_query_outside_source'
    return None


def _snapshot(snapshot, data, documents):
    _shape(snapshot, ('document_id', 'source_comparison', 'bindings'))
    _require(snapshot['source_comparison'] == 'case_insensitive_iupac_exact', 'source_binding_conflict')
    did = snapshot['document_id']
    _require(type(did) is str and did in documents, 'source_binding_conflict')
    document = documents[did]
    _require(document['schema_version'] == 'mauve_xmfa_document_v1', 'source_binding_conflict')
    _require(data['inputs'] is not None and data['inputs']['xmfa_source_inputs'] is not None, 'source_binding_conflict')
    source = data['inputs']['xmfa_source_inputs']
    binding = validate_xmfa_source_bindings(snapshot['bindings'])
    _reports(binding)
    _require(binding['document_id'] == did and binding['invocation_mode'] == source['invocation']['mode']
             and _same(binding['original_maps'], source['original_maps']), 'source_binding_conflict')
    _require([m['member_number'] for m in binding['members']] == _native_members(document), 'source_binding_conflict')
    files = {f['file_id']: f for f in source['files']}
    members = {m['member_number']: m for m in binding['members']}
    for member in binding['members']:
        metadata = [m for m in document['metadata'] if _positive(m['member_number']) == member['member_number']]
        _require(member['metadata_indices'] == [m['metadata_index'] for m in metadata], 'source_binding_conflict')
        if member['file_id'] is not None:
            _require(member['file_id'] in files, 'source_binding_conflict')
        if member['state'] != 'resolved':
            continue
        file = files[member['file_id']]
        names = {m['value_token'] for m in metadata if m['kind'] == 'sequence_file'}
        formats = {m['value_token'] for m in metadata if m['kind'] == 'sequence_format'}
        entries = {_positive(m['integer_value']) for m in metadata if m['kind'] == 'sequence_entry'}
        _require(names == {member['native_file_token']} == {file['native_path_token']}
            and (not formats or formats == {file['format']})
            and file['record_completeness'] == 'complete', 'source_binding_conflict')
        order = source['invocation']['ordered_file_ids']
        if binding['invocation_mode'] == 'single_file_entries':
            _require(order == [file['file_id']] and entries == {member['entry_1based']}, 'source_binding_conflict')
            records = [r for r in file['records'] if r['entry_1based'] == member['entry_1based']]
        else:
            _require(member['member_number'] <= len(order) and order[member['member_number'] - 1] == file['file_id']
                and (not entries or entries == {member['member_number']}), 'source_binding_conflict')
            records = file['records']
        _require(len(records) == len(member['components']), 'source_binding_conflict')
        for component, record in zip(member['components'], records):
            a, b = component['member_interval_0based_half_open']
            _require(component['file_id'] == file['file_id'] and component['record_id'] == record['record_id']
                and component['entry_1based'] == record['entry_1based']
                and component['record_length'] == len(record['sequence'])
                and member['source_sequence'][a:b] == record['sequence'], 'source_binding_conflict')
    expected_refs = [(b['block_index'], r['record_index']) for b in document['blocks'] for r in b['records']]
    _require([(s['record']['block_index'], s['record']['record_index']) for s in binding['source_checks']] == expected_refs,
             'source_binding_conflict')
    for check in binding['source_checks']:
        ref = check['record']; row = document['blocks'][ref['block_index']]['records'][ref['record_index']]
        number = _positive(row['member_number'])
        _require(check['member_number'] == number, 'source_binding_conflict')
        _require(all(i < len(row['sequence']) and row['sequence'][i] != '-' for i in check['mismatch_columns_0based']),
                 'source_binding_conflict')
        member = members.get(number)
        comparable = (row['coordinate_state'] == 'present' and row['sequence_state'] == 'dna_iupac'
            and member is not None and member['state'] == 'resolved'
            and row['interval_0based_half_open'][1] <= member['source_length'])
        _require((check['state'] in ('match', 'mismatch')) == comparable, 'source_binding_conflict')
        if check['state'] in ('match', 'mismatch'):
            _require(row['coordinate_state'] == 'present' and member is not None and member['state'] == 'resolved'
                and row['interval_0based_half_open'][1] <= member['source_length']
                and check['compared_bases'] == row['nongap_character_count'], 'source_binding_conflict')
        _require((check['state'] == 'absent_zero') == (row['coordinate_state'] == 'absent_zero'), 'source_binding_conflict')
    return binding


def _bound_input(data, member):
    if data['inputs'] is None:
        return None
    return next((m for m in data['inputs']['member_bindings'] if m['member'] == member and m['state'] == 'bound'), None)


def _v4_links(document, value, call, data):
    for row in value['member_segments']:
        ref = row['segment']; native = document['intervals'][ref['interval_index']]['segments'][ref['segment_index']]
        index = row['member']['index']
        token = native['native_starts'][index] if index < len(native['native_starts']) else None
        _require(_same(row['native_start'], token), 'saved_reference_conflict')
        width = native['native_width' if native['kind'] == 'gapped_rows' else 'native_length']
        _require(row['alignment_columns']['value'] == (width['value'] if v4f.available(width) else None), 'saved_reference_conflict')
        if row['symbols_origin'] == 'native_rows':
            _require(native['kind'] == 'gapped_rows', 'saved_reference_conflict')
            records = [r for r in native['sequence_rows'] if r['member_index_0based'] == index]
            _require(len(records) == 1 and records[0]['sequence'] == row['aligned_sequence'], 'saved_reference_conflict')
        if row['symbols_origin'] == 'source_extracted' or row['source_comparison'] in ('match', 'mismatch'):
            binding = _bound_input(data, row['member']) if call['inputs_used'] else None
            _require(binding is not None and row['native_interval_0based_half_open'][1] <= binding['source_length'],
                     'saved_reference_conflict')
    for row in value['coverage']:
        denominator = row['denominator_bases']
        if denominator['state'] != 'available':
            continue
        if row['denominator_kind'] == 'native_declared_length':
            _require(denominator['value'] == v4f.scalar(document['metadata'], 'sequence_length', row['member']['index']),
                     'saved_reference_conflict')
        elif row['denominator_kind'] == 'validated_staged_length':
            binding = _bound_input(data, row['member']) if call['inputs_used'] else None
            _require(binding is not None and denominator['value'] == binding['source_length'], 'saved_reference_conflict')


def _backbone_links(document, value, call, data):
    for row in value['rows']:
        native = document['rows'][row['row_index']]
        for span in row['member_spans']:
            pairs = [p for p in native['pairs'] if p['member_index_0based'] == span['member']['index']]
            if not pairs:
                _require(span['state'] == 'missing', 'saved_reference_conflict')
            else:
                _require(len(pairs) == 1 and all(_same(span[k], pairs[0][k]) for k in
                    ('state', 'strand', 'interval_0based_half_open')), 'saved_reference_conflict')
    for row in value['coverage']:
        if row['denominator_bases']['state'] == 'available':
            binding = _bound_input(data, row['member']) if call['inputs_used'] else None
            _require(binding is not None and row['denominator_bases']['value'] == binding['source_length'],
                     'saved_reference_conflict')


def _bbcols_links(document, value, call, data, documents):
    associations = data['associations'] if call['associations_used'] else None
    joins = {} if associations is None else {(j['bbcols_document_id'], j['native_interval_index_0based']): j
                                           for j in associations['bbcols_interval_joins']}
    members = {} if associations is None else {(_key(j['artifact']), j['member']['namespace'], j['member']['index']): j
                                             for j in associations['native_member_joins']}
    for row in value['rows']:
        native = document['rows'][row['row_index']]
        token = native['native_interval_index_0based']; width = native['native_column_count']
        index = token['value'] if bc._available(token, 0) else None
        _require(row['native_interval_index_0based'] == index, 'saved_reference_conflict')
        _require(row['column_count']['value'] == (width['value'] if bc._available(width, 1) else None), 'saved_reference_conflict')
        present = {t['value'] for t in native['native_member_indices_0based'] if bc._available(t, 0)}
        _require(row['selected_present_members'] == [m for m in value['selection']['members'] if m['index'] in present],
                 'saved_reference_conflict')
        join = joins.get((document['document_id'], index)) if index is not None else None
        expected = (None, None) if join is None else (join['xmfa_document_id'], join['xmfa_block_index'])
        _require((row['xmfa_document_id'], row['xmfa_block_index']) == expected, 'saved_reference_conflict')
        if row['join_state'] != 'bound':
            continue
        _require(join is not None and join['state'] == 'bound' and call['xmfa_document_id'] == row['xmfa_document_id'],
                 'saved_reference_conflict')
        primary = documents[row['xmfa_document_id']]; block = primary['blocks'][row['xmfa_block_index']]
        _require(native['columns_0based_half_open'] is not None and block['alignment_column_count'] is not None
                 and native['columns_0based_half_open'][1] <= block['alignment_column_count'], 'saved_reference_conflict')
        for member in row['selected_present_members'] if row['selected_by_multiplicity'] is True else []:
            a = members.get((_key(document['artifact']), bc.SIDECAR_NAMESPACE, member['index']))
            b = members.get((_key(primary['artifact']), 'mauve1_member_1based', member['index'] + 1))
            _require(a is not None and b is not None and a['state'] == b['state'] == 'bound'
                     and a['input_member'] == b['input_member'], 'saved_reference_conflict')
            matching = [r for r in block['records'] if _positive(r['member_number']) == member['index'] + 1]
            _require(len(matching) == 1 and matching[0]['coordinate_state'] == 'present', 'saved_reference_conflict')
    for interval in value['intervals']:
        own = [r for r in value['rows'] if r['native_interval_index_0based'] == interval['native_interval_index_0based']]
        contributing = [r['row_index'] for r in own if r['selected_by_multiplicity'] is True
                        and document['rows'][r['row_index']]['state'] == 'parsed']
        _require(interval['contributing_row_indices'] == contributing, 'saved_reference_conflict')
        ranges = [document['rows'][i]['columns_0based_half_open'] for i in contributing]
        unions = interval['known_union_intervals']
        # These are reference/bounds checks, not a recalculation of the union.
        _require(all(any(a <= x < y <= b for a, b in unions) for x, y in ranges), 'saved_reference_conflict')
        _require(all(any(a == x for x, _ in ranges) and any(b == y for _, y in ranges)
                     for a, b in unions), 'saved_reference_conflict')
        refs = {(r['xmfa_document_id'], r['xmfa_block_index']) for r in own}
        expected = next(iter(refs)) if len(refs) == 1 else (None, None)
        _require((interval['xmfa_document_id'], interval['xmfa_block_index']) == expected, 'saved_reference_conflict')
        if interval['bound_block_width']['value'] is not None:
            did, bi = expected
            _require(did is not None and did == call['xmfa_document_id'] and did in documents
                     and bi < len(documents[did]['blocks'])
                     and interval['bound_block_width']['value'] == documents[did]['blocks'][bi]['alignment_column_count'],
                     'saved_reference_conflict')


def _native_record(document, ref):
    _require(ref['block_index'] < len(document['blocks']), 'saved_reference_conflict')
    block = document['blocks'][ref['block_index']]
    _require(ref['record_index'] < len(block['records']), 'saved_reference_conflict')
    row = block['records'][ref['record_index']]
    if 'column_0based' in ref:
        _require(ref['column_0based'] < len(row['sequence']), 'saved_reference_conflict')
    return row


def _coordinate_links(row, document, binding):
    native = _native_record(document, row['cell'])
    _require(row['aligned_symbol'] == native['sequence'][row['cell']['column_0based']]
             and row['member_number'] == _positive(native['member_number'])
             and row['native_strand'] == native['strand'], 'saved_reference_conflict')
    if row['state'] == 'residue':
        _require(native['coordinate_state'] == 'present' and native['interval_0based_half_open'][0]
                 <= row['native_position_0based'] < native['interval_0based_half_open'][1], 'saved_reference_conflict')
    if row['source_coordinate'] is None:
        return
    _require(binding is not None, 'source_binding_conflict')
    member = next((m for m in binding['members'] if m['member_number'] == row['member_number']), None)
    check = next((s for s in binding['source_checks'] if s['record'] == {k: row['cell'][k] for k in ('block_index', 'record_index')}), None)
    _require(member is not None and member['state'] == 'resolved' and check is not None and check['state'] == 'match',
             'source_binding_conflict')
    sc = row['source_coordinate']
    components = [c for c in member['components'] if c['file_id'] == sc['file_id'] and c['record_id'] == sc['record_id']]
    _require(len(components) == 1, 'source_binding_conflict')
    component = components[0]
    _require(sc['entry_1based'] == component['entry_1based'] and sc['position_0based'] < component['record_length']
             and row['native_position_0based'] == component['member_interval_0based_half_open'][0] + sc['position_0based'],
             'source_binding_conflict')
    for original in row['original_coordinates']:
        mappings = [m for m in binding['original_maps'] if m['file_id'] == sc['file_id'] and m['record_id'] == sc['record_id']
            and m['original_member'] == original['original_member'] and m['transformation_id'] == original['transformation_id']
            and m['original_length'] == original['original_length'] and m['evidence'] == original['evidence']]
        _require(any(m['staged_interval_0based_half_open'][0] <= sc['position_0based'] < m['staged_interval_0based_half_open'][1]
            and m['original_interval_0based_half_open'][0] <= original['position_0based'] < m['original_interval_0based_half_open'][1]
            and original['position_0based'] == (m['original_interval_0based_half_open'][0]
                + sc['position_0based'] - m['staged_interval_0based_half_open'][0] if m['strand'] == '+' else
                m['original_interval_0based_half_open'][1] - 1 - sc['position_0based'] + m['staged_interval_0based_half_open'][0])
            and original['strand'] == ('+' if sc['strand'] == m['strand'] else '-')
            for m in mappings), 'source_binding_conflict')


def _xmfa_links(document, value, call, binding):
    kind = call['kind']
    if kind == 'xmfa_alignment':
        _require(value['parameters'] == {k: call[k] for k in ('case_policy', 'selected_pairs')}, 'component_identity_conflict')
        for block in value['blocks']:
            native = document['blocks'][block['block_index']]
            expected = [{'block_index': block['block_index'], 'record_index': r['record_index']} for r in native['records']
                        if _positive(r['member_number']) in call['selection']['member_numbers']]
            _require(block['record_refs'] == expected, 'saved_reference_conflict')
    elif kind == 'xmfa_coverage':
        _require(value['parameters'] == {'basis': call['basis']}, 'component_identity_conflict')
        members = {} if binding is None else {m['member_number']: m for m in binding['members']}
        for row in value['members']:
            member = members.get(row['member_number'])
            _require(row['source_length']['value'] == (member['source_length'] if member is not None else None),
                     'source_binding_conflict')
            for placement in row['placements']:
                native = _native_record(document, placement['record'])
                a, b = placement['interval_0based_half_open']
                _require(native['coordinate_state'] == 'present' and _positive(native['member_number']) == row['member_number']
                    and placement['strand'] == native['strand'] and native['interval_0based_half_open'][0] <= a < b
                    <= native['interval_0based_half_open'][1], 'saved_reference_conflict')
            for original in row['original_coverage']:
                _require(binding is not None and member is not None and member['state'] == 'resolved', 'source_binding_conflict')
                keys = {(c['file_id'], c['record_id']) for c in member['components']}
                maps = [m for m in binding['original_maps'] if (m['file_id'], m['record_id']) in keys
                        and m['original_member'] == original['original_member']]
                _require(bool(maps), 'source_binding_conflict')
                if original['original_length']['value'] is not None:
                    _require(all(m['original_length'] == original['original_length']['value'] for m in maps), 'source_binding_conflict')
    elif kind == 'xmfa_coordinates':
        _require([r['cell'] for r in value['cells']] == call['cells'], 'component_identity_conflict')
        for row in value['cells']:
            _coordinate_links(row, document, binding)
    else:
        _require([{k: r[k] for k in ('member_number', 'position_0based')} for r in value['queries']] == call['queries'],
                 'component_identity_conflict')
        for row in value['queries']:
            _require(row['search_completeness'] == document['completeness'], 'saved_reference_conflict')
            for ref in row['matches']:
                native = _native_record(document, ref)
                _require(native['coordinate_state'] == 'present' and _positive(native['member_number']) == row['member_number']
                    and native['sequence'][ref['column_0based']] != '-'
                    and native['interval_0based_half_open'][0] <= row['position_0based'] < native['interval_0based_half_open'][1],
                    'saved_reference_conflict')


def validate_genome_alignment_components(value: dict, *, data: dict) -> dict:
    from .bvbrc_genome_alignment_sheet import validate_genome_alignment_data
    data = validate_genome_alignment_data(data); _finite(value)
    _shape(value, ('schema_version', 'analysis_id', 'calculation_plan', 'source_bindings', 'outcomes', 'requirements', 'diagnostics'))
    _require(value['schema_version'] == 'bvbrc_genome_alignment_components_v2')
    _require(value['analysis_id'] == data['analysis_id'], 'analysis_id_conflict')
    plan = validate_genome_alignment_calculation_plan(value['calculation_plan'], document_slots=tuple(data['document_slots']))
    _, resolutions, documents = _indexes(data)
    _array(value['source_bindings']); _array(value['outcomes']); _reports(value)
    expected_snapshots = []
    for request in plan['requests']:
        resolution = resolutions[request['document_slot_id']]
        if resolution['state'] == 'resolved' and _source_available(data, request) and resolution['document_id'] not in expected_snapshots:
            expected_snapshots.append(resolution['document_id'])
    bindings = {}
    for snapshot in value['source_bindings']:
        binding = _snapshot(snapshot, data, documents)
        _require(snapshot['document_id'] not in bindings, 'source_binding_conflict')
        bindings[snapshot['document_id']] = binding
    _require(list(bindings) == expected_snapshots, 'source_binding_conflict')
    _require(len(value['outcomes']) == len(plan['requests']), 'request_outcome_conflict')
    for index, (request, outcome) in enumerate(zip(plan['requests'], value['outcomes'])):
        _shape(outcome, ('request_id', 'request_index', 'kind', 'document_slot_id', 'document_id',
                        'state', 'call', 'measurement', 'requirements', 'diagnostics'))
        _uint(outcome['request_index']); _reports(outcome)
        _require(outcome['request_index'] == index and all(outcome[k] == request[k] for k in
            ('request_id', 'kind', 'document_slot_id')), 'request_outcome_conflict')
        resolution = resolutions[request['document_slot_id']]
        call = _call(data, request, resolutions)
        _require(_same(outcome['call'], call), 'component_identity_conflict')
        reports = [_request_reports(data, request, index, call)]
        if call is None:
            _require(outcome['document_id'] is None and outcome['measurement'] is None and outcome['state'] ==
                ('incompatible' if resolution['state'] == 'incompatible' else 'missing'), 'request_outcome_conflict')
        else:
            did = resolution['document_id']; document = documents[did]
            _require(outcome['document_id'] == did, 'document_identity_conflict')
            binding = bindings.get(call.get('source_binding_document_id'))
            if binding is not None:
                reports.append(binding)
            failure = _target_failure(document, call, binding)
            if outcome['state'] == 'incompatible':
                _require(outcome['measurement'] is None and failure in TARGET_ERRORS[request['kind']], 'request_outcome_conflict')
                reason = 'selection_target_missing' if failure in MISSING_TARGET_ERRORS else 'selection_target_incompatible'
                reports.append(_cause(data, request, index, reason, affected=failure))
            else:
                _require(outcome['state'] == 'calculated' and failure is None, 'request_outcome_conflict')
                measurement = outcome['measurement']; _shape(measurement, ('kind', 'value'))
                _require(measurement['kind'] == request['kind'], 'component_identity_conflict')
                native = COMPONENT_VALIDATORS[request['kind']](measurement['value'])
                _require(native['document_id'] == did, 'document_identity_conflict')
                if 'selection' in call:
                    _require(_same(native['selection'], call['selection']), 'component_identity_conflict')
                if request['kind'] == 'mauve_v4_segments':
                    _v4_links(document, native, call, data)
                elif request['kind'] == 'mauve_backbone':
                    _backbone_links(document, native, call, data)
                elif request['kind'] == 'mauve_bbcols':
                    _bbcols_links(document, native, call, data, documents)
                else:
                    _xmfa_links(document, native, call, binding)
                reports.append(native)
        for field in ('requirements', 'diagnostics'):
            _require(_same(outcome[field], _union(reports, field)), 'request_outcome_conflict')
    groups = [data, *[s['bindings'] for s in value['source_bindings']], *value['outcomes']]
    for field in ('requirements', 'diagnostics'):
        _require(_same(value[field], _union(groups, field)), 'component_identity_conflict')
    _links(value, {r['requirement_id'] for r in value['requirements']})
    return deepcopy(value)


__all__ = ['validate_genome_alignment_calculation_plan', 'validate_genome_alignment_components']
