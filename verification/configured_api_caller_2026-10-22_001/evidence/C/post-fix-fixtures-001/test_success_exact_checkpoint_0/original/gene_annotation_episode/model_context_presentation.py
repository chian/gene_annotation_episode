"""Pure, captured model pages over an episode's complete calculation context.

Only the declared own-action history array is paged. The caller retains the
original context for calculations and the saved presentation for model replay;
this module reads neither live history nor available tools outside that input.
"""
from __future__ import annotations

import hashlib
import json

from method_loop.durable import canonical, content_digest
from method_loop.identities import UnitRef

from .domain import ContractError


VERSION = 'episode_model_presentation_v1'
MODE = 'bounded_wait_history_v1'
REQUEST_VERSION = 'runtime_model_call_request_v2'
_PAGE_VERSION = 'bounded_wait_history_page_v1'
_HISTORY = 'own_completed_action_history'
_PAGE = 'own_completed_action_history_page'
_HISTORY_PATH = 'context.waiting_support.' + _HISTORY


def _conflict(path, cause=None):
    error = ContractError('model_presentation_contract_conflict', detail={'path': path})
    if cause is None:
        raise error
    raise error from cause


def _copy(value, path):
    """Independent finite JSON, with canonical key order and UTF-8 identity."""
    try:
        text = canonical(value)
        text.encode('utf-8')
        return json.loads(text)
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        _conflict(path, error)


def _index(value, path):
    if type(value) is not int or value < 0:
        _conflict(path)


def _owner(run_id, episode_id, before_decision_index):
    for name, value in (('run_id', run_id), ('episode_id', episode_id)):
        if type(value) is not str or not value:
            _conflict(name)
        _copy(value, name)
    _index(before_decision_index, 'before_decision_index')


def model_context_presentation_definition(*, preview_size: int) -> dict:
    """Describe the caller's existing preview operand, never a work budget."""
    _index(preview_size, 'preview_size')
    return {
        'version': MODE,
        'history_path': 'waiting_support.' + _HISTORY,
        'page_size_source': 'restoration.preview_size',
        'preview_size': preview_size,
        'selection': 'latest_completed_rows_in_original_order',
        'serialization': 'canonical_key_order_then_python_json_default_ascii_v1',
        'lookup_tool': 'episode.history',
        'lookup_source': 'original_context.tools',
    }


def _validate_history(history, *, episode_id, before_decision_index):
    if not isinstance(history, list):
        _conflict(_HISTORY_PATH)
    previous_unit, decisions = -1, set()
    for position, row in enumerate(history):
        path = f'{_HISTORY_PATH}[{position}]'
        if not isinstance(row, dict):
            _conflict(path)
        if row.get('episode_id') != episode_id:
            _conflict(path + '.episode_id')
        unit = row.get('unit_index')
        _index(unit, path + '.unit_index')
        if unit <= previous_unit:
            _conflict(path + '.unit_index')
        previous_unit = unit
        for field in ('controller_input', 'controller_step'):
            if field not in row:
                _conflict(path + '.' + field)
        decision = row.get('decision_index')
        if decision is not None:
            _index(decision, path + '.decision_index')
            if decision >= before_decision_index or decision in decisions:
                _conflict(path + '.decision_index')
            decisions.add(decision)
        unit_ref = row.get('unit_ref')
        if unit_ref is not None:
            try:
                reference = UnitRef.from_record(unit_ref)
            except (TypeError, ValueError) as error:
                _conflict(path + '.unit_ref', error)
            if reference.episode_id != episode_id or reference.unit_index != unit:
                _conflict(path + '.unit_ref')


def _lookup(context):
    catalog = context.get('tools')
    if not isinstance(catalog, list):
        return {'availability': 'unknown',
                'unavailable_reason': 'saved_tool_catalog_unavailable'}
    if any(isinstance(tool, dict) and tool.get('name') == 'episode.history'
           for tool in catalog):
        return {'availability': 'available', 'unavailable_reason': None}
    return {'availability': 'unavailable',
            'unavailable_reason': 'episode_history_not_in_saved_catalog'}


