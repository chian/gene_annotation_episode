"""A107 macs2 peak components."""


from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a107.library.atac_differential_result_contracts import validate_atac_result_record, require

def _extent(report):
    state = report['state']
    if state['availability'] == 'missing' or state['identity'] == 'mismatch':
        return 'unavailable'
    return 'complete' if state['output_extent'] == 'complete' and (not report['malformed_data_row_count']) else 'partial'

def _combined_extent(extents):
    return 'unavailable' if not extents or all((e == 'unavailable' for e in extents)) else 'complete' if all((e == 'complete' for e in extents)) else 'partial'

def _native_peaks(sheet, run_keys):
    for run_key in run_keys:
        rows = []
        for representation, field in (('xls', 'peaks_xls'), ('narrowpeak', 'narrowpeaks'), ('summit', 'summits')):
            for report in sheet[field]:
                if report['callpeak_run_key'] != run_key or _extent(report) == 'unavailable':
                    continue
                geometry = {g['row_ordinal']: g for g in report.get('peak_geometry', [])}
                for row in report['rows']:
                    links = [link for link in sheet['peak_links'] if link['callpeak_run_key'] == run_key and link['name'] == row['name']]
                    require(len(links) <= 1, 'atac_ambiguous_peak_link_record')
                    rows.append((row['row_ordinal'], ('xls', 'narrowpeak', 'summit').index(representation), dict(callpeak_run_key=run_key, representation=representation, source=report['artifact'], row=row, geometry=geometry.get(row['row_ordinal']), peak_link=links[0] if links else None)))
        for _, _, row in sorted(rows, key=lambda item: item[:2]):
            yield row

def project_native_peak_window(components, *, run_keys, row_window):
    """Project explicit native occurrences, exhausting rows to qualify totals."""
    row_window = validate_atac_result_record('Window', row_window)
    require(type(run_keys) is list and all((type(key) is str for key in run_keys)) and (len(run_keys) == len(set(run_keys))), 'atac_result_unknown_run')
    require(set(run_keys) <= {r['run_key'] for r in components['callpeak_bindings']}, 'atac_result_unknown_run')
    selected = [r for field in ('peaks_xls', 'narrowpeaks', 'summits') for r in components[field] if r['callpeak_run_key'] in run_keys]
    extent = _combined_extent([_extent(r) for r in selected]) if run_keys else 'complete'
    projection = dict(row_window=deepcopy(row_window), total_rows=None, row_extent=extent, rows=[])
    count = 0
    offset, limit = (row_window['offset'], row_window['limit'])
    for row in _native_peaks(components, run_keys):
        if offset <= count < offset + limit:
            projection['rows'].append(deepcopy(row))
        count += 1
    projection['total_rows'] = count if extent == 'complete' else None
    return validate_atac_result_record('NativePeakWindow', projection)
