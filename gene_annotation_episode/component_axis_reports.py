"""Receipt-bound A107/A110 reports over existing numerical publications.

These are scientific component reports, not new calculators or scalar reducers.
Only the actual receiver's delivered numerical subset is interpreted here.
"""
from copy import deepcopy
import json

from .communication import plain, validate_closed_schema, validate_form
from .domain import ContractError, canonical, obj
from .episode_return_records import EpisodeReturnRecords


VERSION = 'component_axis_report_v1'
GRADING_REPORT_VERSION = 'component_axis_saved_grading_report_v2'
SCORING_SHEET_VERSION = 'component_axis_scoring_sheet_v1'
SCORING_FACT = 'component_axis_scoring_sheets'
PATH_STATES = ('not_assessed', 'evidence_returned', 'partial', 'unavailable', 'inapplicable')
PATHS = {
    'A107': ('requirement', 'presence', 'expression', 'coexpression', 'interaction'),
    'A110': ('reaction_identity', 'stoichiometry', 'electron_accounting',
             'cofactor_regeneration', 'resources', 'energetics'),
}


def cell_views(axis):
    if axis == 'A107':
        from .literature_partner_storage import partner_cells_schema
        return {'partner_components': partner_cells_schema()}
    if axis == 'A110':
        from .literature_reaction_storage import reaction_cells_schema, reaction_semantic_cells_schema
        return {'reaction_components': reaction_cells_schema(),
                'reaction_meanings': reaction_semantic_cells_schema()}
    raise ContractError('component_axis_not_supported')


def repository(services, axis, field):
    if field not in cell_views(axis):
        raise ContractError('component_axis_numerical_view_not_supported')
    if axis == 'A107':
        return services.literature_partner_repository()
    native = services.literature_reaction_repository()
    return native.semantic_projection() if field == 'reaction_meanings' else native


def validate_native_return_channels(selection, schema):
    """Require result custody when admitting a new native-capable child.

    Preparation-only work may return empty components and its real execution
    findings. This does not choose an investigation, run a job or widen a
    receipt. Historical closed commissions retain their original contracts.
    """
    from .component_axis_native_contracts import OPERATIONS
    from .component_axis_native_hpc import FACT_SOURCE, EXECUTION_SOURCE
    axis = selection.get('evidence_axis', {}).get('option_id')
    if axis not in OPERATIONS:
        return
    native = {OPERATIONS[axis]}
    if axis == 'A107':
        native.add('partner.request_detection_hpc')
    if axis == 'A110':
        native.add('chemistry.request_flux_balance_hpc')
    if not native.intersection(item['name'] for item in selection.get('child_tool_info', ())):
        return
    present = {node.get('x-source') for node in schema.get('properties', {}).values()}
    missing = sorted({FACT_SOURCE, EXECUTION_SOURCE} - present)
    if missing:
        raise ContractError('component_native_return_channels_required', detail={
            'field': 'report_schema', 'missing_fact_sources': missing,
            'repair': 'Use episode.return_contract for scientific_process and include both '
                + FACT_SOURCE + ' and ' + EXECUTION_SOURCE + ' as saved-fact return fields. '
                'scientific_process_results contains process metadata, not these numerical results.'})


def _refs(namespace=None):
    item = {'type': 'string', 'format': 'reference'}
    if namespace is not None:
        item['x-reference-namespace'] = namespace
    return {'type': 'array', 'items': item, 'uniqueItems': True}


