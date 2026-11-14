"""Pure scoped endpoint text: exact received numbers and scientific meanings."""
from collections.abc import Mapping
from copy import deepcopy

from .literature_endpoint_signal_prompt import ENDPOINT_SIGNAL_TASK
from .literature_endpoint_signal_storage import SCOPE, REQUESTED, VIEW, VERSION, NAMESPACE


def is_row(value):
    return isinstance(value, Mapping) and value.get('evaluation_scope') == SCOPE and value.get('row_version') == 'endpoint_signal_return_v1' and 'component' in value


def rows_from_values(value):
    if is_row(value):
        yield value
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from rows_from_values(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from rows_from_values(child)


def rows_from_reports(reports):
    yield from rows_from_values(reports)


def task_relevant(state):
    return (bool(state.get('literature_assignment', {}).get(REQUESTED))
        or state.get('literature_endpoint_signal_work', {}).get('version') == 'literature_endpoint_signal_task_v1'
        or any(rows_from_values((state.get('last_local_outcome'), state.get('child_reports'), state.get('current_report_update'))))
        or any(node.get('x-source') == NAMESPACE for node in (state.get('requested_form') or {}).get('properties', {}).values()))


def legacy_task_relevant(state):
    if state.get('literature_legacy_figure_contract_work'):
        return True
    if not task_relevant(state):
        return True
    def walk(value):
        if isinstance(value, Mapping):
            if value.get('evaluation_scope') == 'reference_experimental_figure_ordinates':
                return True
            return any(walk(child) for child in value.values())
        return isinstance(value, (list, tuple)) and any(walk(child) for child in value)
    return bool(state.get('literature_assignment', {}).get('requested_figure_components')) or walk((state.get('last_local_outcome'), state.get('child_reports')))


def lookup_relevant(outcome):
    result = outcome.get('result', {}) if isinstance(outcome, Mapping) else {}
    if not isinstance(result, Mapping):
        return bool(list(rows_from_values(outcome)))
    return (bool(list(rows_from_values(outcome))) or result.get('information_kind') == 'return_contract_information_v1'
        and result.get('source') == NAMESPACE or result.get('information_kind') == 'operation_contract_information_v1'
        and result.get('operation') == 'literature.figure.populate')


def endpoint_history_record(record):
    selection = record.get('selection') if isinstance(record, Mapping) else None
    arguments = selection.get('arguments') if isinstance(selection, Mapping) else None
    return (isinstance(selection, Mapping) and selection.get('tool') == 'literature.figure.populate'
        and isinstance(arguments, Mapping) and arguments.get('version') == 'literature_figure_endpoint_signal_population_v1')


def hidden_records(rows, records, bindings=None):
    locations = [loc for row in rows for loc in row['withheld_locations']]
    images = {ref for row in rows for ref in row['withheld_image_source_refs']}
    private_sources = set(bindings or {})
    private_artifacts = {ref for value in (bindings or {}).values() for ref in value['artifacts']}
    hidden = set()
    for ref, record in records.items():
        for anchor in (record, record.get('anchor'), record.get('visual_anchor')):
            if not isinstance(anchor, Mapping):
                continue
            if anchor.get('source_ref') in private_sources or anchor.get('artifact_ref') in private_artifacts:
                hidden.add(ref)
            if anchor is not record and anchor.get('source_ref') in images:
                hidden.add(ref)
            if any(anchor.get('artifact_ref') == loc['artifact_ref']
                    and type(anchor.get('start')) is int and type(anchor.get('end')) is int
                    and anchor['start'] < loc['end'] and loc['start'] < anchor['end'] for loc in locations):
                hidden.add(ref)
    return hidden


def _exact(value):
    if value is None:
        return 'unknown'
    return value['numerator'] if value['denominator'] == '1' else value['numerator']+'/'+value['denominator']


def render_received(parts, rows, *, section, table):
    groups, seen = {}, set()
    for row in rows:
        key = row['sheet_ref'], row['component']
        if key not in seen:
            seen.add(key); groups.setdefault(row['sheet_ref'], []).append(row)
    for index, selected in enumerate(groups.values(), 1):
        first = selected[0]
        section(parts, 'Endpoint signal evidence '+str(index), table(('Scientific meaning', 'Selected source information'),
            [(name, '; '.join(f['text'] for f in value['fragments']) or value['status']) for name, value in first['source_context'].items()]))
        section(parts, 'Requested endpoint components', table(
            ('Component', 'Ordinary value', 'Conditional value', 'Unit', 'Status', 'Reading enclosure'),
            [(r['component'], r['value'] if r['value'] is not None else _exact(r['exact_value']),
                r['conditional_value'] if r['conditional_value'] is not None else _exact(r['conditional_exact_value']),
                r['unit'], r['status'], '['+_exact(r['exact_lower'])+', '+_exact(r['exact_upper'])+']'
                    if r['exact_lower'] is not None else 'none') for r in selected]))
        section(parts, 'Endpoint interpretation and limitations', table(('Meaning', 'Received qualifier'),
            [(name, value['value']) for name, value in first['relationships'].items()]+
            [('sampling window', first['sampling_window']), ('molecular attribution', first['molecular_attribution']),
             ('functional relevance', first['functional_relevance']), ('physical preparation count', 'not extracted')]))
        section(parts, 'Requested endpoint qualifications', table(('Component', 'Assumptions', 'Unavailable reasons', 'Qualifications'),
            [(r['component'], ', '.join(r['conditional_on']), ', '.join(r['unavailable_reasons']), ', '.join(r['qualifications'])) for r in selected]))
        uncertainty = first['uncertainty']
        section(parts, 'Endpoint uncertainty meaning', table(('Meaning', 'Received qualifier'),
            [(name, uncertainty[name]) for name in ('availability', 'basis', 'variance_status', 'origin',
                'coordinate_units_status', 'physical_uncertainty', 'published_ratio_uncertainty')]))
        section(parts, 'Endpoint dependence',
            'Total = corrected + additional; corrected = retained fraction × total; additional fraction = 1 − retained fraction. '
            'These are dependent views of the same selected trace and shared initial reading. '
            'The amplitude is not an initial-rate g, the reading enclosure is not a confidence interval, '
            'and the fraction is not assay reliability or a function probability.')


def state_view(state, lookup_results=()):
    shown = sanitize_private(state, state.get('literature_endpoint_receipt_bindings', {}))
    if any(lookup_relevant(row) for row in lookup_results):
        shown['literature_endpoint_signal_work'] = {'version': 'literature_endpoint_signal_task_v1'}
    if any(isinstance(row, Mapping) and isinstance(row.get('result'), Mapping)
            and row['result'].get('information_kind') == 'operation_contract_information_v1'
            and row['result'].get('operation') == 'literature.figure.populate' for row in lookup_results):
        shown['literature_legacy_figure_contract_work'] = True
    return shown


def sanitize_private(value, bindings):
    """Keep implementation receipt bytes/aliases out of scientific text views.

    This changes presentation only; selected API access/ownership is separately
    enforced before the literature service returns its actual outcome.
    """
    if not bindings:
        return dict(value) if isinstance(value, Mapping) else value
    sources = set(bindings)
    artifacts = {ref for binding in bindings.values() for ref in binding['artifacts']}
    def copy(item):
        if is_row(item):
            return deepcopy(item)
        if isinstance(item, Mapping):
            anchored = any(isinstance(anchor, Mapping) and (type(anchor.get('source_ref')) is str and anchor['source_ref'] in sources
                or type(anchor.get('artifact_ref')) is str and anchor['artifact_ref'] in artifacts)
                for anchor in (item, item.get('anchor'), item.get('visual_anchor')))
            if anchored and ('text' in item or 'anchor' in item or 'visual_anchor' in item):
                return {**{key: item[key] for key in ('id', 'record_type', 'source_ref') if key in item},
                    'scientific_meaning': 'Private endpoint implementation custody; use the requested typed numerical projection.'}
            return {key: copy(child) for key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [copy(child) for child in item]
        return item
    return copy(value)


__all__ = ['ENDPOINT_SIGNAL_TASK', 'is_row', 'rows_from_values', 'rows_from_reports', 'task_relevant',
    'legacy_task_relevant', 'lookup_relevant', 'hidden_records', 'render_received', 'state_view', 'sanitize_private',
    'endpoint_history_record']
