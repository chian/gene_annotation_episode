"""Typed merged A102 return with distinct scientific and progress quantities."""
from copy import deepcopy

from .a102_structural_evidence import VERSION
from .communication import plain, validate_closed_schema, validate_form
from .domain import ContractError, canonical, obj
from .literature_structure_storage import structure_cells_schema


PATH_STATES = ('not_assessed', 'evidence_returned', 'partial', 'unavailable', 'inapplicable')
LIMITATIONS = ('predicted_model', 'construct_difference', 'missing_coordinates',
    'ambiguous_mapping', 'partial_match', 'fragment_input', 'unknown_full_length',
    'subunit_scope', 'no_model', 'no_informative_match', 'missing_local_validation',
    'validation_revision_mismatch', 'unsupported_validation_method',
    'assignment_uncertainty', 'coordinate_uncertainty', 'target_transfer_unresolved',
    'experiment_identity_unresolved', 'shared_measurements', 'conflicting_evidence',
    'unresolved_assessment_revisions', 'functional_features_unassessed',
    'alternatives_unassessed')


def legacy_report_schema():
    """Original closed contract for immutable historical model summaries."""
    refs = {'type': 'array', 'items': {'type': 'string', 'format': 'reference'}, 'uniqueItems': True}
    status = {'type': 'string', 'enum': list(PATH_STATES),
        'description': 'Applicability to the requested question. Retained partial or unavailable '
            'components keep their own numerical status even when the requested conclusion is unavailable.'}
    schema = obj({'comparative_status': deepcopy(status),
        'experimental_status': deepcopy(status),
        'scope_status': {'type': 'string', 'enum': ['not_assessed', 'unresolved', 'partial', 'represented']},
        'limitations': {'type': 'array', 'uniqueItems': True,
            'items': {'type': 'string', 'enum': list(LIMITATIONS)}},
        'information_need_refs': deepcopy(refs),
        'correspondence_refs': {**deepcopy(refs),
            'description': 'Received subject/model correspondence evidence for the parent to assess. '
                'Listing a reference alone does not qualify target transfer.'},
        'records': {**deepcopy(refs), 'x-source': 'committed_record_refs',
            'description': 'Actual committed records, including native structural grading grants. '
                'The parent resolves comparative quantities from these grants.'},
        'experimental_cells': structure_cells_schema(),
        'controller_progress': {'type': 'number', 'x-source': 'credit',
            'description': 'Host-owned progress in the commissioned task units. '
                'Not a combined A102 scientific score or an experimental measurement.'}})
    validate_closed_schema(schema)
    return schema


def report_schema():
    original = legacy_report_schema()['properties']
    schema = obj({name: deepcopy(original[name]) for name in
        ('records', 'experimental_cells', 'controller_progress')})
    validate_closed_schema(schema)
    return schema


def initial_report():
    return {}


def is_structural_report_schema(schema):
    """Recognize the merged return fields, including caller restrictions."""
    properties = plain(schema).get('properties', {})
    for candidate in (report_schema(), legacy_report_schema()):
        expected = candidate['properties']
        if (set(properties) == set(expected)
                and all(properties[name].get('x-source') == node.get('x-source')
                    for name, node in expected.items())):
            return True
    return False


