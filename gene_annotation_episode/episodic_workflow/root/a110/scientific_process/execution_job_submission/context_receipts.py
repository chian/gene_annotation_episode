"""Private A110 Launch context receipts"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain

class LaunchContextReceipts:

    def required_return_sources(self, parent, role):
        """Preserve the original job identity across a scientific return."""
        if parent is not None and parent.path[-1][0] == 'scientific_process' and getattr(self.services, 'annotation_task_required', lambda: False)():
            return ('execution_handoff_refs',)
        return ()

    def initial_references(self, context):
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import is_compact_assignment, is_compact_launch, read_request_binding
        if is_compact_assignment(plain(context.assignment)) or is_compact_launch(plain(context.assignment)):
            control = read_request_binding(self.store, self.run_id, context.episode_id)
            return list(dict.fromkeys((version['reference'] for row in control['requests'] for version in row['input_versions'])))
        if context.role != 'results':
            assignment = plain(context.assignment)
            requests = assignment.get('requests', {}).values() if context.role == 'launch' else [assignment] if context.role == 'launch_local' else []
            references = []
            for request in requests:
                references.extend(self._flux_balance_inputs(context, request))
            return list(dict.fromkeys(references))
        assignment = plain(context.assignment)
        selected = [assignment['handoff_ref']]
        target = self._target(context)
        if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
            selector = self._selector(assignment, target)
            if selector['mode'] == 'saved_sheet_recalculation':
                self.native_flux_balance_returns.authenticate_received_saved_sheet(context, selector['saved_sheet_file'])
                selected.append(selector['saved_sheet_file']['artifact_ref'])
        return list(dict.fromkeys(selected))
