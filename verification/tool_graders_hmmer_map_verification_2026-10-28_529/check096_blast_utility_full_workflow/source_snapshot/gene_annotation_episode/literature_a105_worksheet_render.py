"""Group admitted A105 numerical sections and constrained relationships.

Only form rows and the supplied public-record mapping are available here.
This renderer neither validates/recalculates science nor fetches private data.
"""
from collections.abc import Mapping

from . import literature_calibration_recovery_render as recovery
from . import literature_compiled_assay_render as compiled
from . import literature_endpoint_signal_render as endpoint
from . import literature_kinetic_summary_precision_render as summary
from . import literature_measurement_comparison_render as comparison
from . import literature_concentration_window_render as concentration
from . import literature_product_coupling_render as coupling
from .literature_a105_worksheet import VERSION


def _native(parts, rows, records, hidden, *, section, table):
    """Native adapter: use only actual delivered roles and public safe labels."""
    groups = {}
    for row in rows:
        groups.setdefault(row['sheet_ref'], []).append(row)

    def label(reference):
        if reference is None:
            return 'unknown'
        record = records.get(reference)
        if not isinstance(record, Mapping):
            return 'source meaning not delivered'
        anchor = record.get('anchor')
        if not isinstance(anchor, Mapping) or any(
                anchor.get('artifact_ref') == loc.get('artifact_ref')
                and type(anchor.get('start')) is int and type(anchor.get('end')) is int
                and anchor['start'] < loc['end'] and loc['start'] < anchor['end'] for loc in hidden):
            return 'source-bound meaning retained for scoped access'
        return record.get('label', 'source meaning not delivered')

    for selected in groups.values():
        section(parts, 'Requested native kinetic components', table(
            ('Component', 'Value', 'Unit', 'Status', 'Relation', 'Threshold', 'Approximate', 'Unavailable reason', 'Origin'),
            [(r['component'], r['value'], r['unit'], r['status'], r['relation'], r['threshold'],
                r['approximate'], r['unavailable_reason'], r['origin']) for r in selected]))
        first = selected[0]
        section(parts, 'Native kinetic experimental relationships', table(('Meaning', 'Selected interpretation'),
            [(name, value['value']) for name, value in first['comparison'].items()]))
        # Both roles' metadata can be delivered with a contrast. Only the exact
        # requested role_parameter row delivers that role's numeric uncertainty.
        for role in ('numerator', 'denominator'):
            metadata = first[role]
            if metadata['parameter_kind'] == 'unknown' and metadata['measurement_ref'] is None:
                continue
            section(parts, role.capitalize() + ' parameter meaning', table(('Meaning', 'Value'),
                [(name, metadata[name]) for name in ('parameter_kind', 'canonical_unit', 'qualification',
                    'input_status', 'observed_relation', 'source_origin', 'converted_origin')]))
            section(parts, role.capitalize() + ' subject and experimental context', table(('Meaning', 'Source definition'),
                [(name, label(ref)) for group in ('subject', 'context') for name, ref in metadata[group].items()]))
            uncertainty = metadata['uncertainty']
            section(parts, role.capitalize() + ' uncertainty meanings', table(('Meaning', 'Value'),
                [(name, uncertainty[name]) for name in ('statistic', 'canonical_unit', 'repetition_basis',
                    'estimate_basis', 'count_reading_status', 'count_relation', 'count_approximate', 'unavailable_reason')]))
            for row in selected:
                values = row[role]['uncertainty_values']
                if row['component'] == role + '_parameter' and values['delivery_status'] == 'requested':
                    section(parts, role.capitalize() + ' requested uncertainty values', table(('Quantity', 'Value'),
                        [(name, values[name]) for name in ('magnitude', 'interval', 'confidence_level', 'count', 'count_reported_value')]))