def legacy_report_schema(axis):
    """Original closed contract for immutable historical path verdicts."""
    if axis not in PATHS:
        raise ContractError('component_axis_not_supported')
    path = obj({'status': {'type': 'string', 'enum': list(PATH_STATES)}, 'evidence_refs': _refs(),
        'assessment_refs': _refs('assessment'),
        'limitations': {**_refs(), 'description':
            'Actual received records retaining applicable qualifications or missing reasons. '
            'The scientific text remains in those saved records.'}})
    result = obj({'axis': {'type': 'string', 'const': axis},
        'report_version': {'type': 'string', 'const': VERSION},
        'paths': obj({name: deepcopy(path) for name in PATHS[axis]}),
        'scope_status': {'type': 'string', 'enum': ['not_assessed', 'unresolved', 'partial', 'represented']},
        'correspondence_refs': {**_refs(), 'description':
            'Received correspondence evidence for particular subjects, partners, regions or '
            'features. Listing a reference alone establishes no target transfer.'},
        'information_need_refs': _refs(),
        'records': {**_refs(), 'x-source': 'committed_record_refs'},
        **cell_views(axis),
        'controller_progress': {'type': 'number', 'x-source': 'credit', 'description':
            'Retained scientific-finding progress in the original controller units. '
            'Separate from scientific numerical components; no combined axis scalar.'}})
    if axis == 'A107':
        from .a107_qualification import FACT_SOURCE, EXECUTION_SOURCE
        result['properties']['qualifications'] = {**_refs(), 'x-source': FACT_SOURCE}
        result['required'].append('qualifications')
        result['properties']['execution_records'] = {**_refs(), 'x-source': EXECUTION_SOURCE}
        result['required'].append('execution_records')
    if axis == 'A110':
        from .a110_qualification import FACT_SOURCE
        result['properties']['qualifications'] = {**_refs(), 'x-source': FACT_SOURCE}
        result['required'].append('qualifications')
    from .component_axis_native_hpc import FACT_SOURCE, EXECUTION_SOURCE
    result['properties']['native_component_records'] = {**_refs('source'), 'x-source': FACT_SOURCE}
    result['required'].append('native_component_records')
    result['properties']['native_execution_records'] = {**_refs('source'), 'x-source': EXECUTION_SOURCE}
    result['required'].append('native_execution_records')
    validate_closed_schema(result)
    return result


def report_schema(axis):
    """Return exact saved numerical/qualification facts, without path verdicts."""
    original = legacy_report_schema(axis)['properties']
    schema = obj({name: deepcopy(node) for name, node in original.items()
        if node.get('x-source') is not None or name in ('axis', 'report_version')})
    schema['properties']['report_version']['const'] = GRADING_REPORT_VERSION
    validate_closed_schema(schema)
    return schema


def initial_report(axis):
    return {'axis': axis, 'report_version': GRADING_REPORT_VERSION}


def report_axis(schema):
    properties = plain(schema).get('properties', {})
    axis = properties.get('axis', {}).get('const')
    version = properties.get('report_version', {}).get('const')
    if axis not in PATHS or version not in {VERSION, GRADING_REPORT_VERSION}:
        return None
    for candidate in (report_schema(axis), legacy_report_schema(axis)):
        expected = candidate['properties']
        if (version == expected['report_version']['const'] and set(properties) == set(expected) and all(
                properties[name].get('x-source') == field.get('x-source') for name, field in expected.items())):
            return axis
    return None


def _numerical_identity(row):
    return row['sheet_ref'], row['component']


def _native_quantities(row):
    return {key: deepcopy(row[key]) for key in ('component', 'value', 'unit', 'status',
        'formula_code', 'origin', 'unavailable_reason', 'conditional_on') if key in row}


def _component_records(store, report, context, services):
    grouped, native = {}, {}
    for field in cell_views(report['axis']):
        reader = repository(services, report['axis'], field)
        if reader.store is not store or reader.run_id != context.run_id:
            raise ContractError('component_axis_original_repository_required')
        rows = report[field]
        reader.validate_fact_values(context, rows)
        seen = set()
        for row in rows:
            key = _numerical_identity(row)
            if key in seen:
                raise ContractError('component_axis_duplicate_component_in_view')
            seen.add(key)
            quantities = _native_quantities(row)
            if key in native and native[key] != quantities:
                raise ContractError('component_axis_conflicting_numerical_views')
            native[key] = quantities
            if key[0] not in grouped:
                saved = reader.read(key[0])
                source = store.get(key[0])
                request = json.loads(store.get_artifact(source['request_ref']))
                grouped[key[0]] = {'sheet_ref': key[0], 'record_version': source['version'],
                    'artifact_ref': source['artifact_ref'], 'request_ref': source['request_ref'],
                    'original_scope': request.get('scope'), 'receiving_scope': plain(context.scope),
                    'experimental_bindings': deepcopy(saved.get('experimental_bindings', {})),
                    'experiment_assessment': deepcopy(saved.get('experiment_assessment')),
                    'source_refs': list(saved.get('input_source_refs', source.get('parent_source_refs', []))),
                    'components': {}, 'returned_views': {},
                    'target_transfer': 'requires_particular_subject_component_region_or_feature_correspondence',
                    'independence': 'not_inferred_from_distinct_records_or_missing_dataset_identity'}
            entry = grouped[key[0]]
            entry['components'][key[1]] = quantities
            entry['returned_views'].setdefault(field, []).append(deepcopy(row))
    results = list(grouped.values())
    _mark_revisions(results)
    return results


