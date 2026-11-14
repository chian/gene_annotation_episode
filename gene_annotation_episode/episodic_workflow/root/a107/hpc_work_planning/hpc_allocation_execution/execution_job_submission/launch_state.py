"""Private A107 Launch launch state"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.a107_blast_execution import BLAST_GRADED_REQUEST_VERSION
from .binding_roles import ROLE_KINDS
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain

class LaunchLaunchState:

    def initialize(self, context):
        value = self._launch(plain(context.assignment), scope=context.scope)
        for resource_id, request in value['requests'].items():
            if request.get('version') == BLAST_GRADED_REQUEST_VERSION:
                self._blast_launch_requirement(request, resource_id, context.scope)
        for request in value['requests'].values():
            self._masking_inputs(context, request)
            self._utility_inputs(context, request)
        self._versions(value['immutable_input_versions'], context.scope, context=context, nmf_assignments=value['requests'].values())

    def state(self, context):
        """Expose the original practical state for its original resource role."""
        raise ValueError('practical_resource_role_required')
