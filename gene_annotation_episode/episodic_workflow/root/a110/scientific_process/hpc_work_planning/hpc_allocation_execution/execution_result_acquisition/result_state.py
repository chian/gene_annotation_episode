"""Private A110 Results result_state"""
from __future__ import annotations
from .binding_roles import ROLE_KINDS
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain

class ResultsResultState:

    def initialize(self, context):
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import is_compact_assignment, is_compact_launch
        if is_compact_launch(plain(context.assignment)):
            self.flux_balance_requests.initialize_launch(context)
            return
        if is_compact_assignment(plain(context.assignment)):
            self.flux_balance_requests.initialize_resource(context)
            self.flux_balance_inputs.initialize(context)
            return self._delegate(context).initialize(self._practical_context(context))
        if self.local_file_sources.applies(context):
            target = self._target(context)
            self.local_file_sources.selector(plain(context.assignment), target, validate_paths=False)
            return self._result_directory(context)
        target = self._target(context)
        self._selector(plain(context.assignment), target)
        if self._flux_balance_selector(plain(context.assignment)):
            self.initial_references(context)
        self._result_directory(context)
