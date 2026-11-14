"""Requested comparison text and relevance; no source IO or scientific calculation."""
from collections.abc import Mapping
from copy import deepcopy

from .literature_measurement_comparison_prompt import MEASUREMENT_COMPARISON_TASK
from .literature_measurement_comparison_storage import NAMESPACE, REQUESTED, VIEW, SCOPE, POPULATION, OPERATION


def is_row(value):
    return (isinstance(value, Mapping) and value.get('row_version') == 'measurement_comparison_return_v2'
        and value.get('evaluation_scope') == SCOPE)


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
    choice = record.get('selection') if isinstance(record, Mapping) else None
    arguments = choice.get('arguments') if isinstance(choice, Mapping) else None
    return (isinstance(choice, Mapping) and choice.get('tool') == OPERATION
        and isinstance(arguments, Mapping) and arguments.get('version') == POPULATION)


def any_history(value):
    if isinstance(value, Mapping):
        return history_record(value) or any(any_history(child) for child in value.values())
    return isinstance(value, (list, tuple)) and any(any_history(child) for child in value)


def task_relevant(state):
    assignment = state.get('literature_assignment') or {}
    outcome = state.get('last_local_outcome') or {}
    selected_here = isinstance(outcome, Mapping) and outcome.get('selected_tool') == OPERATION
    return (REQUESTED in assignment or selected_here or bool(state.get('literature_measurement_comparison_work'))
        or any(rows_from_values((state.get('last_local_outcome'), state.get('child_reports'), state.get('current_report_update'))))
        or any(node.get('x-source') == NAMESPACE or node.get('$ref') == 'episode-fact:'+NAMESPACE
            for node in (state.get('requested_form') or {}).get('properties', {}).values()))


def lookup_relevant(value):
    result = value.get('result') if isinstance(value, Mapping) else None
    return (bool(list(rows_from_values(value))) or any_history(value)
        or isinstance(result, Mapping) and (
            result.get('information_kind') == 'return_contract_information_v1' and result.get('source') == NAMESPACE
            or result.get('information_kind') == 'operation_contract_information_v1' and result.get('operation') == OPERATION))


def hidden_records(rows, records, bindings=None):
    locations = [loc for row in rows for loc in row['withheld_locations']]
    sources = set(bindings or {})
    artifacts = {ref for binding in (bindings or {}).values() for ref in binding['artifacts']}
    hidden = set()
    for ref, record in records.items():
        for anchor in (record, record.get('anchor'), record.get('visual_anchor')):
            if not isinstance(anchor, Mapping):
                continue
            if anchor.get('source_ref') in sources or anchor.get('artifact_ref') in artifacts:
                hidden.add(ref)
            if any(anchor.get('artifact_ref') == loc['artifact_ref'] and type(anchor.get('start')) is int
                    and type(anchor.get('end')) is int and anchor['start'] < loc['end'] and loc['start'] < anchor['end']
                    for loc in locations):
                hidden.add(ref)
    return hidden


def _meaning(value):
    return value.replace('_', ' ') if isinstance(value, str) else value


