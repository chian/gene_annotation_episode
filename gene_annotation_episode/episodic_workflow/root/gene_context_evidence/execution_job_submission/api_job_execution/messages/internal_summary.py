"""Where the API job stands, as a pure function of the loop's view (carried from ``internal_summary.py``,
``decision_state.py``, ``task_state.py`` and the value presentation of ``decision_presentation.py``).

Own fields of the old decision context: ``execution_assignment`` (the parent input) and ``execution_progress``
(here the operations so far, the handoff and result references and the facts the service reported). The credit is
the credit the API service executor's credit view gave after the last unit that reported one; a wait, a capabilities
read, a lookup and a failed operation report none and keep it. The presentation of what the operations returned
(``_operational_scalars``, ``_measurements``, ``_qualifications``, ``_operational_facts``, ``_api_progress``,
``_own_outcome``) keeps its old selection of typed operational facts; a complete recorded API error is kept whole.
"""
from collections.abc import Mapping
import math
import re

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.api_error_feedback import (
    is_api_error_return)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

INITIAL_CREDIT = 0.0
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
    summary = {**view.parent_input, 'steps': [], 'credit': INITIAL_CREDIT, 'handoff_refs': [], 'result_refs': [],
               'completed': False, 'facts': {}, 'last_status': None, 'last_outcome': None, 'feedback': None,
               'lookups': [], 'api_progress': {}, 'job_identity': None, 'yield_table': None}
    progress = {}
    for unit in view.outcomes:
        outcome = unit['outcome']
        summary['steps'].append({'tool': unit['tool'], 'operation': outcome.get('operation'),
                                 'status': outcome['status'], 'event': outcome.get('event'),
                                 'feedback': outcome.get('feedback')})
        summary['last_status'] = outcome['status']
        summary['last_outcome'] = outcome
        summary['feedback'] = outcome.get('feedback')
        if unit['tool'] in ('launch_instructions', 'tool_knowledge'):
            summary['lookups'].append(outcome)
            continue
        if unit['tool'] == 'service_operation':
            progress[unit['arguments']['operation']] = outcome
        if outcome.get('credit') is not None:
            summary['credit'] = outcome['credit']
        for name in ('handoff_refs', 'result_refs'):
            summary[name] += [ref for ref in outcome.get(name, ()) if ref not in summary[name]]
        summary['completed'] = summary['completed'] or bool(outcome.get('completed'))
        summary['facts'].update(outcome.get('facts') or {})
        event = outcome.get('event')
        if event is not None and event['native_handle'] is not None:
            summary['job_identity'] = event['native_handle']
    summary['api_progress'] = _api_progress(progress)
    if summary['last_outcome'] is not None:
        summary['last_outcome'] = _own_outcome(summary['last_outcome'])
    if view.controller_state is not None:
        summary['yield_table'] = yield_table(view.controller_state, forecast_unit='credit')
    return summary
