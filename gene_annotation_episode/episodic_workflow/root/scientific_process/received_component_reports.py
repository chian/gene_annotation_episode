"""Private scientific immediate-child report interpretation and custody."""
from copy import deepcopy
import json
from ..communication import plain, validate_closed_schema, validate_form
from gene_annotation_episode.domain import ContractError, canonical, obj
from ..episode_return_records import EpisodeReturnRecords
from ..library.component_received_reports import (PATHS, legacy_report_schema, report_schema, report_axis, _component_records, _merge_result, _mark_revisions, dependence, native_dependence, cross_dependence, mark_native_execution)
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
    from ..library.component_native_received_records import received_components, execution_findings as native_execution_findings
    native_components = received_components(store, report['native_component_records'], scope, axis=selected, known=known)
    native_execution = native_execution_findings(store, report['native_execution_records'], scope, axis=selected)
    if {row['source_ref'] for row in native_components} != set(report['native_component_records']):
        raise ContractError('component_axis_original_native_components_required')
    if {row['source_ref'] for row in native_execution} != set(report['native_execution_records']):
        raise ContractError('component_axis_original_native_execution_required')
    qualifications, execution = [], []
    if selected == 'A107':
        from ..a107.a107_qualification import received_qualifications, execution_findings
        qualifications = received_qualifications(store, report['qualifications'], scope,
            known_record_refs=known)
        if {row['source_ref'] for row in qualifications} != set(report['qualifications']):
            raise ContractError('a107_original_qualified_return_required')
        execution = execution_findings(store, context, set(report['execution_records']))
        if {row['source_ref'] for row in execution} != set(report['execution_records']):
            raise ContractError('a107_original_genomic_execution_return_required')
    elif selected == 'A110':
        from ..a110.a110_qualification import received
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
        from ..a107.a107_qualification import received_qualifications, execution_findings
        qualifications['A107'] = {row['source_ref']: row for row in received_qualifications(
            store, qualifications.get('A107', {}), context.scope,
            known_record_refs=context.received_record_refs)}
        executions['A107'] = {row['source_ref']: row for row in execution_findings(
            store, context, set(executions.get('A107', {})))}
    if 'A110' in reports:
        from ..a110.a110_qualification import received
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


