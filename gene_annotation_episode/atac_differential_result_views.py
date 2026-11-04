"""Pure projections from retained ATAC numbers, never acquisition or scoring."""
from __future__ import annotations

from copy import deepcopy
from .atac_differential_result_contracts import validate_atac_result_record, CATEGORIES, require
from .macs2_peak_components import (
    _extent, _combined_extent, _native_peaks, native_peak_counts, project_native_peak_window,
)


def native_counts(sheet):
    """Readable occurrence counts per representation; never sum representations."""
    peaks = native_peak_counts(sheet)
    regions = []
    for category in CATEGORIES:
        reports = [r for r in sheet['native_differential'] if r['category'] == category]
        extent = _combined_extent([_extent(r) for r in reports])
        qualifications = {r['coordinate_qualification'] for r in reports}
        regions.append(dict(category=category, count=None if extent == 'unavailable' else sum(r['readable_data_row_count'] for r in reports),
            extent=extent, coordinate_qualification=next(iter(qualifications)) if len(qualifications) == 1 else 'unverified_native_version'))
    return peaks, regions


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
        projection.update(project_native_peak_window(sheet, run_keys=view['run_keys'],
            row_window=view['row_window']))
        return validate_atac_result_record('RequestedProjection', projection)
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
