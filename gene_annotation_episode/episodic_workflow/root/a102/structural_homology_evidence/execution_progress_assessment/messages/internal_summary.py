"""Where the episode stands: the job it was handed, every check of it the Episode holds, what its units did and
what each earned. A pure function of the view; the job and its checks are read from the job ledger rows in the
Episode's custody (``view.records``), never from a service.

Carried from the old ``internal_summary.py`` (``MonitorSummary.decision_context``), ``decision_state.py`` and
``received_progress.py`` (``ReceivedProgress``, ``OwnProgress``): the received progress is the check rows the
commissioner passed (the baseline), the check rows this monitor's own units wrote and the check rows its dependency
monitors returned, in receipt order. Fields of the old decision state that came from the old runner (the pending
work, the report lifecycle and deliveries, the recorded-journal views) are not carried.

What the job has depends on the kind of its route, read from the handoff row: ``log_names`` are the logs a job of
that kind keeps (``job_progress.LOGS``: two for a local and a PBS job, none for an API job) and ``event_target``
is named by a local job only. ``task.py`` offers a log window and a wait only for a job that has them."""
from yield_control import YieldState

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_progress import (
    LOGS, check_view, held_checks, progress_information)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import JOB_LEDGER


def _unit(outcome):
    """One completed unit, as later decisions need it: the action, how it ended and what it named."""
    if outcome['kind'] == 'child':
        return {'action': 'monitor_dependency', 'dependency_handle': outcome['arguments']['dependency_handle'],
                'status': 'completed', 'dependency_credit': outcome['report']['credit'],
                **outcome['report']['finding']}
    result = outcome['outcome']
    unit = {'action': outcome['tool'], 'status': result['status']}
    if result['status'] != 'completed':
        return {**unit, 'failure_code': result['failure']['code']}
    if outcome['tool'] == 'progress_observe':
        return {**unit, 'check_ref': result['check_ref'], 'new_information': result['informative']}
    if outcome['tool'] == 'progress_read':
        return {**unit, 'check_ref': result['check_ref']}
    if outcome['tool'] == 'progress_log':
        return {**unit, 'log': result['name'], 'offset': result['offset'], 'bytes': result['bytes']}
    return {**unit, 'woke_on': result['woke_on']}


def _last(outcome, unit):
    """The last unit with what only the next decision needs of it: the text of its log window, the detail of its
    failed request. (A check it made or read is in ``checks``.)"""
    if unit['status'] != 'completed':
        return {**unit, 'failure_detail': outcome['outcome']['failure']['detail']}
    if unit['action'] == 'progress_log':
        return {**unit, 'text': outcome['outcome']['text']}
    return unit


def internal_summary(view):
    parent, records = view.parent_input, view.records
    fields, baseline = parent['requested_fields'], parent['known_progress_refs']
    ledger = records.table(JOB_LEDGER)
    target = ledger.get(parent['handoff_ref'])
    checks = [{**check_view(row, fields), 'made_by': 'commissioner' if row['id'] in baseline else 'this_monitor'}
              for row in held_checks(records, target['job'])]
    own = [check for check in checks if check['made_by'] == 'this_monitor']
    dependencies = []
    for ref in parent['dependency_handoff_refs']:
        row = ledger.get(ref)
        seen = [check_view(item, fields) for item in held_checks(records, row['job'])]
        dependencies.append({'handle': row['job'], 'handoff_ref': ref, 'resource_id': row['detail']['resource_id'],
                             'resource_kind': row['detail']['kind'], 'submitted_at': row['at'],
                             'check_refs': [item['check_ref'] for item in seen],
                             'latest_check': seen[-1] if seen else None})
    scores = (list(view.controller_state.as_record()['scores'])
              if isinstance(view.controller_state, YieldState) else [])
    units, windows, receipts, cursor = [], [], [], 0
    for index, outcome in enumerate(view.outcomes):
        unit = _unit(outcome)
        if index < len(scores):
            unit['credit_earned'] = scores[index]
        units.append(unit)
        if outcome['kind'] == 'tool' and unit['status'] == 'completed':
            if unit['action'] == 'progress_log':
                windows.extend([outcome['outcome']['window_ref'], outcome['outcome']['content_ref']])
            if unit['action'] == 'progress_wait':
                receipts.extend(outcome['outcome']['receipt_refs'])
                cursor = max(cursor, outcome['outcome']['event_cursor'])
    if units:
        units[-1] = _last(view.outcomes[-1], units[-1])
    information = progress_information(records, baseline, fields, parent['information_unit'])
    return {**parent,
            'job': {'handle': target['job'], 'resource_id': target['detail']['resource_id'],
                    'resource_kind': target['detail']['kind'], 'submitted_at': target['at'],
                    'launch_estimates': target['detail']['estimates'],
                    'event_target': target['detail']['native'].get('event_target'),
                    'log_names': list(LOGS[target['detail']['kind']])},
            'checks': checks,
            'latest': own[-1] if own else None,
            'received_check_refs': [row['id'] for row in held_checks(records) if row['id'] not in baseline],
            'dependencies': dependencies,
            'units': units,
            'log_window_refs': list(dict.fromkeys(windows)),
            'event_receipt_refs': list(dict.fromkeys(receipts)),
            'event_cursor': cursor,
            'monitoring_information': information}
