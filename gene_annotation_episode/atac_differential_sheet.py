"""Join retained ATAC measurements without calculating likelihoods or credit.

This sheet retains original numbers and explicitly converted peak coordinates.
Depth selection extracts the actual post-filter native count; it performs no
million-unit conversion or scaling. The interval calculator consumes the sheet
separately and never repairs the original bdgdiff BED records in place.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Sequence

from .atac_differential_contracts import (
    AtacCallpeakBinding, AtacComparisonBinding, AtacCondition,
    AtacDeclaredDepthSelection, AtacDepthCountSelection, AtacNativeSheet,
    AtacReference, AtacSample, ParsedAtacBamReference, ParsedAtacTrack, ParsedMacs2Bdgdiff,
    ParsedMacs2NarrowPeak, ParsedMacs2PeaksXls, ParsedMacs2Summits,
    issue, valid_track_geometry, validate_atac_callpeak_binding,
    validate_atac_comparison_binding, validate_atac_condition,
    validate_atac_depth_selection, validate_atac_reference,
    validate_atac_retained_track_table, validate_atac_sample,
    validate_atac_track_binding, validate_atac_parsed_table,
)
from .macs2_peak_components import (
    _missing_artifact, _complete_peak_roles, _peak_links, _reference_maps, _check_peak_reference,
)
from .atac_differential_inputs import (
    parse_atac_bedgraph, parse_macs2_bdgdiff_bed, parse_macs2_narrowpeak,
    parse_macs2_peaks_xls, parse_macs2_summits_bed,
)


def _selection_issue(code, condition_id, report=None, field=None, requirement='matching_count_population'):
    return issue(code, report['artifact']['artifact_ref'] if report else None, condition_id,
                 field=field, requirement=requirement)


def select_atac_depth_counts(reports: Sequence[ParsedMacs2PeaksXls], *,
                             conditions: tuple[str, str],
                             callpeak_bindings: Sequence[AtacCallpeakBinding]) -> AtacDepthCountSelection:
    """Select one identity-bound native header/run per comparison condition.

    A usable header in a partial report remains a count. No total-count fallback,
    model-background count, BAM-generator assertion or filename supplies depth.
    """
    if (not isinstance(conditions, (list, tuple)) or len(conditions) != 2
            or any(type(c) is not str or not c for c in conditions)):
        raise ValueError('invalid_atac_depth_conditions')
    for binding in callpeak_bindings:
        validate_atac_callpeak_binding(binding)
    for report in reports:
        validate_atac_parsed_table(report, version='macs2_peaks_xls_parsed_v1')
    issues, selected = [], []
    for condition in conditions:
        bindings = [b for b in callpeak_bindings if b['condition_id'] == condition]
        binding = bindings[0] if len(bindings) == 1 else None
        row = dict(condition_id=condition, sample_ids=deepcopy(binding['sample_ids']) if binding else [],
                   callpeak_run_key=binding['run_key'] if binding else None,
                   count=None, count_lexeme=None, count_unit='postfilter_single_end_tags',
                   count_population='macs2_loaded_treatment_tags_after_duplicate_filtering',
                   source_artifact_ref=None, source_locations=[], source_field='treatment_postfilter_tags',
                   million_denominator=1000000, state='missing')
        selected.append(row)
        if binding is None:
            row['state'] = 'conflicting' if bindings else 'missing'
            issues.append(_selection_issue('condition_binding_conflict' if bindings else 'metadata_missing',
                                           condition, field='callpeak_run_key', requirement='condition_mapping'))
            continue
        candidates = [r for r in reports if r.get('callpeak_run_key') == binding['run_key']]
        if len(candidates) != 1:
            row['state'] = 'conflicting' if candidates else 'missing'
            issues.append(_selection_issue('metadata_conflict' if candidates else 'metadata_missing',
                                           condition, field='peaks_xls', requirement='original_native_metadata'))
            continue
        report = candidates[0]
        if report.get('version') != 'macs2_peaks_xls_parsed_v1':
            raise ValueError('invalid_atac_peaks_xls_report')
        row['source_artifact_ref'] = report['artifact']['artifact_ref']
        count = report['reported_numbers']['treatment_postfilter_tags']
        row['source_locations'] = deepcopy(count['locations'])
        p, metadata = binding['selected_parameters'], report['reported_metadata']
        mode_supported = (binding['selected_format'] == 'BAM' and binding['paired_end'] is False
                          and p['spmr'] is False and p['downsample'] is False and p['broad'] is False
                          and p['nomodel'] is True
                          and binding['supplied_control_input_refs'] == []
                          and binding['supplied_control_sample_ids'] == []
                          and metadata['format'] == 'BAM' and metadata['paired_end'] is False
                          and metadata['control_presence'] == 'absent'
                          and metadata['macs_version'] == '2.2.9.1'
                          and not any(i['code'] in ('unsupported_mode', 'unsupported_normalization') for i in report['issues']))
        identity_bound = (report['state']['identity'] == 'verified'
                          and report['artifact']['artifact_ref'] == binding['artifact_roles']['peaks_xls']
                          and report['artifact']['producer_run_ref'] == binding['producer_ref'])
        conflicts = any(i['code'] == 'metadata_conflict' for i in report['issues'])
        if not identity_bound or conflicts or count['state'] == 'conflicting':
            row['state'] = 'conflicting'
            issues.append(_selection_issue('metadata_conflict', condition, report, 'treatment_postfilter_tags',
                                           requirement='original_native_metadata'))
        elif not mode_supported:
            row['state'] = 'incompatible_mode'
            issues.append(_selection_issue('unsupported_mode', condition, report,
                                           requirement='compatible_native_mode'))
        elif count['state'] != 'present' or type(count['value']) is not int or count['value'] < 0:
            issues.append(_selection_issue('metadata_missing', condition, report, 'treatment_postfilter_tags',
                                           requirement='original_native_metadata'))
        else:
            row.update(count=count['value'], count_lexeme=count['lexeme'],
                       state='zero' if count['value'] == 0 else 'observed')
            if count['value'] == 0:
                issues.append(_selection_issue('zero_depth', condition, report, 'treatment_postfilter_tags'))
    compatible = all(row['state'] in ('observed', 'zero') for row in selected)
    if conditions[0] == conditions[1]:
        compatible = False
        issues.append(_selection_issue('condition_binding_conflict', conditions[0], requirement='condition_mapping'))
    chosen = [[b for b in callpeak_bindings if b['condition_id'] == c] for c in conditions]
    if all(len(group) == 1 for group in chosen):
        first, second = chosen[0][0], chosen[1][0]
        for field, shared in (
            ('shared_samples', set(first['sample_ids']) & set(second['sample_ids'])),
            ('shared_treatment_inputs', set(first['treatment_input_refs']) & set(second['treatment_input_refs'])),
        ):
            if shared:
                issues.append(_selection_issue('duplicate_record', conditions[0],
                                               field=field, requirement='none'))
        if (selected[0]['source_artifact_ref'] is not None
                and selected[0]['source_artifact_ref'] == selected[1]['source_artifact_ref']):
            issues.append(issue('duplicate_record', selected[0]['source_artifact_ref'], conditions[0],
                                field='shared_artifact_content', requirement='none'))
        if first['reference_id'] != second['reference_id']:
            compatible = False
            issues.append(_selection_issue('reference_conflict', conditions[0], requirement='explicit_reference_mapping'))
    return dict(kind='native_postfilter_counts', conditions=selected,
                compatible_population=compatible, issues=issues)


def _unique_map(records, key, code):
    result = {}
    for record in records:
        if record[key] in result:
            raise ValueError(code)
        result[record[key]] = record
    return result


def _missing_track(role, comparison, conditions, bindings):
    condition_id = comparison['condition1_id' if role.endswith('1') else 'condition2_id']
    condition = next((c for c in conditions if c['condition_id'] == condition_id), None)
    matches = [b for b in bindings if b['condition_id'] == condition_id]
    native = matches[0] if len(matches) == 1 else None
    is_signal = role.startswith('signal')
    ref = native['artifact_roles']['signal_track' if is_signal else 'background_track'] if native else None
    binding = dict(track_key=comparison['track_keys'][role], condition_id=condition_id,
                   sample_ids=deepcopy(condition['sample_ids']) if condition else [],
                   role='signal' if is_signal else 'model_background',
                   callpeak_run_key=native['run_key'] if native else None,
                   reference_id=comparison['reference_id'], value_unit=None,
                   normalization='unknown', background_origin='unknown', source_artifact_ref=ref)
    return parse_atac_bedgraph(None, artifact=_missing_artifact(ref, 'bedgraph4',
                               native['producer_ref'] if native else None), binding=binding)


def _reference_track(track, contigs, aliases):
    """Bounds and structural coverage only; never a likelihood/region calculation."""
    issues = track['issues']
    artifact_ref, key = track['artifact']['artifact_ref'], track['binding_key']
    summary_by_token = {e['chromosome']: e for e in track['chromosome_extents']}
    domain_complete = bool(contigs) and all(c['length_bp'] is not None for c in contigs.values())
    covered = set()
    bad_geometry = track['unlocated_invalid_row_count'] > 0 or track['geometry_inspection'] != 'complete'
    for token, extent in summary_by_token.items():
        canonical = aliases.get(token, token)
        contig = contigs.get(canonical)
        if contig is None:
            if not isinstance(track['rows'], list):
                issues.append(issue('unknown_chromosome', artifact_ref, key, field='chromosome', requirement='explicit_reference_mapping'))
            bad_geometry = True
            continue
        length = contig['length_bp']
        extent['reference_length_bp'] = length
        extent['has_unreported_tail'] = extent['last_reported_end'] < length if length is not None and extent['last_reported_end'] is not None else None
        if (length is not None and extent['first_reported_start'] == 0
                and extent['last_reported_end'] == length and not extent['has_unreported_internal_span']):
            covered.add(canonical)
        if length is not None and extent['last_reported_end'] is not None and extent['last_reported_end'] > length:
            bad_geometry = True
    if isinstance(track['rows'], list):
        for row in track['rows']:
            contig = contigs.get(aliases.get(row[4], row[4]))
            if contig is None:
                issues.append(issue('unknown_chromosome', artifact_ref, key, row_ordinals=(row[0],),
                                    locations=(dict(line_number=row[1], byte_start=row[2], byte_end=row[3]),),
                                    field='chromosome', requirement='explicit_reference_mapping'))
            if contig and valid_track_geometry(row) and contig['length_bp'] is not None and row[6] > contig['length_bp']:
                issues.append(issue('coordinate_outside_reference', artifact_ref, key, row_ordinals=(row[0],),
                                    locations=(dict(line_number=row[1], byte_start=row[2], byte_end=row[3]),),
                                    field='end', requirement='explicit_reference_mapping'))
            if row[7] is None or row[7] < 0:
                bad_geometry = True
    else:
        validate_atac_retained_track_table(track['rows'])
        if track['rows']['source_artifact_ref'] != artifact_ref:
            issues.append(issue('metadata_conflict', artifact_ref, key, field='source_artifact_ref', requirement='matching_artifact'))
            bad_geometry = True
        if any(i['code'] in ('negative_pileup', 'invalid_number', 'nonfinite_number', 'numeric_out_of_range') for i in issues):
            bad_geometry = True
    if track['overlap_groups'] or any(i['code'] in ('overlapping_track_rows', 'duplicate_record') for i in issues):
        bad_geometry = True
    if domain_complete and covered != set(contigs):
        issues.append(issue('unreported_interval', artifact_ref, key, requirement='complete_artifact'))
    return ('unknown' if not domain_complete else 'complete_declared_domain'
            if covered == set(contigs) and not bad_geometry and track['state']['output_extent'] == 'complete'
            else 'partial_declared_domain')


def _bam_reference_bindings(reports, runs, issues):
    """Check source occurrences only; the calculation bridge compares dictionaries."""
    by_occurrence = defaultdict(list)
    for report in reports:
        run_key, ordinal = report['callpeak_run_key'], report['input_ordinal']
        by_occurrence[(run_key, ordinal)].append(report)
        run = runs.get(run_key)
        if run is None:
            field = 'callpeak_run_key'
        elif ordinal >= len(run['treatment_input_refs']):
            field = 'input_ordinal'
        elif run['treatment_input_refs'][ordinal] != report['input_artifact_ref']:
            field = 'input_artifact_ref'
        else:
            field = None
        if field:
            issues.append(issue('condition_binding_conflict', report['artifact']['artifact_ref'],
                report['binding_key'], field=field, requirement='matching_artifact'))
    for group in by_occurrence.values():
        if len(group) > 1:
            for report in group:
                issues.append(issue('metadata_conflict', report['artifact']['artifact_ref'],
                    report['binding_key'], field='bam_references', requirement='original_native_metadata'))
    for run in runs.values():
        if run['selected_format'] == 'BAM':
            for ordinal, input_ref in enumerate(run['treatment_input_refs']):
                if not any(report['input_artifact_ref'] == input_ref
                           for report in by_occurrence[(run['run_key'], ordinal)]):
                    issues.append(issue('metadata_missing', None, run['run_key'] + ':input:' + str(ordinal),
                        field='bam_references', requirement='original_native_metadata'))


def build_atac_differential_sheet(*, reference: AtacReference, samples: Sequence[AtacSample],
                                  conditions: tuple[AtacCondition, AtacCondition],
                                  callpeak_bindings: Sequence[AtacCallpeakBinding],
                                  comparison: AtacComparisonBinding, tracks: Sequence[ParsedAtacTrack],
                                  peaks_xls: Sequence[ParsedMacs2PeaksXls],
                                  narrowpeaks: Sequence[ParsedMacs2NarrowPeak],
                                  summits: Sequence[ParsedMacs2Summits],
                                  native_differential: Sequence[ParsedMacs2Bdgdiff],
                                  depth_selection: AtacDepthCountSelection | AtacDeclaredDepthSelection,
                                  bam_references: Sequence[ParsedAtacBamReference] = ()) -> AtacNativeSheet:
    validate_atac_reference(reference)
    validate_atac_comparison_binding(comparison)
    validate_atac_depth_selection(depth_selection)
    if len(conditions) != 2:
        raise ValueError('two_atac_conditions_required')
    for row in conditions:
        validate_atac_condition(row)
    for row in samples:
        validate_atac_sample(row)
    for row in callpeak_bindings:
        validate_atac_callpeak_binding(row)
    for records, version in ((tracks, 'atac_bedgraph_parsed_v1'), (peaks_xls, 'macs2_peaks_xls_parsed_v1'),
                             (narrowpeaks, 'macs2_narrowpeak_parsed_v1'), (summits, 'macs2_summits_parsed_v1'),
                             (native_differential, 'macs2_bdgdiff_parsed_v1'),
                             (bam_references, 'atac_bam_reference_parsed_v1')):
        for report in records:
            validate_atac_parsed_table(report, version=version)
    sample_map = _unique_map(samples, 'sample_id', 'duplicate_atac_sample_id')
    condition_map = _unique_map(conditions, 'condition_id', 'duplicate_atac_condition_id')
    run_map = _unique_map(callpeak_bindings, 'run_key', 'duplicate_atac_callpeak_run_key')
    track_map = _unique_map(tracks, 'binding_key', 'duplicate_atac_track_key')
    issues, key = [], comparison['comparison_key']
    sheet = dict(version='atac_differential_native_sheet_v1', tool_row='B-L125-analyze_atac_seq_differential_accessibility',
                 reference=deepcopy(reference), samples=deepcopy(list(samples)), conditions=deepcopy(list(conditions)),
                 callpeak_bindings=deepcopy(list(callpeak_bindings)), comparison=deepcopy(comparison),
                 tracks=[], peaks_xls=_complete_peak_roles(peaks_xls, callpeak_bindings, 'peaks_xls'),
                 narrowpeaks=_complete_peak_roles(narrowpeaks, callpeak_bindings, 'narrowpeak'),
                 summits=_complete_peak_roles(summits, callpeak_bindings, 'summits'),
                 peak_links=[], native_differential=deepcopy(list(native_differential)),
                 bam_references=deepcopy(list(bam_references)),
                 depth_selection=deepcopy(depth_selection), reference_relation='unknown',
                 normalization_compatibility='unknown', coverage_completeness='unknown',
                 data_status='unavailable', issues=issues)
    def add(code, field, requirement='condition_mapping', artifact_ref=None, binding_key=key):
        issues.append(issue(code, artifact_ref, binding_key, field=field, requirement=requirement))
    _bam_reference_bindings(sheet['bam_references'], run_map, issues)
    desired_conditions = [comparison['condition1_id'], comparison['condition2_id']]
    if [c['condition_id'] for c in conditions] != desired_conditions or desired_conditions[0] == desired_conditions[1]:
        add('condition_binding_conflict', 'conditions')
    references = [comparison['reference_id']] + [s['reference_id'] for s in samples] + [b['reference_id'] for b in callpeak_bindings]
    for condition in conditions:
        if len(set(condition['sample_ids'])) != len(condition['sample_ids']) or any(s not in sample_map for s in condition['sample_ids']):
            add('condition_binding_conflict', 'sample_ids', binding_key=condition['condition_id'])
    for binding in callpeak_bindings:
        expected_condition = condition_map.get(binding['condition_id'])
        if expected_condition is None or binding['sample_ids'] != expected_condition['sample_ids']:
            add('condition_binding_conflict', 'sample_ids', binding_key=binding['run_key'])
        expected_inputs = [ref for sid in binding['sample_ids'] for ref in sample_map.get(sid, {}).get('input_artifact_refs', [])]
        if set(expected_inputs) != set(binding['treatment_input_refs']):
            add('condition_binding_conflict', 'treatment_input_refs', binding_key=binding['run_key'])
    for role, track_key in comparison['track_keys'].items():
        track = deepcopy(track_map[track_key]) if track_key in track_map else _missing_track(role, comparison, conditions, callpeak_bindings)
        sheet['tracks'].append(track)
        binding = track['binding']
        validate_atac_track_binding(binding, missing=track['state']['availability'] == 'missing')
        references.append(binding['reference_id'])
        expected_condition_id = comparison['condition1_id' if role.endswith('1') else 'condition2_id']
        expected_condition = condition_map.get(expected_condition_id)
        expected_role = 'signal' if role.startswith('signal') else 'model_background'
        if (binding['track_key'] != track_key or binding['condition_id'] != expected_condition_id
                or binding['role'] != expected_role or expected_condition is None
                or binding['sample_ids'] != expected_condition['sample_ids']):
            add('condition_binding_conflict', 'track_binding', artifact_ref=track['artifact']['artifact_ref'], binding_key=track_key)
        if binding['source_artifact_ref'] != track['artifact']['artifact_ref']:
            add('metadata_conflict', 'source_artifact_ref', 'matching_artifact', binding_key=track_key)
        run = run_map.get(binding['callpeak_run_key'])
        if binding['callpeak_run_key'] is not None:
            if (run is None or run['condition_id'] != binding['condition_id']
                    or run['sample_ids'] != binding['sample_ids'] or run['reference_id'] != binding['reference_id']
                    or run['artifact_roles']['signal_track' if expected_role == 'signal' else 'background_track'] != binding['source_artifact_ref']
                    or track['artifact']['producer_run_ref'] != run['producer_ref']):
                add('condition_binding_conflict', 'callpeak_run_key', binding_key=track_key)
            elif expected_role == 'model_background':
                expected_background = ('self_model' if run['supplied_control_input_refs'] == [] else
                                       'supplied_control_model' if run['supplied_control_input_refs'] else 'unknown')
                if binding['background_origin'] != expected_background:
                    add('condition_binding_conflict', 'background_origin', binding_key=track_key)
            if run is not None and (run['selected_parameters']['spmr'] is not False
                                    or run['selected_format'] != 'BAM' or run['paired_end'] is not False
                                    or run['selected_parameters']['downsample'] is not False
                                    or run['supplied_control_input_refs'] != []):
                add('unsupported_normalization', 'callpeak_mode', 'compatible_native_mode', binding_key=track_key)
        if expected_role == 'signal' and binding['background_origin'] != 'unknown':
            add('condition_binding_conflict', 'background_origin', binding_key=track_key)
        appropriate_units = ('extended_tag_pileup', 'supplied_signal') if expected_role == 'signal' else ('model_expected_extended_tag_pileup', 'supplied_model_background')
        if binding['value_unit'] not in appropriate_units and track['state']['availability'] != 'missing':
            add('unsupported_normalization', 'value_unit', 'compatible_native_mode', binding_key=track_key)
    if set(track_map) - set(comparison['track_keys'].values()):
        raise ValueError('unselected_atac_track_key')
    # Four explicit bindings can share samples or source bytes, but never acquire
    # a claim of independent replication merely from their different filenames.
    if len(set(comparison['track_keys'].values())) != 4:
        add('condition_binding_conflict', 'track_keys')
    source_roles = defaultdict(list)
    for track in sheet['tracks']:
        ref = track['artifact']['artifact_ref']
        if ref is not None:
            source_roles[ref].append(track['binding_key'])
    for ref, roles in source_roles.items():
        if len(roles) > 1:
            add('duplicate_record', 'shared_artifact_content', requirement='none', artifact_ref=ref)
    if set(conditions[0]['sample_ids']) & set(conditions[1]['sample_ids']):
        add('duplicate_record', 'shared_samples', requirement='none')
    first_inputs = {r for sid in conditions[0]['sample_ids'] for r in sample_map.get(sid, {}).get('input_artifact_refs', [])}
    second_inputs = {r for sid in conditions[1]['sample_ids'] for r in sample_map.get(sid, {}).get('input_artifact_refs', [])}
    if first_inputs & second_inputs:
        add('duplicate_record', 'shared_treatment_inputs', requirement='none')
    first_specimens = {sample_map[sid]['biospecimen_id'] for sid in conditions[0]['sample_ids'] if sid in sample_map and sample_map[sid]['biospecimen_id'] is not None}
    second_specimens = {sample_map[sid]['biospecimen_id'] for sid in conditions[1]['sample_ids'] if sid in sample_map and sample_map[sid]['biospecimen_id'] is not None}
    if first_specimens & second_specimens:
        add('duplicate_record', 'shared_biospecimen', requirement='none')
    differential_by_category = defaultdict(list)
    for result in sheet['native_differential']:
        differential_by_category[result['category']].append(result)
        if result['comparison_key'] != comparison['comparison_key'] or result['artifact']['artifact_ref'] != comparison['artifact_roles'].get(result['category']):
            add('condition_binding_conflict', 'native_differential', artifact_ref=result['artifact']['artifact_ref'])
    for category in ('condition1', 'condition2', 'common'):
        if not differential_by_category[category]:
            sheet['native_differential'].append(parse_macs2_bdgdiff_bed(None,
                artifact=_missing_artifact(comparison['artifact_roles'][category], 'macs2_bdgdiff_bed5', comparison['producer_ref']),
                comparison=comparison, category=category))
        elif len(differential_by_category[category]) > 1:
            add('condition_binding_conflict', 'duplicate_native_category')
    contigs, aliases, ref_conflict = _reference_maps(reference, issues, key)
    if any(r != reference['reference_id'] for r in references):
        ref_conflict = True
        add('reference_conflict', 'reference_id', 'explicit_reference_mapping')
    sheet['reference_relation'] = ('conflicting' if ref_conflict else 'same_supplied_reference'
                                   if contigs else 'unknown')
    coverage = [_reference_track(track, contigs, aliases) for track in sheet['tracks']]
    sheet['coverage_completeness'] = ('unknown' if ref_conflict or 'unknown' in coverage else
                                      'complete_declared_domain' if all(c == 'complete_declared_domain' for c in coverage)
                                      else 'partial_declared_domain')
    formats = {t['binding']['normalization'] for t in sheet['tracks']}
    sheet['normalization_compatibility'] = ('incompatible' if 'spmr' in formats else 'unknown' if 'unknown' in formats
                                           else 'raw_compatible')
    if sheet['normalization_compatibility'] != 'raw_compatible':
        add('unsupported_normalization', 'normalization', 'compatible_native_mode')
    if any(i['code'] == 'unsupported_normalization' and i['field'] in ('value_unit', 'callpeak_mode') for i in issues):
        sheet['normalization_compatibility'] = 'incompatible'
    _check_peak_reference(sheet['peaks_xls'] + sheet['narrowpeaks'] + sheet['summits'] + sheet['native_differential'], contigs, aliases)
    sheet['peak_links'], links_issues = _peak_links(sheet['peaks_xls'], sheet['narrowpeaks'], sheet['summits'])
    issues.extend(links_issues)
    for category, reports in (('peaks_xls', sheet['peaks_xls']), ('narrowpeak', sheet['narrowpeaks']), ('summits', sheet['summits'])):
        for report in reports:
            binding = run_map.get(report['callpeak_run_key'])
            if (binding is None or binding['artifact_roles'][category] != report['artifact']['artifact_ref']
                    or binding['producer_ref'] != report['artifact']['producer_run_ref']):
                add('condition_binding_conflict', category, artifact_ref=report['artifact']['artifact_ref'])
    if [r['condition_id'] for r in depth_selection['conditions']] != desired_conditions:
        add('depth_population_conflict', 'conditions', 'matching_count_population')
        sheet['depth_selection']['compatible_population'] = False
    for depth in sheet['depth_selection']['conditions']:
        condition = condition_map.get(depth['condition_id'])
        if condition is None or condition['sample_ids'] != depth['sample_ids']:
            add('depth_population_conflict', 'sample_ids', 'matching_count_population')
            sheet['depth_selection']['compatible_population'] = False
    if depth_selection['kind'] == 'native_postfilter_counts':
        actual = select_atac_depth_counts(sheet['peaks_xls'], conditions=tuple(desired_conditions), callpeak_bindings=callpeak_bindings)
        if actual != depth_selection:
            add('depth_population_conflict', 'native_count_selection', 'matching_count_population')
            sheet['depth_selection']['compatible_population'] = False
    else:
        depths = depth_selection['conditions']
        if depths[0]['unit'] != depths[1]['unit'] or depths[0]['population'] != depths[1]['population'] or any(d['state'] != 'declared' for d in depths):
            add('depth_population_conflict', 'declared_depth_population', 'matching_count_population')
            sheet['depth_selection']['compatible_population'] = False
    all_reports = (sheet['tracks'] + sheet['peaks_xls'] + sheet['narrowpeaks'] + sheet['summits']
                   + sheet['native_differential'] + sheet['bam_references'])
    for report in all_reports:
        issues.extend(deepcopy(report['issues']))
    issues.extend(deepcopy(sheet['depth_selection']['issues']))
    present = [r for r in all_reports if r['state']['availability'] == 'present']
    sheet['data_status'] = ('unavailable' if not present else 'complete_reported_data'
                            if all(r['state']['output_extent'] == 'complete' for r in all_reports)
                            else 'partial_reported_data')
    return sheet
