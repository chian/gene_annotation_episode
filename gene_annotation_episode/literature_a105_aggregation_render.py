"""Display admitted A105 aggregate values and their actual experiment inputs."""
from collections.abc import Mapping


def render_received(parts, rows, *, section, table):
    groups = {}
    for row in rows:
        if not isinstance(row, Mapping) or row.get('evaluation_scope') != 'a105_across_experiment_aggregation':
            raise ValueError('a105_aggregation_display_contract_mismatch')
        groups.setdefault(row['sheet_ref'], []).append(row)
    for selected in groups.values():
        section(parts, 'A105 combined experiment scores', table(
            ('Metric', 'Operation', 'Complete value', 'Available partial value', 'Status', 'Unit'),
            [(row['component'], row['reducer'], row['value'],
              row['available_value'] if row['status'] != 'complete' else 'not needed',
              row['status'], row['unit']) for row in selected]))
        experiment_labels = {}
        for row in selected:
            for reference in row['selected_experiment_refs']:
                experiment_labels.setdefault(reference, len(experiment_labels) + 1)
        contributions = []
        for row in selected:
            for source in row['selected_components']:
                contributions.append((row['component'], experiment_labels[source['experiment_ref']],
                    source['component'], source['value'], source['unit'], source['status'], source['meaning']))
            for reference in row['missing_experiment_refs']:
                contributions.append((row['component'], experiment_labels[reference],
                    'missing numerical score', None, 'unknown', 'unavailable', 'No zero value substituted.'))
        section(parts, 'Retained experiment contributions', table(
            ('Metric', 'Experiment', 'Selected component', 'Value', 'Unit', 'Status', 'Meaning'), contributions))
        section(parts, 'A105 combination rule',
            'Reliability, validity and overall use ordinary sums. Relevance and attribution use ordinary maxima. '
            'The combination applies no weights, normalization or orthogonality adjustment. '
            'Partial available values do not fill missing complete values. '
            'Source component meanings remain unchanged; this is not final annotation credit.')


__all__ = ['render_received']
