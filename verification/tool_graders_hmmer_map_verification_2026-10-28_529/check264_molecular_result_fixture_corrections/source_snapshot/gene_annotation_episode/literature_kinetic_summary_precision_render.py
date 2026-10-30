"""Pure requested summary-precision text; no source reading or calculation."""
from collections.abc import Mapping
from copy import deepcopy

from .literature_kinetic_summary_precision_prompt import KINETIC_SUMMARY_PRECISION_TASK
from .literature_kinetic_summary_precision_storage import NAMESPACE, REQUESTED, VIEW, SCOPE, POPULATION


def is_row(value):
    return isinstance(value, Mapping) and value.get('row_version') == 'kinetic_summary_precision_return_v1' and value.get('evaluation_scope') == SCOPE


def rows_from_values(value):
    if is_row(value):
        yield value
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from rows_from_values(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from rows_from_values(child)


def history_record(record):
    selection = record.get('selection') if isinstance(record, Mapping) else None
    args = selection.get('arguments') if isinstance(selection, Mapping) else None
    return isinstance(selection, Mapping) and selection.get('tool') == 'literature.kinetic.populate' and isinstance(args, Mapping) and args.get('version') == POPULATION


def task_relevant(state):
    return bool(state.get('literature_assignment', {}).get(REQUESTED)) or bool(state.get('literature_kinetic_summary_precision_work')) or any(rows_from_values((state.get('last_local_outcome'), state.get('child_reports'), state.get('current_report_update')))) or any(
        n.get('x-source') == NAMESPACE for n in (state.get('requested_form') or {}).get('properties', {}).values())


def legacy_task_relevant(state):
    if not task_relevant(state) or state.get('literature_kinetic_union_contract_work'):
        return True
    if state.get('literature_assignment', {}).get('requested_kinetic_components') or state.get('literature_assignment', {}).get('requested_kinetic_model_components'):
        return True
    def walk(value):
        if isinstance(value, Mapping):
            return value.get('evaluation_scope') == 'source_kinetic_parameter_contrast' or any(walk(v) for v in value.values())
        return isinstance(value, (tuple, list)) and any(walk(v) for v in value)
    return walk((state.get('last_local_outcome'), state.get('child_reports')))


def lookup_relevant(value):
    result = value.get('result') if isinstance(value, Mapping) else None
    return bool(list(rows_from_values(value))) or any_history(value) or isinstance(result, Mapping) and (
        result.get('information_kind') == 'return_contract_information_v1' and result.get('source') == NAMESPACE
        or result.get('information_kind') == 'operation_contract_information_v1' and result.get('operation') == 'literature.kinetic.populate')


def any_history(value):
    if isinstance(value, Mapping):
        return history_record(value) or any(any_history(v) for v in value.values())
    return isinstance(value, (list, tuple)) and any(any_history(v) for v in value)


def hidden_records(rows, records, bindings=None):
    locations = [loc for row in rows for loc in row['withheld_locations']]
    sources = set(bindings or {})
    artifacts = {ref for b in (bindings or {}).values() for ref in b['artifacts']}
    result = set()
    for ref, record in records.items():
        for anchor in (record, record.get('anchor'), record.get('visual_anchor')):
            if not isinstance(anchor, Mapping):
                continue
            if anchor.get('source_ref') in sources or anchor.get('artifact_ref') in artifacts:
                result.add(ref)
            if any(anchor.get('artifact_ref') == loc['artifact_ref'] and type(anchor.get('start')) is int
                    and type(anchor.get('end')) is int and anchor['start'] < loc['end'] and loc['start'] < anchor['end']
                    for loc in locations):
                result.add(ref)
    return result


def render_received(parts, rows, *, section, table):
    seen = set(); selected = []
    for row in rows:
        key = row['sheet_ref'], row['component']
        if key not in seen:
            seen.add(key); selected.append(row)
    if not selected:
        return
    section(parts, 'Requested kinetic summary precision', table(
        ('Population', 'Component', 'Value', 'Unit', 'Status', 'Qualification', 'Origin', 'Approximate', 'Unavailable reason'),
        [(r['population'], r['cell_name'], r['cell']['value'], r['cell']['unit'], r['cell']['status'],
            r['cell']['qualification'], r['cell']['origin'], r['cell']['approximate'], r['cell']['unavailable_reason']) for r in selected]))
    meanings, meaning_seen = [], set()
    for row in selected:
        basis = row['sampling_basis']
        meaning = (row['source_kind'], row['parameter_kind'], basis['source_count_meaning'],
            basis['repetition_basis'], basis['estimate_basis'])
        if meaning not in meaning_seen:
            meaning_seen.add(meaning); meanings.append(meaning)
    section(parts, 'Source and sampling meanings', table(
        ('Source kind', 'Parameter', 'Reported count meaning', 'Repetition basis', 'Estimate basis'), meanings))
    section(parts, 'Selected summary precision conditions', table(
        ('Population', 'Component', 'Source condition states', 'Calculation premises', 'Explicit stipulations'),
        [(r['population'], r['cell_name'], '; '.join(c['condition']+'='+c['state'] for c in r['model_conditions']),
            ', '.join(r['cell']['conditional_on']), ', '.join(r['cell']['stipulated_assumptions'])) for r in selected]))
    contexts, shown = [], set()
    for row in selected:
        for name, value in row['source_context'].items():
            for fragment in value['fragments']:
                key = name, fragment['text']
                if key not in shown:
                    shown.add(key); contexts.append(key)
    if contexts:
        section(parts, 'Selected source identity and experimental context', table(('Meaning', 'Source fragment'), contexts))
    section(parts, 'Summary precision meaning',
        'Sample-derived variance and SE estimate random mean precision. Source facts and explicit scenarios remain separate. '
        'SD, counts, variance, SE and interval parameters describe dependent views of one summary contribution; '
        'they are not additional experiments. Shared calibration and systematic uncertainty remain unknown.')


def sanitize_private(value, bindings):
    if not bindings:
        return dict(value) if isinstance(value, Mapping) else value
    sources = set(bindings)
    artifacts = {ref for binding in bindings.values() for ref in binding['artifacts']}
    def copy(item):
        if is_row(item):
            return deepcopy(item)
        if isinstance(item, Mapping):
            anchored = any(isinstance(a, Mapping) and (isinstance(a.get('source_ref'), str) and a['source_ref'] in sources
                or isinstance(a.get('artifact_ref'), str) and a['artifact_ref'] in artifacts)
                for a in (item, item.get('anchor'), item.get('visual_anchor')))
            if anchored and ('text' in item or 'anchor' in item or 'visual_anchor' in item):
                return {'scientific_meaning': 'Private summary precision custody; use the requested typed cells.'}
            return {k: copy(v) for k, v in item.items()}
        if isinstance(item, (tuple, list)):
            return [copy(v) for v in item]
        return item
    return copy(value)


def state_view(state, lookup_results=()):
    shown = sanitize_private(state, state.get('literature_summary_precision_receipt_bindings', {}))
    if any(lookup_relevant(v) for v in lookup_results):
        shown['literature_kinetic_summary_precision_work'] = {'version': 'literature_summary_precision_task_v1'}
    if any(isinstance(v, Mapping) and isinstance(v.get('result'), Mapping)
            and v['result'].get('information_kind') == 'operation_contract_information_v1'
            and v['result'].get('operation') == 'literature.kinetic.populate' for v in lookup_results):
        shown['literature_kinetic_union_contract_work'] = True
    return shown
