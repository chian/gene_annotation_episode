"""Annotation saved and nonreceipt typed return admission from its actual execution_result_acquisition child."""

def admit_return(self, source, child, index, schema, contract, result, request):
    delivery_ref = 'delivery_' + _digest({'run': self.run_id, 'parent': source.episode_id, 'index': index})[:24]
    action = self.journal.row('runtime_actions', source.episode_id, index)
    frozen_index = None if action['result'] is None else json.loads(action['result']).get('delivery_resolution_index')
    saved = self.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND ' + ('decision_index=?' if frozen_index is not None else 'delivery_ref=? ORDER BY decision_index DESC LIMIT 1'), (self.run_id, source.episode_id, frozen_index if frozen_index is not None else delivery_ref)).fetchone()
    if saved is not None:
        if saved['failure'] is not None:
            raise ReportDeliveryError(Record(json.loads(saved['failure'])))
        admitted = json.loads(saved['form'])
    else:
        try:
            admitted = contract.admit(result.as_record()['form'], audit_identifiers=(child.source.episode_id, request.goal.goal_id)).as_record()
        except ReportBoundaryError as error:
            feedback = self.delivery_feedback(delivery_ref, error)
            self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, failure=feedback)
            raise ReportDeliveryError(Record(feedback)) from error
        self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, form=admitted)
    delivery_index = index if saved is None else saved['decision_index']
    delivery_schema = schema if saved is None else json.loads(saved['contract'])['measurements']['schema']
    references = self.receive_form(source, admitted, delivery_schema, delivery_index, redelivery=delivery_index != index)
    return (admitted, references)

def _bind_original_runtime(namespace):
    from gene_annotation_episode.episodic_workflow.root.a101.library.live_runtime_functions import bind_functions
    selected = bind_functions(namespace, {name: globals()[name] for name in ('admit_return',)},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a101.runtime', qualified_names={'admit_return': 'admit_return'},
        defining_module='gene_annotation_episode.episodic_workflow.root.a101.from_child_execution_result_acquisition')
    globals().update(selected)

from gene_annotation_episode.episodic_workflow.root.a101 import runtime as _original_runtime
_bind_original_runtime(vars(_original_runtime))
