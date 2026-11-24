"""Where the API job stands: the assignment, what each unit's tool returned (operations done, recorded facts,
the handoff and result records, acquired records, the credit units), the latest outcome and the operational
progress of each API operation, as a pure function of the loop's view.

Carried from the old ``decision_state.py``, ``decision_presentation.py`` (the value presentation: ``_operational_scalars``,
``_measurements``, ``_qualifications``, ``_operational_facts``, ``_api_progress``, ``_own_outcome``, ``_band``)
and ``internal_summary.py``."""
from collections.abc import Mapping
import math
import re

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.api_error_feedback import (
    is_api_error_return)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

_CODE = re.compile('[A-Za-z_][A-Za-z0-9_.:+/\\-]{0,127}\\Z')
_CODE_FIELDS = frozenset({'state', 'status', 'kind', 'lifecycle_state', 'liveness', 'submission_outcome', 'failure_code', 'code', 'category', 'reason', 'unavailable_reason', 'parse_status', 'qualification', 'population_coverage', 'bucket_window_status', 'count_exactness', 'count_availability', 'fraction_unavailable_reason', 'response_profile', 'representation', 'size_unit', 'progress_unit', 'ended_by', 'end_reason', 'result_status', 'report_delivery', 'cause_code', 'exception_type'})
_NUMBER_FIELDS = frozenset({'http_status', 'returncode', 'retry_after_seconds', 'elapsed_seconds', 'captured_bytes', 'bytes_captured', 'size_bytes', 'reported_total', 'returned_count', 'returned_row_count', 'valid_row_count', 'invalid_row_count', 'requested_offset', 'requested_limit', 'next_offset', 'offset', 'limit', 'completed_rows', 'total_rows', 'completed_sequences', 'total_sequences', 'completed_queries', 'total_queries', 'completed_bytes', 'total_bytes', 'percent_complete', 'progress_fraction'})
_BOOLEAN_FIELDS = frozenset({'response_complete', 'body_complete', 'handoff_ready', 'result_available', 'return_available', 'retry_selected', 'request_sent', 'submission_attempted', 'complete'})
_MEASUREMENT_NAMES = frozenset({'completed_rows', 'total_rows', 'completed_sequences', 'total_sequences', 'completed_queries', 'total_queries', 'completed_bytes', 'total_bytes', 'captured_bytes', 'size_bytes', 'percent_complete', 'progress_fraction', 'elapsed_seconds'})
_MEASUREMENT_UNITS = frozenset({'rows', 'sequences', 'queries', 'bytes', 'percent', 'fraction', 'seconds'})