def render_received(parts, rows, *, section, table):
    groups, seen = {}, set()
    for row in rows:
        key = row['sheet_ref'], row['component']
        if key not in seen:
            seen.add(key)
            groups.setdefault(row['sheet_ref'], []).append(row)
    for index, selected in enumerate(groups.values(), 1):
        section(parts, 'Source comparison scope '+str(index), table(
            ('Source kind', 'Assertion question', 'Actual input origins'),
            list(dict.fromkeys((_meaning(r['source_kind']), _meaning(r['assertion_question']),
                ', '.join(_meaning(v) for v in r['cell']['input_origins'])) for r in selected))))
        assertion_context = list(dict.fromkeys((name, '; '.join(f['text'] for f in item['fragments'])
            or _meaning(item['status'])) for r in selected for name, item in r['assertion_context'].items()))
        section(parts, 'Studied molecule and functional assertion', table(('Meaning', 'Selected source information'),
            [(_meaning(name), value) for name, value in assertion_context]))
        section(parts, 'Requested measurement comparison '+str(index), table(
            ('Component', 'Ordinary value', 'Conditional value', 'Unit', 'Status', 'Bound', 'Approximate', 'Meaning'),
            [(_meaning(r['component']), r['cell']['value'], r['cell']['conditional_value'], r['cell']['unit'],
                _meaning(r['cell']['status']), r['cell']['relation'], r['cell']['approximate'],
                _meaning(r['cell']['interpretation'])) for r in selected]))
        meanings, contexts, conditions = [], [], []
        shown_meanings, shown_contexts, shown_conditions = set(), set(), set()
        for row in selected:
            for meaning in row['role_meanings']:
                fact = tuple(meaning[k] for k in ('role', 'quantity_kind', 'estimator_scale', 'semantics',
                    'normalization', 'qualification', 'reported_uncertainty_statistic'))
                if fact not in shown_meanings:
                    shown_meanings.add(fact)
                    meanings.append(tuple(_meaning(v) for v in fact))
                for context in meaning['contexts']:
                    fragments = '; '.join(f['text'] for f in context['fragments'])
                    key = meaning['role'], context['field'], context['status'], fragments
                    # Keep requested source facts and essential missing subject/
                    # endpoint meaning; do not repeat every optional blank slot.
                    essential = context['field'] in ('subject.organism', 'subject.molecule', 'subject.construct',
                        'subject.arrangement', 'assay.preparation', 'assay.direct_endpoint', 'assay.denominator',
                        'assay.conditions', 'assay.fit_basis', 'assay.intended_change', 'assay.additional_differences')
                    if key not in shown_contexts and (fragments or essential):
                        shown_contexts.add(key)
                        contexts.append((_meaning(key[0]), _meaning(key[1]), fragments or _meaning(key[2])))
            for relationship in row['relationships']:
                fact = relationship['name'], relationship['value']
                if fact not in shown_conditions:
                    shown_conditions.add(fact)
                    conditions.append(tuple(_meaning(v) for v in fact))
            for condition in row['model_conditions']:
                fact = condition['name'], condition['state']
                if fact not in shown_conditions:
                    shown_conditions.add(fact)
                    conditions.append(tuple(_meaning(v) for v in fact))
            for conversion in row['conversion_conditions']:
                fact = ('conversion '+conversion['role'], conversion['kind']+'; '+conversion['direction']+'; '+conversion['support_status'])
                if fact not in shown_conditions:
                    shown_conditions.add(fact)
                    conditions.append(tuple(_meaning(v) for v in fact))
        if meanings:
            section(parts, 'Reported quantity meanings', table(
                ('Role', 'Quantity', 'Estimator scale', 'Source semantics', 'Normalization', 'Qualification', 'Reported spread kind'), meanings))
        if contexts:
            section(parts, 'Selected assayed subjects and experimental context', table(('Role', 'Meaning', 'Source information'), contexts))
        if conditions:
            section(parts, 'Comparison and model conditions', table(('Meaning', 'Received condition'), conditions))
        section(parts, 'Requested comparison limitations', table(
            ('Component', 'Source missingness', 'Relationship limits', 'Implementation limits', 'Domain limits', 'Covariance status', 'Uncertainty scope'),
            [(_meaning(r['component']), *('; '.join(_meaning(code) for code in r['cell']['reasons'][kind])
                for kind in ('source', 'relationship', 'implementation', 'domain')),
                _meaning(r['cell']['uncertainty']['variance_status']), _meaning(r['cell']['uncertainty']['scope'])) for r in selected]))
        assumptions = list(dict.fromkeys(a for r in selected for a in r['assumptions']))
        if assumptions:
            section(parts, 'Applicable calculation assumptions', '; '.join(_meaning(a) for a in assumptions))
        provenance = list(dict.fromkeys(tuple(block[k] for k in ('basis', 'variance_status', 'origin',
            'systematic_coverage', 'derivation', 'status')) for r in selected for block in r['covariance_provenance']))
        if provenance:
            section(parts, 'Selected covariance meaning', table(
                ('Basis', 'Variance status', 'Origin', 'Systematic coverage', 'Derivation', 'Availability'),
                [tuple(_meaning(v) for v in row) for row in provenance]))
        dependence = list(dict.fromkeys((', '.join(d['roles']), d['relation']) for r in selected for d in r['dependence']))
        if dependence:
            section(parts, 'Recorded measurement relationships', table(('Roles', 'Relationship'),
                [(roles, _meaning(relation)) for roles, relation in dependence]))
        settings = list(dict.fromkeys((name, value) for r in selected for name, value in r['model_settings'].items()
            if value is not None and value != 'not_selected'))
        if settings:
            section(parts, 'Applicable model settings', table(('Meaning', 'Setting'),
                [(_meaning(name), _meaning(value)) for name, value in settings]))
        section(parts, 'Contribution meaning',
            'Native, converted and compared values retain their shared measurements. '
            'A descriptive protocol comparison does not establish a common-condition estimate. '
            'Conditional values retain their declared premises; optical readout correction does not by itself isolate molecular catalysis. '
            'Reported spread does not supply joint covariance, and no function probability or target-transfer weight is inferred.')


def sanitize_private(value, bindings):
    if not bindings:
        return dict(value) if isinstance(value, Mapping) else value
    sources = set(bindings)
    artifacts = {ref for binding in bindings.values() for ref in binding['artifacts']}
    def copy(item):
        if is_row(item):
            return deepcopy(item)
        if isinstance(item, Mapping):
            anchored = any(isinstance(a, Mapping) and (
                isinstance(a.get('source_ref'), str) and a['source_ref'] in sources
                or isinstance(a.get('artifact_ref'), str) and a['artifact_ref'] in artifacts)
                for a in (item, item.get('anchor'), item.get('visual_anchor')))
            if anchored and ('text' in item or 'anchor' in item or 'visual_anchor' in item):
                return {'scientific_meaning': 'Private comparison receipt; use the requested typed components.'}
            return {key: copy(child) for key, child in item.items()}
        if isinstance(item, (tuple, list)):
            return [copy(child) for child in item]
        return item
    return copy(value)


def state_view(state, lookup_results=()):
    shown = sanitize_private(state, state.get('literature_measurement_comparison_receipt_bindings', {}))
    if any(lookup_relevant(value) for value in lookup_results):
        shown['literature_measurement_comparison_work'] = {'version': 'literature_measurement_comparison_task_v1'}
    return shown
