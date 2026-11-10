"""Present original A107 work results beside its recorded completion credit.

Only the original own result, admitted child values and already authorized
receiver projections enter this adapter. It opens no source, computes no
correlation or qualification, and creates no functional verdict or score.
"""
from collections.abc import Mapping
from copy import deepcopy
import json


_EXPRESSION_PROFILES = frozenset({
    'a107_expression_components_v1', 'a107_expression_components_v2'})
_DETECTION_PROFILE = 'a107_genomic_detection_v1'
_NATIVE_PROFILES = _EXPRESSION_PROFILES | {_DETECTION_PROFILE}
_QUALIFICATION_VERSION = 'a107_received_qualification_v1'
_QUALIFICATIONS = {
    'partner.component_correspondence': 'Saved correspondence for the selected actual and reference component',
    'partner.requirement_evidence': 'Saved qualification of the selected source requirement evidence',
    'partner.detection_evidence': 'Saved qualification of the selected genomic detection',
    'partner.expression_evidence': 'Saved qualification of the selected measured expression feature',
    'partner.expression_locus_evidence': 'Saved qualification of expression against the selected genomic locus',
}
_CELL_SCOPE = 'reference_experimental_partner_components'
_ENVELOPE_FIELDS = ('source_ref', 'request_ref', 'hpc_result_ref', 'target_ref',
    'target_regions', 'scope', 'operation', 'scientific_profile', 'status',
    'scientific_admission', 'input_source_ref', 'dependencies')
_EXPRESSION_FIELDS = ('version', 'dataset_id', 'origin', 'selection', 'quantity',
    'features', 'sample_scope', 'pairs', 'pairs_retained', 'components',
    'dependence', 'detection_criteria', 'limitations')
_DETECTION_FIELDS = ('component_ref', 'target_ref', 'target_regions', 'present',
    'scope', 'absence_meaning', 'searched_cds', 'uncertain_cds', 'record_scopes',
    'native_hits', 'native_search_complete', 'all_actual_cds_in_search',
    'native_method', 'native_program_version', 'binding_refs', 'native_source_ref',
    'database_source_ref', 'snapshot_ref')


def _native(row):
    native = row.get('native_components')
    if isinstance(native, Mapping) and row.get('axis') == 'A107':
        envelope = {name: deepcopy(row[name]) for name in _ENVELOPE_FIELDS if name in row}
    elif isinstance(row.get('version'), str) and row['version'] in _NATIVE_PROFILES:
        native, envelope = row, {}
    else:
        return None
    profile = native.get('version')
    if isinstance(profile, str) and profile in _EXPRESSION_PROFILES:
        return {'result': 'Saved matched-condition expression measurements and descriptive components',
            **envelope,
            'expression': {name: deepcopy(native[name]) for name in _EXPRESSION_FIELDS if name in native},
            'quantity_scope': 'Original measured feature and condition; local correspondence does not make the quantity region-specific',
            'value_meaning': 'Native descriptive quantities and source-criterion comparisons; original action earned credit is reported separately'}
    if profile != _DETECTION_PROFILE:
        return None
    detection = native.get('detection', {})
    artifacts = {name: {key: deepcopy(value) for key, value in artifact.items()
        if key != 'bytes_base64'} for name, artifact in native.get('native_artifacts', {}).items()
        if isinstance(artifact, Mapping)}
    return {'result': 'Saved native genomic detection over the received sequence and annotation collection',
        **envelope,
        **{name: deepcopy(native[name]) for name in ('dataset_id', 'origin', 'selection') if name in native},
        'detection': {name: deepcopy(detection[name]) for name in _DETECTION_FIELDS if name in detection},
        'native_returncode': native.get('native_returncode'),
        'native_artifacts': artifacts,
        'limitations': deepcopy(native.get('limitations', [])),
        'value_meaning': 'Scoped native detection; no inferred required partnership, sample origin or function'}


