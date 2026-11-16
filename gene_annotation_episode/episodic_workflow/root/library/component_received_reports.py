"""Receipt-bound A107/A110 reports over existing numerical publications.

These are scientific component reports, not new calculators or scalar reducers.
Only the actual receiver's delivered numerical subset is interpreted here.
"""
from copy import deepcopy
import json

from ..communication import plain, validate_closed_schema, validate_form
from gene_annotation_episode.domain import ContractError, canonical, obj
from ..episode_return_records import EpisodeReturnRecords


GRADING_REPORT_VERSION = 'component_axis_saved_grading_report_v2'
SCORING_SHEET_VERSION = 'component_axis_scoring_sheet_v1'
SCORING_FACT = 'component_axis_scoring_sheets'
PATHS = {
    'A107': ('requirement', 'presence', 'expression', 'coexpression', 'interaction'),
    'A110': ('reaction_identity', 'stoichiometry', 'electron_accounting',
             'cofactor_regeneration', 'resources', 'energetics'),
}


def cell_views(axis):
    if axis == 'A107':
        from .literature_partner_return_contracts import partner_cells_schema
        return {'partner_components': partner_cells_schema()}
    if axis == 'A110':
        from .literature_reaction_return_contracts import reaction_cells_schema, reaction_semantic_cells_schema
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



def _refs(namespace=None):
    item = {'type': 'string', 'format': 'reference'}
    if namespace is not None:
        item['x-reference-namespace'] = namespace
    return {'type': 'array', 'items': item, 'uniqueItems': True}


def report_schema(axis):
    """Return exact saved numerical/qualification facts, without path verdicts."""
    if axis not in PATHS:
        raise ContractError('component_axis_not_supported')
    result = obj({'axis': {'type': 'string', 'const': axis},
        'report_version': {'type': 'string', 'const': GRADING_REPORT_VERSION},
        'records': {**_refs(), 'x-source': 'committed_record_refs'},
        **cell_views(axis),
        'controller_progress': {'type': 'number', 'x-source': 'credit', 'description':
            'Retained scientific-finding progress in the original controller units. '
            'Separate from scientific numerical components; no combined axis scalar.'}})
    if axis == 'A107':
        from ..a107.a107_qualification import FACT_SOURCE, EXECUTION_SOURCE
        result['properties']['qualifications'] = {**_refs(), 'x-source': FACT_SOURCE}
        result['required'].append('qualifications')
        result['properties']['execution_records'] = {**_refs(), 'x-source': EXECUTION_SOURCE}
        result['required'].append('execution_records')
    if axis == 'A110':
        from ..a110.a110_qualification import FACT_SOURCE
        result['properties']['qualifications'] = {**_refs(), 'x-source': FACT_SOURCE}
        result['required'].append('qualifications')
    from .component_native_received_records import FACT_SOURCE, EXECUTION_SOURCE
    result['properties']['native_component_records'] = {**_refs('source'), 'x-source': FACT_SOURCE}
    result['required'].append('native_component_records')
    result['properties']['native_execution_records'] = {**_refs('source'), 'x-source': EXECUTION_SOURCE}
    result['required'].append('native_execution_records')
    validate_closed_schema(result)
    return result


def initial_report(axis):
    return {'axis': axis, 'report_version': GRADING_REPORT_VERSION}


def report_axis(schema):
    properties = plain(schema).get('properties', {})
    axis = properties.get('axis', {}).get('const')
    version = properties.get('report_version', {}).get('const')
    if axis not in PATHS or version != GRADING_REPORT_VERSION:
        return None
    expected = report_schema(axis)['properties']
    if set(properties) == set(expected) and all(
            properties[name].get('x-source') == field.get('x-source') for name, field in expected.items()):
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
