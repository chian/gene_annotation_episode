"""Original typed admission controls with actual Literature parent/child IDs."""
from literature_execution_boundary_checks import *

def admission_observation(host, incoming, case, parent, role):
    from gene_annotation_episode.episodic_workflow.root.workflow_values import TypedReportContract, EPISODE_BRANCH_LIFECYCLE
    from gene_annotation_episode.episodic_workflow.root.report_redelivery import ReportRedelivery
    from gene_annotation_episode.episodic_workflow.root.task_values import _digest
    from gene_annotation_episode.episodic_workflow.root.method_loop import ReportDeliveryError
    path = parent_path(parent)
    source = source_for(host, path, EpisodeRef(host.journal.run_id, path).episode_id)
    child = SimpleNamespace(source=SimpleNamespace(
        episode_id=EpisodeRef(host.journal.run_id, binding_path(parent, role)).episode_id))
    schema = {'type': 'object', 'properties': {'qualification': {'type': 'string', 'const': 'unresolved'}},
              'required': ['qualification'], 'additionalProperties': False}
    admitted_schema = TypedReportContract('Preserve a typed unresolved return', schema, lambda *a: True)
    request = source.request
    result = Record({'form': {'qualification': 'unresolved'}})
    events = []
    receive_error = RuntimeError('controlled-receive-error')
    def receive(source, form, actual_schema, index, **kwargs):
        events.append((deepcopy(form), deepcopy(actual_schema), index, kwargs))
        if case == 'receive-error':
            raise receive_error
        return ['original-received-reference']
    workflow = SimpleNamespace(store=host.store, journal=host.journal, run_id=host.journal.run_id,
        episode_branch_lifecycle=EPISODE_BRANCH_LIFECYCLE, receive_form=receive,
        delivery_feedback=ReportRedelivery.delivery_feedback)
    workflow.save_attempt = ReportRedelivery.save_attempt.__get__(workflow)
    index = 11
    host.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': index,
        'action': '{}', 'result': None, 'credit': None})
    delivery = 'delivery_' + _digest({'run': workflow.run_id, 'parent': source.episode_id, 'index': index})[:24]
    if case == 'invalid':
        result = Record({'form': {'qualification': 'invented-support'}})
    if case in ('saved', 'saved-failure', 'redelivery'):
        # Use the real save_attempt protocol, not a hand-written completed receipt.
        saved_index = 13 if case == 'redelivery' else index
        if case == 'saved-failure':
            workflow.save_attempt(source.episode_id, saved_index, delivery, child.source.episode_id,
                admitted_schema, failure={'kind': 'report_delivery_failure', 'reason': 'original-failure'})
        else:
            admitted = admitted_schema.admit(result.as_record()['form'],
                audit_identifiers=(child.source.episode_id, request.goal.goal_id)).as_record()
            workflow.save_attempt(source.episode_id, saved_index, delivery, child.source.episode_id,
                admitted_schema, form=admitted)
            result = SimpleNamespace(as_record=forbidden)
    try:
        output = incoming(workflow, source, child, index, schema, admitted_schema, result, request)
        error = None
    except (ReportDeliveryError, RuntimeError) as caught:
        output = None
        error = caught
    rows = [dict(row) for row in host.store.db.execute(
        'SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? ORDER BY decision_index',
        (workflow.run_id, source.episode_id))]
    return SimpleNamespace(output=output, error=error, events=events, rows=rows, receive_error=receive_error)
