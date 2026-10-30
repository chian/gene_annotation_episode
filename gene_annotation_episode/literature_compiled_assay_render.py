"""Render only possessed compiled numerical rows and their scientific meanings."""
from collections.abc import Mapping
import json
from .literature_compiled_assay_prompt import COMPILED_ASSAY_TASK


def is_row(value):
    return isinstance(value, Mapping) and value.get('evaluation_scope') in ('compiled_source_endpoint', 'common_assertion_contrast') and 'component' in value


def is_common_row(value):
    return is_row(value) and value.get('evaluation_scope') == 'common_assertion_contrast'


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
    if isinstance(outcome, Mapping) and isinstance(outcome.get('result'), Mapping) and outcome['result'].get('view') == 'compiled_assay_components' and outcome['result'].get('record_version') != 'literature_compiled_assay_record_v3':
        return True
    return any(not is_common_row(row) for row in rows_from_reports(state.get('child_reports', ())))


def common_task_relevant(state):
    assignment = state.get('literature_assignment', {})
    if isinstance(assignment, Mapping) and assignment.get('requested_compiled_assay_components_v3'):
        return True
    if state.get('literature_common_assessment_work', {}).get('version') == 'literature_common_assessment_task_v1':
        return True
    return any(is_common_row(row) for row in rows_from_values((state.get('last_local_outcome', {}),
        state.get('child_reports', ()), state.get('current_report_update', {}))))


def hidden_records(rows, records):
    """Do not expand original numeric quotations through generic record aliases."""
    locations = [loc for row in rows if is_common_row(row) for loc in (
        *row['host_custody']['withheld_locations'], *(c['location'] for c in row['context']))]
    hidden = set()
    for reference, record in records.items():
        if not isinstance(record, Mapping):
            continue
        anchor = record.get('anchor')
        if not isinstance(anchor, Mapping):
            continue
        if any(anchor.get('artifact_ref') == loc['artifact_ref']
                and type(anchor.get('start')) is int and type(anchor.get('end')) is int
                and anchor['start'] < loc['end'] and loc['start'] < anchor['end'] for loc in locations):
            hidden.add(reference)
    return hidden


def render_received(parts, rows, *, section, table):
    rows = list(rows)
    common = [row for row in rows if is_common_row(row)]
    if common:
        render_common_received(parts, common, section=section, table=table)
    rows = [row for row in rows if not is_common_row(row)]
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


def render_common_received(parts, rows, *, section, table):
    grouped = {}; seen = set(); labels = {}
    for row in rows:
        exact = json.dumps(row, sort_keys=True, allow_nan=False)
        if exact not in seen:
            seen.add(exact); grouped.setdefault(row['sheet_ref'], []).append(row)
    def label(key):
        if key is None:
            return 'unknown'
        labels.setdefault(key, 'shared measurement ' + str(len(labels) + 1))
        return labels[key]
    for number, selected in enumerate(grouped.values(), 1):
        first = selected[0]
        section(parts, 'Common source assessment ' + str(number), table(('Question', 'Scientific meaning'), [
            ('Functional resolution', first['assertion_resolution']), ('Comparison', first['question']),
            ('Numerical context scope', first['numerical_scope_implementation_status'])]))
        section(parts, 'Selected experimental meanings', table(('Aspect', 'Source meaning', 'Scope qualification'),
            [(r['field'].removeprefix('assessment.').replace('_', ' '), r['display_text'],
              r['implementation_reason'] or r['implementation_status']) for r in first['context']]))
        section(parts, 'Requested numerical assessment', table(
            ('Component', 'Measured or calculated value', 'Conditional scenario', 'Unit', 'Status', 'Native meaning', 'Origin'),
            [(r['component'], r['value'], r['conditional_value'], r['unit'], r['status'], r['native_semantics'], r['origin']) for r in selected]))
        section(parts, 'Numerical interpretation', table(('Component', 'Calculation', 'What it evaluates'),
            [(r['component'], r['formula'], r['meaning']) for r in selected]))
        section(parts, 'Missing inputs and comparison limitations', table(
            ('Component', 'Source information', 'Experimental relationships', 'Implementation'),
            [(r['component'], ', '.join(r['source_missing_reasons']), ', '.join(r['relationship_reasons']),
              ', '.join(r['implementation_reasons'])) for r in selected]))
        relationships = first['relationship_meanings']
        section(parts, 'Experimental relationships', table(('Aspect', 'Meaning'), [
            ('Compared subjects', relationships['subject']), ('Product and reporter', relationships['product_reporter']),
            ('Sampling', relationships['sampling']), ('Correction factorization', relationships['correction_factorization']),
            *((group + ': ' + name, value) for group, links in relationships['groups'].items() for name, value in links.items())]))
        model = first['model_meanings']
        if model is not None:
            section(parts, 'Named alternative model', table(('Aspect', 'Meaning'), list(model.items())
                + list((relationships['model_assumptions'] or {}).items())))
        section(parts, 'Original measurement reuse', table(('Component', 'Operands', 'Input origins', 'Numerical origin'),
            [(r['component'], ', '.join(label(key) for key in r['operand_keys']), ', '.join(r['input_origins']), r['numeric_origin']) for r in selected]))
        section(parts, 'Measurement and sampling bindings', table(('Role', 'Measurement', 'Physical identity', 'Population', 'Assay'),
            [(r['role'], label(r['owner_key']), label(r['physical_owner_key']), label(r['population_key']), label(r['assay_key']))
             for r in first['estimate_bindings']]))
        section(parts, 'Dependence and complementary endpoints', table(('Roles', 'Relationship'),
            [(', '.join(r['roles']), r['relation']) for r in first['dependence']]))
        spread = [(r['component'], r['reported_uncertainty']) for r in selected if r['reported_uncertainty'] is not None]
        if spread:
            section(parts, 'Reported spread of requested native estimates', table(('Component', 'Magnitude', 'Unit', 'Statistic', 'Meaning'),
                [(name, s['exact_magnitude']['numerator'] + '/' + s['exact_magnitude']['denominator'] if s['exact_magnitude'] else None,
                  s['unit'], s['statistic'], s['meaning']) for name, s in spread]))
        section(parts, 'Uncertainty of requested comparisons', table(('Component', 'Scope', 'Variance status', 'Basis', 'Propagation', 'Covariance origin', 'Ordered owners'),
            [(r['component'], r['uncertainty']['scope'], r['uncertainty']['variance_status'], r['uncertainty']['basis'],
              r['uncertainty']['model'], None if r['covariance_provenance'] is None else r['covariance_provenance']['origin'],
              '' if r['covariance_provenance'] is None else ', '.join(label(k) for k in r['covariance_provenance']['owner_keys']))
             for r in selected if r['uncertainty']['scope'] != 'not_applicable']))
        section(parts, 'Assessment limitations', table(('Meaning',), [(value,) for value in first['remaining_implementation_limits']
            if value != 'selected_path_binding_is_host_responsibility']))
