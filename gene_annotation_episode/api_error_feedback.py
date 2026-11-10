"""Keep complete API failure messages in the returned operational feedback."""
from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping


def is_api_error_return(value):
    """Recognize explicit returned failures, including native API job states."""
    if not isinstance(value, Mapping):
        return False
    statuses = (value.get('status'), value.get('state'), value.get('native_response_state'))
    http_status = value.get('http_status')
    return (any(isinstance(status, str) and status in {
        'invalid', 'failed', 'interrupted', 'unavailable', 'error'} for status in statuses)
        or type(http_status) is int and http_status >= 400
        or any(value.get(name) for name in (
            'error', 'errors', 'failure', 'failure_code', 'projection_errors', 'feedback'))
        or any(is_api_error_return(value.get(name)) for name in ('result', 'event', 'facts')))


def api_error_response(snapshot):
    """Return the complete received response body, without a presentation cap."""
    return {'http_status': snapshot.transport.get('status'),
        'media_type': snapshot.media_type,
        'body': snapshot.content.decode('utf-8', errors='replace')}


def api_error_feedback(error, *, snapshot=None):
    """Preserve received diagnostics; artifact handles do not replace the error."""
    feedback = {'exception_type': type(error).__name__, 'message': str(error)}
    for name in ('detail', 'diagnostic', 'operational'):
        value = getattr(error, name, None)
        if value is not None:
            feedback[name] = deepcopy(value)
    cause = error.__cause__
    if cause is not None and cause is not error:
        feedback['exception_cause'] = {
            'exception_type': type(cause).__name__, 'message': str(cause)}
    snapshot = getattr(error, 'snapshot', None) or snapshot
    if snapshot is not None:
        feedback['response'] = api_error_response(snapshot)
    return feedback
