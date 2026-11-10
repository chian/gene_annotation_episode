"""Preserve a decision-source failure separately from usable returned evidence."""
from __future__ import annotations

import json

from method_loop.durable import canonical


def record_source_failure(store, run_id, episode_id, decision_index, error, *,
                          category='decision_source', cause_code='model_call_failed'):
    store.db.execute('CREATE TABLE IF NOT EXISTS runtime_source_failures ('
        'run_id TEXT NOT NULL,episode_id TEXT NOT NULL,decision_index INTEGER NOT NULL,'
        'failure TEXT NOT NULL,PRIMARY KEY(run_id,episode_id,decision_index))')
    failure = {'category': category, 'cause_code': cause_code,
        'exception_type': type(error).__name__}
    diagnostic = getattr(error, 'diagnostic', None)
    if isinstance(diagnostic, dict) and diagnostic.get('cause_code') in {
            'input_too_large', 'provider_output_incomplete'}:
        # Only controlled provider metadata reaches the parent, never its
        # rejected input, private history, traceback or raw transport message.
        failure['cause_code'] = diagnostic['cause_code']
        if diagnostic['cause_code'] == 'input_too_large':
            for name in ('input_chars', 'provider_max_chars'):
                if type(diagnostic.get(name)) is int and diagnostic[name] >= 0:
                    failure[name] = diagnostic[name]
    if isinstance(error, ValueError) and str(error) == 'original_handoff_not_received_by_this_parent':
        # The authority guard remains an error. Expose its controlled reason
        # rather than giving the model only an opaque ValueError; the private
        # traceback address is deliberately absent from TASK presentation.
        failure.update(code='original_handoff_not_received_by_this_parent', recovery=(
            'This episode has not received the original job handoff. If an execution child '
            'still owns that job, await its original typed return. For already completed '
            'work, repair/redeliver the existing typed handoff or result as applicable. '
            'Preserve the original submitted job; this error does not authorize replacement work.'))
    store.db.execute('INSERT OR IGNORE INTO runtime_source_failures VALUES(?,?,?,?)',
        (run_id, episode_id, decision_index, canonical(failure)))
    return failure


def child_completion_status(store, run_id, child_id, completion, *, delivery):
    failure = None
    if completion['ended_by'] == 'source_failed':
        table = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='runtime_source_failures'").fetchone()
        row = (store.db.execute('SELECT failure FROM runtime_source_failures WHERE run_id=? '
            'AND episode_id=? ORDER BY decision_index DESC LIMIT 1', (run_id, child_id)).fetchone()
            if table is not None else None)
        failure = ({'category': 'decision_source', 'cause_code': 'source_failed'}
            if row is None else json.loads(row[0]))
    return {'ended_by': completion['ended_by'], 'end_reason': completion['end_reason'],
        'result_status': 'partial' if failure is not None else 'returned',
        'report_delivery': delivery, 'failure': failure}
