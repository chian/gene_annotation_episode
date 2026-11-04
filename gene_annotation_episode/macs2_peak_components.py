"""Common native MACS2 peak observations and explicit row projections.

This factors the existing ATAC peak authority. It neither calls MACS2 nor
calculates differential accessibility, peak confidence or biological meaning.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

from .atac_differential_contracts import (
    issue, validate_atac_reference, validate_atac_callpeak_binding,
    validate_atac_parsed_table,
)
from .atac_differential_inputs import (
    parse_macs2_peaks_xls, parse_macs2_narrowpeak, parse_macs2_summits_bed,
    MACS2_PEAK_PARSE_PROFILES,
)
from .atac_differential_result_contracts import (
    atac_result_schema, validate_atac_result_record, require,
)


def _missing_artifact(ref, fmt, producer=None):
    return dict(artifact_ref=ref, format=fmt, expected_sha256=None, expected_size_bytes=None,
                supplied_extent='unknown', producer_run_ref=producer, producer_outcome='unknown',
                writer_closed=None, producer_name=None, producer_version=None,
                producer_source_ref=None, origin='unknown')


def _complete_peak_roles(values, bindings, kind, *, parse_profile='atac_single_end_no_control'):
    parser, fmt = {'peaks_xls': (parse_macs2_peaks_xls, 'macs2_peaks_xls_narrow'),
                   'narrowpeak': (parse_macs2_narrowpeak, 'macs2_narrowpeak10'),
                   'summits': (parse_macs2_summits_bed, 'macs2_summits_bed5')}[kind]
    result = deepcopy(list(values))
    for binding in bindings:
        if not any(r['callpeak_run_key'] == binding['run_key'] for r in result):
            result.append(parser(None, artifact=_missing_artifact(binding['artifact_roles'][kind], fmt,
                                  binding['producer_ref']), callpeak=binding, parse_profile=parse_profile))
    return result


def _peak_links(peaks_xls, narrowpeaks, summits):
    groups = defaultdict(lambda: dict(xls=[], narrowpeak=[], summit=[]))
    for kind, reports in (('xls', peaks_xls), ('narrowpeak', narrowpeaks), ('summit', summits)):
        for report in reports:
            geometry = {g['row_ordinal']: g for g in report.get('peak_geometry', [])}
            for row in report['rows']:
                groups[(report['callpeak_run_key'], row['name'])][kind].append((row, report, geometry.get(row['row_ordinal'])))
    links, issues = [], []
    for (run_key, name), representations in sorted(groups.items()):
        counts = [len(representations[k]) for k in ('xls', 'narrowpeak', 'summit')]
        status = 'ambiguous' if any(n > 1 for n in counts) else 'missing_representation' if any(n == 0 for n in counts) else 'matched'
        if status == 'matched':
            (xls, xr, geom), (narrow, nr, _), (summit, sr, _) = (representations[k][0] for k in ('xls', 'narrowpeak', 'summit'))
            consistent = (geom is not None and geom['status'] == 'valid'
                          and xls['chromosome'] == narrow['chromosome'] == summit['chromosome']
                          and (geom['start0'], geom['end0']) == (narrow['start0'], narrow['end0'])
                          and summit['start0'] == geom['summit0']
                          and summit['end0'] == geom['summit0'] + 1
                          and narrow['summit_offset0'] is not None
                          and narrow['start0'] + narrow['summit_offset0'] == geom['summit0'])
            # Writers emit these statistics at the same %.6g precision. Display
            # score is intentionally not recomputed from rounded exported scores.
            for xfield, nfield in (('fold_enrichment', 'signal_value'),
                                   ('minus_log10_pvalue', 'minus_log10_pvalue'),
                                   ('minus_log10_qvalue', 'minus_log10_qvalue')):
                if xls[xfield] is not None and narrow[nfield] is not None and xls[xfield] != narrow[nfield]:
                    consistent = False
            basis = sr['score_basis']
            if basis in xls and summit['score'] is not None and xls[basis] is not None and summit['score'] != xls[basis]:
                consistent = False
            if not consistent:
                status = 'conflicting'
        link = dict(callpeak_run_key=run_key, name=name,
                    xls_row_ordinals=[r[0]['row_ordinal'] for r in representations['xls']],
                    narrowpeak_row_ordinals=[r[0]['row_ordinal'] for r in representations['narrowpeak']],
                    summit_row_ordinals=[r[0]['row_ordinal'] for r in representations['summit']], status=status)
        links.append(link)
        if status != 'matched':
            all_rows = [entry for values in representations.values() for entry in values]
            for row, report, _ in all_rows:
                issues.append(issue('peak_representation_conflict', report['artifact']['artifact_ref'], run_key,
                                    row_ordinals=(row['row_ordinal'],), locations=(row['locator'],),
                                    field='name', requirement='original_native_metadata'))
    return links, issues


def _reference_maps(reference, issues, key):
    contigs, aliases, conflicting = {}, {}, False
    for contig in reference['contigs']:
        token = contig['chromosome']
        if token in contigs:
            conflicting = True
            issues.append(issue('reference_conflict', None, key, field='contigs', requirement='explicit_reference_mapping'))
        contigs[token] = contig
    for alias in reference['aliases']:
        source, target = alias['source_chromosome'], alias['target_chromosome']
        if (alias['reference_id'] != reference['reference_id'] or target not in contigs
                or source in aliases and aliases[source] != target or source in contigs and source != target):
            conflicting = True
            issues.append(issue('reference_conflict', None, key, field='aliases', requirement='explicit_reference_mapping'))
        else:
            aliases[source] = target
    return contigs, aliases, conflicting


def _check_peak_reference(reports, contigs, aliases):
    for report in reports:
        for row in report['rows']:
            contig = contigs.get(aliases.get(row['chromosome'], row['chromosome']))
            code = 'unknown_chromosome' if contig is None else None
            end = row.get('end1', row.get('end0', row.get('reported_end0')))
            if contig is not None and contig['length_bp'] is not None and end is not None and end > contig['length_bp']:
                code = 'coordinate_outside_reference'
            if code:
                report['issues'].append(issue(code, report['artifact']['artifact_ref'], report['binding_key'],
                                              row_ordinals=(row['row_ordinal'],), locations=(row['locator'],),
                                              requirement='explicit_reference_mapping'))


def _extent(report):
    state = report['state']
    if state['availability'] == 'missing' or state['identity'] == 'mismatch':
        return 'unavailable'
    return 'complete' if state['output_extent'] == 'complete' and not report['malformed_data_row_count'] else 'partial'


def _combined_extent(extents):
    return ('unavailable' if not extents or all(e == 'unavailable' for e in extents)
            else 'complete' if all(e == 'complete' for e in extents) else 'partial')


def _native_peaks(sheet, run_keys):
    for run_key in run_keys:
        # Each representation has its own native ordinal. Representation order
        # breaks simultaneous ordinals without conflating the observations.
        rows = []
        for representation, field in (('xls', 'peaks_xls'), ('narrowpeak', 'narrowpeaks'), ('summit', 'summits')):
            for report in sheet[field]:
                if report['callpeak_run_key'] != run_key or _extent(report) == 'unavailable':
                    continue
                geometry = {g['row_ordinal']: g for g in report.get('peak_geometry', [])}
                for row in report['rows']:
                    links = [link for link in sheet['peak_links'] if link['callpeak_run_key'] == run_key and link['name'] == row['name']]
                    require(len(links) <= 1, 'atac_ambiguous_peak_link_record')
                    rows.append((row['row_ordinal'], ('xls', 'narrowpeak', 'summit').index(representation),
                        dict(callpeak_run_key=run_key, representation=representation, source=report['artifact'], row=row,
                             geometry=geometry.get(row['row_ordinal']), peak_link=links[0] if links else None)))
        for _, _, row in sorted(rows, key=lambda item: item[:2]):
            yield row


def build_macs2_peak_components(*, reference, callpeak_bindings, peaks_xls,
        narrowpeaks, summits, parse_profile='atac_single_end_no_control'):
    """Assemble native peak reports without inventing a second condition.

    Already parsed reports keep their original qualifications. The explicit
    profile applies when constructing a missing role; real reports must have
    been read under their selected native mode by the shared table parser.
    """
    require(type(parse_profile) is str and parse_profile in MACS2_PEAK_PARSE_PROFILES,
        'invalid_macs2_peak_parse_profile')
    validate_atac_reference(reference)
    bindings = deepcopy(list(callpeak_bindings))
    for binding in bindings:
        validate_atac_callpeak_binding(binding)
    require(len({row['run_key'] for row in bindings}) == len(bindings), 'duplicate_atac_callpeak_run_key')
    for reports, version in ((peaks_xls, 'macs2_peaks_xls_parsed_v1'),
            (narrowpeaks, 'macs2_narrowpeak_parsed_v1'), (summits, 'macs2_summits_parsed_v1')):
        for report in reports:
            validate_atac_parsed_table(report, version=version)
    components = dict(version='macs2_peak_components_v1', reference=deepcopy(reference),
        callpeak_bindings=bindings,
        peaks_xls=_complete_peak_roles(peaks_xls, bindings, 'peaks_xls', parse_profile=parse_profile),
        narrowpeaks=_complete_peak_roles(narrowpeaks, bindings, 'narrowpeak', parse_profile=parse_profile),
        summits=_complete_peak_roles(summits, bindings, 'summits', parse_profile=parse_profile),
        peak_links=[], reference_relation='unknown', data_status='unavailable', issues=[])
    problems = components['issues']
    contigs, aliases, conflict = _reference_maps(reference, problems, 'macs2_peaks')
    if any(binding['reference_id'] != reference['reference_id'] for binding in bindings):
        conflict = True
        problems.append(issue('reference_conflict', None, 'macs2_peaks', field='reference_id',
            requirement='explicit_reference_mapping'))
    components['reference_relation'] = ('conflicting' if conflict else
        'same_supplied_reference' if contigs else 'unknown')
    reports = components['peaks_xls'] + components['narrowpeaks'] + components['summits']
    _check_peak_reference(reports, contigs, aliases)
    components['peak_links'], link_problems = _peak_links(
        components['peaks_xls'], components['narrowpeaks'], components['summits'])
    problems.extend(link_problems)
    run_map = {row['run_key']: row for row in bindings}
    for role, selected in (('peaks_xls', components['peaks_xls']),
            ('narrowpeak', components['narrowpeaks']), ('summits', components['summits'])):
        for report in selected:
            binding = run_map.get(report['callpeak_run_key'])
            if (binding is None or binding['artifact_roles'][role] != report['artifact']['artifact_ref']
                    or binding['producer_ref'] != report['artifact']['producer_run_ref']):
                problems.append(issue('condition_binding_conflict', report['artifact']['artifact_ref'],
                    'macs2_peaks', field=role, requirement='condition_mapping'))
    for report in reports:
        problems.extend(deepcopy(report['issues']))
    present = [report for report in reports if report['state']['availability'] == 'present']
    components['data_status'] = ('unavailable' if not present else 'complete_reported_data'
        if all(report['state']['output_extent'] == 'complete' for report in reports) else 'partial_reported_data')
    return validate_atac_result_record('NativePeakComponents', components)


def native_peak_counts(components):
    """Readable occurrences per representation; never sum the representations."""
    peaks = []
    for run in components['callpeak_bindings']:
        for field, representation in (('peaks_xls', 'xls'), ('narrowpeaks', 'narrowpeak'), ('summits', 'summit')):
            reports = [r for r in components[field] if r['callpeak_run_key'] == run['run_key']]
            extent = _combined_extent([_extent(r) for r in reports])
            peaks.append(dict(run_key=run['run_key'], representation=representation,
                count=None if extent == 'unavailable' else sum(r['readable_data_row_count'] for r in reports), extent=extent))
    return peaks


def project_native_peak_window(components, *, run_keys, row_window):
    """Project explicit native occurrences, exhausting rows to qualify totals."""
    row_window = validate_atac_result_record('Window', row_window)
    require(type(run_keys) is list and all(type(key) is str for key in run_keys)
        and len(run_keys) == len(set(run_keys)), 'atac_result_unknown_run')
    require(set(run_keys) <= {r['run_key'] for r in components['callpeak_bindings']}, 'atac_result_unknown_run')
    selected = [r for field in ('peaks_xls', 'narrowpeaks', 'summits')
        for r in components[field] if r['callpeak_run_key'] in run_keys]
    extent = _combined_extent([_extent(r) for r in selected]) if run_keys else 'complete'
    projection = dict(row_window=deepcopy(row_window), total_rows=None, row_extent=extent, rows=[])
    count = 0
    offset, limit = row_window['offset'], row_window['limit']
    for row in _native_peaks(components, run_keys):
        if offset <= count < offset + limit:
            projection['rows'].append(deepcopy(row))
        count += 1
    projection['total_rows'] = count if extent == 'complete' else None
    return validate_atac_result_record('NativePeakWindow', projection)


def macs2_peak_schema(kind):
    """Return reachable existing native definitions for the finite new views."""
    names = {'Components': 'NativePeakComponents', 'Window': 'NativePeakWindow'}
    require(type(kind) is str and kind in names, 'unknown_macs2_peak_record')
    return atac_result_schema(names[kind])


__all__ = ['build_macs2_peak_components', 'native_peak_counts',
    'project_native_peak_window', 'macs2_peak_schema']
