"""Element, metadata and numerical-sheet construction from supplied records."""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import re

import numpy as np

from .chromatin_interaction_contracts import ChromatinValidationError, validate_chromatin_record
from .chromatin_cooler_inputs import failure
from .chromatin_interaction_tables import CHUNK_ROWS, _expected_dtype, validate_population_arrays


def parse_chromatin_elements(content: bytes, *, spec):
    spec = validate_chromatin_record('ElementSpec', spec)
    result = {'source_file': deepcopy(spec['file']), 'input_data_row_count': 0,
              'rows': [], 'rejected_rows': [], 'other_lines': [], 'extent': 'complete', 'failures': []}
    if type(content) is not bytes:
        raise ChromatinValidationError('element_bytes_required')
    if len(content) != spec['file']['size_bytes'] or hashlib.sha256(content).hexdigest() != spec['file']['sha256']:
        result['extent'] = 'unavailable'
        result['failures'].append(failure('input_digest_mismatch', spec=spec, stage='input', requirement='matching_file_identity'))
        return validate_chromatin_record('ParsedElements', result)
    assignments = {a['source_data_row']: a for a in spec['assignments']}
    contigs = None if spec['reference']['contigs'] is None else {c['chromosome']: c['length_bp'] for c in spec['reference']['contigs']}
    for number, raw_line in enumerate(content.splitlines(keepends=True), 1):
        line = raw_line.rstrip(b'\r\n')
        stripped = line.lstrip()
        kind = ('blank' if not stripped else 'comment' if stripped.startswith(b'#') else 'track' if stripped == b'track' or stripped.startswith(b'track ') else 'browser' if stripped == b'browser' or stripped.startswith(b'browser ') else None)
        if kind:
            result['other_lines'].append({'source_line': number, 'kind': kind, 'raw_line_base64': base64.b64encode(raw_line).decode('ascii')})
            continue
        ordinal = result['input_data_row_count']
        result['input_data_row_count'] += 1
        assignment = assignments.get(ordinal)
        row_failures = []
        def issue(code, requirement='valid_native_structure'):
            row_failures.append(failure(code, spec=spec, locator={'kind': 'bed_line', 'value': number}, stage='input', element_key=None if assignment is None else assignment['element_key'], requirement=requirement))
        try:
            columns = line.decode('utf-8', 'strict').split('\t')
            if len(columns) < 3 or not columns[0] or any(re.fullmatch(r'0|[1-9][0-9]*', value) is None for value in columns[1:3]):
                raise ValueError('invalid_bed_fields')
            start, end = int(columns[1]), int(columns[2])
            if start >= end or end > np.iinfo(np.int64).max or contigs is not None and (columns[0] not in contigs or end > contigs[columns[0]]):
                raise ValueError('invalid_bed_coordinates')
        except (UnicodeError, ValueError):
            issue('invalid_coordinate')
            result['rejected_rows'].append({'source_data_row': ordinal, 'source_line': number, 'raw_line_base64': base64.b64encode(raw_line).decode('ascii'), 'failures': row_failures})
            result['failures'].extend(row_failures)
            continue
        position = None
        if assignment is None:
            issue('element_assignment_missing', 'explicit_element_assignment')
        else:
            position = start if assignment['anchor']['policy'] == 'interval_start' else assignment['anchor']['position_bp']
            if not start <= position < end:
                issue('anchor_outside_element')
                result['rejected_rows'].append({'source_data_row': ordinal, 'source_line': number, 'raw_line_base64': base64.b64encode(raw_line).decode('ascii'), 'failures': row_failures})
                result['failures'].extend(row_failures)
                continue
        result['rows'].append({'source_data_row': ordinal, 'source_line': number, 'columns': columns,
            'chromosome': columns[0], 'start_bp': start, 'end_bp': end, 'name': columns[3] if len(columns) > 3 else None,
            'element_key': None if assignment is None else assignment['element_key'],
            'class': None if assignment is None else assignment['class'],
            'gene_links': [] if assignment is None else deepcopy(assignment['gene_links']),
            'anchor': None if assignment is None else deepcopy(assignment['anchor']), 'anchor_position_bp': position})
        result['failures'].extend(row_failures)
    for ordinal, assignment in assignments.items():
        if ordinal >= result['input_data_row_count']:
            issue = failure('element_assignment_missing', spec=spec, stage='input', requirement='explicit_element_assignment', element_key=assignment['element_key'])
            issue['field_path'] = '/assignments/' + str(spec['assignments'].index(assignment)) + '/source_data_row'
            result['failures'].append(issue)
    if result['failures']:
        result['extent'] = 'partial'
    return validate_chromatin_record('ParsedElements', result)