def _qualification(row):
    if (row.get('version') != _QUALIFICATION_VERSION
            or not isinstance(row.get('operation'), str) or row['operation'] not in _QUALIFICATIONS):
        return None
    native = row.get('result')
    if not isinstance(native, Mapping):
        return None
    # This is the saved purpose-specific qualification, not a newly authored
    # report summary. Keep original criteria, mappings, missing operands and
    # delivered numerical subsets; omit redundant generic commentary.
    facts = {name: deepcopy(value) for name, value in native.items()
        if name != 'interpretation'}
    return {'result': _QUALIFICATIONS[row['operation']],
        **{name: deepcopy(row[name]) for name in ('source_ref', 'request_ref',
            'target_ref', 'target_regions', 'scope', 'operation',
            'qualification_dependencies') if name in row},
        'qualification': facts,
        'value_meaning': 'Saved qualification for this particular use; not the parent action earned credit'}


def _partner_components(row):
    if row.get('evaluation_scope') == _CELL_SCOPE and 'component' in row:
        return {'result': 'Delivered experimental partner component',
            **{name: deepcopy(row[name]) for name in ('sheet_ref', 'evidence_source_ref',
                'data_source_ref', 'subject_ref', 'partner_ref', 'experiment_ref',
                'endpoint_ref', 'normalization_ref', 'reference_condition_ref',
                'omitted_condition_ref', 'addback_condition_ref', 'function_ref',
                'component', 'value', 'lower', 'upper', 'unit', 'status', 'origin',
                'bound_kind', 'unavailable_reason', 'formula_code', 'comparison_checks',
                'arm_metadata', 'evaluation_scope', 'target_correspondence',
                'partner_necessity', 'statistical_uncertainty') if name in row}}
    views = row.get('returned_views')
    if isinstance(views, Mapping) and 'partner_components' in views and row.get('sheet_ref'):
        return {'result': 'Saved experimental partner components actually delivered to this receiver',
            **{name: deepcopy(row[name]) for name in ('sheet_ref', 'record_version',
                'source_refs', 'original_scope', 'receiving_scope', 'experimental_bindings',
                'components', 'experiment_assessment',
                'target_transfer', 'independence') if name in row},
            'delivered_cells': deepcopy(views['partner_components'])}
    return None


def _execution(row):
    if row.get('axis') != 'A107' or 'native_components' in row or 'status' not in row:
        return None
    if not (str(row.get('operation', '')).startswith('partner.')
            or row.get('version') == 'component_axis_native_v1'):
        return None
    return {'result': 'Received A107 native execution finding',
        **{name: deepcopy(row[name]) for name in ('source_ref', 'request_ref',
            'hpc_result_ref', 'operation', 'scientific_profile', 'scope',
            'target_ref', 'target_regions', 'resource_id', 'status', 'failure',
            'returncode', 'pbs_job_id', 'selection',
            'resolved_by_received_request_ref', 'meaning') if name in row}}


