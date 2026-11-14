"""A106 original implicit improvement responsibility; distinct private invocation."""
from __future__ import annotations
from ..library.live_runtime_functions import bind_functions as _bind_functions

def __init__(self, workflow, path, request, scope):
    self.workflow, self.path, self.request, self.scope = (workflow, path, request, scope)
    self.episode_id = Episode.identity(workflow.context, workflow.grains[path[-1][0]], path[-1][1], parent_path=path[:-1]).episode_id
    self.calls = 0
    self.feedback = None
    self.last_outcome = None
    self.last_outcome_index = None
    self.report_values = _plain(request.message.as_record()['initial_report'])
    self.report_basis = []
    self._restored = False
    self._unfinished_own_actions = []
    self._source_revision = None
    self._latest_effect_index = None
    self._restored_source_state = None
    self._model_snapshot = None
    self._presented_conversation_key = None
    self._selection_view = None
    self._delivery_resolution_ref = None
    self._execution_context = None
    self._suspension_condition = None
    self._inprocess_replay_ready = False
    self.interpret_schema = interpretation_schema(request.report_contract.schema) if request.report_contract else _object({})

def _bind_original_runtime(namespace):
    names = {'__init__': '__init__'}
    globals().update(_bind_functions(namespace, {name: globals()[name] for name in names},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime', qualified_names=names,
        defining_module='gene_annotation_episode.episodic_workflow.root.a106.annotation_improvement.from_parent'))

from .. import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
