"""A104 original implicit improvement responsibility."""
from __future__ import annotations
from ..library.live_runtime_functions import bind_functions as _bind_functions

def working_state(self, source):
    arguments = {'record_selection': self.receipts.selection(source.episode_id)} if self.uses_received_record_context(source) else {}
    return self.store.reasoning_view(source.scope, limit=24, **arguments)

def _bind_original_runtime(namespace):
    definitions = {name: globals()[name] for name in ['working_state']}
    globals().update(_bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime', qualified_names={'working_state': 'working_state'}))

from .. import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
