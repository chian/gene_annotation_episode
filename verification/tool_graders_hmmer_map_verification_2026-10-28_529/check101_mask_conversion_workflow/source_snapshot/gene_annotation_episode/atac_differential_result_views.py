"""Pure projections from retained ATAC numbers, never acquisition or scoring."""
from __future__ import annotations

from copy import deepcopy
from .atac_differential_result_contracts import validate_atac_result_record, CATEGORIES, require


def _extent(report):
    state = report['state']
    if state['availability'] == 'missing' or state['identity'] == 'mismatch':
        return 'unavailable'
    return 'complete' if state['output_extent'] == 'complete' and not report['malformed_data_row_count'] else 'partial'


def native_counts(sheet):
    """Readable occurrence counts per representation; never sum representations."""
    peaks = []
    for run in sheet['callpeak_bindings']:
        for field, representation in (('peaks_xls', 'xls'), ('narrowpeaks', 'narrowpeak'), ('summits', 'summit')):
            reports = [r for r in sheet[field] if r['callpeak_run_key'] == run['run_key']]
            extent = _combined_extent([_extent(r) for r in reports])
            peaks.append(dict(run_key=run['run_key'], representation=representation,
                count=None if extent == 'unavailable' else sum(r['readable_data_row_count'] for r in reports), extent=extent))
    regions = []
    for category in CATEGORIES:
        reports = [r for r in sheet['native_differential'] if r['category'] == category]
        extent = _combined_extent([_extent(r) for r in reports])
        qualifications = {r['coordinate_qualification'] for r in reports}
        regions.append(dict(category=category, count=None if extent == 'unavailable' else sum(r['readable_data_row_count'] for r in reports),
            extent=extent, coordinate_qualification=next(iter(qualifications)) if len(qualifications) == 1 else 'unverified_native_version'))
    return peaks, regions


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


def _native_differential(sheet, categories):
    for category in categories:
        for report in sheet['native_differential']:
            if report['category'] == category and _extent(report) != 'unavailable':
                for row in report['rows']:
                    yield dict(category=category, source=report['artifact'], row=row,
                        coordinate_qualification=report['coordinate_qualification'])


def project_atac_result(sheet, calculations, *, selector, component_rows=None, region_rows=None):
    selector = validate_atac_result_record('ResultSelector', selector)
    calculations = validate_atac_result_record('Calculations', calculations)
    comparison = sheet['comparison']
    require(selector['comparison_key'] == comparison['comparison_key'] == calculations['comparison_key'], 'atac_result_comparison_conflict')
    require(calculations['reference_id'] == sheet['reference']['reference_id']
        and calculations['condition_ids'] == [comparison['condition1_id'], comparison['condition2_id']]
        and calculations['parameters'] == selector['parameters']
        and calculations['selected_intervals'] == selector['intervals'], 'atac_result_calculation_binding_conflict')
    view = selector['projection']
    kind = view['kind']
    projection = dict(version='atac_differential_projection_v1', comparison_key=comparison['comparison_key'],
        reference_id=calculations['reference_id'], condition_ids=deepcopy(calculations['condition_ids']),
        selected_intervals=deepcopy(selector['intervals']), parameters=deepcopy(selector['parameters']), kind=kind,
        row_window=deepcopy(view['row_window']), total_rows=None, row_extent='unavailable', rows=[], summary=None,
        qualifications=deepcopy(calculations['issues']), failures=deepcopy(calculations['failures']))
    if kind == 'summary':
        projection.update(total_rows=0, summary=deepcopy(calculations['summary']), row_extent='complete')
        return validate_atac_result_record('RequestedProjection', projection)
    if kind == 'native_peak_rows':
        require(set(view['run_keys']) <= {r['run_key'] for r in sheet['callpeak_bindings']}, 'atac_result_unknown_run')
        selected = [r for field in ('peaks_xls', 'narrowpeaks', 'summits') for r in sheet[field] if r['callpeak_run_key'] in view['run_keys']]
        extent = _combined_extent([_extent(r) for r in selected]) if view['run_keys'] else 'complete'
        rows = _native_peaks(sheet, view['run_keys'])
    elif kind == 'native_differential_rows':
        selected = [r for r in sheet['native_differential'] if r['category'] in view['categories']]
        extent = _combined_extent([_extent(r) for r in selected]) if view['categories'] else 'complete'
        rows = _native_differential(sheet, view['categories'])
    else:
        table_key = 'components' if kind == 'interval_components' else 'regions'
        tables = [r for r in calculations['tables'] if r['table_key'] == table_key]
        require(len(tables) <= 1, 'atac_result_duplicate_table')
        supplied = component_rows if kind == 'interval_components' else region_rows
        extent = tables[0]['extent'] if tables else 'unavailable'
        require(supplied is not None or not tables, 'atac_result_supplied_rows_required')
        rows = supplied if supplied is not None else ()
        if kind == 'derived_regions':
            rows = (row for row in rows if row['category'] in view['categories'])
    count = 0
    offset, limit = view['row_window']['offset'], view['row_window']['limit']
    # Exhaust even after the window: a valid prefix cannot prove total extent.
    for row in rows:
        if offset <= count < offset + limit:
            projection['rows'].append(deepcopy(row))
        count += 1
    projection.update(total_rows=count if extent == 'complete' else None, row_extent=extent)
    return validate_atac_result_record('RequestedProjection', projection)


__all__ = ['project_atac_result', 'native_counts']
