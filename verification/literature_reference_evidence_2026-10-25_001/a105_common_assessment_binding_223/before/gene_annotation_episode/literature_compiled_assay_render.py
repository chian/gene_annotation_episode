"""Render only possessed compiled numerical rows and their scientific meanings."""
from collections.abc import Mapping
import json
from .literature_compiled_assay_prompt import COMPILED_ASSAY_TASK


def is_row(value):
    return isinstance(value, Mapping) and value.get('evaluation_scope') == 'compiled_source_endpoint' and 'component' in value


def rows_from_values(value):
    if is_row(value):
        yield value
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from rows_from_values(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from rows_from_values(child)


def rows_from_reports(reports):
    for report in reports:
        if isinstance(report, Mapping):
            for value in report.values():
                if isinstance(value, (list, tuple)):
                    yield from (row for row in value if is_row(row))


def task_relevant(state):
    assignment = state.get('literature_assignment', {})
    if isinstance(assignment, Mapping) and (assignment.get('requested_compiled_assay_components') or assignment.get('requested_compiled_assay_components_v2')):
        return True
    if state.get('literature_compiled_assay_work', {}).get('version') == 'literature_compiled_assay_task_v1':
        return True
    outcome = state.get('last_local_outcome') or {}
    if isinstance(outcome, Mapping) and isinstance(outcome.get('result'), Mapping) and outcome['result'].get('view') == 'compiled_assay_components':
        return True
    return any(rows_from_reports(state.get('child_reports', ())))


def render_received(parts, rows, *, section, table):
    grouped = {}; seen = set()
    for row in rows:
        exact = json.dumps(row, sort_keys=True, allow_nan=False)
        if exact in seen:
            continue
        seen.add(exact)
        grouped.setdefault(row['sheet_ref'], []).append(row)
    labels = {}; opaque_labels = {}
    for index, selected in enumerate(grouped.values(), 1):
        first = selected[0]
        section(parts, 'Compiled source assay ' + str(index), table(('Meaning', 'Source value'),
            [(name, value) for name, value in first['assay_meanings'].items() if value is not None]
            + [('Measured endpoint', first['endpoint_kind']), ('Molecular arrangement', first['arrangement_kind'])]))
        section(parts, 'Requested numerical assay sections', table(
            ('Section', 'Component', 'Value', 'Unit', 'Status', 'Unavailable reason'),
            [(row['section'], row['component'], row['value'], row['unit'], row['status'], row['unavailable_reason']) for row in selected]))
        section(parts, 'Numerical meanings and calculations', table(('Component', 'Calculation', 'Meaning', 'Qualifications'),
            [(row['component'], row['formula'], row['meaning'], ', '.join(row['qualifications'])) for row in selected]))
        section(parts, 'Selected operand meanings', table(('Role', 'Witnessed source relationship'),
            first['operand_meanings'].items()))
        native_rows = []
        for row in selected:
            native = row['native_quantity']
            if native is None:
                continue
            domain = native['reported_domain']
            native_rows.append((row['component'], native['value'], native['source_unit'],
                native['threshold'], native['bound'], native['approximate'],
                '' if domain is None else '; '.join(str(domain[key]) for key in
                    ('kind', 'lower', 'lower_inclusive', 'upper', 'upper_inclusive', 'projection'))))
        section(parts, 'Selected native numerical domains; original units, no bound conversion', table(
            ('Component', 'Native point', 'Source unit', 'Threshold', 'Relation', 'Approximate', 'Reported domain'), native_rows))
        section(parts, 'Already applied correction stages', table(('Stage', 'Source interpretation'), first['correction_stages'].items()))
        dependency_rows = []
        for row in selected:
            relationships = []
            for dependency in row['dependencies']:
                if dependency['identity_stage'] is not None:
                    relationships.append(dependency['role'] + ': algebraic identity after ' + dependency['identity_stage'])
                    continue
                keys = dependency['canonical_physical_keys']
                for key in keys:
                    labels.setdefault(key, 'canonical measurement ' + str(len(labels) + 1))
                opaque = dependency['recorded_dependency_keys']
                for key in opaque:
                    opaque_labels.setdefault(key, 'retained dependency identity ' + str(len(opaque_labels) + 1))
                names = ', '.join([*(labels[key] for key in keys), *(opaque_labels[key] for key in opaque)]) or 'physical identity not established'
                relationships.append(dependency['role'] + ': ' + names + ' (' + dependency['physical_identity_status'] + ')')
            dependency_rows.append((row['component'], '; '.join(relationships)))
        section(parts, 'Shared numerical dependencies', table(('Component', 'Original measurement reuse'), dependency_rows))
        section(parts, 'Operand applicability limits', table(('Role', 'Unresolved or incompatible meaning'),
            [(role, reason) for role, reason in first['operand_eligibility'].items() if reason is not None]))
        scoped = [row for row in selected if 'uncertainty' in row and row['uncertainty']['scope'] != 'not_applicable']
        if scoped:
            section(parts, 'Uncertainty of requested numerical results', table(
                ('Component', 'Estimand', 'Scope', 'Operand order', 'Covariance status', 'Origin', 'Propagation'),
                [(row['component'], row['uncertainty']['estimand_component'], row['uncertainty']['scope'],
                  ', '.join(row['uncertainty']['operand_order']), row['uncertainty']['variance_status'],
                  row['uncertainty']['covariance_origin'], row['uncertainty']['propagation_model']) for row in scoped]))
        section(parts, 'Compilation limits', table(('Question', 'Meaning'), [
            ('Uncertainty', first['variance_status'] + '; ' + first['observation_model']),
            ('Partial normalizations', 'joint uncertainty propagation is unimplemented; no confidence level is inferred'
                if first['partial_uncertainty_status'] == 'unimplemented' else
                'component-scoped first-order joint propagation; distinct residual variability and other corrections remain separate; no confidence level is inferred'),
            ('Covariance input', first['covariance_input_status']),
            ('Opaque dependency identities', 'identity across different component families remains unknown; these labels do not count experiments'),
            ('Repeated transforms', 'shared source quantities, not independent verification'),
            ('Functional assertion', 'measured endpoint and source assertion remain distinct'),
            ('Across assays', 'no universal quality grade, combined annotation credit or cross-assay total'),
        ]))
