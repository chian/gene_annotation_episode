"""Private A104 Launch capability operations."""
from __future__ import annotations
from .contracts import _outcome, checked, launch_operation_catalog

class LaunchCapabilities:

    def catalog(self, context):
        return launch_operation_catalog()

    async def execute(self, context, tool_name, arguments, operation_key):
        try:
            catalog = {entry['name']: entry for entry in self.catalog(context)}
            if tool_name not in catalog:
                raise ValueError('execution_operation_not_available')
            arguments = checked(arguments, catalog[tool_name]['input_schema'], 'invalid_execution_operation_arguments')
            return _outcome(self.initial_decision_context(context))
        except (ValueError, TypeError) as error:
            from gene_annotation_episode.episodic_workflow.root.a104.native_file_capture import NativeFileCaptureError
            return _outcome(code=str(error))
