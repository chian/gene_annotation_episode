"""MonitorSummary"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a106.communication import plain

class MonitorSummary:

    def decision_context(self, context, current_view):
        self._role(context.role)
        value = self._assignment(context.assignment, context.scope)
        describe = getattr(self.services, 'describe_progress_target', None)
        result = {'monitor_assignment': value, 'monitor_target_description': describe(value['target_handle'], context.scope) if describe else None, 'monitor_direct_dependencies': plain(self.services.dependencies(value['target_handle'], context.scope)), 'monitor_received_progress_refs': self._received(context), 'monitor_information_meaning': 'Exposed direct relationships and already delivered observations. Empty measurements/log windows do not assert absence or a stall.'}
        result['monitor_goal'] = self.planning_context(context)
        return result