def resolve_report(store, report, *, context, structure_repository):
    """Resolve in the receiving episode's scope and actual admitted possession.

    A receiver must have admitted the child's form using the ordinary runtime
    delivery path before calling this function. Passing a sheet ID is not enough.
    """
    from .a102_credit import A102StructuralCredit
    from .a102_publication import received_grade
    from .a102_experimental_evidence import experimental_evidence, dependency_links
    from .a102_hpc import received_execution_findings
    if structure_repository.store is not store:
        raise ContractError('a102_report_repository_store_mismatch')
    report = plain(report)
    known = set(context.received_record_refs)
    scope = store.validate_scope(plain(context.scope))

    def permitted(reference, namespace):
        return (reference in known and bool(store.reference_subset([reference], scope))
            and (namespace is None or store.get(reference)['record_type'] == namespace))

    legacy = 'comparative_status' in report
    validate_form(report, legacy_report_schema() if legacy else report_schema(), permitted)
    if not set(report['records']) <= known:
        raise ContractError('a102_report_records_not_received')
    experimental = experimental_evidence(structure_repository, context, report['experimental_cells'])
    native = [row for reference in report['records']
        if (row := received_grade(store, reference)) is not None
        and row['grade']['target_ref'] in scope['subject_refs']]
    projection = A102StructuralCredit().read_details(store, scope,
        known_record_refs=report['records'], details_limit=len(report['records']), details_offset=0)
    functional = projection['functional_sheets']
    has_comparative = bool(native or projection['tool_attachments']
        or any(functional[name] for name in ('features', 'contrasts', 'traits', 'interfaces')))
    for path, present in (('comparative', has_comparative),
                          ('experimental', bool(experimental['records']))):
        if legacy and report[f'{path}_status'] in {'evidence_returned', 'partial'} and not present:
            raise ContractError(f'a102_{path}_status_differs_from_delivered_evidence')
    # A measured zero must survive. Absence of comparative measurements remains
    # None, even though the legacy controller starts at zero progress.
    has_correspondence = (any(row['grade']['eligible'] for row in native)
        or any(region['attributed_comparisons']
            for sheet in projection['target_sheets'].values() for region in sheet['regions']))
    comparative = {'native_comparisons': native, 'functional_sheets': functional,
        'tool_attachments': projection['tool_attachments'],
        'correspondence_B': projection['credit'] if has_correspondence else None,
        'target_sheets': projection['target_sheets'] if has_correspondence else {},
        'sheet_version': projection['sheet_version'],
        'interpretation': 'native_or_specifically_attributed_correspondence_not_function_probability'}
    return {'version': VERSION, 'axis': 'A102', 'scope': scope,
        'comparative': comparative,
        'execution_findings': received_execution_findings(store, context, set(report['records'])),
        'experimental': experimental,
        'dependencies': dependency_links(experimental, native, projection['tool_attachments']),
        'child_controller_progress': report['controller_progress'],
        'combined_scientific_score': None,
        'combination_status': 'separate_quantities_no_combination_policy'}


def received_reports(store, *, context, structure_repository, axis_reference):
    """Interpret original immediate-child returns using this parent's receipts.

    The runtime's authenticated return reader proves the original child, form,
    contract and frozen facts. Neither a shared Source inventory nor a private
    child sheet can stand in for an admitted return. Repeated delivery retains
    one numerical identity per original sheet/component, including legacy A111.
    """
    from .episode_return_records import EpisodeReturnRecords
    from .a102_experimental_evidence import experimental_evidence, dependency_links
    from .a102_hpc import received_execution_findings
    reader = EpisodeReturnRecords(store, context.run_id, failure_prefix='a102_received_')
    reports, seen, cells, comparisons, attachments = [], set(), {}, {}, {}
    for child, form, schema in reader.received_attempts(context):
        if child.path[:-1] != context.path or not is_structural_report_schema(schema):
            continue
        if plain(child.assignment).get('selection', {}).get('evidence_axis') != plain(axis_reference):
            continue
        key = canonical([child.episode_id, form])
        if key in seen:
            continue
        seen.add(key)
        resolved = resolve_report(store, form, context=context, structure_repository=structure_repository)
        reports.append({'reporting_episode_id': child.episode_id,
            'commissioned_goal': plain(child.request)['goal'],
            'commissioned_scope': plain(child.scope), 'components': resolved})
        for result in resolved['experimental']['records']:
            for cell in result['cells']:
                cells[(cell['sheet_ref'], cell['component'])] = cell
        for comparison in resolved['comparative']['native_comparisons']:
            comparisons[comparison['source_ref']] = comparison
        for attachment in resolved['comparative']['tool_attachments']:
            attachments[attachment['source_ref']] = attachment
    experimental = experimental_evidence(structure_repository, context, list(cells.values()))
    return {'version': VERSION, 'axis': 'A102', 'scope': plain(context.scope),
        'reports': reports, 'experimental': experimental,
        'execution_findings': received_execution_findings(store, context, set(context.received_record_refs)),
        'dependencies': dependency_links(experimental, comparisons.values(), attachments.values()),
        'numerical_ownership': 'original_source_and_component; no_duplicate_axis_contribution',
        'combined_scientific_score': None,
        'combination_status': 'separate_quantities_no_combination_policy'}