def render_a105_worksheet(parts, form, *, section, table, public_records):
    """Render one already-admitted ordinary worksheet using existing sections.

    Returns None. The caller still owns rendering other ordinary form content
    and the separate full TASK and ordinary own-action/yield table.
    """
    if not isinstance(form, Mapping):
        return
    contexts = [v for v in form.values() if isinstance(v, Mapping) and v.get('version') == VERSION]
    if len(contexts) != 1:
        return
    context = contexts[0]
    records = public_records if isinstance(public_records, Mapping) else {}
    fields = [(field, value) for field, value in form.items() if isinstance(value, (tuple, list))]
    hidden = [loc for _, rows in fields for row in rows if isinstance(row, Mapping)
        for loc in row.get('withheld_locations', ())]
    unknown_sources = set()
    for _, rows in fields:
        for row in rows:
            if not isinstance(row, Mapping) or row.get('evaluation_scope') != 'source_kinetic_parameter_contrast':
                continue
            for role in ('numerator', 'denominator'):
                for token in row[role]['numeric_tokens']:
                    record = records.get(token['ref'], {})
                    anchor = record.get('anchor')
                    if isinstance(anchor, Mapping):
                        hidden.append(anchor)
                    else:
                        unknown_sources.add(token['source_ref'])
    # Missing numeric anchors cannot permit a broader neighboring quote.
    safe_records = {ref: record for ref, record in records.items() if isinstance(record, Mapping)
        and not (isinstance(record.get('anchor'), Mapping) and record['anchor'].get('source_ref') in unknown_sources)}
    section(parts, 'A105 experimental evidence worksheet',
        'Requested numerical sections retain their own experimental and uncertainty meanings. '
        'Shared reports and calculated views do not supply additional independent assays.')
    selectors = {}
    for number, (field, rows) in enumerate(fields, 1):
        if not rows:
            continue
        sheet_labels = {}
        for row in rows:
            sheet_labels.setdefault(row['sheet_ref'], len(sheet_labels) + 1)
            selectors[(field, row['sheet_ref'], row['component'])] = (
                'section ' + str(number) + ', returned set ' + str(sheet_labels[row['sheet_ref']])
                + ', ' + row['component'].replace('_', ' '))
        section(parts, 'Worksheet section ' + str(number) + ': ' + field.replace('_', ' '), '')
        scope = rows[0]['evaluation_scope']
        if scope == 'source_kinetic_parameter_contrast':
            _native(parts, rows, safe_records, hidden, section=section, table=table)
        elif scope == 'source_kinetic_summary_precision':
            summary.render_received(parts, rows, section=section, table=table)
        elif scope == 'source_concentration_window':
            concentration.render_received(parts, rows, section=section, table=table)
        elif scope == 'source_measurement_comparison':
            comparison.render_received(parts, rows, section=section, table=table)
        elif scope == 'source_endpoint_signal_contribution':
            endpoint.render_received(parts, rows, section=section, table=table)
        elif scope == 'source_product_coupling':
            coupling.render_received(parts, rows, section=section, table=table)
        elif scope == 'source_calibration_recovery':
            recovery.render_received(parts, rows, section=section, table=table)
        elif scope in ('compiled_source_endpoint', 'common_assertion_contrast'):
            compiled.render_received(parts, rows, section=section, table=table)

    def selected(value):
        key = tuple(value[k] for k in ('field', 'sheet_ref', 'component'))
        return selectors.get(key, 'quantity not delivered') + ' / ' + value['quantity'].replace('_', ' ')

    relation_meanings = {
        'same_reported_parameter': 'same original parameter report; dependent views',
        'same_reported_spread': 'same original spread report; dependent views',
        'same_count_report': 'same original count report; preserves repetition meaning',
        'conditional_precision_of_report': 'conditional precision of this report under stated premises',
        'unresolved': 'relationship unresolved; no independence or equality inferred',
        'conflicting': 'conflicting delivered support retained',
    }
    if context['quantity_links']:
        section(parts, 'Relationships between requested quantities', table(('First quantity', 'Second quantity', 'Meaning'),
            [(selected(link['left']), selected(link['right']), relation_meanings[link['relation']])
                for link in context['quantity_links']]))
    assertions = {ref: 'assertion ' + str(i) for i, ref in enumerate(context['assertion_refs'], 1)}
    if context['assertion_links']:
        section(parts, 'Bearing on the selected functional assertions', table(('Quantity', 'Assertion', 'Interpretation'),
            [(selected(link['selector']), assertions.get(link['assertion_ref'], 'not established'),
                link['relation'].replace('_', ' ')) for link in context['assertion_links']]))


__all__ = ['render_a105_worksheet']
