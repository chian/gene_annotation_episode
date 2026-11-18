"""Private A103 scientific to children."""
from __future__ import annotations
from .to_child_execution_progress_assessment import prepare_request as prepare_monitor_request

class ScientificChildRequests:

    def child_roles(self, role):
        self._role(role)
        return self._child_roles

    def allowed_children(self, parent, caller_capabilities):
        self.validate_context(parent)
        from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.child_policy import allowed_child_roles
        return allowed_child_roles(self._child_roles)

    def prepare_child_request(self, parent, role, assignment):
        if role == 'monitor':
            return prepare_monitor_request(assignment)
        return assignment

    def required_return_sources(self, parent, role):
        self._role(role)
        if parent is not None and getattr(self.services, 'annotation_task_required', lambda: False)():
            if len(parent.path) == 1:
                return ('gene_context_evidence_results', 'committed_record_refs')
            return ('committed_record_refs',)
        return ()