def _mark_revisions(results):
    by_ref = {row['sheet_ref']: row for row in results}
    for row in results:
        row['assessment_state'] = 'retained' if row['experiment_assessment'] else 'legacy_unlinked'
    for row in results:
        assessment = row['experiment_assessment']
        if assessment and assessment['revises_sheet_ref'] in by_ref:
            by_ref[assessment['revises_sheet_ref']]['assessment_state'] = 'superseded_within_return'


def _merge_result(records, incoming):
    """Union actually delivered subsets; another child cannot erase a cell."""
    key = incoming['sheet_ref']
    if key not in records:
        records[key] = deepcopy(incoming)
        return
    retained = records[key]
    if any(retained[field] != incoming[field] for field in (
            'record_version', 'artifact_ref', 'request_ref', 'original_scope',
            'experimental_bindings', 'experiment_assessment', 'source_refs')):
        raise ContractError('component_axis_original_publication_conflict')
    for name, component in incoming['components'].items():
        if name in retained['components'] and retained['components'][name] != component:
            raise ContractError('component_axis_conflicting_numerical_views')
        retained['components'][name] = deepcopy(component)
    for field, values in incoming['returned_views'].items():
        known = {canonical(row) for row in retained['returned_views'].get(field, [])}
        retained['returned_views'].setdefault(field, []).extend(
            deepcopy(row) for row in values if canonical(row) not in known)


def dependence(records):
    """Describe common origins without summing or asserting independence."""
    owners = {}
    for row in records:
        origins = [('saved_sheet', row['sheet_ref']), ('saved_artifact', row['artifact_ref'])]
        origins.extend(('source', reference) for reference in row['source_refs'])
        assessment = row['experiment_assessment']
        experiment = assessment.get('experiment_ref') if assessment else row['experimental_bindings'].get('experiment_ref')
        if experiment is not None:
            origins.append(('experiment', experiment))
        for view in row['returned_views'].values():
            for cell in view:
                if cell.get('data_source_ref') is not None:
                    origins.append(('retained_dataset_source', cell['data_source_ref']))
        for kind, identity in set(origins):
            owners.setdefault((kind, identity), set()).add(row['sheet_ref'])
    return {'shared_origins': [{'kind': kind, 'identity': identity, 'sheet_refs': sorted(references)}
        for (kind, identity), references in sorted(owners.items()) if len(references) > 1],
        'missing_identity': 'unknown_dependence_not_independence',
        'numerical_ownership': 'original_sheet_ref_and_component; repeated_views_are_not_new_measurements'}


def resolve_report(store, report, *, context, services, axis=None):
    report = plain(report)
    selected = report.get('axis') if axis is None else axis
    if selected not in PATHS or report.get('axis') != selected:
        raise ContractError('component_axis_report_identity_mismatch')
    known = set(context.received_record_refs)
    scope = store.validate_scope(plain(context.scope))
    EpisodeReturnRecords(store, context.run_id, failure_prefix='component_axis_').authenticate(context)
    def permitted(reference, namespace):
        return (reference in known and reference in store.reference_subset([reference], scope)
            and (namespace is None or store.get(reference)['record_type'] == namespace))
    legacy = 'paths' in report
    validate_form(report, legacy_report_schema(selected) if legacy else report_schema(selected), permitted)
    for path in report.get('paths', {}).values():
        if path['status'] in {'evidence_returned', 'partial'} and not (
                path['evidence_refs'] or path['assessment_refs']):
            raise ContractError('component_axis_path_requires_received_evidence')
        if any(not set(store.get(ref).get('evidence_refs', [])) <= known
                for ref in path['assessment_refs']):
            raise ContractError('component_axis_assessment_evidence_not_received')
    records = _component_records(store, report, context, services)
    from .component_axis_native_hpc import received_components, execution_findings as native_execution_findings
    native_components = received_components(store, report['native_component_records'], scope, axis=selected, known=known)
    native_execution = native_execution_findings(store, report['native_execution_records'], scope, axis=selected)
    if {row['source_ref'] for row in native_components} != set(report['native_component_records']):
        raise ContractError('component_axis_original_native_components_required')
    if {row['source_ref'] for row in native_execution} != set(report['native_execution_records']):
        raise ContractError('component_axis_original_native_execution_required')
    qualifications, execution = [], []
    if selected == 'A107':
        from .a107_qualification import received_qualifications, execution_findings
        qualifications = received_qualifications(store, report['qualifications'], scope,
            known_record_refs=known)
        if {row['source_ref'] for row in qualifications} != set(report['qualifications']):
            raise ContractError('a107_original_qualified_return_required')
        execution = execution_findings(store, context, set(report['execution_records']))
        if {row['source_ref'] for row in execution} != set(report['execution_records']):
            raise ContractError('a107_original_genomic_execution_return_required')
    elif selected == 'A110':
        from .a110_qualification import received
        qualifications = received(store, report['qualifications'], scope, known=known)
        if {row['source_ref'] for row in qualifications} != set(report['qualifications']):
            raise ContractError('a110_original_qualified_return_required')
    return {'axis': selected, 'report_version': report['report_version'], 'scope': scope,
        'records': list(report['records']), 'numerical_results': records,
        'native_component_results': native_components, 'native_execution_findings': native_execution,
        'tool_qualifications': qualifications,
        'execution_findings': execution,
        'dependencies': {**dependence(records), 'native': native_dependence(native_components),
            'cross_path': cross_dependence(records, native_components)},
        'child_controller_progress': report['controller_progress'],
        'combined_scientific_score': None,
        'combination_status': 'separate_named_components; no_new_axis_reducer',
        'interpretation': 'source_and_context_qualified_findings; not_activity_or_annotation_probability'}


