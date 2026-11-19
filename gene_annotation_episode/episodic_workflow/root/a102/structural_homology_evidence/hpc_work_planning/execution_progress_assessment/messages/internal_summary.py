"""Where the episode stands, carried from the old ``internal_summary.py`` (``MonitorSummary.decision_context``),
``decision_state.py`` (the fields that come from the view), ``received_progress.py`` (``ReceivedProgress``,
``OwnProgress``) and the goal summary of ``goal.py`` (``MonitorGoal.planning_context``): a pure function of the
view.

Received progress is the assignment's ``known_progress_refs``, the progress refs of this monitor's own action
outcomes (in outcome order) and the progress its child monitors returned. The snapshots are those the observe
tool's outcomes and the children's returns carry; a baseline ref has no snapshot here and raises when the credit
needs it (``credit.py``). Fields of the old decision state that came from the old runner (the pending work, the
report lifecycle and deliveries, the recorded-journal views) are not carried."""
from yield_control import YieldState

from ..credit import information_projection

_MEANING = ('Exposed direct relationships and already delivered observations. Empty measurements/log windows do '
            'not assert absence or a stall.')
_UNRESOLVED = 'Which exposed progress information would improve the original requested report?'
_DEFINITION = ('Actual received information under the monitoring projector; repeated identities and timestamps '
               'alone earn no credit.')


def _unique(values):
    return list(dict.fromkeys(values))


def internal_summary(view):
    parent = view.parent_input
    snapshots, own = {}, []
    last_outcome = None
    for outcome in view.outcomes:
        last_outcome = outcome
        if outcome['kind'] == 'tool':
            result = outcome['outcome']
            own.extend(result['progress_refs'])
            if 'snapshot' in result and result['status'] != 'invalid':
                snapshots[result['snapshot']['progress_ref']] = result['snapshot']
        else:
            report = outcome['report']
            own.extend(report['progress_refs'])
            snapshots.update(report['progress_snapshots'])
    own = _unique(own)
    received = _unique([*parent['known_progress_refs'], *own])
    # The latest delivered observation of the assigned target, in receipt order.
    target = [snapshots[ref] for ref in own if ref in snapshots
              and snapshots[ref]['target_handle'] == parent['target_handle']]
    latest = target[-1] if target else None
    permitted = set(parent['permitted_committed_record_types'])
    committed = _unique(record for ref in own if ref in snapshots
                        for record in snapshots[ref]['committed_record_refs']
                        if view.records.get(record)['record_type'] in permitted)
    controller = view.controller_state.as_record() if isinstance(view.controller_state, YieldState) else None
    summary = {**parent,
               'received_progress_refs': own,
               'progress_snapshots': snapshots,
               'latest_target_observation': latest,
               'committed_record_refs': committed,
               'dependencies': [] if latest is None else latest['dependencies'],
               'last_local_outcome': last_outcome,
               'outcomes': list(view.outcomes),
               'controller': controller,
               'current_credit': None if controller is None else controller['current_credit']}
    projection = information_projection(summary)
    return {**summary,
            'monitoring_information_credit': projection['monitoring_information_credit'],
            'monitoring_information_binding': projection['monitoring_information_binding'],
            'newly_informative_received_snapshot_count': projection['newly_informative_received_snapshot_count'],
            'monitor_assignment': {key: parent[key] for key in ('target_handle', 'requested_fields',
                                                                'known_progress_refs',
                                                                'permitted_committed_record_types')},
            'monitor_direct_dependencies': [] if latest is None else [
                row for row in latest['dependencies'] if row['kind'] == 'job'],
            'monitor_received_progress_refs': received,
            'monitor_information_meaning': _MEANING,
            'monitor_goal': {'objective': view.goal.objective,
                             'target_handle': parent['target_handle'],
                             'requested_fields': parent['requested_fields'],
                             'unresolved_question': _UNRESOLVED,
                             'progress_definition': _DEFINITION}}
