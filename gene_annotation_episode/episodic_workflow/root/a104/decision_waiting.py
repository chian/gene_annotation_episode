"""A104 original decision_waiting defining responsibilities."""
from __future__ import annotations
from .library.live_runtime_functions import bind_functions as _bind_functions

def waiting_support(self, source, context, captures):
    with self.store.read_snapshot():
        arguments = {'include_identities': True}
        metadata = self.source_controller_credit(source)
        if metadata is not None:
            arguments['local_return_history'] = self.local_return_history.capture(source.episode_id, **metadata)
        support = self.wait_inputs.capture(source.episode_id, pending=context['pending_work'], known_progress_refs=self.progress_selection(source)['known_progress_refs'], current_duration_expectations=captures, **arguments)
        if metadata is None:
            support['local_return_history_unavailable_reason'] = 'controller_credit_binding_unavailable'
        if self.native_event_information is not None:
            support['native_event_targets'] = _plain(context.get('native_event_targets', []))
        return support


def _bind_original_runtime(namespace):
    definitions = {name: globals()[name] for name in ['waiting_support']}
    globals().update(_bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime', qualified_names={'waiting_support': 'waiting_support'}))

from . import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