def _nodes(value):
    if isinstance(value, Mapping):
        yield value
        native = value.get('native_components')
        profile = native.get('version') if isinstance(native, Mapping) else None
        version = value.get('version')
        native_result = ((value.get('axis') == 'A107' and isinstance(profile, str) and profile in _NATIVE_PROFILES)
            or isinstance(version, str) and version in _NATIVE_PROFILES)
        qualification = (version == _QUALIFICATION_VERSION
            and isinstance(value.get('operation'), str) and value['operation'] in _QUALIFICATIONS)
        views = value.get('returned_views')
        partner = (value.get('evaluation_scope') == _CELL_SCOPE and 'component' in value
            or isinstance(views, Mapping) and 'partner_components' in views and value.get('sheet_ref'))
        execution = (value.get('axis') == 'A107' and 'native_components' not in value
            and 'status' in value and (str(value.get('operation', '')).startswith('partner.')
                or value.get('version') == 'component_axis_native_v1'))
        if native_result or qualification or partner or execution:
            return
        for child in value.values():
            yield from _nodes(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from _nodes(child)


def _original_partner_cells(value):
    if isinstance(value, Mapping):
        if value.get('evaluation_scope') == _CELL_SCOPE and value.get('sheet_ref') and value.get('component'):
            yield value['sheet_ref'], value['component']
        for child in value.values():
            yield from _original_partner_cells(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from _original_partner_cells(child)


def _references(value):
    if isinstance(value, Mapping):
        for child in value.values():
            yield from _references(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from _references(child)
    elif isinstance(value, str) and value.startswith('source_'):
        yield value


def completed_work_result(selection, outcome, received_records):
    """Retain exact original A107 output versions, never later qualifications."""
    if not isinstance(selection, Mapping) or not isinstance(outcome, Mapping):
        return None
    if selection.get('kind') == 'tool' and selection.get('tool') in {'source.read', 'source.locate'}:
        # A source identity in a read/window is not another delivery of its
        # complete numerical result. The common work report retains the actual
        # navigation outcome; full admitted results keep their receiver views.
        return None
    direct = {key: value for key, value in outcome.items() if key != 'received_axis_results'}
    original_refs = set(_references(direct))
    original_cells = set(_original_partner_cells(direct))
    operation = str(selection.get('tool', ''))
    related = operation.startswith('partner.') or any(
        node.get('option_id') == 'A107' or node.get('id') == 'A107' and node.get('slot') == 'evidence_axis'
        for node in _nodes(selection))
    results, limitations, seen = [], [], set()

    def append(row, *, received=False):
        nonlocal related
        result = _native(row) or _qualification(row) or _partner_components(row) or _execution(row)
        if result is None:
            return
        publication = result.get('source_ref') or result.get('sheet_ref')
        if received and (publication is None or publication not in original_refs):
            return
        if received and result.get('sheet_ref'):
            # The same sheet can arrive through several typed subset returns.
            # Later delivered components do not belong to an earlier action.
            if result.get('component') is not None:
                if (publication, result['component']) not in original_cells:
                    return
            elif 'delivered_cells' in result:
                delivered = [cell for cell in result['delivered_cells']
                    if (publication, cell['component']) in original_cells]
                if not delivered:
                    return
                result['delivered_cells'] = delivered
                selected = {cell['component'] for cell in delivered}
                result['components'] = {name: value for name, value in result.get('components', {}).items()
                    if name in selected}
        identity = (result['result'], publication, result.get('component')) if publication else json.dumps(
            result, sort_keys=True, separators=(',', ':'))
        if identity in seen:
            return
        seen.add(identity)
        related = True
        results.append(result)
        if result.get('unavailable_reason'):
            limitations.append({'sheet_ref': result.get('sheet_ref'),
                'component': result.get('component'), 'reason': result['unavailable_reason']})
        qualification = result.get('qualification', {})
        for field in ('missing', 'correspondence_missing', 'expression_criterion_missing'):
            if qualification.get(field):
                limitations.append({'source_ref': publication, field: deepcopy(qualification[field])})

    for row in _nodes(direct):
        append(row)
    for row in _nodes(outcome.get('received_axis_results', ())):
        append(row, received=True)
    if related:
        body = outcome.get('result')
        if isinstance(body, Mapping):
            facts = {name: deepcopy(body[name]) for name in ('request_ref',
                'commission_source_ref', 'hpc_result_ref', 'execution_status',
                'new_execution_requested', 'native_execution_requested', 'execution_owner',
                'qualification_refs', 'failure', 'returncode', 'completed') if name in body}
            if facts:
                results.append({'result': 'Recorded A107 execution or qualification publication outcome', **facts})
    if not related:
        return None
    admitted = outcome.get('admitted_child_return')
    if isinstance(admitted, Mapping) and 'controller_progress' in admitted:
        results.append({'result': 'Delivered child-local investigation progress',
            'value': admitted['controller_progress'],
            'meaning': 'Child task units; original receiving-parent earned credit is reported separately'})
    if not results:
        limitations.append({'reason': 'No concrete A107 component or qualification was included in this action or its admitted resolved results'})
    return {'axis': 'A107', 'results': results, 'limitations': limitations}
