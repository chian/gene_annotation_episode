from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _delegate
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _practical_context
from .execution_contracts import BLAST_GRADED_RETURN_SCHEMA
from .execution_contracts import BLAST_GRADED_RETURN_SOURCE
from .execution_contracts import ROLE_KINDS
from .execution_contracts import plain

class NativeState:
    _delegate = _delegate
    _practical_context = _practical_context

    def initialize(self, context):
        self._check_parent_inputs(context)
        return self._delegate(context).initialize(context)

    def state(self, context):
        """Expose the original practical state for its original resource role."""
        raise ValueError('practical_resource_role_required')