def received_reports(store, *, context, services):
    """Read only admitted immediate-child returns, in the actual receiver."""
    reader = EpisodeReturnRecords(store, context.run_id, failure_prefix='component_axis_received_')
    reports, seen, records, qualifications, executions = {}, set(), {}, {}, {}
    native_components, native_execution = {}, {}
    for child, form, schema in reader.received_attempts(context):
        axis = report_axis(schema)
        if axis is None or child.path[:-1] != context.path:
            continue
        selected = plain(child.assignment).get('selection', {}).get('evidence_axis', {}).get('option_id')
        if selected != axis:
            raise ContractError('component_axis_original_child_selection_mismatch')
        identity = canonical([child.episode_id, form])
        if identity in seen:
            continue
        seen.add(identity)
        resolved = resolve_report(store, form, context=context, services=services, axis=axis)
        reports.setdefault(axis, []).append({'reporting_episode_id': child.episode_id,
            'original_scope': plain(child.scope), 'components': resolved})
        records.setdefault(axis, {})
        for row in resolved['native_component_results']:
            native_components.setdefault(axis, {})[row['source_ref']] = row
        for row in resolved['native_execution_findings']:
            native_execution.setdefault(axis, {})[row['source_ref']] = row
        for row in resolved['tool_qualifications']:
            qualifications.setdefault(axis, {})[row['source_ref']] = row
        for row in resolved['execution_findings']:
            executions.setdefault(axis, {})[row['source_ref']] = row
        for row in resolved['numerical_results']:
            _merge_result(records[axis], row)
    for values in records.values():
        _mark_revisions(list(values.values()))
    if 'A107' in reports:
        from .a107_qualification import received_qualifications, execution_findings
        qualifications['A107'] = {row['source_ref']: row for row in received_qualifications(
            store, qualifications.get('A107', {}), context.scope,
            known_record_refs=context.received_record_refs)}
        executions['A107'] = {row['source_ref']: row for row in execution_findings(
            store, context, set(executions.get('A107', {})))}
    if 'A110' in reports:
        from .a110_qualification import received
        qualifications['A110'] = {row['source_ref']: row for row in received(store,
            qualifications.get('A110', {}), context.scope, known=context.received_record_refs)}
    return {axis: {'axis': axis, 'reports': values,
        'numerical_results': list(records[axis].values()),
        'tool_qualifications': list(qualifications.get(axis, {}).values()),
        'execution_findings': list(executions.get(axis, {}).values()),
        'native_component_results': list(native_components.get(axis, {}).values()),
        'native_execution_findings': mark_native_execution(
            list(native_execution.get(axis, {}).values()), list(native_components.get(axis, {}).values())),
        'dependencies': {**dependence(list(records[axis].values())),
            'native': native_dependence(list(native_components.get(axis, {}).values())),
            'cross_path': cross_dependence(list(records[axis].values()), list(native_components.get(axis, {}).values()))},
        'combined_scientific_score': None,
        'combination_status': 'separate_named_components; no_new_axis_reducer'}
        for axis, values in reports.items()}