def _check_sources(request, native, elements):
    if native['format'] != request['contact']['format']:
        raise ChromatinValidationError('native_format_request_mismatch')
    if [p['selected_region'] for p in native['populations']] != request['populations']:
        raise ChromatinValidationError('native_population_request_mismatch')
    metadata = native['native_metadata']
    if metadata is not None:
        spec = request['contact']
        if metadata['source_file'] != spec['file'] or metadata['source_ref'] != spec['source_ref'] or any(metadata[key] != spec[key] for key in ('format', 'group_path', 'value_field', 'value_kind', 'value_unit')) or metadata['bin_size_bp'] != spec['resolution_bp']:
            raise ChromatinValidationError('native_source_request_mismatch')
    if elements is not None and (request['elements'] is None or elements['source_file'] != request['elements']['file']):
        raise ChromatinValidationError('element_source_request_mismatch')
    if elements is not None:
        _check_element_rows(elements, request['elements'])


def _check_element_rows(elements, spec):
    assignments = {row['source_data_row']: row for row in spec['assignments']}
    all_rows = elements['rows'] + elements['rejected_rows']
    ordinals = [row['source_data_row'] for row in all_rows]
    if sorted(ordinals) != list(range(elements['input_data_row_count'])):
        raise ChromatinValidationError('element_occurrence_population_mismatch')
    lines = [row['source_line'] for row in all_rows + elements['other_lines']]
    if len(set(lines)) != len(lines) or sorted(lines) != list(range(1, len(lines) + 1)):
        raise ChromatinValidationError('element_line_population_mismatch')
    if [r['source_data_row'] for r in elements['rows']] != sorted(r['source_data_row'] for r in elements['rows']):
        raise ChromatinValidationError('element_row_order_mismatch')
    for row in elements['rows']:
        columns = row['columns']
        if columns[0] != row['chromosome'] or columns[1] != str(row['start_bp']) or columns[2] != str(row['end_bp']) or row['name'] != (columns[3] if len(columns) > 3 else None):
            raise ChromatinValidationError('element_original_columns_mismatch')
        assignment = assignments.get(row['source_data_row'])
        if assignment is None:
            if any(row[field] is not None for field in ('element_key', 'class', 'anchor', 'anchor_position_bp')) or row['gene_links']:
                raise ChromatinValidationError('unassigned_element_interpretation')
        else:
            if any(row[field] != assignment[field] for field in ('element_key', 'class', 'gene_links', 'anchor')):
                raise ChromatinValidationError('element_assignment_mismatch')
            position = row['start_bp'] if assignment['anchor']['policy'] == 'interval_start' else assignment['anchor']['position_bp']
            if row['anchor_position_bp'] != position or not row['start_bp'] <= position < row['end_bp']:
                raise ChromatinValidationError('element_anchor_mismatch')


