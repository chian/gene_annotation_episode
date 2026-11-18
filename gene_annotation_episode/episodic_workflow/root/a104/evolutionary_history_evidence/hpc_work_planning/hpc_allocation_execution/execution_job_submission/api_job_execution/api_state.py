"""Private A104 API api state."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class APIApiState:

    def initialize(self, context):
        self.local_file_sources.applies(context)
        self._check_parent_inputs(context)
        return self._api_execution_for(context).initialize(context)

    def _api_execution_for(self, context):
        assignment = self._validate_request(plain(context.assignment))
        return self.api_execution