def current_scoring_sheets(store, *, context, services, configured_axes=None):
    """Automatically project the receiver's saved scientific scoring state.

    Numerical results do not wait for an interpretive report, a synthesis
    child or a model-selected path status. Existing typed receipts still own
    delivery: a sheet handle grants no unreturned experimental cells. This
    view reuses the original saved calculations and grader-validated native
    publications; it neither recalculates them nor invents an axis scalar.
    """
    workflow = getattr(services, 'workflow', None)
    if context.role not in {'annotation', 'scientific_process'}:
        return {}
    # A retained-result reader can select an existing axis without assembling
    # an executor or model provider. This selects views, never evidence grants.
    configured = set(configured_axes if configured_axes is not None else
        getattr(getattr(workflow, 'tools', None), 'COMPONENT_NATIVE_AXES', ()))
    selected = plain(context.assignment).get('selection', {}).get('evidence_axis', {}).get('option_id')
    axes = configured.intersection(PATHS)
    if context.role == 'scientific_process':
        axes.intersection_update({selected})
    if not axes:
        return {}
    EpisodeReturnRecords(store, context.run_id, failure_prefix='component_axis_scoring_').authenticate(context)
    from .component_axis_native_hpc import received_components, execution_findings
    from .a107_qualification import received_qualifications
    from .a110_qualification import received as chemical_qualifications
    known = tuple(context.received_record_refs)
    native = received_components(store, known, context.scope,
        axis=selected if context.role == 'scientific_process' else None)
    execution = execution_findings(store, known, context.scope,
        axis=selected if context.role == 'scientific_process' else None)
    sheets = {}
    for axis in sorted(axes):
        cells = {field: repository(services, axis, field).received_cells(context)
            for field in cell_views(axis)}
        originals = _component_records(store, {'axis': axis, **cells}, context, services)
        components = [row for row in native if row['axis'] == axis]
        qualifiers = (received_qualifications(store, known, context.scope, known_record_refs=known)
            if axis == 'A107' else chemical_qualifications(store, known, context.scope, known=known))
        if not originals and not components and not qualifiers:
            continue
        sheets[axis] = {'version': SCORING_SHEET_VERSION, 'axis': axis,
            'run_id': context.run_id, 'receiving_episode_id': context.episode_id,
            'scope': plain(context.scope),
            'numerical_results': originals,
            'native_component_results': components,
            'tool_qualifications': qualifiers,
            'native_execution_findings': mark_native_execution(
                [row for row in execution if row['axis'] == axis], components),
            'dependencies': {**dependence(originals),
                'native': native_dependence(components),
                'cross_path': cross_dependence(originals, components)},
            'combined_scientific_score': None,
            'combination_status': 'separate_named_components; no_new_axis_reducer',
            'interpretation': 'current_received_original_components_and_per_use_qualifications',
            'update_rule': 'automatic_from_saved_results_and_actual_receipts; no_finalize_action',
            'unqualified_uses': 'remain_unknown; do_not_suppress_the_original_scientific_components',
            'controller_progress': 'separate_from_this_scientific_scoring_sheet'}
    return sheets


def native_dependence(rows):
    origins = {}
    for row in rows:
        for kind, identity in (('input_bytes', row['input_file']['sha256']),
                ('dataset', row['dependencies']['dataset_id']),
                ('logical_native_measurement', row['logical_work_sha256']),
                *[('source', reference) for reference in row['dependencies']['origin_source_refs']]):
            if identity is not None:
                origins.setdefault((kind, identity), set()).add(row['source_ref'])
    return {'shared_origins': [{'kind': kind, 'identity': identity, 'source_refs': sorted(refs)}
        for (kind, identity), refs in sorted(origins.items()) if len(refs) > 1],
        'missing_dataset_identity': 'unknown_dependence_not_independence',
        'native_and_literature_views': 'shared_origins_require_scientific_review; no_automatic_independence'}


def cross_dependence(experimental, native):
    origins = {}
    for row in experimental:
        for reference in row['source_refs']:
            origins.setdefault(reference, {'experimental_sheet_refs': set(), 'native_source_refs': set()})[
                'experimental_sheet_refs'].add(row['sheet_ref'])
    for row in native:
        for reference in row['dependencies']['origin_source_refs']:
            origins.setdefault(reference, {'experimental_sheet_refs': set(), 'native_source_refs': set()})[
                'native_source_refs'].add(row['source_ref'])
    return {'shared_source_uses': [{'source_ref': reference,
        'experimental_sheet_refs': sorted(uses['experimental_sheet_refs']),
        'native_source_refs': sorted(uses['native_source_refs'])} for reference, uses in sorted(origins.items())
        if uses['experimental_sheet_refs'] and uses['native_source_refs']],
        'unmatched_or_missing_origins': 'unknown_dependence; not_independent_confirmation'}


def mark_native_execution(rows, components):
    admitted = {(row['request_ref'], row['hpc_result_ref']) for row in components}
    logical = {row['logical_work_sha256'] for row in components}
    return [{**row, 'superseded_by_received_admission': (
        row['request_ref'], row['hpc_result_ref']) in admitted or
        row.get('status') == 'native_work_requested' and row.get('logical_work_sha256') in logical} for row in rows]