def extract_chromatin_metadata(*, request, native, supplied, elements):
    request = validate_chromatin_record('ChromatinRequest', request)
    native = validate_chromatin_record('ContactExtraction', native)
    supplied = validate_chromatin_record('MetadataSpec', supplied)
    if supplied != request['supplied_metadata']:
        raise ChromatinValidationError('supplied_metadata_request_mismatch')
    _check_sources(request, native, elements)
    contact, element_spec = request['contact'], request['elements']
    result = {'reference_assertions': [], 'reference_relations': [], **{key: deepcopy(supplied[key]) for key in ('samples', 'contact_sample_links', 'dependence_groups', 'supplied_uncertainty')}, 'failures': []}
    assertions = result['reference_assertions']
    if native['native_metadata'] is not None:
        assertions.append({'assertion_key': 'native_ref', 'input_key': contact['input_key'], 'origin': 'native', 'reference': deepcopy(native['native_metadata']['reference_assertion'])})
    assertions.append({'assertion_key': 'supplied_ref', 'input_key': contact['input_key'], 'origin': 'supplied', 'reference': deepcopy(supplied['reference'])})
    if element_spec is not None:
        assertions.append({'assertion_key': 'element_ref', 'input_key': element_spec['input_key'], 'origin': 'supplied', 'reference': deepcopy(element_spec['reference'])})
    chromosomes = {row['chromosome']: row['length_bp'] for row in native['chromosomes']}
    for population in request['populations']:
        references = [row['reference'] for row in assertions]
        accessions = {ref['assembly_accession'] for ref in references if ref['assembly_accession'] is not None}
        labels = {ref['assembly_label'] for ref in references if ref['assembly_label'] is not None}
        lengths = []
        missing_contig = False
        for reference in references:
            if reference['contigs'] is not None:
                length = next((c['length_bp'] for c in reference['contigs'] if c['chromosome'] == population['chromosome']), None)
                missing_contig |= length is None
                if length is not None:
                    lengths.append(length)
        conflict = len(accessions) > 1 or len(labels) > 1 or len(set(lengths)) > 1 or missing_contig
        if conflict:
            relation, basis = 'conflicting_assertions', 'conflict'
            result['failures'].append(failure('reference_conflict', spec=contact, population=population, stage='metadata', requirement='compatible_reference'))
        elif len(accessions) == 1 and sum(ref['assembly_accession'] is not None for ref in references) >= 2:
            relation, basis = 'consistent_assertions', 'accession_agreement'
        elif len(labels) == 1 and sum(ref['assembly_label'] is not None for ref in references) >= 2:
            relation, basis = 'consistent_assertions', 'label_agreement'
        else:
            relation, basis = 'unknown', 'contig_only' if lengths else 'unknown'
        supplied_length = None
        if supplied['reference']['contigs'] is not None:
            supplied_length = next((c['length_bp'] for c in supplied['reference']['contigs'] if c['chromosome'] == population['chromosome']), None)
        result['reference_relations'].append({'contact_input_key': contact['input_key'], 'element_input_key': None if element_spec is None else element_spec['input_key'], 'population_key': population['population_key'], 'relation': relation, 'basis': basis, 'assertion_keys': [row['assertion_key'] for row in assertions], 'chromosome': population['chromosome'], 'native_length_bp': chromosomes.get(population['chromosome']), 'supplied_length_bp': supplied_length})
    input_keys = {contact['input_key']} | ({element_spec['input_key']} if element_spec else set())
    population_keys = {p['population_key'] for p in request['populations']}
    if any(u['input_key'] not in input_keys or u['population_key'] is not None and u['population_key'] not in population_keys for u in supplied['supplied_uncertainty']):
        raise ChromatinValidationError('unknown_uncertainty_association')
    attributes = {} if native['native_metadata'] is None else {a['path']: a for a in native['native_metadata']['attributes']}
    for binding in supplied['native_attribute_bindings']:
        targets = {row[binding['meaning']] for row in supplied['samples'] if binding['meaning'] in row}
        if binding['meaning'] == 'assembly_label':
            targets = {supplied['reference']['assembly_label']}
        if binding['supplied_target_key'] not in targets:
            raise ChromatinValidationError('unknown_attribute_binding_target')
        attribute = attributes.get(binding['native_attribute_path'])
        if attribute is None or attribute['value_state'] != 'decoded' or attribute['value'] != binding['supplied_target_key']:
            result['failures'].append(failure('reference_conflict' if binding['meaning'] == 'assembly_label' else 'input_unavailable', spec=contact, locator={'kind': 'hdf5_path', 'value': binding['native_attribute_path']}, stage='metadata', requirement='compatible_reference' if binding['meaning'] == 'assembly_label' else 'valid_native_structure'))
    return validate_chromatin_record('MetadataRelations', result)


def _measurement(value, population_key, unit, reason=None):
    return {'value': value, 'state': 'observed' if value is not None else 'missing',
            'unit': {'kind': 'source_contact', 'source_unit': unit}, 'reason': reason,
            'population_key': population_key, 'numerator': None, 'denominator': None,
            'uncertainty': {'kind': 'not_measured', 'value': None, 'unit': None}}


def _pair_rows_for_cell(array, x, y):
    if array is None:
        return None
    left, right = np.searchsorted(array['bin1_id'], [x, x], side='left')[0], np.searchsorted(array['bin1_id'], x, side='right')
    sub = array[int(left):int(right)]
    a, b = np.searchsorted(sub['bin2_id'], y, side='left'), np.searchsorted(sub['bin2_id'], y, side='right')
    return sub[int(a):int(b)]


