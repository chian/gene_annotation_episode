"""Original homer motif received values for supplied decision information."""
from __future__ import annotations
from .molecular_provenance_display import _molecular_literal
from .decision_prompt_text import _rows
from .decision_prompt_text import _table


def _homer_motif_text(packet, number):
    """Show fixed HOMER measurements without reopening or calculating data."""
    series_labels = {series['series_id']: 'Series ' + str(index)
        for index, series in enumerate(packet['available_series'], 1)}
    parts = ['Selected molecular result ' + str(number), '',
        _table(('Callable operand', 'Retained value'), [
            ('Result Source', packet['source_ref']),
            ('Selected series in caller order', _molecular_literal([
                series_labels[series_id] for series_id in packet['selector']['series_ids']])),
            ('Selection offset', packet['selector']['offset']),
            ('Selection limit', packet['selector']['limit'])]), '',
        'Retained series available for saved selection', '',
        _table(('Series', 'Callable series ID', 'Role', 'Requested motif length (bp)',
            'Capture state', 'Native outcome'), [
            (series_labels[series['series_id']], series['series_id'], series['role'],
                series['requested_motif_length_bp'], series['capture_state'], series['native_outcome'])
            for series in packet['available_series']]), '',
        'Recorded execution', '', _table(('Field', 'Retained value'), packet['execution'].items()), '',
        'Captured input population facts', '',
        _table(('Field', 'Retained value'), _rows(packet['population_facts'])), '',
        'Sums of reported input weights', '',
        _table(('Group', 'Value', 'State', 'Unit', 'Origin', 'Method', 'Numerator',
            'Denominator', 'Uncertainty', 'Qualifications'), [
            (summary['group'], summary['cell']['value'], summary['cell']['state'],
                summary['cell']['unit'], summary['cell']['origin'], summary['cell']['method_id'],
                summary['cell']['numerator'], summary['cell']['denominator'],
                _molecular_literal(summary['cell']['uncertainty']),
                _molecular_literal(summary['issues']))
            for summary in packet['reported_input_weight_sums']]), '',
        'These sums use reported input weights. Effective native motif denominators remain separate.', '',
        _table(('Series', 'Role', 'Captured occurrences', 'Selected occurrences',
            'Capture state', 'Native outcome'), [
            (series_labels[count['series_id']], count['role'], count['captured_occurrences'],
                count['selected_occurrences'], count['capture_state'], count['native_outcome'])
            for count in packet['counts']])]
    for series in packet['selected_series']:
        parts.extend(['', series_labels[series['series_id']] + ': ' + series['role'], '',
            _table(('Series property', 'Retained value'), [
                ('Phase', series['phase']), ('Capture state', series['capture_state']),
                ('Native outcome', series['native_outcome']),
                ('Original column headings', _molecular_literal(series['raw_header'])),
                ('Qualifications', _molecular_literal(series['issues']))]), '',
            'Wrapper display totals inferred from the first rounded motif', '',
            _table(('Group', 'Native token', 'Value', 'State'), [
                (group, None if series['displayed_totals'][group] is None else
                    series['displayed_totals'][group]['raw_token'],
                    None if series['displayed_totals'][group] is None else
                    series['displayed_totals'][group]['value'],
                    'not_provided' if series['displayed_totals'][group] is None else
                    series['displayed_totals'][group]['state'])
                for group in ('target', 'background')])])
        for occurrence in series['observations']:
            parts.extend(['', 'Original motif occurrence ' + str(occurrence['ordinal_0based']), '',
                _table(('Property', 'Retained value'), [
                    ('Name', occurrence['name']), ('Consensus', occurrence['consensus']),
                    ('Parse state', occurrence['parse_state']), ('PWM state', occurrence['pwm_state']),
                    ('Qualifications', _molecular_literal(occurrence['issues']))])])
            if occurrence['parse_state'] in ('malformed', 'truncated'):
                parts.extend(['', 'Original fields: ' + _molecular_literal(occurrence['raw_fields'])])
            for representation in occurrence['representations']:
                parts.extend(['', 'Native representation: ' + representation['kind'], '',
                    _table(('Measurement', 'Availability', 'Native token', 'Value', 'State', 'Token kind', 'Unit',
                        'Print precision'), [
                        (field, cell['availability'],
                            None if cell['number'] is None else cell['number']['raw_token'],
                            None if cell['number'] is None else cell['number']['value'],
                            'not_provided' if cell['number'] is None else cell['number']['state'],
                            'not_provided' if cell['number'] is None else cell['number']['token_kind'],
                            cell['unit'], cell['precision'])
                        for field, cell in representation['numbers'].items()]), '',
                    _table(('Representation property', 'Retained value'), [
                        ('Native gap field', representation['native_gap_field']),
                        ('Additional native fields', _molecular_literal(representation['extra_fields'])),
                        ('Unreported auxiliary fields', _molecular_literal(
                            representation['native_auxiliary_absent_fields'])),
                        ('Qualifications', _molecular_literal(representation['issues']))])])
                if representation['pwm_rows']:
                    parts.extend(['', 'Ordered PWM rows; native column order A, C, G, T', '',
                        _table(('Original row', 'Native tokens in original order', 'Cell states'), [
                            (row['ordinal_0based'], _molecular_literal(row['raw_fields']),
                                _molecular_literal([cell['state'] for cell in row['cells']]))
                            for row in representation['pwm_rows']])])
                for auxiliary in representation['native_auxiliary_measurements']:
                    number_cell = auxiliary['reported']
                    parts.extend(['', 'Native auxiliary measurement: ' + auxiliary['field'], '',
                        _table(('Property', 'Retained value'), [
                            ('Original field', auxiliary['raw_field']),
                            ('Extra field ordinal', auxiliary['extra_field_ordinal_0based']),
                            ('Token ordinal', auxiliary['token_ordinal_0based']),
                            ('Native token', number_cell['number']['raw_token']),
                            ('Value', number_cell['number']['value']),
                            ('State', number_cell['number']['state']),
                            ('Unit', number_cell['unit']), ('Print precision', number_cell['precision']),
                            *((field, _molecular_literal(auxiliary[field]) if field == 'qualifications'
                                else auxiliary[field]) for field in ('definition', 'population',
                                    'coordinate_origin', 'weighting', 'denominator', 'qualifications'))])])
    parts.extend(['', 'Result qualifications: ' + _molecular_literal(packet['issues'])])
    return '\n'.join(parts)


