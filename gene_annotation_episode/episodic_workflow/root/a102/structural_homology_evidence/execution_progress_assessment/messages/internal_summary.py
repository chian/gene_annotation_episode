"""The A102 monitor's internal summary (carried from ``internal_summary.py``, ``received_progress.py`` and the
planning context of ``goal.py``): a pure function of the view.

Received progress is the assignment's ``known_progress_refs``, the progress references of this monitor's own tool
outcomes (in outcome order) and those its dependency monitors returned. The snapshots are the baseline ones the
commissioner passed, those the observe tool's outcomes carry and those the children returned. The committed
records are those of the received observations whose type the parent permitted; each must be held (a read of one
the Episode does not hold raises ``CustodyError``). Fields of the old decision state that came from the old runner
(pending work, the report lifecycle and deliveries, the journal views) are not carried.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import plain

MEANING = ('Exposed direct relationships and already delivered observations. Empty measurements/log windows do not '
           'assert absence or a stall.')
PROGRESS_DEFINITION = ('Actual received information under the monitoring information projector; repeated '
                       'identities and timestamps alone earn no credit.')
UNRESOLVED_QUESTION = 'Which exposed progress information would improve the original requested report?'
FORECAST_UNIT = 'newly informative received progress snapshot'


def _unique(values):
    return list(dict.fromkeys(values))


def internal_summary(view):
    parent = view.parent_input
    snapshots = dict(parent['known_progress_snapshots'])
    own, history, last = [], [], None
    for unit in view.outcomes:
        last = unit
        if unit['kind'] == 'tool':
            result = unit['outcome']
            own.extend(result.get('progress_refs', ()))
            if 'snapshot' in result:
                snapshots[result['snapshot']['progress_ref']] = result['snapshot']
            history.append({'tool': unit['tool'], 'status': result['status'],
                            'progress_refs': list(result.get('progress_refs', ()))})
        else:
            report = unit['report']
            own.extend(report['progress_refs'])
            snapshots.update(report['progress_snapshots'])
            history.append({'child': unit['slot'], 'progress_refs': list(report['progress_refs'])})
    received = _unique([*parent['known_progress_refs'], *own])
    target = [snapshots[reference] for reference in received
              if reference in snapshots and snapshots[reference]['target_handle'] == parent['target_handle']]
    latest = target[-1] if target else None
    permitted = set(parent['permitted_committed_record_types'])
    committed = _unique(record for reference in received if reference in snapshots
                        for record in snapshots[reference]['committed_record_refs']
                        if view.records.get(record)['record_type'] in permitted)
    controller = (yield_table(view.controller_state, forecast_unit=FORECAST_UNIT)
                  if view.controller_state is not None else None)
    return {**parent,
            'own_progress_refs': _unique(own),
            'received_progress_refs': received,
            'progress_snapshots': snapshots,
            'latest_target_observation': latest,
            'committed_record_refs': committed,
            'last_outcome': plain(last),
            'outcome_history': history,
            'controller': controller,
            'information_meaning': MEANING,
            'goal': {'objective': plain(view.goal.objective), 'target_handle': parent['target_handle'],
                     'requested_fields': parent['requested_fields'], 'unresolved_question': UNRESOLVED_QUESTION,
                     'progress_definition': PROGRESS_DEFINITION}}
