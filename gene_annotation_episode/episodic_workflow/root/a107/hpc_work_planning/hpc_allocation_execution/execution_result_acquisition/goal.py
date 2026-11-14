"""Private A107 Results goal"""
from __future__ import annotations
from .binding_roles import KINDS
from .binding_roles import ROLE_KINDS
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain

class ResultsGoal:

    def child_roles(self, role):
        return ()

    def allowed_children(self, parent, caller_capabilities):
        return ()

    def permitted_common_actions(self, context):
        target = self._target(context)
        if target['resource_kind'] == 'api' and target['assignment']['version'] == 'api_service_assignment_v1':
            return ('tool', 'wait')
        return ('tool',)
