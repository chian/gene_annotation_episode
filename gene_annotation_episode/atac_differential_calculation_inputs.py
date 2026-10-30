"""Pure handoff from the retained ATAC sheet to the interval calculators.

Bindings, reference bounds and depth sources are checked independently. Native
tables stay unchanged; only the calculation projection canonicalizes explicit
aliases or replaces an out-of-reference operand with null. Supplied external
tables remain lazy. The caller must exhaust every port before sealing results,
including after another port fails, and retain earlier results as partial.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import math

from .atac_differential_contracts import (
    AtacIssue, AtacNativeSheet, AtacTableReadError, BedGraphRow, MAX_COORDINATE, PeakLink,
    atac_track_extent, issue, track_row_key, valid_track_geometry,
    validate_atac_callpeak_binding, validate_atac_comparison_binding,
    validate_atac_condition, validate_atac_depth_selection, validate_atac_locator,
    validate_atac_parsed_table, validate_atac_reference, validate_atac_sample,
    validate_bedgraph_row,
)
from .atac_differential_sheet import select_atac_depth_counts


_ROLES = ('signal1', 'background1', 'signal2', 'background2')


def _unique(records, key, code):
    result = {}
    for record in records:
        value = record[key]
        if value in result:
            raise ValueError(code)
        result[value] = record
    return result


def _validate_issues(items):
    if type(items) is not list:
        raise ValueError('invalid_atac_issues')
    for item in items:
        if (not isinstance(item, dict) or set(item) != set(AtacIssue.__annotations__)
                or any(type(item[k]) is not str or not item[k]
                       for k in ('code', 'binding_key', 'requirement'))
                or any(item[k] is not None and (type(item[k]) is not str or not item[k])
                       for k in ('artifact_ref', 'field'))
                or type(item['row_ordinals']) is not list
                or any(type(n) is not int or n < 0 for n in item['row_ordinals'])
                or type(item['locations']) is not list):
            raise ValueError('invalid_atac_issue')
        for locator in item['locations']:
            validate_atac_locator(locator)


def _validate_parameters(parameters):
    for field, minimum, inclusive in (('cutoff_log10_lr', 0, True),
                                       ('native_pseudocount', 0, False),
                                       ('minimum_length_bp', 0, False)):
        value = parameters[field]
        if value is not None:
            try:
                valid = math.isfinite(value) and (value >= minimum if inclusive else value > minimum)
            except OverflowError:
                valid = False
            if not valid:
                raise ValueError('invalid_atac_comparison_' + field)
    minimum, gap = parameters['minimum_length_bp'], parameters['maximum_gap_bp']
    if minimum is not None and gap is not None and gap >= minimum:
        raise ValueError('invalid_atac_comparison_maximum_gap_bp')
    for field in ('depth1_lexeme', 'depth2_lexeme'):
        if parameters[field] is not None:
            try:
                value = Decimal(parameters[field])
            except InvalidOperation as error:
                raise ValueError('invalid_atac_comparison_' + field) from error
            if not value.is_finite() or value < 0:
                raise ValueError('invalid_atac_comparison_' + field)


def _validate_sheet(sheet):
    fields = set(AtacNativeSheet.__annotations__) | {'bam_references'}
    if (not isinstance(sheet, dict) or set(sheet) not in (fields, fields - {'bam_references'})
            or sheet['version'] != 'atac_differential_native_sheet_v1'
            or sheet['tool_row'] != 'B-L125-analyze_atac_seq_differential_accessibility'):
        raise ValueError('invalid_atac_native_sheet')
    validate_atac_reference(sheet['reference'])
    validate_atac_comparison_binding(sheet['comparison'])
    _validate_parameters(sheet['comparison']['selected_parameters'])
    if sheet['comparison']['condition1_id'] == sheet['comparison']['condition2_id']:
        raise ValueError('duplicate_atac_comparison_condition_id')
    for field, allowed in (
        ('reference_relation', ('same_supplied_reference', 'conflicting', 'unknown')),
        ('normalization_compatibility', ('raw_compatible', 'incompatible', 'unknown')),
        ('coverage_completeness', ('complete_declared_domain', 'partial_declared_domain', 'unknown')),
        ('data_status', ('complete_reported_data', 'partial_reported_data', 'unavailable')),
    ):
        if type(sheet[field]) is not str or sheet[field] not in allowed:
            raise ValueError('invalid_atac_' + field)
    if type(sheet['peak_links']) is not list:
        raise ValueError('invalid_atac_peak_links')
    for link in sheet['peak_links']:
        if (not isinstance(link, dict) or set(link) != set(PeakLink.__annotations__)
                or any(type(link[k]) is not str or not link[k] for k in ('callpeak_run_key', 'name'))
                or link['status'] not in ('matched', 'missing_representation', 'ambiguous', 'conflicting')
                or any(type(link[k]) is not list or any(type(n) is not int or n < 0 for n in link[k])
                       for k in ('xls_row_ordinals', 'narrowpeak_row_ordinals', 'summit_row_ordinals'))):
            raise ValueError('invalid_atac_peak_link')
    validate_atac_depth_selection(sheet['depth_selection'])
    _validate_issues(sheet['issues'])
    _validate_issues(sheet['depth_selection']['issues'])
    for field, validator in (('samples', validate_atac_sample),
                              ('conditions', validate_atac_condition),
                              ('callpeak_bindings', validate_atac_callpeak_binding)):
        if type(sheet[field]) is not list:
            raise ValueError('invalid_atac_' + field)
        for record in sheet[field]:
            validator(record)
    if len(sheet['conditions']) != 2:
        raise ValueError('two_atac_conditions_required')
    for field, version in (('tracks', 'atac_bedgraph_parsed_v1'),
                            ('peaks_xls', 'macs2_peaks_xls_parsed_v1'),
                            ('narrowpeaks', 'macs2_narrowpeak_parsed_v1'),
                            ('summits', 'macs2_summits_parsed_v1'),
                            ('native_differential', 'macs2_bdgdiff_parsed_v1')):
        if type(sheet[field]) is not list:
            raise ValueError('invalid_atac_' + field)
        for table in sheet[field]:
            validate_atac_parsed_table(table, version=version)
            _validate_issues(table['issues'])
    bam_references = sheet.get('bam_references', [])
    if type(bam_references) is not list:
        raise ValueError('invalid_atac_bam_references')
    for table in bam_references:
        validate_atac_parsed_table(table, version='atac_bam_reference_parsed_v1')
        _validate_issues(table['issues'])
    samples = _unique(sheet['samples'], 'sample_id', 'duplicate_atac_sample_id')
    conditions = _unique(sheet['conditions'], 'condition_id', 'duplicate_atac_condition_id')
    runs = _unique(sheet['callpeak_bindings'], 'run_key', 'duplicate_atac_callpeak_run_key')
    tracks = _unique(sheet['tracks'], 'binding_key', 'duplicate_atac_track_key')
    _unique([t['binding'] for t in sheet['tracks']], 'track_key', 'duplicate_atac_track_key')
    selected_keys = list(sheet['comparison']['track_keys'].values())
    if len(set(selected_keys)) != 4:
        raise ValueError('duplicate_atac_comparison_track_key')
    if set(tracks) != set(selected_keys):
        raise ValueError('atac_exact_selected_track_records_required')
    for condition in conditions.values():
        if len(set(condition['sample_ids'])) != len(condition['sample_ids']):
            raise ValueError('duplicate_atac_condition_sample_id')
    return samples, conditions, runs, tracks


def _population(reference, comparison, intervals, add):
    if not isinstance(intervals, Sequence) or isinstance(intervals, (str, bytes)):
        raise ValueError('atac_population_sequence_required')
    contigs, aliases = {}, {}
    usable = True
    for contig in reference['contigs']:
        token = contig['chromosome']
        if token in contigs:
            usable = False
            add('reference_conflict', 'contigs', requirement='explicit_reference_mapping')
        contigs[token] = contig
    for alias in reference['aliases']:
        source, target = alias['source_chromosome'], alias['target_chromosome']
        if (source in aliases or alias['reference_id'] != reference['reference_id']
                or target not in contigs or source in contigs and source != target):
            usable = False
            add('reference_conflict', 'aliases', requirement='explicit_reference_mapping')
        aliases[source] = target
    dictionary_usable = usable
    if comparison['reference_id'] != reference['reference_id']:
        usable = False
        add('reference_conflict', 'comparison.reference_id', requirement='explicit_reference_mapping')
    previous, selected = None, []
    for ordinal, interval in enumerate(intervals):
        if not isinstance(interval, dict) or set(interval) != {'chromosome', 'start', 'end'}:
            raise ValueError('atac_population_interval_required')
        chromosome, start, end = (interval[k] for k in ('chromosome', 'start', 'end'))
        if (type(chromosome) is not str or not chromosome or type(start) is not int
                or type(end) is not int or not 0 <= start < end <= MAX_COORDINATE):
            raise ValueError('atac_valid_interval_geometry_required')
        try:
            key = chromosome.encode('utf-8')
        except UnicodeEncodeError as error:
            raise ValueError('atac_utf8_chromosome_required') from error
        if previous is not None and (key < previous[0] or key == previous[0] and start < previous[1]):
            raise ValueError('atac_populations_out_of_order_or_overlapping')
        previous = key, end
        contig = contigs.get(chromosome)
        code = ('unknown_chromosome' if contig is None else 'metadata_missing'
                if contig['length_bp'] is None else 'coordinate_outside_reference'
                if end > contig['length_bp'] else None)
        if code:
            usable = False
            add(code, 'intervals', row_ordinals=(ordinal,), requirement='explicit_reference_mapping')
        selected.append(dict(interval))
    return selected if usable else [], contigs, aliases, usable, dictionary_usable


def _condition_valid(condition_id, samples, conditions, reference_id):
    condition = conditions.get(condition_id)
    return (condition is not None and bool(condition['sample_ids'])
            and all(sid in samples and samples[sid]['reference_id'] == reference_id
                    for sid in condition['sample_ids']))


def _run_valid(run, samples, conditions, reference_id):
    condition = conditions.get(run['condition_id'])
    if (not _condition_valid(run['condition_id'], samples, conditions, reference_id)
            or run['reference_id'] != reference_id or run['sample_ids'] != condition['sample_ids']):
        return False
    expected = [ref for sid in run['sample_ids'] for ref in samples[sid]['input_artifact_refs']]
    return bool(expected) and Counter(expected) == Counter(run['treatment_input_refs'])


def _mode_supported(run):
    p = run['selected_parameters']
    return (run['selected_format'] == 'BAM' and run['paired_end'] is False
            and p['nomodel'] is True and p['broad'] is False and p['downsample'] is False
            and p['spmr'] is False and p['store_bedgraph'] is True
            and run['supplied_control_sample_ids'] == [] and run['supplied_control_input_refs'] == [])


def _identity_mismatch(table):
    artifact = table['artifact']
    return (table['state']['identity'] == 'mismatch'
            or artifact['expected_sha256'] is not None and artifact['expected_sha256'] != table['parsed_sha256']
            or artifact['expected_size_bytes'] is not None and artifact['expected_size_bytes'] != table['parsed_byte_count'])


def _native_reference_runs(sheet, runs, selected, contigs, aliases, add):
    """Check actual saved @SQ rows for each selected native input occurrence.

    Names/lengths establish dictionary compatibility under the supplied reference
    assignment. Absent M5 stays unknown. Present M5 values can establish a
    contradiction across inputs; they are never compared with reference SHA256.
    """
    needed = {t['binding']['callpeak_run_key'] for t in sheet['tracks']
              if t['binding']['callpeak_run_key'] is not None}
    selected_chromosomes = {p['chromosome'] for p in selected}
    by_occurrence = {}
    for report in sheet.get('bam_references', []):
        by_occurrence.setdefault((report['callpeak_run_key'], report['input_ordinal']), []).append(report)
    valid, digests = {}, {}
    for run_key in sorted(needed):
        run = runs.get(run_key)
        valid[run_key] = run is not None and bool(run['treatment_input_refs'])

        def reject(code, field, report=None, row=None, requirement='explicit_reference_mapping'):
            valid[run_key] = False
            add(code, field, binding_key=run_key, artifact_ref=report['artifact']['artifact_ref'] if report else None,
                row_ordinals=() if row is None else (row['row_ordinal'],),
                locations=() if row is None else (row['locator'],), requirement=requirement)

        if run is None:
            reject('condition_binding_conflict', 'bam_reference_run', requirement='condition_mapping')
            continue
        for ordinal, input_ref in enumerate(run['treatment_input_refs']):
            reports = by_occurrence.get((run_key, ordinal), [])
            if len(reports) != 1:
                reject('metadata_missing' if not reports else 'metadata_conflict', 'bam_reference_occurrence')
                continue
            report = reports[0]
            if (report['input_artifact_ref'] != input_ref
                    or report['binding_key'] != f'{run_key}:input:{ordinal}'):
                reject('condition_binding_conflict', 'bam_input_artifact_ref', report,
                       requirement='matching_artifact')
                continue
            state = report['state']
            if report['artifact']['format'] != 'sam_header_text' or state['format'] == 'unsupported':
                reject('unsupported_format', 'bam_reference_format', report, requirement='compatible_native_mode')
                continue
            if _identity_mismatch(report):
                reject('identity_mismatch', 'bam_reference_artifact', report, requirement='matching_artifact')
                continue
            if state['availability'] != 'present':
                reject('artifact_missing', 'bam_reference_artifact', report, requirement='complete_artifact')
                continue
            if state['identity'] != 'verified':
                reject('identity_unverified', 'bam_reference_artifact', report, requirement='matching_artifact')
                continue
            if (state['byte_extent'] != 'complete' or report['artifact']['supplied_extent'] != 'complete'
                    or report['data_row_count'] is None
                    or report['artifact']['producer_outcome'] == 'failed'):
                reject('incomplete_bam_reference_dictionary', 'bam_reference_artifact', report,
                       requirement='complete_artifact')
                continue
            unlocated = any(record['fields'] is None or not record['fields']
                            or record['fields'][0].startswith('@SQ')
                            or not record['fields'][0].startswith(('@', '#'))
                            for record in report['invalid_records'])
            if unlocated or any(row['chromosome'] is None for row in report['rows']):
                reject('unlocated_bam_reference_row', 'bam_reference_chromosome', report)
                continue
            actual = {}
            for row in report['rows']:
                token = row['chromosome']
                canonical = aliases.get(token, token)
                actual.setdefault(canonical, []).append(row)
            for chromosome in sorted(selected_chromosomes, key=lambda name: name.encode('utf-8')):
                matches = actual.get(chromosome, [])
                if len(matches) != 1:
                    reject('unknown_chromosome' if not matches else 'reference_conflict',
                           'bam_reference_chromosome', report)
                    continue
                row = matches[0]
                if any(row['row_ordinal'] in item['row_ordinals']
                       and item['field'] in ('SN', 'LN', 'M5', 'chromosome', 'length_bp', 'sequence_md5')
                       for item in report['issues']):
                    reject('reference_conflict', 'bam_reference_fields', report, row)
                    continue
                if row['length_bp'] != contigs[chromosome]['length_bp']:
                    reject('reference_conflict', 'bam_reference_length_bp', report, row)
                    continue
                if row['sequence_md5'] is None:
                    if any(token.startswith('M5:') for token in row['original_fields']):
                        reject('reference_conflict', 'sequence_md5', report, row)
                        continue
                    add('sequence_identity_unknown', 'sequence_md5', binding_key=run_key,
                        artifact_ref=report['artifact']['artifact_ref'], row_ordinals=(row['row_ordinal'],),
                        locations=(row['locator'],))
                else:
                    digests.setdefault(chromosome, []).append((run_key, report, row))
        # An extra observation for this run with an unselected input position is
        # a contradictory association, not a second input inferred by the bridge.
        for (observed_run, ordinal), reports in by_occurrence.items():
            if observed_run == run_key and ordinal >= len(run['treatment_input_refs']):
                for report in reports:
                    reject('condition_binding_conflict', 'bam_input_ordinal', report,
                           requirement='condition_mapping')
    for observations in digests.values():
        if len({row['sequence_md5'].lower() for _, _, row in observations}) > 1:
            for run_key, report, row in observations:
                valid[run_key] = False
                add('reference_conflict', 'sequence_md5', binding_key=run_key,
                    artifact_ref=report['artifact']['artifact_ref'], row_ordinals=(row['row_ordinal'],),
                    locations=(row['locator'],), requirement='explicit_reference_mapping')
    return valid


def _track_usable(track, role, sheet, samples, conditions, runs, dictionary_usable, add):
    binding, artifact = track['binding'], track['artifact']
    comparison, reference_id = sheet['comparison'], sheet['reference']['reference_id']
    expected_condition = comparison['condition1_id' if role.endswith('1') else 'condition2_id']
    signal = role.startswith('signal')
    native = binding['callpeak_run_key'] is not None
    valid = True

    def reject(code, field, requirement='condition_mapping'):
        nonlocal valid
        valid = False
        add(code, field, track=track, requirement=requirement)

    if (binding['track_key'] != comparison['track_keys'][role]
            or binding['condition_id'] != expected_condition
            or binding['role'] != ('signal' if signal else 'model_background')
            or not _condition_valid(expected_condition, samples, conditions, reference_id)
            or binding['sample_ids'] != conditions.get(expected_condition, {}).get('sample_ids')):
        reject('condition_binding_conflict', 'track_binding')
    if (not dictionary_usable or binding['reference_id'] != reference_id
            or comparison['reference_id'] != reference_id):
        reject('reference_conflict', 'reference_id', 'explicit_reference_mapping')
    if binding['source_artifact_ref'] != artifact['artifact_ref']:
        reject('metadata_conflict', 'source_artifact_ref', 'matching_artifact')
    if artifact['format'] != 'bedgraph4' or track['state']['format'] == 'unsupported':
        reject('unsupported_format', 'format', 'compatible_native_mode')
    if _identity_mismatch(track):
        reject('identity_mismatch', 'artifact', 'matching_artifact')
    elif track['state']['identity'] == 'unverified':
        add('identity_unverified', 'artifact', track=track, requirement='matching_artifact')
    if binding['normalization'] != 'raw_pileup':
        reject('unsupported_normalization', 'normalization', 'compatible_native_mode')
    expected_unit = (('extended_tag_pileup' if signal else 'model_expected_extended_tag_pileup')
                     if native else ('supplied_signal' if signal else 'supplied_model_background'))
    if binding['value_unit'] != expected_unit:
        reject('unsupported_normalization', 'value_unit', 'compatible_native_mode')
    expected_background = 'unknown' if signal else 'self_model' if native else 'explicit_supplied_track'
    if binding['background_origin'] != expected_background:
        reject('condition_binding_conflict', 'background_origin')
    if native:
        run = runs.get(binding['callpeak_run_key'])
        if (run is None or not _run_valid(run, samples, conditions, reference_id)
                or run['condition_id'] != binding['condition_id'] or run['sample_ids'] != binding['sample_ids']
                or run['artifact_roles']['signal_track' if signal else 'background_track'] != artifact['artifact_ref']
                or run['producer_ref'] != artifact['producer_run_ref']):
            reject('condition_binding_conflict', 'callpeak_run_key')
        if run is not None and not _mode_supported(run):
            reject('unsupported_mode', 'callpeak_mode', 'compatible_native_mode')
        if artifact['producer_name'] != 'MACS2' or artifact['producer_version'] != '2.2.9.1':
            reject('unsupported_mode', 'producer_version', 'compatible_native_mode')
    elif artifact['producer_run_ref'] is not None:
        reject('condition_binding_conflict', 'callpeak_run_key')
    if isinstance(track['rows'], dict) and track['rows']['source_artifact_ref'] != artifact['artifact_ref']:
        reject('metadata_conflict', 'source_artifact_ref', 'matching_artifact')
    return valid


def _depth_operands(sheet, samples, conditions, runs, add):
    selection, comparison = sheet['depth_selection'], sheet['comparison']
    desired = [comparison['condition1_id'], comparison['condition2_id']]
    reference_id = sheet['reference']['reference_id']
    depths = selection['conditions']
    bound = (comparison['reference_id'] == reference_id and desired[0] != desired[1]
             and [d['condition_id'] for d in depths] == desired)
    for depth in depths:
        condition = conditions.get(depth['condition_id'])
        if (not _condition_valid(depth['condition_id'], samples, conditions, reference_id)
                or depth['sample_ids'] != condition['sample_ids']):
            bound = False
    if selection['kind'] == 'native_postfilter_counts':
        actual = select_atac_depth_counts(sheet['peaks_xls'], conditions=tuple(desired),
                                          callpeak_bindings=sheet['callpeak_bindings'])
        # Summary booleans and copied issue lists cannot authenticate operands.
        if actual['conditions'] != depths:
            bound = False
        for depth in depths:
            run = runs.get(depth['callpeak_run_key'])
            if run is None or not _run_valid(run, samples, conditions, reference_id):
                bound = False
            for locator in depth['source_locations']:
                validate_atac_locator(locator)
        if not bound:
            add('depth_population_conflict', 'native_count_selection', requirement='matching_count_population')
            return None, None, 'tags', False
        values = []
        for depth in depths:
            reports = [r for r in sheet['peaks_xls'] if r['callpeak_run_key'] == depth['callpeak_run_key']]
            usable = depth['state'] in ('observed', 'zero')
            if usable:
                report = reports[0] if len(reports) == 1 else None
                usable = (report is not None and report['state']['availability'] == 'present'
                          and report['artifact']['format'] == 'macs2_peaks_xls_narrow'
                          and report['state']['format'] != 'unsupported' and not _identity_mismatch(report)
                          and bool(depth['source_locations']))
            values.append(depth['count'] if usable else None)
        available = all(value is not None for value in values)
        if not available:
            add('metadata_missing', 'native_depth', requirement='original_native_metadata')
        return *values, 'tags', available
    unit = depths[0]['unit'] if depths[0]['unit'] == depths[1]['unit'] else None
    if depths[0]['population'] != depths[1]['population'] or unit is None:
        bound = False
    for depth in depths:
        if depth['state'] == 'declared' and depth['value_lexeme'] is not None:
            try:
                lexical = Decimal(depth['value_lexeme'])
                matches = lexical.is_finite() and float(lexical) == depth['value']
            except (InvalidOperation, OverflowError, ValueError):
                matches = False
            if not matches:
                bound = False
    if not bound:
        add('depth_population_conflict', 'declared_depth_population', requirement='matching_count_population')
        return None, None, unit, False
    values = [depth['value'] if depth['state'] == 'declared' else None for depth in depths]
    available = all(value is not None for value in values)
    if not available:
        add('metadata_missing', 'declared_depth', requirement='matching_count_population')
    return *values, unit, available


def _memory_rows(track, aliases):
    rows, index = track['rows'], track['ordered_row_index']
    if track['state']['availability'] == 'missing' and not rows and index is None:
        return iter(())
    by_ordinal = {row[0]: row for row in rows}
    expected = {row[0] for row in rows if valid_track_geometry(row)}
    if (type(index) is not list or any(type(n) is not int for n in index)
            or len(index) != len(expected) or set(index) != expected):
        raise ValueError('invalid_atac_ordered_row_index')
    previous = None
    for ordinal in index:
        key = track_row_key(by_ordinal[ordinal])
        if previous is not None and key <= previous:
            raise ValueError('invalid_atac_ordered_row_index')
        previous = key
    unlocated = len(track['invalid_records']) + sum(not valid_track_geometry(row) for row in rows)
    if track['unlocated_invalid_row_count'] != unlocated:
        raise ValueError('invalid_atac_unlocated_row_count')
    # Only a derived index is reordered. The native rows/ordinals are unchanged.
    projected_index = sorted(index, key=lambda n: (
        aliases.get(by_ordinal[n][4], by_ordinal[n][4]).encode('utf-8'),
        by_ordinal[n][5], by_ordinal[n][6], n))
    return (by_ordinal[n] for n in projected_index)


def _project_rows(track, source, *, usable, external, contigs, aliases, port, eligibility, role, add):
    previous, count, unlocated = None, 0, 0
    try:
        for raw in source:
            validate_bedgraph_row(raw)
            count += 1
            if not valid_track_geometry(raw):
                unlocated += 1
                continue
            chromosome = aliases.get(raw[4], raw[4])
            row = (*raw[:4], chromosome, *raw[5:])
            key = track_row_key(row)
            if previous is not None and key <= previous:
                raise AtacTableReadError(issue('atac_projected_track_order_required',
                    track['artifact']['artifact_ref'], track['binding_key'], row_ordinals=(raw[0],),
                    locations=(dict(line_number=raw[1], byte_start=raw[2], byte_end=raw[3]),),
                    field='chromosome_start_end_source_ordinal', requirement='unambiguous_track_values'), count, raw[3])
            previous = key
            contig = contigs.get(chromosome)
            code = ('unknown_chromosome' if contig is None else 'metadata_missing'
                    if contig['length_bp'] is None else 'coordinate_outside_reference'
                    if raw[6] > contig['length_bp'] else None)
            if code:
                add(code, 'chromosome' if contig is None else 'reference_length_bp', track=track,
                    row_ordinals=(raw[0],), locations=(dict(line_number=raw[1], byte_start=raw[2], byte_end=raw[3]),),
                    requirement='explicit_reference_mapping')
                row = (*row[:7], None, row[8])
            if usable:
                yield row
        if external:
            if count != track['rows']['row_count']:
                raise ValueError('track_table_row_count_mismatch')
            if unlocated + len(track['invalid_records']) != track['unlocated_invalid_row_count']:
                raise ValueError('invalid_atac_unlocated_row_count')
    except (AtacTableReadError, OSError, ValueError, TypeError) as error:
        if isinstance(error, AtacTableReadError):
            failure = error
        else:
            code = 'stream_read_failed' if isinstance(error, OSError) else str(error) if isinstance(error, ValueError) else 'invalid_atac_track_table_row'
            failure = AtacTableReadError(issue(code, track['artifact']['artifact_ref'], track['binding_key'],
                                              requirement='matching_artifact'), count, 0)
        add(failure.issue['code'], failure.issue['field'], track=track,
            row_ordinals=failure.issue['row_ordinals'], locations=failure.issue['locations'],
            requirement=failure.issue['requirement'], artifact_ref=failure.issue['artifact_ref'])
        eligibility[role] = 'unavailable'
        if port['extent'] not in ('failed', 'missing'):
            port['extent'] = 'partial'
        if failure is error:
            raise
        raise failure from error


def prepare_atac_calculation_inputs(sheet: AtacNativeSheet, *, intervals: Sequence[dict],
                                    ordered_track_rows: Mapping[str, Iterable[BedGraphRow]] | None = None) -> dict:
    """Validate selected operands and return lazy contract005 calculation ports.

    ``intervals`` is the exact canonical, ordered comparison population. Empty
    means empty. ``ordered_track_rows`` must supply every present retained table
    and cannot override in-memory rows. It is the caller's authenticated table
    iterator, ordinarily ``iter_atac_track_table_rows``; no path is opened here.

    Qualifications are final only after all ports have been exhausted. A failed
    port propagates its error and updates its extent/eligibility; it never drains
    another port. The result worker owns finalization of all other streams.
    """
    samples, conditions, runs, track_map = _validate_sheet(sheet)
    issues = deepcopy(sheet['issues'])
    comparison = sheet['comparison']

    def add(code, field, *, track=None, requirement='none', row_ordinals=(), locations=(), artifact_ref=None,
            binding_key=None):
        issues.append(issue(code, artifact_ref if artifact_ref is not None else
                            track['artifact']['artifact_ref'] if track else None,
                            binding_key if binding_key is not None else
                            track['binding_key'] if track else comparison['comparison_key'],
                            field=field, requirement=requirement,
                            row_ordinals=row_ordinals, locations=locations))

    selected, contigs, aliases, population_usable, dictionary_usable = _population(
        sheet['reference'], comparison, intervals, add)
    native_references = _native_reference_runs(sheet, runs, selected, contigs, aliases, add)
    if ordered_track_rows is None:
        ordered_track_rows = {}
    if not isinstance(ordered_track_rows, Mapping):
        raise ValueError('atac_track_stream_mapping_required')
    supplied_keys = list(ordered_track_rows)
    if len(set(supplied_keys)) != len(supplied_keys):
        raise ValueError('duplicate_atac_track_stream_key')
    external_keys = {key for key, track in track_map.items()
                     if isinstance(track['rows'], dict) and track['state']['availability'] == 'present'}
    if set(supplied_keys) - external_keys:
        raise ValueError('atac_unselected_or_in_memory_track_stream')
    if external_keys - set(supplied_keys):
        raise ValueError('atac_retained_track_stream_required')
    eligibility = dict(population='usable' if population_usable else 'unavailable', tracks={}, depths='unavailable')
    ports = {}
    for role in _ROLES:
        track = track_map[comparison['track_keys'][role]]
        if (track['coordinate_convention'] != 'zero_based_half_open'
                or track['numeric_storage'] != 'native_decimal_lexeme_plus_binary64_parse'
                or track['row_order'] != 'native_file_order'):
            raise ValueError('invalid_atac_track_order_or_coordinate_declaration')
        missing = track['state']['availability'] == 'missing'
        external = track['binding_key'] in external_keys
        if missing and (isinstance(track['rows'], dict) or track['rows']):
            raise ValueError('invalid_atac_missing_track_rows')
        if external:
            if track['ordered_row_index'] is not None:
                raise ValueError('invalid_atac_external_ordered_row_index')
            try:
                source = iter(ordered_track_rows[track['binding_key']])
            except TypeError as error:
                raise ValueError('atac_track_row_iterable_required') from error
        else:
            source = _memory_rows(track, aliases)
        usable = not missing and _track_usable(track, role, sheet, samples, conditions, runs, dictionary_usable, add)
        if track['binding']['callpeak_run_key'] is not None and not native_references[track['binding']['callpeak_run_key']]:
            usable = False
        eligibility['tracks'][role] = 'missing' if missing else 'usable' if usable else 'unavailable'
        port = dict(rows=None, extent=atac_track_extent(track) if usable or missing else 'failed',
                    unlocated_invalid_row_count=track['unlocated_invalid_row_count'])
        port['rows'] = _project_rows(track, source, usable=usable, external=external,
                                    contigs=contigs, aliases=aliases, port=port,
                                    eligibility=eligibility['tracks'], role=role, add=add)
        ports[role] = port
    depth1, depth2, unit, depths_usable = _depth_operands(sheet, samples, conditions, runs, add)
    eligibility['depths'] = 'usable' if depths_usable else 'unavailable'
    return dict(tracks=ports, intervals=selected, depth1=depth1, depth2=depth2, depth_unit=unit,
                eligibility=eligibility, issues=issues)


__all__ = ['prepare_atac_calculation_inputs']
