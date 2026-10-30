"""Inspectable barcode abundance, direct-distance and saved-tree calculations.

There is no combined confidence, significance, ancestry, molecule estimate or
native invocation. Parameters select explicit count and retained-tree operands.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import math

from .barcode_contracts import (
    BARCODE_FIELDS, CLUSTER_FIELDS, DISTANCE_FIELDS, SUMMARY_FIELDS, TARGET_NUMERIC_FIELDS,
    BarcodeCalculationParametersV1, BarcodeComponentsV1, BarcodeLinkageV1, BarcodePartitionV1,
    BarcodeSheetV1, digest, finite, issue, require, validate_linkage, validate_parameters, validate_sheet,
)


def recut_barcode_linkage(linkage: BarcodeLinkageV1, *, threshold: float) -> BarcodePartitionV1:
    """Cut the saved complete average-linkage tree at <= threshold.

    IDs are deterministic categories in increasing minimum-leaf order. The cut
    uses cophenetic heights, not a maximum original-pair mismatch constraint.
    """
    linkage = validate_linkage(linkage)
    require(finite(threshold, 0), 'invalid_linkage_membership')
    n = len(linkage['barcode_keys'])
    members = {i: [i] for i in range(n)}
    accepted = {i: [i] for i in range(n)}
    for row in linkage['merges']:
        left, right, new = row['left_node'], row['right_node'], n + row['merge_index']
        members[new] = members[left] + members[right]
        if row['distance'] <= threshold:
            accepted.pop(left)
            accepted.pop(right)
            accepted[new] = members[new]
    ids = {}
    for cluster_id, group in enumerate(sorted(accepted.values(), key=min), 1):
        for leaf in group:
            ids[leaf] = cluster_id
    return {'version': 'barcode_partition_v1', 'barcode_keys': deepcopy(linkage['barcode_keys']),
        'threshold': threshold, 'criterion': 'cophenetic_distance',
        'memberships': [{'barcode_sequence': key, 'cluster_id': ids[i]}
            for i, key in enumerate(linkage['barcode_keys'])]}


def _cell(value, *, units, population, extent, denominator=None, state=None, source='derived'):
    if state is None:
        state = 'partial_population' if extent == 'prefix' else 'available'
    return {'value': value, 'state': state, 'units': units, 'denominator': denominator,
            'population': population, 'extent': extent, 'source': source, 'uncertainty': None}


def _ratio(numerator, denominator, *, population, extent, applicable=True):
    if not applicable:
        state, value = 'not_applicable', None
    elif numerator is None or denominator is None:
        state, value = 'missing_input', None
    elif denominator == 0:
        state, value = 'zero_denominator', None
    else:
        state, value = None, numerator / denominator
    return _cell(value, units='fraction', population=population, extent=extent,
                 denominator=denominator, state=state)


def calculate_barcode_components(sheet: BarcodeSheetV1, *,
                                 parameters: BarcodeCalculationParametersV1) -> BarcodeComponentsV1:
    sheet = validate_sheet(sheet)
    parameters = validate_parameters(parameters)
    sample_key = sheet['sample']['sample_key']
    population = sheet['population']
    extent = population['extent'] if population else 'unknown'
    issues = deepcopy(sheet['issues'])
    result = {'version': 'barcode_components_v1', 'status': sheet['status'], 'sheet_sha256': digest(sheet),
        'parameters': parameters, 'sample_key': sample_key, 'extent': extent, 'summary': {},
        'barcodes': [], 'distances': [], 'clusters': [], 'targets': [], 'issues': issues}
    summary = result['summary']
    if population is None:
        for name in SUMMARY_FIELDS:
            units = 'fraction' if 'fraction' in name else 'positions' if 'distance' in name else 'reads'
            summary[name] = _cell(None, units=units, population='none', extent=extent, state='missing_input')
        return result

    counts = {row['barcode_sequence']: row['read_count'] for row in sheet['counts']}
    retained = [key for key in population['barcode_order'] if counts[key] >= parameters['min_count']]
    total, extracted = population['total_parsed_records'], population['extracted_records']
    retained_reads = sum(counts[key] for key in retained)
    values = {
        'total_records': (total, 'reads', 'parsed_reads'),
        'extracted_records': (extracted, 'reads', 'parsed_reads'),
        'unmatched_records': (population['unmatched_records'], 'reads', 'parsed_reads'),
        'empty_match_records': (population['empty_match_records'], 'reads', 'parsed_reads'),
        'distinct_barcode_count': (len(counts), 'barcode_types', 'extracted_reads'),
        'retained_barcode_count': (len(retained), 'barcode_types', 'barcode_types'),
        'retained_read_count': (retained_reads, 'reads', 'extracted_reads'),
        'discarded_read_count': (extracted - retained_reads, 'reads', 'extracted_reads'),
    }
    for name, (value, units, pop) in values.items():
        summary[name] = _cell(value, units=units, population=pop, extent=extent,
            source='observed' if name in ('total_records', 'extracted_records', 'unmatched_records', 'empty_match_records') else 'derived')
    summary['extraction_fraction'] = _ratio(extracted, total, population='parsed_reads', extent=extent)
    summary['retained_fraction_extracted'] = _ratio(retained_reads, extracted, population='extracted_reads', extent=extent)
    summary['retained_fraction_all_reads'] = _ratio(retained_reads, total, population='parsed_reads', extent=extent)
    for key in population['barcode_order']:
        count = counts[key]
        cells = {
            'barcode_read_count': _cell(count, units='reads', population='extracted_reads', extent=extent, source='observed'),
            'barcode_length': _cell(len(key), units='positions', population='indexed_positions', extent=extent, source='observed'),
            'fraction_all_reads': _ratio(count, total, population='parsed_reads', extent=extent),
            'fraction_extracted_reads': _ratio(count, extracted, population='extracted_reads', extent=extent),
            'fraction_retained_reads': _ratio(count, retained_reads, population='retained_reads', extent=extent,
                                              applicable=key in retained),
        }
        result['barcodes'].append({'sample_key': sample_key, 'barcode_sequence': key,
                                  'retained': key in retained, 'measurements': cells})

    requested_keys = parameters['cluster_population']
    matching_population = (requested_keys == retained == population['distance_population'])
    n = len(requested_keys)
    pair_count = n * (n - 1) // 2
    have_distances = matching_population and len(sheet['distances']) == pair_count
    all_available = have_distances and all(row['state'] == 'available' for row in sheet['distances'])
    if not matching_population:
        issues.append(issue('missing_distance_population', 'distance', sample_key=sample_key,
            field='cluster_population', requirement='native_distance_population'))
    elif pair_count and not have_distances:
        issues.append(issue('missing_distance_population', 'distance', sample_key=sample_key,
            field='distances', requirement='native_distance_population'))
    summary['pair_count'] = _cell(pair_count, units='pairs', population='distance_pairs', extent=extent)
    if have_distances:
        for row in sheet['distances']:
            valid = row['state'] == 'available'
            cells = {name: _cell(row[name], units='positions', population='indexed_positions', extent=extent,
                                source='observed', state=None if name != 'distance_count' or valid else 'invalid')
                for name in DISTANCE_FIELDS[:-1]}
            cells['distance_fraction'] = _ratio(row['distance_count'], max(len(row['barcode_i']), len(row['barcode_j'])),
                population='indexed_positions', extent=extent)
            if not valid:
                cells['distance_fraction']['state'] = 'invalid'
            result['distances'].append({'sample_key': sample_key, 'i': row['i'], 'j': row['j'],
                'barcode_i': row['barcode_i'], 'barcode_j': row['barcode_j'], 'measurements': cells})
    distance_state = 'not_applicable' if pair_count == 0 and matching_population else (
        None if all_available else 'invalid' if have_distances else 'missing_input')
    distance_values = [row['distance_count'] for row in sheet['distances']] if all_available else []
    for name, value in (
        ('mean_pair_distance', math.fsum(distance_values) / pair_count if distance_values else None),
        ('max_pair_distance', max(distance_values) if distance_values else None),
    ):
        summary[name] = _cell(value, units='positions', population='distance_pairs', extent=extent,
                             denominator=pair_count, state=distance_state)

    can_cluster = matching_population and n >= 2 and all_available and sheet['linkage'] is not None
    if can_cluster:
        partition = recut_barcode_linkage(sheet['linkage'], threshold=parameters['cut_threshold'])
        groups = defaultdict(list)
        for row in partition['memberships']:
            groups[row['cluster_id']].append(row['barcode_sequence'])
        for cluster_id, members in groups.items():
            reads = sum(counts[key] for key in members)
            cells = {
                'cluster_barcode_count': _cell(len(members), units='barcode_types', population='retained_reads', extent=extent),
                'cluster_read_count': _cell(reads, units='reads', population='retained_reads', extent=extent),
                'cluster_fraction_all_reads': _ratio(reads, total, population='parsed_reads', extent=extent),
                'cluster_fraction_retained_reads': _ratio(reads, retained_reads, population='retained_reads', extent=extent),
            }
            result['clusters'].append({'sample_key': sample_key, 'cluster_id': cluster_id,
                                      'barcode_keys': members, 'measurements': cells})
        cluster_values = (len(groups), max(len(v) for v in groups.values()),
                          max(sum(counts[key] for key in v) for v in groups.values()))
        cluster_state = None
    else:
        cluster_values = (None, None, None)
        cluster_state = 'not_applicable' if matching_population and n < 2 else 'missing_input'
        code = 'not_enough_barcodes' if matching_population and n < 2 else 'missing_distance_population'
        new_issue = issue(code, 'cluster', sample_key=sample_key, field='linkage',
                          requirement='none' if n < 2 and matching_population else 'native_linkage')
        if new_issue not in issues:
            issues.append(new_issue)
    for name, value, units in zip(('cluster_count', 'largest_cluster_barcode_count', 'largest_cluster_read_count'),
                                  cluster_values, ('clusters', 'barcode_types', 'reads')):
        summary[name] = _cell(value, units=units, population='cluster_types', extent=extent, state=cluster_state)

    mapping_available = bool(sheet['target_rows']) or (sheet['request']['barcode_target_file'] is not None
        and any(row['role'] == 'target_map' and row['file'] == sheet['request']['barcode_target_file']
                for row in sheet['sources']))
    mapping_invalid = any((row['code'] in ('invalid_target_map', 'sample_binding_mismatch')
        and row['stage'] == 'join') or (row['code'] == 'missing_artifact'
        and row['field'] in ('target_rows', 'barcode_target_file')) for row in issues)
    if parameters['target_aggregation'] == 'none':
        target_state, target_counts = 'not_applicable', (None, None, None)
    elif not mapping_available or mapping_invalid:
        target_state, target_counts = 'missing_input', (None, None, None)
        issues.append(issue('target_mapping_not_supplied', 'join', sample_key=sample_key,
                            field='target_rows', requirement='target_mapping'))
    else:
        targets_by_barcode = defaultdict(set)
        for row in sheet['target_rows']:
            targets_by_barcode[row['barcode_sequence']].add((row['target_kind'], row['target_key'], row['target_reference_release']))
        target_groups = defaultdict(list)
        unique = ambiguous = unmapped = 0
        for key, count in counts.items():
            targets = targets_by_barcode[key]
            if len(targets) == 1:
                unique += count
                target_groups[next(iter(targets))].append(key)
            elif len(targets) > 1:
                ambiguous += count
            else:
                unmapped += count
        for (kind, key, release), members in sorted(target_groups.items(), key=lambda item: (item[0][0], item[0][1], item[0][2] or '')):
            count = sum(counts[barcode] for barcode in members)
            cells = {
                'uniquely_assigned_target_read_count': _cell(count, units='reads', population='extracted_reads', extent=extent),
                'fraction_all_reads': _ratio(count, total, population='parsed_reads', extent=extent),
                'fraction_extracted_reads': _ratio(count, extracted, population='extracted_reads', extent=extent),
            }
            result['targets'].append({'sample_key': sample_key, 'target_kind': kind, 'target_key': key,
                'target_reference_release': release, 'barcode_keys': members, 'measurements': cells})
        target_state, target_counts = None, (unique, ambiguous, unmapped)
    for name, value in zip(('uniquely_assigned_target_read_count', 'ambiguous_target_read_count', 'unmapped_target_read_count'), target_counts):
        summary[name] = _cell(value, units='reads', population='extracted_reads', extent=extent, state=target_state)

    # Stable field order is presentation convenience; numerical meaning is keyed.
    result['summary'] = {field: summary[field] for field in SUMMARY_FIELDS}
    if result['status'] == 'ok' and any(row['code'] != 'not_enough_barcodes' for row in issues):
        result['status'] = 'partial'
    return result