def _number(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _returned_value(value):
    """Copy returned diagnostics without filtering their fields or text."""
    if isinstance(value, Mapping):
        return {name: _returned_value(child) for name, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_returned_value(child) for child in value]
    return value


def _operational_scalars(value):
    """Select only named, typed operational facts; never traverse other data."""
    if not isinstance(value, Mapping):
        return {}
    result = {}
    for name in sorted(_CODE_FIELDS | _NUMBER_FIELDS | _BOOLEAN_FIELDS):
        if name not in value:
            continue
        item = value[name]
        if item is None or (name in _CODE_FIELDS and type(item) is str and _CODE.fullmatch(item)) or (name in _NUMBER_FIELDS and _number(item)) or (name in _BOOLEAN_FIELDS and type(item) is bool):
            result[name] = item
    return result


def _measurements(value):
    if not isinstance(value, (list, tuple)):
        return None
    result = []
    for row in value:
        if not isinstance(row, Mapping) or type(row.get('name')) is not str or row['name'] not in _MEASUREMENT_NAMES or (type(row.get('unit')) is not str) or (row['unit'] not in _MEASUREMENT_UNITS) or ('value' not in row) or (not (row['value'] is None or _number(row['value']))):
            continue
        result.append({key: row[key] for key in ('name', 'value', 'unit')})
    return result if result or not value else None


def _qualifications(value):
    if value is None or (type(value) is str and _CODE.fullmatch(value)):
        return value
    if isinstance(value, Mapping):
        return _operational_scalars(value) or None
    if isinstance(value, (list, tuple)):
        return [_qualifications(item) if not isinstance(item, (list, tuple)) else None for item in value]
    return None


def _operational_facts(value):
    """A finite fact projection, independent of arbitrary result/control trees."""
    if is_api_error_return(value):
        return _returned_value(value)
    result = _operational_scalars(value)
    if not isinstance(value, Mapping):
        return result
    for name in ('page', 'pagination', 'progress'):
        if name in value:
            selected = _operational_scalars(value[name])
            if selected:
                result[name] = selected
    for name in ('qualification', 'qualifications'):
        if name in value:
            result[name] = _qualifications(value[name])
    if 'measurements' in value:
        result['measurements'] = _measurements(value['measurements'])
    return result


def _api_progress(value):
    if not isinstance(value, Mapping):
        return {}
    result = {}
    for operation, row in value.items():
        if type(operation) is not str or not operation.startswith('api.') or (not _CODE.fullmatch(operation)) or (not isinstance(row, Mapping)):
            continue
        if is_api_error_return(row) or is_api_error_return(row.get('facts')):
            result[operation] = _returned_value(row)
            continue
        selected = _operational_scalars(row)
        facts = _operational_facts(row.get('facts'))
        if facts:
            selected['facts'] = facts
        if selected:
            result[operation] = selected
    return result


def _own_outcome(value):
    if is_api_error_return(value) or (isinstance(value, Mapping) and is_api_error_return(value.get('result'))):
        return _returned_value(value)
    selected = _operational_scalars(value)
    if isinstance(value, Mapping):
        if value.get('feedback') is not None:
            selected['feedback'] = _returned_value(value['feedback'])
        for name in ('result', 'child_completion'):
            facts = _operational_facts(value.get(name))
            if facts:
                selected[name] = facts
    return selected


def internal_summary(view):
    summary = {**view.parent_input, 'operations_done': 0, 'capabilities': None, 'facts': {},
               'handoff_refs': [], 'result_refs': [], 'handoff_established': False, 'execution_completed': False,
               'acquired_record_count': 0, 'credit_units': None, 'api_received_progress': {},
               'last_local_outcome': None, 'feedback': None, 'lookups': [], 'job_identity': None,
               'request_identity': None, 'submission_outcome': None}
    for outcome in view.outcomes:
        tool, arguments, returned = outcome['tool'], outcome['arguments'], outcome['outcome']
        if tool == 'api_capabilities':
            summary['capabilities'] = returned['capabilities']
            continue
        if tool in ('knowledge_lookup', 'launch_instruction_lookup'):
            summary['lookups'].append(returned)
            continue
        summary['operations_done'] += 1
        summary['last_local_outcome'] = returned
        summary['feedback'] = returned.get('feedback')
        summary['credit_units'] = returned['credit_units']
        summary['facts'] = returned['facts']
        summary['handoff_refs'] = summary['handoff_refs'] + [ref for ref in returned['handoff_refs']
                                                             if ref not in summary['handoff_refs']]
        summary['result_refs'] = summary['result_refs'] + [ref for ref in returned['result_refs']
                                                           if ref not in summary['result_refs']]
        summary['handoff_established'] = summary['handoff_established'] or returned['handoff_established']
        summary['execution_completed'] = returned['execution_completed']
        for name in ('job_identity', 'request_identity', 'submission_outcome'):
            if returned[name] is not None:
                summary[name] = returned[name]
        if tool == 'api_operation':
            summary['api_received_progress'][arguments['operation']] = returned
    summary['acquired_record_count'] = len(summary['result_refs'])
    summary['api_received_progress'] = _api_progress(summary['api_received_progress'])
    if summary['last_local_outcome'] is not None:
        summary['last_local_outcome'] = _own_outcome(summary['last_local_outcome'])
    if view.controller_state is not None:
        summary['action_yields'] = yield_table(view.controller_state, forecast_unit='credit')
    return summary
