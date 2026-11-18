"""Private A104 HPCExecution native actions."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class HPCExecutionNativeActions:

    def catalog(self, context):
        self.native_blast_masking_results.applies(context)
        self.native_blast_utility_results.applies(context)
        practical_context = self._practical_context(context)
        return self._delegate(context).catalog(practical_context)

    async def execute(self, context, tool_name, arguments, operation_key):
        self._check_parent_inputs(context)
        practical_context = self._practical_context(context)
        outcome = await self._delegate(context).execute(practical_context, tool_name, arguments, operation_key)
        return outcome
