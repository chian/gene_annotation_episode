"""Private A104 Launch launch state."""
from __future__ import annotations
from .contracts import BLAST_GRADED_REQUEST_VERSION, plain

class LaunchState:

    def initialize(self, context):
        value = self._launch(plain(context.assignment), scope=context.scope)
        for resource_id, request in value['requests'].items():
            if request.get('version') == BLAST_GRADED_REQUEST_VERSION:
                self._blast_launch_requirement(request, resource_id, context.scope)
        for request in value['requests'].values():
            self._masking_inputs(context, request)
            self._utility_inputs(context, request)
        self._versions(value['immutable_input_versions'], context.scope, context=context)
