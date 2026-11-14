"""Automatic current scientific scoring projection for this process."""
from copy import deepcopy
import json
from ..communication import plain, validate_closed_schema, validate_form
from gene_annotation_episode.domain import ContractError, canonical, obj
from ..episode_return_records import EpisodeReturnRecords
from ..library.component_received_reports import (PATHS, SCORING_SHEET_VERSION, cell_views, repository, _component_records, dependence, native_dependence, cross_dependence, mark_native_execution)
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
    from ..library.component_native_received_records import received_components, execution_findings
    from ..a107.a107_qualification import received_qualifications
    from ..a110.a110_qualification import received as chemical_qualifications
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


