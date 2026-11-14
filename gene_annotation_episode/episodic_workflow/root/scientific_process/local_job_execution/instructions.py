"""Original fixed local execution instructions responsibilities; source candidate."""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.communication import plain


class LocalInstructions:
    def _resource_instructions(self,context):
        workflow=getattr(self.services,'workflow',None)
        library=getattr(workflow,'launch_instructions',None)
        if library is None:return None
        return library.for_resource(self.resources[context.assignment['resource_kind']])

