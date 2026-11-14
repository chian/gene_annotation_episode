"""Private A110 Launch launch state"""
from __future__ import annotations
from .binding_roles import ROLE_KINDS
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain

class LaunchLaunchState:

    def initialize(self, context):
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import is_compact_assignment, is_compact_launch
        if is_compact_launch(plain(context.assignment)):
            self.flux_balance_requests.initialize_launch(context)
            return
        if is_compact_assignment(plain(context.assignment)):
            self.flux_balance_requests.initialize_resource(context)
            self.flux_balance_inputs.initialize(context)
            return self._delegate(context).initialize(self._practical_context(context))
        value = self._launch(plain(context.assignment), scope=context.scope)
        for request in value['requests'].values():
            self._flux_balance_inputs(context, request, input_versions=value['immutable_input_versions'])
        self._versions(value['immutable_input_versions'], context.scope, context=context, flux_balance_assignments=value['requests'].values())

    def state(self, context):
        """Expose the original practical state for its original resource role."""
        raise ValueError('practical_resource_role_required')