def _raw_cell(population, arrays, x, y, native):
    if x is None or y is None:
        return None, 'unavailable', [], 'anchor_bin_unavailable'
    if population['native_storage_mode'] in ('symmetric-upper', 'hic-symmetric'):
        x, y = min(x, y), max(x, y)
    rows = _pair_rows_for_cell(arrays['contacts'], x, y)
    locators = []
    if rows is not None:
        for row in rows:
            if native['format'] == 'cooler_hdf5_v3':
                locators.append({'kind': 'native_row', 'value': {'table_path': native['group_path'].rstrip('/') + '/pixels', 'row_index': int(row['source_row'])}})
            else:
                chromosome = int(arrays['bins']['chromosome_index'][0])
                locators.append({'kind': 'hic_block', 'value': {'chromosome1_index': chromosome, 'chromosome2_index': chromosome, 'resolution_bp': native['bin_size_bp'], 'block_id': int(row['source_block']), 'record_ordinal': int(row['source_row'])}})
        if len(rows) > 1:
            return None, 'unavailable', locators, 'duplicate_native_pixel'
        if len(rows) == 1:
            raw = rows['value'][0]
            if not np.isfinite(raw):
                return None, 'unavailable', locators, 'native_value_nonfinite'
            value = raw.item()
            return value, 'explicit_native', locators, 'native_value_negative' if value < 0 and native['value_kind'] == 'contact_count' else None
    states = _pair_rows_for_cell(arrays['cell_states'], x, y)
    if states is not None and len(states):
        return None, 'unavailable', [], 'native_chunk_unavailable' if 5 in states['state'] else 'native_value_nonfinite'
    if arrays['dense_values'] is not None:
        low = int(arrays['bins']['bin_id'][0])
        raw = arrays['dense_values'][x - low, y - low]
        if np.isfinite(raw):
            return raw.item(), 'explicit_native', [], None
        return None, 'unavailable', [], 'native_value_nonfinite'
    if population['read_evidence']['implicit_zero_semantics'] == 'validated_sparse_absence':
        return 0, 'validated_implicit_zero', [], None
    return None, 'unavailable', [], 'incomplete_comparison_population'


def _anchors_and_pairs(request, population, ordinal, elements, relation, arrays, native):
    anchors, pairs = [], []
    if elements is None:
        return anchors, pairs
    region, bins = population['selected_region'], arrays['bins']
    for element in elements['rows']:
        if element['element_key'] is None:
            continue
        position = element['anchor_position_bp']
        inside = element['chromosome'] == region['chromosome'] and region['start_bp'] <= position < region['end_bp']
        row = {'element_key': element['element_key'], 'source_data_row': element['source_data_row'], 'class': element['class'], 'chromosome': element['chromosome'], 'anchor_position_bp': position, 'bin_id': None, 'bin_ordinal': None, 'membership': 'inside' if inside else 'outside', 'reference_relation': relation, 'reason': None}
        if inside:
            if relation == 'conflicting_assertions':
                row.update(membership='unresolved', reason='reference_conflict')
            elif bins is None:
                row.update(membership='unresolved', reason='anchor_bin_unavailable')
            else:
                index = int(np.searchsorted(bins['end_bp'], position, side='right'))
                if index >= len(bins) or not int(bins['start_bp'][index]) <= position < int(bins['end_bp'][index]):
                    row.update(membership='unresolved', reason='anchor_bin_unavailable')
                else:
                    row.update(bin_id=int(bins['bin_id'][index]), bin_ordinal=index)
        anchors.append(row)
    enhancers = [a for a in anchors if a['class'] == 'enhancer' and a['membership'] != 'outside']
    promoters = [a for a in anchors if a['class'] == 'promoter' and a['membership'] != 'outside']
    for enhancer in enhancers:
        for promoter in promoters:
            if native is None:
                value, origin, locators, reason = None, 'unavailable', [], 'population_unavailable'
            else:
                value, origin, locators, reason = _raw_cell(population, arrays, enhancer['bin_id'], promoter['bin_id'], native)
            if relation == 'conflicting_assertions':
                reason = 'reference_conflict'
            pairs.append({'pair_key': f'p{ordinal}.e{enhancer["source_data_row"]}.p{promoter["source_data_row"]}', 'population_key': population['population_key'],
                'enhancer_element_key': enhancer['element_key'], 'promoter_element_key': promoter['element_key'],
                'enhancer_bin_id': enhancer['bin_id'], 'promoter_bin_id': promoter['bin_id'],
                'enhancer_bin_ordinal': enhancer['bin_ordinal'], 'promoter_bin_ordinal': promoter['bin_ordinal'],
                'enhancer_anchor_bp': enhancer['anchor_position_bp'], 'promoter_anchor_bp': promoter['anchor_position_bp'],
                'raw_contact': _measurement(value, population['population_key'], request['contact']['value_unit'], reason if value is None else None),
                'cell_origin': origin, 'source_locators': locators, 'reference_relation': relation, 'reason': reason})
    return anchors, pairs


