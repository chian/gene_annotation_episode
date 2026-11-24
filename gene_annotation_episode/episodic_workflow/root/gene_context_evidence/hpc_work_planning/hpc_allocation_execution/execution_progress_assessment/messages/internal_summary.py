"""Where the episode stands, carried from the old ``internal_summary.py`` (``MonitorSummary.decision_context``),
``decision_state.py`` (the fields that come from the view), ``received_progress.py`` (``ReceivedProgress``,
``OwnProgress``) and the goal summary of ``goal.py`` (``MonitorGoal.planning_context``): a pure function of the
view.

Received progress is the assignment's ``known_progress_refs``, the progress refs of this monitor's own action
outcomes (in outcome order) and the progress its child monitors returned. The snapshots are the baseline ones the
commissioner passed, those the observe tool's outcomes carry and those the children returned; a reference without a
snapshot raises where the old progress provider would have been read (``credit.snapshot_of``). The exposed direct
dependencies are those of the latest delivered observation of the assigned target (the old code asked the progress
provider for them; they are only present when ``dependencies`` was among the observed fields). Fields of the old
decision state that came from the old runner (the pending work, the report lifecycle and deliveries, the
recorded-journal views) are not carried."""
from yield_control import YieldState

from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import information_projection, snapshot_of

_MEANING = ('Exposed direct relationships and already delivered observations. Empty measurements/log windows do '
            'not assert absence or a stall.')
_UNRESOLVED = 'Which exposed progress information would improve the original requested report?'
_DEFINITION = ('Actual received information under the caller-bound monitoring projector; repeated identities and '
               'timestamps alone earn no credit.')


def _unique(values):
    return list(dict.fromkeys(values))


def internal_summary(view):
    parent = view.parent_input
    snapshots = dict(parent['known_progress_snapshots'])
    own, history, last_outcome = [], [], None
    for outcome in view.outcomes:
        last_outcome = outcome
        if outcome['kind'] == 'tool':
            result = outcome['outcome']
            own.extend(result.get('progress_refs', []))
            if 'snapshot' in result and result['status'] != 'invalid':
                snapshots[result['snapshot']['progress_ref']] = result['snapshot']
            history.append({'tool': outcome['tool'], 'status': result['status'],
                            'progress_refs': list(result.get('progress_refs', []))})
        else:
            report = outcome['report']
            own.extend(report['progress_refs'])
            snapshots.update(report['progress_snapshots'])
            history.append({'child': outcome['slot'], 'progress_refs': list(report['progress_refs'])})
    own = _unique(own)
    received = _unique([*parent['known_progress_refs'], *own])
    # The latest delivered observation of the assigned target, in receipt order (the old ``facts`` order).
    target = [snapshot for snapshot in (snapshot_of(snapshots, ref) for ref in received)
              if snapshot['target_handle'] == parent['target_handle']]
    latest = target[-1] if target else None
    permitted = set(parent['permitted_committed_record_types'])
    committed = _unique(record for ref in received for record in snapshots[ref]['committed_record_refs']
                        if view.records.get(record)['record_type'] in permitted)
    controller = view.controller_state.as_record() if isinstance(view.controller_state, YieldState) else None
    summary = {**parent,
               'own_progress_refs': own,
               'received_progress_refs': received,
               'progress_snapshots': snapshots,
               'latest_target_observation': latest,
               'committed_record_refs': committed,
               'last_local_outcome': last_outcome,
               'outcome_history': history,
               'controller': controller,
               'action_yields': (yield_table(view.controller_state,
                                             forecast_unit='newly informative received progress snapshot')
                                 if controller is not None else None),
               'current_credit': None if controller is None else controller['current_credit']}
    projection = information_projection(summary)
    return {**summary,
            'monitoring_information_credit': projection['monitoring_information_credit'],
            'monitoring_information_binding': projection['monitoring_information_binding'],
            'newly_informative_received_snapshot_count': projection['newly_informative_received_snapshot_count'],
            'monitor_assignment': {key: parent[key] for key in ('target_handle', 'requested_fields',
                                                                'known_progress_refs',
                                                                'permitted_committed_record_types')},
            'monitor_direct_dependencies': [] if latest is None else latest['dependencies'],
            'monitor_received_progress_refs': received,
            'monitor_information_meaning': _MEANING,
            'monitor_goal': {'objective': view.goal.objective,
                             'target_handle': parent['target_handle'],
                             'requested_fields': parent['requested_fields'],
                             'unresolved_question': _UNRESOLVED,
                             'progress_definition': _DEFINITION}}
