"""Original tf binding received values for supplied decision information."""
from __future__ import annotations
from .molecular_provenance_display import _molecular_literal
from .decision_prompt_text import _table


def _tf_binding_text(packet, number):
    """Display literal TF values without reading Files or calculating scores."""
    sequences = {row['sequence_id']: row for row in packet['sequences']}
    matrices = {row['matrix_occurrence_id']: row for row in packet['matrices']}
    models = {row['model_id']: row for row in packet['matrices']}
    parts = ['Selected molecular result ' + str(number), '',
        _table(('Callable operand', 'Retained value'), [
            ('Result Source', packet['source_ref']), ('Result state', packet['status']),
            ('Raw log2-odds threshold', packet['selection']['raw_threshold']),
            ('Selection offset', packet['selection']['offset']),
            ('Selection limit', packet['selection']['limit'])]), '',
        'Selected scans in caller order', '',
        _table(('Callable scan ID',), ((scan,) for scan in packet['selection']['scan_ids'])), '',
        'Declared input parameters before native normalization', '',
        _table(('Base', 'Declared background', 'Declared pseudocount'), [
            (base, packet['parameters']['background'][base], packet['parameters']['pseudocounts'][base])
            for base in 'ACGT']), '',
        'Recorded execution and numerical convention', '',
        _table(('Field', 'Retained value'), [*packet['execution'].items(),
            *((name, packet['numeric_authority'][name]) for name in ('biopython_version',
                'numpy_version', 'threshold_operand', 'comparison', 'relative', 'relative_bounds'))]), '',
        'Supplied input capture states', '',
        _table(('Input', 'Role', 'Format', 'Capture state', 'Capture end (exclusive)', 'Original bytes'), [
            (row['input_id'], row['role'], row['format'], row['capture']['state'],
                row['capture']['byte_end_0based_exclusive'], row['capture']['original_size_bytes'])
            for row in packet['inputs']]), '',
        'Original sequence occurrences', '',
        _table(('Input', 'Original record ordinal', 'Identifier', 'Length', 'State'), [
            (row['input_id'], row['record_ordinal_0based'], row['identifier'], row['length'], row['state'])
            for row in packet['sequences']]), '',
        'Original matrix occurrences', '',
        _table(('Input', 'Original record ordinal', 'Native matrix ID', 'Name', 'Length', 'State'), [
            (row['input_id'], row['record_ordinal_0based'], row['native_matrix_id'], row['name'],
                row['length'], row['state']) for row in packet['matrices']]), '',
        'Retained scans available for saved selection', '',
        _table(('Callable scan ID', 'Sequence input', 'Sequence record', 'Matrix input', 'Matrix record',
            'Strand', 'Possible positions', 'Coverage', 'Declared count', 'Captured complete elements',
            'Usable elements', 'Trailing bytes', 'Excess elements'), [
            (row['scan_id'], sequences[row['sequence_id']]['input_id'],
                sequences[row['sequence_id']]['record_ordinal_0based'],
                matrices[row['matrix_occurrence_id']]['input_id'],
                matrices[row['matrix_occurrence_id']]['record_ordinal_0based'], row['strand'],
                row['possible_positions'], row['coverage']['state'], row['coverage']['declared_count'],
                row['coverage']['captured_complete_elements'], row['coverage']['usable_elements'],
                row['coverage']['trailing_bytes'], row['coverage']['excess_elements'])
            for row in packet['available_scans']]), '',
        'Retained counts for the selected scans', '',
        _table(('Quantity', 'Literal value', 'State', 'Unit', 'Origin', 'Numerator', 'Denominator', 'Uncertainty'), [
            (name.replace('_', ' '), cell['value'], cell['state'], cell['unit'], cell['origin'],
                cell['numerator'], cell['denominator'], _molecular_literal(cell['uncertainty']))
            for name, cell in packet['totals'].items()]), '',
        'Returned raw-threshold rows; coordinates are zero-based forward-sequence intervals', '',
        _table(('Callable scan ID', 'Sequence record', 'Matrix record', 'Strand', 'Start', 'End (exclusive)',
            'Forward sequence', 'Motif-oriented sequence', 'Raw score (bits)', 'Raw score class',
            'Relative score', 'Relative class', 'Relative state', 'Relative reason', 'Model normalization eligible'), [
            (row['scan_id'], row['sequence_record_ordinal_0based'], row['matrix_record_ordinal_0based'],
                row['strand'], row['start_0based'], row['end_0based_exclusive'], row['forward_sequence'],
                row['motif_oriented_sequence'], row['score']['value'], row['score']['classification'],
                row['relative_score']['value'], row['relative_score']['classification'],
                row['relative_score']['state'], row['relative_score']['reason_code'],
                row['model_normalization_eligible']) for row in packet['raw_threshold_matches']])]
    for row in packet['relative_normalizations']:
        matrix = models[row['model_id']]
        parts.extend(['', 'Retained relative normalization', '',
            _table(('Property', 'Retained value'), [
                ('Matrix input', matrix['input_id']), ('Original matrix record', matrix['record_ordinal_0based']),
                *((name, row[name]) for name in
                    ('bounds_strand', 'operand_dtype', 'scientific_state', 'reason_code'))]), '',
            _table(('Operand', 'Literal value', 'Class', 'State', 'Unit'), [
                (name, row[name]['value'], row[name]['classification'], row[name]['state'], row[name]['unit'])
                for name in ('minimum', 'maximum', 'span')])])
    parts.extend(['', 'Result qualifications', '',
        _table(('Code', 'Phase', 'Input/record pointer', 'Severity'), [
            (row['code'], row['phase'], row['path'], row['severity']) for row in packet['issues']])])
    return '\n'.join(parts)


