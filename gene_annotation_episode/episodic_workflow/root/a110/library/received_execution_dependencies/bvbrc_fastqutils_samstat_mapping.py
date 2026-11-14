from __future__ import annotations
_COUNTS = {'samstat_alignment_bin_count', 'samstat_alignment_total_count'}

def _bin_index(cell):
    axis = cell['axis']
    if axis['kind'] == 'mapq':
        bounds = (axis['lower'], axis['upper'])
        if bounds in ((30, 255), (10, 29), (0, 9)):
            return ((30, 255), (10, 29), (0, 9)).index(bounds)
    elif axis['kind'] == 'native_label' and axis['label'] == 'Unmapped' and (axis['lower'] is None) and (axis['upper'] is None):
        return 3
    return None

def _count_operands(sheet, population_refs):
    """Retain every count, including duplicates/invalid axes, in bin order."""
    result = []
    for ref in dict.fromkeys(population_refs):
        rows = [c for c in sheet['measurements'] if c['population_ref'] == ref and c['metric'] in _COUNTS]

        def order(cell):
            if cell['metric'] == 'samstat_alignment_total_count':
                return 5
            index = _bin_index(cell)
            return 4 if index is None else index
        result.extend(sorted(rows, key=order))
    return result

def _report_mode(document):
    """Native labels establish mode; paths and count presence never do."""
    actual = document['artifact']['actual_format']
    if actual == 'samstat_html_2_2_3':
        labels = {r['value'] for r in document['labels'] if r['kind'] == 'native_label' and r['section_key'] == 'samstat_summary' and (r['value'] in {'Mapping statistics', 'File statistics'})}
        alignment, sequence = ('Mapping statistics' in labels, 'File statistics' in labels)
    elif actual == 'samstat_html_2_5_0':
        labels = {r['value'] for r in document['labels'] if r['kind'] == 'native_label' and r['locator']['field'] == 'input_format'}
        if labels - {'SAM', 'BAM', 'FASTQ', 'FASTA'}:
            return 'conflicting' if len(labels) > 1 else 'unknown'
        alignment, sequence = (bool(labels & {'SAM', 'BAM'}), bool(labels & {'FASTQ', 'FASTA'}))
        if len(labels) > 1:
            return 'conflicting'
    else:
        return 'unknown'
    return 'conflicting' if alignment and sequence else 'alignment' if alignment else 'sequence' if sequence else 'unknown'

def _mapping_conflicts(document):
    fields = ('member', 'block', 'block_ordinal', 'row_ordinal', 'field', 'byte_start', 'byte_end')
    locations = {str({key: s['locator'][key] for key in fields}) for s in document['sections'] if s['key'] == 'samstat_mapping'}
    return [d['code'] for d in document['diagnostics'] if d['locator'] in locations and d['code'] in {'selection_ambiguous', 'native_header_conflict'}]