def build_chromatin_sheet(*, request, contacts, elements, metadata, tables, table_views):
    request = validate_chromatin_record('ChromatinRequest', request)
    contacts = validate_chromatin_record('ContactExtraction', contacts)
    metadata = validate_chromatin_record('MetadataRelations', metadata)
    if elements is not None:
        elements = validate_chromatin_record('ParsedElements', elements)
    _check_sources(request, contacts, elements)
    expected_metadata = extract_chromatin_metadata(request=request, native=contacts, supplied=request['supplied_metadata'], elements=elements)
    if metadata != expected_metadata:
        raise ChromatinValidationError('metadata_relations_mismatch')
    tables = [validate_chromatin_record('TableDescriptor', row) for row in tables]
    if [{key: value for key, value in row.items() if key != 'file'} for row in tables] != contacts['table_drafts']:
        raise ChromatinValidationError('table_extraction_mismatch')
    if table_views['version'] != 'chromatin_contact_arrays_v1' or list(table_views['populations']) != [p['population_key'] for p in request['populations']]:
        raise ChromatinValidationError('array_population_mismatch')
    populations = deepcopy(contacts['populations'])
    for ordinal, population in enumerate(populations):
        arrays = table_views['populations'][population['population_key']]
        validate_population_arrays(population, arrays, contacts['chromosomes'])
        relation = next(row['relation'] for row in metadata['reference_relations'] if row['population_key'] == population['population_key'])
        anchors, pairs = _anchors_and_pairs(request, population, ordinal, elements, relation, arrays, contacts['native_metadata'])
        population.update(element_anchor_rows=anchors, pair_rows=pairs)
    sheet = {'version': 'chromatin_interaction_sheet_v1', 'request': request,
             'native': {'metadata': deepcopy(contacts['native_metadata']), 'chromosomes': deepcopy(contacts['chromosomes'])},
             'references': {'assertions': metadata['reference_assertions'], 'relations': metadata['reference_relations']},
             'samples': {key: metadata[key] for key in ('samples', 'contact_sample_links', 'dependence_groups', 'supplied_uncertainty')},
             'elements': elements, 'populations': populations, 'data_tables': tables,
             'failures': deepcopy(contacts['failures']) + ([] if elements is None else deepcopy(elements['failures'])) + deepcopy(metadata['failures'])}
    sheet = validate_chromatin_record('ContactSheet', sheet)
    validate_chromatin_sheet_arrays(sheet, table_views)
    return sheet


