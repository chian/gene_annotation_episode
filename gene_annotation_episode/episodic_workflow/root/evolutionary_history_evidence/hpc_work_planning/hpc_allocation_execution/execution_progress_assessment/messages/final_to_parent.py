"""The return. ``RETURN_FORM`` declares required ``credit`` and ``finding`` and the monitoring facts as selectable
fields (the parent selects which it wants), plus ``monitoring_progress_snapshots`` (what the child monitor returns so
that its parent's credit can read the delivered observations; the commission of a child monitor selects it). A fact
that is absent when nothing was observed (execution state, result availability, observation time) is a ``record``
holding ``{'value': ...}``. ``monitoring_committed_record_refs`` is a ``list`` of references, not ``record_refs``:
this episode holds none of those committed records (the job produced them). Facts come from delivered observations
only; nothing is observed at closure and no model composes the report."""
from datetime import datetime

from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'target_handle': Field('text', 'The assigned execution target'),
    'observed': Field('boolean', 'Whether this monitor received an observation of the assigned target'),
    'execution_state': Field('text', 'The assigned target state in its latest delivered observation', required=False),
    'result_available': Field('boolean', 'Result availability in the latest delivered observation', required=False),
    'received_progress_ref_count': Field('integer', 'How many progress observations this monitor delivered'),
    'newly_informative_snapshot_count': Field('integer', 'How many received snapshots were newly informative'),
    'qualification': Field('text', 'What the finding does and does not establish'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the monitor found of the assigned target', form=FINDING_FORM),
    'monitoring_progress_refs': Field(
        'list', 'Original delivered progress observation identities, including those delivered by dependency '
                'monitors.', required=False),
    'monitoring_target_handle': Field('text', 'The immutable assigned semantic target handle.', required=False),
    'monitoring_execution_state': Field(
        'record', 'Assigned target state in the latest delivered observation (pending, executing, returned, '
                  'admitted) as {"value": state}; value is null without an observation.', required=False),
    'monitoring_result_available': Field(
        'record', 'Assigned target result availability in the latest delivered observation as {"value": ...}; '
                  'value is null without an observation.', required=False),
    'monitoring_observed_at_unix_seconds': Field(
        'record', 'Original assigned-target observation time, converted from UTC without refreshing it, as '
                  '{"value": ...}; value is null without an observation.', required=False),
    'monitoring_committed_record_refs': Field(
        'list', 'Parent-permitted committed record references actually delivered in these progress observations '
                '(named, not passed in custody).', required=False),
    'monitoring_dependency_handles': Field(
        'list', 'Exposed direct dependencies in the latest delivered assigned-target observation; no descendant '
                'traversal.', required=False),
    'monitoring_progress_snapshots': Field(
        'record', 'The delivered progress observations by identity, for the commissioning monitor\'s credit.',
        required=False),
})

_QUALIFICATION = ('Facts are those of delivered observations only. Liveness establishes process presence only; '
                  'elapsed time alone establishes neither productive work nor a stall; unknown information stays '
                  'unknown.')


def _timestamp_seconds(value):
    """The Unix seconds of a UTC ISO timestamp."""
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def monitor_facts(summary):
    """The recorded facts from the progress observations the monitor received."""
    latest = summary['latest_target_observation']
    return {'monitoring_progress_refs': list(summary['received_progress_refs']),
            'monitoring_target_handle': summary['target_handle'],
            'monitoring_execution_state': {'value': latest['execution_status']['lifecycle_state'] if latest else None},
            'monitoring_result_available': {'value': latest['result_available'] if latest else None},
            'monitoring_observed_at_unix_seconds': {
                'value': _timestamp_seconds(latest['observed_at']) if latest else None},
            'monitoring_committed_record_refs': list(summary['committed_record_refs']),
            'monitoring_dependency_handles': [row['handle'] for row in latest['dependencies']] if latest else [],
            'monitoring_progress_snapshots': dict(summary['progress_snapshots'])}


def final_to_parent(summary, completion, selection):
    facts = monitor_facts(summary)
    latest = summary['latest_target_observation']
    finding = {'target_handle': summary['target_handle'], 'observed': latest is not None,
               'received_progress_ref_count': len(summary['received_progress_refs']),
               'newly_informative_snapshot_count': summary['newly_informative_received_snapshot_count'],
               'qualification': _QUALIFICATION}
    if latest is not None:
        finding['execution_state'] = latest['execution_status']['lifecycle_state']
        finding['result_available'] = latest['result_available']
    return {'credit': completion['credit'], 'finding': finding, **{name: facts[name] for name in selection}}