def _project(context, *, run_id, episode_id, before_decision_index, preview_size):
    if 'waiting_support' not in context:
        return
    support = context['waiting_support']
    if not isinstance(support, dict):
        _conflict('context.waiting_support')
    if _PAGE in support:
        _conflict('context.waiting_support.' + _PAGE)
    if _HISTORY not in support:
        return
    history = support[_HISTORY]
    _validate_history(history, episode_id=episode_id,
                      before_decision_index=before_decision_index)
    page = history[-preview_size:] if preview_size else []
    start = len(history) - len(page)
    decisions = [row['decision_index'] for row in page
                 if row.get('decision_index') is not None]
    lookup = _lookup(context)
    available = lookup['availability'] == 'available'
    support[_PAGE] = {
        'version': _PAGE_VERSION,
        'run_id': run_id,
        'episode_id': episode_id,
        'before_decision_index': before_decision_index,
        'page_size_source': 'restoration.preview_size',
        'preview_size': preview_size,
        'order': 'original_unit_index_ascending',
        'total_rows': len(history),
        'included_rows': len(page),
        'omitted_rows': start,
        'range': {'start': start, 'end_exclusive': len(history),
                  'unit': 'completed_own_action_history_position'},
        'first_unit_index': page[0]['unit_index'] if page else None,
        'last_unit_index': page[-1]['unit_index'] if page else None,
        'decision_indices': decisions,
        'identity_fields': ['episode_id', 'unit_index', 'unit_ref', 'decision_index'],
        'included_rows_without_decision_identity': len(page) - len(decisions),
        'included_rows_without_unit_ref': sum(row.get('unit_ref') is None for row in page),
        'raw_history_sha256': content_digest(history),
        'included_history_sha256': content_digest(page),
        'history_is_complete': start == 0,
        'history_lookup': lookup,
        'exact_included_records': ({'tool': 'episode.history', 'arguments': {
            'view': 'records', 'decision_indices': decisions}}
            if available and decisions else None),
        'discover_older_decisions': ({'tool': 'episode.history', 'arguments': {
            'view': 'index', 'offset': 0, 'limit': max(1, preview_size)}}
            if available else None),
        'history_result_row_path': 'result.records[*].controller_observation',
        'history_result_step_path': 'result.records[*].controller_observation.step',
        'calculation_context': 'runtime_model_calls.request.context',
    }
    support[_HISTORY] = page


def _prepare(context, *, run_id, episode_id, before_decision_index, preview_size):
    _owner(run_id, episode_id, before_decision_index)
    definition = model_context_presentation_definition(preview_size=preview_size)
    projected = _copy(context, 'context')
    if not isinstance(projected, dict):
        _conflict('context')
    original_hash = content_digest(projected)
    _project(projected, run_id=run_id, episode_id=episode_id,
             before_decision_index=before_decision_index, preview_size=preview_size)
    # The provider preserves mapping insertion order. Canonical key order here
    # makes its unchanged serializer identical on first dispatch and replay.
    projected = _copy(projected, 'model_presentation.context')
    text = json.dumps(projected, allow_nan=False)
    encoded = text.encode('utf-8')
    return _copy({
        'version': VERSION,
        'definition': definition,
        'run_id': run_id,
        'episode_id': episode_id,
        'before_decision_index': before_decision_index,
        'original_context_sha256': original_hash,
        'presented_context_sha256': content_digest(projected),
        'model_input_text_sha256': hashlib.sha256(encoded).hexdigest(),
        'model_input_char_count': len(text),
        'model_input_utf8_byte_count': len(encoded),
        'context': projected,
    }, 'model_presentation')


def prepare_model_context_presentation(context, *, run_id: str, episode_id: str,
        before_decision_index: int, preview_size: int) -> dict:
    """Capture one declared latest-N model page without altering raw inputs."""
    return _prepare(context, run_id=run_id, episode_id=episode_id,
                    before_decision_index=before_decision_index,
                    preview_size=preview_size)


def validate_model_context_presentation(presentation, *, original_context,
        run_id: str, episode_id: str, before_decision_index: int,
        preview_size: int) -> dict:
    """Validate a stored view against its original raw input; return that view.

    Recomputing the pure declared projection is only an integrity comparison.
    The returned copy comes from the supplied stored capture, never live state
    or a refreshed presentation. Canonical comparisons preserve numeric types
    and the sign of floating zero, which Python container equality can lose.
    """
    supplied = _copy(presentation, 'model_presentation')
    expected = _prepare(original_context, run_id=run_id, episode_id=episode_id,
                        before_decision_index=before_decision_index,
                        preview_size=preview_size)
    if not isinstance(supplied, dict) or set(supplied) != set(expected):
        _conflict('model_presentation')
    for field in expected:
        if canonical(supplied[field]) != canonical(expected[field]):
            _conflict('model_presentation.' + field)
    return supplied


__all__ = ['VERSION', 'MODE', 'REQUEST_VERSION',
           'model_context_presentation_definition',
           'prepare_model_context_presentation',
           'validate_model_context_presentation']