def validate_chromatin_sheet_arrays(sheet, table_views):
    """Check saved assertions against actual arrays, including anchor/cell joins."""
    if table_views['version'] != 'chromatin_contact_arrays_v1' or list(table_views['populations']) != [p['population_key'] for p in sheet['populations']]:
        raise ChromatinValidationError('array_population_mismatch')
    extraction = {'format': sheet['request']['contact']['format'],
        'format_version': None if sheet['native']['metadata'] is None else sheet['native']['metadata']['format_version'],
        'native_metadata': sheet['native']['metadata'], 'chromosomes': sheet['native']['chromosomes'],
        'populations': [{k: v for k, v in row.items() if k not in ('element_anchor_rows', 'pair_rows')} for row in sheet['populations']],
        'table_drafts': [{k: v for k, v in row.items() if k != 'file'} for row in sheet['data_tables']], 'failures': sheet['failures']}
    metadata = extract_chromatin_metadata(request=sheet['request'], native=extraction, supplied=sheet['request']['supplied_metadata'], elements=sheet['elements'])
    if sheet['references'] != {'assertions': metadata['reference_assertions'], 'relations': metadata['reference_relations']} or sheet['samples'] != {k: metadata[k] for k in sheet['samples']}:
        raise ChromatinValidationError('saved_metadata_relationship_mismatch')
    for ordinal, population in enumerate(sheet['populations']):
        key = population['population_key']
        arrays = table_views['populations'][key]
        validate_population_arrays(population, arrays, sheet['native']['chromosomes'])
        descriptors = [t for t in sheet['data_tables'] if t['population_key'] == key]
        for descriptor in descriptors:
            array = arrays[descriptor['role']]
            if (array is None) != (descriptor['availability'] != 'present'):
                raise ChromatinValidationError('array_availability_mismatch')
            if array is not None and (array.flags.writeable or len(array) != descriptor['row_count']):
                raise ChromatinValidationError('mutable_or_wrong_length_array')
            if array is not None:
                shape = [len(array), 4] if descriptor['role'] == 'bins' else list(array.shape)
                if shape != descriptor['shape'] or array.dtype != _expected_dtype(descriptor):
                    raise ChromatinValidationError('array_dtype_or_shape_mismatch')
        evidence = population['read_evidence']
        if evidence['implicit_zero_semantics'] == 'validated_sparse_absence' and any(arrays[role] is None for role in ('bins', 'contacts', 'cell_states')):
            raise ChromatinValidationError('unavailable_tables_claim_sparse_zeros')
        if arrays['bins'] is not None:
            n = len(arrays['bins'])
            if population['raw_cell_population']['directed_cells'] != n * n or population['raw_cell_population']['unique_unordered_cells'] != (n * (n + 1) // 2 if evidence['symmetry'] != 'not_established' else None):
                raise ChromatinValidationError('cell_population_axis_mismatch')
        summary = population['normalization']
        if summary['specification'] != sheet['request']['normalization']:
            raise ChromatinValidationError('normalization_request_mismatch')
        weights = arrays['weights']
        if weights is not None:
            valid = int(np.count_nonzero(np.isfinite(weights) & (weights > 0)))
            masked = int(np.count_nonzero(np.isnan(weights)))
            invalid = len(weights) - valid - masked
            weight_key = next(d['table_key'] for d in descriptors if d['role'] == 'weights')
            if (summary['valid_bin_count'], summary['masked_bin_count'], summary['invalid_bin_count']) != (valid, masked, invalid) or summary['vector_table_key'] != weight_key or summary['availability'] != ('partial' if invalid else 'available'):
                raise ChromatinValidationError('normalization_array_mismatch')
        elif summary['availability'] in ('available', 'partial'):
            raise ChromatinValidationError('unavailable_weight_vector_claimed_available')
        contacts = arrays['contacts']
        if contacts is not None:
            if contacts.dtype.fields['value'][0].str != sheet['native']['metadata']['value_dtype']:
                raise ChromatinValidationError('native_contact_dtype_mismatch')
            counts = population['raw_cell_population']
            if counts['stored_rows'] != len(contacts):
                raise ChromatinValidationError('stored_row_count_mismatch')
            zeros = nonfinite = observed = represented = 0
            previous = None
            duplicate = False
            for start in range(0, len(contacts), CHUNK_ROWS):
                block = contacts[start:start + CHUNK_ROWS]
                finite = np.isfinite(block['value'])
                zeros += int(np.count_nonzero(finite & (block['value'] == 0)))
                bad = (~finite) | ((block['value'] < 0) if sheet['request']['contact']['value_kind'] == 'contact_count' else False)
                if population['native_storage_mode'] == 'symmetric-upper':
                    bad |= block['bin1_id'] > block['bin2_id']
                observed += len(block) - int(np.count_nonzero(bad))
                directed = np.where(block['bin1_id'] == block['bin2_id'], 1, 2) if population['native_storage_mode'] in ('symmetric-upper', 'hic-symmetric') else np.ones(len(block), dtype=np.int64)
                nonfinite += int(np.sum(directed[~finite]))
                represented += int(np.sum(directed))
                for row in block:
                    pair = (int(row['bin1_id']), int(row['bin2_id']))
                    duplicate |= pair == previous
                    previous = pair
                    if sheet['request']['contact']['format'] == 'cooler_hdf5_v3' and int(row['source_block']) != -1:
                        raise ChromatinValidationError('invalid_cooler_source_locator')
                    ranges = population['read_evidence']['required_native_row_ranges']
                    if ranges and not any(r['start_row'] <= int(row['source_row']) < r['end_row'] for r in ranges):
                        raise ChromatinValidationError('source_row_outside_read_evidence')
                    if not np.isfinite(row['value']):
                        states = _pair_rows_for_cell(arrays['cell_states'], pair[0], pair[1])
                        tag = 2 if np.isnan(row['value']) else (3 if row['value'] > 0 else 4)
                        if states is None or not np.any(states['state'] == tag):
                            raise ChromatinValidationError('nonfinite_contact_state_missing')
                    if arrays['dense_values'] is not None:
                        low = int(arrays['bins']['bin_id'][0])
                        value = arrays['dense_values'][pair[0] - low, pair[1] - low]
                        if not (value == row['value'] or np.isnan(value) and np.isnan(row['value'])):
                            raise ChromatinValidationError('sparse_dense_value_mismatch')
            if counts['explicit_zero_rows'] != zeros or counts['native_nonfinite_directed_cells'] != nonfinite or counts['validated_observed_row_count'] != observed:
                raise ChromatinValidationError('native_cell_counts_mismatch')
            if duplicate and population['read_evidence']['implicit_zero_semantics'] == 'validated_sparse_absence':
                raise ChromatinValidationError('duplicate_pixels_claimed_complete')
            if population['read_evidence']['implicit_zero_semantics'] == 'validated_sparse_absence' and counts['implicit_zero_directed_cells'] != len(arrays['bins']) ** 2 - represented:
                raise ChromatinValidationError('implicit_zero_count_mismatch')
        states = arrays['cell_states']
        if states is not None:
            for state in states:
                rows = _pair_rows_for_cell(contacts, int(state['bin1_id']), int(state['bin2_id']))
                if rows is not None and len(rows) and np.any(np.isfinite(rows['value'])):
                    raise ChromatinValidationError('finite_contact_exceptional_state_conflict')
        if population['read_evidence']['symmetry'] == 'square_reciprocal_verified':
            if population['native_storage_mode'] != 'square' or contacts is None:
                raise ChromatinValidationError('invalid_square_symmetry_claim')
            for row in contacts:
                reverse = _pair_rows_for_cell(contacts, int(row['bin2_id']), int(row['bin1_id']))
                if len(reverse) > 1 or not np.isfinite(row['value']) or row['value'] != (reverse['value'][0] if len(reverse) else 0):
                    raise ChromatinValidationError('square_reciprocity_mismatch')
        if arrays['dense_values'] is not None and contacts is not None and evidence['implicit_zero_semantics'] == 'validated_sparse_absence':
            # Check implicit cells in bounded row segments, never a new n*n array.
            dense = arrays['dense_values']
            if dense.dtype.str != sheet['native']['metadata']['value_dtype']:
                raise ChromatinValidationError('native_dense_dtype_mismatch')
            low = int(arrays['bins']['bin_id'][0])
            for i in range(len(dense)):
                for begin in range(0, len(dense), CHUNK_ROWS):
                    for j in range(begin, min(begin + CHUNK_ROWS, len(dense))):
                        x, y = i + low, j + low
                        if population['native_storage_mode'] in ('symmetric-upper', 'hic-symmetric'):
                            x, y = min(x, y), max(x, y)
                        rows = _pair_rows_for_cell(contacts, x, y)
                        if len(rows) == 0:
                            exceptional = _pair_rows_for_cell(states, x, y)
                            if (exceptional is None or not len(exceptional)) and dense[i, j] != 0:
                                raise ChromatinValidationError('dense_value_conflicts_with_sparse_absence')
        relation = next((r['relation'] for r in sheet['references']['relations'] if r['population_key'] == key), None)
        if relation is None:
            raise ChromatinValidationError('missing_reference_relation')
        anchors, pairs = _anchors_and_pairs(sheet['request'], population, ordinal, sheet['elements'], relation, arrays, sheet['native']['metadata'])
        if anchors != population['element_anchor_rows']:
            raise ChromatinValidationError('element_anchor_join_mismatch')
        actual_pairs = population['pair_rows']
        if len(actual_pairs) != len(pairs) or len({p['pair_key'] for p in actual_pairs}) != len(actual_pairs):
            raise ChromatinValidationError('pair_population_mismatch')
        for actual, expected in zip(actual_pairs, pairs):
            if {k: v for k, v in actual.items() if k != 'pair_key'} != {k: v for k, v in expected.items() if k != 'pair_key'}:
                raise ChromatinValidationError('pair_cell_join_mismatch')
